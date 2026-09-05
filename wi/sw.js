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
const CACHE_NAME = "districtry-wi-shell-v37";

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
  "./data/app/adams-county-outline.json",
  "./data/app/ashland-county-outline.json",
  "./data/app/barron-county-outline.json",
  "./data/app/bayfield-county-outline.json",
  "./data/app/brown-county-outline.json",
  "./data/app/buffalo-county-outline.json",
  "./data/app/burnett-county-outline.json",
  "./data/app/calumet-county-outline.json",
  "./data/app/chippewa-county-outline.json",
  "./data/app/clark-county-outline.json",
  "./data/app/columbia-county-outline.json",
  "./data/app/crawford-county-outline.json",
  "./data/app/dane-county-outline.json",
  "./data/app/dodge-county-outline.json",
  "./data/app/door-county-outline.json",
  "./data/app/douglas-county-outline.json",
  "./data/app/dunn-county-outline.json",
  "./data/app/eau-claire-county-outline.json",
  "./data/app/florence-county-outline.json",
  "./data/app/fond-du-lac-county-outline.json",
  "./data/app/forest-county-outline.json",
  "./data/app/grant-county-outline.json",
  "./data/app/green-county-outline.json",
  "./data/app/green-lake-county-outline.json",
  "./data/app/iowa-county-outline.json",
  "./data/app/iron-county-outline.json",
  "./data/app/jackson-county-outline.json",
  "./data/app/jefferson-county-outline.json",
  "./data/app/juneau-county-outline.json",
  "./data/app/kenosha-county-outline.json",
  "./data/app/kewaunee-county-outline.json",
  "./data/app/la-crosse-county-outline.json",
  "./data/app/lafayette-county-outline.json",
  "./data/app/langlade-county-outline.json",
  "./data/app/lincoln-county-outline.json",
  "./data/app/manitowoc-county-outline.json",
  "./data/app/marathon-county-outline.json",
  "./data/app/marinette-county-outline.json",
  "./data/app/marquette-county-outline.json",
  "./data/app/menominee-county-outline.json",
  "./data/app/milwaukee-county-outline.json",
  "./data/app/monroe-county-outline.json",
  "./data/app/oconto-county-outline.json",
  "./data/app/oneida-county-outline.json",
  "./data/app/outagamie-county-outline.json",
  "./data/app/ozaukee-county-outline.json",
  "./data/app/pepin-county-outline.json",
  "./data/app/pierce-county-outline.json",
  "./data/app/polk-county-outline.json",
  "./data/app/portage-county-outline.json",
  "./data/app/price-county-outline.json",
  "./data/app/racine-county-outline.json",
  "./data/app/richland-county-outline.json",
  "./data/app/rock-county-outline.json",
  "./data/app/rusk-county-outline.json",
  "./data/app/sauk-county-outline.json",
  "./data/app/sawyer-county-outline.json",
  "./data/app/shawano-county-outline.json",
  "./data/app/sheboygan-county-outline.json",
  "./data/app/st-croix-county-outline.json",
  "./data/app/taylor-county-outline.json",
  "./data/app/trempealeau-county-outline.json",
  "./data/app/vernon-county-outline.json",
  "./data/app/vilas-county-outline.json",
  "./data/app/walworth-county-outline.json",
  "./data/app/washburn-county-outline.json",
  "./data/app/washington-county-outline.json",
  "./data/app/waukesha-county-outline.json",
  "./data/app/waupaca-county-outline.json",
  "./data/app/waushara-county-outline.json",
  "./data/app/winnebago-county-outline.json",
  "./data/app/wood-county-outline.json",
  "./data/app/congress-districts.json",
  "./data/app/school-districts-unified.json",
  "./data/app/wi-senate-districts.json",
  "./data/app/wi-assembly-districts.json",
  "./data/app/county-supervisory-districts.json",
  "./data/app/wi-circuit-courts.json",
  "./data/app/wi-court-of-appeals-districts.json",
  "./data/app/wi-state-outline.json",
  "./data/app/school-sites.json",
  "./data/app/mpd-districts.json",
  "./data/app/milwaukee-neighborhoods.json",
  "./data/app/mps-school-board-districts.json",
  "./data/app/rusd-school-board-districts.json",
  "./data/app/aldermanic-districts.json",
  "./data/app/library-sites.json",
  "./data/app/fire-service-areas.json",
  "./data/app/law-service-areas.json",
  "./data/app/psap-areas.json",
  "./data/app/ems-service-areas.json",
  "./data/app/mpd-squad-areas.json",
  "./data/app/wtcs-districts.json",
  "./data/app/madison-tid-districts.json",
  "./data/app/madison-neighborhood-assocs.json",
  "./data/app/madison-outline.json",
  "./data/app/tid-districts.json",
];

// Roster/officeholder data (also in data/app/) is refreshed by the weekly CI
// and must never be served stale — network-first, with the cached copy only
// as an offline fallback. Same freshness rule as the shell.
const ROSTER_URLS = [
  "./data/app/adams-polling-places.json",
  "./data/app/ashland-polling-places.json",
  "./data/app/barron-polling-places.json",
  "./data/app/bayfield-polling-places.json",
  "./data/app/brown-polling-places.json",
  "./data/app/buffalo-polling-places.json",
  "./data/app/burnett-polling-places.json",
  "./data/app/calumet-polling-places.json",
  "./data/app/chippewa-polling-places.json",
  "./data/app/clark-polling-places.json",
  "./data/app/columbia-polling-places.json",
  "./data/app/congress-roster.json",
  "./data/app/county-board-directory.json",
  "./data/app/county-board-members.json",
  "./data/app/coverage-gaps.json",
  "./data/app/crawford-polling-places.json",
  "./data/app/dane-polling-places.json",
  "./data/app/dodge-polling-places.json",
  "./data/app/door-polling-places.json",
  "./data/app/douglas-polling-places.json",
  "./data/app/dunn-polling-places.json",
  "./data/app/eau-claire-polling-places.json",
  "./data/app/florence-polling-places.json",
  "./data/app/fond-du-lac-polling-places.json",
  "./data/app/forest-polling-places.json",
  "./data/app/grant-polling-places.json",
  "./data/app/green-lake-polling-places.json",
  "./data/app/green-polling-places.json",
  "./data/app/iowa-polling-places.json",
  "./data/app/iron-polling-places.json",
  "./data/app/jackson-polling-places.json",
  "./data/app/jefferson-polling-places.json",
  "./data/app/juneau-polling-places.json",
  "./data/app/kenosha-polling-places.json",
  "./data/app/kewaunee-polling-places.json",
  "./data/app/la-crosse-polling-places.json",
  "./data/app/lafayette-polling-places.json",
  "./data/app/langlade-polling-places.json",
  "./data/app/lincoln-polling-places.json",
  "./data/app/madison-polling-places.json",
  "./data/app/manitowoc-polling-places.json",
  "./data/app/marathon-polling-places.json",
  "./data/app/marinette-polling-places.json",
  "./data/app/marquette-polling-places.json",
  "./data/app/menominee-polling-places.json",
  "./data/app/milwaukee-polling-places.json",
  "./data/app/mke-polling-places.json",
  "./data/app/monroe-polling-places.json",
  "./data/app/mpd-district-captains.json",
  "./data/app/mps-school-board-members.json",
  "./data/app/rusd-school-board-members.json",
  "./data/app/oconto-polling-places.json",
  "./data/app/oneida-polling-places.json",
  "./data/app/outagamie-polling-places.json",
  "./data/app/ozaukee-polling-places.json",
  "./data/app/pepin-polling-places.json",
  "./data/app/pierce-polling-places.json",
  "./data/app/polk-polling-places.json",
  "./data/app/portage-polling-places.json",
  "./data/app/price-polling-places.json",
  "./data/app/racine-polling-places.json",
  "./data/app/richland-polling-places.json",
  "./data/app/rock-polling-places.json",
  "./data/app/rusk-polling-places.json",
  "./data/app/sauk-polling-places.json",
  "./data/app/sawyer-polling-places.json",
  "./data/app/shawano-polling-places.json",
  "./data/app/sheboygan-polling-places.json",
  "./data/app/st-croix-polling-places.json",
  "./data/app/taylor-polling-places.json",
  "./data/app/town-clerks-001.json",
  "./data/app/town-clerks-003.json",
  "./data/app/town-clerks-005.json",
  "./data/app/town-clerks-007.json",
  "./data/app/town-clerks-009.json",
  "./data/app/town-clerks-011.json",
  "./data/app/town-clerks-013.json",
  "./data/app/town-clerks-015.json",
  "./data/app/town-clerks-017.json",
  "./data/app/town-clerks-019.json",
  "./data/app/town-clerks-021.json",
  "./data/app/town-clerks-023.json",
  "./data/app/town-clerks-025.json",
  "./data/app/town-clerks-027.json",
  "./data/app/town-clerks-029.json",
  "./data/app/town-clerks-031.json",
  "./data/app/town-clerks-033.json",
  "./data/app/town-clerks-035.json",
  "./data/app/town-clerks-037.json",
  "./data/app/town-clerks-039.json",
  "./data/app/town-clerks-041.json",
  "./data/app/town-clerks-043.json",
  "./data/app/town-clerks-045.json",
  "./data/app/town-clerks-047.json",
  "./data/app/town-clerks-049.json",
  "./data/app/town-clerks-051.json",
  "./data/app/town-clerks-053.json",
  "./data/app/town-clerks-055.json",
  "./data/app/town-clerks-057.json",
  "./data/app/town-clerks-059.json",
  "./data/app/town-clerks-061.json",
  "./data/app/town-clerks-063.json",
  "./data/app/town-clerks-065.json",
  "./data/app/town-clerks-067.json",
  "./data/app/town-clerks-069.json",
  "./data/app/town-clerks-071.json",
  "./data/app/town-clerks-073.json",
  "./data/app/town-clerks-075.json",
  "./data/app/town-clerks-077.json",
  "./data/app/town-clerks-078.json",
  "./data/app/town-clerks-081.json",
  "./data/app/town-clerks-083.json",
  "./data/app/town-clerks-085.json",
  "./data/app/town-clerks-087.json",
  "./data/app/town-clerks-089.json",
  "./data/app/town-clerks-091.json",
  "./data/app/town-clerks-093.json",
  "./data/app/town-clerks-095.json",
  "./data/app/town-clerks-097.json",
  "./data/app/town-clerks-099.json",
  "./data/app/town-clerks-101.json",
  "./data/app/town-clerks-103.json",
  "./data/app/town-clerks-105.json",
  "./data/app/town-clerks-107.json",
  "./data/app/town-clerks-109.json",
  "./data/app/town-clerks-111.json",
  "./data/app/town-clerks-113.json",
  "./data/app/town-clerks-115.json",
  "./data/app/town-clerks-117.json",
  "./data/app/town-clerks-119.json",
  "./data/app/town-clerks-121.json",
  "./data/app/town-clerks-123.json",
  "./data/app/town-clerks-125.json",
  "./data/app/town-clerks-127.json",
  "./data/app/town-clerks-129.json",
  "./data/app/town-clerks-131.json",
  "./data/app/town-clerks-133.json",
  "./data/app/town-clerks-135.json",
  "./data/app/town-clerks-137.json",
  "./data/app/town-clerks-139.json",
  "./data/app/town-clerks-141.json",
  "./data/app/trempealeau-polling-places.json",
  "./data/app/vernon-polling-places.json",
  "./data/app/vilas-polling-places.json",
  "./data/app/walworth-polling-places.json",
  "./data/app/washburn-polling-places.json",
  "./data/app/washington-polling-places.json",
  "./data/app/waukesha-polling-places.json",
  "./data/app/waupaca-polling-places.json",
  "./data/app/waushara-polling-places.json",
  "./data/app/wi-alderpersons.json",
  "./data/app/wi-assembly-members.json",
  "./data/app/wi-circuit-judges.json",
  "./data/app/wi-county-clerks.json",
  "./data/app/wi-county-officers.json",
  "./data/app/wi-court-of-appeals-roster.json",
  "./data/app/wi-municipal-clerks.json",
  "./data/app/wi-municipal-executives.json",
  "./data/app/wi-senate-members.json",
  "./data/app/winnebago-polling-places.json",
  "./data/app/wood-polling-places.json",
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
