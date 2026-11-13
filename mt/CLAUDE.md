# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Montana: a single-file, dependency-light web app. Click a point in Montana
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/mt/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
sixth state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `mt/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or Open States' export, because the Legislature's own data cannot yet say who sits today: **County** (`county`, all 56, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (2 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Montana Senate** and **Montana House** (50 and 100 districts, TIGERweb's 2026 state legislative districts joined to Open States' export of current legislators), the TIGERweb fabric drawn from mirrored tile archives — **City or Town** (`municipality`, 127 incorporated places), **School District (Unified)**, **(Elementary)** and **(Secondary)** and **ZIP Code** — three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**) and **Tribal Government** (`tribal-government`, the Census's tribal land, joined to the government that holds it).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `mt/scripts/build_metro_outline.py --check` holds it to 56
INSIDE anchors, one per county, and 14 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN MONTANA IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 2 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `mt/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, 50 Senate and 100 House districts.
Measured 2026-11-12, every district in both chambers is the same as in TIGERweb's 2024 layers (5 and 6), intersection-over-union 1.0. The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage
rolls. **THE TWO CHAMBERS NEST**: every Senate district is House districts 2N-1 and 2N, so both maps are simplified in one shared topology and every Senate vertex is a House vertex. `check_nesting` asks, with no tolerance,
that every Senate vertex is a House vertex, and `--check` runs it offline on the shipped files in CI; there
is no way to rebuild one chamber alone. Both are simplified with Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATURE'S OWN DATA CANNOT SAY WHO SITS TODAY, SO THE MEMBERS COME FROM OPEN STATES** (Adam's
choice of 2026-11-10: the legislature's own site first, Open States as the fall back). Measured
2026-11-12: the member directory at `legislators.legmt.gov` fills itself in from the Legislature's own
member data, and that data already carries the terms beginning in January for members re-elected on 3
November 2026 — 154 records for 150 seats, 58 of them Senate records for 50 seats, with end dates of
2028 and 2030 beside the records of the members they will succeed — so the sitting members cannot be
told from it; the older `leg.mt.gov` roster answered 403 to this project's client.
`mt/scripts/build_mt_legislature_roster.py` reads `data.openstates.org/people/current/mt.csv`, compiled
from the Legislature's own pages: that day it named all 50 senators and all 100 representatives of the
69th Legislature. From each row it carries the name, party, district, the e-mail address at legmt.gov (all
150) and the member's page on legislators.legmt.gov; not the district telephone, which Open States
carries for 54 members, and never the address columns. robots.txt read 2026-11-12: `data.openstates.org`
answered 403, which RFC 9309 §2.3.1.3 reads as no robots.txt.

**MOST OF MONTANA IS IN NO CITY OR TOWN.** The **City or Town** layer is TIGERweb's incorporated places
(layer 4): 127 records, 73 towns, 52 cities and the balances of Butte-Silver Bow and Anaconda-Deer Lodge
County, about 1% of the state's land (4,572.2 of 376,973.5 km2, measured 2026-11-12). An empty card says
the point is outside every city and town and that the county is the local government there. **BUTTE-SILVER
BOW AND ANACONDA-DEER LODGE ARE EACH A CITY AND A COUNTY IN ONE CONSOLIDATED GOVERNMENT**, and both cards
say so. No mayor or council member is named yet (gap `mt-municipal-officeholders`).

**THREE SCHOOL LAYERS.** Measured 2026-11-12: 65 unified districts and 233 elementary districts, which
between them cover the state's land, and 97 secondary districts, which run the higher grades over the same
ground as the elementary districts, so a reader there is in two districts at once. No school board member
is named yet (gap `mt-school-board-members`).

**NO COUNTY OFFICIAL IS NAMED YET**, and the card says so rather than leave a reader to assume the office
is empty. Each county is governed by an elected board of county commissioners and elects officers such
as a clerk and recorder, a treasurer, a sheriff and a county attorney; Butte-Silver Bow and Anaconda-Deer
Lodge are the exceptions above. Recorded as gap `mt-county-officials`.

**TRIBAL GOVERNMENT DRAWS THE LAND OF EIGHT NATIONS AND NAMES NO COUNCIL YET** (`tribal-areas.json`,
since 2026-11-13). The Census keeps seven reservations and seven trust lands in Montana, measured
2026-11-12 with `scripts/tribal_areas.py --report Montana`: the Crow (9,262.3 km2), Fort Peck
(8,551.9 km2), Blackfeet (6,214.1 km2), Flathead (5,329.7 km2), Fort Belknap, Northern Cheyenne and
Rocky Boy's reservations, their trust lands, and the Montana part of the Turtle Mountain trust land
(232.4 km2, 53.4% of it), whose band is seated at Belcourt, North Dakota. All 14 pieces are drawn,
the two that cross the state line whole, each joined in `data/tribal-government-join.json` to the
government the Bureau of Indian Affairs lists for it, and the cards name the tribal districts the
Census draws on the Flathead, Fort Peck, Northern Cheyenne and Fort Belknap land. As published the
land made 1.47 MB, the Turtle Mountain trust land alone in 256 parts and the Crow trust land in 102,
larger than any state shipped at Census detail, so it goes through one Douglas-Peucker run at 3 m
and is 614 KB (167 KB gzipped), the worst stray 3.7 m against a 25 m ceiling (`SIMPLIFY` in
`scripts/build_tribal_areas.py`). No council is carried yet (`ROSTER_NOT_SOUGHT` in
`scripts/build_tribal_areas.py`), recorded in gap `mt-tribal-government`.

**THE ZIP LAYER HIDES OUTSIDE MONTANA.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The five TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the six officers Montana elects statewide (the governor,
lieutenant governor, attorney general, secretary of state, state auditor and superintendent of public
instruction) and both U.S. senators, from `mt/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`. The clerk of the Supreme Court and the Supreme Court's justices
are elected statewide too, and the Public Service Commission by district; none is listed.

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

- Metro: Montana (`montana`) — https://districtry.com/mt/
- Geocoders: address Photon (Montana-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Montana-bounded, serial >=1s queue)
- Ground truth: 46.58566,-112.01822 (Montana State Capitol, 1301 East 6th Avenue, Helena, Lewis and Clark County) → county Lewis and Clark County; us-house 2; mt-senate 41; mt-house 82. Negative point 49.15000,-107.00000 (Saskatchewan, Canada, north of the Montana line — outside Montana and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here, because it is in Canada (control: the Montana State Capitol returns Montana), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any outline in the change that opens the last thirteen states. IT IS IN CANADA, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 13 registered (political 4, safety 2, schools 3, geography 4); `registerLayer(` floor 10. Debug namespace `window.MontanaExplorer`.
- Scheduled workflows: `update-mt-congress-roster.yml` (Wed 22:45 UTC); `update-mt-legislature-roster.yml` (Thu 22:45 UTC); `mt-validate-sources.yml` (2nd of month 22:45 UTC).
- Source registry: `mt/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/mt/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/mt/ node mt/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 mt/scripts/validate_index.py mt/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 mt/scripts/build_metro_outline.py --check

# Nesting gate (every Senate vertex is a vertex of its House districts, offline):
python3 mt/scripts/build_legislative_boundaries.py --check

# Generated-region gate: per-instance facts live ONCE in mt/metro-worksheet.json;
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
which vendors Leaflet into `mt/scripts/vendor/leaflet/` (gitignored);
`mt/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Montana-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`mt/scripts/build_metro_outline.py`), `state-counties.json` (the counties, `mt/scripts/build_state_counties.py`),
and `congress-districts.json`, `mt-senate-districts.json` and `mt-house-districts.json`
(`mt/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m under an 8 m ceiling, the two chambers in one topology, refused unless the 2,000-random-point agreement gate, the 8 m fidelity ceiling and the exact nesting check all pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance mt`; 43,717 populated blocks holding all 1,084,225 people the 2020 census counted in Montana). All three maps are held to that count; the worst districts are +0.000% (congress), +7.293% (Senate District 38) and +13.749% (House District 76) of the raw-census ideal, and why the plan sits there is not on record. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 368 ZIP codes). Rosters:
`congress-roster.json` (`mt/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`mt-senate-members.json` and `mt-house-members.json` (`mt/scripts/build_mt_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`mt/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `mt/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
