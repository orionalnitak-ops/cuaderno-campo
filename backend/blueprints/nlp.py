"""
blueprints/nlp.py — funciones NLP + /api/parse/*
"""
import datetime
import re as _re
import unicodedata as _UD

from flask import Blueprint, jsonify, request
from flask_login import login_required
from db import get_db, one, dicts
from helpers import get_uid, _to_real

bp = Blueprint('nlp', __name__)


def _norm(s):
    """Minúsculas sin acentos para comparación robusta."""
    return ''.join(
        c for c in _UD.normalize('NFD', str(s).lower())
        if _UD.category(c) != 'Mn'
    )


def extraer_parcela(texto, uid):
    conn = get_db()
    parcelas = dicts(conn, "SELECT id, nombre_finca FROM parcelas WHERE user_id=? AND activa=1", (uid,))
    conn.close()
    tnorm = _norm(texto)

    # 1) Coincidencia exacta normalizada (sin acentos ni mayúsculas)
    for p in parcelas:
        if _norm(p['nombre_finca']) in tnorm:
            return {'id': p['id'], 'nombre': p['nombre_finca']}

    # 2) Coincidencia parcial: todas las palabras >3 letras del nombre están en el texto
    for p in parcelas:
        partes = [w for w in _re.split(r'[\s\-/]+', _norm(p['nombre_finca'])) if len(w) > 3]
        if partes and all(parte in tnorm for parte in partes):
            return {'id': p['id'], 'nombre': p['nombre_finca']}

    return None


def extraer_nombre_candidato(texto):
    """Extrae el candidato a nombre de parcela.
    Prioridad 1: locativo explícito 'en/finca/parcela/campo [el/la] NOMBRE'
    Prioridad 2: patrón verbo → NOMBRE (sin 'en' intermedio)
    """
    STOP_FIN = {'hoy', 'ayer', 'esta', 'este', 'manana', 'por', 'he', 'con', 'sin', 'y'}
    # Palabras función que se eliminan al inicio SOLO si están en minúscula.
    # Mayúscula inicial = parte del nombre propio (ej: "Las Mesas", "El Llano").
    SKIP_LOW = {'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
                'parcela', 'finca', 'campo', 'terreno'}

    def _limpiar(palabras):
        while palabras and _norm(palabras[-1]) in {_norm(s) for s in STOP_FIN}:
            palabras.pop()
        while palabras and palabras[0].lower() in SKIP_LOW and not palabras[0][0].isupper():
            palabras.pop(0)
        return ' '.join(palabras)

    # ── Prioridad 1: locativo explícito ──
    m1 = _re.search(
        r'(?:en|finca|parcela|campo)\s+([\w][\w\s]{1,30}?)'
        r'(?=\s+con\s|\s*[,.]|\s*$)',
        texto, _re.IGNORECASE
    )
    if m1:
        candidato = _limpiar(m1.group(1).strip().split())
        if 2 < len(candidato) < 40:
            return candidato.upper()

    # ── Prioridad 2: verbo → [artículo] → NOMBRE (sin preposición en medio) ──
    VERBOS = (
        r'trat\w{1,6}|abon\w{1,6}|reg\w{1,6}|pod\w{1,6}|cosech\w{1,6}|'
        r'fumig\w{1,6}|sembr\w{1,6}|siembr\w{1,5}|labr\w{1,6}|vendimi\w{1,6}|'
        r'recog\w{1,6}|arad\w{1,5}|cav\w{1,5}|desbroz\w{1,5}|pulver\w{1,5}|'
        r'trilla\w{1,4}|recolect\w{1,5}|subsolad\w{1,4}|grad\w{1,5}|cultiv\w{1,5}'
    )
    m2 = _re.search(
        r'(?:' + VERBOS + r')'
        r'\s+(?:el\s+|la\s+|los\s+|las\s+)?'
        r'([\w][\w\s]{1,33}?)'
        r'(?=\s+en\s|\s+con\s|\s*[,.]|\s+(?:hoy|ayer|esta|este|por|de\s+|$)|\s*$)',
        texto, _re.IGNORECASE
    )
    if m2:
        candidato = _limpiar(m2.group(1).strip().split())
        if 2 < len(candidato) < 40:
            return candidato.upper()

    return None


def extraer_accion(texto):
    tnorm = _norm(texto)
    acciones = {
        'tratamiento': [
            'tratado', 'tratamiento', 'tratamos', 'trate', 'pulverizado', 'pulverice',
            'fumigado', 'fumigue', 'fumigaci', 'spray', 'insecticida', 'fungicida',
            'herbicida', 'fitosanitario', 'plaguicida', 'mata', 'mato',
        ],
        'fertilizacion': [
            'abonado', 'abone', 'abonamos', 'fertilizado', 'fertilice', 'abono',
            'nutrientes', 'nitrogeno', 'fosforo', 'potasio', 'npk', 'urea',
            'sulfato', 'superfosfato', 'estiercol', 'compost', 'purines',
        ],
        'riego': [
            'regado', 'regue', 'rege', 'regamos', 'rego', 'riego', 'riegos',
            'inundado', 'goteo', 'aspersion', 'pivote',
        ],
        'cosecha': [
            'cosechado', 'cosechamos', 'coseche', 'cosecho', 'cosecha ',
            'recolectado', 'recogie', 'vendimiado', 'vendimia',
            'trillado', 'trilla', 'recogi',
        ],
        'labor': [
            'labor', 'labrado', 'labre', 'laboreo',
            'arado', 'are ', 'are,', 'cave', 'cavado',
            'poda', 'pode', 'podamos',
            'desyerbado', 'desherbado', 'desbroz',
            'sembrado', 'siembre', 'siembra', 'sembre', 'sembré', 'he sembrado',
            'he sembrado', 'sembramos', 'sembrar', 'siembro',
            'fresado', 'subsolado', 'cultivado', 'he cultivado', 'cultivé', 'cultivamos',
            'gradeo', 'pase de', 'pase ', 'limpie', 'limpieza',
            'plantado', 'plante', 'planté', 'plantamos', 'plantación',
        ],
    }
    for tipo, palabras in acciones.items():
        for palabra in palabras:
            if _norm(palabra) in tnorm:
                return {'tipo': tipo, 'confianza': 0.9, 'palabra_clave': palabra}
    return {'tipo': None, 'confianza': 0, 'palabra_clave': None}


def extraer_producto(texto):
    tnorm = _norm(texto)
    # (palabra_clave_normalizada, nombre_display)
    productos = [
        # Semillas / cultivos
        ('yero', 'Yeros'), ('yeros', 'Yeros'),
        ('trigo', 'Trigo'), ('cebada', 'Cebada'), ('avena', 'Avena'),
        ('centeno', 'Centeno'), ('triticale', 'Triticale'),
        ('girasol', 'Girasol'), ('colza', 'Colza'), ('maiz', 'Maíz'),
        ('soja', 'Soja'), ('guisante', 'Guisante'), ('garbanzo', 'Garbanzo'),
        ('lenteja', 'Lenteja'), ('almorta', 'Almorta'), ('veza', 'Veza'),
        ('alfalfa', 'Alfalfa'), ('remolacha', 'Remolacha'), ('patata', 'Patata'),
        ('tomate', 'Tomate'), ('pimiento', 'Pimiento'), ('cebolla', 'Cebolla'),
        ('ajo', 'Ajo'), ('olivo', 'Olivo'), ('vid', 'Vid'), ('viña', 'Vid'),
        ('almendro', 'Almendro'), ('pistachero', 'Pistachero'),
        # Fungicidas
        ('cobre', 'Cobre'), ('azufre', 'Azufre'), ('mancozeb', 'Mancozeb'),
        ('captan', 'Captán'), ('clorotalonil', 'Clorotalonil'), ('tebuconazol', 'Tebuconazol'),
        ('iprodiona', 'Iprodiona'), ('metalaxil', 'Metalaxil'), ('fosetil', 'Fosetil-Al'),
        ('ziram', 'Ziram'), ('metiram', 'Metiram'), ('oxicloruro', 'Oxicloruro de cobre'),
        # Insecticidas
        ('clorpirifos', 'Clorpirifos'), ('deltametrina', 'Deltametrina'),
        ('lambda', 'Lambda-cihalotrin'), ('imidacloprid', 'Imidacloprid'),
        ('spinosad', 'Spinosad'), ('abamectina', 'Abamectina'),
        ('dimetoato', 'Dimetoato'), ('piretrinas', 'Piretrinas'),
        # Herbicidas
        ('glifosato', 'Glifosato'), ('diquat', 'Diquat'), ('terbutilazina', 'Terbutilazina'),
        ('s-metolacloro', 'S-metolacloro'), ('pendimetalina', 'Pendimetalina'),
        # Fertilizantes
        ('urea', 'Urea'), ('npk', 'NPK'), ('nitrato amonico', 'Nitrato amónico'),
        ('sulfato amonico', 'Sulfato amónico'), ('superfosfato', 'Superfosfato'),
        ('cloruro potasico', 'Cloruro potásico'), ('estiercol', 'Estiércol'),
        ('compost', 'Compost'), ('purines', 'Purines'),
    ]
    for clave, nombre in productos:
        if _norm(clave) in tnorm:
            return {'nombre': nombre, 'confianza': 0.85}
    return {'nombre': None, 'confianza': 0}


def extraer_dosis(texto):
    patrones = [
        (r'(\d+[.,]?\d*)\s*(cc|centilitro)', 'cc'),
        (r'(\d+[.,]?\d*)\s*(l|litro|litros|ℓ)\b', 'L'),
        (r'(\d+[.,]?\d*)\s*(kg|kilo|kilos)\b', 'kg'),
        (r'(\d+[.,]?\d*)\s*(g|gramo|gramos)\b', 'g'),
        (r'(\d+[.,]?\d*)\s*(t|tonelada|toneladas)\b', 't'),
    ]
    for patron, unidad in patrones:
        m = _re.search(patron, texto, _re.IGNORECASE)
        if m:
            valor = float(m.group(1).replace(',', '.'))
            return {'valor': valor, 'unidad': unidad, 'texto_original': m.group(0)}
    return {'valor': None, 'unidad': None, 'texto_original': None}


def extraer_tipo_riego(texto):
    tnorm = _norm(texto)
    if any(k in tnorm for k in ['goteo', 'gota a gota', 'exudacion']):
        return 'Goteo'
    if any(k in tnorm for k in ['aspersion', 'aspersor', 'rociador', 'lluvia']):
        return 'Aspersión'
    if any(k in tnorm for k in ['pivot', 'pivote']):
        return 'Pivot'
    if any(k in tnorm for k in ['gravedad', 'inundacion', 'inundado', 'manta', 'surcos']):
        return 'Gravedad'
    return None


def extraer_cantidad_riego(texto):
    m = _re.search(r'(\d+[.,]?\d*)\s*hora', texto, _re.IGNORECASE)
    if m:
        return {'horas_riego': float(m.group(1).replace(',', '.')), 'volumen_m3': None}
    m = _re.search(r'(\d+[.,]?\d*)\s*(m3|m³|metro|metros cubicos)', texto, _re.IGNORECASE)
    if m:
        return {'horas_riego': None, 'volumen_m3': float(m.group(1).replace(',', '.'))}
    return {'horas_riego': None, 'volumen_m3': None}


def extraer_fecha(texto):
    """Extrae fecha del texto en lenguaje natural. Devuelve ISO string o hoy."""
    texto_l = texto.lower()
    hoy = datetime.date.today()

    if 'anteayer' in texto_l:
        return (hoy - datetime.timedelta(days=2)).isoformat()
    if 'ayer' in texto_l:
        return (hoy - datetime.timedelta(days=1)).isoformat()

    MESES = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    m = _re.search(r'\b(\d{1,2})\s+de\s+(' + '|'.join(MESES.keys()) + r')\b', texto_l)
    if m:
        dia, mes = int(m.group(1)), MESES[m.group(2)]
        for yr in (hoy.year, hoy.year - 1):
            try:
                fecha = datetime.date(yr, mes, dia)
                if fecha <= hoy + datetime.timedelta(days=1):
                    return fecha.isoformat()
            except ValueError:
                pass

    m = _re.search(r'\b(\d{1,2})[/-](\d{1,2})\b', texto_l)
    if m:
        dia, mes = int(m.group(1)), int(m.group(2))
        for yr in (hoy.year, hoy.year - 1):
            try:
                fecha = datetime.date(yr, mes, dia)
                if fecha <= hoy + datetime.timedelta(days=1):
                    return fecha.isoformat()
            except ValueError:
                pass

    DIAS = {
        'lunes': 0, 'martes': 1, 'miércoles': 2, 'miercoles': 2,
        'jueves': 3, 'viernes': 4, 'sábado': 5, 'sabado': 5, 'domingo': 6
    }
    for nombre, num in DIAS.items():
        if nombre in texto_l:
            atras = (hoy.weekday() - num) % 7 or 7
            return (hoy - datetime.timedelta(days=atras)).isoformat()

    return hoy.isoformat()


@bp.route('/api/parse', methods=['POST'])
@login_required
def parse_texto_libre():
    uid = get_uid()
    data = request.json or {}
    texto = (data.get('texto') or '').strip()

    if not texto:
        return jsonify({"status": "error", "message": "El texto no puede estar vacío"}), 400

    parcela_data = extraer_parcela(texto, uid)
    accion_data = extraer_accion(texto)
    producto_data = extraer_producto(texto)
    dosis_data = extraer_dosis(texto)
    nombre_candidato = None if parcela_data else extraer_nombre_candidato(texto)

    parcela_id = parcela_data['id'] if parcela_data else None
    fecha = extraer_fecha(texto)

    es_riego = accion_data['tipo'] == 'riego'
    cantidad_riego = extraer_cantidad_riego(texto) if es_riego else {'horas_riego': None, 'volumen_m3': None}

    return jsonify({
        "status": "success",
        "texto_original": texto,
        "parseo": {
            "parcela": {
                "id": parcela_id,
                "nombre": parcela_data['nombre'] if parcela_data else None,
                "nombre_candidato": nombre_candidato,
                "es_nueva": not parcela_data and bool(nombre_candidato),
                "requiere_seleccion": not parcela_data and not nombre_candidato,
                "confianza": 1.0 if parcela_data else 0.0,
            },
            "accion": {"tipo": accion_data['tipo'], "palabra_clave": accion_data['palabra_clave'], "confianza": accion_data['confianza']},
            "producto": {"nombre": producto_data['nombre'], "confianza": producto_data['confianza']},
            "dosis": {"valor": dosis_data['valor'], "unidad": dosis_data['unidad']},
            "fecha": fecha,
            "riego": {
                "tipo_riego": extraer_tipo_riego(texto) if es_riego else None,
                "horas_riego": cantidad_riego['horas_riego'],
                "volumen_m3": cantidad_riego['volumen_m3'],
            },
        },
        "requiere_confirmacion": not parcela_data and not nombre_candidato,
    })


@bp.route('/api/parse/guardar', methods=['POST'])
@login_required
def parse_guardar():
    uid = get_uid()
    data = request.json or {}

    accion        = data.get('accion')
    palabra_clave = (data.get('palabra_clave') or '').strip()
    parcela_id    = data.get('parcela_id')
    parcela_nombre = (data.get('parcela_nombre') or '').strip()
    producto     = (data.get('producto') or '').strip()
    fecha        = data.get('fecha') or datetime.date.today().isoformat()
    texto        = (data.get('texto_original') or '').strip()
    campana      = data.get('campana') or '2025/2026'

    conn = get_db()

    # Auto-crear parcela si no existe
    if not parcela_id and parcela_nombre:
        c = conn.cursor()
        c.execute("INSERT INTO parcelas (user_id, nombre_finca) VALUES (?, ?)", (uid, parcela_nombre))
        parcela_id = c.lastrowid
        conn.commit()

    if not parcela_id:
        conn.close()
        return jsonify({"ok": False, "error": "No se pudo determinar la parcela. Indícala manualmente."}), 400

    parcela = one(conn, "SELECT nombre_finca FROM parcelas WHERE id=? AND user_id=?", (parcela_id, uid))
    etiqueta = (parcela or {}).get('nombre_finca', '')

    nota = f"NLP: {texto}" if texto else ''

    if accion == 'tratamiento':
        # Los tratamientos fitosanitarios requieren campos obligatorios del RD 1311/2012 (ROPO,
        # nº MAPA, sustancia activa, dosis, plazo de seguridad) que el texto libre no puede capturar.
        # Redirigir al formulario completo para evitar registros ilegalmente incompletos.
        conn.close()
        return jsonify({
            "ok": False,
            "requiere_formulario": True,
            "error": (
                "Los tratamientos fitosanitarios requieren datos obligatorios (Nº MAPA, sustancia "
                "activa, dosis, ROPO del aplicador, plazo de seguridad) que no se pueden capturar "
                "de texto libre. Usa el formulario completo para registrar este tratamiento."
            ),
            "producto": producto,
            "parcela_id": parcela_id,
            "fecha": fecha,
        }), 422
    elif accion == 'fertilizacion':
        # Igual que tratamientos: tipo de fertilizante, dosis y parcela son obligatorios por ley.
        conn.close()
        return jsonify({
            "ok": False,
            "requiere_formulario": True,
            "error": (
                "Las fertilizaciones requieren datos obligatorios (tipo de fertilizante, dosis, "
                "parcela) según el RD 1311/2012 Anexo III S4. Usa el formulario completo."
            ),
            "producto": producto,
            "parcela_id": parcela_id,
            "fecha": fecha,
        }), 422
    elif accion == 'riego':
        tipo_riego = (data.get('tipo_riego') or '').strip() or 'Goteo'
        horas_riego = _to_real(data.get('horas_riego'))
        volumen_m3 = _to_real(data.get('volumen_m3'))
        if not horas_riego and not volumen_m3:
            horas_riego = 1.0
        conn.execute(
            "INSERT INTO riego (user_id, parcela_id, parcela_etiqueta, fecha, tipo_riego, horas_riego, volumen_m3, fuente_agua, notas, campana) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (uid, parcela_id, etiqueta, fecha, tipo_riego,
             horas_riego,
             volumen_m3,
             None, nota, campana)
        )
    elif accion == 'cosecha':
        conn.execute(
            "INSERT INTO cosecha (user_id, parcela_id, parcela_etiqueta, fecha_inicio, cultivo, produccion_total_unidad, notas, campana) VALUES (?,?,?,?,?,?,?,?)",
            (uid, parcela_id, etiqueta, fecha, producto or None, 'kg', nota, campana)
        )
    else:
        # palabra_clave viene del frontend; si no, re-extraer del texto
        if not palabra_clave:
            accion_det = extraer_accion(texto)
            palabra_clave = accion_det.get('palabra_clave') or ''
        # Normalizar al valor exacto del desplegable del formulario
        _LABOR_MAP = {
            'arado': 'Arado', 'are': 'Arado', 'arar': 'Arado',
            'poda': 'Poda', 'pode': 'Poda', 'podamos': 'Poda',
            'desherbado': 'Desherbado', 'desyerbado': 'Desherbado', 'desbroz': 'Desherbado',
            'siembra': 'Siembra', 'sembrado': 'Siembra', 'siembre': 'Siembra', 'sembre': 'Siembra',
            'sembré': 'Siembra', 'sembramos': 'Siembra', 'sembrar': 'Siembra', 'siembro': 'Siembra',
            'he sembrado': 'Siembra', 'plantado': 'Plantación', 'plante': 'Plantación',
            'planté': 'Plantación', 'plantamos': 'Plantación', 'plantación': 'Plantación',
            'cultivado': 'Siembra', 'cultivé': 'Siembra', 'cultivamos': 'Siembra', 'he cultivado': 'Siembra',
            'fresado': 'Fresado', 'fresa': 'Fresado',
            'subsolado': 'Subsolado',
            'gradeo': 'Gradeo', 'pase': 'Gradeo',
            'limpieza': 'Limpieza', 'limpie': 'Limpieza',
            'laboreo': 'Laboreo del suelo', 'labrado': 'Laboreo del suelo',
            'labor': 'Laboreo del suelo',
            'vendimia': 'Vendimia', 'vendimiado': 'Vendimia',
            'escarda': 'Escarda', 'cave': 'Escarda', 'cavado': 'Escarda',
            'trilla': 'Triturado de restos', 'trillado': 'Triturado de restos',
            'riego': 'Riego', 'regado': 'Riego',
            'siega': 'Otros', 'segado': 'Otros',
        }
        tipo = _LABOR_MAP.get((palabra_clave or '').lower().strip()) or palabra_clave or accion or 'Otros'
        # Si es siembra/plantación y se detectó cultivo, usarlo como descripción
        if tipo in ('Siembra', 'Plantación') and producto:
            descripcion_labor = f"{tipo} de {producto}"
        else:
            descripcion_labor = texto
        conn.execute(
            "INSERT INTO labores (user_id, parcela_id, parcela_etiqueta, fecha, tipo_labor, descripcion, producto, notas, campana) VALUES (?,?,?,?,?,?,?,?,?)",
            (uid, parcela_id, etiqueta, fecha, tipo, descripcion_labor, producto or None, nota, campana)
        )

    conn.commit()
    conn.close()
    return jsonify({"ok": True, "parcela_id": parcela_id, "parcela_nombre": etiqueta or parcela_nombre})
