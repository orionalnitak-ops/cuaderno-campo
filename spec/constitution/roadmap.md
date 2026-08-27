# Roadmap — CUE

## Versión actual: v0.9.0 (2026-06-27)

## Prioridades pendientes

| # | Feature | Estado | Urgencia |
|---|---------|--------|----------|
| 001 | Stripe live mode (precios EUR) | Implementado | 🟢 Cerrado — ver nota |
| 002 | Compatibilidad SIEX — datos, catálogos y exportaciones (ver desglose por bloque) | Implementado (8/8 bloques) | 🟢 Cerrado — ver nota |
| 003 | Emails transaccionales (Resend) — verificación + bienvenida | Implementado | 🟢 Cerrado — ver nota |
| 004 | Pantalla de ayuda visual (guía de inicio + ayuda contextual) | Implementado | 🟢 Cerrada |
| 005 | Asistente IA estadístico | Implementado | 🟡 Media |
| 006 | Módulo riego (UI completa) | En spec | 🟡 Media |
| 007 | NPK / Fertilización avanzada | En spec | 🟡 Media |
| 008 | Plan de abonado avanzado | En spec | 🟡 Media |
| 009 | Offline PWA | En spec | 🟡 Media |
| 010 | UHC (Unidades Homogéneas de Cultivo) | Desplegado (PRs #20-23) | 🟡 Media |

> **Sobre el 001 — por qué se cierra.** Stripe está en modo live desde agosto de 2026: precios en EUR con IVA incluido (14,99 €/mes o 150 €/año Básico; 29,99 €/mes o 300 €/año Pro — PR #46), factura deducible con NIF/dirección/IVA desglosado (PR #58), y los identificadores de Stripe Test se limpiaron de las cuentas de producción antes de cambiar la clave a `sk_live_` (PR #54). `backend/blueprints/stripe_bp.py` lee precios y claves de variables de entorno (`STRIPE_PRICE_*`, `STRIPE_SECRET_KEY`), sin hardcodear ningún importe.
>
> **Sobre el 003 — por qué se cierra.** Resend está montado (`backend/email_service.py`, envío HTTP directo, nunca lanza excepción si falla). Cuatro correos transaccionales enganchados y con tests: bienvenida + verificación de email al registrarse, reset de contraseña, y aviso de fin de trial (`backend/blueprints/push.py`, vía el job programado). Dominio `tualiado.es` verificado, `EMAIL_FROM=cuadernodigital@...`.
>
> **Sobre el 004 — por qué se cierra.** La pantalla ya está implementada y en producción (`frontend/screens_ayuda.jsx`): guía de inicio de 6 slides con carrusel + swipe, y ayuda contextual `?` en todas las pantallas, cacheada offline. Los slides usan mini-maquetas `<div>`, no los SVG que constaban como "aprobados" (que no están en el repo). Decisión (2026-08-11): se da por hecha con lo que hay; el cambio a SVG es cosmético y solo se retomará si se detecta que la ayuda no se entiende bien en uso real.

> **Sobre el 002 — qué significa exactamente.** Lo que la ley obliga el 01/01/2027 es que el **agricultor** lleve el cuaderno en formato digital e interoperable con SIEX. No obliga a que esta app envíe los datos por API: el titular puede acceder a su CUE y cumplimentarlo él mismo con sus credenciales digitales. El envío automático por IUWS requiere ser *entidad habilitada* (registro, certificado de sello de componente, autorización firmada por cada titular y, al parecer, estatutos que recojan la representación de terceros ante la administración agraria). Esa vía **no se asume de momento** y por tanto no se promete en ningún sitio. Pendiente de confirmar con `reacue@castillalamancha.es` si un titular puede importar en su CUE un fichero generado por una aplicación externa: si la respuesta es que sí, esa es la vía natural para esta app.
>
> **Los 8 bloques están implementados y mergeados en `main` (2026-08-27)**: los datos y catálogos SIEX ya se capturan y guardan en BD. **No se cierra del todo el 002**: queda pendiente reflejarlos en `export_pdf.py`/`exports.py` (decisión deliberada — sin urgencia legal porque el deadline es 01/01/2027) y confirmar con `reacue@castillalamancha.es` la vía de envío/importación real.
>
> **Desglose del 002 en bloques controlables** (auditoría 2026-08-26 contra Anexo VI + catálogos oficiales SIEX, ~74 campos de brecha total). Cada bloque tuvo su spec y su PR independiente, ordenados de menos a más esfuerzo:
>
> | # | Bloque | Campos que faltan | Tipo de trabajo | Estado |
> |---|--------|-------------------|------------------|--------|
> | 018 | Cultivo | 2 | columna simple + código de catálogo en variedad | ✅ Mergeado (PR #65) |
> | 019 | Cosecha / venta | 8 | columnas simples + distinguir venta directa vs comercializada | ✅ Mergeado (PR #67) |
> | 020 | Riego | 9 | columnas simples + 2 catálogos (energía, buenas prácticas) | ✅ Mergeado (PR #68) |
> | 021 | Fertilización | 11 | columnas + catálogo de producto + asesor de fertilización (concepto nuevo) | ✅ Mergeado (PR #69) |
> | 022 | Tratamientos fitosanitarios | 12 | columnas + catálogo + doble validación de asesor (concepto nuevo) | ✅ Mergeado (PR #73) |
> | 023 | Análisis suelo/agua/producto | 9 | módulo nuevo | ✅ Mergeado (PR #74) |
> | 024 | Tratamiento de semillas | 11 | módulo nuevo | ✅ Mergeado (PR #75) |
> | 025 | Post-cosecha | 12 | módulo nuevo | ✅ Mergeado (PR #77) |
>
> Ganadería (razas, especies, UGM) queda fuera: la app es puramente agrícola, confirmado en la auditoría.
>
> **Dos campos bloqueados, no por la app sino por SIEX**: `probFito` (problemática fitosanitaria, bloques 022/025) y el tipo de carné del aplicador (bloque 022) exigen catálogos que el propio Anexo VI marca como "por crear" — SIEX todavía no los ha publicado. `planAbon` en fertilización (021) está igual, marcado "pendiente confirmar" en el documento oficial. Los tres quedan fuera de alcance hasta que SIEX los publique — no es trabajo pendiente nuestro.

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
