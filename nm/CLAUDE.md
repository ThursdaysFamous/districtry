# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry New Mexico: a single-file, dependency-light web app. Click a point in New Mexico
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/nm/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
first state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `nm/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own member pages: **County** (`county`, all 33, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (3 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **New Mexico Senate** and **New Mexico House** (42 and 70 districts, TIGERweb's 2026 state legislative districts joined to the Legislature's own member pages), the TIGERweb fabric drawn from mirrored tile archives — **City, Town or Village** (`municipality`, 105 incorporated places), **School District** (89 unified districts) and **ZIP Code** — three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**) and **Tribal Government** (`tribal-government`, the Census's tribal land, joined to the government that holds it).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `nm/scripts/build_metro_outline.py --check` holds it to 33
INSIDE anchors, one per county, and 14 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN NEW MEXICO IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 3 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `nm/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, 42 Senate and 70 House districts.
Measured 2026-11-12, every district in both chambers is the same as in TIGERweb's 2024 layers (5 and 6), intersection-over-union 1.0. The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage
rolls, and there is no nesting rule between the chambers (a House district's largest share
inside one Senate district is as low as 0.31 of its area), so each map is simplified on its own,
Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN MEMBER PAGES** (`nmlegis.gov/Members/Legislator_List?T=S`
and `?T=R`, then each member's page, `nm/scripts/build_nm_legislature_roster.py`): the list gives each
member's name, party letter and district, and the member's page the e-mail address and up to two
telephones ("Phone" and "Alt Phone"). Measured 2026-11-12: all 42 senators and 68 of the 70
representatives; House Districts 37 and 64 were not on the list, so their records name nobody and say
so with the day they were read. 101 of the 110 e-mail addresses were at nmlegis.gov and the other
nine are addresses the members gave the Legislature, carried as the page prints them under the fleet's
rule of 2026-10-17; 27 members had a telephone. The member page's address field (a home or business
address for some members), occupation and legislative assistant's details are never read. robots.txt
read 2026-11-12: its `*` group disallows only `/*.axd`; the pages are read one a second.

**MOST OF NEW MEXICO IS IN NO CITY, TOWN OR VILLAGE.** The **City, Town or Village** layer is TIGERweb's
incorporated places (layer 4): 105 records, 48 villages, 37 cities and 20 towns, every one an active
government, about 1% of the state's land (3,067.3 of 314,199.6 km2, measured 2026-11-12). An empty card
says the point is outside every city, town and village and that the county is the local government
there. **LOS ALAMOS IS A COUNTY AND A MUNICIPALITY IN ONE GOVERNMENT**, run by an elected county
council, and its County card says so. No mayor or council member is named yet (gap
`nm-municipal-officeholders`).

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 89 unified districts for New Mexico and nothing on its
elementary or secondary layers (measured 2026-11-12), so those two layers are not drawn. No school board
member is named yet (gap `nm-school-board-members`).

**NO COUNTY OFFICIAL IS NAMED YET**, and the card says so rather than leave a reader to assume the office
is empty. Each county is governed by an elected board of county commissioners and elects officers such
as a clerk, a treasurer, an assessor, a sheriff and a probate judge; Los Alamos is the exception above.
Recorded as gap `nm-county-officials`.

**TRIBAL GOVERNMENT DRAWS THE LAND OF 24 NATIONS AND NAMES NO COUNCIL YET** (`tribal-areas.json`,
since 2026-11-13). The Census keeps 24 reservations and 13 off-reservation trust lands in New
Mexico, measured 2026-11-12 with `scripts/tribal_areas.py --report "New Mexico"`: the land of the 19
pueblos, the Jicarilla Apache Nation's and Mescalero Apache Tribe's reservations, the Fort Sill
Apache Indian Reservation (0.121 km2, Luna County), and the New Mexico parts of the Navajo Nation
(11,376.8 km2, 19.5% of the reservation, and 4,869.5 km2 of trust land), Ute Mountain and Zuni
reservations. All 37 pieces are drawn, the four that cross the state line whole, each joined in
`data/tribal-government-join.json` to the government the Bureau of Indian Affairs lists for it.
Three nations are seated outside the state: the Navajo Nation at Window Rock, Arizona, whose card
names the 54 chapters the Census draws on its New Mexico ground; the Ute Mountain Ute Tribe at
Towaoc, Colorado; and the Fort Sill Apache Tribe at Apache, Oklahoma. The Bureau gives Santa Fe as
the town for the pueblos of Nambe, Pojoaque, San Ildefonso and Tesuque, whose land lies north of the
city, and the cards give it as the Bureau does. The Bureau lists a website for only three of the 24
nations, so the other cards link none and say so. Drawn whole, the Navajo Nation made the file 3.63
MB, so the land goes through one Douglas-Peucker run at 3 m and is 1.30 MB (343 KB gzipped), the
worst stray 3.5 m against a 25 m ceiling (`SIMPLIFY` in `scripts/build_tribal_areas.py`). No council
is carried yet (`ROSTER_NOT_SOUGHT` in `scripts/build_tribal_areas.py`), recorded in gap
`nm-tribal-government`.

**THE ZIP LAYER HIDES OUTSIDE NEW MEXICO.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the seven officers New Mexico elects statewide (the governor,
lieutenant governor, attorney general, secretary of state, state auditor, state treasurer and
commissioner of public lands) and both U.S. senators, from `nm/data/source/statewide-officials.source.json`
through `scripts/build_statewide_officials.py`. The treasurer's own site, `www.nmto.gov`, could not be
reached from the build sandbox on 2026-11-12, so the state's portal at `www.nm.gov`, which lists every
statewide officer, is the page read for that office. The Public Education Commission is elected by
district and the Public Regulation Commission has been appointed since 2023, so neither is listed.

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

- Metro: New Mexico (`newmexico`) — https://districtry.com/nm/
- Geocoders: address Photon (New Mexico-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, New Mexico-bounded, serial >=1s queue)
- Ground truth: 35.68226,-105.93964 (New Mexico State Capitol, 490 Old Santa Fe Trail, Santa Fe, Santa Fe County) → county Santa Fe County; us-house 3; nm-senate 25; nm-house 47. Negative point 31.25000,-108.60000 (Sonora, Mexico, just south of New Mexico's bootheel — outside New Mexico and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here, because it is in Mexico (control: the New Mexico State Capitol returns New Mexico), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any outline in the change that opens the last thirteen states. IT IS IN MEXICO, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 11 registered (political 4, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.NewMexicoExplorer`.
- Scheduled workflows: `update-nm-congress-roster.yml` (Wed 22:05 UTC); `update-nm-legislature-roster.yml` (Thu 22:05 UTC); `nm-validate-sources.yml` (2nd of month 22:05 UTC).
- Source registry: `nm/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/nm/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/nm/ node nm/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 nm/scripts/validate_index.py nm/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 nm/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in nm/metro-worksheet.json;
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
which vendors Leaflet into `nm/scripts/vendor/leaflet/` (gitignored);
`nm/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything New Mexico-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`nm/scripts/build_metro_outline.py`), `state-counties.json` (the counties, `nm/scripts/build_state_counties.py`),
and `congress-districts.json`, `nm-senate-districts.json` and `nm-house-districts.json`
(`nm/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m under an 8 m ceiling, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance nm`; 56,605 populated blocks holding all 2,117,522 people the 2020 census counted in New Mexico). All three maps are held to that count; the worst districts are -0.001% (congress), -6.623% (Senate) and -6.903% (House) of the raw-census ideal, the legislative ones the four northwestern districts, and why the plan sits there is not on record. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 373 ZIP codes). Rosters:
`congress-roster.json` (`nm/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`nm-senate-members.json` and `nm-house-members.json` (`nm/scripts/build_nm_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`nm/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `nm/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
