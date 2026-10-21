// Every layer drawn from vector tiles must print the same card it printed from
// its whole GeoJSON file (docs/OPTIMIZATION_PLAYBOOK.md §10, phase 5).
//
// WHY A BROWSER. scripts/build_vector_tiles.py holds each archive to the FILE,
// which proves the tile and the file contain the same districts. It cannot
// prove the CARD is the same, because a card is the layer's own query code:
// a loader can reshape features after the fetch, a query can join a roster by
// a property, read two layers at once, or collect every overlapping feature,
// and none of that runs in Python. So this boots each app, and for each layer
// registered with `tiles:` asks the app itself (tileCardCheck, engine
// `exports`) to run that layer's query at the same points twice — from the
// tile under each point, then from the whole file — and compares the two
// results as the card receives them, with `seq` and any `geometry` dropped.
//
// WHICH POINTS. For each layer, pairs of points either side of randomly chosen
// district edges, 3-25 m out, so neighbouring districts are both asked, and a
// few more well inside districts. The archives are gated to answer as the file
// does at every point 2 m or more from an edge, so a point is kept only if it
// is that far from EVERY edge: 3-25 m from the chosen edge can still be on
// another one at a corner, and the first CI run of phase 5b failed five
// layers on points 0.09-0.48 m from a second edge. Seeded PER LAYER, from the
// layer's own name, so adding a layer does not move another layer's points.
//
// One fresh page per layer: a layer whose whole file is loaded answers every
// later query from it, so a page shared between layers would stop testing the
// tile path for any loader two layers share.
//
//     python3 -m http.server 8000     # serve the repo first
//     node scripts/probe_tile_cards.mjs              # every tiled layer
//     TAGS=wi LAYERS=county node scripts/probe_tile_cards.mjs
//
// BASE_URL overrides the server; POINTS the pairs per layer (default 20).
//
// A COUNTY-DISPATCHED LAYER (phase 5b) holds only its shipped counties in
// its archive. Its points come from those counties' files, and each answer
// says which county gave it and whether that county is in the archive: a
// point over a county line into a live county, or a county whose entry calls
// its loader directly, is answered from its own source by design and is
// counted, not failed. What fails is a card or a HOVER name that differs:
// the canvas names a district from the tile's own properties, with nothing a
// loader adds after its fetch. EVERY county with a file of its own is also
// asked at up to three points inside its districts, and fails if no county
// answers any of them. And every county the ARCHIVE holds is checked whole,
// with no points at all: its own files, run through its loader's `decorate`,
// must give exactly the features its loader returns (countyStampCheck). A
// loader that adds a property, filters or merges outside withStamp fails here
// the day its county enters the archive, wherever the points happen to land.
//
// EVERY ANSWER FROM ANOTHER HOST IS HELD FOR BOTH RUNS (2026-10-16). A card
// can join data no tile carries — New York's precinct card names the station
// house from a live city dataset — and the two runs used to fetch it each for
// themselves. On 2026-10-16 the city refused that request once and answered
// it moments later, so the first point of the tile run printed no station and
// the file run printed one, and the check failed on a change to Indiana. Each
// layer's page now asks every other host once, through `heldAnswers`, and both
// runs read that one answer, a failure included. The comparison is tile
// against file, so nothing else may vary between the two.
//
// ONE THING STILL CAN: the page's own patience. A loader gives up after its
// own timeout, so an answer that arrives later reaches the second run and not
// the first. When a layer differs AND the page gave up on a held request while
// it was comparing, that layer is run once more on a fresh page, where every
// answer is already held and arrives at once, and that run's result stands.
// With no such request there is no second run: a real difference between a
// tile and its file comes back exactly, because nothing else in it varies.
//
// THE SET A MIRRORED LAYER WAS BUILT FROM IS FETCHED ONCE, BEFORE ITS PAGE
// OPENS, waiting longer between tries — the other failure that day was the
// city answering 503 four times in fifteen seconds — and the page's own
// request for that set is answered from the same copy.
//
// AND IT IS KEPT BETWEEN RUNS WHERE PROBE_SET_CACHE NAMES A DIRECTORY
// (2026-10-20). Fetching every set again was 1,067 s of this probe's 1,392 s
// on that day's every-instance run, about a gigabyte from the Census Bureau
// and three city portals, 643 s of it for the ZIP layers. A set is filed
// under its record's data_sha256, query and page size, so a set whose record
// moves (the weekly mirror jobs rewrite a record when its source changes) is
// fetched afresh and any other is read back exactly as it was fetched. Only a
// response carrying a features array is kept, so a server's error answer is
// never read back on the next run, and a directory no current record names
// is removed at the end. Without the variable every set is fetched as before.
//
// AND ONLY THE INSTANCES A CHANGE CAN REACH ARE PROBED. On a pull request the
// files it changes are read against its base and against this workflow's own
// trigger paths: a file under one instance reaches that instance, and a
// trigger path outside every instance (the engine, this probe, the mirror
// records) reaches all of them. Both failures were on a change to Indiana,
// which draws nothing from tiles. TAGS still names instances outright, and a
// run that is not a pull request probes every instance.

import { chromium, request } from "playwright";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { appendFileSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, renameSync, rmSync,
  writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { ROOT, instances, vendorDir } from "./probe_points.mjs";
import { stubBasemap } from "./basemap_stub.mjs";

const BASE = (process.env.BASE_URL || "http://localhost:8000").replace(/\/+$/, "") + "/";
const PAIRS = +(process.env.POINTS || 20);
const ONLY = process.env.LAYERS ? new Set(process.env.LAYERS.split(",")) : null;
const SOURCES = JSON.parse(readFileSync(join(ROOT, "layer-sources.json"), "utf8"));
// EVERY mirror's record, not one of them: an archive mirrored by any of them
// ships no file, and reading tiger-mirror.json alone reported each portal
// archive as a layer with nowhere to place points (tile_mirror_common.RECORDS).
const MIRROR = Object.assign({}, ...["tiger-mirror.json", "portal-mirror.json"].map((f) =>
  existsSync(join(ROOT, f)) ? JSON.parse(readFileSync(join(ROOT, f), "utf8")).layers : {}));

// A portal record's query is the route the app itself calls, with the app
// token left off (scripts/mirror_portal_tiles.py); NYC's portal refuses an
// untokened request, so the token comes from that app's own index.html, which
// is where it lives.
const APP_TOKEN = {};
function appToken(tag) {
  if (!(tag in APP_TOKEN)) {
    const m = readFileSync(join(ROOT, tag, "index.html"), "utf8")
      .match(/var\s+SOCRATA_APP_TOKEN\s*=\s*"([^"]*)"\s*;/);
    APP_TOKEN[tag] = m ? m[1] : "";
  }
  return APP_TOKEN[tag];
}

// The trigger paths of the workflow that runs this probe, read rather than
// restated, so a path added there reaches the scope below with nothing to edit
// here. A pattern under `*/` is one instance's; any other is shared.
function triggerPaths() {
  const yml = readFileSync(join(ROOT, ".github", "workflows", "vector-tiles.yml"), "utf8").split("\n");
  const out = [];
  let inPaths = false, indent = -1;
  for (const line of yml) {
    const m = line.match(/^(\s*)paths:\s*$/);
    if (m) { inPaths = true; indent = m[1].length; continue; }
    if (!inPaths) continue;
    const item = line.match(/^(\s*)-\s*"([^"]+)"/);
    if (item && item[1].length > indent) { out.push(item[2]); continue; }
    if (/^\s*(#.*)?$/.test(line)) continue;
    if ((line.match(/^\s*/)[0].length) <= indent) break;
  }
  return out;
}
function globRe(glob) {
  return new RegExp("^" + glob.split("**").map((part) =>
    part.split("*").map((t) => t.replace(/[.+?^${}()|[\]\\]/g, "\\$&")).join("[^/]*")).join(".*") + "$");
}
// The probe's own imports are read as triggers too: neither chooses the points
// it probes or answers a card today, but a change to one is a change to this
// probe.
const PROBE_FILES = ["scripts/probe_points.mjs", "scripts/basemap_stub.mjs"];

// Which instances this change can reach, or null for every instance.
function changedTags(all) {
  const base = process.env.GITHUB_BASE_REF;
  if (!base) return null;
  const paths = triggerPaths();
  if (!paths.length) {
    console.log("  note  no trigger paths read from vector-tiles.yml; probing every instance");
    return null;
  }
  let files;
  try {
    files = execFileSync("git", ["diff", "--name-only", `origin/${base}...HEAD`], { cwd: ROOT, encoding: "utf8" })
      .split("\n").filter(Boolean);
  } catch (e) {
    console.log(`  note  could not read the change against origin/${base} (${String(e).split("\n")[0].slice(0, 160)}); probing every instance`);
    return null;
  }
  const shared = paths.filter((p) => !p.startsWith("*/")).map(globRe);
  const own = paths.filter((p) => p.startsWith("*/")).map(globRe);
  const tags = new Set();
  for (const f of files) {
    if (PROBE_FILES.includes(f) || shared.some((re) => re.test(f))) {
      console.log(`  scope ${f} is shared by every instance, so every instance is probed`);
      return null;
    }
    const top = f.split("/")[0];
    if (all.includes(top) && own.some((re) => re.test(f))) tags.add(top);
  }
  return [...tags].sort();
}

// The hosts that only paint the map: no card reads them, so they are left out
// of heldAnswers and answered by the basemap stand-in (scripts/basemap_stub.mjs).
const PAINT_ONLY = /(^|\.)basemaps\.cartocdn\.com$/;
// statuses worth asking again: a rate limit, and a server's own outage
const TRANSIENT = new Set([408, 429, 500, 502, 503, 504]);
// what a fulfilled response must not repeat: the body is already decoded,
// and its length is the body's own
const DROP_HEADERS = new Set(["content-encoding", "content-length", "transfer-encoding", "connection", "set-cookie"]);
// one request context for every held fetch, so a fetch outlives the page that
// first asked for it and the layer's second page finds it finished
const API = await request.newContext();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const keyOf = (method, url, body) => `${method} ${new URL(url).href} ${body || ""}`;

// One answer per request for one layer: the first asks the network, up to four
// times a second or more apart when the answer is a rate limit or an outage,
// and every identical request after it, in either run, gets exactly that.
function heldAnswers() {
  const map = new Map();
  return {
    seed(url, body) {
      map.set(keyOf("GET", url), Promise.resolve({ status: 200, headers: { "content-type": "application/json" }, body }));
    },
    get(req) {
      const k = keyOf(req.method(), req.url(), req.postData());
      if (!map.has(k)) {
        const headers = Object.assign({}, req.headers());
        delete headers["accept-encoding"];
        map.set(k, (async () => {
          let last = null;
          for (let i = 0; i < 4; i++) {
            if (i) await sleep(1000 * 2 ** (i - 1)); // 1, 2 and 4 s
            try {
              const r = await API.fetch(req.url(), { method: req.method(), headers, data: req.postDataBuffer() || undefined,
                timeout: 120000, failOnStatusCode: false });
              last = { status: r.status(), headers: r.headers(), body: await r.body() };
              if (!TRANSIENT.has(last.status)) return last;
            } catch (e) {
              last = { failed: String(e && e.message || e).split("\n")[0] };
            }
          }
          return last;
        })());
      }
      return map.get(k);
    }
  };
}

// a fresh page for one layer, with every other host answered from `held`;
// `gaveUp` counts the held requests the page abandoned while comparing
async function openPage(tag, held, referenceSet) {
  const ctx = await browser.newContext({ serviceWorkers: "block" });
  const page = await ctx.newPage();
  const base = new URL(BASE).origin;
  const inflight = new Set();
  const state = { comparing: false, gaveUp: 0 };
  page.on("requestfailed", (r) => {
    if (state.comparing && inflight.has(r) && /ERR_ABORTED/.test((r.failure() || {}).errorText || "")) state.gaveUp++;
  });
  // registered first, so every route below takes precedence over it
  await page.route((u) => u.origin !== base && !PAINT_ONLY.test(u.hostname), async (route) => {
    const req = route.request();
    inflight.add(req);
    const got = await held.get(req);
    try {
      if (got.failed) await route.abort("failed");
      else {
        const headers = {};
        for (const [k, v] of Object.entries(got.headers)) if (!DROP_HEADERS.has(k.toLowerCase())) headers[k] = v;
        await route.fulfill({ status: got.status, headers, body: got.body });
      }
    } catch { /* the page had already given up on this request, or closed */ }
    inflight.delete(req);
  });
  const dir = vendorDir(tag);
  await page.route(/cdnjs\.cloudflare\.com/, (route) => {
    const f = new URL(route.request().url()).pathname.split("/").pop();
    if (existsSync(join(dir, f)))
      return route.fulfill({ body: readFileSync(join(dir, f)),
        contentType: f.endsWith(".css") ? "text/css" : "application/javascript" });
    return route.fallback();
  });
  if (referenceSet) {
    const body = JSON.stringify(referenceSet);
    // only the whole-set envelope query; a point query is not answered here
    await page.route((u) => /PUMA_TAD_TAZ_UGA_ZCTA/.test(u.href) && /esriGeometryEnvelope/.test(decodeURIComponent(u.href)),
      (route) => route.fulfill({ body, contentType: "application/json" }));
  }
  return { ctx, page, state };
}

// curl for the sets a mirrored layer was built from: it honours a proxy where
// Node's fetch does not, and it waits 1, 2, 4, 8, 16 and 32 s between tries.
// A request the server accepts and then answers with nothing is dropped after
// a minute and asked again: on 2026-10-16 New York City's open data site held
// one open for the whole ten minutes --max-time allows with no byte sent,
// which left no time for a second try, and the layer failed on that alone.
const CURL_RETRY = ["--retry", "6", "--retry-all-errors", "--retry-max-time", "240",
  "--speed-limit", "1", "--speed-time", "60"];

// The body goes to a file, never to stdout. curl truncates a file before it
// tries again, but it cannot take back what it already wrote to stdout, so a
// download that stalled part-way and was retried came back as the partial
// body followed by the whole one, and JSON.parse failed where the two met
// (il:cps-high and ny:es-zone on 2026-10-16, on two runs of one commit).
// Every call is timed, so a run's log says how much of its time went to these
// downloads rather than to the browser.
let fetchMs = 0;
function curlBody(args) {
  const dir = mkdtempSync(join(tmpdir(), "probe-tile-cards-"));
  const out = join(dir, "body");
  const started = Date.now();
  try {
    execFileSync("curl", [...args.slice(0, -1), "-o", out, args[args.length - 1]], { stdio: ["ignore", "ignore", "inherit"] });
    return readFileSync(out);
  } finally {
    fetchMs += Date.now() - started;
    rmSync(dir, { recursive: true, force: true });
  }
}
const secs = (ms) => `${(ms / 1000).toFixed(1)} s`;

// One part of a mirrored layer's set ("whole", or a page's offset), read back
// from the kept copy when there is one (see the header) and fetched by curl
// otherwise. Returns the bytes, which seed the page's own request, and their
// parse.
const KEEP = process.env.PROBE_SET_CACHE || "";
const kept = { read: 0, fetched: 0 };
const keptName = (rec) => createHash("sha256")
  .update(`${rec.data_sha256}\n${rec.query}\n${rec.page_size || ""}`).digest("hex").slice(0, 32);
function fetchSet(rec, part, args) {
  const file = KEEP && rec.data_sha256 ? join(KEEP, keptName(rec), `${part}.json`) : null;
  if (file && existsSync(file)) {
    const raw = readFileSync(file);
    try {
      const json = JSON.parse(raw);
      kept.read++;
      return { raw, json };
    } catch {
      rmSync(file, { force: true }); // a damaged copy is fetched again
    }
  }
  const raw = curlBody(args);
  const json = JSON.parse(raw);
  if (file && Array.isArray(json.features) && !json.error) {
    mkdirSync(join(KEEP, keptName(rec)), { recursive: true });
    writeFileSync(`${file}.part`, raw);
    renameSync(`${file}.part`, file);
    kept.fetched++;
  }
  return { raw, json };
}
// the kept sets no current record names, removed; returns how many
function pruneKept() {
  if (!KEEP || !existsSync(KEEP)) return 0;
  const want = new Set(Object.values(MIRROR).filter((r) => r.data_sha256).map(keptName));
  let n = 0;
  for (const name of readdirSync(KEEP)) {
    if (want.has(name)) continue;
    rmSync(join(KEEP, name), { recursive: true, force: true });
    n++;
  }
  return n;
}

const EDGE_TOLERANCE_M = 2; // scripts/build_vector_tiles.py's gate
let seed = 13;
function rnd() { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }
function seedFor(name) {
  let h = 13;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 2147483648;
  seed = h;
}
// metres from the point to the nearest edge of any feature, in a local
// equirectangular frame (exact enough at a few metres)
function edgeDistanceM(pt, polys) {
  const kx = 111320 * Math.cos(pt.lat * Math.PI / 180), ky = 110574;
  let best = Infinity;
  for (const f of polys) {
    for (const ring of rings(f.geometry)) {
      for (let i = 1; i < ring.length; i++) {
        const ax = (ring[i - 1][0] - pt.lng) * kx, ay = (ring[i - 1][1] - pt.lat) * ky;
        const bx = (ring[i][0] - pt.lng) * kx, by = (ring[i][1] - pt.lat) * ky;
        const dx = bx - ax, dy = by - ay, len2 = dx * dx + dy * dy;
        const t = len2 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / len2)) : 0;
        const d = Math.hypot(ax + t * dx, ay + t * dy);
        if (d < best) best = d;
      }
    }
  }
  return best;
}

function rings(geom) {
  if (!geom) return [];
  if (geom.type === "Polygon") return geom.coordinates;
  if (geom.type === "MultiPolygon") return geom.coordinates.flat();
  return [];
}

// Points either side of an edge and inside districts, in longitude/latitude.
function pointsFor(features) {
  const polys = features.filter((f) => rings(f.geometry).length);
  const out = [];
  for (let i = 0; i < PAIRS && polys.length; i++) {
    const f = polys[Math.floor(rnd() * polys.length)];
    const rs = rings(f.geometry);
    const ring = rs[Math.floor(rnd() * rs.length)];
    if (!ring || ring.length < 2) continue;
    const k = Math.floor(rnd() * (ring.length - 1));
    const [x1, y1] = ring[k], [x2, y2] = ring[k + 1];
    const t = rnd(), mx = x1 + (x2 - x1) * t, my = y1 + (y2 - y1) * t;
    const kx = 111320 * Math.cos(my * Math.PI / 180), ky = 110574;
    const dx = (x2 - x1) * kx, dy = (y2 - y1) * ky, len = Math.hypot(dx, dy);
    if (!len) continue;
    const d = 3 + rnd() * 22, nx = -dy / len, ny = dx / len;
    out.push({ lng: mx + nx * d / kx, lat: my + ny * d / ky });
    out.push({ lng: mx - nx * d / kx, lat: my - ny * d / ky });
  }
  // a few well inside: a vertex pulled halfway toward its ring's centroid
  for (let i = 0; i < Math.ceil(PAIRS / 2) && polys.length; i++) {
    const ring = rings(polys[Math.floor(rnd() * polys.length)].geometry)[0];
    if (!ring || !ring.length) continue;
    const cx = ring.reduce((a, p) => a + p[0], 0) / ring.length;
    const cy = ring.reduce((a, p) => a + p[1], 0) / ring.length;
    const v = ring[Math.floor(rnd() * ring.length)];
    out.push({ lng: (v[0] + cx) / 2, lat: (v[1] + cy) / 2 });
  }
  const kept = out.filter((p) => edgeDistanceM(p, polys) >= EDGE_TOLERANCE_M);
  kept.dropped = out.length - kept.length;
  return kept;
}

function inRings(pt, rs) {
  let inside = false;
  for (const ring of rs) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if ((yi > pt.lat) !== (yj > pt.lat) && pt.lng < (xj - xi) * (pt.lat - yi) / (yj - yi) + xi) inside = !inside;
    }
  }
  return inside;
}

// A point inside a district of EACH county, so every county's own entry is
// asked at least once: random edge points reach only a few dozen counties, and
// the first CI run with a fixed seed per layer failed on Boone, whose library
// loader stamped its officials outside withStamp — a county the earlier seed
// had never landed in.
function countyPoint(features, all) {
  const polys = features.filter((f) => rings(f.geometry).length);
  for (let attempt = 0; attempt < 12 && polys.length; attempt++) {
    const f = polys[Math.floor(rnd() * polys.length)];
    const rs = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
    const ring = rs[Math.floor(rnd() * rs.length)][0];
    if (!ring || !ring.length) continue;
    const cx = ring.reduce((a, p) => a + p[0], 0) / ring.length;
    const cy = ring.reduce((a, p) => a + p[1], 0) / ring.length;
    const v = ring[Math.floor(rnd() * ring.length)], t = 0.3 + rnd() * 0.6;
    const pt = { lng: v[0] + (cx - v[0]) * t, lat: v[1] + (cy - v[1]) * t };
    if (!rs.some((poly) => inRings(pt, poly))) continue;
    if (edgeDistanceM(pt, all) >= EDGE_TOLERANCE_M) return pt;
  }
  return null;
}

function tiledLayers(tag) {
  const html = readFileSync(join(ROOT, tag, "index.html"), "utf8");
  const ids = new Set();
  // an archive is named for the layer that registers it
  for (const m of html.matchAll(/\btiles:\s*"data\/app\/tiles\/([^"/]+)\.pmtiles"/g)) ids.add(m[1]);
  return [...ids].filter((id) => !ONLY || ONLY.has(id)).sort();
}

const FIND = "Object.keys(window).map((k) => window[k]).find((v) => v && typeof v === 'object' && typeof v.tileCardCheck === 'function')";

const ALL = instances();
const SCOPE = process.env.TAGS ? null : changedTags(ALL);
const TAGS = process.env.TAGS ? process.env.TAGS.split(",") : (SCOPE || ALL);
if (SCOPE) console.log(`  scope this change reaches ${SCOPE.length ? SCOPE.join(", ") : "no instance"}; ` +
  `the other ${ALL.length - SCOPE.length} instance(s) draw nothing it changed, so they are not probed`);

let problems = 0, compared = 0, answered = 0, layersDone = 0;
const runStarted = Date.now();
const browser = stubBasemap(await chromium.launch());
try {
  for (const tag of TAGS) {
    const layers = tiledLayers(tag);
    if (!layers.length) continue;
    for (const id of layers) {
      const layerStarted = Date.now(), fetchedBefore = fetchMs;
      const rec = SOURCES.apps[tag] && SOURCES.apps[tag].layers[id];
      const countyFiles = rec && rec.counties && rec.counties.files;
      const files = countyFiles ? Object.values(countyFiles).flat() : ((rec && rec.files) || []);
      const feats = files.flatMap((f) => {
        const p = join(ROOT, f.replace(/^\/+/, ""));
        return existsSync(p) ? (JSON.parse(readFileSync(p, "utf8")).features || []) : [];
      });
      // a layer mirrored from a live source (scripts/mirror_tiger_tiles.py)
      // ships no file: its points come from the set the record says was
      // fetched, asked for again through curl (which honours a proxy where
      // Node's fetch does not). Esri rings are enough to place points.
      // THE REFERENCE FOR A BOX-FETCHED LAYER IS THE SET ITS ARCHIVE WAS BUILT
      // FROM, NOT THE APP'S OWN WHOLE SET. The ZIP layers' whole-set loader asks
      // the server for a ~55 m simplification, while their archives are built
      // at full detail and in-state only, so near every edge the two disagree
      // because the tile is the more accurate. The app's whole-set request is
      // answered below from this set instead; the mirror's own gate already
      // holds the archive to it.
      let referenceSet = null;
      const held = heldAnswers();
      if (!feats.length && MIRROR[`${tag}:${id}`] && MIRROR[`${tag}:${id}`].dataset) {
        // a layer mirrored from a city open-data portal: the record's route is
        // already GeoJSON, and the app's own whole-set loader calls the SAME
        // route at the same detail, so there is no reference set to override —
        // only points to place.
        const rec = MIRROR[`${tag}:${id}`];
        const tok = appToken(tag);
        const url = rec.query + (tok ? (rec.query.includes("?") ? "&" : "?") + "$$app_token=" + tok : "");
        try {
          const { raw, json: fc } = fetchSet(rec, "whole", ["-sS", "--fail", "-L", "--max-redirs", "5", ...CURL_RETRY,
            "--max-time", "600", "-A", "districtry portal-tile mirror (+https://districtry.com/)", url]);
          for (const f of fc.features || []) if (f.geometry) feats.push(f);
          // the app's whole-set loader calls this same route with this same
          // token, so its file run reads these bytes rather than asking again
          held.seed(url, raw);
        } catch (e) {
          console.log(`  FAIL  ${tag}:${id} — could not fetch the mirrored set to place points: ${String(e).slice(0, 200)}`);
          problems++; continue;
        }
      } else if (!feats.length && MIRROR[`${tag}:${id}`]) {
        try {
          // A box-fetched layer (the ZIP layers) is recorded with the page size
          // its mirror fetched at, because the server cannot answer it whole.
          const rec = MIRROR[`${tag}:${id}`];
          for (let offset = 0; ; ) {
            const url = rec.page_size
              ? `${rec.query}&resultOffset=${offset}&resultRecordCount=${rec.page_size}` : rec.query;
            // --retry-all-errors: without it curl's --retry skips a reset
            // connection (exit 35), which is how a CI run lost ia:municipality
            // on 2026-09-27 with three retries unspent.
            const { raw, json: page } = fetchSet(rec, rec.page_size ? String(offset) : "whole", ["-sS", "--fail",
              ...CURL_RETRY, "--max-time", "300", "-A", "districtry tiger-tile mirror (+https://districtry.com/)", url]);
            // a set fetched whole is held under its own query, which the app's
            // loader may or may not ask in exactly this form
            if (!rec.page_size) held.seed(url, raw);
            const got = page.features || [];
            if (rec.page_size && !referenceSet) referenceSet = Object.assign({}, page, { features: [] });
            // an in-state mirror keeps only some of the box (rec.kept); a point in
            // a ZCTA it dropped has no tile answer by design, so none is placed there
            const kept = rec.kept ? new Set(rec.kept.split(",")) : null;
            for (const f of got) {
              if (kept && !kept.has(String((f.attributes || {}).ZCTA5))) continue;
              if (referenceSet) referenceSet.features.push(f);
              if (f.geometry && f.geometry.rings) feats.push({ geometry: { type: "Polygon", coordinates: f.geometry.rings } });
            }
            offset += got.length;
            if (!rec.page_size || !got.length || !page.exceededTransferLimit) break;
          }
        } catch (e) {
          console.log(`  FAIL  ${tag}:${id} — could not fetch the mirrored set to place points: ${String(e).slice(0, 200)}`);
          problems++; continue;
        }
      }
      if (!feats.length) { console.log(`  FAIL  ${tag}:${id} — layer-sources.json names no file to place points in`); problems++; continue; }
      seedFor(`${tag}:${id}`);
      const pts = pointsFor(feats);
      // county key -> the index of its own point, for the check below
      const countyAt = {};
      if (countyFiles) {
        const allPolys = feats.filter((f) => rings(f.geometry).length);
        for (const [key, list] of Object.entries(countyFiles).sort(([a], [b]) => a.localeCompare(b))) {
          const own = list.flatMap((f) => {
            const p = join(ROOT, f.replace(/^\/+/, ""));
            return existsSync(p) ? (JSON.parse(readFileSync(p, "utf8")).features || []) : [];
          });
          // three tries: a county's file can hold a district running over
          // its line, and a point there is the neighbour's to answer
          for (let n = 0; n < 3; n++) {
            const pt = countyPoint(own, allPolys);
            if (pt) { (countyAt[key] = countyAt[key] || []).push(pts.length); pts.push(pt); }
          }
        }
      }
      if (referenceSet) delete referenceSet.exceededTransferLimit;
      async function compare() {
        const { ctx, page, state } = await openPage(tag, held, referenceSet);
        try {
          await page.goto(`${BASE}${tag}/`, { waitUntil: "domcontentloaded" });
          await page.waitForFunction(`!!(${FIND})`, null, { timeout: 60000 });
          state.comparing = true;
          const res = await page.evaluate(`(${FIND}).tileCardCheck(${JSON.stringify(id)}, ${JSON.stringify(pts)})`);
          state.comparing = false;
          const stamps = countyFiles
            ? await page.evaluate(`(${FIND}).countyStampCheck(${JSON.stringify(id)}, ${JSON.stringify(countyFiles)})`) : null;
          return { res, stamps, gaveUp: state.gaveUp };
        } finally {
          await ctx.close();
        }
      }
      let res, stamps = null, rerun = null;
      try {
        let got = await compare();
        // a difference while the page gave up on a held answer: once more,
        // with every answer already held (see the header)
        if (got.gaveUp && got.res.some((r) => r.tiles !== r.file)) {
          rerun = got.gaveUp;
          got = await compare();
        }
        ({ res, stamps } = got);
      } catch (e) {
        console.log(`  FAIL  ${tag}:${id} — ${String(e).slice(0, 200)}`);
        problems++;
        continue;
      }
      const county = res.some((r) => "inArchive" in r);
      // the tile path must be what answered: a query reaching its boundaries
      // another way compares equal while downloading the whole file. For a
      // county layer, only where the answering county's entry reads its
      // boundaries through queryFeatureAt at all; the rest are counted below
      const notTiled = county ? [] : res.filter((r) => !r.viaTiles && !r.hidden);
      // a point the layer's own coverage rejects is never queried: the app
      // hides the layer there, so there is no card to compare (tileCardCheck)
      const hidden = res.filter((r) => r.hidden).length;
      const hoverBad = res.filter((r) => r.hoverTiles != null && r.hoverTiles !== r.hoverFile);
      // a county layer's live counties answer from their own servers, so an
      // error in BOTH runs is that server, not the tiles: the file run reads an
      // archived county from same-origin files and touches the network only
      // for a live one. The two messages need not match — one run can time out
      // ("signal is aborted") where the other fails to connect ("Failed to
      // fetch"), which failed CI on 2026-09-27 at a southern live county. One
      // run erroring alone is still a difference, and stays in `bad`
      // ... and ONLY for a point the archive does not hold: an archived
      // county's both runs read this site's own files and tiles, so an error
      // in both is a real failure, never somebody else's outage. A point whose
      // archive status is unknown (null) is not forgiven either.
      const sameErr = (r) => county && r.inArchive === false && /^error:/.test(r.tiles || "") && /^error:/.test(r.file || "");
      const bad = res.filter((r) => r.tiles !== r.file && !sameErr(r));
      const errs = res.filter((r) => !sameErr(r) && (/^error:/.test(r.tiles || "") || /^error:/.test(r.file || "") ||
        /^error:/.test(r.hoverTiles || "")));
      const liveErrs = res.filter(sameErr);
      compared += res.length;
      answered += res.filter((r) => r.file && !/^error:/.test(r.file)).length;
      layersDone++;
      // every county whose own file placed points must have answered one of
      // them, or its entry was never asked; a county whose every point fell
      // in a neighbour's ground is named, not failed — nothing differed there
      const unasked = [], elsewhere = [];
      for (const [key, idx] of Object.entries(countyAt)) {
        if (idx.some((i) => res[i] && res[i].county === key)) continue;
        const by = [...new Set(idx.map((i) => res[i] && res[i].county).filter(Boolean))];
        if (by.length) elsewhere.push(`${key} (answered by ${by.join(", ")})`); else unasked.push(key);
      }
      // every archived county, whole: its files through its loader's decorate
      // must be what its loader returns (engine `exports`, countyStampCheck)
      const stampBad = (stamps || []).filter((r) => r.problem);
      const ok = !bad.length && !errs.length && !notTiled.length && !hoverBad.length && !unasked.length && !stampBad.length;
      console.log(`  ${ok ? "ok  " : "FAIL"}  ${tag}:${id} — ${res.length} points (${pts.dropped} dropped within ${EDGE_TOLERANCE_M} m of an edge), ${res.filter((r) => r.file).length} with a district, ` +
        (hidden ? `${hidden} outside the layer's coverage and skipped, ` : "") +
        `${bad.length} differ, ${errs.length} errored` +
        (county ? `, ${hoverBad.length} hover names differ` : `, ${notTiled.length} not answered from tiles`));
      if (rerun) console.log(`          the first run differed while the page gave up waiting on ${rerun} answer(s) from another host; ` +
        "this is the second run, with every answer already held");
      if (fetchMs > fetchedBefore) console.log(`          ${secs(fetchMs - fetchedBefore)} of this layer's ${secs(Date.now() - layerStarted)} ` +
        "went to fetching the set its archive was built from");
      if (county) {
        const byCounty = {};
        for (const r of res) {
          if (!r.county) continue;
          const c = byCounty[r.county] = byCounty[r.county] || { in: r.inArchive, tiles: 0, n: 0 };
          c.n++; if (r.viaTiles) c.tiles++;
        }
        const archived = Object.entries(byCounty).filter(([, c]) => c.in);
        const own = archived.filter(([, c]) => !c.tiles).map(([k]) => k);
        console.log(`          ${archived.length} archived counties answered, ${archived.length - own.length} from tiles` +
          (own.length ? `; from their own file (the entry reads its loader directly): ${own.join(", ")}` : "") +
          `; ${Object.keys(byCounty).length - archived.length} live counties answered from their own source` +
          (liveErrs.length ? `; ${liveErrs.length} point(s) errored in both runs, a live source this run could not reach` : ""));
      }
      if (stamps) console.log(`          ${stamps.length} archived counties checked whole: ${stamps.length - stampBad.length} load exactly what their files give through decorate` +
        (stampBad.length ? `; ${stampBad.length} do not` : ""));
      for (const r of stampBad.slice(0, 5)) console.log(`          ${r.key}: ${r.problem}`);
      if (unasked.length) console.log(`          a point inside a district of these counties was answered by no county: ${unasked.join(", ")}`);
      if (elsewhere.length) console.log(`          every point placed in these counties' files fell in a neighbour's ground: ${elsewhere.join("; ")}`);
      for (const r of [...bad, ...errs].slice(0, 3)) {
        console.log(`          ${r.point.lat.toFixed(6)},${r.point.lng.toFixed(6)}: tiles ${String(r.tiles).slice(0, 160)} | file ${String(r.file).slice(0, 160)}`);
      }
      for (const r of hoverBad.slice(0, 3)) {
        console.log(`          ${r.point.lat.toFixed(6)},${r.point.lng.toFixed(6)}: hover from the tile ${r.hoverTiles} | from the file ${r.hoverFile}`);
      }
      if (!ok) problems++;
    }
  }
} finally {
  await browser.close();
  await API.dispose();
  if (KEEP) {
    const pruned = pruneKept();
    console.log(`  kept  ${kept.read} part(s) of the mirrored sets read from the kept copy, ${kept.fetched} fetched and kept` +
      (pruned ? `, ${pruned} set(s) no record names any more removed` : ""));
    // the workflow saves the copy only when this run added to it
    if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT, `fetched=${kept.fetched}\n`);
  }
}
if (layersDone || problems) console.log(`  time  ${secs(Date.now() - runStarted)} in all, ${secs(fetchMs)} of it fetching the sets mirrored layers were built from`);
if (!layersDone && !problems) {
  console.log(SCOPE ? "probe-tile-cards: OK — no instance this change reaches draws a layer from tiles"
    : "probe-tile-cards: OK — no layer is drawn from tiles");
  process.exit(0);
}
if (problems) { console.log(`probe-tile-cards: FAIL — ${problems} layer(s) failed: a card that differs, an error, or a page that did not boot (each is named above)`); process.exit(1); }
console.log(`probe-tile-cards: OK — ${layersDone} layer(s), ${compared} points (${answered} inside a district): every card from tiles matches the card from the whole file`);
