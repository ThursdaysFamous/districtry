# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry South Dakota: a single-file, dependency-light web app. Click a point in South Dakota
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/sd/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
eighth state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `sd/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own data service: **County** (`county`, all 66, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (the at-large district, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **South Dakota Senate** and **South Dakota House** (35 Senate districts and 37 House districts electing 70 representatives, TIGERweb's 2026 state legislative districts joined to the Legislature's own data service), the TIGERweb fabric drawn from mirrored tile archives — **City or Town** (`municipality`, 310 incorporated places), **School District** (147 unified districts) and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `sd/scripts/build_metro_outline.py --check` holds it to 66
INSIDE anchors, one per county, and 16 OUTSIDE anchors over the state line and offshore.

**SOUTH DAKOTA ELECTS ONE MEMBER OF THE U.S. HOUSE, AT LARGE**, so its congressional "map" is the
whole state. TIGERweb carries it on layer 0 (the 120th Congress) as one record, CD120 "00", named
"Congressional District (at Large)", and on layer 4 (the 119th) as the same record.
`sd/scripts/build_legislative_boundaries.py` still measures the two against each other until 3 January
2027 (intersection-over-union 1.0, measured 2026-11-12), and refuses on or after 3 January 2029, so a
person reads the apportionment after the 2030 census before anything is drawn. The U.S. House card names
the district by that record's own name rather than "District 0", which nobody writes.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, 35 Senate districts and 37 House features (33 districts electing two representatives each and the subdistricts 26A, 26B, 28A and 28B electing one each), 70 representatives in all.
Measured 2026-11-12 against TIGERweb's 2024 layers (5 and 6): 33 of the 35 Senate districts are identical, District 8 matches to the sixth decimal and District 7 differs by a sliver (intersection-over-union 0.99994); the House layer moves the same line. The newer vintage is drawn. The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage
rolls. **THE TWO CHAMBERS NEST**: every House feature (33 whole districts and the subdistricts 26A, 26B, 28A and 28B) lies wholly inside the Senate district of its own number, so both maps are simplified in one shared topology. `check_nesting` asks, with no tolerance,
that every Senate vertex is a House vertex, and `--check` runs it offline on the shipped files in CI; there
is no way to rebuild one chamber alone. Both are simplified with Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN DATA SERVICE** (`sdlegislature.gov/api/Sessions`, then
`/api/SessionMembers/Session/<id>`, `sd/scripts/build_sd_legislature_roster.py`). The script reads the
regular session with the latest start date on or before the day of the run, so members elected in
November are not shown before the session they are seated for; on 2026-11-12 that was the 2026 session,
listing 35 senators and 70 representatives, every seat. **THIRTY-THREE DISTRICTS ELECT TWO
REPRESENTATIVES AT LARGE AND DISTRICTS 26 AND 28 ARE EACH SPLIT INTO TWO ONE-MEMBER HOUSE DISTRICTS**
(26A and 26B, 28A and 28B), so the House roster is keyed by House district as TIGERweb names them and
every record carries `seats` and `members`: 70 representatives in 37 House districts. Every contact field
was empty on all 105 records, so the card links the member's page. Each record also has fields for the
member's home address, city and ZIP code, **and none of them is read**. robots.txt read 2026-11-12: no rule
matches `/api/`.

**MOST OF SOUTH DAKOTA IS IN NO CITY OR TOWN.** The **City or Town** layer is TIGERweb's incorporated places
(layer 4): 310 records, 157 cities and 153 towns, every one an active government, under 1% of the state's
land (1,438.5 of 196,345.1 km2, measured 2026-11-12). An empty card says the point is outside every city
and town and that the county is the local government there, with the civil township where one is
organized. No mayor or council member is named yet (gap `sd-municipal-officeholders`).

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 147 unified districts for South Dakota and nothing on its
elementary or secondary layers (measured 2026-11-12), so those two layers are not drawn. No school board
member is named yet (gap `sd-school-board-members`).

**NO COUNTY OFFICIAL IS NAMED YET**, and the card says so rather than leave a reader to assume the office
is empty. Each county is governed by an elected board of county commissioners and elects officers such
as an auditor, a treasurer, a register of deeds, a sheriff and a state's attorney. Recorded as gap
`sd-county-officials`.

**TRIBAL LAND IS NOT DRAWN YET.** The Census keeps nine reservations and seven trust lands in South Dakota
(`scripts/tribal_areas.py --report "South Dakota"`, 2026-11-12): the Cheyenne River (11,424.8 km2), Pine
Ridge (11,272.8 km2), Rosebud, Yankton, Crow Creek, Lower Brule and Flandreau reservations, the South
Dakota parts of the Standing Rock (69.2% of it) and Lake Traverse (92.9%) reservations, and the Rosebud
trust land (1,825.1 km2) among the trust lands. The state is recorded as not yet covered in
`data/tribal-government-join.json`.

**THE ZIP LAYER HIDES OUTSIDE SOUTH DAKOTA.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the seven officers South Dakota elects statewide as single officers
(the governor, lieutenant governor, attorney general, secretary of state, state treasurer, state auditor
and commissioner of school and public lands) and both U.S. senators, from
`sd/data/source/statewide-officials.source.json` through `scripts/build_statewide_officials.py`. The three
members of the Public Utilities Commission are elected statewide too and are not listed yet.

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

- Metro: South Dakota (`southdakota`) — https://districtry.com/sd/
- Geocoders: address Photon (South Dakota-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, South Dakota-bounded, serial >=1s queue)
- Ground truth: 44.36706,-100.34604 (South Dakota State Capitol, 500 East Capitol Avenue, Pierre, Hughes County) → county Hughes County; us-house Congressional District (at Large); sd-senate 24; sd-house 24. Negative point 46.05000,-100.10000 (Emmons County, North Dakota, north of the South Dakota line — outside South Dakota and inside permalink_gate, so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names North Dakota here (control: the South Dakota State Capitol returns South Dakota), none of the state's shipped boundary files contains it, and of every outline in the fleet only North Dakota's does (North Dakota goes live in the same change as South Dakota). South Dakota borders no water and no other country, and every one of its neighbours (North Dakota, Minnesota, Iowa, Nebraska, Wyoming and Montana) is live once this change lands, so no point this app's gate reaches lies outside every instance: the point stays where it is, as Illinois's sits in Indiana's waters, and a selection the app makes from its own link never leaves for another app.).
- Layers: 10 registered (political 3, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.SouthDakotaExplorer`.
- Scheduled workflows: `update-sd-congress-roster.yml` (Wed 23:17 UTC); `update-sd-legislature-roster.yml` (Thu 23:17 UTC); `sd-validate-sources.yml` (2nd of month 23:17 UTC).
- Source registry: `sd/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/sd/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/sd/ node sd/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 sd/scripts/validate_index.py sd/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 sd/scripts/build_metro_outline.py --check

# Nesting gate (every Senate vertex is a vertex of its House districts, offline):
python3 sd/scripts/build_legislative_boundaries.py --check

# Generated-region gate: per-instance facts live ONCE in sd/metro-worksheet.json;
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
which vendors Leaflet into `sd/scripts/vendor/leaflet/` (gitignored);
`sd/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything South Dakota-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`sd/scripts/build_metro_outline.py`), `state-counties.json` (the counties, `sd/scripts/build_state_counties.py`),
and `congress-districts.json`, `sd-senate-districts.json` and `sd-house-districts.json`
(`sd/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m under an 8 m ceiling, the two chambers in one topology, refused unless the 2,000-random-point agreement gate, the 8 m fidelity ceiling and the exact nesting check all pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance sd`; 40,766 populated blocks holding all 886,667 people the 2020 census counted in South Dakota). The Senate map is held to that count; its worst districts are 26 and 27, both on reservation land, at -7.813% and -5.62% of the raw-census ideal, and why the plan sits there is not on record. The at-large congressional district has no number to key and no ideal but the state, and the House is not held, because one ideal describes neither a two-member district nor a one-member half. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 376 ZIP codes). Rosters:
`congress-roster.json` (`sd/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`sd-senate-members.json` and `sd-house-members.json` (`sd/scripts/build_sd_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`sd/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
both chamber files to one record per seat, and each multi-member district to the number of members it elects.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `sd/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
