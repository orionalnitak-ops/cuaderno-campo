# 017 — El límite de explotaciones se aplica de verdad

## El problema

Lo único que diferencia el plan Básico del Pro es el número de explotaciones
(decisión del 2026-08-05). Pero ese límite **solo se comprueba al crear una
finca nueva** (`explotacion.py:83`). En ningún otro sitio.

Consecuencia: quien tenga 5 fincas con Pro y baje a Básico en el portal de
Stripe sigue anotando en las 5. Paga la mitad y usa lo mismo. Es la única
diferencia entre los dos planes y no se sostiene.

**Alcance real hoy:** ninguna cuenta incumple (verificado sobre la copia de
producción del 2026-08-08: las dos cuentas Básico tienen una finca cada una).
Esto se arregla antes de cobrar de verdad, no después.

## Qué NO es este problema

Un plan **caducado** ya bloquea toda escritura por el guard. Ahí el límite es
irrelevante. El único caso que importa es un plan de pago **activo** cuyo tope
es menor que el número de fincas que tiene. Se llega ahí de dos formas, las dos
voluntarias: bajando de Pro a Básico en el portal, o concediendo un plan a mano
desde el panel de admin.

## La regla

**Leer nunca se toca.** El agricultor consulta sus fincas todas, siempre. Este
límite no esconde ni una parcela: lo único que decide es dónde puede *anotar*.

(Aparte, y sin relación con este límite: hoy el PDF y el Excel oficiales exigen
plan activo — `@requires_active_plan` en `imports_exports.py`. Es una decisión
pendiente de revisar, documentada en `test_las_exportaciones_exigen_plan_activo`,
y no se toca en esta feature.)

**Escribir se limita al número de fincas de su plan, y elige él cuáles.**

- El agricultor marca qué explotación es la **principal**. Con Básico, esa es
  en la que puede anotar; las demás quedan en solo lectura.
- Con Pro (tope 5) y 6 fincas, las 5 primeras por `orden, id` son escribibles.
  Reordenar es lo que le deja elegir.
- Si nunca ha elegido, vale la primera por `orden, id`: nadie se queda sin
  ninguna finca escribible por no haber tocado un ajuste.

**Nadie se encuentra un corte por sorpresa, y no hace falta nada especial para
conseguirlo.** Se pensó en un periodo de gracia para las cuentas que ya
incumplieran al desplegar, hasta que se comprobó sobre la copia de producción
del 2026-08-08 que **no hay ninguna**: las dos cuentas Básico tienen una finca
cada una. Y al único sitio donde se llega después es bajando de plan a
propósito, donde recibir el tope que acabas de comprar no es una sorpresa.

Construir el estado de "ha elegido o no" habría costado una columna nueva
—`orden = 0` no vale como marca: ya aparece solo, es la primera finca de cada
usuario— para proteger a cero agricultores de una situación que solo provocan
ellos mismos. No se hace.

## Criterios de aceptación

1. Un Básico con 1 finca no nota absolutamente nada. (El caso de todos hoy.)
2. Un Básico con 3 fincas puede **leer y exportar las 3**.
3. Un Básico con 3 fincas anota en la principal y recibe 403 al intentar
   anotar en las otras dos, con un mensaje que dice qué pasa y cómo se
   arregla — no un `subscription_required` pelado.
4. Cambiar cuál es la principal se hace desde la app, en un toque, y surte
   efecto al momento.
5. Marcar una finca como principal **nunca** se bloquea por este límite: si lo
   hiciera, quien baja de plan se quedaría encerrado sin poder elegir.
6. Pro con 5 o menos fincas: sin cambios.
7. Admin, `premium` y `unlimited_explotaciones`: sin tope, sin cambios.
8. Un plan **caducado** sigue comportándose como hasta ahora: todo bloqueado
   por el guard, esta regla no se mete por medio ni cambia el mensaje.

## Qué no entra

- No se crea ninguna columna nueva: "principal" es `orden = 0`, sobre la
  columna `orden` que ya existe.
- No se borra ni se archiva ninguna finca. Jamás.
- No se toca el precio ni la pantalla de planes.
