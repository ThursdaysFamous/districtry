<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Oklahoma

**Every civic district that covers your point in Oklahoma, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **[districtry.com/ok/](https://districtry.com/ok/)** — a folder of the consolidated repo, following the Wisconsin/Iowa shape rather than a fork.

Eleven layers, the national tier every U.S. state can serve from national publishers:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (5) | U.S. Census TIGERweb boundary (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Oklahoma Senate District (48) | TIGERweb Legislative boundary (pre-built, 2,000-point agreement gate) + the [Open States](https://openstates.org) roster: name, party, e-mail and the member's own page |
| | Oklahoma House District (101) | Same boundary pair and the same roster |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| **Schools** | School District (Unified) (415), School District (Elementary) (91) | TIGERweb School districts — the two layers cover the state between them; identity only, recorded as a gap |
| **Geography** | County (77) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring |
| | City or Town | TIGERweb incorporated places |
| | ZIP Code | TIGERweb ZCTA, fetched by the state's bounding box and hidden outside Oklahoma |
| | Post Office | USGS National Map structures, nearest-N |

This is the national tier only — the first PR of a phased bring-up, and the instance is **dark**
while it lands: it has no `metros.json` entry and its folder is excluded from the Pages deploy,
so nothing is served and no landing card names it.

**The flagship layer this instance is building toward is `county-commissioner`.** Every
Oklahoma county elects three commissioners from three districts (19 O.S. 321), so there is no
at-large county to tell apart, and the state transport department publishes all 231 districts
in one statewide file. There is no township layer: every county subdivision the Census carries
for Oklahoma is a census county division, a statistical area that governs nobody.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ok/
```

The gates, generated regions, engine composition and data pipeline are documented in [`ok/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`ok/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory. Four absences are recorded rather than filled in — county commissioner districts, municipal officeholders, school board members and tribal governments — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
