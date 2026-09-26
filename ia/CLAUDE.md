# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Iowa: a single-file, dependency-light web app. Click a point in Iowa (or search an
address) and it reports every civic district containing that point and who represents you
there. It serves at **districtry.com/ia/** as a folder of the consolidated districtry repo —
following Wisconsin's shape (the second state to expand in place, `docs/EXPANSION_GUIDE.md`
names Wisconsin the worked example for state N+1). It ships four layers, the national tier
every U.S. state can serve from national publishers: **County** (99, from Census TIGERweb,
identity-only — no statewide roster of county officers exists yet, a later expansion tracked
in `docs/IA_EXPANSION_PLAN.md`), **U.S. House** (4 districts, TIGERweb geometry joined to the
public-domain unitedstates/congress-legislators roster, refreshed weekly), and **Iowa Senate**
/ **Iowa House** (50 and 100 districts, TIGERweb geometry joined to Open States' current-people
export, enriched with each member's Capitol phone and e-mail scraped from their own
legis.iowa.gov profile page — the state's own site publishes no district-office address at
all, unlike Wisconsin's, so the card's office group is Capitol contact only). **THE FLAGSHIP
LAYER THIS INSTANCE IS BUILT TOWARD IS `county-supervisor`**: unlike Wisconsin's launch, which
had one state-publisher layer to lean on (LTSB's county-supervisory aggregate), Iowa's
Legislature runs an entire ArcGIS organization publishing precincts, polling places, school
director districts, and — the concept this instance's next PR ships — county supervisor
districts for all 99 counties with each county's own election-plan type (at-large, residence,
or single-member district) carried in the layer's own `PLANTYPE` field. That layer's own
vintage (measured 2024-01-30) already trails **Senate File 75** (signed 2025-04-11), which
forces Story, Johnson and Black Hawk counties from at-large to district elections for November
2026 — the first thing a `county-supervisor` build has to reconcile, and the reason it did not
ship in this instance's first PR alongside the four simpler layers. Everything beyond these
four is this instance's growth per `docs/IA_EXPANSION_PLAN.md`'s phased plan, which itself
follows `docs/EXPANSION_GUIDE.md` Part 2 (a new state instance) and Part 3 (deepening one).

**There is no build step, no framework, and no server-side code.** The app — styles, engine,
and layer modules — lives inline in `index.html`. `sw.js` is the service worker;
`data/app/*.json` are runtime-fetched data files; `data/state/` carries the bootstrap state
config (`build_congress_roster.py` reads its FIPS/USPS/seat count — it ships in the repo and
is excluded from the Pages deploy). `sources.html` will carry the generated per-layer
provenance matrix and `faq.html` the common questions once those pages exist (they compose
from the same shared engine blocks as every other instance via `scripts/compose_app.py`).

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: Iowa (`iowa`) — https://districtry.com/ia/
- Geocoders: address Photon (Iowa-bounded type-ahead); unbounded Photon (whole-coverage, sibling-metro lookup); POI Nominatim (office-address pin lookup, Iowa-bounded, serial >=1s queue)
- Ground truth: 42.04940,-92.90710 (downtown Marshalltown, Marshall County) → county Marshall County; us-house 4; ia-senate 26; ia-house 52; county-supervisor At-large; school-district-unified Marshalltown Community School District. Negative point 43.65000,-93.37000 (inside Minnesota (near Albert Lea), north of the Iowa land border (~43.50) and inside permalink_gate's maxLat (43.70) so the point is still selectable).
- Layers: 20 registered (political 7, safety 2, schools 6, geography 5); `registerLayer(` floor 14. Debug namespace `window.IowaExplorer`.
- Scheduled workflows: `update-ia-congress-roster.yml` (Mon 14:30 UTC); `update-ia-legislature-roster.yml` (Tue 14:30 UTC); `update-ia-county-auditor-roster.yml` (Wed 14:30 UTC); `update-ia-judicial-district-roster.yml` (Thu 16:30 UTC); `update-ia-dsm-council-roster.yml` (Thu 17:30 UTC); `update-ia-county-officers-roster.yml` (Fri 17:30 UTC); `update-ia-supervisor-roster.yml` (Sat 17:30 UTC); `update-ia-city-contact-roster.yml` (Fri 15:30 UTC); `update-ia-waterloo-council-roster.yml` (Thu 18:30 UTC); `update-ia-cedar-rapids-council-roster.yml` (Thu 19:30 UTC); `update-ia-city-officials-roster.yml` (Fri 16:30 UTC); `update-ia-county-chair-roster.yml` (Fri 18:30 UTC); `update-ia-county-city-officials-roster.yml` (Thu 20:30 UTC); `ia-validate-sources.yml` (1st of month 15:00 UTC).
- Source registry: `ia/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ia/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ia/ node ia/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ia/scripts/validate_index.py ia/index.html

# Generated-region gate: per-instance facts live ONCE in ia/metro-worksheet.json;
# GENERATED regions are emitted from it. NEVER hand-edit a GENERATED region:
pip install -c scripts/requirements.txt jsonschema
python3 scripts/generate_metro_files.py            # regenerate in place (all instances)
python3 scripts/generate_metro_files.py --check    # the CI drift gate

# Engine parity: the ENGINE fences are composed from the repo-root engine/ —
# edit a block THERE and recompose, never inside an instance file:
python3 scripts/compose_app.py            # splice engine/ into every instance
python3 scripts/compose_app.py --check    # the CI drift gate
```

**Sandboxed environments (Claude Code web):** the headless browser cannot reach the Leaflet
CDN. The repo root's `.claude/settings.json` SessionStart hook runs `scripts/vendor_leaflet.sh`,
which vendors Leaflet into `ia/scripts/vendor/leaflet/` (gitignored); `ia/scripts/smoke_test.mjs`
serves it same-origin. Production and GitHub Actions CI reach the CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-fork copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Iowa-specific lives in the `METRO:BEGIN config` block (worksheet-generated) and
this instance's own module code.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
this instance's chamber layers use the fenced factory helper `registerIlgaChamber` (the generic
chamber factory both Iowa chambers and the U.S. House card use). Two invariants pervade the
code: the **stale-async guard** (`if (seq !== state.sequence) return;` after every await) and
**per-layer failure isolation** (a layer's failure shows a Retry inside its own card, never
breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name (both
chamber cards degrade to the district number + the legislature's own directory on a roster
miss; the county card carries no roster at all, since no statewide source of county officers
exists). External strings always render through `sanitize()`/`textContent`. Roster refreshes
always land as PRs for human review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script rather than shipped from a bootstrap step (Iowa has none — R2.1 deleted the
state-template machinery before this instance existed): `metro-outline.json` (the whole-state
outline for the coverage wash, `ia/scripts/build_metro_outline.py`), `state-counties.json`
(`ia/scripts/build_state_counties.py`), `congress-districts.json`, `ia-senate-districts.json`
and `ia-house-districts.json` (`ia/scripts/build_legislative_boundaries.py` — statewide
TIGERweb, and ALL THREE simplified in ONE mapshaper run, because two Iowa House districts make
up one Iowa Senate district (Code 42.3) and a shared edge only survives identically if both
layers came off one topology; that builder takes no per-chamber argument for exactly that
reason, and refuses to write unless three gates pass — the 2,000-random-point agreement gate
per layer, an exact cross-layer nesting check, and a fidelity ceiling measured against the
source. Its `--check` re-runs the nesting half offline in CI).
Rosters: `congress-roster.json` (`ia/scripts/build_congress_roster.py`, from
unitedstates/congress-legislators) and `ia-{senate,house}-members.json`
(`ia/scripts/build_ia_legislature_roster.py`, from Open States `ia.csv` enriched by
`ia/scripts/ia_legislature_scraper.py`'s per-legislator profile-page reads — Iowa's site
carries no single listing page with every member's contact block the way Wisconsin's does, so
each of the ~149 current members needs its own page fetch) — all count-guarded, all refreshed
weekly by CI as reviewed PRs.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md` and this
instance's own `docs/IA_EXPANSION_PLAN.md`. The working order those documents teach: prove the
source first (a live fetch you performed), ship the boundary and its officeholder sourcing in
the same change, floor every scraped count, and record what a publisher does NOT publish
rather than guessing. When a layer ships, its row in `ia/metro-worksheet.json` (`layers[]`,
with a `source` block) is what puts it on the sources page and in every gate — a layer cannot
ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the same change.
