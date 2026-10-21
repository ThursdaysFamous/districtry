#!/usr/bin/env node
// Build each app's ZIP code index, data/app/zip-index.json, from the app's
// own ZIP code tile archives, and the fleet's list of which app has which
// ZIP code, fleet-zips.json at the root.
//
// WHY. A ZIP code typed into the search box used to select one point, the
// spot the geocoder gave for it, and every card then named that spot's
// districts. A ZIP code is not a spot: Chicago's 60625 crosses four wards
// (measured 2026-10-21 against Census 2020 blocks: Ward 33 41%, Ward 40 30%,
// Ward 39 16%, Ward 47 13%), so the one ward the cards named was wrong for
// most of the people who live there, and a reader reported exactly that.
// Adam chose that day to have the search show the whole ZIP code and
// compare it (ENGINE geocoder-search, showZip): it selects a spot inside
// the ZIP code, turns its ZIP layer on and pins it for comparison, so every
// ward or county board district it crosses is outlined. This file is what
// the search reads to do that without asking a geocoder: for every ZIP code
// the app's ZIP layer draws, the spot, the ZIP code's extent and its layer.
//
// WHERE IT COMES FROM. The worksheet's `zip_search` key names the file and
// the ZIP layers it is built from, in the order they win: New York names the
// city's MODZCTA layer before the statewide ZIP Code Tabulation Areas, because
// inside the city the MODZCTA layer is the one that answers. Each layer's
// committed archive, data/app/tiles/<layer>.pmtiles, is read through the
// engine's own reader (ENGINE vector-tiles, evaluated here as shipped), every
// tile at the archive's deepest zoom, so the index holds the shapes the map
// draws. A layer field may hold one ZIP code (the Census Bureau's ZCTA5) or
// several separated by commas (a MODZCTA's `zcta`, which lists the ZIP codes
// it joins); 99999, the MODZCTA file's code for ground with no ZIP code, is
// not one. A ZIP code's extent is the extent of every piece of it in those
// tiles, rounded outward to four decimals.
//
// THE SPOT IS ON THE LAYER'S OWN GROUND. Each ZIP layer declares where it
// answers (its coverage test), and a spot outside that would hide the very
// layer the search turns on. So each layer in `zip_search` names the shipped
// outlines its coverage test reads, `inside` (the spot is inside one of
// them) and `outside` (inside none of them: New York's statewide layer
// stands down inside the city), and the spot is the point of the ZIP code
// on that ground farthest from both the ZIP code's edges and the ground's,
// found on a grid over each piece of it and refined around the best. The
// distance matters because the comparison outlines the ZIP code from the
// layer's whole file, which the server simplifies (the apps ask for 0.0005
// degrees, about 55 m), so a spot near an edge could fall in the
// neighbouring ZIP code there: a ZIP code whose best spot is nearer an edge
// than MIN_CLEARANCE_M is left out of the index, and the search finds it
// through the geocoder as before. The spot is rounded to five decimals and
// checked again after rounding.
//
// ONE APP PER ZIP CODE. A ZIP Code Tabulation Area can cross a state line,
// and the tile mirror keeps one in every state it overlaps, so two apps can
// both draw it. Each such ZIP code is listed only by the app holding the
// larger share of it, sampled on a grid, because a reader asking about it
// most likely means the state most of it is in; the other app hands it over
// (fleet-zips.json).
//
// IT IS A FeatureCollection OF POINTS, the shape district-search.json has,
// because validate_index.py holds every geometry file to a feature count and
// the negative point to every polygon; a Point encloses nothing.
//
// fleet-zips.json lists, for each live app (metros.json) with an index, every
// ZIP code its index holds, written as one string of five-digit codes, so an
// app given a ZIP code it does not have can hand it to the app that does, and
// the front door can send one there without asking a geocoder.
//
//   node scripts/build_zip_index.mjs            # write every index and fleet-zips.json
//   node scripts/build_zip_index.mjs --check    # rebuild in memory, fail on drift
//
// --check is offline and needs nothing but Node: it rebuilds every index from
// the committed archives and outlines and fails when a file on disk differs,
// naming the archive or outline whose recorded hash moved when that is why.
// The weekly census tile refresh (update-tiger-tiles.yml) rebuilds the
// indexes in the same run, because a refreshed ZIP archive with the old index
// would fail this check on the bot's own pull request.

import { createHash } from "node:crypto";
import { closeSync, existsSync, openSync, readFileSync, readSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const TILE_LAYER = "d"; // ENGINE tile-overlay TILE_SOURCE_LAYER
const NOT_A_ZIP = "99999";
// metres a ZIP code's spot must be from every edge (see THE SPOT above)
const MIN_CLEARANCE_M = 75;
// beyond this, a ground edge does not move the spot
const GROUND_CAP_M = 500;
// the spot search: a COARSE x COARSE grid over each piece, then a FINE x FINE
// grid around each of the REFINE best cells
const COARSE = 10, FINE = 6, REFINE = 3;
// the share a ZIP code has on a ground, sampled SHARE_GRID x SHARE_GRID per tile
const SHARE_GRID = 32;

const engine = readFileSync(join(ROOT, "engine/index.html/vector-tiles.txt"), "utf8");
const api = new Function(engine + "\nreturn { openTileArchive, decodeTileLayer, tileXYFor, tileToLngLat };")();

const CHECK = process.argv.slice(2).includes("--check");

let failed = false;
function problem(msg) {
  console.error("build-zip-index: FAIL — " + msg);
  failed = true;
}

function worksheetPath(tag) {
  return tag === "il" ? "metro-worksheet.json" : tag + "/metro-worksheet.json";
}

// An instance is a top-level directory with its own index.html and data/app,
// the rule validate_instance_registration.py discovers by.
function instances() {
  return readdirSync(ROOT).filter((d) => /^[a-z]{2}$/.test(d) &&
    existsSync(join(ROOT, d, "index.html")) && existsSync(join(ROOT, d, "data/app"))).sort();
}

function openArchive(path) {
  const fd = openSync(path, "r");
  const archive = api.openTileArchive(path, (offset, length) => {
    const buf = Buffer.alloc(length);
    const n = readSync(fd, buf, 0, length, offset);
    return Promise.resolve(buf.buffer.slice(buf.byteOffset, buf.byteOffset + n));
  });
  return { archive, close: () => closeSync(fd) };
}

function zipsOf(value) {
  if (value == null) return [];
  return String(value).split(",").map((s) => s.trim()).filter((s) => /^\d{5}$/.test(s) && s !== NOT_A_ZIP);
}

// even-odd, the app's own rule within one polygon (ENGINE point-in-polygon)
function inside(x, y, rings) {
  let c = false;
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) c = !c;
    }
  }
  return c;
}

// squared distance from (px, py) to the segment a-b, in the units given
function segDist2(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay;
  let t = dx || dy ? ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy) : 0;
  t = t < 0 ? 0 : t > 1 ? 1 : t;
  const ex = ax + t * dx - px, ey = ay + t * dy - py;
  return ex * ex + ey * ey;
}

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

const down = (v) => Math.floor(v * 1e4) / 1e4;
const up = (v) => Math.ceil(v * 1e4) / 1e4;

/* ---------- the ground a layer answers on ----------
 * The polygons of the outlines a layer's coverage test reads, each tested the
 * app's way (even-odd within a polygon, any polygon of a file), and their
 * edges, bucketed in cells of CELL degrees: a cell no edge crosses is wholly
 * on the ground or wholly off it, which one test at its middle settles, so
 * only a point in a cell an edge crosses is tested against the polygons. */
const CELL = 0.02;
const cellOf = (v) => Math.floor(v / CELL);
function loadGround(tag, files) {
  const polys = [], cells = new Map();
  for (const file of files || []) {
    const path = join(ROOT, tag, "data/app", file);
    if (!existsSync(path)) { problem(`${tag}: zip_search names ${file} as ground, and ${tag}/data/app/${file} does not exist`); continue; }
    const g = JSON.parse(readFileSync(path, "utf8"));
    const feats = g.type === "FeatureCollection" ? g.features : g.type === "Feature" ? [g] : [{ geometry: g }];
    for (const f of feats) {
      const geom = f && f.geometry;
      if (!geom) continue;
      const parts = geom.type === "Polygon" ? [geom.coordinates] : geom.type === "MultiPolygon" ? geom.coordinates : [];
      for (const rings of parts) {
        let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
        for (const ring of rings) {
          for (let i = 0; i < ring.length; i++) {
            const p = ring[i];
            if (p[0] < w) w = p[0];
            if (p[0] > e) e = p[0];
            if (p[1] < s) s = p[1];
            if (p[1] > n) n = p[1];
            if (i + 1 >= ring.length) continue;
            const q = ring[i + 1], seg = [p[0], p[1], q[0], q[1]];
            for (let cx = cellOf(Math.min(p[0], q[0])); cx <= cellOf(Math.max(p[0], q[0])); cx++) {
              for (let cy = cellOf(Math.min(p[1], q[1])); cy <= cellOf(Math.max(p[1], q[1])); cy++) {
                const k = cx + "," + cy;
                if (!cells.has(k)) cells.set(k, []);
                cells.get(k).push(seg);
              }
            }
          }
        }
        polys.push({ rings, w, s, e, n });
      }
    }
  }
  return { polys, cells, whole: new Map() };
}
function onPolys(ground, lng, lat) {
  for (const p of ground.polys) {
    if (lng < p.w || lng > p.e || lat < p.s || lat > p.n) continue;
    if (inside(lng, lat, p.rings)) return true;
  }
  return false;
}
function onGround(ground, lng, lat) {
  const cx = cellOf(lng), cy = cellOf(lat), k = cx + "," + cy;
  if (ground.cells.has(k)) return onPolys(ground, lng, lat);
  if (!ground.whole.has(k)) ground.whole.set(k, onPolys(ground, (cx + 0.5) * CELL, (cy + 0.5) * CELL));
  return ground.whole.get(k);
}
// whether every cell over an extent is wholly on the ground (1), wholly off
// it (0), or neither (null)
function groundOver(ground, w, s, e, n) {
  let all = null;
  for (let cx = cellOf(w); cx <= cellOf(e); cx++) {
    for (let cy = cellOf(s); cy <= cellOf(n); cy++) {
      const k = cx + "," + cy;
      if (ground.cells.has(k)) return null;
      const on = onGround(ground, (cx + 0.5) * CELL, (cy + 0.5) * CELL) ? 1 : 0;
      if (all === null) all = on;
      else if (all !== on) return null;
    }
  }
  return all;
}
// metres to the nearest edge of the ground, or Infinity beyond GROUND_CAP_M
function groundEdgeM(ground, lng, lat) {
  const kx = Math.cos(lat * Math.PI / 180) * 111320, ky = 110574;
  const rx = GROUND_CAP_M / kx, ry = GROUND_CAP_M / ky;
  let best = Infinity;
  for (let cx = cellOf(lng - rx); cx <= cellOf(lng + rx); cx++) {
    for (let cy = cellOf(lat - ry); cy <= cellOf(lat + ry); cy++) {
      const segs = ground.cells.get(cx + "," + cy);
      if (!segs) continue;
      for (const g of segs) {
        const d = segDist2(lng * kx, lat * ky, g[0] * kx, g[1] * ky, g[2] * kx, g[3] * ky);
        if (d < best) best = d;
      }
    }
  }
  best = Math.sqrt(best);
  return best <= GROUND_CAP_M ? best : Infinity;
}

async function readLayer(path, field) {
  const { archive, close } = openArchive(path);
  const h = await archive.header;
  const z = h.maxZoom;
  const lo = api.tileXYFor(h.bounds[0], h.bounds[3], z), hi = api.tileXYFor(h.bounds[2], h.bounds[1], z);
  const byZip = new Map(); // zip -> { w, s, e, n, ids:Set, pieces:[{tile, extent, rings, box}] }
  let tiles = 0;
  for (let x = lo.x; x <= hi.x; x++) {
    for (let y = lo.y; y <= hi.y; y++) {
      const bytes = await archive.getTile(z, x, y);
      if (!bytes) continue;
      tiles++;
      const d = api.decodeTileLayer(bytes, TILE_LAYER);
      for (const f of d.features) {
        const zips = zipsOf(f.properties[field]);
        if (!zips.length) continue;
        let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const ring of f.rings) {
          for (const p of ring) {
            const ll = api.tileToLngLat(z, x, y, p[0], p[1], d.extent);
            if (ll[0] < w) w = ll[0];
            if (ll[0] > e) e = ll[0];
            if (ll[1] < s) s = ll[1];
            if (ll[1] > n) n = ll[1];
            if (p[0] < minX) minX = p[0];
            if (p[0] > maxX) maxX = p[0];
            if (p[1] < minY) minY = p[1];
            if (p[1] > maxY) maxY = p[1];
          }
        }
        const piece = { tile: [x, y], extent: d.extent, rings: f.rings, box: [minX, minY, maxX, maxY] };
        for (const zip of zips) {
          let at = byZip.get(zip);
          if (!at) { at = { w, s, e, n, ids: new Set(), pieces: [] }; byZip.set(zip, at); }
          at.w = Math.min(at.w, w); at.s = Math.min(at.s, s); at.e = Math.max(at.e, e); at.n = Math.max(at.n, n);
          if (f.id != null) at.ids.add(f.id);
          at.pieces.push(piece);
        }
      }
    }
  }
  close();
  return { byZip, tiles, zoom: z };
}

// on the layer's ground: inside one of its `inside` outlines and none of its
// `outside` ones
function onLayerGround(g, lng, lat) {
  return onGround(g.inside, lng, lat) && !(g.outside && onGround(g.outside, lng, lat));
}

/* The spot inside a ZIP code on the layer's ground farthest from every edge,
 * with its distance from the nearest edge in metres; or null where no cell of
 * the grid lands on the ground. Clip edges at a tile's border count as edges,
 * which only makes the spot more cautious. */
function spotOf(at, zoom, g) {
  let best = null;
  // the biggest pieces first, so a narrow one that cannot beat the best spot
  // so far is skipped
  const width = (pc) => Math.min(pc.box[2] - pc.box[0], pc.box[3] - pc.box[1]);
  const pieces = at.pieces.slice().sort((a, b) => width(b) - width(a));
  for (const pc of pieces) {
    const [x0, y0, x1, y1] = pc.box;
    const mid = api.tileToLngLat(zoom, pc.tile[0], pc.tile[1], (x0 + x1) / 2, (y0 + y1) / 2, pc.extent);
    // metres per tile unit at this piece (Web Mercator is uniform within a tile)
    const mpu = 40075016.686 * Math.cos(mid[1] * Math.PI / 180) / Math.pow(2, zoom) / pc.extent;
    if (best && width(pc) / 2 * mpu <= best.clear) continue;
    const segs = [];
    for (const ring of pc.rings) for (let i = 0; i + 1 < ring.length; i++) segs.push(ring[i][0], ring[i][1], ring[i + 1][0], ring[i + 1][1]);
    const score = (x, y) => {
      if (!inside(x, y, pc.rings)) return -1;
      const ll = api.tileToLngLat(zoom, pc.tile[0], pc.tile[1], x, y, pc.extent);
      if (!onLayerGround(g, ll[0], ll[1])) return -1;
      let d = Infinity;
      for (let k = 0; k < segs.length; k += 4) {
        const v = segDist2(x, y, segs[k], segs[k + 1], segs[k + 2], segs[k + 3]);
        if (v < d) d = v;
      }
      d = Math.min(Math.sqrt(d) * mpu, groundEdgeM(g.inside, ll[0], ll[1]));
      if (g.outside) d = Math.min(d, groundEdgeM(g.outside, ll[0], ll[1]));
      return d;
    };
    const cw = (x1 - x0) / COARSE, ch = (y1 - y0) / COARSE;
    const cands = [];
    for (let i = 0; i < COARSE; i++) {
      for (let j = 0; j < COARSE; j++) {
        const x = x0 + (i + 0.5) * cw, y = y0 + (j + 0.5) * ch;
        const d = score(x, y);
        if (d >= 0) cands.push({ x, y, d });
      }
    }
    cands.sort((a, b) => b.d - a.d);
    for (const c of cands.slice(0, REFINE)) {
      let top = c;
      for (let i = 0; i < FINE; i++) {
        for (let j = 0; j < FINE; j++) {
          const x = c.x - cw + (i + 0.5) * (2 * cw / FINE), y = c.y - ch + (j + 0.5) * (2 * ch / FINE);
          const d = score(x, y);
          if (d > top.d) top = { x, y, d };
        }
      }
      if (!best || top.d > best.clear) best = { clear: top.d, x: top.x, y: top.y, pc };
    }
  }
  if (!best) return null;
  const pc = best.pc;
  const ll = api.tileToLngLat(zoom, pc.tile[0], pc.tile[1], best.x, best.y, pc.extent);
  const lngLatRings = pc.rings.map((ring) => ring.map((p) => api.tileToLngLat(zoom, pc.tile[0], pc.tile[1], p[0], p[1], pc.extent)));
  for (const digits of [5, 6]) {
    const k = Math.pow(10, digits);
    const pt = [Math.round(ll[0] * k) / k, Math.round(ll[1] * k) / k];
    if (inside(pt[0], pt[1], lngLatRings) && onLayerGround(g, pt[0], pt[1])) return { pt, clear: best.clear };
  }
  return null;
}

/* The share of a ZIP code on a layer's ground, from a SHARE_GRID x SHARE_GRID
 * grid over each tile it is in, each point counted in the tile it falls in
 * (pieces overlap in the tiles' buffers). 1 without sampling when every cell
 * over the ZIP code is wholly on the ground. */
function shareOf(at, zoom, g) {
  const inAll = groundOver(g.inside, at.w, at.s, at.e, at.n);
  const outAll = g.outside ? groundOver(g.outside, at.w, at.s, at.e, at.n) : 0;
  if (inAll === 1 && outAll === 0) return 1;
  if (inAll === 0 || outAll === 1) return 0;
  let on = 0, all = 0;
  for (const pc of at.pieces) {
    const step = pc.extent / SHARE_GRID;
    for (let x = step / 2; x < pc.extent; x += step) {
      if (x < pc.box[0] || x > pc.box[2]) continue;
      for (let y = step / 2; y < pc.extent; y += step) {
        if (y < pc.box[1] || y > pc.box[3] || !inside(x, y, pc.rings)) continue;
        const ll = api.tileToLngLat(zoom, pc.tile[0], pc.tile[1], x, y, pc.extent);
        all++;
        if (onLayerGround(g, ll[0], ll[1])) on++;
      }
    }
  }
  return all ? on / all : 0;
}

async function buildIndex(tag, w) {
  const spec = w.zip_search;
  const app = join(ROOT, tag, "data/app");
  const sources = {};
  const won = new Map(); // zip -> { feature, share }
  for (const layer of spec.layers) {
    const path = join(app, "tiles", layer.id + ".pmtiles");
    if (!existsSync(path)) { problem(`${tag}: zip_search names ${layer.id}, and ${tag}/data/app/tiles/${layer.id}.pmtiles does not exist`); continue; }
    if (!(w.layers || []).some((l) => l.id === layer.id)) problem(`${tag}: zip_search names ${layer.id}, which the worksheet does not register`);
    if (!(layer.inside || []).length) { problem(`${tag}: zip_search's ${layer.id} names no ground (inside), so its spots could hide the layer`); continue; }
    sources[layer.id] = sha256(path);
    for (const f of layer.inside.concat(layer.outside || [])) {
      if (existsSync(join(app, f))) sources[f] = sha256(join(app, f));
    }
    const g = { inside: loadGround(tag, layer.inside), outside: (layer.outside || []).length ? loadGround(tag, layer.outside) : null };
    const { byZip, tiles, zoom } = await readLayer(path, layer.field);
    let kept = 0, offGround = 0;
    const tooNear = [];
    for (const zip of [...byZip.keys()].sort()) {
      const at = byZip.get(zip);
      if (won.has(zip)) continue; // an earlier layer answers for it
      if (at.ids.size !== 1) { problem(`${tag}: ZIP code ${zip} is ${at.ids.size} shapes in ${layer.id}'s tiles, where it should be one`); continue; }
      const spot = spotOf(at, zoom, g);
      if (!spot) { offGround++; continue; }
      if (spot.clear < MIN_CLEARANCE_M) { tooNear.push(zip + " (" + Math.round(spot.clear) + " m)"); continue; }
      won.set(zip, {
        share: () => shareOf(at, zoom, g),
        feature: {
          type: "Feature",
          bbox: [down(at.w), down(at.s), up(at.e), up(at.n)],
          geometry: { type: "Point", coordinates: spot.pt },
          properties: { zip, layer: layer.id }
        }
      });
      kept++;
    }
    console.log(`  ${tag} ${layer.id}: ${byZip.size} ZIP code(s) in ${tiles} tile(s) at zoom ${zoom}, ${kept} kept` +
      (offGround ? `, ${offGround} with no part on the layer's ground` : ""));
    if (tooNear.length) {
      console.log(`  ${tag} ${layer.id}: ${tooNear.length} left out with no spot ${MIN_CLEARANCE_M} m from every edge: ` + tooNear.join(", "));
    }
  }
  return { won, sources };
}

function indexText(won, sources) {
  const features = [...won.keys()].sort().map((zip) => won.get(zip).feature);
  const head = {
    type: "FeatureCollection",
    _about: "GENERATED by scripts/build_zip_index.mjs from this app's ZIP code tile archives and the outlines its ZIP " +
      "layers answer inside (the worksheet's zip_search key): one Point per ZIP code at the spot inside it, on its " +
      "layer's ground, farthest from every edge, with its extent and its layer, so a ZIP code typed into the search " +
      "box shows the whole ZIP code and compares it (ENGINE geocoder-search, showZip). Never hand-edit; --check in " +
      "CI fails on drift.",
    sources
  };
  const lines = features.map((f) => JSON.stringify(f));
  return { text: JSON.stringify(head).replace(/\}$/, ',"features":[\n') + lines.join(",\n") + "\n]}\n", count: features.length };
}

// the live apps, in metros.json order; a dark app is not in it and is handed
// nothing
const metros = JSON.parse(readFileSync(join(ROOT, "metros.json"), "utf8")).metros;
const metroOf = {};
for (const m of metros) {
  const tag = (/\/([a-z]{2})\/?$/.exec(m.url || "") || [])[1];
  if (tag) metroOf[tag] = m;
}

const built = []; // { tag, file, won, sources }
for (const tag of instances()) {
  const ws = join(ROOT, worksheetPath(tag));
  if (!existsSync(ws)) continue;
  const w = JSON.parse(readFileSync(ws, "utf8"));
  if (!w.zip_search) continue;
  const file = w.zip_search.file;
  if (!((w.data_files || {}).geometry || []).some((g) => g.file === file)) {
    problem(`${tag}: zip_search.file ${file} is not listed under data_files.geometry, so no service worker list and no feature count holds it`);
  }
  const { won, sources } = await buildIndex(tag, w);
  built.push({ tag, file, won, sources });
}

// ONE APP PER ZIP CODE: the larger share keeps it, the earlier app in
// metros.json on a tie
const order = (tag) => { const i = metros.indexOf(metroOf[tag]); return i < 0 ? 1e9 : i; };
const holders = new Map();
for (const b of built) for (const [zip, v] of b.won) {
  if (!holders.has(zip)) holders.set(zip, []);
  holders.get(zip).push({ b, v });
}
for (const [zip, hs] of holders) {
  if (hs.length < 2) continue;
  hs.forEach((h) => { h.share = h.v.share(); });
  hs.sort((a, c) => c.share - a.share || order(a.b.tag) - order(c.b.tag));
  for (const h of hs.slice(1)) h.b.won.delete(zip);
  console.log(`  ZIP code ${zip} is drawn by ${hs.map((h) => h.b.tag + " (" + Math.round(h.share * 100) + "% on its ground)").join(" and ")}: ${hs[0].b.tag} lists it`);
}

const outputs = [];
for (const b of built) {
  const { text, count } = indexText(b.won, b.sources);
  outputs.push({ rel: b.tag + "/data/app/" + b.file, text, count, indexed: true });
}
// fleet-zips.json: the live apps' ZIP codes, so a ZIP code is handed to the
// app that lists it
const fleet = {};
for (const m of metros) {
  const b = built.find((x) => metroOf[x.tag] === m);
  if (b) fleet[m.id] = [...b.won.keys()].sort().join("");
}
outputs.push({
  rel: "fleet-zips.json",
  text: JSON.stringify({
    $comment: "GENERATED by scripts/build_zip_index.mjs: for each live app (its metros.json id) every ZIP code its own " +
      "zip-index.json lists, as one string of five-digit codes, so an app given a ZIP code another app lists hands it " +
      "there and the front door sends a typed ZIP code to its app without a geocoder. A ZIP code is listed by one app " +
      "only. Never hand-edit; --check in CI fails on drift.",
    zips: fleet
  }, null, 1) + "\n"
});

for (const o of outputs) {
  const out = join(ROOT, o.rel);
  if (CHECK) {
    const have = existsSync(out) ? readFileSync(out, "utf8") : null;
    if (have === o.text) continue;
    let why = have == null ? "it does not exist" : "it differs from a rebuild";
    if (have != null && o.indexed) {
      try {
        const recorded = JSON.parse(have).sources || {};
        const fresh = JSON.parse(o.text).sources;
        const moved = Object.keys(fresh).filter((k) => recorded[k] !== fresh[k]);
        if (moved.length) why = "an archive or outline it is built from changed since: " + moved.join(", ");
      } catch (e) { why = "it does not parse as JSON"; }
    }
    problem(`${o.rel}: ${why}. Run node scripts/build_zip_index.mjs`);
  } else {
    writeFileSync(out, o.text);
    console.log(`  wrote ${o.rel}` + (o.count != null ? `: ${o.count} ZIP code(s)` : ""));
  }
}
if (failed) process.exit(1);
console.log(CHECK ? `build-zip-index --check: OK — ${built.length} app index(es) and fleet-zips.json match their sources`
                  : `build-zip-index: wrote ${built.length} index(es) and fleet-zips.json`);
