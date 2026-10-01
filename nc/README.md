<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry North Carolina

**Every civic district that covers your point in North Carolina, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **[districtry.com/nc/](https://districtry.com/nc/)** — a folder of the consolidated repo, following the Wisconsin/Iowa shape rather than a fork.

Eleven layers, the national tier every U.S. state can serve from national publishers:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (14) | U.S. Census TIGERweb boundary (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | N.C. Senate District (50) | TIGERweb Legislative boundary (pre-built, 2,000-point agreement gate) + the [Open States](https://openstates.org) roster, enriched from the General Assembly's own member list with each senator's party, e-mail, legislative-building room and telephone |
| | N.C. House District (120) | Same boundary pair, same two publishers — all 120 members carry an office block and an e-mail |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| **Schools** | School District (118) | TIGERweb School unified districts — identity only; no publisher this instance can reach names the elected boards, which is recorded as a gap |
| **Geography** | County (100) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring |
| | Township, City or Town | TIGERweb county subdivisions and places |
| | ZIP Code | TIGERweb ZCTA, fetched by the state's bounding box |
| | Post Office | USGS National Map structures, nearest-N |

This is the national tier only — the first PR of a phased bring-up, and the instance is **dark**
while it lands: it has no `metros.json` entry and its folder is excluded from the Pages deploy,
so nothing is served and no landing card names it.

**The flagship layer this instance is building toward is `county-commissioner`**, and North
Carolina's shape is unlike any state in the fleet so far. All 100 counties elect a board of
commissioners, and the [NCACC](https://www.ncacc.org) publishes every county's *election
method* in one statewide table — measured: 39 at large, 23 district-labelled but elected
countywide, 22 a combination, 16 purely by district, 587 commissioners in all — so the
`county` card can state every county's board form on day one with no geometry at all. What no
publisher answers is the geometry: NCGS 153A-22(f) leaves each board's district delineation as
a **written description in the county clerk's office**, and the resolution filed with the
Secretary of State is text rather than a map. That absence, and two more, are recorded in the
app's Data gaps panel rather than papered over, following the repo's
[`docs/EXPANSION_GUIDE.md`](../docs/EXPANSION_GUIDE.md).

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/nc/
```

The gates, generated regions, engine composition and data pipeline are documented in [`nc/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`nc/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory. Three absences are recorded rather than filled in — county commissioner districts, municipal officeholders and school board members — each with what is missing, why, and what would close it. The **township** card is the case that needed measuring rather than inheriting: North Carolina's townships are FUNCSTAT `N`, non-functioning, so the card names the township and no officeholder, and records **no** gap, because recording one would imply a body this app could eventually name. City, town and village are one kind of government under NCGS 160A-1(2), so the municipality card carries one note rather than three. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
