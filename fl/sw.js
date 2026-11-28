/* ==== ENGINE:BEGIN sw-header ==== */
// App-shell + app-data cache. Never serve live district/roster API responses
// stale — a stale roster could name the wrong officeholder, and this app's
// rule is that officeholder data is never guessed or served stale. Bump
// CACHE_NAME whenever SHELL_URLS, GEOMETRY_URLS, or ROSTER_URLS change, or
// whenever a file under fonts/ changes, so a removed or superseded entry can't
// live forever; the activate handler deletes every other-named cache.
//
// The config section below is this fork's METRO block (docs/ENGINE_SYNC.md):
// a per-city cache name, the shell assets, and the fork's data/app/*.json
// files split by caching policy — ~static boundary geometry (cache-first, cached
// the FIRST TIME A LAYER USES IT rather than at install, which #1197 changed on
// 2026-09-26 and this comment went on describing the old way) vs officeholder
// rosters (network-first, never stale). Every file
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
const CACHE_NAME = "districtry-fl-shell-v3";

const SHELL_URLS = [
  "./",
  "./icons/apple-touch-icon.png",
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js",
  "https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/5.24.0/maplibre-gl.min.js",
  "./vendor/leaflet-maplibre-gl.js",
];

// Boundary geometry (data/app/*.json, fetched lazily on first toggle).
// Boundaries change ~once a decade, so serve them cache-first (instant, and
// works offline once used) and refresh in the background. Cached the first
// time a layer uses them, never at install (sw-handlers, PRECACHE_URLS).
const GEOMETRY_URLS = [
  "./data/app/metro-outline.json",
  "./data/app/state-counties.json",
  "./data/app/congress-districts.json",
  "./data/app/fl-senate-districts.json",
  "./data/app/fl-house-districts.json",
  "./data/app/zip-index.json",
  "./data/app/tribal-areas.json",
  "./data/app/fl-judicial-districts.json",
];

// Roster/officeholder data (also in data/app/) is refreshed by the weekly CI
// and must never be served stale — network-first, with the cached copy only
// as an offline fallback. Same freshness rule as the shell.
const ROSTER_URLS = [
  "./data/app/congress-roster.json",
  "./data/app/fl-senate-members.json",
  "./data/app/fl-house-members.json",
  "./data/app/tribal-councils.json",
  "./data/app/coverage-gaps.json",
  "./data/app/statewide-officials.json",
  "./data/app/fl-district-judges.json",
];
/* ==== GENERATED:END sw-metro-config ==== */
/* ==== METRO:END sw-config ==== */

/* ==== ENGINE:BEGIN files-origin ==== */
  /* ---------- where the large files are served from ----------
   * The vector-tile archives (data/app/tiles/) and the Census block
   * populations (data/app/population/) are most of what this site publishes,
   * measured 2026-11-10 at 320 MB of a 747 MB site, and GitHub Pages stops
   * publishing a site past 1 GB. So on the live site they can be read from a
   * second host that keeps the same paths (Adam's choice of 2026-11-10: the
   * pages stay on GitHub and these files move to Cloudflare R2, which answers
   * the byte ranges a tile archive is read by; Cloudflare's page hosting
   * answers a range with the whole file, measured that day).
   *
   * THE BOUNDARY FILES FOLLOWED (Adam's "Start" of 2026-11-16): measured that
   * day with all fifty states live, the 902 whole-file boundary sets the apps
   * read were 463.5 MB of the 664.6 MB GitHub still published. A boundary
   * file is one the worksheet lists under data_files.geometry, which the
   * generator writes into the page as BOUNDARY_FILES (bare names) and into the
   * worker as GEOMETRY_URLS, so the page, its worker and the deploy's copy
   * (which reads the worker's list) name the same files. Rosters and election
   * results are not among them and stay on this site: a page and the roster
   * it prints are published together here.
   *
   * filesUrl(path, base) is the address to fetch one of those files from.
   * The live site reads the two folders and its boundary files from
   * FILES_ORIGIN, at the path they have on this site, and only while the page
   * itself is on FILES_SITE_HOST, so a copy served on localhost, in a test or
   * on a preview reads its own files and never the live host's. Anything else
   * is left on this site. The deploy copies the files there and leaves the two
   * folders out of what GitHub Pages publishes (scripts/sync_r2_files.py,
   * deploy-pages.yml). Null would read every file from this site again, as
   * every page did until the switch, which is the way back if the files host
   * fails: set it to null and stop the deploy dropping the files, in one
   * change. This block is ONE copy spliced into every app's index.html and
   * sw.js (engine/shared/), so the page and its service worker cannot
   * disagree about where a file lives.
   *
   * The boundary paths are worked out the first time one is asked for and
   * kept. A list that is not there yet (a `var` read before the line that
   * sets it has run) answers "none" and is NOT kept, so an early caller cannot
   * leave every later one reading this site; the page's one fetch helper also
   * waits for the script to finish before it asks (fetch-retry).
   * ------------------------------------------------------------------------ */
  var FILES_ORIGIN = "https://files.districtry.com";
  var FILES_SITE_HOST = "districtry.com";
  var FILES_FOLDERS = ["/data/app/tiles/", "/data/app/population/"];
  var FILES_BOUNDARY_PATHS = null;
  function filesBoundaryPaths() {
    if (FILES_BOUNDARY_PATHS) return FILES_BOUNDARY_PATHS;
    var names = typeof BOUNDARY_FILES !== "undefined" ? BOUNDARY_FILES
      : typeof GEOMETRY_URLS !== "undefined" ? GEOMETRY_URLS : null;
    if (!names) return {};
    var paths = {};
    for (var i = 0; i < names.length; i++) {
      var name = names[i].slice(names[i].lastIndexOf("/") + 1);
      paths[new URL("data/app/" + name, location.href).pathname] = true;
    }
    return (FILES_BOUNDARY_PATHS = paths);
  }
  function filesUrl(path, base) {
    var url = new URL(path, base);
    if (!FILES_ORIGIN || url.origin !== location.origin || location.hostname !== FILES_SITE_HOST) return url.href;
    for (var i = 0; i < FILES_FOLDERS.length; i++) {
      if (url.pathname.indexOf(FILES_FOLDERS[i]) !== -1) return FILES_ORIGIN + url.pathname + url.search;
    }
    if (filesBoundaryPaths()[url.pathname] === true) return FILES_ORIGIN + url.pathname + url.search;
    return url.href;
  }
/* ==== ENGINE:END files-origin ==== */

/* ==== ENGINE:BEGIN sw-handlers ==== */
// ONLY THE SHELL IS INSTALLED. Boundary files are cached the first time a
// layer uses them (cacheOnlyElseNetwork, below) and never before. Until 2026-09-26 the
// install handler also fetched every file in GEOMETRY_URLS: 9.8 MB gzipped for
// Wisconsin, 4.3 MB Illinois, 2.7 MB Iowa, 2.1 MB Michigan, 1.5 MB New York,
// on every visitor's first load, starting as the app booted and sharing the
// connection with the reader's first cards, for layers most readers never
// switch on (docs/OPTIMIZATION_PLAYBOOK.md §10, finding 4). The cost is
// offline: a layer never opened is not on the device. GEOMETRY_URLS still
// decides the STRATEGY — cache-first — which is all it is read for now.
const PRECACHE_URLS = SHELL_URLS;

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

// Cache-first with NO revalidation, for files whose bytes cannot change under a
// fixed URL without a CACHE_NAME bump: boundary geometry, self-hosted fonts and
// the Census block populations. A hit is served from the cache and nothing
// crosses the network; a miss is fetched and cached.
//
// Boundary geometry used a cacheFirst() that fired a network fetch on EVERY
// hit, serving the cached copy and re-downloading it in the background, so a
// returning visitor paid the full download of every layer they opened on
// every visit — measured 2026-09-26 on /il/ with six layers on, all six files
// fetched again on the second visit and on each one after. That refresh was
// standing in for a missed CACHE_NAME bump, and check_cache_version.py now
// fails any change that edits one of these files without one, so the bump is
// the whole invalidation mechanism. The fonts took this policy on 2026-09-12
// for the same reason.
//
// The miss asks with cache: "no-cache", so the browser's HTTP cache is
// revalidated rather than trusted. A copy the HTTP cache picked up in the
// minutes before a deploy (GitHub Pages serves max-age=600) would otherwise be
// stored under the NEW cache name and, with no background refresh to replace
// it, stay there until the next bump. Revalidating costs a 304 when the file
// is unchanged and nothing when the HTTP cache holds no copy.
function cacheOnlyElseNetwork(request) {
  return caches.match(request).then(
    (cached) =>
      cached ||
      fetch(new Request(request, { cache: "no-cache" })).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      })
  );
}

// Vector-tile archives (data/app/tiles/*.pmtiles): the app reads a tile as
// a byte range of one file, and the Cache API refuses a 206, so each range is
// cached under its own key and handed back as the 206 the page asked for.
// Cache-only-else-network like the other boundary data: an archive's bytes
// change only with a CACHE_NAME bump, which check_cache_version.py enforces
// for everything under data/app/tiles/. A server that ignores Range (python's
// http.server, which the smoke tests use) answers 200 with the whole file:
// that is cached under the archive's own URL and every later range is cut
// from it, so a repeat visit and offline use work on either kind of server.
function rangeKey(request) {
  const url = new URL(request.url);
  url.searchParams.set("dxrange", request.headers.get("range"));
  return url.href;
}
// Last-Modified is kept on every copy because the page holds each range's to
// the archive's first one, to notice an archive rebuilt while it was open
// (ENGINE vector-tiles tileRangeFetcher).
function partial(body, type, from, to, total, modified) {
  return new Response(body, {
    status: 206,
    headers: {
      "Content-Type": type || "application/octet-stream",
      "Content-Range": "bytes " + from + "-" + to + "/" + total,
      "Last-Modified": modified || ""
    }
  });
}
// The page asks with cache: "no-store" after it found an archive changed
// under it (not "reload": Chrome gives that to every request a reloading page
// makes): every copy of that archive held here is from before, so drop them all.
function dropArchive(url) {
  const base = url.split("?")[0];
  return caches.open(CACHE_NAME).then((cache) =>
    cache.keys().then((keys) =>
      Promise.all(keys.filter((k) => k.url.split("?")[0] === base).map((k) => cache.delete(k)))
    )
  );
}
function cachedRange(request) {
  if (request.cache === "no-store") return dropArchive(request.url).then(() => rangeFromNetwork(request));
  const key = rangeKey(request);
  const m = /bytes=(\d+)-(\d+)/.exec(request.headers.get("range") || "");
  return caches.match(key).then((hit) => {
    if (hit) {
      return hit.arrayBuffer().then((body) => new Response(body, {
        status: 206,
        headers: {
          "Content-Type": hit.headers.get("Content-Type") || "application/octet-stream",
          "Content-Range": hit.headers.get("X-Content-Range") || "",
          "Last-Modified": hit.headers.get("Last-Modified") || ""
        }
      }));
    }
    return caches.match(request.url).then((whole) => {
      if (whole && m) {
        return whole.arrayBuffer().then((buf) => {
          const from = +m[1], to = Math.min(+m[2], buf.byteLength - 1);
          return partial(buf.slice(from, to + 1), whole.headers.get("Content-Type"), from, to, buf.byteLength,
            whole.headers.get("Last-Modified"));
        });
      }
      return rangeFromNetwork(request);
    });
  });
}
function rangeFromNetwork(request) {
  const key = rangeKey(request);
  return fetch(request).then((response) => {
    const clone = response.clone();
    if (response.status === 206) {
      clone.arrayBuffer().then((body) =>
        caches.open(CACHE_NAME).then((cache) => cache.put(key, new Response(body, {
          status: 200,
          headers: {
            "Content-Type": clone.headers.get("Content-Type") || "application/octet-stream",
            "X-Content-Range": clone.headers.get("Content-Range") || "",
            "Last-Modified": clone.headers.get("Last-Modified") || ""
          }
        })))
      );
    } else if (response.ok) {
      caches.open(CACHE_NAME).then((cache) => cache.put(request.url, clone));
    }
    return response;
  });
}

// One of this app's folders, on this site or on the files host the page reads
// it from (filesUrl, the files-origin block). Both are asked so the worker
// keeps answering a page that still reads the folder from this site.
function underFolder(href, folder) {
  return href.startsWith(new URL(folder, self.registration.scope).href) ||
    href.startsWith(filesUrl(folder, self.registration.scope));
}

// Boundary geometry lives at two addresses and is ONE file here. On the live
// site the page asks the files host for it (filesUrl, the files-origin block);
// everywhere else, and from any tab loaded before the maps were switched on
// 2026-11-16, it asks this site. geometryKey answers either address with the
// file's address on THIS site, which is the one key it is cached under.
//
// That key is why the switch needed no CACHE_NAME bump: every copy a returning
// visitor already held was cached under its address on this site, so the
// first request for the same file at the files host is a cache hit, offline
// included. A bump would have made every returning visitor download every
// boundary file again for bytes that had not changed.
//
// A miss is fetched from wherever filesUrl says the file lives, whichever
// address was asked for, so a tab still running the page from before the
// switch is served from the files host too and keeps working once this site
// stops publishing the files. It asks with cache: "no-cache" for the reason
// cacheOnlyElseNetwork gives.
let GEOMETRY_KEYS = null;
function geometryKey(href) {
  if (!GEOMETRY_KEYS) {
    GEOMETRY_KEYS = new Map();
    GEOMETRY_URLS.forEach((url) => {
      const own = new URL(url, self.registration.scope).href;
      GEOMETRY_KEYS.set(own, own);
      GEOMETRY_KEYS.set(filesUrl(own), own);
    });
  }
  return GEOMETRY_KEYS.get(href);
}
function boundaryFile(key) {
  return caches.match(key).then(
    (cached) =>
      cached ||
      fetch(filesUrl(key), { cache: "no-cache" }).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(key, clone));
        }
        return response;
      })
  );
}

self.addEventListener("fetch", (event) => {
  const href = new URL(event.request.url).href;

  if (event.request.headers.has("range") && underFolder(href, "data/app/tiles/")) {
    event.respondWith(cachedRange(event.request));
    return;
  }

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

  // Boundary geometry: changes only with a CACHE_NAME bump, so served from the
  // cache without revalidation, for instant toggles, offline use, and no bytes
  // on a repeat visit. Asked for on this site or on the files host, it is the
  // same file under the same key (geometryKey, above).
  const boundary = geometryKey(href);
  if (boundary) {
    event.respondWith(boundaryFile(boundary));
    return;
  }

  // Self-hosted fonts: served from cache without revalidation, matched by
  // prefix rather than listed.
  //
  // Measured 2026-09-12 on /il/ over an emulated 1.6 Mbps link: a second
  // navigation re-fetched six woff2 files, 134,516 bytes, because no font
  // appeared in any list above and nothing else here cached them. Every
  // instance ships eighteen faces and none of the 108 in the fleet was cached
  // by any worker.
  //
  // A PREFIX and not a list, because a list would have to name which faces a
  // page happens to need. The browser downloads only the faces it renders
  // glyphs for -- six of the eighteen on this page -- so precaching the list
  // would fetch about 160 KB at install that the visitor never uses. Nothing
  // is precached here: the first visit pays the network exactly as it does
  // today, and the repeat visit pays nothing.
  //
  // cacheOnlyElseNetwork and not a revalidating cache-first: the latter would
  // have served the font instantly and still spent the 134 KB. An earlier draft
  // of this branch did that and its comment claimed the bytes were saved; the
  // repeat-visit probe showed all six still crossing the wire.
  //
  // Scoped to this registration, so a sibling instance's fonts/ is left to its
  // own worker -- CacheStorage is per-origin and this origin serves six apps.
  //
  // A changed font reaches a returning visitor only on a CACHE_NAME bump;
  // check_cache_version.py enforces it for these files.
  if (href.startsWith(new URL("fonts/", self.registration.scope).href)) {
    event.respondWith(cacheOnlyElseNetwork(event.request));
    return;
  }

  // Census block populations (data/app/population/, the comparison stats
  // screen): one file per county, fetched only for the counties a comparison
  // touches. A PREFIX like the fonts and for the same reason — listing them
  // would precache several megabytes most visitors never ask for — and
  // cacheOnlyElseNetwork like the fonts, because a census count does not
  // change under a fixed URL: a rebuild (the 2030 census) reaches a returning
  // visitor through a CACHE_NAME bump, which check_cache_version.py enforces
  // for these files as it does for fonts. An instance that ships no such
  // folder never requests anything under it.
  if (underFolder(href, "data/app/population/")) {
    event.respondWith(cacheOnlyElseNetwork(event.request));
    return;
  }

  // Everything else (all live district/roster API calls) hits the network normally.
});
/* ==== ENGINE:END sw-handlers ==== */
