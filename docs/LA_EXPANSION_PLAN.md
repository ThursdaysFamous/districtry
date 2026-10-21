# districtry Louisiana — the record of the launch

> **WENT LIVE 2026-10-21, on Adam's word that day, in the change that follows four hidden ones**
> (his ruling of 2026-10-20, "Towns and school boards too", put the last two ahead of the
> publish): #1661 (the first build: the national tier, both chambers named from each chamber's
> own pages, every parish's police jury or council named from the Secretary of State's list of
> elected officials, and the districts drawn in the 6 parishes whose current lines are
> confirmed), #1668 (the land of Louisiana's four federally recognized tribes, and three of their
> councils), #1671 (every town's mayor and council and its elected chief of police or marshal,
> and the members of every school board, from the same list) and #1675 (the City, Town or
> Village, School District and ZIP Code layers drawn from tile files this site serves, so no
> layer sends a reader's selected point anywhere). Live at districtry.com/la/ with twelve layers.
>
> **THIS FILE WAS WRITTEN AT GO-LIVE, NOT BEFORE THE BUILD**, the way `docs/MS_EXPANSION_PLAN.md`
> was and for the same reason: the plan lived in the thread and on the planning page of
> 2026-10-09, so a file here calling itself the plan would be a reconstruction. It is the record
> of what the changes did, what was measured on the way, and what is still owed. The shipped
> instance — `la/metro-worksheet.json`, `la/CLAUDE.md`, `la/WATCH.md` and the guidebook's
> Louisiana column — remains the record of what IS, and where this file and those disagree,
> those win.

## What ships

| Layer | Count | Ships as | Who it names |
|---|---|---|---|
| Parish | 64 | pre-built | the parish's police jury, council or commission (573 members), and the parish president, mayor-president or mayor where the parish elects one (25) |
| U.S. House | 6 | pre-built, the 119th Congress's map until 3 January 2027 | the representative |
| Louisiana Senate | 39 | pre-built | the senator, from the Senate's own pages (Senate 14 vacant) |
| Louisiana House | 105 | pre-built | the representative, from the House's own pages (House 77 and 92 vacant) |
| Police Jury or Council District | 56 in 6 parishes | pre-built | the member, from the Parish card's list; hidden in the other 58 parishes (gap `la-parish-district-lines`) |
| City, Town or Village | 305 | tile files | the mayor, the council or board of aldermen and the elected chief of police or marshal of 302 municipalities; New Orleans's and Baton Rouge's governments are their parishes' and are on the Parish card (gap `la-municipal-ward-lines`) |
| School District | 69 | tile files | every member of the board, 639 in all (gap `la-school-board-district-lines`) |
| ZIP Code | the 540 that overlap Louisiana; hidden outside the state | tile files | — |
| Tribal Government | 6 pieces of land, 4 nations | pre-built | the councils of the Chitimacha, the Jena Band of Choctaw and the Tunica-Biloxi, each from the nation's own page; nobody for the Coushatta (gap `la-tribal-government`) |
| Police Station | — | live | — (a station is a facility) |
| Fire & EMS Station | — | live | — |
| Post Office | — | live | — |

Counts are the ones `la/CLAUDE.md` records with their measurement dates (2026-10-20 and
2026-10-21). Five weekly workflows open a pull request on a change: the U.S. House roster, both
chambers' rosters (one workflow), the parish, town and school board officials (one run writes all
three files), the fleet's shared tribal refresh for the three councils, and the fleet's census
mirror for the three tile files. A monthly source check re-reads every dataset the instance depends on.

## What Louisiana taught that a copy of a sibling would have got wrong

Each is recorded at length in `la/CLAUDE.md`.

**The Census's newest congressional map is not the one the members were elected from.** Louisiana
redrew its congressional map in its 2026 regular session, and TIGERweb's 120th Congress layer
already carries that map, while the six members the roster names were elected in 2024 from the
2024 plan and represent it until noon on 3 January 2027. Measured against the legislature's own
shapefile of the 2024 plan, the 119th Congress layer matches every district and the 120th keeps
only 76.66% of the plan's area in the same-numbered district, so the app draws the 119th until that
day and the builder refuses a build on or after it.

**The Census's parish district lines are out of date in most parishes.** Louisiana's county
subdivisions are the districts its parish governing bodies are elected from. In 52 of the 63
parishes outside Orleans the Census's current map carries lines that move nobody from its 2020
edition, and every one of the 52 is more than 10% out of balance on the 2020 census's own blocks;
four of them were checked against the parish's own current map and found out of date. So, on
Adam's choice ("Confirmed only", 2026-10-20), a parish's districts are drawn only where its lines
moved after the 2020 census and balance on its blocks: Assumption, Caddo, Lafourche, St. Charles,
Tangipahoa and Terrebonne, at 6.03% to 9.16%. Three came close and are not drawn, St. Tammany,
Ascension and St. James, because the ceiling is not lowered for every parish to take in three.
The New Orleans City Council's districts are not filed with the Census at all.

**The names come from one state list, and the list says more than this project carries.** The
Secretary of State's list of elected officials names every parish's governing body, every town's
officials and every school board's members by seat, and exports each office as a file. Its rows
also print a mailing address and the official's race and gender. The race and gender are never
read; an address ships only as a body's office, where at least three of its officials print the
same one and no official outside the body prints that street line; and since Adam's ruling of
2026-10-17 an official's own telephone ships on that official. The list skips a seat in two
parishes without saying the seat is vacant, so the cards and pages say the list names no one there
rather than calling it vacant. A police jury elects its own president, and the list does not say
who, so no card names one.

**The state's two public election sites refuse every client.** `www.sos.la.gov` and
`electionstatistics.sos.la.gov` answer robots.txt with `User-agent: *` / `Disallow: /`, so neither
is ever read; the voter portal that carries the list permits every path under `/ElectedOfficials/`.

**Louisiana has no township government, and most of the state is outside any city.** All the
sub-county units the Census publishes for Louisiana are the parishes' governing-body districts,
recorded as having no functioning government, plus one placeholder for Orleans. Incorporated
places hold 4.3% of the state's land, so the town card's empty state says the parish is the local
government there.

**Three of the largest cities are governed by their parishes.** New Orleans is Orleans Parish's
government and Baton Rouge shares one with East Baton Rouge Parish, so both are named on the Parish
card; the Census records Houma as a place with no government of its own operating. The
done-standard scorer learned a join for this (`COUNTY_GOVERNED_UNITS` in
`scripts/build_eam_status.py`), so those cities are scored through their parish's governing body
and its drawn districts rather than counted as unnamed: New Orleans and Baton Rouge through
Orleans and East Baton Rouge, whose districts are not drawn, and Houma through Terrebonne, whose
are.

## What the go-live change did

It narrowed the deploy's blanket `la/**` exclude to the build inputs the siblings exclude, added
Louisiana to the deploy's check that every live folder was published, and added `la` to
`metros.json`, with its box clipped short of Mississippi's centre, which puts Louisiana on the front
door, the coverage map, the 404 page, the feedback, privacy and about pages, `llms.txt`, the
sitemap, the fleet hand-off outlines and every sibling app's list of places. It added Louisiana's
column to `layer-concepts.json`. It generated `la/congress.html` and `la/state-legislature.html`
(which lists the three vacant seats as vacant), and `la/parish-government.html` with a page for
each of the 64 parishes under `la/parish-government/`, naming each body's members as the list
prints them. It scored Louisiana on the done standard: 7 of the 14 levels are answered or do not
apply.

**No sibling had a fixed point inside Louisiana.** The audit `la/WATCH.md` asked for was re-run at
go-live with the same answer, and the two live neighbours gained a routing case that must open
`/la/`: Franklinton in Mississippi's smoke test and Farmerville in Arkansas's.

## What is still owed

- **58 parishes' district lines** (gap `la-parish-district-lines`). No statewide map of the
  current lines was found, and no letter has been drafted yet. This is evidence for the
  state-level publishing ask: one statewide map of every parish's current districts from a state
  office would close it for every parish at once.
- **The towns' wards and districts and the school boards' election districts** (gaps
  `la-municipal-ward-lines` and `la-school-board-district-lines`). The Census draws neither, so
  each closes one town's or board's own published map at a time, or with one statewide map.
  610 of the 639 school board members' terms, and nearly half the town officials', end on
  31 December 2026, so the list changes in January 2027; the weekly refresh carries it and
  `la/WATCH.md` says when to look.
- **The Coushatta Tribe's council** (gap `la-tribal-government`). The tribe's own page names its
  chairman and says the council has five members without naming the other four, and a partial
  council is not carried.
- **The police juries' presidents**, from each police jury's own page or minutes, parish by parish.
- **The congressional map on 3 January 2027**, when the 120th Congress's map takes over;
  `la/WATCH.md` has the day's steps, and the monthly source check warns from 1 December 2026.
- **Courts elected by district, precincts, special districts and the parish district boundaries
  as a level of their own**, the done standard's open levels for Louisiana.
