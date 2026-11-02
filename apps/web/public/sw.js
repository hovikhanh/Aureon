/* Aureon PWA service worker (SCR-28, R-DEC-25).
 * Tiny on purpose: network-first for page navigations (fresh HTML always wins online; cache is an
 * OFFLINE-only fallback — a UI change must never be masked by a stale cached page), cache-first for
 * a few static shell assets, network-only (never cached) for API/auth so data stays fresh and no
 * credentialed response is stored. */
const SHELL = "aureon-shell-v2";
const SHELL_URLS = ["/manifest.webmanifest", "/favicon.ico"];

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
  // Page navigations: NETWORK-FIRST. Online → always the live HTML (UI changes propagate instantly);
  // offline → the last-seen page for this URL, else the cached root shell. Pages are not stored
  // (avoid caching credentialed/stale HTML like /login); only a minimal offline fallback is kept.
  if (req.mode === "navigate") {
    event.respondWith(fetch(req).catch(() => caches.match(req).then((hit) => hit || caches.match("/"))));
    return;
  }
  // Static shell assets: cache-first (immutable-ish), refreshed in the background on miss.
  if (SHELL_URLS.includes(url.pathname)) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(SHELL).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      })),
    );
  }
});
