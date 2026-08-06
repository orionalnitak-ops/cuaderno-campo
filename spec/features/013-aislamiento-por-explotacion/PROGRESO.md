# 013 — Progreso y handoff

**Rama:** `fix/aislamiento-explotacion` (base: `main` @ 384c459)
**Estado:** Fases 0-4 de 8 hechas. El bug que reportó Lourdes YA está arreglado.
**Última actualización:** 2026-08-06

Este archivo es el punto de entrada para retomar el trabajo en una sesión nueva.
Leer primero `spec.md` (qué y por qué) y `plan.md` (las 8 fases).

---

## Cómo verificar que todo sigue en pie

```bash
cd "H:\Proyectos\Cuaderno ex app\backend"
export PYTHONIOENCODING=utf-8   # sin esto, la consola de Windows (cp1252) rompe
                                # los tests que imprimen '↔'. No es fallo de lógica.
for t in test_cumplimiento test_asesores test_ia_patrones test_alta_multirecinto \
         test_user_id_not_null test_estado_sigpac test_aislamiento_explotacion; do
  venv/Scripts/python.exe tests/$t.py >/dev/null 2>&1 && echo "$t PASA" || echo "$t FALLA"
done
```

Los 7 pasan a día de hoy. `test_aislamiento_explotacion.py` es el criterio de
"hecho" de la feature.

---

## Hecho (5 commits)

| Commit | Fase | Qué |
|---|---|---|
| `dacea98` | 0 | Test en rojo del aislamiento + spec y plan |
| `8e855f2` | 1 | `explotacion_id` en 12 tablas, backfill idempotente, índices |
| `80584d3` | 2 | equipos, aplicadores, asesores, compras, UHC, labores, cosecha |
| `3996238` | 3 | tratamientos, fertilización, riego, abonado + referencias cruzadas |
| `4529433` | 4 | Revisión del cuaderno + bug silencioso de la campaña |

### Piezas clave que conviene conocer antes de seguir

- **`db.py` → `TABLAS_POR_EXPLOTACION`**: fuente única de verdad, 12 tablas. La
  usan la migración, los índices y el backfill. **Toda tabla nueva de datos del
  agricultor va aquí.** El valor es la columna de la que heredar la explotación,
  o `None` si no cuelga de parcela.
- **`db.py` → `_backfill_explotacion_datos()`**: dos pasadas (heredar de la
  parcela; si no, explotación por defecto del usuario). Idempotente. Lo que quede
  en NULL sale por `logger.error` con tabla y recuento.
- **Patrón de filtrado**: literal `AND explotacion_id=?`, sin helper. La red
  contra olvidos es el test de la Fase 6, no una abstracción.
- **`parcela_scope_clause()` está marcado LEGADO**. Solo lo usan `exports.py` y
  `export_pdf.py`. No usarlo en código nuevo (ver "Trampas" abajo).
- **`cumplimiento.py`**: `evaluar_cumplimiento(conn, uid, hoy, campana, explotacion_id)`.
  El parámetro va al final para no romper llamadas antiguas. Dentro se compone
  `expl_sql`/`expl_par` y se concatena a las 11 consultas.

---

## Pendiente

### Fase 5 — Alertas del Inicio, voz e imports  ← EMPEZAR AQUÍ

| Fichero | Qué hacer |
|---|---|
| `blueprints/ia.py` | `_generar_alertas`, `_recalcular_patrones` y `/api/ia/sugerencias` (:284) y `/api/ia/alertas` (:320) no acotan. Ojo: `_generar_alertas` hace 1+3·N consultas y con 50 parcelas son ~151 dentro del login; no empeorarlo. |
| `blueprints/nlp.py` | `/api/parse/guardar` (:311) debe escribir la explotación activa en los INSERT. |
| `blueprints/imports_exports.py` | 3 puntos de INSERT: `/api/import/excel` (:125), `/api/import/gsheet` (:168), `/api/backup/import` (:245). |
| `blueprints/explotacion.py` | Quitar el caso especial de compras del histórico (:280-282) — el comentario "no se acota por explotación en Fase 1" ya no aplica: compras se acotó en `80584d3`. |
| `blueprints/parcelas.py` | Revisar que `/api/cultivos-campana` (:281) y el alta multirrecinto (:209) escriban `explotacion_id` en `cultivos_campana`. |

### Fase 6 — Test genérico

Ampliar `test_aislamiento_explotacion.py` con un test que **enumere**
`TABLAS_POR_EXPLOTACION` y falle si una tabla no tiene la columna o si una
consulta la ignora. Es lo que evita que la próxima tabla nazca con fuga.

### Fase 7 — Frontend

Comprobar que al cambiar de explotación en el selector se refrescan todas las
pantallas afectadas (criterio de aceptación 9 de la spec). El scoping en sí NO
necesita cambios de frontend: las llamadas van con cookie y la sesión ya lleva
`active_explotacion_id`. Tras tocar cualquier `.jsx`: `npm run build` en
`frontend/`.

### Fase 8 — Verificación con datos reales

1. **Copia de seguridad de producción antes de desplegar la migración.**
2. En local con copia de los datos de Lourdes: que el nº de registros por tabla
   no cambie y que no quede ningún `explotacion_id` NULL.
3. **Paso manual inevitable:** reasignar a mano los equipos, aplicadores,
   asesores y facturas de Lourdes que sean de otra finca. El backfill los deja
   todos en la explotación por defecto porque el dato de a qué finca pertenecían
   nunca se guardó.
4. Que Lourdes abra la Revisión con cada explotación y confirme que solo ve lo
   suyo.

---

## Trampas encontradas (no volver a pisarlas)

1. **`parcela_scope_clause()` oculta registros.** `parcela_id` es nullable en
   tratamientos, fertilizacion, labores, riego, cosecha y abonado, y
   `parcela_id IN (…)` descarta los NULL. Es decir: hoy el histórico y las
   estadísticas ya esconden los registros sin parcela, en todas las
   explotaciones. **Al migrar a `explotacion_id` esos registros REAPARECEN.**
   → **Avisar a Lourdes**, o pensará que la app se ha inventado datos.
2. **`/api/historial` y `/api/stats` ya acotaban.** La única fuga real del
   histórico era `compras`. Lo que no acotaba nada eran los listados CRUD.
3. **`cultivos_campana` no tiene `user_id`** — cuelga de la parcela y el dueño se
   comprueba con JOIN. No puede entrar en backfills por usuario.
4. **Lo crítico no son los listados, son las referencias cruzadas.** Un
   tratamiento apunta a parcela, equipo, aplicador, asesor y UHC. Las
   comprobaciones de ROPO/ROMA llevan el filtro en la MISMA consulta, para que un
   equipo de otra finca dé "no encontrado" en vez de colarse por tener el ROMA.
5. **Un UHC anterior a esta feature puede contener parcelas de dos fincas.** Los
   tratamientos se expanden por grupo, así que `_parcelas_uhc()` valida el grupo
   Y sus parcelas. Sin eso, un solo POST escribe en la explotación equivocada.
6. **`_SCOPE_ALIASES` de `db.py`:** el alias `'c'` es **cosecha**, no compras.
7. **Consola de Windows:** los tests que imprimen `↔` fallan en cp1252. Correr
   con `PYTHONIOENCODING=utf-8`.
8. **`parcela_es_del_usuario()` está duplicada** en `tratamientos.py` y
   `fertilizacion.py`. Se mantienen las dos a propósito (unificarlas crea un
   import cruzado entre los dos módulos más grandes). Si se toca una, tocar la otra.

---

## Para el PR

- Rama `fix/aislamiento-explotacion` → PR a `main`. Nunca push directo.
- CI: lint + bandit. Cada PR recibe Security Review de Claude.
- **Antes de abrir el PR:** terminar la Fase 6 (el test genérico es la garantía
  de que no queda ninguna fuga) y la Fase 8.2 (recuentos antes/después).
- **Mencionar en el cuerpo del PR:** el aviso del punto 1 de "Trampas", porque
  cambia lo que Lourdes ve, y el paso manual de la Fase 8.3.
- Este PR toca `db.py`, así que en producción hace falta **reinicio completo de
  gunicorn**, no hot-reload (CLAUDE.md).

## Ojo con otras ramas

- **`feat/stripe-gracia`** (`2f4bb83`): trabajo de Stripe a medias, rescatado el
  2026-08-06 de `feat/margen-por-parcela`, donde estaba sin commitear y sin
  respaldo en git. **Sin revisar ni probar. No mergear sin revisar.** Toca
  `db.py`, `explotacion.py` y `auth.py`, así que al retomarlo habrá que resolver
  conflictos con esta feature.
- **PR #46** abierto (`feat/precios-2026`, precios con IVA incluido).
