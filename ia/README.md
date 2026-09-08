<!-- ==== GENERATED:BEGIN metro-header ==== -->
# districtry Iowa

**Every civic district that covers your point in Iowa, and who represents you there.**
<!-- ==== GENERATED:END metro-header ==== -->

A single-file, dependency-light web app: one `index.html`, Leaflet for the map, no build step, no framework, no server-side code. One instance of the [districtry](https://districtry.com/) fleet, serving at **[districtry.com/ia/](https://districtry.com/ia/)** — following Wisconsin's shape as a folder of the consolidated repo rather than a fork.

Four layers, the national tier every U.S. state can serve from national publishers:

| Group | Layer | Source |
|---|---|---|
| **Political** | U.S. House District | U.S. Census TIGERweb boundary (pre-built, shipped with the app) + the public-domain [congress-legislators](https://github.com/unitedstates/congress-legislators) roster, refreshed weekly by CI |
| | Iowa Senate District (50) | TIGERweb Legislative boundary (pre-built, 2,000-point agreement gate) + the [Open States](https://openstates.org) roster enriched with each member's Capitol phone/e-mail from their own legis.iowa.gov profile page, refreshed weekly by CI |
| | Iowa House District (100) | Same pair as the Senate — boundary pre-built, roster from Open States + legis.iowa.gov |
| **Geography** | County | TIGERweb State_County, pre-built — the app's offline anchor; identity-only, since no statewide roster of county officers exists yet |

This is the national tier only — the first PR of a longer phased plan
([`docs/IA_EXPANSION_PLAN.md`](../docs/IA_EXPANSION_PLAN.md)). The flagship layer this instance
is building toward is a statewide county-supervisor fabric (Iowa's Legislature publishes
supervisor districts for all 99 counties with each county's own election-plan type in-band —
a state-publisher layer Wisconsin didn't have an analog for at its own launch), followed by
precincts, judicial districts, community colleges, and city tiers for Des Moines and Cedar
Rapids. What no publisher answers is recorded in the app's Data gaps panel rather than papered
over, following the repo's [`docs/EXPANSION_GUIDE.md`](../docs/EXPANSION_GUIDE.md).

## Running it

```bash
# From the repo root — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ia/
```

The gates, generated regions, engine composition and data pipeline are documented in [`ia/CLAUDE.md`](CLAUDE.md); the fleet-wide architecture in the repo root's [`CLAUDE.md`](../CLAUDE.md).

## Honesty rules

Officeholder data is never guessed: a vacant or unsourced seat degrades to the district number and the official body's own directory. Every layer will carry a provenance row on sources.html once that page exists (a later PR); what the app *cannot* answer is recorded in its Data gaps panel rather than papered over. Not for legal or official use.
