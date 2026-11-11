# WATCH.md — Florida's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| **2031**, when TIGERweb publishes 2030 census blocks | The Census 2020 block populations the compare screen counts people with, the one dataset here that cannot change until then | `fl/data/app/population/` | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set this app's `INSTANCES` row's `total` to its 2030 count and rebuild with `--instance fl`. `--check` forces it: the first legislative map drawn on 2030 blocks fails against 2020 people until this row is done. |
| Weekly (Mon 20:47 UTC) | U.S. House (Florida) roster refresh | `.github/workflows/update-fl-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Wed 20:47 UTC) | Florida Senate + House roster refresh, from each chamber's own member list and member pages | `.github/workflows/update-fl-legislature-roster.yml` → PR on change | Review + merge the PR. A red run is a person's job: a seat carried by two rows, a member page naming another district, a Capitol office whose address is no longer in Tallahassee, or a field (party, the Senate's e-mail addresses, Capitol office, telephone) going missing from members who carried it |
| Weekly (Sun, `update-tiger-tiles.yml`) | The three TIGERweb fabric archives (city, school district, ZIP) | `scripts/mirror_tiger_tiles.py` → PR on change | Review + merge the PR; it moves this app's cache name itself |
| Monthly (1st, 22:53 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/fl-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Dated (one change each, on or after the date)

| When | What | You do | Last done |
|---|---|---|---|
| **The batch 2 go-live** | **Florida opens with Texas, Ohio, California and Washington**, in one change, on Adam's own "merge" (his answer of 2026-11-10, "batch merge"). | The go-live checklist under "Deferred" below. | — |
| **A few weeks after 3 November 2026** | **43 of the 120 House members' contact pages print no Capitol office**, the members elected on 3 November 2026 whose offices are not posted yet (read 2026-11-11). Florida's legislators take office on election, so the cards name them already; the House's office floor in `fl/scripts/build_fl_legislature_roster.py` is 0.6 until the offices are posted. | When a weekly refresh carries the offices, raise the House `capitolOffice` floor back to 0.9 in the same PR. | — |
| **3 January 2027** | **The 120th Congress is seated, and Florida's congressional map changes.** The card draws TIGERweb layer 4 (the 119th Congress, the map the sitting members were elected from in 2024) and the builder refuses on or after this date. Layer 0 is the map the 3 November 2026 election used; 21 of its 28 districts differ from layer 4's (measured 2026-11-11). | Switch `fl/scripts/build_legislative_boundaries.py`'s congress entry to layer 0 and `CD120`, rebuild `congress-districts.json` and its archive, bump the cache name, and check the weekly congress refresh carries the members elected on 3 November 2026. A person's step, because the card then names different people for much of the state. | — |
| **When FL-20 is filled** | **The 20th District is vacant.** The Clerk of the House lists it as vacant (its member resigned on 21 April 2026), and the card says so with the Clerk's reason. | Nothing by hand: the weekly congress refresh drops the vacancy when the Clerk does. Look at that week's PR. | — |
| **When Senate District 39 is filled** | **The Senate's member list lists District 39 as vacant** (read 2026-11-11), and the card says so. | Nothing by hand: the weekly legislature refresh drops the vacancy when the Senate names a senator. Look at that week's PR. | — |

## Re-check plan for each data file the app reads

The two roster jobs and the tile job are in the standing table above. The files below have no
job, because a weekly job on a boundary would almost always find nothing to change.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **3 January 2027** (above), and on any court order | `congress-districts.json` | The 119th Congress's map is drawn from TIGERweb layer 4, and the builder refuses on or after 3 January 2027, when the members elected from the new map take office | 2026-11-11 (built) |
| **Annually**, and on any court order | `fl-senate-districts.json`, `fl-house-districts.json` | TIGERweb's 2026 state legislative districts (layers 1 and 2). The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage rolls | 2026-11-11 (built) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both come from the same county fabric, the outline being that fabric dissolved, so they share one clock. `fl/scripts/build_metro_outline.py --check` tests the outline against its 67 inside anchors (one per county) and 14 outside anchors, so it would catch a lost county and would not notice a redrawn line | 2026-11-11 (built) |
| **Annually**, and in the same change as any new Florida layer or roster | `coverage-gaps.json` | Emitted from the guidebook's gaps block, and `build_coverage_gaps.py --check` compares the two on every pull request. The yearly clock is for the RECORD: each gap rests on a measurement with a date | 2026-11-11 (written with the instance) |
| **Before each election**, and when an officer changes | `statewide-officials.json` | Built from `data/source/statewide-officials.source.json`, each officer read from their own office's page. The weekly name check in the root goes red on a handover | 2026-11-11 (built) |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **The instance is dark until its go-live change.** It has no `metros.json` entry and no `layer-concepts.json` column, and `'fl/**'` is blanket-excluded from the Pages deploy. | Set up 2026-11-11 on Adam's state-level launch plan, batch 2. | The go-live change: `metros.json` entry (with the worksheet's own `bbox`) and `--sync-fleet`; the deploy's narrow exclude set and presence loop; `AREAS` and `SOURCES`; the `layer-concepts.json` column; `build_legislator_pages.INSTANCES` (`congress.html`, `state-legislature.html`), and the two roster jobs regenerating the pages that read their rosters; the done-standard scorer and `docs/expected-governments.json`; the tribal-coverage record in `data/tribal-government-join.json`; the fixed-point audit below; the traffic page's tables; and every generated root page. |
| **No county, city or school board official is named.** | Not surveyed source by source in this change. Recorded as gaps `fl-county-officials`, `fl-municipal-officeholders` and `fl-school-board-members`. Florida has 67 boards of county commissioners, 411 cities, towns and villages and 67 school boards. | Each as its own change, largest first. |
| **The House prints no e-mail address for its members, and the Commissioner of Agriculture is not named.** | Read 2026-11-11: each House member's contact page names a Capitol office and telephone and links a contact form rather than an address. The Department of Agriculture's robots.txt refuses this project's client, and the Governor and Cabinet's site names the commissioner only inside its script data. | A House page that prints an address, or a government page the Commissioner's name can be read from, each as its own change. Never an address or a name guessed from elsewhere. |
| **Voting precincts are not drawn.** | Not surveyed in this change. | A precinct layer as its own change, if a statewide source proves current. |
| **The land of Florida's tribal nations is not drawn.** | Measured 2026-11-11 with `scripts/tribal_areas.py --report Florida`: the Census keeps 7 reservations in the state (the Miccosukee Reservation and six Seminole reservations, among them Big Cypress, Brighton and Hollywood) and 4 off-reservation trust lands, one of them a 0.007 km² parcel of the Poarch Band of Creek Indians, whose government is in Alabama. | Record Florida as not yet covered in `data/tribal-government-join.json` at go-live; then the fleet's tribal-government reader (`scripts/build_tribal_areas.py`) as its own change, with each nation's council named from its own pages. |
| **The negative point is in the Gulf and never moves.** It is open water about 200 km west of Sarasota (27.0, -85.5). | Measured 2026-11-11: TIGERweb's state layer names no state there and its ZCTA layer no ZIP code (controls: the State Capitol returns Florida and 32399), and no outline in `fleet-outlines.json` contains it. | Nothing: no instance will ever serve it. |
| **Florida's go-live changes what Georgia's app does at points near the line.** | Georgia is the one live app bordering Florida (Alabama is not served). Tested 2026-11-11 by this instance's smoke check 1a2: a click on Georgia's Capitol from Florida opens Georgia's app. What Georgia's app does at a point inside Florida is not tested until go-live, because `fleet-outlines.json` does not carry Florida while it is dark. | Re-run the fixed-point audit at go-live: every coordinate pair in every live instance's smoke test, worksheet and outline builder, tested against `metro-outline.json`. A test point of a neighbour that falls inside Florida moves in the go-live change, the Kentucky lesson. |
| **No ZIP code is shared with a live neighbour.** | `scripts/build_zip_index.mjs` keeps a ZIP code that crosses a state line with a live app over a dark one; measured 2026-11-11 it found no ZIP code drawn by both Florida and Georgia, and left out six Florida ZIP codes whose best spot is under 75 m from an edge (32013, 32723, 32959, 33022, 33550, 34487), which a search answers as before. | Nothing by hand: the go-live change regenerates `fleet-zips.json`. |
| **The done-standard scorer does not know Florida.** | Read 2026-11-11. | The go-live change: `STATE_COUNTIES` (67), `ANSWERS`, and the state's units in `docs/expected-governments.json`. |
| **There is no `fl/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
