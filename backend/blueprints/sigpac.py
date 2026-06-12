"""
blueprints/sigpac.py — /api/sigpac/*
"""
import re
import logging

import requests as req_lib
from flask import Blueprint, jsonify, request
from flask_login import login_required
from extensions import limiter
from helpers import admin_required

bp = Blueprint('sigpac', __name__)
logger = logging.getLogger(__name__)

SIGPAC_BASE = "https://sigpac.mapa.gob.es/fega/serviciosvisorsigpac/query"


def _sigpac_get(url, timeout=10):
    try:
        r = req_lib.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error("_sigpac_get %s: %s", url, e)
        return {"error": "Error al contactar con el servicio SIGPAC"}


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


# Mapa de código cultivo Catastro → uso SIGPAC
_CATASTRO_A_SIGPAC = {
    # Labor/cereal
    'C-': 'TA-TIERRA ARABLE', 'CR': 'TA-TIERRA ARABLE', 'CM': 'TA-TIERRA ARABLE',
    'TA': 'TA-TIERRA ARABLE',
    # Huerta
    'TH': 'TH-HUERTA', 'HR': 'TH-HUERTA', 'HS': 'TH-HUERTA',
    # Olivar
    'O-': 'OV-OLIVAR', 'OL': 'OV-OLIVAR', 'OR': 'OV-OLIVAR',
    # Viñedo
    'VI': 'VI-VIÑEDO', 'V-': 'VI-VIÑEDO', 'VR': 'VI-VIÑEDO',
    # Cítricos
    'CF': 'CF-CITRICOS', 'CI': 'CI-CITRICOS-INVER',
    # Frutales
    'FF': 'FL-FRUTOS SECOS', 'FL': 'FL-FRUTOS SECOS',
    'AL': 'FL-FRUTOS SECOS', 'AM': 'FL-FRUTOS SECOS',
    'FY': 'FY-FRUTALES', 'FR': 'FY-FRUTALES', 'FS': 'FY-FRUTALES',
    # Cultivos sin especificar
    'CS': 'CS-CULTIVOS SIN ESPECIF',
    # Pastos
    'PA': 'PA-PASTO', 'PR': 'PR-PASTO ARBUSTIVO', 'PS': 'PS-PASTIZAL',
    'MT': 'PR-PASTO ARBUSTIVO',
    # Improductivo/otros
    'CA': 'CA-VIALES', 'IM': 'IM-IMPRODUCTIVO', 'FO': 'IM-IMPRODUCTIVO',
    'ZU': 'ZU-ZONA URBANA', 'AG': 'AG-CORRIENTE AGUA',
}


def _catastro_a_uso_sigpac(ccc, dcc=''):
    """Convierte código cultivo Catastro a uso SIGPAC."""
    if ccc:
        for k, v in _CATASTRO_A_SIGPAC.items():
            if ccc.upper().startswith(k):
                return v
    # Fallback por descripción (Catastro puede devolver texto con encoding roto)
    try:
        dcc_n = (dcc or '').encode('latin-1').decode('utf-8', errors='ignore').upper()
    except Exception:
        dcc_n = (dcc or '').upper()
    if 'OLIVO' in dcc_n or 'OLIVAR' in dcc_n: return 'OV-OLIVAR'
    if 'VI' in dcc_n and ('VINED' in dcc_n or 'VIÑA' in dcc_n or 'VID' in dcc_n): return 'VI-VIÑEDO'
    if 'LABOR' in dcc_n or 'LABRAD' in dcc_n or 'CEREAL' in dcc_n or 'TRIGO' in dcc_n or 'CEBADA' in dcc_n: return 'TA-TIERRA ARABLE'
    if 'ALMENDRO' in dcc_n or 'FRUTO SECO' in dcc_n or 'ALMOND' in dcc_n: return 'FL-FRUTOS SECOS'
    if 'CITRICO' in dcc_n or 'NARANJO' in dcc_n: return 'CF-CITRICOS'
    if 'PASTIZAL' in dcc_n: return 'PS-PASTIZAL'
    if 'PASTO' in dcc_n or 'PRADO' in dcc_n: return 'PA-PASTO'
    if 'HUERTA' in dcc_n: return 'TH-HUERTA'
    if 'FORESTAL' in dcc_n or 'MONTE' in dcc_n: return 'IM-IMPRODUCTIVO'
    return ''


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
    return jsonify(_sigpac_get(f"{SIGPAC_BASE}/provincias"))


@bp.route('/api/sigpac/municipios')
@login_required
@limiter.limit("30 per minute")
def sigpac_municipios():
    prov = _sigpac_param(request.args.get('provincia_cod'), '13')
    if not prov: return jsonify({"error": "Parámetro provincia inválido"}), 400
    return jsonify(_sigpac_list(f"{SIGPAC_BASE}/municipios/{prov}"))


@bp.route('/api/sigpac/poligonos')
@login_required
@limiter.limit("30 per minute")
def sigpac_poligonos():
    prov = _sigpac_param(request.args.get('provincia_cod'), '13')
    mun  = _sigpac_param(request.args.get('municipio_cod'), '131')
    if not prov or not mun: return jsonify({"error": "Parámetros SIGPAC inválidos"}), 400
    return jsonify(_sigpac_get(f"{SIGPAC_BASE}/poligonos/{prov}/{mun}"))


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
        # Paso 1: contar recintos
        recintos_data = _sigpac_get(f"{SIGPAC_BASE}/recintos/{prov}/{mun}/0/0/{pol}/{par}")
        resultado['num_recintos'] = len(recintos_data.get('features', []))

        # Paso 2: detalle del recinto por referencia completa
        INTER = "https://sigpac.mapa.gob.es/fega/serviciosvisorsigpac/intersection"
        inter = _sigpac_get(f"{INTER}/recinto/recinto/{prov},{mun},0,0,{pol},{par},{rec}")
        pi = inter.get('parcelaInfo') or {}

        dn = pi.get('dn_surface')
        if dn:
            resultado['superficie_ha'] = round(float(dn) / 10000, 4)

        ref_cat = pi.get('referencia_cat', '')
        resultado['referencia_cat'] = ref_cat

        # Paso 3: uso SIGPAC via Catastro (parcelaInfo no lo incluye)
        if ref_cat:
            try:
                import xml.etree.ElementTree as ET
                cat_r = req_lib.get(
                    'https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx/Consulta_DNPRC',
                    params={'Provincia': '', 'Municipio': '', 'RC': ref_cat},
                    timeout=8
                )
                ns = {'c': 'http://www.catastro.meh.es/'}
                root = ET.fromstring(cat_r.text)
                ccc = root.find('.//c:ccc', ns)
                dcc = root.find('.//c:dcc', ns)
                uso = _catastro_a_uso_sigpac(
                    ccc.text if ccc is not None else '',
                    dcc.text if dcc is not None else ''
                )
                if uso:
                    resultado['uso_sigpac'] = uso
                    resultado['cultivo_catastro'] = dcc.text if dcc is not None else ''
            except Exception:
                pass  # Catastro es opcional

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

    INTER = "https://sigpac.mapa.gob.es/fega/serviciosvisorsigpac/intersection"
    resultado = []
    for rec_num in nums:
        item = {'num': rec_num, 'superficie_ha': None, 'uso_sigpac': ''}
        try:
            inter = _sigpac_get(f"{INTER}/recinto/recinto/{prov},{mun},0,0,{pol},{par},{rec_num}")
            pi = inter.get('parcelaInfo') or {}
            dn = pi.get('dn_surface')
            if dn:
                item['superficie_ha'] = round(float(dn) / 10000, 4)
            ref_cat = pi.get('referencia_cat', '')
            if ref_cat:
                try:
                    import xml.etree.ElementTree as ET
                    cat_r = req_lib.get(
                        'https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx/Consulta_DNPRC',
                        params={'Provincia': '', 'Municipio': '', 'RC': ref_cat},
                        timeout=8
                    )
                    ns = {'c': 'http://www.catastro.meh.es/'}
                    root = ET.fromstring(cat_r.text)
                    ccc = root.find('.//c:ccc', ns)
                    dcc = root.find('.//c:dcc', ns)
                    uso = _catastro_a_uso_sigpac(
                        ccc.text if ccc is not None else '',
                        dcc.text if dcc is not None else ''
                    )
                    item['uso_sigpac'] = uso
                except Exception:
                    pass
        except Exception:
            pass
        resultado.append(item)

    return jsonify(resultado)


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
