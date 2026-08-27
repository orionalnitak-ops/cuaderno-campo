"""Test plano (sin pytest) del cultivo de campaña por grupo UHC.

Cubre la fase 4 de spec/features/016-uhc-en-cosecha-abonado-cultivo/plan.md.

Una UHC ya es, por definición, un conjunto de parcelas del mismo cultivo, así que
declararlo de una vez es el caso natural. Lo que hay que blindar:

  - cada fila lleva la superficie de SU parcela, no una repartida (ya la sabemos),
  - `kg_sembrados`, que sí es una cantidad absoluta, se reparte,
  - nunca se pisa una declaración existente (se salta y se cuenta),
  - una parcela sin sitio se rechaza SOLA, sin tumbar el grupo — al revés que en
    cosecha, porque declarar de menos no es una infracción,
  - el código IACS sigue siendo obligatorio: no se adivina en un documento legal.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_uhc_cultivo_campana.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from blueprints.parcelas import _declarar_cultivo_grupo  # noqa: E402

UID = 1
EXPL = 10
OTRA_EXPL = 20
CAMPANA = '2025/2026'

OLIVAR = '1820'
VINEDO = '1711'

_SCHEMA = """
CREATE TABLE parcelas (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER,
    nombre_finca TEXT, superficie_ha REAL);
CREATE TABLE unidades_homogeneas (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER,
    nombre TEXT, cultivo TEXT, campana TEXT, deleted_at TIMESTAMP);
CREATE TABLE uhc_parcelas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, uhc_id INTEGER, parcela_id INTEGER);
CREATE TABLE cultivos_campana (
    id INTEGER PRIMARY KEY AUTOINCREMENT, parcela_id INTEGER, explotacion_id INTEGER,
    campana TEXT, cultivo TEXT, cultivo_iacs_cod TEXT, variedad TEXT,
    fecha_siembra TEXT, fecha_recoleccion_prevista TEXT,
    superficie_cultivada_ha REAL, notas TEXT, kg_sembrados REAL, precio_kg_compra REAL,
    variedad_cod_siex TEXT);
"""

DECL = {
    'campana': CAMPANA, 'cultivo': 'Olivar', 'cultivo_iacs_cod': OLIVAR,
    'variedad': 'Cornicabra', 'fecha_siembra': '2010-03-01',
    'fecha_recoleccion_prevista': '2026-11-15', 'notas': 'Marco 8x8',
}


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def _db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _parcela(conn, pid, sup, uid=UID, expl=EXPL):
    conn.execute("INSERT INTO parcelas (id, user_id, explotacion_id, nombre_finca, superficie_ha)"
                 " VALUES (?,?,?,?,?)", (pid, uid, expl, f"Finca {pid}", sup))


def _grupo(conn, gid, parcelas, uid=UID, expl=EXPL, cultivo='Olivar'):
    conn.execute("INSERT INTO unidades_homogeneas (id, user_id, explotacion_id, nombre,"
                 " cultivo, campana) VALUES (?,?,?,?,?,?)",
                 (gid, uid, expl, f"Grupo {gid}", cultivo, CAMPANA))
    for pid in parcelas:
        conn.execute("INSERT INTO uhc_parcelas (uhc_id, parcela_id) VALUES (?,?)", (gid, pid))


def _declara(conn, pid, cod, sup, campana=CAMPANA):
    conn.execute("INSERT INTO cultivos_campana (parcela_id, explotacion_id, campana,"
                 " cultivo, cultivo_iacs_cod, superficie_cultivada_ha) VALUES (?,?,?,?,?,?)",
                 (pid, EXPL, campana, 'Previo', cod, sup))


def _filas(conn):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM cultivos_campana ORDER BY parcela_id, id")]


# ── A · lo obligatorio se sigue exigiendo ─────────────────────────────────────

def test_campos_obligatorios():
    print("A · campos obligatorios:")
    conn = _db()
    _parcela(conn, 1, 5.0)
    _grupo(conn, 100, [1])

    r = _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=100, cultivo=''))
    check("sin cultivo falla", r.get('error') and 'cultivo es obligatorio' in r['error'])

    r = _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=100, cultivo_iacs_cod=''))
    check("sin código IACS falla", r.get('error') and 'IACS' in r['error'])
    check("y lo justifica con SIEX", 'SIEX' in r['error'])

    check("no se ha escrito nada", _filas(conn) == [])
    conn.close()


def test_grupo_invalido():
    print("B · grupo no utilizable:")
    conn = _db()
    _parcela(conn, 1, 5.0)
    _grupo(conn, 100, [])                       # grupo sin parcelas
    r = _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=100))
    check("grupo vacío devuelve error", r.get('error') and 'no tiene parcelas' in r['error'])

    _grupo(conn, 200, [1], expl=OTRA_EXPL)      # grupo de otra finca
    r = _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=200))
    check("grupo de otra explotación devuelve error", r.get('error') is not None)

    r = _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=999))
    check("grupo inexistente devuelve error", r.get('error') is not None)
    check("no se ha escrito nada", _filas(conn) == [])
    conn.close()


# ── C · el caso normal ────────────────────────────────────────────────────────

def test_declara_todas_con_su_superficie():
    print("C · una declaración por parcela:")
    conn = _db()
    _parcela(conn, 1, 5.0)
    _parcela(conn, 2, 3.0)
    _parcela(conn, 3, 2.0)
    _grupo(conn, 100, [1, 2, 3])

    r = _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=100))
    conn.commit()
    filas = _filas(conn)

    check("se declaran las 3", r['creadas'] == 3 and len(filas) == 3)
    check("ninguna saltada ni rechazada", r['saltadas'] == 0 and r['rechazadas'] == 0)
    check("cada fila con la superficie de SU parcela",
          [f['superficie_cultivada_ha'] for f in filas] == [5.0, 3.0, 2.0])
    check("el cultivo y el código IACS se replican",
          all(f['cultivo'] == 'Olivar' and f['cultivo_iacs_cod'] == OLIVAR for f in filas))
    check("la variedad y las fechas se replican",
          all(f['variedad'] == 'Cornicabra' and f['fecha_siembra'] == '2010-03-01' for f in filas))
    check("todas en la campaña pedida", {f['campana'] for f in filas} == {CAMPANA})
    check("todas en la explotación activa", {f['explotacion_id'] for f in filas} == {EXPL})
    conn.close()


def test_kg_sembrados_se_reparten():
    print("D · kg_sembrados es absoluto y se reparte:")
    conn = _db()
    _parcela(conn, 1, 5.0)
    _parcela(conn, 2, 3.0)
    _parcela(conn, 3, 2.0)
    _grupo(conn, 100, [1, 2, 3])

    _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=100, kg_sembrados=1000))
    conn.commit()
    filas = _filas(conn)
    check("NO se replican los 1000 kg en cada parcela",
          [f['kg_sembrados'] for f in filas] != [1000, 1000, 1000])
    check("se reparten por superficie", [f['kg_sembrados'] for f in filas] == [500, 300, 200])
    check("la suma es exactamente lo tecleado",
          round(sum(f['kg_sembrados'] for f in filas), 2) == 1000)
    conn.close()


# ── E · nunca pisar lo ya declarado ───────────────────────────────────────────

def test_no_pisa_lo_existente():
    print("E · no pisa una declaración existente:")
    conn = _db()
    _parcela(conn, 1, 5.0)
    _parcela(conn, 2, 3.0)
    _grupo(conn, 100, [1, 2])
    _declara(conn, 1, OLIVAR, 5.0)              # la 1 ya está declarada de olivar

    r = _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=100))
    conn.commit()
    filas = _filas(conn)
    check("solo se crea la que faltaba", r['creadas'] == 1 and r['saltadas'] == 1)
    check("no se duplica la existente",
          len([f for f in filas if f['parcela_id'] == 1]) == 1)
    check("la existente queda intacta",
          [f for f in filas if f['parcela_id'] == 1][0]['cultivo'] == 'Previo')

    # Repetir la operación entera no debe crear nada más: es idempotente
    r2 = _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=100))
    conn.commit()
    check("repetirlo no crea nada", r2['creadas'] == 0 and r2['saltadas'] == 2)
    check("siguen siendo 2 filas", len(_filas(conn)) == 2)
    conn.close()


def test_otra_campana_no_cuenta():
    print("F · una declaración de OTRA campaña no bloquea:")
    conn = _db()
    _parcela(conn, 1, 5.0)
    _grupo(conn, 100, [1])
    _declara(conn, 1, OLIVAR, 5.0, campana='2024/2025')
    r = _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=100))
    conn.commit()
    check("se declara igualmente en la campaña nueva", r['creadas'] == 1)
    check("hay una fila por campaña", len(_filas(conn)) == 2)
    conn.close()


# ── G · el rechazo no tumba el grupo (al revés que en cosecha) ────────────────

def test_rechazo_aislado():
    print("G · una parcela sin sitio no tumba el grupo (criterio del rechazo por parcela):")
    conn = _db()
    _parcela(conn, 1, 5.0)
    _parcela(conn, 2, 3.0)
    _parcela(conn, 3, 2.0)
    _grupo(conn, 100, [1, 2, 3])
    # La 2 ya tiene toda su superficie ocupada por OTRO cultivo (viñedo)
    _declara(conn, 2, VINEDO, 3.0)

    r = _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=100))
    conn.commit()
    filas = _filas(conn)

    check("las otras dos SÍ se declaran", r['creadas'] == 2)
    check("la que no tiene sitio se rechaza sola", r['rechazadas'] == 1)
    check("y se explica por qué", r['motivos'] and 'superficie' in r['motivos'][0])
    check("no se escribe olivar en la parcela sin sitio",
          [f for f in filas if f['parcela_id'] == 2 and f['cultivo_iacs_cod'] == OLIVAR] == [])
    check("la declaración de viñedo queda intacta",
          [f for f in filas if f['parcela_id'] == 2][0]['superficie_cultivada_ha'] == 3.0)
    conn.close()


def test_superficie_parcial():
    print("H · queda sitio pero no entero:")
    conn = _db()
    _parcela(conn, 1, 10.0)
    _grupo(conn, 100, [1])
    _declara(conn, 1, VINEDO, 8.0)              # quedan 2 ha libres de 10

    r = _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=100))
    conn.commit()
    nueva = [f for f in _filas(conn) if f['cultivo_iacs_cod'] == OLIVAR][0]
    check("se declara", r['creadas'] == 1)
    check("solo la superficie que quedaba libre", nueva['superficie_cultivada_ha'] == 2.0)
    check("no se pasa de la superficie de la parcela",
          sum(f['superficie_cultivada_ha'] for f in _filas(conn)) == 10.0)
    conn.close()


def test_parcela_sin_superficie():
    print("I · parcela sin superficie registrada:")
    conn = _db()
    _parcela(conn, 1, None)
    _grupo(conn, 100, [1])
    r = _declarar_cultivo_grupo(conn, UID, EXPL, dict(DECL, uhc_id=100))
    conn.commit()
    check("se declara igualmente", r['creadas'] == 1)
    check("con superficie 0, no inventada", _filas(conn)[0]['superficie_cultivada_ha'] == 0)
    conn.close()


if __name__ == '__main__':
    print("\n=== 016 fase 4 — cultivo de campaña por grupo UHC ===\n")
    test_campos_obligatorios()
    test_grupo_invalido()
    test_declara_todas_con_su_superficie()
    test_kg_sembrados_se_reparten()
    test_no_pisa_lo_existente()
    test_otra_campana_no_cuenta()
    test_rechazo_aislado()
    test_superficie_parcial()
    test_parcela_sin_superficie()
    print("\nTODOS LOS TESTS OK\n")
