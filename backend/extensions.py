"""
extensions.py — Singletons de Flask que se inicializan con init_app().
Importar desde aquí para evitar imports circulares entre blueprints y app.py.
"""
import datetime
from flask import jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin
from db import get_db, one

# default_limits es un backstop anti-DoS/scraping para las rutas SIN @limiter.limit
# propio (las sensibles como login/registro ya tienen límites estrictos que, al ser
# explícitos, reemplazan a estos defaults para esas rutas). Los valores son holgados
# a propósito: muy por encima del uso real de un agricultor (incluidas ráfagas
# legítimas como verificar 50+ parcelas SIGPAC), pero cortan el abuso trivial.
limiter = Limiter(get_remote_address, default_limits=["3000 per hour", "300 per minute"])
login_manager = LoginManager()


# Días que un plan de pago sigue dando acceso después de vencer su periodo.
#
# Es el colchón para que un webhook de renovación perdido no le corte el
# cuaderno a un agricultor que sí ha pagado. Pasado el margen no se corta a
# ciegas: `guard_active_plan` le pregunta a Stripe por el estado real antes de
# denegar nada (ver app.py).
MARGEN_SUSCRIPCION_DIAS = 5


def _a_fecha(valor):
    """Normaliza a datetime lo que venga de la BD (TIMESTAMP o texto ISO).

    Devuelve None si no hay valor o si no se puede interpretar. Un formato que
    no se entiende NO puede colar como fecha válida: quien llama decide, y aquí
    se decide tratarlo como "no hay fecha".
    """
    if not valor:
        return None
    if isinstance(valor, datetime.datetime):
        return valor
    try:
        return datetime.datetime.fromisoformat(str(valor).replace('Z', ''))
    except ValueError:
        return None


def compute_plan_status(plan, trial_ends_at, role, subscription_ends_at=None):
    """Calcula el estado de plan de un usuario a partir de datos crudos de BD.

    Devuelve (label, active):
      label  -> 'pro' | 'basic' | 'trial' | 'expired'
      active -> True si el usuario puede escribir datos en su cuaderno.

    Replica exactamente el comportamiento que antes vivía repartido entre
    User.plan_is_active() y User.plan_label(), para poder reutilizarlo
    también con filas de BD que no pasan por un objeto User (p.ej. el
    listado del panel de admin).

    Sobre `subscription_ends_at`: un plan de pago **caduca**. Antes esta
    función devolvía True para basic/pro/premium sin mirar ninguna fecha, así
    que una cuenta a la que se le perdiera el webhook de cancelación escribía
    gratis para siempre y no saltaba ningún error en ninguna parte.

    `subscription_ends_at` a NULL sigue dando acceso **a propósito**: son las
    altas que no vienen de Stripe (cuentas de prueba, un plan concedido a mano
    desde el panel de admin). Ahí no hay periodo que vencer.

    Esta función es pura y se ejecuta en cada petición: aquí no se llama a
    Stripe ni se toca la BD. Confirmar con Stripe una fecha vencida es cosa de
    `guard_active_plan`, que solo corre en escrituras.
    """
    def _is_active():
        if role == 'admin':
            return True
        if plan in ('basic', 'pro', 'premium'):
            if subscription_ends_at in (None, ''):
                return True     # alta sin periodo (manual/admin): no vence
            fin = _a_fecha(subscription_ends_at)
            if fin is None:
                # Hay algo escrito y no se entiende. No puede colar como plan
                # al día: eso sería exactamente el agujero que esto cierra.
                return False
            limite = fin + datetime.timedelta(days=MARGEN_SUSCRIPCION_DIAS)
            return datetime.datetime.utcnow() < limite
        if plan == 'trial' and trial_ends_at:
            ends = _a_fecha(trial_ends_at)
            return ends is not None and datetime.datetime.utcnow() < ends
        return False

    active = _is_active()
    if plan in ('basic', 'pro', 'premium'):
        # Un plan de pago vencido se etiqueta 'expired', no 'pro': es lo que
        # hace que la app le enseñe el cartel de renovar en vez de decirle que
        # tiene un plan activo mientras le bloquea cada guardado.
        label = plan if active else 'expired'
    elif plan == 'trial':
        label = 'trial' if active else 'expired'
    else:
        label = 'expired'
    return label, active


# Nº máximo de explotaciones por plan. Basic/trial → 1 (mono).
# Admin, plan `premium` y súper usuarios (unlimited_explotaciones) → sin tope.
PRO_EXPLOTACIONES_LIMIT = 5


def explotaciones_limit(plan, role, unlimited=False):
    """Nº máximo de explotaciones permitidas, o None si es ilimitado.

    - Admin, plan `premium` y súper usuarios (`unlimited_explotaciones`) → None (sin tope).
    - `pro` (29,99 €/mes) → PRO_EXPLOTACIONES_LIMIT titulares.
    - `basic` (14,99 €/mes) y `trial` → 1 (mono-explotación, fuerza el upsell).
    """
    if role == 'admin' or unlimited or plan == 'premium':
        return None
    if plan == 'pro':
        return PRO_EXPLOTACIONES_LIMIT
    return 1


def plan_allows_multi(plan, role, unlimited=False):
    """True si el usuario puede tener más de una explotación.

    El plan `basic` (14,99 €/mes) es mono-explotación; `pro` (29,99 €/mes) es multi
    (hasta PRO_EXPLOTACIONES_LIMIT). `trial` se queda en mono para forzar el
    upsell. Admin y súper usuarios siempre multi.
    """
    limit = explotaciones_limit(plan, role, unlimited)
    return limit is None or limit > 1


def es_cuenta_cortesia(plan, stripe_customer_id, stripe_subscription_id):
    """True si el plan de pago se concedió a mano, sin pasar por Stripe.

    Son las cuentas que se dan desde el panel de admin para que alguien pruebe
    la app: el piloto, un amigo, una demo. Stripe **no les cobra nada**, porque
    no existe ninguna suscripción a su nombre.

    El problema que esto resuelve es el contrario: que se cobren ellos solos. En
    la pantalla de planes, el botón de contratar solo se oculta en la tarjeta
    del plan que ya tienes, así que a una cuenta de cortesía le sigue saliendo
    "Contratar" en las demás — y a quien tenga `premium`, que ya no es una
    tarjeta, **le salen todas**. Un toque y hay un cobro real de alguien a quien
    le regalaste el acceso.

    Cómo se distinguen sin inventar ninguna columna: quien pagó de verdad tiene
    `stripe_customer_id`, y quien todavía no ha pagado está en `trial`. Un plan
    de pago sin rastro de Stripe solo puede venir del panel de admin.

    Para que una de estas cuentas pueda pagar de verdad, hay que devolverla a
    `trial` desde el panel primero. Es a propósito: que pase por la puerta.
    """
    return (plan in ('basic', 'pro', 'premium')
            and not stripe_customer_id
            and not stripe_subscription_id)


class User(UserMixin):
    def __init__(self, id, email, nombre, role, active,
                 plan='trial', trial_ends_at=None, subscription_ends_at=None,
                 unlimited_explotaciones=0, pago_fallido_desde=None,
                 stripe_customer_id=None, stripe_subscription_id=None):
        self.id = id
        self.email = email
        self.nombre = nombre
        self.role = role
        self.active = active
        self.plan = plan
        self.trial_ends_at = trial_ends_at
        self.subscription_ends_at = subscription_ends_at
        self.unlimited_explotaciones = bool(unlimited_explotaciones)
        # Fecha del primer cobro fallido, o None. No afecta al acceso: el
        # agricultor sigue pudiendo anotar mientras Stripe reintenta.
        self.pago_fallido_desde = pago_fallido_desde
        # Plan concedido a mano desde el panel, sin suscripción en Stripe. No se
        # guardan los identificadores en el objeto: solo hace falta saber si los
        # hay o no.
        self.es_cortesia = es_cuenta_cortesia(plan, stripe_customer_id, stripe_subscription_id)

    def plan_is_active(self):
        """True si el usuario puede escribir datos (trial vigente, basic o pro)."""
        _, active = compute_plan_status(self.plan, self.trial_ends_at, self.role,
                                        self.subscription_ends_at)
        return active

    def plan_label(self):
        """Estado legible para el frontend."""
        label, _ = compute_plan_status(self.plan, self.trial_ends_at, self.role,
                                       self.subscription_ends_at)
        return label

    def plan_allows_multi(self):
        """True si el plan permite varias explotaciones (feature `pro`)."""
        return plan_allows_multi(self.plan, self.role, self.unlimited_explotaciones)

    def explotaciones_limit(self):
        """Nº máximo de explotaciones para este usuario, o None si ilimitado."""
        return explotaciones_limit(self.plan, self.role, self.unlimited_explotaciones)


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    u = one(conn, "SELECT * FROM users WHERE id=? AND active=1", (int(user_id),))
    conn.close()
    if not u:
        return None
    return User(u['id'], u['email'], u['nombre'], u['role'], u['active'],
                u.get('plan', 'trial'), u.get('trial_ends_at'), u.get('subscription_ends_at'),
                u.get('unlimited_explotaciones', 0), u.get('pago_fallido_desde'),
                u.get('stripe_customer_id'), u.get('stripe_subscription_id'))


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "No autenticado"}), 401
