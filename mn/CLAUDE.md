# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

districtry Minnesota: a single-file, dependency-light web app. Click a point in Minnesota (or
search an address) and it reports every civic district containing that point and who
represents you there. It is a folder of the consolidated districtry repo, following the shape
`docs/EXPANSION_GUIDE.md` Part 2 sets out for a new state instance.

**IT IS NOT PUBLISHED YET.** PR 1 arrived DARK: `mn/**` is blanket-excluded from the Pages
deploy and `metros.json` deliberately carries no `mn` entry, so nothing here is reachable by a
reader. `validate_instance_registration.py` holds those two together in BOTH directions — an
entry in the manifest while the folder is excluded would render a live landing card linking to
a 404. `mn/WATCH.md`'s GO-LIVE section is what the publishing change has to carry.

It ships four layers, the national tier every U.S. state can serve from national publishers:
**County** (87, from Census TIGERweb, identity-only), **U.S. House** (8 districts, TIGERweb
geometry joined to the public-domain unitedstates/congress-legislators roster, refreshed
weekly), and **Minnesota Senate** / **Minnesota House** (67 and 134 districts, TIGERweb
geometry, naming nobody yet).

**THREE OF THE FOUR CARDS NAME NOBODY, AND EACH SILENCE IS RECORDED RATHER THAN IMPLIED.**
Both chamber cards enter the engine chamber factory's roster-miss path deliberately — district
identity plus the chamber's own directory, never an invented name — under gap
`mn-legislature-roster`, which says plainly that the Legislature publishes both rosters and
this instance has not built them. The County card is identity only under `mn-county-officers`.
A reader meeting three quiet cards should be able to find out why, which is what those records
are for.

**THE FLAGSHIP LAYER THIS INSTANCE IS BUILT TOWARD IS `county-commissioner`**, and the
measurement that makes it cheap was taken before any code was written (2026-09-29). The
Minnesota Secretary of State publishes ONE statewide precinct layer —
`enterprise.gisdata.mn.gov`, `us_mn_state_sos/bdry_votingdistricts/FeatureServer/0`, 4,105
precincts — in which every precinct carries the districts it sits in as attributes, so SEVEN
layers dissolve out of one source: `ctycomdist` (447 commissioner districts across all 87
counties — 81 counties elect five and six elect seven), `pctcode` (precincts), `juddist` (10),
`swcdist_n` (117), `hospdist_n` (16), `parkdist_n` (3) and `ward` (274 wards in 76 cities, the
layer Illinois assembled county by county). **A single upstream service serving seven layers
is also a single point of failure for seven layers**, which is why `mn/WATCH.md` watches its
Service Modified stamp and its field names rather than only its endpoint.

**WHAT IS SHUT IS THE ROSTER, NOT THE GEOMETRY.** The SoS's companion results service
`bdry_electionresults_2022_2030` carries federal and state contests only — no commissioner
column — so composing a roster out of certified returns is closed there. Its
`LocalRacesInCounty` pages are UNPROVEN rather than closed: one county at one election id was
read and no commissioner contest was found, which is one reading and not a finding. The
operator ruled on 2026-09-29 that Minnesota launches without commissioner names rather than
waiting for them.

**TWO HOSTS ARE MEASURED AND NEITHER CHANGES THE ANSWER.** `www.mngeo.state.mn.us` serves a
Radware Bot Manager captcha to this project's token — obeyed, never worked around, and it
costs nothing because the data is on the separate enterprise host. `gis.data.mn.gov`'s
robots.txt allows this client with **Crawl-delay: 60** binding on `*`, which is honoured and
makes a full page-through slow rather than impossible. **Do not let a later pass read "MnGeo is
blocked" as "Minnesota publishes nothing"** — that is the Knox shape, and this instance's
whole growth path sits on the host MnGeo is not.

**There is no build step, no framework, and no server-side code.** The app — styles, engine,
and layer modules — lives inline in `index.html`. `sw.js` is the service worker;
`data/app/*.json` are runtime-fetched data files; `data/state/` carries the bootstrap state
config (`build_congress_roster.py` reads its FIPS/USPS/seat count — it ships in the repo and
is excluded from the Pages deploy). This instance ships NO sub-pages yet: no `sources.html`,
no `faq.html`, no `history.html`, and the worksheet therefore carries no `sources_page` or
`history_page` key — those generators are opt-in and generate nothing for an instance that
does not ask.

<!-- ==== GENERATED:BEGIN metro-facts ==== -->
**Metro facts** (generated from `metro-worksheet.json` — edit the worksheet and run
`python3 scripts/generate_metro_files.py`; hand-edits here fail CI):

- Metro: Minnesota (`minnesota`) — https://districtry.com/mn/
- Geocoders: address Photon (Minnesota-bounded type-ahead); unbounded Photon (whole-coverage, sibling-metro lookup); POI Nominatim (office-address pin lookup, Minnesota-bounded, serial >=1s queue)
- Ground truth: 44.97440,-93.26550 (downtown Minneapolis, Hennepin County) → county Hennepin County; us-house 5; mn-senate 61; mn-house 61A. Negative point 46.87720,-97.05000 (inside Cass County, NORTH DAKOTA, about 20 km west of Fargo — outside Minnesota and outside every other instance in the fleet, and inside permalink_gate (minLng -97.40) so the app answers the click and every shipped layer correctly returns nothing. Measured: 0 hits in all five shipped geometry files, TIGERweb's county layer names Cass County STATE 38 (control: the anchor returns Hennepin County STATE 27), and no outline in fleet-outlines.json contains it. TWO POINTS WERE TRIED FIRST AND BOTH FAILED FOR REASONS WORTH RECORDING, because each looked obvious. LAKE SUPERIOR: Minnesota's TIGER county fabric is WATER-INCLUSIVE out to the international boundary, so a point in open Lake Superior at 47.6, -90.0 is named Lk Superior by TIGERweb's hydrography and is still INSIDE Cook County, and a point offshore of Duluth is inside the city of Duluth. Water is not outside the state here. WORTH COUNTY, IOWA (43.45, -93.37): correct on every static test — 0 hits in all five files, TIGERweb naming Worth County STATE 19 — and it MADE THE BROWSER LEAVE. fleet-outlines.json puts it inside Iowa, so placeOwner hands the selection off to districtry.com/ia/ and the page navigates away; the smoke test's coverage-band probe then timed out looking for a button on a blank document. A NEGATIVE POINT MUST BE OUTSIDE EVERY LIVE INSTANCE, not only outside this one. Iowa's own negative point (43.65, -93.37) sits inside Minnesota and will start handing off the day this instance goes live — recorded in mn/WATCH.md as a go-live item on ia/, not a defect in this change.).
- Layers: 4 registered (political 3, geography 1); `registerLayer(` floor 4. Debug namespace `window.MinnesotaExplorer`.
- Scheduled workflows: `update-mn-congress-roster.yml` (Mon 13:40 UTC).
- Source registry: `mn/scripts/validate_sources.py` (machine-checked monthly)
<!-- ==== GENERATED:END metro-facts ==== -->

## Running & testing

```bash
# From the REPO ROOT — one server, every instance:
python3 -m http.server 8000    # then open http://localhost:8000/mn/

# Behaviour gate (real Chromium boot via Playwright) — the main test:
npm install playwright@1.56.1 && npx playwright install --with-deps chromium
BASE_URL=http://localhost:8000/mn/ node mn/scripts/smoke_test.mjs

# Static gate (run after any data/app regeneration or app edit):
python3 mn/scripts/validate_index.py mn/index.html

# Generated-region gate: per-instance facts live ONCE in mn/metro-worksheet.json;
# GENERATED regions are emitted from it. NEVER hand-edit a GENERATED region:
pip install -c scripts/requirements.txt jsonschema
python3 scripts/generate_metro_files.py            # regenerate in place (all instances)
python3 scripts/generate_metro_files.py --check    # the CI drift gate

# Engine parity: the ENGINE fences are composed from the repo-root engine/ —
# edit a block THERE and recompose, never inside an instance file:
python3 scripts/compose_app.py            # splice engine/ into every instance
python3 scripts/compose_app.py --check    # the CI drift gate

# The Data gaps panel's content, emitted from the fleet guidebook:
python3 scripts/build_coverage_gaps.py --check --metro minnesota --out mn/data/app/coverage-gaps.json
```

**THE NEGATIVE POINT IS IN NORTH DAKOTA, AND THE TWO THAT FAILED BEFORE IT ARE WORTH KNOWING.**
`mn/metro-worksheet.json`'s `negative_point.note` carries both in full. Lake Superior does not
work: Minnesota's TIGER county fabric is water-inclusive to the international boundary, so a
point in open lake at 47.6, -90.0 is named `Lk Superior` by TIGERweb's hydrography **and is
still inside Cook County**. Worth County, Iowa passed every static test — 0 hits in all five
shipped files, TIGERweb naming Worth County STATE 19 — and **made the browser leave**:
`fleet-outlines.json` puts it inside Iowa, so `placeOwner` handed the selection to
`districtry.com/ia/` and the smoke test timed out looking for a button on a blank document.
**A NEGATIVE POINT MUST BE OUTSIDE EVERY LIVE INSTANCE, not only outside its own.** Iowa's own
negative point sits inside Minnesota and will start handing off the day this instance is
published — a GO-LIVE row in `mn/WATCH.md`, not a defect in this change.

**Sandboxed environments (Claude Code web):** the headless browser cannot reach the Leaflet
CDN. The repo root's `.claude/settings.json` SessionStart hook runs `scripts/vendor_leaflet.sh`,
which vendors Leaflet into `mn/scripts/vendor/leaflet/` (gitignored); `mn/scripts/smoke_test.mjs`
serves it same-origin. Production and GitHub Actions CI reach the CDN directly.

## Architecture: stable core + pluggable layer modules

The metro-agnostic engine inside `index.html` is fenced with
`/* ==== ENGINE:BEGIN <name> ==== */ … ENGINE:END` markers and is **composed from the single
copy under the repo root's `engine/`** by `scripts/compose_app.py` — there is no release
channel and no per-instance copy to drift. **Never edit inside an ENGINE fence in this file** —
edit the block under `engine/` (when the change is right for every instance) and recompose.
Everything Minnesota-specific lives in the `METRO:BEGIN config` block (worksheet-generated) and
this instance's own module code, which is the `STARTER MODULES` section.

A layer module is registered via `registerLayer({ id, group, label, overlay, query, render })`;
the three district layers use the fenced factory helper `registerIlgaChamber`. **The two
chamber registrations pass `loadNoRoster`, a function returning an empty object**, because the
factory calls `opts.loadRoster()` unconditionally and an empty roster is the honest input — it
enters the factory's own roster-miss path rather than needing an engine change. When
`mn-{senate,house}-members.json` ship, those two become real file loaders and nothing else
about the registration moves.

Two invariants pervade the code: the **stale-async guard** (`if (seq !== state.sequence)
return;` after every await) and **per-layer failure isolation** (a layer's failure shows a
Retry inside its own card, never breaks the others).

**Honesty rules (non-negotiable):** officeholder data is never guessed — where no verifiable
roster source exists, cards link to the official body instead of inventing a name, which is
what three of this instance's four cards do today. External strings always render through
`sanitize()`/`textContent`. Roster refreshes always land as PRs for human review — never as
direct commits to main.

## Data pipeline

Pre-built layers ship as same-origin `data/app/` files, all rebuilt from a live fetch by an
operator script: `metro-outline.json` (the whole-state outline for the coverage wash,
`mn/scripts/build_metro_outline.py`), `state-counties.json`
(`mn/scripts/build_state_counties.py`), and `congress-districts.json`,
`mn-senate-districts.json` and `mn-house-districts.json`
(`mn/scripts/build_legislative_boundaries.py`).

**THAT CHAMBER BUILDER TAKES NO PER-CHAMBER ARGUMENT AND REFUSES ONE**, because rebuilding one
chamber alone is the defect it exists to prevent: mapshaper builds topology WITHIN one file, so
a shared edge between a Senate district and the two House districts inside it only survives
identically if both came off one `combine-files` run. It refuses to write unless three gates
pass — a 2,000-random-point agreement gate per layer, an EXACT cross-layer nesting check at
zero tolerance, and a fidelity ceiling measured against the source. Its `--check` re-runs the
nesting half offline in CI.

**MINNESOTA NESTS BY LETTER**, not by arithmetic: Senate 61 holds House 61A and 61B, where
Iowa's Senate 26 holds House 51 and 52. Porting Iowa's builder failed loudly on that rather
than silently, which is the right failure — its child-key arithmetic matched no Minnesota
BASENAME and the gate reported that no pairing had been checked.

**`FIDELITY_MAX_M` IS 34.0 AND IS PINNED, NEVER RECOMPUTED PER RUN.** A ceiling re-derived from
the source on every run can never fail, because it rises whenever the source gets coarser. 34.0
comes from Minnesota's OWN median staircase step — how far the true line runs before it turns —
measured 2026-09-29 at 31.2 m (mn-house) and 37.6 m (mn-senate), with the instrument first
validated against two states that had published a figure (Iowa 42.2 m against a published 43.4,
Illinois 19.6 m against 19.7). The ceiling is taken from the finer chamber. A redistricting
re-opens it: re-measure the step on the new lines rather than carrying the number forward.

The one roster, `congress-roster.json` (`mn/scripts/build_congress_roster.py`, from
unitedstates/congress-legislators), is count-guarded and refreshed weekly by CI as a reviewed
PR.

## Growing this instance

A new layer or county-level concept follows the repo's `docs/EXPANSION_GUIDE.md`. The working
order it teaches: prove the source first (a live fetch you performed), ship the boundary and
its officeholder sourcing in the same change, floor every scraped count, and record what a
publisher does NOT publish rather than guessing. When a layer ships, its row in
`mn/metro-worksheet.json` (`layers[]`, with a `source` block) is what puts it in every gate.
Extend `LAYER_SIDEBAR_RANK` and `WATCH.md` in the same change.
