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
/* ==== TEMPLATE:BEGIN sw-version-history ==== */
// (-v3 dropped the duplicate "./index.html" shell entry; -v4 added the two
// roster files missing from ROSTER_URLS; -v5 added the water-taxi marker
// icon shown when a point lands on water; -v6/-v7 added the Will County
// outline + board roster; -v8 added the Cook County seal marker icon shown
// for a point in Cook County outside the City of Chicago; -v9 dropped
// leaflet.css from the shell — it's now inlined in index.html (was a
// render-blocking <link>), so the page no longer requests it; -v10 added the
// pre-built legislative-district geometry (congress / il-senate / il-house),
// moved off live TIGERweb to same-origin cache-first data/app files; -v11
// precached the collar-county seal markers (Kane, Lake, Will) alongside Cook
// (-v8) — the counties in this Chicago app's usual footprint. Five more seals
// ship for downstate counties (Hamilton, Macon, Saline, St. Clair, Washington)
// but are intentionally left out of the shell precache: they load on demand
// (network, then the name-badge fallback offline), so rarely-seen markers don't
// weigh down every install; -v12 added the hand-curated early-voting-sites.json
// roster backing the Early Voting Site nearest-point layer — network-first,
// refreshed per election.)
/* ==== TEMPLATE:END sw-version-history ==== */
/* ==== GENERATED:BEGIN sw-metro-config ==== */
const CACHE_NAME = "districtry-il-shell-v16";

const SHELL_URLS = [
  "./",
  "./sources.html",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-maskable-512.png",
  "./icons/apple-touch-icon.png",
  "./icons/water-taxi.png",
  "./icons/seals/cook-county.png",
  "./icons/seals/kane.png",
  "./icons/seals/lake.png",
  "./icons/seals/will.png",
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js",
  "https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/5.24.0/maplibre-gl.min.js",
  "./vendor/leaflet-maplibre-gl.js",
];

// Boundary geometry (data/app/*.json, fetched lazily on first toggle).
// Boundaries change ~once a decade, so serve them cache-first (instant, and
// works offline) and refresh in the background. Precached at install so
// those layers work offline.
const GEOMETRY_URLS = [
  "./data/app/adams-county-outline.json",
  "./data/app/alexander-county-outline.json",
  "./data/app/belvidere-city-outline.json",
  "./data/app/bond-county-outline.json",
  "./data/app/boone-county-outline.json",
  "./data/app/boone-library-districts.json",
  "./data/app/boone-park-districts.json",
  "./data/app/grundy-fire-districts.json",
  "./data/app/grundy-library-districts.json",
  "./data/app/grundy-park-districts.json",
  "./data/app/woodford-fire-districts.json",
  "./data/app/woodford-library-districts.json",
  "./data/app/woodford-park-districts.json",
  "./data/app/brown-county-outline.json",
  "./data/app/bureau-county-outline.json",
  "./data/app/calhoun-county-outline.json",
  "./data/app/carroll-county-board-districts.json",
  "./data/app/carroll-county-outline.json",
  "./data/app/macoupin-library-districts.json",
  "./data/app/carroll-library-districts.json",
  "./data/app/cass-county-board-districts.json",
  "./data/app/cass-county-outline.json",
  "./data/app/cass-precincts.json",
  "./data/app/ccbr-districts.json",
  "./data/app/champaign-county-outline.json",
  "./data/app/christian-county-outline.json",
  "./data/app/clark-county-board-districts.json",
  "./data/app/clark-county-outline.json",
  "./data/app/calhoun-precincts.json",
  "./data/app/clark-precincts.json",
  "./data/app/clay-county-outline.json",
  "./data/app/clay-county-board-districts.json",
  "./data/app/clinton-county-outline.json",
  "./data/app/coles-county-outline.json",
  "./data/app/congress-districts.json",
  "./data/app/cook-fire-districts.json",
  "./data/app/crawford-county-board-districts.json",
  "./data/app/crawford-county-outline.json",
  "./data/app/crawford-precincts.json",
  "./data/app/cumberland-county-outline.json",
  "./data/app/cumberland-precincts.json",
  "./data/app/dekalb-county-outline.json",
  "./data/app/dewitt-county-board-districts.json",
  "./data/app/dewitt-county-outline.json",
  "./data/app/douglas-county-outline.json",
  "./data/app/dupage-county-outline.json",
  "./data/app/edgar-county-board-districts.json",
  "./data/app/edgar-county-outline.json",
  "./data/app/edgar-precincts.json",
  "./data/app/franklin-county-board-districts.json",
  "./data/app/franklin-precincts.json",
  "./data/app/clinton-county-board-districts.json",
  "./data/app/warren-county-board-districts.json",
  "./data/app/warren-precincts.json",
  "./data/app/knox-county-board-districts.json",
  "./data/app/edwards-county-outline.json",
  "./data/app/effingham-county-outline.json",
  "./data/app/fayette-county-outline.json",
  "./data/app/ford-county-outline.json",
  "./data/app/franklin-county-outline.json",
  "./data/app/fulton-county-outline.json",
  "./data/app/gallatin-county-outline.json",
  "./data/app/gallatin-precincts.json",
  "./data/app/greene-county-outline.json",
  "./data/app/greene-precincts.json",
  "./data/app/grundy-county-board-districts.json",
  "./data/app/grundy-county-outline.json",
  "./data/app/hamilton-county-outline.json",
  "./data/app/hancock-county-outline.json",
  "./data/app/hardin-county-outline.json",
  "./data/app/henderson-county-outline.json",
  "./data/app/henry-county-board-districts.json",
  "./data/app/henry-county-outline.json",
  "./data/app/henry-precincts.json",
  "./data/app/il-house-districts.json",
  "./data/app/il-senate-districts.json",
  "./data/app/il-supreme-court-districts.json",
  "./data/app/iroquois-county-outline.json",
  "./data/app/jackson-county-outline.json",
  "./data/app/jasper-county-outline.json",
  "./data/app/jefferson-county-board-districts.json",
  "./data/app/jefferson-county-outline.json",
  "./data/app/jefferson-precincts.json",
  "./data/app/jersey-county-outline.json",
  "./data/app/jo-daviess-county-board-districts.json",
  "./data/app/jo-daviess-county-outline.json",
  "./data/app/jo-daviess-precincts.json",
  "./data/app/johnson-county-outline.json",
  "./data/app/johnson-precincts.json",
  "./data/app/kane-county-outline.json",
  "./data/app/kane-judicial-subcircuits.json",
  "./data/app/kankakee-county-outline.json",
  "./data/app/kendall-county-outline.json",
  "./data/app/kendall-fire-districts.json",
  "./data/app/kendall-library-districts.json",
  "./data/app/kendall-park-districts.json",
  "./data/app/knox-county-outline.json",
  "./data/app/lake-county-outline.json",
  "./data/app/lasalle-county-board-districts.json",
  "./data/app/lasalle-county-outline.json",
  "./data/app/lawrence-county-outline.json",
  "./data/app/lee-county-outline.json",
  "./data/app/lee-library-districts.json",
  "./data/app/livingston-county-board-districts.json",
  "./data/app/livingston-county-outline.json",
  "./data/app/logan-county-outline.json",
  "./data/app/macon-county-outline.json",
  "./data/app/macon-fire-districts.json",
  "./data/app/macon-library-districts.json",
  "./data/app/macon-park-districts.json",
  "./data/app/macoupin-county-outline.json",
  "./data/app/madison-county-outline.json",
  "./data/app/madison-judicial-subcircuits.json",
  "./data/app/marion-county-outline.json",
  "./data/app/marshall-county-board-districts.json",
  "./data/app/marshall-county-outline.json",
  "./data/app/mason-county-board-districts.json",
  "./data/app/mason-county-outline.json",
  "./data/app/massac-county-outline.json",
  "./data/app/mcdonough-board-districts.json",
  "./data/app/mcdonough-county-outline.json",
  "./data/app/mcdonough-precincts.json",
  "./data/app/mchenry-county-outline.json",
  "./data/app/mchenry-judicial-subcircuits.json",
  "./data/app/mclean-county-outline.json",
  "./data/app/menard-commissioner-districts.json",
  "./data/app/menard-county-outline.json",
  "./data/app/menard-precincts.json",
  "./data/app/mercer-county-board-districts.json",
  "./data/app/mercer-county-outline.json",
  "./data/app/mercer-precincts.json",
  "./data/app/il-state-outline.json",
  "./data/app/metro-outline.json",
  "./data/app/monroe-county-outline.json",
  "./data/app/montgomery-county-board-districts.json",
  "./data/app/montgomery-county-outline.json",
  "./data/app/montgomery-precincts.json",
  "./data/app/morgan-county-outline.json",
  "./data/app/moultrie-county-outline.json",
  "./data/app/moultrie-precincts.json",
  "./data/app/municipal-ward-coverage.json",
  "./data/app/ogle-county-board-districts.json",
  "./data/app/ogle-county-outline.json",
  "./data/app/ogle-precincts.json",
  "./data/app/peoria-county-outline.json",
  "./data/app/perry-county-outline.json",
  "./data/app/perry-precincts.json",
  "./data/app/pulaski-precincts.json",
  "./data/app/hardin-precincts.json",
  "./data/app/piatt-county-outline.json",
  "./data/app/pike-county-outline.json",
  "./data/app/pope-county-outline.json",
  "./data/app/pulaski-county-outline.json",
  "./data/app/putnam-county-outline.json",
  "./data/app/randolph-county-outline.json",
  "./data/app/randolph-library-districts.json",
  "./data/app/richland-county-outline.json",
  "./data/app/rock-island-county-outline.json",
  "./data/app/rock-island-fire-districts.json",
  "./data/app/rock-island-library-districts.json",
  "./data/app/rock-island-park-districts.json",
  "./data/app/saline-county-outline.json",
  "./data/app/sangamon-county-outline.json",
  "./data/app/sangamon-library-districts.json",
  "./data/app/sangamon-judicial-subcircuits.json",
  "./data/app/school-board-districts.json",
  "./data/app/schuyler-county-outline.json",
  "./data/app/schuyler-precincts.json",
  "./data/app/scott-county-outline.json",
  "./data/app/scott-precincts.json",
  "./data/app/shelby-county-board-districts.json",
  "./data/app/shelby-precincts.json",
  "./data/app/shelby-county-outline.json",
  "./data/app/st-clair-county-outline.json",
  "./data/app/st-clair-library-districts.json",
  "./data/app/stark-county-board-districts.json",
  "./data/app/stark-county-outline.json",
  "./data/app/stark-fire-districts.json",
  "./data/app/stark-library-districts.json",
  "./data/app/stark-park-districts.json",
  "./data/app/stark-precincts.json",
  "./data/app/stephenson-county-board-districts.json",
  "./data/app/stephenson-county-outline.json",
  "./data/app/stephenson-library-districts.json",
  "./data/app/stephenson-fire-districts.json",
  "./data/app/stephenson-precincts.json",
  "./data/app/tazewell-county-outline.json",
  "./data/app/union-county-outline.json",
  "./data/app/vermilion-county-outline.json",
  "./data/app/wabash-county-outline.json",
  "./data/app/warren-county-outline.json",
  "./data/app/washington-county-board-districts.json",
  "./data/app/washington-county-outline.json",
  "./data/app/wayne-county-outline.json",
  "./data/app/white-county-outline.json",
  "./data/app/white-precincts.json",
  "./data/app/white-county-board-districts.json",
  "./data/app/whiteside-county-outline.json",
  "./data/app/will-county-outline.json",
  "./data/app/williamson-county-outline.json",
  "./data/app/winnebago-county-outline.json",
  "./data/app/winnebago-judicial-subcircuits.json",
  "./data/app/woodford-county-board-districts.json",
  "./data/app/woodford-county-outline.json",
  "./data/app/hancock-county-board-districts.json",
  "./data/app/hancock-precincts.json",
  "./data/app/richland-county-board-districts.json",
  "./data/app/richland-precincts.json",
  "./data/app/jackson-county-board-districts.json",
  "./data/app/jackson-precincts.json",
  "./data/app/douglas-county-board-districts.json",
  "./data/app/vermilion-county-board-districts.json",
  "./data/app/douglas-precincts.json",
  "./data/app/wayne-county-board-districts.json",
  "./data/app/wayne-precincts.json",
];

// Roster/officeholder data (also in data/app/) is refreshed by the weekly CI
// and must never be served stale — network-first, with the cached copy only
// as an offline fallback. Same freshness rule as the shell.
const ROSTER_URLS = [
  "./data/app/clark-county-board-members.json",
  "./data/app/crawford-county-board-members.json",
  "./data/app/edgar-county-board-members.json",
  "./data/app/franklin-county-board-members.json",
  "./data/app/clinton-county-board-members.json",
  "./data/app/warren-county-board-members.json",
  "./data/app/adams-county-board-members.json",
  "./data/app/knox-county-board-members.json",
  "./data/app/il-senate-members.json",
  "./data/app/il-house-members.json",
  "./data/app/mercer-county-board-members.json",
  "./data/app/school-board-members.json",
  "./data/app/congress-roster.json",
  "./data/app/cpd-district-info.json",
  "./data/app/ccpsa-district-councils.json",
  "./data/app/will-county-board-members.json",
  "./data/app/kane-county-board-members.json",
  "./data/app/lake-county-board-roles.json",
  "./data/app/kendall-county-board-members.json",
  "./data/app/mchenry-county-board-members.json",
  "./data/app/early-voting-sites.json",
  "./data/app/ccbr-roster.json",
  "./data/app/il-county-clerks.json",
  "./data/app/dupage-county-board-members.json",
  "./data/app/winnebago-county-board-members.json",
  "./data/app/sangamon-county-board-members.json",
  "./data/app/livingston-county-board-members.json",
  "./data/app/dekalb-county-board-members.json",
  "./data/app/ogle-county-board-members.json",
  "./data/app/stephenson-county-board-members.json",
  "./data/app/carroll-county-board-members.json",
  "./data/app/lee-county-board-members.json",
  "./data/app/rock-island-county-board-members.json",
  "./data/app/coverage-gaps.json",
  "./data/app/municipal-officials.json",
  "./data/app/lasalle-county-board-members.json",
  "./data/app/logan-precinct-polling.json",
  "./data/app/carroll-precinct-polling.json",
  "./data/app/dekalb-precinct-townships.json",
  "./data/app/whiteside-precinct-polling.json",
  "./data/app/hamilton-precinct-polling.json",
  "./data/app/woodford-county-board-members.json",
  "./data/app/logan-county-board-members.json",
  "./data/app/boone-county-board-members.json",
  "./data/app/grundy-county-board-members.json",
  "./data/app/henry-county-board-members.json",
  "./data/app/jefferson-county-board-members.json",
  "./data/app/macon-board-district-labels.json",
  "./data/app/macon-county-board-members.json",
  "./data/app/menard-commissioner-members.json",
  "./data/app/henry-precinct-polling.json",
  "./data/app/montgomery-precinct-polling.json",
  "./data/app/montgomery-county-board-members.json",
  "./data/app/peoria-county-board-members.json",
  "./data/app/tazewell-county-board-members.json",
  "./data/app/iroquois-county-board-members.json",
  "./data/app/il-county-commissioners.json",
  "./data/app/dewitt-county-board-members.json",
  "./data/app/washington-county-board-members.json",
  "./data/app/cass-county-board-members.json",
  "./data/app/marshall-county-board-members.json",
  "./data/app/mcdonough-county-board-members.json",
  "./data/app/fulton-county-board-members.json",
  "./data/app/stark-county-board-members.json",
  "./data/app/mason-county-board-members.json",
  "./data/app/shelby-county-board-members.json",
  "./data/app/white-county-board-members.json",
  "./data/app/white-precinct-polling.json",
  "./data/app/coles-county-board-members.json",
  "./data/app/jo-daviess-county-board-members.json",
  "./data/app/cook-library-trustees.json",
  "./data/app/township-officials.json",
  "./data/app/hancock-county-board-members.json",
  "./data/app/richland-county-board-members.json",
  "./data/app/jackson-county-board-members.json",
  "./data/app/douglas-county-board-members.json",
  "./data/app/vermilion-county-board-members.json",
  "./data/app/wayne-county-board-members.json",
  "./data/app/clay-county-board-members.json",
  "./data/app/st-clair-precinct-polling.json",
  "./data/app/boone-district-officials.json",
  "./data/app/il-county-board-offices.json",
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
