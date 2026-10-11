<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry South Carolina

**Every civic district that covers your point in South Carolina, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **[districtry.com/sc/](https://districtry.com/sc/)** — a folder of the consolidated repo, following the Wisconsin/Iowa shape rather than a fork.

Ten layers, the national tier plus the General Assembly's own member lists:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (7) | U.S. Census TIGERweb boundary (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | South Carolina Senate District (46) | TIGERweb Legislative boundary (pre-built, 2,000-point agreement gate and a 25 m fidelity ceiling) + the General Assembly's own chamber list and member pages: name, party, State House office, business telephone and the member's own page |
| | South Carolina House District (124) | Same boundary pair and the same roster source |
| **Safety** | Police Station, Fire & EMS Station | USGS National Map structures, nearest-N by straight-line distance |
| **Schools** | School District (72) | TIGERweb unified school districts, which tile the whole state; identity only, recorded as a gap |
| **Geography** | County (46) | TIGERweb State_County, pre-built — the app's offline anchor and the coverage ring |
| | City or Town | TIGERweb incorporated places |
| | ZIP Code | TIGERweb ZCTA, fetched by the state's bounding box and hidden outside South Carolina |
| | Post Office | USGS National Map structures, nearest-N |

This is the first PR of a phased bring-up, and the instance is **dark** while it lands: it has
no `metros.json` entry and its folder is excluded from the Pages deploy, so nothing is served
and no landing card names it.

**The flagship layer this instance is building toward is `county-council`.** Every South
Carolina county has been governed by an elected council since the Home Rule Act of 1975; the
state's Revenue and Fiscal Affairs Office publishes the council districts and the State Election
Commission's certified results name the members. There is no township layer: every county
subdivision the Census carries for South Carolina is a census county division, a statistical
area that governs nobody.

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/sc/
```

The gates, generated regions, engine composition and data pipeline are documented in [`sc/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md). Measurements this instance has taken but not yet acted on are in [`sc/WATCH.md`](WATCH.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory. Four absences are recorded rather than filled in — county council districts and members, municipal officeholders, school board members and tribal governments — each with what is missing, why, and what would close it. Every layer carries a provenance row on [sources.html](sources.html). Not for legal or official use.
