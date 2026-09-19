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
| Bartonville's phantom Clerk (#1028) | in review | 2026-09-19 | Fixes the parse first, then widens the guard. Removes one fabricated name a reader can see today. |
| Six roster workflows: shared pages after the branch cut (#1030) | in review | 2026-09-19 | Stops weekly jobs dying when another workflow merges mid-crawl. Also deepens the checkout so sitemap dates are real. |
| Will County municipal directory is blocked (#982, #996, #1026) | blocked | 2026-09-08 | The county's directory sits behind a vendor managed challenge. Will is in `REQUIRED_COUNTIES`, so the **whole** municipal roster has not rebuilt since 2026-09-08. Never worked around. |
| Plattville's Clerk ships as `Beth Fals 56` | open | 2026-08-01 | Kendall's yearbook parser reads past the end of its section. The name must be **dropped, not repaired** to `Beth Fals` — the Douglas County rule. Currently held in `ACCEPTED_NAMES`. |
| 2 of 64 districted board cards name no office | open | 2026-09-15 | Down from 50 on 2026-09-06. The long tail. |

## Status — this session owns this section

*(Illinois: replace this line. Say what you are working on, what you finished,
and what you found. Date every entry. Newest first.)*

## Open questions for Adam

*(Illinois: anything you need a decision on. Nothing here is sent to anyone —
the manager relays it.)*
