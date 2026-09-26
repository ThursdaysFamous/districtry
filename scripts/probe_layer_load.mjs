// Measure how each layer LOADS, in a real browser on a throttled network, and
// write layer-load.json at the repo root: for every layer in every app, how
// long a reader waits for the selected point's card, for the selected district
// to light up and for the layer's shapes to be drawn, and how many bytes
// arrive before each.
//
// It is the baseline for the load-optimization plan in
// docs/OPTIMIZATION_PLAYBOOK.md §10, and the same script measures each phase
// after it ships, so a claimed saving is a difference between two runs of one
// method rather than two methods.
//
// THE NETWORK IS CHROMIUM'S OWN THROTTLING, NOT THE SANDBOX'S ROUTE. A request's
// wait would otherwise be this machine's path to a county server, which says
// nothing about a reader's. So every request the page makes is answered by a
// local HTTP/2 server started here: the repo's own files served gzipped, as
// GitHub Pages serves them, and every other host's responses from a copy
// fetched once through Node. Once the app has booted, the page is throttled
// with DevTools' network conditions — Lighthouse's mobile profile ("Slow 4G":
// 150 ms, 1.6 Mbps; PROFILE=fast is 40 ms and 10 Mbps) — which delays each
// response by the latency and streams every body through one shared downlink,
// the way a phone on a slow connection receives it.
//
// Two earlier drafts of this file modelled the link in JavaScript and were
// wrong in ways worth recording. The first queued responses one after
// another, so a 100 KB point query waited behind a 4 MB download asked for a
// moment earlier, which no browser does; that invented a finding about the
// statewide TIGERweb layers, whose point queries in fact answer in about a
// second. The second shared the link fairly but released each body in one
// piece at the end, so a slow download looked to the app like a stalled one.
// Real throttling has neither defect.
//
// What it leaves out, stated rather than implied: the SERVER's own time to
// answer (an ArcGIS query that takes a county server two seconds costs a
// reader two seconds and costs nothing here), and the reader's CPU, which is
// this machine's. So the times compare layers and phases with one another;
// they do not predict a stopwatch. And every other host is served from ONE
// local origin, so connection setup to a new host is not charged either.
//
// A REMOTE RESPONSE IS FETCHED ONCE. A measured page that had to wait on the
// real network for one is measured again, so no recorded time includes the
// sandbox's own route.
//
// WHAT A PAGE MEASURES. The app boots with the point selected and no layer on,
// unthrottled, and settles; only then is the page throttled, the one layer
// switched on and the clock started — so the boot's own fetches (coverage
// outlines, the gaps panel) are not charged to the layer. The page is left
// until the card has an answer and the shapes are drawn and nothing has been
// requested for 2 s, or 120 s.
//
//     node scripts/probe_layer_load.mjs        # every app (it serves the repo itself)
//     TAGS=il LAYERS=ward,congress node scripts/probe_layer_load.mjs
//
// In a sandbox whose Node reaches the network only through a proxy, run it with
// NODE_USE_ENV_PROXY=1. CONC sets the page count. It needs openssl on the PATH
// for the local server's throwaway certificate.

import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { createSecureServer } from "node:http2";
import { tmpdir } from "node:os";
import { extname, join, normalize } from "node:path";
import { gzipSync } from "node:zlib";
import { ROOT, anchorOf, EXTRA_POINTS, instances, vendorDir } from "./probe_points.mjs";

const OUT = join(ROOT, "layer-load.json");
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

// ---- the local server ---------------------------------------------------------
const TYPES = { ".json": "application/json", ".js": "application/javascript", ".mjs": "application/javascript",
  ".css": "text/css", ".html": "text/html; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png",
  ".woff2": "font/woff2", ".webmanifest": "application/manifest+json", ".txt": "text/plain" };
const COMPRESS = new Set([".json", ".js", ".mjs", ".css", ".html", ".svg", ".txt", ".webmanifest"]);

const files = new Map();
function readRepo(pathname) {
  if (!files.has(pathname)) {
    let p = normalize(join(ROOT, decodeURIComponent(pathname)));
    if (!p.startsWith(ROOT)) { files.set(pathname, null); return null; }
    if (existsSync(p) && statSync(p).isDirectory()) p = join(p, "index.html");
    if (!existsSync(p)) files.set(pathname, null);
    else {
      const buf = readFileSync(p);
      const ext = extname(p);
      files.set(pathname, { buf: COMPRESS.has(ext) ? gzipSync(buf, { level: 6 }) : buf,
        gz: COMPRESS.has(ext), type: TYPES[ext] || "application/octet-stream" });
    }
  }
  return files.get(pathname);
}

const remote = new Map();
const coldPages = new Set();
function fetchRemote(url, method, body, type, page) {
  const key = method + " " + url + " " + (body ? body.toString("utf8") : "");
  if (!remote.has(key)) {
    if (page) coldPages.add(page);
    remote.set(key, (async () => {
      try {
        const res = await fetch(url, { method, body: body && body.length ? body : undefined,
          headers: body && body.length ? { "content-type": type || "application/x-www-form-urlencoded" } : {},
          signal: AbortSignal.timeout(45000) });
        const raw = Buffer.from(await res.arrayBuffer());
        return { status: res.status, buf: gzipSync(raw, { level: 6 }), type: res.headers.get("content-type") || "application/json" };
      } catch (e) {
        return { status: 0, err: String(e).slice(0, 80) };
      }
    })());
  }
  return remote.get(key);
}

const certDir = mkdtempSync(join(tmpdir(), "probe-load-"));
execFileSync("openssl", ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
  "-keyout", join(certDir, "key.pem"), "-out", join(certDir, "cert.pem"), "-subj", "/CN=localhost"], { stdio: "ignore" });
const server = createSecureServer({ key: readFileSync(join(certDir, "key.pem")),
  cert: readFileSync(join(certDir, "cert.pem")), allowHTTP1: true }, async (req, res) => {
  const cors = { "access-control-allow-origin": "*", "access-control-allow-headers": "*",
    "access-control-allow-methods": "GET, POST, OPTIONS" };
  if (req.method === "OPTIONS") { res.writeHead(204, cors); return res.end(); }
  const u = new URL(req.url, "https://localhost");
  if (u.pathname === "/__remote") {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const r = await fetchRemote(u.searchParams.get("u"), req.method, Buffer.concat(chunks),
      req.headers["content-type"], req.headers["x-probe-page"]);
    if (!r.buf) { res.writeHead(502, cors); return res.end(); }
    res.writeHead(r.status, { ...cors, "content-type": r.type, "content-encoding": "gzip" });
    return res.end(r.buf);
  }
  const f = readRepo(u.pathname);
  if (!f) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": f.type, ...(f.gz ? { "content-encoding": "gzip" } : {}) });
  res.end(f.buf);
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const ORIGIN = `https://localhost:${server.address().port}`;

// ---- one page -----------------------------------------------------------------
let pageSeq = 0;
async function wire(page, tag, net) {
  const dir = vendorDir(tag);
  await page.route(/^https?:\/\//, async (route) => {
    const req = route.request();
    const u = new URL(req.url());
    if (u.origin === ORIGIN) return route.continue();
    if (/cdnjs\.cloudflare\.com$/.test(u.hostname)) {
      // The sandbox's Chromium cannot reach cdnjs; the SessionStart hook vendors
      // Leaflet and MapLibre per instance. Absent (CI), let it through.
      const f = u.pathname.split("/").pop();
      if (existsSync(join(dir, f)))
        return route.fulfill({ body: readFileSync(join(dir, f)),
          contentType: f.endsWith(".css") ? "text/css" : "application/javascript" });
      return route.continue();
    }
    if (SKIP_HOST.test(u.hostname)) return route.abort();
    return route.continue({ url: `${ORIGIN}/__remote?u=${encodeURIComponent(req.url())}`,
      headers: { ...req.headers(), "x-probe-page": net.id } });
  });
  page.on("request", (req) => {
    if (!net.armed) return;
    const u = new URL(req.url());
    if (SKIP_HOST.test(u.hostname) || /cdnjs\.cloudflare\.com$/.test(u.hostname)) return;
    net.byReq.set(req, net.requests.push({ t: Date.now() - net.t0,
      host: u.origin === ORIGIN ? "(this site)" : u.hostname, path: u.pathname, bytes: 0, done: null }) - 1);
  });
  const finish = async (req, failed) => {
    const i = net.byReq.get(req);
    if (i === undefined) return;
    const rec = net.requests[i];
    rec.done = Date.now() - net.t0;
    if (failed) rec.failed = true;
    else try { rec.bytes = (await req.sizes()).responseBodySize; } catch { /* page closed */ }
  };
  page.on("requestfinished", (req) => finish(req, false));
  page.on("requestfailed", (req) => finish(req, true));
}

const FIND_EXPORTS = "Object.keys(window).map((k) => window[k]).find((v) => v && typeof v === 'object' && typeof v.layerLoadState === 'function')";

async function quiet(page, ms, max) {
  // Boot is unthrottled and unrecorded; wait for the network to go idle.
  try { await page.waitForLoadState("networkidle", { timeout: max }); } catch { /* keep going */ }
  await new Promise((r) => setTimeout(r, ms));
}

async function measureOnce(browser, job) {
  const ctx = await browser.newContext({ serviceWorkers: "block", ignoreHTTPSErrors: true,
    viewport: { width: 1200, height: 800 } });
  const page = await ctx.newPage();
  const net = { id: String(++pageSeq), armed: false, t0: 0, requests: [], byReq: new Map() };
  coldPages.delete(net.id);
  await wire(page, job.tag, net);
  const out = { error: null };
  try {
    await page.goto(`${ORIGIN}/${job.tag}/#point=${job.pt.lat},${job.pt.lng}`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(`!!(${FIND_EXPORTS})`, null, { timeout: 45000 });
    await quiet(page, 1500, 30000);
    const cdp = await ctx.newCDPSession(page);
    await cdp.send("Network.enable");
    await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: NET.rtt,
      downloadThroughput: NET.bps / 8, uploadThroughput: 750000 / 8 });
    coldPages.delete(net.id);
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
    await new Promise((r) => setTimeout(r, 100)); // let the last sizes() settle
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
      failed_requests: net.requests.filter((x) => x.failed).length,
    });
  } catch (e) { out.error = String(e).slice(0, 200); }
  out.cold = coldPages.has(net.id);
  await ctx.close();
  return out;
}

async function visit(browser, job) {
  let r = await measureOnce(browser, job);
  // A remote response that had to come from the real network the first time
  // is cached now; measure again so only the throttling decides the waits.
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
server.close();
console.log("");

// ---- write ------------------------------------------------------------------
const prior = existsSync(OUT) ? JSON.parse(readFileSync(OUT, "utf8")) : { apps: {} };
const sameMethod = prior.network && prior.network.profile === PROFILE_NAME && prior.network.method === "chromium";
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
  network: { method: "chromium", profile: PROFILE_NAME, rtt_ms: NET.rtt, downlink_bps: NET.bps,
    bytes: "encoded body size as received (gzip -6 for this site and for every copied remote response)" },
  apps: Object.fromEntries(Object.keys(apps).sort().map((k) => [k, apps[k]])),
};
writeFileSync(OUT, JSON.stringify(doc, null, 1) + "\n");
console.log("probe-layer-load: wrote layer-load.json");
