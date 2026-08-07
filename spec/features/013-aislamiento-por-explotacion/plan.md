# 013 — Plan de implementación

Spec aprobada por Raúl el 2026-08-06 (opción A: aislamiento completo, antes de Stripe).

---

## Corrección al diagnóstico inicial

La spec decía que el histórico tenía la misma fuga que la Revisión. **No es exacto.**
Al leer `explotacion.py` a fondo:

- `/api/historial` (explotacion.py:219) y `/api/stats` (:160) **ya acotan** por
  explotación con `parcela_scope_clause()`. Tratamientos, fertilización,
  labores, cosecha, riego, abonado y cultivos_campana salen bien.
- La única fuga del histórico es **compras**, y es deliberada:
  `explotacion.py:281` lo dice explícitamente — *"Compras es un libro a nivel de
  usuario (no cuelga de parcela); no se acota por explotación en Fase 1."*
  Esta feature es esa Fase 2.
- Lo que **no acota nada** son los listados CRUD de cada módulo (ver tabla
  abajo), que es otra vía por la que Lourdes ve datos cruzados.

Y un fallo latente que hay que arreglar de paso: como `parcela_id` es nullable,
`parcela_scope_clause()` **hoy ya oculta** del histórico y de las estadísticas
todo registro sin parcela asignada, en todas las explotaciones. Al migrar a
`explotacion_id` esos registros reaparecen. Es una mejora, pero hay que avisar a
Lourdes de que pueden salirle registros que llevaba tiempo sin ver.

---

## Inventario: qué toca cambiar

### Rutas que NO acotan hoy (la fuga)

| Ruta | Fichero | Tabla |
|---|---|---|
| `/api/tratamientos` GET | tratamientos.py:155 | tratamientos |
| `/api/fertilizacion` GET | fertilizacion.py:204 | fertilizacion |
| `/api/riego` GET | fertilizacion.py:298 | riego |
| `/api/abonado` GET | fertilizacion.py:372 | abonado |
| `/api/labores` GET | labores.py:38 | labores |
| `/api/cosecha` GET | labores.py:101 | cosecha |
| `/api/compras` GET | compras.py:55 | compras |
| `/api/equipos` GET | equipos.py:12 | equipos |
| `/api/aplicadores` GET | equipos.py:46 | aplicadores |
| `/api/asesores` GET | asesores.py:39 | asesores |
| `/api/uhc` GET | uhc.py:23 | unidades_homogeneas |
| `/api/cumplimiento` GET | cumplimiento.py:565 | 11 consultas |
| `/api/ia/alertas`, `/api/ia/sugerencias` | ia.py:284,320 | varias |
| `/api/historial` (solo compras) | explotacion.py:280 | compras |

Cada una tiene su gemelo `/<int:id>` (GET/PUT/DELETE) que también debe validar
que el registro pertenece a la explotación activa, no solo al usuario. Si no, un
PUT con un id de la otra finca sigue funcionando.

### INSERT que deben escribir `explotacion_id`

Además de los POST de las rutas anteriores: `nlp.py:311` (`/api/parse/guardar`),
`imports_exports.py:125` (import Excel), `:168` (import GSheet), `:245`
(backup/import) y `parcelas.py:209` (alta multirrecinto) / `:281`
(cultivos-campana).

### Qué NO se toca

- `exports.py` / `export_pdf.py`: ya acotan. `parcela_scope_clause()` se
  conserva y se marca como legado en su docstring.
- `/api/account/export-data` (auth.py:163): export RGPD, debe seguir devolviendo
  **todo** lo del usuario, de todas sus explotaciones. Es correcto tal cual.
- `admin.py`: opera por `user_id` a propósito (soporte). No se acota.
- `aemet.py`, `push.py`, `stripe_bp.py`, `sigpac.py`: no leen datos de cuaderno.

### Nota sobre el seeding

`_seed_if_needed` (db.py:954) solo siembra equipos para `SINGLE_USER_ID` (cuenta
legacy de desarrollo). El registro real (auth.py:75) crea explotación vacía sin
equipos. Así que **una explotación nueva nacerá sin equipos ni personas, igual
que nace una cuenta nueva**. Es coherente con la decisión de producto y no hay
que tocar nada.

---

## Decisión de implementación: sin helper nuevo

Una vez las 11 tablas tienen `explotacion_id`, el filtro es el literal
`" AND explotacion_id=?"`. Se escribe tal cual en cada consulta.

No se crea un helper que devuelva ese fragmento: sería indirección para 24
caracteres, y `parcela_scope_clause()` solo existía porque el `IN (SELECT …)`
era largo y fácil de escribir mal. La red de seguridad contra olvidos es el test
de la Fase 6, no un helper (principios.md: simplicidad sobre elegancia).

---

## Fases (una por commit)

### Fase 0 — Test que falla primero

`backend/tests/test_aislamiento_explotacion.py`, en el estilo de
`test_cumplimiento.py` (script con `check()`, sin pytest).

Monta un usuario con dos explotaciones A y B, mete un registro en cada tabla de
cada una, y comprueba que consultar A no devuelve nada de B. Debe **fallar** al
escribirlo. Es el criterio de "hecho" de toda la feature.

### Fase 1 — Esquema y migración (`db.py`)

1. `_add_col(c, tabla, 'explotacion_id', 'INTEGER')` en `init_db()` para:
   `tratamientos`, `fertilizacion`, `labores`, `riego`, `cosecha`, `abonado`,
   `cultivos_campana`, `compras`, `equipos`, `aplicadores`, `asesores`,
   `unidades_homogeneas`.
2. Índice `idx_<tabla>_expl` por tabla, en la lista de índices ya existente
   (db.py:1023). Con 50+ parcelas y un filtro en cada query, sin índice se nota.
3. `_backfill_explotacion_datos(conn)`, nueva, junto a
   `_backfill_explotaciones()` y llamada después de ella:
   - Donde haya `parcela_id` no nulo → heredar de la parcela.
   - Resto → `resolve_default_explotacion()` del usuario.
   - Filas que queden NULL → `logger.error` con tabla y recuento. No forzar
     `NOT NULL` sobre una tabla con huérfanos (criterio de
     `_harden_user_id_postgres`).
   - Idempotente: solo toca `WHERE explotacion_id IS NULL`.

Verificación de la fase: correr `init_db()` dos veces sobre una copia y
comprobar que el segundo pase no cambia ninguna fila.

### Fase 2 — Módulos CRUD simples

Un commit por fichero: `equipos.py` (equipos + aplicadores), `asesores.py`,
`compras.py`, `uhc.py`, `labores.py` (labores + cosecha).

Por cada uno: `exp_id = get_active_explotacion_id(conn)` al principio, `AND
explotacion_id=?` en GET/PUT/DELETE, y la columna en el INSERT.

### Fase 3 — Módulos grandes

`tratamientos.py` y `fertilizacion.py` (fertilización + riego + abonado).
Además de lo anterior, aquí hay que **validar las referencias cruzadas**: el
POST/PUT de tratamientos debe rechazar un `equipo_id`, `aplicador_id`,
`asesor_id` o `parcela_id` que pertenezca a otra explotación. Sin esto, el
aislamiento se puede saltar desde el formulario.

### Fase 4 — La Revisión del cuaderno (el reporte de Lourdes)

`cumplimiento.py`:

1. `evaluar_cumplimiento(conn, uid, hoy=None, campana=None, explotacion_id=None)`.
   Parámetro nuevo al final para no romper las ~12 llamadas del test existente.
2. Arreglar el bug de la campaña (línea 217): leer `campana_activa` de la
   explotación activa (`WHERE id=? AND user_id=?`), no la primera fila que salga.
3. `AND explotacion_id=?` en las 11 consultas.
4. El endpoint (:572) pasa `get_active_explotacion_id(conn)`.
5. Revisar los comentarios del módulo que hablan de "a nivel de usuario" — ya no
   es cierto y el fichero está muy comentado; dejarlos desactualizados es peor
   que no tenerlos.

### Fase 5 — Alertas del Inicio y entradas por voz

`ia.py` (`_generar_alertas`, `_recalcular_patrones`, sugerencias), `nlp.py`
(`/api/parse/guardar` debe escribir la explotación activa),
`imports_exports.py` (los 3 puntos de import) y `explotacion.py:280` (quitar el
caso especial de compras del histórico).

### Fase 6 — Test de aislamiento genérico

Ampliar el de la Fase 0 con un test que **enumere las tablas** que deben llevar
`explotacion_id` y falle si alguna no la tiene o si una consulta la ignora. Es
lo que evita que la próxima tabla nazca con fuga.

### Fase 7 — Frontend

Comprobar que al cambiar de explotación en el selector se refrescan todas las
pantallas afectadas (criterio de aceptación 9). Si hoy solo se recarga alguna,
ajustarlo. Tras cualquier cambio en `.jsx`: `npm run build`.

### Fase 8 — Verificación con datos reales

1. Copia de seguridad de producción **antes** de desplegar la migración.
2. En local, con una copia de los datos de Lourdes: comprobar que el nº total de
   registros por tabla no cambia y que ninguno queda con `explotacion_id` NULL.
3. Reasignar a mano los equipos, aplicadores, asesores y facturas de Lourdes que
   pertenezcan a una explotación distinta de la de por defecto. **Este paso es
   manual e inevitable** (ver spec: el dato nunca se guardó).
4. Que Lourdes abra la Revisión con cada explotación seleccionada y confirme que
   solo ve lo suyo.

---

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Una query olvidada sigue filtrando | Test de la Fase 6, que enumera tablas |
| Registros que desaparecen del listado | Fase 8.2: comparar recuentos antes/después |
| Referencias cruzadas entre fincas tras el backfill | Fase 3: validación en POST/PUT |
| Migración a medias en producción | Todo con `_add_col()`, backfill idempotente, y reinicio completo de gunicorn (CLAUDE.md) |
| Trabajo largo, riesgo de dejarlo a medias | Un commit por fase, cada uno desplegable por sí solo |

## Flujo

Rama `fix/aislamiento-explotacion`, PR a `main`, CI (lint + bandit) + Security
Review de Claude. Nunca push directo a `main`.
