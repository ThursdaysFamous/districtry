# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Maryland: a single-file, dependency-light web app. Click a point in Maryland
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/md/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
third state of batch 3 of the state-level launch Adam asked for on 2026-11-10 (Massachusetts, Colorado, Maryland, Alabama, Oregon, Connecticut, Utah, Kansas),
in his chosen order: built dark, with the deploy excluding `md/**`, and opened with the rest of its
batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the General Assembly's own data: **County** (`county`, the 23 counties and Baltimore City, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (8 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Maryland Senate** (`md-senate`, 47 districts) and **Maryland House of Delegates** (`md-house`, 141 delegates elected from 71 districts and subdistricts), the TIGERweb fabric drawn from mirrored tile archives — **City, Town or Village** (`municipality`, 157 incorporated places), **School District** (24, one per county and Baltimore City) and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county or Baltimore City is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `md/scripts/build_metro_outline.py --check` holds it to 24
INSIDE anchors, one per county or Baltimore City, and 15 OUTSIDE anchors over the state line and offshore.

**ITS FLEET BOX IN `metros.json` STARTS AT LONGITUDE -79.41** rather than the state's own -79.49,
and that is a measurement: Virginia's `metro_center` (38.0, -79.42) lies inside the full box, and
`validate_index.py` refuses a sibling's hand-off box that holds an instance's own centre. The clip
leaves out a strip of western Garrett County holding 5,027 of the 2020 census's people (clipping the
box's southern edge to 38.01 instead would have left out 5,135, Crisfield and Smith Island among
them), and the cost is confined to the search box's sibling rows when `fleet-outlines.json` cannot
be read, because the outlines decide every selection.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN MARYLAND IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 8 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `md/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2).**
Measured 2026-11-12 against the 2024 vintage (layers 5 and 6): every district in both chambers identical (intersection-over-union 1.0). The builder refuses if a layer's name changes, since TIGERweb renumbers its
layers when a vintage rolls, and the two chambers nest, so both are simplified in one shared topology (described below).

**THE HOUSE OF DELEGATES ELECTS THREE MEMBERS FROM EACH OF THE 47 DISTRICTS, AND 18 OF THEM ARE
SPLIT INTO SUBDISTRICTS.** TIGER's lower-house layer carries the 71 units a delegate is elected
from: 29 whole districts electing three, and 42 subdistricts ("30A", "38C") electing one or two.
The House roster keys each unit to `{seats, members}`, and the bespoke `md-house` card lists every
member, says how many the unit elects, and says so when the roster lists fewer. **EVERY SENATE
DISTRICT IS EXACTLY ITS DELEGATES' UNITS**: measured 2026-11-12 on TIGERweb's own polygons, each of
the 47 is either one whole-district unit or the union of its subdistricts, so the builder
simplifies both maps in one shared topology (Douglas-Peucker at 5 m under an 8 m ceiling) and its
`--check` holds the nesting offline in CI.

**THE LEGISLATORS COME FROM THE GENERAL ASSEMBLY'S OWN MEMBER PAGES** (`mgaleg.maryland.gov`,
`md/scripts/build_md_legislature_roster.py`): each chamber's member index gives the name, district
and party, and each member's page the Annapolis office and telephone and the legislative e-mail
address. Measured 2026-11-12: all 47 senators and 140 of the 141 delegates; District 36, which
elects three from the whole district, listed two, and its card says so with the date. How many
delegates each unit elects is the builder's `DELEGATES` table, read off that day's index; the weekly
run refuses a list naming more delegates for a unit than it elects, or a unit the map does not draw.
The Interim office, the district office, biographies and staff are never read. robots.txt answered
404 on 2026-11-12, which RFC 9309 reads as no restriction.

**MOST OF MARYLAND IS IN NO CITY, TOWN OR VILLAGE.** The **City, Town or Village** layer is
TIGERweb's incorporated places (layer 4): 157 records, 123 towns, 29 cities and 5 villages, every
one an active government, about 5% of the state's land (measured 2026-11-12). An empty card says
the point is outside every incorporated place and that the county is the local government there.
**BALTIMORE IS AN INDEPENDENT CITY, PART OF NO COUNTY**, and the Census files it as a county
equivalent too, so both its County and City cards say so.

**THE SCHOOL LAYER IS ONE TILING.** Maryland runs one public school system per county and one for
Baltimore City, and TIGER holds those 24 as unified districts and nothing on its elementary or
secondary layers (measured 2026-11-12). No school board member is named yet (gap
`md-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Each county is governed by an elected county council (with an
elected county executive in most charter counties) or by elected county commissioners, and elects
officers such as a sheriff, a state's attorney, a clerk of the circuit court and a register of
wills. Recorded as gaps `md-county-officials` and `md-municipal-officeholders`.

**THERE IS NO TRIBAL LAND TO DRAW.** The Census keeps no reservation, trust land or state
reservation in Maryland (measured 2026-11-12 with `scripts/tribal_areas.py --report Maryland`), so
the state is recorded as covered in `data/tribal-government-join.json`, with nothing to draw.

**THE ZIP LAYER HIDES OUTSIDE MARYLAND.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the four officers Maryland elects statewide (the governor,
lieutenant governor, attorney general and comptroller) and both U.S. senators, from
`md/data/source/statewide-officials.source.json` through `scripts/build_statewide_officials.py`.
The General Assembly chooses the State Treasurer and the governor appoints the Secretary of State,
so neither is listed.

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

- Metro: Maryland (`maryland`) — https://districtry.com/md/
- Geocoders: address Photon (Maryland-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Maryland-bounded, serial >=1s queue)
- Ground truth: 38.97864,-76.49077 (Maryland State House, 100 State Circle, Annapolis, Anne Arundel County) → county Anne Arundel County; us-house 3; md-senate 30; md-house 30A. Negative point 38.35000,-74.95000 (The Atlantic about 15 km east of Ocean City — outside Maryland and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here (control: the State Capitol returns Maryland), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any of the other batch-3 states' outlines. IT IS OPEN WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 10 registered (political 3, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.MarylandExplorer`.
- Scheduled workflows: `update-md-congress-roster.yml` (Mon 22:31 UTC); `update-md-legislature-roster.yml` (Tue 22:31 UTC); `md-validate-sources.yml` (1st of month 23:25 UTC).
- Source registry: `md/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/md/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/md/ node md/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 md/scripts/validate_index.py md/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 md/scripts/build_metro_outline.py --check

# Nesting gate (every Senate vertex is a vertex of its delegates' units, offline):
python3 md/scripts/build_legislative_boundaries.py --check

# Generated-region gate: per-instance facts live ONCE in md/metro-worksheet.json;
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
which vendors Leaflet into `md/scripts/vendor/leaflet/` (gitignored);
`md/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Maryland-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the U.S. House and Senate layers use the fenced factory helper `registerIlgaChamber`, the House of Delegates, County and City, Town or Village cards are bespoke `registerLayer` blocks (the House of Delegates because a unit elects one to three members), the school layer `registerPolygonLayer`, and the three nearest-N layers `registerNearestPointLayer`. Two invariants pervade the
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
`md/scripts/build_metro_outline.py`), `state-counties.json` (`md/scripts/build_state_counties.py`),
and `congress-districts.json`, `md-senate-districts.json` and `md-house-districts.json`
(`md/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, the two chambers in one topology, refused unless the 2,000-random-point agreement gate, the 8 m fidelity ceiling and the exact nesting check (every Senate district the union of its delegates' units) all pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance md`; 65,274 populated
blocks holding all 6,177,224 people the 2020 census counted in Maryland). The congressional and Senate maps are held to that count (worst districts +0.737% and -5.421% of the raw-census ideal; the likeliest reason, inferred and not measured, is that Maryland counts an incarcerated person at their last address). The House of Delegates map is not held, because its units elect one, two or three delegates and one ideal describes none of them. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 477 ZIP codes). Rosters:
`congress-roster.json` (`md/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`md-senate-members.json` and `md-house-members.json` (`md/scripts/build_md_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs — and `statewide-officials.json`
(`scripts/build_statewide_officials.py`, from `md/data/source/statewide-officials.source.json`).
`scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat, and each House of Delegates unit to the number of delegates it elects.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `md/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
