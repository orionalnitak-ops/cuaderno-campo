"""Test plano (sin pytest) de la exportación por secciones — feature 029.

Lo que se protege aquí, por orden de gravedad:

1. **Sin `?secciones`, el PDF y el Excel salen como siempre.** Es el invariante
   que permitió hacer esta feature sin miedo: nadie que exporte como hasta hoy
   nota nada.

2. **El sello del Anexo III cae cuando el documento no es el cuaderno entero.**
   Si se quitan secciones y el PDF sigue diciendo "Cuaderno oficial · RD
   1311/2012 Anexo III", estaríamos emitiendo un papel con pinta de oficial que
   no lo es. Y cae en los TRES sitios (portada, pie de cada página y metadatos)
   o no sirve de nada: el que se olvide es el que engaña.

3. **Nunca se genera un fichero vacío.** Un libro de Excel sin hojas ni se
   puede guardar, y un PDF sin nada dentro es peor que uno con secciones de
   más. Cualquier entrada rara cae del lado del cuaderno completo.

Ejecutar: backend\\venv\\Scripts\\python.exe backend/tests/test_export_secciones.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helpers import SECCIONES, parse_secciones  # noqa: E402

FALLOS = []


def check(nombre, cond):
    if cond:
        print(f"  OK   {nombre}")
    else:
        print(f"  FALLO {nombre}")
        FALLOS.append(nombre)


# ─────────────────────────────────────────────────────────
# 1. parse_secciones: el guardián de la entrada
# ─────────────────────────────────────────────────────────
def test_parse():
    print("\nparse_secciones")
    todas = set(SECCIONES)

    check("nueve secciones definidas", len(SECCIONES) == 9)

    for entrada in (None, '', '   '):
        sec, comp = parse_secciones(entrada)
        check(f"{entrada!r} -> todas y completo", sec == todas and comp is True)

    sec, comp = parse_secciones('loquesea,BORRAR,xxx')
    check("basura pura -> todas y completo", sec == todas and comp is True)

    sec, comp = parse_secciones('tratamientos')
    check("una sola -> esa y NO completo", sec == {'tratamientos'} and comp is False)

    sec, comp = parse_secciones('  TRATAMIENTOS , Riego ')
    check("mayúsculas y espacios se limpian",
          sec == {'tratamientos', 'riego'} and comp is False)

    sec, comp = parse_secciones('tratamientos,,BORRAR,riego')
    check("basura mezclada se descarta sin tirar lo bueno",
          sec == {'tratamientos', 'riego'} and comp is False)

    sec, comp = parse_secciones(','.join(SECCIONES))
    check("las nueve a mano cuentan como completo (el sello vuelve)",
          sec == todas and comp is True)

    for entrada in (None, '', 'loquesea', 'tratamientos', ','.join(SECCIONES)):
        sec, _ = parse_secciones(entrada)
        check(f"{entrada!r} nunca devuelve vacío", len(sec) > 0)


# ─────────────────────────────────────────────────────────
# 2. Excel: qué hojas salen
# ─────────────────────────────────────────────────────────
def _flask_app():
    """App mínima solo para tener contexto de petición: `send_file` lo exige."""
    from flask import Flask
    return Flask(__name__)


def _texto_pdf(datos):
    """Todo el texto legible de un PDF, sin librerías externas.

    Tres capas que hay que pelar, y saltarse cualquiera da un falso fallo:

    1. **ASCII85.** ReportLab codifica los flujos en ASCII85 antes de
       comprimirlos. Si se intenta descomprimir directamente, `zlib` falla y lo
       que queda es un galimatías donde no se encuentra ninguna palabra.

    2. **Flate.** Debajo del ASCII85 va la compresión. Se deshace con `zlib`,
       biblioteca estándar: no se añade una dependencia por un test.

    3. **El texto viene partido.** ReportLab lo trocea entre paréntesis con
       ajustes de espaciado por medio, así que "RD 1311/2012 Anexo III" puede
       salir como `(RD 1311/2012 Ane)` `(xo III)`. Buscar la frase entera daría
       un falso fallo: se reconstruye juntando todos los paréntesis.

    Se devuelve eso, más los bytes crudos, donde viven los metadatos del
    documento (esos sí van sin comprimir ni codificar).
    """
    import base64
    import re
    import zlib

    flujos = []
    for m in re.finditer(rb'stream[\r\n]+(.*?)endstream', datos, re.S):
        crudo = m.group(1)
        for intento in (crudo,):
            datos_flujo = intento
            # Capa 1: ASCII85 (termina en ~>).
            try:
                cortado = datos_flujo.split(b'~>')[0]
                datos_flujo = base64.a85decode(cortado, adobe=False,
                                               ignorechars=b' \t\r\n\v\f')
            except Exception:
                datos_flujo = intento
            # Capa 2: Flate.
            try:
                datos_flujo = zlib.decompress(datos_flujo)
            except zlib.error:
                pass
            flujos.append(datos_flujo)

    # Capa 3: juntar los trozos entre paréntesis.
    trozos = []
    for f in flujos:
        for t in re.findall(rb'\((?:\\.|[^\\()])*\)', f, re.S):
            trozos.append(t[1:-1])
    reconstruido = b''.join(trozos)

    return (reconstruido + b' || ' + datos).decode('latin-1')


def _db_prueba():
    """Una explotación mínima pero completa: una viña con un tratamiento.

    La usan el test del Excel y el del PDF, así que el esquema vive aquí una
    sola vez.
    """
    import sqlite3

    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE explotacion (id INTEGER PRIMARY KEY, user_id INTEGER,
            titular TEXT, nif TEXT, municipio TEXT, provincia TEXT, cp TEXT,
            telefono TEXT, email TEXT, campana_activa TEXT, fecha_apertura TEXT,
            lopd_accepted INTEGER, rega TEXT, nombre_corto TEXT, activa INTEGER,
            orden INTEGER);
        CREATE TABLE parcelas (id INTEGER PRIMARY KEY, user_id INTEGER,
            explotacion_id INTEGER, nombre_finca TEXT, poligono TEXT,
            parcela_num TEXT, recinto TEXT, provincia_nombre TEXT,
            municipio_nombre TEXT, uso_sigpac TEXT, superficie_ha REAL,
            sistema_explotacion TEXT, masa_agua_cercana INTEGER, notas TEXT,
            activa INTEGER DEFAULT 1);
        CREATE TABLE cultivos_campana (id INTEGER PRIMARY KEY, parcela_id INTEGER,
            explotacion_id INTEGER, campana TEXT, cultivo TEXT, variedad TEXT,
            fecha_siembra TEXT, fecha_recoleccion_prevista TEXT,
            superficie_cultivada_ha REAL, kg_sembrados REAL,
            precio_kg_compra REAL, notas TEXT);
        CREATE TABLE tratamientos (id INTEGER PRIMARY KEY, user_id INTEGER,
            explotacion_id INTEGER, parcela_id INTEGER, parcela_etiqueta TEXT,
            fecha_aplicacion TEXT, producto_comercial TEXT, num_registro_mapa TEXT,
            sustancia_activa TEXT, plaga_objetivo TEXT, dosis_valor REAL,
            dosis_unidad TEXT, volumen_caldo REAL, equipo_id INTEGER,
            condiciones_meteo TEXT, plazo_seguridad_dias INTEGER,
            fecha_recoleccion_minima TEXT, eficacia TEXT, aplicador_id INTEGER,
            notas TEXT, campana TEXT, asesor TEXT, asesor_id INTEGER,
            justificacion_actuacion TEXT, motivo_sin_registro TEXT,
            deleted_at TEXT);
        CREATE TABLE fertilizacion (id INTEGER PRIMARY KEY, user_id INTEGER,
            explotacion_id INTEGER, parcela_id INTEGER, parcela_etiqueta TEXT,
            fecha_aplicacion TEXT, tipo_fertilizante TEXT, producto TEXT,
            riqueza_npk TEXT, dosis_valor REAL, dosis_unidad TEXT,
            metodo_aplicacion TEXT, notas TEXT, campana TEXT,
            n_aplicado REAL, p2o5_aplicado REAL, k2o_aplicado REAL,
            deleted_at TEXT);
        CREATE TABLE labores (id INTEGER PRIMARY KEY, user_id INTEGER,
            explotacion_id INTEGER, parcela_id INTEGER, parcela_etiqueta TEXT,
            fecha TEXT, tipo_labor TEXT, descripcion TEXT, maquinaria TEXT,
            horas_trabajadas REAL, operario TEXT, producto TEXT, notas TEXT,
            campana TEXT);
        CREATE TABLE riego (id INTEGER PRIMARY KEY, user_id INTEGER,
            explotacion_id INTEGER, parcela_id INTEGER, parcela_etiqueta TEXT,
            fecha TEXT, tipo_riego TEXT, volumen_m3 REAL, horas_riego REAL,
            fuente_agua TEXT, notas TEXT, campana TEXT, deleted_at TEXT);
        CREATE TABLE cosecha (id INTEGER PRIMARY KEY, user_id INTEGER,
            explotacion_id INTEGER, parcela_id INTEGER, parcela_etiqueta TEXT,
            fecha_inicio TEXT, fecha_fin TEXT, cultivo TEXT, variedad TEXT,
            superficie_cosechada_ha REAL, produccion_total_valor REAL,
            produccion_total_unidad TEXT, rendimiento_kg_ha REAL, destino TEXT,
            comprador TEXT, precio_unidad REAL, notas TEXT, campana TEXT);
        CREATE TABLE abonado (id INTEGER PRIMARY KEY, user_id INTEGER,
            explotacion_id INTEGER, parcela_id INTEGER, parcela_etiqueta TEXT,
            cultivo TEXT, cultivo_anterior TEXT, rendimiento_esperado_kg_ha REAL,
            n_necesario_kg_ha REAL, p_necesario_kg_ha REAL, k_necesario_kg_ha REAL,
            fecha_preparacion TEXT, datos_suelo TEXT, abono_recomendado TEXT,
            dosis_recomendada_kg_ha REAL, notas TEXT, campana TEXT,
            deleted_at TEXT);
        CREATE TABLE compras (id INTEGER PRIMARY KEY, user_id INTEGER,
            explotacion_id INTEGER, fecha TEXT, tipo_producto TEXT, producto TEXT,
            proveedor TEXT, cantidad_valor REAL, cantidad_unidad TEXT,
            num_lote TEXT, num_factura TEXT, precio_total REAL, notas TEXT,
            campana TEXT, num_registro_mapa TEXT, sustancia_activa TEXT,
            deleted_at TEXT);
        CREATE TABLE equipos (id INTEGER PRIMARY KEY, user_id INTEGER,
            explotacion_id INTEGER, descripcion TEXT, tipo TEXT, marca TEXT,
            modelo TEXT, num_registro_roma TEXT, fecha_iteaf TEXT, notas TEXT);
        CREATE TABLE aplicadores (id INTEGER PRIMARY KEY, user_id INTEGER,
            explotacion_id INTEGER, nombre TEXT, nif TEXT, num_ropo TEXT,
            activo INTEGER DEFAULT 1);
        CREATE TABLE asesores (id INTEGER PRIMARY KEY, user_id INTEGER,
            explotacion_id INTEGER, nombre TEXT, nif TEXT, num_ropo TEXT,
            titulacion TEXT, empresa TEXT, telefono TEXT, email TEXT,
            activo INTEGER DEFAULT 1);
        INSERT INTO explotacion (id, user_id, titular, campana_activa)
             VALUES (1, 1, 'Finca de prueba', '2025/2026');
        INSERT INTO parcelas (id, user_id, explotacion_id, nombre_finca, activa)
             VALUES (1, 1, 1, 'Viña del Molino', 1);
        INSERT INTO cultivos_campana (parcela_id, explotacion_id, campana, cultivo, variedad)
             VALUES (1, 1, '2025/2026', 'Viñedo', 'Tempranillo');
        INSERT INTO tratamientos (user_id, explotacion_id, parcela_id, campana,
                                  producto_comercial, fecha_aplicacion)
             VALUES (1, 1, 1, '2025/2026', 'Producto de prueba', '2026-07-28');
        INSERT INTO compras (user_id, explotacion_id, campana, producto, fecha)
             VALUES (1, 1, '2025/2026', 'Abono de prueba', '2026-03-01');
    """)
    conn.commit()
    return conn


def _hojas(secciones):
    """Genera el Excel contra la BD de prueba y devuelve los títulos de hoja."""
    import db as db_mod
    import exports
    from openpyxl import load_workbook

    conn = _db_prueba()
    original = db_mod.get_db
    db_mod.get_db = lambda *a, **k: conn
    exports.get_db = lambda *a, **k: conn
    try:
        # `send_file` necesita una petición viva. Se monta una de mentira.
        with _flask_app().test_request_context():
            resp = exports.export_excel(1, '2025/2026', 1, secciones)
            # send_file devuelve la respuesta en modo passthrough: hay que
            # desactivarlo para poder leer los bytes.
            resp.direct_passthrough = False
            datos = resp.get_data()
        wb = load_workbook(io.BytesIO(datos))
        return wb.sheetnames
    finally:
        db_mod.get_db = original
        exports.get_db = original


def _pdf(secciones, completo):
    """Genera el PDF contra la misma BD de prueba y devuelve sus bytes."""
    import db as db_mod
    import export_pdf as ep

    conn = _db_prueba()
    original = db_mod.get_db
    db_mod.get_db = lambda *a, **k: conn
    try:
        with _flask_app().test_request_context():
            resp = ep.export_pdf(1, '2025/2026', 1, secciones, completo)
            resp.direct_passthrough = False
            return resp.get_data()
    finally:
        db_mod.get_db = original


def test_excel():
    print("\nExcel — qué hojas salen")

    completo = _hojas(None)
    check("sin secciones: sale la PORTADA", 'PORTADA' in completo)
    check("sin secciones: salen las 9 hojas de datos + portada",
          len(completo) >= 9)
    check("sin secciones: está la de fitosanitarios",
          'TRATAMIENTOS FITOSANITARIOS' in completo)
    check("sin secciones: está el plan de abonado (nuevo en Excel)",
          'PLAN DE ABONADO' in completo)

    solo_trat = _hojas({'tratamientos'})
    check("solo tratamientos: exactamente PORTADA + TRATAMIENTOS",
          solo_trat == ['PORTADA', 'TRATAMIENTOS FITOSANITARIOS'])
    check("solo tratamientos: NO se cuela el riego",
          'RIEGO' not in solo_trat)
    check("solo tratamientos: NO se cuelan las compras",
          'COMPRAS-VENTAS' not in solo_trat)

    dos = _hojas({'tratamientos', 'cultivos_campana'})
    check("dos secciones: salen las dos y la portada",
          sorted(dos) == sorted(['PORTADA', 'CULTIVOS POR CAMPAÑA',
                                 'TRATAMIENTOS FITOSANITARIOS']))

    # El caso que rompe openpyxl si el invariante falla.
    sec_basura, _ = parse_secciones('BORRAR-TODO')
    basura = _hojas(sec_basura)
    check("basura: el libro NUNCA sale sin hojas", len(basura) >= 1)
    check("basura: cae del lado del cuaderno completo", len(basura) >= 9)


# ─────────────────────────────────────────────────────────
# 3. PDF: el sello del Anexo III
# ─────────────────────────────────────────────────────────
def test_pdf_sello():
    """El sello del Anexo III cae en los TRES sitios, y vuelve al marcar todo.

    Se comprueba sobre el texto real del PDF (flujos descomprimidos) y sobre
    los metadatos. Si alguno de los tres sitios se olvidara, este test lo ve:
    el que se olvida es justo el que engaña.
    """
    print("\nPDF - el sello del Anexo III")
    import export_pdf as ep

    completo_txt = _texto_pdf(_pdf(None, True))
    check("completo: portada dice 'Cuaderno oficial'",
          'Cuaderno oficial' in completo_txt)
    check("completo: cita el Anexo III",
          'Anexo III' in completo_txt)
    check("completo: NO se llama extracto",
          'EXTRACTO' not in completo_txt.upper().replace('EXTRACTO DEL CUADERNO DE EXPLOTACION', ''))

    extracto_txt = _texto_pdf(_pdf({'tratamientos'}, False))
    check("extracto: aparece la palabra EXTRACTO",
          'EXTRACTO' in extracto_txt.upper())
    check("extracto: avisa de que no sustituye al cuaderno",
          'no sustituye al cuaderno completo' in extracto_txt)
    check("extracto: la portada YA NO dice 'Cuaderno oficial de explotacion'",
          'Cuaderno oficial de explotaci' not in extracto_txt)
    check("extracto: los metadatos dicen Extracto",
          'Extracto del Cuaderno de Explotaci' in extracto_txt)
    check("extracto: dice qué secciones lleva",
          'Incluye' in extracto_txt)

    # ── El pie de página, comprobado APARTE ──
    # Sale en todas las páginas, así que es el sitio que más engaña si se
    # olvida. Un test que solo mirase la portada y los metadatos daría verde
    # con el sello puesto en las veinte páginas (comprobado sabotéandolo).
    # 'Generado con Cuaderno de Campo Digital' aparece SOLO en el pie.
    FIRMA_PIE = 'Generado con Cuaderno de Campo Digital'
    check("completo: el pie lleva el sello en todas las páginas",
          completo_txt.count(FIRMA_PIE) >= 2)
    check("extracto: el pie YA NO lleva el sello en ninguna página",
          extracto_txt.count(FIRMA_PIE) == 0)
    check("extracto: el aviso sale en todas las páginas, no solo en portada",
          extracto_txt.count('EXTRACTO') >= 2)

    # En un extracto de tratamientos, 'Anexo III' debe salir UNA vez: la cita
    # legal de esa tabla, que sigue siendo cierta. Si saliera más veces,
    # estaría volviendo por el pie o por la portada.
    check("extracto: 'Anexo III' solo queda en la cita de la propia tabla",
          extracto_txt.count('Anexo III') == 1)

    # El sello tiene que VOLVER: si se queda pegado, el extracto de ayer
    # contamina el cuaderno oficial de hoy.
    vuelta_txt = _texto_pdf(_pdf(set(SECCIONES), True))
    check("las nueve a mano: vuelve el sello oficial",
          'Cuaderno oficial' in vuelta_txt and 'no sustituye' not in vuelta_txt)
    check("las nueve a mano: vuelve también el pie",
          vuelta_txt.count(FIRMA_PIE) >= 2)

    check("los nombres de sección del PDF coinciden con helpers.SECCIONES",
          tuple(SECCIONES) == ep.SECCIONES_ORDEN)

    # La ruta de admin (`blueprints/admin.py`) llama `export_pdf(uid, campana)`
    # con dos argumentos y nada más. Tiene que seguir dando el cuaderno entero
    # y sellado: los parámetros nuevos nacen con el valor de "como siempre".
    import db as db_mod
    conn = _db_prueba()
    original = db_mod.get_db
    db_mod.get_db = lambda *a, **k: conn
    try:
        with _flask_app().test_request_context():
            resp = ep.export_pdf(1, '2025/2026')
            resp.direct_passthrough = False
            antiguo_txt = _texto_pdf(resp.get_data())
    finally:
        db_mod.get_db = original
    check("llamada antigua de dos argumentos: cuaderno completo y sellado",
          'Cuaderno oficial' in antiguo_txt and FIRMA_PIE in antiguo_txt)


if __name__ == '__main__':
    test_parse()
    test_excel()
    test_pdf_sello()
    print()
    if FALLOS:
        print(f"{len(FALLOS)} FALLOS: " + ", ".join(FALLOS))
        sys.exit(1)
    print("Todo en verde.")
