<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Nevada

**Every civic district that covers your point in Nevada, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, which will serve at **districtry.com/nv/** once it launches — a folder of the consolidated repo, following the Missouri shape rather than a fork.

The national tier and both legislative chambers, named from the Legislature's own pages:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (4) | U.S. Census TIGERweb boundary, the map the Legislature enacted in 2021 (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Nevada Senate District (21) | TIGERweb's 2026 state legislative districts (pre-built, simplified in one topology with the Assembly districts, a 2,000-point agreement gate and an 8 m fidelity ceiling) + the Legislature's own member list: name, party, Carson City room and telephone, the session mailing address, and the senator's e-mail address where the list prints one |
| | Nevada Assembly District (42) | TIGERweb's 2026 state legislative districts, each Senate district exactly two of them + the Legislature's own member list, the same fields |
| **Schools** | School District (17) | TIGERweb unified school districts, from a tile archive; identity only, the trustees recorded as a gap |
| **Geography** | County (16 and Carson City) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; no county official is named yet, and the card says so |
| | City (19) | TIGERweb incorporated places, from a tile archive: 18 cities and Carson City, about 1% of the state's land, so most points are in no city and the card says so |
| | ZIP Code | TIGERweb ZCTA, from a tile archive of the state's ZCTAs, hidden outside Nevada |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it. It opens with
the rest of the first batch of the state-level launch, on the operator's own go-ahead.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/nv/
```

The gates, generated regions, engine composition and data pipeline are documented in [`nv/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`nv/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory. The absences are recorded rather than filled in — county officials, school trustees and city officials — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
