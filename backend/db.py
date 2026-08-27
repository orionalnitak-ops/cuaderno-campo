import os
import re
import logging

logger = logging.getLogger(__name__)

# Los identificadores SQL (tabla/índice/columna) NO se pueden parametrizar con
# ?/%s: los drivers no los admiten. La única defensa frente a interpolación es
# una allowlist estricta. Un identificador válido empieza por letra/_ y solo
# contiene letras, números y guiones bajos (máx. 63, límite de PostgreSQL).
_SAFE_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')


def _safe_sql_identifier(value, context):
    """Valida que `value` sea un identificador SQL seguro antes de interpolarlo."""
    if not _SAFE_IDENTIFIER.match(value):
        raise ValueError(f"Identificador SQL no válido en '{context}': {value!r}")
    return value


DATABASE_URL = os.environ.get('DATABASE_URL', '')
DATABASE_NAME = os.environ.get('DB_PATH', 'cuaderno.db')

# Render exposes postgres://, psycopg2 requires postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

USE_PG = bool(DATABASE_URL)

# Primary key syntax differs between engines
_PK = "SERIAL PRIMARY KEY" if USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"

SINGLE_USER_ID = 2

PAC_USES = frozenset([
    'IV', 'TA', 'TH', 'OP', 'CF', 'CI', 'CS', 'CV',
    'FF', 'FL', 'FS', 'FV', 'FY', 'OC', 'OF', 'OV',
    'VF', 'VI', 'VO', 'PA', 'PR', 'PS'
])


def extract_uso_code(uso_sigpac_str):
    """Extract 2-letter code from 'OV-OLIVAR' → 'OV'"""
    if not uso_sigpac_str:
        return ''
    return uso_sigpac_str.split('-')[0].strip().upper()


def is_pac_eligible(uso_sigpac_str):
    """Return True if parcel uso_sigpac is PAC-eligible and visible in UI."""
    s = str(uso_sigpac_str).upper()
    if 'NO PAC' in s:
        return False
    return extract_uso_code(uso_sigpac_str) in PAC_USES


# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL compatibility wrappers
# ─────────────────────────────────────────────────────────────────────────────

class _PgCursor:
    """Wraps psycopg2 DictCursor to match sqlite3.Cursor API used in this project.

    Translates ? placeholders → %s, and captures RETURNING id for lastrowid.
    """

    def __init__(self, raw):
        self._c = raw
        self._lastrowid = None

    def execute(self, sql, params=None):
        sql = sql.replace('?', '%s')
        is_insert = (
            sql.strip().upper().startswith('INSERT')
            and 'RETURNING' not in sql.upper()
        )
        if is_insert:
            sql = sql.rstrip('; \n\t') + ' RETURNING id'
        if params:
            self._c.execute(sql, params)
        else:
            self._c.execute(sql)
        if is_insert:
            row = self._c.fetchone()
            self._lastrowid = row[0] if row else None

    def executemany(self, sql, params_list):
        sql = sql.replace('?', '%s')
        self._c.executemany(sql, params_list)

    def fetchone(self):
        return self._c.fetchone()

    def fetchall(self):
        return self._c.fetchall()

    @property
    def lastrowid(self):
        return self._lastrowid

    @property
    def rowcount(self):
        return self._c.rowcount


class _PgConn:
    """Wraps psycopg2 connection to match sqlite3.Connection API used in this project."""

    def __init__(self, raw):
        self._conn = raw
        self.row_factory = None  # no-op; kept so app.py can set it without error

    def cursor(self):
        import psycopg2.extras
        return _PgCursor(self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor))

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    def execute(self, sql, params=None):
        c = self.cursor()
        c.execute(sql, params)
        return c

    def rollback(self):
        self._conn.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

def get_db():
    if USE_PG:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return _PgConn(conn)
    import sqlite3
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def dicts(conn, sql, params=()):
    """Execute sql and return list of dicts. Works for both SQLite and PostgreSQL."""
    if not USE_PG:
        import sqlite3
        conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(sql, params)
    return [dict(r) for r in c.fetchall()]


def one(conn, sql, params=()):
    """Execute sql and return one dict, or None. Works for both SQLite and PostgreSQL."""
    if not USE_PG:
        import sqlite3
        conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(sql, params)
    r = c.fetchone()
    return dict(r) if r else None


# Alias de tabla permitidos para acotar por explotación (lista blanca — nunca input de usuario)
_SCOPE_ALIASES = {'', 't', 'f', 'l', 'r', 'c', 'co', 'a', 'cc'}


# Tablas con datos del agricultor que se acotan por explotación (feature 013:
# cada explotación es un cuaderno independiente). Fuente única de verdad: la usan
# la migración, los índices, el backfill y el test de aislamiento. Añadir aquí
# cualquier tabla nueva de datos del agricultor.
#
# El valor es la columna de la que HEREDAR la explotación en el backfill, o None
# si la tabla no cuelga de ninguna parcela y hay que caer a la explotación por
# defecto del usuario.
TABLAS_POR_EXPLOTACION = {
    'tratamientos':        'parcela_id',
    'fertilizacion':       'parcela_id',
    'riego':               'parcela_id',
    'abonado':             'parcela_id',
    'labores':             'parcela_id',
    'cosecha':             'parcela_id',
    'cultivos_campana':    'parcela_id',
    'compras':             None,
    'equipos':             None,
    'aplicadores':         None,
    'asesores':            None,
    'unidades_homogeneas': None,
}

# `cultivos_campana` es la única que no tiene `user_id`: cuelga de la parcela y
# el dueño se comprueba con un JOIN. Así que no puede caer al backfill por
# usuario, solo heredar de su parcela.
_SIN_USER_ID = frozenset({'cultivos_campana'})


def parcela_scope_clause(explotacion_id, alias=''):
    """Cláusula SQL parametrizada para acotar registros a las parcelas de una explotación.

    LEGADO. Solo lo usan `exports.py` y `export_pdf.py`, que ya funcionaban con
    él. El resto del código acota con `AND explotacion_id=?` directamente, desde
    que la feature 013 puso esa columna en todas las tablas de
    `TABLAS_POR_EXPLOTACION`.

    Ojo con su límite, que es el motivo de que se sustituyera: `parcela_id` es
    nullable en tratamientos, fertilizacion, labores, riego, cosecha y abonado,
    y un `parcela_id IN (…)` descarta las filas con NULL. Es decir, este helper
    OCULTA los registros sin parcela asignada en todas las explotaciones. En un
    cuaderno legal, un dato que no se ve es peor que un dato mezclado: el
    agricultor cree que no lo anotó.

    Devuelve `(clausula, params)`:
      - si `explotacion_id` es falsy → ('', ())
      - si no → (" AND <alias>.parcela_id IN (SELECT id FROM parcelas WHERE explotacion_id=?)", (explotacion_id,))

    El `alias` debe estar en la lista blanca `_SCOPE_ALIASES` (identificador de
    tabla controlado por el código, jamás input de usuario). El valor de la
    explotación viaja siempre como placeholder `?`.
    """
    if not explotacion_id:
        return '', ()
    if alias not in _SCOPE_ALIASES:
        raise ValueError(f"alias de scope no permitido: {alias!r}")
    prefix = (alias + '.') if alias else ''
    return (" AND " + prefix + "parcela_id IN (SELECT id FROM parcelas WHERE explotacion_id=?)",
            (explotacion_id,))


# ─────────────────────────────────────────────────────────────────────────────
# Safe column migration helper
# ─────────────────────────────────────────────────────────────────────────────

def _add_col(cursor, table, col, col_type):
    if USE_PG:
        cursor.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}')
    else:
        try:
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_type}')
        except Exception:
            pass  # column already exists


# ─────────────────────────────────────────────────────────────────────────────
# Structural migration helper — NEVER loses farmer data
#
# Pattern for any migration that needs to recreate a table:
#   1. Backup the SQLite .db file before touching anything
#   2. Rename old table to <table>_bak_<timestamp> (never DROP automatically)
#   3. Create new table
#   4. Copy all rows — verify count matches before committing
#   5. If count mismatch → rollback and raise so the old table stays intact
#
# The _bak_ table is kept indefinitely as a safety net. A human must
# decide when it's safe to drop it manually.
# ─────────────────────────────────────────────────────────────────────────────

def _backup_sqlite_db():
    """Copy the .db file to .db.bak_<timestamp> before structural migrations."""
    if USE_PG:
        return  # PostgreSQL: handled by platform backups (Render daily snapshots)
    import shutil, datetime
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    src = DATABASE_NAME
    dst = f"{DATABASE_NAME}.bak_{ts}"
    try:
        shutil.copy2(src, dst)
        print(f"[db] Backup creado: {dst}")
    except Exception as e:
        print(f"[db] AVISO: no se pudo crear backup antes de migración: {e}")


def _safe_recreate_table(conn, c, table, new_ddl, col_list):
    """
    Recreate `table` with `new_ddl` (without the old constraint/schema),
    preserving all rows. Keeps old table as <table>_bak_<timestamp>.

    col_list: list of column names that exist in BOTH old and new table,
              used for the INSERT … SELECT copy.
    """
    import datetime
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"{table}_bak_{ts}"

    # 1. Count rows in old table so we can verify the copy
    c.execute(f"SELECT COUNT(*) FROM {table}")
    old_count = c.fetchone()[0]

    # 2. Backup the .db file (SQLite only — no-op for PG)
    _backup_sqlite_db()

    # 3. Rename old table (keeps data safe, never dropped automatically)
    c.execute(f"ALTER TABLE {table} RENAME TO {backup_name}")

    # 4. Create new table
    c.execute(new_ddl)

    # 5. Copy all rows
    cols = ', '.join(col_list)
    c.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM {backup_name}")

    # 6. Verify row count — if mismatch, rollback so old data stays in backup
    c.execute(f"SELECT COUNT(*) FROM {table}")
    new_count = c.fetchone()[0]
    if new_count != old_count:
        conn.rollback()
        raise RuntimeError(
            f"[db] MIGRACIÓN ABORTADA: {table} tenía {old_count} filas, "
            f"solo se copiaron {new_count}. Datos seguros en '{backup_name}'."
        )

    print(f"[db] Migración OK: {table} ({old_count} filas copiadas). "
          f"Tabla antigua guardada como '{backup_name}'.")


def _enable_rls_postgres(conn):
    """Activa Row Level Security en toda tabla de `public` que aún no la tenga.

    Por qué: el Postgres gestionado de producción puede servir el schema `public`
    a través de una API REST automática. Sin RLS, cualquiera con la clave pública
    del cliente leería las tablas enteras, y aquí hay datos personales de
    agricultores (NIF, teléfono, email, nº ROPO). RLS activado SIN políticas
    deniega todo a los roles públicos, mientras que la app no se entera: conecta
    como owner de las tablas, y el owner hace bypass de RLS.

    Se recorre pg_class en vez de mantener una lista de tablas a mano,
    precisamente para que una tabla nueva no vuelva a nacer desprotegida.
    Idempotente: las que ya lo tienen se ignoran.
    """
    if not USE_PG:
        return
    try:
        c = conn.cursor()
        # El ALTER de cada tabla va en su propio BEGIN/EXCEPTION: si una falla
        # (p. ej. una tabla de extensión de la que no somos owner) las demás se
        # protegen igual, en vez de abortar el bloque entero en la primera.
        c.execute('''
            DO $$
            DECLARE t record;
            BEGIN
                FOR t IN
                    SELECT c.relname
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public'
                      AND c.relkind = 'r'
                      AND NOT c.relrowsecurity
                LOOP
                    BEGIN
                        EXECUTE format(
                            'ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.relname
                        );
                    EXCEPTION WHEN OTHERS THEN
                        RAISE WARNING 'RLS no activado en %: %', t.relname, SQLERRM;
                    END;
                END LOOP;
            END $$;
        ''')
        conn.commit()

        # No basta con que el bloque no lance: al capturar por tabla, un fallo
        # parcial sería invisible desde aquí. Se comprueba la postcondición.
        c.execute('''
            SELECT c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND NOT c.relrowsecurity
            ORDER BY c.relname
        ''')
        pendientes = [r[0] for r in c.fetchall()]
        if pendientes:
            logger.error(
                "[db] RLS NO ACTIVO en %d tabla(s) de public: %s. "
                "Si el schema estuviera expuesto a la API REST del proveedor, "
                "esos datos serían legibles con la clave pública. Revisar a mano.",
                len(pendientes), ', '.join(pendientes)
            )
    except Exception as e:
        # No se aborta el arranque: dejar la app caída para todos los agricultores
        # es peor que quedarse sin la segunda capa de defensa, teniendo la primera
        # (schema fuera de la API REST) en pie. Se registra como error, no warning:
        # aquí hay datos personales en juego.
        conn.rollback()
        logger.error("[db] No se pudo activar RLS automáticamente: %s", e)


# Tablas cuyo user_id nació como `INTEGER DEFAULT 2` y hay que endurecer.
# El 2 era el id de la primera cuenta de la app mono-usuario: un INSERT que se
# dejara el user_id no fallaba, escribía en esa cuenta. Con multi-explotación
# eso es una fuga de datos entre agricultores esperando a que alguien olvide
# la columna. Hoy ningún INSERT del código depende del DEFAULT.
_TABLAS_USER_ID = (
    'explotacion', 'parcelas', 'compras', 'equipos', 'aplicadores',
    'tratamientos', 'fertilizacion', 'riego', 'abonado', 'labores',
    'unidades_homogeneas', 'cosecha',
)


def _harden_user_id_postgres(conn):
    """Quita el `DEFAULT 2` de user_id y lo pone NOT NULL en las tablas antiguas.

    Los CREATE TABLE ya nacen con `NOT NULL`, pero llevan `IF NOT EXISTS`: en una
    BD que ya existe no se aplican. Esta migración es la que arregla producción.

    El DROP DEFAULT se hace siempre (es metadatos, no toca filas). El SET NOT NULL
    solo si la tabla no tiene ya filas con user_id NULL: no se puede endurecer una
    columna con datos que la violan, y borrar registros de un agricultor para que
    cuadre el esquema no es una decisión que deba tomar una migración automática.
    Esas filas se registran por nombre de tabla y recuento para revisarlas a mano.

    Idempotente. Cada tabla va en su propia transacción para que un fallo aislado
    no arrastre a las demás — en PG un error aborta la transacción entera.
    """
    if not USE_PG:
        return
    endurecidas, con_huerfanas = [], []
    for tabla in _TABLAS_USER_ID:
        try:
            # Los identificadores SQL no admiten placeholders, así que el nombre
            # de tabla va interpolado. Hoy la lista son literales de este módulo;
            # esta validación es lo que seguiría protegiendo si un refactor la
            # hiciera derivar de configuración o de la propia BD.
            tabla = _safe_sql_identifier(tabla, '_harden_user_id_postgres')
            c = conn.cursor()
            # Si la tabla no existe todavía (BD nueva a medio init), no hay nada que migrar.
            c.execute("SELECT to_regclass(?)", (f'public.{tabla}',))
            if not c.fetchone()[0]:
                conn.commit()
                continue

            c.execute(f"ALTER TABLE public.{tabla} ALTER COLUMN user_id DROP DEFAULT")

            c.execute(f"SELECT COUNT(*) FROM public.{tabla} WHERE user_id IS NULL")
            huerfanas = c.fetchone()[0]
            if huerfanas:
                con_huerfanas.append(f"{tabla} ({huerfanas})")
            else:
                c.execute(f"ALTER TABLE public.{tabla} ALTER COLUMN user_id SET NOT NULL")
                endurecidas.append(tabla)
            conn.commit()
        except Exception as e:
            # No se aborta el arranque por esto: el aislamiento real lo da el
            # `WHERE user_id=?` de cada query, esto es la red de seguridad.
            conn.rollback()
            logger.error("[db] user_id no endurecido en %s: %s", tabla, e)

    if con_huerfanas:
        logger.error(
            "[db] user_id sigue admitiendo NULL en: %s. Son filas sin dueño: "
            "asignarlas o borrarlas a mano y reiniciar para completar la migración.",
            ', '.join(con_huerfanas))
    logger.info("[db] user_id NOT NULL en %d/%d tablas comprobadas",
                len(endurecidas), len(_TABLAS_USER_ID))


def init_db():
    conn = get_db()
    c = conn.cursor()

    if USE_PG:
        c.execute("SELECT pg_advisory_lock(7311201201)")

    # ── EXPLOTACION ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS explotacion (
            id {_PK},
            user_id INTEGER NOT NULL,
            titular TEXT,
            nif TEXT,
            rega TEXT,
            municipio TEXT,
            provincia TEXT,
            cp TEXT,
            telefono TEXT,
            email TEXT,
            campana_activa TEXT DEFAULT '2025/2026',
            fecha_apertura TEXT,
            lopd_accepted INTEGER DEFAULT 0
        )
    ''')
    for col, typ in [('fecha_apertura', 'TEXT'), ('lopd_accepted', 'INTEGER DEFAULT 0'), ('rega', 'TEXT'),
                     ('nombre_corto', 'TEXT'), ('activa', 'INTEGER DEFAULT 1'), ('orden', 'INTEGER DEFAULT 0')]:
        _add_col(c, 'explotacion', col, typ)

    # ── PARCELAS ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS parcelas (
            id {_PK},
            user_id INTEGER NOT NULL,
            comunidad TEXT DEFAULT '07-Castilla-La Mancha',
            provincia_cod TEXT,
            provincia_nombre TEXT,
            municipio_cod TEXT,
            municipio_nombre TEXT,
            nombre_finca TEXT,
            poligono TEXT,
            parcela_num TEXT,
            recinto TEXT,
            superficie_ha REAL,
            uso_sigpac TEXT,
            referencia_cat TEXT,
            sistema_explotacion TEXT DEFAULT 'Secano',
            masa_agua_cercana INTEGER DEFAULT 0,
            notas TEXT,
            activa INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    for col, typ in [
        ('comunidad', 'TEXT'), ('provincia_cod', 'TEXT'), ('provincia_nombre', 'TEXT'),
        ('municipio_cod', 'TEXT'), ('municipio_nombre', 'TEXT'), ('nombre_finca', 'TEXT'),
        ('poligono', 'TEXT'), ('parcela_num', 'TEXT'), ('recinto', 'TEXT'),
        ('referencia_cat', 'TEXT'),
        ('sistema_explotacion', 'TEXT'), ('masa_agua_cercana', 'INTEGER DEFAULT 0'),
        ('notas', 'TEXT'), ('activa', 'INTEGER DEFAULT 1'),
        ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ('explotacion_id', 'INTEGER'),
        ('sigpac_superficie_ha', 'REAL'),
        ('sigpac_verificado_en', 'TEXT'),
    ]:
        _add_col(c, 'parcelas', col, typ)

    # ── CULTIVOS CAMPAÑA ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS cultivos_campana (
            id {_PK},
            parcela_id INTEGER NOT NULL,
            campana TEXT NOT NULL,
            cultivo TEXT,
            cultivo_iacs_cod TEXT,
            variedad TEXT,
            fecha_siembra TEXT,
            fecha_recoleccion_prevista TEXT,
            superficie_cultivada_ha REAL,
            notas TEXT,
            kg_sembrados REAL,
            precio_kg_compra REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(parcela_id) REFERENCES parcelas(id)
        )
    ''')
    _add_col(c, 'cultivos_campana', 'cultivo_iacs_cod', 'TEXT')
    _add_col(c, 'cultivos_campana', 'kg_sembrados', 'REAL')
    _add_col(c, 'cultivos_campana', 'precio_kg_compra', 'REAL')
    # feature 018: código de variedad del catálogo SIEX, solo cuando el
    # agricultor elige una sugerencia del autocompletado. NULL si escribe
    # texto libre — cero regresión sobre los datos existentes.
    _add_col(c, 'cultivos_campana', 'variedad_cod_siex', 'TEXT')

    # Migración: eliminar UNIQUE(parcela_id, campana) si todavía existe (permite múltiples cultivos por parcela)
    if not USE_PG:
        c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='cultivos_campana'")
        row = c.fetchone()
        tbl_sql = (row[0] if row else '') or ''
        if 'UNIQUE(parcela_id, campana)' in tbl_sql or 'UNIQUE(parcela_id,campana)' in tbl_sql:
            _safe_recreate_table(
                conn, c,
                table='cultivos_campana',
                new_ddl='''CREATE TABLE cultivos_campana (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parcela_id INTEGER NOT NULL,
                    campana TEXT NOT NULL,
                    cultivo TEXT,
                    cultivo_iacs_cod TEXT,
                    variedad TEXT,
                    fecha_siembra TEXT,
                    fecha_recoleccion_prevista TEXT,
                    superficie_cultivada_ha REAL,
                    notas TEXT,
                    kg_sembrados REAL,
                    precio_kg_compra REAL,
                    variedad_cod_siex TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(parcela_id) REFERENCES parcelas(id)
                )''',
                col_list=[
                    'id', 'parcela_id', 'campana', 'cultivo', 'cultivo_iacs_cod', 'variedad',
                    'fecha_siembra', 'fecha_recoleccion_prevista', 'superficie_cultivada_ha',
                    'notas', 'kg_sembrados', 'precio_kg_compra', 'variedad_cod_siex',
                    'created_at', 'updated_at',
                ],
            )
    else:
        # PostgreSQL: eliminar constraint por nombre estándar si existe
        # AVISO: antes de cualquier cambio estructural en producción, tomar un pg_dump manual.
        c.execute("""ALTER TABLE cultivos_campana
                     DROP CONSTRAINT IF EXISTS cultivos_campana_parcela_id_campana_key""")
        c.execute("""ALTER TABLE cultivos_campana
                     DROP CONSTRAINT IF EXISTS cultivos_campana_parcela_id_campana_uniq""")

    # ── REF VARIEDADES SIEX (feature 018) ──
    # Catálogo oficial `Variedad - Especie - Tipo.xlsx` de SIEX (86.136 filas).
    # No es dato de ningún agricultor: es un catálogo de referencia compartido,
    # por eso no lleva user_id ni entra en TABLAS_POR_EXPLOTACION. Se rellena
    # una vez con backend/tools/import_variedades_siex.py, no en cada arranque.
    c.execute('''
        CREATE TABLE IF NOT EXISTS ref_variedades_siex (
            cod_cultivo_siex TEXT NOT NULL,
            cod_variedad TEXT NOT NULL,
            nombre TEXT NOT NULL,
            PRIMARY KEY (cod_cultivo_siex, cod_variedad)
        )
    ''')

    # ── COMPRAS (Trazabilidad — Anexo III S5) ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS compras (
            id {_PK},
            user_id INTEGER NOT NULL,
            fecha TEXT,
            tipo_producto TEXT,
            producto TEXT,
            num_registro_mapa TEXT,
            sustancia_activa TEXT,
            proveedor TEXT,
            cantidad_valor REAL,
            cantidad_unidad TEXT DEFAULT 'kg',
            num_lote TEXT,
            num_factura TEXT,
            precio_total REAL,
            campana TEXT DEFAULT '2025/2026',
            notas TEXT,
            motivo_sin_registro TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    ''')
    for col, typ in [
        ('fecha', 'TEXT'), ('tipo_producto', 'TEXT'), ('producto', 'TEXT'),
        ('num_registro_mapa', 'TEXT'), ('sustancia_activa', 'TEXT'),
        ('proveedor', 'TEXT'), ('cantidad_valor', 'REAL'), ('cantidad_unidad', 'TEXT'),
        ('num_lote', 'TEXT'), ('num_factura', 'TEXT'), ('precio_total', 'REAL'),
        ('campana', 'TEXT'), ('notas', 'TEXT'),
        # Motivo por el que el producto no tiene nº de registro MAPA: sustancias
        # básicas (caolín, vinagre…) y autorizaciones excepcionales no se inscriben
        # en el Registro de Fitosanitarios, así que num_registro_mapa va vacío y este
        # campo justifica por qué. Vacío = el producto tiene nº de registro normal.
        ('motivo_sin_registro', 'TEXT'),
        ('deleted_at', 'TEXT'),
    ]:
        _add_col(c, 'compras', col, typ)

    # ── EQUIPOS ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS equipos (
            id {_PK},
            user_id INTEGER NOT NULL,
            descripcion TEXT,
            tipo TEXT,
            marca TEXT,
            modelo TEXT,
            num_registro_roma TEXT,
            fecha_iteaf TEXT,
            notas TEXT
        )
    ''')
    for col, typ in [
        ('marca', 'TEXT'), ('modelo', 'TEXT'),
        ('num_registro_roma', 'TEXT'), ('fecha_iteaf', 'TEXT'),
    ]:
        _add_col(c, 'equipos', col, typ)

    # ── APLICADORES ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS aplicadores (
            id {_PK},
            user_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            nif TEXT,
            num_ropo TEXT,
            activo INTEGER DEFAULT 1
        )
    ''')

    # ── ASESORES ──
    # Asesor fitosanitario (Orden APA/204/2023). Entidad reutilizable, igual que
    # aplicadores. El nº ROPO es de la sección "asesor" del carnet, distinta de la
    # de aplicador; aquí NO se bloquea si falta (ver spec/features/010-asesores).
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS asesores (
            id {_PK},
            -- Sin DEFAULT, a diferencia de las tablas antiguas: un INSERT que olvide
            -- el user_id debe fallar, no colgarle el asesor al usuario 2.
            user_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            nif TEXT,
            num_ropo TEXT,
            titulacion TEXT,
            empresa TEXT,
            telefono TEXT,
            email TEXT,
            activo INTEGER DEFAULT 1
        )
    ''')

    # ── TRATAMIENTOS ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS tratamientos (
            id {_PK},
            user_id INTEGER NOT NULL,
            parcela_id INTEGER,
            parcela_etiqueta TEXT,
            fecha_aplicacion TEXT,
            producto_comercial TEXT,
            num_registro_mapa TEXT,
            sustancia_activa TEXT,
            plaga_objetivo TEXT,
            dosis_valor REAL,
            dosis_unidad TEXT DEFAULT 'L/ha',
            volumen_caldo REAL,
            equipo_id INTEGER,
            condiciones_meteo TEXT,
            plazo_seguridad_dias INTEGER,
            fecha_recoleccion_minima TEXT,
            eficacia TEXT,
            aplicador_id INTEGER,
            notas TEXT,
            campana TEXT DEFAULT '2025/2026',
            motivo_sin_registro TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    for col, typ in [
        ('parcela_id', 'INTEGER'), ('parcela_etiqueta', 'TEXT'),
        ('fecha_aplicacion', 'TEXT'), ('producto_comercial', 'TEXT'),
        ('num_registro_mapa', 'TEXT'), ('sustancia_activa', 'TEXT'),
        # Ver nota en la tabla compras: justifica un num_registro_mapa vacío para
        # sustancias básicas y autorizaciones excepcionales. Vacío = registro normal.
        ('motivo_sin_registro', 'TEXT'),
        ('plaga_objetivo', 'TEXT'), ('dosis_valor', 'REAL'), ('dosis_unidad', 'TEXT'),
        ('volumen_caldo', 'REAL'), ('equipo_id', 'INTEGER'), ('condiciones_meteo', 'TEXT'),
        ('plazo_seguridad_dias', 'INTEGER'), ('fecha_recoleccion_minima', 'TEXT'),
        ('eficacia', 'TEXT'), ('aplicador_id', 'INTEGER'), ('campana', 'TEXT'),
        ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ('deleted_at', 'TEXT'),
        ('asesor', 'TEXT'),
        ('justificacion_actuacion', 'TEXT'),
        # asesor_id sustituye funcionalmente a `asesor` TEXT, pero esa columna NO se
        # elimina: los tratamientos ya registrados por los pilotos guardan ahí el
        # nombre tecleado a mano y deben seguir apareciendo en PDF/Excel.
        ('asesor_id', 'INTEGER'),
    ]:
        _add_col(c, 'tratamientos', col, typ)

    # ── FERTILIZACION ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS fertilizacion (
            id {_PK},
            user_id INTEGER NOT NULL,
            parcela_id INTEGER,
            parcela_etiqueta TEXT,
            fecha_aplicacion TEXT,
            tipo_fertilizante TEXT,
            producto TEXT,
            riqueza_npk TEXT,
            dosis_valor REAL,
            dosis_unidad TEXT DEFAULT 'kg/ha',
            metodo_aplicacion TEXT,
            notas TEXT,
            campana TEXT DEFAULT '2025/2026',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    for col, typ in [
        ('parcela_id', 'INTEGER'), ('parcela_etiqueta', 'TEXT'),
        ('fecha_aplicacion', 'TEXT'), ('producto', 'TEXT'), ('riqueza_npk', 'TEXT'),
        ('dosis_valor', 'REAL'), ('dosis_unidad', 'TEXT'), ('metodo_aplicacion', 'TEXT'),
        ('campana', 'TEXT'), ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ('deleted_at', 'TEXT'),
        ('n_aplicado', 'REAL'), ('p2o5_aplicado', 'REAL'), ('k2o_aplicado', 'REAL'),
        ('densidad_g_ml', 'REAL'),
    ]:
        _add_col(c, 'fertilizacion', col, typ)
    # feature 021 (bloque 4/8 SIEX): columnas de catálogo adicionales, todas
    # nullable, nunca reemplazan tipo_fertilizante/producto/metodo_aplicacion
    # de texto libre — mismo patrón que riego (feature 020). `asesor_id`
    # reutiliza la tabla `asesores` ya existente (feature 010), igual que
    # tratamientos.asesor_id.
    for col, typ in [
        ('fecha_enterrado', 'TEXT'),
        ('decl_buenas_practicas', 'INTEGER'),
        ('buena_practica_cod', 'INTEGER'),
        ('material_fertilizante_cod', 'INTEGER'),
        ('carbono_pct', 'REAL'),
        ('albaran', 'TEXT'),
        ('unidad_cod', 'INTEGER'),
        ('tipo_fertilizacion_cod', 'INTEGER'),
        ('metodo_cod', 'INTEGER'),
        ('asesor_id', 'INTEGER'),
        ('fecha_asesoramiento', 'TEXT'),
    ]:
        _add_col(c, 'fertilizacion', col, typ)

    # ── RIEGO ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS riego (
            id {_PK},
            user_id INTEGER NOT NULL,
            parcela_id INTEGER,
            parcela_etiqueta TEXT,
            fecha TEXT,
            tipo_riego TEXT,
            volumen_m3 REAL,
            horas_riego REAL,
            fuente_agua TEXT,
            notas TEXT,
            campana TEXT DEFAULT '2025/2026',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    ''')
    # feature 020 (bloque 3/8 SIEX): `tipo_riego` y `fuente_agua` (texto libre)
    # no se tocan — siguen guardando lo que escriba el agricultor. Estas
    # columnas de catálogo son adicionales, no un reemplazo (mismo patrón que
    # `asesor` TEXT conviviendo con `asesor_id` en tratamientos). Todo
    # nullable, sin excepción: ni siquiera `superficie_ha`, aunque SIEX la
    # marca obligatoria — decisión de Raúl 2026-08-27, igual criterio que
    # variedad en el 018 y venta en el 019, nunca bloquear el guardado por un
    # dato de catálogo.
    for col, typ in [
        ('superficie_ha', 'REAL'),
        ('sistema_riego_cod', 'INTEGER'),
        # Solo 3 (m³) o 4 (Litros) — el spec 020 decía 4 y 6, pero el catálogo
        # real `Unidades de medida.xlsx` tiene 6=toneladas, no m³; 3=m³ sí
        # coincide. Verificado contra el xlsx oficial, no contra el spec.
        ('unidad_cantidad_cod', 'INTEGER'),
        ('dosis_valor', 'REAL'),
        ('dosis_unidad', 'TEXT'),
        ('origen_agua_cod', 'INTEGER'),
        ('num_contador', 'TEXT'),
        ('tipo_energia_cod', 'INTEGER'),
        ('decl_buenas_practicas', 'INTEGER'),
        ('buena_practica_cod', 'INTEGER'),
    ]:
        _add_col(c, 'riego', col, typ)

    # ── ABONADO ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS abonado (
            id {_PK},
            user_id INTEGER NOT NULL,
            parcela_id INTEGER,
            parcela_etiqueta TEXT,
            cultivo TEXT,
            cultivo_anterior TEXT,
            rendimiento_esperado_kg_ha REAL,
            n_necesario_kg_ha REAL,
            p_necesario_kg_ha REAL,
            k_necesario_kg_ha REAL,
            fecha_preparacion TEXT,
            datos_suelo TEXT,
            abono_recomendado TEXT,
            dosis_recomendada_kg_ha REAL,
            notas TEXT,
            campana TEXT DEFAULT '2025/2026',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    ''')

    # ── LABORES ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS labores (
            id {_PK},
            user_id INTEGER NOT NULL,
            parcela_id INTEGER,
            parcela_etiqueta TEXT,
            fecha TEXT,
            tipo_labor TEXT,
            descripcion TEXT,
            maquinaria TEXT,
            horas_trabajadas REAL,
            operario TEXT,
            notas TEXT,
            campana TEXT DEFAULT '2025/2026',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    _add_col(c, 'labores', 'producto', 'TEXT')

    # ── UNIDADES HOMOGÉNEAS DE CULTIVO (UHC) ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS unidades_homogeneas (
            id {_PK},
            user_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            cultivo TEXT,
            campana TEXT DEFAULT '2025/2026',
            notas TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    ''')
    for col, typ in [
        ('nombre', 'TEXT'), ('cultivo', 'TEXT'),
        ('campana', 'TEXT'), ('notas', 'TEXT'),
        ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ('deleted_at', 'TEXT'),
    ]:
        _add_col(c, 'unidades_homogeneas', col, typ)

    c.execute(f'''
        CREATE TABLE IF NOT EXISTS uhc_parcelas (
            id {_PK},
            uhc_id INTEGER NOT NULL,
            parcela_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(uhc_id) REFERENCES unidades_homogeneas(id),
            FOREIGN KEY(parcela_id) REFERENCES parcelas(id)
        )
    ''')

    # ── COSECHA ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS cosecha (
            id {_PK},
            user_id INTEGER NOT NULL,
            parcela_id INTEGER,
            parcela_etiqueta TEXT,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            cultivo TEXT,
            variedad TEXT,
            superficie_cosechada_ha REAL,
            produccion_total_valor REAL,
            produccion_total_unidad TEXT DEFAULT 'kg',
            rendimiento_kg_ha REAL,
            destino TEXT,
            comprador TEXT,
            precio_unidad REAL,
            notas TEXT,
            campana TEXT DEFAULT '2025/2026',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # feature 019 (bloque 2/8 SIEX): SIEX modela una VENTA, no una cosecha, y
    # separa venta comercializada (con cliente identificado: NIF, dirección,
    # lote, albarán) de venta directa (sin cliente). Todo nullable — ningún
    # registro existente se toca y ninguno de estos campos bloquea el guardado.
    # `comprador` (ya existente) se reutiliza como nombre del cliente en ambos
    # casos: no se crea una columna `nombre_cliente` aparte, sería el mismo
    # dato dos veces — ver spec/features/019-siex-cosecha.
    for col, typ in [
        ('fecha_venta', 'TEXT'),
        ('tipo_venta', 'TEXT'),  # 'comercializada' | 'directa'
        ('codigo_producto_siex', 'INTEGER'),  # ref_productos_siex.id_producto
        ('albaran', 'TEXT'),
        ('lote', 'TEXT'),
        ('nif_cliente', 'TEXT'),
        ('direccion_cliente', 'TEXT'),
        ('provincia_cliente_cod', 'TEXT'),
        ('municipio_cliente_cod', 'TEXT'),
    ]:
        _add_col(c, 'cosecha', col, typ)

    # ── REF PRODUCTOS SIEX (feature 019) ──
    # Catálogo oficial `Producto Vegetal.xlsx` (693 filas). Reutilizado también
    # por los bloques 023 (análisis) y 025 (post-cosecha) — no es dato de
    # ningún agricultor, mismo criterio que `ref_variedades_siex` del 018.
    # Solo 693 filas en total: a diferencia de variedad, no hace falta
    # autocompletado remoto con límite — el cliente pide la lista entera ya
    # filtrada por cultivo y la renderiza en un <select>.
    c.execute('''
        CREATE TABLE IF NOT EXISTS ref_productos_siex (
            id_producto INTEGER NOT NULL,
            cod_cultivo_siex TEXT NOT NULL,
            nombre TEXT NOT NULL,
            PRIMARY KEY (id_producto, cod_cultivo_siex)
        )
    ''')

    # ── USERS ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS users (
            id {_PK},
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT,
            role TEXT DEFAULT 'agricultor',
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            plan TEXT DEFAULT 'trial',
            trial_ends_at TIMESTAMP,
            subscription_ends_at TIMESTAMP,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            unlimited_explotaciones INTEGER DEFAULT 0,
            pago_fallido_desde TIMESTAMP
        )
    ''')
    for col, typ in [
        ('plan', "TEXT DEFAULT 'trial'"),
        ('trial_ends_at', 'TIMESTAMP'),
        ('subscription_ends_at', 'TIMESTAMP'),
        ('stripe_customer_id', 'TEXT'),
        ('stripe_subscription_id', 'TEXT'),
        ('unlimited_explotaciones', 'INTEGER DEFAULT 0'),
        # Fecha del PRIMER cobro fallido mientras Stripe sigue reintentando.
        # NULL = no hay ningún cobro caído. No quita acceso: solo dispara el
        # aviso de "revisa tu tarjeta" en la app.
        ('pago_fallido_desde', 'TIMESTAMP'),
    ]:
        _add_col(c, 'users', col, typ)
    # email_verified: aviso suave "verifica tu correo", NO bloquea el acceso.
    _add_col(c, 'users', 'email_verified', 'INTEGER DEFAULT 0')
    # trial_reminder_sent: que el job de fin de trial no avise dos veces.
    _add_col(c, 'users', 'trial_reminder_sent', 'INTEGER DEFAULT 0')
    # Admin accounts never expire
    c.execute("UPDATE users SET plan='pro' WHERE role='admin' AND (plan='trial' OR plan IS NULL)")

    # ── EMAILS TRANSACCIONALES: tokens de un solo uso (verify / reset) ──
    # Una sola tabla para verificación y reset (mismo mecanismo, distinto `tipo`).
    # Fechas como TIMESTAMP (igual que el resto del proyecto); se escriben con
    # strftime y se leen igual en SQLite y Postgres (ver email_tokens.py).
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS email_tokens (
            id {_PK},
            token TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # ── PUSH NOTIFICATIONS ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id {_PK},
            user_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL UNIQUE,
            keys_json TEXT NOT NULL,
            provincia TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS push_alertas_cache (
            provincia TEXT PRIMARY KEY,
            alertas_hash TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── AISLAMIENTO POR EXPLOTACIÓN (feature 013) ──
    # `explotacion_id` en toda tabla con datos del agricultor. Va aquí, después
    # de crear todas las tablas y antes de los backfills, porque el backfill de
    # datos necesita que la columna ya exista.
    #
    # Sin DEFAULT, igual que `user_id`: un INSERT que la olvide debe fallar o
    # dejar NULL y salir en los avisos del backfill, nunca escribir callando en
    # la finca equivocada.
    for _tabla in TABLAS_POR_EXPLOTACION:
        _add_col(c, _tabla, 'explotacion_id', 'INTEGER')

    conn.commit()
    _seed_admin(conn)
    _seed_if_needed(conn)
    _backfill_explotaciones(conn)
    _backfill_explotacion_datos(conn)
    # Al final: ya existen todas las tablas, incluidas las que crea _seed_if_needed.
    _harden_user_id_postgres(conn)
    _enable_rls_postgres(conn)
    if USE_PG:
        c.execute("SELECT pg_advisory_unlock(7311201201)")
    conn.close()


def _backfill_explotaciones(conn):
    """Garantiza que toda parcela cuelgue de una explotación (modelo multi).

    Idempotente: para cada usuario con parcelas sin `explotacion_id`, asegura que
    exista al menos una explotación propia y asigna las parcelas huérfanas a la
    explotación por defecto (la de menor `orden`/`id`). No toca parcelas ya
    asignadas ni explotaciones ya creadas por el usuario.
    """
    c = conn.cursor()
    # Usuarios con parcelas huérfanas (explotacion_id NULL)
    user_rows = dicts(conn,
        "SELECT DISTINCT user_id FROM parcelas WHERE explotacion_id IS NULL AND user_id IS NOT NULL")
    for row in user_rows:
        uid = row['user_id']
        expl = one(conn,
            "SELECT id FROM explotacion WHERE user_id=? ORDER BY orden, id LIMIT 1", (uid,))
        if not expl:
            # Crear explotación por defecto para el usuario (usa su nombre si lo tenemos)
            u = one(conn, "SELECT nombre FROM users WHERE id=?", (uid,))
            titular = (u.get('nombre') if u else None) or 'Explotación principal'
            c.execute(
                "INSERT INTO explotacion (user_id, titular, nombre_corto, campana_activa) VALUES (?,?,?,?)",
                (uid, titular, titular, '2025/2026'))
            expl = one(conn,
                "SELECT id FROM explotacion WHERE user_id=? ORDER BY orden, id LIMIT 1", (uid,))
        c.execute("UPDATE parcelas SET explotacion_id=? WHERE user_id=? AND explotacion_id IS NULL",
                  (expl['id'], uid))
    conn.commit()


def _backfill_explotacion_datos(conn):
    """Asigna una explotación a los registros que nacieron sin ella (feature 013).

    Se ejecuta DESPUÉS de `_backfill_explotaciones()`, que garantiza que toda
    parcela ya tiene explotación: aquí se hereda de ella.

    Idempotente: solo toca filas con `explotacion_id IS NULL`, así que un segundo
    arranque no cambia nada.

    Dos pasadas, y el orden importa:

      1. Si la fila cuelga de una parcela, hereda la explotación de esa parcela.
         Es el dato REAL, no una suposición.
      2. Lo que quede (tabla sin parcela, o parcela sin asignar) cae a la
         explotación por defecto del usuario. Aquí sí se está suponiendo: para
         equipos, facturas, aplicadores y asesores nunca se guardó a qué finca
         pertenecían, así que caen todos en la principal y hay que repasarlos a
         mano. No hay forma de deducirlo.

    Lo que quede en NULL tras las dos pasadas se registra con `logger.error`,
    tabla y recuento, para revisarlo a mano. NO se fuerza `NOT NULL`: decidir qué
    se hace con los registros de un agricultor no es cosa de una migración
    automática (mismo criterio que `_harden_user_id_postgres`).
    """
    c = conn.cursor()

    for tabla, col_parcela in TABLAS_POR_EXPLOTACION.items():
        t = _safe_sql_identifier(tabla, 'table name')

        # ── Pasada 1: heredar de la parcela ──
        if col_parcela:
            pc = _safe_sql_identifier(col_parcela, 'column name')
            try:
                c.execute(f"""
                    UPDATE {t} SET explotacion_id = (
                        SELECT p.explotacion_id FROM parcelas p WHERE p.id = {t}.{pc})
                    WHERE explotacion_id IS NULL AND {pc} IS NOT NULL
                      AND EXISTS (SELECT 1 FROM parcelas p
                                   WHERE p.id = {t}.{pc} AND p.explotacion_id IS NOT NULL)
                """)
            except Exception as e:
                logger.error("[013] fallo heredando explotacion_id de la parcela en %s: %s",
                             tabla, e)

        # ── Pasada 2: explotación por defecto del usuario ──
        if tabla not in _SIN_USER_ID:
            try:
                huerfanos = dicts(conn, f"SELECT DISTINCT user_id FROM {t}"
                                        f" WHERE explotacion_id IS NULL AND user_id IS NOT NULL")
                for row in huerfanos:
                    uid = row['user_id']
                    expl = one(conn, "SELECT id FROM explotacion WHERE user_id=?"
                                     " ORDER BY orden, id LIMIT 1", (uid,))
                    if not expl:
                        # Usuario con datos pero sin ninguna explotación. No se le
                        # inventa una aquí: _backfill_explotaciones ya lo hace para
                        # quien tiene parcelas, y crear fincas fantasma a partir de
                        # una factura suelta es peor que dejarlo a la vista.
                        logger.error("[013] %s: el usuario %s tiene registros sin explotación"
                                     " y no tiene ninguna explotación creada", tabla, uid)
                        continue
                    c.execute(f"UPDATE {t} SET explotacion_id=?"
                              f" WHERE user_id=? AND explotacion_id IS NULL", (expl['id'], uid))
            except Exception as e:
                logger.error("[013] fallo asignando la explotación por defecto en %s: %s",
                             tabla, e)

        # ── Aviso de lo que quede sin asignar ──
        try:
            resto = one(conn, f"SELECT COUNT(*) AS n FROM {t} WHERE explotacion_id IS NULL")
            if resto and resto['n']:
                logger.error("[013] %s: %s registros siguen sin explotacion_id."
                             " Revisar a mano antes de fiarse de los listados.",
                             tabla, resto['n'])
        except Exception as e:
            logger.error("[013] no se pudo contar los huérfanos de %s: %s", tabla, e)

    conn.commit()


def _seed_admin(conn):
    import bcrypt
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    if c.fetchone()[0] == 0:
        admin_pw = os.environ.get('ADMIN_PASSWORD')
        if not admin_pw:
            import secrets, string
            admin_pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
            print(f"\n*** ADMIN CREADO — contraseña inicial: {admin_pw} ***")
            print("*** Cámbiala inmediatamente en Ajustes > Mi Cuenta ***\n")
        pw = bcrypt.hashpw(admin_pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        c.execute("INSERT INTO users (email, password_hash, nombre, role, plan) VALUES (?,?,?,?,?)",
                  ('admin@cuaderno.es', pw, 'Administrador', 'admin', 'pro'))
        conn.commit()


def _seed_if_needed(conn):
    c = conn.cursor()

    # Explotación
    c.execute("SELECT COUNT(*) FROM explotacion WHERE user_id=?", (SINGLE_USER_ID,))
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO explotacion (user_id, titular, municipio, provincia, cp, campana_activa)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (SINGLE_USER_ID, "Daniel de Lamo", "Santa Cruz de Mudela",
              "Ciudad Real", "13730", "2025/2026"))

    # Equipos
    c.execute("SELECT COUNT(*) FROM equipos WHERE user_id=?", (SINGLE_USER_ID,))
    if c.fetchone()[0] == 0:
        equipos = [
            (SINGLE_USER_ID, "Pulverizador terrestre (completar marca y modelo)", "Pulverizador terrestre"),
            (SINGLE_USER_ID, "Mochila atomizadora (completar marca)", "Mochila"),
            (SINGLE_USER_ID, "Empresa externa / Contratado", "Externo"),
        ]
        c.executemany("INSERT INTO equipos (user_id, descripcion, tipo) VALUES (?,?,?)", equipos)

    # Parcelas — seed only if empty
    c.execute("SELECT COUNT(*) FROM parcelas WHERE user_id=?", (SINGLE_USER_ID,))
    if c.fetchone()[0] == 0:
        _seed_parcelas(c)

    # ── ASISTENTE IA ──────────────────────────────────────────────────────────
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS ia_patrones (
            id             {_PK},
            user_id        INTEGER NOT NULL,
            modulo         TEXT NOT NULL,
            parcela_id     INTEGER,
            explotacion_id INTEGER,
            temporada      TEXT NOT NULL,
            campo          TEXT NOT NULL,
            valor_sugerido TEXT NOT NULL,
            frecuencia     INTEGER NOT NULL DEFAULT 1,
            ultima_vez     DATE,
            actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # `ia_patrones` no está en TABLAS_POR_EXPLOTACION porque no son datos del
    # agricultor sino una caché que se regenera en cada POST: por eso no lleva
    # backfill. Los patrones antiguos quedan con explotacion_id NULL y dejan de
    # casar con las consultas, que es exactamente lo que se quiere.
    _add_col(c, 'ia_patrones', 'explotacion_id', 'INTEGER')

    c.execute(f'''
        CREATE TABLE IF NOT EXISTS ia_alertas (
            id         {_PK},
            user_id    INTEGER NOT NULL,
            tipo       TEXT NOT NULL,
            parcela_id INTEGER,
            modulo     TEXT,
            mensaje    TEXT NOT NULL,
            leida      INTEGER DEFAULT 0,
            creada_en  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expira_en  TIMESTAMP
        )
    ''')
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS ia_feedback (
            id          {_PK},
            user_id     INTEGER NOT NULL,
            patron_id   INTEGER NOT NULL,
            accion      TEXT NOT NULL,
            valor_final TEXT,
            creado_en   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patron_id) REFERENCES ia_patrones(id)
        )
    ''')

    # ── ÍNDICES ──────────────────────────────────────────────────────────
    # Toda query filtra por user_id (aislamiento entre agricultores) y los
    # módulos suelen filtrar además por parcela_id. Sin índices, SQLite/PG
    # escanean la tabla entera en cada listado. CREATE INDEX IF NOT EXISTS
    # es válido y seguro en ambos motores (SQLite y PostgreSQL >= 9.5).
    _indexes = [
        ('idx_parcelas_user',        'parcelas',           'user_id'),
        ('idx_tratamientos_user',    'tratamientos',       'user_id'),
        ('idx_tratamientos_parcela', 'tratamientos',       'parcela_id'),
        ('idx_fertilizacion_user',   'fertilizacion',      'user_id'),
        ('idx_fertilizacion_parc',   'fertilizacion',      'parcela_id'),
        ('idx_labores_user',         'labores',            'user_id'),
        ('idx_labores_parcela',      'labores',            'parcela_id'),
        ('idx_riego_user',           'riego',              'user_id'),
        ('idx_abonado_user',         'abonado',            'user_id'),
        ('idx_compras_user',         'compras',            'user_id'),
        ('idx_cultivos_parcela',     'cultivos_campana',   'parcela_id'),
        ('idx_cosecha_user',         'cosecha',            'user_id'),
        ('idx_uhc_user',             'unidades_homogeneas','user_id'),
        ('idx_uhc_parcelas_uhc',     'uhc_parcelas',       'uhc_id'),
        ('idx_push_subs_user',       'push_subscriptions', 'user_id'),
        ('idx_ia_alertas_user',      'ia_alertas',         'user_id'),
        ('idx_asesores_user',        'asesores',           'user_id'),
        # La "Revisión del cuaderno" consulta estas tres en cada carga.
        ('idx_equipos_user',         'equipos',            'user_id'),
        ('idx_aplicadores_user',     'aplicadores',        'user_id'),
        ('idx_cultivos_campana',     'cultivos_campana',   'campana'),
        # Autocompletado de variedad (feature 018): filtra por cultivo y hace
        # LIKE 'texto%' sobre nombre, así que el índice compuesto cubre las dos.
        ('idx_ref_variedades_siex',  'ref_variedades_siex', 'cod_cultivo_siex, nombre'),
        # Catálogo de productos por cultivo (feature 019): mismo motivo.
        ('idx_ref_productos_siex',  'ref_productos_siex', 'cod_cultivo_siex'),
    ]
    # Un índice por explotación en cada tabla acotada (feature 013): ahora TODA
    # consulta de datos del agricultor lleva `AND explotacion_id=?`, y sin índice
    # eso es un escaneo completo por listado.
    _indexes += [(f'idx_{t}_expl', t, 'explotacion_id') for t in TABLAS_POR_EXPLOTACION]
    for idx_name, table, cols in _indexes:
        # Validar cada identificador contra la allowlist ANTES de interpolar.
        # cols puede ser "col1, col2": se valida parte a parte.
        safe_idx = _safe_sql_identifier(idx_name, 'index name')
        safe_table = _safe_sql_identifier(table, 'table name')
        safe_cols = ', '.join(
            _safe_sql_identifier(col.strip(), 'column name')
            for col in cols.split(',')
        )
        try:
            c.execute(
                f'CREATE INDEX IF NOT EXISTS {safe_idx} ON {safe_table} ({safe_cols})'
            )
        except Exception as e:
            # Un índice es no-crítico (solo rendimiento): si falla por causa de
            # entorno, se registra y se sigue, para no tumbar el arranque.
            # Un ValueError de _safe_sql_identifier NO llega aquí: se lanza antes
            # del try y aborta ruidosamente (error de programación).
            logger.warning("No se pudo crear el índice %s en %s: %s", idx_name, table, e)

    conn.commit()


def _seed_parcelas(c):
    raw = [
        ("HAZA GRANDE",        25,  1,  1, "OV-OLIVAR",      5.1015),
        ("HAZA GRANDE",        25,  1,  2, "OV-OLIVAR",      2.1308),
        ("HAZA GRANDE-ARR",    25,  2,  1, "OV-OLIVAR",      2.5614),
        ("HAZA GRANDE-ARR",    25,  3,  1, "OV-OLIVAR",      1.9875),
        ("CAMINO ANCHO",       25, 12,  1, "OV-OLIVAR",      3.2541),
        ("CAMINO ANCHO",       25, 12,  2, "CA-VIALES",      0.2103),
        ("CAMINO ANCHO",       25, 13,  1, "OV-OLIVAR",      1.8764),
        ("PAGO ALTO",          25, 20,  1, "OV-OLIVAR",      4.3218),
        ("PAGO ALTO",          25, 20,  2, "CA-VIALES",      0.1547),
        ("PAGO ALTO",          25, 21,  1, "OV-OLIVAR",      2.7632),
        ("LAS MESAS",          30,  5,  1, "OV-OLIVAR",      3.4521),
        ("LAS MESAS",          30,  5,  2, "OV-OLIVAR",      1.2341),
        ("LAS MESAS",          30,  6,  1, "OV-OLIVAR",      2.8754),
        ("EL LLANO",           30, 15,  1, "OV-OLIVAR",      5.6321),
        ("EL LLANO",           30, 15,  2, "CA-VIALES",      0.0987),
        ("EL LLANO",           30, 16,  1, "OV-OLIVAR",      3.1254),
        ("VALDEHIERRO",        35,  8,  1, "OV-OLIVAR",      4.2187),
        ("VALDEHIERRO",        35,  8,  2, "CA-VIALES",      0.1632),
        ("VALDEHIERRO",        35,  9,  1, "OV-OLIVAR",      2.9654),
        ("VALDEHIERRO",        35,  9,  2, "OV-OLIVAR",      1.5478),
        ("CAMINO REAL",        40,  3,  1, "OV-OLIVAR",      6.1254),
        ("CAMINO REAL",        40,  3,  2, "CA-VIALES",      0.2541),
        ("CAMINO REAL",        40,  4,  1, "OV-OLIVAR",      3.5478),
        ("LA RAYA",            45, 10,  1, "OV-OLIVAR",      4.8321),
        ("LA RAYA",            45, 10,  2, "OV-OLIVAR",      2.1547),
        ("LA RAYA",            45, 11,  1, "OV-OLIVAR",      3.2145),
        ("LAS VIÑAS",          48,  5,  1, "VI-VIÑEDO",      8.5412),
        ("LAS VIÑAS",          48,  5,  2, "CA-VIALES",      0.3215),
        ("LAS VIÑAS",          48,  6,  1, "VI-VIÑEDO",      5.2147),
        ("LAS VIÑAS",          48,  6,  2, "VI-VIÑEDO",      2.8754),
        ("SIXTO",              50, 62,  1, "OV-OLIVAR",      3.2541),
        ("SIXTO",              50, 62,  2, "OV-OLIVAR",      1.8754),
        ("SIXTO",              50, 62,  3, "CA-VIALES",      0.1127),
        ("SIXTO",              50, 62,  4, "OV-OLIVAR",      0.3192),
        ("JUAN MANUEL",        50, 75,  2, "OV-OLIVAR",      2.8553),
        ("CHARCÓN",            50, 58,  1, "OV-OLIVAR",      1.4878),
        ("CHARCÓN",            50, 58,  2, "CA-VIALES",      0.0047),
        ("CHARCÓN",            50, 59,  1, "TA-NO PAC",      0.8993),
        ("CHARCÓN",            50, 59,  2, "PR-PASTO ARBUST", 0.2048),
        ("CHARCÓN",            50, 59,  3, "FY-FRUTALES",    0.5473),
        ("CHARCÓN",            50, 59,  4, "TA-NO PAC",      0.9148),
        ("MINAS-N.MOTOR",      49, 22,  2, "OV-OLIVAR",      2.7707),
        ("MINAS-PLACAS",       49, 23,  2, "OV-OLIVAR",      3.6692),
        ("MINAS",              49, 23,  3, "IM-IMPRODUCT",   0.1288),
        ("MINAS",              49, 23,  4, "CA-VIALES",      0.5340),
        ("MINAS",              49, 23,  5, "CA-VIALES",      0.5048),
        ("MINAS-LUISITO",      49, 30,  2, "OV-OLIVAR",      2.8028),
        ("MINAS",              49, 30,  3, "CA-VIALES",      0.2930),
        ("RAMBLA-URBANO",      49, 10,  1, "OV-OLIVAR",      4.5514),
        ("RAMBLA-RAYA",        49, 12,  1, "OV-OLIVAR",      1.1055),
        ("RAMBLA-RAYA",        49, 13,  2, "OV-OLIVAR",      1.1432),
        ("QUINTANAR",          20,  3,  1, "OV-OLIVAR",      1.9660),
        ("QUINTANAR-ARR",      20, 40,  1, "OV-OLIVAR",      1.7968),
    ]
    for nombre_finca, poligono, parcela_num, recinto, uso_sigpac, superficie in raw:
        c.execute('''
            INSERT INTO parcelas (
                user_id, comunidad, provincia_cod, provincia_nombre,
                municipio_cod, municipio_nombre, nombre_finca,
                poligono, parcela_num, recinto, uso_sigpac, superficie_ha,
                sistema_explotacion, activa
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            SINGLE_USER_ID,
            "07-Castilla-La Mancha", "13", "Ciudad Real",
            "131", "Santa Cruz de Mudela", nombre_finca,
            str(poligono), str(parcela_num), str(recinto),
            uso_sigpac, superficie, "Secano", 1
        ))


if __name__ == '__main__':
    init_db()
    print("Base de datos inicializada con éxito.")
