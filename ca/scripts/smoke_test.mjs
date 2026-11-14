// Headless boot smoke test — SF Thread-5 (pipeline: legislative geometry + rosters).
// Serves the real index.html and drives it in Chromium via Playwright
// (.github/workflows/smoke-test.yml on every PR). Asserts both the network-free
// deliverables and the offline classification: the app boots on the SF map,
// registers EXPECT_LAYERS layers with no console errors, is SF-branded, and
// degrades a base-map tile outage to a dismissible banner; the three offline
// anchors (supervisor / neighborhood / police-district) classify SF City Hall
// against the ground truth from same-origin data/app files, and the negative Bay
// point honestly reports no district (never snaps to nearest); the three
// legislative chambers (U.S. House / CA Senate / CA Assembly) classify City Hall
// from pre-built, SF-clipped same-origin geometry AND name the officeholder from
// a scraped same-origin roster. The ZIP stub and the station + schools layers
// remain live DataSF/TIGERweb — not reachable from CI/sandbox — so they are
// asserted present (registered) only (this gate is re-derived each thread —
// docs/METRO_EXPANSION_PLAYBOOK.md §9).
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

// Vendored Leaflet fallback for sandboxed environments (Claude Code web), where
// Chromium cannot reach cdnjs.cloudflare.com (it does not use the agent HTTPS
// proxy, so the request resets and the app never boots — "L is not defined").
// The repo-root scripts/vendor_leaflet.sh populates this dir via curl, which *can*
// reach the CDN
// through the proxy; when present we serve Leaflet same-origin below. Absent
// (production, GitHub Actions CI) the browser loads Leaflet from the CDN as before.
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

// Disk reads are anchored to THIS SCRIPT, never to the process CWD. While each
// instance was its own repo, "data/app/…" was correct because you ran the smoke
// test from that repo's root. They are folders under one root now, and a bare
// relative read silently resolves against whatever directory you happen to be
// in — which is how the SF run died on `ENOENT: data/app/coverage-gaps.json`
// while the app itself booted fine. Anchoring costs one line and cannot drift.
const INSTANCE_DIR = dirname(dirname(fileURLToPath(import.meta.url)));

const BASE = process.env.BASE_URL || "http://localhost:8000/";
// ==== GENERATED:BEGIN smoke-config ====
const POINT = "37.77927,-122.41924"; // SF City Hall (Civic Center)
const OFFLINE = ["supervisor-district", "neighborhood", "police-district"];
const EXPECT_DISTRICT = { "supervisor-district": "5", "neighborhood": "Tenderloin", "police-district": "NORTHERN" };
const NEGATIVE_POINT = "32.40000,-115.60000"; // The Mexicali Valley in Mexico, about 15 km south of the border at Calexico — outside California and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-11 against TIGERweb's state layer (controls: San Francisco City Hall returns California, and Mexicali, Baja California, returns no state). IT IS IN ANOTHER COUNTRY, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.
const APP_NAME = "districtry California";
const EXPECT_LAYERS = 23; // Thread-5: legislative chambers now pre-built SF-clipped geometry (data/app); supervisor-district is a bespoke roster-joined registerLayer; 11 layers total; + 3 amenity nearest-point layers (post-office, library, early-voting) = 14; + bart-director + election-precinct (parity-debt closures, 2026-07) = 16; + election-results (2026-11) = 17; + county, municipality and the three school district tilings when the app grew to the whole state (2026-11) = 22; + tribal-government (2026-11-12) = 23
// ==== GENERATED:END smoke-config ====
const EXPORTS_NAME = "SFExplorer"; // the fork's window debug namespace
const BOOT_TIMEOUT = 45000; // Leaflet + first paint on a cold CI runner
const QUERY_TIMEOUT = 25000;

const failures = [];
function check(name, ok, detail) {
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);
  if (!ok) failures.push(name);
}

function routeLeaflet(page) {
  const routes = [];
  if (VENDORED_LEAFLET) {
    routes.push(
      page.route("**/cdnjs.cloudflare.com/**/leaflet.js", (r) =>
        r.fulfill({ status: 200, contentType: "application/javascript", body: VENDORED_LEAFLET.js })),
      page.route("**/cdnjs.cloudflare.com/**/leaflet.css", (r) =>
        r.fulfill({ status: 200, contentType: "text/css", body: VENDORED_LEAFLET.css })));
  }
  if (VENDORED_MAPLIBRE) {
    routes.push(
      page.route("**/cdnjs.cloudflare.com/**/maplibre-gl.min.js", (r) =>
        r.fulfill({ status: 200, contentType: "application/javascript", body: VENDORED_MAPLIBRE.js })));
  }
  return Promise.all(routes);
}

// Redesigned cards (engine-v1.0.10, docs/CARD_RENDER_API.md in the reference
// fork) render a .card-flush body and move the district identifier into the
// header pill (.card-id-pill), so completion accepts either card generation
// and the returned text prepends the pill — the "District N" assertions read
// the whole card, not just the body, exactly as a user does. Backward
// compatible: with no pill (pre-bump engine) this reads the body alone.
async function cardText(page, id) {
  await page.waitForFunction((cid) => {
    const el = document.getElementById("card-" + cid);
    return el && !el.querySelector(".loading-row") &&
      (el.querySelector(".result-fields") || el.querySelector(".card-flush") ||
       el.querySelector(".state-empty") ||
       // 4b compact cards (docs/CARD_RENDER_API.md): render() is skipped on
       // success and the body goes state-compact (hidden) — the result lives
       // in the header .card-compact-value instead, so accept that as done.
       el.classList.contains("state-compact") ||
       el.classList.contains("state-empty") || el.classList.contains("state-error") || el.querySelector(".state-error"));
  }, id, { timeout: QUERY_TIMEOUT }).catch(() => {});
  return page.evaluate((cid) => {
    const el = document.getElementById("card-" + cid);
    if (!el) return { text: "(no card)", error: true, empty: false };
    const block = el.closest(".layer-block");
    const pill = block && block.querySelector(".card-id-pill:not([hidden])");
    // a compact card carries its identity in the header value/meta, not the
    // (hidden) body — prepend those the same way the pill is prepended, so
    // the "District N" / neighborhood-name assertions read the whole card.
    const cv = block && block.querySelector(".card-compact-value:not([hidden])");
    const cm = block && block.querySelector(".card-compact-meta:not([hidden])");
    const head = [pill, cv, cm].filter(Boolean).map((n) => n.textContent).join(" ");
    const text = (head ? head + " " : "") + el.innerText;
    return {
      text: text.replace(/\s+/g, " ").trim(),
      error: el.classList.contains("state-error") || !!el.querySelector(".state-error"),
      empty: el.classList.contains("state-empty") || !!el.querySelector(".state-empty"),
    };
  }, id);
}

const browser = stubBasemap(await chromium.launch());
try {
  // 1. App boots on the SF map with the Thread-5 layers, SF-branded, clean console.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage();
    const consoleErrors = [];
    page.on("console", (m) => {
      if (m.type() !== "error") return;
      const t = m.text();
      // Ignore sandbox network unreachability — the CARTO basemap tiles (and, absent
      // the vendored fallback, the Leaflet CDN) aren't routable from CI/sandbox. We
      // care about *app* JS errors (a dangling ref surfaces as a pageerror below).
      if (/Failed to load resource|net::ERR|cartocdn|cdnjs\.cloudflare|basemaps/i.test(t)) return;
      consoleErrors.push(t);
    });
    page.on("pageerror", (e) => consoleErrors.push(String(e)));
    await routeLeaflet(page);
    await page.goto(BASE, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => !!window.SFExplorer, null, { timeout: BOOT_TIMEOUT });
    check("app boots (window.SFExplorer exported)", true);

    const n = await page.evaluate(() => document.querySelectorAll('input[type=checkbox][id^="toggle-"]').length);
    check(`${EXPECT_LAYERS} layer(s) registered`, n === EXPECT_LAYERS, `found ${n}`);

    const hasMap = await page.evaluate(() => {
      const m = document.getElementById("map");
      return !!m && m.classList.contains("leaflet-container") && !!m.querySelector(".leaflet-pane");
    });
    check("Leaflet map initialized", hasMap);

    const title = await page.title();
    // Asserted against the name the worksheet owns, not a literal: this check
    // was /San Francisco District Explorer/ and failed the districtry rebrand —
    // a gate rejecting a correct change. APP_NAME is generated from the same
    // brand block appDisplayName() reads at runtime.
    check("title carries the app's own name", title.includes(APP_NAME), `${title} | expected ${APP_NAME}`);

    const stubOk = await page.evaluate(() => !!document.getElementById("toggle-zip-code"));
    check("ZIP Code stub layer present", stubOk);

    // The station + schools layers are live DataSF — assert they register (a
    // toggle exists); their classification can't run without network egress.
    const safetyPtsOk = await page.evaluate(() =>
      !!document.getElementById("toggle-police-station") && !!document.getElementById("toggle-fire-station"));
    check("police + fire station layers present", safetyPtsOk);
    const schoolsOk = await page.evaluate(() =>
      !!document.getElementById("toggle-elementary-attendance-area") && !!document.getElementById("toggle-school-site"));
    check("elementary-zone + school-site layers present", schoolsOk);
    // (The three legislative chambers are asserted by offline classification in
    // block 2c below, now that their geometry is pre-built same-origin.)

    check("no console errors during boot", consoleErrors.length === 0, consoleErrors.slice(0, 2).join(" | "));

    if (process.env.SMOKE_SHOT) await page.screenshot({ path: process.env.SMOKE_SHOT });
    await context.close();
  }

  // 1a. The Data gaps panel: the honest inventory of what this app cannot answer,
  //     and the source-submission path (engine block `coverage-gaps`, shipped in
  //     engine-v1.0.19). Asserted because the panel is the one surface whose whole
  //     job is to be accurate about absence — a silently empty or truncated list is
  //     worse than no panel at all. Same-origin data, so this needs no network.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage();
    await routeLeaflet(page);
    await page.goto(BASE, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => !!window.SFExplorer, null, { timeout: BOOT_TIMEOUT });
    const shipped = JSON.parse(readFileSync(join(INSTANCE_DIR, "data/app/coverage-gaps.json"), "utf8"));
    const expected = Object.keys(shipped).length;
    // The COLD panel groups by kind, so its section count is the number of
    // distinct kinds in the shipped file — derived, never a constant. San
    // Francisco records three gaps and all three are `data-quality`, so a
    // hardcoded 1 passes here BY ACCIDENT and would go red the first time this
    // instance records a `blocked` or `no-source` gap — a failure with no
    // defect behind it. New York's warm check carried the same constant until
    // 2026-09-18 and its cold check until 2026-09-19; both went red exactly
    // that way. Fixed here before it fires, not after.
    const expectedKinds = new Set(Object.values(shipped).map((g) => g.kind)).size;

    // The button lives in the masthead, not the footer (ported from the CHI
    // reference fork). Pinned here because nothing else can see it: the fence
    // system pins the block's BYTES, never its placement, so an engine bump or
    // a refactor could quietly drag it back to the footer and every existing
    // check — which clicks it by id — would still pass.
    check("gaps button sits in the masthead, not the footer",
      await page.evaluate(() => !!document.querySelector("header.masthead #gaps-btn")));
    // The submission link is built from REPO_ISSUES, which is METRO config — so a
    // copy-paste of Chicago's value would quietly send this fork's readers to the
    // wrong issue tracker. Assert the host, not just the template.
    const repoIssues = JSON.parse(readFileSync(join(INSTANCE_DIR, "metro-worksheet.json"), "utf8")).repo_issues;

    async function openGaps() {
      await page.evaluate(() => { const m = document.getElementById("gaps-modal"); if (m) m.hidden = true; });
      await page.click("#gaps-btn");
      await page.waitForFunction(() => {
        const b = document.getElementById("gaps-body");
        return b && !/Loading/.test(b.textContent) && b.textContent.trim().length > 0;
      }, null, { timeout: QUERY_TIMEOUT }).catch(() => {});
      return page.evaluate(() => {
        const b = document.getElementById("gaps-body");
        return {
          items: b.querySelectorAll(".gap-item").length,
          lede: (b.querySelector(".gaps-lede") || {}).textContent || "",
          sections: Array.from(b.querySelectorAll(".gaps-section-label")).map((e) => e.textContent),
          hrefs: Array.from(b.querySelectorAll(".gap-suggest")).map((a) => a.getAttribute("href")),
        };
      });
    }

    const cold = await openGaps();
    check("data gaps panel renders every recorded gap",
      cold.items === expected && cold.sections.length === expectedKinds,
      `${cold.items}/${expected} items, ${cold.sections.length}/${expectedKinds} section(s)`);
    check("every gap offers a prefilled submission to THIS fork's repo",
      cold.hrefs.length === expected &&
      cold.hrefs.every((h) => h.startsWith(repoIssues) &&
        /template=source-submission\.yml/.test(h) && /[?&]gap_id=/.test(h)),
      `${cold.hrefs.length} links -> ${repoIssues}`);

    // Until 2026-11-11 this app shipped no county outlines, so no gap could be
    // matched to a point and selecting one left the list single-sectioned. Since
    // it grew to the whole state it ships San Francisco's outline, so the gaps
    // that name San Francisco lead under "Where you clicked" at City Hall and
    // every other gap is still listed below them: the count is derived from the
    // shipped file, never a constant.
    const sfGaps = Object.values(shipped).filter((g) => (g.counties || []).includes("san-francisco")).length;
    await page.evaluate((p) => window.SFExplorer.setSelectedPoint(p[0], p[1]),
      POINT.split(",").map(Number));
    const warm = await openGaps();
    check("selecting City Hall leads with the gaps recorded for San Francisco, and lists the rest",
      sfGaps > 0 && warm.items === expected && warm.sections.length >= 2 &&
        warm.sections[0] === "Where you clicked" + sfGaps,
      `${warm.items}/${expected} items, sections=${JSON.stringify(warm.sections)}`);

    // ==== TEMPLATE:BEGIN smoke-coverage-band ====
    // THIS INSTANCE PAINTS THREE BANDS SINCE 2026-11-11, AND THAT IS THE CLAIM
    // ASSERTED HERE. Until that day its coverage was the city and it handed
    // drawOutOfScopeMask no region, so the wash had two bands and this block
    // asserted the lede said "nothing there can be answered yet" beyond the city.
    // Since the app grew to the whole state it hands the state outline as its
    // region: San Francisco is the full coverage, the rest of California is the
    // middle band where the statewide layers answer, and the lede must say so
    // in Sacramento and must not say so in Mexico. Both points are asserted,
    // because the second keeps the first honest.
    //
    // IT WAITS FOR THE WASH FIRST, and for `dst-glow`, which is created only in
    // the branch that also retains the region. A null coverage test correctly
    // falls through to wording that claims neither, so a point selected before
    // the wash has loaded asserts against the app's "we cannot tell yet" state —
    // which is what CI caught on this check's first draft.
    async function washPainted() {
      return page.waitForFunction(() => {
        const pane = document.querySelector(".leaflet-pane.leaflet-scope-mask-pane");
        return !!(pane && pane.querySelector("path.dst-glow"));
      }, null, { timeout: QUERY_TIMEOUT }).then(() => true, () => false);
    }
    if (await washPainted()) {
      // THE PURPLE EDGE runs along the state line, and the key names it from
      // the worksheet's coverage_key.region.edge.
      const edge = await page.evaluate(() => {
        const sw = document.querySelector(".districtry-map-legend .dml-items .dml-glow");
        const label = sw && sw.parentElement.querySelector(".dml-label");
        return { label: label ? label.textContent : null };
      });
      check("the wash draws the purple edge along the state line, and the key names it",
        edge.label === "California", JSON.stringify(edge));
      await page.evaluate(() => window.SFExplorer.setSelectedPoint(38.5766, -121.4932));
      const band = await openGaps();
      check("gaps lede names the coverage band in Sacramento (statewide layers answer, city layers do not)",
        /inside California, outside the area this app covers in full/.test(band.lede) &&
        band.lede.indexOf("Statewide layers only") !== -1 &&
        !/nothing there can be answered yet/.test(band.lede), JSON.stringify(band.lede));
      await page.evaluate((p) => window.SFExplorer.setSelectedPoint(p[0], p[1]),
        NEGATIVE_POINT.split(",").map(Number));
      const beyond = await openGaps();
      check("gaps lede claims no coverage band at the negative point in Mexico",
        /nothing there can be answered yet/.test(beyond.lede) &&
        !/covers in full/.test(beyond.lede), JSON.stringify(beyond.lede));
    } else {
      check("the wash painted its region band, so the band wording can be read", false,
        "no dst-glow in the scope-mask pane — the region band never painted");
    }
    // ==== TEMPLATE:END smoke-coverage-band ====

    await context.close();
  }

  // 2. The three offline anchors classify City Hall against the ground truth,
  //    from same-origin data/app/*.json (deterministic — no live API).
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage();
    await routeLeaflet(page);
    await page.goto(`${BASE}#point=${POINT}&layers=${OFFLINE.join(",")}`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => !!window.SFExplorer, null, { timeout: BOOT_TIMEOUT });
    for (const id of OFFLINE) {
      const c = await cardText(page, id);
      const want = EXPECT_DISTRICT[id];
      check(`${id} classifies City Hall (${want})`, !c.error && c.text.includes(want), c.text.slice(0, 70));
    }
    await context.close();
  }

  // 2b. THE APP GREW FROM SAN FRANCISCO TO THE WHOLE STATE ON 2026-11-11, and
  //     two things must hold at once: the city's layers HIDE outside the city
  //     (coverage: inSanFrancisco), and the statewide layers ANSWER there. Both
  //     halves are asserted, because a hide test alone passes for a layer that
  //     is hidden everywhere and an answer test alone passes for a city layer
  //     that wrongly answers in Sacramento. Sacramento's Capitol is the point:
  //     every answer below comes from same-origin files (state-counties.json
  //     and the mirrored tile archives), so this needs no network.
  //     The negative point is in Mexico, so the ZIP layer (coverage:
  //     inCalifornia) hides there and the three chambers, which are statewide
  //     files with no coverage test, answer with no district.
  const SACRAMENTO = "38.57660,-121.49320"; // California State Capitol, 10th and L
  const hiddenAt = async (page, id) => {
    // wait for the coverage test's outline fetch before reading, the rule the
    // New York smoke test learned on a busy runner (PR #1513)
    await page.waitForFunction((cid) => {
      const card = document.getElementById("card-" + cid);
      const block = card && card.closest(".layer-block");
      return !!block && block.hidden === true;
    }, id, { timeout: QUERY_TIMEOUT }).catch(() => {});
    return page.evaluate((cid) => {
      const card = document.getElementById("card-" + cid);
      const block = card && card.closest(".layer-block");
      const visible = (el) => !!el && !el.hidden && el.offsetParent !== null;
      return { card: visible(block) };
    }, id);
  };
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage();
    await routeLeaflet(page);
    const SF_ONLY = OFFLINE.concat(["election-precinct", "elementary-attendance-area"]);
    await page.goto(`${BASE}#point=${SACRAMENTO}&layers=${SF_ONLY.concat(["county", "municipality", "zip-code"]).join(",")}`,
      { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => !!window.SFExplorer, null, { timeout: BOOT_TIMEOUT });
    for (const id of SF_ONLY) {
      const shown = await hiddenAt(page, id);
      check(`${id} hides in Sacramento, outside San Francisco`, !shown.card, JSON.stringify(shown));
    }
    for (const [id, want] of [["county", "Sacramento"], ["municipality", "Sacramento"], ["zip-code", "95814"]]) {
      const c = await cardText(page, id);
      check(`${id} answers in Sacramento (${want})`, !c.error && !c.empty && c.text.includes(want), c.text.slice(0, 70));
    }
    await context.close();
  }
  {
    // the anchor half: at City Hall the ZIP layer and the County card answer,
    // so a ZIP layer hidden everywhere cannot pass the Mexico check below
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage();
    await routeLeaflet(page);
    await page.goto(`${BASE}#point=${POINT}&layers=county,zip-code`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => !!window.SFExplorer, null, { timeout: BOOT_TIMEOUT });
    for (const [id, want] of [["county", "San Francisco"], ["zip-code", "94102"]]) {
      const c = await cardText(page, id);
      check(`${id} answers at City Hall (${want})`, !c.error && !c.empty && c.text.includes(want), c.text.slice(0, 70));
    }
    await context.close();
  }
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage();
    await routeLeaflet(page);
    const CHAMBERS = ["congress", "ca-senate", "ca-assembly"];
    await page.goto(`${BASE}#point=${NEGATIVE_POINT}&layers=${OFFLINE.concat(["zip-code"], CHAMBERS).join(",")}`,
      { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => !!window.SFExplorer, null, { timeout: BOOT_TIMEOUT });
    for (const id of OFFLINE.concat(["zip-code"])) {
      const shown = await hiddenAt(page, id);
      check(`${id} hides at the negative point in Mexico`, !shown.card, JSON.stringify(shown));
    }
    for (const id of CHAMBERS) {
      const c = await cardText(page, id);
      check(`${id} reports no district at the negative point in Mexico`, c.empty && !c.error, c.text.slice(0, 70));
    }
    await context.close();
  }

  // 2c. The three legislative chambers classify City Hall from pre-built,
  //     statewide same-origin geometry (data/app, SF-clipped until 2026-11-11),
  //     and name the officeholder from the scraped same-origin roster
  //     (data/app/*-members.json / roster). Their negative half is in 2b. The
  //     specific names change week to week, so we assert the member's ROLE
  //     label (proof a roster row joined), not a name.
  {
    const CHAMBERS = {
      "congress": { district: "11", role: "Representative" },
      "ca-senate": { district: "11", role: "State Senator" },
      "ca-assembly": { district: "17", role: "Assemblymember" },
    };
    const ids = Object.keys(CHAMBERS);
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage();
    await routeLeaflet(page);
    await page.goto(`${BASE}#point=${POINT}&layers=${ids.join(",")}`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => !!window.SFExplorer, null, { timeout: BOOT_TIMEOUT });
    for (const id of ids) {
      const c = await cardText(page, id);
      const { district, role } = CHAMBERS[id];
      // Roster-join proof, both card generations: the legacy dt/dd card
      // carries the role label ("State Senator") as its member row's label;
      // the redesigned card (engine-v1.0.10) renders the joined member as a
      // .card-person-name row instead — the office lives in the card title
      // and the badge shows party, so the role text is gone by design.
      const member = await page.evaluate((cid) => {
        const box = document.getElementById("toggle-" + cid);
        const block = box && box.closest(".layer-block");
        const name = block && block.querySelector(".card-person-name");
        return name ? name.textContent.trim() : null;
      }, id);
      check(`${id} classifies City Hall (District ${district}) + joins its ${role} roster`,
        !c.error && c.text.includes(district) && (!!member || c.text.includes(role)),
        `${c.text.slice(0, 60)} | member=${member}`);
    }
    await context.close();
  }

  // 2d. Election results: the card, the contest menu and the legend, held to
  //     the shipped files rather than to any count, because the numbers can
  //     move until the Department of Elections certifies them. At City Hall
  //     the card names precinct 7532, says unofficial while the file is not
  //     certified, and offers exactly the contests on this precinct's ballot;
  //     the legend names the picked contest and keys the five lead bands; a
  //     Supervisor contest picked in Noe Valley (District 8) becomes the
  //     Bayview's own District 10 contest when the point moves there.
  {
    const idx = JSON.parse(readFileSync(join(INSTANCE_DIR, "data/app/election-results.json"), "utf8"));
    const ballotOf = (key) => {
      const part = JSON.parse(readFileSync(join(INSTANCE_DIR, "data/app/election-results",
        idx.parts[idx.precincts.indexOf(key)] + ".json"), "utf8"));
      return part.precincts[key].contests.map((r) => String(r[0]));
    };
    const onBallot = ballotOf("7532");
    const firstOnBallot = idx.contests.find((c) => onBallot.includes(String(c.id)));
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage();
    await routeLeaflet(page);
    await page.goto(`${BASE}#point=${POINT}&layers=election-results`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => !!window.SFExplorer, null, { timeout: BOOT_TIMEOUT });
    await page.waitForFunction(() => {
      const c = document.getElementById("card-election-results");
      return c && c.querySelector(".election-table");
    }, null, { timeout: QUERY_TIMEOUT }).catch(() => {});
    const got = await page.evaluate(() => {
      const c = document.getElementById("card-election-results");
      const block = c && c.closest(".layer-block");
      const pill = block && block.querySelector(".card-id-pill");
      const sel = c && c.querySelector("select.election-select");
      const legend = document.querySelector(".election-legend");
      return {
        notice: ((c && c.querySelector(".election-notice")) || {}).textContent || "",
        pill: pill ? pill.textContent.trim() : "",
        options: sel ? Array.from(sel.options).map((o) => o.value) : [],
        legendShown: !!legend && !legend.hidden,
        legendRace: legend ? ((legend.querySelector(".election-legend-race") || {}).textContent || "") : "",
        legendSteps: legend ? legend.querySelectorAll(".election-legend-scale .election-legend-step").length : 0,
        rows: c ? c.querySelectorAll(".election-table tbody tr").length : 0,
        text: c ? c.textContent : "",
      };
    });
    const noticeOk = idx.certified ? got.notice.indexOf("certified") !== -1
      : got.notice.indexOf("Unofficial results") !== -1 &&
        got.notice.indexOf("San Francisco Department of Elections") !== -1;
    const menuOk = got.options.length === onBallot.length && got.options.every((v) => onBallot.includes(v));
    check("the Election Results card says unofficial and lists exactly this precinct's contests",
          noticeOk && menuOk && got.pill === "Precinct 7532" &&
          got.rows === firstOnBallot.choices.length && got.text.indexOf("Across San Francisco's precincts") !== -1 &&
          got.text.indexOf("counted outside any precinct") === -1,
          `notice=${JSON.stringify(got.notice.slice(0, 60))} options=${got.options.length}/${onBallot.length} ` +
          `pill=${JSON.stringify(got.pill)} rows=${got.rows}`);
    check("the Election Results legend names the picked contest and keys the five lead bands",
          got.legendShown && got.legendRace === firstOnBallot.name && got.legendSteps === 5,
          `shown=${got.legendShown} race=${JSON.stringify(got.legendRace)} steps=${got.legendSteps}`);
    const pillNow = async () => page.evaluate(() =>
      (document.querySelector("#card-election-results")?.closest(".layer-block")?.querySelector(".card-id-pill") || {}).textContent || "");
    const moveTo = async (la, ln) => {
      const was = (await pillNow()).trim();
      await page.evaluate(([a, b]) => window.SFExplorer.setSelectedPoint(a, b), [la, ln]);
      await page.waitForFunction((w) => {
        const pill = document.querySelector("#card-election-results")?.closest(".layer-block")?.querySelector(".card-id-pill");
        return pill && pill.textContent.trim() !== w && document.querySelector("#card-election-results .election-table");
      }, was, { timeout: QUERY_TIMEOUT }).catch(() => {});
    };
    await moveTo(37.7510, -122.4330); // Noe Valley, precinct 7833, Supervisor District 8
    const d8 = idx.contests.find((c) => c.group === "supervisor" && ballotOf("7833").includes(String(c.id)));
    await page.selectOption("#card-election-results select.election-select", String(d8.id));
    await page.waitForTimeout(300);
    await moveTo(37.7330, -122.3920); // the Bayview, precinct 7023, Supervisor District 10
    const moved = await page.evaluate(() => ({
      pill: (document.querySelector("#card-election-results")?.closest(".layer-block")?.querySelector(".card-id-pill") || {}).textContent || "",
      value: (document.querySelector("#card-election-results select.election-select") || {}).value || "",
      race: (document.querySelector(".election-legend .election-legend-race") || {}).textContent || "",
    }));
    const d10 = idx.contests.find((c) => c.group === "supervisor" && c.id !== d8.id && moved.value === String(c.id));
    check("a Supervisor contest picked in District 8 becomes District 10's own contest in the Bayview",
          !!d10 && moved.race === d10.name && moved.pill.trim() === "Precinct 7023",
          `from=${d8.name} pill=${JSON.stringify(moved.pill)} picked=${moved.value} race=${JSON.stringify(moved.race)}`);
    await context.close();
  }

  // 3. Base-map tile failure surfaces an honest, dismissible banner (engine behaviour).
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage();
    await routeLeaflet(page);
    // regex, not a glob: the tile host is `a.basemaps.cartocdn.com` (a dot, not a
    // slash, before `basemaps`), which a `**/basemaps…` glob would miss.
    await page.route(/basemaps\.cartocdn\.com/, (r) => r.fulfill({ status: 503, body: "down" }));
    await page.goto(BASE, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => !!window.SFExplorer, null, { timeout: BOOT_TIMEOUT });
    await page
      .waitForFunction(() => { const el = document.getElementById("tile-banner"); return el && !el.hidden; }, null, { timeout: QUERY_TIMEOUT })
      .catch(() => {});
    const shown = await page.evaluate(() => { const el = document.getElementById("tile-banner"); return !!el && !el.hidden; });
    let hiddenAfterDismiss = null;
    if (shown) {
      await page.click("#tile-banner-dismiss");
      hiddenAfterDismiss = await page.evaluate(() => { const el = document.getElementById("tile-banner"); return !!el && el.hidden; });
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
    const page = await context.newPage();
    await routeLeaflet(page);
    await page.goto(`${BASE}#point=${POINT}&layers=${OFFLINE[0]}`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction((n) => !!window[n], EXPORTS_NAME, { timeout: BOOT_TIMEOUT });
    await page.waitForFunction((n) => !!window[n] && !!window[n].setTheme,
      EXPORTS_NAME, { timeout: QUERY_TIMEOUT }).catch(() => {});
    const read = () => page.evaluate(({ n, id: OFFLINE0 }) => {
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
        // the anchor layer's own outline colour, read from the app: it is
        // drawn on the tile canvas since phase 5, so there is no SVG path.
        // Ported from scripts/smoke_test.mjs, where Illinois made exactly this
        // change when its layers moved to tiles; SF's copy was left reading
        // `#map path`, which returns whichever path is first in DOM order —
        // the selected-point marker (no `stroke` attribute, so null, and the
        // assertion short-circuits to a pass that measures nothing) or, once
        // the scope wash has painted, the mask (`stroke="none"` in both
        // themes, so a FAIL although its FILL is what the theme repaints).
        // Measured 2026-09-27: at this block's 400 ms settle the mask is
        // usually absent and the check passes vacuously; at 1500 ms it is
        // present on 8 of 8 loads and the check fails. It could only pass by
        // not measuring. THE `#map path` FALLBACK IS GONE RATHER THAN KEPT for
        // an app without the export: `overlayColor` is an engine export and is
        // in all six apps (measured 2026-09-27), so the fallback was dead code
        // whose only remaining effect was to supply the null the assertion used
        // to pass on — the tigerStatewideLoader lesson, that dead code is not
        // free because a measurement is only as honest as the code it reads.
        stroke: window[n] && window[n].overlayColor ? window[n].overlayColor(OFFLINE0) : null,
      };
    }, { n: EXPORTS_NAME, id: OFFLINE[0] });
    // `overlayColor` returns null whenever the colour is NOT MEASURABLE YET —
    // the layer has no runtime or overlayLayer, a tile layer's GL line layer is
    // not built, or a Leaflet overlay carries no colour on any sub-layer — so
    // the read is waited for rather than sampled, and the assertion below FAILS
    // on a null instead of short-circuiting past it. BOTH reads wait, because a
    // theme flip replaces the GL style and the line layer is rebuilt after it.
    const overlayReady = () => page.waitForFunction(({ n, id }) => {
      const c = window[n] && window[n].overlayColor && window[n].overlayColor(id);
      return typeof c === "string" && !!c;
    }, { n: EXPORTS_NAME, id: OFFLINE[0] }, { timeout: QUERY_TIMEOUT })
      .then(() => true, () => false);

    await page.evaluate((n) => window[n].setTheme("light", false), EXPORTS_NAME);
    await page.waitForTimeout(400);
    await overlayReady();
    const light = await read();
    await page.evaluate((n) => window[n].setTheme("dark", false), EXPORTS_NAME);
    await page.waitForTimeout(600);
    await overlayReady();
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
      !!light.stroke && !!dark.stroke && light.stroke !== dark.stroke,
      `${light.stroke} -> ${dark.stroke}`);
    await context.close();
  }

  // 10. TRIBAL GOVERNMENT. The nation, its seat and the land expected are
  //     read from the shipped file at the point, so a rebuild moves the
  //     expectation with the file; what is asserted is that each card agrees
  //     with it, and with where each seat came from.
  //       - The Round Valley Reservation's seat, Covelo, comes from the
  //         tribes' own site, because the Bureau of Indian Affairs lists no
  //         office town for them; the card says so on an "About the seat"
  //         line, links the site the Bureau lists, and names the whole council
  //         from the councils file; when that file fails the card still names
  //         the nation and names nobody on its council.
  //       - The Capitan Grande Reservation is shared by two governments, the
  //         Barona and Viejas groups of the Capitan Grande Band, so the card
  //         names both, lists each one's seat and site, and carries no single
  //         "(official)" link; it names no council, because each band's is
  //         named on the card for its own reservation.
  //       - The XL Ranch Rancheria's Census name does not name the Pit River
  //         Tribe, which holds it; the card names the tribe with the Bureau's
  //         town and no "About the seat" line, and links the tribe's own site,
  //         pitrivertribe.gov, because the site the Bureau lists had no DNS
  //         record on 2026-11-13 (Adam's "withdraw" of that day).
  //       - The Paskenta Rancheria names the four council members its own page
  //         names, and says the page lists the Tribal Secretary's seat as
  //         vacant; by Adam's ruling of 2026-11-13 ("carry") such a council
  //         is carried.
  //       - The California part of the Colorado River Indian Reservation
  //         names a government the Bureau seats in Parker, Arizona.
  //       - San Francisco City Hall is on no tribal land, and the card says
  //         so in the layer's own words.
  //     Each point is the pole of inaccessibility of the largest part of the
  //     piece inside this app's state outline, as the shipped files draw them
  //     (shapely polylabel, 2026-11-12, and 2026-11-13 for Paskenta): 682 m,
  //     1.9 km, 1.1 km, 3.4 km and 1.2 km from its edge.
  {
    const areas = JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "app", "tribal-areas.json"), "utf8"));
    const councils = JSON.parse(readFileSync(join(INSTANCE_DIR, "data", "app", "tribal-councils.json"), "utf8"));
    // The app's rule for a shipped file: even-odd within a polygon, any part
    // of a multipolygon.
    const inRing = (x, y, ring) => {
      let inside = false;
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i], [xj, yj] = ring[j];
        if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
      }
      return inside;
    };
    const propsAt = (fc, point) => {
      const [lat, lng] = point.split(",").map(Number);
      return fc.features.filter((f) => {
        const g = f.geometry;
        const polys = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
        return polys.some((rings) => rings.reduce((acc, ring) => acc !== inRing(lng, lat, ring), false));
      }).map((f) => f.properties);
    };
    const ROUND_VALLEY = "39.86652,-123.15988";
    const CAPITAN_GRANDE = "32.89983,-116.70090";
    const XL_RANCH = "41.52814,-120.46352";
    const COLORADO_RIVER = "34.20904,-114.27367";
    const PASKENTA = "39.86722,-122.22612";
    const at = async (pt, routeFn) => {
      const context = await browser.newContext({ serviceWorkers: "block" });
      const page = await context.newPage();
      await routeLeaflet(page);
      if (routeFn) await routeFn(page);
      await page.goto(`${BASE}#point=${pt}&layers=tribal-government`, { waitUntil: "domcontentloaded" });
      await page.waitForFunction((n) => !!window[n], EXPORTS_NAME, { timeout: BOOT_TIMEOUT });
      const card = await cardText(page, "tribal-government");
      const fields = await page.$$eval("#card-tribal-government .card-field",
        (els) => els.map((e) => ({
          label: ((e.querySelector(".card-field-label") || {}).textContent || "").trim(),
          value: ((e.querySelector(".card-field-value") || {}).textContent || "").trim()
        })));
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
      const land = propsAt(areas, ROUND_VALLEY);
      const p = land[0] || {};
      const council = (councils[p.aiannh] || {}).roster || [];
      const c = await at(ROUND_VALLEY);
      check("the Round Valley Reservation is seated at Covelo from the tribes' own site, says so, and links the Bureau's site for them, and names their whole council",
        land.length === 1 && !c.error &&
          c.by("Tribal government") === p.nation && p.nation === "Round Valley Indian Tribes, Round Valley Reservation, California" &&
          c.by("Seat of government") === "Covelo, CA" &&
          c.by("Land") === "Round Valley Reservation" &&
          !!p.seatNote && c.by("About the seat") === p.seatNote && p.seatNote.indexOf("From the nation's own site") === 0 &&
          p.url === "http://www.rvit.org" && c.link.text === p.nation + " (official)" && c.link.href === p.url &&
          council.length > 0 && council.every((m) => c.text.includes(m.name)) &&
          c.text.includes("From the nation's own council page") &&
          c.text.includes("Where these names come from") && !c.by("Why no names"),
        `land here=${land.length} link=${JSON.stringify(c.link)} seat=${JSON.stringify(c.by("Seat of government"))} note=${JSON.stringify(c.by("About the seat").slice(0, 80))}`);
    }

    {
      const p = propsAt(areas, ROUND_VALLEY)[0] || {};
      const council = (councils[p.aiannh] || {}).roster || [];
      const c = await at(ROUND_VALLEY, async (pg) => {
        await pg.route("**/data/app/tribal-councils.json", (r) => r.fulfill({ status: 503, body: "down" }));
      });
      const named = council.filter((m) => c.text.includes(m.name)).map((m) => m.name);
      check("the Tribal Government card still names the nation, and names nobody on its council, when the councils file fails",
        !c.error && c.by("Tribal government") === "Round Valley Indian Tribes, Round Valley Reservation, California" &&
          council.length > 0 && named.length === 0,
        `named=${named.slice(0, 2)} ${JSON.stringify(c.text.slice(0, 160))}`);
    }

    {
      const land = propsAt(areas, CAPITAN_GRANDE);
      const p = land[0] || {};
      const c = await at(CAPITAN_GRANDE);
      const names = (p.nations || []).map((n) => n.name);
      check("the Capitan Grande Reservation names both groups that share it, each with its seat and site, no single link, and no council of its own",
        land.length === 1 && !c.error && names.length === 2 &&
          c.by("Why no names") === p.rosterWhy && p.rosterWhy.indexOf("named on the card for its own reservation") !== -1 &&
          names[0].indexOf("(Barona Group") !== -1 && names[1].indexOf("Viejas (Baron Long) Group") !== -1 &&
          c.by("Tribal government") === p.nation && p.nation === names[0] + " and " + names[1] &&
          c.by("Land") === "Capitan Grande Reservation" &&
          c.labels.indexOf("Seat of government") === -1 && c.labels.indexOf("About the seat") === -1 &&
          c.text.indexOf("2 governments share this land") !== -1 &&
          c.text.indexOf("Seat: Lakeside, CA") !== -1 && c.text.indexOf("Seat: Alpine, CA") !== -1 &&
          p.url === null && c.link.text === "",
        `land here=${land.length} labels=${JSON.stringify(c.labels)} link=${JSON.stringify(c.link)} ${JSON.stringify(c.text.slice(0, 160))}`);
    }

    {
      const land = propsAt(areas, XL_RANCH);
      const p = land[0] || {};
      const c = await at(XL_RANCH);
      check("the XL Ranch Rancheria names the Pit River Tribe with the Bureau's town and no note about its seat, and links the tribe's own site in place of the Bureau's dead one",
        land.length === 1 && !c.error &&
          c.by("Tribal government") === "Pit River Tribe, California" &&
          c.by("Land") === "XL Ranch Rancheria" &&
          c.by("Seat of government") === "Burney, CA" && !p.seatNote &&
          c.labels.indexOf("About the seat") === -1 &&
          p.url === "https://pitrivertribe.gov/" && c.link.href === p.url &&
          c.by("Why no names") === p.rosterWhy && p.rosterWhy.indexOf("so the card does not link it") !== -1,
        `land here=${land.length} labels=${JSON.stringify(c.labels)} link=${JSON.stringify(c.link)}`);
    }

    {
      const land = propsAt(areas, PASKENTA);
      const p = land[0] || {};
      const council = (councils[p.aiannh] || {}).roster || [];
      const c = await at(PASKENTA);
      check("the Paskenta Rancheria names the four council members its page names and says the page lists the Tribal Secretary's seat as vacant",
        land.length === 1 && !c.error &&
          c.by("Tribal government") === p.nation && /^Paskenta Band of Nomlaki Indians/.test(p.nation) &&
          council.length === 4 && council.every((m) => c.text.includes(m.name)) &&
          c.text.includes("The page lists the Tribal Secretary's seat as vacant.") &&
          !c.by("Why no names"),
        `land here=${land.length} council=${council.length} ${JSON.stringify(c.text.slice(0, 200))}`);
    }

    {
      const land = propsAt(areas, COLORADO_RIVER);
      const p = land[0] || {};
      const c = await at(COLORADO_RIVER);
      check("the California part of the Colorado River Indian Reservation names a government seated in Arizona",
        land.length === 1 && !c.error &&
          c.by("Tribal government") === "Colorado River Indian Tribes of the Colorado River Indian Reservation, Arizona and California" &&
          c.by("Seat of government") === "Parker, AZ" &&
          c.by("Land") === "Colorado River Indian Reservation" && p.shareInState < 1,
        `land here=${land.length} ${JSON.stringify(c.text.slice(0, 200))}`);
    }

    {
      const off = await at(POINT);
      check("a point off tribal land is told so in the layer's own words",
        propsAt(areas, POINT).length === 0 &&
          off.text.indexOf("not on tribal land") !== -1 && off.text.indexOf("150 tribal areas") !== -1,
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
console.log("\nAll SF Thread-5 smoke checks passed.");
