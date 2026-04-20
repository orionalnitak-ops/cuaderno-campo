const CACHE_NAME = 'cuaderno-cache-v10';
const urlsToCache = [
  '/',
  '/index.html',
  '/app.jsx',
  '/screens_auth.jsx',
  '/screens_home.jsx',
  '/screens_forms.jsx',
  '/screens_history.jsx',
  '/screens_settings.jsx',
  '/screens_admin.jsx',
  '/manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(cacheName => {
          return cacheName.startsWith('cuaderno-cache-') && cacheName !== CACHE_NAME;
        }).map(cacheName => {
          return caches.delete(cacheName);
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  if(event.request.url.includes('/api/')) {
      // Don't cache API requests, just fetch
      return;
  }
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) return response;
        return fetch(event.request);
      })
  );
});
