# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Nebraska: a single-file, dependency-light web app. Click a point in Nebraska
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/ne/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
second state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `ne/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own senator pages: **County** (`county`, all 93, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (3 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Nebraska Legislature** (`ne-legislature`, 49 districts, TIGERweb's 2026 upper-house districts joined to the Legislature's own senator pages), the TIGERweb fabric drawn from mirrored tile archives — **City or Village** (`municipality`, 528 incorporated places), **School District** (244 unified districts) and **ZIP Code** — three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**) and **Tribal Government** (`tribal-government`, the Census's tribal land, joined to the government that holds it).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `ne/scripts/build_metro_outline.py --check` holds it to 93
INSIDE anchors, one per county, and 16 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN NEBRASKA IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 3 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `ne/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**NEBRASKA'S LEGISLATURE HAS ONE CHAMBER, AND IT IS NONPARTISAN** (Nebraska Constitution, Article III,
Section 1): 49 senators, one from each of 49 districts, drawn from TIGERweb's 2026 upper-house districts
(layer 1; layer 2 carries nothing for Nebraska). Measured 2026-11-12, every district is the same as in
TIGERweb's 2024 layer 5 (intersection-over-union 1.0). The builder refuses if the layer's name changes,
since TIGERweb renumbers its layers when a vintage rolls, and with no second map nothing nests, so the one
map is simplified on its own, Douglas-Peucker at 5 m under an 8 m ceiling. The app registers one chamber layer, `ne-legislature`.

**THE SENATORS COME FROM THE LEGISLATURE'S OWN PAGES** (`nebraskalegislature.gov/senators/senator_list.php`,
then each district's senator page, `ne/scripts/build_ne_legislature_roster.py`): the list gives each
senator's name and district, and the senator page the Capitol telephone, which it labels with nothing,
and an e-mail address at leg.ne.gov. Measured 2026-11-12: all 49. Nebraska's ballot names no party, so
no party is carried and the card prints none. The office address lines, committees, staff and
photograph are never read. robots.txt read 2026-11-12: its `*` group disallows three search pages and
states `Crawl-delay: 3`, which the script honours between requests.

**MOST OF NEBRASKA IS IN NO CITY OR VILLAGE.** The **City or Village** layer is TIGERweb's incorporated
places (layer 4): 528 records, 381 villages and 147 cities, every one an active government, about 1% of
the state's land (2,092.9 of 198,950.7 km2, measured 2026-11-12). An empty card says the point is outside
every city and village and that the county is the local government there, with the township in the 20
counties that kept township government. No mayor, council or village board member is named yet (gap
`ne-municipal-officeholders`).

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 244 unified districts for Nebraska and nothing on its
elementary or secondary layers (measured 2026-11-12), so those two layers are not drawn. No school board
member is named yet (gap `ne-school-board-members`).

**NO COUNTY OFFICIAL IS NAMED YET**, and the card says so rather than leave a reader to assume the office
is empty. Each county is governed by an elected board of commissioners or, in the counties that kept
township government, a board of supervisors, and elects officers such as a clerk, a treasurer, an
assessor, a sheriff and a county attorney. Recorded as gap `ne-county-officials`.

**TRIBAL GOVERNMENT DRAWS THE LAND OF SEVEN NATIONS AND NAMES ONE COUNCIL** (`tribal-areas.json` and
`tribal-councils.json`, since 2026-11-13). The Census keeps six reservations and three trust lands
in Nebraska, measured 2026-11-12 with `scripts/tribal_areas.py --report Nebraska`: the Omaha (787.1
km2, 98.0% of it in the state), Santee (477.9 km2) and Winnebago (457.5 km2, 99.4%) reservations,
the Nebraska parts of the Sac and Fox Nation and Iowa (KS-NE) reservations, whose nations are seated
in Kansas, a 2.236 km2 strip of the Pine Ridge Reservation in Sheridan County, and the Ponca,
Winnebago and Sac and Fox trust lands. All nine pieces are drawn, those that cross the state line
whole, each joined in `data/tribal-government-join.json` to the government the Bureau of Indian
Affairs lists for it. The Pine Ridge strip is kept by Adam's rule that a cross-border piece counts
at 1% of its area or 0.25 km2, and its card names the Oglala Sioux Tribe and the one tribal district
the Census draws there. The Winnebago Tribe's card names its council of nine, the list Iowa's card
already names for the reservation's Iowa part, read weekly from the tribe's own page by
`scripts/tribal_council_scraper.py` into this app's own network-first `tribal-councils.json`; if
that file fails to load, the card still names the tribe and names nobody. The Omaha Tribe's site
could not be reached from where this project is built (2026-10-10, `ROSTER_BLOCKED`), so its card
says so; the other five nations' councils are not carried yet (`ROSTER_NOT_SOUGHT` in
`scripts/build_tribal_areas.py`), recorded in gap `ne-tribal-government`.

**THE ZIP LAYER HIDES OUTSIDE NEBRASKA.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the six officers Nebraska elects statewide (the governor,
lieutenant governor, attorney general, secretary of state, state treasurer and auditor of public
accounts) and both U.S. senators, from `ne/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`. The Public Service Commission, the University's Board of Regents
and the State Board of Education are elected by district, so they are not listed.

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

- Metro: Nebraska (`nebraska`) — https://districtry.com/ne/
- Geocoders: address Photon (Nebraska-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Nebraska-bounded, serial >=1s queue)
- Ground truth: 40.80814,-96.69957 (Nebraska State Capitol, 1445 K Street, Lincoln, Lancaster County) → county Lancaster County; us-house 1; ne-legislature 28. Negative point 42.87000,-97.05000 (Clay County, South Dakota, north of the Missouri River — outside Nebraska and inside permalink_gate, so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names South Dakota here (control: the Nebraska State Capitol returns Nebraska), none of the state's shipped boundary files contains it, and of every outline in the fleet only South Dakota's does (South Dakota goes live in the same change as Nebraska). Nebraska borders no water and no other country, and every one of its neighbours (South Dakota, Iowa, Missouri, Kansas, Colorado and Wyoming) is live once this change lands, so no point this app's gate reaches lies outside every instance: the point stays where it is, as Illinois's sits in Indiana's waters, and a selection the app makes from its own link never leaves for another app.).
- Layers: 10 registered (political 3, safety 2, schools 1, geography 4); `registerLayer(` floor 7. Debug namespace `window.NebraskaExplorer`.
- Scheduled workflows: `update-ne-congress-roster.yml` (Wed 22:13 UTC); `update-ne-legislature-roster.yml` (Thu 22:13 UTC); `ne-validate-sources.yml` (2nd of month 22:13 UTC).
- Source registry: `ne/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/ne/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/ne/ node ne/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 ne/scripts/validate_index.py ne/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 ne/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in ne/metro-worksheet.json;
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
which vendors Leaflet into `ne/scripts/vendor/leaflet/` (gitignored);
`ne/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Nebraska-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`ne/scripts/build_metro_outline.py`), `state-counties.json` (the counties, `ne/scripts/build_state_counties.py`),
and `congress-districts.json` and `ne-legislature-districts.json`
(`ne/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m under an 8 m ceiling, the one legislative map, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance ne`; 79,779 populated blocks holding all 1,961,504 people the 2020 census counted in Nebraska). Both maps are held to that count; the worst districts are -0.002% (congress) and -4.960% (the Legislature) of the raw-census ideal. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 585 ZIP codes). Rosters:
`congress-roster.json` (`ne/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`ne-legislature-members.json` (`ne/scripts/build_ne_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`ne/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
the chamber file to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `ne/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
