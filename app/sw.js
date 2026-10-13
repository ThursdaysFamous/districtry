/* The installed app's launcher worker, at scope /app/.

   It keeps one thing: a copy of the launcher page (/app/), so an installed
   districtry opens with no connection. The launcher then opens the state the
   reader used last, and that state's map is served by its own worker
   (<tag>/sw.js). Nothing else passes through here: any request that is not a
   navigation to /app/ goes straight to the network.

   It serves its copy first and refreshes it in the background, so a launch
   never waits on the network for a page that changes rarely.

   IT DELETES ONLY ITS OWN CACHES. Cache storage is shared by the whole origin,
   so a worker that deleted every cache it did not recognise would empty every
   state's offline copy. scripts/build_manifests.py --check fails if this file
   names any cache outside its own prefix. Bump the number on CACHE to replace
   the stored copy at once rather than on the next launch. */
var PREFIX = "districtry-app-launch-v";
var CACHE = PREFIX + "1";
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
  var fresh = fetch(event.request).then(function (response) {
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
