# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Mississippi: a single-file, dependency-light web app. Click a point in Mississippi (or
search an address) and it reports every civic district containing that point and who represents
you there. It serves at **districtry.com/ms/** as a folder of the consolidated districtry repo —
following the Wisconsin/Iowa shape (`docs/EXPANSION_GUIDE.md` Part 2), not the Illinois
root-scripts shape. **IT IS PUBLISHED** since Adam's word of 2026-10-16. It arrived dark on
2026-10-15 (no `metros.json` entry, `ms/**` blanket-excluded from the Pages deploy), and the
go-live change narrowed that exclude to the build inputs the siblings exclude, registered the
instance and regenerated every surface that counts the fleet. `ms/WATCH.md` keeps the go-live row
with its date, and `docs/MS_EXPANSION_PLAN.md` is the record of the launch.

**The national tier** draws its shapes from a national publisher and names people from a national
roster or the Mississippi Legislature: **County** (82, Census TIGERweb, the coverage ring, and the
card that names the county's five supervisors), **U.S. House** (4 districts, TIGERweb geometry
joined to the public-domain unitedstates/congress-legislators roster), **Mississippi Senate** and
**Mississippi House** (52 and 122 districts, TIGERweb geometry joined to the legislature's own
member gallery and member profiles), the LIVE TIGERweb fabric — **City, Town or Village**
(`municipality`, 300), **School District** (137) and **ZIP Code** — and three nearest-N layers from
the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**). Beside it,
**County Supervisor District** (`county-supervisor`) draws the five districts of each of the 25
counties whose current lines are confirmed (12 from the Census's lines, 13 from other published
maps), and is hidden in the other 57. **Tribal Government** (`tribal-government`) draws the
Mississippi Band of Choctaw Indians' reservation and its off-reservation trust land, the only
tribal land the Census draws in the state, and names the Tribal Chief and the seventeen council
members from the band's own page. Four court layers draw the districts of the four courts whose
judges are elected from districts and name those judges: **Supreme Court District**
(`ms-supreme-court`, 3), **Court of Appeals District** (`ms-court-of-appeals`, 5), **Chancery
Court District** (`ms-chancery-court`, 20) and **Circuit Court District** (`ms-circuit-court`, 23
until 1 January 2027 and 22 from that day).

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
in 70 counties the Census's 2026 layer still carries its own 2020 edition, and the planning
measurement found those lines put 34% of Madison County's residents in the wrong district, 16% of
Lee's and 9.5% of Harrison's. So a supervisor district is drawn only where its current lines are
confirmed (Adam's choice, "Confirmed only", on the decision card of 2026-10-15), and the rest is
gap `ms-supervisor-district-lines`. **IN MOST OF THOSE COUNTIES THE CENSUS'S LINES ARE OLDER THAN
THE 2010 CENSUS, AND THIS FILE SAID OTHERWISE UNTIL 2026-10-16**: it called them "the lines drawn
on the 2010 census", which nothing had measured. Measured that day by `--survey` against the
Census's 2010 edition (`tigerWMS_Census2010` layer 28, the January 1, 2010 vintage, whose POP100 is
the 2010 census's own count of each district): in 52 of the 64 counties whose 2020 edition no
longer balances, it puts every 2020 resident in the same district as the 2010 edition, so the
Census's lines there have moved nobody since January 1, 2010, and in 49 of those 52 the districts
were already more than 10% apart on the 2010 census's own counts. Those 49 held 1,504,204 of the
state's 2,961,279 residents in 2020, so for half the state the only statewide map of the supervisor
districts that was found still places every resident where it did in January 2010 —
publishing-reform evidence. Harrison is one of the 49: its own map server's descriptions name a
plan adopted in 2013 on the 2010 census, and the Census's lines there place every resident as the
2010 edition does, 35.8% apart on that census. Seven of the 49 (Coahoma, Greene, Harrison, Hinds,
Lauderdale, Sunflower and Yazoo) hold a 2020 block of more than 1,000 people, which may be a prison
or a campus that a plan can leave out of its count, so their figures may overstate the imbalance on
a plan's own count; estimated from that block's 2020 count against an equal share, leaving it out
could account for the whole figure only in Coahoma and Sunflower, and the other 47 held 1,456,843
residents, still about half the state. **THE DIRECTORY ALSO PRINTS SUPERVISORS' OWN ADDRESSES AND
TELEPHONES IN SOME COUNTIES**, which may be homes: a board address or telephone is carried only
where at least three of the five supervisors print the same one, because five people do not share a
home — 76 counties have an address and 68 a telephone on the 2026 edition, and Amite, Coahoma,
Humphreys, Lincoln, Sunflower and Yalobusha, which print a different address for each supervisor,
have none. **A SUPERVISOR'S OWN TELEPHONE IS CARRIED AND THEIR OWN ADDRESS NEVER IS** (Adam,
2026-10-17, for the whole fleet: "if the official government source uses personal phone numbers,
we publish those"): a number printed for one supervisor that is not the board's, and Copiah's
"(c)" numbers, ride on that supervisor's row, 81 of them on the 2026 edition. **THE SAME DIRECTORY
NAMES THE FIVE ELECTION COMMISSIONERS, AND THEIR NAMES AND OWN TELEPHONES ARE CARRIED**: each
commissioner's line runs on from the name to the commissioner's own address, which may be a home,
and on 45 lines in nine counties to a telephone. The builder keeps the name (everything before the
line's first run of dots) and a last field that is a telephone and nothing else, never the address
between them, and its errors name only the county and the district.
All 410 were named on the 2026 edition, numbered District 1 to 5 in every county, even the five
whose supervisor districts are beats. The County card lists them; the supervisor-district card
names the one with the same number only where the directory uses the same word for both lists.

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
to `CENSUS_COUNTIES` after looking.

**THIRTEEN MORE ARE DRAWN FROM OTHER PUBLISHED MAPS** (`COUNTY_SOURCES` in the same builder, eight
on 2026-10-15 and five on 2026-10-16). A survey of every county's website and its planning and
development district's (`/mnt/project-files/ms/supervisor-map-survey/`) found 14 of the 70
old-edition counties publishing lines of their own, and in Tippah a current plan whose publisher it
did not establish. Twelve of the 14 and Tippah are drawn because each publication names or proves
its own currency, and the build re-reads that evidence every time: a layer named for its adoption
("Supervisor Districts Adopted 2022", Rankin's 2021), population figures per district that equal the
2020 census's own block counts (six of the first eight publish them, and for Hinds, whose layer name
gives no year, they are the witness), a service description saying the lines were "approved 2023 as
a result of the 2020 US Census" (Harrison), a printed map on the county's own website, pinned by its
SHA-256 and compared with the layer by eye (Lamar's, dated 8/09/2022, and Pearl River's, "Effective
January 1, 2023"), or a map of the county's voting precincts that follows those lines and not the
Census's (Lee, Pearl River, Perry, Covington and Tippah, below). Copiah, Hinds, Madison, Rankin,
Simpson and Warren come from the Central Mississippi Planning and Development District's map
viewers, Harrison from the county's own map server, Lamar and Covington from the parcel viewers
their websites link to, Pearl River and Perry from the Find My Supervisor maps their websites link
to, Lee from a map published online as Lee Supervisor Districts 2022, which only the name of the
account it sits in ties to the county, and Tippah from a map published online as the Tippah County
2022 Redistricting Map, in a mapping company's account, which only the titles of that company's maps
tie to the county (the county's website could not be read from here: its robots.txt resets the
connection). **TIPPAH'S LAYER DESCRIBES ITSELF WRONGLY AND IS NOT BELIEVED ABOUT ITSELF**: its
description reads "Supervisor_Districts_2010" and its population fields sum to 22,833 people, not
the county's 21,815 in the 2020 census, so neither is read as evidence, and the precinct map is the
witness. Covington's layer draws District 2 as two features, which the build joins into one district
(`parts` in its entry, which fails once the layer draws each district once). Each must also balance
on the 2020 blocks (4.39% to 8.82%), keep the 2020 edition's district numbers, and the Census's
current lines there must STILL be its 2020 edition's, so the day the Census receives a county's new
lines the build stops and a person moves it to `CENSUS_COUNTIES`. **NOTHING TRACED SHIPS**: each
2020 block goes to the district covering most of it and a district is drawn as the union of its
blocks, so every vertex is the Census Bureau's (the Iowa method), and where a plan publishes a
population per district the blocks reproduce it to the person. Rankin's plan leaves out two blocks
(3,633 people in a block with 3 housing units and 157 in one with none), which the build re-reads
from the Census and the card mentions without saying what they are, because that is not measured. On
the same blocks the Census's old lines give 144,320 of these thirteen counties' 1,056,954 residents
a different district number. The other two (Coahoma and Wilkinson) publish lines that differ from
the Census's, but nothing found shows they are the plan adopted after the 2020 census, so they wait
(`ms/WATCH.md`).

**A PRECINCT MAP IS EVIDENCE ONLY AS A MEASUREMENT, AND THE BUILD TAKES IT ON EVERY RUN**
(`precinct_witness()` in the same builder). Each 2020 block's residents are placed in a precinct at
the block's internal point, and each precinct belongs to the district it names (Lee's, Pearl River's
and Tippah's name one) or else to the district holding most of its residents under the lines being
tested (Perry's and Covington's name none). Measured 2026-10-16, the precinct maps put 10 of Lee's
83,343 residents, none of Pearl River's 56,145, 8 of Perry's 11,511, 17 of Covington's 18,340 and
none of Tippah's 21,815 in a different district from the drawn lines, against 13,351, 4,919, 444,
896 and 669 for the Census's, and every resident in exactly one precinct. The build stops if a
precinct map puts more than 0.5% of a county's residents in a different district, fewer than 50 in a
different district from the Census's (it would no longer tell the two apart), or more than 1% in no
precinct or two. Only each precinct's name and district are read: Coahoma's 2022 precinct and
supervisor layers also carry population by race, and none of that is asked for. A county's own
district layer is asked only for the fields the checks read (`layer_fields()`), because Tippah's
carries population by race as well. **HOW INDEPENDENT EACH PRECINCT MAP IS DIFFERS, AND IS STATED
RATHER THAN ASSUMED.** Lee's describes itself as the Circuit Clerk's master precinct split map of
2024, in a different account from the district map. Perry's is a separate 2023 precinct service in
the same account as its districts. Pearl River's sits in the same map service as its districts, so
there the printed map and the supervisors' names, which match the Secretary of State's directory,
carry more of the weight. Covington's is the precinct layer the same parcel viewer draws as
Precincts 2023, in the same account as its districts. Tippah's, the Tippah County Circuit Clerk
Map's 2024 precincts, is in the same mapping company's account as its districts, so it shows that
company's two maps agree with each other and not with the Census's, and nothing more about who
adopted the lines. **WHY COAHOMA IS NOT DRAWN ON ITS PRECINCT MAP**: the layer its emergency
management agency publishes as Voting Precincts 2022 carries exactly the fields of the Supervisor
Districts 2022 layer beside it (population by race, a target population and the difference from it),
which are a redistricting plan's fields and not a precinct's, so it witnesses nothing the district
layer does not; and the county's own website still points at the old lines.

**THE MAP SERVER'S OWN GEOJSON WAS MEASURED WRONG, SO EVERY POLYGON IS READ AS ARCGIS JSON.**
Asked for GeoJSON, Lamar's layer sometimes sent District 3, whose two parts ArcGIS's own JSON gives
as two outer rings, as one polygon whose smaller part (3.0 km2, 1,317 people) is a hole outside the
larger; the same query was right minutes before and after. The population checks caught it as
people living in no district. The builder converts rings itself by ArcGIS's rule (clockwise outer,
counter-clockwise hole) and repairs a ring only when the repair changes its area by less than one
part in a million.

**THE LAYER'S COVERAGE TEST READS A LIST OF THE DRAWN COUNTIES, NOT THE DISTRICTS FILE.** The test
runs on every selection whether or not the layer is on, and reading the districts file made a
reader's first selection download it: 150 KB gzipped for twenty counties, measured 2026-10-15. It
now finds the point's county in `state-counties.json`, which the County card loads anyway, and
looks it up in `ms-supervisor-counties.json` (under 1 KB), which the builder writes beside the
districts and its `--check` holds to them. Within a few metres of a county line (5.0 m at most,
measured 2026-10-16) the two files can disagree, and there the layer follows the County card. The
smoke test fails if the districts file is requested with the layer off. **The shapes are the county
outline's too**: `state-counties.json` was rebuilt with Douglas-Peucker on 2026-10-15 because
the Visvalingam simplification it shipped with put a county line up to 184.5 m from the
Census's, with 54 counties over 25 m, and the supervisor builder's county witness holds the two
files to each other at 4,000 points. **That rebuild fixed the stray and made the other measure
worse**: the ground answered with the wrong county, or none inside the state, went from 23.1 to
40.7 km² (equal-area, against the full-precision lines), which the first measurement never looked
at. The file is now drawn at a 5 m interval under an 8 m ceiling, Adam's choice for the newer
states' county files ("Finest", 2026-10-15): 5.6 m and 8.1 km², in a file of 295 KB gzipped
against 139 KB, and the six court maps, which are dissolves of it, were rebuilt with it. The
supervisor districts and the legislature's three maps were redrawn at the same setting on
2026-10-16, Adam's choice before the instance opened ("Finer first"); each builder's docstring
carries what that changed, and `ms/WATCH.md` the row.
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

**THE BAND'S COMMUNITIES ARE WORDS ON THE CARD, NEVER SHAPES.** Each council member represents
one of the band's communities (Bogue Chitto, Conehatta, Pearl River and the rest), which the band's
page prints beside the name, so the card carries it beside the name. The Census draws no tribal
subdivision on this land, so this app has no outline for any community, and the card's
districts sentence says so and points at the names rather than saying no council seat belongs to
the land, which would be false here (`scripts/build_tribal_areas.py`, `council_has_districts`).

**THE COURT DISTRICTS ARE LISTS OF WHOLE COUNTIES, AND THE CHANCERY AND CIRCUIT MAPS CHANGE ON 1
JANUARY 2027** (`ms/scripts/build_ms_court_districts.py`, its `--check` in CI). Each map is a
dissolve of `state-counties.json`, so neighbouring districts share their edges exactly, and nothing
is simplified again after the dissolve. The county lists are parsed out of copies kept in
`ms/data/source/courts/` (each court's own district page, and the four laws that write the chancery
and circuit districts: Senate Bill 2768 and House Bill 1544 of 2025, House Bills 1 and 580 of 2026),
and `--check` re-hashes every copy against the SHA-256 recorded when it was fetched. The two 2025
laws write both the map in force now and the map from 1 January 2027 into the Code, so both ship:
the app draws today's map until 06:00 UTC that day (midnight in Mississippi) by the reader's clock,
decided once when the page loads, and the 2027 map from then on. Today's half of each law is held to
the court's own page district by district, and a 2026 law that writes a district the 2025 laws also
write must give it the same counties on every date. The same laws enact a third map from 1 January
2031 (George County to the Nineteenth Chancery District; Holmes, Humphreys and Yazoo out of the
Twenty-second Circuit District, which ends), which is parsed and held to `MOVES_2031` and not built,
and the builder refuses to write a map on or after the day it stops being the law. The four laws
were found by reading the short title of every measure the Legislature lists for the 2025 and 2026
regular sessions and both extraordinary sessions, and `ms/scripts/validate_sources.py` repeats that
scan monthly, so a later law is reported rather than missed.

**THE COURT OF APPEALS SPLITS TEN COUNTIES BY VOTING PRECINCT, AND THAT LINE IS NOT DRAWN.** For each
of Attala, Grenada, Hinds, Jones, Leake, Madison, Montgomery, Panola, Tallahatchie and Wayne, the
court's page names the precincts that belong to one district and gives the rest of the county to
another. This app has no map of those precinct lines (the court's page shows its districts only as a
picture), so each of the ten is one feature naming both districts, and its card names both
districts' judges and says which district takes the listed precincts (gap `ms-coa-precinct-lines`).
The chancery and circuit subdistricts, from each of which one judge of a district is elected, are
not drawn either, so those cards list every judge of the district (gap `ms-court-subdistricts`).

**THE JUDGES COME FROM THE JUDICIARY'S OWN LISTS, AND THE TRIAL-COURT LISTS TRAIL THE BENCH**
(`ms/scripts/build_ms_judges.py`, weekly as a reviewed PR, `--selftest` and `--check` in CI). The
Supreme Court's and the Court of Appeals' pages of their judges are HTML; the chancellors and circuit
judges are two PDF lists, dated 1 August 2025 and 4 February 2026 when they were read on
2026-10-15. Five changes since those dates, each from the court's own news or the Governor's own
announcement, are applied on top (`CHANGES`): two chancellors replaced; two chancellors who died, in
the 5th and 9th Chancery Districts, whose cards say so and that no appointment had been announced
when the news was read; and a circuit judge who joined the Supreme Court and was replaced. Every entry fails the build once the list catches up with
it, and a person then re-reads the list and deletes the entry. **THE PDF LISTS ALSO PRINT THE JUDGES'
STAFF, SOME WITH STREET ADDRESSES**: the parse reads only each judge's name, the judges' own
addresses and telephones are not carried, and neither PDF is ever written into the repository. A
trial list's district headings name their counties, so the builder records which map the list
describes, and a card names chancellors or circuit judges only from a list describing the map it
draws. **SO FROM 1 JANUARY 2027 THE CHANCERY AND CIRCUIT CARDS NAME NOBODY** until a list describing
the 2027 districts appears, which the lists' lag makes likely to be months; `ms/WATCH.md` says how to
close that before the day.

**THE ZIP LAYER HIDES OUTSIDE MISSISSIPPI.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP (the Alabama negative point gives 36925,
measured 2026-10-15). The coverage test reads the shipped outline, and the smoke test asserts both
halves.

**There is no build step, no framework, and no server-side code.** The app — styles, engine,
and layer modules — lives inline in `index.html`. `sw.js` is the service worker;
`data/app/*.json` are runtime-fetched data files; `data/state/` carries the bootstrap state
config (`build_congress_roster.py` reads its FIPS/USPS/seat count — it ships in the repo and is
excluded from the Pages deploy). `sources.html` carries the generated per-layer provenance
matrix and `faq.html` the common questions; `congress.html` and `state-legislature.html` are
generated by `scripts/build_legislator_pages.py` with their tables from
`scripts/build_officeholder_tables.py`, and `county-supervisor.html` with its per-county pages by
`scripts/build_county_pages.py`. All of them compose from the same shared engine blocks as every
other instance via `scripts/compose_app.py`.

**EACH COUNTY HAS A BOARD OF SUPERVISORS PAGE**, `ms/county-supervisor/<county>.html`, indexed
from `ms/county-supervisor.html` and generated by `scripts/build_county_pages.py` from the same
file the County card reads: the five supervisors as the Secretary of State's directory lists them,
each with the telephone the directory prints for that supervisor alone where it prints one, the
board's office only where the directory prints one address or telephone for at least three of the
five, and the directory's page as the source. The election commissioners are not on these
pages, because they are not members of the board, and each page says whether the map draws that
county's districts.

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: Mississippi (`mississippi`) — https://districtry.com/ms/
- Geocoders: address Photon (Mississippi-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Mississippi-bounded, serial >=1s queue)
- Ground truth: 32.30380,-90.18220 (the State Capitol, Jackson, Hinds County) → county Hinds County; us-house 2; ms-senate 29; ms-house 67. Negative point 32.48000,-88.25000 (near York, Sumter County, ALABAMA, about 12 km east of the Mississippi line — outside Mississippi and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-15: TIGERweb's county layer names Sumter County, Alabama at this point (control: the Capitol anchor returns Hinds County, Mississippi), and the Census's ZIP layer answers 36925 there, which is the neighbouring-state answer the ZIP layer's coverage test exists to hide. ALABAMA BECAUSE NO INSTANCE SERVES IT and it is not on the next-states list; Louisiana, Arkansas and Tennessee, which share Mississippi's other borders, were passed over so this point does not have to move when any of them is live.).
- Layers: 16 registered (political 9, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.MississippiExplorer`.
- Scheduled workflows: `update-ms-congress-roster.yml` (Mon 18:11 UTC); `update-ms-legislature-roster.yml` (Tue 18:11 UTC); `update-ms-county-officials.yml` (Wed 18:11 UTC); `update-ms-judges-roster.yml` (Thu 18:11 UTC); `ms-validate-sources.yml` (1st of month 20:13 UTC).
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

# Court districts (offline: every kept page and law re-hashed, every county list
# re-read, and the six maps held to them, the 2027 and 2031 moves included):
python3 ms/scripts/build_ms_court_districts.py --check

# Judges (offline: the parse and the change table on literals, then the shipped
# file against its shape, its counts and the court maps):
python3 ms/scripts/build_ms_judges.py --selftest
python3 ms/scripts/build_ms_judges.py --check

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
(`ms/scripts/build_state_counties.py`, Douglas-Peucker at 5 m, refused unless the 8 m fidelity
ceiling passes), `ms-supervisor-districts.json` (`ms/scripts/build_ms_supervisor_districts.py`, the 25
confirmed counties, 12 from the Census and 13 from other published maps resolved to whole 2020
blocks, in one mapshaper run so a shared line is simplified once) with `ms-supervisor-counties.json`
(the drawn counties' list, written by the same build, which the layer's coverage test reads), and
`congress-districts.json`, `ms-senate-districts.json`,
`ms-house-districts.json` (`ms/scripts/build_legislative_boundaries.py` — statewide TIGERweb,
mapshaper-simplified with Douglas-Peucker at 5 m, refused unless BOTH the 2,000-random-point
agreement gate and the 8 m fidelity ceiling pass), and the six court maps,
`ms-{supreme-court,court-of-appeals,chancery-court,circuit-court}-districts.json` and the
`ms-{chancery,circuit}-court-districts-2027.json` pair (`ms/scripts/build_ms_court_districts.py`,
dissolved from `state-counties.json`). Rosters: `congress-roster.json`
(`ms/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`ms-{senate,house}-members.json` (`ms/scripts/build_ms_legislature_roster.py`, from the
legislature's own pages) and `ms-county-officials.json` (`ms/scripts/build_ms_county_officials.py`,
from the Secretary of State's directory) and `ms-judge-roster.json` (`ms/scripts/build_ms_judges.py`,
from the Judiciary's own lists) — all count-guarded, all scheduled weekly in CI as reviewed PRs. The tribal land is `tribal-areas.json` and its names `tribal-councils.json`, both
written by the fleet's shared `scripts/build_tribal_areas.py` through the one land-to-government
join every instance uses (`data/tribal-government-join.json`); the council is re-read weekly from
the band's own page by `scripts/tribal_council_scraper.py` in the fleet's
`update-tribal-councils.yml`, and the land is rebuilt only when the Census redraws it. `scripts/validate_chamber_rosters.py` holds both chamber files to one record per
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
