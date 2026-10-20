# districtry Mississippi — the record of the launch

> **WENT LIVE 2026-10-16, on Adam's word that day ("Finer first", the go-live card's option that put one
> more hidden change ahead of the publish), in the change that follows four hidden ones:** #1555 (the first build: the national tier, both chambers named from the
> legislature's own pages, every county's five supervisors named from the Secretary of State's
> directory, and the supervisor districts drawn in twelve counties), #1575 (eight more counties'
> supervisor districts, the Mississippi Band of Choctaw Indians' land, the four courts whose judges
> are elected from districts, and every county's five election commissioners), #1588
> (three more counties' supervisor districts, and the county lines at Adam's "Finest" setting)
> and #1597 (the supervisor districts and the legislature's three maps redrawn at the county
> lines' setting, the one more change). Live at districtry.com/ms/ with sixteen layers.
>
> **THIS FILE WAS WRITTEN AT GO-LIVE, NOT BEFORE THE BUILD**, the way `docs/AR_EXPANSION_PLAN.md`
> was and for the same reason: the plan lived in the thread and on the planning page, so a file
> here calling itself the plan would be a reconstruction. It is the record of what the changes
> did, what was measured on the way, and what is still owed. The shipped instance —
> `ms/metro-worksheet.json`, `ms/CLAUDE.md`, `ms/WATCH.md` and the guidebook's Mississippi column —
> remains the record of what IS, and where this file and those disagree, those win.

## What ships

| Layer | Count | Ships as | Who it names |
|---|---|---|---|
| County | 82 | pre-built | the county's five supervisors and five election commissioners |
| U.S. House | 4 | pre-built | the representative |
| Mississippi Senate | 52 | pre-built | the senator, from the legislature's own pages (Senate 34 vacant) |
| Mississippi House | 122 | pre-built | the representative, from the same pages (House 70 and 77 vacant) |
| County Supervisor District | 125 in 25 counties (115 in 23 at go-live; Covington and Tippah added after it) | pre-built | the supervisor, and the election commissioner elected from the same district where the directory numbers both lists alike (gap `ms-supervisor-district-lines` for the other 57 counties) |
| Supreme Court District | 3 | pre-built | the district's three justices |
| Court of Appeals District | 5 | pre-built | the district's two judges, and both districts' judges in the ten counties the court divides by precinct (gap `ms-coa-precinct-lines`) |
| Chancery Court District | 20 | pre-built | the district's chancellors, every one of the district where a chancellor is elected from part of it (gap `ms-court-subdistricts`) |
| Circuit Court District | 23, and 22 from 1 January 2027 | pre-built | the district's circuit judges, on the same terms |
| Tribal Government | 2 | pre-built | the Tribal Chief and the seventeen council members, each with the community they represent |
| City, Town or Village | 300 | live | the mayor and council of 14 of the 15 cities of 25,000 people or more, from each city's own website (added after go-live); nobody elsewhere (gap `ms-municipal-officeholders`) |
| City Ward | 57 in 9 cities (added after go-live) | pre-built | the ward's member, from the City card's list; the other six of the 15 cities are not drawn (gap `ms-city-ward-lines`) |
| School District | 137 | live | nobody (gap `ms-school-board-members`) |
| ZIP Code | hidden outside Mississippi | live | — |
| Police Station | — | live | — (a station is a facility) |
| Fire & EMS Station | — | live | — |
| Post Office | — | live | — |

Counts are the ones `ms/CLAUDE.md` records with their measurement dates (2026-10-15 and
2026-10-16). Six files have a weekly workflow that opens a pull request: the U.S. House roster,
the two chamber rosters, the county officials, the judges and the Choctaw council, which the
fleet's shared tribal refresh reads. The city councils and wards were read once, on 2026-10-17,
and have no weekly workflow; the monthly source check re-reads both.

## What Mississippi taught that a copy of a sibling would have got wrong

Each is recorded at length in `ms/CLAUDE.md`.

**The Census's supervisor district lines are out of balance in 64 counties.** Mississippi's county
subdivisions are its supervisor districts. In 70 counties the Census's current map still carries
the lines of its 2020 edition, and in 64 of them those lines are more than 10% out of balance on
the 2020 census's own blocks; measured on those blocks, the Census's lines put 34% of Madison
County's residents in the wrong district. In 52 of the 64 the lines put every resident in the same
district as the Census's January 2010 edition did, and 49 of those 52 were already more than 10%
out of balance on the 2010 census. Those 49 counties held 1,504,204 of the state's 2,961,279
residents in 2020, about half, and still about half without Coahoma and Sunflower, where one very
large census block could account for the whole imbalance (measured 2026-10-16). So, on Adam's
choice ("Confirmed only", 2026-10-15), a county's districts are drawn only where its current lines
are confirmed: twelve counties whose Census lines changed after the 2020 census and balance on its
blocks, and eleven whose published map proves its currency (thirteen since a change after
go-live added Covington and Tippah). Every drawn line follows 2020 census blocks, so no line is
traced by hand.

**Every line the app draws is about as close to its source as the county lines are.** Adam
chose the finest setting for the county lines ("Finest", 2026-10-15), and before the instance
opened the same setting for the supervisor districts and the legislature's three maps ("Finer
first", 2026-10-16). At the setting the district files had shipped with, a legislative line
strayed up to 21.4 m from the Census's and 58.4 km² of ground was answered with a different
State House district or none; at the new one no line strays more than 5.6 m from the lines it
was built from and that figure is 13.0 km². The four files are about twice the download.

**The names and the lines come from different places.** The Secretary of State's County Offices
and Directory names all 410 supervisors and all 410 election commissioners by district, once a
year, so every County card lists its board even where the map draws no districts. The directory
also prints addresses and telephones that may be homes: a board's address or telephone is carried
only where at least three of its five supervisors print the same one, and no other address is
kept. Since Adam's ruling of 2026-10-17 ("if the official government source uses personal phone
numbers, we publish those") a supervisor's or commissioner's own telephone is carried on that
person, and the addresses still never are.

**Mississippi has no township government.** All 410 county subdivisions the Census publishes are
the supervisor districts, recorded as having no functioning government.

**The courts are drawn from whole counties, and two parts are recorded as missing.** Each court's
own page lists its districts by county, and the 2025 and 2026 laws redraw the chancery and circuit
districts on 1 January 2027, so both maps ship and the app switches at midnight in Mississippi
that night. The Court of Appeals divides ten counties between two districts by voting precinct,
and some chancery and circuit judges are elected from part of a district; neither is drawn.

**The Choctaw land carries no districts.** The Census draws two areas for the band, its
reservation and its off-reservation trust land, and no districts on either, so each council
member's community is a word beside the name rather than a shape on the map.

## What the go-live change did

It narrowed the deploy's blanket `ms/**` exclude to the build inputs the siblings exclude, added
Mississippi to the deploy's check that every live folder was published, and added `ms` to
`metros.json`, which puts Mississippi on the front door, the coverage map, the 404 page, the
privacy and about pages, `llms.txt`, the sitemap, the fleet hand-off outlines and every sibling
app's list of places. It added Mississippi's column to `layer-concepts.json`. It generated
`ms/congress.html` and `ms/state-legislature.html` (which lists the three vacant seats as
vacant), and `ms/county-supervisor.html` with a page for each of the 82 counties under
`ms/county-supervisor/`, naming the five supervisors as the directory lists them.

**No sibling had a fixed point inside Mississippi.** The audit `ms/WATCH.md` asked for was re-run
at go-live with the same answer, and the two live neighbours gained a routing case that must open
`/ms/`: Southaven in Tennessee's smoke test and Clarksdale in Arkansas's.

## After go-live

- **Covington's and Tippah's supervisor districts** (2026-10-16, the first change after go-live).
  Covington's come from the parcel viewer the county's website links to, whose map draws them as
  Supervisor Districts 2023 beside its 2023 voting precincts; the layer draws District 2 in two
  pieces, which the build joins. Tippah's come from a map published online as the Tippah County
  2022 Redistricting Map, in a mapping company's account; who publishes it is not established, and
  the county's website could not be read from here. Both are confirmed by a map of the county's
  voting precincts, measured on the 2020 census's blocks: Covington's precincts put 17 of the
  county's 18,340 residents in a different district from the drawn lines against 896 for the
  Census's, and Tippah's none of 21,815 against 669. The supervisor layer now draws 25 counties.

## What is still owed

- **57 counties' supervisor districts** (gap `ms-supervisor-district-lines`). Two publish lines
  of their own that nothing found proves current (Coahoma and Wilkinson). A letter asking the
  state's GIS clearinghouse to collect and publish every county's current map went on 2026-10-16,
  in a version the operator rewrote and sent (Ask ms-maris-supervisor-districts in
  `docs/ASK_DRAFTS.md`); a follow-up is due about 6 November if there is no answer.
- **The 2027 judges.** From 1 January 2027 the chancery and circuit cards name nobody until there
  is a list of judges for the 2027 districts. The judges elected on 3 November 2026 take those
  seats, so the plan is to build that list from the certified results before 1 January.
- **Every supervisor and legislator after 2 November 2027.** The Secretary of State's election
  calendar lists county supervisors and both chambers of the legislature among the offices
  elected that day, so the directory's next edition and the legislature's pages change after it.
- **The officials of the other 285 municipalities and of Greenville, the wards of six of the 15
  largest cities, and school board members** (gaps `ms-municipal-officeholders`,
  `ms-city-ward-lines` and `ms-school-board-members`). A weekly refresh of the 15 cities' council
  pages waits on the operator's word, since it would be a new weekly workflow.
- **The Court of Appeals' precinct lines and the parts of chancery and circuit districts** (gaps
  `ms-coa-precinct-lines` and `ms-court-subdistricts`).
- **Precincts, school board districts and special districts.**
