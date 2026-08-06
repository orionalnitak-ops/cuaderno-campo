"""Copia de seguridad de los datos, con lo que hay instalado (sin pg_dump).

SOLO LEE la base de datos. Vuelca cada tabla a un JSON con fecha en el nombre.

    venv/Scripts/python.exe tools/copia_datos.py "H:/Proyectos/_backups-cuaderno"

Qué es y qué NO es
------------------
Es una copia de los **datos**: todas las filas de todas las tablas. Sirve para
volver a meterlos si una migración los estropea, porque el esquema lo recrea
`init_db()` solo.

NO es un `pg_dump`. No guarda el esquema, ni los índices, ni las secuencias, ni
nada de la configuración del proveedor. Para una copia completa de verdad hace
falta `pg_dump` o el backup del propio proveedor. Esto es la red de seguridad
proporcionada a una base de datos pequeña, no un sustituto.

El fichero lleva datos personales de agricultores (NIF, teléfono, email, ROPO):
guárdalo FUERA del repositorio, que es público, y no lo compartas.
"""
import datetime
import decimal
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db import get_db, dicts, USE_PG  # noqa: E402


def _serializable(v):
    """Fechas, horas y decimales no caben en JSON tal cual."""
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (bytes, memoryview)):
        return None          # no hay columnas binarias; si aparecen, se avisa aparte
    return v


def _tablas(conn):
    if USE_PG:
        filas = dicts(conn, "SELECT tablename AS t FROM pg_tables"
                            " WHERE schemaname='public' ORDER BY tablename")
    else:
        filas = dicts(conn, "SELECT name AS t FROM sqlite_master"
                            " WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    return [f['t'] for f in filas]


def main(destino):
    os.makedirs(destino, exist_ok=True)
    sello = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    ruta = os.path.join(destino, f'cuaderno-datos-{sello}.json')

    conn = get_db()
    volcado, total = {}, 0
    try:
        for t in _tablas(conn):
            try:
                filas = dicts(conn, f"SELECT * FROM {t}")   # nosec B608 — nombre de tabla del catálogo, no de input
            except Exception as e:
                print(f"  {t:24} ERROR: {e}")
                volcado[t] = {'error': str(e)}
                continue
            filas = [{k: _serializable(v) for k, v in f.items()} for f in filas]
            volcado[t] = filas
            total += len(filas)
            print(f"  {t:24} {len(filas):>6} filas")
    finally:
        conn.close()

    with open(ruta, 'w', encoding='utf-8') as fh:
        json.dump({'fecha': sello, 'motor': 'postgresql' if USE_PG else 'sqlite',
                   'tablas': volcado}, fh, indent=1, ensure_ascii=False, default=str)

    mb = os.path.getsize(ruta) / (1024 * 1024)
    print(f"\n{total} filas guardadas en:\n  {ruta}\n  ({mb:.2f} MB)")
    print("\nLleva datos personales de agricultores: guárdalo fuera del repositorio.")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1])
