# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Ohio: a single-file, dependency-light web app. Click a point in Ohio (or search an
address) and it reports every civic district containing that point and who represents you
there. It will serve at **districtry.com/oh/** as a folder of the consolidated districtry repo,
following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the third state of batch 2
of the state-level launch Adam asked for on 2026-11-10 (Texas, Florida, Ohio, California,
Washington), in his chosen order: built dark, with the deploy excluding `oh/**`, and opened with
the rest of its batch in one go-live change on Adam's own "merge".
**WHETHER IT IS DARK IS READ FROM THE DEPLOY, NEVER FROM THIS SENTENCE.**

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or each chamber's own pages: **County** (`county`, all 88, Census TIGERweb, the state outline
the coverage wash covers), **U.S. House** (15 districts, TIGERweb geometry joined to the
public-domain unitedstates/congress-legislators roster), **Ohio Senate** and **Ohio House** (33
and 99 districts, TIGERweb's 2026 state legislative districts joined to each chamber's own
member pages), the TIGERweb fabric drawn from mirrored tile archives — **City or Village**
(`municipality`, 923 incorporated places), **School District** (612 unified districts) and
**ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**,
**Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline (one ring, 88 counties inside and 16 outside anchors in
Michigan, Indiana, Kentucky, West Virginia, Pennsylvania and Ontario, measured by its `--check`)
and the wash has no lighter band (`coverage_key` with `outside` and `edge` only).

**ALL FIVE OF OHIO'S NEIGHBOURS ARE LIVE, AND FOUR OF THEIR APPS TEST AT POINTS INSIDE OHIO.**
Indiana's uncovered case (Butler County), Illinois's statewide-officials check (the same point),
Kentucky's negative point (Adams County) and Michigan's negative point (Toledo) were each chosen
because no app covered Ohio. Once Ohio's outline is in `fleet-outlines.json`, a selection at each
opens `/oh/`, so the go-live change moves or re-asserts every one (`oh/WATCH.md`, measured
2026-11-11). Ohio's own negative point is in Leamington, Ontario, and never moves.

**THE CONGRESSIONAL MAP IS THE ONE THE SITTING MEMBERS WERE ELECTED FROM, TIGERweb LAYER 4 (THE
119TH CONGRESS), UNTIL 3 JANUARY 2027.** Ohio has a new map for the 120th Congress, which the
November 2026 election used (layer 0, "120th Congressional Districts"). Measured 2026-11-11: 13
of the 15 districts differ between the two (the lowest intersection-over-union District 15 at
0.478), so they are not interchangeable. `oh/scripts/build_legislative_boundaries.py` refuses to
build layer 4 on or after 3 January 2027; the change that day switches it to layer 0, a person's
step, because the cards then name the members elected in 2026.

**THREE OHIO HOUSE DISTRICTS MAKE UP EACH OHIO SENATE DISTRICT (Ohio Constitution, art. XI s. 4),
AND THE SHIPPED FILES AGREE EXACTLY.** The numbering is not arithmetic (Senate District 1 is House
81, 82 and 83), so the three are pinned in the builder's `NESTING_TRIPLETS`, read from TIGER on
2026-11-11. All three maps are simplified in ONE mapshaper run, the Illinois method, so a Senate
edge and the House edge under it are one arc; the build refuses unless the source holds the table,
and `oh/scripts/build_legislative_boundaries.py --check` fails offline in CI unless every shipped
Senate vertex is a vertex of its three shipped House districts. There is no per-chamber argument,
because rebuilding one chamber alone is what breaks the nesting. Simplification is
Douglas-Peucker at 5 m under an 8 m ceiling. Against TIGERweb's 2024 vintage (layers 5 and 6),
all 33 Senate districts are identical and 95 of the 99 House districts, the other four differing
by slivers (the lowest District 23, IoU 0.99987).

**THE LEGISLATORS COME FROM EACH CHAMBER'S OWN PAGES** (`www.ohiosenate.gov`,
`www.ohiohouse.gov`, `oh/scripts/build_oh_legislature_roster.py`). Each chamber's member
directory gives each seat's member and party, and each member's page the name and the Columbus
office and telephone. Neither chamber prints an e-mail address for anyone; each links a contact
form. Measured 2026-11-11: the Senate names 32 of its 33 seats and lists District 13 as vacant,
and all 32 senators' pages print an office; the House names all 99, and two members' pages print
no office. Fax lines, district offices and home towns are never read. robots.txt is read before
the first fetch of each host with the crawling client; the Senate is paced at one request a
second and the House at one every two. The members elected on 3 November 2026 take office in
January 2027, and the weekly refresh carries them when the chambers post them.

**MOST OF OHIO IS IN NO CITY OR VILLAGE.** The **City or Village** layer is TIGERweb's
incorporated places (layer 4): 253 cities and 670 villages, about 9.6% of the state's land
(measured 2026-11-11). One, Rendville village in Perry County, carries the Census's inactive
status, and its card says it does not operate as a local government. An empty card says the
point is outside every city and village and that the township and the county are the local
governments there. Ohio's 1,308 active townships are not drawn (gap `oh-townships`).

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 612 unified districts for Ohio (city, local and
exempted village districts) and nothing on its elementary or secondary layers (measured
2026-11-11), so those two layers are not drawn. No school board member is named yet (gap
`oh-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Recorded as gaps `oh-county-officials` and
`oh-municipal-officeholders`. Ohio's county commissioners are elected countywide, so naming them
needs no district map.

**THE ZIP LAYER HIDES OUTSIDE OHIO.** A ZCTA carries no state field, so over the line the live
service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline, and
the smoke test asserts both halves. The archive keeps 1,233 of the 1,744 ZCTAs in the app's box
(measured 2026-11-11).

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the six officers Ohio elects statewide (the governor and
lieutenant governor, elected on one ticket, the attorney general, secretary of state, auditor of
state and treasurer of state) and both U.S. senators, from
`oh/data/source/statewide-officials.source.json` through `scripts/build_statewide_officials.py`.
The Secretary of State's site answered with a maintenance page and the Auditor of State's
robots.txt refuses every client, so both are read from the state's own list of elected officials
at ohio.gov; the Governor's site and ohio.gov refuse our token and serve the browser client,
which the seed records. Ohio's voters also elect the Supreme Court statewide, and its justices are
not listed yet.

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

- Metro: Ohio (`ohio`) — https://districtry.com/oh/
- Geocoders: address Photon (Ohio-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Ohio-bounded, serial >=1s queue)
- Ground truth: 39.96133,-82.99895 (Ohio Statehouse, 1 Capitol Square, Columbus, Franklin County. Measured 2026-11-11 against the shipped files: 363 m inside its congressional district, 442 m inside its Senate and House districts.) → county Franklin County; us-house 15; oh-senate 15; oh-house 1. Negative point 42.05310,-82.59980 (Leamington, Ontario, on the Canadian shore of Lake Erie — outside Ohio and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-11: TIGERweb's state layer places it in no state (control: the Ohio Statehouse returns Ohio), none of the state's shipped boundary files contains it, and none of the 25 outlines in fleet-outlines.json does. IT IS IN CANADA, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 10 registered (political 3, safety 2, schools 1, geography 4); `registerLayer(` floor 6. Debug namespace `window.OhioExplorer`.
- Scheduled workflows: `update-oh-congress-roster.yml` (Tue 20:53 UTC); `update-oh-legislature-roster.yml` (Thu 20:53 UTC); `oh-validate-sources.yml` (1st of month 23:07 UTC).
- Source registry: `oh/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/oh/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/oh/ node oh/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 oh/scripts/validate_index.py oh/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 oh/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in oh/metro-worksheet.json;
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
which vendors Leaflet into `oh/scripts/vendor/leaflet/` (gitignored);
`oh/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Ohio-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`oh/scripts/build_metro_outline.py` — one INSIDE anchor per county plus OUTSIDE anchors in
Michigan, Indiana, Kentucky, West Virginia, Pennsylvania, Ontario and Lake Erie's Canadian
waters), `state-counties.json` (`oh/scripts/build_state_counties.py`), and
`congress-districts.json`, `oh-senate-districts.json`, `oh-house-districts.json`
(`oh/scripts/build_legislative_boundaries.py` — one mapshaper run for all three, Douglas-Peucker
at 5 m, refused unless the nesting table, the 2,000-random-point agreement gate and the 8 m
fidelity ceiling pass). The TIGERweb fabric layers draw from tile archives under
`data/app/tiles/`, mirrored by `scripts/mirror_tiger_tiles.py`. The compare screen counts people
from Census 2020 blocks under `data/app/population/` (`scripts/build_block_population.py
--instance oh`; 11,799,448 people in 88 county files). The ZIP search reads `zip-index.json`
(`scripts/build_zip_index.mjs`). Rosters: `congress-roster.json`
(`oh/scripts/build_congress_roster.py`, from unitedstates/congress-legislators and the House
Clerk's vacancy list) and `oh-{senate,house}-members.json`
(`oh/scripts/build_oh_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed
PRs. `scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `oh/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
