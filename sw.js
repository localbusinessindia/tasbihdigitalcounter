const CACHE_NAME = 'tasbih-digital-counter-v14';
const PRECACHE_URLS = ["/", "/content.css", "/voice-guide.js", "/routines.js", "/names.js", "/start-counter.js", "/audio/manifest.json", "/digital-tasbih-beginner-guide", "/digital-vs-physical-tasbih", "/daily-dhikr-habit", "/add-tasbih-to-home-screen", "/counter.js", "/i18n.js", "/consent.js", "/ar", "/ur", "/id", "/tr", "/dhikr-list", "/guides", "/manifest.webmanifest", "/icon.svg", "/icon-192.png", "/icon-512.png", "/icon-maskable-512.png", "/og-default.png", "/404.html", "/astaghfirullah", "/subhanallah", "/dhikr-after-salah", "/tasbih-before-sleep", "/morning-evening-adhkar", "/99-names-of-allah", "/99-names-of-allah.pdf", "/what-is-tasbih", "/islamic-dates", "/about", "/contact", "/privacy-policy", "/disclaimer", "/sitemap.xml", '/alhamdulillah',
  '/allahu-akbar',
  '/la-ilaha-illallah',
  '/salawat-durood',
];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin || request.headers.has('range')) return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).then(response => {
      if (response.ok && !response.redirected) { const copy = response.clone(); caches.open(CACHE_NAME).then(cache => cache.put(request, copy)); } return response;
    }).catch(() => caches.match(request).then(cached => cached || caches.match('/404.html'))));
    return;
  }
  event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
    if (response.ok) { const copy = response.clone(); caches.open(CACHE_NAME).then(cache => cache.put(request, copy)); } return response;
  })));
});
