# Mission — Cuaderno de Explotación Digital (CUE)

## Qué construimos

App web SaaS que digitaliza el **Cuaderno de Explotación Agrícola** obligatorio por ley en España (RD 1311/2012). Permite a agricultores registrar y exportar tratamientos fitosanitarios, fertilización, labores, riego, cosecha y compras en formato legalmente válido.

## Para quién

Agricultores de Castilla-La Mancha sin conocimientos informáticos.  
Piloto activo: Lourdes (finca familiar, ~50+ parcelas SIGPAC).

## Obligación legal

- **RD 1311/2012** — cuaderno de explotación obligatorio.
- **Deadline 1 enero 2027** — fitosanitarios digitales obligatorios e interoperables con SIEX (Sistema de Información de Explotaciones, FEGA).
- **Orden APA/204/2023** — campos adicionales obligatorios: asesor, justificación actuación, ROMA, ITEAF.
- **RD 934/2025** — plan de abonado obligatorio desde septiembre 2026.

## Modelo de negocio

SaaS de pago. Trial gratuito → plan de pago vía Stripe.  
URL producción: `https://cuaderno.tualiado.es`

## Lo que NO es

- No es una app de escritorio ni requiere instalación.
- No sustituye al asesor agrícola, lo complementa.
- No envía datos a la administración (de momento) — SIEX es el siguiente hito.
