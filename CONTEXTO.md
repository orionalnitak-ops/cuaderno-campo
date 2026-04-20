# CONTEXTO DEL PROYECTO — Cuaderno de Explotación Digital

## Qué es
App web para agricultores (Castilla-La Mancha) que digitaliza el Cuaderno de Explotación Agrícola obligatorio por ley (RD 1311/2012). Diseñada para usuarios sin conocimientos informáticos. Usable en móvil y PC. Comercializable como SaaS.

## Estado actual
- App Flask funcional con SQLite construida en sesiones anteriores
- Módulos implementados: parcelas SIGPAC, tratamientos fitosanitarios, fertilización, labores, compras/ventas
- Exportación a Excel operativa
- En desarrollo: exportación PDF oficial + sistema multi-usuario

## Stack
- Backend: Python + Flask
- BD: SQLite (local) → PostgreSQL (producción)
- Frontend: HTML5 + CSS + JS (mobile-first)
- Exportación: openpyxl (Excel) + ReportLab (PDF)
- Auth: Flask-Login + bcrypt

## Estructura de carpetas
```
cuaderno_campo/
├── app.py          # Servidor Flask + rutas + BD
├── cuaderno.db     # SQLite
├── templates/      # HTML
└── static/         # CSS + JS
```

## Módulos de la app
1. **Parcelas** — datos SIGPAC (provincia/municipio/polígono/parcela/recinto/superficie)
2. **Fitosanitarios** — producto, dosis, parcela, fecha, aplicador, plazo seguridad
3. **Fertilización** — abono, NPK, dosis, parcela, fecha
4. **Labores** — siembra, riego, poda, cosecha, etc.
5. **Compras/Ventas** — trazabilidad materias primas y productos vendidos

## Pendiente (por orden de prioridad)
1. PDF oficial (ReportLab) — formato gobierno, A4, cabecera por página
2. Sistema multi-usuario (Flask-Login) — cada agricultor ve solo sus datos
3. Panel asesor — vista de todos los agricultores desde una cuenta
4. Autocompletado SIGPAC — API pública visor SIGPAC Castilla-La Mancha
5. Despliegue en servidor (Render.com o Railway)
6. PWA — instalable en móvil sin tienda
7. Integración SIEX API (Anexo VI FEGA) — antes de enero 2027

## Normativa clave
- RD 1311/2012 Anexo III — campos mínimos obligatorios
- Desde 01/01/2027 — fitosanitarios obligatorio en formato digital e interoperable con SIEX
- Interoperabilidad: Anexo VI (API) + Anexo VII (catálogos códigos) del FEGA
- Cualquier formato digital válido si contiene los campos del Anexo III

## Modelo de negocio
- Plan Basic: 29 €/explotación/año (módulos obligatorios)
- Plan Pro: 49 €/explotación/año (todo + PDF oficial + panel asesor)
- Público: agricultores CLM, +45 años, poca experiencia digital, cultivos mixtos
- Diferencial: simplicidad extrema + precio bajo + el asesor gestiona todos sus clientes

## Competencia
~48 apps en mercado (Cropwise/Syngenta, AgroGEST, FitosGEST). Precio medio 80-150€/año. Hueco: simplicidad para usuario no técnico + precio accesible.
