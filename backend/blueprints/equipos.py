"""
blueprints/equipos.py — /api/equipos/*, /api/aplicadores/*

Aislamiento por explotación (feature 013): cada explotación es un cuaderno
independiente, así que los equipos y los aplicadores son de UNA finca. Toda
consulta filtra por `user_id` Y `explotacion_id`. El primero separa clientes
distintos; el segundo, cuadernos del mismo cliente.

El filtro va también en PUT y DELETE, no solo en los listados: sin él, un id de
la otra finca se seguiría pudiendo editar o borrar.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid, get_active_explotacion_id

bp = Blueprint('equipos', __name__)

SIN_EXPLOTACION = "No tienes ninguna explotación creada"


def _coerce_propio(raw):
    """Normaliza `propio` a True/False/None antes de guardarlo.

    Sin esto, un cliente que mande un valor que no sea exactamente `False`
    (p. ej. un string suelto) se cuela en una columna INTEGER como texto en
    vez de 0/1/NULL — SQLite no lo rechaza, pero deja el dato sucio. `None`
    significa "sin especificar" (se trata como propio al mostrarlo).
    """
    if raw is None:
        return None
    return bool(raw)


@bp.route('/api/equipos', methods=['GET', 'POST'])
@login_required
def manage_equipos():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM equipos WHERE user_id=? AND explotacion_id=?",
                     (uid, exp_id))
        conn.close(); return jsonify(rows)
    if not exp_id:
        # Sin explotación el INSERT dejaría explotacion_id NULL y el equipo no
        # aparecería en ningún listado: mejor fallar que crear un registro ciego.
        conn.close(); return jsonify({"error": SIN_EXPLOTACION}), 400
    data = request.json or {}
    # feature 022 (bloque 5/8 SIEX): `nif_propietario` solo tiene sentido si el
    # equipo NO es propio — limpiarlo aquí evita que un NIF quede colgado en un
    # equipo marcado como propio (mismo bug que ya se corrigió en cosecha con
    # los datos de cliente al desmarcar "venta comercializada").
    propio = _coerce_propio(data.get('propio'))
    nif_propietario = data.get('nif_propietario') if propio is False else None
    c = conn.cursor()
    c.execute('''INSERT INTO equipos (user_id, explotacion_id, descripcion, tipo, marca, modelo,
                     num_registro_roma, fecha_iteaf, notas, propio, nif_propietario)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
              (uid, exp_id, data.get('descripcion'), data.get('tipo'), data.get('marca'),
               data.get('modelo'), data.get('num_registro_roma'), data.get('fecha_iteaf'), data.get('notas'),
               propio, nif_propietario))
    conn.commit(); new_id = c.lastrowid; conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/equipos/<int:eid>', methods=['PUT', 'DELETE'])
@login_required
def manage_equipo(eid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'DELETE':
        conn.execute("DELETE FROM equipos WHERE id=? AND user_id=? AND explotacion_id=?",
                     (eid, uid, exp_id))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    data = request.json or {}
    data['propio'] = _coerce_propio(data.get('propio'))
    if data['propio'] is not False:
        data['nif_propietario'] = None
    fields = ['descripcion', 'tipo', 'marca', 'modelo', 'num_registro_roma', 'fecha_iteaf', 'notas',
              'propio', 'nif_propietario']
    sets = ', '.join(f"{f}=?" for f in fields)
    conn.execute(f"UPDATE equipos SET {sets} WHERE id=? AND user_id=? AND explotacion_id=?",
                 [data.get(f) for f in fields] + [eid, uid, exp_id])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})


@bp.route('/api/aplicadores', methods=['GET', 'POST'])
@login_required
def manage_aplicadores():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM aplicadores WHERE user_id=? AND explotacion_id=? AND activo=1",
                     (uid, exp_id))
        conn.close(); return jsonify(rows)
    if not exp_id:
        conn.close(); return jsonify({"error": SIN_EXPLOTACION}), 400
    data = request.json or {}
    c = conn.cursor()
    c.execute("INSERT INTO aplicadores (user_id, explotacion_id, nombre, nif, num_ropo) VALUES (?,?,?,?,?)",
              (uid, exp_id, data.get('nombre'), data.get('nif'), data.get('num_ropo')))
    conn.commit(); new_id = c.lastrowid; conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/aplicadores/<int:aid>', methods=['PUT', 'DELETE'])
@login_required
def manage_aplicador(aid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'DELETE':
        conn.execute("UPDATE aplicadores SET activo=0 WHERE id=? AND user_id=? AND explotacion_id=?",
                     (aid, uid, exp_id))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    data = request.json or {}
    conn.execute("UPDATE aplicadores SET nombre=?, nif=?, num_ropo=? WHERE id=? AND user_id=? AND explotacion_id=?",
                 (data.get('nombre'), data.get('nif'), data.get('num_ropo'), aid, uid, exp_id))
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
