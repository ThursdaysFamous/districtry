# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Kansas: a single-file, dependency-light web app. Click a point in Kansas
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/ks/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
eighth state of batch 3 of the state-level launch Adam asked for on 2026-11-10 (Massachusetts, Colorado, Maryland, Alabama, Oregon, Connecticut, Utah, Kansas),
in his chosen order: built dark, with the deploy excluding `ks/**`, and opened with the rest of its
batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own data: **County** (`county`, all 105, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (4 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Kansas Senate** and **Kansas House** (40 and 125 districts, TIGERweb's 2026 state legislative districts joined to the Legislature's own member feed), the TIGERweb fabric drawn from mirrored tile archives — **City** (`municipality`, 626 incorporated places), **School District** (285) and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `ks/scripts/build_metro_outline.py --check` holds it to 105
INSIDE anchors, one per county, and 14 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN KANSAS IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 4 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `ks/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2).**
Measured 2026-11-12 against the 2024 vintage (layers 5 and 6): every district in both chambers identical (intersection-over-union 1.0). The builder refuses if a layer's name changes, since TIGERweb renumbers its
layers when a vintage rolls, and there is no nesting rule between the chambers (a House district's largest share inside one Senate district is as low as 0.39 of its area), so each map is simplified on its own, Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN MEMBER FEED AND PAGES** (`www.kslegislature.gov`,
`ks/scripts/build_ks_legislature_roster.py`): the JSON feed the site reads its member lists from
gives each member's name, district, party, e-mail address at house.ks.gov or senate.ks.gov,
Statehouse room and telephone, and the member's own page prints the same; every page's footer
prints the Statehouse address, which is carried under the room. Measured 2026-11-12: 40 senators and
125 representatives, every one "Active", every seat of both chambers. **EACH RECORD ALSO CARRIES HOME
AND BUSINESS ADDRESSES AND TELEPHONES (EVERY `HM*` AND `BUS*` FIELD), A CELL TELEPHONE, A SPOUSE'S
NAME AND AN OCCUPATION, AND NONE OF THEM IS EVER READ.** robots.txt answered 404 on 2026-11-12,
which RFC 9309 reads as no restriction; the feed is paced at one request a second regardless.

**MOST OF KANSAS IS IN NO CITY.** The **City** layer is TIGERweb's incorporated places (layer 4):
626 records, 623 active cities, the city of Frederick (which the Census records as an inactive
government), the city of Tribune (which it records as having no functioning government) and the
balance of Greeley County's unified government, about 3% of the state's land (measured 2026-11-12).
An empty card says the point is outside every city and that the county is the local government
there. **WYANDOTTE COUNTY AND KANSAS CITY ARE ONE GOVERNMENT**, the Unified Government of Wyandotte
County and Kansas City, and **GREELEY COUNTY AND TRIBUNE ARE ONE TOO**; their County and City cards
say so.

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 285 unified districts for Kansas and nothing on its
elementary or secondary layers (measured 2026-11-12), so those two layers are not drawn. No school
board member is named yet (gap `ks-school-board-members`).

**NO COUNTY, CITY OR TOWNSHIP OFFICIAL IS NAMED YET**, and the cards say so rather than leave a
reader to assume the office is empty. Each county is governed by an elected board of county
commissioners, and most elect officers such as a clerk, a treasurer, a register of deeds and a
sheriff. Recorded as gaps `ks-county-officials` and `ks-municipal-officeholders`. **KANSAS ALSO HAS
1,258 ACTIVE TOWNSHIPS** (TIGER's county subdivisions), each with elected officers; they are not
drawn yet, and the done-standard scorer marks that level open.

**TRIBAL LAND IS NOT DRAWN YET.** The Census keeps four reservations in Kansas (Kickapoo, about
613 km2, Prairie Band of Potawatomi Nation, about 316 km2, and the Kansas parts of the Iowa (KS-NE)
and Sac and Fox Nation reservations) and two off-reservation trust lands, measured 2026-11-12 with
`scripts/tribal_areas.py --report Kansas`. The state is recorded as not yet covered in
`data/tribal-government-join.json`.

**THE ZIP LAYER HIDES OUTSIDE KANSAS.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** lists the six officers Kansas elects statewide (the governor,
lieutenant governor, attorney general, secretary of state, state treasurer and commissioner of
insurance) and both U.S. senators, from `ks/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`. The governor's, attorney general's and insurance
commissioner's own sites answered this project's token and the browser client alike with HTTP 403
from the build sandbox on 2026-11-12, so the state's own portal at www.kansas.gov, which names
them, is the page read; it does not name the lieutenant governor, who is listed without a name
until a run can read the governor's site.

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

- Metro: Kansas (`kansas`) — https://districtry.com/ks/
- Geocoders: address Photon (Kansas-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Kansas-bounded, serial >=1s queue)
- Ground truth: 39.04807,-95.67803 (Kansas State Capitol, 300 SW 10th Avenue, Topeka, Shawnee County) → county Shawnee County; us-house 2; ks-senate 19; ks-house 57. Negative point 40.20000,-98.50000 (Webster County, Nebraska, about 20 km north of the Kansas line — outside Kansas and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names Nebraska here (control: the State Capitol returns Kansas), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any of the other batch-3 states' outlines. A POINT ON A NEIGHBOUR'S LAND MOVES THE DAY THAT NEIGHBOUR GOES LIVE: Nebraska is in batch 4 of the state-level launch, and the change that makes it live moves this point. Every other neighbour of Kansas is live or goes live in batch 3.).
- Layers: 10 registered (political 3, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.KansasExplorer`.
- Scheduled workflows: `update-ks-congress-roster.yml` (Mon 23:31 UTC); `update-ks-legislature-roster.yml` (Tue 23:31 UTC); `ks-validate-sources.yml` (1st of month 23:55 UTC).
- Source registry: `ks/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ks/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ks/ node ks/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ks/scripts/validate_index.py ks/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 ks/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in ks/metro-worksheet.json;
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
which vendors Leaflet into `ks/scripts/vendor/leaflet/` (gitignored);
`ks/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Kansas-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the three chamber layers use the fenced factory helper `registerIlgaChamber` (which renders a vacancy record as a vacant seat with its reason and source), the County and municipality cards are bespoke `registerLayer` blocks, the school layer `registerPolygonLayer`, and the three nearest-N layers `registerNearestPointLayer`. Two invariants pervade the
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
`ks/scripts/build_metro_outline.py`), `state-counties.json` (`ks/scripts/build_state_counties.py`),
and `congress-districts.json`, `ks-senate-districts.json` and `ks-house-districts.json`
(`ks/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance ks`; 109,149 populated
blocks holding all 2,937,880 people the 2020 census counted in Kansas). All three maps are held to that count; the congressional map sits within 0.001% of its ideal, and the worst legislative districts are +3.946% (Senate) and -3.940% (House). The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 710 ZIP codes). Rosters:
`congress-roster.json` (`ks/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`ks-senate-members.json` and `ks-house-members.json` (`ks/scripts/build_ks_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs — and `statewide-officials.json`
(`scripts/build_statewide_officials.py`, from `ks/data/source/statewide-officials.source.json`).
`scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `ks/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
