# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Virginia: a single-file, dependency-light web app. Click a point in Virginia (or search
an address) and it reports every civic district containing that point and who represents you
there. It will serve at **districtry.com/va/** as a folder of the consolidated districtry repo —
following the Wisconsin/Iowa shape (`docs/EXPANSION_GUIDE.md` Part 2), not the Illinois
root-scripts shape. **The instance is DARK**: no `metros.json` entry, `va/**` excluded from the
Pages deploy, nothing served and no landing card naming it. `va/WATCH.md` lists what go-live has to
do in one change, and what the plan builds before it.

**The layers** draw their shapes from a national publisher and name people from a national roster
or each chamber's own pages: **County or City** (`county`, 133 — the 95 counties and the 38
independent cities, Census TIGERweb, the coverage ring), **U.S. House** (11 districts, TIGERweb
geometry joined to the public-domain unitedstates/congress-legislators roster), **Virginia Senate**
and **House of Delegates** (40 and 100 districts, TIGERweb's 2026 state legislative districts
joined to each chamber's own member pages), the TIGERweb fabric drawn from mirrored tile archives —
**Magisterial District** (`county-subdivision`, 552, shown under the County or City layer), **City
or Town** (`municipality`, 227), **School Division** (`school-district-unified`, 135), **School
Division (Elementary)** (1, Lexington) and **ZIP Code** — and three nearest-N layers from the USGS
National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**VIRGINIA'S 38 INDEPENDENT CITIES BELONG TO NO COUNTY.** A city's council does what a board of
supervisors does in a county, the Census files each city as a county equivalent (GEOIDs 51510 to
51840) and as its own county subdivision, and each is also an incorporated place. So the County
layer is labelled "County or City", its card says when the point is in a city, and the City or Town
card tells a city (in no county) from a town (inside one) by the Census's own name suffix.

**THE CONGRESSIONAL MAP IS THE 2021 MAP, FROM TIGERweb LAYER 0 (THE 120TH CONGRESS).** The Supreme
Court of Virginia drew it in December 2021, and on 8 May 2026 the same court struck down the 2026
amendment that would have let the General Assembly redraw it for that year's election, so the
3 November 2026 election is held on it. Measured 2026-10-29, layer 0 and layer 4 (the 119th
Congress's) carry the same eleven districts with every intersection-over-union 1.0, so layer 0 is
right before and after 3 January 2027. `va/scripts/build_legislative_boundaries.py` refuses if the
two layers stop matching before that date, and refuses on or after 3 January 2029 so a person reads
which map the 2028 election used before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, the plans
the Supreme Court of Virginia drew in December 2021 and first used in 2023. Measured 2026-10-29
against TIGERweb's 2024 vintage: all 100 House of Delegates districts identical, and 38 of 40 Senate
districts identical, the other two differing by slivers (District 31 IoU 0.99972, District 28
0.99988). Each map is simplified on its own (Douglas-Peucker at 5 m under an 8 m ceiling), which is
safe because Virginia has no nesting rule between its chambers.

**THE LEGISLATORS COME FROM EACH CHAMBER'S OWN PAGES.** The Senate's member list
(`apps.senate.virginia.gov/Senator/index.php`) prints one card per seat — name, district, party —
and each senator's page prints the session office in the General Assembly Building, its telephone
and the senator's e-mail address. The House's member list (`house.vga.virginia.gov/members`) prints
one card per seat with the delegate's e-mail address, and each delegate's page the name in reading
order, the party and the Capitol office. On 2026-10-29 the Senate named all 40 and the House named
99, with District 20 printed "Vacant". A district office is printed for every member and is never
read, because the builder has no way to tell it apart from a member's home. robots.txt read that
day: `apps.senate.virginia.gov` has none (404), and `house.vga.virginia.gov` serves a 99-byte file
that binds nobody; both are paced at one request a second.

**THE LOCAL DISTRICTS ARE THE PLAN'S NEXT CHANGE.** Every county's board of supervisors, every
city's council and most school boards are elected, none is named yet, and the County or City, City
or Town and School Division cards say so. The plan (Adam's answers of 22 October 2026, in the
Virginia plan) draws every local election district and precinct from the Department of Elections'
per-locality map files and names the winners from the state's election results, each card saying
which election a name comes from; `va/WATCH.md` carries the order and the checks it owes. The
Magisterial District card is the Census Bureau's copy of each county's magisterial districts and
does not say who represents the point, because a county's election districts can differ from those
lines and the Census copy can lag a redistricting.

**TWO SCHOOL LAYERS TILE THE STATE BETWEEN THEM.** TIGER holds 135 unified school districts and one
elementary one, Lexington City Public Schools, for Virginia and no secondary ones, and the two
tilings partition the state (Census land areas summing to the 133-county-and-city total), so each
layer's empty card points at the other.

**THE ZIP LAYER HIDES OUTSIDE VIRGINIA.** A ZCTA carries no state field, so over the line the live
service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline, and
the smoke test asserts both halves.

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

- Metro: Virginia (`virginia`) — https://districtry.com/va/
- Geocoders: address Photon (Virginia-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Virginia-bounded, serial >=1s queue)
- Ground truth: 37.53850,-77.43370 (Virginia State Capitol, 1000 Bank Street, Richmond (an independent city)) → county Richmond city; us-house 4; va-senate 14; va-house 78. Negative point 37.00000,-75.30000 (Open Atlantic Ocean east of the mouth of Chesapeake Bay, 44 km from the nearest edge of Virginia's outline — outside Virginia and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-29: none of the state's shipped boundary files contains it, none of fleet-outlines.json's outlines does either, and the State Capitol, the control, is inside every shipped file. Water on purpose, the way North Carolina's and Louisiana's are: every land neighbour of Virginia is either live already (Kentucky, Tennessee, North Carolina) or a state the fleet plans to build (West Virginia, Maryland), so a point on a neighbour's land would have to move when that neighbour goes live.).
- Layers: 15 registered (political 4, safety 2, schools 3, geography 6); `registerLayer(` floor 9. Debug namespace `window.VirginiaExplorer`.
- Scheduled workflows: `update-va-congress-roster.yml` (Mon 19:07 UTC); `update-va-legislature-roster.yml` (Tue 19:07 UTC); `update-va-local-officials.yml` (Wed 19:37 UTC); `va-validate-sources.yml` (1st of month 21:43 UTC).
- Source registry: `va/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/va/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/va/ node va/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 va/scripts/validate_index.py va/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 va/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in va/metro-worksheet.json;
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
which vendors Leaflet into `va/scripts/vendor/leaflet/` (gitignored);
`va/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Virginia-specific lives in the `METRO:BEGIN config` block (worksheet-generated) and
this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
this instance's three chamber layers use the fenced factory helper `registerIlgaChamber` (the
generic chamber factory both state chambers and the U.S. House card use, which renders a
vacancy record as a vacant seat with its reason and source), the TIGERweb layers
`registerPolygonLayer` or a bespoke block, and the three nearest-N layers
`registerNearestPointLayer`. Two invariants pervade the code: the **stale-async guard**
(`if (seq !== state.sequence) return;` after every await) and **per-layer failure isolation** (a
layer's failure shows a Retry inside its own card, never breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards say who is not named instead of inventing a name. Both chamber
cards degrade to the district number + the chamber's own member list on a roster miss, and
a vacant seat says it is vacant; the County or City, Magisterial District, City or Town and School
Division cards carry no roster at all and **say so on the card**. External strings always render
through `sanitize()`/`textContent`. Roster refreshes always land as PRs for review — never as direct
commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`va/scripts/build_metro_outline.py` — one INSIDE anchor per county and city plus OUTSIDE anchors
in the neighbouring states, the District of Columbia and the water), `state-counties.json`
(`va/scripts/build_state_counties.py`), and `congress-districts.json`, `va-senate-districts.json`,
`va-house-districts.json` (`va/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m,
refused unless BOTH the 2,000-random-point agreement gate and the 8 m fidelity ceiling pass).
The five TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py` and refreshed by `update-tiger-tiles.yml`. Rosters:
`congress-roster.json` (`va/scripts/build_congress_roster.py`, from unitedstates/congress-legislators)
and `va-{senate,house}-members.json` (`va/scripts/build_va_legislature_roster.py`, from each
chamber's own pages) — count-guarded, refreshed weekly by CI as reviewed PRs.
`scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `va/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
