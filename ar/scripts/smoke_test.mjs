// Headless boot + behaviour smoke test, run in CI on every pull request
// (.github/workflows/smoke-test.yml). Serves the real index.html and drives it
// in Chromium via Playwright — the check the README's "Validation" section
// describes and that OPTIMIZATION_PLAYBOOK item 5 asked to actually commit.
//
// It deliberately depends only on the app shell (Leaflet from its CDN) and the
// same-origin data/app/*.json files — never on the live district APIs, which
// are flaky/blocked in CI. The three no-API layers (school board, IL Supreme
// Court, Board of Review) are the deterministic ground truth.
//
// Run locally against a static server:
//     python3 -m http.server 8000 &
//     npm install playwright && node scripts/smoke_test.mjs
// Configure the URL with BASE_URL (default http://localhost:8000/).

import { chromium } from "playwright";
import { readFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

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
const POINT = "34.74650,-92.28960"; // the State Capitol, Little Rock, Pulaski County
const OFFLINE = ["county", "us-house", "ar-senate", "ar-house", "quorum-court", "county-subdivision", "voting-precinct", "ar-court-of-appeals", "ar-circuit-court", "fire-district"];
const EXPECT_DISTRICT = { "county": "Pulaski County", "us-house": "2", "ar-senate": "14", "ar-house": "74", "quorum-court": "6", "county-subdivision": "Big Rock Township", "voting-precinct": "Precinct 098", "ar-court-of-appeals": "6", "ar-circuit-court": "6th Judicial Circuit", "fire-district": "Little Rock" };
const NEGATIVE_POINT = "33.40000,-94.40000"; // near New Boston, Bowie County, TEXAS, south of the Red River that forms the state line there — outside Arkansas and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-13: TIGERweb's county layer names Bowie County, Texas at this point (control: the Capitol anchor returns Arkansas), and the Census's ZIP layer answers 75570 there, which is the neighbouring-state answer the ZIP layer's coverage test exists to hide. TEXAS BECAUSE NO INSTANCE SERVES IT and none is planned next; Mississippi and Louisiana, both on the next-states list, were passed over so this point does not have to move when either goes live, and the point sits well west of the Texas–Louisiana line.
const APP_NAME = "districtry Arkansas";
const EXPECT_LAYERS = 18;
// ==== GENERATED:END smoke-config ====
// Fork-specific smoke-test constants (the reference repo hoists its own set
// here). The template's CHI-scenario checks are dropped at build time, so the
// GAP_PROBE / MOVE_POINT / STRAGGLER_* names below are contract stubs — the
// span's consumers keep the names resolvable; grow real fixtures (and restore
// the corresponding checks from the reference repo's smoke_test.mjs) as this
// fork ships the layers they exercise.
const EXPORTS_NAME = "ArkansasExplorer";
const PORTAL_HOST = "data.invalid"; // must stay a non-empty hostname: an empty string would abort every request
// Geocoder type-ahead fixture: RAW carries an embedded unit the app's cleaner
// must strip to CLEANED; the Photon STUB answers only CLEANED, so the check
// proves the strip-and-retry path with no live network.
const GEOCODER_QUERY_RAW = "16 W Jones St Suite 200, Capital City";
const GEOCODER_UNIT_FRAGMENT = "Suite 200";
const GEOCODER_QUERY_CLEANED = "16 W Jones St, Capital City";
const GEOCODER_STUB_FEATURE = {
  type: "Feature",
  geometry: { type: "Point", coordinates: [-92.28960, 34.74650] },
  properties: {
    housenumber: "100",
    street: "W Jones St",
    city: "Capital City",
    state: "Arkansas",
    postcode: "00000"
  }
};
// Contract stubs (their consuming checks are reference-fork scenarios,
// dropped from this template's body):
const GAP_PROBE = { county: "statewide", label: "Statewide", lat: 34.74650, lng: -92.28960 };
const MOVE_POINT = { lat: 0, lng: 0, district: "0" };
const STRAGGLER_FILE = "data/app/state-counties.json";
const STRAGGLER_POINT = "0,0";
// Layers expected to HIDE (not merely report no district) at NEGATIVE_POINT.
// The starter layers declare no coverage() test, so none hide — they all take
// the honest "no district here" branch instead.
const NEGATIVE_HIDDEN = [];
const BOOT_TIMEOUT = 45000; // Leaflet CDN + first paint on a cold CI runner
const QUERY_TIMEOUT = 25000;

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

const browser = await chromium.launch();
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
  //     ARKANSAS HAS NEIGHBOURS THE FLEET SERVES AND NEIGHBOURS IT DOES NOT,
  //     so both halves are its own. Oklahoma is live, so a click on Sallisaw
  //     must open that app; Texas is served by nobody, so a click on
  //     Texarkana, Texas must stay here (1a2-ii below). This instance answers
  //     its own side from the coverage rings the wash retained — no fetch.
  //     Chicago proves the file is still read for ground far from here.
  //     Tennessee went live while this instance was being built, so Memphis
  //     joined as a case when that go-live was merged in: Overton Park sits
  //     about 6.5 km east of this instance's own outline (measured 2026-10-13
  //     against the shipped ring and fleet-outlines.json's tennessee entry),
  //     well clear of either outline's simplification. Its first run FAILED,
  //     and correctly: this dark instance's sibling list (`metro_explorers`,
  //     hand-seeded until go-live runs --sync-fleet) still lacked South
  //     Carolina and Tennessee, so the hand-off had nowhere to send the point.
  //     Mississippi joined as a case in the change that published it
  //     (2026-10-16): Clarksdale, the Coahoma County seat, sits about 15 km
  //     east of this app's own outline, inside Mississippi's outline in
  //     fleet-outlines.json and no other.
  {
    const cases = [
      { name: "Chicago", lat: 41.8825, lng: -87.6285, want: "https://districtry.com/il/" },
      { name: "Sallisaw, Oklahoma", lat: 35.4604, lng: -94.7875, want: "https://districtry.com/ok/" },
      { name: "Memphis, Tennessee", lat: 35.1440, lng: -89.9930, want: "https://districtry.com/tn/" },
      { name: "Clarksdale, Mississippi", lat: 34.2001, lng: -90.5709, want: "https://districtry.com/ms/" },
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
      check(`a click on ${c.name} from Arkansas opens ${c.want} with the point`, !!went, went || page.url());
      await context.close();
    }
  }

  // 1a2-ii. The half that keeps 1a2 honest: Texarkana, Texas sits across
  //     State Line Avenue from Texarkana, Arkansas and no districtry instance
  //     covers it, so the click must stay HERE. The point is about 5 km west
  //     of the line, so the outline's own simplification cannot decide it. A route to a sibling would be the same lie
  //     pointing the other way, and the stub makes it visible: if the app
  //     navigated, the URL would be the stubbed sibling rather than this app.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, BASE, async (p) => {
      await p.route("https://districtry.com/**", (route) =>
        route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>sibling</title>" }));
    });
    await page.evaluate(({ n }) => {
      window[n].map.fire("click", { latlng: window.L.latLng(33.4300, -94.1000) });
    }, { n: EXPORTS_NAME });
    await page.waitForTimeout(3000);
    const url = page.url();
    // Still under BASE means still this app. This asked for the URL NOT to
    // name one of a list of sibling tags, and a list needs a new entry each
    // time a state goes live: the tag it lacks reads as staying here.
    check("a click on Texarkana, Texas stays in this app",
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

  // 2. The three no-API layers classify a known point against known ground
  //    truth, fetched from data/app/*.json. Two expected-value shapes: a
  //    NUMERIC expectation asserts the card's own "District N" token exactly
  //    (never a stray digit elsewhere in the card); a NAME expectation (a
  //    state-template fork's county or school-district anchor, whose card
  //    honestly prints an identity rather than a number) asserts the card
  //    names that identity verbatim.
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
    // 2a. A LEGISLATOR'S OWN NUMBER RIDES THE PERSON ROW, as the member's
    //     page prints it, since Adam's ruling of 2026-10-17 ("if the official
    //     government source uses personal phone numbers, we publish those").
    //     The number expected is read from the shipped roster for each
    //     chamber's anchor district, so a weekly refresh that changes it
    //     changes what is expected; a record carrying none is reported, never
    //     passed as a check. The card shows numbers with no-break hyphens,
    //     folded back before comparing.
    //     The member's e-mail address rides the same row since Adam chose
    //     "E-mails too" the same day; it shows as a link labelled Email, so
    //     the link's own address is what is compared.
    for (const [id, file] of [["ar-senate", "ar-senate-members.json"], ["ar-house", "ar-house-members.json"]]) {
      const rec = await page.evaluate(async ({ f, d }) => {
        const r = await fetch("data/app/" + f).then((x) => x.json());
        return r[d] || {};
      }, { f: file, d: EXPECT_DISTRICT[id] });
      const want = rec.phone || null;
      const info = await cardText(page, id);
      const text = (info.text || "").replace(/‑/g, "-");
      if (!want) {
        console.log(`  SKIP  ${id} member's own number — the anchor's member prints none`);
      } else {
        check(`${id} card shows the number the member's own page prints`,
          !info.error && text.includes(want), `want ${want}; got ${text.slice(0, 160)}`);
      }
      if (!rec.email) {
        console.log(`  SKIP  ${id} member's e-mail — the anchor's member prints none`);
      } else {
        const hrefs = await page.evaluate((cid) =>
          Array.from(document.querySelectorAll("#card-" + cid + " a[href^='mailto:']"))
            .map((a) => a.getAttribute("href")), id);
        check(`${id} card links the e-mail address the member's own page prints`,
          hrefs.includes("mailto:" + rec.email), JSON.stringify(hrefs));
      }
    }
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
  //    fire-station is 1,619 points in Arkansas's envelope, within 381
  //    of a 2,000-record cap the service reports as HTTP 200 +
  //    exceededTransferLimit rather than an error, so the day the count passes
  //    the cap a single request drops real stations and the nearest-3 card
  //    looks correct at every point. That was proven by hand when the layer shipped
  //    and then by NOTHING: the source manifest's count row cannot see it,
  //    because returnCountOnly is not subject to maxRecordCount and answers the
  //    true count whatever the client does. This is the check that can.
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
      attributes: { NAME: `FAR STATION ${i}`, ADDRESS: "1 Far Rd", CITY: "Fayetteville", STATE: "AR", ZIPCODE: "72701" },
      geometry: { x: -83.0458, y: 42.3314 },
    });
    const [lat, lng] = POINT.split(",").map(Number);
    const page = await booted(context, BASE, (p) =>
      p.route(/MapServer\/51\/query/, (route) => {
        const params = new URL(route.request().url()).searchParams;
        const offset = Number(params.get("resultOffset"));
        offsets.push(offset);
        fieldsAsked.push(params.get("outFields") || "");
        // ESRI JSON, not GeoJSON — the shape the app now asks for. Every
        // ArcGIS loader moved to f=json on 2026-09-05 because the GeoJSON
        // export unnests interior rings (engine/index.html/arcgis-loader.txt);
        // a stub still answering GeoJSON stops reproducing the contract. The
        // assertions are unchanged; only the wire format is.
        const body = offset === 0
          ? { exceededTransferLimit: true, features: [far(1), far(2), far(3)] }
          : { features: [{
                attributes: { NAME: "PAGE TWO STATION", ADDRESS: "2 Second Page Way",
                              CITY: "Little Rock", STATE: "AR", ZIPCODE: "72201" },
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
    // cardText returns {text, error, empty}, not a bare string.
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
    // broken. Asserting only the rendered line is GREEN FOR THE WRONG REASON —
    // this stub returns STATE whatever outFields asks for, so deleting STATE
    // from the app's request left the line check passing (measured, while
    // writing this). Asserting only the request would pass with a card that
    // never renders what it fetched.
    check("the app ASKS the service for STATE",
      fieldsAsked.every((f) => /\bSTATE\b/.test(f)),
      `outFields=${fieldsAsked[0] || "(none seen)"}`);
    check("a structure line RENDERS its state",
      /Little Rock, AR/.test(text), text.slice(0, 140));
    await context.close();
  }

  // 7. THE THREE LIVE TIGERWEB FABRIC CARDS, STUBBED — and stubbed on purpose
  //    rather than anchored. The worksheet's OFFLINE anchors are same-origin
  //    only, which is this test's own stated contract, and these three layers
  //    fetch the Census live: asserting a card against somebody else's server
  //    makes the test fail on their outage and on any network that intercepts
  //    TLS, which is how it failed here first (ERR_CERT_AUTHORITY_INVALID on
  //    tigerweb.geo.census.gov, with the same query answering 200 to curl
  //    through the agent proxy in the same minute).
  //
  //    WHAT IS ACTUALLY WORTH TESTING IS THIS INSTANCE'S OWN CODE, and none of
  //    it is exercised by a live fetch that happens to work. Three claims, each
  //    wrong in a way a reader would see:
  //
  //    (a) The municipality card states the style the Census records, a CITY
  //        or a TOWN, and an affix the card does not know produces NO type row
  //        rather than an improvised one.
  //    (b) A separate status row appears only for a FUNCSTAT I place. No
  //        Arkansas place is inactive today (501 of 501 active, 2026-10-13),
  //        and the row is tested anyway: a missing status row would imply a
  //        working government where the Census records none.
  //    (c) The one school tiling answers, under the label with no qualifier,
  //        because the unified districts cover the state alone.
  //    (d) A city above 25,000 names its mayor and every council seat from
  //        the roster, joined on the Census id the stub carries, with who
  //        elects each seat; a place outside the 19 says it names nobody.
  //        The roster is the shipped data/app file, so this also holds the
  //        join to it.
  {
    function esriPolygon(props) {
      return {
        attributes: props,
        geometry: { rings: [[[-93, 34], [-91.5, 34], [-91.5, 35.5], [-93, 35.5], [-93, 34]]] }
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

    const cases = [
      {
        name: "a city names itself a city, and names its mayor and board",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "0541000", NAME: "Little Rock city", BASENAME: "Little Rock", STATE: "05", LSADC: "25", FUNCSTAT: "A" },
        want: [/Little Rock city/, /Incorporated city/, /Frank Scott Jr\./, /Virgil Miller Jr\./,
          /Director, Ward 1/, /elected by Ward 1/, /Director, Position 8 \(at large\)/, /Joan Adcock/,
          /How the seats are elected/, /Read on/, /Which ward this point is in/],
        reject: [/INACTIVE/, /Incorporated town/, /Not named here/]
      },
      {
        name: "a city that elects every seat citywide says so for each seat",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "0566080", NAME: "Springdale city", BASENAME: "Springdale", STATE: "05", LSADC: "25", FUNCSTAT: "A" },
        want: [/Springdale city/, /Doug Sprouse/, /Council, Ward 1, Position 1/, /elected by the whole city/],
        reject: [/elected by Ward/, /Which ward this point is in/, /Not named here/]
      },
      {
        name: "a town names itself a town, not a city, and names nobody",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "0507150", NAME: "Blue Eye town", BASENAME: "Blue Eye", STATE: "05", LSADC: "43", FUNCSTAT: "A" },
        want: [/Blue Eye town/, /Incorporated town/, /Not named here/],
        reject: [/INACTIVE/, /Incorporated city/, /Mayor/]
      },
      {
        name: "an affix the card does not carry prints NO type row",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "0599999", NAME: "Nowhere village", BASENAME: "Nowhere", STATE: "05", LSADC: "47", FUNCSTAT: "A" },
        want: [/Nowhere village/],
        reject: [/Incorporated city/, /Incorporated town/]
      },
      {
        name: "a FUNCSTAT I place says it is inactive",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "0599998", NAME: "Example town", BASENAME: "Example", STATE: "05", LSADC: "43", FUNCSTAT: "I" },
        want: [/Example town/, /INACTIVE/, /no government operating/],
        reject: []
      },
      {
        name: "the school district card names the district",
        layer: "school-district-unified",
        service: "School/MapServer/0",
        props: { GEOID: "0509000", NAME: "Little Rock School District", STATE: "05" },
        want: [/Little Rock School District/],
        reject: [/Unified/]
      }
    ];

    for (const c of cases) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=${c.layer}`, async (p) => {
        // Both the point query and the statewide overlay download go to the
        // same service path, so one route answers both with the same feature —
        // which also proves the card comes from the POINT query rather than
        // from the statewide set: the app renders before that finishes.
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
  //    point query cannot be filtered server-side — and outside Arkansas it
  //    does not answer with nothing, it answers with a real neighbouring ZIP.
  //    Measured against the live service 2026-10-13: the Texas negative point
  //    -> 75570, against the State Capitol's correct 72201. So without a coverage test this card would present
  //    another state's ZIP code as this app's answer.
  //
  //    THE OUT-OF-STATE HALF IS THE ONE THAT DISCRIMINATES, and the stub is
  //    what makes it honest: it answers with 75570 — a ZIP the live service
  //    really does return over the line — so a regression that drops
  //    `coverage` renders that card and fails here. Stubbing an EMPTY answer
  //    would pass for the wrong reason. The in-state half is equally
  //    load-bearing: coverage fails OPEN, so a test that only asserted hiding
  //    would also pass on a layer that had stopped working altogether.
  //
  //    The negative point is the worksheet's own, in Bowie County, Texas —
  //    outside the county fabric's dissolve, which is what the coverage test
  //    reads.
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
          geometry: { rings: [[[-95, 33], [-91, 33], [-91, 35.5], [-95, 35.5], [-95, 33]]] }
        }]
      });
    }

    // in state: the layer answers, and answers from the stub
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=zip-code`, async (p) => {
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("72201") }));
      });
      const info = await cardText(page, "zip-code");
      check("zip-code answers inside Arkansas (coverage fails open, so this half matters)",
        !info.error && /72201/.test(info.text || ""),
        (info.text || "").slice(0, 90));
      await context.close();
    }

    // out of state: the layer HIDES, and the neighbouring ZIP never renders
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${NEGATIVE_POINT}&layers=zip-code`, async (p) => {
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("75570") }));
      });
      const hidden = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-zip-code");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === true;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const info = await cardText(page, "zip-code");
      const leaked = /75570/.test(info.text || "");
      const stillOn = await page.evaluate(
        (n) => window[n].state.layersOn["zip-code"] === true, EXPORTS_NAME);
      check("zip-code hides outside Arkansas rather than naming a Texas ZIP",
        hidden && !leaked && stillOn,
        `hidden=${hidden} leaked=${leaked} layersOn=${stillOn} text=${(info.text || "").slice(0, 90)}`);
      await context.close();
    }
  }

  // 9. THE COUNTY JUDGE AND THE QUORUM COURT, at the Capitol (Pulaski
  //    County, quorum court District 6). The expected names are read from
  //    the shipped roster rather than written here, because the weekly
  //    refresh changes them and a name in this file would fail a correct
  //    rebuild. What is held: the County card names Pulaski's judge and every
  //    justice the roster lists, and credits where both came from; the Quorum
  //    Court District card names the presiding judge and EITHER the justice
  //    the county's own page puts in District 6 OR says it names no one —
  //    never a name the roster does not tie to District 6. Then the roster is
  //    refused, and both cards must degrade to sentences naming nobody while
  //    the district itself still classifies: a roster failure is not the
  //    layer's failure.
  {
    const roster = JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "app", "ar-county-officials.json"), "utf8"));
    const pulaski = roster["05119"];
    const justices = pulaski.quorumCourt.justices.filter((j) => !j.vacant).map((j) => j.name);
    const numbered = pulaski.quorumCourt.districts || null;
    const inSix = numbered ? numbered["6"] : null;
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=county,quorum-court`);
      const county = await cardText(page, "county");
      const missing = justices.filter((n) => !county.text.includes(n));
      check("county card names the county judge and every listed justice of the peace",
        !county.error && county.text.includes(pulaski.judge.name) && missing.length === 0 &&
          /Where the judge's name comes from/.test(county.text) &&
          /Where these names come from/.test(county.text),
        missing.length ? `missing=${missing.slice(0, 3)}` : county.text.slice(0, 90));
      const qc = await cardText(page, "quorum-court");
      const others = justices.filter((n) => n !== inSix && qc.text.includes(n));
      const namedRight = inSix ? qc.text.includes(inSix) : /names no one rather than guessing/.test(qc.text);
      check("quorum-court card names District 6's justice only where the county numbers them",
        !qc.error && /District 6\b/.test(qc.text) && qc.text.includes(pulaski.judge.name) &&
          namedRight && others.length === 0,
        `inSix=${inSix} others=${others.slice(0, 3)} text=${qc.text.slice(0, 90)}`);
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=county,quorum-court`, async (p) => {
        await p.route("**/data/app/ar-county-officials.json", (r) => r.fulfill({ status: 503, body: "down" }));
      });
      const county = await cardText(page, "county");
      const qc = await cardText(page, "quorum-court");
      check("county and quorum-court cards degrade to naming nobody when the roster fails",
        !county.error && /did not load/.test(county.text) && !county.text.includes(pulaski.judge.name) &&
          !qc.error && /District 6\b/.test(qc.text) && /did not load/.test(qc.text),
        `county=${county.text.slice(0, 60)} qc=${qc.text.slice(0, 60)}`);
      await context.close();
    }
  }

  // 9b. THE 2024 RESULTS, in two counties that publish no numbered list of
  //    their own. Arkansas County District 1's 2024 winner was still on the
  //    association's list and Benton County District 9's was not, measured
  //    2026-10-13 — but what each card must say is read from the shipped
  //    roster, not written here, because the weekly refresh moves a district
  //    between those two states. Held: the card names the district's 2024
  //    winner and credits the results where the roster names one, says it
  //    names no one where it does not, and never prints another justice of
  //    that county. The points are interior points of the two districts as
  //    the state's map draws them (polylabel, 2026-10-13).
  {
    const roster = JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "app", "ar-county-officials.json"), "utf8"));
    const cases = [
      { name: "Arkansas County District 1", lat: 34.461, lng: -91.42008, fips: "05001", district: "1" },
      { name: "Benton County District 9", lat: 36.33671, lng: -94.2813, fips: "05007", district: "9" },
    ];
    for (const c of cases) {
      const qcRoster = roster[c.fips].quorumCourt;
      const own = qcRoster.districts ? qcRoster.districts[c.district] : null;
      const res = qcRoster.districts ? null : qcRoster.results;
      const elected = res && res.districts ? res.districts[c.district] || null : null;
      const expected = own && !/^vacant$/i.test(own) ? own : elected;
      const everyone = qcRoster.justices.filter((j) => !j.vacant).map((j) => j.name)
        .concat(res ? Object.values(res.districts) : []);
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${c.lat},${c.lng}&layers=quorum-court`);
      const qc = await cardText(page, "quorum-court");
      const others = everyone.filter((n) => n !== expected && !(expected && expected.includes(n)) &&
        qc.text.includes(n));
      const said = expected
        ? qc.text.includes(expected) && (own || /2024 general election results/.test(qc.text))
        : /names no one rather than guessing/.test(qc.text);
      check(`quorum-court card at ${c.name} names ${expected || "no one"} from the roster's own answer`,
        !qc.error && new RegExp(`District ${c.district}\\b`).test(qc.text) && said && others.length === 0,
        `expected=${expected} others=${others.slice(0, 3)} text=${qc.text.slice(0, 120)}`);
      await context.close();
    }
  }

  // 10. THE TOWNSHIP CARD, drawn from the state's own township map rather than
  //    the Census's. Check 2 already holds the Capitol to Big Rock Township;
  //    this holds what the card says there and one place where the two maps
  //    differ. Fayetteville city hall is in Township 2 of the three Washington
  //    County's 2013 order left, and the Census still calls the same ground
  //    Fayetteville township (TIGERweb, read 2026-10-15). So the card must
  //    name Township 2, never Fayetteville township; say the township has no
  //    government of its own; say its voters elect a constable and that this
  //    map names none; and name the county from the township's own record.
  for (const c of [
    { name: "the Capitol", point: POINT, township: "Big Rock Township", county: "Pulaski County", reject: [] },
    { name: "Fayetteville city hall", point: "36.06260,-94.15740", township: "Township 2", county: "Washington County",
      reject: [/Fayetteville township/i] },
  ]) {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${c.point}&layers=county-subdivision`);
    const info = await cardText(page, "county-subdivision");
    const text = info.text || "";
    const want = [new RegExp(c.township + "(?!\\d)"), new RegExp(c.county), /None of its own/,
      /elect a constable/, /does not name constables/, /Arkansas GIS Office/];
    const missing = want.filter((re) => !re.test(text));
    const present = c.reject.filter((re) => re.test(text));
    check(`county-subdivision card at ${c.name} names ${c.township} from the state's map`,
      !info.error && missing.length === 0 && present.length === 0,
      `missing=${missing} unwanted=${present} text=${text.slice(0, 160)}`);
    await context.close();
  }

  // 11. THE TWO COURT CARDS, whole counties grouped by Act 1812 of 2003 and by
  //    the circuit judge directory. Check 2 already holds the Capitol to Court
  //    of Appeals District 6 and the 6th Judicial Circuit; this holds what the
  //    cards say in three places: the Capitol, in a two-judge district and the
  //    17-judge 6th Circuit, one of the five a federal court order divides into
  //    election subdistricts; Fayetteville city hall, in a circuit with no
  //    subdistricts, whose card must not claim any; and downtown El Dorado, in
  //    District 5, which elects one judge. No card may name a judge.
  for (const c of [
    { name: "the Capitol", point: POINT,
      coa: [/Court of Appeals District 6\b/, /Perry, Pulaski and Saline Counties/, /elect two of the court's 12 judges/],
      circuit: [/6th Judicial Circuit/, /Perry and Pulaski Counties/, /Seventeen judges, elected/, /Hunt v\. State of Arkansas/],
      reject: [] },
    { name: "Fayetteville city hall", point: "36.06260,-94.15740",
      coa: [/Court of Appeals District 3\b/, /elect two of the court's 12 judges/],
      circuit: [/4th Judicial Circuit/, /Madison and Washington Counties/, /Eight judges, elected/],
      reject: [/Subdistricts/, /Hunt v\./] },
    { name: "downtown El Dorado", point: "33.20790,-92.66620",
      coa: [/Court of Appeals District 5\b/, /elect one of the court's 12 judges/],
      circuit: [/13th Judicial Circuit/, /Six judges, elected/],
      reject: [/Subdistricts/] },
  ]) {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${c.point}&layers=ar-court-of-appeals,ar-circuit-court`);
    const coa = await cardText(page, "ar-court-of-appeals");
    const circuit = await cardText(page, "ar-circuit-court");
    const coaMissing = c.coa.concat([/hears appeals for the whole state/, /does not name them yet/])
      .filter((re) => !re.test(coa.text || ""));
    const circuitMissing = c.circuit.concat([/nonpartisan elections for six-year terms/, /does not name them yet/])
      .filter((re) => !re.test(circuit.text || ""));
    const unwanted = c.reject.filter((re) => re.test(circuit.text || ""));
    check(`court of appeals card at ${c.name} says the district, its counties and how many judges it elects`,
      !coa.error && coaMissing.length === 0,
      `missing=${coaMissing} text=${(coa.text || "").slice(0, 160)}`);
    check(`judicial circuit card at ${c.name} says the circuit, its judges and only the subdistricts it has`,
      !circuit.error && circuitMissing.length === 0 && unwanted.length === 0,
      `missing=${circuitMissing} unwanted=${unwanted} text=${(circuit.text || "").slice(0, 160)}`);
    await context.close();
  }

  // 12. THE CITY COUNCIL DISTRICT CARD, drawn for the twelve cities above
  //    25,000 people that elect by ward and answered from the shipped files
  //    alone, so nothing here is stubbed. At the Capitol, in Little Rock's
  //    Ward 1, it names the director that ward elects and no other; in Hot
  //    Springs it calls the unit a district, as the city does; and in
  //    Springdale, which ties each seat to a ward and elects every one
  //    citywide, there is no ward to draw and the card says why. Each point
  //    and its ward is one the builder's own anchors hold to the state's map.
  for (const c of [
    { name: "the Capitol", point: POINT,
      want: [/Ward 1\b/, /Little Rock Board of Directors/, /Virgil Miller Jr\./, /Director, Ward 1/,
        /Elected by the whole city/, /The mayor and three directors/, /not the exact legal boundaries/],
      reject: [/Ken Richardson/, /Joan Adcock/, /Frank Scott/] },
    { name: "Hot Springs", point: "34.50410,-93.05540",
      want: [/District 1\b/, /Hot Springs Board of Directors/, /Erin Holliday/, /elected by District 1/,
        /The mayor\. The City or Town card names the mayor\./],
      reject: [/Ward 1/, /Phyllis Beard/] },
    { name: "Springdale", point: "36.18670,-94.12900",
      want: [/not in a city council ward this map draws/, /elect every seat by the whole city/],
      reject: [/Ward 4/, /Springdale City Council/] },
  ]) {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${c.point}&layers=city-ward`);
    const info = await cardText(page, "city-ward");
    const text = info.text || "";
    const missing = c.want.filter((re) => !re.test(text));
    const present = c.reject.filter((re) => re.test(text));
    check(`city-ward card at ${c.name} names only what that ward elects, in the city's own word`,
      !info.error && missing.length === 0 && present.length === 0,
      `missing=${missing} unwanted=${present} text=${text.slice(0, 200)}`);
    await context.close();
  }
} finally {
  await browser.close();
}

if (failures.length) {
  console.error(`\n${failures.length} smoke check(s) failed: ${failures.join(", ")}`);
  process.exit(1);
}
console.log("\nAll smoke checks passed.");
