/* SocialSolve Service Worker v1 */
const CACHE = 'socialsolve-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/socialsolve.css',
  '/static/manifest.json'
];

// Install — cache static shell
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch — network-first for API, cache-first for static
self.addEventListener('fetch', e => {
  const { request } = e;

  // Skip non-GET and cross-origin
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // API routes → network only, no cache
  if (url.pathname.startsWith('/api/')) return;

  // Static assets → cache-first
  if (
    url.pathname.startsWith('/static/') ||
    url.pathname.startsWith('/uploads/')
  ) {
    e.respondWith(
      caches.match(request).then(cached =>
        cached ||
        fetch(request).then(resp => {
          if (resp.ok) {
            const clone = resp.clone();
            caches.open(CACHE).then(cache => cache.put(request, clone));
          }
          return resp;
        })
      )
    );
    return;
  }

  // HTML pages → network-first with cache fallback
  e.respondWith(
    fetch(request)
      .then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE).then(cache => cache.put(request, clone));
        }
        return resp;
      })
      .catch(() => caches.match(request))
  );
});

// Push notification placeholder
self.addEventListener('push', e => {
  const data = e.data?.json() || {};
  self.registration.showNotification(data.title || 'SocialSolve', {
    body: data.body || 'New update from SocialSolve',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-192.png',
    tag: 'socialsolve-notif',
    data: data.url || '/'
  });
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(clients.openWindow(e.notification.data));
});
