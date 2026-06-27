# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.
Formato: [Keep a Changelog](https://keepachangelog.com/es/1.0.0/) · Versionado: [SemVer](https://semver.org/lang/es/).

---

## [0.9.0] — 2026-06-27

### Módulos CUE (Cuaderno de Explotación)

- **Parcelas SIGPAC** — alta, edición y baja de parcelas con proxy SIGPAC, selector automático de recintos, actualización masiva de superficie/uso, importación desde Excel/Google Sheets
- **Tratamientos fitosanitarios** — registro completo (producto, nº MAPA, sustancia activa, plaga, dosis, equipo ROMA/ITEAF, aplicador ROPO, plazo seguridad, fecha mínima cosecha, asesor, justificación)
- **Fertilización / Plan de abonado** — formulario NPK con preview en tiempo real, cálculo y almacenamiento de N/P₂O₅/K₂O por aplicación (RD 934/2025)
- **Riego** — registro por fecha/parcela/tipo, cálculo de volumen desde lectura de contador
- **Labores agrícolas** — tipos actualizados conforme a normativa (siembra, poda, subsolado, escarda, desvareto, etc.)
- **Cultivo campaña** — múltiples cultivos por parcela, validación de superficie, edición inline, desglose de ha por cultivo en indicador, catálogo IACS con Triticale (cod 451)
- **Compras y ventas** — trazabilidad de fitosanitarios (RD 1311/2012 §5)
- **Unidades Homogéneas de Cultivo (UHC)** — agrupación de parcelas para aplicar tratamientos masivos

### Exportación legal

- **PDF oficial** — documento A4 multi-página con cabecera por página, 8 secciones coloreadas, firma y:
  - Portada con Código REGA (Registro General de Explotaciones Agrícolas)
  - Tratamientos en doble fila: aplicación (fila 1) + trazabilidad legal ROMA/ITEAF/asesor/justificación (fila 2, fondo gris)
  - Sección Riego entre Labores y Cosecha
  - KeepTogether por tratamiento para evitar cortes de página
  - Conforme a RD 1311/2012 Anexo III + Orden APA/204/2023
- **Excel** — libro multi-hoja compatible con plantilla del gobierno:
  - Hoja TRATAMIENTOS con columnas asesor, justificación actuación, nº ROMA equipo, fecha ITEAF
  - Hoja RIEGO (nueva)
  - Hoja COMPRAS-VENTAS (solo si hay datos)

### Infraestructura y plataforma

- **Multi-usuario** — Flask-Login + bcrypt; cada agricultor aislado por `user_id`
- **Autoregistro + trial 7 días** — aviso de expiración con días restantes
- **Stripe Test mode** — checkout → webhook → plan activo; precios Basic/Pro
- **GDPR** — exportar datos del agricultor (Art. 20) y borrado permanente (Art. 17)
- **Panel admin** — exportar PDF por agricultor, vaciar cuaderno, borrar cuenta, chip de plan y fecha
- **Onboarding wizard** — pantalla de datos de explotación obligatoria para usuarios nuevos
- **Hardening de seguridad** — cookies HttpOnly/Secure/SameSite, headers CSP, rate limit con Redis, validación de entradas
- **Refactor Blueprints** — `app.py` monolito dividido en 14 Flask Blueprints
- **Compilación JSX** — pre-compilación con Babel CLI en lugar de Babel Standalone en navegador

### PWA y experiencia móvil

- **PWA offline completa** — Service Worker v18, caché de React CDN, IndexedDB para parcelas/historial/equipos/aplicadores, sync automático al volver la conexión
- **NLP por voz** — dictado natural sin conexión ("he regado la parcela 5 con 200 m³")
- **"Habla que yo escribo"** — formulario asistido por voz para todos los módulos
- **Pantalla de ayuda contextual** — guía de inicio + ayuda por pantalla con slides visuales
- **Mobile-first** — diseño "Surco Moderno", botones ≥44px, FAB con lápiz, nav inferior

### Widget meteorológico y alertas

- **Tiempo actual** — Open-Meteo sin API key
- **Alertas oficiales** — METEOALARM ATOM como fuente primaria + AEMET OpenData CAP como fallback
- **Push notifications VAPID** — APScheduler cada 30 min, Redis lock multi-worker
- **Avisos de campo** — acordeón colapsable (viento, calor, lluvia, chubascos WMO 80-82)
- **Modal zoom** — al tocar una alerta AEMET oficial, período de validez, refresco cada 10 min

### Hosting y deploy

- **EasyPanel / VPS Contabo** — Dockerfile en raíz, gunicorn con `--preload`, advisory lock en `init_db`
- **Auto-deploy** — webhook GitHub → EasyPanel
- **Base de datos** — SQLite (local) / PostgreSQL en producción con patrón `get_db()` + `dicts()`/`one()`

---

## Pendiente (próximos releases)

- `v0.9.1` — Stripe Live mode (precios en EUR, cobro real)
- `v0.9.x` — Emails transaccionales (Resend): verificación + bienvenida diferenciada trial/pago
- `v0.9.x` — Pantalla de ayuda visual completa (6 slides SVG, swipe)
- `v1.0.0` — Integración SIEX / IUWS (obligatoria 01/01/2027)

---

[0.9.0]: https://github.com/orionalnitak-ops/cuaderno-campo/commits/v0.9.0
