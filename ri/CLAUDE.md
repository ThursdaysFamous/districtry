# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Rhode Island: a single-file, dependency-light web app. Click a point in Rhode Island
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/ri/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
seventh state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `ri/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the General Assembly's own member list: **County** (`county`, all five, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (2 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Rhode Island Senate** and **Rhode Island House** (38 and 75 districts, TIGERweb's 2026 state legislative districts joined to the General Assembly's own member list), the TIGERweb fabric drawn from mirrored tile archives — **City or Town** (`municipality`, the 39 cities and towns), **School District (Unified)**, **(Elementary)** and **(Secondary)** and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `ri/scripts/build_metro_outline.py --check` holds it to 5
INSIDE anchors, one per county, and 12 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN RHODE ISLAND IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 2 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `ri/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, 38 Senate and 75 House districts.
Measured 2026-11-12, every district in both chambers is the same as in TIGERweb's 2024 layers (5 and 6), intersection-over-union 1.0. The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage
rolls, and there is no nesting rule between the chambers (a House district's largest share
inside one Senate district is as low as 0.32 of its area), so each map is simplified on its own,
Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE GENERAL ASSEMBLY'S OWN MEMBER LIST** (`ri/scripts/build_ri_legislature_roster.py`).
The Senate's and House's member pages fill themselves in after they open, from one SharePoint list,
"legislationInformation", which each page asks for with a SOAP `GetListItems` call to
`rilegislature.gov/_vti_bin/Lists.asmx`; the script sends the same request the pages send — the
read-the-page's-own-feed rule of 2026-10-06. Measured 2026-11-12: 124 rows, 112 marked active, 38
senators (every seat) and 74 representatives; House District 31 had no active row, so its record names
nobody. Each row gives the name, party, an e-mail address at rilegislature.gov (all 112), a telephone,
which it labels with nothing (99 of 112), and the member's biography page. **EACH ROW ALSO CARRIES THE
MEMBER'S TOWN, AND IT IS NEVER READ.** robots.txt read 2026-11-12: no rule matches `/_vti_bin/`.

**EVERY PART OF RHODE ISLAND'S LAND IS IN ONE OF ITS 39 CITIES AND TOWNS**, and the Census files each as a
county subdivision, so the **City or Town** layer is TIGERweb's county subdivisions (layer 1). Measured
2026-11-12 across the 40 records: 31 towns, 8 cities and one record of about 331 km2 of coastal water in
Newport County, filed as "County subdivisions not defined", which the card answers as water rather than
naming a place that does not exist. No mayor, council or town council member is named yet (gap
`ri-municipal-officeholders`).

**THREE SCHOOL LAYERS, AND ONE PLACEHOLDER.** Measured 2026-11-12: 30 unified districts and five
elementary districts, which between them cover the state's land, and one secondary district
(Foster-Glocester), which runs the higher grades over two elementary districts' ground. **ONE UNIFIED
RECORD IS NOT A DISTRICT**: the Census's "School District Not Defined" (GEOID 4499997) files 331 km2 of
coastal water and no land, and the card answers it as no school district. No school committee member is
named yet (gap `ri-school-board-members`).

**RHODE ISLAND HAS HAD NO COUNTY GOVERNMENT SINCE 1842** and nobody is elected to a county office, so the
County card says the city or town is the local government and the City or Town card names it. There is
no county-officials gap, because there is no county official to name.

**TRIBAL LAND IS NOT DRAWN YET.** The Census keeps one reservation in Rhode Island, the Narragansett
Reservation (8.331 km2), measured 2026-11-12 with `scripts/tribal_areas.py --report "Rhode Island"`. The
state is recorded as not yet covered in `data/tribal-government-join.json`.

**THE ZIP LAYER HIDES OUTSIDE RHODE ISLAND.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The five TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the five officers Rhode Island elects statewide (the governor,
lieutenant governor, secretary of state, attorney general and general treasurer) and both U.S. senators,
from `ri/data/source/statewide-officials.source.json` through `scripts/build_statewide_officials.py`.

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

- Metro: Rhode Island (`rhodeisland`) — https://districtry.com/ri/
- Geocoders: address Photon (Rhode Island-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Rhode Island-bounded, serial >=1s queue)
- Ground truth: 41.83087,-71.41492 (Rhode Island State House, 82 Smith Street, Providence, Providence County) → county Providence County; us-house 1; ri-senate 1; ri-house 1. Negative point 41.02000,-71.30000 (the Atlantic Ocean southeast of Block Island — outside Rhode Island and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here, because it is open water (control: the Rhode Island State House returns Rhode Island), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any outline in the change that opens the last thirteen states. IT IS OPEN WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 12 registered (political 3, safety 2, schools 3, geography 4); `registerLayer(` floor 10. Debug namespace `window.RhodeIslandExplorer`.
- Scheduled workflows: `update-ri-congress-roster.yml` (Wed 23:03 UTC); `update-ri-legislature-roster.yml` (Thu 23:03 UTC); `ri-validate-sources.yml` (2nd of month 23:03 UTC).
- Source registry: `ri/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ri/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ri/ node ri/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ri/scripts/validate_index.py ri/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 ri/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in ri/metro-worksheet.json;
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
which vendors Leaflet into `ri/scripts/vendor/leaflet/` (gitignored);
`ri/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Rhode Island-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the U.S. House and chamber layers use the fenced factory helper `registerIlgaChamber` (which renders a vacancy record as a vacant seat with its reason and source), the County, municipality and school cards are bespoke `registerLayer` blocks, the ZIP layer `registerPolygonLayer`, and the three nearest-N layers `registerNearestPointLayer`. Two invariants pervade the
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
`ri/scripts/build_metro_outline.py`), `state-counties.json` (the counties, `ri/scripts/build_state_counties.py`),
and `congress-districts.json`, `ri-senate-districts.json` and `ri-house-districts.json`
(`ri/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m under an 8 m ceiling, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance ri`; 21,382 populated blocks holding all 1,097,379 people the 2020 census counted in Rhode Island). All three maps are held to that count; the worst districts are -0.111% (congress), +8.005% (Senate) and +4.882% (House) of the raw-census ideal, and why the Senate plan sits there is not on record. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 81 ZIP codes). Rosters:
`congress-roster.json` (`ri/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`ri-senate-members.json` and `ri-house-members.json` (`ri/scripts/build_ri_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`ri/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `ri/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
