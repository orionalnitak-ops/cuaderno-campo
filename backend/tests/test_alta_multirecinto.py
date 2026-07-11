"""Test plano (sin pytest) del validador puro validar_alta_multirecinto.
Ejecutar: python backend/tests/test_alta_multirecinto.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from helpers import validar_alta_multirecinto

# Campos mínimos de ubicación que exige el validador (security review PR #20).
LOC = {'poligono': '4', 'parcela_num': '12'}
# Valores normalizados que el validador devuelve cuando la ubicación llega vacía.
LOC_NORM = {
    'poligono': '4', 'parcela_num': '12', 'comunidad': '',
    'provincia_cod': '', 'provincia_nombre': '',
    'municipio_cod': '', 'municipio_nombre': '',
    'sistema_explotacion': 'Secano',
}


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
        'nombre_base': 'La Vega', **LOC,
        'comunidad': '07-Castilla-La Mancha',
        'provincia_cod': '13', 'provincia_nombre': 'Ciudad Real',
        'municipio_cod': '034', 'municipio_nombre': 'Daimiel',
        'sistema_explotacion': 'Regadío',
        'recintos': [
            {'num': 1, 'uso_sigpac': 'OV-Olivar', 'superficie_ha': '1,2'},
            {'num': 2, 'uso_sigpac': 'OV-Olivar', 'superficie_ha': 2.1},
            {'num': 3, 'uso_sigpac': 'PS-Pasto', 'superficie_ha': None},
        ],
        'uhcs': [{'nombre': 'Olivar — Pol 4 Par 12', 'cultivo': 'Olivar', 'recintos': [2, 1]}],
    }
    check_ok("payload_completo", base, {
        'nombre_base': 'La Vega', 'campana': '2025/2026',
        'poligono': '4', 'parcela_num': '12',
        'comunidad': '07-Castilla-La Mancha',
        'provincia_cod': '13', 'provincia_nombre': 'Ciudad Real',
        'municipio_cod': '034', 'municipio_nombre': 'Daimiel',
        'sistema_explotacion': 'Regadío',
        'recintos': [
            {'num': 1, 'uso_sigpac': 'OV-Olivar', 'superficie_ha': 1.2},
            {'num': 2, 'uso_sigpac': 'OV-Olivar', 'superficie_ha': 2.1},
            {'num': 3, 'uso_sigpac': 'PS-Pasto', 'superficie_ha': None},
        ],
        'uhcs': [{'nombre': 'Olivar — Pol 4 Par 12', 'cultivo': 'Olivar', 'recintos': [1, 2]}],
    })
    check_ok("sin_uhcs", {'nombre_base': 'X', **LOC,
                          'recintos': [{'num': 5, 'uso_sigpac': '', 'superficie_ha': ''}]},
             {'nombre_base': 'X', 'campana': '2025/2026', **LOC_NORM,
              'recintos': [{'num': 5, 'uso_sigpac': '', 'superficie_ha': None}], 'uhcs': []})
    # Sistema de explotación fuera de la allowlist → cae a 'Secano'.
    check_ok("sistema_invalido_fallback",
             {'nombre_base': 'X', **LOC, 'sistema_explotacion': 'lo que sea<script>',
              'recintos': [{'num': 1}]},
             {'nombre_base': 'X', 'campana': '2025/2026', **LOC_NORM,
              'recintos': [{'num': 1, 'uso_sigpac': '', 'superficie_ha': None}], 'uhcs': []})
    # Campos de texto largos se truncan (120 nombre / 5 códigos).
    largo = 'A' * 500
    norm, err = validar_alta_multirecinto(
        {'nombre_base': largo, **LOC, 'provincia_cod': '1234567890',
         'municipio_nombre': largo, 'recintos': [{'num': 1}]})
    assert err is None and len(norm['nombre_base']) == 120 and \
        norm['provincia_cod'] == '12345' and len(norm['municipio_nombre']) == 120, \
        f"truncado: {err!r} {norm!r}"
    print("  OK campos_truncados")

    check_err("sin_nombre", {'nombre_base': '  ', **LOC, 'recintos': [{'num': 1}]}, "nombre")
    check_err("sin_poligono", {'nombre_base': 'X', 'parcela_num': '12',
                               'recintos': [{'num': 1}]}, "polígono")
    check_err("poligono_no_numerico", {'nombre_base': 'X', 'poligono': '4; DROP', 'parcela_num': '12',
                                       'recintos': [{'num': 1}]}, "números")
    check_err("sin_recintos", {'nombre_base': 'X', **LOC, 'recintos': []}, "trozos")
    check_err("num_invalido", {'nombre_base': 'X', **LOC, 'recintos': [{'num': 'a'}]}, "inválido")
    check_err("num_repetido", {'nombre_base': 'X', **LOC, 'recintos': [{'num': 1}, {'num': 1}]}, "repetidos")
    check_err("superficie_negativa", {'nombre_base': 'X', **LOC,
                                      'recintos': [{'num': 1, 'superficie_ha': -1}]}, "mayor que cero")
    check_err("campana_mala", {'nombre_base': 'X', **LOC, 'campana': '2025',
                               'recintos': [{'num': 1}]}, "YYYY/YYYY")
    check_err("uhc_sin_nombre", {'nombre_base': 'X', **LOC, 'recintos': [{'num': 1}, {'num': 2}],
                                 'uhcs': [{'nombre': '', 'recintos': [1, 2]}]}, "nombre del grupo")
    check_err("uhc_un_solo_trozo", {'nombre_base': 'X', **LOC, 'recintos': [{'num': 1}, {'num': 2}],
                                    'uhcs': [{'nombre': 'G', 'recintos': [1]}]}, "al menos 2")
    check_err("uhc_trozo_fantasma", {'nombre_base': 'X', **LOC, 'recintos': [{'num': 1}, {'num': 2}],
                                     'uhcs': [{'nombre': 'G', 'recintos': [1, 9]}]}, "no se van a crear")
    print("TODOS OK")


if __name__ == '__main__':
    run()
