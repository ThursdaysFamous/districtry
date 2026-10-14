/* The installed app's launcher worker, at scope /app/.

   It keeps one thing: a copy of the launcher page (/app/), so an installed
   districtry opens with no connection. The launcher then opens the state the
   reader used last, and that state's map is served by its own worker
   (<tag>/sw.js). Nothing else passes through here: any request that is not a
   navigation to /app/ goes straight to the network.

   It serves its copy first and refreshes it in the background, so a launch
   never waits on the network for a page that changes rarely.

   THE REFRESH ASKS FOR /app/ ALONE, never the request it was handed. A place
   shared into the app arrives as /app/?title=...&text=...&url=... (the
   manifest's share_target), so fetching that request would send what was
   shared to the host on every share, while answering from the copy keeps it
   on the phone. The copy is the launcher page whatever the address carries:
   the page reads the share from its own address. scripts/build_manifests.py
   --check fails if this file fetches the request it was handed. The apps
   register this worker too, when districtry is installed from one of them and
   whenever the installed app runs (engine/index.html/install-app.txt), so a
   share is answered here even before the installed app's first launch.

   IT DELETES ONLY ITS OWN CACHES. Cache storage is shared by the whole origin,
   so a worker that deleted every cache it did not recognise would empty every
   state's offline copy. scripts/build_manifests.py --check fails if this file
   names any cache outside its own prefix. Bump the number on CACHE to replace
   the stored copy at once rather than on the next launch. */
var PREFIX = "districtry-app-launch-v";
var CACHE = PREFIX + "2";
var PAGE = "/app/";

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE)
      .then(function (cache) { return cache.add(new Request(PAGE, { cache: "no-cache" })); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (key) {
        return key.indexOf(PREFIX) === 0 && key !== CACHE;
      }).map(function (key) { return caches.delete(key); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (event) {
  if (event.request.mode !== "navigate") return;
  var fresh = fetch(new Request(PAGE, { cache: "no-cache" })).then(function (response) {
    if (!response || !response.ok) return response;
    var copy = response.clone();
    return caches.open(CACHE)
      .then(function (cache) { return cache.put(PAGE, copy); })
      .then(function () { return response; });
  });
  event.waitUntil(fresh.catch(function () {}));
  event.respondWith(
    caches.match(PAGE, { cacheName: CACHE }).then(function (cached) {
      return cached || fresh;
    })
  );
});
