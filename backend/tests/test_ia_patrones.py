"""Test plano (sin pytest) del recálculo de patrones del asistente IA.

Cubre el bug detectado en producción (PostgreSQL):
  - los campos numéricos (dosis_valor REAL, equipo_id/aplicador_id INTEGER) se
    filtraban con `!= ''`, lo que revienta en PG con InvalidTextRepresentation
  - el `try` envolvía el bucle entero, así que el primer campo que fallaba
    dejaba sin procesar los siguientes Y sin commitear los anteriores

Ejecutar: python backend/tests/test_ia_patrones.py
"""
import os, sys, sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import blueprints.ia as ia

UID = 1
PARCELA = 7


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


class _NoCloseConn:
    """Proxy sobre sqlite3.Connection que ignora close(), para poder inspeccionar
    la BD después de que _recalcular_patrones la cierre."""

    def __init__(self, conn):
        self._conn = conn

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _db():
    """BD en memoria con las tablas que necesita _recalcular_patrones."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE tratamientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, parcela_id INTEGER, fecha_aplicacion TEXT,
            producto_comercial TEXT, num_registro_mapa TEXT, sustancia_activa TEXT,
            plaga_objetivo TEXT, dosis_valor REAL, dosis_unidad TEXT,
            equipo_id INTEGER, aplicador_id INTEGER, deleted_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE ia_patrones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, modulo TEXT, parcela_id INTEGER, temporada TEXT,
            campo TEXT, valor_sugerido TEXT, frecuencia INTEGER, ultima_vez TEXT
        )
    """)
    conn.executemany("""
        INSERT INTO tratamientos
            (user_id, parcela_id, fecha_aplicacion, producto_comercial,
             num_registro_mapa, sustancia_activa, plaga_objetivo,
             dosis_valor, dosis_unidad, equipo_id, aplicador_id)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, [
        (UID, PARCELA, '2026-04-10', 'Karate Zeon', 'ES-00123', 'lambda-cihalotrin',
         'Pulgón', 0.5, 'l/ha', 3, 9),
        (UID, PARCELA, '2026-04-20', 'Karate Zeon', 'ES-00123', 'lambda-cihalotrin',
         'Pulgón', 0.5, 'l/ha', 3, 9),
        (UID, PARCELA, '2026-05-02', 'Karate Zeon', 'ES-00123', 'lambda-cihalotrin',
         'Trips',  0.75, 'l/ha', 3, 9),
    ])
    conn.commit()
    return conn


def test_condicion_no_vacia():
    """Los campos numéricos NO pueden compararse con cadena vacía (rompe en PG)."""
    print("\n[1] Condición de campo no vacío")

    txt = ia._cond_no_vacio('producto_comercial')
    check("campo de texto exige IS NOT NULL", 'IS NOT NULL' in txt)
    check("campo de texto descarta la cadena vacía", "!= ''" in txt)

    for campo in ('dosis_valor', 'equipo_id', 'aplicador_id'):
        num = ia._cond_no_vacio(campo)
        check(f"{campo} exige IS NOT NULL", 'IS NOT NULL' in num)
        check(f"{campo} NO se compara con ''", "!= ''" not in num)

    pref = ia._cond_no_vacio('dosis_valor', prefijo='cc.')
    check("el prefijo de alias se aplica", pref.startswith('cc.dosis_valor'))


def test_recalculo_completo():
    """Los 8 campos de tratamientos deben aprenderse, numéricos incluidos."""
    print("\n[2] Recálculo de patrones (tratamientos, primavera)")

    conn = _db()
    original = ia.get_db
    ia.get_db = lambda: _NoCloseConn(conn)
    try:
        ia._recalcular_patrones(UID, 'tratamientos', PARCELA, '2026-05-02')
    finally:
        ia.get_db = original

    rows = {r['campo']: r for r in
            (dict(x) for x in conn.execute(
                "SELECT campo, valor_sugerido, frecuencia FROM ia_patrones WHERE user_id=?",
                (UID,)).fetchall())}

    for campo in ia.CAMPOS_MODULO['tratamientos']:
        check(f"se guardó patrón de {campo}", campo in rows)

    check("producto más frecuente correcto",
          rows['producto_comercial']['valor_sugerido'] == 'Karate Zeon')
    check("frecuencia del producto = 3", rows['producto_comercial']['frecuencia'] == 3)
    check("dosis más frecuente = 0.5", str(rows['dosis_valor']['valor_sugerido']) == '0.5')
    check("equipo_id sugerido = 3", str(rows['equipo_id']['valor_sugerido']) == '3')
    check("plaga más frecuente = Pulgón", rows['plaga_objetivo']['valor_sugerido'] == 'Pulgón')


def test_fallo_aislado_por_campo():
    """Si un campo falla, los demás deben guardarse igualmente."""
    print("\n[3] Un campo roto no arrastra a los demás")

    conn = _db()
    # Se elimina la columna del primer campo simulando un fallo de SQL en él
    conn.execute("ALTER TABLE tratamientos RENAME COLUMN producto_comercial TO otro_nombre")
    conn.commit()

    original = ia.get_db
    ia.get_db = lambda: _NoCloseConn(conn)
    try:
        ia._recalcular_patrones(UID, 'tratamientos', PARCELA, '2026-05-02')
    finally:
        ia.get_db = original

    campos = {r[0] for r in conn.execute(
        "SELECT campo FROM ia_patrones WHERE user_id=?", (UID,)).fetchall()}

    check("el campo roto no se guarda", 'producto_comercial' not in campos)
    for campo in ia.CAMPOS_MODULO['tratamientos'][1:]:
        check(f"{campo} se guarda pese al fallo previo", campo in campos)


if __name__ == '__main__':
    test_condicion_no_vacia()
    test_recalculo_completo()
    test_fallo_aislado_por_campo()
    print("\nTODOS LOS TESTS PASAN\n")
