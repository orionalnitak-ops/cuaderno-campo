# Spec: Asistente IA Estadístico

**Fecha:** 2026-06-12  
**Estado:** Aprobado por usuario — pendiente de implementar  
**Enfoque elegido:** B — Patrones pre-calculados

---

## Objetivo

Añadir un asistente de IA estadístico que ayude al agricultor (>45 años, poca experiencia digital) a rellenar formularios más rápido y recibir recordatorios sin tener que pensar en ellos. La app sugiere, el agricultor siempre decide.

---

## Principios

- La app **sugiere**, nunca obliga. El agricultor puede ignorar cualquier sugerencia.
- Si no hay historial suficiente, el formulario aparece vacío como siempre.
- El agricultor no necesita saber que existe IA — simplemente los formularios vienen más llenos.
- **Coste cero** — todo es SQL + Python en infraestructura existente. Sin llamadas a APIs externas.
- Diseñado para ser ampliable a LLM en el futuro (solo cambia quién escribe en `ia_patrones`).

---

## Alcance

**Incluye:**
- Prerrellenado estacional en formularios de todos los módulos
- Tarjetas de recordatorio en pantalla de inicio
- Registro de feedback (aceptada / ignorada / modificada)

**No incluye (por ahora):**
- LLM / Claude API
- Resúmenes de campaña
- Panel de administrador de sugerencias

---

## Base de datos — 3 tablas nuevas

### `ia_patrones`

Sugerencias pre-calculadas. Una fila = valor más frecuente para un campo en un módulo + parcela + temporada.

```sql
CREATE TABLE ia_patrones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id),
    modulo          TEXT NOT NULL,  -- tratamientos|fertilizacion|riego|labores|cosecha|compras|cultivo_campana
    parcela_id      INTEGER REFERENCES parcelas(id),  -- NULL si el módulo no tiene parcela
    temporada       TEXT NOT NULL,  -- primavera|verano|otono|invierno
    campo           TEXT NOT NULL,
    valor_sugerido  TEXT NOT NULL,
    frecuencia      INTEGER NOT NULL DEFAULT 1,
    ultima_vez      DATE,
    actualizado_en  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(usuario_id, modulo, parcela_id, temporada, campo)
);
```

### `ia_alertas`

Recordatorios para la pantalla de inicio.

```sql
CREATE TABLE ia_alertas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    tipo        TEXT NOT NULL,  -- sin_registro_reciente|plazo_seguridad_proximo|sin_cultivo_campana
    parcela_id  INTEGER REFERENCES parcelas(id),
    modulo      TEXT,
    mensaje     TEXT NOT NULL,
    leida       BOOLEAN DEFAULT 0,
    creada_en   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expira_en   TIMESTAMP
);
```

### `ia_feedback`

Registra si el agricultor aceptó, ignoró o modificó cada sugerencia.

```sql
CREATE TABLE ia_feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    patron_id   INTEGER NOT NULL REFERENCES ia_patrones(id),
    accion      TEXT NOT NULL,  -- aceptada|ignorada|modificada
    valor_final TEXT,           -- valor real usado si accion=modificada
    creado_en   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Lógica de temporadas

```python
def _temporada(fecha):
    mes = fecha.month
    if mes in (3, 4, 5):   return 'primavera'
    if mes in (6, 7, 8):   return 'verano'
    if mes in (9, 10, 11): return 'otono'
    return 'invierno'  # 12, 1, 2
```

---

## Backend

### Recálculo de patrones

Se ejecuta `_recalcular_patrones(usuario_id, modulo, parcela_id, fecha)` al final de cada `POST` de creación/edición en cualquier módulo.

Pasos:
1. Calcular `temporada` a partir de la fecha del registro
2. Para cada campo relevante del módulo, contar ocurrencias agrupadas por valor filtrando por `usuario_id + módulo + parcela_id + temporada`
3. Seleccionar el valor con mayor `frecuencia` (y en empate, el más reciente por `ultima_vez`)
4. `INSERT OR REPLACE INTO ia_patrones`

### Campos aprendidos por módulo

| Módulo | Campos |
|--------|--------|
| tratamientos | producto_nombre, nº_mapa, sustancia_activa, plaga, dosis_valor, unidad, equipo, aplicador |
| fertilizacion | tipo_abono, npk, dosis_valor, unidad |
| riego | tipo_riego, unidad_volumen |
| labores | tipo_labor, maquinaria |
| cosecha | destino, variedad |
| compras | proveedor, unidad |
| cultivo_campana | cultivo_iacs, variedad |

### Generación de alertas

Se ejecuta en cada login. Tres tipos:

- **`sin_registro_reciente`** — si el último registro en un módulo para una parcela activa tiene más de 30 días → *"Llevas X días sin registrar tratamientos en [parcela]"*
- **`plazo_seguridad_proximo`** — si un tratamiento tiene `fecha_minima_cosecha` a menos de 7 días → *"El plazo de seguridad de [producto] en [parcela] vence el [fecha]"*
- **`sin_cultivo_campana`** — si una parcela activa no tiene cultivo asignado para la campaña actual → *"La parcela [nombre] no tiene cultivo de campaña asignado"*

Alertas anteriores del mismo tipo y parcela se marcan como expiradas antes de crear las nuevas.

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/ia/sugerencias` | `?modulo=X&parcela_id=Y` → devuelve `{campo: valor}` para prerrellenar |
| `GET` | `/api/ia/alertas` | Alertas activas del usuario (no leídas) |
| `POST` | `/api/ia/alertas/<id>/leer` | Marca alerta como leída |
| `POST` | `/api/ia/feedback` | `{patron_id, accion, valor_final}` → registra feedback |

---

## Frontend

### Prerrellenado en formularios

1. Al abrir cualquier formulario de nuevo registro, llamar a `GET /api/ia/sugerencias`
2. Prerrellenar los campos con los valores devueltos
3. Mostrar chip `💡 Sugerido` en gris claro debajo de cada campo prerrellenado
4. Al tocar el campo, el chip desaparece
5. Al guardar el formulario, enviar `POST /api/ia/feedback` por cada campo sugerido:
   - Sin cambios → `aceptada`
   - Valor diferente al sugerido → `modificada` + `valor_final`
   - Campo vacío siendo que había sugerencia → `ignorada`

### Tarjetas de alerta en pantalla de inicio

- Sección `💡 Recordatorios` encima de los módulos, solo si hay alertas activas
- Máximo 3 tarjetas visibles (ordenadas por urgencia: `plazo_seguridad_proximo` > `sin_cultivo_campana` > `sin_registro_reciente`)
- Cada tarjeta tiene botón `✕` para descartar (llama a `/api/ia/alertas/<id>/leer`)
- Si no hay alertas, la sección no se renderiza — la pantalla queda exactamente igual que ahora

---

## Orden de implementación sugerido

1. Crear las 3 tablas en BD (migración)
2. Función `_recalcular_patrones` + `_temporada` en `app.py`
3. Enganchar `_recalcular_patrones` en los `POST` de todos los módulos
4. Endpoint `GET /api/ia/sugerencias`
5. Prerrellenado en formularios frontend + chip "Sugerido"
6. Endpoint `POST /api/ia/feedback`
7. Función `_generar_alertas` + ejecutar en login
8. Endpoints de alertas
9. Tarjetas de recordatorio en pantalla de inicio
