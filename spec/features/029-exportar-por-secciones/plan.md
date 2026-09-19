# 029 — Plan de implementación

Spec aprobada por Raúl el 19-09-2026. Este plan no introduce ninguna
dependencia nueva ni ninguna ruta nueva.

**Principio que manda sobre todo lo demás:** sin el parámetro `secciones`, el
PDF y el Excel tienen que salir **idénticos a los de hoy**. Cualquier duda se
resuelve a favor de no tocar el camino actual.

---

## Tarea 1 — El intérprete de la selección (`backend/helpers.py`)

Una función, usada por las dos rutas, para que el PDF y el Excel no puedan
interpretar lo mismo de forma distinta.

```
SECCIONES = ('parcelas', 'tratamientos', 'fertilizacion', 'labores',
             'riego', 'cosecha', 'plan_abonado', 'compras')

parse_secciones(arg) -> (set, bool completo)
```

Reglas, en este orden:

1. `arg` vacío, ausente o `None` → todas. `completo = True`.
2. Se parte por comas, se limpia y se pasa a minúsculas.
3. Las claves que no estén en `SECCIONES` se descartan sin avisar.
4. Si tras descartar no queda ninguna → todas. `completo = True`.
5. Si quedan las ocho → todas. `completo = True` (un extracto de todo es el
   cuaderno completo, no un extracto).
6. En cualquier otro caso → ese conjunto, `completo = False`.

Nunca devuelve un conjunto vacío. Ese es el invariante que impide generar un
fichero sin contenido.

**Test:** los seis casos de arriba, más una entrada con basura mezclada
(`tratamientos,,BORRAR,riego` → `{tratamientos, riego}`).

## Tarea 2 — Las dos rutas (`backend/blueprints/imports_exports.py`)

En `route_export_excel` y `route_export_pdf`, leer
`request.args.get('secciones')`, pasarlo por `parse_secciones` y entregar
`(secciones, completo)` a la función de generación. Nada más. El resto de la
ruta no se toca: `campana`, `get_uid()`, `get_active_explotacion_id()`, los
decoradores de plan activo y el manejo de error del Excel se quedan como están.

## Tarea 3 — Excel (`backend/exports.py`)

`export_excel(user_id, campana, explotacion_id, secciones=None)`.
`secciones=None` significa todas, para que las llamadas que ya existan no
cambien de comportamiento.

Cada bloque `wb.create_sheet(...)` pasa a ir dentro de su `if`. La hoja
`PORTADA` (`wb.active`) queda fuera de cualquier condición: es la que impide
que openpyxl se quede sin hojas y la que identifica al titular.

`COMPRAS-VENTAS` ya está hoy dentro de un `if` por otro motivo: se respeta esa
condición **y** se le añade la de la selección.

## Tarea 4 — PDF: el filtro (`backend/export_pdf.py`)

`export_pdf(user_id, campana, explotacion_id, secciones=None, completo=True)`.

Las ocho llamadas `_section_*()` de `export_pdf()` van dentro de su `if`. Los
`Spacer` que las separan solo se añaden si la sección anterior se imprimió, o
el documento sale con huecos raros al principio.

La portada se mantiene siempre.

## Tarea 5 — PDF: la marca de Extracto (la parte delicada)

Si `completo` es `False`, tres sitios cambian y **los tres a la vez**. Si se
olvida uno, el documento sigue teniendo sello de oficial.

| Sitio | Hoy | En extracto |
|---|---|---|
| `_PageTemplate.__call__` (pie, ~línea 177) | `RD 1311/2012 Anexo III · Generado con Cuaderno de Campo Digital` | `EXTRACTO — no sustituye al cuaderno completo · Cuaderno de Campo Digital` |
| `_cover_page` subtítulo (~línea 810) | `Cuaderno oficial de explotación agrícola · RD 1311/2012 Anexo III` | `Extracto del Cuaderno de Explotación` + línea con las secciones incluidas |
| `SimpleDocTemplate` (~línea 939) | `title=Cuaderno de Campo — …`, `subject=Cuaderno oficial RD 1311/2012` | `title=Extracto — …`, `subject=Extracto del Cuaderno de Explotación` |

`_PageTemplate` recibe un tercer argumento `completo` y decide el texto del
pie. `_cover_page` recibe `completo` y la lista de secciones incluidas, para
poder escribir en portada qué lleva el documento.

**Lo que NO cambia:** los subtítulos de cada sección
(`Registro obligatorio RD 1311/2012 Anexo III — Orden APA/204/2023` y
compañía). Esas citas son ciertas para esa tabla concreta. Lo que se cae es la
afirmación de que el **documento entero** es el cuaderno.

El bloque de firma del final tampoco se toca: un extracto también lo firma el
titular.

## Tarea 6 — La lista, dentro de un único componente de exportar

**Decisión de Raúl (19-09-2026): el camino es el mismo para el PDF y para el
Excel.** Aunque el documento final sea distinto, llegar a él se hace igual.

Eso convierte `BotonPdfOficial` (`frontend/screens_settings.jsx:11`) en
`BotonExportar({ formato, campana, className, style, children })`, con
`formato` valiendo `'pdf'` o `'excel'`. Deja de haber dos caminos que mantener:
hay uno, con un parámetro.

El modal reutiliza el patrón que ese mismo componente ya tiene para el NIF
(`position: fixed`, `inset: 0`, fondo `rgba(0,0,0,0.45)`) — no se inventa un
patrón nuevo.

Estado: `seleccion` (un `Set`) y `todas` (booleano, arranca en `true`).

La máquina de estados de la spec, tal cual:

| Acción | Resultado |
|---|---|
| "Todas" activo + tocas una hoja | `todas = false`, `seleccion = {esa}` |
| Tocas otra hoja | se suma o se quita de `seleccion` |
| `seleccion` llega a las ocho | `todas = true`, `seleccion` se vacía |
| Tocas "Todas" | `todas = true`, `seleccion` se vacía |
| Quitas la última de `seleccion` | `todas = true` |

Al pulsar **Descargar** se construye la URL: si `todas`, sin parámetro (el
camino de hoy, byte por byte); si no, `&secciones=a,b,c`.

Filas grandes (mínimo 44 px de alto, como el resto de la app) porque esto se
usa con el pulgar en el campo.

## Tarea 7 — Encajar con el aviso del NIF

**Primero el NIF, después la lista, y lo mismo en los dos formatos**
(decisión de Raúl, 19-09-2026). Dos pasos en **el mismo modal**, nunca dos
ventanas una encima de la otra:

```
  (si falta el NIF)  paso 'nif'  →  paso 'lista'  →  descarga
```

**Por qué el NIF va primero:** no depende de lo que se elija. La portada lleva
el titular tanto en el cuaderno completo como en un extracto para una bodega,
así que la pregunta es la misma salga lo que salga. Pedirlo al final sería
hacer aparecer un obstáculo cuando la persona ya ha dicho "adelante".

**Por qué también en el Excel** (cambia lo que hay hoy): la hoja `PORTADA` del
Excel lleva el titular y el NIF igual que la portada del PDF, así que sale
igual de incompleta. Y el camino para llegar a un documento no debería
depender del formato del documento. Hoy el aviso solo salta en el PDF; a
partir de la 029 salta en los dos.

El paso del NIF se mantiene tal cual está hoy, textos incluidos, con una sola
diferencia: el botón deja de ser "Guardar y descargar" y pasa a ser
**"Guardar y continuar"**, y el enlace de abajo, **"Continuar sin el NIF"** —
porque ya no descarga, lleva a la lista.

Si el NIF ya está puesto (el caso normal), el paso se salta entero y se abre
la lista directamente. Quien ya tiene sus datos completos no nota nada nuevo
salvo la lista.

El aviso **sigue sin bloquear** en ningún formato: "Continuar sin el NIF"
existe en los dos. Regla heredada de la 028 — avisa, no impide.

## Tarea 8 — Los cuatro puntos de entrada

Los cinco sitios que hoy exportan pasan todos por `BotonExportar`:

| Fichero | Qué hay hoy | Queda como |
|---|---|---|
| `screens_settings.jsx:677` | `BotonPdfOficial` | `<BotonExportar formato="pdf">` |
| `screens_settings.jsx:687` | botón Excel, `window.open` directo | `<BotonExportar formato="excel">` |
| `app.jsx:792` | `BotonPdfOficial` (barra superior) | `<BotonExportar formato="pdf">` |
| `app.jsx:796` | botón Excel, `window.open` directo | `<BotonExportar formato="excel">` |
| `screens_history.jsx:107` | `exportExcel()`, `window.open` directo | `<BotonExportar formato="excel">` |

Los tres `window.open` desaparecen. Después de esta tarea **no puede quedar
ningún `/api/export/` llamado a pelo desde el frontend**: si queda uno, hay un
camino que se salta el aviso del NIF y la lista, que es justo la
inconsistencia que esta decisión viene a quitar. Comprobarlo con
`grep -rn "api/export" frontend/*.jsx`.

Ojo con `screens_history.jsx`: usa `fCampana || campana`, no `campana`. Ese
detalle se conserva pasándoselo como prop `campana`.

## Tarea 9 — Tests (`backend/tests/test_export_secciones.py`)

Test plano, sin pytest, como el resto de `backend/tests/`.

1. `parse_secciones`: los siete casos de la tarea 1.
2. Excel sin `secciones` → mismas hojas y en el mismo orden que hoy.
3. Excel con `secciones=tratamientos` → exactamente `PORTADA` y
   `TRATAMIENTOS FITOSANITARIOS`.
4. Excel con basura → todas las hojas.
5. El libro nunca sale sin hojas.
6. PDF con `secciones=tratamientos` → el texto extraído **no** contiene
   `Anexo III` en la primera página ni en los pies.
7. PDF sin `secciones` → sí lo contiene (el sello vuelve, no se queda pegado).
8. `secciones` con las ocho claves → tratado como completo, con sello.

## Tarea 10 — Compilar y probar a mano

`cd frontend && npm run build` (obligatorio tras tocar cualquier `.jsx`).

Prueba manual antes del PR, con una cuenta de prueba en el servidor local y
**desde el móvil**, que es donde se va a usar:

- Descargar sin tocar nada → comparar con un PDF y un Excel generados antes
  del cambio.
- Seleccionar solo fitosanitarios → comprobar que el PDF dice "Extracto" en
  portada y en el pie, y que el Excel trae dos hojas.
- Marcar las ocho a mano → comprobar que vuelve el sello oficial.

---

## Orden de ejecución

1 → 2 → 3 → 9 (parcial: Excel) → 4 → 5 → 9 (completo: PDF) → 6 → 7 → 8 → 10

El backend entero se termina y se prueba antes de tocar el frontend. Así, si
algo se tuerce en la lista, la API ya está verificada.

## Commits

Uno por tarea, atómicos. La tarea 5 va en su propio commit aunque sea pequeña:
es la que tiene consecuencias si se hace mal.

## Riesgos

| Riesgo | Cómo se corta |
|---|---|
| Que el PDF completo cambie aunque sea un píxel | Test 7 + comparación manual contra un PDF generado antes |
| Que se olvide uno de los tres sitios del sello | Tarea 5 en un commit propio + test 6 que mira portada y pies |
| Que se pueda descargar un fichero vacío | El invariante de `parse_secciones` (nunca devuelve vacío) + test 5 |
| Que la selección se salte el filtro por explotación o usuario | No se toca `parcela_scope_clause` ni el `user_id` de ninguna consulta. El filtro nuevo decide **qué tablas**, nunca **qué filas** |
| Que quien cancele en el paso del NIF se quede sin poder exportar | "Continuar sin el NIF" sigue existiendo y lleva a la lista. El aviso nunca bloquea, igual que hoy (feature 028) |
