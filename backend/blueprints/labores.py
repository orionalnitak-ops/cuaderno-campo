"""
blueprints/labores.py — /api/labores/*, /api/cosecha/*
"""
import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid, _to_real
from blueprints.ia import _recalcular_patrones
from blueprints.fertilizacion import _parcelas_uhc, parcela_es_del_usuario

bp = Blueprint('labores', __name__)


def _validate_labor(data):
    """Requiere fecha y parcela o grupo UHC (antes no se validaba nada en el backend)."""
    if not data.get('fecha'):
        return "La fecha es obligatoria"
    if not data.get('parcela_id') and not data.get('uhc_id'):
        return "Se requiere una parcela o un grupo UHC"
    return None


def _insert_labor(c, uid, data, parcela_id, parcela_etiqueta):
    """Inserta un único registro de labor para la parcela dada."""
    c.execute('''
        INSERT INTO labores (user_id, parcela_id, parcela_etiqueta, fecha,
            tipo_labor, descripcion, producto, maquinaria, horas_trabajadas, operario, notas, campana)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (uid, parcela_id, parcela_etiqueta, data.get('fecha'),
          data.get('tipo_labor'), data.get('descripcion'), data.get('producto'), data.get('maquinaria'),
          _to_real(data.get('horas_trabajadas')), data.get('operario'), data.get('notas'),
          data.get('campana', '2025/2026')))
    return c.lastrowid


@bp.route('/api/labores', methods=['GET', 'POST'])
@login_required
def manage_labores():
    uid = get_uid()
    conn = get_db()
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM labores WHERE user_id=? ORDER BY fecha DESC", (uid,))
        conn.close(); return jsonify(rows)
    data = request.json or {}
    err = _validate_labor(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    c = conn.cursor()

    if data.get('uhc_id'):
        parcelas = _parcelas_uhc(conn, data['uhc_id'], uid)
        if not parcelas:
            conn.close()
            return jsonify({"error": "El grupo UHC no existe o no tiene parcelas asignadas"}), 400
        ids = [_insert_labor(c, uid, data, p['id'], p['nombre_finca']) for p in parcelas]
        conn.commit(); conn.close()
        for p in parcelas:
            _recalcular_patrones(uid, 'labores', p['id'], data.get('fecha'))
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201

    if not parcela_es_del_usuario(conn, data.get('parcela_id'), uid):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403

    new_id = _insert_labor(c, uid, data, data.get('parcela_id'), data.get('parcela_etiqueta'))
    conn.commit(); conn.close()
    _recalcular_patrones(uid, 'labores', data.get('parcela_id'), data.get('fecha'))
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/labores/<int:lid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_labor(lid):
    uid = get_uid()
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM labores WHERE id=? AND user_id=?", (lid, uid))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM labores WHERE id=? AND user_id=?", (lid, uid))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_labor(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    if data.get('parcela_id') and not parcela_es_del_usuario(conn, data['parcela_id'], uid):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403
    fields = ['parcela_id', 'parcela_etiqueta', 'fecha', 'tipo_labor', 'descripcion',
              'producto', 'maquinaria', 'horas_trabajadas', 'operario', 'notas', 'campana']
    sets = ', '.join(f"{f}=?" for f in fields)
    conn.execute(f"UPDATE labores SET {sets} WHERE id=? AND user_id=?",
                 [_to_real(data.get(f)) if f == 'horas_trabajadas' else data.get(f) for f in fields] + [lid, uid])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})


@bp.route('/api/cosecha', methods=['GET', 'POST'])
@login_required
def manage_cosecha():
    uid = get_uid()
    conn = get_db()
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM cosecha WHERE user_id=? ORDER BY fecha_inicio DESC", (uid,))
        conn.close(); return jsonify(rows)
    data = request.json or {}

    # Validar fechas de cosecha
    fi = data.get('fecha_inicio')
    ff = data.get('fecha_fin')
    if not fi:
        conn.close()
        return jsonify({"error": "La fecha de inicio es obligatoria"}), 400
    try:
        d_ini = datetime.date.fromisoformat(str(fi))
        if d_ini > datetime.date.today():
            conn.close()
            return jsonify({"error": "La fecha de inicio de cosecha no puede ser futura"}), 400
        if ff:
            d_fin = datetime.date.fromisoformat(str(ff))
            if d_fin > datetime.date.today():
                conn.close()
                return jsonify({"error": "La fecha de fin de cosecha no puede ser futura"}), 400
            if d_fin < d_ini:
                conn.close()
                return jsonify({"error": "La fecha de fin no puede ser anterior a la de inicio"}), 400
    except (ValueError, TypeError):
        conn.close()
        return jsonify({"error": "Formato de fecha inválido (use YYYY-MM-DD)"}), 400

    if data.get('parcela_id') and not parcela_es_del_usuario(conn, data['parcela_id'], uid):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403

    # Bloquear cosecha si hay tratamientos con plazo de seguridad no vencido en la misma parcela
    if data.get('parcela_id') and data.get('fecha_inicio'):
        plazo_activos = dicts(conn, """
            SELECT producto_comercial, fecha_recoleccion_minima
            FROM tratamientos
            WHERE parcela_id=? AND user_id=? AND deleted_at IS NULL
              AND fecha_recoleccion_minima > ?
        """, (data['parcela_id'], uid, data['fecha_inicio']))
        if plazo_activos:
            nombres = ', '.join(p['producto_comercial'] for p in plazo_activos)
            conn.close()
            return jsonify({"error": (
                f"No se puede registrar la cosecha: plazo de seguridad no vencido para: {nombres}. "
                "Espera hasta que pasen los plazos indicados en los tratamientos."
            )}), 400

    prod = _to_real(data.get('produccion_total_valor')) or 0
    sup  = _to_real(data.get('superficie_cosechada_ha')) or 0
    rend = round(prod / sup, 2) if sup > 0 else None
    c = conn.cursor()
    c.execute('''
        INSERT INTO cosecha (user_id, parcela_id, parcela_etiqueta, fecha_inicio, fecha_fin,
            cultivo, variedad, superficie_cosechada_ha, produccion_total_valor,
            produccion_total_unidad, rendimiento_kg_ha, destino, comprador,
            precio_unidad, notas, campana)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (uid, data.get('parcela_id'), data.get('parcela_etiqueta'),
          data.get('fecha_inicio'), data.get('fecha_fin'), data.get('cultivo'),
          data.get('variedad'), sup, prod, data.get('produccion_total_unidad', 'kg'),
          rend, data.get('destino'), data.get('comprador'),
          _to_real(data.get('precio_unidad')), data.get('notas'), data.get('campana', '2025/2026')))
    conn.commit(); new_id = c.lastrowid; conn.close()
    _recalcular_patrones(uid, 'cosecha', data.get('parcela_id'), data.get('fecha_inicio'))
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/cosecha/<int:cid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_cosecha_one(cid):
    uid = get_uid()
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM cosecha WHERE id=? AND user_id=?", (cid, uid))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM cosecha WHERE id=? AND user_id=?", (cid, uid))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    if data.get('parcela_id') and not parcela_es_del_usuario(conn, data['parcela_id'], uid):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403
    prod = _to_real(data.get('produccion_total_valor')) or 0
    sup  = _to_real(data.get('superficie_cosechada_ha')) or 0
    data['rendimiento_kg_ha'] = round(prod / sup, 2) if sup > 0 else None
    data['produccion_total_valor'] = prod or None
    data['superficie_cosechada_ha'] = sup or None
    fields = ['parcela_id', 'parcela_etiqueta', 'fecha_inicio', 'fecha_fin', 'cultivo',
              'variedad', 'superficie_cosechada_ha', 'produccion_total_valor', 'produccion_total_unidad',
              'rendimiento_kg_ha', 'destino', 'comprador', 'precio_unidad', 'notas', 'campana']
    _real_c = {'precio_unidad'}
    sets = ', '.join(f"{f}=?" for f in fields)
    conn.execute(f"UPDATE cosecha SET {sets} WHERE id=? AND user_id=?",
                 [_to_real(data.get(f)) if f in _real_c else data.get(f) for f in fields] + [cid, uid])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
