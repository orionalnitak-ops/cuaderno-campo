# Diseño — Badge "✓ Verificado con SIGPAC" (Bloque 2, #5)

**Fecha:** 2026-07-10
**Estado:** Aprobado por el usuario, pendiente de plan de implementación
**Rama:** `feat/badge-verificado-sigpac`

## Contexto

Tercera pieza del Bloque 2 de mejoras SIGPAC (tras #4 capas en el mapa, PR #18).
Da al agricultor una señal visible de si la superficie que declaró para cada
parcela coincide con la que consta en SIGPAC. Muchos agricultores teclean la
superficie a mano al dar de alta la parcela; una diferencia real puede tener
impacto en la declaración PAC y en el cálculo de dosis de fitosanitarios por ha.

## Decisiones tomadas (brainstorming)

- **Qué se contrasta:** solo **superficie (ha)**. No municipio, no uso (evita el
  gotcha INE vs código SIGPAC y mantiene el badge simple).
- **Umbral:** **±5%** de diferencia entre superficie guardada y superficie SIGPAC.
- **Cuándo se verifica:** al guardar (crear/editar) la parcela **+ botón manual
  "↻ Re-verificar"**. El resultado se **persiste en BD**; el badge se muestra al
  instante, funciona offline y no machaca a FEGA en cada apertura de ficha.
- **Dónde aparece:** **lista + ficha**. Pill compacto en cada tarjeta de la lista;
  badge con detalle (+ botón re-verificar) dentro de la ficha.
- **Fuente de superficie:** el nuevo **GeoServer "SIGPAC en la Nube"**
  (`sigpac-hubcloud.es`) vía **GetFeatureInfo**, que devuelve `superficie_ha`
  oficial directa (además de uso, pendiente, etc.). Sustituye a la fuente actual
  (`serviciosvisor/intersection` + roundtrip al Catastro) **solo para este flujo**;
  migrar el autorrelleno del formulario a la misma fuente es un PR posterior.

## Modelo de datos

Dos columnas nuevas en la tabla `parcelas`, añadidas con `_add_col()` en
`init_db()` (aditivas, no rompen compatibilidad SIEX):

| Columna | Tipo | Significado |
|---|---|---|
| `sigpac_superficie_ha` | REAL (nullable) | Superficie que devolvió SIGPAC en la última verificación. `NULL` = nunca verificada o no encontrada. |
| `sigpac_verificado_en` | TEXT (nullable) | Timestamp ISO-8601 de la última verificación. `NULL` = nunca verificada. |

No se añade una columna de "estado": el estado se **deriva** al leer (ver abajo),
así el badge se recalcula solo si el agricultor edita la superficie sin re-verificar.

## Estados del badge (derivados)

Se calculan en el backend a partir de `superficie_ha` (declarada), `sigpac_superficie_ha`
y `sigpac_verificado_en`, y se devuelven como campo `sigpac_estado` en cada parcela:

| `sigpac_estado` | Condición | Badge (texto) |
|---|---|---|
| `verde` | verificado, SIGPAC con superficie, `|decl − sigpac| / sigpac ≤ 0.05` | ✓ Verificado |
| `ambar` | verificado, SIGPAC con superficie, diferencia > 5% | ⚠ Revisar superficie |
| `no_encontrada` | verificado (`sigpac_verificado_en` no nulo) pero `sigpac_superficie_ha` nulo | ⚠ No está en SIGPAC |
| `sin_verificar` | `sigpac_verificado_en` nulo | (pill gris neutro) "Sin verificar" |

`diferencia_pct` = `round((decl − sigpac) / sigpac * 100, 1)` (con signo), para el
texto de la ficha (p. ej. "+2%", "−8%").

## Fuente de superficie — helper `_sigpac_superficie_recinto`

Nuevo helper en `blueprints/sigpac.py` (reutilizable por el endpoint de verificación):

1. **Enumerar recintos:** `GET serviciosvisor/query/recintos/{prov}/{mun}/0/0/{pol}/{par}`
   → devuelve un feature por recinto con `nombre` (nº de recinto) y bbox `x1,y1,x2,y2`
   (CRS EPSG:4258, lon/lat). Ya se usa hoy para contar recintos.
2. **Superficie por recinto:** para el recinto objetivo, **GetFeatureInfo** en hubcloud
   en el **centro del bbox de ese recinto**:
   ```
   GET https://sigpac-hubcloud.es/wms/ows
       ?service=WMS&version=1.1.1&request=GetFeatureInfo
       &layers=AU.Sigpac:recinto&query_layers=AU.Sigpac:recinto
       &info_format=application/json
       &srs=EPSG:4258&bbox={bbox_recinto}&width=256&height=256&x=128&y=128
       &feature_count=5&styles=
       &CQL_FILTER=provincia={p} AND municipio={m} AND poligono={pol}
                   AND parcela={par} AND recinto={rec}
   ```
   Se lee `features[0].properties.superficie_ha` (ya viene en hectáreas).
   El `CQL_FILTER` por número de recinto actúa como salvaguarda para no coger un
   recinto vecino que caiga bajo el píxel.
3. **Selección de recinto:**
   - Si `parcela.recinto` está informado → superficie de **ese** recinto.
   - Si `parcela.recinto` está vacío → **suma** de la `superficie_ha` de todos los
     recintos del pol/par (superficie total de la parcela).
4. **Robustez:** usa el helper `_sigpac_get` existente (reintento + timeout). Si
   SIGPAC/FEGA falla o no hay recintos, devuelve `None` (→ estado `no_encontrada`
   si el pol/par no resuelve, o el endpoint informa fallo transitorio sin persistir).

> Nota de red: GetFeatureInfo requiere consultar el centro del bbox de **cada**
> recinto (es por-píxel; `CQL_FILTER` filtra pero no localiza). Coste equivalente
> al flujo actual (una llamada de intersección por recinto), pero con dato oficial
> directo y sin roundtrip al Catastro.

## Endpoint de verificación

`POST /api/parcelas/<int:pid>/verificar-sigpac` (login_required, rate-limit acorde
al resto de rutas SIGPAC, p. ej. `60 per minute`):

1. Carga la parcela (`user_id = current_user.id`); 404 si no es del usuario.
2. Valida prov/mun/pol/par con `_sigpac_param` (solo dígitos).
3. Llama al helper → `sigpac_ha` (float) o `None`.
4. Persiste:
   - éxito: `sigpac_superficie_ha = sigpac_ha`, `sigpac_verificado_en = now()`.
   - pol/par no resuelve en SIGPAC: `sigpac_superficie_ha = NULL`,
     `sigpac_verificado_en = now()` → estado `no_encontrada`.
   - fallo transitorio de FEGA (timeout/502): **no persiste**, responde
     `{ "ok": false, "error": "SIGPAC no disponible, inténtalo de nuevo" }` (HTTP 503)
     para que el badge conserve el último valor bueno.
5. Respuesta éxito: `{ "ok": true, "estado", "sigpac_superficie_ha", "diferencia_pct" }`.

Sigue el patrón BD del proyecto: `get_db()` → operar → `commit()` → `close()`
(sin context manager). Placeholders `?`.

## Lectura de parcelas (lista y ficha)

`GET /api/parcelas` y `GET /api/parcelas/<id>` incluyen en cada parcela:
- `sigpac_superficie_ha` (crudo, para el detalle de la ficha)
- `sigpac_verificado_en`
- `sigpac_estado` (derivado, calculado con un helper puro `_estado_sigpac(parcela)`)
- `sigpac_diferencia_pct` (derivado)

El helper de derivación vive en el backend (fuente única de verdad); el frontend
solo pinta. El cálculo es puro (sin I/O) → testeable de forma aislada.

## Frontend

### Lista (`screens_parcelas.jsx`, tarjeta de parcela)
- Pill compacto por tarjeta según `sigpac_estado`:
  - `verde` → fondo verde, "✓ SIGPAC"
  - `ambar` → fondo ámbar, "⚠ Revisar"
  - `no_encontrada` → fondo ámbar, "⚠ No en SIGPAC"
  - `sin_verificar` → gris tenue, "Sin verificar"
- Táctil ≥ 44px donde sea interactivo; el pill en sí es informativo (no botón).

### Ficha (detalle de parcela)
- Badge grande con el mismo estado.
- Línea de detalle cuando hay dato SIGPAC:
  "SIGPAC: 10,2 ha · tu dato: 10 ha (+2%)".
- Botón **"↻ Re-verificar"** → `POST …/verificar-sigpac`; muestra spinner, y al
  volver refresca badge y detalle. Deshabilitado sin conexión con tooltip
  "Necesitas conexión para verificar con SIGPAC".

### Auto-verificación al guardar
- Tras crear o editar una parcela con éxito, el frontend llama una vez a
  `verificar-sigpac` para esa parcela (fire-and-forget con refresco al volver).
  No bloquea el guardado: si falla, la parcela queda `sin_verificar` y el
  agricultor puede re-verificar luego.

### Offline (PWA)
- Los campos `sigpac_*` viajan con la parcela en IndexedDB → el badge se ve igual
  sin conexión (valor persistido).
- Botón re-verificar deshabilitado offline.
- Bump `CACHE_NAME` del service worker (a un valor **mayor** que el de `main` en el
  momento del merge; `main`=v31, el PR #18 lo lleva a v32 → este usará **v33**).

## Compatibilidad SIEX

Cambios aditivos (2 columnas nuevas, catálogos y códigos SIGPAC oficiales de FEGA).
No se modifica el modelo de datos existente ni las exportaciones. Lenguaje UI:
"compatible con SIEX", nunca "integración/subida".

## Fuera de alcance (YAGNI / otros PRs)

- Migrar el **autorrelleno del formulario** (`sigpac_datos`) y `recintos-detalle`
  a la fuente hubcloud GetFeatureInfo (PR posterior; misma técnica).
- Contrastar **uso SIGPAC** o **municipio** en el badge.
- Aviso **multi-recinto → UHC** (pieza #6 del Bloque 2).
- Guardar uso/pendiente/incidencias de SIGPAC (aunque la fuente los ofrezca).

## Verificación (sin tests formales en el proyecto)

Validación manual en navegador local:
1. Parcela con superficie correcta → tras guardar, badge **verde**.
2. Parcela con superficie alterada > 5% → badge **ámbar** con diferencia.
3. Pol/par inexistente → **no_encontrada**.
4. Parcela creada offline → **sin_verificar**; botón deshabilitado; al reconectar y
   pulsar re-verificar → estado correcto.
5. El helper puro `_estado_sigpac` se puede probar aislado con valores de ejemplo.
