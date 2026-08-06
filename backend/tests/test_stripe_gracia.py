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

from blueprints.stripe_bp import (  # noqa: E402
    ESTADOS_CORTE, accion_suscripcion, aplicar_gracia, cortar_acceso,
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


# ── 4. El aviso se borra en cuanto el cobro entra ──────────────────────
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
