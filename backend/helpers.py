"""
helpers.py — Decoradores y funciones de utilidad compartidas entre blueprints.
"""
import re
from functools import wraps
from flask import jsonify, session
from flask_login import current_user
from db import get_db, one, dicts


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({"error": "No autorizado"}), 403
        return f(*args, **kwargs)
    return decorated


def get_uid():
    """Devuelve el user_id efectivo (admite impersonación del admin)."""
    if current_user.is_authenticated and current_user.role == 'admin':
        imp = session.get('impersonate_id')
        if imp:
            return imp
    return current_user.id


def requires_active_plan(f):
    """Decorador para rutas GET que también requieren suscripción activa (ej. exportaciones)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.plan_is_active():
            return jsonify({"error": "subscription_required", "plan": current_user.plan_label()}), 403
        return f(*args, **kwargs)
    return decorated


def _to_real(v):
    """Parsea float desde input de usuario, aceptando coma decimal (locale español)."""
    if v is None or v == '':
        return None
    try:
        return float(str(v).replace(',', '.'))
    except (ValueError, TypeError):
        return None


def resolve_default_explotacion(conn, uid):
    """Devuelve el id de la explotación por defecto del usuario (menor orden/id), o None."""
    row = one(conn, "SELECT id FROM explotacion WHERE user_id=? ORDER BY orden, id LIMIT 1", (uid,))
    return row['id'] if row else None


def explotaciones_escribibles(conn, uid, limit):
    """Ids de las explotaciones en las que el usuario puede ANOTAR, o None si
    no tiene tope (admin, premium, súper usuarios).

    Leer no se limita nunca: esto no esconde ni una parcela, solo decide dónde
    se puede escribir. Son las `limit` primeras por `orden, id`, y el propio
    agricultor elige cuál va primera marcándola como principal
    (`POST /api/explotaciones/<id>/principal`, que reescribe `orden`).

    Se ordena igual que el selector de la app, para que lo que ve coincida con
    lo que puede hacer.
    """
    if limit is None:
        return None
    rows = dicts(conn, "SELECT id FROM explotacion WHERE user_id=? ORDER BY orden, id", (uid,))
    return {r['id'] for r in rows[:limit]}


def get_active_explotacion_id(conn=None):
    """Devuelve el id de la explotación activa para el usuario efectivo.

    - Lee `session['active_explotacion_id']` y valida que pertenece al usuario.
    - Si no hay selección válida (o el usuario es mono-explotación), devuelve la
      explotación por defecto del usuario.
    - Devuelve None si el usuario aún no tiene ninguna explotación.
    """
    uid = get_uid()
    own_conn = conn is None
    if own_conn:
        conn = get_db()
    try:
        sel = session.get('active_explotacion_id')
        if sel:
            valid = one(conn, "SELECT id FROM explotacion WHERE id=? AND user_id=?", (sel, uid))
            if valid:
                return valid['id']
        return resolve_default_explotacion(conn, uid)
    finally:
        if own_conn:
            conn.close()


def estado_sigpac(parcela):
    """Deriva el estado del badge SIGPAC de una parcela (dict). Función pura, sin I/O.

    Devuelve (estado, diferencia_pct):
      - 'sin_verificar'  -> nunca se verificó (diferencia None)
      - 'no_encontrada'  -> verificada pero SIGPAC no dio superficie (diferencia None)
      - 'verde'          -> |declarada - sigpac| / sigpac <= 5%
      - 'ambar'          -> diferencia > 5% (o sin superficie declarada)
    diferencia_pct = (declarada - sigpac) / sigpac * 100, redondeada a 1 decimal.
    """
    if not parcela.get('sigpac_verificado_en'):
        return 'sin_verificar', None
    sig = parcela.get('sigpac_superficie_ha')
    if sig is None:
        return 'no_encontrada', None
    try:
        sig = float(sig)
    except (TypeError, ValueError):
        return 'no_encontrada', None
    if sig <= 0:
        return 'no_encontrada', None
    decl = parcela.get('superficie_ha')
    if decl in (None, ''):
        return 'ambar', None
    try:
        decl = float(decl)
    except (TypeError, ValueError):
        return 'ambar', None
    ratio = abs(decl - sig) / sig
    diff_pct = round((decl - sig) / sig * 100, 1)
    return ('verde' if ratio <= 0.05 else 'ambar'), diff_pct


_CAMPANA_RE = re.compile(r'^\d{4}/\d{4}$')
_POL_PAR_RE = re.compile(r'^\d{1,5}$')
_SISTEMAS_EXPLOTACION = frozenset({'Invernadero', 'Mixto', 'Regadío', 'Secano'})
_MAX_LEN_NOMBRE = 120


def validar_alta_multirecinto(data):
    """Valida y normaliza el payload de POST /api/parcelas/alta-multirecinto.

    Devuelve (norm, None) si es válido o (None, "mensaje legible") si no.
    norm: {nombre_base, campana, poligono, parcela_num, comunidad, provincia_cod,
           provincia_nombre, municipio_cod, municipio_nombre, sistema_explotacion,
           recintos:[{num:int, uso_sigpac:str, superficie_ha:float|None}],
           uhcs:[{nombre:str, cultivo:str, recintos:[int]}]}
    """
    data = data or {}
    nombre_base = (data.get('nombre_base') or '').strip()[:_MAX_LEN_NOMBRE]
    if not nombre_base:
        return None, "El nombre de la finca es obligatorio"

    campana = str(data.get('campana') or '2025/2026')
    if not _CAMPANA_RE.match(campana):
        return None, "La campaña debe tener formato YYYY/YYYY (ej: 2025/2026)"

    poligono = str(data.get('poligono') or '').strip()
    parcela_num = str(data.get('parcela_num') or '').strip()
    if not poligono or not parcela_num:
        return None, "Faltan el polígono y la parcela SIGPAC"
    if not _POL_PAR_RE.match(poligono) or not _POL_PAR_RE.match(parcela_num):
        return None, "El polígono y la parcela deben ser números"

    sistema = str(data.get('sistema_explotacion') or 'Secano').strip()
    if sistema not in _SISTEMAS_EXPLOTACION:
        sistema = 'Secano'

    raw = data.get('recintos')
    if not isinstance(raw, list) or not raw:
        return None, "Hacen falta los trozos (recintos) que se van a crear"

    recintos, vistos = [], set()
    for r in raw:
        r = r or {}
        try:
            num = int(r.get('num'))
        except (TypeError, ValueError):
            return None, "Número de trozo (recinto) inválido"
        if num <= 0:
            return None, "Número de trozo (recinto) inválido"
        if num in vistos:
            return None, "Hay trozos (recintos) repetidos"
        vistos.add(num)
        sup = r.get('superficie_ha')
        if sup is None or sup == '':
            sup = None
        else:
            try:
                sup = float(str(sup).replace(',', '.'))
            except (TypeError, ValueError):
                return None, f"Superficie inválida en el trozo {num}"
            if sup <= 0:
                return None, f"La superficie del trozo {num} debe ser mayor que cero"
        recintos.append({'num': num, 'uso_sigpac': (r.get('uso_sigpac') or '').strip(),
                         'superficie_ha': sup})

    uhcs = []
    for u in (data.get('uhcs') or []):
        u = u or {}
        nombre = (u.get('nombre') or '').strip()
        if not nombre:
            return None, "El nombre del grupo es obligatorio"
        try:
            nums = sorted({int(n) for n in (u.get('recintos') or [])})
        except (TypeError, ValueError):
            return None, f"El grupo '{nombre}' tiene trozos inválidos"
        if len(nums) < 2:
            return None, f"El grupo '{nombre}' necesita al menos 2 trozos"
        if not set(nums) <= vistos:
            return None, f"El grupo '{nombre}' incluye trozos que no se van a crear"
        uhcs.append({'nombre': nombre, 'cultivo': (u.get('cultivo') or '').strip(),
                     'recintos': nums})

    return {'nombre_base': nombre_base, 'campana': campana,
            'poligono': poligono, 'parcela_num': parcela_num,
            'comunidad': str(data.get('comunidad') or '')[:_MAX_LEN_NOMBRE],
            'provincia_cod': str(data.get('provincia_cod') or '')[:5],
            'provincia_nombre': str(data.get('provincia_nombre') or '')[:_MAX_LEN_NOMBRE],
            'municipio_cod': str(data.get('municipio_cod') or '')[:5],
            'municipio_nombre': str(data.get('municipio_nombre') or '')[:_MAX_LEN_NOMBRE],
            'sistema_explotacion': sistema,
            'recintos': recintos, 'uhcs': uhcs}, None


# ── Cultivos leñosos: herencia entre campañas (feature 014) ───────────────────
# Códigos IACS del Anexo VII FEGA correspondientes al grupo 'Leñosos' del
# catálogo CULTIVOS_IACS (frontend/screens_parcelas.jsx). Se duplica aquí a
# propósito: el backend no puede depender de un array de JSX, y esta lista es
# dato normativo estable, no configuración. Si se añade un leñoso al catálogo
# del frontend, hay que añadirlo también aquí.
#
# Es un dict código -> nombre y no un set porque el nombre también hace falta:
# `cultivos_campana` guarda las dos cosas, y el nombre tiene que salir de aquí y
# no del cliente, para que no se cuele texto libre en un documento legal.
CULTIVOS_LENOSOS_IACS = {
    '1710': 'Almendro',
    '1711': 'Viñedo vinificación',
    '1712': 'Viñedo uva de mesa',
    '1720': 'Melocotonero / Nectarino',
    '1730': 'Ciruelo',
    '1740': 'Pistachero',
    '1750': 'Higuera',
    '1760': 'Nogal',
    '1770': 'Cerezo / Guindo',
    '1820': 'Olivar',
    '1830': 'Naranjo',
    '1840': 'Limonero',
}


def es_cultivo_lenoso(cod_iacs):
    """¿Este código IACS es de un cultivo leñoso (permanente)?

    Tolera None, cadena vacía, int y espacios sobrantes: el código llega tanto
    del JSON del formulario como de la BD, y en registros viejos puede venir sucio.
    """
    if cod_iacs is None:
        return False
    return str(cod_iacs).strip() in CULTIVOS_LENOSOS_IACS


# Campos que viajan de una campaña a la siguiente. Fuera quedan a propósito
# `fecha_siembra`, `fecha_recoleccion_prevista`, `kg_sembrados`, `precio_kg_compra`
# y `notas`: son datos de UNA campaña concreta. Heredar la fecha de recolección
# del año pasado sería inventarse un dato en un documento legal.
_CAMPOS_HEREDABLES = ('cultivo', 'cultivo_iacs_cod', 'variedad', 'superficie_cultivada_ha')


def campana_activa(conn, uid, explotacion_id=None):
    """Campaña activa de UNA explotación concreta.

    De ESA explotación, no de la primera fila del usuario: un
    `one(... WHERE user_id=?)` a secas devuelve una fila arbitraria cuando el
    usuario lleva varias explotaciones, y entonces todo se evalúa contra la
    campaña de otra finca. En silencio: los números salen igual y son mentira.

    Vive en helpers y no en cumplimiento.py porque la usan los dos: el motor de
    la Revisión y la herencia de leñosos.
    """
    if explotacion_id:
        expl = one(conn, "SELECT campana_activa FROM explotacion WHERE id=? AND user_id=?",
                   (explotacion_id, uid))
    else:
        expl = one(conn, "SELECT campana_activa FROM explotacion WHERE user_id=?"
                         " ORDER BY orden, id LIMIT 1", (uid,))
    return (expl or {}).get('campana_activa') or '2025/2026'


def heredar_cultivos_lenosos(conn, uid, campana, explotacion_id):
    """Copia a `campana` la declaración de cultivo de las parcelas de leñoso.

    Un cultivo leñoso (olivar, viñedo, almendro…) es permanente: se planta una vez
    y sigue ahí veinte años. Obligar al agricultor a redeclararlo cada campaña es
    pedirle que reescriba a mano un dato que no ha cambiado — con 50+ parcelas, eso
    es lo que hace que un cuaderno se abandone. Ver spec/features/014-*.

    Lo que NO hace es ocultar el aviso de la Revisión: crea la fila de verdad, para
    que el PDF oficial y las exportaciones compatibles con SIEX lleven el cultivo.

    Es **idempotente** y no pisa nunca una declaración existente (si el agricultor
    arrancó el olivar y puso otra cosa, manda lo que él escribió). Por eso se puede
    llamar sin miedo desde una ruta de lectura: la segunda pasada no hace nada.

    Coste fijo de 2 consultas, no crece con el número de parcelas.

    Devuelve el nº de filas heredadas.
    """
    # La campaña llega del query string en el GET de /api/cultivos-campana. No hay
    # inyección (viaja por placeholder en las tres consultas), pero una campaña
    # malformada crearía filas heredadas con una campaña inventada, y esto es un
    # documento legal. La comprobación va AQUÍ y no en la ruta a propósito: así
    # cubre a los dos sitios que llaman y a los que vengan, sin que nadie tenga
    # que acordarse. Señalado por el Security Review del PR #48.
    if not campana or not _CAMPANA_RE.match(str(campana)):
        return 0
    # El filtro de explotación es OPCIONAL, no un `= ?` a secas: con
    # explotacion_id=None, `explotacion_id = NULL` no casa con ninguna fila en SQL
    # y la herencia dejaría de ocurrir EN SILENCIO. Mismo patrón que `expl_sql` en
    # cumplimiento.py; es texto literal, el id siempre por placeholder.
    expl_sql = " AND p.explotacion_id = ?" if explotacion_id else ""
    expl_par = (explotacion_id,) if explotacion_id else ()

    # Las campañas son 'YYYY/YYYY', así que el orden alfabético ES el cronológico:
    # basta con MAX() para quedarse con la última declaración conocida.
    candidatos = dicts(conn, f"""
        SELECT cc.parcela_id, cc.{', cc.'.join(_CAMPOS_HEREDABLES)}
        FROM cultivos_campana cc
        JOIN parcelas p ON p.id = cc.parcela_id
        WHERE p.user_id = ?{expl_sql} AND cc.campana < ?
          AND cc.campana = (SELECT MAX(c2.campana) FROM cultivos_campana c2
                            WHERE c2.parcela_id = cc.parcela_id AND c2.campana < ?)
          AND NOT EXISTS (SELECT 1 FROM cultivos_campana c3
                          WHERE c3.parcela_id = cc.parcela_id AND c3.campana = ?)
    """, (uid,) + expl_par + (campana, campana, campana))

    filas = [
        (r['parcela_id'], explotacion_id, campana) + tuple(r[c] for c in _CAMPOS_HEREDABLES)
        for r in candidatos if es_cultivo_lenoso(r.get('cultivo_iacs_cod'))
    ]
    if not filas:
        return 0

    cols = ', '.join(('parcela_id', 'explotacion_id', 'campana') + _CAMPOS_HEREDABLES)
    ph = ', '.join(['?'] * (3 + len(_CAMPOS_HEREDABLES)))
    conn.cursor().executemany(
        f"INSERT INTO cultivos_campana ({cols}) VALUES ({ph})", filas)
    return len(filas)


# ── Declarar leñosos a partir del uso SIGPAC (feature 015) ────────────────────
# Lourdes tenía 23 parcelas de olivar, viñedo y almendro sin cultivo declarado, y
# las 23 le salían marcadas en la Revisión. El dato de que son olivar YA lo tiene
# la app en `parcelas.uso_sigpac`, que viene del registro oficial: pedírselo a mano
# parcela por parcela es pedirle que teclee lo que ya sabemos.
# Ver spec/features/015-declarar-lenosos-desde-sigpac/.
#
# El valor es el código IACS que se propone sin preguntar, o None si el uso es
# leñoso pero NO se puede deducir el cultivo. En un documento legal no se adivina:
# si hay duda se pregunta, y hasta entonces la parcela sigue contando como pendiente.
USO_SIGPAC_LENOSO = {
    'OV': '1820',   # Olivar → sin ambigüedad
    'VI': None,     # Viñedo → vinificación (1711) o uva de mesa (1712). Hay que
                    #   preguntar: la de vinificación arrastra datos de destino de
                    #   la producción que la de mesa no lleva, así que el cuaderno
                    #   las trata distinto y no vale elegir por el agricultor.
    'FY': None,     # Frutales → "frutal" no es una especie; IACS pide el árbol.
    'VO': None,     # Viñedo-Olivar → dos cultivos en el mismo recinto, hay que
                    #   repartir la superficie entre los dos.
}

# Opciones que se ofrecen cuando hay que preguntar.
_OPCIONES_USO = {
    'VI': ('1711', '1712'),
    'VO': ('1711', '1712', '1820'),
    'FY': ('1710', '1720', '1730', '1740', '1750', '1760', '1770', '1830', '1840'),
}

_ETIQUETA_USO = {'OV': 'Olivar', 'VI': 'Viñedo', 'VO': 'Viñedo y olivar',
                 'FY': 'Frutales'}

# El uso SIGPAC llega sucio: en la BD de producción conviven 'OV - OLIVAR' y
# 'OV-OLIVAR', más cadenas vacías y algún NULL. Por eso NUNCA se compara la cadena
# entera, solo el código de dos letras del principio. Y por eso no vale un
# startswith: 'VO' (viñedo-olivar) y 'VI' (viñedo) son usos distintos, y
# confundirlos declararía el cultivo equivocado.
_USO_RE = re.compile(r'^\s*([A-Za-z]{2})\b')


def codigo_uso_sigpac(valor):
    """'OV - OLIVAR' -> 'OV'. Devuelve '' si no hay un código reconocible."""
    if not valor or not isinstance(valor, str):
        return ''
    m = _USO_RE.match(valor)
    return m.group(1).upper() if m else ''


def sugerencias_lenosos(conn, uid, explotacion_id):
    """Parcelas de leñoso sin cultivo declarado, agrupadas por uso SIGPAC.

    SOLO LEE. Quien decide es el agricultor: esto prepara lo que se le va a
    proponer, y nada se escribe hasta que confirma con `declarar_cultivos_lote`.

    La campaña NO es un parámetro: se saca de la explotación. Que quien llama
    pudiera elegirla es justo el fallo que el Security Review destapó en la 014.
    """
    # Sin explotación no hay nada que proponer: las parcelas cuelgan siempre de
    # una. Salir aquí no es solo una guarda, es lo que permite que la consulta de
    # abajo sea SQL ESTÁTICA, sin el `expl_sql` condicional que se usa en otros
    # sitios del proyecto. Señalado por el Security Review del PR #49: el patrón
    # no es explotable, pero una consulta que no cambia de forma no puede
    # degradarse el día que alguien le añada otro filtro.
    if not explotacion_id:
        return {'campana': None, 'grupos': []}

    campana = campana_activa(conn, uid, explotacion_id)

    pendientes = dicts(conn, """
        SELECT p.id, p.nombre_finca, p.uso_sigpac, p.superficie_ha
        FROM parcelas p
        WHERE p.user_id = ? AND p.explotacion_id = ? AND p.activa = 1
          AND NOT EXISTS (SELECT 1 FROM cultivos_campana cc
                          WHERE cc.parcela_id = p.id AND cc.campana = ?)
        ORDER BY p.nombre_finca, p.id
    """, (uid, explotacion_id, campana))

    grupos = {}
    for p in pendientes:
        uso = codigo_uso_sigpac(p.get('uso_sigpac'))
        if uso not in USO_SIGPAC_LENOSO:
            continue          # herbáceo, sin uso o uso desconocido: no se propone
        cod = USO_SIGPAC_LENOSO[uso]
        g = grupos.setdefault(uso, {
            'uso': uso,
            'etiqueta': _ETIQUETA_USO.get(uso, uso),
            'propuesta': ({'cod': cod, 'cultivo': CULTIVOS_LENOSOS_IACS[cod]}
                          if cod else None),
            'necesita_pregunta': cod is None,
            'opciones': [{'cod': c, 'nombre': CULTIVOS_LENOSOS_IACS[c]}
                         for c in _OPCIONES_USO.get(uso, ())],
            'parcelas': [],
        })
        g['parcelas'].append({'id': p['id'],
                              'nombre': p.get('nombre_finca') or f"Parcela {p['id']}",
                              'superficie_ha': p.get('superficie_ha')})

    return {'campana': campana,
            'grupos': [grupos[u] for u in ('OV', 'VI', 'VO', 'FY') if u in grupos]}


def declarar_cultivos_lote(conn, uid, explotacion_id, declaraciones):
    """Crea las declaraciones de cultivo que el agricultor ha confirmado.

    Recibe EXACTAMENTE qué declarar; el servidor no rellena huecos por su cuenta
    ni deduce cultivos. Devuelve {'creadas', 'saltadas', 'rechazadas', 'motivos'}.

    Una entrada mala no aborta el lote: se rechaza esa y se sigue. Con 23 parcelas
    de golpe, tirar las 22 buenas por una mala sería la peor UX posible.

    Reglas duras:
      - La campaña NO se recibe: se saca de la explotación. Así es imposible
        escribir en una campaña equivocada, la pida quien la pida. Un cliente
        malicioso que mandara `campana=3000/3001` no tiene por dónde entrar.
      - La parcela se comprueba contra `user_id` Y `explotacion_id` en la MISMA
        consulta. Es la lección 4 de la feature 013: lo crítico no son los
        listados, son las referencias cruzadas.
      - El código IACS tiene que estar en el catálogo de leñosos. Nada de texto
        libre, y el nombre del cultivo sale del catálogo, no del cliente.
      - No pisa una declaración existente.
      - La superficie declarada no puede pasar de la de la parcela.
    """
    res = {'creadas': 0, 'saltadas': 0, 'rechazadas': 0, 'motivos': []}
    if not explotacion_id:
        # Igual que en sugerencias_lenosos: sin explotación no hay dónde escribir.
        # La comprobación de la parcela ya lo rechazaría todo, pero decirlo aquí
        # es más honesto que devolver 23 rechazos sin explicar por qué.
        res['rechazadas'] = len(declaraciones or [])
        res['motivos'].append('No hay ninguna explotación seleccionada')
        return res
    campana = campana_activa(conn, uid, explotacion_id)
    res['campana'] = campana

    def _rechaza(motivo):
        res['rechazadas'] += 1
        if motivo not in res['motivos']:
            res['motivos'].append(motivo)

    # Superficie ya comprometida por parcela, para poder repartir una parcela mixta
    # entre dos cultivos dentro del MISMO lote sin pasarse de su superficie.
    comprometida = {}

    for d in (declaraciones or []):
        d = d or {}
        cod = str(d.get('cultivo_iacs_cod') or '').strip()
        if cod not in CULTIVOS_LENOSOS_IACS:
            _rechaza('Cultivo no válido')
            continue

        parcela = one(conn,
                      "SELECT id, superficie_ha FROM parcelas"
                      " WHERE id=? AND user_id=? AND explotacion_id=? AND activa=1",
                      (d.get('parcela_id'), uid, explotacion_id))
        if not parcela:
            _rechaza('Parcela no encontrada en esta explotación')
            continue

        pid = parcela['id']
        if one(conn, "SELECT id FROM cultivos_campana WHERE parcela_id=? AND campana=?"
                     " AND cultivo_iacs_cod=?", (pid, campana, cod)):
            res['saltadas'] += 1
            continue

        sup = _to_real(d.get('superficie_cultivada_ha'))
        if sup and parcela.get('superficie_ha'):
            if pid not in comprometida:
                fila = one(conn, "SELECT COALESCE(SUM(superficie_cultivada_ha),0) AS t"
                                 " FROM cultivos_campana WHERE parcela_id=? AND campana=?",
                           (pid, campana))
                comprometida[pid] = float(fila['t']) if fila else 0.0
            if comprometida[pid] + sup > parcela['superficie_ha'] + 0.01:
                _rechaza('La superficie declarada supera la de la parcela')
                continue
            comprometida[pid] += sup

        conn.execute(
            "INSERT INTO cultivos_campana (parcela_id, explotacion_id, campana,"
            " cultivo, cultivo_iacs_cod, superficie_cultivada_ha) VALUES (?,?,?,?,?,?)",
            (pid, explotacion_id, campana, CULTIVOS_LENOSOS_IACS[cod], cod, sup))
        res['creadas'] += 1

    return res


# ── Registrar por grupo UHC: repartir cantidades absolutas (feature 016) ──────

def repartir_por_superficie(total, parcelas):
    """Reparte una cantidad TOTAL entre las parcelas de un grupo, según su superficie.

    Devuelve {parcela_id: cantidad}.

    Por qué existe: al registrar por grupo UHC, el backend expande el grupo a una
    fila por parcela. Los campos por hectárea (dosis, N/P/K) se replican tal cual,
    pero los ABSOLUTOS no: si el agricultor teclea 3.000 kg cosechados en un grupo
    de 4 parcelas y se replican, el cuaderno acaba diciendo 12.000 kg. Eso es un
    dato falso en un documento legal.

    El reparto es una ESTIMACIÓN, no una medición — es lo que el agricultor haría a
    mano en un grupo homogéneo. La UI se lo dice antes de guardar; quien quiera el
    dato exacto tiene el modo parcela a parcela.

    Dos reglas que no son obvias:

    - **La última parcela absorbe el redondeo.** Repartir a 2 decimales pierde
      céntimos (1000/3 = 333,33 x3 = 999,99). La suma de lo repartido tiene que ser
      EXACTAMENTE lo que tecleó el agricultor: es el criterio 3 de la spec.
    - **Si alguna superficie falta, se reparte a partes iguales** — todas, no solo
      la que falta. Proporcionalmente, una parcela sin superficie se llevaría 0 kg,
      que es peor mentira que el reparto igualitario. No se inventa una superficie.
    """
    if not parcelas:
        return {}

    total = _to_real(total) or 0.0
    if total <= 0:
        return {p['id']: 0.0 for p in parcelas}

    # Superficie negativa = dato corrupto; se trata como ausente y dispara el
    # reparto igualitario, en vez de restar de la suma y descuadrarlo todo.
    sups = []
    for p in parcelas:
        s = _to_real(p.get('superficie_ha'))
        sups.append(s if (s is not None and s > 0) else None)

    if any(s is None for s in sups):
        sups = [1.0] * len(parcelas)

    suma = sum(sups)
    reparto = {}
    acumulado = 0.0
    for i, p in enumerate(parcelas):
        if i == len(parcelas) - 1:
            cantidad = round(total - acumulado, 2)
        else:
            cantidad = round(total * sups[i] / suma, 2)
            acumulado += cantidad
        reparto[p['id']] = cantidad
    return reparto
