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
import { stubBasemap, realBasemapContext } from "./basemap_stub.mjs";

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
const EXPECT_DISTRICT = { "school-board": "District 6b", "il-supreme-court": "1", "ccbr": "3" };
const NEGATIVE_POINT = "41.70000,-87.10000"; // Lake Michigan, Indiana waters — outside all three anchor layers. IT CANNOT BE MOVED OUT OF A SIBLING'S STATE AND THAT IS MEASURED: one of the three anchors is il-supreme-court, which answers over the whole state, so the point must be outside Illinois — and sampling permalink_gate every 0.25 degrees and naming each of the 480 points' state off TIGERweb, the ground outside Illinois's own ring is Missouri, Indiana, Iowa, Kentucky, Wisconsin and Michigan and nothing else, with no point anywhere in the gate that no state claims. Five of those are live instances (Indiana went live on 2026-10-07, and its outline contains this point) and Missouri is on the fleet's new-state list. Widening the gate to reach a seventh state would move a reader-facing "where we serve" bound to suit a test. So the point stays. Two checks put it at the map's centre, and until 2026-10-13 both had to refuse ../fleet-outlines.json, because the map then switched apps whenever its centre crossed into a sibling's state; panning no longer does that, so neither refuses anything, and a selection the app makes itself never leaves. Check 1i is where Illinois asserts fleet routing, on its own points, and that panning across a state line stays here.
const APP_NAME = "districtry Illinois";
const EXPECT_LAYERS = 41; // 17 base + police-beat (#43) + school-site (#45) + ccpsa-district-council + ward-precinct + 6 statewide local-gov layers (county, township, municipality, school districts x3 — TIGERweb) + 6 consolidated county-dispatched layers (county-board, judicial-subcircuit, fire-district, park-district, library-district, county-precinct — Cook/Will/DuPage/Lake/Kane/McHenry/Kendall entries; docs/COUNTY_LAYER_CONSOLIDATION.md) + 1 DuPage-only layer (dupage-county-special-police) + 2 Cook-only tax-agency layers (tif-district, mwrd — dedicated until a second county ships the concept) + 1 Chicago-only special-service layer (ssa — dedicated until a second municipality ships the concept) + 3 amenity nearest-point layers (post-office, library, early-voting) = 40 — THE SUM IS THE CLAIM, so a new layer needs its own term here and not just a bigger total: this read 39 for the day the `ssa` layer shipped because the total was the only part anyone would have changed. NOTHING GATES THIS NOTE — validate_doc_counts.py compares prose against layers[] and deliberately does not scan the worksheet it takes as canonical, so this is hand-kept. Addition re-checked against layers[] 2026-09-12; the underlying live verification of the layer list was 2026-07
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
// Coverage-band probe (check 1a): a point inside the REGION whose statewide
// layers answer but outside the 93-county area the county-level layers reach —
// the wash's middle band. `region` is the name COVERAGE_KEY.region.edge gives
// it, which is the word the panel is required to use, because the map key a few
// hundred pixels away already uses it. An instance that paints no middle band
// sets this to null and the span below asserts only that it claims none.
const BAND_PROBE = { region: "Illinois", label: "Princeton, Bureau County",
                     // COVERAGE_KEY.region.label for this instance — the words the map
                     // key prints for the band, which the lede must print too.
                     label_says: "Statewide layers only",
                     lat: 41.3681, lng: -89.4648 };
// Point-move probe (check 2): a second point in a DIFFERENT district of the
// first anchor layer than the ground-truth POINT, exercising the
// incremental-restyle fast path. district is the expected identifier there.
const MOVE_POINT = { lat: 41.99, lng: -87.66, district: "2b" }; // school-board district 2b (vs 6b at the Loop POINT)
// Straggler fixture (check 2d): one same-origin county-board county's
// geometry to delay, plus a point inside one of that county's districts.
// App-RELATIVE on purpose: this doubles as a page.route glob ("**/" + it), and
// an un-prefixed form matches whatever path the instance is served from. Disk
// reads go through INSTANCE_DIR (below), which anchors APP_DIR to this script
// rather than to the process CWD.
const STRAGGLER_FILE = "data/app/stephenson-county-board-districts.json";
const APP_DIR = "il/";
const STRAGGLER_POINT = "42.29660,-89.62120"; // Freeport, Stephenson County — inside board District B of the delayed file
// Layers that declare a location-relevance test (mod.coverage) HIDE at an
// out-of-coverage point instead of reporting an empty card — this list mirrors
// the fork's coverage declarations in index.html (school-board is
// Chicago-scoped via chicagoCoverage; ccbr is Cook-scoped via
// cookCountyCoverage). il-supreme-court declares none and keeps the honest
// "no district here" empty state at the negative point.
//
// ZIP CODE IS THE ONE THAT IS NOT AN ANCHOR, and it is checked here rather
// than left to validate_sources.py BECAUSE THE TEST IS OFFLINE. A ZCTA has no
// state field, so the layer's query carries no STATE='17' filter and outside
// Illinois the live fallback answers a neighbouring state's ZIP code — on
// ground every other statewide card here correctly declines. What keeps that
// from reaching a reader is the layer's coverage() test, which reads the
// shipped state outline (same-origin, cache-first) and needs no third party at
// all, so the browser can prove it in both directions: hidden at the negative
// point (2b) and NOT hidden at the anchor (1i2). Both halves are needed — a
// hide test alone passes for a layer that is hidden everywhere.
const NEGATIVE_HIDDEN = ["school-board", "ccbr", "zip-code"];
// The ids checked at the negative point: the offline anchors plus every
// coverage-declaring layer above, deduped because most of them are anchors.
const NEGATIVE_IDS = OFFLINE.concat(NEGATIVE_HIDDEN.filter((id) => !OFFLINE.includes(id)));
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
async function booted(context, url, routeFn, leaves) {
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
  if (leaves) {
    // A page that may hand itself to a sibling app while it boots (a link in
    // #q= to a place in another state is followed at once, check 1d5) is
    // ready when the app is up OR the page has left this app, whichever
    // comes first: once it has left, the namespace never appears.
    await page.goto(url, { waitUntil: "commit" });
    const gone = page.waitForURL((u) => !u.href.startsWith(BASE), { timeout: BOOT_TIMEOUT });
    const up = page.waitForFunction((n) => !!window[n], EXPORTS_NAME, { timeout: BOOT_TIMEOUT })
      .then(() => true, () => gone);
    await Promise.race([up, gone]);
    return page;
  }
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

// A service worker's own requests reach Playwright only behind this flag, and
// check 2k counts them. Read at launch, so it is set here rather than in the job.
process.env.PW_EXPERIMENTAL_SERVICE_WORKER_NETWORK_EVENTS = "1";
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
    // The coverage-band half selects NEGATIVE_POINT, which is in Indiana, and
    // setSelectedPoint PANS there. Until 2026-10-13 that put the map's centre
    // in a sibling's state and the pan hand-off navigated away mid-assertion,
    // so this check refused ../fleet-outlines.json; panning no longer switches
    // apps, so it refuses nothing. Check 1i asserts the pan half directly.
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

    // ==== TEMPLATE:BEGIN smoke-coverage-band ====
    // THE THREE BANDS OF THE WASH, IN THE PANEL'S OWN WORDS. The lede used to
    // answer two ways — inside the covered area or outside it — and outside it
    // said "nothing there can be answered yet", which is true beyond the state
    // line and FALSE in the Illinois counties the county-level layers do not
    // reach yet, where county, township, municipality, school district and ZIP
    // all answer. Asserted in a browser because nothing static can see it:
    // the sentence is assembled at runtime from a point test against geometry
    // the wash fetched, so it appears in no generated diff and no --check.
    //
    // Two halves, and the second is the one that keeps the first honest: the
    // middle-band sentence must appear where the band is and must NOT appear
    // outside the region, or the app would be telling a reader in Indiana that
    // Illinois's statewide layers answer where they clicked.
    //
    // AND BOTH HALVES WAIT FOR THE WASH TO PAINT, WHICH THE FIRST DRAFT DID NOT
    // AND CI CAUGHT. The panel's point tests read the rings the wash retained,
    // and a null from either one correctly falls through to wording that claims
    // neither — so a test that selects a point before the wash has loaded is
    // asserting against the app's "we cannot tell yet" state. In this sandbox
    // the wash was always up first and both checks passed; on a CI runner
    // Illinois draws it at whenIdle behind two CDN fetches and the lede read
    // "Here is everything that is missing and why", the mask-not-loaded branch.
    // The signals are exact: any path in the scope-mask pane means the coverage
    // rings were retained, and in an app that declares a region, as this one
    // does, the `dst-glow` line is created ONLY in the branch that also retains
    // the region polygons. (An app that declares none draws it along its
    // coverage instead, since 2026-10-13; a region whose file fails still
    // draws no line, so the signal here is unchanged.)
    async function washPainted(needRegion) {
      return page.waitForFunction((wantGlow) => {
        const pane = document.querySelector(".leaflet-pane.leaflet-scope-mask-pane");
        if (!pane || !pane.querySelector("path")) return false;
        return wantGlow ? !!pane.querySelector("path.dst-glow") : true;
      }, needRegion, { timeout: QUERY_TIMEOUT }).then(() => true, () => false);
    }
    if (BAND_PROBE) {
      const ready = await washPainted(true);
      check(`the wash painted its region band, so the band wording can be read (${BAND_PROBE.region})`,
        ready, ready ? "scope-mask pane carries dst-glow" :
        "no dst-glow in the scope-mask pane — the region band never painted, so the " +
        "two checks below would assert against the app's unknown-coverage wording");
      await page.evaluate(({ n, lat, lng }) => window[n].setSelectedPoint(lat, lng),
        { n: EXPORTS_NAME, lat: BAND_PROBE.lat, lng: BAND_PROBE.lng });
      const band = await openGaps();
      // The band sentence LEADS the "where you clicked" sentence rather than
      // replacing it: every one of those counties has a gap record of its own,
      // so replacing it would trade a specific true answer for a general one.
      // Both must be in the lede, which is why this probe point is a county
      // that HAS such a record rather than an arbitrary spot in the band.
      //
      // WHAT THE BAND MEANS IS READ FROM THIS INSTANCE'S OWN COVERAGE_KEY rather
      // than asserted here, because it differs per instance: Illinois's band is
      // "Statewide layers only" and Wisconsin's is "District shown, supervisor
      // not named". A literal here would have passed while the engine told a
      // Wisconsin reader something false.
      check(`gaps lede names the coverage band (${BAND_PROBE.label})`,
        band.lede.indexOf("inside " + BAND_PROBE.region + ", outside the area this app covers in full") !== -1 &&
        band.lede.indexOf(BAND_PROBE.label_says) !== -1 &&
        !/nothing there can be answered yet/.test(band.lede),
        JSON.stringify(band.lede));
    }
    if (await washPainted(false)) {
      await page.evaluate(({ n, p }) => window[n].setSelectedPoint(p[0], p[1]),
        { n: EXPORTS_NAME, p: NEGATIVE_POINT.split(",").map(Number) });
      const beyond = await openGaps();
      check("gaps lede claims no coverage band outside the region",
        /nothing there can be answered yet/.test(beyond.lede) &&
        !/covers in full/.test(beyond.lede), JSON.stringify(beyond.lede));
    } else {
      check("gaps lede claims no coverage band outside the region", false,
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

  // 1c. #q=<address> — the other end of the question pages' address box.
  //     Those pages do not geocode: they hand the typed text to this app in
  //     the HASH (never the query string, which count.js sends to the
  //     analytics host) and the app runs the same bounded search. The app
  //     SELECTS a result only when the geocoder returns exactly one; several
  //     matches is where taking the first would name the wrong officeholder,
  //     so the list stays up and the reader picks.
  //
  //     ONE INSTANCE PROVES IT. prefillGeocodeSearch is a single ENGINE block
  //     spliced into all six apps and compose_app.py --check holds them
  //     byte-identical, so the other five copies of this assertion would test
  //     the same bytes. The GENERATING side — that eleven question pages carry
  //     a form pointing at their own layers — is checked per page by
  //     page_consistency_test.mjs and build_question_forms.py --check.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(
      context,
      `${BASE}#q=${encodeURIComponent(GEOCODER_QUERY_CLEANED)}&layers=${OFFLINE[0]}`,
      async (p) => {
        await p.route("**/photon.komoot.io/**", (route) =>
          route.fulfill({
            status: 200, contentType: "application/json",
            body: JSON.stringify({
              type: "FeatureCollection",
              features: new URL(route.request().url()).searchParams.get("q") === GEOCODER_QUERY_CLEANED
                ? [GEOCODER_STUB_FEATURE] : [],
            }),
          }));
      });
    await page
      .waitForFunction(() => /^Selected:/.test(
        (document.getElementById("geo-status") || {}).textContent || ""),
        null, { timeout: QUERY_TIMEOUT })
      .catch(() => {});
    const handed = await page.evaluate((ns) => ({
      typed: document.getElementById("geocode-input").value,
      status: (document.getElementById("geo-status").textContent || "").trim(),
      point: window[ns].state.selectedPoint,
    }), EXPORTS_NAME);
    check("#q= runs the app's own search on an address handed over in the hash",
      handed.typed === GEOCODER_QUERY_CLEANED && !!handed.point,
      `typed=${handed.typed} status=${handed.status} point=${JSON.stringify(handed.point)}`);
    check("#q= selects the one result rather than leaving the reader to click",
      /^Selected:/.test(handed.status), handed.status.slice(0, 70));
    await context.close();
  }

  // 1d. A district by NAME ("33rd ward", "State Senate District 7"), answered
  //     from the same-origin index scripts/build_district_search.py writes —
  //     never by the geocoder. Driven through #q= so the question pages' hand-
  //     off is covered too, and on a layer whose boundary ships in data/app so
  //     the check needs no live service. Three claims: the one district result
  //     is selected, its layer comes on and its card names the district, and
  //     the geocoder is not asked at all (the text a reader types for a
  //     district name stays in the browser).
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    let geocoderCalls = 0;
    const page = await booted(context, `${BASE}#q=${encodeURIComponent("State Senate District 7")}`, async (p) => {
      // Photon only: the search box's geocoder. Nominatim is the OFFICE-PIN
      // lookup, which the senate card legitimately runs on its members'
      // published office addresses once the district is selected.
      await p.route("**/photon.komoot.io/**", (route) => {
        geocoderCalls += 1;
        route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ type: "FeatureCollection", features: [] }) });
      });
      // GoatCounter is how the feature's use is measured, so the event is part
      // of what ships. Its script is replaced by a recorder (the real one also
      // declines to count on localhost), and every count() call is kept.
      await p.route("**/gc.zgo.at/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
      await p.addInitScript(() => {
        window.__gcEvents = [];
        window.goatcounter = { count: (vars) => window.__gcEvents.push(vars) };
      });
    });
    await page
      .waitForFunction(() => [...document.querySelectorAll(".card-id-pill")].some((e) => /District 7\b/.test(e.textContent)),
        null, { timeout: QUERY_TIMEOUT })
      .catch(() => {});
    const found = await page.evaluate((ns) => ({
      status: (document.getElementById("geo-status").textContent || "").trim(),
      on: !!(document.getElementById("toggle-il-senate") || {}).checked,
      pills: [...document.querySelectorAll(".card-id-pill")].map((e) => e.textContent).filter(Boolean),
      point: window[ns].state.selectedPoint,
      events: (window.__gcEvents || []).filter((v) => v && v.event).map((v) => v.path),
    }), EXPORTS_NAME);
    check("a district searched by name is selected and its layer turned on",
      /^Selected: State Senate District 7/.test(found.status) && found.on && !!found.point,
      `status=${found.status.slice(0, 60)} on=${found.on}`);
    check("the searched district's card names that district",
      found.pills.some((t) => /District 7\b/.test(t)), JSON.stringify(found.pills));
    check("a district name is never sent to the search geocoder", geocoderCalls === 0, `${geocoderCalls} Photon request(s)`);
    check("picking a district by name is counted in GoatCounter by layer, once",
      found.events.filter((e) => /^district-search\//.test(e)).join() === "district-search/il-senate",
      JSON.stringify(found.events));
    // A COUNTY-dispatched layer needs the county in the query: every county
    // has a District 3. De Witt's lettered districts ship in data/app, so this
    // needs no county server; the bare phrase must match NO district row.
    const byCounty = async (q) => {
      await page.fill("#geocode-input", q);
      await page.press("#geocode-input", "Enter");
      await page.waitForTimeout(600);
      return page.evaluate(() => [...document.querySelectorAll("#geocode-results li.district-result")]
        .map((li) => li.querySelector("button").firstChild.textContent.trim()));
    };
    const dewitt = await byCounty("DeWitt County Board District A");
    const bare = await byCounty("county board district 3");
    check("a county board district is found by county and letter",
      dewitt.join() === "De Witt County Board District A", JSON.stringify(dewitt));
    check("a county board district without its county matches nothing", bare.length === 0, JSON.stringify(bare));
    // A NAMED district (the statewide school districts, CPS's zones) is found
    // by its name, abbreviations spelled out; a number alone finds only a
    // district whose name has no place in it, and a place alone stays an
    // address search. All four read the index only, so no Census call.
    const galesburg = await byCounty("Galesburg CUSD 205");
    const d214 = await byCounty("district 214");
    const d1 = await byCounty("school district 1");
    const town = await byCounty("Evanston");
    check("a school district is found by its name and abbreviation",
      galesburg.join() === "Galesburg Community Unit School District 205", JSON.stringify(galesburg));
    check("a school district whose only name is its number is found by the number",
      d214.join() === "Township High School District 214", JSON.stringify(d214));
    check("a school district number shared across the state, or a town alone, matches no district",
      d1.length === 0 && town.length === 0, JSON.stringify({ d1, town }));
    // A CHICAGO SCHOOL BOARD SEAT (1a..10b, the Board's own name for each)
    // is found by that name, written "2b" or "2 b", and is the only name
    // shown: the boundary's own 1..20 is an internal row number, so
    // "school board district 4" is the Board's District 4 — 4a and 4b — and
    // never the row numbered 4 (which is 2b).
    const seat = await byCounty("school board district 2b");
    const seatSpaced = await byCounty("School Board 2 B");
    const seatSub = await byCounty("sub-district 2b");
    const bareSeat = await byCounty("district 2b");
    const pair = await byCounty("school board district 4");
    const row = await byCounty("school board district 20");
    check("a school board district is found and named by its number and letter",
      seat.join() === "School Board District 2b" && seatSpaced.join() === seat.join() && seatSub.join() === seat.join(),
      JSON.stringify({ seat, seatSpaced, seatSub }));
    check("a school board district number finds its two lettered districts, never the internal row number",
      bareSeat.length === 0 && row.length === 0 &&
      pair.join() === "School Board District 4a,School Board District 4b",
      JSON.stringify({ bareSeat, row, pair }));
    // TYPE-AHEAD before the number: the words name a kind of district, so the
    // list says what to type next. A hint is text, never a button, so it
    // cannot be picked and #q= can never auto-select it.
    await page.fill("#geocode-input", "Lake County Board Dis");
    await page.waitForFunction(() => document.querySelector("#geocode-results li.district-hint"), null, { timeout: 5000 }).catch(() => {});
    const hint = await page.evaluate(() => [...document.querySelectorAll("#geocode-results li.district-hint")]
      .map((li) => ({ text: li.textContent.replace(/\s+/g, " ").trim(), button: !!li.querySelector("button") })));
    check("typing a district name before its number shows what to type next",
      hint.length === 1 && /Lake County Board District/.test(hint[0].text) && /1\u201319/.test(hint[0].text) && !hint[0].button,
      JSON.stringify(hint));
    await page.fill("#geocode-input", "chicago school board district");
    await page.waitForFunction(() => document.querySelector("#geocode-results li.district-hint"), null, { timeout: 5000 }).catch(() => {});
    const subHint = await page.evaluate(() => [...document.querySelectorAll("#geocode-results li.district-hint")]
      .map((li) => li.textContent.replace(/\s+/g, " ").trim()));
    check("typing the school board's district before its number shows the range to type",
      subHint.length === 1 && /School Board District/.test(subHint[0]) && /1a\u201310b/.test(subHint[0]),
      JSON.stringify(subHint));
    await context.close();
  }

  // 1d2. A PASTED GOOGLE MAPS LINK is read in the browser by the shared
  //      engine/shared/map-link.txt parser: the place it names becomes one
  //      row, #q= selects it as it would a single address match, it is
  //      counted by kind (never by position), and the geocoder is not asked.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    let geocoderCalls = 0;
    const link = "https://www.google.com/maps/place/Daley+Plaza/@41.8836,-87.6314,17z/data=!3m1!4b1!8m2!3d41.88395!4d-87.63022";
    const page = await booted(context, `${BASE}#q=${encodeURIComponent(link)}`, async (p) => {
      await p.route("**/photon.komoot.io/**", (route) => {
        geocoderCalls += 1;
        route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ type: "FeatureCollection", features: [] }) });
      });
      await p.route("**/gc.zgo.at/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
      await p.addInitScript(() => {
        window.__gcEvents = [];
        window.goatcounter = { count: (vars) => window.__gcEvents.push(vars) };
      });
    });
    await page.waitForFunction((ns) => !!window[ns].state.selectedPoint, EXPORTS_NAME, { timeout: QUERY_TIMEOUT }).catch(() => {});
    const got = await page.evaluate((ns) => ({
      point: window[ns].state.selectedPoint,
      events: (window.__gcEvents || []).filter((v) => v && v.event).map((v) => v.path),
    }), EXPORTS_NAME);
    check("a pasted Google Maps link selects the place it names",
      !!got.point && Math.abs(got.point.lat - 41.88395) < 1e-6 && Math.abs(got.point.lng + 87.63022) < 1e-6,
      JSON.stringify(got.point));
    check("a pasted map link is never sent to the search geocoder", geocoderCalls === 0, `${geocoderCalls} Photon request(s)`);
    check("selecting a pasted map link is counted by kind, once",
      got.events.filter((e) => /^map-link\//.test(e)).join() === "map-link/google", JSON.stringify(got.events));
    // the read itself is counted once, with what it showed and nothing of the place
    check("reading a map link handed over in the address is counted once, by kind and result",
      got.events.filter((e) => /^map-link-read\//.test(e)).join() === "map-link-read/il/google/full/opened/point",
      JSON.stringify(got.events));
    await context.close();
  }

  // 1d3. A SHORT MAP LINK holds no position, so it goes to districtry's own
  //      lookup (MAP_LINK_LOOKUP), stubbed here, and the full link it answers
  //      is read like a pasted one. Asserts what is SENT: the short link alone,
  //      to the lookup, and nothing to the geocoder.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    let geocoderCalls = 0;
    const lookupAsked = [];
    const shortLink = "https://maps.app.goo.gl/AbCdEf123";
    const page = await booted(context, `${BASE}#q=${encodeURIComponent(shortLink)}`, async (p) => {
      await p.route("**/photon.komoot.io/**", (route) => {
        geocoderCalls += 1;
        route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ type: "FeatureCollection", features: [] }) });
      });
      await p.route("**/link-lookup.districtry.deno.net/**", (route) => {
        lookupAsked.push(new URL(route.request().url()).searchParams.get("u"));
        route.fulfill({ status: 200, contentType: "application/json",
          body: JSON.stringify({ url: "https://www.google.com/maps/place/Daley+Plaza/@41.8836,-87.6314,17z/data=!3m1!4b1!8m2!3d41.88395!4d-87.63022" }) });
      });
    });
    await page.waitForFunction((ns) => !!window[ns].state.selectedPoint, EXPORTS_NAME, { timeout: QUERY_TIMEOUT }).catch(() => {});
    const point = await page.evaluate((ns) => window[ns].state.selectedPoint, EXPORTS_NAME);
    check("a short map link is sent to the lookup, and only the link",
      lookupAsked.length === 1 && lookupAsked[0] === shortLink, JSON.stringify(lookupAsked));
    check("a short map link selects the place its full link names",
      !!point && Math.abs(point.lat - 41.88395) < 1e-6 && Math.abs(point.lng + 87.63022) < 1e-6,
      JSON.stringify(point));
    check("a short map link is never sent to the search geocoder", geocoderCalls === 0, `${geocoderCalls} Photon request(s)`);
    await context.close();
  }

  // 1d3b. A LOOKUP THAT FAILS IS ASKED AGAIN (ENGINE map-link
  //      resolveShortMapLink): a shared short link once came back "couldn't
  //      be read" on a phone and read at once minutes later. Here the first
  //      try gets no answer at all and the second a 502, and the third
  //      answers, so the place is selected after two tries again. Then a link
  //      whose every try gets no answer says which side failed and never
  //      sends a reader to an address bar.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const tries = {};
    const shortLink = "https://maps.app.goo.gl/AbCdEf123";
    const deadLink = "https://maps.app.goo.gl/ZzYyXx987";
    const page = await booted(context, `${BASE}#q=${encodeURIComponent(shortLink)}`, async (p) => {
      await p.route("**/photon.komoot.io/**", (route) => route.fulfill({ status: 200, contentType: "application/json",
        body: JSON.stringify({ type: "FeatureCollection", features: [] }) }));
      await p.route("**/link-lookup.districtry.deno.net/**", (route) => {
        const u = new URL(route.request().url()).searchParams.get("u");
        const n = tries[u] = (tries[u] || 0) + 1;
        if (u === deadLink || n === 1) return route.abort("failed");
        if (n === 2) return route.fulfill({ status: 502, contentType: "application/json", body: JSON.stringify({ error: "the link could not be followed" }) });
        return route.fulfill({ status: 200, contentType: "application/json",
          body: JSON.stringify({ url: "https://www.google.com/maps/place/Daley+Plaza/@41.8836,-87.6314,17z/data=!3m1!4b1!8m2!3d41.88395!4d-87.63022" }) });
      });
      await p.route("**/gc.zgo.at/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
      await p.addInitScript(() => {
        window.__gcEvents = [];
        window.goatcounter = { count: (vars) => window.__gcEvents.push(vars) };
      });
    });
    await page.waitForFunction((ns) => !!window[ns].state.selectedPoint, EXPORTS_NAME, { timeout: QUERY_TIMEOUT }).catch(() => {});
    const point = await page.evaluate((ns) => window[ns].state.selectedPoint, EXPORTS_NAME);
    check("a short link the lookup fails to read twice is asked a third time, and its place is selected",
      tries[shortLink] === 3 && !!point && Math.abs(point.lat - 41.88395) < 1e-6 && Math.abs(point.lng + 87.63022) < 1e-6,
      `${tries[shortLink]} lookup(s), point ${JSON.stringify(point)}`);
    await page.fill("#geocode-input", deadLink);
    await page.waitForFunction(() => document.querySelector("#geo-status.err"), null, { timeout: QUERY_TIMEOUT }).catch(() => {});
    const msg = await page.evaluate(() => document.getElementById("geo-status").textContent);
    check("a short link the lookup never reaches is asked three times, then says districtry couldn't reach the lookup",
      tries[deadLink] === 3 && /couldn't be read just now \(districtry couldn't reach the service that reads short links\)/.test(msg) &&
      !/address bar/.test(msg), `${tries[deadLink]} lookup(s): ${JSON.stringify(msg)}`);
    const reads = await page.evaluate(() => (window.__gcEvents || [])
      .filter((v) => v && v.event && /^map-link-read\//.test(v.path)).map((v) => v.path));
    check("a short link read on a retry, and one never read after its retries, are each counted once with why",
      reads.join() === "map-link-read/il/google/short-retried/opened/point,map-link-read/il/google/short-retried/pasted/failed-unreached",
      JSON.stringify(reads));
    await context.close();
  }

  // 1d4. A LINK FROM THE GOOGLE MAPS APP names a place with no position: it
  //      resolves to ?q=<the place's name, its address>&ftid=…, which is what
  //      a place shared into the installed app arrives as (SHARED is the
  //      share as the launcher hands it on, its lines joined by spaces). The
  //      whole string goes to the geocoder first; when it matches nothing,
  //      the address alone does, and a single match CARRYING ITS HOUSE
  //      NUMBER is selected. A street that only partly matches is not (the
  //      3rd Street answer is what Photon really gave for this address).
  //      Then the place's name alone, whose answer is listed and never
  //      selected. When nothing matches at all, the reader is told the link
  //      gave no position, in the app's own place name (Illinois's
  //      METRO_NAME is still "Chicago"). Typed text gets no retries.
  //      THE STREET WITHOUT THE NUMBER: when the address alone finds its
  //      street in its town and no answer carries the number, the map frames
  //      that street, selects nothing, lists a name answer only near it, and
  //      a tap on the map then selects the tapped point (showStreetOnly).
  //      AN ADDRESS TYPED WITH NO NAME IN FRONT is held to its house number
  //      too (runAddressSearch, listHeldAnswers): an answer without it is
  //      marked and never selected for the reader, a sent search frames the
  //      street with the Census pin, whose point it selects, when the answers
  //      put it in one town, and while the reader types nothing goes to the
  //      Census lookup until the street's row is picked. A town typed after a
  //      comma that the answers name only by its ZIP code is the town they
  //      are put in (addressInTownOf), with a ZIP code typed after it. An
  //      answer is the house only if it is the number on the address's
  //      street (labelAtHouse), so the number on another street is marked
  //      other-street and never selected. WHEN THE SEARCH KNOWS NEITHER THE
  //      HOUSE NOR ITS STREET in its town, a sent address is asked about as
  //      the lookup asks about every other, in the app's state
  //      (addressForLookup), and a Census answer that is the house is a pin
  //      with its point selected, however far it is from any stretch of the
  //      street the search knows. Every answer here is OpenStreetMap's, so the
  //      street's message links OpenStreetMap's note form at the street or
  //      the pin (osmNoteLink), and following it counts osm-note. A shared
  //      link that ends on its street is counted once the Census answer is
  //      known, as pin or as street (countLinkRead).
  {
    const SHARED = "Starved Rock Lodge 2668 E 875th Rd, Oglesby, IL 61348 https://maps.app.goo.gl/XyZ987";
    const FULL = "https://maps.google.com/?q=Starved+Rock+Lodge,+2668+E+875th+Rd,+Oglesby,+IL+61348&ftid=0x880bd2e1b3a8f5d1:0x9b1c2d3e4f5a6b7c&entry=gps";
    const NAMED = "Starved Rock Lodge, 2668 E 875th Rd, Oglesby, IL 61348";
    const BARE = "2668 E 875th Rd, Oglesby, IL 61348";
    const NAME = "Starved Rock Lodge";
    const feature = (lng, lat, props) => ({ type: "Feature", geometry: { type: "Point", coordinates: [lng, lat] }, properties: props });
    const HOUSE = feature(-88.9893, 41.3196, { housenumber: "2668", street: "East 875th Road", city: "Oglesby", state: "Illinois" });
    const THIRD = feature(-89.0619, 41.2918, { name: "West 3rd Street", city: "Oglesby", state: "Illinois" });
    const LODGE = feature(-88.9945, 41.3190, { name: "Starved Rock Lodge", street: "Fox Canyon Bridge", state: "Illinois" });
    const PHONE = { viewport: { width: 412, height: 915 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true };
    // ranges answers the lookup's ?a= route, the Census Bureau's estimate of
    // where a house number falls (lookupAddressRanges); unset, it finds none
    const run = async (hash, answer, settled, full = FULL, act = null, phone = false, ranges = null) => {
      const context = await browser.newContext(phone ? { serviceWorkers: "block", ...PHONE } : { serviceWorkers: "block" });
      const asked = [], lookedUp = [];
      const page = await booted(context, `${BASE}#q=${encodeURIComponent(hash)}`, async (p) => {
        await p.route("**/gc.zgo.at/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
        await p.addInitScript(() => {
          window.__gcEvents = [];
          window.goatcounter = { count: (vars) => window.__gcEvents.push(vars) };
        });
        await p.route("**/photon.komoot.io/**", (route) => {
          const u = new URL(route.request().url());
          const bounded = !!u.searchParams.get("bbox");
          const q = u.searchParams.get("q");
          asked.push((bounded ? "bounded:" : "unbounded:") + q);
          route.fulfill({ status: 200, contentType: "application/json",
            body: JSON.stringify({ type: "FeatureCollection", features: answer(q, bounded) }) });
        });
        await p.route("**/link-lookup.districtry.deno.net/**", (route) => {
          const u = new URL(route.request().url());
          if (u.searchParams.has("a")) {
            lookedUp.push(u.searchParams.get("a"));
            const r = ranges ? ranges(u.searchParams.get("a")) : { status: 200, matches: [] };
            route.fulfill({ status: r.status, contentType: "application/json",
              body: JSON.stringify(r.status === 200 ? { matches: r.matches } : { error: "stubbed failure" }) });
            return;
          }
          route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ url: full }) });
        });
      });
      await page.waitForFunction(settled, EXPORTS_NAME, { timeout: QUERY_TIMEOUT }).catch(() => {});
      await page.waitForTimeout(300); // a selection, if one were coming, follows the list
      const read = () => page.evaluate((ns) => {
        const m = window[ns].map.getContainer().getBoundingClientRect();
        const el = document.querySelector('.leaflet-marker-icon[aria-label^="Where the Census Bureau puts"]');
        const r = el && el.getBoundingClientRect();
        const note = document.querySelector("#geo-status a");
        return {
          point: window[ns].state.selectedPoint,
          status: document.getElementById("geo-status").textContent,
          note: note ? { href: note.href, text: note.textContent, target: note.target, rel: note.rel } : null,
          events: (window.__gcEvents || []).filter((v) => v && v.event).map((v) => v.path),
          rows: [...document.querySelectorAll("#geocode-results li")].map((li) => ({ cls: li.className, text: li.textContent })),
          centre: window[ns].map.getCenter(),
          zoom: window[ns].map.getZoom(),
          height: m.height,
          panelBelow: document.getElementById("search-extra").getBoundingClientRect().bottom - m.top,
          pin: el ? { label: el.getAttribute("aria-label"), role: el.getAttribute("role"), tabindex: el.getAttribute("tabindex"),
            top: r.top - m.top, bottom: r.bottom - m.top, left: r.left - m.left, right: r.right - m.left } : null,
        };
      }, EXPORTS_NAME);
      const got = await read();
      const after = act ? await act(page, read) : null;
      await context.close();
      return { asked, lookedUp, got, after };
    };
    const selected = (ns) => !!window[ns].state.selectedPoint;
    const found = await run(SHARED, (q, bounded) => (bounded && q === BARE ? [HOUSE] : []), selected);
    check("a Google Maps app link's address is searched alone when its name and address match nothing",
      found.asked[0] === "bounded:" + NAMED && found.asked.indexOf("bounded:" + BARE) > 0,
      JSON.stringify(found.asked));
    check("the one answer carrying the address's house number is selected",
      !!found.got.point && Math.abs(found.got.point.lat - 41.3196) < 1e-6 && Math.abs(found.got.point.lng + 88.9893) < 1e-6,
      JSON.stringify(found.got.point));
    const named = await run(SHARED, (q, bounded) => (bounded && q === BARE ? [THIRD] : bounded && q === NAME ? [LODGE] : []),
      () => /A search for its name/.test(document.getElementById("geo-status").textContent));
    check("a street without the address's house number is never taken for the shared place",
      !named.got.point && named.got.rows.every((r) => r.text.indexOf("3rd Street") < 0), JSON.stringify(named.got));
    check("the place found by its name alone is listed, marked, and never selected",
      !named.got.point && named.got.rows.length === 1 && named.got.rows[0].cls === "name-result" &&
        named.got.rows[0].text.indexOf(NAME) >= 0 && named.got.status.indexOf(BARE) >= 0,
      JSON.stringify(named.got));
    check("the name alone is asked only after the address, here and in the sibling apps",
      named.asked.indexOf("bounded:" + NAME) > named.asked.indexOf("unbounded:" + BARE) &&
        named.asked.indexOf("unbounded:" + BARE) > named.asked.indexOf("unbounded:" + NAMED) &&
        named.asked.indexOf("unbounded:" + NAMED) > named.asked.indexOf("bounded:" + BARE),
      JSON.stringify(named.asked));
    const missed = await run(SHARED, () => [],
      () => /doesn't say where it is/.test(document.getElementById("geo-status").textContent));
    check("a link naming a place nothing matches says the link gave no position, in the app's own place name",
      !missed.got.point && missed.got.status.indexOf(NAMED) >= 0 && missed.got.status.indexOf(APP_NAME.replace(/^districtry /, "")) >= 0 &&
        missed.got.status.indexOf("Chicago") < 0,
      JSON.stringify(missed.got.status));
    const typed = await run(NAMED, () => [], () => /No addresses matched inside/.test(document.getElementById("geo-status").textContent));
    check("typed text that misses names the app's own place and is not retried without its name",
      typed.asked.every((a) => a !== "bounded:" + BARE && a !== "unbounded:" + BARE && a !== "bounded:" + NAME) &&
        typed.got.status.indexOf(APP_NAME.replace(/^districtry /, "")) >= 0 && typed.got.status.indexOf("Chicago") < 0,
      JSON.stringify(typed));

    // The place Adam shared on 2026-10-14 is on a short drive in Westmont
    // that Photon holds without its house number: asked for the address
    // alone it answered six streets there (ON is the address's street,
    // BESIDE one of the others, both with the extent Photon gave them), and
    // asked for the name, places with similar names 20 to 50 km away (FAR).
    // The name, the number and the link here are made up; the streets are
    // Photon's.
    const S_FULL = "https://www.google.com/maps/place/Corner+Shop,+9+W+Oakley+Dr+NW,+Westmont,+IL+60559/data=!4m2!3m1!1s0x880e5575a1b2c3d4:0x1a2b3c4d5e6f7a8b!18m1!1e1?utm_source=mstt_1&entry=gps";
    const S_SHARED = "Corner Shop 9 W Oakley Dr NW, Westmont, IL 60559 https://maps.app.goo.gl/AbC123";
    const S_BARE = "9 W Oakley Dr NW, Westmont, IL 60559";
    const S_NAME = "Corner Shop";
    const ON = feature(-87.9794943, 41.8219565, { name: "West Oakley Drive Northwest", city: "Westmont", state: "Illinois",
      postcode: "60559", type: "street", extent: [-87.9794965, 41.8221975, -87.9794932, 41.8217156] });
    const BESIDE = feature(-87.9779586, 41.8216492, { name: "Oakley Drive North", city: "Westmont", state: "Illinois",
      postcode: "60559", type: "street", extent: [-87.9794947, 41.8217156, -87.9764337, 41.8214675] });
    const FAR = feature(-88.3190, 42.2181, { name: "Corner Shop", street: "Berkshire Drive", city: "Crystal Lake", state: "Illinois" });
    const CLOSE = feature(-87.9790, 41.8218, { name: S_NAME, city: "Westmont", state: "Illinois", postcode: "60559" });
    const onStreet = () => /showing that street/.test(document.getElementById("geo-status").textContent);
    // Where the street's two ends are drawn, in the map's own pixels, and
    // where the search panel holding the message ends: the street is framed
    // below the panel, which floats over the top of the map. On a phone the
    // panel covers nearly half the map, and a street at the middle of the map
    // would run up under it, so this is asked at a phone's size. Then a tap
    // on the middle of the street.
    const tap = async (page, read) => {
      const frame = await page.evaluate(([ns, ends]) => {
        const map = window[ns].map, m = map.getContainer().getBoundingClientRect();
        const panel = document.getElementById("search-extra").getBoundingClientRect();
        return { below: panel.bottom - m.top, width: m.width, height: m.height,
          ends: ends.map((e) => map.latLngToContainerPoint(e)) };
      }, [EXPORTS_NAME, [[41.8221975, -87.9794965], [41.8217156, -87.9794932]]]);
      const box = await page.locator("#map").boundingBox();
      await page.touchscreen.tap(box.x + (frame.ends[0].x + frame.ends[1].x) / 2, box.y + (frame.ends[0].y + frame.ends[1].y) / 2);
      // A tap is selected at once only when the coverage wash has already
      // painted; before that the app asks fleet-outlines.json who serves
      // the point and selects when it answers. On a busy runner that took
      // longer than a fixed 300 ms (2026-10-17), so wait for the selection.
      await page.waitForFunction((ns) => !!window[ns].state.selectedPoint, EXPORTS_NAME, { timeout: QUERY_TIMEOUT }).catch(() => {});
      return { frame, ...(await read()) };
    };
    // The Census Bureau's estimates, made up: one on the address's street and
    // near it, one on another street, and one on the address's street about
    // 4 km from the part of it the map found, which is a pin since
    // 2026-10-19 (below).
    const PIN_AT = { lat: 41.82195, lng: -87.97955 };
    const ON_RANGE = { address: "9 W OAKLEY DR NW, WESTMONT, IL, 60559", ...PIN_AT };
    const OTHER_STREET = { address: "9 OAKLEY LN, WESTMONT, IL, 60559", lat: 41.8100, lng: -87.9700 };
    const FAR_ON_STREET = { address: "9 W OAKLEY DR NW, WESTMONT, IL, 60559", lat: 41.8400, lng: -87.9300 };
    const street = await run(S_SHARED, (q, bounded) => (bounded && q === S_BARE ? [BESIDE, ON] : bounded && q === S_NAME ? [FAR] : []),
      onStreet, S_FULL, tap, true, () => ({ status: 200, matches: [OTHER_STREET] }));
    const g = street.got, t = street.after, f = t.frame;
    check("a shared address whose house number the search lacks frames its street clear of the search panel and selects nothing",
      !g.point && g.zoom >= 16 && f.below > 0 &&
        f.ends.every((e) => e.x >= 0 && e.x <= f.width && e.y >= f.below + 12 && e.y <= f.height) &&
        g.status.indexOf("W Oakley Dr NW in Westmont but not number 9") >= 0 && g.status.indexOf("Tap the place you meant") >= 0,
      JSON.stringify({ got: g, frame: f }));
    check("answers to the place's name far from its street are not listed, and no sibling app is asked",
      g.rows.length === 0 && street.asked.indexOf("bounded:" + S_NAME) > street.asked.indexOf("bounded:" + S_BARE) &&
        street.asked.every((a) => a.indexOf("unbounded:") !== 0),
      JSON.stringify({ rows: g.rows, asked: street.asked }));
    // OPENSTREETMAP'S NOTE FORM (osmNoteLink): the message links it, at the
    // street the map framed, in the part of the map below the search panel
    const NOTE = /^https:\/\/www\.openstreetmap\.org\/note\/new#map=(\d+)\/(-?\d+\.\d{5})\/(-?\d+\.\d{5})$/;
    const noteAt = (n) => { const m = n && NOTE.exec(n.href); return m ? { zoom: +m[1], lat: +m[2], lng: +m[3] } : null; };
    const gn = noteAt(g.note);
    check("the street's message links OpenStreetMap's note form, opening at the street the map framed",
      !!gn && gn.zoom >= 17 && gn.zoom <= 19 && Math.abs(gn.lat - 41.8219565) < 0.0005 && Math.abs(gn.lng + 87.9794949) < 0.0005 &&
        g.note.text === "leave OpenStreetMap a public note" && g.note.target === "_blank" && /\bnoreferrer\b/.test(g.note.rel) &&
        g.status.indexOf("Tap the place you meant. The search reads OpenStreetMap's data. If you know where number 9 is yourself, " +
          "not from another map, you can leave OpenStreetMap a public note so its volunteers can add it.") >= 0,
      JSON.stringify({ note: g.note, centre: g.centre, status: g.status }));
    check("a tap on the street then selects the point tapped and the message goes",
      !!t.point && Math.abs(t.point.lat - 41.8219565) < 0.0003 && Math.abs(t.point.lng + 87.9794949) < 0.0003 && t.status === "",
      JSON.stringify(t));
    check("the Census Bureau is asked for the address, and an estimate on another street draws no pin",
      street.lookedUp.length === 1 && street.lookedUp[0] === S_BARE && !g.pin,
      JSON.stringify({ lookedUp: street.lookedUp, pin: g.pin }));
    const linkReads = (r) => r.events.filter((e) => /^map-link-read\//.test(e)).join();
    check("a shared link that ends on its street with no pin is counted once, as street",
      linkReads(t) === "map-link-read/il/google/short/opened/street", JSON.stringify(t.events));
    const near = await run(S_SHARED, (q, bounded) => (bounded && q === S_BARE ? [BESIDE, ON] : bounded && q === S_NAME ? [FAR, CLOSE] : []),
      () => /A search for its name/.test(document.getElementById("geo-status").textContent), S_FULL, null, false,
      () => ({ status: 502 }));
    check("an answer to the place's name near its street is listed, marked, and never selected",
      !near.got.point && near.got.rows.length === 1 && near.got.rows[0].cls === "name-result" &&
        near.got.rows[0].text.indexOf(S_NAME) >= 0 && near.got.status.indexOf("showing that street") >= 0,
      JSON.stringify(near.got));
    check("a Census lookup that fails draws no pin and leaves the street's message as it was",
      near.lookedUp.length === 1 && !near.got.pin, JSON.stringify({ lookedUp: near.lookedUp, pin: near.got.pin }));
    // FAR ALONG THE STREET: until 2026-10-19 an estimate more than half a
    // mile from the stretch of the street the search knew drew no pin, and of
    // 49 Cook County addresses typed into the search box that day it refused
    // 2 whose district the Census Bureau's records had right. Adam chose its
    // answer whenever it is the house ("Use Census").
    const farAlong = await run(S_SHARED, (q, bounded) => (bounded && q === S_BARE ? [BESIDE, ON] : []),
      () => /Census Bureau's street records put that number/.test(document.getElementById("geo-status").textContent),
      S_FULL, null, false, () => ({ status: 200, matches: [OTHER_STREET, FAR_ON_STREET] }));
    check("the one estimate that is the house is a pin with its point selected, however far along the street it is",
      !!farAlong.got.pin && !!farAlong.got.point && Math.abs(farAlong.got.point.lat - FAR_ON_STREET.lat) < 1e-7 &&
        Math.abs(farAlong.got.point.lng - FAR_ON_STREET.lng) < 1e-7 && farAlong.lookedUp.length === 1,
      JSON.stringify({ got: farAlong.got, lookedUp: farAlong.lookedUp }));

    // THE CENSUS BUREAU'S PIN (lookupAddressRanges). The one estimate on the
    // address's street, in its town and near the street the map found, is a
    // pin whose point is selected at once (Adam's choice of 2026-10-18): the
    // map frames it below the search panel, the message says it can be a
    // block or more from the house, the pin is a picture rather than a button, and a tap on
    // the map beside it, a row for the place's name or a point selected any
    // other way selects that instead and takes the pin and the message away.
    // A pin another state's app answers for waits for a tap (below).
    const ranged = () => ({ status: 200, matches: [ON_RANGE] });
    const PIN = '[aria-label^="Where the Census Bureau puts"]';
    const pinShown = () => /Census Bureau's street records put that number/.test(document.getElementById("geo-status").textContent);
    const atPin = (p) => !!p && Math.abs(p.lat - PIN_AT.lat) < 1e-7 && Math.abs(p.lng - PIN_AT.lng) < 1e-7;
    // a tap on the map 80 px to the pin's left, clear of the pin and of the
    // selected point's own marker
    const tapBeside = async (page, read) => {
      const spot = await page.evaluate(([ns, at]) => {
        const map = window[ns].map, tip = map.latLngToContainerPoint(at);
        return { x: tip.x - 80, y: tip.y, at: map.containerPointToLatLng([tip.x - 80, tip.y]), sequence: window[ns].state.sequence };
      }, [EXPORTS_NAME, [PIN_AT.lat, PIN_AT.lng]]);
      const box = await page.locator("#map").boundingBox();
      await page.touchscreen.tap(box.x + spot.x, box.y + spot.y);
      await page.waitForFunction(([ns, n]) => window[ns].state.sequence > n, [EXPORTS_NAME, spot.sequence],
        { timeout: QUERY_TIMEOUT }).catch(() => {});
      return { tapped: spot.at, ...(await read()) };
    };
    const pinned = await run(S_SHARED, (q, bounded) => (bounded && q === S_BARE ? [BESIDE, ON] : bounded && q === S_NAME ? [FAR] : []),
      pinShown, S_FULL, tapBeside, true, ranged);
    const pg = pinned.got, pa = pinned.after;
    check("the Census Bureau's estimate is a pin below the search panel, and its point is selected at once",
      atPin(pg.point) && !!pg.pin && pg.zoom >= 17.5 && pg.pin.top >= pg.panelBelow && pg.pin.bottom <= pg.height &&
        pg.status.indexOf("W Oakley Dr NW in Westmont but not number 9 on it. The map has selected the pin, where the Census " +
          "Bureau's street records put that number. It can be a block or more from the house, and a district line can run " +
          "between the two. If the place is elsewhere, tap it on the map.") >= 0 &&
        pg.pin.label === "Where the Census Bureau puts 9 W Oakley Dr NW" && pg.pin.role === "img" && pg.pin.tabindex === null,
      JSON.stringify(pg));
    check("a shared link whose house the Census Bureau pins is counted once, as pin",
      linkReads(pa) === "map-link-read/il/google/short/opened/pin", JSON.stringify(pa.events));
    const pn = noteAt(pg.note);
    check("with the pin, the note form opens at the pin",
      !!pn && pn.zoom === 19 && Math.abs(pn.lat - PIN_AT.lat) < 1e-9 && Math.abs(pn.lng - PIN_AT.lng) < 1e-9,
      JSON.stringify(pg.note));
    check("a tap on the map beside the pin selects the point tapped instead, and the pin and the message go",
      !!pa.point && !atPin(pa.point) && Math.abs(pa.point.lat - pa.tapped.lat) < 2e-5 && Math.abs(pa.point.lng - pa.tapped.lng) < 2e-5 &&
        Math.abs(pa.point.lng - PIN_AT.lng) > 1e-4 && !pa.pin && pa.status === "",
      JSON.stringify(pa));
    const pickName = async (page, read) => {
      await page.locator("#geocode-results li.name-result button").first().click();
      await page.waitForTimeout(200);
      return read();
    };
    const both = await run(S_SHARED, (q, bounded) => (bounded && q === S_BARE ? [BESIDE, ON] : bounded && q === S_NAME ? [FAR, CLOSE] : []),
      () => /also found the place below/.test(document.getElementById("geo-status").textContent), S_FULL, pickName, false, ranged);
    check("with an answer to the place's name near the street as well, the pin's point is selected and the name is offered",
      atPin(both.got.point) && !!both.got.pin && both.got.rows.length === 1 && both.got.rows[0].cls === "name-result" &&
        both.got.status.indexOf("also found the place below. Pick it if it's the one you meant, or tap the map.") >= 0,
      JSON.stringify(both.got));
    check("picking the name's row selects that place instead, and the pin goes",
      !!both.after.point && Math.abs(both.after.point.lat - 41.8218) < 1e-7 && Math.abs(both.after.point.lng + 87.9790) < 1e-7 &&
        !both.after.pin,
      JSON.stringify(both.after));
    // Following the link opens the form in a new tab (stood in for here, so
    // nothing reaches OpenStreetMap), counts osm-note and leaves the map as it was
    const followNote = async (page, read) => {
      const context = page.context();
      await context.route("https://www.openstreetmap.org/**", (route) =>
        route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>note</title>" }));
      const opened = context.waitForEvent("page", { timeout: QUERY_TIMEOUT });
      await page.locator("#geo-status a").click();
      const tab = await opened.catch(() => null);
      if (tab) await tab.waitForLoadState("domcontentloaded").catch(() => {});
      await page.waitForTimeout(200);
      return { opened: tab ? tab.url() : null, ...(await read()) };
    };
    const noted = await run(S_SHARED, (q, bounded) => (bounded && q === S_BARE ? [BESIDE, ON] : []),
      pinShown, S_FULL, followNote, false, ranged);
    check("following the note link opens OpenStreetMap's form at the pin, counts osm-note once and leaves the pin's point selected",
      noted.after.opened === "https://www.openstreetmap.org/note/new#map=19/41.82195/-87.97955" &&
        noted.after.events.filter((e) => e === "osm-note").length === 1 && !noted.got.events.some((e) => e === "osm-note") &&
        atPin(noted.after.point) && !!noted.after.pin,
      JSON.stringify({ opened: noted.after.opened, events: noted.after.events, point: noted.after.point }));
    const otherwise = async (page, read) => {
      await page.evaluate((ns) => window[ns].setSelectedPoint(41.8240, -87.9760, { skipPan: true }), EXPORTS_NAME);
      await page.waitForTimeout(200);
      return read();
    };
    const moved = await run(S_SHARED, (q, bounded) => (bounded && q === S_BARE ? [BESIDE, ON] : []),
      pinShown, S_FULL, otherwise, false, ranged);
    check("a point selected another way takes the pin away, and the message about it",
      !!moved.got.pin && atPin(moved.got.point) && !!moved.after.point && Math.abs(moved.after.point.lat - 41.8240) < 1e-9 &&
        !moved.after.pin && moved.after.status === "",
      JSON.stringify({ before: moved.got.pin, after: moved.after }));

    // A PIN ANOTHER STATE'S APP ANSWERS FOR. This app's search box reaches
    // into Iowa, so a typed address can find its street in Davenport, and a
    // selection there would open Iowa's app with the point and without the
    // message, so the pin waits for a tap. Enter on the focused pin opens
    // that app with the pin's point. The street, the number and the estimate
    // are made up; the sibling apps are stubbed.
    const IA_ADDRESS = "9 W Sample St, Davenport";
    const IA_PIN = { lat: 41.5300, lng: -90.5795 };
    const IA_STREET = feature(-90.5800, 41.5300, { name: "West Sample Street", city: "Davenport", state: "Iowa",
      postcode: "52803", type: "street", extent: [-90.5830, 41.5302, -90.5770, 41.5298] });
    const IA_RANGE = { address: "9 W SAMPLE ST, DAVENPORT, IA, 52803", ...IA_PIN };
    const pressPinAway = async (page) => {
      await page.route("https://districtry.com/**", (route) =>
        route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>sibling</title>" }));
      const to = page.waitForURL((u) => !u.href.startsWith(BASE), { timeout: QUERY_TIMEOUT }).then(() => page.url(), () => null);
      await page.focus(PIN);
      await page.keyboard.press("Enter");
      return to;
    };
    const iowa = await run(IA_ADDRESS, (q, bounded) => (bounded && q === IA_ADDRESS ? [IA_STREET] : []),
      () => /Tap the pin to use it/.test(document.getElementById("geo-status").textContent), S_FULL, pressPinAway, false,
      () => ({ status: 200, matches: [IA_RANGE] }));
    const iw = iowa.got;
    check("a Census pin another state's app answers for selects nothing here and waits for a tap",
      !iw.point && !!iw.pin && iw.pin.role === "button" && iw.pin.tabindex === "0" &&
        iw.pin.label === "Where the Census Bureau puts 9 W Sample St. Select this point." &&
        iw.status.indexOf("W Sample St in Davenport but not number 9 on it. The pin is where the Census Bureau's street records " +
          "put that number, which can be a block or more from the house. Tap the pin to use it, or tap the place you meant.") >= 0 &&
        iowa.lookedUp.length === 1 && iowa.lookedUp[0] === IA_ADDRESS + ", IA 52803",
      JSON.stringify(iowa));
    const iaPoint = iowa.after && /^https:\/\/districtry\.com\/ia\/#point=([-\d.]+),([-\d.]+)/.exec(iowa.after);
    check("Enter on that pin opens that state's app with the pin's point",
      !!iaPoint && Math.abs(+iaPoint[1] - IA_PIN.lat) < 1e-4 && Math.abs(+iaPoint[2] - IA_PIN.lng) < 1e-4,
      String(iowa.after));

    // TYPED ADDRESSES, sent with #q= as a question page's box or the front
    // door sends them, or typed into the box. The number and the streets'
    // other town are made up; ELSEWHERE is the street's name in another town.
    const T_ADDRESS = "9 W Oakley Dr NW, Westmont";
    const T_NO_TOWN = "9 W Oakley Dr NW";
    const T_AT = "9 W Oakley Dr NW, Westmont, IL";
    // as the Census lookup is asked about it once the search knows its
    // street: with the one ZIP code the street's answers carry
    const T_AT_ZIP = T_AT + " 60559";
    const ELSEWHERE = feature(-88.0110, 41.7960, { name: "West Oakley Drive Northwest", city: "Downers Grove", state: "Illinois",
      postcode: "60515", type: "street", extent: [-88.0120, 41.7965, -88.0100, 41.7955] });
    const NUMBERED = feature(PIN_AT.lng, PIN_AT.lat, { housenumber: "9", street: "West Oakley Drive Northwest", city: "Westmont",
      state: "Illinois", postcode: "60559" });
    const typedSent = await run(T_ADDRESS, (q, bounded) => (bounded && q === T_ADDRESS ? [BESIDE, ON] : []),
      pinShown, S_FULL, null, true, ranged);
    const ts = typedSent.got;
    check("a typed address sent without the house number the search has frames its street with the Census pin and selects the pin's point",
      atPin(ts.point) && !!ts.pin && ts.pin.top >= ts.panelBelow && ts.rows.length === 0 &&
        ts.status.indexOf("W Oakley Dr NW in Westmont but not number 9 on it. The map has selected the pin, where the Census Bureau's") >= 0 &&
        typedSent.lookedUp.length === 1 && typedSent.lookedUp[0] === T_AT_ZIP &&
        typedSent.asked.length === 1 && typedSent.asked[0] === "bounded:" + T_ADDRESS,
      JSON.stringify(typedSent));
    const pickRow = (text, until = pinShown) => async (page, read) => {
      await page.locator("#geocode-results li button", { hasText: text }).click();
      await page.waitForFunction(until, EXPORTS_NAME, { timeout: QUERY_TIMEOUT }).catch(() => {});
      await page.waitForTimeout(200);
      return read();
    };
    const twoTowns = await run(T_NO_TOWN, (q, bounded) => (bounded && q === T_NO_TOWN ? [ELSEWHERE, BESIDE, ON] : []),
      () => /Pick the street in the town you meant/.test(document.getElementById("geo-status").textContent),
      S_FULL, pickRow("West Oakley Drive Northwest, Westmont"), false, ranged);
    const tw = twoTowns.got, twa = twoTowns.after;
    check("a typed address on a street the search has in two towns lists both, marked, and selects neither",
      !tw.point && !tw.pin && tw.rows.length === 3 && tw.rows.every((r) => r.cls === "no-number") &&
        tw.status.indexOf("The map's search knows W Oakley Dr NW in Downers Grove and Westmont but not number 9 on it. " +
          "Pick the street in the town you meant to see it on the map.") >= 0,
      JSON.stringify(tw));
    check("picking the street in one town frames it there with the Census pin and its point selected, asked once for that town",
      atPin(twa.point) && !!twa.pin && twoTowns.lookedUp.length === 1 && twoTowns.lookedUp[0] === T_AT_ZIP &&
        twa.status.indexOf("W Oakley Dr NW in Westmont but not number 9 on it. The map has selected the pin") >= 0,
      JSON.stringify({ after: twa, lookedUp: twoTowns.lookedUp }));
    // A TOWN TYPED AFTER A COMMA IS KEPT (addressInTownOf). On 2026-10-19
    // Photon named the Cook County township where Chicago's name would be,
    // West Eugenie Street's as North Chicago Township, and answered other
    // Chicago streets once in Chicago and once in the township. The house
    // number, the Census answer and the street's extent are made up. Until
    // then the lookup was asked about the township, and its answer, in
    // Chicago, was refused.
    const E_TYPED = "9 W Eugenie St, Chicago, IL 60614";
    const E_PIN = { lat: 41.91283, lng: -87.63862 };
    const E_EXTENT = [-87.6430, 41.9131, -87.6345, 41.9125];
    const eugenie = (city) => feature(-87.6390, 41.9128, { name: "West Eugenie Street", district: "Lincoln Park", city,
      state: "Illinois", postcode: "60614", type: "street", extent: E_EXTENT });
    const township = await run(E_TYPED,
      (q, bounded) => (bounded && q === E_TYPED ? [eugenie("North Chicago Township"), eugenie("Chicago")] : []),
      pinShown, S_FULL, null, false, () => ({ status: 200, matches: [{ address: "9 W EUGENIE ST, CHICAGO, IL, 60614", ...E_PIN }] }));
    const tt = township.got;
    check("a typed town the answers name only by its ZIP code is kept: one street, the Census lookup asked about that town and ZIP code, its pin selected",
      !!tt.point && Math.abs(tt.point.lat - E_PIN.lat) < 1e-7 && Math.abs(tt.point.lng - E_PIN.lng) < 1e-7 && !!tt.pin &&
        township.lookedUp.length === 1 && township.lookedUp[0] === "9 W Eugenie St, Chicago, IL 60614" &&
        tt.status.indexOf("W Eugenie St in Chicago but not number 9 on it. The map has selected the pin") >= 0 &&
        tt.status.indexOf("Township") < 0,
      JSON.stringify(township));
    const typing = async (page, read) => {
      await page.fill("#geocode-input", T_ADDRESS);
      await page.waitForFunction(() => /Pick the street to see it on the map/.test(document.getElementById("geo-status").textContent),
        null, { timeout: QUERY_TIMEOUT }).catch(() => {});
      await page.waitForTimeout(300);
      const before = await read();
      return { before, after: await pickRow("West Oakley Drive Northwest, Westmont")(page, read) };
    };
    const typeAhead = await run("", (q, bounded) => (bounded && q === T_ADDRESS ? [BESIDE, ON] : []), () => true,
      S_FULL, typing, false, ranged);
    const tb = typeAhead.after.before, tp = typeAhead.after.after;
    check("an address being typed lists the answers without its number, marked, and asks the Census lookup nothing",
      !tb.point && !tb.pin && tb.rows.length === 2 && tb.rows.every((r) => r.cls === "no-number") &&
        tb.status.indexOf("The map's search knows W Oakley Dr NW in Westmont but not number 9 on it. " +
          "Pick the street to see it on the map.") >= 0,
      JSON.stringify(tb));
    check("picking the street's row then frames it, asks the Census lookup once and selects the pin's point",
      atPin(tp.point) && !!tp.pin && typeAhead.lookedUp.length === 1 && typeAhead.lookedUp[0] === T_AT_ZIP,
      JSON.stringify({ after: tp, lookedUp: typeAhead.lookedUp }));
    const loneStreet = await run(T_ADDRESS, (q, bounded) => (bounded ? [BESIDE] : []),
      () => /None of these has the house number 9/.test(document.getElementById("geo-status").textContent));
    check("the one answer to a sent address, on another street and without its number, is listed and not selected once the Census lookup has nothing",
      !loneStreet.got.point && !loneStreet.got.pin && loneStreet.got.rows.length === 1 && loneStreet.got.rows[0].cls === "no-number" &&
        loneStreet.got.status.indexOf("None of these has the house number 9, so pick one only if it's the place you meant, " +
          "or tap the place on the map.") >= 0 &&
        loneStreet.lookedUp.length === 1 && loneStreet.lookedUp[0] === T_AT &&
        loneStreet.asked.every((a) => a.indexOf("unbounded:") !== 0),
      JSON.stringify(loneStreet));
    // THE SEARCH KNOWS NEITHER THE HOUSE NOR ITS STREET in the town typed
    // (Adam's choice of 2026-10-19, "Use Census"): the Census Bureau is asked
    // about the address, written out in this app's state (T_AT), and its
    // answer, when it is the house, is the pin, with its point selected and
    // nothing listed. With no answer from the search at all, it is asked
    // once the sibling apps have none either.
    const noStreetShown = () => /street records put it\./.test(document.getElementById("geo-status").textContent);
    const noStreet = await run(T_ADDRESS, (q, bounded) => (bounded ? [BESIDE] : []), noStreetShown, S_FULL, null, true, ranged);
    const ns = noStreet.got, nsn = noteAt(ns.note);
    check("a sent address whose street the search lacks in its town goes to the Census lookup in this app's state, and its pin's point is selected",
      atPin(ns.point) && !!ns.pin && ns.pin.top >= ns.panelBelow && ns.rows.length === 0 &&
        ns.status.indexOf("The map's search didn't find that address. The map has selected the pin, where the Census Bureau's " +
          "street records put it. It can be a block or more from the house, and a district line can run between the two. " +
          "If the place is elsewhere, tap it on the map.") === 0 &&
        !!nsn && nsn.zoom === 19 && Math.abs(nsn.lat - PIN_AT.lat) < 1e-9 && Math.abs(nsn.lng - PIN_AT.lng) < 1e-9 &&
        noStreet.lookedUp.length === 1 && noStreet.lookedUp[0] === T_AT,
      JSON.stringify(noStreet));
    const nothing = await run(T_ADDRESS, () => [], noStreetShown, S_FULL, null, false, ranged);
    check("a sent address the search finds nothing for, here or in the sibling apps, gets the Census pin too",
      atPin(nothing.got.point) && !!nothing.got.pin && nothing.got.rows.length === 0 && !nothing.got.note &&
        nothing.asked.indexOf("unbounded:" + T_ADDRESS) >= 0 && nothing.lookedUp.length === 1 && nothing.lookedUp[0] === T_AT,
      JSON.stringify(nothing));
    // THE NUMBER ON ANOTHER STREET is not the house (labelAtHouse): on
    // 2026-10-19 the one answer for one of 49 Cook County addresses was its
    // number on a different street, which a question page's address box
    // selected. It is listed, marked other-street, and selected for nobody.
    const NUMBER_BESIDE = feature(-87.9779586, 41.8216492, { housenumber: "9", street: "Oakley Drive North", city: "Westmont",
      state: "Illinois", postcode: "60559" });
    const otherStreet = await run(T_ADDRESS, (q, bounded) => (bounded ? [NUMBER_BESIDE] : []),
      () => /None of these is number 9/.test(document.getElementById("geo-status").textContent));
    check("the one answer to a sent address that is its number on another street is listed, marked other-street, and not selected",
      !otherStreet.got.point && !otherStreet.got.pin && otherStreet.got.rows.length === 1 &&
        otherStreet.got.rows[0].cls === "other-street" &&
        otherStreet.got.status.indexOf("None of these is number 9 on the street you typed, so pick one only if it's the place " +
          "you meant, or tap the place on the map.") >= 0 && otherStreet.lookedUp.length === 1,
      JSON.stringify(otherStreet));
    // AN ADDRESS TYPED WITH NO TOWN takes the town of the answers on its
    // street, which for a Chicago street is the Cook County township, while
    // the Census Bureau's answer names the city: the lookup is asked with
    // the ZIP code those answers carry when they carry one, and the answer
    // is the house when it is in a ZIP code they carry. Until 2026-10-19 the
    // lookup was asked about the township alone and its answer refused as
    // not in the township. A ZIP code typed with the address goes to the
    // lookup with it.
    const E_NO_TOWN = "9 W Eugenie St";
    const E_ZIP = "9 W Eugenie St, IL 60614";
    const E_RANGE = { address: "9 W EUGENIE ST, CHICAGO, IL, 60614", ...E_PIN };
    const inTownship = (typed) => (q, bounded) => (bounded && q === typed ? [eugenie("North Chicago Township")] : []);
    const noTown = await run(E_NO_TOWN, inTownship(E_NO_TOWN), pinShown, S_FULL, null, false,
      () => ({ status: 200, matches: [E_RANGE] }));
    check("an address typed with no town is asked about with the answers' township and ZIP code, and a Census answer in that ZIP code is its pin",
      !!noTown.got.point && Math.abs(noTown.got.point.lat - E_PIN.lat) < 1e-7 && Math.abs(noTown.got.point.lng - E_PIN.lng) < 1e-7 &&
        !!noTown.got.pin && noTown.lookedUp.length === 1 && noTown.lookedUp[0] === "9 W Eugenie St, North Chicago Township, IL 60614",
      JSON.stringify(noTown));
    const zipTyped = await run(E_ZIP, inTownship(E_ZIP), pinShown, S_FULL, null, false,
      () => ({ status: 200, matches: [E_RANGE] }));
    check("a ZIP code typed with no town goes to the Census lookup with the address",
      !!zipTyped.got.pin && zipTyped.lookedUp.length === 1 &&
        zipTyped.lookedUp[0] === "9 W Eugenie St, North Chicago Township, IL 60614",
      JSON.stringify(zipTyped));
    // the stubbed lookup answers at once; the second read is long after it
    const later = async (page, read) => { await page.waitForTimeout(1500); return read(); };
    const otherZip = await run(E_NO_TOWN, inTownship(E_NO_TOWN), onStreet, S_FULL, later, false,
      () => ({ status: 200, matches: [{ ...E_RANGE, address: "9 W EUGENIE ST, CHICAGO, IL, 60601" }] }));
    check("a Census answer in another ZIP code, and not in the town asked about, is not the pin",
      !otherZip.after.pin && !otherZip.after.point && otherZip.lookedUp.length === 1 &&
        otherZip.after.status.indexOf("showing that street") >= 0,
      JSON.stringify(otherZip.after));
    const carried = await run(T_ADDRESS, (q, bounded) => (bounded ? [NUMBERED, ON] : []),
      () => document.querySelectorAll("#geocode-results li").length === 2, S_FULL, pickRow("9 West Oakley Drive Northwest", selected));
    check("beside an answer carrying a sent address's house number, one without it is marked, and neither is selected for the reader",
      !carried.got.point && carried.got.rows.length === 2 && carried.got.rows[0].cls === "" &&
        carried.got.rows[1].cls === "no-number" && carried.lookedUp.length === 0,
      JSON.stringify(carried.got));
    check("picking the answer carrying the number selects it, as before",
      !!carried.after.point && Math.abs(carried.after.point.lat - PIN_AT.lat) < 1e-7 &&
        Math.abs(carried.after.point.lng - PIN_AT.lng) < 1e-7 && carried.lookedUp.length === 0,
      JSON.stringify(carried.after));
    // Found only in a sibling app's state and without its number: the row
    // opens that app with the address, never with the answer's point
    const PARK_ROAD = feature(-89.7320, 43.4170, { name: "Park Road", city: "Baraboo", state: "Wisconsin", postcode: "53913",
      type: "street" });
    const W_ADDRESS = "S5975 Park Rd, Baraboo";
    const follow = async (page) => {
      await page.route("https://districtry.com/**", (route) =>
        route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>sibling</title>" }));
      const to = page.waitForURL((u) => !u.href.startsWith(BASE), { timeout: QUERY_TIMEOUT }).then(() => page.url(), () => null);
      await page.locator("#geocode-results li.sibling-result button").first().click();
      return to;
    };
    const away = await run(W_ADDRESS, (q, bounded) => (!bounded && q === W_ADDRESS ? [PARK_ROAD] : []),
      () => /looks like you're searching/.test(document.getElementById("geo-status").textContent), S_FULL, follow);
    const awayHash = away.after && /^https:\/\/districtry\.com\/wi\/#(.*)$/.exec(away.after);
    check("an address found only in a sibling app without its number is a row that opens that app with the address",
      !away.got.point && away.got.rows.length === 1 && away.got.rows[0].cls === "sibling-result no-number" &&
        !!awayHash && new URLSearchParams(awayHash[1]).get("q") === W_ADDRESS,
      JSON.stringify(away));
  }

  // 1d5. A LINK TO A PLACE IN ANOTHER STATE OPENS THAT STATE'S APP (ENGINE
  //      geocoder-search showLinkElsewhere). The installed app's launcher
  //      opens a shared place in the state the reader used last, and on
  //      2026-10-16 a place in Wisconsin shared from the Google Maps app was
  //      searched for here. Its address names Wisconsin, so this app opens
  //      /wi/ with the link, rebuilt from its words, as #q=, and asks the
  //      geocoder nothing; a short link is read by the lookup first. A link
  //      to a place in a state no app covers says so. A link in California
  //      is searched here as before, because San Francisco's app covers one
  //      city and the address alone does not say the place is in it. And
  //      among several answers to a link, the one that is the place itself
  //      (its name, house number and street) is selected (markLinkPlace),
  //      while the same answers without its number select nothing. The
  //      sibling apps and the lookup are stubbed.
  {
    const WI_FULL = "https://maps.google.com/?q=Devil's+Lake+State+Park,+S5975+Park+Rd,+Baraboo,+WI+53913&ftid=0x0:0x1&entry=gps";
    const WI_REBUILT = "https://www.google.com/maps?q=Devil's+Lake+State+Park,+S5975+Park+Rd,+Baraboo,+WI+53913";
    const OH_FULL = "https://maps.google.com/?q=Union+Terminal,+1301+Western+Ave,+Cincinnati,+OH+45203&ftid=0x0:0x2&entry=gps";
    const CA_FULL = "https://maps.google.com/?q=Grand+Central+Market,+317+S+Broadway,+Los+Angeles,+CA+90013&ftid=0x0:0x3&entry=gps";
    const IL_FULL = "https://maps.google.com/?q=Starved+Rock+Lodge,+2668+E+875th+Rd,+Oglesby,+IL+61348&ftid=0x0:0x4&entry=gps";
    const IL_NAMED = "Starved Rock Lodge, 2668 E 875th Rd, Oglesby, IL 61348";
    const feature = (lng, lat, props) => ({ type: "Feature", geometry: { type: "Point", coordinates: [lng, lat] }, properties: props });
    const LODGE = feature(-88.9893, 41.3196, { name: "Starved Rock Lodge", housenumber: "2668", street: "East 875th Road",
      city: "Oglesby", state: "Illinois", postcode: "61348" });
    const PARK = feature(-88.9750, 41.3150, { name: "Starved Rock State Park", city: "Oglesby", state: "Illinois" });
    const BRIDGE = feature(-88.9945, 41.3190, { name: "Starved Rock Lodge", street: "Fox Canyon Bridge", state: "Illinois" });
    const run = async (hash, answer, settled) => {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const asked = [], looked = [];
      const page = await booted(context, `${BASE}#q=${encodeURIComponent(hash)}`, async (p) => {
        await p.route("https://districtry.com/**", (route) =>
          route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>sibling</title>" }));
        await p.route("**/photon.komoot.io/**", (route) => {
          const q = new URL(route.request().url()).searchParams.get("q");
          asked.push(q);
          route.fulfill({ status: 200, contentType: "application/json",
            body: JSON.stringify({ type: "FeatureCollection", features: answer ? answer(q) : [] }) });
        });
        await p.route("**/link-lookup.districtry.deno.net/**", (route) => {
          looked.push(new URL(route.request().url()).searchParams.get("u"));
          route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ url: WI_FULL }) });
        });
      }, true);
      const went = await page.waitForURL((u) => !u.href.startsWith(BASE), { timeout: settled ? 3000 : QUERY_TIMEOUT })
        .then(() => page.url(), () => null);
      if (settled) await page.waitForFunction(settled, EXPORTS_NAME, { timeout: QUERY_TIMEOUT }).catch(() => {});
      await page.waitForTimeout(300); // a selection or a hand-off, if one were coming, follows the list
      const got = went ? null : await page.evaluate((ns) => ({
        point: window[ns].state.selectedPoint,
        status: document.getElementById("geo-status").textContent,
        rows: [...document.querySelectorAll("#geocode-results li")].map((li) => li.className),
      }), EXPORTS_NAME);
      await context.close();
      return { went, asked, looked, got };
    };
    const handed = (url) => {
      const m = url && /^https:\/\/districtry\.com\/wi\/#(.*)$/.exec(url);
      return m ? new URLSearchParams(m[1]).get("q") : null;
    };
    const short = await run("https://maps.app.goo.gl/AbCdEf123", null, null);
    check("a short link to a place in Wisconsin, read here, opens /wi/ with the link rebuilt from its words",
      handed(short.went) === WI_REBUILT && short.looked.length === 1 && short.asked.length === 0,
      JSON.stringify(short));
    const full = await run(WI_FULL, null, null);
    check("a Google Maps link to a place in Wisconsin opens /wi/ and asks the geocoder nothing",
      handed(full.went) === WI_REBUILT && full.asked.length === 0, JSON.stringify(full));
    const ohio = await run(OH_FULL, null, () => /Ohio/.test(document.getElementById("geo-status").textContent));
    check("a link to a place in a state no app covers says so, and nothing is searched or selected",
      !ohio.went && !ohio.got.point && ohio.asked.length === 0 &&
        /That Google Maps link is to a place in Ohio, which districtry doesn't cover yet\./.test(ohio.got.status),
      JSON.stringify(ohio));
    const ca = await run(CA_FULL, null, () => /match|doesn't say/.test(document.getElementById("geo-status").textContent));
    check("a link to a place in California is searched here, not handed to San Francisco's app",
      !ca.went && ca.asked[0] === "Grand Central Market, 317 S Broadway, Los Angeles, CA 90013", JSON.stringify(ca));
    const place = await run(IL_FULL, (q) => (q === IL_NAMED ? [PARK, LODGE, BRIDGE] : []),
      (ns) => !!window[ns].state.selectedPoint);
    check("among several answers to a link, the one that is the place itself is selected",
      !place.went && !!place.got.point && Math.abs(place.got.point.lat - 41.3196) < 1e-6 && Math.abs(place.got.point.lng + 88.9893) < 1e-6,
      JSON.stringify(place));
    const NO_NUMBER = feature(-88.9893, 41.3196, { name: "Starved Rock Lodge", street: "East 875th Road",
      city: "Oglesby", state: "Illinois", postcode: "61348" });
    const unsure = await run(IL_FULL, (q) => (q === IL_NAMED ? [PARK, NO_NUMBER, BRIDGE] : []),
      () => document.querySelectorAll("#geocode-results li").length === 3);
    check("the same answers without the place's house number select nothing and stay listed",
      !unsure.went && !unsure.got.point && unsure.got.rows.length === 3 && unsure.got.rows.every((c) => c !== "link-place"),
      JSON.stringify(unsure));
  }

  // 1d6. A ZIP CODE IS SHOWN WHOLE (ENGINE geocoder-search showZip, Adam's
  //      choice of 2026-10-21). A reader who searched 60625 reported that the
  //      map named one ward, and that ZIP code crosses four. A ZIP code handed
  //      over as #q= now selects the spot data/app/zip-index.json holds for
  //      it, turns the ZIP layer on and pins it, and turns on the city's wards
  //      to compare it with, so every ward it crosses is outlined; no geocoder
  //      is asked, and the pin is not counted as a reader's. The ZIP layer's
  //      whole set (what the pin reads) is served as the ZIP code's own
  //      extent and Chicago's wards as four strips across it, so no census or
  //      city server is needed; every other host is refused, which also stands
  //      in for the suburban ward servers. Then: a layer already on is
  //      compared instead and nothing more is turned on; a ZIP code another
  //      app holds opens that app with it (the sibling app stubbed); and a ZIP
  //      code no list holds is listed from the geocoder and selected only when
  //      the reader picks it, with a message saying the cards are for one spot.
  {
    const index = JSON.parse(readFileSync(join(INSTANCE_DIR, "data/app/zip-index.json"), "utf8"));
    const Z = index.features.find((f) => f.properties.zip === "60625");
    const [x0, y0, x1, y1] = Z.bbox;
    const [sx, sy] = Z.geometry.coordinates;
    // Esri JSON, as the census query answers: an outer ring wound clockwise
    const ZCTA = { features: [{ attributes: { ZCTA5: "60625" },
      geometry: { rings: [[[x0, y0], [x0, y1], [x1, y1], [x1, y0], [x0, y0]]] } }] };
    // four wards in strips, each reaching past the ZIP code's top and bottom so
    // it crosses the ZIP code's edge, with a vertex on each side at the spot's
    // latitude, inside the ZIP code: the comparison finds an overlap by a
    // vertex inside (ENGINE polygon-containment polygonsOverlap), and a strip
    // whose four corners all lie outside it would never be found. The spot is
    // inside Ward 40's strip.
    const cuts = [x0 - 0.01, (x0 + sx) / 2, sx - 0.005, sx + 0.005, x1 + 0.01];
    const WARDS = { type: "FeatureCollection", features: ["33", "39", "40", "47"].map((ward, i) => ({
      type: "Feature", properties: { ward: ward },
      geometry: { type: "Polygon", coordinates: [[[cuts[i], y0 - 0.01], [cuts[i + 1], y0 - 0.01], [cuts[i + 1], sy],
        [cuts[i + 1], y1 + 0.01], [cuts[i], y1 + 0.01], [cuts[i], sy], [cuts[i], y0 - 0.01]]] } })) };
    const POBOX = { type: "Feature", geometry: { type: "Point", coordinates: [-87.6298, 41.8781] },
      properties: { name: "60690", postcode: "60690", city: "Chicago", state: "Illinois", country: "United States",
        countrycode: "US", type: "other" } };
    const run = async (hash, leaves) => {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const asked = [];
      const page = await booted(context, `${BASE}#${hash}`, async (p) => {
        // every other host is refused (registered first, so the routes below win)
        await p.route((u) => !/^(localhost|127\.0\.0\.1)$/.test(u.hostname) &&
          !/cartocdn\.com$|cdnjs\.cloudflare\.com$/.test(u.hostname), (route) => route.abort());
        await p.route("https://districtry.com/**", (route) =>
          route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>sibling</title>" }));
        await p.route("**/tigerweb.geo.census.gov/**", (route) => /ZCTA/i.test(route.request().url())
          ? route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(ZCTA) })
          : route.abort());
        await p.route("**/data.cityofchicago.org/**", (route) => /p293-wvbd/.test(route.request().url())
          ? route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(WARDS) })
          : route.abort());
        await p.route("**/photon.komoot.io/**", (route) => {
          const q = new URL(route.request().url()).searchParams.get("q");
          asked.push(q);
          route.fulfill({ status: 200, contentType: "application/json",
            body: JSON.stringify({ type: "FeatureCollection", features: q === "60690" ? [POBOX] : [] }) });
        });
        await p.route("**/gc.zgo.at/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
        await p.addInitScript(() => {
          window.__gcEvents = [];
          window.goatcounter = { count: (vars) => window.__gcEvents.push(vars) };
        });
      }, leaves);
      return { context, page, asked };
    };
    const view = (page) => page.evaluate((ns) => ({
      point: window[ns].state.selectedPoint,
      status: (document.getElementById("geo-status").textContent || "").trim(),
      rows: [...document.querySelectorAll("#geocode-results li")].map((li) => li.className),
      on: [...document.querySelectorAll(".layer-block input[type=checkbox]")].filter((c) => c.checked).map((c) => c.id.replace(/^toggle-/, "")).sort(),
      parent: document.querySelectorAll(".rel-parent-outline").length,
      ink: window[ns].highlightColor("zip-code"),
      lead: (() => {
        const first = document.getElementById("groups-root").firstElementChild;
        return first && first.classList.contains("group-pinned")
          ? [...first.querySelectorAll(".layer-block input[type=checkbox]")].map((c) => c.id.replace(/^toggle-/, "")).join() || null : null;
      })(),
      open: document.querySelector(".search-shell").classList.contains("expanded"),
      crossing: [...document.querySelectorAll(".rel-map-label")].map((e) => e.textContent).sort(),
      hash: location.hash,
      button: !!document.querySelector(".zip-stats-btn"),
      events: (window.__gcEvents || []).filter((v) => v && v.event).map((v) => v.path),
    }), EXPORTS_NAME);
    // settled once the outlines carry the cards' own wording ("Ward 40", not
    // the boundary's bare "40"), which they take when the compared layer's
    // card has answered (ENGINE relationship-pinning relLabelText)
    const compared = (n, wording) => (page) => page.waitForFunction(([k, w]) => {
      const labels = [...document.querySelectorAll(".rel-map-label")].map((e) => e.textContent);
      return labels.length >= k && labels.every((t) => new RegExp(w).test(t)) && !!document.querySelector(".zip-stats-btn");
    }, [n, wording], { timeout: QUERY_TIMEOUT }).catch(() => {});

    let r = await run("q=60625");
    await compared(4, "^Ward \\d+$")(r.page);
    let got = await view(r.page);
    check("a ZIP code selects the spot inside it, turns on the ZIP layer and the wards, and pins the ZIP code",
      !!got.point && Math.abs(got.point.lat - sy) < 1e-6 && Math.abs(got.point.lng - sx) < 1e-6 &&
        got.on.join() === "ward,zip-code" && /(^|&)c=zp(&|$)/.test(got.hash.slice(1)),
      JSON.stringify({ point: got.point, on: got.on, hash: got.hash }));
    // the compared ZIP code is its own lit line in the comparison's ink, with
    // no second outline drawn over it (Adam, 2026-10-21: the whole set the
    // comparison reads is simplified and the tiles are not, so the two ran
    // side by side), and its card leads the list on a computer as on a phone
    check("every ward the ZIP code crosses is outlined against it, and the message says the spot is not an address",
      got.parent === 0 && got.ink === "#14181C" && got.lead === "zip-code" && got.crossing.join() === "Ward 33,Ward 39,Ward 40,Ward 47" && got.button &&
        /selected a spot inside ZIP code 60625, not at any address/.test(got.status) &&
        /every City Ward it crosses/.test(got.status),
      JSON.stringify({ parent: got.parent, ink: got.ink, lead: got.lead, crossing: got.crossing, status: got.status.slice(0, 220) }));
    check("a ZIP code a list holds is never sent to the geocoder", r.asked.length === 0, JSON.stringify(r.asked));
    check("a ZIP code search is counted by its layer, once, and its pin is not counted as a reader's",
      got.events.filter((e) => /^zip-search\//.test(e)).join() === "zip-search/zip-code" &&
        !got.events.some((e) => /^compare\//.test(e)),
      JSON.stringify(got.events));
    // "List them" opens the comparison's numbers (ENGINE compare-stats): a row
    // for each ward
    await r.page.click(".zip-stats-btn");
    const listed = await r.page.waitForFunction(() => {
      const modal = document.getElementById("stats-modal");
      return !!modal && !modal.hidden && document.querySelectorAll(".stats-row").length >= 4;
    }, null, { timeout: QUERY_TIMEOUT }).then(() => r.page.evaluate(() => document.querySelectorAll(".stats-row").length), () => 0);
    check("List them opens the comparison's numbers, a row for each ward the ZIP code crosses", listed === 4, `rows=${listed}`);
    await r.context.close();

    r = await run("q=60625&l=cg");
    await compared(1, "^IL-\\d+$")(r.page);
    got = await view(r.page);
    check("with a layer already on, the ZIP code is compared with it and the wards are not turned on",
      got.on.join() === "congress,zip-code" && got.crossing.length >= 1 && got.crossing.every((t) => /^IL-\d+$/.test(t)) &&
        /every U\.S\. House District it crosses/.test(got.status),
      JSON.stringify({ on: got.on, crossing: got.crossing, status: got.status.slice(-120) }));
    // the message stays open at the search bar and folds away once the reader
    // clicks elsewhere, keeping its words for when they come back to the bar
    const openBefore = got.open;
    await r.page.click(".group-pinned .group-heading");
    await r.page.waitForTimeout(200);
    got = await view(r.page);
    check("the ZIP code's message stays open until the reader clicks away from the search bar, then folds",
      openBefore === true && got.open === false && /selected a spot inside ZIP code 60625/.test(got.status),
      JSON.stringify({ openBefore, open: got.open, status: got.status.slice(0, 80) }));
    // stopping the comparison gives the ZIP code its own colour back and puts
    // its card back in its group
    await r.page.click(".group-pinned .pin-parent-btn");
    await r.page.waitForTimeout(300);
    got = await view(r.page);
    check("stopping the comparison gives the ZIP code back its own line and its card back its place",
      got.ink !== "#14181C" && !!got.ink && got.lead === null && got.parent === 0,
      JSON.stringify({ ink: got.ink, lead: got.lead }));
    await r.context.close();

    r = await run("q=53703", true);
    const went = await r.page.waitForURL((u) => !u.href.startsWith(BASE), { timeout: QUERY_TIMEOUT }).then(() => r.page.url(), () => null);
    check("a ZIP code another app holds opens that app with the ZIP code, and asks the geocoder nothing",
      went === "https://districtry.com/wi/#q=53703" && r.asked.length === 0, JSON.stringify({ went, asked: r.asked }));
    await r.context.close();

    r = await run("q=60690");
    await r.page.waitForFunction(() => document.querySelectorAll("#geocode-results li").length > 0, null, { timeout: QUERY_TIMEOUT }).catch(() => {});
    await r.page.waitForTimeout(300); // a selection, if one were coming, follows the list
    got = await view(r.page);
    check("a ZIP code no list holds is searched, and its answer is listed but not selected",
      r.asked.join() === "60690" && !got.point && got.rows.length === 1 && /\bzip-answer\b/.test(got.rows[0]),
      JSON.stringify({ asked: r.asked, point: got.point, rows: got.rows }));
    await r.page.click("#geocode-results li button");
    await r.page.waitForFunction((ns) => !!window[ns].state.selectedPoint, EXPORTS_NAME, { timeout: QUERY_TIMEOUT }).catch(() => {});
    got = await view(r.page);
    check("picking that answer selects it and says the cards are for that one spot",
      !!got.point && Math.abs(got.point.lat - 41.8781) < 1e-6 &&
        /can't show all of ZIP code 60690, so the cards are for this one spot in it/.test(got.status),
      JSON.stringify({ point: got.point, status: got.status }));
    await r.context.close();
  }

  // 1e. THE MASTHEAD NEVER WRAPS: its links fold into "More" from the end
  //     (dstFitMastheadActions) before the row would drop them below the
  //     search, which a reader saw as the search bar jumping from the middle
  //     to the right at ~1,600px. Measured at three widths: all links in the
  //     row, some folded with "What data is missing?" still in the row, and
  //     everything folded including the theme toggle, which folds last.
  {
    const context = await browser.newContext({ serviceWorkers: "block", viewport: { width: 1870, height: 900 } });
    const page = await booted(context, BASE);
    await page.waitForTimeout(800); // the web font changes the pills' widths
    const at = async (w) => {
      await page.setViewportSize({ width: w, height: 900 });
      await page.waitForTimeout(300);
      return page.evaluate(() => {
        const row = document.querySelector(".masthead-actions").getBoundingClientRect();
        const search = document.querySelector(".masthead .map-toolbar").getBoundingClientRect();
        const panel = document.getElementById("dst-more-panel");
        return {
          wrapped: row.top >= search.bottom - 2,
          folded: panel ? panel.children.length : 0,
          gapsInRow: !!document.querySelector(".masthead-actions > #gaps-btn"),
          toggleFolded: !!(panel && panel.querySelector(".districtry-theme-toggle")),
        };
      });
    };
    const wide = await at(1870), mid = await at(1400), narrow = await at(800);
    check("the masthead keeps one row at every desktop width",
      !wide.wrapped && !mid.wrapped && !narrow.wrapped, JSON.stringify({ wide, mid, narrow }));
    check("masthead links fold from the end, the data-gaps door last and the theme toggle after it",
      wide.folded === 0 && mid.folded > 0 && mid.gapsInRow && !mid.toggleFolded && narrow.toggleFolded && !narrow.gapsInRow,
      `1870:${wide.folded} 1400:${mid.folded} 800:${narrow.folded}`);
    await context.close();
  }

  // 1g. THE MORE MENU AND THE GAPS PANEL ARE COUNTED. At 1,400px some
  //     links sit in "More": opening it and picking an item are counted, the
  //     item by its name; opening the data-gaps panel, expanding a gap's
  //     explanation and following its "Suggest a source" link are counted,
  //     the last two by the gap's record id. Links are prevented from
  //     navigating so the page stays to be read.
  {
    const context = await browser.newContext({ serviceWorkers: "block", viewport: { width: 1400, height: 900 } });
    const page = await booted(context, BASE, async (p) => {
      await p.route("**/gc.zgo.at/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
      await p.addInitScript(() => {
        window.__gcEvents = [];
        window.goatcounter = { count: (vars) => window.__gcEvents.push(vars) };
      });
    });
    await page.waitForTimeout(800); // the web font changes the pills' widths
    await page.evaluate(() => document.addEventListener("click", (e) => {
      const a = e.target.closest && e.target.closest("a[href]");
      if (a) e.preventDefault();
    }, true));
    const events = () => page.evaluate(() => (window.__gcEvents || []).filter((v) => v && v.event).map((v) => v.path));
    const hasMore = await page.$("#dst-more-btn:not([hidden])").then((h) => !!h && page.isVisible("#dst-more-btn"));
    if (hasMore) {
      await page.click("#dst-more-btn");
      const key = await page.evaluate(() => {
        const item = document.querySelector("#dst-more-panel a, #dst-more-panel button");
        const href = item && item.getAttribute("href") || "";
        return item ? (item.id ? item.id.replace(/-btn$/, "") : href.split(/[?#]/)[0].split("/").pop().replace(/\.html$/, "")) : "";
      });
      await page.click("#dst-more-panel :is(a, button)");
      const more = (await events()).filter((e) => /^more-/.test(e));
      check("the More menu counts being opened and the item picked, once each",
        more.join() === "more-open,more-item/" + key, JSON.stringify(more));
    } else {
      check("the More menu counts being opened and the item picked, once each", false, "no More menu at 1,400px");
    }
    await page.click("#gaps-btn");
    const why = await page.waitForSelector(".gap-more-label", { state: "attached", timeout: QUERY_TIMEOUT }).then(() => true, () => false);
    if (why) {
      const id = await page.evaluate(() => {
        const d = document.querySelector(".gap-more");
        d.closest("details:not(.gap-more)") && (d.closest("details:not(.gap-more)").open = true);
        const m = /gap_id=([^&]+)/.exec(d.querySelector(".gap-suggest").getAttribute("href"));
        return m ? decodeURIComponent(m[1]) : "";
      });
      await page.click(".gap-more-label");
      await page.click(".gap-more[open] .gap-suggest");
      await page.waitForTimeout(100);
      const gaps = (await events()).filter((e) => /^gaps-/.test(e));
      check("the gaps panel counts opening, a gap's explanation and its suggestion link, by gap",
        id && gaps.join() === `gaps-open,gaps-why/${id},gaps-suggest/${id}`, JSON.stringify(gaps));
    } else {
      check("the gaps panel counts opening, a gap's explanation and its suggestion link, by gap", false, "the panel listed no gap");
    }
    await context.close();
  }

  // 1i. A SELECTION GOES TO THE APP THAT ANSWERS THERE. Decided by state
  //     outlines (ENGINE metro-portal + fleet-outlines.json), never by
  //     rectangles: Illinois's box reaches into Iowa, sibling boxes overlap
  //     over the Upper Peninsula, and the boxes claim states nobody serves.
  //     One place for each of those, plus the Loop, which is selected HERE.
  //     The sibling apps are stubbed: a wrong route would otherwise leave for
  //     the real site.
  //
  //     GARY MOVED FROM THE UNCOVERED CASE TO A ROUTING CASE ON 2026-10-07, when
  //     Indiana went live: the same click now belongs to /in/. The uncovered
  //     case moved to St. Louis, measured that day: inside no outline in
  //     fleet-outlines.json (Illinois's is the nearest, about 1.6 km east across
  //     the Mississippi) and inside this instance's permalink_gate, so it is
  //     still selectable. The app routes by outline containment alone, so that
  //     1.6 km is not inside any tolerance the APP applies; the landing page's
  //     own ~1.5 km allowance is why its test uses a point farther west.
  //
  //     ST. LOUIS MOVED TO A ROUTING CASE AT MISSOURI'S GO-LIVE, AND THE
  //     UNCOVERED CASE WENT WITH IT RATHER THAN MOVING AGAIN. Every state this
  //     instance's permalink_gate reaches is now live, and sampling the gate
  //     every 0.02 degrees against fleet-outlines.json that day found three
  //     points in no outline, all slivers between two simplified outlines
  //     along the Mississippi, which the next simplification would close. A
  //     point that thin is not a fixture (the Wisconsin band-probe lesson), so
  //     the half that a point nobody covers is selected here is asserted by
  //     the instances whose gates still reach an unserved state.
  {
    const cases = [
      { name: "Davenport, Iowa", lat: 41.52, lng: -90.58, want: "https://districtry.com/ia/" },
      { name: "Marquette, Michigan", lat: 46.54, lng: -87.40, want: "https://districtry.com/mi/" },
      { name: "Kenosha, Wisconsin", lat: 42.58, lng: -87.82, want: "https://districtry.com/wi/" },
      { name: "Gary, Indiana", lat: 41.60, lng: -87.34, want: "https://districtry.com/in/" },
      { name: "St. Louis, Missouri", lat: 38.627, lng: -90.199, want: "https://districtry.com/mo/" },
      { name: "the Loop", lat: 41.8825, lng: -87.6285, want: null },
    ];
    for (const c of cases) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, BASE, async (p) => {
        await p.route("https://districtry.com/**", (route) =>
          route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>sibling</title>" }));
      });
      await page.evaluate(({ lat, lng }) => {
        const X = window.ChiExplorer;
        X.map.fire("click", { latlng: window.L.latLng(lat, lng) });
      }, c);
      if (c.want) {
        const went = await page.waitForURL((u) => u.href.startsWith(c.want + "#point="), { timeout: QUERY_TIMEOUT })
          .then(() => page.url(), () => null);
        const pt = went && /#point=([-\d.]+),([-\d.]+)/.exec(went);
        check(`a click on ${c.name} from Illinois opens ${c.want} with the point`,
          !!pt && Math.abs(+pt[1] - c.lat) < 1e-4 && Math.abs(+pt[2] - c.lng) < 1e-4, went || page.url());
      } else {
        const sel = await page.waitForFunction(() => !!window.ChiExplorer.state.selectedPoint, null, { timeout: QUERY_TIMEOUT })
          .then(() => page.evaluate(() => window.ChiExplorer.state.selectedPoint), () => null);
        check(`a click on ${c.name} is selected in Illinois, not handed off`,
          !!sel && Math.abs(sel.lat - c.lat) < 1e-4 && page.url().startsWith(BASE), page.url());
      }
      await context.close();
    }

    // PANNING ACROSS A STATE LINE STAYS HERE (2026-10-13, the operator's
    // ruling, reversing his own of 2026-09-30). Until that day the map opened
    // a sibling's app as soon as its CENTRE crossed into that sibling's state.
    // The map is moved to Gary with nothing selected, after the wash has
    // painted (the retired hand-off read the wash's own outline first), and
    // the page must still be this app a few seconds later. The sibling apps
    // are stubbed, so a hand-off would show as a navigation rather than a
    // failed load.
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, BASE, async (p) => {
        await p.route("https://districtry.com/**", (route) =>
          route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>sibling</title>" }));
      });
      const painted = await page.waitForFunction(() => {
        const pane = document.querySelector(".leaflet-pane.leaflet-scope-mask-pane");
        return !!(pane && pane.querySelector("path"));
      }, null, { timeout: QUERY_TIMEOUT }).then(() => true, () => false);
      await page.evaluate((n) => window[n].map.setView([41.60, -87.34], 11, { animate: false }), EXPORTS_NAME);
      const left = await page.waitForURL((u) => !u.href.startsWith(BASE), { timeout: 4000 })
        .then(() => page.url(), () => null);
      const centre = await page.evaluate((n) => window[n] && window[n].map.getCenter(), EXPORTS_NAME).catch(() => null);
      check("panning the map into Indiana stays in Illinois (no switch on pan)",
        painted && !left && !!centre && Math.abs(centre.lng - -87.34) < 0.01,
        !painted ? "the wash never painted, so the pan was not tested" : left ? `navigated to ${left}` : page.url());
      await context.close();
    }

    // THE LAYERS ON TRAVEL WITH THE READER, NAMED BY WHAT THEY MEAN. A
    // hand-off names concepts from layer-concepts.json (carry=), because
    // Illinois's `congress` is Iowa's `us-house` and Illinois's `ward` is a
    // city council where Wisconsin's is an election ward. Three halves: a
    // click that crosses a state line carries them, the state menu's link
    // carries them, and an app booted with carry= turns on its own layers for
    // each concept it has and drops the rest.
    {
      // Light layers on purpose, and the click waits for the network to go
      // quiet. The page and every boundary file come from one HTTP/1.1 server
      // here, which a browser gives six connections, and the hand-off's own
      // outline request queues behind whatever is still downloading. With the
      // ward layer on as well this check failed once in this sandbox: the
      // outline file was asked for twice and the click was kept here, which
      // is the app's answer when that file cannot be read. The ward-to-city
      // council mapping is held by the boot half below instead.
      const want = ["county", "state-house", "state-senate", "us-house"].join();
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, BASE + "#layers=congress,il-senate,il-house,county", async (p) => {
        await p.route("https://districtry.com/**", (route) =>
          route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>sibling</title>" }));
      });
      await page.waitForFunction((n) => {
        const on = window[n].state.layersOn;
        return on.congress && on["il-senate"] && on["il-house"] && on.county;
      }, EXPORTS_NAME, { timeout: QUERY_TIMEOUT }).catch(() => {});
      await page.waitForLoadState("networkidle", { timeout: QUERY_TIMEOUT }).catch(() => {});
      const menuHref = await page.evaluate(() => {
        const a = [...document.querySelectorAll(".dst-metro-menu a")]
          .find((x) => /\/ia\/(#|$)/.test(x.getAttribute("href") || ""));
        if (!a) return null;
        a.dispatchEvent(new FocusEvent("focus"));
        return a.getAttribute("href");
      });
      const menuCarry = menuHref && /[#&]carry=([^&]*)/.exec(menuHref);
      check("the state menu's Iowa link carries the layers on, by concept",
        !!menuCarry && menuCarry[1].split(",").sort().join() === want && !/[#&]point=/.test(menuHref),
        menuHref || "no Iowa link in the state menu");
      await page.evaluate((n) => window[n].map.fire("click", { latlng: window.L.latLng(41.52, -90.58) }), EXPORTS_NAME);
      const went = await page.waitForURL((u) => u.href.startsWith("https://districtry.com/ia/#point="), { timeout: QUERY_TIMEOUT })
        .then(() => page.url(), () => null);
      const carry = went && /[#&]carry=([^&]*)/.exec(went);
      check("a click on Davenport carries the layers on to Iowa, by concept",
        !!carry && carry[1].split(",").sort().join() === want, went || page.url());
      await context.close();
    }
    {
      // `regional-education-agency` is Iowa's and Michigan's and not Illinois's,
      // so it must be dropped rather than break the boot.
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, BASE + "#point=41.88250,-87.62850&carry=us-house,state-senate,county,city-council,regional-education-agency");
      const on = await page.waitForFunction((n) => {
        const s = window[n].state.layersOn;
        return s.congress && s["il-senate"] && s.county && s.ward;
      }, EXPORTS_NAME, { timeout: QUERY_TIMEOUT })
        .then(() => page.evaluate((n) => Object.keys(window[n].state.layersOn).filter((id) => window[n].state.layersOn[id]).sort(), EXPORTS_NAME), () => null);
      check("an app opened with carry= turns on its own layer for each concept it has",
        !!on && on.join() === ["congress", "county", "il-senate", "ward"].join(), JSON.stringify(on));
      const hash = await page.waitForFunction(() => /[#&]l=/.test(location.hash), null, { timeout: QUERY_TIMEOUT })
        .then(() => page.evaluate(() => location.hash), () => page.evaluate(() => location.hash));
      check("the carried layers are rewritten as this app's own short link",
        /[#&]l=/.test(hash) && !/carry=/.test(hash), hash);
      await context.close();
    }
  }

  // 1i2. THE OTHER HALF OF THE ZIP COVERAGE CHECK IN 2b. A hide test alone
  //      passes for a layer that is hidden everywhere, which would be a ZIP
  //      toggle no reader ever sees — so the anchor must show the same layer
  //      VISIBLE. THIS CHECK REPLACED ONE THAT ASSERTED THE CARD'S EMPTY NOTE
  //      AT GARY, INDIANA ("this map holds Illinois's ZIP codes only"): with
  //      coverage declared the layer hides there instead of rendering a note,
  //      so that wording could no longer appear and the note itself was retired
  //      rather than left as a claim nothing keeps true.
  //
  //      Both halves read only the shipped state outline, with the census host
  //      refused, so neither depends on a government server being up.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=zip-code`, async (p) => {
      await p.route("**tigerweb.geo.census.gov/**", (r) => r.abort());
    });
    const visible = await page
      .waitForFunction(() => {
        const box = document.getElementById("toggle-zip-code");
        const block = box && box.closest(".layer-block");
        return !!block && block.hidden === false;
      }, null, { timeout: QUERY_TIMEOUT })
      .then(() => true, () => false);
    check("zip-code is in coverage at the Loop anchor (not hidden)", visible, `visible=${visible}`);
    await context.close();
  }

  // 1j. A LONG HOVER VALUE WRAPS INSIDE THE CARD. The hover row's value pill
  //     did not wrap, so a long one ("NORTH RIVER — Elementary (PK, K, 1, …)")
  //     took the line, squeezed the label to a column one or two words wide and
  //     ran off the card (reported 2026-09-29). Built with the app's own CSS,
  //     in the popup's own 324px content box, from the reported row's text.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, BASE);
    const m = await page.evaluate(() => {
      const box = document.createElement("div");
      box.className = "hover-popup";
      box.innerHTML = '<div class="leaflet-popup-content"><div class="hover-snapshot"><div class="hover-row">' +
        '<span class="hover-dot"></span><div class="hover-row-head">' +
        '<div class="hover-row-label">School Location (all, incl. private, nearest 3)</div>' +
        '<span class="hover-pill">NORTH RIVER — Elementary (PK, K, 1, 2, 3, 4, 5, 6, 7, 8)</span>' +
        '</div></div></div></div>';
      document.body.appendChild(box);
      const label = box.querySelector(".hover-row-label").getBoundingClientRect();
      const pill = box.querySelector(".hover-pill").getBoundingClientRect();
      const content = box.querySelector(".leaflet-popup-content").getBoundingClientRect();
      const line = parseFloat(getComputedStyle(box.querySelector(".hover-row-label")).fontSize) * 1.3;
      box.remove();
      return { labelH: label.height, line, pillRight: pill.right, contentRight: content.right };
    });
    check("a long hover value leaves its label on one line and stays inside the card",
      m.labelH < m.line * 1.5 && m.pillRight <= m.contentRight + 0.5, JSON.stringify(m));
    await context.close();
  }

  // 1k. THE WHOLE PRECINCT SET LOADS, AND A FULL PAGE IS REFUSED RATHER THAN
  //     DRAWN. The primary Socrata route returns one page and says nothing
  //     about what it left behind, so a set that comes back exactly full
  //     cannot be told from a complete one. The page was capped at 1,000 until
  //     2026-09-29 and Chicago publishes 1,291 ward precincts: the app drew
  //     1,000, and because the portal orders by ward the 291 it dropped were
  //     every precinct of wards 39 to 50 — the whole north side answered
  //     nothing once the set had cached. Both halves are asserted here with a
  //     stubbed portal: the layer loads all 1,291, and a response that exactly
  //     fills the page fails validation so the walk falls through to the
  //     export route, which hands over the whole dataset.
  //
  //     THE ARCHIVE IS REFUSED SO THE PORTAL PATH RUNS AT ALL. Since phase 6c
  //     this layer draws and answers from a committed tile archive and never
  //     asks the portal, so a stub of the portal would sit unused and this
  //     check would pass without exercising anything. Refusing the archive
  //     puts the layer back on its whole-file loader (tile-overlay block,
  //     redrawFromFile) — the same fallback smoke check 2d holds — which is
  //     where the route walk lives and where the defect was.
  {
    const TOTAL = 1291;
    const [plat, plng] = POINT.split(",").map(Number);
    const cell = (i) => {
      const x = plng + (i % 40) * 0.001, y = plat + Math.floor(i / 40) * 0.001;
      return { type: "Feature", properties: { ward: String(1 + (i % 50)), precinct: String(i) },
        geometry: { type: "Polygon", coordinates: [[[x, y], [x + 0.001, y], [x + 0.001, y + 0.001], [x, y + 0.001], [x, y]]] } };
    };
    const page_of = (n) => JSON.stringify({ type: "FeatureCollection",
      features: Array.from({ length: n }, (unused, i) => cell(i)) });
    const context = await browser.newContext({ serviceWorkers: "block" });
    let exportRoute = 0;
    const page = await booted(context, `${BASE}#point=${POINT}&layers=ward-precinct`, async (p) => {
      // the archive is refused, so the layer reads its whole file as it did
      // before phase 6c — which is the path the route walk is on
      await p.route("**/data/app/tiles/ward-precinct.pmtiles", (r) => r.fulfill({ status: 404, body: "" }));
      // the primary route: it hands back exactly as many features as it was
      // asked for, which is what a truncated page looks like from the browser
      await p.route("**/data.cityofchicago.org/resource/i8fv-xe4b.geojson*", (route) => {
        const url = route.request().url();
        if (/where/.test(url)) return route.fulfill({ status: 200, contentType: "application/json", body: page_of(1) });
        const want = Number((url.match(/limit=(\d+)/) || [])[1] || 1000);
        route.fulfill({ status: 200, contentType: "application/json", body: page_of(Math.min(want, TOTAL)) });
      });
      // the export route: the whole dataset, as the portal really answers it
      await p.route("**/api/v3/views/i8fv-xe4b/query.geojson*", (route) => {
        exportRoute += 1;
        route.fulfill({ status: 200, contentType: "application/json", body: page_of(TOTAL) });
      });
    });
    await page
      .waitForFunction((ns) => {
        const s = window[ns].layerLoadState("ward-precinct");
        return s && s.features > 0;
      }, EXPORTS_NAME, { timeout: QUERY_TIMEOUT })
      .catch(() => {});
    const m = await page.evaluate((ns) => {
      const E = window[ns], max = E.socrataPageMax();
      const one = { geometry: { type: "Polygon", coordinates: [] }, properties: {} };
      const set = (n) => ({ type: "FeatureCollection", features: new Array(n).fill(one) });
      return { loaded: E.layerLoadState("ward-precinct").features, max,
        primaryAsksForMax: E.socrataRouteUrls("i8fv-xe4b")[0].indexOf("$limit=" + max) !== -1,
        full: E.hasWholeUsableGeometry(set(max)), justUnder: E.hasWholeUsableGeometry(set(max - 1)) };
    }, EXPORTS_NAME);
    check("every published precinct loads, and a page-filling response is refused as truncated",
      m.loaded === TOTAL && m.primaryAsksForMax && m.full === false && m.justUnder === true,
      JSON.stringify({ ...m, exportRoute }));
    await context.close();
  }

  // 1k1b. THE CHICAGO PRECINCT CARD NAMES ITS POLLING PLACE, AND ONLY UP TO
  //      ELECTION DAY. The polling file is stubbed (every precinct to one test
  //      building) so the check does not expire with the real list: with a
  //      far-future election date the card must name the building, link the
  //      Board's lookup and drop a pin; with a past one it must name nothing.
  //      The Election Day notice is checked on a bare map while the real
  //      notice date has not passed, and must be absent from a link with a point.
  {
    const precincts = {};
    for (let w = 1; w <= 50; w++) for (let n = 1; n <= 90; n++) precincts[w + "-" + n] = 0;
    const [plat, plng] = POINT.split(",").map(Number);
    const fixture = (date) => JSON.stringify({ election: "Test Election", electionDate: date, listDate: "2026-10-19",
      lookupUrl: "https://chicagoelections.gov/voting/your-voter-information",
      sites: [{ place: "TEST POLLING SCHOOL", address: "1 N TEST ST", lat: plat + 0.001, lng: plng + 0.001 }], precincts });
    const read = async (date) => {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=ward-precinct`, async (p) => {
        await p.route("**/data/app/chicago-polling-places.json", (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: fixture(date) }));
      });
      await page.waitForFunction(() => {
        const c = document.getElementById("card-ward-precinct");
        return c && /Ward \d/.test(c.textContent);
      }, null, { timeout: QUERY_TIMEOUT }).catch(() => {});
      // Wait for the polling pin itself rather than a fixed pause: the ward
      // layer this one turns on drops its own office pin on its own schedule,
      // so a count of every pin after a pause was a race (#1725 read 2 and 2).
      if (date > "2026") {
        await page.waitForFunction(() => Array.from(document.querySelectorAll(".leaflet-tooltip-pane .poi-pin-label"))
          .some((el) => /TEST POLLING SCHOOL/.test(el.textContent)), null, { timeout: QUERY_TIMEOUT }).catch(() => {});
      } else {
        await page.waitForTimeout(1500);
      }
      const out = await page.evaluate(() => {
        const c = document.getElementById("card-ward-precinct");
        const block = c ? c.parentNode : null;
        const link = block ? block.querySelector(".card-footer-link") : null;
        const notice = document.getElementById("election-notice");
        return { text: c ? c.textContent.replace(/\s+/g, " ") : null,
          link: link ? link.href : null,
          // every pin says what it is beside itself; the polling pin's line
          // names the kind of place and the building
          pinLabels: Array.from(document.querySelectorAll(".leaflet-tooltip-pane .poi-pin-label"))
            .map((el) => el.textContent.replace(/\s+/g, " ").trim()),
          notice: notice ? notice.hidden : null };
      });
      await context.close();
      return out;
    };
    const live = await read("2999-01-01");
    check("the Chicago precinct card names its polling place, links the Board's lookup and pins the building",
      /TEST POLLING SCHOOL — 1 N TEST ST/.test(live.text || "") && /Test Election/.test(live.text || "") &&
      live.link === "https://chicagoelections.gov/voting/your-voter-information" && live.notice === true,
      JSON.stringify(live));
    const past = await read("2001-01-01");
    check("after its election date the precinct card names no polling place",
      past.text !== null && /Ward \d/.test(past.text) && !/Polling place/.test(past.text),
      JSON.stringify(past));
    check("the polling place drops one pin labelled with the kind of place and the building, and none after the election",
      live.pinLabels.filter((t) => t === "Polling placeTEST POLLING SCHOOL").length === 1 &&
      !past.pinLabels.some((t) => /TEST POLLING SCHOOL/.test(t)),
      JSON.stringify({ live: live.pinLabels, past: past.pinLabels }));
    {
      // A precinct feature carries its ward too, and the engine's fallback
      // reads "ward" first, so its map labels printed the ward (Adam,
      // 2026-10-23: every precinct inside Ward 33 read "33").
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, BASE);
      const name = await page.evaluate(() =>
        window.ChiExplorer.hoverValueFor("ward-precinct", { ward: "33", precinct: "06" }));
      check("a ward precinct's map label names the precinct, not its ward", name === "Precinct 6", JSON.stringify(name));
      await context.close();
    }
    const today = new Date().toLocaleDateString("en-CA", { timeZone: "America/Chicago" });
    if (today <= "2026-11-03") {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, BASE);
      const shown = await page.evaluate(() => {
        const n = document.getElementById("election-notice");
        return n ? !n.hidden : null;
      });
      let toggled = null;
      if (shown) {
        await page.click("#election-notice-go");
        await page.waitForTimeout(500);
        toggled = await page.evaluate(() => ["county", "county-precinct", "ward-precinct", "early-voting"].map((id) => {
          const b = document.getElementById("toggle-" + id); return !!(b && b.checked);
        }).concat([document.getElementById("election-notice").hidden]));
      }
      check("a bare map shows the Election Day notice, and its button turns on the precinct, early voting and county layers",
        shown === true && toggled && toggled.every(Boolean), JSON.stringify({ shown, toggled }));
      await context.close();
    }
  }

  // 1k2. THE CHICAGO WARD CARD LINKS THAT WARD'S CHIPOLI PAGE. The address is
  //     built from the ward number at runtime, so the monthly link check
  //     cannot probe it, and every path on chipoli.org answers 200 whatever
  //     the number, so a wrong one would look fine from outside too. Both City
  //     sources are stubbed so the ward is known: the card must carry exactly
  //     one Chipoli link, to /alderpersons/42, opening in a new tab, beside
  //     the line saying the site is not the City's.
  {
    const [plat, plng] = POINT.split(",").map(Number);
    const d = 0.01;
    const wards = JSON.stringify({ type: "FeatureCollection", features: [{ type: "Feature",
      properties: { ward: "42" },
      geometry: { type: "Polygon", coordinates: [[[plng - d, plat - d], [plng + d, plat - d],
        [plng + d, plat + d], [plng - d, plat + d], [plng - d, plat - d]]] } }] });
    const roster = JSON.stringify([{ ward: "42", alderman: "Hopkins, Brendan" }]);
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=ward`, async (p) => {
      await p.route(/p293-wvbd/, (r) => r.fulfill({ status: 200, contentType: "application/json", body: wards }));
      await p.route(/htai-wnw4/, (r) => r.fulfill({ status: 200, contentType: "application/json", body: roster }));
    });
    const card = await cardText(page, "ward");
    const chipoli = await page.evaluate(() => Array.from(document.querySelectorAll("#card-ward a"))
      .filter((a) => /chipoli\.org/.test(a.href))
      .map((a) => ({ href: a.href, text: a.textContent, target: a.target, rel: a.rel })));
    check("the Chicago ward card links that ward's Chipoli page and says the site is not the City's",
      chipoli.length === 1 && chipoli[0].href === "https://chipoli.org/alderpersons/42" &&
        chipoli[0].text.indexOf("Ward 42 on Chipoli") === 0 && chipoli[0].target === "_blank" &&
        /noopener/.test(chipoli[0].rel) && /not run by the City/.test(card.text),
      JSON.stringify({ chipoli, card: card.text.slice(0, 400) }));
    await context.close();
  }

  // 1k3. A PARK DISTRICT OFFICER'S OWN TELEPHONE AND E-MAIL ADDRESS SIT ON
  //     THAT OFFICER'S ROW, since Adam's ruling of 2026-10-17 ("if the
  //     official government source uses personal phone numbers, we publish
  //     those") and his choice of "E-mails too" the same day. The Loop is in
  //     the Chicago Park District, whose officers come from its own filing
  //     with the Comptroller (il-special-district-officials.json). Cook's park
  //     tiling is read live from the county, so it is stubbed with one square
  //     carrying the district's name and the card is known; what is expected
  //     is read from the shipped roster, so a weekly refresh that changes a
  //     number changes what is expected, and a filing that gives its officers
  //     neither is reported rather than passed. The card prints numbers with
  //     no-break hyphens, folded back before comparing.
  {
    const [plat, plng] = POINT.split(",").map(Number);
    const d = 0.01;
    const parks = JSON.stringify({ features: [{ attributes: { agency_description: "CHICAGO PARK DISTRICT" },
      geometry: { rings: [[[plng - d, plat - d], [plng - d, plat + d], [plng + d, plat + d],
        [plng + d, plat - d], [plng - d, plat - d]]] } }] });
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=park-district`, async (p) => {
      await p.route(/politicalBoundary\/MapServer\/23\/query/, (r) =>
        r.fulfill({ status: 200, contentType: "application/json", body: parks }));
    });
    const want = await page.evaluate(async () => {
      const r = await fetch("data/app/il-special-district-officials.json").then((x) => x.json());
      const rec = (((r.counties || {}).cook || {}).park || {})["CHICAGO PARK DISTRICT"] || {};
      return [].concat(rec.board || [], rec.heads || [])
        .filter((m) => m && m.name && (m.phone || m.email))
        .map((m) => ({ name: m.name, phones: [m.phone].concat(m.phonesExtra || []).filter(Boolean),
          email: m.email || null }));
    });
    const card = await cardText(page, "park-district");
    const rows = await page.evaluate(() => Array.from(document.querySelectorAll("#card-park-district .card-person"))
      .map((row) => ({
        name: (row.querySelector(".card-person-name") || {}).textContent || "",
        phones: Array.from(row.querySelectorAll("a.card-phone")).map((a) => a.textContent.replace(/‑/g, "-")),
        email: Array.from(row.querySelectorAll('a[href^="mailto:"]')).map((a) => a.getAttribute("href").slice(7))[0] || null,
      })));
    if (!want.length) {
      console.log("  SKIP  park-district officers' own telephone and e-mail — the Chicago Park District's filing gives its officers neither");
    } else {
      const wrong = want.filter((w) => {
        const row = rows.find((r) => r.name === w.name);
        return !row || row.phones.join("|") !== w.phones.join("|") || row.email !== w.email;
      });
      check("the Loop's park district card shows each officer's own telephone and e-mail address on that officer's row",
        !card.error && wrong.length === 0,
        JSON.stringify({ wrong: wrong.map((w) => w.name), rows: rows.map((r) => r.name), card: card.text.slice(0, 120) }));
    }
    await context.close();
  }

  // 1h. THE REPORT FORM OPENS FROM A LINK. `#feedback=<text>` beside a point
  //     opens the form with that text filled in, counted once as opened by a
  //     link; "Copy a link to this form" hands back a link carrying the view
  //     and the text; and the report the GitHub button drafts names the page
  //     without the feedback text, which it already carries above.
  {
    const context = await browser.newContext({ serviceWorkers: "block", permissions: ["clipboard-read", "clipboard-write"] });
    const page = await booted(context, `${BASE}#point=41.88250,-87.62850&layers=congress&feedback=Wrong%20name%20here`, async (p) => {
      await p.route("**/gc.zgo.at/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
      await p.addInitScript(() => {
        window.__gcEvents = [];
        window.goatcounter = { count: (vars) => window.__gcEvents.push(vars) };
        window.__opened = [];
        window.open = (url) => { window.__opened.push(String(url)); return null; };
      });
    });
    const opened = await page.waitForFunction(() => { const m = document.getElementById("feedback-modal"); return m && !m.hidden; },
      null, { timeout: QUERY_TIMEOUT }).then(() => true, () => false);
    const text = await page.evaluate(() => (document.getElementById("feedback-text") || {}).value || "");
    check("a #feedback= link opens the report form with its text filled in", opened && text === "Wrong name here", `open=${opened} text=${JSON.stringify(text)}`);
    await page.click(".feedback-link-btn");
    await page.waitForTimeout(300);
    const copied = await page.evaluate(() => navigator.clipboard.readText().catch(() => ""));
    check("the form's copied link carries the view and the text",
      /#p=41\.8825,-87\.6285&l=cg&/.test(copied) && /[#&]feedback=Wrong%20name%20here$/.test(copied), copied);
    await page.click("#feedback-github");
    const drafted = await page.evaluate(() => decodeURIComponent((window.__opened[0] || "").split("&body=")[1] || ""));
    check("the drafted report names the page without repeating the feedback text",
      /^Wrong name here\n/.test(drafted) && /Page: \S+#p=41\.8825,-87\.6285/.test(drafted) && !/Page: \S*feedback=/.test(drafted), drafted.slice(0, 160));
    const events = await page.evaluate(() => (window.__gcEvents || []).filter((v) => v && v.event && /^feedback/.test(v.path)).map((v) => v.path));
    check("opening from a link, copying and sending are each counted once",
      events.join() === "feedback-open/link,feedback-link,feedback-send/github", JSON.stringify(events));
    await context.close();
  }

  // 1i. THE SHARE POPOVER DRAWS A QR CODE, ENCODED HERE. Clicking Share opens
  //     the popover on every screen size now (the native sheet is its first row
  //     on a touch device rather than replacing it, because the OS sheet cannot
  //     host a QR and the QR has to be reachable on a phone too). The code is
  //     held to the URL it should carry, not merely counted: the QR payload is
  //     the same view with `ref=qr`, which differs from the copy-link URL's
  //     `ref=share` and so produces a DIFFERENT matrix, so a stale or
  //     wrong payload fails rather than passing for having drawn something. The
  //     white ground is asserted in the DARK theme, because an inverted QR fails
  //     on many scanners and that is the one thing here that must not follow the
  //     theme. Nothing is fetched to draw it, which is the whole reason the
  //     encoder is ours: a QR service would take this permalink — and the
  //     selected point at full precision inside it — in the URL of an image
  //     request.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=41.88250,-87.62850&layers=congress`, async (p) => {
      await p.route("**/gc.zgo.at/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
      await p.addInitScript(() => {
        window.__gcEvents = [];
        window.goatcounter = { count: (vars) => window.__gcEvents.push(vars) };
        document.documentElement.setAttribute("data-theme", "dark");
      });
    });
    await page.click(".share-btn");
    const drawn = await page.waitForFunction(() => {
      const svg = document.querySelector(".share-popover-qr svg");
      return svg ? { rects: (svg.querySelector("path").getAttribute("d").match(/h1v1h-1z/g) || []).length,
                     ground: svg.querySelector("rect").getAttribute("fill") } : null;
    }, null, { timeout: QUERY_TIMEOUT }).then((h) => h.jsonValue(), () => null);
    const urls = await page.evaluate(() => window.ChiExplorer.shareUrls());
    const expect = await page.evaluate((u) => window.ChiExplorer.qrDarkModules(u), urls.qr);
    const otherPayload = await page.evaluate((u) => window.ChiExplorer.qrDarkModules(u), urls.link);
    check("the share popover draws a QR of THIS view's qr-tagged link",
      !!drawn && !!expect && drawn.rects === expect.dark && drawn.rects !== otherPayload.dark,
      `drawn=${drawn && drawn.rects} qr=${expect && expect.dark} link=${otherPayload && otherPayload.dark} v=${expect && expect.version}`);
    // The short form, held literally: `cg` is congress's permanent code, so a
    // code that moved would fail here as well as in generate_metro_files.
    check("the QR payload carries ref=qr and the same point and layers, in the short form",
      /\?ref=qr#p=41\.8825,-87\.6285&l=cg(&z=[\d.]+)?$/.test(urls.qr) && /\?ref=share#p=41\.8825,-87\.6285&l=cg(&z=[\d.]+)?$/.test(urls.link),
      `${urls.qr} / ${urls.link}`);
    check("the QR keeps a white ground in the dark theme, so it still scans",
      !!drawn && drawn.ground === "#ffffff", drawn && drawn.ground);
    const events = await page.evaluate(() => (window.__gcEvents || []).filter((v) => v && v.event && /^share-qr$/.test(v.path)).map((v) => v.path));
    check("drawing the QR is counted once", events.length === 1, JSON.stringify(events));
    await context.close();
  }

  // 1l. THE INSTALL INVITATION AND THE APP COUNTS (engine install-app). On a
  //     phone-width screen the app holds Chrome's install event, so Chrome's
  //     own mini-infobar never appears, and offers an Install button once the
  //     reader has an answer on screen; pressing it hands over to the
  //     browser's own dialog. It is offered ONCE: after a reload, with the
  //     event fired again, nothing shows. On a computer the event is left
  //     alone. An iPhone's Safari has no such event and gets a short tip with
  //     no button. While the Android app is in Google Play's closed test, a
  //     phone whose browser names Android is invited to the test instead; the
  //     Install case below runs with this headless browser's own user agent,
  //     which does not name Android. A launch of the installed app is counted
  //     once per window and an install once, both by app and never by place.
  //     Chrome's real event cannot be produced in a test, so a synthetic one
  //     carries the two members the app uses, prompt() and userChoice.
  {
    const PHONE = { width: 390, height: 844 };
    const TAG = APP_DIR.replace(/\/$/, "");
    const VIEW = `${BASE}#p=41.8825,-87.6285&l=cg`;
    const stubCounter = async (p) => {
      await p.route("**/gc.zgo.at/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
      await p.addInitScript(() => {
        window.__gcEvents = [];
        window.goatcounter = { count: (vars) => window.__gcEvents.push(vars) };
      });
    };
    const fireInstallEvent = (p) => p.evaluate(() => {
      const e = new Event("beforeinstallprompt", { cancelable: true });
      window.__prompted = window.__prompted || 0;
      e.prompt = () => { window.__prompted++; return Promise.resolve(); };
      e.userChoice = Promise.resolve({ outcome: "accepted", platform: "web" });
      window.dispatchEvent(e);
      return e.defaultPrevented;
    });
    const installEvents = (p) => p.evaluate(() => (window.__gcEvents || [])
      .filter((v) => v && v.event && /^(install-invite|app-install|app-launch)\//.test(v.path)).map((v) => v.path));

    {
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE });
      const page = await booted(context, VIEW, stubCounter);
      const held = await fireInstallEvent(page);
      const shown = await page.waitForSelector(".install-invite .install-invite-go", { timeout: 10000 }).then(() => true, () => false);
      check("on a phone the app holds Chrome's install event and offers its own Install button after an answer",
        held === true && shown, `held=${held} shown=${shown}`);
      if (shown) await page.click(".install-invite-go");
      await page.waitForTimeout(200);
      const after = await page.evaluate(() => ({
        prompted: window.__prompted,
        bar: !!document.querySelector(".install-invite"),
        seen: localStorage.getItem("districtry-install-invite"),
        last: localStorage.getItem("districtry-last-app"),
      }));
      check("Install hands over to the browser's own dialog, and the invitation goes",
        after.prompted === 1 && !after.bar && after.seen === "shown", JSON.stringify(after));
      check("the app records which state was open last, for the installed app's launcher",
        after.last === TAG, JSON.stringify(after.last));
      await page.evaluate(() => window.dispatchEvent(new Event("appinstalled")));
      await page.waitForTimeout(100);
      const events = await installEvents(page);
      check("the invitation, its answer and the install are each counted once, by app",
        events.join() === `install-invite/shown,install-invite/accepted,app-install/${TAG}`, JSON.stringify(events));
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForFunction((n) => !!window[n], EXPORTS_NAME, { timeout: BOOT_TIMEOUT });
      const heldAgain = await fireInstallEvent(page);
      await page.waitForTimeout(4500);
      const again = await page.evaluate(() => !!document.querySelector(".install-invite"));
      check("the invitation is offered once: a later visit holds the event and shows nothing",
        heldAgain === true && !again, `held=${heldAgain} shown=${again}`);
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block", viewport: { width: 1280, height: 900 } });
      const page = await booted(context, VIEW, stubCounter);
      const held = await fireInstallEvent(page);
      check("on a computer the browser's own install control is left alone", held === false, `held=${held}`);
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE });
      await context.addInitScript(() => {
        const real = window.matchMedia.bind(window);
        window.matchMedia = (q) => /display-mode:\s*standalone/.test(q)
          ? { matches: true, media: q, onchange: null, addListener() {}, removeListener() {},
              addEventListener() {}, removeEventListener() {}, dispatchEvent() { return false; } }
          : real(q);
      });
      const page = await booted(context, BASE, stubCounter);
      await page.waitForTimeout(300);
      const first = await installEvents(page);
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForFunction((n) => !!window[n], EXPORTS_NAME, { timeout: BOOT_TIMEOUT });
      await page.waitForTimeout(300);
      const second = await installEvents(page);
      check("a launch of the installed app is counted once per window, by app",
        first.join() === `app-launch/${TAG}` && second.length === 0,
        `first=${JSON.stringify(first)} after reload=${JSON.stringify(second)}`);
      await context.close();
    }
    // NEW OR RETURNING. A first visit in a fresh browser counts
    // visit/first/<tag> and writes the one-character districtry-seen mark; a
    // reload in the same window counts nothing more; a new window in the same
    // browser finds the mark and counts visit/return/<tag>. Nothing else is
    // stored, and Google Analytics is loaded nowhere.
    {
      const visitEvents = (p) => p.evaluate(() => (window.__gcEvents || [])
        .filter((v) => v && v.event && /^visit\//.test(v.path)).map((v) => v.path));
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE });
      let gaRequests = 0;
      context.on("request", (r) => { if (/googletagmanager|google-analytics/.test(r.url())) gaRequests++; });
      const page = await booted(context, BASE, stubCounter);
      await page.waitForTimeout(300);
      const first = await visitEvents(page);
      const mark = await page.evaluate(() => localStorage.getItem("districtry-seen"));
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForFunction((n) => !!window[n], EXPORTS_NAME, { timeout: BOOT_TIMEOUT });
      await page.waitForTimeout(300);
      const reloaded = await visitEvents(page);
      const page2 = await booted(context, BASE, stubCounter);
      await page2.waitForTimeout(300);
      const second = await visitEvents(page2);
      check("a first visit, then a return in a new window, are each counted once by app, with no Google Analytics",
        first.join() === `visit/first/${TAG}` && mark === "1" && reloaded.length === 0 &&
          second.join() === `visit/return/${TAG}` && gaRequests === 0,
        `first=${JSON.stringify(first)} mark=${mark} reload=${JSON.stringify(reloaded)} new window=${JSON.stringify(second)} ga=${gaRequests}`);
      await context.close();
    }
    // A PLACE SHARED INTO THE APP. The launcher (/app/) hands it over as #q=,
    // in the shape Android shares a Google Maps place (its name, then the
    // link), and leaves districtry-share-in in session storage. The app must
    // select the place the link names, read in the browser, and count the
    // share once, by app and never by place; a reload counts nothing more.
    {
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE });
      await context.addInitScript(() => {
        try {
          if (!sessionStorage.getItem("__shareSeeded")) {
            sessionStorage.setItem("__shareSeeded", "1");
            sessionStorage.setItem("districtry-share-in", "1");
          }
        } catch (e) { /* blocked storage: the count check below reports it */ }
      });
      const SHARED = "Willis Tower https://www.google.com/maps/place/Willis+Tower/@41.8789,-87.6359,17z/data=!3m1!4b1!8m2!3d41.8788761!4d-87.6359149";
      const page = await booted(context, `${BASE}#q=${encodeURIComponent(SHARED)}`, stubCounter);
      const sel = await page.waitForFunction((n) => !!window[n].state.selectedPoint, EXPORTS_NAME, { timeout: QUERY_TIMEOUT })
        .then(() => page.evaluate((n) => window[n].state.selectedPoint, EXPORTS_NAME), () => null);
      await page.waitForTimeout(300);
      const shareEvents = () => page.evaluate(() => (window.__gcEvents || [])
        .filter((v) => v && v.event && /^(share-in|map-link)\//.test(v.path)).map((v) => v.path));
      const first = await shareEvents();
      const mark = await page.evaluate(() => sessionStorage.getItem("districtry-share-in"));
      check("a place shared into the app is selected from its link, read in the browser",
        !!sel && Math.abs(sel.lat - 41.8788761) < 1e-5 && Math.abs(sel.lng - -87.6359149) < 1e-5,
        JSON.stringify(sel));
      check("the share is counted once, by app, and its mark removed",
        first.filter((e) => e.indexOf("share-in/") === 0).join() === `share-in/${TAG}` && mark === null,
        JSON.stringify({ events: first, mark }));
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForFunction((n) => !!window[n], EXPORTS_NAME, { timeout: BOOT_TIMEOUT });
      await page.waitForTimeout(300);
      const again = (await shareEvents()).filter((e) => e.indexOf("share-in/") === 0);
      check("a reload in the same window counts the share no more", again.length === 0, JSON.stringify(again));
      await context.close();
    }
    // A LONG-PRESS SHORTCUT. The launcher hands "Use my location" on as
    // #locate and leaves districtry-shortcut in session storage. The map must
    // press its own location button, so the browser asks as it does for the
    // button, select where the reader is, and count the shortcut once, by app
    // and action. The key must leave the address before the browser answers:
    // with the location refused the map selects nothing, so only that strip
    // keeps a reload from asking again. A point in the address wins.
    const seedShortcut = (context, action) => context.addInitScript((a) => {
      try {
        if (!sessionStorage.getItem("__shortcutSeeded")) {
          sessionStorage.setItem("__shortcutSeeded", "1");
          sessionStorage.setItem("districtry-shortcut", a);
        }
      } catch (e) { /* blocked storage: the count check below reports it */ }
    }, action);
    const shortcutEvents = (p) => p.evaluate(() => (window.__gcEvents || [])
      .filter((v) => v && v.event && /^(geolocate|geolocate-success|locate-fail\/.*|app-shortcut\/.*|feedback-open\/.*)$/.test(v.path))
      .map((v) => v.path));
    {
      const HERE = { latitude: 41.8789, longitude: -87.6359 };
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE,
        permissions: ["geolocation"], geolocation: HERE });
      await seedShortcut(context, "locate");
      const page = await booted(context, `${BASE}#locate`, stubCounter);
      const sel = await page.waitForFunction((n) => !!window[n].state.selectedPoint, EXPORTS_NAME, { timeout: QUERY_TIMEOUT })
        .then(() => page.evaluate((n) => window[n].state.selectedPoint, EXPORTS_NAME), () => null);
      await page.waitForTimeout(300);
      const events = await shortcutEvents(page);
      const mark = await page.evaluate(() => sessionStorage.getItem("districtry-shortcut"));
      check("the locate shortcut selects where the reader is, through the map's own location button",
        !!sel && Math.abs(sel.lat - HERE.latitude) < 1e-6 && Math.abs(sel.lng - HERE.longitude) < 1e-6,
        JSON.stringify(sel));
      check("the locate shortcut is counted once, by app, beside the button's own counts, and its mark removed",
        events.slice().sort().join() === [`app-shortcut/${TAG}/locate`, "geolocate", "geolocate-success"].sort().join() && mark === null,
        JSON.stringify({ events, mark }));
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE });
      await seedShortcut(context, "locate");
      const page = await booted(context, `${BASE}#locate`, stubCounter);
      await page.waitForTimeout(800);
      const first = await shortcutEvents(page);
      const hash = await page.evaluate(() => location.hash);
      check("with the location refused, the locate shortcut says so once and leaves no #locate in the address",
        first.slice().sort().join() === [`app-shortcut/${TAG}/locate`, "geolocate", `locate-fail/${TAG}/denied`].sort().join() && hash === "",
        JSON.stringify({ first, hash }));
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForFunction((n) => !!window[n], EXPORTS_NAME, { timeout: BOOT_TIMEOUT });
      await page.waitForTimeout(800);
      const again = await shortcutEvents(page);
      check("a reload after the locate shortcut asks for the location no more", again.length === 0, JSON.stringify(again));
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE,
        permissions: ["geolocation"], geolocation: { latitude: 41.8789, longitude: -87.6359 } });
      const page = await booted(context, `${BASE}#p=41.8825,-87.6285&locate`, stubCounter);
      await page.waitForTimeout(800);
      const sel = await page.evaluate((n) => window[n].state.selectedPoint, EXPORTS_NAME);
      const events = await shortcutEvents(page);
      check("a point in the address wins over #locate, and the location is not asked for",
        !!sel && Math.abs(sel.lat - 41.8825) < 1e-6 && events.length === 0 &&
          !/locate/.test(await page.evaluate(() => location.hash)),
        JSON.stringify({ sel, events }));
      await context.close();
    }
    // "Report a problem" is handed on as #feedback, which opens the report
    // form exactly as a link to it does (check 1h), and is counted once.
    {
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE });
      await seedShortcut(context, "feedback");
      const page = await booted(context, `${BASE}#feedback`, stubCounter);
      await page.waitForTimeout(300);
      const open = await page.evaluate(() => {
        const m = document.getElementById("feedback-modal");
        return !!m && !m.hidden;
      });
      const events = await shortcutEvents(page);
      const mark = await page.evaluate(() => sessionStorage.getItem("districtry-shortcut"));
      check("the report shortcut opens the report form and is counted once, by app",
        open && events.slice().sort().join() === [`app-shortcut/${TAG}/feedback`, "feedback-open/link"].sort().join() && mark === null,
        JSON.stringify({ open, events, mark }));
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE,
        userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1" });
      const page = await booted(context, VIEW, stubCounter);
      const tip = await page.waitForSelector(".install-invite", { timeout: 10000 }).then(() => true, () => false);
      const bar = await page.evaluate(() => {
        const el = document.querySelector(".install-invite");
        return el ? { text: el.textContent, button: !!el.querySelector(".install-invite-go") } : null;
      });
      check("an iPhone's Safari gets the Add to Home Screen tip, with no Install button",
        tip && !!bar && /Add to Home Screen/.test(bar.text) && !bar.button, JSON.stringify(bar));
      if (tip) await page.click(".install-invite-close");
      const gone = await page.evaluate(() => !document.querySelector(".install-invite"));
      const events = await installEvents(page);
      check("closing the tip removes it, and the tip and its closing are each counted once",
        gone && events.join() === "install-invite/tip-shown,install-invite/tip-closed", JSON.stringify(events));
      await context.close();
    }
    // WHILE THE ANDROID APP IS IN GOOGLE PLAY'S CLOSED TEST, an Android phone
    // is invited to the test instead of being offered the website version:
    // Chrome's event is still held, no Install button is offered, and the bar
    // links the steps page. A reader who was offered the install before the
    // test began (the key already reads "shown") is asked once about the
    // test, and not again; and the Play app's own window is not asked at all.
    // A close or a followed link writes "test-answered", which the front
    // page's own invitation to the test reads (Adam, 2026-10-20: a "no"
    // stays closed), and an answer given there keeps this bar away too.
    const ANDROID_UA = "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36";
    {
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE, userAgent: ANDROID_UA });
      await context.addInitScript(() => {
        try {
          if (!sessionStorage.getItem("__inviteSeeded")) {
            sessionStorage.setItem("__inviteSeeded", "1");
            localStorage.setItem("districtry-install-invite", "shown");
          }
        } catch (e) { /* blocked storage: the checks below report it */ }
      });
      const page = await booted(context, VIEW, stubCounter);
      const held = await fireInstallEvent(page);
      const shown = await page.waitForSelector(".install-invite a.install-invite-go", { timeout: 10000 }).then(() => true, () => false);
      const bar = await page.evaluate(() => {
        const el = document.querySelector(".install-invite");
        const a = el && el.querySelector("a.install-invite-go");
        return el ? { text: el.textContent, href: a && a.getAttribute("href"),
          install: !!el.querySelector("button.install-invite-go") } : null;
      });
      check("on an Android phone the app holds Chrome's install event and invites the reader to the Play test instead",
        held === true && shown && !!bar && /Android app/.test(bar.text) && !bar.install &&
        bar.href === "/android.html?ref=map", JSON.stringify({ held, bar }));
      if (shown) {
        await page.evaluate(() => document.addEventListener("click", (e) => {
          if (e.target.closest && e.target.closest(".install-invite-go")) e.preventDefault();
        }));
        await page.click(".install-invite-go");
      }
      await page.waitForTimeout(200);
      const after = await page.evaluate(() => ({
        prompted: window.__prompted || 0,
        bar: !!document.querySelector(".install-invite"),
        seen: localStorage.getItem("districtry-install-invite"),
      }));
      const events = await installEvents(page);
      check("following the test link counts it, records the answer, hands Chrome's dialog nothing, and the bar goes",
        after.prompted === 0 && !after.bar && after.seen === "test-answered" &&
        events.join() === "install-invite/test-shown,install-invite/test-join",
        JSON.stringify({ after, events }));
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForFunction((n) => !!window[n], EXPORTS_NAME, { timeout: BOOT_TIMEOUT });
      const heldAgain = await fireInstallEvent(page);
      await page.waitForTimeout(4500);
      const again = await page.evaluate(() => !!document.querySelector(".install-invite"));
      check("the test is offered once: a later visit holds the event and shows nothing",
        heldAgain === true && !again, `held=${heldAgain} shown=${again}`);
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE, userAgent: ANDROID_UA });
      const page = await booted(context, VIEW, stubCounter);
      const shown = await page.waitForSelector(".install-invite-close", { timeout: 10000 }).then(() => true, () => false);
      if (shown) await page.click(".install-invite-close");
      await page.waitForTimeout(200);
      const after = await page.evaluate(() => ({
        bar: !!document.querySelector(".install-invite"),
        seen: localStorage.getItem("districtry-install-invite"),
      }));
      const events = await installEvents(page);
      check("closing the test invitation records the answer the front page reads, and is counted once",
        shown && !after.bar && after.seen === "test-answered" &&
        events.join() === "install-invite/test-shown,install-invite/test-closed",
        JSON.stringify({ shown, after, events }));
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE, userAgent: ANDROID_UA });
      await context.addInitScript(() => {
        try { localStorage.setItem("districtry-install-invite", "test-answered"); } catch (e) { /* reported below */ }
      });
      const page = await booted(context, VIEW, stubCounter);
      await page.waitForTimeout(4500);
      const bar = await page.evaluate(() => !!document.querySelector(".install-invite"));
      const events = await installEvents(page);
      check("a reader who answered the front page's invitation is not invited again on the map",
        !bar && events.length === 0, JSON.stringify({ bar, events }));
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block", viewport: PHONE, userAgent: ANDROID_UA });
      const page = await booted(context, `${BASE}?ref=play#p=41.8825,-87.6285&l=cg`, stubCounter);
      await page.waitForTimeout(4500);
      const inApp = await page.evaluate(() => ({
        marked: document.documentElement.classList.contains("dst-play-app"),
        bar: !!document.querySelector(".install-invite"),
      }));
      check("inside the Play app nobody is invited to the test",
        inApp.marked && !inApp.bar, JSON.stringify(inApp));
      await context.close();
    }
  }

  // 1m. INSIDE THE GOOGLE PLAY APP THE SUPPORT LINKS ARE HIDDEN, AND ONLY
  //     THERE (engine/shared/play-app.txt). The Play app is this site in a
  //     full-screen Chrome window and Google Play does not allow an app to
  //     send readers to an outside payment page, so a window the app opened
  //     (it arrives with ?ref=play, passed on by the launcher) hides every
  //     link to GitHub Sponsors and to the sponsorship page: the panel's
  //     sponsorship sentence and its Sponsorship link. (The page's old footer
  //     carries a third, and the skin has drawn that footer nowhere since the
  //     redesign, so it is counted in `anywhere` and not in the panel.) The
  //     mark is kept for the window, so the next page hides them with no tag
  //     in its address. A plain visit must keep the panel's links, which is
  //     the half that stops a rule hiding them everywhere from passing.
  {
    const supportShown = (p) => p.evaluate(() => {
      const visible = (el) => !!el && el.getClientRects().length > 0;
      const all = (sel) => Array.prototype.slice.call(document.querySelectorAll(sel));
      const support = ['a[href*="github.com/sponsors"]', 'a[href*="sponsorship.html"]'];
      return {
        marked: document.documentElement.classList.contains("dst-play-app"),
        kept: (function () { try { return sessionStorage.getItem("districtry-play-app"); } catch (e) { return "blocked"; } })(),
        sentence: visible(document.querySelector(".dpf-support")),
        panel: all(support.map((sel) => "#districtry-panel-foot " + sel).join(", ")).map(visible),
        anywhere: all(support.join(", ")).filter(visible).length,
      };
    });
    const noCounter = async (p) => {
      await p.route("**/gc.zgo.at/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
    };
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}?ref=play`, noCounter);
      const inApp = await supportShown(page);
      check("in the Play app every support link on the map page is hidden",
        inApp.marked && inApp.kept === "1" && !inApp.sentence &&
          inApp.panel.length >= 3 && inApp.panel.every((v) => !v) && inApp.anywhere === 0,
        JSON.stringify(inApp));
      await page.goto(`${BASE}sources.html`, { waitUntil: "domcontentloaded" });
      const next = await supportShown(page);
      check("the mark carries to the next page in the window, with no tag in its address",
        next.marked && next.anywhere === 0 &&
          (await page.locator('a[href*="github.com/sponsors"]').count()) >= 1,
        JSON.stringify(next));
      await context.close();
    }
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, BASE, noCounter);
      const web = await supportShown(page);
      check("on the website the map page keeps its support links",
        !web.marked && web.kept === null && web.sentence &&
          web.panel.length >= 3 && web.panel.every((v) => v),
        JSON.stringify(web));
      await context.close();
    }
  }

  // 1f. COMPARISON STATS. With Congress pinned at the Loop and the State
  //     House on, the pinned card carries "Stats", and the screen it opens
  //     counts people from the shipped Census block files: IL-7 holds
  //     753,659 (drawn to 753,677; the 18 people are the simplified outline).
  //     This read 753,676 until 2026-09-25, when the legislative geometry moved
  //     to Douglas-Peucker simplified as ONE family, and the value is a fixture
  //     of whatever outline ships rather than a fact about the district. The
  //     swap was MEASURED before this number was changed, because updating an
  //     expected value to make a test pass is only honest if the new value is
  //     the better one: summing the same block files through both outlines, the
  //     old one was a mean 3.3 people off each district's ideal (worst 14) and
  //     the new one is 3.9 (worst 18), while both assign every block exactly
  //     once. So the new outline is a touch worse at this and 18.6x truer to
  //     where the boundary actually runs, and IL-7's old one-person miss was
  //     luck rather than accuracy.
  //     Every House district it lists is a real overlap, and the House map
  //     covers all of it, so no share of it is left unassigned. Every file
  //     involved ships in data/app, so this needs no live service. The use is
  //     counted by the PINNED layer, once.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=41.88250,-87.62850&layers=congress,il-house&pin=congress&zoom=11`, async (p) => {
      await p.route("**/gc.zgo.at/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
      await p.addInitScript(() => {
        window.__gcEvents = [];
        window.goatcounter = { count: (vars) => window.__gcEvents.push(vars) };
      });
    });
    const shown = await page.waitForSelector(".pin-stats-btn:not([hidden])", { timeout: QUERY_TIMEOUT }).then(() => true, () => false);
    check("a pinned district's card carries the comparison stats button", shown);
    if (shown) {
      await page.click(".pin-stats-btn:not([hidden])");
      await page
        .waitForFunction(() => { const e = document.querySelector(".stats-people"); return e && /^People: .* of its/.test(e.textContent); },
          null, { timeout: QUERY_TIMEOUT })
        .catch(() => {});
      const stats = await page.evaluate(() => ({
        open: !document.getElementById("stats-modal").hidden,
        totals: (document.querySelector(".stats-totals") || {}).textContent || "",
        rows: document.querySelectorAll(".stats-row").length,
        people: [...document.querySelectorAll(".stats-people")].map((e) => e.textContent),
        rest: [...document.querySelectorAll(".stats-rest")].map((e) => e.textContent),
        events: (window.__gcEvents || []).filter((v) => v && v.event).map((v) => v.path),
      }));
      check("the stats screen counts the compared district's people from the block files",
        stats.open && /^753,659 people · \d+ sq mi$/.test(stats.totals), stats.totals);
      check("the stats screen lists each overlapping district with its share of people",
        stats.rows >= 10 && stats.people.length === stats.rows && stats.people.every((t) => /^People: .* of its [\d,]+ are in IL-7/.test(t)),
        `${stats.rows} row(s); first: ${stats.people[0]}`);
      check("a layer that covers the compared district leaves none of it unassigned",
        stats.rest.length === 1 && /^Every part of IL-7/.test(stats.rest[0]), JSON.stringify(stats.rest));
      check("opening the stats is counted in GoatCounter by the pinned layer, once",
        stats.events.filter((e) => /^compare-stats\//.test(e)).join() === "compare-stats/congress", JSON.stringify(stats.events));
      // Opening a row is counted by the ROW's layer, once; printing opens
      // every other row and must count none of them.
      await page.click(".stats-row summary");
      // PRINT OR SHARE opens every row and waits for its card before the
      // print dialog; window.print is replaced by a recorder so the check
      // sees the report as it would be printed.
      await page.evaluate(() => { window.__printed = 0; window.print = () => { window.__printed += 1; }; });
      await page.click(".stats-print-btn");
      await page.waitForFunction(() => window.__printed > 0, null, { timeout: QUERY_TIMEOUT }).catch(() => {});
      const printed = await page.evaluate(() => ({
        printed: window.__printed,
        rows: document.querySelectorAll(".stats-row").length,
        open: document.querySelectorAll(".stats-row[open]").length,
        loading: [...document.querySelectorAll(".stats-card")].filter((c) => /Loading/.test(c.textContent)).length,
        parent: ((document.querySelector(".stats-parent-card") || {}).textContent || "").trim().length,
        printing: document.body.classList.contains("stats-printing"),
      }));
      check("the report leads with the compared district's own card",
        printed.parent > 0, `${printed.parent} characters`);
      check("printing the report opens every row, with every card loaded, before the print dialog",
        printed.printed === 1 && printed.printing && printed.open === printed.rows && printed.loading === 0,
        JSON.stringify(printed));
      const statsEvents = await page.evaluate(() =>
        (window.__gcEvents || []).filter((v) => v && v.event && /^compare-stats-(row|print)\//.test(v.path)).map((v) => v.path));
      check("opening a row and printing are each counted once, by layer",
        statsEvents.join() === "compare-stats-row/il-house,compare-stats-print/congress", JSON.stringify(statsEvents));
      // A LINK REOPENS THE REPORT: the open report puts s=1 in the
      // permalink, closing it takes it out, and a fresh load of that link
      // opens the report by itself once the boundaries are in.
      const openHash = await page.evaluate(() => location.hash);
      await page.click(".stats-link-btn");
      const linkEvents = await page.evaluate(() =>
        (window.__gcEvents || []).filter((v) => v && v.event && /^compare-stats-link\//.test(v.path)).map((v) => v.path));
      check("copying the report's link is counted by the pinned layer, once",
        linkEvents.join() === "compare-stats-link/congress", JSON.stringify(linkEvents));
      await page.keyboard.press("Escape");
      const closedHash = await page.evaluate(() => location.hash);
      check("the open report puts s=1 in the link, and closing it takes it out",
        /[#&]c=cg&s=1(&|$)/.test(openHash) && !/(^|[#&])s=1(&|$)/.test(closedHash), `${openHash} / ${closedHash}`);
      const again = await browser.newContext({ serviceWorkers: "block" });
      // The Congress card's roster is held back 4 s so the boundaries always
      // arrive first: the report must wait for the card, whose wording names
      // the district ("IL-7"), rather than open on the bare number ("7"). The
      // first deploy of this restore lost that race on CI's timing alone.
      const reopened = await booted(again, `${BASE}${openHash}`, async (p) => {
        await p.route("**/congress-roster.json", async (route) => {
          await new Promise((res) => setTimeout(res, 4000));
          await route.continue();
        });
        await p.route("**/gc.zgo.at/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
        await p.addInitScript(() => {
          window.__gcEvents = [];
          window.goatcounter = { count: (vars) => window.__gcEvents.push(vars) };
        });
      });
      const came = await reopened
        .waitForFunction(() => { const m = document.getElementById("stats-modal"); return m && !m.hidden && document.querySelectorAll(".stats-row").length >= 10; },
          null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const back = await reopened.evaluate(() => ({
        name: ((document.querySelector("#stats-modal .stats-name") || {}).textContent || ""),
        rows: document.querySelectorAll(".stats-row").length,
        hash: location.hash,
        events: (window.__gcEvents || []).filter((v) => v && v.event && /^compare-stats/.test(v.path)).map((v) => v.path),
      }));
      check("a link carrying s=1 reopens the report for the same district",
        came && back.name === "IL-7" && /(^|[#&])s=1(&|$)/.test(back.hash), JSON.stringify(back));
      check("a report reopened by a link is counted apart from one opened by hand",
        back.events.join() === "compare-stats-reopen/congress", JSON.stringify(back.events));
      await again.close();
    }
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
        `${id} classifies point (${/^\d/.test(want) ? "District " + want : want})`,
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
    // re-styling every path. MOVE_POINT is school-board district 2b (vs 6b at
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
      // lit, read from the app rather than counted as SVG paths: the anchor
      // layers are drawn from vector tiles since phase 5, on a GL canvas
      const st = window[n].layerLoadState("school-board");
      const highlights = st && st.highlight ? 1 : 0;
      return { text: el ? cardTextNow() : "(no card)", highlights };
    }, { n: EXPORTS_NAME, lat: MOVE_POINT.lat, lng: MOVE_POINT.lng, district: MOVE_POINT.district });
    check(
      `point move re-classifies (${EXPECT_DISTRICT["school-board"]} -> ${MOVE_POINT.district}) and re-highlights`,
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
    const toggled = await page.evaluate(async ({ n, ids }) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // lit layers, read from the app (see smoke-move-point)
      const count = () => ids.filter((id) => { const st = window[n].layerLoadState(id); return st && st.highlight; }).length;
      const box = document.getElementById("toggle-ccbr");
      const before = count();
      box.click(); // ccbr off
      await wait(150);
      const afterOff = count();
      box.click(); // ccbr back on
      for (let i = 0; i < 100; i++) { if (count() >= before) break; await wait(100); }
      return { before, afterOff, afterOn: count() };
    }, { n: EXPORTS_NAME, ids: OFFLINE });
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
    const page = await booted(context, `${BASE}#point=${NEGATIVE_POINT}&layers=${NEGATIVE_IDS.join(",")}`, async (p) => {
      await p.route(`**${PORTAL_HOST}**`, (r) => r.abort());
      // And the census host, for the ZIP layer in NEGATIVE_IDS. Its coverage
      // test reads the shipped state outline and never the census, so the hide
      // verdict is identical either way — aborting it is what keeps this
      // check's verdict independent of whether a runner can reach TIGERweb.
      await p.route("**tigerweb.geo.census.gov/**", (r) => r.abort());
    });
    for (const id of NEGATIVE_IDS) {
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
      // Read through the app's own parse: the hash is rewritten into the
      // short form (`l=cb,fd`) once the toggles fire, so the ids are only
      // visible decoded.
      const ids = window[n].permalinkState().layers;
      return {
        boardOn: !!(board && board.checked) && window[n].state.layersOn["county-board"] === true,
        fireOn: !!(fire && fire.checked) && window[n].state.layersOn["fire-district"] === true,
        hashRewritten: ids.includes("county-board") && ids.includes("fire-district") &&
          !ids.includes("commissioner") && !ids.includes("will-county-board") &&
          !ids.includes("will-county-fire"),
        oneCopy: ids.filter((id) => id === "county-board").length === 1,
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
  //     Stephenson is a shipped county, so county-board draws it from its
  //     tile archive (docs/OPTIMIZATION_PLAYBOOK.md §10 phase 5b). This check
  //     refuses the archive, which is also the check that a layer whose
  //     archive fails falls back to its whole files (tile-overlay block,
  //     redrawFromFile) rather than drawing nothing: the Leaflet union is
  //     what draws here, and what still draws wherever WebGL does not.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const stragglerBody = readFileSync(join(INSTANCE_DIR, STRAGGLER_FILE), "utf8");
    const stragglerFeatures = JSON.parse(stragglerBody).features.length;
    const STRAGGLER_DELAY_MS = 8000;
    // STRAGGLER_POINT sits inside a district of the delayed county's file.
    // The point is selected only once the layer is loading: a point selected
    // first makes the union load its own county first (point-first,
    // docs/OPTIMIZATION_PLAYBOOK.md §10), which is the stalled one, and this
    // check is about every OTHER county drawing without waiting for it.
    const page = await booted(
      context,
      `${BASE}#layers=county-board`,
      async (p) => {
        await p.route("**/data/app/tiles/county-board.pmtiles", (r) => r.fulfill({ status: 404, body: "" }));
        await p.route("**/" + STRAGGLER_FILE, async (r) => {
          await new Promise((res) => setTimeout(res, STRAGGLER_DELAY_MS));
          await r.fulfill({ status: 200, contentType: "application/json", body: stragglerBody });
        });
      }
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
    const [slat, slng] = STRAGGLER_POINT.split(",").map(Number);
    await page.evaluate(({ n, lat, lng }) => window[n].setSelectedPoint(lat, lng), { n: EXPORTS_NAME, lat: slat, lng: slng });
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

  // 2u. A county layer draws its SHIPPED counties from its tile archive
  //     (docs/OPTIMIZATION_PLAYBOOK.md §10 phase 5b). At a point in
  //     Stephenson County the county-board card answers, its district is lit
  //     on the tile canvas, and no county's boundary FILE is downloaded —
  //     neither Stephenson's for the card nor the other shipped counties'
  //     for the map, which before phase 5b all downloaded once the card had
  //     answered. Skipped, saying so, where the vector basemap did not boot
  //     and there is no tile canvas to draw on.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const boundaryFiles = [];
    const page = await booted(context, `${BASE}#point=${STRAGGLER_POINT}&layers=county-board`, async (p) => {
      p.on("request", (r) => {
        const path = new URL(r.url()).pathname;
        // a county's board-district file; the school board's is a different
        // layer's, which the app loads at boot for its city coverage test
        if (/\/data\/app\/(?!school-board)[^/]*(board|commissioner)[^/]*districts\.json$/.test(path)) boundaryFiles.push(path.split("/").pop());
      });
    });
    const state = await page
      .waitForFunction((n) => {
        const t = window[n].tileState("county-board"), l = window[n].layerLoadState("county-board");
        if (!t || !l || l.card !== "result") return null;
        return !t.drawn || t.selected != null ? { drawn: t.drawn, selected: t.selected } : null;
      }, EXPORTS_NAME, { timeout: QUERY_TIMEOUT })
      .then((h) => h.jsonValue(), () => null);
    if (state && !state.drawn) {
      console.log("  SKIP  county-board tile canvas: the vector basemap did not boot here");
    } else {
      await page.waitForTimeout(3000); // the rest of the layer's loading, which must not include a shipped county's file
      check(
        "a shipped county is answered and lit from the layer's tiles, with no county boundary file downloaded",
        !!state && state.selected != null && boundaryFiles.length === 0,
        `state=${JSON.stringify(state)} files=${boundaryFiles.join(", ") || "none"}`
      );
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
        inHash: /(^|[#&])c=sb(&|$)/.test(location.hash),
      };
    });
    check(
      "a shared #pin= restores the pinned parent and stays in the hash (as c=)",
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
        inHash: /(^|[#&])c=/.test(location.hash),
      };
      btn.click();
      const afterRepin = {
        pressed: btn.getAttribute("aria-pressed") === "true",
        inHash: /(^|[#&])c=sb(&|$)/.test(location.hash),
      };
      return { afterUnpin, afterRepin };
    });
    check(
      "unpinning drops the pin from the hash and re-pinning puts it back",
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
        inHash: /(^|[#&])(c|pin)=/.test(location.hash),
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
  //     The hash is the whole assertion: the pin is emitted (as `c=`) only
  //     while its layer is on, so reading `c=cb` — county-board's permanent
  //     code — back proves the alias was applied AND the restore honoured it.
  //     The short keys `l=`/`c=` go through the same rewrite, which is what
  //     the NEXT consolidation needs (it appends the retired layer's code);
  //     a retired id typed into them stands in for that code here.
  for (const [why, hash] of [
    ["pin=", `#point=${POINT}&layers=commissioner&pin=commissioner`],
    ["c=", `#p=${POINT}&l=commissioner&c=commissioner`],
  ]) {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}${hash}`);
    await cardText(page, "county-board");
    const res = await page.evaluate(() => ({
      aliased: /(^|[#&])c=cb(&|$)/.test(location.hash),
      oldGone: location.hash.indexOf("commissioner") === -1,
      hash: location.hash,
    }));
    check(
      `an old permalink id in ${why} aliases with the layers`,
      res.aliased && res.oldGone,
      JSON.stringify(res)
    );
    await context.close();
  }

  // 2h2. A SHORT LINK OPENS THE SAME VIEW AS THE LONG ONE IT REPLACED. Since
  //     2026-10-09 the app writes `#p=…&l=…&c=…&z=…`, layers as their
  //     permanent codes, and every link written before that is still read.
  //     So this boots the LONG form, takes the short hash the app rewrote it
  //     into, boots THAT in a fresh page, and requires the two pages to agree
  //     on the point, the layers switched on, the pin and the zoom — read off
  //     the app's state, not off either string. A code the table does not
  //     know is dropped like an unknown id, never guessed at.
  {
    const long = `#point=${POINT}&layers=school-board,congress,ward&pin=school-board&zoom=14`;
    const view = async (hash) => {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}${hash}`);
      await cardText(page, "school-board");
      const got = await page.evaluate((n) => {
        const X = window[n];
        const pressed = document.querySelector('.pin-parent-btn[aria-pressed="true"]');
        return {
          hash: location.hash,
          point: X.state.selectedPoint && [+X.state.selectedPoint.lat.toFixed(5), +X.state.selectedPoint.lng.toFixed(5)],
          on: Object.keys(X.state.layersOn).filter((id) => X.state.layersOn[id]).sort(),
          pinned: !!pressed && !!document.getElementById("card-school-board").parentElement.contains(pressed),
          zoom: X.map.getZoom(),
        };
      }, EXPORTS_NAME);
      await context.close();
      return got;
    };
    const a = await view(long);
    const b = await view(a.hash);
    const same = (x, y) => JSON.stringify({ ...x, hash: 0 }) === JSON.stringify({ ...y, hash: 0 });
    check("a long link is rewritten into the short form",
      /^#p=41\.8825,-87\.6285&l=[a-z0-9,]+&c=sb&z=14$/.test(a.hash) && a.hash.length < long.length,
      `${long} -> ${a.hash}`);
    check("the short link opens exactly the view the long one did",
      same(a, b) && a.on.length === 3 && a.pinned && a.zoom === 14, JSON.stringify({ a, b }));
    const c = await view("#p=41.8825,-87.6285&l=sb,zz9&z=14");
    check("an unknown code in a short link is dropped, and the known ones still apply",
      c.on.join() === "school-board" && !/zz9/.test(c.hash), JSON.stringify(c));
  }

  // 2h3. A LINK NAMING CITY LAYERS AND NO POINT OPENS ON THE CITY. The map
  //     link on a question page names its layers and nothing else, and until
  //     2026-10-20 this app opened every such link on the whole state, where
  //     Chicago sits at or past the top edge of the map. The worksheet's
  //     `frames` now names the area a city or county layer answers in, and
  //     ENGINE permalink opens a link naming only such layers on their area.
  //     Read off the map, never off the hash: a Chicago-only link opens closer
  //     in than the bare app with all of Chicago in view and no `z=` written,
  //     and the link it is rewritten to opens the same way again; one that
  //     also names a statewide layer keeps the state view; and one carrying
  //     its own zoom keeps that zoom, centred on Chicago. The ward page's
  //     layers also answer in the suburbs, so its link names its area
  //     (`frame=chicago`): that opens on Chicago and stays in the rewritten
  //     hash until a point is selected, the same layers without it keep the
  //     state view, and an area this app does not declare is ignored.
  {
    const view = async (hash) => {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}${hash}`);
      const got = await page.evaluate((n) => {
        const m = window[n].map, c = m.getCenter();
        // the extent of the shipped school-board-districts.json, which is Chicago
        const city = window.L.latLngBounds([41.6443, -87.9401], [42.0231, -87.5237]);
        return { hash: location.hash, zoom: m.getZoom(), center: [c.lat, c.lng],
          cityInView: m.getBounds().contains(city) };
      }, EXPORTS_NAME);
      await context.close();
      return got;
    };
    const near = (x, y) => Math.abs(x.center[0] - y.center[0]) < 0.05 && Math.abs(x.center[1] - y.center[1]) < 0.05;
    const bare = await view("");
    const city = await view("#layers=school-board");
    check("a link naming only Chicago layers opens on Chicago",
      city.zoom > bare.zoom && city.cityInView && city.hash === "#l=sb",
      JSON.stringify({ bare, city }));
    const again = await view(city.hash);
    check("the link it is rewritten to opens the same way again",
      again.zoom === city.zoom && near(again, city) && again.hash === city.hash,
      JSON.stringify({ city, again }));
    const mixed = await view("#layers=school-board,congress");
    check("a link that also names a statewide layer keeps the state view",
      mixed.zoom === bare.zoom && near(mixed, bare), JSON.stringify({ bare, mixed }));
    const zoomed = await view("#layers=school-board&zoom=12");
    check("a link with its own zoom keeps it, centred on Chicago",
      zoomed.zoom === 12 && Math.abs(zoomed.center[0] - 41.834) < 0.05 &&
        Math.abs(zoomed.center[1] + 87.732) < 0.05 && zoomed.hash === "#l=sb&z=12",
      JSON.stringify(zoomed));
    const wardLayers = "#layers=ward,ward-precinct,county-precinct";
    const unnamed = await view(wardLayers);
    check("the ward page's layers alone keep the state view",
      unnamed.zoom === bare.zoom && near(unnamed, bare), JSON.stringify({ bare, unnamed }));
    const named = await view(wardLayers + "&frame=chicago");
    // The rewritten hash also names the parent layers the ward page's
    // sub-layers turn on, so it is read for the three it must carry.
    const namedCodes = (/^#l=([a-z0-9,]+)&f=chicago$/.exec(named.hash) || ["", ""])[1].split(",");
    check("a link naming its area opens on it and keeps it in the hash",
      named.zoom === city.zoom && near(named, city) && named.cityInView &&
        ["wd", "wp", "cp"].every((c) => namedCodes.includes(c)),
      JSON.stringify({ city, named }));
    const namedAgain = await view(named.hash);
    check("the link it is rewritten to opens on the area again",
      namedAgain.zoom === named.zoom && near(namedAgain, named) && namedAgain.hash === named.hash,
      JSON.stringify({ named, namedAgain }));
    const unknown = await view("#layers=school-board&frame=nowhere");
    check("an area this app does not declare is ignored and the layers decide",
      unknown.zoom === city.zoom && near(unknown, city) && unknown.hash === "#l=sb",
      JSON.stringify({ city, unknown }));
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}${named.hash}`);
      const hash = await page.evaluate((n) => {
        window[n].setSelectedPoint(41.8825, -87.6285);
        return location.hash;
      }, EXPORTS_NAME);
      await context.close();
      check("a selected point takes the area out of the hash",
        /^#p=41\.8825,-87\.6285&/.test(hash) && !/(^|&)f=/.test(hash), hash);
    }
  }

  // 2i. THE PANEL COUNT COUNTS WHAT THE SIDEBAR SHOWS. The results panel's
  //     "N of M layers on" counts top-level toggles only — a nested sub-layer
  //     (Township under County, Ward Precinct under City Ward) is not one of
  //     the M — and N was once activeLayerCount(), which counts sub-layers
  //     too, so every layer on at the Loop read "36 of 33 layers on". County
  //     and Township declare no coverage test, so both are relevant at any
  //     point with no network, which makes this pair the deterministic case.
  //     The expected figures are read off the sidebar a reader sees (visible
  //     top-level blocks, and the checked ones among them) rather than
  //     recomputed from the layer list, and the check refuses to pass unless
  //     the sub-layer is actually on and showing, so it cannot pass vacuously.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=county,township`);
    await page
      .waitForFunction(() => {
        const sub = document.getElementById("toggle-township");
        const stats = document.getElementById("districtry-stats");
        return sub && sub.checked && stats && /\d+ of \d+/.test(stats.textContent);
      }, null, { timeout: QUERY_TIMEOUT })
      .catch(() => {});
    const res = await page.evaluate(() => {
      const top = Array.from(document.querySelectorAll(".layer-block:not(.layer-block-sub)"))
        .filter((b) => !b.hidden);
      const on = top.filter((b) => {
        const cb = b.querySelector(":scope > .layer-block-head input[type=checkbox]");
        return cb && cb.checked;
      }).length;
      const sub = document.getElementById("toggle-township");
      const subBlock = sub && sub.closest(".layer-block");
      return {
        header: ((document.getElementById("districtry-stats") || {}).textContent || "").trim(),
        on,
        shown: top.length,
        subOn: !!(sub && sub.checked && subBlock && !subBlock.hidden),
      };
    });
    const m = /^(\d+) of (\d+) layers? on$/.exec(res.header);
    check(
      "the panel count counts top-level toggles only, never above its total",
      !!m && res.subOn && Number(m[1]) === res.on && Number(m[2]) === res.shown && Number(m[1]) <= Number(m[2]),
      JSON.stringify(res)
    );
    await context.close();
  }

  // 2j. THE SELECTED DISTRICT IS LIT FROM THE POINT ANSWER. A layer drawn
  //     from a live service answers its card from a small point query while
  //     the whole set is still downloading, and that answer carries the
  //     district's geometry; until 2026-09-26 the district stayed unlit until
  //     the whole set arrived, 15-22 s later on Slow 4G. Here every point
  //     query to the police-district service is answered from a fixture square
  //     around the Loop and every whole-set request is HELD, never answered, so
  //     the check can only pass if the card and the highlight come from the
  //     point answer alone — and it refuses to pass unless the whole set was in
  //     fact asked for and the layer's full drawing is in fact still absent.
  //     IT USED TO EXERCISE THE MUNICIPALITY LAYER, which since phase 6a
  //     (scripts/mirror_tiger_tiles.py) answers from its tile archive and asks
  //     the Census nothing on a first click, so the police districts, still
  //     live, carry the rule now.
  {
    const [plat, plng] = POINT.split(",").map(Number);
    const ring = [[plng - 0.01, plat - 0.01], [plng - 0.01, plat + 0.01], [plng + 0.01, plat + 0.01],
      [plng + 0.01, plat - 0.01], [plng - 0.01, plat - 0.01]];
    const fixture = { geometryType: "esriGeometryPolygon", features: [{
      attributes: { DIST_NUM: "1", DIST_LABEL: "1ST" },
      geometry: { rings: [ring] } }] };
    const context = await browser.newContext({ serviceWorkers: "block" });
    let held = 0, answered = 0;
    const page = await booted(context, `${BASE}#point=${POINT}&layers=police-district`, async (p) => {
      await p.route("**/Police_District_Boundary_View/**", (route) => {
        if (/esriGeometryPoint/.test(route.request().url())) {
          answered += 1;
          return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fixture) });
        }
        held += 1; // the whole set: left unanswered for the whole check
      });
    });
    await page
      .waitForFunction((ns) => {
        const s = window[ns].layerLoadState("police-district");
        return s && s.card === "result" && s.highlight;
      }, EXPORTS_NAME, { timeout: QUERY_TIMEOUT })
      .catch(() => {});
    const res = await page.evaluate((ns) => window[ns].layerLoadState("police-district"), EXPORTS_NAME);
    check(
      "a point query's district is lit before its layer's whole set arrives",
      !!res && res.card === "result" && res.highlight && !res.overlay && held > 0 && answered > 0,
      JSON.stringify({ ...res, statewide_held: held, point_answered: answered })
    );
    await context.close();
  }

  // 2k. A FIRST VISIT INSTALLS NO BOUNDARY FILE. Until 2026-09-26 the service
  //     worker's install handler fetched every file in GEOMETRY_URLS — 296 of
  //     them for this app, 4.3 MB gzipped — while the reader's first cards
  //     loaded. It now installs the shell and caches a boundary file the first
  //     time a layer uses it. This is the one check here that ALLOWS the
  //     worker, and it holds that every data/app file the worker fetched is
  //     one the page itself asked for, so a boot fetch passing through the
  //     worker is allowed and an install-time fetch of the whole list is not.
  //     It refuses to pass unless the worker took control of the page and was
  //     seen fetching something, so it cannot pass with the worker's requests
  //     simply invisible.
  {
    const context = await browser.newContext();
    const byWorker = [], byPage = new Set();
    context.on("request", (r) => {
      const path = new URL(r.url()).pathname;
      if (r.serviceWorker()) byWorker.push(path);
      else if (/\/data\/app\//.test(path)) byPage.add(path);
    });
    const page = await booted(context, BASE);
    const controlled = await page
      .waitForFunction(() => !!(navigator.serviceWorker && navigator.serviceWorker.controller), null, { timeout: QUERY_TIMEOUT })
      .then(() => true, () => false);
    await page.waitForTimeout(3000);
    const installed = byWorker.filter((p) => /\/data\/app\//.test(p) && !byPage.has(p));
    check(
      "a first visit's service worker fetches no boundary file the page did not ask for",
      controlled && byWorker.length > 0 && installed.length === 0,
      JSON.stringify({ controlled, worker_requests: byWorker.length, unrequested_data_files: installed.length, first: installed.slice(0, 3) })
    );
    await context.close();
  }

  // 2l. A REPEAT VISIT DOWNLOADS NO BOUNDARY FILE IT ALREADY HAS. Until
  //     2026-09-26 the worker served a cached boundary file and fetched it
  //     again in the background on every hit, so a returning visitor paid the
  //     full download of every layer they opened on every visit. It now serves
  //     the cached copy alone; a changed file reaches them through a
  //     CACHE_NAME bump, which check_cache_version.py enforces. The first load
  //     runs before the worker takes control, so the files are cached on the
  //     second and counted on the third, and the cards must still answer.
  {
    const layers = ["school-board", "ccbr", "il-supreme-court"];
    const context = await browser.newContext();
    // Once the worker controls the page, a request it lets through reaches
    // the network from the worker, where a page-level route (booted()'s) does
    // not see it; the vendored libraries have to be routed on the context.
    if (VENDORED_LEAFLET) {
      await context.route("**/cdnjs.cloudflare.com/**/leaflet.js", (r) =>
        r.fulfill({ status: 200, contentType: "application/javascript", body: VENDORED_LEAFLET.js }));
      await context.route("**/cdnjs.cloudflare.com/**/leaflet.css", (r) =>
        r.fulfill({ status: 200, contentType: "text/css", body: VENDORED_LEAFLET.css }));
    }
    if (VENDORED_MAPLIBRE) {
      await context.route("**/cdnjs.cloudflare.com/**/maplibre-gl.min.js", (r) =>
        r.fulfill({ status: 200, contentType: "application/javascript", body: VENDORED_MAPLIBRE.js }));
    }
    let counting = false;
    const refetched = [];
    context.on("request", (r) => {
      const path = new URL(r.url()).pathname;
      // a boundary file, or a byte range of a tile archive: these three
      // layers are drawn from tiles since phase 5, so their ranges are what
      // a returning visitor would otherwise download again
      if (counting && r.serviceWorker() && /\/data\/app\/([^/]*districts\.json|tiles\/[^/]+\.pmtiles)$/.test(path)) refetched.push(path + (r.headers().range ? " " + r.headers().range : ""));
    });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=${layers.join(",")}`);
    const controlled = await page
      .waitForFunction(() => !!(navigator.serviceWorker && navigator.serviceWorker.controller), null, { timeout: QUERY_TIMEOUT })
      .then(() => true, () => false);
    const settled = () => page.waitForFunction(
      (a) => !!window[a.ns] && a.ids.every((id) => { const s = window[a.ns].layerLoadState(id); return s && s.card === "result" && s.overlay; }),
      { ids: layers, ns: EXPORTS_NAME }, { timeout: QUERY_TIMEOUT }
    ).then(() => true, () => false);
    await page.reload({ waitUntil: "domcontentloaded" });
    const cachedOk = await settled();
    counting = true;
    await page.reload({ waitUntil: "domcontentloaded" });
    const repeatOk = await settled();
    await page.waitForTimeout(1500);
    check(
      "a repeat visit's service worker fetches no boundary file it already cached",
      controlled && cachedOk && repeatOk && refetched.length === 0,
      JSON.stringify({ controlled, cachedOk, repeatOk, refetched })
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
      // the file AND the tile archive it is drawn from since phase 5: a card
      // whose tile read fails falls back to the file, so both must be down
      async (p) => {
        await p.route("**/data/app/school-board-districts.json", (r) => r.fulfill({ status: 503, body: "down" }));
        await p.route("**/data/app/tiles/school-board.pmtiles", (r) => r.fulfill({ status: 503, body: "down" }));
      }
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
      async (p) => {
        await p.route("**/data/app/school-board-districts.json", (r) => r.fulfill({ status: 503, body: "down" }));
        await p.route("**/data/app/tiles/school-board.pmtiles", (r) => r.fulfill({ status: 503, body: "down" }));
      }
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

  // 1i2. A CARD'S DISTRICT PILL IS LEGIBLE IN A PAGE THAT BOOTS DARK. Two
  //      defects read "IL-7" at 1.1:1 on a dark card (2026-10-13): the cards
  //      were built before the dark palette's getters were installed, so a page
  //      that booted dark kept every card's LIGHT colour (#14181C for the House)
  //      until the theme was flipped; and the pill painted the layer colour
  //      itself as text. validate_contrast.py measures the pill's mix for every
  //      layer colour statically; this is the half only a browser can see — the
  //      accent a card actually carries after a dark boot, and the ratio the
  //      browser actually paints.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=41.88250,-87.62850&layers=congress`, async (p) => {
      await p.addInitScript(() => { try { localStorage.setItem("districtry-theme", "dark"); } catch (e) {} });
    });
    const pill = await page.waitForFunction(() => {
      const cb = document.getElementById("toggle-congress");
      const block = cb && cb.closest(".layer-block");
      const el = block && block.querySelector(".card-id-pill");
      if (!el || el.hidden || !el.textContent.trim()) return null;
      const rgb = (v) => {
        const m = v.match(/^color\(srgb ([\d.e-]+) ([\d.e-]+) ([\d.e-]+)(?: \/ ([\d.e-]+))?\)$/);
        if (m) return [+m[1] * 255, +m[2] * 255, +m[3] * 255, m[4] === undefined ? 1 : +m[4]];
        const n = v.match(/[\d.]+/g).map(Number);
        return [n[0], n[1], n[2], n.length > 3 ? n[3] : 1];
      };
      const lum = (c) => {
        const f = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
        return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
      };
      const text = rgb(getComputedStyle(el).color);
      const tint = rgb(getComputedStyle(el).backgroundColor);
      const head = rgb(getComputedStyle(el.parentElement).backgroundColor);
      const ground = [0, 1, 2].map((i) => tint[i] * tint[3] + head[i] * (1 - tint[3]));
      const a = lum(text), b = lum(ground);
      return { text: el.textContent.trim(), theme: document.documentElement.getAttribute("data-theme"),
               accent: block.style.getPropertyValue("--layer-accent").trim().toUpperCase(),
               ratio: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) };
    }, null, { timeout: QUERY_TIMEOUT }).then((h) => h.jsonValue(), () => null);
    check("a page that boots dark gives its cards the dark layer colour, not the light one",
      !!pill && pill.theme === "dark" && !!pill.accent && pill.accent !== "#14181C", JSON.stringify(pill));
    check("the U.S. House card's district pill reads at 4.5:1 or better on a dark card",
      !!pill && pill.ratio >= 4.5, JSON.stringify(pill));
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
    const read = () => page.evaluate(({ n }) => {
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
      };
    }, { n: EXPORTS_NAME });

    // A NULL READ IS A FAILURE TO MEASURE, NOT A PASS (2026-09-27). The overlay
    // assertion below used to short-circuit on either side being null, so a run
    // where the anchor's overlay had not painted PASSED without comparing
    // anything — a gate that can only be vacuous, which is the shape this
    // project keeps finding. `overlayColor` returns null three ways: the layer
    // has no overlay yet, it is drawn from tiles and the GL line layer is not
    // built, or its Leaflet path carries no colour; all three mean this check
    // learned nothing. So each side is POLLED to a bound instead of sampled
    // after a fixed sleep, and a side that never answers FAILS naming which.
    // The old SVG-path fallback is gone with it: `overlayColor` is an engine
    // export in every instance, and reading `#map path` is what let the same
    // assertion in ca/ measure the scope mask instead of a district (fixed
    // there in #1234) — dead code that can answer wrongly is not free.
    // MEASURED on this instance over five boots: the light colour first reads
    // non-null at 6-302 ms and the dark repaint lands 2-81 ms after the flip,
    // so QUERY_TIMEOUT is slack rather than tight. It is the bound because it
    // is already tuned for a cold CI runner, where MapLibre comes from the CDN
    // and the anchor is a PMTiles archive. Polling for a dark value that
    // DIFFERS is deliberate: waiting only for non-null samples the race and
    // reads the light colour straight back.
    // A THROW IS ALSO A FAILURE TO MEASURE. This script is one try/finally with
    // no catch, so an exception exits with a stack instead of naming a check —
    // and the poll below asks the page up to QUERY_TIMEOUT/50 times where the
    // old code asked twice. An `overlayColor` that throws is a finding about
    // the app, so it is reported as THIS check failing, with the message.
    let overlayError = null;
    const overlay = () => page.evaluate(({ n, id }) =>
      (window[n] && window[n].overlayColor ? window[n].overlayColor(id) : null),
      { n: EXPORTS_NAME, id: OFFLINE[0] })
      .catch((e) => { overlayError = String((e && e.message) || e).split("\n")[0]; return null; });
    const settleOverlay = async (want) => {
      const t0 = Date.now();
      for (;;) {
        const v = await overlay();
        if (want(v)) return v;
        if (Date.now() - t0 > QUERY_TIMEOUT) return v;
        await page.waitForTimeout(50);
      }
    };

    await page.evaluate((n) => window[n].setTheme("light", false), EXPORTS_NAME);
    await page.waitForTimeout(400);
    const light = await read();
    const lightStroke = await settleOverlay((v) => v !== null);
    await page.evaluate((n) => window[n].setTheme("dark", false), EXPORTS_NAME);
    await page.waitForTimeout(600);
    const dark = await read();
    const darkStroke = await settleOverlay((v) => v !== null && v !== lightStroke);

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
      lightStroke !== null && darkStroke !== null && lightStroke !== darkStroke,
      lightStroke === null
        ? `${OFFLINE[0]} never reported an overlay colour in ${QUERY_TIMEOUT} ms — nothing was measured` +
          (overlayError ? ` (overlayColor threw: ${overlayError})` : "")
        : darkStroke === null
          ? `${lightStroke} -> null: the overlay stopped reporting a colour after the flip`
          : lightStroke === darkStroke
            ? `${lightStroke} unchanged by the flip`
            : `${lightStroke} -> ${darkStroke}`);

    // THE BASEMAP'S LABELS DRAW ABOVE THE DISTRICTS (2026-09-25): the style
    // is split into a ground map in the tile pane and a label-only map in a
    // pane above the overlays. The split and the street-name restyle are
    // held to a fixture through the exported function, so no CARTO fetch is
    // needed; the pane is checked only where the vector basemap booted.
    const split = await page.evaluate((n) => {
      const fx = { version: 8, sources: {}, layers: [
        { id: "water", type: "fill" },
        { id: "place_town", type: "symbol", layout: { "text-size": 12 } },
        { id: "roadname_minor", type: "symbol", minzoom: 16,
          layout: { "text-size": 9, "text-font": ["Montserrat Regular", "Open Sans Regular"] },
          paint: { "text-color": "#838383" } },
        { id: "roadname_major", type: "symbol", minzoom: 13,
          layout: { "text-size": { stops: [[14, 10], [18, 12]] } }, paint: { "text-color": "#383838" } },
      ] };
      const f = window[n].splitBaseStyle;
      const ground = f(fx, "ground", false), labels = f(fx, "labels", false), dark = f(fx, "labels", true);
      const byId = (st, id) => st.layers.find((l) => l.id === id);
      const pane = document.querySelector(".leaflet-dstBaseLabels-pane");
      const over = document.querySelector(".leaflet-overlay-pane");
      return {
        ground: ground.layers.map((l) => l.id).join(),
        labels: labels.layers.map((l) => l.id).join(),
        minor: byId(labels, "roadname_minor"),
        major: byId(labels, "roadname_major"),
        darkMajor: byId(dark, "roadname_major").paint["text-color"],
        fixtureUntouched: fx.layers[2].minzoom === 16 && fx.layers[2].paint["text-color"] === "#838383" &&
          !fx.sources.boundary_streets,
        boundarySource: !!(labels.sources.boundary_streets && labels.sources.boundary_streets.type === "geojson"),
        // the stretch blocker sits just above the ordinary road names, takes
        // up room and draws nothing
        blockInvisible: (function (b) {
          return !!b && b.paint["text-opacity"] === 0 && b.layout["text-allow-overlap"] === true &&
            b.source === "boundary_streets";
        })(byId(labels, "boundary_streets_block")),
        vector: window[n].basemap().vector, labelMap: window[n].basemap().labels,
        paneAbove: !!(pane && over && Number(getComputedStyle(pane).zIndex) > Number(getComputedStyle(over).zIndex)),
      };
    }, EXPORTS_NAME);
    check("the basemap splits into a ground map and a label map above it",
      split.ground === "water" && split.labels === "place_town,roadname_minor,roadname_major,boundary_streets_block,boundary_streets" &&
      split.boundarySource && split.fixtureUntouched && split.blockInvisible,
      `ground=${split.ground} labels=${split.labels}`);
    check("street names are darker, a point larger and named one zoom sooner",
      split.minor.minzoom === 15 && split.minor.layout["text-size"] === 10 &&
      split.minor.layout["text-font"][0] === "Montserrat Medium" && split.minor.paint["text-color"] === "#3a3f4b" &&
      split.major.minzoom === 13 && JSON.stringify(split.major.layout["text-size"].stops) === "[[14,11],[18,13]]" &&
      split.darkMajor === "#e6e4ee",
      JSON.stringify({ minor: split.minor, darkMajor: split.darkMajor }).slice(0, 160));
    check("the label map sits in a pane above the district overlays",
      !split.vector || (split.labelMap && split.paneAbove),
      `vector=${split.vector} labelMap=${split.labelMap} above=${split.paneAbove}`);

    // The hover card never takes the mouse and carries no tail. It follows
    // the cursor and, near the top of the map, flips below it; its tail then
    // pointed up at exactly the cursor, and Leaflet's own stylesheet gives
    // that tail pointer-events: auto, so it took the click the map was meant
    // to get. Built from the real class names under the real stylesheets
    // (Leaflet's included), every part of the card must compute to none and
    // the tail must not display, in both placements.
    const hoverPE = await page.evaluate(() => {
      const out = [];
      ["", " hover-below"].forEach((flip) => {
        const pop = document.createElement("div");
        pop.className = "leaflet-popup hover-popup" + flip;
        pop.innerHTML = '<div class="leaflet-popup-content-wrapper"><div class="leaflet-popup-content">' +
          '<div class="hover-snapshot"><div class="hover-row">x</div></div></div></div>' +
          '<div class="leaflet-popup-tip-container"><div class="leaflet-popup-tip"></div></div>';
        document.querySelector(".leaflet-popup-pane").appendChild(pop);
        [pop].concat([].slice.call(pop.querySelectorAll("*"))).forEach((el) => {
          const pe = getComputedStyle(el).pointerEvents;
          if (pe !== "none") out.push(el.className + flip + "=" + pe);
        });
        // the card carries no tail at all (2026-09-25)
        const tail = getComputedStyle(pop.querySelector(".leaflet-popup-tip-container")).display;
        if (tail !== "none") out.push("tail" + flip + " display=" + tail);
        pop.remove();
      });
      return out;
    });
    check("the hover card has no tail and never takes the mouse from the map",
      hoverPE.length === 0, hoverPE.join(", ") || "every part none");

    // Boundary streets: the matcher names a street the district's edge runs
    // along, and not one that crosses the edge or runs a block away; the
    // stretch it labels ends near where the edge leaves the street. Held to
    // a fixture — a square district of about 830 x 1,110 m — so the answer
    // does not depend on CARTO's tiles or any district source.
    const bs = await page.evaluate((n) => {
      const sq = { type: "Polygon", coordinates: [[[-87.70, 41.90], [-87.69, 41.90], [-87.69, 41.91], [-87.70, 41.91], [-87.70, 41.90]]] };
      const road = (name, coords) => ({ type: "Feature", properties: { name }, geometry: { type: "LineString", coordinates: coords } });
      const roads = [
        road("Edge St", [[-87.69988, 41.899], [-87.69988, 41.911]]),     // 10 m inside the west edge
        road("Cross St", [[-87.705, 41.905], [-87.695, 41.905]]),        // crosses the west edge
        road("Near St", [[-87.69819, 41.899], [-87.69819, 41.911]]),     // 150 m inside it
        road("Long St", [[-87.70, 41.90009], [-87.60, 41.90009]]),       // along the south edge, then 7 km past it
        road("Tiny St", [[-87.6980, 41.91005], [-87.6973, 41.91005]]),   // 60 m along the north edge
      ];
      const r = window[n].matchBoundaryStreets(roads, [{ color: "#123456", geometry: sq }],
        { lat: 41.905, zoom: 15, bbox: [-87.72, 41.89, -87.58, 41.92] });
      const longEast = Math.max.apply(null, r.features.filter((f) => f.properties.name === "Long St")
        .map((f) => Math.max.apply(null, f.geometry.coordinates.map((c) => c[0]))));
      const bsNow = window[n].boundaryStreets();
      const ab = window[n].abbreviateStreetName;
      const abbrev = ["West North Avenue", "North Avenue", "North Broadway", "Avenue A", "Lake Shore Drive North", "Dearborn Street Bikeway"]
        .map((s) => ab(s)).join("|");
      return { names: Object.keys(r.names).sort().join(), color: r.names["Edge St"], longEast,
               allNamed: r.features.every((f) => f.properties.name && f.properties.color === "#123456"),
               edgeLabel: (r.features.find((f) => f.properties.name === "Edge St") || { properties: {} }).properties.label,
               abbrev,
               on: bsNow.on, available: bsNow.available,
               button: !!document.getElementById("boundary-streets-toggle") };
    }, EXPORTS_NAME);
    check("boundary streets: a street along the edge is named, one crossing it or a block away is not",
      bs.names === "Edge St,Long St" && bs.color === "#123456" && bs.allNamed,
      `names=${bs.names} color=${bs.color}`);
    check("boundary streets: labels print USPS abbreviations, never shortening a name to its type",
      bs.abbrev === "W North Ave|North Ave|N Broadway|Avenue A|Lake Shore Dr N|Dearborn Street Bikeway" &&
      bs.edgeLabel === "Edge St", `${bs.abbrev} edge=${bs.edgeLabel}`);
    check("boundary streets: the labelled stretch ends near where the edge leaves the street",
      bs.longEast > -87.69 && bs.longEast < -87.686, `east end ${bs.longEast}`);
    check("boundary streets: the toggle exists exactly where the vector labels do",
      bs.available === !!split.labelMap && bs.button === bs.available && bs.on === true,
      `available=${bs.available} button=${bs.button} on=${bs.on}`);
    if (bs.button) {
      const off = await page.evaluate((n) => {
        document.getElementById("boundary-streets-toggle").click();
        const r = window[n].boundaryStreets();
        const btn = document.getElementById("boundary-streets-toggle");
        const out = { on: r.on, names: Object.keys(r.names).length, pressed: btn.getAttribute("aria-pressed"),
                      stored: (() => { try { return localStorage.getItem("districtry-boundary-streets"); } catch (e) { return "?"; } })() };
        btn.click();
        return out;
      }, EXPORTS_NAME);
      check("boundary streets: switching it off clears the names and is remembered",
        off.on === false && off.names === 0 && off.pressed === "false" && off.stored === "off",
        JSON.stringify(off));
    }

    // Boundary streets on REAL tiles: what the label map renders, counted
    // label by label along every stretch on screen (the app's own
    // boundaryStreetLabels walks each stretch every 4 px and asks the label
    // map what is drawn there). A matched street must print its name in the
    // district's colour and never ALSO in the ordinary grey inside that
    // stretch: the two layers place labels at different points along one
    // road and do not collide, which printed both until the invisible
    // stretch blocker (2026-09-25). The fixture above cannot see this; only
    // placed labels can. Needs CARTO's tiles and WebGL, so it is skipped,
    // and says so, where either is missing. It is the one check that fetches
    // the real basemap (scripts/basemap_stub.mjs says why every other check
    // gets a stand-in), so it opens a context of its own that routes nothing.
    if (bs.button) {
      const liveContext = await realBasemapContext(browser, { serviceWorkers: "block" });
      const live = await booted(liveContext, `${BASE}#point=41.9505,-87.7210&layers=il-house,il-senate&zoom=16`);
      const got = await live.waitForFunction((n) => window[n] && window[n].boundaryStreets &&
        Object.keys(window[n].boundaryStreets().names).length > 0, EXPORTS_NAME, { timeout: QUERY_TIMEOUT })
        .then(() => true).catch(() => false);
      if (!got) {
        console.log("  SKIP  boundary streets on real tiles — no street matched (CARTO's tiles did not arrive)");
      } else {
        await live.waitForTimeout(3000);
        const m = await live.evaluate((n) => window[n].boundaryStreetLabels(), EXPORTS_NAME);
        const rows = Object.keys(m || {}).map((k) => ({ name: k, ...m[k] }));
        const coloured = rows.reduce((a, r) => a + r.coloured, 0);
        const doubled = rows.filter((r) => r.ordinary > 0);
        check("boundary streets on real tiles: matched streets render their coloured labels",
          coloured > 0, `${coloured} coloured labels across ${rows.length} streets`);
        check("boundary streets on real tiles: no matched street also prints its grey name inside its stretch",
          doubled.length === 0,
          doubled.length ? doubled.map((r) => `${r.name} (${r.ordinary} grey, ${r.coloured} coloured)`).join("; ")
            : rows.map((r) => `${r.name.replace(/^(North|South|East|West) /, "")} ${r.coloured}`).join(", "));
        // A theme flip replaces the label map's style, and until 2026-09-26
        // the new style's stretches source started empty and stayed empty
        // until the map next moved: every coloured name vanished on the flip.
        await live.evaluate((n) => window[n].setTheme("dark", false), EXPORTS_NAME);
        await live.waitForTimeout(5000);
        const md = await live.evaluate((n) => window[n].boundaryStreetLabels(), EXPORTS_NAME);
        const drows = Object.keys(md || {}).map((k) => ({ name: k, ...md[k] }));
        const dcol = drows.reduce((a, r) => a + r.coloured, 0);
        const ddoubled = drows.filter((r) => r.ordinary > 0);
        check("boundary streets on real tiles: the coloured names survive a theme flip, still without a grey copy",
          dcol > 0 && ddoubled.length === 0,
          `${dcol} coloured labels after the flip (${coloured} before)` +
            (ddoubled.length ? "; doubled: " + ddoubled.map((r) => r.name).join(", ") : ""));
      }
      await liveContext.close();
    }
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
  // ---- 1x. The Tribal Government card names the nation, where its government
  // sits and why it names no council member. THIS CHECK EXISTS BECAUSE THE
  // FIRST BUILD OF THIS LAYER SHIPPED FOUR SILENT ABSENCES and every static
  // gate passed: `findPropCI` lowercases the property key and compares it to
  // the candidate exactly as given, so the camelCase `keys` this layer was
  // registered with matched nothing and the Land, Districts, Population and
  // "Why no names" rows rendered as nothing at all. The card's claims are
  // asserted in a browser for that reason. The point is
  // shapely's representative point for the shipped parcel, verified interior
  // against the file's own even-odd reading (2026-10-01), and the assertions
  // are on the WORDING and on the nation/land distinction — the Census's text
  // for this parcel describes a piece of land, not the name of a government.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(
      context, `${BASE}#point=41.75560,-88.84957&layers=tribal-government`);
    const card = await cardText(page, "tribal-government");
    const fields = await page.$$eval("#card-tribal-government .card-field",
      (els) => els.map((e) => ({
        label: ((e.querySelector(".card-field-label") || {}).textContent || "").trim(),
        value: ((e.querySelector(".card-field-value") || {}).textContent || "").trim()
      })));
    const by = (l) => (fields.find((f) => f.label === l) || {}).value || "";
    const nation = by("Tribal government") === "Prairie Band Potawatomi Nation";
    const land = by("Land").indexOf("Off-Reservation Trust Land") !== -1;
    const seat = by("Seat of government") === "Mayetta, KS";
    // Since 2026-10-10 the card names the nation's council, read from its
    // own page and merged onto the land from tribal-councils.json by the
    // loader. The "Why no names" row must be gone, the council block must
    // carry the chairperson, and the dated note must say where the names
    // came from.
    const noWhy = by("Why no names") === "";
    const council = card.text.indexOf("Council") !== -1
      && card.text.indexOf("Rupnick") !== -1
      && card.text.indexOf("From the nation's own council page") !== -1;
    const ok = nation && land && seat && noWhy && council;
    check("the Tribal Government card names the nation, its Kansas seat and its council",
          ok, `nation=${JSON.stringify(by("Tribal government"))} land=${land} ` +
              `seat=${JSON.stringify(by("Seat of government"))} noWhy=${noWhy} ` +
              `council=${council}`);

    // and a point off tribal land says so in the layer's own words rather than
    // the generic "not inside any district", which reads as a lookup that
    // failed instead of a fact about the place
    const page2 = await booted(
      context, `${BASE}#point=${POINT}&layers=tribal-government`);
    const off = await cardText(page2, "tribal-government");
    const offOk = off.text.indexOf("not on tribal land") !== -1;
    check("a point off tribal land is told so in the layer's own words",
          offOk, JSON.stringify(off.text.slice(0, 120)));
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
