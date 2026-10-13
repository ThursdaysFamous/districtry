# districtry South Carolina — the record of the launch

> **SHIPPED 2026-10-13 — four changes over four days: #1467 (the instance and the national tier,
> dark), #1486 (every county council's districts and every member, still dark), #1489 (keep the
> council names when the results site turns the weekly job away, and settle seven county pages),
> and the go-live change.** The Catawba Nation's land (#1501) landed in between, from the
> fleet-wide tribal thread. Live at districtry.com/sc/ with twelve layers.
>
> **THIS FILE WAS WRITTEN AT GO-LIVE, NOT BEFORE THE BUILD**, the Minnesota precedent: the
> planning lived in the South Carolina thread, so this is the record of what the changes did, not
> a plan. The shipped instance — `sc/metro-worksheet.json`, `sc/CLAUDE.md`, `sc/WATCH.md`, the
> guidebook's South Carolina column — is the record of what IS.

## What ships

| Layer | Who it names |
|---|---|
| County | the council's countywide seats (chairs, supervisors, at-large members) |
| County Council District | every one of the 334 seats in all 46 counties, each the winner of its most recent general election |
| U.S. House | the representative, refreshed weekly |
| South Carolina Senate | every senator, from the General Assembly's own pages, weekly |
| South Carolina House | every representative, the same way |
| School District | nobody (gap `sc-school-board-members`) |
| City or Town | nobody (gap `sc-municipal-officeholders`) |
| ZIP Code | — (hidden outside the state) |
| Tribal Government | the Catawba Nation's executive committee |
| Police Station, Fire & EMS Station, Post Office | — (a station is a facility) |

## The county council is the flagship, and its names are election winners

Every South Carolina county has been governed by an elected council since the Home Rule Act of
1975. The districts are the state Revenue and Fiscal Affairs Office's, all 46 counties in one
layer. The names are each seat's most recent general-election winner in the State Election
Commission's certified results, so every card and every county page dates each name to that
election and says it is not a claim about who sits today. Each county's own council page is read
beside the results; eleven seats differ and both readings are shown.

Two counties are not district maps: Hampton elects its whole council at large, and Jasper elects
all five countywide, four from residence townships that no published source ties to the map's
numbers. Both cards, and both county pages, name all five members.

## What the go-live change did

- Published the folder: the blanket `'sc/**'` deploy exclude became the siblings' narrow set, and
  `sc` joined the deploy's presence loop. Tennessee stays dark behind its own blanket line.
- Added the `metros.json` entry, its hand-off box clipped at 35.16 N so it does not hold North
  Carolina's own centre (`sc/WATCH.md` has the measurement), and ran `--sync-fleet`; added `sc` to the coverage map's `AREAS`
  (one tier, like North Carolina and Oklahoma) and to `fleet-outlines.json`'s sources.
- Wrote `county-council.html` and turned on the `sc_councils` adapter in
  `scripts/build_county_pages.py`, which writes a page per county under `county-council/`. The
  adapter was written while the instance was dark (it was the first entry in `HELD_INSTANCES`) so
  the status report could score the county tier before go-live; go-live moved it to `INSTANCES`.
- Generated `congress.html` and `state-legislature.html` — South Carolina names both chambers, so
  it owes the legislature page, the North Carolina case.
- Gave the three roster workflows their page-regeneration steps.
- Registered `sc` in the traffic page, the Wikidata draft (Q1456, read from Special:EntityData
  on 2026-10-13), the tribal-join gate and the status report.
- Moved North Carolina's uncovered test point from Columbia, South Carolina to Danville,
  Virginia, and made Columbia a case that must open `/sc/`. The fixed-point audit was re-run at
  go-live, as `sc/WATCH.md` said to, and Columbia was the only point in the fleet inside South
  Carolina.

## What is still owed

Read `sc/WATCH.md`. The two items with dates on them are the November results — the weekly job
cannot read the results site from GitHub's runners, and how the names are refreshed after the
3 November 2026 election waits on Adam's ruling — and the Senate District 15 special election.
