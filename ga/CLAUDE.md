# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Georgia: a single-file, dependency-light web app. Click a point in Georgia (or search
an address) and it reports every civic district containing that point and who represents you
there. It serves at **districtry.com/ga/** as a folder of the consolidated districtry repo —
following the Wisconsin/Iowa shape (`docs/EXPANSION_GUIDE.md` Part 2), not the Illinois
root-scripts shape. **The instance is DARK**: no `metros.json` entry, `ga/**` excluded from the
Pages deploy, nothing served and no landing card naming it. `ga/WATCH.md` lists what go-live has to
do in one change. The launch plan (Adam's answers of 2026-10-22, "all three as recommended") sets
go-live on or after 1 January 2027, after the county commission and school board layers.

**The layers** draw their shapes from the General Assembly or a national publisher, and name people
from the General Assembly's own member data or a national roster: **County** (`county`, 159, Census
TIGERweb, the coverage ring), **U.S. House** (14 districts), **Georgia Senate** and **Georgia House**
(56 and 180 districts) — all three the General Assembly's own maps of its December 2023 plans, the
House members from the public-domain unitedstates/congress-legislators roster and the legislators
from the General Assembly's own member data — the LIVE TIGERweb fabric — **Census County Division**
(`county-subdivision`, 586), **City or Town** (`municipality`, 538), **School District**
(`school-district-unified`, 181) and **ZIP Code** — and three nearest-N layers from the USGS National
Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**THE THREE DISTRICT MAPS ARE THE GENERAL ASSEMBLY'S OWN FILES, NOT TIGERweb's, AND THAT IS A
MEASUREMENT.** The Legislative and Congressional Reapportionment Office lists each enacted 2023 plan
with a shapefile (House Bill 1EX and Senate Bill 1EX, passed 5 December 2023; Senate Bill 3EX,
7 December 2023). Measured 2026-10-29 against TIGERweb's copies, in an equal-area projection, the
plans keep 99.9944% (Congress), 99.9959% (Senate) and 99.9925% (House) of their area in the same
district. The difference is not drafting: the largest piece, about 3.9 km² near 34.7323, -83.9354,
is land the plans put in Lumpkin County's districts and TIGERweb in Union County's, because the
Census Bureau's current county line there is not its 2020 one, and the acts define a district
naming a county as that county "as shown on the census maps for the United States decennial census
of 2020" (House Bill 1EX, section 3(b)(2)). The county layer is TIGERweb's current edition, so on
that piece of ground the County card says Union and the district cards say Lumpkin's districts,
each right about its own map. The zips are pinned by SHA-256 in
`ga/scripts/build_legislative_boundaries.py`, whose `--check-listing` confirms each is still listed
under the plan it was chosen as. Each map is simplified on its own (Douglas-Peucker at 5 m under an
8 m ceiling), which is safe because Georgia has no rule nesting House districts in Senate districts.

**THE CONGRESSIONAL MAP IS THE 2023 MAP FOR THE 120TH CONGRESS TOO.** Governor Kemp called a special
session for 17 June 2026 to redraw for 2028 and its leaders declined to take up any map, so the
3 November 2026 election uses the 2023 map, and TIGERweb's layers 0 (120th Congress) and 4 (119th)
carry the same 14 districts for Georgia, measured 2026-10-29. Unlike Louisiana's and Tennessee's,
nothing about `congress-districts.json` changes on 3 January 2027. The builder refuses on or after
3 January 2029 until a person has read which map the 121st Congress was elected from.

**THE LEGISLATORS COME FROM THE GENERAL ASSEMBLY'S OWN MEMBER DATA, READ THROUGH THE TOKEN ITS PAGE
HANDS EVERY VISITOR.** `www.legis.ga.gov` is one page whose script reads its members from the
assembly's data service at `/api/`, which answers 401 until a visitor presents a token the script
obtains for everyone, from a key it computes out of a fixed string in the same script and the
current time. Under Adam's rule of 2026-10-06 a key a page hands every anonymous visitor is page
configuration, so `ga/scripts/build_ga_legislature_roster.py` reads the key's ingredients out of the
page's own script on every run, never from a copy, and stops if the script changes shape. On
2026-10-29 every one of the 56 senators and 180 representatives was named, each with party, Capitol
office and telephone, and every one but Senate 38 and 53 with an e-mail address. **TWO FIELDS THE
FEED CARRIES DO NOT SHIP.** Some members' records carry a home or cell telephone, which the page's
script never displays (neither field name occurs in any of its scripts), so the General Assembly
does not print them beside the member and the fleet's rule on an official's own number does not
reach them; and the district address, which the page does show, was a post office box for 96 of 236
members and plainly a home for others, so none ships as an office the card would pin on the map.

**THE COUNTY CARD NAMES THE COUNTY AND NO COMMISSIONER YET.** Every Georgia county is governed by an
elected board of commissioners or, in seven, a sole commissioner, and no state office publishes who
they are (the Department of Community Affairs' directory of local officials sits behind a sign-in,
which stays shut). The plan names them from the Secretary of State's election results
(`results.sos.ga.gov`, whose robots.txt answers 404) and draws the commission and school board
districts from the Reapportionment Office's county maps after a check against the precincts each
contest was counted in; that is the next change, and until then the card says so (gaps
`ga-county-commission-members` and `ga-school-board-members`).

**ONE SCHOOL LAYER, AND FORT BENNING IS THE GROUND IT DOES NOT COVER.** TIGER holds 181 unified
districts for Georgia (the 159 county systems, 21 city systems and the Fort Stewart schools). The one
ground they leave is Fort Benning, where the Census maps the post's own schools as an elementary
district (kindergarten to grade 8, 682 km²) and splits the high school grades between the
Chattahoochee and Muscogee county systems; unified plus that one elementary district sum to exactly
the 159 counties' land. So the layer is the unified tiling alone, and its empty card says that on
Fort Benning the post's own schools answer and this app does not draw them, rather than putting two
more toggles on every reader's list for one post.

**THE CENSUS COUNTY DIVISION CARD SAYS NOBODY GOVERNS IT.** Georgia has no township governments: all
586 county subdivisions are census county divisions (FUNCSTAT S), areas the Census Bureau draws to
report its counts, and the card says so rather than presenting one as a government.

**THE CITY CARD SAYS WHEN A CITY AND ITS COUNTY ARE ONE GOVERNMENT.** Georgia has eight such
governments; seven are filed by the Census as consolidated places (Athens-Clarke, Augusta-Richmond,
Macon-Bibb, Cusseta-Chattahoochee, Georgetown-Quitman, Webster County and Echols County) and
Columbus, one government with Muscogee County, as a city. The card reads `GA_CONSOLIDATED`, keyed by
GEOID, and for the two that share their county with other cities (Athens-Clarke and Augusta-Richmond)
it says the balance of the county is the consolidated government.

**THE ZIP LAYER HIDES OUTSIDE GEORGIA.** A ZCTA carries no state field, so over the line the live
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

- Metro: Georgia (`georgia`) — https://districtry.com/ga/
- Geocoders: address Photon (Georgia-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Georgia-bounded, serial >=1s queue)
- Ground truth: 33.74900,-84.38900 (Georgia State Capitol grounds, 206 Washington Street SW, Atlanta, Fulton County — the west side of the grounds, chosen 123 m from the line between House Districts 58 and 59, which runs east of the Capitol (the Capitol's own address point sits 51 m from it), measured 2026-10-29 against the shipped files) → county Fulton County; us-house 5; ga-senate 36; ga-house 58. Negative point 30.43830,-84.28070 (Tallahassee, Florida, about 26 km south of the Georgia line — outside Georgia and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-29: TIGERweb's state layer names Florida here (controls: the State Capitol returns Georgia, and a point in the open Gulf of Mexico returns no state), and none of the state's shipped boundary files contains it. FLORIDA AND ALABAMA ARE THE TWO NEIGHBOURS NO INSTANCE SERVES, so the change that makes Florida live moves this point into Alabama, the way Kentucky's go-live moved Indiana's.).
- Layers: 11 registered (political 3, safety 2, schools 1, geography 5); `registerLayer(` floor 9. Debug namespace `window.GeorgiaExplorer`.
- Scheduled workflows: `update-ga-congress-roster.yml` (Mon 19:23 UTC); `update-ga-legislature-roster.yml` (Tue 19:23 UTC); `ga-validate-sources.yml` (1st of month 21:43 UTC).
- Source registry: `ga/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ga/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ga/ node ga/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ga/scripts/validate_index.py ga/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 ga/scripts/build_metro_outline.py --check

# The three plans' shapefiles are still listed where they were chosen:
python3 ga/scripts/build_legislative_boundaries.py --check-listing

# Generated-region gate: per-instance facts live ONCE in ga/metro-worksheet.json;
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
which vendors Leaflet into `ga/scripts/vendor/leaflet/` (gitignored);
`ga/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Georgia-specific lives in the `METRO:BEGIN config` block (worksheet-generated) and
this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
this instance's three chamber layers use the fenced factory helper `registerIlgaChamber` (the
generic chamber factory both state chambers and the U.S. House card use, which renders a
vacancy record as a vacant seat with its reason and source), the four TIGERweb layers
`registerPolygonLayer` or a bespoke block, and the three nearest-N layers
`registerNearestPointLayer`. The County card is a bespoke `registerLayer` block. Two invariants
pervade the code: the **stale-async guard** (`if (seq !== state.sequence) return;` after every
await) and **per-layer failure isolation** (a layer's failure shows a Retry inside its own card,
never breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name. Both chamber
cards degrade to the district number + the chamber's own member list on a roster miss, and a
vacant seat says it is vacant; the county, school-district, census-county-division and
municipality cards carry no roster at all and **say so on the card**. External strings always
render through `sanitize()`/`textContent`. Roster refreshes always land as PRs for review — never
as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`ga/scripts/build_metro_outline.py` — one INSIDE anchor per county plus OUTSIDE anchors in the
five neighbouring states), `state-counties.json` (`ga/scripts/build_state_counties.py`), and
`congress-districts.json`, `ga-senate-districts.json`, `ga-house-districts.json`
(`ga/scripts/build_legislative_boundaries.py` — the General Assembly's own 2023 plan shapefiles,
pinned by SHA-256, Douglas-Peucker at 5 m, refused unless BOTH the 2,000-random-point agreement
gate and the 8 m fidelity ceiling pass). Rosters: `congress-roster.json`
(`ga/scripts/build_congress_roster.py`, from unitedstates/congress-legislators) and
`ga-{senate,house}-members.json` (`ga/scripts/build_ga_legislature_roster.py`, from the General
Assembly's own member data) — both count-guarded, both refreshed weekly by CI as reviewed PRs.
`scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured; the legislature builder paces every host at
one second even where none is stated.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `ga/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
