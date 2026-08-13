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


if __name__ == '__main__':
    print("\n== auth: correos en registro/verify/forgot/reset ==\n")
    for nombre, fn in sorted(list(globals().items())):
        if nombre.startswith('test_') and callable(fn):
            print(f"{nombre}:"); fn()
    print("\nTodo en verde.\n")
