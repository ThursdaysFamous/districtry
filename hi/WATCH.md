# WATCH.md — Hawaii's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| **2031**, when TIGERweb publishes 2030 census blocks | The Census 2020 block populations the compare screen counts people with, the one dataset here that cannot change until then | `hi/data/app/population/` | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set this app's `INSTANCES` row's `total` to its 2030 count and rebuild with `--instance hi`. `--check` forces it: the first legislative map drawn on 2030 blocks fails against 2020 people until this row is done. |
| Weekly (Wed 22:29 UTC) | U.S. House (Hawaii) roster refresh | `.github/workflows/update-hi-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Thu 22:29 UTC) | Hawaii Senate + Hawaii House roster refresh, from Open States' export, because the Legislature's own site blocks this project's client | `.github/workflows/update-hi-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a seat listed twice, a district the map does not draw, fewer named members than the builder's floor, or too few members carrying their e-mail address, party or member page |
| Weekly (`update-statewide-officials.yml`) | The statewide officials line | `scripts/build_statewide_officials.py` → PR on change | Review + merge the PR; a red run is a handover to read |
| Weekly (Sun, `update-tiger-tiles.yml`) | The two TIGERweb fabric archives (school district and ZIP) | `scripts/mirror_tiger_tiles.py` → PR on change | Review + merge the PR; it moves this app's cache name itself |
| Monthly (2nd of month 22:29 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/hi-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **The batch 4 go-live** | **Hawaii opens with the rest of batch 4** (New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in one change, on Adam's own "merge" (his answer of 2026-11-10, "batch merge"). | Done in the go-live change. | 2026-11-12 (change written) |
| **3 January 2027** | **The 120th Congress is seated.** The map does not change (Hawaii's layer 0 and layer 4 carry the same 2 districts, measured 2026-11-12), but the members elected on 3 November 2026 take their seats. | Nothing by hand: the weekly congress refresh carries the new members once the congress-legislators roster does. Look at that week's PR. | — |
| **20 January 2027** | **The Legislature elected on 3 November 2026 convenes.** The rosters come from Open States' export, which names the new members once Open States records them. | Look at the first weekly legislature PR after this date. If the export still names the old members a few weeks on, record it here; never take names from a page that does not belong to the Legislature or Open States. | — |

## Re-check plan for each data file the app reads

The roster jobs and the tile job are in the standing table above. The files below have no job,
because a weekly job on a boundary would almost always find nothing to change.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **3 January 2029**, and on any court order | `congress-districts.json` | Drawn from TIGERweb layer 0; the builder refuses on or after 3 January 2029, so a person reads which map the 2028 election used before anything is drawn | 2026-11-12 (built) |
| **Annually**, and on any court order | `hi-senate-districts.json` and `hi-house-districts.json` | TIGERweb's 2026 state legislative districts (layers 1 and 2). The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage rolls. | 2026-11-12 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same county fabric, the outline being that fabric dissolved, so they share one clock. `hi/scripts/build_metro_outline.py --check` tests the outline against its 5 inside anchors and 10 outside anchors, so it would catch a lost county and would not notice a redrawn line | 2026-11-12 (built) |
| **Annually**, and in the same change as any new Hawaii layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-11-12 (written with the instance) |
| **Before each election**, and when an officer changes | `statewide-officials.json` | Built from `data/source/statewide-officials.source.json`, each officer read from their own office's page. The weekly name check in the root goes red on a handover | 2026-11-12 (built) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance was dark until its go-live change.** It had no `metros.json` entry and no `layer-concepts.json` column, and `'hi/**'` was blanket-excluded from the Pages deploy. | Set up 2026-11-12 on Adam's state-level launch plan, batch 4. | DONE in the batch 4 go-live change (written 2026-11-12): `metros.json` entry (with the worksheet's own `bbox`) and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`), and the two roster jobs regenerating the pages that read their rosters; the done-standard scorer and `docs/expected-governments.json`; the tribal-coverage record in `data/tribal-government-join.json`; the fixed-point audit below; the traffic page's tables; and every generated root page. |
| **No county mayor or council member is named.** | Not surveyed source by source in this change. Recorded as gap `hi-county-officials`. | Each as its own change, largest first. |
| **Voting precincts and special districts are not drawn.** | Not surveyed in this change; the done-standard scorer marks both open. | A precinct layer as its own change, if a statewide source proves current. |
| **The Legislature's own site cannot be read.** | `capitol.hawaii.gov` answered robots.txt and the member pages with Cloudflare's block page on 2026-11-12. | If it stops blocking this project's client, move the roster to the Legislature's own pages (Adam's 2026-11-10 order: the legislature first, Open States as the fall back). Never work around the block. |
| **Hawaii has no tribal land to draw.** | Measured 2026-11-12 with `scripts/tribal_areas.py --report Hawaii`: no reservation, trust land or state reservation. Recorded as covered in `data/tribal-government-join.json`. | A new Census vintage that adds land; `validate_tribal_join.py --check` would then fail until it is drawn. |
| **The negative point.** | **THE NEGATIVE POINT IS OPEN WATER AND NEVER MOVES**: the Pacific about 100 km southwest of Oahu (20.7, -158.7). Measured 2026-11-12 against TIGERweb's state layer and every outline in `fleet-outlines.json`. | Nothing: no instance will ever serve it. |
| **No fixed point elsewhere in the fleet sits in Hawaii.** | Measured 2026-11-12 over every coordinate in every other instance's smoke test and worksheet, tested against this state's outline in fleet-outlines.json: none falls in Hawaii. | Nothing: Hawaii has no neighbouring state. |
| **The done-standard scorer knows Hawaii.** | Read 2026-11-12. | DONE in the go-live change: `STATE_COUNTIES`, `ANSWERS` (each level measured or marked open), and `MEASURED_EMPTY` in `scripts/build_eam_status.py`, because Hawaii has no incorporated place and `docs/expected-governments.json` lists no unit for it. Hawaii scores E, A and M, and 10 of the 14 levels (`docs/EAM_STATUS.md`). |
| **There is no `hi/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
