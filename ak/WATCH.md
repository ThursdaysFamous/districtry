# WATCH.md — Alaska's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| **2031**, when TIGERweb publishes 2030 census blocks | The Census 2020 block populations the compare screen counts people with, the one dataset here that cannot change until then | `ak/data/app/population/` | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set this app's `INSTANCES` row's `total` to its 2030 count and rebuild with `--instance ak`. `--check` forces it: the first legislative map drawn on 2030 blocks fails against 2020 people until this row is done. |
| Weekly (Wed 23:33 UTC) | U.S. House (Alaska) roster refresh | `.github/workflows/update-ak-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Thu 23:33 UTC) | Alaska Senate + Alaska House roster refresh, from the Legislature's own member pages | `.github/workflows/update-ak-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a seat listed twice, a district the map does not draw, fewer named members than the builder's floor, or too few members carrying their e-mail address, party, telephone or member page |
| Weekly (`update-statewide-officials.yml`) | The statewide officials line | `scripts/build_statewide_officials.py` → PR on change | Review + merge the PR; a red run is a handover to read |
| Weekly (Sun, `update-tiger-tiles.yml`) | The three TIGERweb fabric archives (municipality, school district and ZIP) | `scripts/mirror_tiger_tiles.py` → PR on change | Review + merge the PR; it moves this app's cache name itself |
| Monthly (2nd of month 23:33 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/ak-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **The batch 4 go-live** | **Alaska opens with the rest of batch 4** (New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in one change, on Adam's own "merge" (his answer of 2026-11-10, "batch merge"). | Done in the go-live change. | 2026-11-12 (change written) |
| **3 January 2027** | **The 120th Congress is seated.** The map does not change (Alaska elects its one member at large, and layer 0 and layer 4 carry the same one record, measured 2026-11-12), but the member elected on 3 November 2026 takes the seat. | Nothing by hand: the weekly congress refresh carries the member once the congress-legislators roster does. Look at that week's PR. | — |
| **January 2027** | **The 35th Legislature convenes**, seating the members elected on 3 November 2026. | Nothing by hand: the weekly legislature refresh carries them when the Legislature's pages list them. Read that week's PR. | — |
| **When `ltgov.alaska.gov` serves a complete certificate chain** | **The lieutenant governor is listed without a name**, because the office's own site sends no intermediate certificate (measured 2026-11-12). | The weekly statewide-officials job names the officer the first time a run can read the page. Never turn certificate checking off and never take the name from a page that does not belong to the office. | — |

## Re-check plan for each data file the app reads

The roster jobs and the tile job are in the standing table above. The files below have no job,
because a weekly job on a boundary would almost always find nothing to change.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **3 January 2029**, and after the 2030 apportionment | `congress-districts.json` | The whole state, drawn from TIGERweb layer 0; the builder refuses on or after 3 January 2029, so a person reads the apportionment after the 2030 census before anything is drawn | 2026-11-12 (built) |
| **Annually**, and on any court order | `ak-senate-districts.json` and `ak-house-districts.json` | TIGERweb's 2026 state legislative districts (layers 1 and 2). The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage rolls. The two maps share one topology, so they are rebuilt together and `--check` holds the nesting in CI. | 2026-11-12 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same county fabric, the outline being that fabric dissolved, so they share one clock. `ak/scripts/build_metro_outline.py --check` tests the outline against its 30 inside anchors and 9 outside anchors, so it would catch a lost borough or census area and would not notice a redrawn line | 2026-11-12 (built) |
| **Annually**, and in the same change as any new Alaska layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-11-12 (written with the instance) |
| **Before each election**, and when an officer changes | `statewide-officials.json` | Built from `data/source/statewide-officials.source.json`, each officer read from their own office's page. The weekly name check in the root goes red on a handover | 2026-11-12 (built) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance was dark until its go-live change.** It had no `metros.json` entry and no `layer-concepts.json` column, and `'ak/**'` was blanket-excluded from the Pages deploy. | Set up 2026-11-12 on Adam's state-level launch plan, batch 4. | DONE in the batch 4 go-live change (written 2026-11-12): `metros.json` entry (with the worksheet's own `bbox`) and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`), and the two roster jobs regenerating the pages that read their rosters; the done-standard scorer and `docs/expected-governments.json`; the tribal-coverage record in `data/tribal-government-join.json`; the fixed-point audit below; the traffic page's tables; and every generated root page. |
| **No borough, city or school board official is named.** | Not surveyed source by source in this change. Recorded as gaps `ak-county-officials`, `ak-municipal-officeholders` and `ak-school-board-members`. | Each as its own change, largest first. |
| **Voting precincts and special districts are not drawn.** | Not surveyed in this change; the done-standard scorer marks both open. | A precinct layer as its own change, if a statewide source proves current. |
| **The land of Alaska's tribal nations is not drawn.** | Measured 2026-11-12 with `scripts/tribal_areas.py --report "Alaska"` (see this instance's CLAUDE.md). Alaska is recorded as not yet covered in `data/tribal-government-join.json` (the go-live change). | The fleet's tribal-government reader (`scripts/build_tribal_areas.py`) as its own change, with each nation's council named from its own pages. |
| **The negative point.** | **THE NEGATIVE POINT IS OPEN WATER AND NEVER MOVES**: the Gulf of Alaska about 200 km south of Yakutat (57.7, -140.5). Measured 2026-11-12 against TIGERweb's state layer and every outline in `fleet-outlines.json`. | Nothing: no instance will ever serve it. |
| **No fixed point elsewhere in the fleet sits in Alaska.** | Measured 2026-11-12 over every coordinate in every other instance's smoke test and worksheet, tested against this state's outline in fleet-outlines.json: none falls in Alaska. | Nothing: Alaska borders no other state. |
| **The done-standard scorer knows Alaska.** | Read 2026-11-12. | DONE in the go-live change: `STATE_COUNTIES`, `ANSWERS` (each level measured or marked open), and the state's units in `docs/expected-governments.json`. Alaska scores E, A and M, and 6 of the 14 levels (`docs/EAM_STATUS.md`). |
| **There is no `ak/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
