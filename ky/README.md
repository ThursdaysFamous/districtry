<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Kentucky

**Every civic district that covers your point in Kentucky, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **districtry.com/ky/** — a folder of the consolidated repo rather than a fork.

**Not published yet.** This instance arrived dark: `ky/**` is excluded from the Pages deploy and `metros.json` carries no `ky` entry, so nothing here is reachable by a reader. [`ky/WATCH.md`](WATCH.md) lists what the publishing change has to carry.

Four layers, the national tier every U.S. state can serve from national publishers:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (6) | U.S. Census TIGERweb boundary (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Kentucky Senate District (38) | TIGERweb Legislative boundary, pre-built in one shared mapshaper topology with the other two chambers (2,000-point agreement gate, exact shared-state-border gate, measured fidelity ceiling). **Names no member yet** — the card gives the district and the Senate's own directory |
| | Kentucky House District (100) | Same build as the Senate. The two chambers do NOT nest — 100 House districts stand in no whole-number relation to 38 Senate districts — so what the builder holds exactly across the three layers is the state border they all draw. **Names no member yet** |
| **Geography** | County (120) | TIGERweb State_County, pre-built — the app's offline anchor. Identity only: the state publishes every county's elected officials but pairs none of them with a district, so the card names the county and links the state directory rather than inventing a name |

This is the national tier only — the first PR of a longer plan. **The flagship layer this instance is building toward is the fiscal court**, the body that governs 118 of Kentucky's 120 counties. Its form was censused before this instance shipped, from two certified elections per county: 105 counties elect magistrates from magisterial districts, 13 elect three commissioners, and Jefferson and Fayette are merged city-county governments with no fiscal court at all. What is missing is boundaries — 27 counties publish them, which is a floor rather than a total — and the join between a published official and a district, which no source carries. What no publisher answers is recorded in the app's Data gaps panel rather than papered over, following the repo's [`docs/EXPANSION_GUIDE.md`](../docs/EXPANSION_GUIDE.md).

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ky/
```

The gates, generated regions, engine composition and data pipeline are documented in [`ky/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory, which is the path three of this instance's four cards take today. What the app *cannot* answer is recorded in its Data gaps panel rather than papered over. Not for legal or official use.
