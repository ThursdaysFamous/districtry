<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Georgia

**Every civic district that covers your point in Georgia, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **[districtry.com/ga/](https://districtry.com/ga/)** — a folder of the consolidated repo, following the Wisconsin/Iowa shape rather than a fork.

The national tier, and the three district maps the General Assembly enacted in December 2023, drawn from its own files and named from its own member data:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (14) | The General Assembly's own shapefile of the 2023 congressional plan, the map the November 2026 election uses too (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Georgia Senate District (56) | The General Assembly's own shapefile of the 2023 Senate plan (pre-built, 2,000-point agreement gate and an 8 m fidelity ceiling) + the General Assembly's own member data: name, party, Capitol office, telephone and e-mail address, and a vacant seat named as vacant |
| | Georgia House District (180) | The General Assembly's own shapefile of the 2023 House plan + the same member data |
| **Schools** | School District (181) | TIGERweb unified school districts, which cover the whole state but Fort Benning; identity only, recorded as a gap |
| **Geography** | County (159) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; no commissioner named yet, recorded as a gap |
| | Census County Division | TIGERweb county subdivisions; Georgia has no township governments, and the card says so |
| | City or Town | TIGERweb incorporated places, with the eight governments a city and its county share named as one |
| | ZIP Code | TIGERweb ZCTA, fetched by the state's bounding box and hidden outside Georgia |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it.

**The county commissions and school boards come next**: their districts from the Reapportionment
Office's county maps, checked against the precincts each contest was counted in, and their members
from the Secretary of State's election results. Until then the County and School District cards
name the place and say that nobody is named yet.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ga/
```

The gates, generated regions, engine composition and data pipeline are documented in [`ga/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`ga/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory, and a seat the General Assembly shows as vacant says so. The absences are recorded rather than filled in — county commissioners, school board members, and city and town officials — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
