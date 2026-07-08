# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Contexto global (heredado de Second Brain)
@../second-brain/raul.md
@../second-brain/principios.md
@../second-brain/decisiones.md

---

## Qué es este proyecto

App web SaaS para digitalizar el **Cuaderno de Explotación Agrícola** (CUE) obligatorio por ley en España (RD 1311/2012). Dirigida a agricultores sin conocimientos informáticos de Castilla-La Mancha.

> ## 🔥 REGLA DURA — Compatibilidad SIEX (no negociable, hasta nueva orden)
>
> El cuaderno debe mantener **SIEMPRE plena compatibilidad con SIEX y con lo que la ley pide** (RD 1311/2012, catálogos IACS/FEGA, deadline 01/01/2027). Cualquier feature nueva o cambio de modelo de datos **debe preservar** esa compatibilidad.
>
> **Lenguaje obligatorio:** decir **"compatible con SIEX"**, NUNCA "integración con SIEX" ni "subida/envío a SIEX". Motivo: aún no se sabe qué hace falta para obtener **autorización** de subida a SIEX; hasta tenerlo claro no se promete integración/envío que no se puede cumplir. Sí se garantiza compatibilidad (datos, catálogos, exportaciones alineados con SIEX). Aplica a UI, marketing, ayuda y specs.

**Piloto activo:** Lourdes (finca familiar, ~50+ parcelas SIGPAC).  
**Deadline legal:** 1 enero 2027 — fitosanitarios digitales obligatorios e interoperables con SIEX.  
**Versión actual:** `v0.9.0` (tag en GitHub).

---

## Comandos

```bash
# Arrancar servidor local
cd "H:\Proyectos\Cuaderno ex app\backend"
python app.py
# → http://127.0.0.1:5000 | red local: http://192.168.10.55:5000

# Compilar JSX → JS (necesario tras editar cualquier .jsx)
cd "H:\Proyectos\Cuaderno ex app\frontend"
npm run build       # one-shot
npm run watch       # modo watch durante desarrollo
```

> En producción el Dockerfile compila los JSX con Babel en la etapa `js-build` y los copia a `frontend/dist/`. En local, Flask sirve los `.jsx` originales directamente desde `frontend/` mediante `<script type="text/babel">` (Babel Standalone en navegador). Cuando despliegues, corre `npm run build` o deja que el Docker lo haga.

---

## Arquitectura

### Estructura de carpetas relevante

```
backend/
  app.py              ← factory: init_db, Flask app, CORS, rate-limit, registra blueprints
  db.py               ← capa de acceso a BD (SQLite/PostgreSQL dual engine)
  extensions.py       ← Flask-Login + Flask-Limiter instancias compartidas
  export_pdf.py       ← generación PDF con ReportLab
  exports.py          ← generación Excel con openpyxl
  blueprints/         ← una ruta por dominio; NUNCA añadir rutas en app.py
    auth.py           ← registro, login, logout, trial
    parcelas.py       ← CRUD parcelas SIGPAC
    tratamientos.py   ← CRUD fitosanitarios
    fertilizacion.py  ← CRUD abonado
    labores.py        ← CRUD labores agrícolas
    equipos.py        ← CRUD equipos de aplicación (ROMA, ITEAF)
    compras.py        ← CRUD compras/ventas
    sigpac.py         ← proxy SIGPAC, bulk update, selector recintos
    nlp.py            ← NLP por voz / "Habla que yo escribo"
    imports_exports.py← importar Excel; descargar PDF/Excel
    aemet.py          ← meteorología (Open-Meteo + METEOALARM + AEMET)
    push.py           ← push notifications VAPID + APScheduler
    stripe_bp.py      ← checkout Stripe + webhook
    admin.py          ← panel admin
    explotacion.py    ← datos de explotación (REGA, NIF, titular…)
    uhc.py            ← Unidades Homogéneas de Cultivo
frontend/
  app.jsx             ← router principal, componentes raíz
  screens_*.jsx       ← pantallas (una por módulo)
  screens_forms.jsx   ← todos los formularios de entrada de datos
  service-worker.js   ← SW v18 (PWA offline, caché CDN, IndexedDB sync)
  index.html          ← SPA shell; carga React CDN + Babel Standalone en dev
```

### Capa de base de datos (`db.py`)

El proyecto corre sobre SQLite en local y PostgreSQL en producción. La capa `db.py` abstrae las diferencias:

- `get_db()` → devuelve una conexión normalizada (SQLite `sqlite3.Connection` o `_PgConn`)
- `dicts(conn, sql, params)` → lista de dicts (funciona en ambos motores)
- `one(conn, sql, params)` → un dict o `None`
- `_add_col(cursor, table, col, type)` → migración segura (IF NOT EXISTS en PG, try/except en SQLite)

**Patrón obligatorio para toda operación de BD:**

```python
conn = get_db()
# ... operaciones con conn
conn.commit()
conn.close()
```

No usar context manager (`with conn:`) — `_PgConn` no lo implementa.

**Placeholders:** usar siempre `?` (el wrapper traduce a `%s` para psycopg2 automáticamente).

**Upsert en PostgreSQL:** usar `INSERT INTO ... ON CONFLICT (col) DO UPDATE SET col = EXCLUDED.col`. NO usar `INSERT OR REPLACE` (sólo SQLite).

**Nuevas columnas:** añadir siempre con `_add_col()` en `init_db()`, nunca como `ALTER TABLE` en frío.

### API pattern

Todas las rutas devuelven JSON:
- éxito: `{"ok": true, "data": ...}`
- error: `{"ok": false, "error": "mensaje"}`

Toda query filtra por `user_id = current_user.id` para aislar datos entre agricultores.

---

## Reglas de desarrollo

- **Mobile-first siempre.** Botones mínimo 44px. Formularios una columna.
- **No añadir rutas en `app.py`.** Crear o editar el blueprint correspondiente en `blueprints/`.
- **No romper módulos ya funcionando.** Cualquier cambio en `db.py` o `exports.py` requiere restart completo de gunicorn en producción (hot-reload parcial deja módulos cacheados).
- **Tras editar JSX** en local: `npm run build` en `frontend/`. En producción lo hace el Dockerfile.

---

## Flujo Git (obligatorio)

```
feature/xxx  →  PR  →  CI pasa  →  merge a main  →  deploy automático
```

- **Nunca pushear directo a `main`.** Todo cambio entra vía Pull Request.
- `main` está protegida: el merge queda bloqueado si el CI falla (lint + bandit).
- Cada PR recibe automáticamente un **Security Review de Claude** que busca vulnerabilidades antes de mergear.
- Nombrar ramas: `feat/nombre`, `fix/nombre`, `chore/nombre`.

---

## Prohibiciones de seguridad

- **Nunca hardcodear secretos, API keys ni contraseñas** en el código. Usar siempre variables de entorno.
- **Nunca construir queries SQL con f-strings o concatenación de strings.** Usar placeholders `?` con el wrapper `db.py`.
- **Nunca exponer stack traces al usuario.** Los errores de la API devuelven `{"ok": false, "error": "mensaje legible"}`, no el traceback.
- **Nunca usar `eval()` o `exec()`** con input externo.
- **Nunca subir el archivo `.env`** al repositorio. Está en `.gitignore`.
- **Nunca aprobar a ciegas** el código generado por IA. Leer y entender cada cambio antes de mergear.

---

## Especificaciones (SDD)

Este proyecto usa Spec-Driven Development. Antes de implementar cualquier feature nueva, consultar o crear los artefactos correspondientes:

- `spec/constitution/` — misión, stack y roadmap del proyecto
- `spec/features/NNN-nombre/spec.md` — qué construir y criterios de aceptación
- `spec/features/NNN-nombre/plan.md` — cómo implementarlo, archivos y tareas

Para features ya especificadas ver `spec/features/`. Para nueva feature: crear `spec/features/NNN-nombre/spec.md` antes de tocar código.

---

## Pendiente

Ver `spec/constitution/roadmap.md` para prioridades y estado actualizado.

Resumen rápido: 🔴 Stripe live · 🔴 SIEX (deadline 01/01/2027) · 🟠 Emails Resend · 🟠 Ayuda visual · 🟡 Asistente IA

---

## Producción

- **URL:** `https://cuaderno.tualiado.es`
- **Hosting:** EasyPanel en VPS Contabo `75.119.149.104`
- **Deploy:** push a `main` → webhook GitHub → EasyPanel reconstruye Docker y reinicia
- **Variables de entorno necesarias:** `DATABASE_URL`, `SECRET_KEY`, `REDIS_URL`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_EMAIL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `ALLOWED_ORIGINS`
