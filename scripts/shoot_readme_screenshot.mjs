#!/usr/bin/env node
/**
 * Re-shoot a README screenshot from the live app.
 *
 * The READMEs' screenshots went two weeks past the rebrand still showing the
 * red star and "CHICAGO DISTRICT EXPLORER" — a hand-made artifact nothing
 * regenerates and no gate can check, since a stale PNG is a valid PNG. This
 * does not make it checkable, but it makes refreshing it a command instead of
 * an afternoon of reconstructing how to boot the app headless.
 *
 *   node scripts/shoot_readme_screenshot.mjs il  docs/screenshot.png
 *   node scripts/shoot_readme_screenshot.mjs ca  ca/docs/screenshot.png
 *
 * Serve the repo first (python3 -m http.server 8000). Env: BASE_URL, SHOT_POINT,
 * SHOT_ZOOM, SHOT_LAYERS, SHOT_W/SHOT_H, SHOT_THEME=dark.
 *
 * Two environment shims, both deliberate and neither touching the app:
 *
 * 1. THE RASTER BASEMAP IS FORCED, by making WebGL2 unavailable. The app
 *    prefers CARTO's vector style through MapLibre and keeps a raster fallback;
 *    only the raster path is servable tile-by-tile here, and the two are the
 *    same cartography (Positron / Dark Matter). It also makes the shot
 *    deterministic — whether a headless runner has WebGL2 stops mattering.
 *
 * 2. TILES ARE FETCHED WITH curl. In the Claude Code sandbox Chromium cannot
 *    reach the CDN but curl goes through the agent HTTPS proxy; outside the
 *    sandbox this is simply a slower path to the same bytes. The ?key= is
 *    forwarded verbatim: without it CARTO returns a tile stamped "API KEY
 *    REQUIRED", which is a watermark rather than an error, and would ship a
 *    screenshot that looks like a broken licence.
 *
 * Vendored Leaflet/MapLibre are served same-origin when present, exactly as
 * scripts/smoke_test.mjs does it and for the same reason.
 */
import { chromium } from "playwright";
import { readFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const [tag, out] = process.argv.slice(2);
if (!tag || !out) {
  console.error("usage: shoot_readme_screenshot.mjs <instance-tag> <out.png>");
  process.exit(2);
}

const HERE = dirname(fileURLToPath(import.meta.url));
const VENDOR = join(HERE, "vendor", "leaflet");
const vend = (f) => (existsSync(join(VENDOR, f)) ? readFileSync(join(VENDOR, f)) : null);

// Each instance's debug namespace — the same handle smoke_test.mjs waits on.
const EXPORTS = { il: "ChiExplorer", ca: "SFExplorer", ny: "NYCExplorer",
                  wi: "WIExplorer", ia: "IAExplorer", mi: "MIExplorer" };

const BASE = process.env.BASE_URL || "http://localhost:8000";
const W = +(process.env.SHOT_W || 1400), H = +(process.env.SHOT_H || 1050);
const hash = [
  process.env.SHOT_POINT ? "point=" + process.env.SHOT_POINT : null,
  "zoom=" + (process.env.SHOT_ZOOM || 12),
  process.env.SHOT_LAYERS ? "layers=" + process.env.SHOT_LAYERS : null,
].filter(Boolean).join("&");
const url = `${BASE}/${tag}/#${hash}`;

const browser = await chromium.launch();
// Captured at 2x and downscaled by the caller: supersampling reads better than
// rendering at 1x, and the README image has always been 1400 wide.
const ctx = await browser.newContext({
  viewport: { width: W, height: H },
  deviceScaleFactor: +(process.env.SHOT_DPR || 2),
  colorScheme: process.env.SHOT_THEME === "dark" ? "dark" : "light",
});
const page = await ctx.newPage();

await page.addInitScript(() => {
  const orig = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (type, ...rest) {
    if (type === "webgl2") return null;          // force the raster basemap
    return orig.call(this, type, ...rest);
  };
});

for (const [file, type] of [["leaflet.js", "application/javascript"],
                            ["leaflet.css", "text/css"],
                            ["maplibre-gl.min.js", "application/javascript"],
                            ["maplibre-gl.css", "text/css"]]) {
  const body = vend(file);
  if (body) {
    await page.route(`**/cdnjs.cloudflare.com/**/${file}`,
                     (r) => r.fulfill({ status: 200, contentType: type, body }));
  }
}

let tiles = 0, tileFail = 0;
const cache = new Map();
await page.route("**basemaps.cartocdn.com/**", async (route) => {
  const u = route.request().url();
  if (!cache.has(u)) {
    let body = null;
    try {
      body = execFileSync("curl", ["-sS", "--max-time", "30", u],
                          { maxBuffer: 8 << 20, encoding: "buffer" });
      if (!body || body.length < 100) body = null;
    } catch { body = null; }
    cache.set(u, body);
  }
  const body = cache.get(u);
  if (!body) { tileFail++; return route.abort(); }
  tiles++;
  return route.fulfill({ status: 200, contentType: "image/png", body });
});

await page.goto(url, { waitUntil: "domcontentloaded", timeout: 90000 });
await page.waitForFunction((n) => !!window[n], EXPORTS[tag] || "ChiExplorer", { timeout: 90000 });
await page.waitForTimeout(+(process.env.SHOT_WAIT || 14000));
await page.screenshot({ path: out });
console.log(`wrote ${out} (${W}x${H} @${process.env.SHOT_DPR || 2}x) — ${tiles} tiles, ${tileFail} failed`);
if (tileFail) console.log("  some tiles failed: the basemap will have holes; do not ship this shot");
await browser.close();
