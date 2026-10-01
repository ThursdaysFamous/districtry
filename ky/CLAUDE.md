# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Kentucky: a single-file, dependency-light web app. Click a point in Kentucky (or
search an address) and it reports every civic district containing that point and who
represents you there. It is a folder of the consolidated districtry repo, following the shape
`docs/EXPANSION_GUIDE.md` Part 2 sets out for a new state instance.

**IT IS PUBLISHED.** PR 1 arrived DARK on 2026-09-30 — `ky/**` blanket-excluded from the
Pages deploy, no `ky` entry in `metros.json` — and the go-live change the same day narrowed
that exclude to the granular set the siblings use, registered the instance and regenerated
every surface that counts the fleet. `validate_instance_registration.py` holds the exclude and
the manifest together in BOTH directions, which is why they moved in one change: an entry in
the manifest while the folder was excluded would have rendered a live landing card linking to
a 404. `ky/WATCH.md`'s GO-LIVE section is kept with its dates as the record of what that
change had to carry.

**THE GO-LIVE'S ONE REAL FINDING WAS IN ANOTHER INSTANCE.** `ky/WATCH.md` carried a row saying
to re-run the cross-instance point audit on the day rather than trust its earlier result, and
the re-run found that Indiana's own negative point is Louisville — the same coordinate as this
instance's ground-truth anchor — landed there between PR 1 and go-live. Publishing Kentucky
therefore changed what Indiana's app does at that point, so three fixes went in the same
change: its two checks that put the point at the map's centre now refuse the fleet outline
file, its routing check gains Louisville as a case that must open `/ky/`, and its uncovered
case moved to Butler County, Ohio. An audit that is re-run rather than trusted is the only
reason any of that was seen before it broke.

It ships four layers, the national tier every U.S. state can serve from national publishers:
**County** (120, from Census TIGERweb, identity-only), **U.S. House** (6 districts, TIGERweb
geometry joined to the public-domain unitedstates/congress-legislators roster, refreshed
weekly), and **Kentucky Senate** / **Kentucky House** (38 and 100 districts, TIGERweb
geometry, naming nobody yet).

**THREE OF THE FOUR CARDS NAME NOBODY, AND EACH SILENCE IS RECORDED RATHER THAN IMPLIED.**
Both chamber cards enter the engine chamber factory's roster-miss path deliberately — district
identity plus the chamber's own directory, never an invented name — under gap
`ky-legislature-roster`, which says plainly that the General Assembly publishes both rosters
and this instance has not built them. The County card is identity only under
`ky-county-officers`: the state's Department for Local Government lists every county's elected
officials and pairs none of them with a district, so the card names the county and links that
directory. A reader meeting three quiet cards should be able to find out why, which is what
those records are for.

**THE COUNTY CARD NAMES NO GOVERNING BODY IN PARTICULAR, AND THAT IS DELIBERATE.** 118 of
Kentucky's 120 counties are governed by a fiscal court, but the two that are not are Jefferson
and Fayette — Louisville Metro and the Lexington-Fayette urban-county government — and the
ground-truth anchor every gate in this instance tests sits in Jefferson. A card that read
"fiscal court" would therefore be wrong at the one point the whole battery checks.

**THE FLAGSHIP LAYER THIS INSTANCE IS BUILT TOWARD IS THE FISCAL COURT**, and its FORM was
censused before any code was written (2026-09-30), from two certified elections per county:
**105 counties elect magistrates from magisterial districts, 13 elect three commissioners, and
Jefferson and Fayette have no fiscal court at all** (KRS 67.040/67.045 set the two forms; KRS
67A and 67C set the two merged governments). The commissioner form matters for the card rather
than the map: KRS 67.060(1) elects three commissioners "by the voters of the entire county, one
from each district", so a commissioner district is a RESIDENCE district and not an electorate.
Iowa already ships that shape — draw the polygon, say it is drawn for residence, name nobody on
it — and Kentucky will follow Iowa rather than inventing a second answer.

**WHAT IS MISSING IS GEOMETRY AND THE JOIN, NOT THE FORM.** 27 counties publish magisterial or
commissioner boundaries, which is a FLOOR measured county by county rather than a total, and no
source anywhere pairs a published official with the district they are elected from. Both are
recorded as gap `ky-fiscal-court` and watched in `ky/WATCH.md`, which also carries the county
whose form is genuinely unsettled (Pike, where the certified 2026 primary ran five numbered
magisterial contests and the state directory lists three commissioners) and the two whose
district compositions exist only as scans (Elliott, Leslie).

**TWO HOSTS ARE MEASURED AND BOTH ARE OPEN.** `kydlgweb.ky.gov` (the Department for Local
Government's county directory) and `legislature.ky.gov` (both chambers' member directories) each
serve this project's own token a full page, and neither publishes a robots.txt rule that binds
it. There is no captcha to obey here and nothing to work around — the obstacles on this instance
are missing datasets, not refused hosts.

**There is no build step, no framework, and no server-side code.** The app — styles, engine,
and layer modules — lives inline in `index.html`. `sw.js` is the service worker;
`data/app/*.json` are runtime-fetched data files; `data/state/` carries the bootstrap state
config (`build_congress_roster.py` reads its FIPS/USPS/seat count — it ships in the repo and
is excluded from the Pages deploy). This instance ships three sub-pages: `sources.html` (generated
from the worksheet's `layers[]`), `congress.html`, and `faq.html`. The worksheet carries
`sources_page` and NOT `history_page`, so `history.html` is generated by nobody and is still
absent — deliberately, because a history page's changelog entries are hand-written dated
snapshots and that is its own change. There is no `state-legislature.html` either, recorded in
that generator's `NO_LEGISLATURE_PAGE` with its reason: every sentence on such a page is about
the member, and this instance names none.

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: Kentucky (`kentucky`) — https://districtry.com/ky/
- Geocoders: address Photon (Kentucky-bounded type-ahead); unbounded Photon (whole-coverage, sibling-metro lookup); POI Nominatim (office-address pin lookup, Kentucky-bounded, serial >=1s queue)
- Ground truth: 38.25270,-85.75850 (downtown Louisville, Jefferson County) → county Jefferson County; us-house 3; ky-senate 33; ky-house 43. Negative point 36.40000,-86.50000 (inside Sumner County, TENNESSEE, about 15 km south of the Kentucky line and north-east of Nashville — outside Kentucky and outside every other instance in the fleet, and inside permalink_gate (minLat 36.35) so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-09-30: TIGERweb's county layer names Sumner County STATE 47 (control: the anchor returns Jefferson County STATE 21), and no outline in fleet-outlines.json contains it (control: the Louisville anchor is likewise in none of them, so the file genuinely has no Kentucky coverage rather than the test passing vacuously). TENNESSEE RATHER THAN ONE OF THE OTHER SIX NEIGHBOURS, deliberately. Illinois is live and borders Kentucky across the Ohio, so a point over there would sit inside an instance's own outline and the browser would hand the selection off to districtry.com/il/ and navigate away — which is how Minnesota's first candidate failed, silently, as a smoke-test timeout on a blank document rather than as a wrong answer. Indiana and North Carolina are in build as dark instances and will become live outlines, so they were avoided for the same reason one step ahead. Tennessee is in no instance and in no launch plan. THE POINT IS ON LAND, NOT ON WATER: Kentucky's TIGER county fabric follows the Ohio River's north bank, so the river is INSIDE Kentucky rather than outside it, and a point in open water on the northern border would be inside a Kentucky county exactly as Minnesota's Lake Superior candidate was inside Cook County.).
- Layers: 12 registered (political 7, schools 3, geography 2); `registerLayer(` floor 4. Debug namespace `window.KentuckyExplorer`.
- Scheduled workflows: `update-ky-congress-roster.yml` (Mon 13:55 UTC).
- Source registry: `ky/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ky/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ky/ node ky/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ky/scripts/validate_index.py ky/index.html

# Generated-region gate: per-instance facts live ONCE in ky/metro-worksheet.json;
# GENERATED regions are emitted from it. NEVER hand-edit a GENERATED region:
pip install -c scripts/requirements.txt jsonschema
python3 scripts/generate_metro_files.py            # regenerate in place (all instances)
python3 scripts/generate_metro_files.py --check    # the CI drift gate

# Engine parity: the ENGINE fences are composed from the repo-root engine/ —
# edit a block THERE and recompose, never inside an instance file:
python3 scripts/compose_app.py            # splice engine/ into every instance
python3 scripts/compose_app.py --check    # the CI drift gate

# The Data gaps panel's content, emitted from the fleet guidebook:
python3 scripts/build_coverage_gaps.py --check --metro kentucky --out ky/data/app/coverage-gaps.json
```

**THE NEGATIVE POINT IS IN TENNESSEE, AND THE REASON IT IS NOT IN ILLINOIS IS THE POINT.**
`ky/metro-worksheet.json`'s `negative_point.note` carries the whole measurement. Kentucky has
seven neighbours and most of them are unusable: Illinois is live, so a point over there sits
inside an instance's own outline, `placeOwner` hands the selection to `districtry.com/il/`, and
the browser LEAVES — which surfaces as a smoke-test timeout on a blank document rather than as a
wrong answer, and is exactly how Minnesota's first candidate failed. Indiana and North Carolina
are in build as dark instances and will become live outlines, so they were avoided one step
ahead. Tennessee is in no instance and in no launch plan. **AND THE POINT IS ON LAND**: Kentucky's
TIGER county fabric follows the Ohio River's north bank, so the river is INSIDE Kentucky and a
point in open water on the northern border would be inside a Kentucky county — the same trap
Minnesota hit in Lake Superior.

**THIS INSTANCE'S SMOKE TEST REFUSES `fleet-outlines.json` IN TWO CHECKS RATHER THAN MOVING ITS
POINT.** That is the fleet remedy (Iowa #1267, Illinois #1272): a check that puts a point outside
the state at the map centre depends on no sibling outline existing there, which is a race the day
a neighbour launches. Aborting the fetch makes the check test what it is for. A future Tennessee
instance therefore cannot break it.

**Sandboxed environments (Claude Code web):** the headless browser cannot reach the Leaflet
CDN. The repo root's `.claude/settings.json` SessionStart hook runs `scripts/vendor_leaflet.sh`,
which vendors Leaflet into `ky/scripts/vendor/leaflet/` (gitignored); `ky/scripts/smoke_test.mjs`
serves it same-origin. Production and GitHub Actions CI reach the CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Kentucky-specific lives in the `METRO:BEGIN config` block (worksheet-generated) and
this instance's own module code, which is the `STARTER MODULES` section.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the three district layers use the fenced factory helper `registerIlgaChamber`. **The two
chamber registrations pass `loadNoRoster`, a function returning an empty object**, because the
factory calls `opts.loadRoster()` unconditionally and an empty roster is the honest input — it
enters the factory's own roster-miss path rather than needing an engine change. When
`ky-{senate,house}-members.json` ship, those two become real file loaders and nothing else
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
`ky/scripts/build_metro_outline.py`), `state-counties.json`
(`ky/scripts/build_state_counties.py`), and `congress-districts.json`,
`ky-senate-districts.json` and `ky-house-districts.json`
(`ky/scripts/build_legislative_boundaries.py`).

**THE OUTLINE IS TWO RINGS, AND PREDICTING ONE WAS WRONG.** The first draft of this instance
asserted that Kentucky's 120 counties dissolve to a single ring because every county is
contiguous. Measured, they do not: the **Kentucky Bend** — the loop of Fulton County west of the
Mississippi, reachable by road only through Tennessee — is a separate 69.53 km² outer ring
beside the 104,529.68 km² mainland. **County contiguity is not land contiguity, and a dissolve
answers the second question.** So `build_metro_outline.py` carries a second anchor dict,
`INSIDE_DETACHED`, holding one point inside the Bend, and the registry check requires its county
to also carry an ordinary `INSIDE` anchor and the two lists to be disjoint. A simplification that
dropped the Bend would now fail rather than quietly shrink the state. The key uses the COMMA form
(`"Fulton, Kentucky Bend"`) because the existing convention reads a PARENTHETICAL as the county
name, and the first attempt sent the gate looking for a county called Kentucky Bend.

**THE CHAMBER BUILDER TAKES NO PER-CHAMBER ARGUMENT AND REFUSES ONE**, because rebuilding one
chamber alone is the defect it exists to prevent: mapshaper builds topology WITHIN one file, so
an edge two layers share only survives identically if both came off one `combine-files` run. It
refuses to write unless three gates pass — a 2,000-random-point agreement gate per layer, an
EXACT cross-layer gate at zero tolerance, and a fidelity ceiling measured against the source. Its
`--check` re-runs the cross-layer half offline in CI.

**KENTUCKY'S CHAMBERS DO NOT NEST, SO THE CROSS-LAYER GATE IS THE STATE BORDER.** 100 House
districts stand in no whole-number relation to 38 Senate districts — there is no lettering
(Minnesota), no pairing (Iowa) and no arithmetic to check — and pairing them anyway produces a
meaningless offset, the Michigan 767 km case. What all three layers DO draw identically under a
shared topology is Kentucky's own border. So `check_shared_border()` DERIVES that border rather
than assuming it: under one topology an interior edge is traced twice and a border edge once, so
the border is the set of undirected segments appearing an ODD number of times. All three sets
must then be equal exactly. **It cannot pass vacuously**: it fails on fewer than three layers, on
any empty border, and on any border vertex of odd degree (a border that does not close). Measured
2026-09-30 on the full state, the three layers share one border of **4,856 edges** exactly — and
run as three SEPARATE simplifications the same gate fails, with 696 edges only in the House layer
and 698 only in the Senate, first difference near 36.62020,-89.37192.

**`FIDELITY_MAX_M` IS 29.9 AND IS PINNED, NEVER RECOMPUTED PER RUN.** A ceiling re-derived from
the source on every run can never fail, because it rises whenever the source gets coarser. 29.9
comes from Kentucky's OWN median staircase step — how far the true line runs before it turns —
measured 2026-09-30 at 29.8 m (ky-house) and 27.2 m (ky-senate), with the instrument validated
against Illinois's published figure (19.6 m measured against 19.7 published). The ceiling is
taken from the finer chamber, and **Kentucky reverses the assumption that more districts means
finer lines**: its 100 House districts measure a COARSER step than its 38 Senate districts, so
which chamber is finer must be measured rather than inferred from the count. A redistricting
re-opens it: re-measure the step on the new lines rather than carrying the number forward. At
these settings the worst stray is 15.3 m on all three layers.

The one roster, `congress-roster.json` (`ky/scripts/build_congress_roster.py`, from
unitedstates/congress-legislators), is count-guarded and refreshed weekly by CI as a reviewed
PR.

## Four layers added 2026-10-01 for the fourth done-standard test, and two levels closed by measurement

The fleet's fourth test, **Covered** (`docs/DONE_STANDARD.md`), asks whether an app answers
every level of government it is expected to answer, or carries a measured record of why it
cannot. Kentucky scored **3 of 13** on the day that test landed. It now scores **7**, and the
four new layers are all the Census's own, so none of it needed anybody's permission.

**THE CITY LAYER CLOSES MUNICIPAL BOUNDARIES AND ITS EMPTY CARD IS A REAL ANSWER.** 415
incorporated places, live from TIGERweb `Places_CouSub_ConCity_SubMCD` layer 4, measured
2026-10-01 over 4,978.5 km2 of land — under 5% of Kentucky, at a 12.00 km2 mean — and EVERY
one carries the Census's city descriptor (LSADC 25). Kentucky incorporates no villages and no
towns, so this card needs no unit-type row where Michigan's does. The important part is the
`emptyNote`: outside a city limit the COUNTY governs, because Kentucky has no township tier, so
an empty card means "your county is the answer" rather than "a layer is missing". Minnesota's
identical empty card means "you are in a township", which is why this note is written for
Kentucky rather than carried across from a sibling.

**THE THREE SCHOOL TILINGS CLOSE SCHOOL DISTRICT BOUNDARIES, AND KENTUCKY NEEDS ALL THREE.**
Measured 2026-10-01 against TIGERweb `School/MapServer` for `STATE='21'`: layer 0 (unified) 170
districts, layer 2 (elementary) 4, layer 1 (secondary) 4. The arrangement is a ONE-FOR-ONE
PAIRING and it is measured rather than assumed. The four elementary districts are independent
districts running PK/KG-8 — Anchorage, Southgate, East Bernstadt and Science Hill — and each of
the four secondary districts is the county district running grades 9-12 over exactly one of
them: Jefferson over Anchorage, Campbell over Southgate, Laurel over East Bernstadt, Pulaski
over Science Hill. At all four elementary interior points the secondary layer returns its
partner, 4 of 4, and the reverse, 4 of 4; the unified layer returns NOTHING at any of those
eight points, and at 20 randomly sampled unified interior points neither of the other two
returns anything, 0 of 20. The probe reads INTPTLAT/INTPTLON, the interior point TIGER
guarantees is inside the polygon, never CENTLAT/CENTLON, whose centroid can fall outside a
non-convex shape.

**THE ARITHMETIC IS THE INDEPENDENT WITNESS, AND IT IS EXACT.** The Census's own AREALAND sums
to 102,228.8 km2 over the 170 unified districts and 39.0 km2 over the four elementary ones, and
the two together are 102,267.8 km2 — EXACTLY the 120-county total from the same service. So
unified plus elementary partitions Kentucky's land with nothing left over and nothing counted
twice, and the secondary tiling's own 39.0 km2 is the same ground as the elementary one. That is
also the argument for shipping all three rather than the big one: unified alone would answer
**"no school district"** to every reader inside those four areas, which is a wrong answer rather
than a missing one.

**NO RECONCILIATION WITH THE STATE'S OWN COUNT IS CLAIMED.** The Department of Education's
districts page says Kentucky has 171 school districts; the Census publishes 170 unified plus 4
elementary records. The two are counting different things, nothing measured here resolves them,
and neither figure is presented as the other. This is the same question left open below about
the county/independent split, and it is still open.

**ALL FOUR ARE POINT-FIRST, WHICH MOVED THIS INSTANCE'S PUBLISHED PRIVACY ROW.** They go
through a new `tigerStatewideLoader` carrying the `.atPoint` hook, because the two large ones
need it: measured at `geometryPrecision=5`, unified school districts are 6.53 MB raw / 1.72 MB
gzipped and the places layer 4.72 MB / 1.18 MB, so a first click would otherwise wait on a
multi-MB statewide download. The two four-feature tilings are 0.04 MB each and inherit the hook
for free. `scripts/probe_point_transmission.mjs` re-run on 2026-10-01 measures all four
FIRING — which is also the proof that all four layers genuinely answer, since the smoke test
only exercises the four anchor layers — so `privacy.html`'s Kentucky row moves from "None." to
"4 layers". **In that run every other instance's figures came back byte-identical to the
committed artifact**, which is what makes the Kentucky change trustworthy rather than a sandbox
reading: this probe's answer is known to depend on what the network can reach.

**NEITHER LAYER NAMES ANYBODY, AND BOTH ABSENCES ARE RECORDED** as the coverage gaps
`ky-school-board-members` and `ky-municipal-officeholders`. The school cards link the
Department of Education's district directory and the city card links the Department for Local
Government's municipal directory; both hosts were read with this project's own client on
2026-10-01 and both permit the path. The city directory is a per-city SEARCH rather than a
downloadable list, which is why a roster there is 415 reads rather than one fetch, and that is
in the record rather than in a plan.

**TWO LEVELS ARE CLOSED BY MEASUREMENT RATHER THAN BY WORK**, which is the standard's own
second branch for a level a state does not have.

**Kentucky has no sub-county general-purpose government.** The only sub-county units the Census
publishes for the state are 493 Census County Divisions — statistical areas drawn for
tabulation, which govern nobody — so there is no elected sub-county body to draw. That layer is
deliberately NOT shipped: at 19.91 MB raw / 5.03 MB gzipped it is the heaviest fabric the state
has, and it would put a card on the map for something that is not a government.

**Kentucky has no tribal land.** Measured 2026-10-01 against the Census AIANNHA service over an
envelope covering the whole state: zero features in federal reservations, off-reservation trust
lands, state reservations, tribal subdivisions, and both the state-designated and
tribal-designated statistical areas — six layers, all empty. **RUN WITH CONTROLS**, because a
zero from a query is also what an error looks like: the same two layers return the Qualla
Boundary over western North Carolina and eleven reservations over northern Wisconsin. The
fleet-wide tribal layer and the 2026-09-29 mandate behind it remain the tribal thread's; this
records Kentucky's own measurement and nothing else.

**WHAT WAS STILL OPEN AT THAT POINT, AND WHICH WAS CHEAPEST.** Six levels: the county
governing body, the 17 cities above 25,000 people, courts by district, school boards by
division, election precincts and special districts. **The court districts were the one that
needed no publisher at all** — every judicial district in Kentucky is a list of whole counties
written into statute and this instance already ships a 120-feature county fabric, so all four
tiers dissolve offline from text. `ky/data/source/statutes/` holds the sections, with the one
limitation that the exact PDF route they were fetched from was not recorded and was not
recovered afterwards. **That level is closed** — the four court layers shipped the same day, in
the section below — so five remain: the county governing body, the 17 cities, school boards by
division, election precincts and special districts.

## Two concepts measured 2026-10-01 from primary law — the courts were then built, the school divisions were not

Asked for by the fleet's fourth done-standard test. Each was read out of the statute or the
constitution itself, through `scraper_common.require_robots_once` with the client that fetched
— `apps.legislature.ky.gov` publishes no robots.txt (HTTP 404, allow), `www.kycourts.gov`
serves one with no matching rule, `education.ky.gov`'s is empty.

**KENTUCKY ELECTS EVERY JUDGE FROM A DISTRICT, AND EVERY ONE OF THOSE DISTRICTS IS A GROUP OF
WHOLE COUNTIES ENUMERATED IN STATUTE.** Constitution §117: "Justices of the Supreme Court and
judges of the Court of Appeals, Circuit and District Court shall be elected from their
respective districts or circuits on a nonpartisan basis as provided by law." The four tiers:
**7 Supreme Court districts**, county by county in KRS 21A.010 (redrawn by 2022 Ky. Acts ch. 5,
effective 2022-01-18; District 4 is Jefferson County alone); **7 Court of Appeals districts**,
14 judges two per district, and KRS 22A.010(2) says outright they "correspond in geographical
dimensions to the districts of the Supreme Court" — so the two tiers are ONE geometry drawn
twice, which is the thing to check before building the second; **57 judicial circuits** in KRS
23A.020 (effective 2023-01-02); and **59 judicial districts** in KRS 24A.030.

So unlike the fiscal court, **neither geometry needs a publisher**: both are unions of whole
counties and this instance already ships a 120-feature county fabric, so all four layers
dissolve offline from text plus `state-counties.json`. The Court of Justice also publishes its
own district and circuit maps (`SC_COA_districtsmap.pdf`, `P-107 KY Judicial Circuits Map`,
`circuitfacemap.pdf`), which are a WITNESS to check a dissolve against and never the source.
And unlike Illinois, where a judge is elected from a subcircuit and then sits circuit-wide so
no judge belongs to the subcircuit, a Kentucky judge is elected from the circuit they sit in —
the roster join is the district itself.

**THE TRAP IS THE WORD DIVISION, WHICH MEANS TWO DIFFERENT THINGS IN KENTUCKY LAW.** A circuit
with more than one judge has "numbered divisions" (KRS 23A.040 and the sections after it) and
those are SEATS, elected by the whole circuit, carrying no geometry of their own — the circuit
is the ground. A school board's division is the opposite and is real geography. Reading the
first as the second would invent sub-circuit boundaries that do not exist.

**KRS 24A.030 HAS A SECOND VERSION ALREADY ENACTED, EFFECTIVE 2031-01-01**, which is a dated
redistricting with a known trigger rather than a cycle to watch: 2022 Ky. Acts ch. 129 sec. 7
takes the district courts from 59 to 58 — Edmonson moves from the 38th to the 8th, Marshall
from the 58th to the 42nd, and Cumberland and Monroe become the 58th. Recorded in `WATCH.md`.

**COUNTY SCHOOL BOARDS ARE ELECTED BY DIVISION AND INDEPENDENT ONES AT LARGE** (KRS 160.210,
effective 2026-04-14). Subsection (1) is the whole answer: "In independent school districts,
the members of the school board shall be elected from the district at large. In county school
districts, members shall be elected from divisions." Each county district has **five**
divisions, and subsection (2) requires them to contain "integral voting precincts" — §(6) says
flatly that no precinct may be redrawn or divided to accommodate a division line. **So every
division is a union of whole precincts**, which is the composition route this project has used
in Clark, Hancock and Gallatin, and Kentucky's precinct fabric is published and current (3,193
precincts). Division lines are frozen for five years after any change, and §(4) lets 100
residents petition the state board to force a redraw.

**JEFFERSON COUNTY'S FIVE DIVISIONS ARE WRITTEN OUT IN STATUTE AS PRECINCT LISTS.** KRS 160.211
— created 2026 Ky. Acts ch. 154 sec. 9, effective 2026-04-14 — names 643 distinct precinct
codes across the five divisions, keyed to "the precinct identification codes and precinct
boundaries maintained by the Jefferson County Clerk's Office as of March 19, 2026". That is a
complete description of the largest school board in the state with no map to read. **Its one
measured limit is in §(2)**: a precinct of the district that the list omits is added by the
county board of elections to a contiguous division, so the list is not guaranteed exhaustive
and the residual assignment is made by a body that may not publish it. Measured, not assumed.

**WHAT IS NOT ESTABLISHED, and both are stated rather than inferred.** KDE's own districts page
says Kentucky has **171 school districts**; how many are county and how many independent was
NOT measured, and is deliberately not derived by subtracting 120, because this project's record
is full of figures that were arithmetic rather than measurement. The directory that would
settle it, `openhouse.education.ky.gov`, could not be read from this sandbox at all: its
robots.txt fails certificate verification in this client, the gate therefore refuses the host,
and nothing was fetched from it. That is this vantage's route rather than the publisher's
answer — the `web.archive.org` pattern — and it wants a runner measurement. **No publisher of
division GEOMETRY has been found for any county**, which is an open question and not a measured
refusal: KRS 160.210(6) requires changes to be filed with the county board of education and the
county board of elections and published under KRS Chapter 424, and names no central publisher.

## The four court layers, dissolved from statute 2026-10-01

Kentucky's eighth Covered level closed with no publisher asked and no map traced.
`ky/scripts/build_ky_court_districts.py` reads the three statutory county lists out of
`ky/data/source/statutes/` and dissolves this instance's own shipped 120-county fabric into
**7 Supreme Court districts** (KRS 21A.010), **57 judicial circuits** (KRS 23A.020) and **59
judicial districts** (KRS 24A.030). The **Court of Appeals** layer is the fourth registration
and ships no file of its own, because KRS 22A.010(2) says its districts "correspond in
geographical dimensions to the districts of the Supreme Court" — so it reads the Supreme Court
loader rather than carrying a second copy of one geometry.

**EACH TILING PARTITIONS THE 120 COUNTIES EXACTLY ONCE, AND THAT IS THE GATE RATHER THAN A
NOTE.** `check_partition()` fails on a county name the fabric does not carry, a county claimed
by two units, or a county claimed by none; the dissolve then gates its own arithmetic, the
merged area against the sum of its parts, at 1e-9 relative. Measured on the full state the
drift is at most 2.23e-15, each tiling reproduces the whole-state county footprint, and each
comes out in **2 parts** — which is the Kentucky Bend arriving independently for a third time,
after `build_metro_outline.py` and the outline itself. Nothing was simplified after dissolving:
`state-counties.json` is already simplified, so cancelling interior borders adds no vertex and
re-simplifying would have moved lines the statute does not move.

**`--check` IS STDLIB-ONLY SO IT CAN RUN IN AN ORDINARY CI STEP**, where the build path needs
shapely. It re-derives each unit's area spherically from the shipped rings and fails above 1e-6
against the counties it names, then asserts the already-enacted 2031 text separately:
`check_2031()` requires 58 units and exactly the four county moves the statute makes — Edmonson
38 → 8, Marshall 58 → 42, Cumberland and Monroe into the 58th. **It was negative-tested two
ways** (a county moved in a shipped file, and two units' geometries swapped) and caught both,
so the gate is not vacuous. What it CANNOT see is an amendment: it reads snapshotted statute
text, so a regular session that redraws a circuit leaves every gate green. That is why
`ky/WATCH.md` carries a session-cadence row for these three files rather than relying on the
gate.

**TWO SILENT PARSING TRAPS ARE RECORDED IN THE BUILDER BECAUSE BOTH REPORTED A PLAUSIBLE
ANSWER.** The district-court statute's own TITLE line reads "(Effective until January 1,
2031)", so cutting the history block at the first occurrence of the word "Effective" threw the
entire body away and returned ZERO units without raising — the cut is by LINE now, and the
builder fails loudly on zero paragraphs. And a round ten is spelled one word by two different
rules, Twentieth and Thirtieth keeping the tens stem where Fortieth and Fiftieth drop a letter,
so the ordinals are a table rather than a derivation; every paragraph's ordinal WORD is checked
against its own number.

**NO JUDGE IS NAMED, AND THAT SILENCE IS ITS OWN RECORD** (gap `ky-judges`). The geometry is
settled and the JOIN is missing: nothing published pairs a sitting judge with the district they
were elected from. Unlike Illinois, where a judge is elected from a subcircuit and then sits
circuit-wide so no judge belongs to the subcircuit, a Kentucky judge is elected from the
circuit they sit in — so Kentucky CAN name judges once that join exists. The record names the
Administrative Office of the Courts as the body to ask and says plainly that it has NOT YET
been asked.

**SEAT COUNTS ARE STATED ONLY WHERE THEY WERE MEASURED.** The Supreme Court card says one
justice per district (KRS 21A.020 elects per district) and the Court of Appeals card says two
judges per district (KRS 22A.010(1), verbatim). The circuit and district cards state NO number,
because judges-per-circuit was not extracted — an absent number is honest where a guessed one
is not.

**THE COURT LAYERS SEND NOTHING ABOUT A READER'S POINT.** They are same-origin files answered
in the browser, so `point-transmission.json` re-run on 2026-10-01 still measures Kentucky at
four point-first layers — the city and the three school tilings — with the four court layers
holding no hook and every other instance's figures byte-identical to the committed artifact.
Adding them still forced the probe to re-run, because the privacy page refuses to publish once
an app's layer id list has moved.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and
its officeholder sourcing in the same change, floor every scraped count, and record what a
publisher does NOT publish rather than guessing. When a layer ships, its row in
`ky/metro-worksheet.json` (`layers[]`, with a `source` block) is what puts it in every gate.
Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the same change.
