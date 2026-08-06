"""Test plano (sin pytest) del aislamiento entre explotaciones del mismo usuario.

Cubre spec/features/013-aislamiento-por-explotacion/spec.md. Decisión de producto:
cada explotación es un cuaderno TOTALMENTE independiente. El usuario con varias
explotaciones es un "asesor": cada finca tiene sus parcelas, tratamientos,
equipos, facturas, aplicadores y asesores. Nada se comparte.

Frontera doble, y las dos importan:
  - `user_id` separa clientes distintos. Saltárselo es una brecha de seguridad
    (ya cubierto por test_cumplimiento.py).
  - `explotacion_id` separa cuadernos del MISMO cliente. Saltárselo mete datos
    de otra finca en un cuaderno legal.

Este fichero cubre la segunda. Nace en rojo a propósito: `evaluar_cumplimiento()`
todavía no acepta `explotacion_id`.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_aislamiento_explotacion.py
"""
import datetime
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from blueprints.cumplimiento import evaluar_cumplimiento  # noqa: E402

UID = 1
EXPL_A = 10          # explotación activa en los tests
EXPL_B = 20          # la otra finca del mismo usuario: NADA suyo debe aparecer
HOY = datetime.date(2026, 7, 29)
CAMPANA_A = '2025/2026'
CAMPANA_B = '2024/2025'   # distinta a propósito: destapa el bug de la campaña

# Tablas que deben llevar `explotacion_id` tras la migración de la Fase 1, con
# las columnas que el motor consulta. Si alguien añade una tabla de datos del
# agricultor y olvida la columna, este mapa es donde se nota.
COLUMNAS_REQUERIDAS = {
    'explotacion':      'id, user_id, campana_activa',
    'parcelas':         'id, user_id, explotacion_id, nombre_finca, activa',
    'tratamientos':     ('id, user_id, explotacion_id, parcela_id, fecha_aplicacion, '
                         'producto_comercial, num_registro_mapa, equipo_id, aplicador_id, '
                         'asesor_id, asesor, campana, fecha_recoleccion_minima, deleted_at'),
    'equipos':          ('id, user_id, explotacion_id, descripcion, tipo, marca, modelo, '
                         'num_registro_roma, fecha_iteaf'),
    'compras':          'id, user_id, explotacion_id, producto, num_registro_mapa, deleted_at',
    'aplicadores':      'id, user_id, explotacion_id, nombre, num_ropo, activo',
    'asesores':         'id, user_id, explotacion_id, nombre, num_ropo, activo',
    'cultivos_campana': 'id, explotacion_id, parcela_id, campana',
}

_SCHEMA = """
CREATE TABLE explotacion (
    id INTEGER PRIMARY KEY, user_id INTEGER, campana_activa TEXT);
CREATE TABLE parcelas (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER,
    nombre_finca TEXT, activa INTEGER DEFAULT 1);
CREATE TABLE tratamientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, explotacion_id INTEGER,
    parcela_id INTEGER, fecha_aplicacion TEXT, producto_comercial TEXT,
    num_registro_mapa TEXT, equipo_id INTEGER, aplicador_id INTEGER, asesor_id INTEGER,
    asesor TEXT, campana TEXT, fecha_recoleccion_minima TEXT, deleted_at TEXT);
CREATE TABLE equipos (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER, descripcion TEXT,
    tipo TEXT, marca TEXT, modelo TEXT, num_registro_roma TEXT, fecha_iteaf TEXT);
CREATE TABLE compras (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER, producto TEXT,
    num_registro_mapa TEXT, deleted_at TEXT);
CREATE TABLE aplicadores (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER, nombre TEXT,
    num_ropo TEXT, activo INTEGER DEFAULT 1);
CREATE TABLE asesores (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER, nombre TEXT,
    num_ropo TEXT, activo INTEGER DEFAULT 1);
CREATE TABLE cultivos_campana (
    id INTEGER PRIMARY KEY AUTOINCREMENT, explotacion_id INTEGER, parcela_id INTEGER,
    campana TEXT);
"""


def _db():
    """Usuario único con DOS explotaciones. Mismo dueño, cuadernos separados."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.executemany(
        "INSERT INTO explotacion (id, user_id, campana_activa) VALUES (?,?,?)",
        [(EXPL_A, UID, CAMPANA_A), (EXPL_B, UID, CAMPANA_B)])
    for tabla, cols in COLUMNAS_REQUERIDAS.items():
        conn.execute(f"SELECT {cols} FROM {tabla} LIMIT 0")  # falla si falta alguna
    conn.commit()
    return conn


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def bloque(res, bid):
    return next(b for b in res['bloques'] if b['id'] == bid)


def etiquetas(res):
    """Todas las etiquetas y detalles que la pantalla le enseña al agricultor."""
    out = []
    for b in res['bloques']:
        for i in b['items']:
            out.append(f"{i.get('etiqueta', '')} {i.get('detalle', '')}")
    return ' | '.join(out)


def _ins(conn, tabla, expl, **kw):
    kw['user_id'] = UID
    kw['explotacion_id'] = expl
    cols = ', '.join(kw)
    ph = ', '.join(['?'] * len(kw))
    conn.execute(f"INSERT INTO {tabla} ({cols}) VALUES ({ph})", tuple(kw.values()))


def _cultivo(conn, expl, parcela_id, campana):
    conn.execute("INSERT INTO cultivos_campana (explotacion_id, parcela_id, campana)"
                 " VALUES (?,?,?)", (expl, parcela_id, campana))


def _eval(conn, expl=EXPL_A):
    return evaluar_cumplimiento(conn, UID, hoy=HOY, explotacion_id=expl)


# ── Escenario compartido ──────────────────────────────────────────────────────
# Todo lo de la explotación B lleva 'FINCA-B' en algún campo de texto, así que
# cualquier fuga se ve de un vistazo en el JSON que recibe el frontend.

def _escenario():
    conn = _db()

    # Parcelas: 1 en A (con cultivo declarado), 1 en B (sin declarar → generaría
    # un item en el bloque cultivo_campana si se colara)
    _ins(conn, 'parcelas', EXPL_A, id=1, nombre_finca='Finca A')
    _ins(conn, 'parcelas', EXPL_B, id=2, nombre_finca='FINCA-B sin cultivo')
    _cultivo(conn, EXPL_A, 1, CAMPANA_A)

    # Equipos sin ROMA ni ITEAF, pero USADOS (si no, _es_plantilla los excluye)
    _ins(conn, 'equipos', EXPL_A, id=1, descripcion='Pulverizador A',
         tipo='Pulverizador', fecha_iteaf='2019-01-01')
    _ins(conn, 'equipos', EXPL_B, id=2, descripcion='Pulverizador FINCA-B',
         tipo='Pulverizador', fecha_iteaf='2019-01-01')

    # Personas sin ROPO
    _ins(conn, 'aplicadores', EXPL_A, id=1, nombre='Aplicador A', activo=1)
    _ins(conn, 'aplicadores', EXPL_B, id=2, nombre='Aplicador FINCA-B', activo=1)
    _ins(conn, 'asesores', EXPL_B, id=2, nombre='Asesor FINCA-B', activo=1)

    # Compras: solo en A, para que el cruce de trazabilidad esté encendido en A.
    # (Sin ninguna compra el bloque se apaga y no probaría nada.)
    _ins(conn, 'compras', EXPL_A, id=1, producto='Cobre A', num_registro_mapa='11111')

    # Tratamientos: uno por explotación, cada uno con producto sin respaldo de
    # compra, equipo y persona propios, y un plazo de seguridad en curso.
    _ins(conn, 'tratamientos', EXPL_A, parcela_id=1, campana=CAMPANA_A,
         fecha_aplicacion='2026-07-01', producto_comercial='Azufre A',
         num_registro_mapa='99999', equipo_id=1, aplicador_id=1,
         fecha_recoleccion_minima='2026-08-01')
    _ins(conn, 'tratamientos', EXPL_B, parcela_id=2, campana=CAMPANA_B,
         fecha_aplicacion='2026-07-02', producto_comercial='Azufre FINCA-B',
         num_registro_mapa='88888', equipo_id=2, aplicador_id=2, asesor_id=2,
         asesor='Asesor a mano FINCA-B', fecha_recoleccion_minima='2026-08-02')

    # Parcela de B sin movimiento reciente (bloque registro_reciente)
    _ins(conn, 'tratamientos', EXPL_B, parcela_id=2, campana=CAMPANA_B,
         fecha_aplicacion='2026-01-01', producto_comercial='Viejo FINCA-B')

    conn.commit()
    return conn


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_nada_de_la_otra_explotacion_se_cuela():
    print("A · la Revisión solo habla de la explotación activa:")
    conn = _escenario()
    res = _eval(conn, EXPL_A)
    texto = etiquetas(res)
    check("ningún item menciona la otra finca (reporte de Lourdes)",
          'FINCA-B' not in texto)
    check("la parcela de la otra finca no sale sin cultivo declarado",
          bloque(res, 'cultivo_campana')['universo'] == 1)
    check("solo cuenta el equipo propio en ITEAF",
          bloque(res, 'iteaf')['universo'] == 1)
    check("solo cuenta el equipo propio en ROMA",
          bloque(res, 'roma')['universo'] == 1)
    check("solo cuentan las personas propias en ROPO",
          bloque(res, 'ropo')['universo'] == 1)
    check("solo cuenta el producto aplicado propio en trazabilidad",
          bloque(res, 'trazabilidad_compras')['universo'] == 1)
    check("solo un plazo de seguridad en curso, el propio",
          len(bloque(res, 'plazo_seguridad')['items']) == 1)
    check("ninguna parcela ajena sin movimiento reciente",
          len(bloque(res, 'registro_reciente')['items']) == 0)


def test_simetria_la_otra_explotacion_tambien_esta_aislada():
    print("B · el aislamiento va en los dos sentidos:")
    conn = _escenario()
    res = _eval(conn, EXPL_B)
    texto = etiquetas(res)
    check("desde B no se ve nada de A", 'Finca A' not in texto and ' A ' not in texto)
    check("B ve su propio equipo", bloque(res, 'iteaf')['universo'] == 1)
    check("B ve su parcela sin cultivo declarado",
          len(bloque(res, 'cultivo_campana')['items']) == 1)
    check("B, sin ninguna compra registrada, apaga el cruce de trazabilidad",
          bloque(res, 'trazabilidad_compras')['estado'] == 'no_aplica')
    check("B ve al asesor escrito a mano y a los suyos sin ROPO",
          bloque(res, 'ropo')['universo'] == 3)


def test_campana_de_la_explotacion_activa():
    """Bug de cumplimiento.py:217. `one(SELECT campana_activa WHERE user_id=?)`
    devuelve una fila ARBITRARIA cuando el usuario tiene varias explotaciones, así
    que la Revisión puede evaluarse contra la campaña de la finca equivocada. En
    silencio, que es lo peor: los números salen y son mentira."""
    print("C · la campaña sale de la explotación activa, no de una fila cualquiera:")
    conn = _escenario()
    check("con A activa usa la campaña de A", _eval(conn, EXPL_A)['campana'] == CAMPANA_A)
    check("con B activa usa la campaña de B", _eval(conn, EXPL_B)['campana'] == CAMPANA_B)


def test_explotacion_sin_datos_no_hereda_nada():
    print("D · una explotación recién creada nace con el cuaderno vacío:")
    conn = _escenario()
    res = _eval(conn, 30)   # explotación que no tiene ni una fila
    check("no hereda equipos, personas ni parcelas de las hermanas",
          all(b['estado'] == 'no_aplica' for b in res['bloques'] if not b['informativo']))
    check("sin nada pendiente, no inventa avisos", res['resumen']['criticos'] == 0)


def main():
    print("\n=== Aislamiento entre explotaciones (feature 013) ===\n")
    for fn in (test_nada_de_la_otra_explotacion_se_cuela,
               test_simetria_la_otra_explotacion_tambien_esta_aislada,
               test_campana_de_la_explotacion_activa,
               test_explotacion_sin_datos_no_hereda_nada):
        fn()
        print()
    print("=== TODO OK ===")


if __name__ == '__main__':
    main()
