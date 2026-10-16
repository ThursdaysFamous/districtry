<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Mississippi

**Every civic district that covers your point in Mississippi, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **[districtry.com/ms/](https://districtry.com/ms/)** — a folder of the consolidated repo, following the Wisconsin/Iowa shape rather than a fork.

The national tier, the Mississippi Legislature's own member pages, and every county's board of supervisors as the Secretary of State's directory names them:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (4) | U.S. Census TIGERweb boundary (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Mississippi Senate District (52) | TIGERweb Legislative boundary — the lines of the 2025 court-ordered redraw (pre-built, 2,000-point agreement gate and a 25 m fidelity ceiling) + the legislature's own member gallery and member profiles: name, party, Senate e-mail address and the Capitol office, and a vacant seat named as vacant |
| | Mississippi House District (122) | Same boundary pair and the same roster source |
| **Schools** | School District (137) | TIGERweb unified school districts, which tile the whole state; identity only, recorded as a gap |
| **Geography** | County (82) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; names the county's five supervisors by district from the Secretary of State's County Offices and Directory |
| | City, Town or Village | TIGERweb incorporated places |
| | ZIP Code | TIGERweb ZCTA, fetched by the state's bounding box and hidden outside Mississippi |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it.

**The county board is a board of supervisors, five per county, each elected from a district.**
The Secretary of State's yearly directory names all 410 supervisors by district, so every County
card lists its board. The district LINES are the hard part: the Census still carries the lines
from before the 2020 census in about 70 of the 82 counties, so a supervisor district is drawn
only where its current lines have been confirmed, and the rest is recorded as a gap.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ms/
```

The gates, generated regions, engine composition and data pipeline are documented in [`ms/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`ms/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory, and a seat the legislature shows as vacant says so. The absences are recorded rather than filled in — supervisor district lines in the counties not yet confirmed, municipal officeholders and school board members — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
