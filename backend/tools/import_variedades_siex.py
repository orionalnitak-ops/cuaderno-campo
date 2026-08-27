"""Importa el catálogo oficial de variedades SIEX a `ref_variedades_siex`.

SOLO ESCRIBE esa tabla de referencia (no toca ningún dato de agricultor).
Se corre una vez, a mano, no en cada arranque — ver spec/features/018-siex-cultivo.

Uso (Git Bash, desde `backend/`):

    venv/Scripts/python.exe tools/import_variedades_siex.py "ruta/a/Variedad - Especie - Tipo.xlsx"

El fichero de entrada NO va en el repo (5MB+, catálogo público de SIEX pero sin
motivo para bundlearlo): se descarga aparte y se le pasa la ruta local.

Columnas esperadas del xlsx oficial (en este orden):
  Código cultivo | Cultivo | Latín | EPPO | C. UPOV |
  Código Variedad/Especie/Tipo | Variedad/Especie/Tipo | ...

Solo se usan las columnas 0 (código cultivo) y 5-6 (código y nombre de
variedad) — el resto del catálogo (admisible ayudas, vinificable...) no hace
falta para el autocompletado.

Corre `init_db()` primero (crea `ref_variedades_siex` si no existe) y luego
importa fila a fila con INSERT OR IGNORE / ON CONFLICT DO NOTHING: relanzar
el script no duplica filas.
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
    # Sin read_only=True a propósito: en este xlsx concreto (exportado por
    # SIEX) el modo read_only de openpyxl detecta mal las dimensiones de la
    # hoja y solo devuelve la primera columna. 86.136 filas x 13 columnas
    # entra de sobra en memoria cargado entero.
    wb = openpyxl.load_workbook(ruta, data_only=True)
    ws = wb.active

    init_db()
    conn = get_db()
    c = conn.cursor()

    sql = ("INSERT INTO ref_variedades_siex (cod_cultivo_siex, cod_variedad, nombre) "
           "VALUES (?, ?, ?) ON CONFLICT (cod_cultivo_siex, cod_variedad) DO NOTHING") if USE_PG \
        else ("INSERT OR IGNORE INTO ref_variedades_siex (cod_cultivo_siex, cod_variedad, nombre) "
              "VALUES (?, ?, ?)")

    filas = ws.iter_rows(min_row=2, values_only=True)
    total = 0
    lote = []
    for row in filas:
        if not row or row[0] is None or row[5] is None:
            continue
        cod_cultivo = str(row[0]).strip()
        cod_variedad = str(row[5]).strip()
        nombre = str(row[6] or '').strip().upper()
        if not nombre:
            continue
        lote.append((cod_cultivo, cod_variedad, nombre))
        if len(lote) >= 2000:
            c.executemany(sql, lote)
            total += len(lote)
            lote = []
            print(f"  {total} filas importadas...")
    if lote:
        c.executemany(sql, lote)
        total += len(lote)

    conn.commit()
    conn.close()
    print(f"Importacion completa: {total} filas procesadas en ref_variedades_siex")


if __name__ == '__main__':
    main()
