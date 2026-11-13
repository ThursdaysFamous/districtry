# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Utah: a single-file, dependency-light web app. Click a point in Utah
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/ut/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
seventh state of batch 3 of the state-level launch Adam asked for on 2026-11-10 (Massachusetts, Colorado, Maryland, Alabama, Oregon, Connecticut, Utah, Kansas),
in his chosen order: built dark, with the deploy excluding `ut/**`, and opened with the rest of its
batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own data: **County** (`county`, all 29, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (4 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Utah Senate** and **Utah House** (29 and 75 districts, TIGERweb's 2026 state legislative districts joined to the Legislature's own member file), the TIGERweb fabric drawn from mirrored tile archives — **City or Town** (`municipality`, 255 incorporated places), **School District** (41) and **ZIP Code** — three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**) and **Tribal Government** (`tribal-government`, the Census's tribal land, joined to the government that holds it).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `ut/scripts/build_metro_outline.py --check` holds it to 29
INSIDE anchors, one per county, and 14 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP IS THE ONE THE SITTING MEMBERS WERE ELECTED FROM, TIGERweb LAYER 4 (THE
119TH CONGRESS), UNTIL 3 JANUARY 2027.** Utah's map changed for the 120th Congress, which the
November 2026 election used (layer 0). Measured 2026-11-12: all 4 districts differ between the two (District 2 at an intersection-over-union of 0.008, District 1 at 0.010, District 4 at 0.148 and District 3 at 0.553), so the two are not
interchangeable. `ut/scripts/build_legislative_boundaries.py` refuses to build layer 4 on or after
3 January 2027; the change that day switches it to layer 0 and `CD120`, a person's step, because the
cards then name the members elected in 2026.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2).**
Measured 2026-11-12 against the 2024 vintage (layers 5 and 6): 27 of the 29 Senate districts identical and two different by slivers (District 8 at an intersection-over-union of 0.9974 and District 10 at 0.9987), and 73 of the 75 House districts identical while two differ (District 20 at 0.9889 and District 21 at 0.9981). The newer vintage is drawn. The builder refuses if a layer's name changes, since TIGERweb renumbers its
layers when a vintage rolls, and there is no nesting rule between the chambers (a House district's largest share inside one Senate district is as low as 0.38 of its area), so each map is simplified on its own, Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN MEMBER FILE** (`le.utah.gov/data/legislators.json`,
the file the Senate's and House's own member pages read, `ut/scripts/build_ut_legislature_roster.py`):
each member's name, party, e-mail address at le.utah.gov, page, and up to three telephones the file
prints beside them (cell, work and home), which ship with their labels under the fleet's rule of
2026-10-17; one number printed under several labels ships once with every label. Measured
2026-11-12: all 29 senators and 74 of the 75 House seats; House District 16 had no record, so its
card says no member is listed and gives the date. The party letter F is the Forward Party, which the
Senate's own page prints for the one senator carrying it. **EACH RECORD ALSO CARRIES AN `address`,
WHICH IS THE MEMBER'S HOME OR POST-OFFICE BOX, AND IT IS NEVER READ.** robots.txt read 2026-11-12:
its `*` group disallows `/ASP/`, `/asp/`, `/JSP/`, `/RSS/`, `/includes/`, `/templates/` and three
`/lfa/` paths and states a Crawl-delay of 10, which the shared `HostPacer` honours; `/data/` is
allowed. No path under the disallowed ones is ever fetched.

**MOST OF UTAH IS IN NO CITY OR TOWN.** The **City or Town** layer is TIGERweb's incorporated
places (layer 4): 255 records, 152 cities and 103 towns, every one an active government, about 3%
of the state's land (measured 2026-11-12). An empty card says the point is outside every city and
town and that the county is the local government there.

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 41 unified districts for Utah (county districts
and city districts) and nothing on its elementary or secondary layers (measured 2026-11-12), so
those two layers are not drawn. No school board member is named yet (gap `ut-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Each county is governed by an elected county commission, or by an
elected council where the county has adopted another form of government, and elects officers such
as a clerk, an assessor, a sheriff, an attorney and a treasurer. Recorded as gaps
`ut-county-officials` and `ut-municipal-officeholders`.

**TRIBAL GOVERNMENT DRAWS THE LAND OF SEVEN NATIONS AND NAMES NO COUNCIL YET** (`tribal-areas.json`,
since 2026-11-13). The Census keeps seven reservations in Utah (the largest the Uintah and Ouray
Reservation, about 17,671 km2) and two off-reservation trust lands, measured 2026-11-12 with
`scripts/tribal_areas.py --report Utah`, and all nine pieces are drawn, each joined in
`data/tribal-government-join.json` to the government the Bureau of Indian Affairs lists for it.
Three reservations cross the state line and are drawn whole: the Navajo Nation's (8.9% of it in
Utah, about 5,189 km2), seated in Window Rock, Arizona, whose card names the nine tribal
subdivisions the Census draws on its Utah ground; the Goshute (42% in Utah); and the Ute Mountain
(1.3% in Utah), seated in Towaoc, Colorado. The Bureau lists no office town for the Confederated
Tribes of the Goshute Reservation, so its card gives the one the tribe's own site gives, Ibapah,
says where it came from, and links that site, as Nevada's card for the same land does
(`seatFromNation`). Drawn whole, the Navajo Nation made the file 2.17 MB, so the land goes through
one Douglas-Peucker run at 3 m, Arizona's setting, and is 915 KB (240 KB gzipped), the worst stray
3.3 m against a 25 m ceiling (`SIMPLIFY` in `scripts/build_tribal_areas.py`). No council is carried
yet (`ROSTER_NOT_SOUGHT`), recorded in gap `ut-tribal-government`.

**THE ZIP LAYER HIDES OUTSIDE UTAH.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the five officers Utah elects statewide (the governor,
lieutenant governor, attorney general, state auditor and state treasurer) and both U.S. senators,
from `ut/data/source/statewide-officials.source.json` through `scripts/build_statewide_officials.py`.
Utah has no secretary of state; the lieutenant governor oversees its elections.

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

- Metro: Utah (`utah`) — https://districtry.com/ut/
- Geocoders: address Photon (Utah-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Utah-bounded, serial >=1s queue)
- Ground truth: 40.77749,-111.88800 (Utah State Capitol, 350 State Street, Salt Lake City, Salt Lake County) → county Salt Lake County; us-house 1; ut-senate 8; ut-house 22. Negative point 41.45000,-110.90000 (Uinta County, Wyoming, north of Evanston and about 12 km east of the Utah line — outside Utah and inside permalink_gate, so the app answers a selection there and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names Wyoming here (control: the State Capitol returns Utah), and none of the state's shipped boundary files contains it. WYOMING'S OUTLINE HAS COVERED THIS POINT SINCE THE CHANGE THAT PUBLISHED WYOMING (batch 4 of the state-level launch, written 2026-11-12), which found it inside Wyoming's outline in fleet-outlines.json and no other, AND THE POINT STAYS: measured that day on a 0.05-degree grid, no ground in this app's gate lies more than 2 km from every outline in fleet-outlines.json, so there is nowhere left to move it to. It is still outside Utah and outside every shipped boundary file, which is all the checks that boot on it or select it ask, and a selection the app makes itself never leaves; the click that had to stay here became a Wyoming routing case in the same change, and the click-stays-here check went with it, the way Kentucky's and Tennessee's points stayed put once every neighbour was served.).
- Layers: 11 registered (political 4, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.UtahExplorer`.
- Scheduled workflows: `update-ut-congress-roster.yml` (Mon 23:19 UTC); `update-ut-legislature-roster.yml` (Tue 23:19 UTC); `ut-validate-sources.yml` (1st of month 23:49 UTC).
- Source registry: `ut/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ut/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ut/ node ut/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ut/scripts/validate_index.py ut/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 ut/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in ut/metro-worksheet.json;
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
which vendors Leaflet into `ut/scripts/vendor/leaflet/` (gitignored);
`ut/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Utah-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`ut/scripts/build_metro_outline.py`), `state-counties.json` (`ut/scripts/build_state_counties.py`),
and `congress-districts.json`, `ut-senate-districts.json` and `ut-house-districts.json`
(`ut/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance ut`; 46,792 populated
blocks holding all 3,271,616 people the 2020 census counted in Utah). All three maps are held to that count; the congressional map sits within 0.001% of its ideal, and the worst legislative districts are -1.880% (Senate) and -4.637% (House). The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 299 ZIP codes). Rosters:
`congress-roster.json` (`ut/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`ut-senate-members.json` and `ut-house-members.json` (`ut/scripts/build_ut_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs — and `statewide-officials.json`
(`scripts/build_statewide_officials.py`, from `ut/data/source/statewide-officials.source.json`).
`scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `ut/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
