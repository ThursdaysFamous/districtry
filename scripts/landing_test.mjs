// Behaviour gate for the root's GENERATED pages — the landing page (R4), its
// coverage map, and the fleet privacy page — run in CI by smoke-test.yml.
//
// WHY THIS IS A GATE AND NOT A SCRATCH SCRIPT. The pages themselves are
// generated and drift-checked by build_landing_page.py / build_coverage_map.py,
// which prove they match metros.json. That cannot prove they still WORK, and
// the parts that matter most are invisible to a diff: the forwarding guard, and
// (since the address-first redesign) the address box's routing.
//
// Before R2.3 the Illinois app served from this origin's root, so every share
// link and embed snippet it handed out was built from the root URL —
//
//   https://chidistricts.com/?utm_source=share&utm_medium=link#point=41.88,-87.63
//   <iframe src="https://chidistricts.com/?utm_source=embed&utm_medium=iframe#point=...">
//
// — and those live in other people's pages and bookmarks and cannot be recalled.
// The guard is what keeps them reaching the map instead of a page about
// Illinois. A regex typo or a changed FORWARD_TO would break every one of them
// silently, on a page that still looks perfect and still passes its drift
// check. So the forward is asserted here, in a real browser, both ways: an app
// link forwards with its query AND hash intact, and a plain visit does not.
//
//   node scripts/landing_test.mjs          # BASE_URL defaults to :8131
import { chromium } from "playwright";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const BASE = process.env.BASE_URL || "http://localhost:8131";
const HERE = dirname(fileURLToPath(import.meta.url));
// The expected tags come from metros.json rather than a literal. They were
// hardcoded as (il|nyc|sf) and went stale the moment R5 renamed the folders
// to ny/ and ca/ — the test failed on a correct change, which is the failure
// mode a gate must not have. metros.json is the same source the page is
// generated from, so the two can only disagree if the generator is wrong.
const FLEET = JSON.parse(readFileSync(
  join(HERE, "..", "metros.json"), "utf8")).metros;
const TAGS = FLEET.map((m) => m.tag).filter(Boolean);
const failures = [];
function check(name, ok, detail) {
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);
  if (!ok) failures.push(name);
}

// The coverage map loads Leaflet from cdnjs, which the sandboxed dev
// environment cannot reach (see CLAUDE.md — Chromium does not use the agent
// proxy). scripts/vendor_leaflet.sh mirrors it via curl, which can; serve that
// copy same-origin when it is present, exactly as each instance's own
// smoke_test.mjs does. In CI the dir is absent and the real CDN answers, so
// this route never installs and nothing about the test changes.
const LEAFLET_VENDOR = join(HERE, "vendor", "leaflet");
async function serveVendoredLeaflet(page) {
  if (!existsSync(LEAFLET_VENDOR)) return false;
  await page.route("**/cdnjs.cloudflare.com/ajax/libs/leaflet/**", (route) => {
    const name = new URL(route.request().url()).pathname.split("/").pop();
    const path = join(LEAFLET_VENDOR, name);
    if (!existsSync(path)) return route.abort();
    route.fulfill({
      status: 200,
      contentType: name.endsWith(".css") ? "text/css" : "application/javascript",
      body: readFileSync(path),
    });
  });
  return true;
}

// A 1x1 transparent GIF for the CARTO basemap tiles. The map's correctness has
// nothing to do with whether a raster tile painted, and letting real tile
// requests fly would make this gate depend on a third party's uptime — and
// spend the fleet's metered CARTO quota on CI.
const BLANK_TILE = Buffer.from(
  "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBTAA7", "base64");
async function stubTiles(page) {
  await page.route("**/*.basemaps.cartocdn.com/**", (route) =>
    route.fulfill({ status: 200, contentType: "image/gif", body: BLANK_TILE }));
}

// One Photon response, shaped like the real thing. The address box is asserted
// against a STUB rather than the live geocoder for the same reason /il/ is
// stubbed below: a gate that needs photon.komoot.io to be up and to keep
// ranking a given address the same way is a gate that fails on someone else's
// schedule. What is under test is the ROUTING — bbox match, tie-break, the
// #point= handoff — not whether Photon can find a street.
function photonStub(features) {
  return (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ type: "FeatureCollection", features }),
  });
}
function photonFeature(lat, lng) {
  return { type: "Feature", geometry: { type: "Point", coordinates: [lng, lat] }, properties: {} };
}

// Read an element's text, or null if it is not there. page.textContent()
// blocks for its full 30s timeout and then THROWS, which kills the run with an
// uncaught TimeoutError instead of reporting a failure — so a regression that
// removes an element takes the whole gate down and reports nothing about the
// checks after it. A gate should fail loudly on the thing that broke, not
// crash before it can say so.
async function textOrNull(page, selector) {
  return page.textContent(selector, { timeout: 2000 }).catch(() => null);
}

const browser = await chromium.launch();
try {
  // --- 1. a bare visit renders the landing page, and does NOT forward -------
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(400);
    const url = page.url();
    check("bare / stays on the landing page", new URL(url).pathname === "/", url);

    const wordmark = await page.textContent(".wordmark").catch(() => null);
    check("wordmark renders", wordmark === "districtry", JSON.stringify(wordmark));

    const pills = await page.$$eval(".pill", (els) =>
      els.map((e) => ({
        href: e.getAttribute("href"),
        // the layer count lives in a child span, so strip it off the name
        name: e.firstChild?.textContent?.trim(),
        n: e.querySelector(".pill-n")?.textContent?.trim(),
      })));
    check("every fleet place is listed", pills.length === FLEET.length,
      JSON.stringify(pills.map((p) => p.name)) + " vs metros.json " + FLEET.length);
    check("Illinois pill points at /il/",
      pills.some((p) => p.name === "Illinois" && /\/il\/$/.test(p.href)),
      pills.find((p) => p.name === "Illinois")?.href);
    check("every pill links a fleet url",
      pills.every((p) => FLEET.some((m) => m.url === p.href)),
      JSON.stringify(pills.map((p) => p.href)));
    // A layer count is the one number on this page a reader could act on, and
    // it is read from each instance's own worksheet — a pill showing 0, blank
    // or NaN means the generator lost its grip on that file.
    check("every pill states a positive layer count",
      pills.every((p) => /^\d+$/.test(p.n || "") && Number(p.n) > 0),
      JSON.stringify(pills.map((p) => p.n)));

    // The "not yet" disclosure is generated by subtracting the covered states
    // from the 50+DC list, so a place that is BOTH live and listed as missing
    // is a contradiction the page would state in two directions at once.
    const notYet = await page.$$eval(".not-yet-list div", (els) =>
      els.map((e) => e.textContent.trim()));
    const liveNames = FLEET.map((m) => m.landing_name);
    check("the not-yet list never names a place that already answers",
      notYet.every((s) => !liveNames.includes(s)),
      notYet.filter((s) => liveNames.includes(s)).join(", ") || "no overlap");
    check("the not-yet list is non-empty and plausible",
      notYet.length > 40 && notYet.length < 51, String(notYet.length));

    // Barlow must actually be applied, not silently falling back to system-ui.
    const font = await page.evaluate(() =>
      getComputedStyle(document.querySelector(".wordmark")).fontFamily);
    check("wordmark uses Barlow Condensed", /Barlow Condensed/.test(font), font);
    const loaded = await page.evaluate(async () => {
      await document.fonts.ready;
      return [...document.fonts].filter((f) => f.status === "loaded").map((f) => f.family + " " + f.weight);
    });
    check("a self-hosted face actually loaded", loaded.length > 0, JSON.stringify(loaded));
    await ctx.close();
  }

  // --- 1b. the rename toast fades on its own, and dismisses on click -------
  //
  // It is a TOAST now rather than an inline banner, which means it sits over
  // the masthead and can cover the wordmark. A toast that fails to fade is a
  // permanent obstruction on the front door — and because it is absolutely
  // positioned, a reader cannot scroll it away.
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    const notice = await page.$("#notice");
    check("the rename notice renders", notice !== null);
    if (notice) {
      const shown = await notice.isVisible();
      check("the rename notice starts visible", shown, String(shown));
      await page.click("#notice-dismiss");
      // The fade is a 900ms CSS animation, then display:none.
      await page.waitForTimeout(1600);
      const after = await page.evaluate(() => {
        const el = document.getElementById("notice");
        return el ? getComputedStyle(el).display : "removed";
      });
      check("dismissing the rename notice hides it",
        after === "none" || after === "removed", after);
    }
    await ctx.close();
  }

  // --- 1c. the address box routes to the instance that covers the point ----
  //
  // This is the page's one genuinely interactive feature, and every part of it
  // is invisible to the drift check: the geocode call, the bbox test against
  // metros.json, and the #point= handoff. Photon is STUBBED (see photonStub
  // above) so what is measured is the routing and not a third party's ranking.
  //
  // Each instance is exercised from a point inside its OWN bbox, taken from
  // metros.json rather than typed here — so a bbox that is edited, or a metro
  // that is added, is covered without touching this file.
  //
  // UNCOVERED_POINT leads every stubbed response on purpose. The box is
  // documented to take the first result that falls inside a covered bbox, not
  // simply result #1, so ranking a miss above the hit is what proves the scan
  // happens at all. (It cannot, on its own, prove the bbox test EXISTS — every
  // probe point here is its own bbox's centre, so a build with the filter
  // deleted still lands correctly on the nearest-centre tie-break. Block 1d is
  // what catches that, which is why its instance stubs matter.)
  const UNCOVERED_POINT = [32.7767, -96.797];   // Dallas — outside all five bboxes
  // Stub each instance's PAGE, never its data. The routing under test now
  // fetches `<tag>/data/app/metro-outline.json` to settle a contested point,
  // and a `**/${t}/**` glob swallows that too — the outline would come back as
  // an HTML stub, json() would throw, and the code would quietly fall back to
  // the bbox rule this change exists to replace. The test would still pass, on
  // the old behaviour, which is the worst kind of green.
  async function stubInstances(page) {
    await page.route(
      (url) => TAGS.some((t) => url.pathname.startsWith(`/${t}/`)) &&
               !/\/data\//.test(url.pathname),
      (r) => r.fulfill({
        status: 200, contentType: "text/html",
        body: `<!doctype html><title>instance stub</title>`,
      }));
  }
  for (const m of FLEET) {
    const lat = (m.bbox.minLat + m.bbox.maxLat) / 2;
    const lng = (m.bbox.minLng + m.bbox.maxLng) / 2;
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await page.route("**/photon.komoot.io/**", photonStub([
      photonFeature(...UNCOVERED_POINT),
      photonFeature(lat, lng),
    ]));
    // Stub every instance, not just this one: a routing bug that sends the
    // reader to the WRONG instance must show up as a wrong URL, not as a
    // navigation failure that looks the same as a right one.
    await stubInstances(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.fill("#search-input", "somewhere in " + m.landing_name);
    await page.click("#search-button");
    await page.waitForTimeout(700);
    const u = new URL(page.url());
    check(`an address in ${m.landing_name} opens /${m.tag}/`,
      u.pathname === `/${m.tag}/`, page.url());
    check(`an address in ${m.landing_name} arrives with its point selected`,
      /^#point=-?\d+\.\d+,-?\d+\.\d+$/.test(u.hash), JSON.stringify(u.hash));
    await ctx.close();
  }

  // --- 1c-bis. a point two instances claim reaches the one that serves it --
  //
  // Every probe above is its own bbox's CENTRE, which the comment at 1c
  // concedes: nothing there exercises a point two instances both claim. Lake
  // Michigan makes that ordinary. Michigan's counties are water-inclusive, so
  // its bbox reaches Wisconsin's longitudes; Wisconsin's covers Michigan's
  // whole Upper Peninsula. Measured over 28 real places, the old nearest-CENTRE
  // rule misrouted 7. Routing now settles a contested point against each
  // instance's OWN published coverage ring, and misroutes 4.
  //
  // THE FOUR THAT REMAIN ARE HERE ON PURPOSE, as Ironwood. They are not a
  // tie-break failure: Michigan's fleet bbox was clipped to lng >= -87.60 at
  // go-live so it would stop containing Chicago's and Wisconsin's own centres,
  // and the bbox is still the cheap FIRST pass — so a point west of that line
  // is never offered to Michigan at all and no ring is ever consulted.
  // Reaching them means restoring Michigan's honest full bbox, which needs
  // validate_index's "must not contain a sibling's centre" rule relaxed AND
  // the in-app metro-portal moved off nearest-centre too: a larger change than
  // this one, recorded in mi/WATCH.md. Asserting the measured truth keeps this
  // file honest about what the fleet does today; when that change lands,
  // Ironwood flips to "mi" and the flip is the point.
  const OVERLAP_PROBES = [
    { name: "Marquette, Michigan", lat: 46.5436, lng: -87.3954, tag: "mi",
      why: "inside wi's bbox AND mi's; only Michigan's ring contains it" },
    { name: "Sturgeon Bay, Wisconsin", lat: 44.8342, lng: -87.3773, tag: "wi",
      why: "Door County, inside both boxes; only Wisconsin's ring contains it" },
    { name: "Dubuque, Iowa", lat: 42.5006, lng: -90.6646, tag: "ia",
      why: "claimed by THREE boxes — il, wi and ia — and served by one" },
    { name: "Rock Island, Illinois", lat: 41.5095, lng: -90.5787, tag: "il",
      why: "claimed by il and ia; the case a smallest-bbox-AREA rule gets wrong" },
    { name: "Ironwood, Michigan", lat: 46.4547, lng: -90.1710, tag: "wi",
      why: "MEASURED SHORTFALL: west of mi's clipped bbox, so no ring is consulted" },
  ];
  for (const probe of OVERLAP_PROBES) {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await page.route("**/photon.komoot.io/**", photonStub([
      photonFeature(...UNCOVERED_POINT),
      photonFeature(probe.lat, probe.lng),
    ]));
    await stubInstances(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.fill("#search-input", probe.name);
    await page.click("#search-button");
    await page.waitForTimeout(700);
    const u = new URL(page.url());
    check(`${probe.name} opens /${probe.tag}/ (${probe.why})`,
      u.pathname === `/${probe.tag}/`, page.url());
    await ctx.close();
  }

  // --- 1d. an address nobody covers SAYS SO, and never guesses -------------
  //
  // The honesty rule this whole project runs on, applied to the front door: a
  // point outside every bbox must not be routed anywhere. Sending it to the
  // nearest instance would be the front door inventing an answer.
  //
  // THE INSTANCE STUBS ARE LOAD-BEARING HERE, and their absence is how the
  // first draft of this block passed against a build with the bbox test
  // deleted: the wrong navigation went to the real districtry.com, which is
  // unreachable from the sandbox, so the failed navigation left page.url()
  // sitting on "/" and read exactly like the correct behaviour. Stubbed, a
  // wrong route lands on a real 200 and the pathname check fires. This is
  // therefore the block that proves the bbox filter exists at all.
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await page.route("**/photon.komoot.io/**", photonStub([photonFeature(...UNCOVERED_POINT)]));
    await stubInstances(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.fill("#search-input", "Dallas, Texas");
    await page.click("#search-button");
    await page.waitForTimeout(700);
    check("an uncovered address stays on the landing page",
      new URL(page.url()).pathname === "/", page.url());
    const msg = await textOrNull(page, "#search-status");
    check("an uncovered address is told so", /outside/i.test(msg || ""), JSON.stringify(msg));
    await ctx.close();
  }

  // --- 1e. a geocoder failure degrades to a message, not a dead button -----
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await page.route("**/photon.komoot.io/**", (r) => r.abort());
    await stubInstances(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.fill("#search-input", "200 S 9th St, Springfield IL");
    await page.click("#search-button");
    await page.waitForTimeout(700);
    const msg = await textOrNull(page, "#search-status");
    check("a failed search says so", /failed/i.test(msg || ""), JSON.stringify(msg));
    // The button must come back, or one flaky lookup bricks the box for the
    // rest of the visit.
    const disabled = await page.evaluate(
      () => document.getElementById("search-button")?.disabled).catch(() => null);
    check("a failed search re-enables the button", disabled === false, String(disabled));
    await ctx.close();
  }

  // --- 1f. the coverage map loads, draws, and lists every place -----------
  //
  // The map is a separate generated page embedded in an iframe, so the landing
  // page's own checks say nothing about it. Its legend is the accessible,
  // non-geometric statement of the same fact the polygons make — if the
  // outlines fail to load, the legend is what a reader is left with, so it is
  // what this asserts.
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    const errs = [];
    page.on("console", (mm) => {
      if (mm.type() !== "error") return;
      const t = mm.text();
      if (/Failed to load resource|net::ERR|gc\.zgo\.at/i.test(t)) return;
      errs.push(t);
    });
    page.on("pageerror", (e) => errs.push(String(e)));
    const vendored = await serveVendoredLeaflet(page);
    await stubTiles(page);
    const resp = await page.goto(BASE + "/coverage-map.html", { waitUntil: "load" });
    check("coverage map loads", resp.status() === 200, `HTTP ${resp.status()}`);
    await page.waitForTimeout(1500);
    check("coverage map has no console errors", errs.length === 0, errs.slice(0, 2).join(" | "));
    check("coverage map rendered a Leaflet map",
      await page.evaluate(() => !!document.querySelector(".leaflet-container")),
      vendored ? "vendored Leaflet" : "CDN Leaflet");
    const legend = await page.$$eval("#legend-rows a", (els) =>
      els.map((e) => ({ name: e.querySelector(".nm")?.textContent, href: e.getAttribute("href") })));
    check("coverage map legend lists every fleet place",
      legend.length === FLEET.length,
      JSON.stringify(legend.map((r) => r.name)) + " vs metros.json " + FLEET.length);
    check("coverage map legend links the fleet urls",
      legend.every((r) => FLEET.some((m) => m.url === r.href)),
      JSON.stringify(legend.map((r) => r.href)));
    // The outlines each come from their own instance's data/app — a 404 on one
    // is exactly the "drew Illinois for everybody" failure the two-tier map
    // exists to avoid, and it would otherwise show only as a missing polygon.
    const polys = await page.evaluate(() => document.querySelectorAll(".leaflet-overlay-pane path").length);
    check("coverage map drew the coverage outlines", polys > 0, `${polys} path(s)`);
    await ctx.close();
  }

  // --- 1g. the landing page actually embeds the coverage map --------------
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await serveVendoredLeaflet(page);
    await stubTiles(page);
    // `domcontentloaded`, NOT `load` — see section 6 for the measurement. This
    // check reads an iframe attribute and fetches the map separately; neither
    // needs the page's subresources, and the landing page carries a
    // third-party analytics tag that `load` would wait on.
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    const src = await page.getAttribute("iframe.coverage-frame", "src").catch(() => null);
    check("landing page embeds the coverage map", src === "coverage-map.html", String(src));
    const r = await page.request.get(BASE + "/coverage-map.html");
    check("the embedded coverage map resolves", r.status() === 200, `HTTP ${r.status()}`);
    await ctx.close();
  }

  // --- 2-4. old app links forward, carrying query AND hash ----------------
  //
  // /il/ IS STUBBED, and that is the point of this block. The guard's whole job
  // is to hand the instance the exact query+hash it was given; what the app then
  // does with that hash is the app's business, and it does plenty — booting, it
  // calls syncUrlHash() and rewrites location.hash into its own canonical form
  // (5-decimal coordinates, an appended &zoom=). Asserting the post-boot URL
  // therefore tests the APP's normalisation, not the guard.
  //
  // The first draft did exactly that and passed locally for the worst possible
  // reason: the sandbox cannot reach the Leaflet CDN, so the app never booted,
  // never rewrote the hash, and the byte comparison held. CI reached the CDN,
  // the app booted, and two checks failed on a guard that was working perfectly.
  // Stubbing the destination removes both the app and the network from the
  // measurement, so this asserts one thing and asserts it the same way
  // everywhere.
  for (const [name, query, hash] of [
    ["permalink", "", "#point=41.88250,-87.62850&layers=ward,school-board"],
    ["embed url", "?utm_source=embed&utm_medium=iframe", "#point=41.99,-87.66"],
    ["share link", "?utm_source=share&utm_medium=link", "#point=41.9,-87.6"],
    ["bare campaign tag", "?utm_source=share&utm_medium=link", ""],
  ]) {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await page.route("**/il/**", (r) =>
      r.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>il stub</title>" }));
    await page.goto(BASE + "/" + query + hash, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(400);
    const u = new URL(page.url());
    // Assert the stub actually served, never assume it: if the route pattern
    // stopped matching, the REAL app would load and rewrite the hash, and this
    // block would quietly go back to testing the app's normalisation.
    const title = await page.title();
    check(`${name} lands on the stub (not the live app)`, title === "il stub", title);
    check(`${name} forwards to /il/`, u.pathname === "/il/", page.url());
    check(`${name} keeps its query verbatim`, u.search === query, JSON.stringify(u.search));
    check(`${name} keeps its hash verbatim`, u.hash === hash, JSON.stringify(u.hash));
    await ctx.close();
  }

  // --- 5. an UNRELATED query must NOT forward (it is not an app link) ------
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await page.goto(BASE + "/?utm_source=newsletter", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(500);
    check("an unrelated campaign query stays on the landing page",
      new URL(page.url()).pathname === "/", page.url());
    await ctx.close();
  }

  // --- 6. no console errors on the landing page ---------------------------
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    const errs = [];
    // Ignore network unreachability, the same way all three instance smoke tests do.
    // This page carried no external script at all until it took the fleet's GoatCounter
    // tag, so the check could afford to be absolute; now gc.zgo.at is a third-party host
    // that is unroutable from the sandbox and can be slow or down in CI. A failed request
    // to it says nothing about whether the page boots — which is what this check is for.
    // An *app* JS error still surfaces, via pageerror below and any non-network console error.
    page.on("console", (m) => {
      if (m.type() !== "error") return;
      const t = m.text();
      if (/Failed to load resource|net::ERR|gc\.zgo\.at|googletagmanager/i.test(t)) return;
      errs.push(t);
    });
    page.on("pageerror", (e) => errs.push(String(e)));
    // `domcontentloaded`, NOT `load`, AND THE DIFFERENCE IS MEASURED. The filter
    // above says a failed request to gc.zgo.at must not fail this check — and
    // `load` waits for that request to settle, so a run where the host HANGS
    // rather than refusing dies at `page.goto: Timeout 30000ms exceeded` before
    // the filter is ever consulted. The check asserted the opposite of what its
    // own comment promised. Measured on 2026-09-06 by routing gc.zgo.at to a
    // handler that never responds: `load` threw at 30,003 ms, this passed in
    // 19 ms. Sandboxes where the host is simply unroutable fail FAST and never
    // see it, which is why CI found it and a local run did not.
    //
    // Nothing is lost: `pageerror` and non-network console errors — the app JS
    // failures this exists to catch — fire during parse and execution, and the
    // 500 ms settle below still gives late ones time to arrive. The landing
    // page is the only root page carrying that tag, so privacy.html and
    // coverage-map.html deliberately keep `load`.
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(500);
    check("landing page boots with no console errors", errs.length === 0, errs.slice(0, 2).join(" | "));
    await ctx.close();
  }
  // --- 7. the fleet privacy page ------------------------------------------
  //
  // Generated and drift-checked by build_privacy_page.py, which proves the page
  // matches what the apps do. As with the landing page, that cannot prove it
  // WORKS, and two things here are invisible to a diff.
  //
  // The first is the theme boot. This page is reached FROM an app that has a
  // dark toggle, and it applies the stored choice in <head> before first paint;
  // a reader who picked dark must not be handed a white flash. Nothing in a
  // diff can tell you whether that ran.
  //
  // The second is the reachability of the link itself. The page moved from
  // il/privacy.html to the root, which turned every in-app link into a `../`
  // hop — from il/, ny/ and ca/ alike, and from five sub-pages that had never
  // carried one. A wrong number of dots is a 404 that no gate here would
  // otherwise see: validate_card_links.py probes ABSOLUTE urls, so a relative
  // href is not its subject at all.
  for (const scheme of ["light", "dark"]) {
    const ctx = await browser.newContext({ serviceWorkers: "block", colorScheme: scheme });
    const page = await ctx.newPage();
    const errs = [];
    page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
    page.on("pageerror", (e) => errs.push(String(e)));
    const resp = await page.goto(BASE + "/privacy.html", { waitUntil: "load" });
    check(`privacy page loads (${scheme})`, resp.status() === 200, `HTTP ${resp.status()}`);
    check(`privacy page has no console errors (${scheme})`, errs.length === 0,
      errs.slice(0, 2).join(" | "));

    // The ground must follow the scheme. A page whose only dark rule lived in a
    // media query, or whose body had no explicit background, would pass a diff
    // and read as a white sheet in a dark client.
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    const lum = (s) => { const [r, g, b] = s.match(/\d+/g).map(Number); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
    check(`privacy page paints a ${scheme} ground`, (lum(bg) < 90) === (scheme === "dark"), bg);

    // One row per app, read from the manifest rather than counted by hand: a
    // new instance that never reached the privacy table is the failure this
    // catches, and it is exactly the shape of the bug this page was built to
    // end (an app with no privacy page of its own).
    const appRows = await page.evaluate(() =>
      Array.from(document.querySelectorAll("table")[0].querySelectorAll("tbody tr"))
        .map((r) => r.querySelector("th").innerText.split("\n")[1]));
    for (const tag of TAGS) {
      check(`privacy table has a row for /${tag}/`, appRows.includes(`/${tag}/`), appRows.join(" "));
    }
    await ctx.close();
  }

  // A dark choice made in an app must survive the hop to this page.
  {
    const ctx = await browser.newContext({ serviceWorkers: "block", colorScheme: "light" });
    await ctx.addInitScript(() => {
      try { localStorage.setItem("districtry-theme", "dark"); } catch (e) { /* private mode */ }
    });
    const page = await ctx.newPage();
    await page.goto(BASE + "/privacy.html", { waitUntil: "domcontentloaded" });
    const attr = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    check("a dark choice made in an app carries to the privacy page",
      attr === "dark" && /rgb\(2?\d, /.test(bg), `data-theme=${attr} bg=${bg}`);
    await ctx.close();
  }

  // --- 8. every app links the privacy page, and the link resolves ----------
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    for (const where of ["/", ...TAGS.map((t) => `/${t}/`)]) {
      await page.goto(BASE + where, { waitUntil: "domcontentloaded" });
      const href = await page.evaluate(() => {
        const a = Array.from(document.querySelectorAll("a[href]"))
          .find((x) => /privacy\.html$/.test(x.getAttribute("href")));
        return a ? a.href : null;
      });
      check(`${where} links the privacy page`, href !== null, String(href));
      if (!href) continue;
      const r = await page.request.get(href);
      check(`${where}'s privacy link resolves`, r.status() === 200,
        `${href} -> HTTP ${r.status()}`);
    }
    await ctx.close();
  }
} finally {
  await browser.close();
}

if (failures.length) {
  console.error(`\n${failures.length} root-page check(s) failed: ${failures.join(", ")}`);
  process.exit(1);
}
console.log("\nAll root-page checks passed.");
