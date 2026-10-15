# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Tennessee: a single-file, dependency-light web app. Click a point in Tennessee (or
search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/tn/** as a folder of the consolidated
districtry repo, following the statewide shape (`docs/EXPANSION_GUIDE.md` Part 2), not the
Illinois root-scripts shape. It ships FOURTEEN layers, and **IT IS PUBLISHED** since Adam's word
of 2026-10-13. It arrived dark on 2026-10-10 (no `metros.json` entry, `tn/**` blanket-excluded
from the Pages deploy) and the go-live change narrowed that exclude to the build inputs the
siblings exclude, registered the instance and regenerated every surface that counts the fleet,
including this instance's `congress.html` and `state-legislature.html`. `tn/WATCH.md` keeps the
go-live row with its date, and `docs/TN_EXPANSION_PLAN.md` is the record of the launch. **THAT
CHANGE ALSO MOVED KENTUCKY'S NEGATIVE POINT**, which sat in Sumner County, Tennessee, to Adams
County, Ohio; it was the one fixed point in the fleet inside this instance's outline.

**The national tier, plus the Legislature's own names.** County (95, Census TIGERweb, the
coverage ring and a card that names the county), **U.S. House**
(9 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators
roster), **Tennessee Senate** and **Tennessee House** (33 and 99 districts, TIGERweb geometry),
the LIVE TIGERweb fabric (**City or Town**, **School District (Unified)** 127,
**School District (Elementary)** 15, **School District (Secondary)** 15, **ZIP Code**) and three
nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**,
**Post Office**).

**THE CONGRESSIONAL MAP IS THE 119TH, ON PURPOSE, UNTIL 3 JANUARY 2027.** Tennessee redrew its
congressional districts in 2026. TIGERweb's Legislative layer 0 is now the 120th Congress map
(field CD120), which takes effect when the next Congress sits; the members a reader can call
today were elected from the old lines, which TIGERweb serves as layer 4 (field CD119). The
builder reads layer 4 and REFUSES to run on it after 2027-01-03, so the switch cannot be
forgotten into a wrong answer. North Carolina and Louisiana redrew too; the lesson is the
fleet's.

**WHO HOLDS EACH LEGISLATIVE SEAT COMES FROM THE LEGISLATURE'S OWN MAP, NOT FROM A THIRD
PARTY.** The Legislature publishes its district map on the state's TNMap service, and every
record names the member ("Senator …", "Representative …") or says "Representative Vacant".
`tn/scripts/build_tn_legislature_roster.py` takes the names and vacancies from there, and adds
party, e-mail and the member's own page from Open States only where Open States' member for
that district has the same surname. On 2026-10-10 the two agreed on every named seat; the state
listed House 31 and House 84 as vacant, and Open States still gave House 31 to Ron Travis. The
state's word ships, as a vacancy record the card prints with its date. `capitol.tn.gov` and
`wapp.capitol.tn.gov` both answer robots.txt with `User-agent: *` / `Disallow: /`, so this
project fetches neither: the member pages are LINKED from the card and never read, and the link
checker records the host in `ROBOTS_DECLINED` rather than probing it. Open States carries no
capitol address or telephone for any Tennessee legislator (0 of 131 rows), so the cards carry
no office.

**THREE SCHOOL LAYERS, BECAUSE TENNESSEE USES ALL THREE OF TIGER'S TILINGS.** Most of the state
is in a unified district (127), but fifteen cities and special school districts run their own
elementary schools while the county system runs the high schools, so a reader there is in one
elementary (15) and one secondary (15) district at once. Each empty note points at the other
layers. The card states the grades the Census records ("Pre-kindergarten to grade 8").

**THREE CONSOLIDATED GOVERNMENTS ARE NEITHER A CITY NOR A COUNTY.** TIGERweb carries 345 places
for STATE='47': 182 cities (LSADC 25), 160 towns (LSADC 43), and three metropolitan
governments, where the city and the county are one government with one elected body:
Nashville-Davidson (TIGER names the place "Nashville-Davidson metropolitan government
(balance)", LSADC 00, FUNCSTAT F), Hartsville/Trousdale County (LSADC 00) and Lynchburg, Moore
County (LSADC MG). Both the municipality card and the county card say so. No place is FUNCSTAT I
(inactive), measured 2026-10-10.

**THERE IS NO TOWNSHIP OR CIVIL-DISTRICT LAYER, AND THAT IS A MEASUREMENT.** All 855 county
subdivisions TIGERweb carries for STATE='47' are civil districts ("District N", LSADC 28,
FUNCSTAT N). The Census codes FUNCSTAT N as a legal area with no functioning government: nobody
is elected to run one. Their numbers look like county commission district numbers, and nothing
in the Census record says the lines are the same, so drawing them would invite exactly that
misreading.

**THE ZIP LAYER HIDES OUTSIDE TENNESSEE.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP (Bowling Green, Kentucky gives 42101; a
point just over the Alabama line 35773; the Capitol 37219). The envelope the app downloads
returns 1,070 ZCTAs, 638 of them with their interior point in Tennessee (measured 2026-10-10).
The coverage test reads the shipped outline, and the smoke test asserts both halves.

**THE FLAGSHIP IS THE COUNTY COMMISSION, AND ITS DISTRICTS SHIPPED 2026-10-11; ITS MEMBERS ARE
NAMED COUNTY BY COUNTY, STARTING THE SAME DAY.** Every Tennessee county elects its legislative body from districts, the three
consolidated governments included (Nashville-Davidson's 35 are its Metropolitan Council
districts), and the Comptroller of the Treasury publishes all of them in one statewide layer.
`tn/scripts/build_tn_commission_districts.py` builds **County Commission District** from it: 859
districts in 95 counties, each county numbered 1..N. **THE COUNTY CODE ARRIVES IN TWO SPELLINGS**
("005" and "5"), which read naively is 118 counties, so the builder normalises it and refuses
unless the result is exactly the 95 counties in `state-counties.json`, and a witness then checks
that every district answers to its own county at points inside it. **A DISTRICT IS NOT A SEAT**:
many counties elect two or three members from one district, and the layer carries no seat count,
so the card never says how many people hold a district. **NO STATE OFFICE PUBLISHES THE NAMES** —
the Division of Elections' results of the 6 August 2026 election carry 219 offices and no county
race — so they come county by county from each county's own pages. Recorded as gap
`tn-county-commissioners`, beside `tn-municipal-officeholders` and `tn-school-board-members`;
the gap names every county still unnamed.

**THE NAMES ARE ONE PARSER PER COUNTY, AND A COUNTY JOINS BY HAVING ONE.**
`tn/scripts/tn_commission_parsers/` holds a module per county (its FIPS, the pages it reads, the
seats each district elects, how many sit at large, and a `parse()` over those pages);
`tn/scripts/tn_commissioner_scraper.py` discovers the package, reads robots.txt at every
redirect hop with the client that crawls, and leaves a managed challenge alone;
`tn/scripts/build_tn_commissioner_roster.py` writes `tn/data/app/tn-commissioners.json` and
refuses a county whose districts are not exactly 1..N for the district count the shipped
geometry draws, whose seats per district differ from its module, or that carries a field not on
its whitelist. The first tranche (2026-10-11) is 13 counties: 277 seats, 276 named and one vacant (Blount
District 4, Seat C, which the county's own pages list as vacant although the August results
give it a winner; neither says why, so the card says what the county says). Each of the 13 was
checked against that county's results of 6 August 2026 before it joined, and what each was
checked against is in its module's docstring. The survey of the other counties, and why Shelby
is not in the first tranche, is in `tn/WATCH.md`. **A SECOND TRANCHE OF 20 JOINED THE SAME DAY,
AND NOT ALL OF IT ON RESULTS**: 33 counties, 635 seats, 633 named, the second vacancy Anderson
District 8, whose August winner declined the seat by letter (the county's 21 September agenda).
Fourteen were checked against their own August results. Six could not be, because the results
sit behind a robots.txt refusal on a county's file host (Bedford, Tipton), say "available soon"
(Franklin), or are not published on any county host (Giles, Lincoln, Hawkins), and the state's
results site answers this project 403; those six joined on county documents dated after
1 September 2026 instead, and **two of them, Lincoln and Hawkins, carry a district pairing that
no government document read here confirms**: their September documents name who sits and not
where, and the district each sits in was compared only with a news outlet's copy of the results
or the ballot. Each module's docstring says exactly which. Five more were held back rather than
shipped on weaker evidence: Hamblen (no record readable here gives its districts), Carter (its
results and minutes are behind the same kind of robots.txt refusal and its page carries no
date), Dyer (it letters its districts A to J and the state's map numbers them 1 to 10, with
nothing published that pairs the two), Greene (its page lists District 5 as open while the
county's own September committee list seats the man elected there) and Cumberland (its site
answered every request with HTTP 429). **A THIRD TRANCHE OF 16 JOINED THE SAME DAY, OUT OF 36
TRIED**: 49 counties, 867 seats, 864 named, the third vacancy Polk District 2, which the county's
page states. Twelve were checked against their own August results (Benton, Cannon, Cheatham,
Chester, Cocke, Crockett, DeKalb, Hickman, Marion, Obion, Stewart, Unicoi — Crockett's list is its
election commission's own page, as the county government publishes none), and four on county
documents from after the election that name members by district (Claiborne's "term ends August
2030" on every member plus the outgoing body's roll call for the twelve who continue, Fentress's
21 September resolution signed by all ten by district, Polk's September commissioner list,
Scott's election commission list of officeholders by district). Twenty were held: fourteen with
nothing that confirms the page is current or which district each member sits for, and six whose
page cannot be used as it stands — four disagree with the county's own results or later documents
(Hancock, Johnson, Overton, Sequatchie), Smith leaves three districts' write-in seats unnamed
without calling them vacant, and Houston's layout separates two members from any district
heading. **A FOURTH TRANCHE OF 2 JOINED THE SAME DAY, OUT OF THE 16 NOT TRIED BEFORE**: 51 counties, 901 seats, 898 named. Sullivan is read from its ELECTION COMMISSION's list of elected officials by district, not from the county's commission page, which still lists the 2022 board: **A STALE COUNTY PAGE IS NOT THE END OF THE SEARCH**, because a county's other government hosts can carry the current list (Scott's was the precedent). Clay is read from its own page and checked against its scanned August results. Fourteen were held: Gibson (its page names a District 12 member where the results say no candidate qualified), eight whose only list is the 2022 board, Grundy and Moore (no list published), Pickett (its listed county website is the chamber of commerce's), and Morgan and Rhea (unreadable that day); Cumberland answered 429 again. **A RESULTS FILE IS EVIDENCE AND NEVER A SOURCE**: the weekly reader parses HTML, and a county whose only by-district list is its results is held rather than read from them. **A FIFTH TRANCHE OF 3 JOINED THE SAME DAY, OUT OF 18 HELD COUNTIES RE-EXAMINED**: 54 counties, 950 seats, 946 named. **A COUNTY THAT LETTERS ITS DISTRICTS IS PAIRED BY MEASUREMENT, NEVER BY ORDER**: Dyer's A to J were matched to the state's 1 to 10 through the Comptroller's own lettered precinct layer, its lettered map placed by its own coordinates, and the county's precinct results; the answer happens to be alphabetical and is written out in the module so a change has to be measured again. A module's `DISTRICT_LABELS` carries the county's own name for each district, and the card ("The county's name for it") and the county's page print it BESIDE the state's number, never in place of it, because the number is what the map, the hover name and the page anchor use. Henry's District 2 third seat is recorded vacant on the county's own count of 14, its August tie going back to the voters on 3 November; Hamblen's districts are confirmed by the county GIS office's own elected-representatives layer, with no August results published anywhere to compare. Macon now has two county pages that disagree in five districts and is held until the county says which is current. **A SIXTH PASS RE-EXAMINED SEVEN HELD COUNTIES AND NAMED NONE**, and corrected one reason: Johnson's "later document" is its election commission's list of the 2022 commission under a revision date that is the footer on every page of that site, so Johnson's page is unconfirmed rather than contradicted. **A DATE ON A PAGE IS NOT A DATE ON ITS CONTENT.** Smith's six unnamed seats are on the 3 November ballot as unexpired terms. **A SEVENTH TRANCHE OF 2 JOINED ON 2026-10-13**: 56 counties, 988 seats, 984 named. Morgan came from a retry of the four held for a server or network fault: its page answered and matches its election commission's scanned August results in all 18 seats. Trousdale came from re-reading the stale pages: its page had been rewritten for the new term, with "Beginning Term: September 1, 2026" on every new member's card and the same 20 names as the commission's 28 September agenda, and with no August results published its new members' districts rest on the page, as Claiborne's do. **A STALE PAGE IS RE-READ, NOT WRITTEN OFF**: it was rewritten two days after the survey found it stale. Cumberland's page answered too and is held because nothing can check it (its election commission, damaged by fire in March, posts no August results), Rhea still presents a certificate for another name, and Union's election commission answered its robots.txt with HTTP 500. **A SERVER ERROR IS THAT DAY'S ANSWER, NOT THE COUNTY'S**: Morgan was surveyed as failing on every path and served its page two days later. One letter, sent 2026-10-11 on Adam's choice (Ask tn-ctas-commissioner-districts in `docs/ASK_DRAFTS.md`), asks the University of Tennessee's County Technical Assistance Service to add each commissioner's district to the directory that already lists every commissioner, which would cover every county at once. **A CHAIR NAMED ON A PAGE IS NOT RECORDED UNLESS SOMETHING SHOWS THE NEW
COMMISSION ELECTED THEM**: the chairs are chosen in September, and Cocke's and Claiborne's pages
both print one that nothing confirms for the new term. **A PARSER'S `TITLE` IS A CARD'S WORD AND NOTHING ELSE**:
three of the twenty kept a compiled pattern under that name, which the scraper would have
shipped as the seat title, so it now refuses a non-text `TITLE` or `BODY` at load. A county that cannot be read keeps its
last good record for 45 days, dated to the day it was read, and past that the weekly run
(`update-tn-commissioner-roster.yml`, Wednesday) fails. **PRIVACY IS A WHITELIST, NOT A
FILTER**: county pages print home addresses, personal mobile numbers and personal e-mail beside
the official ones, so a member record can carry only a name, a seat, a role, an e-mail on the
county's own domain, and a telephone only for the one county (Davidson) whose numbers are the
Council's own office lines. **NASHVILLE IS A METROPOLITAN COUNCIL, NOT A COMMISSION**, with 35
district members and 5 elected countywide, so its record carries its own body name and member
title, and its generated page is titled "Davidson County Metro Council". The per-county pages
under `tn/county-commissioner/` and their index on `tn/county-commissioner.html` are generated
by `scripts/build_county_pages.py` from the same roster.
The Comptroller's layer reports the date of its last data edit, and the monthly source check
warns when it moves past the edit the shipped file was built from (2026-09-10).

**TRIBAL GOVERNMENT SHIPPED 2026-10-15**, built by the fleet-wide tribal-government thread with
the same reader every instance uses (`scripts/build_tribal_areas.py --state "Tennessee" --tag tn`).
Measured with `scripts/tribal_areas.py` the Census draws no reservation in Tennessee and one
piece of off-reservation trust land: 0.695 km2 of the Mississippi Band of Choctaw Indians'
trust land, near Henning in Lauderdale County (4.1% of that trust land's area; the rest is in
Mississippi). The nation is seated in Choctaw, Mississippi, so the card names that seat, and
the population line says the 2020 count covers the whole trust land. The card names the Tribal
Chief and the 17-member Tribal Council from the nation's own page at
`www.choctaw.org/about-us/tribal-government/`, read weekly by `scripts/tribal_council_scraper.py`;
each member is elected from one of the nation's eight communities in Mississippi, named beside
them, and none from this land. Like every cross-state parcel in the fleet, the shipped file
carries the whole trust land, so a click on its Mississippi part answers too.

**THE CHAMBER AND COMMISSION BOUNDARIES USE DOUGLAS-PEUCKER AT `interval=20`**, inherited from
North Carolina's measurement and re-measured here: worst stray 23.2 / 21.4 / 21.5 / 21.4 m (U.S.
House, Senate, House, county commission) against the 25 m ceiling the builders gate, with
Tennessee's median source step 27.67 / 25.41 / 23.63 / 21.34 m. At `interval=30` the commission
layer strays 31.2 m and 846 of its 859 districts exceed the ceiling, so 20 is a measured choice here and not a default. The coverage outline is ONE ring, 2,288 vertices, read from
`build_metro_outline.py --check`.

**`tncourts.gov` serves a browser challenge**, which the fleet's robots reader recognises as
challenge-fronted. It is never worked around, and no layer here reads it.

**There is no build step, no framework, and no server-side code.** The app (styles, engine,
and layer modules) lives inline in `index.html`. `sw.js` is the service worker;
`data/app/*.json` are runtime-fetched data files; `data/state/` carries the bootstrap state
config (`build_congress_roster.py` reads its FIPS/USPS/seat count; it ships in the repo and is
excluded from the Pages deploy). `sources.html` carries the generated per-layer provenance
matrix and `faq.html` the common questions; `congress.html` and `state-legislature.html` are
generated by `scripts/build_legislator_pages.py` with their tables from
`scripts/build_officeholder_tables.py`, and `county-commissioner.html` with its per-county pages
by `scripts/build_county_pages.py`. All of them compose from the same shared engine blocks as
every other instance via `scripts/compose_app.py`.

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: Tennessee (`tennessee`) — https://districtry.com/tn/
- Geocoders: address Photon (Tennessee-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Tennessee-bounded, serial >=1s queue)
- Ground truth: 36.16590,-86.78440 (the State Capitol, Nashville, Davidson County) → county Davidson County; us-house 7; tn-senate 21; tn-house 51; county-commissioner 19. Negative point 34.90000,-86.60000 (near Hazel Green, Madison County, ALABAMA, about 11 km south of the state line — outside Tennessee and outside every other instance in the fleet, and inside permalink_gate (minLat 34.80) so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-10: TIGERweb's state layer names Alabama at this point (control: the Capitol anchor returns Tennessee). ALABAMA BECAUSE NO INSTANCE SERVES IT and none is planned next: Arkansas and Mississippi, both on the next-states list, were passed over so this point does not have to move when either goes live.).
- Layers: 14 registered (political 5, safety 2, schools 3, geography 4); `registerLayer(` floor 11. Debug namespace `window.TennesseeExplorer`.
- Scheduled workflows: `update-tn-congress-roster.yml` (Mon 17:15 UTC); `update-tn-legislature-roster.yml` (Tue 17:15 UTC); `update-tn-commissioner-roster.yml` (Wed 17:15 UTC); `tn-validate-sources.yml` (1st of month 19:30 UTC).
- Source registry: `tn/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->
## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/tn/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/tn/ node tn/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 tn/scripts/validate_index.py tn/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 tn/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in tn/metro-worksheet.json;
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
which vendors Leaflet into `tn/scripts/vendor/leaflet/` (gitignored);
`tn/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Tennessee-specific lives in the `METRO:BEGIN config` block
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
cards degrade to the district number + the chamber's own directory on a roster miss; the county,
school-district and municipality cards carry no roster at all and **say so on the
card**. External strings always render through `sanitize()`/`textContent`. Roster refreshes
always land as PRs for human review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`tn/scripts/build_metro_outline.py`: one INSIDE anchor per county, each verified interior
against that county's own rings, all 95 correct, plus eight OUTSIDE anchors, one in each
neighbouring state), `state-counties.json` (`tn/scripts/build_state_counties.py`), and
`congress-districts.json`, `tn-senate-districts.json`, `tn-house-districts.json`
(`tn/scripts/build_legislative_boundaries.py`: statewide TIGERweb, congress from layer 4,
mapshaper-simplified with Douglas-Peucker, refused unless BOTH the 2,000-random-point agreement
gate and the 25 m fidelity ceiling pass). Rosters: `congress-roster.json`
(`tn/scripts/build_congress_roster.py`, from unitedstates/congress-legislators) and
`tn-{senate,house}-members.json` (`tn/scripts/build_tn_legislature_roster.py`, names and
vacancies from the Legislature's map on TNMap, party, e-mail and page from Open States `tn.csv`):
all count-guarded, all refreshed weekly by CI as reviewed PRs. The legislature builder refuses to
write when fewer than 30 Senate or 92 House seats are named, when Open States matches fewer than
90% of the named seats, when the state map answers an error, or when a district falls outside
the chamber's range or appears twice. A vacancy record cites the map query that answers for that
seat, because the service's HTML directory is switched off and a bare layer URL opens an error
page.

robots.txt is read before the first fetch through `scraper_common.require_robots_once`.
`data.openstates.org` answers its robots.txt with HTTP 403, which RFC 9309 files with a 404:
no policy, allow all. `tnmap.tn.gov` serves a 155-byte policy with no rule matching the
legislative map's path.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `tn/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
