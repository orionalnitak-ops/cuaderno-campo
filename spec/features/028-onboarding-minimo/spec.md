# 028 — Entrada mínima: solo nombre, municipio y campaña

**Fecha:** 2026-09-18
**Motivación:** de las 7 personas que entraron a probar entre el 1 y el 4 de
septiembre de 2026, **3 no pasaron de la primera pantalla** (medido el
18-09-2026 con el MCP de Supabase, solo lectura). Esa pantalla
(`frontend/screens_onboarding.jsx`) es obligatoria, no se puede saltar y pide
ocho campos —titular, NIF, municipio, provincia, CP, teléfono, email y
campaña— antes de dejar ver nada de la app. Se pide el NIF a alguien que
todavía no sabe para qué sirve el programa.

De las 4 que sí la pasaron, 2 crearon parcelas y **ninguna registró una sola
actividad**. Esta feature ataca solo el primer escalón; la ayuda guiada con
bocadillos queda aparcada a propósito (decisión de Raúl, 18-09-2026) hasta ver
si esto mueve los números.

---

## El problema

| Escalón | Personas (tanda 1-4 sept) |
|---|---|
| Se registran | 7 |
| Pasan la pantalla de datos | 4 |
| Crean alguna parcela | 2 |
| Registran alguna actividad | 0 |

---

## Qué cambia

### 1. La pantalla de entrada pide tres campos

`frontend/screens_onboarding.jsx` pasa de ocho campos a tres:

| Campo | Por qué se queda |
|---|---|
| `titular` | Es el nombre que sale en el cuaderno. Ya se pide hoy y no genera fricción |
| `municipio` | Es lo que enciende la meteorología (`screens_home.jsx:266`). Sin él, el widget del tiempo y los avisos de AEMET no funcionan |
| `campana_activa` | Decide en qué campaña se guarda todo lo que apunte. Si se quita, el valor por defecto es `'2025/2026'`, escrito a mano en 12 sitios de `db.py`, y estaríamos en la campaña anterior a la actual |

**El texto tiene que decir para qué sirve cada cosa**, que es lo que hoy falta.
En concreto, el municipio se explica como "con tu municipio te ponemos el
tiempo y los avisos de tu zona", no como un dato administrativo.

Los otros cinco campos (NIF, provincia, CP, teléfono, email) **salen de esta
pantalla**. No se borran de ningún sitio: se siguen rellenando en
Ajustes → Explotación, que ya existe y ya los tiene
(`frontend/screens_settings.jsx`, `ExplotacionModal`).

### 2. Aviso antes de descargar el PDF si falta el NIF

El cuaderno oficial para una inspección lleva el NIF del titular
(`backend/export_pdf.py:826`). Hoy, si falta, el PDF se genera igual con un
guion en su lugar. Al dejar de pedirlo en la entrada, eso pasaría a ser lo
normal, y alguien entregaría a un inspector un cuaderno incompleto sin
enterarse.

Antes de generar el PDF, si el NIF de la explotación está vacío, se avisa y se
ofrece rellenarlo en ese momento. El aviso va **en el momento de exportar**,
donde el agricultor ya entiende para qué se le pide.

Criterio de la casa (`second-brain/principios.md`): los controles de
cumplimiento legal fallan cerrados. Aquí eso significa que el aviso salta
cuando el dato falta, nunca al revés.

### 3. Arreglar el guardado que borra campos

`backend/blueprints/explotacion.py:58-62` construye siempre un `UPDATE` con la
lista entera de campos:

```python
sets = ', '.join(f"{f}=?" for f in _EXPL_FIELDS)
c.execute(f"UPDATE explotacion SET {sets} WHERE id=? AND user_id=?",
          [data.get(f) for f in _EXPL_FIELDS] + [exp_id, uid])
```

`data.get(f)` devuelve `None` cuando el campo no viene en la petición, y ese
`None` **se guarda**: machaca lo que hubiera. Hoy no rompe nada porque las dos
pantallas que usan la ruta mandan el formulario completo, pero esta feature
introduce precisamente una pantalla que manda tres campos.

La ruta pasa a actualizar **solo los campos presentes en la petición**,
distinguiendo "no viene" (se deja como está) de "viene vacío" (se borra a
propósito). Si no llega ningún campo conocido, no se ejecuta ningún `UPDATE`.

---

## Criterios de aceptación

1. Un usuario nuevo ve tres campos y llega al inicio de la app rellenando solo
   nombre, municipio y campaña.
2. El texto de la pantalla explica para qué sirve el municipio.
3. Tras completarla, la meteorología del inicio carga con ese municipio.
4. NIF, provincia, CP, teléfono y email se siguen pudiendo ver y editar en
   Ajustes → Explotación, y lo que ya estaba guardado no cambia.
5. Al pedir el PDF oficial sin NIF, sale el aviso y se puede rellenar sin
   perder lo que se estaba haciendo. Con NIF, el PDF sale como hasta ahora.
6. `PUT /api/explotacion` con `{"municipio": "X"}` cambia el municipio y **deja
   intactos** titular, NIF, CP, teléfono y email. Cubierto con un test.
7. `PUT /api/explotacion` con `{"nif": ""}` sí borra el NIF (borrado
   deliberado). Cubierto con un test.
8. Lo que ya usan Lourdes, Cristóbal y Ángel sigue funcionando igual: ninguno
   vuelve a pasar por la pantalla de entrada, porque ya tienen titular.

## Fuera de alcance

- Los bocadillos de ayuda contextual y la guía guiada paso a paso. Aparcados.
- Tocar la guía de inicio de 6 slides (feature 004, cerrada).
- Cualquier cambio en el módulo de parcelas, que es el segundo escalón del
  embudo y se mirará después.
