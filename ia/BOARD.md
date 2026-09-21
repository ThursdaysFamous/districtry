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

**2026-09-21 — resumed on three tasks; two had already been done or had
expired, and the third is measured clean.**

**1. The chair gap record was already correct.** #1034 fixed it on 2026-09-19:
the Data gaps panel reads 38 and 61 today, and `ia/WATCH.md` line 39 says "38
of 99 counties as of 2026-09-18". Checked against the SHIPPED panel file rather
than the guidebook block, since the panel is what a reader opens. The last
stale copy was somewhere nobody named — `ia-county-board-chairs.json`'s note in
`ia/metro-worksheet.json`, wrong twice over: 43 was the superseded total, and
the "38 from its board-of-supervisors page" put that new total in a DIFFERENT
quantity's slot (the split is 33 pages + 5 minutes). **#1065.** My first attempt
hand-edited the generated `validate_index.py` and was reverted; the worksheet
owns it. The replacement states no live count at all and names where each
figure lives, because this is the third thing in three days to go stale by
having a weekly-moving number written into a sentence.

**2. Mitchell needed no fix, and the probe found the defect this board's own
WATCH row predicted.** Measured 2026-09-21 with the scraper's client, robots
first: `mitchellcounty.iowa.gov` serves its real site again — 70-byte
robots.txt, `User-agent: *` empty group, home page 110,546 bytes, supervisors
page 155,651 bytes pairing all five supervisors with districts 1-5, an invented
path 404s. The suspension ended on its own and the 2026-09-19 run keyed
Mitchell 5 of 5 (shipped in #1048). **No parser changed, `--allow-drop` never
passed — the guard was right to refuse for six weeks.**

*What the probe found instead:* the host runs an INTERMITTENT bot challenge and
**I tripped it myself** with four rapid requests including an invented URL;
eight spaced reads afterwards all returned the real file. So one bad read of
this host is not evidence of a suspension, and the trigger is our request shape.
That interstitial proved the defect: `robots_policy.classify()` returned
`served` for it and `allows()` answered TRUE — a managed challenge read as
permission to crawl, in the fleet's single robots reader. Fixed: HTML at
/robots.txt is no longer parsed as one; challenge markers refuse, any other
HTML still ALLOWS (a host with no robots.txt is open, and refusing there would
shut hosts serving us data). 10 new assertions, 73 → 83. **Committed and held
off the branch until #1065 merges, so the two pieces stay separately
reviewable.**

**3. The officer phones are clean, and that is the result.** 391 numbers across
99 counties, measured offline: **zero shared between officers in a county, zero
repeated across counties, all 391 distinct.** No county's `boardPhone` equals
any officer's. 80 counties' four officers share one area+exchange, which is
courthouse direct-dial rather than a switchboard, and 19 span several. The
defect #1000 fixed on the city rosters — one number rendered as several
people's direct line — **does not exist in this file.** The card already labels
each number under its office row rather than as a personal line.

*One of my three tests was vacuous and is not counted as evidence:*
`ia-county-board-directory.json` carries no phone field (keys are county, plan,
seats, url), so "does an officer's number equal the county's main number" was
never actually asked. Answering it needs a comparand this repo does not hold.
Nothing is proposed to build here.

**2026-09-19, 22:39 UTC — the preserve ruling is live, and the weekly run proves
it end to end.** #1051 merged at 22:25. Rather than leave #1048 carrying a
roster that deletes two counties' supervisors until next Saturday, I dispatched
`update-ia-supervisor-roster.yml` on main — the fix is only real once a run that
actually reads the counties writes the file, because a cache fixture's dates
would assert reads that never happened.

**The run rebuilt #1048 and every check passes.**

| | deleting run, 19:30 | preserving run, 22:25 |
|---|---|---|
| counties / districts | 15 / 61 | **17 / 67** |
| diff | 44 insertions, **1,000 deletions**, two county pages deleted | 25 insertions, **4 deletions**, nobody unpublished |
| `check_roster_retention` | FAIL, two sources VANISHED | **OK, quiet on its own** |
| #1048 CI | red | **green** |

Bremer (017) and Hamilton (079) each keep three supervisors, carrying
`readOn` and `asOf` of 2026-08-28 and the reader-facing reason. Mitchell, read
this run, carries `readOn` 2026-09-19 and NO `asOf` — the distinction is in the
data rather than asserted. Both county pages exist again and say "last read
2026-08-28 and no longer re-read ... These names will go out of date"; Mitchell
keeps "re-read on a schedule". Iowa's llms.txt line stays at 17.

**THE ACCEPTANCE TEST WAS THE RULING'S OWN AND IT PASSED WITHOUT AN EXCEPTION:**
the retention gate reports six accepted drops and neither county is among them.
That is the difference between fixing a cause and excusing a symptom, and it is
the test to reach for the next time a gate objects to a builder.

**A correction to how I described this all evening.** I repeatedly wrote that
the two counties "left" and that their pages "were deleted". That describes
#1048's DIFF and never the site: #1048 was never merged, and main carried
Bremer and Hamilton with all six names throughout. A weekly run PROPOSED a
deletion and the retention gate refused it. The distinction matters — one is a
loss to go and fix, the other is a guard working — and I was loose about it.

#1048 is green and waiting on human review. Not mine to merge: officeholder
data.

**2026-09-19, 21:20 UTC — Adam ruled PRESERVE, and my accepted-drop fix was the
wrong one.** The ruling is fleet policy: preserve data we have already fetched.
A robots refusal stops us READING a county; it does not require us to unpublish
three supervisors we fetched legitimately while the county was serving. My
`ACCEPTED_DROPS` entries excused the symptom — they taught the gate to accept a
deletion — where the cause was that `build_ia_supervisor_roster.py` deletes.
Reverted on the bot branch, so #1048 is correctly held red by the gate again.

**Iowa was the outlier and that is the argument for the change.** Illinois
preserves (`PRESERVABLE`), Wisconsin re-asks an `unreachable` verdict before
believing it, and this was the builder that deleted. Shipped as **#1051**:
`ROBOTS_REFUSED_DROPS` → `ROBOTS_REFUSED_PRESERVED` with both audits intact, the
previous roster read in full and carried forward, and `readOn` stamped by the
SCRAPER rather than the builder — a builder run against a week-old cache would
otherwise date every county today.

**THE RULING'S OWN RISK IS THE PART WORTH REMEMBERING.** A preserved county
ships officeholders nothing re-verifies, and the instance-wide "Data last
verified" date would then assert a verification we did not perform. So `asOf`
and `asOfWhy` ride the record and BOTH reader surfaces say so. The county PAGE
was the one nobody had looked at: it said the roster is *"re-read on a
schedule"*, which is false for these two counties, in served bytes a crawler
reads. It now says last read 2026-08-28 and no longer re-read, with the reason,
and a still-read county keeps the scheduled sentence.

**The acceptance test was the ruling's own**: `check_roster_retention` goes
quiet on its own, exit 0, six accepted drops and none of them these counties.
That is the difference between fixing the cause and excusing the symptom, and
it is the test to reach for the next time a gate objects.

*Measured, not assumed:* both refusals re-verified on both host spellings
(Bremer HTTP 500, Hamilton `Disallow: /` in its own per-tenant file at its CMS
vendor); the seed dates come from commit `bce3108`, 2026-08-28, the last weekly
run that wrote either county. No roster data ships in #1051 — the builder was
exercised against a cache fixture rather than by re-scraping 39 county sites,
and a fixture's dates would assert reads that did not happen, so the next
weekly run writes the real file.

*Corrected:* #1049's body said 61 of 63 workflows lack the llms.txt step.
Counting only workflows that REGENERATE county pages it is 60 of 62 — the
denominator included `smoke-test.yml`, which runs `--check` and regenerates
nothing. The conclusion is unchanged, and the proposed gate is still unbuilt.

**2026-09-19, later — the workflow fix merged, and the roster PR's SECOND red
was a different gate doing its job.** #1049 merged at 20:29 UTC, so
`update-ia-supervisor-roster.yml` now regenerates llms.txt and next week's run
will not repeat tonight's first failure.

With llms.txt fixed, #1048's run got further and failed on
`check_roster_retention.py` — Bremer (017) and Hamilton (079) VANISHED, three
records each, with the gate's own instruction: *GO AND LOOK AT THE PAGE before
accepting this.* **TWO GATES FAILED ON ONE PR FOR TWO UNRELATED REASONS, and
assuming the second was the first would have been wrong twice in one evening.**

*Went and looked*, with `robots_policy.fetch_verdict`, reading robots.txt only
and never the refused pages, on both host spellings of each. Bremer answers
HTTP 500 on /robots.txt — disallow-all under RFC 9309 and this project's own
rule. Hamilton's /robots.txt redirects to
`cms2.revize.com/revize/hamiltonia/robots.txt`, a PER-TENANT path and so
Hamilton's own file rather than its CMS vendor's, whose `Disallow: /` at line 18
is the longest match for /. Neither county stopped publishing; this project
declines to read them. That is the Palo case already in `ACCEPTED_DROPS`, and
the builder already carries both in `ROBOTS_REFUSED_DROPS`, which is why the run
SUCCEEDED while dropping them.

**Carrying the last-known supervisors forward is ruled out elsewhere rather than
decided here**: `build_ia_county_chair.py`'s carry-forward takes `unreachable`
and never a refusal, asserted by its own `--selftest`. Bremer's 500 is a robots
file that could not be read, not a page that could not be fetched; either way
the decision is to decline, so nothing may be carried.

**AN ORDERING TRAP, MEASURED BEFORE IT COST ANYTHING.** The obvious move was a
separate PR putting those entries on main. It would have been red by
construction: on main the roster still carries both counties, and the gate's own
stale-audit reads that and fails — "is STALE — the source `017` is back with 3
record(s)". An accepted drop is only valid on the tree that already lost the
source, which is why the Palo and Adams entries each landed in the change that
caused their drop. The entries ride #1048 (`e859550`) and must not be ported.

**#1048 is still NOT merged and is not mine to merge** — officeholder data,
human review. Two commits of mine are on its branch to clear the two failures;
if a re-run force-pushes that branch both are discarded and both failures
return.

*Unchanged and still proposed:* the `build_llms_txt.py --check` gate that would
catch the other 60 workflows, and the two `SyntaxWarning`s in
`build_county_pages.py`. Neither is started.

**2026-09-19 — the supervisor run passed, the prediction held exactly, and its
bot PR went red for a reason nobody was watching for.** The weekly job started
19:30 UTC and SUCCEEDED: 15 Plan 3 counties, 61 districts. Mitchell keyed 5 of 5
off its restored host, Bremer (3) and Hamilton (3) left on the robots refusals
already recorded in `ROBOTS_REFUSED_DROPS`, and `bremer.html` and
`hamilton.html` were deleted. No name changed and no seat moved. That is the
full rebuild I did this morning, produced by the job rather than by me, and the
roster is unfrozen for the first time since 2026-08-28. It is **PR #1048 and I
have not merged it** — officeholder data, human review.

**The red was `build_llms_txt.py --check`, and reading it rather than assuming
Mitchell is what found a real hole.** `llms.txt` COUNTS the per-county board
pages; dropping two took the fleet from 220 to 218 and Iowa's own line from 17
to 15, and `update-ia-supervisor-roster.yml` regenerates the county pages,
about.html and the sitemap but not the file that states the count. Measured
rather than inferred: main at `0e829be` is green at 220, so the failure is the
change's own and not inherited; on the bot branch `--check` FAILs, the builder
fixes it, `--check` passes. Fixed in **#1049** (Iowa's workflow, mirroring
Michigan's), and #1048 carries a separate commit regenerating the file so this
week's roster is reviewable green.

**The wider finding, and it is the same shape this repo keeps hitting.**
`update-mi-commissioner-roster.yml` has carried this exact step and this exact
reason since Michigan hit it — "the builder tolerates two going dark, so it can
happen on an ordinary weekly run" — and it was fixed in that one workflow and
recorded nowhere else. **61 of the 63 workflows that regenerate county pages
still lack the step, and no gate asks them to**: `build_county_pages.py --check`
fails a workflow that does not regenerate ITS pages, and nothing does the same
for llms.txt. Not every one of the 61 can move the count — only a workflow whose
roster can gain or lose a whole county can — so the number at risk is smaller
than 61 and was not measured per workflow.

*Proposed, not built:* the recurrence-proof fix is a GATE in
`build_llms_txt.py --check` of the shape `build_county_pages.py --check`
already has, which catches all 61 without 61 edits and cannot go stale as
workflows are added. Cost: one gate, plus whatever workflows it flags on its
first run — an unknown number of one-line YAML edits across four instances.
The alternative is to keep fixing them one at a time as each goes red, which is
what produced tonight. Recommendation: write the gate. Not started; it edits
other instances' workflows and nothing asked for it.

*Also found, smaller, not fixed:* `scripts/build_county_pages.py` emits two
`SyntaxWarning`s on the runner's CPython 3.14 — `\.` and `\s` in docstrings at
lines 1465 and 1693 (Python 3.11 files the same two as silent
`DeprecationWarning`s, which is why they surfaced only when the runner moved).
Cosmetic, and printed twice per run in 63 workflows plus every CI run. The fix
is two `r` prefixes.

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
