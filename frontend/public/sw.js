// Township One - Resident Interface PWA Service Worker
// Service worker implementing:
// - App shell pre-caching (HTML, manifest, icons)
// - Dynamic runtime caching for hashed frontend assets (/assets/*.js, /assets/*.css)
// - Strict network-only bypass for /api/* requests (never caches private or financial data)
// - Offline navigation fallback to cached /index.html shell

const CACHE_NAME = 'township-one-shell-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/icon.svg',
  '/favicon.ico'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // STRICT SECURITY RULE: Never cache private /api/ requests or financial transactions!
  if (url.pathname.startsWith('/api/')) {
    return; // Pass through directly to network
  }

  // Handle navigation requests: Network first, fallback to cached /index.html
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match('/index.html'))
    );
    return;
  }

  // Handle static assets (/assets/*): Cache-first with network fallback and cache-on-fetch
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(event.request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
          }
          return networkResponse;
        });
      })
    );
    return;
  }

  // Default: Network first, fallback to cache for shell assets
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
