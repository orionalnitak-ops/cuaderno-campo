# Spec: Modo Offline / PWA — Cuaderno de Explotación

**Fecha:** 2026-06-18
**Estado:** Aprobado

---

## Contexto y objetivo

Los agricultores usan la app desde el móvil en la finca, donde no siempre hay cobertura. El objetivo es que puedan registrar tratamientos, fertilizaciones y labores en el campo —sin red— y que esos datos se sincronicen automáticamente cuando vuelvan a tener conexión.

---

## Decisiones de diseño

- **Enfoque:** PWA híbrida (Service Worker + IndexedDB, sin Background Sync API)
- **Razón:** Compatibilidad total con iOS Safari y Android Chrome. Background Sync solo funciona en Chromium y añade complejidad innecesaria para este caso de uso.
- **Conflictos:** `local gana`. Un registro creado offline siempre se sube al servidor. En ediciones simultáneas (prácticamente imposibles con un usuario en un solo dispositivo), gana el timestamp más reciente.

---

## Arquitectura

```
App (HTML/JS/CSS)
├── Sync Engine       — detecta online/offline, dispara sync automático y manual
├── UI Indicators     — banner sin cobertura, badge pendientes, botón sync
└── IndexedDB         — espejo local de la BD del servidor

        │ (cuando hay red)
   Service Worker      — cachea assets, intercepta peticiones
        │
   API Flask (/api/...)
```

---

## Módulos con soporte offline

| Módulo | Lectura offline | Escritura offline |
|---|---|---|
| Parcelas | ✓ (seed al cargar) | ✗ (se gestionan en casa) |
| Tratamientos | ✓ | ✓ |
| Fertilización | ✓ | ✓ |
| Labores | ✓ | ✓ |
| Trazabilidad | ✓ | ✓ |
| Exportación PDF/Excel | ✗ | ✗ |

---

## IndexedDB — esquema

Espeja las tablas del servidor. Cada store añade:

- `sync_status: 'synced' | 'pending'`
- `local_id: string` — UUID generado en el dispositivo (ej: `loc_1718700000_abc`). Solo presente en registros pendientes.

Stores: `parcelas_local`, `tratamientos_local`, `fertilizacion_local`, `labores_local`, `trazabilidad_local`.

---

## Flujos de datos

### Lectura
```
App solicita datos
  ├─ Con red  → fetch /api/{modulo} → actualiza IndexedDB → muestra
  └─ Sin red  → lee IndexedDB → muestra
```

### Escritura
```
Agricultor guarda un registro
  ├─ Con red  → POST /api/{modulo} → OK → guarda en IndexedDB (status: synced)
  └─ Sin red  → guarda en IndexedDB (status: pending, local_id: uuid)
                   → badge "+1 pendiente"
                   → sync automático cuando recupera red
```

### Sincronización
```
Evento 'online' detectado O botón "Sincronizar" pulsado
  → Lee IndexedDB: registros con sync_status = 'pending'
  → POST /api/{modulo} por cada registro pendiente
    ├─ OK    → sync_status = 'synced', elimina local_id
    └─ Error → mantiene 'pending', reintenta en siguiente sync
               → avisa: "X registros no se pudieron subir"
```

---

## Service Worker — estrategia de caché

| Recurso | Estrategia |
|---|---|
| HTML, CSS, JS, iconos, fuentes | Cache First |
| GET `/api/parcelas`, `/api/tratamientos`, etc. | Network First → IndexedDB fallback |
| POST `/api/*` (escritura) | IndexedDB primero → sync posterior |

---

## PWA — instalación

**manifest.json:**
```json
{
  "name": "Cuaderno de Explotación",
  "short_name": "Cuaderno",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#2d7a2d"
}
```

`display: standalone` elimina la barra del navegador al instalar — parece app nativa.

Banner de instalación: aparece una vez, solo cuando el navegador emite `beforeinstallprompt`. Opciones: "Instalar" / "Ahora no". No vuelve a aparecer si el usuario lo descarta.

---

## UI — indicadores de estado

### Banner sin cobertura
Aparece en la cabecera cuando `navigator.onLine === false`. Fondo naranja suave, texto grande.
```
📵  Sin cobertura · datos guardados en el dispositivo
```

### Badge de pendientes
En la cabecera junto al icono de sincronización. Desaparece cuando `pending = 0`.
```
⟳ 3
```

### Botón "Sincronizar" (menú principal)
Siempre visible. Botón mínimo 44px. Muestra:
- Número de registros pendientes
- Hora del último sync exitoso
- Resultado tras pulsar: "3 registros subidos" o "Sin conexión, inténtalo más tarde"

### Toast de confirmación
Aparece 3 segundos tras sync exitoso:
```
✓ 3 registros sincronizados
```
Sin modales, sin confirmaciones extra.

---

## Archivos a crear / modificar

| Archivo | Acción | Descripción |
|---|---|---|
| `frontend/sw.js` | Crear | Service Worker: caché de assets + interceptor de fetch |
| `frontend/js/db.js` | Crear | Wrapper de IndexedDB (stores, read, write, query pending) |
| `frontend/js/sync.js` | Crear | Sync Engine: detecta online/offline, ejecuta sync, expone botón |
| `frontend/manifest.json` | Crear | PWA manifest |
| `frontend/js/ui-offline.js` | Crear | Banner, badge, toast |
| `frontend/index.html` | Modificar | Registrar SW, añadir `<link rel="manifest">`, incluir nuevos scripts |
| Cada módulo HTML/JS | Modificar | Escritura pasa por `db.js` antes de fetch; lectura lee de IndexedDB si falla red |

---

## Fuera de alcance (esta fase)

- Background Sync API
- Sincronización multi-dispositivo simultánea
- Exportación PDF/Excel offline
- Panel asesor offline
