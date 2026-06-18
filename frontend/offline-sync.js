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
    window.OfflineDB.countAllPending()
      .then(count => { _listeners.forEach(fn => fn(count)); })
      .catch(() => {}); // badge update is best-effort
  }

  window.OfflineSync = {
    // Subscribe to pending count changes
    onStatusChange(fn) {
      _listeners.push(fn);
      return () => {
        const idx = _listeners.indexOf(fn);
        if (idx !== -1) _listeners.splice(idx, 1);
      };
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
      let pending;
      try {
        pending = await window.OfflineDB.getAllPending();
      } catch (_e) {
        return { synced: 0, failed: 0 };
      }
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
            // 4xx = permanently invalid, remove to prevent infinite queue
            if (res.status >= 400 && res.status < 500) {
              await window.OfflineDB.deletePending(rec.local_id);
            }
          }
        } catch (_e) {
          failed += (pending.length - synced - failed); // count all unprocessed
          break; // Network gone again — stop trying
        }
      }

      notifyListeners();
      return { synced, failed };
    },
  };
})();
