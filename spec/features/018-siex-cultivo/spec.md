# 018 — Variedad con código SIEX en Cultivo (bloque 1/8 de compatibilidad SIEX)

Primero de los 8 bloques del ítem 002 del roadmap (ver desglose en
`spec/constitution/roadmap.md`). El más pequeño a propósito, para abrir el
camino antes de los bloques grandes.

## El problema

SIEX exige que la variedad del cultivo sea un código de un catálogo cerrado
(`Variedad - Especie - Tipo`, 86.136 filas), no texto libre. Hoy
`cultivos_campana.variedad` es un campo de texto libre (`ZoomInput`, ver
`screens_forms.jsx`), sin ninguna validación contra catálogo.

La auditoría del 2026-08-26 detectó un segundo campo de brecha —`codigo` SIEX
asignado al cultivo tras el alta— que **se descarta** (ver "Qué no entra").
Este spec es solo sobre la variedad.

## El obstáculo real: dos catálogos de cultivo distintos

El selector de cultivo que ya existe (`CULTIVOS_IACS` en
`frontend/screens_parcelas.jsx`, duplicado en `backend/helpers.py`) usa
**códigos IACS/SIGPAC** (`'430'` = Cebada, `'980'` = Barbecho...). El catálogo
oficial `Cultivo.xlsx` de SIEX usa **su propio código numérico secuencial**
(`1` = Trigo blando, `5` = Cebada...) — espacio de códigos totalmente distinto,
sin campo de cruce directo entre ambos en los catálogos descargados.

Y el catálogo de variedades (`Variedad - Especie - Tipo.xlsx`) está indexado
por el código SIEX del cultivo, no por el IACS. Sin resolver este cruce, no
hay forma de acotar las variedades a elegir por el cultivo ya seleccionado.

**La solución:** un cruce por nombre, hecho una sola vez a mano (no en
runtime). Los pilotos actuales cultivan un puñado de cultivos (olivar, viñedo,
cereal, algún hortícola) — no hace falta resolver los ~1.121 cultivos del
catálogo, solo los que aparecen en `CULTIVOS_IACS`. Se añade una columna
`cod_siex` a esa lista (frontend y backend, igual que ya se duplica
`cultivo_iacs_cod`), rellenada a mano comparando nombres contra `Cultivo.xlsx`.
Los cultivos IACS que no tengan un match razonable en el catálogo SIEX
(barbecho, mezclas, "otros") se quedan con `cod_siex: null` — variedad sigue
siendo texto libre para esos.

## La regla

- **86.136 filas no se cargan al frontend.** Se importan a una tabla de
  referencia en BD (`ref_variedades_siex`: `cod_cultivo_siex`, `cod_variedad`,
  `nombre`, PK compuesta) mediante un script en `backend/tools/`, igual que ya
  existe un patrón de import de catálogos/recuentos en esa carpeta. Se corre
  una vez, no en cada arranque.
- Nuevo endpoint de búsqueda (p.ej. `GET /api/catalogos/variedades?cultivo_iacs_cod=430&q=pic`)
  que resuelve el `cod_siex` del cultivo IACS recibido y devuelve variedades
  que empiecen o contengan `q`, limitado a ~20 resultados. Sin este límite, un
  cultivo como trigo blando (cientos de variedades) sería una lista inmanejable
  en móvil.
- En el formulario, el campo `variedad` sigue siendo `ZoomInput` de texto
  libre tal cual está — se le añade autocompletado contra ese endpoint cuando
  el cultivo seleccionado tiene `cod_siex`. Si el agricultor escribe algo que
  no coincide con ninguna sugerencia, se guarda igual como texto libre: nunca
  se bloquea la anotación por no encontrar coincidencia en un catálogo.
- Nueva columna `cultivos_campana.variedad_cod_siex` (nullable, `_add_col`).
  Se rellena solo cuando el agricultor elige una sugerencia del catálogo; si
  escribe libre, se queda `NULL` y `variedad` guarda el texto tal cual —
  igual que hoy, cero regresión sobre los datos existentes.

## Criterios de aceptación

1. Seleccionar un cultivo con cruce SIEX conocido (ej. Cebada) y escribir
   "pla" en variedad sugiere variedades reales del catálogo que empiezan por
   "pla" para ese cultivo (no de otro cultivo).
2. Elegir una sugerencia guarda `variedad` (nombre) y `variedad_cod_siex`
   (código) en el mismo registro.
3. Escribir una variedad que no está en el catálogo se guarda igual, con
   `variedad_cod_siex = NULL`. Ningún guardado se bloquea por esto.
4. Un cultivo sin `cod_siex` mapeado (ej. Barbecho) no ofrece autocompletado;
   el campo se comporta exactamente como hoy.
5. Los cultivos y variedades ya guardados antes de este cambio no se tocan:
   `variedad_cod_siex` nace `NULL` en todos, no hay backfill automático.
6. Import de catálogo verificado con al menos: Cebada, Olivo, Vid — los tres
   cultivos reales de los pilotos — devolviendo variedades sensatas.

## Qué no entra

- El campo `codigo` SIEX del cultivo (asignado tras el alta en SIEX): no se
  construye. La app no envía altas a SIEX (ver nota del roadmap sobre qué
  significa "compatible con SIEX" — no hay envío por API), así que ese campo
  se quedaría vacío siempre. No se crea una columna que nunca se puede
  rellenar.
- No se resuelve el cruce IACS↔SIEX para los ~1.121 cultivos del catálogo
  completo, solo para los que están en `CULTIVOS_IACS` hoy. Si se añade un
  cultivo IACS nuevo más adelante, hay que rellenar su `cod_siex` a mano en
  ese momento (igual que ya pasa con los grupos de leñosos, feature 014).
- No se toca `screens_parcelas.jsx` más allá de añadir el campo `cod_siex` a
  las entradas de `CULTIVOS_IACS` que tengan un cruce claro.
