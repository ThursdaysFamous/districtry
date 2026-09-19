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
| `privacy.html` understates three events sent through `shareCopyButton` | unassigned | open | 2026-09-18 |
| Shallow checkout makes every roster PR rewrite all 243 sitemap dates | manager | **in review** — 73 workflows deepened, plus a gate, after #1030 and #1031 did twelve | 2026-09-19 |
| A scheduled workflow that has NEVER run is invisible to every gate here | manager | measuring | 2026-09-19 |

## Status — manager writes here

**2026-09-19, second pass.** Adam read the boards and gave three instructions:
add Will County to the municipal builder's exception list, start New York's
phase 3, and use judgement on the rest. All five sessions are working.

- **Illinois** — Will joins `PRESERVABLE`, which unfreezes 37 counties' mayors
  and council members. Frozen since 2026-09-08 because one blocked county is
  `REQUIRED`. #1018 stays held behind it.
- **New York** — PR 3, the go-live. Its two live defects (a gap record that is
  false, and an empty CEC roster with no record at all) ship no later than it
  does, because the go-live is what starts sending upstate readers to them.
- **Wisconsin** — the Court of Appeals job: one bounded look for the four judges
  on a host that answers, and if there is none, a recorded expected condition
  plus a staleness ceiling rather than dropping the job. Then the alderperson
  gap, measured whole before any tranche.
- **Iowa** — the 38/61 correction first because it is false on a page a reader
  opens, then Mitchell, re-read rather than `--allow-drop`.
- **Michigan** — tranche 6, the 22 remaining probe candidates, no fetch needed.

**Manager's own work.** The shallow-checkout defect Wisconsin recorded as
fleet-wide was 73 workflows wide, not twelve; every one is deepened and
`validate_workflow_checkout.py` now fails a workflow that commits `sitemap.xml`
without full history or that re-shallows it afterwards. `docs/MANAGER.md`
records the standing merge authority. Michigan's "a workflow that has never run
is invisible to every gate" is being measured across all six instances.

Main is at `ff9ba6e`. One open PR: #1018, held.

## Open questions for Adam

- Nothing outstanding.
