// Headless boot + behaviour smoke test, run in CI on every pull request
// (.github/workflows/smoke-test.yml). Serves the real index.html and drives it
// in Chromium via Playwright — the check the README's "Validation" section
// describes and that OPTIMIZATION_PLAYBOOK item 5 asked to actually commit.
//
// It deliberately depends only on the app shell (Leaflet from its CDN) and the
// same-origin data/app/*.json files — never on the live district APIs, which
// are flaky/blocked in CI. The four same-origin anchors (County, U.S. House,
// Utah Senate and House) are the deterministic ground truth,
// and every live service a check needs is stubbed.
//
// Run locally against a static server:
//     python3 -m http.server 8000 &
//     npm install playwright && BASE_URL=http://localhost:8000/ut/ node ut/scripts/smoke_test.mjs
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
const POINT = "40.77749,-111.88800"; // Utah State Capitol, 350 State Street, Salt Lake City, Salt Lake County
const OFFLINE = ["county", "us-house", "ut-senate", "ut-house"];
const EXPECT_DISTRICT = { "county": "Salt Lake County", "us-house": "1", "ut-senate": "8", "ut-house": "22" };
const NEGATIVE_POINT = "41.45000,-110.90000"; // Uinta County, Wyoming, north of Evanston and about 12 km east of the Utah line — outside Utah and inside permalink_gate, so the app answers a selection there and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names Wyoming here (control: the State Capitol returns Utah), and none of the state's shipped boundary files contains it. WYOMING'S OUTLINE HAS COVERED THIS POINT SINCE THE CHANGE THAT PUBLISHED WYOMING (batch 4 of the state-level launch, written 2026-11-12), which found it inside Wyoming's outline in fleet-outlines.json and no other, AND THE POINT STAYS: measured that day on a 0.05-degree grid, no ground in this app's gate lies more than 2 km from every outline in fleet-outlines.json, so there is nowhere left to move it to. It is still outside Utah and outside every shipped boundary file, which is all the checks that boot on it or select it ask, and a selection the app makes itself never leaves; the click that had to stay here became a Wyoming routing case in the same change, and the click-stays-here check went with it, the way Kentucky's and Tennessee's points stayed put once every neighbour was served.
const APP_NAME = "districtry Utah";
const EXPECT_LAYERS = 11;
// ==== GENERATED:END smoke-config ====
// Instance constants this file owns (the worksheet emits the block above).
const EXPORTS_NAME = "UtahExplorer";
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
  geometry: { type: "Point", coordinates: [-111.888, 40.77749] },
  properties: {
    // the typed number: an answer without it shows the street instead of
    // a row (ENGINE geocoder-search runAddressSearch)
    housenumber: "16",
    street: "W Jones St",
    city: "Capital City",
    state: "Utah",
    postcode: "00000"
  }
};
// Contract stubs (their consuming checks are reference-fork scenarios,
// dropped from this instance's body):
const GAP_PROBE = { county: "statewide", label: "Statewide", lat: 40.77749, lng: -111.888 };
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
      ["350 State St, Salt Lake City, UT 84103", "350 State St, Salt Lake City, UT 84103"],         // UT state code — never strip
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
  //     ALL SIX OF UTAH'S NEIGHBOURS ARE LIVE WHOLE-STATE APPS: Nevada and
  //     Arizona before it, Colorado in its own batch, and Idaho, Wyoming and
  //     New Mexico since the change that published them (batch 4 of the
  //     state-level launch). A click at each capitol must open that app, and
  //     so must a click at the negative point, in Uinta County, Wyoming,
  //     about 12 km from the Utah line: it was the click that had to stay
  //     HERE until Wyoming's go-live made it a case, and measured that day
  //     (2026-11-12) it lies inside Wyoming's outline in fleet-outlines.json
  //     and no other, as each capitol lies inside its own app's and no
  //     other.
  //     The stays-here check (1a2-ii) went with it, because measured the
  //     same day on a 0.05-degree grid no ground in this app's gate lies
  //     more than 2 km from every outline in fleet-outlines.json; the
  //     negative point stays where it is, since every check that still
  //     uses it boots or selects it here and none clicks it.
  //     This instance answers its own side from the state outline the wash
  //     retained, with no fetch.
  {
    const cases = [
      { name: "the Colorado State Capitol", lat: 39.73924, lng: -104.9848, want: "https://districtry.com/co/" },
      { name: "the Nevada State Capitol", lat: 39.16384, lng: -119.76637, want: "https://districtry.com/nv/" },
      { name: "the Arizona State Capitol", lat: 33.4481, lng: -112.097, want: "https://districtry.com/az/" },
      { name: "the Idaho State Capitol", lat: 43.61771, lng: -116.19975, want: "https://districtry.com/id/" },
      { name: "the New Mexico State Capitol", lat: 35.68226, lng: -105.93964, want: "https://districtry.com/nm/" },
      { name: "the negative point, in Uinta County, Wyoming", lat: 41.45, lng: -110.9, want: "https://districtry.com/wy/" },
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
      check(`a click on ${c.name} from Utah opens ${c.want} with the point`, !!went, went || page.url());
      await context.close();
    }
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
    // 2a. EACH ROSTER NAMES THE MEMBER, and the card carries what the roster
    //     holds: the name, the party (both chambers print one for every
    //     member), the office and, where the chamber prints one (the Senate
    //     does for most senators, the House for nobody), the member's e-mail
    //     address, which must open as a mailto link.
    //     The values expected are read from the shipped roster for each
    //     anchor district, so a weekly refresh that changes them changes what
    //     is expected. An office can sit behind a closed disclosure, which
    //     innerText leaves out, so the office is read from textContent.
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
    // A seat is a flat member record, or { seats, members } where a chamber
    // states every district in the several-member shape; each member named
    // must be on the card. A member's office line, or where the roster prints
    // none, the member's own telephone, must be on it too.
    const seatMembers = (rec) => Array.isArray(rec.members) ? rec.members : [rec];
    const digits = (v) => String(v || "").replace(/\D/g, "");
    const memberOk = (m, text, dom, needParty) =>
      !!m.name && text.includes(m.name) &&
      (needParty ? !!m.party && text.toLowerCase().includes(String(m.party).toLowerCase())
        : !m.party && !/\b(Republican|Democrat(ic)?)\b/.test(text)) &&
      ((m.capitolOffice || [])[0] ? dom.all.includes(m.capitolOffice[0])
        : !!digits(m.phone) && digits(dom.all).includes(digits(m.phone).slice(-7))) &&
      (!m.email || dom.mailto.includes(String(m.email).toLowerCase()));
    for (const [id, file, who, needParty] of [
      ["us-house", "congress-roster.json", "representative", true],
      ["ut-senate", "ut-senate-members.json", "senator", true],
      ["ut-house", "ut-house-members.json", "representative", true],
    ]) {
      const rec = shipped(file)[EXPECT_DISTRICT[id]] || {};
      const info = await cardText(page, id);
      const dom = await cardDom(id);
      const ms = seatMembers(rec);
      check(`${id} card names the ${who}${ms.length > 1 ? "s" : ""}, ${needParty ? "the party" : "no party"} and the office${ms.some((m) => m.email) ? ", and each e-mail address opens as a mailto link" : ""}`,
        !info.error && ms.length > 0 && ms.every((m) => memberOk(m, info.text, dom, needParty)),
        `names=${ms.map((m) => m.name).join("; ")} mailto=${JSON.stringify(dom.mailto)} ${info.text.slice(0, 90)}`);
    }
    await context.close();
  }

  // 2a2. A ROSTER THAT FAILS TO LOAD NAMES NOBODY, while the district still
  //     classifies: the chamber factory degrades to the district number and
  //     the chamber's own member list rather than inventing a name.
  {
    const id = "ut-house";
    const rec = shipped("ut-house-members.json")[EXPECT_DISTRICT[id]] || {};
    const names = (Array.isArray(rec.members) ? rec.members : [rec]).map((m) => m.name).filter(Boolean);
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=${id}`, async (p) => {
      await p.route("**/data/app/ut-house-members.json", (r) => r.fulfill({ status: 503, body: "down" }));
    });
    const info = await cardText(page, id);
    const text = info.text || "";
    check("ut-house still classifies and names nobody when its roster fails",
      !info.error && text.includes(EXPECT_DISTRICT[id]) &&
        names.length > 0 && names.every((n) => !text.includes(n)),
      text.slice(0, 120));
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
  //     coordinates. Headless desktop Chromium has no navigator.share, so this
  //     always exercises the popover path; Escape must close it.
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


  // 5. Base-map tile failure surfaces an honest, dismissible banner, instead
  //    of a silently gray map. Fail the CARTO tile CDN and assert the banner
  //    appears, then that dismissing it hides it.
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
  //    fire-station is 420 points in Utah's envelope (measured 2026-11-12),
  //    under the 2,000-record cap the service reports as HTTP 200 +
  //    exceededTransferLimit rather than an error, so more stations would put
  //    the rest on a second page. A loader that lost the pager would then drop
  //    real stations without a word while the nearest-3 card looked correct
  //    near whichever stations page one held. The source manifest's count row
  //    cannot see that, because returnCountOnly is not subject to
  //    maxRecordCount and answers the true count whatever the client does. This
  //    is the check that can.
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
      attributes: { NAME: `FAR STATION ${i}`, ADDRESS: "1 Far Rd", CITY: "St. George", STATE: "UT", ZIPCODE: "84770" },
      geometry: { x: -113.5684, y: 37.0965 },
    });
    const [lat, lng] = POINT.split(",").map(Number);
    const page = await booted(context, BASE, (p) =>
      p.route(/MapServer\/51\/query/, (route) => {
        const params = new URL(route.request().url()).searchParams;
        const offset = Number(params.get("resultOffset"));
        offsets.push(offset);
        fieldsAsked.push(params.get("outFields") || "");
        // ESRI JSON, not GeoJSON — the shape the app asks for (every ArcGIS
        // loader asks for f=json, engine/index.html/arcgis-loader.txt).
        const body = offset === 0
          ? { exceededTransferLimit: true, features: [far(1), far(2), far(3)] }
          : { features: [{
                attributes: { NAME: "PAGE TWO STATION", ADDRESS: "2 Second Page Way",
                              CITY: "Salt Lake City", STATE: "UT", ZIPCODE: "84114" },
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
      /Salt\ Lake\ City, UT/.test(text), text.slice(0, 140));
    await context.close();
  }

  // 7. THE TIGERWEB FABRIC CARDS, STUBBED — and stubbed on purpose rather
  //    than anchored. The worksheet's OFFLINE anchors are same-origin only,
  //    which is this test's own stated contract.
  //
  //    THESE LAYERS ARE ANSWERED FROM SAME-ORIGIN TILE ARCHIVES
  //    (scripts/mirror_tiger_tiles.py), and the stubs stay anyway: several
  //    cases below exist in no archive (an affix no table carries), so each
  //    case refuses its layer's archive and the stub decides the card, through
  //    the archive-failure path.
  //
  //    WHAT IS WORTH TESTING IS THIS INSTANCE'S OWN CODE. Each claim below is
  //    wrong in a way a reader would see:
  //
  //    (a) The City or Town card states the kind the Census records for an
  //        incorporated place, and an affix the card does not know produces
  //        NO type row rather than an improvised one.
  //    (b) A place the Census records as an inactive government says the
  //        county governs there rather than calling it a local government.
  //    (c) The school district card names the district.
  //    A point outside every incorporated place is held in 7c instead,
  //    against the shipped archive, because an empty stub answer is not what
  //    the service sends.
  {
    // a ring around the State Capitol, the point every case selects
    const RING = [[-112.14, 40.53], [-111.64, 40.53], [-111.64, 41.03], [-112.14, 41.03], [-112.14, 40.53]];
    function esriBody(props) {
      return JSON.stringify({
        geometryType: "esriGeometryPolygon",
        spatialReference: { wkid: 4326 },
        fields: Object.keys(props || {}).map((n) => ({ name: n, type: "esriFieldTypeString", alias: n })),
        features: props ? [{ attributes: props, geometry: { rings: [RING] } }] : []
      });
    }
    const PLACES = "Places_CouSub_ConCity_SubMCD/MapServer/4";
    const cases = [
      {
        name: "a city names itself an incorporated city",
        layer: "municipality", service: PLACES,
        props: { GEOID: "4967000", NAME: "Salt Lake City city", BASENAME: "Salt Lake City", STATE: "49", LSADC: "25", FUNCSTAT: "A" },
        want: [/Salt\ Lake\ City\ city/, /Incorporated city — a general-purpose local government over this point, alongside the county/, /Not named here/],
        reject: [/inactive government/]
      },
      {
        name: "a town names itself an incorporated town",
        layer: "municipality", service: PLACES,
        props: { GEOID: "4900650", NAME: "Alta town", BASENAME: "Alta", STATE: "49", LSADC: "43", FUNCSTAT: "A" },
        want: [/Alta\ town/, /Incorporated town — a general-purpose local government/, /Not named here/],
        reject: [/Incorporated city/]
      },
      {
        name: "an inactive town says the county governs there",
        layer: "municipality", service: PLACES,
        props: { GEOID: "4999997", NAME: "Example town", BASENAME: "Example", STATE: "49", LSADC: "43", FUNCSTAT: "I" },
        want: [/Example town/, /inactive government/, /The county governs here/],
        reject: [/a general-purpose local government over this point/]
      },
      {
        name: "an affix the card does not carry prints NO type row",
        layer: "municipality", service: PLACES,
        props: { GEOID: "4999999", NAME: "Nowhere borough", BASENAME: "Nowhere", STATE: "49", LSADC: "21", FUNCSTAT: "A" },
        want: [/Nowhere borough/],
        reject: [/local government over this point/]
      },
      {
        name: "the school district card names the district",
        layer: "school-district-unified", service: "School/MapServer/0",
        props: { GEOID: "4900870", NAME: "Salt Lake City School District", STATE: "49" },
        want: [/Salt Lake City School District/],
        reject: []
      }
    ];

    for (const c of cases) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=${c.layer}`, async (p) => {
        await p.route(`**/data/app/tiles/${c.layer}.pmtiles`, (r) => r.abort());
        await p.route(`**/${c.service}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: esriBody(c.props) }));
      });
      const info = await cardText(page, c.layer);
      const text = info.text || "";
      const missing = c.want.filter((re) => !re.test(text));
      const present = c.reject.filter((re) => re.test(text));
      check(c.name, !info.error && (!c.empty || info.empty) && missing.length === 0 && present.length === 0,
        missing.length || present.length
          ? `missing=${missing} unwanted=${present} text=${text.slice(0, 160)}`
          : text.slice(0, 90));
      await context.close();
    }
  }
  // 7b. THE ARCHIVES THEMSELVES ANSWER, WITH THE CENSUS UNREACHABLE. 7 holds
  //     the card code to a stub; this holds the shipped archives to the
  //     ground the cards are about, so an archive that stopped being read (a
  //     wrong path, a layer losing its tiles: line) fails here rather than
  //     quietly sending every click to the Census. The Capitol is in Salt
  //     Lake City city and in Salt Lake City School District (TIGERweb, read
  //     2026-11-12). Utah has no elementary or secondary districts, so those
  //     two layers are not drawn and there is no split ground to hold.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const census = [];
    const page = await booted(context, `${BASE}#point=${POINT}&layers=municipality,school-district-unified`, async (p) => {
      await p.route("**/tigerweb.geo.census.gov/**", (r) => { census.push(r.request().url()); r.abort(); });
    });
    const muni = await cardText(page, "municipality");
    const school = await cardText(page, "school-district-unified");
    check("the municipality archive answers at the Capitol with no Census request",
      !muni.error && /Salt Lake City city/.test(muni.text) && /Incorporated city/.test(muni.text) &&
        census.every((u) => !/Places_CouSub_ConCity_SubMCD/.test(u)),
      `census=${census.length} ${muni.text.slice(0, 90)}`);
    check("the school district archive answers at the Capitol with no Census request",
      !school.error && /Salt Lake City School District/.test(school.text) &&
        census.every((u) => !/School\/MapServer/.test(u)),
      `census=${census.length} ${school.text.slice(0, 90)}`);
    await context.close();
  }

  // 7c. MOST OF UTAH IS IN NO INCORPORATED PLACE, AND THE CARD SAYS SO. A
  //     point in the West Desert, in Juab County (40.0, -113.0) is outside
  //     every incorporated place (TIGERweb's layer 4 answered no place there
  //     on 2026-11-12, and Salt Lake City city at the Capitol, the control),
  //     so the archive answers nothing there and the card must say the point
  //     is outside every one and that the county governs it, rather than
  //     name a nearby place or read as a failed lookup. The Census is
  //     unreachable, so the archive is what answers.
  {
    const NO_PLACE = "40.00000,-113.00000";
    const context = await browser.newContext({ serviceWorkers: "block" });
    const census = [];
    const page = await booted(context, `${BASE}#point=${NO_PLACE}&layers=municipality`, async (p) => {
      await p.route("**/tigerweb.geo.census.gov/**", (r) => { census.push(r.request().url()); r.abort(); });
    });
    const muni = await cardText(page, "municipality");
    check("a point in the West Desert, in Juab County says it is in no incorporated place and the county governs it",
      !muni.error && muni.empty && /This point is not in any city or town/.test(muni.text) &&
        /the county is the general-purpose local government/.test(muni.text) &&
        census.every((u) => !/Places_CouSub_ConCity_SubMCD/.test(u)),
      `census=${census.length} ${muni.text.slice(0, 120)}`);
    await context.close();
  }


  // 8. THE ZIP LAYER IS IN-STATE ONLY, AND THIS IS THE CHECK THAT PROVES IT.
  //    A ZCTA carries no STATE field, so this is the one layer here whose
  //    point query cannot be filtered server-side — and over a land border it
  //    does not answer with nothing, it answers with a real neighbouring ZIP.
  //
  //    THE OUT-OF-STATE HALF IS THE ONE THAT DISCRIMINATES. The stub answers
  //    82930 (a Wyoming ZIP (Evanston)) whatever point is asked, so a
  //    regression that drops `coverage` shows the block AND renders that ZIP at
  //    the negative point, which is the harm a reader would see. The in-state
  //    half is equally load-bearing: coverage fails OPEN, so a test that only
  //    asserted hiding would also pass on a layer that had stopped working
  //    altogether. Each half refuses the archive first, so the live path is
  //    the one tested.
  //
  //    The negative point is the worksheet's own, in Uinta County, Wyoming,
  //    about 30 km north of the Utah line, outside the state outline, which is
  //    what the coverage test reads.
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
          geometry: { rings: [[[-112.4, 40.3], [-110.4, 40.3], [-110.4, 42.0], [-112.4, 42.0], [-112.4, 40.3]]] }
        }]
      });
    }

    // in state: the layer answers, and answers from the stub
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=zip-code`, async (p) => {
        await p.route("**/data/app/tiles/zip-code.pmtiles", (r) => r.abort());
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("84114") }));
      });
      const info = await cardText(page, "zip-code");
      check("zip-code answers inside Utah (coverage fails open, so this half matters)",
        !info.error && /84114/.test(info.text || ""),
        (info.text || "").slice(0, 90));
      await context.close();
    }

    // out of state: the layer HIDES, and the stubbed ZIP never renders
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${NEGATIVE_POINT}&layers=zip-code`, async (p) => {
        await p.route("**/data/app/tiles/zip-code.pmtiles", (r) => r.abort());
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("82930") }));
      });
      const hidden = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-zip-code");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === true;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const info = await cardText(page, "zip-code");
      const leaked = /82930/.test(info.text || "");
      const stillOn = await page.evaluate(
        (n) => window[n].state.layersOn["zip-code"] === true, EXPORTS_NAME);
      check("zip-code hides outside Utah rather than naming a Wyoming ZIP (Evanston)",
        hidden && !leaked && stillOn,
        `hidden=${hidden} leaked=${leaked} layersOn=${stillOn} text=${(info.text || "").slice(0, 90)}`);
      await context.close();
    }
  }

  // 9. THE COUNTY CARD NAMES NOBODY AND SAYS SO. No list of county officials
  //    has been read (gap ut-county-officials), so the card must name the
  //    county, say how a Utah county is governed and say nobody is named,
  //    rather than leave a reader to assume the list is empty. Which county
  //    holds the Capitol is read from the shipped county file, so the fixture
  //    moves with a rebuild.
  {
    const counties = shipped("state-counties.json");
    const at = propsAt(counties, POINT)[0] || {};
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=county`);
    const info = await cardText(page, "county");
    const text = info.text || "";
    const want = [/County officials/, /elected county commission/, /None of them is named here yet/];
    const missing = want.filter((re) => !re.test(text));
    check("the County card at the Capitol names the county and says no county official is named",
      !info.error && !!at.NAME && text.includes(at.NAME) && missing.length === 0,
      `file=${at.NAME} missing=${missing} text=${text.slice(0, 120)}`);
    await context.close();
  }

  // 10. TRIBAL GOVERNMENT. The nation, its seat and the land expected are
  //     read from the shipped file at the point, so a rebuild moves the
  //     expectation with the file; what is asserted is that each card agrees
  //     with it, and with where each name and seat came from.
  //       - The Utah part of the Goshute Reservation is seated at Ibapah from
  //         the nation's own site, because the Bureau of Indian Affairs lists
  //         no office town for the tribes; the card says so on an "About the
  //         seat" line, links that site, and names the whole council.
  //       - The Utah part of the Navajo Nation Reservation names a nation the
  //         Bureau seats at Window Rock, Arizona, and its districts line names
  //         the nine tribal subdivisions the Census draws on its ground here.
  //       - The Uintah and Ouray Reservation is the ordinary case: the
  //         Bureau's town and site, and no "About the seat" line.
  //       - The Capitol is on no tribal land, and the card says so in the
  //         layer's own words.
  //     Each point is the pole of inaccessibility of the largest part of the
  //     piece inside this app's coverage outline, as the shipped files draw
  //     them (shapely polylabel, 2026-11-13): 4.6 km, 14.5 km and 39.8 km from its edge.
  {
    const areas = shipped("tribal-areas.json");
    const councils = shipped("tribal-councils.json");
    const GOSHUTE = "39.85232,-113.99371";
    const NAVAJO = "37.16204,-109.20824";
    const UINTAH_OURAY = "40.33461,-110.54080";
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
      // The "(official)" link is the card's footer, a sibling of the card body,
      // so cardText() never sees it; read it from the footer itself.
      const link = await page.evaluate(() => {
        const el = document.getElementById("card-tribal-government");
        const block = el && el.closest(".layer-block");
        const a = block && block.querySelector(".card-footer-link");
        return a ? { text: a.textContent.trim(), href: a.getAttribute("href") || "" } : { text: "", href: "" };
      });
      await context.close();
      return { text: card.text || "", error: card.error, link, labels: fields.map((f) => f.label),
               by: (l) => (fields.find((f) => f.label === l) || {}).value || "" };
    };

    {
      const land = propsAt(areas, GOSHUTE);
      const p = land[0] || {};
      const council = (councils[p.aiannh] || {}).roster || [];
      const c = await at(GOSHUTE);
      check("the Utah part of the Goshute Reservation is seated at Ibapah from the nation's own site, says so, links that site, and names its whole council",
        land.length === 1 && !c.error &&
          c.by("Tribal government") === p.nation && p.nation === "Confederated Tribes of the Goshute Reservation, Nevada and Utah" &&
          c.by("Land") === "Goshute Reservation" &&
          c.by("Seat of government") === "Ibapah, UT" &&
          c.labels.indexOf("Recognized by") === -1 &&
          !!p.url && c.link.text === p.nation + " (official)" && c.link.href === p.url &&
          council.length > 0 && council.every((m) => c.text.includes(m.name)) &&
          c.text.includes("From the nation's own council page") &&
          c.text.includes("Where these names come from") && !c.by("Why no names") &&
          !!p.seatNote && c.by("About the seat") === p.seatNote && p.seatNote.indexOf("From the nation's own site") === 0 &&
          p.url === "https://ctgr.us/home/" &&
          p.shareInState < 1,
        `land here=${land.length} link=${JSON.stringify(c.link)} labels=${JSON.stringify(c.labels)} ${JSON.stringify(c.text.slice(0, 160))}`);
    }

    {
      const land = propsAt(areas, NAVAJO);
      const p = land[0] || {};
      const c = await at(NAVAJO);
      check("the Utah part of the Navajo Nation Reservation names a nation seated in Arizona and the tribal subdivisions drawn there",
        land.length === 1 && !c.error &&
          c.by("Tribal government") === p.nation && p.nation === "Navajo Nation, Arizona, New Mexico & Utah" &&
          c.by("Land") === "Navajo Nation Reservation" &&
          c.by("Seat of government") === "Window Rock, AZ" &&
          c.labels.indexOf("Recognized by") === -1 &&
          !!p.url && c.link.text === p.nation + " (official)" && c.link.href === p.url &&
          p.shareInState < 1 &&
          (p.districts || []).length === 9 &&
          c.by("Districts drawn here") === p.districtsNote &&
          (p.districts || []).every((d) => p.districtsNote.indexOf(d) !== -1),
        `land here=${land.length} link=${JSON.stringify(c.link)} labels=${JSON.stringify(c.labels)} ${JSON.stringify(c.text.slice(0, 160))}`);
    }

    {
      const land = propsAt(areas, UINTAH_OURAY);
      const p = land[0] || {};
      const c = await at(UINTAH_OURAY);
      check("the Uintah and Ouray Reservation takes the Bureau's town and site and carries no note about its seat",
        land.length === 1 && !c.error &&
          c.by("Tribal government") === p.nation && p.nation === "Ute Indian Tribe of the Uintah & Ouray Reservation, Utah" &&
          c.by("Land") === "Uintah and Ouray Reservation" &&
          c.by("Seat of government") === "Ft. Duchesne, UT" &&
          c.labels.indexOf("Recognized by") === -1 &&
          !!p.url && c.link.text === p.nation + " (official)" && c.link.href === p.url &&
          !p.seatNote && c.labels.indexOf("About the seat") === -1,
        `land here=${land.length} link=${JSON.stringify(c.link)} labels=${JSON.stringify(c.labels)} ${JSON.stringify(c.text.slice(0, 160))}`);
    }

    {
      const off = await at(POINT);
      check("a point off tribal land is told so in the layer's own words",
        propsAt(areas, POINT).length === 0 &&
          off.text.indexOf("not on tribal land") !== -1 && off.text.indexOf("9 tribal areas") !== -1,
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
