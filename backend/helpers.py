"""
helpers.py — Decoradores y funciones de utilidad compartidas entre blueprints.
"""
import re
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


_CAMPANA_RE = re.compile(r'^\d{4}/\d{4}$')


def validar_alta_multirecinto(data):
    """Valida y normaliza el payload de POST /api/parcelas/alta-multirecinto.

    Devuelve (norm, None) si es válido o (None, "mensaje legible") si no.
    norm: {nombre_base, campana, recintos:[{num:int, uso_sigpac:str, superficie_ha:float|None}],
           uhcs:[{nombre:str, cultivo:str, recintos:[int]}]}
    """
    data = data or {}
    nombre_base = (data.get('nombre_base') or '').strip()
    if not nombre_base:
        return None, "El nombre de la finca es obligatorio"

    campana = str(data.get('campana') or '2025/2026')
    if not _CAMPANA_RE.match(campana):
        return None, "La campaña debe tener formato YYYY/YYYY (ej: 2025/2026)"

    raw = data.get('recintos')
    if not isinstance(raw, list) or not raw:
        return None, "Hacen falta los trozos (recintos) que se van a crear"

    recintos, vistos = [], set()
    for r in raw:
        r = r or {}
        try:
            num = int(r.get('num'))
        except (TypeError, ValueError):
            return None, "Número de trozo (recinto) inválido"
        if num <= 0:
            return None, "Número de trozo (recinto) inválido"
        if num in vistos:
            return None, "Hay trozos (recintos) repetidos"
        vistos.add(num)
        sup = r.get('superficie_ha')
        if sup is None or sup == '':
            sup = None
        else:
            try:
                sup = float(str(sup).replace(',', '.'))
            except (TypeError, ValueError):
                return None, f"Superficie inválida en el trozo {num}"
            if sup <= 0:
                return None, f"La superficie del trozo {num} debe ser mayor que cero"
        recintos.append({'num': num, 'uso_sigpac': (r.get('uso_sigpac') or '').strip(),
                         'superficie_ha': sup})

    uhcs = []
    for u in (data.get('uhcs') or []):
        u = u or {}
        nombre = (u.get('nombre') or '').strip()
        if not nombre:
            return None, "El nombre del grupo es obligatorio"
        try:
            nums = sorted({int(n) for n in (u.get('recintos') or [])})
        except (TypeError, ValueError):
            return None, f"El grupo '{nombre}' tiene trozos inválidos"
        if len(nums) < 2:
            return None, f"El grupo '{nombre}' necesita al menos 2 trozos"
        if not set(nums) <= vistos:
            return None, f"El grupo '{nombre}' incluye trozos que no se van a crear"
        uhcs.append({'nombre': nombre, 'cultivo': (u.get('cultivo') or '').strip(),
                     'recintos': nums})

    return {'nombre_base': nombre_base, 'campana': campana,
            'recintos': recintos, 'uhcs': uhcs}, None
