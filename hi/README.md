<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Hawaii

**Every civic district that covers your point in Hawaii, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **districtry.com/hi/** — a folder of the consolidated repo, following the Missouri shape rather than a fork. It opened with the rest of batch 4, the last batch of the state-level launch.

The national tier, both chambers of the Legislature named from Open States' export, because the Legislature's own site blocks this project's client, and the statewide officials line:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (2) | U.S. Census TIGERweb boundary, layer 0 (the same map as layer 4) (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Hawaii Senate District (25) | TIGERweb's 2026 state legislative districts (pre-built, a 2,000-point agreement gate and an 8 m fidelity ceiling) + Open States' export, because the Legislature's own site blocks this project's client, refreshed weekly by CI |
| | Hawaii House District (51) | TIGERweb's 2026 state legislative districts (pre-built) + the same roster |
| **Schools** | School District | TIGERweb's one unified district for Hawaii, the Department of Education, from a tile archive; its Board of Education is appointed, so no school board is elected and the card says so |
| **Geography** | County (5) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; the five counties are Hawaii's only local governments; no mayor or council member is named yet, and the card says so |
| | ZIP Code | TIGERweb ZCTA, from a tile archive of the state's ZCTAs, hidden outside Hawaii |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/hi/
```

The gates, generated regions, engine composition and data pipeline are documented in [`hi/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`hi/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a seat no source names degrades to the district and the Legislature's own member list, and a vacant or unlisted seat says so and on what day. The absences are recorded rather than filled in — county mayors and councils — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
