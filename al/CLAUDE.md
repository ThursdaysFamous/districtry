# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Alabama: a single-file, dependency-light web app. Click a point in Alabama
(or search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/al/** as a folder of the consolidated
districtry repo, following the Missouri shape (`docs/EXPANSION_GUIDE.md` Part 2). It is the
fourth state of batch 3 of the state-level launch Adam asked for on 2026-11-10 (Massachusetts, Colorado, Maryland, Alabama, Oregon, Connecticut, Utah, Kansas),
in his chosen order: built dark, with the deploy excluding `al/**`, and opened with the rest of its
batch in one go-live change on Adam's own "merge", which narrowed that exclude, added its
`metros.json` entry and gave it a `layer-concepts.json` column.

**The layers** draw their shapes from the Census Bureau and name people from a national roster
or the Legislature's own data: **County** (`county`, all 67, Census TIGERweb, the state outline the coverage wash covers), **U.S. House** (7 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators roster), **Alabama Senate** and **Alabama House** (35 and 105 districts, TIGERweb's 2026 state legislative districts joined to the Legislature's own member data), the TIGERweb fabric drawn from mirrored tile archives — **City or Town** (`municipality`, 465 incorporated places), **School District** (141) and **ZIP Code** — three nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**, **Post Office**) and **Tribal Government** (`tribal-government`, the Census's tribal land, joined to the government that holds it).

**COVERAGE IS ONE TIER, THE WHOLE STATE.** Every county is answered by every layer, so
`metro-outline.json` is the state outline and the wash has no lighter band (`coverage_key` with
`outside` and `edge` only). `al/scripts/build_metro_outline.py --check` holds it to 67
INSIDE anchors, one per county, and 14 OUTSIDE anchors over the state line and offshore.

**THE CONGRESSIONAL MAP IS THE ONE THE SITTING MEMBERS WERE ELECTED FROM, TIGERweb LAYER 4 (THE
119TH CONGRESS), UNTIL 3 JANUARY 2027.** Alabama's map changed for the 120th Congress, which the
November 2026 election used (layer 0). Measured 2026-11-12: 4 of the 7 districts differ between the two (the lowest intersection-over-union District 2 at 0.416, then District 1 at 0.583, District 7 at 0.703 and District 6 at 0.933), so the two are not
interchangeable. `al/scripts/build_legislative_boundaries.py` refuses to build layer 4 on or after
3 January 2027; the change that day switches it to layer 0 and `CD120`, a person's step, because the
cards then name the members elected in 2026.

**THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1 and 2).**
Measured 2026-11-12 against the 2024 vintage (layers 5 and 6): the 35 Senate districts are the same map (the lowest intersection-over-union 0.99995), and 103 of the 105 House districts are identical while two differ by slivers (District 20 at 0.9982 and District 22 at 0.99975). The newer vintage is drawn. The builder refuses if a layer's name changes, since TIGERweb renumbers its
layers when a vintage rolls, and there is no nesting rule between the chambers (a House district's largest share inside one Senate district is as low as 0.43 of its area), so each map is simplified on its own, Douglas-Peucker at 5 m under an 8 m ceiling.

**THE LEGISLATORS COME FROM THE LEGISLATURE'S OWN MEMBER DATA** (ALISON, the Legislature's
information system, `al/scripts/build_al_legislature_roster.py`). The site draws its member lists
from a GraphQL service on the same host and filters it to sitting members with `active: { eq: true }`;
the builder asks the site's own question, one chamber at a time, for each member's name, party,
district, telephone, e-mail address and State House address. Measured 2026-11-12: every one of the
35 Senate and 105 House districts once, plus three records with no district (the Lieutenant
Governor, the Secretary of the Senate and the Clerk of the House), which are not seats and are not
carried. Every member's address that day was the State House at 11 South Union Street in
Montgomery, with the suite on the second line; an address that is not that building is not carried,
so no home address can ship. The e-mail address is the one the Legislature prints beside the member:
28 of 35 senators' and 48 of 105 representatives' were at alsenate.gov or alhouse.gov and the rest
the member's own, all carried under the fleet's rule of 2026-10-17 except one printed beside two
members, which belongs to neither. robots.txt: the host serves no robots.txt (the path answers with
the site's HTML page), which RFC 9309 reads as no restriction.

**MOST OF ALABAMA IS IN NO CITY OR TOWN.** The **City or Town** layer is TIGERweb's incorporated
places (layer 4): 465 records, 278 towns and 187 cities, every one an active government, about 10%
of the state's land (measured 2026-11-12). An empty card says the point is outside every city and
town and that the county is the local government there.

**THE SCHOOL LAYER IS ONE TILING.** TIGER holds 141 unified districts for Alabama (county systems
and city systems) and nothing on its elementary or secondary layers (measured 2026-11-12), so those
two layers are not drawn. No school board member is named yet (gap `al-school-board-members`).

**NO COUNTY OR MUNICIPAL OFFICIAL IS NAMED YET**, and the cards say so rather than leave a reader
to assume the office is empty. Each county is governed by an elected county commission and elects
officers such as a probate judge and a sheriff. Recorded as gaps `al-county-officials` and
`al-municipal-officeholders`.

**TRIBAL GOVERNMENT DRAWS THREE PIECES OF LAND HELD BY TWO TRIBES AND NAMES NO COUNCIL YET**
(`tribal-areas.json`, since 2026-11-13). The Census keeps the Poarch Creek Reservation (about 1.1
km2) and the Poarch Creek Off-Reservation Trust Land (about 0.5 km2, 98.6% of it in Alabama and the
rest in Florida, whose app draws it too) in Alabama, and the MOWA Choctaw state reservation (about
2.7 km2), measured 2026-11-12 with `scripts/tribal_areas.py --report Alabama`. All three are drawn,
each joined in `data/tribal-government-join.json`: the Poarch Band of Creek Indians, seated in
Atmore, from the Bureau of Indian Affairs' list; and the MOWA Band of Choctaw Indians, which the
United States does not recognize, from the Alabama Indian Affairs Commission's list of tribes the
State of Alabama recognizes (revised June 2026), so its card says the state recognizes the band,
links that list and gives the office town the list gives, Mount Vernon. The Poarch Band's own site
answered this project with an automated challenge page on 2026-11-12, so its card names nobody and
says why (`ROSTER_BLOCKED` in `scripts/build_tribal_areas.py`, from the Florida change); the MOWA
Band's council is not carried yet (`ROSTER_NOT_SOUGHT`). Recorded in gap `al-tribal-government`.

**THE ZIP LAYER HIDES OUTSIDE ALABAMA.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP. The coverage test reads the shipped outline,
and the smoke test asserts both halves.

**NO LAYER SENDS A READER'S POINT TO A SERVER.** The three TIGERweb fabric layers answer from
same-origin tile archives (`scripts/mirror_tiger_tiles.py`, refreshed by `update-tiger-tiles.yml`);
their point query runs only when an archive cannot be read.

**THE STATEWIDE OFFICIALS LINE** names the ten officers Alabama elects statewide (the governor,
lieutenant governor, attorney general, secretary of state, state treasurer, state auditor,
commissioner of agriculture and industries, and the president and two members of the Public Service
Commission) and both U.S. senators, from `al/data/source/statewide-officials.source.json` through
`scripts/build_statewide_officials.py`. The justices of the Supreme Court and the judges of the
Court of Civil Appeals and the Court of Criminal Appeals are elected statewide too and are not
listed yet.

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

- Metro: Alabama (`alabama`) — https://districtry.com/al/
- Geocoders: address Photon (Alabama-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Alabama-bounded, serial >=1s queue)
- Ground truth: 32.37771,-86.30091 (Alabama State Capitol, 600 Dexter Avenue, Montgomery, Montgomery County) → county Montgomery County; us-house 2; al-senate 26; al-house 77. Negative point 29.95000,-88.00000 (The Gulf about 25 km south of Dauphin Island — outside Alabama and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-11-12: TIGERweb's state layer names no state here (control: the State Capitol returns Alabama), none of the state's shipped boundary files contains it, and no outline in fleet-outlines.json does, nor any of the other batch-3 states' outlines. IT IS OPEN WATER, SO NO NEIGHBOUR'S GO-LIVE MOVES IT.).
- Layers: 11 registered (political 4, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.AlabamaExplorer`.
- Scheduled workflows: `update-al-congress-roster.yml` (Mon 22:43 UTC); `update-al-legislature-roster.yml` (Tue 22:43 UTC); `al-validate-sources.yml` (1st of month 23:31 UTC).
- Source registry: `al/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/al/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/al/ node al/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 al/scripts/validate_index.py al/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 al/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in al/metro-worksheet.json;
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
which vendors Leaflet into `al/scripts/vendor/leaflet/` (gitignored);
`al/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Alabama-specific lives in the `METRO:BEGIN config` block (worksheet-generated)
and this instance's own module code, between the `chamber-factory` and `hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the three chamber layers use the fenced factory helper `registerIlgaChamber` (which renders a vacancy record as a vacant seat with its reason and source), the County and municipality cards are bespoke `registerLayer` blocks, the school layer `registerPolygonLayer`, and the three nearest-N layers `registerNearestPointLayer`. Two invariants pervade the
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
`al/scripts/build_metro_outline.py`), `state-counties.json` (`al/scripts/build_state_counties.py`),
and `congress-districts.json`, `al-senate-districts.json` and `al-house-districts.json`
(`al/scripts/build_legislative_boundaries.py` — Douglas-Peucker at 5 m, each map on its own, refused unless the 2,000-random-point agreement gate and the 8 m fidelity ceiling both pass). The
TIGERweb fabric layers draw from tile archives under `data/app/tiles/`, mirrored by
`scripts/mirror_tiger_tiles.py`. The compare screen counts people from Census 2020 blocks under
`data/app/population/` (`scripts/build_block_population.py --instance al`; 128,366 populated
blocks holding all 5,024,279 people the 2020 census counted in Alabama). All three maps are held to that count; the congressional map sits within 0.001% of its ideal and both legislative plans run to the 5% range the Legislature adopted (+4.986% and -4.983% at their worst). The ZIP
search reads `zip-index.json` (`scripts/build_zip_index.mjs`, 653 ZIP codes). Rosters:
`congress-roster.json` (`al/scripts/build_congress_roster.py`, from unitedstates/congress-legislators),
`al-senate-members.json` and `al-house-members.json` (`al/scripts/build_al_legislature_roster.py`) — count-guarded,
refreshed weekly by CI as reviewed PRs — and `statewide-officials.json`
(`scripts/build_statewide_officials.py`, from `al/data/source/statewide-officials.source.json`).
`scripts/validate_chamber_rosters.py` holds both chamber files to one record per seat.

robots.txt is read before the first fetch through `scripts/robots_policy.py`, with the same client
the fetches send, and a stated Crawl-delay is honoured.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `al/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
