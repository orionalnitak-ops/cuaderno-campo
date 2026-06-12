"""
blueprints/equipos.py — /api/equipos/*, /api/aplicadores/*
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid

bp = Blueprint('equipos', __name__)


@bp.route('/api/equipos', methods=['GET', 'POST'])
@login_required
def manage_equipos():
    uid = get_uid()
    conn = get_db()
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM equipos WHERE user_id=?", (uid,))
        conn.close(); return jsonify(rows)
    data = request.json or {}
    c = conn.cursor()
    c.execute('''INSERT INTO equipos (user_id, descripcion, tipo, marca, modelo, num_registro_roma, fecha_iteaf, notas)
                 VALUES (?,?,?,?,?,?,?,?)''',
              (uid, data.get('descripcion'), data.get('tipo'), data.get('marca'),
               data.get('modelo'), data.get('num_registro_roma'), data.get('fecha_iteaf'), data.get('notas')))
    conn.commit(); new_id = c.lastrowid; conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/equipos/<int:eid>', methods=['PUT', 'DELETE'])
@login_required
def manage_equipo(eid):
    uid = get_uid()
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM equipos WHERE id=? AND user_id=?", (eid, uid))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    data = request.json or {}
    fields = ['descripcion', 'tipo', 'marca', 'modelo', 'num_registro_roma', 'fecha_iteaf', 'notas']
    sets = ', '.join(f"{f}=?" for f in fields)
    conn.execute(f"UPDATE equipos SET {sets} WHERE id=? AND user_id=?",
                 [data.get(f) for f in fields] + [eid, uid])
    conn.commit(); conn.close(); return jsonify({"status": "ok"})


@bp.route('/api/aplicadores', methods=['GET', 'POST'])
@login_required
def manage_aplicadores():
    uid = get_uid()
    conn = get_db()
    if request.method == 'GET':
        rows = dicts(conn, "SELECT * FROM aplicadores WHERE user_id=? AND activo=1", (uid,))
        conn.close(); return jsonify(rows)
    data = request.json or {}
    c = conn.cursor()
    c.execute("INSERT INTO aplicadores (user_id, nombre, nif, num_ropo) VALUES (?,?,?,?)",
              (uid, data.get('nombre'), data.get('nif'), data.get('num_ropo')))
    conn.commit(); new_id = c.lastrowid; conn.close()
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/aplicadores/<int:aid>', methods=['PUT', 'DELETE'])
@login_required
def manage_aplicador(aid):
    uid = get_uid()
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("UPDATE aplicadores SET activo=0 WHERE id=? AND user_id=?", (aid, uid))
        conn.commit(); conn.close(); return jsonify({"status": "ok"})
    data = request.json or {}
    conn.execute("UPDATE aplicadores SET nombre=?, nif=?, num_ropo=? WHERE id=? AND user_id=?",
                 (data.get('nombre'), data.get('nif'), data.get('num_ropo'), aid, uid))
    conn.commit(); conn.close(); return jsonify({"status": "ok"})
