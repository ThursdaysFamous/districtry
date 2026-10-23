// Headless boot + behaviour smoke test, run in CI on every pull request
// (.github/workflows/smoke-test.yml). Serves the real index.html and drives it
// in Chromium via Playwright — the check the README's "Validation" section
// describes and that OPTIMIZATION_PLAYBOOK item 5 asked to actually commit.
//
// It deliberately depends only on the app shell (Leaflet from its CDN) and the
// same-origin data/app/*.json files — never on the live district APIs, which
// are flaky/blocked in CI. The four same-origin anchors (County, U.S. House,
// Missouri Senate and Missouri House) are the deterministic ground truth,
// and every live service a check needs is stubbed.
//
// Run locally against a static server:
//     python3 -m http.server 8000 &
//     npm install playwright && BASE_URL=http://localhost:8000/mo/ node mo/scripts/smoke_test.mjs
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
const POINT = "38.57910,-92.17290"; // Missouri State Capitol, 201 W. Capitol Avenue, Jefferson City, Cole County
const OFFLINE = ["county", "us-house", "mo-senate", "mo-house"];
const EXPECT_DISTRICT = { "county": "Cole County", "us-house": "3", "mo-senate": "6", "mo-house": "60" };
const NEGATIVE_POINT = "38.61560,-95.26780"; // Franklin County, Kansas, near Ottawa, about 57 km west of the Missouri line — outside Missouri and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-21: TIGERweb's state and county layers name Kansas and Franklin County here (control: the State Capitol returns Missouri and Cole County), and none of the state's shipped boundary files contains it. MISSOURI HAS NO COAST, SO THIS POINT IS ON A NEIGHBOUR'S LAND AND WILL HAVE TO MOVE: Iowa, Illinois, Kentucky, Tennessee, Arkansas and Oklahoma are live already, so Kansas and Nebraska are the only neighbours left, and the change that makes either one live moves this point to the other, the way Kentucky's go-live moved Indiana's.
const APP_NAME = "districtry Missouri";
const EXPECT_LAYERS = 13;
// ==== GENERATED:END smoke-config ====
// Instance constants this file owns (the worksheet emits the block above).
const EXPORTS_NAME = "MissouriExplorer";
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
  geometry: { type: "Point", coordinates: [-92.17290, 38.57910] },
  properties: {
    // the typed number: an answer without it shows the street instead of
    // a row (ENGINE geocoder-search runAddressSearch)
    housenumber: "16",
    street: "W Jones St",
    city: "Capital City",
    state: "Missouri",
    postcode: "00000"
  }
};
// Contract stubs (their consuming checks are reference-fork scenarios,
// dropped from this instance's body):
const GAP_PROBE = { county: "statewide", label: "Statewide", lat: 38.57910, lng: -92.17290 };
const MOVE_POINT = { lat: 0, lng: 0, district: "0" };
const STRAGGLER_FILE = "data/app/state-counties.json";
const STRAGGLER_POINT = "0,0";
// Layers expected to HIDE (not merely report no district) at NEGATIVE_POINT.
// None of the four anchors declares a coverage() test, so none hide — they
// all take the honest "no district here" branch instead.
const NEGATIVE_HIDDEN = [];
// Check 10's points: Christian's from its larger district's pole of
// inaccessibility, Henry's the one check 9 uses.
const CHRISTIAN_POINT = "36.95028,-93.04376";
const LAWRENCE_POINT = "36.99024,-93.67586";
const CASS_POINT = "38.7968,-94.45476";
// Inside the Census's 2020 Marshall 4 precinct, the half of Marshall township
// Saline's clerk lists in the Northern District, 4.1 km from any edge.
const SALINE_POINT = "39.1534,-93.246";
// Perry's Second District, its pole of inaccessibility (shapely polylabel).
const PERRY_POINT = "37.67846,-89.69876";
const HENRY_POINT = "38.38256,-93.69450";
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
  //     MISSOURI HAS EIGHT NEIGHBOURS, AND THE FLEET SERVES SIX OF THEM. A
  //     click a little way inside each live neighbour must open that
  //     neighbour's app: Bloomfield, Iowa; Carbondale, Illinois; Paducah,
  //     Kentucky; Union City, Tennessee; Jonesboro, Arkansas; and Miami,
  //     Oklahoma. Measured against fleet-outlines.json on 2026-10-21, each lies
  //     inside its own state's outline and no other, 17.3, 26.4, 46.3, 22.2,
  //     34.0 and 23.0 km from this app's coverage ring. This instance answers
  //     its own side from the coverage ring the wash retained, with no fetch,
  //     and it works while this instance is dark because the fleet file names
  //     only live apps. Chicago proves the file is still read for ground far
  //     from here.
  //
  //     KANSAS AND NEBRASKA ARE DELIBERATELY NOT CASES. Nobody serves them
  //     today, so a click there stays here; but the fleet is meant to reach
  //     every state, and a "stays here" case in either would start failing the
  //     day it goes live, in a change that is about another state. The
  //     negative point carries that half instead (1a2-ii), and it is the one
  //     thing in this file that must move when Kansas goes live (WATCH.md).
  {
    const cases = [
      { name: "Chicago", lat: 41.8825, lng: -87.6285, want: "https://districtry.com/il/" },
      { name: "Bloomfield, Iowa", lat: 40.7517, lng: -92.4149, want: "https://districtry.com/ia/" },
      { name: "Carbondale, Illinois", lat: 37.7273, lng: -89.2168, want: "https://districtry.com/il/" },
      { name: "Paducah, Kentucky", lat: 37.0834, lng: -88.6000, want: "https://districtry.com/ky/" },
      { name: "Union City, Tennessee", lat: 36.4243, lng: -89.0570, want: "https://districtry.com/tn/" },
      { name: "Jonesboro, Arkansas", lat: 35.8423, lng: -90.7043, want: "https://districtry.com/ar/" },
      { name: "Miami, Oklahoma", lat: 36.8745, lng: -94.8775, want: "https://districtry.com/ok/" },
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
      check(`a click on ${c.name} from Missouri opens ${c.want} with the point`, !!went, went || page.url());
      await context.close();
    }
  }

  // 1a2-ii. The half that keeps 1a2 honest: the negative point, in Franklin
  //     County, Kansas, about 57 km west of the Missouri line, is outside every
  //     outline in the fleet, so the click must stay HERE. A route to a sibling would be
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
    check("a click in Kansas, outside every app's outline, stays in this app",
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
    for (const [id, file] of [["mo-senate", "mo-senate-members.json"], ["mo-house", "mo-house-members.json"]]) {
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
  //     and names nobody. Senate District 10 read vacant on 2026-10-21; the
  //     point is the shipped district's pole of inaccessibility (shapely
  //     polylabel), about 27.6 km from its nearest edge. Where a later refresh
  //     seats a senator there, the check asserts that senator is named
  //     instead, so a filled seat passes and a wrong name still fails.
  {
    const SD10 = "39.24005,-91.17335";
    const rec = shipped("mo-senate-members.json")["10"] || {};
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${SD10}&layers=mo-senate`);
    const info = await cardText(page, "mo-senate");
    const text = info.text || "";
    const others = Object.entries(shipped("mo-senate-members.json"))
      .filter(([d, r]) => d !== "10" && r.name && text.includes(r.name)).map(([, r]) => r.name);
    const ok = rec.vacant
      ? /\bVacant\b/.test(text) && !!rec.vacantWhy && text.includes(rec.vacantWhy)
      : !!rec.name && text.includes(rec.name);
    check(rec.vacant
        ? "mo-senate says District 10 is vacant, in the chamber's own words, and names nobody"
        : "mo-senate names District 10's senator now that the chamber lists one",
      !info.error && /District 10\b/.test(text) && ok && others.length === 0,
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
  //    fire-station is 2,578 points in Missouri's envelope (measured
  //    2026-10-21), already past the 2,000-record cap the service reports as
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
      attributes: { NAME: `FAR STATION ${i}`, ADDRESS: "1 Far Rd", CITY: "Kirksville", STATE: "MO", ZIPCODE: "63501" },
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
                              CITY: "Jefferson City", STATE: "MO", ZIPCODE: "65101" },
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
      /Jefferson City, MO/.test(text), text.slice(0, 140));
    await context.close();
  }

  // 7. THE LIVE TIGERWEB FABRIC CARDS, STUBBED — and stubbed on purpose rather
  //    than anchored. The worksheet's OFFLINE anchors are same-origin only,
  //    which is this test's own stated contract, and these layers fetch the
  //    Census live: asserting a card against somebody else's server makes the
  //    test fail on their outage and on any network that intercepts TLS.
  //
  //    NO TILE ARCHIVE SHIPS FOR THESE LAYERS YET (the mirror is a go-live
  //    step, mo/WATCH.md). Each case refuses its layer's archive anyway, so
  //    the day one ships, the stub still decides the card and a case that
  //    exists in no archive (an affix no table carries) keeps working.
  //
  //    WHAT IS WORTH TESTING IS THIS INSTANCE'S OWN CODE, and none of it is
  //    exercised by a live fetch that happens to work. Each claim below is
  //    wrong in a way a reader would see:
  //
  //    (a) The municipality card states the style the Census records — a
  //        CITY, a TOWN or a VILLAGE, Missouri's three — and an affix the card
  //        does not know produces NO type row rather than an improvised one.
  //    (b) A place the Census records as inactive (FUNCSTAT I, 11 of
  //        Missouri's 947, measured 2026-10-21) drops the type row, says what
  //        the Census records, and offers no mayor and council.
  //    (c) The City of St. Louis belongs to no county, so its card must not
  //        say "alongside the county", and it says the County card names its
  //        officials.
  //    (d) The township card says what each of the five functional statuses
  //        Missouri's 1,394 county subdivisions carry means, names the county
  //        from the app's own county file, and prints no Government row for a
  //        status it does not know.
  //    (e) The two school tilings partition the state, so each answers under
  //        its own label, and an elementary miss points at the unified card
  //        rather than saying no district is here.
  {
    function esriPolygon(props, ring) {
      return {
        attributes: props,
        geometry: { rings: [ring || [[-93.0, 38.0], [-91.5, 38.0], [-91.5, 39.0], [-93.0, 39.0], [-93.0, 38.0]]] }
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
    const COUSUB = "Places_CouSub_ConCity_SubMCD/MapServer/1";
    const cases = [
      {
        name: "a city names itself a city, alongside the county",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2937000", NAME: "Jefferson City city", BASENAME: "Jefferson City", STATE: "29", LSADC: "25", FUNCSTAT: "A" },
        want: [/Jefferson City city/, /Incorporated city — a general-purpose local government over this point, alongside the county/, /Not named here/],
        reject: [/Status/, /Incorporated town/, /Incorporated village/, /County card names/]
      },
      {
        name: "a town names itself a town, not a city",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2902044", NAME: "Arrow Rock town", BASENAME: "Arrow Rock", STATE: "29", LSADC: "43", FUNCSTAT: "A" },
        want: [/Arrow Rock town/, /Incorporated town/],
        reject: [/Incorporated city/, /Incorporated village/]
      },
      {
        name: "a village names itself a village",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2981016", NAME: "Wooldridge village", BASENAME: "Wooldridge", STATE: "29", LSADC: "47", FUNCSTAT: "A" },
        want: [/Wooldridge village/, /Incorporated village/],
        reject: [/Incorporated city/, /Incorporated town/]
      },
      {
        name: "an affix the card does not carry prints NO type row",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2999999", NAME: "Nowhere borough", BASENAME: "Nowhere", STATE: "29", LSADC: "21", FUNCSTAT: "A" },
        want: [/Nowhere borough/],
        reject: [/Incorporated city/, /Incorporated town/, /Incorporated village/]
      },
      {
        name: "an inactive place drops its type row, says what the Census records, and offers no mayor",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2940142", NAME: "Lakeside city", BASENAME: "Lakeside", STATE: "29", LSADC: "25", FUNCSTAT: "I" },
        want: [/Lakeside city/, /records this place's government as inactive/, /The county is the general-purpose local government here/],
        reject: [/Incorporated city/, /Not named here/, /Your mayor and council/]
      },
      {
        name: "the City of St. Louis says it belongs to no county, never alongside one, and that the County card names its officials",
        layer: "municipality", service: PLACES,
        props: { GEOID: "2965000", NAME: "St. Louis city", BASENAME: "St. Louis", STATE: "29", LSADC: "25", FUNCSTAT: "A" },
        want: [/St\. Louis city/, /Independent city — the City of St\. Louis belongs to no county/, /The County card names them/],
        reject: [/alongside the county/, /Not named here/, /Status/]
      },
      {
        name: "a township in a county organized into townships is an active government of its own",
        layer: "county-subdivision", also: "county", service: COUSUB,
        props: { GEOID: "2901112736", NAME: "Central township", BASENAME: "Central", STATE: "29", COUNTY: "011", LSADC: "44", FUNCSTAT: "A" },
        want: [/Central township/, /Barton County/, /An active government of its own/, /This app does not name them yet/],
        reject: [/inactive/, /no government of its own/]
      },
      {
        name: "a partly consolidated township says so",
        layer: "county-subdivision", also: "county", service: COUSUB,
        props: { GEOID: "2901113897", NAME: "City township", BASENAME: "City", STATE: "29", COUNTY: "011", LSADC: "44", FUNCSTAT: "B" },
        want: [/City township/, /Barton County/, /partly consolidated with another government/],
        reject: [/An active government of its own/]
      },
      {
        name: "an inactive township says no government is operating",
        layer: "county-subdivision", also: "county", service: COUSUB,
        props: { GEOID: "2905712196", NAME: "Cedar township", BASENAME: "Cedar", STATE: "29", COUNTY: "057", LSADC: "44", FUNCSTAT: "I" },
        want: [/Cedar township/, /Dade County/, /None operating/, /records this township's government as inactive/],
        reject: [/An active government of its own/]
      },
      {
        name: "a township with no government says the county governs there",
        layer: "county-subdivision", also: "county", service: COUSUB,
        props: { GEOID: "2900104546", NAME: "Benton township", BASENAME: "Benton", STATE: "29", COUNTY: "001", LSADC: "44", FUNCSTAT: "N" },
        want: [/Benton township/, /Adair County/, /a legal area with no government of its own/, /the county governs here/],
        reject: [/An active government of its own/, /inactive/]
      },
      {
        name: "the City of St. Louis is not divided into townships",
        layer: "county-subdivision", also: "county", service: COUSUB,
        props: { GEOID: "2951065000", NAME: "St. Louis city", BASENAME: "St. Louis", STATE: "29", COUNTY: "510", LSADC: "25", FUNCSTAT: "F" },
        want: [/St\. Louis city/, /belongs to no county and is not divided into townships/],
        reject: [/no government of its own/, /An active government of its own/]
      },
      {
        name: "a township status the card does not carry prints NO Government row",
        layer: "county-subdivision", also: "county", service: COUSUB,
        props: { GEOID: "2900104546", NAME: "Benton township", BASENAME: "Benton", STATE: "29", COUNTY: "001", LSADC: "44", FUNCSTAT: "S" },
        want: [/Benton township/, /Adair County/],
        reject: [/Government/]
      },
      {
        name: "the unified school district card names the district",
        layer: "school-district-unified", service: "School/MapServer/0",
        props: { GEOID: "2916190", NAME: "Jefferson City Public Schools", STATE: "29" },
        want: [/Jefferson City Public Schools/],
        reject: [/elementary school districts rather than a unified one/]
      },
      {
        name: "the elementary school district card names the district",
        layer: "school-district-elementary", service: "School/MapServer/2",
        props: { GEOID: "2912720", NAME: "Gasconade C-4 School District", STATE: "29" },
        want: [/Gasconade C-4 School District/],
        reject: [/unified school district rather than an elementary one/]
      },
      {
        // The point query answers nothing and the whole set holds only a
        // district far from the point, which is what the real service does at
        // a point in a unified district: the card must point at the unified
        // card rather than say no school district is here.
        name: "an elementary miss points at the unified card",
        layer: "school-district-elementary", service: "School/MapServer/2",
        props: { GEOID: "2912720", NAME: "Gasconade C-4 School District", STATE: "29" },
        far: [[-91.9, 36.6], [-91.7, 36.6], [-91.7, 36.8], [-91.9, 36.8], [-91.9, 36.6]],
        want: [/in a unified school district rather than an elementary one/, /School District \(Unified\) card names it/],
        reject: [/Gasconade C-4 School District/]
      }
    ];

    for (const c of cases) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const layers = c.also ? `${c.also},${c.layer}` : c.layer;
      const page = await booted(context, `${BASE}#point=${POINT}&layers=${layers}`, async (p) => {
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

  // 8. THE ZIP LAYER IS IN-STATE ONLY, AND THIS IS THE CHECK THAT PROVES IT.
  //    A ZCTA carries no STATE field, so this is the one layer here whose
  //    point query cannot be filtered server-side — and over a land border it
  //    does not answer with nothing, it answers with a real neighbouring ZIP.
  //    Measured against the live service 2026-10-21: Quincy, Illinois gives
  //    62301 and Fort Scott, Kansas 66701.
  //
  //    THE OUT-OF-STATE HALF IS THE ONE THAT DISCRIMINATES. The stub answers
  //    66067 (Ottawa, Kansas) whatever point is asked, so a regression that
  //    drops `coverage` shows the block AND renders a Kansas ZIP here, which
  //    is the harm a reader would see. The in-state half is equally
  //    load-bearing: coverage fails OPEN, so a test that only asserted hiding
  //    would also pass on a layer that had stopped working altogether.
  //
  //    The negative point is the worksheet's own, in Kansas and outside the
  //    state outline, which is what the coverage test reads. It moves with the
  //    worksheet the day Kansas goes live, and this check moves with it.
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
          geometry: { rings: [[[-96, 38], [-91, 38], [-91, 39], [-96, 39], [-96, 38]]] }
        }]
      });
    }

    // in state: the layer answers, and answers from the stub
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=zip-code`, async (p) => {
        // no archive ships yet; refused so the stub decides the day one does
        await p.route("**/data/app/tiles/zip-code.pmtiles", (r) => r.abort());
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("65101") }));
      });
      const info = await cardText(page, "zip-code");
      check("zip-code answers inside Missouri (coverage fails open, so this half matters)",
        !info.error && /65101/.test(info.text || ""),
        (info.text || "").slice(0, 90));
      await context.close();
    }

    // out of state: the layer HIDES, and the stubbed ZIP never renders
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${NEGATIVE_POINT}&layers=zip-code`, async (p) => {
        await p.route("**/data/app/tiles/zip-code.pmtiles", (r) => r.abort());
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("66067") }));
      });
      const hidden = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-zip-code");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === true;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const info = await cardText(page, "zip-code");
      const leaked = /66067/.test(info.text || "");
      const stillOn = await page.evaluate(
        (n) => window[n].state.layersOn["zip-code"] === true, EXPORTS_NAME);
      check("zip-code hides outside Missouri rather than naming a Kansas ZIP",
        hidden && !leaked && stillOn,
        `hidden=${hidden} leaked=${leaked} layersOn=${stillOn} text=${(info.text || "").slice(0, 90)}`);
      await context.close();
    }
  }

  // 9. EVERY COUNTY'S OFFICIALS, on the County card. The names expected are
  //    read from the shipped roster (data/app/mo-county-officials.json) rather
  //    than written here, because the Secretary of State's next edition of
  //    the Missouri Roster changes them and a name in this file would fail a
  //    correct rebuild. Seven places, each for its own claim:
  //      - Cole, at the State Capitol: a county commission with a presiding
  //        commissioner and two district commissioners, the office the three
  //        share, the sentence sending the reader to the County Commission
  //        District layer (Cole's lines are drawn; in a county whose lines
  //        are not, the sentence says the app cannot yet tell which district
  //        commissioner represents the point), and the credit and link;
  //      - St. Louis County: a county executive first, then a seven-member
  //        council, with the e-mail address and telephone the roster prints
  //        beside each;
  //      - Jackson County: a nine-member legislature, and the county
  //        executive's office named with the reason no one is named for it
  //        (the recall the roster's edition predates);
  //      - the City of St. Louis: the mayor, the president of the Board of
  //        Aldermen, and the sentence saying the roster names no ward
  //        alderman;
  //      - Clay County: a seven-member commission;
  //      - St. Charles County: the council's own e-mail address, on the
  //        office block and on no member's row;
  //      - Henry County: an office the roster prints as vacant says Vacant.
  //    The points are poles of inaccessibility of each county as the shipped
  //    file draws it (shapely polylabel, 2026-10-21), 7 to 20 km from the
  //    nearest county line; Cole's is the State Capitol, 8 km inside it.
  {
    const roster = shipped("mo-county-officials.json");
    const drawnCommission = shipped("mo-commission-counties.json");
    const cases = [
      { point: POINT, geoid: "29051" },
      { point: "38.62140,-90.43781", geoid: "29189" },
      { point: "39.00899,-94.28434", geoid: "29095" },
      { point: "38.63635,-90.24007", geoid: "29510" },
      { point: "39.31909,-94.46437", geoid: "29047" },
      { point: "38.74051,-90.82706", geoid: "29183" },
      { point: "38.38256,-93.69450", geoid: "29083" },
    ];
    const BODY_WORDS = { commission: "commission", council: "council", legislature: "legislature", city: "Board" };
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
      const seats = o.seats || [];
      const officers = o.officers || [];
      const exe = o.executive || null;
      const people = seats.concat(officers, exe && exe.name ? [exe] : []);
      const label = (p) => p.vacant ? "Vacant" : p.name;
      const unnamed = seats.filter((s) => !text.includes(label(s)) || !text.includes(s.seat)).map(label)
        .concat(officers.filter((p) => !text.includes(label(p)) || !text.includes(p.office)).map(label));
      const unphoned = people.filter((p) => p.phone && !shown.includes(p.phone)).map(label);
      const unmailed = people.filter((p) => p.email && !got.mailto.includes(String(p.email).toLowerCase())).map(label);
      // The title is a section label, which the card's stylesheet sets in
      // capitals, so it is read from the DOM's own text rather than innerText.
      const exeOk = !exe ? true
        : exe.name ? text.includes(exe.name) && got.all.includes(exe.title)
        : !!exe.notNamed && text.includes(exe.notNamed);
      const officeLabel = `The ${BODY_WORDS[o.kind]}'s office`;
      const officeOk = (o.boardAddress || o.boardPhone || o.boardEmail)
        ? got.all.includes(officeLabel) && (!o.boardAddress || got.all.includes(o.boardAddress)) &&
            (!o.boardPhone || plain(got.all).includes(o.boardPhone)) &&
            (!o.boardEmail || got.officeMail.includes(o.boardEmail.toLowerCase()))
        : !/'s office/.test(got.all);
      const district = seats.filter((s) => !s.countywide);
      const whichOk = o.kind === "commission"
        ? (district.length === 2 && Object.prototype.hasOwnProperty.call(drawnCommission, c.geoid)
            ? text.includes("The County Commission District layer draws the line between them")
            : district.length === 2
            ? text.includes("This app does not have a map of the line between them yet")
            : text.includes("This app does not have a map of those districts yet, so it cannot say which of them represents this point."))
        : o.kind === "city"
          ? text.includes("This app does not draw the city's wards yet") && (!o.bodyNote || text.includes(o.bodyNote))
          : text.includes("The county executive is elected by the whole county.") &&
              text.includes(`Each of the ${seats.length} members of the ${o.kind}`);
      const creditOk = /Where these names come from/i.test(text) &&
        text.includes(`read on ${longDate(o.read)}`) && got.footer.includes(o.sourceUrl);
      check(`the County card in ${o.county} names ${exe && exe.name ? "its " + exe.title + ", " : ""}every member of the ${o.body} and every other official the roster prints, with their own telephones and e-mail addresses and the roster's credit`,
        !info.error && text.includes(o.county) && seats.length > 0 && unnamed.length === 0 &&
          unphoned.length === 0 && unmailed.length === 0 && exeOk && officeOk && whichOk && creditOk,
        `unnamed=${unnamed.slice(0, 3)} unphoned=${unphoned.slice(0, 2)} unmailed=${unmailed.slice(0, 2)} ` +
          `exe=${exeOk} office=${officeOk} which=${whichOk} credit=${creditOk} ${text.slice(0, 100)}`);
      await context.close();
    }
  }

  // 9b. The roster is refused, and the County card must degrade to a sentence
  //    naming nobody while the county itself still classifies: a roster
  //    failure is not the layer's failure.
  {
    const cole = shipped("mo-county-officials.json")["29051"];
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=county`, async (p) => {
      await p.route("**/data/app/mo-county-officials.json", (r) => r.fulfill({ status: 503, body: "down" }));
    });
    const info = await cardText(page, "county");
    const text = info.text || "";
    const named = (cole.seats || []).concat(cole.officers || [])
      .filter((p) => p && p.name && text.includes(p.name)).map((p) => p.name);
    check("the County card degrades to naming nobody when the list of officials fails",
      !info.error && /Cole County/.test(text) && /did not load, so no one is named here/.test(text) &&
        named.length === 0,
      `named=${named.slice(0, 2)} text=${text.slice(0, 90)}`);
    await context.close();
  }

  // 10. THE COUNTY COMMISSION DISTRICT LAYER, drawn only in the counties whose
  //     own map viewer or download publishes the line
  //     (data/app/mo-commission-districts.json). The district, its
  //     commissioner and the presiding commissioner are all read from the
  //     shipped files, so a rebuild or a new roster moves the expectation.
  //       - Cole, at the State Capitol, drawn from MidMO GIS's download, and
  //         Christian, drawn from its map viewer, and Lawrence, drawn from
  //         whole TIGER townships and pointed to by its clerk, and Cass,
  //         drawn from the file its GIS office sent: the card names the district
  //         and its commissioner, the presiding commissioner, where the line
  //         comes from and that it has not been checked against the
  //         county's election records.
  //       - Henry, whose lines this app does not draw: the layer HIDES and
  //         stays switched on. This is the half that discriminates: without
  //         `coverage` the card would say no district is drawn there, about a
  //         county that has two.
  //       - The roster is refused: the district still answers and names
  //         nobody.
  //     Christian's point is the pole of inaccessibility of its larger
  //     district as the shipped file draws it, Lawrence's of its Eastern
  //     District and Cass's of its District 2 (shapely polylabel,
  //     2026-10-23), and Saline's lies in the split Marshall township;
  //     Henry's is check 9's.
  {
    const fc = shipped("mo-commission-districts.json");
    const roster = shipped("mo-county-officials.json");
    const drawn = shipped("mo-commission-counties.json");
    const seatOf = (p) => ((roster[p.countyfips] || {}).seats || []).find((s) => s.seat === p.seat) || {};
    const presidingOf = (p) => ((roster[p.countyfips] || {}).seats || []).find((s) => s.countywide) || {};
    for (const pt of [POINT, CHRISTIAN_POINT, LAWRENCE_POINT, CASS_POINT, SALINE_POINT, PERRY_POINT]) {
      const at = propsAt(fc, pt);
      const p = at[0] || {};
      const mine = seatOf(p), pres = presidingOf(p);
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${pt}&layers=county-commissioner`);
      const info = await cardText(page, "county-commissioner");
      const text = info.text || "";
      const whereOk = p.source === "cole" ? text.includes("MidMO GIS")
        : p.source === "townships"
          ? text.includes("made of whole townships") &&
            text.includes(`clerk pointed this app to that map on ${longDate(p.pointedOn)}`)
          : p.source === "sent"
            ? text.includes(`GIS office sent them to this app on ${longDate(p.sentOn)}`)
          : p.source === "arcgis"
            ? text.includes(`${p.county}'s own map at SEMO GIS`) &&
              text.includes(`clerk pointed this app to that map on ${longDate(p.pointedOn)}`)
          : p.source === "listed"
            ? text.includes(`county clerk listed them, township by township and precinct by precinct on ${longDate(p.listedOn)}`) &&
              text.includes("2020 voting precinct lines")
          : text.includes(`${p.county}'s own map viewer`);
      check(`county-commissioner card in ${p.county || "a drawn county"} names the ${p.seat || "?"} and its commissioner, the presiding commissioner, and where the line comes from`,
        at.length === 1 && !!drawn[p.countyfips] && !info.error && !!mine.name && !!pres.name &&
          text.includes(p.seat) && text.includes(mine.name) && text.includes(pres.name) &&
          whereOk && (p.source === "sent" || p.source === "listed" || text.includes(`read on ${longDate(p.read)}`)) &&
          /has not checked this line against the precinct records/.test(text) &&
          /Where these names come from/.test(text),
        `districts here=${at.length} ${text.slice(0, 140)}`);
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${HENRY_POINT}&layers=county-commissioner`);
      const hidden = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-county-commissioner");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === true;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const stillOn = await page.evaluate(
        (n) => window[n].state.layersOn["county-commissioner"] === true, EXPORTS_NAME);
      check("county-commissioner hides in Henry County, whose lines are not drawn, and stays switched on",
        propsAt(fc, HENRY_POINT).length === 0 && !drawn["29083"] && hidden && stillOn,
        `hidden=${hidden} layersOn=${stillOn}`);
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=county-commissioner`, async (pg) => {
        await pg.route("**/data/app/mo-county-officials.json", (r) => r.fulfill({ status: 503, body: "down" }));
      });
      const info = await cardText(page, "county-commissioner");
      const text = info.text || "";
      const p = propsAt(fc, POINT)[0] || {};
      const cole = roster["29051"] || {};
      const named = (cole.seats || []).filter((s) => s.name && text.includes(s.name));
      check("county-commissioner still answers the district and names nobody when the list of officials fails",
        !info.error && !!p.seat && text.includes(p.seat) &&
          /did not load, so no one is named here/.test(text) && named.length === 0,
        `named=${named.length} ${text.slice(0, 100)}`);
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
console.log("\nAll smoke checks passed.");
