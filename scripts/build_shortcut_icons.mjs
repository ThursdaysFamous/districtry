#!/usr/bin/env node
// Renders the long-press shortcut icons the installed app shows on its home
// screen icon, from their SVG sources under districtry/icons/.
//
// Usage:
//   node scripts/build_shortcut_icons.mjs   # render every shortcut-*.svg
//
// WHAT THEY ARE (2026-10-21). The web app manifest's `shortcuts` puts "Use my
// location" and "Report a problem" on the menu a long press on the installed
// app's icon opens, on Android. Each needs a PNG: Bubblewrap, which builds the
// Google Play app, wants a PNG of at least 96 pixels with purpose "any" and
// scales it down to 48-192 pixels itself, so each source is rendered once at
// 192. The design is the favicon's violet with a white glyph on a full circle,
// because launchers show a shortcut's icon inside a circle and a circle survives
// any mask a launcher applies.
//
// WHAT IT WRITES. districtry/icons/shortcut-<name>-192.png beside each
// districtry/icons/shortcut-<name>.svg, and districtry/icons/shortcut-icons.json
// recording the SHA-256 of each source and of the PNG rendered from it.
// scripts/build_manifests.py copies each PNG to the site's root and its
// `--check` (stdlib, in CI) fails when a source changed after its PNG was
// rendered, or a PNG was replaced by anything this script did not write. That
// proves where each PNG came from, never that it looks right: only a person
// looking at it can tell that.
//
// A rare operator step: it needs Playwright's Chromium, as
// scripts/build_og_image.mjs does.

import { createHash } from "node:crypto";
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const ICON_DIR = join(REPO_ROOT, "districtry", "icons");
const RECORD = join(ICON_DIR, "shortcut-icons.json");
const PX = 192;

const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");

const sources = readdirSync(ICON_DIR).filter((n) => /^shortcut-[a-z]+\.svg$/.test(n)).sort();
if (!sources.length) {
  throw new Error(`no shortcut-*.svg under ${ICON_DIR}`);
}

const { chromium } = await import("playwright");
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: PX, height: PX }, deviceScaleFactor: 1 });
const record = {};
for (const name of sources) {
  const svg = readFileSync(join(ICON_DIR, name));
  await page.setContent(
    "<!doctype html><html><head><style>html,body{margin:0;background:transparent}" +
    `svg{display:block;width:${PX}px;height:${PX}px}</style></head><body>` +
    svg.toString("utf-8") + "</body></html>");
  const png = await page.screenshot({ omitBackground: true, clip: { x: 0, y: 0, width: PX, height: PX } });
  const out = name.replace(/\.svg$/, `-${PX}.png`);
  writeFileSync(join(ICON_DIR, out), png);
  record[out] = { source: name, source_sha256: sha256(svg), png_sha256: sha256(png), px: PX };
  console.log(`build-shortcut-icons: rendered ${name} -> ${out}`);
}
await browser.close();
writeFileSync(RECORD, JSON.stringify(record, null, 2) + "\n");
console.log(`build-shortcut-icons: wrote ${RECORD.slice(REPO_ROOT.length + 1)}`);
