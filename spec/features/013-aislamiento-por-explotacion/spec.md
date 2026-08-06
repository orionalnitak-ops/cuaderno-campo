# 013 — Aislamiento por explotación

**Estado:** propuesta, pendiente de aprobar
**Origen:** reporte de Lourdes (2026-08-06) sobre la Revisión del cuaderno
**Prioridad:** decidir contra Stripe Live (ver "Coste y riesgo")

---

## El problema

Reporte literal de Lourdes:

> "Cuando tengo seleccionada una explotación, si me voy a ajustes para ver la
> revisión de cuaderno, me salen las partes faltantes de todas las
> explotaciones, cuando sólo debería salir la que tengo seleccionada."

La Revisión del cuaderno es el síntoma que ella vio, pero no es el bug. Auditado
el backend, la fuga es sistémica: **9 blueprints consultan datos del agricultor
filtrando solo por `user_id`, sin acotar nunca por la explotación activa.**

Acotan hoy correctamente: `parcelas.py`, `sigpac.py`, `explotacion.py`,
`imports_exports.py` (y `exports.py` / `export_pdf.py`, vía
`parcela_scope_clause()`).

NO acotan: `tratamientos.py`, `fertilizacion.py`, `labores.py`, `compras.py`,
`equipos.py`, `asesores.py`, `uhc.py`, `ia.py`, `cumplimiento.py`.

Consecuencia para el usuario: los listados de cada módulo, las alertas del
Inicio y la Revisión del cuaderno mezclan las fincas. Con 50+ parcelas
repartidas en varias explotaciones, la pantalla es inservible.

Matiz, verificado al escribir el plan: `/api/historial` y `/api/stats` **sí**
acotan ya con `parcela_scope_clause()`. Del histórico solo se fuga **compras**,
por una decisión explícita que dejó el comentario de `explotacion.py:281`
("no se acota por explotación en Fase 1"). Esta feature es esa Fase 2.

### Dos bugs concretos ya localizados en `cumplimiento.py`

1. `evaluar_cumplimiento()` (línea 204) no recibe ni consulta la explotación
   activa. `SELECT ... FROM parcelas WHERE user_id=? AND activa=1` (221-222)
   trae las parcelas de todas las explotaciones, y de ahí salen los bloques
   "Cultivo declarado", "Plazos de seguridad" y "Sin movimiento reciente".
2. Línea 217: `one(conn, "SELECT campana_activa FROM explotacion WHERE user_id=?")`
   devuelve una fila **arbitraria** cuando hay varias explotaciones. La revisión
   puede estar evaluándose contra la campaña de la finca equivocada, en silencio.

---

## Decisión de producto (Raúl, 2026-08-06)

**Cada explotación se comporta como un cuaderno totalmente independiente.** El
usuario con más de una explotación es un "asesor" que gestiona cuadernos
separados: cada explotación tiene sus parcelas, sus tratamientos, sus equipos,
sus facturas, sus aplicadores y sus asesores. Nada se comparte entre ellas.

Esto descarta la alternativa de dejar equipos / personas / compras como
entidades comunes al usuario, que era el comportamiento implícito del esquema
actual.

---

## Alcance

### Tablas y su situación

| Tabla | Tiene `explotacion_id` | Tiene `parcela_id` |
|---|---|---|
| `parcelas` | ✅ sí | — |
| `tratamientos` | ❌ | sí (nullable) |
| `fertilizacion` | ❌ | sí (nullable) |
| `labores` | ❌ | sí (nullable) |
| `riego` | ❌ | sí (nullable) |
| `cosecha` | ❌ | sí (nullable) |
| `cultivos_campana` | ❌ | sí (NOT NULL) |
| `compras` | ❌ | ❌ |
| `equipos` | ❌ | ❌ |
| `aplicadores` | ❌ | ❌ |
| `asesores` | ❌ | ❌ |
| `unidades_homogeneas` | ❌ | ❌ (vía `uhc_parcelas`) |

### Por qué NO basta con `parcela_scope_clause()`

Tentador reutilizar el helper que ya existe en `db.py` y acotar las 6 tablas que
tienen `parcela_id` sin migración alguna. No sirve como solución completa:

- `parcela_id` es **nullable** en 5 de esas 6 tablas. `parcela_id IN (SELECT …)`
  descarta las filas con NULL, así que un tratamiento sin parcela asignada
  desaparecería de **todas** las explotaciones. Perder registros de la vista es
  peor que mezclarlos: en un cuaderno legal, un dato que no se ve es un dato que
  el agricultor cree que no anotó.
- `compras`, `equipos`, `aplicadores`, `asesores` y `unidades_homogeneas` no
  tienen `parcela_id`, así que necesitan columna nueva de todas formas.

Decisión: **una sola regla para todo**, `explotacion_id` en las 11 tablas. Un
único criterio es más simple de razonar y de auditar que dos mecanismos
distintos según la tabla (principios.md: simplicidad sobre elegancia).

`parcela_scope_clause()` se mantiene para no romper `exports.py` /
`export_pdf.py`, y se marca como legado en su docstring.

---

## Criterios de aceptación

1. Con la explotación A seleccionada, la Revisión del cuaderno **no** menciona
   ninguna parcela, equipo, producto, factura ni persona que pertenezca solo a
   la explotación B.
2. El porcentaje y el color del semáforo se calculan solo con los datos de la
   explotación activa.
3. La campaña que usa la Revisión es la `campana_activa` de la **explotación
   activa**, no la de una fila arbitraria.
4. El histórico (`/api/tratamientos`, `/api/fertilizacion`, `/api/labores`,
   `/api/riego`, `/api/cosecha`) devuelve solo registros de la explotación
   activa.
5. Las alertas del Inicio (`ia.py`) solo hablan de la explotación activa.
6. Los listados de equipos, aplicadores, asesores, compras y UHC solo muestran
   los de la explotación activa.
7. Todo `INSERT` de estas tablas escribe la `explotacion_id` activa. Un INSERT
   que la olvide debe fallar, no escribir en la finca equivocada.
8. Ningún registro existente se queda invisible tras la migración: todo lo que
   hoy ve Lourdes sigue viéndose, en la explotación que le corresponde.
9. Cambiar de explotación en el selector refresca todas estas pantallas sin
   necesidad de recargar la app.
10. El usuario mono-explotación (la mayoría) no percibe ningún cambio.

### Regla de aislamiento (no negociable, al nivel de la regla de `user_id`)

Toda tabla con datos de agricultor filtra **`user_id` Y `explotacion_id`**. El
`user_id` sigue siendo la frontera entre clientes; la `explotacion_id` es la
frontera entre cuadernos del mismo cliente. Quitar el primero es una brecha de
seguridad; quitar el segundo es un cuaderno legal con datos de otra finca.

---

## Migración de datos

`explotacion_id` se añade con `_add_col()` en `init_db()`, nunca con `ALTER
TABLE` en frío (CLAUDE.md).

Backfill, idempotente, siguiendo el patrón que ya existe en
`_backfill_parcelas_explotacion()` (db.py:908):

1. Donde la fila tenga `parcela_id`, heredar la `explotacion_id` de esa parcela.
   Es el dato real, no una suposición.
2. Donde no la tenga (o sea NULL), asignar la explotación por defecto del
   usuario (`resolve_default_explotacion()`).
3. Registrar por `logger.error` cualquier fila que quede con `explotacion_id`
   NULL, con tabla y recuento, para revisarla a mano. No forzar `NOT NULL` sobre
   una tabla con huérfanos — mismo criterio que `_harden_user_id_postgres()`.

Consecuencia asumida: en una cuenta multi-explotación ya existente, los equipos
y las facturas caen todos en la explotación por defecto y habrá que reasignar a
mano los que pertenezcan a otra finca. Es inevitable: el dato de a qué finca
pertenecía un equipo nunca se guardó. Afecta hoy solo a la cuenta de Lourdes.

---

## Fuera de alcance

- Compartir un equipo o un aplicador entre dos explotaciones. Descartado por la
  decisión de producto: cuadernos independientes.
- Copiar o mover registros entre explotaciones desde la UI.
- Panel de "asesor" con vista agregada de varias fincas a la vez.
- Cualquier cambio en la exportación Excel/PDF, que ya acota bien.

---

## Coste y riesgo

Esto no es un bugfix. Son ~79 puntos de consulta en 9 blueprints, 11 tablas con
columna nueva, una migración con backfill y los formularios que envían los
INSERT. **Retrasa Stripe Live.**

Riesgo principal: cada query que se toque es una oportunidad de introducir una
fuga o de hacer desaparecer registros. Mitigación obligatoria: un test que
enumere las tablas afectadas y verifique, tabla por tabla, que dos explotaciones
del mismo usuario no se ven entre sí — que falle solo si se añade una tabla y se
olvida el filtro.

Alternativa más barata si se decide no abordarlo entero ahora: arreglar solo
`cumplimiento.py` acotando los 3 bloques basados en parcela y corrigiendo el bug
de la campaña. Tapa lo que Lourdes reportó (~1 h de trabajo) pero deja el
histórico y el Inicio mezclando fincas.
