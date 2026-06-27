# Diseño: Módulo Plan de Abonado (RD 934/2025)

**Fecha:** 2026-06-02
**Motivación:** RD 934/2025 (modifica RD 1051/2022) obliga desde el 1 sept 2026 a incluir un Plan de Abonado como anexo al cuaderno de explotación para todas las explotaciones salvo ≤10 ha de secano/pastos para autoconsumo. Es un documento de **planificación previa** por cultivo y campaña, distinto al registro de fertilización evento a evento (ya implementado).

Existe `frontend/screens_abonado.jsx` con un formulario parcial y cálculo NPK, pero está huérfano (sin ruta API, sin tabla BD, sin integración en el FAB, con diseño Tailwind obsoleto). Esta implementación lo reemplaza completamente siguiendo el patrón `FormRiego`/`FormFertilizacion`.

---

## Base de datos

Nueva tabla `abonado` en `db.py`, usando los mismos helpers `_PK` y `_add_col`:

```sql
CREATE TABLE IF NOT EXISTS abonado (
    id          {_PK},
    user_id     INTEGER DEFAULT 2,
    parcela_id  INTEGER,
    parcela_etiqueta TEXT,
    cultivo     TEXT,
    cultivo_anterior TEXT,
    rendimiento_esperado_kg_ha REAL,
    n_necesario_kg_ha  REAL,
    p_necesario_kg_ha  REAL,
    k_necesario_kg_ha  REAL,
    fecha_preparacion  TEXT,
    datos_suelo        TEXT,
    abono_recomendado  TEXT,
    dosis_recomendada_kg_ha REAL,
    notas       TEXT,
    campana     TEXT DEFAULT '2025/2026',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at  TEXT
)
```

Posición en `init_db()`: justo después del bloque `# ── RIEGO ──` y antes del comentario `# ── LABORES ──`.

---

## Backend

### Validación

`_validate_abonado(data)` — exige:
- `parcela_id`: Parcela
- `cultivo`: Cultivo
- `cultivo_anterior`: Cultivo anterior
- `rendimiento_esperado_kg_ha`: Rendimiento esperado
- `fecha_preparacion`: Fecha de preparación
- `n_necesario_kg_ha`, `p_necesario_kg_ha`, `k_necesario_kg_ha`: los 3 valores NPK (calculados en frontend, enviados en el payload)

Comprueba que `fecha_preparacion` sea fecha ISO válida y no futura.

### Rutas CRUD

```
GET  /api/abonado              → lista por user_id + campana, sin soft-deleted
POST /api/abonado              → crea nuevo plan
GET  /api/abonado/<id>         → detalle
PUT  /api/abonado/<id>         → editar
DELETE /api/abonado/<id>       → soft delete (deleted_at = now)
```

Mismo patrón que `manage_riego` / `manage_riego_one`.

### Historial

En `/api/historial`, añadir bloque para `modulo in ('todos', 'abonado')`:

```python
rows = dicts(conn, "SELECT * FROM abonado WHERE user_id=? AND deleted_at IS NULL ORDER BY fecha_preparacion DESC", (uid,))
for r in apply_filters(rows, 'fecha_preparacion'):
    records.append({**r, '_modulo': 'abonado', '_fecha': r.get('fecha_preparacion', ''),
                    '_resumen': f"{r.get('cultivo','')} — N:{r.get('n_necesario_kg_ha','')} P:{r.get('p_necesario_kg_ha','')} K:{r.get('k_necesario_kg_ha','')} kg/ha"})
```

### Dashboard

En `/api/inicio`, añadir contador `total_abonado` junto a los otros.

---

## Frontend

### CSS — `index.html`

Nueva clase chip teal (diferenciada de fertilización violeta y riego azul):

```css
.chip-abonado { background: rgba(13,148,136,0.12); color: #0f766e; }
```

### FAB — `app.jsx`

Añadir a `MODULE_CARDS`:

```js
{ id: 'abonado', icon: '📋', title: 'Plan de abono', desc: 'Planificación NPK anual por parcela y cultivo.', bg: 'linear-gradient(135deg, #0f766e, #0d9488)' },
```

### Formulario — `screens_forms.jsx`

**`MODULE_CONFIG`:**
```js
abonado: { icon: '📋', title: 'Plan de abono', color: '#0d9488' },
```

**Dispatch en `ScreenForms`:**
```jsx
{modulo === 'abonado' && <FormAbonado parcelas={parcelas} record={record} campana={campana} onClose={onClose} isEdit={isEdit} />}
```

**Componente `FormAbonado`:**

Campos en orden:
1. `ParcelSelect` — Parcela * (auto-rellena superficie)
2. Grid 2 cols: Cultivo * | Cultivo anterior *
3. Grid 2 cols: Rendimiento esperado (kg/ha) * | Fecha de preparación *
4. Bloque NPK calculado en tiempo real (se recalcula al cambiar cultivo o rendimiento):
   - Muestra `N: X kg/ha · P₂O₅: Y kg/ha · K₂O: Z kg/ha`
   - Tabla de referencia por cultivo (misma lógica que `screens_abonado.jsx`, mejorada con viña)
5. `MasCampos` (opcionales):
   - Datos de suelo (textarea libre — "Análisis de suelo o descripción")
   - Abono recomendado (texto)
   - `ZoomInput` Dosis recomendada (kg/ha)
   - `ZoomInput` Notas

El cálculo NPK es automático (no requiere botón), se dispara con `React.useEffect` al cambiar `cultivo` o `rendimiento_esperado_kg_ha`. Los valores calculados se envían en el payload; el backend los valida pero no los recalcula.

**Tabla de referencia NPK (kg/ha) por cultivo — a incluir en `FormAbonado`:**

| Cultivo (includes) | N | P₂O₅ | K₂O |
|---|---|---|---|
| TRIGO | 120 | 60 | 60 |
| CEBADA | 100 | 50 | 50 |
| GIRASOL | 80 | 60 | 60 |
| MAÍZ | 150 | 80 | 100 |
| OLIVAR | 80 | 30 | 100 |
| VIÑA / VID | 40 | 30 | 60 |
| FRUTALES | 100 | 50 | 150 |
| YEROS / LEGUMINOSA / GUISANTE | 20 | 40 | 40 |
| BARBECHO | 0 | 0 | 0 |
| (resto) | 60 | 40 | 40 |

### Historial — `screens_history.jsx`

`MODULE_META`:
```js
abonado: { icon: '📋', label: 'Plan abono', chipClass: 'chip-abonado', accentColor: '#0f766e' },
```

`MODULE_PILLS`:
```js
['abonado', '📋 Plan abono'],
```

### Eliminar fichero obsoleto

```bash
git rm frontend/screens_abonado.jsx
```

---

## Fuera de alcance

- Firma digital del asesor (el RD la contempla para zonas vulnerables, pero el plazo es 1 año después de la obligación del plan — i.e., sept 2027 como mínimo).
- Cálculo NPK ajustado por análisis de suelo real (requeriría integrar laboratorios externos).
- Exportación del plan como documento PDF independiente (el PDF global ya incluirá la sección abonado via historial).
