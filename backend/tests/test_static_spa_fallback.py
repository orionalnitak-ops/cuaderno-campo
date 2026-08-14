"""La ruta estática automática de Flask (static_url_path='') captura el mismo
patrón de URL que la ruta manual serve_static y la registra primero, dejando
la de app.py como código muerto: cualquier URL que no sea un archivo real
(las pantallas SPA como /recuperar) cae en el 404 por defecto de Flask en
vez de servir index.html.
Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_static_spa_fallback.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('SECRET_KEY', 'test')

import app as app_mod  # noqa: E402


def check(nombre, cond):
    assert cond, f"FALLO {nombre}"
    print(f"  OK {nombre}")


def test_ruta_spa_virtual_sirve_index_html():
    client = app_mod.app.test_client()
    resp = client.get('/recuperar')
    check("GET /recuperar responde 200 (no 404 de Flask)", resp.status_code == 200)
    check("GET /recuperar sirve el shell de la SPA", b'id="root"' in resp.data)


if __name__ == '__main__':
    test_ruta_spa_virtual_sirve_index_html()
    print("Todos los tests pasaron.")
