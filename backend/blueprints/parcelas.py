"""
blueprints/parcelas.py — /api/parcelas/* y /api/cultivos-campana/*
"""
import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import login_required
from extensions import limiter
from db import get_db, one, dicts, is_pac_eligible
from helpers import get_uid, _to_real, get_active_explotacion_id, estado_sigpac
from blueprints.ia import _recalcular_patrones
from blueprints.sigpac import superficie_sigpac_parcela

bp = Blueprint('parcelas', __name__)

# Allowlist de columnas actualizables en parcelas. Estos nombres se interpolan en el
# SQL del UPDATE (los placeholders `?` no parametrizan identificadores de columna), así
# que DEBEN provenir siempre de esta constante y nunca de input del usuario.
_PARCELA_UPDATE_FIELDS = (
    'comunidad', 'provincia_cod', 'provincia_nombre', 'municipio_cod', 'municipio_nombre',
    'nombre_finca', 'poligono', 'parcela_num', 'recinto', 'superficie_ha', 'uso_sigpac',
    'referencia_cat', 'sistema_explotacion', 'masa_agua_cercana', 'notas',
)
_PARCELA_UPDATE_ALLOWED = frozenset(_PARCELA_UPDATE_FIELDS)

# Referencia catastral: hasta 20 caracteres alfanuméricos (formato oficial español).
_REF_CAT_RE = re.compile(r'^[A-Z0-9]{1,20}$')


def _clean_ref_cat(v):
    """Normaliza y valida la referencia catastral.

    Devuelve (valor, error): valor '' si viene vacío (campo opcional), la RC en
    mayúsculas si es válida, o (None, mensaje) si el formato no encaja.
    """
    if v is None or str(v).strip() == '':
        return '', None
    v = str(v).strip().upper()
    if not _REF_CAT_RE.match(v):
        return None, "Formato de referencia catastral inválido"
    return v, None


@bp.route('/api/parcelas', methods=['GET', 'POST'])
@login_required
def manage_parcelas():
    uid = get_uid()
    conn = get_db()

    if request.method == 'GET':
        exp_id = get_active_explotacion_id(conn)
        all_p = dicts(conn, "SELECT * FROM parcelas WHERE user_id=? AND explotacion_id=? AND activa=1 ORDER BY nombre_finca", (uid, exp_id))
        pac_only = request.args.get('pac_only', 'false').lower() == 'true'
        if pac_only:
            all_p = [p for p in all_p if is_pac_eligible(p.get('uso_sigpac', ''))]
        for p in all_p:
            estado, diff = estado_sigpac(p)
            p['sigpac_estado'] = estado
            p['sigpac_diferencia_pct'] = diff
        conn.close()
        return jsonify(all_p)

    data = request.json or {}

    def _to_float(v):
        if v is None or v == '': return None
        try: return float(str(v).replace(',', '.'))
        except (ValueError, TypeError): return None

    sup = _to_float(data.get('superficie_ha'))
    if sup is not None and sup <= 0:
        conn.close()
        return jsonify({"error": "La superficie debe ser mayor que cero"}), 400

    ref_cat, ref_err = _clean_ref_cat(data.get('referencia_cat'))
    if ref_err:
        conn.close()
        return jsonify({"error": ref_err}), 400

    exp_id = get_active_explotacion_id(conn)
    c = conn.cursor()
    c.execute('''
        INSERT INTO parcelas (
            user_id, explotacion_id, comunidad, provincia_cod, provincia_nombre,
            municipio_cod, municipio_nombre, nombre_finca,
            poligono, parcela_num, recinto, superficie_ha, uso_sigpac, referencia_cat,
            sistema_explotacion, masa_agua_cercana, notas
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        uid, exp_id, data.get('comunidad'), data.get('provincia_cod'), data.get('provincia_nombre'),
        data.get('municipio_cod'), data.get('municipio_nombre'), data.get('nombre_finca'),
        data.get('poligono'), data.get('parcela_num'), data.get('recinto'),
        sup, data.get('uso_sigpac'), ref_cat,
        data.get('sistema_explotacion', 'Secano'),
        1 if data.get('masa_agua_cercana') else 0,
        data.get('notas'),
    ))
    new_id = c.lastrowid
    conn.commit(); conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/parcelas/<int:pid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_parcela(pid):
    uid = get_uid()
    conn = get_db()
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM parcelas WHERE id=? AND user_id=?", (pid, uid))
        conn.close()
        if row:
            estado, diff = estado_sigpac(row)
            row['sigpac_estado'] = estado
            row['sigpac_diferencia_pct'] = diff
        return jsonify(row or {})

    if request.method == 'DELETE':
        orphan_counts = {}
        for table, label in [('tratamientos', 'tratamientos'), ('fertilizacion', 'fertilizaciones'),
                              ('cosecha', 'cosechas'), ('labores', 'labores'), ('riego', 'riegos')]:
            try:
                row = one(conn, f"SELECT COUNT(*) as n FROM {table} WHERE parcela_id=? AND user_id=?", (pid, uid))
                if row and row['n']:
                    orphan_counts[label] = row['n']
            except Exception:
                pass
        conn.execute("UPDATE parcelas SET activa=0 WHERE id=? AND user_id=?", (pid, uid))
        conn.commit(); conn.close()
        resp = {"status": "ok"}
        if orphan_counts:
            detalle = ', '.join(f"{n} {k}" for k, n in orphan_counts.items())
            resp["warning"] = f"La parcela tenía registros asociados: {detalle}. Siguen en el historial pero sin parcela activa."
        return jsonify(resp)

    data = request.json or {}

    def _to_float(v):
        if v is None or v == '': return None
        try: return float(str(v).replace(',', '.'))
        except (ValueError, TypeError): return None

    sup_put = _to_float(data.get('superficie_ha'))
    if sup_put is not None and sup_put <= 0:
        conn.close()
        return jsonify({"error": "La superficie debe ser mayor que cero"}), 400

    ref_cat, ref_err = _clean_ref_cat(data.get('referencia_cat'))
    if ref_err:
        conn.close()
        return jsonify({"error": ref_err}), 400

    def _field_val(f):
        v = data.get(f)
        if f == 'superficie_ha': return sup_put
        if f == 'referencia_cat': return ref_cat
        if f == 'masa_agua_cercana': return 1 if v else 0
        return v

    # Solo columnas de la allowlist: sus nombres se interpolan en el SQL.
    fields = [f for f in _PARCELA_UPDATE_FIELDS if f in _PARCELA_UPDATE_ALLOWED]
    sets = ', '.join(f"{f}=?" for f in fields)
    vals = [_field_val(f) for f in fields] + [pid, uid]
    conn.execute(f"UPDATE parcelas SET {sets} WHERE id=? AND user_id=?", vals)
    conn.commit(); conn.close()
    return jsonify({"status": "ok"})


@bp.route('/api/parcelas/<int:pid>/verificar-sigpac', methods=['POST'])
@login_required
@limiter.limit("60 per minute")
def verificar_sigpac(pid):
    """Contrasta la superficie de la parcela con SIGPAC y persiste el resultado."""
    uid = get_uid()
    conn = get_db()
    p = one(conn, "SELECT * FROM parcelas WHERE id=? AND user_id=?", (pid, uid))
    if not p:
        conn.close()
        return jsonify({"ok": False, "error": "Parcela no encontrada"}), 404

    prov, mun = p.get('provincia_cod'), p.get('municipio_cod')
    pol, par, rec = p.get('poligono'), p.get('parcela_num'), p.get('recinto')
    if not all([prov, mun, pol, par]):
        conn.close()
        return jsonify({"ok": False, "error": "La parcela no tiene datos SIGPAC completos"}), 400

    ha, resultado = superficie_sigpac_parcela(prov, mun, pol, par, rec)
    if resultado == 'error':
        conn.close()
        return jsonify({"ok": False, "error": "SIGPAC no disponible, inténtalo de nuevo"}), 503

    # resultado 'ok' (ha float) o 'no_encontrada' (ha None) -> ambos se persisten con timestamp.
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    conn.execute(
        "UPDATE parcelas SET sigpac_superficie_ha=?, sigpac_verificado_en=? WHERE id=? AND user_id=?",
        (ha, now, pid, uid),
    )
    conn.commit()
    row = one(conn, "SELECT * FROM parcelas WHERE id=? AND user_id=?", (pid, uid))
    conn.close()
    estado, diff = estado_sigpac(row)
    return jsonify({
        "ok": True, "estado": estado,
        "sigpac_superficie_ha": ha, "diferencia_pct": diff,
        "sigpac_verificado_en": now,
    })


@bp.route('/api/cultivos-campana', methods=['GET', 'POST'])
@login_required
def manage_cultivos():
    uid = get_uid()
    conn = get_db()
    if request.method == 'GET':
        parcela_id = request.args.get('parcela_id')
        campana = request.args.get('campana')
        # Filtrar siempre por user_id a través de la parcela propietaria
        sql = """SELECT cc.* FROM cultivos_campana cc
                 JOIN parcelas p ON cc.parcela_id = p.id
                 WHERE p.user_id=?"""
        params = [uid]
        if parcela_id:
            sql += " AND cc.parcela_id=?"; params.append(parcela_id)
        if campana:
            sql += " AND cc.campana=?"; params.append(campana)
        rows = dicts(conn, sql, params)
        conn.close()
        return jsonify(rows)

    data = request.json or {}
    # Verificar que la parcela pertenece al usuario
    parcela_id = data.get('parcela_id')
    if not parcela_id:
        conn.close()
        return jsonify({"error": "Parcela es obligatoria"}), 400
    parcela = one(conn, "SELECT id, superficie_ha FROM parcelas WHERE id=? AND user_id=?", (parcela_id, uid))
    if not parcela:
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 404
    if not data.get('cultivo'):
        conn.close()
        return jsonify({"error": "El cultivo es obligatorio"}), 400
    if not data.get('cultivo_iacs_cod'):
        conn.close()
        return jsonify({"error": "El código IACS del cultivo es obligatorio para la interoperabilidad con SIEX (obligatorio desde ene 2027)"}), 400
    nueva_sup = _to_real(data.get('superficie_cultivada_ha')) or 0
    if parcela.get('superficie_ha') and nueva_sup > 0:
        row = one(conn, """SELECT COALESCE(SUM(superficie_cultivada_ha), 0) AS total
                           FROM cultivos_campana WHERE parcela_id=? AND campana=?""",
                  (parcela_id, data.get('campana')))
        ya_asignada = float(row['total']) if row else 0
        if ya_asignada + nueva_sup > parcela['superficie_ha'] + 0.01:
            conn.close()
            return jsonify({"error": f"La superficie asignada ({ya_asignada + nueva_sup:.2f} ha) supera las {parcela['superficie_ha']:.2f} ha de la parcela"}), 400
    c = conn.cursor()
    c.execute('''
        INSERT INTO cultivos_campana
            (parcela_id, campana, cultivo, cultivo_iacs_cod, variedad, fecha_siembra,
             fecha_recoleccion_prevista, superficie_cultivada_ha, notas,
             kg_sembrados, precio_kg_compra)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    ''', (parcela_id, data.get('campana'), data.get('cultivo'),
          data.get('cultivo_iacs_cod'),
          data.get('variedad'), data.get('fecha_siembra'),
          data.get('fecha_recoleccion_prevista'), _to_real(data.get('superficie_cultivada_ha')),
          data.get('notas'),
          _to_real(data.get('kg_sembrados')), _to_real(data.get('precio_kg_compra'))))
    new_id = c.lastrowid
    conn.commit(); conn.close()
    _recalcular_patrones(uid, 'cultivo_campana', parcela_id, data.get('fecha_siembra'))
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/cultivos-campana/<int:cid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_cultivo(cid):
    uid = get_uid()
    conn = get_db()
    # Verificar propiedad a través de la parcela (cultivos_campana no tiene user_id propio)
    owner = one(conn, """SELECT cc.id FROM cultivos_campana cc
                         JOIN parcelas p ON cc.parcela_id = p.id
                         WHERE cc.id=? AND p.user_id=?""", (cid, uid))
    if not owner:
        conn.close()
        return jsonify({"error": "No encontrado"}), 404
    if request.method == 'DELETE':
        conn.execute("DELETE FROM cultivos_campana WHERE id=?", (cid,))
        conn.commit(); conn.close()
        return jsonify({"status": "ok"})
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM cultivos_campana WHERE id=?", (cid,))
        conn.close()
        return jsonify(row or {})
    data = request.json or {}
    nueva_sup = _to_real(data.get('superficie_cultivada_ha')) or 0
    if nueva_sup > 0:
        current = one(conn, "SELECT parcela_id, campana FROM cultivos_campana WHERE id=?", (cid,))
        if current:
            parcela = one(conn, "SELECT superficie_ha FROM parcelas WHERE id=?", (current['parcela_id'],))
            if parcela and parcela.get('superficie_ha'):
                row = one(conn, """SELECT COALESCE(SUM(superficie_cultivada_ha), 0) AS total
                                   FROM cultivos_campana WHERE parcela_id=? AND campana=? AND id!=?""",
                          (current['parcela_id'], current['campana'], cid))
                resto = float(row['total']) if row else 0
                if resto + nueva_sup > parcela['superficie_ha'] + 0.01:
                    conn.close()
                    return jsonify({"error": f"La superficie asignada ({resto + nueva_sup:.2f} ha) supera las {parcela['superficie_ha']:.2f} ha de la parcela"}), 400
    fields = ['cultivo', 'cultivo_iacs_cod', 'variedad', 'fecha_siembra', 'fecha_recoleccion_prevista', 'superficie_cultivada_ha', 'notas', 'kg_sembrados', 'precio_kg_compra']
    real_fields = {'superficie_cultivada_ha', 'kg_sembrados', 'precio_kg_compra'}
    values = [_to_real(data.get(f)) if f in real_fields else data.get(f) for f in fields]
    sets = ', '.join(f"{f}=?" for f in fields)
    conn.execute(f"UPDATE cultivos_campana SET {sets} WHERE id=?", values + [cid])
    conn.commit(); conn.close()
    return jsonify({"status": "ok"})
