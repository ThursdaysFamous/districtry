# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Oregon: a single-file, dependency-light web app. Click a point in Oregon
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/or/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
fifth state of batch 3 of the state-level launch Adam asked for on 2026-11-10 (Massachusetts, Colorado, Maryland, Alabama, Oregon, Connecticut, Utah, Kansas),
in his chosen order: built dark, with the deploy excluding `or/**`, and opened with the rest of its
batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own data: **County** (`county`, all 36, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (6 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Oregon Senate** and **Oregon House** (30 and 60 districts, TIGERweb's 2026 state legislative districts joined to the Legislature's own data service), the TIGERweb fabric drawn from mirrored tile archives — **City or Town** (`municipality`, 241 incorporated places), **School District (Unified)**, **(Elementary)** and **(Secondary)** and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `or/scripts/build_metro_outline.py --check` holds it to 36
INSIDE anchors, one per county, and 13 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN OREGON IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 6 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `or/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2).**
Measured 2026-11-12 against the 2024 vintage (layers 5 and 6): every district in both chambers identical (intersection-over-union 1.0). The builder refuses if a layer's name changes, since TIGERweb renumbers its
layers when a vintage rolls, and the two chambers nest, so both are simplified in one shared topology (described below).

**EVERY SENATE DISTRICT IS TWO HOUSE DISTRICTS.** Measured 2026-11-12 on TIGERweb's own polygons,
Senate District N is exactly House Districts 2N-1 and 2N, so the builder simplifies both maps in
one shared topology (Douglas-Peucker at 5 m under an 8 m ceiling), the two layers' lines cannot
part, and its `--check` holds the nesting offline in CI.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN DATA SERVICE** (`api.oregonlegislature.gov`,
the OData service behind the Oregon Legislative Information System,
`or/scripts/build_or_legislature_roster.py`): each member's name, party, Capitol room and telephone,
e-mail address at oregonlegislature.gov and page. The session read is the regular session with the
latest start date on or before the day of the run, so members elected in November are not shown
before they are sworn in; on 2026-11-12 that was 2026R1, which listed every seat of both chambers
and names the members appointed since the 2025 session. The records carry no home address.
robots.txt answered 404 on 2026-11-12, which RFC 9309 reads as no restriction.

**MOST OF OREGON IS IN NO CITY.** The **City or Town** layer is TIGERweb's incorporated places
(layer 4): 241 records, 231 cities, 9 towns and the city of Greenhorn, which the Census records as an
inactive government, about 1% of the state's land (measured 2026-11-12). An empty card says the
point is outside every city and that the county is the local government there.

**THREE SCHOOL LAYERS, AND ONE PLACEHOLDER.** Measured 2026-11-12 for STATE='41': 188 unified
districts, 9 elementary districts (eight running kindergarten to grade 8; the Census records the
ninth, Juntura, as running every grade) and one secondary district, the Harney County Union High
School District, which covers part of the elementary districts' ground, so a reader there is in two
districts at once. **ONE UNIFIED RECORD IS NOT A DISTRICT**: the Census's "School District Not
Defined" (GEOID 4199997) files about 44 km2 of coastal water, and the card answers it as no school
district. No school board member is named yet (gap `or-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Each county is governed by an elected board of commissioners, or by
a board or council its home-rule charter sets up, and most elect officers such as a sheriff, a
district attorney and a clerk. Recorded as gaps `or-county-officials` and
`or-municipal-officeholders`.

**TRIBAL LAND IS NOT DRAWN YET.** The Census keeps ten reservations in Oregon (the largest Warm
Springs, about 2,628 km2, and Umatilla, about 701 km2; the Oregon part of the Fort McDermitt
Indian Reservation is 52% of it) and eight off-reservation trust lands, Celilo Village among them,
measured 2026-11-12 with `scripts/tribal_areas.py --report Oregon`. The state is recorded as not
yet covered in `data/tribal-government-join.json`.

**THE ZIP LAYER HIDES OUTSIDE OREGON.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The five TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the five officers Oregon elects statewide (the governor,
secretary of state, attorney general, state treasurer and commissioner of the Bureau of Labor and
Industries) and both U.S. senators, from `or/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`. Oregon has no lieutenant governor; the secretary of state
is first in line to succeed the governor. The Supreme Court and the Court of Appeals are elected
statewide too and are not listed yet.

**There is no build step, no framework, and no server-side code.** The app — styles, engine,
and layer modules — lives inline in `index.html`. `sw.js` is the service worker;
`data/app/*.json` are runtime-fetched data files; `data/state/` carries the bootstrap state
config (`build_congress_roster.py` reads its FIPS/USPS/seat count — it ships in the repo and is
excluded from the Pages deploy). `sources.html` carries the generated per-layer provenance
matrix and `faq.html` the common questions; both compose from the same shared engine blocks as
every other instance via `scripts/compose_app.py`.

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: Oregon (`oregon`) — https://districtry.com/or/
- Geocoders: address Photon (Oregon-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Oregon-bounded, serial >=1s queue)
- Ground truth: 44.93809,-123.03013 (Oregon State Capitol, 900 Court Street NE, Salem, Marion County) → county Marion County; us-house 6; or-senate 11; or-house 21. Negative point 44.95000,-124.40000 (The Pacific about 30 km off Lincoln City — outside Oregon and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here (control: the State Capitol returns Oregon), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any of the other batch-3 states' outlines. IT IS OPEN WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 12 registered (political 3, safety 2, schools 3, geography 4); `registerLayer(` floor 10. Debug namespace `window.OregonExplorer`.
- Scheduled workflows: `update-or-congress-roster.yml` (Mon 22:55 UTC); `update-or-legislature-roster.yml` (Tue 22:55 UTC); `or-validate-sources.yml` (1st of month 23:37 UTC).
- Source registry: `or/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/or/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/or/ node or/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 or/scripts/validate_index.py or/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 or/scripts/build_metro_outline.py --check

# Nesting gate (every Senate vertex is a vertex of its House districts, offline):
python3 or/scripts/build_legislative_boundaries.py --check

# Generated-region gate: per-instance facts live ONCE in or/metro-worksheet.json;
# GENERATED regions are emitted from it. NEVER hand-edit a GENERATED region:
pip install -c scripts/requirements.txt jsonschema
python3 scripts/generate_metro_files.py            # regenerate in place (all instances)
python3 scripts/generate_metro_files.py --check    # the CI drift gate

# Engine parity: the ENGINE fences are composed from the repo-root engine/ —
# edit a block THERE and recompose, never inside an instance file:
python3 scripts/compose_app.py            # splice engine/ into every instance
python3 scripts/compose_app.py --check    # the CI drift gate
```

Run the full battery through `.claude/skills/steward/SKILL.md`, never through a command list you
extract yourself — the repo root's CLAUDE.md records four different sessions getting that wrong
four different ways, one of which hung for five hours.

**Sandboxed environments (Claude Code web):** the headless browser cannot reach the Leaflet
CDN. The repo root's `.claude/settings.json` SessionStart hook runs `scripts/vendor_leaflet.sh`,
which vendors Leaflet into `or/scripts/vendor/leaflet/` (gitignored);
`or/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Oregon-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the three chamber layers use the fenced factory helper `registerIlgaChamber` (which renders a vacancy record as a vacant seat with its reason and source), the County, municipality and three school cards are bespoke `registerLayer` blocks, and the three nearest-N layers `registerNearestPointLayer`. Two invariants pervade the
code: the **stale-async guard** (`if (seq !== state.sequence) return;` after every await) and
**per-layer failure isolation** (a layer's failure shows a Retry inside its own card, never breaks
the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards say who is not named instead of inventing a name. The chamber cards
degrade to the district + the chamber's own member list on a roster miss, and a vacant or unlisted
seat says so with the day it was read; the County, municipality and school district cards carry no
roster and **say so on the card**. External strings always render through
`sanitize()`/`textContent`. Roster refreshes always land as PRs for review — never as direct commits
to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`or/scripts/build_metro_outline.py`), `state-counties.json` (`or/scripts/build_state_counties.py`),
and `congress-districts.json`, `or-senate-districts.json` and `or-house-districts.json`
(`or/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, the two chambers in one topology, refused unless the 2,000-random-point agreement gate, the 8 m fidelity ceiling and the exact nesting check all pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance or`; 79,081 populated
blocks holding all 4,237,256 people the 2020 census counted in Oregon). All three maps are held to that count; the congressional map sits within 0.001% of its ideal, and the worst legislative districts are -0.950% (Senate) and +0.984% (House). The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 427 ZIP codes). Rosters:
`congress-roster.json` (`or/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`or-senate-members.json` and `or-house-members.json` (`or/scripts/build_or_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs — and `statewide-officials.json`
(`scripts/build_statewide_officials.py`, from `or/data/source/statewide-officials.source.json`).
`scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `or/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
