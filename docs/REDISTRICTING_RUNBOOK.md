# Redistricting Runbook — Surviving Boundary Changes

Status: active, written while hypothetical, executable later. Owner: CHI, applies to every metro.
Cross-refs: docs/MECHANIZATION_PLAYBOOK.md (Conversions 2 & 3), docs/ENGINE_SYNC.md,
docs/METRO_EXPANSION_PLAYBOOK.md, docs/OPTIMIZATION_PLAYBOOK.md, scripts/validate_sources.py,
scripts/build_embedded_boundaries.py, scripts/smoke_test.mjs.

## Purpose + activation triggers

Boundaries change. The app's core promise — "click any point and see who represents you" —
silently rots the day a map changes and our geometry does not. This runbook exists because
redistricting is a **scheduled earthquake**: the 2030 census invalidates anchor geometry,
ground-truth points, smoke assertions, LAYER_AREA_RANK ordering, cached service-worker geometry,
and possibly roster join keys in EVERY metro near-simultaneously. It is also a series of off-cycle
tremors that are already happening.

### Decennial timeline (2030 cycle)

| Date | Event | Consequence for us |
|---|---|---|
| April 1, 2030 | Census Day | Counts begin; nothing changes yet. |
| Dec 31, 2030 | Apportionment counts delivered to the President | House seat counts per state known. |
| By April 1, 2031 (statutory) | P.L. 94-171 redistricting data delivered to states | State map-drawing can begin; start state-layer watch. |
| 2031–2032 | States redraw congressional + state-legislative maps, effective for 2032 elections | Congress + state Senate/House layers change in every metro. |
| 2032–2033 | Municipal remaps (wards, council, commissioner, ERSB) | City-level layers change. |
| Rolling, post-enactment | Census TIGERweb publishes new CD vintage | TIGERweb layer index + field names roll. **OBSERVED 2026-09-03: CD119 → CD120** (not CD121 as this table long guessed), layer renamed "120th Congressional Districts; January 1, 2026 vintage". The old field is REMOVED and its query returns an HTTP-200 error envelope. |

The 2030 statutory deadline is April 1, 2031 (13 U.S.C. 141(c): delivery "no later than April 1,
2031"), but the 2020 cycle slipped to Aug/Sep 2021 due to COVID. Do not assume the deadline holds.

### Off-cycle triggers (this is NOT hypothetical)

- **Court-ordered redraws** — extremely common 2022–2024: NY, AL, LA, GA congressional maps all
  redrawn off-cycle. In 2006 the Supreme Court (LULAC v. Perry) held neither the Constitution nor
  federal law bars mid-decade redistricting, so this door stays open.
- **Mid-decade partisan redraws** — the 2025–2026 wave. As of February 2026, six states —
  California, Missouri, North Carolina, Ohio, Texas, and Utah — had adopted new congressional maps
  ahead of the 2026 elections; before 2025 only two states had voluntarily redistricted mid-decade
  since 1970. California's Prop 50 (approved Nov 4, 2025) explicitly set new maps for 2026/2028/2030
  with the independent commission resuming in 2031. Treat "decennial-only" as false.
- **Administrative safety-layer reorgs** — per the NYC Mayor's Office (Dec 18, 2024), the "nearly
  $105 million 116th Precinct Station House" in Rosedale is "the first, entirely new NYPD command
  established in over 10 years with the last one opening in 2013," and "the southern portion of the
  105th Precinct and parts of the 113th Precinct have been incorporated into the new precinct."
  Police/fire districts change without any census.
- **Annual school-zone rotation** — CPS attendance boundaries get a new Socrata dataset id every
  school year (elementary/middle/high, SYxxyy). This is already a live annual mini-redistricting and
  is our rehearsal.

---

## Per-layer blast-radius inventory

Classify every layer by redistricting exposure. What breaks for any changed layer: anchor geometry
(data/app files), ground-truth points + smoke assertions, LAYER_AREA_RANK ordering, roster join
keys (district numbers can be renumbered, not just redrawn), TIGERweb layer index + field names
(the field is Congress-numbered and rolled `CD119` → `CD120` on 2026-09-03; note it is a BARE
`CD119`/`CD120`, never the `CD119FP` alias this runbook used to name — the app field lists that
said `cd119fp` never matched anything and silently used the NAME regex fallback), Socrata dataset ids (new
id per vintage), and service-worker cached geometry (needs CACHE_NAME bump). **Permalinks
survive:** they encode lat/lng, not district ids, so a point permalink still resolves — it simply
resolves to the NEW district after geometry updates, which is correct behavior. This is confirmed
against the architecture: permalinks are lat/lng-based, so no permalink migration is needed.

### CHI (37 layers)

| Layer | Exposure class | Enacting authority | What breaks |
|---|---|---|---|
| US Congress (IL) | Decennial + court/mid-decade | IL General Assembly | geometry, TIGERweb CD field, roster join |
| IL Senate / House | Decennial | IL General Assembly | geometry, roster join |
| IL Supreme Court districts | Almost-never | IL General Assembly | geometry (see note), roster join — the same five districts seat the Appellate Court, so a redraw moves BOTH benches' cards and `build_il_court_justices.py`'s county gate is what notices |
| Cook County Board of Review | Almost-never | statute | geometry |
| Wards (50) | Decennial-municipal | Chicago City Council | geometry, roster join, anchor if used |
| County board districts (consolidated: Cook 17 / Will 11 / DuPage 6 / Lake 19 / Kane 24 / McHenry 9 / Kendall 2) | Decennial-municipal | each county's board | per-county geometry + roster joins inside the one `county-board` layer (Lake's and Kane's rosters ride on their boundary GIS; Kendall's and McHenry's are weekly-scraped from each county's own directory — McHenry incl. its countywide-elected Chairman; Kendall's post-2020 reapportionment kept the line, so its County_Board_2010 service is the current map — re-verify at the next reapportionment) |
| ERSB school-board districts | New + volatile | IL statute (SB15) | geometry, numbering, roster join |
| Chicago police districts (22) | Administrative-rare | CPD | geometry, anchor, roster join |
| Community areas (77) | Never (frozen) | geography | none expected |
| CPS attendance boundaries | Annual | CPS | dataset id every year |
| ZIP codes | USPS-driven, not census | USPS | occasional |
| Cook / Will / DuPage / Lake / Kane / McHenry judicial subcircuits (Cook 20 + 12th / 18th / 19th / 16th / 22nd Cir.) | Statutory, rare | IL General Assembly | geometry (Kane and McHenry are pre-built — rebuild via build_embedded_boundaries.py on redraw) |
| Will / DuPage / Lake / Kane / McHenry / Kendall fire / library / precinct + Will / DuPage / Lake / Kane / Kendall park (+ DuPage special-police; + Cook fire/park/library tilings; + suburban Cook precincts; + Cook TIF tiling and the MWRD boundary) | Administrative / per-election | districts + county clerks | geometry (precincts redraw with county maps; DuPage's current map is the 2024 consolidation; Kendall's precinct layer is vintage-filtered `status='A'` — a new county map lands as new rows, re-check the filter; suburban Cook serves `precinctHistorical` L0 and Cook TIF serves `clerkTaxDistricts` L18 — both refreshed in place by the Clerk, vintages get their own layers; MWRD's boundary is essentially static) |
| County / township / municipality (statewide) | Annexation-driven, rolling | local referenda; TIGERweb vintages | TIGERweb vintage rolls |
| Statewide school districts (3 TIGERweb layers) | Consolidation-driven | ISBE / referenda | TIGERweb vintage rolls |

IL Supreme Court note: Public Act 102-0011 changed the judicial district boundaries "for the first
time since they were established in 1964." This layer redistricts almost never — do not assume it
changes in 2031. That asymmetry is the whole point of the inventory: some layers change every
decade, some almost never, some every year. The same act is 705 ILCS 23, the Judicial Districts Act
of 2021, and `scripts/build_il_court_justices.py` holds a transcription of its county lists: the
weekly roster run refuses to write unless the counties the court's own district pages name still
match it, so a redraw surfaces as a failing refresh rather than as silence.

### NYC (31 layers)

| Layer | Exposure class | Enacting authority | What breaks |
|---|---|---|---|
| US Congress (NY) | Decennial + court (very volatile) | Legislature / IRC / courts | geometry, TIGERweb CD field, roster join |
| NY Senate / Assembly | Decennial + court | Legislature / IRC | geometry, roster join |
| City Council (51) | Decennial-municipal | NYC Districting Commission | geometry, roster join |
| Community districts | Rarely (charter) | NYC charter | none expected |
| NYPD precincts (78) | Administrative-rare | NYPD | geometry, anchor, roster join |
| Borough | Never (geography) | geography | none |
| School districts/zones | Annual | DOE | dataset rotation |
| Election districts | Frequent (BOE) | NYC BOE | geometry |

NY congressional is the cautionary example: three maps in three years — the 2022 legislature map
was struck in Harkenrider v. Hochul and replaced by special-master (Cervas) lines for 2022, then
Hoffmann v. NYIRC forced a redraw and the legislature's new congressional map was signed Feb 28,
2024. Redistricting is emphatically not only decennial.

### SF (16 layers)

| Layer | Exposure class | Enacting authority | What breaks |
|---|---|---|---|
| US Congress (CA) | Decennial + mid-decade (Prop 50 precedent) | CA Citizens Redistricting Commission | geometry (pre-built SF-clip rebuild), roster join |
| CA Senate / Assembly | Decennial | CA Citizens Redistricting Commission | geometry, roster join |
| Supervisor districts (11) | Decennial-municipal | SF Redistricting Task Force (charter) | geometry, anchor, roster join |
| Election precincts | Same cycle as supervisors | SF Dept. of Elections | new Socrata dataset id ("Defined <year>" title) |
| BART Director districts (9) | Decennial (own cycle) | BART Board | geometry (BART ArcGIS), roster re-verify |
| SFPD districts (10) | Administrative-rare | SFPD | geometry, anchor |
| SFUSD attendance areas | Annual | SFUSD | dataset id every school year |
| Neighborhood / ZIP | Rarely / USPS-driven | DataSF / USPS | occasional |

SF's per-date calendar lives in the SF fork's `WATCH.md` (per-metro file); this master runbook
holds the response procedure.

### WI (12 layers)

| Layer | Exposure class | Enacting authority | What breaks |
|---|---|---|---|
| US Congress (WI) | Decennial | WI Legislature (court history: 2022 maps litigated) | geometry (pre-built statewide rebuild), roster join |
| WI Senate / Assembly | Decennial + PROVEN mid-decade (2024 remap after Clarke v. WEC) | WI Legislature / WI Supreme Court | geometry (wi/scripts/build_legislative_boundaries.py rebuild + agreement gate), roster join, both smoke anchors |
| County board districts | **SEMIANNUAL — the fleet's fastest-moving boundary** | each county board; filed with LTSB under Wis. Stat. 5.15(4)(br)1 on 15 Jan / 15 Jul | geometry (`wi/scripts/build_wi_supervisory_districts.py` rebuild), the county-board smoke anchor, and `county-board-directory.json`'s seat counts, which are read back from the geometry. Unlike every other row here this one has a KNOWN NEXT DATE rather than a trigger to watch for, and a county may change its board's size at any filing — the builder's 1,589-feature guard is meant to fail on that and be re-read, not raised reflexively |
| Court of Appeals (WI) | Statutory — a 752.11 amendment (text unchanged since 1977) | WI Legislature | geometry (`wi/scripts/build_wi_court_of_appeals.py` re-run) + roster keys; the weekly scrape asserts the county lists AND the 4/4/3/5 seat split, so the tripwire is a failed scheduled run |
| Circuit courts (WI) | Statutory — a 753.06 amendment (last real movement is historical; the three two-county circuits have held) | WI Legislature | geometry (`wi/scripts/build_wi_circuit_courts.py` re-run) + the roster join keys; the weekly roster scrape ASSERTS the composition against wicourts, so the tripwire is a failed scheduled run, not a silent drift |
| Municipal wards (WI) | **SEMIANNUAL** — the same 15 Jan / 15 Jul filings as the county-board row | each municipality via its county's LTSB filing, Wis. Stat. 5.15(4)(br) | nothing to rebuild — the layer is LIVE against LTSB's Current service, so a filing lands in the app the day LTSB republishes; the monthly source report's returnCountOnly row is where a count change surfaces, and the supervisory builder's ward-reconciliation gate re-witnesses the ward↔district pairing on its own semiannual re-run |
| Aldermanic districts (WI, 838) | **SEMIANNUAL** — the districts are unions of the wards above, so every filing window can move them | each city or village council, carried as ward `ALDERID` coding in its county's LTSB filing | re-run `wi/scripts/build_wi_aldermanic_districts.py` per its WATCH.md row (pre-built — the dissolve, its pinned exclusion list, the BAS witness and the point-agreement gate all re-run); bump the sw cache with the file |
| County / CouSub / Municipality | TIGER-rolling | Census Bureau vintage | pre-built `state-counties.json` on rebuild; live layers self-update |
| School districts (3 tilings) | Annual-ish TIGER updates | WI DPI consolidations → TIGER | pre-built unified file; live layers self-update; a consolidation moves the unified/paired seam |
| ZIP codes | USPS-driven, not census | USPS | occasional |
| Post offices | Facility churn | USPS → USGS structures | occasional |

WI's per-date calendar lives in `wi/WATCH.md` — including the standing mid-decade note: Wisconsin's
legislative maps have moved off the census cycle before, so a court-ordered remap is a live trigger
here in a way it is not in most states.


### MI (11 layers)

| Layer | Exposure class | Enacting authority | What breaks |
|---|---|---|---|
| U.S. House (MI) | Decennial + **PROVEN mid-decade elsewhere in this vintage** | MI Independent Citizens Redistricting Commission (2018 Prop 2) | geometry (`mi/scripts/build_legislative_boundaries.py congress` rebuild + agreement gate), roster join. The FIELD is versioned and the old name is REMOVED, not deprecated: `CD120` today, and a query naming a retired `CD119` returns HTTP 200 carrying a JSON 400 envelope, so the builder dies as "no features" — read that as "the vintage rolled" |
| MI Senate / House | Decennial | MI Independent Citizens Redistricting Commission | geometry (same builder, `mi-senate` / `mi-house`) + both roster joins. The SLD layer indices (1/2) roll their NAME in place — 2024 → 2026 observed 2026-09-03 — while `SLDU`/`SLDL` survive, so a vintage roll here needs no rebuild unless the lines actually moved; measure before assuming |
| County commissioner districts | **Decennial, on the census cycle** | each county's apportionment commission, filed under MCL 46.401-46.405 and compiled statewide by the Bureau of Elections | geometry (`mi/scripts/build_mi_commissioner_districts.py` rebuild — 619/83 exact-count guards, per-county 1..N numbering, MCL 46.401(1)'s 5..21 board-size check, and the guard that refuses the file if the source's officeholder columns reappear). The 2021 plans run the 2020-census cycle, so the next apportionment is ~2031. **THE ENDPOINT CANNOT ANNOUNCE A REPUBLISH**: the layer has no `editingInfo`, no `lastEditDate` and no date field at all, so the only machine-readable staleness signal is the AGO item's own `modified` epoch on arcgis.com — a watch that polls only `gisagocss.state.mi.us` can never detect one |
| County | TIGER-rolling | Census Bureau vintage | pre-built `state-counties.json` on rebuild; the coverage ring (`mi/scripts/build_metro_outline.py`) is dissolved from the SAME fabric, so a county rebuild wants an outline rebuild and a `--check` |
| Township or City · City or Village | TIGER-rolling | Census Bureau vintage (the underlying incorporations are state/local, continuous) | **NOTHING TO REBUILD — both are LIVE TIGERweb**, no builder and no committed `data/app` file, so a vintage roll reaches them on its own and no cache bump applies. What a roll CAN break is the type row: both cards derive the civil-division kind from what TIGER's own NAME carries beyond BASENAME, and the `KIND_NOTE` tables in `mi/index.html` cover exactly the suffixes measured 2026-09-04 (township · charter township · city; city · village). An unseen suffix renders NO type row rather than a wrong one, which is the safe failure — but it is silent, so re-measure the suffix distribution after a roll. `mi/scripts/validate_sources.py` watches each endpoint still answering for `STATE='26'` |
| School District (Unified / Elementary) | TIGER-rolling; district consolidations are continuous and local | Census Bureau vintage, over districts created and merged under the Revised School Code (MCL 380) | **NOTHING TO REBUILD — both are LIVE TIGERweb.** The exposure here is the PAIR's completeness, not either layer's geometry: the two tile Michigan only because layer 1 (secondary) is empty and the 27 elementary districts fill exactly the gaps the 514 unified ones leave. A roll that introduces a secondary district, or that moves a district between tiers, would leave a hole no gate catches — the smoke test classifies pre-built anchors only, and both of these are live. Re-run the disjointness probe (each layer's features at the other's `INTPT*` interior points; `CENT*` reports false overlaps) and, if layer 1 stops measuring zero, the recorded drop in `docs/DATA_LAYER_GUIDEBOOK.md` becomes a layer to ship |
| Precinct | **Per election cycle, and the newest map moves HOSTS** | local election officials -> county/local GIS -> Bureau of Elections | geometry (`mi/scripts/build_mi_precincts.py` rebuild — exact 3,895/83 count guard, unique-key guard, the 1,530-key MCD join, a registered-voter sanity band, and an agreement gate that judges overlaps AGAINST THE SOURCE). **THE TRAP IS WHERE YOU LOOK, NOT WHAT YOU READ**: the `OpenData/boundaries` MapServer that carries the commissioner layer publishes a precinct layer per cycle and its newest is 2024, while the 2026 map lives on the state's ArcGIS Online org on a different host — and Michigan consolidated 4,340 precincts into 3,895 between them, so building from the MapServer yields a complete-looking file that is 445 precincts wrong. Run the org query (`arcgis.com/sharing/rest/search?q=owner:michigan_admin AND precinct`) BEFORE any MapServer layer list. Four items serve the 2026 map; the builder pins the curated one and gates on the one the state's own Election District Viewer wires reporting the same count |
| ZIP Code | TIGER-rolling; ZCTAs are redrawn each decennial census | Census Bureau (an areal approximation of USPS delivery routes, not a postal boundary) | **NOTHING TO REBUILD — live TIGERweb**, no builder and no `data/app` file, so a vintage roll reaches it on its own and no cache bump applies. The one thing a roll CAN break silently is the ENVELOPE contract: this layer is fetched by `MI_BBOX_ENVELOPE` (Esri's `{xmin,ymin,xmax,ymax}`) rather than `STATE='26'`, because ZCTAs carry no STATE field, and passing the instance's `{minLng,...}` `METRO_BBOX` instead yields HTTP 200 with a JSON error envelope and zero features rather than an error — `mi/scripts/validate_sources.py` watches the count so that failure surfaces |

MI's per-date calendar lives in `mi/WATCH.md`. Note the roster axis moves on a DIFFERENT clock from
the geometry here: commissioner terms went to FOUR years under PA 121-122 of 2021, so the boards
seated January 2025 run to December 2028 and the live risk is mid-term vacancies rather than an
election.

---

## The detection layer (executable NOW)

Extend `scripts/validate_sources.py`:
- Add a per-source `vintage` field to the manifest and an `expected_successor` watch. For TIGERweb
  CD layers: watch for the appearance of a CD121 layer name on the TIGERweb MapServer (the
  current live layer is the 120th, "120th Congressional Districts; January 1, 2026 vintage," field
  `CD120` — rolled from the 119th on 2026-09-03; a new Congress rolls both the layer name and the
  field, and the 119th is still served at `tigerWMS_ACS2025/MapServer/54` if a vintage diff is ever
  needed). For Socrata: the
  existing newer-edition catalog search already handles year-versioned ids (CPS attendance
  boundaries). For shapefile sources: monitor the per-layer provenance page listed in the manifest.
- Add a "redistricting-watch" section to the monthly tracking issue that validate_sources.py
  already opens/updates on WARN/FAIL. It must NOT edit anything — detection only.
- Monitoring sources (checklist, not a scraper): Census Redistricting Data Program pages; state
  redistricting commission sites; Loyola Law School "All About Redistricting"; Redistricting Data
  Hub; city clerk / districting-commission pages (Chicago Committee on Rules; NYC Districting
  Commission).

Adjacent platform risk to watch: Socrata is now Tyler "Data & Insights," and SODA3 is the new
default. The 2025 SODA iteration moves the query endpoint from `/resource/IDENTIFIER.json` to
`/api/v3/views/IDENTIFIER/query.json` and requires that "query requests must be either
authenticated by a user or marked with a valid application token"; SODA2 endpoints still run in
parallel. Keep SOCRATA_APP_TOKEN populated and add a manifest note per Socrata source so a future
SODA2 deprecation is caught by validate_sources rather than by a broken layer.

---

## The response procedure (numbered drill, per changed layer)

Policy decision, recorded: **show-current-until-effective.** New maps are usually enacted long
before they take effect; the app keeps showing CURRENT districts until the effective date, then
switches. Optionally show a banner "New maps take effect [date]." Rationale: users want to know who
represents them TODAY; showing not-yet-effective districts is a correctness bug, not a feature.

1. **Confirm enactment + effective date.** Cite the enacting instrument (ordinance / public act /
   court order). Record both dates. Do nothing to geometry until you have both.
2. **Acquire authoritative geometry**, in order of preference: (a) official shapefile from the
   enacting body; (b) city portal new dataset id; (c) TIGER/Line vintage. Never scrape a rendered
   map.
3. **Provenance intake.** Save the original into `il/data/source/raw/` with a name encoding layer +
   vintage + enactment citation (e.g. `chi_wards_2033_ordinance-O2033-XXXX.shp`).
4. **Full-precision conversion** into `il/data/` (GeoJSON).
5. **build_embedded_boundaries.py entry.** If the changed layer is an anchor, add/update its LAYERS
   entry (Visvalingam keep-shapes, per-layer simplify % + precision). All anchors must be
   registered — CHI currently registers only 1 of its 3 anchors in build_embedded_boundaries.py;
   this parallel fix must be complete before a redistricting event or the smoke test's offline
   classification is under-protected. Regeneration must still clear the built-in gate: ≥99.5%
   agreement on 2,000 seeded random points against the app's own even-odd point-in-polygon AND zero
   points classified into >1 district (topology break = hard fail), feature count/properties
   unchanged.
   - **Legislative layers are now pre-built too (R2-2, 2026-07).** The U.S. House / IL Senate / IL
     House GEOMETRY no longer queries TIGERweb live — it ships as `data/app/{congress,il-senate,il-house}-districts.json`,
     built by **`scripts/build_legislative_boundaries.py`**. This changes the drill for those layers:
     the builder fetches TIGERweb directly (`STATE='17'`) and simplifies, so steps 2–4 (shapefile
     intake / `data/` conversion) don't apply — the builder *is* the intake. On a redistricting or a
     TIGERweb vintage roll (CD120 → CD121, or a new "State Legislative Districts" layer — both have now
     been seen, and they behaved DIFFERENTLY. The CD roll (2026-09-03) RETIRED its field, so every
     builder naming CD119 broke. The SLD roll to 2026, measured the same day, changed only the layer
     NAME: indices 1/2 still serve upper/lower, SLDU/SLDL survived, and all 12 chambers across the
     fleet measured geometrically identical (~180,000 sampled points, 17 sub-metre disagreements) —
     so it needed no rebuild at all, only the vintage pin in ny/scripts/validate_sources.py. Check
     WHICH KIND a roll is before assuming a rebuild), update the
     `LAYERS` dict in `build_legislative_boundaries.py` (TIGERweb layer index, district field,
     `min_features`), re-run it (same ≥99.5% / zero-topology-break gate), and **update the
     `data_files.geometry` feature counts in `metro-worksheet.json`** so `validate_index.py` matches.
     Because the geometry is now static, a redistricting that once "just worked" via live TIGERweb now
     **requires this manual rebuild** — otherwise the app ships the old maps. (The officeholder rosters
     are unaffected — still weekly.)
6. **Regenerate data/app + bump sw.js CACHE_NAME.** Cached old geometry in users' service workers
   must be invalidated; a CACHE_NAME bump is the only thing that forces refetch. Respect the sw.js
   exactly-one-list invariant.
7. **Update ground-truth points + smoke assertions.** Protocol: re-classify the existing landmark
   points against the NEW geometry and update expected values; ADD a second point that changed
   districts across the remap as a regression sentinel (proves the new geometry is actually
   different, not stale). CHI's anchor triad is school-board district / IL Supreme Court / Board of
   Review at the Loop (41.8825, -87.6285); NYC's is borough=Manhattan at City Hall (40.71274,
   -74.00602) plus the mid-East-River negative point.
8. **LAYER_AREA_RANK re-check** — a remap can change relative area ordering.
9. **Roster join-key audit.** District numbers can be renumbered, not just redrawn — CHI's ERSB
   history already proved numbering schemes change (10 districts + lettered subdistricts, full
   21-member board seated Jan 2027). Verify the scraper/builder join keys still map officials to the
   right districts.
10. **validate_index floors update** — feature counts and roster counts may change (e.g. a new
    precinct raises NYC's 78-precinct count).
11. **Update validate_sources manifest vintage** to the new dataset id / vintage / provenance URL.
12. **Worksheet + regenerated docs.** Update the fork's metro-worksheet.json (layers, anchors,
    ground-truth, data_sources) and run `generate_metro_files.py` (MECHANIZATION_PLAYBOOK Conversion
    2). The `--check` gate fails until worksheet and code agree.
13. **Transition-period question.** Dual-map support (showing current and future maps
    simultaneously) is explicitly **OUT of scope.** Recorded decision: the app shows effective-today
    districts only; candidates/advocates wanting draft maps are pointed elsewhere. Override only on
    explicit user instruction.
14. **Update this runbook's appendix.** Update the appendix row for the changed layer
    (enactment/effective dates, publication venue) in the same PR — a runbook whose own tables go
    stale on first use has failed its purpose. Once MECHANIZATION_PLAYBOOK Conversion 2 is live,
    instead mark the appendix tables as GENERATED regions emitted from each fork's
    metro-worksheet.json (which step 12 already updated), making the worksheet the single source
    and this step automatic — from that point, hand-editing the appendix is a `--check` failure.

Every step lands via PR through the normal gates (validate_index static gate, smoke behavior gate,
engine parity assertion). Officeholder changes remain human-reviewed.

---

## The rehearsal schedule

- **Yearly live-fire:** the already-annual CPS attendance-boundary rotation (new SYxxyy dataset each
  school year — e.g. the SY2526 elementary/middle/high boundary datasets on the Chicago portal)
  exercises steps 2–6 and 10–11 at small scale against real machinery. Treat each SY rollover as the
  mandatory annual drill; if it is painful, the runbook is wrong and gets fixed then, not in 2031.
- **One tabletop drill** of the full 14-step procedure against a hypothetical ward remap before
  2030.
- **Calendar checkpoints:** 2029 Q4 — verify this runbook against current code. 2031 Q2 — P.L.
  94-171 lands; begin state-layer watch. Per-metro municipal watch windows open when each city's
  districting commission convenes.

---

## Roster-side effects

After a remap, incumbents map to new district numbers mid-term or at the next election. Scrapers
keyed on district number attribute correctly ONLY after official sources update their own district
assignments — there is a lag. The weekly-PR human-review pattern is the safety net (never
auto-commit officeholder data; force-push + `gh pr list` guard on a fixed bot branch). Add a
post-remap **roster sanity sweep**: spot-check 3 known officials' districts against news sources
before merging the roster PR that follows a remap.

---

## Appendix — per-metro quick tables

Maintenance rule (step 14): every executed response procedure updates its layer's row here in the
same PR; once Conversion 2 is live these tables become GENERATED regions sourced from each fork's
metro-worksheet.json and hand-edits fail `--check`.

### CHI — layer → authority → next-map source → last enactment/effective

| Layer | Enacting authority | Next map published at | Last enactment / effective |
|---|---|---|---|
| Wards (50) | Chicago City Council | Committee on Rules; city data portal (new dataset id) | Ordinance O2022-1318, approved May 16, 2022 (43–7); effective for the 2023 municipal elections (May 2023) |
| Cook County commissioner (17) | Cook County Board | Cook County GIS / clerk | Redistricting Ordinance approved Sep 23, 2021; commissioners nominated/elected under it in 2022 |
| IL Congress / Senate / House | IL General Assembly | ilga.gov; TIGER/Line | 2021 maps; effective 2022 |
| IL Supreme Court districts | IL General Assembly | ilga.gov | PA 102-0011, effective Jan 1, 2022 — first redraw since 1964; may not change in 2031 |
| Cook County Board of Review | statute | ilga.gov | PA 102-0012 (Board of Review Redistricting) |
| ERSB school board | IL statute (SB15) | ilsenateredistricting.com / city | 10 districts (20 subdistricts) for the 2024 election; full 21-member elected board seated Jan 2027 |
| Chicago police districts (22) | CPD | chicagopolice.org | Administrative; changes rarely, not census-tied |
| CPS attendance boundaries | CPS | Chicago data portal (SYxxyy dataset id) | New dataset every school year (e.g. SY2526) |

### NYC — layer → authority → next-map source → last enactment/effective

| Layer | Enacting authority | Next map published at | Last enactment / effective |
|---|---|---|---|
| City Council (51) | NYC Districting Commission | nyc.gov/site/districting | Commission map sent to Council late 2022; effective Feb 2023 for the 2023 elections; next ~2032–2033 |
| US Congress (NY) | Legislature / IRC / courts | Legislature; TIGER/Line | Enacted Feb 28, 2024 (after the 2022 special-master map); volatile — three maps in three years |
| NY Senate / Assembly | Legislature / IRC | IRC; TIGER/Line | Senate: 2022 special-master map. Assembly: redrawn, signed Apr 24, 2023, effective 2024 |
| NYPD precincts (78) | NYPD | nyc.gov | 116th Precinct opened Dec 18, 2024 (Rosedale, SE Queens), carved from the 105th/113th — first new precinct since 2013 |
| Community districts | NYC charter | nyc.gov | Rarely change |
| School zones | DOE | DOE / open data | Annual |

### SF — layer → authority → next-map source → last enactment/effective

| Layer | Enacting authority | Next map published at | Last enactment / effective |
|---|---|---|---|
| Supervisor districts (11) | SF Redistricting Task Force | DataSF (successor to `hcgx-vtsb`) | April 2022 map; next task force ~2032 |
| Election precincts | SF Dept. of Elections | DataSF (successor to `jg6x-23ig`, "Defined <year>") | 2022 precinct map; redraws with the supervisor cycle |
| CA Congress / Senate / Assembly | CA Citizens Redistricting Commission | wedrawthelines.ca.gov; TIGER/Line | 2021 maps, effective 2022; watch Prop 50-style mid-decade changes |
| BART Director districts (9) | BART Board | bart.gov / BART ArcGIS | 2022 Plan E2; holds "until the next round following the 2030 US Census" |
| SFPD districts (10) | SFPD | DataSF (successor to `d4vc-q76h`) | Last major realignment 2015 |
| SFUSD attendance areas | SFUSD | DataSF (new `…(20xx-20xx)` dataset id) | New dataset every school year |

Cross-reference: when any of these changes, execute the 14-step response procedure above and update
the fork's metro-worksheet.json so MECHANIZATION_PLAYBOOK Conversion 2's `--check` gate and
Conversion 3's fleet-status stay green.

### WI — layer → authority → next-map source → last enactment/effective

| Layer | Enacting authority | Next map published at | Last enactment / effective |
|---|---|---|---|
| US Congress (WI, 8) | WI Legislature | TIGERweb Legislative layer 0 | 2022 map (SCOWIS-selected, Johnson v. WEC), effective 2022 |
| WI Senate (33) / Assembly (99) | WI Legislature (2024 remap signed after Clarke v. WEC) | TIGERweb Legislative layers 1/2 | 2024 maps, effective the 2024 general — a MID-DECADE change; watch for more |
| County subdivisions / places / school districts | Census Bureau (TIGER vintage) | TIGERweb (live layers self-update) | rolling |

