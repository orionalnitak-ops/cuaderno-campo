"""
blueprints/stripe_bp.py — /api/stripe/*
"""
import datetime
import logging
import os

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from db import get_db, one

bp = Blueprint('stripe_bp', __name__)
logger = logging.getLogger(__name__)

STRIPE_SECRET_KEY      = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET  = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_PRICES = {
    ('basic',   'monthly'): os.environ.get('STRIPE_PRICE_BASIC_MONTHLY', ''),
    ('basic',   'yearly'):  os.environ.get('STRIPE_PRICE_BASIC_YEARLY', ''),
    ('pro',     'monthly'): os.environ.get('STRIPE_PRICE_PRO_MONTHLY', ''),
    ('pro',     'yearly'):  os.environ.get('STRIPE_PRICE_PRO_YEARLY', ''),
    # Premium está descartado desde julio de 2026 y no se ofrece en la pantalla
    # de planes. La clave se mantiene (vacía) para no romper a quien ya lo tuviera.
    ('premium', 'yearly'):  os.environ.get('STRIPE_PRICE_PREMIUM_YEARLY', ''),
}

# Planes que conceden acceso de pago (usados para validar metadata del webhook).
_PLANES_PAGO = ('basic', 'pro', 'premium')

# ─────────────────────────────────────────────────────────────────────
# Qué hacemos con el acceso del agricultor según el estado de Stripe.
#
# La distinción que importa es entre "el cobro ha fallado pero Stripe sigue
# reintentándolo" y "esto ya no se cobra". Stripe reintenta durante días y la
# mayoría de esos cobros acaban entrando: tarjeta caducada, sin saldo ese día,
# confirmación del banco que no se vio a tiempo. Cortarle el cuaderno a un
# agricultor en plena campaña al primer intento fallido lo pierde como cliente
# por algo que se iba a cobrar solo.
# ─────────────────────────────────────────────────────────────────────
ESTADOS_ALTA   = ('active', 'trialing')
# past_due = ha fallado un cobro y Stripe sigue intentándolo. Mantiene acceso.
ESTADOS_GRACIA = ('past_due',)
# Se acabó: cancelada, agotados los reintentos, o el primer pago nunca entró.
ESTADOS_CORTE  = ('canceled', 'unpaid', 'incomplete_expired')


def accion_suscripcion(status):
    """Traduce el estado de una suscripción de Stripe a lo que hace la app.

    Devuelve 'alta', 'gracia', 'corte', o None si no hay que tocar nada
    (p. ej. `incomplete`: el primer pago aún no ha entrado, así que no da
    acceso, pero tampoco tiene por qué quitar el que ya hubiera).
    """
    if status in ESTADOS_ALTA:
        return 'alta'
    if status in ESTADOS_GRACIA:
        return 'gracia'
    if status in ESTADOS_CORTE:
        return 'corte'
    return None


def aplicar_gracia(conn, user_id, ahora=None):
    """Marca que hay un cobro caído SIN tocar el plan ni el acceso.

    Solo se guarda la fecha del primer fallo (`WHERE ... IS NULL`), porque
    Stripe manda un `past_due` por cada reintento y el aviso tiene que poder
    decir desde cuándo falla, no desde el último intento.
    """
    ahora = ahora or datetime.datetime.utcnow()
    conn.execute(
        "UPDATE users SET pago_fallido_desde=? WHERE id=? AND pago_fallido_desde IS NULL",
        (ahora.strftime('%Y-%m-%d %H:%M:%S'), user_id)
    )


def cortar_acceso(conn, user_id, olvidar_suscripcion=False):
    """Baja al usuario a solo lectura: sigue viendo y descargando su cuaderno,
    pero no puede anotar nada nuevo (ver guard_active_plan en app.py).

    Limpia también el aviso de impago: si la suscripción ya está cortada, el
    cartel que toca es el rojo de "renueva", no el naranja de "revisa tu
    tarjeta".
    """
    if olvidar_suscripcion:
        conn.execute(
            "UPDATE users SET plan='trial', subscription_ends_at=NULL, "
            "pago_fallido_desde=NULL, stripe_subscription_id=NULL WHERE id=?",
            (user_id,)
        )
    else:
        conn.execute(
            "UPDATE users SET plan='trial', subscription_ends_at=NULL, "
            "pago_fallido_desde=NULL WHERE id=?",
            (user_id,)
        )


def reconciliar_suscripcion(user_id):
    """Le pregunta a Stripe el estado real de una suscripción y deja la BD al día.

    La suscripción se lee AQUÍ a partir del `user_id`, y no se acepta por
    parámetro a propósito: si se pudiera pasar desde fuera, un llamador futuro
    podría verificar la suscripción de uno y escribir el resultado en la ficha
    de otro. Al leerla de la fila del propio usuario, esa confusión no cabe.

    Se usa cuando la fecha local ya venció con margen: o el agricultor dejó de
    pagar de verdad, o se perdió el webhook de una renovación normal. Desde
    aquí no se puede distinguir, así que se pregunta a la fuente en vez de
    adivinar. Devuelve True si conserva el acceso.

    Solo se llama desde `guard_active_plan` y solo cuando iba a denegar una
    escritura, así que Stripe se consulta en el caso raro. Después la BD queda
    con la fecha buena (si sigue pagando) o con el plan ya bajado (si no), y no
    se vuelve a preguntar.

    **Ante la duda, no da acceso.** Si Stripe no contesta o no hay clave
    configurada, se deniega: un fallo aquí no puede convertirse en barra libre.
    """
    s = _stripe()
    sub_id = None
    if s:
        conn = get_db()
        try:
            fila = one(conn, "SELECT stripe_subscription_id FROM users WHERE id=?", (user_id,))
        finally:
            conn.close()
        sub_id = (fila or {}).get('stripe_subscription_id')

    if not s or not sub_id:
        logger.error('Suscripcion vencida del usuario %s sin poder verificar en '
                     'Stripe (clave o sub_id ausente). Acceso denegado.', user_id)
        return False

    try:
        sub = s.Subscription.retrieve(sub_id)
    except Exception as err:
        logger.error('Stripe no responde al verificar la suscripcion del usuario '
                     '%s: %s. Acceso denegado.', user_id, err)
        return False

    status = sub.get('status')
    accion = accion_suscripcion(status)
    conn = get_db()
    try:
        if accion in ('alta', 'gracia'):
            # Sigue siendo cliente: la fecha local estaba obsoleta porque se
            # perdió el webhook. Se pone la buena y recupera el acceso.
            #
            # NO SE TOCA `plan` AQUÍ, y no es un olvido. Dos escrituras
            # simultáneas de la misma cuenta pueden consultar Stripe a la vez y
            # escribir en cualquier orden. Como esta rama solo mueve la fecha,
            # una respuesta tardía de "sigue pagando" jamás puede resucitar a
            # una cuenta que la otra acaba de bajar a `trial`: la carrera es
            # inocua justo por esto. Quien añada aquí un `plan=?` convierte un
            # detalle de concurrencia en una forma de recuperar acceso.
            # Lo fija test_una_alta_tardia_no_resucita_un_corte.
            fin = sub.get('current_period_end')
            nueva = (datetime.datetime.utcfromtimestamp(fin) if fin
                     else datetime.datetime.utcnow() + datetime.timedelta(days=1))
            conn.execute(
                "UPDATE users SET subscription_ends_at=? WHERE id=?",
                (nueva.strftime('%Y-%m-%d %H:%M:%S'), user_id)
            )
            if accion == 'gracia':
                aplicar_gracia(conn, user_id)
            conn.commit()
            logger.warning('Suscripcion del usuario %s revalidada contra Stripe '
                           '(estado %s): se habia perdido un webhook.', user_id, status)
            return True

        # 'corte' o estado desconocido: Stripe confirma que ya no se cobra.
        cortar_acceso(conn, user_id)
        conn.commit()
        logger.warning('Suscripcion del usuario %s cortada tras verificar en '
                       'Stripe (estado %s).', user_id, status)
        return False
    finally:
        conn.close()


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
                accion = accion_suscripcion(status)
                if accion == 'alta':
                    # Pago al día: se limpia cualquier aviso de impago previo,
                    # o el agricultor que ya ha pagado se quedaría con el
                    # cartel de "revisa tu tarjeta" para siempre.
                    conn.execute(
                        "UPDATE users SET plan=?, subscription_ends_at=?, stripe_customer_id=?, "
                        "stripe_subscription_id=?, pago_fallido_desde=NULL WHERE id=?",
                        (plan, sub_end, customer, sub_id, int(uid_meta))
                    )
                elif accion == 'gracia':
                    aplicar_gracia(conn, int(uid_meta))
                elif accion == 'corte':
                    cortar_acceso(conn, int(uid_meta))
                conn.commit()

        elif ev_type == 'customer.subscription.deleted':
            sub      = obj
            uid_meta = sub.get('metadata', {}).get('user_id')
            if uid_meta:
                cortar_acceso(conn, int(uid_meta), olvidar_suscripcion=True)
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
                        "UPDATE users SET plan=?, stripe_customer_id=?, stripe_subscription_id=?, "
                        "subscription_ends_at=?, pago_fallido_desde=NULL WHERE id=?",
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
