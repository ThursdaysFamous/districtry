# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry California: a single-file, dependency-light web app. Click a point in California (or search an address) and it reports every civic district containing that point and who represents you there. Across all 58 counties it answers the county, the city or town, the three kinds of school district, the ZIP code, the nearest post offices, and the U.S. House, California Senate and California Assembly districts with the member who holds each seat; inside San Francisco it also answers the supervisor district, precinct and election results, BART director, police district, neighbourhood, attendance area and the city's facilities. Deployed as a static site at `districtry.com/ca/`. It answered for San Francisco alone until 2026-11-11, when it grew to the whole state and kept every San Francisco layer; the worksheet's `this_metro` stays `sf`. Illinois (`il/`) is the reference implementation.

**Two coverage tests, read from two shipped outlines.** The San Francisco layers declare `coverage: inSanFrancisco` (`san-francisco-county-outline.json`, the union of the supervisor districts with Treasure Island) and hide outside the city and county; the statewide layers that need one declare `coverage: inCalifornia` (`ca-state-outline.json`, the 58 counties dissolved). The wash draws the state as its region and San Francisco as its full coverage, so the key's middle band reads "Statewide layers only". No county supervisor, mayor, council member or school board member is named outside San Francisco yet; the four gap records (`ca-county-officials`, `ca-municipal-officeholders`, `ca-school-board-members`, `ca-tribal-government`) say why. The fourth is now about the tribal councils: the land itself is drawn (below).

**TRIBAL GOVERNMENT DRAWS THE LAND OF 98 NATIONS AND NAMES THE COUNCILS OF 49** (`tribal-areas.json`,
since 2026-11-12). The Census keeps 103 reservations and rancherias and 47 off-reservation trust
lands in California, and all 150 pieces are drawn, each joined in `data/tribal-government-join.json`
to the government the Bureau of Indian Affairs lists for it. They lie in 34 of the 58 counties and
none in San Francisco, so the layer declares no coverage test and the city's own layers are
untouched. Five pieces cross the state line and are drawn whole: the Colorado River (16.2% in
California), Fort Mojave (18.5%), Fort Yuma (95.4%) and Timbi-Sha Shoshone (21.9%) reservations
and the Washoe Ranches Trust Land (0.3%). Two nations are seated outside the state, the Colorado
River Indian Tribes in Parker, Arizona, and the Washoe Tribe in Gardnerville, Nevada. **SEVEN
CENSUS CODES ARE THE PIT RIVER TRIBE'S AND SIX OF THEIR NAMES DO NOT SAY SO**: the Big Bend, Likely,
Lookout, Montgomery Creek, Roaring Creek and XL Ranch rancherias and the Pit River Trust Land are
joined to the tribe on its own history page (pitrivertribe.gov/tribal-history/, read 2026-11-12),
which names its land as including those rancherias. **THE CAPITAN GRANDE RESERVATION IS SHARED**:
the Bureau lists the Capitan Grande Band itself with no city, state or site and lists its two
groups, Barona and Viejas, each with a seat, so the reservation is entered under `governments` and
its card names both, with Barona's own history page as the record that the reservation came before
the Barona Ranch. The Bureau lists neither a city nor a state for the Round Valley Indian Tribes and
the Yocha Dehe Wintun Nation, and under Adam's choice of 2026-11-12 for Nevada each is seated at the
town its own site gives, Covelo and Brooks (`seatFromNation`), with a line on the card saying where
the town came from; only the town is carried. Yocha Dehe's own site could not be read from this
project's sandbox, so its card keeps the Bureau's address as the nation's site. The Greenville
Rancheria the Bureau lists with a state and no city, so its card gives the state alone. The Bureau
lists no website for 28 of the 98 nations, and the addresses it lists for ten more no longer reach
the nation (no DNS record, a parked domain, a gambling site, an HTTP 500, or a casino or resort page
that does not give the government), so on Adam's ruling of 2026-11-13 those cards link no site, or,
for the Pit River Tribe, the tribe's own site at pitrivertribe.gov (`websiteWithdrawn`). The Census draws tribal districts on one piece, the Yurok
Reservation (Orick, Pecwan, Requa and Weitchpec), named on its card. The file is 1.12 MB (258 KB
gzipped) at the Census's own detail, smaller than Arizona's simplified file, so it is not
simplified. Since 2026-11-13 the cards name the council of 51 of the 98 nations, read nation by nation from
each nation's own page into `tribal-councils.json` (a separate file the loader merges onto the land,
so a failed read leaves the card naming the nation and nobody on its council) and re-read weekly by
`update-tribal-councils.yml`. Every other card says why it names nobody, in words measured on that
day and kept in `ROSTER_BLOCKED` in `scripts/build_tribal_areas.py`: a site that refused this
project or showed a check only a person can pass, a page naming only part of the council or
none of it, or no site of the nation's own. A council is carried only where its page names or lists as vacant all of its seats, or
all but one (Adam, 2026-11-13), and then the card's note says which seat the page leaves out. Two are: Paskenta's page lists its
secretary's seat as vacant, and the Washoe Tribe's names one of its two Off-Reservation
representatives. Recorded in gap
`ca-tribal-government`.

**There is no build step, no framework, and no server-side code.** The entire app — styles, core, and all layer modules — lives inline in `index.html`. `sw.js` is the service worker; `data/app/*.json` are runtime-fetched data files. Everything else is data pipeline, scrapers, or CI.

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: California (`sf`) — https://districtry.com/ca/
- Geocoders: address Photon (California-bounded type-ahead); unbounded Photon (whole-coverage, sibling-metro lookup); POI Nominatim (office-address pin lookup, serial >=1s queue)
- Ground truth: 37.77927,-122.41924 (SF City Hall (Civic Center)) → supervisor-district 5; neighborhood Tenderloin; police-district NORTHERN. Negative point 32.40000,-115.60000 (The Mexicali Valley in Mexico, about 15 km south of the border at Calexico — outside California and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-11 against TIGERweb's state layer (controls: San Francisco City Hall returns California, and Mexicali, Baja California, returns no state). IT IS IN ANOTHER COUNTRY, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 23 registered (elections 1, political 8, safety 3, schools 5, geography 6); `registerLayer(` floor 12. Debug namespace `window.SFExplorer`.
- Scheduled workflows: `ca-update-election-results.yml` (daily 14:10 UTC); `ca-update-congress-roster.yml` (Mon 13:00 UTC); `ca-update-legislature-roster.yml` (Tue 13:00 UTC); `ca-update-sf-supervisor-roster.yml` (Wed 13:00 UTC); `ca-validate-sources.yml` (1st of month 14:00 UTC).
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

`validate_sources.py` is the **freshness** gate (complements the merge gate above). It catches the failure mode the roster scrapers can't: a publisher silently superseding a dataset the app hardcodes. DataSF (Socrata) datasets can be re-published under a **new id** each year — SFUSD *School Attendance Areas* ship a fresh `…(YYYY-YYYY)` edition every school year — so the old id keeps returning stale data with no error. The script carries a manifest of every live DataSF dataset id, the pre-built boundary files' provenance URLs, and the live endpoints the app depends on, and checks: (1) the manifest still matches index.html (drift guard), (2) each Socrata id still resolves and keeps its expected name, searching the portal catalog for a **newer-year edition** of the year-versioned ones, (3) the pre-built boundary sources (three DataSF anchors, the three statewide TIGERweb CA chambers and the TIGERweb counties) are reachable and their built `data/app/` files present, (4) the live Census endpoints (ZCTAs, incorporated places, school districts) and the USGS post-office layer resolve. Note the SF-specific catalog quirk: DataSF is **not** indexed by the federated `api.us.socrata.com`, so newer-edition search hits the portal-local `data.sfgov.org/api/catalog/v1` (no `domains`/`only` filters). It **never edits the app** — swapping a dataset id is schema-sensitive — it exits non-zero only on hard FAILs and reports a newer edition as a WARN. `.github/workflows/validate-sources.yml` runs it monthly and opens/updates a single tracking issue on any WARN/FAIL (the job stays green; the issue is the signal). When a dataset id is swapped in index.html, update the manifest in `validate_sources.py` to match.

## Architecture: stable core + pluggable layer modules

All inside `index.html`, wrapped in one IIFE. The full contract and per-thread build log live in `docs/BUILD_PLAYBOOK_1.md`; `docs/OPTIMIZATION_PLAYBOOK.md` holds measured optimization tasks. `docs/METRO_EXPANSION_PLAYBOOK.md` is the recipe for porting the app to a new metro (Chicago is the reference implementation; each metro is its own fork), with the completed NYC port's build record archived at `docs/archive/METRO_EXPANSION_NYC.md` (fork: `github.com/ThursdaysFamous/DistrictExplorer-NYC`).

**Core** provides: the Leaflet map, click-to-select + debounced SF-bounded Photon geocoder, a global `state` object `{selectedPoint, sequence, layersOn, ...}`, the layer registry + result-card framework, selected-boundary highlight, and URL-hash permalinks (`#point=lat,lng&layers=supervisor-district,congress`). A small namespace is exposed as `window.SFExplorer` for debugging.

**Shared utilities** (reuse these; don't reinvent):
- `sanitize(str)` / render via `textContent` — all external strings must go through one of these. Injecting scraped or API text as HTML is treated as a real security bug here.
- `pointInGeometry(pt, geometry)` — the point-in-polygon test every polygon layer's `query` uses.
- `fetchJSONWithRetry(url, opts, retries)` — the standard data-fetch path (retry + failure isolation).
- `haversineMiles(...)` — for the nearest-N layers, which use straight-line proximity instead of point-in-polygon (police/fire stations via the `registerNearestPointLayer` factory; `school-site` as a bespoke block).

**A layer module** is registered via `registerLayer({ id, group, label, overlay: {load, style}, query(point, seq), render(result) })`. `group` is one of `political | safety | schools | geography`. Overlays lazy-load their boundaries on first toggle and are cached; `query` runs locally against the cached geometry. Families of similar layers are built by factory helpers (`registerPolygonLayer`, `registerSchoolZone`, `registerCpsNetwork`, `registerIlgaChamber`, `registerNearestPointLayer`) — follow the existing factory when adding a sibling. The factories derive each layer's hover-popup identity (`hoverName`) from the same properties its card reads, so the two surfaces can't disagree; a bespoke `registerLayer` block declares `hoverName(feature)` explicitly. Optional contract field `pointOfInterest(result) => {label, address} | null` drops a geocoded map pin (used by the school-zone layers). Optional contract field `coverage(point) => boolean | Promise<boolean>` declares where a layer's data applies (location relevance): outside its coverage the layer *hides* — toggle block, card, map overlay, hover-snapshot row, relationship outlines, and query all suppressed — without touching `state.layersOn`, so `layers=` permalinks survive and the layer reappears when a selected point re-enters coverage; a throwing coverage test fails open (the layer runs as if undeclared). Until 2026-11-11 no layer here declared `coverage`, because the app's whole ground was one consolidated city-county; since the app grew to the whole state the San Francisco layers declare `inSanFrancisco` and the ZIP layer `inCalifornia` (above). One layer uses the `subOf` sub-layer pattern: `election-precinct` under `supervisor-district` (mirroring the reference's ward-precinct dance — toggling the child auto-enables the parent as outline-only and fills it with precinct polygons). SF **does** use the engine's `makeSocrataPointLoader` (point datasets whose coordinates live only in properties: fire-station `nc68-ngbr`, library `fhhu-wqa7`, school-site `7e7j-59qk`) and `loadArcGISGeoJSON` (the `bart-director` geometry, from BART's own ArcGIS org); `loadArcGISPaged` stays for cross-fork parity but is unused here — the Post Office layer's USGS National Map service is fetched directly by URL. See `docs/METRO_EXPANSION_PLAYBOOK.md` (master in the Chicago repo).

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

- **Boundary geometry** (`supervisor-districts.json`, `sf-neighborhoods.json`, `police-districts.json` plus the three statewide legislative chambers `{congress,ca-senate,ca-assembly}-districts.json`, the 58 counties `state-counties.json`, the state outline and San Francisco's outline) — the first three mapshaper-simplified from the full-precision GeoJSON in `data/` via `scripts/build_embedded_boundaries.py`; the chambers pre-built from Census TIGERweb (`STATE='06'`; the congressional map is the 119th Congress's, layer 4, until 2027-01-03 per `WATCH.md`) via `scripts/build_legislative_boundaries.py`, the counties by `scripts/build_state_counties.py`, the state outline by `scripts/build_state_outline.py` and San Francisco's by `scripts/build_sf_county_outline.py` (rare operator steps). Cities and towns, the three school-district layers and ZIP codes ship only as tile archives mirrored from TIGERweb by the root `scripts/mirror_tiger_tiles.py`. Service worker serves these **cache-first** (boundaries change ~once a decade).
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
