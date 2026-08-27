"""
blueprints/parcelas.py — /api/parcelas/* y /api/cultivos-campana/*
"""
import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import login_required
from extensions import limiter
from db import get_db, one, dicts, is_pac_eligible
from helpers import (get_uid, _to_real, get_active_explotacion_id, estado_sigpac,
                     validar_alta_multirecinto, heredar_cultivos_lenosos,
                     campana_activa, sugerencias_lenosos, declarar_cultivos_lote,
                     repartir_por_superficie, cod_siex_de_cultivo)
from blueprints.fertilizacion import _parcelas_uhc
from blueprints.ia import _recalcular_patrones
from blueprints.sigpac import superficie_sigpac_parcela, referencia_catastral_parcela

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


@bp.route('/api/parcelas/alta-multirecinto', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def alta_multirecinto():
    """Crea una parcela por recinto y las UHC aceptadas, todo o nada (commit único)."""
    data = request.json or {}
    norm, err = validar_alta_multirecinto(data)
    if err:
        return jsonify({"ok": False, "error": err}), 400

    uid = get_uid()
    conn = get_db()
    try:
        try:
            exp_id = get_active_explotacion_id(conn)
        except Exception:
            return jsonify({"ok": False, "error": "No tienes una explotación activa"}), 400

        # Duplicados: si ya existe alguno de los recintos, no se crea nada.
        for r in norm['recintos']:
            ya = one(conn, """SELECT id FROM parcelas
                              WHERE user_id=? AND explotacion_id=? AND poligono=?
                                AND parcela_num=? AND recinto=? AND activa=1""",
                     (uid, exp_id, norm['poligono'], norm['parcela_num'], str(r['num'])))
            if ya:
                return jsonify({"ok": False,
                                "error": f"Ya tienes registrado el trozo {r['num']} de esa parcela"}), 400

        ref_cat = referencia_catastral_parcela(
            norm['provincia_cod'], norm['municipio_cod'], norm['poligono'], norm['parcela_num'],
            recinto=str(norm['recintos'][0]['num'])
        )

        c = conn.cursor()
        ids_por_num = {}
        for r in norm['recintos']:
            c.execute('''
                INSERT INTO parcelas (
                    user_id, explotacion_id, comunidad, provincia_cod, provincia_nombre,
                    municipio_cod, municipio_nombre, nombre_finca,
                    poligono, parcela_num, recinto, superficie_ha, uso_sigpac, referencia_cat,
                    sistema_explotacion, masa_agua_cercana, notas
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                uid, exp_id, norm['comunidad'], norm['provincia_cod'], norm['provincia_nombre'],
                norm['municipio_cod'], norm['municipio_nombre'],
                f"{norm['nombre_base']} — R{r['num']}",
                norm['poligono'], norm['parcela_num'], str(r['num']),
                r['superficie_ha'], r['uso_sigpac'], ref_cat,
                norm['sistema_explotacion'], 0, '',
            ))
            ids_por_num[r['num']] = c.lastrowid

        for u in norm['uhcs']:
            c.execute(
                "INSERT INTO unidades_homogeneas (user_id, explotacion_id, nombre, cultivo, campana, notas)"
                " VALUES (?,?,?,?,?,?)",
                (uid, exp_id, u['nombre'], u['cultivo'], norm['campana'], '')
            )
            uhc_id = c.lastrowid
            for num in u['recintos']:
                c.execute(
                    "INSERT INTO uhc_parcelas (uhc_id, parcela_id) VALUES (?,?)",
                    (uhc_id, ids_por_num[num])
                )

        conn.commit()
        return jsonify({"ok": True, "data": {"parcelas": len(norm['recintos']),
                                             "uhcs": len(norm['uhcs'])}}), 201
    finally:
        conn.close()


def _declarar_cultivo_grupo(conn, uid, exp_id, data):
    """Declara el cultivo de campaña en todas las parcelas de un grupo UHC.

    Devuelve {creadas, saltadas, rechazadas, motivos} o {'error': ...} si el grupo
    entero no es utilizable. No hace commit: lo hace la ruta.

    Dos reglas heredadas de la feature 015, y por los mismos motivos:

    - **Nunca pisa una declaración existente.** Si la parcela ya tiene ese cultivo
      declarado en la campaña, se salta y se cuenta. Redeclarar duplicaría filas en
      un documento legal.
    - **Un rechazo no tumba el grupo.** Si a una parcela no le cabe la superficie,
      se rechaza ESA y se sigue con las demás. Al revés que en cosecha: aquí no hay
      riesgo legal en declarar de menos, y bloquear las 20 parcelas buenas por una
      mal medida no ayuda a nadie. El motivo se devuelve para poder explicarlo.
    """
    res = {'creadas': 0, 'saltadas': 0, 'rechazadas': 0, 'motivos': []}

    cod = str(data.get('cultivo_iacs_cod') or '').strip()
    if not data.get('cultivo'):
        return {'error': "El cultivo es obligatorio"}
    if not cod:
        return {'error': "El código IACS del cultivo es obligatorio para la interoperabilidad"
                         " con SIEX (obligatorio desde ene 2027)"}

    parcelas = _parcelas_uhc(conn, data['uhc_id'], uid, exp_id)
    if not parcelas:
        return {'error': "El grupo UHC no existe o no tiene parcelas asignadas"}

    campana = data.get('campana')
    reparto = repartir_por_superficie(data.get('kg_sembrados'), parcelas)

    def _rechaza(motivo):
        res['rechazadas'] += 1
        if motivo not in res['motivos']:
            res['motivos'].append(motivo)

    c = conn.cursor()
    for p in parcelas:
        pid = p['id']
        if one(conn, "SELECT id FROM cultivos_campana WHERE parcela_id=? AND campana=?"
                     " AND cultivo_iacs_cod=?", (pid, campana, cod)):
            res['saltadas'] += 1
            continue

        # La superficie de la fila es la de la parcela: ya la sabemos, no se
        # estima. Pero la parcela puede tener OTRO cultivo declarado que ya ocupe
        # parte de ella (una parcela mixta viñedo-olivar, p. ej.), así que se
        # declara solo lo que queda libre. Es la misma cuenta que ya hace el POST
        # de una parcela suelta, aplicada por parcela del grupo.
        sup = _to_real(p.get('superficie_ha')) or 0
        if sup > 0:
            fila = one(conn, "SELECT COALESCE(SUM(superficie_cultivada_ha), 0) AS total"
                             " FROM cultivos_campana WHERE parcela_id=? AND campana=?",
                       (pid, campana))
            ya = float(fila['total']) if fila else 0
            libre = round(sup - ya, 4)
            if libre <= 0.01:
                _rechaza('Alguna parcela ya tiene toda su superficie declarada con otro cultivo')
                continue
            sup = libre

        c.execute('''
            INSERT INTO cultivos_campana
                (parcela_id, explotacion_id, campana, cultivo, cultivo_iacs_cod, variedad,
                 fecha_siembra, fecha_recoleccion_prevista, superficie_cultivada_ha, notas,
                 kg_sembrados, precio_kg_compra, variedad_cod_siex)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (pid, exp_id, campana, data.get('cultivo'), cod,
              data.get('variedad'), data.get('fecha_siembra'),
              data.get('fecha_recoleccion_prevista'), sup, data.get('notas'),
              reparto.get(pid), _to_real(data.get('precio_kg_compra')),
              data.get('variedad_cod_siex')))
        res['creadas'] += 1
        res.setdefault('parcela_ids', []).append(pid)

    return res


@bp.route('/api/catalogos/variedades', methods=['GET'])
@login_required
def buscar_variedades_siex():
    """Sugerencias de variedad del catálogo SIEX para un cultivo IACS.

    Solo autocompleta: no valida ni bloquea. Si el cultivo no tiene cruce
    SIEX conocido (`cod_siex_de_cultivo` devuelve None) se responde con una
    lista vacía, y el campo `variedad` del formulario sigue siendo texto
    libre como siempre — ver spec/features/018-siex-cultivo.
    """
    cod_siex = cod_siex_de_cultivo(request.args.get('cultivo_iacs_cod'))
    if not cod_siex:
        return jsonify({"ok": True, "data": []})
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({"ok": True, "data": []})
    conn = get_db()
    rows = dicts(conn, """SELECT cod_variedad, nombre FROM ref_variedades_siex
                          WHERE cod_cultivo_siex=? AND nombre LIKE ?
                          ORDER BY nombre LIMIT 20""",
                 (cod_siex, q.upper() + '%'))
    conn.close()
    return jsonify({"ok": True, "data": rows})


@bp.route('/api/cultivos-campana', methods=['GET', 'POST'])
@login_required
def manage_cultivos():
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    if request.method == 'GET':
        parcela_id = request.args.get('parcela_id')
        campana = request.args.get('campana')
        # Herencia de leñosos (feature 014): el olivar o el viñedo no cambian de
        # campaña en campaña, así que se arrastran solos y el agricultor no tiene
        # que redeclararlos. Ver spec/features/014-cultivos-lenosos-herencia.
        #
        # Se hereda SIEMPRE en la campaña activa de la explotación, y NUNCA en la
        # que venga en `?campana=`. El Security Review del PR #48 avisó de que
        # esto es una escritura en un GET, y por tanto disparable desde fuera:
        # basta un `<img src=".../api/cultivos-campana?campana=3000/3001">` en
        # una página cualquiera para que el navegador de un usuario logueado la
        # ejecute. Si el parámetro mandara, eso crearía filas heredadas en una
        # campaña inventada — datos falsos en un documento legal. Ignorándolo, lo
        # peor que puede provocar un tercero es que se herede en la campaña en la
        # que se habría heredado igualmente al abrir la app.
        if heredar_cultivos_lenosos(conn, uid, campana_activa(conn, uid, exp_id), exp_id):
            conn.commit()
        # Filtrar siempre por user_id a través de la parcela propietaria, y por
        # la explotación activa (feature 013).
        sql = """SELECT cc.* FROM cultivos_campana cc
                 JOIN parcelas p ON cc.parcela_id = p.id
                 WHERE p.user_id=? AND cc.explotacion_id=?"""
        params = [uid, exp_id]
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
    if not parcela_id and not data.get('uhc_id'):
        conn.close()
        return jsonify({"error": "Parcela es obligatoria"}), 400

    # ── Declaración por grupo UHC (feature 016) ───────────────────────────────
    # Una UHC ya es, por definición, un conjunto de parcelas del mismo cultivo:
    # declararlo de una vez es el caso natural. La superficie cultivada de cada
    # fila es la de SU parcela, y `kg_sembrados` (cantidad absoluta) se reparte.
    if data.get('uhc_id'):
        resultado = _declarar_cultivo_grupo(conn, uid, exp_id, data)
        if resultado.get('error'):
            conn.close()
            return jsonify({"error": resultado['error']}), 400
        conn.commit(); conn.close()
        for pid in resultado.pop('parcela_ids', []):
            _recalcular_patrones(uid, 'cultivo_campana', pid, data.get('fecha_siembra'), exp_id)
        return jsonify({"status": "ok", **resultado}), 201
    parcela = one(conn, "SELECT id, superficie_ha FROM parcelas"
                        " WHERE id=? AND user_id=? AND explotacion_id=?",
                  (parcela_id, uid, exp_id))
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
            (parcela_id, explotacion_id, campana, cultivo, cultivo_iacs_cod, variedad,
             fecha_siembra, fecha_recoleccion_prevista, superficie_cultivada_ha, notas,
             kg_sembrados, precio_kg_compra, variedad_cod_siex)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (parcela_id, exp_id, data.get('campana'), data.get('cultivo'),
          data.get('cultivo_iacs_cod'),
          data.get('variedad'), data.get('fecha_siembra'),
          data.get('fecha_recoleccion_prevista'), _to_real(data.get('superficie_cultivada_ha')),
          data.get('notas'),
          _to_real(data.get('kg_sembrados')), _to_real(data.get('precio_kg_compra')),
          data.get('variedad_cod_siex')))
    new_id = c.lastrowid
    conn.commit(); conn.close()
    _recalcular_patrones(uid, 'cultivo_campana', parcela_id, data.get('fecha_siembra'), exp_id)
    return jsonify({"status": "ok", "id": new_id}), 201


@bp.route('/api/cultivos-campana/sugerencias', methods=['GET'])
@login_required
def sugerencias_cultivos():
    """Qué parcelas de leñoso están sin declarar y qué se le propone (feature 015).

    Solo lectura: aquí no se escribe nada. Decide el agricultor.
    """
    conn = get_db()
    try:
        uid = get_uid()
        data = sugerencias_lenosos(conn, uid, get_active_explotacion_id(conn))
        return jsonify({"ok": True, **data})
    finally:
        conn.close()


@bp.route('/api/cultivos-campana/declarar-lote', methods=['POST'])
@login_required
def declarar_lote_cultivos():
    """Declara de una vez los cultivos que el agricultor ha confirmado (feature 015).

    POST y no GET: esto escribe. La lección de la 014 fue justo esa — que el
    efecto sea idempotente no convierte una escritura en un GET seguro.

    Ni la campaña ni el nombre del cultivo se aceptan del cliente: la campaña sale
    de la explotación y el nombre del catálogo IACS. Del cliente solo viene QUÉ
    parcela y QUÉ código, y las dos cosas se validan contra la BD.
    """
    data = request.json or {}
    declaraciones = data.get('declaraciones')
    if not isinstance(declaraciones, list) or not declaraciones:
        return jsonify({"ok": False, "error": "No hay nada que declarar"}), 400
    if len(declaraciones) > 500:
        # Tope de cordura: la explotación más grande que manejamos anda por 120
        # parcelas. Un lote de miles solo puede ser un error o un abuso.
        return jsonify({"ok": False, "error": "Demasiadas declaraciones de una vez"}), 400

    conn = get_db()
    try:
        uid = get_uid()
        exp_id = get_active_explotacion_id(conn)
        res = declarar_cultivos_lote(conn, uid, exp_id, declaraciones)
        if res['creadas']:
            conn.commit()
        return jsonify({"ok": True, **res})
    finally:
        conn.close()


@bp.route('/api/cultivos-campana/<int:cid>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_cultivo(cid):
    uid = get_uid()
    conn = get_db()
    exp_id = get_active_explotacion_id(conn)
    # Verificar propiedad a través de la parcela (cultivos_campana no tiene
    # user_id propio) Y que sea de la explotación activa: si no, con el id a
    # mano se edita o se borra el cultivo de la otra finca (feature 013).
    # Este guardián protege las consultas por `id` que vienen después.
    owner = one(conn, """SELECT cc.id FROM cultivos_campana cc
                         JOIN parcelas p ON cc.parcela_id = p.id
                         WHERE cc.id=? AND p.user_id=? AND cc.explotacion_id=?""",
                (cid, uid, exp_id))
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
    fields = ['cultivo', 'cultivo_iacs_cod', 'variedad', 'fecha_siembra', 'fecha_recoleccion_prevista', 'superficie_cultivada_ha', 'notas', 'kg_sembrados', 'precio_kg_compra', 'variedad_cod_siex']
    real_fields = {'superficie_cultivada_ha', 'kg_sembrados', 'precio_kg_compra'}
    values = [_to_real(data.get(f)) if f in real_fields else data.get(f) for f in fields]
    sets = ', '.join(f"{f}=?" for f in fields)
    conn.execute(f"UPDATE cultivos_campana SET {sets} WHERE id=?", values + [cid])
    conn.commit(); conn.close()
    return jsonify({"status": "ok"})
