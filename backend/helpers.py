"""
helpers.py — Decoradores y funciones de utilidad compartidas entre blueprints.
"""
from functools import wraps
from flask import jsonify, session
from flask_login import current_user


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
