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
const POINT = "42.04940,-92.90710"; // downtown Marshalltown, Marshall County
const OFFLINE = ["county", "us-house", "ia-senate", "ia-house", "county-supervisor", "school-district-unified"];
const EXPECT_DISTRICT = { "county": "Marshall County", "us-house": "4", "ia-senate": "26", "ia-house": "52", "county-supervisor": "At-large", "school-district-unified": "Marshalltown Community School District" };
const NEGATIVE_POINT = "43.65000,-93.37000"; // inside Minnesota (near Albert Lea), north of the Iowa land border (~43.50) and inside permalink_gate's maxLat (43.70) so the point is still selectable. IT CANNOT BE MOVED OUT OF A SIBLING'S STATE AND THAT IS MEASURED: sampling permalink_gate every 0.25 degrees and naming each point's state off TIGERweb, the ground it reaches outside Iowa's own ring is Minnesota, Wisconsin, Illinois, Missouri, Nebraska and South Dakota and nothing else — one live instance, one published dark, four states that could each take one later. Widening the gate to reach a seventh state would move a reader-facing "where we serve" bound to suit a test. So the point stays and the two checks that select it refuse ../fleet-outlines.json instead, which is what the pan hand-off reads; Iowa asserts nothing about fleet routing.
const APP_NAME = "districtry Iowa";
const EXPECT_LAYERS = 20;
// ==== GENERATED:END smoke-config ====
// Fork-specific smoke-test constants (the reference repo hoists its own set
// here). The template's CHI-scenario checks are dropped at build time, so the
// GAP_PROBE / MOVE_POINT / STRAGGLER_* names below are contract stubs — the
// span's consumers keep the names resolvable; grow real fixtures (and restore
// the corresponding checks from the reference repo's smoke_test.mjs) as this
// fork ships the layers they exercise.
const EXPORTS_NAME = "IowaExplorer";
const PORTAL_HOST = "data.invalid"; // must stay a non-empty hostname: an empty string would abort every request
// Geocoder type-ahead fixture: RAW carries an embedded unit the app's cleaner
// must strip to CLEANED; the Photon STUB answers only CLEANED, so the check
// proves the strip-and-retry path with no live network.
const GEOCODER_QUERY_RAW = "100 E Grand Ave Suite 200, Capital City";
const GEOCODER_UNIT_FRAGMENT = "Suite 200";
const GEOCODER_QUERY_CLEANED = "100 E Grand Ave, Capital City";
const GEOCODER_STUB_FEATURE = {
  type: "Feature",
  geometry: { type: "Point", coordinates: [-93.39, 41.94] },
  properties: {
    housenumber: "100",
    street: "E Grand Ave",
    city: "Capital City",
    state: "Iowa",
    postcode: "00000"
  }
};
// Contract stubs (their consuming checks are reference-fork scenarios,
// dropped from this template's body):
const GAP_PROBE = { county: "statewide", label: "Statewide", lat: 41.94, lng: -93.39 };
const MOVE_POINT = { lat: 0, lng: 0, district: "0" };
const STRAGGLER_FILE = "data/app/state-counties.json";
const STRAGGLER_POINT = "0,0";
// Layers expected to HIDE (not merely report no district) at NEGATIVE_POINT.
// The starter layers declare no coverage() test, so they all take the honest
// "no district here" branch instead.
//
// ZIP CODE IS THE ONE THAT HIDES, and it is checked here rather than left to
// validate_sources.py BECAUSE THE TEST IS OFFLINE. A ZCTA has no state field,
// so the layer's query carries no STATE='19' filter and outside Iowa the live
// fallback answers a neighbouring state's ZIP code — on ground every other
// statewide card here correctly declines. What keeps that from reaching a
// reader is the layer's coverage() test, which reads the shipped state outline
// (same-origin, cache-first) and needs no third party at all, so the browser
// can prove it in both directions: hidden at the negative point (2b) and NOT
// hidden at the anchor (2a2). Both halves are needed — a hide test alone passes
// for a layer that is hidden everywhere.
const NEGATIVE_HIDDEN = ["zip-code"];
// The ids checked at the negative point: the offline anchors plus every
// coverage-declaring layer above, deduped in case one is already an anchor.
const NEGATIVE_IDS = OFFLINE.concat(NEGATIVE_HIDDEN.filter((id) => !OFFLINE.includes(id)));
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
    // THE FLEET FILE IS REFUSED FOR THE WHOLE OF THIS CHECK, because its
    // coverage-band half selects NEGATIVE_POINT and setSelectedPoint PANS
    // there, which puts the map's CENTRE outside Iowa and arms the pan
    // hand-off (ENGINE metro-portal's moveend → placeOwner → offerMetroPortal,
    // which sets window.location.href). Iowa's negative point is in Minnesota
    // and every other point it could be is in a sibling too — see the measured
    // note on NEGATIVE_POINT at the top of this file — so the day mn/ enters
    // fleet-outlines.json this check would navigate to /mn/ mid-assertion.
    // Refused, placeOwner's own error leg answers "nobody", which is the
    // state this check is about.
    // Iowa asserts nothing about fleet routing, so nothing else here needs it.
    const page = await booted(context, BASE, async (p) => {
      await p.route("**/fleet-outlines.json", (r) => r.abort());
    });
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

  // 2a2. THE OTHER HALF OF THE ZIP COVERAGE CHECK IN 2b. A hide test alone
  //      passes for a layer that is hidden everywhere, which would be a ZIP
  //      toggle no reader ever sees — so the anchor must show the same layer
  //      VISIBLE. Both halves read only the shipped state outline, with the
  //      census host refused, so neither depends on a government server being
  //      up.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=${NEGATIVE_HIDDEN.join(",")}`, async (p) => {
      await p.route("**tigerweb.geo.census.gov/**", (r) => r.abort());
    });
    for (const id of NEGATIVE_HIDDEN) {
      const visible = await page
        .waitForFunction((cid) => {
          const box = document.getElementById("toggle-" + cid);
          const block = box && box.closest(".layer-block");
          return !!block && block.hidden === false;
        }, id, { timeout: QUERY_TIMEOUT })
        .then(() => true, () => false);
      check(`${id} is in coverage at the Marshalltown anchor (not hidden)`, visible, `visible=${visible}`);
    }
    await context.close();
  }

  // 2a3. THE TOWNSHIP OFFICERS, BOTH BRANCHES, BECAUSE ONE ALONE PROVES
  //      NOTHING. Twelve counties publish their township clerks and trustees
  //      and about 1,400 townships are published by nobody, so the card has a
  //      named branch and a "not shown" branch — and a test of either half
  //      alone passes for a card that renders that half everywhere. The
  //      county-subdivision layer is point-first, so both points are selected
  //      with the census host LIVE (nothing else here can answer which
  //      township a point is in), and a failure to reach it reads as the
  //      check's own skip rather than as a wrong answer.
  //
  //      THE POINTS ARE THE CENSUS'S OWN GEOMETRY, not eyeballed: each is the
  //      ring centroid of a township the shipped roster names (Bath township
  //      in Cerro Gordo, which also publishes terms and whether each officer
  //      was elected or appointed) and of one it does not (Liscomb township in
  //      Marshall, the anchor county, which publishes no township page).
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    for (const [lat, lng, township, want, why] of [
      [43.03083, -93.19912, "Bath township", "Steve Sturges", "named by its county"],
      [42.18000, -92.95000, "Liscomb township", "Not shown", "named by nobody"]
    ]) {
      const page = await booted(context,
        `${BASE}#point=${lat},${lng}&layers=county-subdivision`);
      const info = await cardText(page, "county-subdivision");
      if (info.error || !info.text.includes(township)) {
        // the census host did not answer this township — say so rather than
        // failing on somebody else's server, the rule the tile checks follow
        console.log(`  SKIP  township officers, ${why} — card did not name ${township}`);
        await page.close();
        continue;
      }
      check(`township officers, ${why} (${township})`,
        info.text.includes(want), info.text.slice(0, 120));
      await page.close();
    }
    await context.close();
  }

  // 2a4. THE CITY COUNCILS OF THE FOURTEEN LARGEST CITIES THAT NAMED NOBODY,
  //      and the two SENTENCES the card says about them, because the names
  //      alone would pass for a card that says the wrong thing around them.
  //
  //      Iowa has eighteen cities above 25,000. Four were answered already
  //      and these fourteen published nothing, which was 96 officeholders a
  //      reader in them could not get from this app.
  //
  //      THREE CASES, AND EACH IS A DIFFERENT BRANCH OF THE SAME CARD. Ames
  //      names a mayor and six council members and must NOT carry the
  //      missing-mayor sentence; Davenport names ten aldermen and no mayor
  //      anywhere this project reads, and MUST carry it, or a reader takes a
  //      city with a mayor for a city without one; and a city in neither file
  //      must still reach the "Not shown" branch, because a test of the named
  //      half alone passes for a card that names somebody everywhere.
  //
  //      AMES' SEVENTH SEAT IS THE ONE WORTH ASSERTING BY NAME. Its council
  //      page links eight member pages and the eighth is the Iowa State
  //      ex-officio, whom the scraper drops; Bronwyn Beatty-Hansen is the
  //      council member a hyphen in her own URL slug lost from a first draft,
  //      so the card named six of seven seats and the loss was invisible in
  //      the copy around it.
  //
  //      The municipality layer answers from a committed vector-tile archive,
  //      so these three need no government server. A card that does not name
  //      the city at all is reported as this check's own skip rather than as
  //      a wrong answer, the rule 2a3 above already follows.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    for (const [lat, lng, city, want, absent, why] of [
      [42.03080, -93.63190, "Ames city", "Bronwyn Beatty-Hansen",
       "does not name its mayor", "names its mayor and six council members"],
      [41.52360, -90.57760, "Davenport city", "does not name its mayor",
       null, "names ten aldermen and no mayor"],
      [42.04940, -92.90710, "Marshalltown city", "Mike Ladehoff",
       "does not name its mayor", "the anchor city, mayor and seven members"],
      // AND A CITY IN NONE OF THE THREE ROSTERS, which is the half that keeps
      // the other three honest: 819 Iowa cities name nobody in this app, and
      // a check of the named branch alone passes for a card that names
      // somebody everywhere. Adel's own card must still reach the "Not shown"
      // branch, whose closing sentence this change also edited — it now
      // counts the largest cities from the shipped file rather than naming
      // three of them in prose.
      [41.61400, -94.02200, "Adel city", "Not shown", null,
       "a city named by nobody"]
    ]) {
      const page = await booted(context,
        `${BASE}#point=${lat},${lng}&layers=municipality`);
      const info = await cardText(page, "municipality");
      if (info.error || !info.text.includes(city)) {
        console.log(`  SKIP  city council, ${why} — card did not name ${city}`);
        await page.close();
        continue;
      }
      check(`city council, ${why}`,
        info.text.includes(want), info.text.slice(0, 160));
      if (absent) {
        // THE HALF THAT KEEPS THE FIRST HONEST. A missing-mayor sentence on a
        // city that names its mayor is the same false statement pointing the
        // other way.
        check(`city council, ${why} — no missing-mayor sentence`,
          !info.text.includes(absent), info.text.slice(0, 160));
      }
      await page.close();
    }
    await context.close();
  }

  // 2a5. THE FOUR COUNTY BOARDS NAMED BY THE COUNTY ITSELF, and the sentence
  //      the card says about why, because the names alone would pass for a
  //      card that credits the wrong publisher.
  //
  //      Almost every Iowa county's supervisors come from one statewide
  //      directory, gated against the districts this app draws. Where those
  //      two disagree the whole board is WITHHELD rather than guessed, which
  //      is right and left eight counties of 99 naming nobody. For four of
  //      them the county's own board page settles it, so those names rest on
  //      a publisher no other county's do and the card says so.
  //
  //      BOTH BRANCHES, for the reason 2a4 already gives. Adair must name a
  //      supervisor AND carry the county-named sentence; Pottawattamie must
  //      carry the withheld sentence and NOT the county-named one, because a
  //      county-named line over a board we do not publish would credit a
  //      page we were refused; and Marshall, the anchor county, comes from the
  //      statewide directory like the other 95 and must name a supervisor with
  //      NO county-named sentence at all -- which is the half that keeps the
  //      first honest, since a sentence rendered for every county says nothing.
  //
  //      The county layer answers from a committed archive, so none of these
  //      needs a government server. A card that does not name the county is
  //      this check's own skip, the rule 2a3 and 2a4 already follow.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    for (const [lat, lng, county, want, absent, why] of [
      [41.33000, -94.47000, "Adair County", "Named by the county",
       null, "Adair, named by the county's own page"],
      [41.33000, -94.47000, "Adair County", "Jerry Walker",
       null, "Adair names a supervisor the statewide directory lost"],
      [41.23000, -95.850000, "Pottawattamie County", "Not shown",
       "Named by the county", "Pottawattamie, withheld and not credited"],
      [42.04940, -92.90710, "Marshall County", "Supervisor",
       "Named by the county", "Marshall, from the statewide directory"]
    ]) {
      const page = await booted(context,
        `${BASE}#point=${lat},${lng}&layers=county`);
      const info = await cardText(page, "county");
      if (info.error || !info.text.includes(county)) {
        console.log(`  SKIP  county board, ${why} — card did not name ${county}`);
        await page.close();
        continue;
      }
      check(`county board, ${why}`,
        info.text.includes(want), info.text.slice(0, 200));
      if (absent) {
        check(`county board, ${why} — no county-named sentence`,
          !info.text.includes(absent), info.text.slice(0, 200));
      }
      await page.close();
    }
    await context.close();
  }


  // 2a6. WHOSE NUMBERING HAS BEEN CHECKED, AND WHOSE HAS NOT.
  //      This instance joins a supervisor to a district by NUMBER, and on
  //      2026-10-01 that number turned out not to be the same number: the
  //      Legislative Services Agency's statewide layer orders each county's
  //      districts its own way, and of the first four counties measured THREE
  //      disagreed with their own county's page. Butler and Pocahontas were
  //      live naming supervisors in the wrong districts. So a county's board is
  //      keyed only where somebody has measured the pairing
  //      (NUMBERING_CHECKED in ia/scripts/build_ia_supervisor_roster.py), and
  //      every other county keeps its supervisors on the County card, unkeyed.
  //
  //      POCAHONTAS IS THE ROW THAT MATTERS, because its map is a real
  //      permutation rather than the identity: the county's District 5 is this
  //      layer's district 4. A point in Fonda is in this layer's district 4 and
  //      must name Louis Stauter, whom the county calls its District 5
  //      supervisor -- and must NOT name Brent Aden, who is the county's
  //      District 4 and is exactly who a regression dropping the remap would
  //      print. Both branches are asserted, because a card naming a real
  //      supervisor of the right county reads perfectly either way.
  //
  //      HOWARD IS THE IDENTITY CASE and Washington is the withheld one. A
  //      county whose numbering is unchecked must name NOBODY here: its card
  //      answers the district and leaves the person to the County card. That
  //      is the half that keeps the first two honest -- a regression that
  //      simply keyed every county again would pass the Pocahontas row only by
  //      accident and would fail this one outright.
  //
  //      Every point is a published place centroid and every layer answers
  //      from committed files, so none of this needs a government server.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    for (const [lat, lng, county, want, absent, why] of [
      // EACH CASE ASSERTS THE NUMBER AND THE PERSON TOGETHER, as one string,
      // because they are one claim: the card heads itself with the number the
      // COUNTY uses and names the supervisor who holds that district. Asserted
      // apart, a card could pass with the right person under the layer's own
      // number, which is the state this check exists to refuse. The `absent`
      // string is the same pairing under the layer's number.
      [42.5816991, -94.8455189, "Pocahontas County",
       "District 5 Louis Stauter", "District 4 Louis Stauter",
       "Pocahontas, whose District 5 is this layer's 4"],
      [42.847502, -94.8479386, "Pocahontas County",
       "District 2 Clarence J. Siepker", "District 1 Clarence J. Siepker",
       "Pocahontas, whose District 2 is this layer's 1"],
      [43.3717458, -92.1162868, "Howard County", "District 1 Pat Murray", null,
       "Howard, whose own numbering matches this layer's"],
      // Monona, measured off its own map's TEXT rather than its drawing: the
      // county's District 1 is this layer's 2, so Ashton township is District 1
      // and Bo Fox, and Maple township is District 2 and Tom Brouillette. The
      // numbers were the other way round, with the names swapped, until
      // 2026-10-01.
      [42.0889412, -96.0903664, "Monona County",
       "District 1 Bo Fox", "District 2 Bo Fox",
       "Monona, whose District 1 is this layer's 2"],
      [42.1682353, -95.8542875, "Monona County",
       "District 2 Tom Brouillette", "District 1 Tom Brouillette",
       "Monona, whose District 2 is this layer's 1"],
      // Lyon, measured off the county's own precinct numbers against this
      // instance's own precinct layer: NOT ONE of its five numbers agrees. The
      // town of Lester is the county's District 1 and Douglas Bosch; this
      // layer calls that ground district 5.
      [43.4402929, -96.3314163, "Lyon County",
       "District 1 Douglas Bosch", "District 5 Douglas Bosch",
       "Lyon, whose District 1 is this layer's 5"],
      [43.3418726, -96.0032567, "Lyon County",
       "District 3 Cory Altena", "District 1 Cory Altena",
       "Lyon, whose District 3 is this layer's 1"],
      // Three counties whose own numbering was measured on 2026-10-06 and
      // AGREES with this layer's, so there is no wrong-number string to
      // refuse. Each point is a census interior point (Ida's Galva and
      // Washington's English River townships, each wholly inside one
      // district) or, for Polk, a point inside the county's own published
      // district polygon.
      [42.5216338, -95.4369572, "Ida County", "District 1 Creston Schubert",
       null, "Ida, whose numbering agrees with this layer's"],
      [41.466843, -91.7090319, "Washington County", "District 2 Bob Yoder",
       null, "Washington, whose numbering agrees with this layer's"],
      [41.629118, -93.639423, "Polk County", "District 5 Angela Connolly",
       null, "Polk, whose numbering agrees with this layer's"],
      // Adams was the withheld case below until 2026-10-08, when the
      // county's own district map showed its numbering agrees with this
      // layer's; the same point now names the district's supervisor.
      [41.0216555, -94.6969059, "Adams County", "District 2 Tony Hardisty",
       null, "Adams, whose numbering agrees with this layer's"],
      // THE WITHHELD BRANCH. Madison County's numbering has not been
      // measured, so its district card names nobody at all -- not the
      // supervisor its own page puts in the district of this number, not
      // anyone. Its supervisors are still on the County card. (Washington
      // and then Adams were this case until their numbering was checked.)
      // The point is an interior point of this layer's Madison district 1.
      [41.3280415, -94.141708, "Madison County", "District",
       "Heather Stancil",
       "Madison, unchecked, names nobody on a district card"]
    ]) {
      const page = await booted(context,
        `${BASE}#point=${lat},${lng}&layers=county-supervisor`);
      const info = await cardText(page, "county-supervisor");
      if (info.error || !info.text.includes(county)) {
        console.log(`  SKIP  supervisor district, ${why} — card did not name ${county}`);
        await page.close();
        continue;
      }
      check(`supervisor district, ${why}`,
        info.text.includes(want), info.text.slice(0, 200));
      if (absent) {
        check(`supervisor district, ${why} — the other county's number`,
          !info.text.includes(absent), info.text.slice(0, 200));
      }
      await page.close();
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
    const page = await booted(context, `${BASE}#point=${NEGATIVE_POINT}&layers=${NEGATIVE_IDS.join(",")}`, async (p) => {
      await p.route(`**${PORTAL_HOST}**`, (r) => r.abort());
      // And the census host, for the ZIP layer in NEGATIVE_IDS. Its coverage
      // test reads the shipped state outline and never the census, so the hide
      // verdict is identical either way — aborting it is what keeps this
      // check's verdict independent of whether a runner can reach TIGERweb.
      await p.route("**tigerweb.geo.census.gov/**", (r) => r.abort());
      // And the fleet file, for the reason given on the coverage-band check
      // above: this permalink pans the map's centre into Minnesota, so once a
      // sibling covers it the pan hand-off navigates away mid-assertion.
      await p.route("**/fleet-outlines.json", (r) => r.abort());
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
