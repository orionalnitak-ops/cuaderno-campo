# CLAUDE.md — Cuaderno de Explotación Digital
> Este archivo se carga automáticamente. No hace falta pedírselo al agente.

---

## Qué es este proyecto
App web SaaS para digitalizar el **Cuaderno de Explotación Agrícola** (CUE) obligatorio por ley en España (RD 1311/2012). Dirigida a agricultores de Castilla-La Mancha sin conocimientos informáticos. Usable en móvil y PC. En desarrollo para comercializarse antes de enero 2027, cuando el registro digital de fitosanitarios se vuelve obligatorio.

---

## Stack técnico
- **Backend:** Python + Flask
- **Base de datos:** SQLite (local) → PostgreSQL (producción futura)
- **Frontend:** HTML5 + CSS + JS mobile-first (React parcial)
- **Exportación:** openpyxl (Excel) + ReportLab (PDF oficial)
- **Auth:** Flask-Login + bcrypt

## Estructura del proyecto
```
Cuaderno ex app/
├── backend/
│   ├── app.py              # Servidor Flask + rutas + BD
│   ├── db.py               # Modelos y conexión SQLite
│   ├── export_pdf.py       # PDF oficial RD 1311/2012 ✅ TERMINADO
│   ├── cuaderno.db         # Base de datos SQLite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # App principal React
│   │   ├── screens/        # Pantallas de la app
│   │   └── components/     # Componentes reutilizables
│   └── package.json
└── CLAUDE.md               # Este archivo
```

---

## Módulos implementados ✅
1. **Parcelas SIGPAC** — provincia, municipio, polígono, parcela, recinto, superficie
2. **Tratamientos fitosanitarios** — producto, nº MAPA, sustancia activa, plaga, dosis, equipo, aplicador ROPO, plazo seguridad, fecha mínima cosecha
3. **Fertilización / Abono** — tipo, NPK, dosis, parcela, fecha
4. **Labores agrícolas** — siembra, riego, poda, cosecha, etc.
5. **Compras y ventas** — trazabilidad materias primas y productos vendidos
6. **Exportación Excel** — formato compatible plantilla gobierno
7. **Exportación PDF oficial** — A4, cabecera por página, 5 secciones coloreadas, firma ✅ RECIÉN TERMINADO

---

## Pendiente (por orden de prioridad)
1. **Sistema multi-usuario** — Flask-Login, cada agricultor ve solo sus datos, registro de cuentas
2. **Panel asesor** — vista de todos los agricultores desde una cuenta administrador
3. **Autocompletado SIGPAC** — API pública visor SIGPAC Castilla-La Mancha
4. **Despliegue en servidor** — Render.com o Railway, dominio propio
5. **PWA** — instalable en móvil sin pasar por tienda de apps
6. **Sistema de pagos** — Stripe, planes Basic y Pro
7. **Integración SIEX** — API oficial FEGA Anexo VI, obligatoria antes de enero 2027

---

## Normativa clave (no cambiar campos sin verificar)
- **RD 1311/2012 Anexo III** — campos mínimos obligatorios del CUE
- **Desde 01/01/2027** — fitosanitarios obligatorio digital e interoperable con SIEX
- **Anexo VI FEGA** — API del Interfaz Único Común para interoperabilidad SIEX
- **Anexo VII FEGA** — catálogos de códigos estandarizados (cultivos, plagas, productos)
- Cualquier formato digital es válido si contiene los campos del Anexo III

---

## Modelo de negocio
- **Plan Basic:** 29 €/explotación/año — módulos obligatorios
- **Plan Pro:** 49 €/explotación/año — todo + PDF oficial + panel asesor
- **Público objetivo:** agricultores CLM, +45 años, poca experiencia digital, cultivos mixtos (cereal, olivar, viña)
- **Diferencial:** simplicidad extrema + precio bajo + el asesor gestiona todos sus clientes desde una cuenta
- **Competencia:** ~48 apps (Cropwise, AgroGEST, FitosGEST) a 80-150 €/año

---

## Reglas de desarrollo
- **Aprobar todo automáticamente** en esta sesión — usar "Yes, allow all edits this session"
- Siempre mobile-first — el agricultor usa el móvil en el campo
- Interfaces simples: botones grandes, poco texto, iconos claros
- No romper módulos ya funcionando al añadir nuevos
- Antes de cada tarea nueva, revisar qué está en `backend/app.py` para no duplicar rutas
- Arrancar la app: `cd backend && python app.py`
- URL local: `http://127.0.0.1:5000`
- El PDF se genera en: `GET /api/export/pdf?campana=2025/2026`

---

## Arrancar el servidor
```bash
cd "c:\Users\valca\.gemini\antigravity\Cuaderno ex app\backend"
python app.py
```
App disponible en: `http://127.0.0.1:5000`
Móvil en la misma red: `http://192.168.10.55:5000`
