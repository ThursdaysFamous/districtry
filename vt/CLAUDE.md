# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Vermont: a single-file, dependency-light web app. Click a point in Vermont
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/vt/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
eleventh state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `vt/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own member lists: **County** (`county`, all 14, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (the at-large district, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Vermont Senate** and **Vermont House** (16 named districts electing 30 senators and 109 named districts electing 150 representatives, TIGERweb's 2026 state legislative districts joined to the Legislature's own member lists), the TIGERweb fabric drawn from mirrored tile archives — **Town or City** (`municipality`, 256 county subdivisions), **School District (Unified)**, **(Elementary)** and **(Secondary)** and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `vt/scripts/build_metro_outline.py --check` holds it to 14
INSIDE anchors, one per county, and 15 OUTSIDE anchors over the state line and offshore.

**VERMONT ELECTS ONE MEMBER OF THE U.S. HOUSE, AT LARGE**, so its congressional "map" is the
whole state. TIGERweb carries it on layer 0 (the 120th Congress) as one record, CD120 "00", named
"Congressional District (at Large)", and on layer 4 (the 119th) as the same record.
`vt/scripts/build_legislative_boundaries.py` still measures the two against each other until 3 January
2027 (intersection-over-union 1.0, measured 2026-11-12), and refuses on or after 3 January 2029, so a
person reads the apportionment after the 2030 census before anything is drawn. The U.S. House card names
the district by that record's own name rather than "District 0", which nobody writes.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, 16 Senate districts electing 30 senators and 109 House districts electing 150 representatives.
Measured 2026-11-12, every district in both chambers is the same as in TIGERweb's 2024 layers (5 and 6), intersection-over-union 1.0. The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage
rolls, and there is no nesting rule between the chambers (a House district's largest share
inside one Senate district is as low as 0.37 of its area), so each map is simplified on its own,
Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN MEMBER LISTS** (`legislature.vermont.gov/people/all/<year>/Senate`
and `/House`, which fill their tables from `/people/loadAll/<year>/...`, the address the script reads;
`vt/scripts/build_vt_legislature_roster.py`). **EVERY DISTRICT IS NAMED AND MOST ELECT MORE THAN ONE
MEMBER**: 30 senators from 16 districts electing one to three each, and 150 representatives from 109
districts electing one or two (68 and 41). Both rosters are keyed by the district's name as TIGERweb spells
it (`BASENAME`: "Chittenden Central", "Addison-1") with `seats` and `members`; three Senate districts the
Legislature spells with a hyphen are mapped by `SENATE_SPELLING`, and any other unknown name stops the
build. Measured 2026-11-12: the 2026 lists carried 32 Senate and 158 House rows, of which 30 and 150 had no
termination reason, every seat filled. The party ships as printed, fusion labels included
("Democrat/Progressive"). **NO E-MAIL ADDRESS OR TELEPHONE IS READ FROM THE LIST**, because on 2026-11-12
the member page for one member printed an address and a telephone that matched no field of that member's
row; the card links the member's page, where the Legislature prints them. Each row also carries the
member's home, work and mailing addresses, town and ZIP codes, **and none of them is read**. robots.txt read
2026-11-12: no rule matches `/people/`, and its `Crawl-delay: 30` is honoured between the two fetches.

**EVERY PART OF VERMONT'S LAND IS IN A TOWN, A CITY, A GORE OR A GRANT**, and the Census files each as a
county subdivision, so the **Town or City** layer is TIGERweb's county subdivisions (layer 1). Measured
2026-11-12 across the 256 records: 237 towns with governments, 10 cities, five towns with no government of
their own (Averill, Ferdinand, Glastenbury, Lewis and Somerset), three gores and one grant; the unorganized
ones are administered by a supervisor the governor appoints, and their cards say so. **TWENTY-NINE
INCORPORATED VILLAGES HAVE GOVERNMENTS OF THEIR OWN INSIDE THEIR TOWNS, AND THE MAP DOES NOT DRAW THEM.** No
select board, council or mayor is named yet (gap `vt-municipal-officeholders`).

**THREE SCHOOL LAYERS.** Measured 2026-11-12: 64 unified districts and 56 elementary districts, which
between them cover the state's land, and 11 secondary districts, which run the higher grades over part of
the elementary districts' ground, so a reader there is in two districts at once. No school board member is
named yet (gap `vt-school-board-members`).

**VERMONT'S COUNTIES HAVE NO COUNTY BOARD.** Each elects officers such as a sheriff, a state's attorney, a
probate judge and two assistant judges, and the town or city is the local government. The card names none
of them yet and says so (gap `vt-county-officials`).

**VERMONT HAS NO TRIBAL LAND TO DRAW.** Measured 2026-11-12 with `scripts/tribal_areas.py --report
Vermont`: the three drawn classes keep no feature inside the state, with Vermont resolving to state code 50
as the control. Recorded as covered in `data/tribal-government-join.json`.

**THE ZIP LAYER HIDES OUTSIDE VERMONT.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The five TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the six officers Vermont elects statewide (the governor,
lieutenant governor, secretary of state, attorney general, state treasurer and auditor of accounts) and
both U.S. senators, from `vt/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`.

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

- Metro: Vermont (`vermont`) — https://districtry.com/vt/
- Geocoders: address Photon (Vermont-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Vermont-bounded, serial >=1s queue)
- Ground truth: 44.26216,-72.58085 (Vermont State House, 115 State Street, Montpelier, Washington County) → county Washington County; us-house Congressional District (at Large); vt-senate Washington; vt-house Washington-4. Negative point 45.15000,-72.55000 (Quebec, Canada, north of the Vermont line — outside Vermont and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here, because it is in Canada (control: the Vermont State House returns Vermont), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any outline in the change that opens the last thirteen states. IT IS IN CANADA, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 12 registered (political 3, safety 2, schools 3, geography 4); `registerLayer(` floor 10. Debug namespace `window.VermontExplorer`.
- Scheduled workflows: `update-vt-congress-roster.yml` (Wed 23:43 UTC); `update-vt-legislature-roster.yml` (Thu 23:43 UTC); `vt-validate-sources.yml` (2nd of month 23:43 UTC).
- Source registry: `vt/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/vt/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/vt/ node vt/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 vt/scripts/validate_index.py vt/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 vt/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in vt/metro-worksheet.json;
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
which vendors Leaflet into `vt/scripts/vendor/leaflet/` (gitignored);
`vt/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Vermont-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the U.S. House and chamber layers use the fenced factory helper `registerIlgaChamber` (which renders a vacancy record as a vacant seat with its reason and source, and a district electing several members as every member it elects), the County, municipality and school cards are bespoke `registerLayer` blocks, the ZIP layer `registerPolygonLayer`, and the three nearest-N layers `registerNearestPointLayer`. Two invariants pervade the
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
`vt/scripts/build_metro_outline.py`), `state-counties.json` (the counties, `vt/scripts/build_state_counties.py`),
and `congress-districts.json`, `vt-senate-districts.json` and `vt-house-districts.json`
(`vt/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m under an 8 m ceiling, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance vt`; 17,976 populated blocks holding all 643,077 people the 2020 census counted in Vermont). No district map is held to that count: the at-large congressional district has no number to key, and both chambers' districts are named and elect one to three members, so one ideal describes none of them. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 263 ZIP codes). Rosters:
`congress-roster.json` (`vt/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`vt-senate-members.json` and `vt-house-members.json` (`vt/scripts/build_vt_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`vt/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
both chamber files to one record per seat, and each multi-member district to the number of members it elects.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `vt/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
