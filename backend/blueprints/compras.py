"""
blueprints/compras.py — validadores + /api/compras/*
"""
import datetime
import re

from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid, get_active_explotacion_id, _to_real
from blueprints.ia import _recalcular_patrones

bp = Blueprint('compras', __name__)

SIN_EXPLOTACION = "No tienes ninguna explotación creada"

# Sustancias básicas y autorizaciones excepcionales no se inscriben en el Registro
# de Fitosanitarios (Reg. UE 1107/2009): no tienen nº de registro MAPA. Mismo criterio
# que en tratamientos.py; se guarda el motivo para mantener la trazabilidad.
MOTIVOS_SIN_REGISTRO = {'sustancia_basica', 'autorizacion_excepcional'}


def _validate_campana(campana):
    """Valida que la campaña tenga formato YYYY/YYYY con años consecutivos."""
    if not campana:
        return None
    if not re.fullmatch(r'\d{4}/\d{4}', str(campana)):
        return "El campo campaña debe tener formato YYYY/YYYY (ej: 2025/2026)"
    y1, y2 = int(str(campana)[:4]), int(str(campana)[5:])
    if y2 != y1 + 1:
        return "La campaña debe ser de años consecutivos (ej: 2025/2026)"
    return None


def _validate_compra(data):
    """Valida campos obligatorios de compras (Anexo III S5 — trazabilidad)."""
    required = {
        'fecha':         'Fecha de compra',
        'tipo_producto': 'Tipo de producto',
        'producto':      'Nombre del producto',
    }
    missing = [label for field, label in required.items() if not data.get(field)]
    if missing:
        return f"Campos obligatorios: {', '.join(missing)}"
    if data.get('tipo_producto') == 'fitosanitario':
        motivo = str(data.get('motivo_sin_registro', '') or '').strip()
        if motivo and motivo not in MOTIVOS_SIN_REGISTRO:
            return "Motivo de ausencia de nº de registro no válido"
        # El nº de registro se exige salvo motivo válido (sustancia básica /
        # autorización excepcional). La sustancia activa siempre.
        fito_required = {'sustancia_activa': 'Sustancia activa'}
        if not motivo:
            fito_required['num_registro_mapa'] = 'Nº de registro MAPA'
        missing_fito = [label for field, label in fito_required.items() if not data.get(field)]
        if missing_fito:
            return f"Obligatorio para fitosanitarios (RD 1311/2012 Anexo III S5): {', '.join(missing_fito)}"
    try:
        fecha = datetime.date.fromisoformat(str(data['fecha']))
        if fecha > datetime.date.today():
            return "La fecha de compra no puede ser futura"
    except (ValueError, TypeError):
        return "Fecha con formato inválido (use YYYY-MM-DD)"
    return None


@bp.route('/api/compras', methods=['GET', 'POST'])
@login_required
def manage_compras():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        campana = request.args.get('campana', '')
        sql = "SELECT * FROM compras WHERE user_id=? AND explotacion_id=? AND deleted_at IS NULL"
        params = [uid, exp_id]
        if campana:
            sql += " AND campana=?"
            params.append(campana)
        sql += " ORDER BY fecha DESC"
        rows = dicts(conn, sql, params)
        conn.close(); return jsonify(rows)

    data = request.json or {}
    err = _validate_compra(data) or _validate_campana(data.get('campana'))
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    if not exp_id:
        conn.close()
        return jsonify({"error": SIN_EXPLOTACION}), 400

    c = conn.cursor()
    c.execute('''
        INSERT INTO compras (user_id, explotacion_id, fecha, tipo_producto, producto, num_registro_mapa,
            sustancia_activa, proveedor, cantidad_valor, cantidad_unidad, num_lote,
            num_factura, precio_total, campana, notas, motivo_sin_registro)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (uid, exp_id, data.get('fecha'), data.get('tipo_producto'), data.get('producto'),
          data.get('num_registro_mapa'), data.get('sustancia_activa'),
          data.get('proveedor'), _to_real(data.get('cantidad_valor')),
          data.get('cantidad_unidad', 'kg'), data.get('num_lote'),
          data.get('num_factura'), _to_real(data.get('precio_total')),
          data.get('campana', '2025/2026'), data.get('notas'),
          data.get('motivo_sin_registro') or None))
    conn.commit(); new_id = c.lastrowid; conn.close()
    _recalcular_patrones(uid, 'compras', None, data.get('fecha'), exp_id)
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/compras/<int:cid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_compra(cid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'DELETE':
        conn.execute(
            "UPDATE compras SET deleted_at=CURRENT_TIMESTAMP"
            " WHERE id=? AND user_id=? AND explotacion_id=?",
            (cid, uid, exp_id))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM compras WHERE id=? AND user_id=? AND explotacion_id=?"
                        " AND deleted_at IS NULL", (cid, uid, exp_id))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_compra(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    fields = ['fecha', 'tipo_producto', 'producto', 'num_registro_mapa', 'sustancia_activa',
              'proveedor', 'cantidad_valor', 'cantidad_unidad', 'num_lote', 'num_factura',
              'precio_total', 'campana', 'notas', 'motivo_sin_registro']
    sets = ', '.join(f"{f}=?" for f in fields)
    _real_co = {'cantidad_valor', 'precio_total'}
    conn.execute(f"UPDATE compras SET {sets}"
                 f" WHERE id=? AND user_id=? AND explotacion_id=? AND deleted_at IS NULL",
                 [_to_real(data.get(f)) if f in _real_co else data.get(f) for f in fields]
                 + [cid, uid, exp_id])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
