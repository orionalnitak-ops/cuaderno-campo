"""
blueprints/explotacion.py — /api/explotacion, /api/stats, /api/historial
"""
import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from db import get_db, one, dicts, is_pac_eligible
from helpers import get_uid

bp = Blueprint('explotacion', __name__)


@bp.route('/api/explotacion', methods=['GET', 'PUT', 'POST'])
@login_required
def explotacion():
    uid = get_uid()
    conn = get_db()
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM explotacion WHERE user_id=? LIMIT 1", (uid,))
        # Admin sin explotación propia: usar la del agricultor principal (user_id=2)
        if not row and current_user.role == 'admin':
            row = one(conn, "SELECT * FROM explotacion WHERE user_id=2 LIMIT 1")
        conn.close()
        return jsonify(row or {})

    data = request.json or {}
    fields = ['titular', 'nif', 'municipio', 'provincia', 'cp',
              'telefono', 'email', 'campana_activa', 'fecha_apertura']
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM explotacion WHERE user_id=?", (uid,))
    if c.fetchone()[0] == 0:
        cols = ', '.join(['user_id'] + fields)
        vals = ', '.join(['?'] * (len(fields) + 1))
        c.execute(f"INSERT INTO explotacion ({cols}) VALUES ({vals})",
                  [uid] + [data.get(f) for f in fields])
    else:
        sets = ', '.join(f"{f}=?" for f in fields)
        c.execute(f"UPDATE explotacion SET {sets} WHERE user_id=?",
                  [data.get(f) for f in fields] + [uid])
    conn.commit(); conn.close()
    return jsonify({"status": "ok"})


@bp.route('/api/stats')
@login_required
def stats():
    uid = get_uid()
    conn = get_db()
    today = datetime.date.today().isoformat()
    next7 = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    campana = request.args.get('campana', '2025/2026')

    all_p = dicts(conn, "SELECT uso_sigpac FROM parcelas WHERE user_id=? AND activa=1", (uid,))
    pac_count = sum(1 for p in all_p if is_pac_eligible(p['uso_sigpac']))

    t_count = one(conn, "SELECT COUNT(*) as n FROM tratamientos WHERE user_id=? AND campana=?", (uid, campana))
    f_count = one(conn, "SELECT COUNT(*) as n FROM fertilizacion WHERE user_id=? AND campana=?", (uid, campana))
    l_count = one(conn, "SELECT COUNT(*) as n FROM labores WHERE user_id=? AND campana=?", (uid, campana))
    c_count = one(conn, "SELECT COUNT(*) as n FROM cosecha WHERE user_id=? AND campana=?", (uid, campana))
    r_count = one(conn, "SELECT COUNT(*) as n FROM riego WHERE user_id=? AND campana=? AND deleted_at IS NULL", (uid, campana))
    a_count = one(conn, "SELECT COUNT(*) as n FROM abonado WHERE user_id=? AND campana=? AND deleted_at IS NULL", (uid, campana))

    alertas = dicts(conn, """
        SELECT parcela_etiqueta, producto_comercial, fecha_recoleccion_minima
        FROM tratamientos WHERE user_id=? AND fecha_recoleccion_minima >= ? AND fecha_recoleccion_minima <= ?
    """, (uid, today, next7))

    last_row = one(conn, """
        SELECT MAX(fecha) as last_fecha FROM (
            SELECT fecha_aplicacion as fecha FROM tratamientos WHERE user_id=?
            UNION ALL SELECT fecha FROM labores WHERE user_id=?
            UNION ALL SELECT fecha_aplicacion as fecha FROM fertilizacion WHERE user_id=?
            UNION ALL SELECT fecha FROM riego WHERE user_id=? AND deleted_at IS NULL
        )
    """, (uid, uid, uid, uid))
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
        rows = dicts(conn, "SELECT * FROM tratamientos WHERE user_id=? AND deleted_at IS NULL ORDER BY fecha_aplicacion DESC", (uid,))
        for r in apply_filters(rows, 'fecha_aplicacion'):
            records.append({**r, '_modulo': 'tratamientos', '_fecha': r.get('fecha_aplicacion', ''),
                            '_resumen': f"{r.get('producto_comercial','')} — {r.get('plaga_objetivo','')}"})

    if modulo in ('todos', 'fertilizacion'):
        rows = dicts(conn, "SELECT * FROM fertilizacion WHERE user_id=? AND deleted_at IS NULL ORDER BY fecha_aplicacion DESC", (uid,))
        for r in apply_filters(rows, 'fecha_aplicacion'):
            records.append({**r, '_modulo': 'fertilizacion', '_fecha': r.get('fecha_aplicacion', ''),
                            '_resumen': (
                                f"{r.get('tipo_fertilizante','')} — {r.get('producto','')}"
                                + (f" · N:{r['n_aplicado']} P:{r['p2o5_aplicado']} K:{r['k2o_aplicado']} kg/ha"
                                   if r.get('n_aplicado') is not None else '')
                            )})

    if modulo in ('todos', 'labores'):
        rows = dicts(conn, "SELECT * FROM labores WHERE user_id=? ORDER BY fecha DESC", (uid,))
        for r in apply_filters(rows, 'fecha'):
            desc = r.get('descripcion') or r.get('notas') or ''
            records.append({**r, '_modulo': 'labores', '_fecha': r.get('fecha', ''),
                            '_resumen': f"{r.get('tipo_labor','')} — {desc}".rstrip(' —')})

    if modulo in ('todos', 'cosecha'):
        rows = dicts(conn, "SELECT * FROM cosecha WHERE user_id=? ORDER BY fecha_inicio DESC", (uid,))
        for r in apply_filters(rows, 'fecha_inicio'):
            records.append({**r, '_modulo': 'cosecha', '_fecha': r.get('fecha_inicio', ''),
                            '_resumen': f"{r.get('cultivo','')} — {r.get('produccion_total_valor','')} {r.get('produccion_total_unidad','')}"})

    if modulo in ('todos', 'compras'):
        rows = dicts(conn, "SELECT * FROM compras WHERE user_id=? AND deleted_at IS NULL ORDER BY fecha DESC", (uid,))
        for r in apply_filters(rows, 'fecha'):
            records.append({**r, '_modulo': 'compras', '_fecha': r.get('fecha', ''),
                            '_resumen': f"{r.get('tipo_producto','')} — {r.get('producto','')} · {r.get('proveedor','')}"})

    if modulo in ('todos', 'riego'):
        rows = dicts(conn, "SELECT * FROM riego WHERE user_id=? AND deleted_at IS NULL ORDER BY fecha DESC", (uid,))
        for r in apply_filters(rows, 'fecha'):
            vol = f"{r['volumen_m3']} m³" if r.get('volumen_m3') else f"{r.get('horas_riego','')} h"
            records.append({**r, '_modulo': 'riego', '_fecha': r.get('fecha', ''),
                            '_resumen': f"{r.get('tipo_riego','')} — {vol}"})

    if modulo in ('todos', 'abonado'):
        rows = dicts(conn, "SELECT * FROM abonado WHERE user_id=? AND deleted_at IS NULL ORDER BY fecha_preparacion DESC", (uid,))
        for r in apply_filters(rows, 'fecha_preparacion'):
            records.append({**r, '_modulo': 'abonado', '_fecha': r.get('fecha_preparacion', ''),
                            '_resumen': f"{r.get('cultivo','')} — N:{r.get('n_necesario_kg_ha','')} P:{r.get('p_necesario_kg_ha','')} K:{r.get('k_necesario_kg_ha','')} kg/ha"})

    if modulo in ('todos', 'cultivos_campana'):
        try:
            rows = dicts(conn, """
                SELECT cc.*, p.nombre_finca AS parcela_etiqueta
                FROM cultivos_campana cc
                JOIN parcelas p ON cc.parcela_id = p.id
                WHERE p.user_id=?
                ORDER BY cc.fecha_siembra DESC
            """, (uid,))
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
