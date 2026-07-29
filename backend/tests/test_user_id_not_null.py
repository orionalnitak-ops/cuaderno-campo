"""Test plano (sin pytest) del endurecimiento de user_id.

La columna user_id nació como `INTEGER DEFAULT 2` en 12 tablas: un INSERT que
se dejara la columna escribía en la cuenta 2 en vez de fallar. Este test cubre
la migración que lo corrige.

Ejecutar: python backend/tests/test_user_id_not_null.py
"""
import os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import db

DB_PY = os.path.join(os.path.dirname(__file__), '..', 'db.py')


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


class _FakeCursor:
    """Cursor de mentira: apunta el SQL y devuelve lo que le digan."""

    def __init__(self, conn):
        self._conn = conn
        self._last = None

    def execute(self, sql, params=None):
        self._conn.sql.append(' '.join(sql.split()))
        self._last = sql
        tabla = next((t for t in db._TABLAS_USER_ID if f'public.{t}' in sql), None)
        if tabla in self._conn.rompe_en and 'ALTER' in sql:
            raise RuntimeError(f"boom en {tabla}")

    def fetchone(self):
        if 'to_regclass' in self._last:
            return ('existe',)
        if 'COUNT(*)' in self._last:
            tabla = next((t for t in db._TABLAS_USER_ID if f'public.{t}' in self._last), None)
            return (self._conn.huerfanas.get(tabla, 0),)
        return (None,)


class _FakeConn:
    def __init__(self, huerfanas=None, rompe_en=()):
        self.sql = []
        self.commits = 0
        self.rollbacks = 0
        self.huerfanas = huerfanas or {}
        self.rompe_en = rompe_en

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _run(conn):
    original = db.USE_PG
    db.USE_PG = True
    try:
        db._harden_user_id_postgres(conn)
    finally:
        db.USE_PG = original


def test_esquema_sin_default():
    """Ningún CREATE TABLE puede seguir declarando el DEFAULT 2."""
    print("\n[1] Esquema de db.py")
    src = open(DB_PY, encoding='utf-8').read()
    check("no queda 'user_id INTEGER DEFAULT 2'",
          'user_id INTEGER DEFAULT 2' not in src)

    # Se trocea por bloque CREATE TABLE: un regex sobre el fichero entero saltaría
    # de una tabla a la siguiente, porque estos CREATE no van separados por ';'.
    bloques = re.split(r"CREATE TABLE IF NOT EXISTS ", src)[1:]
    declaradas = {
        b.split('(', 1)[0].strip() for b in bloques
        if 'user_id INTEGER NOT NULL' in b.split('CREATE TABLE')[0]
    }
    faltan = set(db._TABLAS_USER_ID) - declaradas
    check(f"las {len(db._TABLAS_USER_ID)} tablas de la lista declaran user_id NOT NULL "
          f"(faltan: {sorted(faltan) or 'ninguna'})", not faltan)


def test_camino_feliz():
    """Sin filas huérfanas: DROP DEFAULT y SET NOT NULL en las 12 tablas."""
    print("\n[2] Migración sin filas huérfanas")
    conn = _FakeConn()
    _run(conn)

    drops = [s for s in conn.sql if 'DROP DEFAULT' in s]
    sets  = [s for s in conn.sql if 'SET NOT NULL' in s]
    check(f"DROP DEFAULT en las {len(db._TABLAS_USER_ID)} tablas",
          len(drops) == len(db._TABLAS_USER_ID))
    check(f"SET NOT NULL en las {len(db._TABLAS_USER_ID)} tablas",
          len(sets) == len(db._TABLAS_USER_ID))
    check("no hubo ningún rollback", conn.rollbacks == 0)
    for t in db._TABLAS_USER_ID:
        check(f"{t} endurecida",
              any(f'public.{t} ALTER COLUMN user_id SET NOT NULL' in s for s in sets))


def test_filas_huerfanas():
    """Con filas user_id NULL: se quita el DEFAULT pero NO se fuerza NOT NULL."""
    print("\n[3] Tabla con filas sin dueño")
    conn = _FakeConn(huerfanas={'tratamientos': 4})
    _run(conn)

    check("se quitó el DEFAULT igualmente",
          any('public.tratamientos ALTER COLUMN user_id DROP DEFAULT' in s for s in conn.sql))
    check("NO se forzó NOT NULL sobre datos que lo violan",
          not any('public.tratamientos ALTER COLUMN user_id SET NOT NULL' in s for s in conn.sql))
    check("el resto de tablas sí se endurecen",
          len([s for s in conn.sql if 'SET NOT NULL' in s]) == len(db._TABLAS_USER_ID) - 1)


def test_fallo_aislado():
    """Un ALTER que revienta no debe impedir el de las demás tablas."""
    print("\n[4] Fallo aislado en una tabla")
    conn = _FakeConn(rompe_en=('parcelas',))
    _run(conn)

    check("hubo rollback del fallo", conn.rollbacks == 1)
    check("las demás tablas se endurecen igual",
          len([s for s in conn.sql if 'SET NOT NULL' in s]) == len(db._TABLAS_USER_ID) - 1)
    check("parcelas no quedó endurecida",
          not any('public.parcelas ALTER COLUMN user_id SET NOT NULL' in s for s in conn.sql))


def test_nombre_de_tabla_no_valido():
    """Un nombre que no sea identificador SQL seguro no llega a interpolarse."""
    print("\n[5] Nombre de tabla no válido")
    conn = _FakeConn()
    original = db._TABLAS_USER_ID
    db._TABLAS_USER_ID = ('parcelas', 'x"; DROP TABLE users; --')
    try:
        _run(conn)
    finally:
        db._TABLAS_USER_ID = original

    check("el nombre malicioso no aparece en ningún SQL",
          not any('DROP TABLE' in s for s in conn.sql))
    check("la tabla legítima se procesa igual",
          any('public.parcelas ALTER COLUMN user_id SET NOT NULL' in s for s in conn.sql))


def test_sqlite_no_hace_nada():
    """En SQLite (local) la migración es un no-op: no soporta ALTER COLUMN."""
    print("\n[6] SQLite")
    conn = _FakeConn()
    original = db.USE_PG
    db.USE_PG = False
    try:
        db._harden_user_id_postgres(conn)
    finally:
        db.USE_PG = original
    check("no se ejecutó ningún SQL", conn.sql == [])


if __name__ == '__main__':
    test_esquema_sin_default()
    test_camino_feliz()
    test_filas_huerfanas()
    test_fallo_aislado()
    test_nombre_de_tabla_no_valido()
    test_sqlite_no_hace_nada()
    print("\nTODOS LOS TESTS PASAN\n")
