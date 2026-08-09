"""Test plano (sin pytest) del tope de explotaciones por plan — feature 017.

Lo único que diferencia el plan Básico del Pro es el número de explotaciones.
Hasta ahora eso solo se comprobaba al CREAR una finca, así que quien bajaba de
Pro a Básico en el portal de Stripe seguía anotando en las cinco: pagaba la
mitad y usaba lo mismo.

Aquí se fija la regla:
  - LEER no se limita jamás. Sus fincas las consulta todas.
  - ESCRIBIR se limita a las `limit` primeras por `orden, id`.
  - El agricultor elige cuáles marcando una como principal, que la pone la
    primera del orden. Eso NUNCA se bloquea: si se bloqueara, quien baja de
    plan se quedaría encerrado en la finca equivocada.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_limite_explotaciones.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helpers import explotaciones_escribibles  # noqa: E402


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def _db(fincas):
    """BD de mentira. `fincas` es una lista de (id, orden) del usuario 1."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE explotacion (id INTEGER PRIMARY KEY, user_id INTEGER, orden INTEGER)")
    for eid, orden in fincas:
        conn.execute("INSERT INTO explotacion VALUES (?,1,?)", (eid, orden))
    # Un vecino con sus propias fincas, para que ningún filtro se lo lleve por delante.
    conn.execute("INSERT INTO explotacion VALUES (99,2,0)")
    conn.commit()
    return conn


# ── 1. El tope se aplica, y por el orden que ve el agricultor ─────────
def test_basico_con_una_finca_no_nota_nada():
    """El caso de todos hoy: las dos cuentas Básico de producción tienen una
    finca cada una. Este cambio no puede tocarles nada."""
    conn = _db([(10, 0)])
    check("su única finca es escribible", explotaciones_escribibles(conn, 1, 1) == {10})


def test_basico_con_tres_fincas_solo_escribe_en_la_primera():
    conn = _db([(10, 0), (11, 1), (12, 2)])
    check("solo la primera por orden", explotaciones_escribibles(conn, 1, 1) == {10})


def test_pro_con_cinco_fincas_las_escribe_todas():
    conn = _db([(10, 0), (11, 1), (12, 2), (13, 3), (14, 4)])
    check("las cinco entran", len(explotaciones_escribibles(conn, 1, 5)) == 5)


def test_pro_con_seis_fincas_deja_una_fuera():
    """El caso real que hay en producción: una cuenta con 6 fincas. Hoy está en
    `premium` (sin tope), pero si pasara a Pro la sexta quedaría en lectura."""
    conn = _db([(10, 0), (11, 1), (12, 2), (13, 3), (14, 4), (15, 5)])
    esc = explotaciones_escribibles(conn, 1, 5)
    check("entran cinco", len(esc) == 5)
    check("la sexta se queda fuera", 15 not in esc)


def test_sin_tope_no_limita():
    """Admin, premium y súper usuarios: `limit` a None."""
    conn = _db([(10, 0), (11, 1), (12, 2)])
    check("None significa sin tope", explotaciones_escribibles(conn, 1, None) is None)


def test_no_se_cuelan_las_fincas_de_otro():
    conn = _db([(10, 5)])
    esc = explotaciones_escribibles(conn, 1, 5)
    check("solo las suyas", esc == {10})
    check("la del vecino ni aparece", 99 not in esc)


def test_manda_el_orden_no_el_id():
    """Marcar principal reescribe `orden`. Si el cálculo mirara el id, elegir
    no serviría de nada: mandaría siempre la finca creada primero."""
    conn = _db([(10, 3), (11, 0), (12, 1)])
    check("gana la de orden 0, no la de id menor", explotaciones_escribibles(conn, 1, 1) == {11})


def test_sin_fincas_no_revienta():
    conn = _db([])
    check("conjunto vacío, sin error", explotaciones_escribibles(conn, 1, 1) == set())


# ── 2. Las salidas del callejón ───────────────────────────────────────
def test_marcar_principal_nunca_se_bloquea():
    """Si el tope bloqueara el endpoint de elegir principal, quien baja de plan
    se quedaría encerrado en la finca equivocada para siempre."""
    import app as app_mod
    for endpoint in ('explotacion.principal_explotacion', 'explotacion.activar_explotacion'):
        check(f"{endpoint} exento del tope", endpoint in app_mod._LIMITE_EXEMPT_ENDPOINTS)


def test_crear_explotacion_conserva_su_propio_mensaje():
    """Crear ya tiene su control con un mensaje mucho mejor (upgrade_required /
    limit_reached). Si el tope general se le adelantara, el agricultor leería
    'esta finca es de solo lectura' mientras intenta crear una nueva."""
    import app as app_mod
    check("crear/listar exento del tope",
          'explotacion.explotaciones' in app_mod._LIMITE_EXEMPT_ENDPOINTS)


def test_el_endpoint_de_principal_existe():
    import app as app_mod
    rutas = {r.endpoint for r in app_mod.app.url_map.iter_rules()}
    check("existe la ruta de principal", 'explotacion.principal_explotacion' in rutas)


# ── 3. Leer no se toca ────────────────────────────────────────────────
def test_el_tope_solo_mira_escrituras():
    """El guard sale antes en GET/HEAD/OPTIONS, así que consultar cualquier
    finca sigue funcionando aunque no esté cubierta por el plan."""
    ruta = os.path.join(os.path.dirname(__file__), '..', 'app.py')
    with open(ruta, encoding='utf-8') as f:
        fuente = f.read()
    i_guard = fuente.index('def guard_active_plan')
    i_get   = fuente.index("request.method in ('GET', 'HEAD', 'OPTIONS')", i_guard)
    i_lim   = fuente.index('_guard_limite_explotaciones()', i_guard)
    check("la salida por GET va antes del tope", i_get < i_lim)


def test_el_listado_dice_cuales_son_escribibles():
    """La app tiene que poder marcar las de solo lectura ANTES de que el
    agricultor intente guardar y se coma un 403 sin haber avisado."""
    ruta = os.path.join(os.path.dirname(__file__), '..', 'blueprints', 'explotacion.py')
    with open(ruta, encoding='utf-8') as f:
        fuente = f.read()
    check("el GET de explotaciones devuelve 'escribible'", "r['escribible']" in fuente)


# ── 4. El guard de verdad, no solo sus piezas ─────────────────────────
#
# Lo de arriba comprueba que las piezas encajan. Esto ejecuta el guard real
# contra peticiones reales, que es lo único que demuestra que un control de
# cobro corta. Es la primera prueba funcional del proyecto: se justifica aquí
# porque un fallo silencioso significa cobrar de menos o bloquear a quien paga.
class _NoCierra:
    def __init__(self, c):
        self._c = c

    def __getattr__(self, n):
        return getattr(self._c, n)

    def close(self):
        pass


def _guard(plan, activa, ruta='/api/tratamientos', metodo='POST'):
    """Ejecuta el guard con un usuario de `plan` sobre la explotación `activa`.

    Devuelve 'PASA' o el código de error con el que deniega.
    """
    import app as app_mod
    import helpers
    from extensions import User
    from flask import session
    from flask_login import login_user

    conn = _db([(10, 0), (11, 1), (12, 2)])
    app_mod.get_db = lambda: _NoCierra(conn)
    helpers.get_db = lambda: _NoCierra(conn)
    try:
        with app_mod.app.test_request_context(ruta, method=metodo):
            login_user(User(1, 'a@b.es', 'A', 'agricultor', 1, plan=plan))
            session['active_explotacion_id'] = activa
            r = app_mod._guard_limite_explotaciones()
            if r is None:
                return 'PASA'
            body, code = r
            return f"{code} {body.get_json().get('error')}"
    finally:
        conn.close()


def test_guard_deja_anotar_en_la_principal():
    check("basic anota en su finca principal", _guard('basic', 10) == 'PASA')


def test_guard_corta_en_las_que_sobran():
    check("segunda finca denegada", _guard('basic', 11) == '403 explotacion_solo_lectura')
    check("tercera finca denegada",  _guard('basic', 12) == '403 explotacion_solo_lectura')


def test_guard_no_molesta_a_pro():
    check("pro con 3 fincas anota en la tercera", _guard('pro', 12) == 'PASA')


def test_guard_deja_siempre_las_salidas():
    """Las tres puertas que impiden que alguien se quede encerrado."""
    check("marcar principal pasa",
          _guard('basic', 11, '/api/explotaciones/11/principal') == 'PASA')
    check("cambiar de finca activa pasa",
          _guard('basic', 11, '/api/explotaciones/11/activar') == 'PASA')
    check("crear explotación pasa (tiene su propio mensaje)",
          _guard('basic', 11, '/api/explotaciones') == 'PASA')


def test_elegir_principal_cambia_de_verdad_donde_se_puede_anotar():
    """El recorrido entero, que es la razón de ser de la feature: un Básico con
    tres fincas elige la tercera y pasa a ser en la que anota.

    Sin esto, el tope caería siempre sobre la finca creada primero y el
    agricultor no tendría forma de cambiarlo.
    """
    import app as app_mod
    import helpers
    import blueprints.explotacion as ex
    from extensions import User
    from flask import session
    from flask_login import login_user

    conn = _db([(10, 0), (11, 1), (12, 2)])
    ex.get_db = lambda: _NoCierra(conn)
    helpers.get_db = lambda: _NoCierra(conn)
    try:
        check("de partida se anota en la primera",
              explotaciones_escribibles(conn, 1, 1) == {10})

        with app_mod.app.test_request_context('/api/explotaciones/12/principal', method='POST'):
            login_user(User(1, 'a@b.es', 'A', 'agricultor', 1, plan='basic'))
            resp = ex.principal_explotacion(12)
            check("responde ok", resp.get_json().get('status') == 'ok')
            check("y la deja activa", session.get('active_explotacion_id') == 12)

        check("ahora se anota en la elegida",
              explotaciones_escribibles(conn, 1, 1) == {12})
        orden = {r['id']: r['orden'] for r in conn.execute("SELECT * FROM explotacion WHERE user_id=1")}
        check("la elegida pasa a orden 0", orden[12] == 0)
        check("las demás se renumeran sin empatar",
              sorted([orden[10], orden[11]]) == [1, 2])
    finally:
        conn.close()


if __name__ == '__main__':
    print("\n== Tope de explotaciones por plan (017) ==\n")
    for nombre, fn in sorted(list(globals().items())):
        if nombre.startswith('test_') and callable(fn):
            print(f"{nombre}:")
            fn()
    print("\nTodo en verde.\n")
