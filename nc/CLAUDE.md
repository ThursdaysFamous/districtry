# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry North Carolina: a single-file, dependency-light web app. Click a point in North
Carolina (or search an address) and it reports every civic district containing that point and
who represents you there. It serves at **districtry.com/nc/** as a folder of the consolidated
districtry repo — following the Wisconsin/Iowa shape (`docs/EXPANSION_GUIDE.md` Part 2), not
the Illinois root-scripts shape. It ships FIFTEEN layers and has been **LIVE since 2026-10-09**,
after arriving dark on 2026-09-29. Its go-live generated `congress.html` and
`state-legislature.html` — both chambers are named, so unlike Minnesota, Kentucky and Indiana
this instance needed no recorded-absent legislature page — and `nc/WATCH.md` records what that
change did and the re-check plan for every data file the app reads.

**The national tier** — everything these eleven layers answer comes from a national publisher.
The other four are Tribal Government (the Eastern Band of Cherokee Indians' land, from the Census,
its government from the Bureau of Indian Affairs), the voting precincts, the city council
districts and the school board districts below.
**County** (100, Census TIGERweb, identity-only and the coverage ring), **U.S. House** (14
districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators
roster), **N.C. Senate** and **N.C. House** (50 and 120 districts, TIGERweb geometry joined to
Open States and enriched from the General Assembly's own member lists), the LIVE TIGERweb
fabric — **Township** (`county-subdivision`), **City or Town** (`municipality`), **School
District** (118 unified) and **ZIP Code** — and three nearest-N layers from the USGS National
Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**BOTH CHAMBERS CARRY FULL CONTACT DEPTH, AND THAT IS UNUSUAL FOR AN ARRIVING INSTANCE.** All
170 legislators ship with a party, an e-mail, their own legislative page, a legislative-building
room and a telephone — Michigan's arrival managed that for one chamber of two, and Open States
carries no capitol contact for North Carolina either. It works because `www.ncleg.gov` publishes
one member list per chamber, readably, and because the scraper resolves a seat on the page's own
**departure tag** (`(Resigned)`, `(Deceased)`, `(Withdrawn)`) rather than on document order: three
of nine multi-entry districts list the departed member second, so the obvious reading is wrong
in the direction that names somebody who no longer holds the seat.

**THE FABRIC'S TOWNSHIP CARD IS THE ONE THAT NEEDED MEASURING RATHER THAN INHERITING.** North
Carolina's townships are Census FUNCSTAT `N` — **non-functioning**: the boundaries exist and the
governments do not. So the card names the township and no officeholder, and records **NO gap**,
which is the deliberate difference from Michigan's `mi-township-officers`: recording a gap would
state that a body exists whose members this app could eventually name, and here there is none.
Two more North Carolina specifics are in the code rather than in a comment. **City, town and
village are one kind of government** — NCGS 160A-1(2), "'City' is interchangeable with the terms
'town' and 'village'" — so the municipality card carries ONE type note rather than three, and
160A-1(3) does the same for council/board of aldermen/board of commissioners. And **the township
affix can be a prefix or a suffix**: TIGER writes "Coopers township" but also "Township 1,
Carthage", so `subdivisionKind` reads what NAME carries beyond BASENAME at either end and returns
null when the two are unrelated — a TIGER change then shows up as a missing type row rather than
as an improvised one.

**ELECTION PRECINCTS ARE DRAWN SINCE 2026-10-15, FROM THE STATE BOARD OF ELECTIONS' FILE.**
`voting-precinct` draws all 2,625 precincts. The Board posts its statewide precinct shapefile only
as dated zips in a download folder (the newest on 2026-10-15 was `SBE_PRECINCTS_20260824.zip`),
and NC OneMap serves a queryable copy that carries no date of its own; the builder reads that
copy, and matched it to the 2026-08-24 zip by the count in all 100 counties and by the largest,
smallest and summed record ids. It is pre-built by `nc/scripts/build_nc_precincts.py` through the
fleet module `scripts/statewide_precincts.py` at Douglas-Peucker 12 m (8.2 MB, 2.43 MB gzipped),
so a click is answered from the file and no point leaves the browser. The card names the precinct
and its county, says a precinct elects no one, names the Board's file of August 24, 2026 that the
copy matches, states the 12 m, and links the Board's polling-place lookup; the builder holds the
card to both the date and the interval. **THE BOARD NUMBERS ITS COUNTIES IN A DIFFERENT ORDER FROM
THE CENSUS** (it puts Macon, 56, before McDowell; the Census puts McDowell first), so the county
is joined by name, which a first draft found by failing on Macon. An undated copy and a zip with
no metadata are evidence for the state-publishing ask. The quarterly re-check, which also lists
the Board's folder for a newer zip, is in `nc/WATCH.md`.

**THE 42 CITIES AND TOWNS ABOVE 25,000 PEOPLE NAME THEIR MAYOR AND COUNCIL SINCE 2026-10-16, AND
THE 17 WHOSE DISTRICTS ELECT THEIR OWN MEMBERS DRAW THEM.** No state office publishes who holds
North Carolina's city offices: the League of Municipalities' public directory lists no
officials, and the State Board of Elections' results name candidates and their votes but no
winner, no appointee and no empty seat. So `nc/data/source/nc-city-council-seats.json` writes
each place's mayor and council down by hand from its own pages (304 seats, the names and nothing
else: many of the pages also print members' e-mail addresses, telephone numbers or street
addresses, and none of it is copied), and `nc/scripts/build_nc_city_councils.py`, through the
fleet module `scripts/city_councils.py`, re-reads every page it cites on each build and refuses
to write unless every name is on its page. Some names come from somewhere other than the
council's own list, and the builder lists each and the card says so: **RALEIGH'S AND MATTHEWS'S
FROM THE STATE BOARD'S PRECINCT RESULTS** for November 2024 and November 2025, because both
places' websites answer this project with Cloudflare's managed challenge (each seat's `as` is
the contest line and the name together, so the build proves both; `nc/scripts/ncsbe_results.py`
turns each results zip into its winners and holds the two files' addresses, because the builder
sends a browser's client to seven pages and `scripts/probe_user_agents.py` judges every host a
file names by the strongest client that file sends); Goldsboro's and Asheboro's from the data
each council page loads after it opens; and Wilson's mayor's full name from the city's own map
server. Three seats are empty in the place's own words, and one of Cornelius's is named nobody
because the town's own pages disagree. Which seats a district elects is set by each city's
charter, a local act, and recorded nowhere statewide, so it was read from which precincts voted
in each contest from 2022 to 2025: 17 places elect some or all seats by district or ward,
Durham, Concord, Hickory and Morrisville tie seats to districts and elect them by the whole
place (so nothing is drawn for them), and 21 elect every seat by the whole place. `city-ward`
(labelled City Council District) draws the 100 districts and wards of the 17, twelve from the
city's own map and five from its county's, pre-built by `nc/scripts/build_nc_city_wards.py`
through `scripts/city_ward_maps.py`, and each map is held two ways: for 95 of the 97 districts
whose own voters elect a member, the precincts that voted in its last contest hold all but at
most 162 of the 2020 residents the map puts in it, and each city's districts balance its 2020
people within 9.2%. **RALEIGH'S ONLY READABLE MAP IS LABELLED A PROPOSAL**: its live layer is
closed by robots.txt, so the copy the city published in November 2021 as "Proposed Council
Districts, Scenario 2" is drawn, and the precincts that voted in 2024 lie 99.9% to 100% inside
the same districts on it. **ONSLOW COUNTY PUBLISHES TWO DIFFERENT MAPS OF JACKSONVILLE'S
WARDS**, which name a different ward on 6.0% of the ground both draw; the one that balances the
city's people is drawn, which is an inference and recorded as one. Gastonia's Wards 3, 4 and 6
are drawn although their members were elected by the whole city, because the other three wards
elect their own and from 2027 all six do. The ward layers are asked for the district field
alone: New Bern's carries each alderman's home address, and several carry members' names, e-mail
addresses or telephone numbers. Durham's, Greensboro's, Cary's, Greenville's, Rocky Mount's,
Garner's and Wilson's sites refuse this project's own token (Cloudflare's block page at Durham,
Greenville and Rocky Mount, Akamai's at Greensboro, Cary and Garner, and Wilson's own 403), so
those seven pages are read with Chrome and its client hints on the stdlib client, and the
measurement that allows it is in the builder. The 510 smaller places name nobody (gap
`nc-municipal-officeholders`), and no state office publishes a council district, all evidence
for the publishing ask. The quarterly re-checks are in `nc/WATCH.md`.

**THE 38 SCHOOL BOARDS THAT ELECT MEMBERS BY DISTRICT ARE DRAWN SINCE 2026-10-17, FROM THE STATE
BOARD OF ELECTIONS' RESULTS, AND NO MEMBER IS NAMED.** No map of any board's election districts
was found published anywhere: the State Board's ShapeFiles folder carries its precinct maps and
nothing else. So `school-board-district` (labelled School Board District) is read off the State
Board's precinct-level results by `nc/scripts/build_nc_school_board_districts.py`: a seat's
contest is on the ballots of the precincts of its district, so each of the 214 district seats is
the precincts whose ballots carried its latest contest in its board's two most recent election
years, read in the State Board precinct map of that election and cut to the Census school
district. **WHICH BOARDS ELECT BY DISTRICT IS MEASURED, NOT LISTED**: of the 115 boards with a
contest in the results since 2022, 45 elect at large, 38 by district, and 32 label seats by
district while every precinct votes on each of them, which is a rule about where a member lives,
so those 32 are printed by the builder and not drawn. What the results cannot place ships as what
it is, and the card names every seat or election rather than choosing: 100 split precincts whose
ballots carried two seats of one election, 161 overlap pieces where two elections put different
seats on the ballot, and 11 unplaced pieces of 628 km2, 536 of them Watauga's, whose board has no
district contest in the files before the 3 November 2026 ballot. That ballot's file, which the
State Board posted on 2026-10-05 with no votes, is read as the latest contest for the seats on
it; it is not linked from the State Board's results page and was found by listing the bucket the
files are served from. No member is named, because a board fills a vacancy by appointment, which
no results file shows (gap `nc-school-board-members`); the card links each school district's own
website from NCES's Common Core of Data instead. The layer's own limits are gap
`nc-school-board-districts`, and the re-check after the November general is in `nc/WATCH.md`.

**THE FLAGSHIP THIS INSTANCE IS BUILDING TOWARD IS `county-commissioner`, AND ITS TWO HALVES
SEPARATE CLEANLY.** All 100 counties elect a board, 587 commissioners in all, and the
**form** of every board is answerable today from one document: NCACC's *County Commissioner
Election Methods* table — measured 39 at large, 23 district-labelled but elected countywide, 22
a combination, 16 purely by district, 61 counties using residency districts, 5 using limited
voting. That is a `structure` field on the `county` card, statewide, with no geometry at all,
and `ia/index.html` already handles both hard cases, so it needs no card-wording decision. The
**geometry** is what no publisher answers: NCGS 153A-22(f) leaves each board's district
delineation as a **written description in the county clerk's office**, and the resolution filed
with the Secretary of State is text rather than a map. Recorded as gap
`nc-commissioner-districts`, with `nc-school-board-members` beside it — the Census fabric
carries geography and no officeholder field at all, so unlike Michigan's commissioner layer
there is not even a stale name to reject — and `nc-municipal-officeholders`, which since
2026-10-16 covers only the 510 cities, towns and villages below 25,000 people.

**THREE MEASUREMENTS FROM THE ARRIVAL BUILD ARE WORTH CARRYING FORWARD.** First, **this state's
chambers forced the simplification algorithm rather than a dial**: at the inherited Visvalingam
retain percentages the worst drawn line strayed 696 m from the true one and 119 of 120 House
districts were over a 25 m ceiling. Douglas-Peucker at `interval=20` answers 20.8 m with 0 over,
for +0.5% gzipped across the three chambers — Illinois's 2026-09-25 finding reproduced on a
fourth layer family, for the same reason: **area thresholding does not bound how far the drawn
line strays, and perpendicular-deviation thresholding does.** The 25 m ceiling is derived from
North Carolina's own median source step (21.9 / 26.1 / 24.5 m) and is GATED in the builder, which
refuses to write on any district over it. Second, **North Carolina's county fabric is
water-inclusive for the inland sounds**, so Pamlico Sound is Hyde County and Albemarle Sound is
Tyrrell, the Outer Banks tile continuously through them, and the whole state dissolves to **ONE
ring, 2,292 vertices** — measured, not reasoned; read the ring count from
`build_metro_outline.py --check`, never from a map in your head. It is also why the worksheet's
negative point has to be the open Atlantic: a point picked inside either sound would make that
assertion vacuous. Third, **the fire query genuinely exceeds the transfer cap** — 3,665 records
against a 2,000 limit, so 1,665 would be dropped silently unpaged. The paging helper is required
here rather than precautionary.

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

- Metro: North Carolina (`northcarolina`) — https://districtry.com/nc/
- Geocoders: address Photon (North Carolina-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, North Carolina-bounded, serial >=1s queue)
- Ground truth: 35.78040,-78.63910 (the State Capitol block, downtown Raleigh, Wake County) → county Wake County; us-house 2; nc-senate 14; nc-house 38; voting-precinct Precinct 01-14. Negative point 35.60000,-75.30000 (the open Atlantic east of Hatteras Island — outside every North Carolina county, measured 2026-09-29. IT HAS TO BE THE OCEAN: the TIGER county fabric is water-inclusive for the inland sounds, so Pamlico Sound is Hyde County and Albemarle Sound is Tyrrell, and a point picked off a map inside either would make this assertion vacuous. Inside permalink_gate's maxLng (-75.10) so the point is still selectable.).
- Layers: 15 registered (political 5, safety 2, schools 2, geography 6); `registerLayer(` floor 12. Debug namespace `window.NCExplorer`.
- Scheduled workflows: `update-nc-congress-roster.yml` (Mon 15:30 UTC); `update-nc-legislature-roster.yml` (Tue 15:30 UTC); `update-nc-county-commissioners.yml` (Wed 15:30 UTC); `nc-validate-sources.yml` (1st of month 16:00 UTC); `watch-city-council-pages.yml` (Thu 15:30 UTC).
- Source registry: `nc/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->
## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/nc/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/nc/ node nc/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 nc/scripts/validate_index.py nc/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 nc/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in nc/metro-worksheet.json;
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
which vendors Leaflet into `nc/scripts/vendor/leaflet/` (gitignored);
`nc/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything North Carolina-specific lives in the `METRO:BEGIN config` block
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
cards degrade to the district number + the chamber's own directory on a roster miss; the
school-district and township cards carry no roster at all and **say so on the card**, the county
card names the commissioners the State Board's results elected, and the municipality card names
the mayor and council of the 42 cities and towns above 25,000 people and says so on the card for
every other place. External strings always render through `sanitize()`/`textContent`. Roster refreshes
always land as PRs for human review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`nc/scripts/build_metro_outline.py` — one INSIDE anchor per county, each an area-weighted
centroid verified interior against that county's own rings, all 100 correct), `state-counties.json`
(`nc/scripts/build_state_counties.py`), and `congress-districts.json`,
`nc-senate-districts.json`, `nc-house-districts.json`
(`nc/scripts/build_legislative_boundaries.py` — statewide TIGERweb, mapshaper-simplified with
Douglas-Peucker, refused unless BOTH the 2,000-random-point agreement gate and the 25 m
fidelity ceiling pass; all three built at 100.00% agreement, 0 overlaps and 0 districts over the
ceiling). Rosters: `congress-roster.json` (`nc/scripts/build_congress_roster.py`, from
unitedstates/congress-legislators) and `nc-{senate,house}-members.json`
(`nc/scripts/build_nc_legislature_roster.py`, from Open States `nc.csv`, enriched by
`nc/scripts/ncga_member_scraper.py`) — all count-guarded, all refreshed weekly by CI as
reviewed PRs. The city councils (`nc-city-councils.json`) and their districts
(`nc-city-wards.json`) are not refreshed by a weekly job: they are re-read each quarter through
each builder's `--watch`, which says whether every name is still on its page and whether any
city's map has changed (`nc/WATCH.md`).

**THE ENRICHMENT IS GATED ON SURNAME AGREEMENT, AND THE COMPARISON NEEDED A MEASUREMENT OF ITS
OWN.** A district's Open States record and its NCGA record must name the same person or the
builder refuses to write. A first cross-check reported fifteen mismatches and every one was
false: NCGA prints suffixes and honorifics as part of the name (`Danny Earl Britt, Jr.` against
Open States' `Danny Britt`, `Timothy Reeder, MD` against `Tim Reeder`), so `NAME_SUFFIXES` strips
them **for the comparison only** — never on a name that ships. The page also serves at least one
name as a numeric character reference (`Erin Par&#xE9;`), so every capture goes through
`html.unescape`; a scraper that skips that ships the entity text to a reader.

**robots.txt IS READ BEFORE THE FIRST FETCH AND THE CRAWL-DELAY IS HONOURED.**
`nc/scripts/robots_gate.py` gates `ncga_member_scraper.py` through `RobotsGate.allows(url)` and
paces it with `HostPacer.hold(url)` (a context manager — not `.wait()`). `www.ncleg.gov`'s
robots.txt is 73 bytes disallowing `/WHPTest/` and `/Ethics/` with `Crawl-delay: 2`, and **it
begins with a byte-order mark** — the exact shape that made this project read ISBE's
`Disallow: /` as a permission for over a year. `robots_policy._parse` strips it; this host is
why it is worth re-checking that it still does.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `nc/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
