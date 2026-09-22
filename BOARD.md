# districtry fleet board

**What this is.** One board per instance, plus this one for work that belongs to
no single state. It exists so the project's state lives in a file Adam can read
rather than in a session's head.

**How it works.**

- **Two owners, two sections.** The manager session owns *Tasks*. The state's
  own session owns *Status* and *Open questions*. Neither edits the other's
  section, because two writers on one paragraph is a merge conflict every time.
- **Board updates commit STRAIGHT TO MAIN**, in their own commit, never inside a
  feature PR. A board that waits for a PR to merge is stale for as long as that
  PR sits open, which defeats the point. Prose only — no data file, no generated
  region, nothing a gate reads.
- **A session updates its board in the same turn it finishes a piece of work.**
  Every entry carries a date. A board nobody updates is worse than no board:
  that is how `ia/WATCH.md` came to say the chair roster covers 43 counties when
  it covers 38.
- **No generator and no CI gate**, deliberately. This is hand-written markdown
  until it earns machinery. The manager reports a stale board to Adam rather
  than failing anyone's merge over it.
- **A question goes in Open questions, never into a session's own chat.**
  Adam's instruction, 2026-09-19: questions are "sent to their boards for you to
  invest and bring to my attention here". Adam does not read the state sessions;
  he reads the manager session. A question asked in a session's own turn is a
  question nobody answers, and it stalls that session while looking like
  progress. Write it dated, with what was measured, what the options are, what
  each costs, and which the session would pick — a question carrying a
  recommendation is far easier to answer than an open one. The manager settles
  what it can and puts the rest to Adam. A question that blocks everything says
  the word **blocking**, and is escalated rather than waiting for the next board
  pass.
- **The manager merges the state sessions' PRs.** Standing authority from Adam,
  2026-09-19, and his instruction to the sessions to accept it. No session waits
  on him for a pull request and none asks per PR. It lowers no bar: every merge
  is verified on the MERGED tree rather than from a PR body, and a PR that
  cannot be verified is held and reported. Holds are the mechanism working —
  #1018 is held because a bot shipped a name with a zero in it. It is not
  authority for a session to merge its own PR. Adam's own SEO and branding
  session is outside all of this, as it always was.

**Reporting.** The manager reports to Adam what changed **for a reader of the
site**. CI plumbing, gate counts and session bookkeeping are not reported unless
they are blocking something.

| board | instance | session |
|---|---|---|
| `il/BOARD.md` | Illinois | Illinois |
| `wi/BOARD.md` | Wisconsin | Wisconsin |
| `ia/BOARD.md` | Iowa | Iowa |
| `mi/BOARD.md` | Michigan | Michigan |
| `ny/BOARD.md` | New York City | New York |
| `ca/BOARD.md` | San Francisco | **none — no work in progress** |

Six instances, five sessions, one instance each. **San Francisco has no session
because no work is being done on it** — that is a deliberate state, not a gap,
and its board says so. A session gets assigned when there is work.

**Two corrections, both 2026-09-19, both from Adam.** This table first said Iowa
had no session; it does (`session_01GDDwuCzmWxgdbz3V8GHrjJ`, running since
2026-08-27), and the manager inferred its absence from a session listing that
omitted it — the one thing `docs/MANAGER.md` already says never to do. Query the
id; a listing that does not show a session is not evidence the session is gone.
The table then paired one session with both `ny/` and `ca/`; that session's
scope is **New York only**.

---

## Tasks — cross-cutting work, manager owns this section

Work here belongs to no single state. A task that lives inside one instance
belongs on that instance's board instead.

| task | owner | state | opened |
|---|---|---|---|
| Roster workflows: regenerate shared pages after the branch cut | IL + WI | **merged** #1030 `5338913`, #1031 `f2a0d88` | 2026-09-19 |
| Absolute gate on every shipped officeholder name | New York | **merged** #1025 `a3d11c0` | 2026-09-19 |
| #1025 and #1028 collided with no git conflict. | New York | **closed** — New York merged main in first and measured all four states rather than dropping the entry blind, so the branch was correct in either merge order | 2026-09-19 |
| `privacy.html` understated three events sent through `shareCopyButton` | manager | **merged** #1046 `dd5ce05` — the page named ten events while every app sends thirteen. An unreadable `trackEvent` call is now an ERROR rather than a skip; resolution follows one hop and fails naming the line otherwise. Coordinate events stay at two: these three send a name and nothing else | 2026-09-18 |
| Shallow checkout makes every roster PR rewrite all 243 sitemap dates | manager | **merged** — 73 workflows deepened and `scripts/validate_workflow_checkout.py` is on main, failing any workflow that commits `sitemap.xml` without full history or re-shallows it afterwards | 2026-09-19 |
| A scheduled workflow that has NEVER run is invisible to every gate here | manager | **closed — measured** | 2026-09-19 | Swept across all six instances: of 128 scheduled workflows only two have never run, and the calendar explains both. Michigan raised it as a class of blind spot and it is real, but the fleet has no instance of it today, so nothing is built. Re-measure if the count ever moves. |
| The six-pointed star is Chicago's and five apps were wearing it | manager | **merged** #1056 `e903810` | 2026-09-20 | Adam: "SF should adopt the standard pin. The star is reserved for Chicago." Measured, SF was not the only one. The star reached THREE surfaces per app — masthead wordmark, empty-state glyph, map pin — and Illinois had already settled the pin for itself (flag star inside Chicago only, blue circle everywhere else). wi/ia/mi had followed on the pin; SF had not; NOBODY had followed on the wordmark, so Chicago's flag emblem was the masthead glyph of four unrelated apps. It was also broken beyond branding: the shared dark-map rule reaches a `<circle>` only, so SF's star and NYC's teardrop were one colour in both themes. Now ca/wi/ia/mi take the teardrop for wordmark and empty state, ca and ny take the fleet circle as the pin, Illinois untouched. Verified in Chromium on main, seven points, both themes. |
| A cloned instance file keeps the original's text and nothing checks it | manager | open | 2026-09-20 | THIRD occurrence. `mi/sources.html` served Iowa's whole identity block; Michigan's commissioner roster cloned a parser that shipped zero districts; and #1056 found Iowa's and Michigan's map-marker comments were Wisconsin's verbatim — "means nothing in Wisconsin" — sitting in two other states' code. Each was found by a person reading, weeks apart, and each was fixed one at a time. `page_consistency_test.mjs` gained the canonical/og:url check after the first, which catches an identity block and nothing else. The general shape is a cloned file keeping a claim about the instance it came from; a comment is harmless and a canonical is not, so the question is what class is worth a gate rather than whether to fix a fourth by hand. Not started, and not urgent — boarded so the fourth one is recognised as a pattern rather than a surprise. |
| **How the manager wakes a state session, when `SendMessage` cannot** | manager | **closed — route found and used 2026-09-21** | 2026-09-21 | **CORRECTED the same day: the earlier row said the sessions could not be woken at all, and that was wrong about the fleet while being right about one tool.** All five state sessions are IDLE and healthy — Illinois `session_01TifBPZMzrNEir2idEUqro2`, Wisconsin `session_012JWArkaHs7hGqRHxkjGoKw`, Iowa `session_01GDDwuCzmWxgdbz3V8GHrjJ`, Michigan `session_013TPP9BCk1NnjK5EfTUfvGm`, New York `session_01HzrNZpsGsGwVHNh8Wgj9Mb`, each queried by id rather than inferred from a listing. What is missing is the channel: this session has no cross-session send available today, `ListAgents` reports no reachable peer, and a send by id and by name both fail. So the assignments are written into each board's Tasks table instead, which is where a session reads its marching orders on resume, and Adam nudges each session for it to pick them up. `SendMessage` and `ListAgents` reach peers on THIS machine, and the state sessions are cloud sessions, so both report no reachable agent and a send by id or by name fails. That is a fact about one channel, not about the sessions. **The route that works is a Routine bound to a session:** `create_trigger` with `persistent_session_id` and the assignment as its prompt, no cron and no `run_once_at`, then `fire_trigger` to deliver it immediately. All five were woken this way at 18:50 UTC, each call returning the target session id, and Illinois's record confirmed delivery — `updated_at` moved to the firing second, `unread` true, worker epoch 192 to 193. **Starting fresh sessions was still the wrong answer and stays the wrong answer**: Illinois carries 634k tokens of context and Wisconsin 502k, and a second owner on one instance is the failure this board records from 2026-09-19. The assignments also live on each board, which is where a session reads them on resume, so the two routes agree rather than competing. |
| `llms.txt` counts the per-county pages and 60 of 62 refresh workflows do not regenerate it | manager | open | 2026-09-19 | Found by Iowa when its own weekly run went red on a file it never touched. `llms.txt` states the page count, a county dropping out moves it, and only Michigan's and Iowa's workflows rebuild it. Iowa fixed its own and boarded the general case rather than editing four instances' workflows unasked, which was right. The recurrence-proof fix is a GATE — `build_county_pages.py --check` already fails a workflow that does not regenerate its own pages, and nothing does the same for `llms.txt`. Counted here as 60 of 62 rather than Iowa's 61 of 63: their denominator included `smoke-test.yml`, which runs `--check` and regenerates nothing. |

## Status — manager writes here

**2026-09-19, third pass. The open-PR queue is empty but for one hold.** Adam
asked for the open PRs to be merged; two of the three went in, verified on a
tree with `origin/main` merged rather than from a PR body.

- **New York is statewide (#1042).** A reader in Albany or Buffalo typing their
  address at the front door is now routed to `/ny/` with the point selected,
  instead of being told they are outside everywhere districtry covers. The app
  opens on the state rather than the harbour, an upstate `#point=` link
  resolves, and it calls itself districtry New York. Re-measured here: the
  shipped bbox is wider than the widest shipped geometry on all four sides, so
  nothing is clipped, and every sibling instance's `METRO_EXPLORERS` table
  learned the new box — without that, an upstate address typed into the
  Wisconsin app would not have been offered New York at all.
- **Michigan's board probe records the robots reading for the host it accepts
  (#1045).** Both of its load-bearing claims were negative-tested here rather
  than read: deleting one record's robots reading makes `--check` name the
  affected records and exit 1, and `--check` runs clean with a `requests` that
  raises on import. The gate-count pair is the merged tree's own measurement,
  67/94, not either branch's.
- **#1018 is held and the hold is now Adam's to clear.** See question 2.
- **The preserve ruling is live for a reader, and the same guard caught a second case an hour later.**
  Iowa's weekly run re-ran through the new builder (#1048, `bb1676e`): all 17 counties ship, Bremer and
  Hamilton carried forward with their three supervisors each, and **not one of the 67 names changed** —
  checked rather than assumed. Their two pages now tell a reader plainly: *"last read 2026-08-28 and no
  longer re-read… These names will go out of date."* Every still-read county keeps the scheduled sentence.
- **Michigan's weekly run then proposed deleting Delta and Otsego — 14 commissioners — and is HELD (#1052).**
  Not the Iowa case: I read both counties' robots.txt with this repo's own reader as the scraper's client,
  and **neither refuses us**; both board pages answer HTTP 200 at ~109 KB and still name their
  commissioners. Nothing at either source changed. That makes it a scraper defect, routed to Michigan with
  the evidence and with three things not to do — no `ACCEPTED_DROPS` entry, no merge on a re-run that
  happens to come back green, no lowering the guard.
- **The Detroit roster PR now says what its run moved (#1047).** Its weekly PR opened with the
  same sentence every week — "this changes data about real officeholders" — and on both of the
  two refreshes that have ever happened, the only thing that moved was an Archive timestamp. A
  body that cries officeholder every week is how a reviewer learns to skim the week it matters.
  The summariser refuses to claim nothing moved about a document it has not fully accounted for,
  which I negative-tested: an unrecognised field produced "fields this summary cannot name"
  rather than a clean bill. It also found that detroitmi.gov served this client directly on
  2026-09-09, so the block is intermittent where four places called it standing.
- **The queue being empty is why #1046 exists.** With nothing left to review I took the one open
  unassigned task: the privacy page named ten analytics events while every app sends thirteen.

**Manager's own work.** The shallow-checkout defect Wisconsin recorded as
fleet-wide was 73 workflows wide, not twelve; every one is deepened and
`validate_workflow_checkout.py` now fails a workflow that commits `sitemap.xml`
without full history or that re-shallows it afterwards. `docs/MANAGER.md`
records the standing merge authority. Michigan's "a workflow that has never run
is invisible to every gate" was swept across all six instances: of 128
scheduled workflows only two have never run, both explained by the calendar.

Main is at `bb1676e`. Open: #1018 held (Hancock), #1048 held (see question 4). #1049 merged.

**#1048 is no longer red for the reason its own PR body gives.** That body names
`build_llms_txt.py --check`, which was true when it opened; Iowa's own regeneration commit
fixed that half, and the run's log ends in `check_roster_retention.py` and exit 1. So the
gate now refusing the merge is the one that objects to two counties vanishing — which is
question 4 exactly, and is the gate working rather than an obstacle to clear.

## Open questions for Adam

**1. Is "5 boroughs" still the right scope line for New York?** Not blocking.
Raised by the New York session on its own board and carried here unchanged,
because it is now visible on the live front door: the landing page renders
**New York · 5 boroughs** beside **Wisconsin · all 72 counties**, while 15 of
New York's 33 layers answer everywhere in the state and a click in Buffalo
returns seven cards naming real officeholders. The coverage map tells the
two-tier story correctly — a dashed state wash over a solid five-borough fill —
so the map and the scope line now say different things. Three options: leave
it, which understates the instance on the one line most readers see; "statewide,
5 boroughs in depth", honest about both tiers but the only scope string in the
fleet that is not a count; or "all 62 counties", which matches the other
statewide instances and overstates, because no county tier exists yet and the
county card names nobody. **The session would take the middle one and so would
I** — the rule being protected is "never claim a county tier you do not have",
and naming both tiers keeps that.

**2. Hancock needs an e-mail, and only you can send it.** Not blocking anything
else. #1018 is a weekly roster PR that would ship `Jo0n Mason` — a zero where an
`h` belongs — and replace `Alex Blythe` with `Billy Cramer` in the same run. The
Illinois session measured it properly and my first reading of it was wrong: the
parser is fine, the county's own page prints the zero, and the two replaced
names appear on that page zero times, so these are real edits by the county.
The certified returns make it stranger rather than clearer — Billy Cramer has
never run for county board, and Joshua L. Turner, the man the page just dropped,
won the 2026 District 4 Republican primary. That fits two mid-term appointments
and it fits a county page edited wrongly, and nothing published can tell them
apart. Every repair available to us is a guess at a real person's name, so
nothing ships. The ask is two questions to `elections@hancockcounty-il.gov`:
the District 4 member's correct name, and whether Billy Cramer holds District 2.
Illinois drafts it. **Meanwhile main names all fifteen Hancock members
correctly, so no reader sees any of this.**

**4. CLOSED 2026-09-19 — a refusal stops the fetch and never unpublishes, and Iowa's builder now does it.**

**A correction to what I told Adam about this, twice.** I reported that two Iowa counties "came off the site" and that six named supervisors and two county pages were lost. **They were not.** #1048 is a bot PR that has never been merged; main has carried Bremer and Hamilton with all six names and both county pages throughout, verified against the shipped roster and the file's own git log. What happened is that a weekly run PROPOSED the deletion, `check_roster_retention` refused it, and the PR was held. Nothing reached a reader. The episode is the guard working, not a loss — and it matters which, because one of those is a reason to look harder at the guards and the other is a reason to trust them.

Original ruling below.

**4a. ANSWERED 2026-09-19 — a refusal stops the fetch and never unpublishes.** Adam's words: "Preserve data we have already fetched." Recorded in `CLAUDE.md`'s robots section as standing fleet policy (#1050) and routed to Iowa to implement. Obeying a refusal and deleting what it gave us earlier are different acts; the first is not in question and the second costs a reader the answer while gaining the publisher nothing. Illinois and Wisconsin had already landed here independently, which is what made Iowa visible as the outlier. Iowa shipped that builder change as #1051 (`61a3b48`). #1048 stays held until the next weekly run writes real `readOn` dates — and a preserved county needs a per-source last-read stamp, because the card prints one instance-wide verified date that would otherwise assert a verification nobody performed.

**3. New York's county tier has no owner.** Not blocking. Of 57 non-city
counties, 26 have an unverified board form in the plan's own table, and each is
settled from a certified election document when that county is built. Worth
knowing whether the New York session starts it or whether New York rests here.
| The manager's cheap gate read STALE state from the GitHub API | manager | open — measured once, watch for a second | 2026-09-22 | At the 13:21 UTC check-in, `actions_list` for `smoke-test.yml` on `main` returned `total_count` **1090** and a newest run of **#1061, 2026-09-21T00:22Z**. Every check that hour and the four before it had read `total_count` 1162 with a 2026-09-22 head, and `git fetch` against the repository at the same minute showed main at `3cc29d3` with four commits the API listing did not contain. **So the listing was roughly a day behind and looked exactly like a quiet hour.** That is the failure mode the cheap gate cannot see by construction: it reports "nothing changed" from a stale read and a "nothing changed" reply is indistinguishable from a correct one. Caught only because the number went DOWN — 1162 to 1090 — which a reader watching the same figure each hour notices and a fresh reader would not. **Mitigation used and worth keeping: verify a surprising API answer against `git fetch origin main` before believing it**, which is the notification's own standing instruction and cost one command. Not yet worth a gate: one occurrence, cause unknown (cache, replica lag or pagination), and the repository read is authoritative and cheap. If it recurs, the fix is to take SINCE from `git log origin/main` rather than from the API at all. |
| **E.A.M. — the official definition of "done" for a state** | manager | **process ruled and built; gate in review as #1081** | 2026-09-22 | Adam asked when a state counts as done and ruled the three questions that decide it. **A state is done when it is EXAMINED, ANSWERED and MAINTAINED**, and passing all three **switches that state's session from expansion to maintenance** — it stops hunting counties and only tends what ships. **"No gaps left" was rejected and the reason is the whole design:** Illinois carries 104 gap records and is the deepest instance in the fleet where San Francisco carries two, so counting gaps rewards not looking. The bars measure what this project controls instead of what county publishers control. **EXAMINED** — every county of the state is served by a roster or named by a gap record, denominator the whole state and never the coverage ring (a ring denominator is vacuous: a state serves every county it has bothered to list). **ANSWERED** — every district drawn names a member, is marked vacant, or carries a note; **honesty is the bar, not completeness**, per Adam's ruling, so a card naming two of three seats and stating the third is unlisted passes. **MAINTAINED** — every file the pages read is rewritten by a scheduled workflow. **Internal only**, per Adam: publishing the mark would promise readers something a county publisher can revoke any week. Measured on introduction: **il EA·, wi EA·, ia ·AM, mi ·AM** — nothing is done yet, and **Illinois and Wisconsin are one finding each away**, both failing only Maintained. **ANSWERED already passes everywhere** (0 unanswered of 2,599 districts, 3,005 people), which is the honesty rule holding on its own and why that ruling was right. `scripts/build_eam_status.py` computes it and `docs/EAM_STATUS.md` is generated, so **the mark goes backward** — negative-tested: one unexamined county flips Wisconsin to `·A·`, and a county denominator shrunk to flatter the score fails loudly. |
| **Michigan keeps its "why not" records where the measurement cannot see them** | manager | open, routed 2026-09-22 | 2026-09-22 | Found by E.A.M. rather than by reading. Michigan scores **48 of 83 counties examined** while `mi/data/source/mi-county-board-probe.json` records a measured blocker for **25 more** — so it is examined at 73 of 83 in substance and scores 48. **Two readers of one question, which is the defect this repo names in its own docs repeatedly.** The gap record is the canonical home for "why this county is not served" (the gap-record skill says a gap record is the only thing that makes an absence visible); a probe artifact is a measurement filed somewhere only its own author reads. Wanted: promote the 25 into gap records, keeping the probe as the instrument that produces them rather than as the place they live. **Not done to Michigan's instance unasked** — this is their call and their bookkeeping. |
