// Which live ArcGIS layers lose their INTERIOR RINGS to the GeoJSON export.
//
// WHY THIS EXISTS. Asked for `f=geojson`, an ArcGIS service can return a
// feature's holes as separate SHELLS — a MultiPolygon whose parts sit inside
// one another. Under GeoJSON semantics each part is its own area, so ground the
// publisher cut out becomes ground the layer claims, and a click inside the
// cutout gets a card naming a district that does not cover it. Asked for
// `f=json`, the same query on the same service returns the same rings with the
// holes wound counter-clockwise, which is Esri's normative signal.
//
// Measured 2026-09-05 across every ArcGIS layer the six shipped apps fetch: 41
// of 156 polygon layers lost 1,376 rings, worth 298.2 km² and 1,135 wrong card
// answers. docs/DATA_LAYER_GUIDEBOOK.md carries the table and the reader-impact
// method; every loader now asks for `f=json` and nests the rings itself
// (engine/index.html/arcgis-loader.txt).
//
// WHY IT BOOTS A BROWSER RATHER THAN READING THE SOURCE. Every layer URL is
// composed inside a factory from an org base, a service name and per-county
// outFields — `il/index.html` alone builds 51 of them — so no regex can
// enumerate them. The app is booted, every layer switched on, points selected
// across the counties its dispatchers cover, and the URLs recorded from the
// requests that actually leave.
//
// WHY IT IS NOT A CI GATE. It needs 178 live county services to answer, and a
// gate that needs a third party up fails on somebody else's schedule. It is an
// operator command, run when a publisher re-publishes or a new county lands:
//
//     python3 -m http.server 8000 &
//     node scripts/probe_arcgis_ring_nesting.mjs            # every instance
//     node scripts/probe_arcgis_ring_nesting.mjs il wi      # named instances
//
// A layer whose rings differ between the two formats is reported LOSES n. A
// point layer carries no ring and is skipped structurally, not sampled.

import { chromium } from "playwright";
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const BASE = (process.env.BASE_URL || "http://localhost:8000").replace(/\/+$/, "") + "/";
const OUT = join(ROOT, "arcgis-ring-nesting.json");
const UA = "districtry/1.0 (+https://districtry.com/)";

// An instance is a top-level directory with its own index.html and data/app —
// the same rule validate_card_links.py and validate_instance_registration.py
// discover by, so a seventh state is swept the day it lands.
function instances() {
  return readdirSync(ROOT).filter((d) => {
    try {
      return statSync(join(ROOT, d)).isDirectory() &&
        existsSync(join(ROOT, d, "index.html")) &&
        existsSync(join(ROOT, d, "data", "app"));
    } catch { return false; }
  }).sort();
}

// Points to select, per instance. Coverage gating is real: a county-dispatched
// layer is never queried outside its own county, so one point leaves most of a
// statewide instance's layers unexercised. Each instance's own coverage anchors
// are the honest source, and anything still unrequested is simply not measured
// rather than reported clean.
function pointsFor(tag) {
  const pts = [];
  const rel = tag === "il" ? "metro-worksheet.json" : join(tag, "metro-worksheet.json");
  try {
    const w = JSON.parse(readFileSync(join(ROOT, rel), "utf8"));
    if (w.anchor_point) pts.push([w.anchor_point.lat, w.anchor_point.lng]);
  } catch { /* a city instance may not carry one */ }
  // The INSIDE anchors from the instance's own outline builder — one per served
  // county, which is exactly what a county-dispatched layer needs to be asked
  // at all. They are read as literals rather than imported because this runs in
  // node; check_anchor_registry() is what keeps the list honest, and a city
  // instance simply has no such file.
  const outline = tag === "il" ? join(ROOT, "scripts", "build_metro_outline.py")
                               : join(ROOT, tag, "scripts", "build_metro_outline.py");
  if (existsSync(outline)) {
    const src = readFileSync(outline, "utf8");
    const block = src.match(/\nINSIDE = \{([\s\S]*?)\n\}/);
    if (block) {
      for (const m of block[1].matchAll(/\(\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*\)/g)) {
        pts.push([parseFloat(m[1]), parseFloat(m[2])]);
      }
    }
  }
  return pts.length ? pts : [[41.8825, -87.6285]];
}

function vendorDir(tag) {
  return tag === "il" ? join(ROOT, "scripts", "vendor", "leaflet")
                      : join(ROOT, tag, "scripts", "vendor", "leaflet");
}

async function recordUrls(browser, tag) {
  const urls = new Set();
  const ctx = await browser.newContext({ serviceWorkers: "block" });
  const page = await ctx.newPage();
  const dir = vendorDir(tag);
  for (const [f, type] of [["leaflet.js", "application/javascript"],
                           ["leaflet.css", "text/css"],
                           ["maplibre-gl.min.js", "application/javascript"],
                           ["maplibre-gl.css", "text/css"]]) {
    const p = join(dir, f);
    if (existsSync(p)) {
      const body = readFileSync(p);
      await page.route(`**/cdnjs.cloudflare.com/**/${f}`,
        (r) => r.fulfill({ status: 200, contentType: type, body }));
    }
  }
  page.on("request", (r) => { if (/\/rest\/services\//.test(r.url())) urls.add(r.url()); });
  await page.goto(BASE + tag + "/", { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => {
    const k = Object.keys(window).find((n) => /Explorer$/.test(n) && window[n] && window[n].state);
    return !!k;
  }, null, { timeout: 60000 });
  await page.evaluate(() => document.querySelectorAll("input[type=checkbox]")
    .forEach((el) => { if (!el.checked) el.click(); }));
  await page.waitForTimeout(3000);
  for (const [lat, lng] of pointsFor(tag)) {
    await page.evaluate(({ lat, lng }) => {
      const k = Object.keys(window).find((n) => /Explorer$/.test(n) && window[n] && window[n].state);
      window[k].setSelectedPoint(lat, lng);
    }, { lat, lng });
    await page.waitForTimeout(1200);
  }
  await page.waitForTimeout(4000);
  await ctx.close();
  return [...urls];
}

// THE NESTING RULE IS LIFTED FROM THE SHIPPED APP, not re-implemented here.
// Counting counter-clockwise rings is NOT the same answer: on Will County's
// fire districts the winding count is 237 and the app's containment-aware
// converter yields 234, because three CCW rings are contained by nothing and
// become their own shells rather than holes. A probe that reports a number the
// app does not produce is a probe that will one day be believed over the app.
function liftConverter(tag) {
  const src = readFileSync(join(ROOT, tag, "index.html"), "utf8");
  const grab = (name) => {
    const m = src.match(new RegExp("\\n  function " + name + "\\([\\s\\S]*?\\n  \\}\\n"));
    if (!m) throw new Error(`${tag}/index.html no longer defines ${name} — the probe cannot measure what the app does`);
    return m[0];
  };
  const body = grab("esriSignedRingArea") + grab("esriRingsToParts") + grab("pointInRing") +
    "\nreturn esriRingsToParts;";
  // eslint-disable-next-line no-new-func
  return new Function(body)();
}

function geojsonHoles(g) {
  if (!g) return 0;
  if (g.type === "Polygon") return Math.max(0, g.coordinates.length - 1);
  if (g.type === "MultiPolygon") return g.coordinates.reduce((n, p) => n + Math.max(0, p.length - 1), 0);
  return 0;
}

async function getJSON(url) {
  const res = await fetch(url, { headers: { "User-Agent": UA } });
  if (!res.ok) throw new Error("HTTP " + res.status);
  const d = await res.json();
  if (d && d.error) throw new Error(JSON.stringify(d.error).slice(0, 140));
  return d;
}

async function pageAll(base, params, format) {
  const rows = [];
  let offset = 0;
  for (;;) {
    const u = new URL(base + "/query");
    for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
    u.searchParams.set("f", format);
    u.searchParams.set("outSR", "4326");
    u.searchParams.set("returnGeometry", "true");
    if (offset) { u.searchParams.set("resultOffset", String(offset)); u.searchParams.set("resultRecordCount", "1000"); }
    const d = await getJSON(u.toString());
    const got = d.features || [];
    rows.push(...got);
    const more = d.exceededTransferLimit || (d.properties && d.properties.exceededTransferLimit);
    if (!more || !got.length || offset > 40000) return rows;
    offset += got.length;
  }
}

const args = process.argv.slice(2).filter((a) => !a.startsWith("-"));
const tags = args.length ? args : instances();
const browser = await chromium.launch();
const report = {};
let lost = 0, affected = 0, measured = 0, skipped = 0;

for (const tag of tags) {
  const urls = await recordUrls(browser, tag);
  const ringsToParts = liftConverter(tag);
  // One entry per LAYER, carrying the app's OWN query verbatim minus the
  // format: several are envelope-scoped, and dropping `geometry` from the USGS
  // structures query turns a state-sized read into a national one.
  const layers = new Map();
  for (const u of urls) {
    const p = new URL(u);
    const base = u.split("/query")[0];
    const isPoint = (p.searchParams.get("geometryType") || "") === "esriGeometryPoint";
    const params = {};
    for (const [k, v] of p.searchParams) {
      if (!["f", "resultOffset", "resultRecordCount"].includes(k)) params[k] = v;
    }
    const cur = layers.get(base);
    if (!cur || (cur.isPoint && !isPoint)) layers.set(base, { isPoint, params });
  }
  console.log(`\n=== ${tag}: ${layers.size} distinct ArcGIS layer(s) ===`);
  for (const [base, cfg] of [...layers].sort()) {
    let meta;
    try { meta = await getJSON(base + "?f=json"); } catch { meta = {}; }
    if (meta.geometryType === "esriGeometryPoint") {
      skipped++;
      continue;                       // no rings: cannot carry an interior one
    }
    let gj, ej;
    try {
      gj = await pageAll(base, cfg.params, "geojson");
      ej = await pageAll(base, cfg.params, "json");
    } catch (e) {
      console.log(`  ????  ${base.slice(-88)}  ${String(e.message).slice(0, 60)}`);
      report[base] = { instance: tag, error: String(e.message).slice(0, 200) };
      continue;
    }
    const hg = gj.reduce((n, f) => n + geojsonHoles(f.geometry), 0);
    const he = ej.reduce((n, f) => {
      if (!f.geometry || !f.geometry.rings) return n;
      return n + ringsToParts(f.geometry.rings).reduce((h, part) => h + part.length - 1, 0);
    }, 0);
    measured++;
    report[base] = { instance: tag, features: gj.length, holes_geojson: hg, holes_json: he };
    if (he > hg) {
      affected++; lost += he - hg;
      console.log(`  LOSES ${String(he - hg).padStart(4)}  ${base.slice(-88)}  (${hg} -> ${he})`);
    }
  }
}
await browser.close();
writeFileSync(OUT, JSON.stringify(report, null, 1));
console.log(`\n${measured} polygon layer(s) measured, ${skipped} point layer(s) skipped;` +
            ` ${affected} lose ${lost} interior ring(s). Wrote ${OUT}`);
if (affected) {
  console.log("A layer listed here is fetched as GeoJSON somewhere. Every loader in this");
  console.log("fleet should be asking for f=json — grep the instance for `f=geojson`.");
}
