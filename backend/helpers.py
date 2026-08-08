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
CULTIVOS_LENOSOS_IACS = frozenset({
    '1710',  # Almendro
    '1711',  # Viñedo vinificación
    '1712',  # Viñedo uva de mesa
    '1720',  # Melocotonero / Nectarino
    '1730',  # Ciruelo
    '1740',  # Pistachero
    '1750',  # Higuera
    '1760',  # Nogal
    '1770',  # Cerezo / Guindo
    '1820',  # Olivar
    '1830',  # Naranjo
    '1840',  # Limonero
})


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
