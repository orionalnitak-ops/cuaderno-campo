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

limiter = Limiter(get_remote_address, default_limits=[])
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
        if plan in ('basic', 'pro'):
            return True
        if plan == 'trial' and trial_ends_at:
            ends = trial_ends_at
            if isinstance(ends, str):
                ends = datetime.datetime.fromisoformat(ends.replace('Z', ''))
            return datetime.datetime.utcnow() < ends
        return False

    active = _is_active()
    if plan in ('basic', 'pro'):
        label = plan
    elif plan == 'trial':
        label = 'trial' if active else 'expired'
    else:
        label = 'expired'
    return label, active


def plan_allows_multi(plan, role):
    """True si el usuario puede tener varias explotaciones (feature del plan `pro`).

    El plan `basic` (9,99 €) es mono-explotación; `pro` (14,99 €) es multi.
    `trial` se queda en mono para forzar el upsell. Admin siempre multi.
    """
    return role == 'admin' or plan == 'pro'


class User(UserMixin):
    def __init__(self, id, email, nombre, role, active,
                 plan='trial', trial_ends_at=None, subscription_ends_at=None):
        self.id = id
        self.email = email
        self.nombre = nombre
        self.role = role
        self.active = active
        self.plan = plan
        self.trial_ends_at = trial_ends_at
        self.subscription_ends_at = subscription_ends_at

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
        return plan_allows_multi(self.plan, self.role)


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    u = one(conn, "SELECT * FROM users WHERE id=? AND active=1", (int(user_id),))
    conn.close()
    if not u:
        return None
    return User(u['id'], u['email'], u['nombre'], u['role'], u['active'],
                u.get('plan', 'trial'), u.get('trial_ends_at'), u.get('subscription_ends_at'))


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "No autenticado"}), 401
