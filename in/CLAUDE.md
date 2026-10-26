# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Indiana: a single-file, dependency-light web app. Click a point in Indiana (or
search an address) and it reports every civic district containing that point. It serves at
**districtry.com/in/** as a folder of the consolidated districtry repo — following the
Wisconsin/Iowa/Michigan shape (`docs/EXPANSION_GUIDE.md` Part 2), not the Illinois
root-scripts shape. It ships SEVENTEEN layers, all but five from a national publisher: the county
council districts and the voting precincts come from the state's mapping office, the Court of
Appeals districts group the Census's counties as the court's own district map does, the
Indianapolis Public Schools board districts come from the City of Indianapolis, and the
conservancy districts come from the Department of Natural Resources (all below).

**LIVE SINCE THE GO-LIVE CHANGE OF 2026-10-07**, eight days after it arrived dark: it is in
`metros.json`, `fleet-outlines.json`, the sitemap, the landing page and the coverage map, and
the deploy excludes only `in/data/state`, `in/scripts` and raw geojson. Its fleet `bbox` in
`metros.json` is CLIPPED to `minLat 37.83` rather than the state's own 37.77, and that is a
measurement: Kentucky's `metro_center` is 37.82, -85.77, and `validate_index.py` refuses a
sibling's hand-off box containing an instance's own centre. The clip leaves out 0.09% of the
state (a riverfront strip in Posey, Vanderburgh and Spencer counties), and no selection is
decided by the box any more — `fleet-outlines.json` decides — so the cost is confined to the
search box's sibling rows when that file cannot be read.

**The pre-built tier** — four TIGERweb layers shipped as same-origin files, which are what the
smoke test anchors on: **County** (92, identity-only), **U.S. House** (9, joined to the
public-domain unitedstates/congress-legislators roster and refreshed weekly), and **Indiana
Senate** / **Indiana House** (50 and 100).

**The live tier** — seven layers with no builder and no committed `data/app` file between them,
so a TIGERweb or USGS vintage roll reaches all seven on its own: **Township or City**
(`county-subdivision`, 1,012 — 1,004 of them civil townships), **City or Town**
(`municipality`, 566), **School District (Unified)** (291), **ZIP Code** (882 intersecting the
state) and the three USGS point layers, **Police Station**, **Fire Station** and **Post
Office**.

**ZIP CODE IS THE ONE LAYER HERE THAT DECLARES A COVERAGE TEST, AND IT HAS TO.** A ZCTA
carries no state field, so that layer alone cannot be fetched with `STATE='18'` and its point
query carries no state filter either — measured 2026-09-29 against in-state controls in the
same command, it answers 60602 in Chicago, 40202 in Louisville and 48226 in Detroit while
answering 46402 in Gary and 46204 at the Indianapolis anchor. Every other card here correctly
declines outside Indiana, so a real out-of-state ZIP was the one answer breaking that. It now
declares `insideIndiana`, tested against the shipped `metro-outline.json` (same-origin,
cache-first, no request), so outside the state the toggle, card and overlay hide. The smoke test
proves BOTH directions — hidden at the negative point, visible at the anchor — with the census
host refused, because a hide test alone would pass for a layer hidden everywhere. The lesson is
Minnesota's (PR #1274), whose negative point returned a North Dakota ZIP.

**INDIANA SHIPS ONE SCHOOL LAYER WHERE MICHIGAN SHIPS TWO, AND THAT IS A MEASUREMENT.**
TIGERweb's elementary (layer 1) and secondary (layer 2) school tilings both return **zero**
features for `STATE='18'` (measured 2026-09-29), so the state runs unified districts alone.
Both are recorded drops rather than empty toggles.

**THE COUNTY CARD NAMES BOTH COUNTY BODIES** (2026-10-09).
An Indiana county is run by TWO elected bodies — a three-member board of commissioners and a
seven-member county council (nine in St. Joseph) — and each is elected on its own district lines.
`in/scripts/build_in_county_officials.py` reads the Indiana Election Division's archived,
CERTIFIED general-election results (`enr.indianavoters.in.gov`, robots.txt answers 400, which
RFC 9309 files as no policy) and writes `in-county-commissioners.json` and
`in-county-councils.json`: the newest certified winner for every seat, 91 counties, 273
commissioners and 639 council members. **THEY ARE ELECTION WINNERS, NOT A ROSTER**, and the card
says so: a vacancy in Indiana is filled by a party caucus, which no election file records, so a
seat can name someone who has since left. A year counts only once it is certified and its
winners have taken office on January 1. **NINE RACES ARE MISFILED IN THE STATE'S OWN FILES** — a
district race published as electing several seats — and `MISFILED_SEAT_COUNTS` records each with
the winner the file flags, refusing the build if any moves; a few races are titled with no
district at all, and those seats print "Seat not stated" rather than a guessed number.
**MARION IS NOT IN THESE FILES**: Indianapolis and Marion County are consolidated, and its
legislative body is the 25-member City-County Council, elected in the MUNICIPAL general. Since
2026-10-11 Marion's card and county page read it from the city file below. The council file is recorded in `build_county_pages.py`'s
`NOT_COUNTY_BOARDS` (a county council is the FISCAL body, IC 36-1-2-6; commissioners are the
legislative and executive body), so the 91 per-county pages under `in/county-commissioner/` carry
the commissioners.

**THE COUNCIL DISTRICTS OF 60 COUNTIES ARE DRAWN** (55 on 2026-10-15, five more on 2026-10-26), as the County Council District
layer, from the Indiana Geographic Information Office's `CountyCouncilPolygon` layer and, for
Adams, Delaware, Porter, St. Joseph and Vigo, each county's own map layer (`OWN_SOURCES`; St. Joseph's
nine districts are lettered A to I, and Porter's outline runs into Lake Michigan, so its cover floor is 80%)
(`in/scripts/build_in_council_districts.py` → `in-council-districts.json`, 266 districts in 60 counties). Marion's
are the City-County Council's 25. The labels are free text ("CC1", "#1", "Area 1", "Indianapolis
001"), so only the number is read and each county must come out 1..4 (Marion 1..25); Noble's
three at-large features and a Boone sliver labelled "N.T." are recorded in `DROP_LABELS`, and Clay,
which files three of its four districts, is left out whole. Every district is clipped to the
county's outline in `state-counties.json`, so it always agrees with the County card. The card
names the district's own member and lists the at-large members apart; `--check` (run by the
weekly roster job) holds every drawn district to a seat of that name, and Boone's District 3,
whose race the results title "Dist 36", is recorded in `SEAT_NOT_NUMBERED` and named on no card.
Commissioner lines are not drawn: they are elected by the whole county, except in Lake and St.
Joseph, which the state's layers do not carry at all. Gap `in-county-government` records the 37
counties with no lines.

**THE CITY OR TOWN CARD NAMES THE MAYOR AND COUNCIL OF 36 OF THE 39 PLACES OVER 25,000**
(2026-10-11). `in/scripts/build_in_city_officials.py` reads the same archive's certified 2023
MUNICIPAL general (office categories 1002 mayor, 1032 city council, 1037 town council) and
writes `in-city-officials.json`, keyed by Census place id: every city over 25,000, Indianapolis's
City-County Council among them, and the towns of Merrillville and Zionsville. **THE PLACES ARE
STATED, NOT INFERRED**: `UNITS` names each place's races exactly as the results title them
("Ec Council 1", Kokomo's bare "City Council District 1", a mayor's race titled just "Mayor" in
a county with several cities, matched by its jurisdiction) and the district and at-large counts
the 2023 results carry, and the build fails if `UNITS` plus `TOWN_PAGES` stops equalling the
places `docs/expected-governments.json` counts. **THREE TOWNS ARE READ FROM THEIR OWN PAGES**: a
town holds no general election for an uncontested seat, so the results carry no Plainfield race
and only three wards each of Brownsburg and Schererville. Since 2026-10-15 `TOWN_PAGES` reads each
town's council page instead, each seat dated to the read rather than to an election, and the card
says the names are the town's own list. Plainfield's host refuses this project's token behind
Cloudflare and serves the stdlib client with a Chrome string and client hints (measured that day);
its robots.txt is read with that same client. New Albany's at-large race is filed as electing one and elects three
(`MISFILED_SEAT_COUNTS`). Council district lines are not drawn, so the card lists every seat.
Gap `in-municipal-officeholders` records the rest.

**ELECTION PRECINCTS ARE DRAWN SINCE 2026-10-15, FROM INDIANA'S 2026 PRECINCT MAP.**
`voting-precinct` draws all 5,121 precincts from IndianaMap's "Voting District Boundaries 2026",
which the Indiana Geographic Information Office published from data it obtained from the General
Assembly and the Indiana Election Division in June 2026. It is pre-built by
`in/scripts/build_in_precincts.py` through the fleet module `scripts/statewide_precincts.py` at
Douglas-Peucker 4 m (7.1 MB, 1.48 MB gzipped), so a click is answered from the file and no point
leaves the browser. The card names the precinct and its county, says a precinct elects no one,
says it is the 2026 map so a change a county made after June 2026 is not shown, states the 4 m,
and links the state's polling-place lookup. **EACH YEAR IS A NEW SERVICE**, at a new address with the year
in its field names (2010, 2023, 2024 and 2026 are in the catalogue, measured 2026-10-15; there is
no 2025), so the builder's `--watch` also lists the catalogue for a later edition, and the builder
refuses to build while the card names an edition other than the one it reads. The layer names no
licence and carries no county name, only a three-digit code, so the county comes from this
instance's own county file. Those two gaps and the yearly change of address are evidence for the
state-publishing ask. The quarterly re-check is in `in/WATCH.md`.

**THE COURT OF APPEALS' 1ST, 2ND AND 3RD DISTRICTS ARE DRAWN SINCE 2026-10-16, AND THE COUNTIES
WERE READ OFF A PICTURE.** `in-court-of-appeals` dissolves the county fabric this instance ships,
by `in/scripts/build_in_appeals_districts.py` through the fleet module
`scripts/whole_county_courts.py`. Three of the court's fifteen judges come from each of these
districts and stand for retention there alone, which the court's own districts page says; the 4th
and 5th Districts' judges stand for retention statewide, so they are not drawn. The Indiana Code
that assigns the counties is published only through a site that serves nothing to a reader that
does not run its scripts, robots.txt included, so the counties were read from the court's own
district map image, whose SHA-256 is recorded in `in/data/source/courts/`. Two guards make a
misread county stop the build: the pinned counts (53, 19 and 20) and the rule that each district
dissolves to one piece. The card says how the judges are chosen and retained, lists the district's
counties, names nobody (gap `in-court-of-appeals-judges`) and links the court's districts page.
THE TRIAL COURTS ARE NOT DRAWN: every judicial circuit is one county except the 7th, which Dearborn
and Ohio share (the Prosecuting Attorneys Council's list, citing IC 33-33, which was not read), so a
circuit map would redraw the county map. The annual re-check is in `in/WATCH.md`.

**THE INDIANAPOLIS PUBLIC SCHOOLS BOARD'S FIVE DISTRICTS ARE DRAWN SINCE 2026-10-16, AND NO OTHER
BOARD'S ARE.** `school-board-district` draws them from the City of Indianapolis and Marion County's
School Board Districts layer, pre-built by `in/scripts/build_in_school_board_districts.py` through
the fleet module `scripts/published_district_layers.py`. The same layer draws residence districts
for the Lawrence and Washington township boards, which are not drawn because the whole township
votes for every seat. Indiana publishes no statewide map of school board election districts, and
the 2022 and 2024 certified results point to about forty other boards electing some members by
district (gap `in-school-board-districts`). The card names nobody (gap `in-school-board-members`).
The layer states no licence. The quarterly re-check is in `in/WATCH.md`.

**CONSERVANCY DISTRICTS ARE DRAWN SINCE 2026-10-16, WITH THEIR BOARDS NAMED FROM THE STATE'S
DIRECTORY.** A conservancy district is a unit of local government a circuit court sets up, when
property owners petition, for flooding, drainage, sewers, water supply or a lake (IC 14-33); its
directors are elected by the property owners in the district. `conservancy-district` draws the 100
the Department of Natural Resources' map marks active (layer 54 of "Conservancy Districts of
Indiana"), pre-built by `in/scripts/build_in_conservancy_districts.py` through the fleet module
`scripts/published_district_layers.py`; they cover 8.0% of the state and some overlap, so the card
lists every district at the point. The boards come from the department's yearly Indiana
Conservancy District Directory, which each board's chair must keep current, read by
`in/scripts/build_in_conservancy_directors.py`: 465 people and 6 vacant seats across 93 districts
in the 2026 edition. Hired staff are left out and home towns are never carried. **A DIRECTOR'S OWN
TELEPHONE AND E-MAIL SHOW SINCE 2026-10-17**, on Adam's two rulings of that day that a number or an
address a government source prints beside one official is published: 145 people carry a number and
181 an address. One the directory prints beside two or more different people, or equal to the
district's own contact line, belongs to the district and is shown on no person, and the district's
own telephone and e-mail show above its board (86 and 83 districts). Six
districts sent no list and one is missing from the directory, so those cards name nobody (gap
`in-conservancy-district-records`). **THE MAP AND THE DIRECTORY DISAGREE, AND THE BUILDERS SAY
WHERE.** The directory gives four districts another district's id, so the join runs through a
table of corrections; the name and county each source gives a district must agree before a board
is attached; the map files Nature Works under a court whose county holds none of its land, so the
card names no court for it; one establishment date predates the 1947 act, so the card prints none;
and thirteen of the map's 35 website addresses reach nobody or the wrong place, so the card prefers
the directory's. Every correction table stops the build once its entry no longer applies, and all
of it is recorded in the gap as evidence for the state-publishing ask. The card and the hover use
the directory's name for a district, which differs from the map's for 21. The quarterly map check
and the yearly directory rebuild are in `in/WATCH.md`.

**NEITHER CHAMBER NAMES A PERSON.** This instance ships no General Assembly roster, so both
chamber cards give the district number and the Assembly's own directory — the chamber factory's
roster-miss path, which is the honest card until a roster is built. Recorded as gap
`in-general-assembly-roster`. Gap `in-school-board-members` covers the school cards, where the
Census carries geography and no officeholder field at all.

**THE TOWNSHIP CARD NAMES THE TRUSTEE AND BOARD OF MOST TOWNSHIPS** (2026-10-15).
`in/scripts/build_in_township_officials.py` reads the same archive's certified 2022 general
(office categories 1021 trustee and 1023 board member) and writes `in-township-officials.json`,
keyed by the county-subdivision layer's own Census id: 973 trustees and 921 boards across 987 of
the 1,004 civil townships. **THE MATCH IS STATED WHERE THE CENSUS AND THE RESULTS DISAGREE**:
`ALIASES` carries five townships the Census names differently (Hamilton's Adams Township is
recorded as "Sheridan town", and the results call Allen's St. Joseph Township "St Joe"), `SHARED` carries Johnson County's
one government for three townships, and `LEFT_OUT` two races filed under the wrong office; any
other race that matches no township, or more than one, fails the build. Marion's five-member
boards are not in that file, so its nine cards say no board race was found. Gap
`in-township-officers` records the 97 townships named only in part or not at all.

**There is no build step, no framework, and no server-side code.** The app — styles, engine,
and layer modules — lives inline in `index.html`. `sw.js` is the service worker;
`data/app/*.json` are runtime-fetched data files; `data/state/` carries the bootstrap state
config (`build_congress_roster.py` reads its FIPS/USPS/seat count — it ships in the repo and is
excluded from the Pages deploy). `sources.html` carries the generated per-layer provenance
matrix and `faq.html` the common questions; both compose from the same shared engine blocks as
every other instance via `scripts/compose_app.py`.

**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: Indiana (`indiana`) — https://districtry.com/in/
- Geocoders: address Photon (Indiana-bounded type-ahead); unbounded Photon (whole-coverage, sibling-metro lookup); POI Nominatim (office-address pin lookup, Indiana-bounded, serial >=1s queue)
- Ground truth: 39.76860,-86.16260 (the Indiana Statehouse, downtown Indianapolis (Marion County)) → county Marion County; us-house 7; in-senate 46; in-house 97; voting-precinct CN055; county-council 12; in-court-of-appeals 2. Negative point 38.25270,-85.75850 (downtown Louisville, Kentucky — south of the Ohio River, whose north bank is the Indiana line, and inside permalink_gate's minLat (37.60) so the point is still selectable; measured to miss all four ANCHOR layers (the live TIGERweb fabric layers are deliberately not anchors — an anchor must answer with the network down) KENTUCKY WENT LIVE ON 2026-09-30 AND NOW COVERS THIS POINT, so the two checks that put it at the map's CENTRE refused ../fleet-outlines.json until 2026-10-13, when panning stopped switching apps; neither refuses anything now, because a selection the app makes itself never leaves. The point itself is unchanged: it is still outside this instance and still misses all four anchor layers, and the gate reaches uncovered ground in Ohio if it ever needs to move. Check 1a2 is where this instance asserts fleet routing, and Louisville moved there from its uncovered case to a Kentucky routing case the same day.).
- Layers: 17 registered (political 6, safety 2, schools 2, geography 7); `registerLayer(` floor 13. Debug namespace `window.IndianaExplorer`.
- Scheduled workflows: `update-in-congress-roster.yml` (Mon 15:45 UTC); `update-in-county-officials.yml` (Wed 15:50 UTC).
- Source registry: `in/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/in/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/in/ node in/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 in/scripts/validate_index.py in/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 in/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in in/metro-worksheet.json;
# GENERATED regions are emitted from it. NEVER hand-edit a GENERATED region:
pip install -c scripts/requirements.txt jsonschema
python3 scripts/generate_metro_files.py            # regenerate in place (all instances)
python3 scripts/generate_metro_files.py --check    # the CI drift gate

# Engine parity: the ENGINE fences are composed from the repo-root engine/ —
# edit a block THERE and recompose, never inside an instance file:
python3 scripts/compose_app.py            # splice engine/ into every instance
python3 scripts/compose_app.py --check    # the CI drift gate
```

**Sandboxed environments (Claude Code web):** the headless browser cannot reach the Leaflet
CDN. The repo root's `.claude/settings.json` SessionStart hook runs `scripts/vendor_leaflet.sh`,
which vendors Leaflet into `in/scripts/vendor/leaflet/` (gitignored);
`in/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Indiana-specific lives in the `METRO:BEGIN config` block (worksheet-generated) and
this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

**This instance registers NO county-dispatched concept**, so it carries no
`county-layer-dispatcher` fence at all — the NYC/SF shape rather than Illinois's. When the first
county-level concept ships, the fence comes back in that change.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the three chamber-shaped layers use the fenced factory helper `registerIlgaChamber`. Two
invariants pervade the code: the **stale-async guard** (`if (seq !== state.sequence) return;`
after every await) and **per-layer failure isolation** (a layer's failure shows a Retry inside
its own card, never breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name. Nine of this
instance's fifteen layers name nobody (U.S. House, County, County Council District, City or Town,
Township or City and the tribal layer name people), and every one of their cards says so. External strings
always render through `sanitize()`/`textContent`. Roster refreshes always land as PRs for human
review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`in/scripts/build_metro_outline.py` — one INSIDE anchor per county, each verified interior
against that county's own rings), `state-counties.json` (`in/scripts/build_state_counties.py`),
and `congress-districts.json`, `in-senate-districts.json`, `in-house-districts.json`
(`in/scripts/build_legislative_boundaries.py` — statewide TIGERweb, mapshaper-simplified,
refused unless the 2,000-random-point agreement gate passes). The rosters are
`congress-roster.json` (`in/scripts/build_congress_roster.py`, from
unitedstates/congress-legislators), the two county files above
(`in/scripts/build_in_county_officials.py`) and the city file
(`in/scripts/build_in_city_officials.py`), each `--check` offline, count-guarded and refreshed
weekly by CI as a reviewed PR (`update-in-congress-roster.yml`, `update-in-county-officials.yml`,
which runs both Election Division builders).

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md` and this
instance's own `docs/IN_EXPANSION_PLAN.md`. The working order those documents teach: prove the
source first (a live fetch you performed), ship the boundary and its officeholder sourcing in
the same change, floor every scraped count, and record what a publisher does NOT publish rather
than guessing. When a layer ships, its row in `in/metro-worksheet.json` (`layers[]`, with a
`source` block) is what puts it on the sources page and in every gate — a layer cannot ship
without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the same change.
