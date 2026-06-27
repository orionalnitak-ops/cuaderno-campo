# NPK Fertilización — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Calcular automáticamente los kg/ha de N, P₂O₅ y K₂O aplicados a partir de la riqueza NPK y la dosis, guardarlos en BD y mostrarlos en tiempo real en el formulario.

**Architecture:** El backend añade 3 columnas a `fertilizacion`, parsea `riqueza_npk` en cada INSERT/UPDATE y almacena los valores calculados. El frontend muestra un preview en tiempo real mientras el usuario edita el formulario, usando el mismo algoritmo de parseo en JS.

**Tech Stack:** Python/Flask, SQLite (con patrón `_add_col` para migraciones), React (Babel standalone), fetch API.

---

## Task 1: Migración BD — columnas NPK

**Files:**
- Modify: `backend/db.py:370-377`

- [ ] **Step 1: Añadir las 3 columnas con `_add_col`**

En `backend/db.py`, dentro del bloque `for col, typ in [...]` de la tabla `fertilizacion` (líneas 370-377), añadir las 3 nuevas entradas **al final** de la lista:

```python
    for col, typ in [
        ('parcela_id', 'INTEGER'), ('parcela_etiqueta', 'TEXT'),
        ('fecha_aplicacion', 'TEXT'), ('producto', 'TEXT'), ('riqueza_npk', 'TEXT'),
        ('dosis_valor', 'REAL'), ('dosis_unidad', 'TEXT'), ('metodo_aplicacion', 'TEXT'),
        ('campana', 'TEXT'), ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ('deleted_at', 'TEXT'),
        ('n_aplicado', 'REAL'), ('p2o5_aplicado', 'REAL'), ('k2o_aplicado', 'REAL'),
    ]:
        _add_col(c, 'fertilizacion', col, typ)
```

- [ ] **Step 2: Verificar la migración**

Arrancar el servidor:
```bash
cd "h:\Proyectos\Cuaderno ex app\backend"
python app.py
```

Abrir otra terminal y verificar que las columnas existen:
```bash
cd "h:\Proyectos\Cuaderno ex app\backend"
python -c "import sqlite3; c=sqlite3.connect('cuaderno.db'); print([x[1] for x in c.execute('PRAGMA table_info(fertilizacion)')])"
```

Resultado esperado: lista que incluye `'n_aplicado'`, `'p2o5_aplicado'`, `'k2o_aplicado'`.

- [ ] **Step 3: Commit**

```bash
git add backend/db.py
git commit -m "feat: añadir columnas n_aplicado, p2o5_aplicado, k2o_aplicado a fertilizacion"
```

---

## Task 2: Backend — función `_calc_npk` y endpoints actualizados

**Files:**
- Modify: `backend/app.py:770-914`

- [ ] **Step 1: Añadir `_calc_npk` junto a `_validate_fertilizacion`**

Insertar la función justo **después** de `_validate_fertilizacion` (línea 787, antes del comentario `# ─────`):

```python
def _calc_npk(riqueza_npk, dosis_valor):
    """Parsea 'N-P-K' y devuelve (n, p, k) en kg/ha, o (None, None, None) si no parseable."""
    if not riqueza_npk or not dosis_valor:
        return None, None, None
    m = re.search(r'(\d+\.?\d*)[^\d]+(\d+\.?\d*)[^\d]+(\d+\.?\d*)', str(riqueza_npk))
    if not m:
        return None, None, None
    try:
        dosis = float(dosis_valor)
        n = round(float(m.group(1)) / 100 * dosis, 2)
        p = round(float(m.group(2)) / 100 * dosis, 2)
        k = round(float(m.group(3)) / 100 * dosis, 2)
        return n, p, k
    except (ValueError, TypeError):
        return None, None, None
```

Añadir `import re` en la línea 5 de `app.py`, justo después de los imports existentes (líneas 1-4):

```python
import os
import bcrypt
import requests as req_lib
import datetime
import re
```

(El `import re as _re` de la línea 1349 puede quedarse tal cual, no entra en conflicto.)

- [ ] **Step 2: Actualizar el POST de `/api/fertilizacion`**

Reemplazar el bloque INSERT de `manage_fertilizacion` (líneas 877-888) con:

```python
    n_ap, p_ap, k_ap = _calc_npk(data.get('riqueza_npk'), data.get('dosis_valor'))
    c = conn.cursor()
    c.execute('''
        INSERT INTO fertilizacion (
            user_id, parcela_id, parcela_etiqueta, fecha_aplicacion,
            tipo_fertilizante, producto, riqueza_npk,
            dosis_valor, dosis_unidad, metodo_aplicacion, notas, campana,
            n_aplicado, p2o5_aplicado, k2o_aplicado
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (uid, data.get('parcela_id'), data.get('parcela_etiqueta'), data.get('fecha_aplicacion'),
          data.get('tipo_fertilizante'), data.get('producto'), data.get('riqueza_npk'),
          data.get('dosis_valor') or None, data.get('dosis_unidad', 'kg/ha'),
          data.get('metodo_aplicacion'), data.get('notas'), data.get('campana', '2025/2026'),
          n_ap, p_ap, k_ap))
    conn.commit(); new_id = c.lastrowid; conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201
```

- [ ] **Step 3: Actualizar el PUT de `/api/fertilizacion/<fid>`**

Reemplazar el bloque UPDATE de `manage_fertilizacion_one` (líneas 909-914) con:

```python
    n_ap, p_ap, k_ap = _calc_npk(data.get('riqueza_npk'), data.get('dosis_valor'))
    fields = ['parcela_id','parcela_etiqueta','fecha_aplicacion','tipo_fertilizante',
              'producto','riqueza_npk','dosis_valor','dosis_unidad','metodo_aplicacion','notas','campana',
              'n_aplicado','p2o5_aplicado','k2o_aplicado']
    sets = ', '.join(f"{f}=?" for f in fields)
    values = []
    for f in fields:
        if f == 'dosis_valor':
            values.append(data.get(f) or None)
        elif f == 'n_aplicado':
            values.append(n_ap)
        elif f == 'p2o5_aplicado':
            values.append(p_ap)
        elif f == 'k2o_aplicado':
            values.append(k_ap)
        else:
            values.append(data.get(f))
    conn.execute(f"UPDATE fertilizacion SET {sets} WHERE id=? AND user_id=? AND deleted_at IS NULL",
                 values + [fid, uid])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
```

- [ ] **Step 4: Actualizar `_resumen` en el endpoint de historial**

Buscar la línea en `app.py` (alrededor de línea 509):
```python
'_resumen': f"{r.get('tipo_fertilizante','')} — {r.get('producto','')}"
```

Reemplazarla con:
```python
'_resumen': (
    f"{r.get('tipo_fertilizante','')} — {r.get('producto','')}"
    + (f" · N:{r['n_aplicado']} P:{r['p2o5_aplicado']} K:{r['k2o_aplicado']} kg/ha"
       if r.get('n_aplicado') is not None else '')
)
```

- [ ] **Step 5: Verificar manualmente**

Con el servidor corriendo, ejecutar:
```bash
curl -s -X POST http://127.0.0.1:5000/api/fertilizacion \
  -H "Content-Type: application/json" \
  -b "session=<cookie>" \
  -d '{"parcela_id":1,"fecha_aplicacion":"2026-06-02","tipo_fertilizante":"Mineral complejo","producto":"NPK","riqueza_npk":"20-10-10","dosis_valor":100,"campana":"2025/2026"}'
```

Verificar en BD que `n_aplicado=20.0`, `p2o5_aplicado=10.0`, `k2o_aplicado=10.0`.

Alternativamente: crear un abono desde la app y revisar en la consola de BD:
```bash
python -c "import sqlite3; c=sqlite3.connect('cuaderno.db'); print(list(c.execute('SELECT n_aplicado,p2o5_aplicado,k2o_aplicado FROM fertilizacion ORDER BY id DESC LIMIT 1')))"
```

- [ ] **Step 6: Commit**

```bash
git add backend/app.py
git commit -m "feat: calcular y guardar N/P2O5/K2O en fertilizacion (RD 934/2025)"
```

---

## Task 3: Frontend — preview NPK en tiempo real

**Files:**
- Modify: `frontend/screens_forms.jsx:453-485`

- [ ] **Step 1: Añadir función `calcNPK` en el componente `FormFertilizacion`**

Justo **antes** del `return (` del componente `FormFertilizacion` (línea 438), insertar:

```javascript
    const calcNPK = (riqueza, dosis) => {
        if (!riqueza || !dosis) return null;
        const m = riqueza.match(/(\d+\.?\d*)[^\d]+(\d+\.?\d*)[^\d]+(\d+\.?\d*)/);
        if (!m) return null;
        const d = parseFloat(dosis);
        if (isNaN(d) || d <= 0) return null;
        return {
            n:  Math.round(parseFloat(m[1]) / 100 * d * 100) / 100,
            p:  Math.round(parseFloat(m[2]) / 100 * d * 100) / 100,
            k:  Math.round(parseFloat(m[3]) / 100 * d * 100) / 100,
        };
    };
    const npkPreview = calcNPK(f.riqueza_npk, f.dosis_valor);
```

- [ ] **Step 2: Añadir el bloque de preview en el JSX**

Dentro de `<MasCampos>`, justo **después** del `<FieldGroup label="Dosis">` (tras el `</FieldGroup>` que cierra el campo Dosis, alrededor de línea 473), insertar:

```jsx
                    {npkPreview && (
                        <div style={{
                            gridColumn: '1 / -1',
                            background: 'linear-gradient(135deg, #f0f4ff, #e8edff)',
                            border: '1.5px solid #c7d2fe',
                            borderRadius: 'var(--radius-lg)',
                            padding: '10px 14px',
                            fontSize: '0.82rem',
                            color: '#3730a3',
                            fontWeight: 600,
                        }}>
                            🧪 Nutrientes calculados:&nbsp;
                            <span>N: {npkPreview.n} kg/ha</span>
                            <span style={{ margin: '0 8px', opacity: 0.4 }}>·</span>
                            <span>P₂O₅: {npkPreview.p} kg/ha</span>
                            <span style={{ margin: '0 8px', opacity: 0.4 }}>·</span>
                            <span>K₂O: {npkPreview.k} kg/ha</span>
                        </div>
                    )}
```

- [ ] **Step 3: Verificar en el navegador**

1. Abrir `http://127.0.0.1:5000`
2. Ir a Anotar → Abono
3. Abrir "Más campos"
4. Escribir "20-10-10" en Riqueza N-P-K y "100" en Dosis
5. Verificar que aparece el bloque azul: "🧪 Nutrientes calculados: N: 20 kg/ha · P₂O₅: 10 kg/ha · K₂O: 10 kg/ha"
6. Cambiar la dosis a "50" → debe actualizarse a N: 10, P: 5, K: 5
7. Borrar la riqueza → el bloque debe desaparecer

- [ ] **Step 4: Commit y push**

```bash
git add frontend/screens_forms.jsx
git commit -m "feat: preview NPK en tiempo real en formulario de fertilizacion"
git push origin main
```
