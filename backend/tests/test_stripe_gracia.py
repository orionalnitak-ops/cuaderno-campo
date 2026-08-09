"""Test plano (sin pytest) del margen cuando falla el cobro.

Antes, el webhook de Stripe trataba `past_due` igual que `canceled` y `unpaid`:
al PRIMER cobro fallido el agricultor bajaba a solo lectura. Pero `past_due`
significa que Stripe sigue reintentando, y la mayoría de esos cobros acaban
entrando (tarjeta caducada, sin saldo ese día, confirmación del banco no vista).

Aquí se fija la separación:
  - "ha fallado pero seguimos intentándolo"  -> mantiene el acceso + aviso
  - "esto no se cobra"                       -> solo lectura

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_stripe_gracia.py
"""
import datetime
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import blueprints.stripe_bp as stripe_bp  # noqa: E402
from blueprints.stripe_bp import (  # noqa: E402
    ESTADOS_CORTE, accion_suscripcion, aplicar_gracia, cortar_acceso,
)
from extensions import (  # noqa: E402
    MARGEN_SUSCRIPCION_DIAS, compute_plan_status,
)

AHORA = datetime.datetime(2026, 8, 3, 10, 0, 0)
LUEGO = datetime.datetime(2026, 8, 6, 10, 0, 0)


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def _db():
    """Un usuario 1 con plan basic pagando, y un usuario 2 ajeno."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY, plan TEXT, subscription_ends_at TIMESTAMP,
        stripe_subscription_id TEXT, pago_fallido_desde TIMESTAMP)''')
    conn.execute("INSERT INTO users VALUES (1,'basic','2026-09-01 00:00:00','sub_1',NULL)")
    conn.execute("INSERT INTO users VALUES (2,'pro','2026-09-01 00:00:00','sub_2',NULL)")
    conn.commit()
    return conn


def _u(conn, uid=1):
    return conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


# ── 1. Qué acción corresponde a cada estado de Stripe ──────────────────
def test_clasificacion_de_estados():
    check("active da de alta",        accion_suscripcion('active') == 'alta')
    check("trialing da de alta",      accion_suscripcion('trialing') == 'alta')
    check("past_due entra en gracia", accion_suscripcion('past_due') == 'gracia')
    check("canceled corta",           accion_suscripcion('canceled') == 'corte')
    check("unpaid corta",             accion_suscripcion('unpaid') == 'corte')
    check("incomplete_expired corta", accion_suscripcion('incomplete_expired') == 'corte')
    # `incomplete` es una suscripción cuyo primer pago aún no ha entrado:
    # no da acceso, pero tampoco quita el que ya hubiera. No se toca nada.
    check("incomplete no toca nada",  accion_suscripcion('incomplete') is None)
    check("estado desconocido no toca nada", accion_suscripcion('vete_a_saber') is None)


def test_invariante_past_due_nunca_corta():
    """El bug que se arregla aquí. Si alguien vuelve a meter `past_due` en la
    lista de corte, este test tiene que ponerse rojo."""
    check("past_due fuera de los estados de corte", 'past_due' not in ESTADOS_CORTE)


# ── 2. Gracia: el cobro falla pero el agricultor sigue trabajando ──────
def test_gracia_no_quita_el_acceso():
    conn = _db()
    aplicar_gracia(conn, 1, ahora=AHORA)
    u = _u(conn)
    check("el plan no cambia",              u['plan'] == 'basic')
    check("la suscripción sigue asociada",  u['stripe_subscription_id'] == 'sub_1')
    check("queda marcado el fallo",         u['pago_fallido_desde'] == '2026-08-03 10:00:00')


def test_gracia_guarda_la_fecha_del_primer_fallo():
    """Stripe reintenta varias veces y manda un `past_due` por cada intento.
    El aviso debe decir desde cuándo falla, no repartirse la fecha del último
    reintento, o nunca se sabría cuánto tiempo lleva el cobro caído."""
    conn = _db()
    aplicar_gracia(conn, 1, ahora=AHORA)
    aplicar_gracia(conn, 1, ahora=LUEGO)
    check("se conserva la primera fecha",
          _u(conn)['pago_fallido_desde'] == '2026-08-03 10:00:00')


def test_gracia_no_toca_a_otros_agricultores():
    conn = _db()
    aplicar_gracia(conn, 1, ahora=AHORA)
    check("el otro usuario queda intacto", _u(conn, 2)['pago_fallido_desde'] is None)


# ── 3. Corte: esto ya no se cobra ──────────────────────────────────────
def test_corte_baja_a_solo_lectura():
    conn = _db()
    cortar_acceso(conn, 1)
    u = _u(conn)
    check("baja de plan",                    u['plan'] == 'trial')
    check("sin fecha de fin de suscripción", u['subscription_ends_at'] is None)
    check("se limpia el aviso de impago",    u['pago_fallido_desde'] is None)
    check("conserva la suscripción de Stripe para soporte",
          u['stripe_subscription_id'] == 'sub_1')


def test_corte_tras_gracia_limpia_el_aviso():
    """Si el cobro falla y acaba sin cobrarse, no puede quedar el aviso naranja
    de 'revisa tu tarjeta' encima del cartel rojo de suscripción caducada."""
    conn = _db()
    aplicar_gracia(conn, 1, ahora=AHORA)
    cortar_acceso(conn, 1)
    u = _u(conn)
    check("plan a trial",     u['plan'] == 'trial')
    check("aviso limpiado",   u['pago_fallido_desde'] is None)


def test_corte_definitivo_olvida_la_suscripcion():
    conn = _db()
    cortar_acceso(conn, 1, olvidar_suscripcion=True)
    check("suscripción olvidada", _u(conn)['stripe_subscription_id'] is None)


def test_corte_no_toca_a_otros_agricultores():
    conn = _db()
    cortar_acceso(conn, 1)
    check("el otro usuario sigue en pro", _u(conn, 2)['plan'] == 'pro')


# ── 4. Un plan de pago CADUCA ─────────────────────────────────────────
#
# El agujero que cierra este bloque: `compute_plan_status()` devolvía True para
# basic/pro/premium sin mirar ninguna fecha, y `subscription_ends_at` se
# guardaba en la BD sin que nadie la leyera jamás. Una cuenta a la que se le
# perdiera el webhook de cancelación escribía gratis para siempre, en silencio.
_HOY = datetime.datetime.utcnow()


def _fecha(dias):
    """Fecha desplazada N días respecto de ahora (negativo = pasado)."""
    return (_HOY + datetime.timedelta(days=dias)).strftime('%Y-%m-%d %H:%M:%S')


def test_plan_de_pago_vigente_sigue_activo():
    label, activo = compute_plan_status('pro', None, 'user', _fecha(20))
    check("plan al día activo", activo is True)
    check("y se etiqueta pro", label == 'pro')


def test_plan_de_pago_recien_vencido_aguanta_el_margen():
    """Un webhook de renovación que llega tarde no puede cortarle el cuaderno
    a quien sí ha pagado."""
    _, activo = compute_plan_status('pro', None, 'user', _fecha(-2))
    check("dentro del margen de 5 días sigue escribiendo", activo is True)


def test_plan_de_pago_vencido_pierde_el_acceso():
    """EL GATE FALLA CERRADO. Si esto se pone en verde por accidente, una
    cuenta cancelada cuyo webhook se perdió escribe gratis para siempre."""
    label, activo = compute_plan_status('pro', None, 'user', _fecha(-30))
    check("pasado el margen deja de estar activo", activo is False)
    check("y se etiqueta expired, no pro", label == 'expired')


def test_el_margen_es_de_cinco_dias():
    check("margen declarado", MARGEN_SUSCRIPCION_DIAS == 5)
    _, dentro = compute_plan_status('basic', None, 'user', _fecha(-4))
    _, fuera  = compute_plan_status('basic', None, 'user', _fecha(-6))
    check("a 4 días aún entra", dentro is True)
    check("a 6 días ya no",     fuera is False)


def test_alta_sin_periodo_no_vence():
    """Los planes concedidos a mano desde el panel de admin no vienen de
    Stripe y no tienen periodo. No pueden caducar solos."""
    _, activo = compute_plan_status('pro', None, 'user', None)
    check("sin subscription_ends_at sigue activo", activo is True)


def test_admin_nunca_se_corta():
    _, activo = compute_plan_status('pro', None, 'admin', _fecha(-400))
    check("el admin no depende de la fecha", activo is True)


def test_fecha_ilegible_no_da_acceso():
    """Una fecha escrita pero ilegible NO es lo mismo que no tener fecha.
    Si colara como "sin periodo", volvería el agujero por la puerta de atrás."""
    _, activo = compute_plan_status('pro', None, 'user', 'no-es-una-fecha')
    check("fecha corrupta no da acceso", activo is False)


def test_trial_sigue_funcionando_igual():
    """El cambio no puede tocar el trial de 7 días, que es por dónde entra
    todo agricultor nuevo."""
    _, vivo    = compute_plan_status('trial', _fecha(3), 'user')
    lbl, muerto = compute_plan_status('trial', _fecha(-1), 'user')
    check("trial vigente activo",   vivo is True)
    check("trial caducado inactivo", muerto is False)
    check("y etiquetado expired",    lbl == 'expired')


# ── 5. La consulta a Stripe cuando la fecha ya venció ─────────────────
#
# Es el único punto del backend que habla con Stripe fuera del checkout, y el
# que decide si a un agricultor se le corta el cuaderno. Se prueba con un
# Stripe de mentira: aquí no se toca la red.
class _NoCierra:
    """Envuelve la conexión para que el .close() del código no la mate."""

    def __init__(self, c):
        self._c = c

    def __getattr__(self, n):
        return getattr(self._c, n)

    def close(self):
        pass


def _stripe_falso(status, fin=None):
    """Un módulo stripe de mentira que contesta lo que se le diga."""
    class _S:
        Subscription = type('_Sub', (), {
            'retrieve': staticmethod(lambda _id: {'status': status, 'current_period_end': fin})
        })
    return lambda: _S()


def _escenario_vencido():
    """Usuario 1 en pro con la fecha vencida hace 30 días."""
    conn = _db()
    vieja = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("UPDATE users SET plan='pro', subscription_ends_at=? WHERE id=1", (vieja,))
    conn.commit()
    stripe_bp.get_db = lambda: _NoCierra(conn)
    return conn, vieja


def test_reconciliar_revalida_al_que_si_paga():
    """El caso que justifica llamar a Stripe: se perdió el webhook de una
    renovación normal. Si esto falla, le cortas el cuaderno a un cliente."""
    conn, vieja = _escenario_vencido()
    futuro = int((datetime.datetime.utcnow() + datetime.timedelta(days=25)).timestamp())
    stripe_bp._stripe = _stripe_falso('active', futuro)
    check("conserva el acceso", stripe_bp.reconciliar_suscripcion(1, 'sub_1') is True)
    u = _u(conn)
    check("sigue en pro", u['plan'] == 'pro')
    check("y se guarda la fecha buena", u['subscription_ends_at'] > vieja)


def test_reconciliar_con_past_due_mantiene_acceso_y_avisa():
    conn, _ = _escenario_vencido()
    futuro = int((datetime.datetime.utcnow() + datetime.timedelta(days=25)).timestamp())
    stripe_bp._stripe = _stripe_falso('past_due', futuro)
    check("conserva el acceso", stripe_bp.reconciliar_suscripcion(1, 'sub_1') is True)
    check("y queda marcado el impago", _u(conn)['pago_fallido_desde'] is not None)


def test_reconciliar_corta_al_cancelado():
    conn, _ = _escenario_vencido()
    stripe_bp._stripe = _stripe_falso('canceled')
    check("pierde el acceso", stripe_bp.reconciliar_suscripcion(1, 'sub_1') is False)
    u = _u(conn)
    check("baja a trial", u['plan'] == 'trial')
    check("sin fecha de suscripción", u['subscription_ends_at'] is None)


def test_reconciliar_falla_cerrado_si_stripe_no_responde():
    """Un timeout de Stripe no puede convertirse en barra libre. Y tampoco
    puede bajarle el plan a nadie: no sabemos nada, así que no se toca la BD."""
    conn, _ = _escenario_vencido()

    class _Boom:
        Subscription = type('_Sub', (), {
            'retrieve': staticmethod(lambda _id: (_ for _ in ()).throw(RuntimeError('timeout')))
        })
    stripe_bp._stripe = lambda: _Boom()
    check("no concede acceso", stripe_bp.reconciliar_suscripcion(1, 'sub_1') is False)
    check("y no toca el plan", _u(conn)['plan'] == 'pro')


def test_reconciliar_sin_clave_no_concede():
    _escenario_vencido()
    stripe_bp._stripe = lambda: None
    check("sin clave de Stripe, no se concede", stripe_bp.reconciliar_suscripcion(1, 'sub_1') is False)
    check("sin sub_id tampoco", stripe_bp.reconciliar_suscripcion(1, None) is False)


# ── 6. "Solo lectura" tiene que ser lectura ENTERA ────────────────────
def test_el_cortado_puede_seguir_leyendo_y_exportando():
    """Un agricultor cortado conserva su cuaderno: puede consultarlo y
    descargar el PDF y el Excel oficiales. Si una inspección le cae estando
    en descubierto, el documento legal tiene que salir igual.

    Se comprueba sobre el mapa de rutas real: las exportaciones son GET, y el
    guard deja pasar GET siempre.
    """
    import app as app_mod
    rutas = {str(r): r.methods for r in app_mod.app.url_map.iter_rules()}
    for ruta in ('/api/export/excel', '/api/export/pdf', '/api/backup/export'):
        check(f"{ruta} es de solo lectura (GET)", 'GET' in rutas.get(ruta, set())
              and 'POST' not in rutas.get(ruta, set()))


def test_el_cortado_puede_cambiar_de_finca():
    """Cambiar de explotación activa solo guarda un id en la sesión: no
    escribe datos del agricultor. Si el guard lo bloqueara, quien tiene varias
    fincas solo podría leer y exportar la que tuviera abierta al caducarle el
    plan, porque las exportaciones filtran por la finca activa."""
    import app as app_mod
    check("el endpoint de activar está exento del guard",
          'explotacion.activar_explotacion' in app_mod._PLAN_EXEMPT_ENDPOINTS)


def test_el_corte_no_borra_nada():
    """El corte baja el plan y punto. Si alguien mete aquí un DELETE, le está
    borrando el cuaderno a un agricultor por no pagar un mes."""
    ruta = os.path.join(os.path.dirname(__file__), '..', 'blueprints', 'stripe_bp.py')
    with open(ruta, encoding='utf-8') as f:
        fuente = f.read().upper()
    check("stripe_bp no borra filas", 'DELETE FROM' not in fuente)


def test_la_columna_existe_en_el_esquema():
    """Si alguien añade la columna aquí pero se olvida de db.py, la app
    reventaría en producción con 'no such column'."""
    import re
    ruta = os.path.join(os.path.dirname(__file__), '..', 'db.py')
    with open(ruta, encoding='utf-8') as f:
        fuente = f.read()
    check("pago_fallido_desde en CREATE TABLE users",
          re.search(r'pago_fallido_desde\s+TIMESTAMP', fuente) is not None)
    check("pago_fallido_desde migrada con _add_col",
          "('pago_fallido_desde', 'TIMESTAMP')" in fuente)


def test_el_alta_limpia_el_aviso():
    """TODO UPDATE que da de alta un plan de pago tiene que poner
    pago_fallido_desde a NULL. Si no, el agricultor cuyo cobro falló y luego
    arregló la tarjeta se queda con el aviso de impago para siempre.

    Se mira sobre el fuente con los espacios colapsados, porque las consultas
    están partidas en varias líneas."""
    import re
    ruta = os.path.join(os.path.dirname(__file__), '..', 'blueprints', 'stripe_bp.py')
    with open(ruta, encoding='utf-8') as f:
        fuente = ' '.join(f.read().split())
    altas = re.findall(r'UPDATE users SET plan=\?.*?WHERE id=\?', fuente)
    check("hay al menos dos UPDATE de alta (webhook y checkout)", len(altas) >= 2)
    for i, sql in enumerate(altas):
        check(f"el alta #{i + 1} limpia pago_fallido_desde",
              'pago_fallido_desde=NULL' in sql)


if __name__ == '__main__':
    print("\n== Margen cuando falla el cobro (Stripe past_due) ==\n")
    for nombre, fn in sorted(list(globals().items())):
        if nombre.startswith('test_') and callable(fn):
            print(f"{nombre}:")
            fn()
    print("\nTodo en verde.\n")
