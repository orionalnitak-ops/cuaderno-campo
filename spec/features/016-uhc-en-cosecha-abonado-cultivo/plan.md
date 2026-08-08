# 016 — Plan de implementación

Spec: `spec.md` (aprobada — la pide Lourdes). Reparto por superficie = decisión de Raúl.

---

## Gate de 5 preguntas (obligatorio, `second-brain/principios.md`)

1. **¿Tiene que existir?** Sí. Lourdes lo pide desde el uso real con 50+ parcelas; tres
   módulos la obligan a repetir el mismo registro parcela por parcela.
2. **¿Ya hay algo parecido?** Sí, y se reutiliza entero: `ParcelOrUhcSelect` en el front y
   `_parcelas_uhc()` + el patrón de fan-out en el back. **No se crea ningún componente ni
   helper nuevo de selección.**
3. **¿Lo resuelve la plataforma?** No.
4. **¿Alguna dependencia ya instalada?** No hace falta ninguna.
5. **¿Se puede más simple?** Lo simple sería replicar el registro tal cual en cada parcela,
   como hacen los 4 módulos existentes. No vale aquí: en Cosecha y Cultivo campaña hay
   cantidades absolutas y replicarlas escribe datos falsos. El reparto es el mínimo
   necesario, y solo se aplica a los 3 campos absolutos.

---

## Archivos que se tocan

| Archivo | Qué |
|---|---|
| `backend/blueprints/fertilizacion.py` | `_parcelas_uhc()`: añadir `p.superficie_ha` al SELECT · rama `uhc_id` en el POST de `/api/abonado` |
| `backend/helpers.py` | `repartir_por_superficie()` — nueva, única función nueva del backend |
| `backend/blueprints/labores.py` | rama `uhc_id` en el POST de `/api/cosecha` + plazo de seguridad del grupo |
| `backend/blueprints/parcelas.py` | rama `uhc_id` en el POST de `/api/cultivos-campana` |
| `frontend/screens_forms.jsx` | `FormCosecha`, `FormAbonado`, `FormCultivoCampana` |
| `backend/tests/test_uhc_cosecha_abonado_cultivo.py` | nuevo |

Ningún cambio de esquema: no se guarda `uhc_id`, se mantiene el fan-out.

---

## Fases

### Fase 1 — `repartir_por_superficie()` (backend/helpers.py)

```
repartir_por_superficie(total, parcelas) -> {parcela_id: cantidad}
```

- Reparte `total` proporcional a `superficie_ha`. La **última** parcela absorbe el
  redondeo, de forma que `sum(valores) == total` exacto (criterio 3).
- Si alguna parcela no tiene `superficie_ha` (o la suma es 0), reparte **a partes iguales**
  — no es correcto agronómicamente, pero es determinista y no inventa superficies; se
  documenta en el docstring.
- Redondeo a 2 decimales.
- Función pura, sin BD: se testea sola.

**Tests:** suma exacta con 3 y 7 parcelas, superficies desiguales, total 0, una parcela sin
superficie, todas sin superficie.

### Fase 2 — Plan de abonado (el fácil, valida el patrón)

En el POST de `/api/abonado`: rama `if data.get('uhc_id')` copiada de `fertilizacion.py:257`,
un INSERT por parcela con **los mismos valores** (todo es por ha). Devuelve
`{"status":"ok","count":N,"ids":[…]}` como Tratamientos.
En el front, `FormAbonado`: `modoUHC` + `uhcList` + `<ParcelOrUhcSelect>`, igual que
`FormFertilizacion` (líneas 684-782). Validación: `(!f.parcela_id && !f.uhc_id)` → error.

### Fase 3 — Cosecha

Backend, POST `/api/cosecha`, rama `uhc_id`:

1. `_parcelas_uhc()` → si vacío, 400 "El grupo UHC no existe o no tiene parcelas asignadas".
2. **Plazo de seguridad del grupo**: la consulta que hoy corre para una parcela
   (`labores.py:162`) pasa a `WHERE parcela_id IN (…)`. Si devuelve algo → **400, grupo
   entero rechazado**, nombrando parcelas y productos. Criterio 5.
3. `superficie_cosechada_ha` de cada fila = `superficie_ha` de esa parcela.
4. `produccion_total_valor` = `repartir_por_superficie(total, parcelas)`.
5. Resto de campos replicados. `rendimiento_kg_ha` lo sigue calculando el backend por fila.

Front, `FormCosecha`: toggle + en modo grupo, **previsualización del reparto** (tabla
parcela → kg) y la frase *"Reparto estimado según la superficie de cada parcela"* antes del
botón de guardar. Criterio 4. La preview se calcula en el cliente con las superficies que
ya devuelve `GET /api/uhc/<id>` (`uhc.py:108` las incluye); **la cifra que vale es la que
calcula el backend** — el cliente no manda cantidades ya repartidas.

### Fase 4 — Cultivo campaña

Backend, POST `/api/cultivos-campana`, rama `uhc_id`:

1. `_parcelas_uhc()` con `exp_id`.
2. Por parcela: si ya existe fila con ese `cultivo_iacs_cod` en la campaña → **saltar**,
   contar en `saltadas` (criterio 6, mismo criterio que la 015).
3. `superficie_cultivada_ha` = superficie de la parcela; `kg_sembrados` =
   `repartir_por_superficie()`.
4. La validación de superficie existente (`parcelas.py:341`) se aplica **por parcela**; si
   falla, se rechaza esa parcela con su motivo y se sigue. Respuesta tipo
   `declarar_cultivos_lote`: `{creadas, saltadas, rechazadas, motivos}`.

Front, `FormCultivoCampana`: toggle + precarga del `cultivo` del grupo. El código IACS se
pide una vez y es obligatorio (sin él, 400 — no se relaja para grupos).

### Fase 5 — Verificación

- `npm run build` en `frontend/` (obligatorio tras tocar JSX).
- Tests con `PYTHONIOENCODING=utf-8` (los `↔` revientan la consola de Windows).
- Prueba manual con copia real de producción: un grupo de Lourdes en los tres módulos,
  comprobando que la suma cuadra y que el aislamiento por explotación aguanta.

---

## Orden de commits

1. `feat: repartir_por_superficie() + tests`
2. `feat: grupos UHC en el plan de abonado`
3. `feat: grupos UHC en cosecha, con reparto por superficie`
4. `feat: grupos UHC en cultivo campaña`
5. `test: cobertura de las tres rutas con grupo`

Rama `feat/uhc-cosecha-abonado-cultivo` → PR → CI → merge. Nunca directo a `main`.

---

## Riesgos

- **Aislamiento por explotación (013).** Cada rama nueva es un fan-out: un filtro que falte
  escribe en la finca equivocada. `_parcelas_uhc()` ya comprueba grupo **y** parcelas contra
  `explotacion_id`; hay que llamarla **siempre con `exp_id`**, nunca sin él. Test explícito.
- **Añadir `superficie_ha` a `_parcelas_uhc()`** afecta a Tratamientos, Fertilización,
  Labores y Riego, que ya la usan. Es solo una columna más en el SELECT y ninguno hace
  `SELECT *` ni desempaqueta posicionalmente — verificar los 4 puntos de llamada igualmente.
- **El plazo de seguridad en grupo es más estricto que hoy**: una parcela bloqueada tumba el
  registro entero. Es deliberado (spec), pero hay que explicarlo bien en el mensaje de error
  o Lourdes no entenderá por qué no la deja guardar.
