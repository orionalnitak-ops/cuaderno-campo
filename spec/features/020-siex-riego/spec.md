# 020 — Riego: superficie, catálogos de origen/energía y buenas prácticas (bloque 3/8 de compatibilidad SIEX)

Tercer bloque del ítem 002 (ver `spec/constitution/roadmap.md`). Fuente: hoja
"Estructura Cuaderno", nodo `<riego>`, filas 124-137.

## El problema

`riego` (`backend/db.py:768`) guarda: fecha, `tipo_riego` (texto libre),
`volumen_m3`, `horas_riego`, `fuente_agua` (texto libre) y notas. SIEX pide
9 campos que hoy no existen o existen como texto libre sin código de
catálogo:

| Campo SIEX | Fila | Obligat. | Tipo | Estado en la app |
|---|---|---|---|---|
| `superficie` (regada) | 127 | **1** | number(8,2) | falta por completo — no hay columna de superficie en `riego` |
| `sistema` | 128 | **1** | catálogo (7 valores) | `tipo_riego` existe pero es texto libre, sin código |
| `unidadCantidad` de `cantidad` | 131 | 0..1 | catálogo (solo 4=Litros o 6=m³) | `volumen_m3` asume m³ siempre, sin código explícito |
| `dosis` + `unidadDosis` | 130-131 | 0..1 | number(10,2) | falta por completo |
| `origen` (del agua) | 133 | 0..1 | catálogo (6 valores) | `fuente_agua` existe pero es texto libre |
| `numContador` | 134 | 0..1 | string(14) | falta |
| `tipoEnergia` | 135 | 0..1 | catálogo (~11 valores) | falta |
| `declBuenPrac` | 136 | 0..1 | boolean | falta |
| `buenPrac` | 137 | 0..1 | catálogo (ámbito "Riego") | falta |

`codigo` (fila 125, asignado por SIEX) se descarta, mismo motivo que siempre.

## Los catálogos: todos pequeños, todos `<select>`

Verificados en `Catalogos_xlsx.zip` — ninguno necesita tabla de referencia
ni endpoint de búsqueda, un `<select>` simple basta en los cuatro:

- **Sistema de riego** (`Sistema de riego.xlsx`, 7 filas): Superficie o
  Gravedad, Aspersión fija, Aspersión móvil, Microaspersión, Nebulización,
  Goteo, Hidropónico.
- **Origen del agua** (`Procedencia del agua de riego.xlsx`, 6 filas):
  Superficial, Subterránea, Pluvial, Regeneración, Desalinización, Recursos
  alternativos.
- **Tipo de energía** (`Tipo de energía.xlsx`, 11 filas): Eléctrica, Diésel,
  Gasolina, Eléctrica fotovoltaica, Eléctrica eólica, Biodiésel, Biogás...
- **Buenas prácticas** (`Buenas prácticas.xlsx`, 98 filas totales, pero con
  columna `Ámbito` que las separa en Fertilización/Riego/Fitosanitario — el
  `<select>` de este formulario filtra solo las de ámbito "Riego", que son
  unas 30). Incluye un código `0` = "No realiza buenas prácticas" por ámbito,
  útil como opción por defecto cuando `declBuenPrac` es falso.
- **Unidad de la cantidad de agua** (`Unidades de medida.xlsx`, 82 filas
  totales) — pero SIEX restringe este campo concreto a solo dos valores: `4`
  (Litros) y `6` (metros cúbicos), según la observación de la fila 131. El
  `<select>` de este campo no muestra las 82 filas, solo esas dos.

## La regla

- Nuevas columnas nullable en `riego` (`_add_col`): `superficie_ha` (REAL),
  `sistema_riego_cod` (INTEGER), `unidad_cantidad_cod` (INTEGER, solo 4 o 6),
  `dosis_valor` (REAL), `dosis_unidad` (TEXT), `origen_agua_cod` (INTEGER),
  `num_contador` (TEXT), `tipo_energia_cod` (INTEGER), `decl_buenas_practicas`
  (INTEGER/boolean), `buena_practica_cod` (INTEGER).
- `tipo_riego` y `fuente_agua` (texto libre) **no se eliminan** — siguen
  guardando lo que el agricultor escriba hoy, igual que `asesor` TEXT
  convive con `asesor_id` en tratamientos (ver `backend/db.py:726-731`). Los
  campos de catálogo son adicionales, no un reemplazo.
- `superficie_ha` es la única marcada obligatoria por SIEX (`ocurr=1`) que
  hoy no existe en absoluto. Es una decisión pendiente: ¿se hace obligatoria
  en el formulario de la app, o se deja opcional como hoy y se guarda vacía
  cuando falte? Ninguna decisión se toma aquí — señalado explícitamente para
  resolver antes de implementar, igual que pasó con variedad en el 018.
- El `<select>` de buenas prácticas se filtra por `Ámbito = 'Riego'` al
  importar o al servir el catálogo — nunca se le muestran al agricultor las
  de fertilización o fitosanitario.

## Criterios de aceptación

1. El formulario de riego pide superficie regada, con las mismas unidades
   que ya usa el resto de la app (hectáreas).
2. Elegir un sistema de riego del `<select>` (7 opciones) guarda
   `sistema_riego_cod`; el campo `tipo_riego` de texto libre sigue
   funcionando igual que hoy si el agricultor no usa el desplegable.
3. Marcar "sí" en buenas prácticas ofrece solo las ~30 opciones de ámbito
   Riego, nunca las de fertilización.
4. Los registros de riego ya existentes no se tocan: todas las columnas
   nuevas nacen `NULL`.
5. El campo de unidad de cantidad de agua solo ofrece Litros o m³, nunca las
   otras unidades del catálogo general (kg, ha, etc.).

## Qué no entra

- `codigo` del riego asignado por SIEX tras la subida: no se construye.
- No se crea una tabla de referencia en BD para ningún catálogo de este
  bloque — los cuatro caben en un `<select>` estático en el frontend (o una
  tabla de configuración mínima si se prefiere no hardcodear texto en JSX,
  pero sin endpoint de búsqueda ni paginación).
- No se decide aquí si `superficie_ha` pasa a ser obligatoria en el
  formulario — ver nota de "decisión pendiente" arriba.
