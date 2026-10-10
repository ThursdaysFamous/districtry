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
| **Tribal governments are in scope and are not in this PR.** `scripts/tribal_areas.py --report Oklahoma` (2026-10-09): one federal reservation (Osage, 5,967.409 km²), one off-reservation trust land (Shawnee, 0.430 km²), no state reservation; the rest is Oklahoma Tribal Statistical Areas, never drawn as territory under Adam's 2026-09-30 ruling. Cherokee Nation was written to on 2026-10-01 about its district map. | Recorded as gap `ok-tribal-government`. | The fleet-wide tribal-government thread owns the build. Do not draw a tribal layer in `ok/` alone. |
| **There is no `ok/history.html`, and the masthead does not link one.** `history.html` is opt-in through the worksheet's `history_page` key, which this instance does not carry. | — | A history worth reading, once this instance has shipped something a reader noticed. |
