/**
 * 34.6.2 — Service Worker do Portal do Comprador
 * Estratégia: Cache-first para assets estáticos, Network-first para páginas.
 */

const CACHE_NAME = 'portal-gc-v1';

const ASSETS_TO_CACHE = [
    '/portal/',
    '/portal/boletos/',
    '/portal/contratos/',
    '/portal/meus-dados/',
    '/static/vendor/materialize/css/materialize.min.css',
    '/static/vendor/fontawesome/css/all.min.css',
    '/static/vendor/materialize/js/materialize.min.js',
];

// Install: pre-cache assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS_TO_CACHE)).catch(() => {})
    );
    self.skipWaiting();
});

// Activate: limpar caches antigos
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

// Fetch: Network-first para páginas HTML, Cache-first para assets
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Ignora requests fora do scope do portal e não-GET
    if (request.method !== 'GET') return;
    if (!url.pathname.startsWith('/portal/') && !url.pathname.startsWith('/static/')) return;

    // Assets estáticos — Cache-first
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(request).then(cached => cached || fetch(request).then(resp => {
                if (resp.ok) {
                    const clone = resp.clone();
                    caches.open(CACHE_NAME).then(c => c.put(request, clone));
                }
                return resp;
            }))
        );
        return;
    }

    // Páginas HTML — Network-first com fallback para cache
    event.respondWith(
        fetch(request)
            .then(resp => {
                if (resp.ok) {
                    const clone = resp.clone();
                    caches.open(CACHE_NAME).then(c => c.put(request, clone));
                }
                return resp;
            })
            .catch(() => caches.match(request))
    );
});

// Push: exibe notificação recebida do servidor
self.addEventListener('push', event => {
    let data = {};
    try { data = event.data ? event.data.json() : {}; } catch (e) {}

    const titulo = data.titulo || 'Portal do Comprador';
    const corpo  = data.corpo  || 'Você tem uma nova notificação.';
    const url    = data.url    || '/portal/';
    const icone  = data.icone  || '/static/img/icon-192.png';

    event.waitUntil(
        self.registration.showNotification(titulo, {
            body: corpo,
            icon: icone,
            badge: icone,
            data: { url },
        })
    );
});

// Notification click: abre/foca a aba do portal
self.addEventListener('notificationclick', event => {
    event.notification.close();
    const destino = event.notification.data?.url || '/portal/';
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
            for (const client of clientList) {
                if (client.url.includes('/portal/') && 'focus' in client) {
                    client.navigate(destino);
                    return client.focus();
                }
            }
            return clients.openWindow(destino);
        })
    );
});
