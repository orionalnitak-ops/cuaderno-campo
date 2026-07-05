"""
blueprints/auth.py — /api/auth/* y /api/account/*
"""
import io
import json
import datetime
import bcrypt

from flask import Blueprint, jsonify, request, session, send_file
from flask_login import login_user, logout_user, login_required, current_user
from db import get_db, one, dicts
from extensions import User, limiter
from helpers import get_uid

bp = Blueprint('auth', __name__)


@bp.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def auth_login():
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').encode('utf-8')

    conn = get_db()
    u = one(conn, "SELECT * FROM users WHERE email=? AND active=1", (email,))
    conn.close()

    if not u or not bcrypt.checkpw(password, u['password_hash'].encode('utf-8')):
        return jsonify({"error": "Email o contraseña incorrectos"}), 401

    user = User(u['id'], u['email'], u['nombre'], u['role'], u['active'],
                u.get('plan', 'trial'), u.get('trial_ends_at'), u.get('subscription_ends_at'))
    login_user(user, remember=True)
    try:
        from blueprints.ia import _generar_alertas
        _generar_alertas(u['id'])
    except Exception:
        pass
    return jsonify({"id": user.id, "email": user.email,
                    "nombre": user.nombre, "role": user.role})


@bp.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def auth_register():
    data     = request.json or {}
    nombre   = (data.get('nombre') or '').strip()
    email    = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '')

    if not nombre:
        return jsonify({"error": "El nombre es obligatorio"}), 400
    if not email or '@' not in email:
        return jsonify({"error": "Email no válido"}), 400
    if len(password) < 8:
        return jsonify({"error": "La contraseña debe tener al menos 8 caracteres"}), 400

    conn = get_db()
    existing = one(conn, "SELECT id FROM users WHERE email=?", (email,))
    if existing:
        conn.close()
        return jsonify({"error": "Ya existe una cuenta con ese email"}), 409

    pw_hash    = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    trial_ends = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (email, password_hash, nombre, role, plan, trial_ends_at) VALUES (?,?,?,?,?,?)",
            (email, pw_hash, nombre, 'agricultor', 'trial', trial_ends.strftime('%Y-%m-%d %H:%M:%S'))
        )
        new_id = c.lastrowid
        c.execute("INSERT INTO explotacion (user_id, campana_activa) VALUES (?,?)",
                  (new_id, '2025/2026'))
        conn.commit()
    except Exception as e:
        conn.close()
        import logging
        logging.getLogger(__name__).error("Register error: %s", e)
        return jsonify({"error": "Error al crear la cuenta"}), 500

    u = one(conn, "SELECT * FROM users WHERE id=?", (new_id,))
    conn.close()
    user = User(u['id'], u['email'], u['nombre'], u['role'], u['active'],
                u.get('plan', 'trial'), u.get('trial_ends_at'), u.get('subscription_ends_at'))
    login_user(user, remember=True)
    te = user.trial_ends_at
    return jsonify({
        "id": user.id, "email": user.email, "nombre": user.nombre, "role": user.role,
        "plan": user.plan_label(), "plan_raw": user.plan,
        "trial_ends_at": (te.isoformat() if hasattr(te, 'isoformat') else str(te)) if te else None,
        "plan_active": user.plan_is_active(), "impersonating": None,
        "allows_multi": user.plan_allows_multi(),
    }), 201


@bp.route('/api/auth/logout', methods=['POST'])
@login_required
def auth_logout():
    session.pop('impersonate_id', None)
    logout_user()
    return jsonify({"status": "ok"})


@bp.route('/api/auth/me')
@login_required
def auth_me():
    imp_id = session.get('impersonate_id') if current_user.role == 'admin' else None
    imp_info = None
    if imp_id:
        conn = get_db()
        t = one(conn, "SELECT id, email, nombre FROM users WHERE id=?", (imp_id,))
        conn.close()
        if t:
            imp_info = t
    trial_ends = None
    if current_user.trial_ends_at:
        te = current_user.trial_ends_at
        trial_ends = te.isoformat() if hasattr(te, 'isoformat') else str(te)
    return jsonify({
        "id": current_user.id,
        "email": current_user.email,
        "nombre": current_user.nombre,
        "role": current_user.role,
        "impersonating": imp_info,
        "plan": current_user.plan_label(),
        "plan_raw": current_user.plan,
        "trial_ends_at": trial_ends,
        "plan_active": current_user.plan_is_active(),
        "allows_multi": current_user.plan_allows_multi(),
    })


@bp.route('/api/auth/change-password', methods=['POST'])
@login_required
def auth_change_password():
    data = request.json or {}
    old_pw = (data.get('old_password') or '').encode('utf-8')
    new_pw = (data.get('new_password') or '').encode('utf-8')
    if len(new_pw) < 8:
        return jsonify({"error": "La nueva contraseña debe tener al menos 8 caracteres"}), 400
    conn = get_db()
    u = one(conn, "SELECT * FROM users WHERE id=?", (current_user.id,))
    if not u or not bcrypt.checkpw(old_pw, u['password_hash'].encode('utf-8')):
        conn.close()
        return jsonify({"error": "Contraseña actual incorrecta"}), 401
    new_hash = bcrypt.hashpw(new_pw, bcrypt.gensalt()).decode('utf-8')
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, current_user.id))
    conn.commit(); conn.close()
    return jsonify({"status": "ok"})


@bp.route('/api/account/export-data', methods=['GET'])
@login_required
def account_export_data():
    """GDPR Art. 20 — portabilidad de datos. Devuelve todos los datos del usuario en JSON."""
    uid = current_user.id
    conn = get_db()
    export = {
        "usuario":         one(conn, "SELECT id,email,nombre,role,plan,created_at FROM users WHERE id=?", (uid,)),
        "explotacion":     dicts(conn, "SELECT * FROM explotacion WHERE user_id=?", (uid,)),
        "parcelas":        dicts(conn, "SELECT * FROM parcelas WHERE user_id=?", (uid,)),
        "tratamientos":    dicts(conn, "SELECT * FROM tratamientos WHERE user_id=? AND deleted_at IS NULL", (uid,)),
        "fertilizacion":   dicts(conn, "SELECT * FROM fertilizacion WHERE user_id=? AND deleted_at IS NULL", (uid,)),
        "abonado":         dicts(conn, "SELECT * FROM abonado WHERE user_id=? AND deleted_at IS NULL", (uid,)),
        "riego":           dicts(conn, "SELECT * FROM riego WHERE user_id=?", (uid,)),
        "labores":         dicts(conn, "SELECT * FROM labores WHERE user_id=?", (uid,)),
        "cosecha":         dicts(conn, "SELECT * FROM cosecha WHERE user_id=?", (uid,)),
        "compras":         dicts(conn, "SELECT * FROM compras WHERE user_id=? AND deleted_at IS NULL", (uid,)),
        "cultivos_campana": dicts(conn, """SELECT cc.* FROM cultivos_campana cc
                                           JOIN parcelas p ON cc.parcela_id=p.id
                                           WHERE p.user_id=?""", (uid,)),
        "aplicadores":     dicts(conn, "SELECT * FROM aplicadores WHERE user_id=?", (uid,)),
        "equipos":         dicts(conn, "SELECT * FROM equipos WHERE user_id=?", (uid,)),
        "exportado_el":    datetime.datetime.utcnow().isoformat() + "Z",
        "normativa":       "RGPD Art. 20 — Derecho a la portabilidad de datos",
    }
    conn.close()
    buf = io.BytesIO(json.dumps(export, ensure_ascii=False, indent=2, default=str).encode('utf-8'))
    return send_file(buf, as_attachment=True,
                     download_name=f"datos_cuaderno_{uid}.json",
                     mimetype='application/json')


@bp.route('/api/account/delete-account', methods=['DELETE'])
@login_required
def account_delete():
    """GDPR Art. 17 — derecho de supresión. Borra todos los datos del usuario y desactiva la cuenta."""
    uid = current_user.id
    conn = get_db()
    tables_soft = ['tratamientos', 'fertilizacion', 'abonado', 'compras']
    for t in tables_soft:
        conn.execute(f"UPDATE {t} SET deleted_at=CURRENT_TIMESTAMP WHERE user_id=? AND deleted_at IS NULL", (uid,))
    for t in ['labores', 'riego', 'cosecha', 'cultivos_campana', 'aplicadores', 'equipos']:
        try:
            conn.execute(f"DELETE FROM {t} WHERE user_id=?", (uid,))
        except Exception:
            pass
    conn.execute("UPDATE parcelas SET activa=0 WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM explotacion WHERE user_id=?", (uid,))
    conn.execute(
        "UPDATE users SET active=0, email=?, nombre='[eliminado]', password_hash='', "
        "stripe_customer_id=NULL, stripe_subscription_id=NULL WHERE id=?",
        (f"deleted_{uid}_{int(datetime.datetime.utcnow().timestamp())}@borrado.invalid", uid)
    )
    conn.commit(); conn.close()
    logout_user()
    return jsonify({"status": "ok", "mensaje": "Cuenta y datos eliminados conforme al RGPD Art. 17"})
