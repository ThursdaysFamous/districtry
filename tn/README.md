<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Tennessee

**Every civic district that covers your point in Tennessee, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **[districtry.com/tn/](https://districtry.com/tn/)** — a folder of the consolidated repo, following the statewide shape rather than a fork.

Twelve layers, the national tier every U.S. state can serve from national publishers, with the legislators' names taken from the Legislature's own map:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (9) | U.S. Census TIGERweb boundary of the 119th Congress (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Tennessee Senate District (33) | TIGERweb Legislative boundary (pre-built, 2,000-point agreement gate) + each member's name and any vacancy from the Tennessee Legislature's district map on TNMap, with party, e-mail and the member's own page from [Open States](https://openstates.org) where the two agree |
| | Tennessee House District (99) | Same boundary pair and the same two roster sources |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| **Schools** | School District (Unified) (127), School District (Elementary) (15), School District (Secondary) (15) | TIGERweb School districts; fifteen cities run their own elementary schools beside the county's high schools, so all three tilings ship. Identity only, recorded as a gap |
| **Geography** | County (95) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring |
| | City or Town | TIGERweb incorporated places, including the three consolidated city-county governments |
| | ZIP Code | TIGERweb ZCTA, fetched by the state's bounding box and hidden outside Tennessee |
| | Post Office | USGS National Map structures, nearest-N |

The congressional map is the one the sitting members were elected from. Tennessee redrew its districts in 2026, and the new map takes effect on 3 January 2027; the builder refuses to keep drawing the old one after that date.

This is the national tier only — the first PR of a phased bring-up, and the instance is **dark**
while it lands: it has no `metros.json` entry and its folder is excluded from the Pages deploy,
so nothing is served and no landing card names it.

**The flagship layer this instance is building toward is the county commission.** Every county
outside the three consolidated governments elects its commission from districts, and the
state Comptroller publishes those districts statewide. There is no township or civil-district
layer: the 855 county subdivisions the Census carries for Tennessee are civil districts with no
functioning government.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/tn/
```

The gates, generated regions, engine composition and data pipeline are documented in [`tn/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`tn/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory, and a seat the Legislature lists as vacant says so with the date it was read. Three absences are recorded rather than filled in — county commission districts, municipal officeholders and school board members — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
