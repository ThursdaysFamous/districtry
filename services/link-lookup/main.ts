// districtry's short-link lookup, run on Deno Deploy.
//
// WHAT IT IS FOR. A short Google Maps or Apple Maps link (maps.app.goo.gl/…,
// goo.gl/maps/…, maps.apple/p/…) holds no position: only Google or Apple knows
// where it leads, and a web page cannot ask them, because a browser does not
// let a page read where another site redirects. This asks on the page's
// behalf and returns the full link, which the page then reads itself with
// engine/shared/map-link.txt.
//
// WHAT IT DOES, AND NOTHING ELSE:
//   GET /?u=<short link>  ->  {"url": "<the full link it leads to>"}
//   GET /?a=<address>     ->  {"matches": [{"address", "lat", "lng"}, ...]}
// For a short link it follows redirects one hop at a time, refuses any hop to
// a host that is not Google's or Apple's, stops at the first full map link,
// and never reads a page body. It keeps no record: nothing is written,
// logged or cached, and the answer says so (Cache-Control: no-store).
//
// THE ADDRESS ROUTE (added 2026-10-17). A place shared from the Google Maps
// app is its name and its street address with no position, and the map's
// own geocoder (Photon) often holds the street and not the house number on
// it, so the app could only show the street (ENGINE geocoder-search
// showStreetOnly). The Census Bureau's geocoder estimates where a number
// falls along a street from the address ranges in the Bureau's TIGER street
// file, but it sends no CORS header, so a page cannot read its answer. This asks it on the page's behalf and passes on each
// match's address and position, nothing else of the answer. The app checks
// that a match is on the shared address's street, in its town, with its
// number, and shows it as a pin, whose point it has selected since
// 2026-10-18. Since 2026-10-20 New York's app also asks it about the public
// address of an office a card shows, when the city's own address search
// cannot place that office's map pin.
// Measured 2026-10-17: a Chicago storefront Photon knew only as its street
// came back on the right side of the street and on its block, about 45 m
// from the building; asked on 2026-10-14 for a Westmont address, it offered
// that number on two other streets, which is why the app checks the street.
//
// WHY THERE IS NO robots.txt READ. robots.txt governs crawlers. This makes
// one request for one link or address a reader shared, at the moment they
// share it, or for the office on a card the reader opened, at the moment it
// opens, which is a user agent acting for that reader, not a crawl
// (RFC 9309 §1 scopes the protocol to automatic clients that crawl). The
// Census host publishes no robots.txt in any case (HTTP 404, read
// 2026-10-17).
//
// PRIVACY. Deno, which runs this, and Google or Apple, which answer it,
// receive the short link. Deno and the Census Bureau receive the address on
// the address route. Google, Apple and the Census Bureau see Deno's address,
// not the reader's. privacy.html must name each recipient on the day an
// app's MAP_LINK_LOOKUP points at a route that reaches it.
//
// DEPLOY: the Deno Deploy app `link-lookup` in the `districtry` organization,
// with this file as its entry point. It needs no environment variables and no
// secrets.
// The app is NOT linked to this repository, and must not be linked again.
// A linked app rebuilds on every push to every branch, and each build takes
// a full copy of the repository: 200 MiB compressed, measured with
// `git archive` on 2026-10-14. The app was linked on 2026-10-13, and in
// about 21 hours there were 79 builds (26 from main, 53 from work branches),
// about 15.5 GiB. The Free plan allows 20 GiB of egress a month, and Deno
// sent a 75% usage alert the next morning. Adam unlinked the repository on
// 2026-10-14. The version deployed then keeps serving.
//
// To change this file, deploy it by hand from this folder, so that the folder
// is all that is uploaded:
//   cd services/link-lookup && deno deploy --org districtry --app link-lookup --prod
// Since only this folder is uploaded, the app's settings in Deno's console
// must read an empty App directory and the Entrypoint main.ts. The app was
// set up while it read the whole repository, so check both before the first
// hand deploy. Deno puts a revision live only once its build succeeds
// (docs.deno.com/deploy/reference/builds, read 2026-10-17), so a wrong
// setting leaves the current version answering.
// Then check it answers: ?u=https://example.com/ must return a 400 that names
// short links, a real maps.app.goo.gl link must return {"url": ...}, and
// ?a=1600 Pennsylvania Ave NW, Washington, DC 20500 must return a match.

const ALLOWED_ORIGINS = new Set([
  "https://districtry.com",
  "https://www.districtry.com",
]);

const SHORT_HOSTS = new Set(["maps.app.goo.gl", "goo.gl", "maps.apple"]);
// Every host a short link may pass through on its way to a full link.
const HOP_HOSTS = /^(maps\.app\.goo\.gl|goo\.gl|maps\.apple|maps\.apple\.com|consent\.google\.[a-z.]+|(www\.|maps\.)?google\.[a-z]{2,3}(\.[a-z]{2})?)$/;
const MAX_HOPS = 6;
const UA = "districtry-link-lookup/1.0 (+https://districtry.com/privacy.html)";

const CENSUS_GEOCODER = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress";
const CENSUS_TIMEOUT_MS = 7000;
const MAX_ADDRESS = 200;
const MAX_MATCHES = 5;

function corsHeaders(origin: string | null): Record<string, string> {
  const h: Record<string, string> = {
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
    "Vary": "Origin",
  };
  if (origin && (ALLOWED_ORIGINS.has(origin) || /^http:\/\/localhost(:\d+)?$/.test(origin))) {
    h["Access-Control-Allow-Origin"] = origin;
  }
  return h;
}

function reply(status: number, body: unknown, origin: string | null): Response {
  return new Response(JSON.stringify(body), { status, headers: corsHeaders(origin) });
}

function isShort(u: URL): boolean {
  const host = u.hostname.toLowerCase();
  if (!SHORT_HOSTS.has(host)) return false;
  return host !== "goo.gl" || u.pathname.startsWith("/maps/");
}

// A full link is one the page can read: anything on Google Maps or Apple
// Maps that is not itself a short link or a consent page.
function isFull(u: URL): boolean {
  const host = u.hostname.toLowerCase();
  if (host === "maps.apple.com") return true;
  if (/^consent\./.test(host)) return false;
  return /google\./.test(host) && (host.startsWith("maps.") || u.pathname.startsWith("/maps"));
}

export async function resolve(start: URL, fetchFn: typeof fetch = fetch): Promise<string | null> {
  let u = start;
  for (let hop = 0; hop < MAX_HOPS; hop++) {
    if (!HOP_HOSTS.test(u.hostname.toLowerCase()) || u.protocol !== "https:") return null;
    if (hop > 0 && isFull(u)) return u.href;
    // Google sends some regions to a consent page that carries the real
    // destination in `continue`; read it rather than answering the page.
    if (/^consent\./.test(u.hostname)) {
      const next = u.searchParams.get("continue");
      if (!next) return null;
      u = new URL(next);
      continue;
    }
    const res = await fetchFn(u.href, {
      method: "GET",
      redirect: "manual",
      headers: { "User-Agent": UA, "Accept": "text/html" },
    });
    await res.body?.cancel();
    const loc = res.headers.get("location");
    if (res.status < 300 || res.status > 399 || !loc) return null;
    u = new URL(loc, u);
  }
  return null;
}

// A street address with its town: a house number somewhere in it, a comma
// before the town, and nothing a person would not write.
export function isAddress(a: string): boolean {
  return a.length <= MAX_ADDRESS && /\d/.test(a) && /,/.test(a) && !/[\u0000-\u001f\u007f]/.test(a);
}

export interface RangeMatch { address: string; lat: number; lng: number }

// The Census Bureau's matches for one address, as their address and position
// only. Null when the geocoder fails or answers something else.
export async function rangeMatches(address: string, fetchFn: typeof fetch = fetch): Promise<RangeMatch[] | null> {
  const q = new URL(CENSUS_GEOCODER);
  q.searchParams.set("address", address);
  q.searchParams.set("benchmark", "Public_AR_Current");
  q.searchParams.set("format", "json");
  const res = await fetchFn(q.href, {
    headers: { "User-Agent": UA, "Accept": "application/json" },
    signal: AbortSignal.timeout(CENSUS_TIMEOUT_MS),
  });
  if (!res.ok) {
    await res.body?.cancel();
    return null;
  }
  const body = await res.json() as { result?: { addressMatches?: unknown } } | null;
  const found = body?.result?.addressMatches;
  if (!Array.isArray(found)) return null;
  const matches: RangeMatch[] = [];
  for (const m of found) {
    const label = m?.matchedAddress, lat = m?.coordinates?.y, lng = m?.coordinates?.x;
    if (typeof label === "string" && label && typeof lat === "number" && typeof lng === "number" &&
        Number.isFinite(lat) && Number.isFinite(lng)) matches.push({ address: label, lat, lng });
    if (matches.length === MAX_MATCHES) break;
  }
  return matches;
}

export async function handler(req: Request): Promise<Response> {
  const origin = req.headers.get("origin");
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(origin) });
  if (req.method !== "GET") return reply(405, { error: "GET only" }, origin);
  const params = new URL(req.url).searchParams;
  if (params.has("a")) {
    const address = (params.get("a") ?? "").trim();
    if (!isAddress(address)) return reply(400, { error: "a must be a street address with its town" }, origin);
    try {
      const matches = await rangeMatches(address);
      if (!matches) return reply(502, { error: "the Census Bureau's geocoder did not answer" }, origin);
      return reply(200, { matches }, origin);
    } catch {
      return reply(502, { error: "the Census Bureau's geocoder did not answer" }, origin);
    }
  }
  const raw = params.get("u");
  let start: URL;
  try {
    start = new URL(raw ?? "");
  } catch {
    return reply(400, { error: "u must be a link" }, origin);
  }
  if (start.protocol !== "https:" || !isShort(start)) {
    return reply(400, { error: "only short Google Maps and Apple Maps links are looked up" }, origin);
  }
  try {
    const url = await resolve(start);
    if (!url) return reply(404, { error: "the link does not lead to a map" }, origin);
    return reply(200, { url }, origin);
  } catch {
    return reply(502, { error: "the link could not be followed" }, origin);
  }
}

if (import.meta.main) Deno.serve(handler);
