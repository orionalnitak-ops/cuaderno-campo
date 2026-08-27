"""
blueprints/labores.py — /api/labores/*, /api/cosecha/*

Aislamiento por explotación (feature 013): toda consulta filtra por `user_id` Y
`explotacion_id`, y los POST/PUT validan que la parcela o el grupo UHC sean de la
explotación activa. Sin esa validación el aislamiento se salta desde el
formulario mandando el id de una parcela de la otra finca.
"""
import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import (get_uid, get_active_explotacion_id, _to_real,
                     repartir_por_superficie)
from blueprints.ia import _recalcular_patrones
from blueprints.fertilizacion import _parcelas_uhc, parcela_es_del_usuario

bp = Blueprint('labores', __name__)

SIN_EXPLOTACION = "No tienes ninguna explotación creada"


def _plazo_seguridad_bloquea(conn, parcela_ids, uid, exp_id, fecha_inicio, etiquetas=None):
    """Mensaje de error si alguna parcela tiene un plazo de seguridad sin vencer, o None.

    Cosechar antes de que venza el plazo de seguridad de un fitosanitario es una
    infracción, así que esto no es un aviso: corta el registro.

    Con un grupo UHC se comprueban TODAS sus parcelas y basta con que UNA esté en
    plazo para rechazar el grupo entero. No se guarda "las que se puede y las que
    no": un guardado parcial silencioso deja al agricultor creyendo que registró
    ocho parcelas cuando registró siete. Por eso el mensaje nombra la parcela y el
    producto — si no, Lourdes no puede saber qué desbloquear.
    """
    if not parcela_ids or not fecha_inicio:
        return None
    # Los ids se castean a entero antes de construir el `IN`. Los valores viajan
    # por placeholder y la interpolación solo decide CUÁNTOS `?` hay, así que no
    # hay inyección — pero en la rama de parcela suelta el id viene del payload, y
    # una consulta que no puede degradarse el día que alguien la toque vale los dos
    # renglones. Señalado por el Security Review del PR #51.
    try:
        parcela_ids = [int(pid) for pid in parcela_ids]
    except (TypeError, ValueError):
        # Fail-closed: si no se puede ni identificar la parcela, NO se puede
        # afirmar que su plazo de seguridad haya vencido. Un control legal que
        # falla en abierto es peor que no tenerlo, porque da falsa seguridad.
        return "No se ha podido comprobar el plazo de seguridad de la parcela"
    nombres = {p['id']: p.get('nombre_finca') for p in (etiquetas or [])}
    ph = ', '.join(['?'] * len(parcela_ids))
    activos = dicts(conn, f"""
        SELECT parcela_id, producto_comercial, fecha_recoleccion_minima
        FROM tratamientos
        WHERE parcela_id IN ({ph}) AND user_id=? AND explotacion_id=? AND deleted_at IS NULL
          AND fecha_recoleccion_minima > ?
        ORDER BY parcela_id
    """, list(parcela_ids) + [uid, exp_id, fecha_inicio])
    if not activos:
        return None

    detalle = []
    for a in activos:
        finca = nombres.get(a['parcela_id'])
        prod = a['producto_comercial']
        detalle.append(f"{finca}: {prod} (hasta el {a['fecha_recoleccion_minima']})"
                       if finca else prod)
    if len(parcela_ids) > 1:
        return ("No se puede registrar la cosecha del grupo: hay plazo de seguridad sin vencer en "
                + '; '.join(detalle) + ". Registra esas parcelas aparte cuando venza el plazo.")
    return ("No se puede registrar la cosecha: plazo de seguridad no vencido para: "
            + ', '.join(detalle)
            + ". Espera hasta que pasen los plazos indicados en los tratamientos.")


def _insert_cosecha(c, uid, data, parcela_id, parcela_etiqueta, exp_id, sup, prod):
    """Inserta una cosecha para UNA parcela y devuelve su id.

    `sup` y `prod` van aparte de `data` a propósito: en el registro por grupo cada
    parcela lleva SU superficie y SU parte de la producción, no las del formulario.
    """
    rend = round(prod / sup, 2) if sup > 0 else None
    c.execute('''
        INSERT INTO cosecha (user_id, explotacion_id, parcela_id, parcela_etiqueta, fecha_inicio, fecha_fin,
            cultivo, variedad, superficie_cosechada_ha, produccion_total_valor,
            produccion_total_unidad, rendimiento_kg_ha, destino, comprador,
            precio_unidad, notas, campana, fecha_venta, tipo_venta, codigo_producto_siex,
            albaran, lote, nif_cliente, direccion_cliente, provincia_cliente_cod,
            municipio_cliente_cod)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (uid, exp_id, parcela_id, parcela_etiqueta,
          data.get('fecha_inicio'), data.get('fecha_fin'), data.get('cultivo'),
          data.get('variedad'), sup, prod, data.get('produccion_total_unidad', 'kg'),
          rend, data.get('destino'), data.get('comprador'),
          _to_real(data.get('precio_unidad')), data.get('notas'), data.get('campana', '2025/2026'),
          data.get('fecha_venta'), data.get('tipo_venta'), data.get('codigo_producto_siex'),
          data.get('albaran'), data.get('lote'), data.get('nif_cliente'),
          data.get('direccion_cliente'), data.get('provincia_cliente_cod'),
          data.get('municipio_cliente_cod')))
    return c.lastrowid


def _validate_labor(data):
    """Requiere fecha y parcela o grupo UHC (antes no se validaba nada en el backend)."""
    if not data.get('fecha'):
        return "La fecha es obligatoria"
    if not data.get('parcela_id') and not data.get('uhc_id'):
        return "Se requiere una parcela o un grupo UHC"
    return None


def _insert_labor(c, uid, data, parcela_id, parcela_etiqueta, explotacion_id):
    """Inserta un único registro de labor para la parcela dada."""
    c.execute('''
        INSERT INTO labores (user_id, explotacion_id, parcela_id, parcela_etiqueta, fecha,
            tipo_labor, descripcion, producto, maquinaria, horas_trabajadas, operario, notas, campana)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (uid, explotacion_id, parcela_id, parcela_etiqueta, data.get('fecha'),
          data.get('tipo_labor'), data.get('descripcion'), data.get('producto'), data.get('maquinaria'),
          _to_real(data.get('horas_trabajadas')), data.get('operario'), data.get('notas'),
          data.get('campana', '2025/2026')))
    return c.lastrowid


@bp.route('/api/labores', methods=['GET', 'POST'])
@login_required
def manage_labores():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM labores WHERE user_id=? AND explotacion_id=?"
                           " ORDER BY fecha DESC", (uid, exp_id))
        conn.close(); return jsonify(rows)
    data = request.json or {}
    err = _validate_labor(data)
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
        ids = [_insert_labor(c, uid, data, p['id'], p['nombre_finca'], exp_id) for p in parcelas]
        conn.commit(); conn.close()
        for p in parcelas:
            _recalcular_patrones(uid, 'labores', p['id'], data.get('fecha'), exp_id)
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201

    if not parcela_es_del_usuario(conn, data.get('parcela_id'), uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403

    new_id = _insert_labor(c, uid, data, data.get('parcela_id'), data.get('parcela_etiqueta'), exp_id)
    conn.commit(); conn.close()
    _recalcular_patrones(uid, 'labores', data.get('parcela_id'), data.get('fecha'), exp_id)
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/labores/<int:lid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_labor(lid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'DELETE':
        conn.execute("DELETE FROM labores WHERE id=? AND user_id=? AND explotacion_id=?",
                     (lid, uid, exp_id))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM labores WHERE id=? AND user_id=? AND explotacion_id=?",
                  (lid, uid, exp_id))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_labor(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    if data.get('parcela_id') and not parcela_es_del_usuario(conn, data['parcela_id'], uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403
    fields = ['parcela_id', 'parcela_etiqueta', 'fecha', 'tipo_labor', 'descripcion',
              'producto', 'maquinaria', 'horas_trabajadas', 'operario', 'notas', 'campana']
    sets = ', '.join(f"{f}=?" for f in fields)
    conn.execute(f"UPDATE labores SET {sets} WHERE id=? AND user_id=? AND explotacion_id=?",
                 [_to_real(data.get(f)) if f == 'horas_trabajadas' else data.get(f) for f in fields]
                 + [lid, uid, exp_id])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})


@bp.route('/api/cosecha', methods=['GET', 'POST'])
@login_required
def manage_cosecha():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM cosecha WHERE user_id=? AND explotacion_id=?"
                           " ORDER BY fecha_inicio DESC", (uid, exp_id))
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

    # El orden importa: sin explotación activa, `parcela_es_del_usuario` cae en
    # la rama que NO filtra por explotación, así que se comprueba antes.
    if not exp_id:
        conn.close()
        return jsonify({"error": SIN_EXPLOTACION}), 400

    if not data.get('parcela_id') and not data.get('uhc_id'):
        conn.close()
        return jsonify({"error": "Se requiere una parcela o un grupo UHC"}), 400

    c = conn.cursor()

    # ── Registro por grupo UHC (feature 016) ──────────────────────────────────
    # A diferencia del plan de abonado, aquí NO se puede replicar: la producción
    # y la superficie cosechada son cantidades ABSOLUTAS. Copiar 3.000 kg en las
    # 4 parcelas de un grupo escribiría 12.000 kg en un documento legal.
    if data.get('uhc_id'):
        parcelas = _parcelas_uhc(conn, data['uhc_id'], uid, exp_id)
        if not parcelas:
            conn.close()
            return jsonify({"error": "El grupo UHC no existe o no tiene parcelas asignadas"}), 400

        err = _plazo_seguridad_bloquea(conn, [p['id'] for p in parcelas], uid, exp_id,
                                       data.get('fecha_inicio'), etiquetas=parcelas)
        if err:
            conn.close()
            return jsonify({"error": err}), 400

        reparto = repartir_por_superficie(data.get('produccion_total_valor'), parcelas)
        ids = []
        for p in parcelas:
            # La superficie cosechada de cada fila es la REAL de esa parcela, no
            # un reparto: la superficie no se estima, ya la tenemos.
            ids.append(_insert_cosecha(c, uid, data, p['id'], p['nombre_finca'], exp_id,
                                       sup=_to_real(p.get('superficie_ha')) or 0,
                                       prod=reparto.get(p['id'], 0)))
        conn.commit(); conn.close()
        for p in parcelas:
            _recalcular_patrones(uid, 'cosecha', p['id'], data.get('fecha_inicio'), exp_id)
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201

    if not parcela_es_del_usuario(conn, data['parcela_id'], uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403

    err = _plazo_seguridad_bloquea(conn, [data['parcela_id']], uid, exp_id, data.get('fecha_inicio'))
    if err:
        conn.close()
        return jsonify({"error": err}), 400

    new_id = _insert_cosecha(c, uid, data, data.get('parcela_id'), data.get('parcela_etiqueta'), exp_id,
                             sup=_to_real(data.get('superficie_cosechada_ha')) or 0,
                             prod=_to_real(data.get('produccion_total_valor')) or 0)
    conn.commit(); conn.close()
    _recalcular_patrones(uid, 'cosecha', data.get('parcela_id'), data.get('fecha_inicio'), exp_id)
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/cosecha/<int:cid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_cosecha_one(cid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'DELETE':
        conn.execute("DELETE FROM cosecha WHERE id=? AND user_id=? AND explotacion_id=?",
                     (cid, uid, exp_id))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM cosecha WHERE id=? AND user_id=? AND explotacion_id=?",
                  (cid, uid, exp_id))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    if data.get('parcela_id') and not parcela_es_del_usuario(conn, data['parcela_id'], uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403
    prod = _to_real(data.get('produccion_total_valor')) or 0
    sup  = _to_real(data.get('superficie_cosechada_ha')) or 0
    data['rendimiento_kg_ha'] = round(prod / sup, 2) if sup > 0 else None
    data['produccion_total_valor'] = prod or None
    data['superficie_cosechada_ha'] = sup or None
    fields = ['parcela_id', 'parcela_etiqueta', 'fecha_inicio', 'fecha_fin', 'cultivo',
              'variedad', 'superficie_cosechada_ha', 'produccion_total_valor', 'produccion_total_unidad',
              'rendimiento_kg_ha', 'destino', 'comprador', 'precio_unidad', 'notas', 'campana',
              'fecha_venta', 'tipo_venta', 'codigo_producto_siex', 'albaran', 'lote',
              'nif_cliente', 'direccion_cliente', 'provincia_cliente_cod', 'municipio_cliente_cod']
    _real_c = {'precio_unidad'}
    sets = ', '.join(f"{f}=?" for f in fields)
    conn.execute(f"UPDATE cosecha SET {sets} WHERE id=? AND user_id=? AND explotacion_id=?",
                 [_to_real(data.get(f)) if f in _real_c else data.get(f) for f in fields]
                 + [cid, uid, exp_id])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
