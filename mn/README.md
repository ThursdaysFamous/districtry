<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Minnesota

**Every civic district that covers your point in Minnesota, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **districtry.com/mn/** — following Wisconsin's shape as a folder of the consolidated repo rather than a fork.

**Not published yet.** This instance arrived dark: `mn/**` is excluded from the Pages deploy and `metros.json` carries no `mn` entry, so nothing here is reachable by a reader. `mn/WATCH.md` lists what the publishing change has to carry.

Four layers, the national tier every U.S. state can serve from national publishers:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (8) | U.S. Census TIGERweb boundary (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Minnesota Senate District (67) | TIGERweb Legislative boundary, pre-built in one shared mapshaper topology with the other two chambers (2,000-point agreement gate, exact nesting gate, measured fidelity ceiling). **Names no member yet** — the card gives the district and the Senate's own directory |
| | Minnesota House District (134) | Same build as the Senate. Minnesota numbers its House districts by letter, so Senate 61 holds 61A and 61B. **Names no member yet** |
| **Geography** | County (87) | TIGERweb State_County, pre-built — the app's offline anchor. Identity only: no statewide roster of Minnesota county officers exists, so the card names the county and links the county directory rather than inventing a name |

This is the national tier only — the first PR of a longer plan. **The flagship layer this instance is building toward is `county-commissioner`**: the Minnesota Secretary of State publishes one statewide precinct layer in which every precinct carries the districts it sits in as attributes, so all 447 commissioner districts in all 87 counties dissolve out of a single source (measured 2026-09-29), along with precincts, judicial, soil & water conservation, hospital, park and ward districts. It does not ship here because no publisher names the commissioners; the operator ruled on 2026-09-29 that go-live does not wait for them. What no publisher answers is recorded in the app's Data gaps panel rather than papered over, following the repo's [`docs/EXPANSION_GUIDE.md`](../docs/EXPANSION_GUIDE.md).

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/mn/
```

The gates, generated regions, engine composition and data pipeline are documented in [`mn/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory, which is the path three of this instance's four cards take today. What the app *cannot* answer is recorded in its Data gaps panel rather than papered over. Not for legal or official use.
