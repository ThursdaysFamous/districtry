# Illinois board

Owner session: **Illinois**. Manager owns *Tasks*; this session owns *Status*
and *Open questions*. Rules and reporting posture: `BOARD.md` at the repo root.
Commit board edits straight to main, in their own commit, dated.

## What a reader gets today

Click any point in Illinois and the app answers from **40 layers**. **93 of the
state's 102 counties** are in the coverage ring, all of them on the dispatch
tier. The statewide layers (county, township, municipality, school district,
ZIP) answer anywhere in Illinois.

**104 recorded gaps** — 71 no-source, 24 data-quality, 9 blocked. That is by far
the largest gap list in the fleet, and it is a consequence of being the deepest
instance rather than the worst-maintained one.

## Tasks — manager owns this section

| task | state | opened | notes |
|---|---|---|---|
| **Hancock's weekly roster PR ships a corrupted name (#1018) — HELD, not merged** | **open, second** | 2026-09-19 | `Jo0n Mason` carries a zero where an `h` belongs. `Alex Blythe` → `Billy Cramer` lands in the same run and is suspect for that reason alone. The builder's only drift guard is the member COUNT — fifteen in, fifteen out — which is the Rock Island shape. Find the cause: read what the county is serving now, establish whether one name is wrong or both, fix the parser. **Do not hand-correct `Jo0n` to `John`** — a slipped parser makes the surname as suspect as the given name, and repairing a guess produces a more convincing guess. #1025's gate now refuses it (`digits in it`), so a rebase should turn that PR red. |
| Reddick Fire lost its office address and phone (#1023, merged) | open | 2026-09-19 | Merged because the filing moved `filedFor` 2025 → 2026, so it is a NEW Annual Financial Report rather than a re-parse of the same one, and a sparser form is what that source legitimately produces. But a reader who clicked Reddick Fire yesterday saw an address and a phone and today sees neither, and SUE BERGAN moved Treasurer → C.E.O. while ROBERT LOWERY left entirely. Worth one look at the actual filing to confirm the district filed it that way. |
| **#1025 and #1028 collide with no git conflict — merge order matters** | **blocking** | 2026-09-19 | Found by this session and verified by the manager on both branches. #1025's `ACCEPTED_NAMES` excuses Bartonville's `’s Email: clerk@bartonville.org`; #1028 deletes exactly that value; different files, so git reports nothing. Either order leaves main failing `validate_officeholder_names.py` on "stale, remove it". Order: **#1028 first, then drop the Bartonville entry from #1025 before it merges.** The edit is NYC/SF's to make — routed to them 2026-09-19. Illinois offered and correctly did not touch another session's branch. |
| Bartonville's phantom Clerk (#1028) | in review | 2026-09-19 | Fixes the parse first, then widens the guard. Removes one fabricated name a reader can see today. Merge this before #1025. |
| Six roster workflows: shared pages after the branch cut (#1030) | in review | 2026-09-19 | Stops weekly jobs dying when another workflow merges mid-crawl, and deepens the checkout so sitemap dates are real. |
| **Will County: move it from `REQUIRED_COUNTIES` into `PRESERVABLE`** (#982, #996, #1026) | **assigned, do first** | 2026-09-19 | Adam's ruling, 2026-09-19: "Add will county to the exception list so the remaining workflow can continue." The block itself is unchanged and is never worked around — what changes is that it stops withholding 36 other counties' turnover. Two edits: the `PRESERVABLE` entry, and the workflow's build step, which gates on `scrape_will.outcome == 'success'` and so never runs. Cook stays required. The cost is real and gets stated rather than smoothed: a preserved full-body county means a Will council member who changes stays stale, and no count floor notices. Ask 28 stays drafted and unsent. |
| Plattville's Clerk ships as `Beth Fals 56` | open | 2026-08-01 | **Corrected 2026-09-19:** this board first said the value was held in `ACCEPTED_NAMES`. It is not — that table arrives with #1025 and is not on main, so the name is simply shipping and has been since 2026-08-01. Must be **dropped, not repaired** to `Beth Fals` — the Douglas County rule. |
| General Assembly roster is stale | open | 2026-09-19 | Raised by this session; the manager had it nowhere. Measured on main: `il-house-members.json` last moved 2026-09-08, `il-senate-members.json` 2026-09-02. Its workflow failed on 09-14 and was fixed on 09-18, so the next scheduled run is the first test. Reader-facing — these are the people on the state House and Senate cards. |
| Logan County's 11 municipalities and 65 officials are frozen | blocked | — | The county's own robots.txt disallows the directory the Clerk's yearbook sits under. That is the host's answer. |
| 2 of 64 districted board cards name no office | open | 2026-09-15 | Down from 50 on 2026-09-06. The long tail. |

## Status — this session owns this section

**2026-09-19, 16:45. #1018: THE PARSER IS NOT AT FAULT, AND THE PREMISE IN THE
TASK ROW IS WRONG.** The row reads "the page moved under the parser". It did
not. Measured, with robots read first through `robots_policy.py` as the
scraper's own client (allowed, no crawl delay, no Content-Signal):

- Running `hancock_county_board_scraper.py` against the live page reproduces
  the bot PR **exactly** — 5 districts, 15 members, twelve names unchanged.
- The page itself prints **`Jo0n Mason (R)`**, one occurrence. The zero is the
  COUNTY'S OWN TYPO, not a corruption this repo introduced.
- `Josh Turner` and `Alex Blythe` appear **zero times** on the page. So these
  are two genuine roster changes, not a mis-association.
- The parser reads one `<li>` per member. There is no column association to
  slip, which is what makes this NOT the Rock Island shape.

**`ACCEPTED_NAMES` IS RULED OUT BY ITS OWN RULE.** That table's docstring says
in terms: "NEITHER REASON IS 'the source publishes it that way'." This is
exactly that, so an entry there would be the one thing it forbids.

**THE CERTIFIED RETURNS DEEPEN IT RATHER THAN SETTLING IT.** Hancock's own
results database (`electionstats.hancockcounty-il.gov`, `/candidates/search/`,
param `name`) says: Billy Cramer has **no county board contest ever** — he is a
Pilot Grove Township trustee, 2021 and 2025. No Mason has run in District 4;
Kelly Mason ran in District **1** in 2024. And **Joshua L. Turner won the 2026
District 4 Republican primary**, so the man the page just dropped is its
nominee for November.

That is consistent with two mid-term APPOINTMENTS, which no election record
would ever show — and it is equally consistent with the county having edited
its page wrongly. **The returns cannot distinguish those two**, which is
precisely why this needs the county rather than more inference.

**So nothing ships and #1018 stays held.** Shipping `John Mason` guesses at a
real person's name; `Jo0n Mason` is refused by the merged name gate and is a
typo either way; `Josh Turner` would name someone the county no longer lists.
The route is an ask to `elections@hancockcounty-il.gov` — the address the
county publishes — on two questions: the District 4 member's correct name, and
whether Billy Cramer holds District 2. **Drafted next; Adam sends, never this
session.**

**2026-09-19, 16:20.** THE FREEZE IS OVER, PROVED BY A RUN RATHER THAN BY THE
DIFF. #1043 is green, and the municipal workflow dispatched by hand against its
branch (run 35453832897) succeeded at 16:15 — but success is what that workflow
reported for eleven days while refusing to build, so the log is the evidence
and not the conclusion. It shows the build step running, the roster changing,
and a bot PR opening:
[#1044](https://github.com/ThursdaysFamous/districtry/pull/1044), 328
insertions and 155 deletions.

Its body carries the line this change existed to produce:

    PRESERVED (blocked this run, carried forward from the shipped roster):
    joliet 1, kendall 6, logan 11, mchenry 27, will 31

**`will 31` — the exact count measured before the change.** Diffed entry by
entry against main: 629 municipalities before and after, none dropped, **48
changed across five counties** — DuPage 17, Rock Island 15, Livingston 14,
Mason 1, Kendall 1. Will, McHenry and Logan each show **0 changed**, which is
preservation doing precisely what was claimed for it.

**The one entry that looked like a counter-example is not.** Kendall is
preserved and yet one of its six municipalities moved: Plano's `board` went
from `null` to eight named aldermen with a city e-mail each. That is the
`--enrich` path, not the county path — Plano's own city payload runs fresh and
can only FILL a field the county left empty. Kendall's six county entries were
carried forward untouched. A preserved county's data was never rewritten;
checking that specifically is what turns the safety argument into a
measurement.

**2026-09-19, afternoon.** [#1043](https://github.com/ThursdaysFamous/districtry/pull/1043)
opens: Will moves from `REQUIRED_COUNTIES` to `PRESERVABLE`, so the municipal
roster refreshes again for the first time since 8 September. Adam approved it
directly. 14 gates pass.

**What a reader gets back:** 36 counties' mayors, presidents and council
members start being rechecked weekly again. They had been eleven days stale
because Will's Clerk moved its directory behind a managed challenge and Will
was one of two counties the builder refused to build without — so every weekly
run scraped all 37 sources, skipped the build on Will alone, and reported
success. Nothing went red for eleven days.

**What a reader loses, and it is said on the card's own gap record rather than
here:** Will's own 31 towns now carry forward indefinitely. A trustee who
changes will not change here, and no count floor will notice, because all 31
municipalities remain. The gap's `area` narrows from "every Illinois town card"
to Will County alone, because the wider claim stopped being true.

**The measurement, in case it is questioned later:** the comment that held Will
in `REQUIRED_COUNTIES` described building WITHOUT a full-body county and was
applied to PRESERVING one. Preserved entries re-enter through the same
`absorb()` -> `pick_entry`, which sorts on depth then `COUNTY_PRECEDENCE`, so
order cannot demote anything. All 31 Will entries are at maximum depth and Will
ranks second behind Cook, so its 28 straddles resolve exactly as they do today
— the six it loses to Cook it already loses.

**Owed and not paid:** `.claude/skills/municipal-officials/SKILL.md` still says
`REQUIRED_COUNTIES` is "Cook and Will only", in the body and in its Nevers.
Every edit to that file was refused by this environment's permission
classifier, so it is stale and flagged rather than quietly skipped.
`validate_skills.py` cannot catch it — it checks that a named path or
identifier exists, not that the prose is true. It needs one line from a session
that can write the file.

**Next:** #1018's cause (Hancock's `Jo0n Mason`, never hand-corrected), then
Marshall's weekly job, whose fix merged in #968 after its last failing run, so
the honest state is "fixed, unproven" until it next fires.

**2026-09-19, end of the evening.** Pausing here. Main is `8506c8c`. Three
Illinois changes merged tonight — #1024 (Rock Island's 112 fabricated names),
#1028 (Bartonville's phantom Clerk) and #1030 (the six workflows) — alongside
#1031, #1025 and #1023.

**No reader is seeing Hancock's corrupted name.** Checked on main: the shipped
`hancock-county-board-members.json` names all fifteen members correctly,
`Josh Turner` and `Alex Blythe` among them. The corruption exists only in the
held bot PR #1018, which is the hold working.

**Next thing I would pick up: the cause behind #1018.** The merged name gate
answers `digits in it` for `Jo0n Mason`, so rebasing that PR turns it red, which
is the gate doing its job and not the question. The question is what
`hancockcounty-il.gov` is serving now. Two simultaneous name changes on a
fifteen-seat board, one of them with a zero where an `h` belongs, reads like the
page moved under the parser rather than like two members being replaced — so
`Alex Blythe` → `Billy Cramer` is suspect for the same reason, and `Billy Cramer`
passes every gate we have. The builder's only drift guard is the member count,
five districts of three, which a mis-associated parse satisfies exactly. This is
the Rock Island shape again and it wants the parser diagnosed, never `Jo0n`
hand-corrected to `John`: if the parse slipped, the surname is as suspect as the
given name, and repairing a guess produces a more convincing guess.

**2026-09-19, later still.** #1030 merged (`5338913`), so both Illinois PRs are
in and nothing from this session is in review. Verified on main: all six roster
workflows now run **zero** shared-page generators before the branch cut and run
them after, every checkout carries `fetch-depth: 0`, and all 131 workflow files
parse. Wisconsin's equivalent (#1031) landed straight after.

What this fixes for a reader is indirect but real: those six weekly jobs were
dying whenever another workflow merged a shared page mid-crawl, and a job that
dies opens no pull request, so the roster it refreshes silently stayed frozen.
It also stops every bot roster PR rewriting all 243 sitemap dates — the shallow
checkout made every page claim it changed that day.

**2026-09-19, later.** #1028 merged (`d450c52`). Verified on main: 4,332 person
records in `il/data/app/municipal-officials.json`, **zero** that fail
`fabricated_name`, and the string `clerk@bartonville.org` appears nowhere in
the file. Bartonville's phantom second Clerk is gone from what a reader
downloads.

**The #1025 collision predicted below is now live and measured.** Running that
branch's `validate_officeholder_names.py` against merged main:

    validate_officeholder_names: FAIL
      - ACCEPTED_NAMES excuses '’s Email: clerk@bartonville.org' in
        il/data/app/municipal-officials.json and that value is no longer there
        — stale, remove it

That is the gate working exactly as designed: an exception cannot outlive the
fix that retires it. The fix is to delete that one `ACCEPTED_NAMES` entry from
#1025 before it merges; its Plattville entry stays, because `Beth Fals 56` is
still shipping. I have told the NYC/SF session and have not touched their
branch.

**2026-09-19.** Nothing in progress. Both Illinois PRs are in review and green,
and I am not opening a third until they land or Adam picks the next item.

**#1025 and #1028 collide, and git shows no conflict because they touch
different files.** #1025 records Bartonville's `’s Email: clerk@bartonville.org`
in `ACCEPTED_NAMES`, and its `audit_accepted()` fails when an excused value is
no longer in the file — "stale, remove it". #1028 removes exactly that value.
So merging both, in either order, leaves main failing
`validate_officeholder_names.py` until that one entry is deleted. Simplest
order is #1028 first, then drop the Bartonville entry from #1025 before it
merges. I can make that edit on #1025's branch if the NYC/SF session would
rather not.

**Correction to the Tasks table:** `ACCEPTED_NAMES` is not on main — it arrives
with #1025. Plattville's `Beth Fals 56` is held nowhere today; it is simply
shipping, and has been since 2026-08-01.

**What a reader is missing right now**, in order of how many people it reaches:

- **Municipal officials are eleven days old.** The roster naming the mayors,
  presidents and council members of 37 counties' cities and villages last
  rebuilt on 2026-09-08. Will County is one of two counties the builder refuses
  to build without, and its directory sits behind a vendor managed challenge we
  do not work around. Every weekly run scrapes the other sources, refuses the
  build, and reports success, so nothing goes red. Ask 28 is the only route and
  it is drafted, unsent.
- **Logan County's 11 municipalities and 65 officials are frozen** by that
  county's own robots.txt, which disallows the directory the Clerk's yearbook
  sits in (#1027). Compliance, not an outage — the check re-runs weekly and
  resumes on its own if the policy changes. Ask 23 is drafted, unsent.
- **The General Assembly roster has not refreshed since 2026-09-08** (House) or
  **2026-09-01** (Senate). `update-ilga-roster.yml` failed on 09-14 and its code
  was fixed on 09-18, so its next scheduled run is the first thing to test it.
  Not chasing it before then.

Nothing else on the Illinois map is known to be wrong. The coverage ring checks
out at five rings with all 93 inside and 10 outside anchors correct; 62 of the
64 districted board cards name an office; 83 county pages name 1,108 board
members; 55 counties have their precincts drawn.

**Stale record found, not yet fixed.** `docs/ASK_DRAFTS.md` Ask 12 still lists
Christian County as owing a second follow-up about which precinct Taylorville 9
was carved from. That question was answered on 2026-09-15 by the county's own
registration counts and Christian has shipped, so the row should read OVERTAKEN
the way Knox's already does. The same file and the Christian gap record also
disagree on the clerk's first name — Jodie in the drafts, Kandi in the
guidebook — and neither is guessed at.

## Open questions for Adam

- **Thirteen Illinois asks are drafted and waiting on you to send them** — Asks
  2, 9, 10, 11, 13, 16, 18, 19, 21, 23, 26, 27 and 28 in `docs/ASK_DRAFTS.md`,
  of which 18 and 19 you deliberately held. **Ask 28, to the Will County Clerk,
  is the one with a consequence today**: it is the only route to unfreezing the
  municipal roster above.
- **Two second follow-ups are past due** (Ask 12): Ford and Piatt, each asked
  3 August with one follow-up spent on 16 August. Christian's row in that table
  is overtaken and Knox's already says do not send.
- **Bureau County wants $150 and a licence whose terms forbid republishing what
  we would build with it.** Ask 9 asks for modified permission and offers the
  free fallback in the same note. Purchases are yours alone; nothing has been
  spent and nothing is queued.
