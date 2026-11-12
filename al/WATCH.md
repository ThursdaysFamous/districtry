# WATCH.md — Alabama's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| **2031**, when TIGERweb publishes 2030 census blocks | The Census 2020 block populations the compare screen counts people with, the one dataset here that cannot change until then | `al/data/app/population/` | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set this app's `INSTANCES` row's `total` to its 2030 count and rebuild with `--instance al`. `--check` forces it: the first legislative map drawn on 2030 blocks fails against 2020 people until this row is done. |
| Weekly (Mon 22:43 UTC) | U.S. House (Alabama) roster refresh | `.github/workflows/update-al-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Tue 22:43 UTC) | Alabama Senate + Alabama House roster refresh, from the Legislature's own member data | `.github/workflows/update-al-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a seat listed twice, a district the map does not draw, fewer named members than the builder's floor, or too few members carrying their Capitol office, e-mail address or party |
| Weekly (`update-statewide-officials.yml`) | The statewide officials line | `scripts/build_statewide_officials.py` → PR on change | Review + merge the PR; a red run is a handover to read |
| Weekly (Sun, `update-tiger-tiles.yml`) | The three TIGERweb fabric archives (municipality, school district and ZIP) | `scripts/mirror_tiger_tiles.py` → PR on change | Review + merge the PR; it moves this app's cache name itself |
| Monthly (1st of month 23:31 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/al-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **The batch 3 go-live** | **Alabama opens with the rest of batch 3** (Massachusetts, Colorado, Maryland, Alabama, Oregon, Connecticut, Utah, Kansas), in one change, on Adam's own "merge" (his answer of 2026-11-10, "batch merge"). | Done in the go-live change. | 2026-11-12 (change written) |
| **3 January 2027** | **The 120th Congress is seated, and Alabama's congressional map changes.** The card draws TIGERweb layer 4 (the 119th Congress, the map the sitting members were elected from in 2024) and the builder refuses on or after this date. Layer 0 is the map the 3 November 2026 election used; 4 of the 7 districts differ between the two (the lowest intersection-over-union District 2 at 0.416, then District 1 at 0.583, District 7 at 0.703 and District 6 at 0.933) (measured 2026-11-12). | Switch `al/scripts/build_legislative_boundaries.py`'s congress entry to layer 0 and `CD120`, rebuild `congress-districts.json` and its archive, bump the cache name, and check the weekly congress refresh carries the members elected on 3 November 2026. A person's step, because the card then names different people for much of the state. | — |
| **When the legislators elected on 3 November 2026 take office** | **The chamber rosters name the sitting members**, read from the Legislature's own member data, so the members elected on 3 November 2026 appear when that data lists them. | Nothing by hand: the weekly legislature refresh carries them. Read that week's PR, which may change many seats at once. | — |

## Re-check plan for each data file the app reads

The roster jobs and the tile job are in the standing table above. The files below have no job,
because a weekly job on a boundary would almost always find nothing to change.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **3 January 2027** (above), and on any court order | `congress-districts.json` | The 119th Congress's map is drawn from TIGERweb layer 4, and the builder refuses on or after 3 January 2027, when the members elected from the new map take office | 2026-11-12 (built) |
| **Annually**, and on any court order | `al-senate-districts.json`, `al-house-districts.json` | TIGERweb's 2026 state legislative districts (layers 1 and 2). The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage rolls. | 2026-11-12 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same county fabric, the outline being that fabric dissolved, so they share one clock. `al/scripts/build_metro_outline.py --check` tests the outline against its 67 inside anchors and 14 outside anchors, so it would catch a lost county and would not notice a redrawn line | 2026-11-12 (built) |
| **Annually**, and in the same change as any new Alabama layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-11-12 (written with the instance) |
| **Before each election**, and when an officer changes | `statewide-officials.json` | Built from `data/source/statewide-officials.source.json`, each officer read from their own office's page. The weekly name check in the root goes red on a handover | 2026-11-12 (built) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance was dark until its go-live change.** It had no `metros.json` entry and no `layer-concepts.json` column, and `'al/**'` was blanket-excluded from the Pages deploy. | Set up 2026-11-12 on Adam's state-level launch plan, batch 3. | DONE in the batch 3 go-live change (written 2026-11-12): `metros.json` entry (with the worksheet's own `bbox`) and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`), and the two roster jobs regenerating the pages that read their rosters; the done-standard scorer and `docs/expected-governments.json`; the tribal-coverage record in `data/tribal-government-join.json`; the fixed-point audit below; the traffic page's tables; and every generated root page. |
| **No county, city or school board official is named.** | Not surveyed source by source in this change. Recorded as gaps `al-county-officials`, `al-municipal-officeholders` and `al-school-board-members`. | Each as its own change, largest first. |
| **Voting precincts and special districts are not drawn.** | Not surveyed in this change; the done-standard scorer marks both open. | A precinct layer as its own change, if a statewide source proves current. |
| **The land of Alabama's tribal nations is not drawn.** | Measured 2026-11-12 with `scripts/tribal_areas.py --report Alabama` (see this instance's CLAUDE.md). Alabama is recorded as not yet covered in `data/tribal-government-join.json` (the go-live change). | The fleet's tribal-government reader (`scripts/build_tribal_areas.py`) as its own change, with each nation's council named from its own pages. |
| **The negative point.** | **THE NEGATIVE POINT IS OPEN WATER AND NEVER MOVES**: the Gulf about 25 km south of Dauphin Island (29.95, -88.00). Measured 2026-11-12 against TIGERweb's state layer and every outline in `fleet-outlines.json`. | Nothing: no instance will ever serve it. |
| **Fixed points elsewhere in the fleet that sat in Alabama were dealt with in the go-live change.** | Audited 2026-11-12 in the go-live change. The points inside Alabama were Mississippi's `NEGATIVE_POINT` (York, 32.48, -88.25), Tennessee's `NEGATIVE_POINT` (near Hazel Green, 34.90, -86.60) and a ZIP test ring in Tennessee's smoke test, and the outline-builder OUTSIDE anchors of Florida, Georgia, Mississippi and Tennessee. Mississippi's point moved to the Gulf (30.00, -88.35) and York became an Alabama routing case. Tennessee's is a permalink-only point that never leaves, so it stays; Tennessee is surrounded by live apps and has no uncovered ground more than 2 km from every outline, so its stays-here check was dropped and Huntsville became an Alabama routing case. Florida's routing check gained Dothan and Georgia's Opelika. The OUTSIDE anchors and the ZIP ring need nothing. | Re-run the audit whenever a neighbouring state goes live. Live neighbours: Mississippi, Tennessee, Georgia and Florida; not yet live: none. |
| **The done-standard scorer knows Alabama.** | Read 2026-11-12. | DONE in the go-live change: `STATE_COUNTIES`, `ANSWERS` (each level measured or marked open), and the state's units in `docs/expected-governments.json`. Alabama scores E, A and M, and 6 of the 14 levels (`docs/EAM_STATUS.md`). |
| **There is no `al/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
