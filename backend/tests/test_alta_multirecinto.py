"""Test plano (sin pytest) del validador puro validar_alta_multirecinto.
Ejecutar: python backend/tests/test_alta_multirecinto.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from helpers import validar_alta_multirecinto


def check_ok(nombre, data, esperado):
    norm, err = validar_alta_multirecinto(data)
    assert err is None, f"{nombre}: error inesperado {err!r}"
    assert norm == esperado, f"{nombre}:\n  got  {norm!r}\n  want {esperado!r}"
    print(f"  OK {nombre}")


def check_err(nombre, data, fragmento):
    norm, err = validar_alta_multirecinto(data)
    assert norm is None, f"{nombre}: se esperaba error, llegó {norm!r}"
    assert fragmento in err, f"{nombre}: {fragmento!r} no está en {err!r}"
    print(f"  OK {nombre}")


def run():
    base = {
        'nombre_base': 'La Vega',
        'recintos': [
            {'num': 1, 'uso_sigpac': 'OV-Olivar', 'superficie_ha': '1,2'},
            {'num': 2, 'uso_sigpac': 'OV-Olivar', 'superficie_ha': 2.1},
            {'num': 3, 'uso_sigpac': 'PS-Pasto', 'superficie_ha': None},
        ],
        'uhcs': [{'nombre': 'Olivar — Pol 4 Par 12', 'cultivo': 'Olivar', 'recintos': [2, 1]}],
    }
    check_ok("payload_completo", base, {
        'nombre_base': 'La Vega', 'campana': '2025/2026',
        'recintos': [
            {'num': 1, 'uso_sigpac': 'OV-Olivar', 'superficie_ha': 1.2},
            {'num': 2, 'uso_sigpac': 'OV-Olivar', 'superficie_ha': 2.1},
            {'num': 3, 'uso_sigpac': 'PS-Pasto', 'superficie_ha': None},
        ],
        'uhcs': [{'nombre': 'Olivar — Pol 4 Par 12', 'cultivo': 'Olivar', 'recintos': [1, 2]}],
    })
    check_ok("sin_uhcs", {'nombre_base': 'X', 'recintos': [{'num': 5, 'uso_sigpac': '', 'superficie_ha': ''}]},
             {'nombre_base': 'X', 'campana': '2025/2026',
              'recintos': [{'num': 5, 'uso_sigpac': '', 'superficie_ha': None}], 'uhcs': []})

    check_err("sin_nombre", {'nombre_base': '  ', 'recintos': [{'num': 1}]}, "nombre")
    check_err("sin_recintos", {'nombre_base': 'X', 'recintos': []}, "trozos")
    check_err("num_invalido", {'nombre_base': 'X', 'recintos': [{'num': 'a'}]}, "inválido")
    check_err("num_repetido", {'nombre_base': 'X', 'recintos': [{'num': 1}, {'num': 1}]}, "repetidos")
    check_err("superficie_negativa", {'nombre_base': 'X', 'recintos': [{'num': 1, 'superficie_ha': -1}]}, "mayor que cero")
    check_err("campana_mala", {'nombre_base': 'X', 'campana': '2025', 'recintos': [{'num': 1}]}, "YYYY/YYYY")
    check_err("uhc_sin_nombre", {'nombre_base': 'X', 'recintos': [{'num': 1}, {'num': 2}],
                                 'uhcs': [{'nombre': '', 'recintos': [1, 2]}]}, "nombre del grupo")
    check_err("uhc_un_solo_trozo", {'nombre_base': 'X', 'recintos': [{'num': 1}, {'num': 2}],
                                    'uhcs': [{'nombre': 'G', 'recintos': [1]}]}, "al menos 2")
    check_err("uhc_trozo_fantasma", {'nombre_base': 'X', 'recintos': [{'num': 1}, {'num': 2}],
                                     'uhcs': [{'nombre': 'G', 'recintos': [1, 9]}]}, "no se van a crear")
    print("TODOS OK")


if __name__ == '__main__':
    run()
