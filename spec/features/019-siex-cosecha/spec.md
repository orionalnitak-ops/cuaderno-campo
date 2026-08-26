# 019 — Cosecha/venta: distinguir comercializada de directa (bloque 2/8 de compatibilidad SIEX)

Segundo bloque del ítem 002 del roadmap (ver `spec/constitution/roadmap.md`).
Fuente: hoja "Estructura Cuaderno" del Anexo VI, nodo `<cosecha_venta>`, filas
139-159.

## El problema

Hoy `cosecha` (`backend/db.py:868`) registra una única cosecha por parcela:
cultivo, variedad, superficie, producción total, destino, comprador, precio.
SIEX no modela "una cosecha", modela **una venta de un producto ya
cosechado**, y separa dos casos que la app hoy mezcla en un solo campo
`destino` de texto libre:

- `<comercializada>` (fila 142-154): venta a través de un cliente
  identificado — cooperativa, almacén, mayorista. Exige `nifCliente`,
  `nombre_o_RS`, `direccion`, `codProv`, `codMuni`, `lote` y `albaran`.
- `<directa>` (fila 152-155): venta directa (mercadillo, tienda de la
  finca...), sin cliente identificado — solo `cantidadVenta` y `unidad`.

La app de hoy tiene `comprador` (texto libre) y `precio_unidad`, que sirven
para ambos casos pero no permiten declarar **cuál de los dos es**, ni
capturan NIF/lote/albarán/dirección del cliente cuando es venta comercializada.

## Campos de brecha

| Campo SIEX | Fila | Obligat. | Tipo | Estado en la app |
|---|---|---|---|---|
| `codProducto` | 142 | 1 | catálogo | falta — ver "El catálogo" |
| `fecha` (venta) | 144 | 1 | date | falta (`fecha_inicio`/`fecha_fin` son de cosecha, no de venta) |
| tipo venta (comercializada/directa) | 145 | 0..1 | — | falta, no hay campo que distinga |
| `cantidadComerc` / `cantidadVenta` | 146, 156 | 0..1 | number(10,2) | cubierto por `produccion_total_valor` si se reutiliza |
| `albaran` | 147 | 0..1 | string(50) | falta |
| `lote` | 148 | 0..1 | — | falta |
| `nifCliente` | 149 | 0..1 | string(9) | falta (`comprador` es solo nombre libre) |
| `direccion`, `codProv`, `codMuni` del cliente | 151-153 | 0..1 | — | falta |

`codigo` (fila 141, asignado por SIEX tras subir la venta) se descarta igual
que en el bloque 018: la app no envía altas a SIEX.

## El catálogo: `codProducto`

`ctrl` dice "Validar contra el Catálogo", observación "CAT-??" — remite al
mismo catálogo `Producto Vegetal.xlsx` (693 filas: `Id`, `Código`,
`Producto`, `Código SIEX`, `Cultivo SIEX`) que usan también los bloques 023
(análisis) y 025 (post-cosecha). La columna `Cultivo SIEX` liga cada producto
a un nombre de cultivo — mismo patrón de cruce que variedad↔cultivo del
bloque 018, pero **693 filas, no 86.136**: no hace falta el mismo aparato de
tabla de referencia + búsqueda con límite de resultados. Basta importar las
693 filas a `ref_productos_siex` (mismo script `backend/tools/`, misma tabla
que reutilizan 019/023/025) y filtrar en el propio cliente por el cultivo ya
seleccionado — sin paginar, sin autocompletado remoto.

`codProv`/`codMuni` del cliente: la app ya guarda `provincia_cod`/
`municipio_cod` de origen INE en `parcelas` (ver `backend/helpers.py:214-216`,
alimentados desde SIGPAC). Son los mismos códigos INE que pide aquí SIEX
("Provincias según INE", "Municipios según INE", filas 152-153) — se reutiliza
el mismo selector de provincia/municipio ya existente en el alta de parcela,
no se construye uno nuevo.

## La regla

- Nueva columna `cosecha.fecha_venta` (nullable, `_add_col`) — la fecha de
  venta es distinta de `fecha_inicio`/`fecha_fin` de cosecha y no se puede
  derivar de ellas sin inventar un dato.
- Nueva columna `cosecha.tipo_venta` con dos valores: `comercializada` /
  `directa`. Determina qué subconjunto de campos pide el formulario.
- Nuevas columnas, todas nullable: `codigo_producto_siex` (INTEGER, del
  catálogo), `albaran` (TEXT), `lote` (TEXT), `nif_cliente` (TEXT),
  `nombre_cliente` (TEXT — puede que ya sirva para reemplazar `comprador`, a
  decidir en implementación si se funde o se mantienen los dos), `direccion_cliente`
  (TEXT), `provincia_cliente_cod` (TEXT), `municipio_cliente_cod` (TEXT).
- El formulario (`FormCosecha`, `frontend/screens_forms.jsx:1133`) añade un
  selector tipo venta que muestra/oculta los campos de cliente según
  `comercializada` o `directa`.
- Nada de esto bloquea el guardado: los campos SIEX son opcionales salvo
  `codProducto` y `fecha`, y aun esos se guardan en blanco si el agricultor no
  los rellena — igual que variedad en el bloque 018, la anotación nunca se
  bloquea por falta de un dato de catálogo.

## Criterios de aceptación

1. Registrar una venta marcándola "comercializada" pide NIF, nombre,
   dirección, provincia/municipio del cliente, lote y albarán (todos
   opcionales, pero visibles).
2. Registrar una venta marcándola "directa" no pide ninguno de esos campos.
3. Seleccionar un producto del catálogo (ej. "Aceitunas" para un cultivo de
   Olivo) guarda `codigo_producto_siex`; no seleccionar ninguno dejó
   `codigo_producto_siex = NULL` sin bloquear el guardado.
4. Los registros de cosecha ya existentes no se tocan: todas las columnas
   nuevas nacen `NULL`/vacías, `tipo_venta` incluido.
5. El PDF/Excel oficial (`export_pdf.py`, `exports.py`) sigue exportando lo
   que exportaba hoy sin romperse con los registros antiguos que no tienen
   `tipo_venta`.

## Qué no entra

- `codigo` de la venta asignado por SIEX: no se construye (mismo motivo que
  el bloque 018 — no hay envío por API).
- No se resuelve el cruce completo cultivo↔producto para los ~1.121 cultivos
  del catálogo `Cultivo.xlsx`, solo para los cultivos que ya están en
  `CULTIVOS_IACS` con `cod_siex` relleno por el bloque 018. Si el bloque 018
  no está desplegado antes que este, la relación producto↔cultivo del
  formulario no puede filtrar y hay que mostrar el catálogo completo (693
  filas) sin filtrar por cultivo — decisión de orden de despliegue, no de
  este spec.
- Migrar `comprador`/`destino` existentes a los campos nuevos: no hay
  backfill automático, igual que el criterio 4 de la variedad.
