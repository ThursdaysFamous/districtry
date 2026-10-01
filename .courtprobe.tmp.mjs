import { chromium } from "playwright";
import fs from "node:fs";
const BASE = "http://localhost:8000/ky/";
const V = "ky/scripts/vendor/leaflet/";
const b = await chromium.launch();
const p = await b.newPage();
for (const [pat, f, t] of [
  ["**/leaflet.css", "leaflet.css", "text/css"],
  ["**/leaflet.js", "leaflet.js", "application/javascript"],
  ["**/maplibre-gl.css", "maplibre-gl.css", "text/css"],
  ["**/maplibre-gl*.js", "maplibre-gl.min.js", "application/javascript"],
]) await p.route(pat, r => r.fulfill({ body: fs.readFileSync(V + f), contentType: t }));
await p.goto(BASE + "#point=38.25270,-85.75850&layers=ky-supreme-court,ky-court-of-appeals,ky-circuit-court,ky-district-court", { waitUntil: "domcontentloaded" });
await p.waitForFunction(() => window.KentuckyExplorer, null, { timeout: 60000 });
await p.waitForTimeout(9000);
const out = await p.evaluate(() => {
  const r = {};
  for (const id of ["ky-supreme-court","ky-court-of-appeals","ky-circuit-court","ky-district-court"]) {
    const el = document.querySelector('[data-layer="' + id + '"], #card-' + id + ', .layer-block[data-layer-id="' + id + '"]');
    r[id] = el ? el.innerText.replace(/\s+/g," ").slice(0,220) : null;
  }
  r._blocks = Array.from(document.querySelectorAll(".layer-block")).map(e => (e.getAttribute("data-layer")||e.getAttribute("data-layer-id")||"?") + " :: " + e.innerText.replace(/\s+/g," ").slice(0,160));
  return r;
});
console.log(JSON.stringify(out, null, 1));
await b.close();
