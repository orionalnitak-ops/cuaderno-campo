"""
blueprints/uhc.py — CRUD de Unidades Homogéneas de Cultivo

Aislamiento por explotación (feature 013): un grupo pertenece a UNA explotación y
solo puede agrupar parcelas de esa misma finca. Un UHC que mezclara parcelas de
dos explotaciones rompería el aislamiento por la puerta de atrás, porque los
tratamientos se expanden por grupo.
"""
import re
from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid, get_active_explotacion_id

bp = Blueprint('uhc', __name__)


def _valid_parcela_ids(conn, uid, parcela_ids, explotacion_id=None):
    """Devuelve solo los ids de parcela que son de este usuario (y, si se indica,
    de esta explotación). Filtrar aquí es lo que evita que un grupo agrupe
    parcelas de otra finca aunque el cliente mande sus ids."""
    if not parcela_ids:
        return []
    placeholders = ','.join('?' * len(parcela_ids))
    sql = (f"SELECT id FROM parcelas WHERE id IN ({placeholders})"
           f" AND user_id=? AND activa=1")
    params = list(parcela_ids) + [uid]
    if explotacion_id is not None:
        sql += " AND explotacion_id=?"
        params.append(explotacion_id)
    rows = dicts(conn, sql, params)
    return [r['id'] for r in rows]


@bp.route('/api/uhc', methods=['GET', 'POST'])
@login_required
def manage_uhc():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)

    if request.method == 'GET':
        campana = request.args.get('campana', '2025/2026')
        rows = dicts(conn, """
            SELECT u.*,
                   COUNT(up.id) AS num_parcelas
            FROM unidades_homogeneas u
            LEFT JOIN uhc_parcelas up ON up.uhc_id = u.id
            WHERE u.user_id = ? AND u.explotacion_id = ? AND u.campana = ?
              AND u.deleted_at IS NULL
            GROUP BY u.id
            ORDER BY u.nombre
        """, (uid, exp_id, campana))
        conn.close()
        return jsonify(rows)

    data = request.json or {}
    nombre = (data.get('nombre') or '').strip()
    if not nombre:
        conn.close()
        return jsonify({"error": "El nombre del grupo es obligatorio"}), 400

    campana = data.get('campana', '2025/2026')
    if not re.fullmatch(r'\d{4}/\d{4}', str(campana)):
        conn.close()
        return jsonify({"error": "La campaña debe tener formato YYYY/YYYY (ej: 2025/2026)"}), 400
    if not exp_id:
        conn.close()
        return jsonify({"error": "No tienes ninguna explotación creada"}), 400

    c = conn.cursor()
    c.execute(
        "INSERT INTO unidades_homogeneas (user_id, explotacion_id, nombre, cultivo, campana, notas)"
        " VALUES (?,?,?,?,?,?)",
        (uid, exp_id, nombre, data.get('cultivo', '').strip(), campana,
         data.get('notas', '').strip())
    )
    uhc_id = c.lastrowid

    # INSERT normal: _valid_parcela_ids no devuelve duplicados y "OR IGNORE"
    # es sintaxis solo-SQLite (rompe en PostgreSQL, el wrapper no la traduce).
    for pid in _valid_parcela_ids(conn, uid, data.get('parcela_ids', []), exp_id):
        c.execute(
            "INSERT INTO uhc_parcelas (uhc_id, parcela_id) VALUES (?,?)",
            (uhc_id, pid)
        )

    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "id": uhc_id}), 201


@bp.route('/api/uhc/<int:uhc_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_one_uhc(uhc_id):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)

    uhc = one(conn, "SELECT * FROM unidades_homogeneas WHERE id=? AND user_id=?"
                    " AND explotacion_id=? AND deleted_at IS NULL", (uhc_id, uid, exp_id))
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
            WHERE up.uhc_id = ? AND p.user_id = ? AND p.explotacion_id = ?
        """, (uhc.get('campana', '2025/2026'), uhc_id, uid, exp_id))
        conn.close()
        return jsonify({"uhc": uhc, "parcelas": parcelas})

    if request.method == 'DELETE':
        conn.execute(
            "UPDATE unidades_homogeneas SET deleted_at=CURRENT_TIMESTAMP"
            " WHERE id=? AND user_id=? AND explotacion_id=?",
            (uhc_id, uid, exp_id))
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
        "UPDATE unidades_homogeneas SET nombre=?, cultivo=?, notas=?, updated_at=CURRENT_TIMESTAMP"
        " WHERE id=? AND user_id=? AND explotacion_id=?",
        (nombre, data.get('cultivo', '').strip(), data.get('notas', '').strip(),
         uhc_id, uid, exp_id)
    )

    # Reasignar parcelas: borrar y reinsertar (INSERT normal: tras el DELETE no
    # puede haber duplicados y "OR IGNORE" es solo-SQLite, rompe en PostgreSQL)
    c.execute("DELETE FROM uhc_parcelas WHERE uhc_id=?", (uhc_id,))
    for pid in _valid_parcela_ids(conn, uid, data.get('parcela_ids', []), exp_id):
        c.execute(
            "INSERT INTO uhc_parcelas (uhc_id, parcela_id) VALUES (?,?)",
            (uhc_id, pid)
        )

    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@bp.route('/api/uhc/<int:uhc_id>/parcelas', methods=['GET'])
@login_required
def get_uhc_parcelas(uhc_id):
    """Devuelve la lista de parcelas de un UHC (para expandir en tratamientos)."""
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    uhc = one(conn, "SELECT * FROM unidades_homogeneas WHERE id=? AND user_id=?"
                    " AND explotacion_id=? AND deleted_at IS NULL", (uhc_id, uid, exp_id))
    if not uhc:
        conn.close()
        return jsonify({"error": "Grupo no encontrado"}), 404

    # p.explotacion_id además de p.user_id: un grupo creado antes de la feature 013
    # puede tener dentro parcelas de dos fincas, y este endpoint alimenta la
    # expansión por grupo en tratamientos. Sin el filtro, el aislamiento se rompe
    # justo donde más duele.
    parcelas = dicts(conn, """
        SELECT p.id, p.nombre_finca, p.superficie_ha
        FROM uhc_parcelas up
        JOIN parcelas p ON p.id = up.parcela_id
        WHERE up.uhc_id = ? AND p.user_id = ? AND p.explotacion_id = ?
    """, (uhc_id, uid, exp_id))
    conn.close()
    return jsonify(parcelas)
