# 029 — Exportar por secciones: el extracto de fitosanitarios

**Fecha:** 2026-09-19
**Estado:** spec pendiente de confirmar

## Motivación

Raúl habló el 19-09-2026 con la **enóloga de una bodega**. Dos cosas salieron
de esa conversación:

1. Las bodegas **ya están pidiendo exactamente lo que la app hace hoy**: el
   registro digital de fitosanitarios. No piden SIEX, ni integración, ni nada
   que no tengamos.
2. Lo que hoy le llega de sus viticultores, y que Raúl vio en el móvil de
   ella, son **dos tablas de fitosanitarios y nada más**. Una hoja. Peor
   presentadas y con los datos menos claros que los nuestros.

Hoy nuestra exportación no sabe hacer eso. El PDF saca **ocho secciones** y el
Excel **ocho hojas**, siempre. Un viticultor que quiera mandarle sus
tratamientos a la bodega le manda de paso sus labores, su riego, su cosecha y
sus facturas de compra. Da de más, y obliga al de la bodega a buscar.

## La ventaja que ya tenemos y no estamos usando

La tabla de tratamientos del PDF ([export_pdf.py:310](../../../backend/export_pdf.py))
ya sale con doce columnas, entre ellas:

| Columna | Por qué le importa a la bodega |
|---|---|
| `Parcela` | Sabe de qué viña viene la uva |
| `Nº MAPA` | Comprueba que el producto está autorizado |
| `Sustancia Activa` | Es lo que se mide en el análisis de residuos |
| `Plazo Seg.(d)` | El plazo de seguridad del producto |
| **`F. mín. Cosecha`** | **La fecha a partir de la cual se puede vendimiar** |

Esa última columna es el diferencial, y está **verificado contra la
competencia real** (19-09-2026, dos hojas de dos viticultores distintos vistas
en el móvil de la enóloga):

> Las dos hojas ponían **el plazo de espera en días**. La nuestra es la única
> que pone **la fecha**.

Y las saca las dos: `Plazo Seg.(d)` y `F. mín. Cosecha`. La app la calcula sola
a partir del plazo del producto y la fecha de aplicación.

Un plazo en días obliga al de la bodega a trabajar: buscar la fecha de
aplicación en otra columna, sumar, y repetirlo por cada tratamiento y cada
parcela. Con varias aplicaciones sobre la misma viña manda la más tardía, que
es otra cuenta a mano más y otro sitio donde equivocarse. Una fecha no es un
dato: es la respuesta.

**Cautela sobre el alcance del hallazgo:** son dos hojas y no se sabe con qué
programa se hicieron (puede que ni con uno). No vale para decir "la
competencia no lo hace"; vale para decir "las que has visto no lo hacen".
Confirmarlo contra C3/SIGCEX, SICdecampo o GlobalCampo antes de usarlo como
argumento comparativo en público.

Es decir: el extracto no es solo "lo mismo en menos páginas". Es la misma
información **ya resuelta**.

## Qué cambia

### 1. Un parámetro opcional en las dos rutas

`blueprints/imports_exports.py` — las rutas `/api/export/excel` y
`/api/export/pdf` aceptan `?secciones=tratamientos,parcelas`.

**Si el parámetro no viene, el comportamiento es idéntico al de hoy.** Ese es
el criterio de diseño: nada de lo que funciona puede cambiar.

Claves válidas, una por sección ya existente:
`parcelas`, `tratamientos`, `fertilizacion`, `labores`, `riego`, `cosecha`,
`plan_abonado`, `compras`.

Una clave desconocida se ignora en silencio. Una lista vacía o sin ninguna
clave válida se trata como "todo", nunca como "nada": un fichero vacío es peor
que uno de más.

### 2. El filtro, donde ya está troceado el código

- **PDF:** `export_pdf()` ([export_pdf.py:909](../../../backend/export_pdf.py))
  llama a ocho `_section_*()` en fila. Cada llamada pasa a ir dentro de un `if`.
- **Excel:** `export_excel()` ([exports.py:53](../../../backend/exports.py))
  hace ocho `wb.create_sheet(...)`. Mismo tratamiento.

No se reestructura nada. No entra ninguna dependencia nueva.

### 3. La portada va siempre

No es opcional y no aparece como casilla.

- **Técnico:** openpyxl no admite un libro sin hojas. Si se desmarca todo, el
  fichero revienta.
- **De fondo:** una tabla de tratamientos sin titular, NIF y explotación no le
  vale a la bodega — no sabe de quién es.

### 4. La marca de extracto (el punto que más importa)

Si la selección **no** incluye las ocho secciones, el PDF deja de presentarse
como el cuaderno oficial. Tres sitios, los tres hay que tocarlos:

| Dónde | Hoy | En un extracto |
|---|---|---|
| Pie de cada página ([:177](../../../backend/export_pdf.py)) | `RD 1311/2012 Anexo III · Generado con...` | `EXTRACTO — no sustituye al cuaderno completo` |
| Subtítulo de portada ([:810](../../../backend/export_pdf.py)) | `Cuaderno oficial de explotación agrícola · RD 1311/2012 Anexo III` | `Extracto del Cuaderno de Explotación · secciones incluidas: ...` |
| Metadatos del PDF ([:939](../../../backend/export_pdf.py)) | `subject='Cuaderno oficial RD 1311/2012'` | `subject='Extracto del Cuaderno de Explotación'` |

**Por qué:** hoy el documento se sella como válido conforme al Anexo III. Si se
pueden quitar seis secciones de ocho y el sello sigue puesto, estaríamos
emitiendo un papel con pinta de oficial que no lo es. Es el mismo fallo del
plazo de seguridad de la feature 016: un control que falla en abierto.
El sello tiene que caerse solo, sin que el agricultor tenga que acordarse.

Las secciones que sí van dentro **no pierden** sus citas legales propias
(`Registro obligatorio RD 1311/2012 Anexo III — Orden APA/204/2023`, etc.):
esas son ciertas para esa tabla. Lo que se cae es la afirmación de que el
**documento entero** es el cuaderno.

### 5. La pantalla (diseño de Raúl, 19-09-2026)

Al pulsar **Exportar PDF** o **Exportar Excel** se abre una lista. La misma
lista para los dos formatos.

```
  ¿Qué quieres exportar?

  ● Todas  — el cuaderno de explotación completo
  ─────────────────────────────────────────────
  ○ Parcelas
  ○ Tratamientos fitosanitarios
  ○ Fertilización
  ○ Labores
  ○ Riego
  ○ Cosecha
  ○ Plan de abonado
  ○ Compras y ventas

               [ Cancelar ]   [ Descargar ]
```

**"Todas" viene marcado al abrir.** Quien no quiera pensar, pulsa Descargar y
obtiene exactamente lo que obtiene hoy.

La regla de selección, que es lo único que puede confundir:

| Acción | Qué pasa |
|---|---|
| Está "Todas" y tocas una hoja | "Todas" se apaga y queda marcada **solo** esa hoja |
| Marcas una segunda, una tercera… | Se van sumando |
| Llegas a marcar las ocho a mano | "Todas" se enciende sola |
| Tocas "Todas" | Se apagan todas las individuales |
| Desmarcas la última que quedaba | Vuelve "Todas" (nunca se puede descargar nada) |

Nunca existe el estado "Todas + dos hojas sueltas": no significa nada.

**La portada no aparece en la lista.** Va siempre, en los dos formatos, y no es
elegible (ver punto 3).

El orden de la lista es el del cuaderno oficial, el mismo en que salen las
secciones del PDF. Así lo que ves en la lista es lo que te vas a encontrar en
el documento.

El botón del PDF ya existe como componente compartido (`BotonPdfOficial` en
`screens_settings.jsx`, usado también desde `app.jsx`) y el de Excel está en
esos mismos dos sitios, así que la lista se escribe una vez y se usa en los
cuatro puntos de entrada.

## Criterios de aceptación

1. `/api/export/pdf?campana=X` sin `secciones` devuelve **byte por byte** el
   mismo documento que hoy. Igual para Excel.
2. `?secciones=tratamientos` devuelve un PDF con portada + tratamientos, y un
   Excel con PORTADA + TRATAMIENTOS FITOSANITARIOS. Nada más.
3. Ese PDF **no** contiene la cadena `Anexo III` en portada ni en el pie, y sus
   metadatos dicen "Extracto".
4. Con las ocho secciones marcadas, el documento sale sellado como oficial
   igual que hoy (el sello vuelve al marcar todo, no se queda pegado).
5. `?secciones=` vacío, `?secciones=loquesea` o claves inventadas → sale el
   cuaderno completo, nunca un fichero vacío.
8. En la lista, marcar una hoja teniendo "Todas" deja marcada solo esa; marcar
   las ocho a mano vuelve a encender "Todas"; desmarcar la última vuelve a
   "Todas". Nunca se llega a un estado sin nada seleccionado.
9. La portada no aparece en la lista y sale siempre en los dos formatos.
6. El Excel nunca se genera sin hojas.
7. La selección no puede saltarse el filtro por explotación activa ni el de
   usuario: `parcela_scope_clause` y el `user_id` siguen aplicando igual.

## Qué NO entra

- Elegir **columnas** dentro de una sección. Solo secciones enteras.
- Filtrar por parcela o por rango de fechas. El filtro sigue siendo la campaña.
- Enviar el extracto por email desde la app. Se descarga y el agricultor lo
  manda por donde quiera.
- Un formato específico para ninguna bodega concreta.

## Orden respecto a la 026

La 026 (campos SIEX en PDF y Excel) toca **los mismos dos ficheros**. No chocan
—026 añade columnas dentro de las tablas, 029 decide qué tablas salen— pero si
se hace la 026 primero, la 029 se escribe encima sin tocar nada suyo. Ese es el
orden recomendado.
