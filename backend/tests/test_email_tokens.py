"""Test plano de los tokens de un solo uso.
Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_email_tokens.py
"""
import os, sys, sqlite3, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import email_tokens  # noqa: E402


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def _db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE email_tokens (
        id INTEGER PRIMARY KEY, token TEXT UNIQUE NOT NULL, user_id INTEGER NOT NULL,
        tipo TEXT NOT NULL, expires_at TEXT NOT NULL, used_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    return conn


def test_crear_devuelve_token_y_lo_guarda():
    conn = _db()
    tok = email_tokens.crear_token(conn, 7, 'verify', ttl_horas=168)
    conn.commit()
    check("token no vacío", isinstance(tok, str) and len(tok) > 20)
    fila = conn.execute("SELECT * FROM email_tokens WHERE token=?", (tok,)).fetchone()
    check("guardado con user_id", fila['user_id'] == 7)
    check("guardado con tipo", fila['tipo'] == 'verify')


def test_consumir_valido_devuelve_uid_y_sella():
    conn = _db()
    tok = email_tokens.crear_token(conn, 7, 'reset', ttl_horas=1); conn.commit()
    uid = email_tokens.consumir_token(conn, tok, 'reset'); conn.commit()
    check("devuelve el uid", uid == 7)
    fila = conn.execute("SELECT used_at FROM email_tokens WHERE token=?", (tok,)).fetchone()
    check("queda sellado", fila['used_at'] is not None)


def test_no_se_puede_usar_dos_veces():
    conn = _db()
    tok = email_tokens.crear_token(conn, 7, 'reset', ttl_horas=1); conn.commit()
    email_tokens.consumir_token(conn, tok, 'reset'); conn.commit()
    segundo = email_tokens.consumir_token(conn, tok, 'reset')
    check("segundo uso rechazado", segundo is None)


def test_tipo_equivocado_no_cuela():
    conn = _db()
    tok = email_tokens.crear_token(conn, 7, 'verify', ttl_horas=1); conn.commit()
    check("reset no consume un token verify", email_tokens.consumir_token(conn, tok, 'reset') is None)


def test_caducado_no_cuela():
    conn = _db()
    tok = email_tokens.crear_token(conn, 7, 'reset', ttl_horas=1); conn.commit()
    ayer = (datetime.datetime.utcnow() - datetime.timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("UPDATE email_tokens SET expires_at=? WHERE token=?", (ayer, tok)); conn.commit()
    check("token caducado rechazado", email_tokens.consumir_token(conn, tok, 'reset') is None)


def test_token_inexistente_devuelve_none():
    conn = _db()
    check("token que no existe", email_tokens.consumir_token(conn, 'noexiste', 'reset') is None)


if __name__ == '__main__':
    print("\n== email_tokens: un solo uso y caducidad ==\n")
    for nombre, fn in sorted(list(globals().items())):
        if nombre.startswith('test_') and callable(fn):
            print(f"{nombre}:"); fn()
    print("\nTodo en verde.\n")
