"""
blueprints/aemet.py — /api/aemet/*
"""
import os
import requests as req_lib

from flask import Blueprint, jsonify, request
from flask_login import login_required

bp = Blueprint('aemet', __name__)


@bp.route('/api/aemet/alertas')
@login_required
def aemet_alertas():
    import xml.etree.ElementTree as ET
    provincia = (request.args.get('provincia') or '').strip().lower()
    api_key = os.environ.get('AEMET_API_KEY', '')
    if not api_key:
        return jsonify({'ok': True, 'alertas': [], 'msg': 'AEMET_API_KEY no configurada'})
    try:
        r1 = req_lib.get(
            'https://opendata.aemet.es/opendata/api/avisos_cap/ultimoelaborado',
            params={'api_key': api_key},
            timeout=10
        )
        if r1.status_code == 404:
            return jsonify({'ok': True, 'alertas': [], 'msg': 'Sin alertas activas'})
        if r1.status_code != 200:
            return jsonify({'ok': False, 'alertas': [], 'status': r1.status_code, 'detail': r1.text[:300]})
        datos_url = r1.json().get('datos')
        if not datos_url:
            return jsonify({'ok': False, 'alertas': []})

        r2 = req_lib.get(datos_url, timeout=15)
        root = ET.fromstring(r2.text)

        CAP  = 'urn:oasis:names:tc:emergency:cap:1.2'
        ATOM = 'http://www.w3.org/2005/Atom'
        severity_map = {
            'Minor':    ('amarillo', '🟡'),
            'Moderate': ('naranja',  '🟠'),
            'Severe':   ('rojo',     '🔴'),
            'Extreme':  ('rojo',     '🔴'),
        }

        def parse_alert(alert_el):
            results = []
            for info in alert_el.findall(f'{{{CAP}}}info'):
                lang = info.findtext(f'{{{CAP}}}language') or ''
                if lang and 'es' not in lang.lower():
                    continue
                event    = info.findtext(f'{{{CAP}}}event')    or ''
                severity = info.findtext(f'{{{CAP}}}severity') or 'Minor'
                headline = info.findtext(f'{{{CAP}}}headline') or event
                expires  = info.findtext(f'{{{CAP}}}expires')  or ''
                nivel, icono = severity_map.get(severity, ('amarillo', '🟡'))
                for area in info.findall(f'{{{CAP}}}area'):
                    area_desc = area.findtext(f'{{{CAP}}}areaDesc') or ''
                    if provincia and provincia not in area_desc.lower():
                        continue
                    results.append({
                        'nivel': nivel, 'icon': icono,
                        'evento': event, 'area': area_desc,
                        'texto': headline, 'expira': expires,
                        'fuente': 'AEMET',
                    })
            return results

        alertas = []
        for entry in root.findall(f'{{{ATOM}}}entry'):
            for alert in entry.findall(f'{{{CAP}}}alert'):
                alertas.extend(parse_alert(alert))
        if not alertas:
            if root.tag == f'{{{CAP}}}alert':
                alertas.extend(parse_alert(root))
            else:
                for alert in root.findall(f'{{{CAP}}}alert'):
                    alertas.extend(parse_alert(alert))

        return jsonify({'ok': True, 'alertas': alertas})
    except Exception as e:
        return jsonify({'ok': False, 'alertas': [], 'error': str(e)})
