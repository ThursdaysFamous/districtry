# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Massachusetts: a single-file, dependency-light web app. Click a point in Massachusetts
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/ma/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
first state of batch 3 of the state-level launch Adam asked for on 2026-11-10 (Massachusetts, Colorado, Maryland, Alabama, Oregon, Connecticut, Utah, Kansas),
in his chosen order: built dark, with the deploy excluding `ma/**`, and opened with the rest of its
batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the General Court's own pages: **County** (`county`, the 14 counties, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (9 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Massachusetts Senate** (`ma-senate`, 40 named districts) and **Massachusetts House** (`ma-house`, 160 named districts), the TIGERweb fabric drawn from mirrored tile archives — **City or Town** (`municipality`, the 351 cities and towns), **School District (Unified)**, **(Elementary)** and **(Secondary)** and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `ma/scripts/build_metro_outline.py --check` holds it to 14
INSIDE anchors, one per county, and 15 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN MASSACHUSETTS IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 9 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `ma/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2).**
Measured 2026-11-12 against the 2024 vintage (layers 5 and 6): every district in both chambers identical (intersection-over-union 1.0). The builder refuses if a layer's name changes, since TIGERweb renumbers its
layers when a vintage rolls, and there is no nesting rule between the chambers (a House district's largest share inside one Senate district is as low as 0.37 of its area), so each map is simplified on its own, Douglas-Peucker at 5 m under an 8 m ceiling.

**THE DISTRICTS ARE NAMED, NOT NUMBERED.** Every Senate and House district is a name ("Third
Middlesex", "19th Suffolk", "Second Plymouth and Norfolk"), and TIGER carries it as `BASENAME`, so
both rosters are keyed by that name and the card's pill prints the boundary file's own name
("Third Middlesex District") through the chamber factory's `namedDistricts` option. TIGER writes a
district of several counties with hyphens ("Hampshire-Franklin-Worcester") where the General Court
writes commas and "and"; the builder matches a name after turning every comma and every " and "
into a hyphen on both sides, and a list name that matches no district the map draws stops the
build.

**THE LEGISLATORS COME FROM THE GENERAL COURT'S OWN MEMBER TABLES** (`malegislature.gov/Legislators/Members/Senate`
and `/House`, `ma/scripts/build_ma_legislature_roster.py`): each member's name, party (Democrat,
Republican or Unenrolled), State House room and telephone, General Court e-mail address and page.
Measured 2026-11-12: all 40 senators and 157 of the 160 House members; the table lists 1st
Franklin, 16th Middlesex and 17th Middlesex as vacant, and those cards say so with the day they
were first read that way. A vacant row's office room and telephone are not carried. robots.txt read
2026-11-12: `User-agent: *` with an empty Disallow, everything allowed and no Crawl-delay.

**EVERY PART OF MASSACHUSETTS'S LAND IS IN A CITY OR A TOWN**, and the Census files each as a
county subdivision, so the **City or Town** layer is TIGERweb's county subdivisions
(Places_CouSub_ConCity_SubMCD layer 1). Measured 2026-11-12 across the 357 records: 293 towns, 58
cities and 6 records of coastal water off Barnstable, Bristol, Essex, Nantucket, Plymouth and
Suffolk counties, which the card answers as water rather than naming a place that does not exist.
The cities are also incorporated places, so the Census records their subdivision as fictitious
(FUNCSTAT F); the card names the city either way.

**THREE SCHOOL LAYERS, AND ONE PLACEHOLDER.** Measured 2026-11-12 for STATE='25': 212 unified
districts, 64 elementary districts and 30 secondary districts (18 running grades 7 to 12, 10
running 9 to 12 and 2 running 6 to 12), which cover part of the elementary districts' ground, so a
reader there is in two districts at once. One of the 64 elementary districts is recorded as running
every grade. **ONE UNIFIED RECORD IS NOT A DISTRICT**: the Census's "School District Not Defined"
(GEOID 2599997) files about 4,007 km2 of Massachusetts Bay, Cape Cod Bay, Buzzards Bay and the
other coastal water, and the card answers it as no school district. No school committee member is
named yet (gap `ma-school-board-members`).

**EIGHT OF THE FOURTEEN COUNTIES HAVE NO COUNTY GOVERNMENT.** Massachusetts abolished the county
governments of Berkshire, Essex, Franklin, Hampden, Hampshire, Middlesex, Suffolk and Worcester
between 1997 and 2000 and moved their duties to the state; their voters still elect a sheriff and
registers of deeds. Barnstable has a regional government (an elected board of regional
commissioners and an assembly of delegates), Bristol, Dukes, Norfolk and Plymouth elect county
commissioners, and Nantucket's town select board serves as its county commissioners. The County
card says which form the county has and names nobody yet (gap `ma-county-officials`); nor is any
city or town official named (gap `ma-municipal-officeholders`).

**TRIBAL LAND IS NOT DRAWN YET.** The Census keeps two trust lands in Massachusetts, the
Wampanoag-Aquinnah Trust Land (about 2.0 km2) and the Mashpee Wampanoag Trust Land (about 1.3
km2), and the Hassanamisco state reservation (0.02 km2), measured 2026-11-12 with
`scripts/tribal_areas.py --report Massachusetts`. The state is recorded as not yet covered in
`data/tribal-government-join.json`.

**THE ZIP LAYER HIDES OUTSIDE MASSACHUSETTS.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The five TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** lists the six officers Massachusetts elects statewide (the
governor, lieutenant governor, attorney general, secretary of the commonwealth, treasurer and
receiver general, and state auditor) and both U.S. senators, from
`ma/data/source/statewide-officials.source.json` through `scripts/build_statewide_officials.py`.
**ONLY THE TREASURER IS NAMED TODAY.** `www.mass.gov`, where the governor's, lieutenant governor's,
attorney general's and auditor's pages are, answered this project's token and the browser client
alike with HTTP 403 from the build sandbox on 2026-11-12, so those four are listed without a name
until a run can read the page; whether a GitHub runner reaches it is the weekly name check's
question. The Secretary of the Commonwealth's site answered with an Incapsula challenge, an access
control that is never answered or worked around, so that office is linked and never read.

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

- Metro: Massachusetts (`massachusetts`) — https://districtry.com/ma/
- Geocoders: address Photon (Massachusetts-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Massachusetts-bounded, serial >=1s queue)
- Ground truth: 42.35866,-71.06363 (Massachusetts State House, 24 Beacon Street, Boston, Suffolk County) → county Suffolk County; us-house 8; ma-senate Third Suffolk; ma-house 8th Suffolk. Negative point 41.95000,-69.70000 (The Atlantic about 15 km east of Cape Cod's outer shore at Wellfleet — outside Massachusetts and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here (control: the State Capitol returns Massachusetts), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any of the other batch-3 states' outlines. IT IS OPEN WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 12 registered (political 3, safety 2, schools 3, geography 4); `registerLayer(` floor 10. Debug namespace `window.MassachusettsExplorer`.
- Scheduled workflows: `update-ma-congress-roster.yml` (Mon 22:07 UTC); `update-ma-legislature-roster.yml` (Tue 22:07 UTC); `ma-validate-sources.yml` (1st of month 23:13 UTC).
- Source registry: `ma/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ma/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ma/ node ma/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ma/scripts/validate_index.py ma/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 ma/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in ma/metro-worksheet.json;
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
which vendors Leaflet into `ma/scripts/vendor/leaflet/` (gitignored);
`ma/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Massachusetts-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the U.S. House and both chamber layers use the fenced factory helper `registerIlgaChamber` (the two chambers with its `namedDistricts` option), the County, City or Town and three school cards are bespoke `registerLayer` blocks, and the three nearest-N layers `registerNearestPointLayer`. Two invariants pervade the
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
`ma/scripts/build_metro_outline.py`), `state-counties.json` (`ma/scripts/build_state_counties.py`),
and `congress-districts.json`, `ma-senate-districts.json` and `ma-house-districts.json`
(`ma/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance ma`; 88,207 populated
blocks holding all 7,029,917 people the 2020 census counted in Massachusetts). The congressional map is held to that count; the two chambers are not, because their districts are named rather than numbered and the driver keys numbered districts, so their partition is held by the boundary builder's own 2,000-point gate. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 537 ZIP codes). Rosters:
`congress-roster.json` (`ma/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`ma-senate-members.json` and `ma-house-members.json` (`ma/scripts/build_ma_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs — and `statewide-officials.json`
(`scripts/build_statewide_officials.py`, from `ma/data/source/statewide-officials.source.json`).
`scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `ma/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
