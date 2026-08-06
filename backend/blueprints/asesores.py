"""
blueprints/asesores.py — /api/asesores/*

Asesor fitosanitario (Orden APA/204/2023). Entidad reutilizable dentro de una
explotación, mismo patrón que `aplicadores`. A diferencia del aplicador, la
ausencia de nº ROPO NO bloquea el guardado del tratamiento: el agricultor rara
vez tiene a mano el carnet de su técnico externo. Ver
spec/features/010-asesores/spec.md.

Desde la feature 013 la ficha pertenece a UNA explotación, no al usuario: cada
explotación es un cuaderno independiente. Toda consulta filtra por `user_id` Y
`explotacion_id`.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid, get_active_explotacion_id

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


def asesor_es_del_usuario(conn, asesor_id, uid, explotacion_id=None):
    """True si asesor_id existe y pertenece a uid. Evita IDOR: sin esto, cualquier
    usuario autenticado podría colgar sus tratamientos del asesor de otro.

    Con `explotacion_id` comprueba además que el asesor sea de ESA finca
    (feature 013). Sin esa segunda comprobación el aislamiento se puede saltar
    desde el propio formulario de tratamientos: basta mandar el id de un asesor
    de la otra explotación. El parámetro es opcional para no romper a quien solo
    quiera la comprobación de dueño.
    """
    sql = "SELECT id FROM asesores WHERE id=? AND user_id=?"
    params = [asesor_id, uid]
    if explotacion_id is not None:
        sql += " AND explotacion_id=?"
        params.append(explotacion_id)
    return one(conn, sql, params) is not None


@bp.route('/api/asesores', methods=['GET', 'POST'])
@login_required
def manage_asesores():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM asesores WHERE user_id=? AND explotacion_id=?"
                           " AND activo=1 ORDER BY nombre", (uid, exp_id))
        conn.close()
        return jsonify(rows)

    vals, err = _clean(request.json or {})
    if err:
        conn.close()
        return jsonify({"ok": False, "error": err}), 400
    if not exp_id:
        # Sin explotación la ficha nacería con explotacion_id NULL y no saldría
        # en ningún listado: mejor fallar que crear un registro ciego.
        conn.close()
        return jsonify({"ok": False, "error": "No tienes ninguna explotación creada"}), 400

    c = conn.cursor()
    cols = ', '.join(_FIELDS)
    marks = ','.join('?' * len(_FIELDS))
    # nosec B608 — cols/marks salen de _FIELDS (lista hardcodeada), nunca de input
    # externo; los valores van siempre por placeholder.
    c.execute(f"INSERT INTO asesores (user_id, explotacion_id, {cols}) VALUES (?,?,{marks})",
              [uid, exp_id] + [vals[f] for f in _FIELDS])
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/asesores/<int:aid>', methods=['PUT', 'DELETE'])
@login_required
def manage_asesor(aid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)

    if request.method == 'DELETE':
        # Baja lógica: los tratamientos ya registrados siguen apuntando a esta ficha
        # y deben poder resolver el nombre en el PDF oficial.
        conn.execute("UPDATE asesores SET activo=0 WHERE id=? AND user_id=? AND explotacion_id=?",
                     (aid, uid, exp_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})

    vals, err = _clean(request.json or {})
    if err:
        conn.close()
        return jsonify({"ok": False, "error": err}), 400

    sets = ', '.join(f"{f}=?" for f in _FIELDS)
    # nosec B608 — sets sale de _FIELDS (lista hardcodeada), no de input externo
    conn.execute(f"UPDATE asesores SET {sets} WHERE id=? AND user_id=? AND explotacion_id=?",
                 [vals[f] for f in _FIELDS] + [aid, uid, exp_id])
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})
