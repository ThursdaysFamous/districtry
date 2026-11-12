# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Florida: a single-file, dependency-light web app. Click a point in Florida
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/fl/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
second state of batch 2 of the state-level launch Adam asked for on 2026-11-10 (Texas, Florida,
Ohio, California, Washington), in his chosen order: built dark, with the deploy excluding
`fl/**`, and opened with the rest of its batch in one go-live change on Adam's own "merge",
which narrowed that exclude, added its `metros.json` entry and gave it a `layer-concepts.json`
column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or each chamber's own pages: **County** (`county`, all 67, Census TIGERweb, the state outline
the coverage wash covers), **U.S. House** (28 districts, TIGERweb geometry joined to the
public-domain unitedstates/congress-legislators roster), **Florida Senate** and **Florida House**
(40 and 120 districts, TIGERweb's 2026 state legislative districts joined to each chamber's own
member pages), the TIGERweb fabric drawn from mirrored tile archives — **City, Town or Village**
(`municipality`, 411 incorporated places), **School District** (67, one per county) and **ZIP
Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire &
EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline (two rings, 67 counties inside, measured by its
`--check`) and the wash has no lighter band (`coverage_key` with `outside` and `edge` only).

**THE CONGRESSIONAL MAP IS THE ONE THE SITTING MEMBERS WERE ELECTED FROM, TIGERweb LAYER 4 (THE
119TH CONGRESS), UNTIL 3 JANUARY 2027.** Florida has a new map for the 120th Congress, which the
November 2026 election used (layer 0, "120th Congressional Districts"). Measured 2026-11-11: 21
of the 28 districts differ between the two (the lowest intersection-over-union District 23 at
0.0), so they are not interchangeable. `fl/scripts/build_legislative_boundaries.py` refuses to
build layer 4 on or after 3 January 2027; the change that day switches it to layer 0, a person's
step, because the cards then name the members elected in 2026.

**THE FL-20 SEAT IS VACANT, AND THE CARD SAYS SO FROM THE HOUSE CLERK'S OWN PAGE.** The
congress-legislators roster carries 27 Florida members; the Clerk's vacancy list
(clerk.house.gov/Members/ViewVacancies) says the 20th District's member resigned on April 21,
2026. `fl/scripts/build_congress_roster.py` fills a missing district only with a vacancy the Clerk
lists, and refuses any other gap; the record keeps the date it was first read across weekly runs.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2).** Measured
2026-11-11 against the 2024 vintage (layers 5 and 6): 32 of the 40 Senate districts identical and
eight different by slivers (the lowest District 20, IoU 0.99955), 103 of the 120 House districts
identical and 17 different (the lowest District 71, IoU 0.986), the Census Bureau's own correction
between vintages. There is no nesting rule between the chambers, so each map is simplified on its
own, Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM EACH CHAMBER'S OWN PAGES** (`www.flsenate.gov`, `www.flhouse.gov`,
`fl/scripts/build_fl_legislature_roster.py`). The Senate's member list gives each seat's senator
and party, and each senator's page the name, the senator's own e-mail address and the Tallahassee
office and telephone; 31 of the 39 named senators print an e-mail address, and the other eight
offer only the Senate's e-mail form (measured 2026-11-11). District 39 is listed as vacant. The
House's member list gives each seat's member and party, and each member's contact page the name
and the Capitol office and telephone; the House prints no e-mail address for anyone. 43 of the
120 members' contact pages print no Capitol office yet, the members elected on 3 November 2026
whose offices are not posted, so the office floor is 0.6 until they are (`fl/WATCH.md`). Fax lines
and district offices are never read. robots.txt is read before the first fetch of each host with
the crawling client; the Senate is paced at one request a second and the House at one every two.

**MOST OF FLORIDA IS IN NO CITY, TOWN OR VILLAGE.** The **City, Town or Village** layer is
TIGERweb's incorporated places (layer 4): 267 cities, 123 towns and 21 villages, every one an
active government, about 10.3% of the state's land (measured 2026-11-11). Jacksonville's
government is consolidated with Duval County's, and the Census records it as a city like any
other. An empty card says the point is outside every incorporated place and that the county is
the local government there.

**THE SCHOOL LAYER IS ONE TILING.** Florida's constitution makes each county one school district,
and TIGER holds 67 unified districts for Florida and nothing on its elementary or secondary layers
(measured 2026-11-11), so those two layers are not drawn. No school board member is named yet
(gap `fl-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Recorded as gaps `fl-county-officials` and
`fl-municipal-officeholders`.

**THE ZIP LAYER HIDES OUTSIDE FLORIDA.** A ZCTA carries no state field, so over the line the live
service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline, and
the smoke test asserts both halves. The archive keeps 1,013 of the 1,102 ZCTAs in the app's box
(measured 2026-11-11).

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the five officers Florida elects statewide (the governor,
lieutenant governor, attorney general, chief financial officer and commissioner of agriculture)
and both U.S. senators, from `fl/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`. The Commissioner of Agriculture is listed without a name:
the department's robots.txt refuses this project's client, and the one other government page that
names him (the Governor and Cabinet's site) prints it only inside its script data, which the
builder does not read. The Attorney General's site refuses our token and serves the browser
client, which the seed records. Supreme Court justices are retained by statewide vote but
appointed, so they are not listed.

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

- Metro: Florida (`florida`) — https://districtry.com/fl/
- Geocoders: address Photon (Florida-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Florida-bounded, serial >=1s queue)
- Ground truth: 30.43817,-84.28164 (Florida State Capitol, 400 South Monroe Street, Tallahassee, Leon County) → county Leon County; us-house 2; fl-senate 3; fl-house 9. Negative point 27.00000,-85.50000 (Open water in the Gulf, about 200 km west of Sarasota — outside Florida and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-11: TIGERweb's state layer places it in no state and its ZCTA layer in no ZIP code (controls: the State Capitol returns Florida and ZIP code 32399, and a point in Havana returns no state), none of the state's shipped boundary files contains it, and none of the 25 outlines in fleet-outlines.json does. IT IS FAR OUT TO SEA, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 10 registered (political 3, safety 2, schools 1, geography 4); `registerLayer(` floor 6. Debug namespace `window.FloridaExplorer`.
- Scheduled workflows: `update-fl-congress-roster.yml` (Mon 20:47 UTC); `update-fl-legislature-roster.yml` (Wed 20:47 UTC); `fl-validate-sources.yml` (1st of month 22:53 UTC).
- Source registry: `fl/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/fl/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/fl/ node fl/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 fl/scripts/validate_index.py fl/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 fl/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in fl/metro-worksheet.json;
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
which vendors Leaflet into `fl/scripts/vendor/leaflet/` (gitignored);
`fl/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Florida-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the three chamber layers use the fenced factory helper `registerIlgaChamber` (which renders a
vacancy record as a vacant seat with its reason and source), the County and municipality cards
are bespoke `registerLayer` blocks, the school layer `registerPolygonLayer`, and the three
nearest-N layers `registerNearestPointLayer`. Two invariants pervade the code: the
**stale-async guard** (`if (seq !== state.sequence) return;` after every await) and **per-layer
failure isolation** (a layer's failure shows a Retry inside its own card, never breaks the
others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards say who is not named instead of inventing a name. The chamber cards
degrade to the district number + the chamber's own member list on a roster miss, and a vacant
seat says it is vacant; the County, municipality and school district cards carry no roster and
**say so on the card**. External strings always render through `sanitize()`/`textContent`.
Roster refreshes always land as PRs for review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`fl/scripts/build_metro_outline.py` — one INSIDE anchor per county plus OUTSIDE anchors in
Alabama, Georgia and the sea), `state-counties.json` (`fl/scripts/build_state_counties.py`),
and `congress-districts.json`, `fl-senate-districts.json`, `fl-house-districts.json`
(`fl/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, refused unless the
2,000-random-point agreement gate and the 8 m fidelity ceiling pass). The TIGERweb fabric layers
draw from tile archives under `data/app/tiles/`, mirrored by `scripts/mirror_tiger_tiles.py`. The
compare screen counts people from Census 2020 blocks under `data/app/population/`
(`scripts/build_block_population.py --instance fl`; 21,538,187 people in 67 county files). The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`). Rosters: `congress-roster.json`
(`fl/scripts/build_congress_roster.py`, from unitedstates/congress-legislators and the House
Clerk's vacancy list) and `fl-{senate,house}-members.json`
(`fl/scripts/build_fl_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed
PRs. `scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `fl/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
