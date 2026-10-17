# districtry Arkansas — the record of the launch

> **WENT LIVE 2026-10-15, on Adam's word ("turn on arkansas"), in the change that follows one
> hidden one:** #1515 (the first build: the national tier, both chambers named from the
> legislature's own pages, every quorum court district drawn and named, hidden). Live at
> districtry.com/ar/ with eleven layers.
>
> **THIS FILE WAS WRITTEN AT GO-LIVE, NOT BEFORE THE BUILD**, the way `docs/TN_EXPANSION_PLAN.md`
> was and for the same reason: the planning lived in the thread and in the planning page, so a
> file here calling itself the plan would be a reconstruction. It is the record of what the
> changes did, what was measured on the way, and what is still owed. The shipped instance —
> `ar/metro-worksheet.json`, `ar/CLAUDE.md`, `ar/WATCH.md` and the guidebook's Arkansas column —
> remains the record of what IS, and where this file and those disagree, those win.

## What ships

| Layer | Count | Ships as | Who it names |
|---|---|---|---|
| County | 75 | pre-built | the county judge, and the county's justices of the peace as a list |
| U.S. House | 4 | pre-built | the representative, refreshed weekly |
| Arkansas Senate | 35 | pre-built | the senator, from the legislature's own pages (Senate 1 and 18 vacant) |
| Arkansas House | 100 | pre-built | the representative, from the same pages (House 8 vacant) |
| Quorum Court District | 775 in 75 counties | pre-built | the justice of the peace in 737 districts (gap `ar-quorum-court`) |
| City or Town | 501 | live | nobody (gap `ar-municipal-officeholders`) |
| School District | 234 | live | nobody (gap `ar-school-board-members`) |
| ZIP Code | hidden outside Arkansas | live | — |
| Police Station | — | live | — (a station is a facility) |
| Fire & EMS Station | — | live | — |
| Post Office | — | live | — |

Counts are the ones `ar/CLAUDE.md` records with their measurement date (2026-10-13). Three
rosters ship, and each has a weekly workflow that opens a pull request; one of the three has never
completed, below.

## What Arkansas taught that a copy of a sibling would have got wrong

Each is recorded at length in `ar/CLAUDE.md`.

**The congressional map is the Census's default layer, and that was measured.** Tennessee and
North Carolina redrew for 2026, so their builders read the 119th Congress's layer until
3 January 2027. Arkansas did not redraw: its four districts on the two layers carry the same
identifiers and the same land areas, so the default layer is right here.

**The legislature's member list cannot tell a sitting member from a former one.** It holds 138
rows for 135 seats; a member who has left keeps their row and only their own page says why. So
every member page is read, a seat whose only member has left ships as a vacancy naming the page
that says so, and the mailing address on those pages is never read, because some are home
addresses. The telephone beside it was left out for the same reason until Adam's ruling of
2026-10-17 ("if the official government source uses personal phone numbers, we publish those"),
and now ships as printed.

**The quorum court's districts and its people come from different places.** The state's mapping
office draws every county's justice of the peace districts. The counties association lists each
county's justices without saying who sits for which district. On Adam's rulings of 2026-10-13 a
district's justice is named from the county's own numbered list where the county publishes one
(20 counties), and elsewhere from the association's 2024 election results, only while the
association's current list still includes the winner. On the 20 counties that number their own,
the results rule named 203 districts and 202 agreed; the one that did not was a justice the
county has since moved to another district.

**The state courts' directory was the stale publisher, not the association.** In all five
counties where the two named different county judges, a third source sided with the association.

**There is no township layer.** All 1,051 county subdivisions the Census carries for Arkansas are
legal areas with no functioning government.

## What the go-live change did

It narrowed the deploy's blanket `ar/**` exclude to the build inputs the siblings exclude, added
Arkansas to the deploy's check that every live folder was published, and added `ar` to
`metros.json`, which puts Arkansas on the front door, the coverage map, the 404 page, the
privacy and about pages, `llms.txt`, the sitemap, the fleet hand-off outlines and every sibling
app's list of places. It added Arkansas's column to `layer-concepts.json` and took the concept
colours. It generated `ar/congress.html` and `ar/state-legislature.html` (which lists the three
vacant seats as vacant), and `ar/quorum-court.html` with a page for each of the 75 counties
under `ar/quorum-court/`.

**EACH COUNTY'S PAGE NAMES EVERY PERSON ON THE ASSOCIATION'S LIST EXACTLY ONCE.** The county
judge first, then each district's justice where a source places one, then a section for the
justices the association lists and no source places, so a reader still sees who sits on their
court where the district is not known. Across the 75 pages that is 75 judges and 772 justices.
The judge is not counted as a member of the court, because under the state constitution the
county judge presides without a vote.

**THE COUNTY-OFFICIALS JOB HAS NEVER COMPLETED, AND THE APP NOW SAYS SO BY DATE.** Its first
run, scheduled 2026-10-14 and re-run 2026-10-15, failed because the association's site answers
GitHub's servers with HTTP 403. That is an access control and is not worked around. The cards and
the sources page had said the names were refreshed every week; they now say the day the names
were read, 2026-10-13, and so do the county pages.

**No sibling had a fixed point inside Arkansas.** The audit `ar/WATCH.md` asked for was re-run at
go-live with the same answer, and the two live neighbours gained a routing case that must open
`/ar/`: West Memphis in Tennessee's smoke test and Fort Smith in Oklahoma's.

## What is still owed

- **38 quorum court districts with no named justice**: two seats the county lists vacant, 27
  whose 2024 winner is no longer on the association's list, 5 with no 2024 winner and 4 whose
  names cannot be matched with certainty. Each card says which.
- **A weekly reader the association lets in.** Until then the January 2027 re-read, after the new
  terms start, is a person's run. A letter asking for it, and for each justice's district on the
  association's county pages, was drafted on 2026-10-15 (Ask ar-aac-county-pages in
  `docs/ASK_DRAFTS.md`).
- **Every county seat after 3 November 2026.** All 75 county judges and 775 justices are on that
  ballot and the new terms start on 1 January 2027.
- **City and town officials, and school board members** (gaps `ar-municipal-officeholders` and
  `ar-school-board-members`). The state's map service draws wards for all 19 cities over 25,000
  people and board zones for 176 school districts.
- **Precincts, court districts and special districts**, which the same service draws.
