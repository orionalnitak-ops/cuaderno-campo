"""
blueprints/stripe_bp.py — /api/stripe/*
"""
import datetime
import os

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from db import get_db, one

bp = Blueprint('stripe_bp', __name__)

STRIPE_SECRET_KEY      = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET  = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_PRICES = {
    ('basic',   'monthly'): os.environ.get('STRIPE_PRICE_BASIC_MONTHLY', ''),
    ('basic',   'yearly'):  os.environ.get('STRIPE_PRICE_BASIC_YEARLY', ''),
    ('pro',     'monthly'): os.environ.get('STRIPE_PRICE_PRO_MONTHLY', ''),
    ('pro',     'yearly'):  os.environ.get('STRIPE_PRICE_PRO_YEARLY', ''),
    # Premium es solo anual (200 €/año de momento). Crear el Price en Stripe
    # y exponerlo en STRIPE_PRICE_PREMIUM_YEARLY.
    ('premium', 'yearly'):  os.environ.get('STRIPE_PRICE_PREMIUM_YEARLY', ''),
}

# Planes que conceden acceso de pago (usados para validar metadata del webhook).
_PLANES_PAGO = ('basic', 'pro', 'premium')


def _stripe():
    """Devuelve el módulo stripe inicializado, o None si no hay clave configurada."""
    if not STRIPE_SECRET_KEY:
        return None
    import stripe as _s
    _s.api_key = STRIPE_SECRET_KEY
    return _s


def _plan_from_price(stripe_price_id):
    """Identifica el plan ('basic'/'pro'/'premium') a partir del Price ID de Stripe."""
    for (plan, _), pid in STRIPE_PRICES.items():
        if pid and pid == stripe_price_id:
            return plan
    return 'basic'


@bp.route('/api/stripe/checkout', methods=['POST'])
@login_required
def stripe_checkout():
    """Crea una sesión de Stripe Checkout y devuelve la URL de pago."""
    s = _stripe()
    if not s:
        return jsonify({"error": "Stripe no configurado"}), 503

    data    = request.json or {}
    plan    = data.get('plan', 'basic')
    billing = data.get('billing', 'monthly')

    price_id = STRIPE_PRICES.get((plan, billing))
    if not price_id:
        return jsonify({"error": "Plan o intervalo no válido"}), 400

    base_url = request.host_url.rstrip('/')

    conn = get_db()
    u = one(conn, "SELECT stripe_customer_id FROM users WHERE id=?", (current_user.id,))
    conn.close()
    customer_id = u.get('stripe_customer_id') if u else None

    try:
        params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{base_url}/pago-completado?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url":  f"{base_url}/#planes",
            "metadata": {
                "user_id": str(current_user.id),
                "plan":    plan,
            },
            "subscription_data": {
                "metadata": {"user_id": str(current_user.id), "plan": plan}
            },
        }
        if customer_id:
            params["customer"] = customer_id
        else:
            params["customer_email"] = current_user.email

        session_obj = s.checkout.Session.create(**params)
        return jsonify({"url": session_obj.url})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Stripe checkout error: %s", e)
        return jsonify({"error": "Error al crear sesión de pago"}), 500


@bp.route('/api/stripe/portal', methods=['POST'])
@login_required
def stripe_portal():
    """Crea una sesión del portal de cliente de Stripe (gestión de suscripción)."""
    s = _stripe()
    if not s:
        return jsonify({"error": "Stripe no configurado"}), 503

    conn = get_db()
    u = one(conn, "SELECT stripe_customer_id FROM users WHERE id=?", (current_user.id,))
    conn.close()

    customer_id = u.get('stripe_customer_id') if u else None
    if not customer_id:
        return jsonify({"error": "No tienes una suscripción activa en Stripe"}), 400

    try:
        portal = s.billing_portal.Session.create(
            customer=customer_id,
            return_url=request.host_url,
        )
        return jsonify({"url": portal.url})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Stripe portal error: %s", e)
        return jsonify({"error": "Error al abrir el portal"}), 500


@bp.route('/api/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Recibe eventos de Stripe y actualiza el plan del usuario en BD."""
    s = _stripe()
    if not s:
        return jsonify({"error": "Stripe no configurado"}), 503

    payload = request.get_data()
    sig     = request.headers.get('Stripe-Signature', '')

    try:
        event = s.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Stripe webhook signature error: %s", e)
        return jsonify({"error": "Invalid signature"}), 400

    ev_type = event['type']
    obj     = event['data']['object']

    conn = get_db()
    try:
        if ev_type in ('customer.subscription.created', 'customer.subscription.updated'):
            sub        = obj
            customer   = sub.get('customer')
            status     = sub.get('status')
            items      = sub.get('items', {}).get('data', [])
            price_id   = items[0]['price']['id'] if items else None
            plan       = _plan_from_price(price_id)
            period_end = sub.get('current_period_end')
            sub_end    = (datetime.datetime.utcfromtimestamp(period_end).strftime('%Y-%m-%d %H:%M:%S')
                          if period_end else None)
            sub_id     = sub.get('id')
            uid_meta   = sub.get('metadata', {}).get('user_id')

            if uid_meta:
                if status == 'active':
                    conn.execute(
                        "UPDATE users SET plan=?, subscription_ends_at=?, stripe_customer_id=?, stripe_subscription_id=? WHERE id=?",
                        (plan, sub_end, customer, sub_id, int(uid_meta))
                    )
                elif status in ('canceled', 'unpaid', 'past_due'):
                    conn.execute(
                        "UPDATE users SET plan='trial', subscription_ends_at=NULL WHERE id=?",
                        (int(uid_meta),)
                    )
                conn.commit()

        elif ev_type == 'customer.subscription.deleted':
            sub      = obj
            uid_meta = sub.get('metadata', {}).get('user_id')
            if uid_meta:
                conn.execute(
                    "UPDATE users SET plan='trial', subscription_ends_at=NULL, stripe_subscription_id=NULL WHERE id=?",
                    (int(uid_meta),)
                )
                conn.commit()

        elif ev_type == 'checkout.session.completed':
            session_obj = obj
            customer    = session_obj.get('customer')
            uid_meta    = session_obj.get('metadata', {}).get('user_id')
            plan_meta   = session_obj.get('metadata', {}).get('plan')
            sub_id      = session_obj.get('subscription')
            if uid_meta and customer:
                if plan_meta in _PLANES_PAGO:
                    import datetime as _dt
                    sub_end = (_dt.datetime.utcnow() + _dt.timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')
                    conn.execute(
                        "UPDATE users SET plan=?, stripe_customer_id=?, stripe_subscription_id=?, subscription_ends_at=? WHERE id=?",
                        (plan_meta, customer, sub_id, sub_end, int(uid_meta))
                    )
                else:
                    conn.execute(
                        "UPDATE users SET stripe_customer_id=? WHERE id=?",
                        (customer, int(uid_meta))
                    )
                conn.commit()
    finally:
        conn.close()

    return jsonify({"status": "ok"})
