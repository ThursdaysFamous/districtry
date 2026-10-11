# WATCH.md — Oklahoma's watch calendar and deferred measurements

Two things live here: *when to look* for boundary and roster changes in this instance's
sources, and the measurements this instance has taken but not yet acted on. The repo's
`docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a boundary changes. Update the
"Last done" column each time you complete a row — a checkpoint with a stale date is a
checkpoint that didn't happen.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| Weekly (Mon 16:45 UTC) | U.S. House (Oklahoma) roster refresh | `.github/workflows/update-ok-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Weekly (Tue 16:45 UTC) | Oklahoma Senate + House roster refresh — Open States `ok.csv` | `.github/workflows/update-ok-legislature-roster.yml` → PR on change | Review + merge the PR — especially after an Oklahoma general (November, even years) and each February session start |
| Monthly (1st, 19:00 UTC) | Source freshness for every dataset this instance depends on | `.github/workflows/ok-validate-sources.yml` → tracking issue on WARN/FAIL | Read the issue; the job stays green on purpose |

## Deferred at this instance's first PR — each one measured, none acted on

| What | The measurement | What would move it |
|---|---|---|
| **Go-live is done.** `ok` is in `metros.json` and every fleet list (front door, coverage map, hand-off outlines, privacy, about, llms.txt, sitemap, traffic report, Wikidata draft, tribal join and the Examined/Answered/Maintained report); the deploy publishes `ok/` with the siblings' narrow exclude set; `ok/congress.html` and `ok/state-legislature.html` are generated and the two roster workflows regenerate them. | Done in the go-live change, held for the tribal census areas on Adam's ruling (2026-10-10). | Nothing. `docs/OK_EXPANSION_PLAN.md` is still unwritten and is the next record to write once the commissioner layer is planned. |
| **The House 99 seat and the Senate 24 seat have no member in the Open States export.** The export carried 47 of 48 senators and 100 of 101 representatives on 2026-10-09. House 99 is the district the State Capitol sits in, so the anchor point shows the chamber's directory instead of a name. | Measured 2026-10-09 from `ok.csv`. Not yet checked against the chambers' own sites, so whether each is a real vacancy or a gap in the export is NOT established. | Read `www.okhouse.gov` and `oksenate.gov` for both seats. If either chamber names a member, an enrichment from the chamber's own list is the fix rather than a hand edit. |
| **No chamber card carries a Capitol office or telephone.** The export carries neither for any Oklahoma legislator (0 of 147). Both chambers publish member pages (`https://oksenate.gov/senators` and `https://www.okhouse.gov/representatives` answered 200 on 2026-10-09). | `www.okhouse.gov`'s robots.txt answered a 404 HTML page on one read and an SSL error on the next, from this sandbox, on 2026-10-09. Measure it from a GitHub runner before deciding what it says. | A chamber-list scraper joined by district and surname, the North Carolina shape, gated so a roster with no offices cannot ship by accident. |
| **Commissioner districts are the next layer.** Every county elects three commissioners from three districts (19 O.S. 321); the state transport department publishes all 231 districts in one statewide file. | Read during planning. | The second PR: `county-commissioner`, with its roster source measured before it ships. Retires gap `ok-commissioner-districts`. |
| **Precinct maps are a separate question with an ask out.** The State Election Board said the precinct maps in the OU Center for Spatial Analysis warehouse are downloadable and that permission questions belong to the Center. The Center was written to on 2026-10-01 (ask `ok-csa-precinct-terms` in `docs/ASK_DRAFTS.md`); no reply as of 2026-10-06. | The follow-up clock belongs to the Letters thread. | A reply stating the terms. Until then no precinct layer ships. |
| **Tribal areas SHIPPED 2026-10-10 by the fleet-wide thread as `tribal-government`, drawing the Census's statistical areas on Adam's exception for Oklahoma.** 31 areas across 33 nations: Osage, the Shawnee Tribe's trust land, 25 Oklahoma Tribal Statistical Areas and 4 joint-use areas. No council is named (`ROSTER_NOT_SOUGHT`). Five governments with no area of their own are listed by their seat city as "Also seated in this area". | Recorded as gap `ok-tribal-government`. Cherokee Nation was written to on 2026-10-01 about its district map. | **Annually, on the TIGERweb vintage roll**: `python3 scripts/build_tribal_areas.py --state Oklahoma --tag ok` rebuilds and re-measures the 25 m simplification ceiling; `--check` is offline and proves the join, never the Census's own set. Reading each nation's council list is the next step, and moves its nations out of `ROSTER_NOT_SOUGHT`. |
| **There is no `ok/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |

---

## Per-class re-checks — the map files no job rewrites

`docs/EAM_STATUS.md` checks that every data file the app reads has a stated
re-check plan. On 2026-10-11 seven of Oklahoma's had none: six boundary files
and the gaps record. None of them names a person, so a weekly job would find
nothing to change. Each needs a stated time to look again, and these rows are
that.

The monthly `ok-validate-sources.yml` check does not replace these rows. It
confirms the sources still answer and that feature counts have not dropped.
It cannot tell when a line is redrawn with the same number of districts, which
is what a redistricting usually looks like. A `--check` proves a shipped file
matches its inputs, not that the inputs are still current.

| Cadence | File | The clock, and why it is that one | Last done |
|---|---|---|---|
| **Annually**, when TIGERweb rolls its congressional vintage, and on each decennial redraw (next: 2031–2032) or any court-ordered one | `congress-districts.json` | The Legislature redraws Oklahoma's five U.S. House districts after each census. TIGERweb's yearly vintage roll is the annual clock, because a roll can rename or remove the field the builder reads. Re-run `ok/scripts/build_legislative_boundaries.py` with no arguments, compare the district count against the apportioned delegation, re-verify the smoke anchors and bump `sw.cache_name`, because this geometry is cache-first | **_(never)_**, built 2026-10-09 |
| **After each decennial census** (next: 2031–2032), and on any court-ordered redraw | `ok-senate-districts.json`, `ok-house-districts.json` | The Legislature redraws its own 48 Senate and 101 House districts after each census. Same builder and the same steps as the row above. The 25 m stray ceiling was measured on these lines, so re-measure it on new ones rather than carrying it forward | **_(never)_**, built 2026-10-09 |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json`, `metro-outline.json` | Both are the same 77-county set; the outline is its dissolve, so they share one clock. County lines almost never move, but the Census's drawing of them does. Re-run `ok/scripts/build_state_counties.py` and `ok/scripts/build_metro_outline.py`. Note that `build_metro_outline.py --check` only tests the shipped outline against its anchors and does not re-fetch | **_(never)_**, built 2026-10-09 |
| **Annually**, on the TIGERweb AIANNH vintage roll | `tribal-areas.json` | The Census redraws Oklahoma Tribal Statistical Areas with its own partners, and a vintage roll can add, merge or move an area. Run `python3 scripts/build_tribal_areas.py --state Oklahoma --tag ok`, which rebuilds the file and re-measures the 25 m ceiling. Its `--check` proves the join of land to government and never the Census's own set. The fleet-wide tribal thread owns the builder | **_(never)_**, built 2026-10-10 |
| **Monthly**, and whenever a gap's blocker changes | `coverage-gaps.json` | This file comes from the guidebook's gaps block, and `build_coverage_gaps.py --check` already keeps file and record in step on every pull request. The cadence is for the RECORD. Its four entries (`ok-commissioner-districts`, `ok-municipal-officeholders`, `ok-school-board-members`, `ok-tribal-government`) describe work in progress and letters awaiting replies, so they go stale as soon as that work ships or a reply arrives. Re-read each against what the app now draws | **_(never)_**, written 2026-10-09 |
