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
const POINT = "35.78040,-78.63910"; // the State Capitol block, downtown Raleigh, Wake County
const OFFLINE = ["county", "us-house", "nc-senate", "nc-house", "voting-precinct"];
const EXPECT_DISTRICT = { "county": "Wake County", "us-house": "2", "nc-senate": "14", "nc-house": "38", "voting-precinct": "Precinct 01-14" };
const NEGATIVE_POINT = "35.60000,-75.30000"; // the open Atlantic east of Hatteras Island — outside every North Carolina county, measured 2026-09-29. IT HAS TO BE THE OCEAN: the TIGER county fabric is water-inclusive for the inland sounds, so Pamlico Sound is Hyde County and Albemarle Sound is Tyrrell, and a point picked off a map inside either would make this assertion vacuous. Inside permalink_gate's maxLng (-75.10) so the point is still selectable.
const APP_NAME = "districtry North Carolina";
const EXPECT_LAYERS = 15;
// ==== GENERATED:END smoke-config ====
// Fork-specific smoke-test constants (the reference repo hoists its own set
// here). The template's CHI-scenario checks are dropped at build time, so the
// GAP_PROBE / MOVE_POINT / STRAGGLER_* names below are contract stubs — the
// span's consumers keep the names resolvable; grow real fixtures (and restore
// the corresponding checks from the reference repo's smoke_test.mjs) as this
// fork ships the layers they exercise.
const EXPORTS_NAME = "NCExplorer";
const PORTAL_HOST = "data.invalid"; // must stay a non-empty hostname: an empty string would abort every request
// Geocoder type-ahead fixture: RAW carries an embedded unit the app's cleaner
// must strip to CLEANED; the Photon STUB answers only CLEANED, so the check
// proves the strip-and-retry path with no live network.
const GEOCODER_QUERY_RAW = "16 W Jones St Suite 200, Capital City";
const GEOCODER_UNIT_FRAGMENT = "Suite 200";
const GEOCODER_QUERY_CLEANED = "16 W Jones St, Capital City";
const GEOCODER_STUB_FEATURE = {
  type: "Feature",
  geometry: { type: "Point", coordinates: [-78.6391, 35.7804] },
  properties: {
    housenumber: "100",
    street: "W Jones St",
    city: "Capital City",
    state: "North Carolina",
    postcode: "00000"
  }
};
// Contract stubs (their consuming checks are reference-fork scenarios,
// dropped from this template's body):
const GAP_PROBE = { county: "statewide", label: "Statewide", lat: 35.7804, lng: -78.6391 };
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

  // 1a2. A SELECTION GOES TO THE APP THAT ANSWERS THERE, decided by state
  //     outlines (ENGINE metro-portal + the root fleet-outlines.json) rather
  //     than by rectangles. The sibling apps are stubbed so a wrong route
  //     cannot leave for the real site — unstubbed, a wrong route navigates to
  //     the real districtry.com, fails in the sandbox and leaves page.url() on
  //     the app, which reads exactly like correct behaviour.
  //
  //     NORTH CAROLINA'S OWN CASE IS THE ONE BELOW THAT MATTERS, and it is the
  //     absence half: a point just over the state line where no instance
  //     answers must be selected HERE, where the app says nothing answers
  //     there, rather than handed to an app with nothing to show. This app
  //     answers its own side from the coverage rings the wash retained, with no
  //     fetch; the positive cases prove fleet-outlines.json is still read for
  //     somebody else's ground.
  //
  //     COLUMBIA, SOUTH CAROLINA WAS THE UNCOVERED CASE UNTIL SOUTH CAROLINA
  //     WENT LIVE (2026-10-13), and publishing it put Columbia inside
  //     fleet-outlines.json, so the same click now opens /sc/. It moved to the
  //     positive cases in that change, the Kentucky go-live lesson run again:
  //     a fixed point in a neighbour stops meaning "uncovered" the day that
  //     neighbour publishes.
  {
    const cases = [
      { name: "Chicago", lat: 41.8825, lng: -87.6285, want: "https://districtry.com/il/" },
      { name: "Milwaukee", lat: 43.04, lng: -87.91, want: "https://districtry.com/wi/" },
      { name: "Columbia, South Carolina", lat: 34.0007, lng: -81.0348, want: "https://districtry.com/sc/" },
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
      check(`a click on ${c.name} from North Carolina opens ${c.want} with the point`, !!went, went || page.url());
      await context.close();
    }
  }

  // 1a2-ii. The half that keeps 1a2 honest: Danville, Virginia, about 5 km
  //     north of the state line, where no districtry instance answers, so the
  //     click must stay HERE. A route to a sibling would be the same lie
  //     pointing the other way, and the stub makes it visible: if the app
  //     navigated, the URL would be the stubbed sibling rather than this app.
  //
  //     Measured 2026-10-13: TIGERweb's state layer names Virginia at this
  //     point (controls: Raleigh returns North Carolina and Columbia South
  //     Carolina), and no outline in fleet-outlines.json contains it. VIRGINIA
  //     BECAUSE NO INSTANCE SERVES IT OR IS BEING BUILT FOR IT, where
  //     Tennessee is next to go live. It is inside the worksheet's
  //     permalink_gate (maxLat 36.75), so the click is handled.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, BASE, async (p) => {
      await p.route("https://districtry.com/**", (route) =>
        route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>sibling</title>" }));
    });
    await page.evaluate(({ n }) => {
      window[n].map.fire("click", { latlng: window.L.latLng(36.586, -79.395) });
    }, { n: EXPORTS_NAME });
    await page.waitForTimeout(3000);
    const url = page.url();
    // Any sibling, not a list of them: a list goes stale the day a state
    // publishes, which is exactly how Columbia stopped meaning "uncovered".
    check("a click on Danville, Virginia stays in this app",
      !/districtry\.com\//.test(url), url);
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


  // 2c. The County card names the supervisors of the county's soil and water
  //     conservation district from the state's District Directory
  //     (nc-conservation-boards.json, keyed by county GEOID; a same-origin
  //     file, so no stub). What is asserted: every name the file gives for
  //     the county is on the card, with the district's name and the sentence
  //     saying how a board is chosen; at Pasquotank, one of the five counties
  //     of the Albemarle district, the card says the district covers several
  //     counties; and at Person, where the directory lists a seat with no
  //     name, the card says so and never calls the seat vacant.
  for (const c of [
    { point: POINT, geoid: "37183", label: "Wake", want: [], reject: [] },
    { point: "36.29460,-76.25110", geoid: "37139", label: "Pasquotank",
      want: [/Covers several counties/, /covers Camden, Chowan, Currituck, Pasquotank and Perquimans counties/],
      reject: [] },
    { point: "36.39380,-78.98280", geoid: "37145", label: "Person",
      want: [/No name listed/], reject: [/\bVacant\b/] }
  ]) {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${c.point}&layers=county`);
    const boards = await page.evaluate(() =>
      fetch("data/app/nc-conservation-boards.json").then((r) => r.json()));
    const districts = (boards[c.geoid] || {}).districts || [];
    const names = [].concat(...districts.map((d) =>
      (d.members || []).filter((m) => m.name).map((m) => m.name)));
    const info = await cardText(page, "county");
    const text = info.text || "";
    const want = [/three elected by the county's voters without party labels/,
      /two appointed by the state Soil and Water Conservation Commission/].concat(c.want);
    const missingNames = names.filter((n) => !text.includes(n));
    // a section label is drawn in capitals, which innerText reports, so the
    // district's name is matched without regard to case
    const lower = text.toLowerCase();
    const missingDistricts = districts.map((d) => d.name).filter((n) => !lower.includes(n.toLowerCase()));
    const missing = want.filter((re) => !re.test(text));
    // the conservation section alone, so a vacancy elsewhere on the card
    // (the county board's own roster) cannot satisfy or fail its tests
    const end = "North Carolina district directory (PDF)";
    const from = districts.length ? lower.indexOf(districts[0].name.toLowerCase()) : -1;
    const section = from >= 0 ? text.slice(from, text.lastIndexOf(end) + end.length) : "";
    const present = c.reject.filter((re) => re.test(section));
    check(`county names ${c.label} County's conservation district supervisors from the directory`,
      !info.error && names.length >= 3 && !missingNames.length && !missingDistricts.length &&
        !missing.length && !present.length,
      `names ${names.length}; missing names: ${missingNames.join(", ") || "none"}; ` +
        `missing districts: ${missingDistricts.join(", ") || "none"}; missing text: ${missing.join(", ") || "none"}; ` +
        `unwanted: ${present.join(", ") || "none"}`);
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
  //    fire-station is 2,838 points against a 2,000-record cap the service
  //    reports as HTTP 200 + exceededTransferLimit rather than an error, so a
  //    single request drops 838 real stations and the nearest-3 card looks
  //    correct at every point. That was proven by hand when the layer shipped
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
      attributes: { NAME: `FAR STATION ${i}`, ADDRESS: "1 Far Rd", CITY: "Charlotte", STATE: "NC", ZIPCODE: "28202" },
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
                              CITY: "Raleigh", STATE: "NC", ZIPCODE: "27601" },
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
      /Raleigh, NC/.test(text), text.slice(0, 140));
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
  //    SINCE 2026-10-17 THESE LAYERS ARE ANSWERED FROM SAME-ORIGIN TILE
  //    ARCHIVES, and the stubs stay anyway: several cases below exist in no
  //    archive (an affix no table carries, an inactive municipality), so
  //    each case refuses its layer's archive and the stub decides the card.
  //
  //    WHAT IS ACTUALLY WORTH TESTING IS THIS INSTANCE'S OWN CODE, and none of
  //    it is exercised by a live fetch that happens to work. Three claims, each
  //    written for North Carolina and each wrong in a way a reader would see:
  //
  //    (a) `subdivisionKind` reads the type off what TIGER's NAME carries
  //        beyond its BASENAME, and North Carolina writes that affix at EITHER
  //        end — "Coopers township" (suffix) and "Township 1, Carthage"
  //        (prefix). A suffix-only reading, which is what every sibling
  //        instance needs, silently drops the type row on the numbered
  //        townships, of which this state has hundreds.
  //    (b) An affix the table does not carry must produce NO row rather than an
  //        improvised one.
  //    (c) The municipality card carries ONE type note for city, town and
  //        village (NCGS 160A-1(2)) and a SEPARATE status row only for the
  //        three FUNCSTAT I municipalities. A per-style note would invent a
  //        distinction the statute denies; a missing status row would imply a
  //        working government where the Census records none.
  //    (d) A place above 25,000 names its mayor and every council seat from
  //        the roster, joined on the Census id the stub carries, with who
  //        elects each seat; a place outside the 42 says it names nobody.
  //        The roster is the shipped data/app file, so this also holds the
  //        join to it. Each id and NAME is the Census's own (TIGERweb,
  //        read 2026-10-16).
  {
    function esriPolygon(props) {
      return {
        attributes: props,
        geometry: { rings: [[[-79, 35], [-78, 35], [-78, 36], [-79, 36], [-79, 35]]] }
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
        name: "a SUFFIX township names its type",
        layer: "county-subdivision",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/1",
        props: { GEOID: "3702191740", NAME: "Coopers township", BASENAME: "Coopers", STATE: "37", COUNTY: "021", LSADC: "44" },
        want: [/Coopers township/, /non-functioning/, /no township board/],
        reject: []
      },
      {
        name: "a PREFIX township names its type too",
        layer: "county-subdivision",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/1",
        props: { GEOID: "3712591000", NAME: "Township 1, Carthage", BASENAME: "1, Carthage", STATE: "37", COUNTY: "125", LSADC: "44" },
        want: [/Township 1, Carthage/, /non-functioning/],
        reject: []
      },
      {
        name: "an affix the table does not carry prints NO type row",
        layer: "county-subdivision",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/1",
        props: { GEOID: "3702900000", NAME: "Number 3 barony", BASENAME: "Number 3", STATE: "37", COUNTY: "029", LSADC: "00" },
        want: [/Number 3 barony/],
        reject: [/^[\s\S]*Type[\s\S]*$/]
      },
      {
        name: "a town below 25,000 gets the ONE municipality note, no status row and no names",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "3736080", NAME: "Knightdale town", BASENAME: "Knightdale", STATE: "37", LSADC: "43", FUNCSTAT: "A" },
        want: [/Knightdale town/, /same kind of government/, /Not named here/, /42 cities and towns above 25,000/],
        reject: [/INACTIVE/, /Mayor/]
      },
      {
        name: "a city names its mayor and council, and who elected each seat",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "3725580", NAME: "Gastonia city", BASENAME: "Gastonia", STATE: "37", LSADC: "25", FUNCSTAT: "A" },
        want: [/Gastonia city/, /same kind of government/, /Richard Franks/, /Demetrios Koutsoupias/,
          /Council, Ward 1/, /elected by Ward 1/, /James Gallagher/, /Council, Ward 3/,
          /elected by the whole city/, /How the seats are elected/, /Read on/, /Which ward this point is in/],
        reject: [/INACTIVE/, /Not named here/]
      },
      {
        name: "a town that elects every seat by the whole town says so",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "3701520", NAME: "Apex town", BASENAME: "Apex", STATE: "37", LSADC: "43", FUNCSTAT: "A" },
        want: [/Apex town/, /Jacques Gilbert/, /Council, At large/, /elected by the whole town/,
          /all five council members are elected by the voters of the whole town/],
        reject: [/elected by (Ward|District)/, /this point is in/, /Not named here/]
      },
      {
        name: "a city that ties seats to wards and elects them all citywide says so",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "3719000", NAME: "Durham city", BASENAME: "Durham", STATE: "37", LSADC: "25", FUNCSTAT: "A" },
        want: [/Durham city/, /Matt Kopac/, /Council, Ward 1/, /elected by the whole city/,
          /three of the members each represent one of the city's three wards/],
        reject: [/elected by Ward/, /this point is in/, /Not named here/]
      },
      {
        name: "a city whose website this app cannot read says where its names come from",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "3755000", NAME: "Raleigh city", BASENAME: "Raleigh", STATE: "37", LSADC: "25", FUNCSTAT: "A" },
        want: [/Raleigh city/, /Janet Cowell/, /Corey Branch/, /elected by District C/,
          /Raleigh's website does not let this app read it/, /State Board of Elections' results/,
          /Which district this point is in/],
        reject: [/Not named here/, /As listed on Raleigh's own website/]
      },
      {
        name: "a village gets the SAME note, not one of its own",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "3799999", NAME: "Marvin village", BASENAME: "Marvin", STATE: "37", LSADC: "47", FUNCSTAT: "A" },
        want: [/Marvin village/, /same kind of government/],
        reject: [/INACTIVE/]
      },
      {
        name: "a FUNCSTAT I municipality says it is inactive",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "3717040", NAME: "Dellview town", BASENAME: "Dellview", STATE: "37", LSADC: "43", FUNCSTAT: "I" },
        want: [/Dellview town/, /INACTIVE/, /no government operating/],
        reject: []
      },
      {
        name: "the school district names the district and nobody on its board",
        layer: "school-district-unified",
        service: "School/MapServer/0",
        props: { GEOID: "3704720", NAME: "Wake County Schools", STATE: "37", LOGRADE: "KG", HIGRADE: "12" },
        want: [/Wake County Schools/],
        reject: []
      }
    ];

    for (const c of cases) {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=${c.layer}`, async (p) => {
        // The layer is drawn and answered from a tile archive since 2026-10-17,
        // so the archive is refused here: the card then falls back to the
        // census loader, whose point query and whole-set download go to the
        // same service path, and this one route answers either with the same
        // feature (the archive-failure path il's smoke check 2d also holds).
        await p.route(`**/data/app/tiles/${c.layer}.pmtiles`, (r) => r.abort());
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
  //    point query cannot be filtered server-side — and outside North
  //    Carolina it does not answer with nothing, it answers with a real
  //    neighbouring ZIP. Measured against the live service 2026-09-29:
  //    Norfolk VA -> 23504, Columbia SC -> 29201, Nashville TN -> 37203,
  //    against Raleigh's correct 27601. So without a coverage test this card
  //    would present another state's ZIP code as this app's answer.
  //
  //    THE OUT-OF-STATE HALF IS THE ONE THAT DISCRIMINATES, and the stub is
  //    what makes it honest: it answers with 23504 — the ZIP the live service
  //    really does return out there — so a regression that drops `coverage`
  //    renders that card and fails here. Stubbing an EMPTY answer would pass
  //    for the wrong reason, which is the shape this file's section 7 already
  //    exists to avoid. The in-state half is equally load-bearing: coverage
  //    fails OPEN, so a test that only asserted hiding would also pass on a
  //    layer that had stopped working altogether.
  //
  //    The negative point is the worksheet's own, the open Atlantic east of
  //    Hatteras — outside the county fabric's dissolve, which is what the
  //    coverage test reads. It cannot be a sound: the fabric is
  //    water-inclusive, so Pamlico is in Hyde County and inside coverage.
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
          geometry: { rings: [[[-80, 34], [-74, 34], [-74, 37], [-80, 37], [-80, 34]]] }
        }]
      });
    }

    // in state: the layer answers, and answers from the stub
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=zip-code`, async (p) => {
        // The layer is drawn and answered from a tile archive since 2026-10-17;
        // refusing it sends the card to the census loader, which this stub answers
        // (the archive-failure path il's smoke check 2d also holds).
        await p.route("**/data/app/tiles/zip-code.pmtiles", (r) => r.abort());
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("27601") }));
      });
      const info = await cardText(page, "zip-code");
      check("zip-code answers inside North Carolina (coverage fails open, so this half matters)",
        !info.error && /27601/.test(info.text || ""),
        (info.text || "").slice(0, 90));
      await context.close();
    }

    // out of state: the layer HIDES, and the neighbouring ZIP never renders
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${NEGATIVE_POINT}&layers=zip-code`, async (p) => {
        // The layer is drawn and answered from a tile archive since 2026-10-17;
        // refusing it sends the card to the census loader, which this stub answers
        // (the archive-failure path il's smoke check 2d also holds).
        await p.route("**/data/app/tiles/zip-code.pmtiles", (r) => r.abort());
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("23504") }));
      });
      const hidden = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-zip-code");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === true;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const info = await cardText(page, "zip-code");
      const leaked = /23504/.test(info.text || "");
      const stillOn = await page.evaluate(
        (n) => window[n].state.layersOn["zip-code"] === true, EXPORTS_NAME);
      check("zip-code hides outside North Carolina rather than naming a Virginia ZIP",
        hidden && !leaked && stillOn,
        `hidden=${hidden} leaked=${leaked} layersOn=${stillOn} text=${(info.text || "").slice(0, 90)}`);
      await context.close();
    }
  }
  // ---- Tribal Government. The Qualla Boundary was the 2020 census's Eastern Cherokee Reservation
  // under another code, so its card carries that count and says so; the Band's
  // communities are drawn by the Census and named; its site could not be read,
  // so the card must say why it names nobody. Points are shapely's representative point
  // for the part of each shipped parcel inside the state (2026-10-10).
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const fieldsOf = (page) => page.$$eval("#card-tribal-government .card-field",
      (els) => els.map((e) => ({
        label: ((e.querySelector(".card-field-label") || {}).textContent || "").trim(),
        value: ((e.querySelector(".card-field-value") || {}).textContent || "").trim()
      })));
    const at = async (pt) => {
      const page = await booted(context, `${BASE}#point=${pt}&layers=tribal-government`);
      const card = await cardText(page, "tribal-government");
      const fields = await fieldsOf(page);
      return { text: card.text, by: (l) => (fields.find((f) => f.label === l) || {}).value || "" };
    };
    const q = await at("35.51618,-83.23237");
    check("the Qualla Boundary names the Eastern Band, its communities and its 2020 count",
          q.by("Tribal government") === "Eastern Band of Cherokee Indians" &&
          q.by("Land") === "Qualla Boundary" &&
          q.by("Districts drawn here").indexOf("Birdtown Community") !== -1 &&
          q.by("Population").indexOf("9,233") !== -1 &&
          q.by("Population").indexOf("Eastern Cherokee Reservation") !== -1 &&
          /\d{4}-\d{2}-\d{2}/.test(q.by("Why no names")),
          JSON.stringify(q.text.slice(0, 300)));
    const off = await at(POINT);
    check("a point off tribal land is told so in the layer's own words",
          off.text.indexOf("not on tribal land") !== -1 && off.text.indexOf("2 tribal areas") !== -1,
          JSON.stringify(off.text.slice(0, 120)));
    await context.close();
  }

  // ---- City Council District, drawn for the seventeen cities above 25,000
  // people that elect members by district or ward, and answered from the
  // shipped files alone, so nothing here is stubbed. In Charlotte, Raleigh,
  // Greensboro and Winston-Salem it names the member that district or ward
  // elects and no other, in the city's own word for the unit, and says whose
  // map the line comes from; in Gastonia's Ward 3 it names the ward's member
  // and says the whole city elected them; in Durham and Concord, which tie
  // seats to wards and districts and elect them all citywide, and in
  // Asheville, which elects every seat citywide, there is nothing to answer
  // and the card says why. Raleigh's point is the State Capitol, which lies
  // in District C; the Charlotte, Greensboro and Winston-Salem points and
  // the three outside points are the ward builder's own anchors; the
  // Gastonia point is shapely's representative point of Ward 3. Each lies
  // inside the Census outline of the city named (TIGERweb, read 2026-10-16).
  for (const c of [
    { name: "Charlotte", point: "35.24796,-80.80292",
      want: [/District 1\b/, /Charlotte City Council/, /Danté Anderson/, /Council, District 1/,
        /elected by District 1/, /The mayor and four more members\. The City or Town card names them\./,
        /the City of Charlotte's own map/, /within 4 metres/],
      reject: [/Malcolm Graham/, /Dimple Ajmera/, /Rob Harrington/, /elected by Ward/] },
    { name: "Raleigh", point: POINT,
      want: [/District C\b/, /Raleigh City Council/, /Corey Branch/, /elected by District C/,
        /The mayor and two more members/, /Raleigh's website does not let this app read it/,
        /published by the city in November 2021/, /2024 election/],
      reject: [/Mitchell Silver/, /Janet Cowell/, /Stormie Denise Forte/] },
    { name: "Greensboro", point: "36.07530,-79.86492",
      want: [/District 4\b/, /Greensboro City Council/, /Adam Marshall/, /elected by District 4/,
        /The mayor and three more members/, /Guilford County's map of Greensboro's districts/],
      reject: [/Tammi Thurm/, /Hugh Holston/, /Marikay Abuzuaiter/] },
    { name: "Winston-Salem", point: "36.09319,-80.16777",
      want: [/East Ward/, /Winston-Salem City Council/, /Annette Scippio/, /Council, East Ward/,
        /elected by the East Ward/, /The mayor\. The City or Town card names the mayor\./],
      reject: [/Denise D\. Adams/, /J\. Allen Joines/, /elected by Ward/] },
    { name: "Gastonia's Ward 3", point: "35.22074,-81.14536",
      want: [/Ward 3\b/, /Gastonia City Council/, /James Gallagher/, /Council, Ward 3/,
        /elected by the whole city/, /The mayor and two more members/,
        /from 2027 those wards elect their own members too/],
      reject: [/Demetrios Koutsoupias/, /Angela Dreher/, /elected by Ward 3/] },
    { name: "Durham", point: "35.99400,-78.89860",
      want: [/not in a council district or ward this map draws/, /Durham, Concord, Hickory and Morrisville/],
      reject: [/Durham City Council/] },
    { name: "Concord", point: "35.40880,-80.57950",
      want: [/not in a council district or ward this map draws/, /Durham, Concord, Hickory and Morrisville/],
      reject: [/Concord City Council/] },
    { name: "Asheville", point: "35.59510,-82.55150",
      want: [/not in a council district or ward this map draws/, /names the mayor and council of all 42/],
      reject: [/Asheville City Council/] },
  ]) {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${c.point}&layers=city-ward`);
    const info = await cardText(page, "city-ward");
    const text = info.text || "";
    const missing = c.want.filter((re) => !re.test(text));
    const present = c.reject.filter((re) => re.test(text));
    check(`city-ward card at ${c.name} names only what that district elects, in the city's own word`,
      !info.error && missing.length === 0 && present.length === 0,
      `missing=${missing} unwanted=${present} text=${text.slice(0, 200)}`);
    await context.close();
  }

  // ---- School Board District, drawn from the State Board of Elections'
  // precinct-level results and answered from the shipped file alone, so
  // nothing here is stubbed. Each point is shapely's representative point of
  // the shipped piece shrunk by about 200 m, so it is no nearer an edge than
  // that (nc/data/app/nc-school-board-districts.json, 2026-10-17). The State
  // Capitol is in Wake's District 6, last elected on November 5, 2024: the card
  // names the seat, the election it is drawn from and the school district's
  // website, and must NOT name either candidate in that contest (Sam Hershey
  // won it), because the app names no member. A split precinct names both
  // seats and says the results do not place the line; ground two elections put
  // different seats on names both elections and chooses neither; Watauga's
  // ground that no district seat's latest contest reached says so; Durham
  // names the consolidated district over its district; and Smithfield, whose
  // Johnston County board labels seats by district while every precinct votes
  // on each, gets the empty card and no district.
  for (const c of [
    { name: "the State Capitol (Wake District 6)", point: POINT,
      want: [/District 6\b/, /Wake County Schools \(Wake County Board of Education\)/,
        /The election of November 5, 2024: the precincts whose ballots carried this seat's contest/,
        /Members Not named here/, /Results by precinct/, /Look up your voter registration/],
      reject: [/Sam Hershey/, /Josh Points/, /Members elected at large/, /Districts from/],
      footer: ["Wake County Schools website", "https://www.wcpss.net/"] },
    { name: "Bladen's COLLY precinct (split)", point: "34.66595,-78.49338",
      want: [/District 1 or District 3/, /Why two districts/,
        /COLLY precinct carried the contests for District 1 and District 3 in the ballot of November 3, 2026, which the State Board posted on October 5, 2026, before the election was held/,
        /the results do not say where/, /Members elected at large/],
      reject: [/Drawn from/, /Districts from/] },
    { name: "Duplin ground two elections disagree on (overlap)", point: "34.79927,-77.82405",
      want: [/Districts from two elections/, /The ballot of November 3, 2026, which the State Board posted on October 5, 2026, before the election was held District 3/,
        /The election of November 5, 2024 District 4/, /chooses none/,
        /Results of November 3, 2026/, /Results of November 5, 2024/],
      reject: [/Drawn from/] },
    { name: "Watauga ground no district contest reached (unplaced)", point: "36.23570,-81.83690",
      want: [/No district placed here/, /On the ballot here/, /At large \(November 5, 2024\)/,
        /The results do not say which/],
      reject: [/Drawn from/, /Districts from/] },
    { name: "Durham District 1 under Consolidated District A", point: "35.97381,-78.88550",
      want: [/District 1\b/, /Durham Public Schools \(Durham County Board of Education\)/,
        /Also elects Consolidated District A, which covers District 1 and District 2 and elects a member of its own/],
      reject: [/Districts from/, /No district placed here/] },
    { name: "Smithfield (Johnston, district-labelled seats voted on everywhere)", point: "35.50850,-78.33940",
      empty: true,
      want: [/No school board election district is drawn at this point/, /elected at large/],
      reject: [/Not named here/, /Drawn from/, /District \d/] },
  ]) {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${c.point}&layers=school-board-district`);
    const info = await cardText(page, "school-board-district");
    const text = info.text || "";
    const footer = await page.evaluate(() => {
      const el = document.getElementById("card-school-board-district");
      const block = el && el.closest(".layer-block");
      const a = block && block.querySelector(".card-footer-link");
      return a ? [a.textContent.trim(), a.getAttribute("href")] : null;
    });
    const missing = c.want.filter((re) => !re.test(text));
    const present = c.reject.filter((re) => re.test(text));
    const footerOk = !c.footer || (!!footer && footer[0] === c.footer[0] && footer[1] === c.footer[1]);
    check(`school-board-district card at ${c.name} says what the results place there and names no member`,
      !info.error && (c.empty ? info.empty : !info.empty) &&
        missing.length === 0 && present.length === 0 && footerOk,
      `missing=${missing} unwanted=${present} footer=${JSON.stringify(footer)} text=${text.slice(0, 240)}`);
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
