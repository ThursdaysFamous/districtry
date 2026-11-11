# WATCH.md — New Hampshire's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| **2031**, when TIGERweb publishes 2030 census blocks | The Census 2020 block populations the compare screen counts people with, the one dataset here that cannot change until then | `nh/data/app/population/` | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set this app's `INSTANCES` row's `total` to its 2030 count and rebuild with `--instance nh`. `--check` forces it: the first legislative map drawn on 2030 blocks fails against 2020 people until this row is done. |
| Weekly (Mon 21:55 UTC) | U.S. House (New Hampshire) roster refresh | `.github/workflows/update-nh-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Tue 21:55 UTC) | New Hampshire Senate + House roster refresh, from the General Court's own member file, or Open States' export of the General Court's pages when that file cannot be read | `.github/workflows/update-nh-legislature-roster.yml` → PR on change | Review + merge the PR. **Read the first run's log for which route it used** (below). A red run is a person's job: a district carrying more members than it elects, a member with no district or a district the plan does not name, or a field (party, e-mail) going missing from members who carried it |
| Weekly (Sun, `update-tiger-tiles.yml`) | The five TIGERweb fabric archives (City or Town, three school district tilings, ZIP) | `scripts/mirror_tiger_tiles.py` → PR on change | Review + merge the PR; it moves this app's cache name itself |
| Monthly (1st, 23:45 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/nh-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose. Its first run says whether a runner reaches gc.nh.gov, which the build sandbox could not |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **The batch 1 go-live** | **New Hampshire opens with Pennsylvania, Nevada, Arizona and New Jersey**, in one change, on Adam's own "merge" (his answer of 2026-11-10, "batch merge"). | Done in the go-live change. | 2026-11-11 (change written) |
| **3 January 2027** | **The 120th Congress and the 2027-2028 General Court are seated.** The congressional map does not change (layers 0 and 4 carry the same two districts), and every seat in both chambers was on the 3 November 2026 ballot, since both serve two-year terms. | Check the weekly refreshes carry the members elected on 3 November 2026: both U.S. House members, all 24 senators and the 400 representatives. | — |

## Re-check plan for each data file the app reads

The two roster jobs and the tile job are in the standing table above. The files below have no
job, because a weekly job on a boundary would almost always find nothing to change.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **Annually**, when TIGERweb rolls its congressional vintage, and on any court order | `congress-districts.json` | The 2022 map is drawn from TIGERweb layer 0, and the builder refuses if layers 0 and 4 stop carrying the same two districts before 3 January 2027, and refuses outright on or after 3 January 2029 | 2026-11-11 (built) |
| **Annually**, and on any court order | `nh-senate-districts.json`, `nh-house-districts.json` | The 2022 Senate and House plans are in force until the plans drawn after the 2030 census. The builder refuses if a TIGERweb or GRANIT layer's name changes, if a floterial stops being an exact union of whole base districts, or if GRANIT's base districts stop matching TIGER's 164 | 2026-11-11 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same county fabric, the outline being that fabric dissolved, so they share one clock. `nh/scripts/build_metro_outline.py --check` tests the outline against its inside and outside anchors, so it would catch a lost county and would not notice a redrawn line | 2026-11-11 (built) |
| **Annually**, and in the same change as any new New Hampshire layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-11-11 (written with the instance) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance was dark until its go-live change.** It had no `metros.json` entry and no `layer-concepts.json` column, and `'nh/**'` was blanket-excluded from the Pages deploy. | Set up 2026-11-11 on Adam's state-level launch plan. | DONE in the batch 1 go-live change (written 2026-11-11): `metros.json` entry and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`), whose House table names every member of a base district and of the floterial drawn over it (`build_officeholder_tables.nh_house_districts`), and the two roster jobs regenerating the pages that read their rosters; the done-standard scorer and `docs/expected-governments.json`; the tribal-coverage record in `data/tribal-government-join.json`; the fixed-point audit below; the statewide officials list (`data/app/statewide-officials.json`); the traffic page's tables; and every generated root page. |
| **gc.nh.gov could not be reached from the build sandbox.** Every request, robots.txt included, got an empty reply on 2026-11-11, so the first roster came from Open States' export (route 2) and the monthly source check carries a WARN row for the host. | Measured 2026-11-11 from the sandbox only. | The first weekly roster run and the first monthly source run, from a GitHub runner. If a runner reaches the General Court, the roster moves to route 1 on its own; if not, record that here and keep route 2. |
| **Representatives' personal e-mail addresses are left off.** On the Open States route only an address at `gc.nh.gov` or `leg.state.nh.us` is carried, because many representatives give the General Court a personal address and Open States is not a government. 329 of the 382 listed House members carried an address on 2026-11-11. | Read 2026-11-11. | Route 1, the General Court's own file, carries whatever it prints beside each member, under the fleet rule of 2026-10-17. |
| **The member file's telephone column is not read.** | Not read in this pass. | Read it in a change of its own, holding it to the same who-is-it-printed-beside rule, once a runner reaches the file. The file's home addresses are never read. |
| **18 House districts list fewer members than they elect** (382 of 400 seats named on 2026-11-11). | Read 2026-11-11 from Open States' export; each short record says how many it lists and on what day. | The General Court's own file, or the January 2027 refresh after the 3 November 2026 election. |
| **The Executive Council is not drawn.** New Hampshire elects a five-member Executive Council from districts, which approves the governor's appointments and contracts. | Not surveyed in this change. | A layer of its own, if the Secretary of State or GRANIT publishes the 2022 council districts; the statewide officials card does not cover it. |
| **No county, city, town or school board official is named.** | Not surveyed source by source in this change. Recorded as gaps `nh-county-officials`, `nh-municipal-officeholders` and `nh-school-board-members`. | Each as its own change, largest first. |
| **Voting places are not drawn.** New Hampshire votes by town and city ward, which the City or Town layer already draws at the town level. | Not surveyed in this change. | A ward layer for the cities, if a statewide source proves current. |
| **No fixed point elsewhere in the fleet needs to move for New Hampshire.** | Audited 2026-11-11 in the go-live change: every coordinate pair in every instance's smoke test, worksheet and outline builder, and the root's landing test, landing builder and probe points, tested against `metro-outline.json`: no point falls inside it. None of New Hampshire's own test or worksheet points falls inside another live instance's outline in `fleet-outlines.json`. | Re-run the audit whenever a neighbouring state goes live. |
| **The negative point is in the Gulf of Maine, and no go-live should ever move it.** (42.90, -70.30), about 40 km east of Hampton Beach. | Measured 2026-11-11: TIGERweb's state layer names no state there, and no outline in `fleet-outlines.json` contains it. | Nothing short of the fleet serving the ocean. |
| **The done-standard scorer did not know New Hampshire.** | Read 2026-11-11. | DONE in the go-live change: `STATE_COUNTIES` (10, the 10 counties), `ANSWERS` (each level measured or marked open), and the state's units in `docs/expected-governments.json`. New Hampshire scores E, A and M, and 8 of the 14 levels (`docs/EAM_STATUS.md`). |
| **There is no `nh/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
| **NH GRANIT is credited on the sources page** for the floterial districts. Its certificate chain ends at a root the build sandbox's proxy bundle lacks, so the builder and the monthly source check verify it against certifi's copy of Mozilla's store. | Measured 2026-11-11. | Nothing, unless GRANIT changes its certificate. |
