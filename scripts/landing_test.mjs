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
import { chromium, devices } from "playwright";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { stubBasemap } from "./basemap_stub.mjs";

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
// The host the site is served at, which the manifest's share target names.
const SITE_HOST = readFileSync(join(HERE, "..", "CNAME"), "utf8").trim();
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

// A service worker's own requests reach Playwright only behind this flag, and
// block 9b counts the launcher worker's requests to prove a share never
// leaves the phone. Read at launch, so it is set here rather than in the job.
process.env.PW_EXPERIMENTAL_SERVICE_WORKER_NETWORK_EVENTS = "1";
const browser = stubBasemap(await chromium.launch());
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

    // The state list under the coverage map: every state and DC, once each,
    // a link where a place answers and plain text where none does. It
    // replaced a row per live place plus a folded "not yet" list on
    // 2026-10-13, so it carries what both used to: the place's scope and its
    // layer count, and an honest account of the rest of the country.
    const states = await page.$$eval(".states li", (els) =>
      els.map((li) => {
        const a = li.querySelector("a.st");
        return {
          name: li.querySelector(".st-name")?.textContent?.trim(),
          href: a ? a.getAttribute("href") : null,
          part: !!(a && a.classList.contains("st-part")),
          scope: li.querySelector(".st-scope")?.textContent?.replace(/\s+/g, " ").trim(),
          n: li.querySelector(".st-n")?.textContent?.trim(),
          text: li.textContent.replace(/\s+/g, " ").trim(),
        };
      }));
    const linked = states.filter((s) => s.href);
    check("the state list names every state and DC once",
      states.length === 51 && new Set(states.map((s) => s.name)).size === 51,
      `${states.length} row(s), ${new Set(states.map((s) => s.name)).size} distinct`);
    check("every fleet place is linked exactly once",
      linked.length === FLEET.length &&
        FLEET.every((m) => linked.filter((l) => l.href === m.url).length === 1),
      JSON.stringify(linked.map((l) => l.href)) + " vs metros.json " + FLEET.length);
    check("Illinois row points at /il/",
      linked.some((p) => p.name === "Illinois" && /\/il\/$/.test(p.href)),
      linked.find((p) => p.name === "Illinois")?.href);
    // A layer count is the one number on this page a reader could act on, and
    // it is read from each instance's own worksheet — a row showing 0, blank
    // or NaN means the generator lost its grip on that file.
    check("every place states a positive layer count",
      linked.every((p) => /^\d+$/.test(p.n || "") && Number(p.n) > 0),
      JSON.stringify(linked.map((p) => p.n)));
    check("every place states its scope",
      linked.every((p) => (p.scope || "").length > 2),
      JSON.stringify(linked.map((p) => p.scope)));
    // A city instance sits on its STATE's row and says the city is all that
    // answers there. California reading as a covered state, or vanishing from
    // the list because San Francisco is not a state, are the two ways to get
    // this wrong, and each would tell a reader in Los Angeles something false.
    const cities = FLEET.filter((m) => !states.some((s) => s.name === m.landing_name));
    check("a city's row is its state's, and names the city",
      cities.length > 0 && cities.every((m) => {
        const row = linked.find((l) => l.href === m.url);
        return row && row.part && row.name !== m.landing_name &&
          (row.scope || "").startsWith(m.landing_name + " only");
      }),
      JSON.stringify(cities.map((m) => linked.find((l) => l.href === m.url))));
    // An unlinked row is marked "not yet" by an empty square, which a screen
    // reader cannot see, so the words have to be there too.
    check("every state nobody covers says not yet",
      states.filter((s) => !s.href).every((s) => /not yet$/.test(s.text)),
      JSON.stringify(states.filter((s) => !s.href && !/not yet$/.test(s.text)).map((s) => s.name)));
    // The count above the list and the sentence under the address box are one
    // phrase from one function, and both must agree with the list itself.
    const nStates = linked.filter((l) => !l.part && l.name !== "District of Columbia").length;
    const countLine = (await textOrNull(page, ".cov-count strong") || "").replace(/\s+/g, " ").trim();
    const helpLine = (await textOrNull(page, ".search-help") || "").replace(/\s+/g, " ").trim();
    check("the count line counts the linked states",
      new RegExp("^" + nStates + " states? ").test(countLine) &&
        cities.every((m) => countLine.includes(m.landing_name)),
      JSON.stringify(countLine) + ` vs ${nStates} state row(s)`);
    check("the address box says the same count",
      helpLine.includes(countLine.replace(/\.$/, "")), JSON.stringify(helpLine));
    // On a screen wider than a phone the list is never folded and its toggle
    // is not drawn; section 1h holds the phone half.
    const wide = await page.evaluate(() => {
      const box = document.querySelector(".states-box");
      const t = document.querySelector(".states-toggle");
      return { open: !!(box && box.open), toggle: t ? getComputedStyle(t).display : null,
               shown: [...document.querySelectorAll(".states li")].filter((li) => li.checkVisibility()).length };
    });
    check("on a wide screen the state list is open with no toggle",
      wide.open && wide.toggle === "none" && wide.shown === 51, JSON.stringify(wide));

    // THE QUESTION ROWS ARE THE FRONT DOOR'S INTERNAL LINKS, and the whole
    // reason this block exists: the 2026-09-15 search audit found the root
    // linking none of them while /il/ward.html sat uncrawled. Regrouping them
    // by question in 2026-09-18 moved the question out of the link text, so
    // the chip now carries a place AND a topic — a link reading only
    // "Illinois" says nothing about where it points. Two chips alike means one
    // of them is unlabelled, which the generator refuses to emit; this asserts
    // it in the rendered page.
    const chips = await page.$$eval(".ask-chips a", (els) =>
      els.map((e) => ({ href: e.getAttribute("href"), text: e.textContent.replace(/\s+/g, " ").trim() })));
    check("the question rows link every question page",
      chips.length >= 20 && chips.every((c) => /^\/[a-z]{2}\/[a-z-]+\.html$/.test(c.href)),
      `${chips.length} chip(s): ` + JSON.stringify(chips.slice(0, 2)));
    check("no two question links read the same",
      new Set(chips.map((c) => c.text)).size === chips.length,
      JSON.stringify(chips.map((c) => c.text)));
    check("every question link names a place and a topic",
      chips.every((c) => /\S \u00b7 \S/.test(c.text)),
      JSON.stringify(chips.filter((c) => !/\S \u00b7 \S/.test(c.text)).map((c) => c.text)));
    // Each row's heading is the question; a chip with no heading above it is a
    // link a reader meets with no idea what it answers.
    const rows = await page.$$eval(".ask", (els) =>
      els.map((e) => ({ q: e.querySelector("h3")?.textContent?.trim(), n: e.querySelectorAll("a").length })));
    check("every question row has a heading and at least one place",
      rows.length > 3 && rows.every((r) => (r.q || "").length > 8 && r.n > 0),
      JSON.stringify(rows));

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

  // --- 1b. the notice: the Android test invitation, on Android only --------
  //
  // The front page's notice (NOTICE in build_landing_page.py) invites Android
  // readers into the Google Play app's closed test. It ships hidden and the
  // page's script shows it, so the script is what is under test: shown in an
  // Android browser and nowhere else, never inside the Play app or an
  // installed copy, linking the steps page with its ref, and closed on
  // request. It sits in the page's flow above the masthead and no longer
  // fades, so one that would not close would hold the address box down for
  // the whole visit. A close or a followed link is remembered (Adam,
  // 2026-10-20: a "no" stays closed) under the key the maps' own invitation
  // to the test uses, so an answer on either page keeps both closed, while a
  // reader who has only SEEN the maps' bar is still shown this one.
  {
    async function noticeOn(opts, path, init, initArg) {
      const ctx = await browser.newContext({ ...opts, serviceWorkers: "block" });
      const page = await ctx.newPage();
      if (init) await page.addInitScript(init, initArg);
      await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(300);
      const shown = await page.isVisible("#notice").catch(() => false);
      return { ctx, page, shown };
    }
    const android = devices["Pixel 7"];
    {
      const { ctx, page, shown } = await noticeOn({}, "/");
      check("the notice is in the page", (await page.$("#notice")) !== null);
      check("a computer is not shown the Android invitation", !shown, String(shown));
      await ctx.close();
    }
    {
      const { ctx, shown } = await noticeOn(devices["iPhone 14"], "/");
      check("an iPhone is not shown the Android invitation", !shown, String(shown));
      await ctx.close();
    }
    {
      const { ctx, page, shown } = await noticeOn(android, "/");
      check("an Android phone is shown the invitation", shown, String(shown));
      if (shown) {
        const link = await page.$eval(".notice-cta a", (a) => {
          const r = a.getBoundingClientRect();
          return { href: a.getAttribute("href"), w: Math.round(r.width), h: Math.round(r.height) };
        }).catch(() => null);
        check("the invitation links the steps page, tagged for the traffic report",
          !!link && link.href === "/android.html?ref=front-page", JSON.stringify(link));
        check("the invitation's link is at least a 24px target",
          !!link && link.w >= 24 && link.h >= 24, JSON.stringify(link));
        const close = await page.$eval("#notice-dismiss", (b) => {
          const r = b.getBoundingClientRect();
          return [Math.round(r.width), Math.round(r.height)];
        });
        check("the close button is at least a 24px target",
          close[0] >= 24 && close[1] >= 24, JSON.stringify(close));
        await page.click("#notice-dismiss");
        const after = await page.isVisible("#notice");
        check("closing the invitation hides it", !after, String(after));
        const kept = await page.evaluate(() => localStorage.getItem("districtry-install-invite"));
        check("closing the invitation is remembered under the maps' invitation key",
          kept === "test-answered", String(kept));
        await page.reload({ waitUntil: "domcontentloaded" });
        await page.waitForTimeout(300);
        const again = await page.isVisible("#notice");
        check("a closed invitation stays closed on the next visit", !again, String(again));
      }
      await ctx.close();
    }
    {
      const { ctx, page, shown } = await noticeOn(android, "/");
      let kept = null;
      let again = null;
      if (shown) {
        await Promise.all([
          page.waitForURL(/\/android\.html/, { timeout: 15000 }).catch(() => null),
          page.click(".notice-cta a"),
        ]);
        kept = await page.evaluate(() => localStorage.getItem("districtry-install-invite"));
        await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(300);
        again = await page.isVisible("#notice");
      }
      check("following the invitation's link is remembered too, and it is not shown again",
        shown && kept === "test-answered" && again === false, JSON.stringify({ shown, kept, again }));
      await ctx.close();
    }
    for (const [stored, want, what] of [
      ["test-shown", true, "an Android phone that has only seen the maps' invitation is still shown this one"],
      ["test-answered", false, "an Android phone that closed or followed the maps' invitation is not shown this one"],
    ]) {
      const { ctx, shown } = await noticeOn(android, "/", (v) => {
        try { localStorage.setItem("districtry-install-invite", v); } catch (e) { /* reported by the check */ }
      }, stored);
      check(what, shown === want, String(shown));
      await ctx.close();
    }
    // Inside the Google Play app, which opens its first page with ref=play
    // (engine/shared/play-app.txt marks the window in the head).
    {
      const { ctx, shown } = await noticeOn(android, "/?ref=play");
      check("the Play app is not shown the invitation", !shown, String(shown));
      await ctx.close();
    }
    // An installed copy reports display-mode standalone, which Playwright
    // cannot emulate, so matchMedia is made to answer it.
    {
      const { ctx, shown } = await noticeOn(android, "/", () => {
        const real = window.matchMedia.bind(window);
        window.matchMedia = (q) => /display-mode:\s*standalone/.test(q)
          ? { matches: true, media: q, onchange: null,
              addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }
          : real(q);
      });
      check("an installed copy is not shown the invitation", !shown, String(shown));
      await ctx.close();
    }
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
  // Wait for the address box to SETTLE, not for a fixed time. It reads
  // fleet-outlines.json before it decides, and on a busy runner that took
  // longer than the 700 ms these checks used to sleep: on 2026-10-13, with
  // thirteen outlines in the file, Illinois (the first case, so the first
  // fetch) read the landing page's own URL. Settled means the page navigated
  // or the status line shows one of its error-class endings (outside every
  // place, no matches, search failed). A navigation destroys the page's
  // context, so the status test's rejection is swallowed rather than allowed
  // to win the race before the new URL commits; the deadline falls through to
  // the check, which reports what it found.
  async function addressSettled(page) {
    const timeout = 10000;
    await Promise.race([
      page.waitForURL((u) => u.pathname !== "/", { timeout, waitUntil: "commit" }),
      page.waitForFunction(() => {
        const s = document.getElementById("search-status");
        return !!s && s.classList.contains("err");
      }, null, { timeout }).catch(() => new Promise(() => {})),
    ]).catch(() => {});
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
    await addressSettled(page);
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
  // IRONWOOD FLIPPED TO "mi" ON 2026-09-28, as this comment said it would.
  // It sits west of Michigan's clipped bbox, so the rectangle pass never
  // offered it to Michigan; the page now asks fleet-outlines.json first — the
  // file the apps' own hand-off reads — and Michigan's outline contains it.
  // The rectangle pass survives only for when that file cannot be read, which
  // 1c-ter below holds.
  const OVERLAP_PROBES = [
    { name: "Marquette, Michigan", lat: 46.5436, lng: -87.3954, tag: "mi",
      why: "inside wi's bbox AND mi's; only Michigan's ring contains it" },
    { name: "Sturgeon Bay, Wisconsin", lat: 44.8342, lng: -87.3773, tag: "wi",
      why: "Door County, inside both boxes; only Wisconsin's ring contains it" },
    { name: "Dubuque, Iowa", lat: 42.5006, lng: -90.6646, tag: "ia",
      why: "claimed by THREE boxes — il, wi and ia — and served by one" },
    { name: "Rock Island, Illinois", lat: 41.5095, lng: -90.5787, tag: "il",
      why: "claimed by il and ia; the case a smallest-bbox-AREA rule gets wrong" },
    { name: "Ironwood, Michigan", lat: 46.4547, lng: -90.1710, tag: "mi",
      why: "west of mi's clipped bbox; only Michigan's outline contains it" },
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
    await addressSettled(page);
    const u = new URL(page.url());
    check(`${probe.name} opens /${probe.tag}/ (${probe.why})`,
      u.pathname === `/${probe.tag}/`, page.url());
    await ctx.close();
  }

  // --- 1c-ter. with the outline file unreachable, the rectangles answer -----
  //
  // fleet-outlines.json is refused here, so the page must fall back to the
  // bbox pass rather than route nothing. Rock Island is claimed by il and ia
  // and settled by the rings, so it exercises the whole fallback, not only
  // its one-claimant shortcut.
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await page.route("**/fleet-outlines.json", (r) => r.abort());
    await page.route("**/photon.komoot.io/**", photonStub([photonFeature(41.5095, -90.5787)]));
    await stubInstances(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.fill("#search-input", "Rock Island, Illinois");
    await page.click("#search-button");
    await addressSettled(page);
    check("with fleet-outlines.json unreachable, Rock Island still opens /il/ by the rectangle pass",
      new URL(page.url()).pathname === "/il/", page.url());
    await ctx.close();
  }

  // --- 1c-quater. an address a rectangle claims and nobody serves ----------
  //
  // Clayton, Missouri sits inside Illinois's bbox, so the rectangle pass sent
  // it to an app with nothing to show there. It is about 13 km from Illinois's
  // outline, well past the tolerance the page allows a simplified edge.
  //
  // THIS WAS GARY, INDIANA UNTIL 2026-10-07, when Indiana went live and Gary
  // became an address the front door must OPEN /in/ for (asserted just below).
  // Downtown St. Louis was not used: it is about 1.6 km from Illinois's
  // simplified outline, close enough to the page's ~1.5 km allowance that the
  // test would be deciding a rounding question rather than this one.
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await page.route("**/photon.komoot.io/**", photonStub([photonFeature(38.6426, -90.3237)]));
    await stubInstances(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.fill("#search-input", "Clayton, Missouri");
    await page.click("#search-button");
    await addressSettled(page);
    check("Clayton, Missouri stays on the landing page though Illinois's bbox claims it",
      new URL(page.url()).pathname === "/", page.url());
    const msg = await textOrNull(page, "#search-status");
    check("Clayton, Missouri is told it is outside every covered place", /outside/i.test(msg || ""), JSON.stringify(msg));
    await ctx.close();
  }
  // ...and Gary, which Illinois's bbox ALSO claims, opens Indiana: the outline
  // pass decides, so the rectangle that contains it is never consulted.
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await page.route("**/photon.komoot.io/**", photonStub([photonFeature(41.6020, -87.3372)]));
    await stubInstances(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.fill("#search-input", "Gary, Indiana");
    await page.click("#search-button");
    await addressSettled(page);
    check("Gary, Indiana opens /in/ though Illinois's bbox also claims it",
      new URL(page.url()).pathname === "/in/", page.url());
    await ctx.close();
  }

  // --- 1c-quinquies. a pasted map link is read here, never geocoded --------
  //
  // engine/shared/map-link.txt reads the position out of a full Google Maps
  // link in the browser, so the front door opens the app that covers it and
  // Photon is never asked. The Photon route records any request at all, so a
  // build that sent the link to the geocoder as address text fails here even
  // though the stub would have answered it.
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    let photonAsked = false;
    await page.route("**/photon.komoot.io/**", (r) => { photonAsked = true; return photonStub([])(r); });
    await stubInstances(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.fill("#search-input", "https://www.google.com/maps/place/Lambeau+Field/@44.50,-88.06,12z/data=!3m1!4b1!8m2!3d44.5013!4d-88.0622");
    await page.click("#search-button");
    await page.waitForTimeout(700);
    check("a pasted Google Maps link in Green Bay opens /wi/", new URL(page.url()).pathname === "/wi/", page.url());
    check("a pasted Google Maps link is never sent to the geocoder", !photonAsked, String(photonAsked));
    await ctx.close();
  }
  // ...a short link goes to districtry's own lookup, and the full link it
  // answers opens the app that covers that place. The lookup is stubbed, so
  // this asserts what the page ASKS for (only the short link, as `u=`) and
  // does with the answer, not that Google still redirects the same way.
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    let photonAsked = false;
    const lookupAsked = [];
    await page.route("**/photon.komoot.io/**", (r) => { photonAsked = true; return photonStub([])(r); });
    await page.route("**/link-lookup.districtry.deno.net/**", (r) => {
      lookupAsked.push(new URL(r.request().url()).searchParams.get("u"));
      return r.fulfill({ status: 200, contentType: "application/json",
        body: JSON.stringify({ url: "https://www.google.com/maps/place/Lambeau+Field/@44.50,-88.06,12z/data=!3m1!4b1!8m2!3d44.5013!4d-88.0622" }) });
    });
    // the counter is stubbed, and each count it is handed is recorded outside
    // the page, because the page navigates away straight after counting
    const counted = [];
    await page.route("**/gc.zgo.at/**", (r) => r.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
    await page.exposeFunction("__gcCount", (path) => { counted.push(path); });
    await page.addInitScript(() => {
      window.goatcounter = { count: (vars) => { if (vars && vars.event) window.__gcCount(vars.path); } };
    });
    await stubInstances(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.fill("#search-input", "https://maps.app.goo.gl/AbCdEf123");
    await page.click("#search-button");
    await page.waitForTimeout(700);
    check("a short map link is sent to the lookup, and only the link",
      lookupAsked.length === 1 && lookupAsked[0] === "https://maps.app.goo.gl/AbCdEf123", JSON.stringify(lookupAsked));
    check("a short map link to Green Bay opens /wi/", new URL(page.url()).pathname === "/wi/", page.url());
    check("a short map link is never sent to the geocoder", !photonAsked, String(photonAsked));
    check("the front page counts the short link it read once, by kind and where it went",
      counted.join() === "map-link-read/front/google/short/pasted/to-wi", JSON.stringify(counted));
    await ctx.close();
  }
  // ...a lookup that fails once is asked again, and the second answer is used
  // (ENGINE map-link resolveShortMapLink: a try again after 1.5 seconds)...
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    let lookups = 0;
    await page.route("**/photon.komoot.io/**", photonStub([]));
    await page.route("**/link-lookup.districtry.deno.net/**", (r) => ++lookups === 1
      ? r.fulfill({ status: 502, contentType: "application/json", body: JSON.stringify({ error: "the link could not be followed" }) })
      : r.fulfill({ status: 200, contentType: "application/json",
          body: JSON.stringify({ url: "https://www.google.com/maps/place/Lambeau+Field/@44.50,-88.06,12z/data=!3m1!4b1!8m2!3d44.5013!4d-88.0622" }) }));
    await stubInstances(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.fill("#search-input", "https://maps.app.goo.gl/AbCdEf123");
    await page.click("#search-button");
    await page.waitForTimeout(600);
    const between = await textOrNull(page, "#search-status");
    await page.waitForURL((u) => new URL(u).pathname === "/wi/", { timeout: 6000 }).catch(() => {});
    check("a lookup that fails once says it is trying again", /trying again/i.test(between || ""), JSON.stringify(between));
    check("a lookup that fails once is asked again, and its answer opens /wi/",
      lookups === 2 && new URL(page.url()).pathname === "/wi/", lookups + " lookup(s), at " + page.url());
    await ctx.close();
  }
  // ...and when the lookup still cannot follow it, the page says which side
  // failed, and no longer sends a phone reader to an address bar
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    let photonAsked = false, lookups = 0;
    await page.route("**/photon.komoot.io/**", (r) => { photonAsked = true; return photonStub([])(r); });
    await page.route("**/link-lookup.districtry.deno.net/**", (r) => {
      lookups++;
      return r.fulfill({ status: 502, contentType: "application/json", body: JSON.stringify({ error: "the link could not be followed" }) });
    });
    await stubInstances(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.fill("#search-input", "https://maps.app.goo.gl/AbCdEf123");
    await page.click("#search-button");
    await page.waitForSelector("#search-status.err", { timeout: 12000 }).catch(() => {});
    const msg = await textOrNull(page, "#search-status");
    check("a short map link the lookup cannot follow is asked three times in all", lookups === 3, String(lookups));
    check("a short map link the lookup cannot follow stays on the landing page and says Google didn't answer",
      new URL(page.url()).pathname === "/" && /couldn't be read just now \(Google didn't answer/.test(msg || "") &&
      !/address bar/.test(msg || ""), JSON.stringify(msg));
    check("a short map link is never sent to the geocoder, even when the lookup fails", !photonAsked, String(photonAsked));
    await ctx.close();
  }

  // ...a link from the Google Maps app carries no position, only the place's
  // name and address in one string. When that matches nothing, the address
  // alone is asked, and an answer counts only if it is the address's house,
  // its number on its street (ENGINE map-link labelAtHouse; until
  // 2026-10-19 the number anywhere in the label, labelCarriesNumber): a
  // street that merely partly matches must route nowhere. The address's own street in its own
  // town, without the number (labelOnStreet), opens the app that covers it
  // with what was typed, so that app shows the street (showStreetOnly).
  // Typed text gets no such retry.
  //
  // AND A LINK GOES ONLY TO THE APP OF THE STATE ITS ADDRESS NAMES (namedState,
  // ENGINE map-link addressStateTag): an answer elsewhere is another place of
  // that name, and when nothing there answers, the link is handed to that app,
  // rebuilt from its words (mapLinkForText), so its own search tries the
  // address, the street and the name. On 2026-10-16 a Wisconsin place's short
  // link said "No matches" here. A state no app covers is said to be, with
  // nothing searched, and California, where San Francisco's app covers one
  // city, is routed by position as before.
  {
    const NAMED = "Lambeau Field, 1265 Lombardi Ave, Green Bay, WI 54304";
    const BARE = "1265 Lombardi Ave, Green Bay, WI 54304";
    const FULL = "https://maps.google.com/?q=Lambeau+Field,+1265+Lombardi+Ave,+Green+Bay,+WI+54304&ftid=0x0:0x1&entry=gps";
    const REBUILT = "#q=" + encodeURIComponent("https://www.google.com/maps?q=Lambeau+Field,+1265+Lombardi+Ave,+Green+Bay,+WI+54304");
    const OHIO = "https://maps.google.com/?q=Union+Terminal,+1301+Western+Ave,+Cincinnati,+OH+45203&ftid=0x0:0x2&entry=gps";
    const LA_NAMED = "Grand Central Market, 317 S Broadway, Los Angeles, CA 90013";
    const LA = "https://maps.google.com/?q=Grand+Central+Market,+317+S+Broadway,+Los+Angeles,+CA+90013&ftid=0x0:0x3&entry=gps";
    const at = (props) => ({ ...photonFeature(44.5013, -88.0622), properties: props });
    for (const c of [
      { name: "an answer carrying its house number opens /wi/", text: FULL, answer: at({ housenumber: "1265", street: "Lombardi Avenue" }),
        asks: [NAMED, BARE], want: "/wi/", hash: /^#point=44\.50130,-88\.06220$/ },
      { name: "a street without its house number selects no point, and the link goes to /wi/, the state its address names",
        text: FULL, answer: at({ street: "Lombardi Avenue" }), asks: [NAMED, BARE], want: "/wi/", hash: REBUILT },
      { name: "its street in its town, without the number, opens /wi/ with the link to show the street",
        text: FULL, answer: at({ name: "Lombardi Avenue", city: "Green Bay", state: "Wisconsin", postcode: "54304" }),
        asks: [NAMED, BARE], want: "/wi/", hash: REBUILT },
      { name: "an answer in Illinois is another place of its name, and the link goes to /wi/",
        text: FULL, answerFor: (q) => (q === NAMED ? [photonFeature(41.8825, -87.6285)] : []),
        asks: [NAMED], want: "/wi/", hash: REBUILT },
      { name: "a place in Ohio, which no app covers, is said to be, and nothing is searched",
        text: OHIO, answerFor: () => [], asks: [], want: "/",
        msg: /^That place is in Ohio, which districtry doesn't cover yet/ },
      { name: "a place in Los Angeles is routed by its position, since San Francisco's app covers one city",
        text: LA, answerFor: (q) => (q === LA_NAMED ? [photonFeature(34.0508, -118.2489)] : []),
        asks: [LA_NAMED], want: "/", msg: /outside every place districtry covers/ },
      { name: "the same words typed are not retried", text: NAMED, answer: at({ housenumber: "1265", street: "Lombardi Avenue" }),
        asks: [NAMED], want: "/" },
    ]) {
      const ctx = await browser.newContext({ serviceWorkers: "block" });
      const page = await ctx.newPage();
      const asked = [];
      await page.route("**/photon.komoot.io/**", (r) => {
        const q = new URL(r.request().url()).searchParams.get("q");
        asked.push(q);
        return photonStub(c.answerFor ? c.answerFor(q) : q === BARE ? [c.answer] : [])(r);
      });
      await stubInstances(page);
      await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
      await page.fill("#search-input", c.text);
      await page.click("#search-button");
      await addressSettled(page);
      const hash = new URL(page.url()).hash;
      const msg = c.msg ? await textOrNull(page, "#search-status") : null;
      check(`a place's name and address that match nothing whole: ${c.name}`,
        JSON.stringify(asked) === JSON.stringify(c.asks) && new URL(page.url()).pathname === c.want &&
          (!c.hash || (c.hash instanceof RegExp ? c.hash.test(hash) : hash === c.hash)) && (!c.msg || c.msg.test(msg || "")),
        JSON.stringify({ asked, url: page.url(), msg }));
      await ctx.close();
    }
    // The case Adam met: a short link to a Wisconsin place, read by the
    // lookup, whose words and address match nothing, is handed to /wi/.
    {
      const ctx = await browser.newContext({ serviceWorkers: "block" });
      const page = await ctx.newPage();
      const asked = [], looked = [];
      await page.route("**/photon.komoot.io/**", (r) => { asked.push(new URL(r.request().url()).searchParams.get("q")); return photonStub([])(r); });
      await page.route("**/link-lookup.districtry.deno.net/**", (r) => {
        looked.push(new URL(r.request().url()).searchParams.get("u"));
        return r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ url: FULL }) });
      });
      await stubInstances(page);
      await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
      await page.fill("#search-input", "https://maps.app.goo.gl/AbCdEf123");
      await page.click("#search-button");
      await addressSettled(page);
      check("a short link to a Wisconsin place that matches nothing here opens /wi/ with the link, not \"No matches\"",
        looked.length === 1 && JSON.stringify(asked) === JSON.stringify([NAMED, BARE]) &&
          new URL(page.url()).pathname === "/wi/" && new URL(page.url()).hash === REBUILT,
        JSON.stringify({ looked, asked, url: page.url() }));
      await ctx.close();
    }
  }

  // ...AN ADDRESS TYPED WITH NO NAME IN FRONT is held to its house number
  // from the first try (searchAndRoute `whole`, as in the apps): an answer
  // without the number is a street, and its point a spot somewhere along it,
  // so the app covering the address's street (addressInTownOf), or else the
  // first covered answer, is opened with what was typed and never with a
  // point. An answer that is the house (labelAtHouse) still opens its point,
  // and since 2026-10-19 an answer with the number on another street does
  // not. An address that names a state whose app covers the whole state is
  // handed to that app when no answer is in a place districtry covers, so
  // that its search asks the Census Bureau's address records. The number and
  // the street's spot are made up.
  {
    const TYPED = "9 W Oakley Dr NW, Westmont, IL";
    const NO_STATE = "9 W Oakley Dr NW, Westmont";
    const NO_TOWN = "9 W Oakley Dr NW";
    const at = (props) => ({ ...photonFeature(41.82196, -87.97949), properties: props });
    const ON = at({ name: "West Oakley Drive Northwest", city: "Westmont", state: "Illinois", postcode: "60559" });
    const OTHER = at({ name: "Oakley Drive North", city: "Westmont", state: "Illinois", postcode: "60559" });
    const HOUSE = at({ housenumber: "9", street: "West Oakley Drive Northwest", city: "Westmont", state: "Illinois" });
    const OTHER_HOUSE = at({ housenumber: "9", street: "Oakley Drive North", city: "Westmont", state: "Illinois", postcode: "60559" });
    const TEXAS = { ...photonFeature(...UNCOVERED_POINT), properties: { name: "Oakley Drive", city: "Dallas", state: "Texas" } };
    for (const c of [
      { name: "its street without the number opens /il/ with the address, not a point", text: TYPED, answer: [ON],
        want: "/il/", hash: "#q=" + encodeURIComponent(TYPED) },
      { name: "typed with no town, its street opens /il/ with what was typed", text: NO_TOWN, answer: [ON],
        want: "/il/", hash: "#q=" + encodeURIComponent(NO_TOWN) },
      { name: "an answer on another street, without the number, opens /il/ with the address, not that street's point",
        text: TYPED, answer: [OTHER], want: "/il/", hash: "#q=" + encodeURIComponent(TYPED) },
      { name: "an answer that is the house opens its point, as before", text: TYPED, answer: [ON, HOUSE],
        want: "/il/", hash: /^#point=41\.82196,-87\.97949$/ },
      { name: "its number on another street opens /il/ with the address, not that house's point", text: TYPED,
        answer: [OTHER_HOUSE], want: "/il/", hash: "#q=" + encodeURIComponent(TYPED) },
      { name: "answers no app covers, to an address that names no state, are said to be outside", text: NO_STATE,
        answer: [TEXAS], want: "/", msg: /outside every place districtry covers/ },
      { name: "answers no app covers, to an address in Illinois, open /il/ with the address", text: TYPED,
        answer: [TEXAS], want: "/il/", hash: "#q=" + encodeURIComponent(TYPED) },
      { name: "no answer at all, to an address in Illinois, opens /il/ with the address", text: TYPED,
        answer: [], want: "/il/", hash: "#q=" + encodeURIComponent(TYPED) },
      { name: "no answer at all, to an address that names no state, is said to match nothing", text: NO_STATE,
        answer: [], want: "/", msg: /^No matches/ },
    ]) {
      const ctx = await browser.newContext({ serviceWorkers: "block" });
      const page = await ctx.newPage();
      const asked = [];
      await page.route("**/photon.komoot.io/**", (r) => {
        asked.push(new URL(r.request().url()).searchParams.get("q"));
        return photonStub(c.answer)(r);
      });
      await stubInstances(page);
      await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
      await page.fill("#search-input", c.text);
      await page.click("#search-button");
      await addressSettled(page);
      const hash = new URL(page.url()).hash;
      const msg = c.msg ? await textOrNull(page, "#search-status") : null;
      check(`a typed address held to its house number: ${c.name}`,
        JSON.stringify(asked) === JSON.stringify([c.text]) && new URL(page.url()).pathname === c.want &&
          (!c.hash || (c.hash instanceof RegExp ? c.hash.test(hash) : hash === c.hash)) && (!c.msg || c.msg.test(msg || "")),
        JSON.stringify({ asked, url: page.url(), msg }));
      await ctx.close();
    }
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
    await addressSettled(page);
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
    await addressSettled(page);
    const msg = await textOrNull(page, "#search-status");
    check("a failed search says so", /failed/i.test(msg || ""), JSON.stringify(msg));
    // The button must come back, or one flaky lookup bricks the box for the
    // rest of the visit.
    const disabled = await page.evaluate(
      () => document.getElementById("search-button")?.disabled).catch(() => null);
    check("a failed search re-enables the button", disabled === false, String(disabled));
    await ctx.close();
  }

  // --- 1f. the coverage map loads, draws, and names every place ----------
  //
  // The map is a separate generated page embedded in an iframe, so the landing
  // page's own checks say nothing about it. It carries no legend since
  // 2026-10-13 (the landing page's state list is the accessible statement of
  // the same fact), so what is asserted here is what the map itself says: a
  // tooltip per place assembled at runtime, a short label per place, and a
  // link per place.
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
    const resp = await page.goto(BASE + "/coverage-map.html", { waitUntil: "load" });
    check("coverage map loads", resp.status() === 200, `HTTP ${resp.status()}`);
    await page.waitForTimeout(1500);
    check("coverage map has no console errors", errs.length === 0, errs.slice(0, 2).join(" | "));
    check("coverage map rendered a Leaflet map",
      await page.evaluate(() => !!document.querySelector(".leaflet-container")),
      vendored ? "vendored Leaflet" : "CDN Leaflet");
    const tips = await page.evaluate(() => {
      const out = [], seen = new Set();
      window.map.eachLayer((l) => {
        const t = l.getTooltip && l.getTooltip();
        if (!t || seen.has(t)) return;
        seen.add(t);
        const c = t.getContent();
        out.push({ name: c.querySelector(".nm")?.textContent, scope: c.querySelector(".mt")?.textContent });
      });
      return out;
    });
    check("coverage map has a tooltip for every fleet place",
      tips.length === FLEET.length && FLEET.every((m) => tips.some((t) => t.name === m.landing_name)),
      JSON.stringify(tips.map((t) => t.name)) + " vs metros.json " + FLEET.length);
    // The scope is the one tooltip field ASSEMBLED AT RUNTIME: a two-tier area
    // gets a "statewide, " prefix the generated file does not contain, so a
    // wrong scope here appears in no diff. New York's scope became
    // "statewide, 5 boroughs in depth" on 2026-09-23 and read
    // "statewide, statewide, 5 boroughs in depth" until the generator learned
    // not to prefix a scope that already says it. Both halves are asserted:
    // every tooltip still ends with its own metros.json scope (the prefix may
    // not eat or reword it), and none says statewide twice.
    check("coverage map tooltips state each place's own scope",
      tips.every((t) => {
        const m = FLEET.find((f) => f.landing_name === t.name);
        return m && typeof t.scope === "string" && t.scope.endsWith(m.scope);
      }),
      JSON.stringify(tips.map((t) => t.scope)));
    check("no tooltip scope repeats statewide",
      tips.every((t) => (String(t.scope).toLowerCase().match(/statewide/g) || []).length <= 1),
      JSON.stringify(tips.map((t) => t.scope)));
    const linkTargets = await page.evaluate(() =>
      window.AREAS.map((a) => a.url).concat(window.CITIES.map((c) => c.url)));
    check("coverage map opens every fleet url",
      FLEET.every((m) => linkTargets.includes(m.url)) && linkTargets.length === FLEET.length,
      JSON.stringify(linkTargets));
    // One label per place, and at the fleet's own zoom most of them must be
    // showing: a label hidden everywhere is the failure the fits-on-screen
    // test could introduce without any error.
    const labels = await page.$$eval(".tag-label", (els) =>
      els.map((e) => ({ text: e.textContent, shown: !e.classList.contains("hidden") })));
    check("coverage map labels every place once", labels.length === FLEET.length,
      JSON.stringify(labels.map((l) => l.text)));
    check("coverage map shows the labels that fit",
      labels.filter((l) => l.shown).length * 2 >= labels.length,
      JSON.stringify(labels));
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

  // --- 1h. on a phone the state list starts folded, and one tap opens it ---
  //
  // Adam, 2026-10-13: fifty-one rows under a small map are a long scroll to
  // the questions below. The list SHIPS open and a script folds it, so a
  // broken script leaves a phone with the whole list rather than a toggle
  // that does nothing, and that is what this would catch first: a list still
  // open at 390px.
  {
    const ctx = await browser.newContext({ serviceWorkers: "block", viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    // checkVisibility, not offsetParent: Chromium hides a closed <details>
    // body with content-visibility rather than display, so offsetParent
    // stays set on rows nobody can see and a folded list counts as 51.
    const shown = () => page.evaluate(() =>
      [...document.querySelectorAll(".states li")].filter((li) => li.checkVisibility()).length);
    const folded = await page.evaluate(() => {
      const box = document.querySelector(".states-box");
      const t = document.querySelector(".states-toggle");
      const r = t ? t.getBoundingClientRect() : null;
      return { open: !!(box && box.open), toggle: t ? getComputedStyle(t).display : null,
               label: t ? t.textContent.trim() : null, h: r ? Math.round(r.height) : 0 };
    });
    check("on a phone the state list starts folded",
      !folded.open && folded.toggle !== "none" && (await shown()) === 0, JSON.stringify(folded));
    check("the fold's toggle says what it holds and is a full-size target",
      folded.label === "All 50 states and DC" && folded.h >= 44, JSON.stringify(folded));
    await page.click(".states-toggle");
    check("one tap on the toggle opens all 51 rows", (await shown()) === 51, `${await shown()} row(s) shown`);
    // Turning a phone or widening a window past the fold's width must not
    // leave the list shut with its toggle hidden — that would be a list
    // nobody can open.
    await page.click(".states-toggle");
    await page.setViewportSize({ width: 1024, height: 844 });
    await page.waitForTimeout(100);
    check("widening a folded page opens the list again", (await shown()) === 51, `${await shown()} row(s) shown`);
    await ctx.close();
  }

  // --- 1h-bis. the question tiles fold, and one tap opens one --------------
  //
  // The questions are tiles that open to their places (2026-10-21), and they
  // follow the state list's rule: they SHIP open and a script folds them, so a
  // page whose script failed shows every link rather than tiles that hide
  // them. The shipped half is read off the page as served, before any script
  // runs; the folded half in the browser, on every width, since unlike the
  // state list the tiles fold on a computer too.
  {
    const raw = await (await fetch(BASE + "/")).text();
    const tags = raw.match(/<details class="ask"[^>]*>/g) || [];
    check("every question tile ships open, for a page with no script",
      tags.length > 3 && tags.every((t) => /\sopen>$/.test(t)), `${tags.length} tile(s)`);
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    const shownChips = () => page.evaluate(() =>
      [...document.querySelectorAll(".ask-chips a")].filter((a) => a.checkVisibility()).length);
    const open = await page.evaluate(() =>
      [...document.querySelectorAll("details.ask")].map((d) => d.open));
    check("the question tiles start folded, with no place showing",
      open.length === tags.length && open.every((o) => !o) && (await shownChips()) === 0,
      JSON.stringify(open) + `, ${await shownChips()} place(s) showing`);
    const inFirst = await page.evaluate(() =>
      document.querySelector("details.ask").querySelectorAll(".ask-chips a").length);
    await page.click("details.ask > summary");
    check("one tap opens that tile's places and no other's",
      inFirst > 0 && (await shownChips()) === inFirst, `${await shownChips()} showing, ${inFirst} in the tile`);
    await ctx.close();
  }

  // --- 1i. the worked example: one place, and who represents it there ------
  //
  // Beside the address box since 2026-10-21: a place, the offices that answer
  // there and the people who hold them. The districts are measured by the
  // generator from the boundary files the map draws (render_example) and held
  // there by build_landing_page.py --check; the names are read by the page's
  // own script, when it opens, from the rosters the map's cards read
  // (EXAMPLE_SCRIPT), so they are held HERE: each card names what its roster
  // says for its seat, by the rule the officeholder tables print by. Also
  // held: the example beside the box on a computer and after it on a phone,
  // each card in its layer's map colour in both themes, links that open an app
  // at a point with layers on and keep that point when followed, the
  // independence sentence still on a phone's first screen (which is why the
  // try-it line comes after it), the bodies and districts with no name lines
  // when there is no script, and a roster that fails to load saying so on its
  // own card only.
  const exampleNamed = () => {
    const lines = [...document.querySelectorAll(".ex-card .ex-name")];
    return lines.length > 0 && lines.every((l) => !l.hidden && l.textContent.trim());
  };
  // The page's rule, restated so the page is held to it: a name, or "Vacant",
  // or "Not listed", and not named at all where the roster's number and
  // letter for the seat differ from the district the card shows.
  const rosterSays = (roster, seat, pill) => {
    const rec = roster && typeof roster === "object" ? roster[seat] : null;
    if (!rec || typeof rec !== "object") return "Not listed";
    if (rec.subDistrict && pill !== "District " + rec.subDistrict) return "Not listed";
    const n = typeof rec.name === "string" ? rec.name.trim() : "";
    if (n && n.toUpperCase() !== "VACANT") return n;
    return rec.vacant || n ? "Vacant" : "Not listed";
  };
  {
    const examples = {};
    for (const [label, opts] of [
      ["computer", { viewport: { width: 1280, height: 800 }, colorScheme: "light" }],
      // iPhone 13's viewport, so "first screen" means a real phone's.
      ["phone", { viewport: { width: 390, height: 664 }, colorScheme: "light" }],
      ["dark", { viewport: { width: 1280, height: 800 }, colorScheme: "dark" }],
    ]) {
      const ctx = await browser.newContext({ ...opts, serviceWorkers: "block" });
      const page = await ctx.newPage();
      await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
      await page.evaluate(() => document.fonts.ready);
      await page.waitForFunction(exampleNamed, null, { timeout: 10000 }).catch(() => {});
      examples[label] = await page.evaluate(() => {
        const aside = document.querySelector(".example");
        const search = document.querySelector(".search-card");
        const a = aside && aside.getBoundingClientRect();
        const s = search && search.getBoundingClientRect();
        return {
          shown: !!aside && aside.checkVisibility(),
          beside: !!(a && s && a.left >= s.right && a.top < s.bottom),
          after: !!(a && s && a.top >= s.bottom && a.left < s.right),
          sideways: document.documentElement.scrollWidth > innerWidth,
          indep: (() => {
            const p = document.querySelector(".independence");
            if (!p) return null;
            return { top: Math.round(p.getBoundingClientRect().top),
                     line: parseFloat(getComputedStyle(p).lineHeight), screen: innerHeight };
          })(),
          cards: [...document.querySelectorAll(".ex-card")].map((li) => ({
            body: (li.querySelector(".ex-body")?.textContent || "").trim(),
            name: (li.querySelector(".ex-name")?.textContent || "").trim(),
            pill: (li.querySelector(".ex-pill")?.textContent || "").trim(),
            roster: li.getAttribute("data-roster"),
            seat: li.getAttribute("data-seat"),
            lc: getComputedStyle(li).getPropertyValue("--lc").trim().toUpperCase(),
            light: li.style.getPropertyValue("--lc-l").trim().toUpperCase(),
            dark: li.style.getPropertyValue("--lc-d").trim().toUpperCase(),
          })),
          links: [...document.querySelectorAll(".example a, .try a")].map((l) => l.href),
        };
      });
      await ctx.close();
    }
    const { computer, phone, dark } = examples;
    check("the worked example is on the page, with a name and a district on every card",
      computer.shown && computer.cards.length >= 3 &&
        computer.cards.every((c) => c.body && c.name && c.pill),
      JSON.stringify(computer.cards.map((c) => [c.body, c.name, c.pill])));
    // Each name against the roster file the page fetched, read here from the
    // tree the server serves. A roster the map's own app does not read is
    // build_landing_page.py's to refuse.
    const rosterSaid = computer.cards.map((c) => {
      try {
        return rosterSays(JSON.parse(readFileSync(join(HERE, "..", c.roster), "utf8")), c.seat, c.pill);
      } catch (e) {
        return `(${c.roster}: ${e.message})`;
      }
    });
    check("each example card names what its roster says for its seat",
      computer.cards.length > 0 && computer.cards.every((c, i) => c.name === rosterSaid[i]),
      JSON.stringify(computer.cards.map((c, i) => [c.roster, c.seat, c.name, rosterSaid[i]])));
    check("on a computer the example sits beside the address box", computer.beside, JSON.stringify(computer));
    check("on a phone the example comes after the address box, with no sideways scroll",
      phone.shown && phone.after && !phone.sideways, JSON.stringify({ ...phone, cards: phone.cards.length }));
    // INDEPENDENCE in build_landing_page.py says why that sentence is above
    // the fold. Put under the box, the try-it line pushed it to the last line
    // of this screen, so two lines of it must show.
    check("on a phone the independence sentence starts on the first screen, at least two lines of it",
      !!phone.indep && phone.indep.top + 2 * phone.indep.line <= phone.indep.screen,
      JSON.stringify(phone.indep));
    check("each example card takes its layer's map colour, light and dark",
      computer.cards.every((c) => /^#[0-9A-F]{6}$/.test(c.light) && c.lc === c.light) &&
        dark.cards.every((c) => /^#[0-9A-F]{6}$/.test(c.dark) && c.lc === c.dark),
      JSON.stringify([computer.cards.map((c) => c.lc), dark.cards.map((c) => c.lc)]));
    // A link opens an app with its point and its layers in the short form the
    // apps write: #p=lat,lng and &l= with the layers' permanent codes.
    const apps = FLEET.map((m) => m.url);
    check("every example link opens an app at a point with layers on",
      computer.links.length >= 3 && computer.links.every((h) =>
        apps.some((u) => h.startsWith(u + "#")) &&
        /#p=-?\d+(\.\d+)?,-?\d+(\.\d+)?&l=[a-z][a-z0-9]*(,[a-z][a-z0-9]*)*$/.test(h)),
      JSON.stringify(computer.links));

    // With no script: the bodies and districts and the link to the map, and
    // no name line, empty or otherwise.
    {
      const ctx = await browser.newContext({ javaScriptEnabled: false, serviceWorkers: "block" });
      const page = await ctx.newPage();
      await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
      const bare = await page.evaluate(() => ({
        cards: [...document.querySelectorAll(".ex-card")].map((li) => ({
          body: (li.querySelector(".ex-body")?.textContent || "").trim(),
          pill: (li.querySelector(".ex-pill")?.textContent || "").trim(),
          name: li.querySelector(".ex-name")?.checkVisibility() ?? false,
        })),
        link: !!document.querySelector(".example a.ex-open")?.checkVisibility(),
      }));
      await ctx.close();
      check("with no script the example shows its bodies, districts and map link, and no name lines",
        bare.link && bare.cards.length === computer.cards.length &&
          bare.cards.every((c) => c.body && c.pill && !c.name),
        JSON.stringify(bare));
    }
    // A roster that fails to load says so on its own card, and the others
    // still name their seats.
    {
      const failing = computer.cards[0]?.roster;
      const ctx = await browser.newContext({ serviceWorkers: "block" });
      const page = await ctx.newPage();
      if (failing) {
        await page.route((u) => u.pathname === "/" + failing,
          (r) => r.fulfill({ status: 404, contentType: "text/plain", body: "not found" }));
      }
      await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
      await page.waitForFunction(exampleNamed, null, { timeout: 10000 }).catch(() => {});
      const got = await page.evaluate(() => [...document.querySelectorAll(".ex-card")].map((li) => [
        li.getAttribute("data-roster"), (li.querySelector(".ex-name")?.textContent || "").trim()]));
      await ctx.close();
      check("a roster that fails to load says so on its own card only",
        !!failing && got.length === computer.cards.length &&
          got.every(([roster, name], i) => roster === failing ? name === "Name didn't load"
                                                              : name === computer.cards[i].name),
        JSON.stringify(got));
    }

    // Followed, a link keeps its point: the instance is stubbed, so a wrong
    // route shows as a wrong URL rather than as a failed navigation that
    // leaves the page on / and reads like a right one.
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    await stubInstances(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    const want = await page.getAttribute(".try a", "href");
    await page.click(".try a");
    await page.waitForURL((u) => u.pathname !== "/", { timeout: 10000, waitUntil: "commit" }).catch(() => {});
    check("following a try-it link opens that app with its point and layers",
      page.url() === want, `${page.url()} vs ${want}`);
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
    // 500 ms settle below still gives late ones time to arrive.
    //
    // CORRECTED 2026-09-15: this used to end "the landing page is the only root
    // page carrying that tag, so privacy.html and coverage-map.html deliberately
    // keep `load`". privacy.html carries it now — 191 pages gained the counter
    // that day — and its check failed on the sandbox's cert interception within
    // the hour. coverage-map.html still keeps `load`: it is the one root page
    // deliberately uncounted, recorded in validate_analytics.NO_COUNTER.
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
    // The same filter and the same `domcontentloaded` as the landing page's own
    // check above, for the same reason and as of 2026-09-15: this page carries
    // the fleet's GoatCounter tag now. gc.zgo.at is a third-party host that is
    // unroutable from the sandbox and can hang in CI, and a failed request to it
    // says nothing about whether the page boots. An app JS error still surfaces
    // through pageerror and any non-network console error.
    page.on("console", (m) => {
      if (m.type() !== "error") return;
      const t = m.text();
      if (/Failed to load resource|net::ERR|gc\.zgo\.at|googletagmanager/i.test(t)) return;
      errs.push(t);
    });
    page.on("pageerror", (e) => errs.push(String(e)));
    const resp = await page.goto(BASE + "/privacy.html", { waitUntil: "domcontentloaded" });
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
      // The same pages carry the ONE install manifest, at the root. A page
      // still pointing at a per-state copy would install a second districtry
      // beside the first; build_manifests.py --check reads the markup, and
      // this reads where the browser actually resolves it.
      const manifestHref = await page.evaluate(() => {
        const l = document.querySelector('link[rel="manifest"]');
        return l ? l.href : null;
      });
      check(`${where} links the one root manifest`,
        manifestHref === new URL("/manifest.webmanifest", BASE).href, String(manifestHref));
    }
    await ctx.close();
  }

  // --- 9. the installed app opens the state the reader used last ------------
  //
  // The manifest's start_url is the launcher at /app/, which reads the tag
  // every app writes under districtry-last-app and goes there. Nothing else
  // ever opens /app/ — only an installed copy does — so a launcher sending
  // readers to the wrong place would be found on a reader's phone and nowhere
  // else. Every instance page is STUBBED, as in 1c, so what is measured is
  // where the launcher goes, and a wrong destination shows as a wrong URL
  // rather than as an app that failed to boot. A stored value that is not a
  // plain two-letter tag must open the front page, never a path built from it.
  {
    const ctx = await browser.newContext({ serviceWorkers: "block" });
    const page = await ctx.newPage();
    const manifest = await page.request.get(BASE + "/manifest.webmanifest")
      .then((r) => r.json()).catch(() => null);
    check("the root manifest is one app, opened at the launcher",
      !!manifest && manifest.id === "/" && manifest.scope === "/" &&
        manifest.start_url === "/app/" && manifest.display === "standalone" &&
        manifest.name === "districtry",
      JSON.stringify(manifest && { id: manifest.id, name: manifest.name, scope: manifest.scope,
        start_url: manifest.start_url, display: manifest.display }));
    // The address is the launcher's FULL one: the Google Play app copies it as
    // written, and Chrome drops a share whose address names no site.
    const st = manifest && manifest.share_target;
    check("the manifest puts the app in the Share menu, sending title, text and url to the launcher's full address by GET",
      !!st && st.action === `https://${SITE_HOST}/app/` && st.method === "GET" && !st.enctype &&
        JSON.stringify(st.params) === JSON.stringify({ title: "title", text: "text", url: "url" }),
      JSON.stringify(st));
    await ctx.close();

    const cases = [
      { stored: TAGS.includes("wi") ? "wi" : TAGS[0], want: null },
      { stored: null, want: "/" },
      { stored: "../privacy.html", want: "/" },
    ];
    for (const c of cases) {
      const want = c.want || `/${c.stored}/`;
      const ctx2 = await browser.newContext({ serviceWorkers: "block" });
      await ctx2.addInitScript((stored) => {
        if (location.pathname !== "/app/") return;
        try {
          if (stored === null) localStorage.removeItem("districtry-last-app");
          else localStorage.setItem("districtry-last-app", stored);
        } catch (e) { /* private mode */ }
      }, c.stored);
      const p = await ctx2.newPage();
      await stubInstances(p);
      await p.route((url) => url.pathname === "/", (r) => r.fulfill({
        status: 200, contentType: "text/html", body: "<!doctype html><title>front door stub</title>",
      }));
      await p.goto(BASE + "/app/", { waitUntil: "commit" });
      await p.waitForURL((u) => u.pathname !== "/app/", { timeout: 5000, waitUntil: "commit" }).catch(() => {});
      const at = new URL(p.url()).pathname;
      check(`the launcher with ${c.stored === null ? "nothing" : JSON.stringify(c.stored)} stored opens ${want}`,
        at === want, p.url());
      await ctx2.close();
    }

    // OFFLINE, which is why the launcher has a worker of its own. The first
    // launch installs it; a later launch with no connection must still get the
    // launcher page, from that worker, or an installed districtry opens to the
    // browser's offline error before it can reach a state whose own worker
    // would have answered. Service workers are ALLOWED here and nowhere else
    // in this file.
    {
      const ctx3 = await browser.newContext({ serviceWorkers: "allow" });
      await ctx3.addInitScript(() => {
        if (location.pathname !== "/app/") return;
        try { localStorage.setItem("districtry-last-app", "il"); } catch (e) { /* private mode */ }
      });
      const p = await ctx3.newPage();
      await stubInstances(p);
      await p.goto(BASE + "/app/", { waitUntil: "commit" });
      await p.waitForURL((u) => u.pathname === "/il/", { timeout: 5000, waitUntil: "commit" }).catch(() => {});
      let stored = null;
      for (let i = 0; i < 20 && !(stored && stored.hit); i++) {
        stored = await p.evaluate(async () => {
          const keys = (await caches.keys()).filter((k) => k.indexOf("districtry-app-launch-v") === 0);
          const hit = keys.length === 1 && !!(await caches.match("/app/", { cacheName: keys[0] }));
          return { keys, hit };
        }).catch((e) => ({ error: String(e) }));
        if (!(stored && stored.hit)) await p.waitForTimeout(250);
      }
      check("the first launch stores the launcher in its own cache, and only there",
        !!stored && stored.hit === true, JSON.stringify(stored));
      await ctx3.setOffline(true);
      const resp = await p.goto(BASE + "/app/", { waitUntil: "commit" }).catch(() => null);
      check("offline, the launcher is served by its own worker",
        !!resp && resp.status() === 200 && resp.fromServiceWorker(),
        resp ? `HTTP ${resp.status()} fromServiceWorker=${resp.fromServiceWorker()}` : "no response");
      await ctx3.close();
    }
  }

  // --- 9b. a place shared into the installed app ----------------------------
  //
  // The manifest's share_target sends Android's Share menu to the launcher as
  // /app/?title=…&text=…&url=…. The launcher must hand what was shared to the
  // state used last as #q= (the hash, which never leaves the browser), or to
  // the front page when none is remembered, which searches it like a pasted
  // link; it must take the share out of its own address first, because that
  // address is the next page's referrer and the counter there reports one;
  // and its worker must answer a share from its copy and refresh that copy
  // WITHOUT the share, or every share would reach the host. Android puts the
  // link in `text`, often after the place's name and address, which is the
  // shape used here; `url` alone stands in for a browser that fills it.
  {
    const MAPLINK = "https://www.google.com/maps/place/Lambeau+Field/@44.50,-88.06,12z/data=!3m1!4b1!8m2!3d44.5013!4d-88.0622";
    const SHORT = "https://maps.app.goo.gl/AbCdEf123";
    const wi = TAGS.includes("wi") ? "wi" : TAGS[0];
    const launch = async ({ stored, query, referrer, workers }) => {
      const ctx = await browser.newContext({ serviceWorkers: workers || "block" });
      await ctx.addInitScript(({ s, r }) => {
        if (location.pathname !== "/app/") return;
        try {
          if (s === null) localStorage.removeItem("districtry-last-app");
          else localStorage.setItem("districtry-last-app", s);
        } catch (e) { /* private mode */ }
        if (r) Object.defineProperty(Document.prototype, "referrer", { get: () => r, configurable: true });
      }, { s: stored, r: referrer || null });
      const p = await ctx.newPage();
      return { ctx, p };
    };
    const landed = (p) => p.evaluate(() => ({
      path: location.pathname, search: location.search, hash: location.hash,
      referrer: document.referrer,
      mark: (function () { try { return sessionStorage.getItem("districtry-share-in"); } catch (e) { return "blocked"; } })(),
    }));
    const handed = (h) => { const m = /^#q=(.*)$/.exec(h || ""); return m ? decodeURIComponent(m[1]) : null; };

    for (const c of [
      { name: "a link Android puts in text, after the place's name and address",
        query: "?title=" + encodeURIComponent("Lambeau Field") + "&text=" +
          encodeURIComponent("Lambeau Field\n1265 Lombardi Ave, Green Bay, WI 54304\n" + SHORT),
        want: "Lambeau Field 1265 Lombardi Ave, Green Bay, WI 54304 " + SHORT },
      { name: "a link sent as url alone", query: "?url=" + encodeURIComponent(SHORT), want: SHORT },
    ]) {
      const { ctx, p } = await launch({ stored: wi });
      await stubInstances(p);
      await p.goto(BASE + "/app/" + c.query, { waitUntil: "commit" });
      await p.waitForURL((u) => u.pathname !== "/app/", { timeout: 5000, waitUntil: "commit" }).catch(() => {});
      await p.waitForLoadState("domcontentloaded").catch(() => {});
      const at = await landed(p).catch((e) => ({ error: String(e) }));
      check(`${c.name} opens /${wi}/ with the place in #q= and nothing in the query`,
        at.path === `/${wi}/` && at.search === "" && handed(at.hash) === c.want, JSON.stringify(at));
      check(`${c.name}: the page it opens is sent the launcher's address with the share taken out`,
        at.referrer === BASE + "/app/", JSON.stringify(at.referrer));
      check(`${c.name}: the map it opens finds the mark that counts a share`, at.mark === "1", JSON.stringify(at.mark));
      await ctx.close();
    }
    {
      const { ctx, p } = await launch({ stored: wi });
      await stubInstances(p);
      await p.goto(BASE + "/app/", { waitUntil: "commit" });
      await p.waitForURL((u) => u.pathname !== "/app/", { timeout: 5000, waitUntil: "commit" }).catch(() => {});
      await p.waitForLoadState("domcontentloaded").catch(() => {});
      const at = await landed(p).catch((e) => ({ error: String(e) }));
      check("an ordinary launch hands on no place and leaves no share mark",
        at.path === `/${wi}/` && at.hash === "" && at.mark === null, JSON.stringify(at));
      await ctx.close();
    }
    // A share into the Google Play app arrives with the app as the launcher's
    // referrer and no ref=play: the launcher's Play-app block marks the
    // window and the launcher passes ref=play on beside the place.
    {
      const { ctx, p } = await launch({ stored: wi, referrer: "android-app://com.districtry.app/" });
      await stubInstances(p);
      await p.goto(BASE + "/app/?text=" + encodeURIComponent(SHORT), { waitUntil: "commit" });
      await p.waitForURL((u) => u.pathname !== "/app/", { timeout: 5000, waitUntil: "commit" }).catch(() => {});
      await p.waitForLoadState("domcontentloaded").catch(() => {});
      const at = await landed(p).catch((e) => ({ error: String(e) }));
      const play = await p.evaluate(() => sessionStorage.getItem("districtry-play-app")).catch(() => null);
      check("a share into the Google Play app keeps ref=play and the window's Play mark",
        at.path === `/${wi}/` && at.search === "?ref=play" && handed(at.hash) === SHORT && play === "1",
        JSON.stringify({ at, play }));
      await ctx.close();
    }
    // No state remembered: the front page receives #q= and routes the place
    // as if the link had been pasted into its box. Its own address loses the
    // place before it searches, and the geocoder is never asked for a link.
    {
      const { ctx, p } = await launch({ stored: null });
      let photonAsked = false;
      await p.route("**/photon.komoot.io/**", (r) => { photonAsked = true; return photonStub([])(r); });
      await stubInstances(p);
      await p.goto(BASE + "/app/?text=" + encodeURIComponent("Lambeau Field " + MAPLINK), { waitUntil: "commit" });
      await p.waitForURL((u) => u.pathname === `/${wi}/`, { timeout: 10000, waitUntil: "commit" }).catch(() => {});
      check(`with no state remembered, a shared Google Maps link goes through the front page to /${wi}/`,
        new URL(p.url()).pathname === `/${wi}/` && /^#point=44\.5013\d*,-88\.0622/.test(new URL(p.url()).hash),
        p.url());
      check("a shared map link is never sent to the geocoder", !photonAsked, String(photonAsked));
      await ctx.close();
    }
    {
      const ctx = await browser.newContext({ serviceWorkers: "block" });
      const p = await ctx.newPage();
      await p.route("**/photon.komoot.io/**", photonStub([photonFeature(44.5013, -88.0622)]));
      await stubInstances(p);
      await p.goto(BASE + "/#q=" + encodeURIComponent("1265 Lombardi Ave, Green Bay, WI"), { waitUntil: "domcontentloaded" });
      const mid = await p.evaluate(() => location.hash).catch(() => "(left)");
      await addressSettled(p);
      check(`the front page searches an address handed over in #q= and opens /${wi}/`,
        new URL(p.url()).pathname === `/${wi}/`, p.url());
      check("the front page takes #q= out of its own address before it searches",
        mid === "" || mid === "(left)", JSON.stringify(mid));
      await ctx.close();
    }
    // THE WORKER. The first launch installs it; a share after that must be
    // answered from its copy, and the copy refreshed by a request for /app/
    // with no query. The worker's own requests are visible only behind
    // PW_EXPERIMENTAL_SERVICE_WORKER_NETWORK_EVENTS (set at the top of this
    // file), so the check refuses to pass unless it saw the refresh at all.
    {
      const { ctx, p } = await launch({ stored: "il", workers: "allow" });
      await stubInstances(p);
      await p.goto(BASE + "/app/", { waitUntil: "commit" });
      await p.waitForURL((u) => u.pathname === "/il/", { timeout: 5000, waitUntil: "commit" }).catch(() => {});
      let ready = false;
      for (let i = 0; i < 20 && !ready; i++) {
        ready = await p.evaluate(async () => {
          const keys = (await caches.keys()).filter((k) => k.indexOf("districtry-app-launch-v") === 0);
          return keys.length === 1 && !!(await caches.match("/app/", { cacheName: keys[0] }));
        }).catch(() => false);
        if (!ready) await p.waitForTimeout(250);
      }
      const byWorker = [];
      ctx.on("request", (r) => { if (r.serviceWorker()) byWorker.push(r.url()); });
      const resp = await p.goto(BASE + "/app/?text=" + encodeURIComponent("Lambeau Field " + SHORT), { waitUntil: "commit" }).catch(() => null);
      const fromWorker = !!resp && resp.fromServiceWorker();
      await p.waitForURL((u) => u.pathname === "/il/", { timeout: 5000, waitUntil: "commit" }).catch(() => {});
      await p.waitForTimeout(500);
      const refresh = byWorker.filter((u) => new URL(u).pathname === "/app/");
      const leaked = byWorker.filter((u) => /[?&](?:title|text|url)=/.test(u));
      check("with its worker installed, a share is answered from the launcher's copy",
        ready && fromWorker && handed(new URL(p.url()).hash) === "Lambeau Field " + SHORT,
        JSON.stringify({ ready, fromWorker, url: p.url() }));
      check("the worker refreshes its copy without the share, so the host never sees it",
        refresh.length > 0 && leaked.length === 0, JSON.stringify({ refresh, leaked }));
      await ctx.close();
    }
  }

  // --- 10. inside the Google Play app the support links are hidden ----------
  //
  // The Play app is this site in a full-screen Chrome window, and Google Play
  // does not allow an app to send readers to an outside payment page, so
  // engine/shared/play-app.txt hides the GitHub Sponsors and sponsorship links
  // in a window the app opened, and nowhere else. The app opens
  // /app/?ref=play: the launcher must pass that one tag on, the page it lands
  // on must mark the window, and the next page must read the mark with no tag
  // in its address. Every half is asserted both ways, because a rule that
  // hid the links everywhere would pass a hiding test on its own. The
  // referrer path stands in for a shared link opened straight into the app,
  // with a link from Gmail as the control.
  {
    const supportShown = (p) => p.evaluate(() => {
      const visible = (el) => !!el && el.getClientRects().length > 0;
      const all = (sel) => Array.prototype.slice.call(document.querySelectorAll(sel));
      return {
        marked: document.documentElement.classList.contains("dst-play-app"),
        sponsors: all('a[href*="github.com/sponsors"]').map(visible),
        policy: all('a[href*="sponsorship.html"]').map(visible),
      };
    });
    const hidden = (s) => s.marked && s.sponsors.length > 0 && s.sponsors.every((v) => !v) &&
      s.policy.every((v) => !v);
    const kept = (s) => !s.marked && s.sponsors.length > 0 && s.sponsors.every((v) => v) &&
      s.policy.length > 0 && s.policy.every((v) => v);

    for (const stored of [TAGS.includes("wi") ? "wi" : TAGS[0], null]) {
      const want = stored ? `/${stored}/` : "/";
      const ctx = await browser.newContext({ serviceWorkers: "block" });
      await ctx.addInitScript((s) => {
        if (location.pathname !== "/app/") return;
        try {
          if (s === null) localStorage.removeItem("districtry-last-app");
          else localStorage.setItem("districtry-last-app", s);
        } catch (e) { /* private mode */ }
      }, stored);
      const p = await ctx.newPage();
      await stubInstances(p);
      await p.route((url) => url.pathname === "/", (r) => r.fulfill({
        status: 200, contentType: "text/html", body: "<!doctype html><title>front door stub</title>",
      }));
      await p.goto(BASE + "/app/?ref=play", { waitUntil: "commit" });
      await p.waitForURL((u) => u.pathname !== "/app/", { timeout: 5000, waitUntil: "commit" }).catch(() => {});
      const u = new URL(p.url());
      check(`a launch from Google Play opens ${want} carrying ref=play and nothing else`,
        u.pathname === want && u.search === "?ref=play", p.url());
      await ctx.close();
    }
    {
      const ctx = await browser.newContext({ serviceWorkers: "block" });
      const p = await ctx.newPage();
      await p.route("**/gc.zgo.at/**", (r) => r.abort());
      await p.goto(BASE + "/?ref=play", { waitUntil: "domcontentloaded" });
      const inApp = await supportShown(p);
      check("in the Play app the front page hides its sponsorship paragraph and link",
        hidden(inApp) && inApp.policy.length > 0, JSON.stringify(inApp));
      await p.goto(BASE + "/sponsorship.html", { waitUntil: "domcontentloaded" });
      const next = await supportShown(p);
      check("the mark carries to the next page in the window, with no tag in its address",
        hidden(next), JSON.stringify(next));
      await ctx.close();
    }
    {
      const ctx = await browser.newContext({ serviceWorkers: "block" });
      const p = await ctx.newPage();
      await p.route("**/gc.zgo.at/**", (r) => r.abort());
      await p.goto(BASE + "/", { waitUntil: "domcontentloaded" });
      const web = await supportShown(p);
      check("on the website the front page keeps its sponsorship paragraph and link",
        kept(web), JSON.stringify(web));
      await ctx.close();
    }
    for (const [referrer, inside] of [["android-app://com.districtry.app/", true],
                                       ["android-app://com.google.android.gm/", false]]) {
      const ctx = await browser.newContext({ serviceWorkers: "block" });
      await ctx.addInitScript((r) => {
        Object.defineProperty(Document.prototype, "referrer", { get: () => r, configurable: true });
      }, referrer);
      const p = await ctx.newPage();
      await p.route("**/gc.zgo.at/**", (r) => r.abort());
      await p.goto(BASE + "/", { waitUntil: "domcontentloaded" });
      const s = await supportShown(p);
      check(`a page opened from ${referrer} ${inside ? "hides" : "keeps"} the sponsorship links`,
        inside ? hidden(s) : kept(s), JSON.stringify(s));
      await ctx.close();
    }
  }
} finally {
  await browser.close();
}

if (failures.length) {
  console.error(`\n${failures.length} root-page check(s) failed: ${failures.join(", ")}`);
  process.exit(1);
}
console.log("\nAll root-page checks passed.");
