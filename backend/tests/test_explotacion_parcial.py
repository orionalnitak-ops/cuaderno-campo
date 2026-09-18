"""Test plano (sin pytest) del guardado parcial de la explotación — feature 028.

El guardado escribía SIEMPRE los 13 campos de `_EXPL_FIELDS` con `data.get()`,
que devuelve None cuando el campo no viene. Resultado: quien mandara medio
formulario borraba el resto. Guardar el municipio dejaba al titular sin NIF,
sin teléfono y sin CP.

No había estallado porque las dos pantallas mandaban el formulario entero. La
feature 028 introduce una pantalla de entrada que manda tres campos, así que el
fallo latente pasaba a ser seguro.

La regla que se fija aquí:
  - Campo ausente  → se deja como estaba. NUNCA se borra por omisión.
  - Campo presente y vacío → se borra. Vaciar un dato tiene que ser posible.
  - Campo desconocido → se ignora (`_EXPL_FIELDS` es lista blanca; nada del
    cliente entra en el SQL).

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_explotacion_parcial.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from blueprints.explotacion import actualizar_explotacion  # noqa: E402

UID = 1
EID = 10
OTRO_UID = 2          # el vecino: nada de lo suyo puede moverse
OTRO_EID = 99


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def _db():
    """Explotación con todos los datos puestos, como la de un usuario veterano."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE explotacion (
        id INTEGER PRIMARY KEY, user_id INTEGER, titular TEXT, nombre_corto TEXT,
        nif TEXT, rega TEXT, municipio TEXT, provincia TEXT, cp TEXT,
        telefono TEXT, email TEXT, campana_activa TEXT, fecha_apertura TEXT)""")
    conn.execute("""INSERT INTO explotacion VALUES
        (?,?, 'Cristóbal Campillo', 'La finca', '05123456A', 'ES13', 'San Carlos del Valle',
         'Ciudad Real', '13247', '600111222', 'cris@example.com', '2025/2026', '2026-01-01')""",
        (EID, UID))
    conn.execute("""INSERT INTO explotacion VALUES
        (?,?, 'Vecino', NULL, '99999999Z', NULL, 'Valdepeñas', NULL, NULL, NULL, NULL, NULL, NULL)""",
        (OTRO_EID, OTRO_UID))
    conn.commit()
    return conn


def _fila(conn, eid=EID):
    return conn.execute("SELECT * FROM explotacion WHERE id=?", (eid,)).fetchone()


# ── 1. El caso que provocó la feature ──────────────────────────────────
def test_guardar_solo_el_municipio_no_borra_lo_demas():
    """EL TEST QUE NO SE PUEDE ROMPER. Es lo que hará la pantalla de entrada."""
    conn = _db()
    actualizar_explotacion(conn, EID, UID, {'municipio': 'Valdepeñas'})
    row = _fila(conn)
    check("el municipio cambia",     row['municipio'] == 'Valdepeñas')
    check("el NIF sigue ahí",        row['nif'] == '05123456A')
    check("el titular sigue ahí",    row['titular'] == 'Cristóbal Campillo')
    check("el teléfono sigue ahí",   row['telefono'] == '600111222')
    check("el CP sigue ahí",         row['cp'] == '13247')
    check("el email sigue ahí",      row['email'] == 'cris@example.com')


def test_la_pantalla_de_entrada_manda_tres_campos():
    """Usuario nuevo: nombre, municipio y campaña. Nada más."""
    conn = _db()
    tocados = actualizar_explotacion(conn, EID, UID, {
        'titular': 'Ramón Pérez', 'municipio': 'Consuegra', 'campana_activa': '2026/2027'})
    row = _fila(conn)
    check("se tocan solo tres campos", sorted(tocados) == ['campana_activa', 'municipio', 'titular'])
    check("titular guardado",  row['titular'] == 'Ramón Pérez')
    check("campaña guardada",  row['campana_activa'] == '2026/2027')
    check("el NIF no se toca", row['nif'] == '05123456A')


# ── 2. Vaciar a propósito sí tiene que funcionar ───────────────────────
def test_mandar_un_campo_vacio_lo_borra():
    """Quien se equivocó al escribir su NIF tiene que poder dejarlo en blanco."""
    conn = _db()
    actualizar_explotacion(conn, EID, UID, {'nif': ''})
    row = _fila(conn)
    check("el NIF queda vacío",    row['nif'] == '')
    check("el resto no se mueve",  row['telefono'] == '600111222')


def test_none_explicito_tambien_borra():
    conn = _db()
    actualizar_explotacion(conn, EID, UID, {'rega': None})
    check("el REGA queda a NULL", _fila(conn)['rega'] is None)


# ── 3. Peticiones raras no rompen nada ─────────────────────────────────
def test_peticion_vacia_no_toca_nada():
    conn = _db()
    tocados = actualizar_explotacion(conn, EID, UID, {})
    row = _fila(conn)
    check("no se toca ningún campo", tocados == [])
    check("el titular sigue igual",  row['titular'] == 'Cristóbal Campillo')
    check("el NIF sigue igual",      row['nif'] == '05123456A')


def test_campo_desconocido_se_ignora():
    """Lista blanca: lo que no esté en _EXPL_FIELDS no entra en el SQL."""
    conn = _db()
    tocados = actualizar_explotacion(conn, EID, UID, {'user_id': 999, 'id': 7, 'lo_que_sea': 'x'})
    row = _fila(conn)
    check("no se toca nada",        tocados == [])
    check("el dueño no cambia",     row['user_id'] == UID)
    check("el id no cambia",        row['id'] == EID)


# ── 4. La frontera entre usuarios sigue en pie ─────────────────────────
def test_no_se_puede_editar_la_explotacion_de_otro():
    conn = _db()
    actualizar_explotacion(conn, OTRO_EID, UID, {'titular': 'Intruso'})
    check("la del vecino no se toca", _fila(conn, OTRO_EID)['titular'] == 'Vecino')


if __name__ == '__main__':
    test_guardar_solo_el_municipio_no_borra_lo_demas()
    test_la_pantalla_de_entrada_manda_tres_campos()
    test_mandar_un_campo_vacio_lo_borra()
    test_none_explicito_tambien_borra()
    test_peticion_vacia_no_toca_nada()
    test_campo_desconocido_se_ignora()
    test_no_se_puede_editar_la_explotacion_de_otro()
    print("Todos los tests pasaron.")
