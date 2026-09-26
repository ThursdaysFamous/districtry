// Measure which layers fetch their SHAPES from another host at runtime, in a
// real browser, and write layer-sources.json at the repo root.
//
// WHY A BROWSER. A layer's boundary can come from its own shipped file under
// data/app, from a government service downloaded whole on first toggle, or from
// a service asked about the reader's point, and the code does not say which in
// one place: a registration factory builds many layers from one call, and
// registerCountyLayer closes over its entries, so Illinois's ward layer has 28
// sources and nothing static lists them. scripts/probe_point_transmission.mjs
// found the same thing about points. So this boots each app, switches on ONE
// layer per page, and records every request the page makes to another host.
//
// WHAT COUNTS AS A SHAPE. Every cross-origin request (bar the basemap, the
// library CDN, analytics and the geocoders) is fetched for real through Node,
// and its body is read: a response carrying polygon or line geometry is a
// shape, one carrying only points is a point dataset (stations, schools), and
// anything else is a roster or a lookup. The layer's own loaded geometry types
// come from the app (`layerSources`), which is how a layer drawn from our own
// files is told apart from a point layer.
//
// WHAT IS SUBTRACTED. Outside Chicago the Illinois app fetches the city's
// community areas, the Lake Michigan outline and the state's county outlines
// for its coverage tests with no layer on at all. So each point is also loaded
// with NO layer, those requests are subtracted at THAT point and recorded once
// as `app_level`, rather than charged to whichever layer happened to be on. A
// sub-layer switches its parent on too, so the parent's requests at the same
// point are subtracted from it as well; one drawing the very set its parent
// loaded (`sharesParentLoader`) makes no request of its own and is recorded as
// fetched through its parent.
//
// COUNTY-DISPATCHED LAYERS are measured a second way. With the layer on, the
// page loads every county entry at once and the requests cannot be told apart,
// so a separate page with no layer on loads each entry in turn through
// `loadCountyEntry` and attributes what it fetched to that county. That also
// reaches counties the selected point is nowhere near.
//
// LIMITS, stated rather than implied. It selects each instance's worksheet
// anchor plus the extra points in probe_points.mjs, so a layer whose fetch
// depends on where the reader is could fetch more elsewhere (county entries
// excepted). A source that does not answer from where the probe runs is
// recorded under `unanswered` rather than guessed at. And the answer is a
// snapshot. .github/workflows/update-layer-sources.yml re-runs it weekly and
// opens a pull request when a result changes, but nothing FAILS when it is
// stale: the endpoint inventory prints the date it was measured and names any
// layer the worksheet declares that the file does not describe.
//
//     python3 -m http.server 8000                 # serve the repo first
//     node scripts/probe_layer_sources.mjs        # measure every instance (~20 min)
//     TAGS=il,wi node scripts/probe_layer_sources.mjs   # re-measure some, keep the rest
//     python3 scripts/build_endpoint_inventory.py # then regenerate the table
//
// In a sandbox whose Node reaches the network only through a proxy, run it with
// NODE_USE_ENV_PROXY=1. BASE_URL overrides the server; CONC the page count.

import { chromium } from "playwright";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { ROOT, anchorOf, EXTRA_POINTS, instances, vendorDir } from "./probe_points.mjs";

const OUT = join(ROOT, "layer-sources.json");
const BASE = (process.env.BASE_URL || "http://localhost:8000").replace(/\/+$/, "") + "/";
const CONC = +(process.env.CONC || 5);
const ALL = instances();
const TAGS = process.env.TAGS ? process.env.TAGS.split(",") : ALL;
// Hosts that are not a layer's source: the basemap, the Leaflet/MapLibre CDN,
// analytics and the geocoders. Aborted, never fetched.
const SKIP_HOST = /(cdnjs\.cloudflare\.com|cartocdn\.com|zgo\.at|goatcounter\.com|photon\.komoot\.io|nominatim\.openstreetmap\.org|fonts\.(googleapis|gstatic)\.com|googletagmanager\.com|google-analytics\.com)$/;
const SHAPE = /"rings"\s*:|"paths"\s*:|"(Multi)?(Polygon|LineString)"|esriGeometry(Polygon|Polyline)/;
const POINTS = /"(x|coordinates)"\s*:|"Point"|esriGeometryPoint/;
// A request that sends the reader's point rather than asking for a whole set.
const AT_POINT = /esriGeometryPoint|intersects\(|within_circle|geometry=%7B%22x|geometry=-?\d+\.\d+(%2C|,)-?\d+\.\d+(&|$)/i;
const SHAPE_TYPES = new Set(["Polygon", "MultiPolygon", "LineString", "MultiLineString"]);

let problems = 0;
function problem(msg) { console.log("  FAIL  " + msg); problems++; }

function layerIds(tag) {
  const src = readFileSync(join(ROOT, tag, "index.html"), "utf8");
  const m = src.match(/var LAYER_AREA_RANK = \[([\s\S]*?)\n\s*\];/);
  if (!m) { problem(`${tag}: could not read LAYER_AREA_RANK from its index.html`); return []; }
  return [...m[1].matchAll(/"([^"]+)"/g)].map((x) => x[1]);
}

// One real fetch per distinct request for the whole run: several layers share a
// source, and asking a government server the same question forty times is not
// a measurement of anything.
const cache = new Map();
function realFetch(url, method, body, type) {
  const key = method + " " + url + " " + (body || "");
  if (!cache.has(key)) {
    cache.set(key, (async () => {
      try {
        const res = await fetch(url, { method, body: body || undefined,
          headers: body ? { "content-type": type || "application/x-www-form-urlencoded" } : {},
          signal: AbortSignal.timeout(30000) });
        const buf = Buffer.from(await res.arrayBuffer());
        return { status: res.status, buf, type: res.headers.get("content-type") || "" };
      } catch (e) {
        return { status: 0, buf: null, type: "", err: String(e).slice(0, 80) };
      }
    })());
  }
  return cache.get(key);
}

async function wire(page, tag, rec) {
  const dir = vendorDir(tag);
  await page.route(/^https?:\/\//, async (route) => {
    const req = route.request();
    const u = new URL(req.url());
    if (u.origin + "/" === new URL(BASE).origin + "/") {
      if (/\/data\/app\/.+\.json$/.test(u.pathname)) rec.push({ t: Date.now(), host: "(this site)", url: u.pathname, kind: "local", atPoint: false });
      return route.continue();
    }
    if (/cdnjs\.cloudflare\.com$/.test(u.hostname)) {
      // The sandbox's Chromium cannot reach cdnjs; the SessionStart hook vendors
      // Leaflet and MapLibre per instance. Absent (CI), let it through.
      const f = u.pathname.split("/").pop();
      if (existsSync(join(dir, f)))
        return route.fulfill({ body: readFileSync(join(dir, f)),
          contentType: f.endsWith(".css") ? "text/css" : "application/javascript" });
      return route.continue();
    }
    if (SKIP_HOST.test(u.hostname)) return route.abort();
    const r = await realFetch(req.url(), req.method(), req.postData(), req.headers()["content-type"]);
    const text = r.buf ? r.buf.toString("utf8", 0, Math.min(r.buf.length, 8e6)) : "";
    const shape = SHAPE.test(text);
    rec.push({
      t: Date.now(), host: u.hostname, url: req.url(),
      status: r.status,
      kind: !r.buf || r.status >= 400 ? "unanswered" : shape ? "shape" : POINTS.test(text) ? "points" : "other",
      atPoint: AT_POINT.test(req.url() + " " + (req.postData() || "")),
    });
    if (!r.buf) return route.abort();
    return route.fulfill({ status: r.status, body: r.buf,
      headers: { "content-type": r.type || "application/json", "access-control-allow-origin": "*" } });
  });
}

// Settled once no request has started for 4 s, after at least 6 s; a page that
// never settles is recorded as it stands after 60 s rather than waited on.
async function settle(rec, minMs, maxMs) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    await new Promise((r) => setTimeout(r, 500));
    const last = rec.length ? rec[rec.length - 1].t : start;
    if (Date.now() - start > minMs && Date.now() - last > 4000) return;
  }
}

// The debug namespace is branded per instance (ChiExplorer, …); find it by the
// export this probe needs.
const FIND_EXPORTS = "Object.keys(window).map((k) => window[k]).find((v) => v && typeof v === 'object' && typeof v.layerSources === 'function')";

async function visit(browser, job) {
  const ctx = await browser.newContext({ serviceWorkers: "block", viewport: { width: 1200, height: 800 } });
  const page = await ctx.newPage();
  const rec = [];
  await wire(page, job.tag, rec);
  const out = { ...job, requests: rec, info: null, counties: null, error: null };
  try {
    const layers = job.mode === "layer" ? job.id : "";
    await page.goto(`${BASE}${job.tag}/#point=${job.pt.lat},${job.pt.lng}&layers=${layers}`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(`!!(${FIND_EXPORTS})`, null, { timeout: 45000 });
    await settle(rec, 6000, 60000);
    if (job.mode === "layer") {
      out.info = await page.evaluate(`(${FIND_EXPORTS}).layerSources(${JSON.stringify(job.id)})`);
    }
    if (job.mode === "counties") {
      const info = await page.evaluate(`(${FIND_EXPORTS}).layerSources(${JSON.stringify(job.id)})`);
      out.counties = [];
      for (const key of (info && info.countyKeys) || []) {
        const before = rec.length;
        const res = await page.evaluate(`(async () => {
          try {
            const r = await Promise.race([(${FIND_EXPORTS}).loadCountyEntry(${JSON.stringify(job.id)}, ${JSON.stringify(key)}),
              new Promise((_, rj) => setTimeout(() => rj(new Error("no answer in 90 s")), 90000))]);
            return Object.assign({ ok: true }, r);
          } catch (e) { return { ok: false, error: String(e && e.message || e).slice(0, 120) }; }
        })()`);
        await new Promise((r) => setTimeout(r, 300));
        out.counties.push({ key, ...res, requests: rec.slice(before) });
      }
    }
  } catch (e) { out.error = String(e).slice(0, 200); }
  await ctx.close();
  return out;
}

// ---- measure --------------------------------------------------------------
const jobs = [];
const points = {};
for (const tag of TAGS) {
  const pts = [anchorOf(tag, problem), ...(EXTRA_POINTS[tag] || [])].filter(Boolean)
    .map((p) => ({ lat: p.lat, lng: p.lng }));
  points[tag] = pts;
  pts.forEach((pt) => jobs.push({ tag, id: "", mode: "baseline", pt }));
  for (const id of layerIds(tag)) {
    pts.forEach((pt) => jobs.push({ tag, id, mode: "layer", pt }));
    // Only Illinois dispatches by county today; the page answers with no keys
    // for any layer that does not, so asking costs one boot per layer.
    if (/registerCountyLayer\(/.test(readFileSync(join(ROOT, tag, "index.html"), "utf8")))
      jobs.push({ tag, id, mode: "counties", pt: pts[0] });
  }
}
console.log(`probe-layer-sources: ${jobs.length} page(s) across ${TAGS.join(", ")}`);
const results = [];
let next = 0;
const browser = await chromium.launch();
await Promise.all(Array.from({ length: CONC }, async () => {
  while (next < jobs.length) {
    const job = jobs[next++];
    const r = await visit(browser, job);
    results.push(r);
    if (r.error) problem(`${job.tag} ${job.id || "(no layer)"} @${job.pt.lat}: ${r.error}`);
    process.stdout.write(`\r  ${results.length}/${jobs.length}`);
  }
}));
await browser.close();
console.log("");

// ---- summarise --------------------------------------------------------------
const hostsOf = (reqs, kind) => [...new Set(reqs.filter((x) => x.kind === kind).map((x) => x.host))].sort();
const prior = existsSync(OUT) ? JSON.parse(readFileSync(OUT, "utf8")) : { apps: {} };
const apps = { ...prior.apps };
for (const tag of TAGS) {
  const mine = results.filter((r) => r.tag === tag);
  // SUBTRACTED PER POINT. Outside Chicago the Illinois app fetches the city's
  // community areas for a coverage test, and the community-area layer draws
  // that same dataset: pooled across points, the baseline erased that layer's
  // own fetch at the Loop, where no coverage test asks for it.
  const urlsAt = (mode, id, pt) => new Set(mine.filter((r) => r.mode === mode && r.id === id &&
    r.pt.lat === pt.lat && r.pt.lng === pt.lng).flatMap((r) => r.requests.map((x) => x.url)));
  const appLevel = [...new Set(mine.filter((r) => r.mode === "baseline")
    .flatMap((r) => r.requests).filter((x) => x.kind === "shape").map((x) => x.host))].sort();
  const layers = {};
  for (const id of layerIds(tag)) {
    const runs = mine.filter((r) => r.id === id && r.mode === "layer");
    const info = runs.map((r) => r.info).find(Boolean) || {};
    const reqs = runs.flatMap((r) => {
      const drop = urlsAt("baseline", "", r.pt);
      // A sub-layer switches its parent on as well, so the parent's own
      // requests at the same point are not the sub-layer's.
      if (info.subOf) for (const u of urlsAt("layer", info.subOf, r.pt)) drop.add(u);
      return r.requests.filter((x) => !drop.has(x.url));
    });
    const types = new Set(runs.flatMap((r) => (r.info && r.info.geometryTypes) || []));
    const shapes = reqs.filter((x) => x.kind === "shape");
    const entry = {
      whole_set: [...new Set(shapes.filter((x) => !x.atPoint).map((x) => x.host))].sort(),
      at_point: [...new Set(shapes.filter((x) => x.atPoint).map((x) => x.host))].sort(),
      points_from: hostsOf(reqs, "points"),
      unanswered: hostsOf(reqs, "unanswered"),
      loaded_geometry: [...types].sort(),
    };
    const c = mine.find((r) => r.id === id && r.mode === "counties");
    if (c && c.counties && c.counties.length) {
      const live = [], shipped = [], failed = [];
      for (const k of c.counties) {
        const shapeHosts = hostsOf(k.requests, "shape");
        if (shapeHosts.length) live.push({ key: k.key, hosts: shapeHosts });
        else if (!k.ok) failed.push({ key: k.key, hosts: hostsOf(k.requests, "unanswered"), error: k.error });
        else shipped.push(k.key);
      }
      entry.counties = { live, shipped, failed };
    }
    if (info.subOf) entry.sub_of = info.subOf;
    if (info.sharesParentLoader) entry.shares_parent_loader = true;
    const liveCounties = entry.counties ? entry.counties.live.length : 0;
    entry.source = entry.whole_set.length || entry.at_point.length || liveCounties ? "fetched"
      : [...types].some((t) => SHAPE_TYPES.has(t)) ? "shipped"
      : types.size ? "points"
      : entry.points_from.length ? "points"
      : entry.unanswered.length ? "unanswered"
      : "not-loaded";
    layers[id] = entry;
  }
  // Second pass, once every layer is classified: a sub-layer drawing the very
  // set its parent loaded made no request of its own, so the subtraction left
  // it nothing, and its shapes come from wherever the parent's do.
  for (const entry of Object.values(layers)) {
    const parent = entry.shares_parent_loader && layers[entry.sub_of];
    if (parent && entry.source !== "fetched" && parent.source === "fetched") {
      entry.source = "fetched";
      entry.via_parent = entry.sub_of;
    }
  }
  apps[tag] = { points: points[tag], app_level: appLevel, layers };
}

if (problems) { console.log(`probe-layer-sources: ${problems} problem(s) — refusing to write.`); process.exit(1); }
const doc = { measured: new Date().toISOString().slice(0, 10), apps: Object.fromEntries(Object.keys(apps).sort().map((k) => [k, apps[k]])) };
writeFileSync(OUT, JSON.stringify(doc, null, 1) + "\n");
for (const tag of TAGS) {
  const L = Object.values(apps[tag].layers);
  const n = (s) => L.filter((x) => x.source === s).length;
  console.log(`  ${tag}: ${n("fetched")} fetched, ${n("shipped")} shipped, ${n("points")} points, ` +
    `${n("unanswered")} unanswered, ${n("not-loaded")} not loaded — of ${L.length}`);
}
console.log("probe-layer-sources: wrote layer-sources.json");
