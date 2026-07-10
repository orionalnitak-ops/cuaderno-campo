# Spec — Aviso multi-recinto → UHC (Bloque 2 #6)

**Fecha:** 2026-07-10
**Estado:** aprobado en brainstorming (pendiente plan de implementación)
**Regla dura:** lenguaje "compatible con SIEX" en toda la UI; nunca "integración/subida a SIEX".

---

## Problema

Una parcela SIGPAC (provincia/municipio/polígono/parcela) puede estar dividida en
varios **recintos**, cada uno con su uso (olivar, tierra arable, pasto…). En la app,
cada fila de `parcelas` representa **un recinto**. Hoy, al dar de alta una parcela
multi-recinto, el picker obliga a elegir **un solo recinto**: el agricultor que quiere
registrar todos tiene que repetir el alta N veces, y después no hay nada que le
sugiera agrupar los recintos del mismo cultivo en una **UHC** (Unidad Homogénea de
Cultivo) para apuntar las faenas una sola vez.

## Objetivo

Al dar de alta una parcela cuyo polígono/parcela tiene **2 o más recintos**, ofrecer
crear **una parcela por recinto** y, para los recintos que compartan uso SIGPAC,
proponer agruparlos en una **UHC por grupo de uso** — con aceptación explícita del
agricultor y explicado en lenguaje llano, sin tecnicismos.

## Decisiones tomadas (brainstorming 2026-07-10)

| Decisión | Elección |
|---|---|
| Disparador | Solo en el **alta** (picker en modo `form` con 2+ recintos). Aviso retroactivo para parcelas existentes → fuera de alcance (#6b futuro). |
| Criterio de agrupación | Una UHC propuesta **por cada grupo de ≥2 recintos con el mismo uso SIGPAC**. Recintos de uso único o sin uso conocido → parcela suelta, sin UHC. |
| UX | **Resumen confirmable** antes de crear nada: tabla de recintos + UHCs propuestas con nombre editable y **aceptación explícita por grupo** (agrupar sí/no). |
| Implementación | **Endpoint transaccional** nuevo: `POST /api/parcelas/alta-multirecinto`. Todo o nada con un único `commit()`. |
| Lenguaje | Explicación en lenguaje llano con el **beneficio práctico** por delante; "trozos" y "grupo" como vocabulario principal, "recinto"/"UHC" entre paréntesis. |

## Flujo de usuario

1. Alta de parcela por SIGPAC → `recintos-detalle` devuelve 2+ recintos.
2. El picker actual muestra, además de la lista de recintos individuales (flujo
   actual intacto), una opción nueva: **"➕ Crear todas (N trozos)"**.
3. Al pulsarla se abre el **resumen confirmable**:
   - Una fila por recinto: nº, uso SIGPAC, superficie (datos ya obtenidos de
     `recintos-detalle`, sin llamadas extra).
   - Sección de agrupación con la explicación en lenguaje llano (ver "Textos UI").
   - Por cada grupo de uso con ≥2 recintos: una tarjeta de UHC propuesta con
     **nombre editable** pre-rellenado (`{Uso} — Pol {pol} Par {par}`) y un control
     claro de **"Sí, agrupar" / "No, dejar sueltas"** (por defecto: agrupar).
4. Botón "Confirmar y crear" → **una sola llamada** al endpoint transaccional →
   toast con el resultado ("Creadas N parcelas y M grupos") y refresh de la lista.
5. Si el usuario elige un recinto individual, el comportamiento es exactamente el
   actual — cero regresión.

## Textos UI (lenguaje llano)

Encabezado de la sección de agrupación en el resumen:

> **¿Juntamos los trozos que se trabajan igual?**
>
> Esta parcela del SIGPAC está dividida en varios trozos (la administración los
> llama "recintos"). Te vamos a crear una parcela por cada trozo.
>
> Los trozos que tienen **el mismo cultivo** puedes juntarlos en un **grupo**.
> **¿Qué ganas con eso?** Que las faenas se apuntan **una sola vez**:
>
> - Si sulfatas el olivar, apuntas el tratamiento **una vez** y queda registrado
>   en los 3 trozos a la vez. Sin grupo, tendrías que apuntarlo 3 veces.
> - Lo mismo con el abonado y las labores: una anotación vale para todo el grupo.
> - Tu cuaderno queda igual de completo y correcto ante una inspección: cada
>   trozo tiene sus datos, solo que tú escribes menos.
>
> A ese grupo la administración lo llama "Unidad Homogénea de Cultivo (UHC)".
> Para ti es, simplemente, un grupo de trozos que se trabajan igual. Tú decides:
> puedes agruparlos ahora o dejarlos sueltos (podrás agruparlos más adelante
> desde la pantalla de Grupos).

Tarjeta por grupo propuesto:

> **Grupo: [input nombre editable]**
> Junta los trozos 1, 2 y 5 (Olivar · 4,2 ha en total)
> ( • Sí, agrupar   ○ No, dejar sueltos )

Principios de todo el copy del flujo (botones, toasts, errores):
- Beneficio práctico antes que definición legal.
- "Trozos" y "grupo" como palabras principales; "recinto" y "UHC" entre
  paréntesis para que la terminología oficial de los papeles PAC le vaya sonando.
- Decir "compatible con SIEX" si se menciona SIEX; nunca "integración/subida".

## Backend — `POST /api/parcelas/alta-multirecinto`

En `backend/blueprints/parcelas.py` (nunca en `app.py`).

**Payload:**

```json
{
  "nombre_base": "La Vega",
  "provincia_cod": "13", "municipio_cod": "034",
  "poligono": "4", "parcela_num": "12",
  "municipio_nombre": "...", "provincia_nombre": "...",
  "recintos": [
    {"num": 1, "uso_sigpac": "OV", "superficie_ha": 1.2},
    {"num": 2, "uso_sigpac": "OV", "superficie_ha": 2.1},
    {"num": 3, "uso_sigpac": "PS", "superficie_ha": 0.8}
  ],
  "uhcs": [
    {"nombre": "Olivar — Pol 4 Par 12", "cultivo": "Olivar", "recintos": [1, 2]}
  ]
}
```

Los `uhcs` que llegan son solo los que el usuario **aceptó** agrupar (los grupos
rechazados no viajan).

**Comportamiento:**

- Validación server-side: nombre base y nombres de UHC no vacíos; lista de
  recintos no vacía y sin números duplicados; cada `uhcs[].recintos` referencia
  números presentes en `recintos`; campaña formato `YYYY/YYYY` (default activa,
  misma que `uhc.py`).
- **Duplicados:** si el usuario ya tiene una parcela activa con ese
  prov/mun/pol/par/recinto → 400 con error legible ("Ya tienes registrado el
  trozo N de esa parcela") y **no se crea nada**.
- Inserta N parcelas (nombre `{nombre_base} — R{num}`), M `unidades_homogeneas`
  y sus `uhc_parcelas`, y hace **un único `conn.commit()`** al final. Si algo
  falla: rollback implícito (no commit), `conn.close()`, error legible.
- Patrones obligatorios del proyecto: `get_db()`/`commit`/`close` sin context
  manager, placeholders `?`, filtrado por `user_id`, sin `INSERT OR REPLACE`
  (compatible PG). `INSERT OR IGNORE` de `uhc_parcelas` sigue el patrón ya usado
  en `uhc.py`.
- Respuesta: `{"ok": true, "data": {"parcelas": N, "uhcs": M}}` /
  `{"ok": false, "error": "mensaje legible"}`.

## Frontend — `frontend/screens_parcelas.jsx`

- El `recintosPicker` en modo `form` ya dispone de los recintos con uso y
  superficie: añadir la opción "Crear todas" solo cuando hay 2+ recintos.
- Nuevo estado/modal `resumenMultirecinto` con la tabla, la explicación, las
  tarjetas de grupo (nombre editable + agrupar sí/no) y el botón de confirmar.
- Mobile-first: una columna, botones ≥44px, texto legible.
- Agrupación de usos: por el código/descripción de `uso_sigpac` tal cual llega de
  `recintos-detalle`; recintos con uso vacío se listan como "Sin uso conocido" y
  nunca generan grupo.
- Tras el alta correcta: cerrar modales, refrescar lista de parcelas, toast.
- **Bump de `CACHE_NAME`** en `service-worker.js` (regla dura del proyecto).

## Casos borde

| Caso | Comportamiento |
|---|---|
| Todos los usos distintos | No se propone ningún grupo; el resumen crea solo las N parcelas y lo dice claramente ("Cada trozo tiene un cultivo distinto, así que no hay nada que agrupar"). |
| Uso desconocido (Catastro falló) | Fila "Sin uso conocido"; parcela suelta, sin grupo. |
| Usuario desmarca todos los grupos | Se crean solo las parcelas; ninguna UHC. |
| Recinto ya registrado por el usuario | 400 legible, nada creado (transacción). |
| `recintos-detalle` falla o devuelve 1 recinto | Flujo actual sin cambios (elegir un recinto). |

## Fuera de alcance (YAGNI)

- Aviso retroactivo para parcelas ya existentes (las ~50 de Lourdes) → #6b futuro.
- Chequeo de "superficies que no cuadran" → ya cubierto por el badge de #5.
- Migrar autorrelleno / `recintos-detalle` a GetFeatureInfo hubcloud → PR aparte
  ya apuntado como pendiente.
- Deshacer/editar el lote creado → se gestiona con el CRUD normal de parcelas y UHC.

## Testing

- Prueba manual local: alta con una parcela multi-recinto real (finca de Lourdes),
  verificando resumen, edición de nombre, rechazo de un grupo y creación final.
- Regresión: alta mono-recinto y elección individual en el picker siguen igual.
- Backend: probar duplicado (400, nada creado) y payload inválido.

## Convención de entrega

Una pieza = un PR. Rama `feat/aviso-multirecinto-uhc` → PR → CI (lint + bandit) →
security review → merge a `main` → deploy automático EasyPanel (restart completo
si se toca `db.py`/`exports.py` — en principio no se tocan).
