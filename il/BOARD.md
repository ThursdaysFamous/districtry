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
| **#1025 and #1028 collide with no git conflict — merge order matters** | **blocking** | 2026-09-19 | Found by this session and verified by the manager on both branches. #1025's `ACCEPTED_NAMES` excuses Bartonville's `’s Email: clerk@bartonville.org`; #1028 deletes exactly that value; different files, so git reports nothing. Either order leaves main failing `validate_officeholder_names.py` on "stale, remove it". Order: **#1028 first, then drop the Bartonville entry from #1025 before it merges.** The edit is NYC/SF's to make — routed to them 2026-09-19. Illinois offered and correctly did not touch another session's branch. |
| Bartonville's phantom Clerk (#1028) | in review | 2026-09-19 | Fixes the parse first, then widens the guard. Removes one fabricated name a reader can see today. Merge this before #1025. |
| Six roster workflows: shared pages after the branch cut (#1030) | in review | 2026-09-19 | Stops weekly jobs dying when another workflow merges mid-crawl, and deepens the checkout so sitemap dates are real. |
| Will County municipal directory is blocked (#982, #996, #1026) | blocked | 2026-09-08 | The county's directory sits behind a vendor managed challenge. Will is in `REQUIRED_COUNTIES`, so the **whole** municipal roster has not rebuilt since 2026-09-08 — 37 counties' mayors and council members are eleven days old, and every weekly run refuses the build and reports success, so nothing goes red. Ask 28 is the only route and is drafted, unsent. Never worked around. |
| Plattville's Clerk ships as `Beth Fals 56` | open | 2026-08-01 | **Corrected 2026-09-19:** this board first said the value was held in `ACCEPTED_NAMES`. It is not — that table arrives with #1025 and is not on main, so the name is simply shipping and has been since 2026-08-01. Must be **dropped, not repaired** to `Beth Fals` — the Douglas County rule. |
| General Assembly roster is stale | open | 2026-09-19 | Raised by this session; the manager had it nowhere. Measured on main: `il-house-members.json` last moved 2026-09-08, `il-senate-members.json` 2026-09-02. Its workflow failed on 09-14 and was fixed on 09-18, so the next scheduled run is the first test. Reader-facing — these are the people on the state House and Senate cards. |
| Logan County's 11 municipalities and 65 officials are frozen | blocked | — | The county's own robots.txt disallows the directory the Clerk's yearbook sits under. That is the host's answer. |
| 2 of 64 districted board cards name no office | open | 2026-09-15 | Down from 50 on 2026-09-06. The long tail. |

## Status — this session owns this section

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
