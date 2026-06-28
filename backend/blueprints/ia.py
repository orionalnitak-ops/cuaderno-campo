"""
blueprints/ia.py — Asistente IA estadístico (patrones pre-calculados, sin LLM)
"""
import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, dicts, one, USE_PG
from helpers import get_uid

bp = Blueprint('ia', __name__)

# ── Configuración ──────────────────────────────────────────────────────────────

CAMPOS_MODULO = {
    'tratamientos':    ['producto_comercial', 'num_registro_mapa', 'sustancia_activa',
                        'plaga_objetivo', 'dosis_valor', 'dosis_unidad', 'equipo_id', 'aplicador_id'],
    'fertilizacion':   ['tipo_fertilizante', 'producto', 'dosis_valor', 'dosis_unidad'],
    'riego':           ['tipo_riego'],
    'labores':         ['tipo_labor', 'maquinaria'],
    'cosecha':         ['destino', 'variedad'],
    'compras':         ['proveedor', 'cantidad_unidad'],
    'cultivo_campana': ['cultivo_iacs_cod', 'variedad'],
}

TABLA_MODULO = {
    'tratamientos':    'tratamientos',
    'fertilizacion':   'fertilizacion',
    'riego':           'riego',
    'labores':         'labores',
    'cosecha':         'cosecha',
    'compras':         'compras',
    'cultivo_campana': 'cultivos_campana',
}

FECHA_MODULO = {
    'tratamientos':    'fecha_aplicacion',
    'fertilizacion':   'fecha_aplicacion',
    'riego':           'fecha',
    'labores':         'fecha',
    'cosecha':         'fecha_inicio',
    'compras':         'fecha',
    'cultivo_campana': 'fecha_siembra',
}

TEMPORADA_MESES = {
    'primavera': (3, 4, 5),
    'verano':    (6, 7, 8),
    'otono':     (9, 10, 11),
    'invierno':  (12, 1, 2),
}

_HAS_DELETED_AT = {'tratamientos'}


# ── Funciones internas ─────────────────────────────────────────────────────────

def _temporada(fecha=None):
    if fecha is None:
        return _temporada(datetime.date.today())
    if isinstance(fecha, str):
        try:
            fecha = datetime.date.fromisoformat(str(fecha)[:10])
        except (ValueError, TypeError):
            return _temporada(datetime.date.today())
    mes = fecha.month
    if mes in (3, 4, 5):   return 'primavera'
    if mes in (6, 7, 8):   return 'verano'
    if mes in (9, 10, 11): return 'otono'
    return 'invierno'


def _mes_in_expr(fecha_col, meses):
    """Expresión SQL compatible SQLite y PostgreSQL para filtrar meses."""
    ph = ','.join(['?' for _ in meses])
    if USE_PG:
        return f"EXTRACT(MONTH FROM {fecha_col}::date)::int IN ({ph})"
    return f"CAST(strftime('%m', {fecha_col}) AS INTEGER) IN ({ph})"


def _recalcular_patrones(user_id, modulo, parcela_id, fecha_str):
    """Recalcula el valor más frecuente de cada campo para user+módulo+parcela+temporada.
    Llamar al final de cada POST exitoso en todos los módulos."""
    if modulo not in CAMPOS_MODULO:
        return
    campos    = CAMPOS_MODULO[modulo]
    tabla     = TABLA_MODULO[modulo]
    fecha_col = FECHA_MODULO[modulo]
    temporada = _temporada(fecha_str)
    meses     = TEMPORADA_MESES[temporada]
    mes_expr  = _mes_in_expr(fecha_col, meses)
    soft_del  = " AND deleted_at IS NULL" if modulo in _HAS_DELETED_AT else ""

    conn = get_db()
    try:
        for campo in campos:
            if modulo == 'cultivo_campana':
                # cultivos_campana no tiene user_id propio → JOIN con parcelas
                if not parcela_id:
                    continue
                sql = f"""
                    SELECT cc.{campo} AS val, COUNT(*) AS cnt, MAX(cc.{fecha_col}) AS ultima
                    FROM cultivos_campana cc
                    JOIN parcelas p ON cc.parcela_id = p.id
                    WHERE p.user_id=? AND cc.parcela_id=?
                      AND cc.{campo} IS NOT NULL AND cc.{campo} != ''
                      AND {mes_expr}
                    GROUP BY cc.{campo} ORDER BY cnt DESC, ultima DESC LIMIT 1
                """
                params = [user_id, parcela_id] + list(meses)
            elif parcela_id:
                sql = f"""
                    SELECT {campo} AS val, COUNT(*) AS cnt, MAX({fecha_col}) AS ultima
                    FROM {tabla}
                    WHERE user_id=? AND parcela_id=?
                      AND {campo} IS NOT NULL AND {campo} != ''
                      {soft_del} AND {mes_expr}
                    GROUP BY {campo} ORDER BY cnt DESC, ultima DESC LIMIT 1
                """
                params = [user_id, parcela_id] + list(meses)
            else:
                sql = f"""
                    SELECT {campo} AS val, COUNT(*) AS cnt, MAX({fecha_col}) AS ultima
                    FROM {tabla}
                    WHERE user_id=?
                      AND {campo} IS NOT NULL AND {campo} != ''
                      {soft_del} AND {mes_expr}
                    GROUP BY {campo} ORDER BY cnt DESC, ultima DESC LIMIT 1
                """
                params = [user_id] + list(meses)

            row = one(conn, sql, params)
            if not row or row.get('val') is None:
                continue

            # DELETE + INSERT (funciona en SQLite y PG; evita problema de NULL en UNIQUE)
            conn.execute("""
                DELETE FROM ia_patrones
                WHERE user_id=? AND modulo=? AND temporada=? AND campo=?
                  AND (parcela_id=? OR (parcela_id IS NULL AND ? IS NULL))
            """, (user_id, modulo, temporada, campo, parcela_id, parcela_id))
            conn.execute("""
                INSERT INTO ia_patrones
                    (user_id, modulo, parcela_id, temporada, campo, valor_sugerido, frecuencia, ultima_vez)
                VALUES (?,?,?,?,?,?,?,?)
            """, (user_id, modulo, parcela_id, temporada, campo,
                  str(row['val']), row['cnt'], row['ultima']))

        conn.commit()
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


def _generar_alertas(user_id):
    """Regenera alertas activas del usuario. Llamar en cada login exitoso."""
    conn = get_db()
    try:
        hoy     = datetime.date.today()
        expl    = one(conn, "SELECT campana_activa FROM explotacion WHERE user_id=?", (user_id,))
        campana = (expl or {}).get('campana_activa') or '2025/2026'

        parcelas = dicts(conn,
            "SELECT id, nombre_finca FROM parcelas WHERE user_id=? AND activa=1",
            (user_id,))

        for p in parcelas:
            pid    = p['id']
            nombre = p.get('nombre_finca') or f"Parcela {pid}"

            # 1. sin_registro_reciente (solo si ya hay historial)
            ultimo = one(conn, """
                SELECT MAX(fecha_aplicacion) AS ultima FROM tratamientos
                WHERE user_id=? AND parcela_id=? AND deleted_at IS NULL
            """, (user_id, pid))
            if ultimo and ultimo.get('ultima'):
                try:
                    dt   = datetime.date.fromisoformat(str(ultimo['ultima'])[:10])
                    dias = (hoy - dt).days
                    if dias > 30:
                        conn.execute(
                            "DELETE FROM ia_alertas WHERE user_id=? AND tipo=? AND parcela_id=?",
                            (user_id, 'sin_registro_reciente', pid))
                        conn.execute("""
                            INSERT INTO ia_alertas (user_id, tipo, parcela_id, modulo, mensaje)
                            VALUES (?,?,?,?,?)
                        """, (user_id, 'sin_registro_reciente', pid, 'tratamientos',
                              f"Llevas {dias} días sin registrar tratamientos en {nombre}"))
                except (ValueError, TypeError):
                    pass

            # 2. plazo_seguridad_proximo (vence en ≤7 días)
            proximos = dicts(conn, """
                SELECT producto_comercial, fecha_recoleccion_minima FROM tratamientos
                WHERE user_id=? AND parcela_id=? AND deleted_at IS NULL
                  AND fecha_recoleccion_minima IS NOT NULL AND fecha_recoleccion_minima != ''
            """, (user_id, pid))
            for t in proximos:
                try:
                    fm   = datetime.date.fromisoformat(str(t['fecha_recoleccion_minima'])[:10])
                    diff = (fm - hoy).days
                    if 0 <= diff <= 7:
                        conn.execute("""
                            DELETE FROM ia_alertas
                            WHERE user_id=? AND tipo=? AND parcela_id=? AND modulo=?
                        """, (user_id, 'plazo_seguridad_proximo', pid,
                              t.get('producto_comercial', '')))
                        conn.execute("""
                            INSERT INTO ia_alertas
                                (user_id, tipo, parcela_id, modulo, mensaje, expira_en)
                            VALUES (?,?,?,?,?,?)
                        """, (user_id, 'plazo_seguridad_proximo', pid,
                              t.get('producto_comercial', ''),
                              f"El plazo de seguridad de {t['producto_comercial']} en {nombre} vence el {t['fecha_recoleccion_minima']}",
                              t['fecha_recoleccion_minima']))
                except (ValueError, TypeError):
                    pass

            # 3. sin_cultivo_campana
            cultivo = one(conn, """
                SELECT cc.id FROM cultivos_campana cc
                JOIN parcelas p ON cc.parcela_id = p.id
                WHERE cc.parcela_id=? AND cc.campana=? AND p.user_id=?
            """, (pid, campana, user_id))
            if not cultivo:
                conn.execute(
                    "DELETE FROM ia_alertas WHERE user_id=? AND tipo=? AND parcela_id=?",
                    (user_id, 'sin_cultivo_campana', pid))
                conn.execute("""
                    INSERT INTO ia_alertas (user_id, tipo, parcela_id, mensaje)
                    VALUES (?,?,?,?)
                """, (user_id, 'sin_cultivo_campana', pid,
                      f"La parcela {nombre} no tiene cultivo de campaña asignado"))

        conn.commit()
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@bp.route('/api/ia/sugerencias', methods=['GET'])
@login_required
def get_sugerencias():
    uid        = get_uid()
    modulo     = request.args.get('modulo')
    parcela_id = request.args.get('parcela_id')

    if not modulo:
        return jsonify({"ok": False, "error": "modulo es obligatorio"}), 400

    temporada = _temporada()
    conn = get_db()

    if parcela_id:
        rows = dicts(conn, """
            SELECT id, campo, valor_sugerido FROM ia_patrones
            WHERE user_id=? AND modulo=? AND parcela_id=? AND temporada=?
        """, (uid, modulo, parcela_id, temporada))
    else:
        rows = dicts(conn, """
            SELECT id, campo, valor_sugerido FROM ia_patrones
            WHERE user_id=? AND modulo=? AND parcela_id IS NULL AND temporada=?
        """, (uid, modulo, temporada))

    conn.close()
    data = {r['campo']: {'patron_id': r['id'], 'valor': r['valor_sugerido']} for r in rows}
    return jsonify({"ok": True, "data": data})


@bp.route('/api/ia/alertas', methods=['GET'])
@login_required
def get_alertas():
    uid  = get_uid()
    conn = get_db()
    rows = dicts(conn, """
        SELECT id, tipo, parcela_id, modulo, mensaje, creada_en, expira_en
        FROM ia_alertas
        WHERE user_id=? AND leida=0
          AND (expira_en IS NULL OR expira_en > CURRENT_TIMESTAMP)
        ORDER BY
          CASE tipo
            WHEN 'plazo_seguridad_proximo' THEN 1
            WHEN 'sin_cultivo_campana'     THEN 2
            ELSE 3
          END, creada_en DESC
        LIMIT 3
    """, (uid,))
    conn.close()
    return jsonify({"ok": True, "data": rows})


@bp.route('/api/ia/alertas/<int:aid>/leer', methods=['POST'])
@login_required
def marcar_alerta_leida(aid):
    uid  = get_uid()
    conn = get_db()
    conn.execute("UPDATE ia_alertas SET leida=1 WHERE id=? AND user_id=?", (aid, uid))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


@bp.route('/api/ia/feedback', methods=['POST'])
@login_required
def post_feedback():
    uid  = get_uid()
    data = request.json or {}
    patron_id   = data.get('patron_id')
    accion      = data.get('accion')
    valor_final = data.get('valor_final')

    if not patron_id or accion not in ('aceptada', 'ignorada', 'modificada'):
        return jsonify({"ok": False, "error": "patron_id y accion válida son obligatorios"}), 400

    conn   = get_db()
    patron = one(conn, "SELECT id FROM ia_patrones WHERE id=? AND user_id=?", (patron_id, uid))
    if not patron:
        conn.close()
        return jsonify({"ok": False, "error": "Patrón no encontrado"}), 404

    conn.execute("""
        INSERT INTO ia_feedback (user_id, patron_id, accion, valor_final)
        VALUES (?,?,?,?)
    """, (uid, patron_id, accion, valor_final))
    conn.commit(); conn.close()
    return jsonify({"ok": True})
