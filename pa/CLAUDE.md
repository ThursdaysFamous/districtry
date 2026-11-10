# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Pennsylvania: a single-file, dependency-light web app. Click a point in Pennsylvania
(or search an address) and it reports every civic district containing that point and who
represents you there. It will serve at **districtry.com/pa/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). **The instance
is DARK**: it has no `metros.json` entry and no `layer-concepts.json` column, and the deploy
excludes `pa/**`, so nothing is served. It is the first state of batch 1 of the state-level
launch Adam asked for on 2026-11-10 (Pennsylvania, Nevada, Arizona, New Jersey, New Hampshire),
and it opens with the rest of its batch, in one go-live change, on Adam's own "merge". Nothing
anywhere may call the instance live before then.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the General Assembly's own pages: **County** (`county`, 67, Census TIGERweb, the state
outline the coverage wash covers), **U.S. House** (17 districts, TIGERweb geometry joined to the
public-domain unitedstates/congress-legislators roster), **Pennsylvania Senate** and **House**
(50 and 203 districts, TIGERweb's 2026 state legislative districts joined to each chamber's own
member pages), the TIGERweb fabric drawn from mirrored tile archives — **City, Borough or
Township** (`municipality`, 2,568 county subdivisions), **School District**
(`school-district-unified`, 501) and **ZIP Code** — and three nearest-N layers from the USGS
National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only).

**THE CONGRESSIONAL MAP IS THE 2022 MAP, FROM TIGERweb LAYER 0 (THE 120TH CONGRESS).** The
Supreme Court of Pennsylvania drew the 17 districts in February 2022. Measured 2026-11-10, layer 0
and layer 4 (the 119th Congress's) carry the same 17 districts, every intersection-over-union 1.0,
so layer 0 is right before and after 3 January 2027. `pa/scripts/build_legislative_boundaries.py`
refuses if the two stop matching before that date, and refuses on or after 3 January 2029 so a
person reads which map the 2028 election used before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, the plan
the Legislative Reapportionment Commission adopted in 2022. Measured 2026-11-10 against the 2024
vintage: 49 of 50 Senate districts identical (District 22 IoU 0.99986) and 199 of 203 House
districts identical (lowest District 118, 0.99960). Each map is simplified on its own
(Douglas-Peucker at 5 m under an 8 m ceiling), which is safe because 203 House districts do not
nest in 50 Senate districts.

**THE LEGISLATORS COME FROM THE GENERAL ASSEMBLY'S OWN PAGES** (`www.palegis.us`,
`pa/scripts/build_pa_legislature_roster.py`): each chamber's member list gives the name, party and
district, and each member's page the Capitol office, its mailing box and its telephone. 36 of the
50 senators carry the e-mail address the Senate list writes into the page; the other 14 and every
House member link a contact form instead, which is not carried. District offices are printed and
never read, because the builder cannot tell one from a member's home, and every Capitol office
must name a Harrisburg Capitol ZIP code (171xx) or the build refuses it. The fax line is never
read. robots.txt read 2026-11-10: its one group names an accessibility scanner, so nothing binds
these fetches; the host is paced at one request a second regardless.

**EVERY PART OF PENNSYLVANIA'S LAND IS IN ONE MUNICIPALITY**, and the Census files each as a
county subdivision, so the City, Borough or Township layer is TIGERweb's county subdivisions
(Places_CouSub_ConCity_SubMCD layer 1), not its incorporated places. Measured 2026-11-10 across the
2,568 records: 1,544 townships, 960 borough pieces, 56 city pieces, 6 home rule municipalities and
the town of Bloomsburg. A city or borough crossing a county line is one record per county, so the
card names the county of the part the point is in. One record is not a municipality:
Pennsylvania's part of Lake Erie, filed as "County subdivisions not defined" (LSADC 00), which
the card answers as the lake. One township, Cold Spring in Lebanon County, is recorded as an
inactive government, and its card says so.

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 501 unified districts for Pennsylvania and no
elementary or secondary ones. No board member is named yet (gap `pa-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Most counties elect three commissioners by the whole county, a home
rule county may elect a council and an executive, and Philadelphia's county government is the
city's, which its County card says. Recorded as gaps `pa-county-officials` and
`pa-municipal-officeholders`.

**THE ZIP LAYER HIDES OUTSIDE PENNSYLVANIA.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

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

- Metro: Pennsylvania (`pennsylvania`) — https://districtry.com/pa/
- Geocoders: address Photon (Pennsylvania-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Pennsylvania-bounded, serial >=1s queue)
- Ground truth: 40.26450,-76.88330 (Pennsylvania State Capitol, 501 North 3rd Street, Harrisburg, Dauphin County) → county Dauphin County; us-house 10; pa-senate 15; pa-house 103. Negative point 42.62000,-79.85000 (Lake Erie on the Canadian side of the international line, north of Erie — outside Pennsylvania and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-10: TIGERweb's state layer places it in no state (controls: the State Capitol returns Pennsylvania, and a point in the open Atlantic returns no state), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does. IT IS WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 10 registered (political 3, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.PennsylvaniaExplorer`.
- Scheduled workflows: `update-pa-congress-roster.yml` (Mon 20:07 UTC); `update-pa-legislature-roster.yml` (Tue 20:07 UTC); `pa-validate-sources.yml` (1st of month 21:57 UTC).
- Source registry: `pa/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/pa/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/pa/ node pa/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 pa/scripts/validate_index.py pa/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 pa/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in pa/metro-worksheet.json;
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
which vendors Leaflet into `pa/scripts/vendor/leaflet/` (gitignored);
`pa/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Pennsylvania-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`pa/scripts/build_metro_outline.py` — one INSIDE anchor per county plus 21 OUTSIDE anchors in the
six neighbouring states and on Lake Erie), `state-counties.json`
(`pa/scripts/build_state_counties.py`), and `congress-districts.json`, `pa-senate-districts.json`,
`pa-house-districts.json` (`pa/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m,
refused unless BOTH the 2,000-random-point agreement gate and the 8 m fidelity ceiling pass). The
three TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance pa`; 13,002,700 people in
275,023 blocks, and all three district maps partition them exactly). Rosters:
`congress-roster.json` (`pa/scripts/build_congress_roster.py`, from unitedstates/congress-legislators)
and `pa-{senate,house}-members.json` (`pa/scripts/build_pa_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs. `scripts/validate_chamber_rosters.py` holds both chamber
files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `pa/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
