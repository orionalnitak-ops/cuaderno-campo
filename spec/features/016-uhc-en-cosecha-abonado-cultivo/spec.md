# 016 — Grupos UHC en Cosecha, Plan de abonado y Cultivo campaña

**Estado:** aprobada · **Origen:** reporte de **Lourdes** (piloto), 2026-08-08

> Lo pide Lourdes desde el uso real con sus 50+ parcelas. Por la regla establecida, lo que
> reporta el piloto va aprobado por defecto. La decisión de producto que sí tomó Raúl es el
> **reparto proporcional por superficie** en Cosecha (opción A de tres).

---

## El problema

El toggle **📍 Parcela / 🌱 Grupo UHC** (`ParcelOrUhcSelect`, `frontend/screens_forms.jsx:222`)
está en 4 de los 7 formularios que llevan parcela:

| Formulario | ¿Tiene el toggle? |
|---|---|
| Tratamiento | ✅ |
| Fertilización | ✅ |
| Labor | ✅ |
| Riego | ✅ |
| **Cosecha** | ❌ |
| **Plan de abonado** | ❌ |
| **Cultivo campaña** | ❌ |
| Compras/ventas | — (no lleva parcela, correcto) |

Con 50+ parcelas, que tres módulos obliguen a repetir el mismo registro parcela por parcela
es justo el trabajo que la UHC existe para evitar.

## Cómo funciona hoy la UHC (no se cambia)

El `uhc_id` **no se guarda en el registro**. El backend expande el grupo y crea **una fila
por parcela** (`blueprints/tratamientos.py:240`). El grupo es un atajo de entrada; el
cuaderno legal sigue siendo por parcela. Esta feature copia ese patrón, no lo toca.

## Qué se hace en cada módulo

### 1. Plan de abonado — copia directa

Todos sus campos son **por hectárea** (`n_necesario_kg_ha`, `p_`, `k_`,
`dosis_recomendada_kg_ha`, `rendimiento_esperado_kg_ha`). Replicar el mismo valor en todas
las parcelas del grupo es correcto. Se copia el patrón de Fertilización tal cual.

### 2. Cosecha — reparto proporcional (decisión de Raúl, opción A)

`produccion_total_valor` y `superficie_cosechada_ha` son **totales absolutos**, no por
hectárea. Replicarlos multiplicaría la cosecha por el nº de parcelas: dato falso en un
documento legal.

Regla acordada:

- La **superficie cosechada** de cada parcela se rellena con la superficie real de esa
  parcela (`parcelas.superficie_ha`), no se reparte nada inventado.
- La **producción total** del grupo se reparte **proporcionalmente a la superficie** de
  cada parcela. La última parcela absorbe el redondeo, para que la suma de las filas sea
  exactamente el total tecleado.
- La UI **dice que es un reparto estimado** antes de guardar, y muestra el desglose
  parcela → kg. Nada se guarda sin que el agricultor vea ese reparto.
- El resto de campos (fechas, cultivo, variedad, destino, comprador, precio, notas) se
  replican igual en todas.
- `rendimiento_kg_ha` lo sigue calculando el backend por fila; al repartir por superficie
  sale el mismo en todas, que es lo coherente con un grupo homogéneo.

**Plazo de seguridad:** el POST de cosecha ya bloquea si hay un tratamiento con
`fecha_recoleccion_minima` sin vencer en esa parcela (`blueprints/labores.py:162`). Con un
grupo, si **una sola** parcela tiene el plazo vivo, **se rechaza el grupo entero** y se
nombran las parcelas afectadas. No se guarda "las que se puede y las que no": cosechar en
plazo de seguridad es una infracción, y un guardado parcial silencioso es peor que un error.

### 3. Cultivo campaña — reparto proporcional y cultivo precargado

`superficie_cultivada_ha` y `kg_sembrados` son absolutos. Misma regla:

- La **superficie cultivada** de cada parcela se propone igual a la superficie de esa
  parcela (mismo criterio que la feature 015, criterio 8), editable.
- **`kg_sembrados`**, si se rellena, se reparte proporcional a la superficie.
- El **cultivo del grupo** (`unidades_homogeneas.cultivo`) precarga el campo cultivo: una
  UHC ya es, por definición, un conjunto de parcelas del mismo cultivo. El código IACS
  sigue siendo obligatorio y se pide una vez para el grupo.
- **Nunca pisa una declaración existente**: si una parcela del grupo ya tiene ese cultivo
  declarado en la campaña, se salta y se dice cuántas se saltaron (mismo criterio que la
  015).
- La validación de superficie que ya existe (`blueprints/parcelas.py:341`) sigue aplicando
  por parcela; si alguna la incumple, se rechaza esa parcela con su motivo, no el grupo
  entero — aquí sí, porque no hay riesgo legal en declarar de menos.

## Criterios de aceptación

1. Los tres formularios muestran el mismo toggle 📍 Parcela / 🌱 Grupo UHC que los otros
   cuatro. Idéntico componente, sin variantes visuales.
2. Guardar con un grupo crea **una fila por parcela** del grupo, como en Tratamientos.
3. En Cosecha, la suma de `produccion_total_valor` de las filas creadas es **exactamente**
   el total que tecleó el agricultor. Sin céntimos perdidos por redondeo.
4. En Cosecha, antes de guardar se ve el desglose parcela → cantidad, con aviso explícito
   de que es un reparto por superficie.
5. Una parcela del grupo con plazo de seguridad vivo **rechaza el grupo entero** y nombra
   las parcelas afectadas.
6. En Cultivo campaña, las parcelas ya declaradas se saltan sin error y se informa cuántas.
7. Todo respeta el aislamiento por explotación (feature 013): el grupo y sus parcelas se
   comprueban contra `explotacion_id` en la misma consulta, como en `tratamientos.py:245`.
8. Si el grupo no tiene parcelas asignadas, error claro y no se escribe nada.
9. Sin grupos UHC creados, el toggle sigue apareciendo y el modo grupo explica cómo crear
   uno — comportamiento actual del componente, no se cambia.

## Fuera de alcance

- Guardar `uhc_id` en los registros. Se mantiene el fan-out.
- Tocar los 4 formularios que ya lo tienen.
- Compras/ventas: no lleva parcela.
- Editar un registro creado desde un grupo: se sigue editando parcela a parcela, como hoy
  en Tratamientos.
- Repartir por cualquier criterio que no sea la superficie (producción histórica,
  rendimiento por parcela). Si algún día hace falta, es otra feature.

## Riesgo asumido

El reparto por superficie es una **estimación**, no una medición. Es exactamente lo que el
agricultor haría a mano con un grupo homogéneo, y por eso se acepta — pero se le dice en
pantalla, y quien quiera el dato exacto sigue teniendo el modo parcela a parcela.
