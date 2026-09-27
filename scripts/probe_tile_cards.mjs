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
// does at every point 2 m or more from an edge, so 3 m is the nearest honest
// distance. Seeded, so a run is repeatable.
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

import { chromium } from "playwright";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { ROOT, instances, vendorDir } from "./probe_points.mjs";

const BASE = (process.env.BASE_URL || "http://localhost:8000").replace(/\/+$/, "") + "/";
const PAIRS = +(process.env.POINTS || 20);
const TAGS = process.env.TAGS ? process.env.TAGS.split(",") : instances();
const ONLY = process.env.LAYERS ? new Set(process.env.LAYERS.split(",")) : null;
const SOURCES = JSON.parse(readFileSync(join(ROOT, "layer-sources.json"), "utf8"));

let seed = 13;
function rnd() { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }

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
  return out;
}

function tiledLayers(tag) {
  const html = readFileSync(join(ROOT, tag, "index.html"), "utf8");
  const ids = new Set();
  // an archive is named for the layer that registers it
  for (const m of html.matchAll(/\btiles:\s*"data\/app\/tiles\/([^"/]+)\.pmtiles"/g)) ids.add(m[1]);
  return [...ids].filter((id) => !ONLY || ONLY.has(id)).sort();
}

const FIND = "Object.keys(window).map((k) => window[k]).find((v) => v && typeof v === 'object' && typeof v.tileCardCheck === 'function')";

let problems = 0, compared = 0, answered = 0, layersDone = 0;
const browser = await chromium.launch();
try {
  for (const tag of TAGS) {
    const layers = tiledLayers(tag);
    if (!layers.length) continue;
    for (const id of layers) {
      const rec = SOURCES.apps[tag] && SOURCES.apps[tag].layers[id];
      const files = (rec && rec.files) || [];
      const feats = files.flatMap((f) => {
        const p = join(ROOT, f.replace(/^\/+/, ""));
        return existsSync(p) ? (JSON.parse(readFileSync(p, "utf8")).features || []) : [];
      });
      if (!feats.length) { console.log(`  FAIL  ${tag}:${id} — layer-sources.json names no file to place points in`); problems++; continue; }
      const pts = pointsFor(feats);
      const ctx = await browser.newContext({ serviceWorkers: "block" });
      const page = await ctx.newPage();
      const dir = vendorDir(tag);
      await page.route(/cdnjs\.cloudflare\.com/, (route) => {
        const f = new URL(route.request().url()).pathname.split("/").pop();
        if (existsSync(join(dir, f)))
          return route.fulfill({ body: readFileSync(join(dir, f)),
            contentType: f.endsWith(".css") ? "text/css" : "application/javascript" });
        return route.continue();
      });
      let res;
      try {
        await page.goto(`${BASE}${tag}/`, { waitUntil: "domcontentloaded" });
        await page.waitForFunction(`!!(${FIND})`, null, { timeout: 60000 });
        res = await page.evaluate(`(${FIND}).tileCardCheck(${JSON.stringify(id)}, ${JSON.stringify(pts)})`);
      } catch (e) {
        console.log(`  FAIL  ${tag}:${id} — ${String(e).slice(0, 200)}`);
        problems++;
        await ctx.close();
        continue;
      }
      await ctx.close();
      const bad = res.filter((r) => r.tiles !== r.file);
      // the tile path must be what answered: a query reaching its boundaries
      // another way compares equal while downloading the whole file
      const notTiled = res.filter((r) => !r.viaTiles);
      const errs = res.filter((r) => /^error:/.test(r.tiles || "") || /^error:/.test(r.file || ""));
      compared += res.length;
      answered += res.filter((r) => r.file && !/^error:/.test(r.file)).length;
      layersDone++;
      const ok = !bad.length && !errs.length && !notTiled.length;
      console.log(`  ${ok ? "ok  " : "FAIL"}  ${tag}:${id} — ${res.length} points, ${res.filter((r) => r.file).length} with a district, ` +
        `${bad.length} differ, ${errs.length} errored, ${notTiled.length} not answered from tiles`);
      for (const r of [...bad, ...errs].slice(0, 3)) {
        console.log(`          ${r.point.lat.toFixed(6)},${r.point.lng.toFixed(6)}: tiles ${String(r.tiles).slice(0, 160)} | file ${String(r.file).slice(0, 160)}`);
      }
      if (!ok) problems++;
    }
  }
} finally {
  await browser.close();
}
if (!layersDone && !problems) { console.log("probe-tile-cards: OK — no layer is drawn from tiles"); process.exit(0); }
if (problems) { console.log(`probe-tile-cards: FAIL — ${problems} layer(s) failed: a card that differs, an error, or a page that did not boot (each is named above)`); process.exit(1); }
console.log(`probe-tile-cards: OK — ${layersDone} layer(s), ${compared} points (${answered} inside a district): every card from tiles matches the card from the whole file`);
