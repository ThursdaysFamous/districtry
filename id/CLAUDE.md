# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Idaho: a single-file, dependency-light web app. Click a point in Idaho
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/id/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
third state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `id/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own membership pages: **County** (`county`, all 44, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (2 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Idaho Senate** and **Idaho House** (`id-senate` and `id-house`, the same 35 legislative districts, one senator and two representatives each, joined to the Legislature's own membership pages), the TIGERweb fabric drawn from mirrored tile archives — **City** (`municipality`, 199 incorporated cities), **School District** (116 unified districts) and **ZIP Code** — three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**) and **Tribal Government** (`tribal-government`, the Census's tribal land, joined to the government that holds it).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `id/scripts/build_metro_outline.py --check` holds it to 44
INSIDE anchors, one per county, and 16 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN IDAHO IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 2 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `id/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**ONE MAP SERVES BOTH CHAMBERS, BECAUSE IDAHO ELECTS BOTH FROM THE SAME 35 DISTRICTS**: each elects
one senator and two representatives, to Seat A and Seat B, which the Legislature's own member list prints.
TIGERweb carries the plan twice (layers 1 and 2, its 2026 state legislative districts); measured
2026-11-12 the two carry the same 35 districts, each intersection-over-union 1.0, and both match
TIGERweb's 2024 layers (5 and 6). The builder measures the two against each other on every build
(`check_twin`: the same 35 numbers, each at least 0.9999) and refuses otherwise, then writes the plan
once, as `id-legislative-districts.json`, which the Senate and House layers both read, so a reader
downloads it once and the two layers' lines cannot part. It refuses if a layer's name changes, and the
map is simplified with Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN MEMBERSHIP PAGES** (`legislature.idaho.gov/senate/membership/`
and `/house/membership/`, `id/scripts/build_id_legislature_roster.py`): one block per member giving the
name and party letter, an e-mail address at senate.idaho.gov or house.idaho.gov, the district, a
representative's seat ("House Seat A" or "Seat B") and a Statehouse telephone the page marks "(Session
Only)", which ships with those words. Measured 2026-11-12: all 35 senators and all 70 representatives.
The House roster is `{seats: 2, members: [Seat A, Seat B]}` per district, so the House card names both.
**EACH BLOCK ALSO PRINTS THE MEMBER'S HOME ADDRESS, AND IT IS NEVER READ**: the script takes the name,
party, e-mail link, district link, seat line and the one telephone link labelled "Statehouse", and
nothing else. robots.txt read 2026-11-12: no rule in its `*` group matches the two pages.

**MOST OF IDAHO IS IN NO CITY.** The **City** layer is TIGERweb's incorporated places (layer 4): 199
records, 198 active cities and the city of Lost River, which the Census records as an inactive
government, about 1% of the state's land (1,967.8 of 214,050.8 km2, measured 2026-11-12). An empty card
says the point is outside every city and that the county is the local government there. No mayor or
council member is named yet (gap `id-municipal-officeholders`).

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 116 unified districts for Idaho and nothing on its
elementary or secondary layers (measured 2026-11-12), so those two layers are not drawn. No school board
member is named yet (gap `id-school-board-members`).

**NO COUNTY OFFICIAL IS NAMED YET**, and the card says so rather than leave a reader to assume the office
is empty. Each county is governed by an elected board of three county commissioners and elects officers
such as a clerk, a treasurer, an assessor, a sheriff, a coroner and a prosecuting attorney. Recorded as
gap `id-county-officials`.

**TRIBAL GOVERNMENT DRAWS THE LAND OF FIVE NATIONS AND NAMES ONE NATION'S COUNCIL** (`tribal-areas.json`,
since 2026-11-13). The Census keeps five reservations and two trust lands in Idaho, measured
2026-11-12 with `scripts/tribal_areas.py --report Idaho`: the Nez Perce (3,120.9 km2), Fort Hall
(2,214.0 km2), Coeur d'Alene (1,389.4 km2) and Kootenai reservations, the Idaho half of the Duck
Valley Reservation (588.7 km2, 50.3% of it), and the Kootenai and Fort Hall trust lands. All seven
pieces are drawn, the Duck Valley Reservation whole into Nevada, each joined in
`data/tribal-government-join.json` to the government the Bureau of Indian Affairs lists for it. The
Bureau lists no office town for the Shoshone-Paiute Tribes of the Duck Valley Reservation, so its
card gives the one the tribes' own site gives, Owyhee, Nevada, says where it came from, and links
that site, as Nevada's card for the same land does (`seatFromNation`). The Shoshone-Paiute Tribes' card names their Business Council, read 2026-11-13 for the Nevada half
of the Duck Valley Reservation; the other nations are not carried yet (`ROSTER_NOT_SOUGHT` in
`scripts/build_tribal_areas.py`), recorded in gap `id-tribal-government`.

**THE ZIP LAYER HIDES OUTSIDE IDAHO.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the seven officers Idaho elects statewide (the governor, lieutenant
governor, secretary of state, attorney general, state controller, state treasurer and superintendent of
public instruction) and both U.S. senators, from `id/data/source/statewide-officials.source.json` through
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

- Metro: Idaho (`idaho`) — https://districtry.com/id/
- Geocoders: address Photon (Idaho-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Idaho-bounded, serial >=1s queue)
- Ground truth: 43.61771,-116.19975 (Idaho State Capitol, 700 West Jefferson Street, Boise, Ada County) → county Ada County; us-house 2; id-senate 19; id-house 19. Negative point 49.08000,-116.45000 (British Columbia, Canada, north of Bonners Ferry — outside Idaho and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here, because it is in Canada (control: the Idaho State Capitol returns Idaho), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any outline in the change that opens the last thirteen states. IT IS IN CANADA, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 11 registered (political 4, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.IdahoExplorer`.
- Scheduled workflows: `update-id-congress-roster.yml` (Wed 22:21 UTC); `update-id-legislature-roster.yml` (Thu 22:21 UTC); `id-validate-sources.yml` (2nd of month 22:21 UTC).
- Source registry: `id/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/id/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/id/ node id/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 id/scripts/validate_index.py id/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 id/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in id/metro-worksheet.json;
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
which vendors Leaflet into `id/scripts/vendor/leaflet/` (gitignored);
`id/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Idaho-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`id/scripts/build_metro_outline.py`), `state-counties.json` (the counties, `id/scripts/build_state_counties.py`),
and `congress-districts.json` and `id-legislative-districts.json`
(`id/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m under an 8 m ceiling, the one legislative map written once, refused unless the twin check, the 2,000-random-point agreement gate and the 8 m fidelity ceiling all pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance id`; 46,134 populated blocks holding all 1,839,106 people the 2020 census counted in Idaho). Both maps are held to that count; the worst districts are +0.000% (congress) and -3.768% (the legislative map) of the raw-census ideal. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 278 ZIP codes). Rosters:
`congress-roster.json` (`id/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`id-senate-members.json` and `id-house-members.json` (`id/scripts/build_id_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`id/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
both chamber files to one record per seat, and each multi-member district to the number of members it elects.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `id/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
