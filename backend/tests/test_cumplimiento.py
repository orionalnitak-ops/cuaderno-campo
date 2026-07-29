"""Test plano (sin pytest) del semáforo "Revisión del cuaderno".

Cubre las decisiones de riesgo de spec/features/011-revision-cuaderno/spec.md:
  - decisión 1: denominador dinámico (lo que no aplica no lastra el porcentaje)
  - decisión 3: nunca luz verde habiendo un crítico
  - decisión 4: sin compras registradas, el cruce se apaga en vez de dar rojo
  - decisión 6: nº de consultas constante, no crece con las parcelas
  - decisión 7: la normalización de productos va en Python, no en SQL
  - decisión 8: los registros con campaña vacía cuentan en la campaña activa
  - aislamiento entre agricultores (IDOR)

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_cumplimiento.py
"""
import datetime
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from blueprints.cumplimiento import (  # noqa: E402
    _color, _estado_iteaf, _norm, evaluar_cumplimiento,
)

UID = 1
OTRO_UID = 2
HOY = datetime.date(2026, 7, 29)
CAMPANA = '2025/2026'

# Columnas que el motor consulta. Se verifican al final de _db() para que, si
# alguien añade una columna al motor y no al esquema del test, esto falle
# ruidosamente en vez de dar un falso verde.
COLUMNAS_REQUERIDAS = {
    'explotacion':      'user_id, campana_activa',
    'parcelas':         'id, user_id, nombre_finca, activa',
    'tratamientos':     ('id, user_id, parcela_id, fecha_aplicacion, producto_comercial, '
                         'num_registro_mapa, equipo_id, aplicador_id, asesor_id, asesor, '
                         'campana, fecha_recoleccion_minima, deleted_at'),
    'equipos':          ('id, user_id, descripcion, tipo, marca, modelo, '
                         'num_registro_roma, fecha_iteaf'),
    'compras':          'id, user_id, producto, num_registro_mapa, deleted_at',
    'aplicadores':      'id, user_id, nombre, num_ropo, activo',
    'asesores':         'id, user_id, nombre, num_ropo, activo',
    'cultivos_campana': 'id, parcela_id, campana',
}

_SCHEMA = """
CREATE TABLE explotacion (user_id INTEGER, campana_activa TEXT);
CREATE TABLE parcelas (
    id INTEGER PRIMARY KEY, user_id INTEGER, nombre_finca TEXT, activa INTEGER DEFAULT 1);
CREATE TABLE tratamientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, parcela_id INTEGER,
    fecha_aplicacion TEXT, producto_comercial TEXT, num_registro_mapa TEXT,
    equipo_id INTEGER, aplicador_id INTEGER, asesor_id INTEGER, asesor TEXT,
    campana TEXT, fecha_recoleccion_minima TEXT, deleted_at TEXT);
CREATE TABLE equipos (
    id INTEGER PRIMARY KEY, user_id INTEGER, descripcion TEXT, tipo TEXT, marca TEXT,
    modelo TEXT, num_registro_roma TEXT, fecha_iteaf TEXT);
CREATE TABLE compras (
    id INTEGER PRIMARY KEY, user_id INTEGER, producto TEXT, num_registro_mapa TEXT,
    deleted_at TEXT);
CREATE TABLE aplicadores (
    id INTEGER PRIMARY KEY, user_id INTEGER, nombre TEXT, num_ropo TEXT, activo INTEGER DEFAULT 1);
CREATE TABLE asesores (
    id INTEGER PRIMARY KEY, user_id INTEGER, nombre TEXT, num_ropo TEXT, activo INTEGER DEFAULT 1);
CREATE TABLE cultivos_campana (
    id INTEGER PRIMARY KEY AUTOINCREMENT, parcela_id INTEGER, campana TEXT);
"""


def _db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.execute("INSERT INTO explotacion (user_id, campana_activa) VALUES (?,?)",
                 (UID, CAMPANA))
    for tabla, cols in COLUMNAS_REQUERIDAS.items():
        conn.execute(f"SELECT {cols} FROM {tabla} LIMIT 0")  # falla si falta alguna
    conn.commit()
    return conn


class _CountingConn:
    """Envuelve la conexión para contar consultas (test de regresión N+1)."""

    def __init__(self, conn):
        object.__setattr__(self, '_conn', conn)
        object.__setattr__(self, 'queries', 0)

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __setattr__(self, name, value):
        setattr(self._conn, name, value)  # p.ej. row_factory, que fija dicts()

    def cursor(self):
        object.__setattr__(self, 'queries', self.queries + 1)
        return self._conn.cursor()


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def bloque(res, bid):
    return next(b for b in res['bloques'] if b['id'] == bid)


def _parcela(conn, pid, uid=UID, nombre=None, activa=1):
    conn.execute("INSERT INTO parcelas (id, user_id, nombre_finca, activa) VALUES (?,?,?,?)",
                 (pid, uid, nombre or f"Finca {pid}", activa))


def _trat(conn, uid=UID, **kw):
    kw.setdefault('campana', CAMPANA)
    kw.setdefault('fecha_aplicacion', '2026-07-01')
    cols = ', '.join(['user_id'] + list(kw))
    ph = ', '.join(['?'] * (len(kw) + 1))
    conn.execute(f"INSERT INTO tratamientos ({cols}) VALUES ({ph})", (uid,) + tuple(kw.values()))


# ── A · _estado_iteaf (puro, sin BD) ──────────────────────────────────────────

def test_iteaf():
    print("A · _estado_iteaf:")
    for vacio in (None, '', '   '):
        check(f"fecha {vacio!r} -> sin_fecha", _estado_iteaf(vacio, HOY)[0] == 'sin_fecha')
    check("fecha ilegible -> no_valida (sin excepción)",
          _estado_iteaf('basura', HOY)[0] == 'no_valida')
    check("formato español se repara y se evalúa",
          _estado_iteaf('11/03/2020', HOY)[0] == 'caducada')
    check("hace 4 años -> caducada", _estado_iteaf('2022-07-29', HOY)[0] == 'caducada')
    check("caduca en 17 días -> proxima", _estado_iteaf('2023-08-15', HOY)[0] == 'proxima')
    check("caduca en 6 meses -> ok", _estado_iteaf('2024-01-01', HOY)[0] == 'ok')
    check("fecha futura -> fecha_futura", _estado_iteaf('2027-01-01', HOY)[0] == 'fecha_futura')
    # date.replace(year=) revienta con el 29 de febrero
    check("29-feb no lanza ValueError al sumar 3 años",
          _estado_iteaf('2024-02-29', HOY)[1] == datetime.date(2027, 2, 28))


# ── B · _norm (puro) ──────────────────────────────────────────────────────────

def test_norm():
    print("B · _norm:")
    check("mismo registro con formatos distintos", _norm('ES-25.123 ') == _norm('es25123'))
    # NFKD convierte 'º' en 'o', así que un "Nº" escrito a mano deja rastro:
    # el producto saldrá listado. Preferimos ese falso aviso a dar por
    # respaldado algo que no lo está.
    check("un 'Nº' escrito a mano NO se equipara al código limpio",
          _norm('Nº 25123') != _norm('25123'))
    # el caso que rompería si se normalizara con UPPER() en SQL: SQLite solo
    # mayusculiza ASCII, PostgreSQL es Unicode
    check("acentos: 'Añejo' == 'ANEJO'", _norm('Añejo') == _norm('ANEJO') == 'ANEJO')
    check("None -> cadena vacía", _norm(None) == '')
    check("solo signos -> cadena vacía", _norm('---') == '')


# ── C · cruce compras ↔ tratamientos ──────────────────────────────────────────

def test_trazabilidad():
    print("C · trazabilidad compras↔tratamientos:")
    conn = _db()
    _parcela(conn, 1)
    conn.executemany(
        "INSERT INTO compras (id, user_id, producto, num_registro_mapa, deleted_at) VALUES (?,?,?,?,?)", [
            (1, UID,      'Cobre Nordox',  'ES-25.123', None),
            (2, UID,      'Azufre Mojable', None,       None),
            (3, UID,      'Borrado',        '99999',    '2026-01-01'),  # baja lógica
            (4, OTRO_UID, 'Ajeno',          '77777',    None),          # de otro usuario
        ])
    _trat(conn, producto_comercial='Cobre Nordox', num_registro_mapa='es25123')  # por registro
    _trat(conn, producto_comercial='azufre mojable')                             # por nombre
    # compras admite 'ES-25.123' pero tratamientos exige el registro numérico:
    # los códigos no casan y solo salva el nombre
    _trat(conn, producto_comercial='COBRE NORDOX', num_registro_mapa='25123')
    _trat(conn, producto_comercial='Herbicida X', num_registro_mapa='11111')     # sin compra
    _trat(conn, producto_comercial='Producto Borrado', num_registro_mapa='99999')
    _trat(conn, producto_comercial='Producto Ajeno', num_registro_mapa='77777')
    _trat(conn, producto_comercial='Sin Campana', num_registro_mapa='11111', campana=None)
    _trat(conn, producto_comercial='Tratamiento Borrado', num_registro_mapa='11111',
          deleted_at='2026-01-01')
    conn.commit()

    b = bloque(evaluar_cumplimiento(conn, UID, hoy=HOY), 'trazabilidad_compras')
    etiquetas = {i['etiqueta'] for i in b['items']}

    check("cruce por nº registro con formato distinto -> respaldado",
          'Cobre Nordox' not in etiquetas)
    check("cruce por nombre cuando no hay registro -> respaldado",
          'azufre mojable' not in etiquetas)
    check("registros que no casan pero mismo nombre -> respaldado",
          'COBRE NORDOX' not in etiquetas)
    check("producto sin compra -> hallazgo crítico",
          'Herbicida X' in etiquetas and b['estado'] == 'critico')
    check("compra dada de baja NO respalda", 'Producto Borrado' in etiquetas)
    check("compra de otro usuario NO respalda", 'Producto Ajeno' in etiquetas)
    check("tratamiento borrado no genera hallazgo", 'Tratamiento Borrado' not in etiquetas)
    check("tratamiento con campaña vacía SÍ entra en el universo",
          'Sin Campana' in etiquetas and b['universo'] == 7)
    check("el copy dice 'no consta la compra', no 'no compraste'",
          all('no consta la compra' in i['detalle'] for i in b['items']))
    conn.close()


def test_sin_compras():
    print("C2 · usuario sin compras registradas:")
    conn = _db()
    _parcela(conn, 1)
    _trat(conn, parcela_id=1, producto_comercial='Herbicida X', num_registro_mapa='11111')
    conn.execute("INSERT INTO cultivos_campana (parcela_id, campana) VALUES (?,?)", (1, CAMPANA))
    conn.commit()

    res = evaluar_cumplimiento(conn, UID, hoy=HOY)
    b = bloque(res, 'trazabilidad_compras')
    check("sin compras -> el bloque no aplica", b['estado'] == 'no_aplica')
    check("sin compras -> ningún producto marcado en rojo", b['items'] == [])
    check("sin compras -> el peso 4 sale del denominador", res['puntuacion']['totales'] == 2)
    check("sin compras -> el porcentaje NO baja", res['porcentaje'] == 100)
    conn.close()


# ── D · puntuación y color ────────────────────────────────────────────────────

def test_color():
    print("D · color:")
    check("100 sin críticos -> verde", _color(100, 0) == 'verde')
    check("95 CON un crítico -> naranja (nunca verde)", _color(95, 1) == 'naranja')
    check("90 sin críticos -> verde", _color(90, 0) == 'verde')
    check("89 sin críticos -> naranja", _color(89, 0) == 'naranja')
    check("60 -> naranja", _color(60, 0) == 'naranja')
    check("59 -> rojo", _color(59, 0) == 'rojo')


def test_puntuacion():
    print("D2 · puntuación:")
    conn = _db()
    conn.commit()
    res = evaluar_cumplimiento(conn, UID, hoy=HOY)
    check("cuaderno vacío -> todo 'no aplica'", res['puntuacion']['totales'] == 0)
    check("cuaderno vacío -> 100% (no se castiga por no tener nada)",
          res['porcentaje'] == 100 and res['color'] == 'verde')

    # cuaderno impecable pero SIN equipos: los pesos de iteaf (4) y roma (3)
    # salen del denominador, y el resto (4+3+2) se puntúa al completo
    _parcela(conn, 1)
    conn.execute("INSERT INTO compras (id, user_id, producto) VALUES (?,?,?)", (1, UID, 'X'))
    conn.execute("INSERT INTO aplicadores (id, user_id, nombre, num_ropo) VALUES (?,?,?,?)",
                 (1, UID, 'Juan', 'ROPO-1'))
    conn.execute("INSERT INTO cultivos_campana (parcela_id, campana) VALUES (?,?)", (1, CAMPANA))
    _trat(conn, parcela_id=1, aplicador_id=1, producto_comercial='X')
    conn.commit()
    res = evaluar_cumplimiento(conn, UID, hoy=HOY)
    check("sin equipos -> iteaf no aplica", bloque(res, 'iteaf')['estado'] == 'no_aplica')
    check("sin equipos -> el denominador baja 4+3", res['puntuacion']['totales'] == 16 - 4 - 3)
    check("todo lo aplicable en orden -> 100% y verde",
          res['porcentaje'] == 100 and res['color'] == 'verde')

    # un equipo con ITEAF caducada y usado esta campaña -> crítico, nunca verde
    conn.execute("INSERT INTO equipos (id, user_id, descripcion, num_registro_roma, fecha_iteaf)"
                 " VALUES (?,?,?,?,?)", (5, UID, 'Atomizador', 'ROMA-1', '2020-03-11'))
    _trat(conn, parcela_id=1, equipo_id=5, aplicador_id=1, producto_comercial='X')
    conn.commit()
    res = evaluar_cumplimiento(conn, UID, hoy=HOY)
    check("ITEAF caducada en equipo usado -> crítico",
          bloque(res, 'iteaf')['estado'] == 'critico')
    check("con un crítico el semáforo NUNCA sale verde", res['color'] != 'verde')

    # el mismo equipo, si no se ha usado esta campaña, solo avisa
    conn.execute("DELETE FROM tratamientos")
    conn.commit()
    res = evaluar_cumplimiento(conn, UID, hoy=HOY)
    check("equipo caducado pero no usado -> solo aviso",
          bloque(res, 'iteaf')['estado'] == 'aviso')

    # equipo exento (mochila) fuera del universo de ITEAF y ROMA
    conn.execute("DELETE FROM equipos")
    conn.execute("INSERT INTO equipos (id, user_id, descripcion, tipo, fecha_iteaf)"
                 " VALUES (?,?,?,?,?)", (6, UID, 'Mochila de sulfatar', 'mochila', ''))
    conn.commit()
    res = evaluar_cumplimiento(conn, UID, hoy=HOY)
    check("mochila exenta -> iteaf no aplica", bloque(res, 'iteaf')['estado'] == 'no_aplica')
    check("mochila exenta -> roma no aplica", bloque(res, 'roma')['estado'] == 'no_aplica')
    conn.close()


def test_informativos():
    print("D3 · los informativos no puntúan:")
    conn = _db()
    _parcela(conn, 1)
    conn.execute("INSERT INTO cultivos_campana (parcela_id, campana) VALUES (?,?)", (1, CAMPANA))
    _trat(conn, parcela_id=1, producto_comercial='X', fecha_aplicacion='2026-01-01',
          fecha_recoleccion_minima='2026-08-02')
    conn.commit()
    res = evaluar_cumplimiento(conn, UID, hoy=HOY)

    check("plazo de seguridad próximo aparece", bloque(res, 'plazo_seguridad')['afectados'] == 1)
    check("plazo de seguridad marcado como informativo",
          bloque(res, 'plazo_seguridad')['informativo'] is True)
    check("parcela sin movimiento aparece", bloque(res, 'registro_reciente')['afectados'] == 1)
    check("los informativos pesan 0",
          bloque(res, 'plazo_seguridad')['peso'] == 0
          and bloque(res, 'registro_reciente')['peso'] == 0)
    check("los informativos no bajan el porcentaje", res['porcentaje'] == 100)
    check("los informativos no cuentan como pendientes", res['resumen']['avisos'] == 0)
    conn.close()


def test_ropo():
    print("D4 · ROPO:")
    conn = _db()
    conn.executemany("INSERT INTO aplicadores (id, user_id, nombre, num_ropo) VALUES (?,?,?,?)",
                     [(1, UID, 'Juan Con Ropo', 'ROPO-1'), (2, UID, 'Luis Sin Ropo', '')])
    conn.execute("INSERT INTO asesores (id, user_id, nombre, num_ropo) VALUES (?,?,?,?)",
                 (3, UID, 'Ana Sin Ropo', None))
    _trat(conn, aplicador_id=2, producto_comercial='X')          # firma -> crítico
    _trat(conn, asesor='Técnico a mano', producto_comercial='X')  # legacy -> crítico
    conn.commit()
    res = evaluar_cumplimiento(conn, UID, hoy=HOY)
    b = bloque(res, 'ropo')
    sev = {i['etiqueta']: i['severidad'] for i in b['items']}

    check("universo = fichas activas + asesores a mano", b['universo'] == 4)
    check("aplicador sin ROPO que firma -> crítico",
          sev.get('Aplicador: Luis Sin Ropo') == 'critico')
    check("asesor sin ROPO que no ha firmado -> solo aviso",
          sev.get('Asesor: Ana Sin Ropo') == 'aviso')
    check("asesor de texto libre -> crítico (sin ficha, sin ROPO)",
          sev.get('Asesor: Técnico a mano') == 'critico')
    check("aplicador con ROPO no aparece", 'Aplicador: Juan Con Ropo' not in sev)
    conn.close()


# ── E · aislamiento entre agricultores ────────────────────────────────────────

def test_aislamiento():
    print("E · aislamiento entre agricultores:")
    conn = _db()
    # todo lo del usuario legítimo, impecable
    _parcela(conn, 1)
    conn.execute("INSERT INTO cultivos_campana (parcela_id, campana) VALUES (?,?)", (1, CAMPANA))
    conn.execute("INSERT INTO compras (id, user_id, producto, num_registro_mapa) VALUES (?,?,?,?)",
                 (1, UID, 'Cobre', '111'))
    conn.execute("INSERT INTO equipos (id, user_id, descripcion, num_registro_roma, fecha_iteaf)"
                 " VALUES (?,?,?,?,?)", (1, UID, 'Atomizador', 'ROMA-1', '2025-01-01'))
    conn.execute("INSERT INTO aplicadores (id, user_id, nombre, num_ropo) VALUES (?,?,?,?)",
                 (1, UID, 'Juan', 'ROPO-1'))
    _trat(conn, parcela_id=1, producto_comercial='Cobre', num_registro_mapa='111',
          equipo_id=1, aplicador_id=1)

    # el otro usuario, hecho un desastre en las 8 tablas
    conn.execute("INSERT INTO explotacion (user_id, campana_activa) VALUES (?,?)",
                 (OTRO_UID, CAMPANA))
    _parcela(conn, 99, uid=OTRO_UID, nombre='Finca Ajena')
    conn.execute("INSERT INTO equipos (id, user_id, descripcion, num_registro_roma, fecha_iteaf)"
                 " VALUES (?,?,?,?,?)", (99, OTRO_UID, 'Tractor Ajeno', '', '2010-01-01'))
    conn.execute("INSERT INTO aplicadores (id, user_id, nombre, num_ropo) VALUES (?,?,?,?)",
                 (99, OTRO_UID, 'Ajeno', ''))
    conn.execute("INSERT INTO asesores (id, user_id, nombre, num_ropo) VALUES (?,?,?,?)",
                 (98, OTRO_UID, 'Asesora Ajena', ''))
    conn.execute("INSERT INTO compras (id, user_id, producto) VALUES (?,?,?)",
                 (99, OTRO_UID, 'Compra Ajena'))
    _trat(conn, uid=OTRO_UID, parcela_id=99, producto_comercial='Producto Ajeno',
          asesor='Asesor Ajeno A Mano', fecha_recoleccion_minima='2026-08-01')
    conn.commit()

    res = evaluar_cumplimiento(conn, UID, hoy=HOY)
    texto = repr(res)
    for ajeno in ('Ajena', 'Ajeno'):
        check(f"nada de '{ajeno}' aparece en el resultado", ajeno not in texto)
    check("universo de equipos = solo los míos", bloque(res, 'iteaf')['universo'] == 1)
    check("universo de personas = solo las mías", bloque(res, 'ropo')['universo'] == 1)
    check("universo de parcelas = solo las mías", bloque(res, 'cultivo_campana')['universo'] == 1)
    check("universo de productos = solo los míos",
          bloque(res, 'trazabilidad_compras')['universo'] == 1)
    check("el desastre ajeno no me baja el porcentaje", res['porcentaje'] == 100)
    conn.close()


# ── F · regresión N+1 ─────────────────────────────────────────────────────────

def test_sin_n_mas_1():
    print("F · nº de consultas constante:")

    def _consultas(n_parcelas):
        raw = _db()
        for i in range(1, n_parcelas + 1):
            _parcela(raw, i)
            _trat(raw, parcela_id=i, producto_comercial=f'Producto {i}')
        raw.commit()
        conn = _CountingConn(raw)
        evaluar_cumplimiento(conn, UID, hoy=HOY)
        n = conn.queries
        raw.close()
        return n

    q3, q60 = _consultas(3), _consultas(60)
    check(f"3 parcelas y 60 parcelas cuestan lo mismo ({q3} consultas)", q3 == q60)
    check("son 11 consultas fijas", q3 == 11)


def run():
    print("test_cumplimiento:")
    test_iteaf()
    test_norm()
    test_trazabilidad()
    test_sin_compras()
    test_color()
    test_puntuacion()
    test_informativos()
    test_ropo()
    test_aislamiento()
    test_sin_n_mas_1()
    print("test_cumplimiento: TODO OK")


if __name__ == '__main__':
    run()
