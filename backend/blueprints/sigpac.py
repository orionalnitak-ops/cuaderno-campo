"""
blueprints/sigpac.py — /api/sigpac/*
"""
import re
import time
import logging
import unicodedata
from collections import OrderedDict

import requests as req_lib
from flask import Blueprint, jsonify, request
from flask_login import login_required
from extensions import limiter
from helpers import admin_required, get_uid, get_active_explotacion_id
from db import get_db, dicts

bp = Blueprint('sigpac', __name__)
logger = logging.getLogger(__name__)

SIGPAC_HOST = "https://sigpac.mapa.gob.es/fega/serviciosvisorsigpac"
SIGPAC_BASE = f"{SIGPAC_HOST}/query"
# Endpoint de primera mano que usa el propio visor oficial para el tooltip de cada
# recinto (identificado en cfg/cfg.js del visor: "urlSigPacServices + /layerinfo/recinto/...").
# Da el uso_sigpac y la superficie REALES de un recinto concreto por sus IDs, incluidos
# los no agrícolas (caminos, aguas...) que el WMS de terceros no siempre localiza porque
# muestrea un píxel del mapa en vez de identificar el recinto por atributo.
SIGPAC_LAYERINFO_RECINTO = f"{SIGPAC_HOST}/layerinfo/recinto"


def _sigpac_get(url, timeout=10, retries=1):
    """GET a la API SIGPAC con un reintento por defecto.

    El servicio de FEGA es intermitente (devuelve 502/timeout de forma
    esporádica). Un reintento corto con backoff convierte en éxito la mayoría
    de esos fallos transitorios sin penalizar la latencia del caso bueno.
    """
    last = None
    for attempt in range(retries + 1):
        try:
            r = req_lib.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            if attempt < retries:
                time.sleep(0.4 * (attempt + 1))
    logger.error("_sigpac_get %s: %s", url, last)
    return {"error": "Error al contactar con el servicio SIGPAC"}


# ── Caché en proceso para los catálogos estáticos (provincias/municipios/polígonos) ──
# Estos datos apenas cambian, así que se cachean por worker con TTL. Además, si una
# petición fresca a SIGPAC falla, se sirve el último valor bueno aunque haya caducado
# ("stale-on-error"): la app sigue respondiendo aunque el servicio de FEGA esté caído.
#
# La caché está ACOTADA (LRU): un usuario autenticado podría pedir muchas combinaciones
# prov/municipio/polígono válidas; sin tope, el diccionario crecería sin límite (riesgo
# de agotar memoria del worker). Al superar _CACHE_MAX se evicta la entrada más antigua.
_CACHE = OrderedDict()  # key -> (expires_at, value)
_CACHE_MAX = 512


def _cache_get_or_fetch(key, ttl, fetch, is_valid):
    now = time.time()
    entry = _CACHE.get(key)
    if entry and entry[0] > now:
        _CACHE.move_to_end(key)         # LRU: marcar como usada recientemente
        return entry[1]                 # todavía fresco
    fresh = fetch()
    if is_valid(fresh):
        _CACHE[key] = (now + ttl, fresh)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_MAX:
            _CACHE.popitem(last=False)  # evicta la entrada más antigua
        return fresh
    if entry:                           # fetch falló → servir stale si lo hay
        logger.warning("SIGPAC caché: sirviendo valor stale para %s (fetch falló)", key)
        return entry[1]
    return fresh                        # sin stale previo: propaga el error tal cual


def _is_featurecollection(d):
    return isinstance(d, dict) and 'features' in d


def _sigpac_list(url):
    data = _sigpac_get(url)
    if not isinstance(data, dict) or 'features' not in data:
        return data
    out = []
    for f in data.get('features', []):
        p = (f or {}).get('properties') or {}
        nombre = p.get('nombre') or ''
        nombre = re.sub(r'\s*\(\d+\)\s*$', '', nombre).strip()
        out.append({'codigo': p.get('codigo'), 'nombre': nombre})
    out.sort(key=lambda x: (x['nombre'] or '').lower())
    return out


def _sigpac_param(val, default=''):
    """Valida que un parámetro SIGPAC sea solo dígitos (máx 6). Evita inyección en URLs."""
    s = str(val).strip() if val else default
    if not re.fullmatch(r'\d{1,6}', s):
        return None
    return s


def _norm_nombre(s):
    """Normaliza un nombre de municipio para comparar: sin acentos, mayúsculas, espacios colapsados."""
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', s).strip().upper()


def _parcela_resuelve(prov, mun, pol, par):
    """True si el pol/par existe en SIGPAC bajo ese código de municipio (≥1 recinto)."""
    d = _sigpac_get(f"{SIGPAC_BASE}/recintos/{prov}/{mun}/0/0/{pol}/{par}")
    return isinstance(d, dict) and bool(d.get('features'))


HUBCLOUD_FEATUREINFO = "https://sigpac-hubcloud.es/wms/ows"


def _recinto_bboxes(recintos_data):
    """Extrae [(num_recinto, (x1,y1,x2,y2)), ...] de la respuesta query/recintos (EPSG:4258)."""
    out = []
    for f in (recintos_data.get('features') or []):
        p = f.get('properties') or {}
        try:
            num = int(p.get('nombre'))
        except (TypeError, ValueError):
            continue
        bbox = (p.get('x1'), p.get('y1'), p.get('x2'), p.get('y2'))
        if all(v is not None for v in bbox):
            out.append((num, bbox))
    return out


def _recinto_featureinfo(prov, mun, pol, par, rec, bbox):
    """Datos oficiales de un recinto (superficie_ha, uso_sigpac) vía GetFeatureInfo en
    hubcloud, o None si falla o el recinto no está en la capa (p.ej. es un camino/CA
    que SIGPAC no cataloga como recinto agrícola).

    Esta es la ÚNICA fuente fiable del uso SIGPAC por recinto: el uso vía Catastro
    (referencia catastral) es incorrecto cuando varios recintos comparten la misma
    parcela catastral, porque Catastro clasifica a nivel de parcela completa, no de
    recinto — un recinto que en SIGPAC es "CA-VIALES" (camino) puede heredar el
    cultivo de la parcela catastral entera (p.ej. "OV-OLIVAR") si solo se usa Catastro.
    """
    x1, y1, x2, y2 = bbox
    cql = (f"provincia={prov} AND municipio={mun} AND poligono={pol} "
           f"AND parcela={par} AND recinto={rec}")
    params = {
        'service': 'WMS', 'version': '1.1.1', 'request': 'GetFeatureInfo',
        'layers': 'AU.Sigpac:recinto', 'query_layers': 'AU.Sigpac:recinto',
        'info_format': 'application/json', 'srs': 'EPSG:4258',
        'bbox': f"{x1},{y1},{x2},{y2}", 'width': 256, 'height': 256, 'x': 128, 'y': 128,
        'feature_count': 5, 'styles': '', 'CQL_FILTER': cql,
    }
    try:
        # El WAF de hubcloud bloquea el User-Agent por defecto de requests
        # (devuelve un ServiceExceptionReport XML en vez de JSON). Un UA de
        # navegador evita el bloqueo sin necesidad de headers adicionales.
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; CuadernoDeExplotacion/1.0)'}
        r = req_lib.get(HUBCLOUD_FEATUREINFO, params=params, timeout=10, headers=headers)
        r.raise_for_status()
        feats = (r.json() or {}).get('features') or []
        if not feats:
            return None
        props = feats[0].get('properties') or {}
        sup = props.get('superficie_ha')
        return {
            'superficie_ha': float(sup) if sup is not None else None,
            'uso_sigpac': props.get('uso_sigpac') or '',
        }
    except Exception as e:
        logger.warning("featureinfo %s/%s/%s/%s/%s: %s", prov, mun, pol, par, rec, e)
        return None


def _superficie_featureinfo(prov, mun, pol, par, rec, bbox):
    """superficie_ha oficial de un recinto, o None si falla. Ver _recinto_featureinfo."""
    info = _recinto_featureinfo(prov, mun, pol, par, rec, bbox)
    return info['superficie_ha'] if info else None


def _recinto_layerinfo(prov, mun, pol, par, rec, agr='0', zona='0'):
    """Datos oficiales de un recinto (superficie_ha, uso_sigpac) vía layerinfo/recinto,
    el endpoint que usa el propio visor de sigpac.mapa.gob.es para el tooltip al pasar
    el ratón sobre un recinto. A diferencia de _recinto_featureinfo (WMS de hubcloud,
    que muestrea un píxel), este identifica el recinto por sus IDs, así que también
    funciona para recintos no agrícolas (caminos, aguas, improductivo...).

    Devuelve dict {'superficie_ha', 'uso_sigpac'} o None si falla o no existe.
    """
    url = f"{SIGPAC_LAYERINFO_RECINTO}/{prov},{mun},{agr},{zona},{pol},{par},{rec}"
    data = _sigpac_get(url)
    if not isinstance(data, dict) or 'error' in data:
        return None
    rows = data.get('query') or []
    if not rows:
        return None
    dn = rows[0].get('dn_surface')
    return {
        'superficie_ha': round(float(dn) / 10000, 4) if dn is not None else None,
        'uso_sigpac': rows[0].get('uso_sigpac') or '',
    }


# Mismo criterio que _clean_ref_cat en blueprints/parcelas.py: alfanumérico,
# hasta 20 caracteres (las referencias rústicas no siempre llegan a 20).
_REF_CAT_RE = re.compile(r'^[A-Z0-9]{1,20}$')


def referencia_catastral_parcela(prov, mun, pol, par):
    """Referencia catastral de un pol/par, vía el endpoint de intersección.

    Es la misma para todos los recintos de una parcela catastral (ver
    _recinto_layerinfo), así que basta con consultarla una vez por el
    recinto 1. Devuelve '' si falla, no existe o el formato no es el
    esperado — mismo criterio que superficie_sigpac_parcela.
    """
    # Validación defensiva: los identificadores van en la URL.
    for v in (prov, mun, pol, par):
        if not re.fullmatch(r'\d{1,6}', str(v or '')):
            return ''
    try:
        INTER = "https://sigpac.mapa.gob.es/fega/serviciosvisorsigpac/intersection"
        inter = _sigpac_get(f"{INTER}/recinto/recinto/{prov},{mun},0,0,{pol},{par},1")
        pi = inter.get('parcelaInfo') or {}
        ref = (pi.get('referencia_cat') or '').strip().upper()
        return ref if _REF_CAT_RE.match(ref) else ''
    except Exception:
        return ''


def superficie_sigpac_parcela(prov, mun, pol, par, recinto=None):
    """Superficie SIGPAC (ha) para el badge de verificación.

    - recinto informado -> superficie de ese recinto.
    - recinto vacío -> suma de todos los recintos del pol/par.

    Devuelve (superficie_ha|None, resultado) con resultado en:
      'ok'            -> superficie_ha es un float válido.
      'no_encontrada' -> el pol/par (o el recinto declarado) no existe en SIGPAC.
      'error'         -> fallo transitorio de FEGA (no se debe persistir).
    """
    # Validación defensiva: los identificadores van en URLs.
    for v in (prov, mun, pol, par):
        if not re.fullmatch(r'\d{1,6}', str(v or '')):
            return None, 'no_encontrada'

    data = _sigpac_get(f"{SIGPAC_BASE}/recintos/{prov}/{mun}/0/0/{pol}/{par}")
    if not isinstance(data, dict) or 'error' in data:
        return None, 'error'                      # FEGA caído / respuesta inválida
    bboxes = _recinto_bboxes(data)
    if not bboxes:
        return None, 'no_encontrada'              # pol/par no resuelve

    if recinto:
        try:
            rnum = int(recinto)
        except (TypeError, ValueError):
            return None, 'no_encontrada'
        objetivo = [(n, b) for (n, b) in bboxes if n == rnum]
        if not objetivo:
            return None, 'no_encontrada'          # recinto declarado inexistente
    else:
        objetivo = bboxes

    total = 0.0
    for (n, b) in objetivo:
        ha = _superficie_featureinfo(prov, mun, pol, par, n, b)
        if ha is None:
            # Cualquier recinto que falle invalida la suma: mejor no persistir un
            # total parcial (daría un badge ámbar falso) y tratarlo como transitorio.
            return None, 'error'
        total += ha
    return round(total, 4), 'ok'


_USO_LABELS = {
    'OV': 'OV-OLIVAR', 'VI': 'VI-VIÑEDO', 'TA': 'TA-TIERRA ARABLE',
    'TH': 'TH-HUERTA', 'CF': 'CF-CITRICOS', 'FL': 'FL-FRUTOS SECOS',
    'FY': 'FY-FRUTALES', 'PA': 'PA-PASTO', 'PR': 'PR-PASTO ARBUSTIVO',
    'PS': 'PS-PASTIZAL', 'CA': 'CA-VIALES', 'IM': 'IM-IMPRODUCTIVO',
    'AG': 'AG-CORRIENTES AGUA', 'ZU': 'ZU-ZONA URBANA', 'ED': 'ED-EDIFICACIONES',
    'IV': 'IV-INVERNADERO',
}


@bp.route('/api/sigpac/provincias')
@login_required
@limiter.limit("30 per minute")
def sigpac_provincias():
    return jsonify(_cache_get_or_fetch(
        'prov', 86400,
        lambda: _sigpac_get(f"{SIGPAC_BASE}/provincias"),
        _is_featurecollection))


@bp.route('/api/sigpac/municipios')
@login_required
@limiter.limit("30 per minute")
def sigpac_municipios():
    prov = _sigpac_param(request.args.get('provincia_cod'), '13')
    if not prov: return jsonify({"error": "Parámetro provincia inválido"}), 400
    return jsonify(_cache_get_or_fetch(
        f'muni:{prov}', 21600,
        lambda: _sigpac_list(f"{SIGPAC_BASE}/municipios/{prov}"),
        lambda d: isinstance(d, list)))


@bp.route('/api/sigpac/poligonos')
@login_required
@limiter.limit("30 per minute")
def sigpac_poligonos():
    prov = _sigpac_param(request.args.get('provincia_cod'), '13')
    mun  = _sigpac_param(request.args.get('municipio_cod'), '131')
    if not prov or not mun: return jsonify({"error": "Parámetros SIGPAC inválidos"}), 400
    return jsonify(_cache_get_or_fetch(
        f'poli:{prov}:{mun}', 21600,
        lambda: _sigpac_get(f"{SIGPAC_BASE}/poligonos/{prov}/{mun}"),
        _is_featurecollection))


@bp.route('/api/sigpac/parcelas')
@login_required
@limiter.limit("30 per minute")
def sigpac_parcelas():
    prov = _sigpac_param(request.args.get('provincia_cod'), '13')
    mun  = _sigpac_param(request.args.get('municipio_cod'), '131')
    pol  = _sigpac_param(request.args.get('poligono'), '1')
    if not prov or not mun or not pol: return jsonify({"error": "Parámetros SIGPAC inválidos"}), 400
    return jsonify(_sigpac_get(f"{SIGPAC_BASE}/parcelas/{prov}/{mun}/{pol}"))


@bp.route('/api/sigpac/recintos')
@login_required
@limiter.limit("120 per minute")
def sigpac_recintos():
    prov = _sigpac_param(request.args.get('provincia'), '13')
    mun  = _sigpac_param(request.args.get('municipio'), '131')
    pol  = _sigpac_param(request.args.get('poligono'), '1')
    par  = _sigpac_param(request.args.get('parcela'), '1')
    agr  = _sigpac_param(request.args.get('agregado'), '0')
    zona = _sigpac_param(request.args.get('zona'), '0')
    if not all([prov, mun, pol, par, agr, zona]): return jsonify({"error": "Parámetros SIGPAC inválidos"}), 400
    return jsonify(_sigpac_get(f"{SIGPAC_BASE}/recintos/{prov}/{mun}/{agr}/{zona}/{pol}/{par}"))


@bp.route('/api/sigpac/datos')
@login_required
@limiter.limit("120 per minute")
def sigpac_datos():
    """Obtiene superficie y uso SIGPAC via endpoint de intersección."""
    prov = _sigpac_param(request.args.get('provincia'), '')
    mun  = _sigpac_param(request.args.get('municipio'), '')
    pol  = _sigpac_param(request.args.get('poligono'), '')
    par  = _sigpac_param(request.args.get('parcela'), '')
    rec  = _sigpac_param(request.args.get('recinto') or '1', '1')
    if not all([prov, mun, pol, par, rec]):
        return jsonify({"error": "Parámetros SIGPAC inválidos"}), 400

    resultado = {'superficie_ha': '', 'uso_sigpac': '', 'referencia_cat': '', 'num_recintos': 0}

    try:
        # Paso 1: contar recintos del pol/par
        recintos_data = _sigpac_get(f"{SIGPAC_BASE}/recintos/{prov}/{mun}/0/0/{pol}/{par}")
        resultado['num_recintos'] = len(recintos_data.get('features', []))

        # Paso 2: superficie y uso SIGPAC REALES del recinto, vía layerinfo/recinto — el
        # mismo endpoint de primera mano que usa el visor oficial para su tooltip. Da el
        # dato correcto por recinto (incluidos los no agrícolas, como un camino CA-VIALES),
        # a diferencia de ir por Catastro con la referencia catastral (que es la misma
        # para todos los recintos de una parcela y daría el mismo cultivo a todos).
        info = _recinto_layerinfo(prov, mun, pol, par, rec)
        if info:
            resultado['uso_sigpac'] = info['uso_sigpac']
            if info['superficie_ha'] is not None:
                resultado['superficie_ha'] = info['superficie_ha']

        # Paso 3: referencia catastral (informativa, para el badge de verificación)
        INTER = "https://sigpac.mapa.gob.es/fega/serviciosvisorsigpac/intersection"
        inter = _sigpac_get(f"{INTER}/recinto/recinto/{prov},{mun},0,0,{pol},{par},{rec}")
        pi = inter.get('parcelaInfo') or {}
        resultado['referencia_cat'] = pi.get('referencia_cat', '')
        if not resultado['superficie_ha']:
            dn = pi.get('dn_surface')
            if dn:
                resultado['superficie_ha'] = round(float(dn) / 10000, 4)

    except Exception as e:
        logger.error("sigpac/datos prov=%s mun=%s pol=%s par=%s: %s", prov, mun, pol, par, e)
        resultado['error'] = 'No se pudieron obtener los datos SIGPAC'

    return jsonify(resultado)


@bp.route('/api/sigpac/recintos-detalle')
@login_required
@limiter.limit("120 per minute")
def sigpac_recintos_detalle():
    """Devuelve superficie y uso SIGPAC para CADA recinto de un pol/par."""
    prov = _sigpac_param(request.args.get('provincia'), '')
    mun  = _sigpac_param(request.args.get('municipio'), '')
    pol  = _sigpac_param(request.args.get('poligono'), '')
    par  = _sigpac_param(request.args.get('parcela'), '')
    if not all([prov, mun, pol, par]):
        return jsonify({"error": "Parámetros inválidos"}), 400

    recintos_data = _sigpac_get(f"{SIGPAC_BASE}/recintos/{prov}/{mun}/0/0/{pol}/{par}")
    nums = sorted({
        int(f['properties']['nombre'])
        for f in recintos_data.get('features', [])
        if f.get('properties', {}).get('nombre') is not None
    })
    if not nums:
        return jsonify([])

    resultado = []
    for rec_num in nums:
        item = {'num': rec_num, 'superficie_ha': None, 'uso_sigpac': ''}
        try:
            # layerinfo/recinto da el uso y la superficie reales por recinto (mismo
            # endpoint que el tooltip del visor oficial), incluidos los no agrícolas.
            info = _recinto_layerinfo(prov, mun, pol, par, rec_num)
            if info:
                item['uso_sigpac'] = info['uso_sigpac']
                item['superficie_ha'] = info['superficie_ha']
        except Exception:
            pass
        resultado.append(item)

    return jsonify(resultado)


@bp.route('/api/sigpac/recinto-bbox')
@login_required
@limiter.limit("120 per minute")
def sigpac_recinto_bbox():
    """Devuelve el bounding box (WGS84) de cada recinto de un pol/par.

    Sirve para centrar el mapa embebido de la ficha (Leaflet + fitBounds) sin
    depender del visor externo de SIGPAC. El contorno real del recinto lo pinta
    la capa WMS oficial de SIGPAC; aquí solo necesitamos las coordenadas para
    encuadrar. El bbox viene en las properties (x1,y1,x2,y2) de la consulta de
    recintos, así que es una sola llamada rápida (no usa el endpoint de
    geometría, que es lento e intermitente).
    """
    prov = _sigpac_param(request.args.get('provincia'), '')
    mun  = _sigpac_param(request.args.get('municipio'), '')
    pol  = _sigpac_param(request.args.get('poligono'), '')
    par  = _sigpac_param(request.args.get('parcela'), '')
    if not all([prov, mun, pol, par]):
        return jsonify({"error": "Parámetros inválidos"}), 400

    data = _sigpac_get(f"{SIGPAC_BASE}/recintos/{prov}/{mun}/0/0/{pol}/{par}")
    if not isinstance(data, dict) or 'features' not in data:
        return jsonify({"error": "SIGPAC no devolvió datos para esta parcela"}), 404

    recintos = []
    for f in data.get('features', []):
        p = f.get('properties') or {}
        try:
            recintos.append({
                'recinto': p.get('nombre'),
                'bbox': [float(p['x1']), float(p['y1']), float(p['x2']), float(p['y2'])],
            })
        except (KeyError, TypeError, ValueError):
            continue

    if not recintos:
        return jsonify({"error": "SIGPAC no devolvió coordenadas para esta parcela"}), 404

    return jsonify({'recintos': recintos})


def _reparar_municipios_core(conn, uid, exp_id, dry):
    """Corrige el municipio_cod de las parcelas de un usuario cuando está guardado
    como código INE (u otro) en lugar del código interno de SIGPAC.

    Estrategia a prueba de errores: traduce municipio_nombre → código SIGPAC casando
    por nombre, y SOLO acepta un código si el polígono/parcela de la parcela existe
    de verdad en SIGPAC bajo ese código (verificación real, no solo el nombre).

    - `exp_id` None → todas las parcelas activas del usuario (todas sus explotaciones).
    - `dry` True → solo informa, no escribe.

    Devuelve el dict de resultado (no cierra la conexión).
    """
    if exp_id is None:
        rows = dicts(conn,
                     "SELECT id, nombre_finca, provincia_cod, municipio_cod, municipio_nombre, "
                     "poligono, parcela_num FROM parcelas WHERE user_id=? AND activa=1",
                     (uid,))
    else:
        rows = dicts(conn,
                     "SELECT id, nombre_finca, provincia_cod, municipio_cod, municipio_nombre, "
                     "poligono, parcela_num FROM parcelas "
                     "WHERE user_id=? AND explotacion_id=? AND activa=1",
                     (uid, exp_id))

    muni_cache = {}   # prov -> lista [{codigo, nombre}]
    cand_cache = {}   # (prov, nombre_norm) -> [códigos SIGPAC que casan por nombre]

    def _municipios(prov):
        if prov not in muni_cache:
            data = _sigpac_list(f"{SIGPAC_BASE}/municipios/{prov}")
            muni_cache[prov] = data if isinstance(data, list) else []
        return muni_cache[prov]

    def _candidatos(prov, nom):
        """Códigos SIGPAC cuyo nombre casa (solo por nombre, sin verificar parcela)."""
        key = (prov, nom)
        if key not in cand_cache:
            cand_cache[key] = [
                mc for m in _municipios(prov)
                if _norm_nombre(m['nombre']) == nom and (mc := _sigpac_param(m['codigo']))
            ]
        return cand_cache[key]

    detalle = []
    cambios = 0
    for p in rows:
        prov = _sigpac_param(p['provincia_cod'])
        pol  = _sigpac_param(p['poligono'])
        par  = _sigpac_param(p['parcela_num'])
        cur  = _sigpac_param(p['municipio_cod'])
        nuevo = None

        if not (prov and pol and par):
            estado = 'sin_datos'
        elif cur and _parcela_resuelve(prov, cur, pol, par):
            estado = 'ya_correcto'
        else:
            # El código de municipio depende solo del nombre; la validez de ESTA
            # parcela (pol/par) se comprueba aparte contra cada candidato.
            nom = _norm_nombre(p['municipio_nombre'])
            for mc in _candidatos(prov, nom):
                if _parcela_resuelve(prov, mc, pol, par):
                    nuevo = mc
                    break
            if nuevo and nuevo != cur:
                estado = 'corregido'
                if not dry:
                    conn.execute("UPDATE parcelas SET municipio_cod=? WHERE id=? AND user_id=?",
                                 (nuevo, p['id'], uid))
                    cambios += 1
            elif nuevo:
                estado = 'ya_correcto'
            else:
                estado = 'no_resuelto'

        detalle.append({
            'id': p['id'], 'finca': p['nombre_finca'], 'municipio': p['municipio_nombre'],
            'antes': p['municipio_cod'], 'despues': nuevo, 'estado': estado,
        })

    if not dry and cambios:
        conn.commit()
    resumen = {}
    for d in detalle:
        resumen[d['estado']] = resumen.get(d['estado'], 0) + 1
    return {'ok': True, 'dry_run': dry, 'total': len(rows),
            'cambios': cambios, 'resumen': resumen, 'detalle': detalle}


@bp.route('/api/sigpac/reparar-municipios', methods=['POST'])
@login_required
@limiter.limit("6 per hour")
def sigpac_reparar_municipios():
    """Repara los códigos de municipio de la explotación activa del usuario efectivo.
    `?dry_run=false` aplica; por defecto solo informa."""
    dry = request.args.get('dry_run', 'true').lower() != 'false'
    conn = get_db()
    try:
        res = _reparar_municipios_core(conn, get_uid(), get_active_explotacion_id(conn), dry)
    finally:
        conn.close()
    return jsonify(res)


@bp.route('/api/sigpac/debug')
@login_required
@admin_required
def sigpac_debug():
    """Prueba todas las variantes de la API SIGPAC y devuelve respuestas crudas."""
    prov = request.args.get('provincia', '13')
    mun  = request.args.get('municipio', '')
    pol  = request.args.get('poligono', '')
    par  = request.args.get('parcela', '')
    rec  = request.args.get('recinto', '1')
    INTER = "https://sigpac.mapa.gob.es/fega/serviciosvisorsigpac/intersection"

    recintos_raw = _sigpac_get(f"{SIGPAC_BASE}/recintos/{prov}/{mun}/0/0/{pol}/{par}")
    features = recintos_raw.get('features', [])
    dn_pk = features[0].get('properties', {}).get('dn_pk') if features else None

    dk = str(dn_pk) if dn_pk else None
    return jsonify({
        'params': {'prov': prov, 'mun': mun, 'pol': pol, 'par': par, 'rec': rec},
        'recintos_features_count': len(features),
        'recintos_first_props': features[0].get('properties', {}) if features else {},
        'dn_pk': dk,
        'query_recinto_dnpk':    _sigpac_get(f"{SIGPAC_BASE}/recinto/{dk}") if dk else 'no dn_pk',
        'inter_recinto_dnpk':    _sigpac_get(f"{INTER}/recinto/{dk}") if dk else 'no dn_pk',
        'inter_geometria_dnpk':  _sigpac_get(f"{INTER}/recinto/geometria/{dk}") if dk else 'no dn_pk',
        'inter_by_ref':          _sigpac_get(f"{INTER}/recinto/recinto/{prov},{mun},0,0,{pol},{par},{rec}"),
    })
