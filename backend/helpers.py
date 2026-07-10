"""
helpers.py — Decoradores y funciones de utilidad compartidas entre blueprints.
"""
from functools import wraps
from flask import jsonify, session
from flask_login import current_user
from db import get_db, one


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({"error": "No autorizado"}), 403
        return f(*args, **kwargs)
    return decorated


def get_uid():
    """Devuelve el user_id efectivo (admite impersonación del admin)."""
    if current_user.is_authenticated and current_user.role == 'admin':
        imp = session.get('impersonate_id')
        if imp:
            return imp
    return current_user.id


def requires_active_plan(f):
    """Decorador para rutas GET que también requieren suscripción activa (ej. exportaciones)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.plan_is_active():
            return jsonify({"error": "subscription_required", "plan": current_user.plan_label()}), 403
        return f(*args, **kwargs)
    return decorated


def _to_real(v):
    """Parsea float desde input de usuario, aceptando coma decimal (locale español)."""
    if v is None or v == '':
        return None
    try:
        return float(str(v).replace(',', '.'))
    except (ValueError, TypeError):
        return None


def resolve_default_explotacion(conn, uid):
    """Devuelve el id de la explotación por defecto del usuario (menor orden/id), o None."""
    row = one(conn, "SELECT id FROM explotacion WHERE user_id=? ORDER BY orden, id LIMIT 1", (uid,))
    return row['id'] if row else None


def get_active_explotacion_id(conn=None):
    """Devuelve el id de la explotación activa para el usuario efectivo.

    - Lee `session['active_explotacion_id']` y valida que pertenece al usuario.
    - Si no hay selección válida (o el usuario es mono-explotación), devuelve la
      explotación por defecto del usuario.
    - Devuelve None si el usuario aún no tiene ninguna explotación.
    """
    uid = get_uid()
    own_conn = conn is None
    if own_conn:
        conn = get_db()
    try:
        sel = session.get('active_explotacion_id')
        if sel:
            valid = one(conn, "SELECT id FROM explotacion WHERE id=? AND user_id=?", (sel, uid))
            if valid:
                return valid['id']
        return resolve_default_explotacion(conn, uid)
    finally:
        if own_conn:
            conn.close()


def estado_sigpac(parcela):
    """Deriva el estado del badge SIGPAC de una parcela (dict). Función pura, sin I/O.

    Devuelve (estado, diferencia_pct):
      - 'sin_verificar'  -> nunca se verificó (diferencia None)
      - 'no_encontrada'  -> verificada pero SIGPAC no dio superficie (diferencia None)
      - 'verde'          -> |declarada - sigpac| / sigpac <= 5%
      - 'ambar'          -> diferencia > 5% (o sin superficie declarada)
    diferencia_pct = (declarada - sigpac) / sigpac * 100, redondeada a 1 decimal.
    """
    if not parcela.get('sigpac_verificado_en'):
        return 'sin_verificar', None
    sig = parcela.get('sigpac_superficie_ha')
    if sig is None:
        return 'no_encontrada', None
    try:
        sig = float(sig)
    except (TypeError, ValueError):
        return 'no_encontrada', None
    if sig <= 0:
        return 'no_encontrada', None
    decl = parcela.get('superficie_ha')
    if decl in (None, ''):
        return 'ambar', None
    try:
        decl = float(decl)
    except (TypeError, ValueError):
        return 'ambar', None
    ratio = abs(decl - sig) / sig
    diff_pct = round((decl - sig) / sig * 100, 1)
    return ('verde' if ratio <= 0.05 else 'ambar'), diff_pct
