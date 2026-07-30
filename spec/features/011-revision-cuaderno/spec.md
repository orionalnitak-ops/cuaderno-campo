# Diseño: Revisión del cuaderno (semáforo de cumplimiento)

**Estado:** aprobado
**Origen:** pregunta de posicionamiento (julio 2026) — existe `SGA_CEX`, la herramienta **gratuita** del MAPA para el CUE, y varias aplicaciones autonómicas también gratuitas. ¿Por qué pagaría un agricultor por esta app?

**Motivación:** competir en "cumplo la ley" es competir donde la Administración es imbatible: eso lo regala. El hueco real es otro.

El agricultor rellena el cuaderno porque le obligan, pero **mientras lo rellena nunca sabe si lo está haciendo bien**. Se entera el día que aparece el inspector, y entonces ya no hay arreglo. Ninguna de las herramientas gratuitas le quita ese miedo: recogen datos y se callan.

> **La herramienta gratuita te deja cumplir. Esta te dice si estás cumpliendo.**

**Restricción dura que define el diseño: cero fricción añadida.** Ni un campo nuevo en los formularios, ni un dato más que recordar. Todo se **deriva de lo que el agricultor ya anotó**. La pantalla solo lee: es un espejo, no un formulario.

---

## Alcance

### Incluido

- Pantalla nueva de solo lectura **«Revisión del cuaderno»** (id interno `cumplimiento`): porcentaje, color y lista concreta de lo que falta, con botón «Arreglar ahora» que lleva al sitio exacto.
- Endpoint `GET /api/cumplimiento` en blueprint propio. No escribe nada en base de datos.
- **Cuatro comprobaciones nuevas**, todas derivadas de datos ya guardados:
  - `iteaf` — inspección del equipo caducada o próxima a caducar.
  - `trazabilidad_compras` — producto aplicado del que no consta compra.
  - `ropo` — falta el nº ROPO de aplicador o asesor.
  - `roma` — equipo sin nº de registro ROMA.
- **Tres comprobaciones ya existentes**, recalculadas al momento: `cultivo_campana` (puntúa), `plazo_seguridad` y `registro_reciente` (informativas).
- Tarjeta de estado en la pantalla de Inicio como puerta de entrada.
- Entrada en `HELP_SCREENS`.

### No incluido

- **Validar el producto contra el registro oficial de fitosanitarios** (que esté autorizado para ese cultivo). Sería la comprobación más potente, pero obliga a descargar y mantener un catálogo externo que cambia constantemente. Es justo la complejidad que esta feature no quiere. Diferido.
- **Comparar cantidades** compradas contra aplicadas. `compras` guarda kg/L totales y `tratamientos` guarda dosis en L/ha sin superficie tratada: habría que multiplicar por superficie y convertir unidades. Los falsos positivos erosionarían la confianza en toda la pantalla. El cruce es **solo cualitativo**.
- Refactor de `_generar_alertas` en `ia.py` (ver decisión 5).
- Notificaciones push del semáforo.
- Cualquier promesa de envío o subida a SIEX. La app es **compatible con SIEX**; esta pantalla no cambia eso.

---

## Decisiones de diseño

### 1. El porcentaje es una media ponderada parcial sobre comprobaciones aplicables

```
si universo == 0  →  bloque "no_aplica", fuera del denominador
si no             →  puntos = peso * (1 - afectados / universo)
porcentaje        =  round(100 * Σ puntos / Σ pesos)
```

Tres propiedades que lo hacen defendible y no arbitrario:

- **El peso es exposición sancionadora, no gusto.** Cada peso se justifica con la norma en el campo `por_que`, que se le enseña al usuario. Si cambia la norma, cambia una constante.
- **Parcial, no binario.** Arreglar 2 de 3 problemas mueve la aguja. Con un semáforo binario, arreglar la mayoría no cambiaría nada y el agricultor dejaría de usar la pantalla.
- **Denominador dinámico.** Quien no tiene equipos no puede tener la ITEAF caducada, así que ese bloque sale del denominador. Sin esto, un agricultor de secano sin atomizador tendría techo del 60 % hiciera lo que hiciera, y el número sería mentira.

| bloque | peso | norma |
|---|---|---|
| `iteaf` | 4 | RD 1702/2011 |
| `trazabilidad_compras` | 4 | RD 1311/2012 Anexo III S5 |
| `roma` | 3 | RD 1702/2011 |
| `ropo` | 3 | RD 1311/2012 art. 12 + Orden APA/204/2023 |
| `cultivo_campana` | 2 | cultivo por parcela y campaña |
| `plazo_seguridad`, `registro_reciente` | **0** | informativos |

### 2. El plazo de seguridad y los «30 días sin registrar» NO puntúan

Se muestran en una sección aparte, «Avisos operativos (no cuentan en el porcentaje)».

**Motivo:** un plazo de seguridad que vence en cinco días **no es un defecto, es información**. Si restara, el porcentaje empeoraría justo cuando el agricultor acaba de hacer las cosas bien. Y los 30 días sin registrar son criterio nuestro, no obligación legal: en verano casi todas las parcelas los superan de forma perfectamente legal, y hundirían el número con ruido.

Así el porcentaje significa exactamente una cosa: **documentación exigible**.

### 3. El color mide gravedad; el porcentaje mide cuánto falta

```
rojo    si hay al menos un hallazgo crítico
verde   si no hay críticos y pct >= 90
naranja en el resto
```

Son **dos ejes distintos, a propósito**. Rojo significa *«tienes algo que te puede costar una sanción»*, no *«te faltan muchas cosas»*.

Atar el rojo al porcentaje producía un semáforo que se contradecía a sí mismo: al probarlo con datos reales salía **25 % en rojo mientras la propia pantalla decía «importantes: 0»**. Un cuaderno a medio rellenar sin ningún incumplimiento grave es naranja; el número ya dice cuánto queda.

En la otra dirección la garantía se mantiene y se refuerza: una ITEAF caducada pone el semáforo en rojo por sí sola, por alto que sea el porcentaje.

### 4. El cruce compras↔tratamientos se apaga si no hay compras

Si el usuario tiene **0 compras registradas**, el bloque es `no_aplica` y sale del denominador, con el mensaje *«Aún no usas el módulo de compras.»*

**Motivo:** sin esta salvaguarda, quien no use ese módulo abre la pantalla y ve el 100 % de sus productos en rojo el primer día. La comprobación sería ruido puro, el semáforo saldría rojo de entrada y el agricultor no volvería. **Es el mayor riesgo de adopción de la feature.**

Por el mismo motivo, el copy dice siempre **«no consta la compra»**, nunca «no compraste».

### 5. No se toca `_generar_alertas` de `ia.py`

Las tres comprobaciones existentes se reimplementan agregadas en el motor nuevo en vez de extraerse de `ia.py`.

**Motivo:** `_generar_alertas` se invoca en un solo sitio de toda la app, dentro del login y envuelto en `try/except: pass` ([auth.py:36-40](../../../backend/blueprints/auth.py)). Una regresión ahí **no produce ningún error visible**: simplemente dejarían de generarse alertas para todos los usuarios y nadie se enteraría. Es el peor sitio del repo para refactorizar por elegancia.

Además, lo que se reutilizaría no es el SQL: el generador recorre parcelas y escribe una fila por parcela; el semáforo agrega con `GROUP BY` y no escribe nada.

Lo que sí puede divergir y causar incoherencia visible son los **umbrales** (30 y 7 días), así que se definen una sola vez en `cumplimiento.py` y `ia.py` los importa.

### 6. Número de consultas constante, independiente del número de parcelas

`_generar_alertas` hace `1 + 3·N` consultas. Con las 50+ parcelas del piloto son ~151 consultas síncronas dentro del login. **Ese patrón no se replica.**

El motor hace **11 consultas fijas** y cruza en Python con sets y diccionarios. Hay un test de regresión que compara el número de consultas con 3 parcelas y con 60.

### 7. La normalización de productos va en Python, nunca en SQL

`UPPER()` en SQLite solo mayusculiza ASCII; en PostgreSQL es Unicode. `UPPER('Añejo')` daría resultados distintos en local y en producción — un bug que solo aparecería con datos reales acentuados y sería casi imposible de reproducir.

`_norm()` normaliza en Python: quita acentos y todo lo que no sea alfanumérico. `'Nº 25.123/HA '` y `'25123-ha'` son el mismo producto.

Emparejamiento, en este orden: **1)** por `num_registro_mapa` normalizado si existe (identificador fuerte, común a las dos tablas); **2)** si no, por nombre comercial normalizado.

### 8. Los registros con campaña vacía cuentan en la campaña activa

`tratamientos.campana` tiene `DEFAULT '2025/2026'`, es editable y se añadió vía `_add_col`, así que hay registros antiguos con `NULL`. Filtrar `campana = ?` a secas los sacaría del universo e **inflaría el porcentaje** — el peor tipo de error aquí, porque falla hacia el lado optimista.

Se usa `COALESCE(NULLIF(TRIM(campana), ''), ?) = ?`, ANSI y válido en ambos motores.

### 9. Un equipo que ya no se usa avisa, pero no es crítico

`equipos` no tiene `activo` ni `deleted_at`: el borrado es duro y borrarlo rompería las referencias `tratamientos.equipo_id`. Un tractor vendido en 2021 con la ITEAF caducada quedaría en rojo para siempre y el agricultor **no podría arreglarlo**.

Regla: severidad `critico` solo si el equipo aparece en ≥1 tratamiento de la campaña. Si no, se degrada a `aviso` con el detalle *«No lo has usado esta campaña. Si ya no lo tienes, bórralo en Ajustes → Equipos.»* Misma regla para las personas sin ROPO.

### 9b. Un equipo de plantilla que nadie tocó no cuenta

`_seed_if_needed()` en `db.py` crea tres equipos al dar de alta la cuenta, del tipo *«Pulverizador terrestre (completar marca y modelo)»*. Al probar con datos reales, **una sola de esas filas se llevaba 7 de los 16 puntos** (falla ITEAF y ROMA a la vez) y era la causa principal de que el semáforo saliera rojo en un cuaderno sin ningún incumplimiento.

Regla: un equipo **sin ROMA, sin fecha ITEAF y que no aparece en ningún tratamiento jamás** es indistinguible de una plantilla sin rellenar y queda fuera del universo.

Se autocorrige: basta con anotar el ROMA, la fecha ITEAF **o** usarlo una vez —aunque sea de una campaña anterior— para que vuelva a contar. Y el riesgo de silenciar un equipo real está cubierto donde importa: el POST de tratamientos ya bloquea usar un equipo sin ROMA.

### 10. La pantalla lleva un descargo de responsabilidad

Una pantalla que dice «estás listo para una inspección» es una promesa. El descargo — *«Orientativo. No sustituye a la revisión oficial de un inspector.»* — va en el JSON, bajo el semáforo y en la ayuda. No es decorativo.

### 11. Periodicidad ITEAF derivada, sin campo nuevo

La app guarda `equipos.fecha_iteaf` y nada más. El vencimiento se calcula con `ITEAF_PERIODICIDAD_ANIOS = 3` (RD 1702/2011, vigente tras 2020).

Limitaciones asumidas y documentadas: no se modela la excepción de "equipo nuevo, primera inspección a los 5 años" (no se guarda fecha de compra), y los equipos exentos (mochilas, equipos manuales) se detectan por palabra clave sobre `tipo` y `descripcion`, que son texto libre — *best effort*. Excluir de más genera falsos negativos silenciosos; incluir de más genera falsos positivos que el usuario no puede limpiar, que es peor para la confianza.

`fecha_iteaf` no se valida en el backend, así que el parseo es tolerante: acepta ISO, repara `DD/MM/YYYY`, y ante un valor vacío o ilegible devuelve un **aviso**, nunca «caducada» — afirmar que está caducada cuando no lo sabemos sería falso.

---

## Criterios de aceptación

- [ ] La pantalla no pide **ningún** dato nuevo al agricultor: no hay formulario ni campo nuevo en ningún módulo.
- [ ] Abro «Revisión del cuaderno» y veo un porcentaje, un color y la lista de lo que me falta.
- [ ] Cada punto de la lista explica **por qué** importa, citando la norma, y qué hacer.
- [ ] «Arreglar ahora» me lleva a la sección exacta donde se corrige, no a la portada de Ajustes.
- [ ] Un equipo con la ITEAF caducada sale como crítico si lo he usado esta campaña, y como aviso si no.
- [ ] Un producto aplicado sin compra registrada aparece listado, con el texto «no consta la compra».
- [ ] Si no tengo ninguna compra registrada, ese bloque sale como «no aplica» y **el porcentaje no baja**.
- [ ] Si no tengo equipos, los bloques de ITEAF y ROMA salen como «no aplica» y no lastran el porcentaje.
- [ ] Con un fallo crítico el semáforo **nunca** sale verde, por alto que sea el porcentaje.
- [ ] El plazo de seguridad y los avisos de registro aparecen en su sección, marcados como que no puntúan.
- [ ] La pantalla muestra el descargo de que es orientativa.
- [ ] Los datos de otro agricultor no aparecen jamás: ni en los recuentos, ni en las listas.
- [ ] El número de consultas a la base de datos no crece con el número de parcelas.
- [ ] La pantalla de ayuda documenta qué es el semáforo y cómo se calcula.
