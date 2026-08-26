# 022 — Tratamientos fitosanitarios: superficie, catálogos y doble validación de asesor (bloque 5/8 de compatibilidad SIEX)

Quinto bloque del ítem 002 (ver `spec/constitution/roadmap.md`) y el más
grande de los "de columnas" — el siguiente (023) ya es módulo nuevo. Fuente:
hoja "Estructura Cuaderno", nodo `<actFito>`, filas 20-64.

## El problema

`tratamientos` (`backend/db.py:687-733`) es la tabla más completa de las
cuatro que ya existen: ya tiene `justificacion_actuacion`, `asesor_id` (FK a
`asesores`), `aplicador_id` (FK a `aplicadores`), `equipo_id` (FK a
`equipos`), `num_registro_mapa`/`producto_comercial`/`sustancia_activa` (que
ya cubren el bloque `<ASPAFITOS>` completo, filas 35-39). Pero SIEX pide
varios campos que hoy no existen, y una estructura de asesor que la tabla
actual no soporta.

| Campo SIEX | Fila | Obligat. | Tipo | Estado en la app |
|---|---|---|---|---|
| `supTratada` | 23 | 0..1 | number(8,2) | **falta por completo** — no hay superficie en `tratamientos` |
| `probFito` | 24 | 0..1 | catálogo | **el catálogo no existe todavía ni en SIEX** — ver más abajo |
| `justifActua` | 25 | 0..1 | catálogo, 6 valores | existe como texto libre (`justificacion_actuacion`), sin código |
| `unidad` (de `cantidad`) | 27 | 0..1 | catálogo | `dosis_unidad` es texto libre, sin código |
| `eficacia` | 28 | 0..1 | catálogo, 3 valores | existe como texto libre (`eficacia`), sin código |
| `anq` (alternativa no química, bloque completo) | 30-34 | 0..1 | — | **falta por completo**, ver más abajo |
| `tipoCarnet` del aplicador | 45 | 0..1 | catálogo | **el catálogo no existe todavía** — `aplicadores` no tiene esta columna |
| `asesor` × 2 (Intermedia + Final) | 47-55 | 0..2 | — | la app solo soporta **un** asesor por tratamiento |
| `propio` del equipo | 61 | 0..1 | boolean | falta en `equipos` |
| `docIdentPropiet` del equipo | 62 | 0..1 | string(9) | falta en `equipos` |

`codigo` (fila 21, asignado por SIEX) se descarta, mismo motivo de siempre.

## Dos catálogos que no existen ni en el propio SIEX

`probFito` (problemática fitosanitaria) y el catálogo de "Tipo Carnet
Aplicador" no están en `Catalogos_xlsx.zip` (122 hojas revisadas, ninguna se
llama así). El propio Anexo VI lo dice en la columna Observaciones: *"Validar
según catálogo **por crear**"*. No es una brecha de la app — es que SIEX
todavía no ha publicado ese catálogo. **No se puede codificar un campo
contra un catálogo que no existe.** Se deja el campo fuera hasta que SIEX lo
publique (ver "Qué no entra"). Lo mismo aplica al catálogo de "Intensidad
Medida" que necesitaría `unidadANQ` dentro del bloque `anq`.

## El bloque `anq` (alternativa no química): concepto nuevo, opcional

Cuando el tratamiento no es un producto químico sino una medida alternativa
(suelta de fauna auxiliar, mallas anti-insectos, siembra directa...), SIEX
lo modela como un sub-bloque `anq` con `tipoANQ` (catálogo
`Tipo de medida fitosanitaria.xlsx`, 14 filas — pequeño, `<select>` directo)
y `cantIntMedANQ`/`unidadANQ` (este último bloqueado por el catálogo
"Intensidad Medida" que no existe, ver arriba). Es opcional (`0..1`) y no
tiene nada hoy en la app.

## El asesor doble: `asesor_id` único no basta

SIEX permite hasta **2** asesores por tratamiento — uno de validación
**Intermedia** y otro de validación **Final** (`tipoVal`: I/F, fila 48) — cada
uno con su propia fecha, código/descripción de validación
(`validacion`, fila 53) e indicador de si fue confirmación o firma
electrónica (`conf_o_firElect`, fila 54). Hoy `tratamientos.asesor_id`
apunta a un único asesor sin distinguir el tipo de validación. Esto es el
"concepto nuevo" que menciona el roadmap para este bloque.

## La regla

- Nuevas columnas nullable en `tratamientos` (`_add_col`): `superficie_tratada_ha`
  (REAL), `justificacion_actuacion_cod` (INTEGER, catálogo de 6 — codifica lo
  que ya guarda `justificacion_actuacion` en texto), `unidad_cod` (INTEGER),
  `eficacia_cod` (INTEGER, catálogo de 3 — codifica `eficacia` existente).
- Nuevas columnas para el asesor de validación **Final**, sin tocar
  `asesor_id` (que pasa a representar la validación **Intermedia**):
  `asesor_final_id` (FK `asesores`), `fecha_validacion_intermedia`,
  `fecha_validacion_final`, `validacion_intermedia` (TEXT),
  `validacion_final` (TEXT), `confirmacion_o_firma_intermedia` (TEXT, 'C'/'F'),
  `confirmacion_o_firma_final` (TEXT, 'C'/'F').
- Nuevas columnas en `equipos`: `propio` (boolean, default true — la mayoría
  de equipos hoy registrados son del propio agricultor) y
  `nif_propietario` (TEXT, nullable, solo relevante si `propio = false`).
- El bloque `anq` es una estructura nueva y opcional: si se implementa,
  columnas nullable `anq_tipo_cod` (catálogo de 14), `anq_cantidad`,
  `anq_unidad_cod` — este último sin catálogo real disponible (ver arriba),
  se deja como texto libre hasta que SIEX publique "Intensidad Medida".
- `justificacion_actuacion`, `eficacia`, `dosis_unidad` de texto libre no se
  tocan — conviven con los códigos nuevos, mismo patrón que `asesor`/
  `asesor_id` ya establecido en esta misma tabla.

## Criterios de aceptación

1. El formulario de tratamiento pide superficie tratada (opcional).
2. Elegir una justificación del catálogo de 6 opciones guarda
   `justificacion_actuacion_cod`; el campo de texto libre sigue funcionando
   igual que hoy.
3. Se puede asignar un asesor de validación Intermedia y otro de validación
   Final al mismo tratamiento, cada uno con su propia fecha.
4. Marcar un equipo como "ajeno" (no propio) pide el NIF del propietario;
   marcarlo como propio no lo pide.
5. `probFito` y `tipoCarnet` no aparecen en ningún `<select>` ni columna
   nueva — no hay catálogo oficial contra el que validarlos todavía.
6. Los tratamientos ya registrados no se tocan: todas las columnas nuevas
   nacen `NULL`, y `asesor_id` sigue significando lo mismo que hoy
   (compatibilidad con los ~datos ya guardados por los pilotos).

## Qué no entra

- `codigo` del tratamiento asignado por SIEX: no se construye.
- `probFito` (problemática fitosanitaria) y `tipoCarnet` (tipo de carné del
  aplicador): SIEX aún no ha publicado el catálogo. Revisar cuando lo
  publiquen — hasta entonces, no hay nada que codificar.
- `unidadANQ` del bloque `anq`: mismo motivo, catálogo "Intensidad Medida" no
  publicado. Si se implementa `anq`, ese campo concreto queda como texto
  libre o vacío.
- No se elimina ni se renombra `asesor_id` — pasa a significar
  "asesor de validación Intermedia" sin romper los tratamientos ya guardados
  por los pilotos (siguen leyéndose igual en PDF/Excel).
