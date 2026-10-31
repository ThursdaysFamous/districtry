# districtry Virginia — the record of the launch

> **WENT LIVE on Adam's word of 2026-10-30, in the change that follows six hidden ones**, which
> opened Virginia before the 3 November 2026 election rather than in January 2027 as the plan
> first had it. The hidden changes: the first build (#1812: the national tier, both chambers named
> from each chamber's own pages, counties and cities, towns, school divisions, ZIP codes and the
> outline of Virginia); every supervisor, council and school board district and all 2,531
> precincts from the Department of Elections, with the members named from the state's election
> results (#1819); every town's council and mayor, and hand reads of seats the results cannot
> settle (#1823); the soil and water conservation districts and their elected directors (#1826);
> tribal land and the Pamunkey's and the Mattaponi's councils (#1827); the magisterial districts
> drawn from the Department's lines where the census names match (#1829); and the Rappahannock
> Tribe's Chief and Assistant Chief from the Secretary of the Commonwealth's list (#1836). Live at
> districtry.com/va/ with sixteen layers.
>
> **THIS FILE WAS WRITTEN AT GO-LIVE, NOT BEFORE THE BUILD**, the way `docs/MO_EXPANSION_PLAN.md`
> and `docs/LA_EXPANSION_PLAN.md` were and for the same reason: the plan is the claude.ai artifact
> R4apNobGbZaZRpCDiWRxVc of 2026-10-21, with Adam's answers of 2026-10-22, so a file here calling
> itself the plan would be a reconstruction. The shipped instance — `va/metro-worksheet.json`,
> `va/CLAUDE.md`, `va/WATCH.md` and the guidebook's Virginia gap records — remains the record of
> what IS, and where this file and those disagree, those win.

## What ships

| Layer | Count | Ships as | Who it names |
|---|---|---|---|
| County or City | 133 (95 counties and 38 independent cities) | pre-built | a board or council elected at large, the soil and water conservation directors, and whether the school board is appointed |
| U.S. House | 11 | pre-built, the 2021 map | the representative |
| Virginia Senate | 40 | pre-built | the senator |
| House of Delegates | 100 | pre-built | the delegate (District 20 vacant) |
| Supervisor or Council District | 597 in 106 counties and cities | pre-built, unions of precincts | the district's members, from the election that names them; a seat the results cannot settle says why (gap `va-county-board-members`) |
| School Board District | 545 in 98 counties and cities | pre-built, unions of precincts | the district's members, the same way (gap `va-school-board-members`) |
| Voting Precinct | 2,531 | pre-built | — |
| Magisterial District | 552 | pre-built | — (drawn from the Department's lines in 72 counties; gap `va-magisterial-district-lines`) |
| City or Town | 227 (38 cities and 189 towns) | tile files | a town's mayor and council where the results settle them (gap `va-municipal-officeholders`) |
| School Division (Unified, Elementary) | 135 and 1 | tile files | — (the board is named on the cards above) |
| ZIP Code | the codes that overlap Virginia; hidden outside the state | tile files | — |
| Tribal Government | 3 pieces of land | pre-built | the Pamunkey's and the Mattaponi's councils, the Rappahannock's Chief and Assistant Chief (gap `va-tribal-government`) |
| Police Station, Fire & EMS Station, Post Office | — | downloaded whole | — (a station is a facility) |

Counts are the ones `va/CLAUDE.md` and `va/WATCH.md` record with their measurement dates.

## What Virginia taught that a copy of a sibling would have got wrong

**Virginia's 38 independent cities belong to no county.** A city's council does what a board of
supervisors does in a county, and the Census files each city as a county, as its own county
subdivision and as an incorporated place. So the County layer is "County or City", each city has a
page of its own beside the counties under `va/local-government/`, and the done standard scores a
city once, under the level for local governments above 25,000 people, and not again as a county,
the way Missouri's City of St. Louis is scored.

**The districts every local body is elected from are unions of the state's precincts.** The
Department of Elections publishes every precinct statewide with the districts it votes in, so the
local districts were drawn from one source rather than county by county, and measured against five
localities' own maps they agree on 99.93% to 99.97% of the ground.

**The names come from the state's election results, and the results do not say who fills a
vacancy.** The Department answered on 2026-10-30 that it keeps no list of appointees, so a seat a
special election filled without saying which seat, or one a body appointed, is left unnamed and
the card says why.

**No judge is elected by the voters.** The General Assembly elects every judge, so no court layer
is drawn and the done standard records that level as not applying.

## What the go-live change did

It narrowed the deploy's blanket `va/**` exclude to the build inputs the siblings exclude, added
Virginia to the deploy's check that every live folder was published, and added `va` to
`metros.json`, which puts Virginia on the front door, the coverage map, the 404 page, the feedback,
privacy and about pages, `llms.txt`, the sitemap, the fleet hand-off outlines and every sibling
app's list of places. It added Virginia's column to `layer-concepts.json`. It generated
`va/congress.html` and `va/state-legislature.html`, and `va/local-government.html` with a page for
each county and each independent city under `va/local-government/`, which the weekly local
officials job regenerates. It built the ZIP code search. It scored Virginia on the done standard:
13 of the 14 levels are answered or do not apply, and the one open is the governing body of every
local government above 25,000 people, where Hampton's, Roanoke's and Staunton's councils and
Leesburg's are not named yet.

**One fixed point elsewhere in the fleet was inside Virginia**, as `va/WATCH.md` recorded on the
day the instance arrived. North Carolina's smoke test clicked Danville, Virginia, as its uncovered
case; it now must open `/va/`, and the uncovered case moved to the Atlantic east of Cape Fear.
Tennessee's smoke test gained Abingdon, Virginia, as a case that must open `/va/`.

**Virginia's hand-off box in `metros.json` stops at latitude 38.91**, because Virginia wraps round
West Virginia and the state's own box holds West Virginia's center, which West Virginia's own
checks refuse. The box decides nothing unless `fleet-outlines.json` cannot be read.

**House of Delegates District 20 lost its card at go-live.** The House's list printed it "Vacant"
on 2026-10-29 and printed no card for it on 2026-10-31, so the roster builder now carries a vacancy
it recorded when the seat's card disappears.

## Still owed

- The seats the election results cannot settle, read from each body's own page, and the councils of
  Hampton, Roanoke, Staunton and Leesburg.
- The town councils the results do not settle, and the wards of the nine towns that elect by ward.
- Contact details for local officials, which the results do not carry (gap
  `va-local-official-contacts`).
- November's local winners, switched on when they take office on 1 January 2027.
