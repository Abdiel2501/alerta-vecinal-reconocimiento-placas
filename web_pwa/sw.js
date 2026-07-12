const CACHE_NAME = 'alertavecinal-v9';
const APP_SHELL = [
  'index.html',
  'styles.css',
  'app.js',
  'manifest.json',
  'icon.png',
  'https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.1.1/crypto-js.min.js',
  'https://accounts.google.com/gsi/client'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Service Worker] Cacheando App Shell');
      return cache.addAll(APP_SHELL);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(keyList.map((key) => {
        if (key !== CACHE_NAME) {
          console.log('[Service Worker] Borrando caché antiguo', key);
          return caches.delete(key);
        }
      }));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Ignorar peticiones WebSocket y otras URLs externas o dinámicas para no interferir
  if (event.request.url.startsWith('ws://') || event.request.url.startsWith('wss://')) {
    return;
  }
  
  // Responder con caché o red
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
