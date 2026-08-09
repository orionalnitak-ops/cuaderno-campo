"""Test plano (sin pytest) del fin de periodo de la suscripción.

EL FALLO QUE FIJA ESTE ARCHIVO
------------------------------
Desde la versión de API `2025-03-31.basil`, Stripe **quitó**
`current_period_start` y `current_period_end` del objeto suscripción y los
movió a cada *item* de la suscripción. Es un cambio incompatible declarado
como tal en el changelog oficial:

  docs.stripe.com/changelog/basil/2025-03-31/
      deprecate-subscription-current-period-start-and-end

El webhook leía el campo del sitio viejo. Contra un endpoint moderno
(el nuestro se creó con `2026-07-29.dahlia`) eso devuelve `None`, y `None`
se guardaba como `subscription_ends_at = NULL`. Pero NULL, en esta app,
significa "plan concedido a mano, no vence nunca". Resultado: el agricultor
pagaba un mes y se quedaba con el cuaderno abierto para siempre.

Es decir, el gate fallaba en ABIERTO. Aquí se fija que falle CERRADO.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_stripe_periodo.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import blueprints.stripe_bp as stripe_bp  # noqa: E402


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def _ts(dias):
    return int((datetime.datetime.utcnow() + datetime.timedelta(days=dias)).timestamp())


def _sub_moderna(fin, extra_items=()):
    """Una suscripción tal y como la manda Stripe HOY: la fecha va en el item."""
    items = [{'price': {'id': 'price_x'}, 'current_period_end': fin}]
    for f in extra_items:
        items.append({'price': {'id': 'price_y'}, 'current_period_end': f})
    return {'id': 'sub_1', 'status': 'active', 'items': {'data': items}}


def _sub_antigua(fin):
    """Como la mandaba antes de basil, y como la manda aún un endpoint fijado
    a una versión vieja. Se sigue soportando: no queremos que el arreglo rompa
    a quien tenga el webhook anclado."""
    return {'id': 'sub_1', 'status': 'active',
            'current_period_end': fin,
            'items': {'data': [{'price': {'id': 'price_x'}}]}}


# ── 1. De dónde se saca la fecha ──────────────────────────────────────
def test_lee_la_fecha_del_item():
    fin = _ts(30)
    check("saca el fin de periodo del item (formato actual)",
          stripe_bp.fin_de_periodo(_sub_moderna(fin)) == fin)


def test_sigue_leyendo_el_formato_antiguo():
    fin = _ts(30)
    check("si viene en la suscripción (formato pre-basil), también vale",
          stripe_bp.fin_de_periodo(_sub_antigua(fin)) == fin)


def test_con_varios_items_se_queda_con_el_mas_cercano():
    """Stripe admite suscripciones con items de intervalos distintos, y en ese
    caso cada item vence en una fecha. Se coge la MÁS CERCANA: conceder hasta
    la más lejana sería regalar acceso no pagado."""
    pronto, tarde = _ts(10), _ts(300)
    check("se queda con la fecha más cercana",
          stripe_bp.fin_de_periodo(_sub_moderna(tarde, extra_items=(pronto,))) == pronto)


def test_sin_fecha_por_ningun_lado_devuelve_none():
    sub = {'id': 'sub_1', 'items': {'data': [{'price': {'id': 'price_x'}}]}}
    check("sin fecha, devuelve None", stripe_bp.fin_de_periodo(sub) is None)


def test_no_se_rompe_con_una_suscripcion_vacia():
    check("sin items ni nada, no revienta", stripe_bp.fin_de_periodo({}) is None)
    check("con items a None, tampoco",
          stripe_bp.fin_de_periodo({'items': None}) is None)


# ── 2. Lo que se guarda en la BD nunca puede ser NULL ─────────────────
def test_la_fecha_guardada_sale_del_periodo_real():
    fin = _ts(30)
    esperado = datetime.datetime.utcfromtimestamp(fin).strftime('%Y-%m-%d %H:%M:%S')
    check("se guarda el fin de periodo que dice Stripe",
          stripe_bp.fecha_fin_segura(_sub_moderna(fin)) == esperado)


def test_sin_fecha_falla_cerrado_y_nunca_escribe_null():
    """EL NÚCLEO DEL ARREGLO.

    Si Stripe no manda la fecha (campo movido otra vez, evento raro, formato
    que no conocemos), NO se puede escribir NULL: NULL es "no vence nunca".
    Se concede un margen corto y al día siguiente `guard_active_plan` le
    pregunta a Stripe y pone la buena.
    """
    sin_fecha = {'id': 'sub_1', 'items': {'data': []}}
    guardado = stripe_bp.fecha_fin_segura(sin_fecha)
    check("no devuelve None (NULL daría acceso permanente)", guardado is not None)
    fecha = datetime.datetime.strptime(guardado, '%Y-%m-%d %H:%M:%S')
    margen = fecha - datetime.datetime.utcnow()
    check("concede un margen corto, no un año",
          datetime.timedelta(hours=23) < margen < datetime.timedelta(days=2))


# ── 3. El alta por checkout no puede regalar un año ───────────────────
def test_el_mensual_no_recibe_un_ano_de_acceso():
    """`checkout.session.completed` no trae el periodo, así que se concede una
    fecha provisional hasta que llegue el evento de la suscripción. Esa
    provisional tiene que ir con el intervalo contratado: dar 365 días a quien
    paga 14,99 €/mes es regalarle once meses."""
    check("mensual -> alrededor de un mes", 28 <= stripe_bp.dias_provisionales('monthly') <= 32)
    check("anual   -> alrededor de un año", 365 <= stripe_bp.dias_provisionales('yearly') <= 367)


def test_un_intervalo_desconocido_concede_lo_minimo():
    check("intervalo raro -> el margen corto, no el largo",
          stripe_bp.dias_provisionales('lo-que-sea') == stripe_bp.dias_provisionales('monthly'))
    check("intervalo ausente -> el margen corto",
          stripe_bp.dias_provisionales(None) == stripe_bp.dias_provisionales('monthly'))


# ── 4. Que nadie vuelva a leer el campo del sitio viejo ───────────────
def test_el_webhook_ya_no_lee_el_campo_deprecado():
    """Cinturón contra la regresión: si alguien vuelve a escribir
    `sub.get('current_period_end')` suelto en el webhook, este test se pone
    rojo. Se mira sobre el fuente porque lo que se quiere impedir es el uso
    del campo, venga de donde venga.
    """
    ruta = os.path.join(os.path.dirname(__file__), '..', 'blueprints', 'stripe_bp.py')
    with open(ruta, encoding='utf-8') as f:
        fuente = f.read()

    i_helper = fuente.index('def fin_de_periodo')
    j_helper = fuente.index('def ', i_helper + 10)
    fuera_del_helper = fuente[:i_helper] + fuente[j_helper:]

    check("solo el helper lee current_period_end",
          "current_period_end" not in fuera_del_helper)


def test_el_webhook_no_puede_escribir_una_fecha_vacia():
    """La otra mitad del cinturón: que la rama de alta del webhook use el
    helper seguro y no vuelva a meter un `None` en la columna."""
    ruta = os.path.join(os.path.dirname(__file__), '..', 'blueprints', 'stripe_bp.py')
    with open(ruta, encoding='utf-8') as f:
        fuente = f.read()
    cuerpo = fuente[fuente.index('def stripe_webhook'):]
    check("la rama de alta usa fecha_fin_segura", 'fecha_fin_segura(' in cuerpo)


if __name__ == '__main__':
    fallos = 0
    for nombre, fn in sorted(globals().items()):
        if nombre.startswith('test_') and callable(fn):
            print(f"\n{nombre}")
            try:
                fn()
            except AssertionError as e:
                fallos += 1
                print(f"  !! {e}")
    print("\n" + ("TODO OK" if not fallos else f"{fallos} TEST(S) EN ROJO"))
    sys.exit(1 if fallos else 0)
