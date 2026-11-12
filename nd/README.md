<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry North Dakota

**Every civic district that covers your point in North Dakota, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **districtry.com/nd/** — a folder of the consolidated repo, following the Missouri shape rather than a fork. It opened with the rest of batch 4, the last batch of the state-level launch.

The national tier, both chambers of the Legislative Assembly named from the Legislative Branch's own member pages, and the statewide officials line:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (at large) | U.S. Census TIGERweb boundary, layer 0, the whole state (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | North Dakota Senate District (47) | TIGERweb's 2026 state legislative districts (pre-built, a 2,000-point agreement gate and an 8 m fidelity ceiling) + the Legislative Branch's own member pages, refreshed weekly by CI |
| | North Dakota House District (48: 46 districts electing two and the subdistricts 4A and 4B) | TIGERweb, inside the Senate districts and drawn in one shared topology with them + the same roster |
| **Schools** | School District (Unified), (Elementary) | TIGERweb school districts, from tile archives; identity and grades only, the school boards recorded as a gap |
| **Geography** | County (53) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; no county official is named yet, and the card says so |
| | City | TIGERweb incorporated places, from a tile archive; most of the state is in none, and an empty card says so |
| | ZIP Code | TIGERweb ZCTA, from a tile archive of the state's ZCTAs, hidden outside North Dakota |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/nd/
```

The gates, generated regions, engine composition and data pipeline are documented in [`nd/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`nd/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a seat no source names degrades to the district and the Legislative Assembly's own member list, and a vacant or unlisted seat says so and on what day. The absences are recorded rather than filled in — county officials, municipal officials and school boards — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
