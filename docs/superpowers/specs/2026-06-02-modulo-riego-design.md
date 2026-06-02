# Diseño: Módulo de Riego (FAB)

**Fecha:** 2026-06-02
**Motivación:** RD 934/2025 obliga desde el 1 enero 2026 a registrar las operaciones de riego (fecha, tipo, volumen de agua aplicado) en el cuaderno de explotación.

---

## Base de datos

Nueva tabla `riego`:

| Campo | Tipo | Obligatorio |
|---|---|---|
| `id` | PK | auto |
| `user_id` | INTEGER | auto |
| `parcela_id` | INTEGER | ✅ |
| `parcela_etiqueta` | TEXT | auto |
| `fecha` | TEXT (YYYY-MM-DD) | ✅ |
| `tipo_riego` | TEXT | ✅ — Goteo, Aspersión, Gravedad, Pivot |
| `volumen_m3` | REAL | ✅ — m³ totales aplicados |
| `horas_riego` | REAL | opcional |
| `fuente_agua` | TEXT | opcional — Pozo, Comunidad de regantes, Balsa, Río |
| `notas` | TEXT | opcional |
| `campana` | TEXT | auto (campaña activa) |
| `created_at` | TIMESTAMP | auto |
| `updated_at` | TIMESTAMP | auto |
| `deleted_at` | TEXT | borrado lógico |

---

## Backend (`backend/app.py`)

### `_validate_riego(data)`
Valida que `fecha`, `parcela_id`, `tipo_riego` y `volumen_m3` estén presentes y que la fecha no sea futura.

### Rutas
- `GET /api/riego` — lista riegos del usuario para la campaña activa (query param `campana`)
- `POST /api/riego` — crea nuevo registro
- `GET /api/riego/<id>` — devuelve un registro (para editar)
- `PUT /api/riego/<id>` — actualiza registro
- `DELETE /api/riego/<id>` — borrado lógico (`deleted_at = now()`)

Todas filtradas por `user_id`. Devuelven `{"ok": true}` o `{"error": "..."}`.

### Historial
La query de `/api/historial` añade registros de `riego` con:
- `_modulo: 'riego'`
- `_fecha: fecha`
- `_resumen: "{tipo_riego} — {volumen_m3} m³"`

### Dashboard
El contador de `/api/inicio` suma los riegos de la campaña activa.

---

## Frontend

### `app.jsx`
Añadir a `MODULE_CARDS`:
```js
{ id: 'riego', icon: '💧', title: 'Riego', desc: 'Aplicación de agua por parcela y campaña.', bg: 'linear-gradient(135deg, #0369a1, #0ea5e9)' }
```

### `screens_forms.jsx`
- Añadir `riego` al mapa de configuración de módulos (`icon: '💧'`, `title: 'Riego'`, `color: '#0ea5e9'`)
- Añadir componente `FormRiego` con:
  - Campos principales (visibles): Parcela, Fecha, Tipo de riego, Volumen (m³)
  - Campos opcionales en `<MasCampos>`: Horas de riego, Fuente de agua, Notas
  - Mismo patrón que `FormFertilizacion`: `ZoomInput`, `FieldGroup`, `ParcelSelect`

### `screens_history.jsx`
- Añadir `riego` a `MODULE_META`: `{ icon: '💧', label: 'Riego', chipClass: 'chip-riego', accentColor: '#0ea5e9' }`
- Añadir `'💧 Riego'` al selector de filtros de módulo

### CSS (`index.html`)
Añadir clase `.chip-riego` siguiendo el mismo patrón que `.chip-fertilizacion`.

### Borrar `screens_riego.jsx`
El archivo existente usa Tailwind CSS (no cargado) y no está conectado a nada. Se elimina.

---

## Fuera de alcance
- Plan de riego anual / programación de riegos futuros
- Integración con sensores de humedad o datos meteorológicos
- Cálculo de eficiencia hídrica
