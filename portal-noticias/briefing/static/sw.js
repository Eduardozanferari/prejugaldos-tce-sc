// Service worker mínimo: permite instalar o portal no celular. Não guarda páginas em cache,
// para que o conteúdo exibido seja sempre o mais recente e protegido pela senha.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
