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
const POINT = "38.25270,-85.75850"; // downtown Louisville, Jefferson County
const OFFLINE = ["county", "us-house", "ky-senate", "ky-house", "voting-precinct"];
const EXPECT_DISTRICT = { "county": "Jefferson County", "us-house": "3", "ky-senate": "33", "ky-house": "43", "voting-precinct": "Precinct 168 43 District" };
const NEGATIVE_POINT = "38.80000,-83.55000"; // near West Union, Adams County, OHIO, about 15 km north of the Ohio River — outside Kentucky and outside every other instance in the fleet, and inside permalink_gate (maxLat 39.30) so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-13: TIGERweb's state and county layers name Ohio and Adams County STATE 39 (controls: the Louisville anchor returns Kentucky and Jefferson County STATE 21, and Columbus returns Ohio and Franklin County STATE 39, so the query answers rather than failing), and no outline in fleet-outlines.json contains it, with Tennessee's outline in that file (control: the Louisville anchor IS inside Kentucky's outline there). THIS POINT WAS IN SUMNER COUNTY, TENNESSEE UNTIL TENNESSEE'S GO-LIVE, chosen on 2026-09-30 because no instance covered Tennessee; that change put Tennessee's outline in the fleet file with the old point inside it, so a Kentucky selection there would have handed off to districtry.com/tn/. OHIO RATHER THAN ANOTHER NEIGHBOUR: Illinois, Indiana, Tennessee, Missouri and, since its go-live, Virginia are live, and the states planned next (Arkansas, Mississippi, Louisiana) do not border Kentucky, so this point should not have to move when they go live. West Virginia, which does and is being built, does not contain this point either. THE POINT IS ON LAND, NOT ON WATER: Kentucky's TIGER county fabric follows the Ohio River's north bank, so the river is INSIDE Kentucky rather than outside it, and a point in open water on the northern border would be inside a Kentucky county exactly as Minnesota's Lake Superior candidate was inside Cook County.
const APP_NAME = "districtry Kentucky";
const EXPECT_LAYERS = 16;
// ==== GENERATED:END smoke-config ====
// Fork-specific smoke-test constants (the reference repo hoists its own set
// here). The template's CHI-scenario checks are dropped at build time, so the
// GAP_PROBE / MOVE_POINT / STRAGGLER_* names below are contract stubs — the
// span's consumers keep the names resolvable; grow real fixtures (and restore
// the corresponding checks from the reference repo's smoke_test.mjs) as this
// fork ships the layers they exercise.
const EXPORTS_NAME = "KentuckyExplorer";
const PORTAL_HOST = "data.invalid"; // must stay a non-empty hostname: an empty string would abort every request
// Geocoder type-ahead fixture: RAW carries an embedded unit the app's cleaner
// must strip to CLEANED; the Photon STUB answers only CLEANED, so the check
// proves the strip-and-retry path with no live network.
const GEOCODER_QUERY_RAW = "700 Capital Avenue Suite 100, Capital City";
const GEOCODER_UNIT_FRAGMENT = "Suite 100";
const GEOCODER_QUERY_CLEANED = "700 Capital Avenue, Capital City";
const GEOCODER_STUB_FEATURE = {
  type: "Feature",
  geometry: { type: "Point", coordinates: [-84.8753, 38.1867] },
  properties: {
    housenumber: "700",
    street: "Capital Avenue",
    city: "Capital City",
    state: "Kentucky",
    postcode: "00000"
  }
};
// Contract stubs (their consuming checks are reference-fork scenarios,
// dropped from this template's body):
const GAP_PROBE = { county: "statewide", label: "Statewide", lat: 38.1867, lng: -84.8753 };
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
    // The coverage-band half selects NEGATIVE_POINT, which is in Ohio (it was
    // in Tennessee until Tennessee went live), and setSelectedPoint PANS there.
    // Until 2026-10-13 that put the map's centre outside Kentucky and armed the
    // pan hand-off, so this check refused ../fleet-outlines.json in case a
    // sibling came to cover the point; panning no longer switches apps, so it
    // refuses nothing.
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
      // THE PURPLE EDGE (2026-10-13). This app's coverage is its whole ground,
      // so the glowing line is drawn along the coverage itself, as the apps
      // with a wider region band always drew theirs. Until that day this one
      // drew no line at all. The coverage key names it.
      const edge = await page.evaluate(() => {
        const pane = document.querySelector(".leaflet-pane.leaflet-scope-mask-pane");
        const sw = document.querySelector(".districtry-map-legend .dml-items .dml-glow");
        const label = sw && sw.parentElement.querySelector(".dml-label");
        return { line: !!(pane && pane.querySelector("path.dst-glow")), label: label ? label.textContent : null };
      });
      check("the wash draws the purple edge along the coverage, and the key names it",
        edge.line && !!edge.label, JSON.stringify(edge));
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


  // 2d. The four court cards name the judges elected from the unit they draw.
  //     The anchor sits in Jefferson, where the two appellate tiers come from
  //     the Court of Justice's statewide pages and the two trial tiers from the
  //     three Jefferson court sites its county page links (since 2026-10-07;
  //     until then those two cards said the court named nobody). So this one
  //     point asserts both routes, and the trial cards must also say where
  //     their judges were read, in the roster's own words.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const courts = ["ky-supreme-court", "ky-court-of-appeals",
                    "ky-circuit-court", "ky-district-court"];
    const page = await booted(context, `${BASE}#point=${POINT}&layers=${courts.join(",")}`);

    // Names are read from the shipped roster rather than written in, so a
    // refresh that seats a new judge does not fail this check — what is
    // asserted is that the card names whoever the roster says, and that it is
    // not the "names nobody" wording.
    const roster = await page.evaluate(() =>
      fetch("data/app/ky-judge-roster.json").then((r) => r.json()));
    for (const [id, tier, unit] of [["ky-supreme-court", "supreme", "4"],
                                    ["ky-court-of-appeals", "appeals", "4"],
                                    ["ky-circuit-court", "circuit", "30"],
                                    ["ky-district-court", "district", "30"]]) {
      const seat = ((roster.tiers || {})[tier] || {})[unit] || { members: [] };
      const named = seat.members.filter((m) => m.name).map((m) => m.name);
      const info = await cardText(page, id);
      check(`${id} names the judge(s) elected from unit ${unit}`,
        !info.error && named.length > 0 && named.every((n) => info.text.includes(n)),
        `roster names ${named.length}: ${named.slice(0, 4).join(", ")} | card: ${info.text.slice(0, 90)}`);
      check(`${id} does not say it names nobody`,
        !/names nobody/i.test(info.text), info.text.slice(0, 90));
      if (tier === "circuit" || tier === "district") {
        const note = (seat.readFrom || {}).note;
        const lead = note ? note.split(",")[0] : null;
        check(`${id} says where Louisville's judges were read`,
          !!lead && info.text.includes(lead),
          `${lead || "no readFrom note in the roster"} | card: ${info.text.slice(-120)}`);
      }
    }
    await context.close();
  }

  // 2f. The City card names the mayor and council from the state's municipal
  //     directory (ky-city-officials.json, keyed by Census place id). The city
  //     itself comes from TIGERweb live, which a sandboxed browser cannot
  //     reach, so the Places query is answered with one stubbed feature around
  //     the anchor; what is asserted is the JOIN — that the card names whoever
  //     the shipped roster names for that id, and that a place the directory
  //     does not carry (Keene) says it names nobody rather than borrowing.
  {
    const [lat, lng] = POINT.split(",").map(Number);
    function placesBody(props) {
      const d = 0.05;
      return JSON.stringify({
        geometryType: "esriGeometryPolygon",
        spatialReference: { wkid: 4326 },
        fields: Object.keys(props).map((n) => ({ name: n, type: "esriFieldTypeString", alias: n })),
        features: [{
          attributes: props,
          geometry: { rings: [[[lng - d, lat - d], [lng + d, lat - d], [lng + d, lat + d], [lng - d, lat + d], [lng - d, lat - d]]] }
        }]
      });
    }
    for (const c of [
      { geoid: "2158620", name: "Owensboro city", named: true },
      { geoid: "2141716", name: "Keene city", named: false }
    ]) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=municipality`, async (p) => {
        // The layer is drawn and answered from a tile archive since 2026-10-17;
        // refusing it sends the card to the census loader, which this stub answers
        // (the archive-failure path il's smoke check 2d also holds).
        await p.route("**/data/app/tiles/municipality.pmtiles", (r) => r.abort());
        await p.route("**/Places_CouSub_ConCity_SubMCD/MapServer/4/query**", (r) =>
          r.fulfill({ status: 200, contentType: "application/json",
            body: placesBody({ GEOID: c.geoid, NAME: c.name, BASENAME: c.name.replace(/ city$/, ""), STATE: "21", LSADC: "25" }) }));
      });
      const roster = await page.evaluate(() =>
        fetch("data/app/ky-city-officials.json").then((r) => r.json()));
      const seats = ((roster[c.geoid] || {}).seats || []).map((s) => s.name);
      const info = await cardText(page, "municipality");
      const text = info.text || "";
      if (c.named) {
        check(`municipality names ${c.name}'s mayor and council from the directory`,
          !info.error && seats.length > 0 && seats.every((n) => text.includes(n)) && /Mayor/.test(text) &&
            !/Not named here/.test(text),
          `roster names ${seats.length}: ${seats.slice(0, 3).join(", ")} | card: ${text.slice(0, 120)}`);
      } else {
        check(`municipality names nobody for ${c.name}, which the directory does not carry`,
          !info.error && seats.length === 0 && /Not named here/.test(text),
          text.slice(0, 120));
      }
      await context.close();
    }
  }

  // 2g. The County card names the county's governing body from the Department
  //     for Local Government's directory (ky-county-officials.json, keyed by
  //     county GEOID). The county layer is a same-origin file, so this needs
  //     no stub. At the anchor (Jefferson) the body is the Louisville Metro
  //     Council, read from the city roster, with the mayor first; at Frankfort
  //     (Franklin) it is a fiscal court led by its judge/executive. What is
  //     asserted is that every person the shipped roster names is on the card,
  //     and that every member the roster gives a 2022 district carries it
  //     ("Magistrate, District 3"), so a district the builder matched cannot be
  //     dropped by the card.
  for (const c of [
    { point: POINT, geoid: "21111", label: "Jefferson", body: /Louisville Metro Council/i },
    { point: "38.20090,-84.87330", geoid: "21073", label: "Franklin", body: /Fiscal court/i }
  ]) {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${c.point}&layers=county`);
    const roster = await page.evaluate(() =>
      fetch("data/app/ky-county-officials.json").then((r) => r.json()));
    const rec = roster[c.geoid] || {};
    const names = (rec.members || []).map((m) => m.name)
      .concat(rec.executive ? [rec.executive.name] : [])
      .concat((rec.officers || []).map((o) => o.name));
    const info = await cardText(page, "county");
    const text = info.text || "";
    const badges = (rec.members || []).filter((m) => m.district != null).map((m) =>
      new RegExp(String(m.role).replace(/[/]/g, "\\/") + ", (District " + m.district +
        "|" + m.district + " District)", "i"));
    if (c.geoid === "21073") {
      check(`county shows the district each ${c.label} County magistrate won in 2022`,
        badges.length > 0 && badges.every((re) => re.test(text)),
        `members with a district ${badges.length}; missing: ${badges.filter((re) => !re.test(text)).map(String).join(", ") || "none"}`);
    }
    check(`county names ${c.label} County's governing body and officers from the directory`,
      !info.error && names.length > 5 && names.every((n) => text.includes(n)) && c.body.test(text),
      `roster names ${names.length}; missing: ${names.filter((n) => !text.includes(n)).join(", ") || "none"} | card: ${text.slice(0, 160)}`);
    await context.close();
  }

  // 2g2. The County card names the supervisors of the county's conservation
  //      district from the Division of Conservation's sheet for it
  //      (ky-conservation-boards.json, keyed by county GEOID; a same-origin
  //      file, so no stub). What is asserted: every name the file gives for
  //      the county is on the card, every vacancy reads "Vacant", each
  //      district's name and the sentence saying how the board is chosen are
  //      there; at Logan, the one county with two districts, both boards
  //      are listed and the card says why; and at Scott, whose sheet marks a
  //      seat "Vacant" (one of four on 2026-10-16), the card shows it.
  for (const c of [
    { point: POINT, geoid: "21111", label: "Jefferson", want: [] },
    { point: "36.84540,-86.88720", geoid: "21141", label: "Logan",
      want: [/has two conservation districts, and this app does not draw the line between them/] },
    { point: "38.20980,-84.55880", geoid: "21209", label: "Scott", want: [] }
  ]) {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${c.point}&layers=county`);
    const boards = await page.evaluate(() =>
      fetch("data/app/ky-conservation-boards.json").then((r) => r.json()));
    const districts = (boards[c.geoid] || {}).districts || [];
    const members = [].concat(...districts.map((d) => d.members || []));
    const names = members.filter((m) => m.name).map((m) => m.name);
    const vacant = members.filter((m) => m.vacant).length;
    const info = await cardText(page, "county");
    const text = info.text || "";
    const want = [/elect all seven supervisors/, /declares them elected without an election/].concat(c.want);
    const missingNames = names.filter((n) => !text.includes(n));
    // a section label is drawn in capitals, which innerText reports, so the
    // district's name is matched without regard to case
    const lower = text.toLowerCase();
    const missingDistricts = districts.map((d) => d.name).filter((n) => !lower.includes(n.toLowerCase()));
    const missing = want.filter((re) => !re.test(text));
    // the conservation section alone, so a vacancy elsewhere on the card
    // (the county's own governing body) cannot satisfy or fail its count
    const end = "This district's sheet (PDF)";
    const from = districts.length ? lower.indexOf(districts[0].name.toLowerCase()) : -1;
    const section = from >= 0 ? text.slice(from, text.lastIndexOf(end) + end.length) : "";
    const vacantShown = (section.match(/\bVacant\b/g) || []).length;
    check(`county names ${c.label} County's conservation district supervisors from the Division's sheet`,
      !info.error && names.length >= 5 && !missingNames.length && !missingDistricts.length &&
        !missing.length && vacantShown === vacant,
      `names ${names.length}; missing names: ${missingNames.join(", ") || "none"}; ` +
        `missing districts: ${missingDistricts.join(", ") || "none"}; missing text: ${missing.join(", ") || "none"}; ` +
        `vacant ${vacantShown}/${vacant}`);
    await context.close();
  }

  // 2h. The Census County Division card, the level-14 map. Every Kentucky
  //     subdivision is a census county division (LSADC 22, FUNCSTAT S, all
  //     493, measured 2026-10-15). The layer reads TIGERweb live, which a
  //     sandboxed browser cannot reach, so the query is answered with one
  //     stubbed feature around the anchor, built from the Census's own record
  //     for that point. What is asserted is this instance's code: the card
  //     says no one is elected from the division, names its county from the
  //     app's own county file, titles it without TIGER's "CCD" (the header
  //     says Census County Division), and prints no Government row for a
  //     status code it does not carry rather than an improvised one.
  {
    const [lat, lng] = POINT.split(",").map(Number);
    function cousubBody(props) {
      const d = 0.05;
      return JSON.stringify({
        geometryType: "esriGeometryPolygon",
        spatialReference: { wkid: 4326 },
        fields: Object.keys(props).map((n) => ({ name: n, type: "esriFieldTypeString", alias: n })),
        features: [{
          attributes: props,
          geometry: { rings: [[[lng - d, lat - d], [lng + d, lat - d], [lng + d, lat + d], [lng - d, lat + d], [lng - d, lat - d]]] }
        }]
      });
    }
    const record = { GEOID: "2111192106", NAME: "Louisville Central CCD", BASENAME: "Louisville Central", STATE: "21", COUNTY: "111", LSADC: "22" };
    for (const c of [
      { name: "a census county division says no one is elected from it", funcstat: "S",
        want: [/Louisville Central/, /Jefferson County/, /no one is elected from it/, /Kentucky has no townships/],
        reject: [/\bCCD\b/] },
      { name: "a subdivision the Census records as nonfunctioning says so", funcstat: "N",
        want: [/Louisville Central/, /no functioning government/],
        reject: [/draws to report its counts/] },
      { name: "a status code the card does not carry prints NO government row", funcstat: "A",
        want: [/Louisville Central/, /Jefferson County/],
        reject: [/Government/] }
    ]) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=county-subdivision`, async (p) => {
        // The layer is drawn and answered from a tile archive since 2026-10-17;
        // refusing it sends the card to the census loader, which this stub answers
        // (the archive-failure path il's smoke check 2d also holds).
        await p.route("**/data/app/tiles/county-subdivision.pmtiles", (r) => r.abort());
        await p.route("**/Places_CouSub_ConCity_SubMCD/MapServer/1/query**", (r) =>
          r.fulfill({ status: 200, contentType: "application/json",
            body: cousubBody(Object.assign({}, record, { FUNCSTAT: c.funcstat })) }));
      });
      const info = await cardText(page, "county-subdivision");
      const text = info.text || "";
      const missing = c.want.filter((re) => !re.test(text));
      const present = c.reject.filter((re) => re.test(text));
      check(`county-subdivision: ${c.name}`, !info.error && missing.length === 0 && present.length === 0,
        missing.length || present.length
          ? `missing=${missing} unwanted=${present} text=${text.slice(0, 160)}`
          : text.slice(0, 90));
      await context.close();
    }
  }

  // 2i. The Magistrate or Council District layer (ky-county-districts.json,
  //     composed by ky/scripts/build_ky_county_districts.py). At the anchor it
  //     answers a Louisville Metro Council district and names the member the
  //     roster gives that district; at Elizabethtown it answers a Hardin County
  //     magisterial district and names its magistrate where the 2022 results
  //     matched one; at Frankfort (Franklin, not drawn) it says the county's
  //     districts are not drawn rather than "no district".
  for (const c of [
    { point: POINT, geoid: "21111", title: /Louisville Metro Council District (\d+)/ },
    { point: "37.69390,-85.85910", geoid: "21093", title: /Hardin County Magisterial District (\d+)/ },
    { point: "38.20090,-84.87330", geoid: "21073", title: null }
  ]) {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${c.point}&layers=fiscal-court`);
    const roster = await page.evaluate(() =>
      fetch("data/app/ky-county-officials.json").then((r) => r.json()));
    const rec = roster[c.geoid] || {};
    const info = await cardText(page, "fiscal-court");
    const text = info.text || "";
    if (!c.title) {
      check("fiscal-court says Franklin County's districts are not drawn yet",
        !info.error && /Districts not drawn here/.test(text) && /does not draw them yet/.test(text),
        text.slice(0, 160));
    } else {
      const m = c.title.exec(text);
      const own = m ? (rec.members || []).filter((x) => String(x.district) === m[1]) : [];
      check(`fiscal-court answers ${c.geoid} with its district and the member the roster gives it`,
        !info.error && !!m && own.length > 0 && own.every((x) => text.includes(x.name)),
        `district ${m ? m[1] : "none"}; roster members there ${own.map((x) => x.name).join(", ") || "none"} | card: ${text.slice(0, 160)}`);
    }
    await context.close();
  }

  // 2j. The School Board Division layer (ky-school-board-divisions.json,
  //     composed by ky/scripts/build_ky_school_board_divisions.py). No list
  //     of members by division has been read (gap ky-school-board-members), so
  //     every card MUST say the members are not named and MUST NOT render a
  //     person row or any field beyond the ones the module writes; each card
  //     must also say how its line was drawn and link the board's own page.
  //     The anchor is in Jefferson County's Division 4, drawn from KRS 160.211.
  //     38.27000,-85.55000 is in precinct F155, which the statute's lists leave
  //     out, so its card must place it in no division and name no division.
  //     Morehead is in Rowan County's Division 4, drawn from the 2024 general
  //     election's results. Frankfort, in Franklin County, is in no division
  //     this map draws, and the card must say so rather than name one.
  {
    const SB = "school-board-district";
    const interim = Date.now() < Date.UTC(2027, 0, 1);
    const cases = [
      { what: "Jefferson County Division 4, drawn from KRS 160.211", point: POINT,
        title: "Division 4", note: "Jefferson County Board of Education",
        must: ["KRS 160.211", "November 3, 2026", "within 8 metres",
               "Anchorage Independent School District", "127 precincts"],
        labels: interim
          ? ["Who it elects", "Until the new board takes office", "Members", "How this line is drawn"]
          : ["Who it elects", "Members", "How this line is drawn"],
        link: "https://www.jefferson.kyschools.us/page/board-of-education" },
      { what: "precinct F155, on none of the statute's lists", point: "38.27000,-85.55000",
        title: "Placed in no division", note: "Precinct F155, Jefferson County",
        must: ["KRS 160.211", "No such assignment has been found published",
               "3.31 km² in all", "597 ballots"],
        mustNot: [/Division\s+[1-5]\b/],
        labels: ["Why no division", "Size", "Ballots in 2022"],
        link: "https://www.jefferson.kyschools.us/page/board-of-education" },
      { what: "Rowan County Division 4, drawn from election results", point: "38.18400,-83.43270",
        title: "Division 4", note: "Rowan County Board of Education",
        must: ["From election results", "November 5, 2024", "within 8 metres",
               "4th Educational District"],
        labels: ["Who it elects", "Members", "How this line is drawn"],
        link: "https://www.rowan.kyschools.us/page/board-of-education" },
      { what: "Frankfort, in a county whose divisions are not drawn", point: "38.20090,-84.87330",
        empty: true }
    ];
    for (const c of cases) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${c.point}&layers=${SB}`);
      const info = await cardText(page, SB);
      const text = info.text || "";
      if (c.empty) {
        check(`${SB} at ${c.what} says no division is drawn there`,
          !info.error && info.empty && /not drawn here yet/.test(text) && !/Division\s+[1-5]\b/.test(text),
          text.slice(0, 160));
        await context.close();
        continue;
      }
      const dom = await page.evaluate((cid) => {
        const el = document.getElementById("card-" + cid);
        const block = el && el.closest(".layer-block");
        const pick = (sel) => { const n = el && el.querySelector(sel); return n ? n.textContent.trim() : null; };
        const link = block && block.querySelector(".card-footer-link");
        return {
          title: pick(".card-intro-title"),
          note: pick(".card-intro-note"),
          labels: el ? Array.from(el.querySelectorAll(".card-field-label")).map((n) => n.textContent.trim()) : [],
          fields: el ? Array.from(el.querySelectorAll(".card-field")).map((f) => {
            const l = f.querySelector(".card-field-label");
            const v = f.querySelector(".card-field-value");
            return { label: l ? l.textContent.trim() : null, value: v ? v.textContent.trim() : "" };
          }) : [],
          persons: el ? el.querySelectorAll(".card-person, .card-person-name").length : -1,
          href: link ? link.getAttribute("href") : null
        };
      }, SB);
      const missing = c.must.filter((m) => !text.includes(m));
      const unwanted = (c.mustNot || []).filter((re) => re.test(text)).map(String);
      check(`${SB} at ${c.what}: names the division and says how it was drawn`,
        !info.error && dom.title === c.title && dom.note === c.note &&
          missing.length === 0 && unwanted.length === 0 &&
          JSON.stringify(dom.labels) === JSON.stringify(c.labels) && dom.href === c.link,
        `title=${dom.title} note=${dom.note} labels=${JSON.stringify(dom.labels)} href=${dom.href}` +
          ` missing=${JSON.stringify(missing)} unwanted=${JSON.stringify(unwanted)} | ${text.slice(0, 120)}`);
      // The member half: no person row anywhere on the card, and where the
      // card has a Members field it says nobody is named.
      const members = dom.fields.filter((f) => f.label === "Members");
      const membersOk = c.labels.includes("Members")
        ? members.length === 1 && /^Not named here\./.test(members[0].value)
        : members.length === 0;
      check(`${SB} at ${c.what}: names no board member`,
        !info.error && dom.persons === 0 && membersOk,
        `person rows=${dom.persons} members=${JSON.stringify(members)}`);
      await context.close();
    }
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
} finally {
  await browser.close();
}

if (failures.length) {
  console.error(`\n${failures.length} smoke check(s) failed: ${failures.join(", ")}`);
  process.exit(1);
}
console.log("\nAll smoke checks passed.");
