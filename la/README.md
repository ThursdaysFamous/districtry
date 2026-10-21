<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Louisiana

**Every civic district that covers your point in Louisiana, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **[districtry.com/la/](https://districtry.com/la/)** — a folder of the consolidated repo, following the Wisconsin/Iowa shape rather than a fork.

The national tier, each Louisiana chamber's own member pages, and every parish's governing body as the Secretary of State's list of elected officials names it:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (6) | U.S. Census TIGERweb boundary — the 119th Congress's map, which the sitting members were elected from, until 3 January 2027 (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Louisiana Senate District (39) | TIGERweb Legislative boundary — the 2022 plan (pre-built, 2,000-point agreement gate and an 8 m fidelity ceiling) + the Senate's own member list and member pages: name, party, district office and e-mail address, and a vacant seat named as vacant |
| | Louisiana House District (105) | Same boundary pair and the House's own member list and member pages |
| | Police Jury or Council District | The Census's county subdivisions, drawn only in the 6 parishes whose current lines are confirmed, each district joined to its member on the Secretary of State's list |
| **Schools** | School District (69) | TIGERweb unified school districts, which tile the whole state; identity only, recorded as a gap |
| **Geography** | Parish (64) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; names the parish's police jury, council or commission by district, and its parish president or mayor, from the Secretary of State's list of elected officials |
| | City, Town or Village | TIGERweb incorporated places |
| | ZIP Code | TIGERweb ZCTA, fetched by the state's bounding box and hidden outside Louisiana |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it.

**Every parish elects its governing body by district** — 38 police juries, 25 councils and
Caddo's commission — and the Secretary of State's list names every member, so every Parish card
lists its body. The district LINES are the hard part: the Census still carries lines drawn before
the 2020 census in most parishes, so a district is drawn only where its current lines have been
confirmed, and the rest is recorded as a gap.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/la/
```

The gates, generated regions, engine composition and data pipeline are documented in [`la/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`la/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory, a seat a chamber shows as vacant says so, and a seat the Secretary of State's list leaves out is said to be left out rather than called vacant. The absences are recorded rather than filled in — parish district lines in the parishes not yet confirmed, municipal officeholders and school board members — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
