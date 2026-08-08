"""Test plano (sin pytest) del plan de abonado por grupo UHC.

Cubre la fase 2 de spec/features/016-uhc-en-cosecha-abonado-cultivo/plan.md.

El plan de abonado es el caso FÁCIL de la feature: todos sus campos son por
hectárea (N/P/K necesarios, dosis recomendada, rendimiento esperado), así que al
expandir el grupo se replican tal cual. Aquí no se reparte nada — eso llega en
cosecha (fase 3) y cultivo campaña (fase 4).

Lo que sí hay que blindar es el aislamiento: cada rama de grupo es un fan-out, y
un filtro que falte escribe en la finca equivocada (lección de la feature 013).

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_uhc_abonado.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from blueprints.fertilizacion import (  # noqa: E402
    _insert_abonado, _parcelas_uhc, _validate_abonado,
)

UID = 1
OTRO_UID = 2
EXPL = 10
OTRA_EXPL = 20

_SCHEMA = """
CREATE TABLE parcelas (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER,
    nombre_finca TEXT, superficie_ha REAL);
CREATE TABLE unidades_homogeneas (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER,
    nombre TEXT, cultivo TEXT, campana TEXT, deleted_at TIMESTAMP);
CREATE TABLE uhc_parcelas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, uhc_id INTEGER, parcela_id INTEGER);
CREATE TABLE abonado (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, explotacion_id INTEGER,
    parcela_id INTEGER, parcela_etiqueta TEXT, cultivo TEXT, cultivo_anterior TEXT,
    rendimiento_esperado_kg_ha REAL, n_necesario_kg_ha REAL, p_necesario_kg_ha REAL,
    k_necesario_kg_ha REAL, fecha_preparacion TEXT, datos_suelo TEXT,
    abono_recomendado TEXT, dosis_recomendada_kg_ha REAL, notas TEXT, campana TEXT,
    deleted_at TIMESTAMP);
"""

PLAN = {
    'cultivo': 'Olivar', 'cultivo_anterior': 'Olivar',
    'rendimiento_esperado_kg_ha': 3500,
    'fecha_preparacion': '2026-02-10',
    'datos_suelo': 'Análisis de 2025: pH 7,8 · MO 1,4 %',
    'n_necesario_kg_ha': 60, 'p_necesario_kg_ha': 30, 'k_necesario_kg_ha': 45,
    'abono_recomendado': 'NPK 15-15-15', 'dosis_recomendada_kg_ha': 400,
    'notas': 'Aplicar antes de la floración', 'campana': '2025/2026',
}


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def _db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _parcela(conn, pid, uid=UID, expl=EXPL, sup=2.5):
    conn.execute("INSERT INTO parcelas (id, user_id, explotacion_id, nombre_finca, superficie_ha)"
                 " VALUES (?,?,?,?,?)", (pid, uid, expl, f"Finca {pid}", sup))


def _grupo(conn, gid, parcelas, uid=UID, expl=EXPL, borrado=None):
    conn.execute("INSERT INTO unidades_homogeneas (id, user_id, explotacion_id, nombre,"
                 " cultivo, campana, deleted_at) VALUES (?,?,?,?,?,?,?)",
                 (gid, uid, expl, f"Grupo {gid}", 'Olivar', '2025/2026', borrado))
    for pid in parcelas:
        conn.execute("INSERT INTO uhc_parcelas (uhc_id, parcela_id) VALUES (?,?)", (gid, pid))


def _abonados(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM abonado ORDER BY parcela_id")]


# ── A · la validación admite grupo igual que parcela ──────────────────────────

def test_validacion_acepta_grupo():
    print("A · validación:")
    solo_grupo = dict(PLAN, uhc_id=3)
    check("con grupo y sin parcela es válido", _validate_abonado(solo_grupo) is None)
    solo_parcela = dict(PLAN, parcela_id=1)
    check("con parcela y sin grupo es válido", _validate_abonado(solo_parcela) is None)
    err = _validate_abonado(dict(PLAN))
    check("sin parcela ni grupo falla", err and 'Parcela o Grupo UHC' in err)
    err = _validate_abonado({'parcela_id': 1})
    check("sigue exigiendo el resto de campos", err and 'Cultivo' in err)
    err = _validate_abonado(dict(PLAN, parcela_id=1, fecha_preparacion='2099-01-01'))
    check("la fecha futura sigue rechazándose", err and 'futura' in err)


# ── B · el fan-out: un plan por parcela, con los mismos kg/ha ─────────────────

def test_expande_a_una_fila_por_parcela():
    print("B · un plan por parcela:")
    conn = _db()
    for pid in (1, 2, 3):
        _parcela(conn, pid, sup=pid)          # superficies distintas: 1, 2 y 3 ha
    _grupo(conn, 100, [1, 2, 3])

    parcelas = _parcelas_uhc(conn, 100, UID, EXPL)
    check("el grupo devuelve sus 3 parcelas", len(parcelas) == 3)

    c = conn.cursor()
    ids = [_insert_abonado(c, UID, PLAN, p['id'], p['nombre_finca'], EXPL) for p in parcelas]
    conn.commit()

    filas = _abonados(conn)
    check("se crean 3 planes", len(filas) == 3 and len(set(ids)) == 3)
    check("uno por parcela", [f['parcela_id'] for f in filas] == [1, 2, 3])
    check("la etiqueta es la de SU parcela",
          [f['parcela_etiqueta'] for f in filas] == ['Finca 1', 'Finca 2', 'Finca 3'])
    # Lo importante: los kg/ha NO se reparten, se replican. 60 kg N/ha son 60 en
    # una parcela de 1 ha y en una de 3 ha.
    check("el N por ha es idéntico en las 3", {f['n_necesario_kg_ha'] for f in filas} == {60})
    check("el P por ha es idéntico", {f['p_necesario_kg_ha'] for f in filas} == {30})
    check("el K por ha es idéntico", {f['k_necesario_kg_ha'] for f in filas} == {45})
    check("la dosis por ha es idéntica", {f['dosis_recomendada_kg_ha'] for f in filas} == {400})
    check("el rendimiento esperado es idéntico",
          {f['rendimiento_esperado_kg_ha'] for f in filas} == {3500})
    check("los datos de suelo se replican", all(f['datos_suelo'] == PLAN['datos_suelo'] for f in filas))
    check("todas quedan en la explotación activa", {f['explotacion_id'] for f in filas} == {EXPL})
    check("todas quedan en el usuario correcto", {f['user_id'] for f in filas} == {UID})
    conn.close()


# ── C · aislamiento: el fan-out no puede escapar de la finca ──────────────────

def test_aislamiento():
    print("C · aislamiento (feature 013):")
    conn = _db()
    _parcela(conn, 1)
    _parcela(conn, 2, expl=OTRA_EXPL)          # parcela de la OTRA finca
    _grupo(conn, 100, [1, 2])                  # grupo mal formado: mezcla fincas

    parcelas = _parcelas_uhc(conn, 100, UID, EXPL)
    check("solo se expande la parcela de la finca activa",
          [p['id'] for p in parcelas] == [1])

    _grupo(conn, 200, [1], expl=OTRA_EXPL)
    check("un grupo de otra finca no devuelve nada",
          _parcelas_uhc(conn, 200, UID, EXPL) == [])

    _parcela(conn, 3, uid=OTRO_UID)
    _grupo(conn, 300, [3], uid=OTRO_UID)
    check("un grupo de otro usuario no devuelve nada",
          _parcelas_uhc(conn, 300, UID, EXPL) == [])

    _grupo(conn, 400, [1], borrado='2026-01-01')
    check("un grupo borrado no devuelve nada",
          _parcelas_uhc(conn, 400, UID, EXPL) == [])

    check("un grupo inexistente no devuelve nada",
          _parcelas_uhc(conn, 999, UID, EXPL) == [])

    # El `uhc_id` llega del payload: si no es un número se trata como grupo
    # inexistente en vez de reventar la consulta con un 500 (Security Review #51).
    check("un id de grupo como texto numérico sí funciona",
          [p['id'] for p in _parcelas_uhc(conn, '100', UID, EXPL)] == [1])
    check("un id de grupo no numérico no devuelve nada",
          _parcelas_uhc(conn, 'DROP TABLE parcelas', UID, EXPL) == [])
    check("un id de grupo que es una lista no revienta",
          _parcelas_uhc(conn, [1, 2], UID, EXPL) == [])
    check("un id de grupo None no revienta",
          _parcelas_uhc(conn, None, UID, EXPL) == [])
    check("y las parcelas siguen ahí", len(_abonados(conn)) == 0
          and conn.execute("SELECT COUNT(*) FROM parcelas").fetchone()[0] == 3)
    conn.close()


# ── D · el grupo vacío no escribe nada ────────────────────────────────────────

def test_grupo_sin_parcelas():
    print("D · grupo sin parcelas:")
    conn = _db()
    _grupo(conn, 100, [])
    check("devuelve lista vacía -> la ruta responde 400 y no inserta",
          _parcelas_uhc(conn, 100, UID, EXPL) == [])
    check("no hay planes escritos", _abonados(conn) == [])
    conn.close()


if __name__ == '__main__':
    print("\n=== 016 fase 2 — plan de abonado por grupo UHC ===\n")
    test_validacion_acepta_grupo()
    test_expande_a_una_fila_por_parcela()
    test_aislamiento()
    test_grupo_sin_parcelas()
    print("\nTODOS LOS TESTS OK\n")
