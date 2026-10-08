# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Minnesota: a single-file, dependency-light web app. Click a point in Minnesota (or
search an address) and it reports every civic district containing that point and who
represents you there. It is a folder of the consolidated districtry repo, following the shape
`docs/EXPANSION_GUIDE.md` Part 2 sets out for a new state instance.

**IT IS LIVE, since the go-live change of 2026-09-30, at districtry.com/mn/.** It arrived DARK
in PR 1 and stayed dark through PR 2: `mn/**` was blanket-excluded from the Pages deploy and
`metros.json` deliberately carried no `mn` entry, which
`validate_instance_registration.py` holds together in BOTH directions — an entry in the
manifest while the folder is excluded would render a live landing card linking to a 404, and a
published folder the manifest does not name is a page the front door cannot reach. The
publishing change narrowed that exclude to `mn/data/state mn/data/source mn/scripts`, matching
`ia` and `mi`, and added the manifest row. `mn/WATCH.md`'s GO-LIVE section records what it
carried and what it deliberately did not.

It ships thirteen layers, the whole national tier — everything a U.S. state can serve from
national publishers, with no state-specific source between them.

**The four pre-built ones** are the offline anchors:
**County** (87, from Census TIGERweb, identity-only), **U.S. House** (8 districts, TIGERweb
geometry joined to the public-domain unitedstates/congress-legislators roster, refreshed
weekly), and **Minnesota Senate** / **Minnesota House** (67 and 134 districts, TIGERweb
geometry, naming nobody yet).

**The nine LIVE ones** carry no builder and no committed `data/app` file between them, so a
TIGER vintage roll reaches all of them on its own: three school tilings (**Unified** 322,
**Elementary** 8, **Secondary** 1), **ZIP Code** (1,385 ZCTAs intersecting the state's
envelope), **Township or City** (`county-subdivision`, 2,762) and **City** (`municipality`,
856), plus three nearest-3 point layers off the USGS National Map — **Police Station** (694),
**Fire & EMS Station** (1,484) and **Post Office** (1,199).

**MINNESOTA IS THE IOWA SHAPE AND NEITHER MICHIGAN'S NOR ILLINOIS'S, AND THE CARDS SAY SO.**
There is no village among the 856 incorporated places — every one carries the Census's city
descriptor — and a Minnesota city is NOT inside a township, so neither the city card nor the
township card names the other the way Michigan's village card must. The subdivision layer is
1,797 organized towns, 901 city placeholder records standing for 851 distinct cities (50 of
which cross a county line) and 59 unorganized territories.

**THE SECONDARY SCHOOL TILING HAS EXACTLY ONE FEATURE AND SHIPS ANYWAY** — Park Rapids for
grades 9-12 over the Pine Point district, 13.3 km². Iowa and Michigan both record a measured
ZERO there and correctly ship nothing; one feature is not zero, and a reader standing inside it
would otherwise be told no such district exists.

**THE ELEMENTARY CARD REFUSES THE SENTENCE EVERY SIBLING PRINTS.** Each sibling's elementary
card says the district runs no high school of its own, and TIGER's own fields contradict that
here: **seven of the eight** record LOGRADE PK and HIGRADE 12, the same span as a unified
district. So the cards print the grade range TIGER gives, say which tiling the district sits
in, and claim nothing about which grades it operates — gap `mn-elementary-district-grades`.
Exclusivity against the unified tiling is measured in both directions and is clean, so the
tiling itself is trustworthy; what the Census means by placing a PK-12 district in the
elementary tiling is not established and is not guessed at.

**ZIP CODE IS THE ONE LAYER DECLARING A `coverage` TEST, AND THE NEGATIVE POINT IS WHY.** A
ZCTA query has no state field, so it is fetched by envelope, and at the North Dakota anchor
TIGERweb answers **58059** — a genuine ZIP code, genuinely not Minnesota's. The test is the
shipped state outline, which is offline, so the browser gate proves it both ways: hidden at the
negative point with the permalink intact, present at the anchor. A layer that merely returned
nothing there would have been indistinguishable from one that was broken.

**THREE OF THE FOUR ANCHOR CARDS NAME NOBODY, AND EACH SILENCE IS RECORDED RATHER THAN IMPLIED.**
Both chamber cards enter the engine chamber factory's roster-miss path deliberately — district
identity plus the chamber's own directory, never an invented name — under gap
`mn-legislature-roster`, which says plainly that the Legislature publishes both rosters and
this instance has not built them. The County card is identity only under `mn-county-officers`.
A reader meeting three quiet cards should be able to find out why, which is what those records
are for. The nine live layers add four more of the same kind: `mn-school-board-members` (331
districts, each publishing its own board), `mn-township-officers` (1,797 towns electing three
supervisors plus a clerk and a treasurer under Minn. Stat. 367.03 — the largest per-unit roster
task any instance in this fleet has recorded), `mn-municipal-officeholders` (856 cities) and
`mn-elementary-district-grades`. Every one of them names the FORM from the state's own revisor
rather than assuming it, and none of them is an ask: they are bounded work this project may do
itself.

**THE FLAGSHIP LAYER THIS INSTANCE IS BUILT TOWARD IS `county-commissioner`**, and the
measurement that makes it cheap was taken before any code was written (2026-09-29). The
Minnesota Secretary of State publishes ONE statewide precinct layer —
`enterprise.gisdata.mn.gov`, `us_mn_state_sos/bdry_votingdistricts/FeatureServer/0`, 4,105
precincts — in which every precinct carries the districts it sits in as attributes, so SEVEN
layers dissolve out of one source: `ctycomdist` (447 commissioner districts across all 87
counties — 81 counties elect five and six elect seven), `pctcode` (precincts), `juddist` (10),
`swcdist_n` (117), `hospdist_n` (16), `parkdist_n` (3) and `ward` (274 wards in 76 cities, the
layer Illinois assembled county by county). **A single upstream service serving seven layers
is also a single point of failure for seven layers**, which is why `mn/WATCH.md` watches its
Service Modified stamp and its field names rather than only its endpoint.

**THE ROSTER WAS NOT SHUT, AND THE ROUTE THAT OPENED IT IS A PLAIN TEXT FILE** (2026-10-06).
The record here said the SoS's results service carries federal and state contests only, which
is true of that ArcGIS service and was read as true of the Secretary of State. The results
SITE publishes a `cntyRaces.txt` per election day on `electionresultsfiles.sos.mn.gov`, every
county commissioner contest in it, and `mn/scripts/build_mn_commissioner_roster.py` names
445 of 447 seats from the 2022 and 2024 generals plus seven specials, each dated to the
election that seated it (the Michigan certified-returns posture: a winner is not a sitting
commissioner, and the card, the 87 county pages and the index all say so). **A general carries
a WRITE-IN line and a primary does not** — the office name does not say which, the date does
not either (specials run on primary day), and a first draft that guessed from the candidate
count had to hold two August 2026 specials as undecidable. Five counties publish a name on
their own district map; the builder compares them weekly and a seat they name differently is
printed on its card beside the winner (Ramsey District 3 today). **Never read the results
site's own pages (`electionresults.sos.mn.gov`)**: they load a Radware bot manager, so the
builder finds election days by asking each Tuesday's directory on the files host instead.

**THE CITY CARD NAMES THE COUNCILS OF THE 43 CITIES OVER 25,000 FROM THE SAME FILES HOST**
(2026-10-07). `local.txt` carries every city contest, and
`mn/scripts/build_mn_city_councils.py` names 249 of 268 seats from the 2022 to 2025 generals
and their specials, each dated to the election that seated it, exactly as the commissioner
roster is. **HOW MANY SEATS SHARE ONE OFFICE IS NOT IN THE FILE**, so `SEATS` declares it per
city, from each city's own council page; 33 of the 43 pages were read on 2026-10-07 and every
one gave the same council size, and 194 of the 197 seats they name agree with the winner. The
three that do not are in `CITY_PAGE_SAYS` and print on the card beside the winner, and that
entry FAILS once the results stop naming the recorded winner. **RANKED-CHOICE CITIES ARE READ
FROM FIRST CHOICES ONLY**, because the later rounds are not in the file: a seat is named only
where one candidate holds a majority of first choices, or the Droop quota in a multi-seat race,
so Minneapolis's and St. Paul's mayors name nobody and say why. **A MEMBER ELECTED TO A SECOND
SEAT HAS LEFT THE FIRST**: Andover, Minnetonka and St. Cloud each elected a council member
mayor, and the first draft named that person for both seats, so the seat they left now names
nobody and the check fails on any name carried twice in one city. A seat the files cannot
settle — a tie, a write-in winner, a special still pending — names nobody rather than a guess.
Ten city sites refused this client (seven behind Akamai, two Cloudflare, Eagan a captcha on
robots.txt itself) and were not read any other way; `mn/WATCH.md` lists them.

**THE SCHOOL DISTRICT CARDS NAME THE BOARD FROM THE SAME FILES HOST** (2026-10-07,
`mn/scripts/build_mn_school_boards.py`): 1,882 of 2,099 seats on 326 boards, from each
election day's `sdrace.txt` since the 2022 general, every name dated. The results name a
district by its state number and the map by a Census id, so the Department of Education's
own district layer joins them, by name and then by interior point, one to one. **A BOARD'S
SIZE IS COUNTED, NOT DECLARED**: terms are four years and staggered (Minn. Stat. 123B.09
subd. 1), so the seats elected at the two most recent regular elections two years apart are
the board, and 6 and 7 seats is what the count gives on almost every board. **WHOSE SEAT A
SPECIAL ELECTION FILLED IS SETTLED BY STATUTE OR NOT AT ALL**: a special is held only for a
vacancy two years or more before the term ends (subd. 5b), which places a special held on
the same day as a regular election in the older group; any other special leaves the seats
it could have touched naming nobody, listing who they could be. A term that has certainly
ended names nobody too. The secondary card names no board, because Pine Point's voters elect
Pine Point's board and not Park Rapids's.

**`watershed-district` (2026-10-06) IS THE FIRST LAYER HERE FROM A SECOND STATE OFFICE**, the Board of Water and Soil Resources: 45 watershed districts, 16 metro watershed management organizations and three county-run areas, the bodies that manage water by watershed and can levy for it — the done standard's special-district level. Its builder (`mn/scripts/build_mn_watershed_districts.py`) reads BWSR's feature service on the same enterprise host, because the Geospatial Commons download host refuses this client in robots.txt. **THE PUBLISHER'S POLYGONS OVERLAP AND SHIP AS DRAWN**, so its card reads every body the map puts the point in rather than the first; nobody is named because every one of these boards is appointed. It declares the same state-outline `coverage` test as ZIP Code, because its empty card states a fact about Minnesota, and it is both an offline anchor and a negative-point hide in the smoke test.

**TWO HOSTS ARE MEASURED AND NEITHER CHANGES THE ANSWER.** `www.mngeo.state.mn.us` serves a
Radware Bot Manager captcha to this project's token — obeyed, never worked around, and it
costs nothing because the data is on the separate enterprise host. `gis.data.mn.gov`'s
robots.txt allows this client with **Crawl-delay: 60** binding on `*`, which is honoured and
makes a full page-through slow rather than impossible. **Do not let a later pass read "MnGeo is
blocked" as "Minnesota publishes nothing"** — that is the Knox shape, and this instance's
whole growth path sits on the host MnGeo is not.

**There is no build step, no framework, and no server-side code.** The app — styles, engine,
and layer modules — lives inline in `index.html`. `sw.js` is the service worker;
`data/app/*.json` are runtime-fetched data files; `data/state/` carries the bootstrap state
config (`build_congress_roster.py` reads its FIPS/USPS/seat count — it ships in the repo and
is excluded from the Pages deploy). **IT SHIPS ONE SUB-PAGE, `sources.html`, AND IT WAS ALMOST PUBLISHED WITHOUT ONE.** Through
PR 1 and PR 2 this instance carried no sub-pages at all, on a reason that was correct while it
was dark — a masthead link to a file the tree does not contain is a 404 the moment the page is
published, which `validate_instance_assets.py` says out loud. What that reasoning did not
answer is what happens when the page IS published: every sibling instance answers *where did
this answer come from* on a provenance page, and Minnesota would have been the only live
instance with no way to ask. So the go-live change shipped the page rather than the omission,
and it cost no research — each of the thirteen `layers[]` entries already carried a full
`source` block (`generate_metro_files.py` refuses a `sources_page` instance where one does
not), so the layer matrix and the credit rows generate from what was already there. The shell
was cloned from `in/sources.html` and localized; the Indiana sweep is 0 hits.
`faq.html` and `history.html` are still absent, and deliberately: both are hand-written prose
rather than generated, so each is its own change, and `mn/WATCH.md` carries them. The
worksheet therefore has `sources_page` and no `history_page` — those generators are opt-in and
generate nothing for an instance that does not ask.

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: Minnesota (`minnesota`) — https://districtry.com/mn/
- Geocoders: address Photon (Minnesota-bounded type-ahead); unbounded Photon (whole-coverage, sibling-metro lookup); POI Nominatim (office-address pin lookup, Minnesota-bounded, serial >=1s queue)
- Ground truth: 44.97440,-93.26550 (downtown Minneapolis, Hennepin County) → county Hennepin County; us-house 5; mn-senate 61; mn-house 61A; mn-judicial-district Fourth Judicial District; voting-precinct Minneapolis W-7 P-6; county-commissioner Hennepin County Commissioner District 3; watershed-district Mississippi Watershed Management Organization. Negative point 46.87720,-97.05000 (inside Cass County, NORTH DAKOTA, about 20 km west of Fargo — outside Minnesota and outside every other instance in the fleet, and inside permalink_gate (minLng -97.40) so the app answers the click and every shipped layer correctly returns nothing. Measured: 0 hits in every shipped geometry file, TIGERweb's county layer names Cass County STATE 38 (control: the anchor returns Hennepin County STATE 27), and no outline in fleet-outlines.json contains it. TWO POINTS WERE TRIED FIRST AND BOTH FAILED FOR REASONS WORTH RECORDING, because each looked obvious. LAKE SUPERIOR: Minnesota's TIGER county fabric is WATER-INCLUSIVE out to the international boundary, so a point in open Lake Superior at 47.6, -90.0 is named Lk Superior by TIGERweb's hydrography and is still INSIDE Cook County, and a point offshore of Duluth is inside the city of Duluth. Water is not outside the state here. WORTH COUNTY, IOWA (43.45, -93.37): correct on every static test — 0 hits in every shipped geometry file, TIGERweb naming Worth County STATE 19 — and it MADE THE BROWSER LEAVE. fleet-outlines.json puts it inside Iowa, so placeOwner hands the selection off to districtry.com/ia/ and the page navigates away; the smoke test's coverage-band probe then timed out looking for a button on a blank document. A NEGATIVE POINT MUST BE OUTSIDE EVERY LIVE INSTANCE, not only outside this one. Iowa's own negative point (43.65, -93.37) sits inside Minnesota and will start handing off the day this instance goes live — recorded in mn/WATCH.md as a go-live item on ia/, not a defect in this change.).
- Layers: 17 registered (political 5, safety 2, schools 3, geography 7); `registerLayer(` floor 15. Debug namespace `window.MinnesotaExplorer`.
- Scheduled workflows: `update-mn-congress-roster.yml` (Mon 13:40 UTC); `update-mn-commissioner-roster.yml` (Tue 13:40 UTC); `update-mn-city-councils.yml` (Tue 14:10 UTC); `update-mn-school-boards.yml` (Wed 14:10 UTC).
- Source registry: `mn/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/mn/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/mn/ node mn/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 mn/scripts/validate_index.py mn/index.html

# Generated-region gate: per-instance facts live ONCE in mn/metro-worksheet.json;
# GENERATED regions are emitted from it. NEVER hand-edit a GENERATED region:
pip install -c scripts/requirements.txt jsonschema
python3 scripts/generate_metro_files.py            # regenerate in place (all instances)
python3 scripts/generate_metro_files.py --check    # the CI drift gate

# Engine parity: the ENGINE fences are composed from the repo-root engine/ —
# edit a block THERE and recompose, never inside an instance file:
python3 scripts/compose_app.py            # splice engine/ into every instance
python3 scripts/compose_app.py --check    # the CI drift gate

# The Data gaps panel's content, emitted from the fleet guidebook:
python3 scripts/build_coverage_gaps.py --check --metro minnesota --out mn/data/app/coverage-gaps.json
```

**THE NEGATIVE POINT IS IN NORTH DAKOTA, AND THE TWO THAT FAILED BEFORE IT ARE WORTH KNOWING.**
`mn/metro-worksheet.json`'s `negative_point.note` carries both in full. Lake Superior does not
work: Minnesota's TIGER county fabric is water-inclusive to the international boundary, so a
point in open lake at 47.6, -90.0 is named `Lk Superior` by TIGERweb's hydrography **and is
still inside Cook County**. Worth County, Iowa passed every static test — 0 hits in all five
shipped files, TIGERweb naming Worth County STATE 19 — and **made the browser leave**:
`fleet-outlines.json` puts it inside Iowa, so `placeOwner` handed the selection to
`districtry.com/ia/` and the smoke test timed out looking for a button on a blank document.
**A NEGATIVE POINT MUST BE OUTSIDE EVERY LIVE INSTANCE, not only outside its own.** Iowa's own
negative point sits inside Minnesota, and Wisconsin's does too; both started handing off the
day this instance was published, and both were settled BEFORE it — in #1267 and #1268, by
having those two instances' checks REFUSE `fleet-outlines.json` rather than by moving a point
that had been measured correctly. That is the better remedy and it generalises: the fleet was
swept for every other coordinate Minnesota's outline would claim (48 pairs across every
`scripts/*.mjs`, `*/scripts/*.mjs`, `*/metro-worksheet.json` and `metros.json`) and those two
were the only ones. **This instance's own negative point does NOT yet use that pattern**, and
that is a measured choice rather than an oversight: Cass County, North Dakota is outside every
live instance, so `placeOwner` finds no owner and the app selects the point locally. It breaks
the day a Dakotas instance ships, silently, as a timeout waiting for a masthead button —
recorded in `mn/WATCH.md` as a Dakotas blocker.

**Sandboxed environments (Claude Code web):** the headless browser cannot reach the Leaflet
CDN. The repo root's `.claude/settings.json` SessionStart hook runs `scripts/vendor_leaflet.sh`,
which vendors Leaflet into `mn/scripts/vendor/leaflet/` (gitignored); `mn/scripts/smoke_test.mjs`
serves it same-origin. Production and GitHub Actions CI reach the CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Minnesota-specific lives in the `METRO:BEGIN config` block (worksheet-generated) and
this instance's own module code, which is the `STARTER MODULES` section.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the three district layers use the fenced factory helper `registerIlgaChamber`. **The two
chamber registrations pass `loadNoRoster`, a function returning an empty object**, because the
factory calls `opts.loadRoster()` unconditionally and an empty roster is the honest input — it
enters the factory's own roster-miss path rather than needing an engine change. When
`mn-{senate,house}-members.json` ship, those two become real file loaders and nothing else
about the registration moves.

Two invariants pervade the code: the **stale-async guard** (`if (seq !== state.sequence)
return;` after every await) and **per-layer failure isolation** (a layer's failure shows a
Retry inside its own card, never breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name, which is
what three of this instance's four cards do today. External strings always render through
`sanitize()`/`textContent`. Roster refreshes always land as PRs for human review — never as
direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`mn/scripts/build_metro_outline.py`), `state-counties.json`
(`mn/scripts/build_state_counties.py`), and `congress-districts.json`,
`mn-senate-districts.json` and `mn-house-districts.json`
(`mn/scripts/build_legislative_boundaries.py`).

**THAT CHAMBER BUILDER TAKES NO PER-CHAMBER ARGUMENT AND REFUSES ONE**, because rebuilding one
chamber alone is the defect it exists to prevent: mapshaper builds topology WITHIN one file, so
a shared edge between a Senate district and the two House districts inside it only survives
identically if both came off one `combine-files` run. It refuses to write unless three gates
pass — a 2,000-random-point agreement gate per layer, an EXACT cross-layer nesting check at
zero tolerance, and a fidelity ceiling measured against the source. Its `--check` re-runs the
nesting half offline in CI.

**MINNESOTA NESTS BY LETTER**, not by arithmetic: Senate 61 holds House 61A and 61B, where
Iowa's Senate 26 holds House 51 and 52. Porting Iowa's builder failed loudly on that rather
than silently, which is the right failure — its child-key arithmetic matched no Minnesota
BASENAME and the gate reported that no pairing had been checked.

**`FIDELITY_MAX_M` IS 34.0 AND IS PINNED, NEVER RECOMPUTED PER RUN.** A ceiling re-derived from
the source on every run can never fail, because it rises whenever the source gets coarser. 34.0
comes from Minnesota's OWN median staircase step — how far the true line runs before it turns —
measured 2026-09-29 at 31.2 m (mn-house) and 37.6 m (mn-senate), with the instrument first
validated against two states that had published a figure (Iowa 42.2 m against a published 43.4,
Illinois 19.6 m against 19.7). The ceiling is taken from the finer chamber. A redistricting
re-opens it: re-measure the step on the new lines rather than carrying the number forward.

The one roster, `congress-roster.json` (`mn/scripts/build_congress_roster.py`, from
unitedstates/congress-legislators), is count-guarded and refreshed weekly by CI as a reviewed
PR.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and
its officeholder sourcing in the same change, floor every scraped count, and record what a
publisher does NOT publish rather than guessing. When a layer ships, its row in
`mn/metro-worksheet.json` (`layers[]`, with a `source` block) is what puts it in every gate.
Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the same change.
