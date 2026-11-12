# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Connecticut: a single-file, dependency-light web app. Click a point in Connecticut
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/ct/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
sixth state of batch 3 of the state-level launch Adam asked for on 2026-11-10 (Massachusetts, Colorado, Maryland, Alabama, Oregon, Connecticut, Utah, Kansas),
in his chosen order: built dark, with the deploy excluding `ct/**`, and opened with the rest of its
batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the state's open data portal: **Planning Region** (`county`, the nine planning regions, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (5 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Connecticut Senate** and **Connecticut House** (36 and 151 districts, TIGERweb's 2026 state legislative districts joined to the General Assembly's own member list), the TIGERweb fabric drawn from mirrored tile archives — **Town** (`municipality`, the 169 towns), **School District (Unified)**, **(Elementary)** and **(Secondary)** and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every planning region is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `ct/scripts/build_metro_outline.py --check` holds it to 9
INSIDE anchors, one per planning region, and 10 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN CONNECTICUT IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 5 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `ct/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2).**
Measured 2026-11-12 against the 2024 vintage (layers 5 and 6): every district in both chambers identical (intersection-over-union 1.0). The builder refuses if a layer's name changes, since TIGERweb renumbers its
layers when a vintage rolls, and there is no nesting rule between the chambers (a House district's largest share inside one Senate district is as low as 0.42 of its area), so each map is simplified on its own, Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE GENERAL ASSEMBLY'S OWN MEMBER LIST, PUBLISHED ON THE STATE'S
OPEN DATA PORTAL** (data.ct.gov dataset `rgw6-bpst`, "Current Connecticut Legislators",
`ct/scripts/build_ct_legislature_roster.py`): each member's name, party, Legislative Office Building
room, telephone, e-mail address where the list gives one, and caucus page. Measured 2026-11-12:
187 records, every seat of both chambers. The query names the columns it reads with `$select`, so
the list's home-address columns are never fetched. **THE TELEPHONE IS THE CAUCUS'S, SO IT SHIPS ON
THE OFFICE**: 167 of the 187 records print one of a handful of caucus numbers, which by the fleet's
rule belongs to the office, so every number ships under the card's office room and never as the
member's own telephone. The 25 Senate Democrats' records hold their caucus website's address in the
e-mail field, which is not an e-mail address and is not carried. Each member's page is their
caucus's, under ct.gov for the two Democratic caucuses and not for the two Republican ones; all four
are printed by the state's own dataset and carried. robots.txt read 2026-11-12: a Crawl-delay of 1,
which the fetch honours.

**EVERY PART OF CONNECTICUT'S LAND IS IN ONE OF ITS 169 TOWNS**, and the Census files each as a
county subdivision, so the **Town** layer is TIGERweb's county subdivisions
(Places_CouSub_ConCity_SubMCD layer 1). Measured 2026-11-12 across the 174 records: 149 towns, 20
towns the Census records as consolidated with the city or borough of the same name (FUNCSTAT C:
Hartford, New Haven, Bridgeport, Naugatuck and the rest, one government each) and 5 records of Long
Island Sound and other coastal water, which the card answers as water. Nine boroughs and the city
of Groton have governments of their own inside their towns; the layer draws the towns and says so,
and does not draw the boroughs.

**THREE SCHOOL LAYERS, AND ONE PLACEHOLDER.** Measured 2026-11-12 for STATE='09': 114 unified
districts, 44 elementary districts (the Census records 17 of them as running every grade) and 8
regional secondary districts (5 running grades 7 to 12 and 3 running 9 to 12), which cover part of
the elementary districts' ground, so a reader there is in two districts at once. **ONE UNIFIED
RECORD IS NOT A DISTRICT**: the Census's "School District Not Defined" (GEOID 0999997) files about
1,096 km2 of Long Island Sound, and the card answers it as no school district. No board of education
member is named yet (gap `ct-school-board-members`).

**CONNECTICUT HAS NO COUNTY GOVERNMENT**, and has had none since 1960. Since 2022 the Census Bureau
files its nine planning regions as the county equivalents, so the first layer draws them and is
labelled **Planning Region**. Each region is a council of governments whose board is made up of the
chief elected officials of its towns, and nobody is elected to one, so there is no county
officeholder to name and no gap is recorded for one (the done-standard scorer carries Connecticut in
`NO_COUNTY_TIER`). The town is the local government over every point, and no town official is named
yet (gap `ct-municipal-officeholders`). **THE POPULATION FILES USE THE EIGHT COUNTIES OF 2020**,
because the 2020 blocks carry those codes and not the planning regions'.

**TRIBAL LAND IS NOT DRAWN YET.** The Census keeps the Mashantucket Pequot Reservation (about 5.5
km2) and the Mohegan Reservation (about 2.5 km2) in Connecticut, the Mashantucket Pequot
Off-Reservation Trust Land, and three state reservations (Schaghticoke, Paucatuck Eastern Pequot
and Golden Hill Paugussett), measured 2026-11-12 with `scripts/tribal_areas.py --report
Connecticut`. The state is recorded as not yet covered in `data/tribal-government-join.json`.

**THE ZIP LAYER HIDES OUTSIDE CONNECTICUT.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The five TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the six officers Connecticut elects statewide (the
governor, lieutenant governor, attorney general, secretary of the state, state treasurer and state
comptroller) and both U.S. senators, from `ct/data/source/statewide-officials.source.json` through
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

- Metro: Connecticut (`connecticut`) — https://districtry.com/ct/
- Geocoders: address Photon (Connecticut-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Connecticut-bounded, serial >=1s queue)
- Ground truth: 41.76373,-72.68255 (Connecticut State Capitol, 210 Capitol Avenue, Hartford, Capitol Planning Region) → county Capitol Planning Region; us-house 1; ct-senate 1; ct-house 7. Negative point 40.85000,-71.60000 (The Atlantic about 25 km south of Block Island and 30 km south-east of Montauk Point — outside Connecticut and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here (control: the State Capitol returns Connecticut), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any of the other batch-3 states' outlines. IT IS OPEN WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 12 registered (political 3, safety 2, schools 3, geography 4); `registerLayer(` floor 10. Debug namespace `window.ConnecticutExplorer`.
- Scheduled workflows: `update-ct-congress-roster.yml` (Mon 23:07 UTC); `update-ct-legislature-roster.yml` (Tue 23:07 UTC); `ct-validate-sources.yml` (1st of month 23:41 UTC).
- Source registry: `ct/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ct/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ct/ node ct/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ct/scripts/validate_index.py ct/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 ct/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in ct/metro-worksheet.json;
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
which vendors Leaflet into `ct/scripts/vendor/leaflet/` (gitignored);
`ct/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Connecticut-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`ct/scripts/build_metro_outline.py`), `state-counties.json` (`ct/scripts/build_state_counties.py`),
and `congress-districts.json`, `ct-senate-districts.json` and `ct-house-districts.json`
(`ct/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance ct`; 42,008 populated
blocks holding all 3,605,944 people the 2020 census counted in Connecticut). All three maps are held to that count; the congressional map sits within 0.001% of its ideal, the Senate's worst district is 5.677% under the raw-census ideal and the House's 8.809% over (the likeliest reason, inferred and not measured, is that Connecticut counts an incarcerated person at their last address since its 2021 plan). The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 288 ZIP codes). Rosters:
`congress-roster.json` (`ct/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`ct-senate-members.json` and `ct-house-members.json` (`ct/scripts/build_ct_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs — and `statewide-officials.json`
(`scripts/build_statewide_officials.py`, from `ct/data/source/statewide-officials.source.json`).
`scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `ct/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
