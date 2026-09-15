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
// ("L is not defined"). The repo-root scripts/vendor_leaflet.sh populates this dir via curl,
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

const BASE = process.env.BASE_URL || "http://localhost:8000/";
// ==== GENERATED:BEGIN smoke-config ====
const POINT = "41.88250,-87.62850"; // downtown Loop — inside Cook County
const OFFLINE = ["school-board", "il-supreme-court", "ccbr"];
const EXPECT_DISTRICT = { "school-board": "12", "il-supreme-court": "1", "ccbr": "3" };
const NEGATIVE_POINT = "41.70000,-87.10000"; // Lake Michigan, Indiana waters — outside all three anchor layers
const APP_NAME = "districtry Illinois";
const EXPECT_LAYERS = 40; // 17 base + police-beat (#43) + school-site (#45) + ccpsa-district-council + ward-precinct + 6 statewide local-gov layers (county, township, municipality, school districts x3 — TIGERweb) + 6 consolidated county-dispatched layers (county-board, judicial-subcircuit, fire-district, park-district, library-district, county-precinct — Cook/Will/DuPage/Lake/Kane/McHenry/Kendall entries; docs/COUNTY_LAYER_CONSOLIDATION.md) + 1 DuPage-only layer (dupage-county-special-police) + 2 Cook-only tax-agency layers (tif-district, mwrd — dedicated until a second county ships the concept) + 1 Chicago-only special-service layer (ssa — dedicated until a second municipality ships the concept) + 3 amenity nearest-point layers (post-office, library, early-voting) = 40 — THE SUM IS THE CLAIM, so a new layer needs its own term here and not just a bigger total: this read 39 for the day the `ssa` layer shipped because the total was the only part anyone would have changed. NOTHING GATES THIS NOTE — validate_doc_counts.py compares prose against layers[] and deliberately does not scan the worksheet it takes as canonical, so this is hand-kept. Addition re-checked against layers[] 2026-09-12; the underlying live verification of the layer list was 2026-07
// ==== GENERATED:END smoke-config ====
// ==== TEMPLATE:BEGIN smoke-fork-constants ====
// Fork constants: every Chicago/Illinois literal the checks below use. Layer
// ids (school-board, ccbr, county-board, fire-district, …) are deliberately
// NOT here — they are worksheet-driven and stay inline in the checks.
const EXPORTS_NAME = "ChiExplorer"; // the fork's window debug namespace
const PORTAL_HOST = "data.cityofchicago.org"; // the Socrata portal chicagoCoverage's fallback leg consults (check 2b aborts it)
// Geocoder fixture (check 1b): the stub answers ONLY the cleaned form, which
// is what the real geocoder does for these queries.
const GEOCODER_QUERY_RAW = "233 S Wacker Dr Suite 8400, Chicago"; // typed query carrying a unit fragment
const GEOCODER_UNIT_FRAGMENT = "Suite 8400"; // the fragment the retry must strip
const GEOCODER_QUERY_CLEANED = "233 S Wacker Dr, Chicago"; // the only q the stub answers
const GEOCODER_STUB_FEATURE = {
  type: "Feature",
  geometry: { type: "Point", coordinates: [-87.6359, 41.8789] },
  properties: { housenumber: "233", street: "South Wacker Drive", city: "Chicago", state: "Illinois", postcode: "60606" },
};
// Gaps-panel location probe (check 1a): a point in a county that shipped gap
// records name, so the panel must lead with that county's own gaps there.
const GAP_PROBE = { county: "kankakee", label: "Kankakee", lat: 41.1254, lng: -87.8487 };
// Point-move probe (check 2): a second point in a DIFFERENT district of the
// first anchor layer than the ground-truth POINT, exercising the
// incremental-restyle fast path. district is the expected identifier there.
const MOVE_POINT = { lat: 41.99, lng: -87.66, district: "4" }; // school-board district 4 (vs 12 at the Loop POINT)
// Straggler fixture (check 2d): one same-origin county-board county's
// geometry to delay, plus a point inside one of that county's districts.
// App-RELATIVE on purpose: this doubles as a page.route glob ("**/" + it), and
// an un-prefixed form matches whatever path the instance is served from. Disk
// reads go through INSTANCE_DIR (below), which anchors APP_DIR to this script
// rather than to the process CWD.
const STRAGGLER_FILE = "data/app/stephenson-county-board-districts.json";
const APP_DIR = "il/";
const STRAGGLER_POINT = "42.29660,-89.62120"; // Freeport, Stephenson County — inside board District B of the delayed file
// Anchor layers that declare a location-relevance test (mod.coverage) HIDE at
// an out-of-coverage point instead of reporting an empty card — this list
// mirrors the fork's coverage declarations in index.html (school-board is
// Chicago-scoped via chicagoCoverage; ccbr is Cook-scoped via
// cookCountyCoverage). il-supreme-court declares none and keeps the honest
// "no district here" empty state at the negative point.
const NEGATIVE_HIDDEN = ["school-board", "ccbr"];
// ==== TEMPLATE:END smoke-fork-constants ====

// Disk reads are anchored to THIS SCRIPT, never to the process CWD. APP_DIR
// names the instance folder; joining it here is what makes a bare `node
// scripts/smoke_test.mjs` work from any directory. While each instance was its
// own repo a bare "data/app/…" read was correct, because you ran the test from
// that repo's root — they are folders under one root now, and the un-anchored
// form silently resolves against wherever you happen to be standing.
const INSTANCE_DIR = join(dirname(dirname(fileURLToPath(import.meta.url))), APP_DIR);
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
      ["118 NORTH CLARK STREET ROOM 230 CHICAGO, IL 60602", "118 NORTH CLARK STREET CHICAGO, IL 60602"], // embedded Room
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
      // Chicago renders four large ones, and both satisfy the same assertions.
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
    check("data gaps panel renders every recorded gap, grouped with honest counts",
      cold.items === expected && cold.groups.length >= 1 &&
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

    // ==== TEMPLATE:BEGIN smoke-gap-probe ====
    // With a point selected the panel must lead with the gaps that apply THERE.
    // GAP_PROBE names the strongest probe county in the shipped gap records.
    // (Needs county-tagged gap records at the probe point — forks whose gaps
    // data is not county-tagged drop or payload this span.)
    const probeGaps = Object.values(shipped)
      .filter((g) => (g.counties || []).indexOf(GAP_PROBE.county) !== -1).length;
    await page.evaluate(({ n, lat, lng }) => window[n].setSelectedPoint(lat, lng),
      { n: EXPORTS_NAME, lat: GAP_PROBE.lat, lng: GAP_PROBE.lng });
    const warm = await openGaps();
    check(`data gaps panel is location-aware (${GAP_PROBE.label} point leads with its own gaps)`,
      warm.groups.length >= 2 && /clicked/i.test(warm.groups[0].label) &&
      warm.groups[0].items === probeGaps && warm.items === expected &&
      /clicked/i.test(warm.lede),
      `groups=${JSON.stringify(warm.groups.map((g) => g.label))} ` +
      `here=${warm.groups[0] && warm.groups[0].items}/${probeGaps} total=${warm.items}`);
    // ==== TEMPLATE:END smoke-gap-probe ====

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
    // ==== TEMPLATE:BEGIN smoke-sources-page ====
    // sources.html is OPT-IN per fork (the worksheet's sources_page key): a
    // fork that carries no sources page drops this span — the masthead and
    // #gaps deep-link checks around it stay.
    check("the app points readers at the sources page",
      chrome.sourcesLinks >= 1, `${chrome.sourcesLinks} link(s)`);

    // The matrix must account for EVERY registered layer. Asked of the live
    // page rather than the file, so a broken fence or a half-written region
    // fails here too.
    const ids = await page.evaluate(() =>
      Array.from(document.querySelectorAll('input[type=checkbox][id^="toggle-"]'))
        .map((el) => el.id.replace(/^toggle-/, "")));
    const sources = await context.newPage();
    await sources.goto(new URL("sources.html", BASE).href, { waitUntil: "domcontentloaded" });
    const rows = await sources.evaluate((layerIds) => ({
      total: document.querySelectorAll("table.matrix tbody tr").length,
      missing: layerIds.filter((id) => !document.getElementById("layer-" + id)),
      deadInternal: Array.from(document.querySelectorAll("a[href]"))
        .map((a) => a.getAttribute("href"))
        .filter((h) => h && !/^https?:|^#|^mailto:/.test(h)),
    }), ids);
    check("sources page carries a matrix row for every registered layer",
      rows.missing.length === 0 && rows.total === ids.length,
      `${rows.total} rows for ${ids.length} layers${rows.missing.length ? `, missing ${rows.missing.join(",")}` : ""}`);

    // Every relative link on the page must resolve — the page's whole value is
    // that its links work, and "./" vs "/" is exactly the kind of thing that
    // breaks only once deployed under a path.
    const resolved = [];
    for (const href of new Set(rows.deadInternal)) {
      const r = await context.request.get(new URL(href, new URL("sources.html", BASE).href).href);
      resolved.push(`${href}=${r.status()}`);
    }
    check("sources page's relative links resolve",
      resolved.every((r) => r.endsWith("=200")), resolved.join(" "));
    await sources.close();
    // ==== TEMPLATE:END smoke-sources-page ====

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
    // 33029973722 and 33040783537, both in the WI copy of this same block).
    // Dispatching input and submit in one synchronous task still runs both app
    // handlers — input arms the debounce, submit cancels it and searches — but
    // leaves the timer no gap to fire in.
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
    // ==== TEMPLATE:BEGIN smoke-roster-join ====
    // Bonus: the school-board card joins its externalized member roster.
    const board = await cardText(page, "school-board");
    check("school-board joins member roster", /Board member/i.test(board.text), board.text.slice(0, 70));
    // ==== TEMPLATE:END smoke-roster-join ====

    // ==== TEMPLATE:BEGIN smoke-move-point ====
    // Bonus: moving the selection re-classifies correctly. This exercises the
    // incremental-restyle fast path (P7) — same layers on, new point — where
    // updateLayerHighlight only flips the old/new matched paths instead of
    // re-styling every path. MOVE_POINT is school-board district 4 (vs 12 at
    // the Loop point above), and the matched-region highlight must move with it.
    const moved = await page.evaluate(async ({ n, lat, lng, district }) => {
      window[n].setSelectedPoint(lat, lng);
      const el = document.getElementById("card-school-board");
      // the district identifier lives in the header pill on redesigned cards
      const cardTextNow = () => {
        const block = el && el.closest(".layer-block");
        const pill = block && block.querySelector(".card-id-pill:not([hidden])");
        return ((pill ? pill.textContent + " " : "") + (el ? el.innerText : "")).replace(/\s+/g, " ").trim();
      };
      const districtRe = new RegExp("District\\s+" + district + "\\b", "i");
      for (let i = 0; i < 100; i++) {
        if (el && !el.querySelector(".loading-row") && districtRe.test(cardTextNow())) break;
        await new Promise((r) => setTimeout(r, 100));
      }
      const highlights = document.querySelectorAll("#map .region-highlight").length;
      return { text: el ? cardTextNow() : "(no card)", highlights };
    }, { n: EXPORTS_NAME, lat: MOVE_POINT.lat, lng: MOVE_POINT.lng, district: MOVE_POINT.district });
    check(
      `point move re-classifies (District ${EXPECT_DISTRICT["school-board"]} -> ${MOVE_POINT.district}) and re-highlights`,
      new RegExp("District\\s+" + MOVE_POINT.district + "\\b", "i").test(moved.text) && moved.highlights >= 1,
      `${moved.text.slice(0, 60)} | highlights=${moved.highlights}`
    );
    // ==== TEMPLATE:END smoke-move-point ====

    // ==== TEMPLATE:BEGIN smoke-toggle-preserve ====
    // (If smoke-move-point is dropped, the selection simply stays at POINT —
    // the assertions below only need >= 2 anchor layers highlighting wherever
    // the selection currently sits, so they hold either way.)
    // Bonus: toggling one layer off/on must NOT disturb the other active layers'
    // highlights (P8). The opacity rescale on a count change now skips layers that
    // already show a selection highlight (their faded/highlight fill is
    // count-independent) instead of re-running the full highlight for every layer,
    // so the survivors' matched regions must stay lit exactly through the toggle.
    // With all three offline layers on and a point selected, drop ccbr: its single
    // highlight leaves, the other two stay untouched (before-1); re-add it and the
    // count returns to baseline. Re-adding it also exercises P11: ccbr's Leaflet
    // layer graph is released on toggle-off and rebuilt from the cached geojson on
    // toggle-on — the highlight can only reappear (afterOn === before) if that
    // rebuild produced a working, highlightable overlay with no refetch.
    const toggled = await page.evaluate(async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const count = () => document.querySelectorAll("#map .region-highlight").length;
      const box = document.getElementById("toggle-ccbr");
      const before = count();
      box.click(); // ccbr off
      await wait(150);
      const afterOff = count();
      box.click(); // ccbr back on
      for (let i = 0; i < 100; i++) { if (count() >= before) break; await wait(100); }
      return { before, afterOff, afterOn: count() };
    });
    check(
      "layer toggle preserves other layers' highlights (opacity rescale, P8)",
      toggled.before >= 2 && toggled.afterOff === toggled.before - 1 && toggled.afterOn === toggled.before,
      `before=${toggled.before} afterOff=${toggled.afterOff} afterOn=${toggled.afterOn}`
    );
    // ==== TEMPLATE:END smoke-toggle-preserve ====
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
    // chicagoCoverage's fallback leg consults the community-area dataset
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
        const hashKeepsLayer = await page.evaluate((cid) => location.hash.includes(cid), id);
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

  // ==== TEMPLATE:BEGIN smoke-legacy-aliases ====
  // 2c. Consolidated-layer permalink compatibility: pre-consolidation ids in a
  //     shared link (#layers=commissioner / will-county-board / will-county-fire
  //     / …) must light the consolidated toggles — the fork's alias shim
  //     rewrites those ids before the boot parse reads the hash, where unknown
  //     ids are otherwise dropped silently. Duplicate-producing lists (two old
  //     ids aliasing to the same layer) must collapse to one id.
  //     See docs/COUNTY_LAYER_CONSOLIDATION.md.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#layers=commissioner,will-county-board,will-county-fire`);
    const res = await page.evaluate((n) => {
      const board = document.getElementById("toggle-county-board");
      const fire = document.getElementById("toggle-fire-district");
      const hash = location.hash;
      return {
        boardOn: !!(board && board.checked) && window[n].state.layersOn["county-board"] === true,
        fireOn: !!(fire && fire.checked) && window[n].state.layersOn["fire-district"] === true,
        hashRewritten: hash.indexOf("county-board") !== -1 && hash.indexOf("fire-district") !== -1 &&
          hash.indexOf("commissioner") === -1 && hash.indexOf("will-county-board") === -1 &&
          hash.indexOf("will-county-fire") === -1,
        oneCopy: hash.split("county-board").length === 2,
      };
    }, EXPORTS_NAME);
    check(
      "old permalink ids alias to the consolidated layers",
      res.boardOn && res.fireOn && res.hashRewritten && res.oneCopy,
      `board=${res.boardOn} fire=${res.fireOn} hashRewritten=${res.hashRewritten} deduped=${res.oneCopy}`
    );
    await context.close();
  }
  // ==== TEMPLATE:END smoke-legacy-aliases ====

  // ==== TEMPLATE:BEGIN smoke-straggler ====
  // 2d. The county-board union overlay draws INCREMENTALLY: boundaries appear
  //     as soon as the first county's geometry is in, instead of waiting out
  //     the slowest of ~40 independent county servers (the 2026-08-04
  //     regression report: one slow host kept every county's boundaries off
  //     the map for a minute-plus while the card answered in a second). Delay
  //     one same-origin county's geometry behind a long route stall and assert
  //     (a) other counties' boundaries are on the map well before it lands,
  //     (b) once it lands it is appended to the drawing and the selected
  //     point's own district — inside the delayed county — gets highlighted.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const stragglerBody = readFileSync(join(INSTANCE_DIR, STRAGGLER_FILE), "utf8");
    const stragglerFeatures = JSON.parse(stragglerBody).features.length;
    const STRAGGLER_DELAY_MS = 8000;
    // STRAGGLER_POINT sits inside a district of the delayed county's file
    const page = await booted(
      context,
      `${BASE}#point=${STRAGGLER_POINT}&layers=county-board`,
      (p) => p.route("**/" + STRAGGLER_FILE, async (r) => {
        await new Promise((res) => setTimeout(res, STRAGGLER_DELAY_MS));
        await r.fulfill({ status: 200, contentType: "application/json", body: stragglerBody });
      })
    );
    const overlayPathCount = () =>
      page.evaluate(() => document.querySelectorAll("#map .leaflet-overlay-pane path").length);
    // (a) the fast counties draw long before the straggler's 8 s stall is up
    const EARLY_BUDGET_MS = 4000;
    const earlyDeadline = Date.now() + EARLY_BUDGET_MS;
    let earlyPaths = 0;
    while (Date.now() < earlyDeadline && earlyPaths === 0) {
      earlyPaths = await overlayPathCount();
      if (earlyPaths === 0) await new Promise((res) => setTimeout(res, 200));
    }
    check(
      "county-board boundaries draw before the slowest county settles",
      earlyPaths > 0,
      `${earlyPaths} paths within ${EARLY_BUDGET_MS}ms (straggler stalled ${STRAGGLER_DELAY_MS}ms)`
    );
    // (b) the straggler is appended once it arrives — proven end-to-end by the
    // selection highlight, which can only appear after the delayed county's
    // features are BOTH in rt.geojson and drawn as paths (updateLayerHighlight
    // matches Leaflet sub-layers by feature identity). Disjoint county
    // footprints guarantee no earlier county can light this point up.
    const highlighted = await page
      .waitForFunction(() => document.querySelectorAll("#map path.region-highlight").length >= 1,
        null, { timeout: STRAGGLER_DELAY_MS + QUERY_TIMEOUT })
      .then(() => true, () => false);
    const finalPaths = await overlayPathCount();
    check(
      "late county appends to the drawing and highlights the selected district",
      highlighted && finalPaths >= earlyPaths + stragglerFeatures,
      `highlighted=${highlighted} paths ${earlyPaths} -> ${finalPaths} (straggler has ${stragglerFeatures})`
    );
    await context.close();
  }
  // ==== TEMPLATE:END smoke-straggler ====

  // 2e. Share control: the point chip carries ONE "Share" button whose popover
  //     serves the live campaign-tagged permalink, the embed snippet (tagged
  //     with its own source and pointed at the canonical deployment), and the
  //     coordinates — replacing the old Copy link / Embed pill pair. Headless
  //     desktop Chromium has no navigator.share, so this always exercises the
  //     popover path; Escape must close it.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=school-board`);
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
      const wantUrl = location.origin + location.pathname +
        "?utm_source=share&utm_medium=link" + location.hash;
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      return {
        opened: true,
        urlOk: url === wantUrl,
        linkTagged: url.indexOf("?utm_source=share&utm_medium=link#") !== -1,
        embedTagged: embed.indexOf("?utm_source=embed&utm_medium=iframe") !== -1,
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

  // 2f. THE PINNED PARENT SURVIVES A SHARED LINK, and a pin that cannot be
  //     honoured is dropped rather than half-applied. Both halves need a
  //     browser: pinnedParentId is not exported, so the only honest reading
  //     of the restore is the card button's own pressed state, and the only
  //     honest reading of the write is location.hash after a real click.
  //
  //     This runs on Illinois alone and covers all six instances, for the
  //     reason compose_app --check establishes: the permalink and
  //     relationship-pinning blocks are ONE copy spliced byte-identically
  //     into every instance, so the path a browser exercises here is the same
  //     path everywhere. What is instance-specific is the fixture — a polygon
  //     layer, switched on, with a district at the anchor point — and
  //     school-board is that layer here, same-origin so it needs no network.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=school-board&pin=school-board`);
    await cardText(page, "school-board"); // the pin control is appended as the card renders
    // The `card-<id>` id is on the card BODY and the pin control is appended
    // to a SIBLING `.card-footer`, so `#card-school-board .pin-parent-btn`
    // matches nothing — measured, on the first run of this check. The card
    // BLOCK is the body's parent, and that is what scopes a card's controls.
    const restored = await page.evaluate(() => {
      const btn = document.getElementById("card-school-board").parentElement
        .querySelector(".pin-parent-btn");
      return {
        present: !!btn,
        pressed: btn && btn.getAttribute("aria-pressed") === "true",
        styled: btn && btn.classList.contains("is-pinned"),
        inHash: /(^|[#&])pin=school-board(&|$)/.test(location.hash),
      };
    });
    check(
      "a shared #pin= restores the pinned parent and stays in the hash",
      restored.present && restored.pressed && restored.styled && restored.inHash,
      JSON.stringify(restored)
    );

    // The write path: unpin, then re-pin, reading the hash after each.
    //
    // `inHash` above is NOT redundant with this, which is worth stating
    // because it looks it: the incoming `pin=` does not simply survive. The
    // point selection inside applyStateFromHash runs syncUrlHash while
    // pinnedParentId is still null, which REWRITES the hash without the pin,
    // and the restore that follows is the only thing that puts it back —
    // through setPinnedParent's own syncUrlHash call. Measured by removing
    // that one call: the button reads pressed and styled, and the hash the
    // reader would copy has no pin in it.
    const roundTrip = await page.evaluate(() => {
      const btn = document.getElementById("card-school-board").parentElement
        .querySelector(".pin-parent-btn");
      btn.click();
      const afterUnpin = {
        pressed: btn.getAttribute("aria-pressed") === "true",
        inHash: /(^|[#&])pin=/.test(location.hash),
      };
      btn.click();
      const afterRepin = {
        pressed: btn.getAttribute("aria-pressed") === "true",
        inHash: /(^|[#&])pin=school-board(&|$)/.test(location.hash),
      };
      return { afterUnpin, afterRepin };
    });
    check(
      "unpinning drops pin= from the hash and re-pinning puts it back",
      !roundTrip.afterUnpin.pressed && !roundTrip.afterUnpin.inHash &&
        roundTrip.afterRepin.pressed && roundTrip.afterRepin.inHash,
      JSON.stringify(roundTrip)
    );
    await context.close();
  }

  // 2g. The three ways a pin is refused, each driven separately, because a
  //     single "no pin" result cannot tell which guard fired — and a guard
  //     that has never refused anything has not been tested. fire-station is
  //     a nearest-point layer: it is switched ON here, so the layersOn guard
  //     passes and the polygon guard is the one under test.
  {
    const cases = [
      ["an id no layer registers", "&layers=school-board&pin=not-a-layer"],
      ["a layer that is not switched on", "&layers=school-board&pin=il-supreme-court"],
      ["a layer with no polygons", "&layers=school-board,fire-station&pin=fire-station"],
    ];
    for (const [why, tail] of cases) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}${tail}`);
      await cardText(page, "school-board"); // one card rendered = the hash parse is done
      const res = await page.evaluate(() => ({
        inHash: /(^|[#&])pin=/.test(location.hash),
        anyPressed: !!document.querySelector('.pin-parent-btn[aria-pressed="true"]'),
        hash: location.hash,
      }));
      check(
        `a pin naming ${why} is dropped, not half-applied`,
        !res.inHash && !res.anyPressed,
        JSON.stringify(res)
      );
      await context.close();
    }
  }

  // 2h. An aliased pin is rewritten with the layers. This is ILLINOIS-ONLY
  //     code — CONSOLIDATED_LAYER_ALIASES and rewriteAliasedPermalink live
  //     outside every engine fence — and it is here because the shim ran on
  //     `layers=` alone: a link shared before the county consolidation
  //     carries the old id in BOTH parameters, and a rewrite that fixed one
  //     of them would light the consolidated layer and silently drop the pin.
  //     The hash is the whole assertion: `pin=` is emitted only while its
  //     layer is on, so reading `pin=county-board` back proves the alias was
  //     applied AND the restore honoured it.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=commissioner&pin=commissioner`);
    await cardText(page, "county-board");
    const res = await page.evaluate(() => ({
      aliased: /(^|[#&])pin=county-board(&|$)/.test(location.hash),
      oldGone: location.hash.indexOf("commissioner") === -1,
      hash: location.hash,
    }));
    check(
      "an old permalink id in pin= aliases with the layers",
      res.aliased && res.oldGone,
      JSON.stringify(res)
    );
    await context.close();
  }

  // ==== TEMPLATE:BEGIN smoke-failure-isolation ====
  // 3. A failing data source degrades to that layer's error card + Retry, in
  //    isolation — the app's per-layer failure-isolation rule. (Named on two
  //    CHI anchor layers and one same-origin data file — a fork keeps the
  //    scenario by payloading this span with two of its own anchors.)
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(
      context,
      `${BASE}#point=${POINT}&layers=school-board,ccbr`,
      (p) => p.route("**/data/app/school-board-districts.json", (r) => r.fulfill({ status: 503, body: "down" }))
    );
    await page
      .waitForFunction(
        () => {
          const el = document.getElementById("card-school-board");
          return el && el.classList.contains("state-error");
        },
        null,
        { timeout: QUERY_TIMEOUT }
      )
      .catch(() => {});
    const res = await page.evaluate(() => {
      const sb = document.getElementById("card-school-board");
      const other = document.getElementById("card-ccbr");
      // the surviving layer's district identifier lives in its header pill
      const otherBlock = other && other.closest(".layer-block");
      const otherPill = otherBlock && otherBlock.querySelector(".card-id-pill:not([hidden])");
      const otherText = (otherPill ? otherPill.textContent + " " : "") + (other ? other.innerText : "");
      return {
        errored: !!sb && sb.classList.contains("state-error"),
        hasRetry: !!sb && !!sb.querySelector(".retry-btn"),
        otherOk: !!other && !other.classList.contains("state-error") && /District/i.test(otherText),
      };
    });
    check("failed layer shows error card + Retry", res.errored && res.hasRetry);
    check("failure is isolated (other layer still classifies)", res.otherOk);
    await context.close();
  }
  // ==== TEMPLATE:END smoke-failure-isolation ====

  // ==== TEMPLATE:BEGIN smoke-prepoint-failure ====
  // 4. Overlay-load failure with NO point selected still surfaces (R5 / item 7).
  //    Toggle a layer via the permalink before any point is picked and fail its
  //    boundary fetch — the card must show an error + Retry (un-hidden), not
  //    fail silently the way it used to on 15 of 18 layers.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(
      context,
      `${BASE}#layers=school-board`,
      (p) => p.route("**/data/app/school-board-districts.json", (r) => r.fulfill({ status: 503, body: "down" }))
    );
    await page
      .waitForFunction(
        () => {
          const el = document.getElementById("card-school-board");
          return el && el.classList.contains("state-error");
        },
        null,
        { timeout: QUERY_TIMEOUT }
      )
      .catch(() => {});
    const res = await page.evaluate((n) => {
      const el = document.getElementById("card-school-board");
      return {
        pointSelected: !!(window[n] && window[n].state.selectedPoint),
        errored: !!el && el.classList.contains("state-error"),
        hasRetry: !!el && !!el.querySelector(".retry-btn"),
        visible: !!el && getComputedStyle(el).display !== "none",
      };
    }, EXPORTS_NAME);
    check(
      "pre-point overlay failure surfaces (not silent)",
      !res.pointSelected && res.errored && res.hasRetry && res.visible,
      `point=${res.pointSelected} err=${res.errored} retry=${res.hasRetry} visible=${res.visible}`
    );
    await context.close();
  }
  // ==== TEMPLATE:END smoke-prepoint-failure ====

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

  // 6. Dark mode (R4.2) — the one function the re-skin ADDS, so it is the one
  //    that has no prior behaviour to fall back on if it breaks. Asserted
  //    through the surfaces a CSS-only check cannot see: the theme attribute,
  //    the ground the page actually paints, the theme-color meta the OS chrome
  //    reads, the basemap tile URL, and the derived layer palette repainting a
  //    live overlay. Driven via the debug namespace rather than a click, so
  //    this tests the controller and not the button's hit box.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=${OFFLINE[0]}`);
    await page.waitForFunction(() => !!window[EXPORTS_NAME] && !!window[EXPORTS_NAME].setTheme,
      null, { timeout: QUERY_TIMEOUT }).catch(() => {});
    const read = () => page.evaluate((n) => {
      const path = document.querySelector("#map path");
      // The vector basemap is a GL canvas with no tile <img> whose src names
      // its style, so the basemap kind comes from the debug namespace; the
      // raster-fallback img sampler stays for a boot that fell back.
      const base = window[n] && window[n].basemap ? window[n].basemap() : null;
      return {
        attr: document.documentElement.getAttribute("data-theme"),
        ground: getComputedStyle(document.body).backgroundColor,
        meta: document.querySelector('meta[name="theme-color"]')?.content,
        tiles: (document.querySelector(".leaflet-tile-pane img")?.src || "").match(/(light|dark)_all/)?.[1]
          || (base ? (base.kind === "dark_all" ? "dark" : "light") : null),
        stroke: path ? path.getAttribute("stroke") : null,
      };
    }, EXPORTS_NAME);
    await page.evaluate((n) => window[n].setTheme("light", false), EXPORTS_NAME);
    await page.waitForTimeout(400);
    const light = await read();
    await page.evaluate((n) => window[n].setTheme("dark", false), EXPORTS_NAME);
    await page.waitForTimeout(600);
    const dark = await read();

    check("dark mode flips the theme attribute and the painted ground",
      light.attr === "light" && dark.attr === "dark" && light.ground !== dark.ground,
      `${light.attr}/${light.ground} -> ${dark.attr}/${dark.ground}`);
    check("dark mode moves theme-color (the OS chrome reads it)",
      !!light.meta && !!dark.meta && light.meta !== dark.meta,
      `${light.meta} -> ${dark.meta}`);
    check("dark mode swaps the basemap tiles",
      light.tiles === null || dark.tiles === null || (light.tiles === "light" && dark.tiles === "dark"),
      `${light.tiles} -> ${dark.tiles}`);
    check("dark mode repaints a live overlay from the derived palette",
      light.stroke === null || dark.stroke === null || light.stroke !== dark.stroke,
      `${light.stroke} -> ${dark.stroke}`);
    await context.close();
  }

  // 7. The USGS structures loader PAGES past the service's transfer cap.
  //     This guards a defect that shipped and was invisible: carto.nationalmap.gov
  //     caps at maxRecordCount 2,000 and flags exceededTransferLimit when it
  //     truncates, and Illinois's envelope holds 2,820 fire stations (L51) —
  //     measured live 2026-09-05 — so a single request answered the nearest-3
  //     card over 2,000 of them. Nothing failed: a truncated FeatureCollection is
  //     a valid one, and a nearest-N card always has an answer. Over a uniform
  //     40x40 grid of the bbox the truncated set named a different nearest-3 at
  //     58% of points and a different NEAREST station at 27%.
  //     The service is stubbed rather than called, for the reason every stub here
  //     exists: a gate that needs a third party up fails on somebody else's
  //     schedule. The stub reproduces the cap exactly — 2,000 per page with the
  //     flag set while more remain — so the assertion is on the app's behaviour
  //     against that contract, not on today's national feature count.
  {
    const CAP = 2000, TOTAL = 2820;      // the live cap and the live Illinois count
    const seen = [];
    // ESRI JSON, not GeoJSON — the shape the app now asks these services for.
    // Every ArcGIS loader moved to f=json on 2026-09-05, because the GeoJSON
    // export unnests interior rings (engine/index.html/arcgis-loader.txt), and
    // a stub that keeps answering GeoJSON is no longer reproducing the
    // service's contract. The assertion below is unchanged; only the wire
    // format is.
    const stubFeature = (i) => ({
      attributes: { name: "Station " + i, address: i + " Main St", city: "Town", state: "IL", zipcode: "60000" },
      geometry: { x: -87.63 + (i % 100) * 0.001, y: 41.88 + Math.floor(i / 100) * 0.001 },
    });
    const context = await browser.newContext({ serviceWorkers: "block" });
    // ONE handler for every structures layer, branching on the layer index:
    // two page.route patterns would collide, since the most recently
    // registered wins and a broad one swallows the specific one.
    const page = await booted(context, `${BASE}#point=${POINT}&layers=fire-station`, (p) =>
      p.route("**/structures/MapServer/**", (r) => {
        const u = new URL(r.request().url());
        const m = /\/MapServer\/(\d+)\/query/.exec(u.pathname);
        if (!m) return r.continue();
        const body = (feats, more) => r.fulfill({
          status: 200, contentType: "application/json",
          body: JSON.stringify({ features: feats, exceededTransferLimit: more }),
        });
        if (m[1] !== "51") return body([stubFeature(0)], false);
        const offset = parseInt(u.searchParams.get("resultOffset") || "0", 10);
        const want = parseInt(u.searchParams.get("resultRecordCount") || "0", 10);
        seen.push(offset);
        const n = Math.min(CAP, want || CAP, Math.max(0, TOTAL - offset));
        const feats = [];
        for (let i = offset; i < offset + n; i++) feats.push(stubFeature(i));
        return body(feats, offset + n < TOTAL);
      }));
    const fire = await cardText(page, "fire-station");
    check("USGS structures loader pages past the 2,000-row transfer cap",
      seen.length === 2 && seen[0] === 0 && seen[1] === CAP && !fire.error,
      `offsets requested: [${seen.join(", ")}]`);
    await context.close();
  }

/* ---------- 12. batch address check --------------------------------------
 * The panel runs the app's OWN layer machinery down a pasted list — the
 * overlay loaders, mod.coverage(), findFeatureContaining(), hoverValue() —
 * all of which the checks above already cover. What needs proving here is the
 * part that is not the app's: that a list becomes rows, that each row says how
 * precisely the geocoder resolved it and how far the point sits from the edge
 * of the district it landed in, that the review flags fire, and that the CSV
 * carries the same values the table shows.
 *
 * PHOTON IS STUBBED. A gate that needs a third party to be up, and to rank a
 * given address the same way today as it did yesterday, fails on somebody
 * else's schedule — the rule scripts/landing_test.mjs already follows for the
 * front door's box. The stub matches a MARKER WORD rather than the whole
 * query, so cleanPoiAddress() stays free to rewrite what it sends.
 */
{
  const context = await browser.newContext({ serviceWorkers: "block", acceptDownloads: true });
  const [LAT, LNG] = POINT.split(",").map(Number);
  const [NLAT, NLNG] = NEGATIVE_POINT.split(",").map(Number);
  // Marker word -> what Photon answers. HOUSE carries a housenumber (a rooftop
  // match). STREET does not, which is the case worth having a column for: the
  // geocoder found the street, and that is no answer at all to a question
  // about which side of that street somebody lives on. MISS answers with no
  // features at all. OUTSIDE is a clean rooftop match beyond the layer's
  // coverage.
  const FIXTURES = {
    HOUSE: { lat: LAT, lng: LNG, props: { housenumber: "233", street: "S Wacker Dr", city: "Chicago" } },
    STREET: { lat: LAT, lng: LNG, props: { street: "S Wacker Dr", city: "Chicago" } },
    OUTSIDE: { lat: NLAT, lng: NLNG, props: { housenumber: "1", street: "Shore Dr", city: "Chicago" } },
    MISS: null,
  };
  const stubPhoton = (p) => p.route("**photon.komoot.io**", (r) => {
    const q = (new URL(r.request().url()).searchParams.get("q") || "").toUpperCase();
    const key = Object.keys(FIXTURES).find((k) => q.includes(k));
    const fx = key ? FIXTURES[key] : null;
    return r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        features: fx ? [{ type: "Feature", properties: fx.props,
          geometry: { type: "Point", coordinates: [fx.lng, fx.lat] } }] : [],
      }),
    });
  });

  // The panel's own width and the width of the form column inside it. The two
  // move independently by design, which is the whole of what the check below
  // asserts — so it reads them relationally rather than pinning the px values
  // the CSS already owns.
  const panelWidths = (page) => page.evaluate(() => {
    const w = (s) => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().width) : null; };
    const box = document.getElementById("batch-results");
    const tbl = box && box.querySelector("table");
    return { panel: w(".batch-panel"), lede: w(".batch-lede"), picker: w(".batch-layers"),
      textarea: w("#batch-input"),
      overflows: tbl && box && !box.hidden ? tbl.scrollWidth > box.clientWidth + 1 : null };
  });

  // Drive one run and return the rendered table as plain text rows. The wait
  // is on the run having FINISHED (the button re-enabled) as well as on the
  // row count, so a check can never read a half-built table.
  async function runList(page, lines, thresholdFt) {
    if (await page.isHidden("#batch-modal")) await page.click("#batch-btn");
    await page.fill("#batch-input", lines.join("\n"));
    if (thresholdFt !== undefined) await page.fill("#batch-threshold", String(thresholdFt));
    await page.click("#batch-run");
    await page.waitForFunction((n) => {
      const rows = document.querySelectorAll("#batch-results tbody tr");
      return rows.length === n && !document.getElementById("batch-run").disabled;
    }, lines.length, { timeout: QUERY_TIMEOUT });
    return page.evaluate(() => Array.from(document.querySelectorAll("#batch-results tbody tr"))
      .map((tr) => Array.from(tr.children).map((td) => td.textContent)));
  }

  {
    // school-board is one of the three no-API layers, so this check needs no
    // government endpoint either. The portal abort is check 2b's, for the same
    // reason: chicagoCoverage's fallback leg would otherwise stall the
    // out-of-coverage verdict behind a slow rejection.
    const page = await booted(context, `${BASE}#point=${POINT}&layers=school-board`, async (p) => {
      await p.route(`**${PORTAL_HOST}**`, (r) => r.abort());
      await stubPhoton(p);
    });

    // The picker inherits what the reader already has switched on.
    const picked = await page.evaluate(() => {
      document.getElementById("batch-btn").click();
      return Array.from(document.querySelectorAll("#batch-layers input"))
        .filter((cb) => cb.checked).map((cb) => cb.parentNode.textContent.trim());
    });
    check("batch picker inherits the layers already switched on",
      picked.length === 1 && /School Board/.test(picked[0]), picked.join(", ") || "(none)");

    const formOnly = await panelWidths(page);

    const rows = await runList(page, [
      "233 HOUSE Dr, Chicago",
      "1 STREET Ave, Chicago",
      "9 MISS Rd, Chicago",
      "1 OUTSIDE Dr, Chicago",
    ]);
    const cols = rows[0] ? rows[0].length : 0;
    check("batch turns a pasted list into one row per address",
      rows.length === 4 && cols === 7, `${rows.length} row(s) x ${cols} column(s)`);

    // The window is sized to the form until there is a table to be wide for.
    // The form column must NOT move when it grows: a table appearing is no
    // reason for the prose and the picker to change shape, and the panel is
    // 688px wide precisely because that is what the picker needs.
    const withRows = await panelWidths(page);
    check("the window widens for the results table and the form column does not",
      withRows.panel > formOnly.panel &&
      withRows.lede === formOnly.lede && withRows.picker === formOnly.picker &&
      withRows.textarea === formOnly.textarea,
      `panel ${formOnly.panel} -> ${withRows.panel}px; form column ${formOnly.picker}px in both`);
    // One selected layer is the case this tool was built for, and at that width
    // its table must not need a sideways scroll to reach the Review column.
    check("one layer's results table needs no horizontal scroll",
      withRows.overflows === false, `table overflows its box: ${withRows.overflows}`);

    // [#, Address, Matched, Match, <layer>, Edge (ft), Review]
    const [house, street, miss, outside] = rows.map((r) => r || []);
    check("batch classifies a rooftop match against the layer",
      house[3] === "house" && house[4].includes(EXPECT_DISTRICT["school-board"]),
      `match=${house[3]} district=${house[4]}`);
    check("batch measures the distance to the district's own edge",
      Number(house[5]) > 0, `${house[5]} ft`);
    check("a deep-interior point is not flagged at the default threshold",
      house[6] === "", house[6] || "(no flags)");
    check("batch flags a street-level match as not an address",
      street[3] === "street" && /matched the street/.test(street[6]), street[6]);
    // The wording matters as much as the flag: geocodeOne is bounded to
    // METRO_BBOX, so this must not claim the address does not exist when it
    // may simply sit outside the envelope.
    check("batch flags a miss as the bounded search it was",
      miss[3] === "none" && /no match in the .* search area/.test(miss[6]), miss[6]);
    check("batch reports out-of-coverage rather than inventing a district",
      /outside coverage/.test(outside[4]) && /outside .* coverage/.test(outside[6]),
      `cell=${outside[4]} review=${outside[6]}`);

    // The two-sided half of the edge measurement. The same point that went
    // unflagged above must flag when the reader widens the review distance
    // past its measured distance to the line — otherwise "not flagged" would
    // only ever have proved that the threshold never fires.
    const wide = await runList(page, ["233 HOUSE Dr, Chicago"], Math.ceil(Number(house[5])) + 10);
    check("widening the review distance flags the same point",
      /\d+ ft from a .* line/.test(wide[0][6]), wide[0][6]);

    // Back to the four-row run, so the CSV is checked against a table that
    // carries every case rather than the single row above.
    const table = await runList(page, [
      "233 HOUSE Dr, Chicago",
      "1 STREET Ave, Chicago",
      "9 MISS Rd, Chicago",
      "1 OUTSIDE Dr, Chicago",
    ], 150);
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.click("#batch-csv"),
    ]);
    const csv = readFileSync(await download.path(), "utf8");
    const csvRows = csv.replace(/^﻿/, "").trim().split("\r\n");
    const header = csvRows[0].split(",");
    check("CSV header names the address, the match and every checked layer",
      csvRows.length === 5 && header[1] === "address" && header[5] === "match" &&
      /School Board/.test(header[6]) && header.slice(-1)[0] === "review",
      `${csvRows.length - 1} data row(s): ${header.join("|")}`);
    // The CSV is the deliverable people work from, so it has to carry the
    // table's own values rather than a second derivation of them.
    // Compared against the TABLE's own cells, never against a literal. The
    // first version of this check retyped the miss flag, so rewording that
    // flag updated one copy and left this one red — the gate working, and a
    // second literal not worth keeping. table[2] is the miss row; csvRows[3]
    // is the same row once the header is counted.
    check("CSV carries the values the table shows",
      csvRows[1].includes(table[0][4]) && csvRows[1].includes(String(Math.round(Number(table[0][5])))) &&
      csvRows[3].includes(table[2][6]) && table[2][6] !== "",
      `${csvRows[1]} || miss flag: ${table[2][6]}`);
    check("CSV quotes a field containing a comma",
      /,"[^"]*,[^"]*"/.test(csvRows[1]) || !table[0][1].includes(","), "comma handling");

    // A flagged row is the one somebody has to look at, so it has to lead back
    // to the map.
    await page.click("#batch-results tbody tr");
    const selected = await page.evaluate((n) => {
      const p = window[n].state.selectedPoint;
      return { hidden: document.getElementById("batch-modal").hidden, lat: p && p.lat };
    }, EXPORTS_NAME);
    check("clicking a result row selects that point on the map",
      selected.hidden === true && Math.abs(selected.lat - LAT) < 1e-6,
      `modal closed=${selected.hidden} lat=${selected.lat}`);

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
