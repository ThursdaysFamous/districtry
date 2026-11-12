# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Hawaii: a single-file, dependency-light web app. Click a point in Hawaii
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/hi/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
fourth state of batch 4, the last batch of the state-level launch Adam asked for on 2026-11-10
(New Mexico, Nebraska, Idaho, Hawaii, Maine, Montana, Rhode Island, South Dakota, North Dakota, Alaska, Vermont, Wyoming, Delaware), in his chosen order: built dark, with the deploy excluding `hi/**`, and opened with the rest
of its batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column. That change gave every one of the 50
states an app.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or Open States' export, because the Legislature's own site blocks this project's client: **County** (`county`, all five, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (2 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Hawaii Senate** and **Hawaii House** (25 and 51 districts, TIGERweb's 2026 state legislative districts joined to Open States' export of current legislators), the TIGERweb fabric drawn from mirrored tile archives — **School District** (the one statewide district) and **ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `hi/scripts/build_metro_outline.py --check` holds it to 5
INSIDE anchors, one per county, and 10 OUTSIDE anchors offshore.

**THE NORTHWESTERN HAWAIIAN ISLANDS ARE LEFT OUT.** The City and County of Honolulu also holds the atolls reaching 1,900 km northwest to Kure Atoll (-178.3), where no one lives. Every builder here drops each polygon part west of longitude -161 whole before anything is simplified, so the outline, the county file and the legislative maps all stop at Kaula (-160.5); a part straddling the line stops the build.

**THE CONGRESSIONAL MAP COMES FROM TIGERweb LAYER 0 (THE 120TH CONGRESS), WHICH IN HAWAII IS
THE SAME MAP AS LAYER 4.** Measured 2026-11-12, layer 0 and layer 4 (the 119th Congress's) carry the
same 2 districts, every intersection-over-union 1.0, so layer 0 is right before and after
3 January 2027. `hi/scripts/build_legislative_boundaries.py` refuses if the two stop matching before
that date, and refuses on or after 3 January 2029 so a person reads which map the 2028 election used
before anything is drawn.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2)**, 25 Senate and 51 House districts.
Measured 2026-11-12, every district in both chambers is the same as in TIGERweb's 2024 layers (5 and 6), intersection-over-union 1.0. The builder refuses if a layer's name changes, since TIGERweb renumbers its layers when a vintage
rolls, and there is no nesting rule between the chambers (a House district's largest share
inside one Senate district is as low as 0.43 of its area), so each map is simplified on its own,
Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATURE'S OWN SITE REFUSES THIS PROJECT, SO THE MEMBERS COME FROM OPEN STATES** (Adam's choice
of 2026-11-10: "start with the legislatures own sites with Open states as a fall back"). Measured
2026-11-12, `capitol.hawaii.gov` answered robots.txt and the member pages alike with Cloudflare's
"Attention Required!" block page, an access control that is never worked around; the cards still link
it. `hi/scripts/build_hi_legislature_roster.py` reads `data.openstates.org/people/current/hi.csv`,
compiled from the Legislature's own pages: that day it named all 25 senators and all 51
representatives. From each row it carries the name, party, district, the e-mail address at
capitol.hawaii.gov (all 76) and the member's page on capitol.hawaii.gov. Open States is not a government,
so an address at any other domain would not be carried, and the address columns are never read.
robots.txt read 2026-11-12: `data.openstates.org` answered 403 (an S3 "Access Denied"), which RFC 9309
§2.3.1.3 reads as no robots.txt.

**HAWAII HAS NO CITY OR TOWN LAYER, BECAUSE IT HAS NO INCORPORATED CITIES OR TOWNS.** Its five counties
are its only local governments, so the County card names the government over every point; Honolulu is
the City and County of Honolulu, which covers the whole island of Oahu.

**THE SCHOOL LAYER IS ONE DISTRICT, THE WHOLE STATE.** TIGER holds one unified district for Hawaii, the
Hawaii Department of Education (GEOID 1500030, kindergarten to grade 12), and nothing on its elementary
or secondary layers. Its Board of Education is appointed by the governor and confirmed by the state
Senate, so no school board is elected and the card says so; there is no school-board gap to record.

**THE FIVE COUNTIES ARE HAWAII'S ONLY LOCAL GOVERNMENTS.** Honolulu is a city and a county in one
government, run by an elected mayor and city council; Hawaii, Maui and Kauai counties each elect a mayor
and a county council; and Kalawao County, the Kalaupapa settlement on Molokai, has no elected government
and is administered by the state Department of Health. No mayor or council member is named yet, and the
card says so (gap `hi-county-officials`).

**HAWAII HAS NO TRIBAL LAND TO DRAW.** Measured 2026-11-12 with `scripts/tribal_areas.py --report Hawaii`:
the three drawn classes (reservation, trust land, state reservation) keep no feature inside the state,
with Hawaii resolving to state code 15 as the control. Recorded as covered in
`data/tribal-government-join.json`. Hawaiian home lands are a different class, which the fleet does not
draw.

**THE ZIP LAYER HIDES OUTSIDE HAWAII**, as it does in every app. A ZCTA carries no state
field, so the coverage test reads the shipped outline rather than the service, and the smoke test asserts
both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The two TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the two officers Hawaii elects statewide as single officers (the
governor and lieutenant governor) and both U.S. senators, from
`hi/data/source/statewide-officials.source.json` through `scripts/build_statewide_officials.py`. The nine
trustees of the Office of Hawaiian Affairs are elected statewide too and are not listed yet; the attorney
general is appointed.

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

- Metro: Hawaii (`hawaii`) — https://districtry.com/hi/
- Geocoders: address Photon (Hawaii-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Hawaii-bounded, serial >=1s queue)
- Ground truth: 21.30742,-157.85743 (Hawaii State Capitol, 415 South Beretania Street, Honolulu, Honolulu County) → county Honolulu County; us-house 1; hi-senate 13; hi-house 25. Negative point 20.70000,-158.70000 (the open Pacific about 100 km southwest of Oahu — outside Hawaii and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here, because it is open water (control: the Hawaii State Capitol returns Hawaii), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any outline in the change that opens the last thirteen states. IT IS OPEN WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 9 registered (political 3, safety 2, schools 1, geography 3); `registerLayer(` floor 7. Debug namespace `window.HawaiiExplorer`.
- Scheduled workflows: `update-hi-congress-roster.yml` (Wed 22:29 UTC); `update-hi-legislature-roster.yml` (Thu 22:29 UTC); `hi-validate-sources.yml` (2nd of month 22:29 UTC).
- Source registry: `hi/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/hi/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/hi/ node hi/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 hi/scripts/validate_index.py hi/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 hi/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in hi/metro-worksheet.json;
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
which vendors Leaflet into `hi/scripts/vendor/leaflet/` (gitignored);
`hi/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Hawaii-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the U.S. House and chamber layers use the fenced factory helper `registerIlgaChamber` (which renders a vacancy record as a vacant seat with its reason and source), the County and school cards are bespoke `registerLayer` blocks, the ZIP layer `registerPolygonLayer`, and the three nearest-N layers `registerNearestPointLayer`. Two invariants pervade the
code: the **stale-async guard** (`if (seq !== state.sequence) return;` after every await) and
**per-layer failure isolation** (a layer's failure shows a Retry inside its own card, never breaks
the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards say who is not named instead of inventing a name. The chamber cards
degrade to the district + the chamber's own member list on a roster miss, and a vacant or unlisted
seat says so with the day it was read; the County and school district cards carry no
roster and **say so on the card**. External strings always render through
`sanitize()`/`textContent`. Roster refreshes always land as PRs for review — never as direct commits
to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`hi/scripts/build_metro_outline.py`), `state-counties.json` (the counties, `hi/scripts/build_state_counties.py`),
and `congress-districts.json`, `hi-senate-districts.json` and `hi-house-districts.json`
(`hi/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m under an 8 m ceiling, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance hi`; 10,169 populated blocks holding all 1,455,271 people the 2020 census counted in Hawaii). All three maps are held to that count. The congressional map's worst district is -0.170% of the raw-census ideal; the Senate's and House's are +40.032% (District 15) and +79.027% (District 46), because Hawaii apportions its Legislature on a permanent-resident base that leaves out non-resident military personnel, their dependants and non-resident students, and the districts around the bases run far over the raw count. That base is the likeliest reason, inferred and not measured, and the tolerance records the figures rather than certifying the plan. The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 97 ZIP codes). Rosters:
`congress-roster.json` (`hi/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`hi-senate-members.json` and `hi-house-members.json` (`hi/scripts/build_hi_legislature_roster.py`) — count-guarded, refreshed weekly by CI as reviewed PRs — and
`statewide-officials.json` (`scripts/build_statewide_officials.py`, from
`hi/data/source/statewide-officials.source.json`). `scripts/validate_chamber_rosters.py` holds
both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `hi/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
