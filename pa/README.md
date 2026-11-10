<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Pennsylvania

**Every civic district that covers your point in Pennsylvania, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, which will serve at **districtry.com/pa/** once it launches — a folder of the consolidated repo, following the Missouri shape rather than a fork.

The national tier and both legislative chambers, named from the General Assembly's own pages:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (17) | U.S. Census TIGERweb boundary, the map the Supreme Court of Pennsylvania drew in 2022 (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Pennsylvania Senate District (50) | TIGERweb's 2026 state legislative districts (pre-built, 2,000-point agreement gate and an 8 m fidelity ceiling) + the General Assembly's own member pages: name, party, Capitol office and telephone, and the senator's e-mail address where the Senate prints one |
| | Pennsylvania House District (203) | TIGERweb's 2026 state legislative districts + the General Assembly's own member pages: name, party, Capitol office and telephone |
| **Schools** | School District (501) | TIGERweb unified school districts, from a tile archive; identity only, the board members recorded as a gap |
| **Geography** | County (67) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; no county official is named yet, and the card says so |
| | City, Borough or Township (2,568) | TIGERweb county subdivisions, from a tile archive: every part of Pennsylvania's land is in one municipality |
| | ZIP Code | TIGERweb ZCTA, from a tile archive of the state's ZCTAs, hidden outside Pennsylvania |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it. It opens with
the rest of the first batch of the state-level launch, on the operator's own go-ahead.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/pa/
```

The gates, generated regions, engine composition and data pipeline are documented in [`pa/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`pa/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory. The absences are recorded rather than filled in — county officials, school board members and municipal officials — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
