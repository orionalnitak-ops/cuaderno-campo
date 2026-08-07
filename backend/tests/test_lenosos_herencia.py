"""Test plano (sin pytest) de la herencia del cultivo en parcelas de leñoso.

Cubre los criterios de aceptación de spec/features/014-cultivos-lenosos-herencia/spec.md.

El caso que lo origina: Lourdes, con 50+ parcelas de olivar y viña, veía el aviso
"Sin cultivo declarado" en TODAS ellas, campaña tras campaña. Un leñoso es
permanente: se declara una vez y se hereda.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_lenosos_herencia.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helpers import (  # noqa: E402
    CULTIVOS_LENOSOS_IACS, es_cultivo_lenoso, heredar_cultivos_lenosos,
)

UID = 1
OTRO_UID = 2
EXPL = 10
OTRA_EXPL = 20
ANTERIOR = '2024/2025'
ACTUAL = '2025/2026'

OLIVAR = '1820'
VINEDO = '1711'
CEBADA = '430'

_SCHEMA = """
CREATE TABLE parcelas (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER,
    nombre_finca TEXT, activa INTEGER DEFAULT 1);
CREATE TABLE cultivos_campana (
    id INTEGER PRIMARY KEY AUTOINCREMENT, parcela_id INTEGER, explotacion_id INTEGER,
    campana TEXT, cultivo TEXT, cultivo_iacs_cod TEXT, variedad TEXT,
    fecha_siembra TEXT, fecha_recoleccion_prevista TEXT,
    superficie_cultivada_ha REAL, notas TEXT,
    kg_sembrados REAL, precio_kg_compra REAL);
"""


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def _db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _parcela(conn, pid, uid=UID, expl=EXPL, nombre=None):
    conn.execute("INSERT INTO parcelas (id, user_id, explotacion_id, nombre_finca)"
                 " VALUES (?,?,?,?)", (pid, uid, expl, nombre or f"Finca {pid}"))


def _cultivo(conn, pid, campana, cod, expl=EXPL, **kw):
    kw.setdefault('cultivo', 'Olivar' if cod == OLIVAR else 'Cultivo')
    kw.setdefault('variedad', 'Cornicabra')
    kw.setdefault('superficie_cultivada_ha', 2.5)
    cols = ['parcela_id', 'explotacion_id', 'campana', 'cultivo_iacs_cod'] + list(kw)
    vals = [pid, expl, campana, cod] + list(kw.values())
    ph = ', '.join(['?'] * len(cols))
    conn.execute(f"INSERT INTO cultivos_campana ({', '.join(cols)}) VALUES ({ph})", vals)


def _filas(conn, pid, campana):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM cultivos_campana WHERE parcela_id=? AND campana=?", (pid, campana))]


# ── A · el catálogo de leñosos ────────────────────────────────────────────────

def test_catalogo():
    print("A · catálogo de códigos IACS leñosos:")
    # Los 12 del grupo 'Leñosos' de CULTIVOS_IACS (frontend/screens_parcelas.jsx).
    check("olivar (1820) es leñoso", es_cultivo_lenoso(OLIVAR))
    check("viñedo vinificación (1711) es leñoso", es_cultivo_lenoso(VINEDO))
    check("viñedo uva de mesa (1712) es leñoso", es_cultivo_lenoso('1712'))
    check("almendro (1710) es leñoso", es_cultivo_lenoso('1710'))
    check("cebada (430) NO es leñoso", not es_cultivo_lenoso(CEBADA))
    check("girasol (701) NO es leñoso", not es_cultivo_lenoso('701'))
    check("barbecho (980) NO es leñoso", not es_cultivo_lenoso('980'))
    check("None no revienta", not es_cultivo_lenoso(None))
    check("cadena vacía no revienta", not es_cultivo_lenoso(''))
    check("acepta int además de str", es_cultivo_lenoso(1820))
    check("tolera espacios", es_cultivo_lenoso(' 1820 '))
    check("son los 12 del grupo Leñosos", len(CULTIVOS_LENOSOS_IACS) == 12)


# ── B · la herencia (criterios 1, 2, 8) ───────────────────────────────────────

def test_hereda_lenoso():
    print("B · el leñoso se hereda de la campaña anterior:")
    conn = _db()
    _parcela(conn, 1, nombre='El Olivar Grande')
    _cultivo(conn, 1, ANTERIOR, OLIVAR, cultivo='Olivar', variedad='Cornicabra',
             superficie_cultivada_ha=3.2, fecha_siembra='1998-03-01',
             fecha_recoleccion_prevista='2024-11-15')
    conn.commit()

    n = heredar_cultivos_lenosos(conn, UID, ACTUAL, EXPL)
    conn.commit()

    filas = _filas(conn, 1, ACTUAL)
    check("hereda 1 parcela", n == 1)
    check("crea la fila en la campaña actual", len(filas) == 1)
    f = filas[0]
    check("hereda el código IACS", f['cultivo_iacs_cod'] == OLIVAR)
    check("hereda el nombre del cultivo", f['cultivo'] == 'Olivar')
    check("hereda la variedad", f['variedad'] == 'Cornicabra')
    check("hereda la superficie cultivada", f['superficie_cultivada_ha'] == 3.2)
    check("hereda la explotación de la parcela", f['explotacion_id'] == EXPL)
    # Criterio 8: las fechas son propias de cada campaña, no se arrastran.
    check("NO hereda la fecha de siembra", not f['fecha_siembra'])
    check("NO hereda la recolección prevista", not f['fecha_recoleccion_prevista'])
    conn.close()


def test_herbaceo_no_se_hereda():
    print("C · el herbáceo sigue siendo obligación del agricultor (criterio 4):")
    conn = _db()
    _parcela(conn, 1, nombre='La Cebada')
    _cultivo(conn, 1, ANTERIOR, CEBADA, cultivo='Cebada')
    conn.commit()

    n = heredar_cultivos_lenosos(conn, UID, ACTUAL, EXPL)
    conn.commit()

    check("no hereda nada", n == 0)
    check("la parcela sigue sin cultivo en la campaña actual", _filas(conn, 1, ACTUAL) == [])
    conn.close()


# ── C · idempotencia y respeto al dato del agricultor (criterios 5 y 6) ───────

def test_idempotente():
    print("D · idempotencia (criterio 5):")
    conn = _db()
    _parcela(conn, 1)
    _cultivo(conn, 1, ANTERIOR, OLIVAR)
    conn.commit()

    heredar_cultivos_lenosos(conn, UID, ACTUAL, EXPL)
    conn.commit()
    n2 = heredar_cultivos_lenosos(conn, UID, ACTUAL, EXPL)
    conn.commit()

    check("la segunda pasada no hereda nada", n2 == 0)
    check("no duplica filas", len(_filas(conn, 1, ACTUAL)) == 1)
    conn.close()


def test_no_pisa_lo_declarado():
    print("E · nunca pisa lo que escribió el agricultor (criterio 6):")
    conn = _db()
    _parcela(conn, 1)
    _cultivo(conn, 1, ANTERIOR, OLIVAR, cultivo='Olivar')
    # Lourdes arrancó el olivar y plantó cebada: manda lo suyo.
    _cultivo(conn, 1, ACTUAL, CEBADA, cultivo='Cebada')
    conn.commit()

    n = heredar_cultivos_lenosos(conn, UID, ACTUAL, EXPL)
    conn.commit()

    filas = _filas(conn, 1, ACTUAL)
    check("no hereda encima", n == 0)
    check("sigue habiendo una sola fila", len(filas) == 1)
    check("y es la que puso ella", filas[0]['cultivo_iacs_cod'] == CEBADA)
    conn.close()


def test_hereda_de_la_mas_reciente():
    print("F · hereda de la campaña más reciente, no de la más vieja:")
    conn = _db()
    _parcela(conn, 1)
    _cultivo(conn, 1, '2022/2023', OLIVAR, cultivo='Olivar', variedad='Picual')
    _cultivo(conn, 1, ANTERIOR, VINEDO, cultivo='Viñedo', variedad='Tempranillo')
    conn.commit()

    heredar_cultivos_lenosos(conn, UID, ACTUAL, EXPL)
    conn.commit()

    f = _filas(conn, 1, ACTUAL)[0]
    check("hereda el viñedo de 2024/2025, no el olivar de 2022/2023",
          f['cultivo_iacs_cod'] == VINEDO)
    check("con su variedad", f['variedad'] == 'Tempranillo')
    conn.close()


def test_no_hereda_del_futuro():
    print("G · no hereda de una campaña posterior:")
    conn = _db()
    _parcela(conn, 1)
    _cultivo(conn, 1, '2026/2027', OLIVAR)
    conn.commit()

    n = heredar_cultivos_lenosos(conn, UID, ACTUAL, EXPL)
    conn.commit()

    check("no hereda hacia atrás en el tiempo", n == 0)
    check("no crea fila", _filas(conn, 1, ACTUAL) == [])
    conn.close()


# ── D · aislamiento (criterio 7) ──────────────────────────────────────────────

def test_aislamiento():
    print("H · aislamiento por usuario y explotación (criterio 7):")
    conn = _db()
    _parcela(conn, 1, uid=OTRO_UID, expl=OTRA_EXPL)   # parcela de otro agricultor
    _cultivo(conn, 1, ANTERIOR, OLIVAR, expl=OTRA_EXPL)
    _parcela(conn, 2, uid=UID, expl=OTRA_EXPL)        # mía, pero de otra finca
    _cultivo(conn, 2, ANTERIOR, OLIVAR, expl=OTRA_EXPL)
    conn.commit()

    n = heredar_cultivos_lenosos(conn, UID, ACTUAL, EXPL)
    conn.commit()

    check("no toca nada de otra explotación ni de otro usuario", n == 0)
    check("la parcela ajena sigue intacta", _filas(conn, 1, ACTUAL) == [])
    check("mi parcela de otra finca sigue intacta", _filas(conn, 2, ACTUAL) == [])
    conn.close()


def test_coste_constante():
    print("I · el coste no crece con el nº de parcelas:")

    class _Counting:
        def __init__(self, conn):
            object.__setattr__(self, '_conn', conn)
            object.__setattr__(self, 'queries', 0)

        def __getattr__(self, name):
            return getattr(self._conn, name)

        def __setattr__(self, name, value):
            setattr(self._conn, name, value)

        def cursor(self):
            object.__setattr__(self, 'queries', self.queries + 1)
            return self._conn.cursor()

        def execute(self, *a, **kw):
            object.__setattr__(self, 'queries', self.queries + 1)
            return self._conn.execute(*a, **kw)

    def _consultas(n_parcelas):
        raw = _db()
        for i in range(1, n_parcelas + 1):
            _parcela(raw, i)
            _cultivo(raw, i, ANTERIOR, OLIVAR)
        raw.commit()
        conn = _Counting(raw)
        heredar_cultivos_lenosos(conn, UID, ACTUAL, EXPL)
        raw.commit()
        n = conn.queries
        raw.close()
        return n

    q3, q60 = _consultas(3), _consultas(60)
    check(f"3 parcelas y 60 parcelas cuestan lo mismo ({q3} consultas)", q3 == q60)


def run():
    print("test_lenosos_herencia:")
    test_catalogo()
    test_hereda_lenoso()
    test_herbaceo_no_se_hereda()
    test_idempotente()
    test_no_pisa_lo_declarado()
    test_hereda_de_la_mas_reciente()
    test_no_hereda_del_futuro()
    test_aislamiento()
    test_coste_constante()
    print("test_lenosos_herencia: TODO OK")


if __name__ == '__main__':
    run()
