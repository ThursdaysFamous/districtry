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
| `ia/BOARD.md` | Iowa | **none — unassigned** |
| `mi/BOARD.md` | Michigan | Michigan |
| `ny/BOARD.md` | New York City | NYC/SF |
| `ca/BOARD.md` | San Francisco | NYC/SF |

Six instances, four sessions. NYC/SF owns two boards; Iowa has no session.

---

## Tasks — cross-cutting work, manager owns this section

Work here belongs to no single state. A task that lives inside one instance
belongs on that instance's board instead.

| task | owner | state | opened |
|---|---|---|---|
| Roster workflows: regenerate shared pages after the branch cut (#1030 IL, #1031 WI) | IL + WI | in review | 2026-09-19 |
| Absolute gate on every shipped officeholder name (#1025) | NYC/SF | in review | 2026-09-19 |
| `privacy.html` understates three events sent through `shareCopyButton` | unassigned | open | 2026-09-18 |

## Status — manager writes here

**2026-09-19.** Boards created. Main is at `820338c`.

Merged today that a reader would notice: Rock Island County's 15 municipalities
stopped naming 112 officeholders after strings that are not people (#1024). It
had been live 15 days.

Open PRs: #1030, #1031 (CI plumbing), #1028 (Bartonville phantom Clerk), #1025
(name gate), #1018 and #1023 (weekly roster refreshes, Hancock and Grundy).

## Open questions for Adam

- Nothing outstanding.
