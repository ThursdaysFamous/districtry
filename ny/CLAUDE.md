# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

NYC District Explorer: a single-file, dependency-light web app. Click a point in New York City (or search an address) and it reports every civic district containing that point and who represents you there — boroughs, council/community/legislative districts, NYPD precincts/sectors, school zones, and more. Deployed as a static site to `nyc.chidistricts.com` (see `CNAME`). This is a metro fork of the Chicago reference implementation (`ThursdaysFamous/DistrictExplorer-CHI`); the build record for the port is archived at CHI `docs/archive/METRO_EXPANSION_NYC.md`, and the completed conformance work order is archived at `docs/archive/NYC_CONFORMANCE.md`.

**There is no build step, no framework, and no server-side code.** The entire app — styles, core, and all layer modules — lives inline in `index.html`. `sw.js` is the service worker; `data/app/*.json` are runtime-fetched data files. Everything else is data pipeline, scrapers, or CI.

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: New York (`nyc`) — https://districtry.com/ny/
- Geocoders: address GeoSearch (city type-ahead, geosearch.planninglabs.nyc) then Photon bounded to the state when the city search finds nothing; unbounded Photon (whole-coverage, sibling-metro lookup); POI GeoSearch (office-address pin lookup; every layer that drops a pin is city-only)
- Ground truth: 42.65203,-73.75731 (Downtown Albany — measured inside the City of Albany, Albany County) → judicial-district 3; county Albany; nys-school-district ALBANY; municipality Albany. Negative point 41.76370,-72.68510 (Downtown Hartford, Connecticut — outside New York State and 66 km from the nearest geometry this instance ships. NOT a water point: the county, school-district, cities-towns, villages and three legislative files are all water-inclusive off Long Island and in Lake Ontario, so a mid-Sound or mid-lake click is positive, not negative).
- Layers: 33 registered (political 12, safety 5, schools 7, geography 9); `registerLayer(` floor 5. Debug namespace `window.NycExplorer`.
- Scheduled workflows: `ny-update-legislature-roster.yml` (Mon 13:00 UTC); `ny-update-congress-roster.yml` (Mon 13:30 UTC); `ny-update-nypd-roster.yml` (Tue 13:00 UTC); `ny-update-cec-roster.yml` (Wed 13:00 UTC); `ny-update-council-roster.yml` (Thu 13:00 UTC); `ny-validate-sources.yml` (1st of month 12:00 UTC).
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

`smoke_test.mjs` is a single end-to-end script, not a framework. It asserts the app boots, registers all layers, classifies City Hall against the three no-API anchors (borough → Manhattan, judicial district 1, municipal court 1), verifies a mid-East-River click honestly resolves to **no** borough (never snap-to-nearest), and degrades to an isolated error card when a source fails. `node_modules`/`package.json` are intentionally gitignored — this repo never commits build artifacts.

**Sandboxed environments (Claude Code web) — Leaflet CDN egress:** `index.html` loads Leaflet from `cdnjs.cloudflare.com`, which the sandboxed browser can't reach. Handled automatically: the REPO ROOT's `scripts/vendor_leaflet.sh` curls Leaflet into each instance's own vendor dir — `nyc/scripts/vendor/leaflet/` for this one (gitignored) — and `nyc/scripts/smoke_test.mjs` serves it same-origin via `page.route`. Production and CI are untouched. Before a local smoke run in such an environment, run `bash scripts/vendor_leaflet.sh nyc` from the repo root. **There is no `nyc/scripts/vendor_leaflet.sh`** — the three byte-identical per-fork copies collapsed into that one instance-aware script when the forks became folders.

`validate_index.py` is the merge gate; `validate_sources.py` is the monthly freshness gate (ported from CHI in Phase 0.2 — its manifest is the machine-checked registry of every Socrata id, ArcGIS/TIGERweb endpoint, and anchor provenance this fork depends on).

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with `/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers, and since the consolidation (R2.1, `docs/DEV_PROCESS_ASSESSMENT.md` at the repo root) there is ONE copy of every block under the root `engine/`: `python3 scripts/compose_app.py` splices it into this folder's `index.html` and `sw.js`, and its `--check` is the CI gate. The release channel this paragraph used to describe — `engine.lock.json`, `apply_engine.py`, `engine-bump.yml` — was retired with it, and none of those files exists (corrected 2026-09-02). Edit the block file under `engine/` and recompose, never the fence here; never inline a city-specific value in one — city values live in the `METRO:BEGIN config` block (worksheet-generated). `docs/ENGINE_SYNC.md` is the engine's history and block inventory, not the procedure.

Shared utilities (reuse these; don't reinvent): `sanitize()`/`textContent` for every external string, `pointInGeometry()`, `fetchJSONWithRetry()`, `haversineMiles()`. Layer modules register via `registerLayer({ id, group, label, overlay, query, render })`; families go through the factories (`registerPolygonLayer`, `registerSchoolZone`, `registerCpsNetwork`, `registerIlgaChamber` — shared engine names kept fork-agnostic) with NYC-side wrappers carrying city dataset schemas (`registerNycZone`, `registerBoroughOfficeLayer`). The two invariants that pervade the code: the stale-async `sequence` guard, and per-layer failure isolation (one layer's dead source never breaks another's card).

**Result-card content order (fleet convention):** a card leads with the layer name (the card header), then the district identifier, then — wherever a verifiable source exists — the representative(s)/officeholder(s), the office location, contact info (phone/email), and a link to more detail, in that order. Deviations are allowed where the concept demands them (nearest-N lists, layers with no elected officer), but when identity, location, or contact data exists in a layer's source, surface it on the card rather than leaving it in the dataset. Known gaps are tracked in the Chicago repo's `docs/DATA_LAYER_GUIDEBOOK.md` backlog.

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable roster exists the card links to the official body (`cec-members.json` ships as a placeholder for exactly this reason (CEC members are decentralized across independent council sites, no scrapable source); `borough-officials.json` is operator-maintained and now carries verified BP/DA names; NYPD resolves ~74/78 commanding officers with honest nulls). External strings are always sanitized or set via `textContent`. Water clicks resolve honestly to "no district" — much of the in-bounds map is river/bay (METRO_BBOX runs SW Tottenville → NE north Bronx, out to the Rockaways) and the app never snaps to the nearest shore.

## NYC-specific notes worth keeping

- **Socrata**: anonymous `.json` requests 403 on NYC's portal, so the METRO block carries a Socrata app token — a public throttling identifier, not a secret (never put an API Key *secret* there).
- **Hover keys** exclude the encoded fields `boro_cd` and `electdist` on purpose: they need decoding before display and would misread raw. Re-seed hover keys from observed NYC field names via the worksheet.
- **Geocoders**: `geocodeAddress()`/`poiGeocodeRequest()` use GeoSearch (`geosearch.planninglabs.nyc`), `geocodeUnbounded()` uses Photon — provider code is fork code by design (see the GEOCODER section in `index.html`).
- `docs/BUILD_PLAYBOOK_1.md`, `docs/OPTIMIZATION_PLAYBOOK.md`, and `docs/REDISTRICTING_RUNBOOK.md` are **pointer stubs** — the masters live in the CHI repo. Never grow a copy here.

## Data pipeline

Most layers fetch live public APIs at runtime (NYC Open Data / Socrata, ArcGIS, TIGERweb, GeoSearch). Layers with no public API ship same-origin files under `data/app/`: boundary geometry for the three anchors (built by `scripts/build_embedded_boundaries.py`, which registers all three anchor provenances) served cache-first, and officeholder rosters (scraper → builder pairs with count guards: `ny_legislature_scraper`/`build_ny_roster`, `council_scraper`/`build_council_roster`, `nypd_precinct_scraper`/`build_nypd_roster`, `cec_scraper`/`build_cec_roster`, `build_congress_roster`, `build_borough_officials`) served network-first so a returning visitor never gets a stale officeholder.

## CI workflows (`.github/workflows/`)

- `smoke-test.yml` — the `--check` generated-region gate, then the behaviour gate, on every PR and push to `main`.
- `deploy-pages.yml` (repo root) — publishes `main`, this folder included, to GitHub Pages; the committed bytes are the deployed bytes. The `engine-bump.yml` workflow this list used to carry was retired with the release channel (corrected 2026-09-02).
- `update-{ny-legislature,congress,nypd,cec,council}-roster.yml` — weekly staggered roster refreshes; each opens a PR, never commits to `main`. Officeholder data always gets a human review before it ships.
- `validate-sources.yml` — monthly freshness + redistricting watch; opens/updates one tracking issue, never edits anything.

## Conventions

- Code style is ES5-flavored (`var`, `function` expressions) throughout `index.html` — match it when editing existing modules.
- The "verified" date shown in the UI is hardcoded near the boot block in `index.html`; bump it when reverifying data sources.
- `WATCH.md` at repo root is NYC's redistricting watch calendar (when to look); the response procedure is the Chicago-mastered `docs/REDISTRICTING_RUNBOOK.md`.
- This is a public-facing civic tool that explicitly disclaims legal precision — accuracy and the honesty rules matter more than feature velocity.
