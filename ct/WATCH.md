# WATCH.md — Connecticut's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| **2031**, when TIGERweb publishes 2030 census blocks | The Census 2020 block populations the compare screen counts people with, the one dataset here that cannot change until then | `ct/data/app/population/` | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set this app's `INSTANCES` row's `total` to its 2030 count and rebuild with `--instance ct`. `--check` forces it: the first legislative map drawn on 2030 blocks fails against 2020 people until this row is done. |
| Weekly (Mon 23:07 UTC) | U.S. House (Connecticut) roster refresh | `.github/workflows/update-ct-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Tue 23:07 UTC) | Connecticut Senate + Connecticut House roster refresh, from the General Assembly's own member data | `.github/workflows/update-ct-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a seat listed twice, a district the map does not draw, fewer named members than the builder's floor, or too few members carrying their Capitol office, e-mail address, party or member page |
| Weekly (`update-statewide-officials.yml`) | The statewide officials line | `scripts/build_statewide_officials.py` → PR on change | Review + merge the PR; a red run is a handover to read |
| Weekly (Sun, `update-tiger-tiles.yml`) | The five TIGERweb fabric archives (town, three school district layers and ZIP) | `scripts/mirror_tiger_tiles.py` → PR on change | Review + merge the PR; it moves this app's cache name itself |
| Monthly (1st of month 23:41 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/ct-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **The batch 3 go-live** | **Connecticut opens with the rest of batch 3** (Massachusetts, Colorado, Maryland, Alabama, Oregon, Connecticut, Utah, Kansas), in one change, on Adam's own "merge" (his answer of 2026-11-10, "batch merge"). | Done in the go-live change. | 2026-11-12 (change written) |
| **3 January 2027** | **The 120th Congress is seated.** The map does not change (Connecticut's layer 0 and layer 4 carry the same 5 districts, measured 2026-11-12), but the members elected on 3 November 2026 take their seats. | Nothing by hand: the weekly congress refresh carries the new members once the congress-legislators roster does. Look at that week's PR. | — |
| **When the legislators elected on 3 November 2026 take office** | **The chamber rosters name the sitting members**, read from the General Assembly's own member data, so the members elected on 3 November 2026 appear when that data lists them. | Nothing by hand: the weekly legislature refresh carries them. Read that week's PR, which may change many seats at once. | — |

## Re-check plan for each data file the app reads

The roster jobs and the tile job are in the standing table above. The files below have no job,
because a weekly job on a boundary would almost always find nothing to change.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **3 January 2029**, and on any court order | `congress-districts.json` | Drawn from TIGERweb layer 0; the builder refuses on or after 3 January 2029, so a person reads which map the 2028 election used before anything is drawn | 2026-11-12 (built) |
| **Annually**, and on any court order | `ct-senate-districts.json`, `ct-house-districts.json` | TIGERweb's 2026 state legislative districts (layers 1 and 2). The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage rolls. | 2026-11-12 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same county fabric, the outline being that fabric dissolved, so they share one clock. `ct/scripts/build_metro_outline.py --check` tests the outline against its 9 inside anchors and 10 outside anchors, so it would catch a lost planning region and would not notice a redrawn line | 2026-11-12 (built) |
| **Annually**, and in the same change as any new Connecticut layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-11-12 (written with the instance) |
| **Before each election**, and when an officer changes | `statewide-officials.json` | Built from `data/source/statewide-officials.source.json`, each officer read from their own office's page. The weekly name check in the root goes red on a handover | 2026-11-12 (built) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance was dark until its go-live change.** It had no `metros.json` entry and no `layer-concepts.json` column, and `'ct/**'` was blanket-excluded from the Pages deploy. | Set up 2026-11-12 on Adam's state-level launch plan, batch 3. | DONE in the batch 3 go-live change (written 2026-11-12): `metros.json` entry (with the worksheet's own `bbox`) and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`), and the two roster jobs regenerating the pages that read their rosters; the done-standard scorer and `docs/expected-governments.json`; the tribal-coverage record in `data/tribal-government-join.json`; the fixed-point audit below; the traffic page's tables; and every generated root page. |
| **No town or board of education official is named.** | Not surveyed source by source in this change. Recorded as gaps `ct-municipal-officeholders` and `ct-school-board-members`. | Each as its own change, largest first. |
| **Voting precincts and special districts are not drawn.** | Not surveyed in this change; the done-standard scorer marks both open. | A precinct layer as its own change, if a statewide source proves current. |
| **No board of selectmen, council or mayor is named.** | Every point is in a town, so this is the local government a reader most often asks about. The done-standard scorer marks the sub-county level open. | A statewide list of town officials from a government source, as its own change. |
| **The land of Connecticut's tribal nations is not drawn.** | Measured 2026-11-12 with `scripts/tribal_areas.py --report Connecticut` (see this instance's CLAUDE.md). Connecticut is recorded as not yet covered in `data/tribal-government-join.json` (the go-live change). | The fleet's tribal-government reader (`scripts/build_tribal_areas.py`) as its own change, with each nation's council named from its own pages. |
| **The negative point.** | **THE NEGATIVE POINT IS OPEN WATER AND NEVER MOVES**: the Atlantic about 25 km south of Block Island and 30 km south-east of Montauk Point (40.85, -71.60). Measured 2026-11-12 against TIGERweb's state layer and every outline in `fleet-outlines.json`. | Nothing: no instance will ever serve it. |
| **Fixed points elsewhere in the fleet that sat in Connecticut were dealt with in the go-live change.** | Audited 2026-11-12 in the go-live change. The points inside Connecticut are New York's `NEGATIVE_POINT` (downtown Hartford, 41.7637, -72.6851) and New York's and Massachusetts's outline-builder OUTSIDE anchors (Hartford; Enfield and Thompson). New York's point is a permalink-only point: its checks boot it or select it in the app and none clicks it, and a selection the app makes itself never leaves, so it stays; its note was updated to say Connecticut covers it now. The OUTSIDE anchors need nothing. | Re-run the audit whenever a neighbouring state goes live. Live neighbours: New York and Massachusetts (this batch); not yet live: Rhode Island. |
| **The done-standard scorer knows Connecticut.** | Read 2026-11-12. | DONE in the go-live change: `STATE_COUNTIES` and `NO_COUNTY_TIER`, `ANSWERS` (each level measured or marked open), and the state's units in `docs/expected-governments.json`. Connecticut scores M; with no county government, E and A do not apply, and 7 of the 14 levels (`docs/EAM_STATUS.md`). |
| **There is no `ct/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
