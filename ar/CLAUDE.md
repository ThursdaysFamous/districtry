# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Arkansas: a single-file, dependency-light web app. Click a point in Arkansas (or
search an address) and it reports every civic district containing that point and who represents
you there. It serves at **districtry.com/ar/** as a folder of the consolidated districtry repo —
following the Wisconsin/Iowa shape (`docs/EXPANSION_GUIDE.md` Part 2), not the Illinois
root-scripts shape. It ships ELEVEN layers, and **the instance is DARK**: no
`metros.json` entry, `ar/**` excluded from the Pages deploy, nothing served and no landing card
naming it. `ar/WATCH.md` lists what go-live has to do in one change.

**The national tier** — ten of the eleven layers draw their shapes from a national publisher and
name people from a national roster or the Arkansas State Legislature; the eleventh is the quorum
court, below. **County** (75, Census TIGERweb, the coverage ring, and the card that names the
county judge and lists the justices of the peace), **U.S. House** (4 districts, TIGERweb geometry joined to the public-domain
unitedstates/congress-legislators roster), **Arkansas Senate** and **Arkansas House** (35 and 100
districts, TIGERweb geometry joined to the legislature's own member list and member pages), the
LIVE TIGERweb fabric — **City or Town** (`municipality`, 501), **School District** (234) and
**ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**,
**Fire & EMS Station**, **Post Office**).

**THE CONGRESSIONAL MAP IS TIGERweb LAYER 0, AND THAT WAS MEASURED RATHER THAN ASSUMED.** Layer 0
is the 120th Congress's map, which is wrong for a state that redrew for 2026. Arkansas did not:
its four districts in layer 0 and in layer 4 (the 119th) carry the same GEOIDs and identical land
areas, every one differing by 0.00000% (2026-10-13).

**THE LEGISLATORS COME FROM THE LEGISLATURE, NOT FROM OPEN STATES.** The builder reads the one
member list on `www.arkleg.state.ar.us` (both chambers) and every member's own page
(`ar/scripts/build_ar_legislature_roster.py`). **THE LIST CANNOT TELL A SITTING MEMBER FROM A
FORMER ONE**: measured 2026-10-13 it holds 138 rows for 135 seats, a member who has left keeps
their row, and only the member's own page says why, in bold under the name ("Deceased",
"Resigned"). So every member page is read, a seat whose only row is a departed member ships as a
VACANCY RECORD naming the page that says so, and a seat with two sitting members fails the build.
That day three seats read vacant — Senate 1 and 18 and House 8 — so the cards name 33 of 35
senators and 99 of 100 representatives, each with a party, an e-mail address (the list's) and a
link to the member's own page. **THE SAME PAGES PRINT A MAILING ADDRESS AND A TELEPHONE, AND THE
BUILDER NEVER READS THEM**: on a senator's page the bold line under the name is that address,
sometimes a street address that may be a home, and the telephone is not labelled as to whose line
it is. A bold line that is neither a known status word nor an address stops the build.

**THERE IS NO TOWNSHIP LAYER, AND THAT IS A MEASUREMENT.** All 1,051 county subdivisions TIGERweb
carries for STATE='05' are FUNCSTAT N, nonfunctioning legal entities (951 townships, 82 "District
N" and 18 "Township N"), measured 2026-10-13. A township does elect a constable, and no source
naming constables has been read, so a township card would name nobody and claim a government the
Census says is not one. A justice of the peace district is a different line.

**ONE SCHOOL LAYER, LABELLED WITHOUT A QUALIFIER.** TIGER's unified tiling holds 234 districts
for Arkansas and its elementary and secondary tilings hold none, and the unified districts' land
area sums to the 75-county total (134,659 km²) — so the layer is "School District", the North
Carolina shape, and its id stays `school-district-unified` because a layer id is a public
address.

**THE ZIP LAYER HIDES OUTSIDE ARKANSAS.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP (the Texas negative point gives 75570,
against the Capitol's 72201, measured 2026-10-13). The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**THE FLAGSHIP IS THE QUORUM COURT, AND ITS DISTRICTS AND ITS PEOPLE COME FROM DIFFERENT
PLACES.** Every county elects a county judge, who runs the county, and a quorum court of 9 to 15
justices of the peace, each from a district. The `quorum-court` layer draws all 775 districts from
the state's mapping office (`ar/scripts/build_ar_quorum_court_districts.py`); the county judge
comes from the state courts' directory and the justices from the Association of Arkansas
Counties' county pages, which list each court WITHOUT districts (`ar/scripts/build_ar_county_officials.py`,
weekly). On Adam's ruling of 2026-10-13 ("District, else list") a district's justice is named only
where the county's own site numbers them — 20 counties, 218 districts, measured by surveying every
county that day — and elsewhere the County card lists the whole court, credited and dated, and the
district card says it names no one rather than guessing. **THE STATE COURTS' DIRECTORY WAS THE STALE
PUBLISHER, NOT THE ASSOCIATION**: in all five counties where the two named different judges (Boone,
Cleveland, Desha, Jefferson, Sevier) a third source sided with the association, so a government
list is not the authority by being a government's, and each disagreement is recorded in
`JUDGE_DISAGREES` with the source that settled it. **Every one of those seats is on the 3 November
2026 ballot and the new terms start on 1 January 2027**; every county is re-read in January (Adam's
"Now, then January"). The association also publishes its 2024 election results by district, and
whether to name justices from it is Adam's decision, asked 2026-10-13. What is still missing is
gap `ar-quorum-court`, beside `ar-municipal-officeholders` and `ar-school-board-members`.

**NO TRIBAL LAYER, BECAUSE NO TRIBAL NATION'S LAND LIES IN ARKANSAS.** Measured with
`scripts/tribal_areas.py --report Arkansas` on 2026-10-13: no federal reservation, no
off-reservation trust land and no state reservation. Two Oklahoma Tribal Statistical Areas
(Cherokee and Choctaw) reach across the state line by a sliver, and a statistical area is never
drawn under the fleet's rule, so there is no gap record either — a reader-facing gap would say a
tribal government is missing where none governs.

**THE CHAMBER BOUNDARIES USE DOUGLAS-PEUCKER AT `interval=20`**, inherited from North Carolina's
measurement and re-measured here: worst stray 21.2 / 21.6 / 21.8 m (U.S. House, Senate, House)
against the 25 m ceiling the builder gates, with Arkansas's median source step 23.98 / 23.69 /
23.85 m in the same order, and 0 districts over the ceiling in any chamber. The coverage outline
is ONE ring, 2,197 vertices, read from `build_metro_outline.py --check`.

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

- Metro: Arkansas (`arkansas`) — https://districtry.com/ar/
- Geocoders: address Photon (Arkansas-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Arkansas-bounded, serial >=1s queue)
- Ground truth: 34.74650,-92.28960 (the State Capitol, Little Rock, Pulaski County) → county Pulaski County; us-house 2; ar-senate 14; ar-house 74; quorum-court 6. Negative point 33.40000,-94.40000 (near New Boston, Bowie County, TEXAS, south of the Red River that forms the state line there — outside Arkansas and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-13: TIGERweb's county layer names Bowie County, Texas at this point (control: the Capitol anchor returns Arkansas), and the Census's ZIP layer answers 75570 there, which is the neighbouring-state answer the ZIP layer's coverage test exists to hide. TEXAS BECAUSE NO INSTANCE SERVES IT and none is planned next; Mississippi and Louisiana, both on the next-states list, were passed over so this point does not have to move when either goes live, and the point sits well west of the Texas–Louisiana line.).
- Layers: 11 registered (political 4, safety 2, schools 1, geography 4); `registerLayer(` floor 9. Debug namespace `window.ArkansasExplorer`.
- Scheduled workflows: `update-ar-congress-roster.yml` (Mon 17:23 UTC); `update-ar-legislature-roster.yml` (Tue 17:23 UTC); `update-ar-county-officials.yml` (Wed 17:23 UTC); `ar-validate-sources.yml` (1st of month 19:43 UTC).
- Source registry: `ar/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ar/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ar/ node ar/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ar/scripts/validate_index.py ar/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 ar/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in ar/metro-worksheet.json;
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
which vendors Leaflet into `ar/scripts/vendor/leaflet/` (gitignored);
`ar/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Arkansas-specific lives in the `METRO:BEGIN config` block (worksheet-generated) and
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
a vacant seat says it is vacant and why; the county, school-district and municipality cards
carry no roster at all and **say so on the card**. External strings always render through
`sanitize()`/`textContent`. Roster refreshes always land as PRs for review — never as direct
commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`ar/scripts/build_metro_outline.py` — one INSIDE anchor per county, all 75 correct, plus eleven
OUTSIDE anchors in Missouri, Tennessee, Mississippi, Louisiana, Texas and Oklahoma; the
Louisiana one is keyed `Monroe (Ouachita Parish, Louisiana)` because Arkansas has a Monroe
COUNTY and the builder's county lookup would read the bare city name as that county),
`state-counties.json` (`ar/scripts/build_state_counties.py`), and `congress-districts.json`,
`ar-senate-districts.json`, `ar-house-districts.json` (`ar/scripts/build_legislative_boundaries.py`
— statewide TIGERweb, mapshaper-simplified with Douglas-Peucker, refused unless BOTH the
2,000-random-point agreement gate and the 25 m fidelity ceiling pass), and
`ar-quorum-court-districts.json` (`ar/scripts/build_ar_quorum_court_districts.py` — the state's
own layer of every county's justice of the peace districts, read four pages at a time at the
state portal's 60 seconds, refused unless there are 775 districts in 75 counties, each county
numbered 1..n at one of the four counts state law allows, the agreement gate and fidelity
ceiling pass, and every county's districts cover that county's own outline; it records a
fingerprint of the layer's attributes so the weekly workflow's `--watch` can say when a county
redraws). Rosters:
`congress-roster.json` (`ar/scripts/build_congress_roster.py`, from unitedstates/congress-legislators)
and `ar-{senate,house}-members.json` (`ar/scripts/build_ar_legislature_roster.py`, from the
legislature's own pages) and `ar-county-officials.json` (`ar/scripts/build_ar_county_officials.py`
— each county judge from the state courts' directory and each county's justices of the peace
from the Association of Arkansas Counties' page for that county, paced at the association's
20 seconds) — all count-guarded, all refreshed weekly by CI as reviewed PRs. The
legislature builder writes neither file unless BOTH chambers pass: one record per seat (a member
or a vacancy), no fewer than 30 senators and 90 representatives named, every district inside
the chamber's range, the member page's own title, district and surname agreeing with the list, and at
least 90% of named members carrying an e-mail address. A vacancy keeps the date it was first
recorded across weekly rebuilds. `scripts/validate_chamber_rosters.py` holds both files to one
record per seat.

robots.txt is read before the first fetch through `scraper_common.require_robots_once`, with the
same client the fetches send. `www.arkleg.state.ar.us`'s robots.txt (97 bytes, beginning with a
byte-order mark, read 2026-10-13) is `User-agent: *` / `Allow: /` plus two groups naming
ChatGPT's crawlers, which do not bind this client; it states no Crawl-delay, and the member pages
are paced at two seconds anyway. That host reset the connection on about one request in five on
2026-10-13, so each fetch is retried. The weekly workflow scrapes ONCE and carries the rebuilt
files across its branch cut rather than reading all 139 pages a second time.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `ar/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
