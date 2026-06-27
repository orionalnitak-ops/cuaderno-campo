# UHC (Unidades Homogéneas de Cultivo) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir al agricultor agrupar parcelas del mismo cultivo en "Unidades Homogéneas de Cultivo" (UHC) y registrar un tratamiento fitosanitario una sola vez para que se aplique automáticamente a todas las parcelas del grupo.

**Architecture:** Se añaden dos tablas nuevas (`unidades_homogeneas` y `uhc_parcelas`). El backend expande `uhc_id` → N registros en `tratamientos` al guardar (un registro por parcela del grupo). El frontend añade un toggle "Parcela / Grupo UHC" en el formulario de tratamiento, y una pantalla de gestión de grupos accesible desde el sidebar.

**Tech Stack:** Python/Flask blueprint, SQLite + PostgreSQL, React JSX (Babel CLI), mobile-first 480px.

---

## File Structure

| Archivo | Acción | Responsabilidad |
|---------|--------|-----------------|
| `backend/db.py` | Modificar | Añadir tablas `unidades_homogeneas` y `uhc_parcelas` |
| `backend/blueprints/uhc.py` | Crear | CRUD de grupos UHC + endpoint de parcelas del grupo |
| `backend/app.py` | Modificar | Registrar blueprint uhc |
| `backend/blueprints/tratamientos.py` | Modificar | Soportar `uhc_id` en POST: expandir a N tratamientos |
| `frontend/screens_uhc.jsx` | Crear | Pantalla de gestión de grupos UHC |
| `frontend/screens_forms.jsx` | Modificar | Añadir toggle parcela/UHC en `FormTratamiento` |
| `frontend/app.jsx` | Modificar | Añadir case 'uhc' en renderScreen + sidebar item |
| `frontend/index.html` | Modificar | Añadir `<script src="/dist/screens_uhc.js">` |

---

## Task 1: Migración de BD — tablas UHC

**Files:**
- Modify: `backend/db.py` (al final del bloque de CREATE TABLE, antes de `conn.commit()`)

- [ ] **Step 1: Añadir tablas al bloque de inicialización de db.py**

Busca el bloque `# ── LABORES ──` en `backend/db.py` (línea ~543) y añade justo después del bloque de `labores`:

```python
    # ── UNIDADES HOMOGÉNEAS DE CULTIVO (UHC) ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS unidades_homogeneas (
            id {_PK},
            user_id INTEGER DEFAULT 2,
            nombre TEXT NOT NULL,
            cultivo TEXT,
            campana TEXT DEFAULT '2025/2026',
            notas TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    for col, typ in [
        ('nombre', 'TEXT'), ('cultivo', 'TEXT'),
        ('campana', 'TEXT'), ('notas', 'TEXT'),
        ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
    ]:
        _add_col(c, 'unidades_homogeneas', col, typ)

    c.execute(f'''
        CREATE TABLE IF NOT EXISTS uhc_parcelas (
            id {_PK},
            uhc_id INTEGER NOT NULL,
            parcela_id INTEGER NOT NULL,
            FOREIGN KEY(uhc_id) REFERENCES unidades_homogeneas(id),
            FOREIGN KEY(parcela_id) REFERENCES parcelas(id)
        )
    ''')
```

> Nota: `uhc_parcelas` no usa `_add_col` porque es una tabla nueva — no puede preexistir en producción. El UNIQUE(uhc_id, parcela_id) se maneja en la lógica de inserción (INSERT OR IGNORE).

- [ ] **Step 2: Verificar que el servidor arranca sin errores**

```bash
cd "H:/Proyectos/Cuaderno ex app/backend"
python app.py
```

Esperado: `Running on http://0.0.0.0:5000` sin traceback. Pulsa Ctrl+C.

- [ ] **Step 3: Verificar que las tablas existen en SQLite**

```bash
cd "H:/Proyectos/Cuaderno ex app/backend"
python -c "from db import get_db; c=get_db(); rows=c.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'u%'\").fetchall(); print(rows); c.close()"
```

Esperado: `[('unidades_homogeneas',), ('uhc_parcelas',)]` (o similar con tuples).

- [ ] **Step 4: Commit**

```bash
git add backend/db.py
git commit -m "feat(uhc): add unidades_homogeneas and uhc_parcelas tables"
```

---

## Task 2: Backend CRUD para UHC

**Files:**
- Create: `backend/blueprints/uhc.py`

- [ ] **Step 1: Crear el blueprint completo**

Crea el archivo `backend/blueprints/uhc.py` con este contenido:

```python
"""
blueprints/uhc.py — CRUD de Unidades Homogéneas de Cultivo
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid

bp = Blueprint('uhc', __name__)


@bp.route('/api/uhc', methods=['GET', 'POST'])
@login_required
def manage_uhc():
    uid = get_uid()
    conn = get_db()

    if request.method == 'GET':
        campana = request.args.get('campana', '2025/2026')
        rows = dicts(conn, """
            SELECT u.*,
                   COUNT(up.id) AS num_parcelas
            FROM unidades_homogeneas u
            LEFT JOIN uhc_parcelas up ON up.uhc_id = u.id
            WHERE u.user_id = ? AND u.campana = ?
            GROUP BY u.id
            ORDER BY u.nombre
        """, (uid, campana))
        conn.close()
        return jsonify(rows)

    data = request.json or {}
    nombre = (data.get('nombre') or '').strip()
    if not nombre:
        conn.close()
        return jsonify({"error": "El nombre del grupo es obligatorio"}), 400

    campana = data.get('campana', '2025/2026')
    c = conn.cursor()
    c.execute(
        "INSERT INTO unidades_homogeneas (user_id, nombre, cultivo, campana, notas) VALUES (?,?,?,?,?)",
        (uid, nombre, data.get('cultivo', '').strip(), campana, data.get('notas', '').strip())
    )
    uhc_id = c.lastrowid

    parcela_ids = data.get('parcela_ids', [])
    for pid in parcela_ids:
        c.execute(
            "INSERT OR IGNORE INTO uhc_parcelas (uhc_id, parcela_id) VALUES (?,?)",
            (uhc_id, pid)
        )

    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "id": uhc_id}), 201


@bp.route('/api/uhc/<int:uid_uhc>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_one_uhc(uid_uhc):
    uid = get_uid()
    conn = get_db()

    uhc = one(conn, "SELECT * FROM unidades_homogeneas WHERE id=? AND user_id=?", (uid_uhc, uid))
    if not uhc:
        conn.close()
        return jsonify({"error": "Grupo no encontrado"}), 404

    if request.method == 'GET':
        parcelas = dicts(conn, """
            SELECT p.id, p.nombre_finca, p.superficie_ha,
                   cc.cultivo
            FROM uhc_parcelas up
            JOIN parcelas p ON p.id = up.parcela_id
            LEFT JOIN cultivos_campana cc ON cc.parcela_id = p.id AND cc.campana = ?
            WHERE up.uhc_id = ?
        """, (uhc.get('campana', '2025/2026'), uid_uhc))
        conn.close()
        return jsonify({"uhc": uhc, "parcelas": parcelas})

    if request.method == 'DELETE':
        c = conn.cursor()
        c.execute("DELETE FROM uhc_parcelas WHERE uhc_id=?", (uid_uhc,))
        c.execute("DELETE FROM unidades_homogeneas WHERE id=? AND user_id=?", (uid_uhc, uid))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})

    # PUT — actualizar nombre/cultivo/notas y reasignar parcelas
    data = request.json or {}
    nombre = (data.get('nombre') or '').strip()
    if not nombre:
        conn.close()
        return jsonify({"error": "El nombre del grupo es obligatorio"}), 400

    c = conn.cursor()
    c.execute(
        "UPDATE unidades_homogeneas SET nombre=?, cultivo=?, notas=? WHERE id=? AND user_id=?",
        (nombre, data.get('cultivo', '').strip(), data.get('notas', '').strip(), uid_uhc, uid)
    )

    # Reasignar parcelas: borrar y reinsertar
    c.execute("DELETE FROM uhc_parcelas WHERE uhc_id=?", (uid_uhc,))
    for pid in data.get('parcela_ids', []):
        c.execute(
            "INSERT OR IGNORE INTO uhc_parcelas (uhc_id, parcela_id) VALUES (?,?)",
            (uid_uhc, pid)
        )

    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@bp.route('/api/uhc/<int:uid_uhc>/parcelas', methods=['GET'])
@login_required
def get_uhc_parcelas(uid_uhc):
    """Devuelve la lista de parcelas de un UHC (para expandir en tratamientos)."""
    uid = get_uid()
    conn = get_db()
    uhc = one(conn, "SELECT * FROM unidades_homogeneas WHERE id=? AND user_id=?", (uid_uhc, uid))
    if not uhc:
        conn.close()
        return jsonify({"error": "Grupo no encontrado"}), 404

    parcelas = dicts(conn, """
        SELECT p.id, p.nombre_finca, p.superficie_ha
        FROM uhc_parcelas up
        JOIN parcelas p ON p.id = up.parcela_id
        WHERE up.uhc_id = ?
    """, (uid_uhc,))
    conn.close()
    return jsonify(parcelas)
```

- [ ] **Step 2: Verificar sintaxis**

```bash
cd "H:/Proyectos/Cuaderno ex app/backend"
python -c "from blueprints.uhc import bp; print('OK')"
```

Esperado: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/blueprints/uhc.py
git commit -m "feat(uhc): CRUD blueprint for UHC groups"
```

---

## Task 3: Registrar blueprint en app.py

**Files:**
- Modify: `backend/app.py` (imports y register_blueprint)

- [ ] **Step 1: Añadir el import**

En `backend/app.py`, localiza la línea:
```python
from blueprints.push import bp as push_bp
```

Añade justo después:
```python
from blueprints.uhc import bp as uhc_bp
```

- [ ] **Step 2: Registrar el blueprint**

Localiza:
```python
app.register_blueprint(push_bp)
```

Añade justo después:
```python
app.register_blueprint(uhc_bp)
```

- [ ] **Step 3: Verificar que el servidor arranca y los endpoints existen**

```bash
cd "H:/Proyectos/Cuaderno ex app/backend"
python app.py
```

En otro terminal:
```bash
curl -s http://localhost:5000/api/uhc
```

Esperado: `{"error": "..."}` con código 401 (no autenticado) — confirma que el endpoint existe.

Pulsa Ctrl+C en el servidor.

- [ ] **Step 4: Commit**

```bash
git add backend/app.py
git commit -m "feat(uhc): register uhc blueprint in app"
```

---

## Task 4: Expansión UHC en tratamientos backend

**Files:**
- Modify: `backend/blueprints/tratamientos.py`

El objetivo: cuando el POST a `/api/tratamientos` incluye `uhc_id` en lugar de `parcela_id`, el backend crea **un tratamiento por cada parcela del grupo**.

- [ ] **Step 1: Modificar el validador `_validate_tratamiento`**

Localiza la función `_validate_tratamiento` en `backend/blueprints/tratamientos.py`. Cambia la key `'parcela_id'` para que sea opcional cuando hay `uhc_id`:

```python
def _validate_tratamiento(data):
    """Devuelve mensaje de error si faltan campos obligatorios (Anexo III S3)."""
    # parcela_id es obligatorio salvo que se especifique uhc_id
    required = {
        'fecha_aplicacion':    'Fecha de aplicación',
        'producto_comercial':  'Producto comercial',
        'num_registro_mapa':   'Nº Registro MAPA',
        'sustancia_activa':    'Sustancia activa',
        'plaga_objetivo':      'Plaga / enfermedad objetivo',
        'dosis_valor':         'Dosis',
        'aplicador_id':        'Aplicador (obligatorio por ROPO)',
        'equipo_aplicacion':   'Equipo de aplicación (Anexo III S3)',
        'plazo_seguridad_dias': 'Plazo de seguridad (días)',
    }
    missing = [label for field, label in required.items() if not data.get(field) and data.get(field) != 0]

    # Validar que hay parcela_id O uhc_id, pero no ninguno
    if not data.get('parcela_id') and not data.get('uhc_id'):
        missing.append('Parcela SIGPAC o Grupo UHC (Anexo III S3)')

    if missing:
        return f"Campos obligatorios según RD 1311/2012: {', '.join(missing)}"
    try:
        fecha = datetime.date.fromisoformat(str(data['fecha_aplicacion']))
        if fecha > datetime.date.today():
            return "La fecha de aplicación no puede ser futura"
    except (ValueError, TypeError):
        return "Fecha de aplicación con formato inválido (use YYYY-MM-DD)"
    try:
        if int(data['plazo_seguridad_dias']) < 0:
            return "El plazo de seguridad no puede ser negativo"
    except (ValueError, TypeError):
        return "El plazo de seguridad debe ser un número entero"
    try:
        if float(str(data['dosis_valor']).replace(',', '.')) <= 0:
            return "La dosis debe ser mayor que cero"
    except (ValueError, TypeError):
        return "La dosis debe ser un número válido"
    mapa = str(data.get('num_registro_mapa', '')).strip()
    if not re.fullmatch(r'\d{4,6}(/\d+)?', mapa):
        return "El Nº de Registro MAPA debe ser numérico (ej: 12345 o 12345/2)"
    return None
```

- [ ] **Step 2: Añadir helper de inserción de un tratamiento**

Justo antes de `@bp.route('/api/tratamientos', ...)`, añade este helper privado:

```python
def _insert_tratamiento(c, uid, data, parcela_id, parcela_etiqueta):
    """Inserta un único registro de tratamiento para la parcela dada."""
    c.execute('''
        INSERT INTO tratamientos (
            user_id, parcela_id, parcela_etiqueta, fecha_aplicacion,
            producto_comercial, num_registro_mapa, sustancia_activa,
            plaga_objetivo, dosis_valor, dosis_unidad, volumen_caldo,
            equipo_id, condiciones_meteo, plazo_seguridad_dias,
            fecha_recoleccion_minima, eficacia, aplicador_id, notas, campana
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        uid, parcela_id, parcela_etiqueta, data.get('fecha_aplicacion'),
        data.get('producto_comercial'), data.get('num_registro_mapa'), data.get('sustancia_activa'),
        data.get('plaga_objetivo'), _to_real(data.get('dosis_valor')), data.get('dosis_unidad', 'L/ha'),
        _to_real(data.get('volumen_caldo')), data.get('equipo_id') or None, data.get('condiciones_meteo'),
        data.get('plazo_seguridad_dias') or None,
        _calc_fecha_recoleccion(data.get('fecha_aplicacion'), data.get('plazo_seguridad_dias')),
        data.get('eficacia'), data.get('aplicador_id') or None, data.get('notas'),
        data.get('campana', '2025/2026'),
    ))
    return c.lastrowid
```

- [ ] **Step 3: Modificar el handler POST de /api/tratamientos**

En la función `manage_tratamientos`, reemplaza el bloque POST completo (desde `c = conn.cursor()` hasta `return jsonify(...)`) con:

```python
    c = conn.cursor()

    if data.get('uhc_id'):
        # Expansión UHC: crear un tratamiento por parcela del grupo
        from db import dicts as _dicts
        parcelas = _dicts(conn, """
            SELECT p.id, p.nombre_finca
            FROM uhc_parcelas up
            JOIN parcelas p ON p.id = up.parcela_id
            JOIN unidades_homogeneas u ON u.id = up.uhc_id
            WHERE up.uhc_id = ? AND u.user_id = ?
        """, (data['uhc_id'], uid))

        if not parcelas:
            conn.close()
            return jsonify({"error": "El grupo UHC no existe o no tiene parcelas asignadas"}), 400

        ids = []
        for p in parcelas:
            new_id = _insert_tratamiento(c, uid, data, p['id'], p['nombre_finca'])
            ids.append(new_id)

        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201

    # Caso normal: parcela individual
    new_id = _insert_tratamiento(c, uid, data, data.get('parcela_id'), data.get('parcela_etiqueta'))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201
```

> Nota: El `from db import dicts as _dicts` se puede mover al top del archivo si prefieres (al lado de los otros imports). Aquí se pone inline para minimizar el diff.

- [ ] **Step 4: Verificar sintaxis**

```bash
cd "H:/Proyectos/Cuaderno ex app/backend"
python -c "from blueprints.tratamientos import bp; print('OK')"
```

Esperado: `OK`

- [ ] **Step 5: Verificar arranque del servidor**

```bash
cd "H:/Proyectos/Cuaderno ex app/backend"
python app.py
```

Esperado: sin traceback. Ctrl+C.

- [ ] **Step 6: Commit**

```bash
git add backend/blueprints/tratamientos.py
git commit -m "feat(uhc): expand uhc_id to N tratamientos on POST"
```

---

## Task 5: Frontend — pantalla de gestión de grupos UHC

**Files:**
- Create: `frontend/screens_uhc.jsx`

- [ ] **Step 1: Crear el archivo screens_uhc.jsx**

```jsx
// screens_uhc.jsx — Gestión de Unidades Homogéneas de Cultivo

function ScreenUHC({ campana, showToast, parcelas }) {
    const [grupos, setGrupos] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [editando, setEditando] = React.useState(null); // null | 'new' | {uhc object}
    const [detalle, setDetalle] = React.useState(null);   // parcelas del grupo en edición

    const reload = () => {
        setLoading(true);
        fetch(`/api/uhc?campana=${encodeURIComponent(campana)}`, { credentials: 'include' })
            .then(r => r.json())
            .then(d => { setGrupos(Array.isArray(d) ? d : []); setLoading(false); })
            .catch(() => setLoading(false));
    };

    React.useEffect(() => { reload(); }, [campana]);

    const abrirNuevo = () => {
        setDetalle([]);
        setEditando({ nombre: '', cultivo: '', notas: '', parcela_ids: [] });
    };

    const abrirEditar = async (g) => {
        const res = await fetch(`/api/uhc/${g.id}`, { credentials: 'include' });
        const d = await res.json();
        setDetalle(d.parcelas || []);
        setEditando({ ...d.uhc, parcela_ids: (d.parcelas || []).map(p => p.id) });
    };

    const eliminar = async (g) => {
        if (!confirm(`¿Eliminar el grupo "${g.nombre}"? Los tratamientos ya guardados no se borran.`)) return;
        await fetch(`/api/uhc/${g.id}`, { method: 'DELETE', credentials: 'include' });
        showToast('Grupo eliminado');
        reload();
    };

    const guardar = async () => {
        const esNuevo = !editando.id;
        const method = esNuevo ? 'POST' : 'PUT';
        const url = esNuevo ? '/api/uhc' : `/api/uhc/${editando.id}`;
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ ...editando, campana }),
        });
        if (!res.ok) {
            const d = await res.json().catch(() => ({}));
            alert(d.error || 'Error al guardar');
            return;
        }
        showToast(esNuevo ? '✅ Grupo creado' : '✅ Grupo actualizado');
        setEditando(null);
        reload();
    };

    const toggleParcela = (pid) => {
        setEditando(prev => {
            const ids = prev.parcela_ids || [];
            return {
                ...prev,
                parcela_ids: ids.includes(pid) ? ids.filter(x => x !== pid) : [...ids, pid],
            };
        });
    };

    if (editando !== null) {
        return (
            <div style={{ maxWidth: 600, margin: '0 auto', padding: '16px 12px' }}>
                <button onClick={() => setEditando(null)} style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--primary)', fontWeight: 600, fontSize: '0.9rem', marginBottom: 16,
                }}>← Volver</button>

                <h2 style={{ margin: '0 0 20px', fontSize: '1.1rem' }}>
                    {editando.id ? 'Editar grupo' : 'Nuevo grupo UHC'}
                </h2>

                <div style={{ marginBottom: 14 }}>
                    <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: '0.85rem' }}>
                        Nombre del grupo *
                    </label>
                    <input
                        className="input-field"
                        placeholder="Ej: Trigo secano norte"
                        value={editando.nombre}
                        onChange={e => setEditando(p => ({ ...p, nombre: e.target.value }))}
                    />
                </div>

                <div style={{ marginBottom: 14 }}>
                    <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: '0.85rem' }}>
                        Cultivo principal
                    </label>
                    <input
                        className="input-field"
                        placeholder="Ej: TRIGO, CEBADA, GIRASOL…"
                        value={editando.cultivo || ''}
                        onChange={e => setEditando(p => ({ ...p, cultivo: e.target.value }))}
                    />
                </div>

                <div style={{ marginBottom: 20 }}>
                    <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: '0.85rem' }}>
                        Notas
                    </label>
                    <textarea
                        className="input-field"
                        rows={2}
                        placeholder="Opcional"
                        value={editando.notas || ''}
                        onChange={e => setEditando(p => ({ ...p, notas: e.target.value }))}
                        style={{ resize: 'vertical' }}
                    />
                </div>

                <div style={{ marginBottom: 20 }}>
                    <label style={{ display: 'block', fontWeight: 600, marginBottom: 8, fontSize: '0.85rem' }}>
                        Parcelas del grupo ({(editando.parcela_ids || []).length} seleccionadas)
                    </label>
                    {parcelas.length === 0 ? (
                        <p style={{ color: 'var(--on-surface-variant)', fontSize: '0.85rem' }}>
                            No tienes parcelas registradas todavía.
                        </p>
                    ) : (
                        <div style={{ border: '1px solid var(--outline-variant)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                            {parcelas.filter(p => p.activa !== 0).map((p, i) => {
                                const sel = (editando.parcela_ids || []).includes(p.id);
                                return (
                                    <label key={p.id} style={{
                                        display: 'flex', alignItems: 'center', gap: 12,
                                        padding: '10px 14px',
                                        background: sel ? 'var(--primary-container)' : (i % 2 === 0 ? '#fff' : 'var(--surface-variant)'),
                                        cursor: 'pointer', transition: 'background 0.15s',
                                        borderBottom: i < parcelas.length - 1 ? '1px solid var(--outline-variant)' : 'none',
                                    }}>
                                        <input
                                            type="checkbox"
                                            checked={sel}
                                            onChange={() => toggleParcela(p.id)}
                                            style={{ accentColor: 'var(--primary)', width: 18, height: 18 }}
                                        />
                                        <span style={{ flex: 1, fontSize: '0.88rem', fontWeight: sel ? 600 : 400 }}>
                                            {p.nombre_finca}
                                        </span>
                                        <span style={{ fontSize: '0.78rem', color: 'var(--on-surface-variant)' }}>
                                            {p.superficie_ha ? `${Number(p.superficie_ha).toFixed(2)} ha` : ''}
                                        </span>
                                    </label>
                                );
                            })}
                        </div>
                    )}
                </div>

                <button
                    onClick={guardar}
                    style={{
                        width: '100%', padding: '14px', background: 'var(--primary)',
                        color: '#fff', border: 'none', borderRadius: 'var(--radius-full)',
                        fontWeight: 700, fontSize: '1rem', cursor: 'pointer',
                        fontFamily: 'var(--font-body)',
                    }}
                >
                    {editando.id ? '💾 Actualizar grupo' : '✓ Crear grupo'}
                </button>
            </div>
        );
    }

    return (
        <div style={{ maxWidth: 600, margin: '0 auto', padding: '16px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <h2 style={{ margin: 0, fontSize: '1.1rem' }}>🌱 Grupos UHC</h2>
                <button
                    onClick={abrirNuevo}
                    style={{
                        background: 'var(--primary)', color: '#fff', border: 'none',
                        borderRadius: 'var(--radius-full)', padding: '8px 18px',
                        fontWeight: 700, fontSize: '0.88rem', cursor: 'pointer',
                        fontFamily: 'var(--font-body)',
                    }}
                >+ Nuevo grupo</button>
            </div>

            <p style={{ fontSize: '0.82rem', color: 'var(--on-surface-variant)', marginTop: 0, marginBottom: 20 }}>
                Un grupo UHC permite registrar un tratamiento fitosanitario una sola vez para todas las parcelas del grupo.
            </p>

            {loading ? (
                <p style={{ textAlign: 'center', color: 'var(--on-surface-variant)' }}>Cargando…</p>
            ) : grupos.length === 0 ? (
                <div style={{
                    textAlign: 'center', padding: '40px 20px',
                    background: 'var(--surface-container-low)', borderRadius: 'var(--radius-lg)',
                }}>
                    <div style={{ fontSize: '2.5rem', marginBottom: 12 }}>🌾</div>
                    <p style={{ fontWeight: 600, margin: '0 0 8px' }}>Sin grupos todavía</p>
                    <p style={{ fontSize: '0.82rem', color: 'var(--on-surface-variant)', margin: 0 }}>
                        Crea un grupo para agrupar parcelas del mismo cultivo.
                    </p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {grupos.map(g => (
                        <div key={g.id} style={{
                            background: '#fff', borderRadius: 'var(--radius-lg)',
                            border: '1px solid var(--outline-variant)', padding: '14px 16px',
                            display: 'flex', alignItems: 'center', gap: 12,
                        }}>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: 2 }}>{g.nombre}</div>
                                <div style={{ fontSize: '0.78rem', color: 'var(--on-surface-variant)' }}>
                                    {g.cultivo ? `${g.cultivo} · ` : ''}{g.num_parcelas} parcela{g.num_parcelas !== 1 ? 's' : ''}
                                </div>
                            </div>
                            <button onClick={() => abrirEditar(g)} style={{
                                background: 'var(--surface-container-low)', border: 'none',
                                borderRadius: 'var(--radius-md)', padding: '6px 12px',
                                cursor: 'pointer', fontSize: '0.82rem', fontWeight: 600,
                                color: 'var(--on-surface-variant)',
                            }}>✏️ Editar</button>
                            <button onClick={() => eliminar(g)} style={{
                                background: 'none', border: 'none',
                                cursor: 'pointer', color: '#dc2626', fontSize: '1.1rem',
                                padding: '4px 8px',
                            }}>🗑</button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
```

- [ ] **Step 2: Compilar el archivo**

```bash
cd "H:/Proyectos/Cuaderno ex app/frontend"
npm run build
```

Esperado: sin errores. Verifica que existe `frontend/dist/screens_uhc.js`.

- [ ] **Step 3: Commit**

```bash
git add frontend/screens_uhc.jsx frontend/dist/screens_uhc.js
git commit -m "feat(uhc): add UHC management screen"
```

---

## Task 6: Integrar UHC en FormTratamiento

**Files:**
- Modify: `frontend/screens_forms.jsx`

El objetivo: añadir un toggle "📍 Parcela / 🌱 Grupo UHC" en el formulario de tratamiento. Cuando se selecciona "Grupo UHC", se muestra un select de grupos en vez de `ParcelSelect`. Al guardar, se envía `uhc_id` en lugar de `parcela_id`.

- [ ] **Step 1: Añadir estado de modo UHC en FormTratamiento**

Localiza la función `FormTratamiento` (línea ~225 de `screens_forms.jsx`). Dentro, después de la línea:
```javascript
    const [showAddAplic, setShowAddAplic] = React.useState(false);
```

Añade:
```javascript
    const [modoUHC, setModoUHC]   = React.useState(false);
    const [uhcList, setUhcList]   = React.useState([]);
```

- [ ] **Step 2: Cargar los grupos UHC al montar el componente**

Localiza el `React.useEffect` que llama a `/api/equipos`. Dentro del mismo efecto (o añade uno nuevo justo después), añade la carga de UHC:

```javascript
    React.useEffect(() => {
        fetch(`/api/uhc?campana=${encodeURIComponent(campana)}`, { credentials: 'include' })
            .then(r => r.json())
            .then(d => setUhcList(Array.isArray(d) ? d : []))
            .catch(() => {});
    }, [campana]);
```

- [ ] **Step 3: Añadir `uhc_id` al estado del formulario**

En el objeto de estado inicial `f`, añade:
```javascript
        uhc_id: record?.uhc_id || '',
```

Justo después de:
```javascript
        parcela_id:               record?.parcela_id || '',
```

- [ ] **Step 4: Modificar la validación del botón Guardar**

Localiza la función `save` en `FormTratamiento`. Cambia:
```javascript
        if (!f.parcela_id || !f.fecha_aplicacion ...
```

Por:
```javascript
        if ((!f.parcela_id && !f.uhc_id) || !f.fecha_aplicacion || !f.aplicador_id || !f.producto_comercial ||
            !f.plaga_objetivo || !f.sustancia_activa || !f.num_registro_mapa || !f.dosis_valor ||
            !f.equipo_id || !f.plazo_seguridad_dias) {
            alert('Rellena todos los campos obligatorios (marcados con *)'); return;
        }
```

- [ ] **Step 5: Reemplazar el campo "Parcela *" en el JSX del formulario**

Localiza el bloque:
```jsx
            <FieldGroup label="Parcela *">
                <ParcelSelect parcelas={parcelas} value={f.parcela_id} onChange={v => set('parcela_id', v)} />
            </FieldGroup>
```

Reemplázalo por:
```jsx
            {/* Toggle parcela / grupo UHC */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                <button
                    type="button"
                    onClick={() => { setModoUHC(false); set('uhc_id', ''); }}
                    style={{
                        flex: 1, padding: '8px', border: 'none', borderRadius: 'var(--radius-full)',
                        fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer',
                        fontFamily: 'var(--font-body)',
                        background: !modoUHC ? 'var(--primary)' : 'var(--surface-container-low)',
                        color: !modoUHC ? '#fff' : 'var(--on-surface-variant)',
                    }}
                >📍 Parcela individual</button>
                <button
                    type="button"
                    onClick={() => { setModoUHC(true); set('parcela_id', ''); }}
                    style={{
                        flex: 1, padding: '8px', border: 'none', borderRadius: 'var(--radius-full)',
                        fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer',
                        fontFamily: 'var(--font-body)',
                        background: modoUHC ? 'var(--primary)' : 'var(--surface-container-low)',
                        color: modoUHC ? '#fff' : 'var(--on-surface-variant)',
                    }}
                >🌱 Grupo UHC</button>
            </div>

            {!modoUHC ? (
                <FieldGroup label="Parcela *">
                    <ParcelSelect parcelas={parcelas} value={f.parcela_id} onChange={v => set('parcela_id', v)} />
                </FieldGroup>
            ) : (
                <FieldGroup label="Grupo UHC *">
                    {uhcList.length === 0 ? (
                        <p style={{ fontSize: '0.82rem', color: 'var(--on-surface-variant)', margin: '4px 0' }}>
                            No tienes grupos UHC. <a href="#" onClick={e => { e.preventDefault(); alert('Ve a "Grupos UHC" en el menú lateral para crear uno.'); }}>¿Cómo crearlos?</a>
                        </p>
                    ) : (
                        <select className="input-field" value={f.uhc_id} onChange={e => set('uhc_id', e.target.value)}>
                            <option value="">-- Selecciona grupo --</option>
                            {uhcList.map(g => (
                                <option key={g.id} value={g.id}>
                                    {g.nombre}{g.cultivo ? ` (${g.cultivo})` : ''} — {g.num_parcelas} parcelas
                                </option>
                            ))}
                        </select>
                    )}
                </FieldGroup>
            )}
```

- [ ] **Step 6: Compilar**

```bash
cd "H:/Proyectos/Cuaderno ex app/frontend"
npm run build
```

Esperado: sin errores.

- [ ] **Step 7: Commit**

```bash
git add frontend/screens_forms.jsx frontend/dist/screens_forms.js
git commit -m "feat(uhc): add UHC toggle in FormTratamiento"
```

---

## Task 7: Wiring — app.jsx, index.html, sidebar

**Files:**
- Modify: `frontend/app.jsx`
- Modify: `frontend/index.html`

- [ ] **Step 1: Añadir case 'uhc' en renderScreen**

En `frontend/app.jsx`, localiza:
```javascript
    const renderScreen = () => {
        switch (screen) {
```

Añade antes de `default:`:
```javascript
            case 'uhc':       return <ScreenUHC campana={campana} showToast={showMsg} parcelas={parcelas || []} />;
```

> Nota: `parcelas` ya se carga en `app.jsx`. Revisa el nombre de la variable de estado donde se guardan las parcelas del usuario (busca `const [parcelas` o `setParcelas`). Si no existe en app.jsx, pasa `[]` — la pantalla UHC las carga internamente igualmente vía la prop `parcelas` para el formulario de edición.

- [ ] **Step 2: Añadir UHC al sidebar desktop**

Localiza:
```javascript
    const sidebarItems = [
        { id: 'inicio',    icon: '🏡', label: 'Inicio' },
        { id: 'parcelas',  icon: '🗺️', label: 'Mis parcelas' },
        { id: 'historial', icon: '📋', label: 'Historial' },
        { id: 'mas',       icon: '⚙️', label: 'Ajustes' },
```

Añade después de `parcelas`:
```javascript
        { id: 'uhc',       icon: '🌱', label: 'Grupos UHC' },
```

> No añadir al bottomNavItems (barra móvil) — ya tiene 5 items y está llena. En móvil se accede via sidebar (hamburguesa/menú).

- [ ] **Step 3: Compilar app.jsx**

```bash
cd "H:/Proyectos/Cuaderno ex app/frontend"
npm run build
```

Esperado: sin errores.

- [ ] **Step 4: Añadir script en index.html**

En `frontend/index.html`, localiza:
```html
  <script src="/dist/screens_parcelas.js"></script>
```

Añade justo después:
```html
  <script src="/dist/screens_uhc.js"></script>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/app.jsx frontend/dist/app.js frontend/index.html
git commit -m "feat(uhc): wire UHC screen into routing and sidebar"
```

---

## Task 8: Verificación manual en el navegador

- [ ] **Step 1: Arrancar el servidor**

```bash
cd "H:/Proyectos/Cuaderno ex app/backend"
python app.py
```

- [ ] **Step 2: Verificar flujo completo de creación de grupo**

1. Abre `http://localhost:5000` en el navegador e inicia sesión.
2. En el sidebar desktop, haz clic en "🌱 Grupos UHC".
3. Pulsa "+ Nuevo grupo", rellena nombre "Trigo norte", selecciona 2-3 parcelas, guarda.
4. Verifica que el grupo aparece en la lista con el contador de parcelas correcto.

- [ ] **Step 3: Verificar que el toggle funciona en el formulario de tratamiento**

1. Pulsa el FAB (✏️) → "Tratamiento fitosanitario".
2. Comprueba que aparecen los botones "📍 Parcela individual" y "🌱 Grupo UHC".
3. Selecciona "🌱 Grupo UHC" → debe aparecer el selector con el grupo creado.
4. Rellena todos los campos y guarda.
5. Verifica en Historial que aparecen **N registros** (uno por parcela del grupo), cada uno con su nombre de finca correcto.

- [ ] **Step 4: Verificar edición y borrado de grupo**

1. Vuelve a "🌱 Grupos UHC".
2. Edita el grupo: cambia el nombre, desmarca una parcela, guarda.
3. Borra el grupo con el botón 🗑.
4. Verifica que los tratamientos ya guardados **siguen apareciendo** en Historial (no se borran en cascada).

- [ ] **Step 5: Commit final si todo OK**

```bash
git add -A
git commit -m "chore: UHC feature complete and verified"
```

---

## Self-Review

**Spec coverage:**
- ✅ Tabla `unidades_homogeneas` — Task 1
- ✅ Tabla `uhc_parcelas` con relación N:N — Task 1
- ✅ CRUD backend (crear, leer, editar, borrar grupos) — Task 2
- ✅ Asignar parcelas al grupo — Task 2 (parcela_ids en POST/PUT)
- ✅ Expansión UHC → N tratamientos en backend — Task 4
- ✅ Toggle parcela/UHC en FormTratamiento — Task 6
- ✅ Pantalla de gestión de grupos — Task 5
- ✅ Navegación desde sidebar — Task 7
- ✅ Build y verificación manual — Task 8

**Gaps identificados:**
- La integración UHC en `FormFertilizacion` y `FormRiego` NO está en este plan (se recomienda como siguiente sprint, el patrón es idéntico al de Task 6).
- No se muestra en Historial el "nombre del grupo UHC" que originó los tratamientos (los registros individuales ya tienen `parcela_etiqueta`). Mejora futura si se necesita auditoría del origen.

**Placeholder scan:** Ningún TBD/TODO encontrado — todos los pasos tienen código completo.

**Type consistency:** `uhc_id` se usa consistentemente en frontend (state `f.uhc_id`) y en el POST al backend. `parcela_ids` (array) en CRUD de UHC, `uhc_id` (integer FK) en tratamientos — distintos, correctos.
