<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry New Hampshire

**Every civic district that covers your point in New Hampshire, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, which will serve at **districtry.com/nh/** once it launches — a folder of the consolidated repo, following the Missouri shape rather than a fork.

The national tier and both chambers of the General Court, named from the General Court's own pages:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (2) | U.S. Census TIGERweb boundary, the map the New Hampshire Supreme Court drew in 2022 (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | New Hampshire Senate District (24) | TIGERweb's 2026 state legislative districts (pre-built, a 2,000-point agreement gate and an 8 m fidelity ceiling) + the General Court's own member file, with Open States' export of the General Court's pages when that file cannot be read: name, party, the senator's legislative e-mail address and page |
| | New Hampshire House District (400 seats in 203 districts) | TIGERweb's 164 base districts, drawn in one shared topology with the Senate and congressional maps, each carrying the floterial district drawn over it, measured from NH GRANIT's 2022 House layers + the same roster, every member of the base district and of its floterial named on one card |
| **Schools** | School District (Unified) (81) | TIGERweb unified school districts, from a tile archive; the Census's "School District Not Defined" record, which in New Hampshire covers 15 unincorporated places and a strip of the Atlantic, is answered as no school district; identity and grades only, the school boards recorded as a gap |
| | School District (Elementary) (90) | TIGERweb elementary school districts, from a tile archive |
| | School District (Secondary) (8) | TIGERweb secondary (cooperative high school) districts, from a tile archive, over part of the elementary districts' ground |
| **Geography** | County (10) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; no county official is named yet, and the card says so |
| | City or Town (259) | TIGERweb county subdivisions, from a tile archive: 13 cities, 222 towns and 24 unincorporated places, which the card says have no government of their own; the coastal water record is answered as water |
| | ZIP Code | TIGERweb ZCTA, from a tile archive of the state's ZCTAs, hidden outside New Hampshire |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it. It opens with
the rest of the first batch of the state-level launch, on the operator's own go-ahead.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/nh/
```

The gates, generated regions, engine composition and data pipeline are documented in [`nh/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`nh/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a seat no source names degrades to the district and the General Court's own directory, and a House district listed with fewer members than it elects says how many it lists and on what day. The absences are recorded rather than filled in — county officials, school boards and city and town officials — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
