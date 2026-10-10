# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Oklahoma: a single-file, dependency-light web app. Click a point in Oklahoma (or
search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/ok/** as a folder of the consolidated
districtry repo — following the Wisconsin/Iowa shape (`docs/EXPANSION_GUIDE.md` Part 2), not
the Illinois root-scripts shape. It ships ELEVEN layers, and it went **LIVE** in its go-live change,
which Adam held until the fleet-wide tribal thread had drawn Oklahoma's tribal areas: it has a
`metros.json` entry and a landing card, the Pages deploy publishes `ok/` (keeping
`ok/data/state`, `ok/data/source` and `ok/scripts` out), and `ok/congress.html` and
`ok/state-legislature.html` carry its rosters as generated tables.

**The national tier** — everything eleven layers answer today comes from a national publisher.
**County** (77, Census TIGERweb, identity-only and the coverage ring), **U.S. House** (5
districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators
roster), **Oklahoma Senate** and **Oklahoma House** (48 and 101 districts, TIGERweb geometry
joined to the Open States export), the LIVE TIGERweb fabric — **City or Town**
(`municipality`), **School District (Unified)** (415), **School District (Elementary)** (91)
and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**,
**Fire & EMS Station**, **Post Office**).

**THE CHAMBER CARDS CARRY NAME, PARTY, E-MAIL AND THE MEMBER'S OWN PAGE, AND NO OFFICE.** The
Open States export carries no capitol address or telephone for any Oklahoma legislator (0 of 147
rows, measured 2026-10-09), and one seat in each chamber has no member in the export (Senate 24,
House 99 on that date). House 99 contains the State Capitol, so the instance's own anchor point
exercises the factory's empty-member path: the card shows the district and the chamber's
directory, never a name. Reading the chambers' own sites for office and telephone is a WATCH
item, not done here.

**THERE IS NO TOWNSHIP LAYER, AND THAT IS A MEASUREMENT.** All 305 county subdivisions TIGERweb
carries for STATE='40' are census county divisions (LSADC 22, FUNCSTAT S): statistical areas
drawn for counting, which govern nobody. A card for one would put a non-government on the map.

**TWO SCHOOL LAYERS, BECAUSE TWO OF TIGER'S THREE TILINGS PARTITION THE STATE.** Unified (415)
and elementary (91) districts together cover the state's land exactly (166,222.99 + 11,441.40 =
177,664.38 km², the 77-county total from the same service), and the secondary layer is empty.
Unified alone would tell every reader in an elementary district they are in no school district,
so both ship and each empty note points at the other.

**CITY AND TOWN ARE DIFFERENT FORMS HERE.** Oklahoma's Title 11 gives a town a board of trustees
and a city a council, so the municipality card names the two separately, unlike North Carolina's
one note. 600 places: 165 cities, 435 towns, 8 of the towns FUNCSTAT I (inactive), which the
card states.

**THE ZIP LAYER HIDES OUTSIDE OKLAHOMA.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP (Wichita Falls TX gives 76301, Fort Smith
AR 72903, against the Capitol's 73105, measured 2026-10-09). The coverage test reads the shipped
outline, and the smoke test asserts both halves.

**THE FLAGSHIP THIS INSTANCE IS BUILDING TOWARD IS `county-commissioner`.** Every county elects
three commissioners from three districts (19 O.S. 321), so the board's form needs no per-county
research, and the state transport department publishes all 231 districts in one statewide file.
Recorded as gap `ok-commissioner-districts` until it ships, beside `ok-municipal-officeholders`,
`ok-school-board-members` and `ok-tribal-government`.

**TRIBAL GOVERNMENTS ARE IN SCOPE AND ARE NOT IN THIS PR.** Measured with
`scripts/tribal_areas.py` on 2026-10-09, the Census draws one federal reservation in Oklahoma
(Osage, 5,967 km²) and one off-reservation trust land (Shawnee, 0.43 km²); everything else it
records for Oklahoma's nations is an Oklahoma Tribal Statistical Area, which under Adam's ruling
of 2026-09-30 is never drawn as territory. That is the Census's classification and not a legal
one, and the fleet-wide tribal-government thread owns the decision.

**THE CHAMBER BOUNDARIES USE DOUGLAS-PEUCKER AT `interval=20`**, inherited from North Carolina's
measurement and re-measured here: worst stray 23.9 / 24.0 / 24.0 m against the 25 m ceiling the
builder gates, with Oklahoma's median source step about 40-45 m. The coverage outline is ONE
ring, 2,685 vertices, read from `build_metro_outline.py --check`.

**There is no build step, no framework, and no server-side code.** The app — styles, engine,
and layer modules — lives inline in `index.html`. `sw.js` is the service worker;
`data/app/*.json` are runtime-fetched data files; `data/state/` carries the bootstrap state
config (`build_congress_roster.py` reads its FIPS/USPS/seat count — it ships in the repo and is
excluded from the Pages deploy). `sources.html` carries the generated per-layer provenance
matrix and `faq.html` the common questions; both compose from the same shared engine blocks as
every other instance via `scripts/compose_app.py`.

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: Oklahoma (`oklahoma`) — https://districtry.com/ok/
- Geocoders: address Photon (Oklahoma-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Oklahoma-bounded, serial >=1s queue)
- Ground truth: 35.49230,-97.50340 (the State Capitol, Oklahoma City, Oklahoma County) → county Oklahoma County; us-house 5; ok-senate 48; ok-house 99. Negative point 33.65000,-97.15000 (near Gainesville, Cooke County, TEXAS, about 15 km south of the Red River — outside Oklahoma and outside every other instance in the fleet, and inside permalink_gate (minLat 33.50) so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-09: TIGERweb's state layer names Texas at this point (control: the Capitol anchor returns Oklahoma). TEXAS BECAUSE NO INSTANCE SERVES IT, and on land rather than on the Red River, whose channel the county fabric could place on either side.).
- Layers: 11 registered (political 3, safety 2, schools 2, geography 4); `registerLayer(` floor 8. Debug namespace `window.OklahomaExplorer`.
- Scheduled workflows: `update-ok-congress-roster.yml` (Mon 16:45 UTC); `update-ok-legislature-roster.yml` (Tue 16:45 UTC); `ok-validate-sources.yml` (1st of month 19:00 UTC).
- Source registry: `ok/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->
## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ok/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ok/ node ok/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ok/scripts/validate_index.py ok/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 ok/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in ok/metro-worksheet.json;
# GENERATED regions are emitted from it. NEVER hand-edit a GENERATED region:
pip install -c scripts/requirements.txt jsonschema
python3 scripts/generate_metro_files.py            # regenerate in place (all instances)
python3 scripts/generate_metro_files.py --check    # the CI drift gate

# Engine parity: the ENGINE fences are composed from the repo-root engine/ —
# edit a block THERE and recompose, never inside an instance file:
python3 scripts/compose_app.py            # splice engine/ into every instance
python3 scripts/compose_app.py --check    # the CI drift gate
```

Run the full battery through `.claude/skills/steward/SKILL.md`, never through a command list you
extract yourself — the repo root's CLAUDE.md records four different sessions getting that wrong
four different ways, one of which hung for five hours.

**Sandboxed environments (Claude Code web):** the headless browser cannot reach the Leaflet
CDN. The repo root's `.claude/settings.json` SessionStart hook runs `scripts/vendor_leaflet.sh`,
which vendors Leaflet into `ok/scripts/vendor/leaflet/` (gitignored);
`ok/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Oklahoma-specific lives in the `METRO:BEGIN config` block
(worksheet-generated) and this instance's own module code, between the `chamber-factory` and
`hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
this instance's three chamber layers use the fenced factory helper `registerIlgaChamber` (the
generic chamber factory both state chambers and the U.S. House card use), and the three
nearest-N layers use `registerNearestPointLayer`. Two invariants pervade the code: the
**stale-async guard** (`if (seq !== state.sequence) return;` after every await) and **per-layer
failure isolation** (a layer's failure shows a Retry inside its own card, never breaks the
others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name. Both chamber
cards degrade to the district number + the chamber's own directory on a roster miss; the county,
school-district and municipality cards carry no roster at all and **say so on the
card**. External strings always render through `sanitize()`/`textContent`. Roster refreshes
always land as PRs for human review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`ok/scripts/build_metro_outline.py` — one INSIDE anchor per county, each verified interior
against that county's own rings, all 77 correct, plus four OUTSIDE anchors in Texas, Arkansas
and Kansas), `state-counties.json` (`ok/scripts/build_state_counties.py`), and
`congress-districts.json`, `ok-senate-districts.json`, `ok-house-districts.json`
(`ok/scripts/build_legislative_boundaries.py` — statewide TIGERweb, mapshaper-simplified with
Douglas-Peucker, refused unless BOTH the 2,000-random-point agreement gate and the 25 m fidelity
ceiling pass). Rosters: `congress-roster.json` (`ok/scripts/build_congress_roster.py`, from
unitedstates/congress-legislators) and `ok-{senate,house}-members.json`
(`ok/scripts/build_ok_legislature_roster.py`, from Open States `ok.csv`) — all count-guarded,
all refreshed weekly by CI as reviewed PRs. The legislature builder also refuses to write when
fewer than 90% of seats carry an e-mail, a district number falls outside the chamber's range, or
two members claim one district.

robots.txt is read before the first fetch through `scraper_common.require_robots_once`.
`data.openstates.org` answers its robots.txt with HTTP 403, which RFC 9309 files with a 404:
no policy, allow all.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `ok/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
