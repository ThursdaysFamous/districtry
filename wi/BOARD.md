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
| Six roster workflows: shared pages after the branch cut (#1031) | **merged** `f2a0d88` | 2026-09-19 | The defect was measured here: run 35391214303 died on `wi/history.html` being dirty when #1014 merged mid-crawl. The ~40-minute county-clerk crawl is what makes the window wide, and the `Crawl-delay: 10` it honours is correct and untouched. |
| Lincoln District 21 boundary withheld | open | — | The county's map and the state's filing put the boundary in different places. The card says so rather than picking one. Correct as it stands; listed so it is not forgotten. |
| **Court of Appeals: one look for another host, then tolerate-and-ceiling** | **assigned, do first** | 2026-09-19 | Manager's call on your open question, reasoning sent in full. Not option (c). Spend one bounded pass on whether the four judges are published on a host that answers; failing that, make the wicourts.gov connect timeout a recorded expected condition so the run goes green and opens nothing, and add a staleness ceiling that goes RED when the last successful verification ages out. Keeps the signal, drops the weekly red that trains the eye to skim. Not a loosened guard — the ceiling is stricter than what exists today. |
| **The alderperson gap — measure the whole pool before any tranche** | **assigned, after the above** | 2026-09-19 | Your own board calls this Wisconsin's biggest reader-facing hole and I agree. In most of the 156 municipalities with council districts drawn the card names the district and nobody in it; 24 cities name theirs. Michigan's #989 probe is the shape: measure every candidate once, report, then ship tranches against the artifact with no discovery per tranche. |
| MPS and RUSD school-board jobs: Monday 21 September is the first test | open | 2026-09-19 | Both had a duplicate `run:` key that stopped GitHub starting them at all; fixed 2026-09-16 in #978 and no Monday has passed since. A zero-job run means the fix did not take. Check-in already armed. |

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

**2026-09-19 — the Court of Appeals job. Mostly answered, by the repo itself.**
I asked whether to re-route this, accept it as unautomatable, or drop the
weekly job. Reading `wi/scripts/wi_coa_scraper.py`'s own header, dated
2026-09-16, two of those were already settled and written down:

- **A second publisher was already looked for and rejected.** The Blue Book's
  bench is April 2025, older than what ships, and the Internet Archive's
  snapshots of both pages (8 and 19 August) are also older than the shipped
  roster. Either would move the data backwards.
- **Recording it as an expected block was already rejected, with a reason that
  still holds.** The cause is measured as per-runner packet DROPS, not a
  refusal: on 2026-09-16, 36 minutes apart, one runner reached the host in
  0.078s and another never opened a socket at all. So the host IS reachable
  from CI, just not from every runner, and an "expected unreachable" flag would
  flap month to month on the luck of the draw. Appeals is 2 green of 7 runs,
  circuit court 4 of 5, against the same host.

I confirmed the two facts that reasoning rests on rather than taking the file
for them: `wicourts.gov/robots.txt` is a 404, so allow-all, and both pages
answer HTTP 200 to the scraper's own `districtry-wisconsin/1.0` token. That
second check is from this sandbox through its proxy, so it says nothing about
runner routing either way.

**What is genuinely unsolved is smaller and different.** The file's stated
remedy is "re-run it and draw another runner" — but nothing re-runs it, and
nothing notices the roster ageing. Two additive guards would close that, and
neither loosens anything:

1. A staleness ceiling that turns the job RED when the last SUCCESSFUL
   verification passes a stated age. Sixty days is the number Iowa's chair
   carry-forward uses.
2. An automatic single re-run on a connect timeout, which is what a human would
   do and what the file already says the remedy is.

**The question for you is whether that is worth building at all**, given the
roster is four judges who change rarely and the job already succeeds about a
third of the time. I have not built it.
