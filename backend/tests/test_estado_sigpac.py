"""Test plano (sin pytest) del helper puro estado_sigpac.
Ejecutar: python backend/tests/test_estado_sigpac.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from helpers import estado_sigpac


def check(nombre, parcela, esperado_estado, esperado_diff):
    estado, diff = estado_sigpac(parcela)
    assert estado == esperado_estado, f"{nombre}: estado {estado!r} != {esperado_estado!r}"
    assert diff == esperado_diff, f"{nombre}: diff {diff!r} != {esperado_diff!r}"
    print(f"  OK {nombre}")


def run():
    check("sin_verificar",
          {'sigpac_verificado_en': None, 'sigpac_superficie_ha': None, 'superficie_ha': 10},
          'sin_verificar', None)
    check("no_encontrada",
          {'sigpac_verificado_en': '2026-07-10', 'sigpac_superficie_ha': None, 'superficie_ha': 10},
          'no_encontrada', None)
    check("verde_igual",
          {'sigpac_verificado_en': '2026-07-10', 'sigpac_superficie_ha': 10.0, 'superficie_ha': 10.0},
          'verde', 0.0)
    check("verde_dentro_5pct",
          {'sigpac_verificado_en': '2026-07-10', 'sigpac_superficie_ha': 10.0, 'superficie_ha': 10.2},
          'verde', 2.0)
    check("verde_limite_5pct",
          {'sigpac_verificado_en': '2026-07-10', 'sigpac_superficie_ha': 10.0, 'superficie_ha': 9.5},
          'verde', -5.0)
    check("ambar_fuera",
          {'sigpac_verificado_en': '2026-07-10', 'sigpac_superficie_ha': 10.0, 'superficie_ha': 8.0},
          'ambar', -20.0)
    check("ambar_sin_declarada",
          {'sigpac_verificado_en': '2026-07-10', 'sigpac_superficie_ha': 10.0, 'superficie_ha': None},
          'ambar', None)
    print("TODOS OK")


if __name__ == '__main__':
    run()
