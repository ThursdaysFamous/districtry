# WATCH.md — New Mexico's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| **2031**, when TIGERweb publishes 2030 census blocks | The Census 2020 block populations the compare screen counts people with, the one dataset here that cannot change until then | `nm/data/app/population/` | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set this app's `INSTANCES` row's `total` to its 2030 count and rebuild with `--instance nm`. `--check` forces it: the first legislative map drawn on 2030 blocks fails against 2020 people until this row is done. |
| Weekly (Wed 22:05 UTC) | U.S. House (New Mexico) roster refresh | `.github/workflows/update-nm-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Thu 22:05 UTC) | New Mexico Senate + New Mexico House roster refresh, from the Legislature's own member pages | `.github/workflows/update-nm-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a seat listed twice, a district the map does not draw, fewer named members than the builder's floor, or too few members carrying their e-mail address, party or member page |
| Weekly (`update-statewide-officials.yml`) | The statewide officials line | `scripts/build_statewide_officials.py` → PR on change | Review + merge the PR; a red run is a handover to read |
| Weekly (Sun, `update-tiger-tiles.yml`) | The three TIGERweb fabric archives (municipality, school district and ZIP) | `scripts/mirror_tiger_tiles.py` → PR on change | Review + merge the PR; it moves this app's cache name itself |
| Monthly (2nd of month 22:05 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/nm-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **The batch 4 go-live** | **New Mexico opens with the rest of batch 4** (New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in one change, on Adam's own "merge" (his answer of 2026-11-10, "batch merge"). | Done in the go-live change. | 2026-11-12 (change written) |
| **3 January 2027** | **The 120th Congress is seated.** The map does not change (New Mexico's layer 0 and layer 4 carry the same 3 districts, measured 2026-11-12), but the members elected on 3 November 2026 take their seats. | Nothing by hand: the weekly congress refresh carries the new members once the congress-legislators roster does. Look at that week's PR. | — |
| **When the legislators elected on 3 November 2026 take office** | **The chamber rosters name the sitting members**, read from the Legislature's own member pages, so the members elected on 3 November 2026 appear when that source lists them. | Nothing by hand: the weekly legislature refresh carries them. Read that week's PR, which may change many seats at once. | — |
| **When House Districts 37 and 64 are listed** | **The House's member list did not carry two districts** (read 2026-11-12), and their cards say no member is listed. | Nothing by hand: the weekly legislature refresh fills each seat when the list names a member. Look at that week's PR. | — |

## Re-check plan for each data file the app reads

The roster jobs and the tile job are in the standing table above. The files below have no job,
because a weekly job on a boundary would almost always find nothing to change.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **3 January 2029**, and on any court order | `congress-districts.json` | Drawn from TIGERweb layer 0; the builder refuses on or after 3 January 2029, so a person reads which map the 2028 election used before anything is drawn | 2026-11-12 (built) |
| **Annually**, and on any court order | `nm-senate-districts.json` and `nm-house-districts.json` | TIGERweb's 2026 state legislative districts (layers 1 and 2). The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage rolls. | 2026-11-12 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same county fabric, the outline being that fabric dissolved, so they share one clock. `nm/scripts/build_metro_outline.py --check` tests the outline against its 33 inside anchors and 14 outside anchors, so it would catch a lost county and would not notice a redrawn line | 2026-11-12 (built) |
| **Annually**, when TIGERweb's AIANNHA service moves to a new vintage | `tribal-areas.json` | The Census redraws tribal land rarely, and the land is served cache-first. `python3 scripts/build_tribal_areas.py --check` holds the file to the land-to-government join and the Bureau of Indian Affairs' list on every pull request; it never proves the Census has not redrawn. The Bureau's town for four pueblos is Santa Fe; a nation's own site naming another town is not read yet. Rebuild with `python3 scripts/build_tribal_areas.py --state "New Mexico" --tag nm` and compare the 37 pieces | 2026-11-13 (built) |
| **Annually**, and in the same change as any new New Mexico layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-11-12 (written with the instance) |
| **Before each election**, and when an officer changes | `statewide-officials.json` | Built from `data/source/statewide-officials.source.json`, each officer read from their own office's page. The weekly name check in the root goes red on a handover | 2026-11-12 (built) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance was dark until its go-live change.** It had no `metros.json` entry and no `layer-concepts.json` column, and `'nm/**'` was blanket-excluded from the Pages deploy. | Set up 2026-11-12 on Adam's state-level launch plan, batch 4. | DONE in the batch 4 go-live change (written 2026-11-12): `metros.json` entry (with the worksheet's own `bbox`) and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`), and the two roster jobs regenerating the pages that read their rosters; the done-standard scorer and `docs/expected-governments.json`; the tribal-coverage record in `data/tribal-government-join.json`; the fixed-point audit below; the traffic page's tables; and every generated root page. |
| **No county, city or school board official is named.** | Not surveyed source by source in this change. Recorded as gaps `nm-county-officials`, `nm-municipal-officeholders` and `nm-school-board-members`. | Each as its own change, largest first. |
| **Voting precincts and special districts are not drawn.** | Not surveyed in this change; the done-standard scorer marks both open. | A precinct layer as its own change, if a statewide source proves current. |
| **The land of New Mexico's tribal nations was not drawn.** | Measured 2026-11-12 with `scripts/tribal_areas.py --report "New Mexico"` (see this instance's CLAUDE.md). New Mexico is recorded as not yet covered in `data/tribal-government-join.json` (the go-live change). | DONE 2026-11-13 (the tribal change): Tribal Government draws all 37 pieces, the Navajo Nation's whole and simplified, and names no council yet (gap `nm-tribal-government`). |
| **The negative point.** | **THE NEGATIVE POINT IS IN MEXICO AND NEVER MOVES**: Sonora, just south of the bootheel (31.25, -108.6). Measured 2026-11-12 against TIGERweb's state layer and every outline in `fleet-outlines.json`. | Nothing: no instance will ever serve it. |
| **Fixed points elsewhere in the fleet that sat in New Mexico were dealt with in the go-live change.** | Measured 2026-11-12 over every coordinate in every other instance's smoke test and worksheet, tested against this state's outline in fleet-outlines.json: Oklahoma's negative point sat in Curry County, New Mexico. It stays where it is, because Oklahoma only boots or selects it, and its click became a New Mexico routing case; Colorado's and Utah's tests also gained the New Mexico State Capitol as one. | Re-run the audit if a neighbour's outline is rebuilt. Every neighbour is live once this change lands: Arizona, Colorado, Oklahoma, Texas and Utah. |
| **The done-standard scorer knows New Mexico.** | Read 2026-11-12. | DONE in the go-live change: `STATE_COUNTIES`, `ANSWERS` (each level measured or marked open), and the state's units in `docs/expected-governments.json`. New Mexico scores E, A and M, and 6 of the 14 levels (`docs/EAM_STATUS.md`). |
| **There is no `nm/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
