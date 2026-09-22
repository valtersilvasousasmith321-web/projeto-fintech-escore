/*
  service-worker.js

  Necessário para o app ser instalável como PWA (o navegador só mostra
  o prompt de instalação se existir um service worker registrado).
  Cache mínimo: só o essencial pra abrir offline depois de instalado.
*/

const CACHE_NOME = "nome-limpo-v1";
const ARQUIVOS_ESSENCIAIS = [
  "./index.html",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NOME).then((cache) => cache.addAll(ARQUIVOS_ESSENCIAIS))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((chaves) =>
      Promise.all(chaves.filter((c) => c !== CACHE_NOME).map((c) => caches.delete(c)))
    )
  );
});

self.addEventListener("fetch", (event) => {
  // Só serve do cache os arquivos estáticos do app (HTML/ícones).
  // Chamadas para /score, /auth, /negociacao etc. sempre vão direto
  // pra rede — dado financeiro nunca deve vir de cache.
  const url = new URL(event.request.url);
  const ehChamadaDeApi = ["/score", "/auth", "/negociacao", "/marketplace", "/health"].some(
    (prefixo) => url.pathname.startsWith(prefixo)
  );

  if (ehChamadaDeApi) {
    return; // deixa passar direto pra rede, sem interceptar
  }

  event.respondWith(
    caches.match(event.request).then((respostaCache) => respostaCache || fetch(event.request))
  );
});
