# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry South Carolina: a single-file, dependency-light web app. Click a point in South
Carolina (or search an address) and it reports every civic district containing that point and
who represents you there. It serves at **districtry.com/sc/** as a folder of the consolidated
districtry repo — following the Wisconsin/Iowa shape (`docs/EXPANSION_GUIDE.md` Part 2), not the
Illinois root-scripts shape. It ships TWELVE layers, and **the instance is LIVE since
2026-10-13**, on Adam's word: it has a `metros.json` entry and a landing card, its folder is
published with the siblings' narrow deploy excludes, and its question pages (`county-council.html`
with a page per county under `county-council/`, `congress.html`, `state-legislature.html`) are in
the sitemap. It arrived dark on 2026-10-10; `docs/SC_EXPANSION_PLAN.md` is the record of both
changes.

**The national tier** — ten of the twelve layers answer from a national publisher or the
General Assembly. **County** (46, Census TIGERweb, identity-only and the coverage ring),
**U.S. House** (7 districts, TIGERweb geometry joined to the public-domain
unitedstates/congress-legislators roster), **South Carolina Senate** and **South Carolina House**
(46 and 124 districts, TIGERweb geometry joined to the General Assembly's own member pages), the
LIVE TIGERweb fabric — **City or Town** (`municipality`, 271), **School District** (72) and
**ZIP Code** — and three nearest-N layers from the USGS National Map (**Police Station**,
**Fire & EMS Station**, **Post Office**).

**THE CONGRESSIONAL MAP IS TIGERweb LAYER 0, AND THAT WAS MEASURED RATHER THAN ASSUMED.** Layer 0
is the 120th Congress's map, which is wrong for a state that redrew for 2026. South Carolina did
not: its seven districts in layer 0 and in layer 4 (the 119th) carry the same GEOIDs and differ by
under 0.001% of each district's area (largest 0.00077%, District 4), 2026-10-10.

**THE LEGISLATORS COME FROM THE LEGISLATURE, NOT FROM OPEN STATES.** Oklahoma's and North
Carolina's arrivals took names from the Open States export; this one reads the General Assembly's
two chamber lists and all 170 member pages on `www.scstatehouse.gov`
(`sc/scripts/build_sc_legislature_roster.py`). Every seat is filled (46 of 46, 124 of 124 on
2026-10-10), and every card carries a party, the member's State House office and business
telephone, and a link to the member's own page. **THE SAME PAGES PRINT A HOME ADDRESS AND HOME
TELEPHONE, AND THE BUILDER NEVER READS THEM** — its parse is confined to the block headed
"Columbia Address". The General Assembly publishes no e-mail address for any member (each page
offers a message form), so the cards carry none.

**THERE IS NO TOWNSHIP LAYER, AND THAT IS A MEASUREMENT.** All 299 county subdivisions TIGERweb
carries for STATE='45' are census county divisions (LSADC 22, FUNCSTAT S): statistical areas
drawn for counting, which govern nobody.

**ONE SCHOOL LAYER, LABELLED WITHOUT A QUALIFIER.** TIGER's unified tiling holds 72 districts
for South Carolina and its elementary and secondary tilings hold none, and the unified districts'
land area sums to the 46-county total (77,866 km²) — so the layer is "School District", the
North Carolina shape, and its id stays `school-district-unified` because a layer id is a public
address.

**THE ZIP LAYER HIDES OUTSIDE SOUTH CAROLINA.** A ZCTA carries no state field, so over the line
the live service answers with a neighbouring state's ZIP (the Georgia negative point gives 30817
and Augusta 30904, against the State House's 29201, measured 2026-10-10). The coverage test reads
the shipped outline, and the smoke test asserts both halves.

**THE FLAGSHIP IS `county-council`, AND ITS NAMES COME FROM CERTIFIED ELECTION RESULTS.** Every
county has been governed by an elected council since the Home Rule Act of 1975. The districts are
the state Revenue and Fiscal Affairs Office's one statewide layer — 315 districts in 46 counties,
`sc/scripts/build_sc_county_council_districts.py`, Douglas-Peucker at 20 m under a 25 m ceiling,
with every county's districts held to cover that county. The people are each seat's most recent
winner in the State Election Commission's certified results (the 2022 and 2024 generals, their
recounts and runoffs), `sc/scripts/build_sc_county_council_roster.py`: **334 seats, every one
named**, refreshed weekly by `update-sc-county-council-roster.yml`, which also watches the district
layer and opens an issue when a county redistricts. Thirteen counties elect somebody countywide —
six chairs, three supervisors, three at-large members, and Hampton's whole council — so the
`county` card names those members and the council card names the district's own; Jasper elects
all five countywide from four residence townships, and no published source says which of the
map's four numbers is which township, so its card names all five.

**A WINNER IS NOT A SITTING MEMBER, SO THE COUNTY'S OWN PAGE IS READ BESIDE THE RESULTS.** The
roster builder reads each county's council page (robots.txt at every redirect hop, standard
library, our own token) and keeps only folded words, never an address — four of those pages print
members' home addresses. A page naming somebody else for a seat FAILS the build unless a person
has read it and recorded it in `COUNTY_SAYS`; on 2026-10-11, 43 of the 46 pages were read (36 by
the build, seven more by a person) and eleven seats differed, each shown on the card beside the
winner. Six of those pages refuse our own
token by Cloudflare or Akamai and were read with the browser client, so the weekly job, which
still sends the token, prints them unreadable. Charleston's page blocks every client and is the
one county left in `UNREAD_BY_A_PERSON`, where a disagreement is printed rather than failed until
somebody reads it, and two are never read on purpose (Allendale's robots.txt disallows every
path; Berkeley answers with a managed challenge). Recorded as gap `sc-county-council`
(data-quality), beside `sc-municipal-officeholders` and `sc-school-board-members`. **Council seats are on the 3 November 2026 ballot, and the weekly job
cannot read the results site from GitHub's runners** (a 202 challenge on robots.txt, measured
2026-10-11): it keeps the shipped names, opens a tracking issue, and turns red once an election's
results are 21 days old and unread. How those names get refreshed waits on Adam's ruling
(`sc/WATCH.md`).

**TRIBAL LAND IS DRAWN, AND ITS CARD NAMES THE CATAWBA NATION'S EXECUTIVE COMMITTEE.** Measured
with `scripts/tribal_areas.py` on 2026-10-12, the Census draws one federal reservation in South
Carolina (Catawba, 4.123 km², 849 people in 2020) and one off-reservation trust land (Catawba,
0.054 km², nobody), both in York County and both wholly inside the state. `tribal-government` draws
both from `data/app/tribal-areas.json` (`scripts/build_tribal_areas.py`, the same builder every
instance uses), and the card names the five officers the nation lists on its own page at
`catawba.com/executive-committee`, read weekly by `scripts/tribal_council_scraper.py`. The Bureau of
Indian Affairs still lists `www.catawbaindian.net` as the nation's site, which reset the connection
on every read from here on 2026-10-12, so the card's official link is the Bureau's and the names
link to the page they came from. That page's prose still says the committee elected in 2019 serves
until July 2023; its list was revised after that, and the list is what is carried.

**THE CHAMBER BOUNDARIES USE DOUGLAS-PEUCKER AT `interval=20`**, inherited from North Carolina's
measurement and re-measured here: worst stray 21.7 / 20.6 / 20.2 m (U.S. House, Senate, House)
against the 25 m ceiling the builder gates, with South Carolina's median source step 17.8 /
21.1 / 24.3 m in the same order. The coverage outline is ONE
ring, 2,910 vertices, read from `build_metro_outline.py --check`.

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

- Metro: South Carolina (`southcarolina`) — https://districtry.com/sc/
- Geocoders: address Photon (South Carolina-bounded type-ahead); unbounded Photon (whole-coverage, sibling-instance lookup); POI Nominatim (office-address pin lookup, South Carolina-bounded, serial >=1s queue)
- Ground truth: 34.00035,-81.03295 (the State House, Columbia, Richland County) → county Richland County; us-house 6; sc-senate 26; sc-house 72; county-council 4. Negative point 33.75000,-82.55000 (Wilkes County, GEORGIA, about 25 km west of the Savannah River — outside South Carolina and outside every other instance in the fleet, and inside permalink_gate so the app answers the click and every shipped layer correctly returns nothing. Measured 2026-10-10: TIGERweb's state layer names Georgia at this point (control: the State House anchor returns South Carolina). GEORGIA BECAUSE NO INSTANCE SERVES IT, and on land well clear of the river, whose channel the county fabric could place on either side.).
- Layers: 12 registered (political 5, safety 2, schools 1, geography 4); `registerLayer(` floor 8. Debug namespace `window.SCExplorer`.
- Scheduled workflows: `update-sc-congress-roster.yml` (Mon 17:07 UTC); `update-sc-legislature-roster.yml` (Tue 17:07 UTC); `update-sc-county-council-roster.yml` (Wed 17:07 UTC); `sc-validate-sources.yml` (1st of month 19:37 UTC).
- Source registry: `sc/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/sc/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/sc/ node sc/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 sc/scripts/validate_index.py sc/index.html

# Coverage-wash gate (anchors + envelopes, offline against the shipped file):
python3 sc/scripts/build_metro_outline.py --check

# Generated-region gate: per-instance facts live ONCE in sc/metro-worksheet.json;
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
which vendors Leaflet into `sc/scripts/vendor/leaflet/` (gitignored);
`sc/scripts/smoke_test.mjs` serves it same-origin. Production and GitHub Actions CI reach the
CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything South Carolina-specific lives in the `METRO:BEGIN config` block
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
cards degrade to the district number + the chamber's own directory on a roster miss; the
council and county cards keep the district or county and link the state association's county
directory when the council roster does not load; the school-district and municipality cards carry no roster at all
and **say so on the card**. External strings always render through `sanitize()`/`textContent`. Roster refreshes
always land as PRs for human review — never as direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`sc/scripts/build_metro_outline.py` — one INSIDE anchor per county at the Census's own interior
point, each verified interior against that county's own rings, all 46 correct, plus six OUTSIDE
anchors in Georgia and North Carolina), `state-counties.json`
(`sc/scripts/build_state_counties.py`), and `congress-districts.json`,
`sc-senate-districts.json`, `sc-house-districts.json`
(`sc/scripts/build_legislative_boundaries.py` — statewide TIGERweb, mapshaper-simplified with
Douglas-Peucker, refused unless BOTH the 2,000-random-point agreement gate and the 25 m fidelity
ceiling pass), and `sc-county-council-districts.json` (`sc/scripts/build_sc_county_council_districts.py`, from the state's own layer, with its source
fingerprint in `data/source/`). Rosters: `congress-roster.json` (`sc/scripts/build_congress_roster.py`, from
unitedstates/congress-legislators), `sc-{senate,house}-members.json`
(`sc/scripts/build_sc_legislature_roster.py`, from the General Assembly's own pages) and
`sc-county-council-members.json` (`sc/scripts/build_sc_county_council_roster.py`, from the
Election Commission's certified results) — all
count-guarded, all refreshed weekly by CI as reviewed PRs. The legislature builder writes neither
file unless BOTH chambers pass: no fewer than 42 senators and 114 representatives, every
district inside the chamber's range and claimed once, the member page's own district and surname
agreeing with the list, and at least 90% of seats carrying an office and a telephone.

robots.txt is read before the first fetch through `scraper_common.require_robots_once`, with the
same client the fetches send. `www.scstatehouse.gov`'s robots.txt (176 bytes, read 2026-10-10)
allows `/member.php` under its `*` group, and the member pages are paced at one request a second
anyway.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and its
officeholder sourcing in the same change, floor every scraped count, and record what a publisher
does NOT publish rather than guessing. When a layer ships, its row in `sc/metro-worksheet.json`
(`layers[]`, with a `source` block) is what puts it on the sources page and in every gate — a
layer cannot ship without a provenance row. Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the
same change.
