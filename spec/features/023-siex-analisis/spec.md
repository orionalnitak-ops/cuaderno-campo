# 023 — Análisis de suelo/agua/producto: módulo nuevo (bloque 6/8 de compatibilidad SIEX)

Sexto bloque del ítem 002 (ver `spec/constitution/roadmap.md`). Primero de
los tres módulos completamente nuevos. Fuente: hoja "Estructura Cuaderno",
dos nodos `<analisis>` — uno colgado de `<cultivo>` (filas 157-168, analiza
el cultivo o su producto cosechado) y otro colgado de `<recinto>` (filas
171-181, analiza suelo o agua). Comparten casi todos los campos.

## El problema

Hoy no existe ninguna tabla, endpoint ni pantalla para análisis de ningún
tipo (suelo, agua o producto). Es un módulo entero por construir, no una
columna que falta.

## Los 9 campos (unificando los dos nodos)

| Campo SIEX | Fila | Obligat. | Tipo | Catálogo |
|---|---|---|---|---|
| `material` | 159, 173 | **1** | number(1) | `Material analizado.xlsx` (4 filas: 1=Cultivo, 2=Producto cosechado, 3=Suelo, 4=Agua de riego) |
| `codProdVegetal` | 160 | 0..1, solo si `material` indica producto | number(4) | `Producto Vegetal.xlsx` (693 filas, mismo catálogo que el bloque 019) |
| `fecha` | 161, 174 | **1** | date | — |
| `rsLaborat` | 162, 175 | 0..1 | string(150) | — |
| `direccion` (laboratorio) | 163, 176 | 0..1 | string(150) | — |
| `codProv` (laboratorio) | 164, 177 | 0..1 | number(2) | INE, mismo patrón que `parcelas.provincia_cod` |
| `codMuni` (laboratorio) | 165, 178 | 0..1 | number(3) | INE, mismo patrón que `parcelas.municipio_cod` |
| `numBoletin` | 166, 179 | 0..1 | string(50) | — |
| `tipo` (de análisis) | 167, 180 | 0..1 | number(1) | `Tipo de análisis.xlsx` (6 filas: residuos fito, microbiológico, metales pesados, nutrientes, parámetros del suelo, presencia OMG) |

`codigo` (fila 158, 172, asignado por SIEX) se descarta, mismo motivo de
siempre. Ojo: el Anexo VI dice para el `<analisis>` de cultivo que `material`
"Solo valores 0 y 1" (fila 162, observación), pero el propio catálogo
`Material analizado.xlsx` no tiene un valor `0` — sus 4 filas van de 1 a 4.
Es una inconsistencia del documento oficial, no de la app: se sigue el
catálogo real (1-4), no la nota de la fila 162.

## Los catálogos

Los tres pequeños (`Material analizado`, 4 filas; `Tipo de análisis`, 6
filas) son `<select>` directos. `Producto Vegetal` (693 filas) reutiliza
exactamente la tabla de referencia `ref_productos_siex` que ya construye el
bloque 019 — no se importa dos veces, es la misma tabla y el mismo filtro
por cultivo.

`codProv`/`codMuni` del laboratorio: mismo patrón ya usado en el bloque 019
para la dirección del cliente — reutiliza el selector provincia/municipio
INE que ya existe en el alta de parcela, sin catálogo nuevo.

## La regla

- Nueva tabla `analisis` (patrón de `backend/blueprints/fertilizacion.py`
  como referencia de blueprint simple): `id`, `user_id NOT NULL`,
  `explotacion_id`, `parcela_id` (nullable — un análisis de suelo/agua es del
  recinto, uno de producto es del cultivo dentro de la parcela; ambos casos
  cuelgan de una parcela igual que el resto de módulos), `material_cod`
  (INTEGER, catálogo de 4), `codigo_producto_siex` (INTEGER, nullable, solo
  si `material_cod` es Cultivo o Producto cosechado), `fecha` (TEXT),
  `rs_laboratorio` (TEXT), `direccion_laboratorio` (TEXT),
  `provincia_laboratorio_cod` (TEXT), `municipio_laboratorio_cod` (TEXT),
  `num_boletin` (TEXT), `tipo_analisis_cod` (INTEGER, catálogo de 6),
  `notas` (TEXT), `campana` (TEXT DEFAULT '2025/2026'), `created_at`,
  `updated_at`, `deleted_at` (soft delete, mismo patrón que `tratamientos`).
- Nuevo blueprint `backend/blueprints/analisis.py`: `GET/POST /api/analisis`,
  `GET/PUT/DELETE /api/analisis/<id>`. Mismo patrón de validación de
  pertenencia (`parcela_es_del_usuario`) y aislamiento por
  `explotacion_id` que ya siguen fertilización y riego.
- Nueva pantalla de formulario en `frontend/screens_forms.jsx`
  (`FormAnalisis`), siguiendo el patrón de `FormRiego`/`FormFertilizacion`:
  selector de parcela o grupo UHC, selector de material, condicional al
  producto si aplica, catálogo de tipo de análisis, y los campos de
  laboratorio en texto libre + selector provincia/municipio.
- Añadir la entrada en `HELP_SCREENS` de `screens_ayuda.jsx` (regla del
  proyecto: toda feature de UI nueva actualiza la ayuda en el mismo PR).

## Criterios de aceptación

1. Se puede registrar un análisis de suelo sin cultivo asociado (solo
   parcela, material="Suelo").
2. Se puede registrar un análisis de producto cosechado, con el producto
   elegido del mismo catálogo que usa el bloque 019.
3. El listado de análisis se filtra por `user_id` y `explotacion_id`, igual
   que el resto de módulos (aislamiento por finca).
4. El PDF/Excel oficial no necesita incluir este módulo en esta fase —
   añadirlo a la exportación es una tarea aparte, no un criterio de este spec.
5. Falta cualquier campo de laboratorio y el registro se guarda igual —
   solo `material` y `fecha` son obligatorios.

## Qué no entra

- `codigo` del análisis asignado por SIEX: no se construye.
- No se añade este módulo a `export_pdf.py`/`exports.py` en este spec —
  llegado el momento de exportar oficialmente, es una tarea de exportación,
  no de captura de datos.
- No se resuelve el cruce cultivo↔producto para cultivos fuera de
  `CULTIVOS_IACS` (misma limitación que el bloque 019).
- No se corrige la inconsistencia del Anexo VI sobre `material` "0,1" vs el
  catálogo real 1-4 — se sigue el catálogo, se documenta aquí y punto.
