"""
blueprints/stripe_bp.py — /api/stripe/*
"""
import datetime
import logging
import os

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from db import get_db, one
from extensions import es_cuenta_cortesia

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

# Tasa de IVA (21% incluido) creada a mano en Stripe (NO es Stripe Tax, es
# gratis). Se aplica a la suscripción para que la factura desglose base + IVA
# y sea deducible por el agricultor autónomo. Cada entorno (test/live) tiene su
# propio `txr_...`, por eso viaja en variable de entorno como los precios.
STRIPE_TAX_RATE_IVA = os.environ.get('STRIPE_TAX_RATE_IVA', '')

# Planes que conceden acceso de pago (usados para validar metadata del webhook).
_PLANES_PAGO = ('basic', 'pro', 'premium')

# ─────────────────────────────────────────────────────────────────────
# Hasta cuándo está pagado el cuaderno.
#
# Stripe MOVIÓ este dato en la versión de API 2025-03-31.basil: dejó de estar
# en la suscripción y pasó a cada item de la suscripción. Es un cambio
# incompatible declarado como tal en su changelog
# ("deprecate-subscription-current-period-start-and-end"). El webhook de
# producción se creó con 2026-07-29.dahlia, muy posterior, así que el sitio
# bueno es el item; se conserva el respaldo al sitio antiguo por si algún
# endpoint queda anclado a una versión previa.
#
# Leerlo del sitio equivocado no es un detalle: devuelve None, y un None
# acababa escrito como NULL en `subscription_ends_at`. NULL significa en esta
# app "plan concedido a mano, no vence nunca" (ver es_cuenta_cortesia), así
# que el agricultor pagaba un mes y se quedaba el cuaderno para siempre.
# ─────────────────────────────────────────────────────────────────────
# Margen corto cuando Stripe no manda la fecha: al día siguiente
# guard_active_plan le pregunta a Stripe y escribe la buena.
MARGEN_SIN_FECHA_DIAS = 1
# Acceso provisional del alta por checkout, que no trae el periodo.
DIAS_PROVISIONALES = {'monthly': 31, 'yearly': 366}


def fin_de_periodo(sub):
    """Timestamp en que vence el periodo pagado, o None si no viene.

    Con varios items de intervalos distintos (Stripe lo permite) cada uno
    vence en su fecha: se devuelve la MÁS CERCANA. Conceder hasta la más
    lejana sería regalar acceso que no se ha pagado.
    """
    sub   = sub or {}
    items = (sub.get('items') or {}).get('data') or []
    fines = [i.get('current_period_end') for i in items
             if isinstance(i, dict) and i.get('current_period_end')]
    if fines:
        return min(fines)
    return sub.get('current_period_end')


def fecha_fin_segura(sub):
    """La fecha lista para guardar en `subscription_ends_at`. NUNCA None.

    Falla CERRADO: si Stripe no manda el periodo (campo movido otra vez,
    evento con una forma que no conocemos), se concede el margen corto en
    lugar de dejar la columna vacía. Escribir NULL aquí sería conceder
    acceso permanente y gratis, que es el peor error posible en este punto.
    """
    fin   = fin_de_periodo(sub)
    fecha = (datetime.datetime.utcfromtimestamp(fin) if fin
             else datetime.datetime.utcnow() + datetime.timedelta(days=MARGEN_SIN_FECHA_DIAS))
    return fecha.strftime('%Y-%m-%d %H:%M:%S')


def dias_provisionales(billing):
    """Días que concede el alta por checkout hasta que llegue el evento de la
    suscripción con el periodo real. Un intervalo desconocido concede el
    mínimo: pasarse de largo regala meses sin cobrar."""
    return DIAS_PROVISIONALES.get(billing, DIAS_PROVISIONALES['monthly'])

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


def _metadata_coherente(conn, uid_meta, customer):
    """True si el `user_id` que viene en el metadata de Stripe encaja con el
    cliente del evento.

    Hoy no hay forma conocida de que no encaje: el metadata lo escribe nuestro
    propio checkout con `current_user.id`, nunca con nada que mande el
    navegador, y crear una suscripción en esta cuenta exige la clave secreta.
    Esto es un cinturón por si un cambio futuro lo estropea: escribir el plan en
    la ficha de otro agricultor sería de las peores cosas que pueden pasar aquí.

    **Se acepta cuando todavía no hay cliente guardado, y es deliberado.** En un
    alta nueva `stripe_customer_id` está a NULL hasta que se procesa el evento
    que lo escribe, y Stripe NO garantiza el orden de entrega. Rechazar el
    evento en ese caso dejaría al agricultor pagando sin recibir su plan: el
    control se volvería contra el cliente honrado, que es a quien menos falta
    hace protegerse.
    """
    if not customer:
        return True
    try:
        fila = one(conn, "SELECT stripe_customer_id FROM users WHERE id=?", (int(uid_meta),))
    except (TypeError, ValueError):
        logger.error('Webhook con user_id de metadata ilegible (%r). Ignorado.', uid_meta)
        return False
    if not fila:
        logger.error('Webhook para un user_id inexistente (%s). Ignorado.', uid_meta)
        return False
    guardado = fila.get('stripe_customer_id')
    if guardado and guardado != customer:
        logger.error('Webhook incoherente: el cliente %s no es el del usuario %s (%s). '
                     'Ignorado.', customer, uid_meta, guardado)
        return False
    return True


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
        # Dos conexiones distintas, a propósito: una para leer y otra para
        # escribir, con la llamada a Stripe en medio y SIN conexión abierta.
        # Sostenerla durante una petición HTTP a un tercero deja una conexión
        # del pool retenida a merced de la latencia de Stripe. No consolidar.
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
            fin = fin_de_periodo(sub)
            nueva = (datetime.datetime.utcfromtimestamp(fin) if fin
                     else datetime.datetime.utcnow() + datetime.timedelta(
                         days=MARGEN_SIN_FECHA_DIAS))
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
    u = one(conn, "SELECT plan, stripe_customer_id, stripe_subscription_id FROM users WHERE id=?",
            (current_user.id,))
    conn.close()
    customer_id = u.get('stripe_customer_id') if u else None

    # Cuenta con el plan concedido a mano desde el panel: no se le abre el pago.
    # Ya tiene acceso gratis, así que contratar aquí sería cobrarle por algo que
    # le regalaste. Se lee de la BD y no de la sesión para decidir sobre el
    # estado de AHORA, que es el que va a acabar en un cargo.
    if u and es_cuenta_cortesia(u.get('plan'), customer_id, u.get('stripe_subscription_id')):
        logger.warning('Checkout bloqueado: la cuenta %s tiene plan de cortesía (%s).',
                       current_user.id, u.get('plan'))
        return jsonify({
            "error": "plan_de_cortesia",
            "message": ("Tu cuenta ya tiene el plan activo sin coste, así que no hay nada "
                        "que contratar. Si quieres pasar a una suscripción de pago, "
                        "escríbenos a cuadernodigital@tualiado.es y lo preparamos."),
        }), 403

    try:
        params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            # Recoger NIF/CIF y dirección fiscal en el checkout: los agricultores
            # son autónomos/empresas y necesitan factura COMPLETA para deducir el
            # IVA (la simplificada solo permite deducir IRPF). Es gratis:
            # tax_id_collection NO es Stripe Tax. Los datos quedan en el Customer.
            "tax_id_collection": {"enabled": True},
            "billing_address_collection": "required",
            "success_url": f"{base_url}/pago-completado?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url":  f"{base_url}/#planes",
            # `billing` viaja en el metadata porque el evento
            # checkout.session.completed no dice si es mensual o anual, y de
            # eso depende el acceso provisional que se concede al cobrar.
            "metadata": {
                "user_id": str(current_user.id),
                "plan":    plan,
                "billing": billing,
            },
            "subscription_data": {
                "metadata": {"user_id": str(current_user.id), "plan": plan,
                             "billing": billing}
            },
        }
        # El 21% de IVA se aplica como tasa manual (inclusive) para que la factura
        # desglose base + IVA y el agricultor pueda deducir. `default_tax_rates` en
        # subscription_data hace que TODAS las facturas de la suscripción lo lleven,
        # no solo la primera. Si la variable está vacía (entorno sin configurar) no
        # se aplica: la factura sale como hasta ahora, sin romper el cobro.
        if STRIPE_TAX_RATE_IVA:
            params["subscription_data"]["default_tax_rates"] = [STRIPE_TAX_RATE_IVA]
        if customer_id:
            params["customer"] = customer_id
            # Con un customer ya existente, Stripe exige customer_update para
            # GUARDAR en su ficha el NIF y la dirección recogidos en el checkout.
            # Sin esto, con clientes recurrentes se piden pero no se guardan.
            params["customer_update"] = {"name": "auto", "address": "auto"}
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
            sub_end    = fecha_fin_segura(sub)
            sub_id     = sub.get('id')
            uid_meta   = sub.get('metadata', {}).get('user_id')

            if uid_meta and not _metadata_coherente(conn, uid_meta, customer):
                uid_meta = None     # ya se ha registrado el motivo

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
            # Aquí también, y con más motivo que en el alta: esta rama QUITA el
            # acceso. Un id que no encaje cortaría el cuaderno a un agricultor
            # que está al corriente, que es el peor error posible de los dos.
            if uid_meta and _metadata_coherente(conn, uid_meta, sub.get('customer')):
                cortar_acceso(conn, int(uid_meta), olvidar_suscripcion=True)
                conn.commit()

        elif ev_type == 'checkout.session.completed':
            session_obj = obj
            customer    = session_obj.get('customer')
            uid_meta     = session_obj.get('metadata', {}).get('user_id')
            plan_meta    = session_obj.get('metadata', {}).get('plan')
            billing_meta = session_obj.get('metadata', {}).get('billing')
            sub_id       = session_obj.get('subscription')
            if uid_meta and not _metadata_coherente(conn, uid_meta, customer):
                uid_meta = None
            if uid_meta and customer:
                if plan_meta in _PLANES_PAGO:
                    # Este evento no trae el periodo pagado, así que la fecha
                    # es provisional hasta que llegue el de la suscripción con
                    # la real. Va según el intervalo contratado: 365 días
                    # fijos regalaban once meses a quien paga 14,99 €/mes.
                    import datetime as _dt
                    sub_end = (_dt.datetime.utcnow() + _dt.timedelta(
                        days=dias_provisionales(billing_meta))).strftime('%Y-%m-%d %H:%M:%S')
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
