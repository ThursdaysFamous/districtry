// Measure how each layer LOADS, in a real browser on a modelled slow network,
// and write layer-load.json at the repo root: for every layer in every app,
// how long a reader waits for the selected point's card, for the selected
// district to light up and for the layer's shapes to be drawn, and how many
// bytes arrive before each.
//
// It is the baseline for the load-optimization plan in
// docs/OPTIMIZATION_PLAYBOOK.md §10, and the same script measures each phase
// after it ships, so a claimed saving is a difference between two runs of one
// method rather than two methods.
//
// THE NETWORK IS MODELLED, NOT SAMPLED. A request's wait here would otherwise
// be the sandbox's route to a county server, which says nothing about a
// reader's. Every request made after the layer is switched on is held back by
// a fixed model and then released: one round trip (RTT) plus its compressed
// size over ONE shared downlink, so two large responses in parallel take as
// long as they would on a real link. The default is Lighthouse's mobile
// profile ("Slow 4G": 150 ms, 1.6 Mbps); PROFILE=fast is 40 ms and 10 Mbps.
// What the model leaves out, stated rather than implied: the SERVER's own time
// to answer (an ArcGIS query that takes a county server two seconds costs a
// reader two seconds and costs nothing here), HTTP/2 multiplexing and
// connection setup beyond one RTT, and the reader's CPU, which is this
// machine's. So the times compare layers and phases with one another; they do
// not predict a stopwatch.
//
// COMPRESSED SIZE is gzip of the body at level 6. Our own host (GitHub Pages)
// and the government ArcGIS and Socrata servers the apps read all compress
// JSON; a server that does not would send more.
//
// THE REAL RESPONSE IS FETCHED ONCE. Remote bodies are fetched through Node and
// cached for the run; a measured page whose remote request had to wait on the
// real network is measured again, so no recorded time includes the sandbox's
// own route.
//
// WHAT A PAGE MEASURES. The app boots with the point selected and no layer on,
// settles, and only then is the one layer switched on and the clock started —
// so the boot's own fetches (coverage outlines, the gaps panel) are not
// charged to the layer. The page is left until the card has an answer and the
// shapes are drawn and nothing has been requested for 2 s, or 120 s.
//
//     python3 -m http.server 8000              # serve the repo first
//     node scripts/probe_layer_load.mjs        # every app
//     TAGS=il LAYERS=ward,congress node scripts/probe_layer_load.mjs
//
// In a sandbox whose Node reaches the network only through a proxy, run it with
// NODE_USE_ENV_PROXY=1. BASE_URL overrides the server; CONC the page count.

import { chromium } from "playwright";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";
import { ROOT, anchorOf, EXTRA_POINTS, instances, vendorDir } from "./probe_points.mjs";

const OUT = join(ROOT, "layer-load.json");
const BASE = (process.env.BASE_URL || "http://localhost:8000").replace(/\/+$/, "") + "/";
const CONC = +(process.env.CONC || 6);
const PROFILES = {
  slow4g: { rtt: 150, bps: 1.6e6 },
  fast: { rtt: 40, bps: 10e6 },
};
const PROFILE_NAME = process.env.PROFILE || "slow4g";
const NET = PROFILES[PROFILE_NAME];
const TAGS = process.env.TAGS ? process.env.TAGS.split(",") : instances();
const ONLY = process.env.LAYERS ? new Set(process.env.LAYERS.split(",")) : null;
const SKIP_HOST = /(cartocdn\.com|zgo\.at|goatcounter\.com|photon\.komoot\.io|nominatim\.openstreetmap\.org|fonts\.(googleapis|gstatic)\.com|googletagmanager\.com|google-analytics\.com)$/;
const MAX_MS = 120000;

let problems = 0;
function problem(msg) { console.log("  FAIL  " + msg); problems++; }

function layerIds(tag) {
  const src = readFileSync(join(ROOT, tag, "index.html"), "utf8");
  const m = src.match(/var LAYER_AREA_RANK = \[([\s\S]*?)\n\s*\];/);
  if (!m) { problem(`${tag}: could not read LAYER_AREA_RANK from its index.html`); return []; }
  return [...m[1].matchAll(/"([^"]+)"/g)].map((x) => x[1]).filter((id) => !ONLY || ONLY.has(id));
}

const gz = (buf) => (buf && buf.length ? gzipSync(buf, { level: 6 }).length : 0);

const remote = new Map();
function fetchRemote(url, method, body, type) {
  const key = method + " " + url + " " + (body || "");
  let hit = remote.has(key);
  if (!hit) {
    remote.set(key, (async () => {
      try {
        const res = await fetch(url, { method, body: body || undefined,
          headers: body ? { "content-type": type || "application/x-www-form-urlencoded" } : {},
          signal: AbortSignal.timeout(45000) });
        const buf = Buffer.from(await res.arrayBuffer());
        return { status: res.status, buf, type: res.headers.get("content-type") || "", gz: gz(buf) };
      } catch (e) {
        return { status: 0, buf: null, type: "", gz: 0, err: String(e).slice(0, 80) };
      }
    })());
  }
  return { hit, promise: remote.get(key) };
}

const local = new Map();
function readLocal(pathname) {
  if (!local.has(pathname)) {
    const p = join(ROOT, decodeURIComponent(pathname));
    if (!existsSync(p)) local.set(pathname, null);
    else { const buf = readFileSync(p); local.set(pathname, { buf, gz: gz(buf) }); }
  }
  return local.get(pathname);
}

const typeOf = (p) => p.endsWith(".json") ? "application/json" : p.endsWith(".js") ? "application/javascript"
  : p.endsWith(".css") ? "text/css" : p.endsWith(".html") ? "text/html" : "application/octet-stream";

async function wire(page, tag, net) {
  const dir = vendorDir(tag);
  const origin = new URL(BASE).origin;
  // One downlink per page: a response starts arriving one RTT after it was
  // asked for, and cannot finish before the link has delivered everything
  // queued ahead of it.
  let linkFree = 0;
  function hold(bytes) {
    const now = Date.now();
    const start = now + NET.rtt;
    const finish = Math.max(start, linkFree) + (bytes * 8 * 1000) / NET.bps;
    linkFree = finish;
    return finish - now;
  }
  await page.route(/^https?:\/\//, async (route) => {
    const req = route.request();
    const u = new URL(req.url());
    const armed = net.armed;
    const t = armed ? Date.now() - net.t0 : null;
    if (u.origin === origin) {
      const f = u.pathname.endsWith("/") ? null : readLocal(u.pathname);
      if (!f || !armed) return route.continue();
      const rec = { t, host: "(this site)", path: u.pathname, bytes: f.gz, done: null };
      net.requests.push(rec);
      await new Promise((r) => setTimeout(r, hold(f.gz)));
      rec.done = Date.now() - net.t0;
      return route.fulfill({ status: 200, body: f.buf, contentType: typeOf(u.pathname) });
    }
    if (/cdnjs\.cloudflare\.com$/.test(u.hostname)) {
      const f = u.pathname.split("/").pop();
      if (existsSync(join(dir, f)))
        return route.fulfill({ body: readFileSync(join(dir, f)),
          contentType: f.endsWith(".css") ? "text/css" : "application/javascript" });
      return route.continue();
    }
    if (SKIP_HOST.test(u.hostname)) return route.abort();
    const { hit, promise } = fetchRemote(req.url(), req.method(), req.postData(), req.headers()["content-type"]);
    if (!armed) {
      const r = await promise;
      if (!r.buf) return route.abort();
      return route.fulfill({ status: r.status, body: r.buf,
        headers: { "content-type": r.type || "application/json", "access-control-allow-origin": "*" } });
    }
    const rec = { t, host: u.hostname, path: u.pathname, bytes: 0, status: 0, done: null };
    net.requests.push(rec);
    const asked = Date.now();
    const r = await promise;
    if (!hit && Date.now() - asked > NET.rtt) net.cold = true; // waited on the real network: measure again
    rec.bytes = r.gz; rec.status = r.status;
    const wait = hold(r.gz) - (Date.now() - asked);
    if (wait > 0) await new Promise((res) => setTimeout(res, wait));
    rec.done = Date.now() - net.t0;
    if (!r.buf) return route.abort();
    return route.fulfill({ status: r.status, body: r.buf,
      headers: { "content-type": r.type || "application/json", "access-control-allow-origin": "*" } });
  });
}

const FIND_EXPORTS = "Object.keys(window).map((k) => window[k]).find((v) => v && typeof v === 'object' && typeof v.layerLoadState === 'function')";

async function quiet(net, ms, max) {
  const start = Date.now();
  while (Date.now() - start < max) {
    await new Promise((r) => setTimeout(r, 250));
    const pending = net.requests.some((x) => x.done === null);
    const last = net.requests.length ? Math.max(...net.requests.map((x) => x.done ?? Date.now() - net.t0)) + net.t0 : start;
    if (!pending && Date.now() - last > ms && Date.now() - start > ms) return;
  }
}

async function measureOnce(browser, job) {
  const ctx = await browser.newContext({ serviceWorkers: "block", viewport: { width: 1200, height: 800 } });
  const page = await ctx.newPage();
  const net = { armed: false, t0: 0, requests: [], cold: false };
  await wire(page, job.tag, net);
  const out = { error: null };
  try {
    await page.goto(`${BASE}${job.tag}/#point=${job.pt.lat},${job.pt.lng}`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(`!!(${FIND_EXPORTS})`, null, { timeout: 45000 });
    await quiet(net, 2000, 30000);
    net.armed = true;
    net.t0 = Date.now();
    const clicked = await page.evaluate((id) => {
      const box = document.getElementById("toggle-" + id);
      if (!box) return false;
      if (!box.checked) box.click();
      return true;
    }, job.id);
    if (!clicked) throw new Error("no toggle-" + job.id + " checkbox");
    const seen = { card: null, cardState: null, highlight: null, overlay: null };
    let last = null;
    while (Date.now() - net.t0 < MAX_MS) {
      const s = await page.evaluate(`(${FIND_EXPORTS}).layerLoadState(${JSON.stringify(job.id)})`);
      const t = Date.now() - net.t0;
      last = s;
      if (s) {
        if (seen.card === null && s.card !== "loading" && s.card !== "off" && s.card !== "none") { seen.card = t; seen.cardState = s.card; }
        if (seen.highlight === null && s.highlight) seen.highlight = t;
        if (seen.overlay === null && s.overlay) seen.overlay = t;
        if (!s.relevant) break;
        const pending = net.requests.some((x) => x.done === null);
        const lastDone = Math.max(0, ...net.requests.map((x) => x.done ?? t));
        if (seen.card !== null && (seen.overlay !== null || s.card === "error") && !pending && t - lastDone > 2000) break;
      }
      await new Promise((r) => setTimeout(r, 50));
    }
    const before = (t) => net.requests.filter((x) => t !== null && x.done !== null && x.done <= t);
    const sum = (rs) => rs.reduce((a, x) => a + x.bytes, 0);
    Object.assign(out, {
      relevant: last ? last.relevant : null,
      card_ms: seen.card, card_state: seen.cardState ?? (last && last.card),
      highlight_ms: seen.highlight, overlay_ms: seen.overlay,
      features: last ? last.features : 0,
      requests: net.requests.length,
      bytes: sum(net.requests),
      bytes_before_card: seen.card === null ? null : sum(before(seen.card)),
      requests_before_card: seen.card === null ? null : before(seen.card).length,
      local_bytes: sum(net.requests.filter((x) => x.host === "(this site)")),
      hosts: [...new Set(net.requests.map((x) => x.host))].sort(),
      largest: net.requests.slice().sort((a, b) => b.bytes - a.bytes).slice(0, 3)
        .map((x) => ({ host: x.host, path: x.path.slice(0, 120), bytes: x.bytes })),
      unfinished: net.requests.filter((x) => x.done === null).length,
    });
  } catch (e) { out.error = String(e).slice(0, 200); }
  out.cold = net.cold;
  await ctx.close();
  return out;
}

async function visit(browser, job) {
  let r = await measureOnce(browser, job);
  // A remote response that had to come from the real network the first time
  // is cached now; measure again so only the model decides the waits.
  if (r.cold && !r.error) r = await measureOnce(browser, job);
  return r;
}

// ---- measure --------------------------------------------------------------
const jobs = [];
const points = {};
for (const tag of TAGS) {
  const pts = [anchorOf(tag, problem), ...(EXTRA_POINTS[tag] || [])].filter(Boolean)
    .map((p) => ({ lat: p.lat, lng: p.lng }));
  points[tag] = pts;
  for (const id of layerIds(tag)) pts.forEach((pt, i) => jobs.push({ tag, id, pt, pi: i }));
}
console.log(`probe-layer-load: ${jobs.length} page(s) across ${TAGS.join(", ")}, network ${PROFILE_NAME} (${NET.rtt} ms, ${NET.bps / 1e6} Mbps)`);
const results = [];
let next = 0;
const browser = await chromium.launch();
await Promise.all(Array.from({ length: CONC }, async () => {
  while (next < jobs.length) {
    const job = jobs[next++];
    const r = await visit(browser, job);
    results.push({ job, r });
    if (r.error) problem(`${job.tag} ${job.id} @${job.pt.lat}: ${r.error}`);
    process.stdout.write(`\r  ${results.length}/${jobs.length}`);
  }
}));
await browser.close();
console.log("");

// ---- write ------------------------------------------------------------------
const prior = existsSync(OUT) ? JSON.parse(readFileSync(OUT, "utf8")) : { apps: {} };
const sameMethod = prior.network && prior.network.profile === PROFILE_NAME;
const apps = sameMethod ? { ...prior.apps } : {};
for (const tag of TAGS) {
  const layers = ONLY && apps[tag] ? { ...apps[tag].layers } : {};
  for (const id of layerIds(tag)) {
    layers[id] = results.filter((x) => x.job.tag === tag && x.job.id === id)
      .sort((a, b) => a.job.pi - b.job.pi)
      .map(({ job, r }) => { const { cold, ...rest } = r; return { point: job.pi, ...rest }; });
  }
  apps[tag] = { points: points[tag], layers };
}
if (problems) { console.log(`probe-layer-load: ${problems} problem(s) — refusing to write.`); process.exit(1); }
const doc = {
  measured: new Date().toISOString().slice(0, 10),
  network: { profile: PROFILE_NAME, rtt_ms: NET.rtt, downlink_bps: NET.bps, bytes: "gzip -6 of each body" },
  apps: Object.fromEntries(Object.keys(apps).sort().map((k) => [k, apps[k]])),
};
writeFileSync(OUT, JSON.stringify(doc, null, 1) + "\n");
console.log("probe-layer-load: wrote layer-load.json");
