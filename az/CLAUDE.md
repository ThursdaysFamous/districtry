# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Arizona: a single-file, dependency-light web app. Click a point in Arizona
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/az/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
third state of batch 1 of the state-level launch Adam asked for on 2026-11-10 (Pennsylvania,
Nevada, Arizona, New Jersey, New Hampshire): built dark, with the deploy excluding `az/**`, and
opened with the rest of its batch in one go-live change on Adam's own "merge", which narrowed
that exclude, added its `metros.json` entry and gave it a `layer-concepts.json` column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own rosters: **County** (`county`, the 15 counties, Census TIGERweb, the
state outline the coverage wash covers), **U.S. House** (9 districts, TIGERweb geometry joined to
the public-domain unitedstates/congress-legislators roster), **Arizona Senate** and **Arizona
House** (`az-senate`, `az-house`, the same 30 districts, joined to each chamber's own member
roster), the TIGERweb fabric drawn from mirrored tile archives — **City or Town**
(`municipality`, 92 incorporated places), **School District (Unified)**, **(Elementary)** and
**(Secondary)** and **ZIP Code** — and three nearest-N layers from the USGS National Map
(**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only).

**THE CONGRESSIONAL MAP IS THE 2022 MAP, FROM TIGERweb LAYER 0 (THE 120TH CONGRESS).** The
Independent Redistricting Commission drew the 9 districts after the 2020 census. Measured
2026-11-10, layer 0 and layer 4 (the 119th Congress's) carry the same 9 districts, so layer 0 is
right before and after 3 January 2027. `az/scripts/build_legislative_boundaries.py` refuses if the
two stop matching before that date, and refuses on or after 3 January 2029 so a person reads which
map the 2028 election used before anything is drawn.

**ONE MAP SERVES BOTH CHAMBERS.** Arizona elects one senator and two representatives from each of
the same 30 legislative districts (Ariz. Const. art. 4, pt. 2, sec. 1). TIGERweb carries the
Commission's plan twice, as layer 1 (upper) and layer 2 (lower); the builder measures them against
each other on every build and refuses unless they are the same 30 districts, then writes layer 1
ONCE as `az-legislative-districts.json`, which both the Senate and House layers read. A reader
downloads it once, and the two layers' lines cannot part. Douglas-Peucker at 5 m under an 8 m
ceiling, the setting the newer states' builders carry.

**A HOUSE DISTRICT ELECTS TWO REPRESENTATIVES, AND THE CARD NAMES BOTH.** The House roster keys each
district to `{seats: 2, members: [...]}`, a shape the engine's chamber factory reads since this
instance (`seatMembers` in `engine/index.html/chamber-factory.txt`); the card lists every member
with their own row and offices and says the district elects two, each representing every point in
it. A district the roster lists fewer members for than it elects ships those listed, dated, and
the card says how many are missing. `scripts/validate_chamber_rosters.py` holds the shape. New
Jersey's General Assembly is the next chamber to use it.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN ROSTERS** (`www.azleg.gov/memberroster/`,
`az/scripts/build_az_legislature_roster.py`): one table per chamber, giving each current member's
name, district, party, e-mail address, Capitol room and Capitol telephone. Members who have left
keep a row marked inactive, which is not read; a leadership title after the name is not part of
the name. The rosters print no street address, so the office ships as the chamber, room and
telephone. robots.txt read 2026-11-10: its `*` group disallows search, XML, calendar and
document-formatting paths and nothing under `/memberroster/`, and it states a **Crawl-delay of 120
seconds**, which the builder and `az/scripts/validate_sources.py` both honour through
`robots_policy.HostPacer`. `apps.azleg.gov` says `Disallow: /` to every client and is never read.

**MOST OF ARIZONA IS IN NO CITY OR TOWN**, so the **City or Town** layer is TIGERweb's incorporated
places (layer 4): 92 cities and towns, each card saying which the Census records it as. Sun City,
an unincorporated community of about 39,000, is outside every one, and an empty card says the
point is outside every city and town, that the county is the local government there, and that on
a tribal nation's land the nation's own government governs as well. Census-designated places are
statistical areas with no government and are not drawn.

**THREE SCHOOL LAYERS, BECAUSE ARIZONA USES ALL THREE OF TIGER'S TILINGS.** Measured 2026-11-10 for
STATE='04': 98 unified records, 102 elementary districts and 15 union high school districts. The
unified layer and the elementary districts together cover the state, and the union high school
districts run grades 9 to 12 over about half of the elementary districts' ground, so a reader
there is in one elementary and one secondary district at once. Each card prints the grades the
Census records. **ONE OF THE 98 UNIFIED RECORDS IS NOT A DISTRICT**: the Census files ground no
school district covers under "School District Not Defined" (GEOID 0499997, 15,670 km2 of land,
Sun City in it), with grades PK to 12 like a real district, and the card names it as no school
district rather than a unified district running every grade (`azSchoolPlaceholder`, any GEOID
ending 99997, the Census's code for that placeholder in every state). No governing board member
is named yet (gap `az-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Recorded as gaps `az-county-officials` and
`az-municipal-officeholders`.

**TRIBAL GOVERNMENT DRAWS THE LAND OF 21 NATIONS AND NAMES NO COUNCIL YET** (`tribal-areas.json`,
since 2026-11-12). The Census keeps 21 reservations and 7 off-reservation trust lands in Arizona,
and all 28 pieces are drawn, each joined in `data/tribal-government-join.json` to the government
the Bureau of Indian Affairs lists for it, with its seat and, where the Bureau gives one, its
website. Five reservations cross the state line and are drawn whole: the Navajo Nation's (71.6% in
Arizona), the Colorado River Indian Reservation (83.8%), the Fort Mojave (70.0%), the Fort Yuma
(4.6%) and the Zuni (3.1%). Three nations are seated outside the state: the Fort Mojave Indian Tribe
in Needles and the Quechan Tribe in Winterhaven, California, and the Zuni Tribe in Zuni, New
Mexico. The Bureau lists no website for six of the 21 nations, so their cards link nothing, and it
writes the Zuni Tribe's as a bare host, which the builder links with the http scheme
(`_website` in `scripts/build_tribal_areas.py`). The Census draws tribal districts on the land of the
Gila River, Hopi, Navajo, Salt River and Tohono O'odham nations, and their cards list them. The
Census's own lines come to 3.9 MB, the Navajo Nation's land the bulk of it, so they are simplified
by Douglas-Peucker at 3 m and held to a 25 m ceiling, with every part and ring kept (`SIMPLIFY`
there says why 3 m and not Oklahoma's 20). The San Juan Southern Paiute Tribe is federally
recognized and the Census draws no land for it, so no card names it. No council is named yet
(`ROSTER_NOT_SOUGHT`, the Oklahoma shape): each nation's own page is read and its council moved
into `tribal-councils.json` one nation at a time, recorded in gap `az-tribal-government`.

**THE ZIP LAYER HIDES OUTSIDE ARIZONA.** A ZCTA carries no state field, so over the line the live
service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline, and
the smoke test asserts both halves.

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

- Metro: Arizona (`arizona`) — https://districtry.com/az/
- Geocoders: address Photon (Arizona-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Arizona-bounded, serial >=1s queue)
- Ground truth: 33.44812,-112.09699 (Arizona State Capitol, 1700 West Washington Street, Phoenix) → county Maricopa County; us-house 3; az-senate 11; az-house 11. Negative point 31.00000,-111.50000 (Sonora, Mexico, about 37 km south of the Arizona line between Nogales and Sasabe — outside Arizona and outside every other instance in the fleet, and inside permalink_gate (minLat 30.90) so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-10: TIGERweb's state layer names no state here (controls: the State Capitol and Tucson's city hall return Arizona, and a point in the open Pacific returns no state), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does. MEXICO BECAUSE NO INSTANCE WILL EVER SERVE IT: every U.S. neighbour of Arizona is in a later batch of the state-level launch, and a point on any of them would have to move the day that neighbour goes live.).
- Layers: 13 registered (political 4, safety 2, schools 3, geography 4); `registerLayer(` floor 10. Debug namespace `window.ArizonaExplorer`.
- Scheduled workflows: `update-az-congress-roster.yml` (Mon 20:43 UTC); `update-az-legislature-roster.yml` (Tue 20:43 UTC); `az-validate-sources.yml` (1st of month 22:33 UTC).
- Source registry: `az/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->
## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/az/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/az/ node az/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 az/scripts/validate_index.py az/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 az/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in az/metro-worksheet.json;
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
which vendors Leaflet into `az/scripts/vendor/leaflet/` (gitignored);
`az/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Arizona-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
seat says it is vacant; the County, City or Town and school district cards carry no roster and
**say so on the card**. External strings always render through `sanitize()`/`textContent`.
Roster refreshes always land as PRs for review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`az/scripts/build_metro_outline.py` — one INSIDE anchor per county plus 15 OUTSIDE anchors over
the state line), `state-counties.json` (`az/scripts/build_state_counties.py`), and
`congress-districts.json` and `az-legislative-districts.json`
(`az/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, refused unless the
2,000-random-point agreement gate, the 8 m fidelity ceiling and the layer-1/layer-2 twin check
all pass). The five TIGERweb fabric layers draw from tile archives under `data/app/tiles/`,
mirrored by `scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020
blocks under `data/app/population/` (`scripts/build_block_population.py --instance az`;
7,151,502 people in 107,938 blocks; the congressional map partitions them to within 0.001% of the
ideal and the legislative map's worst district is 5.415% under it). The ZIP search reads
`zip-index.json` (`scripts/build_zip_index.mjs`, 417 ZIP codes). Rosters: `congress-roster.json`
(`az/scripts/build_congress_roster.py`, from unitedstates/congress-legislators) and
`az-{senate,house}-members.json` (`az/scripts/build_az_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs. `scripts/validate_chamber_rosters.py` holds both chamber
files to their shape: one record per Senate district, and two members per House district.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `az/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
