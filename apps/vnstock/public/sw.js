/* eslint-disable no-restricted-globals */
// Vnstock PWA Service Worker
const CACHE_NAME = 'vnstock-pwa-v1.0.0';

// Essential assets to cache during installation
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.png',
  '/favicon.ico',
  '/icon-192.png',
  '/icon-512.png',
  '/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS).catch((err) => {
        // Continue even if some individual static asset fails to cache
        console.warn('[SW] Pre-caching asset warning:', err);
      });
    }).then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter(name => name.startsWith('vnstock-pwa-') && name !== CACHE_NAME)
          .map(name => caches.delete(name)),
      );
    }).then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle GET requests and http/https schemes
  if (request.method !== 'GET' || !url.protocol.startsWith('http')) {
    return;
  }

  // Do not cache API endpoints or websocket streams
  if (
    url.pathname.startsWith('/api')
    || url.hostname.includes('api')
    || request.headers.get('Upgrade') === 'websocket'
  ) {
    return;
  }

  // 1. Navigation requests (HTML pages): Network-first with cache fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return response;
        })
        .catch(async () => {
          const cachedResponse = await caches.match(request);
          if (cachedResponse)
            return cachedResponse;
          return caches.match('/') || caches.match('/index.html');
        }),
    );
    return;
  }

  // 2. Static Expo assets (JS bundles, CSS, fonts, images): Cache-first or Stale-while-revalidate
  const isStaticAsset
    = url.pathname.includes('/_expo/static/')
      || url.pathname.endsWith('.js')
      || url.pathname.endsWith('.css')
      || url.pathname.endsWith('.woff2')
      || url.pathname.endsWith('.ttf')
      || url.pathname.endsWith('.png')
      || url.pathname.endsWith('.jpg')
      || url.pathname.endsWith('.ico')
      || url.pathname.endsWith('.svg');

  if (isStaticAsset) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) {
          // Revalidate in background
          fetch(request)
            .then((networkResponse) => {
              if (networkResponse && networkResponse.status === 200) {
                caches.open(CACHE_NAME).then(cache => cache.put(request, networkResponse));
              }
            })
            .catch(() => {});
          return cachedResponse;
        }

        return fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return networkResponse;
        });
      }),
    );
    return;
  }

  // Default: Network with fallback to cache
  event.respondWith(
    fetch(request)
      .then((networkResponse) => {
        return networkResponse;
      })
      .catch(() => caches.match(request)),
  );
});

// Allow client app to trigger skipWaiting
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
