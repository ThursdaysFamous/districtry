# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry West Virginia: a single-file, dependency-light web app. Click a point in West Virginia
(or search an address) and it reports every civic district containing that point and who
represents you there. It will serve at **districtry.com/wv/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). **The instance
is DARK**: it has no `metros.json` entry and no `layer-concepts.json` column, and the deploy
excludes `wv/**`, so nothing is served. Adam's answers to the plan (2026-10-29, "all as
recommended") set when it opens: built now, published on or after 1 January 2027, after the
November 2026 election's winners take their seats, and only on his own "merge" of the go-live
change. Nothing anywhere may call the instance live before then.

**The layers** draw their shapes from a national publisher or the state, and name people from a
national roster or the state's own publications: **County** (`county`, 55, Census TIGERweb, the
state outline the coverage wash covers, and the card that names the county commission and the
other elected county officers), **U.S. House** (2 districts, TIGERweb geometry joined to the
public-domain unitedstates/congress-legislators roster), **West Virginia Senate** and **House of
Delegates** (17 and 100 districts, the Legislature's own files of the 2021 plans joined to each
chamber's own roster), **Magisterial District** (`county-subdivision`, 195, the state's own map,
shown under the County layer), the live TIGERweb fabric — **City, Town or Village**
(`municipality`, 229), **School District** (`school-district-unified`, 55, one per county) and
**ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**,
**Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (the Louisiana and
Mississippi shape, `coverage_key` with `outside` and `edge` only). Precincts, when they come, are
a layer that hides outside the 29 counties whose current precinct maps are confirmed (Adam's
answer of 2026-10-29); they do not make a second tier.

**THE CONGRESSIONAL MAP IS THE 2021 MAP AND DOES NOT SWITCH ON 3 JANUARY 2027.** West Virginia
drew two districts in October 2021 and has not drawn them again; TIGERweb's layer 4 (119th
Congress) and layer 0 (120th) carry the same two districts for the state (measured 2026-10-29,
IoU 1.0 each, and both match the Legislature's own file of the plan). The builder refuses if the
two layers ever disagree for West Virginia, so a redraw is read by a person before it is drawn.

**THE TWO CHAMBERS ARE THE LEGISLATURE'S OWN PLAN FILES, NOT TIGERweb's, AND THAT IS A
MEASUREMENT.** TIGERweb's 2024 and 2026 House of Delegates layers put about 1.4 km2 of Harrison
County around Clarksburg in a different district than the enacted plan does (lowest district IoU
0.91441, District 70), while the state GIS centre's own map agrees with the plan to 99.9933%. So
the plan is drawn and the GIS centre's map is read on every build as a second witness
(`check_state_witness`, at least 99.5% of sampled points). Each map is simplified on its own
(Douglas-Peucker at 5 m under an 8 m ceiling), which is safe because 100 delegate districts do not
nest in 17 Senate districts.

**THE SENATE ELECTS TWO SENATORS PER DISTRICT, SO ITS CARD IS ITS OWN LAYER BLOCK.** Each of the 17
districts elects two senators in staggered four-year terms, and `registerIlgaChamber` renders one
member per district, so `wv-senate` is a bespoke `registerLayer` that names both, their Capitol
offices and both hover names. The roster record is `{"seats": 2, "members": [...]}` per district,
and `scripts/validate_chamber_rosters.py` holds it to two members per district. Half the seats
turn over in January 2027 (the 2026 election), which the weekly refresh picks up.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN ROSTERS** (`wvlegislature.gov` Senate and House
roster pages, `wv/scripts/build_wv_legislature_roster.py`): name, party, the member's page, the
Capitol room and telephone, and the member's own e-mail address. The Senate roster also prints each
senator's home county, which is not read. Every member's office must be in the Capitol at 1900
Kanawha Blvd. E., or the build refuses rather than ship an address that might be a home.

**THE COUNTY COMMISSION AND OFFICERS COME FROM THE SECRETARY OF STATE'S DIRECTORY OF COUNTY
OFFICIALS** (`apps.sos.wv.gov/elections/Officials/`, `wv/scripts/build_wv_county_officials.py`),
which the builder reads for the newest year that lists all 55 counties (2025 on 2026-10-29).
Each county has a three-member commission, five in Berkeley and Jefferson, every commissioner
elected by the whole county; no two may live in the same magisterial district, which is what the
Magisterial District layer is for. The directory also lists each county's board of education,
which is NOT read: board members change on 1 July of even years, so the 2025 list is out of date
(gap `wv-school-board-members`). An official's telephone or e-mail ships where the directory
prints it in that official's own entry, and one printed for two or more commissioners is the
commission's; an address ships only as the commission's office, where two or more commissioners
give it. Fax numbers never ship. The directory's `/search?` path is disallowed by sos.wv.gov's
robots.txt and is never read.

**THE MAGISTERIAL DISTRICTS ARE THE STATE'S OWN MAP**, the West Virginia GIS Technical Center's
"Magisterial 2026" layer (`services.wvgis.wvu.edu`, Boundaries/WV_Election_Layers, layer 9),
because only about 26 counties' Census subdivisions were plausibly current. Each district is keyed
by its county and name, because the layer's own district number is empty in two counties and
disagrees with the voter registration system's in a third. Drawing slivers and zero-width spikes
in the state's layer are removed before simplifying, and every run prints how many and how much
ground they held. **THE SAME SERVICE HOLDS A LAYER OF INDIVIDUAL VOTER LOCATIONS, IN ITS
Applications/WV_Election FOLDER. IT IS NEVER READ, BY ANY BUILDER, PROBE OR AGENT.**

**THE SCHOOL LAYER IS ONE PER COUNTY.** TIGER holds 55 unified districts for West Virginia and no
elementary or secondary ones, so one layer covers the state. No board member is named yet.

**THE ZIP LAYER HIDES OUTSIDE WEST VIRGINIA.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped
outline, and the smoke test asserts both halves.

**CITY WARDS WAIT ON FOUR LETTERS.** Charleston, Huntington, Parkersburg and Wheeling were asked
for their ward maps on 2026-10-21 (recorded in `docs/ASK_DRAFTS.md`); Charleston passed its letter
to the City Clerk. Adam's answer was to launch naming every council member and add the wards as
the files arrive. Until then city and town officials are gap `wv-municipal-officeholders` and the
wards gap `wv-city-wards`.

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

- Metro: West Virginia (`westvirginia`) — https://districtry.com/wv/
- Geocoders: address Photon (West Virginia-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, West Virginia-bounded, serial >=1s queue)
- Ground truth: 38.33650,-81.61230 (West Virginia State Capitol, 1900 Kanawha Boulevard East, Charleston, Kanawha County) → county Kanawha County; us-house 1; wv-senate 8; wv-house 54. Negative point 39.55000,-79.25000 (Garrett County, Maryland, about 20 km east of the West Virginia line at Preston County — outside West Virginia and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-29: TIGERweb's state and county layers name Maryland and Garrett County here (control: the State Capitol returns West Virginia and Kanawha County), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does. A POINT ON A NEIGHBOUR'S LAND WILL HAVE TO MOVE THE DAY THAT NEIGHBOUR GOES LIVE: Kentucky is live already, and Maryland, Pennsylvania, Ohio and Virginia are not, so the change that makes Maryland live moves this point, the way Kentucky's go-live moved Indiana's.).
- Layers: 11 registered (political 3, safety 2, schools 1, geography 5); `registerLayer(` floor 10. Debug namespace `window.WestVirginiaExplorer`.
- Scheduled workflows: `update-wv-congress-roster.yml` (Mon 19:53 UTC); `update-wv-legislature-roster.yml` (Tue 19:53 UTC); `update-wv-county-officials.yml` (Wed 19:53 UTC); `wv-validate-sources.yml` (1st of month 21:43 UTC).
- Source registry: `wv/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/wv/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/wv/ node wv/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 wv/scripts/validate_index.py wv/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 wv/scripts/build_metro_outline.py --check

# County officials and magisterial districts (offline: the shipped files' shape):
python3 wv/scripts/build_wv_county_officials.py --check
python3 wv/scripts/build_wv_magisterial_districts.py --check

# Generated-region gate: per-instance facts live ONCE in wv/metro-worksheet.json;
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
which vendors Leaflet into `wv/scripts/vendor/leaflet/` (gitignored);
`wv/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything West Virginia-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the U.S. House and House of Delegates layers use the fenced factory helper `registerIlgaChamber`
(which renders a vacancy record as a vacant seat with its reason and source), the Senate a bespoke
block for its two members per district, the TIGERweb layers `registerPolygonLayer` or a bespoke
block, and the three nearest-N layers `registerNearestPointLayer`. The County card is a bespoke
`registerLayer` block that reads the county-officials roster. Two invariants pervade the code: the
**stale-async guard** (`if (seq !== state.sequence) return;` after every await) and **per-layer
failure isolation** (a layer's failure shows a Retry inside its own card, never breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name. The chamber
cards degrade to the district number + the chamber's own member list on a roster miss, and a
vacant seat says it is vacant; the school-district, magisterial and municipality cards carry no
roster and **say so on the card**. External strings always render through
`sanitize()`/`textContent`. Roster refreshes always land as PRs for review — never as direct
commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`wv/scripts/build_metro_outline.py` — one INSIDE anchor per county plus OUTSIDE anchors in the
five neighbouring states), `state-counties.json` (`wv/scripts/build_state_counties.py`),
`congress-districts.json`, `wv-senate-districts.json`, `wv-house-districts.json`
(`wv/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, refused unless BOTH the
2,000-random-point agreement gate and the 8 m fidelity ceiling pass), and
`wv-magisterial-districts.json` (`wv/scripts/build_wv_magisterial_districts.py`, the same two
gates). Rosters: `congress-roster.json` (`wv/scripts/build_congress_roster.py`, from
unitedstates/congress-legislators), `wv-{senate,house}-members.json`
(`wv/scripts/build_wv_legislature_roster.py`) and `wv-county-officials.json`
(`wv/scripts/build_wv_county_officials.py`) — all count-guarded, all refreshed weekly by CI as
reviewed PRs.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `wv/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
