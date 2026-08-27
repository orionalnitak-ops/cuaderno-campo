"""
blueprints/post_cosecha.py — /api/post-cosecha/*

Módulo nuevo (feature 025, bloque 8/8 SIEX, último del roadmap): tratamiento
fitosanitario aplicado después de la cosecha (fumigación de grano
almacenado, tratamiento de fruta en cámara...). Casi idéntico en forma a
`tratamientos.py` (bloque 022) pero referido a un producto ya cosechado
(`codigo_producto_siex`), no a un cultivo en pie. Mismo patrón de
aislamiento por explotación y validación de pertenencia que
fertilizacion.py/analisis.py/tratamiento_semillas.py.
"""
import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid, get_active_explotacion_id

bp = Blueprint('post_cosecha', __name__)

SIN_EXPLOTACION = "No tienes ninguna explotación creada"


def _validate_post_cosecha(data):
    if not data.get('fecha_actuacion'):
        return "La fecha de la actuación es obligatoria"
    try:
        fecha = datetime.date.fromisoformat(str(data['fecha_actuacion']))
        if fecha > datetime.date.today():
            return "La fecha de la actuación no puede ser futura"
    except (ValueError, TypeError):
        return "Fecha con formato inválido (use YYYY-MM-DD)"
    if not data.get('parcela_id') and not data.get('uhc_id'):
        return "Selecciona una parcela o un grupo UHC"
    # numRegistro es obligatorio en SIEX, pero solo tiene sentido si se
    # informa un producto — mismo criterio que en tratamiento_semillas.py.
    if data.get('producto_comercial') and not data.get('num_registro_mapa'):
        return "El nº de registro MAPA es obligatorio si indicas un producto"
    return None


def parcela_es_del_usuario(conn, parcela_id, uid, explotacion_id=None):
    """True si parcela_id existe y pertenece a uid. Evita IDOR — mismo patrón
    que en fertilizacion.py, analisis.py y tratamiento_semillas.py."""
    sql = "SELECT id FROM parcelas WHERE id=? AND user_id=?"
    params = [parcela_id, uid]
    if explotacion_id is not None:
        sql += " AND explotacion_id=?"
        params.append(explotacion_id)
    return one(conn, sql, params) is not None


def _parcelas_uhc(conn, uhc_id, uid, explotacion_id=None):
    """Parcelas de un grupo UHC — ver nota completa en fertilizacion.py."""
    try:
        uhc_id = int(uhc_id)
    except (TypeError, ValueError):
        return []
    sql = """
        SELECT p.id, p.nombre_finca
        FROM uhc_parcelas up
        JOIN parcelas p ON p.id = up.parcela_id
        JOIN unidades_homogeneas u ON u.id = up.uhc_id
        WHERE up.uhc_id = ? AND u.user_id = ? AND u.deleted_at IS NULL
    """
    params = [uhc_id, uid]
    if explotacion_id is not None:
        sql += " AND u.explotacion_id = ? AND p.explotacion_id = ?"
        params += [explotacion_id, explotacion_id]
    return dicts(conn, sql, params)


def _insert_post_cosecha(c, uid, data, parcela_id, parcela_etiqueta, explotacion_id):
    c.execute('''
        INSERT INTO post_cosecha (
            user_id, explotacion_id, parcela_id, parcela_etiqueta,
            fecha_actuacion, codigo_producto_siex, justificacion_actuacion_cod,
            cantidad, unidad_cod, eficacia_cod, observaciones,
            producto_comercial, num_registro_mapa, sustancia_activa, campana
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        uid, explotacion_id, parcela_id, parcela_etiqueta,
        data.get('fecha_actuacion'), data.get('codigo_producto_siex'), data.get('justificacion_actuacion_cod'),
        data.get('cantidad'), data.get('unidad_cod'), data.get('eficacia_cod'), data.get('observaciones'),
        data.get('producto_comercial'), data.get('num_registro_mapa'), data.get('sustancia_activa'),
        data.get('campana', '2025/2026'),
    ))
    return c.lastrowid


_POST_COSECHA_UPDATE_FIELDS = (
    'parcela_id', 'parcela_etiqueta', 'fecha_actuacion', 'codigo_producto_siex',
    'justificacion_actuacion_cod', 'cantidad', 'unidad_cod', 'eficacia_cod',
    'observaciones', 'producto_comercial', 'num_registro_mapa', 'sustancia_activa', 'campana',
)


@bp.route('/api/post-cosecha', methods=['GET', 'POST'])
@login_required
def manage_post_cosecha():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM post_cosecha WHERE user_id=? AND explotacion_id=?"
                           " AND deleted_at IS NULL ORDER BY fecha_actuacion DESC", (uid, exp_id))
        conn.close(); return jsonify(rows)

    data = request.json or {}
    err = _validate_post_cosecha(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    if not exp_id:
        conn.close()
        return jsonify({"error": SIN_EXPLOTACION}), 400

    c = conn.cursor()

    if data.get('uhc_id'):
        parcelas = _parcelas_uhc(conn, data['uhc_id'], uid, exp_id)
        if not parcelas:
            conn.close()
            return jsonify({"error": "El grupo UHC no existe o no tiene parcelas asignadas"}), 400
        ids = [_insert_post_cosecha(c, uid, data, p['id'], p['nombre_finca'], exp_id) for p in parcelas]
        conn.commit(); conn.close()
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201

    if not parcela_es_del_usuario(conn, data.get('parcela_id'), uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403

    new_id = _insert_post_cosecha(c, uid, data, data.get('parcela_id'),
                                  data.get('parcela_etiqueta'), exp_id)
    conn.commit(); conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/post-cosecha/<int:pid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_post_cosecha_one(pid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'DELETE':
        conn.execute(
            "UPDATE post_cosecha SET deleted_at=CURRENT_TIMESTAMP"
            " WHERE id=? AND user_id=? AND explotacion_id=?",
            (pid, uid, exp_id))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM post_cosecha WHERE id=? AND user_id=? AND explotacion_id=?"
                        " AND deleted_at IS NULL", (pid, uid, exp_id))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_post_cosecha(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    if not data.get('parcela_id'):
        conn.close()
        return jsonify({"error": "La parcela es obligatoria al editar un tratamiento post-cosecha"}), 400
    if not parcela_es_del_usuario(conn, data['parcela_id'], uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403
    fields = list(_POST_COSECHA_UPDATE_FIELDS)
    sets = ', '.join(f"{f}=?" for f in fields)
    conn.execute(f"UPDATE post_cosecha SET {sets}"
                 f" WHERE id=? AND user_id=? AND explotacion_id=? AND deleted_at IS NULL",
                 [data.get(f) for f in fields] + [pid, uid, exp_id])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
