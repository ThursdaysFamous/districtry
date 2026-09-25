# WATCH.md — redistricting watch calendar

The one place the dates live. `docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a
boundary changes; this file is *when to look*. Keep it at repo root so it's the first thing
seen. Update the "Last done" column each time you complete a row — a checkpoint with a stale
date is a checkpoint that didn't happen.

Rule of thumb: **detection runs itself monthly; you run the CPS drill yearly; you open the
runbook per-layer whenever a map is enacted.** Everything below is just those three habits
pinned to dates so a trigger never catches you cold.

---

## Standing (already automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| Monthly (1st, 14:00 UTC) | Source-freshness + redistricting-watch scan | `.github/workflows/validate-sources.yml` → single tracking issue on WARN/FAIL | Glance at the issue when it updates. A WARN = a trigger below may have fired. |

If that workflow isn't live yet, that's the prerequisite — see the runbook's "detection
layer" section. Until it runs, you're watching by hand, which is the failure mode.

---

## Yearly — the CPS drill (the load-bearing habit)

| When | What | Runbook steps | Last done |
|---|---|---|---|
| **Late August to early October**, when the new `SYxxyy` CPS attendance datasets post — the span this file's own edition table records (24 August to 3 October across four observed publications), never a single month | Execute the response procedure against the rotated school-zone datasets as a live rehearsal | Steps 2–6, 10–11 | **2026-09-03 — detection half only; see below** |

**2026-09-03 — the first time this row was ever exercised, and it half-ran, which
is worth stating plainly.** The DETECTION half ran end to end against the live
portal: all three pinned attendance-boundary datasets resolve and are current at
**SY2526** (`x72b-38qv` elementary, `xg7c-d8rm` high, `fyff-53xy` middle), and a
catalog sweep found **zero SY2627 datasets anywhere on data.cityofchicago.org**.
So the monthly scan's silence on 2026-09-01 was a real negative, not a missed
rotation — which is the thing this drill exists to confirm.

The RESPONSE half (runbook steps 2–6, 10–11) could not be rehearsed, because
nothing has rotated. Recording that rather than stamping the row done: a drill
that never swapped an id has not exercised the machinery it is for.

**The window is open now.** CPS has published this layer every year since
SY0607, between late August and early October:

| Edition | Elementary dataset | Published |
|---|---|---|
| SY2526 | `x72b-38qv` | 2025-09-02 |
| SY2425 | `im2a-is7h` | 2024-09-20 |
| SY2324 | `njaf-gekg` | 2023-08-24 |
| SY2223 | `w9ky-kbav` | 2022-10-03 |

SY2526 posted a year and a day before this check, so SY2627 is due imminently.
Until it lands the app is serving SY2526 — CPS's own current edition, so the
cards are right — but the moment SY2627 appears the shipped ids are last year's
boundaries, silently, because a retired Socrata id keeps answering. Re-run this
row when the monthly `validate-sources` issue reports a newer edition, and take
the drill the rest of the way then.

This is the only time the machinery gets exercised before it matters. If the drill is
painful, fix the runbook **that year**, not during the 2031 census scramble. A repo that has
run this three times will handle the decennial cycle; one that has only read the runbook
won't. Record the run in the runbook's drill-evidence habit and stamp the date above.

---

## Per-election — early-voting sites refresh

| When | What | Last done |
|---|---|---|
| ~1 month before each election, when chicagoelections.gov posts the voting-locations list | Refresh `data/app/early-voting-sites.json` (hand-transcribe the official list, geocode, verify pins), update the election name in the `early-voting` layer's `intro` in `index.html`, update the `source_url` in `scripts/validate_sources.py` PROVENANCE if the page moved, and bump `sw.cache_name` in `metro-worksheet.json` + regenerate | 2026-07 (initial) |

The layer's honesty depends on this row: the card names the election the sites belong to, so
a stale file is visibly stale rather than silently wrong — but refresh it anyway. The site
403s non-browser clients, so the monthly source scan can only WARN on reachability; the
transcription itself is manual (Playwright or by hand).

---

## Per-class re-checks — the boundary files no job rewrites

`docs/EAM_STATUS.md` measures whether every data file the app reads is under a
stated plan, and on 2026-09-25 **305 of Illinois's 397 were under none.** Almost
all of them are boundary geometry, which is exactly the case a weekly job cannot
serve: a scraper run every Tuesday against a county outline that moves once a
decade is a guaranteed no-op, and the honest alternative is a stated cadence
here. So these rows are the plan for whole CLASSES of file rather than for
files one at a time — a row may name its class as a glob in backticks
(`*-<suffix>.json`), which the instrument reads, because writing out 101
filenames would be 101 lines restating one fact.

**Every clock below is the exposure class `docs/REDISTRICTING_RUNBOOK.md`
already assigns that layer family**, quoted in the third column and not
re-reasoned here. That file is what to DO when one of these moves; this is when
to look.

| Cadence | Class | The runbook's exposure class | Last done |
|---|---|---|---|
| **Annually**, when TIGERweb publishes a new county vintage | `*-county-outline.json` (101) · `*-city-outline.json` (1) | *County / township / municipality (statewide): annexation-driven, rolling; TIGERweb vintages* | **_(never)_** |
| **Annually** | `*-library-districts.json` (79) · `*-fire-districts.json` (9) · `*-park-districts.json` (8) | *Administrative / per-election* — a special district's boundary moves by annexation, which can happen in any month and rarely does | **_(never)_** |
| **Each decennial census** — and a mid-decade consolidation is **NOT DETECTED**, see below | `*-precincts.json` (46) | *precincts redraw with county maps* | **_(never)_** |
| **The year after each decennial census** (55 ILCS 5/2-3003) | `*-county-board-districts.json` (35), plus `mcdonough-board-districts.json` and `menard-commissioner-districts.json`, which are the same thing under the name each county elects | *Decennial-municipal* — each county's own board redraws | **_(never)_** |
| **Each decennial census**, and on a court-ordered or mid-decade redraw | `congress-districts.json`, `il-senate-districts.json`, `il-house-districts.json` | *Decennial + court/mid-decade* for Congress, *Decennial* for the two chambers — the IL General Assembly draws all three. **The procedure is the 2031 Q2 and 2031–2032 checkpoints below**, which this row names rather than restates; it exists so the instrument can see that those three files have a plan, because a checkpoint row states its trigger in prose and names no file | **_(never)_** |
| **Each decennial** cycle, and no more often | `il-supreme-court-districts.json`, `ccbr-districts.json`, `school-board-districts.json` | *Almost-never* — the Supreme Court districts and the Board of Review tiling are set by statute and have not moved in decades; Chicago's elected school board is *New + volatile* and its 20 seats were drawn once, for 2024 | **_(never)_** |
| **Each decennial** redistricting cycle | `*-subcircuits.json` (5) | *Statutory, rare* — the IL General Assembly draws them | **_(never)_** |
| **Each March and each November**, before the primary and the general | `*-precinct-polling.json` (6: Carroll, Hamilton, Logan, Montgomery, St. Clair, Whiteside) | *per-election* — a polling place moves for one election and back | **_(never)_** |
| **Annually** | `dekalb-precinct-townships.json`, `municipal-ward-coverage.json` | Neither has a `--check`: `build_municipal_ward_coverage.py` has no check flag and nothing builds the DeKalb file at all, so a re-read is the only guard they have | **_(never)_** |
| **Annually** | `macon-board-district-labels.json` | `build_macon_board_district_labels.py --check` EXISTS and runs in no workflow — measured 2026-09-25, zero occurrences in `smoke-test.yml`. Wiring it in retires this row | **_(never)_** |

| **Annually**, on the same TIGERweb vintage roll as the county outlines | `metro-outline.json`, `il-state-outline.json` | Both are dissolves of the same county fabric. `build_metro_outline.py --check` does NOT rebuild them — that needs TIGERweb — it compares the shipped ring against its own anchor registry, so it catches a county added without an anchor and would not notice TIGER redrawing a county line | **_(never)_** |
| **Annually** | `il-county-board-offices.json` | Its inputs are ISBE's County Officers Book and the counties' Annual Financial Reports, both annual publications. `--check` verifies the file matches a fresh build from the committed copies of those, which is a different question from whether the copies are current | **_(never)_** |
| **Annually** | `coverage-gaps.json` | The one file here with no upstream: its source is the guidebook's own gaps block, and `build_coverage_gaps.py --check` re-emits and compares on every pull request, so file-vs-record drift is already impossible. The cadence is for the RECORD — a gap can go stale in the direction nothing detects, which is how Cass, Greene, Scott and Moultrie sat served with no precinct layer and no record saying so | **_(never)_** |

**A `--check` PROVES A FILE MATCHES ITS INPUTS AND NEVER THAT THE INPUTS ARE
CURRENT**, which is why all four of those are in the table rather than excused by
it. That was measured rather than assumed, and it corrected the first draft of
this section: `build_coverage_gaps.py --check` re-emits and compares,
`build_county_board_offices.py --check` verifies against a fresh build, and
`build_metro_outline.py --check` does neither — it reads the anchor registry.
Three different guarantees, none of them upstream.

### The precinct row's missing detector

Thirty-eight of Illinois's 46 shipped precinct layers are a Census 2020
snapshot, and until 2026-09-25 the tripwire for a county re-precincting was
`scripts/isbe_precinct_fabric.py`, reading ISBE's directory of all 102 election
authorities. **ISBE's robots.txt refuses this project** — 29 bytes of
`User-agent: * / Disallow: /`, read as a permission for over a year because of a
byte-order mark — so that route is closed and nothing replaces it at full
coverage. What remains is the three results vendors, which carry 34, 13 and 17
counties and can be swept for a precinct-name change; that is a smaller
tripwire, not an equal one, and it is not built. **So this row is a calendar
entry standing in for a detector**, which is the weakest plan in this file and
is recorded as such rather than dressed up.

---

## Fixed checkpoints (put these on a real calendar)

| Date | Trigger | Action | Done |
|---|---|---|---|
| **2029 Q4** | Pre-cycle dry read | Re-read `docs/REDISTRICTING_RUNBOOK.md` against current code; confirm the per-layer inventory and appendix still match reality. Catches drift while it's calm. | ☐ |
| **2031 Q2** | P.L. 94-171 redistricting data delivered to states (statutory deadline ~Apr 1 2031; the 2020 cycle slipped to Aug/Sep — don't assume) | Begin active watch on congressional + state-legislative layers in every metro. State map-drawing starts now. | ☐ |
| **2031**, when TIGERweb publishes 2030 census blocks | The block populations (`il/data/app/population/`) are Census 2020 and the one dataset here that cannot change until then | Point `scripts/build_block_population.py` at the 2030 block and tract layers, set `STATE_TOTAL` to the 2030 count, rebuild. `--check` forces it: it holds each shipped congressional and legislative map to its equal-population ideal on these blocks, so the first map drawn on 2030 blocks FAILS against 2020 people until this row is done — rebuild the population first, then the maps. | ☐ |
| **2031–2032** | State maps enacted, effective 2032 elections | Per-layer response procedure for Congress / IL Senate / IL House as each is enacted. Enacted ≠ effective — do the geometry work on enactment, keep showing current districts until the effective date. | ☐ |
| **2032–2033** | Municipal remaps | Response procedure for wards, commissioner, ERSB as each city body redraws. | ☐ |
| Same day as any boundary rebuild above | The district-name search index (`il/data/app/district-search.json`, "33rd ward") holds one point and extent per district of wards, police districts, school board, Congress, IL Senate, IL House, IL Supreme Court, Board of Review and every indexed county's board — and, BY NAME, every statewide school district and every CPS attendance zone | Run `python3 scripts/build_district_search.py` (network + shapely + playwright: the county board is read through the app) and commit the result with the rebuild. CI's `--check` fails on its own for the six layers whose boundaries ship in `il/data/app`, but it CANNOT see a redrawn ward, police or county-board map, which the app loads live — for those this row is the only reminder. A county that JOINS the county-board layer is printed by `--check` as not yet searchable until the builder is re-run. The school layers need no calendar of their own: CPS re-publishes its zones under a NEW dataset id each school year and Census rolls TIGER each vintage, and in both cases `--check` FAILS the day `il/index.html` loads the new source, because the index records which one it was built from. A district renamed in place (same id, new name) is not caught — rebuild after a TIGER roll even when `--check` is green. | ☐ |
| Rolling, post-enactment | Census TIGERweb publishes the new CD vintage | **DONE 2026-09-03 — the roll happened and it was CD119→CD120, not CD121.** The retired field is REMOVED, not deprecated: a query naming CD119 answers HTTP 200 carrying `{"error":{"code":400}}` with no features key, so the builder dies as "no features" and a status-code check reads success. `scripts/build_legislative_boundaries.py` names CD120 and the file was rebuilt (18 features, geometry unchanged — 3,667 sampled points, 0 disagreements). Next watch: CD120→CD121. | ☑ |
| Per-body, ad hoc | A districting commission / city council convenes to redraw | Open that layer's watch window; expect an enactment within the session. | ☐ |

---

## Off-cycle triggers (no date — stay alert)

Redistricting is **not** only decennial. Any of these fires the per-layer response procedure
immediately, regardless of where we are in the ten-year cycle:

- **Court order** — very common 2022–2024 (NY, AL, LA, GA congressional maps). NY had three
  congressional maps in three years.
- **Mid-decade partisan redraw** — the 2025–2026 wave (CA Prop 50, TX, OH, and others). If a
  state we cover joins it, act.
- **Administrative safety-layer reorg** — e.g. NYC's 116th Precinct (opened Dec 2024, carved
  from the 105th/113th). Police/fire districts change with no census.
- **Annual school-zone rotation** — the CPS drill above is the scheduled instance; NYC school
  zones rotate similarly.

When one fires: confirm enactment + effective date, then work **one layer at a time** through
`docs/REDISTRICTING_RUNBOOK.md` steps 1–14. Don't touch layers that didn't change.

---

## Per-metro note

This file is CHI's. Each sibling fork carries its own `WATCH.md` with its own municipal
bodies and enactment history (NYC: Districting Commission ~2032–2033, BOE election districts
which rotate frequently, NYPD precinct reorgs). The decennial and off-cycle framing is shared;
the layer rows are per-city. When Conversion 2 (generated docs) is live, the per-metro layer
rows can be emitted from each fork's `metro-worksheet.json` — until then, hand-maintained,
and this note is the reminder.
