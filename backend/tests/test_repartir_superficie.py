"""Test plano (sin pytest) del reparto de una cantidad total entre las parcelas de un grupo UHC.

Cubre la fase 1 de spec/features/016-uhc-en-cosecha-abonado-cultivo/plan.md.

Por qué existe: en Cosecha y en Cultivo campaña hay cantidades ABSOLUTAS
(kg cosechados, kg sembrados). Al registrar por grupo UHC, replicar el mismo
valor en cada parcela multiplicaría la cosecha por el nº de parcelas — un dato
falso en un documento legal. Se reparte proporcional a la superficie.

El criterio 3 de la spec es el que manda: la suma de lo repartido tiene que ser
EXACTAMENTE el total que tecleó el agricultor. Ni un kilo de más ni de menos.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_repartir_superficie.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helpers import repartir_por_superficie  # noqa: E402


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def _p(pid, sup):
    """Parcela mínima tal y como la devuelve _parcelas_uhc()."""
    return {'id': pid, 'nombre_finca': f"Finca {pid}", 'superficie_ha': sup}


# ── A · el reparto proporcional ───────────────────────────────────────────────

def test_proporcional_simple():
    print("A · reparto proporcional:")
    # 10 ha en total, 3.000 kg -> 300 kg/ha
    r = repartir_por_superficie(3000, [_p(1, 5), _p(2, 3), _p(3, 2)])
    check("la parcela de 5 ha se lleva 1500", r[1] == 1500)
    check("la de 3 ha se lleva 900", r[2] == 900)
    check("la de 2 ha se lleva 600", r[3] == 600)
    check("una entrada por parcela", len(r) == 3)


def test_una_sola_parcela():
    print("B · una sola parcela:")
    r = repartir_por_superficie(1234.56, [_p(7, 4.2)])
    check("se lleva el total entero", r[7] == 1234.56)


# ── C · el criterio 3: la suma cuadra SIEMPRE ─────────────────────────────────

def test_suma_exacta_con_decimales_feos():
    print("C · la suma es exacta (criterio 3):")
    # 3 parcelas iguales y un total que no divide: 1000/3 = 333.333...
    r = repartir_por_superficie(1000, [_p(1, 1), _p(2, 1), _p(3, 1)])
    check("suma exactamente 1000 con 3 parcelas", round(sum(r.values()), 2) == 1000)

    # 7 parcelas de superficies dispares, total con céntimos
    parcelas = [_p(i, s) for i, s in enumerate([0.37, 1.21, 2.05, 0.9, 3.33, 1.14, 0.5], 1)]
    r = repartir_por_superficie(4821.77, parcelas)
    check("suma exactamente 4821.77 con 7 parcelas", round(sum(r.values()), 2) == 4821.77)

    # El caso que más duele: el resto se acumula en la última, no se pierde
    r = repartir_por_superficie(100, [_p(1, 1), _p(2, 1), _p(3, 1), _p(4, 1), _p(5, 1),
                                      _p(6, 1), _p(7, 1)])
    check("suma exactamente 100 con 7 parcelas iguales", round(sum(r.values()), 2) == 100)
    check("la última absorbe el redondeo", r[7] != r[1])


def test_no_se_pierde_nada_en_reparto_grande():
    print("D · reparto grande:")
    parcelas = [_p(i, 1 + (i % 5) * 0.3) for i in range(1, 51)]
    r = repartir_por_superficie(98765.43, parcelas)
    check("50 parcelas, suma exacta", round(sum(r.values()), 2) == 98765.43)
    check("ninguna cantidad negativa", all(v >= 0 for v in r.values()))


# ── E · superficies ausentes: se reparte a partes iguales ─────────────────────

def test_sin_superficie_reparte_igual():
    print("E · parcelas sin superficie:")
    # Una sin superficie -> proporcional daría 0 a esa parcela. Se cae a partes
    # iguales: no es exacto agronómicamente, pero no inventa una superficie.
    r = repartir_por_superficie(900, [_p(1, 5), _p(2, None), _p(3, 3)])
    check("las tres reciben lo mismo", r[1] == r[2] == r[3] == 300)
    check("la suma sigue cuadrando", round(sum(r.values()), 2) == 900)

    r = repartir_por_superficie(1000, [_p(1, 0), _p(2, 0)])
    check("todas a 0 ha -> partes iguales", r[1] == r[2] == 500)

    r = repartir_por_superficie(100, [_p(1, 2), _p(2, 3)])
    check("con superficies válidas NO cae a partes iguales", r[1] == 40 and r[2] == 60)


# ── F · bordes que no pueden reventar ─────────────────────────────────────────

def test_bordes():
    print("F · casos borde:")
    check("sin parcelas devuelve vacío", repartir_por_superficie(500, []) == {})
    check("total None -> ceros", repartir_por_superficie(None, [_p(1, 2)]) == {1: 0.0})
    check("total 0 -> ceros", repartir_por_superficie(0, [_p(1, 2), _p(2, 3)]) == {1: 0.0, 2: 0.0})
    check("total como texto se acepta", repartir_por_superficie('300', [_p(1, 1), _p(2, 1)]) == {1: 150.0, 2: 150.0})
    check("total basura -> ceros", repartir_por_superficie('no soy un número', [_p(1, 1)]) == {1: 0.0})
    check("superficie como texto se acepta",
          repartir_por_superficie(100, [{'id': 1, 'superficie_ha': '3'},
                                        {'id': 2, 'superficie_ha': '1'}]) == {1: 75.0, 2: 25.0})
    check("superficie negativa se trata como ausente",
          repartir_por_superficie(100, [_p(1, -5), _p(2, 5)]) == {1: 50.0, 2: 50.0})


if __name__ == '__main__':
    print("\n=== 016 fase 1 — repartir_por_superficie() ===\n")
    test_proporcional_simple()
    test_una_sola_parcela()
    test_suma_exacta_con_decimales_feos()
    test_no_se_pierde_nada_en_reparto_grande()
    test_sin_superficie_reparte_igual()
    test_bordes()
    print("\nTODOS LOS TESTS OK\n")
