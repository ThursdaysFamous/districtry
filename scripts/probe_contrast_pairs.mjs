// Every text node on every sitemap page, in a browser, in both themes —
// checked against what validate_contrast.py already knows about.
//
// WHY THIS EXISTS. That gate tests a STATED table of (foreground, background)
// pairs, and states plainly why: no regex can follow `color:` through the
// cascade to the background four ancestors up. The cost of a stated table is
// that a pair with no row reads as covered, and twice now it has been:
//
//   traffic.html          nine selectors at 12-13px, 2.93:1 and 3.04:1 light,
//                         4.49:1 dark. The page then declared fifteen colours
//                         of its own and the gate read only the brand token
//                         file; since 2026-09-18 it wears the sub-page shell
//                         and declares three, for its chart.
//   sources.html          the layer matrix's row-header band was
//                         rgba(244,247,249,0.6) with no dark counterpart, which
//                         over --panel is a light grey block under light text:
//                         the layer name 2.18:1, its id 1.25:1, the guide link
//                         1.37:1, on all six sources pages.
//   .dpf-support, code.k  a brand token (--faint) on two tints the table had
//                         rows for under --muted and --ink and not under
//                         --faint: 2.30:1 and 2.15:1 light, 2.76:1 and 2.60:1
//                         dark.
//
// Every one was found by measuring in a browser, and the first two were found
// by a sweep that lived in a scratch directory and would have been written
// again from nothing next time. This is that sweep, kept.
//
// WHAT IT ASSERTS, AND WHAT IT DELIBERATELY DOES NOT. It does not judge the
// palette — the static gate does that, and its ACCEPTED_SHORTFALLS is where a
// shortfall is recorded and decided. This asserts one thing: every
// colour-on-ground pair a browser finds below its floor is a pair the static
// gate ALREADY MEASURES AND ALREADY CALLS SHORT. A new one fails, and the
// message names the page, the selector and the two colours so a row can be
// written. So a shortfall the project has looked at costs nothing here, and a
// shortfall nothing has looked at cannot ship.
//
// The join is on the PAINTED COLOURS, not on token names, because a browser
// knows only colours: `--faint on --brand-tint over --surface` and
// `rgb(116,110,134) on rgb(54,47,74)` are the same claim, and only the second
// is a thing both sides can say. Both round composited channels to 8 bits, so
// the two agree exactly (validate_contrast.py --json prints its own).
//
// A pair whose colours match a row the static gate PASSES also fails, with a
// different message: same colours, different role. That is the case where a
// pair is decorative in the table and text on the page.
//
//   BASE_URL=http://localhost:8000 node scripts/probe_contrast_pairs.mjs
//
// Needs a server for the tree and Playwright, so it belongs in CI's browser
// job beside page_consistency_test.mjs, not among the stdlib gates.

import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, "..");
const BASE = (process.env.BASE_URL || "http://localhost:8000").replace(/\/$/, "");

// Every instance's app pulls Leaflet and MapLibre from cdnjs, which the
// sandbox cannot reach; the smoke tests solve this the same way, from the same
// gitignored vendor dir. Absent (CI, production), the CDN is reached directly.
const VENDOR = join(REPO, "scripts", "vendor", "leaflet");
const VENDORED = ["leaflet.js", "leaflet.css", "maplibre-gl.min.js", "maplibre-gl.css"]
  .filter((f) => existsSync(join(VENDOR, f)))
  .map((f) => [f, f.endsWith(".css") ? "text/css" : "application/javascript",
               readFileSync(join(VENDOR, f))]);

const SITEMAP = [...readFileSync(join(REPO, "sitemap.xml"), "utf8")
  .matchAll(/<loc>([^<]+)<\/loc>/g)]
  .map((m) => m[1].replace("https://districtry.com", ""));

// THE 329 PER-COUNTY PAGES ARE COVERED BY ONE REPRESENTATIVE PER DISTINCT
// PAINTED-ELEMENT SIGNATURE, WHICH IS A PARTITION AND NOT A SAMPLE.
//
// They are four templates rendered 329 times, and sweeping all of them was 658
// of this probe's 784 page loads. What a contrast pair can come from is a
// (tag, class) pair some rule paints, so two pages carrying the same SET of
// (tag, class) combinations cannot produce a colour pair the other does not.
// Grouping on that set and visiting one page per group is therefore lossless
// here, where "three per instance, spread across the alphabet" — the honest
// sample page_consistency_test.mjs takes, for a check whose subject is
// different — would be a real if small reduction in coverage.
//
// MEASURED 2026-09-23 on the full sweep it replaces: of the twelve below-floor
// pairs, ELEVEN appear on no per-county page at all, and the twelfth
// (rgb(107,114,128) on rgb(244,242,238)) appears on 329 of them AND on 8
// other pages. So the 658 loads were contributing one pair that eight cheaper
// pages already carry. 329 pages fall into 41 signatures.
//
// A GROUP'S REPRESENTATIVE IS ITS LARGEST PAGE, which costs nothing and buys
// insurance the signature does not cover by itself: more districts means more
// rows, so a structural rule keyed on position would still be exercised.
//
// THE GROUPING IS ONLY SOUND WHILE THE CSS CANNOT DISTINGUISH TWO PAGES THAT
// SHARE A SIGNATURE, so that is asserted rather than assumed — see
// assertSignatureIsComplete below. If a page ever gains an id selector or a
// position-keyed colour rule, this refuses to group rather than quietly
// measuring less than it says.
//
// It is self-maintaining in the direction that matters: a new county page
// whose markup differs at all lands in its own group and is visited. Only a
// page identical in every (tag, class) to one already visited is skipped.
const DEEP = (p) => p.replace(/^\//, "").split("/").length >= 3;

function paintedSignature(html) {
  const out = new Set();
  for (const m of html.matchAll(/<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>/g)) {
    const cls = /class="([^"]*)"/.exec(m[2]);
    out.add(m[1].toLowerCase() + "." + (cls ? cls[1].trim() : ""));
  }
  return [...out].sort().join("|");
}

// The two things a (tag, class) signature cannot see. An id selector can paint
// one page in a group and not its twin; a position-keyed rule can paint a row
// that a shorter page in the same group does not have. Neither exists in these
// pages' CSS today, and if one appears the grouping is unsound.
function assertSignatureIsComplete(html, path) {
  const css = [...html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1]).join("\n");
  // `[, sel, body]` and not `[sel, body]`: matchAll yields the FULL match first,
  // so the latter binds sel to the whole rule and body to the selector, and the
  // paints test below then never sees a declaration. Caught by negative test.
  for (const [, sel, body] of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const paints = /(^|;|\s)(color|background|background-color|border[-a-z]*color)\s*:/.test(body);
    if (!paints) continue;
    // `#abc123` inside a declaration is a colour; an id SELECTOR is in the selector.
    if (/#[A-Za-z][-\w]*/.test(sel)) {
      return `${path}: CSS paints through an id selector (${sel.trim().slice(0, 60)})`;
    }
    if (/:(nth-child|nth-of-type|nth-last-child|first-child|last-child|only-child)/.test(sel)) {
      return `${path}: CSS paints through a position-keyed selector (${sel.trim().slice(0, 60)})`;
    }
  }
  return null;
}

const guidePages = SITEMAP.filter((p) => !DEEP(p));
const deepPages = SITEMAP.filter(DEEP);
const groups = new Map();
const unsound = [];
for (const path of deepPages) {
  const file = join(REPO, path.replace(/^\//, ""));
  if (!existsSync(file)) { groups.set("missing:" + path, [{ path, size: 0 }]); continue; }
  const html = readFileSync(file, "utf8");
  const why = assertSignatureIsComplete(html, path);
  if (why) unsound.push(why);
  const sig = paintedSignature(html);
  if (!groups.has(sig)) groups.set(sig, []);
  groups.get(sig).push({ path, size: html.length });
}
if (unsound.length) {
  console.error("probe-contrast-pairs: FAIL — per-county pages cannot be grouped by " +
    "painted-element signature any more, so grouping them would measure less than " +
    "this probe claims. Sweep them all, or narrow the grouping:");
  for (const u of unsound.slice(0, 5)) console.error("  - " + u);
  process.exit(1);
}
// Largest first, then by path, so the choice is deterministic across runs.
const representatives = [...groups.values()]
  .map((g) => g.sort((a, b) => b.size - a.size || (a.path < b.path ? -1 : 1))[0].path);
const PAGES = [...guidePages, ...representatives].sort();

// Walks every element that owns text, composites its ground the way the
// browser paints it (nearest painted ancestor, translucent layers stacked),
// and returns only what falls below its own floor. WCAG's large-text
// relaxation is applied here, not in the static table, because only the
// browser knows the rendered size.
const BELOW_FLOOR = () => {
  const parse = (c) => {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const over = (f, b) => ({
    r: f.r * f.a + b.r * (1 - f.a), g: f.g * f.a + b.g * (1 - f.a),
    b: f.b * f.a + b.b * (1 - f.a), a: 1,
  });
  const r8 = (c) => ({ r: Math.round(c.r), g: Math.round(c.g), b: Math.round(c.b), a: 1 });
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const ratio = (a, b) => {
    const l1 = lum(a), l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };
  const bgOf = (el) => {
    const stack = [];
    let n = el;
    while (n && n.nodeType === 1) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) { stack.push(c); if (c.a === 1) break; }
      n = n.parentElement;
    }
    let base = parse(getComputedStyle(document.documentElement).backgroundColor);
    if (!base || base.a < 1) base = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = stack.length - 1; i >= 0; i--) base = r8(over(stack[i], base));
    return base;
  };
  const out = [];
  document.querySelectorAll("body, body *").forEach((el) => {
    let own = "";
    for (const n of el.childNodes) if (n.nodeType === 3) own += n.nodeValue;
    if (!own.trim()) return;
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden" || parseFloat(cs.opacity) === 0) return;
    const box = el.getBoundingClientRect();
    if (!(box.width > 0 && box.height > 0)) return;
    const fg0 = parse(cs.color);
    if (!fg0) return;
    const bg = bgOf(el);
    const fg = r8(over(fg0, bg));
    const px = parseFloat(cs.fontSize);
    const large = px >= 24 || (parseInt(cs.fontWeight, 10) >= 700 && px >= 18.66);
    const got = Math.round(ratio(fg, bg) * 100) / 100;
    const floor = large ? 3.0 : 4.5;
    if (got >= floor) return;
    out.push({
      sel: el.tagName.toLowerCase() + (typeof el.className === "string" && el.className.trim()
        ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".") : ""),
      text: own.trim().replace(/\s+/g, " ").slice(0, 40),
      fg: [fg.r, fg.g, fg.b], bg: [bg.r, bg.g, bg.b], px, ratio: got, floor,
    });
  });
  return out;
};

const key = (tier, fg, bg) => `${tier}|${fg.join(",")}|${bg.join(",")}`;

// How often the page loop reports progress. Low enough to locate a stall,
// high enough that a green run's log is read rather than scrolled past.
const PROGRESS_EVERY = 25;

// How long an app root gets to stop changing, and how often it is asked.
// The cap is 20x the longest settle any root has ever needed.
const SETTLE_STEP_MS = 100;
const SETTLE_CAP_MS = 2000;

const gateRows = JSON.parse(execFileSync("python3",
  [join(REPO, "scripts", "validate_contrast.py"), "--json"], { encoding: "utf8" }));
const known = new Map();       // colours the gate measures AND calls short
const passing = new Map();     // colours the gate measures and passes
for (const r of gateRows) {
  const k = key(r.tier, r.rgb_fg, r.rgb_bg);
  (r.status === "short" ? known : passing).set(k, r);
}

const browser = await chromium.launch({ args: ["--no-sandbox"] });
const found = new Map();
const FONTS = new Map();   // same-origin .woff2 read once, keyed by url path
// The app roots, derived from the fleet manifest for the same reason every
// other gate here derives its instance list: a sixth instance registered
// without a line edited is the point.
const APP_ROOTS = new Set(JSON.parse(readFileSync(join(REPO, "metros.json"), "utf8"))
  .metros.map((m) => `/${m.tag}/`));
let nodes = 0, visited = 0;
const brokenPages = [];   // a page that never answered, or whose answer never stopped moving
for (const scheme of ["light", "dark"]) {
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 900 }, colorScheme: scheme, serviceWorkers: "block",
  });
  // Every cross-origin request is aborted: basemap tiles, analytics, the
  // government APIs the apps query. None of them paints a colour this measures
  // — the stylesheets and the self-hosted Barlow are same-origin — and waiting
  // on them makes the answer depend on somebody else's uptime. It is also the
  // difference between a run of minutes and one of tens of minutes, since
  // `waitUntil: "load"` otherwise waits out the navigation timeout on every app
  // page wherever those hosts are unreachable.
  //
  // REGISTERED FIRST, and the vendored CDN files after it: Playwright gives
  // priority to the handler registered LAST, so a catch-all added at the end
  // would silently abort the two libraries the app needs to boot.
  await ctx.route("**/*", (route, request) => {
    const origin = new URL(request.url()).origin;
    // cdnjs stays allowed: where the vendor dir is absent (CI, production) the
    // fulfil handlers below do not exist and the app boots from the CDN, the
    // same way every instance's smoke test boots there.
    const ok = origin === new URL(BASE).origin || origin === "https://cdnjs.cloudflare.com";
    return ok ? route.continue() : route.abort();
  });
  for (const [name, type, body] of VENDORED) {
    await ctx.route(`**/cdnjs.cloudflare.com/**/${name}`,
      (r) => r.fulfill({ status: 200, contentType: type, body }));
  }
  // The self-hosted Barlow, served from memory. REGISTERED AFTER the catch-all
  // for the reason stated above: the LAST handler wins.
  //
  // WHY THIS IS NOT A MICRO-OPTIMISATION. A ctx.route handler takes its request
  // out of the browser's HTTP cache, so `route.continue()` re-fetches every
  // face on every navigation: measured on this tree, 3,240 requests over 784
  // loads for 55 distinct urls — nine font files, each served from the root and
  // from every instance — and 76% of the whole step's log. Reading them once
  // and fulfilling from a buffer serves the SAME BYTES, which is what
  // the settle below depends on — a fallback face must never be what gets
  // measured, so these are fulfilled and never aborted.
  await ctx.route("**/*.woff2", (route, request) => {
    const path = new URL(request.url()).pathname;
    if (!FONTS.has(path)) {
      const file = join(REPO, path.replace(/^\//, ""));
      FONTS.set(path, existsSync(file) ? readFileSync(file) : null);
    }
    const body = FONTS.get(path);
    return body
      ? route.fulfill({ status: 200, contentType: "font/woff2", body })
      : route.continue();
  });
  const page = await ctx.newPage();
  let done = 0;
  for (const path of PAGES) {
    try {
      await page.goto(BASE + path, { waitUntil: "load", timeout: 60000 });
      // Barlow is a webfont, and a fallback face can render at a different
      // size, which changes the large-text classification. So wait for the
      // faces, then for a frame painted with them — two rAFs is the condition
      // "layout now reflects the loaded faces", stated rather than slept for.
      //
      // A FLAT `waitForTimeout(300)` STOOD HERE AND IT WAS 300ms OF EVERY
      // 345ms THIS PROBE SPENT PER PAGE: 3.9 minutes of a 4.9-minute run, on
      // 784 loads of which 778 needed none of it. Replacing it with the two
      // rAFs alone is WRONG, and measuring is what said so: /il/ and /wi/ both
      // drop 12 below-floor nodes to 10, because an app boots its map and
      // renders its cards after `load` and two frames do not wait for that.
      // Every other page in the sitemap is unmoved — measured page by page
      // across all 392, both themes.
      //
      // So the app roots, which are DERIVED from metros.json and never listed,
      // are measured until the answer stops moving. That is the condition the
      // sleep was guessing at, and it is self-verifying where a number is not:
      // swept 2026-09-23, all six roots hold the same count from 100ms to
      // 5000ms, so the old 300ms was adequate and this cannot silently become
      // inadequate the way a number can.
      await page.evaluate(() => document.fonts.ready);
      await page.evaluate(() => new Promise((r) =>
        requestAnimationFrame(() => requestAnimationFrame(r))));
      visited++;
      let rows = await page.evaluate(BELOW_FLOOR);
      if (APP_ROOTS.has(path)) {
        let settled = false;
        for (let waited = 0; waited < SETTLE_CAP_MS; waited += SETTLE_STEP_MS) {
          await page.waitForTimeout(SETTLE_STEP_MS);
          const again = await page.evaluate(BELOW_FLOOR);
          settled = again.length === rows.length;
          rows = again;
          if (settled) break;
        }
        // Never take the last value and say nothing: a count still moving after
        // the cap means this page's answer is not reproducible, which is a
        // defect in its own right and not something to average away.
        if (!settled) {
          brokenPages.push(`${scheme} ${path}: below-floor count still moving ` +
            `after ${SETTLE_CAP_MS}ms (last ${rows.length})`);
          continue;
        }
      }
      // A line every PROGRESS_EVERY pages, naming the last one done, so a run
      // that stalls still says roughly where. It used to be one line per page,
      // which on a green run said nothing: 784 lines of which 350 read "0" and
      // the other 434 counted nodes the closing summary accounts for anyway.
      // Nothing here is diagnostic — the failure report below names every page
      // of every unmeasured pair, and that is what a red run needs.
      if (++done % PROGRESS_EVERY === 0) {
        console.log("  %s  %d/%d pages  (last: %s)", scheme.padEnd(5), done, PAGES.length, path);
      }
      for (const row of rows) {
        nodes++;
        const k = key(scheme, row.fg, row.bg);
        if (!found.has(k)) found.set(k, { tier: scheme, ...row, pages: new Set(), sels: new Set() });
        found.get(k).pages.add(path);
        found.get(k).sels.add(row.sel);
      }
    } catch (e) {
      brokenPages.push(`${scheme} ${path}: ${String(e).split("\n")[0]}`);
    }
  }
  await ctx.close();
}
await browser.close();

const problems = [];
for (const [k, f] of found) {
  if (known.has(k)) continue;
  const rgb = (c) => `rgb(${c.join(",")})`;
  const seen = `${rgb(f.fg)} on ${rgb(f.bg)} at ${f.px}px reads ${f.ratio}:1 against a ` +
    `${f.floor} floor — ${[...f.sels].sort().join(", ")} on ${f.pages.size} page(s): ` +
    `${[...f.pages].sort().slice(0, 4).join(" ")}`;
  const pass = passing.get(k);
  problems.push(pass
    ? `${f.tier}: ${seen}\n      validate_contrast.py measures these colours as ` +
      `(${pass.fg}, ${pass.bg}) with role "${pass.role}" and passes them at ${pass.ratio}:1 — ` +
      `same colours, different role. The row's role is what needs deciding.`
    : `${f.tier}: ${seen}\n      no pair in validate_contrast.py resolves to these colours. ` +
      `Add the row, then record or fix the shortfall.`);
}

if (brokenPages.length) {
  console.error("probe-contrast-pairs: FAIL — page(s) did not load, or did not settle:");
  for (const b of brokenPages) console.error("  - " + b);
  process.exit(1);
}
if (problems.length) {
  console.error("probe-contrast-pairs: FAIL — %d colour pair(s) below floor that the " +
    "static gate does not measure as short:", problems.length);
  for (const p of problems) console.error("  - " + p);
  process.exit(1);
}
console.log("probe-contrast-pairs: OK — %s page(s) x 2 themes (%s guide + %s representing " +
  "%s per-county pages in %s painted-element signature(s)), %s below-floor text node(s) in %s " +
  "distinct colour pair(s), every one already measured and called short by validate_contrast.py",
  visited / 2, guidePages.length, representatives.length, deepPages.length, groups.size,
  nodes, found.size);
