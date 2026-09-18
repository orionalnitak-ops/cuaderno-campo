# 028 — Plan de implementación

Rama: `feat/028-onboarding-minimo`, partiendo de `main` (no de
`feat/autorrelleno-superficie-parcela`, que sigue sin fusionar).

Orden deliberado: primero el backend con sus tests, porque el arreglo del
guardado es lo que hace seguro mandar un formulario de tres campos. Cada paso
es un commit.

---

## Paso 1 — `PUT /api/explotacion` actualiza solo lo que recibe

**Archivo:** `backend/blueprints/explotacion.py`

Hoy (líneas 58-62) el `UPDATE` incluye siempre los 13 campos de
`_EXPL_FIELDS`, y `data.get(f)` mete `None` en los que no vengan.

Cambio: construir la lista de columnas a partir de las **claves presentes** en
el JSON, filtradas contra `_EXPL_FIELDS` (la lista blanca se mantiene: nunca
se interpola nada que venga del cliente en el SQL).

- Campo presente con valor → se guarda.
- Campo presente y vacío (`""` o `null`) → se guarda vacío. Es un borrado
  deliberado.
- Campo ausente → no entra en el `UPDATE`, queda como estaba.
- Ningún campo conocido → no se ejecuta `UPDATE`; responde `ok` sin tocar nada.

Mismo tratamiento en `PUT /api/explotaciones/<id>` si comparte el patrón.

## Paso 2 — Tests del guardado parcial

**Archivo nuevo:** `backend/tests/test_explotacion_parcial.py`, con el patrón de
los tests que ya existen.

1. Con una explotación con todos los campos llenos, `PUT {"municipio": "X"}`
   cambia el municipio y deja intactos titular, NIF, CP, teléfono y email.
2. `PUT {"nif": ""}` borra el NIF y no toca el resto.
3. `PUT {}` no rompe y no cambia nada.
4. Un campo que no está en `_EXPL_FIELDS` se ignora.

## Paso 3 — La pantalla de entrada baja a tres campos

**Archivo:** `frontend/screens_onboarding.jsx`

- `FIELDS` se queda con `titular`, `municipio` y `campana_activa`.
- El estado inicial mantiene `email` con el del usuario y `campana_activa`
  como está hoy, pero ya no se envían ocho campos: el `PUT` manda solo los
  tres (por eso el paso 1 va antes).
- Textos: el título y el subtítulo dejan de hablar de "datos de la
  explotación" y explican el para qué. El municipio lleva su ayuda propia:
  con él se cargan el tiempo y los avisos de la zona.
- La validación sigue igual de simple: sin nombre no se continúa.

## Paso 4 — Aviso de NIF al exportar el PDF

**Archivos:** `frontend/screens_settings.jsx` (componente) y `frontend/app.jsx`
(botón de la barra superior).

Se define un único componente `AvisoNifModal` en `screens_settings.jsx`, que se
carga antes que `app.js` (ver el orden de `index.html`), y lo usan los dos
sitios que hoy abren el PDF: `app.jsx:793` y `screens_settings.jsx:588`.

Comportamiento: al pulsar "PDF oficial", si la explotación activa no tiene NIF,
en vez de abrir el PDF sale el aviso, que explica que el cuaderno para una
inspección lo lleva, con un campo para escribirlo y dos botones: guardarlo y
descargar, o descargar igualmente. Guardar usa el `PUT` parcial del paso 1, así
que no pisa ningún otro dato.

El Excel no lleva aviso: no es el documento que se entrega en una inspección.

## Paso 5 — Compilar y verificar

- `npm run build` en `frontend/` (obligatorio tras tocar cualquier `.jsx`).
- `pytest` en `backend/`.
- Prueba manual con una cuenta nueva: registrarse, ver los tres campos,
  entrar, comprobar que la meteorología carga con ese municipio, y pedir el
  PDF para ver el aviso.

---

## Riesgos

| Riesgo | Cómo se controla |
|---|---|
| Que el `PUT` parcial rompa el guardado de Ajustes, que manda el formulario entero | Los tests del paso 2; mandar todos los campos sigue funcionando igual que hoy |
| Que alguien entregue un PDF sin NIF | Es el paso 4. El aviso se puede saltar a propósito, pero ya no por desconocimiento |
| Que a los usuarios actuales les cambie algo | La pantalla solo sale si no hay titular; Lourdes, Cristóbal y Ángel no la ven |
| Olvidar compilar los JSX | Paso 5; en producción lo hace el Dockerfile, pero en local no |
