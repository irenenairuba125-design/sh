// Served at /sw.js (see core/views.py:service_worker) so its scope defaults to "/" -
// serving it from /static/ would scope it to /static/ only and it couldn't control
// page navigations.

const SHELL_CACHE = 'qiora-shell-v1';
const LESSON_CACHE = 'qiora-lessons-v1';
const APP_SHELL = ['/', '/offline/'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name !== SHELL_CACHE && name !== LESSON_CACHE)
          .map((name) => caches.delete(name))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);

  // Downloaded lesson videos/notes: serve from cache first (that's the whole point of
  // "download for offline"), fall back to network if not yet downloaded.
  if (url.pathname.includes('/stream/') || url.pathname.includes('/notes/')) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
    return;
  }

  // Everything else: network-first so logged-in state and fresh content always win,
  // falling back to a cached copy or the offline page when there's no connection.
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (event.request.mode === 'navigate' || response.ok) {
          const copy = response.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() =>
        caches.match(event.request).then((cached) => {
          if (cached) return cached;
          if (event.request.mode === 'navigate') return caches.match('/offline/');
          return Response.error();
        })
      )
  );
});

// Triggered from a lesson page's "Download for offline" button.
self.addEventListener('message', (event) => {
  if (!event.data || event.data.type !== 'CACHE_LESSON') return;
  const { urls, lessonId } = event.data;

  event.waitUntil(
    (async () => {
      const cache = await caches.open(LESSON_CACHE);
      let ok = true;
      for (const url of urls) {
        try {
          const response = await fetch(url);
          if (response.ok) {
            await cache.put(url, response.clone());
          } else {
            ok = false;
          }
        } catch (e) {
          ok = false;
        }
      }
      const clients = await self.clients.matchAll();
      clients.forEach((client) => client.postMessage({ type: 'CACHE_LESSON_DONE', lessonId, ok }));
    })()
  );
});
