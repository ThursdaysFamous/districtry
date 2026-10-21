# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Louisiana: a single-file, dependency-light web app. Click a point in Louisiana (or
search an address) and it reports every civic district containing that point and who represents
you there. It serves at **districtry.com/la/** as a folder of the consolidated districtry repo —
following the Wisconsin/Iowa shape (`docs/EXPANSION_GUIDE.md` Part 2), not the Illinois
root-scripts shape. **The instance is DARK**: no `metros.json` entry, `la/**` excluded from the
Pages deploy, nothing served and no landing card naming it. `la/WATCH.md` lists what go-live has to
do in one change.

**The national tier** draws its shapes from a national publisher and names people from a national
roster or the Louisiana Legislature: **Parish** (`county`, 64, Census TIGERweb, the coverage ring,
and the card that names the parish's governing body), **U.S. House** (6 districts, TIGERweb geometry
joined to the public-domain unitedstates/congress-legislators roster), **Louisiana Senate** and
**Louisiana House** (39 and 105 districts, TIGERweb geometry joined to each chamber's own member
list and member pages), the LIVE TIGERweb fabric — **City, Town or Village** (`municipality`, 305),
**School District** (69) and **ZIP Code** — and three nearest-N layers from the USGS National Map
(**Police Station**, **Fire & EMS Station**, **Post Office**). Beside it, **Police Jury or Council
District** (`parish-district`) draws the districts of each of the 6 parishes whose current lines
are confirmed, and is hidden in the other 58.

**THE CONGRESSIONAL MAP IS TIGERweb LAYER 4 (THE 119TH CONGRESS), NOT LAYER 0, UNTIL 3 JANUARY
2027.** Louisiana redrew its congressional map in the 2026 regular session (Act 2 of 2026), and
layer 0, "120th Congressional Districts", already carries that map. The six members the roster
names were elected in 2024 from the map of Act 2 of the 2024 First Extraordinary Session, and they
represent it until noon on 3 January 2027. Measured 2026-10-20 against the legislature's own
shapefile of that 2024 plan: layer 4 matches every district at IoU 0.99999 or better, while layer 0
keeps only 76.66% of the plan's area in the same-numbered district. The builder refuses a build on
or after 3 January 2027 and refuses if layer 4 stops being the 119th's map; the monthly source check
warns from 1 December 2026; `la/WATCH.md` has the day's steps.

**THE TWO CHAMBERS ARE THE 2022 PLANS, AND ONE 2026 LAW IS NOT IN THEM YET.** TIGERweb's 2026
legislative layers carry the House and Senate plans of the 2022 First Extraordinary Session, which
the sitting members were elected from in 2023. Act 955 of 2026 (SB25) moves precincts between
Senate Districts 33, 34 and 35 in Lincoln, Morehouse, Ouachita, Rapides and Winn parishes, and its
Section 4 keeps every sitting senator's term, so the 2027 election is the first held on the new
lines. The Senate layer's "not defined" feature (GEOID 22ZZZ, the open water of Lake Pontchartrain)
is left out, so a point on the lake answers no Senate district, as the Census's own map does.

**THE LEGISLATORS COME FROM EACH CHAMBER'S OWN PAGES.** The House publishes one card per seat at
`house.louisiana.gov/H_Reps/H_Reps_FullInfo` and the Senate at `senate.la.gov/Senators_FullInfo`;
each card prints the name surname first, the district, the party, the district office's address and
telephone and the member's e-mail address. On 2026-10-20 the House held 103 members and two seats
printed vacant (77 and 92), and the Senate 38 members and one (14). **THE NAME IS THE MEMBER PAGE'S,
NOT THE LIST'S**, because the list drops part of some names when it turns them round ("Morris, John
C. "Jay"" against "John C. "Jay" Morris III"), so every member's page is read and must agree with the
list about the district and the surname. A vacant seat's card still prints the office of the member
who left, and that office does not ship. The pages also name a legislative assistant and a fax
number, which are never read.

**THE PARISH'S GOVERNING BODY COMES FROM THE SECRETARY OF STATE'S LIST OF ELECTED OFFICIALS.** Every
parish elects its governing body by district: 38 police juries, 25 councils (each beside an elected
parish president, mayor-president or mayor) and Caddo's commission. Seven councils also elect some
members at large. The Secretary of State's voter portal (`voterportal.sos.la.gov`) lists every
elected official by office and exports each office as a CSV; three are read, and on 2026-10-20 they
named 573 members (559 by district, 14 at large) and 25 executives across all 64 parishes. **THE
ROWS ALSO PRINT A MAILING ADDRESS, THE OFFICIAL'S RACE AND GENDER**: the race and gender are never
read, and an address ships only as a body's office, where at least three of its members print the
same one (14 parishes), because three people do not share a home — and never when another parish's
officials print the same street line, which is how Tensas's police jurors came to print Rapides's
street address and why neither parish carries one. A telephone printed for one official alone
ships on that official's row (the fleet rule of 2026-10-17); one printed for three or more members
is the body's office telephone (St. Landry); one printed for two is carried nowhere. **A police
jury elects its own president, and the list does not say who**, so no card names one. Where a
parish's numbered or lettered districts skip one (Avoyelles's District 4 and LaSalle's District 5
that day), the card says the list names no one for that seat rather than calling it vacant, which
the list does not say. **`www.sos.la.gov` AND `electionstatistics.sos.la.gov` REFUSE EVERY CLIENT**
by a `User-agent: *` / `Disallow: /` robots.txt, and neither is ever read; the voter portal permits
every path under `/ElectedOfficials/`.

**A PARISH'S DISTRICTS ARE DRAWN ONLY WHEN TWO MEASUREMENTS AGREE, AND SIX PASS** (Adam's ruling of
2026-10-20, "Confirmed only", the rule Mississippi's supervisor districts follow;
`la/scripts/build_la_parish_districts.py`, its `--check` in CI). The Census carries the districts as
county subdivisions — every one outside Orleans is nonfunctioning (FUNCSTAT N), which is how the
Census files a governing-body district, and Orleans has a single subdivision because the New
Orleans City Council's districts are not filed with the Census at all. A parish is drawn when its
2026 lines MOVE residents from the Census's own 2020 edition (evidence that the parish sent new
lines) AND its districts hold nearly equal numbers of people on the 2020 census's own blocks,
within 10% of an equal share. Measured 2026-10-20: 52 of the 63 parishes outside Orleans carry
lines that move nobody, and all 52 are more than 10% apart; of the 11 that moved, six pass —
Assumption, Caddo, Lafourche, St. Charles, Tangipahoa and Terrebonne, at 6.03% to 9.16% — and
**three come close and are NOT drawn**: St. Tammany (10.48%), Ascension (11.26%) and St. James
(11.86%), with Vermilion (20.71%) and LaSalle (88.84%) further off. The near three are a question
for each parish's own map, never a reason to lower the ceiling for every parish. `--survey`
re-takes both measurements for every parish and marks one that newly passes, which a person adds
to `CENSUS_PARISHES` after looking. The name on a drawn district comes from the Secretary of State's
list and the line from the Census, joined by the district's number or letter, and the build refuses
unless the list has a seat for exactly the districts the Census draws. **THE LAYER'S COVERAGE TEST
READS A LIST, NOT THE LAYER'S FILE** (`la-parish-district-parishes.json`, under 1 KB), because it
runs on a reader's first selection even with the layer off.

**ONE SCHOOL LAYER, LABELLED WITHOUT A QUALIFIER.** TIGER's unified tiling holds 69 districts for
Louisiana and its elementary and secondary tilings hold none — so the layer is "School District",
and its id stays `school-district-unified` because a layer id is a public address. No school board
member is named yet (gap `la-school-board-members`).

**MOST OF LOUISIANA IS OUTSIDE ANY CITY, TOWN OR VILLAGE.** Incorporated places hold 4,826 of the
state's 111,943 km² of land (4.3%), so the municipality card's empty state says the parish is the
general-purpose local government there. Baton Rouge and Lafayette are recorded by the Census as
partly consolidated with their parish governments (FUNCSTAT B), and Houma as a place with no
government of its own operating (FUNCSTAT N); the card says each in the Census's own terms and
claims nothing about the form of government. No mayor or council is named yet (gap
`la-municipal-officeholders`).

**THE ZIP LAYER HIDES OUTSIDE LOUISIANA.** A ZCTA carries no state field, so over the line the live
service answers with a neighbouring state's ZIP (77630 at Orange, Texas and 39183 at Vicksburg,
Mississippi, measured 2026-10-20). The coverage test reads the shipped outline, and the smoke test
asserts both halves.

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

- Metro: Louisiana (`louisiana`) — https://districtry.com/la/
- Geocoders: address Photon (Louisiana-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Louisiana-bounded, serial >=1s queue)
- Ground truth: 29.95240,-90.07670 (New Orleans City Hall, 1300 Perdido Street, Orleans Parish) → county Orleans Parish; us-house 2; la-senate 5; la-house 93. Negative point 28.60000,-90.50000 (open water about 50 km south of the Louisiana coast, past the state's offshore line — outside Louisiana and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-20: TIGERweb's state and county layers name no state or parish here, its legislative layers no district, and its ZIP layer no ZIP code (control: New Orleans City Hall returns Louisiana, Orleans Parish and 70112). OPEN WATER BECAUSE A POINT ON A NEIGHBOUR'S LAND WOULD HAVE TO MOVE: Arkansas and Mississippi are live already, and the fleet is meant to reach every state, Texas included.).
- Layers: 11 registered (political 4, safety 2, schools 1, geography 4); `registerLayer(` floor 9. Debug namespace `window.LouisianaExplorer`.
- Scheduled workflows: `update-la-congress-roster.yml` (Mon 19:23 UTC); `update-la-legislature-roster.yml` (Tue 19:23 UTC); `update-la-parish-officials.yml` (Wed 19:23 UTC); `la-validate-sources.yml` (1st of month 20:47 UTC).
- Source registry: `la/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/la/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/la/ node la/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 la/scripts/validate_index.py la/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 la/scripts/build_metro_outline.py --check

# Parish officials and parish districts (offline: the shipped roster's shape,
# and the districts against their build record, the list's seats, the Census
# edition the card names, and the Parish layer at 4,000 points):
python3 la/scripts/build_la_parish_officials.py --check
python3 la/scripts/build_la_parish_districts.py --check

# Generated-region gate: per-instance facts live ONCE in la/metro-worksheet.json;
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
which vendors Leaflet into `la/scripts/vendor/leaflet/` (gitignored);
`la/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Louisiana-specific lives in the `METRO:BEGIN config` block (worksheet-generated) and
this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
this instance's three chamber layers use the fenced factory helper `registerIlgaChamber` (the
generic chamber factory both state chambers and the U.S. House card use, which renders a
vacancy record as a vacant seat with its reason and source), and the three nearest-N layers use
`registerNearestPointLayer`. The Parish and Police Jury or Council District cards are bespoke
`registerLayer` blocks that read the same roster. Two invariants pervade the code: the
**stale-async guard** (`if (seq !== state.sequence) return;` after every await) and **per-layer
failure isolation** (a layer's failure shows a Retry inside its own card, never breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name. Both chamber
cards degrade to the district number + the chamber's own member list on a roster miss, and
a vacant seat says it is vacant; a seat the Secretary of State's list leaves out is said to be left
out, never called vacant; the school-district and municipality cards carry no roster at all
and **say so on the card**. External strings always render through `sanitize()`/`textContent`.
Roster refreshes always land as PRs for review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`la/scripts/build_metro_outline.py` — one INSIDE anchor per parish plus OUTSIDE anchors in
Texas, Arkansas and Mississippi), `state-counties.json` (`la/scripts/build_state_counties.py`,
Douglas-Peucker at 5 m, refused unless the 8 m fidelity ceiling passes),
`la-parish-districts.json` and `la-parish-district-parishes.json`
(`la/scripts/build_la_parish_districts.py`, the 6 confirmed parishes, one mapshaper run so a shared
line is simplified once), and `congress-districts.json`, `la-senate-districts.json`,
`la-house-districts.json` (`la/scripts/build_legislative_boundaries.py` — statewide TIGERweb,
mapshaper-simplified with Douglas-Peucker, refused unless BOTH the 2,000-random-point agreement gate
and the 8 m fidelity ceiling pass). Rosters: `congress-roster.json`
(`la/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`la-{senate,house}-members.json` (`la/scripts/build_la_legislature_roster.py`, from each chamber's
own pages) and `la-parish-officials.json` (`la/scripts/build_la_parish_officials.py`, from the
Secretary of State's list) — all count-guarded, all refreshed weekly by CI as reviewed PRs.
`scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat, and
`scripts/office_address_test.mjs` holds every district office to the address its map pin is
looked up by.

robots.txt is read before the first fetch through `scraper_common.require_robots_once`, with the
same client the fetches send.

## Growing this instance

A new layer or parish-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `la/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
