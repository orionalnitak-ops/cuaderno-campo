"""Borra los identificadores de Stripe del modo Test antes de pasar a Live.

    venv/Scripts/python.exe tools/limpiar_stripe_test.py            # solo mira
    venv/Scripts/python.exe tools/limpiar_stripe_test.py --aplicar  # escribe

Por qué hace falta
------------------
`cus_...` y `sub_...` son objetos de UN modo de Stripe. Los creados durante las
pruebas NO existen en Live. Si se quedan en la ficha del agricultor al cambiar
la clave a `sk_live_`, pasan dos cosas, las dos malas:

1. Al pulsar un plan, el checkout le pasa a Stripe Live un `customer` que allí
   no existe (`stripe_bp.py`, `params["customer"] = customer_id`). Stripe
   responde "No such customer" y el pago no llega a abrirse. El agricultor ve un
   error genérico y nadie sabe por qué.

2. Si llegara a pagar, `_metadata_coherente` vería que el cliente del evento no
   es el guardado en su ficha e ignoraría el alta. Habría pagado sin recibir el
   plan: el control de seguridad disparándose contra el cliente honrado.

Qué toca y qué NO
-----------------
Pone a NULL `stripe_customer_id` y `stripe_subscription_id`. Nada más.

**No toca el plan, ni las fechas, ni un solo dato del cuaderno.** Quien tenga un
plan concedido lo conserva igual: esos dos campos solo sirven para hablar con
Stripe, y hoy apuntan a un sitio que en Live no existe. Al pagar de verdad, el
webhook los vuelve a rellenar con los buenos.

Es idempotente: pasarlo dos veces no hace nada la segunda.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db import get_db, dicts  # noqa: E402

APLICAR = '--aplicar' in sys.argv


def main():
    destino = 'PostgreSQL (producción)' if os.environ.get('DATABASE_URL') else 'SQLite local'
    print(f"\nBase de datos: {destino}\n")

    conn = get_db()
    try:
        filas = dicts(conn, """
            SELECT id, email, plan, stripe_customer_id, stripe_subscription_id
            FROM users
            WHERE stripe_customer_id IS NOT NULL OR stripe_subscription_id IS NOT NULL
            ORDER BY id
        """)

        if not filas:
            print("No hay ninguna ficha con identificadores de Stripe. Nada que hacer.\n")
            return 0

        print(f"{len(filas)} cuenta(s) con identificadores de Stripe:\n")
        for f in filas:
            print(f"  id={f['id']:<4} plan={str(f['plan']):8} {f['email']}")
            print(f"      customer     : {f['stripe_customer_id']}")
            print(f"      subscription : {f['stripe_subscription_id']}")

        if not APLICAR:
            print("\nEsto ha sido solo una lectura. Para borrarlos:")
            print("  venv/Scripts/python.exe tools/limpiar_stripe_test.py --aplicar\n")
            return 0

        print("\nSe van a poner a NULL esos dos campos en las cuentas de arriba.")
        print("El plan, las fechas y los datos del cuaderno NO se tocan.")
        respuesta = input('Escribe "limpiar" para continuar: ').strip()
        if respuesta != 'limpiar':
            print("Cancelado. No se ha tocado nada.\n")
            return 1

        conn.execute("""
            UPDATE users SET stripe_customer_id=NULL, stripe_subscription_id=NULL
            WHERE stripe_customer_id IS NOT NULL OR stripe_subscription_id IS NOT NULL
        """)
        conn.commit()

        quedan = dicts(conn, """
            SELECT id FROM users
            WHERE stripe_customer_id IS NOT NULL OR stripe_subscription_id IS NOT NULL
        """)
        print(f"\nHecho. Cuentas limpiadas: {len(filas)}. Quedan sin limpiar: {len(quedan)}.")
        print("Comprueba que ningún agricultor ha perdido su plan antes de seguir.\n")
        return 0
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
