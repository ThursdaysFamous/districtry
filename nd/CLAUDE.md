# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry North Dakota: a single-file, dependency-light web app. Click a point in North Dakota
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/nd/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
ninth state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `nd/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislative Branch's own member pages: **County** (`county`, all 53, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (the at-large district, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **North Dakota Senate** and **North Dakota House** (47 Senate districts and 48 House districts electing 94 representatives, TIGERweb's 2026 state legislative districts joined to the Legislative Branch's own member pages), the TIGERweb fabric drawn from mirrored tile archives — **City** (`municipality`, 355 incorporated cities), **School District (Unified)** and **(Elementary)** and **ZIP Code** — three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**) and **Tribal Government** (`tribal-government`, the Census's tribal land, joined to the government that holds it).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `nd/scripts/build_metro_outline.py --check` holds it to 53
INSIDE anchors, one per county, and 14 OUTSIDE anchors over the state line and offshore.

**NORTH DAKOTA ELECTS ONE MEMBER OF THE U.S. HOUSE, AT LARGE**, so its congressional "map" is the
whole state. TIGERweb carries it on layer 0 (the 120th Congress) as one record, CD120 "00", named
"Congressional District (at Large)", and on layer 4 (the 119th) as the same record.
`nd/scripts/build_legislative_boundaries.py` still measures the two against each other until 3 January
2027 (intersection-over-union 1.0, measured 2026-11-12), and refuses on or after 3 January 2029, so a
person reads the apportionment after the 2030 census before anything is drawn. The U.S. House card names
the district by that record's own name rather than "District 0", which nobody writes.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, 47 Senate districts and 48 House features (46 districts electing two representatives each and the subdistricts 4A and 4B electing one each), 94 representatives in all.
Measured 2026-11-12 against TIGERweb's 2024 layers (5 and 6): 45 of the 47 Senate districts are identical, District 29 matches to the sixth decimal and District 12 differs by a sliver (intersection-over-union 0.99997); the House layer moves the same line. The newer vintage is drawn. The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage
rolls. **THE TWO CHAMBERS NEST**: every House feature (46 whole districts and the subdistricts 4A and 4B) lies wholly inside the Senate district of its own number, so both maps are simplified in one shared topology. `check_nesting` asks, with no tolerance,
that every Senate vertex is a House vertex, and `--check` runs it offline on the shipped files in CI; there
is no way to rebuild one chamber alone. Both are simplified with Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE LEGISLATIVE BRANCH'S OWN PAGES** (the 69th Assembly's members-by-district
page, `ndlegis.gov/assembly/69-2025/regular/members/members-by-district`, then each member's biography
page, `nd/scripts/build_nd_legislature_roster.py`). The list prints every member who has served in the
assembly with a status line for anyone whose service began or ended during it; measured 2026-11-12 it
carried 148 members, seven of whom had resigned or died, and the script drops every member whose status
is not "Active" or absent and stops on a status word it does not know. The 141 kept fill every seat: 47
senators and 94 representatives. **DISTRICT 4'S TWO REPRESENTATIVES ARE ELECTED FROM SUBDISTRICTS 4A AND
4B**, which TIGERweb draws as two districts, so the House roster is keyed by district or subdistrict with
`seats` and `members`. Each biography page prints the member's e-mail address at ndlegis.gov and, for
most, telephones under their own labels ("Cell", "Home", "Work"), which ship with those labels under the
fleet's rule of 2026-10-17; a number labelled "Fax" does not. **WHICH ASSEMBLY**: terms begin on 1
December after the election, so from that day the script reads the 70th Assembly's page (70-2027) and
stops if it is not yet published, rather than show the 69th's members after their terms end. robots.txt
read 2026-11-12: its `*` group disallows Drupal's own paths only; pages are read one a second.

**MOST OF NORTH DAKOTA IS IN NO CITY.** The **City** layer is TIGERweb's incorporated places (layer 4): 355
records, every one an active city, under 1% of the state's land (1,552.3 of 178,694.4 km2, measured
2026-11-12). An empty card says the point is outside every city and that the county is the local
government there, with the civil township where one is organized. No mayor or commissioner is named yet
(gap `nd-municipal-officeholders`).

**TWO SCHOOL LAYERS.** Measured 2026-11-12: 147 unified districts and 20 elementary districts, which
between them cover the state's land, and nothing on TIGER's secondary layer, so it is not drawn. No school
board member is named yet (gap `nd-school-board-members`).

**NO COUNTY OFFICIAL IS NAMED YET**, and the card says so rather than leave a reader to assume the office
is empty. Each county is governed by an elected board of county commissioners and elects officers such
as an auditor, a treasurer, a recorder, a sheriff and a state's attorney. Recorded as gap
`nd-county-officials`.

**TRIBAL GOVERNMENT DRAWS THE LAND OF FIVE NATIONS AND NAMES NO COUNCIL YET** (`tribal-areas.json`,
since 2026-11-13). The Census keeps five reservations and two trust lands in North Dakota, measured
2026-11-12 with `scripts/tribal_areas.py --report "North Dakota"`: the Fort Berthold (4,099.0 km2),
Spirit Lake and Turtle Mountain reservations, the North Dakota parts of the Standing Rock (30.8% of
it) and Lake Traverse (7.1%) reservations, and the Turtle Mountain (46.1%) and Lake Traverse trust
lands. All seven pieces are drawn, the four that cross the state line whole, each joined in
`data/tribal-government-join.json` to the government the Bureau of Indian Affairs lists for it; the
Sisseton-Wahpeton Oyate is seated at Agency Village, South Dakota. The cards name the tribal
districts the Census draws on the Fort Berthold, Spirit Lake, Standing Rock and Lake Traverse land.
No council is carried yet (`ROSTER_NOT_SOUGHT` in `scripts/build_tribal_areas.py`), recorded in gap
`nd-tribal-government`.

**THE ZIP LAYER HIDES OUTSIDE NORTH DAKOTA.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The four TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the ten officers North Dakota elects statewide as single officers
(the governor, lieutenant governor, attorney general, secretary of state, state treasurer, state auditor,
agriculture commissioner, insurance commissioner, superintendent of public instruction and tax
commissioner) and both U.S. senators, from `nd/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`. **THE LIEUTENANT GOVERNOR IS READ OFF THE GOVERNOR'S HOME PAGE**,
which names her "Lt. Gov. Strinden" and never prints her given name; its `/lt-governor` page still
describes Brent Sanford, who left the office in 2024, so it is not read. The three members of the Public
Service Commission are elected statewide too and are not listed yet. The attorney general's site did not
answer one build run on 2026-11-12 and was read on the next.

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

- Metro: North Dakota (`northdakota`) — https://districtry.com/nd/
- Geocoders: address Photon (North Dakota-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, North Dakota-bounded, serial >=1s queue)
- Ground truth: 46.82078,-100.78267 (North Dakota State Capitol, 600 East Boulevard Avenue, Bismarck, Burleigh County) → county Burleigh County; us-house Congressional District (at Large); nd-senate 35; nd-house 35. Negative point 49.15000,-99.00000 (Manitoba, Canada, north of the North Dakota line — outside North Dakota and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here, because it is in Canada (control: the North Dakota State Capitol returns North Dakota), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any outline in the change that opens the last thirteen states. IT IS IN CANADA, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 12 registered (political 4, safety 2, schools 2, geography 4); `registerLayer(` floor 9. Debug namespace `window.NorthDakotaExplorer`.
- Scheduled workflows: `update-nd-congress-roster.yml` (Wed 23:27 UTC); `update-nd-legislature-roster.yml` (Thu 23:27 UTC); `nd-validate-sources.yml` (2nd of month 23:27 UTC).
- Source registry: `nd/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/nd/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/nd/ node nd/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 nd/scripts/validate_index.py nd/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 nd/scripts/build_metro_outline.py --check

# Nesting gate (every Senate vertex is a vertex of its House districts, offline):
python3 nd/scripts/build_legislative_boundaries.py --check

# Generated-region gate: per-instance facts live ONCE in nd/metro-worksheet.json;
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
which vendors Leaflet into `nd/scripts/vendor/leaflet/` (gitignored);
`nd/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything North Dakota-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the U.S. House and chamber layers use the fenced factory helper `registerIlgaChamber` (which renders a vacancy record as a vacant seat with its reason and source, and a district electing several members as every member it elects), the County, municipality and school cards are bespoke `registerLayer` blocks, the ZIP layer `registerPolygonLayer`, and the three nearest-N layers `registerNearestPointLayer`. Two invariants pervade the
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
`nd/scripts/build_metro_outline.py`), `state-counties.json` (the counties, `nd/scripts/build_state_counties.py`),
and `congress-districts.json`, `nd-senate-districts.json` and `nd-house-districts.json`
(`nd/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m under an 8 m ceiling, the two chambers in one topology, refused unless the 2,000-random-point agreement gate, the 8 m fidelity ceiling and the exact nesting check all pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance nd`; 40,198 populated blocks holding all 779,094 people the 2020 census counted in North Dakota). The Senate map is held to that count; its worst district is -4.992% of the raw-census ideal. The at-large congressional district has no number to key and no ideal but the state, and the House is not held, because one ideal describes neither a two-member district nor a one-member half. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 388 ZIP codes). Rosters:
`congress-roster.json` (`nd/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`nd-senate-members.json` and `nd-house-members.json` (`nd/scripts/build_nd_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`nd/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
both chamber files to one record per seat, and each multi-member district to the number of members it elects.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `nd/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
