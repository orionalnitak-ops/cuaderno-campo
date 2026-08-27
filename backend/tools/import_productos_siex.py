"""Importa el catálogo oficial de productos vegetales SIEX a `ref_productos_siex`.

SOLO ESCRIBE esa tabla de referencia (no toca ningún dato de agricultor). Se
corre una vez, a mano — ver spec/features/019-siex-cosecha. La misma tabla la
reutilizan los bloques 023 (análisis) y 025 (post-cosecha): no hace falta
volver a correr esto para esos.

Uso (Git Bash, desde `backend/`):

    venv/Scripts/python.exe tools/import_productos_siex.py "ruta/a/Producto Vegetal.xlsx"

El fichero de entrada NO va en el repo — se descarga aparte y se le pasa la
ruta local.

Columnas esperadas del xlsx oficial (en este orden):
  Id | Código | Producto | Código SIEX | Cultivo SIEX | ...

`Id` es el identificador del producto (repetido si el mismo producto —p. ej.
"Ajetes, ajos tiernos"— cuenta como más de un cultivo botánico). `Código SIEX`
es, pese al nombre, el código SIEX del CULTIVO al que pertenece ese producto
(el mismo espacio de códigos que `CULTIVOS_COD_SIEX` en `backend/helpers.py`)
— no un código de producto en sí. `Cultivo SIEX` es solo el nombre de ese
mismo cultivo, no se usa.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db import get_db, init_db, USE_PG  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    ruta = sys.argv[1]
    if not os.path.isfile(ruta):
        print(f"No existe el fichero: {ruta}")
        sys.exit(1)

    import openpyxl
    # Sin read_only=True: en los xlsx exportados por SIEX ese modo de
    # openpyxl detecta mal las dimensiones de la hoja (visto ya en el import
    # de variedades). 693 filas entra de sobra en memoria cargado entero.
    wb = openpyxl.load_workbook(ruta, data_only=True)
    ws = wb.active

    init_db()
    conn = get_db()
    c = conn.cursor()

    sql = ("INSERT INTO ref_productos_siex (id_producto, cod_cultivo_siex, nombre) "
           "VALUES (?, ?, ?) ON CONFLICT (id_producto, cod_cultivo_siex) DO NOTHING") if USE_PG \
        else ("INSERT OR IGNORE INTO ref_productos_siex (id_producto, cod_cultivo_siex, nombre) "
              "VALUES (?, ?, ?)")

    filas = ws.iter_rows(min_row=2, values_only=True)
    lote = []
    total = 0
    for row in filas:
        if not row or row[0] is None or row[3] is None:
            continue
        try:
            id_producto = int(str(row[0]).strip())
        except ValueError:
            continue
        cod_cultivo_siex = str(row[3]).strip()
        nombre = str(row[2] or '').strip()
        if not nombre:
            continue
        lote.append((id_producto, cod_cultivo_siex, nombre))
    if lote:
        c.executemany(sql, lote)
        total = len(lote)

    conn.commit()
    conn.close()
    print(f"Importacion completa: {total} filas procesadas en ref_productos_siex")


if __name__ == '__main__':
    main()
