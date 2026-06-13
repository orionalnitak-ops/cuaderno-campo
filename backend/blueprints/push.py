"""
blueprints/push.py — /api/push/*
Web Push Notifications (VAPID) para alertas meteorológicas AEMET.
"""
import hashlib
import json
import logging
import os

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import get_db, one, dicts

logger = logging.getLogger(__name__)
bp = Blueprint('push', __name__)

VAPID_PUBLIC_KEY  = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_EMAIL       = os.environ.get('VAPID_EMAIL', 'mailto:orionalnitak@gmail.com')


@bp.route('/api/push/vapid-public-key')
@login_required
def vapid_public_key():
    if not VAPID_PUBLIC_KEY:
        return jsonify({'ok': False, 'error': 'VAPID no configurado'}), 503
    return jsonify({'ok': True, 'public_key': VAPID_PUBLIC_KEY})


@bp.route('/api/push/subscribe', methods=['POST'])
@login_required
def push_subscribe():
    data      = request.get_json() or {}
    endpoint  = data.get('endpoint', '').strip()
    keys      = data.get('keys', {})
    provincia = (data.get('provincia') or '').strip().lower()
    if not endpoint or not keys.get('p256dh') or not keys.get('auth'):
        return jsonify({'ok': False, 'error': 'Suscripción incompleta'}), 400
    conn = get_db()
    try:
        conn.execute(
            '''INSERT INTO push_subscriptions (user_id, endpoint, keys_json, provincia)
               VALUES (?, ?, ?, ?)
               ON CONFLICT (endpoint) DO UPDATE SET
                   user_id   = EXCLUDED.user_id,
                   keys_json = EXCLUDED.keys_json,
                   provincia = EXCLUDED.provincia''',
            (current_user.id, endpoint, json.dumps(keys), provincia)
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({'ok': True})


@bp.route('/api/push/unsubscribe', methods=['DELETE'])
@login_required
def push_unsubscribe():
    conn = get_db()
    try:
        conn.execute('DELETE FROM push_subscriptions WHERE user_id = ?', (current_user.id,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'ok': True})


@bp.route('/api/push/status')
@login_required
def push_status():
    conn = get_db()
    try:
        row = one(conn, 'SELECT id FROM push_subscriptions WHERE user_id = ? LIMIT 1',
                  (current_user.id,))
    finally:
        conn.close()
    return jsonify({'ok': True, 'activo': row is not None})


def _send_push(sub: dict, payload: dict) -> bool:
    """Envía push a una suscripción. Devuelve False si la suscripción es inválida (410/404)."""
    from pywebpush import webpush, WebPushException
    try:
        webpush(
            subscription_info={
                'endpoint': sub['endpoint'],
                'keys': json.loads(sub['keys_json']),
            },
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={'sub': VAPID_EMAIL},
        )
        return True
    except WebPushException as ex:
        try:
            status = ex.response.status_code if ex.response else None
        except Exception:
            status = None
        if status in (404, 410):
            return False  # suscripción revocada por el navegador
        logger.warning('WebPushException endpoint=%s: %s', sub['endpoint'][:50], ex)
        return True  # error temporal — conservar suscripción
    except Exception as ex:
        logger.error('push send error: %s', ex)
        return True


def _alertas_hash(alertas: list) -> str:
    txt = json.dumps(alertas, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(txt.encode()).hexdigest()[:16]


def job_check_push_alertas():
    """
    APScheduler job: comprueba METEOALARM cada 30 min y envía push si cambian las alertas.
    Redis SETNX garantiza ejecución única en entornos multi-worker Gunicorn.
    """
    redis_url = os.environ.get('REDIS_URL')
    if redis_url:
        try:
            import redis as _redis
            r = _redis.from_url(redis_url, socket_connect_timeout=2)
            if not r.set('cuaderno:push_job_lock', '1', ex=25 * 60, nx=True):
                return  # otro worker ya ejecutando
        except Exception:
            pass  # sin Redis → seguimos (OK en dev single-worker)

    if not VAPID_PRIVATE_KEY:
        return

    from blueprints.aemet import _fetch_meteoalarm

    # Obtener provincias únicas con suscriptores
    conn = get_db()
    try:
        provincias = [
            r['provincia'] for r in
            dicts(conn, "SELECT DISTINCT provincia FROM push_subscriptions WHERE provincia != ''")
        ]
    except Exception as e:
        logger.error('push job: no se pudo leer provincias: %s', e)
        conn.close()
        return
    conn.close()

    for provincia in provincias:
        try:
            alertas, err = _fetch_meteoalarm(provincia)
            if alertas is None:
                continue
            nuevo_hash = _alertas_hash(alertas)

            conn = get_db()
            try:
                cache = one(conn,
                            'SELECT alertas_hash FROM push_alertas_cache WHERE provincia = ?',
                            (provincia,))
                if cache and cache['alertas_hash'] == nuevo_hash:
                    conn.close()
                    continue  # sin cambios
                conn.execute(
                    '''INSERT INTO push_alertas_cache (provincia, alertas_hash, updated_at)
                       VALUES (?, ?, CURRENT_TIMESTAMP)
                       ON CONFLICT (provincia) DO UPDATE SET
                           alertas_hash = EXCLUDED.alertas_hash,
                           updated_at   = CURRENT_TIMESTAMP
                       RETURNING provincia''',
                    (provincia, nuevo_hash)
                )
                conn.commit()
            finally:
                conn.close()

            if not alertas:
                continue  # alertas desaparecieron — no notificar

            # Nivel máximo para el título
            nivel_max = 'amarillo'
            for a in alertas:
                if a.get('nivel') == 'rojo':
                    nivel_max = 'rojo'
                    break
                if a.get('nivel') == 'naranja':
                    nivel_max = 'naranja'
            icono = {'rojo': '🔴', 'naranja': '🟠', 'amarillo': '🟡'}.get(nivel_max, '⚠️')
            payload = {
                'title': f'{icono} Alerta AEMET — {provincia.title()}',
                'body':  alertas[0]['texto'] if alertas else 'Nueva alerta meteorológica',
                'url':   '/',
            }

            conn = get_db()
            try:
                subs = dicts(conn,
                             'SELECT id, endpoint, keys_json FROM push_subscriptions WHERE provincia = ?',
                             (provincia,))
            finally:
                conn.close()

            invalid_ids = [s['id'] for s in subs if not _send_push(s, payload)]

            if invalid_ids:
                conn = get_db()
                try:
                    placeholders = ','.join(['?'] * len(invalid_ids))
                    conn.execute(
                        f'DELETE FROM push_subscriptions WHERE id IN ({placeholders})',
                        invalid_ids
                    )
                    conn.commit()
                finally:
                    conn.close()

        except Exception as e:
            logger.error('push job error provincia=%s: %s', provincia, e)
