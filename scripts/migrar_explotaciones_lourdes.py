#!/usr/bin/env python
"""
migrar_explotaciones_lourdes.py — Migración one-off de parcelas con prefijo → multi-explotación.

Lourdes codifica el titular en el nombre de la parcela con un prefijo
(D-, L-, J-, JL-, EMILIO, ROBERT). Este script:

  1. Detecta el prefijo de cada parcela del usuario indicado.
  2. Crea una explotación por prefijo distinto (nombre_corto = etiqueta del prefijo).
  3. Asigna explotacion_id a cada parcela y le quita el prefijo del nombre.

Es idempotente: al re-ejecutarse, las parcelas ya sin prefijo se ignoran, y las
explotaciones se buscan por (user_id, nombre_corto) para no duplicar.

Uso:
    # Contra producción (PostgreSQL): exporta DATABASE_URL antes de ejecutar.
    # Contra local (SQLite): exporta DB_PATH=/ruta/cuaderno.db (o usa el default).

    python scripts/migrar_explotaciones_lourdes.py --user-id 3 --dry-run
    python scripts/migrar_explotaciones_lourdes.py --user-id 3          # aplica

Los datos reales de Lourdes están en producción. Haz SIEMPRE una copia de la BD
y ejecuta primero con --dry-run para revisar el mapeo antes de aplicar.
"""
import argparse
import os
import sys

# La consola de Windows usa cp1252 por defecto; forzar UTF-8 para los símbolos del informe.
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Permitir importar la capa db.py del backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from db import get_db, one, dicts  # noqa: E402

# Orden importante: JL- antes que J- y L-; palabras completas para EMILIO/ROBERT.
PREFIXES = [
    ('JL-', 'JL'),
    ('J-', 'J'),
    ('L-', 'L'),
    ('D-', 'D'),
    ('EMILIO', 'EMILIO'),
    ('ROBERT', 'ROBERT'),
]


def detectar(nombre):
    """Devuelve (etiqueta_prefijo, nombre_limpio) o (None, nombre) si no hay prefijo."""
    n = (nombre or '').strip()
    up = n.upper()
    for pref, label in PREFIXES:
        if up.startswith(pref):
            resto = n[len(pref):].lstrip(' -')
            return label, (resto or n)
    return None, n


def get_or_create_explotacion(conn, uid, label, dry_run, cache):
    """Devuelve el id de la explotación (user_id, nombre_corto=label), creándola si falta."""
    if label in cache:
        return cache[label]
    row = one(conn, "SELECT id FROM explotacion WHERE user_id=? AND nombre_corto=?", (uid, label))
    if row:
        cache[label] = row['id']
        return row['id']
    if dry_run:
        cache[label] = f"(nueva:{label})"
        return cache[label]
    # orden = número de explotaciones actuales (para ordenar el selector)
    n = one(conn, "SELECT COUNT(*) AS n FROM explotacion WHERE user_id=?", (uid,))
    orden = n['n'] if n else 0
    c = conn.cursor()
    c.execute("INSERT INTO explotacion (user_id, nombre_corto, titular, campana_activa, orden) VALUES (?,?,?,?,?)",
              (uid, label, label, '2025/2026', orden))
    conn.commit()
    new = one(conn, "SELECT id FROM explotacion WHERE user_id=? AND nombre_corto=?", (uid, label))
    cache[label] = new['id']
    return new['id']


def main():
    ap = argparse.ArgumentParser(description="Migrar parcelas con prefijo a multi-explotación")
    ap.add_argument('--user-id', type=int, required=True, help="ID del usuario (Lourdes)")
    ap.add_argument('--dry-run', action='store_true', help="Solo mostrar el mapeo, sin escribir")
    args = ap.parse_args()

    uid = args.user_id
    dry = args.dry_run

    conn = get_db()
    parcelas = dicts(conn, "SELECT id, nombre_finca, explotacion_id FROM parcelas WHERE user_id=? AND activa=1 ORDER BY nombre_finca", (uid,))
    if not parcelas:
        print(f"⚠ El usuario {uid} no tiene parcelas activas. Nada que migrar.")
        return

    cache = {}
    cambios = []
    sin_prefijo = []
    for p in parcelas:
        label, limpio = detectar(p['nombre_finca'])
        if label is None:
            sin_prefijo.append(p['nombre_finca'])
            continue
        eid = get_or_create_explotacion(conn, uid, label, dry, cache)
        cambios.append((p['id'], p['nombre_finca'], limpio, label, eid))

    # ── Informe ──
    print(f"\n{'='*70}")
    print(f"{'DRY-RUN — nada se escribe' if dry else 'APLICANDO MIGRACIÓN'} · usuario {uid}")
    print(f"{'='*70}")
    print(f"Parcelas con prefijo detectado: {len(cambios)}")
    print(f"Parcelas sin prefijo (se dejan como están): {len(sin_prefijo)}")

    por_label = {}
    for _pid, _orig, _limpio, label, _eid in cambios:
        por_label.setdefault(label, 0)
        por_label[label] += 1
    print("\nExplotaciones a crear/usar (nombre_corto → nº parcelas):")
    for label, n in sorted(por_label.items()):
        print(f"  · {label:10s} → {n} parcelas")

    print("\nEjemplos de renombrado (nombre original → nombre limpio | explotación):")
    for _pid, orig, limpio, label, _eid in cambios[:15]:
        print(f"  '{orig}'  →  '{limpio}'   [{label}]")
    if len(cambios) > 15:
        print(f"  … y {len(cambios) - 15} más")

    if sin_prefijo:
        print("\nParcelas SIN prefijo (revisar manualmente):")
        for nm in sin_prefijo[:20]:
            print(f"  · {nm}")

    if dry:
        print("\n✔ DRY-RUN completado. Revisa el mapeo y vuelve a ejecutar sin --dry-run para aplicar.")
        conn.close()
        return

    # ── Aplicar ──
    c = conn.cursor()
    for pid, _orig, limpio, _label, eid in cambios:
        c.execute("UPDATE parcelas SET explotacion_id=?, nombre_finca=? WHERE id=? AND user_id=?",
                  (eid, limpio, pid, uid))
    conn.commit()
    conn.close()
    print(f"\n✔ Migración aplicada: {len(cambios)} parcelas reasignadas y renombradas.")
    print("  Recuerda rellenar NIF/REGA de cada explotación en Ajustes.")


if __name__ == '__main__':
    main()
