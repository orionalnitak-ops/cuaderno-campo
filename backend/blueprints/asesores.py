"""
blueprints/asesores.py — /api/asesores/*

Asesor fitosanitario (Orden APA/204/2023). Entidad reutilizable por usuario,
mismo patrón que `aplicadores`. A diferencia del aplicador, la ausencia de nº
ROPO NO bloquea el guardado del tratamiento: el agricultor rara vez tiene a mano
el carnet de su técnico externo. Ver spec/features/010-asesores/spec.md.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid

bp = Blueprint('asesores', __name__)

_FIELDS = ['nombre', 'nif', 'num_ropo', 'titulacion', 'empresa', 'telefono', 'email']

_MAX_LEN = 120


def _clean(data):
    """Recorta y normaliza los campos del formulario. Devuelve (valores, error)."""
    vals = {}
    for f in _FIELDS:
        v = data.get(f)
        vals[f] = str(v).strip()[:_MAX_LEN] if v is not None and str(v).strip() else None
    if not vals['nombre']:
        return None, "El nombre del asesor es obligatorio"
    return vals, None


def asesor_es_del_usuario(conn, asesor_id, uid):
    """True si asesor_id existe y pertenece a uid. Evita IDOR: sin esto, cualquier
    usuario autenticado podría colgar sus tratamientos del asesor de otro."""
    return one(conn, "SELECT id FROM asesores WHERE id=? AND user_id=?",
               (asesor_id, uid)) is not None


@bp.route('/api/asesores', methods=['GET', 'POST'])
@login_required
def manage_asesores():
    uid = get_uid()
    conn = get_db()
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM asesores WHERE user_id=? AND activo=1 ORDER BY nombre",
                     (uid,))
        conn.close()
        return jsonify(rows)

    vals, err = _clean(request.json or {})
    if err:
        conn.close()
        return jsonify({"ok": False, "error": err}), 400

    c = conn.cursor()
    cols = ', '.join(_FIELDS)
    marks = ','.join('?' * len(_FIELDS))
    # nosec B608 — cols/marks salen de _FIELDS (lista hardcodeada), nunca de input
    # externo; los valores van siempre por placeholder.
    c.execute(f"INSERT INTO asesores (user_id, {cols}) VALUES (?,{marks})",
              [uid] + [vals[f] for f in _FIELDS])
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/asesores/<int:aid>', methods=['PUT', 'DELETE'])
@login_required
def manage_asesor(aid):
    uid = get_uid()
    conn = get_db()

    if request.method == 'DELETE':
        # Baja lógica: los tratamientos ya registrados siguen apuntando a esta ficha
        # y deben poder resolver el nombre en el PDF oficial.
        conn.execute("UPDATE asesores SET activo=0 WHERE id=? AND user_id=?", (aid, uid))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})

    vals, err = _clean(request.json or {})
    if err:
        conn.close()
        return jsonify({"ok": False, "error": err}), 400

    sets = ', '.join(f"{f}=?" for f in _FIELDS)
    # nosec B608 — sets sale de _FIELDS (lista hardcodeada), no de input externo
    conn.execute(f"UPDATE asesores SET {sets} WHERE id=? AND user_id=?",
                 [vals[f] for f in _FIELDS] + [aid, uid])
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})
