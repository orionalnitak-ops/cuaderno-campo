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
            WHERE u.user_id = ? AND u.campana = ? AND u.deleted_at IS NULL
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


@bp.route('/api/uhc/<int:uhc_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_one_uhc(uhc_id):
    uid = get_uid()
    conn = get_db()

    uhc = one(conn, "SELECT * FROM unidades_homogeneas WHERE id=? AND user_id=? AND deleted_at IS NULL", (uhc_id, uid))
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
        """, (uhc.get('campana', '2025/2026'), uhc_id))
        conn.close()
        return jsonify({"uhc": uhc, "parcelas": parcelas})

    if request.method == 'DELETE':
        conn.execute(
            "UPDATE unidades_homogeneas SET deleted_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",
            (uhc_id, uid))
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
        "UPDATE unidades_homogeneas SET nombre=?, cultivo=?, notas=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",
        (nombre, data.get('cultivo', '').strip(), data.get('notas', '').strip(), uhc_id, uid)
    )

    # Reasignar parcelas: borrar y reinsertar
    c.execute("DELETE FROM uhc_parcelas WHERE uhc_id=?", (uhc_id,))
    for pid in data.get('parcela_ids', []):
        c.execute(
            "INSERT OR IGNORE INTO uhc_parcelas (uhc_id, parcela_id) VALUES (?,?)",
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
    uhc = one(conn, "SELECT * FROM unidades_homogeneas WHERE id=? AND user_id=? AND deleted_at IS NULL", (uhc_id, uid))
    if not uhc:
        conn.close()
        return jsonify({"error": "Grupo no encontrado"}), 404

    parcelas = dicts(conn, """
        SELECT p.id, p.nombre_finca, p.superficie_ha
        FROM uhc_parcelas up
        JOIN parcelas p ON p.id = up.parcela_id
        WHERE up.uhc_id = ?
    """, (uhc_id,))
    conn.close()
    return jsonify(parcelas)
