# Plan de Abonado — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir el módulo Plan de Abonado al CUE, con tabla BD, CRUD backend, formulario en el design system actual, integración en FAB e historial, y eliminación del fichero obsoleto `screens_abonado.jsx`.

**Architecture:** Misma estructura que `riego`: tabla SQLite con `_PK`/`_add_col`, rutas Flask `@login_required`, componente `FormAbonado` dentro de `screens_forms.jsx`, entrada en `MODULE_CARDS` de `app.jsx` y en `MODULE_META`/`MODULE_PILLS` de `screens_history.jsx`. El fichero obsoleto `screens_abonado.jsx` (huérfano, diseño Tailwind) se elimina.

**Tech Stack:** Python/Flask, SQLite (`_PK`/`_add_col` pattern), React (Babel standalone), componentes `ZoomInput`/`FieldGroup`/`MasCampos`/`ParcelSelect` del design system "Surco Moderno".

---

## Archivos modificados / creados

| Archivo | Acción |
|---|---|
| `backend/db.py` | Añadir tabla `abonado` |
| `backend/app.py` | `_validate_abonado`, rutas CRUD, historial, dashboard |
| `frontend/index.html` | CSS clase `.chip-abonado` |
| `frontend/app.jsx` | Añadir `abonado` a `MODULE_CARDS` |
| `frontend/screens_forms.jsx` | Añadir `abonado` a `MODULE_CONFIG` + dispatch + componente `FormAbonado` |
| `frontend/screens_history.jsx` | Añadir `abonado` a `MODULE_META` y `MODULE_PILLS` |
| `frontend/screens_abonado.jsx` | **Borrar** |

---

## Task 1: Tabla BD `abonado`

**Files:**
- Modify: `backend/db.py` (línea 399, justo después del bloque `# ── RIEGO ──` y antes de `# ── LABORES ──`)

- [ ] **Step 1: Insertar la tabla `abonado` en `init_db()`**

Localizar el bloque `# ── RIEGO ──` (línea ~380) que termina en la línea 399 con `    ''')`  y el comentario `# ── LABORES ──` en línea 400. Insertar el nuevo bloque **entre** esas dos líneas:

```python
    # ── ABONADO ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS abonado (
            id {_PK},
            user_id INTEGER DEFAULT 2,
            parcela_id INTEGER,
            parcela_etiqueta TEXT,
            cultivo TEXT,
            cultivo_anterior TEXT,
            rendimiento_esperado_kg_ha REAL,
            n_necesario_kg_ha REAL,
            p_necesario_kg_ha REAL,
            k_necesario_kg_ha REAL,
            fecha_preparacion TEXT,
            datos_suelo TEXT,
            abono_recomendado TEXT,
            dosis_recomendada_kg_ha REAL,
            notas TEXT,
            campana TEXT DEFAULT '2025/2026',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    ''')
```

El resultado debe quedar:
```
    ''')   ← cierre del CREATE TABLE riego

    # ── ABONADO ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS abonado (
        ...
        )
    ''')

    # ── LABORES ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS labores (
```

- [ ] **Step 2: Verificar que la tabla se crea correctamente**

```bash
cd "h:\Proyectos\Cuaderno ex app\backend"
python -c "from db import init_db; import sqlite3; init_db(); c=sqlite3.connect('cuaderno.db'); print([x[1] for x in c.execute('PRAGMA table_info(abonado)')])"
```

Resultado esperado: lista que incluye `'cultivo'`, `'cultivo_anterior'`, `'n_necesario_kg_ha'`, `'fecha_preparacion'`.

- [ ] **Step 3: Commit**

```bash
git add backend/db.py
git commit -m "feat: crear tabla abonado en BD (RD 934/2025)"
```

---

## Task 2: Backend — validación, CRUD, historial, dashboard

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: Añadir `_validate_abonado` justo después de `_validate_riego` (línea ~841)**

Buscar la línea `    return None` que cierra `_validate_riego` y el comentario `# ───` que viene después. Insertar **a continuación**:

```python
def _validate_abonado(data):
    required = {
        'parcela_id':               'Parcela',
        'cultivo':                  'Cultivo',
        'cultivo_anterior':         'Cultivo anterior',
        'rendimiento_esperado_kg_ha': 'Rendimiento esperado',
        'fecha_preparacion':        'Fecha de preparación',
        'n_necesario_kg_ha':        'N necesario',
        'p_necesario_kg_ha':        'P necesario',
        'k_necesario_kg_ha':        'K necesario',
    }
    missing = [label for field, label in required.items() if not str(data.get(field, '')).strip()]
    if missing:
        return f"Campos obligatorios: {', '.join(missing)}"
    try:
        fecha = datetime.date.fromisoformat(str(data['fecha_preparacion']))
        if fecha > datetime.date.today():
            return "La fecha de preparación no puede ser futura"
    except (ValueError, TypeError):
        return "Fecha con formato inválido (use YYYY-MM-DD)"
    return None
```

- [ ] **Step 2: Añadir las rutas CRUD justo después de `manage_riego_one` (línea ~1038)**

Buscar la función `manage_riego_one` y añadir **a continuación**:

```python
# ─────────────────────────────────────────────
# PLAN DE ABONADO
# ─────────────────────────────────────────────
@app.route('/api/abonado', methods=['GET', 'POST'])
@login_required
def manage_abonado():
    uid = get_uid()
    conn = get_db()
    if request.method == 'GET':
        campana = request.args.get('campana', '2025/2026')
        rows = dicts(conn, "SELECT * FROM abonado WHERE user_id=? AND campana=? AND deleted_at IS NULL ORDER BY fecha_preparacion DESC", (uid, campana))
        conn.close(); return jsonify(rows)

    data = request.json or {}
    err = _validate_abonado(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400

    c = conn.cursor()
    c.execute('''
        INSERT INTO abonado (
            user_id, parcela_id, parcela_etiqueta, cultivo, cultivo_anterior,
            rendimiento_esperado_kg_ha, n_necesario_kg_ha, p_necesario_kg_ha,
            k_necesario_kg_ha, fecha_preparacion, datos_suelo,
            abono_recomendado, dosis_recomendada_kg_ha, notas, campana
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (uid, data.get('parcela_id'), data.get('parcela_etiqueta'),
          data.get('cultivo'), data.get('cultivo_anterior'),
          data.get('rendimiento_esperado_kg_ha') or None,
          data.get('n_necesario_kg_ha'), data.get('p_necesario_kg_ha'), data.get('k_necesario_kg_ha'),
          data.get('fecha_preparacion'), data.get('datos_suelo'),
          data.get('abono_recomendado'), data.get('dosis_recomendada_kg_ha') or None,
          data.get('notas'), data.get('campana', '2025/2026')))
    conn.commit(); new_id = c.lastrowid; conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@app.route('/api/abonado/<int:aid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_abonado_one(aid):
    uid = get_uid()
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute(
            "UPDATE abonado SET deleted_at=datetime('now') WHERE id=? AND user_id=?",
            (aid, uid))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM abonado WHERE id=? AND user_id=? AND deleted_at IS NULL", (aid, uid))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_abonado(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    fields = ['parcela_id', 'parcela_etiqueta', 'cultivo', 'cultivo_anterior',
              'rendimiento_esperado_kg_ha', 'n_necesario_kg_ha', 'p_necesario_kg_ha',
              'k_necesario_kg_ha', 'fecha_preparacion', 'datos_suelo',
              'abono_recomendado', 'dosis_recomendada_kg_ha', 'notas', 'campana']
    numeric = {'rendimiento_esperado_kg_ha', 'n_necesario_kg_ha', 'p_necesario_kg_ha',
               'k_necesario_kg_ha', 'dosis_recomendada_kg_ha'}
    sets = ', '.join(f"{f}=?" for f in fields)
    values = [data.get(f) or None if f in numeric else data.get(f) for f in fields]
    conn.execute(f"UPDATE abonado SET {sets} WHERE id=? AND user_id=? AND deleted_at IS NULL",
                 values + [aid, uid])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
```

- [ ] **Step 3: Añadir abonado al historial**

En `/api/historial` (línea ~539), buscar el bloque de `riego` que termina con:
```python
    records.sort(key=lambda x: x.get('_fecha', '') or '', reverse=True)
```

Añadir **justo antes** de ese `records.sort(...)`:

```python
    if modulo in ('todos', 'abonado'):
        rows = dicts(conn, "SELECT * FROM abonado WHERE user_id=? AND deleted_at IS NULL ORDER BY fecha_preparacion DESC", (uid,))
        for r in apply_filters(rows, 'fecha_preparacion'):
            records.append({**r, '_modulo': 'abonado', '_fecha': r.get('fecha_preparacion', ''),
                            '_resumen': f"{r.get('cultivo','')} — N:{r.get('n_necesario_kg_ha','')} P:{r.get('p_necesario_kg_ha','')} K:{r.get('k_necesario_kg_ha','')} kg/ha"})
```

- [ ] **Step 4: Añadir contador de abonado al dashboard**

En `/api/inicio` (línea ~436), buscar:
```python
    r_count = one(conn, "SELECT COUNT(*) as n FROM riego WHERE user_id=? AND campana=? AND deleted_at IS NULL", (uid, campana))
```

Añadir **a continuación**:
```python
    a_count = one(conn, "SELECT COUNT(*) as n FROM abonado WHERE user_id=? AND campana=? AND deleted_at IS NULL", (uid, campana))
```

Y en el `return jsonify({...})` (línea ~467), añadir junto a `"total_riego"`:
```python
        "total_abonado": a_count['n'] if a_count else 0,
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
git commit -m "feat: rutas CRUD abonado + historial + dashboard (RD 934/2025)"
```

---

## Task 3: Frontend — CSS, FAB, formulario, historial, borrar obsoleto

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.jsx`
- Modify: `frontend/screens_forms.jsx`
- Modify: `frontend/screens_history.jsx`
- Delete: `frontend/screens_abonado.jsx`

- [ ] **Step 1: Añadir `.chip-abonado` en `index.html`**

Buscar la línea (línea 555):
```css
    .chip-riego         { background: rgba(14,165,233,0.12);  color: #0369a1; }
```

Añadir **debajo**:
```css
    .chip-abonado       { background: rgba(13,148,136,0.12); color: #0f766e; }
```

- [ ] **Step 2: Añadir `abonado` a `MODULE_CARDS` en `app.jsx`**

Buscar `MODULE_CARDS` (línea 12) y la entrada de `riego` (línea 18):
```js
    { id: 'riego', icon: '💧', title: 'Riego', desc: 'Aplicación de agua por parcela y campaña.', bg: 'linear-gradient(135deg, #0369a1, #0ea5e9)' },
```

Añadir **a continuación**:
```js
    { id: 'abonado', icon: '📋', title: 'Plan de abono', desc: 'Planificación NPK anual por parcela y cultivo (RD 934/2025).', bg: 'linear-gradient(135deg, #0f766e, #0d9488)' },
```

- [ ] **Step 3: Añadir `abonado` a `MODULE_CONFIG` en `screens_forms.jsx`**

Buscar `MODULE_CONFIG` (línea ~136) y la entrada de `riego` (línea 142):
```js
        riego:         { icon: '💧', title: 'Riego',                    color: '#0ea5e9' },
```

Añadir **a continuación**:
```js
        abonado:       { icon: '📋', title: 'Plan de abono',            color: '#0d9488' },
```

- [ ] **Step 4: Añadir dispatch de `FormAbonado` en `ScreenForms`**

Buscar la línea (línea ~163):
```jsx
                {modulo === 'riego'         && <FormRiego         parcelas={parcelas} record={record} campana={campana} onClose={onClose} isEdit={isEdit} />}
```

Añadir **a continuación**:
```jsx
                {modulo === 'abonado'       && <FormAbonado       parcelas={parcelas} record={record} campana={campana} onClose={onClose} isEdit={isEdit} />}
```

- [ ] **Step 5: Añadir el componente `FormAbonado` al final de `screens_forms.jsx`**

Añadir al final del archivo:

```jsx
function calcNpkAbonado(cultivo) {
    const c = (cultivo || '').toUpperCase();
    if (c.includes('TRIGO'))                                                        return { n: 120, p: 60,  k: 60  };
    if (c.includes('CEBADA'))                                                       return { n: 100, p: 50,  k: 50  };
    if (c.includes('GIRASOL'))                                                      return { n: 80,  p: 60,  k: 60  };
    if (c.includes('MAÍZ') || c.includes('MAIZ'))                                  return { n: 150, p: 80,  k: 100 };
    if (c.includes('OLIVAR'))                                                       return { n: 80,  p: 30,  k: 100 };
    if (c.includes('VIÑA') || c.includes('VID') || c.includes('VIÑEDO'))           return { n: 40,  p: 30,  k: 60  };
    if (c.includes('FRUTALES') || c.includes('FRUTAL'))                            return { n: 100, p: 50,  k: 150 };
    if (c.includes('YEROS') || c.includes('LEGUMINOSA') || c.includes('GUISANTE')
        || c.includes('GARBANZO') || c.includes('LENTEJA'))                        return { n: 20,  p: 40,  k: 40  };
    if (c.includes('BARBECHO'))                                                     return { n: 0,   p: 0,   k: 0   };
    return { n: 60, p: 40, k: 40 };
}

function FormAbonado({ parcelas, record, campana, onClose, isEdit }) {
    const today = new Date().toISOString().split('T')[0];
    const [saving, setSaving] = React.useState(false);
    const [f, setF] = React.useState({
        parcela_id:                  record?.parcela_id                  || '',
        parcela_etiqueta:            record?.parcela_etiqueta            || '',
        cultivo:                     record?.cultivo                     || '',
        cultivo_anterior:            record?.cultivo_anterior            || '',
        rendimiento_esperado_kg_ha:  record?.rendimiento_esperado_kg_ha  || '',
        fecha_preparacion:           record?.fecha_preparacion           || today,
        n_necesario_kg_ha:           record?.n_necesario_kg_ha           || '',
        p_necesario_kg_ha:           record?.p_necesario_kg_ha           || '',
        k_necesario_kg_ha:           record?.k_necesario_kg_ha           || '',
        datos_suelo:                 record?.datos_suelo                 || '',
        abono_recomendado:           record?.abono_recomendado           || '',
        dosis_recomendada_kg_ha:     record?.dosis_recomendada_kg_ha     || '',
        notas:                       record?.notas                       || '',
        campana,
    });
    const set = (k, v) => setF(x => ({ ...x, [k]: v }));

    // Sincronizar parcela_etiqueta al seleccionar parcela
    React.useEffect(() => {
        if (!f.parcela_id) return;
        const p = parcelas.find(x => String(x.id) === String(f.parcela_id));
        if (p) set('parcela_etiqueta', p.nombre_finca);
    }, [f.parcela_id]);

    // Recalcular NPK cuando cambia el cultivo
    React.useEffect(() => {
        if (!f.cultivo) return;
        const { n, p, k } = calcNpkAbonado(f.cultivo);
        setF(x => ({ ...x, n_necesario_kg_ha: n, p_necesario_kg_ha: p, k_necesario_kg_ha: k }));
    }, [f.cultivo]);

    const save = async () => {
        if (!f.parcela_id || !f.cultivo || !f.cultivo_anterior || !f.rendimiento_esperado_kg_ha || !f.fecha_preparacion) {
            alert('Rellena: parcela, cultivo, cultivo anterior, rendimiento y fecha'); return;
        }
        setSaving(true);
        const method = isEdit ? 'PUT' : 'POST';
        const url    = isEdit ? `/api/abonado/${record.id}` : '/api/abonado';
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(f),
            credentials: 'include',
        });
        if (!res.ok) {
            const d = await res.json().catch(() => ({}));
            alert(d.error || 'Error al guardar');
            setSaving(false);
            return;
        }
        onClose('✅ Plan de abono guardado');
    };

    const npkReady = f.n_necesario_kg_ha !== '' && f.n_necesario_kg_ha !== null;

    return (
        <div>
            <FieldGroup label="Parcela *">
                <ParcelSelect parcelas={parcelas} value={f.parcela_id} onChange={v => set('parcela_id', v)} />
            </FieldGroup>

            <div className="responsive-grid cols-2">
                <FieldGroup label="Cultivo *">
                    <input type="text" className="input-field" value={f.cultivo}
                        placeholder="Ej: Trigo, Olivar, Viña…"
                        onChange={e => set('cultivo', e.target.value)} />
                </FieldGroup>
                <FieldGroup label="Cultivo anterior *">
                    <input type="text" className="input-field" value={f.cultivo_anterior}
                        placeholder="Ej: Cebada, Barbecho…"
                        onChange={e => set('cultivo_anterior', e.target.value)} />
                </FieldGroup>
            </div>

            <div className="responsive-grid cols-2">
                <FieldGroup label="Rendimiento esperado (kg/ha) *">
                    <ZoomInput label="Rendimiento (kg/ha)" value={f.rendimiento_esperado_kg_ha}
                        placeholder="Ej: 3500" inputMode="decimal"
                        onConfirm={v => set('rendimiento_esperado_kg_ha', v)} />
                </FieldGroup>
                <FieldGroup label="Fecha de preparación *">
                    <input type="date" className="input-field" value={f.fecha_preparacion}
                        onChange={e => set('fecha_preparacion', e.target.value)} />
                </FieldGroup>
            </div>

            {npkReady && (
                <div style={{ background: 'rgba(13,148,136,0.08)', border: '1px solid rgba(13,148,136,0.25)', borderRadius: 12, padding: '12px 14px', marginBottom: 16 }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0f766e', marginBottom: 8 }}>
                        🌱 Necesidades NPK calculadas
                    </div>
                    <div style={{ display: 'flex', gap: 10 }}>
                        {[['N', f.n_necesario_kg_ha, '#1d4ed8'], ['P₂O₅', f.p_necesario_kg_ha, '#b45309'], ['K₂O', f.k_necesario_kg_ha, '#0f766e']].map(([label, val, color]) => (
                            <div key={label} style={{ flex: 1, background: '#fff', borderRadius: 8, padding: '8px 4px', textAlign: 'center', border: `1px solid ${color}22` }}>
                                <div style={{ fontSize: '0.65rem', fontWeight: 700, color, textTransform: 'uppercase' }}>{label}</div>
                                <div style={{ fontSize: '1.1rem', fontWeight: 900, color }}>{val}</div>
                                <div style={{ fontSize: '0.6rem', color: 'var(--on-surface-variant)' }}>kg/ha</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <MasCampos>
                <FieldGroup label="Datos de suelo">
                    <ZoomInput label="Datos de suelo" value={f.datos_suelo}
                        placeholder="Ej: Análisis 2024 — pH 7.5, M.O. 1.2%, textura franca…"
                        multiline onConfirm={v => set('datos_suelo', v)} />
                </FieldGroup>
                <FieldGroup label="Abono recomendado">
                    <input type="text" className="input-field" value={f.abono_recomendado}
                        placeholder="Ej: Urea 46%, NPK 8-15-15…"
                        onChange={e => set('abono_recomendado', e.target.value)} />
                </FieldGroup>
                <FieldGroup label="Dosis recomendada (kg/ha)">
                    <ZoomInput label="Dosis (kg/ha)" value={f.dosis_recomendada_kg_ha}
                        placeholder="Ej: 250" inputMode="decimal"
                        onConfirm={v => set('dosis_recomendada_kg_ha', v)} />
                </FieldGroup>
                <FieldGroup label="Notas">
                    <ZoomInput label="Notas" value={f.notas} placeholder="Observaciones…"
                        multiline onConfirm={v => set('notas', v)} />
                </FieldGroup>
            </MasCampos>

            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <button className="btn-ghost" onClick={() => onClose()} style={{ flex: 1 }}>Cancelar</button>
                <button className="btn-primary" onClick={save} disabled={saving} style={{ flex: 2 }}>
                    {saving ? 'Guardando…' : (isEdit ? 'Guardar cambios' : '📋 Guardar plan')}
                </button>
            </div>
        </div>
    );
}
```

- [ ] **Step 6: Actualizar `screens_history.jsx`**

Añadir `abonado` a `MODULE_META` (línea ~26), después de la entrada de `riego`:
```js
        abonado:       { icon: '📋', label: 'Plan abono',    chipClass: 'chip-abonado',        accentColor: '#0f766e' },
```

Añadir `abonado` a `MODULE_PILLS` (línea ~36), después de la entrada de `riego`:
```js
        ['abonado',       '📋 Plan abono'],
```

- [ ] **Step 7: Borrar `screens_abonado.jsx`**

```bash
cd "h:\Proyectos\Cuaderno ex app"
git rm frontend/screens_abonado.jsx
```

- [ ] **Step 8: Verificar en navegador**

1. Arrancar servidor: `cd "h:\Proyectos\Cuaderno ex app\backend" && python app.py`
2. Abrir `http://127.0.0.1:5000`
3. Pulsar FAB ✏️ → debe aparecer la tarjeta "📋 Plan de abono" (color teal)
4. Abrir el formulario → escribir cultivo "Trigo" → debe aparecer el bloque NPK automáticamente: N:120 P:60 K:60
5. Rellenar cultivo anterior, rendimiento y fecha → pulsar "📋 Guardar plan" → debe aparecer "✅ Plan de abono guardado"
6. Ir a Historial → el registro debe aparecer con chip teal "PLAN ABONO" y resumen "Trigo — N:120 P:60 K:60 kg/ha"

- [ ] **Step 9: Commit y push**

```bash
git add frontend/index.html frontend/app.jsx frontend/screens_forms.jsx frontend/screens_history.jsx
git commit -m "feat: modulo plan de abonado en FAB — formulario NPK, historial y dashboard (RD 934/2025)"
git push origin main
```
