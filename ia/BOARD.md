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
| **The chair gap record states a number the file no longer carries** | open | 2026-09-19 | `ia-board-chair`'s reader text says "in 43 of Iowa's 99 counties… In the other 56 it cannot". The file holds **38**, so it is 38 and 61. This ships to the Data gaps panel, so it is wrong on the page a reader opens. `ia/WATCH.md` line 39 carries the same 43. This session already has it — its own last summary names it. |
| **Supervisor roster covers 17 of 99 counties** | open | — | The headline gap. It also caps the per-county pages: 26 counties have a chair and no board list, so they get no page at all. |
| City card names nobody | open | — | `ia-city-contact.json` covers 939 cities with contact details and no officeholder names; 834 have no website at all. |
| Precinct card cannot say where to vote | open | — | no-source. The polling-place precinct column was dropped upstream. |
| Johnson County districts pending; Jones County absent from the state layer | open | — | Two county-level data-quality holes. Johnson's minutes host refuses `districtry` in robots.txt — that is the host's answer, not a bug. |
| Marion ward card blocked | blocked | — | Access control. Never worked around. |

**Do not re-probe the blocked counties with different headers.** Measured
2026-09-06: of the 20 counties the gated run calls unreachable, nine answer 403
and eight of those are Cloudflare, seven serving a managed challenge. A complete
header set with this project's own user-agent moved none of them, and a browser
user-agent is not an option. Polk is **withdrawn** rather than blocked — review
could not reproduce it, so it is client-dependent.

## Status — this session owns this section

*(Iowa: replace this line. Say what you are working on, what you finished, and
what you found. Date every entry, newest first.)*

## Open questions for Adam

*(Iowa: anything you need a decision on.)*
