# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Missouri: a single-file, dependency-light web app. Click a point in Missouri (or search
an address) and it reports every civic district containing that point and who represents you
there. It serves at **districtry.com/mo/** as a folder of the consolidated districtry repo —
following the Wisconsin/Iowa shape (`docs/EXPANSION_GUIDE.md` Part 2), not the Illinois
root-scripts shape. **The instance is LIVE**, on Adam's word, launched on his choices of
2026-10-26: the map is shaded in two tiers like Illinois's (solid where the county commission
districts are drawn, a lighter wash over the rest of the state, where every statewide layer and the
County card answer), and it launched without voting precincts. `docs/MO_EXPANSION_PLAN.md` is the
record of the launch.

**The layers** draw their shapes from a national publisher or the state, and name people from a
national roster or the state's own publications: **County** (`county`, 115 — the 114 counties and
the City of St. Louis, Census TIGERweb, the state outline the lighter wash covers, and the card that names the county's
governing body and its other elected officers), **U.S. House** (8 districts, TIGERweb geometry
joined to the public-domain unitedstates/congress-legislators roster), **Missouri Senate** and
**Missouri House** (34 and 163 districts, the state's own maps of the 2022 plans joined to each
chamber's own publications), **County Commission District** (`county-commissioner`, 58 districts
in the 29 counties whose own published maps, files or clerks give the lines, joined to the County card's roster),
the TIGERweb fabric, drawn and answered from tile files this site serves (`scripts/mirror_tiger_tiles.py`) — **Township** (`county-subdivision`, 1,394,
shown under the County layer), **City, Town or Village** (`municipality`, 947), **School District
(Unified)** (445), **School District (Elementary)** (71) and **ZIP Code** — and three nearest-N layers
from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**THE CONGRESSIONAL MAP IS THE 2022 MAP, FROM TIGERweb LAYER 4 (THE 119TH CONGRESS), AND IT DOES
NOT SWITCH ON 3 JANUARY 2027 THE WAY LOUISIANA'S AND TENNESSEE'S DO.** Missouri's legislature passed
a new congressional map in September 2025; a referendum petition froze it, and the U.S. Supreme
Court's order of 25 September 2026 kept the 3 November 2026 election on the 2022 map. So the members
seated on 3 January 2027 are elected from the 2022 map too and serve until 3 January 2029.
TIGERweb's layer 0 ("120th Congressional Districts") already carries the frozen 2025 map for
Missouri: measured 2026-10-21 in an equal-area projection, Kansas City's 5th District grows there
from 1,118 to 21,546 km² and the 3rd keeps only 27.49% of its ground, so drawing layer 0 would name
the wrong member across most of the state. The builder refuses if layer 4 stops being the 119th
Congress's map and refuses on or after 3 January 2029; the referendum on the 2025 map is on the
3 November 2026 ballot, and if voters keep it the 2028 election is the first held on it.

**THE TWO CHAMBERS ARE THE STATE'S OWN MAPS, NOT TIGERweb's, AND THAT IS A MEASUREMENT.** Both are
the 2022 plans, published by the Office of Administration's redistricting office as shapefiles and
as a map service (`gis.mo.gov` LEGIS). Measured 2026-10-21 against the filed plan shapefiles,
district by district, the state's map keeps 99.9977% (Senate) and 99.9954% (House) of the plan's
area in the same district, lowest district IoU 0.9995 and 0.99851, where TIGERweb's lowest is
0.99078 (Senate 13) and 0.97332 (House 135): about 1.45 km² of Springfield that the plan puts in
House District 131 TIGERweb puts in 135. Each map is simplified on its own (Douglas-Peucker at 5 m
under an 8 m ceiling), which is safe here because Missouri has no nesting rule between its chambers.

**THE LEGISLATORS COME FROM EACH CHAMBER'S OWN PUBLICATIONS.** The Senate's directory prints one card
per seat — name, district, party, Capitol room and telephone — and on 2026-10-21 held 33 senators
and District 10 printed vacant. No Senate page prints an e-mail address, so each senator's comes
from the Secretary of State's General Assembly Roster, and only where that roster's line for the
district names the surname the Senate's directory names (on 2026-10-21 it still printed Travis
Fitzwater for District 10). **`house.mo.gov` STATES `Crawl-delay: 120` AND DISALLOWS EVERY ADDRESS
WITH A QUERY STRING**, which is how its member pages are addressed, so they are never read and never
linked; the House publishes the same records as one XML file per district at
`documents.house.mo.gov`, whose robots.txt asks for 20 seconds between requests, so a weekly run
takes about 55 minutes. On 2026-10-21 it named 155 members and printed 8 seats vacant (29, 95, 99,
110, 114, 149, 159 and 160). Each file also gives the member's home town and a legislative
assistant's name, neither of which is read.

**THE COUNTY'S GOVERNING BODY COMES FROM THE SECRETARY OF STATE'S MISSOURI ROSTER**, a 256-page PDF
the office prints every two years ("2025-2026 Missouri Roster"), whose "Missouri County Officials"
section lists every county official the county clerks furnished. 110 counties are governed by a
county commission — a presiding commissioner elected countywide and two district commissioners,
seven seats in Clay County — St. Louis, St. Charles and Jefferson counties by a county executive
and a seven-member council, Jackson County by a county executive and a nine-member legislature,
and the City of St. Louis by its mayor and Board of Aldermen, whose fourteen ward aldermen the
roster does not name (gap `mo-st-louis-aldermen`). The builder reads the PDF with `pdftotext -tsv`
(poppler-utils, installed by the workflow) and orders each page's two columns itself. **ONE NAME THE
ROSTER PRINTS IS NOT SHIPPED**: Jackson County's voters recalled County Executive Frank White Jr. on
30 September 2025, after the edition was printed, so `STALE` carries the office and the card says it
is not named; the entry stops the build once an edition no longer prints the name. A telephone or
e-mail address printed in one official's own entry ships on that official; one printed beside two
or more members of the governing body is the body's; an address ships only as the body's office,
where two or more members print it word for word. Fax numbers never ship.

**THE COMMISSION DISTRICTS ARE DRAWN COUNTY BY COUNTY, FROM EACH COUNTY'S OWN MAP.** A county's
two commission districts are drawn by its commission "without dividing municipal townships"
(RSMo 49.010), and no statewide map of them was found. Townships are not a substitute: tested
against three counties' own maps on 2026-10-21, Franklin's twelve townships fall whole inside its
districts, while Buchanan splits 2 of 12 and Clay 2 of 7. Since 2026-10-23 the County Commission
District layer draws 29 counties (`mo/scripts/build_mo_commission_districts.py`, `--check` in CI):
21 from the commissioner district layer of the county's own map viewer, Cole from MidMO GIS's
download, Lawrence from its posted map, whose line runs along whole townships drawn from TIGER, and Cass
from the shapefile its GIS office e-mailed on 2026-10-23 (kept as sent in `mo/data/source/raw/`, held
to its SHA-256 by the builder), and Saline from its clerk's list of the townships and precincts in each
district, drawn from TIGER's townships and, inside Marshall township, which its city wards split, the Census
Bureau's 2020 voting districts, and Perry from the Commissioner Districts layer of the county's public map
at SEMO GIS, which its clerk pointed to, and Iron and Scott from the same server's Commissioner
District layers, found there on 2026-10-24 with no county pointing to them (St. Francois's, on the same
server, is not drawn: it reaches 0.61% of the county past the Census line and splits current precincts,
so its letter's answer decides it), and Wayne from the township map its clerk's office e-mailed on 2026-10-26, whose
line between the two districts runs along township lines only, drawn from TIGER's townships, each clipped to the County layer so the two districts tile the county exactly, and each
district joined to the roster's seat by name. **The card says the line is not checked against the
county's election records**, because no viewer dates its lines and Missouri sets no redistricting
date; the Secretary of State's per-jurisdiction precinct reports (SUN0000590, not ordered) would be
that check. The layer hides in the other 85 counties and the City of St. Louis, which stay in gap
`mo-county-commission-district-lines`; a county joins when its own map proves the lines.

**TWO SCHOOL LAYERS TILE THE STATE BETWEEN THEM.** TIGER holds 445 unified and 71 elementary
districts for Missouri and no secondary ones, and the two tilings partition the state, so each
layer's empty card points at the other. No school board member is named yet (gap
`mo-school-board-members`).

**THE TOWNSHIP CARD SAYS WHETHER THE TOWNSHIP GOVERNS.** Of the 1,394 county subdivisions, 282 in 20
counties are active governments (FUNCSTAT A), 16 in Dade County are inactive, 1,094 have no
government (N), one is the City of St. Louis (F) and one, Barton County's City township, is
recorded as partly consolidated (B); the card states each in the Census's own terms. No township
officer is named yet (gap `mo-township-officers`).

**THE ZIP LAYER HIDES OUTSIDE MISSOURI.** A ZCTA carries no state field, so over the line the live
service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline, and
the smoke test asserts both halves.

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

- Metro: Missouri (`missouri`) — https://districtry.com/mo/
- Geocoders: address Photon (Missouri-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Missouri-bounded, serial >=1s queue)
- Ground truth: 38.57910,-92.17290 (Missouri State Capitol, 201 W. Capitol Avenue, Jefferson City, Cole County) → county Cole County; us-house 3; mo-senate 6; mo-house 60. Negative point 38.61560,-95.26780 (Franklin County, Kansas, near Ottawa, about 57 km west of the Missouri line — outside Missouri and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-21: TIGERweb's state and county layers name Kansas and Franklin County here (control: the State Capitol returns Missouri and Cole County), and none of the state's shipped boundary files contains it. MISSOURI HAS NO COAST, SO THIS POINT IS ON A NEIGHBOUR'S LAND AND WILL HAVE TO MOVE: Iowa, Illinois, Kentucky, Tennessee, Arkansas and Oklahoma are live already, so Kansas and Nebraska are the only neighbours left, and the change that makes either one live moves this point to the other, the way Kentucky's go-live moved Indiana's.).
- Layers: 13 registered (political 4, safety 2, schools 2, geography 5); `registerLayer(` floor 10. Debug namespace `window.MissouriExplorer`.
- Scheduled workflows: `update-mo-congress-roster.yml` (Mon 18:37 UTC); `update-mo-legislature-roster.yml` (Tue 18:37 UTC); `update-mo-county-officials.yml` (Wed 18:37 UTC); `mo-validate-sources.yml` (1st of month 21:13 UTC).
- Source registry: `mo/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/mo/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/mo/ node mo/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 mo/scripts/validate_index.py mo/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 mo/scripts/build_metro_outline.py --check

# County officials (offline: the shipped roster's shape):
python3 mo/scripts/build_mo_county_officials.py --check

# Generated-region gate: per-instance facts live ONCE in mo/metro-worksheet.json;
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
which vendors Leaflet into `mo/scripts/vendor/leaflet/` (gitignored);
`mo/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Missouri-specific lives in the `METRO:BEGIN config` block (worksheet-generated) and
this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
this instance's three chamber layers use the fenced factory helper `registerIlgaChamber` (the
generic chamber factory both state chambers and the U.S. House card use, which renders a
vacancy record as a vacant seat with its reason and source), the five TIGERweb layers
`registerPolygonLayer` or a bespoke block, and the three nearest-N layers
`registerNearestPointLayer`. The County card is a bespoke `registerLayer` block that reads the
county-officials roster. Two invariants pervade the code: the **stale-async guard**
(`if (seq !== state.sequence) return;` after every await) and **per-layer failure isolation** (a
layer's failure shows a Retry inside its own card, never breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name. Both chamber
cards degrade to the district number + the chamber's own member list on a roster miss, and
a vacant seat says it is vacant; an office the roster prints as vacant is shown as vacant; the
school-district, township and municipality cards carry no roster at all and **say so on the
card**. External strings always render through `sanitize()`/`textContent`. Roster refreshes
always land as PRs for review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`mo/scripts/build_metro_outline.py` — one INSIDE anchor per county plus OUTSIDE anchors in the
eight neighbouring states), `state-counties.json` (`mo/scripts/build_state_counties.py`), and
`congress-districts.json`, `mo-senate-districts.json`, `mo-house-districts.json`
(`mo/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, refused unless BOTH the
2,000-random-point agreement gate and the 8 m fidelity ceiling pass), and
`mo-commission-districts.json` with its list of drawn counties `mo-commission-counties.json`
(`mo/scripts/build_mo_commission_districts.py`, from 21 county map viewers, Cole's download and Lawrence's township map,
each pair clipped to tile its county). Rosters:
`congress-roster.json` (`mo/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`mo-{senate,house}-members.json` (`mo/scripts/build_mo_legislature_roster.py`, from each chamber's
own publications and the Secretary of State's General Assembly Roster) and
`mo-county-officials.json` (`mo/scripts/build_mo_county_officials.py`, from the Secretary of State's
Missouri Roster) — all count-guarded, all refreshed weekly by CI as reviewed PRs.
`scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `mo/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
