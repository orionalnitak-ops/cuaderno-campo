# Módulo Riego — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir el módulo de Riego al FAB del CUE, con tabla propia en BD, CRUD en backend, formulario en el design system actual e integración en historial y dashboard.

**Architecture:** Misma estructura que `fertilizacion`: tabla SQLite con `_add_col`, rutas Flask `@login_required`, componente `FormRiego` dentro de `screens_forms.jsx`, entrada en `MODULE_CARDS` de `app.jsx` y en `MODULE_META` de `screens_history.jsx`. El fichero obsoleto `screens_riego.jsx` se elimina.

**Tech Stack:** Python/Flask, SQLite (`_PK`/`_add_col` pattern), React (Babel standalone), `ZoomInput`/`FieldGroup`/`MasCampos`/`ParcelSelect` components.

---

## Archivos modificados / creados

| Archivo | Acción |
|---|---|
| `backend/db.py` | Añadir tabla `riego` |
| `backend/app.py` | `_validate_riego`, rutas CRUD, historial, dashboard |
| `frontend/index.html` | CSS clase `.chip-riego` |
| `frontend/app.jsx` | Añadir `riego` a `MODULE_CARDS` |
| `frontend/screens_forms.jsx` | Añadir `riego` a `MODULE_CONFIG` + componente `FormRiego` |
| `frontend/screens_history.jsx` | Añadir `riego` a `MODULE_META` y `MODULE_PILLS` |
| `frontend/screens_riego.jsx` | **Borrar** |

---

## Task 1: Tabla BD `riego`

**Files:**
- Modify: `backend/db.py` (justo antes del comentario `# ── LABORES ──`, línea ~379)

- [ ] **Step 1: Insertar la tabla `riego` en `init_db()`**

Añadir este bloque justo **antes** del comentario `# ── LABORES ──` (línea 380 aprox):

```python
    # ── RIEGO ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS riego (
            id {_PK},
            user_id INTEGER DEFAULT 2,
            parcela_id INTEGER,
            parcela_etiqueta TEXT,
            fecha TEXT,
            tipo_riego TEXT,
            volumen_m3 REAL,
            horas_riego REAL,
            fuente_agua TEXT,
            notas TEXT,
            campana TEXT DEFAULT '2025/2026',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    ''')
```

- [ ] **Step 2: Verificar la tabla**

```bash
cd "h:\Proyectos\Cuaderno ex app\backend"
python -c "from db import init_db; import sqlite3; init_db(); c=sqlite3.connect('cuaderno.db'); print([x[1] for x in c.execute('PRAGMA table_info(riego)')])"
```

Resultado esperado: lista que incluye `'fecha'`, `'tipo_riego'`, `'volumen_m3'`.

- [ ] **Step 3: Commit**

```bash
git add backend/db.py
git commit -m "feat: crear tabla riego en BD"
```

---

## Task 2: Backend — validación, CRUD, historial, dashboard

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: Añadir `_validate_riego` justo después de `_calc_npk` (línea ~808)**

```python
def _validate_riego(data):
    """Valida campos obligatorios del registro de riego (RD 934/2025).
    Requiere fecha, parcela, tipo y al menos horas o m³ (UX agrícola: no todos tienen contador)."""
    required = {
        'fecha':      'Fecha de riego',
        'parcela_id': 'Parcela',
        'tipo_riego': 'Tipo de riego',
    }
    missing = [label for field, label in required.items() if not data.get(field)]
    if missing:
        return f"Campos obligatorios: {', '.join(missing)}"
    if not data.get('horas_riego') and not data.get('volumen_m3'):
        return "Indica al menos las horas de riego o el volumen en m³"
    try:
        fecha = datetime.date.fromisoformat(str(data['fecha']))
        if fecha > datetime.date.today():
            return "La fecha de riego no puede ser futura"
    except (ValueError, TypeError):
        return "Fecha con formato inválido (use YYYY-MM-DD)"
    return None
```

- [ ] **Step 2: Añadir las rutas CRUD justo después de `manage_fertilizacion_one` (línea ~944)**

```python
# ─────────────────────────────────────────────
# RIEGO
# ─────────────────────────────────────────────
@app.route('/api/riego', methods=['GET', 'POST'])
@login_required
def manage_riego():
    uid = get_uid()
    conn = get_db()
    if request.method == 'GET':
        campana = request.args.get('campana', '2025/2026')
        rows = dicts(conn, "SELECT * FROM riego WHERE user_id=? AND campana=? AND deleted_at IS NULL ORDER BY fecha DESC", (uid, campana))
        conn.close(); return jsonify(rows)

    data = request.json or {}
    err = _validate_riego(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400

    c = conn.cursor()
    c.execute('''
        INSERT INTO riego (
            user_id, parcela_id, parcela_etiqueta, fecha,
            tipo_riego, volumen_m3, horas_riego, fuente_agua, notas, campana
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
    ''', (uid, data.get('parcela_id'), data.get('parcela_etiqueta'), data.get('fecha'),
          data.get('tipo_riego'), data.get('volumen_m3') or None,
          data.get('horas_riego') or None, data.get('fuente_agua'), data.get('notas'),
          data.get('campana', '2025/2026')))
    conn.commit(); new_id = c.lastrowid; conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@app.route('/api/riego/<int:rid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_riego_one(rid):
    uid = get_uid()
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute(
            "UPDATE riego SET deleted_at=datetime('now') WHERE id=? AND user_id=?",
            (rid, uid))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM riego WHERE id=? AND user_id=? AND deleted_at IS NULL", (rid, uid))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_riego(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    fields = ['parcela_id','parcela_etiqueta','fecha','tipo_riego','volumen_m3',
              'horas_riego','fuente_agua','notas','campana']
    sets = ', '.join(f"{f}=?" for f in fields)
    numeric = {'volumen_m3', 'horas_riego'}
    values = [data.get(f) or None if f in numeric else data.get(f) for f in fields]
    conn.execute(f"UPDATE riego SET {sets} WHERE id=? AND user_id=? AND deleted_at IS NULL",
                 values + [rid, uid])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
```

- [ ] **Step 3: Añadir riego al historial**

Buscar el bloque que termina con compras en `/api/historial` (línea ~534) y añadir **antes** del `records.sort(...)`:

```python
    if modulo in ('todos', 'riego'):
        rows = dicts(conn, "SELECT * FROM riego WHERE user_id=? AND deleted_at IS NULL ORDER BY fecha DESC", (uid,))
        for r in apply_filters(rows, 'fecha'):
            records.append({**r, '_modulo': 'riego', '_fecha': r.get('fecha', ''),
                            '_resumen': f"{r.get('tipo_riego','')} — {r.get('volumen_m3','')} m³"})
```

- [ ] **Step 4: Añadir contador de riego al dashboard**

En `/api/inicio` (línea ~435), añadir junto a los otros contadores:

```python
    r_count = one(conn, "SELECT COUNT(*) as n FROM riego WHERE user_id=? AND campana=?", (uid, campana))
```

Y añadir al `return jsonify({...})` (línea ~458):

```python
        "total_riego": r_count['n'] if r_count else 0,
```

También añadir `riego` a la query de días sin registro (línea ~442):

```python
    last_row = one(conn, """
        SELECT MAX(fecha) as last_fecha FROM (
            SELECT fecha_aplicacion as fecha FROM tratamientos WHERE user_id=?
            UNION ALL SELECT fecha FROM labores WHERE user_id=?
            UNION ALL SELECT fecha_aplicacion as fecha FROM fertilizacion WHERE user_id=?
            UNION ALL SELECT fecha FROM riego WHERE user_id=?
        )
    """, (uid, uid, uid, uid))
```

- [ ] **Step 5: Verificar que el servidor arranca sin errores**

```bash
cd "h:\Proyectos\Cuaderno ex app\backend"
python -c "import app; print('OK')"
```

Resultado esperado: `OK` (con el aviso de SECRET_KEY que es normal).

- [ ] **Step 6: Commit**

```bash
git add backend/app.py
git commit -m "feat: rutas CRUD riego + historial + dashboard (RD 934/2025)"
```

---

## Task 3: Frontend — CSS, FAB, formulario, historial

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.jsx`
- Modify: `frontend/screens_forms.jsx`
- Modify: `frontend/screens_history.jsx`
- Delete: `frontend/screens_riego.jsx`

- [ ] **Step 1: Añadir `.chip-riego` en `index.html`**

Buscar las líneas de chips (línea ~551):
```css
.chip-tratamiento   { background: rgba(0,105,76,0.12);   color: #00694c; }
.chip-fertilizacion { background: rgba(79,70,229,0.12);  color: #4f46e5; }
.chip-labor         { background: rgba(30,58,95,0.12);   color: #1e3a5f; }
.chip-cosecha       { background: rgba(219,39,119,0.12); color: #be185d; }
```

Añadir **debajo**:
```css
.chip-riego         { background: rgba(14,165,233,0.12); color: #0369a1; }
```

- [ ] **Step 2: Añadir `riego` a `MODULE_CARDS` en `app.jsx`**

Buscar `MODULE_CARDS` (línea 12) y añadir al final del array:

```js
{ id: 'riego', icon: '💧', title: 'Riego', desc: 'Aplicación de agua por parcela y campaña.', bg: 'linear-gradient(135deg, #0369a1, #0ea5e9)' },
```

- [ ] **Step 3: Añadir `riego` a `MODULE_CONFIG` en `screens_forms.jsx`**

Buscar `MODULE_CONFIG` (línea ~136) y añadir al objeto:

```js
riego:         { icon: '💧', title: 'Riego',                  color: '#0ea5e9' },
```

- [ ] **Step 4: Añadir la línea de dispatch en `ScreenForms` en `screens_forms.jsx`**

Buscar el bloque de dispatch de formularios (línea ~157-161):
```jsx
{modulo === 'tratamiento'   && <FormTratamiento   ... />}
{modulo === 'fertilizacion' && <FormFertilizacion ... />}
{modulo === 'labor'         && <FormLabor         ... />}
{modulo === 'cosecha'       && <FormCosecha       ... />}
{modulo === 'compra'        && <FormCompra        ... />}
```

Añadir **al final**:
```jsx
{modulo === 'riego'         && <FormRiego         parcelas={parcelas} record={record} campana={campana} onClose={onClose} isEdit={isEdit} />}
```

- [ ] **Step 5: Añadir el componente `FormRiego` en `screens_forms.jsx`**

Añadir al final del archivo (antes del último `</script>` si lo hubiera, o simplemente al final):

```jsx
function FormRiego({ parcelas, record, campana, onClose, isEdit }) {
    const today = new Date().toISOString().split('T')[0];
    const [saving, setSaving] = React.useState(false);
    const [f, setF] = React.useState({
        parcela_id:      record?.parcela_id      || '',
        parcela_etiqueta: record?.parcela_etiqueta || '',
        fecha:           record?.fecha            || today,
        tipo_riego:      record?.tipo_riego       || '',
        volumen_m3:      record?.volumen_m3       || '',
        horas_riego:     record?.horas_riego      || '',
        fuente_agua:     record?.fuente_agua      || '',
        notas:           record?.notas            || '',
        campana,
    });
    const set = (k, v) => setF(x => ({ ...x, [k]: v }));

    React.useEffect(() => {
        if (!f.parcela_id) return;
        const p = parcelas.find(x => String(x.id) === String(f.parcela_id));
        if (p) set('parcela_etiqueta', p.nombre_finca);
    }, [f.parcela_id]);

    const save = async () => {
        if (!f.parcela_id || !f.fecha || !f.tipo_riego) {
            alert('Rellena: parcela, fecha y tipo de riego'); return;
        }
        if (!f.horas_riego && !f.volumen_m3) {
            alert('Indica al menos las horas de riego o el volumen en m³'); return;
        }
        setSaving(true);
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `/api/riego/${record.id}` : '/api/riego';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar'); setSaving(false); return; }
        onClose('✅ Riego guardado');
    };

    return (
        <div>
            <FieldGroup label="Parcela *">
                <ParcelSelect parcelas={parcelas} value={f.parcela_id} onChange={v => set('parcela_id', v)} />
            </FieldGroup>
            <div className="responsive-grid cols-2">
                <FieldGroup label="Fecha *">
                    <input type="date" className="input-field" value={f.fecha} onChange={e => set('fecha', e.target.value)} />
                </FieldGroup>
                <FieldGroup label="Tipo de riego *">
                    <select className="input-field" value={f.tipo_riego} onChange={e => set('tipo_riego', e.target.value)}>
                        <option value="">Seleccionar…</option>
                        {['Aspersión', 'Goteo', 'Gravedad', 'Pivot', 'Otro'].map(t => <option key={t}>{t}</option>)}
                    </select>
                </FieldGroup>
            </div>
            <div className="responsive-grid cols-2">
                <FieldGroup label="Horas de riego">
                    <ZoomInput label="Horas" value={f.horas_riego} placeholder="4.5" inputMode="decimal"
                        onConfirm={v => set('horas_riego', v)} />
                </FieldGroup>
                <FieldGroup label="Volumen (m³)">
                    <ZoomInput label="Volumen (m³)" value={f.volumen_m3} placeholder="150" inputMode="decimal"
                        onConfirm={v => set('volumen_m3', v)} />
                </FieldGroup>
            </div>
            <p style={{ fontSize: '0.74rem', color: 'var(--on-surface-variant)', margin: '-8px 0 12px', padding: '0 2px' }}>
                Rellena al menos uno de los dos campos de arriba.
            </p>

            <MasCampos>
                <FieldGroup label="Fuente de agua">
                    <select className="input-field" value={f.fuente_agua} onChange={e => set('fuente_agua', e.target.value)}>
                        <option value="">Seleccionar…</option>
                        {['Balsa', 'Comunidad de regantes', 'Pozo propio', 'Río', 'Otro'].map(s => <option key={s}>{s}</option>)}
                    </select>
                </FieldGroup>
                <FieldGroup label="Notas">
                    <ZoomInput label="Notas" value={f.notas} placeholder="Observaciones…"
                        multiline onConfirm={v => set('notas', v)} />
                </FieldGroup>
            </MasCampos>

            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <button className="btn-ghost" onClick={() => onClose()} style={{ flex: 1 }}>Cancelar</button>
                <button className="btn-primary" onClick={save} disabled={saving} style={{ flex: 2 }}>
                    {saving ? 'Guardando…' : (isEdit ? 'Guardar cambios' : '💧 Guardar riego')}
                </button>
            </div>
        </div>
    );
}
```

- [ ] **Step 6: Actualizar `screens_history.jsx`**

Añadir `riego` a `MODULE_META` (línea ~20):
```js
riego:         { icon: '💧', label: 'Riego',          chipClass: 'chip-riego',         accentColor: '#0369a1' },
```

Añadir `riego` a `MODULE_PILLS` (línea ~28):
```js
['riego', '💧 Riego'],
```

- [ ] **Step 7: Borrar `screens_riego.jsx`**

```bash
cd "h:\Proyectos\Cuaderno ex app"
git rm frontend/screens_riego.jsx
```

- [ ] **Step 8: Verificar en navegador**

1. Arrancar servidor: `cd backend && python app.py`
2. Abrir `http://127.0.0.1:5000`
3. Pulsar FAB ✏️ → debe aparecer la tarjeta "💧 Riego"
4. Abrir el formulario → rellenar parcela, fecha, tipo, volumen → guardar → debe aparecer "✅ Riego guardado"
5. Ir a Historial → el registro debe aparecer con chip azul "RIEGO" y resumen "Goteo — 150 m³"

- [ ] **Step 9: Commit y push**

```bash
git add frontend/index.html frontend/app.jsx frontend/screens_forms.jsx frontend/screens_history.jsx
git commit -m "feat: modulo riego en FAB — formulario, historial y dashboard (RD 934/2025)"
git push origin main
```
