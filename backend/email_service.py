"""email_service.py — Envío de correos transaccionales vía Resend (HTTP directo).

No es un blueprint: no expone rutas. Solo envía. La regla dura es que un fallo
de envío NUNCA propaga excepción: se registra y se devuelve False, para que un
alta o un reset no se caigan porque Resend esté caído o el dominio sin verificar.
"""
import os
import logging
from html import escape

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


# ── Plantilla base ────────────────────────────────────────────────────────────

def _layout(titulo, cuerpo_html):
    """Envoltorio HTML común: cabecera con la marca y cuerpo. Sobrio, una columna,
    legible en el móvil. Sin imágenes externas (algunos clientes las bloquean)."""
    titulo = escape(titulo)
    return f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#f4f6f5;padding:24px 0;">
  <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e5e9e7;">
    <div style="background:#00694c;padding:24px;text-align:center;">
      <div style="font-size:30px;">🌿</div>
      <div style="color:#fff;font-weight:800;font-size:18px;margin-top:6px;">Cuaderno de Campo</div>
    </div>
    <div style="padding:28px 24px;color:#1a1c1b;font-size:15px;line-height:1.6;">
      <h1 style="font-size:19px;margin:0 0 16px;">{titulo}</h1>
      {cuerpo_html}
    </div>
    <div style="padding:16px 24px;border-top:1px solid #eef1f0;color:#6b7280;font-size:12px;text-align:center;">
      Cuaderno de Campo · Registro oficial de explotación agrícola · RD 1311/2012
    </div>
  </div>
</div>"""


def _boton(url, texto):
    return (f'<a href="{escape(url, quote=True)}" style="display:inline-block;background:#00694c;color:#fff;'
            f'text-decoration:none;font-weight:700;padding:13px 24px;border-radius:10px;'
            f'font-size:15px;">{escape(texto)}</a>')


# ── Correos concretos ─────────────────────────────────────────────────────────

def send_verificacion_bienvenida(user, token):
    """Alta: bienvenida (tono Isra) + bloque de verificación (seco). Un solo correo."""
    nombre = escape((user.get('nombre') or '').split(' ')[0] or 'agricultor')
    url = f"{base_url()}/verificar?token={token}"
    url_html = escape(url, quote=True)
    cuerpo = f"""\
<p>Bienvenido, {nombre}.</p>
<p>El papeleo del cuaderno ya no es tu problema. Apuntas en el campo, desde el móvil,
y lo demás se ordena solo. Eso es lo que acabas de estrenar.</p>
<p>Tienes 7 días de prueba. Sin tarjeta. Sin letra pequeña.</p>
<hr style="border:none;border-top:1px solid #eef1f0;margin:22px 0;">
<p style="margin:0 0 14px;">Para confirmar tu correo, pulsa aquí:</p>
<p style="text-align:center;margin:0 0 14px;">{_boton(url, 'Verificar mi correo')}</p>
<p style="color:#6b7280;font-size:13px;">Si el botón no funciona, copia esta dirección en el navegador:<br>{url_html}</p>
"""
    return send_email(user['email'], 'Bienvenido a Cuaderno de Campo', _layout('Ya estás dentro', cuerpo))


def send_password_reset(user, token):
    """Reset: técnico y seco. La acción manda."""
    url = f"{base_url()}/nueva-contrasena?token={token}"
    url_html = escape(url, quote=True)
    cuerpo = f"""\
<p>Has pedido cambiar tu contraseña. Pulsa el botón para poner una nueva:</p>
<p style="text-align:center;margin:18px 0;">{_boton(url, 'Cambiar mi contraseña')}</p>
<p style="color:#6b7280;font-size:13px;">Si el botón no funciona, copia esta dirección en el navegador:<br>{url_html}</p>
<p style="color:#6b7280;font-size:13px;">El enlace caduca en 1 hora y solo sirve una vez. Si no has sido tú, ignora este correo: tu contraseña no cambia.</p>
"""
    return send_email(user['email'], 'Cambiar tu contraseña — Cuaderno de Campo',
                      _layout('Cambiar tu contraseña', cuerpo))


def send_trial_ending(user):
    """Aviso de fin de trial: tono Isra, empuje suave a contratar."""
    nombre = escape((user.get('nombre') or '').split(' ')[0] or 'agricultor')
    url = f"{base_url()}/#planes"
    cuerpo = f"""\
<p>{nombre}, tu prueba está a punto de terminar.</p>
<p>Lo que has apuntado estos días no se borra. Sigue ahí, ordenado y listo para
cuando te lo pidan. La pregunta es solo si quieres seguir apuntando igual de fácil.</p>
<p style="text-align:center;margin:18px 0;">{_boton(url, 'Ver los planes')}</p>
<p style="color:#6b7280;font-size:13px;">Un plan cuesta menos que una multa por llevar mal el cuaderno. Pero eso ya lo decides tú.</p>
"""
    return send_email(user['email'], 'Tu prueba termina pronto',
                      _layout('Tu prueba termina pronto', cuerpo))
