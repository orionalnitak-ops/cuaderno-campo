"""Test plano de los correos enganchados a las rutas de auth.
Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_auth_emails.py
"""
import os, sys, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('SECRET_KEY', 'test')

import app as app_mod           # noqa: E402
import blueprints.auth as authbp  # noqa: E402
import email_service            # noqa: E402


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


class _NoCierra:
    def __init__(self, c): self._c = c
    def __getattr__(self, n): return getattr(self._c, n)
    def close(self): pass


def _db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE users (
        id INTEGER PRIMARY KEY, email TEXT, password_hash TEXT, nombre TEXT,
        role TEXT, active INTEGER DEFAULT 1, plan TEXT, trial_ends_at TEXT,
        subscription_ends_at TEXT, unlimited_explotaciones INTEGER DEFAULT 0,
        pago_fallido_desde TEXT, stripe_customer_id TEXT, stripe_subscription_id TEXT,
        email_verified INTEGER DEFAULT 0, trial_reminder_sent INTEGER DEFAULT 0)""")
    conn.execute("""CREATE TABLE explotacion (id INTEGER PRIMARY KEY, user_id INTEGER,
        campana_activa TEXT, orden INTEGER DEFAULT 0)""")
    conn.execute("""CREATE TABLE email_tokens (id INTEGER PRIMARY KEY, token TEXT UNIQUE,
        user_id INTEGER, tipo TEXT, expires_at TEXT, used_at TEXT, created_at TEXT)""")
    conn.commit()
    return conn


def _wire(conn):
    authbp.get_db = lambda: _NoCierra(conn)
    import email_tokens
    email_tokens.get_db = lambda: _NoCierra(conn)


def test_registro_crea_cuenta_aunque_el_correo_falle():
    conn = _db(); _wire(conn)
    email_service.send_verificacion_bienvenida = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("resend caído"))
    with app_mod.app.test_request_context('/api/auth/register', method='POST',
            json={'nombre': 'Juan', 'email': 'juan@campo.es', 'password': 'clave1234'}):
        resp = authbp.auth_register()
    fila = conn.execute("SELECT email, email_verified FROM users WHERE email=?", ('juan@campo.es',)).fetchone()
    check("la cuenta se crea igual", fila is not None)
    check("email_verified arranca a 0", fila['email_verified'] == 0)


def test_registro_dispara_el_correo_de_verificacion():
    conn = _db(); _wire(conn)
    llamadas = []
    email_service.send_verificacion_bienvenida = lambda user, token: llamadas.append((user['email'], token)) or True
    with app_mod.app.test_request_context('/api/auth/register', method='POST',
            json={'nombre': 'Ana', 'email': 'ana@campo.es', 'password': 'clave1234'}):
        authbp.auth_register()
    check("se llamó al envío", len(llamadas) == 1)
    check("con el email correcto", llamadas[0][0] == 'ana@campo.es')
    tok = conn.execute("SELECT token FROM email_tokens WHERE tipo='verify'").fetchone()
    check("se creó un token verify", tok is not None)


def test_verify_email_marca_verificado_y_no_repite():
    conn = _db(); _wire(conn)
    conn.execute("INSERT INTO users (id,email,nombre,role,plan,email_verified) VALUES (5,'v@campo.es','V','agricultor','trial',0)")
    import email_tokens
    tok = email_tokens.crear_token(conn, 5, 'verify', ttl_horas=168); conn.commit()
    with app_mod.app.test_request_context('/api/auth/verify-email', method='POST', json={'token': tok}):
        resp = authbp.auth_verify_email()
    fila = conn.execute("SELECT email_verified FROM users WHERE id=5").fetchone()
    check("queda verificado", fila['email_verified'] == 1)
    with app_mod.app.test_request_context('/api/auth/verify-email', method='POST', json={'token': tok}):
        resp2 = authbp.auth_verify_email()
        codigo = resp2[1] if isinstance(resp2, tuple) else 200
    check("token ya usado se rechaza", codigo == 400)


def test_verify_email_token_malo_da_400():
    conn = _db(); _wire(conn)
    with app_mod.app.test_request_context('/api/auth/verify-email', method='POST', json={'token': 'nope'}):
        resp = authbp.auth_verify_email()
        codigo = resp[1] if isinstance(resp, tuple) else 200
    check("token inexistente = 400", codigo == 400)


def test_forgot_password_envia_si_existe():
    conn = _db(); _wire(conn)
    conn.execute("INSERT INTO users (id,email,nombre,role,plan,active) VALUES (8,'r@campo.es','R','agricultor','trial',1)"); conn.commit()
    llamadas = []
    email_service.send_password_reset = lambda user, token: llamadas.append((user['email'], token)) or True
    with app_mod.app.test_request_context('/api/auth/forgot-password', method='POST', json={'email': 'r@campo.es'}):
        resp = authbp.auth_forgot_password()
    check("se envió el reset", len(llamadas) == 1 and llamadas[0][0] == 'r@campo.es')
    tok = conn.execute("SELECT token FROM email_tokens WHERE tipo='reset'").fetchone()
    check("se creó token reset", tok is not None)


def test_forgot_password_no_filtra_emails_desconocidos():
    conn = _db(); _wire(conn)
    llamadas = []
    email_service.send_password_reset = lambda user, token: llamadas.append(1) or True
    with app_mod.app.test_request_context('/api/auth/forgot-password', method='POST', json={'email': 'nadie@campo.es'}):
        resp = authbp.auth_forgot_password()
        cuerpo = resp[0] if isinstance(resp, tuple) else resp
    check("no se envía nada", len(llamadas) == 0)
    check("responde ok igualmente", cuerpo.get_json().get('ok') is True)


def test_reset_password_cambia_el_hash():
    import bcrypt
    conn = _db(); _wire(conn)
    viejo = bcrypt.hashpw(b'viejaclave', bcrypt.gensalt()).decode('utf-8')
    conn.execute("INSERT INTO users (id,email,nombre,role,plan,password_hash,active) VALUES (9,'p@campo.es','P','agricultor','trial',?,1)", (viejo,))
    import email_tokens
    tok = email_tokens.crear_token(conn, 9, 'reset', ttl_horas=1); conn.commit()
    with app_mod.app.test_request_context('/api/auth/reset-password', method='POST',
            json={'token': tok, 'password': 'nuevaclave1'}):
        resp = authbp.auth_reset_password()
    fila = conn.execute("SELECT password_hash FROM users WHERE id=9").fetchone()
    check("la contraseña nueva valida", bcrypt.checkpw(b'nuevaclave1', fila['password_hash'].encode('utf-8')))


def test_reset_password_rechaza_corta():
    conn = _db(); _wire(conn)
    import email_tokens
    conn.execute("INSERT INTO users (id,email,nombre,role,plan,password_hash,active) VALUES (10,'q@campo.es','Q','agricultor','trial','x',1)")
    tok = email_tokens.crear_token(conn, 10, 'reset', ttl_horas=1); conn.commit()
    with app_mod.app.test_request_context('/api/auth/reset-password', method='POST',
            json={'token': tok, 'password': 'corta'}):
        resp = authbp.auth_reset_password()
        codigo = resp[1] if isinstance(resp, tuple) else 200
    check("contraseña corta = 400", codigo == 400)


def test_reset_password_token_malo_da_400():
    conn = _db(); _wire(conn)
    with app_mod.app.test_request_context('/api/auth/reset-password', method='POST',
            json={'token': 'nope', 'password': 'nuevaclave1'}):
        resp = authbp.auth_reset_password()
        codigo = resp[1] if isinstance(resp, tuple) else 200
    check("token malo = 400", codigo == 400)


if __name__ == '__main__':
    print("\n== auth: correos en registro/verify/forgot/reset ==\n")
    for nombre, fn in sorted(list(globals().items())):
        if nombre.startswith('test_') and callable(fn):
            print(f"{nombre}:"); fn()
    print("\nTodo en verde.\n")
