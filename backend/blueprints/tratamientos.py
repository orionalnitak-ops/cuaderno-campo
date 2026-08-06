"""
blueprints/tratamientos.py — validadores + /api/tratamientos/*

Aislamiento por explotación (feature 013). Este módulo es el más sensible de los
doce, porque un tratamiento apunta a cinco entidades a la vez: parcela, equipo,
aplicador, asesor y grupo UHC. Filtrar solo el listado no basta: si el POST
acepta el `equipo_id` de otra finca, el aislamiento se salta desde el propio
formulario y todo el resto del trabajo sobra.

Así que aquí se valida en las dos direcciones:
  - los listados y el endpoint por id filtran por `user_id` Y `explotacion_id`;
  - y cada id recibido del cliente se comprueba contra la explotación activa
    antes de guardar.
"""
import datetime
import re

from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid, get_active_explotacion_id, _to_real
from blueprints.ia import _recalcular_patrones

bp = Blueprint('tratamientos', __name__)

SIN_EXPLOTACION = "No tienes ninguna explotación creada"


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
        'equipo_id':           'Equipo de aplicación (Anexo III S3)',
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

def parcela_es_del_usuario(conn, parcela_id, uid, explotacion_id=None):
    """True si parcela_id existe y pertenece a uid. Evita IDOR: sin esto, cualquier
    usuario autenticado podría enviar el parcela_id de otro y colgarle registros.

    Con `explotacion_id` comprueba además que la parcela sea de esa finca
    (feature 013). Gemela de la de fertilizacion.py: se mantienen las dos copias
    porque unificarlas crearía un import cruzado entre los dos módulos más
    grandes, y ya hay bastantes ciclos que esquivar en este paquete.
    """
    sql = "SELECT id FROM parcelas WHERE id=? AND user_id=?"
    params = [parcela_id, uid]
    if explotacion_id is not None:
        sql += " AND explotacion_id=?"
        params.append(explotacion_id)
    return one(conn, sql, params) is not None


def _insert_tratamiento(c, uid, data, parcela_id, parcela_etiqueta, explotacion_id):
    """Inserta un único registro de tratamiento para la parcela dada."""
    c.execute('''
        INSERT INTO tratamientos (
            user_id, explotacion_id, parcela_id, parcela_etiqueta, fecha_aplicacion,
            producto_comercial, num_registro_mapa, sustancia_activa,
            plaga_objetivo, dosis_valor, dosis_unidad, volumen_caldo,
            equipo_id, condiciones_meteo, plazo_seguridad_dias,
            fecha_recoleccion_minima, eficacia, aplicador_id, notas, campana,
            asesor, justificacion_actuacion, asesor_id
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        uid, explotacion_id, parcela_id, parcela_etiqueta, data.get('fecha_aplicacion'),
        data.get('producto_comercial'), data.get('num_registro_mapa'), data.get('sustancia_activa'),
        data.get('plaga_objetivo'), _to_real(data.get('dosis_valor')), data.get('dosis_unidad', 'L/ha'),
        _to_real(data.get('volumen_caldo')), data.get('equipo_id') or None, data.get('condiciones_meteo'),
        data.get('plazo_seguridad_dias') or None,
        _calc_fecha_recoleccion(data.get('fecha_aplicacion'), data.get('plazo_seguridad_dias')),
        data.get('eficacia'), data.get('aplicador_id') or None, data.get('notas'),
        data.get('campana', '2025/2026'),
        data.get('asesor'), data.get('justificacion_actuacion'),
        data.get('asesor_id') or None,
    ))
    return c.lastrowid


def _check_asesor(conn, data, uid, explotacion_id=None):
    """Valida el asesor_id recibido. Devuelve (error, aviso).

    - error: bloquea el guardado. Solo si el asesor no es del usuario (IDOR).
    - aviso: NO bloquea. Se devuelve al cliente para mostrarlo como advertencia.

    A diferencia del aplicador, la falta de nº ROPO del asesor no impide guardar:
    el agricultor rara vez tiene a mano el carnet de su técnico externo y
    bloquearle el registro en plena parcela deja el módulo inservible.
    Ver spec/features/010-asesores/spec.md (decisión 2).

    Normaliza `asesor_id` in place a int o None antes de validarlo: un `<select>`
    vacío llega como '' pero un cliente puede mandar el string '0', que es truthy
    y colaba como id válido — el asesor 0 no existe y el guardado moría con un 403
    en vez de limpiar el campo.
    """
    raw = data.get('asesor_id')
    try:
        data['asesor_id'] = int(raw) or None
    except (TypeError, ValueError):
        data['asesor_id'] = None

    if not data.get('asesor_id'):
        return None, None
    sql = "SELECT nombre, num_ropo FROM asesores WHERE id=? AND user_id=?"
    params = [data['asesor_id'], uid]
    if explotacion_id is not None:
        sql += " AND explotacion_id=?"
        params.append(explotacion_id)
    asesor = one(conn, sql, params)
    if not asesor:
        return "Asesor no encontrado", None
    if not (asesor.get('num_ropo') or '').strip():
        return None, (
            f"Tratamiento guardado. Aviso: el asesor «{asesor.get('nombre')}» no tiene "
            "nº ROPO registrado. La Orden APA/204/2023 identifica al asesor por ese "
            "número — añádelo en Configuración → Asesores cuando lo tengas."
        )
    return None, None


@bp.route('/api/tratamientos', methods=['GET', 'POST'])
@login_required
def manage_tratamientos():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM tratamientos WHERE user_id=? AND explotacion_id=?"
                           " AND deleted_at IS NULL ORDER BY fecha_aplicacion DESC",
                     (uid, exp_id))
        conn.close()
        return jsonify(rows)

    data = request.json or {}
    err = _validate_tratamiento(data) or _validate_campana(data.get('campana'))
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    if not exp_id:
        conn.close()
        return jsonify({"error": SIN_EXPLOTACION}), 400

    # Verificar que el aplicador seleccionado tiene ROPO registrado (RD 1311/2012).
    # El filtro por explotación va en la misma consulta a propósito: un aplicador
    # de la otra finca debe dar "no encontrado", no colarse por tener ROPO.
    if data.get('aplicador_id'):
        aplicador = one(conn, "SELECT num_ropo FROM aplicadores"
                              " WHERE id=? AND user_id=? AND explotacion_id=?",
                        (data['aplicador_id'], uid, exp_id))
        if not aplicador or not (aplicador.get('num_ropo') or '').strip():
            conn.close()
            return jsonify({"error": (
                "El aplicador seleccionado no tiene número ROPO registrado. "
                "El ROPO es obligatorio según el RD 1311/2012 Anexo III S3. "
                "Edita el aplicador y añade su número de carnet ROPO."
            )}), 400

    # Verificar que el equipo tiene nº ROMA registrado (Orden APA/204/2023)
    if data.get('equipo_id'):
        equipo = one(conn, "SELECT num_registro_roma FROM equipos"
                           " WHERE id=? AND user_id=? AND explotacion_id=?",
                     (data['equipo_id'], uid, exp_id))
        if not equipo or not (equipo.get('num_registro_roma') or '').strip():
            conn.close()
            return jsonify({"error": (
                "El equipo seleccionado no tiene número ROMA registrado. "
                "El nº ROMA es obligatorio según la Orden APA/204/2023. "
                "Edita el equipo en Configuración y añade su número de registro ROMA."
            )}), 400

    err_asesor, aviso_asesor = _check_asesor(conn, data, uid, exp_id)
    if err_asesor:
        conn.close()
        return jsonify({"error": err_asesor}), 403

    c = conn.cursor()

    if data.get('uhc_id'):
        # u.explotacion_id Y p.explotacion_id: un grupo creado antes de la feature
        # 013 puede tener dentro parcelas de dos fincas, y aquí se expande a un
        # tratamiento por parcela. Sin el segundo filtro, un solo POST escribiría
        # registros en la otra explotación.
        parcelas = dicts(conn, """
            SELECT p.id, p.nombre_finca
            FROM uhc_parcelas up
            JOIN parcelas p ON p.id = up.parcela_id
            JOIN unidades_homogeneas u ON u.id = up.uhc_id
            WHERE up.uhc_id = ? AND u.user_id = ? AND u.deleted_at IS NULL
              AND u.explotacion_id = ? AND p.explotacion_id = ?
        """, (data['uhc_id'], uid, exp_id, exp_id))

        if not parcelas:
            conn.close()
            return jsonify({"error": "El grupo UHC no existe o no tiene parcelas asignadas"}), 400

        ids = []
        for p in parcelas:
            new_id = _insert_tratamiento(c, uid, data, p['id'], p['nombre_finca'], exp_id)
            ids.append(new_id)

        conn.commit()
        conn.close()
        for p in parcelas:
            _recalcular_patrones(uid, 'tratamientos', p['id'], data.get('fecha_aplicacion'))
        resp = {"status": "ok", "count": len(ids), "ids": ids}
        if aviso_asesor:
            resp["aviso"] = aviso_asesor
        return jsonify(resp), 201

    if not parcela_es_del_usuario(conn, data.get('parcela_id'), uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403

    new_id = _insert_tratamiento(c, uid, data, data.get('parcela_id'),
                                 data.get('parcela_etiqueta'), exp_id)
    conn.commit()
    conn.close()
    _recalcular_patrones(uid, 'tratamientos', data.get('parcela_id'), data.get('fecha_aplicacion'))
    resp = {"status": "ok", "id": new_id}
    if aviso_asesor:
        resp["aviso"] = aviso_asesor
    return jsonify(resp), 201


@bp.route('/api/tratamientos/<int:tid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_tratamiento(tid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'DELETE':
        conn.execute(
            "UPDATE tratamientos SET deleted_at=CURRENT_TIMESTAMP"
            " WHERE id=? AND user_id=? AND explotacion_id=?",
            (tid, uid, exp_id))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM tratamientos WHERE id=? AND user_id=? AND explotacion_id=?"
                        " AND deleted_at IS NULL", (tid, uid, exp_id))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_tratamiento(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    if data.get('aplicador_id'):
        aplicador = one(conn, "SELECT num_ropo FROM aplicadores"
                              " WHERE id=? AND user_id=? AND explotacion_id=?",
                        (data['aplicador_id'], uid, exp_id))
        if not aplicador or not (aplicador.get('num_ropo') or '').strip():
            conn.close()
            return jsonify({"error": (
                "El aplicador seleccionado no tiene número ROPO registrado. "
                "Edita el aplicador y añade su número de carnet ROPO antes de guardar."
            )}), 400
    if data.get('equipo_id'):
        equipo = one(conn, "SELECT num_registro_roma FROM equipos"
                           " WHERE id=? AND user_id=? AND explotacion_id=?",
                     (data['equipo_id'], uid, exp_id))
        if not equipo or not (equipo.get('num_registro_roma') or '').strip():
            conn.close()
            return jsonify({"error": (
                "El equipo seleccionado no tiene número ROMA registrado. "
                "Edita el equipo en Configuración y añade su número de registro ROMA."
            )}), 400
    err_asesor, aviso_asesor = _check_asesor(conn, data, uid, exp_id)
    if err_asesor:
        conn.close()
        return jsonify({"error": err_asesor}), 403
    if data.get('parcela_id') and not parcela_es_del_usuario(conn, data['parcela_id'], uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403
    # Calcular siempre en backend, nunca confiar en el cliente
    data['fecha_recoleccion_minima'] = _calc_fecha_recoleccion(
        data.get('fecha_aplicacion'), data.get('plazo_seguridad_dias'))
    fields = ['parcela_id', 'parcela_etiqueta', 'fecha_aplicacion', 'producto_comercial',
              'num_registro_mapa', 'sustancia_activa', 'plaga_objetivo', 'dosis_valor', 'dosis_unidad',
              'volumen_caldo', 'equipo_id', 'condiciones_meteo', 'plazo_seguridad_dias',
              'fecha_recoleccion_minima', 'eficacia', 'aplicador_id', 'notas', 'campana',
              'asesor', 'justificacion_actuacion', 'asesor_id']
    sets = ', '.join(f"{f}=?" for f in fields)
    _real_t = {'dosis_valor', 'volumen_caldo'}
    _int_t  = {'equipo_id', 'plazo_seguridad_dias', 'aplicador_id', 'asesor_id'}
    conn.execute(f"UPDATE tratamientos SET {sets}"
                 f" WHERE id=? AND user_id=? AND explotacion_id=? AND deleted_at IS NULL",
                 [_to_real(data.get(f)) if f in _real_t else (data.get(f) or None if f in _int_t else data.get(f)) for f in fields]
                 + [tid, uid, exp_id])
    conn.commit(); conn.close()
    resp = {"status": "ok"}
    if aviso_asesor:
        resp["aviso"] = aviso_asesor
    return jsonify(resp)
