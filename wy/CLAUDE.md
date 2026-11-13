# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Wyoming: a single-file, dependency-light web app. Click a point in Wyoming
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/wy/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
twelfth state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `wy/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own member feed: **County** (`county`, all 23, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (the at-large district, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Wyoming Senate** and **Wyoming House** (31 and 62 districts, TIGERweb's 2026 state legislative districts joined to the Legislature's own member feed), the TIGERweb fabric drawn from mirrored tile archives — **City or Town** (`municipality`, 99 incorporated places), **School District (Unified)** and **(Elementary)** and **ZIP Code** — three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**) and **Tribal Government** (`tribal-government`, the Census's tribal land, joined to the government that holds it).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `wy/scripts/build_metro_outline.py --check` holds it to 23
INSIDE anchors, one per county, and 14 OUTSIDE anchors over the state line and offshore.

**WYOMING ELECTS ONE MEMBER OF THE U.S. HOUSE, AT LARGE**, so its congressional "map" is the
whole state. TIGERweb carries it on layer 0 (the 120th Congress) as one record, CD120 "00", named
"Congressional District (at Large)", and on layer 4 (the 119th) as the same record.
`wy/scripts/build_legislative_boundaries.py` still measures the two against each other until 3 January
2027 (intersection-over-union 1.0, measured 2026-11-12), and refuses on or after 3 January 2029, so a
person reads the apportionment after the 2030 census before anything is drawn. The U.S. House card names
the district by that record's own name rather than "District 0", which nobody writes.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, 31 Senate and 62 House districts.
Measured 2026-11-12 against TIGERweb's 2024 layers (5 and 6): 29 of the 31 Senate districts are identical while District 29 (intersection-over-union 0.99967) and District 30 (0.99999) differ by slivers, and 60 of the 62 House districts are identical while District 59 (0.99682) and District 58 (0.99997) differ. The newer vintage is drawn. The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage
rolls. **WYOMING DRAWS TWO HOUSE DISTRICTS INSIDE EACH SENATE DISTRICT, BUT NOT EXACTLY**: the
pairing is not by number, and measured 2026-11-12 on the full-precision fetch the House district least
inside its Senate district has only 0.89 of its area there and the worst pair's union matches its Senate
district at an intersection-over-union of 0.93. A shared topology would not make the files agree with a
pairing the source itself does not keep, so each map is simplified on its own, Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN MEMBER FEED** (`wyoleg.gov/LsoService/api/legislator/<year>/S`
and `/H`, the feeds the Legislature's own member pages read; `wy/scripts/build_wy_legislature_roster.py`):
one record per member with name, party, district, an e-mail address at wyoleg.gov, a telephone, which the
feed labels with nothing, a current-member status and the number in the member's page address. Measured
2026-11-12: 31 senators and 62 representatives, every seat, every one with an e-mail address and a
telephone. The year read is the calendar year of the run. Each record also carries the member's address,
city and ZIP code, date of birth, birthplace, religion, spouse and children, **and none of them is read**.
robots.txt read 2026-11-12: it answered 404, which RFC 9309 reads as no restriction.

**MOST OF WYOMING IS IN NO CITY OR TOWN.** The **City or Town** layer is TIGERweb's incorporated places
(layer 4): 99 records, 80 towns and 19 cities, every one an active government, under 1% of the state's land
(921.9 of 251,458.2 km2, measured 2026-11-12). An empty card says the point is outside every city and town
and that the county is the local government there. No mayor or council member is named yet (gap
`wy-municipal-officeholders`).

**TWO SCHOOL LAYERS, AND ONE PLACEHOLDER.** Measured 2026-11-12: 47 unified districts and one elementary
district (Fremont County School District 38), which between them cover the state's land, and nothing on
TIGER's secondary layer. **ONE UNIFIED RECORD IS NOT A DISTRICT**: the Census's "School District Not
Defined" (GEOID 5699997) files about 4,499 km2 of land in Park County, with Canyon Village and Mammoth Hot
Springs in Yellowstone National Park inside it, and the card answers it as no school district. No school
board member is named yet (gap `wy-school-board-members`).

**NO COUNTY OFFICIAL IS NAMED YET**, and the card says so rather than leave a reader to assume the office
is empty. Each county is governed by an elected board of county commissioners and elects officers such
as a clerk, a treasurer, an assessor, a sheriff and a county attorney. Recorded as gap
`wy-county-officials`.

**TRIBAL GOVERNMENT DRAWS THE WIND RIVER RESERVATION AND NAMES NO COUNCIL YET**
(`tribal-areas.json`, since 2026-11-13). The Census keeps the Wind River Reservation (9,128.7 km2)
and its trust land (20.4 km2) in Wyoming, measured 2026-11-12 with `scripts/tribal_areas.py --report
Wyoming`. Both are drawn and held by two nations together, which the Bureau of Indian Affairs lists
separately, so each piece is joined in `data/tribal-government-join.json` to both, and its card
names the Eastern Shoshone Tribe (Fort Washakie) and the Northern Arapaho Tribe (Ethete), each with
its seat and site, and carries no single link, as Oregon's card for Celilo Village does. No council
is carried yet (`ROSTER_NOT_SOUGHT` in `scripts/build_tribal_areas.py`), recorded in gap
`wy-tribal-government`.

**THE ZIP LAYER HIDES OUTSIDE WYOMING.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The four TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the five officers Wyoming elects statewide (the governor, secretary
of state, state auditor, state treasurer and superintendent of public instruction) and both U.S. senators,
from `wy/data/source/statewide-officials.source.json` through `scripts/build_statewide_officials.py`.
Wyoming has no lieutenant governor, and its attorney general is appointed.

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

- Metro: Wyoming (`wyoming`) — https://districtry.com/wy/
- Geocoders: address Photon (Wyoming-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Wyoming-bounded, serial >=1s queue)
- Ground truth: 41.14010,-104.82024 (Wyoming State Capitol, 200 West 24th Street, Cheyenne, Laramie County) → county Laramie County; us-house Congressional District (at Large); wy-senate 8; wy-house 11. Negative point 40.85000,-105.40000 (Larimer County, Colorado, south of the Wyoming line — outside Wyoming and inside permalink_gate, so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names Colorado here (control: the Wyoming State Capitol returns Wyoming), none of the state's shipped boundary files contains it, and of every outline in the fleet only Colorado's does (Colorado went live in batch 3 of the state-level launch). Wyoming borders no water and no other country, and every one of its neighbours (Montana, South Dakota, Nebraska, Colorado, Utah and Idaho) is live once this change lands, so no point this app's gate reaches lies outside every instance: the point stays where it is, as Illinois's sits in Indiana's waters, and a selection the app makes from its own link never leaves for another app.).
- Layers: 12 registered (political 4, safety 2, schools 2, geography 4); `registerLayer(` floor 9. Debug namespace `window.WyomingExplorer`.
- Scheduled workflows: `update-wy-congress-roster.yml` (Wed 23:51 UTC); `update-wy-legislature-roster.yml` (Thu 23:51 UTC); `wy-validate-sources.yml` (2nd of month 23:51 UTC).
- Source registry: `wy/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/wy/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/wy/ node wy/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 wy/scripts/validate_index.py wy/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 wy/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in wy/metro-worksheet.json;
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
which vendors Leaflet into `wy/scripts/vendor/leaflet/` (gitignored);
`wy/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Wyoming-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`wy/scripts/build_metro_outline.py`), `state-counties.json` (the counties, `wy/scripts/build_state_counties.py`),
and `congress-districts.json`, `wy-senate-districts.json` and `wy-house-districts.json`
(`wy/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m under an 8 m ceiling, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance wy`; 22,857 populated blocks holding all 576,851 people the 2020 census counted in Wyoming). Both chamber maps are held to that count; their worst districts are +5.857% (Senate) and +6.255% (House) of the raw-census ideal. The at-large congressional district has no number to key and no ideal but the state. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 176 ZIP codes). Rosters:
`congress-roster.json` (`wy/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`wy-senate-members.json` and `wy-house-members.json` (`wy/scripts/build_wy_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`wy/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `wy/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
