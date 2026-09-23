#!/usr/bin/env node
// Dump every district of a county-dispatched layer, through the APP'S OWN
// per-county loaders, for scripts/build_district_search.py.
//
// WHY A BROWSER. Illinois's county-board layer is ~60 counties, most of them
// fetched live from each county's own GIS server by loader code that exists
// only in il/index.html — ArcGIS paging, Esri ring repair, per-county field
// names, the lot. Re-implementing those fetches in Python would be a second
// copy that drifts from the map the reader sees. Instead this boots the app
// headless and asks it (window.ChiExplorer.layerDistricts) for every county's
// features and the hover identity it would print for each, so the index is
// built from exactly what the map draws.
//
// Usage (serve the repo first, e.g. `python3 -m http.server 8000`):
//   BASE_URL=http://localhost:8000/il/ node scripts/dump_layer_districts.mjs county-board out.json
//
// Every county is settled, failures included, and the output says which
// failed: the builder refuses a partial index rather than shipping one.
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { chromium } from "playwright";

const [layerId, outPath] = process.argv.slice(2);
if (!layerId || !outPath) {
  console.error("usage: BASE_URL=http://localhost:8000/il/ node scripts/dump_layer_districts.mjs <layer-id> <out.json>");
  process.exit(2);
}
const BASE = process.env.BASE_URL || "http://localhost:8000/il/";

// The same same-origin Leaflet fallback the smoke test uses, for a sandbox
// whose browser cannot reach cdnjs (scripts/vendor_leaflet.sh fills it).
const here = path.dirname(fileURLToPath(import.meta.url));
const vendor = path.join(here, "vendor", "leaflet");
const vendored = (name) => {
  const p = path.join(vendor, name);
  return fs.existsSync(p) ? fs.readFileSync(p) : null;
};

const browser = await chromium.launch();
try {
  const context = await browser.newContext({ serviceWorkers: "block" });
  const page = await context.newPage();
  for (const [glob, name, type] of [
    ["**/cdnjs.cloudflare.com/**/leaflet.js", "leaflet.js", "application/javascript"],
    ["**/cdnjs.cloudflare.com/**/leaflet.css", "leaflet.css", "text/css"],
    ["**/cdnjs.cloudflare.com/**/maplibre-gl.min.js", "maplibre-gl.min.js", "application/javascript"],
  ]) {
    const body = vendored(name);
    if (body) await page.route(glob, (r) => r.fulfill({ status: 200, contentType: type, body }));
  }
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => !!(window.ChiExplorer && window.ChiExplorer.layerDistricts), null, { timeout: 60000 });
  const counties = await page.evaluate((id) => window.ChiExplorer.layerDistricts(id), layerId);
  fs.writeFileSync(outPath, JSON.stringify({ layer: layerId, counties }));
  const failed = counties.filter((c) => !c.ok);
  console.log(`dump-layer-districts: ${layerId} — ${counties.length} entr${counties.length === 1 ? "y" : "ies"}, ` +
    `${counties.reduce((n, c) => n + (c.ok ? c.features.length : 0), 0)} feature(s), ${failed.length} failed` +
    (failed.length ? ": " + failed.map((c) => c.key).join(", ") : ""));
} finally {
  await browser.close();
}
