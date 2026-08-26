# 024 — Tratamiento de semillas: módulo nuevo (bloque 7/8 de compatibilidad SIEX)

Séptimo bloque del ítem 002 (ver `spec/constitution/roadmap.md`). Segundo de
los tres módulos completamente nuevos. Fuente: hoja "Estructura Cuaderno",
nodo `<semillaTrat>`, filas 65-79.

## El problema

Hoy no existe ninguna tabla ni pantalla para registrar el tratamiento de
semilla antes de la siembra (desinfección, tratamiento fungicida de la
semilla...). El RD 1311/2012 obliga a anotarlo cuando el tratamiento se
hace en la propia explotación, y SIEX lo modela como un bloque propio
colgado del recinto, distinto de `<actFito>` (bloque 022) aunque comparte
el mismo sub-bloque `<ASPAFITOS>`.

## Los 11 campos

| Campo SIEX | Fila | Obligat. | Tipo | Catálogo |
|---|---|---|---|---|
| `supTratada` | 67 | **1** | number(8,2) | — |
| `tratamiento` | 68 | **1** | number(1) | `Tratamiento semilla.xlsx` (4 filas: 2=Realizado en la explotación, 3=Realizado en centro de acondicionamiento, 4=Adquirida tratada en España, 5=Adquirida tratada fuera de España) |
| `fecActuacion` | 69 | **1** | date | — |
| `cantidad` | 70 | 0..1 | number(8,2) | — |
| `unidad` | 71 | 0..1 | number(1) | `Unidades de medida.xlsx` (82 filas, catálogo genérico ya usado en varios bloques) |
| `eficacia` | 72 | 0..1 | number(1) | `Eficacia del tratamiento.xlsx` (3 filas: Buena/Regular/Mala) |
| `observaciones` | 73 | 0..1 | string(150) | — |
| `nomComProd` (ASPAFITOS) | 75 | 0..1 | string(50) | — texto libre, se trae de ASPAFITOS |
| `numRegistro` (ASPAFITOS) | 76 | **1** | string(50) | — texto libre, se trae de ASPAFITOS |
| `sustAct` (ASPAFITOS) | 77 | 0..1 | string(200) | — texto libre, se trae de ASPAFITOS |

`codigo` (fila 66, asignado por SIEX) se descarta, mismo motivo de siempre.

Nótese que `tratamiento` empieza en código `2`, no en `1` — el catálogo real
no tiene una fila `1` (verificado, `Tratamiento semilla.xlsx` solo tiene
filas 2 a 5). No es un error de importación: así viene el catálogo oficial.

## Los tres campos `ASPAFITOS`: mismo patrón que tratamientos, sin catálogo

`nomComProd`/`numRegistro`/`sustAct` son idénticos en forma a los que ya
tiene `tratamientos.producto_comercial`/`num_registro_mapa`/
`sustancia_activa` (`backend/db.py:693-695`) — texto libre, sin catálogo, tal
como ya funciona ese bloque hoy (el nombre comercial y sustancia activa no
se validan contra catálogo en ningún sitio de la app actual). Se replica el
mismo patrón, no se inventa uno nuevo.

## La regla

- Nueva tabla `tratamiento_semillas` (patrón de blueprint simple,
  `backend/blueprints/fertilizacion.py`): `id`, `user_id NOT NULL`,
  `explotacion_id`, `parcela_id`, `parcela_etiqueta`,
  `superficie_tratada_ha` (REAL, obligatorio en el formulario),
  `tratamiento_cod` (INTEGER, catálogo de 4, obligatorio),
  `fecha_actuacion` (TEXT, obligatorio), `cantidad` (REAL), `unidad_cod`
  (INTEGER), `eficacia_cod` (INTEGER, catálogo de 3), `observaciones` (TEXT),
  `producto_comercial` (TEXT), `num_registro_mapa` (TEXT, obligatorio si se
  informa un producto), `sustancia_activa` (TEXT), `campana` (TEXT DEFAULT
  '2025/2026'), `created_at`, `updated_at`, `deleted_at`.
- Nuevo blueprint `backend/blueprints/tratamiento_semillas.py`: `GET/POST
  /api/tratamiento-semillas`, `GET/PUT/DELETE /api/tratamiento-semillas/<id>`.
  Mismo aislamiento por `user_id`/`explotacion_id` y misma validación de
  pertenencia de parcela que el resto de módulos.
- Nueva pantalla de formulario en `frontend/screens_forms.jsx`
  (`FormTratamientoSemilla`), con selector de parcela/UHC (mismo patrón que
  `FormFertilizacion`), selector de tipo de tratamiento (catálogo de 4) y
  eficacia (catálogo de 3).
- Añadir la entrada en `HELP_SCREENS` de `screens_ayuda.jsx` en el mismo PR.

## Criterios de aceptación

1. Se puede registrar un tratamiento de semilla "realizado en la
   explotación" con superficie, fecha y tipo de tratamiento.
2. Se puede registrar uno de "adquirida tratada fuera de España" sin dato de
   cantidad/eficacia (todos opcionales salvo los tres marcados obligatorios).
3. El listado se filtra por `user_id` y `explotacion_id`.
4. El catálogo de tipo de tratamiento muestra solo los 4 valores reales (2 a
   5), no un falso valor 1.

## Qué no entra

- `codigo` del tratamiento de semilla asignado por SIEX: no se construye.
- No se añade este módulo a `export_pdf.py`/`exports.py` en este spec.
- No se valida `numRegistro`/`sustAct` contra ningún catálogo — hoy tampoco
  se valida en `tratamientos`, mismo criterio.
