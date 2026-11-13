# WATCH.md — Massachusetts's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| **2031**, when TIGERweb publishes 2030 census blocks | The Census 2020 block populations the compare screen counts people with, the one dataset here that cannot change until then | `ma/data/app/population/` | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set this app's `INSTANCES` row's `total` to its 2030 count and rebuild with `--instance ma`. `--check` forces it: the first legislative map drawn on 2030 blocks fails against 2020 people until this row is done. |
| Weekly (Mon 22:07 UTC) | U.S. House (Massachusetts) roster refresh | `.github/workflows/update-ma-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Tue 22:07 UTC) | Massachusetts Senate + Massachusetts House roster refresh, from the General Court's own member data | `.github/workflows/update-ma-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a seat listed twice, a district the map does not draw, fewer named members than the builder's floor, or too few members carrying their Capitol office, e-mail address or party |
| Weekly (`update-statewide-officials.yml`) | The statewide officials line | `scripts/build_statewide_officials.py` → PR on change | Review + merge the PR; a red run is a handover to read |
| Weekly (Sun, `update-tiger-tiles.yml`) | The five TIGERweb fabric archives (city or town, three school district layers and ZIP) | `scripts/mirror_tiger_tiles.py` → PR on change | Review + merge the PR; it moves this app's cache name itself |
| Monthly (1st of month 23:13 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/ma-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **The batch 3 go-live** | **Massachusetts opens with the rest of batch 3** (Massachusetts, Colorado, Maryland, Alabama, Oregon, Connecticut, Utah, Kansas), in one change, on Adam's own "merge" (his answer of 2026-11-10, "batch merge"). | Done in the go-live change. | 2026-11-12 (change written) |
| **3 January 2027** | **The 120th Congress is seated.** The map does not change (Massachusetts's layer 0 and layer 4 carry the same 9 districts, measured 2026-11-12), but the members elected on 3 November 2026 take their seats. | Nothing by hand: the weekly congress refresh carries the new members once the congress-legislators roster does. Look at that week's PR. | — |
| **When the legislators elected on 3 November 2026 take office** | **The chamber rosters name the sitting members**, read from the General Court's own member data, so the members elected on 3 November 2026 appear when that data lists them. | Nothing by hand: the weekly legislature refresh carries them. Read that week's PR, which may change many seats at once. | — |
| **When 1st Franklin, 16th Middlesex and 17th Middlesex are filled** | **The House's member table lists three districts as vacant** (read 2026-11-12), and their cards say so. | Nothing by hand: the weekly legislature refresh drops each vacancy when the table names a member. Look at that week's PR. | — |
| **When `www.mass.gov` can be read** | **Four statewide officers are listed without a name** because `www.mass.gov` answered both clients with HTTP 403 from the build sandbox on 2026-11-12. | The weekly statewide-officials job names them the first time a run reads the page. If a run on GitHub's servers is refused too, record it in the seed and leave them unnamed; never take a name from another page that does not belong to the office. | — |

## Re-check plan for each data file the app reads

The roster jobs and the tile job are in the standing table above. The files below have no job,
because a weekly job on a boundary would almost always find nothing to change.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **3 January 2029**, and on any court order | `congress-districts.json` | Drawn from TIGERweb layer 0; the builder refuses on or after 3 January 2029, so a person reads which map the 2028 election used before anything is drawn | 2026-11-12 (built) |
| **Annually**, and on any court order | `ma-senate-districts.json`, `ma-house-districts.json` | TIGERweb's 2026 state legislative districts (layers 1 and 2). The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage rolls. | 2026-11-12 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same county fabric, the outline being that fabric dissolved, so they share one clock. `ma/scripts/build_metro_outline.py --check` tests the outline against its 14 inside anchors and 15 outside anchors, so it would catch a lost county and would not notice a redrawn line | 2026-11-12 (built) |
| **Annually**, when TIGERweb's AIANNHA service moves to a new vintage | `tribal-areas.json` | The Census redraws tribal land rarely, and the land is served cache-first. `python3 scripts/build_tribal_areas.py --check` holds the file to the land-to-government join and the Bureau of Indian Affairs' list on every pull request; it never proves the Census has not redrawn. The same check holds the Hassanamisco (state) Reservation's absence to the join's `landsNotDrawn` row and to the sentence on the page that names it. Rebuild with `python3 scripts/build_tribal_areas.py --state Massachusetts --tag ma` and compare the 2 pieces | 2026-11-13 (built) |
| **Annually**, and in the same change as any new Massachusetts layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-11-12 (written with the instance) |
| **Before each election**, and when an officer changes | `statewide-officials.json` | Built from `data/source/statewide-officials.source.json`, each officer read from their own office's page. The weekly name check in the root goes red on a handover | 2026-11-12 (built) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance was dark until its go-live change.** It had no `metros.json` entry and no `layer-concepts.json` column, and `'ma/**'` was blanket-excluded from the Pages deploy. | Set up 2026-11-12 on Adam's state-level launch plan, batch 3. | DONE in the batch 3 go-live change (written 2026-11-12): `metros.json` entry (with the worksheet's own `bbox`) and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`), and the two roster jobs regenerating the pages that read their rosters; the done-standard scorer and `docs/expected-governments.json`; the tribal-coverage record in `data/tribal-government-join.json`; the fixed-point audit below; the traffic page's tables; and every generated root page. |
| **No county, city or school board official is named.** | Not surveyed source by source in this change. Recorded as gaps `ma-county-officials`, `ma-municipal-officeholders` and `ma-school-board-members`. | Each as its own change, largest first. |
| **Voting precincts and special districts are not drawn.** | Not surveyed in this change; the done-standard scorer marks both open. | A precinct layer as its own change, if a statewide source proves current. |
| **No town meeting, select board, council or mayor is named.** | Every point is in a city or town, so this is the local government a reader most often asks about. The done-standard scorer marks the sub-county level open. | A statewide list of city and town officials from a government source, as its own change. |
| **The land of Massachusetts's tribal nations was not drawn.** | Measured 2026-11-12 with `scripts/tribal_areas.py --report Massachusetts` (see this instance's CLAUDE.md). Massachusetts is recorded as not yet covered in `data/tribal-government-join.json` (the go-live change). | DONE IN PART 2026-11-13, on Adam's ruling of that day: Tribal Government draws the two Wampanoag trust lands and names no council yet (gap `ma-tribal-government`). STILL OPEN: the Hassanamisco (state) Reservation in Grafton is not drawn. www.mass.gov refused this project on 2026-11-13 and the one readable state source, House Bill 3413, is a bill and not a law. Re-read both when the bill moves or the General Court's session ends; a state law or a state agency's page naming the tribe is what draws it (delete the `landsNotDrawn` row in `data/tribal-government-join.json` in that change). ALSO WATCH the Mashpee link: the Bureau of Indian Affairs lists `http://www.mashpeewampanoagtribe.com`, which served another publisher's pages that day, so the join withdraws it; `scripts/validate_tribal_join.py --check` fails once the Bureau lists a different address. |
| **The negative point.** | **THE NEGATIVE POINT IS OPEN WATER AND NEVER MOVES**: the Atlantic about 15 km east of Cape Cod's outer shore at Wellfleet (41.95, -69.70). Measured 2026-11-12 against TIGERweb's state layer and every outline in `fleet-outlines.json`. | Nothing: no instance will ever serve it. |
| **Fixed points elsewhere in the fleet that sat in Massachusetts were dealt with in the go-live change.** | Audited 2026-11-12 in the go-live change: every coordinate pair in every instance's smoke test, worksheet and outline builder, and the root's landing test, tested against this state's outline. The points inside Massachusetts are New Hampshire's, New York's and Connecticut's outline-builder OUTSIDE anchors (Tyngsborough, Townsend, Winchendon, Northfield and Amesbury; Pittsfield; Sheffield, Springfield and Webster), which must stay outside those states and need nothing, and two ZIP test rings in New Hampshire's and Connecticut's smoke tests that reach into Massachusetts by design. No neighbour's test point had to move. | Re-run the audit whenever a neighbouring state goes live. Live neighbours: New York, New Hampshire, Connecticut (this batch); not yet live: Vermont and Rhode Island. |
| **The done-standard scorer knows Massachusetts.** | Read 2026-11-12. | DONE in the go-live change: `STATE_COUNTIES`, `ANSWERS` (each level measured or marked open), and the state's units in `docs/expected-governments.json`. Massachusetts scores E, A and M, and 7 of the 14 levels (`docs/EAM_STATUS.md`). |
| **There is no `ma/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
