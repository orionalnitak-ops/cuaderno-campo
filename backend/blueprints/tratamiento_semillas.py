"""
blueprints/tratamiento_semillas.py — /api/tratamiento-semillas/*

Módulo nuevo (feature 024, bloque 7/8 SIEX): tratamiento de semilla antes de
la siembra (desinfección, fungicida de semilla...). Distinto de `tratamientos`
(bloque 022, aplicaciones fitosanitarias en campo) aunque comparte el mismo
sub-bloque ASPAFITOS en SIEX. Mismo patrón de aislamiento por explotación y
validación de pertenencia que fertilizacion.py y analisis.py.
"""
import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid, get_active_explotacion_id

bp = Blueprint('tratamiento_semillas', __name__)

SIN_EXPLOTACION = "No tienes ninguna explotación creada"

# `Tratamiento semilla.xlsx` empieza en el código 2 — no hay código 1
# (verificado, no es un error de importación).
_TRATAMIENTO_COD_VALIDOS = {2, 3, 4, 5}


def _validate_tratamiento_semilla(data):
    if not data.get('tratamiento_cod'):
        return "El tipo de tratamiento es obligatorio"
    try:
        if int(data['tratamiento_cod']) not in _TRATAMIENTO_COD_VALIDOS:
            return "Tipo de tratamiento no válido"
    except (TypeError, ValueError):
        return "Tipo de tratamiento no válido"
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
    # informa un producto — mismo criterio que el resto de bloques: nunca
    # bloquear el guardado por un dato de catálogo que el agricultor no tenga
    # a mano en el momento de anotar.
    if data.get('producto_comercial') and not data.get('num_registro_mapa'):
        return "El nº de registro MAPA es obligatorio si indicas un producto"
    return None


def parcela_es_del_usuario(conn, parcela_id, uid, explotacion_id=None):
    """True si parcela_id existe y pertenece a uid. Evita IDOR — mismo patrón
    que en fertilizacion.py y analisis.py."""
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


def _insert_tratamiento_semilla(c, uid, data, parcela_id, parcela_etiqueta, explotacion_id):
    c.execute('''
        INSERT INTO tratamiento_semillas (
            user_id, explotacion_id, parcela_id, parcela_etiqueta,
            superficie_tratada_ha, tratamiento_cod, fecha_actuacion,
            cantidad, unidad_cod, eficacia_cod, observaciones,
            producto_comercial, num_registro_mapa, sustancia_activa, campana
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        uid, explotacion_id, parcela_id, parcela_etiqueta,
        data.get('superficie_tratada_ha'), data.get('tratamiento_cod'), data.get('fecha_actuacion'),
        data.get('cantidad'), data.get('unidad_cod'), data.get('eficacia_cod'), data.get('observaciones'),
        data.get('producto_comercial'), data.get('num_registro_mapa'), data.get('sustancia_activa'),
        data.get('campana', '2025/2026'),
    ))
    return c.lastrowid


_TRATAMIENTO_SEMILLA_UPDATE_FIELDS = (
    'parcela_id', 'parcela_etiqueta', 'superficie_tratada_ha', 'tratamiento_cod',
    'fecha_actuacion', 'cantidad', 'unidad_cod', 'eficacia_cod', 'observaciones',
    'producto_comercial', 'num_registro_mapa', 'sustancia_activa', 'campana',
)


@bp.route('/api/tratamiento-semillas', methods=['GET', 'POST'])
@login_required
def manage_tratamiento_semillas():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM tratamiento_semillas WHERE user_id=? AND explotacion_id=?"
                           " AND deleted_at IS NULL ORDER BY fecha_actuacion DESC", (uid, exp_id))
        conn.close(); return jsonify(rows)

    data = request.json or {}
    err = _validate_tratamiento_semilla(data)
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
        ids = [_insert_tratamiento_semilla(c, uid, data, p['id'], p['nombre_finca'], exp_id) for p in parcelas]
        conn.commit(); conn.close()
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201

    if not parcela_es_del_usuario(conn, data.get('parcela_id'), uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403

    new_id = _insert_tratamiento_semilla(c, uid, data, data.get('parcela_id'),
                                         data.get('parcela_etiqueta'), exp_id)
    conn.commit(); conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/tratamiento-semillas/<int:tid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_tratamiento_semilla_one(tid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'DELETE':
        conn.execute(
            "UPDATE tratamiento_semillas SET deleted_at=CURRENT_TIMESTAMP"
            " WHERE id=? AND user_id=? AND explotacion_id=?",
            (tid, uid, exp_id))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM tratamiento_semillas WHERE id=? AND user_id=? AND explotacion_id=?"
                        " AND deleted_at IS NULL", (tid, uid, exp_id))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_tratamiento_semilla(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    if not data.get('parcela_id'):
        conn.close()
        return jsonify({"error": "La parcela es obligatoria al editar un tratamiento de semilla"}), 400
    if not parcela_es_del_usuario(conn, data['parcela_id'], uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403
    fields = list(_TRATAMIENTO_SEMILLA_UPDATE_FIELDS)
    sets = ', '.join(f"{f}=?" for f in fields)
    conn.execute(f"UPDATE tratamiento_semillas SET {sets}"
                 f" WHERE id=? AND user_id=? AND explotacion_id=? AND deleted_at IS NULL",
                 [data.get(f) for f in fields] + [tid, uid, exp_id])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
