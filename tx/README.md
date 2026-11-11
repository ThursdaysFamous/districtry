<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Texas

**Every civic district that covers your point in Texas, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, which will serve at **districtry.com/tx/** once it launches — a folder of the consolidated repo, following the Missouri shape rather than a fork.

The national tier and both legislative chambers, named from each chamber's own pages:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (38) | U.S. Census TIGERweb boundary, the map the sitting members were elected from (the 119th Congress's, until 3 January 2027; pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI, with a seat the House Clerk lists as vacant shown as vacant |
| | Texas Senate District (31) | TIGERweb's 2026 state legislative districts (pre-built, Douglas-Peucker under an 8 m fidelity ceiling and a 2,000-point agreement gate) + the Senate's own member list and member pages: name, party, Capitol office and telephone |
| | Texas House District (150) | TIGERweb's 2026 state legislative districts + the House's own member list and member pages: name, Capitol room and telephone (the House prints no party) |
| **Schools** | School District (1,016 unified, 1 elementary, 1 secondary) | TIGERweb school districts, from tile archives; identity only, the trustees recorded as a gap |
| **Geography** | County (254) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; no county official is named yet, and the card says so |
| | City, Town or Village (1,230) | TIGERweb incorporated places, from a tile archive: 978 cities, 230 towns and 22 villages, about 4.5% of the state's land, so most points are in none and the card says so |
| | ZIP Code | TIGERweb ZCTA, from a tile archive of the state's ZCTAs, hidden outside Texas |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it. It opens with
the rest of the second batch of the state-level launch, on the operator's own go-ahead.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/tx/
```

The gates, generated regions, engine composition and data pipeline are documented in [`tx/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`tx/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory. The absences are recorded rather than filled in — county officials, school trustees and city officials — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
