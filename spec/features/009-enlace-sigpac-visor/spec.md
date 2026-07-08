# 009 — Enlace "Ver en el mapa" al visor SIGPAC

## Qué construir

Un botón en la ficha de parcela que abre el **visor oficial de SIGPAC** centrado en
la parcela/recinto del agricultor, para que **verifique visualmente que es la suya**.

No es una feature de datos: es una feature de **confianza**. El agricultor no valida
un polígono/recinto leyendo números, pero sí reconoce la forma de su finca en el mapa.

Compatible con SIEX: solo lee campos ya existentes, no toca modelo de datos ni catálogos.

## Contexto validado (2026-07-08)

- Formato de URL confirmado en la ayuda oficial del visor:
  `https://sigpac.mapa.gob.es/fega/visor/?provincia=PR&municipio=MN&agregado=AG&zona=ZN&poligono=PL&parcela=PC&recinto=RC`
- Probado con parcelas **reales de Lourdes** contra el servicio oficial:
  - Torrenueva (cód. SIGPAC 85) 40/146 recinto 1 → resuelve ✅
  - Sta. Cruz de Mudela (cód. 77) 50/75 recinto 2 → resuelve ✅
- El "autodescubrir recinto" (nivel 1 original) **ya está implementado**
  (`/api/sigpac/recintos-detalle` + `recintosPicker` en `screens_parcelas.jsx`) y ya
  maneja el caso recinto ≠ 1. **La única pieza nueva es el botón de mapa.**

## Alcance (solo esto)

- Añadir en la pestaña "Parcela" del detalle (`screens_parcelas.jsx`) un botón
  **"🗺️ Ver mi parcela en el mapa"**.
- Construye la URL con `provincia_cod`, `municipio_cod`, `poligono`, `parcela_num`,
  `recinto` (agregado/zona = 0). Abre en **pestaña nueva** (`target="_blank"`,
  `rel="noopener noreferrer"`).
- Copy que aclare que es la **web oficial del Ministerio** (que el salto no asuste).

## Criterios de aceptación

1. El botón **solo aparece** si la parcela tiene `provincia_cod`, `municipio_cod`,
   `poligono` y `parcela_num`. (El `recinto` es opcional: si falta, la URL lo omite y
   el visor centra en la parcela entera — no debe romper.)
2. Al pulsarlo abre el visor SIGPAC en pestaña nueva, centrado en la parcela.
3. No hay llamadas nuevas al backend: la URL se construye en cliente con datos ya cargados.
4. Mobile-first: botón ≥44px de alto, ancho completo, una columna.

## Fuera de alcance (fases siguientes)

- Nivel 2: verificación masiva "revisa mis parcelas" (recinto inexistente, superficie
  que no cuadra, parcela desaparecida por reparcelación). Ver [[project-enlace-sigpac-visor]].
