# Iowa board

Owner session: **none — Iowa is currently unassigned.** The manager writes both
sections until a session owns it. Rules and reporting posture: `BOARD.md` at the
repo root. Commit board edits straight to main, in their own commit, dated.

## What a reader gets today

Click any point in Iowa and the app answers from **20 layers**, across all 99
counties. Two rosters are **complete**: county officers (99 of 99) and county
auditors (99 of 99).

**6 recorded gaps** — 4 data-quality, 1 no-source, 1 blocked.

## Tasks — manager owns this section

| task | state | opened | notes |
|---|---|---|---|
| **Supervisor roster covers 17 of 99 counties** | open | — | The headline gap. It also caps the per-county pages: 26 counties have a board chair and no board list, so they get no page at all. |
| Board chair roster is 38 of 99, and two files still say 43 | **stale record** | 2026-09-19 | #1016 dropped carried records with no `confirmedOn` and moved the file 43 → 38. The gap record and `ia/WATCH.md` both still read "43 of Iowa's 99". The gap record **ships to the Data gaps panel**, so this is a wrong number a reader can see. Fix both in one change. |
| City card names nobody | open | — | `ia-city-contact.json` covers 939 cities with contact details; no officeholder names. |
| Precinct card cannot say where to vote | open | — | no-source. |
| Johnson County districts pending; Jones County absent from the state layer | open | — | Two county-level data-quality holes. |
| Marion ward card blocked | blocked | — | Access control. Never worked around. |

**Do not re-probe the blocked counties with different headers.** Of 28
unreachable county sites: 9 Cloudflare, 5 TLS name mismatch, 4 connection reset,
2 TLS handshake, 1 Akamai, 7 this sandbox's proxy. Osceola is a captcha. A
browser user-agent is not an option for any of them.

## Status — manager writes here until Iowa is assigned

**2026-09-19.** Board created. No session is working Iowa. The stale 43/99 above
is the one item with a reader-visible consequence.

## Open questions for Adam

- Iowa has no session. Do you want one started, or should the supervisor-roster
  work be picked up by an existing session?
