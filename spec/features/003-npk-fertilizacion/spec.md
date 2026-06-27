# Diseño: Cálculo automático NPK en módulo de fertilización

**Fecha:** 2026-06-02
**Motivación:** RD 934/2025 obliga desde el 1 enero 2026 a registrar los kg/ha de N, P₂O₅ y K₂O realmente aplicados en cada operación de fertilización.

---

## Base de datos

Tres columnas nuevas en la tabla `fertilizacion`, añadidas con `_add_col` (migración no destructiva):

```
n_aplicado    REAL   -- kg/ha de N
p2o5_aplicado REAL   -- kg/ha de P₂O₅
k2o_aplicado  REAL   -- kg/ha de K₂O
```

Registros existentes quedan con NULL hasta que el usuario los edite. No hay campo obligatorio nuevo en el formulario: los valores son siempre calculados.

---

## Backend

Función auxiliar `_calc_npk(riqueza_npk, dosis_valor)`:
- Parsea `riqueza_npk` con regex `(\d+\.?\d*)[^\d]+(\d+\.?\d*)[^\d]+(\d+\.?\d*)` para extraer los tres porcentajes.
- Calcula: `n = (n_pct/100) × dosis_valor`, igual para P y K.
- Devuelve `(None, None, None)` si la cadena no es parseable o falta la dosis.
- Resultado redondeado a 2 decimales.

Los endpoints POST y PUT de `/api/fertilizacion` llaman a `_calc_npk` antes de escribir en BD y guardan los 3 valores. El GET no necesita cambios (devuelve todas las columnas de la tabla).

---

## Frontend

### Formulario (tiempo real)
- Cuando `riqueza_npk` y `dosis_valor` están rellenos, aparece un bloque "🧪 Nutrientes calculados" debajo del campo de dosis.
- Muestra: `N: X kg/ha · P₂O₅: Y kg/ha · K₂O: Z kg/ha`
- Mismo regex que backend, calculado en JS en cada keystroke.
- Si la riqueza no es parseable, el bloque no aparece (sin error visible).

### Historial
- Las tarjetas de fertilización muestran los 3 valores si `n_aplicado` no es null (registros nuevos o editados).

---

## Fuera de alcance
- Plan de abonado (se diseñará en sprint independiente).
- Módulo de riego (siguiente sprint tras este).
- Validación de que N aplicado ≤ límite de zona vulnerable (requiere datos externos).
