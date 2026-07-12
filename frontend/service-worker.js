const CACHE_NAME = 'cuaderno-cache-v46';

const APP_SHELL = [
  '/',
  '/manifest.json',
  '/offline-db.js',
  '/offline-sync.js',
  '/nlp-local.js',
  '/sw-register.js',
  '/dist/screens_auth.js',
  '/dist/screens_lopd.js',
  '/dist/screens_home.js',
  '/dist/screens_forms.js',
  '/dist/screens_parcelas.js',
  '/dist/screens_history.js',
  '/dist/screens_settings.js',
  '/dist/screens_admin.js',
  '/dist/screens_planes.js',
  '/dist/screens_onboarding.js',
  '/dist/app.js',
  'https://unpkg.com/react@18.3.1/umd/react.production.min.js',
  'https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k.startsWith('cuaderno-cache-') && k !== CACHE_NAME)
            .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Nunca interceptar API
  if (url.pathname.startsWith('/api/')) return;

  // CDN (React/Leaflet de unpkg): cache-first — el SW los pre-cachea en install.
  // SOLO unpkg: el resto de peticiones cross-origin (tiles WMS del mapa SIGPAC/IGN,
  // fuentes de Google, Open-Meteo) NO se interceptan y las carga el navegador de
  // forma nativa. Interceptarlas convertía cargas <img> (gobernadas por img-src)
  // en fetch() del SW (gobernadas por connect-src) → el CSP bloqueaba las tiles y
  // dejaba el mapa en blanco. Además cachear tiles por bbox cache-first era indeseable.
  if (url.origin !== self.location.origin) {
    if (url.hostname === 'unpkg.com') {
      event.respondWith(
        caches.match(event.request).then(cached => {
          if (cached) return cached;
          return fetch(event.request).then(response => {
            if (response.ok) {
              caches.open(CACHE_NAME).then(cache => cache.put(event.request, response.clone()));
            }
            return response;
          });
        })
      );
    }
    return; // resto cross-origin: el navegador lo gestiona (img-src/font-src)
  }

  // Navegación (HTML): network-first, caída a caché del shell
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put('/', clone));
          return response;
        })
        .catch(() => caches.match('/'))
    );
    return;
  }

  // Assets estáticos (JSX, iconos, manifest): stale-while-revalidate
  event.respondWith(
    caches.open(CACHE_NAME).then(cache =>
      cache.match(event.request).then(cached => {
        const networkFetch = fetch(event.request)
          .then(response => {
            if (response.ok) cache.put(event.request, response.clone());
            return response;
          })
          .catch(() => cached);
        return cached || networkFetch;
      })
    )
  );
});

// Notificar a los clientes cuando hay una nueva versión disponible
self.addEventListener('message', event => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});

// ── Notificaciones push ──────────────────────────────────────
self.addEventListener('push', event => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch {}
  const title = data.title || '⚠️ Alerta meteorológica';
  const options = {
    body: data.body || 'Nueva alerta AEMET para tu zona',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-72.png',
    data: { url: data.url || '/' },
    requireInteraction: true,
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(cls => {
      const existing = cls.find(c => c.url.includes(self.location.origin));
      if (existing) return existing.focus();
      return clients.openWindow(url);
    })
  );
});
