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
| `privacy.html` understates three events sent through `shareCopyButton` | manager | **in review** #1046 — the fix is that an unreadable `trackEvent` call is now an ERROR rather than a skip, which is the `registerCountyLayer` shape a third time; resolution follows one hop and fails naming the line otherwise. Coordinate events stay at two: these three send a name and nothing else | 2026-09-18 |
| Shallow checkout makes every roster PR rewrite all 243 sitemap dates | manager | **in review** — 73 workflows deepened, plus a gate, after #1030 and #1031 did twelve | 2026-09-19 |
| A scheduled workflow that has NEVER run is invisible to every gate here | manager | measuring | 2026-09-19 |

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
- **The queue being empty is why #1046 exists.** With nothing left to review I took the one open
  unassigned task: the privacy page named ten analytics events while every app sends thirteen.

**Manager's own work.** The shallow-checkout defect Wisconsin recorded as
fleet-wide was 73 workflows wide, not twelve; every one is deepened and
`validate_workflow_checkout.py` now fails a workflow that commits `sitemap.xml`
without full history or that re-shallows it afterwards. `docs/MANAGER.md`
records the standing merge authority. Michigan's "a workflow that has never run
is invisible to every gate" was swept across all six instances: of 128
scheduled workflows only two have never run, both explained by the calendar.

Main is at `66f2976`. One open PR: #1018, held.

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

**3. New York's county tier has no owner.** Not blocking. Of 57 non-city
counties, 26 have an unverified board form in the plan's own table, and each is
settled from a certified election document when that county is built. Worth
knowing whether the New York session starts it or whether New York rests here.
