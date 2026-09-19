# WATCH.md — redistricting watch calendar (New York)

The one place the dates live. `docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a
boundary changes; this file is *when to look*. It sits at `ny/`, beside the instance it
describes. Update the "Last done" column each time you complete a row — a checkpoint with
a stale date is a checkpoint that didn't happen.

Rule of thumb: **detection runs itself monthly; you run the school-zone drill yearly; you
open the runbook per-layer whenever a map is enacted.** New York adds one twist the other
instances do not have: its congressional map is the most litigated in the fleet (three
maps in three years, 2022–2024), so the off-cycle triggers below are not hypothetical
here.

**Corrected at the 2026-09-19 go-live**, where this file had gone stale in three ways at
once. It called the runbook a "master in the Chicago repo; pointer stub here" and told the
reader to keep this file "at repo root" — both true of the per-metro FORKS, which were
retired at R2.1; there is one repository now and this file has never been at its root. And
the instance it describes is no longer New York City: since 2026-09-18 fifteen of its
thirty-three layers answer anywhere in the state.

---

## Standing (already automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| Monthly (1st, 12:00 UTC) | Source-freshness + redistricting-watch scan | `.github/workflows/validate-sources.yml` → single tracking issue on WARN/FAIL | Glance at the issue when it updates. A WARN = a trigger below may have fired. |
| Weekly (staggered Mon–Thu) | Roster refreshes (legislature, congress, NYPD, CEC, council) | `update-*-roster.yml` → PR for human review on change | Review + merge the roster PRs. |

---

## Yearly — the school-zone drill (the load-bearing habit)

| When | What | Runbook steps | Last done |
|---|---|---|---|
| Late summer, when DOE posts the new school year's zone datasets | The ES/MS/HS zone datasets are **year-versioned Socrata ids** (in use: `cmjf-yawu` / `t26j-jbq7` / `ruu9-egea`); `validate_sources.py`'s year-search WARNs when a newer edition appears. Execute the response procedure against the rotated datasets as a live rehearsal. | Steps 2–6, 10–11 | _(never — first cycle is summer 2026)_ |

This is the only time the machinery gets exercised before it matters. If the drill is
painful, fix the runbook **that year**, not during the 2031 census scramble.

---

## Per-election — early-voting note (no transcription needed here)

Unlike Chicago and SF, NYC's `early-voting` layer queries the **live NYS GIS elections
service** — there is no hand-curated file to refresh per election. The watch item is the
*service* itself: if the monthly endpoint check WARNs, or the layer's card comes back
empty during an election period, check whether NYS ITS moved or renamed the service.

---

## Fixed checkpoints (put these on a real calendar)

| Date | Trigger | Action | Done |
|---|---|---|---|
| **2029 Q4** | Pre-cycle dry read | Re-read the redistricting runbook against current code; confirm the per-layer inventory still matches reality. Catches drift while it's calm. | ☐ |
| **2031 Q2** | P.L. 94-171 redistricting data delivered to states (statutory deadline ~Apr 1 2031; the 2020 cycle slipped — don't assume) | Begin active watch on congressional + state-legislative layers. | ☐ |
| **2031–2032** | NY IRC / Legislature adopts new congressional + state maps, effective 2032 elections | Per-layer response for `congress` / `state-senate` / `state-assembly` — all three are **pre-built geometry from TIGERweb**, so the work is a rebuild + anchor re-verify + roster-join re-check, staged on enactment, shipped at effectiveness. Expect litigation: the 2022 maps were struck and special-mastered; watch the courts, not just the IRC. | ☐ |
| **2032–2033** | NYC Districting Commission redraws City Council districts (last map effective Feb 2023 for the 2023 elections) | `council` is a **Socrata + weekly-roster layer**: watch for the successor dataset id to `872g-cjhh`, rebuild, re-verify anchors, confirm the roster builder still joins. | ☐ |
| **Post-council-redraw** | BOE re-cuts election districts to the new lines | `election-district` (~4,200 EDs, subOf `state-assembly`) redraws **frequently** even off-cycle — BOE re-districts around every major boundary change. The DCP ArcGIS service is versioned; re-verify after any council/state redraw. | ☐ |
| Rolling, post-enactment | Census TIGERweb publishes the new CD vintage (CD119 field → CD120) | **DONE 2026-09-03.** The watch worked — `ny/scripts/validate_sources.py` FAILed on the layer-name mismatch, which is what it was built for. Rebuilt on CD120 (26 districts, geometry unchanged — 5,000 points, 0 disagreements) and the manifest now expects the 120th and watches for the 121st. | ☑ |
| Ad hoc | NYPD opens/merges precincts (administrative — the 116th Precinct opened Dec 2024, the first since 2013) | Rebuild `police-precinct`/`police-sector` geometry, re-verify anchors, confirm the commander scraper covers the new precinct page. | ☐ |
| Ad hoc | DOE redraws Community School District lines (rare) or CEC structure changes | Re-verify `school-district` + `cec` (they share geometry). | ☐ |

---

## Off-cycle triggers (no date — stay alert; NYC is the fleet's cautionary example)

- **Court order** — NY congressional: 2022 legislature map struck (*Harkenrider v. Hochul*),
  replaced by special-master lines; *Hoffmann v. NYIRC* then forced the Feb 2024 redraw.
  Three maps in three years. Any active NY redistricting litigation = open the watch window.
- **Mid-decade partisan redraw** — the 2025–2026 national wave; NY's constitution limits
  it but litigation keeps finding paths. Same staged-enactment rule as everywhere.
- **Administrative safety reorg** — NYPD precinct changes (above) are not census-tied.
- **Annual school-zone rotation** — the drill above is the scheduled instance.
- **Charter revision** — a Charter Revision Commission can touch community-district or
  borough-office structure; if one convenes, read its proposals against the layer list.

When one fires: confirm enactment + effective date, then work **one layer at a time**
through the runbook. Don't touch layers that didn't change.

---

## Per-metro note

**This file is New York's.** Each instance in this repository carries its own `WATCH.md`
with its own bodies and enactment history (Illinois: wards/ERSB/CPS plus the collar
counties; San Francisco: Redistricting Task Force, election precincts, BART, SFUSD). The
decennial and off-cycle framing is shared; the layer rows are per-instance.

**The statewide tier is not yet in the rows below, and that is the open item.** PR 2
shipped the county, municipality, village, school-district and judicial-district layers on
2026-09-18; the go-live added their freshness entries to
`ny/scripts/validate_sources.py`, which is what notices a service that moves. What is
missing here is the other half — when to LOOK for a redraw of the bodies those layers
draw. County and municipal boundaries change by annexation rather than on a cycle, so the
row is not simply decennial, and writing it needs a decision about what triggers a check.
