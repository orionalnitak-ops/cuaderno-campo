"""Test plano (sin pytest) del envío de correos.
Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_email_service.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ['RESEND_API_KEY'] = 'test_key'
os.environ['EMAIL_FROM'] = 'Cuaderno de Campo <hola@tualiado.es>'
os.environ['PUBLIC_BASE_URL'] = 'https://cuaderno.tualiado.es'

import email_service  # noqa: E402


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def test_envio_ok_hace_post_a_resend():
    llamadas = []
    class _Resp:
        status_code = 200
        def json(self): return {"id": "abc"}
    email_service.requests.post = lambda url, **kw: (llamadas.append((url, kw)), _Resp())[1]
    ok = email_service.send_email('a@b.es', 'Asunto', '<p>Hola</p>')
    check("devuelve True", ok is True)
    url, kw = llamadas[0]
    check("url correcta", url == 'https://api.resend.com/emails')
    check("auth bearer", kw['headers']['Authorization'] == 'Bearer test_key')
    check("destinatario", kw['json']['to'] == ['a@b.es'])
    check("remitente del entorno", kw['json']['from'] == 'Cuaderno de Campo <hola@tualiado.es>')


def test_un_fallo_de_red_no_revienta():
    def _boom(*a, **k): raise ConnectionError("sin red")
    email_service.requests.post = _boom
    ok = email_service.send_email('a@b.es', 'Asunto', '<p>Hola</p>')
    check("devuelve False sin lanzar", ok is False)


def test_status_no_2xx_devuelve_false():
    class _Resp:
        status_code = 422
        text = 'dominio no verificado'
        def json(self): return {}
    email_service.requests.post = lambda url, **kw: _Resp()
    ok = email_service.send_email('a@b.es', 'Asunto', '<p>Hola</p>')
    check("422 devuelve False", ok is False)


def test_verificacion_bienvenida_lleva_enlace_con_token():
    orig = email_service.send_email
    enviados = []
    email_service.send_email = lambda to, subject, html, reply_to=None: (
        enviados.append((to, subject, html)), True)[1]
    try:
        ok = email_service.send_verificacion_bienvenida(
            {'email': 'juan@campo.es', 'nombre': 'Juan'}, 'TOK123')
    finally:
        email_service.send_email = orig
    check("devuelve True", ok is True)
    to, subject, html = enviados[0]
    check("va al agricultor", to == 'juan@campo.es')
    check("enlace con base y token", 'https://cuaderno.tualiado.es/verificar?token=TOK123' in html)
    check("saluda por su nombre", 'Juan' in html)


def test_reset_lleva_enlace_de_nueva_contrasena():
    orig = email_service.send_email
    enviados = []
    email_service.send_email = lambda to, subject, html, reply_to=None: (
        enviados.append((to, subject, html)), True)[1]
    try:
        email_service.send_password_reset({'email': 'juan@campo.es', 'nombre': 'Juan'}, 'RST9')
    finally:
        email_service.send_email = orig
    to, subject, html = enviados[0]
    check("enlace de reset con token",
          'https://cuaderno.tualiado.es/nueva-contrasena?token=RST9' in html)


def test_trial_ending_menciona_la_prueba():
    orig = email_service.send_email
    enviados = []
    email_service.send_email = lambda to, subject, html, reply_to=None: (
        enviados.append((to, subject, html)), True)[1]
    try:
        email_service.send_trial_ending({'email': 'juan@campo.es', 'nombre': 'Juan'})
    finally:
        email_service.send_email = orig
    to, subject, html = enviados[0]
    check("va al agricultor", to == 'juan@campo.es')
    check("apunta a planes", 'https://cuaderno.tualiado.es/#planes' in html)


if __name__ == '__main__':
    print("\n== email_service: envío base ==\n")
    for nombre, fn in sorted(list(globals().items())):
        if nombre.startswith('test_') and callable(fn):
            print(f"{nombre}:"); fn()
    print("\nTodo en verde.\n")
