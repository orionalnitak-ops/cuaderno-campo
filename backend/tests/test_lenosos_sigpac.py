"""Test plano (sin pytest) de la declaración de leñosos a partir del uso SIGPAC.

Cubre spec/features/015-declarar-lenosos-desde-sigpac/.

El caso: Lourdes tiene 23 parcelas de olivar, viñedo y almendro y ninguna con el
cultivo declarado, así que las 23 le salen marcadas en la Revisión. El dato de
que son olivar ya lo tiene la app en `parcelas.uso_sigpac`, que viene del
registro oficial. Se le propone y ella confirma.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_lenosos_sigpac.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helpers import (  # noqa: E402
    CULTIVOS_LENOSOS_IACS, USO_SIGPAC_LENOSO, codigo_uso_sigpac,
    declarar_cultivos_lote, sugerencias_lenosos,
)

UID = 1
OTRO_UID = 2
EXPL = 10
OTRA_EXPL = 20
CAMPANA = '2025/2026'

_SCHEMA = """
CREATE TABLE explotacion (
    id INTEGER PRIMARY KEY, user_id INTEGER, campana_activa TEXT, orden INTEGER DEFAULT 0);
CREATE TABLE parcelas (
    id INTEGER PRIMARY KEY, user_id INTEGER, explotacion_id INTEGER,
    nombre_finca TEXT, uso_sigpac TEXT, superficie_ha REAL, activa INTEGER DEFAULT 1);
CREATE TABLE cultivos_campana (
    id INTEGER PRIMARY KEY AUTOINCREMENT, parcela_id INTEGER, explotacion_id INTEGER,
    campana TEXT, cultivo TEXT, cultivo_iacs_cod TEXT, variedad TEXT,
    fecha_siembra TEXT, fecha_recoleccion_prevista TEXT,
    superficie_cultivada_ha REAL, notas TEXT, kg_sembrados REAL, precio_kg_compra REAL);
"""

# Los 10 valores DISTINTOS que hay hoy en la base de datos de producción. El mismo
# uso aparece escrito de tres formas, y hay vacíos y un NULL.
USOS_REALES = [
    ('OV - OLIVAR', 'OV'), ('TA - TIERRAS ARABLES', 'TA'), ('VI - VIÑEDO', 'VI'),
    ('', ''), ('TA-TIERRA ARABLE', 'TA'), ('VO - VIÑEDO - OLIVAR', 'VO'),
    ('OV-OLIVAR', 'OV'), ('VI-VIÑEDO', 'VI'), ('FY - FRUTALES', 'FY'), (None, ''),
]


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def _db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    # La campaña sale SIEMPRE de la explotación, nunca de quien llama.
    conn.execute("INSERT INTO explotacion (id, user_id, campana_activa) VALUES (?,?,?)",
                 (EXPL, UID, CAMPANA))
    conn.execute("INSERT INTO explotacion (id, user_id, campana_activa) VALUES (?,?,?)",
                 (OTRA_EXPL, OTRO_UID, CAMPANA))
    return conn


def _parcela(conn, pid, uso, uid=UID, expl=EXPL, sup=2.0, nombre=None):
    conn.execute("INSERT INTO parcelas (id, user_id, explotacion_id, nombre_finca,"
                 " uso_sigpac, superficie_ha) VALUES (?,?,?,?,?,?)",
                 (pid, uid, expl, nombre or f"Finca {pid}", uso, sup))


def _grupo(res, uso):
    return next((g for g in res['grupos'] if g['uso'] == uso), None)


def _filas(conn, pid=None):
    sql = "SELECT * FROM cultivos_campana"
    args = ()
    if pid:
        sql += " WHERE parcela_id=?"; args = (pid,)
    return [dict(r) for r in conn.execute(sql, args)]


# ── A · el código de uso SIGPAC ───────────────────────────────────────────────

def test_codigo_uso():
    print("A · extraer el código de uso, con los valores reales de la BD:")
    for valor, esperado in USOS_REALES:
        check(f"{valor!r} -> {esperado!r}", codigo_uso_sigpac(valor) == esperado)
    # El que más peligro tiene: VO no puede confundirse con VI ni con OV.
    check("'VO - VIÑEDO - OLIVAR' NO es VI", codigo_uso_sigpac('VO - VIÑEDO - OLIVAR') != 'VI')
    check("'VO - VIÑEDO - OLIVAR' NO es OV", codigo_uso_sigpac('VO - VIÑEDO - OLIVAR') != 'OV')
    check("minúsculas también valen", codigo_uso_sigpac('ov - olivar') == 'OV')
    check("espacios delante no molestan", codigo_uso_sigpac('  OV - OLIVAR') == 'OV')
    check("basura sin formato -> vacío", codigo_uso_sigpac('cualquier cosa') == '')
    check("una sola letra -> vacío", codigo_uso_sigpac('O') == '')
    check("un número -> vacío", codigo_uso_sigpac(123) == '')

    print("A bis · qué usos son leñosos:")
    check("OV es leñoso y se propone solo", USO_SIGPAC_LENOSO.get('OV') == '1820')
    for u in ('VI', 'FY', 'VO'):
        check(f"{u} es leñoso pero hay que preguntar",
              u in USO_SIGPAC_LENOSO and USO_SIGPAC_LENOSO[u] is None)
    check("TA no es leñoso", 'TA' not in USO_SIGPAC_LENOSO)
    check("el código propuesto para OV está en el catálogo de leñosos",
          '1820' in CULTIVOS_LENOSOS_IACS)


# ── B · las sugerencias ───────────────────────────────────────────────────────

def test_sugerencias():
    print("B · qué parcelas se proponen:")
    conn = _db()
    _parcela(conn, 1, 'OV - OLIVAR', nombre='El Olivar')
    _parcela(conn, 2, 'OV-OLIVAR')                    # otra forma de escribirlo
    _parcela(conn, 3, 'VI - VIÑEDO')
    _parcela(conn, 4, 'VO - VIÑEDO - OLIVAR')
    _parcela(conn, 5, 'FY - FRUTALES')
    _parcela(conn, 6, 'TA - TIERRAS ARABLES')         # herbáceo: no se toca
    _parcela(conn, 7, 'TA-TIERRA ARABLE')             # idem, otra forma
    _parcela(conn, 8, '')                             # sin uso: no se adivina
    _parcela(conn, 9, None)
    conn.commit()

    res = sugerencias_lenosos(conn, UID, EXPL)
    usos = {g['uso'] for g in res['grupos']}
    check("propone OV, VI, VO y FY", usos == {'OV', 'VI', 'VO', 'FY'})
    check("NO propone tierras arables", 'TA' not in usos)
    check("las dos formas de OV caen en el mismo grupo", len(_grupo(res, 'OV')['parcelas']) == 2)
    check("OV no necesita pregunta", _grupo(res, 'OV')['necesita_pregunta'] is False)
    check("OV propone olivar 1820", _grupo(res, 'OV')['propuesta']['cod'] == '1820')
    for u in ('VI', 'VO', 'FY'):
        check(f"{u} necesita pregunta", _grupo(res, u)['necesita_pregunta'] is True)
        check(f"{u} no trae propuesta cerrada", _grupo(res, u)['propuesta'] is None)
    check("VI ofrece vinificación y uva de mesa",
          {o['cod'] for o in _grupo(res, 'VI')['opciones']} == {'1711', '1712'})
    check("FY ofrece el almendro entre sus opciones",
          '1710' in {o['cod'] for o in _grupo(res, 'FY')['opciones']})
    check("la parcela lleva su superficie, para repartirla",
          _grupo(res, 'OV')['parcelas'][0]['superficie_ha'] == 2.0)
    conn.close()


def test_sugerencias_no_repite_lo_declarado():
    print("C · no propone lo que ya está declarado:")
    conn = _db()
    _parcela(conn, 1, 'OV - OLIVAR')
    _parcela(conn, 2, 'OV - OLIVAR')
    conn.execute("INSERT INTO cultivos_campana (parcela_id, explotacion_id, campana,"
                 " cultivo, cultivo_iacs_cod) VALUES (?,?,?,?,?)",
                 (1, EXPL, CAMPANA, 'Olivar', '1820'))
    conn.commit()

    res = sugerencias_lenosos(conn, UID, EXPL)
    ids = [p['id'] for p in _grupo(res, 'OV')['parcelas']]
    check("la ya declarada no aparece", 1 not in ids)
    check("la pendiente sí", ids == [2])
    conn.close()


def test_sugerencias_aislamiento():
    print("D · las sugerencias no cruzan usuario ni explotación:")
    conn = _db()
    _parcela(conn, 1, 'OV - OLIVAR', uid=OTRO_UID, expl=OTRA_EXPL)
    _parcela(conn, 2, 'OV - OLIVAR', uid=UID, expl=OTRA_EXPL)
    _parcela(conn, 3, 'OV - OLIVAR', uid=UID, expl=EXPL)
    conn.commit()

    res = sugerencias_lenosos(conn, UID, EXPL)
    ids = [p['id'] for p in _grupo(res, 'OV')['parcelas']]
    check("solo la parcela de mi explotación", ids == [3])
    conn.close()


def test_sin_explotacion():
    print("D bis · sin explotación no se propone ni se escribe nada:")
    conn = _db()
    _parcela(conn, 1, 'OV - OLIVAR')
    conn.commit()

    res = sugerencias_lenosos(conn, UID, None)
    check("no propone nada", res['grupos'] == [])

    r = declarar_cultivos_lote(conn, UID, None,
                               [{'parcela_id': 1, 'cultivo_iacs_cod': '1820'}])
    conn.commit()
    check("no declara nada", r['creadas'] == 0)
    check("y dice por qué", 'No hay ninguna explotación seleccionada' in r['motivos'])
    check("no ha escrito en la BD", _filas(conn) == [])
    conn.close()


# ── C · declarar en lote ──────────────────────────────────────────────────────

def test_declarar_lote():
    print("E · declarar en lote:")
    conn = _db()
    _parcela(conn, 1, 'OV - OLIVAR', sup=2.4, nombre='La Loma')
    _parcela(conn, 2, 'OV - OLIVAR', sup=1.5)
    conn.commit()

    res = declarar_cultivos_lote(conn, UID, EXPL, [
        {'parcela_id': 1, 'cultivo_iacs_cod': '1820', 'superficie_cultivada_ha': 2.4},
        {'parcela_id': 2, 'cultivo_iacs_cod': '1820', 'superficie_cultivada_ha': 1.5},
    ])
    conn.commit()

    check("declara las 2", res['creadas'] == 2)
    f = _filas(conn, 1)[0]
    check("guarda el código IACS", f['cultivo_iacs_cod'] == '1820')
    check("rellena el nombre del cultivo desde el catálogo", f['cultivo'] == 'Olivar')
    check("guarda la explotación", f['explotacion_id'] == EXPL)
    check("guarda la superficie", f['superficie_cultivada_ha'] == 2.4)
    conn.close()


def test_declarar_lote_valida():
    print("F · lo que el lote tiene que rechazar:")
    conn = _db()
    _parcela(conn, 1, 'OV - OLIVAR', sup=2.0)
    _parcela(conn, 99, 'OV - OLIVAR', uid=OTRO_UID, expl=OTRA_EXPL)   # de otro
    _parcela(conn, 98, 'OV - OLIVAR', uid=UID, expl=OTRA_EXPL)        # mía, otra finca
    conn.commit()

    res = declarar_cultivos_lote(conn, UID, EXPL, [
        {'parcela_id': 99, 'cultivo_iacs_cod': '1820'},   # parcela ajena
        {'parcela_id': 98, 'cultivo_iacs_cod': '1820'},   # otra explotación
        {'parcela_id': 1,  'cultivo_iacs_cod': '430'},    # cebada: no es leñoso
        {'parcela_id': 1,  'cultivo_iacs_cod': 'X; DROP TABLE parcelas--'},
        {'parcela_id': 1,  'cultivo_iacs_cod': ''},
        {'parcela_id': 12345, 'cultivo_iacs_cod': '1820'},  # no existe
    ])
    conn.commit()

    check("no crea ninguna", res['creadas'] == 0)
    check("informa de las 6 rechazadas", res['rechazadas'] == 6)
    check("no escribe nada en la BD", _filas(conn) == [])
    check("la parcela ajena sigue intacta", _filas(conn, 99) == [])
    conn.close()


def test_declarar_lote_idempotente():
    print("G · repetir el lote no duplica:")
    conn = _db()
    _parcela(conn, 1, 'OV - OLIVAR', sup=2.0)
    conn.commit()
    lote = [{'parcela_id': 1, 'cultivo_iacs_cod': '1820', 'superficie_cultivada_ha': 2.0}]

    declarar_cultivos_lote(conn, UID, EXPL, lote); conn.commit()
    res = declarar_cultivos_lote(conn, UID, EXPL, lote); conn.commit()

    check("la segunda vez no crea nada", res['creadas'] == 0)
    check("y lo dice", res['saltadas'] == 1)
    check("sigue habiendo una sola fila", len(_filas(conn, 1)) == 1)
    conn.close()


def test_parcela_mixta():
    print("H · la parcela mixta (80% viñedo de vino, 20% olivar):")
    conn = _db()
    _parcela(conn, 1, 'VO - VIÑEDO - OLIVAR', sup=5.0, nombre='La Mixta')
    conn.commit()

    res = declarar_cultivos_lote(conn, UID, EXPL, [
        {'parcela_id': 1, 'cultivo_iacs_cod': '1711', 'superficie_cultivada_ha': 4.0},
        {'parcela_id': 1, 'cultivo_iacs_cod': '1820', 'superficie_cultivada_ha': 1.0},
    ])
    conn.commit()

    filas = _filas(conn, 1)
    check("crea las dos filas", res['creadas'] == 2)
    check("una por cultivo", {f['cultivo_iacs_cod'] for f in filas} == {'1711', '1820'})
    check("con su reparto de superficie",
          sorted(f['superficie_cultivada_ha'] for f in filas) == [1.0, 4.0])
    conn.close()


def test_superficie_no_se_pasa():
    print("I · la superficie declarada no puede pasar de la de la parcela:")
    conn = _db()
    _parcela(conn, 1, 'VO - VIÑEDO - OLIVAR', sup=5.0)
    conn.commit()

    res = declarar_cultivos_lote(conn, UID, EXPL, [
        {'parcela_id': 1, 'cultivo_iacs_cod': '1711', 'superficie_cultivada_ha': 4.0},
        {'parcela_id': 1, 'cultivo_iacs_cod': '1820', 'superficie_cultivada_ha': 3.0},
    ])
    conn.commit()

    check("la primera entra", res['creadas'] == 1)
    check("la que se pasa se rechaza", res['rechazadas'] == 1)
    check("solo hay una fila", len(_filas(conn, 1)) == 1)
    conn.close()


def test_campana_no_la_elige_el_cliente():
    print("J · la campaña la pone el servidor, no la petición:")
    conn = _db()
    _parcela(conn, 1, 'OV - OLIVAR', sup=2.0)
    conn.commit()

    # Ni siquiera hay un hueco por donde meterla: la función no la recibe. Se
    # escribe en la campaña activa de la explotación y punto.
    r = declarar_cultivos_lote(conn, UID, EXPL,
                               [{'parcela_id': 1, 'cultivo_iacs_cod': '1820'}])
    conn.commit()
    check("declara la parcela", r['creadas'] == 1)
    check("en la campaña activa de la explotación", r['campana'] == CAMPANA)
    check("y la fila lleva esa campaña", _filas(conn, 1)[0]['campana'] == CAMPANA)

    # Si la explotación cambia de campaña, la declaración va a la nueva.
    conn.execute("UPDATE explotacion SET campana_activa='2026/2027' WHERE id=?", (EXPL,))
    conn.commit()
    r2 = declarar_cultivos_lote(conn, UID, EXPL,
                                [{'parcela_id': 1, 'cultivo_iacs_cod': '1820'}])
    conn.commit()
    check("sigue la campaña de la explotación", r2['campana'] == '2026/2027')
    check("y no pisa la fila de la campaña anterior", len(_filas(conn, 1)) == 2)
    conn.close()


def run():
    print("test_lenosos_sigpac:")
    test_codigo_uso()
    test_sugerencias()
    test_sugerencias_no_repite_lo_declarado()
    test_sugerencias_aislamiento()
    test_sin_explotacion()
    test_declarar_lote()
    test_declarar_lote_valida()
    test_declarar_lote_idempotente()
    test_parcela_mixta()
    test_superficie_no_se_pasa()
    test_campana_no_la_elige_el_cliente()
    print("test_lenosos_sigpac: TODO OK")


if __name__ == '__main__':
    run()
