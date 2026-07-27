"""Test plano (sin pytest) de la ficha de asesor fitosanitario.

Cubre las tres decisiones de riesgo de spec/features/010-asesores/spec.md:
  - decisión 2: la falta de nº ROPO avisa pero NO bloquea el guardado
  - decisión 3: el texto libre antiguo sigue saliendo en los exports
  - decisión 4: no se puede colgar un tratamiento del asesor de otro usuario (IDOR)

Ejecutar: python backend/tests/test_asesores.py
"""
import os, sys, sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from blueprints.tratamientos import _check_asesor
from export_pdf import _asesor_text

UID = 1
OTRO_UID = 2


def _db():
    """BD en memoria con solo la tabla que necesita _check_asesor."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE asesores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, nombre TEXT, num_ropo TEXT, activo INTEGER DEFAULT 1
        )
    """)
    conn.executemany(
        "INSERT INTO asesores (id, user_id, nombre, num_ropo) VALUES (?,?,?,?)", [
            (10, UID,      'Ana Técnica',  'ROPO-123'),  # completo
            (11, UID,      'Luis Sin Ropo', ''),         # sin ROPO
            (12, OTRO_UID, 'Asesor Ajeno', 'ROPO-999'),  # de otro usuario
        ])
    conn.commit()
    return conn


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def run():
    print("test_asesores:")
    conn = _db()

    # ── decisión 4: aislamiento entre usuarios (IDOR) ──
    err, aviso = _check_asesor(conn, {'asesor_id': 12}, UID)
    check("asesor de otro usuario -> error", err == "Asesor no encontrado")
    check("asesor de otro usuario -> sin aviso", aviso is None)

    err, aviso = _check_asesor(conn, {'asesor_id': 9999}, UID)
    check("asesor inexistente -> error", err == "Asesor no encontrado")

    # ── decisión 2: sin ROPO avisa pero no bloquea ──
    err, aviso = _check_asesor(conn, {'asesor_id': 11}, UID)
    check("asesor sin ROPO -> NO bloquea", err is None)
    check("asesor sin ROPO -> avisa", aviso is not None and 'Luis Sin Ropo' in aviso)

    # ── caso normal ──
    err, aviso = _check_asesor(conn, {'asesor_id': 10}, UID)
    check("asesor completo -> sin error", err is None)
    check("asesor completo -> sin aviso", aviso is None)

    # ── sin asesor: el campo sigue siendo opcional ──
    err, aviso = _check_asesor(conn, {}, UID)
    check("tratamiento sin asesor -> sin error", err is None and aviso is None)

    conn.close()

    # ── decisión 3: fallback del texto libre en el PDF ──
    check("ficha con ROPO se muestra con ROPO",
          _asesor_text({'asesor_nombre': 'Ana Técnica', 'asesor_ropo': 'ROPO-123'})
          == 'Ana Técnica (ROPO ROPO-123)')
    check("ficha sin ROPO se muestra sin paréntesis",
          _asesor_text({'asesor_nombre': 'Luis', 'asesor_ropo': ''}) == 'Luis')
    check("tratamiento antiguo cae al texto libre",
          _asesor_text({'asesor': 'Escrito a mano en 2025'}) == 'Escrito a mano en 2025')
    check("la ficha tiene prioridad sobre el texto libre",
          _asesor_text({'asesor_nombre': 'Ana', 'asesor': 'viejo'}) == 'Ana')
    check("sin asesor de ningún tipo -> guion",
          _asesor_text({}) == '—')
    # El PDF pasa por Paragraph, que interpreta mini-XML: los datos deben ir escapados
    check("el nombre se escapa para ReportLab",
          '&amp;' in _asesor_text({'asesor_nombre': 'Pérez & Hijos'}))

    print("test_asesores: TODO OK")


if __name__ == '__main__':
    run()
