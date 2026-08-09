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

Antes de escribir deja un acta en un fichero JSON con quién lo ejecutó, cuándo y
**qué identificadores tenía cada cuenta**. Un `print` por pantalla se lo lleva el
cierre de la terminal, y aquí lo que hace falta no es saber que se ejecutó, sino
poder responder "¿qué `cus_` tenía esta cuenta?" cuando ya se ha borrado.

El acta lleva emails de agricultores: se guarda FUERA del repositorio, que es
público. Por defecto va a `_backups-cuaderno/`, junto a las copias de datos.
"""
import datetime
import getpass
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db import get_db, dicts  # noqa: E402

APLICAR = '--aplicar' in sys.argv
# Un `--aplicarr` mal tecleado NO activa la escritura: hace la pasada de solo
# lectura y lo dice. Un dedazo tiene que caer del lado seguro, así que aquí no
# se usa argparse a propósito: convertiría el dedazo en un error en vez de en
# una pasada inofensiva.

_POR_DEFECTO = os.path.join(os.path.dirname(__file__), '..', '..', '..', '_backups-cuaderno')


def _ruta_acta():
    """Dónde se deja el acta. Se puede pasar una carpeta como argumento."""
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    carpeta = args[0] if args else _POR_DEFECTO
    os.makedirs(carpeta, exist_ok=True)
    sello = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    return os.path.abspath(os.path.join(carpeta, f'limpieza-stripe-{sello}.json'))


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

        # El acta se escribe ANTES del UPDATE y a propósito: si se escribiera
        # después, un fallo a mitad dejaría los identificadores borrados y sin
        # rastro de cuáles eran. Si no se puede dejar constancia, no se borra.
        acta = '(sin determinar)'
        try:
            acta = _ruta_acta()
            with open(acta, 'w', encoding='utf-8') as f:
                json.dump({
                    'fecha': datetime.datetime.now().isoformat(timespec='seconds'),
                    'usuario': getpass.getuser(),
                    'base_de_datos': destino,
                    'motivo': 'identificadores de Stripe del modo Test antes del go-live',
                    'cuentas': [dict(f_) for f_ in filas],
                }, f, ensure_ascii=False, indent=2)
        except OSError as err:
            print(f"\nNo se ha podido escribir el acta en {acta}: {err}")
            print("No se borra nada sin dejar constancia. Cancelado.\n")
            return 1
        print(f"\nActa guardada en: {acta}")
        print("Lleva emails de agricultores: no la subas al repositorio.")

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
