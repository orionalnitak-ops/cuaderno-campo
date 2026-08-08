# 015 — Plan de implementación

Ver `spec.md` para el qué y el porqué. Aquí va el cómo.

---

## Lo primero: el uso SIGPAC viene sucio

Los valores reales en la base de datos, contados hoy:

```
'OV - OLIVAR'  x37   'TA - TIERRAS ARABLES' x34   'VI - VIÑEDO'  x24
''             x7    'TA-TIERRA ARABLE'     x6    'VO - VIÑEDO - OLIVAR' x3
'OV-OLIVAR'    x2    'VI-VIÑEDO'            x1    'FY - FRUTALES' x1
None           x1
```

Mismo uso escrito de tres formas (`'OV - OLIVAR'`, `'OV-OLIVAR'`), más vacíos y un NULL.
Así que **nunca se compara la cadena entera**: se extrae el código de dos letras del
principio y se compara eso. Un `startswith('OV')` mal hecho tampoco vale, porque no
distingue `'VO'` de `'VI'` si alguien cambia el formato.

Regla: `^\s*([A-Z]{2})\b` sobre el valor en mayúsculas. Lo que no case, no se propone.
Fallar hacia "no propongo nada" es lo correcto: un aviso de más es recuperable, una
declaración inventada en un documento legal no.

## Mapeo (constante en `helpers.py`, junto a `CULTIVOS_LENOSOS_IACS`)

| Código SIGPAC | Qué se hace |
|---|---|
| `OV` Olivar | Propone **Olivar** `1820` sin preguntar |
| `VI` Viñedo | **Pregunta**: vinificación `1711` o uva de mesa `1712` |
| `FY` Frutales | **Pregunta** la especie (almendro 1710, melocotonero 1720, ciruelo 1730, higuera 1750, nogal 1760, cerezo 1770, naranjo 1830, limonero 1840, pistachero 1740) |
| `VO` Viñedo-Olivar | **Pregunta** el reparto de superficie entre los dos cultivos |
| Cualquier otro (`TA`, vacío, NULL…) | No se toca. Ahí el cultivo cambia cada campaña |

## Backend

### 1. `helpers.py`
- `USO_SIGPAC_LENOSO`: dict `{'OV': '1820', 'VI': None, 'FY': None, 'VO': None}` — `None`
  significa "es leñoso pero hay que preguntar".
- `codigo_uso_sigpac(valor)`: extrae las dos letras. Devuelve `''` si no casa.
- Reutiliza `campana_activa()` y `es_cultivo_lenoso()`, que ya existen de la 014.

### 2. `GET /api/cultivos-campana/sugerencias` (nuevo, en `parcelas.py`)
Solo lectura. Devuelve las parcelas de la explotación activa, sin cultivo en la campaña
activa, cuyo uso SIGPAC sea leñoso, agrupadas por código:

```json
{"ok": true, "campana": "2025/2026", "grupos": [
  {"uso": "OV", "etiqueta": "Olivar", "propuesta": {"cultivo": "Olivar", "cod": "1820"},
   "necesita_pregunta": false,
   "parcelas": [{"id": 12, "nombre": "La Loma", "superficie_ha": 2.4}]},
  {"uso": "VI", "etiqueta": "Viñedo", "propuesta": null, "necesita_pregunta": true,
   "opciones": [{"cod": "1711", "nombre": "Viñedo vinificación"},
                {"cod": "1712", "nombre": "Viñedo uva de mesa"}],
   "parcelas": [...]}]}
```

### 3. `POST /api/cultivos-campana/declarar-lote` (nuevo)
Recibe **exactamente** qué declarar; el servidor no rellena huecos por su cuenta:

```json
{"campana": "2025/2026", "declaraciones": [
  {"parcela_id": 12, "cultivo_iacs_cod": "1820", "superficie_cultivada_ha": 2.4}]}
```

Validaciones, todas obligatorias:
- La campaña se **ignora si no coincide con la activa** de la explotación — misma lección
  que la 014: el cliente no elige en qué campaña se escribe.
- Cada `parcela_id` se comprueba contra `user_id` **y** `explotacion_id` en la MISMA
  consulta (lección 4 de la feature 013: lo crítico son las referencias cruzadas).
- El código IACS tiene que estar en el catálogo. Nada de texto libre.
- No pisa declaraciones existentes: si ya hay fila para esa parcela y campaña, se salta.
- La suma de superficies por parcela no puede pasar de su superficie (ya lo valida el POST
  de uno en uno; aquí se replica para el lote, que es lo que permite el 80/20 de la mixta).
- Devuelve cuántas se han creado y cuántas se han saltado, sin fallar entera por una.

## Frontend

En la pantalla de Parcelas, un aviso cuando haya sugerencias:

> **23 parcelas de olivar, viñedo y almendro sin cultivo declarado.**
> Según SIGPAC, 18 son olivar. ¿Lo confirmas?
> `[Confirmar los 18 olivares]` `[Revisar las 5 restantes]`

Las que necesitan pregunta se resuelven en un paso por grupo, no parcela a parcela. La
mixta (`VO`) pide el reparto con la superficie de la parcela delante.

Nada se escribe sin que ella pulse confirmar.

## Tests (antes del código, en rojo)

`backend/tests/test_lenosos_sigpac.py`:
1. `codigo_uso_sigpac` con los 10 valores reales de la BD, incluidos `''`, `None` y las
   tres variantes de formato.
2. `'VO - VIÑEDO - OLIVAR'` NO se confunde con `VI` ni con `OV`.
3. `TA` en cualquiera de sus dos formatos nunca se propone.
4. Las sugerencias no incluyen parcelas que ya tienen cultivo declarado.
5. Las sugerencias no cruzan explotación ni usuario.
6. `declarar-lote` rechaza una parcela de otra explotación **aunque el id exista**.
7. `declarar-lote` rechaza un código IACS que no esté en el catálogo.
8. `declarar-lote` es idempotente: repetirlo no duplica filas.
9. El 80/20 de la parcela mixta crea dos filas y respeta el límite de superficie.
10. Una campaña distinta de la activa no manda.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Declarar un cultivo equivocado en un documento legal | Solo `OV` se propone; el resto se pregunta. Nada sin confirmación |
| Un formato de `uso_sigpac` nuevo que no case | Se ignora y la parcela sigue pendiente. Nunca se adivina |
| Escribir en la explotación equivocada | Validación de `user_id` + `explotacion_id` en la misma consulta |
| Que el lote falle entero por una parcela mala | Se salta esa y se informa; no se aborta todo |
