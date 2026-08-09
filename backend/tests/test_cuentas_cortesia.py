"""Test plano (sin pytest) de las cuentas con el plan regalado desde el panel.

El riesgo que cubre no es que Stripe les cobre —no puede: no existe ninguna
suscripción a su nombre— sino que **se cobren ellos solos**.

En la pantalla de planes, el botón de contratar se ocultaba SOLO en la tarjeta
del plan que ya tienes. A una cuenta de cortesía le seguían saliendo las demás,
y a quien tuviera `premium` (que ya no es una tarjeta) le salían TODAS. Un toque
y había un cargo real a alguien a quien se le había regalado el acceso. La
primera expuesta era la cuenta del piloto.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_cuentas_cortesia.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from extensions import es_cuenta_cortesia  # noqa: E402


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


# ── 1. Quién es de cortesía y quién no ─────────────────────────────────
def test_plan_regalado_es_cortesia():
    """Plan de pago sin rastro de Stripe: solo puede venir del panel de admin."""
    check("basic a mano",   es_cuenta_cortesia('basic', None, None) is True)
    check("pro a mano",     es_cuenta_cortesia('pro', None, None) is True)
    check("premium a mano", es_cuenta_cortesia('premium', None, None) is True)


def test_quien_paga_de_verdad_no_es_cortesia():
    """Si tiene cliente o suscripción en Stripe, pagó. No se le bloquea nada:
    tiene que poder cambiar de plan como cualquier cliente."""
    check("con customer",     es_cuenta_cortesia('pro', 'cus_1', None) is False)
    check("con subscription", es_cuenta_cortesia('pro', None, 'sub_1') is False)
    check("con los dos",      es_cuenta_cortesia('pro', 'cus_1', 'sub_1') is False)


def test_un_cliente_nuevo_no_queda_bloqueado():
    """EL CASO QUE NO SE PUEDE ROMPER. Quien llega a pagar por primera vez está
    en `trial` y todavía no tiene identificadores de Stripe. Si el control lo
    tratara como cortesía, nadie podría comprar nunca."""
    check("trial sin nada", es_cuenta_cortesia('trial', None, None) is False)
    check("trial caducado", es_cuenta_cortesia('expired', None, None) is False)


def test_una_cuenta_cancelada_puede_volver_a_pagar():
    """Al cancelar, `cortar_acceso` baja el plan a `trial` y conserva el
    `stripe_customer_id`. Esa persona tiene que poder volver a suscribirse."""
    check("cancelada, conserva cliente", es_cuenta_cortesia('trial', 'cus_1', None) is False)


def test_la_cadena_vacia_cuenta_como_sin_stripe():
    """Una columna a '' en vez de NULL no puede colar como 'ya pagó' y abrirle
    el cobro a una cuenta regalada."""
    check("cadenas vacías", es_cuenta_cortesia('basic', '', '') is True)


# ── 2. El checkout de verdad, no solo la función ───────────────────────
class _NoCierra:
    def __init__(self, c):
        self._c = c

    def __getattr__(self, n):
        return getattr(self._c, n)

    def close(self):
        pass


def _db(plan, customer, subscription):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE users (
        id INTEGER PRIMARY KEY, plan TEXT,
        stripe_customer_id TEXT, stripe_subscription_id TEXT)""")
    conn.execute("INSERT INTO users VALUES (1,?,?,?)", (plan, customer, subscription))
    conn.commit()
    return conn


def _checkout(plan, customer=None, subscription=None):
    """Llama al endpoint real de checkout y devuelve 'ABRE PAGO' o el error."""
    import app as app_mod
    import blueprints.stripe_bp as sb
    from extensions import User
    from flask_login import login_user

    conn = _db(plan, customer, subscription)
    sb.get_db = lambda: _NoCierra(conn)
    # Un Stripe de mentira: si el guard falla, se ve que llega hasta aquí en vez
    # de salir a la red de verdad.
    creadas = []

    class _S:
        class checkout:
            class Session:
                @staticmethod
                def create(**kw):
                    creadas.append(kw)
                    return type('_R', (), {'url': 'https://pago.example'})
    sb._stripe = lambda: _S()
    sb.STRIPE_PRICES = {('basic', 'monthly'): 'price_x', ('pro', 'monthly'): 'price_y'}

    try:
        with app_mod.app.test_request_context(
                '/api/stripe/checkout', method='POST',
                json={'plan': 'basic', 'billing': 'monthly'}):
            login_user(User(1, 'a@b.es', 'A', 'agricultor', 1, plan=plan))
            resp = sb.stripe_checkout()
            if isinstance(resp, tuple):
                cuerpo, codigo = resp
                return f"{codigo} {cuerpo.get_json().get('error')}", creadas
            return 'ABRE PAGO', creadas
    finally:
        conn.close()


def test_el_checkout_rechaza_a_una_cuenta_de_cortesia():
    """Lo que de verdad impide el cargo. Aunque alguien llegue al endpoint por
    su cuenta, sin pasar por los botones, no se abre ningún pago."""
    resultado, creadas = _checkout('basic')
    check("responde 403 plan_de_cortesia", resultado == '403 plan_de_cortesia')
    check("y NO se crea sesión de pago en Stripe", creadas == [])


def test_el_checkout_deja_pagar_a_un_cliente_nuevo():
    """El caso que no se puede romper: un `trial` tiene que poder comprar."""
    resultado, creadas = _checkout('trial')
    check("abre el pago", resultado == 'ABRE PAGO')
    check("y se crea la sesión", len(creadas) == 1)


def test_el_checkout_deja_cambiar_de_plan_a_quien_ya_paga():
    resultado, _ = _checkout('basic', customer='cus_1', subscription='sub_1')
    check("un cliente de pago puede cambiar de plan", resultado == 'ABRE PAGO')


if __name__ == '__main__':
    print("\n== Cuentas con el plan regalado desde el panel ==\n")
    for nombre, fn in sorted(list(globals().items())):
        if nombre.startswith('test_') and callable(fn):
            print(f"{nombre}:")
            fn()
    print("\nTodo en verde.\n")
