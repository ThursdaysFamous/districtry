# Optimization & Refinement Playbook — San Francisco

> **Historical measurement record.** Every count and figure below is a measurement as of
> **2026-07-18**, when the app had 14 layers, 11 `data/app/` files, and 5 rosters. The app
> has since grown (16 layers / 12 files / 6 rosters as of 2026-07-19 — Election Precinct +
> BART Director). Current facts live in `CLAUDE.md`; a re-measurement gets a new dated
> section, it doesn't overwrite this one.

**Fork:** ThursdaysFamous/DistrictExplorer-SF · **Date:** 2026-07-18 · **Scope:** `index.html` (14 layers), `sw.js`, `data/app/` payloads, boot + interaction compute.

This is **San Francisco's own optimization pass**, measured against this working tree — not the Chicago reference record. (Chicago's campaign is archived in that repo; the engine-level wins it shipped are byte-identical here and are noted below where SF inherits them.) Every number here was produced by re-running the profiler, not carried over.

## Methodology & what to trust

Measured with `scripts/perf_profile.mjs` (the CDP harness, localized to SF's ground truth: City Hall `37.77927,-122.41924`; offline anchors `supervisor-district` / `neighborhood` / `police-district`; the `window.SFExplorer` boot signal). It serves the repo over a gzip server that mirrors GitHub Pages delivery, serves Leaflet + a stub tile same-origin (the sandbox can't reach the CDN), and blocks the live district APIs. Payload bytes are `gzip -9`.

- **Environment-independent — trust as absolute:** payload bytes, V8 compile, boot script-duration, DOM/heap counts, CPU-sample *shape*, and every A/B *ratio*.
- **Sandbox-inflated — relative only:** paint / pan / zoom wall-times (headless Chromium rasterizes on software GL, no GPU).
- **NOT measurable here — flagged, not guessed:** production PageSpeed-Insights mobile FCP/LCP (real network + CDN + device), and live-layer first-toggle latency (DataSF / TIGERweb / USGS are blocked in the sandbox).

## Measured state (working tree, 2026-07-18)

**Cold boot — median of 7 (run 1 is a cold-cache/compile outlier, excluded from the medians):**

| Metric | Median | Notes |
|---|---|---|
| Time to app-ready | **152 ms** | window.SFExplorer assigned (end of boot IIFE) |
| First Contentful Paint | **148 ms** | |
| DOM interactive | 109 ms | |
| Script duration | **46 ms** | environment-independent |
| V8 compile | **3.1 ms** | |
| Recalc style / Layout | 19 ms / 59 ms | |
| JS heap / DOM nodes | **3.1 MB / 562** | at boot, before any layer |
| Boot long tasks | **none** | (beyond the cold first run) |

**Payload (raw / gzip):**

| Asset | Raw | Gzip | On the critical path? |
|---|---|---|---|
| `index.html` | 258,453 | **74,376** | yes — every visit |
| `sw.js` | 6,745 | 2,675 | SW install |
| self-hosted fonts (woff2) | — | ~84 KB | boot (inter 48.5 KB + big-shoulders 35.7 KB + plex-mono) |
| **`data/app/` total** (11 files) | 304,787 | **72,434** | first-toggle / SW precache |
| — `sf-neighborhoods.json` | 134,812 | **34,867** | **48% of the data/app gzip** |
| — `police-districts.json` | 36,020 | 9,043 | |
| — `supervisor-districts.json` | 30,972 | 7,405 | precached tiler (scope-mask) |
| — `ca-assembly-districts.json` | 23,954 | 5,056 | |
| — the other 3 geometry files | 11–12 KB ea. | 2.5 KB ea. | |
| — 5 rosters | 0.5–18 KB | 0.2–4.2 KB | network-first |

**Footprint & interaction:**

| Signal | Value |
|---|---|
| Layers registered | 14 |
| Footprint: baseline → 3 layers on | heap 4.03 → 5.99 MB · nodes 562 → 714 · paths 4 → 67 |
| All 6 offline polygon layers on | 85 SVG paths (the realistic worst case) |
| First click→classify | 45.8 ms wall / **16.7 ms CPU** (Leaflet `_updateLevels` = 54% — overlay draw, not app code) |
| Incremental point-move (P7) | 23.3 ms wall / **2.1 ms CPU** — the sequence-guarded partial update is cheap |
| Cold layer toggle-on | 35.8 ms wall / 4.6 ms CPU (GC + fetch) |
| Highlight drop-shadow filter, pan A/B | filter-ON **37.6 ms** vs OFF **16.7 ms** (~2.25× — environment-independent ratio) |
| Pan/zoom reproject at 85 vs 67 paths | zoom dominated by Leaflet `project` / `_projectLatlngs` (SVG reproject scales with path count) |

## What's healthy / at the floor

- **Boot is fast and clean.** 152 ms to app-ready, 46 ms script, 3.1 ms compile, 3.1 MB heap, 562 nodes, **zero boot long tasks**. The engine wins SF inherits — Leaflet loaded `defer`, CSS inlined (no render-blocking `<link>`), fonts self-hosted as same-origin woff2, boot gated on `DOMContentLoaded` — all hold. No SF-specific boot regression.
- **`index.html` at 74 KB gzip is near the floor** for a no-build single-file app carrying all 14 layer modules + styles inline. `validate_index.py` forbids inline datasets, so there is no hidden data blob to cut; the compressible mass is the engine + CSS, which are shared and already lean.
- **The incremental point-move is 2.1 ms CPU** — the `state.sequence` stale-guard + partial re-render keeps dragging the pin cheap.
- **The heaviest live layers were already pre-built (Thread 5).** The three legislative chambers, which the reference measured at ~5.7 s live from TIGERweb, ship as same-origin cache-first geometry here, so they classify offline in single-digit ms.

## Prioritized findings

### SF-1 — the Neighborhood geometry dominates the data payload *(top actionable; PENDING)*

`sf-neighborhoods.json` is **34,867 bytes gzip — 48% of the entire `data/app` gzip total (72,434) and 4.7× the next-largest file** (police-districts, 9 KB). It sits in `sw.js` `GEOMETRY_URLS`, so it was ~half of the geometry the service worker precached at install. **Since 2026-09-26 the worker precaches no geometry** (root `docs/OPTIMIZATION_PLAYBOOK.md` §10, phase 2): the file is fetched when a reader switches the Neighborhood layer on, so only those readers pay its size.

*Cause:* SF's 41 Analysis Neighborhoods carry very detailed shoreline geometry; the full-precision source (`data/sf-neighborhoods.geojson`) is 1.8 MB, and even at the current 10% Visvalingam retain / 6-decimal precision it lands at 134 KB raw.

*Recommendation:* re-simplify via `scripts/build_embedded_boundaries.py` with a tighter budget — a lower retain % and/or 5-decimal precision (~1.1 m, immaterial to a neighborhood boundary) — **re-validating the built-in gate**: ≥99.5% agreement with the full-precision source on the 2,000-random-point protocol, and zero points in two districts. Expected result: roughly halve the file (target ≈15–18 KB gzip). The saving this sentence originally claimed, the SW precache payload cut by ~25%, no longer exists since the precache holds no geometry; what remains is about 17–20 KB off the Neighborhood layer's first switch-on.

*Why it's PENDING, not shipped in this pass:* neighborhood boundaries drive point-in-polygon classification on a public civic tool, so this ships **only if the 2,000-point gate holds** — accuracy over bytes. That warrants a deliberate re-generation + gate review (and an operator eye on the coast), not a drive-by inside an audit. The tooling is ready (`build_embedded_boundaries.py` + mapshaper) and the source is present.

### SF-2 — production load-delivery + live-layer latency *(measure in prod; can't be done in-sandbox)*

The harness can't reach a real device, network, CDN, or the live APIs. The reference's Round-2 lesson was that the true production gap was **load delivery** (render-blocking third parties — the Leaflet CDN and basemap tiles), not payload compute. SF inherits the same mitigations (deferred Leaflet, `preconnect` to the three tile shards + cdnjs, self-hosted fonts, `dns-prefetch` for `data.sfgov.org` / `tigerweb.geo.census.gov`). **Confirm with a production PSI-mobile run** before assuming SF's delivery profile matches.

Live-layer first-toggle latency — `police-station` / `fire-station` / `elementary-attendance-area` / `school-site` / `zip-code` / `post-office` / `library` hitting DataSF / TIGERweb / USGS — is unmeasured here. These are small point/ZCTA queries (not the multi-thousand-feature payloads pre-building was built for), and the heaviest layers are already offline, so this is a monitoring item, not a known regression.

### Engine-level *(defer to the reference; byte-identical across forks)*

- **Highlight drop-shadow filter ≈2.25× pan-frame cost** (filter-ON 37.6 ms vs OFF 16.7 ms — an environment-independent ratio). This is the reference's "P9" finding; the selected-region highlight filter is **ENGINE** code, identical in every fork. Any fix ships as a reference engine release (SF consumes the engine at deploy), not a per-fork edit.
- **Canvas renderer — MEASURED-REJECTED for SF.** SVG reproject scales with path count, but SF's realistic worst case is **~85 same-origin polygon paths** (a user toggling all six offline polygon layers at once) — well inside SVG's comfortable range on real hardware. The reference's open question of porting to a canvas renderer is *even less* compelling here than for a bigger metro; SF should not carry that complexity.

## Honesty note

Boot compute, payload bytes, footprint counts, and A/B ratios above are real and environment-independent. Paint/pan/zoom absolute milliseconds are software-GL-inflated and used only as ratios. Production mobile FCP/LCP and live-API first-toggle latency were **not** live-verified (sandbox limits) and are called out as production-measurement TODOs rather than estimated. The one shippable optimization this pass surfaced (SF-1) is left PENDING behind its accuracy gate on purpose.
