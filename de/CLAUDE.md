# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Delaware: a single-file, dependency-light web app. Click a point in Delaware
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/de/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
thirteenth state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `de/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the General Assembly's own member lists: **County** (`county`, all three, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (the at-large district, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Delaware Senate** and **Delaware House** (21 and 41 districts, TIGERweb's 2026 state legislative districts joined to the General Assembly's own member lists), the TIGERweb fabric drawn from mirrored tile archives — **City, Town or Village** (`municipality`, 57 incorporated places), **School District** (16 unified districts) and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `de/scripts/build_metro_outline.py --check` holds it to 3
INSIDE anchors, one per county, and 11 OUTSIDE anchors over the state line and offshore.

**DELAWARE ELECTS ONE MEMBER OF THE U.S. HOUSE, AT LARGE**, so its congressional "map" is the
whole state. TIGERweb carries it on layer 0 (the 120th Congress) as one record, CD120 "00", named
"Congressional District (at Large)", and on layer 4 (the 119th) as the same record.
`de/scripts/build_legislative_boundaries.py` still measures the two against each other until 3 January
2027 (intersection-over-union 1.0, measured 2026-11-12), and refuses on or after 3 January 2029, so a
person reads the apportionment after the 2030 census before anything is drawn. The U.S. House card names
the district by that record's own name rather than "District 0", which nobody writes.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, 21 Senate and 41 House districts.
Measured 2026-11-12, every district in both chambers is the same as in TIGERweb's 2024 layers (5 and 6), intersection-over-union 1.0. The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage
rolls, and there is no nesting rule between the chambers (a House district's largest share
inside one Senate district is as low as 0.48 of its area), so each map is simplified on its own,
Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE GENERAL ASSEMBLY'S OWN MEMBER LISTS** (`de/scripts/build_de_legislature_roster.py`).
The Senate and House member pages draw their tables from `/json/Senate/GetSenators` and
`/json/House/GetRepresentatives`, which each page names as its table's read address and asks with a POST
carrying the table's paging fields; the script sends what the page sends. Measured 2026-11-12: 21 and 41
rows, one per district, each with the district, the member's name, a party code and the member's number.
**THE LIST'S OWN MEMBER LINK GOES TO A PARTY CAUCUS SITE**, which is a partisan site and not a government
publication, so it is never linked; the card links `legis.delaware.gov/LegislatorDetail?personId=<n>`,
which redirects to the member's page on the General Assembly's own site. The lists carry no e-mail address
or telephone, so the card links that page for them. robots.txt read 2026-11-12: the address answered with
the site's own HTML page, which RFC 9309 reads as no robots.txt.

**MOST OF DELAWARE IS IN NO CITY, TOWN OR VILLAGE.** The **City, Town or Village** layer is TIGERweb's
incorporated places (layer 4): 57 records, 44 towns, 10 cities and 3 villages, every one an active
government, about 8% of the state's land (393.1 of 5,046.8 km2, measured 2026-11-12). An empty card says the
point is outside every city, town and village and that the county is the local government there. No mayor
or council member is named yet (gap `de-municipal-officeholders`).

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 16 unified districts for Delaware and nothing on its
elementary or secondary layers (measured 2026-11-12), so those two layers are not drawn. No school board
member is named yet (gap `de-school-board-members`).

**EACH OF THE THREE COUNTIES HAS ITS OWN FORM OF GOVERNMENT.** New Castle County is governed by an
elected county executive and county council, Kent County by an elected levy court and Sussex County by an
elected county council, and each elects officers such as a sheriff, a recorder of deeds and a register of
wills. The card names none of them yet and says so (gap `de-county-officials`).

**DELAWARE HAS NO TRIBAL LAND TO DRAW.** Measured 2026-11-12 with `scripts/tribal_areas.py --report
Delaware`: the three drawn classes keep no feature inside the state, with Delaware resolving to state code 10
as the control. Recorded as covered in `data/tribal-government-join.json`. The Nanticoke and Lenape
statistical areas are statistical areas, which the fleet draws only in Oklahoma.

**THE ZIP LAYER HIDES OUTSIDE DELAWARE.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the six officers Delaware elects statewide (the governor,
lieutenant governor, attorney general, state treasurer, auditor of accounts and insurance commissioner) and
both U.S. senators, from `de/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`. Delaware's secretary of state is appointed by the governor.

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

- Metro: Delaware (`delaware`) — https://districtry.com/de/
- Geocoders: address Photon (Delaware-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Delaware-bounded, serial >=1s queue)
- Ground truth: 39.15700,-75.51964 (Legislative Hall, 411 Legislative Avenue, Dover, Kent County) → county Kent County; us-house Congressional District (at Large); de-senate 17; de-house 32. Negative point 38.70000,-74.92000 (the Atlantic Ocean east of Rehoboth Beach — outside Delaware and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here, because it is open water (control: the Legislative Hall returns Delaware), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any outline in the change that opens the last thirteen states. IT IS OPEN WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 10 registered (political 3, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.DelawareExplorer`.
- Scheduled workflows: `update-de-congress-roster.yml` (Wed 23:11 UTC); `update-de-legislature-roster.yml` (Thu 23:11 UTC); `de-validate-sources.yml` (2nd of month 23:11 UTC).
- Source registry: `de/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/de/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/de/ node de/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 de/scripts/validate_index.py de/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 de/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in de/metro-worksheet.json;
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
which vendors Leaflet into `de/scripts/vendor/leaflet/` (gitignored);
`de/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Delaware-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the U.S. House and chamber layers use the fenced factory helper `registerIlgaChamber` (which renders a vacancy record as a vacant seat with its reason and source), the County, municipality and school cards are bespoke `registerLayer` blocks, the ZIP layer `registerPolygonLayer`, and the three nearest-N layers `registerNearestPointLayer`. Two invariants pervade the
code: the **stale-async guard** (`if (seq !== state.sequence) return;` after every await) and
**per-layer failure isolation** (a layer's failure shows a Retry inside its own card, never breaks
the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards say who is not named instead of inventing a name. The chamber cards
degrade to the district + the chamber's own member list on a roster miss, and a vacant or unlisted
seat says so with the day it was read; the County, municipality and school district cards carry no
roster and **say so on the card**. External strings always render through
`sanitize()`/`textContent`. Roster refreshes always land as PRs for review — never as direct commits
to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`de/scripts/build_metro_outline.py`), `state-counties.json` (the counties, `de/scripts/build_state_counties.py`),
and `congress-districts.json`, `de-senate-districts.json` and `de-house-districts.json`
(`de/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m under an 8 m ceiling, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance de`; 15,317 populated blocks holding all 989,948 people the 2020 census counted in Delaware). Both chamber maps are held to that count; their worst districts are +7.184% (Senate) and +6.278% (House) of the raw-census ideal (Delaware has counted an incarcerated person at their last address since 2010, which this raw count does not do). The at-large congressional district has no number to key and no ideal but the state. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 68 ZIP codes). Rosters:
`congress-roster.json` (`de/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`de-senate-members.json` and `de-house-members.json` (`de/scripts/build_de_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`de/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `de/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
