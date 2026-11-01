<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Virginia

**Every civic district that covers your point in Virginia, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, which will serve at **districtry.com/va/** — a folder of the consolidated repo, following the Wisconsin/Iowa shape rather than a fork.

The national tier, and both chambers of the General Assembly named from each chamber's own member pages:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (11) | U.S. Census TIGERweb boundary — the map the Supreme Court of Virginia adopted in December 2021, which the November 2026 election uses (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Virginia Senate District (40) | TIGERweb's 2026 state legislative districts (pre-built, 2,000-point agreement gate and an 8 m fidelity ceiling) + the Senate of Virginia's own member list and member pages: name, party, e-mail address, session office and telephone |
| | House of Delegates District (100) | TIGERweb's 2026 state legislative districts, drawn in one topology with the Senate's + the House of Delegates' own member list and member pages: name, party, e-mail address, Capitol office and telephone, and a vacant seat named as vacant |
| **Schools** | School Division (135), School Division (Elementary) (1, Lexington) | TIGERweb unified and elementary school districts, which between them tile the whole state; identity only, recorded as a gap |
| **Geography** | County or City (133) | TIGERweb State_County, pre-built — the 95 counties and the 38 independent cities, the app's offline anchor and the coverage ring |
| | Magisterial District | The Department of Elections' election district lines in the 72 counties whose census subdivisions carry the same names; elsewhere TIGERweb's county subdivisions, the Census Bureau's copy |
| | City or Town | TIGERweb incorporated places: 38 independent cities and 189 towns |
| | ZIP Code | TIGERweb ZCTA, fetched by the state's bounding box and hidden outside Virginia |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it.

**The local districts come next.** Every county's board of supervisors, every city's council and
most school boards are elected, and none of them is named yet. The Department of Elections
publishes every county's and city's election districts and precincts as map files, and the
state's election results name who won each seat; the plan builds those in the next change.
Until then the County or City, City or Town and School Division cards say who is not named, and
the Data gaps panel says why.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/va/
```

The gates, generated regions, engine composition and data pipeline are documented in [`va/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`va/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory, and a seat a chamber shows as vacant says so. The absences are recorded rather than filled in — boards of supervisors, city and town councils, school boards and the election districts they are elected from — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
