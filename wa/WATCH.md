# WATCH.md — Washington's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| **2031**, when TIGERweb publishes 2030 census blocks | The Census 2020 block populations the compare screen counts people with, the one dataset here that cannot change until then | `wa/data/app/population/` | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set this app's `INSTANCES` row's `total` to its 2030 count and rebuild with `--instance wa`. `--check` forces it: the first map drawn on 2030 blocks fails against 2020 people until this row is done. |
| Weekly (Tue 21:23 UTC) | U.S. House (Washington) roster refresh | `.github/workflows/update-wa-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Thu 21:23 UTC) | Washington Senate + House roster refresh, from the Legislature's own member list and member pages at leg.wa.gov | `.github/workflows/update-wa-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a seat carried by two rows, a district listing more members than it elects, a member page naming another district, or a field (party, Olympia office, telephone) going missing from members who carried it |
| Weekly (Sun, `update-tiger-tiles.yml`) | The three TIGERweb fabric archives (city and town, school district, ZIP) | `scripts/mirror_tiger_tiles.py` → PR on change | Review + merge the PR; it moves this app's cache name itself |
| Monthly (1st, 23:37 UTC) | Source freshness for every dataset this instance depends on, including which map each congressional layer holds | `.github/workflows/wa-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **The batch 2 go-live** | **Washington opens with Texas, Florida, Ohio and California**, in one change, on Adam's own "merge" (his answer of 2026-11-10, "batch merge"). | The go-live checklist under "Deferred" below. | — |
| **January 2027** | **The Washington Legislature members elected on 3 November 2026 take office** when the session convenes. Until then the Legislature's member list names the sitting members, and the cards name them. | Nothing by hand: the weekly legislature refresh carries the new members when leg.wa.gov posts them. Look at the first January PR, which will change many rows at once. | — |
| **3 January 2027** | **The 120th Congress is seated, and Washington's congressional map does NOT change.** The card draws TIGERweb layer 0 (the 120th Congress), and its 10 districts are the same as layer 4's (the 119th Congress): Washington used its 2022 map in 2024 and again in 2026. `wa/scripts/build_legislative_boundaries.py` compares the two on every build and refuses to draw layer 0 before this date if they differ. | Check the weekly congress refresh carries the members elected on 3 November 2026. No boundary rebuild. | — |
| **3 January 2029** | **The builder refuses to draw the congressional map on or after this date**, so a person reads which map the 2028 election used before the cards go on naming its members. `wa/scripts/validate_sources.py` starts warning from 1 December 2028. | Read the map TIGERweb's layer 0 holds then, rebuild `congress-districts.json` and its archive if it moved, set the builder's next date and bump the cache name. | — |
| **When House District 16's second seat is listed** | **The Legislature's member list names one representative for House District 16** (read 2026-11-11), so 97 of the 98 House seats are named and the card names the one member listed. | Nothing by hand: the weekly legislature refresh adds the second member when leg.wa.gov lists one. Look at that week's PR. | — |

## Re-check plan for each data file the app reads

The two roster jobs and the tile job are in the standing table above. The files below have no
job, because a weekly job on a boundary would almost always find nothing to change.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **3 January 2029** (above), and on any court order | `congress-districts.json` | TIGERweb layer 0, the 2022 map, right for the members serving until 3 January 2029. The builder refuses on that date | 2026-11-11 (built) |
| **Annually**, and on any court order or Redistricting Commission plan | `wa-legislative-districts.json` | One map serves both chambers: each of the 49 districts elects one senator and two representatives. It is TIGERweb's 2026 state legislative districts, upper chamber (layer 1), and the builder refuses unless the lower-chamber layer (layer 2) draws the same 49 districts, and refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage rolls | 2026-11-11 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same county fabric, the outline being that fabric dissolved, so they share one clock. `wa/scripts/build_metro_outline.py --check` tests the outline against its 39 inside anchors (one per county) and 15 outside anchors, so it would catch a lost county and would not notice a redrawn line | 2026-11-11 (built) |
| **Annually**, and in the same change as any new Washington layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-11-11 (written with the instance) |
| **Before each election**, and when an officer changes | `statewide-officials.json` | Built from `data/source/statewide-officials.source.json`, each of the nine officers Washington elects statewide read from their own office's page. The weekly name check in the root goes red on a handover | 2026-11-11 (built) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance is dark until its go-live change.** It has no `metros.json` entry and no `layer-concepts.json` column, and `'wa/**'` is blanket-excluded from the Pages deploy. | Set up 2026-11-11 on Adam's state-level launch plan, batch 2. | The go-live change: `metros.json` entry (with the worksheet's own `bbox`) and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`), whose one-map wording says each district elects one senator and two representatives, and the two roster jobs regenerating the pages that read their rosters; the done-standard scorer and `docs/expected-governments.json`; the tribal-coverage record in `data/tribal-government-join.json`; the fixed-point audit below; the traffic page's tables; and every generated root page. |
| **No live app's fixed point should fall inside Washington, and the audit is re-run at go-live.** Washington's neighbours, Oregon and Idaho, have no app, so no sibling chose a point here for want of coverage. | To be measured at the go-live change by testing every coordinate pair in every live instance's smoke test, worksheet and outline builder against `wa/data/app/metro-outline.json`, the audit Ohio's change ran. | The go-live change: move or re-assert any point it finds. |
| **No county, city, town or school board official is named.** | Not surveyed source by source in this change. Recorded as gaps `wa-county-officials`, `wa-municipal-officeholders` and `wa-school-board-members`. Washington has 39 counties, 281 incorporated places in the Census's place layer (212 cities and 69 towns, about 2.6% of the state's land) and 295 school districts in its unified layer, with none on the elementary or secondary layers (all read 2026-11-11). | Each as its own change, largest first. |
| **No e-mail address is printed for a legislator.** | Read 2026-11-11: each member's page at leg.wa.gov names an Olympia office and telephone and offers a contact form. | A member page that prints an address, as its own change. Never an address guessed from a pattern. |
| **Voting precincts are not drawn.** | Not surveyed in this change. | A precinct layer as its own change, if a statewide source proves current. |
| **The land of Washington's tribal nations is not drawn.** | Measured 2026-11-11 with `scripts/tribal_areas.py --report Washington` (control: the reader resolved Washington as state code 53): the Census keeps 28 reservations and 22 off-reservation trust lands in the state, and no state reservation. | The fleet's tribal-government reader (`scripts/build_tribal_areas.py`) as its own change, with each nation's council named from its own pages where they publish one, and the go-live change recording Washington in `data/tribal-government-join.json` as not yet covered. |
| **The negative point is in Victoria, British Columbia, and never moves.** (48.4284, -123.3656), across the Strait of Juan de Fuca. | Measured 2026-11-11: TIGERweb's state layer names no state there (control: the Legislative Building in Olympia returns Washington), and no outline in `fleet-outlines.json` contains it. | Nothing: no instance will ever serve Canada. |
| **Four ZIP codes are not listed for the ZIP search.** | Measured 2026-11-11 by `scripts/build_zip_index.mjs`: the archive draws 606 ZIP codes and the index keeps 602. The other four have no spot 75 m from every edge (98154, 98164 and 98174 at 46 m, 98559 at 64 m), and a search answers those as an address, as before. No ZIP code is shared with a live neighbour. | Nothing by hand: the go-live change regenerates `fleet-zips.json`. |
| **The compare screen's people are not the plan's own counts.** On the raw Census blocks congressional District 5 is 0.564% over its ideal and legislative District 16 2.336% over. The likeliest reason, inferred and not read from the law here (the Legislature's code site refuses every automated reader), is that Washington's redistricting commission counts incarcerated people at their last home address rather than at the prison, as New York's and Virginia's do. | Measured 2026-11-11 by `scripts/build_block_population.py --check`, whose tolerances for this app are those figures rounded up. | Nothing: the tolerance catches a map swapped for another and does not certify the plan. |
| **The done-standard scorer does not score Washington yet.** Its answers are in `scripts/build_eam_status.py`'s `ANSWERS` and its population files in `PREFIX_CLASSES`, written with the instance. | Read 2026-11-11: the scorer skips a dark instance. | The go-live change: `STATE_COUNTIES` (39) and the state's units in `docs/expected-governments.json`. |
| **There is no `wa/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
