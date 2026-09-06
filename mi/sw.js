/* ==== ENGINE:BEGIN sw-header ==== */
// App-shell + app-data cache. Never serve live district/roster API responses
// stale — a stale roster could name the wrong officeholder, and this app's
// rule is that officeholder data is never guessed or served stale. Bump
// CACHE_NAME whenever SHELL_URLS, GEOMETRY_URLS, or ROSTER_URLS change so a
// removed entry can't live forever; the activate handler deletes every
// other-named cache.
//
// The config section below is this fork's METRO block (docs/ENGINE_SYNC.md):
// a per-city cache name, the shell assets, and the fork's data/app/*.json
// files split by caching policy — ~static boundary geometry (cache-first,
// precached) vs officeholder rosters (network-first, never stale). Every file
// under data/app/ must appear in exactly one of the two data lists;
// validate_index.py enforces it. The handler logic below the config is shared
// engine and stays byte-identical across every metro fork.
//
// "./" and "./index.html" resolve to the same GitHub Pages document, so we
// precache only the canonical "./" — caching both stored two ~112 KB-gzip
// copies under two keys and re-downloaded the page at install. The manifest's
// start_url is still ./index.html and a deep bookmark may hit /index.html
// directly; the navigate-request branch in the fetch handler serves the cached
// "./" shell for any such navigation, so offline boot still works either way.
/* ==== ENGINE:END sw-header ==== */

/* ==== METRO:BEGIN sw-config ==== */
// (Shell version history — grow this comment as the shell changes; the
// template starts at -v1: the app shell, icons, and the starter data
// files bootstrap_state.py builds.)
/* ==== GENERATED:BEGIN sw-metro-config ==== */
const CACHE_NAME = "districtry-mi-shell-v7";

const SHELL_URLS = [
  "./",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/apple-touch-icon.png",
  "./icons/icon-maskable-512.png",
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js",
  "https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/5.24.0/maplibre-gl.min.js",
  "./vendor/leaflet-maplibre-gl.js",
];

// Boundary geometry (data/app/*.json, fetched lazily on first toggle).
// Boundaries change ~once a decade, so serve them cache-first (instant, and
// works offline) and refresh in the background. Precached at install so
// those layers work offline.
const GEOMETRY_URLS = [
  "./data/app/metro-outline.json",
  "./data/app/state-counties.json",
  "./data/app/congress-districts.json",
  "./data/app/mi-senate-districts.json",
  "./data/app/mi-house-districts.json",
  "./data/app/mi-commissioner-districts.json",
  "./data/app/mi-precincts.json",
  "./data/app/mi-detroit-council-districts.json",
  "./data/app/mi-grand-rapids-wards.json",
  "./data/app/mi-warren-wards.json",
];

// Roster/officeholder data (also in data/app/) is refreshed by the weekly CI
// and must never be served stale — network-first, with the cached copy only
// as an offline fallback. Same freshness rule as the shell.
const ROSTER_URLS = [
  "./data/app/congress-roster.json",
  "./data/app/mi-senate-members.json",
  "./data/app/mi-house-members.json",
  "./data/app/coverage-gaps.json",
  "./data/app/mi-detroit-council-members.json",
  "./data/app/mi-grand-rapids-council-members.json",
];
/* ==== GENERATED:END sw-metro-config ==== */
/* ==== METRO:END sw-config ==== */

/* ==== ENGINE:BEGIN sw-handlers ==== */
const PRECACHE_URLS = SHELL_URLS.concat(GEOMETRY_URLS);

function inList(href, list) {
  return list.some((url) => new URL(url, self.registration.scope).href === href);
}

self.addEventListener("install", (event) => {
  // Cache each URL independently so one unreachable resource (e.g. a CDN blip)
  // doesn't fail the whole install — addAll() would abort atomically.
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      Promise.all(PRECACHE_URLS.map((url) => cache.add(url).catch(() => {})))
    )
  );
  self.skipWaiting();
});

// Retire MY OWN superseded caches, and only those.
//
// CacheStorage is per-ORIGIN, not per-scope, and this origin now serves several
// instances side by side (/il/, /ny/, /ca/), each with its own worker and its
// own cache. The original sweep here was "delete every key that is not mine",
// which was correct while an origin held exactly one app and becomes mutual
// destruction the moment it holds two: every visit to one instance would wipe
// the others' precached boundary geometry — tens of megabytes, re-fetched on
// their next visit, forever.
//
// A cache belongs to this instance when it shares this instance's name minus
// its version suffix, which every instance's CACHE_NAME carries ("…-v4",
// "…-v9", "…-v1"). Anything else on the origin belongs to a sibling and is not
// ours to delete. Cross-instance cleanup, where it is ever needed, is done
// explicitly and by exact name — see the root kill switch in /sw.js.
self.addEventListener("activate", (event) => {
  const mine = CACHE_NAME.replace(/-v\d+$/, "");
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key.startsWith(mine + "-v"))
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Network-first: online visitors always get the current copy, and the cache is
// refreshed as a side effect; offline falls back to the last good cached copy.
function networkFirst(request) {
  return fetch(request)
    .then((response) => {
      if (response.ok) {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
      }
      return response;
    })
    .catch(() => caches.match(request));
}

// Cache-first with background revalidation: serve the cached copy instantly
// (or fetch it the first time), and quietly refresh the cache for next time.
function cacheFirst(request) {
  return caches.match(request).then((cached) => {
    const network = fetch(request)
      .then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(() => cached);
    return cached || network;
  });
}

self.addEventListener("fetch", (event) => {
  const href = new URL(event.request.url).href;

  // Page navigations (including an installed PWA's ./index.html start_url and
  // any deep /index.html bookmark): network-first so an online visitor always
  // gets the current page, falling back offline to the cached canonical shell
  // ("./") — which is why the duplicate "./index.html" precache entry could be
  // dropped without losing offline boot.
  if (event.request.mode === "navigate") {
    event.respondWith(
      networkFirst(event.request).then(
        (resp) => resp || caches.match(new URL("./", self.registration.scope).href)
      )
    );
    return;
  }

  // Shell and roster data: never stale online, cached only for offline boot.
  if (inList(href, SHELL_URLS) || inList(href, ROSTER_URLS)) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  // Boundary geometry: ~static, so cache-first for instant toggles + offline.
  if (inList(href, GEOMETRY_URLS)) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // Everything else (all live district/roster API calls) hits the network normally.
});
/* ==== ENGINE:END sw-handlers ==== */
