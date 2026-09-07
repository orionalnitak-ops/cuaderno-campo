"""Test plano (sin pytest) del desplegable de valores repetitivos (comprador,
proveedor, maquinaria, operario) pedido por un piloto (Cristóbal): en vez de
teclear siempre el mismo nombre de cooperativa, se le ofrecen los valores que
ya escribió antes.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_valores_recientes.py
"""
import os, sys, sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import blueprints.ia as ia

UID = 1
EXPL = 5
OTRA_EXPL = 6


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def _db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE cosecha (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, explotacion_id INTEGER,
            fecha_inicio TEXT, comprador TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, explotacion_id INTEGER,
            fecha TEXT, proveedor TEXT, deleted_at TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO cosecha (user_id, explotacion_id, fecha_inicio, comprador) VALUES (?,?,?,?)",
        [
            (UID, EXPL, '2026-06-01', 'Cooperativa Santa Catalina'),
            (UID, EXPL, '2026-07-15', 'Cooperativa Santa Catalina'),
            (UID, EXPL, '2026-08-20', 'Almazara El Pilar'),
            # Otra explotación del mismo usuario: no debe colarse en la lista.
            (UID, OTRA_EXPL, '2026-08-01', 'Comprador de la otra finca'),
        ])
    conn.executemany(
        "INSERT INTO compras (user_id, explotacion_id, fecha, proveedor, deleted_at) VALUES (?,?,?,?,?)",
        [
            (UID, EXPL, '2026-03-01', 'Agroquímicos Valdepeñas', None),
            (UID, EXPL, '2026-05-01', 'Compra borrada', '2026-05-02'),  # borrado lógico
        ])
    conn.commit()
    return conn


def test_modulo_campo_no_permitido():
    print("\n[1] modulo/campo fuera de la allowlist")
    conn = _db()
    for modulo, campo in [('cosecha', 'destino'), ('tratamientos', 'producto_comercial'),
                           ('compras', 'comprador'), ('otro', 'comprador')]:
        try:
            ia._valores_recientes(conn, UID, modulo, campo, EXPL)
            check(f"{modulo}.{campo} debía rechazarse", False)
        except ValueError:
            check(f"{modulo}.{campo} rechazado", True)


def test_valores_mas_recientes_primero():
    print("\n[2] Valores distintos, más reciente primero")
    conn = _db()
    valores = ia._valores_recientes(conn, UID, 'cosecha', 'comprador', EXPL)
    check("2 valores distintos (sin duplicar Santa Catalina)", len(valores) == 2)
    check("el más reciente va primero", valores[0] == 'Almazara El Pilar')
    check("no se cuela el de la otra explotación",
          'Comprador de la otra finca' not in valores)


def test_borrado_logico_se_excluye_en_compras():
    print("\n[3] compras respeta el borrado lógico")
    conn = _db()
    valores = ia._valores_recientes(conn, UID, 'compras', 'proveedor', EXPL)
    check("solo el proveedor no borrado", valores == ['Agroquímicos Valdepeñas'])


if __name__ == '__main__':
    test_modulo_campo_no_permitido()
    test_valores_mas_recientes_primero()
    test_borrado_logico_se_excluye_en_compras()
    print("\nTODOS LOS TESTS PASAN\n")
