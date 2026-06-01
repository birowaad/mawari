// static/service-worker.js
const CACHE_NAME = 'mawari-ar-v1';

// الملفات التي سيتم تخزينها مؤقتًا
const urlsToCache = [
  '/',
  '/static/style.css',
  '/offline'
];

// تثبيت Service Worker
self.addEventListener('install', event => {
  console.log('Service Worker installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Caching files...');
        return cache.addAll(urlsToCache);
      })
      .then(() => self.skipWaiting())
  );
});

// تفعيل Service Worker
self.addEventListener('activate', event => {
  console.log('Service Worker activated');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log('Deleting old cache:', cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

// جلب الملفات
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request)
          .then(response => {
            // لا تخزن الـ API calls مؤقتًا
            if (!event.request.url.includes('/qrcode') &&
                !event.request.url.includes('/heritage') &&
                event.request.method === 'GET') {
              return caches.open(CACHE_NAME)
                .then(cache => {
                  cache.put(event.request, response.clone());
                  return response;
                });
            }
            return response;
          })
          .catch(() => {
            return caches.match('/offline');
          });
      })
  );
});