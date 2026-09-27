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

import { chromium } from "playwright";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { ROOT, instances, vendorDir } from "./probe_points.mjs";

const BASE = (process.env.BASE_URL || "http://localhost:8000").replace(/\/+$/, "") + "/";
const PAIRS = +(process.env.POINTS || 20);
const TAGS = process.env.TAGS ? process.env.TAGS.split(",") : instances();
const ONLY = process.env.LAYERS ? new Set(process.env.LAYERS.split(",")) : null;
const SOURCES = JSON.parse(readFileSync(join(ROOT, "layer-sources.json"), "utf8"));

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

let problems = 0, compared = 0, answered = 0, layersDone = 0;
const browser = await chromium.launch();
try {
  for (const tag of TAGS) {
    const layers = tiledLayers(tag);
    if (!layers.length) continue;
    for (const id of layers) {
      const rec = SOURCES.apps[tag] && SOURCES.apps[tag].layers[id];
      const countyFiles = rec && rec.counties && rec.counties.files;
      const files = countyFiles ? Object.values(countyFiles).flat() : ((rec && rec.files) || []);
      const feats = files.flatMap((f) => {
        const p = join(ROOT, f.replace(/^\/+/, ""));
        return existsSync(p) ? (JSON.parse(readFileSync(p, "utf8")).features || []) : [];
      });
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
      let res, stamps = null;
      try {
        await page.goto(`${BASE}${tag}/`, { waitUntil: "domcontentloaded" });
        await page.waitForFunction(`!!(${FIND})`, null, { timeout: 60000 });
        res = await page.evaluate(`(${FIND}).tileCardCheck(${JSON.stringify(id)}, ${JSON.stringify(pts)})`);
        if (countyFiles) stamps = await page.evaluate(`(${FIND}).countyStampCheck(${JSON.stringify(id)}, ${JSON.stringify(countyFiles)})`);
      } catch (e) {
        console.log(`  FAIL  ${tag}:${id} — ${String(e).slice(0, 200)}`);
        problems++;
        await ctx.close();
        continue;
      }
      await ctx.close();
      const county = res.some((r) => "inArchive" in r);
      // the tile path must be what answered: a query reaching its boundaries
      // another way compares equal while downloading the whole file. For a
      // county layer, only where the answering county's entry reads its
      // boundaries through queryFeatureAt at all; the rest are counted below
      const notTiled = county ? [] : res.filter((r) => !r.viaTiles);
      const hoverBad = res.filter((r) => r.hoverTiles != null && r.hoverTiles !== r.hoverFile);
      // a county layer's live counties answer from their own servers, so an
      // error in BOTH runs is that server, not the tiles: the file run reads an
      // archived county from same-origin files and touches the network only
      // for a live one. The two messages need not match — one run can time out
      // ("signal is aborted") where the other fails to connect ("Failed to
      // fetch"), which failed CI on 2026-09-27 at a southern live county. One
      // run erroring alone is still a difference, and stays in `bad`
      const sameErr = (r) => county && /^error:/.test(r.tiles || "") && /^error:/.test(r.file || "");
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
        `${bad.length} differ, ${errs.length} errored` +
        (county ? `, ${hoverBad.length} hover names differ` : `, ${notTiled.length} not answered from tiles`));
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
}
if (!layersDone && !problems) { console.log("probe-tile-cards: OK — no layer is drawn from tiles"); process.exit(0); }
if (problems) { console.log(`probe-tile-cards: FAIL — ${problems} layer(s) failed: a card that differs, an error, or a page that did not boot (each is named above)`); process.exit(1); }
console.log(`probe-tile-cards: OK — ${layersDone} layer(s), ${compared} points (${answered} inside a district): every card from tiles matches the card from the whole file`);
