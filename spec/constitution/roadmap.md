# Roadmap — CUE

## Versión actual: v0.9.0 (2026-06-27)

## Prioridades pendientes

| # | Feature | Estado | Urgencia |
|---|---------|--------|----------|
| 001 | Stripe live mode (precios EUR, actualmente en SEK) | Pendiente | 🔴 Crítico |
| 002 | Compatibilidad SIEX — datos, catálogos y exportaciones | Pendiente | 🔴 Deadline 01/01/2027 |
| 003 | Emails transaccionales (Resend) — verificación + bienvenida | Pendiente | 🟠 Alta |
| 004 | Pantalla de ayuda visual (6 slides SVG aprobados) | Pendiente | 🟠 Alta |
| 005 | Asistente IA estadístico | Implementado | 🟡 Media |
| 006 | Módulo riego (UI completa) | En spec | 🟡 Media |
| 007 | NPK / Fertilización avanzada | En spec | 🟡 Media |
| 008 | Plan de abonado avanzado | En spec | 🟡 Media |
| 009 | Offline PWA | En spec | 🟡 Media |
| 010 | UHC (Unidades Homogéneas de Cultivo) | Desplegado (PRs #20-23) | 🟡 Media |

> **Sobre el 002 — qué significa exactamente.** Lo que la ley obliga el 01/01/2027 es que el **agricultor** lleve el cuaderno en formato digital e interoperable con SIEX. No obliga a que esta app envíe los datos por API: el titular puede acceder a su CUE y cumplimentarlo él mismo con sus credenciales digitales. El envío automático por IUWS requiere ser *entidad habilitada* (registro, certificado de sello de componente, autorización firmada por cada titular y, al parecer, estatutos que recojan la representación de terceros ante la administración agraria). Esa vía **no se asume de momento** y por tanto no se promete en ningún sitio. Pendiente de confirmar con `reacue@castillalamancha.es` si un titular puede importar en su CUE un fichero generado por una aplicación externa: si la respuesta es que sí, esa es la vía natural para esta app.

## Módulos ya implementados (v0.9.0)

- Parcelas SIGPAC (CRUD + proxy + bulk update + selector recintos)
- Tratamientos fitosanitarios (RD 1311/2012 + Orden APA/204/2023)
- Fertilización / Abonado básico
- Labores agrícolas
- Riego (backend completo, UI básica)
- Cosecha / Recolección
- Plan de abonado (básico)
- Compras de fitosanitarios
- Exportación PDF/Excel legal (REGA, doble fila tratamientos, sección riego)
- Auth + trial + Stripe (modo test)
- Panel admin
- AEMET / METEOALARM / Open-Meteo
- Push notifications VAPID
- NLP por voz ("Habla que yo escribo")
- SIGPAC proxy
- UHC (backend inicial)
