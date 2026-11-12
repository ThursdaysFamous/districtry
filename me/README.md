<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Maine

**Every civic district that covers your point in Maine, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **districtry.com/me/** — a folder of the consolidated repo, following the Missouri shape rather than a fork. It opened with the rest of batch 4, the last batch of the state-level launch.

The national tier, both chambers of the Legislature named from the Legislature's own pages, and the statewide officials line:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (2) | U.S. Census TIGERweb boundary, layer 0 (the same map as layer 4) (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Maine Senate District (35) | TIGERweb's 2026 state legislative districts (pre-built, a 2,000-point agreement gate and an 8 m fidelity ceiling) + the Legislature's own pages, refreshed weekly by CI |
| | Maine House District (151) | TIGERweb's 2026 state legislative districts (pre-built) + the same roster |
| **Schools** | School District (Unified), (Elementary), (Secondary) | TIGERweb school districts, from tile archives; identity and grades only, the school boards recorded as a gap |
| **Geography** | County (16) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; no county official is named yet, and the card says so |
| | Town or City | TIGERweb county subdivisions, from a tile archive; every part of the state's land is in one |
| | ZIP Code | TIGERweb ZCTA, from a tile archive of the state's ZCTAs, hidden outside Maine |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/me/
```

The gates, generated regions, engine composition and data pipeline are documented in [`me/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`me/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a seat no source names degrades to the district and the Legislature's own member list, and a vacant or unlisted seat says so and on what day. The absences are recorded rather than filled in — county officials, municipal officials and school boards — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
