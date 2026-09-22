/*
  admin-service-worker.js — necessário para o admin.html ser instalável.
  Cache mínimo: só a casca estática. NUNCA cacheia respostas de /admin/*
  (dados administrativos não devem ficar em cache do navegador).
*/

const CACHE_NOME = "nome-limpo-admin-v1";
const ARQUIVOS_ESSENCIAIS = [
  "./admin.html",
  "./admin-manifest.json",
  "./icons/admin-icon-192.png",
  "./icons/admin-icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NOME).then((cache) => cache.addAll(ARQUIVOS_ESSENCIAIS)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((chaves) => Promise.all(chaves.filter((c) => c !== CACHE_NOME).map((c) => caches.delete(c))))
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // Nenhuma chamada de API (login, /admin/*, /auth/*) é cacheada — sempre rede.
  const ehChamadaDeApi = ["/admin", "/auth", "/health"].some((prefixo) => url.pathname.startsWith(prefixo));
  if (ehChamadaDeApi) return;

  event.respondWith(caches.match(event.request).then((resp) => resp || fetch(event.request)));
});
