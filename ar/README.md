<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Arkansas

**Every civic district that covers your point in Arkansas, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **[districtry.com/ar/](https://districtry.com/ar/)** — a folder of the consolidated repo, following the Wisconsin/Iowa shape rather than a fork.

Eleven layers, the national tier plus the Arkansas State Legislature's own member list and every county's quorum court:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (4) | U.S. Census TIGERweb boundary (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Arkansas Senate District (35) | TIGERweb Legislative boundary (pre-built, 2,000-point agreement gate and a 25 m fidelity ceiling) + the legislature's own member list and member pages: name, party, e-mail and the member's own page, and a vacant seat named as vacant with the reason |
| | Arkansas House District (100) | Same boundary pair and the same roster source |
| | Quorum Court District (775) | The state's own map of every county's justice of the peace districts (pre-built, Douglas-Peucker under a 25 m ceiling, each county's districts held to cover that county); the justice is named only where the county's own site says who sits for which district |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| **Schools** | School District (234) | TIGERweb unified school districts, which tile the whole state; identity only, recorded as a gap |
| **Geography** | County (75) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; names the county judge (the state courts' directory, checked against the Association of Arkansas Counties) and lists the county's justices of the peace as the association prints them, credited and dated |
| | City or Town | TIGERweb incorporated places |
| | ZIP Code | TIGERweb ZCTA, fetched by the state's bounding box and hidden outside Arkansas |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it.

**The flagship layer is the quorum court.** Every Arkansas county elects a county judge and a
quorum court of justices of the peace, each from a district. The state's mapping office draws all
775 districts and the state courts' directory names the 75 county judges; no government names the
justices, and the Association of Arkansas Counties lists them without saying who sits for which
district. So the justice is named by district only where the county's own site says, and
elsewhere the County card carries the association's list, credited and dated (Adam's ruling,
2026-10-13). Every one of those seats is on the 3 November 2026 ballot with new terms from
1 January 2027, and every county is read again in January. There is no township layer: every
county subdivision the Census carries for Arkansas is a nonfunctioning legal entity.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ar/
```

The gates, generated regions, engine composition and data pipeline are documented in [`ar/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`ar/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory, and a seat whose member has resigned or died says so. Three absences are recorded rather than filled in — which justice of the peace sits for which district, municipal officeholders and school board members — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
