<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Washington

**Every civic district that covers your point in Washington, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, which will serve at **districtry.com/wa/** once it launches — a folder of the consolidated repo, following the Missouri shape rather than a fork.

The national tier and both legislative chambers, named from the Legislature's own pages:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (10) | U.S. Census TIGERweb boundary, the map drawn after the 2020 census (layer 0, the same map as the 119th Congress's layer 4; pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI, with a seat the House Clerk lists as vacant shown as vacant |
| | Washington Senate District (49) | TIGERweb's 2026 state legislative districts, one file for both chambers because each district elects one senator and two representatives (pre-built, Douglas-Peucker under an 8 m fidelity ceiling and a 2,000-point agreement gate) + the Legislature's own member list and member pages: name, party, Olympia office and telephone |
| | Washington House District (49 districts, 98 seats) | The same file + the same member list and pages, both representatives of each district by position (the Legislature prints no e-mail address, only a form) |
| **Schools** | School District (295) | TIGERweb unified school districts, from a tile archive; identity only, the school board members recorded as a gap |
| **Geography** | County (39) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring; no county official is named yet, and the card says so |
| | City or Town (281) | TIGERweb incorporated places, from a tile archive: 212 cities and 69 towns, about 2.6% of the state's land, so most points are in none and the card says the county governs there |
| | ZIP Code | TIGERweb ZCTA, from a tile archive of the state's ZCTAs, hidden outside Washington |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| | Post Office | USGS National Map structures, nearest-N |

The instance is **dark** while it is built: it has no `metros.json` entry and its folder is
excluded from the Pages deploy, so nothing is served and no landing card names it. It opens with
the rest of the second batch of the state-level launch, on the operator's own go-ahead.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/wa/
```

The gates, generated regions, engine composition and data pipeline are documented in [`wa/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`wa/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory. The absences are recorded rather than filled in — county officials, school board members, and city and town officials — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
