# Offline PWA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the app fully usable without internet — farmer can register treatments, fertilizations, labors, etc. in the field; data syncs automatically or via button when back online.

**Architecture:** Plain JS files (`offline-db.js`, `offline-sync.js`) expose globals (`window.OfflineDB`, `window.OfflineSync`) loaded before React app. Forms call `window.OfflineSync.post()` instead of raw fetch for POSTs. IndexedDB stores pending records; sync engine uploads them on reconnect. Service Worker already caches app shell — just needs version bump and new files added to pre-cache list.

**Tech Stack:** IndexedDB (native browser API, no library), Service Worker (already present at `frontend/service-worker.js`), React JSX compiled with Babel (`npm run build` from `frontend/`), Flask serves all static files from `frontend/` directory.

**Context:**
- Backend: `h:/Proyectos/Cuaderno ex app/backend/app.py`
- Frontend root: `h:/Proyectos/Cuaderno ex app/frontend/`
- Build: `cd "h:/Proyectos/Cuaderno ex app/frontend" && npm run build`
- Dev server: `cd "h:/Proyectos/Cuaderno ex app/backend" && python app.py` → http://127.0.0.1:5000
- Flask serves `frontend/` as static root — any file there is accessible at `/filename`
- `offline-db.js` and `offline-sync.js` are plain JS (no JSX, no Babel needed)
- JSX files that change need `npm run build` after editing

**API endpoints for offline POST queueing:**
- `/api/tratamientos`
- `/api/fertilizacion`
- `/api/labores`
- `/api/cosecha`
- `/api/compras`
- `/api/riego`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/offline-db.js` | **Create** | IndexedDB wrapper — pending queue + parcelas cache |
| `frontend/offline-sync.js` | **Create** | Sync engine — `post()` wrapper + `syncAll()` |
| `frontend/service-worker.js` | **Modify** | Bump cache version, add new files to APP_SHELL |
| `frontend/index.html` | **Modify** | Add `<script>` tags for offline-db.js + offline-sync.js |
| `frontend/app.jsx` | **Modify** | Offline banner, pending badge, sync trigger on reconnect |
| `frontend/screens_forms.jsx` | **Modify** | 6 form save() functions + parcelas offline fallback |

---

## Task 1: Create `frontend/offline-db.js` — IndexedDB wrapper

**Files:**
- Create: `frontend/offline-db.js`

- [ ] **Step 1: Create the file**

```js
// IndexedDB wrapper — exposes window.OfflineDB
(function () {
  const DB_NAME = 'cuaderno-offline-v1';
  const DB_VERSION = 1;
  let _db = null;

  function openDB() {
    return new Promise((resolve, reject) => {
      if (_db) { resolve(_db); return; }
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        // Pending records queue (one store for all modules)
        if (!db.objectStoreNames.contains('pending_records')) {
          const store = db.createObjectStore('pending_records', { keyPath: 'local_id' });
          store.createIndex('by_store', 'store_name', { unique: false });
        }
        // Parcelas cache (so forms work offline)
        if (!db.objectStoreNames.contains('parcelas_cache')) {
          db.createObjectStore('parcelas_cache', { keyPath: 'id' });
        }
      };
      req.onsuccess = (e) => { _db = e.target.result; resolve(_db); };
      req.onerror = () => reject(req.error);
    });
  }

  function tx(storeName, mode, fn) {
    return openDB().then(db => new Promise((resolve, reject) => {
      const transaction = db.transaction(storeName, mode);
      const store = transaction.objectStore(storeName);
      const req = fn(store);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    }));
  }

  window.OfflineDB = {
    // Save a record to the pending queue
    savePending(storeName, apiUrl, payload, localId) {
      const record = {
        local_id: localId,
        store_name: storeName,
        api_url: apiUrl,
        payload: payload,
        created_at: Date.now(),
      };
      return tx('pending_records', 'readwrite', s => s.put(record));
    },

    // Get all pending records (flat array)
    getAllPending() {
      return openDB().then(db => new Promise((resolve, reject) => {
        const t = db.transaction('pending_records', 'readonly');
        const req = t.objectStore('pending_records').getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => reject(req.error);
      }));
    },

    // Count all pending records
    countAllPending() {
      return openDB().then(db => new Promise((resolve, reject) => {
        const t = db.transaction('pending_records', 'readonly');
        const req = t.objectStore('pending_records').count();
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => resolve(0);
      }));
    },

    // Delete a pending record after successful sync
    deletePending(localId) {
      return tx('pending_records', 'readwrite', s => s.delete(localId));
    },

    // Cache parcelas list (called when loaded online)
    cacheParcelas(records) {
      return openDB().then(db => new Promise((resolve) => {
        const t = db.transaction('parcelas_cache', 'readwrite');
        const s = t.objectStore('parcelas_cache');
        s.clear();
        records.forEach(r => s.put(r));
        t.oncomplete = resolve;
        t.onerror = resolve; // fail silently
      }));
    },

    // Get cached parcelas (for offline form use)
    getCachedParcelas() {
      return openDB().then(db => new Promise((resolve) => {
        const t = db.transaction('parcelas_cache', 'readonly');
        const req = t.objectStore('parcelas_cache').getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => resolve([]);
      }));
    },
  };
})();
```

- [ ] **Step 2: Verify the file exists**

```
ls "h:/Proyectos/Cuaderno ex app/frontend/offline-db.js"
```

Expected: file listed with non-zero size.

---

## Task 2: Create `frontend/offline-sync.js` — Sync engine

**Files:**
- Create: `frontend/offline-sync.js`

- [ ] **Step 1: Create the file**

```js
// Sync engine — exposes window.OfflineSync
(function () {
  // Maps API URL prefix to a store name for the pending queue
  const URL_TO_STORE = {
    '/api/tratamientos': 'tratamientos',
    '/api/fertilizacion': 'fertilizacion',
    '/api/labores': 'labores',
    '/api/cosecha': 'cosecha',
    '/api/compras': 'compras',
    '/api/riego': 'riego',
  };

  function getStoreName(url) {
    for (const prefix of Object.keys(URL_TO_STORE)) {
      if (url.startsWith(prefix)) return URL_TO_STORE[prefix];
    }
    return 'generic';
  }

  function genLocalId() {
    return 'loc_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7);
  }

  const _listeners = [];

  function notifyListeners() {
    window.OfflineDB.countAllPending().then(count => {
      _listeners.forEach(fn => fn(count));
    });
  }

  window.OfflineSync = {
    // Subscribe to pending count changes
    onStatusChange(fn) {
      _listeners.push(fn);
    },

    // Call this instead of fetch() for POST requests in forms.
    // Returns a response-like object: { ok, _savedOffline, json() }
    async post(url, data) {
      if (navigator.onLine) {
        try {
          const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
            credentials: 'include',
          });
          // Success — no pending record needed
          return res;
        } catch (_e) {
          // Network error despite onLine — fall through to offline save
        }
      }

      // Save to IndexedDB pending queue
      const localId = genLocalId();
      const storeName = getStoreName(url);
      await window.OfflineDB.savePending(storeName, url, data, localId);
      notifyListeners();

      // Return a mock response that looks like a successful fetch response
      return {
        ok: true,
        _savedOffline: true,
        json: async () => ({ ok: true, data: { ...data, id: localId } }),
      };
    },

    // Upload all pending records to the server. Returns { synced, failed }.
    async syncAll() {
      const pending = await window.OfflineDB.getAllPending();
      let synced = 0;
      let failed = 0;

      for (const rec of pending) {
        try {
          const res = await fetch(rec.api_url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(rec.payload),
            credentials: 'include',
          });
          if (res.ok) {
            await window.OfflineDB.deletePending(rec.local_id);
            synced++;
          } else {
            failed++;
          }
        } catch (_e) {
          failed++;
          break; // Network gone again — stop trying
        }
      }

      notifyListeners();
      return { synced, failed };
    },
  };
})();
```

- [ ] **Step 2: Verify the file exists**

```
ls "h:/Proyectos/Cuaderno ex app/frontend/offline-sync.js"
```

Expected: file listed with non-zero size.

---

## Task 3: Update `frontend/service-worker.js` — bump cache version + add new files

**Files:**
- Modify: `frontend/service-worker.js`

The SW currently only pre-caches `'/'` and `'/manifest.json'`. Add the two new JS files to the APP_SHELL and bump the cache version so existing users get the update.

- [ ] **Step 1: Replace the top of the file**

Find and replace the first 7 lines (CACHE_NAME + APP_SHELL declaration):

```js
// OLD:
const CACHE_NAME = 'cuaderno-cache-v15';

const APP_SHELL = [
  '/',
  '/manifest.json',
];
```

Replace with:

```js
const CACHE_NAME = 'cuaderno-cache-v16';

const APP_SHELL = [
  '/',
  '/manifest.json',
  '/offline-db.js',
  '/offline-sync.js',
];
```

- [ ] **Step 2: Verify change**

Read the first 10 lines of `frontend/service-worker.js` and confirm `v16` and the two new paths appear.

---

## Task 4: Update `frontend/index.html` — add script tags

**Files:**
- Modify: `frontend/index.html`

The two new plain JS files must be loaded **before** all React scripts so `window.OfflineDB` and `window.OfflineSync` are available when the app boots.

- [ ] **Step 1: Add script tags**

In `index.html`, find this block (near line 873):

```html
  <!-- React (CDN) -->
  <script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
```

Insert the two new scripts **immediately before** that block:

```html
  <!-- Offline: IndexedDB + Sync engine (must load before React app) -->
  <script src="/offline-db.js"></script>
  <script src="/offline-sync.js"></script>

  <!-- React (CDN) -->
  <script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
```

- [ ] **Step 2: Verify**

Check that `offline-db.js` and `offline-sync.js` appear before the React CDN line.

---

## Task 5: Update `frontend/app.jsx` — offline banner, badge, sync trigger

**Files:**
- Modify: `frontend/app.jsx`
- Build after: `cd "h:/Proyectos/Cuaderno ex app/frontend" && npm run build`

This task adds three things to `app.jsx`:
1. State for `isOnline` and `pendingCount`
2. Effects that listen to online/offline events and trigger auto-sync
3. Offline banner and pending badge in the render output

- [ ] **Step 1: Add state variables**

In the `App()` function, after the existing state declarations (look for `const [showOnboarding, setShowOnboarding]`), add:

```jsx
    const [isOnline, setIsOnline]       = useState(navigator.onLine);
    const [pendingCount, setPendingCount] = useState(0);
    const [syncing, setSyncing]         = useState(false);
```

- [ ] **Step 2: Add online/offline effect**

After the existing `useEffect` blocks in `App()`, add a new one:

```jsx
    // Offline support: listen to network events, auto-sync on reconnect
    useEffect(() => {
        // Initialize pending count on mount
        if (window.OfflineDB) {
            window.OfflineDB.countAllPending().then(setPendingCount);
        }
        // Subscribe to pending count changes from OfflineSync
        if (window.OfflineSync) {
            window.OfflineSync.onStatusChange(setPendingCount);
        }

        const handleOnline = async () => {
            setIsOnline(true);
            if (window.OfflineSync) {
                setSyncing(true);
                const { synced, failed } = await window.OfflineSync.syncAll();
                setSyncing(false);
                if (synced > 0) {
                    showMsg(`✅ ${synced} registro${synced > 1 ? 's' : ''} sincronizado${synced > 1 ? 's' : ''}`);
                }
                if (failed > 0) {
                    showMsg(`⚠️ ${failed} registro${failed > 1 ? 's' : ''} no se pudieron subir`);
                }
            }
        };
        const handleOffline = () => setIsOnline(false);

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);
        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);
```

Note: `showMsg` is the existing toast function — verify the exact name in the file and use it.

- [ ] **Step 3: Add manual sync handler**

After the `handleSwitchUser` function, add:

```jsx
    const handleManualSync = useCallback(async () => {
        if (!navigator.onLine) { showMsg('Sin conexión — conéctate a internet para sincronizar'); return; }
        if (syncing) return;
        setSyncing(true);
        const { synced, failed } = await window.OfflineSync.syncAll();
        setSyncing(false);
        if (synced === 0 && failed === 0) { showMsg('No hay registros pendientes'); return; }
        if (synced > 0) showMsg(`✅ ${synced} registro${synced > 1 ? 's' : ''} sincronizado${synced > 1 ? 's' : ''}`);
        if (failed > 0) showMsg(`⚠️ ${failed} registro${failed > 1 ? 's' : ''} no se pudieron subir`);
    }, [syncing]);
```

- [ ] **Step 4: Add CSS for offline UI in `index.html`**

In `index.html`, inside the `<style>` block, append before the closing `</style>` tag:

```css
    /* ── Offline banner ── */
    .offline-banner {
      position: fixed;
      top: 0; left: 0; right: 0;
      z-index: 200;
      background: #92400e;
      color: #fef3c7;
      font-family: var(--font-body);
      font-size: 0.82rem;
      font-weight: 600;
      text-align: center;
      padding: 9px 16px;
      letter-spacing: 0.01em;
    }
    .pending-banner {
      position: fixed;
      top: 0; left: 0; right: 0;
      z-index: 200;
      background: #1e3a5f;
      color: #bfdbfe;
      font-family: var(--font-body);
      font-size: 0.82rem;
      font-weight: 600;
      text-align: center;
      padding: 9px 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
    }
    .pending-banner button {
      background: #3b82f6;
      color: #fff;
      border: none;
      border-radius: 20px;
      padding: 4px 14px;
      font-size: 0.78rem;
      font-weight: 700;
      cursor: pointer;
      font-family: var(--font-body);
      min-height: 28px;
    }
    .pending-banner button:disabled { opacity: 0.6; cursor: not-allowed; }
```

- [ ] **Step 5: Render the banners**

In the `App()` render/return, find the outermost wrapping `<div>` that contains `#sidebar`, `#topbar`, etc. Insert the banners as the **first children**:

```jsx
      {/* Offline & pending banners */}
      {!isOnline && (
        <div className="offline-banner">
          📵 Sin cobertura — los datos se guardan en el dispositivo
        </div>
      )}
      {isOnline && pendingCount > 0 && (
        <div className="pending-banner">
          <span>⟳ {pendingCount} registro{pendingCount > 1 ? 's' : ''} pendiente{pendingCount > 1 ? 's' : ''} de sincronizar</span>
          <button onClick={handleManualSync} disabled={syncing}>
            {syncing ? 'Subiendo...' : 'Sincronizar'}
          </button>
        </div>
      )}
```

- [ ] **Step 6: Build JSX**

```bash
cd "h:/Proyectos/Cuaderno ex app/frontend"
npm run build
```

Expected output: `Successfully compiled N files with Babel.` — no errors.

---

## Task 6: Update `frontend/screens_forms.jsx` — offline-aware saves + parcelas fallback

**Files:**
- Modify: `frontend/screens_forms.jsx`
- Build after: `cd "h:/Proyectos/Cuaderno ex app/frontend" && npm run build`

**Important pattern:** Only intercept `POST` (new records). `PUT` (edits) stay as direct fetch — we don't queue edits offline.

**For each form's `save()`, the change is:**
1. Split the fetch call: POST goes through `window.OfflineSync.post()`, PUT stays as `fetch()`.
2. Adjust the success toast to say "⏳ Guardado sin conexión" when `res._savedOffline` is true.

### 6a: Add parcelas offline fallback

The `useEffect` that loads parcelas (line ~137) fetches `/api/parcelas?pac_only=false`. Wrap it to cache on success and fallback to cache on failure.

- [ ] **Step 1: Find the parcelas fetch in TratamientoForm**

Look for (around line 135-140):
```js
        fetch('/api/parcelas?pac_only=false', { credentials: 'include' })
            .then(r => r.json())
            .then(d => setParcelas(Array.isArray(d) ? d : []))
            .catch(() => {});
```

Replace with:
```js
        fetch('/api/parcelas?pac_only=false', { credentials: 'include' })
            .then(r => r.json())
            .then(d => {
                const list = Array.isArray(d) ? d : [];
                setParcelas(list);
                if (window.OfflineDB && list.length > 0) window.OfflineDB.cacheParcelas(list);
            })
            .catch(() => {
                if (window.OfflineDB) {
                    window.OfflineDB.getCachedParcelas().then(cached => {
                        if (cached.length > 0) setParcelas(cached);
                    });
                }
            });
```

### 6b: TratamientoForm save() — lines ~289-293

- [ ] **Step 2: Replace the fetch call**

Find:
```js
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `/api/tratamientos/${record.id}` : '/api/tratamientos';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar el tratamiento'); setSaving(false); return; }
        onClose('✅ Tratamiento guardado');
```

Replace with:
```js
        const url = isEdit ? `/api/tratamientos/${record.id}` : '/api/tratamientos';
        const res = isEdit
            ? await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' })
            : await window.OfflineSync.post('/api/tratamientos', f);
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar el tratamiento'); setSaving(false); return; }
        onClose(res._savedOffline ? '⏳ Guardado sin conexión — se subirá al conectarte' : '✅ Tratamiento guardado');
```

### 6c: FertilizacionForm save() — lines ~448-451

- [ ] **Step 3: Replace the fetch call**

Find:
```js
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `/api/fertilizacion/${record.id}` : '/api/fertilizacion';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar el abono'); setSaving(false); return; }
```

Replace with:
```js
        const url = isEdit ? `/api/fertilizacion/${record.id}` : '/api/fertilizacion';
        const res = isEdit
            ? await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' })
            : await window.OfflineSync.post('/api/fertilizacion', f);
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar el abono'); setSaving(false); return; }
```

Find the `onClose` call right after (should be `onClose('✅ Abono guardado')` or similar) and add:
```js
        onClose(res._savedOffline ? '⏳ Guardado sin conexión — se subirá al conectarte' : '✅ Abono guardado');
```
(Replace whatever success message was there.)

### 6d: LaborForm save() — lines ~631-634

- [ ] **Step 4: Replace the fetch call**

Find:
```js
            const method = isEdit ? 'PUT' : 'POST';
            const url = isEdit ? `/api/labores/${record.id}` : '/api/labores';
            ...
            const res = await fetch(url, ...);
            if (!res.ok) { alert('Error al guardar. Inténtalo de nuevo.'); setSaving(false); return; }
```

Replace with:
```js
            const url = isEdit ? `/api/labores/${record.id}` : '/api/labores';
            const res = isEdit
                ? await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' })
                : await window.OfflineSync.post('/api/labores', f);
            if (!res.ok) { alert('Error al guardar. Inténtalo de nuevo.'); setSaving(false); return; }
```

Then find the `onClose(...)` call and replace it:
```js
            onClose(res._savedOffline ? '⏳ Guardado sin conexión — se subirá al conectarte' : '✅ Labor guardada');
```

### 6e: CosechaForm save() — lines ~741-744

- [ ] **Step 5: Replace the fetch call**

Find:
```js
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `/api/cosecha/${record.id}` : '/api/cosecha';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar la cosecha'); setSaving(false); return; }
```

Replace with:
```js
        const url = isEdit ? `/api/cosecha/${record.id}` : '/api/cosecha';
        const res = isEdit
            ? await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' })
            : await window.OfflineSync.post('/api/cosecha', f);
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar la cosecha'); setSaving(false); return; }
```

Then find the `onClose(...)` and replace:
```js
        onClose(res._savedOffline ? '⏳ Guardado sin conexión — se subirá al conectarte' : '✅ Cosecha guardada');
```

### 6f: CompraForm save() — lines ~849-858

- [ ] **Step 6: Replace the fetch call**

Find:
```js
        const method = isEdit ? 'PUT' : 'POST';
        const url    = isEdit ? `/api/compras/${record.id}` : '/api/compras';
        ...
        const res    = await fetch(url, ...);
        if (!res.ok) { setError(data.error || 'Error al guardar'); setSaving(false); return; }
```

Replace with:
```js
        const url = isEdit ? `/api/compras/${record.id}` : '/api/compras';
        const res = isEdit
            ? await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' })
            : await window.OfflineSync.post('/api/compras', f);
        if (!res.ok) { const d = await res.json().catch(() => ({})); setError(d.error || 'Error al guardar'); setSaving(false); return; }
```

Then find the `onClose(...)` and replace:
```js
        onClose(res._savedOffline ? '⏳ Guardado sin conexión — se subirá al conectarte' : '✅ Compra guardada');
```

### 6g: RiegoForm save() — lines ~992-995

- [ ] **Step 7: Replace the fetch call**

Find:
```js
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `/api/riego/${record.id}` : '/api/riego';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar'); setSaving(false); return; }
```

Replace with:
```js
        const url = isEdit ? `/api/riego/${record.id}` : '/api/riego';
        const res = isEdit
            ? await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' })
            : await window.OfflineSync.post('/api/riego', f);
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar'); setSaving(false); return; }
```

Then find the `onClose(...)` and replace:
```js
        onClose(res._savedOffline ? '⏳ Guardado sin conexión — se subirá al conectarte' : '✅ Riego guardado');
```

- [ ] **Step 8: Build JSX**

```bash
cd "h:/Proyectos/Cuaderno ex app/frontend"
npm run build
```

Expected: `Successfully compiled N files with Babel.` — no errors.

---

## Task 7: Verify end-to-end

**Files:** None

- [ ] **Step 1: Start the server**

```bash
cd "h:/Proyectos/Cuaderno ex app/backend"
python app.py
```

Expected: Flask running on http://127.0.0.1:5000

- [ ] **Step 2: Test offline banner**

Open http://127.0.0.1:5000 in Chrome DevTools.
Go to Application → Service Workers → check "Offline".
Reload the page.
Expected: app loads (served from SW cache) + orange "Sin cobertura" banner appears at top.

- [ ] **Step 3: Test offline record creation**

With DevTools still in offline mode, navigate to a form (e.g., ✏️ → Tratamiento fitosanitario).
Fill in all required fields and tap "Guardar".
Expected: toast shows "⏳ Guardado sin conexión — se subirá al conectarte".

- [ ] **Step 4: Verify record in IndexedDB**

In DevTools → Application → IndexedDB → cuaderno-offline-v1 → pending_records.
Expected: one record with `store_name: 'tratamientos'` and `api_url: '/api/tratamientos'`.

- [ ] **Step 5: Test auto-sync on reconnect**

Uncheck "Offline" in DevTools.
Expected: app auto-detects network, runs syncAll(), shows toast "✅ 1 registro sincronizado".
Check IndexedDB pending_records: should be empty.
Check backend DB: record should exist.

- [ ] **Step 6: Test manual sync button**

Go offline again, save a record.
Go online (but don't wait for auto-sync — navigate quickly).
The "⟳ 1 registro pendiente" banner should appear with "Sincronizar" button.
Tap the button. Expected: toast "✅ 1 registro sincronizado", banner disappears.

- [ ] **Step 7: Test parcelas cache**

Load the app online (clears offline mode).
Navigate to Parcelas screen or open any form with a parcela selector — parcelas load from API and get cached in IndexedDB.
Go offline. Open the Tratamiento form.
Expected: parcela selector is populated from cache (not empty).

---

## Out of scope (future work)

- History list offline (full historial from IndexedDB cache)
- Conflict resolution for edits made offline
- Background Sync API (when browser support improves on iOS)
- Abonado and cultivos-campaña offline (more complex data structures)
