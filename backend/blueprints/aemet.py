"""
blueprints/aemet.py — /api/aemet/*

Fuente primaria: METEOALARM ATOM feed (público, sin API key, más fiable).
Fuente secundaria: AEMET OpenData CAP (requiere AEMET_API_KEY, puede tener lag).
"""
import os
import xml.etree.ElementTree as ET

import requests as req_lib

from flask import Blueprint, jsonify, request
from flask_login import login_required

bp = Blueprint('aemet', __name__)

METEOALARM_ATOM = 'https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-spain'
AEMET_CAP_URL   = 'https://opendata.aemet.es/opendata/api/avisos_cap/ultimoelaborado'

SEVERITY_MAP = {
    'Minor':    ('amarillo', '🟡'),
    'Moderate': ('naranja',  '🟠'),
    'Severe':   ('rojo',     '🔴'),
    'Extreme':  ('rojo',     '🔴'),
    'minor':    ('amarillo', '🟡'),
    'moderate': ('naranja',  '🟠'),
    'severe':   ('rojo',     '🔴'),
    'extreme':  ('rojo',     '🔴'),
}

CAP_NS  = 'urn:oasis:names:tc:emergency:cap:1.2'
ATOM_NS = 'http://www.w3.org/2005/Atom'


def _parse_cap_alert(alert_el, provincia):
    """Extrae alertas de un elemento <alert> CAP filtrando por provincia."""
    results = []
    for info in alert_el.findall(f'{{{CAP_NS}}}info'):
        lang = info.findtext(f'{{{CAP_NS}}}language') or ''
        if lang and 'es' not in lang.lower():
            continue
        event    = info.findtext(f'{{{CAP_NS}}}event')    or ''
        severity = info.findtext(f'{{{CAP_NS}}}severity') or 'Minor'
        headline = info.findtext(f'{{{CAP_NS}}}headline') or event
        expires  = info.findtext(f'{{{CAP_NS}}}expires')  or ''
        nivel, icono = SEVERITY_MAP.get(severity, ('amarillo', '🟡'))
        for area in info.findall(f'{{{CAP_NS}}}area'):
            area_desc = area.findtext(f'{{{CAP_NS}}}areaDesc') or ''
            if provincia and provincia not in area_desc.lower():
                continue
            results.append({
                'nivel': nivel, 'icon': icono,
                'evento': event, 'area': area_desc,
                'texto': headline, 'expira': expires,
                'fuente': 'AEMET',
            })
    return results


def _fetch_meteoalarm(provincia):
    """Obtiene alertas de METEOALARM ATOM — sin API key, actualización inmediata."""
    r = req_lib.get(METEOALARM_ATOM, timeout=12,
                    headers={'User-Agent': 'CuadernoExplotacion/2.0'})
    if r.status_code != 200:
        return None, f'METEOALARM HTTP {r.status_code}'

    root = ET.fromstring(r.text)
    alertas = []

    for entry in root.findall(f'{{{ATOM_NS}}}entry'):
        # Cada entry tiene un <content> o un <link> al CAP completo
        # Intentar parsear CAP embebido primero
        for alert_el in entry.findall(f'{{{CAP_NS}}}alert'):
            alertas.extend(_parse_cap_alert(alert_el, provincia))

        # Si no hay CAP embebido, intentar con el summary/title filtrado por provincia
        if not alertas:
            title   = entry.findtext(f'{{{ATOM_NS}}}title')   or ''
            summary = entry.findtext(f'{{{ATOM_NS}}}summary') or ''
            if provincia and provincia not in (title + summary).lower():
                continue
            # Extraer severidad del título si viene en formato METEOALARM
            nivel, icono = ('amarillo', '🟡')
            for k in ('Extreme', 'Severe', 'Moderate', 'Minor',
                      'extreme', 'severe', 'moderate', 'minor'):
                if k.lower() in (title + summary).lower():
                    nivel, icono = SEVERITY_MAP.get(k, ('amarillo', '🟡'))
                    break
            if title:
                alertas.append({
                    'nivel': nivel, 'icon': icono,
                    'evento': title, 'area': '',
                    'texto': summary or title, 'expira': '',
                    'fuente': 'AEMET',
                })

    return alertas, None


def _fetch_aemet_cap(provincia):
    """Obtiene alertas de AEMET OpenData CAP (puede tener lag de horas)."""
    api_key = os.environ.get('AEMET_API_KEY', '')
    if not api_key:
        return None, 'sin API key'
    es_jwt = api_key.startswith('eyJ')
    hdrs   = {'Authorization': f'Bearer {api_key}'} if es_jwt else {'api_key': api_key}
    params = {} if es_jwt else {'api_key': api_key}
    r1 = req_lib.get(AEMET_CAP_URL, headers=hdrs, params=params, timeout=10)
    if r1.status_code == 404:
        return [], None   # sin boletín activo
    if r1.status_code != 200:
        return None, f'AEMET HTTP {r1.status_code}'
    datos_url = r1.json().get('datos')
    if not datos_url:
        return None, 'sin URL datos'
    r2 = req_lib.get(datos_url, timeout=15)
    root = ET.fromstring(r2.text)
    alertas = []
    for entry in root.findall(f'{{{ATOM_NS}}}entry'):
        for alert in entry.findall(f'{{{CAP_NS}}}alert'):
            alertas.extend(_parse_cap_alert(alert, provincia))
    if not alertas:
        if root.tag == f'{{{CAP_NS}}}alert':
            alertas.extend(_parse_cap_alert(root, provincia))
        else:
            for alert in root.findall(f'{{{CAP_NS}}}alert'):
                alertas.extend(_parse_cap_alert(alert, provincia))
    return alertas, None


@bp.route('/api/aemet/alertas')
@login_required
def aemet_alertas():
    provincia = (request.args.get('provincia') or '').strip().lower()
    try:
        # 1) Intentar METEOALARM (más fiable y sin lag)
        alertas, err = _fetch_meteoalarm(provincia)
        if alertas is not None:
            return jsonify({'ok': True, 'alertas': alertas, 'fuente': 'meteoalarm'})

        # 2) Fallback: AEMET OpenData CAP
        alertas, err = _fetch_aemet_cap(provincia)
        if alertas is not None:
            return jsonify({'ok': True, 'alertas': alertas, 'fuente': 'aemet_cap'})

        return jsonify({'ok': True, 'alertas': [], 'msg': err or 'sin datos'})
    except Exception as e:
        return jsonify({'ok': False, 'alertas': [], 'error': str(e)})


@bp.route('/api/aemet/diagnostico')
@login_required
def aemet_diagnostico():
    """Diagnóstico: muestra respuesta cruda de ambas fuentes."""
    provincia = (request.args.get('provincia') or 'ciudad real').strip().lower()
    resultado = {}
    try:
        r = req_lib.get(METEOALARM_ATOM, timeout=12,
                        headers={'User-Agent': 'CuadernoExplotacion/2.0'})
        resultado['meteoalarm'] = {
            'status': r.status_code,
            'primeros_500': r.text[:500] if r.status_code == 200 else r.text[:200],
        }
    except Exception as e:
        resultado['meteoalarm'] = {'error': str(e)}

    api_key = os.environ.get('AEMET_API_KEY', '')
    if api_key:
        try:
            es_jwt = api_key.startswith('eyJ')
            hdrs   = {'Authorization': f'Bearer {api_key}'} if es_jwt else {'api_key': api_key}
            params = {} if es_jwt else {'api_key': api_key}
            r1 = req_lib.get(AEMET_CAP_URL, headers=hdrs, params=params, timeout=10)
            resultado['aemet_cap'] = {'status': r1.status_code, 'es_jwt': es_jwt}
        except Exception as e:
            resultado['aemet_cap'] = {'error': str(e)}
    else:
        resultado['aemet_cap'] = {'msg': 'AEMET_API_KEY no configurada'}

    return jsonify(resultado)
