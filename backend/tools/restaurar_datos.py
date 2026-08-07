"""Restaura en una base de datos LOCAL una copia hecha con `copia_datos.py`.

Existe para una cosa concreta: poder ensayar la migración de la feature 013
sobre los datos reales de Lourdes **sin tocar producción**. Ver la Fase 8 de
spec/features/013-aislamiento-por-explotacion/plan.md.

    # 1. crear la BD local vacía con el esquema actual
    venv/Scripts/python.exe -c "import db; db.init_db()"

    # 2. volcar dentro la copia de producción
    venv/Scripts/python.exe tools/restaurar_datos.py \\
        "H:/Proyectos/_backups-cuaderno/cuaderno-datos-AAAAMMDD-HHMMSS.json"

SEGURIDAD — dos cerrojos, a propósito
-------------------------------------
1. **Se niega a escribir en PostgreSQL.** Si hay `DATABASE_URL` en el entorno,
   aborta. Esta herramienta BORRA tablas antes de rellenarlas; apuntarla sin
   querer a producción sería catastrófico e irreversible. La comprobación no se
   puede saltar con un flag: si algún día hace falta restaurar en Postgres, se
   escribe otra cosa pensada para eso.
2. **Pide confirmación escrita**, porque vacía las tablas de la BD local.

El fichero de copia lleva datos personales de agricultores (NIF, teléfono,
email, ROPO). Vive fuera del repositorio, que es público. No lo muevas dentro
ni lo pegues en un chat.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db import get_db, USE_PG  # noqa: E402

# El orden importa: las tablas que dan de comer a otras van primero, para que
# las claves ajenas (si algún día se activan) no salten al insertar.
_ORDEN_PREFERIDO = ('users', 'explotacion', 'parcelas')


def _ordenar(tablas):
    primero = [t for t in _ORDEN_PREFERIDO if t in tablas]
    return primero + sorted(t for t in tablas if t not in primero)


def main(origen):
    if USE_PG:
        sys.exit("ABORTADO: hay DATABASE_URL en el entorno.\n"
                 "Esta herramienta BORRA tablas y solo puede correr contra la BD "
                 "local (SQLite). Abre una consola limpia, sin DATABASE_URL.")

    with open(origen, encoding='utf-8') as f:
        copia = json.load(f)

    tablas = copia.get('tablas') or {}
    if not tablas:
        sys.exit(f"El fichero {origen} no tiene ninguna tabla.")

    destino = os.environ.get('DB_PATH', 'cuaderno.db')
    total = sum(len(v) for v in tablas.values())
    print(f"Copia:   {origen}")
    print(f"         motor de origen: {copia.get('motor')} · fecha: {copia.get('fecha')}")
    print(f"         {len(tablas)} tablas, {total} filas")
    print(f"Destino: {destino}  (SQLite local)")
    print()
    print("Se van a VACIAR esas tablas en la base de datos local y rellenarlas")
    print("con el contenido de la copia. Los datos locales actuales se pierden.")
    if input('Escribe "restaurar" para continuar: ').strip() != 'restaurar':
        sys.exit("Cancelado. No se ha tocado nada.")

    conn = get_db()
    escritas, saltadas = {}, {}
    try:
        for tabla in _ordenar(tablas):
            filas = tablas[tabla]
            if not filas:
                continue
            # Solo columnas que existan en el esquema local: la copia puede venir
            # de un esquema más nuevo o más viejo, y reventar aquí obligaría a
            # editar el JSON a mano.
            try:
                cur = conn.execute(f"SELECT * FROM {tabla} LIMIT 0")
            except Exception:
                saltadas[tabla] = 'no existe en el esquema local'
                continue
            locales = {d[0] for d in cur.description}
            cols = [c for c in filas[0] if c in locales]
            if not cols:
                saltadas[tabla] = 'ninguna columna en común'
                continue
            ignoradas = sorted(set(filas[0]) - locales)

            conn.execute(f"DELETE FROM {tabla}")
            ph = ', '.join(['?'] * len(cols))
            conn.executemany(
                f"INSERT INTO {tabla} ({', '.join(cols)}) VALUES ({ph})",
                [tuple(f.get(c) for c in cols) for f in filas])
            escritas[tabla] = len(filas)
            if ignoradas:
                print(f"  {tabla}: {len(filas)} filas "
                      f"(columnas ignoradas: {', '.join(ignoradas)})")
        conn.commit()
    finally:
        conn.close()

    print()
    for tabla, n in sorted(escritas.items()):
        print(f"  {tabla:24} {n}")
    print(f"\nRestauradas {sum(escritas.values())} filas en {len(escritas)} tablas.")
    for tabla, motivo in sorted(saltadas.items()):
        print(f"  SALTADA {tabla}: {motivo}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
