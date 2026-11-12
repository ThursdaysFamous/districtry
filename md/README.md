<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Maryland

**Every civic district that covers your point in Maryland, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **districtry.com/md/** — a folder of the consolidated repo, following the Missouri shape rather than a fork. It opened with the rest of batch 3 of the state-level launch.

The national tier, both chambers of the General Assembly named from its own data, and the statewide officials line:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (8) | U.S. Census TIGERweb boundary, layer 0 (the same map as layer 4) (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Maryland Senate District (47) | TIGERweb's 2026 state legislative districts (pre-built, a 2,000-point agreement gate and an 8 m fidelity ceiling) + the General Assembly's own member pages, refreshed weekly by CI |
| | Maryland House of Delegates District (141 delegates in 71 districts and subdistricts) | TIGERweb's 71 lower-house units, drawn in one shared topology with the Senate map + the same roster, every delegate of the unit named on one card |
| **Schools** | School District (Unified) | TIGERweb unified school districts, from a tile archive; identity and grades only, the school boards recorded as a gap |
| **Geography** | County (24) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; no county official is named yet, and the card says so |
| | City, Town or Village | TIGERweb incorporated places, from a tile archive; most of the state is in none, and an empty card says the county governs there |
| | ZIP Code | TIGERweb ZCTA, from a tile archive of the state's ZCTAs, hidden outside Maryland |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/md/
```

The gates, generated regions, engine composition and data pipeline are documented in [`md/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`md/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a seat no source names degrades to the district and the General Assembly's own member list, and a vacant or unlisted seat says so and on what day. The absences are recorded rather than filled in — county officials, school boards and municipal officials — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
