# Auditoría de seguridad — IDOR / control de acceso

**Fecha:** 2026-07-06
**Alcance:** `backend/blueprints/*.py` (todas las rutas de datos + admin + auth + stripe)
**Herramienta:** skill `angelapaia/skill_auditor_seguridad` (SecOps Maestro v4.0) + revisión manual de patrones de consulta
**Vector auditado:** Broken Access Control / IDOR (acceso a recursos de otro usuario cambiando el `id` de la URL)
**Motivo:** pendiente registrado — SQLite no tiene RLS, así que cada consulta debe filtrar por dueño en el código.

---

## Veredicto

✅ **El backend está consistentemente defendido contra IDOR.** No se ha encontrado ninguna vulnerabilidad IDOR confirmada en las tablas de datos del usuario. El pendiente asumía un riesgo abierto; la revisión muestra que el patrón de propiedad ya está aplicado de forma sistemática.

Patrón correcto encontrado en todos los módulos:
- Mutaciones y lecturas filtran con `... WHERE id=? AND user_id=?`, **o**
- Un pre-check de propiedad devuelve 404 antes de mutar (p.ej. `cultivos_campana`, `explotacion`), **o**
- JOIN sobre la tabla propietaria: `JOIN parcelas p ON ... WHERE p.user_id=?`.

Rutas de administración: **todas** (`/api/admin/*`) llevan el decorador `@admin_required` (admin.py:24,79,120,150,158,166,193). No hay escalada de privilegios por ruta admin sin proteger.

Webhooks Stripe: usan `current_user.id` o `uid_meta` de metadatos firmados por Stripe, no input de URL. Correcto.

---

## Observaciones de *hardening* (no son vulnerabilidades, son defensa en profundidad)

### 1. Consultas con `WHERE id=?` que dependen de un check previo — 🟡 fragilidad ante refactor
Correctas hoy, pero el filtro de dueño está en una línea anterior, no en la propia consulta:
- `parcelas.py:197,201,222` (`cultivos_campana`) — protegidas por el owner-check de `parcelas.py:190-193`.
- `explotacion.py:110` (`SELECT * FROM explotacion WHERE id=?`) — protegida por el owner-check de `explotacion.py:104`.

**Riesgo:** si un futuro refactor mueve o elimina el check previo, se abriría un IDOR silencioso.
**Nota:** `cultivos_campana` **no tiene columna `user_id`** (su propiedad se hereda de la parcela vía JOIN), así que el `id` desnudo + check previo es la única opción ahí — aceptable. Para `explotacion` sí se podría reforzar el GET con `AND user_id=?` directo.

### 2. Ámbito por explotación en recurso individual — 🟢 no es IDOR
`parcelas.py:69` (GET parcela individual) filtra por `user_id` pero no por `explotacion_id`. Un usuario con varias explotaciones podría tocar una parcela propia de una explotación no activa. **Mismo dueño → no es fuga de seguridad**, a lo sumo un matiz de UX/scoping.

---

## Confianza y límites de esta auditoría
- Revisión a nivel de **patrón de consulta** (grep exhaustivo de `WHERE id=?`, `parcela_id=?`, `explotacion_id=?` en todos los blueprints) + lectura completa de `parcelas.py` como módulo de referencia.
- **No** es una prueba dinámica (no se han lanzado peticiones reales con ids ajenos). Para certeza total, complementar con un test de integración que intente acceder a recursos de otro `user_id` y espere 404.

## Recomendación
- **No hay fix urgente que aplicar.** Cerrar el pendiente reclasificándolo de "riesgo abierto" a "verificado / hardening opcional".
- Opcional: (a) reforzar `explotacion.py:110` con `AND user_id=?`; (b) añadir un test de regresión IDOR.
- **Ningún cambio aplicado** en esta sesión (regla del proyecto: revisar `app.py`/rutas antes de tocar y aprobar aparte).
