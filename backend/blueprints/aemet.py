"""
blueprints/aemet.py — /api/aemet/*

Fuente primaria: METEOALARM ATOM feed (público, sin API key, más fiable).
Fuente secundaria: AEMET OpenData CAP (requiere AEMET_API_KEY, puede tener lag).
"""
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests as req_lib

from flask import Blueprint, jsonify, request
from flask_login import login_required

bp = Blueprint('aemet', __name__)

_feed_cache = {'xml': None, 'ts': 0}
_CACHE_TTL  = 600  # 10 minutos

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


def _is_expired(expires_str: str) -> bool:
    """True si el aviso ya ha expirado. Devuelve False si no se puede determinar."""
    if not expires_str:
        return False
    try:
        dt = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
        return dt < datetime.now(timezone.utc)
    except Exception:
        return False


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
        onset    = info.findtext(f'{{{CAP_NS}}}onset')    or ''
        if _is_expired(expires):
            continue
        nivel, icono = SEVERITY_MAP.get(severity, ('amarillo', '🟡'))
        for area in info.findall(f'{{{CAP_NS}}}area'):
            area_desc = area.findtext(f'{{{CAP_NS}}}areaDesc') or ''
            if provincia and provincia not in area_desc.lower():
                continue
            results.append({
                'nivel': nivel, 'icon': icono,
                'evento': event, 'area': area_desc,
                'texto': headline, 'inicio': onset, 'expira': expires,
                'fuente': 'AEMET',
            })
    return results


def _norm(s: str) -> str:
    """Normaliza para comparar: minúsculas, guiones → espacios, sin prefijos admin."""
    s = s.lower().replace('-', ' ').strip()
    for prefix in ('comunidad autónoma de ', 'comunidad autonoma de ',
                   'provincia de la ', 'provincia de '):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s


def _zona_match(haystack: str, provincia: str, comunidad: str) -> bool:
    """True si la provincia O la comunidad aparecen en el haystack normalizado."""
    h = _norm(haystack)
    if provincia and _norm(provincia) in h:
        return True
    if comunidad and _norm(comunidad) in h:
        return True
    return False


def _fetch_meteoalarm(provincia, comunidad=''):
    """Obtiene alertas de METEOALARM ATOM — sin API key, actualización inmediata.

    Acepta `comunidad` (CCAA) para ampliar el matching cuando METEOALARM
    publica el aviso bajo el nombre de la comunidad en lugar de la provincia.
    El feed completo de España se cachea 10 minutos para evitar descargarlo
    en cada carga de pantalla.
    """
    now = time.time()
    if _feed_cache['xml'] is None or now - _feed_cache['ts'] > _CACHE_TTL:
        r = req_lib.get(METEOALARM_ATOM, timeout=12,
                        headers={'User-Agent': 'CuadernoExplotacion/2.0'})
        if r.status_code != 200:
            return None, f'METEOALARM HTTP {r.status_code}'
        _feed_cache['xml'] = r.text
        _feed_cache['ts']  = now

    root = ET.fromstring(_feed_cache['xml'])
    alertas = []

    FENOMENOS = {
        'thunderstorm': 'Tormentas', 'storm': 'Tormenta',
        'rain': 'Lluvia intensa', 'wind': 'Viento fuerte',
        'snow': 'Nieve', 'fog': 'Niebla', 'heat': 'Calor extremo',
        'cold': 'Frío extremo', 'ice': 'Hielo', 'flood': 'Inundaciones',
        'avalanche': 'Aludes', 'coastal': 'Oleaje',
    }

    for entry in root.findall(f'{{{ATOM_NS}}}entry'):
        # 1) CAP embebido dentro de <cap:alert> wrapper (algunos feeds)
        entry_cap = []
        for alert_el in entry.findall(f'{{{CAP_NS}}}alert'):
            entry_cap.extend(_parse_cap_alert(alert_el, provincia))
        alertas.extend(entry_cap)

        if entry_cap:
            continue  # ya procesado

        # 2) Elementos CAP directamente en <entry> (METEOALARM legacy ATOM)
        area_desc = entry.findtext(f'{{{CAP_NS}}}areaDesc') or ''
        if area_desc:
            if (provincia or comunidad) and not _zona_match(area_desc, provincia, comunidad):
                continue
            expira_entry = entry.findtext(f'{{{CAP_NS}}}expires') or ''
            if _is_expired(expira_entry):
                continue
            # METEOALARM usa severity='Moderate' para alertas amarillas — usar título ATOM
            t_low = (entry.findtext(f'{{{ATOM_NS}}}title') or '').lower()
            if 'red' in t_low:
                nivel, icono = 'rojo', '🔴'
            elif 'orange' in t_low:
                nivel, icono = 'naranja', '🟠'
            else:
                nivel, icono = 'amarillo', '🟡'
            event_raw  = (entry.findtext(f'{{{CAP_NS}}}event') or '').lower()
            fenomeno   = next((es for en, es in FENOMENOS.items() if en in event_raw), 'Fenómeno adverso')
            alertas.append({
                'nivel': nivel, 'icon': icono,
                'evento': fenomeno, 'area': area_desc,
                'texto': f'⚠️ {fenomeno} — {area_desc}',
                'inicio': entry.findtext(f'{{{CAP_NS}}}onset')   or '',
                'expira': expira_entry,
                'fuente': 'AEMET',
            })
            continue

        # 3) Fallback: parsear título si no hay CAP de ningún tipo
        title    = entry.findtext(f'{{{ATOM_NS}}}title')   or ''
        summary  = entry.findtext(f'{{{ATOM_NS}}}summary') or ''
        haystack = title + ' ' + summary
        if (provincia or comunidad) and not _zona_match(haystack, provincia, comunidad):
            continue

        nivel, icono = 'amarillo', '🟡'
        h_low = haystack.lower()
        if 'red' in h_low:
            nivel, icono = 'rojo', '🔴'
        elif 'orange' in h_low:
            nivel, icono = 'naranja', '🟠'

        fenomeno = 'Fenómeno adverso'
        for en, es in FENOMENOS.items():
            if en in h_low:
                fenomeno = es
                break

        area = title.split(' - ', 1)[-1].strip() if ' - ' in title else ''
        if title:
            alertas.append({
                'nivel': nivel, 'icon': icono,
                'evento': fenomeno, 'area': area,
                'texto': f'⚠️ {fenomeno} — {area}' if area else f'Aviso {nivel}: {fenomeno}',
                'expira': '', 'fuente': 'AEMET',
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
    comunidad = (request.args.get('comunidad') or '').strip().lower()
    try:
        # 1) Intentar METEOALARM (más fiable y sin lag)
        alertas, err = _fetch_meteoalarm(provincia, comunidad)
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
    """Diagnóstico: muestra entries del feed METEOALARM y resultado del filtro."""
    provincia = (request.args.get('provincia') or 'ciudad real').strip().lower()
    comunidad = (request.args.get('comunidad') or '').strip().lower()
    resultado = {}

    # ── METEOALARM: entries reales + qué coincide ──
    try:
        r = req_lib.get(METEOALARM_ATOM, timeout=12,
                        headers={'User-Agent': 'CuadernoExplotacion/2.0'})
        resultado['meteoalarm_status'] = r.status_code
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            entries = []
            for entry in root.findall(f'{{{ATOM_NS}}}entry'):
                title   = entry.findtext(f'{{{ATOM_NS}}}title')   or ''
                summary = entry.findtext(f'{{{ATOM_NS}}}summary') or ''
                hay     = title + ' ' + summary
                coincide = _zona_match(hay, provincia, comunidad)
                entries.append({
                    'title':    title,
                    'summary':  summary[:120],
                    'coincide': coincide,
                })
            resultado['entries_total']     = len(entries)
            resultado['entries_coinciden'] = [e for e in entries if e['coincide']]
            resultado['todos_los_titles']  = [e['title'] for e in entries]
    except Exception as e:
        resultado['meteoalarm_error'] = str(e)

    # ── Resultado final del filtro ──
    try:
        alertas, err = _fetch_meteoalarm(provincia, comunidad)
        resultado['alertas_resultado'] = alertas
        resultado['alertas_err']       = err
    except Exception as e:
        resultado['alertas_exception'] = str(e)

    return jsonify(resultado)
