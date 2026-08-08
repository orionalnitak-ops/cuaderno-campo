# 014 — Herencia automática del cultivo en parcelas de leñoso

**Estado:** aprobada · **Origen:** reporte de Lourdes (piloto) el 2026-08-07
**Rama base:** `fix/aislamiento-explotacion` (feature 013 toca los mismos archivos)

---

## El problema

Lourdes, con 50+ parcelas, ve en la **Revisión del cuaderno** el aviso *"Sin cultivo
declarado en 2025/2026"* en **todas** sus fincas de olivar y viña, campaña tras campaña.

Su veredicto como usuaria real, confirmado: **ese aviso no debe aparecer nunca en leñoso.**

Un cultivo leñoso (olivar, viñedo, almendro, pistachero, frutales) es **permanente**: se
planta una vez y sigue ahí veinte años. Pedir que se "declare" cada campaña es pedirle que
reescriba a mano un dato que no ha cambiado ni va a cambiar. Con 50 parcelas, eso es la
diferencia entre un cuaderno que se usa y uno que se abandona.

### Dónde está hoy

`backend/blueprints/cumplimiento.py` (bloque `cultivo_campana`) marca como pendiente toda
parcela sin fila en `cultivos_campana` para la campaña activa. No distingue leñoso de
herbáceo, porque el backend no sabe qué cultivos son permanentes.

## Lo que NO se hace, y por qué

**No se suprime el aviso sin más.** El CUE (RD 1311/2012) exige que el cuaderno refleje qué
se cultiva en cada parcela **y en cada campaña**, también en leñosos, y ese dato tiene que
salir en el PDF oficial, en el Excel y en lo que se exporte de forma compatible con SIEX.
Ocultar el aviso dejaría a Lourdes tranquila y al cuaderno incompleto — justo el fallo que
no nos podemos permitir en la parte legal.

## Lo que sí se hace

El cultivo permanente **se hereda solo** de la campaña anterior. Lourdes declara el olivar
una vez; en las campañas siguientes la app copia esa declaración sin pedirle nada y sin
avisar de nada.

El aviso desaparece **porque el dato está**, no porque lo escondamos.

## Cómo se sabe que un cultivo es leñoso

El catálogo `CULTIVOS_IACS` (`frontend/screens_parcelas.jsx`) ya clasifica cada cultivo por
grupo, y tiene un grupo `'Leñosos'` con 12 códigos IACS del Anexo VII FEGA:

`1710` almendro · `1711` viñedo vinificación · `1712` viñedo uva de mesa · `1720`
melocotonero/nectarino · `1730` ciruelo · `1740` pistachero · `1750` higuera · `1760` nogal
· `1770` cerezo/guindo · `1820` olivar · `1830` naranjo · `1840` limonero

No hace falta ningún campo nuevo en la base de datos: el código IACS ya se guarda en
`cultivos_campana.cultivo_iacs_cod` y es obligatorio desde la feature de SIEX.

## Criterios de aceptación

1. Una parcela cuya última declaración conocida es un cultivo leñoso **no aparece** como
   pendiente en el bloque *Cultivo declarado por parcela* de la Revisión.
2. Esa parcela tiene una fila real en `cultivos_campana` para la campaña activa, copiada de
   la anterior (cultivo, código IACS, variedad, superficie cultivada).
3. El PDF oficial y el Excel de la campaña nueva muestran el cultivo en esas parcelas.
4. Una parcela de cultivo **herbáceo** (cereal, girasol, hortaliza) **sigue apareciendo**
   como pendiente: ahí el cultivo sí cambia y declararlo es obligación real del agricultor.
5. La herencia es **idempotente**: ejecutarla dos veces no duplica filas.
6. La herencia **nunca pisa** una declaración existente. Si Lourdes arranca el olivar y
   pone otro cultivo, manda lo que ella escribió.
7. La herencia respeta el aislamiento por explotación (feature 013): no cruza datos entre
   fincas.
8. La fecha de siembra y la de recolección prevista **no se heredan** (son propias de cada
   campaña); sí el cultivo, el código IACS, la variedad y la superficie.

## Fuera de alcance

- Avisar al agricultor de que se ha heredado algo. Es ruido: el objetivo es justamente que
  no tenga que enterarse.
- Arrancar/replantar parcelas (cambiar de leñoso a otra cosa) — eso ya se hace editando el
  cultivo a mano y el criterio 6 lo protege.
