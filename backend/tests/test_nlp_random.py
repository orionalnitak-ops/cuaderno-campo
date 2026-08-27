"""Test aleatorio (fuzz) de "Habla que yo escribo" — el parser de texto libre.

Genera frases al azar combinando finca + acción + producto + dosis + fecha, se
las pasa a los mismos endpoints que usa el frontend (/api/parse y
/api/parse/guardar), y comprueba que cada dato termina en el sitio correcto:

  - riego / cosecha / labor  -> se guardan en su tabla, con la finca correcta.
  - tratamiento / abonado    -> el sistema los detecta pero SIEMPRE los
    rechaza y pide el formulario completo (a propósito: el RD 1311/2012 exige
    datos — ROPO, nº MAPA, plazo de seguridad — que una frase no puede dar).
    Aquí "ir a su sitio" significa que NO se cuela ninguna fila en tablas que
    ni siquiera existen en este esquema de prueba: si el código intentara
    insertar, sqlite reventaría con "no such table" y el caso quedaría marcado
    como fallo.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_nlp_random.py
"""
import os
import random
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import blueprints.nlp as nlp_mod  # noqa: E402
import helpers  # noqa: E402

UID = 1
EXP_ID = 10
SEED = 20260827  # fijo: mismos casos en cada ejecución, reproducible

_SCHEMA = """
CREATE TABLE explotacion (
    id INTEGER PRIMARY KEY, user_id INTEGER, orden INTEGER DEFAULT 0);
CREATE TABLE parcelas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, explotacion_id INTEGER,
    nombre_finca TEXT, activa INTEGER DEFAULT 1);
CREATE TABLE riego (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, explotacion_id INTEGER,
    parcela_id INTEGER, parcela_etiqueta TEXT, fecha TEXT, tipo_riego TEXT,
    horas_riego REAL, volumen_m3 REAL, fuente_agua TEXT, notas TEXT, campana TEXT);
CREATE TABLE cosecha (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, explotacion_id INTEGER,
    parcela_id INTEGER, parcela_etiqueta TEXT, fecha_inicio TEXT, cultivo TEXT,
    produccion_total_unidad TEXT, notas TEXT, campana TEXT);
CREATE TABLE labores (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, explotacion_id INTEGER,
    parcela_id INTEGER, parcela_etiqueta TEXT, fecha TEXT, tipo_labor TEXT,
    descripcion TEXT, producto TEXT, notas TEXT, campana TEXT);
"""

# Fincas reales-plausibles, con nombres de una y varias palabras a propósito:
# el emparejamiento por palabras (extraer_parcela, paso 2) es justo lo que más
# falla cuando el nombre tiene varias palabras cortas.
FINCAS = ['El Olivar', 'La Cebada', 'Los Llanos', 'Finca Grande',
          'El Bancal Nuevo', 'Majada Alta', 'La Solana']

SEMILLAS = ['trigo', 'cebada', 'girasol', 'maiz', 'patata', 'tomate', 'garbanzo']
QUIMICOS = ['cobre', 'azufre', 'glifosato', 'clorpirifos', 'mancozeb']
FERTILIZANTES = ['urea', 'npk', 'estiercol', 'compost', 'superfosfato']
DOSIS = [('50 kg', 50.0, 'kg'), ('2 litros', 2.0, 'L'), ('300 g', 300.0, 'g'),
         ('1.5 t', 1.5, 't'), ('80 cc', 80.0, 'cc')]

# (plantilla, categoría esperada, usa_producto, lista_productos, usa_dosis)
PLANTILLAS = [
    # riego -> se guarda
    ("Regué en {finca} 2 horas por goteo", 'riego', False, None, False),
    ("He regado {finca} con aspersión hoy", 'riego', False, None, False),
    ("Riego en {finca} 3 horas", 'riego', False, None, False),
    ("Regamos la finca {finca} por pivote ayer", 'riego', False, None, False),
    ("Puse el goteo en {finca} esta mañana", 'riego', False, None, False),
    # cosecha -> se guarda
    ("Cosechamos {producto} en {finca} ayer", 'cosecha', True, SEMILLAS, False),
    ("Recolectamos en {finca} hoy", 'cosecha', False, None, False),
    ("Vendimiamos en {finca}", 'cosecha', False, None, False),
    ("Trillamos {finca} esta semana", 'cosecha', False, None, False),
    # labor -> se guarda
    ("Sembré {producto} en {finca} hoy", 'labor', True, SEMILLAS, False),
    ("Aramos {finca} ayer", 'labor', False, None, False),
    ("Poda en {finca}", 'labor', False, None, False),
    ("Hicimos una labor de desbroce en {finca}", 'labor', False, None, False),
    ("Plantamos {producto} en {finca}", 'labor', True, SEMILLAS, False),
    ("Dimos un pase de grada en {finca}", 'labor', False, None, False),
    # tratamiento -> se rechaza, nunca se guarda
    ("Traté con {producto} en {finca}, {dosis}", 'tratamiento', True, QUIMICOS, True),
    ("Fumigamos {finca} con {producto}", 'tratamiento', True, QUIMICOS, False),
    ("Pulverizamos {producto} en {finca} {dosis}", 'tratamiento', True, QUIMICOS, True),
    # abonado -> se rechaza, nunca se guarda
    ("Aboné {finca} con {producto} {dosis}", 'fertilizacion', True, FERTILIZANTES, True),
    ("Fertilizamos {finca} con {producto}", 'fertilizacion', True, FERTILIZANTES, False),
    ("Echamos {producto} en {finca}, {dosis}", 'fertilizacion', True, FERTILIZANTES, True),
]

TABLA_POR_CATEGORIA = {'riego': 'riego', 'cosecha': 'cosecha', 'labor': 'labores'}


class _NoCierra:
    def __init__(self, c):
        self._c = c

    def __getattr__(self, n):
        return getattr(self._c, n)

    def close(self):
        pass


def _db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.execute("INSERT INTO explotacion (id, user_id, orden) VALUES (?,?,0)", (EXP_ID, UID))
    parcela_ids = {}
    for nombre in FINCAS:
        c = conn.execute(
            "INSERT INTO parcelas (user_id, explotacion_id, nombre_finca) VALUES (?,?,?)",
            (UID, EXP_ID, nombre))
        parcela_ids[nombre] = c.lastrowid
    conn.commit()
    return conn, parcela_ids


def _generar_casos(n):
    rnd = random.Random(SEED)
    casos = []
    for _ in range(n):
        plantilla, categoria, usa_producto, productos, usa_dosis = rnd.choice(PLANTILLAS)
        finca = rnd.choice(FINCAS)
        producto = rnd.choice(productos) if usa_producto else None
        dosis_txt, dosis_val, dosis_unidad = rnd.choice(DOSIS) if usa_dosis else (None, None, None)
        texto = plantilla.format(finca=finca, producto=producto or '', dosis=dosis_txt or '')
        casos.append({
            'texto': texto, 'finca': finca, 'categoria': categoria,
            'producto_esperado': producto, 'dosis_esperada': dosis_val,
            'unidad_esperada': dosis_unidad,
        })
    return casos


_TABLAS_PERMITIDAS = set(TABLA_POR_CATEGORIA.values())


def _ultima_fila(conn, tabla):
    if tabla not in _TABLAS_PERMITIDAS:
        raise ValueError(f"Tabla no permitida: {tabla!r}")
    return conn.execute(f"SELECT * FROM {tabla} ORDER BY id DESC LIMIT 1").fetchone()


def _contar(conn, tabla):
    if tabla not in _TABLAS_PERMITIDAS:
        raise ValueError(f"Tabla no permitida: {tabla!r}")
    return conn.execute(f"SELECT COUNT(*) c FROM {tabla}").fetchone()['c']


def run():
    print("test_nlp_random: fuzz de 'Habla que yo escribo'")
    conn, parcela_ids = _db()
    # Se guardan los originales para restaurarlos al salir: si este archivo se
    # llegara a importar junto a otros tests en el mismo proceso, el parche no
    # debe sobrevivir a esta función y contaminar lo que corra después.
    _orig_nlp_get_db = nlp_mod.get_db
    _orig_helpers_get_db = helpers.get_db
    _orig_get_exp = nlp_mod.get_active_explotacion_id
    _orig_get_uid = nlp_mod.get_uid
    nlp_mod.get_db = lambda: _NoCierra(conn)
    helpers.get_db = lambda: _NoCierra(conn)
    nlp_mod.get_active_explotacion_id = lambda conn=None: EXP_ID
    nlp_mod.get_uid = lambda: UID

    fallos = []

    def marcar(caso, motivo, extra=''):
        fallos.append(f"«{caso['texto']}» -> {motivo}" + (f" ({extra})" if extra else ''))

    try:
        casos = _generar_casos(150)
        _fuzz(conn, parcela_ids, casos, marcar)
    finally:
        conn.close()
        nlp_mod.get_db = _orig_nlp_get_db
        helpers.get_db = _orig_helpers_get_db
        nlp_mod.get_active_explotacion_id = _orig_get_exp
        nlp_mod.get_uid = _orig_get_uid

    print(f"\n{len(casos)} frases generadas, {len(fallos)} fallos.\n")
    if fallos:
        print("FALLOS:")
        for f in fallos:
            print(f"  - {f}")
    else:
        print("Todo en verde: cada frase fue a su sitio (o fue rechazada cuando debía serlo).")

    assert not fallos, f"{len(fallos)} caso(s) de {len(casos)} mal encaminados (ver arriba)"


def _fuzz(conn, parcela_ids, casos, marcar):
    for caso in casos:
        texto = caso['texto']
        finca_id_esperado = parcela_ids[caso['finca']]

        # 1) reconocimiento de finca
        parcela = nlp_mod.extraer_parcela(texto, UID)
        if not parcela or parcela['id'] != finca_id_esperado:
            marcar(caso, 'finca mal reconocida',
                   f"esperada={caso['finca']!r} obtenida={parcela}")
            continue

        # 2) reconocimiento de categoría (riego/cosecha/labor/tratamiento/abonado)
        accion = nlp_mod.extraer_accion(texto)
        if accion['tipo'] != caso['categoria']:
            marcar(caso, 'categoría mal reconocida',
                   f"esperada={caso['categoria']!r} obtenida={accion['tipo']!r}"
                   f" (palabra_clave={accion['palabra_clave']!r})")
            continue

        # 3) producto, si la frase llevaba uno (se descarta el nombre de la
        # finca, igual que hace la app, para no confundir "La Cebada" con el
        # cultivo "cebada")
        if caso['producto_esperado']:
            producto = nlp_mod.extraer_producto(texto, caso['finca'])
            if not producto['nombre'] or nlp_mod._norm(caso['producto_esperado']) not in nlp_mod._norm(producto['nombre']):
                marcar(caso, 'producto mal reconocido',
                       f"esperado={caso['producto_esperado']!r} obtenido={producto['nombre']!r}")
                continue

        # 4) dosis, si la frase llevaba una
        if caso['dosis_esperada'] is not None:
            dosis = nlp_mod.extraer_dosis(texto)
            if dosis['valor'] != caso['dosis_esperada'] or dosis['unidad'] != caso['unidad_esperada']:
                marcar(caso, 'dosis mal reconocida',
                       f"esperada={caso['dosis_esperada']}{caso['unidad_esperada']}"
                       f" obtenida={dosis['valor']}{dosis['unidad']}")
                continue

        # 5) recorrido completo vía los endpoints reales
        import app as app_mod  # noqa: E402  (import tardío: necesita el resto de blueprints cargados)
        with app_mod.app.test_request_context('/api/parse', method='POST', json={'texto': texto}):
            from extensions import User
            from flask_login import login_user
            login_user(User(UID, 'a@b.es', 'A', 'agricultor', 1))
            resp = nlp_mod.parse_texto_libre()
            data = resp.get_json()['parseo']
            if data['parcela']['id'] != finca_id_esperado:
                marcar(caso, '/api/parse devolvió otra finca', data['parcela'])
                continue
            if data['accion']['tipo'] != caso['categoria']:
                marcar(caso, '/api/parse devolvió otra categoría', data['accion'])
                continue

        payload = {
            'accion': accion['tipo'],
            'palabra_clave': accion['palabra_clave'],
            'parcela_id': finca_id_esperado,
            'producto': caso['producto_esperado'] or '',
            'fecha': '2026-08-27',
            'texto_original': texto,
        }

        if caso['categoria'] in ('tratamiento', 'fertilizacion'):
            antes = (_contar(conn, 'riego'), _contar(conn, 'cosecha'), _contar(conn, 'labores'))
            with app_mod.app.test_request_context('/api/parse/guardar', method='POST', json=payload):
                login_user(User(UID, 'a@b.es', 'A', 'agricultor', 1))
                try:
                    resp = nlp_mod.parse_guardar()
                except Exception as e:  # p.ej. "no such table tratamientos": se coló un insert
                    marcar(caso, 'intentó guardar en tabla legal en vez de pedir formulario', repr(e))
                    continue
                body, code = resp
                data = body.get_json()
                if code != 422 or data.get('ok') is not False or not data.get('requiere_formulario'):
                    marcar(caso, 'no rechazó ni pidió el formulario completo', data)
                    continue
            despues = (_contar(conn, 'riego'), _contar(conn, 'cosecha'), _contar(conn, 'labores'))
            if antes != despues:
                marcar(caso, 'guardó algo aunque debía rechazar', f"{antes} -> {despues}")
        else:
            tabla = TABLA_POR_CATEGORIA[caso['categoria']]
            antes = _contar(conn, tabla)
            with app_mod.app.test_request_context('/api/parse/guardar', method='POST', json=payload):
                login_user(User(UID, 'a@b.es', 'A', 'agricultor', 1))
                resp = nlp_mod.parse_guardar()
                data = resp.get_json()
                if not data.get('ok'):
                    marcar(caso, 'no se guardó', data)
                    continue
                if data.get('parcela_id') != finca_id_esperado:
                    marcar(caso, 'se guardó en otra finca', data)
                    continue
            despues = _contar(conn, tabla)
            if despues != antes + 1:
                marcar(caso, f'no aumentó la tabla {tabla}', f"{antes} -> {despues}")
                continue
            fila = _ultima_fila(conn, tabla)
            if fila['parcela_id'] != finca_id_esperado:
                marcar(caso, f'la fila de {tabla} apunta a otra parcela',
                       f"esperada={finca_id_esperado} guardada={fila['parcela_id']}")


if __name__ == '__main__':
    run()
