// A stand-in for CARTO's basemap in every browser test, so the tests stop
// spending the site's CARTO quota (2026-10-20).
//
// Every app draws its map from CARTO's basemap service under one key for the
// whole site, and CARTO meters that key: 5,000,000 requests a calendar month,
// after which it may answer every request with HTTP 429 until the 1st, which is
// a blank map for every reader of every app. On 2026-10-20 CARTO wrote that the
// key had used 4,020,049 requests in twenty days. Readers were a small part of
// that. Measured the same day, with every CARTO request answered locally and
// counted, one run of the fifteen smoke tests, the page-consistency gate and
// the point-transmission probe asked CARTO for 12,948 resources, 5,939 of them
// distinct within their browser context (about what reaches CARTO once the
// browser's cache has answered the repeats); scripts/smoke_test.mjs alone asked
// for 2,074. That battery runs on every push to a pull request and to main, and
// the Illinois smoke test runs again in every deploy.
//
// So every context a test opens answers CARTO from here: a style that boots
// both of the app's GL maps (the ground, and the label map above the
// districts), vector tiles with nothing in them, and a blank image for the
// raster fallback and the coverage map. No gate reads what the basemap draws
// except the one below; the style split, the street-name restyle and the
// boundary-street matcher are held to fixtures through the app's own exported
// functions. The checks that fail the basemap on purpose (the tile-failure
// banner) route it on the PAGE, and a page's routes are asked before its
// context's, so they keep their 503.
//
// ONE CHECK STILL USES THE REAL MAP: Illinois's boundary streets on real tiles,
// which counts the labels the label map actually places along a district's
// edge, so a stand-in cannot answer it. It opens its own context through
// realBasemapContext(), which routes nothing, so the browser's HTTP cache
// answers its repeats as it does for a reader. Playwright turns that cache off
// in any context that routes a request, which is also why the stand-in is not
// simply switched off for one page.
//
// REAL_BASEMAP=1 turns the stand-in off, for a local run against the real map.

const CARTO_HOST = /(^|\.)basemaps\.cartocdn\.com$/;
const PLAIN_NEW_CONTEXT = Symbol("newContext without the basemap stand-in");

// Every URL in the stand-in styles is on a CARTO host, so a request one of them
// leads to is answered here too and never reaches CARTO.
const VECTOR_TILES = "https://tiles.basemaps.cartocdn.com/vectortiles/carto.streets/v1/{z}/{x}/{y}.mvt";
const GLYPHS = "https://tiles.basemaps.cartocdn.com/fonts/{fontstack}/{range}.pbf";

// The smallest style the app treats as a real one. It needs at least one layer
// (the tile-failure notice ignores a style with none, which is how it tells the
// placeholder the GL map starts with from the style it asked for), a symbol
// layer so the label map is built, and a road-name layer named the way CARTO
// names them, because the label map inserts its boundary-street layers after
// the last one. `glyphs` is declared because a style with a text layer is
// invalid without it; no glyph is fetched while the tiles are empty.
function standInStyle(dark) {
  return JSON.stringify({
    version: 8,
    name: dark ? "Stand-in for Dark Matter" : "Stand-in for Positron",
    glyphs: GLYPHS,
    sources: { carto: { type: "vector", tiles: [VECTOR_TILES], minzoom: 0, maxzoom: 14 } },
    layers: [
      { id: "background", type: "background", paint: { "background-color": dark ? "#0e0e0e" : "#fafaf8" } },
      { id: "water", type: "fill", source: "carto", "source-layer": "water",
        paint: { "fill-color": dark ? "#2c353c" : "#d4dadc" } },
      { id: "roadname_major", type: "symbol", source: "carto", "source-layer": "transportation_name", minzoom: 13,
        layout: { "symbol-placement": "line", "text-field": ["get", "name"], "text-font": ["Montserrat Regular"],
                  "text-size": 10 } },
    ],
  });
}
const STYLES = { light: standInStyle(false), dark: standInStyle(true) };

// A 1x1 transparent PNG, for every raster tile and any sprite image.
const BLANK_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "base64");
// MapLibre fetches from a worker with CORS, so every answer says who may read it.
const HEADERS = { "access-control-allow-origin": "*", "cache-control": "public, max-age=3600" };

let answered = 0;

function answer(route) {
  answered++;
  const { pathname } = new URL(route.request().url());
  const reply = (contentType, body) => route.fulfill({ status: 200, headers: HEADERS, contentType, body })
    .catch(() => {}); // the page closed first
  if (/\/style\.json$/.test(pathname))
    return reply("application/json", /dark-matter/.test(pathname) ? STYLES.dark : STYLES.light);
  if (/\.json$/.test(pathname)) return reply("application/json", "{}");
  if (/\.png$/.test(pathname)) return reply("image/png", BLANK_PNG);
  // an empty vector tile, an empty glyph range, and anything else CARTO serves
  return reply("application/x-protobuf", Buffer.alloc(0));
}

const isCarto = (url) => CARTO_HOST.test(url.hostname);

// Every context the browser opens from here on answers CARTO with the stand-in.
// It wraps browser.newContext rather than asking each check to opt in, so a
// check added later cannot spend the quota by forgetting to.
export function stubBasemap(browser) {
  const plain = browser.newContext.bind(browser);
  browser[PLAIN_NEW_CONTEXT] = plain;
  if (process.env.REAL_BASEMAP) {
    console.log("  (REAL_BASEMAP is set: the CARTO basemap is fetched for real, and counts against the quota)");
    return browser;
  }
  browser.newContext = async (options) => {
    const context = await plain(options);
    await context.route(isCarto, answer);
    return context;
  };
  process.on("exit", () => {
    if (answered) console.log(`  (CARTO basemap: ${answered} requests answered by the stand-in)`);
  });
  return browser;
}

// A context that fetches the real basemap, for the one check that needs it.
export function realBasemapContext(browser, options) {
  return (browser[PLAIN_NEW_CONTEXT] || browser.newContext.bind(browser))(options);
}
