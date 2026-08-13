"""email_service.py — Envío de correos transaccionales vía Resend (HTTP directo).

No es un blueprint: no expone rutas. Solo envía. La regla dura es que un fallo
de envío NUNCA propaga excepción: se registra y se devuelve False, para que un
alta o un reset no se caigan porque Resend esté caído o el dominio sin verificar.
"""
import os
import logging

import requests

logger = logging.getLogger(__name__)

RESEND_URL = 'https://api.resend.com/emails'


def _api_key():
    return os.environ.get('RESEND_API_KEY', '')


def _from():
    return os.environ.get('EMAIL_FROM', 'Cuaderno de Campo <hola@tualiado.es>')


def base_url():
    """URL pública para construir los enlaces de los correos. No se usa
    request.host_url: el job de fin de trial corre sin petición, y el host de la
    petición puede ser el interno del contenedor."""
    return os.environ.get('PUBLIC_BASE_URL', 'https://cuaderno.tualiado.es').rstrip('/')


def send_email(to, subject, html, reply_to=None):
    """Envía un correo. Devuelve True si Resend lo aceptó, False en cualquier
    otro caso. Nunca lanza."""
    key = _api_key()
    if not key:
        logger.error("RESEND_API_KEY no configurada; correo a %s no enviado", to)
        return False
    payload = {"from": _from(), "to": [to], "subject": subject, "html": html}
    if reply_to:
        payload["reply_to"] = reply_to
    try:
        resp = requests.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )
        if 200 <= resp.status_code < 300:
            return True
        logger.error("Resend rechazó el correo a %s: %s %s", to, resp.status_code,
                     getattr(resp, 'text', ''))
        return False
    except Exception as e:
        logger.error("Error enviando correo a %s: %s", to, e)
        return False
