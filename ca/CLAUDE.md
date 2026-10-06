# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

San Francisco District Explorer: a single-file, dependency-light web app. Click a point in San Francisco (or search an address) and it reports every civic district containing that point and who represents you there — supervisor districts, state/federal legislative districts, police districts, school attendance areas, and more. Deployed as a static site to `sf.chidistricts.com` (see `CNAME`). One of several sibling metro forks; Chicago is the reference implementation.

**There is no build step, no framework, and no server-side code.** The entire app — styles, core, and all layer modules — lives inline in `index.html` (~5,000 lines). `sw.js` is the service worker; `data/app/*.json` are runtime-fetched data files. Everything else is data pipeline, scrapers, or CI.

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: San Francisco (`sf`) — https://districtry.com/ca/
- Geocoders: address Photon (SF-bounded type-ahead); unbounded Photon (whole-coverage, sibling-metro lookup); POI Nominatim (office-address pin lookup, serial >=1s queue)
- Ground truth: 37.77927,-122.41924 (SF City Hall (Civic Center)) → supervisor-district 5; neighborhood Tenderloin; police-district NORTHERN. Negative point 37.74000,-122.59000 (Open Pacific west of Ocean Beach, beyond CA state waters - outside every layer, including the water-inclusive TIGERweb legislative chambers).
- Layers: 16 registered (political 7, safety 3, schools 2, geography 4); `registerLayer(` floor 8. Debug namespace `window.SFExplorer`.
- Scheduled workflows: `ca-update-congress-roster.yml` (Mon 13:00 UTC); `ca-update-legislature-roster.yml` (Tue 13:00 UTC); `ca-update-sf-supervisor-roster.yml` (Wed 13:00 UTC); `ca-validate-sources.yml` (1st of month 14:00 UTC).
- Source registry: `scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# Run locally — any static server works; internet needed for live-API layers:
python3 -m http.server 8000    # then open http://localhost:8000/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ node scripts/smoke_test.mjs   # serve first, then run

# Static gate (run after any data/app regeneration or app edit):
python3 scripts/validate_index.py index.html

# Generated-region gate (Conversion 2): per-fork facts live ONCE in
# metro-worksheet.json; GENERATED:BEGIN/END regions in index.html, sw.js,
# validate_index.py, smoke_test.mjs, CLAUDE.md, and README.md are emitted from
# it. NEVER hand-edit a GENERATED region — edit the worksheet and regenerate:
pip install -c scripts/requirements.txt jsonschema
python3 scripts/generate_metro_files.py            # regenerate in place
python3 scripts/generate_metro_files.py --check    # the CI drift gate

# Source-freshness gate (checks upstream datasets haven't gone stale):
pip install -c scripts/requirements.txt requests
python3 scripts/validate_sources.py            # add --offline to skip network
```

`smoke_test.mjs` is a single end-to-end script, not a framework — there are no "individual tests" to select. It asserts the app boots, registers all layers, classifies SF City Hall against ground truth (Supervisor District 5, Tenderloin neighborhood, NORTHERN police district — plus U.S. House 11 / CA Senate 11 / CA Assembly 17 with their officeholder roster joins), and degrades to an isolated error card when a source fails. `node_modules`/`package.json` are intentionally gitignored — this repo never commits build artifacts.

**Sandboxed environments (Claude Code web) — Leaflet CDN egress:** `index.html` loads Leaflet from `cdnjs.cloudflare.com`. In the Claude Code web/sandbox the headless browser cannot reach that CDN — Chromium doesn't use the agent HTTPS proxy, so the request resets (`ERR_CONNECTION_RESET` → `L is not defined` → the app never boots). This is environmental, **not** a code regression; don't chase it in app code. It's handled automatically: a `SessionStart` hook (the REPO ROOT's `.claude/settings.json`) runs the repo-root `scripts/vendor_leaflet.sh`, which `curl`s Leaflet (curl *does* go through the proxy) into each instance's own `scripts/vendor/leaflet/` — `sf/scripts/vendor/leaflet/` for this one (gitignored). `sf/scripts/smoke_test.mjs` then serves those files same-origin via `page.route`, so the app boots. Production and GitHub Actions CI are untouched — they reach the CDN directly and the vendor dir is absent, so the fallback is skipped. To run the smoke test manually in this env, `bash scripts/vendor_leaflet.sh sf` from the repo root first (or just rely on the session-start hook, which vendors every instance). **There is no `sf/scripts/vendor_leaflet.sh`** — the three byte-identical per-fork copies collapsed into that one instance-aware script when the forks became folders.

`validate_index.py` is the merge gate: it confirms `index.html` passes `node --check`, still registers every layer (a drop in the `registerLayer(` count fails), embeds no dataset inline, and that every `data/app/` file is present with the expected feature/roster counts.

`validate_sources.py` is the **freshness** gate (complements the merge gate above). It catches the failure mode the roster scrapers can't: a publisher silently superseding a dataset the app hardcodes. DataSF (Socrata) datasets can be re-published under a **new id** each year — SFUSD *School Attendance Areas* ship a fresh `…(YYYY-YYYY)` edition every school year — so the old id keeps returning stale data with no error. The script carries a manifest of every live DataSF dataset id, the pre-built boundary files' provenance URLs, and the live endpoints the app depends on, and checks: (1) the manifest still matches index.html (drift guard), (2) each Socrata id still resolves and keeps its expected name, searching the portal catalog for a **newer-year edition** of the year-versioned ones, (3) the six pre-built boundary sources (three DataSF anchors + three TIGERweb CA chambers) are reachable and their built `data/app/` files present, (4) the live Census ZCTA endpoint resolves. Note the SF-specific catalog quirk: DataSF is **not** indexed by the federated `api.us.socrata.com`, so newer-edition search hits the portal-local `data.sfgov.org/api/catalog/v1` (no `domains`/`only` filters). It **never edits the app** — swapping a dataset id is schema-sensitive — it exits non-zero only on hard FAILs and reports a newer edition as a WARN. `.github/workflows/validate-sources.yml` runs it monthly and opens/updates a single tracking issue on any WARN/FAIL (the job stays green; the issue is the signal). When a dataset id is swapped in index.html, update the manifest in `validate_sources.py` to match.

## Architecture: stable core + pluggable layer modules

All inside `index.html`, wrapped in one IIFE. The full contract and per-thread build log live in `docs/BUILD_PLAYBOOK_1.md`; `docs/OPTIMIZATION_PLAYBOOK.md` holds measured optimization tasks. `docs/METRO_EXPANSION_PLAYBOOK.md` is the recipe for porting the app to a new metro (Chicago is the reference implementation; each metro is its own fork), with the completed NYC port's build record archived at `docs/archive/METRO_EXPANSION_NYC.md` (fork: `github.com/ThursdaysFamous/DistrictExplorer-NYC`).

**Core** provides: the Leaflet map, click-to-select + debounced SF-bounded Photon geocoder, a global `state` object `{selectedPoint, sequence, layersOn, ...}`, the layer registry + result-card framework, selected-boundary highlight, and URL-hash permalinks (`#point=lat,lng&layers=supervisor-district,congress`). A small namespace is exposed as `window.SFExplorer` for debugging.

**Shared utilities** (reuse these; don't reinvent):
- `sanitize(str)` / render via `textContent` — all external strings must go through one of these. Injecting scraped or API text as HTML is treated as a real security bug here.
- `pointInGeometry(pt, geometry)` — the point-in-polygon test every polygon layer's `query` uses.
- `fetchJSONWithRetry(url, opts, retries)` — the standard data-fetch path (retry + failure isolation).
- `haversineMiles(...)` — for the nearest-N layers, which use straight-line proximity instead of point-in-polygon (police/fire stations via the `registerNearestPointLayer` factory; `school-site` as a bespoke block).

**A layer module** is registered via `registerLayer({ id, group, label, overlay: {load, style}, query(point, seq), render(result) })`. `group` is one of `political | safety | schools | geography`. Overlays lazy-load their boundaries on first toggle and are cached; `query` runs locally against the cached geometry. Families of similar layers are built by factory helpers (`registerPolygonLayer`, `registerSchoolZone`, `registerCpsNetwork`, `registerIlgaChamber`, `registerNearestPointLayer`) — follow the existing factory when adding a sibling. The factories derive each layer's hover-popup identity (`hoverName`) from the same properties its card reads, so the two surfaces can't disagree; a bespoke `registerLayer` block declares `hoverName(feature)` explicitly. Optional contract field `pointOfInterest(result) => {label, address} | null` drops a geocoded map pin (used by the school-zone layers). Optional contract field `coverage(point) => boolean | Promise<boolean>` declares where a layer's data applies (location relevance): outside its coverage the layer *hides* — toggle block, card, map overlay, hover-snapshot row, relationship outlines, and query all suppressed — without touching `state.layersOn`, so `layers=` permalinks survive and the layer reappears when a selected point re-enters coverage; a throwing coverage test fails open (the layer runs as if undeclared). San Francisco is a consolidated city-county with no partial-coverage problem, so **no SF layer declares `coverage`** — every layer runs everywhere (the reference's `chicagoCoverage`/`cookCountyCoverage` tiling has no SF analog). One layer uses the `subOf` sub-layer pattern: `election-precinct` under `supervisor-district` (mirroring the reference's ward-precinct dance — toggling the child auto-enables the parent as outline-only and fills it with precinct polygons). SF **does** use the engine's `makeSocrataPointLoader` (point datasets whose coordinates live only in properties: fire-station `nc68-ngbr`, library `fhhu-wqa7`, school-site `7e7j-59qk`) and `loadArcGISGeoJSON` (the `bart-director` geometry, from BART's own ArcGIS org); `loadArcGISPaged` stays for cross-fork parity but is unused here — the Post Office layer's USGS National Map service is fetched directly by URL. See `docs/METRO_EXPANSION_PLAYBOOK.md` (master in the Chicago repo).

**Two invariants that pervade the code:**

1. **Stale-async guard via `sequence`.** Every point selection bumps `state.sequence`. Async work captures `seq` and bails (`if (seq !== state.sequence) return;`) when a newer point has been selected. Preserve this in any code that awaits between selection and render.

2. **Per-layer failure isolation.** Each result card is independent: a layer whose data source is down shows an error + Retry *inside its own card* and never affects the others. Never let one layer's failure throw out of its `query`/`render` into shared code.

**Result-card content order (fleet convention):** a card leads with the layer name (the card header), then the district identifier, then — wherever a verifiable source exists — the representative(s)/officeholder(s), the office location, contact info (phone/email), and a link to more detail, in that order. Deviations are allowed where the concept demands them (nearest-N lists, layers with no elected officer), but when identity, location, or contact data exists in a layer's source, surface it on the card rather than leaving it in the dataset. Known gaps are tracked in the Chicago repo's `docs/DATA_LAYER_GUIDEBOOK.md` backlog.

**Honesty rules (non-negotiable, enforced in review):** officeholder data is never guessed. Where no verifiable roster source exists, cards link to the official body instead of inventing a name. External strings are always sanitized or set via `textContent`.

## Cross-metro engine parity

This app is one instance folder in the districtry repo, served at `districtry.com/ca/`; **Illinois (`il/`) is the reference implementation**. The metro-agnostic engine inside `index.html` is fenced with `/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and must stay **byte-identical across forks**; everything city-specific those blocks reference lives in the `METRO:BEGIN config` block near the top of the script. When editing:

- Never inline a city-specific value in an ENGINE block — add a variable to the METRO config block instead.
- Parity is maintained **by construction**: there is ONE copy of every block under the root `engine/`, `python3 scripts/compose_app.py` splices it into this folder's `index.html` and `sw.js`, and its `--check` is the CI gate (`python3 scripts/check_engine_parity.py ca/index.html` is the fence lint). The release channel this bullet used to describe — `engine.lock.json`, `apply_engine.py`, `engine-bump.yml`, `engine-parity.yml` — was retired at R2.1 and none of those files exists (corrected 2026-09-02).
- Full protocol + the known reconciliation backlog: `docs/ENGINE_SYNC.md`.

## Data pipeline

Most layers fetch live public APIs at runtime (DataSF / Socrata, Census TIGERweb, Nominatim / Photon). Layers whose geometry is decadal or has no runtime API ship their data as same-origin files under `data/app/`, fetched on first toggle:

- **Boundary geometry** (`supervisor-districts.json`, `sf-neighborhoods.json`, `police-districts.json` plus the three SF-clipped legislative chambers `{congress,ca-senate,ca-assembly}-districts.json`) — the first three mapshaper-simplified from the full-precision GeoJSON in `data/` via `scripts/build_embedded_boundaries.py`; the chambers pre-built from Census TIGERweb (`STATE='06'`) via `scripts/build_legislative_boundaries.py` (rare operator steps). Service worker serves these **cache-first** (boundaries change ~once a decade).
- **Officeholder rosters** (`congress-roster.json`, `ca-{senate,assembly}-members.json`, `sf-supervisor-members.json`) — regenerated **weekly by CI** from builder output. Service worker serves these **network-first** so a returning visitor never gets a stale officeholder. Two more network-first files are **hand-maintained, not CI-built**: `early-voting-sites.json` (the Voting Center & Ballot Drop-off layer — hand-curated per election from the Department of Elections pages; refresh it and the card's election-label intro together) and `bart-directors.json` (the BART Director roster — hand-verified against bart.gov/about/bod per the WATCH.md even-year election row; it has no builder script by design).

**Builder pattern:** SF's CI-built rosters come straight from canonical machine-readable sources (OpenStates `ca.csv`, unitedstates/congress-legislators, DataSF `hcgx-vtsb`), so there are **no HTML scrapers** — each CI roster is a single `build_*.py` that downloads its source with stdlib `urllib`/`csv` and writes the `data/app/*.json` file with count guards (it refuses to write if too few records resolve). The two hand-maintained files (`early-voting-sites.json`, `bart-directors.json`) bypass the builder pattern deliberately — their sources are human-readable pages, and the honesty rules require a human transcription + verification step. Builders emit plain JSON via `json.dump` into `data/app/`, and the app renders every external string through `sanitize()`/`textContent` — together that closes the injection surface. (The historical `js_string()`-style `</script>` + U+2028/U+2029 escaping guard existed only when data was spliced directly into the HTML; it closed a real injection bug then, and becomes mandatory again only if roster text is ever spliced into HTML/JS — don't.)

## CI workflows (`.github/workflows/`)

- `smoke-test.yml` — runs the behaviour gate on every PR and push to `main`.
- `update-{congress,ca-legislature,sf-supervisor}-roster.yml` — weekly (staggered) roster refreshes. Each re-fetches its source, rebuilds `data/app/`, runs `validate_index.py`, and — if anything changed — **opens a PR rather than committing to `main`.** Officeholder data always gets a human review before it ships. Match this pattern for any new roster: never auto-commit roster changes to `main`.
- `validate-sources.yml` — monthly source-freshness check. Runs `scripts/validate_sources.py`; on any WARN/FAIL (e.g. a DataSF dataset superseded by a newer-year edition, or a pre-built boundary source gone unreachable) it **opens or updates a single tracking issue** rather than editing anything — the job stays green, the issue is the signal. Same "surface for a human, don't auto-apply" convention as the roster PRs.
- `deploy-pages.yml` (repo root) — publishes `main`, this folder included, to GitHub Pages; the committed bytes are the deployed bytes. An ENGINE-fenced change is made in the root `engine/` block file and recomposed, never in this folder's `index.html` (corrected 2026-09-02: the deploy no longer splices a pinned bundle).

## Conventions

- Code style is ES5-flavored (`var`, `function` expressions) throughout `index.html` — match it when editing existing modules.
- The "verified" date shown in the UI is hardcoded near the boot block in `index.html`; bump it when reverifying data sources.
- This is a public-facing civic tool that explicitly disclaims legal precision — accuracy and the honesty rules matter more than feature velocity.
