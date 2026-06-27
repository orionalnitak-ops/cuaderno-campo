# Tech Stack — CUE

## Backend

- **Lenguaje:** Python 3.x
- **Framework:** Flask con blueprints (una ruta por dominio, nunca en `app.py`)
- **Base de datos:** SQLite (local) / PostgreSQL (producción)
- **PDF:** ReportLab
- **Excel:** openpyxl
- **Auth:** Flask-Login
- **Rate limiting:** Flask-Limiter
- **Pagos:** Stripe
- **Push notifications:** VAPID + APScheduler

## Frontend

- **Framework:** React (CDN + Babel Standalone en dev)
- **Build:** `npm run build` en `frontend/` → genera `frontend/dist/*.js`
- **Patrón:** SPA, mobile-first (botones mínimo 44px, formularios una columna)

## Infraestructura

- **Hosting:** EasyPanel en VPS Contabo `75.119.149.104`
- **Deploy:** push a `main` → webhook GitHub → EasyPanel reconstruye Docker
- **Arranque local:** `python app.py` en `backend/` → `http://127.0.0.1:5000`

## Reglas de BD (no negociables)

```python
# Patrón obligatorio — NO usar context manager with conn:
conn = get_db()
# ... operaciones
conn.commit()
conn.close()
```

- Placeholders: siempre `?` (el wrapper traduce a `%s` para psycopg2)
- Nuevas columnas: `_add_col(c, 'tabla', 'col', 'TYPE')` en `init_db()`, nunca `ALTER TABLE` en frío
- Upsert en PG: `INSERT INTO ... ON CONFLICT (col) DO UPDATE SET col = EXCLUDED.col`
- No usar `INSERT OR REPLACE` (solo SQLite)

## Reglas de API

- Toda ruta devuelve JSON: éxito `{"ok": true, "data": ...}` / error `{"ok": false, "error": "mensaje"}`
- Toda query filtra por `user_id = current_user.id` — aislamiento total entre agricultores

## Estructura de carpetas clave

```
backend/
  app.py              ← factory: init_db, Flask app, registra blueprints
  db.py               ← capa de acceso a BD (SQLite/PG dual engine)
  export_pdf.py       ← generación PDF con ReportLab
  exports.py          ← generación Excel con openpyxl
  blueprints/         ← una ruta por dominio
frontend/
  app.jsx             ← router principal
  screens_*.jsx       ← pantallas por módulo
  screens_forms.jsx   ← todos los formularios
  service-worker.js   ← PWA offline (SW v18)
  index.html          ← SPA shell
```

## Variables de entorno (producción)

`DATABASE_URL`, `SECRET_KEY`, `REDIS_URL`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`,
`VAPID_EMAIL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `ALLOWED_ORIGINS`
