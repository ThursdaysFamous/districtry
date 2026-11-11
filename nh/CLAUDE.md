# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry New Hampshire: a single-file, dependency-light web app. Click a point in New Hampshire
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/nh/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
fifth state of batch 1 of the state-level launch Adam asked for on 2026-11-10 (Pennsylvania,
Nevada, Arizona, New Jersey, New Hampshire): built dark, with the deploy excluding `nh/**`, and
opened with the rest of its batch in one go-live change on Adam's own "merge", which narrowed
that exclude, added its `metros.json` entry and gave it a `layer-concepts.json` column.

**The layers** draw their shapes from the Census Bureau and NH GRANIT and name people from a
national roster or the General Court's own pages: **County** (`county`, the 10 counties, Census
TIGERweb, the state outline the coverage wash covers), **U.S. House** (2 districts, TIGERweb
geometry joined to the public-domain unitedstates/congress-legislators roster),
**New Hampshire Senate** (`nh-senate`, 24 districts) and **New Hampshire House** (`nh-house`,
400 seats in 203 named districts), the TIGERweb fabric drawn from mirrored tile archives —
**City or Town** (`municipality`), **School District (Unified)**, **(Elementary)** and
**(Secondary)** and **ZIP Code** — and three nearest-N layers from the USGS National Map
(**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). The outline is one ring with no holes (`nh/scripts/build_metro_outline.py`
holds 10 INSIDE anchors, one per county, and 17 OUTSIDE anchors in Massachusetts, Vermont, Maine,
Quebec and the Gulf of Maine).

**THE CONGRESSIONAL MAP IS THE 2022 MAP, FROM TIGERweb LAYER 0 (THE 120TH CONGRESS).** The New
Hampshire Supreme Court drew the two districts in 2022, when the Legislature and the Governor did
not agree on a plan. `nh/scripts/build_legislative_boundaries.py` measures layer 0 against layer 4
(the 119th Congress's) on every build and refuses to draw layer 0 before 3 January 2027 if they
stop carrying the same two districts, and refuses on or after 3 January 2029 so a person reads
which map the 2028 election used before anything is drawn.

**THE HOUSE IS 400 SEATS IN 203 NAMED DISTRICTS, AND 39 OF THEM ARE DRAWN OVER THE OTHER 164.**
A district is a county and a number ("Merrimack 18") and elects one to ten representatives. 164
"base" districts tile the state; 39 "floterial" districts are each the whole of two or more base
districts and elect more members from all of them together, so a reader in a base district that
belongs to a floterial is represented by the members of both. TIGERweb's lower-house layer
carries the 164 base districts and no floterial (Census geography cannot overlap), so the
floterials come from NH GRANIT's 2022 House layers (University of New Hampshire), and the builder
measures with shapely which base districts make each floterial, refusing unless every floterial
is exactly a union of whole base districts and no base district sits in two. Measured 2026-11-11:
all 39 are exact, 108 of the 164 base districts belong to one, none to two. The House ships as ONE
file of the 164 base districts, each carrying `district`, and where it has one `floterial` and
`floterialOf`; a floterial is never drawn as an outline of its own, which keeps the file a
partition. The three maps are simplified in one shared topology (`combine-files`), Douglas-Peucker
at 5 m under an 8 m ceiling, so a Senate line and the House line it runs along cannot part.
GRANIT's certificate chain ends at a root the sandbox's proxy bundle lacks, so its fetches verify
against certifi's copy of Mozilla's store; verification is never switched off.

**THE HOUSE CARD NAMES EVERY MEMBER OF THE BASE DISTRICT AND OF ITS FLOTERIAL**, through a
bespoke `registerLayer` block (`nh-house`), because the engine chamber factory joins one district
to one record and this point has two. The card lists the base district's members, then a
"Floterial district" section with its members and a sentence naming every base district it is
drawn over. A district listed with fewer members than it elects says how many it lists and on what
day. The Senate uses the engine chamber factory (`registerIlgaChamber`).

**THE LEGISLATORS COME FROM THE GENERAL COURT, WITH OPEN STATES AS THE FALLBACK** (Adam's choice
of 2026-11-10, `nh/scripts/build_nh_legislature_roster.py`): route 1 is the General Court's own
member file (`gc.nh.gov/downloads/members.txt`), route 2 Open States' export of current
legislators, compiled from the General Court's pages. **gc.nh.gov answered every request from the
build sandbox with an empty reply on 2026-11-11**, robots.txt included, so the first shipped roster
came from route 2; whether a GitHub runner reaches the General Court is the first weekly run's
question (`nh/WATCH.md`). The member file prints each representative's home address, which is
NEVER read; its telephone column is not read in this pass. From route 2 only an address at the
General Court's own domains (`@gc.nh.gov`, `@leg.state.nh.us`) is carried, because many
representatives give the General Court a personal address and Open States is not a government.
On 2026-11-11 the roster named all 24 senators and 382 of the House's 400 seats, with 18 districts
listing fewer members than they elect.

**EVERY PART OF NEW HAMPSHIRE'S LAND IS IN A CITY, A TOWN OR AN UNINCORPORATED PLACE**, and the
Census files each as a county subdivision, so the **City or Town** layer is TIGERweb's county
subdivisions (Places_CouSub_ConCity_SubMCD layer 1). Measured 2026-11-11 across the 260 records:
13 cities and 221 towns with functioning governments, Livermore (a town whose government the
Census records as inactive), 24 unincorporated places with no government of their own (grants,
purchases, townships and locations, all in Coos County but Hale's location in Carroll County), and
one record of coastal water, which the card answers as water (`nhPlaceIsWater`,
`answerIsNotADistrict`). The card names each place's kind from `NH_PLACE_KINDS` and prints no type
row for a legal description it does not carry.

**THREE SCHOOL LAYERS, AND ONE PLACEHOLDER.** Measured 2026-11-11 for STATE='33': 82 records on
the unified layer, 90 elementary districts and 8 secondary districts (cooperative high schools),
which cover part of the elementary districts' ground, so a reader there is in two districts at
once. **ONE OF THE 82 UNIFIED RECORDS IS NOT A DISTRICT**: the Census's "School District Not
Defined" (GEOID 3399997) files 859 km2 of land in 15 unincorporated places and 115 km2 of the
Atlantic, and the card answers it as no school district (`nhSchoolPlaceholder`) rather than
saying it runs every grade. No school board member is named yet (gap `nh-school-board-members`).

**NO COUNTY, CITY OR TOWN OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Each county elects three commissioners, a sheriff, a county
attorney, a treasurer, a register of deeds and a register of probate (RSA 653:1), and the
county's own state representatives sit as its county convention. Recorded as gaps
`nh-county-officials` and `nh-municipal-officeholders`. New Hampshire has no federally recognized
tribe and no reservation.

**THE ZIP LAYER HIDES OUTSIDE NEW HAMPSHIRE.** A ZCTA carries no state field, so over the line the
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

- Metro: New Hampshire (`newhampshire`) — https://districtry.com/nh/
- Geocoders: address Photon (New Hampshire-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, New Hampshire-bounded, serial >=1s queue)
- Ground truth: 43.20672,-71.53781 (New Hampshire State House, 107 North Main Street, Concord, Merrimack County) → county Merrimack County; us-house 2; nh-senate 15; nh-house Merrimack 18. Negative point 42.90000,-70.30000 (The Gulf of Maine about 40 km east of Hampton Beach and 25 km south-east of the Isles of Shoals — outside New Hampshire and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-11: TIGERweb's state layer names no state here (control: the State House in Concord returns New Hampshire), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does. IT IS WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 12 registered (political 3, safety 2, schools 3, geography 4); `registerLayer(` floor 10. Debug namespace `window.NewHampshireExplorer`.
- Scheduled workflows: `update-nh-congress-roster.yml` (Mon 21:55 UTC); `update-nh-legislature-roster.yml` (Tue 21:55 UTC); `nh-validate-sources.yml` (1st of month 23:45 UTC).
- Source registry: `nh/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->
## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/nh/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/nh/ node nh/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 nh/scripts/validate_index.py nh/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 nh/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in nh/metro-worksheet.json;
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
which vendors Leaflet into `nh/scripts/vendor/leaflet/` (gitignored);
`nh/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything New Hampshire-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the U.S. House and Senate layers use the fenced factory helper `registerIlgaChamber`, the House,
County, City or Town and three school cards are bespoke `registerLayer` blocks, and the three
nearest-N layers `registerNearestPointLayer`. Two invariants pervade the code: the
**stale-async guard** (`if (seq !== state.sequence) return;` after every await) and
**per-layer failure isolation** (a layer's failure shows a Retry inside its own card, never
breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards say who is not named instead of inventing a name. The chamber cards
degrade to the district + the chamber's own member directory on a roster miss, and a House
district listed short says how many it lists and on what day, never that a seat is vacant; the
County, City or Town and school district cards carry no roster and **say so on the card**.
External strings always render through `sanitize()`/`textContent`. Roster refreshes always land as
PRs for review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`nh/scripts/build_metro_outline.py` — one INSIDE anchor per county plus 17 OUTSIDE anchors over
the state line and offshore), `state-counties.json` (`nh/scripts/build_state_counties.py`), and
`congress-districts.json`, `nh-senate-districts.json` and `nh-house-districts.json`
(`nh/scripts/build_legislative_boundaries.py` — one shared topology, Douglas-Peucker at 5 m,
refused unless the 2,000-random-point agreement gate, the 8 m fidelity ceiling and the floterial
membership check all pass). The five TIGERweb fabric layers draw from tile archives under
`data/app/tiles/`, mirrored by `scripts/mirror_tiger_tiles.py`. The compare screen counts people
from Census 2020 blocks under `data/app/population/` (`scripts/build_block_population.py
--instance nh`; 25,317 populated blocks holding all 1,377,529 people the 2020 census counted in
New Hampshire), which holds the congressional and Senate maps to that count; the House map is not
held there, because its districts elect one to ten members each and are named rather than
numbered, so its partition is held by the boundary builder's own gate. The ZIP search reads
`zip-index.json` (`scripts/build_zip_index.mjs`, 247 ZIP codes). Rosters: `congress-roster.json`
(`nh/scripts/build_congress_roster.py`, from unitedstates/congress-legislators) and
`nh-{senate,house}-members.json` (`nh/scripts/build_nh_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs. `scripts/validate_chamber_rosters.py` holds both chamber
files to their shape: one record per Senate district, and each House district held to its own
seat count from the builder's `HOUSE_DISTRICT_SEATS`.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `nh/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
