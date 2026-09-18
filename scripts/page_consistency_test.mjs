// Behaviour gate: every page in the sitemap carries the same brand, the same
// standing links, the same keyboard entry, and tap targets a finger can hit —
// run in CI by smoke-test.yml.
//
// WHY THIS EXISTS. On 2026-08-24 three published pages were found still serving
// the pre-rebrand skin — ny/council-district.html, ny/community-board.html and
// ca/supervisor-district.html were on Inter and Big Shoulders, with no theme
// boot and no mark, while Illinois's three equivalents had all of it. They had
// survived two consecutive stages whose entire subject was the rebrand.
//
// Nothing caught them because nothing COMPARED them. compose_app.py checks the
// apps, generate_metro_files.py checks generated regions, validate_card_links.py
// checks that links resolve — and not one of them asks whether two published
// documents look like the same product. The pages were found by a throwaway
// script that drove all seventeen urls and printed a row each; this is that
// script, kept.
//
// TWO CHECKS ADDED 2026-09-13, both from the SEO re-audit and both the same
// shape as the rebrand miss above: a claim nobody compared against the pages.
// Six pages carried no skip link and no <main> — the root, traffic.html and the
// four history pages — while the app and the twelve sub-pages carried both, so
// a keyboard reader met a different site depending where they landed. And a
// sweep of WCAG 2.5.8 target size across all 37 pages at 390 and 1280 found
// four link rows short: the app's panel foot at a 2px row gap, the landing and
// history footers' wrapped rows, and the map-tile banner's 21x19 dismiss. The
// audit that reported the first of them had sampled four pages, which is why
// this sweeps every one.
//
// IT DERIVES ITS SURFACE, IT DOES NOT CARRY A LIST. The pages come from
// sitemap.xml and the expectations from the tree — a page is expected to link
// its instance's sources page when that instance HAS one, and never to link
// itself. So a new page is covered the day it ships, and a correct change (a
// fourth instance, a retired sub-page) cannot fail it. That distinction is the
// difference between a gate and a tripwire: SF's smoke test asserted its brand
// name as a literal and failed the rebrand, which is the failure mode to avoid.
//
//   node scripts/page_consistency_test.mjs      # BASE_URL defaults to :8000
import { chromium } from "playwright";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

// The sandbox's headless Chromium cannot reach cdnjs, so the three map pages
// would fail the console check on "L is not defined" — an environment fact, not
// a page defect. The smoke tests already solve this by serving the vendored copy
// same-origin; this does the same rather than exempting the pages, so the gate
// tests the real thing everywhere. Absent (production, GitHub Actions) the
// browser loads Leaflet from the CDN exactly as a reader does.
const VENDOR = join(ROOT, "scripts", "vendor", "leaflet");
const LEAFLET = existsSync(join(VENDOR, "leaflet.js")) && existsSync(join(VENDOR, "leaflet.css"))
  ? { js: readFileSync(join(VENDOR, "leaflet.js")), css: readFileSync(join(VENDOR, "leaflet.css")) }
  : null;
if (LEAFLET) console.log("  (serving Leaflet from scripts/vendor/leaflet — CDN unreachable in this env)");
const BASE = (process.env.BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const WHY = "https://overberg.co/why/";

// GENERATED PER-COUNTY PAGES ARE SAMPLED, NOT SWEPT, and the reason is a
// measurement rather than a preference: this gate costs 5.1s a page (3m8s for
// 37, timed 2026-09-13), and the per-county board pages added 164 more — 75 in
// Illinois, 72 in Wisconsin, 17 in Iowa — which swept would take it past twenty
// minutes on every PR.
//
// What makes sampling honest here is that they are ONE template.
// scripts/build_county_pages.py --check regenerates every one and compares it
// byte for byte, so a page that differs from the template cannot ship, and the
// same run reads each page back and asserts every name in that county's roster
// appears on it. Content is gated per page, statically. What a browser adds is
// whether the template renders, boots its theme, resolves its skip link and
// keeps its tap targets apart.
//
// THE SAMPLE IS PER INSTANCE, not per site, and that is the correction of
// 2026-09-13. An evenly-spaced sample of four across the whole sitemap can
// land entirely inside one instance, and the instances differ in exactly the
// place a template bug hides: each carries its own heading, title, breadcrumb
// label and map link, and the first Wisconsin draft titled every page
// "Menominee County County Board" while Illinois's were correct. A gate that
// could have sampled only Illinois would have passed it. Three per instance,
// spread across that instance's own alphabet, fixed so CI is reproducible.
const SAMPLE_GENERATED = 3;

function sampleGenerated(all) {
  const deep = (p) => p.split("/").filter(Boolean).length > 2;
  const byInstance = new Map();
  for (const p of all) {
    if (!deep(p)) continue;
    const tag = p.split("/").filter(Boolean)[0];
    if (!byInstance.has(tag)) byInstance.set(tag, []);
    byInstance.get(tag).push(p);
  }
  const keep = new Set();
  for (const pages of byInstance.values()) {
    if (pages.length <= SAMPLE_GENERATED) {
      for (const p of pages) keep.add(p);
      continue;
    }
    for (let i = 0; i < SAMPLE_GENERATED; i++) {
      keep.add(pages[Math.round((i * (pages.length - 1)) / (SAMPLE_GENERATED - 1))]);
    }
  }
  return all.filter((p) => !deep(p) || keep.has(p));
}

const paths = sampleGenerated([...readFileSync(join(ROOT, "sitemap.xml"), "utf8")
  .matchAll(/<loc>([^<]+)<\/loc>/g)]
  .map((m) => m[1].replace(/^https?:\/\/[^/]+/, "")));

// WCAG 2.5.8 Target Size (Minimum), swept below. An entry here is a target
// under 24 CSS px whose 24px circle reaches a neighbour and which the
// criterion's own exceptions cover — recorded with the exception it claims and
// a date, the shape ACCEPTED_SHORTFALLS and EXPECTED_UNREACHABLE already use,
// and re-audited every run: an entry nothing matches FAILS rather than sitting
// here after the thing it excused has gone.
// Runs in the page. Returns every target under 24 CSS px whose 24px circle
// reaches a neighbour and which none of WCAG 2.5.8's exceptions covers.
//
// Three things it took three passes to get right, each a false positive it
// produced on its own first runs:
//
//   PER FRAGMENT, not per element. getBoundingClientRect() on an inline link
//   that wraps returns the UNION of its lines — 335x45 for one 13.5px link in
//   the landing footer — a rectangle covering whitespace nobody can tap, which
//   then "collides" with every target near it. getClientRects() gives the line
//   boxes a reader sees.
//
//   AN ANCESTOR IS NOT A NEIGHBOUR. Leaflet's map container is focusable and
//   fills the map, so without this every overlay control on every app page
//   collides with it forever. A control inside a surface is nested, not
//   something you mis-tap beside it.
//
//   THE INLINE EXCEPTION WANTS THREE TESTS, not one. It covers a target that is
//   part of a line of text: an <a> (a button or a summary placed beside prose
//   is a control, not prose), computed display inline (an <a> set to block or
//   flex is a control too), and a parent whose remaining text is more than
//   separator punctuation (a row of links joined by "·" is a link list, and
//   that list is exactly what failed on three surfaces).
const TARGETS_FN = () => {
  const SEL = "a[href], button, input:not([type=hidden]), select, textarea, summary, " +
              "[role=button], [role=link], [tabindex]:not([tabindex='-1'])";
  const SEPARATORS = /^[\s·•|/–—,;>→←]*$/;
  const name = (el) => {
    const cls = el.getAttribute && el.getAttribute("class");
    return el.tagName.toLowerCase() +
      (cls && cls.trim() ? "." + cls.trim().split(/\s+/).slice(0, 2).join(".") : "");
  };
  const els = [...document.querySelectorAll(SEL)].filter((el) => {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") return false;
    const r = el.getBoundingClientRect();
    // A skip link parks itself at left:-9999px until focused; it is not a
    // target a pointer can reach and measuring it there is meaningless.
    return r.width > 0 && r.height > 0 && r.left > -1000 && r.top > -1000;
  });
  const boxes = [];
  for (const el of els) {
    for (const r of el.getClientRects()) {
      if (r.width <= 0 || r.height <= 0) continue;
      boxes.push({ el, x: r.left, y: r.top, w: r.width, h: r.height,
                   cx: r.left + r.width / 2, cy: r.top + r.height / 2 });
    }
  }
  const inline = (el) => {
    if (el.tagName !== "A" || getComputedStyle(el).display !== "inline") return false;
    const parent = el.parentElement;
    if (!parent) return false;
    let other = parent.textContent || "";
    for (const a of parent.querySelectorAll(SEL)) other = other.replace(a.textContent || "", "");
    return !SEPARATORS.test(other);
  };
  const circleHitsRect = (cx, cy, r) => {
    const nx = Math.max(r.x, Math.min(cx, r.x + r.w));
    const ny = Math.max(r.y, Math.min(cy, r.y + r.h));
    return Math.hypot(cx - nx, cy - ny) < 12;
  };
  const out = [];
  for (let i = 0; i < boxes.length; i++) {
    const b = boxes[i];
    if (b.w >= 24 && b.h >= 24) continue;
    if (inline(b.el)) continue;
    let worst = null;
    for (let j = 0; j < boxes.length; j++) {
      const o = boxes[j];
      if (i === j || o.el === b.el) continue;
      if (o.el.contains(b.el) || b.el.contains(o.el)) continue;
      const undersized = o.w < 24 || o.h < 24;
      const hit = undersized ? Math.hypot(b.cx - o.cx, b.cy - o.cy) < 24
                             : circleHitsRect(b.cx, b.cy, o);
      if (!hit) continue;
      const d = Math.round(Math.hypot(b.cx - o.cx, b.cy - o.cy) * 10) / 10;
      if (!worst || d < worst.d) {
        worst = { d, sel: name(o.el),
                  text: (o.el.textContent || o.el.value || "").trim().replace(/\s+/g, " ").slice(0, 26) };
      }
    }
    if (!worst) continue;                       // the spacing exception is met
    out.push({ sel: name(b.el),
               text: (b.el.textContent || b.el.value || "").trim().replace(/\s+/g, " ").slice(0, 30),
               parent: b.el.parentElement ? name(b.el.parentElement) : "—",
               w: Math.round(b.w * 10) / 10, h: Math.round(b.h * 10) / 10, near: worst });
  }
  // One row per (selector, parent): 124 chart columns are one finding.
  const seen = new Set();
  return out.filter((t) => {
    const k = `${t.sel}|${t.parent}`;
    if (seen.has(k)) return false;
    seen.add(k); return true;
  });
};

const TARGET_EXCEPTIONS = [
  {
    page: "/traffic.html", sel: "rect.hitcol", date: "2026-09-13",
    exception: "Equivalent",
    reason: "the daily chart's per-day hit columns, 14.8px wide at 1280 and " +
            "11.1px at 390 (measured 2026-09-18, when the redesign widened the " +
            "column to 1000px and gave the chart a 720px floor on phones; they " +
            "were 13.2 and 4.7 before) and necessarily touching — a chart of a " +
            "two-month window cannot give each day 24px without showing fewer " +
            "days. The two widths are re-measured above and hold whatever the " +
            "day count; " +
            "the day count itself was in this reason and moved the first time " +
            "the window did (51 to 62 on 2026-09-14), so it is not stated. " +
            "2.5.8's Equivalent " +
            "exception applies rather than Essential: the same numbers are on " +
            "the same page in the `View as table` disclosure below the chart, " +
            "whose rows are full-width.",
  },
];

const failures = [];
const exercised = new Set();
const probed = new Map();
function check(page, name, ok, detail) {
  if (!ok) failures.push(`${page} — ${name}${detail ? ": " + detail : ""}`);
  return ok;
}

// Luminance rather than the data-theme attribute: the attribute is only set
// when a reader has actually chosen a theme, so a fresh visit legitimately has
// none. What must hold on every page either way is that it paints the ground
// its viewer asked for.
const lum = (rgb) => {
  const [r, g, b] = (rgb.match(/\d+/g) || [255, 255, 255]).map(Number);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

// WCAG relative luminance + contrast, for the check below. This is a different
// calculation from `lum` above and both are wanted: `lum` answers "is this
// ground dark or light", which wants a cheap perceptual number, and this
// answers "can the text on it be read", which is a defined ratio with a
// defined threshold.
const rel = (rgb) => {
  const [r, g, b] = (rgb.match(/\d+/g) || [255, 255, 255]).map(Number);
  const f = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};
const contrast = (fg, bg) => {
  const a = rel(fg), b = rel(bg);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
};

const browser = await chromium.launch();
try {
  for (const path of paths) {
    const seg = path.replace(/^\/|\/$/g, "").split("/");
    const tag = seg.length > 1 ? seg[0] : null;       // null for the root pages
    const file = path.endsWith("/") ? "index.html" : seg[seg.length - 1];

    for (const scheme of ["light", "dark"]) {
      const ctx = await browser.newContext({ colorScheme: scheme, serviceWorkers: "block" });
      const p = await ctx.newPage();
      if (LEAFLET) {
        await p.route("**/cdnjs.cloudflare.com/**/leaflet.js", (r) =>
          r.fulfill({ status: 200, contentType: "application/javascript", body: LEAFLET.js }));
        await p.route("**/cdnjs.cloudflare.com/**/leaflet.css", (r) =>
          r.fulfill({ status: 200, contentType: "text/css", body: LEAFLET.css }));
      }
      const errs = [];
      p.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
      p.on("pageerror", (e) => errs.push(String(e)));
      const resp = await p.goto(BASE + path, { waitUntil: "domcontentloaded" });
      await p.waitForTimeout(250); // let the theme boot and any inline script run
      check(path, `loads (${scheme})`, resp.status() === 200, `HTTP ${resp.status()}`);

      const info = await p.evaluate(() => ({
        font: getComputedStyle(document.body).fontFamily.split(",")[0].replace(/['"]/g, ""),
        bg: getComputedStyle(document.body).backgroundColor,
        mark: !!document.querySelector(".districtry-mark, .logo-mark"),
        // The bars, measured rather than assumed. This page's whole subject is
        // whether two documents look like the same product, and it was passing
        // twelve pages whose header was a near-white bar carrying #fff text.
        bars: [["header", "header.masthead, .masthead, header"],
               ["footer", "footer.site-footer, footer"]].map(([role, sel]) => {
          const el = document.querySelector(sel);
          if (!el) return { role, missing: true };
          // Only what a reader SEES. getComputedStyle happily returns colours
          // for a display:none element, and the first draft of this check
          // failed all three apps on their footers — which the app skin hides,
          // because the links moved to the masthead. A contrast finding on an
          // invisible bar is noise, and noise is how a gate stops being read.
          if (!el.getClientRects().length) return { role, missing: true };
          const txt = el.querySelector("h1, h2, p, a") || el;
          return { role, bg: getComputedStyle(el).backgroundColor,
                   fg: getComputedStyle(txt).color };
        }),
        // The search box against the map, measured as rectangles. An app page
        // puts its search in the masthead toolbar BESIDE the layer pills; NY
        // and SF shipped it floating over the map instead, because the CSS for
        // both placements is shared and identical (`.masthead .map-toolbar {
        // position: static }` — a DESCENDANT selector) while the markup that
        // decides which one applies is per-instance, and only Chicago's was
        // ever moved. Nothing compared them, so it came back.
        //
        // Geometry, not markup: "is the toolbar inside the masthead" would pass
        // a toolbar that is inside the masthead and still painted over the map
        // by a position rule, and it would fail a future layout that solves
        // this a different and perfectly good way. What must never be true is
        // that the search covers the thing you are meant to click.
        search: (() => {
          const box = document.querySelector(".search-shell") ||
                      document.getElementById("geocode-input");
          const map = document.getElementById("map");
          if (!box || !map) return null;          // sub-pages have neither
          const a = box.getBoundingClientRect(), m = map.getBoundingClientRect();
          const over = !(a.right <= m.left || a.left >= m.right ||
                         a.bottom <= m.top || a.top >= m.bottom);
          return { over, box: [Math.round(a.top), Math.round(a.left)],
                   map: [Math.round(m.top), Math.round(m.left)] };
        })(),
        // The app's two standing footer facts, measured as pixels: the date
        // the data was last verified, and the way to report a problem with it.
        // The skin hides `footer.site-footer` (the links moved to the
        // masthead), so an app that leaves these inside that husk RENDERS them
        // and shows them to nobody. Chicago relocated them into the
        // results-panel foot at the redesign; NY and SF did not, and shipped
        // for weeks with an invisible verified date and no reachable feedback
        // button — past every gate in this repo, because parity of the SHARED
        // engine was checked and parity of what a reader can SEE was not.
        // Anchored to the map so sub-pages (which have neither) skip it.
        appFoot: (() => {
          if (!document.getElementById("map")) return null;
          const seen = (el) => !!el && el.getClientRects().length > 0 &&
                               getComputedStyle(el).visibility !== "hidden";
          return { date: seen(document.getElementById("verified-date")),
                   feedback: seen(document.getElementById("feedback-btn")) };
        })(),
        // The VALUES, not merely the presence. Michigan's go-live found
        // mi/sources.html serving Iowa's entire identity block — canonical,
        // og:url, og:site_name, title and the whole ld+json graph still said
        // districtry.com/ia/sources.html, because the page was cloned from
        // Iowa and only its generated regions were ever regenerated. This gate
        // PASSED it: `!!document.querySelector("link[rel=canonical]")` asks
        // whether the tag is there and never what it says, and a canonical
        // pointing at another instance's page is not a cosmetic slip — it asks
        // Google to drop this page in favour of that one.
        canonical: (document.querySelector("link[rel=canonical]") || {}).href || null,
        ogUrl: (document.querySelector('meta[property="og:url"]') || {}).content || null,
        // Every url on this fleet's own origin anywhere in the ld+json graph:
        // @id, url, isPartOf, breadcrumb items. Read as text rather than by
        // key name, so a graph that grows a key is covered without an edit.
        jsonLdSelfUrls: [...document.querySelectorAll('script[type="application/ld+json"]')]
          .flatMap((s) => (s.textContent || "")
            .match(/https?:\/\/(?:www\.)?districtry\.com\/[^"\s]*/g) || []),
        ogTitle: !!document.querySelector('meta[property="og:title"]'),
        // A skip link and the landmark it needs. Measured 2026-09-12, six
        // sitemap pages had neither — the root, traffic.html and the four
        // history pages — while the app and the twelve sub-pages had both, so
        // a keyboard reader met a different site depending where they landed.
        // The href must RESOLVE: a skip link pointing at an id nothing carries
        // is worse than none, because it reads as present and does nothing.
        skip: (() => {
          const a = [...document.querySelectorAll("a[href^='#']")]
            .find((x) => /skip/i.test(x.textContent || "") || /skip/i.test(x.className || ""));
          if (!a) return { present: false };
          const id = a.getAttribute("href").slice(1);
          return { present: true, target: !!id && !!document.getElementById(id), id };
        })(),
        hasMain: !!document.querySelector("main"),
        links: [...document.querySelectorAll("a[href]")].map((a) => a.getAttribute("href") || ""),
      }));

      check(path, `brand typeface (${scheme})`, info.font === "Barlow", info.font);
      check(path, `paints a ${scheme} ground`, (lum(info.bg) < 90) === (scheme === "dark"), info.bg);
      check(path, `carries the mark (${scheme})`, info.mark);

      if (info.search) {
        check(path, `search sits beside the map, not on it (${scheme})`,
              !info.search.over,
              `search@${info.search.box} overlaps map@${info.search.map}`);
      }

      if (info.appFoot) {
        check(path, `verified date is visible to a reader (${scheme})`, info.appFoot.date);
        check(path, `feedback button is reachable (${scheme})`, info.appFoot.feedback);
      }

      // A surface is never a text token. `background: var(--ink)` reads as a
      // deliberate dark bar in light mode and is a coincidence — --ink is the
      // TEXT colour, so in dark mode it flips and the bar turns near-white with
      // white text on it. Twelve of thirteen sub-pages shipped that way,
      // measured at 1.20:1 against WCAG AA's 4.5:1, past every gate in this
      // repo including this one. 4.5 is the body-text threshold; a masthead
      // title is large text, whose bar is 3:1, so the stricter number is used
      // deliberately — nothing here needs to sit between them.
      for (const bar of info.bars) {
        if (bar.missing) continue;
        if (/rgba\(0, 0, 0, 0\)|transparent/.test(bar.bg)) continue;  // inherits the ground
        const c = contrast(bar.fg, bar.bg);
        check(path, `${bar.role} text is readable on its own bar (${scheme})`,
              c >= 4.5, `${c.toFixed(2)}:1 — ${bar.fg} on ${bar.bg}`);
      }
      check(path, "canonical", !!info.canonical);
      check(path, "og:title", info.ogTitle);
      check(path, `carries a skip link (${scheme})`, info.skip.present);
      if (info.skip.present) {
        check(path, `the skip link resolves (${scheme})`, info.skip.target,
              `#${info.skip.id} matches no element`);
      }
      check(path, `carries a <main> landmark (${scheme})`, info.hasMain);

      // --- the page's identity is its OWN ------------------------------------
      // All 31 sitemap pages self-canonicalise exactly, measured 2026-09-03, so
      // this is an equality rather than a prefix rule: a page that canonicalises
      // anywhere but itself is either lying about which page it is, or is a
      // deliberate change that should say so here.
      const ownPath = (u) => { try { return new URL(u).pathname; } catch { return null; } };
      if (info.canonical) {
        check(path, `canonical names this page (${scheme})`,
              ownPath(info.canonical) === path, info.canonical);
      }
      if (info.ogUrl) {
        check(path, `og:url names this page (${scheme})`,
              ownPath(info.ogUrl) === path, info.ogUrl);
      }
      // The ld+json graph legitimately points UP (isPartOf the instance's own
      // site, a breadcrumb to its map) but never SIDEWAYS into a sibling
      // instance. Checked as a prefix for that reason, where canonical is an
      // equality. Root pages have no tag and are skipped rather than guessed at.
      if (tag) {
        const foreign = info.jsonLdSelfUrls.filter((u) => {
          const pn = ownPath(u);
          return pn && pn !== "/" && !pn.startsWith(`/${tag}/`);
        });
        check(path, `ld+json stays inside /${tag}/ (${scheme})`,
              foreign.length === 0, foreign.slice(0, 3).join(" "));
      }

      // GoatCounter cannot be reached from a sandbox and its failure is not a
      // page defect — it reproduces identically on every page including ones
      // nobody touched.
      const real = errs.filter((e) => !/gc\.zgo\.at|ERR_CONNECTION_RESET/.test(e));
      check(path, `no console errors (${scheme})`, real.length === 0, real.slice(0, 2).join(" | "));

      if (scheme !== "light") { await ctx.close(); continue; }

      // --- the standing links, expected from the TREE rather than a list ----
      const want = [];
      if (tag) {
        if (file !== "sources.html" && existsSync(join(ROOT, tag, "sources.html"))) want.push("sources.html");
        if (file !== "faq.html" && existsSync(join(ROOT, tag, "faq.html"))) want.push("faq.html");
      }
      want.push("privacy");
      want.push(WHY);
      for (const w of want) {
        const has = w === "privacy"
          ? info.links.some((h) => /(^|\/)privacy\.html$/.test(h))
          : info.links.some((h) => h.endsWith(w));
        check(path, `links ${w}`, has || (w === "privacy" && file === "privacy.html"));
      }

      // --- WCAG 2.5.8 target size, at the two widths that matter -----------
      // Measured 2026-09-13 across all 37 pages: four link rows failed (the
      // app's panel foot at a 2px row gap, the landing and history footers'
      // wrapped rows, and the map-tile banner's 21x19 dismiss), and the audit
      // that found the first of them had sampled four pages. A sweep is the
      // only honest way to answer "does this hold everywhere".
      for (const [label, vw, vh] of [[390, 390, 844], [1280, 1280, 900]]) {
        await p.setViewportSize({ width: vw, height: vh });
        await p.waitForTimeout(150);
        const bad = await p.evaluate(TARGETS_FN);
        for (const t of bad) {
          const exc = TARGET_EXCEPTIONS.find((e) => e.page === path && e.sel === t.sel);
          if (exc) { exercised.add(`${exc.page}|${exc.sel}`); continue; }
          check(path, `target ${t.sel} is 24px or clear of its neighbours (@${label})`,
                false,
                `"${t.text}" ${t.w}x${t.h} in ${t.parent}, ${t.near.d}px from ` +
                `${t.near.sel} "${t.near.text}"`);
        }
      }
      await p.setViewportSize({ width: 1280, height: 720 });

      // --- every relative link resolves, each distinct url probed ONCE -------
      // Anything with a SCHEME is not a relative link, matched generically
      // rather than as the allowlist (https:, mailto:, #) this was. That
      // allowlist held only while no page used a fourth scheme; the county
      // pages put `tel:` on 523 phone numbers and the probe tried to fetch one,
      // which Playwright refuses outright — the whole gate died on a link that
      // was never its subject.
      for (const h of info.links.filter((x) => x && !/^([a-z][a-z0-9+.-]*:|#)/i.test(x))) {
        const abs = new URL(h, BASE + path).href;
        if (!probed.has(abs)) probed.set(abs, (await p.request.get(abs)).status());
        check(path, `link ${h}`, probed.get(abs) === 200, `HTTP ${probed.get(abs)}`);
      }

      // --- the question pages' address box, LAST because it navigates ------
      // scripts/build_question_forms.py generates one form eleven times and
      // its --check proves the bytes; this is the half a static check cannot
      // have. The form ships `hidden` and its own script unhides it, so a
      // reader with no JavaScript never meets an input that cannot submit —
      // which means "hidden" is also what a broken script looks like, and
      // only a browser can tell the two apart. The submit is then measured by
      // the URL it produces: ./#q=<address>&layers=<the page's own cta>, with
      // the address in the HASH, where count.js cannot send it.
      if (await p.locator("#lookup").count()) {
        check(path, "address box unhides when its script runs",
              await p.locator("#lookup").isVisible());
        const cta = await p.evaluate(() => {
          const a = document.querySelector('a.cta[href^="./#layers="]');
          return a ? a.getAttribute("href").split("#layers=")[1] : null;
        });
        check(path, "address box sits above a cta naming its layers", !!cta);
        // The app is not this check's subject. Stubbing the instance root
        // keeps eleven pages from booting a 26,000-line document each.
        await p.route(`**/${tag}/`, (r) => r.fulfill({
          status: 200, contentType: "text/html",
          body: "<!doctype html><title>stub</title>" }));
        await p.fill("#lookup-q", "233 S Wacker Dr");
        await Promise.all([
          p.waitForURL((u) => u.pathname === `/${tag}/`, { timeout: 5000 }).catch(() => {}),
          p.click(".lookup-go"),
        ]);
        const got = new URL(p.url());
        check(path, "submitting hands the address to the app in the hash",
              got.pathname === `/${tag}/` &&
              got.search === "" &&
              got.hash === `#q=233%20S%20Wacker%20Dr&layers=${cta}`,
              p.url());
      }
      await ctx.close();
    }
  }
} finally {
  await browser.close();
}

// An exception that no longer excuses anything is a hole in the gate with
// nothing saying so — the property check_roster_retention.py's ACCEPTED_DROPS
// had to be given after the fact.
for (const e of TARGET_EXCEPTIONS) {
  if (!exercised.has(`${e.page}|${e.sel}`)) {
    failures.push(`TARGET_EXCEPTIONS records ${e.sel} on ${e.page} (${e.exception}, ` +
      `${e.date}) and nothing on that page matches it now — drop the entry`);
  } else {
    console.log(`  ~ ${e.page} ${e.sel}: under 24px, WCAG 2.5.8 ${e.exception} ` +
      `exception, recorded ${e.date} — ${e.reason}`);
  }
}

if (failures.length) {
  console.error(`\n${failures.length} consistency failure(s):`);
  for (const f of failures) console.error("  - " + f);
  process.exit(1);
}
console.log(`All ${paths.length} page(s) consistent — brand, metadata, standing links, no dead links, a skip link that resolves into a <main>, and every tap target at 390 and 1280 either 24px or clear of its neighbours.`);
