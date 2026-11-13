# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Alaska: a single-file, dependency-light web app. Click a point in Alaska
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/ak/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
tenth state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `ak/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own member pages: **Borough or Census Area** (`county`, all 30, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (the at-large district, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Alaska Senate** and **Alaska House** (20 lettered and 40 numbered districts, TIGERweb's 2026 state legislative districts joined to the Legislature's own member pages), the TIGERweb fabric drawn from mirrored tile archives — **City** (`municipality`, 149 incorporated places), **School District** (52 unified districts) and **ZIP Code** — three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**) and **Tribal Government** (`tribal-government`, the Census's tribal land, joined to the government that holds it).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every borough or census area is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `ak/scripts/build_metro_outline.py --check` holds it to 30
INSIDE anchors, one per borough or census area, and 9 OUTSIDE anchors over the Canadian border, across the Bering Strait in Russia and offshore.

**THE NEAR ISLANDS PAST THE 180TH MERIDIAN ARE LEFT OUT.** Attu, Agattu, Shemya and the rest of the western Aleutians lie at east longitudes 172 to 180, which a web map draws on the far side of the world. Every builder here drops each polygon part outside longitudes -180 to -125 whole before anything is simplified, so the outline, the borough file and the legislative maps all stop at the meridian; a part straddling the box stops the build.

**ALASKA ELECTS ONE MEMBER OF THE U.S. HOUSE, AT LARGE**, so its congressional "map" is the
whole state. TIGERweb carries it on layer 0 (the 120th Congress) as one record, CD120 "00", named
"Congressional District (at Large)", and on layer 4 (the 119th) as the same record.
`ak/scripts/build_legislative_boundaries.py` still measures the two against each other until 3 January
2027 (intersection-over-union 1.0, measured 2026-11-12), and refuses on or after 3 January 2029, so a
person reads the apportionment after the 2030 census before anything is drawn. The U.S. House card names
the district by that record's own name rather than "District 0", which nobody writes.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, 20 Senate and 40 House districts.
Measured 2026-11-12, every district in both chambers is the same as in TIGERweb's 2024 layers (5 and 6), intersection-over-union 1.0. The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage
rolls. **THE TWO CHAMBERS NEST**: every Senate district (lettered A to T) is two House districts (1 and 2 in A, 3 and 4 in B, and so on to 39 and 40 in T), so both maps are simplified in one shared topology and every Senate vertex is a House vertex. `check_nesting` asks, with no tolerance,
that every Senate vertex is a House vertex, and `--check` runs it offline on the shipped files in CI; there
is no way to rebuild one chamber alone. Both are simplified with Douglas-Peucker at 4 m under an 8 m ceiling (4 m rather than the 5 m the other newer states use, because 5 m failed the ceiling here: the at-large congressional district strayed 8.6 m at Alaska's high latitudes, measured 2026-11-12).

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN PAGES** (`akleg.gov/senate.php` and `/house.php`,
`ak/scripts/build_ak_legislature_roster.py`): every sitting member of the 34th Legislature with a link to
the member's page, party, district, a Capitol telephone, a toll-free number and an e-mail link. Measured
2026-11-12: all 20 senators and all 40 representatives. **THE PAGE HIDES EACH E-MAIL ADDRESS BEHIND
CLOUDFLARE'S E-MAIL PROTECTION LINK**, which the page's own script turns back into the address for every
visitor; the script does the same decoding, which reads the page as published, and carries an address
only at akleg.gov. The Capitol number ships unlabelled and the toll-free number labelled "toll-free",
under the fleet's rule of 2026-10-17; a number printed for two or more members is not carried. Each
entry's City line, which names the member's home town, is never read. The Senate roster is keyed by
letter and the House by number. robots.txt is read before the two requests.

**MOST OF ALASKA IS IN NO CITY.** The **City** layer is TIGERweb's incorporated places (layer 4): 149
records, 145 cities and the consolidated governments of Anchorage, Juneau, Sitka and Wrangell, each a city
and a borough in one, about 2% of the state's land (31,679.7 of 1,479,942.8 km2, measured 2026-11-12). An
empty card says the point is outside every city; an organized borough is the local government there, and
in the Unorganized Borough, which has no borough government, the state provides its services. No mayor or
council member is named yet (gap `ak-municipal-officeholders`).

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 52 unified districts for Alaska and nothing on its
elementary or secondary layers (measured 2026-11-12), so those two layers are not drawn. No school board
member is named yet (gap `ak-school-board-members`).

**ALASKA HAS BOROUGHS, NOT COUNTIES, AND THE CARD IS LABELLED BOROUGH OR CENSUS AREA.** TIGER's 30 county
equivalents are the 19 organized boroughs, each governed by an elected assembly and mayor (Anchorage,
Juneau, Sitka, Skagway, Wrangell and Yakutat each a city and a borough in one government), and the 11
census areas the Census Bureau draws over the Unorganized Borough, which has no borough government and
where the state provides the services a borough would. No assembly member or mayor is named yet, and the
card says so (gap `ak-county-officials`).

**TRIBAL GOVERNMENT DRAWS THE ANNETTE ISLAND RESERVE AND NAMES NO COUNCIL YET**
(`tribal-areas.json`, since 2026-11-13). The Census keeps one reservation in Alaska, the Metlakatla
Indian Community's Annette Island Reserve (587.3 km2), and no trust land, measured 2026-11-12 with
`scripts/tribal_areas.py --report Alaska`. It is drawn and joined in
`data/tribal-government-join.json` to the community, seated at Metlakatla, from the Bureau of Indian
Affairs' list. Alaska Native villages and corporations are statistical areas, which the fleet draws
only in Oklahoma, so a point anywhere else in Alaska is told it is on no tribal land the Census
draws for a government, in words that say why. No council is carried yet (`ROSTER_NOT_SOUGHT` in
`scripts/build_tribal_areas.py`), recorded in gap `ak-tribal-government`.

**THE ZIP LAYER HIDES OUTSIDE ALASKA**, as it does in every app. A ZCTA carries no state
field, so the coverage test reads the shipped outline rather than the service, and the smoke test asserts
both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** lists the two officers Alaska elects statewide (the governor and
lieutenant governor) and both U.S. senators, from `ak/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`. **THE LIEUTENANT GOVERNOR IS LISTED WITHOUT A NAME**:
`ltgov.alaska.gov` sends its own certificate twice and no intermediate certificate (measured 2026-11-12
with `openssl s_client`), so no client that checks certificates can read it, and the other state pages
tried either closed the connection or have the same fault. The card says the office's own site could not
be read; the attorney general and the commissioners are appointed.

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

- Metro: Alaska (`alaska`) — https://districtry.com/ak/
- Geocoders: address Photon (Alaska-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Alaska-bounded, serial >=1s queue)
- Ground truth: 58.30196,-134.41035 (Alaska State Capitol, 120 4th Street, Juneau, Juneau City and Borough) → county Juneau City and Borough; us-house Congressional District (at Large); ak-senate B; ak-house 4. Negative point 57.70000,-140.50000 (the Gulf of Alaska about 200 km south of Yakutat — outside Alaska and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here, because it is open water (control: the Alaska State Capitol returns Alaska), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any outline in the change that opens the last thirteen states. IT IS OPEN WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 11 registered (political 4, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.AlaskaExplorer`.
- Scheduled workflows: `update-ak-congress-roster.yml` (Wed 23:33 UTC); `update-ak-legislature-roster.yml` (Thu 23:33 UTC); `ak-validate-sources.yml` (2nd of month 23:33 UTC).
- Source registry: `ak/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ak/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ak/ node ak/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ak/scripts/validate_index.py ak/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 ak/scripts/build_metro_outline.py --check

# Nesting gate (every Senate vertex is a vertex of its House districts, offline):
python3 ak/scripts/build_legislative_boundaries.py --check

# Generated-region gate: per-instance facts live ONCE in ak/metro-worksheet.json;
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
which vendors Leaflet into `ak/scripts/vendor/leaflet/` (gitignored);
`ak/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Alaska-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`ak/scripts/build_metro_outline.py`), `state-counties.json` (the boroughs and census areas, `ak/scripts/build_state_counties.py`),
and `congress-districts.json`, `ak-senate-districts.json` and `ak-house-districts.json`
(`ak/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 4 m under an 8 m ceiling (4 m rather than the 5 m the other newer states use, because 5 m failed the ceiling here: the at-large congressional district strayed 8.6 m at Alaska's high latitudes, measured 2026-11-12), the two chambers in one topology, refused unless the 2,000-random-point agreement gate, the 8 m fidelity ceiling and the exact nesting check all pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance ak`; 11,763 populated blocks holding 733,159 of the 733,391 people the 2020 census counted in Alaska, every one but those past the 180th meridian). The House map is held to that count; its worst district is -4.809% of the raw-census ideal. **THE FILES LEAVE OUT THE 232 PEOPLE LIVING PAST THE 180TH MERIDIAN**, on the Near Islands, because the app's own outline stops there (the census counted 733,391 in Alaska), and `build_block_population.py` fails if that number moves. The lettered Senate is not held, because the numbered reading cannot key it; each Senate district is two House districts, and the House is held. The at-large congressional district has no number to key. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 244 ZIP codes). Rosters:
`congress-roster.json` (`ak/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`ak-senate-members.json` and `ak-house-members.json` (`ak/scripts/build_ak_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`ak/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `ak/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
