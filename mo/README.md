<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Missouri

**Every civic district that covers your point in Missouri, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **[districtry.com/mo/](https://districtry.com/mo/)** — a folder of the consolidated repo, following the Wisconsin/Iowa shape rather than a fork.

The national tier, both legislative chambers drawn from the state's own maps and named from each chamber's own publications, and every county's governing body as the Secretary of State's Missouri Roster names it:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (8) | U.S. Census TIGERweb boundary — the 2022 map, which the sitting members were elected from and which the November 2026 election uses too (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Missouri Senate District (34) | The Office of Administration's own map of the 2022 Senate plan (pre-built, 2,000-point agreement gate and an 8 m fidelity ceiling) + the Senate's own senator directory: name, party, Capitol office and telephone, with each senator's e-mail address from the Secretary of State's General Assembly Roster, and a vacant seat named as vacant |
| | Missouri House District (163) | The Office of Administration's own map of the 2022 House plan + the House's own published member files: name, party, Capitol office, telephone and e-mail address |
| **Schools** | School District (Unified) (445), School District (Elementary) (71) | TIGERweb unified and elementary school districts, which between them tile the whole state; identity only, recorded as a gap |
| **Geography** | County (115) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring, the City of St. Louis among the 115; names the county commission, council or legislature, the county executive where one is elected, and the other elected county officers, from the Secretary of State's Missouri Roster |
| | Township | TIGERweb county subdivisions, with whether the township has a government of its own (20 counties organise townships) |
| | City, Town or Village | TIGERweb incorporated places |
| | ZIP Code | TIGERweb ZCTA, fetched by the state's bounding box and hidden outside Missouri |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it.

**Every county's governing body is named on the County card**: a presiding commissioner and two
district commissioners in most counties, a seven-member commission in Clay, a council and county
executive in St. Louis, St. Charles and Jefferson counties, a legislature and county executive in
Jackson County, and the mayor and the Board of Aldermen's president in the City of St. Louis. The
district LINES the commissioners are elected from are not drawn yet, because no statewide map of
them was found; that is recorded as a gap.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/mo/
```

The gates, generated regions, engine composition and data pipeline are documented in [`mo/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`mo/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory, a seat a chamber shows as vacant says so, and an office the Secretary of State's roster prints as vacant is shown as vacant. The absences are recorded rather than filled in — county commission district lines, city and town officials, township officers, school board members and the City of St. Louis's ward aldermen — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
