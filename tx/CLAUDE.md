# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Texas: a single-file, dependency-light web app. Click a point in Texas
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/tx/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
first state of batch 2 of the state-level launch Adam asked for on 2026-11-10 (Texas, Florida,
Ohio, California, Washington), in his chosen order: built dark, with the deploy excluding
`tx/**`, and opened with the rest of its batch in one go-live change on Adam's own "merge",
which narrowed that exclude, added its `metros.json` entry and gave it a `layer-concepts.json`
column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or each chamber's own pages: **County** (`county`, all 254, Census TIGERweb, the state outline
the coverage wash covers), **U.S. House** (38 districts, TIGERweb geometry joined to the
public-domain unitedstates/congress-legislators roster), **Texas Senate** and **Texas House**
(31 and 150 districts, TIGERweb's 2026 state legislative districts joined to each chamber's own
member list), the TIGERweb fabric drawn from mirrored tile archives — **City, Town or Village**
(`municipality`, 1,230 incorporated places), the three **School District** tilings and **ZIP
Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire &
EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only).

**THE CONGRESSIONAL MAP IS THE ONE THE SITTING MEMBERS WERE ELECTED FROM, TIGERweb LAYER 4 (THE
119TH CONGRESS), UNTIL 3 JANUARY 2027.** The Legislature drew a new map in August 2025 and the
November 2026 election used it (layer 0, "120th Congressional Districts"). Measured 2026-11-11:
37 of the 38 districts differ between the two, the lowest intersection-over-union 0.0024, so they
are not interchangeable. `tx/scripts/build_legislative_boundaries.py` refuses to build layer 4 on
or after 3 January 2027; the change that day switches it to layer 0, a person's step, because the
cards then name the members elected in 2026.

**THE TX-23 SEAT IS VACANT, AND THE CARD SAYS SO FROM THE HOUSE CLERK'S OWN PAGE.** The
congress-legislators roster carries 37 Texas members; the Clerk's vacancy list
(clerk.house.gov/Members/ViewVacancies) says the 23rd District's member resigned on April 14,
2026. `tx/scripts/build_congress_roster.py` fills a missing district only with a vacancy the Clerk
lists, and refuses any other gap; the record keeps the date it was first read across weekly runs.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2).** Measured
2026-11-11 against the 2024 vintage (layers 5 and 6): 30 of 31 Senate districts identical and one
different by a sliver (District 12, IoU 0.99996), 145 of 150 House districts identical and five
different by slivers (the lowest District 65, IoU 0.99964), the Census Bureau's own correction
between vintages. There is no nesting rule between the chambers (150 against 31 is not a ratio),
so each map is simplified on its own, Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM EACH CHAMBER'S OWN PAGES** (`senate.texas.gov`, `house.texas.gov`,
`tx/scripts/build_tx_legislature_roster.py`). The Senate's member list and each senator's page give
the name, the party and the Capitol office and telephone; four senators print a physical room
above their mailing address, and the room is the one carried. The House's member list (a JSON
block in the page) and each member's page give the name and the Capitol room and telephone; the
House prints no party and no e-mail address for anyone, so its cards name none. A seat the list
names no one for, or marks vacant, ships as vacant with that reason (measured 2026-11-11: Senate 22
and House 1 and 93). Fax lines, office hours and district offices are never read. robots.txt read
2026-11-11 for both hosts with the crawling client; neither states a Crawl-delay, and the Senate
is paced at one request a second and the House at three, because the House timed out under a
faster pace.

**MOST OF TEXAS IS IN NO CITY, TOWN OR VILLAGE.** The **City, Town or Village** layer is TIGERweb's
incorporated places (layer 4): 978 cities, 230 towns and 22 villages, about 4.5% of the state's
land. Three towns are inactive governments (FUNCSTAT I), and their card says the county governs
there. An empty card says the point is outside every incorporated place and that the county is
the local government there.

**THE SCHOOL LAYER IS THREE TILINGS, AND ONE PLACE NEEDS TWO OF THEM.** TIGER holds 1,016 unified
districts for Texas, which cover all its land but Vysehrad in Lavaca County, where Vysehrad
Independent School District runs pre-kindergarten to grade 8 (layer 2, elementary) and
Hallettsville Independent School District grades 9 to 12 (layer 1, secondary). The unified layer
answers HTTP 500 to a whole-state request, so the mirror and the app's own fallback page it 250 at
a time. No trustee is named yet (gap `tx-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Recorded as gaps `tx-county-officials` and
`tx-municipal-officeholders`.

**THE ZIP LAYER HIDES OUTSIDE TEXAS.** A ZCTA carries no state field, so over the line the live
service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline, and
the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the nine officers Texas elects statewide outside the courts
(the governor, lieutenant governor, attorney general, comptroller, land commissioner, agriculture
commissioner and three railroad commissioners) and both U.S. senators, from
`tx/data/source/statewide-officials.source.json` through `scripts/build_statewide_officials.py`.
The comptroller, Don Huffines, was appointed and sworn in on 1 August 2026, as the office's own
biography page says. The Supreme Court and the Court of Criminal Appeals, also elected statewide,
are not listed yet.

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

- Metro: Texas (`texas`) — https://districtry.com/tx/
- Geocoders: address Photon (Texas-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Texas-bounded, serial >=1s queue)
- Ground truth: 30.27467,-97.74035 (Texas State Capitol, 1100 Congress Avenue, Austin, Travis County) → county Travis County; us-house 37; tx-senate 14; tx-house 49. Negative point 28.50000,-101.50000 (The Coahuila desert in Mexico, about 60 km south of the Rio Grande opposite Del Rio — outside Texas and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-11: TIGERweb's state layer places it in no state (controls: the State Capitol returns Texas, and a point in Chihuahua returns no state), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does. IT IS IN ANOTHER COUNTRY, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 12 registered (political 3, safety 2, schools 3, geography 4); `registerLayer(` floor 8. Debug namespace `window.TexasExplorer`.
- Scheduled workflows: `update-tx-congress-roster.yml` (Mon 20:33 UTC); `update-tx-legislature-roster.yml` (Tue 20:33 UTC); `tx-validate-sources.yml` (1st of month 22:23 UTC).
- Source registry: `tx/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/tx/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/tx/ node tx/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 tx/scripts/validate_index.py tx/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 tx/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in tx/metro-worksheet.json;
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
which vendors Leaflet into `tx/scripts/vendor/leaflet/` (gitignored);
`tx/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Texas-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the three chamber layers use the fenced factory helper `registerIlgaChamber` (which renders a
vacancy record as a vacant seat with its reason and source), the County and municipality cards
are bespoke `registerLayer` blocks, the school layer `registerPolygonLayer`, and the three
nearest-N layers `registerNearestPointLayer`. Two invariants pervade the code: the
**stale-async guard** (`if (seq !== state.sequence) return;` after every await) and **per-layer
failure isolation** (a layer's failure shows a Retry inside its own card, never breaks the
others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards say who is not named instead of inventing a name. The chamber cards
degrade to the district number + the chamber's own member list on a roster miss, and a vacant
seat says it is vacant; the County, municipality and school district cards carry no roster and
**say so on the card**. External strings always render through `sanitize()`/`textContent`.
Roster refreshes always land as PRs for review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`tx/scripts/build_metro_outline.py` — one INSIDE anchor per county plus OUTSIDE anchors in the
four neighbouring states and Mexico), `state-counties.json` (`tx/scripts/build_state_counties.py`),
and `congress-districts.json`, `tx-senate-districts.json`, `tx-house-districts.json`
(`tx/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, refused unless the
2,000-random-point agreement gate and the 8 m fidelity ceiling pass). The TIGERweb fabric layers
draw from tile archives under `data/app/tiles/`, mirrored by `scripts/mirror_tiger_tiles.py`. The
compare screen counts people from Census 2020 blocks under `data/app/population/`
(`scripts/build_block_population.py --instance tx`; 29,145,505 people in 254 county files). The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`). Rosters: `congress-roster.json`
(`tx/scripts/build_congress_roster.py`, from unitedstates/congress-legislators and the House
Clerk's vacancy list) and `tx-{senate,house}-members.json`
(`tx/scripts/build_tx_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed
PRs. `scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `tx/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
