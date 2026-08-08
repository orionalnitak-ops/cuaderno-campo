"""Test plano (sin pytest) de la cosecha por grupo UHC.

Cubre la fase 3 de spec/features/016-uhc-en-cosecha-abonado-cultivo/plan.md.

Es el caso DELICADO de la feature 016. La producción y la superficie cosechada son
cantidades ABSOLUTAS, no por hectárea: replicarlas en las parcelas del grupo
multiplicaría la cosecha por el nº de parcelas. Aquí se comprueba que:

  - cada fila lleva la superficie REAL de su parcela (no se estima lo que ya se sabe),
  - la producción se reparte proporcional y la suma cuadra exacta,
  - el rendimiento kg/ha sale coherente,
  - y el plazo de seguridad de UNA parcela tumba el grupo entero.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_uhc_cosecha.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from blueprints.fertilizacion import _parcelas_uhc  # noqa: E402
from blueprints.labores import _insert_cosecha, _plazo_seguridad_bloquea  # noqa: E402
from helpers import repartir_por_superficie  # noqa: E402

UID = 1
EXPL = 10
OTRA_EXPL = 20
HOY = '2026-09-15'

_SCHEMA = """
CREATE TABLE parcelas (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER,
    nombre_finca TEXT, superficie_ha REAL);
CREATE TABLE unidades_homogeneas (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER,
    nombre TEXT, cultivo TEXT, campana TEXT, deleted_at TIMESTAMP);
CREATE TABLE uhc_parcelas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, uhc_id INTEGER, parcela_id INTEGER);
CREATE TABLE tratamientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, explotacion_id INTEGER,
    parcela_id INTEGER, producto_comercial TEXT, fecha_recoleccion_minima TEXT,
    deleted_at TIMESTAMP);
CREATE TABLE cosecha (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, explotacion_id INTEGER,
    parcela_id INTEGER, parcela_etiqueta TEXT, fecha_inicio TEXT, fecha_fin TEXT,
    cultivo TEXT, variedad TEXT, superficie_cosechada_ha REAL,
    produccion_total_valor REAL, produccion_total_unidad TEXT, rendimiento_kg_ha REAL,
    destino TEXT, comprador TEXT, precio_unidad REAL, notas TEXT, campana TEXT);
"""

COSECHA = {
    'fecha_inicio': HOY, 'fecha_fin': '2026-09-30',
    'cultivo': 'Olivar', 'variedad': 'Cornicabra',
    'produccion_total_unidad': 'kg',
    'destino': 'Almazara', 'comprador': 'Cooperativa de Valdepeñas',
    'precio_unidad': 0.45, 'notas': 'Recolección mecanizada', 'campana': '2025/2026',
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


def _grupo(conn, gid, parcelas, uid=UID, expl=EXPL):
    conn.execute("INSERT INTO unidades_homogeneas (id, user_id, explotacion_id, nombre,"
                 " cultivo, campana) VALUES (?,?,?,?,?,?)",
                 (gid, uid, expl, f"Grupo {gid}", 'Olivar', '2025/2026'))
    for pid in parcelas:
        conn.execute("INSERT INTO uhc_parcelas (uhc_id, parcela_id) VALUES (?,?)", (gid, pid))


def _tratamiento(conn, pid, producto, hasta, expl=EXPL, borrado=None):
    conn.execute("INSERT INTO tratamientos (user_id, explotacion_id, parcela_id,"
                 " producto_comercial, fecha_recoleccion_minima, deleted_at)"
                 " VALUES (?,?,?,?,?,?)", (UID, expl, pid, producto, hasta, borrado))


def _cosechas(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM cosecha ORDER BY parcela_id")]


def _guardar_grupo(conn, gid, total):
    """Reproduce lo que hace la rama de grupo del POST /api/cosecha."""
    parcelas = _parcelas_uhc(conn, gid, UID, EXPL)
    reparto = repartir_por_superficie(total, parcelas)
    c = conn.cursor()
    for p in parcelas:
        _insert_cosecha(c, UID, COSECHA, p['id'], p['nombre_finca'], EXPL,
                        sup=p.get('superficie_ha') or 0, prod=reparto.get(p['id'], 0))
    conn.commit()
    return parcelas


# ── A · _parcelas_uhc ahora trae la superficie ────────────────────────────────

def test_parcelas_uhc_trae_superficie():
    print("A · el grupo devuelve la superficie:")
    conn = _db()
    _parcela(conn, 1, 5.0)
    _parcela(conn, 2, 3.0)
    _grupo(conn, 100, [1, 2])
    parcelas = _parcelas_uhc(conn, 100, UID, EXPL)
    check("dos parcelas", len(parcelas) == 2)
    check("con superficie_ha", [p['superficie_ha'] for p in parcelas] == [5.0, 3.0])
    check("y con nombre_finca, que usan los 4 módulos que ya existían",
          all(p['nombre_finca'] for p in parcelas))
    conn.close()


# ── B · el fan-out reparte en vez de replicar ─────────────────────────────────

def test_reparte_no_replica():
    print("B · la producción se reparte, no se replica:")
    conn = _db()
    _parcela(conn, 1, 5.0)
    _parcela(conn, 2, 3.0)
    _parcela(conn, 3, 2.0)
    _grupo(conn, 100, [1, 2, 3])

    _guardar_grupo(conn, 100, 3000)          # 10 ha en total -> 300 kg/ha
    filas = _cosechas(conn)

    check("una cosecha por parcela", len(filas) == 3)
    check("NO se replica el total en cada parcela",
          [f['produccion_total_valor'] for f in filas] != [3000, 3000, 3000])
    check("se reparte por superficie",
          [f['produccion_total_valor'] for f in filas] == [1500, 900, 600])
    check("la suma es exactamente lo tecleado",
          round(sum(f['produccion_total_valor'] for f in filas), 2) == 3000)
    check("cada fila lleva la superficie REAL de su parcela",
          [f['superficie_cosechada_ha'] for f in filas] == [5.0, 3.0, 2.0])
    check("el rendimiento kg/ha es el mismo en las 3 (grupo homogéneo)",
          {f['rendimiento_kg_ha'] for f in filas} == {300.0})
    check("los campos comunes sí se replican",
          all(f['comprador'] == 'Cooperativa de Valdepeñas' and f['cultivo'] == 'Olivar'
              for f in filas))
    check("la etiqueta es la de SU parcela",
          [f['parcela_etiqueta'] for f in filas] == ['Finca 1', 'Finca 2', 'Finca 3'])
    check("todas en la explotación activa", {f['explotacion_id'] for f in filas} == {EXPL})
    conn.close()


def test_suma_cuadra_con_decimales():
    print("C · la suma cuadra con decimales feos:")
    conn = _db()
    for pid, sup in [(1, 1.0), (2, 1.0), (3, 1.0)]:
        _parcela(conn, pid, sup)
    _grupo(conn, 100, [1, 2, 3])
    _guardar_grupo(conn, 100, 1000)          # 1000/3 = 333,33...
    filas = _cosechas(conn)
    check("la suma sigue siendo 1000 exacto",
          round(sum(f['produccion_total_valor'] for f in filas), 2) == 1000)
    check("la última absorbe el redondeo",
          filas[-1]['produccion_total_valor'] != filas[0]['produccion_total_valor'])
    conn.close()


def test_sin_produccion_no_revienta():
    print("D · grupo sin producción tecleada:")
    conn = _db()
    _parcela(conn, 1, 4.0)
    _parcela(conn, 2, 6.0)
    _grupo(conn, 100, [1, 2])
    _guardar_grupo(conn, 100, None)
    filas = _cosechas(conn)
    check("se crean las dos filas igualmente", len(filas) == 2)
    check("con producción 0", [f['produccion_total_valor'] for f in filas] == [0, 0])
    check("la superficie sí se guarda", [f['superficie_cosechada_ha'] for f in filas] == [4.0, 6.0])
    check("el rendimiento es 0, no un error", {f['rendimiento_kg_ha'] for f in filas} == {0.0})
    conn.close()


# ── E · el plazo de seguridad tumba el grupo entero ───────────────────────────

def test_plazo_seguridad():
    print("E · plazo de seguridad (criterio 5):")
    conn = _db()
    _parcela(conn, 1, 5.0)
    _parcela(conn, 2, 3.0)
    _parcela(conn, 3, 2.0)
    _grupo(conn, 100, [1, 2, 3])
    parcelas = _parcelas_uhc(conn, 100, UID, EXPL)
    ids = [p['id'] for p in parcelas]

    check("sin tratamientos no bloquea",
          _plazo_seguridad_bloquea(conn, ids, UID, EXPL, HOY, parcelas) is None)

    # Plazo ya vencido: la fecha mínima de recolección es ANTERIOR a la cosecha
    _tratamiento(conn, 2, 'Vencido S.L.', '2026-08-01')
    check("un plazo ya vencido no bloquea",
          _plazo_seguridad_bloquea(conn, ids, UID, EXPL, HOY, parcelas) is None)

    # Plazo vivo en UNA sola parcela de las tres
    _tratamiento(conn, 2, 'Cobre 50', '2026-10-01')
    err = _plazo_seguridad_bloquea(conn, ids, UID, EXPL, HOY, parcelas)
    check("una sola parcela en plazo tumba el grupo entero", err is not None)
    check("el mensaje nombra la parcela", 'Finca 2' in err)
    check("el mensaje nombra el producto", 'Cobre 50' in err)
    check("el mensaje dice hasta cuándo", '2026-10-01' in err)
    check("no menciona las parcelas que sí se podían cosechar",
          'Finca 1' not in err and 'Finca 3' not in err)

    # Y no se ha escrito NADA: el rechazo es previo a cualquier INSERT
    check("no se escribió ninguna cosecha", _cosechas(conn) == [])

    # Un tratamiento borrado no cuenta
    conn.execute("DELETE FROM tratamientos WHERE producto_comercial='Cobre 50'")
    _tratamiento(conn, 1, 'Borrado S.A.', '2026-10-01', borrado='2026-01-01')
    check("un tratamiento borrado no bloquea",
          _plazo_seguridad_bloquea(conn, ids, UID, EXPL, HOY, parcelas) is None)

    # Un tratamiento de OTRA explotación no cuenta
    _tratamiento(conn, 1, 'Otra finca S.A.', '2026-10-01', expl=OTRA_EXPL)
    check("un tratamiento de otra explotación no bloquea",
          _plazo_seguridad_bloquea(conn, ids, UID, EXPL, HOY, parcelas) is None)
    conn.close()


def test_plazo_seguridad_parcela_suelta():
    print("F · el mensaje de una sola parcela no cambia:")
    conn = _db()
    _parcela(conn, 1, 5.0)
    _tratamiento(conn, 1, 'Cobre 50', '2026-10-01')
    err = _plazo_seguridad_bloquea(conn, [1], UID, EXPL, HOY)
    check("bloquea igual que antes", err is not None)
    check("mantiene el texto de siempre", 'plazo de seguridad no vencido' in err)
    check("sin fecha de cosecha no puede comprobar nada",
          _plazo_seguridad_bloquea(conn, [1], UID, EXPL, None) is None)
    check("sin parcelas no revienta",
          _plazo_seguridad_bloquea(conn, [], UID, EXPL, HOY) is None)
    check("acepta un id que viene como texto del payload",
          _plazo_seguridad_bloquea(conn, ['1'], UID, EXPL, HOY) is not None)
    # Fail-closed: si el id no es identificable, no se puede AFIRMAR que el plazo
    # haya vencido. Un control legal que falla en abierto da falsa seguridad.
    check("un id no numérico BLOQUEA, no deja pasar",
          _plazo_seguridad_bloquea(conn, ['no soy un id'], UID, EXPL, HOY) is not None)
    conn.close()


if __name__ == '__main__':
    print("\n=== 016 fase 3 — cosecha por grupo UHC ===\n")
    test_parcelas_uhc_trae_superficie()
    test_reparte_no_replica()
    test_suma_cuadra_con_decimales()
    test_sin_produccion_no_revienta()
    test_plazo_seguridad()
    test_plazo_seguridad_parcela_suelta()
    print("\nTODOS LOS TESTS OK\n")
