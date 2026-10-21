// Headless boot + behaviour smoke test, run in CI on every pull request
// (.github/workflows/smoke-test.yml). Serves the real index.html and drives it
// in Chromium via Playwright — the check the README's "Validation" section
// describes and that OPTIMIZATION_PLAYBOOK item 5 asked to actually commit.
//
// It deliberately depends only on the app shell (Leaflet from its CDN) and the
// same-origin data/app/*.json files — never on the live district APIs, which
// are flaky/blocked in CI. The same-origin anchors (Parish, U.S. House, the
// two chambers, the voting precinct and the three courts elected by district)
// are the deterministic ground truth, and every live service a check needs is
// stubbed.
//
// Run locally against a static server:
//     python3 -m http.server 8000 &
//     npm install playwright && BASE_URL=http://localhost:8000/la/ node la/scripts/smoke_test.mjs
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
const POINT = "29.95240,-90.07670"; // New Orleans City Hall, 1300 Perdido Street, Orleans Parish
const OFFLINE = ["county", "us-house", "la-senate", "la-house", "voting-precinct", "la-supreme-court", "la-court-of-appeal", "la-district-court"];
const EXPECT_DISTRICT = { "county": "Orleans Parish", "us-house": "2", "la-senate": "5", "la-house": "93", "voting-precinct": "Precinct 3-1", "la-supreme-court": "7", "la-court-of-appeal": "Fourth Circuit, District 1", "la-district-court": "Civil District Court and Criminal District Court" };
const NEGATIVE_POINT = "28.60000,-90.50000"; // open water about 50 km south of the Louisiana coast, past the state's offshore line — outside Louisiana and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-20: TIGERweb's state and county layers name no state or parish here, its legislative layers no district, and its ZIP layer no ZIP code (control: New Orleans City Hall returns Louisiana, Orleans Parish and 70112). OPEN WATER BECAUSE A POINT ON A NEIGHBOUR'S LAND WOULD HAVE TO MOVE: Arkansas and Mississippi are live already, and the fleet is meant to reach every state, Texas included.
const APP_NAME = "districtry Louisiana";
const EXPECT_LAYERS = 17;
// ==== GENERATED:END smoke-config ====
// Instance constants this file owns (the worksheet emits the block above).
const EXPORTS_NAME = "LouisianaExplorer";
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
  geometry: { type: "Point", coordinates: [-90.07670, 29.95240] },
  properties: {
    // the typed number: an answer without it shows the street instead of
    // a row (ENGINE geocoder-search runAddressSearch)
    housenumber: "16",
    street: "W Jones St",
    city: "Capital City",
    state: "Louisiana",
    postcode: "00000"
  }
};
// Contract stubs (their consuming checks are reference-fork scenarios,
// dropped from this instance's body):
const GAP_PROBE = { county: "statewide", label: "Statewide", lat: 29.95240, lng: -90.07670 };
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
  //     LOUISIANA HAS THREE NEIGHBOURS, AND THE FLEET SERVES TWO OF THEM.
  //     Mississippi is live, so a click at its State Capitol in Jackson must
  //     open that app: measured against fleet-outlines.json on 2026-10-20 it
  //     lies inside Mississippi's outline and no other, about 77 km from this
  //     app's coverage ring. Arkansas is live, so a click on El Dorado must
  //     open THAT app: it is about 21 km north of the state line, inside
  //     Arkansas's outline and no other. This instance answers its own side
  //     from the coverage ring the wash retained, with no fetch, and since
  //     go-live the fleet file carries this app's own outline too, which is
  //     asked first, so a point both draw stays here. Chicago proves the file
  //     is still read for ground far from here.
  //
  //     TEXAS IS DELIBERATELY NOT A CASE. Nobody serves it today, so a click
  //     there stays here; but the fleet is meant to reach every state, and a
  //     "stays here" case in Texas would start failing the day it goes live,
  //     in a change that is about another state. The offshore negative point
  //     carries that half instead (1a2-ii).
  {
    const cases = [
      { name: "Chicago", lat: 41.8825, lng: -87.6285, want: "https://districtry.com/il/" },
      { name: "Jackson, Mississippi", lat: 32.3038, lng: -90.1822, want: "https://districtry.com/ms/" },
      { name: "El Dorado, Arkansas", lat: 33.2076, lng: -92.6663, want: "https://districtry.com/ar/" },
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
      check(`a click on ${c.name} from Louisiana opens ${c.want} with the point`, !!went, went || page.url());
      await context.close();
    }
  }

  // 1a2-ii. The half that keeps 1a2 honest: the negative point, in open water
  //     about 50 km south of the Louisiana coast, is outside every outline in
  //     the fleet, so the click must stay HERE. A route to a sibling would be
  //     the same lie pointing the other way, and the stub makes it visible: if
  //     the app navigated, the URL would be the stubbed sibling rather than
  //     this app.
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
    check("a click offshore, outside every app's outline, stays in this app",
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
      .waitForFunction(() => document.querySelectorAll("#geocode-results li").length > 0,
        null, { timeout: QUERY_TIMEOUT })
      .catch(() => {});
    const rows = await page.$$eval("#geocode-results li", (ls) => ls.length);
    const bounded = seen.filter((c) => c.bounded);
    check("search box retries a unit-fragment miss with the cleaned address",
      bounded.length === 2 && bounded[0].q.includes(GEOCODER_UNIT_FRAGMENT) && bounded[1].q === GEOCODER_QUERY_CLEANED && rows > 0,
      `calls=${JSON.stringify(bounded.map((c) => c.q))} rows=${rows}`);

    seen.length = 0;
    await search("nowhere at all xyzzy");
    await page.waitForTimeout(2000);
    check("a query with nothing to clean is not retried",
      seen.filter((c) => c.bounded).length === 1,
      `bounded=${seen.filter((c) => c.bounded).length} total=${seen.length}`);

    await context.close();
  }

  // 2. The same-origin anchors classify a known point against known
  //    ground truth, fetched from data/app/*.json. Two expected-value shapes:
  //    a NUMERIC expectation asserts the card's own "District N" token exactly
  //    (never a stray digit elsewhere in the card); a NAME expectation (the
  //    Parish anchor, whose card prints an identity rather than a number)
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
    // 2a. EACH CHAMBER'S OWN PAGES NAME THE MEMBER, and the card carries what
    //     they print: the name, the party, the district office and the
    //     chamber's own e-mail address, which must open as a mailto link. The
    //     values expected are read from the shipped roster for each chamber's
    //     anchor district, so a weekly refresh that changes them changes what
    //     is expected. The office sits behind a closed disclosure, which
    //     innerText leaves out, so the office is read from textContent.
    for (const [id, file] of [["la-senate", "la-senate-members.json"], ["la-house", "la-house-members.json"]]) {
      const rec = shipped(file)[EXPECT_DISTRICT[id]] || {};
      const info = await cardText(page, id);
      const got = await page.evaluate((cid) => {
        const el = document.getElementById("card-" + cid);
        return {
          all: el ? el.textContent.replace(/\s+/g, " ") : "",
          mailto: el ? Array.from(el.querySelectorAll("a[href^='mailto:']")).map((a) => a.getAttribute("href")) : [],
        };
      }, id);
      const street = (rec.districtOffice || [])[0] || null;
      const mailOk = !!rec.email && got.mailto.some((h) =>
        decodeURIComponent(h.slice(7)).toLowerCase() === String(rec.email).toLowerCase());
      check(`${id} card names the member, the party, the district office and the chamber e-mail its own pages print`,
        !info.error && !!rec.name && info.text.includes(rec.name) &&
          !!rec.party && info.text.toLowerCase().includes(String(rec.party).toLowerCase()) &&
          !!street && got.all.includes(street) && mailOk,
        `name=${rec.name} street=${street} mailto=${JSON.stringify(got.mailto)} ${info.text.slice(0, 80)}`);
    }
    await context.close();
  }

  // 2a2. A SEAT THE CHAMBER LISTS AS VACANT SAYS SO, in the chamber's words,
  //     and names nobody. Senate District 14 read vacant on 2026-10-20; the
  //     point is the shipped district's pole of inaccessibility (shapely
  //     polylabel), about 3.8 km from its nearest edge. Where a later refresh
  //     seats a senator there, the check asserts that senator is named
  //     instead, so a filled seat passes and a wrong name still fails.
  {
    const SD14 = "30.47794,-91.16278";
    const rec = shipped("la-senate-members.json")["14"] || {};
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${SD14}&layers=la-senate`);
    const info = await cardText(page, "la-senate");
    const text = info.text || "";
    const others = Object.entries(shipped("la-senate-members.json"))
      .filter(([d, r]) => d !== "14" && r.name && text.includes(r.name)).map(([, r]) => r.name);
    const ok = rec.vacant
      ? /\bVacant\b/.test(text) && !!rec.vacantWhy && text.includes(rec.vacantWhy)
      : !!rec.name && text.includes(rec.name);
    check(rec.vacant
        ? "la-senate says District 14 is vacant, in the chamber's own words, and names nobody"
        : "la-senate names District 14's senator now that the chamber lists one",
      !info.error && /District 14\b/.test(text) && ok && others.length === 0,
      `vacant=${!!rec.vacant} others=${others.slice(0, 2)} ${text.slice(0, 140)}`);
    await context.close();
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
  //    fire-station is 1,675 points in Louisiana's envelope (measured
  //    2026-10-20), within 325 of a 2,000-record cap the service reports as
  //    HTTP 200 + exceededTransferLimit rather than an error, so the day the
  //    count passes the cap a single request drops real stations and the
  //    nearest-3 card looks correct at every point. The source manifest's
  //    count row cannot see that, because returnCountOnly is not subject to
  //    maxRecordCount and answers the true count whatever the client does.
  //    This is the check that can.
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
      attributes: { NAME: `FAR STATION ${i}`, ADDRESS: "1 Far Rd", CITY: "Monroe", STATE: "LA", ZIPCODE: "71201" },
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
                              CITY: "New Orleans", STATE: "LA", ZIPCODE: "70112" },
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
      /New Orleans, LA/.test(text), text.slice(0, 140));
    await context.close();
  }

  // 7. THE LIVE TIGERWEB FABRIC CARDS, STUBBED — and stubbed on purpose rather
  //    than anchored. The worksheet's OFFLINE anchors are same-origin only,
  //    which is this test's own stated contract, and these layers fetch the
  //    Census live: asserting a card against somebody else's server makes the
  //    test fail on their outage and on any network that intercepts TLS.
  //
  //    SINCE 2026-10-21 THESE LAYERS ARE ANSWERED FROM SAME-ORIGIN TILE
  //    ARCHIVES (scripts/mirror_tiger_tiles.py), and the stubs stay anyway:
  //    several cases below exist in no archive (an affix no table carries, a
  //    roster refused), so each case refuses its layer's archive and the stub
  //    decides the card, through the archive-failure path il's smoke check 2d
  //    also holds.
  //
  //    WHAT IS WORTH TESTING IS THIS INSTANCE'S OWN CODE, and none of it is
  //    exercised by a live fetch that happens to work. Four claims, each wrong
  //    in a way a reader would see:
  //
  //    (a) The municipality card states the style the Census records — a
  //        CITY, a TOWN or a VILLAGE, Louisiana's three — and an affix the
  //        card does not know produces NO type row rather than an improvised
  //        one.
  //    (b) A status row appears only for the two statuses other than active
  //        that Louisiana's places carry, measured 2026-10-20 across all 305:
  //        FUNCSTAT B (Baton Rouge and Lafayette) keeps its type row and
  //        points at the Parish card; FUNCSTAT N (Houma) drops the type row,
  //        because a place with no government of its own is not "a
  //        general-purpose local government over this point".
  //    (c) New Orleans, FUNCSTAT A like any city, is one government with
  //        Orleans Parish, so its card must not say "alongside the parish",
  //        and it says the Parish card names its mayor and council.
  //    (d) The one school tiling answers, under the label with no qualifier,
  //        because the unified districts cover the state alone.
  //    (e) A town's card and a school district's card agree with that place's
  //        record in the shipped roster (la-municipal-officials.json,
  //        la-school-board-members.json): the mayor, every member under the
  //        list's own word for them with their seat, every officer under the
  //        title the list gives, each telephone, the shared office, a seat the
  //        list skips, the list's credit and link, and which member represents
  //        the point said no further than the seats allow: a town whose list
  //        gives no seats is never said to elect at large, and a seat that is
  //        a lettered seat or a division is not said to cover any ground. The
  //        names are read from the files, because the Secretary of State's
  //        next edition changes them and a name written here would fail a
  //        correct rebuild. Shreveport (council districts), Ridgecrest (no
  //        seats), Napoleonville (a village), Chatham (which the list calls a
  //        village and the Census a town), Bernice (a district the list
  //        skips), Gonzales (divisions), Lafayette (FUNCSTAT B, a council and
  //        no mayor of its own), and Orleans and West Baton Rouge's school
  //        boards (district seats, and one member elected at large).
  //        A city whose council districts the City Council District layer
  //        draws (the cities in the shipped la-city-wards.json; Lafayette
  //        here) says that layer names the member, and Shreveport, whose
  //        districts are not drawn, says this app cannot say which district
  //        the point is in.
  //    (f) Either roster refused: the place still answers, naming nobody.
  {
    function esriPolygon(props) {
      return {
        attributes: props,
        geometry: { rings: [[[-90.6, 29.6], [-89.6, 29.6], [-89.6, 30.3], [-90.6, 30.3], [-90.6, 29.6]]] }
      };
    }
    function esriBody(props) {
      return JSON.stringify({
        geometryType: "esriGeometryPolygon",
        spatialReference: { wkid: 4326 },
        fields: Object.keys(props).map((n) => ({ name: n, type: "esriFieldTypeString", alias: n })),
        features: [esriPolygon(props)]
      });
    }
    const PLACES = "Places_CouSub_ConCity_SubMCD/MapServer/4";
    const SCHOOLS = "School/MapServer/0";
    const towns = shipped("la-municipal-officials.json");
    const boards = shipped("la-school-board-members.json");
    const WORDS = { aldermen: ["Aldermen", "alderman"], council: ["Council members", "council member"],
                    selectmen: ["Selectmen", "selectman"], trustees: ["Trustees", "trustee"] };
    const groundOf = (seats) => {
      let word = null;
      for (const p of seats) {
        const m = /^(Ward|District)\b/.exec(p.seat || "");
        if (!m || (word && m[1].toLowerCase() !== word)) return null;
        word = m[1].toLowerCase();
      }
      return word;
    };
    // The cities whose council districts the City Council District layer
    // draws, read from the shipped file, so the City card's sentence about
    // which member represents the point is held to what is drawn.
    const wardCities = new Set(shipped("la-city-wards.json").features.map((f) => String(f.properties.geoid)));
    // Every way the card can disagree with the place's record, as a list of
    // short labels; empty means it agrees. `drawn` is whether the City Council
    // District layer draws the place's districts.
    function disagreements(o, text, footer, board, drawn) {
      const out = [];
      const shown = plain(text);
      const named = (list) => (list || []).filter((p) => p && p.name);
      const atLarge = named(o.atLarge), seats = named(o.seats), members = named(o.members);
      const people = atLarge.concat(seats, members);
      const mayor = o.mayor && o.mayor.name ? o.mayor : null;
      const officers = named(o.officers);
      const everyone = people.concat(mayor ? [mayor] : [], officers);
      const unnamed = everyone.filter((p) => !text.includes(p.name)).map((p) => p.name);
      if (unnamed.length) out.push(`unnamed=${unnamed.slice(0, 3)}`);
      const unseated = people.filter((p) => p.seat && !text.includes(p.seat)).map((p) => p.seat);
      if (unseated.length) out.push(`seats=${unseated.slice(0, 3)}`);
      const unphoned = everyone.filter((p) => p.phone && !shown.includes(p.phone)).map((p) => p.name);
      if (unphoned.length) out.push(`unphoned=${unphoned.slice(0, 3)}`);
      // section labels are set in capitals, which innerText reports
      const has = (words) => text.toLowerCase().includes(String(words).toLowerCase());
      const head = board ? "School board" : (WORDS[o.kind] || ["Members"])[0];
      if (!people.length || !has(head)) out.push(`heading=${head}`);
      for (const p of officers) if (!has(p.title)) out.push(`title=${p.title}`);
      if (!board && (mayor ? !has("Mayor") : !/names no mayor for this/.test(text))) out.push("mayor");
      const office = /The [a-z ]+'s office/.test(text);
      const hasOffice = !!(o.officeAddress || o.officePhone);
      if (hasOffice !== office || (o.officeAddress && !text.includes(o.officeAddress)) ||
          (o.officePhone && !shown.includes(o.officePhone))) out.push("office");
      const unlisted = o.unlisted || [];
      if (unlisted.some((u) => !text.includes(u)) ||
          (unlisted.length > 0) !== /names no one for/.test(text) ||
          (unlisted.length && !/does not say the seat is vacant, so this card does not either/.test(text))) out.push("unlisted");
      if (atLarge.length ? !/elected at large represents? the whole/.test(text)
                         : /at large/i.test(text)) out.push("at large");
      const ground = groundOf(seats);
      const one = (WORDS[o.kind] || [null, "member"])[1];
      const namedHere = board ? text.includes(`does not draw the school board's ${ground}s`)
        : drawn ? new RegExp(`The City Council District layer draws the (city|town|village)'s ${ground}s ` +
                             `and names that ${one}\\.`).test(text) && !/cannot say which/.test(text)
        : text.includes(`${ground}s, so it cannot say which ${ground} that is`);
      if (seats.length && !(ground
            ? text.includes(`elected from the ${ground} this point is in represents it`) && namedHere
            : text.includes("but not the ground each seat covers"))) out.push("which");
      if (drawn && !ground) out.push("drawn, with no ground");
      if (!ground && /this point is in represents it/.test(text)) out.push("claims ground");
      if (members.length && !text.includes("without a ward or district")) out.push("plain");
      // one shared date names it, whether or not that day has passed
      const terms = [...new Set(people.map((p) => p.termEnds))];
      if (terms.length === 1 && terms[0] &&
          !text.includes(`The list gives every member's term as ending on ${longDate(terms[0])}`)) out.push("term");
      if (!/Where (these names come|the name comes) from/.test(text) ||
          !text.includes(`read on ${longDate(o.read)}`)) out.push("credit");
      if (!footer.includes(o.sourceUrl)) out.push("link");
      return out;
    }
    const cases = [
      {
        name: "a city names itself a city, alongside the parish, with its mayor and its council by district",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2270000", NAME: "Shreveport city", BASENAME: "Shreveport", STATE: "22", LSADC: "25", FUNCSTAT: "A" },
        town: true,
        want: [/Shreveport city/, /Incorporated city — a general-purpose local government over this point, alongside the parish/],
        reject: [/Status/, /Incorporated town/, /Incorporated village/, /Parish card names/, /Not named here/, /names no officials/]
      },
      {
        name: "a town names itself a town, not a city, and its aldermen without calling them elected at large",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2264765", NAME: "Ridgecrest town", BASENAME: "Ridgecrest", STATE: "22", LSADC: "43", FUNCSTAT: "A" },
        town: true,
        want: [/Ridgecrest town/, /Incorporated town/],
        reject: [/Incorporated city/, /Incorporated village/, /Its name in the list/]
      },
      {
        name: "a village names itself a village",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2253370", NAME: "Napoleonville village", BASENAME: "Napoleonville", STATE: "22", LSADC: "47", FUNCSTAT: "A" },
        town: true,
        want: [/Napoleonville village/, /Incorporated village/],
        reject: [/Incorporated city/, /Incorporated town/]
      },
      {
        name: "a place the list styles differently from the Census says what the list calls it",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2214485", NAME: "Chatham town", BASENAME: "Chatham", STATE: "22", LSADC: "43", FUNCSTAT: "A" },
        town: true,
        want: [/Chatham town/, /Incorporated town/, /The Secretary of State's list calls it the Village of Chatham\./],
        reject: [/Incorporated village/]
      },
      {
        name: "a district the list skips is named as skipped, not vacant",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2207030", NAME: "Bernice town", BASENAME: "Bernice", STATE: "22", LSADC: "43", FUNCSTAT: "A" },
        town: true,
        want: [/Bernice town/],
        reject: [/vacant\b(?!, so)/]
      },
      {
        name: "a council elected by divisions is not said to cover any ground",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2229850", NAME: "Gonzales city", BASENAME: "Gonzales", STATE: "22", LSADC: "25", FUNCSTAT: "A" },
        town: true,
        want: [/Gonzales city/],
        reject: []
      },
      {
        name: "an affix the card does not carry prints NO type row, and no improvised word for the place",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2299999", NAME: "Nowhere borough", BASENAME: "Nowhere", STATE: "22", LSADC: "21", FUNCSTAT: "A" },
        want: [/Nowhere borough/, /names no officials for this place, so no one is named here/],
        reject: [/Incorporated city/, /Incorporated town/, /Incorporated village/, /this borough/]
      },
      {
        name: "a FUNCSTAT B city with a council of its own names the council and points at the Parish card for its executive",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2240735", NAME: "Lafayette city", BASENAME: "Lafayette", STATE: "22", LSADC: "25", FUNCSTAT: "B" },
        town: true,
        want: [/Lafayette city/, /Incorporated city/, /partly consolidated with another government/,
               /names no mayor for this city on its own/,
               /The Parish card names the parish's governing body and its executive/],
        reject: [/no government of its own/]
      },
      {
        name: "a FUNCSTAT B city keeps its type, says what the Census records, and points at the Parish card",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2205000", NAME: "Baton Rouge city", BASENAME: "Baton Rouge", STATE: "22", LSADC: "25", FUNCSTAT: "B" },
        want: [/Baton Rouge city/, /Incorporated city/, /partly consolidated with another government/,
               /The Parish card names the parish's governing body and its executive/],
        reject: [/no government of its own/]
      },
      {
        name: "a FUNCSTAT N city drops its type row, says it has no government of its own, and points at the Parish card",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2236255", NAME: "Houma city", BASENAME: "Houma", STATE: "22", LSADC: "25", FUNCSTAT: "N" },
        want: [/Houma city/, /no government of its own operating/,
               /The Parish card names the parish's governing body and its executive/],
        reject: [/Incorporated city/, /partly consolidated/]
      },
      {
        name: "New Orleans says it is one government with Orleans Parish, never alongside it, and that the Parish card names its mayor and council",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2255000", NAME: "New Orleans city", BASENAME: "New Orleans", STATE: "22", LSADC: "25", FUNCSTAT: "A" },
        want: [/New Orleans city/, /New Orleans and Orleans Parish are one government/,
               /The Parish card names them/, /New Orleans City Council as Orleans Parish's governing body/],
        reject: [/alongside the parish/, /Not named here/, /Status/]
      },
      {
        name: "the school district card names the district and its whole board by district",
        layer: "school-district-unified", service: SCHOOLS,
        props: { GEOID: "2201170", NAME: "Orleans Parish School District", STATE: "22" },
        board: true,
        want: [/Orleans Parish School District/],
        reject: [/Unified/]
      },
      {
        name: "a school board with a member elected at large names that member and the district members",
        layer: "school-district-unified", service: SCHOOLS,
        props: { GEOID: "2201920", NAME: "West Baton Rouge Parish School District", STATE: "22" },
        board: true,
        want: [/West Baton Rouge Parish School District/],
        reject: []
      },
      {
        name: "the town card still names the place, and names nobody, when the list of mayors and councils fails",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2270000", NAME: "Shreveport city", BASENAME: "Shreveport", STATE: "22", LSADC: "25", FUNCSTAT: "A" },
        refuse: "la-municipal-officials.json",
        want: [/Shreveport city/, /Incorporated city/, /The list of mayors and councils did not load, so no one is named here/],
        reject: [/^MAYOR$/m]
      },
      {
        name: "the school district card still names the district, and names nobody, when the list of board members fails",
        layer: "school-district-unified", service: SCHOOLS,
        props: { GEOID: "2201170", NAME: "Orleans Parish School District", STATE: "22" },
        refuse: "la-school-board-members.json",
        want: [/Orleans Parish School District/, /The list of school board members did not load, so no one is named here/],
        reject: []
      }
    ];

    const footerLinks = (page, id) => page.evaluate((cid) => {
      const el = document.getElementById("card-" + cid);
      const block = el && el.closest(".layer-block");
      return block ? Array.from(block.querySelectorAll(".card-footer a[href]")).map((a) => a.href) : [];
    }, id);
    for (const c of cases) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=${c.layer}`, async (p) => {
        await p.route(`**/data/app/tiles/${c.layer}.pmtiles`, (r) => r.abort());
        await p.route(`**/${c.service}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: esriBody(c.props) }));
        if (c.refuse) await p.route(`**/data/app/${c.refuse}`, (r) => r.fulfill({ status: 503, body: "down" }));
      });
      const info = await cardText(page, c.layer);
      const text = info.text || "";
      const missing = c.want.filter((re) => !re.test(text));
      const present = c.reject.filter((re) => re.test(text));
      const record = c.town ? towns[c.props.GEOID] : c.board ? boards[c.props.GEOID] : null;
      const off = (c.town || c.board)
        ? (record ? disagreements(record, text, await footerLinks(page, c.layer), !!c.board,
                                  c.layer === "municipality" && wardCities.has(c.props.GEOID))
                   : ["no record in the shipped roster"])
        : [];
      // a refused roster names nobody the shipped one would
      const leaked = c.refuse
        ? (() => {
            const o = (c.layer === "municipality" ? towns : boards)[c.props.GEOID] || {};
            return [o.mayor].concat(o.atLarge || [], o.seats || [], o.members || [], o.officers || [])
              .filter((p) => p && p.name && text.includes(p.name)).map((p) => p.name);
          })()
        : [];
      check(c.name, !info.error && missing.length === 0 && present.length === 0 && off.length === 0 && leaked.length === 0,
        missing.length || present.length || off.length || leaked.length
          ? `missing=${missing} unwanted=${present} disagrees=${off} named=${leaked.slice(0, 2)} text=${text.slice(0, 160)}`
          : text.slice(0, 90));
      await context.close();
    }
  }

  // 8. THE ZIP LAYER IS IN-STATE ONLY, AND THIS IS THE CHECK THAT PROVES IT.
  //    A ZCTA carries no STATE field, so this is the one layer here whose
  //    point query cannot be filtered server-side — and over a land border it
  //    does not answer with nothing, it answers with a real neighbouring ZIP.
  //    Measured against the live service 2026-10-20: Orange, Texas gives
  //    77630 and Vicksburg, Mississippi 39183.
  //
  //    THE OUT-OF-STATE HALF IS THE ONE THAT DISCRIMINATES. The stub answers
  //    77630 whatever point is asked, so a regression that drops `coverage`
  //    shows the block AND renders a Texas ZIP here, which is the harm a
  //    reader would see; the live service answers no ZCTA at this offshore
  //    point, so without the stub that regression would show only an empty
  //    card. The in-state half is equally load-bearing: coverage fails OPEN,
  //    so a test that only asserted hiding would also pass on a layer that
  //    had stopped working altogether.
  //
  //    The negative point is the worksheet's own, offshore and outside the
  //    state outline, which is what the coverage test reads. A point in Texas
  //    would test the same thing and start failing the day a Texas app goes
  //    live and a selection there leaves for it.
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
          geometry: { rings: [[[-91, 28.4], [-89.8, 28.4], [-89.8, 30.2], [-91, 30.2], [-91, 28.4]]] }
        }]
      });
    }

    // in state: the layer answers, and answers from the stub
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=zip-code`, async (p) => {
        // the layer is answered from a tile archive since 2026-10-21; refusing it
        // sends the card to the census loader, which this stub answers
        await p.route("**/data/app/tiles/zip-code.pmtiles", (r) => r.abort());
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("70112") }));
      });
      const info = await cardText(page, "zip-code");
      check("zip-code answers inside Louisiana (coverage fails open, so this half matters)",
        !info.error && /70112/.test(info.text || ""),
        (info.text || "").slice(0, 90));
      await context.close();
    }

    // out of state: the layer HIDES, and the stubbed ZIP never renders
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${NEGATIVE_POINT}&layers=zip-code`, async (p) => {
        await p.route("**/data/app/tiles/zip-code.pmtiles", (r) => r.abort());
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("77630") }));
      });
      const hidden = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-zip-code");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === true;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const info = await cardText(page, "zip-code");
      const leaked = /77630/.test(info.text || "");
      const stillOn = await page.evaluate(
        (n) => window[n].state.layersOn["zip-code"] === true, EXPORTS_NAME);
      check("zip-code hides outside Louisiana rather than naming a Texas ZIP",
        hidden && !leaked && stillOn,
        `hidden=${hidden} leaked=${leaked} layersOn=${stillOn} text=${(info.text || "").slice(0, 90)}`);
      await context.close();
    }
  }

  // 9. EVERY PARISH'S GOVERNING BODY, on the Parish card. The names expected
  //    are read from the shipped roster (data/app/la-parish-officials.json)
  //    rather than written here, because the Secretary of State's next
  //    edition of its list changes them and a name in this file would fail a
  //    correct rebuild. Six parishes, each for its own claim:
  //      - Orleans, at City Hall: the Mayor first, then the New Orleans City
  //        Council with its two members elected at large and its five
  //        district members, the one term every one of them shares, which
  //        member represents the point, and the credit and link to the list;
  //      - Avoyelles, a police jury whose District 4 the list leaves out: the
  //        card says the list names no one for it and does not call it
  //        vacant, says the list does not record the jury's president, and
  //        shows the office three or more members share;
  //      - Cameron, whose District 4 elects two jurors: both are listed;
  //      - Caddo, the one parish commission, with its shared office;
  //      - East Baton Rouge, a Mayor-President and the Metropolitan Council,
  //        whose seats the list calls Metro Districts;
  //      - Assumption, whose seats are wards: the card's sentence about which
  //        member represents the point says ward.
  //    Each person the list prints a telephone for shows it, since Adam's
  //    ruling of 2026-10-17. The points are poles of inaccessibility of each
  //    parish as the shipped file draws it (shapely polylabel, 2026-10-20),
  //    13 to 24 km from the nearest parish line, and Assumption's is the one
  //    check 10 uses for its Ward 4.
  {
    const roster = shipped("la-parish-officials.json");
    const cases = [
      { point: POINT, geoid: "22071" },
      { point: "31.03895,-92.02714", geoid: "22009" },
      { point: "29.82600,-92.82737", geoid: "22023" },
      { point: "32.45376,-93.89207", geoid: "22017" },
      { point: "30.59069,-91.10618", geoid: "22033" },
      { point: "29.84237,-91.03153", geoid: "22007" },
    ];
    const footerLinks = (page, id) => page.evaluate((cid) => {
      const el = document.getElementById("card-" + cid);
      const block = el && el.closest(".layer-block");
      return block ? Array.from(block.querySelectorAll(".card-footer a[href]")).map((a) => a.href) : [];
    }, id);
    for (const c of cases) {
      const o = roster[c.geoid];
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${c.point}&layers=county`);
      const info = await cardText(page, "county");
      const text = info.text || "";
      const shown = plain(text);
      const people = (o.atLarge || []).concat(o.seats || []);
      const unnamed = people.filter((p) => !text.includes(p.name) || !text.includes(p.seat)).map((p) => p.name);
      const unphoned = people.concat(o.executive ? [o.executive] : [])
        .filter((p) => p.phone && !shown.includes(p.phone)).map((p) => p.name);
      const exe = o.executive;
      const exeOk = exe ? text.includes(exe.name) && new RegExp(exe.title, "i").test(text) : true;
      const terms = [...new Set(people.map((p) => p.termEnds))];
      const termOk = terms.length === 1 && terms[0]
        ? text.includes(`The list gives every member's term as ending on ${longDate(terms[0])}`)
        : !/The list gives every member's term/.test(text);
      const office = /The (police jury|council|commission)'s office/i.test(text);
      const officeOk = (o.boardAddress || o.boardPhone)
        ? office && (!o.boardAddress || text.includes(o.boardAddress))
        : !office;
      const word = (o.seats || []).every((s) => /^Ward\b/.test(s.seat)) ? "ward" : "district";
      const whichOk = (o.atLarge || []).length
        ? /elected at large represents? the whole parish/.test(text) &&
            text.includes(`the one elected from the ${word} this point is in does`)
        : text.includes(`The member elected from the ${word} this point is in.`);
      const juryOk = o.kind === "police-jury"
        ? /A police jury elects its own president from among its members/.test(text)
        : !/police jury elects its own president/.test(text);
      const unlisted = o.unlisted || [];
      const unlistedOk = unlisted.length
        ? unlisted.every((s) => text.includes(s)) && /names no one for/.test(text) &&
            /does not say the seat is vacant, so this card does not either/.test(text)
        : !/names no one for/.test(text);
      const footer = await footerLinks(page, "county");
      const creditOk = /Where these names come from/i.test(text) &&
        text.includes(`read on ${longDate(o.read)}`) && footer.includes(o.sourceUrl);
      check(`the Parish card in ${o.parish} names ${exe ? "its " + exe.title + " and " : ""}every member of the ${o.body} by seat, with the list's own credit`,
        !info.error && text.includes(o.parish) && people.length > 0 && unnamed.length === 0 &&
          exeOk && termOk && officeOk && whichOk && juryOk && unlistedOk && creditOk &&
          unphoned.length === 0,
        `unnamed=${unnamed.slice(0, 3)} unphoned=${unphoned.slice(0, 2)} exe=${exeOk} term=${termOk} office=${officeOk} ` +
          `which=${whichOk} jury=${juryOk} unlisted=${unlistedOk} credit=${creditOk} ${text.slice(0, 100)}`);
      await context.close();
    }
  }

  // 9b. The roster is refused, and the Parish card must degrade to a sentence
  //    naming nobody while the parish itself still classifies: a roster
  //    failure is not the layer's failure.
  {
    const orleans = shipped("la-parish-officials.json")["22071"];
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=county`, async (p) => {
      await p.route("**/data/app/la-parish-officials.json", (r) => r.fulfill({ status: 503, body: "down" }));
    });
    const info = await cardText(page, "county");
    const text = info.text || "";
    const named = [orleans.executive].concat(orleans.atLarge || [], orleans.seats || [])
      .filter((p) => p && p.name && text.includes(p.name)).map((p) => p.name);
    check("the Parish card degrades to naming nobody when the list of officials fails",
      !info.error && /Orleans Parish/.test(text) && /did not load, so no one is named here/.test(text) &&
        named.length === 0,
      `named=${named.slice(0, 2)} text=${text.slice(0, 90)}`);
    await context.close();
  }

  // 10. THE POLICE JURY OR COUNCIL DISTRICT LAYER, drawn only in the parishes
  //     whose current lines are confirmed (Adam's ruling of 2026-10-20,
  //     "Confirmed only"). The district, parish, body and member expected are
  //     read from the shipped files at the point, so a rebuild that renumbers
  //     a parish moves the expectation with it; what is asserted is that the
  //     card agrees with those files.
  //       - Caddo District 1 (the commission), Assumption Ward 4 (a police
  //         jury whose seats are wards) and St. Charles District 4 (a council
  //         with two members elected at large): each card names the district
  //         in the parish's own word, its member, the at-large members where
  //         there are any, the body, where the line comes from (the Census's
  //         January 1, 2026 edition, which the build checked) and where the
  //         names come from.
  //       - New Orleans City Hall, in the New Orleans City Council's District
  //         B, and the State Capitol, in East Baton Rouge's Metro District 10:
  //         these two parishes are drawn from their own government's map
  //         (since 2026-10-21), so each card says whose map the line is,
  //         never the Census edition, and links that government's page for
  //         its districts. Measured 2026-10-21 against each government's own
  //         layer: New Orleans's answered B at City Hall and C at a point in
  //         Algiers; the City-Parish's answered 10 at the Capitol and 2 and 9
  //         at points in the parish's north and south-east.
  //       - A point in Jefferson Parish, which is not drawn: the layer HIDES,
  //         with the layers= permalink intact. This is the half that
  //         discriminates: without `coverage` the card would say no district
  //         is drawn here, about a parish with five.
  //       - A point in Lake Pontchartrain inside Orleans Parish, where the
  //         city's map draws no district (its own layer answered none there on
  //         2026-10-21, and TIGER's areal hydrography names the lake there and
  //         no water at City Hall): the layer shows, and the card says the
  //         parish's own map leaves out some of its water.
  //       - With the layer OFF at the Caddo parish point, the coverage test
  //         reads the list of drawn parishes and never the districts file,
  //         which every reader would otherwise download on a first selection,
  //         and the layer's toggle still shows there.
  //       - The roster is refused: the district still answers and names nobody.
  //       - A seat the list leaves out, on a stubbed roster because no drawn
  //         parish has one on 2026-10-20: the card says the list names no one
  //         for it and calls nothing vacant.
  //       - Two members from one district, Cameron's shape, on a stubbed
  //         roster for the same reason: the card names both.
  //     The three Census-lined points are each district's pole of
  //     inaccessibility as the shipped file draws it (shapely polylabel,
  //     2026-10-20), 5 to 13 km from its nearest line; City Hall is 520 m
  //     inside District B and the Capitol 845 m inside Metro District 10 as
  //     the shipped file draws them (2026-10-21).
  {
    const districts = shipped("la-parish-districts.json");
    const roster = shipped("la-parish-officials.json");
    const counties = shipped("state-counties.json");
    const drawnParishes = shipped("la-parish-district-parishes.json");
    // the app's own word for a seat: "Ward 4", "Metro District 10", "District B"
    const seatName = (p) => `${p.label === "Ward" || p.label === "Metro District" ? p.label : "District"} ${p.district}`;
    const seatOf = (p) => (((roster[p.parishfips] || {}).seats) || []).filter((s) => s.seat === seatName(p));
    const CAPITOL = "30.45710,-91.18740";  // the Louisiana State Capitol, East Baton Rouge Parish
    const drawnPoints = ["32.83961,-93.92869", "29.84237,-91.03153", "29.77359,-90.28081", POINT, CAPITOL];  // Caddo 1, Assumption Ward 4, St. Charles 4, Orleans B, East Baton Rouge Metro 10
    const CADDO_PARISH = "32.45376,-93.89207";  // the Caddo point check 9 uses, in District 12
    const JEFFERSON = "29.98410,-90.15290";  // in Jefferson Parish on the shipped parish outlines, 2.8 km from Orleans's nearest drawn district
    const ORLEANS_LAKE = "30.10000,-90.10000";  // Lake Pontchartrain, inside Orleans Parish's outline, 7.8 km from its nearest drawn district
    const hrefs = (page, id) => page.evaluate((cid) => {
      const el = document.getElementById("card-" + cid);
      return el ? Array.from(el.querySelectorAll("a[href]")).map((a) => a.href) : [];
    }, id);
    const blockHidden = (page, id, want) => page
      .waitForFunction(([cid, w]) => {
        const box = document.getElementById("toggle-" + cid);
        const block = box && box.closest(".layer-block");
        return block && block.hidden === w;
      }, [id, want], { timeout: QUERY_TIMEOUT })
      .then(() => true, () => false);

    for (const pt of drawnPoints) {
      const at = propsAt(districts, pt);
      const p = at[0] || {};
      const seats = seatOf(p);
      const o = roster[p.parishfips] || {};
      const atLarge = o.atLarge || [];
      const name = seatName(p);
      const own = p.lines === "own";
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${pt}&layers=parish-district`);
      const info = await cardText(page, "parish-district");
      const text = info.text || "";
      const links = await hrefs(page, "parish-district");
      const word = p.label === "Ward" ? "ward" : "district";
      check(`the parish-district card in ${p.parish || "a drawn parish"} names ${name}, its member${atLarge.length ? ", the members elected at large" : ""} and where the line and the names come from${own ? ", and links the parish government's page for its districts" : ""}`,
        at.length === 1 && seats.length === 1 && !info.error &&
          new RegExp(`\\b${name}\\b`).test(text) && text.includes(seats[0].name) &&
          atLarge.every((m) => text.includes(m.name)) &&
          (atLarge.length ? /Members elected at large/i.test(text) : !/Members elected at large/i.test(text)) &&
          text.includes(p.parish) && text.includes(p.body) &&
          /Where this line comes from/i.test(text) &&
          (own
            ? p.lines === "own" && !!p.source && text.includes(p.source + ".") &&
              !text.includes("January 1, 2026 edition") && !!p.sourceUrl && links.includes(p.sourceUrl) &&
              /The official page for these districts/.test(text)
            : p.lines === "census" && text.includes("January 1, 2026 edition") &&
              text.includes(`${word}s hold nearly equal numbers of people`) &&
              !/The official page for these districts/.test(text)) &&
          (atLarge.length ? /Where the names come from/i.test(text) : /Where the name comes from/i.test(text)),
        `districts here=${at.length} seats=${seats.length} lines=${p.lines} ${text.slice(0, 140)}`);
      await context.close();
    }

    {
      const parish = propsAt(counties, JEFFERSON)[0] || {};
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${JEFFERSON}&layers=parish-district`);
      const hidden = await blockHidden(page, "parish-district", true);
      const stillOn = await page.evaluate(
        (n) => window[n].state.layersOn["parish-district"] === true, EXPORTS_NAME);
      check("parish-district hides in Jefferson Parish, whose current lines are not confirmed, and stays switched on",
        parish.NAME === "Jefferson Parish" && !Object.prototype.hasOwnProperty.call(drawnParishes, String(parish.GEOID)) &&
          propsAt(districts, JEFFERSON).length === 0 && hidden && stillOn,
        `parish=${parish.NAME} drawn here=${propsAt(districts, JEFFERSON).length} hidden=${hidden} layersOn=${stillOn}`);
      await context.close();
    }

    {
      const parish = propsAt(counties, ORLEANS_LAKE)[0] || {};
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${ORLEANS_LAKE}&layers=parish-district`);
      const shown = await blockHidden(page, "parish-district", false);
      const info = await cardText(page, "parish-district");
      const text = info.text || "";
      check("in Orleans Parish's part of Lake Pontchartrain, where the city's map draws no district, parish-district shows and says the parish's own map leaves out some of its water",
        parish.NAME === "Orleans Parish" && propsAt(districts, ORLEANS_LAKE).length === 0 && shown && !info.error &&
          /No police jury or council district is drawn at this point/.test(text) &&
          /the parish's own district map leaves out some of the parish's water/.test(text),
        `parish=${parish.NAME} drawn here=${propsAt(districts, ORLEANS_LAKE).length} shown=${shown} ${text.slice(0, 140)}`);
      await context.close();
    }

    {
      const asked = [];
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${CADDO_PARISH}&layers=county`, async (pg) => {
        pg.on("request", (r) => asked.push(r.url()));
      });
      await cardText(page, "county");
      const shown = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-parish-district");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === false;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const list = asked.some((u) => /\/data\/app\/la-parish-district-parishes\.json/.test(u));
      const file = asked.some((u) => /\/data\/app\/la-parish-districts\.json/.test(u));
      const off = await page.evaluate(
        (n) => !window[n].state.layersOn["parish-district"], EXPORTS_NAME);
      check("with parish-district off, its coverage test reads the list of drawn parishes and never the districts file, and its toggle shows in Caddo",
        off && list && !file && shown,
        `off=${off} list=${list} districts file=${file} shown=${shown}`);
      await context.close();
    }

    const p = propsAt(districts, drawnPoints[0])[0] || {};
    const seat = seatOf(p)[0] || {};
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${drawnPoints[0]}&layers=parish-district`, async (pg) => {
        await pg.route("**/data/app/la-parish-officials.json", (r) => r.fulfill({ status: 503, body: "down" }));
      });
      const info = await cardText(page, "parish-district");
      const text = info.text || "";
      const o = roster[p.parishfips] || {};
      const named = (o.seats || []).concat(o.atLarge || [])
        .filter((s) => s.name && text.includes(s.name)).map((s) => s.name);
      check("parish-district still names the district, and names nobody, when the list of officials fails",
        !info.error && new RegExp(`\\bDistrict ${p.district}\\b`).test(text) &&
          /The list of members did not load, so no one is named here/.test(text) && named.length === 0,
        `named=${named.slice(0, 2)} ${text.slice(0, 120)}`);
      await context.close();
    }

    {
      const stub = JSON.parse(JSON.stringify(roster));
      stub[p.parishfips].seats = stub[p.parishfips].seats.filter((s) => s.seat !== `District ${p.district}`);
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${drawnPoints[0]}&layers=parish-district`, async (pg) => {
        await pg.route("**/data/app/la-parish-officials.json", (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(stub) }));
      });
      const info = await cardText(page, "parish-district");
      const text = info.text || "";
      check("parish-district says the list names no one for a seat it leaves out, and calls nothing vacant",
        !info.error && !!seat.name && /The Secretary of State's list names no one for this district/.test(text) &&
          !text.includes(seat.name) && !/vacant/i.test(text),
        text.slice(0, 140));
      await context.close();
    }

    {
      // Two members from one district, the shape of Cameron's District 4, on
      // a stubbed roster because no drawn parish elects two from one district
      // on 2026-10-20: the card names both, in the list's order.
      const stub = JSON.parse(JSON.stringify(roster));
      const second = { seat: seat.seat, name: "Second Member (test fixture)" };
      stub[p.parishfips].seats.push(second);
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${drawnPoints[0]}&layers=parish-district`, async (pg) => {
        await pg.route("**/data/app/la-parish-officials.json", (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(stub) }));
      });
      const info = await cardText(page, "parish-district");
      const text = info.text || "";
      check("parish-district names both members of a district that elects two",
        !info.error && !!seat.name && text.includes(seat.name) && text.includes(second.name) &&
          text.indexOf(seat.name) < text.indexOf(second.name) && /Where the names come from/i.test(text),
        text.slice(0, 160));
      await context.close();
    }
  }

  // 11. TRIBAL GOVERNMENT. The nation, its seat, the land and the council
  //     expected are read from the shipped files at the point, so a weekly
  //     council refresh moves the expectation with the file; what is asserted
  //     is that each card agrees with them.
  //       - The Tunica-Biloxi Reservation names the tribe, its seat, the land,
  //         every member of the council its own page names, the date and page
  //         they come from, and says no council seat belongs to this land,
  //         because the Census draws no tribal district on it.
  //       - The Coushatta Reservation names nobody and says why: the tribe's
  //         own site names its chairman and not the other four members.
  //       - The councils file is refused: the land still answers, naming the
  //         tribe and nobody on its council.
  //       - New Orleans City Hall is on no tribal land, and the card says so
  //         in the layer's own words.
  //     Each point is the pole of inaccessibility of the piece's largest part
  //     as the shipped file draws it (shapely polylabel, 2026-10-20), 258 to
  //     388 m from its edge.
  {
    const areas = shipped("tribal-areas.json");
    const councils = shipped("tribal-councils.json");
    const TUNICA = "31.11428,-92.05452";
    const COUSHATTA = "30.52604,-92.80054";
    const fieldsOf = (page) => page.$$eval("#card-tribal-government .card-field",
      (els) => els.map((e) => ({
        label: ((e.querySelector(".card-field-label") || {}).textContent || "").trim(),
        value: ((e.querySelector(".card-field-value") || {}).textContent || "").trim()
      })));
    const at = async (pt, routeFn) => {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${pt}&layers=tribal-government`, routeFn);
      const card = await cardText(page, "tribal-government");
      const fields = await fieldsOf(page);
      await context.close();
      return { text: card.text || "", error: card.error,
               by: (l) => (fields.find((f) => f.label === l) || {}).value || "" };
    };

    {
      const land = propsAt(areas, TUNICA);
      const p = land[0] || {};
      const council = (councils[p.aiannh] || {}).roster || [];
      const c = await at(TUNICA);
      check("the Tunica-Biloxi Reservation names the tribe, its seat, the land and its whole council, and where the names come from",
        land.length === 1 && council.length > 0 && !c.error &&
          c.by("Tribal government") === p.nation && p.nation === "Tunica-Biloxi Indian Tribe" &&
          c.by("Seat of government") === "Marksville, LA" &&
          c.by("Land") === "Tunica-Biloxi Reservation" &&
          council.every((m) => c.text.includes(m.name)) &&
          c.text.includes("Council") && c.text.includes("From the nation's own council page") &&
          c.text.includes("Where these names come from") &&
          c.by("Districts drawn here").indexOf("no council seat") !== -1 && !c.by("Why no names"),
        `land here=${land.length} council=${council.length} ${JSON.stringify(c.text.slice(0, 200))}`);
    }

    {
      const land = propsAt(areas, COUSHATTA);
      const p = land[0] || {};
      const c = await at(COUSHATTA);
      check("the Coushatta Reservation names nobody and says the tribe's own site names only its chairman",
        land.length === 1 && !councils[p.aiannh] && !c.error &&
          c.by("Tribal government") === "Coushatta Tribe of Louisiana" &&
          c.by("Why no names").indexOf("David Sickey") !== -1 &&
          !c.text.includes("From the nation's own council page"),
        `land here=${land.length} ${JSON.stringify(c.text.slice(0, 200))}`);
    }

    {
      const p = propsAt(areas, TUNICA)[0] || {};
      const council = (councils[p.aiannh] || {}).roster || [];
      const c = await at(TUNICA, async (pg) => {
        await pg.route("**/data/app/tribal-councils.json", (r) => r.fulfill({ status: 503, body: "down" }));
      });
      const named = council.filter((m) => c.text.includes(m.name)).map((m) => m.name);
      check("the Tribal Government card still names the tribe, and names nobody on its council, when the councils file fails",
        !c.error && c.by("Tribal government") === "Tunica-Biloxi Indian Tribe" &&
          council.length > 0 && named.length === 0,
        `named=${named.slice(0, 2)} ${JSON.stringify(c.text.slice(0, 160))}`);
    }

    {
      const off = await at(POINT);
      check("a point off tribal land is told so in the layer's own words",
        propsAt(areas, POINT).length === 0 &&
          off.text.indexOf("not on tribal land") !== -1 && off.text.indexOf("6 tribal areas") !== -1,
        JSON.stringify(off.text.slice(0, 120)));
    }
  }

  // 12. THE COURTS ELECTED BY DISTRICT: the Supreme Court, the courts of
  //     appeal and the district courts. Who is expected is read from the
  //     shipped la-judges.json, and which district from the shipped court
  //     files at the point, so a weekly refresh moves the expectation with
  //     the file; what is asserted is that each card agrees with them.
  //       - At City Hall the Supreme Court card names District 7's justice
  //         and party, says Orleans Parish is divided among the districts
  //         the shipped file gives a part of it, and links the court's site.
  //       - At City Hall the Court of Appeal card names every judge of the
  //         Fourth Circuit's First District and both judges the whole circuit
  //         elects, the court's office, and how many judges the list names.
  //       - At City Hall the Judicial District card names every judge of the
  //         Orleans civil and criminal district courts, both courts' offices
  //         and the one day every term ends.
  //       - In St. John the Baptist Parish, which the river divides between
  //         two districts, the Court of Appeal card names both and the judges
  //         of each.
  //       - In Iberville Parish, which La. R.S. 13:312 puts wholly in the
  //         First Circuit's First District's Election Section 1, the card says
  //         the point is in that section.
  //       - The judges file is refused: each card still names its district,
  //         says the names did not load, and names nobody.
  //     The St. John and Iberville points are each parish's pole of
  //     inaccessibility on the shipped parish file (shapely polylabel,
  //     2026-10-21), about 10 and 15 km from its edge.
  {
    const judges = shipped("la-judges.json");
    const sc = shipped("la-supreme-court-districts.json");
    const coa = shipped("la-court-of-appeal-districts.json");
    const jdc = shipped("la-district-court-districts.json");
    const STJOHN = "30.18432,-90.42573";
    const IBERVILLE = "30.18724,-91.22222";
    const COURTS = ["la-supreme-court", "la-court-of-appeal", "la-district-court"];
    const at = async (pt, routeFn) => {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${pt}&layers=${COURTS.join(",")}`, routeFn);
      const out = {};
      for (const id of COURTS) {
        const card = await cardText(page, id);
        const links = await page.evaluate((cid) => {
          const el = document.getElementById("card-" + cid);
          const block = el && el.closest(".layer-block");
          return block ? Array.from(block.querySelectorAll("a[href]")).map((a) => a.getAttribute("href")) : [];
        }, id);
        out[id] = { text: card.text || "", error: card.error, links };
      }
      await context.close();
      return out;
    };
    const names = (list) => (list || []).filter((p) => p && p.name).map((p) => p.name);
    const all = (text, list) => list.length > 0 && list.every((n) => text.includes(n));
    const andList = (l) => l.length === 1 ? l[0] : l.slice(0, -1).join(", ") + " and " + l[l.length - 1];

    {
      const c = await at(POINT);
      const here = propsAt(sc, POINT)[0] || {};
      const justice = ((judges.supreme.districts[here.unit] || {}).members || [])[0] || {};
      const sharing = sc.features.map((f) => f.properties)
        .filter((p) => (p.part || []).includes("Orleans")).map((p) => String(p.unit)).sort();
      const t = c["la-supreme-court"];
      check("the Supreme Court card names the district's justice and party, the parish's division, and the court's site",
        here.unit === "7" && !t.error && !!justice.name && t.text.includes(justice.name) &&
          !!justice.party && t.text.includes(justice.party) && sharing.length === 3 &&
          t.text.includes("Orleans Parish is divided among Supreme Court Districts " + andList(sharing)) &&
          t.links.includes("https://www.lasc.org/"),
        `unit=${here.unit} justice=${justice.name} sharing=${sharing} ${JSON.stringify(t.text.slice(0, 160))}`);

      const unit = (propsAt(coa, POINT)[0] || {}).unit;
      const members = names((judges.appeal.districts[unit] || {}).members);
      const circuit = judges.appeal.circuits["4"] || {};
      const big = names(circuit.atLarge);
      const office = (circuit.office || {}).address;
      const a = c["la-court-of-appeal"];
      check("the Court of Appeal card names every judge of the district, the circuit's at-large judges, the court's office and the count",
        unit === "4-1" && !a.error && all(a.text, members) && all(a.text, big) &&
          !!office && a.text.includes(office) &&
          a.text.includes(`names ${members.length} judges elected from this district, and ` +
            `${big.length} elected from the whole Fourth Circuit`),
        `unit=${unit} members=${members.length} big=${big.length} ${JSON.stringify(a.text.slice(0, 160))}`);

      const courts = (judges.district.districts["Orleans"] || {}).courts || [];
      const each = courts.map((x) => names(x.members));
      const terms = [...new Set(courts.flatMap((x) => (x.members || []).map((p) => p.termEnds)))];
      const j = c["la-district-court"];
      check("the Judicial District card names every judge of both Orleans courts, both offices and the day every term ends",
        (propsAt(jdc, POINT)[0] || {}).unit === "Orleans" && !j.error && courts.length === 2 &&
          each.every((n) => all(j.text, n)) &&
          courts.every((x) => !!(x.office || {}).address && j.text.includes(x.office.address)) &&
          terms.length === 1 && j.text.includes("ending on " + longDate(terms[0])),
        `courts=${courts.length} named=${each.map((n) => n.length)} terms=${terms} ${JSON.stringify(j.text.slice(0, 160))}`);
    }

    {
      const c = await at(STJOHN);
      const f = propsAt(coa, STJOHN)[0] || {};
      const two = (f.units || []).map((u) => names((judges.appeal.districts[u] || {}).members));
      const a = c["la-court-of-appeal"];
      check("in St. John the Baptist Parish the Court of Appeal card names both districts the river divides it between, and each one's judges",
        JSON.stringify(f.units) === JSON.stringify(["5-2", "5-3"]) && !a.error &&
          a.text.includes("Fifth Circuit, District 2 or 3") && a.text.includes("Which of the two") &&
          two.length === 2 && two.every((n) => all(a.text, n)),
        `units=${f.units} ${JSON.stringify(a.text.slice(0, 200))}`);
    }

    {
      const c = await at(IBERVILLE);
      const unit = (propsAt(coa, IBERVILLE)[0] || {}).unit;
      const secs = (judges.appeal.districts[unit] || {}).sections || {};
      const mine = Object.keys(secs).filter((s) => (secs[s].whole || []).includes("Iberville"));
      const a = c["la-court-of-appeal"];
      check("in Iberville Parish the Court of Appeal card says which election section the point is in, from the law",
        unit === "1-1" && mine.length === 1 && !a.error &&
          // a section label is set in capitals by the stylesheet, which
          // innerText reports, so the label is compared without case
          a.text.toLowerCase().includes(`judges elected from ${mine[0]}, which this point is in`.toLowerCase()) &&
          a.text.includes(`puts all of Iberville Parish in ${mine[0]}`),
        `unit=${unit} mine=${mine} ${JSON.stringify(a.text.slice(0, 200))}`);
    }

    {
      const c = await at(POINT, async (pg) => {
        await pg.route("**/data/app/la-judges.json", (r) => r.fulfill({ status: 503, body: "down" }));
      });
      const everyone = [].concat(
        names((judges.supreme.districts["7"] || {}).members),
        names((judges.appeal.districts["4-1"] || {}).members),
        names((judges.appeal.circuits["4"] || {}).atLarge),
        ...((judges.district.districts["Orleans"] || {}).courts || []).map((x) => names(x.members)));
      const named = everyone.filter((n) => COURTS.some((id) => c[id].text.includes(n)));
      check("each court card still names its district, says the names did not load, and names nobody, when the judges file fails",
        everyone.length > 0 && named.length === 0 &&
          COURTS.every((id) => !c[id].error && c[id].text.includes("The list of judges did not load just now")) &&
          c["la-supreme-court"].text.includes("Supreme Court District 7") &&
          c["la-court-of-appeal"].text.includes("Fourth Circuit, District 1") &&
          c["la-district-court"].text.includes("Civil District Court and Criminal District Court"),
        `named=${named.slice(0, 2)} ${COURTS.map((id) => JSON.stringify(c[id].text.slice(0, 80))).join(" | ")}`);
    }
  }

  // 13. THE CITY COUNCIL DISTRICT LAYER, in the four cities whose own current
  //     map is confirmed: Lafayette, Bossier City, Central and Slidell (since
  //     2026-10-21). The district, city and member expected are read from the
  //     shipped files at the point (la-city-wards.json and the City card's
  //     roster, la-municipal-officials.json), so a rebuild moves the
  //     expectation with them; what is asserted is that the card agrees.
  //       - In each city, the card names the city, the district, its member,
  //         the members elected at large where the city has them, whose map
  //         the line is and how close the drawing is to it, and where the
  //         names come from; it links the city's page for its map and, in its
  //         footer, the Secretary of State's list; and it dials every member
  //         it names, each at the number the list prints, and no other.
  //       - Where Bossier City's own map draws District 2 and District 4 over
  //         one spot, the card names both districts and both members.
  //       - At New Orleans City Hall the layer shows and says which four
  //         cities are drawn, and that New Orleans is governed by its parish's
  //         council.
  //       - The roster is refused: the district still answers and names nobody.
  //       - A seat the list leaves out, on a stubbed roster because no drawn
  //         city has one on 2026-10-21: the card says the list names no one
  //         for it, calls nothing vacant, and still names the members elected
  //         at large.
  //     The four city points are each city's district farthest from its own
  //     edge, at its pole of inaccessibility as the shipped file draws it
  //     (shapely polylabel, 2026-10-21), 1.2 to 2.7 km inside; the Bossier City
  //     point is the polylabel of the largest part of that overlap, 1.9 m from
  //     its edge. Measured the same day against each city's own layer, each
  //     point answered the district the file draws there (both 2 and 4 at the
  //     overlap), and a point outside each city answered none.
  {
    const wards = shipped("la-city-wards.json");
    const towns = shipped("la-municipal-officials.json");
    const CITY_POINTS = ["30.17791,-92.05253", "32.54174,-93.64607", "30.60565,-91.06211", "30.32313,-89.80894"];  // Lafayette 3, Bossier City 4, Central 5, Slidell D
    const BOSSIER_TWO = "32.526884,-93.632816";  // Bossier City Districts 2 and 4, as the city's map draws them
    const named = (list) => (list || []).filter((m) => m && m.name);
    const memberOf = (p) => named((towns[p.geoid] || {}).seats).filter((m) => m.seat === p.seat);
    const dials = (people) => people.filter((m) => m.phone).map((m) => "tel:" + m.phone.replace(/[^\d+]/g, ""));
    const wardCard = async (pt, routeFn) => {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${pt}&layers=city-ward`, routeFn);
      const info = await cardText(page, "city-ward");
      const got = await page.evaluate((cid) => {
        const el = document.getElementById("card-" + cid);
        const block = el && el.closest(".layer-block");
        return {
          body: el ? Array.from(el.querySelectorAll("a[href]")).map((a) => a.href) : [],
          footer: block ? Array.from(block.querySelectorAll(".card-footer a[href]")).map((a) => a.href) : [],
          hidden: !!(block && block.hidden)
        };
      }, "city-ward");
      await context.close();
      return { text: info.text || "", error: info.error, links: got };
    };
    const lineSentence = (p) => p.source.charAt(0).toUpperCase() + p.source.slice(1) +
      ". The line drawn here is within 4 metres of that map's own.";

    for (const pt of CITY_POINTS) {
      const at = propsAt(wards, pt);
      const p = at[0] || {};
      const o = towns[p.geoid] || {};
      const seats = memberOf(p);
      const atLarge = named(o.atLarge);
      const people = seats.concat(atLarge);
      const c = await wardCard(pt);
      const tel = c.links.body.filter((h) => h.startsWith("tel:"));
      const want = dials(people);
      check(`the City Council District card in ${p.city || "a drawn city"} names ${p.seat}, its member${atLarge.length ? ", the members elected at large" : ""}, whose map the line is and where the names come from, links the city's map page and the list, and dials each member`,
        at.length === 1 && seats.length === 1 && !c.error && !c.links.hidden &&
          new RegExp(`\\b${p.seat}\\b`).test(c.text) && c.text.includes(p.city) &&
          people.every((m) => c.text.includes(m.name)) &&
          (atLarge.length ? /Members elected at large/i.test(c.text) : !/Members elected at large/i.test(c.text)) &&
          /Where this line comes from/i.test(c.text) && c.text.includes(lineSentence(p)) &&
          (people.length > 1 ? /Where the names come from/i.test(c.text) : /Where the name comes from/i.test(c.text)) &&
          c.text.includes(`read on ${longDate(o.read)}`) &&
          c.links.body.includes(p.sourceUrl) && /The city's page for this map/.test(c.text) &&
          c.links.footer.includes(o.sourceUrl) &&
          want.length === people.length && want.every((h) => tel.includes(h)) && tel.length === want.length &&
          !/More than one/.test(c.text),
        `districts here=${at.length} seats=${seats.length} tel want=${want.length} got=${tel.length} ${c.text.slice(0, 160)}`);
    }

    {
      const at = propsAt(wards, BOSSIER_TWO);
      const people = at.flatMap(memberOf);
      const c = await wardCard(BOSSIER_TWO);
      const seatsHere = at.map((p) => p.seat).sort();
      check("where Bossier City's own map draws District 2 and District 4 over one spot, the City Council District card names both districts and both members",
        at.length === 2 && seatsHere.join() === "District 2,District 4" && people.length === 2 && !c.error &&
          people.every((m) => c.text.includes(m.name)) && /More than one district here/.test(c.text) &&
          c.text.includes("Bossier City's own district map draws District 2 and District 4 over this spot, so this app names both rather than choosing one."),
        `districts here=${seatsHere} members=${people.length} ${c.text.slice(0, 160)}`);
    }

    {
      const c = await wardCard(POINT);
      check("at New Orleans City Hall the City Council District card shows, says which four cities are drawn and that New Orleans is governed by its parish's council",
        propsAt(wards, POINT).length === 0 && !c.error && !c.links.hidden &&
          /No city council district is drawn at this point/.test(c.text) &&
          /four of Louisiana's 13 cities of 25,000 people or more \(Lafayette, Bossier City, Central and Slidell\)/.test(c.text) &&
          /New Orleans, Baton Rouge and Houma are governed by their parish's council/.test(c.text),
        c.text.slice(0, 160));
    }

    {
      const pt = CITY_POINTS[0];
      const p = propsAt(wards, pt)[0] || {};
      const o = towns[p.geoid] || {};
      const everyone = named(o.seats).concat(named(o.atLarge), o.mayor && o.mayor.name ? [o.mayor] : []);
      const c = await wardCard(pt, async (pg) => {
        await pg.route("**/data/app/la-municipal-officials.json", (r) => r.fulfill({ status: 503, body: "down" }));
      });
      const leaked = everyone.filter((m) => c.text.includes(m.name)).map((m) => m.name);
      check("the City Council District card still names the district, and names nobody, when the list of mayors and councils fails",
        !c.error && new RegExp(`\\b${p.seat}\\b`).test(c.text) && c.text.includes(lineSentence(p)) &&
          /The list of mayors and councils did not load, so no one is named here/.test(c.text) &&
          everyone.length > 0 && leaked.length === 0,
        `named=${leaked.slice(0, 2)} ${c.text.slice(0, 140)}`);
    }

    {
      const pt = CITY_POINTS[3];
      const p = propsAt(wards, pt)[0] || {};
      const stub = JSON.parse(JSON.stringify(towns));
      const left = memberOf(p)[0] || {};
      stub[p.geoid].seats = stub[p.geoid].seats.filter((m) => m.seat !== p.seat);
      const atLarge = named(stub[p.geoid].atLarge);
      const c = await wardCard(pt, async (pg) => {
        await pg.route("**/data/app/la-municipal-officials.json", (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(stub) }));
      });
      check("the City Council District card says the list names no one for a seat it leaves out, calls nothing vacant, and still names the members elected at large",
        !c.error && !!left.name && !c.text.includes(left.name) && atLarge.length > 0 &&
          atLarge.every((m) => c.text.includes(m.name)) &&
          /The Secretary of State's list names no one for this district, so no one is named here/.test(c.text) &&
          !/vacant/i.test(c.text),
        c.text.slice(0, 160));
    }
  }
} finally {
  await browser.close();
}

if (failures.length) {
  console.error(`\n${failures.length} smoke check(s) failed: ${failures.join(", ")}`);
  process.exit(1);
}
console.log("\nAll smoke checks passed.");
