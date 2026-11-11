<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry New Jersey

**Every civic district that covers your point in New Jersey, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, which will serve at **districtry.com/nj/** once it launches — a folder of the consolidated repo, following the Missouri shape rather than a fork.

The national tier and both legislative chambers, named from the Legislature's own roster:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (12) | U.S. Census TIGERweb boundary, the map the New Jersey Redistricting Commission drew in December 2021 (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | New Jersey Senate District (40) | TIGERweb's 2026 state legislative districts (pre-built, a 2,000-point agreement gate and an 8 m fidelity ceiling) + the Legislature's own roster: name, party, the senator's legislative e-mail address and main district office |
| | New Jersey Assembly District (40) | The same 40 districts, drawn from the same file, because New Jersey elects one senator and two members of the General Assembly from each + the same roster, both members named on one card |
| **Schools** | School District (Unified) (341) | TIGERweb unified school districts, from a tile archive; the Census's "School District Not Defined" record, which in New Jersey is coastal and bay water, is answered as water; identity and grades only, the boards of education recorded as a gap |
| | School District (Elementary) (168) | TIGERweb elementary school districts, from a tile archive |
| | School District (Secondary) (45) | TIGERweb secondary (regional high school) districts, from a tile archive, over the elementary districts' ground |
| **Geography** | County (21) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; no county official is named yet, and the card says so |
| | Municipality (564) | TIGERweb county subdivisions, from a tile archive: every part of New Jersey's land is in one borough, township, city, town or village (or Princeton); the coastal water records are answered as water |
| | ZIP Code | TIGERweb ZCTA, from a tile archive of the state's ZCTAs, hidden outside New Jersey |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it. It opens with
the rest of the first batch of the state-level launch, on the operator's own go-ahead.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/nj/
```

The gates, generated regions, engine composition and data pipeline are documented in [`nj/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`nj/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory. The absences are recorded rather than filled in — county officials, boards of education and municipal officials — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
