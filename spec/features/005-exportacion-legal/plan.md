# Exportación Legal PDF/Excel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer que los exports PDF y Excel sean legalmente conformes a RD 1311/2012 + Orden APA/204/2023, añadiendo el código REGA, los campos de asesor/justificación/ROMA/ITEAF en tratamientos, y la sección de riego.

**Architecture:** 4 archivos modificados en secuencia: primero BD y API (base), luego frontend (UI REGA), luego Excel (más simple), finalmente PDF (más complejo). Cada tarea es independiente y commitable por separado.

**Tech Stack:** Python/Flask, SQLite, ReportLab (PDF), openpyxl (Excel), React JSX + Babel CLI

---

## Archivos que se tocan

| Archivo | Qué cambia |
|---|---|
| `backend/db.py` | Añadir `rega TEXT` al DDL de `explotacion` + `_add_col` migration |
| `backend/blueprints/explotacion.py` | Añadir `'rega'` a la lista `fields` del PUT/POST |
| `frontend/screens_settings.jsx` | Añadir campo REGA al array FIELDS + texto de ayuda |
| `frontend/dist/screens_settings.js` | Regenerado por `npm run build` |
| `backend/exports.py` | Tratamientos: JOIN equipos + 4 cols; nueva hoja RIEGO |
| `backend/export_pdf.py` | REGA en portada; tratamientos doble fila; nueva sección riego |

---

## Task 1: DB — añadir campo `rega` a `explotacion`

**Files:**
- Modify: `backend/db.py`

- [ ] **Paso 1: Localizar el bloque CREATE TABLE de explotacion**

  En `db.py`, buscar (línea ~245):
  ```python
  CREATE TABLE IF NOT EXISTS explotacion (
      id {_PK},
      user_id INTEGER DEFAULT 2,
      titular TEXT,
      nif TEXT,
      municipio TEXT,
      provincia TEXT,
      cp TEXT,
      telefono TEXT,
      email TEXT,
      campana_activa TEXT DEFAULT '2025/2026',
      fecha_apertura TEXT,
      lopd_accepted INTEGER DEFAULT 0
  )
  ```

- [ ] **Paso 2: Añadir `rega` al DDL**

  Cambiar a:
  ```python
  CREATE TABLE IF NOT EXISTS explotacion (
      id {_PK},
      user_id INTEGER DEFAULT 2,
      titular TEXT,
      nif TEXT,
      rega TEXT,
      municipio TEXT,
      provincia TEXT,
      cp TEXT,
      telefono TEXT,
      email TEXT,
      campana_activa TEXT DEFAULT '2025/2026',
      fecha_apertura TEXT,
      lopd_accepted INTEGER DEFAULT 0
  )
  ```

- [ ] **Paso 3: Añadir la migración `_add_col` para bases de datos existentes**

  Justo debajo del `CREATE TABLE`, hay (línea ~260):
  ```python
  for col, typ in [('fecha_apertura', 'TEXT'), ('lopd_accepted', 'INTEGER DEFAULT 0')]:
      _add_col(c, 'explotacion', col, typ)
  ```

  Cambiar a:
  ```python
  for col, typ in [('fecha_apertura', 'TEXT'), ('lopd_accepted', 'INTEGER DEFAULT 0'), ('rega', 'TEXT')]:
      _add_col(c, 'explotacion', col, typ)
  ```

- [ ] **Paso 4: Verificar la migración**

  ```bash
  cd "h:\Proyectos\Cuaderno ex app\backend"
  python -c "from db import init_db; init_db(); import sqlite3; c=sqlite3.connect('cuaderno.db').cursor(); c.execute('PRAGMA table_info(explotacion)'); print([r[1] for r in c.fetchall()])"
  ```

  Salida esperada: lista con `'rega'` incluido.

- [ ] **Paso 5: Commit**

  ```bash
  git add backend/db.py
  git commit -m "feat(db): add rega field to explotacion table"
  ```

---

## Task 2: Backend API — exponer campo `rega`

**Files:**
- Modify: `backend/blueprints/explotacion.py:28`

- [ ] **Paso 1: Añadir `rega` a la lista de campos**

  En `blueprints/explotacion.py`, línea ~28:
  ```python
  fields = ['titular', 'nif', 'municipio', 'provincia', 'cp',
            'telefono', 'email', 'campana_activa', 'fecha_apertura']
  ```

  Cambiar a:
  ```python
  fields = ['titular', 'nif', 'rega', 'municipio', 'provincia', 'cp',
            'telefono', 'email', 'campana_activa', 'fecha_apertura']
  ```

  Esto hace que el GET devuelva `rega` y el PUT/POST lo guarde.

- [ ] **Paso 2: Verificar en terminal que el GET devuelve el campo**

  Con el servidor arrancado (`python app.py` en `backend/`):
  ```bash
  curl -s http://localhost:5000/api/explotacion -b "session=..." | python -m json.tool | grep rega
  ```

  O simplemente arrancar el servidor y comprobar que no hay error 500.

- [ ] **Paso 3: Commit**

  ```bash
  git add backend/blueprints/explotacion.py
  git commit -m "feat(api): expose rega field in explotacion endpoint"
  ```

---

## Task 3: Frontend — campo REGA en formulario de ajustes

**Files:**
- Modify: `frontend/screens_settings.jsx:89-115`
- Generated: `frontend/dist/screens_settings.js`

- [ ] **Paso 1: Añadir `rega` al array FIELDS y extender el render con texto de ayuda**

  En `screens_settings.jsx`, el componente `ExplotacionModal`. Actualmente (línea ~89):
  ```javascript
  const FIELDS = [
      ['titular','Titular','text','Nombre completo'],
      ['nif','NIF / CIF','text','12345678A'],
      ['municipio','Municipio','text','Santa Cruz de Mudela'],
      ['provincia','Provincia','text','Ciudad Real'],
      ['cp','Código postal','text','13730'],
      ['telefono','Teléfono','tel','600 000 000'],
      ['email','Email','email','titular@explotacion.es'],
      ['campana_activa','Campaña activa','text','2025/2026'],
  ];
  ```

  Cambiar a (añadiendo `rega` con un 5.º elemento para el texto de ayuda):
  ```javascript
  const FIELDS = [
      ['titular','Titular','text','Nombre completo'],
      ['nif','NIF / CIF','text','12345678A'],
      ['rega','Código REGA','text','ej: ES-CM-12345', 'Número de Registro de Explotaciones Agrícolas. Lo facilita la Consejería de Agricultura de tu comunidad autónoma.'],
      ['municipio','Municipio','text','Santa Cruz de Mudela'],
      ['provincia','Provincia','text','Ciudad Real'],
      ['cp','Código postal','text','13730'],
      ['telefono','Teléfono','tel','600 000 000'],
      ['email','Email','email','titular@explotacion.es'],
      ['campana_activa','Campaña activa','text','2025/2026'],
  ];
  ```

- [ ] **Paso 2: Actualizar el render del FIELDS.map para mostrar el texto de ayuda**

  Actualmente (línea ~108):
  ```javascript
  {FIELDS.map(([k,l,t,ph]) => (
      <div key={k} style={{ marginBottom:14 }}>
          <label className="field-label">{l}</label>
          <input type={t} className="input-field" value={form[k]||''} readOnly placeholder={ph}
              onClick={() => setZoomField({ key:k, label:l, type:t, placeholder:ph })}
              style={{ cursor:'pointer' }} />
      </div>
  ))}
  ```

  Cambiar a:
  ```javascript
  {FIELDS.map(([k,l,t,ph,help]) => (
      <div key={k} style={{ marginBottom:14 }}>
          <label className="field-label">{l}</label>
          <input type={t} className="input-field" value={form[k]||''} readOnly placeholder={ph}
              onClick={() => setZoomField({ key:k, label:l, type:t, placeholder:ph })}
              style={{ cursor:'pointer' }} />
          {help && <p style={{ fontSize:'0.75rem', color:'#6b7280', marginTop:4, marginBottom:0 }}>{help}</p>}
      </div>
  ))}
  ```

- [ ] **Paso 3: Compilar el JSX**

  ```bash
  cd "h:\Proyectos\Cuaderno ex app\frontend"
  npm run build
  ```

  Salida esperada: sin errores, `dist/screens_settings.js` actualizado.

- [ ] **Paso 4: Verificar visualmente**

  Arrancar servidor (`python app.py`) y abrir la app → Ajustes → Datos de la Explotación.
  Comprobar que aparece el campo "Código REGA" entre NIF y Municipio, con texto de ayuda debajo.

- [ ] **Paso 5: Commit**

  ```bash
  git add frontend/screens_settings.jsx frontend/dist/screens_settings.js
  git commit -m "feat(ui): add REGA field to explotacion settings form"
  ```

---

## Task 4: Excel — 4 columnas nuevas en tratamientos + hoja RIEGO

**Files:**
- Modify: `backend/exports.py`

### 4a — Tratamientos: JOIN equipos y 4 columnas nuevas

- [ ] **Paso 1: Actualizar la consulta SQL de tratamientos**

  En `exports.py`, línea ~166, la consulta actual:
  ```python
  trats = dicts(conn, """
      SELECT t.*, p.nombre_finca, e.descripcion as equipo_nombre,
             a.nombre as aplicador_nombre
      FROM tratamientos t
      LEFT JOIN parcelas p ON t.parcela_id = p.id
      LEFT JOIN equipos e ON t.equipo_id = e.id
      LEFT JOIN aplicadores a ON t.aplicador_id = a.id
      WHERE t.user_id=? AND t.campana=?
      ORDER BY t.fecha_aplicacion DESC
  """, (user_id, campana))
  ```

  Cambiar a:
  ```python
  trats = dicts(conn, """
      SELECT t.*, p.nombre_finca,
             e.descripcion as equipo_nombre, e.num_registro_roma, e.fecha_iteaf,
             a.nombre as aplicador_nombre
      FROM tratamientos t
      LEFT JOIN parcelas p ON t.parcela_id = p.id
      LEFT JOIN equipos e ON t.equipo_id = e.id
      LEFT JOIN aplicadores a ON t.aplicador_id = a.id
      WHERE t.user_id=? AND t.campana=?
      ORDER BY t.fecha_aplicacion DESC
  """, (user_id, campana))
  ```

- [ ] **Paso 2: Añadir 4 columnas al array `t_cols`**

  Actualmente (línea ~162):
  ```python
  t_cols = ["ID", "Parcela", "Fecha Aplicación", "Producto Comercial", "Nº Reg. MAPA",
            "Sustancia Activa", "Plaga/Objetivo", "Dosis", "Unidad", "Vol. Caldo (L/ha)",
            "Equipo", "Condic. Meteo.", "Plazo Seg. (días)", "Fecha Mín. Cosecha",
            "Eficacia", "Aplicador", "Notas", "Campaña"]
  ```

  Cambiar a:
  ```python
  t_cols = ["ID", "Parcela", "Fecha Aplicación", "Producto Comercial", "Nº Reg. MAPA",
            "Sustancia Activa", "Plaga/Objetivo", "Dosis", "Unidad", "Vol. Caldo (L/ha)",
            "Equipo", "Condic. Meteo.", "Plazo Seg. (días)", "Fecha Mín. Cosecha",
            "Eficacia", "Aplicador", "Notas", "Campaña",
            "Asesor", "Justificación Actuación", "Nº ROMA Equipo", "Fecha ITEAF Equipo"]
  ```

- [ ] **Paso 3: Añadir los 4 valores al `row_data` de tratamientos**

  Actualmente (línea ~177):
  ```python
  row_data = [
      r.get('id'), r.get('nombre_finca') or r.get('parcela_etiqueta'),
      r.get('fecha_aplicacion'), r.get('producto_comercial'), r.get('num_registro_mapa'),
      r.get('sustancia_activa'), r.get('plaga_objetivo'),
      r.get('dosis_valor'), r.get('dosis_unidad'), r.get('volumen_caldo'),
      r.get('equipo_nombre'), r.get('condiciones_meteo'), r.get('plazo_seguridad_dias'),
      r.get('fecha_recoleccion_minima'), r.get('eficacia'), r.get('aplicador_nombre'),
      r.get('notas'), r.get('campana'),
  ]
  ```

  Cambiar a:
  ```python
  row_data = [
      r.get('id'), r.get('nombre_finca') or r.get('parcela_etiqueta'),
      r.get('fecha_aplicacion'), r.get('producto_comercial'), r.get('num_registro_mapa'),
      r.get('sustancia_activa'), r.get('plaga_objetivo'),
      r.get('dosis_valor'), r.get('dosis_unidad'), r.get('volumen_caldo'),
      r.get('equipo_nombre'), r.get('condiciones_meteo'), r.get('plazo_seguridad_dias'),
      r.get('fecha_recoleccion_minima'), r.get('eficacia'), r.get('aplicador_nombre'),
      r.get('notas'), r.get('campana'),
      r.get('asesor'), r.get('justificacion_actuacion'),
      r.get('num_registro_roma'), r.get('fecha_iteaf'),
  ]
  ```

### 4b — Nueva hoja RIEGO (entre LABORES y COSECHA)

- [ ] **Paso 4: Insertar el bloque de la hoja RIEGO entre ws6 (LABORES) y ws7 (COSECHA)**

  Localizar el comentario `# HOJA 7 — COSECHA` (línea ~240) e insertar el bloque RIEGO justo antes:

  ```python
  # ══════════════════════════════════════════
  # HOJA 6b — RIEGO
  # ══════════════════════════════════════════
  ws_riego = wb.create_sheet("RIEGO")
  riego_cols = ["ID", "Parcela", "Fecha", "Tipo Riego", "Volumen (m³)",
                "Horas", "Fuente Agua", "Notas", "Campaña"]
  _header_row(ws_riego, riego_cols, TEAL_FILL)
  riegos = dicts(conn, """
      SELECT r.*, p.nombre_finca FROM riego r
      LEFT JOIN parcelas p ON r.parcela_id = p.id
      WHERE r.user_id=? AND r.campana=? AND r.deleted_at IS NULL
      ORDER BY r.fecha ASC
  """, (user_id, campana))
  for ri, r in enumerate(riegos, 2):
      riego_row = [r.get('id'), r.get('nombre_finca') or r.get('parcela_etiqueta'),
                  r.get('fecha'), r.get('tipo_riego'), r.get('volumen_m3'),
                  r.get('horas_riego'), r.get('fuente_agua'), r.get('notas'), r.get('campana')]
      for ci, val in enumerate(riego_row, 1):
          ws_riego.cell(row=ri, column=ci, value=val)
      _alt_row(ws_riego, ri)
  _auto_width(ws_riego, riego_cols)
  ```

- [ ] **Paso 5: Verificar en terminal que el Excel se genera sin errores**

  ```bash
  cd "h:\Proyectos\Cuaderno ex app\backend"
  python -c "
  from exports import export_excel
  from flask import Flask
  app = Flask(__name__)
  with app.app_context():
      result = export_excel(2, '2025/2026')
      print('OK' if hasattr(result, 'status_code') or hasattr(result, 'headers') else result)
  "
  ```

  Salida esperada: `OK` (o el objeto response de Flask sin error 500).

- [ ] **Paso 6: Commit**

  ```bash
  git add backend/exports.py
  git commit -m "feat(excel): add asesor/ROMA/ITEAF cols to tratamientos + RIEGO sheet"
  ```

---

## Task 5: PDF — REGA en portada

**Files:**
- Modify: `backend/export_pdf.py:654-668` (función `_cover_page`, bloque `portal_fields`)

- [ ] **Paso 1: Añadir la fila REGA a `portal_fields`**

  En `_cover_page`, el bloque `portal_fields` actualmente empieza así (línea ~654):
  ```python
  portal_fields = [
      ('Titular de la explotación', ex.get('titular') or '—'),
      ('NIF / CIF',                 ex.get('nif') or '—'),
      ('Municipio',                 ex.get('municipio') or '—'),
  ```

  Cambiar a:
  ```python
  portal_fields = [
      ('Titular de la explotación', ex.get('titular') or '—'),
      ('NIF / CIF',                 ex.get('nif') or '—'),
      ('Código REGA',               ex.get('rega') or '—'),
      ('Municipio',                 ex.get('municipio') or '—'),
  ```

- [ ] **Paso 2: Actualizar el índice de secciones en `_cover_page`**

  El bloque `sections` actualmente (línea ~701):
  ```python
  sections = [
      ('1', 'Registro de Parcelas',              'Identificación SIGPAC — polígono, parcela, recinto, uso'),
      ('2', 'Tratamientos Fitosanitarios',        'Producto, nº registro MAPA, plaga, dosis, aplicador, plazo'),
      ('3', 'Abonado / Fertilización',            'Tipo fertilizante, producto, N-P-K, dosis, método'),
      ('4', 'Labores Agrícolas',                  'Siembra, poda, laboreo, horas, maquinaria, operario'),
      ('5', 'Cosecha / Recolección',              'Cultivo, producción, rendimiento, destino, comprador'),
      ('6', 'Plan de Abonado',                    'Programa fertilización por parcela — RD 934/2025 (obligatorio sept 2026)'),
      ('7', 'Compras de Fitosanitarios',          'Trazabilidad adquisiciones — Nº MAPA, lote, proveedor, factura'),
  ]
  ```

  Cambiar a (insertar Riego como sección 5, renumerar el resto):
  ```python
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
  ```

- [ ] **Paso 3: Commit**

  ```bash
  git add backend/export_pdf.py
  git commit -m "feat(pdf): add REGA to cover page and update section index"
  ```

---

## Task 6: PDF — tratamientos en fila doble

**Files:**
- Modify: `backend/export_pdf.py` — `_styles()` y `_section_tratamientos()`

### 6a — Nuevo estilo `table_cell_sub`

- [ ] **Paso 1: Añadir el estilo `table_cell_sub` a la función `_styles()`**

  En `_styles()`, al final del diccionario (antes del cierre `}`):
  ```python
  'table_cell_sub': ParagraphStyle('TableCellSub',
      fontName='Helvetica', fontSize=6.5,
      textColor=C_MUTED, leading=9),
  ```

### 6b — Nueva función `_trat_table`

- [ ] **Paso 2: Añadir la función `_trat_table` justo antes de `_section_tratamientos`**

  ```python
  def _trat_table(rows, styles):
      """Tabla tratamientos con dos filas por registro: aplicación + trazabilidad legal."""
      s = styles

      # 12 columnas proporcionales al ancho de página
      col_w_raw = [1.6, 2.0, 2.6, 1.5, 2.0, 1.8, 1.6, 1.4, 1.2, 1.6, 2.0, 1.5]
      total_w = sum(col_w_raw)
      col_widths = [w * INNER_W / total_w for w in col_w_raw]

      headers = ['Fecha', 'Parcela', 'Producto\nComercial', 'Nº\nMAPA',
                 'Sustancia\nActiva', 'Plaga/\nObjetivo', 'Dosis',
                 'Vol. Caldo\n(L/ha)', 'Plazo\nSeg.(d)', 'F. mín.\nCosecha',
                 'Aplicador', 'Nº ROPO']

      table_data = [[Paragraph(h, s['table_header']) for h in headers]]

      style_cmds = [
          ('BACKGROUND', (0, 0), (-1, 0), C_GREEN2),
          ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
          ('FONTSIZE', (0, 0), (-1, 0), 7),
          ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
          ('VALIGN', (0, 0), (-1, -1), 'TOP'),
          ('TOPPADDING', (0, 0), (-1, 0), 6),
          ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
          ('TOPPADDING', (0, 1), (-1, -1), 3),
          ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
          ('LEFTPADDING', (0, 0), (-1, -1), 4),
          ('RIGHTPADDING', (0, 0), (-1, -1), 4),
          ('GRID', (0, 0), (-1, -1), 0.3, C_GREY2),
          ('LINEBELOW', (0, 0), (-1, 0), 1, C_GREEN2),
      ]

      for i, r in enumerate(rows):
          row_a_idx = 1 + i * 2
          row_b_idx = 2 + i * 2

          dosis = f"{_v(r.get('dosis_valor'))} {_v(r.get('dosis_unidad', ''))}".strip('— ')

          # Fila A — datos de aplicación
          row_a = [
              Paragraph(_fmt_date(r.get('fecha_aplicacion')), s['table_cell']),
              Paragraph(_v(r.get('nombre_finca') or r.get('parcela_etiqueta')), s['table_cell']),
              Paragraph(_v(r.get('producto_comercial')), s['table_cell']),
              Paragraph(_v(r.get('num_registro_mapa')), s['table_cell']),
              Paragraph(_v(r.get('sustancia_activa')), s['table_cell']),
              Paragraph(_v(r.get('plaga_objetivo')), s['table_cell']),
              Paragraph(dosis, s['table_cell']),
              Paragraph(_v(r.get('volumen_caldo')), s['table_cell']),
              Paragraph(_v(r.get('plazo_seguridad_dias')), s['table_cell']),
              Paragraph(_fmt_date(r.get('fecha_recoleccion_minima')), s['table_cell']),
              Paragraph(_v(r.get('aplicador_nombre')), s['table_cell']),
              Paragraph(_v(r.get('num_ropo')), s['table_cell']),
          ]

          # Fila B — trazabilidad legal (4 celdas fusionadas sobre 12 cols: 3+2+3+4)
          equipo_text = (f"Equipo: {_v(r.get('equipo_nombre'))}  ·  "
                         f"ROMA: {_v(r.get('num_registro_roma'))}  ·  "
                         f"ITEAF: {_fmt_date(r.get('fecha_iteaf'))}")
          row_b = [
              Paragraph(equipo_text, s['table_cell_sub']),          # span 0–2
              '', '',
              Paragraph(f"Meteo: {_v(r.get('condiciones_meteo'))}", s['table_cell_sub']),  # span 3–4
              '',
              Paragraph(f"Asesor: {_v(r.get('asesor'))}", s['table_cell_sub']),            # span 5–7
              '', '',
              Paragraph(f"Justif.: {_v(r.get('justificacion_actuacion'))}", s['table_cell_sub']),  # span 8–11
              '', '', '',
          ]

          table_data.append(row_a)
          table_data.append(row_b)

          style_cmds += [
              ('BACKGROUND', (0, row_b_idx), (-1, row_b_idx), C_GREY1),
              ('SPAN', (0, row_b_idx), (2, row_b_idx)),
              ('SPAN', (3, row_b_idx), (4, row_b_idx)),
              ('SPAN', (5, row_b_idx), (7, row_b_idx)),
              ('SPAN', (8, row_b_idx), (11, row_b_idx)),
              ('LINEBELOW', (0, row_b_idx), (-1, row_b_idx), 0.8, C_GREY2),
          ]

      t = Table(table_data, colWidths=col_widths, repeatRows=1)
      t.setStyle(TableStyle(style_cmds))
      return t
  ```

### 6c — Actualizar `_section_tratamientos`

- [ ] **Paso 3: Reemplazar el cuerpo de `_section_tratamientos`**

  Actualmente la función construye la tabla con `_data_table`. Reemplazar todo desde el `c.execute` hasta el final de la función:

  ```python
  def _section_tratamientos(conn, user_id, campana, styles, story):
      import sqlite3
      conn.row_factory = sqlite3.Row
      c = conn.cursor()
      c.execute("""
          SELECT t.*, p.nombre_finca,
                 e.descripcion as equipo_nombre, e.num_registro_roma, e.fecha_iteaf,
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
          'Registro obligatorio RD 1311/2012 Anexo III — Orden APA/204/2023',
          '🌿', C_GREEN2, styles))
      story.append(Spacer(1, 4))

      if not rows:
          story.append(Paragraph('Sin tratamientos registrados en esta campaña.', styles['empty']))
          return

      story.append(Paragraph(
          'Conforme al Art. 67 Reglamento (CE) 1107/2009, RD 1311/2012 Anexo III y Orden APA/204/2023. '
          'Fila superior: datos de aplicación. Fila inferior (gris): equipo, asesor y justificación.',
          styles['note']))

      story.append(_trat_table(rows, styles))
      story.append(Spacer(1, 4))
      story.append(Paragraph(
          f'Total registros campaña {campana}: {len(rows)} tratamientos',
          styles['note']))
  ```

- [ ] **Paso 4: Verificar que el PDF se genera sin errores**

  ```bash
  cd "h:\Proyectos\Cuaderno ex app\backend"
  python -c "
  from export_pdf import export_pdf
  from flask import Flask
  app = Flask(__name__)
  with app.app_context():
      result = export_pdf(2, '2025/2026')
      print('OK' if hasattr(result, 'headers') else result)
  "
  ```

  Salida esperada: `OK`

- [ ] **Paso 5: Commit**

  ```bash
  git add backend/export_pdf.py
  git commit -m "feat(pdf): restructure tratamientos to double-row with ROMA/asesor/justificacion"
  ```

---

## Task 7: PDF — sección Riego + llamada en export_pdf

**Files:**
- Modify: `backend/export_pdf.py`

- [ ] **Paso 1: Añadir la función `_section_riego` antes de `_cover_page`**

  ```python
  def _section_riego(conn, user_id, campana, styles, story):
      import sqlite3
      conn.row_factory = sqlite3.Row
      c = conn.cursor()
      c.execute("""
          SELECT r.*, p.nombre_finca FROM riego r
          LEFT JOIN parcelas p ON r.parcela_id = p.id
          WHERE r.user_id=? AND r.campana=? AND r.deleted_at IS NULL
          ORDER BY r.fecha ASC
      """, (user_id, campana))
      rows = [dict(r) for r in c.fetchall()]

      story.append(PageBreak())
      story.append(_section_banner(
          'Riego',
          'Registro de riegos por parcela y campaña — RD 1311/2012',
          '💧', C_CYAN, styles))
      story.append(Spacer(1, 4))

      if not rows:
          story.append(Paragraph('Sin registros de riego en esta campaña.', styles['empty']))
          return

      cols = ['Fecha', 'Parcela', 'Tipo de Riego', 'Volumen (m³)',
              'Horas', 'Fuente de Agua', 'Notas']
      widths = [1.8*cm, 2.8*cm, 3.0*cm, 2.0*cm, 1.6*cm, 3.2*cm, 3.0*cm]
      total = sum(widths)
      widths = [w * INNER_W / total for w in widths]

      total_vol = 0.0
      data_rows = []
      for r in rows:
          vol = r.get('volumen_m3')
          try:
              total_vol += float(vol or 0)
          except (ValueError, TypeError):
              pass
          data_rows.append([
              _fmt_date(r.get('fecha')),
              _v(r.get('nombre_finca') or r.get('parcela_etiqueta')),
              _v(r.get('tipo_riego')),
              _v(r.get('volumen_m3')),
              _v(r.get('horas_riego')),
              _v(r.get('fuente_agua')),
              _v(r.get('notas')),
          ])

      story.append(_data_table(cols, data_rows, widths, C_CYAN, styles))
      story.append(Spacer(1, 4))
      story.append(Paragraph(
          f'Total registros: {len(rows)}  ·  Volumen total: {total_vol:.2f} m³',
          styles['note']))
  ```

- [ ] **Paso 2: Insertar la llamada a `_section_riego` en `export_pdf()`**

  En la función `export_pdf()`, actualmente (línea ~785):
  ```python
  # ── Section 4: Labores ──
  _section_labores(conn, user_id, campana, styles, story)
  story.append(Spacer(1, 10))

  # ── Section 5: Cosecha ──
  _section_cosecha(conn, user_id, campana, styles, story)
  ```

  Cambiar a:
  ```python
  # ── Section 4: Labores ──
  _section_labores(conn, user_id, campana, styles, story)
  story.append(Spacer(1, 10))

  # ── Section 5: Riego ──
  _section_riego(conn, user_id, campana, styles, story)
  story.append(Spacer(1, 10))

  # ── Section 6: Cosecha ──
  _section_cosecha(conn, user_id, campana, styles, story)
  ```

- [ ] **Paso 3: Verificar PDF completo con todas las secciones**

  ```bash
  cd "h:\Proyectos\Cuaderno ex app\backend"
  python -c "
  from export_pdf import export_pdf
  from flask import Flask
  app = Flask(__name__)
  with app.app_context():
      result = export_pdf(2, '2025/2026')
      print('OK — PDF generado sin errores')
  "
  ```

  Salida esperada: `OK — PDF generado sin errores`

- [ ] **Paso 4: Verificación manual completa**

  1. Arrancar servidor: `python app.py` en `backend/`
  2. Abrir la app en el navegador → Ajustes → rellenar un código REGA de prueba → Guardar
  3. Generar PDF → Verificar:
     - Portada: aparece "Código REGA" con el valor rellenado
     - Sección 2 (Tratamientos): cada tratamiento muestra 2 filas; la segunda en gris con Equipo/ROMA/ITEAF/Asesor/Justificación
     - Sección 5 (Riego): existe la sección (aunque aparezca "Sin registros de riego")
     - Índice de portada: 8 secciones incluyendo Riego en posición 5
  4. Generar Excel → Verificar:
     - Hoja "TRATAMIENTOS FITOSANITARIOS": tiene columnas Asesor, Justificación Actuación, Nº ROMA Equipo, Fecha ITEAF Equipo al final
     - Existe hoja "RIEGO"

- [ ] **Paso 5: Commit final**

  ```bash
  git add backend/export_pdf.py
  git commit -m "feat(pdf): add riego section and complete legal export compliance"
  ```

---

## Verificación final de criterios de aceptación

- [ ] PDF portada muestra REGA (o `—` si no rellenado) ✓
- [ ] Cada tratamiento en PDF: 2 filas (aplicación + trazabilidad legal) ✓
- [ ] Campos `asesor`, `justificacion_actuacion`, `num_registro_roma`, `fecha_iteaf` en fila 2 ✓
- [ ] PDF incluye sección Riego con 7 campos ✓
- [ ] Excel hoja tratamientos: 4 columnas nuevas al final ✓
- [ ] Excel hoja RIEGO siempre presente ✓
- [ ] Campo REGA en formulario de ajustes de explotación ✓
- [ ] Agricultor sin REGA puede exportar sin error ✓
- [ ] Todos los datos filtran por `user_id` (garantizado por las consultas existentes) ✓
