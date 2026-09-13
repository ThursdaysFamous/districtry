#!/usr/bin/env node
// Renders the shared districtry OG card ("districtry/OG Card.dc.html") for one
// surface — an instance, or the fleet root.
//
// Usage:
//   node scripts/build_og_image.mjs <tag>    # one instance: il, wi, ia, …
//   node scripts/build_og_image.mjs root     # the fleet front door
//   node scripts/build_og_image.mjs --all    # every surface, then the manifest
//   node scripts/build_og_image.mjs --check  # stdlib-free drift gate, no browser
//
// WHY THIS EXISTS. districtry/OG Card.dc.html is the real design source —
// SVG shapes, exact colors, Barlow/Barlow Condensed type — but it hardcodes
// "illinois" as the label and there was no renderer, so every instance after
// Illinois either reused that PNG verbatim (Wisconsin: its live og-image.png
// says "illinois") or hand-approximated a new one in a raster library
// (Iowa's first pass, drawn with system fonts, not the real brand type).
// This is the renderer: same layout and assets as the .dc.html card, minus
// its Claude-Design-canvas scaffolding (<x-dc>, support.js), with Google Fonts
// swapped for the surface's own self-hosted woff2 files so it needs no network
// access — the same reason every other page in this fleet self-hosts its fonts.
//
// WHAT 2026-09-13 FOUND, and it is the reason the label is no longer an
// argument. Adam shared an /il/ permalink into a Signal group and the link
// preview showed "CHICAGO DISTRICT EXPLORER … chidistricts.com" — the
// pre-rebrand card, under a correct districtry title and description. Measured
// across all seven surfaces, FOUR were wrong:
//
//   /            districtry / ILLINOIS   the fleet front door labelled as one state
//   il/          CHICAGO DISTRICT EXPLORER · chidistricts.com
//   ny/          NEW YORK CITY DISTRICT EXPLORER · nyc.chidistricts.com
//   ca/          SAN FRANCISCO DISTRICT EXPLORER · sf.chidistricts.com,
//                and carrying CHICAGO'S flag star
//
// wi, ia and mi were right, because they are the three rendered by this script.
// The other four are the surfaces that predate it, and 97 of the site's 201
// pages name one of them. Two retired subdomains and one city's flag on
// another city's card had been the fleet's social preview for as long as the
// rebrand has existed.
//
// THE LABEL IS NOW DERIVED, NEVER TYPED. It is the instance's `tag` from
// metros.json — il, ny, ca, wi, ia, mi — because a hand-typed argument is
// exactly how the root came to say "illinois": the design source said it, and
// it was copied. The root takes NO label, since the fleet is not one of its
// states.
//
// THE TAG RATHER THAN THE PLACE NAME, decided 2026-09-13 after the first pass
// rendered `landing_name`. Two reasons, and the second is the stronger one.
// The long names broke the layout: "new york city" and "san francisco" wrap to
// a second line at 82px and push the strapline down, and every future state is
// one bad name away from the same thing. And metros.json's own comment already
// says what this card is supposed to print — `tag` is "the instance tag the
// brand spec sets in the wordmark (districtry / il)" — so rendering the place
// name was the card disagreeing with the brand spec, and with the URL the
// reader is about to open. NY and CA are STATE codes on purpose even though
// those two instances serve one city each: the tag is the path, /ny/ and /ca/,
// and a card reading "new york city" over a link to /ny/ names two different
// things.
//
// Rare operator step for the rendering itself (it needs Playwright), but
// `--check` is stdlib-only and runs in CI. See the manifest note on
// buildManifest() for what that check can and cannot prove.

import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const MANIFEST = join(REPO_ROOT, "districtry", "og-images.json");

// Every surface that carries an og:image, and the label its card prints.
// DERIVED FROM metros.json, so a new instance is covered by adding it there
// and re-rendering — there is no list here to forget. The root is the one
// entry this file states, because it is not in that manifest and never will
// be: it is the fleet, not a place in it.
function surfaces() {
  const fleet = JSON.parse(
    readFileSync(join(REPO_ROOT, "metros.json"), "utf8")).metros;
  const out = [{ tag: "root", dir: ".", label: null }];
  for (const m of fleet) {
    if (!m.tag) {
      throw new Error(`metros.json entry ${JSON.stringify(m)} has no tag`);
    }
    out.push({ tag: m.tag, dir: m.tag, label: m.tag });
  }
  return out;
}

const pngPath = (s) => join(REPO_ROOT, s.dir, "og-image.png");
const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");

// Width and height out of the IHDR chunk, which is always the first chunk and
// always at a fixed offset. Enough to catch a card replaced by something that
// is not 1200x630, without a decoder.
function pngSize(buf) {
  const sig = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  if (buf.length < 24 || !buf.subarray(0, 8).equals(sig)) return null;
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}

async function render(surface) {
  const { chromium } = await import("playwright");
  const fontsDir = join(REPO_ROOT, surface.dir, "fonts");
  const fontFace = (family, weight, file) => {
    const path = join(fontsDir, file);
    if (!existsSync(path)) throw new Error(`missing font for ${surface.tag}: ${path}`);
    return `
@font-face {
  font-family: '${family}';
  font-style: normal;
  font-weight: ${weight};
  src: url('file://${path}') format('woff2');
}`;
  };

  // Layout, shapes, colors and copy match districtry/OG Card.dc.html's #og-card
  // div exactly (its <x-dc> canvas wrapper and data-dc-script are editor
  // scaffolding, not part of the rendered card, so they're dropped here). The
  // one departure: the label span is OMITTED for the root rather than rendered
  // empty, so the fleet card reads "districtry" and not "districtry /".
  const labelSpan = surface.label
    ? `<span style="font:400 82px/1 'Barlow Condensed',sans-serif;color:#9aa3b2">/ ${surface.label}</span>`
    : "";
  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
${fontFace("Barlow Condensed", 600, "barlow-condensed-600-latin.woff2")}
${fontFace("Barlow Condensed", 400, "barlow-condensed-400-latin.woff2")}
${fontFace("Barlow", 500, "barlow-500-latin.woff2")}
${fontFace("Barlow", 400, "barlow-400-latin.woff2")}
body{margin:0}
</style></head>
<body>
<div id="og-card" style="width:1200px;height:630px;background:#f4f2ee;display:flex;align-items:center;gap:70px;padding:0 90px;box-sizing:border-box;overflow:hidden;position:relative">
  <svg width="330" height="330" viewBox="0 0 96 96" style="flex:none">
    <g style="mix-blend-mode:multiply"><polygon points="51.5,63.2 12.4,55.7 11.5,18.6 42.7,5.0 72.7,35.3" fill="#6d3fd1" fill-opacity="0.55"></polygon></g>
    <g style="mix-blend-mode:multiply"><polygon points="54.1,81.9 34.6,47.9 56.5,19.3 87.5,28.1 83.8,71.0" fill="#1d5fd6" fill-opacity="0.5"></polygon></g>
    <g style="mix-blend-mode:multiply"><polygon points="13.7,64.5 27.6,31.2 62.7,37.6 70.3,66.9 33.9,89.0" fill="#b0316e" fill-opacity="0.45"></polygon></g>
    <circle cx="42" cy="60" r="17" fill="none" stroke="#17161c" stroke-width="11"></circle>
    <line x1="59" y1="16" x2="59" y2="82.5" stroke="#17161c" stroke-width="11"></line>
  </svg>
  <div style="display:flex;flex-direction:column;gap:22px;min-width:0">
    <div style="display:flex;align-items:baseline;gap:16px">
      <span style="font:600 104px/1 'Barlow Condensed',sans-serif;color:#17161c;letter-spacing:.005em">districtry</span>
      ${labelSpan}
    </div>
    <div style="font:500 40px/1.25 Barlow,sans-serif;color:#374151;text-wrap:pretty">They're your Districts. Now in one place.</div>
    <div style="font:400 24px/1 Barlow,sans-serif;color:#9aa3b2">districtry.com</div>
  </div>
</div>
</body></html>`;

  const tmpFile = join("/tmp", `og-card-${surface.tag}.html`);
  writeFileSync(tmpFile, html);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
  await page.goto("file://" + tmpFile);
  await page.evaluate(() => document.fonts.ready); // wait for @font-face, not a fixed timeout
  await page.locator("#og-card").screenshot({ path: pngPath(surface) });
  await browser.close();
  console.log(`  rendered ${surface.dir}/og-image.png (label: ${surface.label || "none — the fleet card"})`);
}

// WHAT THE MANIFEST IS FOR, AND WHAT IT CANNOT DO.
//
// validate_instance_assets.py already checks that og-image.png EXISTS, and
// every one of the four wrong cards existed. Nothing compared a card against
// what it should say — the same shape as mi/sources.html serving Iowa's
// identity block, where the gate asked whether a canonical tag was THERE and
// never what it SAID.
//
// So the renderer records what it rendered: the surface, its label, the file's
// sha256 and the date. `--check` is stdlib-only and asserts every surface has
// an entry, every entry's label still matches metros.json, every PNG's hash
// still matches, and every card is 1200x630. That catches a card never
// rendered (no entry — which is exactly what il, ny and ca would have failed
// on), a card replaced by hand, and a tag changed without a re-render.
//
// IT CANNOT READ THE PIXELS. A card whose DESIGN is wrong — the wrong star, an
// unreadable colour — passes, and only a person looking at it will catch that.
// The check proves provenance, not correctness, and says so rather than
// implying more.
function buildManifest() {
  const entries = {};
  for (const s of surfaces()) {
    const buf = readFileSync(pngPath(s));
    const size = pngSize(buf);
    entries[s.tag] = {
      path: (s.dir === "." ? "" : s.dir + "/") + "og-image.png",
      label: s.label,
      sha256: sha256(buf),
      width: size.w,
      height: size.h,
      rendered: new Date().toISOString().slice(0, 10),
    };
  }
  writeFileSync(MANIFEST, JSON.stringify(entries, null, 2) + "\n");
  console.log(`build-og-image: wrote ${Object.keys(entries).length} manifest entries`);
}

function check() {
  const problems = [];
  if (!existsSync(MANIFEST)) {
    console.error("build-og-image --check: FAIL — districtry/og-images.json is "
      + "missing. Run `node scripts/build_og_image.mjs --all`.");
    process.exit(1);
  }
  const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
  const want = surfaces();
  for (const s of want) {
    const e = manifest[s.tag];
    if (!e) {
      problems.push(`${s.tag}: no manifest entry — its card has never been `
        + `rendered by scripts/build_og_image.mjs. Run `
        + `\`node scripts/build_og_image.mjs ${s.tag}\`, then --all to refresh `
        + `the manifest.`);
      continue;
    }
    if ((e.label ?? null) !== s.label) {
      problems.push(`${s.tag}: its card was rendered with the label `
        + `${JSON.stringify(e.label)} and metros.json's tag is now `
        + `${JSON.stringify(s.label)} — re-render it.`);
    }
    const file = pngPath(s);
    if (!existsSync(file)) {
      problems.push(`${s.tag}: ${e.path} is in the manifest and not in the tree.`);
      continue;
    }
    const buf = readFileSync(file);
    if (sha256(buf) !== e.sha256) {
      problems.push(`${s.tag}: ${e.path} does not match the manifest hash — it `
        + `was changed by something other than this renderer. Re-render it, or `
        + `run --all if the change was intended.`);
    }
    const size = pngSize(buf);
    if (!size) problems.push(`${s.tag}: ${e.path} is not a PNG.`);
    else if (size.w !== 1200 || size.h !== 630) {
      problems.push(`${s.tag}: ${e.path} is ${size.w}x${size.h}; a social card `
        + `is 1200x630 and every scraper crops or rejects anything else.`);
    }
  }
  const extra = Object.keys(manifest).filter(
    (t) => !want.some((s) => s.tag === t));
  for (const t of extra) {
    problems.push(`the manifest carries ${t}, which metros.json does not — `
      + `drop the entry and its PNG, or restore the instance.`);
  }
  if (problems.length) {
    console.error("build-og-image --check: FAIL — %d problem(s):", problems.length);
    for (const p of problems) console.error("  - " + p);
    process.exit(1);
  }
  console.log(`build-og-image --check: OK — ${want.length} social card(s), each `
    + `1200x630, hash-matching the manifest, and labelled as metros.json says. `
    + `(Provenance only: nothing here reads the pixels.)`);
}

const arg = process.argv[2];
if (arg === "--check") {
  check();
} else if (arg === "--all") {
  for (const s of surfaces()) await render(s);
  buildManifest();
} else if (arg && surfaces().some((s) => s.tag === arg)) {
  await render(surfaces().find((s) => s.tag === arg));
  buildManifest();
} else {
  console.error("usage: node scripts/build_og_image.mjs <tag>|root|--all|--check");
  console.error("       tags: " + surfaces().map((s) => s.tag).join(", "));
  process.exit(2);
}
