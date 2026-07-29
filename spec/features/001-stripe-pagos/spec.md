# Stripe — Sistema de Pagos
**Fecha:** 2026-05-28  
**Estado:** Aprobado

---

## Planes

| | Mensual | Anual |
|---|:---:|:---:|
| **Básico** | 9,99€/mes | 100€/año |
| **Pro** *(multi-explotación)* | 14,99€/mes | 150€/año |

## Funcionalidades por plan

| Funcionalidad | Básico | Pro |
|---|:---:|:---:|
| Parcelas SIGPAC | ✅ | ✅ |
| Tratamientos fitosanitarios | ✅ | ✅ |
| Fertilización / Abono | ✅ | ✅ |
| Labores agrícolas | ✅ | ✅ |
| Compras y Ventas | ✅ | ✅ |
| Exportación Excel | ✅ | ✅ |
| Exportación PDF oficial (RD 1311/2012) | ✅ | ✅ |
| Widget meteorológico | ✅ | ✅ |
| Importar desde Excel / Google Sheets | ✅ | ✅ |
| **Compatible con SIEX** | ✅ | ✅ |
| Multi-explotación (hasta 5 titulares) | ❌ | ✅ |

La compatibilidad con SIEX está en **los dos planes**: es cómo se guardan y se exportan los datos, no un extra que se cobre. Lo que diferencia a Pro es la multi-explotación.

> **Lenguaje:** "compatible con SIEX", nunca "integración/subida a SIEX" — ver la regla dura en `CLAUDE.md`. La vía de *entidad habilitada* (envío por API IUWS) exige registro como entidad, certificado de sello de componente y una autorización firmada por cada titular; además, aparentemente, que los estatutos recojan la representación de terceros ante la administración agraria. No se asume por ahora, así que no se promete.

---

## Ciclo de vida del usuario

```
Registro
  → 7 días prueba gratuita (acceso Pro completo)
  → Caduca → Solo lectura + banner de pago
  → Paga Básico  → acceso completo excepto SIEX
  → Paga Pro     → acceso completo incluyendo SIEX
  → Cancela      → activo hasta fin del periodo pagado → Solo lectura
```

## Solo lectura (trial caducado / suscripción expirada)

- Puede ver todos sus datos (parcelas, tratamientos, etc.) ✅
- No puede añadir, editar ni borrar registros ❌
- No puede exportar PDF ni Excel ❌
- Banner fijo en la parte superior: *"Tu suscripción ha caducado — Renovar por 9,99€/mes"*

---

## Cambios en base de datos

```sql
ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'trial';
-- Valores: 'trial' | 'basic' | 'pro' | 'expired'
ALTER TABLE users ADD COLUMN trial_ends_at TIMESTAMP;
ALTER TABLE users ADD COLUMN subscription_ends_at TIMESTAMP;
ALTER TABLE users ADD COLUMN stripe_customer_id TEXT;
ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT;
```

Al registrarse un usuario nuevo: `plan = 'trial'`, `trial_ends_at = NOW() + 7 días`.

---

## Productos en Stripe

Crear cuatro precios (Price objects):

| ID lógico | Producto | Intervalo | Importe |
|---|---|---|---|
| `price_basic_monthly` | Básico | month | 9,99€ |
| `price_basic_yearly` | Básico | year | 100,00€ |
| `price_pro_monthly` | Pro | month | 14,99€ |
| `price_pro_yearly` | Pro | year | 150,00€ |

Los Price IDs reales de Stripe se guardan en variables de entorno:
```
STRIPE_PRICE_BASIC_MONTHLY
STRIPE_PRICE_BASIC_YEARLY
STRIPE_PRICE_PRO_MONTHLY
STRIPE_PRICE_PRO_YEARLY
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
```

---

## Flujo de pago (Stripe Checkout hosted)

1. Usuario elige plan + intervalo en la app → frontend llama `POST /api/stripe/checkout`
2. Backend crea sesión de Stripe Checkout con `trial_period_days=0` (ya usó el trial en la app)
3. Usuario completa pago en página de Stripe → redirige a `/pago-completado`
4. Stripe envía webhook `checkout.session.completed` → backend actualiza `plan` y `subscription_ends_at`

## Webhooks a manejar

| Evento | Acción |
|---|---|
| `checkout.session.completed` | `plan = 'basic'/'pro'`, guardar `stripe_customer_id` y `stripe_subscription_id` |
| `invoice.paid` | Extender `subscription_ends_at` |
| `customer.subscription.deleted` | `plan = 'expired'` al vencer el periodo actual |
| `customer.subscription.updated` | Actualizar plan si cambia de Básico a Pro o viceversa |

---

## Guardas de acceso en el backend

```python
def requires_active_plan(f):
    """Bloquea escritura si plan == 'expired' o trial caducado."""

def requires_pro(f):
    """Bloquea si plan != 'pro'. Para rutas SIEX (futuro)."""
```

El middleware comprueba en cada petición de escritura:
- Si `plan == 'trial'` y `trial_ends_at < now()` → tratar como `expired`
- Si `plan == 'expired'` → devolver 403 con `{"error": "subscription_required"}`

---

## Portal de cliente (Stripe Billing Portal)

No se construye UI propia para gestión de suscripción. Se usa el portal hosted de Stripe:
- Cambiar tarjeta
- Cancelar suscripción
- Descargar facturas

Accesible desde la app con un botón "Gestionar suscripción" → `POST /api/stripe/portal` → redirige al portal de Stripe.

---

## Fuera de alcance (no se implementa ahora)

- Facturas con NIF/CIF personalizadas (Stripe las genera automáticamente)
- Descuentos / cupones
- Plan de asesor / multiempresa
