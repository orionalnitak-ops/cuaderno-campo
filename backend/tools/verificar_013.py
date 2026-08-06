"""Verificación de la migración de la feature 013 sobre datos reales.

SOLO LEE. No escribe nada en la base de datos, ni siquiera para corregir.

La pregunta que responde es una: **¿la migración ha perdido o duplicado algún
registro del agricultor?** Se contesta contando antes y después y comparando.

Uso (Git Bash, desde `backend/`):

    # 1. ANTES de arrancar la app con el código nuevo
    venv/Scripts/python.exe tools/verificar_013.py antes

    # 2. Arrancar la app una vez (init_db aplica la migración y el backfill)

    # 3. DESPUÉS
    venv/Scripts/python.exe tools/verificar_013.py despues

El paso 1 guarda los recuentos en `tools/recuento_013.json`. El paso 3 los
compara y además informa de:

  - filas con `explotacion_id` NULL (lo que el backfill no supo repartir),
  - el reparto por explotación de cada tabla, que es donde se ve qué equipos,
    facturas, aplicadores y asesores hay que reasignar a mano.

Sobre qué base de datos corre: la que digan las variables de entorno, igual que
la app (`DATABASE_URL` para Postgres, `DB_PATH` para SQLite). Sin variables, la
`cuaderno.db` local.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db import get_db, dicts, one, TABLAS_POR_EXPLOTACION  # noqa: E402

RECUENTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recuento_013.json')

# `parcelas` no está en TABLAS_POR_EXPLOTACION (ya tenía la columna antes de la
# feature), pero es de donde heredan casi todas: si aquí se pierde una fila, se
# pierde el rastro de muchas más.
TABLAS = ['parcelas'] + list(TABLAS_POR_EXPLOTACION)


def _cuenta(conn, tabla):
    row = one(conn, f"SELECT COUNT(*) AS n FROM {tabla}")
    return int(row['n']) if row else 0


def _sin_explotacion(conn, tabla):
    row = one(conn, f"SELECT COUNT(*) AS n FROM {tabla} WHERE explotacion_id IS NULL")
    return int(row['n']) if row else 0


def antes():
    conn = get_db()
    try:
        datos = {t: _cuenta(conn, t) for t in TABLAS}
    finally:
        conn.close()
    with open(RECUENTO, 'w', encoding='utf-8') as fh:
        json.dump(datos, fh, indent=2, ensure_ascii=False)
    print(f"Recuentos guardados en {RECUENTO}\n")
    for t, n in datos.items():
        print(f"  {t:22} {n:>7}")
    print("\nAhora arranca la app una vez y vuelve con:  "
          "venv/Scripts/python.exe tools/verificar_013.py despues")


def despues():
    if not os.path.exists(RECUENTO):
        print(f"No encuentro {RECUENTO}. Hay que correr primero:\n"
              f"  venv/Scripts/python.exe tools/verificar_013.py antes")
        return 1

    with open(RECUENTO, encoding='utf-8') as fh:
        previo = json.load(fh)

    conn = get_db()
    problemas = []
    try:
        print("1) ¿Se ha perdido o duplicado algún registro?\n")
        for t in TABLAS:
            ahora, antes_n = _cuenta(conn, t), previo.get(t)
            if antes_n is None:
                print(f"  {t:22} {ahora:>7}   (sin recuento previo)")
                continue
            if ahora == antes_n:
                print(f"  {t:22} {ahora:>7}   =")
            else:
                print(f"  {t:22} {ahora:>7}   ERA {antes_n}  ← DIFERENCIA")
                problemas.append(f"{t}: {antes_n} → {ahora}")

        print("\n2) ¿Ha quedado algo sin explotación asignada?\n")
        for t in TABLAS_POR_EXPLOTACION:
            n = _sin_explotacion(conn, t)
            print(f"  {t:22} {n:>7} sin asignar" + ("   ← REVISAR" if n else ""))
            if n:
                problemas.append(f"{t}: {n} filas con explotacion_id NULL")

        print("\n3) Reparto por explotación — aquí se ve qué hay que repasar a mano\n")
        expls = dicts(conn, "SELECT id, user_id, COALESCE(nombre_corto, titular) AS nombre"
                            " FROM explotacion ORDER BY user_id, orden, id")
        for e in expls:
            print(f"  · [{e['id']}] {e['nombre'] or '(sin nombre)'}  (usuario {e['user_id']})")
            for t in ('equipos', 'aplicadores', 'asesores', 'compras'):
                row = one(conn, f"SELECT COUNT(*) AS n FROM {t} WHERE explotacion_id=?", (e['id'],))
                print(f"      {t:14} {int(row['n']) if row else 0:>6}")
    finally:
        conn.close()

    print()
    if problemas:
        print("NO está limpio. Revisar antes de desplegar:")
        for p in problemas:
            print(f"  - {p}")
        return 1

    print("Limpio: ni un registro perdido y ni una fila sin explotación.")
    print("Queda el paso manual: el backfill mete los equipos, aplicadores,")
    print("asesores y facturas en la explotación por defecto, porque el dato de a")
    print("qué finca pertenecían nunca se guardó. Mirar el reparto de arriba y")
    print("mover a mano lo que sea de otra finca.")
    return 0


if __name__ == '__main__':
    modo = sys.argv[1] if len(sys.argv) > 1 else ''
    if modo == 'antes':
        antes()
    elif modo == 'despues':
        sys.exit(despues())
    else:
        print(__doc__)
        sys.exit(2)
