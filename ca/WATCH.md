# WATCH.md — redistricting watch calendar (San Francisco)

The one place the dates live. `docs/REDISTRICTING_RUNBOOK.md` (master in the Chicago repo;
pointer stub here) is *what to do* when a boundary changes; this file is *when to look*.
Keep it at repo root so it's the first thing seen. Update the "Last done" column each time
you complete a row — a checkpoint with a stale date is a checkpoint that didn't happen.

Rule of thumb: **detection runs itself monthly; you run the SFUSD drill yearly; you open
the runbook per-layer whenever a map is enacted.** Everything below is just those three
habits pinned to dates so a trigger never catches you cold.

---

## Standing (already automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| Monthly (1st, 14:00 UTC) | Source-freshness + redistricting-watch scan | `.github/workflows/validate-sources.yml` → single tracking issue on WARN/FAIL | Glance at the issue when it updates. A WARN = a trigger below may have fired. |

---

## Yearly — the SFUSD drill (the load-bearing habit)

| When | What | Runbook steps | Last done |
|---|---|---|---|
| Late summer, when SFUSD's new school-year attendance-area dataset posts | The attendance areas are republished each school year under a **brand-new dataset id** (in use: `e6tr-sxwg`, "…(2024-2025)"); `validate_sources.py`'s year-search WARNs when a newer edition appears. Execute the response procedure against the rotated dataset as a live rehearsal. | Steps 2–6, 10–11 | _(never — first cycle is summer 2026)_ |

This is the only time the machinery gets exercised before it matters. If the drill is
painful, fix the runbook **that year**, not during the 2031 census scramble.

---

## Per-election — voting center & drop-box refresh

| When | What | Last done |
|---|---|---|
| ~1 month before each election, when sf.gov posts the election's drop-box / voting-center locations | Refresh `data/app/early-voting-sites.json` (hand-transcribe the official list from sf.gov/return-your-ballot + the Voter Information Pamphlet, geocode, verify pins against the Department's own locations map), update the election name in the `early-voting` layer's `intro` in `index.html`, update the `source_url` in `scripts/validate_sources.py` PROVENANCE if the page moved, and bump `sw.cache_name` in `metro-worksheet.json` + regenerate | 2026-07 (initial — June 2026 primary list; the Department describes the 37 drop boxes in recurring terms) |

The layer's honesty depends on this row: the card **intro** names the election the shipped
list was published for, so a stale file is visibly stale rather than silently wrong — but
refresh it anyway (each feature also carries an `election` property for provenance; it is
not rendered). The transcription is manual (no open point dataset exists on DataSF —
re-check the catalog each cycle in case that changes).

---

## Per-file re-checks — the boundary files no job rewrites

`docs/EAM_STATUS.md` measures whether every data file the app reads is under a
stated plan, and on 2026-10-01 **seven of San Francisco's fourteen were under
none.** Six are boundary geometry and one is the gap record; not one of them
names a person, so no officeholder was going stale. Geometry is exactly the
case a weekly job cannot serve — a scraper run every Tuesday against a city
boundary that has not moved since 1856 is a guaranteed no-op — and the honest
alternative is a stated cadence here.

Each row names its own files so the instrument can see them. The checkpoint
rows below state the same triggers in prose and name no file, which is why
these exist beside them rather than instead of them.

| Cadence | Files | Why this clock | Last done |
|---|---|---|---|
| **Annually**, when TIGERweb publishes a new legislative vintage | `congress-districts.json` | *Decennial + court/mid-decade.* The annual vintage roll is the only detector this file has, and it is not theoretical: the 119th→120th roll in 2026 carried a real statewide California remap (Prop 50), which the SF clip happened to survive unchanged. The decennial response is the 2031–2032 checkpoint below | 2026-09-03 (rebuilt on CD120; SF's six districts identical in both vintages) |
| **Annually**, on the same TIGERweb vintage roll | `ca-senate-districts.json`, `ca-assembly-districts.json` | *Decennial.* Same source and same roll as the row above, split from it because the 2026 roll re-read Congress and did not re-read these two — one row would have claimed a verification that did not happen | **_(never)_** |
| **Annually**, on the same TIGERweb vintage roll | `san-francisco-county-outline.json` | *Almost-never.* The city and county boundary is consolidated and has not moved since 1856; TIGER re-publishing it is the only thing that can change these bytes. A year is the shortest cadence that is not a pretence | **_(never)_** |
| **Annually** | `police-districts.json` | *Administrative, rare.* SFPD redraws its districts by departmental decision, last in 2015, so there is no date to anchor to. The monthly source scan probes the DataSF dataset for reachability and a rename; it cannot see the boundary itself move under the same dataset id, which is what this re-read is for | **_(never)_** |
| **Annually** | `sf-neighborhoods.json` | *Administrative, rare.* The city's 41 analysis neighborhoods are maintained by Planning and revised on no schedule. Same gap as the row above: the dataset id is watched, the geometry inside it is not | **_(never)_** |
| **Annually** | `coverage-gaps.json` | The one file here with no upstream: its source is the guidebook's own gaps block, and `build_coverage_gaps.py --check` re-emits and compares on every pull request, so file-versus-record drift is already impossible. The cadence is for the RECORD — a gap can go stale in the direction nothing detects, which is a blocker quietly lifting with no one re-reading it | **_(never)_** |

**A `--check` PROVES A FILE MATCHES ITS INPUTS AND NEVER THAT THE INPUTS ARE
CURRENT**, which is why the gap record is in the table rather than excused by
it.

---

## Fixed checkpoints (put these on a real calendar)

| Date | Trigger | Action | Done |
|---|---|---|---|
| **2029 Q4** | Pre-cycle dry read | Re-read the redistricting runbook against current code; confirm the per-layer inventory still matches reality. Catches drift while it's calm. | ☐ |
| **2031 Q2** | P.L. 94-171 redistricting data delivered to states (statutory deadline ~Apr 1 2031; the 2020 cycle slipped — don't assume) | Begin active watch on congressional + state-legislative layers. | ☐ |
| **2031–2032** | CA Citizens Redistricting Commission adopts new maps (congressional / senate / assembly), effective 2032 elections | Per-layer response for `congress` / `ca-senate` / `ca-assembly` — all three are **pre-built SF-clipped geometry** (`build_legislative_boundaries.py` from TIGERweb), so the work is a rebuild + anchor re-verify, staged on enactment, shipped at effectiveness. | ☐ |
| **2032** | SF Redistricting Task Force redraws Supervisor districts (charter: within ~9 months of census data; last map April 2022) | `supervisor-district` is an **offline anchor + roster layer**: rebuild `supervisor-districts.json` from the successor DataSF dataset, re-verify the City Hall / Ferry Building ground-truth anchors, confirm the roster builder still joins. The **election-precinct map redraws on the same cycle** — expect a successor to `jg6x-23ig` with a new "Defined <year>" title (`validate_sources`' year-search watches for it). | ☐ |
| **Nov 2026, then every even-year November** | BART Director elections (staggered 4-year terms; SF districts on the ballot: **7 & 8 in 2026**, 9 in 2028) | Re-verify `data/app/bart-directors.json` against bart.gov/about/bod (names, board roles, member URLs); bump `sw.cache_name` + regenerate. | ☐ |
| **2031–2032** | BART redistricting (the 2022 Plan E2 map holds "until the next round following the 2030 US Census") | Rebuild/re-verify the `bart-director` geometry against BART's updated ArcGIS service; re-confirm which districts cover SF. | ☐ |
| Rolling, post-enactment | Census TIGERweb publishes the new CD vintage | **DONE 2026-09-03 — and California actually REDISTRICTED in this roll.** The 119th→120th vintages disagree statewide on 34% of sampled points, whole regions flipping (e.g. Redding: district 1 → 2). The SF clip is NOT affected: its six districts {2,8,11,12,15,16} are identical in both vintages and 18,549 in-window points produced 2 disagreements, both in open water. Rebuilt on CD120. **A future CA instance serving beyond SF must treat this as a real remap, not a rename.** | ☑ |
| Per-body, ad hoc | A commission convenes to redraw any mapped body | Open that layer's watch window; expect an enactment within the session. | ☐ |

---

## Off-cycle triggers (no date — stay alert)

Redistricting is **not** only decennial. Any of these fires the per-layer response
procedure immediately:

- **Court order** — very common 2022–2024 (NY, AL, LA, GA congressional maps).
- **Mid-decade partisan redraw** — the 2025–2026 wave is the live example, and it includes
  **California (Prop 50)**: if the CA congressional map changes mid-decade, `congress`
  rebuilds here on the same staged-enactment rule.
- **Administrative safety reorg** — SFPD redraws district boundaries administratively
  (last major realignment 2015). `police-district` is a **pre-built offline anchor**
  (`d4vc-q76h`): rebuild the file, re-verify the Tenderloin/NORTHERN anchor expectations.
- **Annual school-zone rotation** — the SFUSD drill above is the scheduled instance.

When one fires: confirm enactment + effective date, then work **one layer at a time**
through the runbook. Don't touch layers that didn't change.

---

## Per-metro note

**This file is SF's.** Each sibling fork carries its own `WATCH.md` with its own bodies
and enactment history (Chicago: wards/ERSB/CPS + collar counties; NYC: Districting
Commission, BOE election districts, NYPD precinct reorgs). The decennial and off-cycle
framing is shared; the layer rows are per-city.
