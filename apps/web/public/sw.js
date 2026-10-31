/* Aureon PWA service worker (SCR-28, R-DEC-25).
 * Tiny on purpose: cache-first for the static app shell only; network-first (never cached) for the
 * API so data stays fresh and no credentialed response is stored. */
const SHELL = "aureon-shell-v1";
const SHELL_URLS = ["/", "/manifest.webmanifest", "/favicon.ico"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll(SHELL_URLS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== SHELL).map((k) => caches.delete(k)))).then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return; // never cache mutations
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // Never cache API / auth traffic — always go to the network (fresh data, no credential storage).
  if (url.pathname.startsWith("/api/")) return;
  if (req.mode === "navigate" || SHELL_URLS.includes(url.pathname)) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(SHELL).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      }).catch(() => caches.match("/"))),
    );
  }
});
