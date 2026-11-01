<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry West Virginia

**Every civic district that covers your point in West Virginia, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, which will serve at **districtry.com/wv/** once it launches — a folder of the consolidated repo, following the Missouri shape rather than a fork.

The national tier, both legislative chambers drawn from the Legislature's own plan files and named from its own rosters, the magisterial districts county commissioners are elected from, and every county's commission and elected officers as the Secretary of State's directory names them:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (2) | U.S. Census TIGERweb boundary, the map drawn in 2021, which the sitting members were elected from and which the November 2026 election uses too (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | West Virginia Senate District (17) | The Legislature's own files of the 2021 Senate plan (pre-built, 2,000-point agreement gate and an 8 m fidelity ceiling, with the state's GIS centre's map read as a second witness) + the Senate's own roster: both senators for each district, with party, Capitol office, telephone and e-mail address |
| | West Virginia House of Delegates District (100) | The Legislature's own files of the 2021 House of Delegates plan + the House's own roster: name, party, Capitol office, telephone and e-mail address |
| **Schools** | School District (55) | TIGERweb unified school districts, one per county; identity only, the board members recorded as a gap |
| **Geography** | County (55) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; names the county commission and the other elected county officers, from the Secretary of State's directory of county officials |
| | Magisterial District (195) | The state's own map of each county's magisterial districts, from the West Virginia GIS Technical Center's election layers (pre-built); each county commissioner must live in a different one, and all are elected by the whole county |
| | City, Town or Village | TIGERweb incorporated places |
| | ZIP Code | TIGERweb ZCTA, fetched by the state's bounding box and hidden outside West Virginia |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it. It is
planned to publish on or after 1 January 2027, after the November 2026 election's winners
take their seats, and only on the operator's own go-ahead.

**Every county's commission is named on the County card**: three commissioners in 53 counties
and five in Berkeley and Jefferson, all elected by the whole county, each required to live in a
different magisterial district. The card also names the county clerk, circuit clerk, assessor,
sheriff, prosecuting attorney and surveyor where the directory lists one.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/wv/
```

The gates, generated regions, engine composition and data pipeline are documented in [`wv/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`wv/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory, and an office the Secretary of State's directory does not list is left off rather than filled in. The absences are recorded rather than filled in — school board members, city and town officials, city wards and voting precincts — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
