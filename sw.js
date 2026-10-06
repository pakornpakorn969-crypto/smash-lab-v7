// Service Worker ขั้นพื้นฐานสำหรับรองรับ PWA Install
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
  // ให้ดึงข้อมูลตามปกติผ่าน Network
  event.respondWith(fetch(event.request));
});