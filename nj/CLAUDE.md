# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry New Jersey: a single-file, dependency-light web app. Click a point in New Jersey
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/nj/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
fourth state of batch 1 of the state-level launch Adam asked for on 2026-11-10 (Pennsylvania,
Nevada, Arizona, New Jersey, New Hampshire): built dark, with the deploy excluding `nj/**`, and
opened with the rest of its batch in one go-live change on Adam's own "merge", which narrowed
that exclude, added its `metros.json` entry and gave it a `layer-concepts.json` column.
Its `metro_center`, which only biases the address search toward a point, moved at go-live from
40.07,-74.73 to 40.28,-74.55, because the old point sits inside Pennsylvania's fleet box and
`validate_index.py` refuses a sibling's box that holds an instance's centre.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own roster: **County** (`county`, the 21 counties, Census TIGERweb, the
state outline the coverage wash covers), **U.S. House** (12 districts, TIGERweb geometry joined
to the public-domain unitedstates/congress-legislators roster), **New Jersey Senate** and
**New Jersey Assembly** (`nj-senate`, `nj-assembly`, the same 40 districts, joined to the
Legislature's own member roster), the TIGERweb fabric drawn from mirrored tile archives —
**Municipality** (`municipality`, 564 municipalities), **School District (Unified)**,
**(Elementary)** and **(Secondary)** and **ZIP Code** — and three nearest-N layers from the USGS
National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). The outline is one ring with two holes: Liberty Island and the part of
Ellis Island that is New York's, both inside New Jersey's waters (`nj/scripts/build_metro_outline.py`
holds 21 INSIDE anchors, one per county, and 13 OUTSIDE anchors in Pennsylvania, New York,
Delaware and the open Atlantic).

**THE CONGRESSIONAL MAP IS THE 2022 MAP, FROM TIGERweb LAYER 0 (THE 120TH CONGRESS).** The New
Jersey Redistricting Commission drew the 12 districts in December 2021. Measured 2026-11-10, layer 0
and layer 4 (the 119th Congress's) carry the same 12 districts, every intersection-over-union 1.0,
so layer 0 is right before and after 3 January 2027. `nj/scripts/build_legislative_boundaries.py`
refuses if the two stop matching before that date, and refuses on or after 3 January 2029 so a
person reads which map the 2028 election used before anything is drawn.

**ONE MAP SERVES BOTH CHAMBERS.** New Jersey elects one senator and two members of the General
Assembly from each of the same 40 legislative districts (N.J. Const. art. IV, sec. II, pars. 1
and 2). TIGERweb carries the Apportionment Commission's 2022 plan twice, as layer 1 (upper) and
layer 2 (lower); the builder measures them against each other on every build and refuses unless
they are the same 40 districts, then writes layer 1 ONCE as `nj-legislative-districts.json`,
which both chamber layers read. Douglas-Peucker at 5 m under an 8 m ceiling.

**AN ASSEMBLY DISTRICT ELECTS TWO MEMBERS, AND THE CARD NAMES BOTH**, through the engine chamber
factory's `{seats, members}` record (`seatMembers` in `engine/index.html/chamber-factory.txt`,
added for Arizona's House). The card lists each member with their own party, e-mail and district
office and says the district elects two, each representing every point in it.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN ROSTER** (`www.njleg.state.nj.us`,
`nj/scripts/build_nj_legislature_roster.py`): the roster page's own data block gives each member's
chamber, district, party and page, and each member's record in the Legislature's own feed (the
address the member's page requests) gives the name, the member's @njleg.org mailbox and the main
district office with its telephone. The Legislature prints no Trenton office for a member, so the
card carries the district office. A second district office, the committees, the photograph, the
contact form and the fax are never read. robots.txt read 2026-11-10: one `*` group, `Allow: /`, no
Crawl-delay; the host is paced at one request a second regardless.

**EVERY PART OF NEW JERSEY'S LAND IS IN ONE MUNICIPALITY**, and the Census files each as a county
subdivision, so the **Municipality** layer is TIGERweb's county subdivisions
(Places_CouSub_ConCity_SubMCD layer 1), not its incorporated places. Measured 2026-11-10 across the
569 records: 252 boroughs, 240 townships, 52 cities, 15 towns, 4 villages, Princeton, and 5 records
that are not municipalities but coastal and bay water ("County subdivisions not defined"). Princeton
is filed with the same type code as the water (LSADC 00) and has land, so the card tells water apart
by the county subdivision code 00000 (`njMunicipalIsWater`) and names Princeton with no type row,
since the Census records none. The card names the county from the app's own county file.

**THREE SCHOOL LAYERS, BECAUSE NEW JERSEY USES ALL THREE OF TIGER'S TILINGS.** Measured 2026-11-10
for STATE='34': 342 unified records and 168 elementary districts, which together cover the state's
land, and 45 secondary districts (31 running grades 9 to 12 and 14 running 7 to 12), which cover
exactly the elementary districts' ground, so a reader there is in one elementary and one secondary
district at once. Each card prints the grades the Census records. **ONE OF THE 342 UNIFIED RECORDS
IS NOT A DISTRICT**: the Census files New Jersey's coastal and bay waters under "School District Not
Defined" (GEOID 3499997, no land, 2,217 km2 of water), and the card answers it as water
(`njSchoolPlaceholder`). No board of education member is named yet (gap `nj-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Each county elects a board of county commissioners (freeholders
until 2021), a clerk, a sheriff and a surrogate. Recorded as gaps `nj-county-officials` and
`nj-municipal-officeholders`. New Jersey has no federally recognized tribe or reservation; the
Census draws two State Designated Tribal Statistical Areas (Ramapough and Nanticoke Lenni-Lenape),
which are statistical areas rather than governed land and are not drawn (`nj/WATCH.md`).

**THE ZIP LAYER HIDES OUTSIDE NEW JERSEY.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The five TIGERweb fabric layers answer from
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

- Metro: New Jersey (`newjersey`) — https://districtry.com/nj/
- Geocoders: address Photon (New Jersey-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, New Jersey-bounded, serial >=1s queue)
- Ground truth: 40.22040,-74.76990 (New Jersey State House, 125 West State Street, Trenton, Mercer County) → county Mercer County; us-house 12; nj-senate 15; nj-assembly 15. Negative point 39.30000,-74.00000 (The open Atlantic about 36 km east of Atlantic City — outside New Jersey and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-10: TIGERweb's state layer names no state here (controls: the State House in Trenton and Newark return New Jersey), and New Jersey's water-inclusive county fabric reaches three nautical miles out, far short of it. IT IS WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 12 registered (political 3, safety 2, schools 3, geography 4); `registerLayer(` floor 10. Debug namespace `window.NewJerseyExplorer`.
- Scheduled workflows: `update-nj-congress-roster.yml` (Mon 21:19 UTC); `update-nj-legislature-roster.yml` (Tue 21:19 UTC); `nj-validate-sources.yml` (1st of month 23:09 UTC).
- Source registry: `nj/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->
## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/nj/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/nj/ node nj/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 nj/scripts/validate_index.py nj/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 nj/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in nj/metro-worksheet.json;
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
which vendors Leaflet into `nj/scripts/vendor/leaflet/` (gitignored);
`nj/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything New Jersey-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the three chamber layers use the fenced factory helper `registerIlgaChamber` (which renders a
vacancy record as a vacant seat with its reason and source, and a multi-member record as every
member it lists), the County, City or Town and three school cards are bespoke `registerLayer`
blocks, and the three nearest-N layers `registerNearestPointLayer`. Two invariants pervade the
code: the **stale-async guard** (`if (seq !== state.sequence) return;` after every await) and
**per-layer failure isolation** (a layer's failure shows a Retry inside its own card, never
breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards say who is not named instead of inventing a name. The chamber cards
degrade to the district number + the chamber's own member roster on a roster miss, and a vacant
seat says it is vacant; the County, Municipality and school district cards carry no roster and
**say so on the card**. External strings always render through `sanitize()`/`textContent`.
Roster refreshes always land as PRs for review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`nj/scripts/build_metro_outline.py` — one INSIDE anchor per county plus 13 OUTSIDE anchors over
the state line and offshore), `state-counties.json` (`nj/scripts/build_state_counties.py`), and
`congress-districts.json` and `nj-legislative-districts.json`
(`nj/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, refused unless the
2,000-random-point agreement gate, the 8 m fidelity ceiling and the layer-1/layer-2 twin check
all pass). The five TIGERweb fabric layers draw from tile archives under `data/app/tiles/`,
mirrored by `scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020
blocks under `data/app/population/` (`scripts/build_block_population.py --instance nj`;
113,212 populated blocks holding all 9,288,994 people the 2020 census counted in New Jersey). The ZIP search reads
`zip-index.json` (`scripts/build_zip_index.mjs`, 598 ZIP codes). Rosters: `congress-roster.json`
(`nj/scripts/build_congress_roster.py`, from unitedstates/congress-legislators) and
`nj-{senate,assembly}-members.json` (`nj/scripts/build_nj_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs. `scripts/validate_chamber_rosters.py` holds both chamber
files to their shape: one record per Senate district, and two members per Assembly district.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `nj/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
