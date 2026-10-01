# WATCH.md — redistricting watch calendar

The one place the dates live: *when to look* for boundary and roster changes in this
instance's sources. The repo's `docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a
boundary changes. Update the "Last done" column each time you complete a row — a
checkpoint with a stale date is a checkpoint that didn't happen.

This instance arrived DARK (PR 1, 2026-09-30) and WENT LIVE the same day: the deploy
exclude is narrowed to the granular set the siblings use, `metros.json` carries a `ky`
entry, and `districtry.com/ky/` serves. The **GO-LIVE** rows below are kept with their
dates rather than deleted, because each records what the publishing change had to carry
and the next state's go-live reads them.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| Weekly (Mon 13:55 UTC) | U.S. House (KY) roster refresh | `.github/workflows/update-ky-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Monthly (1st, 17:00 UTC) | Source freshness — the four TIGERweb layers and the congress-legislators feed | `.github/workflows/ky-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose, the issue is the signal |

Only one roster refreshes here, because only one roster ships. The two chamber cards and
the county card name nobody — gaps `ky-legislature-roster`, `ky-fiscal-court` and
`ky-county-officers` in `docs/DATA_LAYER_GUIDEBOOK.md`.

**Minnesota, the instance this one was ported from, has no monthly source workflow at
all.** That is a gap on that instance rather than a precedent for this one: an instance
that declares a source registry and never runs it has filed a measurement nowhere.

---

## GO-LIVE — what the publishing change had to carry (done 2026-09-30)

| What | Why it cannot wait | Last done |
|---|---|---|
| **MINNESOTA'S GO-LIVE HAD TO LAND FIRST AND IT HAS** (#1281, on `main` 2026-09-30). It carries a fix for a defect that breaks the instances still dark when one state goes live, and Kentucky is one of them, so a Kentucky go-live merged ahead of it would have broken the other dark instances — which nothing in this instance's own battery tests. Relayed from Adam through the coordinator session and recorded here rather than only in a thread, because the ordering is invisible in this tree: nothing in `ky/` references Minnesota and no gate can see the dependency. **WHAT STILL BLOCKS IS ADAM'S WORD.** The same day he let threads merge their own low-risk work he kept publishing out of it, and a go-live is reader-visible by definition | An ordering constraint no gate enforces is one the next pass repeats | Order satisfied 2026-09-30; Adam said proceed the same day |
| **NO LIVE INSTANCE HAS A FIXED POINT INSIDE KENTUCKY, and that is measured rather than assumed.** Every instance's `anchor_point`, `negative_point` and `metro_center` was tested against this instance's own shipped outline, and every coordinate literal in the 36–39 N by 82–90 W box in all eight smoke tests plus the two fleet probes was tested the same way. Nothing outside Kentucky's own files lands inside Kentucky. So publishing this instance does not start any sibling handing a selection to `/ky/` — which is what happened to Iowa when Minnesota was planned (#1267) and to Wisconsin (#1268). **RE-RUN THAT AUDIT AT GO-LIVE RATHER THAN TRUSTING THIS ROW**: Indiana, North Carolina and Minnesota are all in build, and any of them could add a point in Kentucky between now and then. The measurement is cheap — point-in-polygon against `ky/data/app/metro-outline.json` | It is the one thing that fails as a TIMEOUT WAITING FOR A BUTTON on a page that has navigated away, a symptom that names nothing about its cause | **2026-09-30 AT GO-LIVE — AND THE RE-RUN FOUND ONE, which is exactly why the row says re-run rather than trust.** Indiana's own negative point IS Louisville (38.2527, -85.7585), the same coordinate as this instance's anchor, and it landed in the tree between PR 1 and this change. Three fixes, all in the go-live PR: its two checks that put that point at the map's CENTRE now refuse `../fleet-outlines.json` (the Iowa/Illinois/Wisconsin fix, never moving the point), its routing check gains Louisville as a fourth case that must open `/ky/`, and its uncovered case moves to Butler County, Ohio (39.4, -84.65), measured against TIGERweb with Louisville and Indianapolis as controls |
| **This instance's OWN checks already refuse `fleet-outlines.json`, so it needs no fix of its own.** Its negative point is in Sumner County, Tennessee, which no instance and no launch plan covers today — so nothing is broken now — and the two checks that select that point abort the fleet file anyway, following what Iowa and Wisconsin both settled on. A future Tennessee instance therefore cannot break this instance's tests | Recorded so a later pass does not "fix" a problem that was closed by construction | 2026-09-30 |
| Rebuild `fleet-outlines.json` (`scripts/build_fleet_outlines.py`) with Kentucky's outline as a `SOURCES` entry, and add a `ky` row to `metros.json` | The front door and every sibling app route by that file; without it no address in Kentucky reaches this app, and the landing page does not list it | 2026-09-30 (8 instances in the file; the outline is a MultiPolygon, so the Kentucky Bend routes too) |
| **Check whether the fleet hand-off bbox needs CLIPPING.** Kentucky's own extent is -89.57 to -81.96 by 36.50 to 39.15. No sibling's centre falls in it today — measured above — but `validate_index.py` enforces "a bbox must not contain a sibling metro's centre" against the FLEET box in `metros.json`, and that has to be re-checked against whatever instances exist on the day, not against today's six. Michigan and Minnesota both needed a clip | The rule is enforced on every instance at once, so an unclipped box fails a sibling's gate rather than this one's | 2026-09-30 (no clip needed against the six live instances) |
| Add a `ky` entry to the other instances' `metro_explorers`, and check each new entry does not contain that instance's own centre | A sibling that does not list Kentucky sends a Kentucky address nowhere; one that lists it before the deploy publishes `/ky/` sends a reader to a 404 | 2026-09-30 (`--sync-fleet`; no sibling's own centre falls in Kentucky's box and Kentucky's falls in no sibling's) |
| Narrow the `'ky/**'` line in `deploy-pages.yml` to `ky/data/state ky/data/source ky/scripts`, matching `ia` and `mi`, and add `ky` to its presence loop | `validate_instance_registration.py` holds the deploy exclude and `metros.json` together in both directions, so this and the `metros.json` row are one change | 2026-09-30 |
| Add `ky` to `AREAS` in `scripts/build_coverage_map.py` (an outline pair; a state is never a marker), add every page it serves to `sitemap.xml`, and update the README fleet table and its instance count | A `metros.json` tag in neither `AREAS` nor `CITY_TAGS` fails that script's `--check`; Iowa shipped while the README still said "four instances" with every gate green | 2026-09-30 (README now says eight instances in all four places it states a count) |
| **`ky/sources.html` SHIPPED WITH THE GO-LIVE CHANGE and the masthead links it.** It was absent through PR 1 for a reason that was correct then — a link to a file the tree does not contain is a 404 the moment the page is published — and stopped being correct the moment this instance went live, because every sibling ships one and a reader here would otherwise have no way to ask where a boundary came from. It needed no research: every `layers[]` entry already carried a `source` block, so the matrix and credit rows generate | A CORRECT REASON FOR AN OMISSION WHILE DARK IS NOT A REASON FOR IT ONCE LIVE, and no gate asks the question — the asset gate proves every link resolves, and a page nobody links resolves trivially | 2026-09-30 |
| **`ky/congress.html` SHIPPED TOO, and `state-legislature.html` is RECORDED ABSENT rather than written.** The U.S. House page names all six members. The state-legislature page is not generated because this instance names nobody in either chamber and every sentence that page writes is about the member, so it would be a page of false claims about people; `NO_LEGISLATURE_PAGE` in `scripts/build_legislator_pages.py` carries the entry, its reason and its date, re-audited every run and failing the day either roster arrives | Kentucky is the SECOND instance of that case after Minnesota, which is what makes it a rule rather than one state's exception | 2026-09-30 (gap `ky-legislature-roster`) |
| **The weekly U.S. House refresh now regenerates the pages that count its roster** and stages them in the same commit. Until this change it correctly had no such step, because no page read the file | Otherwise the bot's own PR fails those pages' `--check` on a number the PR is not about, which lands the failure on the bot rather than on whoever caused it | 2026-09-30 |
| Regenerate `build_landing_page.py`, `build_privacy_page.py` and `build_coverage_map.py` | The privacy page is MEASURED from the shipped `index.html`, so it describes this instance only once its analytics and geocoder posture are real | 2026-09-30 (plus `llms.txt`, `about.html`, `sitemap.xml`, `404.html`, `feedback.html`, `stats.json`, `docs/COUNTY_STATUS.md`, `docs/ENDPOINT_INVENTORY.md` and `docs/WIKIDATA.md`, whose Kentucky item Q1603 was DERIVED from Illinois's own shares-border list and verified rather than recalled) |

---

## Per-election — the seats above the boundaries

| When | What | Last done |
|---|---|---|
| After each U.S. general (November, even years) | The delegation turns over; the weekly congress-legislators refresh picks it up | 2026-09-30 (initial build: 6/6, each with a district office) |
| After each Kentucky general (November, even years) and each January seating | The two chamber rosters turn over — and this instance names nobody in either, so there is nothing to refresh until `ky-legislature-roster` is built. Until then the cards enter the engine chamber factory's roster-miss path and link each chamber's own directory | — (gap `ky-legislature-roster`) |
| After each Kentucky general | County judge-executives, magistrates and commissioners turn over. The Department for Local Government's directory is the roster source and it carries no district number, so there is nothing here to refresh yet either (gap `ky-fiscal-court`) | — |

---

## Per-decade — the census redistricting cycle

| When | What | Last done |
|---|---|---|
| After each decennial census (next: 2031–2032) | Congressional + legislative districts redraw: re-run `ky/scripts/build_legislative_boundaries.py` (**NO arguments** — it rebuilds all three chambers in one mapshaper run and rejects a per-chamber argument, because rebuilding one alone is what makes the three layers draw the state border differently), confirm the counts against the apportioned delegation and the 38/100 chambers, re-verify the smoke anchors, and bump `sw.cache_name` — this geometry is cache-first. A redistricting also re-opens `FIDELITY_MAX_M`: it is 29.9 m because Kentucky's own median staircase step measures 29.8 m (ky-house) and 27.2 m (ky-senate), so **re-measure that step on the new lines rather than carrying the number forward** | 2026-09-30 (initial build as one topology: 100.00% agreement on us-house and ky-house, 99.95% on ky-senate, 4,856 border edges shared exactly across all three, worst stray 15.3 m against the 29.9 m ceiling) |
| After each decennial census | `ky/scripts/build_state_counties.py` and `ky/scripts/build_metro_outline.py` — county boundaries move rarely, but the outline's 120 INSIDE anchors are interior points and a boundary change can put one outside its own county. `build_metro_outline.py --check` is what says so | 2026-09-30 (initial build: 120 counties, 2 rings, 3,383 vertices, all 120 anchors plus the Kentucky Bend correct) |

---

## Per-class re-checks — the files no job rewrites

`docs/EAM_STATUS.md` measures whether every data file the app reads is under a
stated plan. Measured 2026-10-01 through that module's own readers, **six of
this instance's seven were under none** — the one exception being
`congress-roster.json`, which the weekly workflow rewrites. All six are
boundary geometry or a record, which is exactly the case a weekly job cannot
serve: a scraper run every Tuesday against a county outline that moves once a
decade is a guaranteed no-op, and the honest alternative is a stated cadence
here. The sections above already carried the right clocks in prose and named
the BUILDERS rather than the files, which is a mention and not a plan.

**TWO THINGS WERE MEASURED WHILE WRITING THIS AND BOTH BOUND WHAT THESE ROWS
CLAIM.**

First, **five of the six are already watched in substance, and the instrument
cannot see it.** `ky-validate-sources.yml` is scheduled monthly, carries
`issues: write`, commits nothing and opens a tracking issue — the watcher shape
exactly — and `ky/scripts/validate_sources.py` names every one of those five in
`PROVENANCE`, fails when the built file is missing, and queries the four
TIGERweb layers for a feature COUNT against a floor of 120, 6, 38 and 100. But
`watcher_texts()` reads the workflow's own text, and the workflow names those
files only in the script it runs, so none of it registers. That is a blind spot
in the measure rather than a gap in this instance, and it is reported to
whoever owns that module rather than closed by writing paths into a `.yml` to
satisfy a regex.

Second, **what that monthly check cannot see is the thing these rows are for.**
A count floor fires when a count DROPS. It is silent when a count RISES — a
seventh Kentucky congressional seat after the 2030 apportionment would pass a
floor of 6 — and it is silent when a boundary is redrawn with the same number
of districts, which is what a redistricting mostly looks like. Reachability and
a floor are not a boundary-change check, so the clock below is the only guard
against a line moving.

**These exposure classes are KENTUCKY'S OWN.** `docs/REDISTRICTING_RUNBOOK.md`
carries per-layer tables for Illinois, New York City, San Francisco, Wisconsin
and Michigan and **has no Kentucky section at all** — zero occurrences of the
state's name — so unlike Illinois's equivalent table these rows cannot quote it
and do not pretend to. Writing that section is a repo-level change and is named
here as owed rather than done.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **Annually**, when TIGERweb rolls its congressional vintage — and again on each decennial redraw (next: 2031–2032) or any court-ordered mid-decade one | `congress-districts.json` | TIGERweb rolled CD119 → CD120 on 2026-09-03, observed rather than predicted, and the retired field was REMOVED rather than deprecated — the old query then answers HTTP 200 with an Esri error envelope and no features, which the monthly check does catch. The vintage roll is the annual clock; the redraw is the decennial one, and the procedure for it is the per-decade checkpoint above, which this row names rather than restates | **_(never)_** — built 2026-09-30 |
| **After each decennial census** (next: 2031–2032), and on any mid-decade or court-ordered redraw | `ky-senate-districts.json`, `ky-house-districts.json` | The General Assembly draws both chambers, and Kentucky Constitution §33 constrains each to county lines where population permits without relating one chamber to the other — which is why they do not nest and why the shared-border gate rather than a nesting gate is what holds them together. Both ship from one mapshaper run; the procedure is the per-decade checkpoint above | **_(never)_** — built 2026-09-30 |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both are the same 120-county fabric — the outline is its dissolve — so they have one clock and it is not a redistricting: county lines move essentially never, and what does move is TIGER's digitisation of them. `build_metro_outline.py --check` does NOT re-fetch: it tests the shipped ring against the 120 INSIDE anchors plus the Kentucky Bend, so it catches a county added without an anchor and would not notice TIGER redrawing a county line | **_(never)_** — built 2026-09-30 |
| **Annually** | `coverage-gaps.json` | The one file here with no upstream: its source is the guidebook's own gaps block, and `build_coverage_gaps.py --check` re-emits and compares on every pull request, so file-versus-record drift is already impossible. The cadence is for the RECORD, and this instance has a named reason — `ky-fiscal-court` states that 27 counties publish magisterial district geometry and says outright that the number is a FLOOR. A county that starts publishing moves that floor and nothing detects it, which is the direction a gap record rots in. The other two records are ours to build and turn over with each Kentucky general, which the per-election table above covers | **_(never)_** — written 2026-09-30 |

**A `--check` PROVES A FILE MATCHES ITS INPUTS AND NEVER THAT THE INPUTS ARE
CURRENT**, which is why `coverage-gaps.json` and `metro-outline.json` are in the
table rather than excused by their own gates. Measured rather than assumed, and
the two gates differ: `build_coverage_gaps.py --check` re-emits from the
guidebook and compares, while `build_metro_outline.py --check` reads the anchor
registry and never fetches. Two different guarantees, neither of them upstream.

---

## Kentucky specifically — no fixed cadence

| What | Why it is here | Last done |
|---|---|---|
| **The fiscal court's FORM is settled and its GEOMETRY is not, and those are separate pieces of work.** Every county's governing body was censused from two certified elections apiece off the Secretary of State's own recap canvasses: 105 magisterial counties, 13 commissioner counties, and Jefferson and Fayette, which are merged city-county governments under KRS 67C and 67A and have no fiscal court at all. The two elections agreed in every county with no conflicts. What is missing is boundaries: **27 counties publish magisterial district geometry**, each confirmed geometrically against TIGERweb, and that is a FLOOR — no census of the remaining counties' GIS has been completed | This is the flagship layer. The next research question is how many of the roughly ninety unpublished counties compose cleanly from whole precincts, which is a per-county answer and was deliberately not estimated | 2026-09-30 |
| **PIKE COUNTY IS THE ONE COUNTY WHOSE FORM IS IN QUESTION, and it needs its own clerk asked.** Its certified 2026 primary runs five numbered magisterial contests while the Department for Local Government lists three commissioners. Those are different bodies under different statutes, and no published source this project has read settles which is current | It is the only blocking question in the whole census, and it is one e-mail. Nothing has been sent — an outbound ask is the operator's to send | 2026-09-30 (question drafted, not sent) |
| **Elliott and Leslie counties' district descriptions are scans**, so their form was settled from the contest names in their returns and their district composition was not read | Both counted as magisterial in the census on the contest names alone, which is enough for the form and not enough for geometry | 2026-09-30 |
| **The roster source is the Department for Local Government and it carries NO DISTRICT NUMBER.** `kydlgweb.ky.gov` publishes a page per county naming the judge-executive, county attorney, clerk, sheriff, jailer, coroner, surveyor and board members — 120 of 120 counties, 1,526 officials, 563 of them board members, 98% with a telephone number and 90% with an e-mail address. robots.txt allows the pages this project would read. It agrees with the election census on the county's governing-body form in 115 of the 116 counties where both can be compared | So the people are published and the join between a person and a district is not. That join has to come from certified returns or from a county layer carrying its own roster, which is the shape Illinois's frontier work takes | 2026-09-30 |
| **Kentucky has NO federally recognised tribal land, and that is a measurement with controls.** All six of the Census AIANNH layers return zero features for Kentucky, with Oklahoma (26 areas) and North Carolina (13) run as controls on the same queries to prove the queries work | The fleet mandate puts tribal governments in scope in every state. In Kentucky the honest answer is that there is nothing to draw, which is different from not having looked | 2026-09-30 |
| **Special-purpose districts are a boundary question here, not a roster one.** The state's SPGE registry (`spge.dlg.ky.gov`) is public and queryable and names ONE contact per district with no board, so fire, library and park districts would ship with a contact and no members. No boundaries are published there at all | Recorded so a later pass does not read "the registry exists" as "the layer is cheap" | 2026-09-30 |
| **The precinct fabric is published and current**: 3,193 precincts, updated 19 September 2026. It is what a whole-precinct composition of the unpublished counties' magisterial districts would be built from | Every source in this instance's plan is a government publisher; no university or research source is used as a primary | 2026-09-30 |
| **`history.html` is still absent, deliberately.** Its changelog entries are hand-written dated snapshots rather than generated, so it is its own change, and the worksheet carries no `history_page` key to generate it from. `faq.html` SHIPPED on 2026-10-01 — written against this instance's own measurements rather than cloned, because prose cloned from a sibling is how one go-live shipped another state's whole identity block, and how `nc/faq.html` carries Michigan's canonical, `og:url` and JSON-LD identity today | Named so the absence reads as owed rather than overlooked | 2026-10-01 (faq.html shipped; history.html still owed) |
| **The school-board publisher is unknown and the district map's licence text is unread.** Both are open questions rather than measured refusals | Named so the absence reads as unexamined rather than as closed | — |
