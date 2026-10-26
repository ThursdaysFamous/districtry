# districtry Tennessee — the record of the launch

> **WENT LIVE 2026-10-13, on Adam's word, in the change that follows six hidden ones:** #1468
> (the first build: the national tier and both chambers named, hidden), #1485 (every county
> commission district, and a re-check date for each map file), #1488 and #1491 (the county
> commissioners, county by county, to 54 of 95), and #1495 and #1499 (the letter to the
> University of Tennessee's County Technical Assistance Service, drafted and then recorded as
> sent). Live at districtry.com/tn/ with thirteen layers.
>
> **THIS FILE WAS WRITTEN AT GO-LIVE, NOT BEFORE THE BUILD**, the way `docs/MN_EXPANSION_PLAN.md`
> was and for the same reason: the planning lived in the thread, so a file here calling itself
> the plan would be a reconstruction. It is the record of what the changes did, what was
> measured on the way, and what is still owed. The shipped instance — `tn/metro-worksheet.json`,
> `tn/CLAUDE.md`, `tn/WATCH.md` and the guidebook's Tennessee column — remains the record of
> what IS, and where this file and those disagree, those win.

## What ships

| Layer | Count | Ships as | Who it names |
|---|---|---|---|
| County | 95 | pre-built | nobody; the county commission card does that |
| U.S. House | 9 (the 119th Congress's map) | pre-built | the representative, refreshed weekly |
| Tennessee Senate | 33 | pre-built | the senator, from the Legislature's own map |
| Tennessee House | 99 | pre-built | the representative, from the same map (two seats listed vacant) |
| County Commission District | 859 in 95 counties | pre-built | the members, in the 61 counties whose own pages were read (gap `tn-county-commissioners`) |
| City or Town | 345 | live | nobody (gap `tn-municipal-officeholders`) |
| School District (Unified) | 127 | live | nobody (gap `tn-school-board-members`) |
| School District (Elementary) | 15 | live | nobody (same gap) |
| School District (Secondary) | 15 | live | nobody (same gap) |
| ZIP Code | 1,070 in the envelope, hidden outside Tennessee | live | — |
| Police Station | — | live | — (a station is a facility) |
| Fire & EMS Station | — | live | — |
| Post Office | — | live | — |

Counts are the ones `tn/CLAUDE.md` records with their measurement dates (2026-10-10 and
2026-10-11). Three rosters ship, and each has a weekly workflow that opens a pull request.

## What Tennessee taught that a copy of a sibling would have got wrong

Each is recorded at length in `tn/CLAUDE.md`.

**The congressional map is the old one on purpose until 3 January 2027.** Tennessee redrew its
districts in 2026, and the Census already serves the new map as its default layer. The members
a reader can call today were elected from the old lines, so the builder reads the 119th
Congress's layer and refuses to run after the new Congress sits.

**Who holds each legislative seat comes from the Legislature's own map.** Every district record
on the state's map service names its member or says the seat is vacant. Open States fills in
party and e-mail only where its member for that district has the same surname. The two sources
disagree about House District 31: the state lists it vacant and Open States names Ron Travis.
Re-read at go-live (2026-10-13), both still say what they said on 2026-10-10, so the state's
word still ships.

**Tennessee uses all three of the Census's school tilings.** Most of the state is unified, and
fifteen cities run their own elementary schools while the county runs the high schools, so a
reader there is in one elementary and one secondary district at once.

**There is no civil-district layer.** All 855 county subdivisions the Census carries for
Tennessee are civil districts with no functioning government, and their numbers look like
county commission district numbers without being the same lines.

**County commissioners are named county by county.** No state office publishes who sits on a
county commission, so the names come from each county's own pages, one parser per county, each
checked against that county's August 2026 results or a county document from after the election
before it joins. At go-live 54 of 95 counties are named; Morgan and Trousdale joined later the same day, for 56. A single letter to the University of
Tennessee's County Technical Assistance Service, sent by Adam on 2026-10-11, asks it to add each
commissioner's district to the directory it already keeps, which would cover every county at
once; the follow-up falls due about 1 November 2026.

## What the go-live change did

It narrowed the deploy's blanket `tn/**` exclude to the build inputs the siblings exclude, added
Tennessee to the deploy's check that every live folder was published, and added `tn` to
`metros.json`, which puts Tennessee on the front door, the coverage map, the 404 page, the
privacy and about pages, `llms.txt`, the sitemap, the fleet hand-off outlines and every
sibling app's list of places. It generated `tn/congress.html` and `tn/state-legislature.html`,
and the two roster workflows that feed those pages now regenerate them.

**IT MOVED KENTUCKY'S NEGATIVE POINT, which was the one fixed point in the fleet inside
Tennessee.** Kentucky had placed it in Sumner County on 2026-09-30, when no instance covered
Tennessee. Kentucky's own map-centre checks already refused the fleet outline file, so nothing
would have failed; the point moved anyway, to Adams County, Ohio (38.80, -83.55), because the
worksheet's note says it is outside every instance. It was measured against the Census's state
and county layers with Louisville and Columbus as controls. The same audit, re-run over every
instance's worksheet and every coordinate in every smoke test and fleet probe, found no other
point inside Tennessee's outline.

**THE HAND-WRITTEN ADDRESS BOX ON `tn/county-commissioner.html` HAD NO MARKERS.** `tn/WATCH.md`
said the box was written by hand from the question-form generator's own renderer and must come
out unchanged once the generator reached it. The body did come out unchanged, but the
`GENERATED:BEGIN/END question-lookup` lines around it had been left out, so the generator's
first run added a second box beneath the first. The markers were added around the existing box
and the generator now leaves it as it is.

## What is still owed

- **41 counties' commissioners**, each recorded with its reason in the gap and in `tn/WATCH.md`:
  pages that are stale or unconfirmed, members listed without districts, one seat in doubt,
  sources this project may not read, no published list, sites that were down, and sites that
  refuse or challenge this project's reader. Smith County's six unnamed seats are on the
  3 November ballot.
- **City and town officials, and school board members** (gaps `tn-municipal-officeholders` and
  `tn-school-board-members`). The Comptroller's same service draws 115 school board districts.
- **The Mississippi Band of Choctaw Indians' trust land near Henning**, 0.695 km², which the
  fleet-wide tribal-government thread owns.
- **A judicial layer.** The state courts' site serves a browser challenge, which is never worked
  around, so it would need another publisher.
- **A Capitol office and telephone on the chamber cards.** The Legislature's own pages carry
  both and its robots.txt refuses every crawler; Open States carries neither.
- **The congressional switch on 3 January 2027**, which the builder enforces by refusing to run.
