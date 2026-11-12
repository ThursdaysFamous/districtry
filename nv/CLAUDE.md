# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Nevada: a single-file, dependency-light web app. Click a point in Nevada
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/nv/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
second state of batch 1 of the state-level launch Adam asked for on 2026-11-10 (Pennsylvania,
Nevada, Arizona, New Jersey, New Hampshire): built dark, with the deploy excluding `nv/**`, and
opened with the rest of its batch in one go-live change on Adam's own "merge", which narrowed
that exclude, added its `metros.json` entry and gave it a `layer-concepts.json` column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own pages: **County** (`county`, the 16 counties and Carson City, Census
TIGERweb, the state outline the coverage wash covers), **U.S. House** (4 districts, TIGERweb
geometry joined to the public-domain unitedstates/congress-legislators roster), **Nevada Senate**
and **Assembly** (21 and 42 districts, TIGERweb's 2026 state legislative districts joined to each
chamber's own member list), the TIGERweb fabric drawn from mirrored tile archives — **City**
(`municipality`, 19 incorporated places), **School District** (`school-district-unified`, 17) and
**ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**,
**Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only).

**THE CONGRESSIONAL MAP IS THE 2021 MAP, FROM TIGERweb LAYER 0 (THE 120TH CONGRESS).** The
Legislature enacted the 4 districts in November 2021. Measured 2026-11-10, layer 0 and layer 4
(the 119th Congress's) carry the same 4 districts, every intersection-over-union 1.0, so layer 0
is right before and after 3 January 2027. `nv/scripts/build_legislative_boundaries.py` refuses if
the two stop matching before that date, and refuses on or after 3 January 2029 so a person reads
which map the 2028 election used before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, the plan
the Legislature enacted in November 2021. Measured 2026-11-10 against the 2024 vintage (layers 5
and 6): every district identical, IoU 1.0. **EVERY SENATE DISTRICT IS EXACTLY TWO ASSEMBLY
DISTRICTS**, but not by number: Senate 16, which holds the Capitol, is Assembly 26 and 40, and
the measured pairing is `NESTING` in the builder. So the builder simplifies both chambers in ONE
mapshaper topology (`combine-files`, Douglas-Peucker at 5 m under an 8 m ceiling), the lesson of
Illinois's 2026-09-25 fix; it refuses a fetch whose pairing has moved, and `--check` proves offline
that every Senate vertex is a vertex of its two Assembly districts.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN PAGES** (`www.leg.state.nv.us`,
`nv/scripts/build_nv_legislature_roster.py`): each chamber's member list gives the party, the
district, the member's Carson City room and telephone, an e-mail address and, for some, a work
telephone; each member's own page gives the name in reading order, from its title. The list's
head gives the chamber's mailing address for the session, which every card carries. Measured
2026-11-10, a week after the election: 20 of 21 senators and 30 of 42 Assembly members print an
e-mail address and a Carson City room, and the floors sit under that. The e-mail addresses are
hidden with Cloudflare's e-mail protection, which the builder decodes exactly as a visitor's
browser does. An address or work telephone printed for two or more members is an office's and
ships on nobody. The Las Vegas room (no building named), the fax line, the term and the counties
are never read. robots.txt read 2026-11-10: its `*` group disallows report, exhibit, fiscal-note,
lobbyist and opinion paths and nothing under `/App/Legislator/`, and states no Crawl-delay; the
host is paced at one request a second regardless.

**MOST OF NEVADA IS IN NO CITY**, so the **City** layer is TIGERweb's incorporated places (layer
4): 18 cities and Carson City, about 1% of the state's land. The Las Vegas Strip is outside every
city, and an empty card says the point is outside every city and that the county is the local
government there. Census-designated places and county subdivisions are statistical areas with no
government and are not drawn.

**CARSON CITY IS A CITY AND A COUNTY IN ONE GOVERNMENT** (county FIPS 32510, place 3209700), run
by an elected mayor and board of supervisors, and both its County and City cards say so.

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 17 unified districts for Nevada, as many as its 16
counties and Carson City, and no elementary or secondary ones. No trustee is named yet (gap
`nv-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Recorded as gaps `nv-county-officials` and
`nv-municipal-officeholders`.

**THE ZIP LAYER HIDES OUTSIDE NEVADA.** A ZCTA carries no state field, so over the line the live
service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline, and
the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
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

- Metro: Nevada (`nevada`) — https://districtry.com/nv/
- Geocoders: address Photon (Nevada-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Nevada-bounded, serial >=1s queue)
- Ground truth: 39.16384,-119.76637 (Nevada State Capitol, 101 North Carson Street, Carson City) → county Carson City; us-house 2; nv-senate 16; nv-assembly 40. Negative point 42.15000,-116.00000 (Owyhee County, Idaho, about 15 km north of the Nevada line — outside Nevada and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-10: TIGERweb's state layer names Idaho here (controls: the State Capitol returns Nevada, and a point in the open Pacific returns no state), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does. A POINT ON A NEIGHBOUR'S LAND MOVES THE DAY THAT NEIGHBOUR GOES LIVE: Idaho is in the last batch of the state-level launch, after California, Oregon, Utah and Arizona, which is why it was chosen, and the change that makes Idaho live moves this point.).
- Layers: 10 registered (political 3, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.NevadaExplorer`.
- Scheduled workflows: `update-nv-congress-roster.yml` (Mon 20:21 UTC); `update-nv-legislature-roster.yml` (Tue 20:21 UTC); `nv-validate-sources.yml` (1st of month 22:11 UTC).
- Source registry: `nv/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/nv/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/nv/ node nv/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 nv/scripts/validate_index.py nv/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 nv/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in nv/metro-worksheet.json;
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
which vendors Leaflet into `nv/scripts/vendor/leaflet/` (gitignored);
`nv/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Nevada-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
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
`nv/scripts/build_metro_outline.py` — one INSIDE anchor per county and Carson City plus 17 OUTSIDE
anchors in the five neighbouring states), `state-counties.json`
(`nv/scripts/build_state_counties.py`), and `congress-districts.json`, `nv-senate-districts.json`,
`nv-assembly-districts.json` (`nv/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m,
the two chambers in one topology, refused unless the 2,000-random-point agreement gate, the 8 m
fidelity ceiling and the exact nesting check all pass). The three TIGERweb fabric layers draw from
tile archives under `data/app/tiles/`, mirrored by `scripts/mirror_tiger_tiles.py`. The compare
screen counts people from Census 2020 blocks under `data/app/population/`
(`scripts/build_block_population.py --instance nv`; 3,104,614 people in 35,249 blocks, and all
three district maps partition them exactly). The ZIP search reads `zip-index.json`
(`scripts/build_zip_index.mjs`, 180 ZIP codes). Rosters: `congress-roster.json`
(`nv/scripts/build_congress_roster.py`, from unitedstates/congress-legislators) and
`nv-{senate,assembly}-members.json` (`nv/scripts/build_nv_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs. `scripts/validate_chamber_rosters.py` holds both chamber
files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `nv/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
