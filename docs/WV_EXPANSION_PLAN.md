# districtry West Virginia — the record of the launch

> **OPENED BY THE GO-LIVE CHANGE THAT FOLLOWS FOUR HIDDEN ONES, on Adam's choice of 2026-11-10 to
> launch now** rather than on or after 1 January 2027, the date his answers to the plan
> (2026-10-29, "all as recommended") had set. His choice set the timing only; the change itself
> waited for his own "merge". The hidden changes: the first build (#1814: the national tier, both
> chambers drawn from the Legislature's own plan files and named from its own rosters, the
> magisterial districts from the state's own map, and every county's commission and other elected
> officers from the Secretary of State's directory); Charleston's 20 council wards from the city's
> own map, with its council named from the city's own page (#1859); and the weekly refreshes of
> the county directory (#1888) and Charleston's council (#1904). The last hidden step, the tile
> archives for the three TIGERweb layers, went in as the first commit of the go-live change.
>
> **THIS FILE WAS WRITTEN AT GO-LIVE, NOT BEFORE THE BUILD**, the way `docs/VA_EXPANSION_PLAN.md`
> and `docs/MO_EXPANSION_PLAN.md` were and for the same reason: the plan was a claude.ai artifact
> with Adam's answers of 2026-10-29, so a file here calling itself the plan would be a
> reconstruction. The shipped instance — `wv/metro-worksheet.json`, `wv/CLAUDE.md`,
> `wv/WATCH.md` and the guidebook's West Virginia gap records — remains the record of what IS, and
> where this file and those disagree, those win.

## What ships

| Layer | Count | Ships as | Who it names |
|---|---|---|---|
| County | 55 | pre-built | the county commission (three members, five in Berkeley and Jefferson, all elected countywide) and the county clerk, circuit clerk, assessor, sheriff, prosecuting attorney and surveyor |
| U.S. House | 2 | pre-built, the 2021 map | the representative |
| West Virginia Senate | 17 | pre-built, the Legislature's plan file | both senators for each district |
| House of Delegates | 100 | pre-built, the Legislature's plan file | the delegate |
| Magisterial District | 195 | pre-built, the state's own map | — (a magisterial district elects nobody of its own) |
| City, Town or Village | 229 | tile files | — (gap `wv-municipal-officeholders`) |
| City Council Ward | 20, Charleston only | pre-built, the city's own map | the ward's council member, and the six at-large members (gap `wv-city-wards`) |
| School District | 55, one per county | tile files | — (gap `wv-school-board-members`) |
| ZIP Code | the codes that overlap West Virginia; hidden outside the state | tile files | — |
| Police Station, Fire & EMS Station, Post Office | — | downloaded whole | — (a station is a facility) |

Counts are the ones `wv/CLAUDE.md` and `wv/WATCH.md` record with their measurement dates.

## What West Virginia taught that a copy of a sibling would have got wrong

**Every county commission is elected by the whole county.** A commissioner must live in a
different magisterial district from the others, but every voter in the county votes for every
seat, so there is no commission district to draw and naming the members is the whole answer. The
done-standard scorer had never met a state like that: its Answered test credited a county tier
only through drawn districts or a gap record, so West Virginia first read as answering nothing.
It now credits a state whose every county names an at-large body and owes no map. Kentucky, whose
records are flat too, is unchanged, because its magisterial-form fiscal courts are elected by
district and their maps are owed.

**The Senate elects two members from each district.** The legislator page builder and the
officeholder tables expected one member per district, so both learned to read a district holding
a `members` list and a `seats` count, and the page counts people rather than districts.

**Virginia's centre lies inside West Virginia's box.** Virginia wraps round the state's eastern
panhandle, so the hand-off box in `metros.json` stops at longitude -79.43 rather than -77.71.
Clipping the bottom of the box instead would have cut fourteen counties, seven of them whole,
against ten for the side.

**The state's election map service holds a layer of individual voter locations.** It is never
read, by any builder, probe or agent; only the folder of election boundaries is.

## What the go-live change did

It mirrored the City, Town or Village, School District and ZIP Code layers into tile archives,
so no West Virginia layer sends a reader's selected point to a server. It narrowed the deploy's
blanket `wv/**` exclude to the build inputs the siblings exclude, added West Virginia to the
deploy's check that every live folder was published, and added `wv` to `metros.json`, which puts
West Virginia on the front door, the coverage map, the 404 page, the feedback, privacy and about
pages, `llms.txt`, the sitemap, the fleet hand-off outlines and every sibling app's list of
places. It added West Virginia's column to `layer-concepts.json`. It generated `wv/congress.html`
and `wv/state-legislature.html`, and `wv/county-commissioner.html` with a page for each county
under `wv/county-commissioner/`, and each weekly roster job now regenerates the pages that read
its roster. It built the ZIP code search. It scored West Virginia on the done standard: 10 of the
14 levels are answered or do not apply, and the four open are the councils of Huntington,
Morgantown, Parkersburg and Wheeling, the courts, the precincts and the special districts.

**No fixed point elsewhere in the fleet was inside West Virginia**, re-measured at the go-live
change as `wv/WATCH.md` asked. West Virginia's own negative point is in Garrett County, Maryland,
which no app serves, and stays there until Maryland goes live.

**One request broke a robots rule while the legislator page was written.** A check of
`www.wvlegislature.gov`'s robots.txt was read wrong (the reader returns a pair, and the pair was
tested as if it were the answer), so one page under `/WVCODE/`, which that file disallows, was
fetched once. Nothing from it was used: the page's sentence about terms rests on what the
instance already records, and the builder's comment says the constitution was not read.

## Still owed

- The councils of Huntington, Morgantown, Parkersburg and Wheeling, and the wards of the three that
  elect by ward as each city sends its file (letters out 2026-10-21, follow-ups about 2026-11-11).
- The county boards of education, named from the May 2026 primary's results or the 2027 directory.
- Voting precincts in the 29 counties whose current maps are confirmed.
- Tile archives for the pre-built polygon layers, the magisterial districts first (3.9 MB whole).
- November's winners, carried by the weekly refreshes as each source lists them: delegates and
  senators from 1 December 2026, commissioners from 1 January 2027.
