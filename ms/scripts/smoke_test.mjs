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
const POINT = "32.30380,-90.18220"; // the State Capitol, Jackson, Hinds County
const OFFLINE = ["county", "us-house", "ms-senate", "ms-house"];
const EXPECT_DISTRICT = { "county": "Hinds County", "us-house": "2", "ms-senate": "29", "ms-house": "67" };
const NEGATIVE_POINT = "32.48000,-88.25000"; // near York, Sumter County, ALABAMA, about 12 km east of the Mississippi line — outside Mississippi and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-15: TIGERweb's county layer names Sumter County, Alabama at this point (control: the Capitol anchor returns Hinds County, Mississippi), and the Census's ZIP layer answers 36925 there, which is the neighbouring-state answer the ZIP layer's coverage test exists to hide. ALABAMA BECAUSE NO INSTANCE SERVES IT and it is not on the next-states list; Louisiana, Arkansas and Tennessee, which share Mississippi's other borders, were passed over so this point does not have to move when any of them is live.
const APP_NAME = "districtry Mississippi";
const EXPECT_LAYERS = 17;
// ==== GENERATED:END smoke-config ====
// Fork-specific smoke-test constants (the reference repo hoists its own set
// here). The template's CHI-scenario checks are dropped at build time, so the
// GAP_PROBE / MOVE_POINT / STRAGGLER_* names below are contract stubs — the
// span's consumers keep the names resolvable; grow real fixtures (and restore
// the corresponding checks from the reference repo's smoke_test.mjs) as this
// fork ships the layers they exercise.
const EXPORTS_NAME = "MississippiExplorer";
const PORTAL_HOST = "data.invalid"; // must stay a non-empty hostname: an empty string would abort every request
// Geocoder type-ahead fixture: RAW carries an embedded unit the app's cleaner
// must strip to CLEANED; the Photon STUB answers only CLEANED, so the check
// proves the strip-and-retry path with no live network.
const GEOCODER_QUERY_RAW = "16 W Jones St Suite 200, Capital City";
const GEOCODER_UNIT_FRAGMENT = "Suite 200";
const GEOCODER_QUERY_CLEANED = "16 W Jones St, Capital City";
const GEOCODER_STUB_FEATURE = {
  type: "Feature",
  geometry: { type: "Point", coordinates: [-90.18220, 32.30380] },
  properties: {
    // the typed number: an answer without it shows the street instead of
    // a row (ENGINE geocoder-search runAddressSearch)
    housenumber: "16",
    street: "W Jones St",
    city: "Capital City",
    state: "Mississippi",
    postcode: "00000"
  }
};
// Contract stubs (their consuming checks are reference-fork scenarios,
// dropped from this template's body):
const GAP_PROBE = { county: "statewide", label: "Statewide", lat: 32.30380, lng: -90.18220 };
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
  //     MISSISSIPPI HAS TWO NEIGHBOURS THE FLEET SERVES AND TWO IT DOES NOT,
  //     so both halves are its own. Tennessee is live, so a click on Memphis
  //     must open that app: Overton Park sits about 16 km north of the state
  //     line, well clear of either outline's simplification. Arkansas went
  //     live on 2026-10-15, so a click on Lake Village must open THAT app: it
  //     is the Chicot County seat, about 11.5 km west of the river that is the
  //     state line, and measured against fleet-outlines.json it lies inside
  //     Arkansas's outline and no other, and outside this app's coverage ring.
  //     Alabama is served by nobody, so a click near York, Alabama must stay
  //     here (1a2-ii below). This instance answers its own side from the
  //     coverage rings the wash retained — no fetch. Chicago proves the file
  //     is still read for ground far from here.
  //
  //     LOUISIANA IS DELIBERATELY NOT A CASE. It is on the next-states list,
  //     so a "stays here" case there would start failing the day it goes
  //     live, in a change that is about another state.
  {
    const cases = [
      { name: "Chicago", lat: 41.8825, lng: -87.6285, want: "https://districtry.com/il/" },
      { name: "Memphis, Tennessee", lat: 35.1440, lng: -89.9930, want: "https://districtry.com/tn/" },
      { name: "Lake Village, Arkansas", lat: 33.3290, lng: -91.2818, want: "https://districtry.com/ar/" },
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
      check(`a click on ${c.name} from Mississippi opens ${c.want} with the point`, !!went, went || page.url());
      await context.close();
    }
  }

  // 1a2-ii. The half that keeps 1a2 honest: the negative point, near York in
  //     Sumter County, Alabama, is about 12 km east of the state line and no
  //     districtry instance covers it, so the click must stay HERE. A route to
  //     a sibling would be the same lie pointing the other way, and the stub
  //     makes it visible: if the app navigated, the URL would be the stubbed
  //     sibling rather than this app.
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
    // Still under BASE means still this app. This asked for the URL NOT to
    // name one of a list of sibling tags, and a list needs a new entry each
    // time a state goes live: the one it lacked would read as staying here.
    check("a click near York, Alabama stays in this app",
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
  //    fire-station is 1,508 points in Mississippi's envelope, within 492
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
      attributes: { NAME: `FAR STATION ${i}`, ADDRESS: "1 Far Rd", CITY: "Tupelo", STATE: "MS", ZIPCODE: "38804" },
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
                              CITY: "Jackson", STATE: "MS", ZIPCODE: "39201" },
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
      /Jackson, MS/.test(text), text.slice(0, 140));
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
  //    (a) The municipality card states the style the Census records — a
  //        CITY, a TOWN or a VILLAGE, Mississippi's three — and an affix the
  //        card does not know produces NO type row rather than an improvised
  //        one.
  //    (b) A separate status row appears only for a FUNCSTAT I place. One
  //        Mississippi place is inactive today (Tillatoba, one of 300,
  //        measured 2026-10-15), and a missing status row would imply a
  //        working government where the Census records none.
  //    (c) The one school tiling answers, under the label with no qualifier,
  //        because the unified districts cover the state alone.
  {
    function esriPolygon(props) {
      return {
        attributes: props,
        geometry: { rings: [[[-91, 31.5], [-89.5, 31.5], [-89.5, 33], [-91, 33], [-91, 31.5]]] }
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
        name: "a city names itself a city",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "2836000", NAME: "Jackson city", BASENAME: "Jackson", STATE: "28", LSADC: "25", FUNCSTAT: "A" },
        want: [/Jackson city/, /Incorporated city/, /Mayor/],
        reject: [/INACTIVE/, /Incorporated town/, /Incorporated village/, /Not named here/]
      },
      {
        name: "a town names itself a town, not a city",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "2824940", NAME: "Flora town", BASENAME: "Flora", STATE: "28", LSADC: "43", FUNCSTAT: "A" },
        want: [/Flora town/, /Incorporated town/, /this town is not one of them/],
        reject: [/INACTIVE/, /Incorporated city/, /Incorporated village/, /Who these are/]
      },
      {
        name: "a village names itself a village",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "2865680", NAME: "Satartia village", BASENAME: "Satartia", STATE: "28", LSADC: "47", FUNCSTAT: "A" },
        want: [/Satartia village/, /Incorporated village/],
        reject: [/INACTIVE/, /Incorporated city/, /Incorporated town/]
      },
      {
        name: "an affix the card does not carry prints NO type row",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "2899999", NAME: "Nowhere borough", BASENAME: "Nowhere", STATE: "28", LSADC: "21", FUNCSTAT: "A" },
        want: [/Nowhere borough/],
        reject: [/Incorporated city/, /Incorporated town/, /Incorporated village/]
      },
      {
        name: "a FUNCSTAT I place says it is inactive",
        layer: "municipality",
        service: "Places_CouSub_ConCity_SubMCD/MapServer/4",
        props: { GEOID: "2873440", NAME: "Tillatoba town", BASENAME: "Tillatoba", STATE: "28", LSADC: "43", FUNCSTAT: "I" },
        want: [/Tillatoba town/, /INACTIVE/, /no government operating/],
        reject: []
      },
      {
        name: "the school district card names the district",
        layer: "school-district-unified",
        service: "School/MapServer/0",
        props: { GEOID: "2802190", NAME: "Jackson Public School District", STATE: "28" },
        want: [/Jackson Public School District/],
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
  //    point query cannot be filtered server-side — and outside Mississippi it
  //    does not answer with nothing, it answers with a real neighbouring ZIP.
  //    Measured against the live service 2026-10-15: the Alabama negative
  //    point -> 36925, against the State Capitol's correct 39201. So without a
  //    coverage test this card would present another state's ZIP code as this
  //    app's answer.
  //
  //    THE OUT-OF-STATE HALF IS THE ONE THAT DISCRIMINATES, and the stub is
  //    what makes it honest: it answers with 36925 — a ZIP the live service
  //    really does return over the line — so a regression that drops
  //    `coverage` renders that card and fails here. Stubbing an EMPTY answer
  //    would pass for the wrong reason. The in-state half is equally
  //    load-bearing: coverage fails OPEN, so a test that only asserted hiding
  //    would also pass on a layer that had stopped working altogether.
  //
  //    The negative point is the worksheet's own, in Sumter County, Alabama —
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
          geometry: { rings: [[[-91, 31.5], [-87.5, 31.5], [-87.5, 33], [-91, 33], [-91, 31.5]]] }
        }]
      });
    }

    // in state: the layer answers, and answers from the stub
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=zip-code`, async (p) => {
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("39201") }));
      });
      const info = await cardText(page, "zip-code");
      check("zip-code answers inside Mississippi (coverage fails open, so this half matters)",
        !info.error && /39201/.test(info.text || ""),
        (info.text || "").slice(0, 90));
      await context.close();
    }

    // out of state: the layer HIDES, and the neighbouring ZIP never renders
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${NEGATIVE_POINT}&layers=zip-code`, async (p) => {
        await p.route(`**/${ZCTA}/query**`, (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: zctaBody("36925") }));
      });
      const hidden = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-zip-code");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === true;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const info = await cardText(page, "zip-code");
      const leaked = /36925/.test(info.text || "");
      const stillOn = await page.evaluate(
        (n) => window[n].state.layersOn["zip-code"] === true, EXPORTS_NAME);
      check("zip-code hides outside Mississippi rather than naming an Alabama ZIP",
        hidden && !leaked && stillOn,
        `hidden=${hidden} leaked=${leaked} layersOn=${stillOn} text=${(info.text || "").slice(0, 90)}`);
      await context.close();
    }
  }

  // 9. THE BOARD OF SUPERVISORS, on the County card. The expected names are
  //    read from the shipped roster rather than written here, because a new
  //    edition of the directory changes them and a name in this file would
  //    fail a correct rebuild. Three counties, each for its own claim:
  //      - Hinds, at the Capitol: all five supervisors with their districts,
  //        the board's address where the roster carries one, and the credit;
  //      - Jasper, one of the five counties whose directory page says "Beat":
  //        the card uses the county's word;
  //      - Amite, one of the six counties whose supervisors each print a
  //        different address: NO office block at all, because a supervisor's
  //        own address may be a home;
  //      - Sunflower, whose District 3 the 2026 directory prints as "Vacant":
  //        the card says the seat is vacant, and nobody called Vacant is
  //        listed as a supervisor. A roster with no vacancy there still runs
  //        the other assertions, so a new edition filling the seat passes.
  //    In all four the card also names the county's five election
  //    commissioners by district, in the directory's word for them ("District"
  //    even in Jasper, where the supervisors' districts are beats), and quotes
  //    the directory on what they do. Only names reach the card: the roster
  //    carries nothing else for them, which the builder's --check holds.
  //    The non-Capitol points are interior points of each county as the
  //    shipped geometry draws it (polylabel, 2026-10-15).
  {
    const roster = JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "app", "ms-county-officials.json"), "utf8"));
    const cases = [
      { name: "Hinds County", point: POINT, fips: "28049" },
      { name: "Jasper County", point: "32.01901,-89.11740", fips: "28061" },
      { name: "Amite County", point: "31.17456,-90.72388", fips: "28005" },
      { name: "Sunflower County", point: "33.47334,-90.60537", fips: "28133" },
    ];
    for (const c of cases) {
      const o = roster[c.fips];
      const word = o.label === "Beat" ? "Beat" : "District";
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${c.point}&layers=county`);
      const county = await cardText(page, "county");
      const seated = o.supervisors.filter((sv) => sv.vacant !== true);
      const empty = o.supervisors.filter((sv) => sv.vacant === true);
      const missing = seated.filter((sv) => !county.text.includes(sv.name) ||
        !county.text.includes(`${word} ${sv.district}`)).map((sv) => sv.name);
      // every vacant seat is said to be vacant; no "Vacant" stands as a name
      const unsaid = empty.filter((sv) =>
        !new RegExp(`${word} ${sv.district}\\b[^.]*listed as vacant`).test(county.text))
        .map((sv) => `${word} ${sv.district}`);
      const vacantAsName = /Vacant(?! seats?)/.test(county.text);
      const vacancyRight = unsaid.length === 0 && !vacantAsName &&
        (empty.length > 0 || !/Vacant seat/.test(county.text));
      const office = /Board of supervisors' office/.test(county.text);
      const officeRight = (o.boardAddress || o.boardPhone)
        ? office && (!o.boardAddress || county.text.includes(o.boardAddress))
        : !office;
      check(`county card at ${c.name} names every seated supervisor by ${word.toLowerCase()} and says which seats are vacant, with a board office only where the roster has one`,
        !county.error && county.text.includes(c.name) && missing.length === 0 && officeRight &&
          vacancyRight &&
          /Where these names come from/.test(county.text) &&
          /County Offices and Directory/.test(county.text),
        missing.length ? `missing=${missing.slice(0, 3)}`
          : !vacancyRight ? `unsaid=${unsaid} vacantAsName=${vacantAsName}`
          : `office=${office} ${county.text.slice(0, 90)}`);
      const cword = o.commissionerLabel === "Beat" ? "Beat" : "District";
      const commissioners = (o.electionCommissioners || []).filter((ec) => ec.vacant !== true);
      // the commissioners follow their own heading, so each is looked for
      // there; the heading is set in capitals, which innerText reports
      const at = county.text.search(/election commissioners/i);
      const after = at >= 0 ? county.text.slice(at) : "";
      const unnamed = commissioners.filter((ec) => !after.includes(ec.name) ||
        !after.includes(`${cword} ${ec.district}`)).map((ec) => ec.name);
      check(`county card at ${c.name} names its election commissioners by ${cword.toLowerCase()} and quotes the directory on what they do`,
        !county.error && commissioners.length > 0 && unnamed.length === 0 &&
          /Election commissioner\b/.test(after) &&
          /What election commissioners do/.test(county.text) &&
          /certifying election results/.test(county.text) &&
          /supervisor and the election commissioner elected from the/.test(county.text),
        unnamed.length ? `unnamed=${unnamed.slice(0, 3)}` : after.slice(0, 120));
      await context.close();
    }
  }

  // 9b. The roster is refused, and the County card must degrade to a sentence
  //    naming nobody while the county itself still classifies: a roster
  //    failure is not the layer's failure.
  {
    const roster = JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "app", "ms-county-officials.json"), "utf8"));
    const hinds = roster["28049"];
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=county`, async (p) => {
      await p.route("**/data/app/ms-county-officials.json", (r) => r.fulfill({ status: 503, body: "down" }));
    });
    const county = await cardText(page, "county");
    const named = hinds.supervisors.concat(hinds.electionCommissioners)
      .filter((sv) => sv.name && county.text.includes(sv.name)).map((sv) => sv.name);
    check("county card degrades to naming nobody when the roster fails",
      !county.error && /Hinds County/.test(county.text) && /did not load/.test(county.text) &&
        named.length === 0,
      `named=${named.slice(0, 2)} text=${county.text.slice(0, 90)}`);
    await context.close();
  }

  // 10. THE COUNTY SUPERVISOR DISTRICT LAYER, drawn only in the counties whose
  //     current lines are confirmed. The expected district, county, supervisor
  //     and edition are read from the shipped files, so a rebuild that
  //     renumbers a county moves the expectation with it; what is asserted is
  //     that the card agrees with those files at the point.
  //       - Two counties drawn from the Census's lines: the card's
  //         "District N" is the district the shipped file puts the point in, it
  //         names that district's supervisor from the directory, and it says
  //         where the line and the name come from, naming the Census edition.
  //       - Two counties drawn from their own maps, Hinds at the Capitol and
  //         Rankin: the card says whose map the line comes from and when it
  //         was read, and never names the Census edition; in Rankin it also
  //         says how many people the map's own population figures leave out,
  //         and in Hinds that it leaves nobody out.
  //       - Amite, whose Census lines place every resident as the Census's
  //         January 1, 2010 edition does, and which publishes none of its
  //         own: the layer HIDES, with the layers= permalink intact. This is
  //         the half that discriminates: without `coverage` the card would
  //         say no district is drawn here, about a county that has five.
  //       - With the layer OFF at the Capitol, the coverage test reads the
  //         list of drawn counties and never the districts file, which was
  //         150 KB gzipped on every reader's first selection when the test
  //         read it (2026-10-15), and the layer's toggle still shows there.
  //       - Each of those cards also names the election commissioner of the
  //         same district from the same directory, and says where the names
  //         (plural) come from.
  //       - The roster is refused: the district still answers and names nobody.
  //       - A vacant seat, on a stubbed directory because no drawn county has
  //         one in the 2026 edition: the card says the seat is vacant and
  //         names nobody for it. The same for a vacant commissioner's seat,
  //         while the supervisor is still named.
  //       - A stubbed directory that names the supervisors' districts with one
  //         word and the commissioners' with another: no commissioner is
  //         joined to the district on the strength of its number alone.
  //     The points are interior points of each district as the shipped file
  //     draws it (polylabel, 2026-10-15), each at least 5 km from its lines.
  {
    const sup = JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "app", "ms-supervisor-districts.json"), "utf8"));
    const rec = JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "source", "ms-supervisor-districts.source.json"), "utf8"));
    const roster = JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "app", "ms-county-officials.json"), "utf8"));
    // the app's rule: even-odd within a polygon, any part of a multipolygon
    function inRing(x, y, ring) {
      let inside = false;
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i], [xj, yj] = ring[j];
        if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
      }
      return inside;
    }
    function districtsAt(point) {
      const [lat, lng] = point.split(",").map(Number);
      return sup.features.filter((f) => {
        const g = f.geometry;
        const polys = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
        return polys.some((rings) => rings.reduce((acc, ring) => acc !== inRing(lng, lat, ring), false));
      }).map((f) => f.properties);
    }
    function seatOf(p) {
      const o = roster[p.countyfips] || { supervisors: [] };
      return o.supervisors.find((sv) => String(sv.district) === String(p.district)) || {};
    }
    function commissionerOf(p) {
      const o = roster[p.countyfips] || {};
      return (o.electionCommissioners || []).find((ec) => String(ec.district) === String(p.district)) || {};
    }
    const drawnPoints = ["34.92782,-90.17414", "33.34602,-88.57919"];  // DeSoto 3, Lowndes 4
    const ownMapPoints = [POINT, "32.34382,-89.84721"];  // Hinds 5 (the Capitol), Rankin 4
    const AMITE = "31.17456,-90.72388";  // the Amite County point check 9 uses

    for (const pt of drawnPoints) {
      const at = districtsAt(pt);
      const p = at[0] || {};
      const seat = seatOf(p);
      const word = p.label === "Beat" ? "Beat" : "District";
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${pt}&layers=county-supervisor`);
      const info = await cardText(page, "county-supervisor");
      const text = info.text || "";
      const ec = commissionerOf(p);
      check(`county-supervisor card in ${p.county || "a drawn county"} names ${word} ${p.district}, its supervisor and its election commissioner, with where the line and the names come from`,
        at.length === 1 && !info.error && !!seat.name && !!ec.name &&
          new RegExp(`\\b${word} ${p.district}\\b`).test(text) &&
          text.includes(seat.name) && text.includes(ec.name) && /Election commissioner/.test(text) &&
          text.includes(p.county) &&
          /Where this line comes from/.test(text) && text.includes(`${rec.vintage} edition`) &&
          /Where the names come from/.test(text),
        `districts here=${at.length} ${text.slice(0, 120)}`);
      await context.close();
    }

    for (const pt of ownMapPoints) {
      const at = districtsAt(pt);
      const p = at[0] || {};
      const seat = seatOf(p);
      const aside = Number(p.set_aside) || 0;
      const asideText = `${aside.toLocaleString("en-US")} people in census blocks with almost no homes`;
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${pt}&layers=county-supervisor`);
      const info = await cardText(page, "county-supervisor");
      const text = info.text || "";
      const ec = commissionerOf(p);
      check(`county-supervisor card in ${p.county || "a county drawn from its own map"} names District ${p.district}, its supervisor and its election commissioner, and says whose map the line comes from${aside ? " and whom its figures leave out" : ""}`,
        at.length === 1 && p.lines === "county" && !info.error && !!seat.name && !!ec.name &&
          new RegExp(`\\bDistrict ${p.district}\\b`).test(text) &&
          text.includes(seat.name) && text.includes(ec.name) && text.includes(p.county) &&
          !!p.source && text.includes(p.source) && /, read on \d{1,2} [A-Z][a-z]+ \d{4}\./.test(text) &&
          !text.includes(`${rec.vintage} edition`) &&
          (aside > 0 ? text.includes(asideText) : !/almost no homes/.test(text)),
        `districts here=${at.length} lines=${p.lines} ${text.slice(0, 160)}`);
      await context.close();
    }

    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${AMITE}&layers=county-supervisor`);
      const hidden = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-county-supervisor");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === true;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const stillOn = await page.evaluate(
        (n) => window[n].state.layersOn["county-supervisor"] === true, EXPORTS_NAME);
      check("county-supervisor hides in Amite County, whose current lines are not confirmed, and stays switched on",
        districtsAt(AMITE).length === 0 && hidden && stillOn,
        `drawn here=${districtsAt(AMITE).length} hidden=${hidden} layersOn=${stillOn}`);
      await context.close();
    }

    {
      const asked = [];
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=county`, async (pg) => {
        pg.on("request", (r) => asked.push(r.url()));
      });
      await cardText(page, "county");
      const shown = await page
        .waitForFunction(() => {
          const box = document.getElementById("toggle-county-supervisor");
          const block = box && box.closest(".layer-block");
          return block && block.hidden === false;
        }, null, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      const list = asked.some((u) => /\/data\/app\/ms-supervisor-counties\.json/.test(u));
      const file = asked.some((u) => /\/data\/app\/ms-supervisor-districts\.json/.test(u));
      const off = await page.evaluate(
        (n) => !window[n].state.layersOn["county-supervisor"], EXPORTS_NAME);
      check("with county-supervisor off, its coverage test reads the list of drawn counties and never the districts file, and its toggle shows in Hinds",
        off && list && !file && shown,
        `off=${off} list=${list} districts file=${file} shown=${shown}`);
      await context.close();
    }

    const p = districtsAt(drawnPoints[0])[0] || {};
    const seat = seatOf(p);
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${drawnPoints[0]}&layers=county-supervisor`, async (pg) => {
        await pg.route("**/data/app/ms-county-officials.json", (r) => r.fulfill({ status: 503, body: "down" }));
      });
      const info = await cardText(page, "county-supervisor");
      const text = info.text || "";
      const o = roster[p.countyfips] || { supervisors: [] };
      const named = o.supervisors.concat(o.electionCommissioners || [])
        .filter((sv) => sv.name && text.includes(sv.name)).map((sv) => sv.name);
      check("county-supervisor still names the district, and names nobody, when the roster fails",
        !info.error && new RegExp(`\\bDistrict ${p.district}\\b`).test(text) &&
          /did not load/.test(text) && named.length === 0,
        `named=${named.slice(0, 2)} ${text.slice(0, 120)}`);
      await context.close();
    }

    {
      const stub = JSON.parse(JSON.stringify(roster));
      const seats = stub[p.countyfips].supervisors;
      seats[seats.findIndex((sv) => String(sv.district) === String(p.district))] =
        { district: String(p.district), vacant: true };
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${drawnPoints[0]}&layers=county-supervisor`, async (pg) => {
        await pg.route("**/data/app/ms-county-officials.json", (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(stub) }));
      });
      const info = await cardText(page, "county-supervisor");
      const text = info.text || "";
      check("county-supervisor says a vacant seat is vacant and names nobody for it",
        !info.error && !!seat.name && /listed as vacant/.test(text) && !text.includes(seat.name) &&
          !/Vacant/.test(text),
        text.slice(0, 120));
      await context.close();
    }

    const ec = commissionerOf(p);
    {
      const stub = JSON.parse(JSON.stringify(roster));
      const coms = stub[p.countyfips].electionCommissioners;
      coms[coms.findIndex((c) => String(c.district) === String(p.district))] =
        { district: String(p.district), vacant: true };
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${drawnPoints[0]}&layers=county-supervisor`, async (pg) => {
        await pg.route("**/data/app/ms-county-officials.json", (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(stub) }));
      });
      const info = await cardText(page, "county-supervisor");
      const text = info.text || "";
      check("county-supervisor says a vacant election commissioner's seat is vacant, names nobody for it, and still names the supervisor",
        !info.error && !!ec.name && !!seat.name && text.includes(seat.name) &&
          /Election commissioner[^.]*listed as vacant/.test(text) && !text.includes(ec.name) &&
          /Where the name comes from/.test(text),
        text.slice(0, 160));
      await context.close();
    }

    {
      const stub = JSON.parse(JSON.stringify(roster));
      stub[p.countyfips].commissionerLabel = stub[p.countyfips].label === "Beat" ? "District" : "Beat";
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${drawnPoints[0]}&layers=county-supervisor`, async (pg) => {
        await pg.route("**/data/app/ms-county-officials.json", (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(stub) }));
      });
      const info = await cardText(page, "county-supervisor");
      const text = info.text || "";
      check("county-supervisor joins no election commissioner where the directory names the two lists' districts with different words",
        !info.error && !!ec.name && !!seat.name && text.includes(seat.name) &&
          !text.includes(ec.name) && !/Election commissioner/.test(text),
        text.slice(0, 160));
      await context.close();
    }
  }
  // 11. THE FOUR COURTS WHOSE JUDGES ARE ELECTED FROM DISTRICTS. Every
  //     expectation is read from the shipped maps and the shipped list of
  //     judges at the point, so a rebuild moves it with the files; what is
  //     asserted is that each card agrees with them.
  //       - At the Capitol, in Hinds County: the Supreme Court card names its
  //         district and that district's three justices and no others. The
  //         Court of Appeals divides Hinds by voting precinct, so its card
  //         names both districts, says which one takes the listed precincts,
  //         and names the judges of both. The chancery card names its
  //         chancellors and the vacancy the court's news reported, with that
  //         news as its link. The circuit card names its judges and says which
  //         counties its district takes in on 1 January 2027, worked out here
  //         from the two shipped circuit maps.
  //       - In Claiborne County, whose circuit district ends on 1 January
  //         2027: the circuit card names today's district and its judge, says
  //         which district the point is in from that day and that today's
  //         district will not exist; the chancery card says which chancery
  //         district the point moves to. The point is the shipped county's
  //         pole of inaccessibility, 13 km from its nearest edge (2026-10-16).
  //       - With the page's clock at 2 January 2027: both trial layers draw
  //         the 2027 maps and never fetch today's, so the Claiborne point is
  //         in the district the 2027 file puts it in, and the cards name
  //         nobody, because the lists of judges this app reads still describe
  //         the earlier districts. The Supreme Court card still names its
  //         justices, since that court is not redrawn.
  //       - The list of judges is refused: every card still names its
  //         district, says the names did not load, and names nobody.
  {
    const courtFile = (n) => JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "app", n), "utf8"));
    const judges = courtFile("ms-judge-roster.json").courts;
    const maps = {
      supreme: courtFile("ms-supreme-court-districts.json"),
      appeals: courtFile("ms-court-of-appeals-districts.json"),
      chancery: courtFile("ms-chancery-court-districts.json"),
      chancery2027: courtFile("ms-chancery-court-districts-2027.json"),
      circuit: courtFile("ms-circuit-court-districts.json"),
      circuit2027: courtFile("ms-circuit-court-districts-2027.json"),
    };
    // the app's rule: even-odd within a polygon, any part of a multipolygon
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
    function ord(n) {
      const t = n % 100, u = n % 10;
      return n + ((t >= 11 && t <= 13) ? "th" : u === 1 ? "st" : u === 2 ? "nd" : u === 3 ? "rd" : "th");
    }
    function countyPhrase(names) {
      const joined = names.length === 1 ? names[0] : names.slice(0, -1).join(", ") + " and " + names[names.length - 1];
      return joined + (names.length === 1 ? " County" : " Counties");
    }
    const namesOf = (court, unit) =>
      ((judges[court].districts[String(unit)] || {}).members || []).map((m) => m.name);
    const allNames = (court) =>
      Object.values(judges[court].districts).flatMap((d) => (d.members || []).map((m) => m.name));
    const ALL = "ms-supreme-court,ms-court-of-appeals,ms-chancery-court,ms-circuit-court";
    const CLAIBORNE = "31.96509,-90.84966";
    const hrefs = (page, id) => page.$$eval(`#card-${id} a[href]`, (as) => as.map((a) => a.href));

    const sc = propsAt(maps.supreme, POINT);
    const coa = propsAt(maps.appeals, POINT);
    const ch = propsAt(maps.chancery, POINT);
    const ci = propsAt(maps.circuit, POINT);
    const ci27 = propsAt(maps.circuit2027, POINT);
    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=${ALL}`);

      const s = sc[0] || {};
      const sInfo = await cardText(page, "ms-supreme-court");
      const sNames = namesOf("supreme", s.unit);
      const sOthers = allNames("supreme").filter((n) => !sNames.includes(n) && sInfo.text.includes(n));
      check("ms-supreme-court names the Capitol's district and its three justices, and no others",
        sc.length === 1 && !sInfo.error && sNames.length === 3 &&
          new RegExp(`Supreme Court District ${s.unit}\\b`).test(sInfo.text) &&
          sNames.every((n) => sInfo.text.includes(n)) && sOthers.length === 0 &&
          /where these names come from/i.test(sInfo.text),
        `features here=${sc.length} others named=${sOthers.slice(0, 2)} ${sInfo.text.slice(0, 120)}`);

      const a = coa[0] || {};
      const aInfo = await cardText(page, "ms-court-of-appeals");
      const units = (a.units || []).map(String);
      const aNames = units.flatMap((u) => namesOf("appeals", u));
      check("ms-court-of-appeals names both districts that divide Hinds, says which takes the listed precincts, and names both districts' judges",
        coa.length === 1 && units.length === 2 && a.county === "Hinds" && !aInfo.error &&
          aInfo.text.includes(`Court of Appeals District ${units[0]} or ${units[1]}`) &&
          aInfo.text.includes(`are in District ${a.named}, and the rest of the county is in District ${a.rest}`) &&
          units.every((u) => new RegExp(`judges elected from district ${u}\\b`, "i").test(aInfo.text)) &&
          aNames.length === 4 && aNames.every((n) => aInfo.text.includes(n)),
        `features here=${coa.length} units=${units} ${aInfo.text.slice(0, 160)}`);

      const c = ch[0] || {};
      const cInfo = await cardText(page, "ms-chancery-court");
      const cDistrict = judges.chancery.districts[String(c.unit)] || {};
      const cNames = namesOf("chancery", c.unit);
      const cNotes = cDistrict.notes || [];
      const cLinks = await hrefs(page, "ms-chancery-court");
      check("ms-chancery-court names the Capitol's district, its chancellors and the vacancy the court's news reported, with that news as its link",
        ch.length === 1 && !cInfo.error && cNames.length > 0 &&
          cInfo.text.includes(`${ord(c.unit)} Chancery District`) &&
          cNames.every((n) => cInfo.text.includes(n)) &&
          cNotes.every((n) => cInfo.text.includes(n.text) && cLinks.includes(n.url)) &&
          (judges.chancery.listUpdated ? /where these names come from/i.test(cInfo.text) : true),
        `features here=${ch.length} notes=${cNotes.length} ${cInfo.text.slice(0, 160)}`);

      const r = ci[0] || {}, r27 = ci27[0] || {};
      const gains = (r27.counties || []).filter((n) => !(r.counties || []).includes(n));
      const rInfo = await cardText(page, "ms-circuit-court");
      const rNames = namesOf("circuit", r.unit);
      const change = `The ${ord(r27.unit)} Circuit District takes in ${countyPhrase(gains)}.`;
      check("ms-circuit-court names the Capitol's district and its judges, and says which counties it takes in on 1 January 2027",
        ci.length === 1 && ci27.length === 1 && String(r.unit) === String(r27.unit) && gains.length > 0 &&
          !rInfo.error && rNames.length > 0 &&
          rInfo.text.includes(`${ord(r.unit)} Circuit District`) &&
          rNames.every((n) => rInfo.text.includes(n)) && rInfo.text.includes(change) &&
          rInfo.text.includes("filled at the election of 3 November 2026"),
        `features here=${ci.length}/${ci27.length} want "${change}" ${rInfo.text.slice(0, 160)}`);
      await context.close();
    }

    {
      const r = propsAt(maps.circuit, CLAIBORNE)[0] || {};
      const r27 = propsAt(maps.circuit2027, CLAIBORNE)[0] || {};
      const c = propsAt(maps.chancery, CLAIBORNE)[0] || {};
      const c27 = propsAt(maps.chancery2027, CLAIBORNE)[0] || {};
      const ends = !maps.circuit2027.features.some((f) => String(f.properties.unit) === String(r.unit));
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${CLAIBORNE}&layers=ms-chancery-court,ms-circuit-court`);
      const rInfo = await cardText(page, "ms-circuit-court");
      const rNames = namesOf("circuit", r.unit);
      const moves = `This point is in the ${ord(r27.unit)} Circuit District: ${countyPhrase(r27.counties || [])}.`;
      const gone = `There is no ${ord(r.unit)} Circuit District from that day.`;
      check("in Claiborne County the circuit card names today's district and its judge, the district it moves to, and that today's district ends",
        String(r.unit) !== String(r27.unit) && ends && !rInfo.error && rNames.length > 0 &&
          rInfo.text.includes(`${ord(r.unit)} Circuit District`) &&
          rNames.every((n) => rInfo.text.includes(n)) &&
          rInfo.text.includes(moves) && rInfo.text.includes(gone),
        `today=${r.unit} 2027=${r27.unit} ends=${ends} ${rInfo.text.slice(0, 200)}`);
      const cInfo = await cardText(page, "ms-chancery-court");
      const cMoves = `This point is in the ${ord(c27.unit)} Chancery District: ${countyPhrase(c27.counties || [])}.`;
      check("in Claiborne County the chancery card says which chancery district the point moves to on 1 January 2027",
        String(c.unit) !== String(c27.unit) && !cInfo.error &&
          cInfo.text.includes(`${ord(c.unit)} Chancery District`) && cInfo.text.includes(cMoves) &&
          !cInfo.text.includes(`There is no ${ord(c.unit)} Chancery District`),
        `today=${c.unit} 2027=${c27.unit} ${cInfo.text.slice(0, 200)}`);
      await context.close();
    }

    {
      const r27 = propsAt(maps.circuit2027, CLAIBORNE)[0] || {};
      const c27 = propsAt(maps.chancery2027, CLAIBORNE)[0] || {};
      const s = propsAt(maps.supreme, CLAIBORNE)[0] || {};
      const asked = [];
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${CLAIBORNE}&layers=${ALL}`, async (pg) => {
        await pg.clock.setFixedTime(new Date("2027-01-02T12:00:00Z"));
        pg.on("request", (q) => asked.push(q.url()));
      });
      const rInfo = await cardText(page, "ms-circuit-court");
      const cInfo = await cardText(page, "ms-chancery-court");
      const sInfo = await cardText(page, "ms-supreme-court");
      const nobody = (info, court) => allNames(court).filter((n) => info.text.includes(n));
      const fetched = (re) => asked.some((u) => re.test(u));
      const today = fetched(/\/ms-(circuit|chancery)-court-districts\.json/);
      const later = fetched(/\/ms-circuit-court-districts-2027\.json/) && fetched(/\/ms-chancery-court-districts-2027\.json/);
      const redrawn = /These districts were redrawn on 1 January 2027/;
      check("on 2 January 2027 the trial courts draw the 2027 maps, never fetch today's, and name nobody from lists of the earlier districts",
        later && !today && !rInfo.error && !cInfo.error &&
          rInfo.text.includes(`${ord(r27.unit)} Circuit District`) &&
          cInfo.text.includes(`${ord(c27.unit)} Chancery District`) &&
          redrawn.test(rInfo.text) && redrawn.test(cInfo.text) &&
          nobody(rInfo, "circuit").length === 0 && nobody(cInfo, "chancery").length === 0 &&
          !/from 1 january 2027/i.test(rInfo.text) && !rInfo.text.includes("3 November 2026"),
        `2027 files=${later} today's files=${today} named=${nobody(rInfo, "circuit").slice(0, 2)} ${rInfo.text.slice(0, 160)}`);
      const sNames = namesOf("supreme", s.unit);
      check("on 2 January 2027 the Supreme Court card still names its justices",
        !sInfo.error && sNames.length === 3 && sNames.every((n) => sInfo.text.includes(n)),
        sInfo.text.slice(0, 120));
      await context.close();
    }

    {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=${ALL}`, async (pg) => {
        await pg.route("**/data/app/ms-judge-roster.json", (q) => q.fulfill({ status: 503, body: "down" }));
      });
      const cards = [
        ["ms-supreme-court", "supreme", `Supreme Court District ${(sc[0] || {}).unit}`],
        ["ms-court-of-appeals", "appeals", "Court of Appeals District"],
        ["ms-chancery-court", "chancery", `${ord((ch[0] || {}).unit)} Chancery District`],
        ["ms-circuit-court", "circuit", `${ord((ci[0] || {}).unit)} Circuit District`],
      ];
      const bad = [];
      for (const [id, court, title] of cards) {
        const info = await cardText(page, id);
        const named = allNames(court).filter((n) => info.text.includes(n));
        if (info.error || !info.text.includes(title) || !/did not load/.test(info.text) || named.length) {
          bad.push(`${id}: ${named.length ? "named " + named[0] : info.text.slice(0, 80)}`);
        }
      }
      check("every court card still names its district, and names nobody, when the list of judges fails",
        bad.length === 0, bad.join(" | "));
      await context.close();
    }
  }

  // ---- Tribal Government. The Mississippi Choctaw Reservation's card names
  // the band, its seat, the Tribal Chief and the council members with the
  // community each represents, from the band's own page; the districts
  // sentence points at those community names rather than saying no council
  // seat belongs to the land, which would be false here. A point off tribal
  // land is told so in the layer's own words. The point is shapely's
  // representative point of the shipped reservation's part in Neshoba County
  // (2026-10-15).
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
    const c = await at("32.79497,-89.25493");
    const districts = c.by("Districts drawn here");
    check("the Mississippi Choctaw Reservation names the band, its seat, its Chief and its council by community",
          c.by("Tribal government") === "Mississippi Band of Choctaw Indians" &&
          c.by("Seat of government") === "Choctaw, MS" &&
          c.by("Land") === "Mississippi Choctaw Reservation" &&
          c.text.indexOf("Cyrus Ben") !== -1 &&
          c.text.indexOf("Tribal Chief and Tribal Council") !== -1 &&
          c.text.indexOf("Bogue Chitto") !== -1 &&
          c.text.indexOf("From the nation's own council page") !== -1 &&
          districts.indexOf("beside their name below") !== -1 &&
          districts.indexOf("no council seat") === -1 &&
          !c.by("Why no names"),
          JSON.stringify(c.text.slice(0, 200)));
    const off = await at(POINT);
    check("a point off tribal land is told so in the layer's own words",
          off.text.indexOf("not on tribal land") !== -1 && off.text.indexOf("2 tribal areas") !== -1,
          JSON.stringify(off.text.slice(0, 120)));
    await context.close();
  }

  // 12. THE MAYOR AND COUNCIL OF THE 15 CITIES OF 25,000 PEOPLE OR MORE, AND
  //     THE WARDS OF NINE. Every name expected is read from the shipped
  //     roster (data/app/ms-city-councils.json) and every ward from the
  //     shipped ward file (data/app/ms-city-wards.json) at the point, so a
  //     rebuild moves the expectation with the files; what is asserted is
  //     that each card agrees with them and says where they come from.
  //       - The City card in Jackson (the place query stubbed, as in 7) names
  //         the mayor and every member by seat, says when the city's page was
  //         read, links the mayor's page and, in its footer, the council's,
  //         and says the City Ward layer draws Jackson's wards. In Biloxi,
  //         whose wards are not drawn, it says so.
  //       - Greenville's names nobody and says why; a roster that fails to
  //         load leaves the place standing and says no name is shown.
  //       - The City Ward card at the Capitol names its ward, the ward's
  //         member and whose map the line is, and links the city's ward-map
  //         page and the council page.
  //       - Where Oxford's own map draws two wards over one spot it names
  //         both. The point is shapely's polylabel of the largest Ward 2 /
  //         Ward 4 sliver in the drawn file, 2.5 m from its edge (2026-10-17).
  //       - In Biloxi, whose wards are not drawn, the card says which nine
  //         cities' wards are.
  {
    const councils = JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "app", "ms-city-councils.json"), "utf8"));
    const wards = JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "app", "ms-city-wards.json"), "utf8"));
    function inRing(x, y, ring) {
      let inside = false;
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i], [xj, yj] = ring[j];
        if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
      }
      return inside;
    }
    function wardsAt(point) {
      const [lat, lng] = point.split(",").map(Number);
      return wards.features.filter((f) => {
        const g = f.geometry;
        const polys = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
        return polys.some((rings) => rings.reduce((acc, ring) => acc !== inRing(lng, lat, ring), false));
      }).map((f) => f.properties);
    }
    const memberOf = (p) => ((councils[p.geoid] || {}).seats || []).find((s) => s.seat === p.seat) || {};
    const placeBody = (props) => JSON.stringify({
      geometryType: "esriGeometryPolygon", spatialReference: { wkid: 4326 },
      fields: Object.keys(props).map((n) => ({ name: n, type: "esriFieldTypeString", alias: n })),
      features: [{ attributes: props,
                   geometry: { rings: [[[-91, 31.5], [-89.5, 31.5], [-89.5, 33], [-91, 33], [-91, 31.5]]] } }]
    });
    const links = (page, id) => page.evaluate((cid) => {
      const el = document.getElementById("card-" + cid);
      const block = el && el.closest(".layer-block");
      return {
        body: el ? Array.from(el.querySelectorAll("a[href]")).map((a) => a.href) : [],
        footer: block ? Array.from(block.querySelectorAll(".card-footer a[href]")).map((a) => a.href) : []
      };
    }, id);
    const cityAt = async (props, routeExtra) => {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${POINT}&layers=municipality`, async (pg) => {
        await pg.route("**/Places_CouSub_ConCity_SubMCD/MapServer/4/query**", (r) =>
          r.fulfill({ status: 200, contentType: "application/json", body: placeBody(props) }));
        if (routeExtra) await routeExtra(pg);
      });
      const info = await cardText(page, "municipality");
      const got = await links(page, "municipality");
      await context.close();
      return { text: info.text || "", error: info.error, links: got };
    };

    {
      const j = councils["2836000"];
      const c = await cityAt({ GEOID: "2836000", NAME: "Jackson city", BASENAME: "Jackson", STATE: "28", LSADC: "25", FUNCSTAT: "A" });
      const names = j.seats.filter((s) => s.name).map((s) => s.name);
      const missing = names.filter((n) => !c.text.includes(n));
      check("the City card in Jackson names the mayor and every council member by seat, says when the city's page was read, and links the mayor's and the council's pages",
        !c.error && names.length === j.seats.length && missing.length === 0 &&
          /Mayor/.test(c.text) && /Ward 7/.test(c.text) &&
          /as Jackson's own website named them on \d{1,2} [A-Z][a-z]+ \d{4}/.test(c.text) &&
          /Your ward/.test(c.text) && /The City Ward layer draws Jackson's wards/.test(c.text) &&
          !/Not named here/.test(c.text) &&
          c.links.body.includes(j.mayorUrl) && c.links.footer.includes(j.councilUrl),
        `missing=${missing} links=${JSON.stringify(c.links)} ${c.text.slice(0, 140)}`);
    }
    {
      const c = await cityAt({ GEOID: "2806220", NAME: "Biloxi city", BASENAME: "Biloxi", STATE: "28", LSADC: "25", FUNCSTAT: "A" });
      check("the City card in Biloxi, whose wards are not drawn, names its council and says this app does not draw its wards",
        !c.error && c.text.includes(councils["2806220"].seats[0].name) &&
          /This app does not draw Biloxi's wards/.test(c.text) && !/City Ward layer draws/.test(c.text),
        c.text.slice(0, 200));
    }
    {
      const c = await cityAt({ GEOID: "2829180", NAME: "Greenville city", BASENAME: "Greenville", STATE: "28", LSADC: "25", FUNCSTAT: "A" });
      check("the City card in Greenville names nobody and says the city's own website names no member",
        !c.error && /Your mayor and council: not named here/.test(c.text) &&
          /does not name its mayor or its council members/.test(c.text) &&
          !/Who these are/.test(c.text) && !/\bMayor\b/.test(c.text),
        c.text.slice(0, 200));
    }
    {
      const c = await cityAt({ GEOID: "2836000", NAME: "Jackson city", BASENAME: "Jackson", STATE: "28", LSADC: "25", FUNCSTAT: "A" },
        async (pg) => {
          await pg.route("**/data/app/ms-city-councils.json", (r) => r.fulfill({ status: 500, body: "down" }));
        });
      check("the City card still names the place, and names nobody, when the list of mayors and councils fails",
        !c.error && /Jackson city/.test(c.text) && /did not load, so no name is shown/.test(c.text) &&
          !c.text.includes(councils["2836000"].seats[0].name),
        c.text.slice(0, 160));
    }

    const wardCard = async (pt, routeExtra) => {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await booted(context, `${BASE}#point=${pt}&layers=city-ward`, routeExtra);
      const info = await cardText(page, "city-ward");
      const got = await links(page, "city-ward");
      await context.close();
      return { text: info.text || "", error: info.error, links: got };
    };
    {
      const at = wardsAt(POINT);
      const p = at[0] || {};
      const m = memberOf(p);
      const council = councils[p.geoid] || {};
      const c = await wardCard(POINT);
      check(`the City Ward card at the Capitol names ${p.city} ${p.seat}, its member and whose map the line is, and links the city's ward-map page and the council's page`,
        at.length === 1 && !c.error && !!m.name && c.text.includes(m.name) &&
          c.text.includes(String(p.seat)) && c.text.includes(`${p.city} ${council.body}`) &&
          /How this line is drawn/.test(c.text) && c.text.includes("Jackson Adopted Wards 2024") &&
          /as Jackson's own website named them on \d{1,2} [A-Z][a-z]+ \d{4}/.test(c.text) &&
          c.links.body.includes(p.sourceUrl) && c.links.footer.includes(council.councilUrl),
        `wards here=${at.length} links=${JSON.stringify(c.links)} ${c.text.slice(0, 160)}`);
    }
    {
      const OXFORD_TWO = "34.354137,-89.508531";
      const at = wardsAt(OXFORD_TWO);
      const names = at.map((p) => memberOf(p).name).filter(Boolean);
      const c = await wardCard(OXFORD_TWO);
      check("where Oxford's own map draws two wards over one spot, the City Ward card names both and both members",
        at.length === 2 && names.length === 2 && !c.error &&
          names.every((n) => c.text.includes(n)) &&
          /Ward 2 and Ward 4/.test(c.text) && /More than one ward here/.test(c.text),
        `wards here=${at.map((p) => p.seat)} ${c.text.slice(0, 160)}`);
    }
    {
      const BILOXI = "30.3958,-88.8853";
      const c = await wardCard(BILOXI);
      check("in Biloxi, whose wards are not drawn, the City Ward card says which nine cities' wards are",
        wardsAt(BILOXI).length === 0 && !c.error && /No ward is drawn at this point/.test(c.text) &&
          /nine of Mississippi's 15 cities/.test(c.text) && /Brandon/.test(c.text),
        c.text.slice(0, 160));
    }
    {
      const at = wardsAt(POINT);
      const p = at[0] || {};
      const c = await wardCard(POINT, async (pg) => {
        await pg.route("**/data/app/ms-city-councils.json", (r) => r.fulfill({ status: 500, body: "down" }));
      });
      check("the City Ward card still names the ward, and names nobody, when the list of mayors and councils fails",
        !c.error && c.text.includes(String(p.seat)) && /did not load, so no name is shown/.test(c.text) &&
          !c.text.includes(memberOf(p).name || "(none)"),
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
