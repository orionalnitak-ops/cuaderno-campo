# 021 — Fertilización: catálogo de material, tipo/método y asesor (bloque 4/8 de compatibilidad SIEX)

Cuarto bloque del ítem 002 (ver `spec/constitution/roadmap.md`). Fuente: hoja
"Estructura Cuaderno", nodo `<fertilizacion>`, filas 97-122.

## El problema

`fertilizacion` (`backend/db.py:737`) guarda: fecha de aplicación,
`tipo_fertilizante` y `producto` (texto libre), `riqueza_npk` (texto tipo
"15-15-15" o "46%N", parseado por `_calc_npk` en
`backend/blueprints/fertilizacion.py:62-109` a `n_aplicado`/`p2o5_aplicado`/
`k2o_aplicado`), dosis, densidad (para líquidos) y método de aplicación
(texto libre). Once campos de SIEX no tienen equivalente:

| Campo SIEX | Fila | Obligat. | Tipo | Estado en la app |
|---|---|---|---|---|
| `fecActuacion` (fecha de enterrado) | 99 | 0..1 | date | falta — distinto de `fecha_aplicacion` |
| `declBuenPrac` | 100 | 0..1 | boolean | falta |
| `buenPrac` | 101 | 0..1 | catálogo (ámbito "Fertilización") | falta |
| `codFertiliz` | 103 | **1** | catálogo, 25 valores | `tipo_fertilizante` es texto libre, sin código |
| `carbono` (% Carbono Orgánico) | 108 | 0..1 | number(5,2) | falta — `riqueza_npk` cubre N/P/K, no carbono |
| `albaran` | 110 | 0..1 | string(50) | falta |
| `unidad` (de `cantidad`) | 112 | 0..1 | catálogo | `dosis_unidad` es texto libre ("kg/ha"), sin código |
| `tipo` (de fertilización) | 113 | 0..1 | catálogo, 3 valores | falta — distinto de `tipo_fertilizante` |
| `metodo` | 114 | **1** | catálogo, 7 valores | `metodo_aplicacion` es texto libre, sin código |
| `asesorFerti` (numRegistro, docIdent, nombre, fecha) | 117-121 | 0..1 | — | falta por completo — no hay ningún asesor en fertilización |

`codigo` (fila 98, asignado por SIEX) se descarta, mismo motivo de siempre.
`planAbon` (fila 116) se descarta también, pero por un motivo distinto: el
propio Anexo VI lo marca "Propuesta de SGMPA para incluir en el contenido
mínimo. **PENDIENTE CONFIRMAR**" — ni SIEX tiene cerrado si va o no. No se
construye nada para un campo que la propia especificación oficial no ha
cerrado todavía.

## El catálogo: `codFertiliz`

`Material fertilizante.xlsx` — **25 filas**, categorías amplias (0=Otros,
1=Estiércol líquido de aves, 2=Estiércol líquido de bovino... hasta abonos
minerales). Es un catálogo pequeño: un `<select>` de 25 opciones basta, sin
tabla de referencia ni endpoint. (No confundir con `Detalle material
fertilizante.xlsx`, 1.244 filas de productos comerciales concretos —el
Anexo VI no referencia esa hoja para `codFertiliz`, solo "Hoja Materia
Fertilizacion"; ese catálogo grande queda fuera de este bloque.)

Los otros tres catálogos de este bloque son igual de pequeños:
**Tipo de fertilización** (3 filas: Abonado de fondo / de cobertera /
Aplicación de enmienda), **Método de fertilización** (7 filas: esparcido
general, esparcido y enterrado, localizado, foliar, fertirrigación...) y
**Buenas prácticas** filtradas a ámbito "Fertilización" (mismo catálogo
compartido del bloque 020, ~30 de sus 98 filas).

## El asesor de fertilización: concepto nuevo, reutiliza `asesores`

SIEX pide un asesor específico de fertilización (`numRegistro`, `docIdent`,
`nombre_o_RS`, `fecha` de asesoramiento). La app **ya tiene** la tabla
`asesores` (`backend/db.py:669-683`, feature 010) y ya la reutiliza en
tratamientos vía `tratamientos.asesor_id` (`backend/db.py:731`). Este bloque
repite el mismo patrón sobre fertilización: no se crea una tabla de asesores
nueva, se añade una columna `asesor_id` (FK a `asesores`) más
`fecha_asesoramiento` a la tabla `fertilizacion`.

## La regla

- Nuevas columnas nullable en `fertilizacion` (`_add_col`): `fecha_enterrado`
  (TEXT), `decl_buenas_practicas` (boolean), `buena_practica_cod` (INTEGER),
  `material_fertilizante_cod` (INTEGER, del catálogo de 25), `carbono_pct`
  (REAL), `albaran` (TEXT), `unidad_cod` (INTEGER), `tipo_fertilizacion_cod`
  (INTEGER, catálogo de 3), `metodo_cod` (INTEGER, catálogo de 7),
  `asesor_id` (INTEGER, FK `asesores`), `fecha_asesoramiento` (TEXT).
- `tipo_fertilizante`, `producto` y `metodo_aplicacion` (texto libre) no se
  tocan — conviven con los códigos nuevos igual que en tratamientos.
- El formulario (`FormFertilizacion`, `frontend/screens_forms.jsx:699`)
  reutiliza el mismo patrón de selector de asesor que ya existe en
  `FormTratamiento` (líneas 299-301, 361-370, 434+): fetch a `/api/asesores`,
  opción de alta rápida inline.

## Criterios de aceptación

1. Elegir un material fertilizante del catálogo de 25 opciones guarda
   `material_fertilizante_cod`; `tipo_fertilizante` de texto libre sigue
   funcionando si no se usa el desplegable.
2. Asignar un asesor de fertilización desde el mismo selector que ya usa
   tratamientos (mismo endpoint `/api/asesores`) guarda `asesor_id` y
   `fecha_asesoramiento` en el registro de fertilización.
3. Los registros ya existentes no se tocan: todas las columnas nuevas nacen
   `NULL`.
4. Marcar "sí" en buenas prácticas ofrece solo las de ámbito Fertilización.
5. `planAbon` no aparece en ningún sitio del formulario ni de la BD.

## Qué no entra

- `codigo` de la fertilización asignado por SIEX: no se construye.
- `planAbon`: pendiente de que el propio SIEX lo confirme; no se implementa
  nada mientras la especificación oficial lo marque como no cerrado.
- No se toca `Detalle material fertilizante.xlsx` (1.244 filas de productos
  comerciales) — el catálogo de 25 filas de `Material fertilizante.xlsx` es
  el que pide el campo `codFertiliz` según el propio Anexo VI.
- No se crea una segunda tabla de asesores para fertilización: se reutiliza
  `asesores` completa, tal cual existe hoy.
