# WATCH.md — Pennsylvania's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| **2031**, when TIGERweb publishes 2030 census blocks | The Census 2020 block populations the compare screen counts people with, the one dataset here that cannot change until then | `pa/data/app/population/` | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set this app's `INSTANCES` row's `total` to its 2030 count and rebuild with `--instance pa`. `--check` forces it: the first legislative map drawn on 2030 blocks fails against 2020 people until this row is done. |
| Weekly (Mon 20:07 UTC) | U.S. House (Pennsylvania) roster refresh | `.github/workflows/update-pa-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Tue 20:07 UTC) | Pennsylvania Senate + House roster refresh, from the General Assembly's member lists and member pages | `.github/workflows/update-pa-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a seat carried by two cards, a Capitol office outside Harrisburg's Capitol ZIP codes, or a field (party, Capitol office, e-mail) going missing from members who carried it |
| Weekly (Sun, `update-tiger-tiles.yml`) | The three TIGERweb fabric archives (municipality, school district, ZIP) | `scripts/mirror_tiger_tiles.py` → PR on change | Review + merge the PR; it moves this app's cache name itself |
| Monthly (1st, 21:57 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/pa-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **The batch 1 go-live** | **Pennsylvania opens with Nevada, Arizona, New Jersey and New Hampshire**, in one change, on Adam's own "merge" (his answer of 2026-11-10, "batch merge"). | Done in the go-live change. | 2026-11-11 (change written) |
| **3 January 2027** | **The 120th Congress is seated.** The congressional map does not change (layer 0 and layer 4 carry the same 17 districts). | Check the weekly congress refresh carries the members elected on 3 November 2026. | — |
| **1 December 2026** | **The General Assembly's new session.** All 203 House seats and the 25 even-numbered Senate seats were on the 3 November 2026 ballot. | Check the weekly legislature refresh carries the new members once the member lists name them. | — |

## Re-check plan for each data file the app reads

The two roster jobs and the tile job are in the standing table above. The files below have no
job, because a weekly job on a boundary would almost always find nothing to change.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **Annually**, when TIGERweb rolls its congressional vintage, and on any court order | `congress-districts.json` | The 2022 map is drawn from TIGERweb layer 0, and the builder refuses if layers 0 and 4 stop carrying the same 17 districts before 3 January 2027, and refuses outright on or after 3 January 2029 | 2026-11-10 (built) |
| **Annually**, and on any court order | `pa-senate-districts.json`, `pa-house-districts.json` | The 2022 plan is in force until the plan drawn after the 2030 census. The builder refuses if a TIGERweb layer's name changes, since TIGERweb renumbers its layers when a vintage rolls | 2026-11-10 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same 67-county TIGERweb fabric, the outline being that fabric dissolved, so they share one clock. `pa/scripts/build_metro_outline.py --check` tests the outline against its 67 inside anchors and 21 outside anchors, so it would catch a lost county and would not notice a redrawn line | 2026-11-10 (built) |
| **Annually**, and in the same change as any new Pennsylvania layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-11-10 (written with the instance) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance was dark until its go-live change.** It had no `metros.json` entry and no `layer-concepts.json` column, and `'pa/**'` was blanket-excluded from the Pages deploy. | Set up 2026-11-10 on Adam's state-level launch plan. | DONE in the batch 1 go-live change (written 2026-11-11): `metros.json` entry and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`), and the two roster jobs regenerating the pages that read their rosters; the done-standard scorer and `docs/expected-governments.json`; the tribal-coverage record in `data/tribal-government-join.json`; the fixed-point audit below; the statewide officials list (`data/app/statewide-officials.json`); the traffic page's tables; and every generated root page. |
| **No county, municipal or school board official is named.** | Not surveyed source by source in this change. Recorded as gaps `pa-county-officials`, `pa-municipal-officeholders` and `pa-school-board-members`. | Each as its own change, largest first. |
| **Voting precincts are not drawn.** | Not surveyed in this change. | A precinct layer as its own change, if a statewide source proves current. |
| **No fixed point elsewhere in the fleet needs to move for Pennsylvania.** | Audited 2026-11-11 in the go-live change: every coordinate pair in every instance's smoke test, worksheet and outline builder, and the root's landing test, landing builder and probe points, tested against `metro-outline.json`: the only points inside it are three neighbours' outline-builder OUTSIDE anchors, which must stay outside those states and need nothing: New Jersey's Philadelphia, Easton, Milford, New Hope and Morrisville, New York's Scranton and Erie, and West Virginia's Waynesburg and Uniontown. None of Pennsylvania's own test or worksheet points falls inside another live instance's outline in `fleet-outlines.json`. | Re-run the audit whenever a neighbouring state goes live. |
| **The negative point is water, so no neighbour's go-live moves it.** It is on Lake Erie beyond the international line north of Erie (42.62, -79.85). | Measured 2026-11-10: TIGERweb's state layer places it in no state, and no outline in `fleet-outlines.json` contains it. | Nothing, unless an Ontario instance is ever built. |
| **The done-standard scorer did not know Pennsylvania.** | Read 2026-11-10. | DONE in the go-live change: `STATE_COUNTIES` (67, the 67 counties), `ANSWERS` (each level measured or marked open), and the state's units in `docs/expected-governments.json`. Pennsylvania scores E, A and M, and 7 of the 14 levels (`docs/EAM_STATUS.md`). |
| **There is no `pa/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
