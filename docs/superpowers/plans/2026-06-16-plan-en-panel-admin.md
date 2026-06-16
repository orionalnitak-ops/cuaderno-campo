# Plan del agricultor en el Panel de Admin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mostrar en cada tarjeta de agricultor del Panel de Admin un chip con su plan actual (Pro/Básico/Prueba/Caducado) y la fecha relevante (fin de prueba o renovación).

**Architecture:** Una función pura `compute_plan_status(plan, trial_ends_at, role)` en `backend/extensions.py` centraliza la lógica de fechas que ya existía duplicada en `User.plan_is_active()`/`plan_label()`. El endpoint `GET /api/admin/users` la reutiliza para anotar cada usuario con `plan_label`/`plan_active`. El frontend (`screens_admin.jsx`) renderiza un chip de color según `plan_label`, con la fecha de `trial_ends_at` o `subscription_ends_at` formateada.

**Tech Stack:** Python/Flask (backend), React vía Babel standalone (frontend, sin bundler — `npm run build` compila `.jsx` a `frontend/dist/*.js`).

**Spec:** `docs/superpowers/specs/2026-06-16-plan-en-panel-admin-design.md`

---

### Task 1: Extraer `compute_plan_status` en `extensions.py`

**Files:**
- Modify: `backend/extensions.py:28-49`

- [ ] **Step 1: Añadir la función `compute_plan_status` y hacer que `User` delegue en ella**

Reemplaza el bloque completo de `plan_is_active`/`plan_label` (líneas 28-49 del archivo actual):

```python
    def plan_is_active(self):
        """True si el usuario puede escribir datos (trial vigente, basic o pro)."""
        if self.role == 'admin':
            return True
        if self.plan in ('basic', 'pro'):
            return True
        if self.plan == 'trial' and self.trial_ends_at:
            ends = self.trial_ends_at
            if isinstance(ends, str):
                ends = datetime.datetime.fromisoformat(ends.replace('Z', ''))
            return datetime.datetime.utcnow() < ends
        return False

    def plan_label(self):
        """Estado legible para el frontend."""
        if self.plan in ('basic', 'pro'):
            return self.plan
        if self.plan == 'trial':
            if self.plan_is_active():
                return 'trial'
            return 'expired'
        return 'expired'
```

por:

```python
    def plan_is_active(self):
        """True si el usuario puede escribir datos (trial vigente, basic o pro)."""
        _, active = compute_plan_status(self.plan, self.trial_ends_at, self.role)
        return active

    def plan_label(self):
        """Estado legible para el frontend."""
        label, _ = compute_plan_status(self.plan, self.trial_ends_at, self.role)
        return label
```

Y justo **antes** de `class User(UserMixin):` (línea 16), añade la función a nivel de módulo:

```python
def compute_plan_status(plan, trial_ends_at, role):
    """Calcula el estado de plan de un usuario a partir de datos crudos de BD.

    Devuelve (label, active):
      label  -> 'pro' | 'basic' | 'trial' | 'expired'
      active -> True si el usuario puede escribir datos en su cuaderno.

    Replica exactamente el comportamiento que antes vivía repartido entre
    User.plan_is_active() y User.plan_label(), para poder reutilizarlo
    también con filas de BD que no pasan por un objeto User (p.ej. el
    listado del panel de admin).
    """
    def _is_active():
        if role == 'admin':
            return True
        if plan in ('basic', 'pro'):
            return True
        if plan == 'trial' and trial_ends_at:
            ends = trial_ends_at
            if isinstance(ends, str):
                ends = datetime.datetime.fromisoformat(ends.replace('Z', ''))
            return datetime.datetime.utcnow() < ends
        return False

    active = _is_active()
    if plan in ('basic', 'pro'):
        label = plan
    elif plan == 'trial':
        label = 'trial' if active else 'expired'
    else:
        label = 'expired'
    return label, active
```

- [ ] **Step 2: Verificar que el refactor no cambia el comportamiento**

Crea un script temporal `backend/_verify_plan_status.py` (no se commitea):

```python
import sys, datetime
sys.path.insert(0, '.')
from extensions import compute_plan_status

future = (datetime.datetime.utcnow() + datetime.timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
past   = (datetime.datetime.utcnow() - datetime.timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')

cases = [
    (('pro', None, 'agricultor'),     ('pro', True)),
    (('basic', None, 'agricultor'),   ('basic', True)),
    (('trial', future, 'agricultor'), ('trial', True)),
    (('trial', past, 'agricultor'),   ('expired', False)),
    (('trial', None, 'agricultor'),   ('expired', False)),
    (('trial', past, 'admin'),        ('trial', True)),
    (('pro', None, 'admin'),          ('pro', True)),
    (('unknown', None, 'agricultor'), ('expired', False)),
]

ok = True
for args, expected in cases:
    result = compute_plan_status(*args)
    status = 'OK' if result == expected else 'FAIL'
    if result != expected:
        ok = False
    print(f"{status}  compute_plan_status{args} -> {result}  (esperado {expected})")

print('\nTODO OK' if ok else '\nHAY FALLOS')
```

Run: `cd "h:/Proyectos/Cuaderno ex app/backend" && python _verify_plan_status.py`

Expected: las 8 líneas dicen `OK` y la última línea es `TODO OK`. Si alguna dice `FAIL`, revisa el caso antes de continuar — no avances con fallos.

- [ ] **Step 3: Borrar el script temporal**

Run: `rm "h:/Proyectos/Cuaderno ex app/backend/_verify_plan_status.py"`

- [ ] **Step 4: Commit**

```bash
cd "h:/Proyectos/Cuaderno ex app"
git add backend/extensions.py
git commit -m "refactor: extraer compute_plan_status para reutilizar lógica de plan"
```

---

### Task 2: Anotar `plan_label`/`plan_active` en `GET /api/admin/users`

**Files:**
- Modify: `backend/blueprints/admin.py:1-30`

- [ ] **Step 1: Importar `compute_plan_status`**

En la cabecera de imports de `backend/blueprints/admin.py`:

```python
from db import get_db, one, dicts
from helpers import admin_required
```

cambia por:

```python
from db import get_db, one, dicts
from helpers import admin_required
from extensions import compute_plan_status
```

- [ ] **Step 2: Ampliar el SELECT y anotar cada usuario**

Dentro de `admin_users()`, reemplaza:

```python
    if request.method == 'GET':
        users = dicts(conn, "SELECT id,email,nombre,role,active,created_at FROM users ORDER BY created_at DESC")
        for u in users:
            uid = u['id']
            t = one(conn, "SELECT COUNT(*) as n FROM tratamientos WHERE user_id=?", (uid,))
            p = one(conn, "SELECT COUNT(*) as n FROM parcelas WHERE user_id=? AND activa=1", (uid,))
            l = one(conn, "SELECT COUNT(*) as n FROM labores WHERE user_id=?", (uid,))
            u['stats'] = {
                "tratamientos": t['n'] if t else 0,
                "parcelas": p['n'] if p else 0,
                "labores": l['n'] if l else 0,
            }
        conn.close()
        return jsonify(users)
```

por:

```python
    if request.method == 'GET':
        users = dicts(conn, "SELECT id,email,nombre,role,active,created_at,plan,trial_ends_at,subscription_ends_at FROM users ORDER BY created_at DESC")
        for u in users:
            uid = u['id']
            t = one(conn, "SELECT COUNT(*) as n FROM tratamientos WHERE user_id=?", (uid,))
            p = one(conn, "SELECT COUNT(*) as n FROM parcelas WHERE user_id=? AND activa=1", (uid,))
            l = one(conn, "SELECT COUNT(*) as n FROM labores WHERE user_id=?", (uid,))
            u['stats'] = {
                "tratamientos": t['n'] if t else 0,
                "parcelas": p['n'] if p else 0,
                "labores": l['n'] if l else 0,
            }
            u['plan_label'], u['plan_active'] = compute_plan_status(u['plan'], u['trial_ends_at'], u['role'])
        conn.close()
        return jsonify(users)
```

- [ ] **Step 3: Verificar contra la base de datos real (solo lectura)**

Crea un script temporal `backend/_verify_admin_users_query.py` (no se commitea):

```python
import sys
sys.path.insert(0, '.')
from db import get_db, dicts
from extensions import compute_plan_status

conn = get_db()
users = dicts(conn, "SELECT id,email,nombre,role,active,created_at,plan,trial_ends_at,subscription_ends_at FROM users ORDER BY created_at DESC")
conn.close()

for u in users:
    label, active = compute_plan_status(u['plan'], u['trial_ends_at'], u['role'])
    print(f"{u['email']:30s} role={u['role']:11s} plan={str(u['plan']):8s} -> label={label:8s} active={active}")
```

Run: `cd "h:/Proyectos/Cuaderno ex app/backend" && python _verify_admin_users_query.py`

Expected: una línea por cada usuario real de la BD, sin errores ni tracebacks. Revisa que los admins salgan con `label=pro active=True` y que los agricultores muestren un `label` coherente con lo que esperarías de su plan real.

- [ ] **Step 4: Borrar el script temporal**

Run: `rm "h:/Proyectos/Cuaderno ex app/backend/_verify_admin_users_query.py"`

- [ ] **Step 5: Commit**

```bash
cd "h:/Proyectos/Cuaderno ex app"
git add backend/blueprints/admin.py
git commit -m "feat(admin): incluir plan_label y plan_active en GET /api/admin/users"
```

---

### Task 3: Chip de plan en la tarjeta de agricultor

**Files:**
- Modify: `frontend/screens_admin.jsx:121-123` (añadir helpers), `frontend/screens_admin.jsx:265-277` (renderizar chip)

- [ ] **Step 1: Añadir constantes y helpers de formato**

Justo después de esta línea existente:

```javascript
    const ROLE_LABEL = { admin: '👑 Admin', agricultor: '🌾 Agricultor' };
    const ROLE_COLOR = { admin: '#78350f', agricultor: '#065f46' };
    const ROLE_BG    = { admin: 'rgba(120,53,15,0.10)', agricultor: 'rgba(6,95,70,0.10)' };
```

añade:

```javascript
    const PLAN_CHIP = {
        pro:     { bg:'#ede9fe', color:'#5b21b6', label:'🟣 PRO' },
        basic:   { bg:'#dcfce7', color:'#065f46', label:'🟢 BÁSICO' },
        trial:   { bg:'#fef3c7', color:'#78350f', label:'🟡 PRUEBA' },
        expired: { bg:'var(--tertiary-fixed)', color:'var(--tertiary)', label:'🔴 CADUCADO' },
    };

    const formatFecha = (iso) => {
        if (!iso) return '';
        const d = new Date(iso.replace(' ', 'T'));
        if (isNaN(d.getTime())) return '';
        return d.toLocaleDateString('es-ES');
    };

    const renderPlanChip = (u) => {
        if (u.role === 'admin') return null;
        const style = PLAN_CHIP[u.plan_label] || PLAN_CHIP.expired;
        let suffix = '';
        if (u.plan_label === 'trial') {
            const f = formatFecha(u.trial_ends_at);
            if (f) suffix = ` · vence ${f}`;
        } else if (u.plan_label === 'expired') {
            const f = formatFecha(u.trial_ends_at);
            if (f) suffix = ` · caducó ${f}`;
        } else if (u.plan_label === 'basic' || u.plan_label === 'pro') {
            const f = formatFecha(u.subscription_ends_at);
            if (f) suffix = ` · renueva ${f}`;
        }
        return (
            <span style={{
                display:'inline-flex', alignItems:'center', gap:3,
                background: style.bg, color: style.color,
                borderRadius:'var(--radius-full)', padding:'2px 8px',
                fontSize:'0.65rem', fontWeight:700, letterSpacing:'0.04em',
            }}>
                {style.label}{suffix}
            </span>
        );
    };
```

- [ ] **Step 2: Renderizar el chip junto al rol**

Reemplaza:

```javascript
                                <div style={{ display:'flex', gap:6, marginTop:6, flexWrap:'wrap' }}>
                                    <span style={{
                                        display:'inline-flex', alignItems:'center', gap:3,
                                        background: ROLE_BG[u.role], color: ROLE_COLOR[u.role],
                                        borderRadius:'var(--radius-full)', padding:'2px 8px',
                                        fontSize:'0.65rem', fontWeight:700, letterSpacing:'0.04em',
                                    }}>
                                        {ROLE_LABEL[u.role] || u.role}
                                    </span>
                                    {!u.active && (
                                        <span className="chip chip-grey">INACTIVO</span>
                                    )}
                                </div>
```

por:

```javascript
                                <div style={{ display:'flex', gap:6, marginTop:6, flexWrap:'wrap' }}>
                                    <span style={{
                                        display:'inline-flex', alignItems:'center', gap:3,
                                        background: ROLE_BG[u.role], color: ROLE_COLOR[u.role],
                                        borderRadius:'var(--radius-full)', padding:'2px 8px',
                                        fontSize:'0.65rem', fontWeight:700, letterSpacing:'0.04em',
                                    }}>
                                        {ROLE_LABEL[u.role] || u.role}
                                    </span>
                                    {renderPlanChip(u)}
                                    {!u.active && (
                                        <span className="chip chip-grey">INACTIVO</span>
                                    )}
                                </div>
```

- [ ] **Step 3: Compilar el JSX a `dist/`**

Run: `cd "h:/Proyectos/Cuaderno ex app/frontend" && npm run build`

Expected: termina sin errores y `dist/screens_admin.js` se actualiza (mira la fecha de modificación o el contenido — debe incluir `renderPlanChip`).

- [ ] **Step 4: Verificar visualmente en la app**

1. Arranca el servidor: `cd "h:/Proyectos/Cuaderno ex app/backend" && python app.py`
2. Abre `http://127.0.0.1:5000` e inicia sesión como admin.
3. Ve a **Panel de Admin**.
4. Confirma que cada agricultor (no los admins) muestra su chip de plan junto a "🌾 Agricultor", con el color y la fecha esperados según su plan real en BD.
5. Comprueba que ningún chip se ve cortado ni rompe el ancho de la tarjeta en móvil (puedes usar las devtools del navegador en modo responsive).

- [ ] **Step 5: Commit**

```bash
cd "h:/Proyectos/Cuaderno ex app"
git add frontend/screens_admin.jsx frontend/dist/screens_admin.js
git commit -m "feat(admin): mostrar chip de plan y fecha en la tarjeta de cada agricultor"
```

---

## Self-Review

- **Cobertura de la spec:** chip con plan + fecha (Task 3) ✅, reutilizar lógica existente sin duplicar (Task 1) ✅, ampliar `GET /api/admin/users` (Task 2) ✅, excluir admins del chip (Task 3 Step 1, `if (u.role === 'admin') return null`) ✅, los 4 colores/etiquetas acordados (Task 3 Step 1) ✅, formato de fecha `dd/mm/aaaa` sin "Invalid Date" cuando falta (Task 3 Step 1, `formatFecha` devuelve `''` si no hay fecha) ✅.
- **Placeholders:** ninguno — todos los pasos llevan código completo y comandos con salida esperada.
- **Consistencia de tipos/nombres:** `compute_plan_status(plan, trial_ends_at, role)` se define igual en Task 1 y se usa igual en Task 2; `plan_label`/`plan_active` se nombran igual en el JSON de Task 2 y se leen igual (`u.plan_label`, `u.plan_active` no se usa en frontend pero queda disponible) en Task 3.
