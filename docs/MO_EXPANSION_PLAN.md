# districtry Missouri — the record of the launch

> **WENT LIVE on Adam's word, in the change that follows the hidden ones**, on his choices of
> 2026-10-26: "Shade the map like IL is currently. Launch without voting precincts". The hidden
> changes: the first build (#1687: the national tier, both chambers named from each chamber's own
> pages, and every county's governing body and elected officers named from the Secretary of
> State's 2025–2026 Missouri Roster); the commission districts of the 28 counties whose own maps,
> files or clerks give the lines (#1724, #1725, #1728, #1737); the three charter county councils
> named from their own pages (#1759); the census layers drawn from tile files this site serves, so
> no layer sends a reader's selected point anywhere (#1764); and the two-tier map shading. Live at
> districtry.com/mo/ with thirteen layers.
>
> **THIS FILE WAS WRITTEN AT GO-LIVE, NOT BEFORE THE BUILD**, the way `docs/LA_EXPANSION_PLAN.md`
> was and for the same reason: the plan lived in the thread, so a file here calling itself the plan
> would be a reconstruction. The shipped instance — `mo/metro-worksheet.json`, `mo/CLAUDE.md`,
> `mo/WATCH.md` and the guidebook's Missouri gap records — remains the record of what IS, and where
> this file and those disagree, those win.

## What ships

| Layer | Count | Ships as | Who it names |
|---|---|---|---|
| County | 115 (114 counties and the City of St. Louis) | pre-built | the county's commission, council or legislature and its executive where it elects one, and its other elected officers |
| U.S. House | 8 | pre-built, the 2022 map | the representative |
| Missouri Senate | 34 | pre-built | the senator (Senate 10 vacant) |
| Missouri House | 163 | pre-built | the representative (House 29, 95, 99, 110, 114, 149, 159 and 160 vacant) |
| County Commission District | 56 in 28 counties | pre-built | the district commissioner or council member, from the County card's list; hidden in the other 86 counties and the City of St. Louis (gap `mo-county-commission-district-lines`) |
| Township | 1,394 | tile files | — (gap `mo-township-officers` for the 282 active townships in 20 counties) |
| City, Town or Village | 947 | tile files | — (gap `mo-municipal-officeholders`) |
| School District (Unified, Elementary) | 445 and 71 | tile files | — (gap `mo-school-board-members`) |
| ZIP Code | the 1,040 that overlap Missouri; hidden outside the state | tile files | — |
| Police Station, Fire & EMS Station, Post Office | — | live | — (a station is a facility) |

Counts are the ones `mo/CLAUDE.md` and `mo/WATCH.md` record with their measurement dates.

## What Missouri taught that a copy of a sibling would have got wrong

**The county's body is elected by district, and nobody publishes the districts statewide.** Every
county commission's two associate commissioners are each elected from half the county (RSMo 49.010
and 49.020), and the four charter counties elect their councils and legislature by district too, so
naming who represents a point needs each county's own line. The Secretary of State holds no map of
them (Sunshine request SUN0000585) and offers per-jurisdiction precinct reports without geometry for
$50 (SUN0000590, held on Adam's word). Townships do not stand in for them: Buchanan's and Clay's own
maps split townships. So the lines are drawn county by county from what each county publishes or
sends, 28 at launch, and 40 letters to county election authorities (23 October) ask the rest.

**So the map is shaded in two tiers, the way Illinois's is.** The coverage ring is the counties whose
commission districts are drawn, and the state outline is the lighter band, where every statewide
layer and the County card answer and the commission district layer does not. The band's name in the
map key and the data-gaps panel is "County commission districts not drawn yet". Each county whose
lines are drawn joins the ring in the same change.

**The state's roster is printed every two years, and it was out of date in two of the three charter
counties checked.** Jackson's and Jefferson's own pages name a member the June 2025 edition does not,
so those three counties are named from their own pages; St. Louis County's site serves a managed
challenge to every client and stays on the roster's names.

**A ZIP code crossing a state line goes to the app holding most of it, and the index does not skip a
hidden app**, so Missouri's ZIP search went in at go-live and not before: it took 1 ZIP code from
Illinois's index and 3 from Arkansas's.

**Missouri has no tribal land**, measured on the Census's current vintage.

## What the go-live change did

It narrowed the deploy's blanket `mo/**` exclude to the build inputs the siblings exclude, added
Missouri to the deploy's check that every live folder was published, and added `mo` to
`metros.json`, which puts Missouri on the front door, the coverage map (both tiers), the 404 page,
the feedback, privacy and about pages, `llms.txt`, the sitemap, the fleet hand-off outlines (its
state outline, the widest ground it answers on) and every sibling app's list of places. It added
Missouri's column to `layer-concepts.json`. It generated `mo/congress.html` and
`mo/state-legislature.html` (which lists the nine vacant seats as vacant), and
`mo/county-government.html` with a page for each of the 114 counties under `mo/county-government/`;
the City of St. Louis has no page, because its Board of Aldermen's ward members are not named yet
(gap `mo-st-louis-aldermen`). It built the ZIP code search. It scored Missouri on the done standard:
7 of the 14 levels are answered or do not apply.

**Two fixed points elsewhere in the fleet were inside Missouri**, as `mo/WATCH.md` recorded on the
day the instance arrived. The front door's uncovered case was Clayton, Missouri; it is now Lawrence,
Kansas, and Clayton must open `/mo/`. Illinois's smoke test selected St. Louis expecting it to stay
in Illinois; it now must open `/mo/`, and Illinois's uncovered case was retired rather than moved,
because every state Illinois's permalink gate reaches is now live and the only ground no outline
covers there is slivers between simplified outlines along the Mississippi.

## Still owed

- The commission districts of the other 86 counties, county by county as letters are answered
  (follow-ups about 2026-11-13).
- The City of St. Louis's ward aldermen and wards, the councils of the 27 places of 25,000 people or
  more, township officers and school board members.
- Voting precincts (gap `mo-voting-precincts`), which the 40 county letters also ask for.
- A court layer from the roster's list of circuit judges, if Adam wants one.
