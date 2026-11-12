# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Washington: a single-file, dependency-light web app. Click a point in Washington (or
search an address) and it reports every civic district containing that point and who represents
you there. It serves at **districtry.com/wa/** as a folder of the consolidated districtry repo,
following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the fifth state of batch
2 of the state-level launch Adam asked for on 2026-11-10 (Texas, Florida, Ohio, California,
Washington), in his chosen order: built dark, with the deploy excluding `wa/**`, and opened with
the rest of its batch in one go-live change on Adam's own "merge", which narrowed that exclude,
added its `metros.json` entry and gave it a `layer-concepts.json` column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own pages: **County** (`county`, all 39, Census TIGERweb, the state outline
the coverage wash covers), **U.S. House** (10 districts, TIGERweb geometry joined to the
public-domain unitedstates/congress-legislators roster), **Washington Senate District** and
**Washington House District** (`wa-senate`, `wa-house`, the same 49 districts, joined to the
Legislature's member pages), the TIGERweb fabric drawn from mirrored tile archives — **City or
Town** (`municipality`, 281 incorporated places), **School District** (295 unified districts) and
**ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**,
**Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline (one ring, 39 counties inside and 15 outside anchors,
measured by its `--check`) and the wash has no lighter band (`coverage_key` with `outside` and
`edge` only).

**NEITHER OF WASHINGTON'S NEIGHBOURS HAS AN APP**, so no live app chose a test point inside
Washington for want of coverage, and the go-live change's audit found none (2026-11-11, every
coordinate in every app's smoke test, worksheet and outline builder). Washington's own negative
point is in Victoria, British Columbia, across the Strait of Juan de Fuca, and never moves.

**THE CONGRESSIONAL MAP IS THE 2022 MAP, FROM TIGERweb LAYER 0 (THE 120TH CONGRESS).** Measured
2026-11-11, layer 0 and layer 4 (the 119th Congress's) carry the same 10 districts, so layer 0 is
right before and after 3 January 2027. `wa/scripts/build_legislative_boundaries.py` refuses if the
two stop matching before that date, and refuses on or after 3 January 2029 so a person reads which
map the 2028 election used before anything is drawn.

**ONE MAP SERVES BOTH CHAMBERS.** Washington elects one senator and two representatives (Position 1
and Position 2) from each of the same 49 legislative districts. TIGERweb carries the plan twice, as
layer 1 (upper) and layer 2 (lower); the builder measures them against each other on every build
and refuses unless they are the same 49 districts, then writes layer 1 ONCE as
`wa-legislative-districts.json`, which both the Senate and House layers read, so the two layers'
lines cannot part. Douglas-Peucker at 5 m under an 8 m ceiling.

**A HOUSE DISTRICT ELECTS TWO REPRESENTATIVES, AND THE CARD NAMES BOTH**, through the
`{seats: 2, members: [...]}` roster shape Arizona's House brought to the engine's chamber factory
(`seatMembers` in `engine/index.html/chamber-factory.txt`). A district the Legislature lists fewer
members for ships those listed, dated, and the card says how many are missing: on 2026-11-11 the
member list gave House District 16 one representative, so 97 of the 98 House seats are named.
`scripts/validate_chamber_rosters.py` holds the shape.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN PAGES** (`https://leg.wa.gov/legislators/` and
each member's page under `/legislators/member/`, `wa/scripts/build_wa_legislature_roster.py`). The
member list gives each sitting member's chamber, district and party, and each member's page the
name, the district and position, and the Olympia office and telephone. No page prints an e-mail
address: each links a contact form on `app.leg.wa.gov`, whose robots.txt says `Disallow: /` to
every client and which is never read. District offices and photographs are never read.
leg.wa.gov serves no robots.txt (404 on 2026-11-11, allow-all under RFC 9309), read through
`scripts/robots_policy.py` with the crawling client, and the host is paced at one request a
second. The members elected on 3 November 2026 take office in January 2027, and the weekly
refresh carries them when the Legislature posts them.

**MOST OF WASHINGTON IS IN NO CITY OR TOWN.** The **City or Town** layer is TIGERweb's
incorporated places (layer 4): 212 cities and 69 towns, every one recorded as an active
government, about 2.6% of the state's land (measured 2026-11-11). An empty card says the point is
outside every city and town, that the county is the local government there, and that on a tribal
nation's land the nation's own government governs as well. The card still handles the Census's
inactive status, which no Washington place carries today.

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 295 unified districts for Washington and nothing
on its elementary or secondary layers (measured 2026-11-11), so those two layers are not drawn.
No school board member is named yet (gap `wa-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Recorded as gaps `wa-county-officials` and
`wa-municipal-officeholders`. The land of Washington's tribal nations is not drawn yet: the
Census keeps 28 reservations and 22 off-reservation trust lands in the state (`wa/WATCH.md`).

**THE ZIP LAYER HIDES OUTSIDE WASHINGTON.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves. The archive keeps 606 of the 740 ZCTAs in the app's box,
and the ZIP search lists 602 of them (measured 2026-11-11).

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the nine officers Washington elects statewide (the
governor, lieutenant governor, secretary of state, treasurer, auditor, attorney general,
commissioner of public lands, superintendent of public instruction and insurance commissioner)
and both U.S. senators, from `wa/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`. Washington's voters also elect the Supreme Court
statewide, and its justices are not listed yet.

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

- Metro: Washington (`washington`) — https://districtry.com/wa/
- Geocoders: address Photon (Washington-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Washington-bounded, serial >=1s queue)
- Ground truth: 47.03579,-122.90494 (The Legislative Building, Olympia, Thurston County. Measured 2026-11-11 against the shipped files: 3,815 m inside its legislative district and 13,515 m inside its congressional district and county.) → county Thurston County; us-house 10; wa-senate 22; wa-house 22. Negative point 48.42840,-123.36560 (Victoria, British Columbia, across the Strait of Juan de Fuca — outside Washington and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-11: TIGERweb's state layer places it in no state (control: the Legislative Building in Olympia returns Washington), none of the state's shipped boundary files contains it, and none of the outlines in fleet-outlines.json does. IT IS IN CANADA, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 10 registered (political 3, safety 2, schools 1, geography 4); `registerLayer(` floor 6. Debug namespace `window.WashingtonExplorer`.
- Scheduled workflows: `update-wa-congress-roster.yml` (Tue 21:23 UTC); `update-wa-legislature-roster.yml` (Thu 21:23 UTC); `wa-validate-sources.yml` (1st of month 23:37 UTC).
- Source registry: `wa/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/wa/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/wa/ node wa/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 wa/scripts/validate_index.py wa/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 wa/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in wa/metro-worksheet.json;
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
which vendors Leaflet into `wa/scripts/vendor/leaflet/` (gitignored);
`wa/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Washington-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the three chamber layers use the fenced factory helper `registerIlgaChamber` (which renders a
vacancy record as a vacant seat with its reason and source), the County and municipality cards
are bespoke `registerLayer` blocks, the school layer `registerPolygonLayer`, and the three
nearest-N layers `registerNearestPointLayer`. Two invariants pervade the code: the
**stale-async guard** (`if (seq !== state.sequence) return;` after every await) and **per-layer
failure isolation** (a layer's failure shows a Retry inside its own card, never breaks the
others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards say who is not named instead of inventing a name. The chamber cards
degrade to the district number + the chamber's own member list on a roster miss, and a vacant
seat says it is vacant; the County, municipality and school district cards carry no roster and
**say so on the card**. External strings always render through `sanitize()`/`textContent`.
Roster refreshes always land as PRs for review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`wa/scripts/build_metro_outline.py` — one INSIDE anchor per county plus 15 OUTSIDE anchors in
Oregon, Idaho and British Columbia), `state-counties.json`
(`wa/scripts/build_state_counties.py`), and `congress-districts.json` and
`wa-legislative-districts.json` (`wa/scripts/build_legislative_boundaries.py` — Douglas-Peucker
at 5 m, refused unless the twin check, the 2,000-random-point agreement gate and the 8 m fidelity
ceiling pass). The TIGERweb fabric layers draw from tile archives under `data/app/tiles/`,
mirrored by `scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020
blocks under `data/app/population/` (`scripts/build_block_population.py --instance wa`;
7,705,281 people in 39 county files). The ZIP search reads `zip-index.json`
(`scripts/build_zip_index.mjs`). Rosters: `congress-roster.json`
(`wa/scripts/build_congress_roster.py`, from unitedstates/congress-legislators and the House
Clerk's vacancy list) and `wa-{senate,house}-members.json`
(`wa/scripts/build_wa_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed
PRs. `scripts/validate_chamber_rosters.py` holds both chamber files to their shapes.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `wa/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
