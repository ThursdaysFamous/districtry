// Headless boot + behaviour smoke test, run in CI on every pull request
// (.github/workflows/smoke-test.yml). Serves the real index.html and drives it
// in Chromium via Playwright — the check the README's "Validation" section
// describes and that OPTIMIZATION_PLAYBOOK item 5 asked to actually commit.
//
// It deliberately depends only on the app shell (Leaflet from its CDN) and the
// same-origin data/app/*.json files — never on the live district APIs, which
// are flaky/blocked in CI. The four same-origin anchors (County or City,
// U.S. House, Virginia Senate and House of Delegates) are the deterministic
// ground truth, and every live service a check needs is stubbed.
//
// Run locally against a static server:
//     python3 -m http.server 8000 &
//     npm install playwright && BASE_URL=http://localhost:8000/va/ node va/scripts/smoke_test.mjs
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
const POINT = "37.53850,-77.43370"; // Virginia State Capitol, 1000 Bank Street, Richmond (an independent city)
const OFFLINE = ["county", "us-house", "va-senate", "va-house"];
const EXPECT_DISTRICT = { "county": "Richmond city", "us-house": "4", "va-senate": "14", "va-house": "78" };
const NEGATIVE_POINT = "37.00000,-75.30000"; // Open Atlantic Ocean east of the mouth of Chesapeake Bay, 44 km from the nearest edge of Virginia's outline — outside Virginia and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-29: none of the state's shipped boundary files contains it, none of fleet-outlines.json's outlines does either, and the State Capitol, the control, is inside every shipped file. Water on purpose, the way North Carolina's and Louisiana's are: every land neighbour of Virginia is either live already (Kentucky, Tennessee, North Carolina) or a state the fleet plans to build (West Virginia, Maryland), so a point on a neighbour's land would have to move when that neighbour goes live.
const APP_NAME = "districtry Virginia";
const EXPECT_LAYERS = 16;
// ==== GENERATED:END smoke-config ====
// Instance constants this file owns (the worksheet emits the block above).
const EXPORTS_NAME = "VirginiaExplorer";
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
  geometry: { type: "Point", coordinates: [-77.43370, 37.53850] },
  properties: {
    // the typed number: an answer without it shows the street instead of
    // a row (ENGINE geocoder-search runAddressSearch)
    housenumber: "16",
    street: "W Jones St",
    city: "Capital City",
    state: "Virginia",
    postcode: "00000"
  }
};
// Contract stubs (their consuming checks are reference-fork scenarios,
// dropped from this instance's body):
const GAP_PROBE = { county: "statewide", label: "Statewide", lat: 37.53850, lng: -77.43370 };
const MOVE_POINT = { lat: 0, lng: 0, district: "0" };
const STRAGGLER_FILE = "data/app/state-counties.json";
const STRAGGLER_POINT = "0,0";
// Layers expected to HIDE (not merely report no district) at NEGATIVE_POINT.
// None of the four anchors declares a coverage() test, so none hide — they
// all take the honest "no district here" branch instead.
const NEGATIVE_HIDDEN = [];
// A point in a county rather than a city, for the County or City card's
// other half: Chesterfield County's pole of inaccessibility as the shipped
// file draws it (shapely polylabel, 2026-10-29).
const COUNTY_POINT = "37.41619,-77.64089";
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
  //     VIRGINIA HAS FIVE LAND NEIGHBOURS AND THE DISTRICT OF COLUMBIA, AND
  //     THE FLEET SERVES THREE OF THEM. A click a little way inside each live
  //     neighbour must open that neighbour's app: Pikeville, Kentucky; Johnson
  //     City, Tennessee; and Greensboro, North Carolina. Measured against
  //     fleet-outlines.json on 2026-10-29, each lies inside its own state's
  //     outline and no other, 26.6, 31.2 and 51.9 km from this app's outline.
  //     This instance answers its own side from the state outline the wash
  //     retained, with no fetch, and Chicago proves the fleet file is still
  //     read for ground far from here.
  //
  //     WEST VIRGINIA, MARYLAND AND THE DISTRICT ARE DELIBERATELY NOT CASES.
  //     Nobody serves them today, so a click there stays here; but West
  //     Virginia is the plan's third state, and a "stays here" case in any of
  //     them would start failing the day it goes live, in a change that is
  //     about another state. The negative point, in the Atlantic, carries that
  //     half instead (1a2-ii).
  {
    const cases = [
      { name: "Chicago", lat: 41.8825, lng: -87.6285, want: "https://districtry.com/il/" },
      { name: "Pikeville, Kentucky", lat: 37.4793, lng: -82.5188, want: "https://districtry.com/ky/" },
      { name: "Johnson City, Tennessee", lat: 36.3134, lng: -82.3535, want: "https://districtry.com/tn/" },
      { name: "Greensboro, North Carolina", lat: 36.0726, lng: -79.7920, want: "https://districtry.com/nc/" },
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
      check(`a click on ${c.name} from Virginia opens ${c.want} with the point`, !!went, went || page.url());
      await context.close();
    }
  }

  // 1a2-ii. The half that keeps 1a2 honest: the negative point, in the
  //     Atlantic 44 km from Virginia's outline, is outside every outline in
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
    check("a click in the Atlantic, outside every app's outline, stays in this app",
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
    // 2a. EACH CHAMBER'S OWN PAGES NAME THE MEMBER, and the card carries what
    //     the state prints: the name, the party, the Capitol office and the
    //     member's e-mail address, which must open as a mailto link. The
    //     values expected are read from the shipped roster for each chamber's
    //     anchor district, so a weekly refresh that changes them changes what
    //     is expected. The office sits behind a closed disclosure, which
    //     innerText leaves out, so the office is read from textContent.
    for (const [id, file] of [["va-senate", "va-senate-members.json"], ["va-house", "va-house-members.json"]]) {
      const rec = shipped(file)[EXPECT_DISTRICT[id]] || {};
      const info = await cardText(page, id);
      const got = await page.evaluate((cid) => {
        const el = document.getElementById("card-" + cid);
        return {
          all: el ? el.textContent.replace(/\s+/g, " ") : "",
          mailto: el ? Array.from(el.querySelectorAll("a[href^='mailto:']")).map((a) => a.getAttribute("href")) : [],
        };
      }, id);
      const street = (rec.capitolOffice || [])[0] || null;
      const mailOk = !!rec.email && got.mailto.some((h) =>
        decodeURIComponent(h.slice(7)).toLowerCase() === String(rec.email).toLowerCase());
      check(`${id} card names the member, the party, the Capitol office and the e-mail address the state prints`,
        !info.error && !!rec.name && info.text.includes(rec.name) &&
          !!rec.party && info.text.toLowerCase().includes(String(rec.party).toLowerCase()) &&
          !!street && got.all.includes(street) && mailOk,
        `name=${rec.name} street=${street} mailto=${JSON.stringify(got.mailto)} ${info.text.slice(0, 80)}`);
    }
    await context.close();
  }

  // 2a2. A SEAT THE CHAMBER LISTS AS VACANT SAYS SO, in the chamber's words,
  //     and names nobody. House of Delegates District 20 read vacant on
  //     2026-10-29; the point is the shipped district's pole of inaccessibility
  //     (shapely polylabel), about 2.2 km from its nearest edge. Where a later
  //     refresh seats a delegate there, the check asserts that delegate is
  //     named instead, so a filled seat passes and a wrong name still fails.
  {
    const HD20 = "38.75665,-77.47521";
    const rec = shipped("va-house-members.json")["20"] || {};
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${HD20}&layers=va-house`);
    const info = await cardText(page, "va-house");
    const text = info.text || "";
    const others = Object.entries(shipped("va-house-members.json"))
      .filter(([d, r]) => d !== "20" && r.name && text.includes(r.name)).map(([, r]) => r.name);
    const ok = rec.vacant
      ? /\bVacant\b/.test(text) && !!rec.vacantWhy && text.includes(rec.vacantWhy)
      : !!rec.name && text.includes(rec.name);
    check(rec.vacant
        ? "va-house says District 20 is vacant, in the chamber's own words, and names nobody"
        : "va-house names District 20's delegate now that the chamber lists one",
      !info.error && /District 20\b/.test(text) && ok && others.length === 0,
      `vacant=${!!rec.vacant} others=${others.slice(0, 2)} ${text.slice(0, 140)}`);
    await context.close();
  }

  // 2a3. THE COUNTY OR CITY CARD TELLS A CITY FROM A COUNTY, AND NAMES WHO
  //     GOVERNS IT. Virginia's 38 independent cities belong to no county, so
  //     at the State Capitol, in the City of Richmond, the card must say the
  //     city belongs to no county, that its council is elected from the
  //     number of districts the names file holds, and name the mayor the
  //     names file gives; in Chesterfield County it must say the board of
  //     supervisors is elected from that county's districts and claim no
  //     city. Every name and count is read from the shipped files, so a
  //     rebuild that moved either point or changed a seat fails here rather
  //     than passing on stale words.
  const officials = shipped("va-local-officials.json");
  function boardDistricts(fips, body) {
    const loc = officials.localities[fips] || {};
    return Object.values(loc.districts || {}).filter((d) => d.seats && d.seats[body]).length;
  }
  {
    const counties = shipped("state-counties.json");
    for (const [pt, isCity] of [[POINT, true], [COUNTY_POINT, false]]) {
      const props = propsAt(counties, pt)[0] || {};
      const name = props.NAME || "";
      const fips = String(props.GEOID || "");
      const loc = officials.localities[fips] || {};
      const n = boardDistricts(fips, "board");
      const mayor = (((loc.bodies || {}).mayor || {}).atLarge || {}).members || [];
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${pt}&layers=county`);
      const info = await cardText(page, "county");
      const text = info.text || "";
      const ok = isCity
        ? / city$/.test(name) && /An independent city/.test(text) && /Your city council/.test(text) &&
          text.includes(`Elected from ${n} districts`) && mayor.length === 1 && text.includes(mayor[0].name) &&
          !/Your board of supervisors/.test(text)
        : / County$/.test(name) && /Your board of supervisors/.test(text) &&
          text.includes(`Elected from ${n} districts`) && !/An independent city/.test(text);
      check(isCity
          ? `the County or City card says ${name || "the city"} belongs to no county and names its council's ${n} districts and its mayor`
          : `the County or City card says ${name || "the county"}'s board of supervisors is elected from ${n} districts and claims no city`,
        !info.error && !!name && n > 0 && text.includes(name) && ok, text.slice(0, 200));
      await context.close();
    }
  }

  // 2a4. THE LOCAL DISTRICT AND PRECINCT CARDS name what the shipped files
  //     put at the point. In Chesterfield County the Supervisor or Council
  //     District and School Board District cards must name the district the
  //     district file draws there and the member the names file seats in it,
  //     with the election that seated them, and the Voting Precinct card the
  //     precinct the precinct file draws there. At Norfolk's City Hall the
  //     point is in a ward and a superward, and the council card must name
  //     both districts and both members. In Arlington, whose County Board is
  //     elected at large, the district layer hides rather than saying no
  //     district is here, and the County or City card names the members.
  //     In Hanover County, whose school board is appointed, the County or
  //     City card says so and names no one. In Poquoson's Eastern District,
  //     read by hand from the city's own page, the card names the page.
  {
    const districts = shipped("va-local-districts.json");
    const precincts = shipped("va-precincts.json");
    function seated(p, body) {
      const d = ((officials.localities[String(p.countyFips)] || {}).districts || {})[p.key] || {};
      return ((d.seats || {})[body] || {}).members || [];
    }
    function drawnAt(pt, body) {
      return propsAt(districts, pt).filter((p) => seated(p, body).length);
    }
    for (const [id, body] of [["supervisor-district", "board"], ["school-board-district", "school"]]) {
      const here = drawnAt(COUNTY_POINT, body);
      const members = here.length === 1 ? seated(here[0], body) : [];
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${COUNTY_POINT}&layers=${id}`);
      const info = await cardText(page, id);
      const text = info.text || "";
      check(`${id} names ${here.length === 1 ? here[0].name : "the district"} and the member the names file seats there`,
        !info.error && here.length === 1 && members.length > 0 && text.includes(here[0].name) &&
          members.every((m) => text.includes(m.name)) && /Elected \d{1,2} \w+ \d{4}/.test(text),
        text.slice(0, 160));
      await context.close();
    }
    {
      const here = propsAt(precincts, COUNTY_POINT);
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${COUNTY_POINT}&layers=voting-precinct`);
      const info = await cardText(page, "voting-precinct");
      const text = info.text || "";
      check(`voting-precinct names ${here.length === 1 ? here[0].name : "the precinct"}, the one the precinct file draws at the point`,
        !info.error && here.length === 1 && text.includes(String(here[0].name)) && /No one to public office/.test(text),
        text.slice(0, 120));
      await context.close();
    }
    {
      const NORFOLK_POINT = "36.84680,-76.28520"; // Norfolk City Hall, 810 Union Street
      const here = drawnAt(NORFOLK_POINT, "board");
      const people = here.flatMap((p) => seated(p, "board"));
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${NORFOLK_POINT}&layers=supervisor-district`);
      const info = await cardText(page, "supervisor-district");
      const text = info.text || "";
      check("at Norfolk's City Hall the council card names the ward and the superward and both members",
        !info.error && here.length === 2 && here.some((p) => /^Ward /.test(p.name)) &&
          here.some((p) => /^Superward /.test(p.name)) && here.every((p) => text.includes(p.name)) &&
          people.length >= 2 && people.every((m) => text.includes(m.name)),
        `${here.map((p) => p.name)} ${text.slice(0, 160)}`);
      await context.close();
    }
    {
      // A seat read by hand from the city's own page: Poquoson's Eastern
      // District, which the results could not settle. Its card names both
      // members, the page it read them from and the day.
      const POQUOSON_POINT = "37.13344,-76.34268"; // inside the Eastern District
      const here = drawnAt(POQUOSON_POINT, "board");
      const seat = here.length === 1
        ? (((officials.localities["51735"] || {}).districts || {})[here[0].key] || {}).seats.board : {};
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POQUOSON_POINT}&layers=supervisor-district`);
      const info = await cardText(page, "supervisor-district");
      const text = info.text || "";
      check("in Poquoson's Eastern District the card names the members read from the city's own page, and says so",
        !info.error && here.length === 1 && !!(seat.verified && seat.verified.url) &&
          (seat.members || []).length === 2 && seat.members.every((m) => text.includes(m.name)) &&
          /Poquoson's own page, read \d{1,2} \w+ \d{4}/.test(text),
        text.slice(0, 200));
      await context.close();
    }
    {
      const ARLINGTON_POINT = "38.88990,-77.08580"; // Arlington County courthouse
      const members = ((((officials.localities["51013"] || {}).bodies || {}).board || {}).atLarge || {}).members || [];
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${ARLINGTON_POINT}&layers=supervisor-district,county`);
      const hidden = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-supervisor-district");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === true;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const info = await cardText(page, "county");
      const text = info.text || "";
      check("in Arlington, elected at large, the district layer hides and the County card names the board",
        hidden && drawnAt(ARLINGTON_POINT, "board").length === 0 && members.length > 1 &&
          members.every((m) => text.includes(m.name)) && /elected at large/.test(text),
        `hidden=${hidden} ${text.slice(0, 160)}`);
      await context.close();
    }
    {
      const HANOVER_POINT = "37.76290,-77.36830"; // Hanover County courthouse
      const school = (((officials.localities["51085"] || {}).bodies || {}).school) || {};
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${HANOVER_POINT}&layers=county`);
      const info = await cardText(page, "county");
      const text = info.text || "";
      check("in Hanover County, whose school board is appointed, the County card says so and names no one",
        !info.error && school.elected === false && /is appointed by the board of supervisors/.test(text),
        text.slice(0, 160));
      await context.close();
    }
  }

  // 2a5. THE SOIL AND WATER CONSERVATION DISTRICT, on the County or City
  //     card. Chesterfield County is in a district of two localities, whose
  //     card must name the district, the other county and both directors its
  //     voters elected; Fairfax County is a district alone, which elects three;
  //     Alleghany County's last election lists one of its two seats, and the
  //     card must say the other is not named; the City of Richmond is in no
  //     district, and the card must say the state's list places it in none.
  //     Every name, count and district is read from the shipped file.
  {
    const boards = shipped("va-conservation-boards.json");
    const counties = shipped("state-counties.json");
    const cases = [
      [COUNTY_POINT, "51041", "shared"],
      ["38.85300,-77.35820", "51059", "alone"],   // Fairfax County Government Center
      ["37.78870,-79.88200", "51005", "listed"],  // Low Moor, Alleghany County
      [POINT, "51760", "none"],
    ];
    for (const [pt, fips, kind] of cases) {
      const props = propsAt(counties, pt)[0] || {};
      const e = boards.localities[fips] || {};
      const dist = e.district ? boards.districts[e.district] || {} : {};
      const others = (dist.localities || []).filter((g) => g !== fips)
        .map((g) => (boards.localities[g] || {}).name);
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${pt}&layers=county`);
      const info = await cardText(page, "county");
      const text = info.text || "";
      // The section label is set in capitals by the stylesheet, and innerText
      // returns it that way, so a district's name is compared without case.
      const lower = text.toLowerCase();
      const at = lower.indexOf("conservation district");
      const names = (e.members || []).map((m) => m.name);
      let ok = !info.error && String(props.GEOID || "") === fips;
      if (kind === "none") {
        ok = ok && e.district === null && /places Richmond city in none of them/.test(text) &&
          !Object.keys(boards.districts).some((d) => lower.includes(`${d} soil and water conservation district`.toLowerCase()));
      } else {
        ok = ok && !!e.district && lower.includes(`${e.district} Soil and Water Conservation District`.toLowerCase()) &&
          names.length > 0 && names.every((n) => text.includes(n)) &&
          /Elected director/.test(text) && /two more are appointed by the Virginia Soil and Water Conservation Board/.test(text);
        if (kind === "shared") {
          ok = ok && others.length > 0 && others.every((n) => text.includes(n)) && names.length === 2 &&
            /two directors are elected by the voters of each county and city in the district/.test(text);
        }
        if (kind === "alone") {
          ok = ok && others.length === 0 && names.length === 3 && /Fairfax County alone/.test(text) &&
            /three directors are elected by the voters of the district/.test(text);
        }
        if (kind === "listed") {
          ok = ok && e.listed === 1 && e.seats === 2 && names.length === 1 &&
            /the results of its last election list 1, so the other is not named here/.test(text);
        }
      }
      check(kind === "none"
          ? "in the City of Richmond the County or City card says no conservation district covers it"
          : `the County or City card names ${props.NAME || fips}'s conservation district (${kind}) and its elected directors`,
        ok, text.slice(Math.max(0, at - 80), at + 220));
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
  //    fire-station is 2,330 points in Virginia's envelope (measured
  //    2026-10-29), already past the 2,000-record cap the service reports as
  //    HTTP 200 + exceededTransferLimit rather than an error, so a single
  //    request would drop real stations and the nearest-3 card would look
  //    correct at every point. The source manifest's count row cannot see
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
      attributes: { NAME: `FAR STATION ${i}`, ADDRESS: "1 Far Rd", CITY: "Abingdon", STATE: "VA", ZIPCODE: "24210" },
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
                              CITY: "Richmond", STATE: "VA", ZIPCODE: "23219" },
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
      /Richmond, VA/.test(text), text.slice(0, 140));
    await context.close();
  }

  // 7. THE LIVE TIGERWEB FABRIC CARDS, STUBBED — and stubbed on purpose rather
  //    than anchored. The worksheet's OFFLINE anchors are same-origin only,
  //    which is this test's own stated contract, and these layers fetch the
  //    Census live: asserting a card against somebody else's server makes the
  //    test fail on their outage and on any network that intercepts TLS.
  //
  //    THESE LAYERS ARE ANSWERED FROM SAME-ORIGIN TILE ARCHIVES
  //    (scripts/mirror_tiger_tiles.py), and the stubs stay anyway: several
  //    cases below exist in no archive (an affix or a status no table
  //    carries), so each case refuses its layer's archive and the stub decides
  //    the card, through the archive-failure path il's smoke check 2d also
  //    holds.
  //
  //    WHAT IS WORTH TESTING IS THIS INSTANCE'S OWN CODE, and none of it is
  //    exercised by a live fetch that happens to work. Each claim below is
  //    wrong in a way a reader would see:
  //
  //    (a) The City or Town card tells a Virginia CITY, which belongs to no
  //        county, from a TOWN, which governs alongside its county, by the
  //        Census's own name suffix, and an affix the card does not know
  //        produces NO type row rather than an improvised one.
  //    (b) The Magisterial District card says what each of the three things
  //        TIGER files as a Virginia county subdivision is (a magisterial
  //        district, an independent city, and Arlington County, which is not
  //        divided), names the county from the app's own county file, and
  //        says nothing about a status it does not know. A magisterial
  //        district says which drawing it is: the Department's lines, where
  //        it is the district the county's board is elected from, or the
  //        Census's copy, in a county whose election districts differ or
  //        that elects its board at large, read from the officials file the
  //        Supervisor or Council District card reads. These cases serve the
  //        layer's one shipped file as a one-feature fixture; the two checks
  //        after them read the real file at real points.
  //    (c) The two school tilings partition the state, so each answers under
  //        its own label, and a miss on either points at the other card
  //        rather than saying no school division is here.
  //
  //    Labels are matched without case because the card's stylesheet sets
  //    them in capitals and innerText reads them that way.
  {
    function esriPolygon(props, ring) {
      return {
        attributes: props,
        geometry: { rings: [ring || [[-78.0, 37.0], [-77.0, 37.0], [-77.0, 38.0], [-78.0, 38.0], [-78.0, 37.0]]] }
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
    // the town cases' names are read from the shipped file, so a rebuild that
    // changes a seat fails here rather than passing on stale words; each
    // case also fails if the file names nobody it expects
    function townNames(town, body) {
      const names = ((((officials.towns || {})[town] || {})[body] || {}).members || []).map((m) => m.name);
      return names.length ? names : ["(the shipped file names no one for " + town + "'s " + body + ")"];
    }
    function nameRe(name) {
      return new RegExp(String(name).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    }
    // a ring in far southwest Virginia, nowhere near the point
    const FAR = [[-82.9, 36.6], [-82.7, 36.6], [-82.7, 36.8], [-82.9, 36.8], [-82.9, 36.6]];
    const cases = [
      {
        name: "a city says it belongs to no county, never alongside one",
        layer: "municipality", service: PLACES,
        props: { GEOID: "5101000", NAME: "Alexandria city", BASENAME: "Alexandria", STATE: "51", LSADC: "25", FUNCSTAT: "A" },
        want: [/Alexandria city/, /Independent city — it belongs to no county/, /Your city council/, /Every member is elected at large/],
        reject: [/alongside the county/, /Incorporated town/, /town council/i]
      },
      {
        // Abingdon's council chooses its mayor, and its page lists the mayor
        // with the council, so the card names the council from the page and
        // says nothing about a missing mayor's election
        name: "a town says it governs alongside its county, and names its council from its own page",
        layer: "municipality", service: PLACES,
        props: { GEOID: "5100148", NAME: "Abingdon town", BASENAME: "Abingdon", STATE: "51", LSADC: "43", FUNCSTAT: "A" },
        want: [/Abingdon town/, /Incorporated town — a local government over this point, alongside the county it lies in/,
          ...townNames("Abingdon", "town").map(nameRe), /Abingdon's own page, read/],
        reject: [/Independent city/, /city council/i, /no election for this town's mayor/, /Not named here/]
      },
      {
        name: "a town's council and mayor are named from the state's results, each with its election",
        layer: "municipality", service: PLACES,
        props: { GEOID: "5116608", NAME: "Christiansburg town", BASENAME: "Christiansburg", STATE: "51", LSADC: "43", FUNCSTAT: "A" },
        want: [/Christiansburg town/, ...townNames("Christiansburg", "mayor").map(nameRe),
          ...townNames("Christiansburg", "town").map(nameRe), /Elected \d+ November 20\d\d/],
        reject: [/Not named here/, /own page, read/, /no election for this town's mayor/]
      },
      {
        name: "a town that elects its council by ward names no council member and says why",
        layer: "municipality", service: PLACES,
        props: { GEOID: "5183136", NAME: "Warrenton town", BASENAME: "Warrenton", STATE: "51", LSADC: "43", FUNCSTAT: "A" },
        want: [/Warrenton town/, /elects council members by ward/, /Warrenton's own website is the current source/,
          ...townNames("Warrenton", "mayor").map(nameRe)],
        reject: [/own page, read/]
      },
      {
        name: "a town with no mayor's election in the results says so and names its council",
        layer: "municipality", service: PLACES,
        props: { GEOID: "5187072", NAME: "Wise town", BASENAME: "Wise", STATE: "51", LSADC: "43", FUNCSTAT: "A" },
        want: [/Wise town/, /no election for this town's mayor since 2015/, ...townNames("Wise", "town").map(nameRe)],
        reject: [/Not named here/]
      },
      {
        name: "a town with a school division of its own names its school board",
        layer: "municipality", service: PLACES,
        props: { GEOID: "5118400", NAME: "Colonial Beach town", BASENAME: "Colonial Beach", STATE: "51", LSADC: "43", FUNCSTAT: "A" },
        want: [/Colonial Beach town/, /Town school board/, ...townNames("Colonial Beach", "school").map(nameRe)],
        reject: []
      },
      {
        name: "an affix the card does not carry prints NO type row",
        layer: "municipality", service: PLACES,
        props: { GEOID: "5199999", NAME: "Nowhere borough", BASENAME: "Nowhere", STATE: "51", LSADC: "21", FUNCSTAT: "A" },
        want: [/Nowhere borough/],
        reject: [/Independent city/, /Incorporated town/]
      },
      {
        // the shipped file's real Rockbridge entry is drawn from the
        // Department's lines, and the county elects its board and its school
        // board by district (va-local-officials.json, read as shipped)
        name: "a magisterial district drawn from the Department's lines says whose election district it is",
        layer: "county-subdivision", also: "county", file: true,
        props: { GEOID: "5116390568", NAME: "Buffalo district", BASENAME: "Buffalo", COUNTY: "163", LSADC: "27", FUNCSTAT: "N", lines: "department", district: "51163-01" },
        want: [/Buffalo district/, /Rockbridge County/, /the districts the board of supervisors and the school board are elected from/,
          /Department of Elections' precinct lines/, /Supervisor or Council District card names its supervisor/],
        reject: [/as the U\.S\. Census Bureau maps it/, /belongs to no county/, /does not divide this county/]
      },
      {
        name: "the Census's copy in a county whose election districts differ says it is not them",
        layer: "county-subdivision", also: "county", file: true,
        props: { GEOID: "5110790400", NAME: "Blue Ridge district", BASENAME: "Blue Ridge", COUNTY: "107", LSADC: "27", FUNCSTAT: "N", lines: "census" },
        want: [/Blue Ridge district/, /Loudoun County/, /A magisterial district, as the U\.S\. Census Bureau maps it/,
          /Loudoun County elects its board of supervisors from districts whose names or number differ from these/],
        reject: [/Department of Elections' precinct lines/, /at large/]
      },
      {
        name: "the Census's copy in a county that elects its board at large says so",
        layer: "county-subdivision", also: "county", file: true,
        props: { GEOID: "5109190368", NAME: "Blue Grass district", BASENAME: "Blue Grass", COUNTY: "091", LSADC: "27", FUNCSTAT: "N", lines: "census" },
        want: [/Blue Grass district/, /Highland County/, /Highland County elects its board of supervisors at large/, /County or City card names the board/],
        reject: [/Department of Elections' precinct lines/, /names or number differ/]
      },
      {
        // the officials file refused: the card cannot say which bodies the
        // county elects by district, so it says only what the district is
        name: "with the officials file refused, a magisterial district says only what it is",
        layer: "county-subdivision", also: "county", file: true, refuseOfficials: true,
        props: { GEOID: "5110790400", NAME: "Blue Ridge district", BASENAME: "Blue Ridge", COUNTY: "107", LSADC: "27", FUNCSTAT: "N", lines: "census" },
        want: [/Blue Ridge district/, /A magisterial district, as the U\.S\. Census Bureau maps it/, /does not use them to say who represents this point/],
        reject: [/names or number differ/, /at large/]
      },
      {
        name: "an independent city is not divided into magisterial districts",
        layer: "county-subdivision", also: "county", file: true,
        props: { GEOID: "5151090020", NAME: "Alexandria city", BASENAME: "Alexandria", COUNTY: "510", LSADC: "25", FUNCSTAT: "F", lines: "census" },
        want: [/Alexandria city/, /belongs to no county and is not divided into magisterial districts/],
        reject: [/A magisterial district/, /does not divide this county/]
      },
      {
        name: "Arlington County, which the Census does not divide, says so",
        layer: "county-subdivision", also: "county", file: true,
        props: { GEOID: "5101390072", NAME: "Arlington", BASENAME: "Arlington", COUNTY: "013", LSADC: "00", FUNCSTAT: "F", lines: "census" },
        want: [/Arlington/, /does not divide this county into magisterial districts/],
        reject: [/A magisterial district/, /belongs to no county/]
      },
      {
        name: "a subdivision status the card does not carry says nothing about what it is",
        layer: "county-subdivision", also: "county", file: true,
        props: { GEOID: "5116390568", NAME: "Buffalo district", BASENAME: "Buffalo", COUNTY: "163", LSADC: "27", FUNCSTAT: "S", lines: "census" },
        want: [/Buffalo district/, /Rockbridge County/],
        reject: [/what this is/i, /A magisterial district/, /belongs to no county/, /does not divide this county/]
      },
      {
        name: "the School Division card names the division",
        layer: "school-district-unified", service: "School/MapServer/0",
        props: { GEOID: "5103240", NAME: "Richmond City Public Schools", STATE: "51" },
        want: [/Richmond City Public Schools/],
        reject: [/runs the lower grades/]
      },
      {
        name: "the elementary card names Lexington's division",
        layer: "school-district-elementary", service: "School/MapServer/2",
        props: { GEOID: "5102160", NAME: "Lexington City Public Schools", STATE: "51" },
        want: [/Lexington City Public Schools/],
        reject: [/Only the City of Lexington has a division of this kind/]
      },
      {
        // The point query answers nothing and the whole set holds only a
        // division far from the point, which is what the real service does
        // everywhere outside Lexington: the card must point at the School
        // Division card rather than say no division is here.
        name: "an elementary miss points at the School Division card",
        layer: "school-district-elementary", service: "School/MapServer/2",
        props: { GEOID: "5102160", NAME: "Lexington City Public Schools", STATE: "51" },
        far: FAR,
        want: [/Only the City of Lexington has a division of this kind/, /School Division card names the division/],
        reject: [/Lexington City Public Schools/]
      },
      {
        // the other half: a unified miss is Lexington, and says so
        name: "a School Division miss points at Lexington's elementary card",
        layer: "school-district-unified", service: "School/MapServer/0",
        props: { GEOID: "5103240", NAME: "Richmond City Public Schools", STATE: "51" },
        far: FAR,
        want: [/City of Lexington, whose school division runs the lower grades/, /School Division \(Elementary\) card names it/],
        reject: [/Richmond City Public Schools/]
      }
    ];

    for (const c of cases) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const layers = c.also ? `${c.also},${c.layer}` : c.layer;
      const page = await booted(context, `${BASE}#point=${POINT}&layers=${layers}`, async (p) => {
        if (c.refuseOfficials) await p.route("**/data/app/va-local-officials.json", (r) => r.abort());
        if (c.file) {
          // the Magisterial District layer reads one shipped file; the
          // fixture is one feature on the default ring, around the point
          await p.route("**/data/app/va-magisterial-districts.json", (r) => r.fulfill({
            status: 200, contentType: "application/json",
            body: JSON.stringify({ type: "FeatureCollection", features: [{ type: "Feature", properties: c.props,
              geometry: { type: "Polygon", coordinates: [esriPolygon(c.props).geometry.rings[0]] } }] })
          }));
          return;
        }
        await p.route(`**/data/app/tiles/${c.layer}.pmtiles`, (r) => r.abort());
        await p.route(`**/${c.service}/query**`, (r) => {
          const point = /esriGeometryPoint/.test(r.request().url());
          const body = c.far
            ? (point ? esriBody(null) : esriBody(c.props, c.far))
            : esriBody(c.props);
          r.fulfill({ status: 200, contentType: "application/json", body });
        });
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

  // 7b. THE MAGISTERIAL DISTRICT LAYER DRAWS THE DEPARTMENT'S LINES WHERE THE
  //     NAMES MATCH, read from the real shipped file at real points. In
  //     Dinwiddie County, at 37.07655,-77.7137, the Census's copy says District
  //     5 and the Department's lines say District 1, more than 400 m from
  //     either line (measured 2026-10-30, va/scripts/
  //     build_va_magisterial_districts.py). A layer drawing the Census's copy
  //     there would name District 5, so this is the check that the
  //     Department's lines are the ones drawn, and the Supervisor or Council
  //     District card at the same point must name the same district. In
  //     Leesburg, in Loudoun County, whose election districts differ from the
  //     Census's names, the card says the Census's copy is not them.
  {
    const DINWIDDIE = "37.07655,-77.71370";
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${DINWIDDIE}&layers=county,county-subdivision,supervisor-district`);
      const mag = await cardText(page, "county-subdivision");
      const sup = await cardText(page, "supervisor-district");
      const m = mag.text || "", su = sup.text || "";
      check("a Dinwiddie point names the Department's district, not the Census's copy's",
        !mag.error && /District 1/.test(m) && !/District 5/.test(m) && /Dinwiddie County/.test(m) &&
          /Department of Elections' precinct lines/.test(m),
        m.slice(0, 200));
      check("the Supervisor or Council District card names the same district there",
        !sup.error && /District 1/.test(su) && !/District 5/.test(su), su.slice(0, 160));
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=39.11570,-77.56360&layers=county,county-subdivision`);
      const info = await cardText(page, "county-subdivision");
      const t = info.text || "";
      check("a Loudoun point says the Census's copy is not the county's election districts",
        !info.error && /Leesburg district/.test(t) && /Loudoun County elects its board of supervisors from districts whose names or number differ/.test(t),
        t.slice(0, 200));
      await context.close();
    }
  }

  // 8. THE ZIP LAYER IS IN-STATE ONLY, AND THIS IS THE CHECK THAT PROVES IT.
  //    A ZCTA carries no STATE field, so this is the one layer here whose
  //    point query cannot be filtered server-side — and over a land border it
  //    does not answer with nothing, it answers with a real neighbouring ZIP.
  //    Measured against the live service 2026-10-29: Salisbury, Maryland gives
  //    21801 and Bristol, Tennessee 37620.
  //
  //    THE OUT-OF-STATE HALF IS THE ONE THAT DISCRIMINATES. The stub answers
  //    21801 whatever point is asked, so a regression that drops `coverage`
  //    shows the block AND renders a Maryland ZIP here, which is the harm a
  //    reader would see. The in-state half is equally load-bearing: coverage
  //    fails OPEN, so a test that only asserted hiding would also pass on a
  //    layer that had stopped working altogether.
  //
  //    The negative point is the worksheet's own, in the Atlantic and outside
  //    the state outline, which is what the coverage test reads.
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
          geometry: { rings: [[[-78, 36.5], [-75, 36.5], [-75, 38], [-78, 38], [-78, 36.5]]] }
        }]
      });
    }

    // in state: the layer answers, and answers from the stub
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=zip-code`, async (p) => {
        // the layer is answered from a tile archive; refusing it sends the
        // card to the census loader, which this stub answers
        await p.route("**/data/app/tiles/zip-code.pmtiles", (r) => r.abort());
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("23219") }));
      });
      const info = await cardText(page, "zip-code");
      check("zip-code answers inside Virginia (coverage fails open, so this half matters)",
        !info.error && /23219/.test(info.text || ""),
        (info.text || "").slice(0, 90));
      await context.close();
    }

    // out of state: the layer HIDES, and the stubbed ZIP never renders
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${NEGATIVE_POINT}&layers=zip-code`, async (p) => {
        await p.route("**/data/app/tiles/zip-code.pmtiles", (r) => r.abort());
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("21801") }));
      });
      const hidden = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-zip-code");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === true;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const info = await cardText(page, "zip-code");
      const leaked = /21801/.test(info.text || "");
      const stillOn = await page.evaluate(
        (n) => window[n].state.layersOn["zip-code"] === true, EXPORTS_NAME);
      check("zip-code hides outside Virginia rather than naming a Maryland ZIP",
        hidden && !leaked && stillOn,
        `hidden=${hidden} leaked=${leaked} layersOn=${stillOn} text=${(info.text || "").slice(0, 90)}`);
      await context.close();
    }
  }

  // 9. TRIBAL GOVERNMENT. The nation, its seat, the land and the council
  //    expected are read from the shipped files at the point, so a weekly
  //    council refresh moves the expectation with the file; what is asserted
  //    is that each card agrees with them.
  //      - The Pamunkey Reservation names the tribe, its seat, the land,
  //        every member of the council its own page names, the date and page
  //        they come from, and says no council seat belongs to this land.
  //      - The Mattaponi Reservation names the tribe as the Commonwealth's
  //        list does, says the Commonwealth and not the United States
  //        recognizes it, names its council with the assistant chief's note
  //        and links the Commonwealth's list.
  //      - The Rappahannock Trust Land names nobody and says why, and says
  //        the land was not counted in 2020.
  //      - The councils file is refused: the land still answers, naming the
  //        tribe and nobody on its council.
  //      - The State Capitol is on no tribal land, and the card says so in
  //        the layer's own words.
  //    Each point is the pole of inaccessibility of the piece's largest part
  //    as the shipped file draws it (shapely polylabel, 2026-10-30), 197 to
  //    833 m from its edge.
  {
    const areas = shipped("tribal-areas.json");
    const councils = shipped("tribal-councils.json");
    const PAMUNKEY = "37.57306,-77.00826";
    const MATTAPONI = "37.66191,-76.91471";
    const RAPPAHANNOCK = "37.89954,-77.02804";
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
      // the footer link (primaryLink) sits beside the card body, in the
      // layer's block, so the links are read from the whole block
      const links = await page.evaluate(() => {
        const card = document.getElementById("card-tribal-government");
        const block = (card && card.closest(".layer-block")) || card;
        return block ? Array.from(block.querySelectorAll("a[href]")).map((a) =>
          ({ text: (a.textContent || "").trim(), href: a.getAttribute("href") })) : [];
      });
      await context.close();
      return { text: card.text || "", error: card.error, links,
               by: (l) => (fields.find((f) => f.label === l) || {}).value || "" };
    };

    {
      const land = propsAt(areas, PAMUNKEY);
      const p = land[0] || {};
      const council = (councils[p.aiannh] || {}).roster || [];
      const c = await at(PAMUNKEY);
      check("the Pamunkey Reservation names the tribe, its seat, the land and its whole council, and where the names come from",
        land.length === 1 && council.length > 0 && !c.error &&
          c.by("Tribal government") === p.nation && p.nation === "Pamunkey Indian Tribe" &&
          c.by("Seat of government") === p.seat && p.seat === "King William, VA" &&
          c.by("Land") === "Pamunkey (state) Reservation" &&
          council.every((m) => c.text.includes(m.name)) &&
          c.text.includes("Council") && c.text.includes("From the nation's own council page") &&
          c.text.includes("Where these names come from") &&
          c.by("Districts drawn here").indexOf("no council seat") !== -1 &&
          !c.by("Why no names") && !c.by("Recognized by"),
        `land here=${land.length} council=${council.length} ${JSON.stringify(c.text.slice(0, 200))}`);
    }

    {
      const land = propsAt(areas, MATTAPONI);
      const p = land[0] || {};
      const council = (councils[p.aiannh] || {}).roster || [];
      const noted = council.filter((m) => m.note);
      const c = await at(MATTAPONI);
      check("the Mattaponi Reservation says the Commonwealth recognizes the tribe, names its whole council and links the Commonwealth's list",
        land.length === 1 && council.length > 0 && noted.length > 0 && !c.error &&
          c.by("Tribal government") === "Mattaponi Tribe" &&
          c.by("Seat of government") === "West Point, VA" &&
          c.by("Recognized by") === p.recognition &&
          c.by("Recognized by").indexOf("Commonwealth of Virginia") !== -1 &&
          c.by("Recognized by").indexOf("not by the federal government") !== -1 &&
          council.every((m) => c.text.includes(m.name)) &&
          noted.every((m) => c.text.includes(m.note)) &&
          c.links.some((l) => l.href === p.recognitionUrl) &&
          c.links.some((l) => l.href === p.url),
        `land here=${land.length} council=${council.length} links=${JSON.stringify(c.links.map((l) => l.href))} ${JSON.stringify(c.text.slice(0, 200))}`);
    }

    {
      const land = propsAt(areas, RAPPAHANNOCK);
      const p = land[0] || {};
      const c = await at(RAPPAHANNOCK);
      check("the Rappahannock Trust Land names nobody, says why, and says the land was not counted in 2020",
        land.length === 1 && !councils[p.aiannh] && !c.error &&
          c.by("Tribal government") === "Rappahannock Tribe, Inc." &&
          c.by("Land") === "Rappahannock Trust Land" &&
          c.by("Why no names") === p.rosterWhy && c.by("Why no names").indexOf("names no council") !== -1 &&
          c.by("Population").indexOf("Not counted") !== -1 &&
          !c.text.includes("From the nation's own council page"),
        `land here=${land.length} ${JSON.stringify(c.text.slice(0, 200))}`);
    }

    {
      const p = propsAt(areas, PAMUNKEY)[0] || {};
      const council = (councils[p.aiannh] || {}).roster || [];
      const c = await at(PAMUNKEY, async (pg) => {
        await pg.route("**/data/app/tribal-councils.json", (r) => r.fulfill({ status: 503, body: "down" }));
      });
      const named = council.filter((m) => c.text.includes(m.name)).map((m) => m.name);
      check("the Tribal Government card still names the tribe, and names nobody on its council, when the councils file fails",
        !c.error && c.by("Tribal government") === "Pamunkey Indian Tribe" &&
          council.length > 0 && named.length === 0,
        `named=${named.slice(0, 2)} ${JSON.stringify(c.text.slice(0, 160))}`);
    }

    {
      const off = await at(POINT);
      check("a point off tribal land is told so in the layer's own words",
        propsAt(areas, POINT).length === 0 &&
          off.text.indexOf("not on tribal land") !== -1 && off.text.indexOf("3 tribal areas") !== -1,
        JSON.stringify(off.text.slice(0, 120)));
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
