# WATCH.md — West Virginia's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| Weekly (Mon 19:53 UTC) | U.S. House (West Virginia) roster refresh | `.github/workflows/update-wv-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Tue 19:53 UTC) | West Virginia Senate + House of Delegates roster refresh, from the Legislature's two roster pages | `.github/workflows/update-wv-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a Senate district with other than two members, a member whose office is not in the Capitol, or a field (party, Capitol office, e-mail) going missing from members who carried it |
| Weekly (Wed 19:53 UTC) | Every county's commission and elected officers, from the Secretary of State's directory of county officials | `.github/workflows/update-wv-county-officials.yml` → PR on change | Review + merge the PR. The builder reads the newest year that lists all 55 counties, so a new year's directory is read the week it is complete. A red run is a county whose page no longer matches the shape the builder expects, or a commission with the wrong number of seats |
| Monthly (1st, 21:43 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/wv-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **3 November 2026**, and again when the winners take office | **The general election.** All 100 House of Delegates seats, one senator from each of the 17 Senate districts, both U.S. House seats and one commissioner in most counties are on the ballot. By the plan's research, the delegates and senators take office on 1 December 2026, the commissioners on 1 January 2027 and the members of Congress on 3 January 2027. The congressional map does not change (the 2021 map is the 120th Congress's too). | Check that the weekly legislature, congress and county refreshes carry the new members once each source lists them. The county directory is published by year, so the 2027 directory may not list all 55 counties until well into 2027; until it does the builder keeps reading 2025, and the card says which year it read. | — |
| **On or after 1 January 2027** | **Earliest launch** (Adam's answer of 2026-10-29: build now, publish on or after 1 January 2027). | The go-live change, on Adam's own "merge" only — see the go-live row below. | — |
| **1 July 2026, and every even year** | **School board members change.** County boards of education take office on 1 July of even years, so the 2025 directory's board list is out of date. | Name the boards from the May 2026 primary's results, or the 2027 directory once it lists them, as its own change (gap `wv-school-board-members`). | — |

## Re-check plan for each data file the app reads

The three roster jobs are in the standing table above. The files below have no job, because a
weekly job on a boundary would almost always find nothing to change. Each row says what moves the
file and when to look. A builder's `--check` proves a file matches what it was built from; it
never proves the source is still current.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **Annually**, when TIGERweb rolls its congressional vintage, and on any court order | `congress-districts.json` | The 2021 map is drawn from TIGERweb layer 4, and the builder refuses if layers 4 and 0 stop carrying the same two districts for West Virginia, because a redraw or a renumbered layer would show there first | 2026-10-29 (built) |
| **Annually**, and on any court order | `wv-senate-districts.json`, `wv-house-districts.json` | The 2021 plans are in force until the plans drawn after the 2030 census. The builder refuses if a plan file's district set or feature count changes, and reads the state GIS centre's map as a second witness on every build | 2026-10-29 (built) |
| **Annually**, and when a county redraws | `wv-magisterial-districts.json` | Counties may redraw magisterial districts after a census (W. Va. Code 7-2-2), and since 2022 each county sends its current maps to the Secretary of State, which is why the state's layer is called "Magisterial 2026". The yearly look is for a newer layer name or a changed district count | 2026-10-29 (built, 195 districts) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same 55-county TIGERweb fabric, the outline being that fabric dissolved, so they share one clock. `wv/scripts/build_metro_outline.py --check` tests the outline against its 55 inside anchors and 14 outside anchors in the five neighbouring states, so it would catch a lost county and would not notice a redrawn line | 2026-10-29 (built) |
| **Annually**, and in the same change as any new West Virginia layer or roster | `coverage-gaps.json` | This file is emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request, so the file cannot drift from the record. The yearly clock is for the RECORD: each gap rests on a measurement with a date, and a publisher that starts publishing moves that finding with nothing to detect it | 2026-10-29 (written with the instance) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance is dark.** It has no `metros.json` entry and no `layer-concepts.json` column, and `'wv/**'` is blanket-excluded from the Pages deploy, which is what `validate_instance_registration.dark_instances()` reads. | Set up 2026-10-29 on Adam's "Give the coordinator VA, GA and WV to start building". | The go-live change, on or after 1 January 2027 and on Adam's own "merge": `metros.json` entry and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`); the county-pages adapter and the `NOT_COUNTY_BOARDS` entry retired; the ZIP search (`zip_search`); the done-standard scorer; the fixed-point audit below; and every generated root page. |
| **Three layers send a reader's selected point to the Census.** `municipality`, `school-district-unified` and `zip-code` are live TIGERweb layers, so a first click asks the Census about the point. | Read from the code 2026-10-29: each uses `tigerStatewideLoader`, whose point query is the `.atPoint` hook `point-transmission.json` counts. | Mirror the three into tile archives with `scripts/mirror_tiger_tiles.py` before go-live, as Missouri did, so no layer sends the point. |
| **The magisterial districts ship as one 3.9 MB file** (1.08 MB gzipped), read whole on the layer's first toggle. | Measured 2026-10-29. The House of Delegates file is 2.4 MB (0.68 MB gzipped). | A tile archive for each polygon layer the app ships (`scripts/build_vector_tiles.py`), as its own change before go-live. |
| **No fixed point elsewhere in the fleet is inside West Virginia.** | Audited 2026-10-29: every coordinate pair in every other instance's tests, worksheets and builders, and the root's, tested against `metro-outline.json`: none inside. No live instance's centre is in West Virginia's box, and West Virginia's centre is in no live instance's box. | Re-run the audit at go-live, because Virginia and others are being built at the same time, as Indiana's go-live moved a point into Kentucky. |
| **The negative point is in Maryland and must move when Maryland goes live.** West Virginia borders five states and the fleet serves one (Kentucky). The point (39.55, -79.25, Garrett County, Maryland, about 20 km east of the line) is outside every outline today. West Virginia has no open water on its border to use instead. | Measured 2026-10-29 against `fleet-outlines.json` and TIGERweb. | When Maryland goes live, move the point into the next neighbour nobody serves, with the same controls, in the change that publishes Maryland. |
| **School board members are not named.** The Secretary of State's 2025 directory lists each county's board of education, but board members take office on 1 July of even years, so the 2025 list does not show the members seated on 1 July 2026. | Read 2026-10-29. Recorded as gap `wv-school-board-members`. | Name each board from the May 2026 primary's certified results (school board races are nonpartisan and decided in May), as its own change. |
| **City and town officials and city wards are not named or drawn.** West Virginia has 229 incorporated places (78 cities, 144 towns, 6 villages and the Corporation of Ranson), covering about 1.9% of the state's land. Adam's answer of 2026-10-29: launch naming every council member, and ask the four largest cities for ward files by letter. | Letters for Charleston, Huntington, Parkersburg and Wheeling went out 2026-10-21 (`docs/ASK_DRAFTS.md`); Charleston passed its letter to the City Clerk; follow-ups to the other three about 2026-11-11. Recorded as gaps `wv-municipal-officeholders` and `wv-city-wards`. | Each city's council named from its own pages, largest first, as its own change; wards drawn as each city's file arrives. |
| **Voting precincts are not drawn.** Adam's answer of 2026-10-29: precincts only in the 29 counties whose current maps are confirmed. | The plan's research found 29 counties whose current precinct maps were confirmed. Recorded as gap `wv-voting-precincts`. | A precinct layer for those 29 counties as its own change, hidden in the other 26. |
| **The courts and conservation district supervisors are not drawn or named.** | Not surveyed source by source in this change. The West Virginia Conservation Agency's directory prints supervisors' home addresses, which are never published; its `/directory/reports/` path is disallowed by its robots.txt. | Each as its own change, if Adam wants it. |
| **The state's election map service holds a layer of individual voter locations** (Applications/WV_Election on `services.wvgis.wvu.edu`). It is never read, by any builder, probe or agent. | Recorded 2026-10-29. Only the Boundaries/WV_Election_Layers folder is read, for the magisterial districts and as a witness for the two chambers. | Nothing. |
| **Crawling rules.** `www.wvlegislature.gov` and `apps.sos.wv.gov` disallow nothing the builders read; `sos.wv.gov` disallows `/search?`, which is never read. | Read 2026-10-29 through `scripts/robots_policy.py`. | Re-read before each builder's first fetch; every builder does so with the client its fetches send. |
| **There is no `wv/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
