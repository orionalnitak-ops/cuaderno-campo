import os

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


def init_db():
    conn = get_db()
    c = conn.cursor()

    # ── EXPLOTACION ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS explotacion (
            id {_PK},
            user_id INTEGER DEFAULT 2,
            titular TEXT,
            nif TEXT,
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
    for col, typ in [('fecha_apertura', 'TEXT'), ('lopd_accepted', 'INTEGER DEFAULT 0')]:
        _add_col(c, 'explotacion', col, typ)

    # ── PARCELAS ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS parcelas (
            id {_PK},
            user_id INTEGER DEFAULT 2,
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
        ('sistema_explotacion', 'TEXT'), ('masa_agua_cercana', 'INTEGER DEFAULT 0'),
        ('notas', 'TEXT'), ('activa', 'INTEGER DEFAULT 1'),
        ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(parcela_id) REFERENCES parcelas(id),
            UNIQUE(parcela_id, campana)
        )
    ''')
    _add_col(c, 'cultivos_campana', 'cultivo_iacs_cod', 'TEXT')

    # ── COMPRAS (Trazabilidad — Anexo III S5) ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS compras (
            id {_PK},
            user_id INTEGER DEFAULT 2,
            fecha TEXT,
            tipo_producto TEXT,
            producto TEXT,
            proveedor TEXT,
            cantidad_valor REAL,
            cantidad_unidad TEXT DEFAULT 'kg',
            num_lote TEXT,
            num_factura TEXT,
            precio_total REAL,
            campana TEXT DEFAULT '2025/2026',
            notas TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    ''')
    for col, typ in [
        ('fecha', 'TEXT'), ('tipo_producto', 'TEXT'), ('producto', 'TEXT'),
        ('proveedor', 'TEXT'), ('cantidad_valor', 'REAL'), ('cantidad_unidad', 'TEXT'),
        ('num_lote', 'TEXT'), ('num_factura', 'TEXT'), ('precio_total', 'REAL'),
        ('campana', 'TEXT'), ('notas', 'TEXT'), ('deleted_at', 'TEXT'),
    ]:
        _add_col(c, 'compras', col, typ)

    # ── EQUIPOS ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS equipos (
            id {_PK},
            user_id INTEGER DEFAULT 2,
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
            user_id INTEGER DEFAULT 2,
            nombre TEXT NOT NULL,
            nif TEXT,
            num_ropo TEXT,
            activo INTEGER DEFAULT 1
        )
    ''')

    # ── TRATAMIENTOS ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS tratamientos (
            id {_PK},
            user_id INTEGER DEFAULT 2,
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    for col, typ in [
        ('parcela_id', 'INTEGER'), ('parcela_etiqueta', 'TEXT'),
        ('fecha_aplicacion', 'TEXT'), ('producto_comercial', 'TEXT'),
        ('num_registro_mapa', 'TEXT'), ('sustancia_activa', 'TEXT'),
        ('plaga_objetivo', 'TEXT'), ('dosis_valor', 'REAL'), ('dosis_unidad', 'TEXT'),
        ('volumen_caldo', 'REAL'), ('equipo_id', 'INTEGER'), ('condiciones_meteo', 'TEXT'),
        ('plazo_seguridad_dias', 'INTEGER'), ('fecha_recoleccion_minima', 'TEXT'),
        ('eficacia', 'TEXT'), ('aplicador_id', 'INTEGER'), ('campana', 'TEXT'),
        ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ('deleted_at', 'TEXT'),
    ]:
        _add_col(c, 'tratamientos', col, typ)

    # ── FERTILIZACION ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS fertilizacion (
            id {_PK},
            user_id INTEGER DEFAULT 2,
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
    ]:
        _add_col(c, 'fertilizacion', col, typ)

    # ── LABORES ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS labores (
            id {_PK},
            user_id INTEGER DEFAULT 2,
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

    # ── COSECHA ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS cosecha (
            id {_PK},
            user_id INTEGER DEFAULT 2,
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

    # ── USERS ──
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS users (
            id {_PK},
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT,
            role TEXT DEFAULT 'agricultor',
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    _seed_admin(conn)
    _seed_if_needed(conn)
    conn.close()


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
        c.execute("INSERT INTO users (email, password_hash, nombre, role) VALUES (?,?,?,?)",
                  ('admin@cuaderno.es', pw, 'Administrador', 'admin'))
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
