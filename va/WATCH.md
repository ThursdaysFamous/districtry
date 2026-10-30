# WATCH.md — Virginia's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

The plan this instance is built to is the Virginia plan of 2026-10-21 (claude.ai artifact
R4apNobGbZaZRpCDiWRxVc), with Adam's answers of 2026-10-22: all three choices as
recommended. It is built in five changes; this file was written with the first.

1. **Hidden: the statewide layers** (this change). Congress, both chambers with their
   members, counties and cities, towns, school divisions, ZIP codes, the census's county
   subdivisions, and the outline of Virginia.
2. **Hidden: local districts and names.** Supervisor, council and school board districts and
   all 2,531 precincts from the Department of Elections' per-locality files, with names from
   the state's election results, each card saying which election the name comes from.
3. **Go live**, on Adam's word only.
4. **Soil and water conservation districts and tribal land**, each a change of its own.
5. **County subdivisions from the Department's lines** where the census names match.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| Weekly (Mon 19:07 UTC) | U.S. House (Virginia) roster refresh | `.github/workflows/update-va-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Tue 19:07 UTC) | Senate of Virginia + House of Delegates roster refresh, from each chamber's own member list and member pages | `.github/workflows/update-va-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a seat with no record or two, a list's card shape changing, or a field (party, Capitol office, e-mail) going missing from members who carried it |
| Monthly (1st, 21:43 UTC) | Source freshness for every dataset this instance depends on, including the names of the TIGERweb layers the congressional and chamber maps are drawn from | `.github/workflows/va-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **3 November 2026**, and again when the winners take office | **The general election.** All 11 House seats are on the ballot; neither chamber of the General Assembly is (the Senate is next elected in 2027, the House of Delegates in 2027). City councils, school boards and town councils elected that day take office on 1 January 2027, and the House members on 3 January. The congressional map does not change: the Supreme Court of Virginia blocked the 2026 redraw on 8 May 2026, so the members seated in January are elected from the 2021 map. | After 3 January 2027, check that the weekly congress refresh carries the new members. The plan's second change is to hold November's local winners and switch them on 1 January 2027, not on the day results appear. | — |
| **3 January 2027** | **`check_same_map` stops applying.** Until that date the builder draws layer 0 (the 120th Congress) only while it matches layer 4 (the 119th) district for district, because the sitting members were elected from layer 4's map. | Nothing by hand. | — |
| **1 December 2028**, and **3 January 2029** | **The congressional map must be re-read.** `va/scripts/build_legislative_boundaries.py` refuses to run on or after 3 January 2029, and `va/scripts/validate_sources.py` check 5 warns from 1 December 2028, so a person reads which map the 2028 election used before anything is drawn. Another attempt to redraw before 2028 is possible. | Read which map the 2028 election used; rebuild `congress-districts.json` from the TIGERweb layer that carries it with the same IoU comparison; change the `us-house` entry's dates in the builder and in `validate_sources.py`. | — |

## Re-check plan for each data file the app reads

The two roster jobs are in the standing table above. The files below have no job, because a
weekly job on a boundary would almost always find nothing to change. Each row says what moves the
file and when to look. A builder's `--check` proves a file matches what it was built from; it
never proves the source is still current.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **Annually** when TIGERweb rolls its congressional vintage, on any court order, and on the dated rows above | `congress-districts.json` | The 2021 map is drawn from TIGERweb layer 0, and the builder refuses if that layer or layer 4 is renamed, because TIGERweb renumbers its layers when a vintage rolls | 2026-10-29 (built from the 2021 map) |
| **Annually**, and on any court order | `va-senate-districts.json`, `va-house-districts.json` | The 2021 plans are in force until the plans drawn after the 2030 census. Both come from TIGERweb's 2026 state legislative layers, and the builder refuses if either is renamed, which is how a rolled vintage shows itself | 2026-10-29 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same 133-county-and-city TIGERweb fabric, and the outline is that fabric dissolved, so they share one clock. `va/scripts/build_metro_outline.py --check` tests the shipped ring against one inside anchor per county and city and outside anchors in every neighbouring state, so it would catch a lost county and would not notice a redrawn line | 2026-10-29 (built) |
| **Weekly**, by `update-tiger-tiles.yml` | `tiles/county-subdivision.pmtiles`, `tiles/municipality.pmtiles`, `tiles/school-district-unified.pmtiles`, `tiles/school-district-elementary.pmtiles`, `tiles/zip-code.pmtiles` | Mirrored from TIGERweb by `scripts/mirror_tiger_tiles.py` and recorded in `tiger-mirror.json`; the weekly job refetches a set only when its attribute hash or query moves, and opens a PR | 2026-10-29 (mirrored) |
| **Annually**, and in the same change as any new Virginia layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request, so the file cannot drift from the record. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-10-29 (written with the instance) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance is DARK and two things hold it that way.** It carries no `metros.json` entry, and `'va/**'` is blanket-excluded from the Pages deploy. `scripts/build_legislator_pages.py` is deliberately NOT registered for `va`, so there is no `va/congress.html` or `va/state-legislature.html` yet. **THE BLANKET `<tag>/**` FORM IS LOAD-BEARING**: it is what `validate_instance_registration.dark_instances()` reads. Virginia goes live only on Adam's word. | Set up 2026-10-29. | **Go-live, and all of it in the same change**: add `va` to `metros.json` (with `--sync-fleet` for the `metro_explorers` tables); replace the blanket `'va/**'` exclude with the siblings' narrow set (`va/data/state va/data/source va/scripts`) and add `va` to the deploy's presence loop; add `va` to `AREAS` in `scripts/build_coverage_map.py` and to `SOURCES` in `scripts/build_fleet_outlines.py`; give `va` its column in the root `layer-concepts.json` (every layer already draws in its concept's colours and width); add `va` to `build_legislator_pages.INSTANCES` and regenerate the sub-pages (Virginia names BOTH chambers, so it owes a state-legislature page, and District 20 of the House is vacant today, so check the page says so rather than dropping it); add the page steps to the two roster workflows; opt into ZIP search (below); move the fixed point below; then re-run `build_sitemap.py`, `build_llms_txt.py`, `build_question_forms.py`, `build_landing_page.py`, `build_privacy_page.py` and the README fleet row. |
| **One fixed point elsewhere in the fleet is inside Virginia, and it must change at go-live.** North Carolina's smoke test (`nc/scripts/smoke_test.mjs`) clicks Danville, Virginia (36.586, -79.395) as its UNCOVERED case and expects it to stay in North Carolina. While Virginia is dark, `fleet-outlines.json` does not carry it and the case holds; the day it does, the click opens `/va/`. | Audited 2026-10-29: every coordinate pair in the tree's `.mjs`, `.js`, `.py` and worksheet files outside `va/` tested against `va/data/app/metro-outline.json`. Four fall inside Virginia: North Carolina's Danville case; Tennessee's outline builder's OUTSIDE anchor at Abingdon, Virginia, which stays outside Tennessee; and two envelope corners in `scripts/mirror_tiger_tiles.py` and `tn/scripts/validate_sources.py`, which are not points anyone selects. | At go-live, make North Carolina's case expect `/va/` (or give it a new uncovered point outside every outline, as Kentucky's go-live did for Indiana), and re-run the audit: a state that lands in between can move a point into Virginia. |
| **The negative point is in the Atlantic, on purpose.** Every land neighbour of Virginia is either live already (Kentucky, Tennessee, North Carolina) or a state the fleet plans to build (West Virginia, Maryland), so a point on a neighbour's land would have to move when that neighbour goes live. The point (37.0, -75.3) is 44 km from Virginia's outline and in no outline in `fleet-outlines.json`. | Measured 2026-10-29. | Nothing, unless an instance's outline ever reaches into the ocean there. |
| **ZIP code search is not opted in.** The search that shows a typed ZIP code whole is built from each app's committed ZIP archive by `scripts/build_zip_index.mjs`, and the root `fleet-zips.json` lists every app's codes; a dark instance's codes would take neighbours' ZIP codes into an app nobody can open. Until then a typed ZIP code goes through the geocoder and is never selected for the reader. | Decided 2026-10-29, the Missouri and Louisiana pattern. | At go-live: add the worksheet's `zip_search` key (the siblings' `zip-code` / `ZCTA5` / `metro-outline.json` entry) and run `node scripts/build_zip_index.mjs`. |
| **One House of Delegates seat is vacant on the House's own list.** District 20, on 2026-10-29. The card says the seat is vacant and names nobody. | Read 2026-10-29. Whether a special election is set is NOT measured. | Nothing by hand: the weekly refresh names a successor the day the House lists one. Before go-live, re-read the seat. |
| **Local officials are not named and their districts are not drawn.** Boards of supervisors, city councils, school boards and town councils. | Recorded as gaps `va-county-board-members`, `va-school-board-members`, `va-municipal-officeholders` and `va-voting-precincts`. The plan measured the sources on 2026-10-21; the Department of Elections' per-locality files were found 2026-10-27 and not yet downloaded. | The plan's second change, which also measures the Department's statewide layer against five counties' own maps before it merges, checks by hand the 19 supervisor districts that show winners in both 2023 and 2025, and fixes the three counties (Carroll, Charles City, Isle of Wight) whose district names in the file are wrong. |
| **The Magisterial District card draws the census's older copy.** Against the Department's current lines, TIGER's county subdivisions agree to within 1% of the area in only 32 of 91 counties. The card says what a magisterial district is and does not say who represents the point. | The plan, 2026-10-21. Recorded as gap `va-magisterial-district-lines`. | The plan's fifth change (Adam's choice 3): the Department's lines where the census names match (about 71 of 94 counties), the census copy elsewhere. |
| **The letter to the Department of Elections is out.** Two asks in one letter: may we use its district and precinct files with credit, and does it keep, or could it publish, a record of members appointed to fill vacancies. Sent through the Letters thread on 2026-10-27; follow-up due about 2026-11-17. The terms are treated as unstated until it answers. | — | The Letters thread owns it. The build does not wait on it. |
| **No layer sends a reader's selected point to a server.** The five census layers draw and answer from same-origin tile archives, and the three USGS point layers and the chamber and county files are downloaded whole. | `scripts/probe_point_transmission.mjs`, recorded in `point-transmission.json`. | Re-run the probe in any change that adds a live layer. |
| **Tribal land is drawn in the fourth change, not this one.** The Census's current tribal land layers hold the Pamunkey Reservation (6.39 km²), the Mattaponi Reservation (0.31 km²) and the Rappahannock Tribe's trust land (0.56 km²). | The plan, 2026-10-21. | The plan's fourth change, with leaders from the federal tribal leaders directory and, for the Mattaponi, the nation's own page or the state's list. |
| **Judges are not drawn, because none are elected by district.** The General Assembly elects Virginia's judges. | The plan, 2026-10-21. | Nothing; the done standard records the level as not applying. |
| **Crawling rules.** `apps.senate.virginia.gov` answers 404 for robots.txt (allow all); `house.vga.virginia.gov` serves a 99-byte file holding only a comment, which binds nobody; `tigerweb.geo.census.gov` serves an HTML page at that path (allow all); `carto.nationalmap.gov` answers 403, which RFC 9309 files with a 404 (allow all). None states a Crawl-delay. | Read 2026-10-29 through `scripts/robots_policy.py`. | Re-read before each builder's first fetch; every builder does so with the client its fetches send. |
| **There is no `va/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
