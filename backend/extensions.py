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
        if self.role == 'admin':
            return True
        if self.plan in ('basic', 'pro'):
            return True
        if self.plan == 'trial' and self.trial_ends_at:
            ends = self.trial_ends_at
            if isinstance(ends, str):
                ends = datetime.datetime.fromisoformat(ends.replace('Z', ''))
            return datetime.datetime.utcnow() < ends
        return False

    def plan_label(self):
        """Estado legible para el frontend."""
        if self.plan in ('basic', 'pro'):
            return self.plan
        if self.plan == 'trial':
            if self.plan_is_active():
                return 'trial'
            return 'expired'
        return 'expired'


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
