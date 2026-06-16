# Mostrar el plan del agricultor en el Panel de Admin

## Problema

El Panel de Admin (`screens_admin.jsx`) lista a todos los agricultores con su rol,
estado (activo/inactivo) y estadísticas (parcelas, tratamientos, labores), pero no
muestra qué plan tiene cada uno (`trial`, `basic`, `pro` o caducado), ni cuándo
caduca. El admin tiene que entrar a Stripe o a la base de datos para saberlo.

## Alcance

- Mostrar en cada tarjeta de agricultor: el plan actual (Básico / Pro / Prueba /
  Caducado) y la fecha relevante (fin de prueba o renovación de suscripción).
- No aplica a usuarios con `role === 'admin'` (su plan no es relevante para el
  negocio).
- No incluye: filtros/ordenación por plan, edición manual del plan desde el panel,
  ni avisos de prueba a punto de caducar — fuera de alcance de este cambio.

## Backend — `GET /api/admin/users`

Archivo: `backend/blueprints/admin.py`.

1. Ampliar el `SELECT` para incluir `plan, trial_ends_at, subscription_ends_at`.
2. Por cada usuario, calcular `plan_label` y `plan_active` reutilizando la lógica
   de fechas ya existente en `extensions.py` (evita duplicar la comparación de
   fechas que ya usa `User.plan_is_active()` / `plan_label()`).

### Refactor en `extensions.py`

Extraer la lógica de fecha/estado a una función pura:

```python
def compute_plan_status(plan, trial_ends_at, role):
    """Devuelve (label, active) para un plan dado.
    label: 'pro' | 'basic' | 'trial' | 'expired'
    """
    if role == 'admin':
        return ('pro', True)
    if plan in ('basic', 'pro'):
        return (plan, True)
    if plan == 'trial' and trial_ends_at:
        ends = trial_ends_at
        if isinstance(ends, str):
            ends = datetime.datetime.fromisoformat(ends.replace('Z', ''))
        active = datetime.datetime.utcnow() < ends
        return ('trial' if active else 'expired', active)
    return ('expired', False)
```

`User.plan_is_active()` y `User.plan_label()` pasan a delegar en esta función
(sin cambiar su firma ni el contrato que ya consume el resto del backend).

El endpoint `admin_users()` (GET) la usa para añadir a cada `u` del listado:

```python
label, active = compute_plan_status(u['plan'], u['trial_ends_at'], u['role'])
u['plan_label']  = label
u['plan_active'] = active
# u['plan'], u['trial_ends_at'], u['subscription_ends_at'] ya vienen del SELECT
```

No se toca el endpoint `POST /api/admin/users` (creación) ni ningún otro.

## Frontend — `screens_admin.jsx`

En la fila de chips de cada tarjeta (junto a `ROLE_LABEL` / `INACTIVO`,
línea ~265), añadir un chip de plan cuando `u.role !== 'admin'`:

| `plan_label` | Texto del chip | Color (bg / texto) | Fecha mostrada |
|---|---|---|---|
| `pro` | `🟣 PRO` (+ fecha si hay) | `#ede9fe` / `#5b21b6` | `subscription_ends_at` → "· renueva dd/mm/aaaa" si existe |
| `basic` | `🟢 BÁSICO` (+ fecha si hay) | `#dcfce7` / `#065f46` | igual que arriba |
| `trial` | `🟡 PRUEBA · vence dd/mm/aaaa` | `#fef3c7` / `#78350f` | `trial_ends_at` (siempre presente si label es trial) |
| `expired` | `🔴 CADUCADO` (+ fecha si hay) | `var(--tertiary-fixed)` / `var(--tertiary)` (clase `chip-red` ya existente) | `trial_ends_at` → "· caducó dd/mm/aaaa" si existe, si no, sin fecha |

Reglas de fecha:
- Formato `dd/mm/aaaa` con `toLocaleDateString('es-ES')`.
- Si no hay fecha disponible (plan asignado a mano sin `subscription_ends_at`,
  o sin `trial_ends_at`), el chip se muestra sin la parte de fecha — nunca un
  guion o "Invalid Date".

Implementación: un pequeño helper local en el componente,
`renderPlanChip(u)`, que devuelve `null` si `u.role === 'admin'` y si no,
el `<span className="chip" style={{...}}>` correspondiente. Se coloca junto a
los chips existentes dentro del mismo `<div style={{ display:'flex', gap:6, ... }}>`.

## Testing

- Manual: con el panel de admin abierto, comprobar que aparecen los 4 estados
  (crear/ajustar usuarios de prueba en BD local con cada combinación de
  `plan` / `trial_ends_at` / `subscription_ends_at`) y que las fechas se ven
  correctas y sin overflow en la tarjeta.
- No se modifica comportamiento de `plan_is_active()` para usuarios ya
  logueados — verificar que el guard de planes (`guard_active_plan` en
  `app.py`) sigue funcionando igual tras el refactor (mismo resultado antes/después
  para los mismos inputs).
