# WATCH.md — redistricting watch calendar

The one place the dates live: *when to look* for boundary and roster changes in this
instance's sources. The repo's `docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a
boundary changes. Update the "Last done" column each time you complete a row — a
checkpoint with a stale date is a checkpoint that didn't happen.

This instance arrived DARK (PR 1, 2026-09-30): `ky/**` is blanket-excluded from the
Pages deploy and `metros.json` carries no `ky` entry, so nothing here is reachable by a
reader yet. Rows marked **GO-LIVE** are what has to happen in the change that publishes it.

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

## GO-LIVE — what the publishing change has to carry

| What | Why it cannot wait | Last done |
|---|---|---|
| **NO LIVE INSTANCE HAS A FIXED POINT INSIDE KENTUCKY, and that is measured rather than assumed.** Every instance's `anchor_point`, `negative_point` and `metro_center` was tested against this instance's own shipped outline, and every coordinate literal in the 36–39 N by 82–90 W box in all eight smoke tests plus the two fleet probes was tested the same way. Nothing outside Kentucky's own files lands inside Kentucky. So publishing this instance does not start any sibling handing a selection to `/ky/` — which is what happened to Iowa when Minnesota was planned (#1267) and to Wisconsin (#1268). **RE-RUN THAT AUDIT AT GO-LIVE RATHER THAN TRUSTING THIS ROW**: Indiana, North Carolina and Minnesota are all in build, and any of them could add a point in Kentucky between now and then. The measurement is cheap — point-in-polygon against `ky/data/app/metro-outline.json` | It is the one thing that fails as a TIMEOUT WAITING FOR A BUTTON on a page that has navigated away, a symptom that names nothing about its cause | 2026-09-30 (0 of 9 instances, 0 of 10 test files) |
| **This instance's OWN checks already refuse `fleet-outlines.json`, so it needs no fix of its own.** Its negative point is in Sumner County, Tennessee, which no instance and no launch plan covers today — so nothing is broken now — and the two checks that select that point abort the fleet file anyway, following what Iowa and Wisconsin both settled on. A future Tennessee instance therefore cannot break this instance's tests | Recorded so a later pass does not "fix" a problem that was closed by construction | 2026-09-30 |
| Rebuild `fleet-outlines.json` (`scripts/build_fleet_outlines.py`) with Kentucky's outline as a `SOURCES` entry, and add a `ky` row to `metros.json` | The front door and every sibling app route by that file; without it no address in Kentucky reaches this app, and the landing page does not list it | — |
| **Check whether the fleet hand-off bbox needs CLIPPING.** Kentucky's own extent is -89.57 to -81.96 by 36.50 to 39.15. No sibling's centre falls in it today — measured above — but `validate_index.py` enforces "a bbox must not contain a sibling metro's centre" against the FLEET box in `metros.json`, and that has to be re-checked against whatever instances exist on the day, not against today's six. Michigan and Minnesota both needed a clip | The rule is enforced on every instance at once, so an unclipped box fails a sibling's gate rather than this one's | 2026-09-30 (no clip needed against the six live instances) |
| Add a `ky` entry to the other instances' `metro_explorers`, and check each new entry does not contain that instance's own centre | A sibling that does not list Kentucky sends a Kentucky address nowhere; one that lists it before the deploy publishes `/ky/` sends a reader to a 404 | — |
| Narrow the `'ky/**'` line in `deploy-pages.yml` to `ky/data/state ky/data/source ky/scripts`, matching `ia` and `mi`, and add `ky` to its presence loop | `validate_instance_registration.py` holds the deploy exclude and `metros.json` together in both directions, so this and the `metros.json` row are one change | — |
| Add `ky` to `AREAS` in `scripts/build_coverage_map.py` (an outline pair; a state is never a marker), add every page it serves to `sitemap.xml`, and update the README fleet table and its instance count | A `metros.json` tag in neither `AREAS` nor `CITY_TAGS` fails that script's `--check`; Iowa shipped while the README still said "four instances" with every gate green | — |
| Regenerate `build_landing_page.py`, `build_privacy_page.py` and `build_coverage_map.py` | The privacy page is MEASURED from the shipped `index.html`, so it describes this instance only once its analytics and geocoder posture are real | — |

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
| **The school-board publisher is unknown and the district map's licence text is unread.** Both are open questions rather than measured refusals | Named so the absence reads as unexamined rather than as closed | — |
