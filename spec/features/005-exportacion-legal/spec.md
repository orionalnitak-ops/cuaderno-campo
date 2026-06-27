# Spec: Exportación PDF/Excel conforme a ley — RD 1311/2012 + Orden APA/204/2023

**Fecha:** 2026-06-27  
**Estado:** Aprobado  
**Normativa:** RD 1311/2012 Anexo III · Orden APA/204/2023 · RD 934/2025  
**Objetivo:** Que el documento exportado (PDF y Excel) sea legalmente válido y esté estructurado para ser compatible con SIEX cuando llegue ese momento. El agricultor no necesita saber qué campos exige la ley — la app los recoge y los exporta completos.

---

## Contexto y motivación

Los exports actuales (PDF y Excel) están bien construidos pero tienen cuatro brechas legales:

1. Los campos `asesor` y `justificacion_actuacion` existen en la tabla `tratamientos` (añadidos en commit 2ceba2e por Orden APA/204/2023) pero **no se exportan**.
2. Los campos `num_registro_roma` y `fecha_iteaf` existen en la tabla `equipos` pero **el JOIN del export no los recupera**.
3. El módulo de **riego** tiene tabla y datos pero **no hay sección en ningún export**.
4. El **código REGA** (Registro General de Explotaciones Agrícolas) no existe en la BD ni en el formulario — es necesario para SIEX y para identificar la explotación en el documento oficial.

---

## Alcance

### Fuera de alcance
- Integración técnica con SIEX/IUWS (envío automático de datos al REA).
- Módulo de cultivos campaña (código IACS): queda pendiente para sprint SIEX.

---

## Cambios por componente

### 1. Base de datos — migración `explotacion`

```sql
ALTER TABLE explotacion ADD COLUMN rega TEXT;
```

Se ejecuta en `init_db()` de `app.py` con `IF NOT EXISTS` implícito por ser `ALTER TABLE` sobre columna nueva (SQLite no falla si ya existe siempre que se envuelva en try/except).

### 2. UI — Formulario de explotación (ajustes)

Campo nuevo en la pantalla de ajustes de explotación, entre NIF y Municipio:

- **Label:** Código REGA
- **Tipo:** text input
- **Placeholder:** `ej: ES-CM-12345`
- **Ayuda:** _"Número de Registro de Explotaciones Agrícolas. Lo facilita la Consejería de Agricultura de tu comunidad autónoma."_
- **Obligatoriedad:** Opcional en UI. Si está vacío, el PDF lo muestra como `—` sin bloquear la exportación.
- **Validación:** Sin validación de formato (cada CCAA tiene formatos distintos).

### 3. PDF — `backend/export_pdf.py`

#### 3a. Portada (`_cover_page`)

Añadir fila "Código REGA" entre NIF y Municipio:

```python
('Código REGA', ex.get('rega') or '—'),
```

#### 3b. Tratamientos (`_section_tratamientos`) — fila doble

Restructurar de tabla plana a layout de dos filas por tratamiento:

**Fila 1** — datos de aplicación (fondo blanco/alternado normal):
| Fecha | Parcela | Producto Comercial | Nº Reg. MAPA | Sustancia Activa | Plaga/Objetivo | Dosis | Vol. Caldo (L/ha) | Plazo Seg. (d) | F. mín. Cosecha | Aplicador | Nº ROPO |

**Fila 2** — trazabilidad legal (fondo gris claro `#F3F4F6`, fuente 6.5pt):
| Equipo | Nº ROMA | Fecha ITEAF | Condic. Meteo | Asesor | Justificación actuación |

Implementación:
- La consulta SQL añade `JOIN equipos e ON t.equipo_id = e.id` y recupera `e.num_registro_roma`, `e.fecha_iteaf`.
- Cada tratamiento se construye como un `KeepTogether([fila1_table, fila2_table])` para evitar que se parta entre páginas.
- Las dos filas comparten el mismo ancho de columnas en las primeras 2 celdas (fecha + parcela) para alineación visual.
- La fila 2 no tiene borde exterior propio (solo borde inferior ligero para separar del siguiente tratamiento).

#### 3c. Nueva sección Riego (`_section_riego`)

Posición: entre `_section_labores` y `_section_cosecha`.  
Color de banner: `C_CYAN` (ya definido, sin usar actualmente).  
Icono: 💧

Columnas:
| Fecha | Parcela | Tipo de Riego | Volumen (m³) | Horas | Fuente de Agua | Notas |

Consulta:
```sql
SELECT r.*, p.nombre_finca 
FROM riego r
LEFT JOIN parcelas p ON r.parcela_id = p.id
WHERE r.user_id=? AND r.campana=? AND r.deleted_at IS NULL
ORDER BY r.fecha ASC
```

Pie de sección: total registros + volumen total m³ sumado.

Actualizar el índice de la portada para incluir la nueva sección (renumerar Cosecha, Plan Abonado, Compras).

### 4. Excel — `backend/exports.py`

#### 4a. Hoja TRATAMIENTOS FITOSANITARIOS

- Añadir al JOIN: `LEFT JOIN equipos e ON t.equipo_id = e.id`
- Añadir 4 columnas al final de `t_cols`:
  ```python
  "Asesor", "Justificación Actuación", "Nº ROMA Equipo", "Fecha ITEAF Equipo"
  ```
- Añadir los valores correspondientes en `row_data`:
  ```python
  r.get('asesor'), r.get('justificacion_actuacion'),
  r.get('num_registro_roma'), r.get('fecha_iteaf')
  ```

#### 4b. Nueva hoja RIEGO

- Color de cabecera: `TEAL_FILL` (ya definido).
- Columnas: `["ID", "Parcela", "Fecha", "Tipo Riego", "Volumen (m³)", "Horas", "Fuente Agua", "Notas", "Campaña"]`
- Insertar entre la hoja LABORES y COSECHA (antes del `wb.create_sheet("COSECHA")`).
- La hoja se incluye siempre (consistente con el resto de hojas). Si no hay registros, queda con solo la fila de cabecera.

---

## Seguridad y protección de datos

- Todas las consultas filtran por `user_id` — ningún dato de un agricultor es accesible por otro.
- El REGA es un código administrativo público (no dato personal sensible), pero se trata con el mismo nivel de protección que el resto de datos de la explotación.
- Los archivos se generan en memoria (`BytesIO`) y se sirven directamente — no se persisten en disco en el servidor.

---

## Índice actualizado del PDF

```
1. Registro de Parcelas
2. Tratamientos Fitosanitarios
3. Abonado / Fertilización
4. Labores Agrícolas
5. Riego        ← NUEVO
6. Cosecha / Recolección
7. Plan de Abonado
8. Compras de Fitosanitarios
```

---

## Criterios de aceptación

- [ ] El PDF generado incluye REGA en portada (o `—` si no está rellenado).
- [ ] Cada tratamiento en el PDF muestra dos filas: aplicación + trazabilidad legal.
- [ ] Los campos `asesor`, `justificacion_actuacion`, `num_registro_roma`, `fecha_iteaf` aparecen en la fila 2.
- [ ] Un tratamiento con muchas líneas no se parte entre páginas (KeepTogether).
- [ ] El PDF incluye sección de Riego con los 7 campos especificados.
- [ ] El Excel incluye las 4 columnas nuevas en la hoja de tratamientos.
- [ ] El Excel incluye hoja RIEGO si hay registros.
- [ ] El campo REGA aparece en el formulario de ajustes de explotación.
- [ ] Un agricultor sin REGA puede exportar sin error.
- [ ] Todos los datos filtran por `user_id` (test manual con dos usuarios distintos).
