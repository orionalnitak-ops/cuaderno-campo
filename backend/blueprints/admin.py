"""
blueprints/admin.py — /api/admin/*
"""
import datetime
import bcrypt

from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user
from db import get_db, one, dicts
from helpers import admin_required
from extensions import compute_plan_status

bp = Blueprint('admin', __name__)


@bp.route('/api/admin/users', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_users():
    conn = get_db()
    if request.method == 'GET':
        users = dicts(conn, "SELECT id,email,nombre,role,active,created_at,plan,trial_ends_at,subscription_ends_at FROM users ORDER BY created_at DESC")
        for u in users:
            uid = u['id']
            t = one(conn, "SELECT COUNT(*) as n FROM tratamientos WHERE user_id=?", (uid,))
            p = one(conn, "SELECT COUNT(*) as n FROM parcelas WHERE user_id=? AND activa=1", (uid,))
            l = one(conn, "SELECT COUNT(*) as n FROM labores WHERE user_id=?", (uid,))
            u['stats'] = {
                "tratamientos": t['n'] if t else 0,
                "parcelas": p['n'] if p else 0,
                "labores": l['n'] if l else 0,
            }
            u['plan_label'], u['plan_active'] = compute_plan_status(u['plan'], u['trial_ends_at'], u['role'])
        conn.close()
        return jsonify(users)

    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    nombre = data.get('nombre') or ''
    password = data.get('password') or ''
    role = data.get('role', 'agricultor')

    if not email or not password:
        conn.close()
        return jsonify({"error": "Email y contraseña son obligatorios"}), 400

    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    trial_ends = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (email, password_hash, nombre, role, plan, trial_ends_at) VALUES (?,?,?,?,?,?)",
            (email, pw_hash, nombre, role, 'trial', trial_ends.strftime('%Y-%m-%d %H:%M:%S'))
        )
        new_id = c.lastrowid
        # Crear explotación vacía para el nuevo usuario
        c.execute("INSERT INTO explotacion (user_id, titular, campana_activa) VALUES (?,?,?)",
                  (new_id, nombre, '2025/2026'))
        conn.commit()
    except Exception as e:
        conn.close()
        if 'UNIQUE' in str(e):
            return jsonify({"error": "Ya existe un usuario con ese email"}), 409
        import logging
        logging.getLogger(__name__).error("Error creando usuario: %s", e)
        return jsonify({"error": "Error interno al crear el usuario"}), 500
    conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/admin/users/<int:uid>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def admin_user(uid):
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("UPDATE users SET active=0 WHERE id=?", (uid,))
        conn.commit(); conn.close()
        return jsonify({"status": "ok"})

    data = request.json or {}
    sets, vals = [], []
    if 'nombre' in data:
        sets.append('nombre=?'); vals.append(data['nombre'])
    if 'role' in data:
        sets.append('role=?'); vals.append(data['role'])
    if 'active' in data:
        sets.append('active=?'); vals.append(1 if data['active'] else 0)
    if data.get('password'):
        sets.append('password_hash=?')
        vals.append(bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8'))
    if sets:
        conn.execute(f"UPDATE users SET {','.join(sets)} WHERE id=?", vals + [uid])
        conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@bp.route('/api/admin/users/<int:uid>/delete-permanent', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_permanent(uid):
    """Borra completamente un usuario y todos sus datos."""
    conn = get_db()
    try:
        row = conn.execute("SELECT nombre FROM users WHERE id=?", (uid,)).fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Usuario no encontrado"}), 404
        nombre = row[0]
        # cultivos_campana no tiene user_id, va por parcela_id
        conn.execute("DELETE FROM cultivos_campana WHERE parcela_id IN (SELECT id FROM parcelas WHERE user_id=?)", (uid,))
        # resto de tablas con user_id directo, en orden de dependencia
        for t in ['riego', 'abonado', 'cosecha', 'tratamientos', 'fertilizacion',
                  'labores', 'compras', 'equipos', 'aplicadores', 'parcelas', 'explotacion']:
            conn.execute(f"DELETE FROM {t} WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "usuario": nombre})
    except Exception as e:
        try: conn.rollback()
        except: pass
        conn.close()
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route('/api/admin/switch-user/<int:target_id>', methods=['POST'])
@login_required
@admin_required
def admin_switch_user(target_id):
    session['impersonate_id'] = target_id
    return jsonify({"status": "ok"})


@bp.route('/api/admin/switch-back', methods=['POST'])
@login_required
@admin_required
def admin_switch_back():
    session.pop('impersonate_id', None)
    return jsonify({"status": "ok"})


@bp.route('/api/admin/users/<int:uid>/reset-cuaderno', methods=['POST'])
@login_required
@admin_required
def admin_reset_cuaderno(uid):
    """Borra todos los datos agrícolas del usuario conservando cuenta y explotación."""
    conn = get_db()
    try:
        row = conn.execute("SELECT nombre FROM users WHERE id=?", (uid,)).fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Usuario no encontrado"}), 404
        nombre = row[0]
        conn.execute("DELETE FROM cultivos_campana WHERE parcela_id IN (SELECT id FROM parcelas WHERE user_id=?)", (uid,))
        for t in ['riego', 'abonado', 'cosecha', 'tratamientos', 'fertilizacion',
                  'labores', 'compras', 'equipos', 'aplicadores', 'parcelas']:
            conn.execute(f"DELETE FROM {t} WHERE user_id=?", (uid,))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "usuario": nombre})
    except Exception as e:
        try: conn.rollback()
        except: pass
        conn.close()
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route('/api/admin/users/<int:uid>/export/pdf')
@login_required
@admin_required
def admin_export_pdf(uid):
    from export_pdf import export_pdf
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE id=? AND active=1", (uid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Usuario no encontrado"}), 404
    campana = request.args.get('campana', '2025/2026')
    return export_pdf(uid, campana)
