# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Maine: a single-file, dependency-light web app. Click a point in Maine
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/me/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
fifth state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `me/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own pages: **County** (`county`, all 16, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (2 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Maine Senate** and **Maine House** (35 and 151 districts, TIGERweb's 2026 state legislative districts joined to the Legislature's own member lists), the TIGERweb fabric drawn from mirrored tile archives — **Town or City** (`municipality`, 529 county subdivisions), **School District (Unified)**, **(Elementary)** and **(Secondary)** and **ZIP Code** — three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**) and **Tribal Government** (`tribal-government`, the Census's tribal land, joined to the government that holds it).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `me/scripts/build_metro_outline.py --check` holds it to 16
INSIDE anchors, one per county, and 12 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN MAINE IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 2 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `me/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, 35 Senate and 151 House districts.
Measured 2026-11-12, every district in both chambers is the same as in TIGERweb's 2024 layers (5 and 6), intersection-over-union 1.0. The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage
rolls, and there is no nesting rule between the chambers (a House district's largest share
inside one Senate district is as low as 0.37 of its area), so each map is simplified on its own,
Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN PAGES** (`me/scripts/build_me_legislature_roster.py`).
The House's own export of its sitting members (`legislature.maine.gov/house/Home/ExportActiveMembers?format=csv`)
gives each representative's name, party ("Democrat", "Republican" or "Unenrolled", Maine's word for a
member enrolled in no party), district, e-mail address at legislature.maine.gov and one telephone, which
it labels with nothing; measured 2026-11-12 it held 150 members for 151 districts, and District 46, which
had no row, gets a record naming nobody. The export also carries each member's residence, city and ZIP
code, **and none of them is read**. The Senate's page "Senators" lists each senator and links the
senator's own page, which prints the district and an e-mail address; all 35 that day. The senators'
"State House" telephone is the Senate's office line, printed for many senators, so it is not carried.
robots.txt read 2026-11-12: no rule matches the pages and no Crawl-delay is stated; the host is paced at
one request a second.

**EVERY PART OF MAINE'S LAND IS IN A TOWN, A CITY, A PLANTATION, AN UNORGANIZED TERRITORY, A GORE OR A
RESERVATION**, and the Census files each as a county subdivision, so the **Town or City** layer is
TIGERweb's county subdivisions (layer 1). Measured 2026-11-12 across the 529 records: 430 towns, 23
cities, 29 plantations (a smaller form of local government run by elected assessors), 42 unorganized
territories, one gore and four reservation records (the Passamaquoddy Tribe's and the Penobscot
Nation's). An unorganized territory or a gore has no local government of its own and a reservation is
governed by its tribe, so their cards say that instead of naming a town government. No select board,
council or mayor is named yet (gap `me-municipal-officeholders`).

**THREE SCHOOL LAYERS.** Measured 2026-11-12: 187 unified districts and 74 elementary districts, which
between them cover the state's land, and three secondary districts (Five Town, Moosabec and Mount
Desert), which run the higher grades over part of the elementary districts' ground, so a reader there is
in two districts at once. No school board member is named yet (gap `me-school-board-members`).

**NO COUNTY OFFICIAL IS NAMED YET**, and the card says so rather than leave a reader to assume the office
is empty. Each county is governed by an elected board of county commissioners and elects officers such
as a sheriff, a register of deeds and a judge of probate. Recorded as gap `me-county-officials`.

**TRIBAL GOVERNMENT DRAWS THE LAND OF FOUR NATIONS AND NAMES NO COUNCIL YET** (`tribal-areas.json`,
since 2026-11-13). The Census keeps four reservations and four trust lands in Maine, measured
2026-11-12 with `scripts/tribal_areas.py --report Maine`: the Indian Township (115.1 km2), Penobscot
(57.8 km2), Houlton Maliseet and Pleasant Point reservations, and the Passamaquoddy (391.7 km2),
Penobscot (391.2 km2), Aroostook Band of Micmac and Houlton Maliseet trust lands. All eight pieces
are drawn, each joined in `data/tribal-government-join.json` to the government the Bureau of Indian
Affairs lists for it. The Bureau lists the Passamaquoddy Tribe's two governments separately, at
Indian Township (Princeton) and at Pleasant Point (Perry), and each reservation is joined to its
own; the Passamaquoddy Trust Land is held for the tribe as a whole, so its card names both
governments, each with its seat and site, and carries no single link, as Oregon's card for Celilo
Village does. The Town or City card still names the two reservations the Census files as county
subdivisions, without their governments. No council is carried yet (`ROSTER_NOT_SOUGHT` in
`scripts/build_tribal_areas.py`), recorded in gap `me-tribal-government`.

**THE ZIP LAYER HIDES OUTSIDE MAINE.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The five TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the governor, the only officer Maine's voters elect statewide, and
both U.S. senators, from `me/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`. The secretary of state, attorney general and treasurer are
elected by the Legislature, so they are not listed. `www.maine.gov` answered this project's token with
HTTP 403 on its robots.txt and on the governor's page and served the browser client both (no rule
matching the page), which the seed records.

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

- Metro: Maine (`maine`) — https://districtry.com/me/
- Geocoders: address Photon (Maine-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Maine-bounded, serial >=1s queue)
- Ground truth: 44.30710,-69.78167 (Maine State House, 210 State Street, Augusta, Kennebec County) → county Kennebec County; us-house 2; me-senate 15; me-house 59. Negative point 43.50000,-69.40000 (the Gulf of Maine about 40 km off Pemaquid Point — outside Maine and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here, because it is open water (control: the Maine State House returns Maine), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any outline in the change that opens the last thirteen states. IT IS OPEN WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 13 registered (political 4, safety 2, schools 3, geography 4); `registerLayer(` floor 10. Debug namespace `window.MaineExplorer`.
- Scheduled workflows: `update-me-congress-roster.yml` (Wed 22:37 UTC); `update-me-legislature-roster.yml` (Thu 22:37 UTC); `me-validate-sources.yml` (2nd of month 22:37 UTC).
- Source registry: `me/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/me/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/me/ node me/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 me/scripts/validate_index.py me/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 me/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in me/metro-worksheet.json;
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
which vendors Leaflet into `me/scripts/vendor/leaflet/` (gitignored);
`me/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Maine-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`me/scripts/build_metro_outline.py`), `state-counties.json` (the counties, `me/scripts/build_state_counties.py`),
and `congress-districts.json`, `me-senate-districts.json` and `me-house-districts.json`
(`me/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m under an 8 m ceiling, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance me`; 30,548 populated blocks holding all 1,362,359 people the 2020 census counted in Maine). All three maps are held to that count; the worst districts are -0.001% (congress), +4.813% (Senate) and -4.924% (House) of the raw-census ideal. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 424 ZIP codes). Rosters:
`congress-roster.json` (`me/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`me-senate-members.json` and `me-house-members.json` (`me/scripts/build_me_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`me/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `me/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
