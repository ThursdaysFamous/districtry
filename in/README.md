<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Indiana

**Every civic district that covers your point in Indiana, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **[districtry.com/in/](https://districtry.com/in/)** — a folder of the consolidated repo, following the Wisconsin/Iowa shape rather than a fork.

Eleven layers, all from national publishers, in three groups:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (9) | U.S. Census TIGERweb boundary (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Indiana Senate District (50) | TIGERweb Legislative boundary (pre-built, 2,000-point agreement gate). **No roster** — the card gives the district and the General Assembly's own directory |
| | Indiana House District (100) | Same boundary pair, same absence of a roster |
| **Schools** | School District (Unified) (291) | TIGERweb School layer 0, live |
| **Geography** | County (92) | TIGERweb State_County, pre-built — the app's offline anchor; identity-only, and the card says so |
| | Township or City (1,012) | TIGERweb county subdivisions, live |
| | City or Town (566) | TIGERweb incorporated places, live |
| | ZIP Code (882) | TIGERweb ZCTA, live |
| **Public Safety** | Police Station, Fire Station, Post Office | USGS National Map structures, live — nearest-3 proximity layers |

**Indiana ships ONE school layer, not two.** TIGERweb's elementary and secondary school layers
both return zero features for Indiana, so those are recorded drops rather than empty toggles.
**No county body is drawn yet**, and that is the largest recorded gap: an Indiana county is run
by two elected bodies — a board of commissioners and a county council — each on its own district
lines, and neither has shipped. What no publisher answers is recorded in the app's Data gaps
panel rather than papered over, following the repo's
[`docs/EXPANSION_GUIDE.md`](../docs/EXPANSION_GUIDE.md).

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/in/
```

The gates, generated regions, engine composition and data pipeline are documented in [`in/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md).

## Honesty rules

Officeholder data is never guessed. This instance names exactly one class of officeholder — the
state's nine U.S. Representatives — and every other card says plainly what it does not name: the
county card that no county body is drawn, both chamber cards that no General Assembly roster
ships here, the township, municipal and school cards that no statewide roster of those officers
was found. Every layer carries a provenance row on [sources.html](sources.html); what the app
*cannot* answer is recorded in its Data gaps panel. Not for legal or official use.
