/* Prasad Menu — Service Worker
   Caches the HTML, all CSVs, and icons so the app works offline.
   Bump CACHE_VERSION when you ship changes so old caches are wiped. */

const CACHE_VERSION = 'prasad-v20';
const ASSETS = [
  './',
  './index.html',
  './prasad_planner_liquid.html',
  './prasad_planner.html',
  './manifest.json',
  './menu.csv',
  './icons/deities.jpg',
  './icons/logo.jpg',
  './icons/icon-120.png',
  './icons/icon-152.png',
  './icons/icon-167.png',
  './icons/icon-180.png',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-1024.png',
  './dishes/Alu_Gobi_Matar.csv',
  './dishes/Alu_gobi_sabji.csv',
  './dishes/Chole_paneer.csv',
  './dishes/Dahi_Bundi_Raita.csv',
  './dishes/Dahi_Kakudi_Salad.csv',
  './dishes/Dalma.csv',
  './dishes/Mango_Halwa.csv',
  './dishes/Matar_paneer.csv',
  './dishes/Mitha_Dali.csv',
  './dishes/Muga_Khichdi.csv',
  './dishes/Navratna_Korma.csv',
  './dishes/Plain_Dali.csv',
  './dishes/Plain_Rice.csv',
  './dishes/Rice_Khiri.csv',
  './dishes/Saga_muga.csv',
  './dishes/Simei_Khiri.csv',
  './dishes/Suji_Halwa.csv',
  './dishes/Tomato_Khajuri_khata.csv',
  './dishes/Veggie_chips.csv'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then(cache => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_VERSION).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;

  // Never cache the PDF-save endpoint — must hit the live server
  if (req.url.includes('/save-pdf')) return;

  // Cache-first for everything else
  event.respondWith(
    caches.match(req).then(cached => {
      if (cached) return cached;
      return fetch(req).then(resp => {
        // Cache successful same-origin GETs on the fly
        if (req.method === 'GET' && resp.ok && new URL(req.url).origin === self.location.origin) {
          const respClone = resp.clone();
          caches.open(CACHE_VERSION).then(c => c.put(req, respClone));
        }
        return resp;
      }).catch(() => caches.match('./index.html'));
    })
  );
});
