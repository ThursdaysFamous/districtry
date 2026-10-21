# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Oklahoma: a single-file, dependency-light web app. Click a point in Oklahoma (or
search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/ok/** as a folder of the consolidated
districtry repo — following the Wisconsin/Iowa shape (`docs/EXPANSION_GUIDE.md` Part 2), not
the Illinois root-scripts shape. It ships SEVENTEEN layers, and it went **LIVE** in its go-live change,
which Adam held until the fleet-wide tribal thread had drawn Oklahoma's tribal areas: it has a
`metros.json` entry and a landing card, the Pages deploy publishes `ok/` (keeping
`ok/data/state`, `ok/data/source` and `ok/scripts` out), and `ok/congress.html` and
`ok/state-legislature.html` carry its rosters as generated tables.

**The national tier** — these eleven layers answer from a national publisher.
**County** (77, Census TIGERweb, identity-only and the coverage ring), **U.S. House** (5
districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators
roster), **Oklahoma Senate** and **Oklahoma House** (48 and 101 districts, TIGERweb geometry
joined to the Open States export), the LIVE TIGERweb fabric — **City or Town**
(`municipality`), **School District (Unified)** (415), **School District (Elementary)** (91)
and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**,
**Fire & EMS Station**, **Post Office**).

**THE CHAMBER CARDS CARRY NAME, PARTY, E-MAIL AND THE MEMBER'S OWN PAGE, AND NO OFFICE.** The
Open States export carries no capitol address or telephone for any Oklahoma legislator (0 of 147
rows, measured 2026-10-09), and one seat in each chamber has no member in the export (Senate 24,
House 99 on that date). House 99 contains the State Capitol, so the instance's own anchor point
exercises the factory's empty-member path: the card shows the district and the chamber's
directory, never a name. Reading the chambers' own sites for office and telephone is a WATCH
item, not done here.

**THE COUNTY DIVISIONS ARE DRAWN, AND THE CARD SAYS THEY GOVERN NOBODY.** All 305 county
subdivisions TIGERweb carries for STATE='40' are census county divisions (LSADC 22, FUNCSTAT S,
measured 2026-10-15): statistical areas drawn for counting. They were left out at arrival so the
map would not carry a card for a non-government. Since 2026-10-15 the done standard's level 14
(Adam, 2026-10-14) asks every state to draw its subdivision boundaries whether or not they govern
anyone, so `county-subdivision` ("Census County Division") draws them live from TIGERweb, North
Carolina's layer, with a card that names the division without TIGER's "CCD", names its county
and says no one is elected from it. The statewide set is 10.7 MB, uncompressed, and downloads
only when the layer is switched on; a click asks TIGERweb about the point alone.

**TWO SCHOOL LAYERS, BECAUSE TWO OF TIGER'S THREE TILINGS PARTITION THE STATE.** Unified (415)
and elementary (91) districts together cover the state's land exactly (166,222.99 + 11,441.40 =
177,664.38 km², the 77-county total from the same service), and the secondary layer is empty.
Unified alone would tell every reader in an elementary district they are in no school district,
so both ship and each empty note points at the other.

**CITY AND TOWN ARE DIFFERENT FORMS HERE.** Oklahoma's Title 11 gives a town a board of trustees
and a city a council, so the municipality card names the two separately, unlike North Carolina's
one note. 600 places: 165 cities, 435 towns, 8 of the towns FUNCSTAT I (inactive), which the
card states.

**THE 16 CITIES ABOVE 25,000 PEOPLE NAME THEIR MAYOR AND COUNCIL SINCE 2026-10-16, AND NINE OF
THE ELEVEN WHOSE WARDS ELECT THEIR OWN MEMBERS DRAW THEM.** No state office publishes who holds
Oklahoma's city offices or where their wards run. So `ok/data/source/ok-city-council-seats.json`
writes each city's mayor and council down by hand from its own pages (111 seats, the names and
nothing else), and `ok/scripts/build_ok_city_councils.py`, through the fleet module
`scripts/city_councils.py`, re-reads every page it cites on each build and refuses to write
unless every name is on its page. **MUSKOGEE'S ARE NOT FROM THE CITY**: its website's robots.txt
shuts out every crawler but five named ones (a content-management vendor's default,
byte-identical to Rochester Hills, Michigan's), so its mayor and three members come from the
Muskogee County Election Board's official results for 10 February 2026, in the copy a Tulsa
television station published, and the other five from news reports; the card says so.
`ok/scripts/muskogee_results.py` names a winner only with more than half the votes, and holds
the results file's address because the builder sends a browser's client to Broken Arrow and
`scripts/probe_user_agents.py` judges every host a file names by the strongest client that file
sends. Which seats a ward elects is set by each city's charter and recorded nowhere statewide,
so it was read from each charter, the city's own pages, a county election board's results or
news reports: eleven cities elect by ward or district, Broken Arrow, Owasso, Jenks and Edmond
tie seats to wards and elect every seat by the whole city (so nothing is drawn for them), and
Stillwater's council has no wards. Five councils choose the mayor from among their members, and
the card says which ward elected that member. `city-ward` (labelled City Council District)
draws the 64 wards and districts of ten of the eleven, each from the city's own map, pre-built
by `ok/scripts/build_ok_city_wards.py` through `scripts/city_ward_maps.py`. Nine cities' wards
hold their 2020 people within 5.3% of an equal share, which is what a map drawn on that census
shows and does not prove it is the map in force (an inference, recorded as one); the precinct
test North Carolina runs is not available, because the State Election Board's results site
refuses this project. **LAWTON'S WARDS ARE DRAWN ON THE CITY'S WORD** (2026-10-21): its only
published ward map does not balance on the 2020 census and carries 2010 census figures, so it
was left undrawn and the City Clerk's office was asked which map is in force; the office
answered by pointing to the city's public ward map, whose only layer is that map, and said
nothing about the population figures. **MUSKOGEE'S WARDS ARE NOT DRAWN**: it publishes none
this project may read. The ward layers are asked for the ward field alone: seven of them carry
members' names, Shawnee's beside fields called Contact and Photo. Broken Arrow's
site refuses this project's own token at its Akamai edge, so that one page is read with Chrome
and its client hints on the stdlib client, and the measurement that allows it is in the
builder. The 584 smaller places name nobody (gap `ok-municipal-officeholders`), all evidence for
the publishing ask. The quarterly re-checks are in `ok/WATCH.md`.

**THE ZIP LAYER HIDES OUTSIDE OKLAHOMA.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP (Wichita Falls TX gives 76301, Fort Smith
AR 72903, against the Capitol's 73105, measured 2026-10-09). The coverage test reads the shipped
outline, and the smoke test asserts both halves.

**`county-commissioner` SHIPPED 2026-10-11, THE STATE'S MAP AND THE STATE'S NAMES.** Every
county elects three commissioners from three districts (19 O.S. 321). The 231 districts are the
state Department of Transportation's statewide layer (`ok/scripts/build_ok_commissioner_districts.py`),
and every build compares a University of Oklahoma copy of the same map: they agree on 229 of 231
and disagree in Beaver County alone, over 27.6 km² between Districts 1 and 2, so those two
features carry a `lineNote` the card prints and the builder fails if any other county starts to
disagree. Government source first, per the fleet rule, so ODOT's copy is the one drawn. The names
are the State Election Board's Roster of State and County Officers (`build_ok_commissioner_roster.py`,
weekly): a PDF compiled after each general election that lists all three of every county's
commissioners, holdovers included. It is a snapshot, so every card and county page dates it, and
the two seats it lists vacant (Oklahoma County 1, Okmulgee County 1) say vacant rather than nobody.
**The roster prints each officer's home town and that is never carried** — `--check` fails on any
field outside the ones the card reads. The County card lists the whole board, and
`build_county_pages.py` writes a page per county under `ok/county-commissioner/`.

**THE 26 DISTRICT COURT JUDICIAL DISTRICTS ARE DRAWN SINCE 2026-10-16, FROM THE ELECTION BOARD'S
ROSTER.** `ok-judicial-district` dissolves the county fabric this instance ships, by
`ok/scripts/build_ok_judicial_districts.py` through the fleet module `scripts/whole_county_courts.py`.
The districts are set in the Oklahoma Statutes, and both of the state's publishers of them refuse
this project in robots.txt (the `*` group in each disallows every page, while oklegislature.gov
admits named search engines and oscn.net leaves its news feeds open), so the county lists come
from the State Election Board's 2024 roster of state and county officers: every district judge
office with the counties that elect it, and the roster's own key of each county's district, which
the build requires to agree on every county. Only the office headings are kept, never a judge's
name or home town. MOST DISTRICTS ELECT EVERY JUDGE DISTRICT-WIDE AND THREE DO NOT: in District 4
one office is elected by five counties and two by the other four, in District 12 Office 2 is
elected by all three counties and the others by parts, and in District 14 nine offices are elected
by Pawnee and Tulsa and five by Tulsa alone. So each district ships its offices with their
electorates, and the card says which offices the clicked county votes for rather than claiming
every judge answers to every county. It names nobody (gap `ok-judicial-district-judges`) and links
the roster. The appellate courts are not drawn: the roster lists their districts but not whether a
retention vote is held in the district or across the state, and the constitution that says so
could not be read. The re-check, after each November general election, is in `ok/WATCH.md`.

**THE 84 CONSERVATION DISTRICTS ARE DRAWN SINCE 2026-10-16, EACH WITH ITS OFFICE AND NOBODY ON
ITS BOARD.** `conservation-district` draws the Oklahoma Conservation Commission's own map
(`cons_dis` on its ArcGIS Online account; a copy the state Senate's account publishes is
identical), built by `ok/scripts/build_ok_conservation_districts.py` through
`scripts/published_district_layers.py`: 106 records join into 84 districts, five districts being
published in several records each. They cover the state bar 67 km² of slivers, 43 km² of them
along the Kansas line in Texas County, and five pairs overlap by 0.36 km² in all, which the card
says when a point falls in two. Kingfisher County's and East Canadian County's districts interlock
near the line between the two counties, ten of Kingfisher's pieces inside East Canadian's lines and
seven of East Canadian's inside Kingfisher's, and are drawn as published. Each card gives the
district's office, telephone, e-mail and, for three, a website, from the Commission's Conservation
District Offices Directory (`ok/scripts/build_ok_conservation_offices.py`), joined to the map by
name because the directory carries no district number. THE DIRECTORY NAMES NO DIRECTOR, though
three of each board's five are elected by the district's voters and the Commission issues every
director's certificate, so the card names nobody and says how the board is chosen (gap
`ok-conservation-district-directors`; the letter asking the Commission for the list is in
`docs/ASK_DRAFTS.md`). The quarterly re-checks are in `ok/WATCH.md`.

**TRIBAL AREAS ARE DRAWN, AND THIS IS THE ONE INSTANCE THAT DRAWS CENSUS STATISTICAL AREAS.**
Measured with `scripts/tribal_areas.py` on 2026-10-09, the Census draws one federal reservation
in Oklahoma (Osage, 5,967 km²) and one off-reservation trust land (the Shawnee Tribe's, 0.43 km²);
everything else it records for Oklahoma's nations is an Oklahoma Tribal Statistical Area (25) or a
joint-use area two of them share (4). The fleet rule (Adam, 2026-09-30) is that a statistical area
is never drawn as territory, and **Adam made an exception for Oklahoma on 2026-10-10** ("Make an
exception for OK"), because without it a reader almost anywhere in the state would be told no
tribal government answers there. The exception is `tribal_areas.DRAWN_STATISTICAL`, keyed by
state, so no other instance can draw one by accident. `tribal-government` ships 31 areas across 33
nations, and every statistical-area card says the Census draws the area to count people and that it
is not a legal boundary. That is the Census's classification and not a legal one: since McGirt v.
Oklahoma (2020) federal courts have held several of these reservations were never disestablished,
and this layer settles none of it. Where the Census's name for an area names several nations, the
card names every one, each with its own seat and site. Five governments with no area
of their own (the United Keetoowah Band and the Delaware Tribe of Indians in the Cherokee OTSA, and
three Muscogee tribal towns in the Creek one) are placed by their seat city and listed on that
area's card as "Also seated in this area", and `--check` fails if any government the Bureau seats in
Oklahoma is named nowhere. No council is named yet (`ROSTER_NOT_SOUGHT` in
`scripts/build_tribal_areas.py`), recorded in gap `ok-tribal-government`.

**THE CHAMBER BOUNDARIES USE DOUGLAS-PEUCKER AT `interval=20`**, inherited from North Carolina's
measurement and re-measured here: worst stray 23.9 / 24.0 / 24.0 m against the 25 m ceiling the
builder gates, with Oklahoma's median source step about 40-45 m. The coverage outline is ONE
ring, 2,685 vertices, read from `build_metro_outline.py --check`.

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

- Metro: Oklahoma (`oklahoma`) — https://districtry.com/ok/
- Geocoders: address Photon (Oklahoma-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Oklahoma-bounded, serial >=1s queue)
- Ground truth: 35.49230,-97.50340 (the State Capitol, Oklahoma City, Oklahoma County) → county Oklahoma County; us-house 5; ok-senate 48; ok-house 99; ok-judicial-district 7. Negative point 33.65000,-97.15000 (near Gainesville, Cooke County, TEXAS, about 15 km south of the Red River — outside Oklahoma and outside every other instance in the fleet, and inside permalink_gate (minLat 33.50) so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-09: TIGERweb's state layer names Texas at this point (control: the Capitol anchor returns Oklahoma). TEXAS BECAUSE NO INSTANCE SERVES IT, and on land rather than on the Red River, whose channel the county fabric could place on either side.).
- Layers: 17 registered (political 7, safety 2, schools 2, geography 6); `registerLayer(` floor 12. Debug namespace `window.OklahomaExplorer`.
- Scheduled workflows: `update-ok-congress-roster.yml` (Mon 16:45 UTC); `update-ok-legislature-roster.yml` (Tue 16:45 UTC); `update-ok-commissioner-roster.yml` (Wed 16:45 UTC); `ok-validate-sources.yml` (1st of month 19:00 UTC).
- Source registry: `ok/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->
## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ok/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ok/ node ok/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ok/scripts/validate_index.py ok/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 ok/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in ok/metro-worksheet.json;
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
which vendors Leaflet into `ok/scripts/vendor/leaflet/` (gitignored);
`ok/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Oklahoma-specific lives in the `METRO:BEGIN config` block
(worksheet-generated) and this instance's own module code, between the `chamber-factory` and
`hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
this instance's three chamber layers use the fenced factory helper `registerIlgaChamber` (the
generic chamber factory both state chambers and the U.S. House card use), and the three
nearest-N layers use `registerNearestPointLayer`. Two invariants pervade the code: the
**stale-async guard** (`if (seq !== state.sequence) return;` after every await) and **per-layer
failure isolation** (a layer's failure shows a Retry inside its own card, never breaks the
others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name. Both chamber
cards degrade to the district number + the chamber's own directory on a roster miss; the county
and school-district cards carry no roster at all and **say so on the card**, and the
municipality card names the mayor and council of the 16 cities above 25,000 people and says so
on the card for every other place. External strings always render through `sanitize()`/`textContent`. Roster refreshes
always land as PRs for human review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`ok/scripts/build_metro_outline.py` — one INSIDE anchor per county, each verified interior
against that county's own rings, all 77 correct, plus four OUTSIDE anchors in Texas, Arkansas
and Kansas), `state-counties.json` (`ok/scripts/build_state_counties.py`), and
`congress-districts.json`, `ok-senate-districts.json`, `ok-house-districts.json`
(`ok/scripts/build_legislative_boundaries.py` — statewide TIGERweb, mapshaper-simplified with
Douglas-Peucker, refused unless BOTH the 2,000-random-point agreement gate and the 25 m fidelity
ceiling pass). Rosters: `congress-roster.json` (`ok/scripts/build_congress_roster.py`, from
unitedstates/congress-legislators) and `ok-{senate,house}-members.json`
(`ok/scripts/build_ok_legislature_roster.py`, from Open States `ok.csv`) — all count-guarded,
all refreshed weekly by CI as reviewed PRs. The legislature builder also refuses to write when
fewer than 90% of seats carry an e-mail, a district number falls outside the chamber's range, or
two members claim one district.
`ok-conservation-districts.json` and `ok-conservation-offices.json` are the Conservation
Commission's map and its directory of district offices; neither has a weekly job, because the map
changes only when the Commission moves a district's lines and the directory names no one, so both
are rebuilt by hand on the quarterly rows in `ok/WATCH.md`.
The city councils (`ok-city-councils.json`) and their wards (`ok-city-wards.json`) are not
refreshed by a weekly job either: they are re-read each quarter through each builder's
`--watch`, which says whether every name is still on its page and whether any city's map has
changed (`ok/WATCH.md`).

robots.txt is read before the first fetch through `scraper_common.require_robots_once`.
`data.openstates.org` answers its robots.txt with HTTP 403, which RFC 9309 files with a 404:
no policy, allow all.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `ok/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
