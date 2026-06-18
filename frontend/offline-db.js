// IndexedDB wrapper — exposes window.OfflineDB
(function () {
  const DB_NAME = 'cuaderno-offline-v1';
  const DB_VERSION = 1;
  let _db = null;
  let _dbPromise = null;

  function openDB() {
    if (_dbPromise) return _dbPromise;
    _dbPromise = new Promise((resolve, reject) => {
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
      req.onsuccess = (e) => {
        _db = e.target.result;
        _db.onversionchange = () => { _db.close(); _db = null; _dbPromise = null; };
        resolve(_db);
      };
      req.onerror = () => { _dbPromise = null; reject(req.error); };
    });
    return _dbPromise;
  }

  function tx(storeName, mode, fn) {
    return openDB().then(db => new Promise((resolve, reject) => {
      const transaction = db.transaction(storeName, mode);
      const store = transaction.objectStore(storeName);
      fn(store);
      transaction.oncomplete = () => resolve();
      transaction.onerror   = () => reject(transaction.error);
      transaction.onabort   = () => reject(transaction.error);
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
        t.oncomplete = () => resolve();
        t.onerror = () => console.warn('[OfflineDB] cacheParcelas failed:', t.error);
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
