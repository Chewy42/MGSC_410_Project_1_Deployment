self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open('real-estate-v1').then(function(cache) {
            return cache.addAll([
                '/',
                '/service.js',
                '/styles.css'
            ]);
        })
    );
});

self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request).then(function(response) {
            return response || fetch(event.request);
        })
    );
}); 