# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Indiana: a single-file, dependency-light web app. Click a point in Indiana (or
search an address) and it reports every civic district containing that point. It serves at
**districtry.com/in/** as a folder of the consolidated districtry repo — following the
Wisconsin/Iowa/Michigan shape (`docs/EXPANSION_GUIDE.md` Part 2), not the Illinois
root-scripts shape. It ships ELEVEN layers, every one of them from a national publisher.

**LIVE SINCE THE GO-LIVE CHANGE OF 2026-10-07**, eight days after it arrived dark: it is in
`metros.json`, `fleet-outlines.json`, the sitemap, the landing page and the coverage map, and
the deploy excludes only `in/data/state`, `in/scripts` and raw geojson. Its fleet `bbox` in
`metros.json` is CLIPPED to `minLat 37.83` rather than the state's own 37.77, and that is a
measurement: Kentucky's `metro_center` is 37.82, -85.77, and `validate_index.py` refuses a
sibling's hand-off box containing an instance's own centre. The clip leaves out 0.09% of the
state (a riverfront strip in Posey, Vanderburgh and Spencer counties), and no selection is
decided by the box any more — `fleet-outlines.json` decides — so the cost is confined to the
search box's sibling rows when that file cannot be read.

**The pre-built tier** — four TIGERweb layers shipped as same-origin files, which are what the
smoke test anchors on: **County** (92, identity-only), **U.S. House** (9, joined to the
public-domain unitedstates/congress-legislators roster and refreshed weekly), and **Indiana
Senate** / **Indiana House** (50 and 100).

**The live tier** — seven layers with no builder and no committed `data/app` file between them,
so a TIGERweb or USGS vintage roll reaches all seven on its own: **Township or City**
(`county-subdivision`, 1,012 — 1,004 of them civil townships), **City or Town**
(`municipality`, 566), **School District (Unified)** (291), **ZIP Code** (882 intersecting the
state) and the three USGS point layers, **Police Station**, **Fire Station** and **Post
Office**.

**ZIP CODE IS THE ONE LAYER HERE THAT DECLARES A COVERAGE TEST, AND IT HAS TO.** A ZCTA
carries no state field, so that layer alone cannot be fetched with `STATE='18'` and its point
query carries no state filter either — measured 2026-09-29 against in-state controls in the
same command, it answers 60602 in Chicago, 40202 in Louisville and 48226 in Detroit while
answering 46402 in Gary and 46204 at the Indianapolis anchor. Every other card here correctly
declines outside Indiana, so a real out-of-state ZIP was the one answer breaking that. It now
declares `insideIndiana`, tested against the shipped `metro-outline.json` (same-origin,
cache-first, no request), so outside the state the toggle, card and overlay hide. The smoke test
proves BOTH directions — hidden at the negative point, visible at the anchor — with the census
host refused, because a hide test alone would pass for a layer hidden everywhere. The lesson is
Minnesota's (PR #1274), whose negative point returned a North Dakota ZIP.

**INDIANA SHIPS ONE SCHOOL LAYER WHERE MICHIGAN SHIPS TWO, AND THAT IS A MEASUREMENT.**
TIGERweb's elementary (layer 1) and secondary (layer 2) school tilings both return **zero**
features for `STATE='18'` (measured 2026-09-29), so the state runs unified districts alone.
Both are recorded drops rather than empty toggles.

**THE COUNTY CARD NAMES BOTH COUNTY BODIES, AND THEIR DISTRICTS ARE NOT DRAWN YET** (2026-10-09).
An Indiana county is run by TWO elected bodies — a three-member board of commissioners and a
seven-member county council (nine in St. Joseph) — and each is elected on its own district lines.
`in/scripts/build_in_county_officials.py` reads the Indiana Election Division's archived,
CERTIFIED general-election results (`enr.indianavoters.in.gov`, robots.txt answers 400, which
RFC 9309 files as no policy) and writes `in-county-commissioners.json` and
`in-county-councils.json`: the newest certified winner for every seat, 91 counties, 273
commissioners and 639 council members. **THEY ARE ELECTION WINNERS, NOT A ROSTER**, and the card
says so: a vacancy in Indiana is filled by a party caucus, which no election file records, so a
seat can name someone who has since left. A year counts only once it is certified and its
winners have taken office on January 1. **NINE RACES ARE MISFILED IN THE STATE'S OWN FILES** — a
district race published as electing several seats — and `MISFILED_SEAT_COUNTS` records each with
the winner the file flags, refusing the build if any moves; a few races are titled with no
district at all, and those seats print "Seat not stated" rather than a guessed number.
**MARION IS NOT IN THESE FILES**: Indianapolis and Marion County are consolidated, its
legislative body is the 25-member City-County Council elected in municipal years, and the card
says this app does not show it yet. The council file is recorded in `build_county_pages.py`'s
`NOT_COUNTY_BOARDS` (a county council is the FISCAL body, IC 36-1-2-6; commissioners are the
legislative and executive body), so the 91 per-county pages under `in/county-commissioner/` carry
the commissioners. Gap `in-county-government` now records only the missing district lines, which
IGIO publishes for 58 counties (commissioners) and 56 (councils) — the next change.

**NEITHER CHAMBER NAMES A PERSON.** This instance ships no General Assembly roster, so both
chamber cards give the district number and the Assembly's own directory — the chamber factory's
roster-miss path, which is the honest card until a roster is built. Recorded as gap
`in-general-assembly-roster`. Three more gaps cover the live fabric, where the Census carries
geography and no officeholder field at all: `in-township-officers`,
`in-municipal-officeholders`, `in-school-board-members`.

**There is no build step, no framework, and no server-side code.** The app — styles, engine,
and layer modules — lives inline in `index.html`. `sw.js` is the service worker;
`data/app/*.json` are runtime-fetched data files; `data/state/` carries the bootstrap state
config (`build_congress_roster.py` reads its FIPS/USPS/seat count — it ships in the repo and is
excluded from the Pages deploy). `sources.html` carries the generated per-layer provenance
matrix and `faq.html` the common questions; both compose from the same shared engine blocks as
every other instance via `scripts/compose_app.py`.

**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: Indiana (`indiana`) — https://districtry.com/in/
- Geocoders: address Photon (Indiana-bounded type-ahead); unbounded Photon (whole-coverage, sibling-metro lookup); POI Nominatim (office-address pin lookup, Indiana-bounded, serial >=1s queue)
- Ground truth: 39.76860,-86.16260 (the Indiana Statehouse, downtown Indianapolis (Marion County)) → county Marion County; us-house 7; in-senate 46; in-house 97. Negative point 38.25270,-85.75850 (downtown Louisville, Kentucky — south of the Ohio River, whose north bank is the Indiana line, and inside permalink_gate's minLat (37.60) so the point is still selectable; measured to miss all four ANCHOR layers (the live TIGERweb fabric layers are deliberately not anchors — an anchor must answer with the network down) KENTUCKY WENT LIVE ON 2026-09-30 AND NOW COVERS THIS POINT, so the two checks that put it at the map's CENTRE refuse ../fleet-outlines.json, which is what the pan hand-off reads — the same fix Iowa, Illinois and Wisconsin each made rather than moving their own point. The point itself is unchanged: it is still outside this instance and still misses all four anchor layers, and the gate reaches uncovered ground in Ohio if it ever needs to move. Check 1a2 is where this instance asserts fleet routing, and Louisville moved there from its uncovered case to a Kentucky routing case the same day.).
- Layers: 11 registered (political 3, safety 2, schools 1, geography 5); `registerLayer(` floor 9. Debug namespace `window.IndianaExplorer`.
- Scheduled workflows: `update-in-congress-roster.yml` (Mon 15:45 UTC); `update-in-county-officials.yml` (Wed 15:50 UTC).
- Source registry: `in/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/in/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/in/ node in/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 in/scripts/validate_index.py in/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 in/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in in/metro-worksheet.json;
# GENERATED regions are emitted from it. NEVER hand-edit a GENERATED region:
pip install -c scripts/requirements.txt jsonschema
python3 scripts/generate_metro_files.py            # regenerate in place (all instances)
python3 scripts/generate_metro_files.py --check    # the CI drift gate

# Engine parity: the ENGINE fences are composed from the repo-root engine/ —
# edit a block THERE and recompose, never inside an instance file:
python3 scripts/compose_app.py            # splice engine/ into every instance
python3 scripts/compose_app.py --check    # the CI drift gate
```

**Sandboxed environments (Claude Code web):** the headless browser cannot reach the Leaflet
CDN. The repo root's `.claude/settings.json` SessionStart hook runs `scripts/vendor_leaflet.sh`,
which vendors Leaflet into `in/scripts/vendor/leaflet/` (gitignored);
`in/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Indiana-specific lives in the `METRO:BEGIN config` block (worksheet-generated) and
this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

**This instance registers NO county-dispatched concept**, so it carries no
`county-layer-dispatcher` fence at all — the NYC/SF shape rather than Illinois's. When the first
county-level concept ships, the fence comes back in that change.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the three chamber-shaped layers use the fenced factory helper `registerIlgaChamber`. Two
invariants pervade the code: the **stale-async guard** (`if (seq !== state.sequence) return;`
after every await) and **per-layer failure isolation** (a layer's failure shows a Retry inside
its own card, never breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name. Nine of this
instance's eleven layers name nobody (U.S. House and County name people), and every one of their
cards says so. External strings
always render through `sanitize()`/`textContent`. Roster refreshes always land as PRs for human
review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`in/scripts/build_metro_outline.py` — one INSIDE anchor per county, each verified interior
against that county's own rings), `state-counties.json` (`in/scripts/build_state_counties.py`),
and `congress-districts.json`, `in-senate-districts.json`, `in-house-districts.json`
(`in/scripts/build_legislative_boundaries.py` — statewide TIGERweb, mapshaper-simplified,
refused unless the 2,000-random-point agreement gate passes). The rosters are
`congress-roster.json` (`in/scripts/build_congress_roster.py`, from
unitedstates/congress-legislators) and the two county files above
(`in/scripts/build_in_county_officials.py`, `--check` offline), each count-guarded and refreshed
weekly by CI as a reviewed PR (`update-in-congress-roster.yml`, `update-in-county-officials.yml`).

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md` and this
instance's own `docs/IN_EXPANSION_PLAN.md`. The working order those documents teach: prove the
source first (a live fetch you performed), ship the boundary and its officeholder sourcing in
the same change, floor every scraped count, and record what a publisher does NOT publish rather
than guessing. When a layer ships, its row in `in/metro-worksheet.json` (`layers[]`, with a
`source` block) is what puts it on the sources page and in every gate — a layer cannot ship
without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the same change.
