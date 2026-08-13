"""Test plano (sin pytest) del escape-hatch de nº de registro MAPA.

Cubre el arreglo de "productos sin nº de registro" (caolín y demás sustancias
básicas / autorizaciones excepcionales, Reg. UE 1107/2009): el nº de registro
deja de ser obligatorio SOLO si se justifica con un motivo válido, y el gate
falla cerrado (sin número y sin motivo válido, bloquea).

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_sin_registro.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from blueprints.tratamientos import _validate_tratamiento  # noqa: E402
from blueprints.compras import _validate_compra  # noqa: E402


def _trat_base(**over):
    """Tratamiento válido en todo menos lo que se sobreescriba."""
    d = {
        'parcela_id': 1,
        'fecha_aplicacion': '2026-07-01',
        'producto_comercial': 'Caolín',
        'sustancia_activa': 'Silicato de aluminio',
        'plaga_objetivo': 'Mosca del olivo',
        'dosis_valor': '11',
        'aplicador_id': 3,
        'equipo_id': 5,
        'plazo_seguridad_dias': '0',
    }
    d.update(over)
    return d


def _ok(cond, msg):
    print(('  OK  ' if cond else 'FAIL  ') + msg)
    if not cond:
        raise AssertionError(msg)


def test_tratamiento_sin_num_ni_motivo_bloquea():
    err = _validate_tratamiento(_trat_base())  # sin num_registro_mapa, sin motivo
    _ok(err is not None and 'Nº Registro MAPA' in err,
        'tratamiento sin número y sin motivo -> bloquea pidiendo el nº')


def test_tratamiento_sustancia_basica_pasa():
    err = _validate_tratamiento(_trat_base(motivo_sin_registro='sustancia_basica'))
    _ok(err is None, 'caolín como sustancia básica (sin número) -> válido')


def test_tratamiento_autorizacion_excepcional_pasa():
    err = _validate_tratamiento(_trat_base(motivo_sin_registro='autorizacion_excepcional'))
    _ok(err is None, 'autorización excepcional (sin número) -> válido')


def test_tratamiento_motivo_invalido_bloquea():
    err = _validate_tratamiento(_trat_base(motivo_sin_registro='porque_si'))
    _ok(err is not None and 'no válido' in err,
        'motivo inventado -> bloquea (gate cerrado)')


def test_tratamiento_con_numero_normal_sigue_validando_formato():
    err = _validate_tratamiento(_trat_base(num_registro_mapa='no-numerico'))
    _ok(err is not None and 'numérico' in err,
        'número no numérico y sin motivo -> sigue exigiendo formato')
    err_ok = _validate_tratamiento(_trat_base(num_registro_mapa='25123'))
    _ok(err_ok is None, 'número numérico válido -> pasa como siempre')


def test_compra_fitosanitario_sin_num_ni_motivo_bloquea():
    err = _validate_compra({'fecha': '2026-07-01', 'tipo_producto': 'fitosanitario',
                            'producto': 'Caolín', 'sustancia_activa': 'Silicato de aluminio'})
    _ok(err is not None and 'Nº de registro MAPA' in err,
        'compra fitosanitario sin número y sin motivo -> bloquea')


def test_compra_fitosanitario_sustancia_basica_pasa():
    err = _validate_compra({'fecha': '2026-07-01', 'tipo_producto': 'fitosanitario',
                            'producto': 'Caolín', 'sustancia_activa': 'Silicato de aluminio',
                            'motivo_sin_registro': 'sustancia_basica'})
    _ok(err is None, 'compra de caolín como sustancia básica -> válido')


def test_compra_fitosanitario_motivo_invalido_bloquea():
    err = _validate_compra({'fecha': '2026-07-01', 'tipo_producto': 'fitosanitario',
                            'producto': 'Caolín', 'sustancia_activa': 'Silicato de aluminio',
                            'motivo_sin_registro': 'porque_si'})
    _ok(err is not None and 'no válido' in err, 'compra con motivo inventado -> bloquea')


if __name__ == '__main__':
    fns = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for fn in fns:
        fn()
    print(f'\n{len(fns)} tests OK')
