"""Test plano del aviso de fin de trial.
Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_trial_reminder.py
"""
import os, sys, sqlite3, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import blueprints.push as pushbp  # noqa: E402
import email_service              # noqa: E402


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
    conn.execute("""CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, nombre TEXT,
        plan TEXT, trial_ends_at TEXT, trial_reminder_sent INTEGER DEFAULT 0)""")
    return conn


def _fecha(dias):
    return (datetime.datetime.utcnow() + datetime.timedelta(days=dias)).strftime('%Y-%m-%d %H:%M:%S')


def test_avisa_solo_a_trials_que_acaban_pronto():
    conn = _db()
    conn.execute("INSERT INTO users VALUES (1,'pronto@c.es','A','trial',?,0)", (_fecha(1),))   # avisar
    conn.execute("INSERT INTO users VALUES (2,'lejos@c.es','B','trial',?,0)", (_fecha(5),))     # aún no
    conn.execute("INSERT INTO users VALUES (3,'yaavisado@c.es','C','trial',?,1)", (_fecha(1),))# ya avisado
    conn.execute("INSERT INTO users VALUES (4,'pagando@c.es','D','pro',?,0)", (_fecha(1),))     # no es trial
    conn.commit()
    enviados = []
    email_service.send_trial_ending = lambda user: enviados.append(user['email']) or True
    pushbp.get_db = lambda: _NoCierra(conn)
    n = pushbp.avisar_fin_de_trial()
    check("avisa a 1 solo", n == 1)
    check("es el que acaba pronto", enviados == ['pronto@c.es'])
    marcado = conn.execute("SELECT trial_reminder_sent FROM users WHERE id=1").fetchone()
    check("queda marcado para no repetir", marcado['trial_reminder_sent'] == 1)


if __name__ == '__main__':
    print("\n== aviso fin de trial ==\n")
    for nombre, fn in sorted(list(globals().items())):
        if nombre.startswith('test_') and callable(fn):
            print(f"{nombre}:"); fn()
    print("\nTodo en verde.\n")
