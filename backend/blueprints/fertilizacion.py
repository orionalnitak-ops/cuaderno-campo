"""
blueprints/fertilizacion.py — /api/fertilizacion/*, /api/riego/*, /api/abonado/*

Aislamiento por explotación (feature 013): toda consulta de los tres módulos
filtra por `user_id` Y `explotacion_id`, y los POST/PUT validan que la parcela o
el grupo UHC sean de la explotación activa antes de guardar.
"""
import datetime
import re

from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid, get_active_explotacion_id, _to_real
from blueprints.ia import _recalcular_patrones

bp = Blueprint('fertilizacion', __name__)

SIN_EXPLOTACION = "No tienes ninguna explotación creada"


# ─────────────────────────────────────────────
# VALIDADORES
# ─────────────────────────────────────────────

def _validate_fertilizacion(data):
    """Devuelve mensaje de error si faltan campos obligatorios (Anexo III S4)."""
    required = {
        'fecha_aplicacion': 'Fecha de aplicación',
        'tipo_fertilizante': 'Tipo de fertilizante',
        'producto':          'Nombre del producto',
        'dosis_valor':       'Dosis (cantidad)',
    }
    missing = [label for field, label in required.items() if not data.get(field) and data.get(field) != 0]
    if not data.get('parcela_id') and not data.get('uhc_id'):
        missing.append('Parcela SIGPAC o Grupo UHC (Anexo III S4)')
    if missing:
        return f"Campos obligatorios según RD 1311/2012: {', '.join(missing)}"
    try:
        fecha = datetime.date.fromisoformat(str(data['fecha_aplicacion']))
        if fecha > datetime.date.today():
            return "La fecha de aplicación no puede ser futura"
    except (ValueError, TypeError):
        return "Fecha de aplicación con formato inválido (use YYYY-MM-DD)"
    try:
        if float(str(data['dosis_valor']).replace(',', '.')) <= 0:
            return "La dosis debe ser mayor que cero"
    except (ValueError, TypeError):
        return "La dosis debe ser un número válido"
    if str(data.get('dosis_unidad', '')).strip().lower() in ('l/ha', 'l ha', 'litros/ha'):
        dens = data.get('densidad_g_ml')
        if not dens:
            return "Para fertilizantes líquidos (L/ha) indica la densidad en g/mL para calcular NPK correctamente"
        try:
            if float(str(dens).replace(',', '.')) <= 0:
                return "La densidad debe ser mayor que cero"
        except (ValueError, TypeError):
            return "La densidad debe ser un número válido (g/mL)"
    return None


def _calc_npk(riqueza_npk, dosis_valor, dosis_unidad='kg/ha', densidad_g_ml=None):
    """Parsea riqueza N-P-K y devuelve (n, p, k) en kg/ha.
    Soporta: '15-15-15', '27-0-0', '46%N', '34,5%N', '18%N 46%P2O5 0%K2O'.
    Para líquidos (L/ha) requiere densidad_g_ml para convertir a kg/ha correctamente.
    Devuelve (None, None, None) si no es parseable."""
    if not riqueza_npk or not dosis_valor:
        return None, None, None
    try:
        dosis = float(str(dosis_valor).replace(',', '.'))
        if dosis <= 0:
            return None, None, None
    except (ValueError, TypeError):
        return None, None, None
    # Convertir L/ha → kg/ha usando densidad (g/mL = kg/L)
    if str(dosis_unidad).strip().lower() in ('l/ha', 'l ha', 'litros/ha'):
        try:
            dens = float(str(densidad_g_ml).replace(',', '.'))
            if dens > 0:
                dosis = dosis * dens
            else:
                return None, None, None
        except (ValueError, TypeError):
            return None, None, None
    s = str(riqueza_npk).replace(',', '.').upper()
    # Formato triple N-P-K (ej: "15-15-15", "27-0-0", "15 15 15")
    m3 = re.search(r'(\d+\.?\d*)[^\d]+(\d+\.?\d*)[^\d]+(\d+\.?\d*)', s)
    if m3:
        try:
            return (round(float(m3.group(1)) / 100 * dosis, 2),
                    round(float(m3.group(2)) / 100 * dosis, 2),
                    round(float(m3.group(3)) / 100 * dosis, 2))
        except (ValueError, TypeError):
            pass
    # Formato con letra: "46%N", "34.5%N 0%P 0%K", "18%N46%P2O5"
    def _pct(letter):
        m = re.search(r'(\d+\.?\d*)\s*%?\s*' + letter + r'(?:[^A-Z]|$)', s)
        if m:
            try:
                return round(float(m.group(1)) / 100 * dosis, 2)
            except (ValueError, TypeError):
                pass
        return None
    n = _pct('N')
    p = _pct('P')
    k = _pct('K')
    if any(v is not None for v in (n, p, k)):
        return (n or 0.0, p or 0.0, k or 0.0)
    return None, None, None


def _validate_riego(data):
    """Valida campos obligatorios del registro de riego (RD 934/2025).
    Requiere fecha, parcela o grupo UHC, tipo y al menos horas o m³."""
    required = {
        'fecha':      'Fecha de riego',
        'tipo_riego': 'Tipo de riego',
    }
    missing = [label for field, label in required.items() if not data.get(field)]
    if not data.get('parcela_id') and not data.get('uhc_id'):
        missing.append('Parcela o Grupo UHC')
    if missing:
        return f"Campos obligatorios: {', '.join(missing)}"
    if not data.get('horas_riego') and not data.get('volumen_m3'):
        return "Indica al menos las horas de riego o el volumen en m³"
    try:
        fecha = datetime.date.fromisoformat(str(data['fecha']))
        if fecha > datetime.date.today():
            return "La fecha de riego no puede ser futura"
    except (ValueError, TypeError):
        return "Fecha con formato inválido (use YYYY-MM-DD)"
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


def _validate_abonado(data):
    required = {
        'cultivo':                  'Cultivo',
        'cultivo_anterior':         'Cultivo anterior',
        'rendimiento_esperado_kg_ha': 'Rendimiento esperado',
        'fecha_preparacion':        'Fecha de preparación',
        'datos_suelo':              'Datos de análisis de suelo (RD 934/2025)',
        'n_necesario_kg_ha':        'N necesario',
        'p_necesario_kg_ha':        'P necesario',
        'k_necesario_kg_ha':        'K necesario',
    }
    missing = [label for field, label in required.items() if not str(data.get(field, '')).strip()]
    if not data.get('parcela_id') and not data.get('uhc_id'):
        missing.append('Parcela o Grupo UHC')
    if missing:
        return f"Campos obligatorios: {', '.join(missing)}"
    try:
        fecha = datetime.date.fromisoformat(str(data['fecha_preparacion']))
        if fecha > datetime.date.today():
            return "La fecha de preparación no puede ser futura"
    except (ValueError, TypeError):
        return "Fecha con formato inválido (use YYYY-MM-DD)"
    return None


# ─────────────────────────────────────────────
# FERTILIZACIÓN
# ─────────────────────────────────────────────

def _insert_fertilizacion(c, uid, data, parcela_id, parcela_etiqueta, n_ap, p_ap, k_ap,
                          explotacion_id):
    """Inserta un único registro de fertilización para la parcela dada."""
    c.execute('''
        INSERT INTO fertilizacion (
            user_id, explotacion_id, parcela_id, parcela_etiqueta, fecha_aplicacion,
            tipo_fertilizante, producto, riqueza_npk,
            dosis_valor, dosis_unidad, densidad_g_ml, metodo_aplicacion, notas, campana,
            n_aplicado, p2o5_aplicado, k2o_aplicado
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (uid, explotacion_id, parcela_id, parcela_etiqueta, data.get('fecha_aplicacion'),
          data.get('tipo_fertilizante'), data.get('producto'), data.get('riqueza_npk'),
          _to_real(data.get('dosis_valor')), data.get('dosis_unidad', 'kg/ha'),
          _to_real(data.get('densidad_g_ml')),
          data.get('metodo_aplicacion'), data.get('notas'), data.get('campana', '2025/2026'),
          n_ap, p_ap, k_ap))
    return c.lastrowid


def _parcelas_uhc(conn, uhc_id, uid, explotacion_id=None):
    """Parcelas (id, nombre_finca, superficie_ha) de un grupo UHC, o [] si no existe/no tiene.

    Con `explotacion_id` exige que el grupo Y sus parcelas sean de esa finca
    (feature 013). Se comprueban las dos cosas y no solo el grupo: si algún UHC
    antiguo quedó con parcelas de dos explotaciones, expandirlo metería registros
    en la finca equivocada.

    `superficie_ha` la necesita el reparto de cantidades absolutas en cosecha y en
    cultivo campaña (feature 016). A los módulos que replican valores por hectárea
    les sobra, pero devolverla siempre evita tener dos variantes de esta consulta.

    `uhc_id` llega del payload de la petición en las cinco rutas que llaman aquí,
    así que se castea a entero EN ESTE SITIO y no en cada una: un `uhc_id` que no
    sea un número (lista, dict, texto) no es un problema de inyección —va por
    placeholder— pero en PostgreSQL revienta la consulta y devuelve un 500 en vez
    de un error legible. Tratarlo como "grupo inexistente" es la respuesta honesta.
    Señalado por el Security Review del PR #51.
    """
    try:
        uhc_id = int(uhc_id)
    except (TypeError, ValueError):
        return []
    sql = """
        SELECT p.id, p.nombre_finca, p.superficie_ha
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


def parcela_es_del_usuario(conn, parcela_id, uid, explotacion_id=None):
    """True si parcela_id existe y pertenece a uid. Evita IDOR: sin esto, cualquier
    usuario autenticado podría enviar el parcela_id de otro y colgarle registros.

    Con `explotacion_id` comprueba además que la parcela sea de esa finca
    (feature 013). Sin eso, el aislamiento se salta desde el propio formulario:
    basta mandar el id de una parcela de la otra explotación del mismo usuario.
    """
    sql = "SELECT id FROM parcelas WHERE id=? AND user_id=?"
    params = [parcela_id, uid]
    if explotacion_id is not None:
        sql += " AND explotacion_id=?"
        params.append(explotacion_id)
    return one(conn, sql, params) is not None


@bp.route('/api/fertilizacion', methods=['GET', 'POST'])
@login_required
def manage_fertilizacion():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM fertilizacion WHERE user_id=? AND explotacion_id=?"
                           " AND deleted_at IS NULL ORDER BY fecha_aplicacion DESC", (uid, exp_id))
        conn.close(); return jsonify(rows)

    data = request.json or {}
    err = _validate_fertilizacion(data) or _validate_campana(data.get('campana'))
    if err:
        conn.close()
        return jsonify({"error": err}), 400

    if not exp_id:
        conn.close()
        return jsonify({"error": SIN_EXPLOTACION}), 400

    n_ap, p_ap, k_ap = _calc_npk(data.get('riqueza_npk'), data.get('dosis_valor'),
                                  data.get('dosis_unidad', 'kg/ha'), data.get('densidad_g_ml'))
    c = conn.cursor()

    if data.get('uhc_id'):
        parcelas = _parcelas_uhc(conn, data['uhc_id'], uid, exp_id)
        if not parcelas:
            conn.close()
            return jsonify({"error": "El grupo UHC no existe o no tiene parcelas asignadas"}), 400
        ids = [_insert_fertilizacion(c, uid, data, p['id'], p['nombre_finca'], n_ap, p_ap, k_ap, exp_id)
               for p in parcelas]
        conn.commit(); conn.close()
        for p in parcelas:
            _recalcular_patrones(uid, 'fertilizacion', p['id'], data.get('fecha_aplicacion'), exp_id)
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201

    if not parcela_es_del_usuario(conn, data.get('parcela_id'), uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403

    new_id = _insert_fertilizacion(c, uid, data, data.get('parcela_id'),
                                   data.get('parcela_etiqueta'), n_ap, p_ap, k_ap, exp_id)
    conn.commit(); conn.close()
    _recalcular_patrones(uid, 'fertilizacion', data.get('parcela_id'), data.get('fecha_aplicacion'), exp_id)
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/fertilizacion/<int:fid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_fertilizacion_one(fid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'DELETE':
        conn.execute(
            "UPDATE fertilizacion SET deleted_at=CURRENT_TIMESTAMP"
            " WHERE id=? AND user_id=? AND explotacion_id=?",
            (fid, uid, exp_id))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM fertilizacion WHERE id=? AND user_id=? AND explotacion_id=?"
                        " AND deleted_at IS NULL", (fid, uid, exp_id))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_fertilizacion(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    if data.get('parcela_id') and not parcela_es_del_usuario(conn, data['parcela_id'], uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403
    n_ap, p_ap, k_ap = _calc_npk(data.get('riqueza_npk'), data.get('dosis_valor'),
                                  data.get('dosis_unidad', 'kg/ha'), data.get('densidad_g_ml'))
    fields = ['parcela_id', 'parcela_etiqueta', 'fecha_aplicacion', 'tipo_fertilizante',
              'producto', 'riqueza_npk', 'dosis_valor', 'dosis_unidad', 'densidad_g_ml',
              'metodo_aplicacion', 'notas', 'campana',
              'n_aplicado', 'p2o5_aplicado', 'k2o_aplicado']
    sets = ', '.join(f"{f}=?" for f in fields)
    _real_f = {'dosis_valor', 'densidad_g_ml'}
    npk_map = {'n_aplicado': n_ap, 'p2o5_aplicado': p_ap, 'k2o_aplicado': k_ap}
    values = [_to_real(data.get(f)) if f in _real_f else npk_map.get(f, data.get(f)) for f in fields]
    conn.execute(f"UPDATE fertilizacion SET {sets}"
                 f" WHERE id=? AND user_id=? AND explotacion_id=? AND deleted_at IS NULL",
                 values + [fid, uid, exp_id])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})


# ─────────────────────────────────────────────
# RIEGO
# ─────────────────────────────────────────────

def _insert_riego(c, uid, data, parcela_id, parcela_etiqueta, explotacion_id):
    """Inserta un único registro de riego para la parcela dada."""
    c.execute('''
        INSERT INTO riego (
            user_id, explotacion_id, parcela_id, parcela_etiqueta, fecha,
            tipo_riego, volumen_m3, horas_riego, fuente_agua, notas, campana,
            superficie_ha, sistema_riego_cod, unidad_cantidad_cod, dosis_valor,
            dosis_unidad, origen_agua_cod, num_contador, tipo_energia_cod,
            decl_buenas_practicas, buena_practica_cod
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (uid, explotacion_id, parcela_id, parcela_etiqueta, data.get('fecha'),
          data.get('tipo_riego'), _to_real(data.get('volumen_m3')),
          _to_real(data.get('horas_riego')), data.get('fuente_agua'), data.get('notas'),
          data.get('campana', '2025/2026'),
          _to_real(data.get('superficie_ha')), data.get('sistema_riego_cod'),
          data.get('unidad_cantidad_cod'), _to_real(data.get('dosis_valor')),
          data.get('dosis_unidad'), data.get('origen_agua_cod'), data.get('num_contador'),
          data.get('tipo_energia_cod'), data.get('decl_buenas_practicas'),
          data.get('buena_practica_cod')))
    return c.lastrowid


@bp.route('/api/riego', methods=['GET', 'POST'])
@login_required
def manage_riego():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        campana = request.args.get('campana', '2025/2026')
        rows = dicts(conn, "SELECT * FROM riego WHERE user_id=? AND explotacion_id=? AND campana=?"
                           " AND deleted_at IS NULL ORDER BY fecha DESC", (uid, exp_id, campana))
        conn.close(); return jsonify(rows)

    data = request.json or {}
    err = _validate_riego(data)
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
        ids = [_insert_riego(c, uid, data, p['id'], p['nombre_finca'], exp_id) for p in parcelas]
        conn.commit(); conn.close()
        for p in parcelas:
            _recalcular_patrones(uid, 'riego', p['id'], data.get('fecha'), exp_id)
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201

    if not parcela_es_del_usuario(conn, data.get('parcela_id'), uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403

    new_id = _insert_riego(c, uid, data, data.get('parcela_id'),
                           data.get('parcela_etiqueta'), exp_id)
    conn.commit(); conn.close()
    _recalcular_patrones(uid, 'riego', data.get('parcela_id'), data.get('fecha'), exp_id)
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/riego/<int:rid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_riego_one(rid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'DELETE':
        conn.execute(
            "UPDATE riego SET deleted_at=CURRENT_TIMESTAMP"
            " WHERE id=? AND user_id=? AND explotacion_id=?",
            (rid, uid, exp_id))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM riego WHERE id=? AND user_id=? AND explotacion_id=?"
                        " AND deleted_at IS NULL", (rid, uid, exp_id))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_riego(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    if data.get('parcela_id') and not parcela_es_del_usuario(conn, data['parcela_id'], uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403
    fields = ['parcela_id', 'parcela_etiqueta', 'fecha', 'tipo_riego', 'volumen_m3',
              'horas_riego', 'fuente_agua', 'notas', 'campana',
              'superficie_ha', 'sistema_riego_cod', 'unidad_cantidad_cod', 'dosis_valor',
              'dosis_unidad', 'origen_agua_cod', 'num_contador', 'tipo_energia_cod',
              'decl_buenas_practicas', 'buena_practica_cod']
    sets = ', '.join(f"{f}=?" for f in fields)
    numeric = {'volumen_m3', 'horas_riego', 'superficie_ha', 'dosis_valor'}
    values = [_to_real(data.get(f)) if f in numeric else data.get(f) for f in fields]
    conn.execute(f"UPDATE riego SET {sets}"
                 f" WHERE id=? AND user_id=? AND explotacion_id=? AND deleted_at IS NULL",
                 values + [rid, uid, exp_id])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})


# ─────────────────────────────────────────────
# PLAN DE ABONADO
# ─────────────────────────────────────────────

def _insert_abonado(c, uid, data, parcela_id, parcela_etiqueta, exp_id):
    """Inserta un plan de abonado para UNA parcela y devuelve su id.

    Extraído del POST para poder reutilizarlo desde la rama de grupo UHC sin
    duplicar la lista de columnas: dos INSERT idénticos se desincronizan en cuanto
    alguien añade un campo a uno solo. Mismo patrón que `_insert_fertilizacion`.
    """
    c.execute('''
        INSERT INTO abonado (
            user_id, explotacion_id, parcela_id, parcela_etiqueta, cultivo, cultivo_anterior,
            rendimiento_esperado_kg_ha, n_necesario_kg_ha, p_necesario_kg_ha,
            k_necesario_kg_ha, fecha_preparacion, datos_suelo,
            abono_recomendado, dosis_recomendada_kg_ha, notas, campana
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (uid, exp_id, parcela_id, parcela_etiqueta,
          data.get('cultivo'), data.get('cultivo_anterior'),
          data.get('rendimiento_esperado_kg_ha') or None,
          data.get('n_necesario_kg_ha'), data.get('p_necesario_kg_ha'), data.get('k_necesario_kg_ha'),
          data.get('fecha_preparacion'), data.get('datos_suelo'),
          data.get('abono_recomendado'), data.get('dosis_recomendada_kg_ha') or None,
          data.get('notas'), data.get('campana', '2025/2026')))
    return c.lastrowid


@bp.route('/api/abonado', methods=['GET', 'POST'])
@login_required
def manage_abonado():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        campana = request.args.get('campana', '2025/2026')
        rows = dicts(conn, "SELECT * FROM abonado WHERE user_id=? AND explotacion_id=? AND campana=?"
                           " AND deleted_at IS NULL ORDER BY fecha_preparacion DESC",
                     (uid, exp_id, campana))
        conn.close(); return jsonify(rows)

    data = request.json or {}
    err = _validate_abonado(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    # El orden importa: sin explotación activa, `parcela_es_del_usuario` cae en
    # la rama que NO filtra por explotación, así que se comprueba antes.
    if not exp_id:
        conn.close()
        return jsonify({"error": SIN_EXPLOTACION}), 400
    c = conn.cursor()

    # Registro por grupo UHC: se expande a un plan por parcela (feature 016). Todos
    # los campos del plan de abonado son POR HECTÁREA (N/P/K necesarios, dosis
    # recomendada, rendimiento esperado), así que se replican tal cual — aquí no
    # hay nada que repartir, al contrario que en cosecha o en cultivo campaña.
    if data.get('uhc_id'):
        parcelas = _parcelas_uhc(conn, data['uhc_id'], uid, exp_id)
        if not parcelas:
            conn.close()
            return jsonify({"error": "El grupo UHC no existe o no tiene parcelas asignadas"}), 400
        ids = [_insert_abonado(c, uid, data, p['id'], p['nombre_finca'], exp_id) for p in parcelas]
        conn.commit(); conn.close()
        return jsonify({"status": "ok", "count": len(ids), "ids": ids}), 201

    if not parcela_es_del_usuario(conn, data.get('parcela_id'), uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403

    new_id = _insert_abonado(c, uid, data, data.get('parcela_id'),
                             data.get('parcela_etiqueta'), exp_id)
    conn.commit(); conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/abonado/<int:aid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_abonado_one(aid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'DELETE':
        conn.execute(
            "UPDATE abonado SET deleted_at=CURRENT_TIMESTAMP"
            " WHERE id=? AND user_id=? AND explotacion_id=?",
            (aid, uid, exp_id))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM abonado WHERE id=? AND user_id=? AND explotacion_id=?"
                        " AND deleted_at IS NULL", (aid, uid, exp_id))
        conn.close(); return jsonify(row or {})
    data = request.json or {}
    err = _validate_abonado(data)
    if err:
        conn.close()
        return jsonify({"error": err}), 400
    # `_validate_abonado` acepta parcela O grupo, porque al CREAR se admiten los dos
    # (feature 016). Editar es otra cosa: se toca un plan concreto, que ya está
    # atado a su parcela. Sin esta comprobación, un PUT con solo `uhc_id` dejaría
    # `parcela_id = NULL` y el plan quedaría huérfano en el cuaderno.
    if not data.get('parcela_id'):
        conn.close()
        return jsonify({"error": "La parcela es obligatoria al editar un plan de abonado"}), 400
    if not parcela_es_del_usuario(conn, data['parcela_id'], uid, exp_id):
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 403
    fields = ['parcela_id', 'parcela_etiqueta', 'cultivo', 'cultivo_anterior',
              'rendimiento_esperado_kg_ha', 'n_necesario_kg_ha', 'p_necesario_kg_ha',
              'k_necesario_kg_ha', 'fecha_preparacion', 'datos_suelo',
              'abono_recomendado', 'dosis_recomendada_kg_ha', 'notas', 'campana']
    numeric = {'rendimiento_esperado_kg_ha', 'n_necesario_kg_ha', 'p_necesario_kg_ha',
               'k_necesario_kg_ha', 'dosis_recomendada_kg_ha'}
    sets = ', '.join(f"{f}=?" for f in fields)
    values = [data.get(f) or None if f in numeric else data.get(f) for f in fields]
    conn.execute(f"UPDATE abonado SET {sets}"
                 f" WHERE id=? AND user_id=? AND explotacion_id=? AND deleted_at IS NULL",
                 values + [aid, uid, exp_id])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
