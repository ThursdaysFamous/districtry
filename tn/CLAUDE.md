# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Tennessee: a single-file, dependency-light web app. Click a point in Tennessee (or
search an address) and it reports every civic district containing that point and who
represents you there. It serves at **districtry.com/tn/** as a folder of the consolidated
districtry repo, following the statewide shape (`docs/EXPANSION_GUIDE.md` Part 2), not the
Illinois root-scripts shape. It ships TWELVE layers, and **the instance is DARK**: no
`metros.json` entry, `tn/**` excluded from the Pages deploy, nothing served and no landing card
naming it. It goes live on the operator's word, after Oklahoma. `tn/WATCH.md` lists what
go-live has to do in one change.

**The national tier, plus the Legislature's own names.** County (95, Census TIGERweb, the
coverage ring and a card that names the county and not yet its commissioners), **U.S. House**
(9 districts, TIGERweb geometry joined to the public-domain unitedstates/congress-legislators
roster), **Tennessee Senate** and **Tennessee House** (33 and 99 districts, TIGERweb geometry),
the LIVE TIGERweb fabric (**City or Town**, **School District (Unified)** 127,
**School District (Elementary)** 15, **School District (Secondary)** 15, **ZIP Code**) and three
nearest-N layers from the USGS National Map (**Police Station**, **Fire & EMS Station**,
**Post Office**).

**THE CONGRESSIONAL MAP IS THE 119TH, ON PURPOSE, UNTIL 3 JANUARY 2027.** Tennessee redrew its
congressional districts in 2026. TIGERweb's Legislative layer 0 is now the 120th Congress map
(field CD120), which takes effect when the next Congress sits; the members a reader can call
today were elected from the old lines, which TIGERweb serves as layer 4 (field CD119). The
builder reads layer 4 and REFUSES to run on it after 2027-01-03, so the switch cannot be
forgotten into a wrong answer. North Carolina and Louisiana redrew too; the lesson is the
fleet's.

**WHO HOLDS EACH LEGISLATIVE SEAT COMES FROM THE LEGISLATURE'S OWN MAP, NOT FROM A THIRD
PARTY.** The Legislature publishes its district map on the state's TNMap service, and every
record names the member ("Senator …", "Representative …") or says "Representative Vacant".
`tn/scripts/build_tn_legislature_roster.py` takes the names and vacancies from there, and adds
party, e-mail and the member's own page from Open States only where Open States' member for
that district has the same surname. On 2026-10-10 the two agreed on every named seat; the state
listed House 31 and House 84 as vacant, and Open States still gave House 31 to Ron Travis. The
state's word ships, as a vacancy record the card prints with its date. `capitol.tn.gov` and
`wapp.capitol.tn.gov` both answer robots.txt with `User-agent: *` / `Disallow: /`, so this
project fetches neither: the member pages are LINKED from the card and never read, and the link
checker records the host in `ROBOTS_DECLINED` rather than probing it. Open States carries no
capitol address or telephone for any Tennessee legislator (0 of 131 rows), so the cards carry
no office.

**THREE SCHOOL LAYERS, BECAUSE TENNESSEE USES ALL THREE OF TIGER'S TILINGS.** Most of the state
is in a unified district (127), but fifteen cities and special school districts run their own
elementary schools while the county system runs the high schools, so a reader there is in one
elementary (15) and one secondary (15) district at once. Each empty note points at the other
layers. The card states the grades the Census records ("Pre-kindergarten to grade 8").

**THREE CONSOLIDATED GOVERNMENTS ARE NEITHER A CITY NOR A COUNTY.** TIGERweb carries 345 places
for STATE='47': 182 cities (LSADC 25), 160 towns (LSADC 43), and three metropolitan
governments, where the city and the county are one government with one elected body:
Nashville-Davidson (TIGER names the place "Nashville-Davidson metropolitan government
(balance)", LSADC 00, FUNCSTAT F), Hartsville/Trousdale County (LSADC 00) and Lynchburg, Moore
County (LSADC MG). Both the municipality card and the county card say so. No place is FUNCSTAT I
(inactive), measured 2026-10-10.

**THERE IS NO TOWNSHIP OR CIVIL-DISTRICT LAYER, AND THAT IS A MEASUREMENT.** All 855 county
subdivisions TIGERweb carries for STATE='47' are civil districts ("District N", LSADC 28,
FUNCSTAT N). The Census codes FUNCSTAT N as a legal area with no functioning government: nobody
is elected to run one. Their numbers look like county commission district numbers, and nothing
in the Census record says the lines are the same, so drawing them would invite exactly that
misreading.

**THE ZIP LAYER HIDES OUTSIDE TENNESSEE.** A ZCTA carries no state field, so over the line the
live service answers with a neighbouring state's ZIP (Bowling Green, Kentucky gives 42101; a
point just over the Alabama line 35773; the Capitol 37219). The envelope the app downloads
returns 1,070 ZCTAs, 638 of them with their interior point in Tennessee (measured 2026-10-10).
The coverage test reads the shipped outline, and the smoke test asserts both halves.

**THE FLAGSHIP THIS INSTANCE IS BUILDING TOWARD IS THE COUNTY COMMISSION.** Every county but the
three consolidated governments elects a county commission from districts, and the Comptroller's
redistricting address lookup publishes them statewide (859 districts in one layer, measured
2026-10-09). Recorded as gap `tn-county-commission-districts` until it ships, beside
`tn-municipal-officeholders` and `tn-school-board-members`.

**TRIBAL GOVERNMENTS ARE IN SCOPE AND ARE NOT IN THIS PR.** Measured with
`scripts/tribal_areas.py` on 2026-10-10, the Census draws no reservation in Tennessee and one
piece of off-reservation trust land: 0.695 km2 of the Mississippi Band of Choctaw Indians'
trust land, near Henning in Lauderdale County (4.1% of that trust land's area). The fleet-wide
tribal-government thread owns it.

**THE CHAMBER BOUNDARIES USE DOUGLAS-PEUCKER AT `interval=20`**, inherited from North Carolina's
measurement and re-measured here: worst stray 23.2 / 21.4 / 21.5 m (U.S. House, Senate, House)
against the 25 m ceiling the builder gates, with Tennessee's median source step 27.67 / 25.41 /
23.63 m. The coverage outline is ONE ring, 2,288 vertices, read from
`build_metro_outline.py --check`.

**`tncourts.gov` serves a browser challenge**, which the fleet's robots reader recognises as
challenge-fronted. It is never worked around, and no layer here reads it.

**There is no build step, no framework, and no server-side code.** The app (styles, engine,
and layer modules) lives inline in `index.html`. `sw.js` is the service worker;
`data/app/*.json` are runtime-fetched data files; `data/state/` carries the bootstrap state
config (`build_congress_roster.py` reads its FIPS/USPS/seat count; it ships in the repo and is
excluded from the Pages deploy). `sources.html` carries the generated per-layer provenance
matrix and `faq.html` the common questions; both compose from the same shared engine blocks as
every other instance via `scripts/compose_app.py`.

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: Tennessee (`tennessee`) — https://districtry.com/tn/
- Geocoders: address Photon (Tennessee-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, Tennessee-bounded, serial >=1s queue)
- Ground truth: 36.16590,-86.78440 (the State Capitol, Nashville, Davidson County) → county Davidson County; us-house 7; tn-senate 21; tn-house 51. Negative point 34.90000,-86.60000 (near Hazel Green, Madison County, ALABAMA, about 11 km south of the state line — outside Tennessee and outside every other instance in the fleet, and inside permalink_gate (minLat 34.80) so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-10: TIGERweb's state layer names Alabama at this point (control: the Capitol anchor returns Tennessee). ALABAMA BECAUSE NO INSTANCE SERVES IT and none is planned next: Arkansas and Mississippi, both on the next-states list, were passed over so this point does not have to move when either goes live.).
- Layers: 12 registered (political 3, safety 2, schools 3, geography 4); `registerLayer(` floor 11. Debug namespace `window.TennesseeExplorer`.
- Scheduled workflows: `update-tn-congress-roster.yml` (Mon 17:15 UTC); `update-tn-legislature-roster.yml` (Tue 17:15 UTC); `tn-validate-sources.yml` (1st of month 19:30 UTC).
- Source registry: `tn/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->
## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/tn/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/tn/ node tn/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 tn/scripts/validate_index.py tn/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 tn/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in tn/metro-worksheet.json;
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
which vendors Leaflet into `tn/scripts/vendor/leaflet/` (gitignored);
`tn/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Tennessee-specific lives in the `METRO:BEGIN config` block
(worksheet-generated) and this instance's own module code, between the `chamber-factory` and
`hover-explorer` fences.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
this instance's three chamber layers use the fenced factory helper `registerIlgaChamber` (the
generic chamber factory both state chambers and the U.S. House card use), and the three
nearest-N layers use `registerNearestPointLayer`. Two invariants pervade the code: the
**stale-async guard** (`if (seq !== state.sequence) return;` after every await) and **per-layer
failure isolation** (a layer's failure shows a Retry inside its own card, never breaks the
others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name. Both chamber
cards degrade to the district number + the chamber's own directory on a roster miss; the county,
school-district and municipality cards carry no roster at all and **say so on the
card**. External strings always render through `sanitize()`/`textContent`. Roster refreshes
always land as PRs for human review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`tn/scripts/build_metro_outline.py`: one INSIDE anchor per county, each verified interior
against that county's own rings, all 95 correct, plus eight OUTSIDE anchors, one in each
neighbouring state), `state-counties.json` (`tn/scripts/build_state_counties.py`), and
`congress-districts.json`, `tn-senate-districts.json`, `tn-house-districts.json`
(`tn/scripts/build_legislative_boundaries.py`: statewide TIGERweb, congress from layer 4,
mapshaper-simplified with Douglas-Peucker, refused unless BOTH the 2,000-random-point agreement
gate and the 25 m fidelity ceiling pass). Rosters: `congress-roster.json`
(`tn/scripts/build_congress_roster.py`, from unitedstates/congress-legislators) and
`tn-{senate,house}-members.json` (`tn/scripts/build_tn_legislature_roster.py`, names and
vacancies from the Legislature's map on TNMap, party, e-mail and page from Open States `tn.csv`):
all count-guarded, all refreshed weekly by CI as reviewed PRs. The legislature builder refuses to
write when fewer than 30 Senate or 92 House seats are named, when Open States matches fewer than
90% of the named seats, when the state map answers an error, or when a district falls outside
the chamber's range or appears twice. A vacancy record cites the map query that answers for that
seat, because the service's HTML directory is switched off and a bare layer URL opens an error
page.

robots.txt is read before the first fetch through `scraper_common.require_robots_once`.
`data.openstates.org` answers its robots.txt with HTTP 403, which RFC 9309 files with a 404:
no policy, allow all. `tnmap.tn.gov` serves a 155-byte policy with no rule matching the
legislative map's path.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `tn/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
