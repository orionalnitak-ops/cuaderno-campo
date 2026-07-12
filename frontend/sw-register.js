// Registro del service worker (PWA offline).
// Externalizado de index.html para poder aplicar un CSP sin 'unsafe-inline'
// en script-src. Cargar como <script src="/sw-register.js"></script>.
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () =>
    navigator.serviceWorker.register('/service-worker.js').catch(() => {})
  );
}
