<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Michigan

**Every civic district that covers your point in Michigan, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **[districtry.com/mi/](https://districtry.com/mi/)** — a folder of the consolidated repo, following the Wisconsin/Iowa shape rather than a fork.

Four layers, the national tier every U.S. state can serve from national publishers:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District (13) | U.S. Census TIGERweb boundary (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Michigan Senate District (38) | TIGERweb Legislative boundary (pre-built, 2,000-point agreement gate) + the [Open States](https://openstates.org) roster, enriched with each senator's Capitol phone, office and contact page from the Senate's own all-senators directory, refreshed weekly by CI |
| | Michigan House District (110) | Same boundary pair; roster from Open States alone — no capitol contact block, because no source this instance can reach publishes one (see below) |
| **Geography** | County (83) | TIGERweb State_County, pre-built — the app's offline anchor; identity-only, and the card says so |

This is the national tier only — the first PR of a longer phased plan
([`docs/MI_EXPANSION_PLAN.md`](../docs/MI_EXPANSION_PLAN.md)). **The flagship layer this
instance is building toward is `county-commissioner`**, and it is why Michigan was picked as
the fleet's sixth state: the Bureau of Elections publishes every county's commissioner
districts as ONE statewide layer, compiled from the filings MCL 46.404/46.405 requires — the
Wisconsin LTSB shape rather than the Illinois county-by-county grind — and the same records
carry each commissioner's name and party. What no publisher answers is recorded in the app's
Data gaps panel rather than papered over, following the repo's
[`docs/EXPANSION_GUIDE.md`](../docs/EXPANSION_GUIDE.md).

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/mi/
```

The gates, generated regions, engine composition and data pipeline are documented in [`mi/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory. The county card names the county and states plainly that it does not yet name the board of commissioners, rather than leaving a reader to wonder. The Michigan House card ships no capitol contact block because no source this instance can reach publishes one — Open States carries none for any Michigan legislator (measured 0 of 148), and `house.mi.gov` could not be reached from the build environment at all. Every layer carries a provenance row on [sources.html](sources.html); what the app *cannot* answer is recorded in its Data gaps panel. Not for legal or official use.
