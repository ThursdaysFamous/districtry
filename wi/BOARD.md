# Wisconsin board

Owner session: **Wisconsin**. Manager owns *Tasks*; this session owns *Status*
and *Open questions*. Rules and reporting posture: `BOARD.md` at the repo root.
Commit board edits straight to main, in their own commit, dated.

## What a reader gets today

Click any point in Wisconsin and the app answers from **31 layers**, across all
72 counties. County board supervisors, circuit judges, county officers and the
Milwaukee and Racine school boards all name people.

**10 recorded gaps** — 8 data-quality, 2 no-source.

## Tasks — manager owns this section

| task | state | opened | notes |
|---|---|---|---|
| Six roster workflows: shared pages after the branch cut (#1031) | in review | 2026-09-19 | The defect was measured here: run 35391214303 died on `wi/history.html` being dirty when #1014 merged mid-crawl. The ~40-minute county-clerk crawl is what makes the window wide, and the `Crawl-delay: 10` it honours is correct and untouched. |
| Lincoln District 21 boundary withheld | open | — | The county's map and the state's filing put the boundary in different places. The card says so rather than picking one. Correct as it stands; listed so it is not forgotten. |

## Status — this session owns this section

**2026-09-19, close of evening.** Wisconsin passes the new fleet-wide name gate
from #1025 — 1,492 person records, every one a name. Nothing to fix here; the
two records it found are Illinois's.

**What I would pick up next, in this order.**

1. **Monday 21 September.** The Milwaukee and Racine school-board jobs run for
   the first time since their repair. A check-in is armed for 23:00 UTC that
   day, late enough to allow for this repo's scheduled jobs starting 3 to 5
   hours behind their cron time. A zero-job run means the #978 fix did not take;
   a run that starts and then fails is a different problem and belongs here.
2. **The Court of Appeals decision**, in Open questions below. It is not work
   until it is answered.
3. **The county clerk refresh.** Unblocked by #1031 but not re-run. Friday
   14:30 UTC on its own, or dispatched sooner at the cost noted above.
4. **The alderperson gap is Wisconsin's biggest reader-facing hole** and is the
   place to spend effort if anyone wants new ground rather than repairs. In most
   of the 156 municipalities with council districts drawn, the card names your
   district and not the person in it; 24 cities name theirs. That is the gap a
   reader notices.

**One finding here is fleet-wide and is not Wisconsin's to close.** The shallow
checkout that made the sitemap stamp every page with the run date affects every
roster workflow, not only these six. #1030 and #1031 fixed twelve of them. The
rest of the fleet's weekly jobs still check out one commit deep, so any of them
that regenerates and commits the sitemap has the same defect. Recorded for the
root board rather than acted on.

**2026-09-19, later.** #1031 merged. Two things a reader gets from it. The six
Wisconsin roster jobs can now finish instead of dying at the last step whenever
an unrelated change lands on main mid-scrape, which is what stopped last week's
county clerk refresh reaching anyone. And every page on the site stops claiming
it was updated today: these jobs fetched only one commit of history, so the
sitemap stamped all 243 pages with the run date, and a bot run on 17 September
had already shipped 241 wrong dates. The site's own drift check could never
catch that — it only tests whether a date is too OLD.

**2026-09-19.** Three of Wisconsin's eleven weekly refresh jobs are not
working. Nothing a reader sees is wrong today; the risk is that these rosters
quietly stop being checked and go stale without anyone noticing.

- **Court of Appeals — dead two weeks.** Last successful run 4 September;
  failed 9, 12 and 16 September with a connection timeout to wicourts.gov. The
  note committed on 18 September says the failure depends on which GitHub
  machine the job lands on, so the court appears to refuse some runner
  addresses. A retry does not fix that. The roster is four judges and last
  changed 27 August, so the card still reads correctly — it is simply no longer
  being verified.
- **Milwaukee and Racine school boards — repaired but never yet run.** Both had
  a duplicate `run:` key that stopped GitHub starting them at all: every push to
  any branch created a failed run with zero jobs. Fixed 16 September in #978.
  Both are scheduled for Mondays and no Monday has passed since, so **Monday 21
  September is the first real test.** A failure then is a different problem from
  the one that was fixed. MPS's roster last changed 27 August, RUSD's 3
  September.
- **County clerk — fixed and merged.** Run 35391214303 died at the branch cut on
  18 September after a 40-minute scrape; #1008 was closed unmerged rather than
  ship a roster built by a superseded builder. #1031 merged 02:38 UTC today
  (`f2a0d88`), so this job and its five siblings can now finish. Its next
  scheduled run is **Friday 14:30 UTC**; it can be dispatched sooner, but a pass
  costs about 40 minutes because wisconsincountyclerks.org asks for a 10-second
  delay between pages and the scraper honours it, and that host already served
  three passes on 18 September.

Everything else is intact and was measured today: 1,574 of 1,591 county board
seats named across all 72 counties (15 seats the counties themselves report
vacant, 1 withheld, 1 county electing countywide), all 72 county clerks, 608
municipal clerks, 69 circuit judges, and polling places for roughly 8,000 wards.
Sources last verified 11 September.

**Correction for the Tasks table.** The summary above says the Milwaukee and
Racine school boards "name people", which is true, but both rosters are ageing
and neither job has run since its repair. Worth a row until Monday proves them.

## Open questions for Adam

**2026-09-19 — the Court of Appeals job.** Two weeks of failure, diagnosed as
wicourts.gov refusing some GitHub runner addresses rather than anything in our
code. Three ways out, and it needs a decision rather than another retry: fetch
it by a different route, accept that this one roster cannot be checked
automatically and say so on the record, or drop the weekly job and re-verify by
hand when the court's bench changes. Four judges change rarely, so the third is
cheaper than it sounds.
