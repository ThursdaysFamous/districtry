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
| Late summer, when the new `SYxxyy` CPS attendance datasets post | Execute the response procedure against the rotated school-zone datasets as a live rehearsal | Steps 2–6, 10–11 | **2026-09-03 — detection half only; see below** |

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

## Fixed checkpoints (put these on a real calendar)

| Date | Trigger | Action | Done |
|---|---|---|---|
| **2029 Q4** | Pre-cycle dry read | Re-read `docs/REDISTRICTING_RUNBOOK.md` against current code; confirm the per-layer inventory and appendix still match reality. Catches drift while it's calm. | ☐ |
| **2031 Q2** | P.L. 94-171 redistricting data delivered to states (statutory deadline ~Apr 1 2031; the 2020 cycle slipped to Aug/Sep — don't assume) | Begin active watch on congressional + state-legislative layers in every metro. State map-drawing starts now. | ☐ |
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
