// Headless boot + behaviour smoke test, run in CI on every pull request
// (.github/workflows/smoke-test.yml). Serves the real index.html and drives it
// in Chromium via Playwright — the check the README's "Validation" section
// describes and that OPTIMIZATION_PLAYBOOK item 5 asked to actually commit.
//
// It deliberately depends only on the app shell (Leaflet from its CDN) and the
// same-origin data/app/*.json files — never on the live district APIs, which
// are flaky/blocked in CI. The four same-origin anchors (County, U.S. House,
// West Virginia Senate and House of Delegates) are the deterministic ground truth,
// and every live service a check needs is stubbed.
//
// Run locally against a static server:
//     python3 -m http.server 8000 &
//     npm install playwright && BASE_URL=http://localhost:8000/wv/ node wv/scripts/smoke_test.mjs
// Configure the URL with BASE_URL (default http://localhost:8000/).

import { chromium } from "playwright";
import { readFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { stubBasemap } from "../../scripts/basemap_stub.mjs";

// Vendored Leaflet fallback for sandboxed environments (e.g. Claude Code web),
// where the browser (Chromium) cannot reach cdnjs.cloudflare.com — it does not
// use the agent HTTPS proxy, so the request resets and the app never boots
// ("L is not defined"). scripts/vendor_leaflet.sh populates this dir via curl,
// which *can* reach the CDN through the proxy; when present we serve Leaflet
// same-origin below so the app boots. Absent (production, GitHub Actions CI)
// the browser loads Leaflet straight from the CDN exactly as before.
const VENDOR_DIR = join(dirname(fileURLToPath(import.meta.url)), "vendor", "leaflet");
const VENDORED_LEAFLET =
  existsSync(join(VENDOR_DIR, "leaflet.js")) && existsSync(join(VENDOR_DIR, "leaflet.css"))
    ? { js: readFileSync(join(VENDOR_DIR, "leaflet.js")), css: readFileSync(join(VENDOR_DIR, "leaflet.css")) }
    : null;
if (VENDORED_LEAFLET) console.log("  (serving Leaflet from scripts/vendor/leaflet — CDN unreachable in this env)");
// MapLibre GL (the vector-basemap renderer) rides the same vendor dir: absent,
// the app's own raster fallback keeps the boot alive, so this one is optional
// where Leaflet's pair is required.
const VENDORED_MAPLIBRE = existsSync(join(VENDOR_DIR, "maplibre-gl.min.js"))
  ? { js: readFileSync(join(VENDOR_DIR, "maplibre-gl.min.js")) }
  : null;
if (VENDORED_MAPLIBRE) console.log("  (serving MapLibre GL from scripts/vendor/leaflet — CDN unreachable in this env)");

// Every same-origin file this test reads resolves against the INSTANCE, not
// the process CWD — smoke-test.yml runs all four instances from the repo
// root, and a CWD-relative read silently resolves against whatever directory
// you happen to be in (the ENOENT the ca/ny imports hit at R3). Anchoring
// costs one line and cannot drift.
const INSTANCE_DIR = dirname(dirname(fileURLToPath(import.meta.url)));

const BASE = process.env.BASE_URL || "http://localhost:8000/";
// ==== GENERATED:BEGIN smoke-config ====
const POINT = "38.33650,-81.61230"; // West Virginia State Capitol, 1900 Kanawha Boulevard East, Charleston, Kanawha County
const OFFLINE = ["county", "us-house", "wv-senate", "wv-house"];
const EXPECT_DISTRICT = { "county": "Kanawha County", "us-house": "1", "wv-senate": "8", "wv-house": "54" };
const NEGATIVE_POINT = "39.55000,-79.25000"; // Garrett County, Maryland, about 20 km east of the West Virginia line at Preston County — outside West Virginia and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-29: TIGERweb's state and county layers name Maryland and Garrett County here (control: the State Capitol returns West Virginia and Kanawha County), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does. A POINT ON A NEIGHBOUR'S LAND WILL HAVE TO MOVE THE DAY THAT NEIGHBOUR GOES LIVE: Kentucky is live already, and Maryland, Pennsylvania, Ohio and Virginia are not, so the change that makes Maryland live moves this point, the way Kentucky's go-live moved Indiana's.
const APP_NAME = "districtry West Virginia";
const EXPECT_LAYERS = 11;
// ==== GENERATED:END smoke-config ====
// Instance constants this file owns (the worksheet emits the block above).
// Instance constants this file owns (the worksheet emits the block above).
const EXPORTS_NAME = "WestVirginiaExplorer";
const PORTAL_HOST = "data.invalid"; // must stay a non-empty hostname: an empty string would abort every request
// Geocoder type-ahead fixture: RAW carries an embedded unit the app's cleaner
// must strip to CLEANED; the Photon STUB answers only CLEANED, so the check
// proves the strip-and-retry path with no live network. The address is the
// fleet's shared placeholder; only its position is this state's.
const GEOCODER_QUERY_RAW = "16 W Jones St Suite 200, Capital City";
const GEOCODER_UNIT_FRAGMENT = "Suite 200";
const GEOCODER_QUERY_CLEANED = "16 W Jones St, Capital City";
const GEOCODER_STUB_FEATURE = {
  type: "Feature",
  geometry: { type: "Point", coordinates: [-81.61230, 38.33650] },
  properties: {
    // the typed number: an answer without it shows the street instead of
    // a row (ENGINE geocoder-search runAddressSearch)
    housenumber: "16",
    street: "W Jones St",
    city: "Capital City",
    state: "West Virginia",
    postcode: "00000"
  }
};
// Contract stubs (their consuming checks are reference-fork scenarios,
// dropped from this instance's body):
const GAP_PROBE = { county: "statewide", label: "Statewide", lat: 38.33650, lng: -81.61230 };
const MOVE_POINT = { lat: 0, lng: 0, district: "0" };
const STRAGGLER_FILE = "data/app/state-counties.json";
const STRAGGLER_POINT = "0,0";
// Layers expected to HIDE (not merely report no district) at NEGATIVE_POINT.
// None of the four anchors declares a coverage() test, so none hide — they
// all take the honest "no district here" branch instead.
const NEGATIVE_HIDDEN = [];
const BOOT_TIMEOUT = 45000; // Leaflet CDN + first paint on a cold CI runner
const QUERY_TIMEOUT = 25000;


// The app's rule for a shipped file: even-odd within a polygon, any part of a
// multipolygon. Used to read what the shipped files put at a point, so an
// expectation moves with a rebuild instead of being written down here.
function inRing(x, y, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
function propsAt(fc, point) {
  const [lat, lng] = point.split(",").map(Number);
  return fc.features.filter((f) => {
    const g = f.geometry;
    const polys = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
    return polys.some((rings) => rings.reduce((acc, ring) => acc !== inRing(lng, lat, ring), false));
  }).map((f) => f.properties);
}
function shipped(name) {
  return JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "app", name), "utf8"));
}
// "2030-01-13" -> "January 13, 2030", the card's own date wording.
const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
  "August", "September", "October", "November", "December"];
function longDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
  return m ? `${MONTHS[Number(m[2]) - 1]} ${Number(m[3])}, ${m[1]}` : null;
}
// A card writes a telephone with non-breaking hyphens (U+2011).
const plain = (s) => String(s || "").replace(/‑/g, "-");

const failures = [];
function check(name, ok, detail) {
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);
  if (!ok) failures.push(name);
}

// Each check runs in its own context with service workers BLOCKED. The app's
// SW serves data/app/* cache-first and — critically — its requests are not
// interceptable by page.route, so an active SW would defeat the failure
// injection in check 3 (it did, flakily, on the first CI run). The SW is a
// delivery optimization, not what this behaviour test targets, so we take it
// out of the picture; the app's layer behaviour is identical without it.
async function booted(context, url, routeFn) {
  const page = await context.newPage();
  if (VENDORED_LEAFLET) {
    await page.route("**/cdnjs.cloudflare.com/**/leaflet.js", (r) =>
      r.fulfill({ status: 200, contentType: "application/javascript", body: VENDORED_LEAFLET.js }));
    await page.route("**/cdnjs.cloudflare.com/**/leaflet.css", (r) =>
      r.fulfill({ status: 200, contentType: "text/css", body: VENDORED_LEAFLET.css }));
  }
  if (VENDORED_MAPLIBRE) {
    await page.route("**/cdnjs.cloudflare.com/**/maplibre-gl.min.js", (r) =>
      r.fulfill({ status: 200, contentType: "application/javascript", body: VENDORED_MAPLIBRE.js }));
  }
  if (routeFn) await routeFn(page);
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.waitForFunction((n) => !!window[n], EXPORTS_NAME, { timeout: BOOT_TIMEOUT });
  return page;
}

// Wait for a layer card to finish loading, then return its normalized text.
// Redesigned cards (docs/CARD_RENDER_API.md) render a .card-flush body and
// move the district identifier into the header pill (.card-id-pill), so
// completion accepts either card generation and the returned text prepends
// the pill — the "District N" assertions read the whole card, not just the
// body, exactly as a user does.
async function cardText(page, id) {
  await page
    .waitForFunction(
      (cid) => {
        const el = document.getElementById("card-" + cid);
        return el && !el.querySelector(".loading-row") &&
          (el.querySelector(".card-flush") ||
           el.classList.contains("state-compact") ||
           el.querySelector(".state-empty") ||
           el.classList.contains("state-empty") || el.classList.contains("state-error") || el.querySelector(".state-error"));
      },
      id,
      { timeout: QUERY_TIMEOUT }
    )
    .catch(() => {});
  return page.evaluate((cid) => {
    const el = document.getElementById("card-" + cid);
    if (!el) return { text: "(no card)", error: true, empty: false };
    const block = el.closest(".layer-block");
    const pill = block && block.querySelector(".card-id-pill:not([hidden])");
    // a compact (4b name-only) card renders its whole reader-visible content
    // into the block HEAD (.card-compact-value/-meta) and leaves the body
    // empty — read the head, or a compact layer's card reads as blank
    const compact = block
      ? Array.from(block.querySelectorAll(".card-compact-value, .card-compact-meta"))
          .map((n) => n.textContent).join(" ")
      : "";
    const text = (pill ? pill.textContent + " " : "") + (compact ? compact + " " : "") + el.innerText;
    return {
      text: text.replace(/\s+/g, " ").trim(),
      error: el.classList.contains("state-error") || !!el.querySelector(".state-error"),
      empty: el.classList.contains("state-empty") || !!el.querySelector(".state-empty"),
    };
  }, id);
}

const browser = stubBasemap(await chromium.launch());
try {
  // 1. App boots and registers every layer.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, BASE);
    check(`app boots (window.${EXPORTS_NAME} exported)`, true);
    const n = await page.evaluate(
      () => document.querySelectorAll('input[type=checkbox][id^="toggle-"]').length
    );
    check(`${EXPECT_LAYERS} layers registered`, n === EXPECT_LAYERS, `found ${n}`);

    // Regression guard for the office-pin address cleaner (a recurring break
    // point — secondary-unit fragments packed into the street segment made the
    // geocode return nothing, silently dropping the map pin). Pure function,
    // run in-browser against a fixed table — no network, deterministic.
    const poiCases = [
      ["118 NORTH CLARK STREET ROOM 230 PEORIA, IL 61602", "118 NORTH CLARK STREET PEORIA, IL 61602"], // embedded Room
      ["105 SOUTH 5TH STREET SUITE 104 OREGON, IL 61061", "105 SOUTH 5TH STREET OREGON, IL 61061"],       // embedded Suite
      ["88-11 Sutphin Blvd #106, Jamaica, NY 11435", "88-11 Sutphin Blvd, Jamaica, NY 11435"],            // embedded #, dashed house no.
      ["851 Grand Concourse, Room 118, Bronx, NY 10451", "851 Grand Concourse, Bronx, NY 10451"],         // comma-part Room (must still work)
      ["#10 PUBLIC SQUARE BELLEVILLE, IL 62220", "#10 PUBLIC SQUARE BELLEVILLE, IL 62220"],               // leading # is a primary number — keep it
      ["200 S Biscayne Blvd, Miami, FL 33131", "200 S Biscayne Blvd, Miami, FL 33131"],                   // FL state code — never strip
      ["507 VERMONT STREET QUINCY, IL 62301", "507 VERMONT STREET QUINCY, IL 62301"],                     // no unit — untouched
      // The three shapes the numeric-only rules missed, measured across the
      // whole shipped roster corpus (8 of 37 unit-bearing addresses).
      ["115 WEST COURT STREET ROOM J PARIS, IL 61944", "115 WEST COURT STREET PARIS, IL 61944"],          // letter-only unit
      ["719 SOUTH BATAVIA AVENUE BUILDING B GENEVA, IL 60134", "719 SOUTH BATAVIA AVENUE GENEVA, IL 60134"], // letter-only Building
      ["1 SUPERMAN SQUARE, ROOM 2A PO BOX 429 METROPOLIS, IL 62960", "1 SUPERMAN SQUARE METROPOLIS, IL 62960"], // unit + PO box
      ["2S101 Harter Rd. (P.O. Box 83), Kaneville IL 60144", "2S101 Harter Rd., Kaneville IL 60144"],     // parenthesized PO box
      ["69 W. Washington St. - 6th Floor", "69 W. Washington St."],                                       // dash left by the removed floor
      // …and the guards those rules must not trip: a box-only address keeps its
      // box (it geocodes to nothing and the card honestly drops its pin, rather
      // than pinning a city centroid), and hyphens inside names survive.
      ["P.O. Box 429, Metropolis IL 62960", "P.O. Box 429, Metropolis IL 62960"],                         // no street — leave it alone
      ["100 Main St, Winston-Salem, NC 27101", "100 Main St, Winston-Salem, NC 27101"]                    // hyphenated city — never trimmed
    ];
    const poiResults = await page.evaluate(
      ({ cases, n }) => cases.map(([input]) => window[n].cleanPoiAddress(input)),
      { cases: poiCases, n: EXPORTS_NAME }
    );
    const poiBad = poiCases
      .map(([input, want], i) => ({ input, want, got: poiResults[i] }))
      .filter((r) => r.got !== r.want);
    check("cleanPoiAddress strips embedded units, keeps primary #/state",
      poiBad.length === 0,
      poiBad.length ? JSON.stringify(poiBad[0]) : `${poiCases.length}/${poiCases.length} cases`);

    await context.close();
  }

  // 1a. The Data gaps panel: the honest inventory of what the app cannot answer,
  //     and the source-submission path. Asserted here because the panel is the
  //     one surface whose whole job is to be accurate about absence — a silently
  //     empty or unfiltered list is worse than no panel at all. Same-origin data,
  //     so this needs no network.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, BASE);
    const shipped = JSON.parse(readFileSync(join(INSTANCE_DIR, "data/app/coverage-gaps.json"), "utf8"));
    const expected = Object.keys(shipped).length;

    async function openGaps() {
      await page.evaluate(() => { const m = document.getElementById("gaps-modal"); if (m) m.hidden = true; });
      await page.click("#gaps-btn");
      await page.waitForFunction(() => {
        const b = document.getElementById("gaps-body");
        return b && !/Loading/.test(b.textContent) && b.textContent.trim().length > 0;
      }, null, { timeout: QUERY_TIMEOUT }).catch(() => {});
      // Every gap lives inside a <details class="gaps-group">, so a section is
      // read as {label, count-as-rendered, items-actually-inside}. Counting the
      // items INSIDE each group rather than walking siblings is what makes this
      // fork-generic: a sibling with three gaps renders three small groups and
      // the reference fork renders four large ones, and both satisfy the same assertions.
      return page.evaluate(() => {
        const b = document.getElementById("gaps-body");
        const groups = Array.from(b.querySelectorAll(".gaps-group")).map((g) => ({
          label: (g.querySelector(".gaps-section-text") || {}).textContent || "",
          shown: Number((g.querySelector(".gaps-section-count") || {}).textContent),
          items: g.querySelectorAll(".gap-item").length,
        }));
        return {
          items: b.querySelectorAll(".gap-item").length,
          lede: (b.querySelector(".gaps-lede") || {}).textContent || "",
          groups,
          details: b.querySelectorAll(".gap-item .gap-more").length,
          hrefs: Array.from(b.querySelectorAll(".gap-suggest")).map((a) => a.getAttribute("href")),
        };
      });
    }

    const cold = await openGaps();
    // A fork can genuinely ship zero recorded gaps (this instance, at launch) —
    // the honest render is zero groups, not a forced placeholder group, so the
    // "at least one group" expectation only applies when gaps are expected.
    const groupsOk = expected === 0 ? cold.groups.length === 0 : cold.groups.length >= 1;
    check("data gaps panel renders every recorded gap, grouped with honest counts",
      cold.items === expected && groupsOk &&
      cold.groups.every((g) => g.label && g.shown === g.items) &&
      cold.groups.reduce((n, g) => n + g.items, 0) === expected,
      `${cold.items}/${expected} items in ${cold.groups.length} group(s): ` +
      JSON.stringify(cold.groups));
    // The panel's whole point is that a reader can scan it. Detail belongs
    // behind a disclosure, one per gap — this is the assertion that would fail
    // if a research note ever grew back into the card body.
    check("every gap keeps its detail behind a disclosure",
      cold.details === expected, `${cold.details}/${expected} disclosures`);
    check("every gap offers a prefilled source submission",
      cold.hrefs.length === expected &&
      cold.hrefs.every((h) => /template=source-submission\.yml/.test(h) && /[?&]gap_id=/.test(h)),
      `${cold.hrefs.length} links`);

    // ==== TEMPLATE:BEGIN smoke-coverage-band ====
    // THIS INSTANCE PAINTS NO MIDDLE BAND, AND THAT IS THE CLAIM ASSERTED HERE.
    // The gaps lede answers three ways since 2026-09-26 — inside the covered
    // area, inside a wider region whose own key says what still answers there,
    // or outside both — and the middle answer exists only where the app hands
    // drawOutOfScopeMask a region geometry. This one hands it none, so the wash
    // has two bands and the lede must keep saying "nothing there can be
    // answered yet" beyond the covered area. Asserted rather than assumed
    // because the engine block is one shared copy: a change that started
    // retaining a region unconditionally would have this app claiming something
    // answers where nothing does, and nothing static could see it — the
    // sentence is assembled at runtime from a point test.
    //
    // IT WAITS FOR THE WASH FIRST. A null coverage test correctly falls through
    // to wording that claims neither, so a point selected before the wash has
    // loaded asserts against the app's "we cannot tell yet" state — which is
    // what CI caught on this check's first draft.
    async function washPainted() {
      return page.waitForFunction(() => {
        const pane = document.querySelector(".leaflet-pane.leaflet-scope-mask-pane");
        return !!(pane && pane.querySelector("path"));
      }, null, { timeout: QUERY_TIMEOUT }).then(() => true, () => false);
    }
    if (await washPainted()) {
      await page.evaluate(({ n, p }) => window[n].setSelectedPoint(p[0], p[1]),
        { n: EXPORTS_NAME, p: NEGATIVE_POINT.split(",").map(Number) });
      const beyond = await openGaps();
      check("gaps lede claims no coverage band at the negative point",
        /nothing there can be answered yet/.test(beyond.lede) &&
        !/covers in full/.test(beyond.lede), JSON.stringify(beyond.lede));
    } else {
      check("gaps lede claims no coverage band at the negative point", false,
        "the wash never painted, so the panel's coverage test could only answer unknown");
    }
    // ==== TEMPLATE:END smoke-coverage-band ====


    await context.close();
  }

  // 1a-ii. The two "about the data" doors, which are chrome nothing else
  //     asserts. The gaps button moved out of the footer into the masthead so a
  //     reader meets the caveat before the answers; the sources page took over
  //     the footer's credit row and expanded it to one row per layer. Both are
  //     load-bearing honesty surfaces: a matrix silently missing a layer reads
  //     as "that layer has no source", and a gaps button nobody scrolls to is a
  //     caveat nobody reads. Static markup, so no network.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, BASE);

    const chrome = await page.evaluate(() => ({
      gapsInMasthead: !!document.querySelector("header.masthead #gaps-btn"),
      sourcesLinks: Array.from(document.querySelectorAll('a[href$="sources.html"]')).length,
    }));
    check("gaps button sits in the masthead, not the footer",
      chrome.gapsInMasthead, `inMasthead=${chrome.gapsInMasthead}`);

    // sources.html sends readers back with #gaps; that must land ON the panel.
    // Through booted(), not a bare newPage: the panel's handler is attached by
    // the app script, so a page that never boots would fail this for the wrong
    // reason (and does, in the sandbox where the Leaflet CDN is unreachable).
    const deep = await booted(context, new URL("#gaps", BASE).href);
    await deep.waitForFunction(() => {
      const m = document.getElementById("gaps-modal");
      return m && !m.hidden;
    }, null, { timeout: QUERY_TIMEOUT }).catch(() => {});
    const opened = await deep.evaluate(() => {
      const m = document.getElementById("gaps-modal");
      return !!m && !m.hidden;
    });
    check("#gaps deep link opens the gaps panel", opened, `open=${opened}`);
    await deep.close();
    await context.close();
  }


  // 1a2. A SELECTION GOES TO THE APP THAT ANSWERS THERE, decided by state
  //     outlines (ENGINE metro-portal + the root fleet-outlines.json) rather
  //     than by rectangles. The sibling apps are stubbed so a wrong route
  //     cannot leave for the real site — unstubbed, a wrong route navigates to
  //     the real districtry.com, fails in the sandbox and leaves page.url() on
  //     the app, which reads exactly like correct behaviour.
  //
  //     WEST VIRGINIA HAS FIVE NEIGHBOURS, AND THE FLEET SERVES ONE OF THEM.
  //     A click a little way inside Kentucky must open Kentucky's app:
  //     Ashland and Pikeville, measured against fleet-outlines.json on
  //     2026-10-29, each inside Kentucky's outline and no other, about 6 and
  //     26 km from this app's outline. This instance answers its own side from
  //     the state outline the wash retained, with no fetch. Chicago proves the
  //     file is still read for ground far from here.
  //
  //     OHIO, PENNSYLVANIA, MARYLAND AND VIRGINIA ARE DELIBERATELY NOT CASES.
  //     Nobody serves them today, so a click there stays here; but the fleet
  //     is meant to reach every state, and a "stays here" case in any of them
  //     would start failing the day it goes live, in a change that is about
  //     another state. The negative point carries that half instead (1a2-ii),
  //     and it is the one thing in this file that must move when Maryland
  //     goes live (WATCH.md).
  {
    const cases = [
      { name: "Chicago", lat: 41.8825, lng: -87.6285, want: "https://districtry.com/il/" },
      { name: "Ashland, Kentucky", lat: 38.4784, lng: -82.6379, want: "https://districtry.com/ky/" },
      { name: "Pikeville, Kentucky", lat: 37.4793, lng: -82.5185, want: "https://districtry.com/ky/" },
    ];
    for (const c of cases) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, BASE, async (p) => {
        await p.route("https://districtry.com/**", (route) =>
          route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>sibling</title>" }));
      });
      await page.evaluate(({ c, n }) => {
        window[n].map.fire("click", { latlng: window.L.latLng(c.lat, c.lng) });
      }, { c, n: EXPORTS_NAME });
      const went = await page.waitForURL((u) => u.href.startsWith(c.want + "#point="), { timeout: QUERY_TIMEOUT })
        .then(() => page.url(), () => null);
      check(`a click on ${c.name} from West Virginia opens ${c.want} with the point`, !!went, went || page.url());
      await context.close();
    }
  }

  // 1a2-ii. The half that keeps 1a2 honest: the negative point, in Garrett
  //     County, Maryland, about 20 km east of the West Virginia line, is
  //     outside every outline in the fleet, so the click must stay HERE. A
  //     route to a sibling would be the same lie pointing the other way, and
  //     the stub makes it visible: if the app navigated, the URL would be the
  //     stubbed sibling rather than this app.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, BASE, async (p) => {
      await p.route("https://districtry.com/**", (route) =>
        route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>sibling</title>" }));
    });
    await page.evaluate(({ n, pt }) => {
      const [la, ln] = pt.split(",").map(Number);
      window[n].map.fire("click", { latlng: window.L.latLng(la, ln) });
    }, { n: EXPORTS_NAME, pt: NEGATIVE_POINT });
    await page.waitForTimeout(3000);
    const url = page.url();
    // Still under BASE means still this app. Asking instead for the URL NOT to
    // name one of a list of sibling tags needs a new entry each time a state
    // goes live, and the one it lacked would read as staying here.
    check("a click in Maryland, outside every app's outline, stays in this app",
      url.startsWith(BASE), url);
    await context.close();
  }

  // 1b. The search box retries a zero-result query with the unit fragment
  //     stripped. Stubbed geocoder, so this is deterministic and needs no
  //     external network: the stub answers ONLY the cleaned form, which is what
  //     the real geocoder does for these queries. Guards two properties at once
  //     — the retry happens, and it does NOT fire when there is nothing to
  //     clean (the raw query must always get first crack, so a search that
  //     works today can never regress into a second round-trip).
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const seen = [];
    const page = await booted(context, BASE, async (p) => {
      await p.route("**/photon.komoot.io/**", (route) => {
        const u = new URL(route.request().url());
        // the home-metro search carries bbox; the sibling-metro fallback is the
        // same host WITHOUT it — never conflate the two when counting requests
        seen.push({ q: u.searchParams.get("q"), bounded: u.searchParams.has("bbox") });
        const hit = u.searchParams.get("q") === GEOCODER_QUERY_CLEANED;
        route.fulfill({
          status: 200, contentType: "application/json",
          body: JSON.stringify({
            type: "FeatureCollection",
            features: hit ? [GEOCODER_STUB_FEATURE] : [],
          }),
        });
      });
    });

    // One page task, not fill()+press(): those are two Playwright actions with
    // real wall-clock between them, and when a loaded runner stretched that gap
    // past the input handler's 400ms debounce, the type-ahead fired its own
    // search ahead of Enter's — two bounded calls for one query, which the
    // exact counts below read as a retry (bounded=2 total=3 on main runs
    // 33029973722 and 33040783537). Dispatching input and submit in one
    // synchronous task still runs both app handlers — input arms the debounce,
    // submit cancels it and searches — but leaves the timer no gap to fire in.
    async function search(q) {
      await page.evaluate((query) => {
        const input = document.getElementById("geocode-input");
        input.value = query;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        document.getElementById("geocode-form").requestSubmit();
      }, q);
    }

    await search(GEOCODER_QUERY_RAW);
    await page
      .waitForFunction(() => document.querySelectorAll("#geocode-results li").length > 0 ||
        /^Selected:/.test((document.getElementById("geo-status") || {}).textContent || ""),
        null, { timeout: QUERY_TIMEOUT })
      .catch(() => {});
    const rows = await page.$$eval("#geocode-results li", (ls) => ls.length);
    // one answer that is the house is selected at once (selectClearMatch),
    // which empties the list
    const selected = await page.$eval("#geo-status", (el) => /^Selected:/.test(el.textContent || ""));
    const bounded = seen.filter((c) => c.bounded);
    check("search box retries a unit-fragment miss with the cleaned address",
      bounded.length === 2 && bounded[0].q.includes(GEOCODER_UNIT_FRAGMENT) && bounded[1].q === GEOCODER_QUERY_CLEANED && (rows > 0 || selected),
      `calls=${JSON.stringify(bounded.map((c) => c.q))} rows=${rows} selected=${selected}`);

    seen.length = 0;
    await search("nowhere at all xyzzy");
    await page.waitForTimeout(2000);
    check("a query with nothing to clean is not retried",
      seen.filter((c) => c.bounded).length === 1,
      `bounded=${seen.filter((c) => c.bounded).length} total=${seen.length}`);

    await context.close();
  }

  // 2. The four same-origin anchors classify a known point against known
  //    ground truth, fetched from data/app/*.json. Two expected-value shapes:
  //    a NUMERIC expectation asserts the card's own "District N" token exactly
  //    (never a stray digit elsewhere in the card); a NAME expectation (the
  //    County anchor, whose card prints an identity rather than a number)
  //    asserts the card names that identity verbatim.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=${OFFLINE.join(",")}`);
    for (const id of OFFLINE) {
      const info = await cardText(page, id);
      const want = EXPECT_DISTRICT[id];
      const m = /District\s+(\S+)/i.exec(info.text);
      const got = m ? m[1] : null;
      const ok = /[^0-9]/.test(want) ? info.text.includes(want) : got === want;
      check(
        `${id} classifies point (District ${want})`,
        !info.error && ok,
        info.text.slice(0, 70)
      );
    }
    // 2a. EACH CHAMBER'S OWN ROSTER NAMES THE MEMBERS, and the card carries
    //     what the Legislature prints: the name, the party, the Capitol office
    //     and the member's e-mail address, which must open as a mailto link.
    //     The Senate elects two senators per district, so its card must name
    //     BOTH; the House of Delegates one. The values expected are read from
    //     the shipped roster for each chamber's anchor district, so a weekly
    //     refresh that changes them changes what is expected. An office can
    //     sit behind a closed disclosure, which innerText leaves out, so the
    //     office is read from textContent.
    async function cardDom(cid) {
      return page.evaluate((id) => {
        const el = document.getElementById("card-" + id);
        return {
          all: el ? el.textContent.replace(/\s+/g, " ") : "",
          mailto: el ? Array.from(el.querySelectorAll("a[href^='mailto:']"))
            .map((a) => decodeURIComponent(a.getAttribute("href").slice(7)).toLowerCase()) : [],
        };
      }, cid);
    }
    const memberOk = (m, text, dom) =>
      !!m.name && text.includes(m.name) &&
      !!m.party && text.toLowerCase().includes(String(m.party).toLowerCase()) &&
      !!(m.capitolOffice || [])[0] && dom.all.includes(m.capitolOffice[0]) &&
      !!m.email && dom.mailto.includes(String(m.email).toLowerCase());
    {
      const rec = shipped("wv-senate-members.json")[EXPECT_DISTRICT["wv-senate"]] || {};
      const members = rec.members || [];
      const info = await cardText(page, "wv-senate");
      const dom = await cardDom("wv-senate");
      const bad = members.filter((m) => !memberOk(m, info.text, dom)).map((m) => m.name);
      check("wv-senate card names BOTH senators, each with party, Capitol office and e-mail address",
        !info.error && rec.seats === 2 && members.length === 2 && bad.length === 0 &&
          /Each West Virginia Senate district elects two senators/.test(info.text),
        `members=${members.length} bad=${bad} ${info.text.slice(0, 120)}`);
    }
    {
      const rec = shipped("wv-house-members.json")[EXPECT_DISTRICT["wv-house"]] || {};
      const info = await cardText(page, "wv-house");
      const dom = await cardDom("wv-house");
      check("wv-house card names the delegate, the party, the Capitol office and the e-mail address the Legislature prints",
        !info.error && memberOk(rec, info.text, dom),
        `name=${rec.name} mailto=${JSON.stringify(dom.mailto)} ${info.text.slice(0, 80)}`);
    }
    await context.close();
  }

  // 2a2. A SENATE DISTRICT THE ROSTER LISTS WITH ONE SENATOR NAMES THAT ONE
  //     AND SAYS SO, rather than printing a second name or none. The shipped
  //     roster lists two for every district today, so the roster is served
  //     with the anchor district's second member removed. And a roster that
  //     fails to load names nobody while the district still classifies.
  {
    const roster = shipped("wv-senate-members.json");
    const d = EXPECT_DISTRICT["wv-senate"];
    const [kept, dropped] = (roster[d] || {}).members || [];
    const oneLeft = JSON.parse(JSON.stringify(roster));
    oneLeft[d].members = [kept];
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=wv-senate`, async (p) => {
        await p.route("**/data/app/wv-senate-members.json", (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(oneLeft) }));
      });
      const info = await cardText(page, "wv-senate");
      const text = info.text || "";
      check("wv-senate names the one senator a district's roster lists, and says only that one is named",
        !info.error && !!kept && text.includes(kept.name) && !!dropped && !text.includes(dropped.name) &&
          /lists 1 senator for this district/.test(text) && /only that one is named here/.test(text),
        text.slice(0, 160));
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=wv-senate`, async (p) => {
        await p.route("**/data/app/wv-senate-members.json", (r) => r.fulfill({ status: 503, body: "down" }));
      });
      const info = await cardText(page, "wv-senate");
      const text = info.text || "";
      check("wv-senate still classifies and names nobody when the list of senators fails",
        !info.error && new RegExp(`District ${d}\\b`).test(text) &&
          /did not load, so no one is named here/.test(text) &&
          ![kept, dropped].some((m) => m && text.includes(m.name)),
        text.slice(0, 120));
      await context.close();
    }
  }


  // 2b. The negative ground-truth point (from the worksheet: a point outside
  //     every anchor layer). Anchors that declare a location-relevance test
  //     (mod.coverage — see NEGATIVE_HIDDEN above) HIDE there: the toggle
  //     block is suppressed, the query is skipped, and the layers= permalink
  //     is left intact (hide-only — state.layersOn is never mutated). Anchors
  //     without a coverage test keep the honest empty state — "no district
  //     here" as a statement of fact, not an error and not a wrong district.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    // A fork's coverage fallback leg may consult a second dataset
    // (Socrata) after an ERSB miss. On a black-holed network (the sandboxed
    // dev env) that rejection is slow — through the loader's route retries —
    // which stalls the hide verdict past this check's wait. Abort it so the
    // fallback's own catch ("stand on the first tiling's verdict") runs
    // deterministically fast in every environment; the verdict here is
    // identical either way — the negative point is outside both tilings.
    const page = await booted(context, `${BASE}#point=${NEGATIVE_POINT}&layers=${OFFLINE.join(",")}`, async (p) => {
      await p.route(`**${PORTAL_HOST}**`, (r) => r.abort());
    });
    for (const id of OFFLINE) {
      if (NEGATIVE_HIDDEN.includes(id)) {
        const hidden = await page
          .waitForFunction((cid) => {
            const box = document.getElementById("toggle-" + cid);
            const block = box && box.closest(".layer-block");
            return block && block.hidden === true;
          }, id, { timeout: QUERY_TIMEOUT })
          .then(() => true, () => false);
        const hashKeepsLayer = await page.evaluate(
          ({ cid, n }) => window[n].permalinkState().layers.includes(cid), { cid: id, n: EXPORTS_NAME });
        // assert the invariant directly, not just its hash reflection: hide
        // must never mutate state.layersOn (that's what keeps permalinks and
        // reappear-on-return working)
        const stillOn = await page.evaluate(
          ({ cid, n }) => window[n].state.layersOn[cid] === true, { cid: id, n: EXPORTS_NAME });
        check(
          `${id} hides at the negative point (out of coverage, permalink intact)`,
          hidden && hashKeepsLayer && stillOn,
          `hidden=${hidden} permalink=${hashKeepsLayer} layersOn=${stillOn}`
        );
      } else {
        const info = await cardText(page, id);
        check(
          `${id} reports no district at the negative point`,
          info.empty && !info.error,
          info.text.slice(0, 70)
        );
      }
    }
    await context.close();
  }


  // 2e. Share control: the point chip carries ONE "Share" button whose popover
  //     serves the live campaign-tagged permalink, the embed snippet (tagged
  //     with its own source and pointed at the canonical deployment), and the
  //     coordinates — replacing the old Copy link / Embed pill pair. Headless
  //     desktop Chromium has no navigator.share, so this always exercises the
  //     popover path; Escape must close it.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=county`);
    await page.waitForFunction(() => !!document.querySelector("#point-chip .share-btn"), null, { timeout: QUERY_TIMEOUT });
    const res = await page.evaluate(() => {
      const btn = document.querySelector("#point-chip .share-btn");
      btn.click();
      const pop = document.querySelector("#point-chip .share-popover");
      if (!pop) return { opened: false };
      const url = pop.querySelector(".share-popover-url").value;
      const embed = pop.querySelector(".share-popover-embed").value;
      const coords = pop.querySelector(".share-popover-coords").textContent;
      // the values are built at open time, AFTER the click's syncUrlHash —
      // so location.hash here is exactly the hash both strings must carry
      const wantUrl = location.origin + location.pathname + "?ref=share" + location.hash;
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      return {
        opened: true,
        urlOk: url === wantUrl,
        linkTagged: url.indexOf("?ref=share#") !== -1,
        embedTagged: embed.indexOf("?ref=embed#") !== -1,
        embedShape: embed.indexOf('<iframe src="') === 0 && embed.indexOf(location.hash) !== -1,
        embedCanonical: embed.indexOf(location.origin) === -1 || location.hostname !== "localhost",
        coordsOk: /^-?\d+\.\d{5}, -?\d+\.\d{5}$/.test(coords),
        closedOnEscape: !document.querySelector("#point-chip .share-popover"),
      };
    });
    check(
      "share popover serves tagged permalink + embed + coordinates",
      res.opened && res.urlOk && res.linkTagged && res.embedTagged &&
        res.embedShape && res.embedCanonical && res.coordsOk && res.closedOnEscape,
      JSON.stringify(res)
    );
    await context.close();
  }


  // 5. Base-map tile failure surfaces an honest, dismissible banner (R6 / item
  //    16), instead of a silently gray map. Fail the CARTO tile CDN and assert
  //    the banner appears, then that dismissing it hides it.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, BASE, (p) =>
      // regex, not a glob: the tile host is `a.basemaps.cartocdn.com` (a dot,
      // not a slash, before `basemaps`), which a `**/basemaps…` glob misses.
      p.route(/basemaps\.cartocdn\.com/, (r) => r.fulfill({ status: 503, body: "down" }))
    );
    await page
      .waitForFunction(() => {
        const el = document.getElementById("tile-banner");
        return el && !el.hidden;
      }, null, { timeout: QUERY_TIMEOUT })
      .catch(() => {});
    const shown = await page.evaluate(() => {
      const el = document.getElementById("tile-banner");
      return !!el && !el.hidden;
    });
    let hiddenAfterDismiss = null;
    if (shown) {
      await page.click("#tile-banner-dismiss");
      hiddenAfterDismiss = await page.evaluate(() => {
        const el = document.getElementById("tile-banner");
        return !!el && el.hidden;
      });
    }
    check("tile failure shows dismissible banner", shown && hiddenAfterDismiss === true, `shown=${shown} hiddenAfterDismiss=${hiddenAfterDismiss}`);
    await context.close();
  }


  // 6. The USGS structures loader PAGES, and the second page reaches the card.
  //    fire-station is 1,928 points in West Virginia's envelope (measured
  //    2026-10-29), just under the 2,000-record cap the service reports as
  //    HTTP 200 + exceededTransferLimit rather than an error, so one more year
  //    of new stations and a single request would drop real ones while the
  //    nearest-3 card looked correct at every point. The source manifest's count row cannot see
  //    that, because returnCountOnly is not subject to maxRecordCount and
  //    answers the true count whatever the client does. This is the check that
  //    can.
  //
  //    The service is stubbed rather than called, so the assertion is about
  //    THIS APP'S control flow and cannot fail on somebody else's outage. Page
  //    one is far away and flagged as truncated; page two carries one station
  //    at the selected point. A single-request loader would request once, never
  //    see that station, and name a page-one station instead — so this fails
  //    for the right reason rather than merely counting requests.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const offsets = [];
    const fieldsAsked = [];
    const far = (i) => ({
      attributes: { NAME: `FAR STATION ${i}`, ADDRESS: "1 Far Rd", CITY: "Elkins", STATE: "WV", ZIPCODE: "26241" },
      geometry: { x: -83.0458, y: 42.3314 },
    });
    const [lat, lng] = POINT.split(",").map(Number);
    const page = await booted(context, BASE, (p) =>
      p.route(/MapServer\/51\/query/, (route) => {
        const params = new URL(route.request().url()).searchParams;
        const offset = Number(params.get("resultOffset"));
        offsets.push(offset);
        fieldsAsked.push(params.get("outFields") || "");
        // ESRI JSON, not GeoJSON — the shape the app asks for. Every ArcGIS
        // loader moved to f=json on 2026-09-05 because the GeoJSON export
        // unnests interior rings (engine/index.html/arcgis-loader.txt).
        const body = offset === 0
          ? { exceededTransferLimit: true, features: [far(1), far(2), far(3)] }
          : { features: [{
                attributes: { NAME: "PAGE TWO STATION", ADDRESS: "2 Second Page Way",
                              CITY: "Charleston", STATE: "WV", ZIPCODE: "25305" },
                geometry: { x: lng, y: lat },
              }] };
        route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
      })
    );
    await page.evaluate(({ pt, n }) => {
      const [la, ln] = pt.split(",").map(Number);
      window[n].setSelectedPoint(la, ln);
      const box = document.getElementById("toggle-fire-station");
      if (box && !box.checked) box.click();
    }, { pt: POINT, n: EXPORTS_NAME }).catch(() => {});
    let card = { text: "(card never resolved)" };
    try {
      card = await cardText(page, "fire-station");
    } catch (e) { /* keep the placeholder; the assertions below report it */ }
    const text = card.text || "";
    check("USGS structures loader pages past the record cap",
      offsets.length > 1, `requests at offsets [${offsets.join(", ")}]`);
    check("the second page's station reaches the card",
      /PAGE TWO STATION/.test(text), text.slice(0, 140));
    // TWO assertions, because either alone passes while the other half is
    // broken: this stub returns STATE whatever outFields asks for, so a check
    // of the rendered line alone stays green with STATE deleted from the
    // app's request, and a check of the request alone passes with a card that
    // never renders what it fetched.
    check("the app ASKS the service for STATE",
      fieldsAsked.every((f) => /\bSTATE\b/.test(f)),
      `outFields=${fieldsAsked[0] || "(none seen)"}`);
    check("a structure line RENDERS its state",
      /Charleston, WV/.test(text), text.slice(0, 140));
    await context.close();
  }

  // 7. THE LIVE TIGERWEB FABRIC CARDS, STUBBED — and stubbed on purpose rather
  //    than anchored. The worksheet's OFFLINE anchors are same-origin only,
  //    which is this test's own stated contract, and these layers fetch the
  //    Census live: asserting a card against somebody else's server makes the
  //    test fail on their outage and on any network that intercepts TLS.
  //
  //    WHAT IS WORTH TESTING IS THIS INSTANCE'S OWN CODE, and none of it is
  //    exercised by a live fetch that happens to work. Each claim below is
  //    wrong in a way a reader would see:
  //
  //    (a) The municipality card states the style the Census records — a
  //        CITY, a TOWN, a VILLAGE or, for Ranson alone, a CORPORATION,
  //        West Virginia's four — and an affix the card does not know
  //        produces NO type row rather than an improvised one.
  //    (b) The school district card names the district (one per county).
  {
    function esriPolygon(props, ring) {
      return {
        attributes: props,
        geometry: { rings: [ring || [[-82.0, 38.0], [-81.0, 38.0], [-81.0, 38.7], [-82.0, 38.7], [-82.0, 38.0]]] }
      };
    }
    function esriBody(props, ring) {
      return JSON.stringify({
        geometryType: "esriGeometryPolygon",
        spatialReference: { wkid: 4326 },
        fields: Object.keys(props || {}).map((n) => ({ name: n, type: "esriFieldTypeString", alias: n })),
        features: props ? [esriPolygon(props, ring)] : []
      });
    }
    const PLACES = "Places_CouSub_ConCity_SubMCD/MapServer/4";
    const cases = [
      {
        name: "a city names itself a city, alongside the county",
        layer: "municipality", service: PLACES,
        props: { GEOID: "5414600", NAME: "Charleston city", BASENAME: "Charleston", STATE: "54", LSADC: "25", FUNCSTAT: "A" },
        want: [/Charleston city/, /Incorporated city — a general-purpose local government over this point, alongside the county/, /Not named here/],
        reject: [/Incorporated town/, /Incorporated village/, /styled a corporation/]
      },
      {
        name: "a town names itself a town, not a city",
        layer: "municipality", service: PLACES,
        props: { GEOID: "5401000", NAME: "Alderson town", BASENAME: "Alderson", STATE: "54", LSADC: "43", FUNCSTAT: "A" },
        want: [/Alderson town/, /Incorporated town/],
        reject: [/Incorporated city/, /Incorporated village/]
      },
      {
        name: "a village names itself a village",
        layer: "municipality", service: PLACES,
        props: { GEOID: "5400000", NAME: "Example village", BASENAME: "Example", STATE: "54", LSADC: "47", FUNCSTAT: "A" },
        want: [/Example village/, /Incorporated village/],
        reject: [/Incorporated city/, /Incorporated town/]
      },
      {
        name: "Ranson says it is styled a corporation",
        layer: "municipality", service: PLACES,
        props: { GEOID: "5467228", NAME: "Ranson corporation", BASENAME: "Ranson", STATE: "54", LSADC: "51", FUNCSTAT: "A" },
        want: [/Ranson corporation/, /Incorporated municipality, styled a corporation/],
        reject: [/Incorporated city/, /Incorporated town/, /Incorporated village/]
      },
      {
        name: "an affix the card does not carry prints NO type row",
        layer: "municipality", service: PLACES,
        props: { GEOID: "5499999", NAME: "Nowhere borough", BASENAME: "Nowhere", STATE: "54", LSADC: "21", FUNCSTAT: "A" },
        want: [/Nowhere borough/],
        reject: [/Incorporated city/, /Incorporated town/, /Incorporated village/, /styled a corporation/]
      },
      {
        name: "the school district card names the district",
        layer: "school-district-unified", service: "School/MapServer/0",
        props: { GEOID: "5400660", NAME: "Kanawha County School District", STATE: "54" },
        want: [/Kanawha County School District/],
        reject: []
      }
    ];

    for (const c of cases) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=${c.layer}`, async (p) => {
        await p.route(`**/${c.service}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: esriBody(c.props) }));
      });
      const info = await cardText(page, c.layer);
      const text = info.text || "";
      const missing = c.want.filter((re) => !re.test(text));
      const present = c.reject.filter((re) => re.test(text));
      check(c.name, !info.error && missing.length === 0 && present.length === 0,
        missing.length || present.length
          ? `missing=${missing} unwanted=${present} text=${text.slice(0, 160)}`
          : text.slice(0, 90));
      await context.close();
    }
  }


  // 8. THE ZIP LAYER IS IN-STATE ONLY, AND THIS IS THE CHECK THAT PROVES IT.
  //    A ZCTA carries no STATE field, so this is the one layer here whose
  //    point query cannot be filtered server-side — and over a land border it
  //    does not answer with nothing, it answers with a real neighbouring ZIP.
  //    A ZCTA over the line in Ohio, Kentucky, Pennsylvania, Maryland or
  //    Virginia is a real ZIP code the live service returns for a point there.
  //
  //    THE OUT-OF-STATE HALF IS THE ONE THAT DISCRIMINATES. The stub answers
  //    21550 (Oakland, Maryland) whatever point is asked, so a regression that
  //    drops `coverage` shows the block AND renders a Maryland ZIP here, which
  //    is the harm a reader would see. The in-state half is equally
  //    load-bearing: coverage fails OPEN, so a test that only asserted hiding
  //    would also pass on a layer that had stopped working altogether.
  //
  //    The negative point is the worksheet's own, in Maryland and outside the
  //    state outline, which is what the coverage test reads. It moves with the
  //    worksheet the day Maryland goes live, and this check moves with it.
  {
    const ZCTA = "PUMA_TAD_TAZ_UGA_ZCTA/MapServer/11";
    function zctaBody(zip) {
      return JSON.stringify({
        geometryType: "esriGeometryPolygon",
        spatialReference: { wkid: 4326 },
        fields: [{ name: "ZCTA5", type: "esriFieldTypeString", alias: "ZCTA5" }],
        features: [{
          attributes: { ZCTA5: zip },
          // a ring around BOTH probe points, so geometry never decides this
          geometry: { rings: [[[-83, 37], [-77, 37], [-77, 41], [-83, 41], [-83, 37]]] }
        }]
      });
    }

    // in state: the layer answers, and answers from the stub
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=zip-code`, async (p) => {
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("25301") }));
      });
      const info = await cardText(page, "zip-code");
      check("zip-code answers inside West Virginia (coverage fails open, so this half matters)",
        !info.error && /25301/.test(info.text || ""),
        (info.text || "").slice(0, 90));
      await context.close();
    }

    // out of state: the layer HIDES, and the stubbed ZIP never renders
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${NEGATIVE_POINT}&layers=zip-code`, async (p) => {
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("21550") }));
      });
      const hidden = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-zip-code");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === true;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const info = await cardText(page, "zip-code");
      const leaked = /21550/.test(info.text || "");
      const stillOn = await page.evaluate(
        (n) => window[n].state.layersOn["zip-code"] === true, EXPORTS_NAME);
      check("zip-code hides outside West Virginia rather than naming a Maryland ZIP",
        hidden && !leaked && stillOn,
        `hidden=${hidden} leaked=${leaked} layersOn=${stillOn} text=${(info.text || "").slice(0, 90)}`);
      await context.close();
    }
  }

  // 9. EVERY COUNTY'S OFFICIALS, on the County card. The names expected are
  //    read from the shipped roster (data/app/wv-county-officials.json) rather
  //    than written here, because the Secretary of State's next year of the
  //    directory changes them and a name in this file would fail a correct
  //    rebuild. Each case asserts every commissioner and every other officer
  //    the roster carries is named with their own telephone and e-mail
  //    address, the commission's office where the roster has one, the
  //    sentence saying every commissioner represents every point and naming
  //    the magisterial-district rule, the board-of-education sentence, and the
  //    credit and link. Four places:
  //      - Kanawha, at the State Capitol: a three-member commission;
  //      - Berkeley and Jefferson: the two five-member commissions;
  //      - Cabell, whose directory entry lists no assessor.
  //    The other points are poles of inaccessibility of each county as the
  //    shipped file draws it (shapely polylabel, 2026-10-29), 9 to 11 km from
  //    the nearest county line.
  {
    const roster = shipped("wv-county-officials.json");
    const cases = [
      { point: POINT, geoid: "54039" },
      { point: "39.45844,-78.05805", geoid: "54003" },
      { point: "39.28956,-77.87265", geoid: "54037" },
      { point: "38.44648,-82.20542", geoid: "54011" },
    ];
    for (const c of cases) {
      const o = roster[c.geoid];
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${c.point}&layers=county`);
      const info = await cardText(page, "county");
      const text = info.text || "";
      const shown = plain(text);
      const got = await page.evaluate((cid) => {
        const el = document.getElementById("card-" + cid);
        const block = el && el.closest(".layer-block");
        return {
          all: el ? el.textContent.replace(/\s+/g, " ") : "",
          mailto: el ? Array.from(el.querySelectorAll("a[href^='mailto:']"))
            .map((a) => decodeURIComponent(a.getAttribute("href").slice(7)).toLowerCase()) : [],
          officeMail: el ? Array.from(el.querySelectorAll(".card-office a[href^='mailto:']"))
            .map((a) => decodeURIComponent(a.getAttribute("href").slice(7)).toLowerCase()) : [],
          footer: block ? Array.from(block.querySelectorAll(".card-footer a[href]")).map((a) => a.href) : [],
        };
      }, "county");
      const seats = (o && o.seats) || [];
      const officers = (o && o.officers) || [];
      const people = seats.concat(officers);
      const unnamed = seats.filter((s) => !text.includes(s.name)).map((s) => s.name)
        .concat(officers.filter((p) => !text.includes(p.name) || !text.includes(p.office)).map((p) => p.name));
      const unphoned = people.filter((p) => p.phone && !shown.includes(p.phone)).map((p) => p.name);
      const unmailed = people.filter((p) => p.email && !got.mailto.includes(String(p.email).toLowerCase())).map((p) => p.name);
      const officeOk = (o && (o.boardAddress || o.boardPhone || o.boardEmail))
        ? got.all.includes("The commission's office") && (!o.boardAddress || got.all.includes(o.boardAddress)) &&
            (!o.boardPhone || plain(got.all).includes(o.boardPhone)) &&
            (!o.boardEmail || got.officeMail.includes(o.boardEmail.toLowerCase()))
        : !/The commission's office/.test(got.all);
      const wantSeats = c.geoid === "54003" || c.geoid === "54037" ? 5 : 3;
      const whichOk = text.includes(`All ${seats.length} commissioners. Each is elected by the whole county`) &&
        text.includes("No two may live in the same magisterial district");
      const boeOk = /Board of education/i.test(text) && text.includes("is not named here yet");
      const creditOk = /Where these names come from/i.test(text) &&
        text.includes(`read on ${longDate(o && o.read)}`) && got.footer.includes(o && o.sourceUrl);
      check(`the County card in ${o ? o.county : c.geoid} names all ${wantSeats} commissioners and every other official the directory lists, with their own telephones and e-mail addresses and the directory's credit`,
        !!o && !info.error && text.includes(o.county) && seats.length === wantSeats && unnamed.length === 0 &&
          unphoned.length === 0 && unmailed.length === 0 && officeOk && whichOk && boeOk && creditOk,
        `seats=${seats.length} unnamed=${unnamed.slice(0, 3)} unphoned=${unphoned.slice(0, 2)} unmailed=${unmailed.slice(0, 2)} ` +
          `office=${officeOk} which=${whichOk} boe=${boeOk} credit=${creditOk} ${text.slice(0, 100)}`);
      await context.close();
    }
  }

  // 9b. The roster is refused, and the County card must degrade to a sentence
  //    naming nobody while the county itself still classifies: a roster
  //    failure is not the layer's failure.
  {
    const kanawha = shipped("wv-county-officials.json")["54039"];
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=county`, async (p) => {
      await p.route("**/data/app/wv-county-officials.json", (r) => r.fulfill({ status: 503, body: "down" }));
    });
    const info = await cardText(page, "county");
    const text = info.text || "";
    const named = (kanawha.seats || []).concat(kanawha.officers || [])
      .filter((p) => p && p.name && text.includes(p.name)).map((p) => p.name);
    check("the County card degrades to naming nobody when the list of officials fails",
      !info.error && /Kanawha County/.test(text) && /did not load, so no one is named here/.test(text) &&
        named.length === 0,
      `named=${named.slice(0, 2)} text=${text.slice(0, 90)}`);
    await context.close();
  }

  // 10. THE MAGISTERIAL DISTRICT LAYER, from the state's own map
  //     (data/app/wv-magisterial-districts.json). The district and its county
  //     are read from the shipped file at each point, so a rebuild moves the
  //     expectation; the card must name exactly that district, say that a
  //     magisterial district elects nobody and what the commission's rule is,
  //     and say where the line comes from. The Capitol, and the two counties
  //     with five commissioners, whose district counts are the largest.
  {
    const fc = shipped("wv-magisterial-districts.json");
    for (const pt of [POINT, "39.45844,-78.05805", "39.28956,-77.87265"]) {
      const at = propsAt(fc, pt);
      const p = at[0] || {};
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${pt}&layers=county,county-subdivision`);
      const info = await cardText(page, "county-subdivision");
      const text = info.text || "";
      const others = fc.features.map((f) => f.properties)
        .filter((q) => q.COUNTY === p.COUNTY && q.NAME !== p.NAME && new RegExp(`\\b${q.NAME.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`).test(text))
        .map((q) => q.NAME);
      check(`county-subdivision names the magisterial district the shipped map puts at ${pt} (${p.NAME || "?"}, ${p.COUNTY || "?"})`,
        at.length === 1 && !info.error && text.includes(p.NAME) && text.includes(p.COUNTY) &&
          others.length === 0 && /elects nobody of its own/.test(text) &&
          /no two county commissioners may live in the same/.test(text) &&
          /West Virginia GIS Technical Center/.test(text),
        `districts here=${at.length} others=${others} ${text.slice(0, 120)}`);
      await context.close();
    }
  }
} finally {
  await browser.close();
}

if (failures.length) {
  console.error(`\n${failures.length} smoke check(s) failed: ${failures.join(", ")}`);
  process.exit(1);
}
