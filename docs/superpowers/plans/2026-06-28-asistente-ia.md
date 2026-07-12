# Asistente IA Estadístico — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir prerrellenado inteligente de formularios y tarjetas de recordatorio en la pantalla de inicio, usando patrones calculados del historial del agricultor (sin LLM, coste cero).

**Architecture:** Un blueprint nuevo `ia.py` centraliza toda la lógica: calcula el valor más frecuente por campo/módulo/parcela/temporada y lo guarda en `ia_patrones`. En cada POST de cualquier módulo se recalculan los patrones. Los formularios fetch las sugerencias al abrirse y muestran un chip `💡 Sugerido` bajo cada campo prerrellenado. En cada login se regeneran alertas proactivas que aparecen en ScreenHome.

**Tech Stack:** Python + Flask (backend), React JSX (frontend), SQLite/PostgreSQL (bd.py dual engine ya existente)

---

## File Map

### New
- `backend/blueprints/ia.py` — toda la lógica IA: `_temporada`, `_recalcular_patrones`, `_generar_alertas` + 4 endpoints

### Modified
- `backend/db.py` — 3 nuevas tablas en `init_db()`: `ia_patrones`, `ia_alertas`, `ia_feedback`
- `backend/app.py` — `import + register_blueprint` de ia
- `backend/blueprints/auth.py` — llamar `_generar_alertas(uid)` después de login exitoso
- `backend/blueprints/tratamientos.py` — llamar `_recalcular_patrones` tras POST exitoso
- `backend/blueprints/fertilizacion.py` — ídem para módulos fertilizacion y riego
- `backend/blueprints/labores.py` — ídem para módulos labores y cosecha
- `backend/blueprints/compras.py` — ídem para módulo compras
- `backend/blueprints/parcelas.py` — ídem para módulo cultivo_campana
- `frontend/screens_forms.jsx` — sugerencias + chip + feedback en 7 formularios
- `frontend/screens_home.jsx` — sección `💡 Recordatorios` sobre módulos

---

## Task 1: DB Migration — 3 nuevas tablas

**Files:**
- Modify: `backend/db.py` (al final de `init_db()`, antes del `conn.commit()` final)

- [ ] **Step 1: Localizar el final de `init_db()` en `db.py`**

Buscar la línea `conn.commit()` al final de `init_db()` (aprox. línea 795). Insertar el bloque siguiente **antes** de ese commit:

```python
    # ── ASISTENTE IA ──────────────────────────────────────────────────────────
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS ia_patrones (
            id             {_PK},
            usuario_id     INTEGER NOT NULL,
            modulo         TEXT NOT NULL,
            parcela_id     INTEGER,
            temporada      TEXT NOT NULL,
            campo          TEXT NOT NULL,
            valor_sugerido TEXT NOT NULL,
            frecuencia     INTEGER NOT NULL DEFAULT 1,
            ultima_vez     DATE,
            actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS ia_alertas (
            id         {_PK},
            usuario_id INTEGER NOT NULL,
            tipo       TEXT NOT NULL,
            parcela_id INTEGER,
            modulo     TEXT,
            mensaje    TEXT NOT NULL,
            leida      INTEGER DEFAULT 0,
            creada_en  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expira_en  TIMESTAMP
        )
    ''')
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS ia_feedback (
            id          {_PK},
            usuario_id  INTEGER NOT NULL,
            patron_id   INTEGER NOT NULL,
            accion      TEXT NOT NULL,
            valor_final TEXT,
            creado_en   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
```

- [ ] **Step 2: Arrancar el servidor y verificar que las tablas existen**

```bash
cd "H:\Proyectos\Cuaderno ex app\backend"
python -c "from db import init_db; init_db(); print('OK')"
python -c "from db import get_db; c=get_db(); print(c.execute('SELECT name FROM sqlite_master WHERE type=\'table\' AND name LIKE \'ia_%\'').fetchall())"
```

Resultado esperado: `[('ia_patrones',), ('ia_alertas',), ('ia_feedback',)]`

- [ ] **Step 3: Commit**

```bash
git add backend/db.py
git commit -m "feat(ia): add ia_patrones, ia_alertas, ia_feedback tables"
```

---

## Task 2: Crear `backend/blueprints/ia.py`

**Files:**
- Create: `backend/blueprints/ia.py`

- [ ] **Step 1: Crear el archivo completo**

```python
"""
blueprints/ia.py — Asistente IA estadístico (patrones pre-calculados, sin LLM)
"""
import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, dicts, one, USE_PG
from helpers import get_uid

bp = Blueprint('ia', __name__)

# ── Configuración ──────────────────────────────────────────────────────────────

# Campos a aprender por módulo (columnas reales de cada tabla)
CAMPOS_MODULO = {
    'tratamientos':    ['producto_comercial', 'num_registro_mapa', 'sustancia_activa',
                        'plaga_objetivo', 'dosis_valor', 'dosis_unidad', 'equipo_id', 'aplicador_id'],
    'fertilizacion':   ['tipo_fertilizante', 'producto', 'dosis_valor', 'dosis_unidad'],
    'riego':           ['tipo_riego'],
    'labores':         ['tipo_labor', 'maquinaria'],
    'cosecha':         ['destino', 'variedad'],
    'compras':         ['proveedor', 'cantidad_unidad'],
    'cultivo_campana': ['cultivo_iacs_cod', 'variedad'],
}

TABLA_MODULO = {
    'tratamientos':    'tratamientos',
    'fertilizacion':   'fertilizacion',
    'riego':           'riego',
    'labores':         'labores',
    'cosecha':         'cosecha',
    'compras':         'compras',
    'cultivo_campana': 'cultivos_campana',
}

FECHA_MODULO = {
    'tratamientos':    'fecha_aplicacion',
    'fertilizacion':   'fecha_aplicacion',
    'riego':           'fecha',
    'labores':         'fecha',
    'cosecha':         'fecha_inicio',
    'compras':         'fecha',
    'cultivo_campana': 'fecha_siembra',
}

TEMPORADA_MESES = {
    'primavera': (3, 4, 5),
    'verano':    (6, 7, 8),
    'otono':     (9, 10, 11),
    'invierno':  (12, 1, 2),
}

_HAS_DELETED_AT = {'tratamientos'}


# ── Funciones internas ─────────────────────────────────────────────────────────

def _temporada(fecha=None):
    if fecha is None:
        return _temporada(datetime.date.today())
    if isinstance(fecha, str):
        try:
            fecha = datetime.date.fromisoformat(str(fecha)[:10])
        except (ValueError, TypeError):
            return _temporada(datetime.date.today())
    mes = fecha.month
    if mes in (3, 4, 5):   return 'primavera'
    if mes in (6, 7, 8):   return 'verano'
    if mes in (9, 10, 11): return 'otono'
    return 'invierno'


def _mes_in_expr(fecha_col, meses):
    """Expresión SQL compatible SQLite y PostgreSQL para filtrar meses."""
    ph = ','.join(['?' for _ in meses])
    if USE_PG:
        return f"EXTRACT(MONTH FROM {fecha_col}::date)::int IN ({ph})"
    return f"CAST(strftime('%m', {fecha_col}) AS INTEGER) IN ({ph})"


def _recalcular_patrones(usuario_id, modulo, parcela_id, fecha_str):
    """Recalcula el valor más frecuente de cada campo para usuario+módulo+parcela+temporada.
    Llamar al final de cada POST exitoso en todos los módulos."""
    if modulo not in CAMPOS_MODULO:
        return
    campos    = CAMPOS_MODULO[modulo]
    tabla     = TABLA_MODULO[modulo]
    fecha_col = FECHA_MODULO[modulo]
    temporada = _temporada(fecha_str)
    meses     = TEMPORADA_MESES[temporada]
    mes_expr  = _mes_in_expr(fecha_col, meses)
    soft_del  = " AND deleted_at IS NULL" if modulo in _HAS_DELETED_AT else ""

    conn = get_db()
    try:
        for campo in campos:
            if modulo == 'cultivo_campana':
                # cultivos_campana no tiene user_id propio → JOIN con parcelas
                if not parcela_id:
                    continue
                sql = f"""
                    SELECT cc.{campo} AS val, COUNT(*) AS cnt, MAX(cc.{fecha_col}) AS ultima
                    FROM cultivos_campana cc
                    JOIN parcelas p ON cc.parcela_id = p.id
                    WHERE p.user_id=? AND cc.parcela_id=?
                      AND cc.{campo} IS NOT NULL AND cc.{campo} != ''
                      AND {mes_expr}
                    GROUP BY cc.{campo} ORDER BY cnt DESC, ultima DESC LIMIT 1
                """
                params = [usuario_id, parcela_id] + list(meses)
            elif parcela_id:
                sql = f"""
                    SELECT {campo} AS val, COUNT(*) AS cnt, MAX({fecha_col}) AS ultima
                    FROM {tabla}
                    WHERE user_id=? AND parcela_id=?
                      AND {campo} IS NOT NULL AND {campo} != ''
                      {soft_del} AND {mes_expr}
                    GROUP BY {campo} ORDER BY cnt DESC, ultima DESC LIMIT 1
                """
                params = [usuario_id, parcela_id] + list(meses)
            else:
                sql = f"""
                    SELECT {campo} AS val, COUNT(*) AS cnt, MAX({fecha_col}) AS ultima
                    FROM {tabla}
                    WHERE user_id=?
                      AND {campo} IS NOT NULL AND {campo} != ''
                      {soft_del} AND {mes_expr}
                    GROUP BY {campo} ORDER BY cnt DESC, ultima DESC LIMIT 1
                """
                params = [usuario_id] + list(meses)

            row = one(conn, sql, params)
            if not row or row.get('val') is None:
                continue

            # DELETE + INSERT (funciona en SQLite y PG; evita problema de NULL en UNIQUE)
            conn.execute("""
                DELETE FROM ia_patrones
                WHERE usuario_id=? AND modulo=? AND temporada=? AND campo=?
                  AND (parcela_id=? OR (parcela_id IS NULL AND ? IS NULL))
            """, (usuario_id, modulo, temporada, campo, parcela_id, parcela_id))
            conn.execute("""
                INSERT INTO ia_patrones
                    (usuario_id, modulo, parcela_id, temporada, campo, valor_sugerido, frecuencia, ultima_vez)
                VALUES (?,?,?,?,?,?,?,?)
            """, (usuario_id, modulo, parcela_id, temporada, campo,
                  str(row['val']), row['cnt'], row['ultima']))

        conn.commit()
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


def _generar_alertas(usuario_id):
    """Regenera alertas activas del usuario. Llamar en cada login exitoso."""
    conn = get_db()
    try:
        hoy     = datetime.date.today()
        expl    = one(conn, "SELECT campana_activa FROM explotacion WHERE user_id=?", (usuario_id,))
        campana = (expl or {}).get('campana_activa') or '2025/2026'

        parcelas = dicts(conn,
            "SELECT id, nombre_finca FROM parcelas WHERE user_id=? AND activa=1",
            (usuario_id,))

        for p in parcelas:
            pid    = p['id']
            nombre = p.get('nombre_finca') or f"Parcela {pid}"

            # 1. sin_registro_reciente (solo si ya hay historial, no alertar a nuevos usuarios)
            ultimo = one(conn, """
                SELECT MAX(fecha_aplicacion) AS ultima FROM tratamientos
                WHERE user_id=? AND parcela_id=? AND deleted_at IS NULL
            """, (usuario_id, pid))
            if ultimo and ultimo.get('ultima'):
                try:
                    dt   = datetime.date.fromisoformat(str(ultimo['ultima'])[:10])
                    dias = (hoy - dt).days
                    if dias > 30:
                        conn.execute(
                            "DELETE FROM ia_alertas WHERE usuario_id=? AND tipo=? AND parcela_id=?",
                            (usuario_id, 'sin_registro_reciente', pid))
                        conn.execute("""
                            INSERT INTO ia_alertas (usuario_id, tipo, parcela_id, modulo, mensaje)
                            VALUES (?,?,?,?,?)
                        """, (usuario_id, 'sin_registro_reciente', pid, 'tratamientos',
                              f"Llevas {dias} días sin registrar tratamientos en {nombre}"))
                except (ValueError, TypeError):
                    pass

            # 2. plazo_seguridad_proximo (vence en ≤7 días)
            proximos = dicts(conn, """
                SELECT producto_comercial, fecha_recoleccion_minima FROM tratamientos
                WHERE user_id=? AND parcela_id=? AND deleted_at IS NULL
                  AND fecha_recoleccion_minima IS NOT NULL AND fecha_recoleccion_minima != ''
            """, (usuario_id, pid))
            for t in proximos:
                try:
                    fm   = datetime.date.fromisoformat(str(t['fecha_recoleccion_minima'])[:10])
                    diff = (fm - hoy).days
                    if 0 <= diff <= 7:
                        conn.execute("""
                            DELETE FROM ia_alertas
                            WHERE usuario_id=? AND tipo=? AND parcela_id=? AND modulo=?
                        """, (usuario_id, 'plazo_seguridad_proximo', pid,
                              t.get('producto_comercial', '')))
                        conn.execute("""
                            INSERT INTO ia_alertas
                                (usuario_id, tipo, parcela_id, modulo, mensaje, expira_en)
                            VALUES (?,?,?,?,?,?)
                        """, (usuario_id, 'plazo_seguridad_proximo', pid,
                              t.get('producto_comercial', ''),
                              f"El plazo de seguridad de {t['producto_comercial']} en {nombre} vence el {t['fecha_recoleccion_minima']}",
                              t['fecha_recoleccion_minima']))
                except (ValueError, TypeError):
                    pass

            # 3. sin_cultivo_campana
            cultivo = one(conn, """
                SELECT cc.id FROM cultivos_campana cc
                JOIN parcelas p ON cc.parcela_id = p.id
                WHERE cc.parcela_id=? AND cc.campana=? AND p.user_id=?
            """, (pid, campana, usuario_id))
            if not cultivo:
                conn.execute(
                    "DELETE FROM ia_alertas WHERE usuario_id=? AND tipo=? AND parcela_id=?",
                    (usuario_id, 'sin_cultivo_campana', pid))
                conn.execute("""
                    INSERT INTO ia_alertas (usuario_id, tipo, parcela_id, mensaje)
                    VALUES (?,?,?,?)
                """, (usuario_id, 'sin_cultivo_campana', pid,
                      f"La parcela {nombre} no tiene cultivo de campaña asignado"))

        conn.commit()
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@bp.route('/api/ia/sugerencias', methods=['GET'])
@login_required
def get_sugerencias():
    uid       = get_uid()
    modulo    = request.args.get('modulo')
    parcela_id = request.args.get('parcela_id')

    if not modulo:
        return jsonify({"ok": False, "error": "modulo es obligatorio"}), 400

    temporada = _temporada()
    conn = get_db()

    if parcela_id:
        rows = dicts(conn, """
            SELECT id, campo, valor_sugerido FROM ia_patrones
            WHERE usuario_id=? AND modulo=? AND parcela_id=? AND temporada=?
        """, (uid, modulo, parcela_id, temporada))
    else:
        rows = dicts(conn, """
            SELECT id, campo, valor_sugerido FROM ia_patrones
            WHERE usuario_id=? AND modulo=? AND parcela_id IS NULL AND temporada=?
        """, (uid, modulo, temporada))

    conn.close()
    data = {r['campo']: {'patron_id': r['id'], 'valor': r['valor_sugerido']} for r in rows}
    return jsonify({"ok": True, "data": data})


@bp.route('/api/ia/alertas', methods=['GET'])
@login_required
def get_alertas():
    uid  = get_uid()
    conn = get_db()
    rows = dicts(conn, """
        SELECT id, tipo, parcela_id, modulo, mensaje, creada_en, expira_en
        FROM ia_alertas
        WHERE usuario_id=? AND leida=0
          AND (expira_en IS NULL OR expira_en > CURRENT_TIMESTAMP)
        ORDER BY
          CASE tipo
            WHEN 'plazo_seguridad_proximo' THEN 1
            WHEN 'sin_cultivo_campana'     THEN 2
            ELSE 3
          END, creada_en DESC
        LIMIT 3
    """, (uid,))
    conn.close()
    return jsonify({"ok": True, "data": rows})


@bp.route('/api/ia/alertas/<int:aid>/leer', methods=['POST'])
@login_required
def marcar_alerta_leida(aid):
    uid  = get_uid()
    conn = get_db()
    conn.execute("UPDATE ia_alertas SET leida=1 WHERE id=? AND usuario_id=?", (aid, uid))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


@bp.route('/api/ia/feedback', methods=['POST'])
@login_required
def post_feedback():
    uid  = get_uid()
    data = request.json or {}
    patron_id   = data.get('patron_id')
    accion      = data.get('accion')
    valor_final = data.get('valor_final')

    if not patron_id or accion not in ('aceptada', 'ignorada', 'modificada'):
        return jsonify({"ok": False, "error": "patron_id y accion válida son obligatorios"}), 400

    conn   = get_db()
    patron = one(conn, "SELECT id FROM ia_patrones WHERE id=? AND usuario_id=?", (patron_id, uid))
    if not patron:
        conn.close()
        return jsonify({"ok": False, "error": "Patrón no encontrado"}), 404

    conn.execute("""
        INSERT INTO ia_feedback (usuario_id, patron_id, accion, valor_final)
        VALUES (?,?,?,?)
    """, (uid, patron_id, accion, valor_final))
    conn.commit(); conn.close()
    return jsonify({"ok": True})
```

- [ ] **Step 2: Verificar sintaxis**

```bash
cd "H:\Proyectos\Cuaderno ex app\backend"
python -c "from blueprints.ia import bp, _recalcular_patrones, _generar_alertas; print('OK')"
```

Resultado esperado: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/blueprints/ia.py
git commit -m "feat(ia): add ia blueprint with pattern calc, alert gen, and 4 endpoints"
```

---

## Task 3: Registrar blueprint en `app.py`

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: Añadir import y register**

En `backend/app.py`, después de la línea `from blueprints.uhc import bp as uhc_bp`, añadir:

```python
from blueprints.ia import bp as ia_bp
```

Y después de `app.register_blueprint(uhc_bp)`, añadir:

```python
app.register_blueprint(ia_bp)
```

- [ ] **Step 2: Verificar arranque**

```bash
cd "H:\Proyectos\Cuaderno ex app\backend"
python -c "import app; print('blueprints OK')"
```

Resultado esperado: `blueprints OK` (sin errores)

- [ ] **Step 3: Verificar endpoint desde servidor**

```bash
cd "H:\Proyectos\Cuaderno ex app\backend"
python app.py &
curl -s http://127.0.0.1:5000/api/ia/alertas
# → {"ok": false} o redirect al login (cualquiera confirma que la ruta existe)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app.py
git commit -m "feat(ia): register ia blueprint"
```

---

## Task 4: Hook en `tratamientos.py`

**Files:**
- Modify: `backend/blueprints/tratamientos.py`

- [ ] **Step 1: Añadir import al inicio del archivo**

Después de `from helpers import get_uid, _to_real`, añadir:

```python
from blueprints.ia import _recalcular_patrones
```

- [ ] **Step 2: Hook en el POST de tratamiento individual**

En `manage_tratamientos`, localizar:

```python
    new_id = _insert_tratamiento(c, uid, data, data.get('parcela_id'), data.get('parcela_etiqueta'))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201
```

Reemplazar con:

```python
    new_id = _insert_tratamiento(c, uid, data, data.get('parcela_id'), data.get('parcela_etiqueta'))
    conn.commit()
    conn.close()
    _recalcular_patrones(uid, 'tratamientos', data.get('parcela_id'), data.get('fecha_aplicacion'))
    return jsonify({"status": "ok", "id": new_id}), 201
```

- [ ] **Step 3: Hook en el POST UHC (múltiples parcelas)**

En `manage_tratamientos`, localizar el bloque UHC:

```python
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201
```

Reemplazar con:

```python
        conn.commit()
        conn.close()
        for p in parcelas:
            _recalcular_patrones(uid, 'tratamientos', p['id'], data.get('fecha_aplicacion'))
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201
```

- [ ] **Step 4: Commit**

```bash
git add backend/blueprints/tratamientos.py
git commit -m "feat(ia): hook _recalcular_patrones in tratamientos POST"
```

---

## Task 5: Hook en `fertilizacion.py`

**Files:**
- Modify: `backend/blueprints/fertilizacion.py`

- [ ] **Step 1: Añadir import al inicio**

```python
from blueprints.ia import _recalcular_patrones
```

- [ ] **Step 2: Hook en POST de fertilizacion**

En `manage_fertilizacion`, localizar:

```python
    conn.commit(); new_id = c.lastrowid; conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201
```

(el primero, correspondiente al POST de fertilizacion)

Reemplazar con:

```python
    conn.commit(); new_id = c.lastrowid; conn.close()
    _recalcular_patrones(uid, 'fertilizacion', data.get('parcela_id'), data.get('fecha_aplicacion'))
    return jsonify({"status": "ok", "id": new_id}), 201
```

- [ ] **Step 3: Hook en POST de riego**

En `manage_riego`, localizar:

```python
    conn.commit(); new_id = c.lastrowid; conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201
```

Reemplazar con:

```python
    conn.commit(); new_id = c.lastrowid; conn.close()
    _recalcular_patrones(uid, 'riego', data.get('parcela_id'), data.get('fecha'))
    return jsonify({"status": "ok", "id": new_id}), 201
```

- [ ] **Step 4: Commit**

```bash
git add backend/blueprints/fertilizacion.py
git commit -m "feat(ia): hook _recalcular_patrones in fertilizacion and riego POST"
```

---

## Task 6: Hook en `labores.py`

**Files:**
- Modify: `backend/blueprints/labores.py`

- [ ] **Step 1: Añadir import al inicio**

```python
from blueprints.ia import _recalcular_patrones
```

- [ ] **Step 2: Hook en POST de labores**

En `manage_labores`, localizar:

```python
    conn.commit(); new_id = c.lastrowid; conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201
```

(el primero, labores)

Reemplazar con:

```python
    conn.commit(); new_id = c.lastrowid; conn.close()
    _recalcular_patrones(uid, 'labores', data.get('parcela_id'), data.get('fecha'))
    return jsonify({"status": "ok", "id": new_id}), 201
```

- [ ] **Step 3: Hook en POST de cosecha**

En `manage_cosecha`, localizar:

```python
    conn.commit(); new_id = c.lastrowid; conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201
```

Reemplazar con:

```python
    conn.commit(); new_id = c.lastrowid; conn.close()
    _recalcular_patrones(uid, 'cosecha', data.get('parcela_id'), data.get('fecha_inicio'))
    return jsonify({"status": "ok", "id": new_id}), 201
```

- [ ] **Step 4: Commit**

```bash
git add backend/blueprints/labores.py
git commit -m "feat(ia): hook _recalcular_patrones in labores and cosecha POST"
```

---

## Task 7: Hook en `compras.py`

**Files:**
- Modify: `backend/blueprints/compras.py`

- [ ] **Step 1: Añadir import al inicio**

```python
from blueprints.ia import _recalcular_patrones
```

- [ ] **Step 2: Hook en POST de compras**

En el handler POST de compras, localizar:

```python
    conn.commit(); new_id = c.lastrowid; conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201
```

Reemplazar con:

```python
    conn.commit(); new_id = c.lastrowid; conn.close()
    _recalcular_patrones(uid, 'compras', None, data.get('fecha'))
    return jsonify({"status": "ok", "id": new_id}), 201
```

(compras no tiene parcela_id, se pasa `None`)

- [ ] **Step 3: Commit**

```bash
git add backend/blueprints/compras.py
git commit -m "feat(ia): hook _recalcular_patrones in compras POST"
```

---

## Task 8: Hook en `parcelas.py` (cultivo_campana)

**Files:**
- Modify: `backend/blueprints/parcelas.py`

- [ ] **Step 1: Añadir import al inicio**

```python
from blueprints.ia import _recalcular_patrones
```

- [ ] **Step 2: Hook en POST de cultivos-campana**

En `manage_cultivos`, localizar:

```python
    new_id = c.lastrowid
    conn.commit(); conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201
```

Reemplazar con:

```python
    new_id = c.lastrowid
    conn.commit(); conn.close()
    _recalcular_patrones(uid, 'cultivo_campana', parcela_id, data.get('fecha_siembra'))
    return jsonify({"status": "ok", "id": new_id}), 201
```

- [ ] **Step 3: Commit**

```bash
git add backend/blueprints/parcelas.py
git commit -m "feat(ia): hook _recalcular_patrones in cultivos-campana POST"
```

---

## Task 9: Hook en `auth.py` — alertas en login

**Files:**
- Modify: `backend/blueprints/auth.py`

- [ ] **Step 1: Modificar `auth_login`**

En `auth_login`, localizar:

```python
    login_user(user, remember=True)
    return jsonify({"id": user.id, "email": user.email,
                    "nombre": user.nombre, "role": user.role})
```

Reemplazar con:

```python
    login_user(user, remember=True)
    try:
        from blueprints.ia import _generar_alertas
        _generar_alertas(u['id'])
    except Exception:
        pass  # no bloquear login si falla
    return jsonify({"id": user.id, "email": user.email,
                    "nombre": user.nombre, "role": user.role})
```

- [ ] **Step 2: Verificar que el login sigue funcionando**

Arrancar servidor (`python app.py`) y hacer login desde el navegador en `http://127.0.0.1:5000`. Debe entrar sin error. Verificar en consola del servidor que no hay traceback.

- [ ] **Step 3: Commit**

```bash
git add backend/blueprints/auth.py
git commit -m "feat(ia): generate alerts on login"
```

---

## Task 10: Frontend — sugerencias en formularios

**Files:**
- Modify: `frontend/screens_forms.jsx`

El patrón es idéntico en los 7 formularios. Se añade a cada uno:
1. Estado `sugerencias` y `sugeridosTocados`
2. `useEffect` que fetcha `/api/ia/sugerencias` al abrir formulario nuevo (no en edición)
3. Aplica valores a campos vacíos
4. Chip `💡 Sugerido` debajo de cada campo con valor sugerido
5. `postFeedback()` llamado antes de cerrar tras guardado exitoso

### Formularios y sus módulos

| Función | modulo | campo_fecha | campos_con_chip |
|---------|--------|-------------|-----------------|
| `FormTratamiento` | `tratamientos` | parcela_id | producto_comercial, num_registro_mapa, sustancia_activa, plaga_objetivo, dosis_valor, dosis_unidad, equipo_id, aplicador_id |
| `FormFertilizacion` | `fertilizacion` | parcela_id | tipo_fertilizante, producto, dosis_valor, dosis_unidad |
| `FormRiego` | `riego` | parcela_id | tipo_riego |
| `FormLabor` | `labores` | parcela_id | tipo_labor, maquinaria |
| `FormCosecha` | `cosecha` | parcela_id | destino, variedad |
| `FormCompra` | `compras` | — (no parcela) | proveedor, cantidad_unidad |
| `FormCultivoCampana` | `cultivo_campana` | parcela_id | cultivo_iacs_cod, variedad |

### Bloque de código a añadir en cada formulario (adaptar `MODULO` y `CAMPOS`)

- [ ] **Step 1: Añadir el helper `SugChip` UNA SOLA VEZ, justo antes de `function ScreenForms`**

Insertar en `screens_forms.jsx` antes de `function ScreenForms({ modulo, record, campana, onClose })`:

```javascript
function SugChip({ campo, sugerencias, valorActual }) {
    const item = sugerencias && sugerencias[campo];
    if (!item || String(valorActual) !== String(item.valor)) return null;
    return (
        <span style={{ fontSize: '0.68rem', color: '#aaa', display: 'block', marginTop: 2, lineHeight: 1.2 }}>
            💡 Sugerido
        </span>
    );
}
```

- [ ] **Step 2: Añadir estado y lógica a `FormTratamiento`**

Al inicio de `FormTratamiento`, tras la declaración de estados existentes, añadir:

```javascript
    const [sugerencias, setSugerencias] = React.useState({});

    React.useEffect(() => {
        if (isEdit) return;
        const qs = new URLSearchParams({ modulo: 'tratamientos' });
        if (f.parcela_id) qs.append('parcela_id', f.parcela_id);
        fetch(`/api/ia/sugerencias?${qs}`, { credentials: 'include' })
            .then(r => r.ok ? r.json() : { ok: false })
            .then(d => {
                if (!d.ok || !d.data) return;
                setSugerencias(d.data);
                const patch = {};
                for (const [campo, item] of Object.entries(d.data)) {
                    if (!f[campo]) patch[campo] = item.valor;
                }
                if (Object.keys(patch).length) setF(x => ({ ...x, ...patch }));
            })
            .catch(() => {});
    }, [f.parcela_id, isEdit]);

    const postFeedbackTratamiento = () => {
        for (const [campo, item] of Object.entries(sugerencias)) {
            const val = f[campo];
            const accion = !val ? 'ignorada' : String(val) === String(item.valor) ? 'aceptada' : 'modificada';
            fetch('/api/ia/feedback', {
                method: 'POST', credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ patron_id: item.patron_id, accion, valor_final: accion === 'modificada' ? String(val) : null })
            }).catch(() => {});
        }
    };
```

En el handler de guardado exitoso de `FormTratamiento` (justo antes de `onClose(...)`), añadir:

```javascript
                    postFeedbackTratamiento();
```

Añadir `<SugChip campo="producto_comercial" sugerencias={sugerencias} valorActual={f.producto_comercial} />` debajo del input de `producto_comercial`, y repetir para cada campo de la lista.

- [ ] **Step 3: Repetir patrón en `FormFertilizacion`**

Mismo bloque de estado/efecto/postFeedback, cambiando:
- `modulo: 'fertilizacion'`
- Chips para: `tipo_fertilizante`, `producto`, `dosis_valor`, `dosis_unidad`
- nombre de función: `postFeedbackFertilizacion`

- [ ] **Step 4: Repetir en `FormRiego`**

- `modulo: 'riego'`
- Chip solo para: `tipo_riego`
- nombre: `postFeedbackRiego`

- [ ] **Step 5: Repetir en `FormLabor`**

- `modulo: 'labores'`
- Chips para: `tipo_labor`, `maquinaria`
- nombre: `postFeedbackLabor`

- [ ] **Step 6: Repetir en `FormCosecha`**

- `modulo: 'cosecha'`
- Chips para: `destino`, `variedad`
- nombre: `postFeedbackCosecha`

- [ ] **Step 7: Repetir en `FormCompra`**

- `modulo: 'compras'`
- Sin `parcela_id` en query (no tiene parcela)
- Chips para: `proveedor`, `cantidad_unidad`
- nombre: `postFeedbackCompra`

- [ ] **Step 8: Repetir en `FormCultivoCampana`**

- `modulo: 'cultivo_campana'`
- Chips para: `cultivo_iacs_cod`, `variedad`
- nombre: `postFeedbackCultivo`

- [ ] **Step 9: Compilar JSX**

```bash
cd "H:\Proyectos\Cuaderno ex app\frontend"
npm run build
```

Sin errores de compilación.

- [ ] **Step 10: Verificar en navegador**

1. Crear un tratamiento (formulario nuevo) → no debe aparecer chip (sin historial)
2. Guardar el tratamiento
3. Abrir formulario de nuevo tratamiento para la misma parcela → deben aparecer chips `💡 Sugerido` con los valores del anterior

- [ ] **Step 11: Commit**

```bash
git add frontend/screens_forms.jsx
git commit -m "feat(ia): prerrellenado con sugerencias + chip 'Sugerido' en todos los formularios"
```

---

## Task 11: Frontend — sección Recordatorios en `ScreenHome`

**Files:**
- Modify: `frontend/screens_home.jsx`

- [ ] **Step 1: Añadir estado de alertas en `ScreenHome`**

En `ScreenHome`, tras los estados existentes, añadir:

```javascript
    const [iaAlertas, setIaAlertas] = React.useState([]);
```

- [ ] **Step 2: Añadir useEffect para cargar alertas**

Añadir junto a los demás `useEffect` de carga inicial:

```javascript
    useEffect(() => {
        fetch('/api/ia/alertas', { credentials: 'include' })
            .then(r => r.ok ? r.json() : { ok: false })
            .then(d => { if (d.ok) setIaAlertas(d.data || []); })
            .catch(() => {});
    }, []);

    const handleDismissAlerta = (id) => {
        fetch(`/api/ia/alertas/${id}/leer`, { method: 'POST', credentials: 'include' }).catch(() => {});
        setIaAlertas(prev => prev.filter(a => a.id !== id));
    };
```

- [ ] **Step 3: Añadir sección Recordatorios en el render de ScreenHome**

Localizar el punto del render donde aparece la cuadrícula de módulos o el área de acciones rápidas. Insertar justo encima:

```javascript
                {iaAlertas.length > 0 && (
                    <div style={{ padding: '0 16px 4px' }}>
                        <div style={{ fontSize: '0.75rem', color: '#666', fontWeight: 600, marginBottom: 6, letterSpacing: '0.03em', textTransform: 'uppercase' }}>
                            💡 Recordatorios
                        </div>
                        {iaAlertas.map(a => (
                            <div key={a.id} style={{
                                background: '#fff8e1',
                                border: '1px solid #ffe082',
                                borderRadius: 10,
                                padding: '10px 12px',
                                marginBottom: 8,
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: 8,
                            }}>
                                <span style={{ flex: 1, fontSize: '0.85rem', color: '#333', lineHeight: 1.4 }}>{a.mensaje}</span>
                                <button
                                    onClick={() => handleDismissAlerta(a.id)}
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: '#bbb', lineHeight: 1, padding: 0, flexShrink: 0, marginTop: -2 }}
                                    aria-label="Descartar"
                                >✕</button>
                            </div>
                        ))}
                    </div>
                )}
```

- [ ] **Step 4: Compilar JSX**

```bash
cd "H:\Proyectos\Cuaderno ex app\frontend"
npm run build
```

- [ ] **Step 5: Verificar en navegador**

1. Hacer login → si hay parcelas activas sin cultivo de campaña, deben aparecer las tarjetas amarillas
2. Hacer clic en `✕` de una tarjeta → desaparece sin recargar
3. Si no hay alertas, la sección no aparece

- [ ] **Step 6: Commit**

```bash
git add frontend/screens_home.jsx
git commit -m "feat(ia): Recordatorios section in ScreenHome with dismiss support"
```

---

## Task 12: Smoke test integral

- [ ] **Step 1: Arrancar servidor local**

```bash
cd "H:\Proyectos\Cuaderno ex app\backend"
python app.py
```

- [ ] **Step 2: Flujo completo de sugerencias**

1. Login como Lourdes (`lourdelamo@gmail.com`)
2. Abrir formulario de Tratamiento para una parcela → los campos deben venir vacíos (aún no hay historial)
3. Guardar un tratamiento completo
4. Abrir de nuevo el formulario de Tratamiento para la misma parcela → los campos deben aparecer prerrellenados con chips `💡 Sugerido`

- [ ] **Step 3: Flujo de alertas**

1. Verificar en la BD que hay alertas: `SELECT * FROM ia_alertas WHERE usuario_id=...`
2. Si no hay parcelas sin cultivo, crear una y hacer login de nuevo → debe aparecer la alerta

- [ ] **Step 4: Verificar endpoints directamente**

```bash
# Con sesión activa (requiere cookie de sesión válida)
curl -s http://127.0.0.1:5000/api/ia/sugerencias?modulo=tratamientos
curl -s http://127.0.0.1:5000/api/ia/alertas
```

- [ ] **Step 5: Commit final**

```bash
git add -A
git commit -m "feat(ia): asistente IA estadístico completo — sugerencias + recordatorios"
```

---

## Self-Review

### Spec coverage

| Requisito spec | Task que lo cubre |
|---------------|-------------------|
| 3 tablas BD | Task 1 |
| `_temporada()` | Task 2 |
| `_recalcular_patrones` | Task 2 |
| Hook POST todos los módulos | Tasks 4–8 |
| `GET /api/ia/sugerencias` | Task 2 |
| Prerrellenado + chip Sugerido | Task 10 |
| `POST /api/ia/feedback` | Task 2 + Task 10 |
| `_generar_alertas` en login | Tasks 2 + 9 |
| `GET /api/ia/alertas` | Task 2 |
| `POST /api/ia/alertas/<id>/leer` | Task 2 |
| Tarjetas en pantalla inicio | Task 11 |
| Sin LLM, coste cero | ✅ (solo SQL + Python) |
| Sugerencia invisible (no sabe que existe IA) | ✅ (solo chip gris sutil) |

### Gaps detectados

- **cultivo_campana en FormCultivoCampana**: el campo `cultivo_iacs_cod` se elige de un selector IACS, no se teclea. Verificar que la comparación string funciona al aplicar la sugerencia (puede requerir convertir a string antes de comparar).
- **equipo_id / aplicador_id en FormTratamiento**: son IDs numéricos de selectores. El chip se mostrará cuando el id seleccionado coincida. El usuario no verá el nombre, solo el ID internamente. Esto es correcto y funciona.
- **abonado (plan abonado)**: no incluido en la spec de patrones, no se hook-ea.
