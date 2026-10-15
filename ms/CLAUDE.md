# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Mississippi: a single-file, dependency-light web app. Click a point in Mississippi (or
search an address) and it reports every civic district containing that point and who represents
you there. It serves at **districtry.com/ms/** as a folder of the consolidated districtry repo —
following the Wisconsin/Iowa shape (`docs/EXPANSION_GUIDE.md` Part 2), not the Illinois
root-scripts shape. **The instance is DARK**: no `metros.json` entry, `ms/**` excluded from the
Pages deploy, nothing served and no landing card naming it. `ms/WATCH.md` lists what go-live has to
do in one change.

**The national tier** draws its shapes from a national publisher and names people from a national
roster or the Mississippi Legislature: **County** (82, Census TIGERweb, the coverage ring, and the
card that names the county's five supervisors), **U.S. House** (4 districts, TIGERweb geometry
joined to the public-domain unitedstates/congress-legislators roster), **Mississippi Senate** and
**Mississippi House** (52 and 122 districts, TIGERweb geometry joined to the legislature's own
member gallery and member profiles), the LIVE TIGERweb fabric — **City, Town or Village**
(`municipality`, 300), **School District** (137) and **ZIP Code** — and three nearest-N layers from
the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**). Beside it,
**County Supervisor District** (`county-supervisor`) draws the five districts of each of the 12
counties whose current lines are confirmed, and is hidden in the other 70.

**THE CONGRESSIONAL MAP IS TIGERweb LAYER 0, AND THAT WAS MEASURED RATHER THAN ASSUMED.** Layer 0
is the 120th Congress's map, which is wrong for a state that redrew for 2026 (North Carolina,
Tennessee, Louisiana). Mississippi did not: its four districts in layer 0 and in layer 4 (the
119th) carry the same GEOIDs and identical land areas (2026-10-15).

**THE LEGISLATURE MAPS ARE THE 2025 COURT-ORDERED REDRAW.** A federal court ordered some of the
2022 districts redrawn under the Voting Rights Act, and the redrawn districts were used for special
elections on 4 November 2025: nine Senate districts (1, 2, 11, 19, 34, 41, 42, 44, 45) and five
House districts (16, 22, 36, 39, 41) moved. TIGERweb's 2026 legislative layers carry the redrawn lines, so the
national tier is current; a later redraw would need this re-measured.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN PAGES, AND TWO OF ITS OWN FILES ARE STALE.** The
member gallery on `www.legislature.ms.gov` shows one card per seat, and a seat nobody holds is a
card reading "Vacant" (Senate 34, House 70 and 77 on 2026-10-15); each member's profile names the
party, the official `@senate.ms.gov` or `@house.ms.gov` address, and the Capitol office. The
legislature's own member XML files on `billstatus.ls.state.ms.us` still list members who have left,
so they are not read. **THE PROFILES ALSO PRINT A HOME ADDRESS, A PERSONAL TELEPHONE AND SOMETIMES
A PERSONAL E-MAIL ADDRESS, AND THE BUILDER NEVER READS THEM**: only an address on the chamber's own
domain is carried, and the office printed is the Capitol's. **THE HOST SENDS ONLY ITS OWN
CERTIFICATE AND NOT THE INTERMEDIATE THAT SIGNED IT**, so a client that does not fetch missing
intermediates fails to connect; the builder pins the GlobalSign intermediate through
`scripts/aia_bundle.py` rather than turning verification off.

**THE COUNTY BOARD IS A BOARD OF SUPERVISORS, AND ITS PEOPLE AND ITS LINES COME FROM DIFFERENT
PLACES.** Every county elects five supervisors, each from a district (some counties call them
"beats"). The Secretary of State's County Offices and Directory (2026 edition) names all 410 by
district, so every County card lists its board. The Census carries the district lines as county
subdivisions — all 410 are nonfunctioning (FUNCSTAT N) and they ARE the supervisor districts — but
in 70 counties the Census's 2026 layer still carries its own 2020 edition, the lines drawn on the
2010 census — the planning measurement found those put 34% of Madison County's residents in the
wrong district, 16% of Lee's and 9.5% of Harrison's. So a supervisor district is drawn only where
its current lines are confirmed (Adam's choice, "Confirmed only", on the decision card of
2026-10-15), and the rest is gap `ms-supervisor-district-lines`. **THE
DIRECTORY ALSO PRINTS SUPERVISORS' OWN ADDRESSES AND TELEPHONES IN SOME COUNTIES**, which may be
homes: a board address or telephone is carried only where at least three of the five supervisors
print the same one, because five people do not share a home — 76 counties have an address and 68 a
telephone on the 2026 edition, and Amite, Coahoma, Humphreys, Lincoln, Sunflower and Yalobusha,
which print a different address for each supervisor, have none. No supervisor's own line and
nothing printed for the election commissioners is ever carried.

**A COUNTY'S SUPERVISOR DISTRICTS ARE DRAWN ONLY WHEN TWO MEASUREMENTS AGREE, AND TWELVE PASS**
(`ms/scripts/build_ms_supervisor_districts.py`, its `--check` in CI). Its Census lines changed
after the 2020 census, counted in PEOPLE whose district number moved rather than in area — Clay's
change covers 0.07% of the county and moves 689 people — AND its five districts hold nearly equal
numbers of people on the 2020 census's own blocks, within 10% of an equal share. Measured
2026-10-15 over all 82 counties: twelve pass at 3.2% to 9.0% (Choctaw, Clay, DeSoto, Grenada,
Lawrence, Lowndes, Neshoba, Noxubee, Oktibbeha, Tate, Webster, Winston), and their old lines
measured 15.6% to 85.6% on the same blocks. **SIX COUNTIES CARRY THE OLD EDITION AND BALANCE ANYWAY,
AND ARE NOT DRAWN** — Lafayette, Marshall, Montgomery, Jefferson Davis, Walthall and Marion — because
a balanced old map may have been kept or redrawn without telling the Census, and no measurement
here can tell which; the county's own map or its answer to a letter settles one. `--survey`
re-takes both measurements for every county and marks one that newly passes, which a person adds
to `CENSUS_COUNTIES` after looking. **THE LAYER'S COVERAGE TEST READS THE LAYER'S OWN FILE**, so a
reader's first selection downloads it even with the layer off — 83 KB gzipped for twelve counties.
Past about 150 KB, give it a coverage file of its own or tiles. **The shapes are the county
outline's too**: `state-counties.json` was rebuilt with Douglas-Peucker on 2026-10-15 because
the Visvalingam simplification it shipped with put a county line up to 184.5 m from the
Census's, with 54 counties over 25 m, and the supervisor builder's county witness holds the two
files to each other at 4,000 points.
**THE DIRECTORY PRINTS MOST COUNTY NAMES AS ARTWORK, NOT TEXT.** 80 of its 82 county pages carry
the county's name as an image, so the builder finds the 82 start pages (each opens with "Named
for"), pairs them with the 82 counties in alphabetical order, and refuses to write unless there are
exactly 82, the two pages that do print the name as text (Adams and Humphreys) agree, and at least
62 of the "Named for" lines contain the name of the county the pairing gives them (68 did in 2026 —
"Named for President John Adams" on Adams County's page). A new edition that breaks any of those
stops the weekly run, and a person reads the PDF.

**ONE SCHOOL LAYER, LABELLED WITHOUT A QUALIFIER.** TIGER's unified tiling holds 137 districts for
Mississippi and its elementary and secondary tilings hold none, and the unified districts' land
area sums to the 82-county total (121,535 km²) — so the layer is "School District", and its id
stays `school-district-unified` because a layer id is a public address.

**THE ZIP LAYER HIDES OUTSIDE MISSISSIPPI.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP (the Alabama negative point gives 36925,
measured 2026-10-15). The coverage test reads the shipped outline, and the smoke test asserts both
halves.

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

- Metro: Mississippi (`mississippi`) — https://districtry.com/ms/
- Geocoders: address Photon (Mississippi-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Mississippi-bounded, serial >=1s queue)
- Ground truth: 32.30380,-90.18220 (the State Capitol, Jackson, Hinds County) → county Hinds County; us-house 2; ms-senate 29; ms-house 67. Negative point 32.48000,-88.25000 (near York, Sumter County, ALABAMA, about 12 km east of the Mississippi line — outside Mississippi and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-15: TIGERweb's county layer names Sumter County, Alabama at this point (control: the Capitol anchor returns Hinds County, Mississippi), and the Census's ZIP layer answers 36925 there, which is the neighbouring-state answer the ZIP layer's coverage test exists to hide. ALABAMA BECAUSE NO INSTANCE SERVES IT and it is not on the next-states list; Louisiana, Arkansas and Tennessee, which share Mississippi's other borders, were passed over so this point does not have to move when any of them is live.).
- Layers: 11 registered (political 4, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.MississippiExplorer`.
- Scheduled workflows: `update-ms-congress-roster.yml` (Mon 18:11 UTC); `update-ms-legislature-roster.yml` (Tue 18:11 UTC); `update-ms-county-officials.yml` (Wed 18:11 UTC); `ms-validate-sources.yml` (1st of month 20:13 UTC).
- Source registry: `ms/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ms/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ms/ node ms/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ms/scripts/validate_index.py ms/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 ms/scripts/build_metro_outline.py --check

# Supervisor districts (offline: build record, directory seats, the Census edition
# the card names, and the County layer at 4,000 points):
python3 ms/scripts/build_ms_supervisor_districts.py --check

# Generated-region gate: per-instance facts live ONCE in ms/metro-worksheet.json;
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
which vendors Leaflet into `ms/scripts/vendor/leaflet/` (gitignored);
`ms/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Mississippi-specific lives in the `METRO:BEGIN config` block (worksheet-generated) and
this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
this instance's three chamber layers use the fenced factory helper `registerIlgaChamber` (the
generic chamber factory both state chambers and the U.S. House card use, which renders a
vacancy record as a vacant seat with its reason and source), and the three nearest-N layers use
`registerNearestPointLayer`. Two invariants pervade the code: the **stale-async guard**
(`if (seq !== state.sequence) return;` after every await) and **per-layer failure isolation**
(a layer's failure shows a Retry inside its own card, never breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name. Both chamber
cards degrade to the district number + the legislature's own member list on a roster miss, and
a vacant seat says it is vacant; the school-district and municipality cards carry no roster at all
and **say so on the card**. External strings always render through `sanitize()`/`textContent`.
Roster refreshes always land as PRs for review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`ms/scripts/build_metro_outline.py` — one INSIDE anchor per county plus OUTSIDE anchors in
Alabama, Tennessee, Arkansas and Louisiana), `state-counties.json`
(`ms/scripts/build_state_counties.py`, Douglas-Peucker, refused unless the 25 m fidelity ceiling
passes), `ms-supervisor-districts.json` (`ms/scripts/build_ms_supervisor_districts.py`, the 12
confirmed counties, one mapshaper run so a shared line is simplified once), and
`congress-districts.json`, `ms-senate-districts.json`,
`ms-house-districts.json` (`ms/scripts/build_legislative_boundaries.py` — statewide TIGERweb,
mapshaper-simplified with Douglas-Peucker, refused unless BOTH the 2,000-random-point agreement gate
and the 25 m fidelity ceiling pass). Rosters: `congress-roster.json`
(`ms/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`ms-{senate,house}-members.json` (`ms/scripts/build_ms_legislature_roster.py`, from the
legislature's own pages) and `ms-county-officials.json` (`ms/scripts/build_ms_county_officials.py`,
from the Secretary of State's directory) — all count-guarded, all refreshed weekly by CI as
reviewed PRs. `scripts/validate_chamber_rosters.py` holds both chamber files to one record per
seat.

robots.txt is read before the first fetch through `scraper_common.require_robots_once`, with the
same client the fetches send.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `ms/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
