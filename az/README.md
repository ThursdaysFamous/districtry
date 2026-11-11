<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Arizona

**Every civic district that covers your point in Arizona, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, which will serve at **districtry.com/az/** once it launches — a folder of the consolidated repo, following the Missouri shape rather than a fork.

The national tier and both legislative chambers, named from the Legislature's own rosters:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (9) | U.S. Census TIGERweb boundary, the map the Independent Redistricting Commission drew after the 2020 census (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Arizona Senate District (30) | TIGERweb's 2026 state legislative districts (pre-built, a 2,000-point agreement gate and an 8 m fidelity ceiling) + the Legislature's own Senate roster: name, party, Capitol room and telephone, and the senator's e-mail address |
| | Arizona House District (30) | The same 30 districts, drawn from the same file, because Arizona elects one senator and two representatives from each + the Legislature's own House roster, both representatives named on one card |
| **Schools** | School District (Unified) (97) | TIGERweb unified school districts, from a tile archive, plus the Census's "School District Not Defined" placeholder, which the card names as no district; identity and grades only, the governing boards recorded as a gap |
| | School District (Elementary) (102) | TIGERweb elementary school districts, from a tile archive |
| | School District (Secondary) (15) | TIGERweb union high school districts, from a tile archive, over the elementary districts' ground |
| **Geography** | County (15) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; no county official is named yet, and the card says so |
| | City or Town (92) | TIGERweb incorporated places, from a tile archive; most of the state's land is in no city or town, and the card says so |
| | ZIP Code | TIGERweb ZCTA, from a tile archive of the state's ZCTAs, hidden outside Arizona |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it. It opens with
the rest of the first batch of the state-level launch, on the operator's own go-ahead.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/az/
```

The gates, generated regions, engine composition and data pipeline are documented in [`az/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`az/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory. The absences are recorded rather than filled in — county officials, school governing boards and city and town officials — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
