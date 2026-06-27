"""
export_pdf.py — PDF oficial Cuaderno de Explotación Agrícola
Formato: A4 vertical, cabecera en cada página, RD 1311/2012 Anexo III
"""
import io
import datetime
from flask import send_file

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Color palette (Stitch / "Surco Moderno") ──
C_DARK    = colors.HexColor('#141b2b')   # secondary-fixed
C_GREEN   = colors.HexColor('#00694c')   # primary
C_GREEN2  = colors.HexColor('#1a4731')   # deep forest
C_LIME    = colors.HexColor('#68dbae')   # primary-fixed-dim
C_BLUE    = colors.HexColor('#1e3a5f')   # labor
C_VIOLET  = colors.HexColor('#3730a3')   # fertilización
C_CYAN    = colors.HexColor('#0c4a6e')   # riego
C_PINK    = colors.HexColor('#9f1239')   # cosecha
C_AMBER   = colors.HexColor('#78350f')   # planes
C_GREY1   = colors.HexColor('#f3f4f6')   # row alt
C_GREY2   = colors.HexColor('#e5e7eb')   # divider
C_TEXT    = colors.HexColor('#111827')
C_MUTED   = colors.HexColor('#6b7280')
C_WHITE   = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm
INNER_W = PAGE_W - 2 * MARGIN


def _styles():
    base = getSampleStyleSheet()
    normal = base['Normal']
    return {
        'cover_title': ParagraphStyle('CoverTitle',
            fontName='Helvetica-Bold', fontSize=22,
            textColor=C_WHITE, leading=28, alignment=TA_CENTER),
        'cover_sub': ParagraphStyle('CoverSub',
            fontName='Helvetica', fontSize=11,
            textColor=C_LIME, leading=16, alignment=TA_CENTER),
        'cover_label': ParagraphStyle('CoverLabel',
            fontName='Helvetica-Bold', fontSize=8,
            textColor=C_LIME, leading=12, spaceAfter=2),
        'cover_value': ParagraphStyle('CoverValue',
            fontName='Helvetica', fontSize=10,
            textColor=C_WHITE, leading=14, spaceAfter=6),
        'section_title': ParagraphStyle('SectionTitle',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=C_WHITE, leading=18, spaceAfter=2),
        'section_sub': ParagraphStyle('SectionSub',
            fontName='Helvetica', fontSize=8,
            textColor=C_LIME, leading=12, spaceAfter=0),
        'table_header': ParagraphStyle('TableHeader',
            fontName='Helvetica-Bold', fontSize=7,
            textColor=C_WHITE, leading=10, alignment=TA_CENTER),
        'table_cell': ParagraphStyle('TableCell',
            fontName='Helvetica', fontSize=7.5,
            textColor=C_TEXT, leading=10),
        'table_cell_c': ParagraphStyle('TableCellC',
            fontName='Helvetica', fontSize=7.5,
            textColor=C_TEXT, leading=10, alignment=TA_CENTER),
        'footer': ParagraphStyle('Footer',
            fontName='Helvetica', fontSize=7,
            textColor=C_MUTED, leading=10),
        'note': ParagraphStyle('Note',
            fontName='Helvetica-Oblique', fontSize=7.5,
            textColor=C_MUTED, leading=11, spaceAfter=4),
        'empty': ParagraphStyle('Empty',
            fontName='Helvetica-Oblique', fontSize=9,
            textColor=C_MUTED, leading=14, alignment=TA_CENTER, spaceBefore=8, spaceAfter=8),
    }


def _fmt_date(val):
    if not val:
        return '—'
    try:
        d = datetime.date.fromisoformat(str(val))
        return d.strftime('%d/%m/%Y')
    except Exception:
        return str(val)


def _v(val, default='—'):
    if val is None or val == '':
        return default
    return str(val)


def _yesno(val):
    return 'Sí' if val else 'No'


# ─────────────────────────────────────────────────────────
# PAGE TEMPLATE — header + footer on every page
# ─────────────────────────────────────────────────────────
class _PageTemplate:
    def __init__(self, titular, campana):
        self.titular = titular
        self.campana = campana

    def __call__(self, canvas, doc):
        canvas.saveState()
        w, h = A4

        # ── Top bar ──
        canvas.setFillColor(C_DARK)
        canvas.rect(0, h - 1.1 * cm, w, 1.1 * cm, fill=1, stroke=0)

        canvas.setFont('Helvetica-Bold', 8)
        canvas.setFillColor(C_WHITE)
        canvas.drawString(MARGIN, h - 0.72 * cm, '🌿  Cuaderno de Campo')

        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(C_LIME)
        camp_text = f'Campaña {self.campana}  ·  {self.titular}'
        canvas.drawRightString(w - MARGIN, h - 0.72 * cm, camp_text)

        # ── Bottom bar ──
        canvas.setFillColor(C_GREY2)
        canvas.rect(0, 0, w, 0.9 * cm, fill=1, stroke=0)

        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(C_MUTED)
        canvas.drawString(MARGIN, 0.32 * cm,
                          'RD 1311/2012 Anexo III · Generado con Cuaderno de Campo Digital')
        canvas.drawRightString(w - MARGIN, 0.32 * cm,
                               f'Página {doc.page}')

        canvas.restoreState()


# ─────────────────────────────────────────────────────────
# SECTION BANNER
# ─────────────────────────────────────────────────────────
def _section_banner(title, subtitle, icon, color, styles):
    """Colored banner that starts each section."""
    banner_data = [[
        Paragraph(f'{icon}  {title}', styles['section_title']),
        Paragraph(subtitle, styles['section_sub']),
    ]]
    t = Table(banner_data, colWidths=[INNER_W * 0.65, INNER_W * 0.35])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), color),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (0, -1), 14),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 14),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [color]),
    ]))
    return t


def _data_table(col_headers, rows, col_widths, header_color, styles):
    """Build a styled data table. rows is list of lists of plain values."""
    s = styles

    # Header row
    header = [Paragraph(h, s['table_header']) for h in col_headers]
    table_data = [header]

    for i, row in enumerate(rows):
        style = s['table_cell_c'] if False else s['table_cell']
        table_data.append([
            Paragraph(_v(cell), s['table_cell']) for cell in row
        ])

    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    row_bg = []
    for i in range(1, len(rows) + 1):
        bg = C_GREY1 if i % 2 == 0 else C_WHITE
        row_bg.append(('ROWBACKGROUNDS', (0, i), (-1, i), [bg]))

    t.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), C_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7.5),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.4, C_GREY2),
        ('LINEBELOW', (0, 0), (-1, 0), 1, header_color),
    ] + row_bg))
    return t


# ─────────────────────────────────────────────────────────
# SECTIONS
# ─────────────────────────────────────────────────────────
def _section_parcelas(conn, user_id, styles, story):
    from db import get_db
    import sqlite3
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM parcelas WHERE user_id=? AND activa=1 ORDER BY nombre_finca", (user_id,))
    rows = [dict(r) for r in c.fetchall()]

    story.append(_section_banner(
        'Registro de Parcelas', 'Identificación SIGPAC de la explotación',
        '🗺', C_GREEN, styles))
    story.append(Spacer(1, 6))

    if not rows:
        story.append(Paragraph('Sin parcelas registradas.', styles['empty']))
        return

    story.append(Paragraph(
        'Relación de parcelas declaradas conforme al Sistema de Información Geográfica de Parcelas Agrícolas (SIGPAC).',
        styles['note']))

    cols = ['Finca', 'Prov.', 'Municipio', 'Polígono', 'Parcela', 'Rec.',
            'Uso SIGPAC', 'Sup. (ha)', 'Sistem.', 'Agua <50m']
    widths = [3.5*cm, 1.4*cm, 3.2*cm, 1.5*cm, 1.4*cm, 1.0*cm,
              2.8*cm, 1.6*cm, 1.6*cm, 1.5*cm]

    data_rows = []
    for p in rows:
        data_rows.append([
            _v(p.get('nombre_finca')),
            _v(p.get('provincia_nombre')),
            _v(p.get('municipio_nombre')),
            _v(p.get('poligono')),
            _v(p.get('parcela_num')),
            _v(p.get('recinto')),
            _v(p.get('uso_sigpac')),
            _v(p.get('superficie_ha')),
            _v(p.get('sistema_explotacion')),
            _yesno(p.get('masa_agua_cercana')),
        ])

    story.append(_data_table(cols, data_rows, widths, C_GREEN, styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f'Total: {len(rows)} parcelas  ·  Superficie total: '
        f'{sum(float(r.get("superficie_ha") or 0) for r in rows):.4f} ha',
        styles['note']))


def _section_tratamientos(conn, user_id, campana, styles, story):
    import sqlite3
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT t.*, p.nombre_finca, e.descripcion as equipo_nombre,
               a.nombre as aplicador_nombre, a.num_ropo
        FROM tratamientos t
        LEFT JOIN parcelas p ON t.parcela_id = p.id
        LEFT JOIN equipos e ON t.equipo_id = e.id
        LEFT JOIN aplicadores a ON t.aplicador_id = a.id
        WHERE t.user_id=? AND t.campana=?
        ORDER BY t.fecha_aplicacion ASC
    """, (user_id, campana))
    rows = [dict(r) for r in c.fetchall()]

    story.append(PageBreak())
    story.append(_section_banner(
        'Tratamientos Fitosanitarios',
        'Registro obligatorio RD 1311/2012 Anexo III — campos exigidos SIEX',
        '🌿', C_GREEN2, styles))
    story.append(Spacer(1, 4))

    if not rows:
        story.append(Paragraph('Sin tratamientos registrados en esta campaña.', styles['empty']))
        return

    story.append(Paragraph(
        'Conforme al Artículo 67 del Reglamento (CE) 1107/2009 y RD 1311/2012 '
        'Anexo III, sección "Tratamientos Fitosanitarios".',
        styles['note']))

    cols = ['Fecha', 'Parcela', 'Producto\nComercial', 'Nº Reg.\nMAPA',
            'Sustancia\nActiva', 'Plaga\nObjetivo', 'Dosis', 'Vol. Caldo\n(L/ha)',
            'Equipo', 'Meteo.', 'Plazo\nSeg. (d)', 'F. mín.\nCosecha',
            'Aplicador', 'Nº ROPO', 'Eficacia']
    widths = [1.6*cm, 2.0*cm, 2.4*cm, 1.5*cm, 2.0*cm, 2.0*cm, 1.4*cm,
              1.4*cm, 2.0*cm, 1.6*cm, 1.2*cm, 1.6*cm, 2.0*cm, 1.5*cm, 1.4*cm]

    # Adjust widths to fit INNER_W
    total = sum(widths)
    widths = [w * INNER_W / total for w in widths]

    data_rows = []
    for r in rows:
        dosis = f"{_v(r.get('dosis_valor'))} {_v(r.get('dosis_unidad',''))}"
        aplicador = _v(r.get('aplicador_nombre'))
        data_rows.append([
            _fmt_date(r.get('fecha_aplicacion')),
            _v(r.get('nombre_finca') or r.get('parcela_etiqueta')),
            _v(r.get('producto_comercial')),
            _v(r.get('num_registro_mapa')),
            _v(r.get('sustancia_activa')),
            _v(r.get('plaga_objetivo')),
            dosis.strip('— '),
            _v(r.get('volumen_caldo')),
            _v(r.get('equipo_nombre')),
            _v(r.get('condiciones_meteo')),
            _v(r.get('plazo_seguridad_dias')),
            _fmt_date(r.get('fecha_recoleccion_minima')),
            aplicador,
            _v(r.get('num_ropo')),
            _v(r.get('eficacia')),
        ])

    story.append(_data_table(cols, data_rows, widths, C_GREEN2, styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f'Total registros campaña {campana}: {len(rows)} tratamientos',
        styles['note']))


def _section_fertilizacion(conn, user_id, campana, styles, story):
    import sqlite3
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT f.*, p.nombre_finca FROM fertilizacion f
        LEFT JOIN parcelas p ON f.parcela_id = p.id
        WHERE f.user_id=? AND f.campana=?
        ORDER BY f.fecha_aplicacion ASC
    """, (user_id, campana))
    rows = [dict(r) for r in c.fetchall()]

    story.append(PageBreak())
    story.append(_section_banner(
        'Abonado / Fertilización',
        'Registro de aplicaciones de fertilizantes — RD 1311/2012 Anexo III',
        '🌱', C_VIOLET, styles))
    story.append(Spacer(1, 4))

    if not rows:
        story.append(Paragraph('Sin registros de abonado en esta campaña.', styles['empty']))
        return

    cols = ['Fecha', 'Parcela', 'Tipo', 'Producto',
            'Riqueza NPK', 'Dosis', 'Ud.', 'N kg/ha', 'P kg/ha', 'K kg/ha', 'Método']
    widths = [1.6*cm, 2.2*cm, 2.4*cm, 2.6*cm,
              1.8*cm, 1.3*cm, 1.0*cm, 1.4*cm, 1.4*cm, 1.4*cm, 1.8*cm]
    total = sum(widths)
    widths = [w * INNER_W / total for w in widths]

    data_rows = []
    total_n = total_p = total_k = 0.0
    for r in rows:
        n = r.get('n_aplicado')
        p = r.get('p2o5_aplicado')
        k = r.get('k2o_aplicado')
        try:
            total_n += float(n or 0)
            total_p += float(p or 0)
            total_k += float(k or 0)
        except (ValueError, TypeError):
            pass
        data_rows.append([
            _fmt_date(r.get('fecha_aplicacion')),
            _v(r.get('nombre_finca') or r.get('parcela_etiqueta')),
            _v(r.get('tipo_fertilizante')),
            _v(r.get('producto')),
            _v(r.get('riqueza_npk')),
            _v(r.get('dosis_valor')),
            _v(r.get('dosis_unidad')),
            _v(f"{float(n):.2f}" if n is not None else '—'),
            _v(f"{float(p):.2f}" if p is not None else '—'),
            _v(f"{float(k):.2f}" if k is not None else '—'),
            _v(r.get('metodo_aplicacion')),
        ])

    story.append(_data_table(cols, data_rows, widths, C_VIOLET, styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f'Total registros: {len(rows)}  ·  '
        f'N total: {total_n:.2f} kg/ha  ·  P total: {total_p:.2f} kg/ha  ·  K total: {total_k:.2f} kg/ha',
        styles['note']))


def _section_labores(conn, user_id, campana, styles, story):
    import sqlite3
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT l.*, p.nombre_finca FROM labores l
        LEFT JOIN parcelas p ON l.parcela_id = p.id
        WHERE l.user_id=? AND l.campana=?
        ORDER BY l.fecha ASC
    """, (user_id, campana))
    rows = [dict(r) for r in c.fetchall()]

    story.append(PageBreak())
    story.append(_section_banner(
        'Labores Agrícolas',
        'Siembra, poda, laboreo de suelos y otras operaciones — RD 1311/2012',
        '🚜', C_BLUE, styles))
    story.append(Spacer(1, 4))

    if not rows:
        story.append(Paragraph('Sin labores registradas en esta campaña.', styles['empty']))
        return

    cols = ['Fecha', 'Parcela', 'Tipo de Labor', 'Descripción',
            'Maquinaria', 'Horas', 'Operario', 'Notas']
    widths = [1.8*cm, 2.4*cm, 2.8*cm, 3.8*cm,
              2.8*cm, 1.2*cm, 2.2*cm, 2.5*cm]
    total = sum(widths)
    widths = [w * INNER_W / total for w in widths]

    data_rows = []
    for r in rows:
        data_rows.append([
            _fmt_date(r.get('fecha')),
            _v(r.get('nombre_finca') or r.get('parcela_etiqueta')),
            _v(r.get('tipo_labor')),
            _v(r.get('descripcion')),
            _v(r.get('maquinaria')),
            _v(r.get('horas_trabajadas')),
            _v(r.get('operario')),
            _v(r.get('notas')),
        ])

    story.append(_data_table(cols, data_rows, widths, C_BLUE, styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f'Total labores: {len(rows)}', styles['note']))


def _section_cosecha(conn, user_id, campana, styles, story):
    import sqlite3
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT co.*, p.nombre_finca FROM cosecha co
        LEFT JOIN parcelas p ON co.parcela_id = p.id
        WHERE co.user_id=? AND co.campana=?
        ORDER BY co.fecha_inicio ASC
    """, (user_id, campana))
    rows = [dict(r) for r in c.fetchall()]

    story.append(PageBreak())
    story.append(_section_banner(
        'Cosecha / Recolección',
        'Registro de producciones y destino del producto — RD 1311/2012',
        '📦', C_PINK, styles))
    story.append(Spacer(1, 4))

    if not rows:
        story.append(Paragraph('Sin registros de cosecha en esta campaña.', styles['empty']))
        return

    cols = ['Inicio', 'Fin', 'Parcela', 'Cultivo', 'Variedad',
            'Sup. (ha)', 'Producción', 'Unidad', 'Rend. (kg/ha)',
            'Destino', 'Comprador', 'Precio/u.', 'Notas']
    widths = [1.5*cm, 1.5*cm, 2.2*cm, 1.8*cm, 1.8*cm, 1.3*cm,
              1.6*cm, 1.2*cm, 1.6*cm, 2.0*cm, 2.2*cm, 1.4*cm, 2.4*cm]
    total = sum(widths)
    widths = [w * INNER_W / total for w in widths]

    data_rows = []
    total_prod = 0.0
    for r in rows:
        prod_val = r.get('produccion_total_valor') or 0
        try:
            total_prod += float(prod_val)
        except Exception:
            pass
        data_rows.append([
            _fmt_date(r.get('fecha_inicio')),
            _fmt_date(r.get('fecha_fin')),
            _v(r.get('nombre_finca') or r.get('parcela_etiqueta')),
            _v(r.get('cultivo')),
            _v(r.get('variedad')),
            _v(r.get('superficie_cosechada_ha')),
            _v(prod_val),
            _v(r.get('produccion_total_unidad')),
            _v(r.get('rendimiento_kg_ha')),
            _v(r.get('destino')),
            _v(r.get('comprador')),
            _v(r.get('precio_unidad')),
            _v(r.get('notas')),
        ])

    story.append(_data_table(cols, data_rows, widths, C_PINK, styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f'Total registros: {len(rows)}  ·  Producción total campaña: {total_prod:.2f}',
        styles['note']))


def _section_plan_abonado(conn, user_id, campana, styles, story):
    import sqlite3
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT a.*, p.nombre_finca FROM abonado a
        LEFT JOIN parcelas p ON a.parcela_id = p.id
        WHERE a.user_id=? AND a.campana=? AND a.deleted_at IS NULL
        ORDER BY a.fecha_preparacion ASC
    """, (user_id, campana))
    rows = [dict(r) for r in c.fetchall()]

    story.append(PageBreak())
    story.append(_section_banner(
        'Plan de Abonado',
        'Programa de fertilización por parcela — RD 934/2025 (obligatorio desde 1 sept 2026)',
        '🌿', C_AMBER, styles))
    story.append(Spacer(1, 4))

    if not rows:
        story.append(Paragraph('Sin planes de abonado en esta campaña.', styles['empty']))
        return

    cols = ['Fecha', 'Parcela', 'Cultivo', 'Cult. Anterior',
            'Rend. Esp. (kg/ha)', 'Datos Suelo',
            'N nec.', 'P nec.', 'K nec.', 'Abono Rec.', 'Dosis Rec.']
    widths = [1.6*cm, 2.2*cm, 2.0*cm, 2.0*cm,
              2.0*cm, 3.0*cm,
              1.2*cm, 1.2*cm, 1.2*cm, 2.8*cm, 1.8*cm]
    total = sum(widths)
    widths = [w * INNER_W / total for w in widths]

    data_rows = []
    for r in rows:
        data_rows.append([
            _fmt_date(r.get('fecha_preparacion')),
            _v(r.get('nombre_finca') or r.get('parcela_etiqueta')),
            _v(r.get('cultivo')),
            _v(r.get('cultivo_anterior')),
            _v(r.get('rendimiento_esperado_kg_ha')),
            _v(r.get('datos_suelo')),
            _v(r.get('n_necesario_kg_ha')),
            _v(r.get('p_necesario_kg_ha')),
            _v(r.get('k_necesario_kg_ha')),
            _v(r.get('abono_recomendado')),
            _v(r.get('dosis_recomendada_kg_ha')),
        ])

    story.append(_data_table(cols, data_rows, widths, C_AMBER, styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f'Total planes: {len(rows)}  ·  Obligatorio desde 1 sept 2026 (RD 934/2025)',
        styles['note']))


def _section_compras(conn, user_id, campana, styles, story):
    import sqlite3
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT * FROM compras
        WHERE user_id=? AND campana=? AND deleted_at IS NULL
        ORDER BY fecha ASC
    """, (user_id, campana))
    rows = [dict(r) for r in c.fetchall()]

    story.append(PageBreak())
    story.append(_section_banner(
        'Compras de Fitosanitarios y Materias Primas',
        'Trazabilidad de adquisiciones — RD 1311/2012 Anexo III Sección 5',
        '🛒', C_AMBER, styles))
    story.append(Spacer(1, 4))

    if not rows:
        story.append(Paragraph('Sin registros de compras en esta campaña.', styles['empty']))
        return

    cols = ['Fecha', 'Tipo', 'Producto', 'Nº MAPA', 'Sust. Activa',
            'Proveedor', 'Cantidad', 'Ud.', 'Nº Lote', 'Nº Factura']
    widths = [1.6*cm, 1.8*cm, 3.2*cm, 1.8*cm, 3.2*cm,
              2.8*cm, 1.4*cm, 1.0*cm, 1.8*cm, 1.8*cm]
    total = sum(widths)
    widths = [w * INNER_W / total for w in widths]

    data_rows = []
    for r in rows:
        cant = _v(r.get('cantidad_valor'))
        data_rows.append([
            _fmt_date(r.get('fecha')),
            _v(r.get('tipo_producto')),
            _v(r.get('producto')),
            _v(r.get('num_registro_mapa')),
            _v(r.get('sustancia_activa')),
            _v(r.get('proveedor')),
            cant,
            _v(r.get('cantidad_unidad')),
            _v(r.get('num_lote')),
            _v(r.get('num_factura')),
        ])

    story.append(_data_table(cols, data_rows, widths, C_AMBER, styles))
    story.append(Spacer(1, 4))
    fito_count = sum(1 for r in rows if r.get('tipo_producto') == 'fitosanitario')
    story.append(Paragraph(
        f'Total registros: {len(rows)}  ·  Fitosanitarios: {fito_count}',
        styles['note']))


# ─────────────────────────────────────────────────────────
# COVER PAGE
# ─────────────────────────────────────────────────────────
def _cover_page(ex, campana, styles):
    """Return a list of flowables for the cover page."""
    story = []

    # Big header block
    cover_data = [[
        Paragraph('CUADERNO DE EXPLOTACIÓN AGRÍCOLA', styles['cover_title']),
    ]]
    cover_tbl = Table(cover_data, colWidths=[INNER_W])
    cover_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_DARK),
        ('TOPPADDING', (0, 0), (-1, -1), 24),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
    ]))
    story.append(cover_tbl)

    sub_data = [[
        Paragraph('Cuaderno oficial de explotación agrícola  ·  RD 1311/2012 Anexo III', styles['cover_sub']),
    ]]
    sub_tbl = Table(sub_data, colWidths=[INNER_W])
    sub_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_GREEN),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
    ]))
    story.append(sub_tbl)
    story.append(Spacer(1, 20))

    # Data grid
    now_str = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    portal_fields = [
        ('Titular de la explotación', ex.get('titular') or '—'),
        ('NIF / CIF',                 ex.get('nif') or '—'),
        ('Código REGA',               ex.get('rega') or '—'),
        ('Municipio',                 ex.get('municipio') or '—'),
        ('Provincia',                 ex.get('provincia') or '—'),
        ('Código Postal',             ex.get('cp') or '—'),
        ('Teléfono',                  ex.get('telefono') or '—'),
        ('Email',                     ex.get('email') or '—'),
        ('Campaña agrícola',          campana),
        ('Fecha apertura cuaderno',   _fmt_date(ex.get('fecha_apertura'))),
        ('Fecha de generación',       now_str),
        ('Normativa aplicable',       'RD 1311/2012 · Uso sostenible de plaguicidas'),
        ('Desde el 01/01/2027',       'Obligatorio formato digital interoperable SIEX (Anexo VI FEGA)'),
    ]

    for label, val in portal_fields:
        row_data = [[
            Paragraph(label.upper(), styles['cover_label']),
            Paragraph(val, styles['cover_value']),
        ]]
        row_tbl = Table(row_data, colWidths=[5.5*cm, INNER_W - 5.5*cm])
        row_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), C_DARK),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (0, -1), 10),
            ('LEFTPADDING', (1, 0), (1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor('#1e2d4a')),
        ]))
        story.append(row_tbl)

    story.append(Spacer(1, 24))

    # Index / summary box
    idx_data = [[Paragraph('ÍNDICE DEL DOCUMENTO', ParagraphStyle(
        'IdxTitle', fontName='Helvetica-Bold', fontSize=9,
        textColor=C_LIME, leading=14))]]
    idx_tbl = Table(idx_data, colWidths=[INNER_W])
    idx_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_DARK),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('LINEBELOW', (0, 0), (-1, -1), 1, C_GREEN),
    ]))
    story.append(idx_tbl)

    sections = [
        ('1', 'Registro de Parcelas',              'Identificación SIGPAC — polígono, parcela, recinto, uso'),
        ('2', 'Tratamientos Fitosanitarios',        'Producto, nº MAPA, plaga, dosis, equipo ROMA, asesor, justificación'),
        ('3', 'Abonado / Fertilización',            'Tipo fertilizante, producto, N-P-K, dosis, método'),
        ('4', 'Labores Agrícolas',                  'Siembra, poda, laboreo, horas, maquinaria, operario'),
        ('5', 'Riego',                              'Tipo, volumen m³, horas, fuente de agua por parcela'),
        ('6', 'Cosecha / Recolección',              'Cultivo, producción, rendimiento, destino, comprador'),
        ('7', 'Plan de Abonado',                    'Programa fertilización por parcela — RD 934/2025 (obligatorio sept 2026)'),
        ('8', 'Compras de Fitosanitarios',          'Trazabilidad adquisiciones — Nº MAPA, lote, proveedor, factura'),
    ]
    for num, sec_title, sec_desc in sections:
        sec_data = [[
            Paragraph(f'<b>{num}.</b>', ParagraphStyle('Num', fontName='Helvetica-Bold',
                fontSize=9, textColor=C_LIME, leading=14)),
            Paragraph(sec_title, ParagraphStyle('SecTitle', fontName='Helvetica-Bold',
                fontSize=9, textColor=C_WHITE, leading=14)),
            Paragraph(sec_desc, ParagraphStyle('SecDesc', fontName='Helvetica',
                fontSize=8, textColor=C_MUTED, leading=12)),
        ]]
        sec_tbl = Table(sec_data, colWidths=[0.8*cm, 5.5*cm, INNER_W - 6.3*cm])
        sec_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), C_DARK),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (0, -1), 12),
            ('LEFTPADDING', (1, 0), (1, -1), 4),
            ('LEFTPADDING', (2, 0), (2, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#1e2d4a')),
        ]))
        story.append(sec_tbl)

    return story


# ─────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────
def export_pdf(user_id, campana='2025/2026'):
    from db import get_db
    import sqlite3

    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM explotacion WHERE user_id=? LIMIT 1", (user_id,))
    ex_row = c.fetchone()
    ex = dict(ex_row) if ex_row else {}
    titular = ex.get('titular') or 'Explotación'

    buf = io.BytesIO()
    styles = _styles()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f'Cuaderno de Campo — {titular} — Campaña {campana}',
        author=titular,
        subject='Cuaderno oficial RD 1311/2012',
        creator='Cuaderno de Campo Digital v2.0',
    )

    page_cb = _PageTemplate(titular, campana)
    story = []

    # ── Cover ──
    story.extend(_cover_page(ex, campana, styles))
    story.append(PageBreak())

    # ── Section 1: Parcelas ──
    _section_parcelas(conn, user_id, styles, story)
    story.append(Spacer(1, 10))

    # ── Section 2: Tratamientos ──
    _section_tratamientos(conn, user_id, campana, styles, story)
    story.append(Spacer(1, 10))

    # ── Section 3: Fertilización ──
    _section_fertilizacion(conn, user_id, campana, styles, story)
    story.append(Spacer(1, 10))

    # ── Section 4: Labores ──
    _section_labores(conn, user_id, campana, styles, story)
    story.append(Spacer(1, 10))

    # ── Section 5: Cosecha ──
    _section_cosecha(conn, user_id, campana, styles, story)
    story.append(Spacer(1, 10))

    # ── Section 6: Plan Abonado ──
    _section_plan_abonado(conn, user_id, campana, styles, story)
    story.append(Spacer(1, 10))

    # ── Section 7: Compras ──
    _section_compras(conn, user_id, campana, styles, story)

    # ── Firma / cierre ──
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width=INNER_W, thickness=0.5, color=C_GREY2))
    story.append(Spacer(1, 8))

    firma_data = [[
        Paragraph('Firma del titular / responsable de la explotación', ParagraphStyle(
            'FirmaLabel', fontName='Helvetica', fontSize=8, textColor=C_MUTED, leading=12)),
        Paragraph(f'Generado el {datetime.datetime.now().strftime("%d/%m/%Y")} · '
                  f'Cuaderno de Campo Digital · RD 1311/2012',
                  ParagraphStyle('FirmaNote', fontName='Helvetica', fontSize=7,
                                 textColor=C_MUTED, leading=11, alignment=TA_RIGHT)),
    ]]
    firma_tbl = Table(firma_data, colWidths=[INNER_W * 0.5, INNER_W * 0.5])
    firma_tbl.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(firma_tbl)

    # ── Signature line ──
    story.append(Spacer(1, 24))
    sig_data = [[
        Paragraph('_' * 40, ParagraphStyle('SigLine', fontName='Helvetica',
                  fontSize=9, textColor=C_GREY2, alignment=TA_CENTER)),
        Paragraph('_' * 40, ParagraphStyle('SigLine2', fontName='Helvetica',
                  fontSize=9, textColor=C_GREY2, alignment=TA_CENTER)),
    ]]
    sig_tbl = Table(sig_data, colWidths=[INNER_W / 2, INNER_W / 2])
    sig_tbl.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(sig_tbl)

    sig_label = [[
        Paragraph('Titular de la explotación', ParagraphStyle('SigL',
                  fontName='Helvetica', fontSize=7.5, textColor=C_MUTED,
                  alignment=TA_CENTER)),
        Paragraph('Técnico asesor (si procede)', ParagraphStyle('SigR',
                  fontName='Helvetica', fontSize=7.5, textColor=C_MUTED,
                  alignment=TA_CENTER)),
    ]]
    sig_label_tbl = Table(sig_label, colWidths=[INNER_W / 2, INNER_W / 2])
    sig_label_tbl.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(sig_label_tbl)

    conn.close()

    doc.build(story, onFirstPage=page_cb, onLaterPages=page_cb)
    buf.seek(0)

    safe_name = titular.replace(' ', '_').replace('/', '-')[:40]
    camp_safe = campana.replace('/', '-')
    filename = f"Cuaderno_Campo_{safe_name}_{camp_safe}.pdf"

    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf',
    )
