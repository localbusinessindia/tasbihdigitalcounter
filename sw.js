const CACHE_NAME = 'tasbih-digital-counter-v7';
const PRECACHE_URLS = ["/", "/index.html", "/content.css", "/manifest.webmanifest", "/icon.svg", "/icon-192.png", "/icon-512.png", "/og-default.png", "/404.html", "/astaghfirullah.html", "/subhanallah.html", "/dhikr-after-salah.html", "/tasbih-before-sleep.html", "/morning-evening-adhkar.html", "/99-names-of-allah.html", "/what-is-tasbih.html", "/islamic-dates.html", "/about.html", "/contact.html", "/privacy-policy.html", "/disclaimer.html", "/sitemap.xml", '/alhamdulillah.html',
  '/allahu-akbar.html',
  '/la-ilaha-illallah.html',
  '/salawat-durood.html',
];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).then(response => {
      const copy = response.clone(); caches.open(CACHE_NAME).then(cache => cache.put(request, copy)); return response;
    }).catch(() => caches.match(request).then(cached => cached || caches.match('/404.html'))));
    return;
  }
  event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
    const copy = response.clone(); caches.open(CACHE_NAME).then(cache => cache.put(request, copy)); return response;
  })));
});
