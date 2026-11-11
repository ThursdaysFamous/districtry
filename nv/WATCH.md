# WATCH.md — Nevada's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| **2031**, when TIGERweb publishes 2030 census blocks | The Census 2020 block populations the compare screen counts people with, the one dataset here that cannot change until then | `nv/data/app/population/` | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set this app's `INSTANCES` row's `total` to its 2030 count and rebuild with `--instance nv`. `--check` forces it: the first legislative map drawn on 2030 blocks fails against 2020 people until this row is done. |
| Weekly (Mon 20:21 UTC) | U.S. House (Nevada) roster refresh | `.github/workflows/update-nv-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Tue 20:21 UTC) | Nevada Senate + Assembly roster refresh, from the Legislature's member lists and member pages | `.github/workflows/update-nv-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a seat carried by two rows, a member page naming another district, a mailing address that is no longer in Carson City, or a field (party, Carson City office, e-mail) going missing from members who carried it |
| Weekly (Sun, `update-tiger-tiles.yml`) | The three TIGERweb fabric archives (city, school district, ZIP) | `scripts/mirror_tiger_tiles.py` → PR on change | Review + merge the PR; it moves this app's cache name itself |
| Monthly (1st, 22:11 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/nv-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **The batch 1 go-live** | **Nevada opens with Pennsylvania, Arizona, New Jersey and New Hampshire**, in one change, on Adam's own "merge" (his answer of 2026-11-10, "batch merge"). | Done in the go-live change. | 2026-11-11 (change written) |
| **3 January 2027** | **The 120th Congress is seated.** The congressional map does not change (layer 0 and layer 4 carry the same 4 districts). | Check the weekly congress refresh carries the members elected on 3 November 2026. | — |
| **1 February 2027** | **The Legislature's 2027 session opens.** All 42 Assembly seats and about half the Senate seats were on the 3 November 2026 ballot, and on 2026-11-10 twelve Assembly members and one senator printed only a Carson City telephone. | Check the weekly legislature refresh carries the new members, and their rooms and e-mail addresses once the member list prints them; raise the floors to what it then measures. | — |

## Re-check plan for each data file the app reads

The two roster jobs and the tile job are in the standing table above. The files below have no
job, because a weekly job on a boundary would almost always find nothing to change.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **Annually**, when TIGERweb rolls its congressional vintage, and on any court order | `congress-districts.json` | The 2021 map is drawn from TIGERweb layer 0, and the builder refuses if layers 0 and 4 stop carrying the same 4 districts before 3 January 2027, and refuses outright on or after 3 January 2029 | 2026-11-10 (built) |
| **Annually**, and on any court order | `nv-senate-districts.json`, `nv-assembly-districts.json` | The 2021 plan is in force until the plan drawn after the 2030 census. The builder refuses if a TIGERweb layer's name changes, since TIGERweb renumbers its layers when a vintage rolls, and refuses if the measured Senate-to-Assembly pairing moves | 2026-11-10 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same county fabric, the outline being that fabric dissolved, so they share one clock. `nv/scripts/build_metro_outline.py --check` tests the outline against its 17 inside anchors and 17 outside anchors, so it would catch a lost county and would not notice a redrawn line | 2026-11-10 (built) |
| **Annually**, and in the same change as any new Nevada layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-11-10 (written with the instance) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance was dark until its go-live change.** It had no `metros.json` entry and no `layer-concepts.json` column, and `'nv/**'` was blanket-excluded from the Pages deploy. | Set up 2026-11-10 on Adam's state-level launch plan. | DONE in the batch 1 go-live change (written 2026-11-11): `metros.json` entry and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`), and the two roster jobs regenerating the pages that read their rosters; the done-standard scorer and `docs/expected-governments.json`; the tribal-coverage record in `data/tribal-government-join.json`; the fixed-point audit below; the statewide officials list (`data/app/statewide-officials.json`); the traffic page's tables; and every generated root page. |
| **No county, city or school board official is named.** | Not surveyed source by source in this change. Recorded as gaps `nv-county-officials`, `nv-municipal-officeholders` and `nv-school-board-members`. | Each as its own change, largest first. |
| **Voting precincts are not drawn.** | Not surveyed in this change. | A precinct layer as its own change, if a statewide source proves current. |
| **The land of Nevada's tribal nations is not drawn.** | Measured 2026-11-11 at the go-live change with `scripts/tribal_areas.py --report Nevada`: the Census keeps 27 reservations and 8 trust lands in the state, and `data/tribal-government-join.json` records Nevada as not yet covered. | The fleet's tribal-government reader (`scripts/build_tribal_areas.py`) as its own change, with each nation's council named from its own pages where they publish one. |
| **No fixed point elsewhere in the fleet needs to move for Nevada.** | Audited 2026-11-11 in the go-live change: every coordinate pair in every instance's smoke test, worksheet and outline builder, and the root's landing test, landing builder and probe points, tested against `metro-outline.json`: the only points inside it are Arizona's outline-builder OUTSIDE anchors Laughlin and Mesquite, which must stay outside Arizona and need nothing. None of Nevada's own test or worksheet points falls inside another live instance's outline in `fleet-outlines.json`. | Re-run the audit whenever a neighbouring state goes live. |
| **The negative point is on a neighbour's land, so a neighbour's go-live moves it.** It is in Owyhee County, Idaho, about 15 km north of the Nevada line (42.15, -116.00). | Measured 2026-11-10: TIGERweb's state layer names Idaho there, and no outline in `fleet-outlines.json` contains it. Idaho is in the last batch of the state-level launch, after California, Oregon, Utah and Arizona. | The change that makes Idaho live moves it. Arizona opens in this same batch, so its outline was checked too: the point is more than 500 km north of Arizona. |
| **The done-standard scorer did not know Nevada.** | Read 2026-11-10. | DONE in the go-live change: `STATE_COUNTIES` (17, the 16 counties and Carson City), `ANSWERS` (each level measured or marked open), and the state's units in `docs/expected-governments.json`. Nevada scores E, A and M, and 6 of the 14 levels (`docs/EAM_STATUS.md`). |
| **There is no `nv/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
