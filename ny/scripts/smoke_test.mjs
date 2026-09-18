// Headless boot + behaviour smoke test, run in CI on every pull request
// (.github/workflows/smoke-test.yml). Serves the real index.html and drives it
// in Chromium via Playwright.
//
// THREAD 1 scope (METRO_EXPANSION_PLAYBOOK §8/§10): five layers are registered —
// Neighborhood, ZIP, Borough, Judicial District, Municipal Court. The three
// offline anchors (borough / judicial-district / municipal-court) ship as
// same-origin data/app/*.json, so this test classifies a known point against
// them without depending on any third-party API being up in CI. It also
// exercises the NYC water-click honesty rule (a mid-river click resolves to no
// borough) and per-layer failure isolation. EXPECT_LAYERS climbs to 24 by
// Thread 6; the neighborhood/ZIP layers are live-Socrata and are deliberately
// NOT asserted as ground truth (flaky/throttled in CI).
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

// Disk reads are anchored to THIS SCRIPT, never to the process CWD. While each
// instance was its own repo, "data/app/…" was correct because you ran the smoke
// test from that repo's root. They are folders under one root now, and a bare
// relative read silently resolves against whatever directory you happen to be
// in — which is how the SF run died on `ENOENT: data/app/coverage-gaps.json`
// while the app itself booted fine. Anchoring costs one line and cannot drift.
const INSTANCE_DIR = dirname(dirname(fileURLToPath(import.meta.url)));

const BASE = process.env.BASE_URL || "http://localhost:8000/";
// ==== GENERATED:BEGIN smoke-config ====
const POINT = "40.71274,-74.00602"; // New York City Hall (Manhattan)
const OFFLINE = ["borough", "judicial-district", "municipal-court"];
const EXPECT_DISTRICT = { "borough": "Manhattan", "judicial-district": "1", "municipal-court": "1" };
const NEGATIVE_POINT = "40.72000,-74.04000"; // Hudson River, New Jersey waters — outside every anchor geometry (the East River is inside the county-derived judicial districts, so mid-river points there are only borough-negative)
const APP_NAME = "districtry New York City";
const EXPECT_LAYERS = 33; // Threads 1–4: full roster (+ council, community-district, congress, state senate/assembly, election-district, borough-president, district-attorney) + 3 amenity nearest-point layers (post-office, library, early-voting)
// ==== GENERATED:END smoke-config ====
const POINT2 = "40.69354,-73.98963"; // Brooklyn Borough Hall (Brooklyn) — the re-classify hop stays fork test code
const BOOT_TIMEOUT = 45000; // Leaflet CDN + first paint on a cold CI runner
const QUERY_TIMEOUT = 25000;

const failures = [];
function check(name, ok, detail) {
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);
  if (!ok) failures.push(name);
}

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
  await page.waitForFunction(() => !!window.NycExplorer, null, { timeout: BOOT_TIMEOUT });
  return page;
}

// Wait for a layer card to finish loading, then return its normalized text.
async function cardText(page, id) {
  await page
    .waitForFunction(
      (cid) => {
        const el = document.getElementById("card-" + cid);
        return el && !el.querySelector(".loading-row") &&
          (el.querySelector(".result-fields") || el.querySelector(".card-flush") ||
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
    // redesigned cards (engine-v1.0.10) carry the district identifier in the
    // header pill, outside the card body — read the card the way a user does
    const block = el.closest(".layer-block");
    const pill = block && block.querySelector(".card-id-pill:not([hidden])");
    const text = (pill ? pill.textContent + " " : "") + el.innerText;
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
    check("app boots (window.NycExplorer exported)", true);
    const n = await page.evaluate(
      () => document.querySelectorAll('input[type=checkbox][id^="toggle-"]').length
    );
    check(`${EXPECT_LAYERS} layers registered`, n === EXPECT_LAYERS, `found ${n}`);

    // THE APOSTROPHE RULE, asserted with no network call, because it is a pure
    // string function whose two halves pull in opposite directions and a later
    // edit can re-break one while the other still looks right. Measured across
    // the fleet's shipped data 2026-09-18: a single letter before an apostrophe
    // takes the capital (O'Brien, D'Arc, L'Anse), two or more do not (John's,
    // Children's), a digit before it is a possessive (D2's), and a leading
    // apostrophe opens a quote ('Tis). ST. JOHN'S CHURCH rendered
    // "St. John'S Church" until this was fixed.
    const tc = await page.evaluate(() => {
      const f = window.NycExplorer.toTitleCase;
      return [["ST. JOHN'S CHURCH", "St. John's Church"], ["O'BRIEN", "O'Brien"],
              ["LAND O'LAKES", "Land O'Lakes"], ["D'ANGELO", "D'Angelo"],
              ["VETERANS' HALL", "Veterans' Hall"], ["MCDONALD'S", "Mcdonald's"],
              ["D2'S BLOCK", "D2's Block"], ["'TIS", "'Tis"],
              ["J. LEO O'BRIEN SENIOR FACILITY", "J. Leo O'Brien Senior Facility"]]
        .map(([input, want]) => ({ input, want, got: f(input) }))
        .filter((r) => r.got !== r.want);
    });
    check("toTitleCase keeps O'Brien's capital and leaves John's alone",
      tc.length === 0,
      tc.length ? tc.map((r) => `${r.input} -> ${r.got} (want ${r.want})`).join("; ") : "9/9 cases");
    await context.close();
  }

  // 1a. The Data gaps panel: the honest inventory of what this app cannot answer,
  //     and the source-submission path (engine block `coverage-gaps`, shipped in
  //     engine-v1.0.19). Asserted because the panel is the one surface whose whole
  //     job is to be accurate about absence — a silently empty or truncated list is
  //     worse than no panel at all. Same-origin data, so this needs no network.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, BASE);
    const shipped = JSON.parse(readFileSync(join(INSTANCE_DIR, "data/app/coverage-gaps.json"), "utf8"));
    const expected = Object.keys(shipped).length;

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
          sections: Array.from(b.querySelectorAll(".gaps-section-label")).map((e) => e.textContent),
          hrefs: Array.from(b.querySelectorAll(".gap-suggest")).map((a) => a.getAttribute("href")),
        };
      });
    }

    const cold = await openGaps();
    check("data gaps panel renders every recorded gap",
      cold.items === expected && cold.sections.length === 1,
      `${cold.items}/${expected} items, ${cold.sections.length} section(s)`);
    check("every gap offers a prefilled submission to THIS fork's repo",
      cold.hrefs.length === expected &&
      cold.hrefs.every((h) => h.startsWith(repoIssues) &&
        /template=source-submission\.yml/.test(h) && /[?&]gap_id=/.test(h)),
      `${cold.hrefs.length} links -> ${repoIssues}`);

    // SELECTING A POINT MUST NOT DROP A GAP. That is the invariant, and the
    // thing a naive filter would break: the panel REGROUPS — the gaps naming
    // the clicked point's county lift into a "Where you clicked" section and
    // the rest stay grouped by kind — so the section COUNT is a function of
    // the data and never a property worth asserting.
    //
    // It was asserted anyway until 2026-09-18, as `sections.length === 1`,
    // under a comment reading "this fork ships no county outlines, so no gap
    // can be location-matched". That was false when it was written: `ny/`
    // ships five borough outlines, and all three gaps of the day named all
    // five boroughs, so every one matched City Hall and landed in a single
    // section. The check passed for a reason its own comment denied, and it
    // went red the moment a fourth gap arrived that correctly does NOT apply
    // at City Hall — the statewide election-district record, which is about
    // New York State outside the city.
    //
    // So this asserts what the panel actually owes a reader: every gap still
    // rendered, the clicked-point section present and holding the gaps that
    // name that borough, and the statewide-only gap NOT filed under where
    // they clicked.
    await page.evaluate((p) => window.NycExplorer.setSelectedPoint(p[0], p[1]),
      POINT.split(",").map(Number));
    const warm = await openGaps();
    const clicked = warm.sections.filter((t) => /^Where you clicked/.test(t));
    check("selecting a point regroups the gaps without dropping one",
      warm.items === expected && clicked.length === 1 &&
      warm.sections.length > 1 && /Where you clicked3$/.test(clicked[0]),
      `${warm.items}/${expected} items, sections=${JSON.stringify(warm.sections)}`);

    await context.close();
  }

  // 2. The three offline anchors classify New York City Hall against known
  //    ground truth, fetched from data/app/*.json (no third-party API).
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${POINT}&layers=${OFFLINE.join(",")}`);

    const boro = await cardText(page, "borough");
    check(`borough classifies City Hall (${EXPECT_DISTRICT["borough"]})`, !boro.error && new RegExp(EXPECT_DISTRICT["borough"]).test(boro.text) && /New York/.test(boro.text), boro.text.slice(0, 70));

    const jud = await cardText(page, "judicial-district");
    // pill-aware since the fork's card pass: the identifier lives in the header
    // pill ("District 1"), which cardText prepends — the body no longer
    // repeats it (Handoff 3 §5b).
    check(`judicial-district classifies City Hall (District ${EXPECT_DISTRICT["judicial-district"]})`, !jud.error && new RegExp("District\\s*" + EXPECT_DISTRICT["judicial-district"] + "\\b").test(jud.text), jud.text.slice(0, 70));

    const muni = await cardText(page, "municipal-court");
    check(`municipal-court classifies City Hall (${EXPECT_DISTRICT["borough"]} District ${EXPECT_DISTRICT["municipal-court"]})`, !muni.error && new RegExp(EXPECT_DISTRICT["borough"] + " Municipal Court District " + EXPECT_DISTRICT["municipal-court"] + "\\b").test(muni.text), muni.text.slice(0, 80));

    // Moving the selection re-classifies (P7 incremental-restyle fast path):
    // City Hall -> Brooklyn Borough Hall flips borough Manhattan->Brooklyn and
    // judicial district 1->2, and the matched-region highlight must move with it.
    const moved = await page.evaluate(async (p2) => {
      const [lat, lng] = p2.split(",").map(Number);
      window.NycExplorer.setSelectedPoint(lat, lng);
      const boroEl = document.getElementById("card-borough");
      const judEl = document.getElementById("card-judicial-district");
      // the district identifier lives in the header pill since the card
      // pass (Handoff 3 §5b) — read the whole block (header + body)
      const judBlock = judEl ? judEl.closest(".layer-block") : null;
      for (let i = 0; i < 100; i++) {
        if (boroEl && /Brooklyn/.test(boroEl.innerText) && judBlock && /District\s*2\b/.test(judBlock.innerText)) break;
        await new Promise((r) => setTimeout(r, 100));
      }
      return {
        boro: boroEl ? boroEl.innerText.replace(/\s+/g, " ").trim() : "(none)",
        jud: judBlock ? judBlock.innerText.replace(/\s+/g, " ").trim() : "(none)",
        highlights: document.querySelectorAll("#map .region-highlight").length,
      };
    }, POINT2);
    check(
      "point move re-classifies (Manhattan/1 -> Brooklyn/2) and re-highlights",
      /Brooklyn/.test(moved.boro) && /District\s*2\b/.test(moved.jud) && moved.highlights >= 1,
      `boro=${moved.boro.slice(0, 30)} | jud=${moved.jud.slice(0, 60)} | highlights=${moved.highlights}`
    );
    await context.close();
  }

  // 3. The NYC water-click honesty rule, made executable: the worksheet's
  //    negative point (Hudson River, NJ waters) is inside the map bounds but in
  //    no borough — the card must show the honest no-result state, never snap
  //    to nearest. (validate_index's negative-point-ground-truth check asserts
  //    the same point misses EVERY anchor geometry, not just the borough file.)
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(context, `${BASE}#point=${NEGATIVE_POINT}&layers=borough`);
    const boro = await cardText(page, "borough");
    check("mid-river click resolves to no borough (honest empty state)", !boro.error && boro.empty, boro.text.slice(0, 70));
    await context.close();
  }

  // 4. A failing data source degrades to that layer's error card + Retry, in
  //    isolation — the app's per-layer failure-isolation rule. Fail the borough
  //    anchor fetch; judicial-district (a different anchor file) still classifies.
  {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await booted(
      context,
      `${BASE}#point=${POINT}&layers=borough,judicial-district`,
      (p) => p.route("**/data/app/borough-boundaries.json", (r) => r.fulfill({ status: 503, body: "down" }))
    );
    await page
      .waitForFunction(
        () => {
          const el = document.getElementById("card-borough");
          return el && el.classList.contains("state-error");
        },
        null,
        { timeout: QUERY_TIMEOUT }
      )
      .catch(() => {});
    const res = await page.evaluate(() => {
      const b = document.getElementById("card-borough");
      const j = document.getElementById("card-judicial-district");
      // pill-aware (Handoff 3 §5b): the identifier is in the block header pill
      const jBlock = j ? j.closest(".layer-block") : null;
      return {
        errored: !!b && b.classList.contains("state-error"),
        hasRetry: !!b && !!b.querySelector(".retry-btn"),
        otherOk: !!j && !j.classList.contains("state-error") && !!jBlock && /District\s*1\b/.test(jBlock.innerText),
      };
    });
    check("failed layer shows error card + Retry", res.errored && res.hasRetry);
    check("failure is isolated (other anchor still classifies)", res.otherOk);
    await context.close();
  }

  // 5. Base-map tile failure surfaces an honest, dismissible banner (R6),
  //    instead of a silently gray map. Pure engine behaviour, no layer data.
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
