# Iowa board

Owner session: **Iowa** (`session_01GDDwuCzmWxgdbz3V8GHrjJ`). Manager owns
*Tasks*; this session owns *Status* and *Open questions*. Rules and reporting
posture: `BOARD.md` at the repo root. Commit board edits straight to main, in
their own commit, dated.

> **Correction, 2026-09-19.** The first version of this board said Iowa had no
> session. That was wrong — this session has been running since 2026-08-27 and
> was active twenty minutes before the board was written. The manager concluded
> it from a session listing that omitted it, which is the one thing
> `docs/MANAGER.md` already says never to do: query the id, never infer absence
> from a listing. Nothing was assigned elsewhere on that basis.

## What a reader gets today

Click any point in Iowa and the app answers from **20 layers**, across all 99
counties. Two rosters are **complete**: county officers (99 of 99) and county
auditors (99 of 99).

**6 recorded gaps** — 4 data-quality, 1 no-source, 1 blocked.

## Tasks — manager owns this section

| task | state | opened | notes |
|---|---|---|---|
| **The chair gap record states a number the file no longer carries** | **assigned, do FIRST** | 2026-09-19 | `ia-board-chair`'s reader text says "in 43 of Iowa's 99 counties… In the other 56 it cannot". The file holds **38**, so it is 38 and 61. This ships to the Data gaps panel, so it is wrong on the page a reader opens. `ia/WATCH.md` line 39 carries the same 43. This session already has it — its own last summary names it. |
| **Supervisor roster covers 17 of 99 counties** | open | — | The headline gap. It also caps the per-county pages: 26 counties have a chair and no board list, so they get no page at all. |
| City card names nobody | open | — | `ia-city-contact.json` covers 939 cities with contact details and no officeholder names; 834 have no website at all. |
| Precinct card cannot say where to vote | open | — | no-source. The polling-place precinct column was dropped upstream. |
| Johnson County districts pending; Jones County absent from the state layer | open | — | Two county-level data-quality holes. Johnson's minutes host refuses `districtry` in robots.txt — that is the host's answer, not a bug. |
| Marion ward card blocked | blocked | — | Access control. Never worked around. |
| **Mitchell County: re-read the page and fix the parser** | **assigned, second** | 2026-09-19 | Manager's answer to your open question, and it is agreement rather than an override: do NOT pass `--allow-drop`. The guard refused to write rather than drop five real supervisors, which is correct, and is why the supervisor roster has been frozen since 2026-08-28. Fix the cause. |
| `ia-county-officers.json` phone numbers have never been measured | **assigned, third** | 2026-09-19 | Yes to your question, with one condition: measure and report before building anything. ~305 numbers across 99 counties, same defect class #1000 fixed on the city rosters — a switchboard number rendered as a named person's direct line. A clean result is a result worth recording. |

**Do not re-probe the blocked counties with different headers.** Measured
2026-09-06: of the 20 counties the gated run calls unreachable, nine answer 403
and eight of those are Cloudflare, seven serving a managed challenge. A complete
header set with this project's own user-agent moved none of them, and a browser
user-agent is not an option. Polk is **withdrawn** rather than blocked — review
could not reproduce it, so it is client-dependent.

## Status — this session owns this section

**2026-09-19 — the queue is clear and both changes are on main; one item is
waiting on a clock.** #1038 merged as `ca7a284` and #1034 before it, both
verified on the merged tree rather than taken from the PR page: the chair-page
line prints the set difference (30) where it printed the subtraction (21), and
`CLAUDE.md`'s stale 26 is gone. Nothing of mine is open.

**The weekly supervisor run has not been due yet, and a late run is not a
missing one.** Its cron is Saturday 17:30 UTC and it was 15:43 UTC when I
checked. Its last three runs started 19:55, 19:18 and 19:34 UTC — 1h48m to
2h25m after the cron — so the earliest plausible start today is about 19:15.
Nothing is dispatched; a replacement run for a job that is merely late would
race the real one. What the run should show, from the full rebuild I did this
morning and did not ship: Mitchell keying 5 of 5 on its restored host, and
Bremer (3) and Hamilton (3) leaving on robots refusals already recorded in
`ROBOTS_REFUSED_DROPS`, with `bremer.html` and `hamilton.html` deleted from
`ia/county-supervisor/`. If it opens a bot PR it is not mine to merge — it gets
read and reported. If it fails, the reason gets read before Mitchell is blamed
again.

**2026-09-19 — the queue is clear; #1034 merged and #1038 is open.** The
38/61 gap-record correction landed. The last item, the chair-page count, is
#1038: `build_county_pages.py` printed `len(chairs) - len(out)`, which is right
only if every county with a member list also has a chair, and nine do not
(Bremer, Franklin, Hamilton, Lyon, Mitchell, Pocahontas, Polk, Sac, Webster).
It is the set difference now — 21 printed where the answer is 30. `CLAUDE.md`
carried the same figure as 26 and is corrected with it, quoting no live value,
because all three counts move weekly and the line prints them. No page content
changes; `--check` reads all 198 pages back and names every one of the 2,980
people on them.

**Where the four items ended.** 38/61 shipped. Mitchell needed no fix — its
host's suspension had lifted and it keys 5 of 5, so the roster unfreezes on its
own at the weekly run. The phone measurement came back clean on
`ia-county-officers.json` and found the shape one file over, in the auditors.
The count fix is #1038.

**Two things are waiting on a yes, neither built:** labelling the 17 auditors
whose phone is their county's board line, and giving the supervisor builder a
recorded excuse path for a measured suspended host.

**2026-09-19 — the phone measurement: `ia-county-officers.json` is clean, and
the finding is one file over.** Measured this morning, numbers normalised to
digits so the two published formats compare. That file carries **391 named
people, all 391 with a phone**, and on the switchboard question it comes back
clean four ways: **zero** numbers held by two or more named people in one
county, **zero** row officers carrying their own county's `boardPhone` across
91 testable counties, **zero** numbers shared by named people in different
counties, and **345 supervisors carrying no phone at all** — the officer builder
already hoists a board-wide number into `boardPhone` and strips it from the
member rows, and the roster builder raises rather than letting one back in. A
clean result, recorded as one.

**`ia-county-auditors.json` is where the shape shows up: 17 of 89 testable
auditors carry the same number as their county's board line.** It is not a
pipeline agreeing with itself — the auditors come from their own association's
directory and `boardPhone` is derived from ISAC's supervisor rows, so two
independent publishers land on one number. And it is not a wrong number: Iowa
Code 331.504 makes the auditor clerk to the board, so the board's line IS the
auditor's office. What makes it worth reporting is the RENDERING — `ia/index.html`
puts that number in the person row beside the name and the County Auditor badge,
while the office group below it carries only a label and an address, so a reader
sees a general office line presented as one person's.

**Why no existing guard sees it.** The switchboard rule this project already
wrote down (EXPANSION_GUIDE Part 5) fires when ONE number covers EVERY member of
a body. An auditor is one person in a different file, so a test that looks for a
number repeated across a board can never fire on them. The test that does catch
it is the cross-file one — auditor's phone against the board's hoisted
switchboard — and nothing runs it.

**Proposed, not built:** the #1000 treatment, which is a label rather than a
data change — mark those 17 as the board's office line the way the Iowa city
rows say "City office number", and keep the number dialable. Waiting for a yes.

**2026-09-19 — Mitchell needed no parser fix, and the reason is on the record
already.** I was told to re-read the page and fix the parser, and that premise
does not hold: `mitchellcounty.iowa.gov`'s hosting account was SUSPENDED, so the
host answered every path with one 7,640-byte cPanel page. The repo measured that
on 2026-09-13 (#943, `serves_one_document`) — one day AFTER the 2026-09-12 run
that failed, and this job runs Saturdays, so today is the first run to exercise
it. **The suspension has since been lifted.** Asked through the scraper's own
gated path this morning, robots served and allowing, Mitchell keys 5 of 5 off
`/board-of-supervisors/`. There was never a parser to fix and `--allow-drop`
would have dropped a county whose page was coming back.

**The full rebuild passes, and it is not a no-op.** 15 Plan 3 counties, 61
districts. Against the shipped file that is Mitchell staying and **Bremer (3) and
Hamilton (3) leaving** — six named supervisors — both on robots refusals already
recorded on 2026-09-13, Bremer's a 500 on its robots.txt and Hamilton's a `*`
Disallow through its CMS vendor. No name changed and no seat moved. I did NOT
ship it: the weekly job at 17:30 UTC produces exactly this diff as a bot PR, its
workflow already regenerates the county pages the roster feeds (verified — the
gate names `bremer.html` and `hamilton.html` for deletion), and officeholder data
belongs in that reviewed PR rather than in one of mine racing it.

**One latent gap found, reported rather than built.** A measured robots refusal
has a recorded excuse path (`ROBOTS_REFUSED_DROPS`, one entry per county with a
reason and a date, added by a person). A measured SUSPENDED HOST has none — it
can only be cleared by `--allow-drop`, which the weekly workflow does not pass
and should not. Mitchell recovering makes that moot today; the next suspended
county freezes the whole roster again with no recorded way out. The fix is to let
that same recorded table carry a non-robots standing condition, and it is a
decision about a guard rather than a bug, so it waits for a yes.

**2026-09-19 — the 38/61 correction is in review as #1034.** The
`ia-board-chair` record said 43 of 99 and the other 56; the shipped file holds
38, so the Data gaps panel was making a false statement to a reader. It reads 38
and 61 now. `ia/WATCH.md` carried the same 43 and two figures that had moved with
it — the per-route split is a weekly measurement (33 board pages, 4 minutes, 1
carried on 2026-09-18, against 38 and 5 a week earlier), and **the floors stay at
30 and 3** rather than following it down.

The blocker log now carries the vantage correction I had only written on this
board, appended with the superseded 2026-09-06 sandbox measurement left above it.
The Actions runner reports **15** unreachable rather than 20, in a different
shape, and **the eight answering HTTP 202 are new**: four of them resolved on
2026-09-11 and were behind a challenge a week later. Nothing was re-probed. Polk
now carries both readings with whose vantage each is.

**Next: Mitchell County.** Re-read the page and fix the parser — not
`--allow-drop`. The guard refused to write rather than drop five named
supervisors, which is why the supervisor roster has been frozen since 2026-08-28,
and talking a working guard out of its answer is not a fix. Then the
`ia-county-officers.json` phone measurement, reported before anything is built,
then the `len(chairs) - len(out)` one-liner.

**2026-09-19 — board commits go straight to main.** Adam answered the question
this section carried: the board rule wins, and board edits from this session
push directly rather than riding a pull request. This entry is the first one
that did. PR #1032, which held the two entries below while the question was
open, is closed as superseded rather than merged.

**2026-09-19, later — paused for the night.** Nothing of mine is in flight.
The Status below was written against main at `881d3f0`; main is `8506c8c` now
and none of tonight's merges change any figure in it. Iowa's own reading of the
fleet-wide name gate that arrived with them (`validate_officeholder_names.py`,
which discovers every instance rather than listing them): **2,181 Iowa person
records, every one a name, nothing accepted or flagged.** Its whole-fleet total
reads 12,446 across 757 files on this tree — the 10,985 in circulation is the
figure that file's own docstring quotes as its SUPERSEDED OK line, so it is a
relay of a corrected number rather than a disagreement with the gate.

**What I would pick up first, in this order.** (1) Mitchell County's supervisors
page, because the weekly supervisor job has been red on its guard since
2026-09-12 and ran red again today, which is why the 17-of-99 headline has not
moved since 2026-08-28. (2) The 43/56 in the `ia-board-chair` record and in
`ia/WATCH.md` line 39 — 38 and 61 — since that one is wrong on a page a reader
opens. (3) The `len(chairs) - len(out)` line in `build_county_pages.py`, a
one-line fix for a build-log figure that is 21 where the answer is 30.

**2026-09-19 — in flight: nothing.** Last work merged as #1000 (Iowa city
phones say whose number they are) and #1016 (the weekly chair refresh). What
follows is a read of Iowa taken against main at `881d3f0` this morning, newest
first.

**The chair count fell from 43 to 38 yesterday and a reader sees it.** #1016
merged the weekly refresh and five counties left the file. Four — O'Brien,
Osceola, Palo Alto and Plymouth — now answer HTTP 202 on robots.txt, an access
control, where they resolved normally a week earlier; the fifth, Union, timed
out. A sixth, Dallas, left for a different and real reason: its minutes stopped
yielding extractable text. Henry joined. So the reader-facing pair is **38 and
61**, which is the manager's top task and is correct as written.

The good news underneath it: every one of the 38 records now carries a
`confirmedOn` date, so the carry-forward built in #897 is armed for all of them
rather than for Clayton alone. Clayton itself was the test — it went unreachable
again on the 18th and was **carried** rather than dropped, exactly as predicted.
A county that goes dark next week keeps its chair for up to 60 days instead of
vanishing.

**The blocked-counties note on this board is one measurement behind, and the
rule it states still stands.** That paragraph was measured 2026-09-06 from this
sandbox: 20 unreachable, nine 403s, eight Cloudflare, seven managed challenges.
The 2026-09-18 GitHub Actions run — the vantage the weekly refresh actually uses
— reports a different shape: **15 unreachable**, of which 5 are a plain 403
(Clayton, Decatur, Guthrie, Hardin, Polk), **8 answer HTTP 202 on robots.txt**
(Dickinson, Emmet, Jefferson, O'Brien, Osceola, Palo Alto, Plymouth, Sioux), 1
is a connect timeout (Union) and 1 is robots.txt answering HTTP 500 (Bremer),
with Cherokee and Hamilton separately refusing by robots.txt. Do not re-probe
any of them — the point of the correction is that the 202 group is **new**, not
that anything should be retried. Four of those eight were readable on
2026-09-11.

**Polk answers 403 from the Actions runner.** This board calls Polk *withdrawn*
because review could not reproduce the block. That reading is still right about
review's vantage — but the client that runs the weekly refresh got 403 on
2026-09-18, so Polk is not going to resolve on its own and should not be
expected to.

**"26 counties have a chair and no board list" is 30, and no source of that
number was measured.** Three figures are in circulation: 26 (`CLAUDE.md`, from
the 43-chair era), 21 (printed by `build_county_pages.py` on every run) and 30
(the actual set difference). The builder computes it as `len(chairs) -
len(out)`, which is only correct if every county with a board list also has a
chair — nine do not (Bremer, Franklin, Hamilton, Lyon, Mitchell, Pocahontas,
Polk, Sac, Webster). Measured: 38 chairs, 17 board lists, 8 counties with both,
so **30 counties have a chair and no page**. It is a build-log line rather than
anything a reader sees, and the one-line fix belongs in its own change because
board commits are prose only.

**The supervisor roster has been frozen since 2026-08-28 because its weekly
refresh is red, and that is why the headline gap has not moved.** The
2026-09-12 run stopped itself:

> Mitchell (5 districts) shipped last time and keyed nothing this time — that
> is a page to re-read, not a diff to merge.

That is the guard working: Mitchell's page stopped naming its districts in a way
the scraper reads, and rather than silently dropping five real supervisors the
builder refused to write. But nobody has read that page since, the job runs
again today at 17:30 UTC, and it will fail again until someone does.

**One red job that costs a reader nothing, recorded so nobody chases it.** The
legislature refresh shows failure on 2026-09-15. It scraped, built, validated
and pushed fine, then died at `gh pr create` on the account's GraphQL rate
limit. The pull request was opened by hand and merged the same day as #974, so
the Senate and House rosters are current. Nothing has changed to stop it
recurring.

## Open questions for Adam

- **Neither of my two open findings should jump the queue, and here is the
  ranking anyway.** Asked whether either should, my answer is no — but if one
  moves first it should be the SUSPENDED-HOST excuse path, and the reason is the
  failure's shape rather than its likelihood. When a county's host is suspended
  the supervisor build does not drop that one county; it refuses to write at
  all, so a single dead host freezes the roster for all 99. Mitchell froze it
  for a week and would have frozen it indefinitely had the hosting account not
  been restored on its own. The only escape is `--allow-drop`, which is the
  lowered-guard rule in another costume. It is dormant today, which is why it
  does not jump.
  The AUDITOR LABELLING is the lower-consequence of the two: 17 counties where a
  reader sees a real, working office number presented beside one person's name.
  Misleading in emphasis, not wrong in fact — the auditor does answer it, under
  Iowa Code 331.504. Worth doing, worth doing after almost anything else.

- **Mitchell County** — re-read the page and fix the parser, or pass
  `--allow-drop` and let the county go? I would re-read it: five named
  supervisors is a real loss and the page changing shape is the likelier cause.
- **`ia-county-officers.json`'s phone numbers have never been measured** for the
  problem #1000 fixed on the city rosters — a single switchboard number repeated
  across several named people. It carries roughly 305 numbers across 99
  counties. Worth the measurement, or leave it?
