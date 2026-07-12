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


def compute_plan_status(plan, trial_ends_at, role):
    """Calcula el estado de plan de un usuario a partir de datos crudos de BD.

    Devuelve (label, active):
      label  -> 'pro' | 'basic' | 'trial' | 'expired'
      active -> True si el usuario puede escribir datos en su cuaderno.

    Replica exactamente el comportamiento que antes vivía repartido entre
    User.plan_is_active() y User.plan_label(), para poder reutilizarlo
    también con filas de BD que no pasan por un objeto User (p.ej. el
    listado del panel de admin).
    """
    def _is_active():
        if role == 'admin':
            return True
        if plan in ('basic', 'pro', 'premium'):
            return True
        if plan == 'trial' and trial_ends_at:
            ends = trial_ends_at
            if isinstance(ends, str):
                ends = datetime.datetime.fromisoformat(ends.replace('Z', ''))
            return datetime.datetime.utcnow() < ends
        return False

    active = _is_active()
    if plan in ('basic', 'pro', 'premium'):
        label = plan
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
    - `pro` (14,99 €) → PRO_EXPLOTACIONES_LIMIT titulares.
    - `basic` (9,99 €) y `trial` → 1 (mono-explotación, fuerza el upsell).
    """
    if role == 'admin' or unlimited or plan == 'premium':
        return None
    if plan == 'pro':
        return PRO_EXPLOTACIONES_LIMIT
    return 1


def plan_allows_multi(plan, role, unlimited=False):
    """True si el usuario puede tener más de una explotación.

    El plan `basic` (9,99 €) es mono-explotación; `pro` (14,99 €) es multi
    (hasta PRO_EXPLOTACIONES_LIMIT). `trial` se queda en mono para forzar el
    upsell. Admin y súper usuarios siempre multi.
    """
    limit = explotaciones_limit(plan, role, unlimited)
    return limit is None or limit > 1


class User(UserMixin):
    def __init__(self, id, email, nombre, role, active,
                 plan='trial', trial_ends_at=None, subscription_ends_at=None,
                 unlimited_explotaciones=0):
        self.id = id
        self.email = email
        self.nombre = nombre
        self.role = role
        self.active = active
        self.plan = plan
        self.trial_ends_at = trial_ends_at
        self.subscription_ends_at = subscription_ends_at
        self.unlimited_explotaciones = bool(unlimited_explotaciones)

    def plan_is_active(self):
        """True si el usuario puede escribir datos (trial vigente, basic o pro)."""
        _, active = compute_plan_status(self.plan, self.trial_ends_at, self.role)
        return active

    def plan_label(self):
        """Estado legible para el frontend."""
        label, _ = compute_plan_status(self.plan, self.trial_ends_at, self.role)
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
                u.get('unlimited_explotaciones', 0))


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "No autenticado"}), 401
