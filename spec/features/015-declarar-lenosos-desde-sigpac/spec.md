# 015 — Declarar los leñosos a partir del uso SIGPAC

**Estado:** pendiente de aprobar · **Origen:** reporte de Lourdes (piloto) el 2026-08-07

---

## El problema, con los números reales

Lourdes tiene **23 parcelas de cultivo leñoso y ninguna con el cultivo declarado**. Las
23 le salen marcadas en la Revisión del cuaderno como *"Sin cultivo declarado"*.

| Uso SIGPAC | Parcelas | Con cultivo declarado |
|---|---|---|
| OV - Olivar | 18 | 0 |
| VI - Viñedo | 3 | 0 |
| VO - Viñedo-Olivar | 1 | 0 |
| FY - Frutales | 1 | 0 |

Ella sabe que esas parcelas son olivar porque **lo dice SIGPAC**, que es el registro
oficial. La app tiene ese dato guardado en `parcelas.uso_sigpac` desde que se dio de alta
la parcela, y aun así le pide que lo teclee a mano, parcela por parcela.

## Por qué no lo resuelve la feature 014

La 014 hereda el cultivo leñoso de la campaña anterior. Con los datos reales de Lourdes
no hace nada: solo existe **una campaña** (2025/2026) y **ningún leñoso declarado**, así
que no hay nada de donde heredar. La 014 evita que el problema vuelva; la 015 es la que
lo resuelve hoy.

## Qué se hace

Proponerle la declaración ya hecha a partir de SIGPAC, y que ella solo **confirme**.

- **OV → Olivar (IACS 1820).** Sin ambigüedad: 18 parcelas resueltas con un botón.
- **VI, VO y FY → hay que preguntar**, una vez por grupo, no parcela por parcela.

## Lo que se pregunta, y por qué es obligatorio

Aplicando la regla de no pedir nada que la ley no exija, **los tres casos que quedan son
obligatorios**, no comodidad nuestra:

- **Viñedo (VI):** el cuaderno trata la *viña de vinificación* como producto propio, con
  datos de destino de la producción y clasificación de la categoría que la uva de mesa no
  lleva. Por eso IACS separa 1711 (vinificación) de 1712 (uva de mesa) y hay que saber
  cuál es. Se pregunta **una vez** y se aplica a las 3.
- **Frutales (FY):** "frutales" no es una especie. IACS pide melocotonero (1720), ciruelo
  (1730), cerezo (1770), nogal (1760)… El código es obligatorio para SIEX.
- **Viñedo-Olivar (VO):** son dos cultivos en un mismo recinto. El cuaderno se lleva por
  cultivo, así que hay que repartir la superficie entre los dos.

## Criterios de aceptación

1. Con parcelas de leñoso sin declarar en la campaña activa, la app ofrece resolverlas en
   bloque, diciendo cuántas son y qué cultivo propone para cada grupo.
2. Confirmar crea filas reales en `cultivos_campana` con su código IACS: el dato existe
   para el PDF oficial y para SIEX, no se oculta el aviso.
3. Las parcelas OV se proponen como Olivar (1820) sin preguntar nada más.
4. VI, VO y FY **no se declaran solas**: se pregunta y, hasta que se responda, siguen
   contando como pendientes. Nunca se adivina un cultivo en un documento legal.
5. Nada se escribe sin confirmación explícita del agricultor.
6. Nunca pisa una declaración existente.
7. Respeta el aislamiento por explotación (feature 013).
8. La superficie cultivada se propone igual a la de la parcela, y es editable.

## Fuera de alcance

- Adivinar la especie de un frutal o el tipo de viñedo. Si no se sabe, se pregunta.
- Tocar las parcelas de tierra arable (TA): ahí el cultivo cambia cada campaña y
  declararlo es obligación real del agricultor.

## Respuestas de Lourdes (2026-08-08)

Ya contestadas. Sirven para probar con datos de verdad; la app se las seguirá preguntando
a cualquier otro agricultor, porque no se pueden adivinar.

| Grupo | Parcelas | Respuesta | Código IACS |
|---|---|---|---|
| VI - Viñedo | 3 | Viñedo de **vinificación** | `1711` |
| FY - Frutales | 1 | **Almendros** | `1710` |
| VO - Viñedo-Olivar | 1 | **80 % viñedo de vinificación, 20 % olivar** | `1711` + `1820` |

La parcela mixta genera **dos filas** en `cultivos_campana`, una por cultivo, repartiendo
la superficie. Encaja con la validación que ya existe en el POST de `/api/cultivos-campana`
(la suma de superficies declaradas no puede pasar de la superficie de la parcela).

Con esto, las 23 parcelas de leñoso de Lourdes quedan resueltas: 18 olivar, 4 viñedo de
vinificación (3 + la parte de la mixta), 1 almendro y la parte de olivar de la mixta.
