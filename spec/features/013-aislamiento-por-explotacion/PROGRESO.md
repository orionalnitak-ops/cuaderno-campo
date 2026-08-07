# 013 — Progreso y handoff

**Rama:** `fix/aislamiento-explotacion` (base: `main` @ 384c459)
**Estado:** Fases 0-7 hechas + Fase 8 puntos 1-3 verificados sobre datos reales.
Solo queda que Lourdes lo confirme en la app (puntos 4 y 5). El bug que reportó Lourdes YA está arreglado.
**Última actualización:** 2026-08-07

Este archivo es el punto de entrada para retomar el trabajo en una sesión nueva.
Leer primero `spec.md` (qué y por qué) y `plan.md` (las 8 fases).

---

## Cómo verificar que todo sigue en pie

```bash
cd "H:\Proyectos\Cuaderno ex app\backend"
export PYTHONIOENCODING=utf-8   # sin esto, la consola de Windows (cp1252) rompe
                                # los tests que imprimen '↔'. No es fallo de lógica.
for t in test_cumplimiento test_asesores test_ia_patrones test_alta_multirecinto \
         test_user_id_not_null test_estado_sigpac test_aislamiento_explotacion \
         test_tablas_acotadas; do
  venv/Scripts/python.exe tests/$t.py >/dev/null 2>&1 && echo "$t PASA" || echo "$t FALLA"
done
```

Los 8 pasan a día de hoy. `test_aislamiento_explotacion.py` es el criterio de
"hecho" de la feature; `test_tablas_acotadas.py` es la red que evita que la
próxima tabla nazca con fuga.

---

## Hecho (8 commits)

| Commit | Fase | Qué |
|---|---|---|
| `dacea98` | 0 | Test en rojo del aislamiento + spec y plan |
| `8e855f2` | 1 | `explotacion_id` en 12 tablas, backfill idempotente, índices |
| `80584d3` | 2 | equipos, aplicadores, asesores, compras, UHC, labores, cosecha |
| `3996238` | 3 | tratamientos, fertilización, riego, abonado + referencias cruzadas |
| `4529433` | 4 | Revisión del cuaderno + bug silencioso de la campaña |
| `31c4652` | 5 | Alertas del Inicio, voz, cultivos de campaña e histórico |
| `1dfa976` | 6 | Test genérico de tablas acotadas + 3 fugas que destapó |
| `2219aec` | 7 | Frontend: campaña y cachés offline al cambiar de finca |

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
- **`parcela_scope_clause()` está marcado LEGADO**. Desde la Fase 5 solo lo usan
  `exports.py` y `export_pdf.py`; `explotacion.py` ya no. No usarlo en código
  nuevo (ver "Trampas" abajo). **Queda pendiente sacarlo también de los dos
  exports**: hasta entonces el PDF y el Excel siguen escondiendo los registros
  sin parcela. Las compras de esos dos ficheros SÍ se migraron ya
  (`explotacion_id` propio), porque no colgaban de parcela y el documento oficial
  listaba las facturas de todas las fincas.
- **`test_tablas_acotadas.py` analiza el código por FUNCIÓN**: si una consulta
  nueva no lleva el filtro, hay que acotarla o justificar la excepción por
  escrito en `EXCEPCIONES`. Hoy solo hay dos: `admin.py` (soporte) y `auth.py`
  (GDPR). La ruta de la BD en los tests es `db.DATABASE_NAME`, no `DB_PATH`:
  apuntar mal hace que el test corra contra la BD de desarrollo sin avisar.
- **`ia_patrones` lleva `explotacion_id` pero NO está en
  `TABLAS_POR_EXPLOTACION`**: es una caché que se regenera en cada POST, no un
  dato del agricultor, así que no lleva backfill (los patrones viejos quedan en
  NULL y dejan de casar, que es lo que se quiere). `ia_alertas` no lleva la
  columna: todas sus filas tienen `parcela_id`, y se acota por ahí.
- **`_recalcular_patrones(uid, modulo, parcela_id, fecha, explotacion_id)`**: el
  parámetro va al final, igual que en `evaluar_cumplimiento`. Hay que pasarlo
  siempre desde las rutas.
- **`cumplimiento.py`**: `evaluar_cumplimiento(conn, uid, hoy, campana, explotacion_id)`.
  El parámetro va al final para no romper llamadas antiguas. Dentro se compone
  `expl_sql`/`expl_par` y se concatena a las 11 consultas.

---

## Pendiente

### Fase 8 — Verificación con datos reales

**Ensayo hecho el 2026-08-07 sobre una copia real de producción. Resultado: limpio.**

Cómo se hizo (repetible): `tools/copia_datos.py` para el volcado,
`tools/restaurar_datos.py` para meterlo en una BD de ensayo, `init_db()` encima y
`tools/verificar_013.py antes|despues` para comparar.

```bash
cd "H:\Proyectos\Cuaderno ex app\backend"
export DB_PATH=ensayo_013.db PYTHONIOENCODING=utf-8   # BD aparte: no toca la de desarrollo
rm -f ensayo_013.db
venv/Scripts/python.exe -c "import db; db.init_db()"
venv/Scripts/python.exe tools/restaurar_datos.py "H:/Proyectos/_backups-cuaderno/cuaderno-datos-20260806-190052.json"
venv/Scripts/python.exe tools/verificar_013.py antes
venv/Scripts/python.exe -c "import db; db.init_db()"     # aplica migración y backfill
venv/Scripts/python.exe tools/verificar_013.py despues
```

- [x] **1. Copia de seguridad de producción.** Hecha el 2026-08-06
      (`cuaderno-datos-20260806-190052.json`, motor postgresql, 246 filas / 21
      tablas). Vive fuera del repo y lleva datos personales: no moverla dentro.
- [x] **2. Recuentos antes/después.** Los 13 idénticos, y **cero** filas con
      `explotacion_id` NULL tras el backfill.
- [x] **3. El "paso manual inevitable" resultó estar VACÍO.** No hay nada real
      que reasignar. Lo que el backfill dejó en la explotación por defecto son:
      los **3 equipos semilla** que crea `_seed_if_needed` sola al dar de alta la
      cuenta ("Pulverizador terrestre (completar marca y modelo)", "Mochila
      atomizadora (completar marca)", "Empresa externa / Contratado") y **4
      compras borradas** (`deleted_at` del 2026-08-06). Aplicadores y asesores
      del usuario 2: cero. Da igual en qué finca queden.
- [ ] **4.** Que Lourdes abra la Revisión con cada explotación y confirme que
      solo ve lo suyo.
- [ ] **5.** Que cambie de finca en el selector y confirme que la campaña y las
      listas cambian con ella. La Fase 7 se verificó leyendo el código y
      compilando, **no ejecutando la app**.

**Límite del ensayo, no olvidarlo:** corre sobre SQLite. Valida la LÓGICA del
backfill, que es donde estaba el riesgo de perder datos, pero **no** las rutas
específicas de PostgreSQL (`_add_col` con ALTER, `_harden_user_id_postgres`,
`_enable_rls_postgres`). Eso solo se prueba desplegando — de ahí que el punto 1
no sea opcional.

**Mapa de explotaciones del usuario 2** (66 parcelas en 6 fincas), útil para el
punto 4: [12] Lourdes de Lamo Valencia · 11 · [14] Daniel de Lamo Laguna · 27 ·
[13] Juani · 14 · [15] José Luis · 6 · [17] Emilio · 6 · [16] Lourdes de Lamo · 2.

---

## Decisión pendiente de Raúl — los registros creados sin cobertura

`pending_records` guarda lo que se anota en el campo sin cobertura, pero **no
guarda a qué explotación pertenece**: al sincronizar, el servidor lo escribe en
la que esté activa en ESE momento.

Hoy el riesgo es estrecho, no nulo: cambiar de finca exige llamar al servidor, o
sea que sin cobertura no se puede cambiar, y la sincronización salta sola al
recuperarla. La ventana es cambiar de finca entre que vuelve la cobertura y que
termina de sincronizar. Si pasa, el registro se guarda en la finca equivocada y
en un cuaderno legal eso es un dato falso, no una molestia.

Arreglarlo bien pide que el registro pendiente viaje con su `explotacion_id` y
que el POST lo acepte validando que es del usuario — es decir, tocar la frontera
de seguridad. **No se ha hecho en esta feature**: no estaba en el plan y merece
su propia decisión. Queda anotado aquí para que no se pierda.

---

## Trampas encontradas (no volver a pisarlas)

1. **`parcela_scope_clause()` oculta registros.** `parcela_id` es nullable en
   tratamientos, fertilizacion, labores, riego, cosecha y abonado, y
   `parcela_id IN (…)` descarta los NULL. Es decir: hoy el histórico y las
   estadísticas ya esconden los registros sin parcela, en todas las
   explotaciones. **Al migrar a `explotacion_id` esos registros REAPARECEN.**
   → **COMPROBADO el 2026-08-07 sobre los datos reales: hay CERO registros con
   `parcela_id` NULL en las seis tablas. No reaparece nada y NO hay que avisar a
   Lourdes.** El riesgo sigue siendo real para otro agricultor con datos así, pero
   con los datos de hoy no se materializa.
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
8. **Al cambiar de finca no basta con remontar las pantallas.** El `key={explKey}`
   de `app.jsx` ya lo hacía, pero quedaban dos cosas fuera de React: la campaña
   activa (es de la explotación, y seguía siendo la de la finca vieja en filtros
   y exportaciones) y las cachés de IndexedDB, que guardan datos de UNA finca sin
   decir de cuál. Sin vaciarlas, al quedarse sin cobertura en la finca nueva la
   app enseñaba las parcelas y los equipos de la anterior. **`pending_records` NO
   se toca**: son registros del agricultor sin sincronizar.
9. **El Service Worker no cachea `/api/`** (`service-worker.js:63`), así que por
   ahí no se cuelan datos de otra finca. Sí cachea `offline-db.js` y `app.js`, de
   modo que tocarlos obliga a subir `CACHE_NAME` (v49 → v50).
10. **`parcela_es_del_usuario()` está duplicada** en `tratamientos.py` y
   `fertilizacion.py`. Se mantienen las dos a propósito (unificarlas crea un
   import cruzado entre los dos módulos más grandes). Si se toca una, tocar la otra.

---

## Para el PR

- Rama `fix/aislamiento-explotacion` → PR a `main`. Nunca push directo.
- CI: lint + bandit. Cada PR recibe Security Review de Claude.
- **Antes de abrir el PR:** la Fase 8.2 (recuentos antes/después con datos
  reales). La Fase 6 ya está: `test_tablas_acotadas.py` es la garantía de que no
  queda ninguna fuga.
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
