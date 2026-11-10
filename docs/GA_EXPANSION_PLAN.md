# districtry Georgia — the record of the launch

> **WENT LIVE on Adam's word of 2026-11-10 to launch now**, in the change that follows six hidden
> ones, rather than on or after 1 January 2027 as the plan first had it. His reason was hosting: the
> tile archives and Census block populations moved to Cloudflare that day (#1958, #1959), so a new
> state's files no longer count against GitHub Pages' limit. The hidden changes: the first build
> (#1813: the national tier, both chambers drawn from the General Assembly's own 2023 plan files and
> named from its own member data, counties, census county divisions, cities, school districts, ZIP
> codes and the outline of Georgia); the check of every county commission and school board map the
> Reapportionment Office publishes against how each county's precincts voted (#1817); county
> commissioners and school board members named from the Secretary of State's election results
> (#1818); the county commission and school board districts drawn where that check passed (#1821);
> the office's 2024 statewide precinct map and the 51 judicial circuits with their judges and
> district attorneys (#1822); and Newton County's districts, drawn once the county's own map showed
> the precinct map had two precinct names swapped (#1940). Live at districtry.com/ga/ with fifteen
> layers.
>
> **THIS FILE WAS WRITTEN AT GO-LIVE, NOT BEFORE THE BUILD**, the way `docs/VA_EXPANSION_PLAN.md`,
> `docs/MO_EXPANSION_PLAN.md` and `docs/LA_EXPANSION_PLAN.md` were and for the same reason: the plan
> was a claude.ai page, with Adam's answers of 2026-10-22 ("all three as recommended"), so a file here
> calling itself the plan would be a reconstruction. The shipped instance — `ga/metro-worksheet.json`,
> `ga/CLAUDE.md`, `ga/WATCH.md` and the guidebook's Georgia gap records — remains the record of what
> IS, and where this file and those disagree, those win.

## What ships

| Layer | Count | Ships as | Who it names |
|---|---|---|---|
| County | 159 | pre-built | the board of commissioners or sole commissioner, where the election results name them (gap `ga-county-commission-members`) |
| U.S. House | 14 | pre-built, the General Assembly's 2023 map | the representative |
| Georgia Senate | 56 | pre-built, the 2023 plan | the senator |
| Georgia House | 180 | pre-built, the 2023 plan | the representative |
| County Commission District | 536 in 110 counties | pre-built, the Reapportionment Office's county maps that passed the precinct check | the district's member, from the election that names them (gaps `ga-county-commission-members`, `ga-county-commission-district-lines`) |
| School Board District | 565 in 105 counties | pre-built, the same way | the district's member, the same way (gaps `ga-school-board-members`, `ga-school-board-district-lines`) |
| Voting Precinct | 2,724 | pre-built, the office's 2024 map | — (each card says what the 2026 ballots say about its county's precincts; gap `ga-precinct-lines-since-2024`) |
| Judicial Circuit | 51 | pre-built, whole counties placed by the newest ballot with a court contest | the superior court judges and the district attorney |
| Census County Division | 586 | tile files | — (a statistical area, not a government) |
| City or Town | 538 | tile files | — (gap `ga-municipal-officeholders`) |
| School District | 181 | tile files | the county school board, where the results name them |
| ZIP Code | 749 in the ZIP search; hidden outside the state | tile files | — |
| Police Station, Fire & EMS Station, Post Office | — | downloaded whole | — (a station is a facility) |

Counts are the ones `ga/CLAUDE.md`, `ga/WATCH.md` and the shipped files record. Measured from the
shipped roster on 2026-11-10, 443 of 783 commission seats and 233 of 645 school board seats are
named, because the results site carries county contests only from November 2024 on.

## What Georgia taught that a copy of a sibling would have got wrong

**The legislative and congressional maps are the General Assembly's own files, not TIGERweb's.**
They agree with TIGERweb on 99.99% of the area, and the largest difference is land the plans put in
Lumpkin County's districts and TIGERweb in Union County's, because the acts define a county as the
2020 census drew it and the Census Bureau has moved that line since.

**The county maps were checked against how the precincts voted before any was drawn.** The
Reapportionment Office publishes a commission and school board map for most counties without saying
which are current, so each map was drawn only where the precincts that voted in each district's
contest lie in that district. Newton's failed, the county's own map then matched the office's, and
the fault was the statewide precinct map, which had two precincts under each other's names; the
State Senate results were the control.

**No state office publishes who sits on a county commission or school board.** The Department of
Community Affairs' directory sits behind a sign-in, so the members are named from the Secretary of
State's official results, each seat for the winner of its newest contest who has taken office, and
a seat with no contest on that site since November 2024 names nobody and says why.

**The judicial circuits come from the ballots, not the court council's table of counties**, which
disagrees with the ballots about 18 counties. The court system's directory is read as a check and
never as a source, because it carries no dates.

**Georgia has no township governments.** All 586 county subdivisions are census county divisions,
so the card says nobody governs one, and the done standard records that level as not applying.

## What the go-live change did

It narrowed the deploy's blanket `ga/**` exclude to the build inputs the siblings exclude, added
Georgia to the deploy's check that every live folder was published, and added `ga` to `metros.json`,
which puts Georgia on the front door, the coverage map, the 404 page, the feedback, privacy and about
pages, `llms.txt`, the sitemap, the fleet hand-off outlines and every sibling app's list of places.
It added Georgia's column to `layer-concepts.json`, the judicial circuits under the trial-court
concept. It generated `ga/congress.html` and `ga/state-legislature.html`, and
`ga/county-commissioner.html` with a page for each of the 152 counties whose commission the results
name, which the weekly county officials job regenerates; the other seven are recorded with their
reasons in `NAMES_NOBODY` in `scripts/build_county_pages.py`. It mirrored the four census layers
into tile archives, so a click in Georgia sends the selected point to no outside server (it was four
layers before; `point-transmission.json`), and built the ZIP code search. It scored Georgia on the
done standard: 9 of the 14 levels are answered or do not apply, and the five open are the county
governing body in every county (146 of 159 name a body and draw it where it is elected by district),
the governing bodies of local governments above 25,000 people, school boards elected by district,
special districts, and tribal government.

**Fixed points elsewhere in the fleet were inside Georgia.** South Carolina's negative point sat in
Wilkes County, Georgia, and moved to the Atlantic, because once Georgia is live no land in South
Carolina's gate is unserved; South Carolina's smoke test now expects a click on Augusta to open
`/ga/`. Tennessee's smoke test gained Dalton and North Carolina's gained Clayton, each expecting
`/ga/`. Each point was checked against the Census Bureau's state layer, with both capitols as
controls.

## Still owed

- November's county winners, shown as elected until they take office on 1 January 2027, when the
  weekly job names them and Chattahoochee, Clarke and Quitman leave `NAMES_NOBODY`.
- The county maps the precinct check could not confirm, once a contest tests them or the county
  answers (letters to McDuffie and Pickens are out).
- The mayors and councils of cities and towns, starting with the 44 above 25,000 people.
- Tile archives for the pre-built district files, the largest this instance ships.
- The Tama state reservation, soil and water conservation districts and a polling-place link, each
  in `ga/WATCH.md`.
