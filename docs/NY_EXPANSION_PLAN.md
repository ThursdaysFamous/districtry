# districtry New York: growing `ny/` from the city into the state, in place

> **Status, 2026-09-19.** ALL THREE PRs HAVE SHIPPED. PR 1 (`2548fec`, #1005) and PR 2
> (`8765e9b`, #1007) both merged 2026-09-18; PR 3, the go-live, is this change. California is
> still HELD; the last section says what reopens it.
>
> **THIS BLOCK WAS STALE FOR A DAY AND COST A SESSION AN HOUR.** It read "PR 2 ... and PR 3 ...
> are NOT started" while PR 2 had merged the same afternoon — that PR edited this very file,
> appending to its own section six lines below, and left the status block alone. A session
> reading top-down then reported to the operator that PR 2 was the next change. The file's own
> preamble says it "is appended to when a PR ships", and appending without updating the first
> thing a reader sees is how a document lies while every sentence in it is true. READ THE GIT
> LOG, NOT THIS BLOCK — `git log --oneline origin/main -- ny/metro-worksheet.json` answers in
> one line.
>
> Every fact here traces to a measurement made on 2026-09-18 by the assessment recorded in
> `/root/.claude/plans/what-is-the-viability-dreamy-turtle.md` (six repo readers, two external
> researchers under the fleet's robots rules, two adversarial verifiers per load-bearing external
> claim) or to a file in this tree read the same day. Where two verifiers disagreed the disagreement
> is stated. Anything not measured is marked UNVERIFIED. No count that moves is written without its
> date. This file stays in `docs/` and is appended to when a PR ships, the posture
> `docs/IA_EXPANSION_PLAN.md` and `docs/MI_EXPANSION_PLAN.md` already take.

The doctrine this plan applies is `docs/EXPANSION_GUIDE.md` §0.2.1 (a city instance growing into its
state, decided 2026-09-18). It is not restated here; where a step below is the doctrine's, the
section is cited.

## Context

`ny/` is a New York City app: tag `ny`, `THIS_METRO="nyc"`, served at `districtry.com/ny/`, with
27 layers in `ny/metro-worksheet.json` (read 2026-09-18). Measured on that date:

- **Three layers are already statewide on disk.** `congress-districts.json` (26 features),
  `state-senate-districts.json` (63) and `state-assembly-districts.json` (150) are built by
  `ny/scripts/build_legislative_boundaries.py` with `where=STATE='36'` and no clip step; their
  bounding boxes run lng -79.763 to -71.777, lat 40.477 to 45.016, which is the whole state. Their
  rosters are statewide too: 26, 63 and 150 keys, rebuilt weekly by `ny-update-congress-roster.yml`
  and `ny-update-legislature-roster.yml`. Until PR 1 the worksheet and the generated
  `ny/sources.html` described all three as "clipped to the city". That was false and is fixed.
- **Two New York State services are already read and narrowed.** `school-site` reads the NYSED
  `NYS_Schools` FeatureServer (layers 2, 3, 4) through a hard-coded five-county WHERE clause
  (`NYC_SCHOOL_WHERE`, `ny/index.html:9140`); `early-voting` reads the NYS ITS
  `NYS_Elections_Districts_and_Polling_Locations` FeatureServer at layer 1, which is the NYC-only
  early-voting layer (158 sites). Both services publish statewide.
- **Zero `coverage:` declarations.** The four occurrences of `coverage:` in `ny/index.html` are the
  factories' own `coverage: opts.coverage` pass-throughs. Nothing hides a layer outside the city;
  the only city-shaped surface is the two-band wash `drawOutOfScopeMask(loadBoroughBoundaries)` with
  `COVERAGE_KEY = { outside: "Outside New York City" }`, which the engine's own comment calls "not a
  no-data claim".
- **The anchors are all NYC-only.** `borough` (Manhattan), `judicial-district` (1) and
  `municipal-court` (1), evaluated at New York City Hall; the negative point is in the Hudson River
  in New Jersey waters, which sits inside the statewide legislative fabric already shipped.
- **The nearest-point defect is fixed fleet-wide.** Before PR 1 `registerNearestPointLayer` sorted
  every feature by haversine distance and sliced the top N with no distance ceiling, so a click far
  from the city returned the city's own facilities as "nearest 3" with a distance pill. PR 1 put the
  ceiling in `engine/index.html/nearest-point-factory.txt` (see PR 1 below).
- **`METRO_BBOX` is load-bearing in four places only**: the geolocate out-of-bounds check, the three
  sibling-metro handoff tests, and the USGS post-office query envelope. `PERMALINK_GATE` guards
  restoring a `#point=` hash. Widening them is what makes PR 3 live.
- **Demand.** On the districtry.com Search Console property, 2026-08-23 to 2026-09-15, `/ny/` is the
  best-performing page on the site: 697 impressions and 22 clicks, and the five `/ny/` pages
  together 863 impressions and 22 clicks, more clicks than any other path prefix. Across 942 Google
  queries in both properties no query names any New York place outside the city. The page class a
  statewide instance gains does earn: 73 per-county board pages took 12.9% of the property's
  impressions and 22.0% of its clicks at median position 6 to 7, on county-name queries the landing
  pages cannot rank for (`data/search-performance.json`, read 2026-09-18).

## The thesis: why New York's arrival differs from Wisconsin's and Illinois's

Wisconsin arrived on one statutory filing: the LTSB's statewide county-supervisory aggregate, one
fetch for 72 counties' districts, then a 72-county roster grind. Illinois arrived as one city and has
filled its counties one at a time for a year. New York is a third shape, and the fleet has not built
it before.

1. **The state publishes the civic and legislative tiers with rosters embedded.** NYS ITS
   Geospatial Services publishes, keylessly and statewide, the Senate (63), Assembly (150) and
   Congressional (26) district polygons with `DISTRICT, NAME, PARTY, PHONE, EMAIL, DIST_PHONE,
   ADDRESS, CITY, STATE, ZIP` in the same attribute table, and the civic fabric in one service:
   62 counties, 62 cities, 933 towns, 532 villages (all counts measured 2026-09-18). The roster
   attributes differ by chamber and are not a free win (see Traps). The instance already ships the
   three legislative layers statewide from TIGERweb with its own roster pipelines, so nothing in
   this tier is blocked and one thing is a source-switch decision, not a build.
2. **The state publishes no compilation of county legislative districts.** Measured across seven
   publishers (data.ny.gov domain-scoped, LATFOR, the Redistricting Data Hub, the NYS ITS ArcGIS
   Server, the NYS AGOL org, the data.gis.ny.gov Hub, TIGERweb Legislative), and independently
   against Cornell CUGIR, ArcGIS Hub and GitHub: nothing. The county flagship is therefore
   Illinois-shaped, one county at a time, and an ArcGIS Online title search under-reports: Broome
   and Niagara both publish 15-feature district layers on their own hosts and both returned zero
   relevant hits on AGOL. An AGOL miss is never recorded as an absence.
3. **Three county forms.** A County Legislature (some titled Board of Legislators), one Board of
   Representatives (Otsego), and Boards of Supervisors composed of town supervisors and, in some
   counties, city-ward supervisors, voting by weight. The 16 / 40 / 1 split is stated on slide 22 of
   NYSAC's "Foundations of County Government" deck (fetched 2026-09-18). A supervisor county is
   DISTRICTED under this fleet's own axis (`docs/EXPANSION_GUIDE.md` §1.2): each seat is elected by
   a town or a city ward, not countywide, so it is never card-only, and weighted voting is a card
   fact.
4. **NYC's five counties have no county legislature.** The state's Counties layer carries a
   one-character `NYC` field whose only values are `Y` (exactly Bronx, Kings, New York, Queens,
   Richmond) and `N` (the other 57), measured with no nulls and no third value. That is the gate for
   the county-legislature concept inside the city, the suburban-Cook shape.

## Scope decisions

- **In place.** `ny/` keeps its folder and tag; `metros.json` `id` stays `nyc` (the Illinois
  precedent: `id: chicago`, `label: Illinois`). No second instance. §0.2.1 step 1.
- **Statewide tier first, as one dark change** (PR 2), from the state's own ArcGIS services where
  they exist and TIGERweb where they do not. `metro_bbox` and `permalink_gate` stay city-sized until
  PR 3, so PR 2 ships dark. §0.2.1 step 2.
- **The existing NYC layers become the §3.0 city tier** gated by `coverage(point)` against
  `ny/data/app/borough-boundaries.json` (5 features, 285,290 bytes, read 2026-09-18), the Madison
  pattern (`wi/index.html:11011-11020`). Nothing is removed and no permalink breaks. §0.2.1 step 3.
- **Three bands.** `coverage_key.region` per §2.5.1's Illinois row: the city is the full band, the
  state the region band, the region ring built and simplified at the coverage-outline tolerance.
  §0.2.1 step 4.
- **The ring does not grow with the statewide tier.** The county-keyed honesty test (§3.5.1) is
  unchanged: a county joins `METRO_COUNTY_FIPS` only when its BOARD or its PRECINCTS answer there,
  never for a rich statewide answer. After PR 2 the full band is still the five boroughs, which
  qualify on their city election-district layer. `metros.json` `scope` states the served count,
  never "all 62 counties". `build_about_page.check_illinois_scope` is generalised to any instance
  whose ring is a subset of its state, so a wrong scope string fails the build instead of shipping.
  §0.2.1 step 5.
- **The county flagship arrives by tranche** through `county-n-plus-1`'s §3.5 checklist. Tranche 1
  is Westchester, Suffolk, Nassau and Erie. Form is settled per county from a certified election
  document; NYSAC's tables are the lead.
- **Go-live is its own change** (PR 3). §0.2.1 step 6.
- **California is held.** Reasons and the reopening conditions are in the last section.

## Conventions binding every PR

- **Engine edits only under `engine/`**, then `python3 scripts/compose_app.py`; never inside a fence
  in `ny/index.html`. `python3 scripts/check_engine_parity.py index.html` is the fence lint.
- **Worksheet first.** Every per-instance fact lives once in `ny/metro-worksheet.json`; the
  GENERATED regions in `ny/index.html`, `ny/sw.js`, `ny/sources.html`, `ny/scripts/validate_index.py`,
  `ny/scripts/smoke_test.mjs`, `ny/CLAUDE.md` and `ny/README.md` are emitted from it by
  `python3 scripts/generate_metro_files.py`. Every layer gets a `source` block (the generator refuses
  otherwise), a `LAYER_SIDEBAR_RANK` slot, a `validate_sources.py` row, a `ny/WATCH.md` row, and a
  guidebook matrix, coverage-map and inventory update in the same change.
- **`CACHE_NAME` moves on every cache-first change.** `ny/sw.js` is cache-first for `GEOMETRY_URLS`;
  every ring rewrite and every pre-built geometry file is cache-first.
  `python3 scripts/check_cache_version.py --base origin/main` fails a PR that changes one without
  changing the name. Current name: `nyc-district-explorer-shell-v15` (read 2026-09-18).
- **Roster changes are reviewed PRs, never commits to `main`.** `BOT_PR_TOKEN`, a fixed `bot/ny-*`
  branch, PR-never-push. Every officeholder fact lives in a data file, never in a paragraph.
- **Robots rules.** `scripts/robots_policy.py` is the one reader; robots.txt is read before the first
  fetch of a host; a `*` disallow binds; a 401 or 403 on robots.txt is default-allow on an API host
  and a refusal on a government WEBSITE (the DuPage strict reading); a 202, a managed challenge or a
  captcha is an access control and is never worked around; a scraper starts with a districtry token
  and records the measurement if a browser string is ever needed.
- **A name column in a GIS layer is a join key, never the roster of record** (the Coles rule,
  `CLAUDE.md`): Coles's board layer published an `Official` column that was a 2022 snapshot with six
  of twelve names wrong. Geometry comes from whatever proves the lines and people from whatever the
  county maintains as people. Four New York county layers carry a name column (Westchester,
  Suffolk, Nassau, Erie); each ships geometry from the layer and a roster from the county's own
  board page, joined on the district id.
- **Officeholder data is never guessed.** Where no verifiable roster source exists, the card links
  to the official body. External strings render through `sanitize()` or `textContent`.
- **Prose.** Say what you mean; no metaphor; every count with its date.

## PR 1 (shipped 2026-09-18): plan, label fix, engine ceiling, hold, gate fixes

Branch `claude/nyc-sf-statewide-expansion-lxbbig`. It changed no map behaviour except the engine
ceiling. It contained:

- **This document**, `docs/NY_EXPANSION_PLAN.md`.
- **The three false "clipped to the city" labels** in `ny/metro-worksheet.json` (the
  `source.boundary[0].label` on `congress`, `state-senate` and `state-assembly`) reworded to
  "statewide and shipped with the app", and `ny/sources.html` regenerated from them, including its
  `DataCatalog` names. The builder applies no clip and the files hold all 26, 63 and 150 districts.
- **The engine-wide nearest-point ceiling** in `engine/index.html/nearest-point-factory.txt`,
  recomposed into all six instances: a per-layer `opts.maxMiles`, else the instance's
  `NEAREST_MAX_MILES` from the METRO config block under the fleet's `typeof` inertness guard, else an
  engine default; `withDistance` filtered to the ceiling before the sort and slice; `null` returned
  when nothing is within range so the card framework's empty path renders; an `emptyNote` naming the
  ceiling. The default was MEASURED, not guessed, by sampling nearest-1 distances for every
  nearest-point layer in il, wi, ia and mi over each instance's own coverage, and set above the
  fleet's real maxima so no card that answered correctly before goes empty. The value and the
  sampling are recorded in the block's own comment and in `docs/CARD_RENDER_API.md`; they are not
  restated here. No smoke anchor sits on a nearest-point layer (measured across all six worksheets),
  and the Illinois smoke test's "a nearest-N card always has an answer" comment still holds at the
  Loop anchor.
- **The lifted `/ny/` hold**, recorded under the hold in
  `docs/search-baseline/2026-09-15-migration-status.md`: the operator lifted it for `/ny/` on
  2026-09-18 on the measured figures above, so PR 3 may retitle `/ny/`. The retitle itself waits for
  PR 3, because "districtry New York" over a map that answers only inside the city would be a false
  claim. `scripts/check_legacy_redirects.py`'s `HOLD_REWRITES` lists Illinois pages only, so nothing
  was removed there.
- **`scripts/validate_doc_counts.py` `INSTANCE_NAMES` gained "California"**, so a document naming
  the `ca` instance by its state can no longer state a layer count the gate never compares.
- **`docs/EXPANSION_GUIDE.md` §0.2.1** and a routing line in `.claude/skills/expand/SKILL.md`, because
  `new-state-instance` excludes deepening and `county-n-plus-1` is scoped to Illinois, Wisconsin and
  Iowa, so no skill covered this path.

## PR 2: the statewide tier, dark

One PR, its own branch. `metro_bbox` and `permalink_gate` stay city-sized, so nothing a reader can
reach changes; CI runs against every new layer all the same. Every new layer below states its
source, id, measured count and date, robots verdict, join field and trap. Counts are all measured
2026-09-18 unless stated.

### What ships

| Layer id (proposed) | Source | Measured count | Ships as |
|---|---|---|---|
| `county` | `NYS_Civil_Boundaries/FeatureServer/2` | 62 | pre-built `ny-counties.json`, cache-first |
| `municipality` (city / town / village) | `NYS_Civil_Boundaries/FeatureServer/6` (Cities_Towns) and `/7` (Villages) | 995 and 532 | live or pre-built, decided by measured size (open) |
| `school-district` | `NYS_Schools/FeatureServer/18` | 936 | live, after the TIGERweb reconciliation below |
| `election-district` (statewide) | `NYS_Elections_Districts_and_Polling_Locations/FeatureServer/4` | 13,335 rows | live, paged |
| `polling-place` (Election Day) and `early-voting` (widened) | same service, layers 2 and 0 (non-NYC), 3 and 1 (NYC) | 3,655 + 1,214; 251 + 158 | live nearest-N |
| `judicial-district` (statewide) | computed: Counties dissolved on a Judiciary Law §140 lookup | 13 districts over 62 counties | pre-built, replaces the five-borough file |
| `fire-station` (statewide) | `FireStations/FeatureServer/0` on the NYS ITS AGOL org | 2,966 points | live nearest-N |
| `library` (statewide) | `NYS_Schools/FeatureServer/15` | 762 points | live nearest-N |
| `school-site` (widened) | `NYS_Schools/FeatureServer/2,3,4` with the WHERE clause deleted | UNMEASURED statewide; the five NYC counties alone are ~2,831 points | live, paged |
| `post-office` (widened) | USGS National Map structures layer 38 | UNMEASURED statewide | live, paged |
| `zip-code` (statewide ZCTA) | TIGERweb ZCTA (the SF and Michigan precedent) | UNMEASURED for STATE='36' | live |

Also measured available and NOT in PR 2: BOCES districts (`NYS_Schools/17`, 38 polygons) and
`NY_State_Police_Troop_Boundary` (10). Each is a §1.6 concept question for a later change.

### `county`

- Source: `https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Civil_Boundaries/FeatureServer/2`.
  Service description "Publication Date: March 2026. Updated as needed." Host robots.txt HTTP 404,
  read as allow-all by `scripts/robots_policy.py`. Fields `NAME, ABBREV, GNIS_ID, FIPS_CODE, SWIS,
  NYSP_ZONE, POP1990..POP2020, DOS_LL, DOSLL_DATE, NYC, CALC_SQ_MI, DATEMOD`. Key: `FIPS_CODE`.
- Measured: 62 features; `NYC='Y'` on exactly Bronx 36005, Kings 36047, New York 36061, Queens
  36081, Richmond 36085; `NYC='N'` on 57; `returnDistinctValues` on `NYC` returns only `N` and `Y`.
  `max(DATEMOD)` on this layer is 2020-05-19. `copyrightText` names NYS ITS Geospatial Data
  Services, nysgis@its.ny.gov, 518-242-5029; the layer's own text and gis.ny.gov state an as-is
  disclaimer and no attribution requirement (whether that credit line is the sources-page credit
  for every state layer is an open decision).
- Trap: the spatial reference is **EPSG:26918** (NAD83 / UTM 18N) and the polygons are
  **shoreline-clipped**; request `outSR=4326` and expect the coast to disagree with TIGERweb's
  water-inclusive county fabric (one verifier counted 22 named counties affected, including the
  five boroughs). The `NYC` flag is the county-legislature gate inside the city; it is NOT a form
  field: the layer says nothing about which of the 57 elect a Board of Supervisors, so that fact
  needs a second source (the county tier).
- Card: identity only in PR 2 (the county, its population, a link to the county's site); the
  legislature and the District Attorney are county-tier work.

### `municipality`

- Source: layers 4 Cities (62), 5 Towns (933), 6 Cities_Towns (995 = 62 + 933), 7 Villages (532),
  same service. Fields on 4/5/6: `NAME, MUNI_TYPE, MUNITYCODE, COUNTY, GNIS_ID, FIPS_CODE, SWIS,
  POP..., DOS_LL, DOSLL_DATE`; Villages carry `NAME, TOWN, COUNTY`. `maxRecordCount` 1000 on these
  layers, so Cities_Towns needs a second page.
- Measured cross-check: 532 villages + 62 cities = 594 = TIGERweb Incorporated Places for
  STATE='36' on the current, BAS 2026 and ACS 2025 vintages (the Census 2020 vintage layer is 596,
  so name the vintage layer id in any cross-check). TIGERweb county subdivisions are 1,023, which is
  not 995 and is not a usable cross-check either way.
- Trap: **villages nest inside towns and are many-to-many with them**: 76 of 532 villages carry a
  multi-town `TOWN` value as one comma-joined string (Ballston Spa = "Ballston, Milton"; Brockport =
  "Clarkson, Sweden"; Baldwinsville = "Lysander, Van Buren"), and some span counties (Almond:
  "Allegany, Steuben"; Attica: "Genesee, Wyoming"). A nesting builder splits the string; it never
  joins on one key. New York City is ONE row in the Cities layer (OBJECTID 33, `COUNTY` = "New York,
  Bronx, Kings, Richmond, Queens"), so inside the city this layer says "New York" and the borough
  is the city tier's answer. Villages are being maintained: 'Ateres' (Sullivan, 2025-05-02) and
  'Rushville' (2026-01-13) are the two rows edited since 2025-01-01.
- Roster: none. No statewide town-board or municipal-officials dataset exists on gis.ny.gov,
  data.ny.gov or the NYS ITS AGOL org (measured absence). 933 towns + 532 villages + 62 cities is
  an order of magnitude past the Illinois municipal-officials ladder. Ship the polygons, record the
  gap.

### `school-district`

- Source: `https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Schools/FeatureServer/18`
  ("School Districts"), fields `SCHOOL_ID, SCHOOLDIST, SED_CODE_1, POPULAR_NA, SEDDIR_BOC`.
- Measured: 936 polygons. TIGERweb School for STATE='36': 663 unified + 3 secondary + 14 elementary
  = 680. The state layer is finer and carries SED codes.
- Trap: **936 against 680 must be reconciled before a layer of record is chosen**; the extra ~256
  polygons may be administrative or non-unified entities. Neither number ships until the difference
  is named (the Iowa 325-vs-324 rule). The NYC Community School District layer (Socrata
  `8ugf-3d8u`, 32 districts) stays as the city tier under coverage, because it is a different
  concept.

### `election-district` (statewide) and the poll sites

- Source: `https://services6.arcgis.com/EbVsqZ18sv1kVJ3k/arcgis/rest/services/NYS_Elections_Districts_and_Polling_Locations/FeatureServer`,
  the NYS ITS AGOL org (`NYSGIS_GPO`), the same server `ny/` already reads for `early-voting`.
  robots.txt on services6.arcgis.com answers HTTP 403: an API host, default-allow under the
  reader's RFC 9309 rule. Layer 4 "Election Districts", fields `OBJECTID, County, Municipality,
  Election_District, Shape__Area, Shape__Length`; `maxRecordCount` 1000; EPSG:26918.
- Measured: **13,335 rows, 13,289 distinct (County, Municipality, Election_District) tuples,
  46 excess rows** in 41 duplicated tuples (Orange 28, Erie 4, Westchester 3, Dutchess 2, Onondaga 2,
  Tompkins 2, Chautauqua 1, Cortland 1, Delaware 1, Rockland 1, Tioga 1; Orange's "Monroe Town 1"
  through "Monroe Town 21" nearly all at n=2, consistent with one municipality loaded twice);
  **2 rows with null geometry** (OBJECTID 1894 and 1895, Erie / Lancaster / "Lancaster 28"); all 62
  County values present and summing to 13,335 (Kings 1,403, Queens 1,132, Nassau 1,122, Suffolk
  1,070, Westchester 910, New York 851, Bronx 714, Monroe 659, Erie 658, Onondaga 452 ... Hamilton
  11; NYC subtotal 4,345). Cross-checks: Broome 126 = Broome County's own ED layer 126; Wyoming 40 =
  the county's own `Wyco_ElectionDistrictFinal` 40. Note that `returnDistinctValues=true` with
  `returnCountOnly=true` returns 13,335, i.e. ArcGIS ignores the distinct flag in count-only mode;
  the distinct count came from paging the groupBy (14 pages).
- **The districts are dated 2025-06-12 by the layer's own description** ("as of 6/12/25"); the
  service's `lastEditDate` 2026-06-16 is a poll-site refresh ("The polling place data is as of June
  2026"). Staleness is per county: Tompkins measured 64 in the state layer = the county's own
  ElectionDistricts2024 layer (64), while the county's ElectionDistricts2026 layer has 61. The
  publisher states that "Spatially, the districts may not align with districts from neighboring
  counties or with other reference datasets such as civil boundaries."
- Trap: **no FIPS or GEOID field**; keys are free text, County spelled "St Lawrence" (no period),
  Municipality casing inconsistent ('STAMFORD', 'Town Of Ithaca', 'Middletown City'),
  Election_District formats varying by county ('Cortland WARD 5 ED2 LD5', 'GED-06', 'City of Ithaca
  1-1'). Whether the string joins cleanly to any county BOE's results file is UNTESTED; test one
  county before any results route is designed. LATFOR publishes a 2018-ED-to-2020-VTD equivalency,
  the only crosswalk found.
- Decision recorded, not made: inside the city the instance already reads the NYC DCP
  `NYC_Election_Districts` service (live, paged, ~4,200 EDs) against this layer's NYC subtotal of
  4,345; PR 2 measures which is current before choosing whether the city keeps DCP under coverage
  and the state layer answers outside it.
- Poll sites: layer 0 Early Voting Non-NYC 251, layer 1 Early Voting NYC 158 (already shipped as
  `early-voting`), layer 2 Election Day Non-NYC 3,655, layer 3 Election Day NYC 1,214; polling data
  as of June 2026. These are what no other instance gets free: Iowa and Michigan already ship
  statewide precincts (1,660 and 3,895 features) but neither carries polling places.
- **SHIPPED IN PR 2 AS TWO LAYERS, NOT FOUR.** The publisher's NYC / non-NYC split is a publishing
  decision rather than two concepts, so `early-voting` merges layers 1 and 0 and the new
  `polling-place` merges layers 3 and 2, each behind one toggle. The split is clean and that was
  measured rather than assumed: each non-NYC table names exactly 57 counties, the state's 62 less
  the five boroughs, so nothing is carried twice and no row needs dropping. Total payload for the
  Election Day pair is 1,146,385 bytes over six paged requests, lazy on first toggle.
- **THE ELECTION DAY CARD IS THE HONESTY CALL OF THIS PR AND IT IS WORTH STATING PLAINLY.** Every
  New York voter is assigned one poll site by their election district, so the nearest site is not
  necessarily theirs — anywhere in the state, early voting included. Nothing published joins the
  two: layer 4's election-district polygons carry no poll-site column and none of the four
  poll-site tables carries an election district, verified against all five field lists. The
  authoritative lookup is the state Board of Elections', which asks for a name and date of birth
  this app never collects. **The argument against shipping it at all is real** — a card that looks
  like an answer and is not is the exact failure this project's honesty rules exist to prevent —
  and it was shipped anyway on three grounds: the locations and addresses are true and are what a
  reader asking "where do people vote near me" actually wants; every other nearest-N layer in the
  fleet has the same shape (the nearest post office is not "your" post office); and refusing to
  ship means a reader gets nothing where the state publishes 4,869 verified locations. The
  mitigations are structural rather than a sentence nobody reads: the LABEL is "Election Day Poll
  Site (nearest 3)" rather than "Polling Place", the intro's SECOND clause is the limitation, and
  the card carries the BOE lookup as a footer link. **That link needed an engine change**: the
  nearest-point factory could not carry a `primaryLink` at all until 2026-09-18, so a layer whose
  honest answer is "these are near you, yours is looked up elsewhere" had to put the URL in the
  intro as unclickable text. One line in `engine/index.html/nearest-point-factory.txt`,
  byte-identical for the five instances that pass nothing.
- **The BOE estate is behind a Cloudflare managed challenge, not a plain 403**, and that matters
  because the "API host, default-allow" reading does not apply to it. Measured 2026-09-18: a
  `cType: 'managed'` challenge body on `/robots.txt` AND on the root, for `elections.ny.gov`,
  `www.elections.ny.gov` and `voterlookup.elections.ny.gov` alike. That is an access control. It is
  never worked around and the host is never fetched; the link is for a reader's own browser, which
  clears it. The plan's earlier note that the estate "403s robots.txt" was right about the status
  code and wrong about what produced it.
- **THE STRING `<Null>` IS A VALUE IN THESE TABLES, NOT A NULL**, and a card that read the columns
  verbatim would print it. Counted 2026-09-18: it fills 3,117 of layer 2's 3,655 comment fields,
  3,355 of its second address lines and 199 of layer 0's 251 town fields — and, which is what makes
  it a guard rather than a filter on one column, 5 CITY values and 2 ZIP values on layer 2. Every
  string these cards read goes through one reject function.
- **The comment and town columns are not read at all.** `USER_Town` looked like it might say
  whether any site in the county may be used (28 of 251 rows say "ALL"), but it holds four distinct
  values across the whole table — 199 `<Null>`, 28 "ALL", 24 "NONE" — plus 24 blanks. A field that
  is right where it speaks and silent where it matters cannot carry a claim about a voter's rights,
  so no card makes one, and no statute is cited that this project has not read.

### `judicial-district` (statewide, computed)

- Today: `ny/data/app/judicial-districts.json` is the five counties relabelled 1, 2, 11, 12, 13 from
  TIGERweb, a hand-applied crosswalk baked into `ny/data/judicial-districts.geojson`.
- Statewide: New York Judiciary Law §140 defines 13 judicial districts as unions of whole counties,
  so the layer is COMPUTABLE by dissolving the state Counties layer on a 62-row lookup, with better
  provenance than the relabel. The memberships as enumerated in the evidence
  (`https://law.justia.com/codes/new-york/jud/article-5/140/`, search-only; the page was NOT
  fetched) are UNVERIFIED and **must be checked against the statute before the lookup is written**.
  No published judicial-district shapefile was found on gis.ny.gov.
- No roster: a New York judge is elected from a district and the card links to nycourts.gov, as
  the Illinois subcircuit card does.

### `fire-station` and `library` (statewide points)

- Fire stations: `FireStations/FeatureServer/0` on the same AGOL org, **2,966 points** with `Name,
  Address, City, Zip, Contact, ContactTitle, Phone, EMAIL`. Libraries: `NYS_Schools/FeatureServer/15`,
  **762 points** with `LEGAL_NAME, POPULAR_NAME`, address, `COUNTY_DESC, INST_TYPE_DESC`.
- Measured absence: no statewide fire-DISTRICT polygon layer and no library-system boundary layer
  on the 35-entry ITS directory, the 49-service AGOL org or the domain-scoped data.ny.gov catalogue.
  Fire districts are elected special districts; the absence is a recorded gap, not a search failure.
- **DECIDED IN PR 2, AND THE TWO WENT OPPOSITE WAYS BECAUSE THE MEASUREMENTS DID.** The question
  was the same for both — does the state's point set cover the city's facilities — and the answer
  was yes for fire stations and no for libraries.
  - `fire-station`: the state layer REPLACED the city's. Measured 2026-09-18, 214 of FDNY's 219
    firehouses match a state point within 60 metres, five sampled addresses match exactly with the
    same company designations, and the state set ADDS six volunteer companies inside the city that
    FDNY's own dataset omits (Rockaway Point, Roxbury, Gerritsen Beach, Broad Channel, West
    Hamilton Beach and City Island's). Three caveats are recorded in the block's own comment: two
    FDNY borough-command offices are the only clean gaps and may not belong on this card at all;
    Rescue 2 appears in both sets about 480 metres apart, a currency disagreement between two
    publishers rather than a missing station; and the Name field free-texts several companies per
    building exactly as FDNY's own field did.
  - `library`: the state layer is a COMPLEMENT, so BOTH ship behind ONE toggle. Measured the same
    day, NYS_Schools layer 15 holds 762 points typed PUBLIC LIBRARIES across 59 of the 62 counties,
    names no county Kings, Queens or Richmond at all, and its only three rows inside the five
    boroughs are private special collections — the Frick Collection, the Huntington Free Library
    and the Kristine Mann Library. Not one NYPL, BPL or QPL branch. So the city dataset answers
    inside the city, the state points answer outside it, and those three city rows are DROPPED
    rather than merged: two of the three sit within a few blocks of an NYPL branch, and offering a
    reader an appointment-only research collection ahead of the lending branch would be a worse
    answer than the one the city dataset already gives. The filter names all five borough counties
    even though three return nothing today, so a later edition adding a Brooklyn row is dropped by
    the same rule rather than appearing unexamined.
  - Two toggles for one concept is still not the fleet's shape, and neither of these became one.

### `school-site` and `post-office` (widened)

- `school-site`: deleting `NYC_SCHOOL_WHERE` widens the NYSED query statewide. The five NYC counties
  alone are ~2,831 points, so the statewide query needs a paging or bbox-envelope strategy
  (`loadArcGISPaged` exists in the engine); the statewide count is UNMEASURED.
- `post-office`: `ny/index.html:8899-8906` builds one `fetchArcGISAsGeoJSON` call from `METRO_BBOX`
  with no `resultOffset` loop; the USGS service caps at 2,000 features and signals it with HTTP 200
  plus `exceededTransferLimit`, so a widened envelope would truncate silently. Illinois's version is
  paged; port that. The statewide count is UNMEASURED.

### `zip-code` (statewide ZCTA)

- Today: NYC MODZCTA (Socrata `pri4-ifjk`, ~178). Statewide: live TIGERweb ZCTA, the SF and
  Michigan precedent. The STATE='36' count is UNMEASURED. MODZCTA stays as the city tier under
  coverage only if PR 2 finds it answers something ZCTA does not; otherwise it is retired.

### The city tier: `coverage:` on the NYC registrations

Every registration below is NYC-only by source or by concept and gains
`coverage: nycCoverage` (a promise resolving a containment test against
`ny/data/app/borough-boundaries.json`, load failure rejecting through to the engine's fail-open),
the Madison pattern. The list is read from the inventory measured 2026-09-18; it is 24 registrations,
the three legislative layers being the only ones that stay ungated:

- Identity and polygon layers (18): `borough`, `borough-president`, `district-attorney`,
  `municipal-court`, `school-district` (the Community School District), `cec`, `fire-battalion`,
  `council`, `community-district`, `election-district` (the DCP service; see the decision above),
  `police-sector`, `police-precinct`, `zip-code` (MODZCTA; see above), `neighborhood`, `hs-zone`,
  `ms-zone`, `es-zone`, and `judicial-district` until the statewide computed layer replaces it.
- Nearest-N layers (6): `school-site`, `police-station`, `fire-station`, `post-office`, `library`,
  `early-voting`. Which of these widen into the statewide source and which stay city-tier under
  coverage is decided per layer in the subsections above; a widened layer is ungated.

The three DOE zones carry `emptyNote` text written for the city (the high-school zone's reads
"Most NYC high schools admit by application citywide, not by zone."); under coverage the note never
renders upstate, which is the point.

Concepts with no statewide analogue and no coverage question beyond the gate: `council`,
`community-district`, `cec`, `police-precinct`, `police-sector`, `fire-battalion`,
`municipal-court`, `borough-president`, `neighborhood` (NTA is a NYC Department of City Planning
construct), the three DOE zones.

### The wash: three bands

`coverage_key` goes from `{ outside: "Outside New York City" }` to a three-band key. Proposed wording,
mirroring Illinois's row and to be confirmed in PR 2:

```json
"coverage_key": {
  "outside": "Outside New York",
  "region": { "edge": "New York",
              "label": "Statewide layers only",
              "sub": "City districts and county legislatures not sourced here yet" }
}
```

§2.5.1: a three-band instance owes GEOMETRY as well as words. The region ring is passed as the
second argument at boot, `drawOutOfScopeMask(loadMetroOutline, loadStateOutline)`, and the key
renders only the bands the draw produced. Declaring `region` without wiring the geometry gets a
two-band key and no error: check the map, not the worksheet.

### The ring: `ny/scripts/build_metro_outline.py`

- **Copy `wi/scripts/build_metro_outline.py` into `ny/scripts/`, never import across trees**:
  `scripts/validate_workflow_deps.py` requires an instance's scripts to import only inside its own
  tree.
- `STATE_FIPS = "36"`. `METRO_COUNTY_FIPS` = the five boroughs (36005, 36047, 36061, 36081, 36085),
  which qualify under §3.5.1 on their city election-district layer. `DISPATCH_COUNTY_FIPS` empty
  until tranche 1. One INSIDE anchor per served county (five) and one OUTSIDE anchor per unserved
  county (57), each chosen in PR 2 and measured against the shipped ring by `--check`;
  `check_anchor_registry()` holds the anchor list to the county list offline, one INSIDE per served
  county, none doubled, none both inside and outside.
- Two outputs: `ny/data/app/metro-outline.json` (the five-borough dissolve) and
  `ny/data/app/ny-state-outline.json` (the region ring from layer 0 of the same TIGERweb MapServer),
  both simplified at the same tolerance, per §2.5.1. Both are cache-first; `CACHE_NAME` moves.
- `ny/data/app/state-counties.json` and `ny/data/state/state.json` (`fips 36, usps NY,
  house_districts 26`), the bootstrap the three state instances carry and `ny/` lacks.
- Read the ring count from `--check`, never from a sentence.

### Paging and page-weight budget (open item)

Measured 2026-09-18 in `ny/data/app/` (19 files, 1.6 MB): the three statewide legislative files
are 208,936 + 258,071 + 364,774 = **831,781 bytes, ~832 KB, all precached cache-first**;
`borough-boundaries.json` 285,290; `municipal-court-districts.json` 262,883. PR 2 adds the county
fabric (62), two rings, and decides live-versus-pre-built for 995 cities and towns and 532
villages; the statewide EDs (13,335, 14 pages at 1,000) and the widened school sites are live and
paged. **No size is stated for a file that has not been built**; each new pre-built file's byte
size and each live layer's page count are recorded in this section when PR 2 ships, against
`REMOTE_GEOJSON_TIMEOUT_MS` (30,000 ms, `engine/index.html/fetch-retry.txt`).

### Gates PR 2 must pass

`python3 ny/scripts/build_metro_outline.py --check`; `python3 scripts/check_cache_version.py --base
origin/main`; `python3 scripts/build_privacy_page.py --check` and
`node scripts/probe_point_transmission.mjs --check`, which will move if any new layer sends the
selected point (the county layer's `.atPoint` hook, if it has one, is a transmission the privacy
page must name); `python3 ny/scripts/validate_index.py ny/index.html`; the ny smoke test; and a
manual check that a Buffalo click shows the statewide cards answering, the city cards hidden, and
no nearest card naming an NYC facility.

## PR 3: go-live

The exact list, from the approved plan:

1. Flip `metro_bbox`, `permalink_gate`, `metro_center` (and the initial zoom) to the state values
   in "Worksheet and fleet values" below.
2. `metros.json`: `label`, `landing_name`, `explorer_name`, `blurb`, `bbox`, with **`scope` as the
   honest served count** (see below). `id` stays `nyc`, `tag` stays `ny`, `url` and `emoji` do not
   change.
3. `python3 scripts/generate_metro_files.py --sync-fleet` into all six worksheets (every worksheet
   carries a `metro_explorers` entry for `nyc`), then regenerate every GENERATED region.
4. `scripts/build_coverage_map.py`: move `ny` from `CITY_TAGS` to `AREAS` with
   `{"outline": "ny/data/app/metro-outline.json", "state_outline": "ny/data/app/ny-state-outline.json"}`;
   the build hard-fails otherwise. The landing page's `outline:` field is discovered from disk and
   needs no edit; front-door routing gains the ring-based contested-point refinement automatically.
5. Regenerate every generated root page: landing (the "not yet" list drops New York; the summary
   "Not yet: 46 states and DC" as shipped 2026-09-18 becomes 45), coverage map, privacy page (its
   per-app row renames from `landing_name`; its docstring carries a literal "New York City, San
   Francisco" that needs a hand edit), `llms.txt` (`build_llms_txt.SUMMARY` is the one hand-typed
   fleet sentence and names "New York City"), question forms (five `ny` pages re-render their
   placeholder to "Address or ZIP in New York"), concept pages (the cross-instance "same lookup,
   <scope>" row), `about.html`.
6. `scripts/build_wikidata_draft.py` `JURISDICTION`: the `ny` entry maps to the item for New York
   City; replace it with the item for New York State, **verified on wikidata.org through the
   `Special:EntityData/*.json` endpoint the fleet's robots reading permits, never remembered**, and
   add its `LABELS` row. The gate fails only on a missing entry, never on a wrong one, so a wrong
   id would ship.
7. `scripts/build_officeholder_tables.py` `CITY_TABLES`: the `ny` entries name New York City bodies
   (the City Council, the NYPD) as JSON-LD `org` nodes and remain correct as city-tier tables;
   re-read them at go-live so no node comes to claim a state body.
8. `docs/DATA_LAYER_GUIDEBOOK.md`: the four `| Concept | Chicago | NYC | SF | ...` matrix headers
   (lines 2890, 2939, 2960, 2970 on 2026-09-18) and the "Fleet totals" line at 2882.
9. `docs/press-list.json`: the `nyc` region (12 outlets, label "New York City", `utm_source`
   `press-ny`, subject line "Every district your address is in, from CB to precinct") re-scoped
   for the state; two outlets already cover it (City & State New York, New York Focus). Nothing
   has been sent to any of the 12 (`sent_on` null on all, read 2026-09-18).
10. `ny/CLAUDE.md`: the geocoder roles, the metro facts, the retired "New York City" prose.
11. Retitle `/ny/` under the lifted hold: `brand.app_name`, the `<title>`, H1, OG and JSON-LD nodes.
    `scripts/build_og_image.mjs` renders the tag (`ny`) and needs no edit.
12. **Re-choose the anchors.** All three current anchors are NYC-only layers and the negative point
    sits inside the state fabric. The generator emits ONE `anchor_point` and every `anchors[]` row
    is evaluated at it, so a statewide anchor means either moving `anchor_point` off City Hall
    (which retires the three NYC anchors) or a generator change; decide in PR 3. The new negative
    point is chosen outside New York State and measured to miss every anchor layer.
13. **SUPERSEDED 2026-09-19 — the swap below was measured and REJECTED, and what shipped is a
    two-provider fall-through instead.** GeoSearch stays first: it is PAD-backed, keyless, and
    answered every city string correctly. The state service resolves `20 W 34th St, New York, NY`
    ten miles away in Bensonhurst at score 98.7, consuming the directional `W` as part of the
    street name, and never returns the right address at all for `350 5th Ave, Manhattan, NY`,
    consuming `Manhattan` as a street name — on an app that names an officeholder from a point,
    a silently wrong borough is worse than no answer. It also cannot drive a type-ahead in one
    call (`findAddressCandidates` returns zero for partial input), so a swap needed either seven
    requests per keystroke or an edit inside the `geocoder-search` ENGINE fence all six instances
    carry. What shipped: a zero-result GeoSearch falls through to Photon hard-bounded to
    `METRO_BBOX` and biased to `METRO_CENTER` — the same provider and shape the four statewide
    instances already use — so the city keeps its authoritative answers and upstate gets one at
    all. THE FALL-THROUGH IS NOT OPTIONAL: `siblingMetroAt()` excludes THIS metro, so after the
    bbox widened, an upstate hit from the sibling lookup landed inside our own box and was
    dropped, leaving the reader told nothing matched while the map beneath classified that point
    on fifteen layers. The original proposal, for the record:

13. The geocoder (§2.6: a state-authoritative keyless geocoder with real autocomplete wins).
    `https://nysgeohub.ny.gov/arcgis/rest/services/Geocoder/NYS_Geocoder/GeocodeServer`, measured
    2026-09-18: capabilities `Geocode,ReverseGeocode,Suggest`, currentVersion 11.5, no token, CORS
    `Access-Control-Allow-Origin: https://districtry.com` on GET and a 200 OPTIONS preflight, the
    two-call suggest-then-magicKey contract GeoSearch provides. It replaces GeoSearch for the
    bounded type-ahead and the office-pin lookup and **does not replace unbounded Photon**, which
    serves the cross-metro sibling lookup (`geocodeUnbounded`, `ny/index.html:6027`) and the root
    landing page's router; the state geocoder returns zero candidates for a Chicago or a San
    Francisco address. It can be built dark in PR 2 behind the city bbox. Three measured quirks
    for the swap: candidates duplicate across sub-locators (de-duplicate); borough-as-city input is
    inconsistent ("350 5th Ave, Manhattan, NY" resolved to a Brooklyn street at score 85.87 while "1
    Centre St, Manhattan" scored 100), so normalise or floor the score; the service updates on the
    second and fourth Friday, 5 to 7 am, and no rate limit is stated anywhere (sustained behaviour
    UNVERIFIED).
14. **The bbox trap was measured not to fire.** A full New York State box (-79.76, 40.50, -71.85,
    45.02) contains no other instance's `metro_center` (il 41.8781,-87.6298; ca 37.7749,-122.4194;
    wi 44.9,-89.565; ia 41.94,-93.39; mi 44.8,-85.6) and overlaps no other hand-off rectangle, so
    `validate_index.py` check 0b stays quiet and `resolveMetro()` resolves every point with one
    candidate.

Then tranche 1 via `county-n-plus-1`, adding a `scripts/build_county_pages.py` `INSTANCES` entry when
the first roster file lands (the registry question, below).

## The county tier

### The form table

The 16 / 40 / 1 split is stated verbatim on slide 22 of NYSAC's "Foundations of County Government"
deck (`https://www.nysac.org/media/1q3gtuzx/foundations-of-county-government-1.pdf`, HTTP 200,
32 slides, fetched 2026-09-18): "16 counties have a Board of Supervisors | 40 counties have a County
Legislature | 1 County has a Board of Representatives". The deck names no county. The per-county
forms below come from NYSAC's County Organization Report 2023 refresh
(`https://www.nysac.org/media/0yeap2sd/county-organization-report-2023-refresh.pdf`, 878,380 bytes,
42 pages), whose pp. 8-9 tables one verifier extracted with a stdlib-only PDF read on 2026-09-18 and
a second verifier could not extract at all. Those tables carry two measured defects: **Essex is
labelled "Bd. of Legislature" and is a Board of Supervisors** (its own page, fetched: 18 town
supervisors, weighted vote), and **Schuyler is omitted** (56 rows for 57 counties; the report's
narrative calls its body a legislature). Repaired, the tables reproduce 16 / 40 / 1 exactly.

**The deck and the report are a LEAD. Each county's form is settled from a certified election
document when that county is built, per `county-n-plus-1`, never from a website heading or this
table.** The report's "Legislature" covers bodies titled County Legislature and Board of Legislators
alike; a 34 + 6 split of those names is search-only (Wikipedia, uncited there) and UNVERIFIED.

Verification status is what was measured on 2026-09-18. "Page 200" means an HTTP status probe of a
live board page on the county's own domain, body NOT read and robots NOT checked per host unless
stated; a 200 confirms a path, not its contents. "Polygons N" is a live district layer measured by
`returnCountOnly`. Seat counts are not carried here except where a measured polygon count is one.

| County | Form (NYSAC 2023 tables) | Verified 2026-09-18 | Notes |
|---|---|---|---|
| Albany | Legislature | Polygons 39 (`AlbCo_LegDist_2023`, services6 org mBzcjj7yrA6fBe9F); pages 200 | Hub attributes the item to the county's Real Property Tax Service Agency; the DOS handbook's "39 in Albany" corroborates |
| Allegany | Legislature | UNVERIFIED | AGOL search zero |
| Broome | Legislature | Polygons 15, county-owned `br_elections/MapServer/3`; page 200 | AGOL search zero; `legislature.broomecountyny.gov` unreachable |
| Cattaraugus | Legislature | UNVERIFIED | 404 on a guessed path says nothing |
| Cayuga | Legislature | UNVERIFIED | AGOL search zero |
| Chautauqua | Legislature | UNVERIFIED | 404 on a guessed path |
| Chemung | Legislature | UNVERIFIED | AGOL search zero |
| Chenango | Board of Supervisors | UNVERIFIED live | robots.txt unreachable (TLS hostname mismatch); search snippet only |
| Clinton | Legislature | Polygons 10 (`LegDistricts`, services3 org 33FPYaVQYNa7sFJ5, owner CutterL) | Hub titles it "Clinton County Legislative Districts"; a "Proposed ... 2023" viewer sits under clinco.maps.arcgis.com |
| Columbia | Board of Supervisors | Page 200 | Five Hudson city-ward supervisors (search-confirmed) |
| Cortland | Legislature | AGOL item present, incl. a "2028 Cortland Legislative Districts" item | Count not measured |
| Delaware | Board of Supervisors | UNVERIFIED live | search snippet only |
| Dutchess | Legislature | Page 200; results page 200 | AGOL: a Vassar-owned combined layer and a services5 `County_Legislative_Districts` hit, owner unconfirmed; `giswww.dutchessny.gov` unreachable |
| Erie | Legislature | Polygons 11, county-owned `OGIS/ErieCountyNY/MapServer/9`, `Legislator` field; page 200 | `gis2.erie.gov` and `elections.erie.gov` unreachable |
| Essex | Board of Supervisors (report says "Bd. of Legislature": defect) | Page 200 and read by one verifier | 18 town supervisors, weighted vote by town population |
| Franklin | Legislature | UNVERIFIED | AGOL search zero; DOS handbook names it among the smallest boards |
| Fulton | Board of Supervisors | Page 200 | Johnstown Wards 1-4 and Gloversville ward supervisors (search-confirmed) |
| Genesee | Legislature | Page 200 | |
| Greene | Legislature | Page 200 | |
| Hamilton | Board of Supervisors | UNVERIFIED live | search snippet; 404 on a guessed path |
| Herkimer | Legislature | UNVERIFIED | AGOL search zero |
| Jefferson | Legislature | UNVERIFIED | |
| Lewis | Legislature | UNVERIFIED | one verifier saw a services8 `LClegislatordist_SB` hit; not measured |
| Livingston | Board of Supervisors | Page 200 | |
| Madison | Board of Supervisors | Page 200 | Oneida city supervisors by ward grouping (search-confirmed) |
| Monroe | Legislature | Polygons 29 (services2 org EYLPKrWH43iFrTLz, owner 'Etak', third party); page 200; results page 200 | Layer carries turnout fields and no officeholder; `gis.monroecounty.gov` unreachable |
| Montgomery | Legislature | UNVERIFIED | |
| Nassau | Legislature | Polygons 19 (`Nassau_Legislative_Districts_2020`, services1 org rsOafHhKLHpnpr4t); page 200 | AGOL owners ebautista2 / ms867_CUGIS; NOT confirmed as the county |
| Niagara | Legislature | Polygons 15, county-owned `Legislative_Districts/FeatureServer/0` | No officeholder field; found only by probing the host, AGOL returned nothing relevant |
| Oneida | Legislature | UNVERIFIED | AGOL zero; `gis.co.oneida.ny.us` unreachable |
| Onondaga | Legislature | Polygons 17 (services.arcgis.com org uDTUpUPbk8X8mXwl, owner CommGeog, third party) | Sibling 2019, 2023 and "July 8 2026 V2/V3" draft items on a Syracuse University account; `ongov.net` unreachable |
| Ontario | Board of Supervisors | Page 200 | Geneva and Canandaigua ward groupings; the county publishes an election-district shapefile page (200, undated); robots.txt answered 429 to one verifier |
| Orange | Legislature | Page 200 | AGOL query poisoned by Orange County, California; `gis.orangecountygov.com` unreachable |
| Orleans | Legislature | UNVERIFIED | AGOL zero; 404 on a guessed path; DOS handbook names it among the smallest boards |
| Oswego | Legislature | UNVERIFIED | AGOL zero |
| Otsego | Board of Representatives | County page fetched by one verifier | Districts 1-14; District 14 is "Oneonta City - Wards 7 & 8" |
| Putnam | Legislature | UNVERIFIED | AGOL zero |
| Rensselaer | Legislature | UNVERIFIED | AGOL zero |
| Rockland | Legislature | Polygons 17 (`Legislative_Districts_2024`, services1 org 0Lw2m57KEotYYFaA, owner jmz75_CCEgeomaps, Cornell Cooperative Extension) | Roster page `rocklandgov.com/departments/legislature` HTTP 403 (WAF); `gis.rocklandgov.com` unreachable; Hub lists the item under "Rockland County Planning Department" |
| St. Lawrence | Legislature | UNVERIFIED | |
| Saratoga | Board of Supervisors | Page 200; search-level read by one verifier | 23 supervisors over 21 municipalities, Saratoga Springs and Clifton Park two each, weighted vote under Local Law No. 1 of 2022 (search-level, UNVERIFIED by a page read); `maps.saratogacountyny.gov` unreachable |
| Schenectady | Legislature | UNVERIFIED | AGOL zero |
| Schoharie | Board of Supervisors | UNVERIFIED live | search snippet; 404 on a guessed path |
| Schuyler | Legislature (omitted from the tables; narrative) | UNVERIFIED | |
| Seneca | Board of Supervisors | HTTP 202 managed challenge on the county site | Access control; recorded, not probed further |
| Steuben | Legislature | Page 200 | |
| Suffolk | Legislature | Polygons 18, county-owned `LocalGovernmentSQLData/LegislativeDistrict/FeatureServer/0` with `REPNAME, PARTY, DISTPHONE, DISTEMAIL`; roster site 200; results page 200 | A sibling layer holds the 2014-2023 plan; `SuffolkCountyDistrict` (1 feature) carries countywide officers |
| Sullivan | Legislature | UNVERIFIED | AGOL zero |
| Tioga | Legislature | UNVERIFIED | AGOL zero |
| Tompkins | Legislature | AGOL items present (one 2012 vintage; Hub "Legislative Districts" and a "Proposed 16 V3 E" item) | The county's own ED layers were measured (2024: 64; 2026: 61); legislative-district count not measured |
| Ulster | Legislature | Page 200 | AGOL zero; `maps.ulstercountyny.gov` unreachable |
| Warren | Board of Supervisors | Page fetched by one verifier | Glens Falls one supervisor per ward (Wards 1-5); Queensbury one town supervisor plus four at-large; per-ward seat pages |
| Washington | Board of Supervisors | Page 200 | |
| Wayne | Board of Supervisors | UNVERIFIED live | search snippet; robots served |
| Westchester | Legislature | Polygons 17, county-owned `Datahub_Boundaries/MapServer/160` with `LEGISLATOR, PHONE, ADDRESS, CITY, ZIP, WEBSITE`, no e-mail | `westchesterlegislators.com` unreachable |
| Wyoming | Board of Supervisors | Page 200 | County's own `Wyco_ElectionDistrictFinal` 40 = state ED layer 40 |
| Yates | Legislature | UNVERIFIED | |

Totals as of 2026-09-18: 10 supervisor boards confirmed by a live page (Ontario, Livingston, Essex,
Madison, Columbia, Washington, Warren, Wyoming, Fulton, Saratoga), 13 districted counties with a
measured polygon layer (Erie 11, Monroe 29, Onondaga 17, Westchester 17, Nassau 19, Suffolk 18,
Albany 39, Broome 15, Niagara 15, Rockland 17, Clinton 10, Tompkins, Cortland), 6 districted by a
roster page only (Steuben, Genesee, Greene, Orange, Ulster, Dutchess), Otsego by a page read, Seneca
behind a 202, Rockland's roster page behind a 403. Everything else is UNVERIFIED.

### Provenance flags

- **Third-party AGOL items**: Monroe (owner 'Etak'), Onondaga ('CommGeog'), Rockland
  ('jmz75_CCEgeomaps', Cornell Cooperative Extension). None is the county. Each needs a
  county-published source or a recorded provenance gap before its geometry ships.
- **Nassau's owner is unconfirmed**: the item's owners are AGOL users not identifiable as the
  county; the county's own page (200) is the citation of record and the search for a
  county-published layer continues.
- **The four layers carrying a name column** (Westchester `LEGISLATOR`, Suffolk `REPNAME`, Nassau
  `Name`, Erie `Legislator`) are join keys only, under the Coles rule. Westchester's carries no
  e-mail and Erie's carries a name alone, so neither meets a `MIN_EMAILS`-shaped roster contract on
  its own; the roster comes from the county's board page.
- **Onondaga may be mid-redistricting**: the "July 8 2026 V2/V3" draft items. Settle which plan is
  in force from a certified document before anything ships.

### Tranche 1: Westchester, Suffolk, Nassau, Erie

All four have measured district polygons and a roster page answering 200. Per county: geometry
from the layer (Westchester and Suffolk county-owned; Erie county-owned; Nassau pending a
confirmed county source), roster from the board page under the robots gate, form from a certified
election document, the dispatch entry, the county's outline, its INSIDE anchor, its FIPS in
`METRO_COUNTY_FIPS`, `metros.json` `scope` re-derived, `CACHE_NAME` bumped, the per-county page
generated. Suffolk additionally publishes a countywide-officers layer (Executive, Comptroller,
Clerk, District Attorney, Sheriff), which is County-card material.

### Supervisor counties

A Board of Supervisors is DISTRICTED by town or by city ward, and weighted voting is a card fact
(NYSAC slide 25 also states weighted voting for legislator counties without a charter). Every town
seat has its polygon in `NYS_Civil_Boundaries` layer 5 or 6. **Ward seats do not**: Hudson
(Columbia), Johnstown and Gloversville (Fulton), Geneva and Canandaigua (Ontario), Glens Falls
(Warren) and Oneida (Madison) seat supervisors from city wards, the civil-boundaries service has no
ward layer, and no statewide ward source was found. Multi-seat rows exist (Queensbury one town
supervisor plus four at-large; Saratoga Springs and Clifton Park two each). So a supervisor county
needs a town/city polygon layer with multi-seat rows plus per-city ward polygons, sourced per city,
before its card can say who represents a point inside those cities. Whether any of those seven
cities publishes ward GIS is UNVERIFIED (only Ontario's shapefile page was seen).

### The registry question

`scripts/build_county_pages.py` `INSTANCES` takes one entry per state with one `member_word`, one
`heading` and one `page_title`, rendered into the H1 and the JSON-LD. New York's Boards of
Supervisors, County Legislatures, Boards of Legislators and Otsego's Board of Representatives
cannot share one honest title. The entry therefore needs per-county form wording, or the registry
grows a field, which is a generator change and is decided when the first roster file lands (the
gate `check_registration()` refuses the build until an adapter reads it). The concept slug is
undecided among `county-board`, `county-legislature` and another; existing slugs are
`county-board` (il, wi), `county-supervisor` (ia), `county-commissioner` (mi), and the slug is both
the output directory and the index page name.

## Traps (carried into every phase)

1. **EPSG:26918, shoreline-clipped.** Every NYS ITS polygon layer (civil boundaries, the three
   chambers, the EDs) is in UTM 18N and clipped to the shoreline; pass `outSR=4326`, and expect the
   coast to disagree with TIGERweb's water-inclusive geometry at anchors and negative points.
2. **The state's chamber rosters are not one shape.** Senate and Assembly `EMAIL` are real
   addresses and `ADDRESS` is the district office (PHONE the Albany line, DIST_PHONE the local one).
   Congress `EMAIL` is a house.gov contact-form URL on 26 of 26 rows and `ADDRESS` is the
   Washington office on 26 of 26; only `DIST_PHONE` is district-level. Senate District 12 carries
   `NAME='VACANT'` with party, e-mail and address null (62 named of 63), and Assembly Districts 108
   and 109 carry no district phone or address. The shipped `ny-senate-members.json` names a member
   for District 12; that divergence is queued as its own task, and under the fleet's rule a
   divergence not pinned ships no name. Adopting the state layers as the roster source is a
   source switch with a divergence to pin, not a free win; no `lastEditDate` is exposed on the three
   services (Hub items modified 2026-08-28 and 2026-08-07).
3. **Villages are many-to-many with towns**: 76 of 532 (measured), some spanning counties.
4. **936 school districts against TIGERweb's 680**: reconcile before either ships.
5. **The statewide ED layer**: dated 2025-06-12, 46 duplicate tuples, 2 null geometries, no FIPS,
   free-text keys, per-county staleness (Tompkins 64 against the county's 61). Its poll sites are
   current (June 2026) and are what no other instance gets free.
6. **The USGS post-office query is unpaged** at a 2,000 cap; the NYSED school query needs paging
   at ~2,831 points for the city alone.
7. **The Judiciary Law §140 membership table is search-only** and must be verified before the
   dissolve is written.
8. **The `NYC='Y'` flag** partitions 5 / 57 cleanly today; whether NYS ITS commits to maintaining
   the field is UNVERIFIED (treat it as measured-today, and gate the count of `Y` rows at exactly 5).
9. **Legacy state locators retire October 2026.** The `gisservices.its.ny.gov/arcgis/rest/services/Locators/*`
   GeocodeServers have no Suggest (their `/suggest` answers `{"error":{"code":400,"message":"Invalid
   URL."}}`), were frozen at a final update on 2026-06-26, and gis.ny.gov schedules their retirement
   for "October 2026 (subject to change)". Build on `nysgeohub` NYS_Geocoder only. It replaces
   GeoSearch and NOT unbounded Photon.
10. **The NYS Board of Elections estate answers 403 on robots.txt** (elections.ny.gov,
    www.elections.ny.gov, results.elections.ny.gov, nyenr.elections.ny.gov) and
    results.elections.ny.gov answers 403 on its root. Under the government-website reading that is
    an access control; nothing on those hosts was fetched, nothing here is, and everything about
    NYS BOE in this plan is search-only. Search text says the certified canvass is reported by
    County / Judicial District / Congressional / Senate / Assembly district, not by election
    district, so per-ED results come from the 62 county boards one at a time.
11. **Onondaga's 2026 draft district items** on a Syracuse University account.
12. **The most litigated congressional map in the fleet**: three maps in three years
    (`ny/WATCH.md`); the 2022 maps were struck and special-mastered, and a 2024 redraw followed. A
    constitutional amendment on mid-decade redistricting passed the legislature in June 2026 with
    projected effect in 2028 (search-only, UNVERIFIED). Staged on enactment, shipped at
    effectiveness.
13. **Results publishers.** No New York county was found on pollresults.net,
    platinumelectionresults.com or results.gbsvote.com (a targeted search, not a per-county sweep);
    Erie publishes an Excel archive back to 2001 (search-only; `elections.erie.gov` unreachable);
    Onondaga appears to use Results Caster (`www.resultscaster.com`, robots absent) via a
    `lake.ongov.net` page that was unreachable; Monroe, Suffolk and Dutchess results pages answer
    200, contents unread.
14. **Counting rows is not counting districts**: the 13,335 lesson applies to every ArcGIS count
    here; page the groupBy for a distinct count.
15. **A data.ny.gov search without `domains=data.ny.gov` federates across every Socrata domain**
    and returns New Jersey, Maryland and Washington datasets; that unscoped search is what would make
    someone believe New York publishes legislative districts there.
16. **An AGOL title search under-reports county publishers** (Broome, Niagara); probe the county
    host next, never record an absence from a search miss.
17. **UNREACHABLE is not absent.** The county hosts in the appendix's last list were connection
    failures from this sandbox, not 404s; none may be recorded as a gap until re-probed from another
    network, the rule `docs/EXPANSION_GUIDE.md` §0.4 item 6 states.
18. **The smoke test evaluates every anchor at one point**, so a statewide anchor is a decision
    about `anchor_point`, not an extra row.

## Verification (every PR, in order)

Run the workflow's own command list (`.github/workflows/smoke-test.yml`), never a remembered
subset; `.claude/skills/steward/SKILL.md` mirrors it. The gates that decide each PR:

**PR 1**

```bash
python3 scripts/generate_metro_files.py --check
python3 scripts/compose_app.py --check
python3 scripts/check_engine_parity.py index.html
python3 scripts/validate_doc_counts.py
python3 scripts/validate_skills.py
python3 ny/scripts/validate_index.py ny/index.html      # and the other five instance validators
bash scripts/vendor_leaflet.sh                           # sandbox only; production reaches the CDN
python3 -m http.server 8000
BASE_URL=http://localhost:8000/il/ node scripts/smoke_test.mjs
BASE_URL=http://localhost:8000/ny/ node ny/scripts/smoke_test.mjs   # and ca, wi, ia, mi likewise
```

plus a manual check in the served app that a Loop click still lists three post offices and that a
click far outside any instance's coverage renders the new empty sentence rather than a distant
facility.

**PR 2**

```bash
python3 ny/scripts/build_metro_outline.py --check
python3 scripts/check_cache_version.py --base origin/main
python3 scripts/build_privacy_page.py --check
node scripts/probe_point_transmission.mjs --check
python3 ny/scripts/validate_index.py ny/index.html
BASE_URL=http://localhost:8000/ny/ node ny/scripts/smoke_test.mjs
```

plus the Buffalo click described above.

**PR 3**

The full battery per `.claude/skills/steward/SKILL.md`, and:

```bash
BASE_URL=http://localhost:8000 node scripts/landing_test.mjs   # an upstate address must route to /ny/
python3 scripts/build_coverage_map.py --check
python3 scripts/build_about_page.py --check                    # the generalised scope check
```

## Worksheet and fleet values (proposed; PR 3 sets them)

All of these are PROPOSED. The state values are derived from measurements dated 2026-09-18 and are
re-measured against the shipped county fabric in the PR that sets them.

- `this_metro` "nyc" (unchanged). `STATE_FIPS = "36"` in the METRO config block and in
  `ny/scripts/build_metro_outline.py`. `ny/data/state/state.json`: `{"fips": "36", "usps": "NY",
  "house_districts": 26}`.
- `metro_bbox`: today `{minLng -74.27, minLat 40.48, maxLng -73.68, maxLat 40.93}`. The measured
  statewide extent of the shipped legislative geometry is lng -79.763 to -71.777, lat 40.477 to
  45.016; the Iowa convention pads the state extent by about 0.05 degrees. Proposed
  `{minLng -79.82, minLat 40.43, maxLng -71.73, maxLat 45.07}`, to be set from the shipped county
  fabric.
- `permalink_gate` (and `poi_geocode_bbox` if declared): today `{minLat 40.4, maxLat 41.05,
  minLng -74.3, maxLng -73.6}`; padded about 0.15 degrees past the state extent at go-live.
- `metro_center`: today `[40.7128, -74.006]` (City Hall). At go-live a point that frames the whole
  state at about zoom 7 (the state centroid is near 42.9, -75.5 per the fleet-gates measurement);
  chosen in PR 3.
- `coverage_key`: the three-band block proposed in PR 2 above.
- `metros.json` for `nyc`: `label` "New York", `landing_name` "New York", `explorer_name`
  "districtry New York", `blurb` rewritten for the state, `bbox` the hand-off box (must contain no
  sibling's `metro_center`; measured clear), and **`scope` the served count**: it stays "5 boroughs"
  (or becomes "5 counties") until a county joins the ring, and then "N counties" with N =
  `len(METRO_COUNTY_FIPS)`, gated by the generalised `check_illinois_scope`. Never "all 62 counties".
- `--sync-fleet` touches all six worksheets: `metro-worksheet.json` (il), `ny/`, `ca/`, `wi/`,
  `ia/`, `mi/metro-worksheet.json`, each of which carries a `metro_explorers` entry for `nyc`
  (measured at il :33, ca :55, ia :392, mi :682, ny :44, wi :2539 on 2026-09-18).
- `sw.cache_name`: any different name evicts the old cache; renaming
  `nyc-district-explorer-shell-v15` to a `districtry-ny-shell-v1` shape at go-live is cosmetic and
  allowed, and a bump is required regardless.
- `brand.app_name` "districtry New York"; `geocoder.address` and `geocoder.poi` re-pointed to the
  NYS Geocoder; `geocoder.unbounded` unchanged (Photon); `search_placeholder` "Search a New York
  address".

## California: held, and what reopens it

Held on 2026-09-18 for three measured reasons: `/ca/` had 154 impressions and zero clicks on the
districtry.com property (2026-08-23 to 2026-09-15) against `/ny/`'s 22 clicks; its supervisorial
geometry has no state publisher and is roughly 51 per-county scrapes with 3 of 13 sampled county
sites refusing this client (Shasta, Kern and `rivcocob.org` 403) and two more with robots.txt
timeouts (San Diego, Santa Clara); and its legislative geometry is SF-clipped (6 / 4 / 8 features
against 52 / 40 / 80) and must be rebuilt statewide across the Prop 50 remap, where TIGERweb CD120
carries the AB 604 map but the districts take effect for sitting members in January 2027 and the
2026 CD 1 and CD 14 specials ran on CD119 lines, so a statewide congress layer before then is
CD119-based under show-current-until-effective.

What reopens it: a click on `/ca/`, or a decision to want a Southern California tranche. The cheap
tranche is SCAG's six-county supervisorial aggregate (Imperial, Los Angeles, Orange, Riverside,
San Bernardino, Ventura; 34 polygons, one service; its embedded roster is stamped 2023 and stale, so
it is a join key under the Coles rule) plus the roster of record, the Secretary of State's
California Roster 2026 county-officials PDF
(`https://admin.cdn.sos.ca.gov/ca-roster/2026/counties.pdf`, HTTP 200, Last-Modified 2026-06-29,
57 five-member boards and San Francisco's 11 as "District N: Name", 296 seats measured). That PDF
refutes the research claim that no statewide California roster exists.

**One ruling is owed before any California roster fetch: `admin.cdn.sos.ca.gov` answers its
robots.txt with 403.** The New York half of the assessment refused the whole `elections.ny.gov`
estate on exactly that answer under the government-website reading, while the California half
fetched the roster under the API-host default-allow reading. A government CDN is neither case by
name; the operator decides which reading applies, and the same reading then applies to both
states. Until then the CA roster route is not open, and the SoS page that links the PDF
(`https://www.sos.ca.gov/elections/helpful-resources/redistricting`, robots allowed) is.

Nothing in `ca/` changes in PRs 1 to 3 except what the engine ceiling and the shared generators
carry to every instance.

## Appendix: measured source ledger

Every row measured 2026-09-18 unless the Measured column says search-only. Robots verdicts are
`scripts/robots_policy.py`'s: "absent" is HTTP 404 read as allow-all; "served, allows" is a file
with no binding rule against the path; "403, API default-allow" is a refused robots.txt on an API
host under the reader's RFC 9309 rule; "403, access control" is the government-website reading and
nothing on that host was fetched; "unchecked" means a status probe only.

| # | Source | URL | Publisher | Coverage | HTTP | Robots | Measured |
|---|---|---|---|---|---|---|---|
| 1 | NYS ITS ArcGIS REST root | `https://gisservices.its.ny.gov/arcgis/rest/services?f=json` | NYS ITS Geospatial Services | statewide | 200 | absent | 35 service entries (MapServer/FeatureServer pairs; one verifier counted 23 distinct names, another 20; the first researcher said 34), folders Locators and Utilities; no county-legislature service |
| 2 | NYS Civil Boundaries | `https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Civil_Boundaries/FeatureServer` | NYS ITS Geospatial Data Services | statewide | 200 | absent | 9 polygon sublayers; Counties 62, Cities 62, Towns 933, Cities_Towns 995, Villages 532, Indian_Territories 10; "Publication Date: March 2026"; `NYC='Y'` on exactly 5; 76 of 532 villages multi-town; EPSG:26918 |
| 3 | NYS Senate Districts | `https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Senate_Districts/FeatureServer/0` | NYS ITS Geospatial Services | statewide | 200 | absent | 63; roster fields; District 12 `VACANT`; Hub item modified 2026-08-28; EPSG:26918; maxRecordCount 500 |
| 4 | NYS Assembly Districts | `https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Assembly_Districts/FeatureServer/0` | NYS ITS Geospatial Services | statewide | 200 | absent | 150; same fields; Districts 108 and 109 null district office; Hub item modified 2026-08-07 |
| 5 | NYS Congressional Districts | `https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Congressional_Districts/FeatureServer/0` | NYS ITS Geospatial Services | statewide | 200 | absent | 26; `EMAIL` is a contact-form URL 26/26; `ADDRESS` is the DC office 26/26; maxRecordCount 1000 |
| 6 | NYS Elections Districts and Polling Locations | `https://services6.arcgis.com/EbVsqZ18sv1kVJ3k/arcgis/rest/services/NYS_Elections_Districts_and_Polling_Locations/FeatureServer` | NYS ITS with NYS BOE and county BOEs | statewide | 200 | 403, API default-allow | layer 0 = 251, 1 = 158, 2 = 3,655, 3 = 1,214, 4 = 13,335 rows / 13,289 tuples / 2 null geometries; EDs as of 2025-06-12; polling as of June 2026 |
| 7 | NYS ITS AGOL org services | `https://services6.arcgis.com/EbVsqZ18sv1kVJ3k/arcgis/rest/services?f=json` | NYS ITS Geospatial Services (NYSGIS_GPO) | statewide | 200 | 403, API default-allow | exactly 49 services; FireStations 2,966; NY_State_Police_Troop_Boundary 10; NYS_Address_Points 6,579,287; no county-legislature service |
| 8 | NYS Geocoder | `https://nysgeohub.ny.gov/arcgis/rest/services/Geocoder/NYS_Geocoder/GeocodeServer` | NYS ITS Geospatial Services | statewide, NY-only | 200 | absent | `Geocode,ReverseGeocode,Suggest`; v11.5; keyless; CORS open to districtry.com; zero candidates for Chicago and SF addresses; duplicates across sub-locators; borough-as-city inconsistency |
| 9 | Legacy NYS locators | `https://gisservices.its.ny.gov/arcgis/rest/services/Locators/Street_and_Address_Composite/GeocodeServer` | NYS ITS Geospatial Services | statewide | 200 | absent | `Geocode,ReverseGeocode` only; `/suggest` returns error 400; frozen 2026-06-26; retire October 2026 |
| 10 | NYS Geocoding Service page | `https://gis.ny.gov/nys-geocoding-service` | NYS GIS Program Office | statewide | 200 | served, allows | Suggest documented; as-is disclaimer; no attribution, rate or key condition; retirement schedule; maintenance 2nd and 4th Friday 5-7 am |
| 11 | Legacy geocoder page | `https://gis.ny.gov/legacy-address-geocoder` | NYS GIS Program Office | statewide | 200 | served, allows | "final update was published on June 26, 2026 ... online through October 2026" |
| 12 | NYS Schools | `https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Schools/FeatureServer` | NYS ITS / NYSED | statewide | 200 | absent | 18 sublayers; School Districts (18) 936; BOCES (17) 38; Libraries (15) 762; school points by type |
| 13 | gis.ny.gov robots.txt | `https://gis.ny.gov/robots.txt` | NYS GIS Program Office | statewide | 200 | served (1,586 bytes), allows | Drupal default; dos.ny.gov serves the identical file |
| 14 | Civil boundaries programme page | `https://gis.ny.gov/civil-boundaries` | NYS GIS Program Office | statewide | 200 | served, allows | "for planning and general use purposes only"; no attribution requirement; measured absence of fire-district and library-system polygons |
| 15 | data.ny.gov catalogue (domain-scoped) | `https://api.us.socrata.com/api/catalog/v1?domains=data.ny.gov&search_context=data.ny.gov` | New York State / Socrata | statewide | 200 | absent (api.us.socrata.com); data.ny.gov served, allows | q=boundaries 196 (Civil Boundaries is an `href` pointer; Metropolitan Planning Areas Boundaries is a dataset); q=election 14, all campaign finance; q=county 773; no county-legislature, ED or results dataset |
| 16 | LATFOR data page | `https://latfor.state.ny.us/data/` | NYS LATFOR | statewide | 200 | empty file, allow-all | 2020 adjusted population; 2018-ED-to-2020-VTD equivalency; census, vote and enrollment files; state districts only |
| 17 | Redistricting Data Hub, New York | `https://redistrictingdatahub.org/state/new-york/` | Redistricting Data Hub | statewide | 200 | served, allows this path | 299 NY dataset slugs, none a county or local legislature set; the page's wording is the generic "Local data is available in select jurisdictions", not a plain statement of absence; downloads account-gated |
| 18 | NYS Board of Elections estate | `https://elections.ny.gov/election-results` | NYS Board of Elections | statewide | 403 on robots.txt on four hosts; 403 on `results.elections.ny.gov/` | 403, access control | search-only: certified results by County / Judicial / Congressional / Senate / Assembly district |
| 19 | DOS Local Government Handbook, county government | `https://video.dos.ny.gov/lg/handbook/html/county_government.html` | NYS Department of State | statewide | 200 | absent | names the four body titles; weighted voting versus districting; "57 counties" outside the city; sizes 7 (Franklin, Orleans) to 39 (Albany); 23 charter counties; no per-county form |
| 20 | NYSAC County Organization Report 2023 refresh | `https://www.nysac.org/media/0yeap2sd/county-organization-report-2023-refresh.pdf` | NYSAC | statewide | 200 | served, allows | 878,380 bytes, 42 pages (one researcher reported 857,380 and ~83, wrong); pp. 8-9 form tables, 56 rows; Essex mislabelled, Schuyler omitted; extractable by one verifier, not by another |
| 21 | NYSAC Foundations of County Government deck | `https://www.nysac.org/media/1q3gtuzx/foundations-of-county-government-1.pdf` | NYSAC | statewide | 200 | served, allows | 32 slides; slide 22 states 16 / 40 / 1; slide 25 weighted vote in non-charter legislator counties |
| 22 | NYSAC County Directory | `https://www.nysac.org/member-services/county-directory/` | NYSAC | statewide | 200 | served, allows | flipbook of county officials, all 62 counties; not machine-readable; district breakdown UNVERIFIED |
| 23 | Erie County Legislature Districts | `https://gis.erie.gov/server/rest/services/OGIS/ErieCountyNY/MapServer/9` | Erie County GIS | per-county | 200 | allowed | 11; `Legislator` field; `https://www.erie.gov/legislature` 200 |
| 24 | Westchester County Legislative Districts | `https://giswww.westchestergov.com/arcgis/rest/services/Datahub_Boundaries/MapServer/160` | Westchester County GIS | per-county | 200 | allowed | 17; `LEGISLATOR, PHONE, ADDRESS, CITY, ZIP, WEBSITE`; no e-mail |
| 25 | Suffolk County Legislative District | `https://gis.suffolkcountyny.gov/server/rest/services/LocalGovernmentSQLData/LegislativeDistrict/FeatureServer/0` | Suffolk County GIS | per-county | 200 | allowed | 18; `REPNAME, PARTY, DISTPHONE, DISTEMAIL, LASTUPDATE`; sibling 2014-2023 plan; countywide-officers layer; `https://www.scnylegislature.us/` 200 |
| 26 | Nassau Legislative Districts 2020 | `https://services1.arcgis.com/rsOafHhKLHpnpr4t/arcgis/rest/services/Nassau_Legislative_Districts_2020/FeatureServer/0` | AGOL owners ebautista2 and ms867_CUGIS; NOT confirmed as the county | per-county | 200 | 403, API default-allow | 19; `Name, Address, Phone, Email, Website`; `https://www.nassaucountyny.gov/1780/County-Legislature` 200 |
| 27 | Monroe County Legislative District | `https://services2.arcgis.com/EYLPKrWH43iFrTLz/arcgis/rest/services/Monroe_County_Legislative_District/FeatureServer/0` | AGOL owner 'Etak', third party | per-county | 200 | 403, API default-allow | 29; turnout fields, no officeholder; `https://www.monroecounty.gov/legislature` 200 |
| 28 | Onondaga County Legislative Districts | `https://services.arcgis.com/uDTUpUPbk8X8mXwl/arcgis/rest/services/Onondaga_County_Legislative_Districts/FeatureServer/0` | AGOL owner 'CommGeog', third party | per-county | 200 | 403, API default-allow | 17; `COUNTY_LEG` only; 2019, 2023 and "July 8 2026 V2/V3" siblings |
| 29 | Albany County Legislative Districts | `https://services6.arcgis.com/mBzcjj7yrA6fBe9F/arcgis/rest/services/AlbanyCoLegislativeDist/FeatureServer/0` | Hub attributes to Albany County RPTSA | per-county | 200 | 403, API default-allow | 39 (`AlbCo_LegDist_2023`); `https://www.albanycounty.com/departments/legislature` and `/legislators` 200 |
| 30 | Broome County elections MapServer | `https://gis.broomecountyny.gov/arcgis/rest/services/elections/br_elections/MapServer` | Broome County GIS | per-county | 200 | absent | layer 3 County Legislative Districts 15; layer 1 Election Districts 126 (= state layer); `https://www.gobroomecounty.com/legis` 200 |
| 31 | Niagara County Legislative Districts | `https://gis.niagaracounty.com/arcgis/rest/services/Legislative_Districts/FeatureServer/0` | Niagara County GIS | per-county | 200 | absent | 15; `LEG, Label`; no officeholder field |
| 32 | Rockland Legislative Districts 2024 | `https://services1.arcgis.com/0Lw2m57KEotYYFaA/arcgis/rest/services/Legislative_Districts_2024/FeatureServer/0` | AGOL owner jmz75_CCEgeomaps (Cornell Cooperative Extension) | per-county | 200 | 403, API default-allow | 17; `LD, District`; `rocklandgov.com/departments/legislature` 403 |
| 33 | Clinton County Legislative Districts | `https://services3.arcgis.com/33FPYaVQYNa7sFJ5/arcgis/rest/services/LegDistricts/FeatureServer/0` | AGOL owner CutterL; Hub-titled as the county's | per-county | 200 | 403, API default-allow | 10; `LD` |
| 34 | ArcGIS Online item search | `https://www.arcgis.com/sharing/rest/search` | Esri | discovery | 200 | served, allows | hits for Erie, Monroe, Onondaga, Westchester, Nassau, Suffolk, Albany, Rockland, Dutchess (Vassar-owned), Tompkins, Cortland, Clinton, Lewis; zero for Broome and Niagara, who both publish; "Orange" poisoned by Orange County, California |
| 35 | ArcGIS Hub datasets API | `https://hub.arcgis.com/api/v3/datasets` | Esri | discovery | 200 | served, allows | single-county items only (Clinton, Nassau, Westchester, Tompkins, Rockland, Albany, Lewis); no statewide aggregation |
| 36 | ShareGIS NY owner sweep | `https://www.arcgis.com/sharing/rest/search?q=title%3A%22NYS%20Civil%20Boundaries%22` | NYS GIS Program Office | statewide | 200 | served, allows | publisher is AGOL owner `NYSGIS_GPO` (org EbVsqZ18sv1kVJ3k); `owner:sharegisny` does not exist (dead end recorded) |
| 37 | data.gis.ny.gov Hub search | `https://data.gis.ny.gov/api/search/v1/collections/dataset/items` | NYS GIS Clearinghouse | statewide | 200 | served (192 bytes), allows | q="county legislative district" 3 (the three state layers); no county-legislature item |
| 38 | TIGERweb Legislative | `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer` | U.S. Census Bureau | statewide | 200 | served, no group binds | STATE='36': layer 0 (120th CD) 26; layer 1 (2026 SLDU) 63; layer 2 (2026 SLDL) 150; layer 4 (119th CD) 26; no county-legislature layer |
| 39 | TIGERweb School | `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer` | U.S. Census Bureau | statewide | 200 | served, no group binds | STATE='36': unified 663, secondary 3, elementary 14 |
| 40 | TIGERweb Places / CouSub | `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer` | U.S. Census Bureau | statewide | 200 | served, no group binds | STATE='36': county subdivisions 1,023; incorporated places 594 (current, BAS 2026, ACS 2025), 596 (Census 2020 vintage) |
| 41 | Cornell CUGIR | `https://cugir.library.cornell.edu/catalog.json?q=legislative%20district&per_page=20` | Cornell University Library | statewide | 200 | served, allows | 33 hits, all agricultural districts and Tompkins election districts (2002-2013); no county legislative districts |
| 42 | Board-of-Supervisors pages (status probe) | `https://www.ontariocountyny.gov/89/Board-of-Supervisors` and nine siblings | ten counties | per-county | 200 on all ten | unchecked | Ontario, Livingston, Essex, Madison, Columbia, Washington, Warren, Wyoming, Fulton, Saratoga; body not read except Essex and Warren by one verifier |
| 43 | County legislature roster pages (status probe) | `https://www.scnylegislature.us/` and eleven siblings | twelve counties | per-county | 200 on all listed | unchecked | Suffolk, Erie, Monroe, Nassau, Dutchess, Albany, Broome, Orange, Ulster, Steuben, Genesee, Greene |
| 44 | Otsego Board of Representatives page | `https://www.otsegocountyny.gov/legislature/board_of_representatives_/` | Otsego County | per-county | 200 | unchecked on this host (the verifier's robots read was of `www.otsegocounty.com`, HTTP 404) | Districts 1-14; District 14 "Oneonta City - Wards 7 & 8" |
| 45 | Warren County Board of Supervisors | `https://www.warrencountyny.gov/bos` | Warren County | per-county | 200 | served, allows | 20 supervisors listed: ten towns, Glens Falls Wards 1-5, Queensbury five |
| 46 | Essex County Board of Supervisors | `https://essexcountyny.gov/essex-county-board-of-supervisors/` | Essex County | per-county | 200 | served (182 bytes), allows | 18 town supervisors; weighted vote by town population |
| 47 | Ontario County election maps page | `https://www.ontariocountyny.gov/921/Election-and-Political-Maps-of-Ontario-C` | Ontario County | per-county | 200 | robots.txt answered 429 to one verifier | election-district shapefile and PDFs listed; no dates shown |
| 48 | Erie County BOE results archive | `https://elections.erie.gov/ElectionArch` | Erie County Board of Elections | per-county | 302 on a status probe | unreachable robots | search-only: Excel results back to 2001 |
| 49 | County BOE results pages (status probe) | `https://www.monroecounty.gov/elections-results` and two siblings | Monroe, Suffolk, Dutchess BOEs | per-county | 200 | unchecked | contents and per-ED granularity NOT verified; Onondaga described as on Results Caster |
| 50 | NY Judiciary Law §140 | `https://law.justia.com/codes/new-york/jud/article-5/140/` | New York State (statute) | statewide | not fetched | not fetched | search-only enumeration of 13 whole-county districts; verify before use |
| 51 | Tompkins County ED layers | `https://services.arcgis.com/oJbAAWNInLrxvF0A/arcgis/rest/services/ElectionDistricts2026/FeatureServer/0` (and `ElectionDistricts2023/FeatureServer/1`) | Tompkins County | per-county | 200 | 403, API default-allow | 2026 layer 61; 2024 layer 64 (= state layer's Tompkins 64) |
| 52 | Wyoming County ED layer | `Wyco_ElectionDistrictFinal` on `services3.arcgis.com/Sq7KUOgahdDkqoAp` | Wyoming County | per-county | 200 | 403, API default-allow | 40 (= state layer's Wyoming 40); item modified 2026-07-06 |

### UNREACHABLE is not absent

Connection failures from this sandbox on 2026-09-18, not 404s; none may be recorded as a coverage
gap until re-probed from a different network:

`www.ongov.net`, `ongov.net`, `lake.ongov.net` (Onondaga); `westchesterlegislators.com`;
`legislature.broomecountyny.gov`; `gis2.erie.gov`; `elections.erie.gov`; `maps.saratogacountyny.gov`;
`gis.ocgov.net`; `gis.orangecountygov.com`; `giswww.dutchessny.gov`; `gis.co.oneida.ny.us`;
`maps.ulstercountyny.gov`; `gis.rocklandgov.com`; `gis.monroecounty.gov`.

Two hosts with a different non-answer: `www.co.chenango.ny.us` (robots.txt unreachable on a TLS
hostname mismatch; not fetched) and `www.ontariocountyny.gov` (robots.txt HTTP 429 to one verifier,
who did not fetch; the reader returns allow-all on a 429 and the other researcher's status probe
answered 200). Access controls, recorded and not worked around: `www.co.seneca.ny.us` (HTTP 202),
`rocklandgov.com/departments/legislature` (403), the `elections.ny.gov` estate (403 on robots.txt),
`ballotpedia.org` (202 on robots.txt).

This sandbox's egress runs through a proxy; a 403 or a connection reset from here is checked against
its response body before being recorded as a site property.
