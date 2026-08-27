"""
blueprints/analisis.py — /api/analisis/*

Módulo nuevo (feature 023, bloque 6/8 SIEX): análisis de suelo, agua de riego,
cultivo o producto cosechado. Mismo patrón de aislamiento por explotación y
validación de pertenencia que fertilizacion.py y riego.py — ver esos archivos
para el razonamiento completo de por qué se valida en las dos direcciones.
"""
import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid, get_active_explotacion_id

bp = Blueprint('analisis', __name__)

SIN_EXPLOTACION = "No tienes ninguna explotación creada"

# Solo material_cod 1 (Cultivo) y 2 (Producto cosechado) admiten un producto
# del catálogo SIEX — 3 (Suelo) y 4 (Agua de riego) no analizan un cultivo.
_MATERIAL_CON_PRODUCTO = {1, 2}


def _validate_analisis(data):
    """Solo material y fecha son obligatorios (spec: criterio de aceptación 5)."""
    if not data.get('material_cod'):
        return "El tipo de material analizado es obligatorio"
    if not data.get('fecha'):
        return "La fecha del análisis es obligatoria"
    try:
        fecha = datetime.date.fromisoformat(str(data['fecha']))
        if fecha > datetime.date.today():
            return "La fecha del análisis no puede ser futura"
    except (ValueError, TypeError):
        return "Fecha con formato inválido (use YYYY-MM-DD)"
    if not data.get('parcela_id') and not data.get('uhc_id'):
        return "Selecciona una parcela o un grupo UHC"
    return None


def parcela_es_del_usuario(conn, parcela_id, uid, explotacion_id=None):
    """True si parcela_id existe y pertenece a uid. Evita IDOR — mismo patrón
    que en fertilizacion.py y tratamientos.py (no se importa de allí para no
    crear un import cruzado entre módulos)."""
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


def _insert_analisis(c, uid, data, parcela_id, parcela_etiqueta, explotacion_id):
    """Inserta un único registro de análisis para la parcela dada."""
    material_cod = data.get('material_cod')
    try:
        material_cod = int(material_cod)
    except (TypeError, ValueError):
        material_cod = None
    # codigo_producto_siex solo tiene sentido si el material es Cultivo o
    # Producto cosechado — para Suelo/Agua se descarta aunque el cliente lo
    # mande, en vez de dejarlo colgado sin sentido en el registro.
    codigo_producto = data.get('codigo_producto_siex') if material_cod in _MATERIAL_CON_PRODUCTO else None
    c.execute('''
        INSERT INTO analisis (
            user_id, explotacion_id, parcela_id, parcela_etiqueta,
            material_cod, codigo_producto_siex, fecha,
            rs_laboratorio, direccion_laboratorio,
            provincia_laboratorio_cod, municipio_laboratorio_cod,
            num_boletin, tipo_analisis_cod, notas, campana
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        uid, explotacion_id, parcela_id, parcela_etiqueta,
        material_cod, codigo_producto, data.get('fecha'),
        data.get('rs_laboratorio'), data.get('direccion_laboratorio'),
        data.get('provincia_laboratorio_cod'), data.get('municipio_laboratorio_cod'),
        data.get('num_boletin'), data.get('tipo_analisis_cod'), data.get('notas'),
        data.get('campana', '2025/2026'),
    ))
    return c.lastrowid


_ANALISIS_UPDATE_FIELDS = (
    'parcela_id', 'parcela_etiqueta', 'material_cod', 'codigo_producto_siex',
    'fecha', 'rs_laboratorio', 'direccion_laboratorio',
    'provincia_laboratorio_cod', 'municipio_laboratorio_cod',
    'num_boletin', 'tipo_analisis_cod', 'notas', 'campana',
)


@bp.route('/api/analisis', methods=['GET', 'POST'])
@login_required
def manage_analisis():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM analisis WHERE user_id=? AND explotacion_id=?"
                           " AND deleted_at IS NULL ORDER BY fecha DESC", (uid, exp_id))
        conn.close(); return jsonify(rows)

    data = request.json or {}
    err = _validate_analisis(data)
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
        ids = [_insert_analisis(c, uid, data, p['id'], p['nombre_finca'], exp_id) for p in parcelas]
        conn.commit(); conn.close()
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201

    if not parcela_es_del_usuario(conn, data.get('parcela_id'), uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403

    new_id = _insert_analisis(c, uid, data, data.get('parcela_id'),
                              data.get('parcela_etiqueta'), exp_id)
    conn.commit(); conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/analisis/<int:aid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_analisis_one(aid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'DELETE':
        conn.execute(
            "UPDATE analisis SET deleted_at=CURRENT_TIMESTAMP"
            " WHERE id=? AND user_id=? AND explotacion_id=?",
            (aid, uid, exp_id))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM analisis WHERE id=? AND user_id=? AND explotacion_id=?"
                        " AND deleted_at IS NULL", (aid, uid, exp_id))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_analisis(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    if not data.get('parcela_id'):
        conn.close()
        return jsonify({"error": "La parcela es obligatoria al editar un análisis"}), 400
    if not parcela_es_del_usuario(conn, data['parcela_id'], uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403
    material_cod = data.get('material_cod')
    try:
        material_cod = int(material_cod)
    except (TypeError, ValueError):
        material_cod = None
    if material_cod not in _MATERIAL_CON_PRODUCTO:
        data['codigo_producto_siex'] = None
    fields = list(_ANALISIS_UPDATE_FIELDS)
    sets = ', '.join(f"{f}=?" for f in fields)
    conn.execute(f"UPDATE analisis SET {sets}"
                 f" WHERE id=? AND user_id=? AND explotacion_id=? AND deleted_at IS NULL",
                 [data.get(f) for f in fields] + [aid, uid, exp_id])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
