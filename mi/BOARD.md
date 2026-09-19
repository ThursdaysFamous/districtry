# Michigan board

Owner session: **Michigan**. Manager owns *Tasks*; this session owns *Status*
and *Open questions*. Rules and reporting posture: `BOARD.md` at the repo root.
Commit board edits straight to main, in their own commit, dated.

## What a reader gets today

Click any point in Michigan and the app answers from **15 layers** — the fewest
in the fleet, because Michigan is the newest instance (live 2026-09-03). The
state House and Senate rosters are complete at 110 and 38.

**20 recorded gaps** — 13 no-source, 5 blocked, 2 data-quality. Eighteen of the
twenty are city council wards.

## Tasks — manager owns this section

| task | state | opened | notes |
|---|---|---|---|
| **Commissioner roster covers 16 of 83 counties** | open | — | The headline gap and the layer the instance was built around. The runway already exists: the probe in #989 measured 59 counties. Next is tranche 5 onward against that list, not more discovery. |
| City council wards — 18 of the 20 gaps | open | — | Ann Arbor and Jackson blocked; Bay City data-quality; Dearborn, Detroit, Flint, Holland, Kentwood no-source. **Run the state's WARD column first** (`mi/WATCH.md` line 30) — one query settled 23 cities on 2026-09-06. `WARD='00'` means stop. |
| Tranche parser candidates | open | — | Carried from this session's last report. |
| Detroit PR-body proposal | open | — | Carried from this session's last report. |
| PR #979 | open | — | Carried from this session's last report; state unverified by the manager. |
| Michigan's full bbox vs. the clipped one | open | 2026-09-04 | The county fabric is water-inclusive and runs west across Lake Michigan to -90.42, containing Chicago's and Wisconsin's centres. Shipped clipped to `lng >= -87.60`. Four western-UP places still misroute at the front door. Recorded in `mi/WATCH.md`; no fix proposed. |

**Wyoming (MI) is off limits.** Its own robots.txt names ClaudeBot and disallows
the whole site. Do not fetch it with a browser user-agent.

## Status — this session owns this section

*(Michigan: replace this line. Say what you are working on, what you finished,
and what you found. Date every entry. Newest first.)*

## Open questions for Adam

*(Michigan: anything you need a decision on.)*
