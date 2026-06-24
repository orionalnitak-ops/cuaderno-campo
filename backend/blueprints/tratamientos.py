"""
blueprints/tratamientos.py — validadores + /api/tratamientos/*
"""
import datetime
import re

from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid, _to_real

bp = Blueprint('tratamientos', __name__)


# ─────────────────────────────────────────────
# VALIDADORES RD 1311/2012
# ─────────────────────────────────────────────

def _calc_fecha_recoleccion(fecha_aplicacion_str, plazo_dias):
    """Calcula fecha mínima de recolección. Siempre calculada en backend, nunca confiamos en el cliente."""
    try:
        fecha = datetime.date.fromisoformat(str(fecha_aplicacion_str))
        plazo = int(plazo_dias or 0)
        return (fecha + datetime.timedelta(days=plazo)).isoformat()
    except (ValueError, TypeError):
        return None


def _validate_tratamiento(data):
    """Devuelve mensaje de error si faltan campos obligatorios (Anexo III S3)."""
    required = {
        'fecha_aplicacion':    'Fecha de aplicación',
        'producto_comercial':  'Producto comercial',
        'num_registro_mapa':   'Nº Registro MAPA',
        'sustancia_activa':    'Sustancia activa',
        'plaga_objetivo':      'Plaga / enfermedad objetivo',
        'dosis_valor':         'Dosis',
        'aplicador_id':        'Aplicador (obligatorio por ROPO)',
        'equipo_aplicacion':   'Equipo de aplicación (Anexo III S3)',
        'plazo_seguridad_dias': 'Plazo de seguridad (días)',
    }
    missing = [label for field, label in required.items() if not data.get(field) and data.get(field) != 0]

    if not data.get('parcela_id') and not data.get('uhc_id'):
        missing.append('Parcela SIGPAC o Grupo UHC (Anexo III S3)')

    if missing:
        return f"Campos obligatorios según RD 1311/2012: {', '.join(missing)}"
    try:
        fecha = datetime.date.fromisoformat(str(data['fecha_aplicacion']))
        if fecha > datetime.date.today():
            return "La fecha de aplicación no puede ser futura"
    except (ValueError, TypeError):
        return "Fecha de aplicación con formato inválido (use YYYY-MM-DD)"
    try:
        if int(data['plazo_seguridad_dias']) < 0:
            return "El plazo de seguridad no puede ser negativo"
    except (ValueError, TypeError):
        return "El plazo de seguridad debe ser un número entero"
    try:
        if float(str(data['dosis_valor']).replace(',', '.')) <= 0:
            return "La dosis debe ser mayor que cero"
    except (ValueError, TypeError):
        return "La dosis debe ser un número válido"
    mapa = str(data.get('num_registro_mapa', '')).strip()
    if not re.fullmatch(r'\d{4,6}(/\d+)?', mapa):
        return "El Nº de Registro MAPA debe ser numérico (ej: 12345 o 12345/2)"
    return None


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


# ─────────────────────────────────────────────

def _insert_tratamiento(c, uid, data, parcela_id, parcela_etiqueta):
    """Inserta un único registro de tratamiento para la parcela dada."""
    c.execute('''
        INSERT INTO tratamientos (
            user_id, parcela_id, parcela_etiqueta, fecha_aplicacion,
            producto_comercial, num_registro_mapa, sustancia_activa,
            plaga_objetivo, dosis_valor, dosis_unidad, volumen_caldo,
            equipo_id, condiciones_meteo, plazo_seguridad_dias,
            fecha_recoleccion_minima, eficacia, aplicador_id, notas, campana
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        uid, parcela_id, parcela_etiqueta, data.get('fecha_aplicacion'),
        data.get('producto_comercial'), data.get('num_registro_mapa'), data.get('sustancia_activa'),
        data.get('plaga_objetivo'), _to_real(data.get('dosis_valor')), data.get('dosis_unidad', 'L/ha'),
        _to_real(data.get('volumen_caldo')), data.get('equipo_id') or None, data.get('condiciones_meteo'),
        data.get('plazo_seguridad_dias') or None,
        _calc_fecha_recoleccion(data.get('fecha_aplicacion'), data.get('plazo_seguridad_dias')),
        data.get('eficacia'), data.get('aplicador_id') or None, data.get('notas'),
        data.get('campana', '2025/2026'),
    ))
    return c.lastrowid


@bp.route('/api/tratamientos', methods=['GET', 'POST'])
@login_required
def manage_tratamientos():
    uid = get_uid()
    conn = get_db()
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM tratamientos WHERE user_id=? AND deleted_at IS NULL ORDER BY fecha_aplicacion DESC", (uid,))
        conn.close()
        return jsonify(rows)

    data = request.json or {}
    err = _validate_tratamiento(data) or _validate_campana(data.get('campana'))
    if err:
        conn.close()
        return jsonify({"error": err}), 400

    # Verificar que el aplicador seleccionado tiene ROPO registrado (RD 1311/2012)
    if data.get('aplicador_id'):
        aplicador = one(conn, "SELECT num_ropo FROM aplicadores WHERE id=? AND user_id=?",
                        (data['aplicador_id'], uid))
        if not aplicador or not (aplicador.get('num_ropo') or '').strip():
            conn.close()
            return jsonify({"error": (
                "El aplicador seleccionado no tiene número ROPO registrado. "
                "El ROPO es obligatorio según el RD 1311/2012 Anexo III S3. "
                "Edita el aplicador y añade su número de carnet ROPO."
            )}), 400

    c = conn.cursor()

    if data.get('uhc_id'):
        parcelas = dicts(conn, """
            SELECT p.id, p.nombre_finca
            FROM uhc_parcelas up
            JOIN parcelas p ON p.id = up.parcela_id
            JOIN unidades_homogeneas u ON u.id = up.uhc_id
            WHERE up.uhc_id = ? AND u.user_id = ? AND u.deleted_at IS NULL
        """, (data['uhc_id'], uid))

        if not parcelas:
            conn.close()
            return jsonify({"error": "El grupo UHC no existe o no tiene parcelas asignadas"}), 400

        ids = []
        for p in parcelas:
            new_id = _insert_tratamiento(c, uid, data, p['id'], p['nombre_finca'])
            ids.append(new_id)

        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201

    new_id = _insert_tratamiento(c, uid, data, data.get('parcela_id'), data.get('parcela_etiqueta'))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/tratamientos/<int:tid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_tratamiento(tid):
    uid = get_uid()
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute(
            "UPDATE tratamientos SET deleted_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",
            (tid, uid))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM tratamientos WHERE id=? AND user_id=? AND deleted_at IS NULL", (tid, uid))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_tratamiento(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    if data.get('aplicador_id'):
        aplicador = one(conn, "SELECT num_ropo FROM aplicadores WHERE id=? AND user_id=?",
                        (data['aplicador_id'], uid))
        if not aplicador or not (aplicador.get('num_ropo') or '').strip():
            conn.close()
            return jsonify({"error": (
                "El aplicador seleccionado no tiene número ROPO registrado. "
                "Edita el aplicador y añade su número de carnet ROPO antes de guardar."
            )}), 400
    # Calcular siempre en backend, nunca confiar en el cliente
    data['fecha_recoleccion_minima'] = _calc_fecha_recoleccion(
        data.get('fecha_aplicacion'), data.get('plazo_seguridad_dias'))
    fields = ['parcela_id', 'parcela_etiqueta', 'fecha_aplicacion', 'producto_comercial',
              'num_registro_mapa', 'sustancia_activa', 'plaga_objetivo', 'dosis_valor', 'dosis_unidad',
              'volumen_caldo', 'equipo_id', 'condiciones_meteo', 'plazo_seguridad_dias',
              'fecha_recoleccion_minima', 'eficacia', 'aplicador_id', 'notas', 'campana']
    sets = ', '.join(f"{f}=?" for f in fields)
    _real_t = {'dosis_valor', 'volumen_caldo'}
    _int_t  = {'equipo_id', 'plazo_seguridad_dias', 'aplicador_id'}
    conn.execute(f"UPDATE tratamientos SET {sets} WHERE id=? AND user_id=? AND deleted_at IS NULL",
                 [_to_real(data.get(f)) if f in _real_t else (data.get(f) or None if f in _int_t else data.get(f)) for f in fields] + [tid, uid])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
