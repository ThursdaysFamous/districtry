# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Colorado: a single-file, dependency-light web app. Click a point in Colorado
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/co/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
second state of batch 3 of the state-level launch Adam asked for on 2026-11-10 (Massachusetts, Colorado, Maryland, Alabama, Oregon, Connecticut, Utah, Kansas),
in his chosen order: built dark, with the deploy excluding `co/**`, and opened with the rest of its
batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the General Assembly's own data: **County** (`county`, all 64, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (8 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Colorado Senate** and **Colorado House** (35 and 65 districts, TIGERweb's 2026 state legislative districts joined to the General Assembly's own legislator list), the TIGERweb fabric drawn from mirrored tile archives — **City or Town** (`municipality`, 272 incorporated places and one inactive town), **School District** (178) and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `co/scripts/build_metro_outline.py --check` holds it to 64
INSIDE anchors, one per county, and 16 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN COLORADO IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 8 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `co/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2).**
Measured 2026-11-12 against the 2024 vintage (layers 5 and 6): every district in both chambers identical (intersection-over-union 1.0). The builder refuses if a layer's name changes, since TIGERweb renumbers its
layers when a vintage rolls, and there is no nesting rule between the chambers (a House district's largest share inside one Senate district is as low as 0.41 of its area), so each map is simplified on its own, Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE GENERAL ASSEMBLY'S OWN LEGISLATOR LIST** (`leg.colorado.gov/legislators`,
`co/scripts/build_co_legislature_roster.py`): one table, a row per member, giving the name, district,
party, Capitol telephone, e-mail address and page. Measured 2026-11-12 it held 102 rows for 100
seats, because two members who resigned stay listed with a note under the name beside the members
appointed to their seats; a row whose note says the member resigned is not read, and any other note
stops the build for a person to read. The page's footer prints the Capitol's address, which every
member's own page prints too, so it is carried above the member's Capitol telephone. The e-mail
address is the one the General Assembly prints: 100 of the 102 were at coleg.gov, and the other two
(one at gmail.com, one at senate.co.com) are carried as printed under the fleet's rule of
2026-10-17. robots.txt read 2026-11-12: its `*` group disallows admin and file-download paths and
the calendars and journals, `/legislators` is allowed, and no Crawl-delay is stated.

**MOST OF COLORADO IS IN NO CITY OR TOWN.** The **City or Town** layer is TIGERweb's
incorporated places (layer 4): 273 records, 197 towns, 75 cities and the town of Bonanza, which the
Census records as an inactive government, about 2% of the state's land (measured 2026-11-12). An
empty card says the point is outside every city and town and that the county is the local
government there. **DENVER AND BROOMFIELD ARE EACH A CITY AND A COUNTY IN ONE GOVERNMENT**, run by
an elected mayor and city council, and both their County and City cards say so.

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 178 unified districts for Colorado and nothing on
its elementary or secondary layers (measured 2026-11-12), so those two layers are not drawn. No
school board member is named yet (gap `co-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Each county is governed by an elected board of county commissioners
and elects officers such as a clerk and recorder, a treasurer, an assessor, a sheriff and a coroner.
Recorded as gaps `co-county-officials` and `co-municipal-officeholders`.

**TRIBAL LAND IS NOT DRAWN YET.** The Census keeps two reservations in Colorado, the Southern Ute
Reservation (about 2,759 km2) and the Colorado part of the Ute Mountain Reservation (about 1,854
km2, 80.5% of it), measured 2026-11-12 with `scripts/tribal_areas.py --report Colorado`. The state
is recorded as not yet covered in `data/tribal-government-join.json`.

**THE ZIP LAYER HIDES OUTSIDE COLORADO.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the five officers Colorado elects statewide (the governor,
lieutenant governor, attorney general, secretary of state and state treasurer) and both U.S.
senators, from `co/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`. Several officers' own sites answered this project's token
with HTTP 403 and served the browser client, which the seed records host by host. The attorney
general's site answered its robots.txt request with HTTP 202, an access control rather than a
document, so it is linked and never read; the state's home page, which lists every statewide
officer, is read instead. The at-large members of the University of Colorado's Board of Regents and
of the State Board of Education are elected statewide too and are not listed yet.

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

- Metro: Colorado (`colorado`) — https://districtry.com/co/
- Geocoders: address Photon (Colorado-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Colorado-bounded, serial >=1s queue)
- Ground truth: 39.73924,-104.98480 (Colorado State Capitol, 200 East Colfax Avenue, Denver) → county Denver County; us-house 1; co-senate 31; co-house 6. Negative point 41.15000,-105.90000 (Albany County, Wyoming, about 17 km north of the Colorado line west of Laramie — outside Colorado and inside permalink_gate, so the app answers a selection there and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names Wyoming here (control: the State Capitol returns Colorado), and none of the state's shipped boundary files contains it. WYOMING'S OUTLINE HAS COVERED THIS POINT SINCE THE CHANGE THAT PUBLISHED WYOMING (batch 4 of the state-level launch, written 2026-11-12), which found it inside Wyoming's outline in fleet-outlines.json and no other, AND THE POINT STAYS: measured that day on a 0.05-degree grid, no ground in this app's gate lies more than 2 km from every outline in fleet-outlines.json, so there is nowhere left to move it to. It is still outside Colorado and outside every shipped boundary file, which is all the checks that boot on it or select it ask, and a selection the app makes itself never leaves; the click that had to stay here became a Wyoming routing case in the same change, and the click-stays-here check went with it, the way Kentucky's and Tennessee's points stayed put once every neighbour was served.).
- Layers: 10 registered (political 3, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.ColoradoExplorer`.
- Scheduled workflows: `update-co-congress-roster.yml` (Mon 22:19 UTC); `update-co-legislature-roster.yml` (Tue 22:19 UTC); `co-validate-sources.yml` (1st of month 23:19 UTC).
- Source registry: `co/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/co/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/co/ node co/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 co/scripts/validate_index.py co/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 co/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in co/metro-worksheet.json;
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
which vendors Leaflet into `co/scripts/vendor/leaflet/` (gitignored);
`co/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Colorado-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`co/scripts/build_metro_outline.py`), `state-counties.json` (`co/scripts/build_state_counties.py`),
and `congress-districts.json`, `co-senate-districts.json` and `co-house-districts.json`
(`co/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance co`; 99,899 populated
blocks holding all 5,773,714 people the 2020 census counted in Colorado). All three maps are held to that count; the worst districts are +0.011% (congress), +4.568% (Senate) and +3.234% (House) of the raw-census ideal. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 525 ZIP codes). Rosters:
`congress-roster.json` (`co/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`co-senate-members.json` and `co-house-members.json` (`co/scripts/build_co_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs — and `statewide-officials.json`
(`scripts/build_statewide_officials.py`, from `co/data/source/statewide-officials.source.json`).
`scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `co/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
