// Offline support: app shell from cache, listing data always fresh when online.
const CACHE = 'wohnungssuche-v1'

self.addEventListener('install', () => self.skipWaiting())

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return

  // Network first, cache as fallback – so the app also opens without signal.
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone()
          const key = url.pathname.endsWith('data.json') ? new Request(url.pathname) : event.request
          caches.open(CACHE).then((cache) => cache.put(key, copy))
        }
        return response
      })
      .catch(() =>
        caches.match(url.pathname.endsWith('data.json') ? new Request(url.pathname) : event.request),
      ),
  )
})
