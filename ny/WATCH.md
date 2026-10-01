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
thirty-four layers answer anywhere in the state.

---

## Standing (already automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| Monthly (1st, 12:00 UTC) | Source-freshness + redistricting-watch scan | `.github/workflows/ny-validate-sources.yml` → single tracking issue on WARN/FAIL. **Corrected 2026-10-01**: this cell named the root `validate-sources.yml`, which runs Illinois's scan and reaches no other instance; New York has its own job on its own cron, and the per-class table below is the first thing that depended on knowing which | Glance at the issue when it updates. A WARN = a trigger below may have fired. |
| Weekly (staggered Mon–Thu) | Roster refreshes (legislature, congress, NYPD, CEC, council) | `update-*-roster.yml` → PR for human review on change | Review + merge the roster PRs. |
| Monthly (rides the scan above) | **Statewide tier tripwire** — feature count on all four NYS services, plus the publisher's own "Publication Date" on the three Civil Boundaries layers | `ny/scripts/validate_sources.py` → same tracking issue | Nothing routine. A WARN here means a village dissolved, a town line moved or a district merged — work the matching trigger below. |

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

## Per-class re-checks — the boundary files no job rewrites

`docs/EAM_STATUS.md` measures whether every data file the app reads is under a
stated plan, and on 2026-10-01 **21 of New York's 29 were under none** — 20 of
them boundary geometry and the twenty-first a restatement of this project's own
gap records. Not one names a person: every roster this instance ships is
rewritten weekly by a job, so no officeholder here is going stale. Geometry is
the case a weekly job cannot serve — a scraper run every Tuesday against a
borough outline that has not moved since 1898 is a guaranteed no-op — so the
honest alternative is a stated cadence here.

**Where the runbook already assigns the layer family an exposure class, that
class is quoted in the third column and not re-reasoned.**
`docs/REDISTRICTING_RUNBOOK.md` is what to DO when one of these moves; this is
when to look. Where it assigns none, the row says so rather than borrowing a
neighbour's.

**Most of these already have a publisher-side detector and what they lacked was
a row naming them.** `ny/scripts/validate_sources.py` carries a manifest entry
for fifteen of the twenty-one, read monthly by `ny-validate-sources.yml` — New
York's own source-freshness job, on its own cron, not the root
`validate-sources.yml`, which runs Illinois's scan and no other instance's. The
instrument cannot see any of it, because it matches a workflow's own text and
the workflow delegates to that script. Six have no detector at all and the rows say
which.

| Cadence | Files | The runbook's exposure class | Last done |
|---|---|---|---|
| **Monthly**, on the statewide tripwire in the Standing table above | `ny-counties.json`, `ny-cities-towns.json`, `ny-villages.json`, `judicial-districts.json`, `tompkins-county-outline.json` | *Statewide civil boundaries: incorporation and annexation (occasional)* — which carries no date, so the plan is a publisher-side signal rather than a calendar: the scan reads the feature count on all four NYS services and the stated publication date on the three that have one. The last two are dissolves and slices of the SHIPPED county file rather than re-fetches, so they ride that entry and must be rebuilt in the same change — the Ad hoc civil-boundaries row below is the procedure. *Judicial districts: statute (rare)* in their own right, which is close to never | **_(never)_** |
| **Monthly** on the same scan, and **annually** when TIGERweb rolls its vintage | `metro-outline.json`, `ny-state-outline.json` | No runbook class: neither is a district. They are the coverage ring and the region band, water-inclusive Census geometry out of TIGERweb's State_County MapServer — a different publisher from the state's own shoreline-clipped fabric, which is why this instance's county edges and these two rings disagree at the shoreline by design. They got their own manifest entry on 2026-09-26, when a comment claiming the county entry covered them was measured false | **_(never)_** |
| **Each decennial census**, and on any court-ordered or mid-decade redraw | `congress-districts.json`, `state-senate-districts.json`, `state-assembly-districts.json` | *Decennial + court (very volatile)* for Congress and *Decennial + court* for the two chambers — three congressional maps in three years here, 2022-2024. The procedure is the **2031 Q2** and **2031–2032** checkpoints below, which this row names rather than restates; it exists so the instrument can see these three files have a plan, because a checkpoint row states its trigger in prose and names no file. Between cycles the monthly scan watches the TIGERweb layer vintage, which is what caught the CD119 to CD120 roll on 2026-09-03 | **_(never)_** |
| **Annually**, late summer, alongside the school-zone drill above | `ny-school-districts.json`, `ny-central-hs-districts.json` | *Statewide school districts: annual*, and the upper tier *statute — a reorganisation, not a redistricting (very rare)*. One builder writes both files from one NYS_Schools layer in one run, so they are rebuilt together or not at all. NYSED publishes no date to watch (measured 2026-09-21: its whole description is "School Districts of NYS."), so the raw row count — 936 polygon rows, dissolved to 716 districts, of which the 713 ordinary ones ship in the first file and the 3 upper-tier ones in the second — is the only automatic signal, and it sees a merger but not a boundary redraw | **_(never)_** |
| **Each decennial** cycle, and no more often | `borough-boundaries.json`, `bronx-county-outline.json`, `brooklyn-county-outline.json`, `manhattan-county-outline.json`, `queens-county-outline.json`, `staten-island-county-outline.json` | *Borough: never (geography)* — the five boroughs have been the same five counties since 1898, so this is a cadence for LOOKING rather than a claim that anything moves. The five outlines are slices of the borough file, so re-slice them in the same change. **Their only guard is this row:** `build_ny_borough_outlines.py --check` compares the slices against the shipped boroughs and runs in no workflow — measured 2026-10-01, zero occurrences in `smoke-test.yml` — and wiring it in retires that half of this row | **_(never)_** |
| **Each decennial** cycle, and no more often | `municipal-court-districts.json` | **No runbook class**, and none is borrowed: the NYC table in `docs/REDISTRICTING_RUNBOOK.md` has no Civil Court row. The 28 districts are set by state statute and the only automatic signal is the monthly scan's Socrata id-and-name check on `7vpq-4bh4`, which catches a replacement dataset and would not notice a redraw inside the same one | **_(never)_** |
| **Each decennial census**, when Tompkins County reapportions | `tompkins-legislature-districts.json` | *County legislature: decennial-county* — the county's own reapportionment. This one fires as a BUILD FAILURE rather than as silence: `build_tompkins_legislature.py` refuses to write unless each district's published population reproduces to the person from the Census 2020 blocks inside it, so a plan drawn on 2030 blocks fails that gate. The procedure is the **2031-2032** Tompkins checkpoint below | **_(never)_** |
| **Annually**, and on any Sullivan County district creation or dissolution | `sullivan-fire-districts.json`, `sullivan-library-districts.json`, `sullivan-county-outline.json` | **No runbook class**, and none is borrowed: the NYS table in `docs/REDISTRICTING_RUNBOOK.md` has no special-district row, because these districts are not redistricted — a fire district is created, dissolved or has its boundary altered by its own town board on petition, which follows no cycle at all. So the cadence is for LOOKING, and three automatic signals sit under it. The feature counts are EXACT in the manifest (45 and 2), so a creation or a dissolution fails `validate_index.py` on the next rebuild rather than shipping quietly. `build_sullivan_special_districts.py` refuses to write if the county's register ever marks a row retired, which it does not today on any of the 58, and refuses if the fire districts stop tiling the county. And its `--check` is offline on every pull request. **What none of the three can see is a boundary redrawn with the count unchanged**, which is the ordinary case when a town alters a district, and the annual look is for exactly that. The third file is a slice of the SHIPPED county file rather than a re-fetch, so it rides the monthly civil-boundaries row above as well and must be re-sliced in the same change | **_(never)_** |
| **Annually** | `coverage-gaps.json` | Not geometry and not a publisher's: its source is this project's own gaps block in `docs/DATA_LAYER_GUIDEBOOK.md`, and `build_coverage_gaps.py --check` re-emits and compares on every pull request, so file-against-record drift is already impossible. The cadence is for the RECORD — a gap can go stale in the direction nothing detects, which is how four Illinois counties sat served with no precinct layer and no record saying so | **_(never)_** |

**A `--check` PROVES A FILE MATCHES ITS INPUTS AND NEVER THAT THE INPUTS ARE
CURRENT**, which is why the three rows that name one are in this table rather
than excused by it. The three guarantees are also different from each other:
`build_coverage_gaps.py --check` re-emits and compares,
`build_tompkins_legislature.py` re-derives a population identity from the
census, and `build_ny_borough_outlines.py --check` compares one shipped file
against another. None of them is upstream.

**The monthly scan is a weaker plan than a rebuild and is recorded as the
weaker thing.** It tells you a publisher's count or date moved and a person
still has to act; for an annexation that moves a line between two
municipalities that both still exist, the count does not move at all, which is
why the publication date is watched beside it. The three layers with no
published date — the state school districts and the two TIGERweb rings — are
the least watched files in this instance, and that is a measurement rather than
an oversight.

---


## Open work the done standard asks for (measured 2026-10-01, not scheduled)

New York fails the standard's Covered test on four levels of government besides tribal,
and these two rows are the things a later pass must not have to rediscover. Neither is a
cadence: they are owed once, and then they are done.

| What | Why it is here | Done |
|---|---|---|
| **Re-measure the sites that would not answer, from the build machine** — 14 of the 57 county sites and 36 of the 101 largest town, city and village sites | Measured from a sandbox whose own route failed on most of them: re-read one at a time, only ONE was a real access control (Seneca's HTTP 202 managed challenge), against expired and mismatched certificates, resets, a 522 and four 403s. An unreachable robots.txt correctly disallows, so the reader was right and the input was the network. **Draft no ask about any of those units until this is done** | ☐ |
| **The county and town tranche programme** — 56 county governing bodies and 103 local ones | The route is measured and recorded in the guidebook section "New York's county and local tiers": no statewide roster exists, the state publishes every unit's own website with a GNIS id and a SWIS code, and in a board-of-supervisors county the county board seat IS the town supervisor, so one county's board page names every one of its towns' supervisors in a single fetch. Form first, from a certified document, per the Tompkins order | ☐ |

The one letter worth sending before any of that is Ask 33 in `docs/ASK_DRAFTS.md`, to the
state rather than to a hundred and sixty clerks: whether the Department of State or the
Comptroller holds a directory of local elected officials that is not on the open-data
portal. A clean no closes the statewide route for good.

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
| Ad hoc | A village is incorporated or dissolved, a town line moves, or a county boundary changes (the last needs an act of the Legislature) | `ny-counties.json`, `ny-cities-towns.json` and `ny-villages.json` are ONE product: `ny/scripts/build_ny_civil_boundaries.py` simplifies all three in a single mapshaper topology, because the county layer is the publisher's own dissolve of the town layer and three separate runs drew the shared line up to 310 m apart. Never rebuild one alone. The builder's exact feature counts (62 / 995 / 532) make this a BUILD FAILURE rather than silence; after rebuilding, rebuild `judicial-districts.json` in the same change (it dissolves the shipped county file), bump `cache_name` (all four are cache-first) and re-run `ny/scripts/validate_index.py`, whose shared-vertex gate is what catches a partial rebuild. | ☐ |
| **2031-2032** | Tompkins County reapportions its Legislature on the 2030 census | `county-legislature`'s Tompkins entry is the county's OWN GIS, and the thing that says the shipped plan is the one in force is arithmetic rather than a label: `ny/scripts/build_tompkins_legislature.py` refuses to write unless the 16 districts' published populations each reproduce EXACTLY from the Census 2020 blocks inside them. So a redrawn plan published against 2030 blocks will FAIL that gate rather than ship quietly — which is the point, and also means the block source (TIGERweb `Tracts_Blocks/MapServer/12`) has to move to the 2030 census in the same change. Rebuild, bump `cache_name` (the districts file is cache-first), and re-run the builder's `--check`. | ☐ |
| Ad hoc | Tompkins's Legislature page or its contact sheet is restructured, or the county's district service is renamed | The roster is SIX parse traps deep on a hand-edited page (a styled `<p>` for District 10's heading, a colon that moves in and out of `<strong>`, a nested `<strong>`, three unlinked names, a `<ul type="disc">`, and a last district closed by no `<hr>`), so a restructure is likelier here than a redraw. It fires as a SCRAPER FAILURE rather than as silence: `ny/scripts/tompkins_legislature_scraper.py` refuses unless it reads districts 1-16 from the page AND 1-16 from the PDF AND the two agree by surname in every district, and the contact-sheet pattern FAILS if it stops recognising the home address it exists to drop. The weekly run also re-reads the district service's own `Member` column as a drift witness and prints a disagreement. | ☐ |
| Ad hoc | NYPD opens/merges precincts (administrative — the 116th Precinct opened Dec 2024, the first since 2013) | Rebuild `police-precinct`/`police-sector` geometry, re-verify anchors, confirm the commander scraper covers the new precinct page. | ☐ |
| Ad hoc | DOE redraws Community School District lines (rare) or CEC structure changes | Re-verify `school-district` + `cec` (they share geometry). | ☐ |
| Ad hoc | A central high school district is created, merged or dissolved — a school-district REORGANISATION under Education Law, which needs the component districts' own voters and is rarer than any redistricting here | `nys-central-hs-district` is split out of the statewide school file BY CONTAINMENT, because nothing NYSED publishes marks the tier. `ny/scripts/build_ny_school_districts.py` refuses to write unless the upper tier comes out at `EXPECTED_UPPER_TIER` (3), so this fires as a BUILD FAILURE rather than as silence — rebuild both files together, re-run the builder's `--check`, and update `EXPECTED_UPPER_TIER` and the two files' feature counts in `ny/metro-worksheet.json` only after reading what actually changed. | ☐ |
| **2032–2033** (estimated from the 2020 cycle — the 2020-census ZCTAs reached TIGERweb about two years after the count; don't treat the year as firm) | Census publishes the ZCTA vintage built on the 2030 census | `nys-zip-code` is **live TIGERweb**, envelope-queried at runtime, so there is no file to rebuild — the work is confirming the layer index still holds ZCTAs and that the city's own `zip-code` (MODZCTA, a Socrata file) still answers inside New York City. The two are different tilings of the same ground and only one may answer a point. | ☐ |

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
- **A NYS Civil Boundaries republish** — `county`, `municipality` and `village` are
  *updated in place*: same URL, same service name, new content, for ever. Nothing renames,
  so reachability checks stay green while the shipped geometry quietly stops matching the
  state's. Two signals, because one is not enough: a **dissolution or incorporation moves
  the feature count**, and an **annexation does not** — it moves a line between two
  municipalities that both still exist — which is why the publisher's own "Publication
  Date" is watched beside the count. Either moving: rebuild that layer, re-verify the
  anchors, and check whether `judicial-district` (dissolved from the county fabric) and
  `metro-outline.json` need rebuilding with it.
- **A school-district reorganisation** — `nys-school-district` is the same in-place shape,
  but NYS_Schools publishes **no** date to watch (measured 2026-09-21: its whole description
  is "School Districts of NYS."), so the raw row count — 936, dissolved to 716 on
  `SED_CODE_1` — is the only automatic signal, and it sees a merger but not a boundary
  redraw. This layer is the least watched of the six and that is a measurement, not an
  oversight.
- **Judiciary Law §140** — `judicial-district` is thirteen unions of *whole counties*, so it
  moves only when the statute does or when a county boundary does. The county row above
  already watches the second, and the first is close to never; no separate detector exists
  and none is proposed.

When one fires: confirm enactment + effective date, then work **one layer at a time**
through the runbook. Don't touch layers that didn't change.

---

## Per-metro note

**This file is New York's.** Each instance in this repository carries its own `WATCH.md`
with its own bodies and enactment history (Illinois: wards/ERSB/CPS plus the collar
counties; San Francisco: Redistricting Task Force, election precincts, BART, SFUSD). The
decennial and off-cycle framing is shared; the layer rows are per-instance.

**The statewide tier is in the rows above as of 2026-09-21, and the open item is closed.**
PR 2 shipped the county, municipality, village, school-district and judicial-district layers
on 2026-09-18 and the go-live added their freshness entries; what was missing was the other
half — when to LOOK. The answer turned out not to be a date. Five of the six bodies change
by annexation, dissolution and reorganisation rather than on a cycle, so a decennial row
would have been a date nobody should wait for, and the honest trigger is a **measurable
change at the publisher**: the monthly scan now reads the feature count on all four NYS
services and the stated publication date on the three that have one. Only `nys-zip-code`
gets a calendar row, because a Census vintage genuinely is decennial.

The sixth layer also had no freshness entry at all until 2026-09-21 — `nys-zip-code` drew
TIGERweb ZCTAs with nothing watching them, while every other instance that uses that same
service already carried a row for it.
