"""Red contra olvidos: toda tabla de datos del agricultor va acotada por explotación.

Fase 6 de la feature 013. Los otros tests comprueban CASOS concretos; este
comprueba la REGLA, enumerando `TABLAS_POR_EXPLOTACION` para que la próxima
tabla no nazca con fuga. Dos frentes:

  A. Esquema — la columna existe de verdad en la BD que crea `init_db()`, y
     tiene su índice. Si alguien añade la tabla al diccionario pero la migración
     no la toca, salta aquí.

  B. Código — ninguna consulta a esas tablas ignora la columna. Se recorren los
     literales SQL del backend y se exige `explotacion_id` en cada sentencia que
     lea o escriba en ellas.

Sobre el frente B: es un análisis de texto, no un intérprete de SQL. Prefiere
avisar de más a callarse una fuga, y por eso existe `EXCEPCIONES`. Añadir algo
ahí es una decisión consciente que hay que justificar por escrito, no la salida
fácil para que el test se calle.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_tablas_acotadas.py
"""
import ast
import io
import os
import re
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import db  # noqa: E402
from db import TABLAS_POR_EXPLOTACION  # noqa: E402

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Ficheros que se revisan. `db.py` queda fuera a propósito: es quien CREA la
# columna y hace el backfill, así que ahí las consultas sin acotar son correctas.
FICHEROS = ([os.path.join(BACKEND, 'blueprints', f)
             for f in sorted(os.listdir(os.path.join(BACKEND, 'blueprints')))
             if f.endswith('.py')]
            + [os.path.join(BACKEND, 'exports.py'),
               os.path.join(BACKEND, 'export_pdf.py')])

# Nombres de variables que aportan el filtro por explotación cuando el SQL se
# compone por trozos. Si aparece una nueva forma de acotar, va aquí.
VARS_DE_SCOPE = {'pf', 'expl_sql', 'expl_cc', 'expl_par', 'clause', 'cparams',
                 '_cl', '_cp', 'parcela_scope_clause'}

# Cuánto código alrededor de la mención se considera "la misma operación".
VENTANA_ANTES, VENTANA_DESPUES = 400, 500

# Excepciones justificadas. Clave: (fichero, tabla) o (fichero, '*'). Valor: el
# porqué. Que algo esté aquí NO significa que esté bien para siempre: significa
# que se miró y se decidió. Sin motivo escrito, no entra.
EXCEPCIONES = {
    ('admin.py', '*'):
        "El panel de admin cuenta y borra a nivel de USUARIO, a propósito: no es "
        "el cuaderno de nadie, es soporte. Acotarlo por explotación daría cifras "
        "falsas y dejaría datos sin borrar al eliminar una cuenta.",
    ('auth.py', '*'):
        "GDPR (art. 20 portabilidad y art. 17 supresión): la exportación y el "
        "borrado de cuenta tienen que abarcar TODAS las explotaciones del "
        "usuario. Acotar aquí sería incumplir la ley, no aislar.",
}

_SENTENCIA = re.compile(r'\b(?:INSERT\s+INTO|DELETE\s+FROM|FROM|UPDATE)\s+([a-z_]+)',
                        re.IGNORECASE)


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


# ── A. Esquema ────────────────────────────────────────────────────────────────

def test_esquema():
    """La columna y su índice existen en la BD que crea init_db()."""
    print("A · el esquema real lleva la columna en todas las tablas:")

    # OJO: la ruta de la BD es `db.DATABASE_NAME`. Apuntar a otra cosa hace que
    # el test corra contra la base de datos de desarrollo sin avisar.
    ruta = os.path.join(tempfile.mkdtemp(), 'test_tablas_acotadas.db')
    db.DATABASE_NAME = ruta
    db.init_db()

    conn = sqlite3.connect(ruta)
    indices = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'")}

    for tabla in TABLAS_POR_EXPLOTACION:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tabla})")]
        check(f"{tabla} tiene explotacion_id", 'explotacion_id' in cols)
        check(f"{tabla} tiene su índice por explotación", f'idx_{tabla}_expl' in indices)
    conn.close()


# ── B. Código ─────────────────────────────────────────────────────────────────

def _funciones(src):
    """[(primera_linea, ultima_linea, código)] de cada función del fichero."""
    return [(n.lineno, n.end_lineno, ast.get_source_segment(src, n) or '')
            for n in ast.walk(ast.parse(src))
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def _ambito(funciones, linea, src):
    """Código de la función MÁS INTERNA que contiene esa línea.

    Si la consulta está fuera de toda función (SQL a nivel de módulo), no hay
    ámbito que valga y se cae a una ventana de texto alrededor.
    """
    dentro = [f for f in funciones if f[0] <= linea <= f[1]]
    if not dentro:
        pos = sum(len(l) + 1 for l in src.splitlines()[:linea - 1])
        return src[max(0, pos - VENTANA_ANTES): pos + VENTANA_DESPUES]
    return min(dentro, key=lambda f: f[1] - f[0])[2]


def _acotado(codigo):
    return ('explotacion_id' in codigo
            or any(re.search(rf'\b{v}\b', codigo) for v in VARS_DE_SCOPE))


def test_ninguna_consulta_ignora_la_columna():
    """Por cada mención a una tabla acotada, exige el filtro cerca en el código.

    La unidad que se mira es la FUNCIÓN que contiene la consulta, no la
    sentencia suelta, porque el SQL se compone de muchas formas y todas son
    legítimas: concatenando (`"SELECT …" + pf`), ampliando
    (`sql += " AND explotacion_id=?"`) o con un guardián al principio de la ruta
    que comprueba la propiedad y protege las consultas por `id` que vienen
    detrás.

    El precio es que una consulta sin acotar puede esconderse en una función que
    sí acota en otro sitio. Se asume: este test es la red que caza el olvido
    gordo (una tabla o una ruta nuevas que nadie acotó), no una demostración
    formal. Los casos concretos los cubre test_aislamiento_explotacion.py.
    """
    print("\nB · ninguna consulta lee ni escribe en esas tablas sin acotar:")

    fallos, revisadas = [], 0
    for ruta in FICHEROS:
        fichero = os.path.basename(ruta)
        src = io.open(ruta, encoding='utf-8').read()
        funciones = _funciones(src)
        for m in _SENTENCIA.finditer(src):
            tabla = m.group(1).lower()
            if tabla not in TABLAS_POR_EXPLOTACION:
                continue
            revisadas += 1
            if EXCEPCIONES.get((fichero, tabla)) or EXCEPCIONES.get((fichero, '*')):
                continue
            linea = src.count('\n', 0, m.start()) + 1
            if _acotado(_ambito(funciones, linea, src)):
                continue
            fallos.append(f"{fichero}:{linea} → {tabla}: "
                          f"{' '.join(src[m.start():m.start() + 90].split())}")

    for f in fallos:
        print(f"  FUGA {f}")
    check(f"{revisadas} menciones revisadas, ninguna sin acotar", not fallos)


def test_las_excepciones_siguen_existiendo():
    """Una excepción que ya no aplica es ruido que tapa la siguiente fuga."""
    print("\nC · las excepciones anotadas siguen correspondiendo a código real:")
    for (fichero, tabla), motivo in EXCEPCIONES.items():
        ruta = next((r for r in FICHEROS if os.path.basename(r) == fichero), None)
        src = io.open(ruta, encoding='utf-8').read() if ruta else ''
        toca = any(m.group(1).lower() in TABLAS_POR_EXPLOTACION
                   if tabla == '*' else m.group(1).lower() == tabla
                   for m in _SENTENCIA.finditer(src))
        check(f"{fichero} existe y sigue tocando {tabla}", toca and len(motivo) > 20)


def main():
    print("\n=== Tablas acotadas por explotación (feature 013, fase 6) ===\n")
    test_esquema()
    test_ninguna_consulta_ignora_la_columna()
    test_las_excepciones_siguen_existiendo()
    print("\n=== TODO OK ===")


if __name__ == '__main__':
    main()
