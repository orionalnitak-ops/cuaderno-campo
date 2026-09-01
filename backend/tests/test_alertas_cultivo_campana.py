"""Test plano (sin pytest) del aviso "Sin cultivo de campaña" en Inicio (ia.py).

Reporte real de Lourdes (01-sept-2026): tres parcelas con cultivo YA declarado
(una anual recién creada, un olivar y una viña heredados de la campaña
anterior) seguían saliendo en "Recordatorios" como si no lo tuvieran.

Causa: `_generar_alertas` (que genera esos recordatorios) solo corre en el
login y, a diferencia de la "Revisión del cuaderno" (cumplimiento.py) y del
listado de cultivos (parcelas.py GET), nunca llamaba a
`heredar_cultivos_lenosos` — así que un olivar/viña heredado de la campaña
anterior seguía marcado como pendiente. Y crear un cultivo (individual o por
grupo UHC) no borraba el aviso ya generado, así que quedaba vivo hasta el
siguiente login aunque el cultivo ya estuviera declarado.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_alertas_cultivo_campana.py
"""
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from blueprints import ia as ia_module  # noqa: E402

UID = 1
EXPL = 10
ANTERIOR = '2024/2025'
ACTUAL = '2025/2026'

OLIVAR = '1820'
VINEDO = '1711'
CEBADA = '430'

_SCHEMA = """
CREATE TABLE explotacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, campana_activa TEXT);
CREATE TABLE parcelas (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER,
    nombre_finca TEXT, activa INTEGER DEFAULT 1);
CREATE TABLE cultivos_campana (
    id INTEGER PRIMARY KEY AUTOINCREMENT, parcela_id INTEGER, explotacion_id INTEGER,
    campana TEXT, cultivo TEXT, cultivo_iacs_cod TEXT, variedad TEXT,
    fecha_siembra TEXT, fecha_recoleccion_prevista TEXT,
    superficie_cultivada_ha REAL, notas TEXT,
    kg_sembrados REAL, precio_kg_compra REAL);
CREATE TABLE tratamientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, parcela_id INTEGER,
    explotacion_id INTEGER, fecha_aplicacion TEXT, producto_comercial TEXT,
    fecha_recoleccion_minima TEXT, deleted_at TEXT);
CREATE TABLE ia_alertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, tipo TEXT,
    parcela_id INTEGER, modulo TEXT, mensaje TEXT, expira_en TEXT);
"""


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def _fresh_db_path():
    fd, path = tempfile.mkstemp(suffix='.sqlite')
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()
    return path


def _conn(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _parcela(conn, pid, nombre, uid=UID, expl=EXPL):
    conn.execute("INSERT INTO parcelas (id, user_id, explotacion_id, nombre_finca)"
                 " VALUES (?,?,?,?)", (pid, uid, expl, nombre))


def _cultivo(conn, pid, campana, cod, cultivo='Cultivo', expl=EXPL):
    conn.execute("""INSERT INTO cultivos_campana
        (parcela_id, explotacion_id, campana, cultivo, cultivo_iacs_cod, superficie_cultivada_ha)
        VALUES (?,?,?,?,?,2.5)""", (pid, expl, campana, cultivo, cod))


def _alertas_sin_cultivo(conn, uid=UID):
    return [r['parcela_id'] for r in conn.execute(
        "SELECT parcela_id FROM ia_alertas WHERE user_id=? AND tipo='sin_cultivo_campana'",
        (uid,))]


def test_hereda_lenosos_antes_de_avisar():
    print("A · leñoso heredado de la campaña anterior no genera aviso:")
    path = _fresh_db_path()
    setup = _conn(path)
    setup.execute("INSERT INTO explotacion (id, user_id, campana_activa) VALUES (?,?,?)",
                  (EXPL, UID, ACTUAL))
    _parcela(setup, 1, 'Minas Luis')   # olivar, declarado solo en la campaña anterior
    _parcela(setup, 2, 'Moros Viña')   # viña, ídem
    _parcela(setup, 3, 'Sin cultivo')  # de verdad sin nada, en ninguna campaña
    _cultivo(setup, 1, ANTERIOR, OLIVAR, 'Olivar')
    _cultivo(setup, 2, ANTERIOR, VINEDO, 'Viñedo')
    setup.commit()
    setup.close()

    ia_module.get_db = lambda: _conn(path)
    ia_module._generar_alertas(UID)

    verify = _conn(path)
    pendientes = _alertas_sin_cultivo(verify)
    check("Minas Luis (olivar heredado) NO sale como pendiente", 1 not in pendientes)
    check("Moros Viña (viña heredada) NO sale como pendiente", 2 not in pendientes)
    check("la parcela sin ningún cultivo SÍ sale como pendiente", 3 in pendientes)
    verify.close()
    os.remove(path)


def test_declarar_cultivo_borra_el_aviso_ya_generado():
    print("B · declarar un cultivo borra el aviso 'sin cultivo' que ya existía:")
    path = _fresh_db_path()
    setup = _conn(path)
    setup.execute("INSERT INTO explotacion (id, user_id, campana_activa) VALUES (?,?,?)",
                  (EXPL, UID, ACTUAL))
    _parcela(setup, 1, 'Mollejón Ines')
    setup.commit()
    setup.close()

    ia_module.get_db = lambda: _conn(path)
    ia_module._generar_alertas(UID)
    antes = _conn(path)
    check("al principio, sin cultivo, sí sale pendiente", 1 in _alertas_sin_cultivo(antes))
    antes.close()

    # El agricultor declara la cebada de esta campaña (equivalente a lo que hacen
    # las rutas POST /api/cultivos-campana tras este fix).
    tras_declarar = _conn(path)
    _cultivo(tras_declarar, 1, ACTUAL, CEBADA, 'Cebada')
    tras_declarar.execute(
        "DELETE FROM ia_alertas WHERE user_id=? AND tipo=? AND parcela_id=?",
        (UID, 'sin_cultivo_campana', 1))
    tras_declarar.commit()
    tras_declarar.close()

    despues = _conn(path)
    check("tras declararlo, ya no sale pendiente", 1 not in _alertas_sin_cultivo(despues))
    despues.close()
    os.remove(path)


if __name__ == '__main__':
    test_hereda_lenosos_antes_de_avisar()
    test_declarar_cultivo_borra_el_aviso_ya_generado()
    print("\nTodos los tests pasaron.")
