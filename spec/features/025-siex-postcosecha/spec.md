# 025 — Post-cosecha: módulo nuevo (bloque 8/8 de compatibilidad SIEX)

Octavo y último bloque del ítem 002 (ver `spec/constitution/roadmap.md`).
Tercero de los tres módulos completamente nuevos. Fuente: hoja "Estructura
Cuaderno", nodo `<postCosecha>`, filas 80-96.

## El problema

Hoy no existe ninguna tabla ni pantalla para tratamientos fitosanitarios
aplicados **después** de la cosecha (fumigación de grano almacenado,
tratamiento de fruta en cámara...). SIEX lo modela como un bloque propio,
casi idéntico en forma a `<actFito>` (bloque 022) pero referido a un
producto ya cosechado, no a un cultivo en pie.

## Los campos (11 de los 12 estimados en la auditoría — ver nota)

| Campo SIEX | Fila | Obligat. | Tipo | Catálogo |
|---|---|---|---|---|
| `fecActuacion` | 82 | **1** | date | — |
| `codProdVegetal` | 83 | **1** | number(4) | `Producto Vegetal.xlsx` (693 filas, mismo catálogo y misma tabla `ref_productos_siex` que los bloques 019 y 023) |
| `probFito` | 84 | 0..1 | catálogo | **no existe todavía en SIEX** — mismo bloqueo que en el bloque 022, ver más abajo |
| `justifActua` | 85 | 0..1 | number(1) | `Justificación de la actuación.xlsx` (6 filas, mismo catálogo del bloque 022) |
| `cantidad` | 86 | 0..1 | number(8,2) | — |
| `unidad` | 87 | 0..1 | number(1) | `Unidades de medida.xlsx` (82 filas, catálogo genérico) |
| `eficacia` | 88 | 0..1 | number(1) | `Eficacia del tratamiento.xlsx` (3 filas, mismo catálogo del bloque 022 y 024) |
| `observaciones` | 89 | 0..1 | string(150) | — |
| `nomComProd` (ASPAFITOS) | 91 | 0..1 | string(50) | texto libre |
| `numRegistro` (ASPAFITOS) | 92 | **1** | string(50) | texto libre |
| `sustAct` (ASPAFITOS) | 93 | 0..1 | string(200) | texto libre |

`codigo` (fila 81, asignado por SIEX) se descarta, mismo motivo de siempre.
La auditoría del roadmap estimaba 12 campos de brecha; contando uno por
fila real de este bloque salen 11 (sin contar `codigo`, que nunca se cuenta
en ningún bloque). Diferencia menor, no cambia el esfuerzo del bloque.

## `probFito`: mismo bloqueo que en el bloque 022

Igual que en tratamientos fitosanitarios, el catálogo de "Problemática
Fitosanitaria" no existe todavía — el propio Anexo VI lo marca "Validar
según catálogo **por crear**" (observación, fila 84). No se codifica un
campo contra un catálogo que SIEX no ha publicado. Si el bloque 022 se
implementa primero y resuelve este catálogo (porque SIEX lo publica), este
bloque hereda la misma solución sin trabajo adicional — son el mismo campo
con el mismo bloqueo.

## La regla

- Nueva tabla `post_cosecha` (patrón de blueprint simple,
  `backend/blueprints/fertilizacion.py`): `id`, `user_id NOT NULL`,
  `explotacion_id`, `parcela_id`, `parcela_etiqueta`, `fecha_actuacion` (TEXT,
  obligatorio), `codigo_producto_siex` (INTEGER, catálogo de 693, obligatorio),
  `justificacion_actuacion_cod` (INTEGER, catálogo de 6), `cantidad` (REAL),
  `unidad_cod` (INTEGER), `eficacia_cod` (INTEGER, catálogo de 3),
  `observaciones` (TEXT), `producto_comercial` (TEXT), `num_registro_mapa`
  (TEXT, obligatorio si se informa un producto), `sustancia_activa` (TEXT),
  `campana` (TEXT DEFAULT '2025/2026'), `created_at`, `updated_at`,
  `deleted_at`.
- Nuevo blueprint `backend/blueprints/post_cosecha.py`: `GET/POST
  /api/post-cosecha`, `GET/PUT/DELETE /api/post-cosecha/<id>`. Mismo
  aislamiento por `user_id`/`explotacion_id` y misma validación de
  pertenencia de parcela que el resto de módulos.
- Nueva pantalla de formulario en `frontend/screens_forms.jsx`
  (`FormPostCosecha`), reutilizando el mismo selector de producto de la
  tabla `ref_productos_siex` que construyen los bloques 019/023 — si alguno
  de esos dos ya está desplegado, este bloque no reimporta el catálogo, solo
  reutiliza el endpoint de búsqueda que ya exista.
- Añadir la entrada en `HELP_SCREENS` de `screens_ayuda.jsx` en el mismo PR.

## Criterios de aceptación

1. Se puede registrar un tratamiento post-cosecha con fecha, producto
   vegetal tratado (del catálogo) y datos ASPAFITOS del producto
   fitosanitario aplicado.
2. El listado se filtra por `user_id` y `explotacion_id`.
3. `probFito` no aparece en ningún `<select>` ni columna — no hay catálogo
   oficial contra el que validarlo todavía.
4. Si los bloques 019 o 023 ya están desplegados, este bloque reutiliza su
   tabla `ref_productos_siex` sin reimportarla.

## Qué no entra

- `codigo` del tratamiento post-cosecha asignado por SIEX: no se construye.
- `probFito`: bloqueado hasta que SIEX publique el catálogo — igual que en
  el bloque 022. Revisar los dos bloques juntos cuando se publique.
- No se añade este módulo a `export_pdf.py`/`exports.py` en este spec.
- No se resuelve el cruce cultivo↔producto para cultivos fuera de
  `CULTIVOS_IACS` (misma limitación que los bloques 019 y 023).
