<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry New York City

**Click the map for every district you're in, and who represents you.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. Deployed as a static site — any static host or server works.

> **Status: all 27 layers live with officeholders; roster pipeline proven end-to-end.** This is the New York City fork of [District Explorer](https://github.com/ThursdaysFamous/DistrictExplorer-CHI) (Chicago is the reference implementation), built thread by thread following the [metro-expansion playbook](docs/METRO_EXPANSION_PLAYBOOK.md). **All build threads (0–6) are complete** — the full **27-layer** civic profile is wired (**Geography**: Borough/County, NTA, ZIP, Post Office, Library; **Political**: City Council, Election District, Community District/Board, U.S. House, NY Senate & Assembly, Judicial & Civil Court, Borough President, District Attorney, Early Voting Site; **Public Safety**: NYPD Precinct + Sector, Police Station & Firehouse, FDNY Battalion; **Schools**: ES/MS/HS zones with honest choice-based empty states, Community School District, CEC, School sites). The **roster pipeline** names the officeholders — NY Senate & Assembly (Open Legislation API), City Council, NYPD precinct commanders, U.S. House, live Community-Board chairs, and hand-verified Borough Presidents / District Attorneys — and runs weekly: each workflow re-scrapes its roster and opens a PR for human review (the first, [PR #6](https://github.com/ThursdaysFamous/DistrictExplorer-NYC/pull/6), refreshed the state legislature and populated every member's district-office address via Open States). Political cards carry office addresses with card + map pins wherever a verified source exists. The only roster still pending is Community Education Council members (`cec-members.json` ships as a placeholder until its scrape lands).

## Running it

There is nothing to build.

```bash
# any static server works:
python3 -m http.server 8000
# then open http://localhost:8000/
```

## What it answers (27 NYC layers)

Pick a point. The app runs a point-in-district lookup across every layer you have toggled on and builds a "civic profile" for that location. The NYC roster is **27 layers** (`metro-worksheet.json` is the source of truth; the fleet-wide inventory is the Chicago repo's `docs/DATA_LAYER_GUIDEBOOK.md`):

| Group | Layers |
|---|---|
| **Political** (11) | City Council District · Election District · Community District / Community Board · U.S. House District · NY State Senate · NY State Assembly · NY Supreme Court Judicial District · Civil Court (Municipal Court) District · Borough President · District Attorney · Early Voting Site (nearest 3) |
| **Public Safety** (5) | NYPD Precinct · NYPD Sector · Police Station (nearest 3) · Firehouse (nearest 3) · FDNY Battalion |
| **Schools** (6) | Elementary / Middle / High School Zone · Community School District · Community Education Council · School (nearest 3) |
| **Geography** (5) | Neighborhood (NTA) · ZIP Code (MODZCTA) · Borough / County · Post Office (nearest 3) · Library (nearest 3) |

Every result card is independent: a layer whose data source is down shows an error with a Retry button in that card and never affects the others. Because NYC is water-heavy, many in-bounds clicks land in rivers or bays and honestly resolve to **no district** — the app never snaps to the nearest.

Chicago layers with no honest NYC analog (county legislature, elected school board, elected police-oversight board, elected property-tax board) are **dropped, not faked** — see the playbook.

### Shareable links

The URL hash mirrors your current view (`#point=40.71274,-74.00602&layers=borough,council`). Copy it from the URL bar — or use the **Copy link** button on the selected-point chip — and anyone opening the link sees the same point with the same layers on.

## Architecture

Stable core + pluggable layer modules, all inside `index.html`. The engine contract and build history live in the Chicago repo's [`docs/BUILD_PLAYBOOK_1.md`](https://github.com/ThursdaysFamous/DistrictExplorer-CHI/blob/main/docs/BUILD_PLAYBOOK_1.md) — this repo carries only a [pointer stub](docs/BUILD_PLAYBOOK_1.md); the porting recipe (with the NYC port preserved as its worked example) is stubbed at [`docs/METRO_EXPANSION_PLAYBOOK.md`](docs/METRO_EXPANSION_PLAYBOOK.md).

- **Core (metro-agnostic, ~60–65% of `index.html`)**: Leaflet map, click-to-select + GeoSearch geocoder (debounced, NYC-scoped), global `{selectedPoint, sequence}` state where a monotonic sequence counter discards stale async results, shared `sanitize` / `pointInGeometry` / `fetchJSONWithRetry` utilities, the four layer factories (`registerPolygonLayer` / `registerSchoolZone` / `registerCpsNetwork` / `registerIlgaChamber`) and the Socrata / ArcGIS / TIGERweb loaders, layer registry + result-card framework with per-layer failure isolation, selected-boundary highlight, URL-hash permalinks.
- **Modules**: each layer registers `{id, group, label, overlay:{load, style}, query(point, seq), render(result)}`. Overlays lazy-load on first toggle and are cached; `query` runs a local point-in-polygon test against the cached boundaries (or nearest-N haversine for point layers).
- **Honesty rules**: external strings are sanitized or rendered via `textContent`; officeholder data is never guessed — where no verifiable roster source exists, cards link to the official body instead.

### Data sources (NYC)

| Source | Used for |
|---|---|
| [NYC Open Data](https://opendata.cityofnewyork.us) (Socrata) | Council, community & election districts, precincts/sectors, firehouses, library branches, school zones/districts, NTAs, ZIP (MODZCTA), community-board leadership |
| NYC Planning ArcGIS (`services5.arcgis.com/GfwWNkhOj9bNBqoJ`) | Election districts, FDNY battalions |
| NYSED ArcGIS (`services6.arcgis.com/EbVsqZ18sv1kVJ3k`) | School points (public / charter / private) |
| [U.S. Census TIGERweb](https://tigerweb.geo.census.gov) | U.S. House, NY Senate, NY Assembly boundaries; judicial/municipal county geometry |
| [unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators) | U.S. House roster (NY reps) |
| NY Open Legislation API · [Open States](https://openstates.org) (district offices) | NY Senate & Assembly roster + office addresses (weekly CI) |
| council.nyc.gov · nyc.gov precinct pages · schools.nyc.gov (CI scrapers) | City Council roster + district offices, NYPD precinct commanders, CEC members |
| [NYC Planning GeoSearch](https://geosearch.planninglabs.nyc) (Pelias, keyless, PAD-backed) | Address search + address pins |
| [USGS The National Map](https://www.usgs.gov/programs/national-geospatial-program/national-map) structures layer 38 | Post office locations (live bbox query; public domain) |
| NYS GIS Program Office elections service (`services6.arcgis.com/EbVsqZ18sv1kVJ3k`) | Early-voting sites (NYS ITS Geospatial Services / NYS & NYC Boards of Elections) |

## Repository layout

```
index.html                   the entire app (styles, engine, layer modules)
metro-worksheet.json          per-fork facts; regenerates the GENERATED regions
sw.js                         service worker (cache-first geometry, network-first rosters)
data/app/                     app-data files the page fetches (offline anchors + officeholder rosters)
WATCH.md                      NYC redistricting watch calendar (when to look; the runbook is what to do)
scripts/smoke_test.mjs        Playwright boot/behaviour smoke test (runs on every PR)
scripts/validate_index.py     static gate: layer ids + z-order rank, sw.js cache lists, anchor counts, roster floors
scripts/validate_sources.py   monthly source-freshness gate: dataset ids resolve, newer editions flagged, redistricting watch
scripts/build_embedded_boundaries.py  simplifies source GeoJSON into data/app/*.json (the 3 offline anchors)
scripts/*.py                  NYC scraper/builder pairs (state legislature, council, NYPD, CEC, congress)
.github/workflows/            per-PR smoke test · deploy · five weekly roster crons (each opens a PR for review) · monthly source validation (opens a tracking issue)
docs/METRO_EXPANSION_PLAYBOOK.md  pointer stub — the master (porting recipe + NYC worked example) lives in the CHI repo
docs/BUILD_PLAYBOOK_1.md      pointer stub — the master (engine contract + build log) lives in the CHI repo
docs/OPTIMIZATION_PLAYBOOK.md pointer stub — the master lives in the CHI repo
docs/REDISTRICTING_RUNBOOK.md pointer stub — the master (fleet-wide runbook) lives in the CHI repo
docs/MECHANIZATION_PLAYBOOK.md pointer stub — archived master lives in the CHI repo
```

> **Operator setup: complete.** The NYC PWA icons shipped in [#31](https://github.com/ThursdaysFamous/DistrictExplorer-NYC/pull/31); `data/app/borough-officials.json` (5 Borough Presidents + 5 District Attorneys) is populated and hand-verified — do **not** re-seed it, refresh it via `scripts/build_borough_officials.py` against `scripts/borough_officials_source.json`. CI configuration is in place: the API-key secrets (`NYSENATE_API_KEY`, `OPENSTATES_API_KEY`) plus the Socrata app token in `metro-worksheet.json` (a public throttling identifier, not a secret). The one remaining placeholder is `cec-members.json` (empty until the CEC scrape lands).

## Not for legal or official use

Boundary and roster data come from public sources that explicitly disclaim legal precision. Always confirm district assignments and officeholders with the relevant government office before relying on them for anything official.
