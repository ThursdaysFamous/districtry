# WATCH.md — New Jersey's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| **2031**, when TIGERweb publishes 2030 census blocks | The Census 2020 block populations the compare screen counts people with, the one dataset here that cannot change until then | `nj/data/app/population/` | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set this app's `INSTANCES` row's `total` to its 2030 count and rebuild with `--instance nj`. `--check` forces it: the first legislative map drawn on 2030 blocks fails against 2020 people until this row is done. |
| Weekly (Mon 21:19 UTC) | U.S. House (New Jersey) roster refresh | `.github/workflows/update-nj-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Tue 21:19 UTC) | New Jersey Senate + Assembly roster refresh, from the Legislature's own roster and each member's record in its feed | `.github/workflows/update-nj-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a district carrying more members than it elects, a member with no district, or a field (party, e-mail, district office) going missing from members who carried it. The host states no Crawl-delay and is paced at one request a second, so a run takes about two minutes |
| Weekly (Sun, `update-tiger-tiles.yml`) | The five TIGERweb fabric archives (municipality, three school district tilings, ZIP) | `scripts/mirror_tiger_tiles.py` → PR on change | Review + merge the PR; it moves this app's cache name itself |
| Monthly (1st, 23:09 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/nj-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **The batch 1 go-live** | **New Jersey opens with Pennsylvania, Nevada, Arizona and New Hampshire**, in one change, on Adam's own "merge" (his answer of 2026-11-10, "batch merge"). | See the go-live row below. | — |
| **3 January 2027** | **The 120th Congress is seated.** The congressional map does not change (layer 0 and layer 4 carry the same 12 districts). | Check the weekly congress refresh carries the members elected on 3 November 2026. | — |
| **November 2027** | **Both chambers are on the ballot.** The Senate serves a four-year term from the 2023 election and the General Assembly a two-year term from the 2025 election; on 2026-11-10 the roster listed the 222nd Legislature. | In January 2028, check the weekly legislature refresh carries the 223rd Legislature, with one senator and two members of the General Assembly in every district. | — |

## Re-check plan for each data file the app reads

The two roster jobs and the tile job are in the standing table above. The files below have no
job, because a weekly job on a boundary would almost always find nothing to change.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **Annually**, when TIGERweb rolls its congressional vintage, and on any court order | `congress-districts.json` | The 2022 map is drawn from TIGERweb layer 0, and the builder refuses if layers 0 and 4 stop carrying the same 12 districts before 3 January 2027, and refuses outright on or after 3 January 2029 | 2026-11-10 (built) |
| **Annually**, and on any court order | `nj-legislative-districts.json` | The Apportionment Commission's 2022 plan is in force until the plan drawn after the 2030 census. The builder refuses if a TIGERweb layer's name changes, since TIGERweb renumbers its layers when a vintage rolls, and refuses if layer 1 and layer 2 stop carrying the same 40 districts, since both chambers are elected from them | 2026-11-10 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same county fabric, the outline being that fabric dissolved, so they share one clock. `nj/scripts/build_metro_outline.py --check` tests the outline against its inside and outside anchors, so it would catch a lost county and would not notice a redrawn line | 2026-11-10 (built) |
| **Annually**, and in the same change as any new New Jersey layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-11-11 (written with the instance) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance is dark.** It has no `metros.json` entry and no `layer-concepts.json` column, and `'nj/**'` is blanket-excluded from the Pages deploy, which is what `validate_instance_registration.dark_instances()` reads. | Set up 2026-11-11 on Adam's state-level launch plan. | The batch 1 go-live change: `metros.json` entry and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`); the ZIP search (`zip_search`); the done-standard scorer; the fixed-point audit below; the statewide officials card once its shape lands; and every generated root page. |
| **No county, municipal or board of education official is named.** | Not surveyed source by source in this change. Recorded as gaps `nj-county-officials`, `nj-municipal-officeholders` and `nj-school-board-members`. | Each as its own change, largest first. |
| **The two State Designated Tribal Statistical Areas are not drawn.** New Jersey has no federally recognized tribe or reservation. TIGERweb's AIANNHA service draws two statistical areas in the state, Ramapough and Nanticoke Lenni-Lenape (read 2026-11-11). | They are statistical areas the Census draws for state-recognized tribes, not land a tribal government governs, so a card naming one as a government would claim too much. | A ruling on whether the fleet's tribal mandate covers state-recognized tribes with no land; then, if it does, each nation's council from its own pages. |
| **Voting precincts are not drawn.** | Not surveyed in this change. | A precinct layer as its own change, if a statewide source proves current. |
| **Fixed points elsewhere in the fleet sit in New Jersey.** `ny/scripts/smoke_test.mjs` selects `HUDSON_POINT` (40.72, -74.04), "Hudson River, New Jersey waters", by permalink and asserts the borough card is empty there. | Found 2026-11-11 by reading New York's smoke test; not yet tested against New Jersey's outline. | Audit at go-live: every coordinate pair in every other instance's tests, worksheets and builders tested against `metro-outline.json`, as Indiana's go-live moved a point into Kentucky. A point New Jersey's outline contains must be shown to stay in New York (a permalink does not hand off) or be moved. Pennsylvania opens in the same batch, so its tests and New Jersey's are audited against each other. |
| **The negative point is in the open Atlantic, and no go-live should ever move it.** (39.30, -74.00), about 36 km east of Atlantic City. | Measured 2026-11-10: TIGERweb's state layer names no state there, and no outline in `fleet-outlines.json` contains it. | Nothing short of the fleet serving the ocean. |
| **The done-standard scorer does not know New Jersey.** `scripts/build_eam_status.py` scores the live states; only its population row names New Jersey. | Read 2026-11-11. | At go-live: add New Jersey to the scorer's state tables and measure each answer before claiming it. |
| **There is no `nj/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
