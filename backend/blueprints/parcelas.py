"""
blueprints/parcelas.py — /api/parcelas/* y /api/cultivos-campana/*
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts, is_pac_eligible
from helpers import get_uid, _to_real

bp = Blueprint('parcelas', __name__)


@bp.route('/api/parcelas', methods=['GET', 'POST'])
@login_required
def manage_parcelas():
    uid = get_uid()
    conn = get_db()

    if request.method == 'GET':
        all_p = dicts(conn, "SELECT * FROM parcelas WHERE user_id=? AND activa=1 ORDER BY nombre_finca", (uid,))
        pac_only = request.args.get('pac_only', 'false').lower() == 'true'
        if pac_only:
            all_p = [p for p in all_p if is_pac_eligible(p.get('uso_sigpac', ''))]
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

    c = conn.cursor()
    c.execute('''
        INSERT INTO parcelas (
            user_id, comunidad, provincia_cod, provincia_nombre,
            municipio_cod, municipio_nombre, nombre_finca,
            poligono, parcela_num, recinto, superficie_ha, uso_sigpac,
            sistema_explotacion, masa_agua_cercana, notas
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        uid, data.get('comunidad'), data.get('provincia_cod'), data.get('provincia_nombre'),
        data.get('municipio_cod'), data.get('municipio_nombre'), data.get('nombre_finca'),
        data.get('poligono'), data.get('parcela_num'), data.get('recinto'),
        sup, data.get('uso_sigpac'),
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

    def _field_val(f):
        v = data.get(f)
        if f == 'superficie_ha': return sup_put
        if f == 'masa_agua_cercana': return 1 if v else 0
        return v

    fields = ['comunidad', 'provincia_cod', 'provincia_nombre', 'municipio_cod', 'municipio_nombre',
              'nombre_finca', 'poligono', 'parcela_num', 'recinto', 'superficie_ha', 'uso_sigpac',
              'sistema_explotacion', 'masa_agua_cercana', 'notas']
    sets = ', '.join(f"{f}=?" for f in fields)
    vals = [_field_val(f) for f in fields] + [pid, uid]
    conn.execute(f"UPDATE parcelas SET {sets} WHERE id=? AND user_id=?", vals)
    conn.commit(); conn.close()
    return jsonify({"status": "ok"})


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
    owner = one(conn, "SELECT id FROM parcelas WHERE id=? AND user_id=?", (parcela_id, uid))
    if not owner:
        conn.close()
        return jsonify({"error": "Parcela no encontrada"}), 404
    if not data.get('cultivo'):
        conn.close()
        return jsonify({"error": "El cultivo es obligatorio"}), 400
    if not data.get('cultivo_iacs_cod'):
        conn.close()
        return jsonify({"error": "El código IACS del cultivo es obligatorio para la interoperabilidad con SIEX (obligatorio desde ene 2027)"}), 400
    c = conn.cursor()
    try:
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
    except Exception:
        c.execute('''
            UPDATE cultivos_campana SET cultivo=?, cultivo_iacs_cod=?, variedad=?,
                fecha_siembra=?, fecha_recoleccion_prevista=?,
                superficie_cultivada_ha=?, notas=?,
                kg_sembrados=?, precio_kg_compra=?, updated_at=CURRENT_TIMESTAMP
            WHERE parcela_id=? AND campana=?
        ''', (data.get('cultivo'), data.get('cultivo_iacs_cod'),
              data.get('variedad'), data.get('fecha_siembra'),
              data.get('fecha_recoleccion_prevista'), _to_real(data.get('superficie_cultivada_ha')),
              data.get('notas'),
              _to_real(data.get('kg_sembrados')), _to_real(data.get('precio_kg_compra')),
              parcela_id, data.get('campana')))
        new_id = None
    conn.commit(); conn.close()
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
    fields = ['cultivo', 'cultivo_iacs_cod', 'variedad', 'fecha_siembra', 'fecha_recoleccion_prevista', 'superficie_cultivada_ha', 'notas', 'kg_sembrados', 'precio_kg_compra']
    real_fields = {'superficie_cultivada_ha', 'kg_sembrados', 'precio_kg_compra'}
    values = [_to_real(data.get(f)) if f in real_fields else data.get(f) for f in fields]
    sets = ', '.join(f"{f}=?" for f in fields)
    conn.execute(f"UPDATE cultivos_campana SET {sets} WHERE id=?", values + [cid])
    conn.commit(); conn.close()
    return jsonify({"status": "ok"})
