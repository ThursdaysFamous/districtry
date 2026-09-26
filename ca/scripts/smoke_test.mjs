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
const NEGATIVE_POINT = "37.74000,-122.59000"; // Open Pacific west of Ocean Beach, beyond CA state waters - outside every layer, including the water-inclusive TIGERweb legislative chambers
const APP_NAME = "districtry San Francisco";
const EXPECT_LAYERS = 16; // Thread-5: legislative chambers now pre-built SF-clipped geometry (data/app); supervisor-district is a bespoke roster-joined registerLayer; 11 layers total; + 3 amenity nearest-point layers (post-office, library, early-voting) = 14; + bart-director + election-precinct (parity-debt closures, 2026-07) = 16
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

const browser = await chromium.launch();
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

    // This fork ships no county outlines, so no gap can be location-matched.
    // Selecting a point must therefore leave the list WHOLE and single-sectioned —
    // that is the correct degradation, and the thing a naive filter would break.
    await page.evaluate((p) => window.SFExplorer.setSelectedPoint(p[0], p[1]),
      POINT.split(",").map(Number));
    const warm = await openGaps();
    check("selecting a point leaves the gap list whole (no outlines to match on)",
      warm.items === expected && warm.sections.length === 1,
      `${warm.items}/${expected} items, sections=${JSON.stringify(warm.sections)}`);

    // ==== TEMPLATE:BEGIN smoke-coverage-band ====
    // THIS INSTANCE PAINTS NO MIDDLE BAND, AND THAT IS THE CLAIM ASSERTED HERE.
    // The gaps lede answers three ways since 2026-09-26 — inside the covered
    // area, inside a wider region whose own key says what still answers there,
    // or outside both — and the middle answer exists only where the app hands
    // drawOutOfScopeMask a region geometry. This one hands it none (its coverage
    // IS the city), so the wash has two bands and the lede must keep saying
    // "nothing there can be answered yet" beyond the covered area. Asserted
    // rather than assumed because the engine block is one shared copy: a change
    // that started retaining a region unconditionally would have this app
    // claiming something answers in Oakland, and nothing static could see it.
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
      await page.evaluate((p) => window.SFExplorer.setSelectedPoint(p[0], p[1]),
        NEGATIVE_POINT.split(",").map(Number));
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

  // 2b. The negative Bay point misses every anchor — the honest "no district"
  //     empty state (never snap to nearest), from the same static geometry.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage();
    await routeLeaflet(page);
    await page.goto(`${BASE}#point=${NEGATIVE_POINT}&layers=${OFFLINE.join(",")}`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => !!window.SFExplorer, null, { timeout: BOOT_TIMEOUT });
    for (const id of OFFLINE) {
      const c = await cardText(page, id);
      check(`${id} reports no district at the Bay point`, c.empty && !c.error, c.text.slice(0, 70));
    }
    await context.close();
  }

  // 2c. The three legislative chambers classify City Hall from pre-built,
  //     SF-clipped same-origin geometry (data/app), and now name the officeholder
  //     from the scraped same-origin roster (data/app/*-members.json / roster).
  //     They use water-inclusive TIGERweb boundaries, so — unlike the
  //     shoreline-clipped anchors — they legitimately DO contain the negative Bay
  //     point (§7); they are checked positive-only here, deliberately not in the
  //     negative-point block above. The specific names change week to week, so we
  //     assert the member's ROLE label (proof a roster row joined), not a name.
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
} finally {
  await browser.close();
}

if (failures.length) {
  console.error(`\n${failures.length} smoke check(s) failed: ${failures.join(", ")}`);
  process.exit(1);
}
console.log("\nAll SF Thread-5 smoke checks passed.");
