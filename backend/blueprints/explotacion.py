"""
blueprints/explotacion.py — /api/explotacion, /api/explotaciones, /api/stats, /api/historial
"""
import datetime

from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user
from db import get_db, one, dicts, is_pac_eligible
from helpers import get_uid, get_active_explotacion_id, resolve_default_explotacion

bp = Blueprint('explotacion', __name__)

# Campos editables de una explotación
_EXPL_FIELDS = ['titular', 'nombre_corto', 'nif', 'rega', 'municipio', 'provincia', 'cp',
                'telefono', 'email', 'campana_activa', 'fecha_apertura']


def _active_expl(conn, uid):
    """id de la explotación activa del usuario (crea una por defecto si no existe)."""
    exp_id = get_active_explotacion_id(conn)
    if exp_id:
        return exp_id
    # El usuario aún no tiene ninguna explotación: crear una vacía por defecto
    c = conn.cursor()
    c.execute("INSERT INTO explotacion (user_id, campana_activa) VALUES (?, ?)",
              (uid, '2025/2026'))
    conn.commit()
    return resolve_default_explotacion(conn, uid)


@bp.route('/api/explotacion', methods=['GET', 'PUT', 'POST'])
@login_required
def explotacion():
    """Explotación ACTIVA (compat hacia atrás con el modelo mono-explotación)."""
    uid = get_uid()
    conn = get_db()
    if request.method == 'GET':
        exp_id = get_active_explotacion_id(conn)
        row = one(conn, "SELECT * FROM explotacion WHERE id=? AND user_id=?", (exp_id, uid)) if exp_id else None
        # Admin sin explotación propia: usar la del agricultor principal (user_id=2)
        if not row and current_user.role == 'admin':
            row = one(conn, "SELECT * FROM explotacion WHERE user_id=2 ORDER BY orden, id LIMIT 1")
        conn.close()
        return jsonify(row or {})

    data = request.json or {}
    exp_id = _active_expl(conn, uid)
    c = conn.cursor()
    sets = ', '.join(f"{f}=?" for f in _EXPL_FIELDS)
    c.execute(f"UPDATE explotacion SET {sets} WHERE id=? AND user_id=?",
              [data.get(f) for f in _EXPL_FIELDS] + [exp_id, uid])
    conn.commit(); conn.close()
    return jsonify({"status": "ok", "id": exp_id})


@bp.route('/api/explotaciones', methods=['GET', 'POST'])
@login_required
def explotaciones():
    """Lista de explotaciones del usuario (selector) y creación (gated `pro`)."""
    uid = get_uid()
    conn = get_db()

    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM explotacion WHERE user_id=? ORDER BY orden, id", (uid,))
        active_id = get_active_explotacion_id(conn)
        for r in rows:
            r['is_active'] = (r['id'] == active_id)
        conn.close()
        return jsonify(rows)

    # POST → crear nueva explotación
    count = one(conn, "SELECT COUNT(*) AS n FROM explotacion WHERE user_id=?", (uid,))
    n = count['n'] if count else 0
    if n >= 1 and not current_user.plan_allows_multi():
        conn.close()
        return jsonify({"error": "upgrade_required", "feature": "multi_explotacion",
                        "message": "El plan Multi-explotación permite gestionar varios titulares. Sube a Pro (14,99 €)."}), 403

    data = request.json or {}
    cols = ['user_id'] + _EXPL_FIELDS + ['orden']
    vals = [uid] + [data.get(f) for f in _EXPL_FIELDS] + [n]
    placeholders = ', '.join(['?'] * len(cols))
    c = conn.cursor()
    c.execute(f"INSERT INTO explotacion ({', '.join(cols)}) VALUES ({placeholders})", vals)
    new_id = c.lastrowid
    conn.commit(); conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/explotaciones/<int:eid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def explotacion_item(eid):
    uid = get_uid()
    conn = get_db()
    owner = one(conn, "SELECT id FROM explotacion WHERE id=? AND user_id=?", (eid, uid))
    if not owner:
        conn.close()
        return jsonify({"error": "No encontrada"}), 404

    if request.method == 'GET':
        row = one(conn, "SELECT * FROM explotacion WHERE id=?", (eid,))
        conn.close()
        return jsonify(row or {})

    if request.method == 'DELETE':
        # No permitir borrar la última explotación
        count = one(conn, "SELECT COUNT(*) AS n FROM explotacion WHERE user_id=?", (uid,))
        if (count['n'] if count else 0) <= 1:
            conn.close()
            return jsonify({"error": "No puedes borrar tu única explotación"}), 400
        # No permitir borrar si tiene parcelas activas asignadas
        parc = one(conn, "SELECT COUNT(*) AS n FROM parcelas WHERE explotacion_id=? AND activa=1", (eid,))
        if parc and parc['n']:
            conn.close()
            return jsonify({"error": f"La explotación tiene {parc['n']} parcelas. Reasígnalas o bórralas antes."}), 400
        conn.execute("DELETE FROM explotacion WHERE id=? AND user_id=?", (eid, uid))
        # Si era la activa, limpiar la sesión
        if session.get('active_explotacion_id') == eid:
            session.pop('active_explotacion_id', None)
        conn.commit(); conn.close()
        return jsonify({"status": "ok"})

    # PUT → editar
    data = request.json or {}
    sets = ', '.join(f"{f}=?" for f in _EXPL_FIELDS)
    conn.execute(f"UPDATE explotacion SET {sets} WHERE id=? AND user_id=?",
                 [data.get(f) for f in _EXPL_FIELDS] + [eid, uid])
    conn.commit(); conn.close()
    return jsonify({"status": "ok"})


@bp.route('/api/explotaciones/<int:eid>/activar', methods=['POST'])
@login_required
def activar_explotacion(eid):
    uid = get_uid()
    conn = get_db()
    owner = one(conn, "SELECT id FROM explotacion WHERE id=? AND user_id=?", (eid, uid))
    conn.close()
    if not owner:
        return jsonify({"error": "No encontrada"}), 404
    session['active_explotacion_id'] = eid
    return jsonify({"status": "ok", "active_explotacion_id": eid})


@bp.route('/api/stats')
@login_required
def stats():
    uid = get_uid()
    conn = get_db()
    today = datetime.date.today().isoformat()
    next7 = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    campana = request.args.get('campana', '2025/2026')
    exp_id = get_active_explotacion_id(conn)

    # Filtro por parcelas de la explotación activa (los módulos cuelgan de parcela_id)
    pfilter = "parcela_id IN (SELECT id FROM parcelas WHERE explotacion_id=?)"

    all_p = dicts(conn, "SELECT uso_sigpac FROM parcelas WHERE user_id=? AND explotacion_id=? AND activa=1", (uid, exp_id))
    pac_count = sum(1 for p in all_p if is_pac_eligible(p['uso_sigpac']))

    t_count = one(conn, f"SELECT COUNT(*) as n FROM tratamientos WHERE user_id=? AND campana=? AND {pfilter}", (uid, campana, exp_id))
    f_count = one(conn, f"SELECT COUNT(*) as n FROM fertilizacion WHERE user_id=? AND campana=? AND {pfilter}", (uid, campana, exp_id))
    l_count = one(conn, f"SELECT COUNT(*) as n FROM labores WHERE user_id=? AND campana=? AND {pfilter}", (uid, campana, exp_id))
    c_count = one(conn, f"SELECT COUNT(*) as n FROM cosecha WHERE user_id=? AND campana=? AND {pfilter}", (uid, campana, exp_id))
    r_count = one(conn, f"SELECT COUNT(*) as n FROM riego WHERE user_id=? AND campana=? AND deleted_at IS NULL AND {pfilter}", (uid, campana, exp_id))
    a_count = one(conn, f"SELECT COUNT(*) as n FROM abonado WHERE user_id=? AND campana=? AND deleted_at IS NULL AND {pfilter}", (uid, campana, exp_id))

    alertas = dicts(conn, f"""
        SELECT parcela_etiqueta, producto_comercial, fecha_recoleccion_minima
        FROM tratamientos WHERE user_id=? AND fecha_recoleccion_minima >= ? AND fecha_recoleccion_minima <= ? AND {pfilter}
    """, (uid, today, next7, exp_id))

    last_row = one(conn, f"""
        SELECT MAX(fecha) as last_fecha FROM (
            SELECT fecha_aplicacion as fecha FROM tratamientos WHERE user_id=? AND {pfilter}
            UNION ALL SELECT fecha FROM labores WHERE user_id=? AND {pfilter}
            UNION ALL SELECT fecha_aplicacion as fecha FROM fertilizacion WHERE user_id=? AND {pfilter}
            UNION ALL SELECT fecha FROM riego WHERE user_id=? AND deleted_at IS NULL AND {pfilter}
        ) sub
    """, (uid, exp_id, uid, exp_id, uid, exp_id, uid, exp_id))
    days_inactive = 0
    if last_row and last_row.get('last_fecha'):
        try:
            last_date = datetime.date.fromisoformat(last_row['last_fecha'])
            days_inactive = (datetime.date.today() - last_date).days
        except Exception:
            days_inactive = 0

    conn.close()
    return jsonify({
        "parcelas_activas": pac_count,
        "tratamientos_mes": t_count['n'] if t_count else 0,
        "total_tratamientos": t_count['n'] if t_count else 0,
        "total_fertilizacion": f_count['n'] if f_count else 0,
        "total_labores": l_count['n'] if l_count else 0,
        "total_cosecha": c_count['n'] if c_count else 0,
        "total_riego": r_count['n'] if r_count else 0,
        "total_abonado": a_count['n'] if a_count else 0,
        "dias_sin_registro": days_inactive,
        "alertas_plazo": alertas,
    })


@bp.route('/api/historial')
@login_required
def historial():
    uid = get_uid()
    conn = get_db()
    parcela_id = request.args.get('parcela_id')
    modulo = request.args.get('modulo', 'todos')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    campana = request.args.get('campana', '')
    exp_id = get_active_explotacion_id(conn)

    # Filtro por parcelas de la explotación activa
    pfilter = "parcela_id IN (SELECT id FROM parcelas WHERE explotacion_id=?)"

    records = []

    def apply_filters(rows, date_field='fecha'):
        result = []
        for r in rows:
            if parcela_id and str(r.get('parcela_id')) != str(parcela_id):
                continue
            if campana and r.get('campana') != campana:
                continue
            f = r.get(date_field, '') or ''
            if fecha_desde and f < fecha_desde:
                continue
            if fecha_hasta and f > fecha_hasta:
                continue
            result.append(r)
        return result

    if modulo in ('todos', 'tratamientos'):
        rows = dicts(conn, f"SELECT * FROM tratamientos WHERE user_id=? AND deleted_at IS NULL AND {pfilter} ORDER BY fecha_aplicacion DESC", (uid, exp_id))
        for r in apply_filters(rows, 'fecha_aplicacion'):
            records.append({**r, '_modulo': 'tratamientos', '_fecha': r.get('fecha_aplicacion', ''),
                            '_resumen': f"{r.get('producto_comercial','')} — {r.get('plaga_objetivo','')}"})

    if modulo in ('todos', 'fertilizacion'):
        rows = dicts(conn, f"SELECT * FROM fertilizacion WHERE user_id=? AND deleted_at IS NULL AND {pfilter} ORDER BY fecha_aplicacion DESC", (uid, exp_id))
        for r in apply_filters(rows, 'fecha_aplicacion'):
            records.append({**r, '_modulo': 'fertilizacion', '_fecha': r.get('fecha_aplicacion', ''),
                            '_resumen': (
                                f"{r.get('tipo_fertilizante','')} — {r.get('producto','')}"
                                + (f" · N:{r['n_aplicado']} P:{r['p2o5_aplicado']} K:{r['k2o_aplicado']} kg/ha"
                                   if r.get('n_aplicado') is not None else '')
                            )})

    if modulo in ('todos', 'labores'):
        rows = dicts(conn, f"SELECT * FROM labores WHERE user_id=? AND {pfilter} ORDER BY fecha DESC", (uid, exp_id))
        for r in apply_filters(rows, 'fecha'):
            desc = r.get('descripcion') or r.get('notas') or ''
            records.append({**r, '_modulo': 'labores', '_fecha': r.get('fecha', ''),
                            '_resumen': f"{r.get('tipo_labor','')} — {desc}".rstrip(' —')})

    if modulo in ('todos', 'cosecha'):
        rows = dicts(conn, f"SELECT * FROM cosecha WHERE user_id=? AND {pfilter} ORDER BY fecha_inicio DESC", (uid, exp_id))
        for r in apply_filters(rows, 'fecha_inicio'):
            records.append({**r, '_modulo': 'cosecha', '_fecha': r.get('fecha_inicio', ''),
                            '_resumen': f"{r.get('cultivo','')} — {r.get('produccion_total_valor','')} {r.get('produccion_total_unidad','')}"})

    if modulo in ('todos', 'compras'):
        # Compras es un libro a nivel de usuario (no cuelga de parcela); no se acota por explotación en Fase 1.
        rows = dicts(conn, "SELECT * FROM compras WHERE user_id=? AND deleted_at IS NULL ORDER BY fecha DESC", (uid,))
        for r in apply_filters(rows, 'fecha'):
            records.append({**r, '_modulo': 'compras', '_fecha': r.get('fecha', ''),
                            '_resumen': f"{r.get('tipo_producto','')} — {r.get('producto','')} · {r.get('proveedor','')}"})

    if modulo in ('todos', 'riego'):
        rows = dicts(conn, f"SELECT * FROM riego WHERE user_id=? AND deleted_at IS NULL AND {pfilter} ORDER BY fecha DESC", (uid, exp_id))
        for r in apply_filters(rows, 'fecha'):
            vol = f"{r['volumen_m3']} m³" if r.get('volumen_m3') else f"{r.get('horas_riego','')} h"
            records.append({**r, '_modulo': 'riego', '_fecha': r.get('fecha', ''),
                            '_resumen': f"{r.get('tipo_riego','')} — {vol}"})

    if modulo in ('todos', 'abonado'):
        rows = dicts(conn, f"SELECT * FROM abonado WHERE user_id=? AND deleted_at IS NULL AND {pfilter} ORDER BY fecha_preparacion DESC", (uid, exp_id))
        for r in apply_filters(rows, 'fecha_preparacion'):
            records.append({**r, '_modulo': 'abonado', '_fecha': r.get('fecha_preparacion', ''),
                            '_resumen': f"{r.get('cultivo','')} — N:{r.get('n_necesario_kg_ha','')} P:{r.get('p_necesario_kg_ha','')} K:{r.get('k_necesario_kg_ha','')} kg/ha"})

    if modulo in ('todos', 'cultivos_campana'):
        try:
            rows = dicts(conn, """
                SELECT cc.*, p.nombre_finca AS parcela_etiqueta
                FROM cultivos_campana cc
                JOIN parcelas p ON cc.parcela_id = p.id
                WHERE p.user_id=? AND p.explotacion_id=?
                ORDER BY cc.fecha_siembra DESC
            """, (uid, exp_id))
            for r in apply_filters(rows, 'fecha_siembra'):
                sup = f"{r['superficie_cultivada_ha']} ha" if r.get('superficie_cultivada_ha') else ''
                variedad = f" · {r['variedad']}" if r.get('variedad') else ''
                records.append({**r, '_modulo': 'cultivos_campana',
                                '_fecha': str(r.get('fecha_siembra') or r.get('created_at') or ''),
                                '_resumen': f"{r.get('cultivo','')}{variedad}" + (f" · {sup}" if sup else '')})
        except Exception as e:
            import traceback, sys
            print(f"[historial] cultivos_campana ERROR: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

    records.sort(key=lambda x: str(x.get('_fecha', '') or ''), reverse=True)
    conn.close()
    return jsonify(records)
