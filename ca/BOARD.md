# San Francisco board

Owner session: **none.** No work is being done on San Francisco, so no session
is assigned — a deliberate state rather than a gap. The manager keeps this board
until one is. Rules and reporting posture: `BOARD.md` at the repo root. Commit
board edits straight to main, in their own commit, dated.

## What a reader gets today

Click any point in San Francisco and the app answers from **16 layers**. All 11
Supervisors are named, and since 2026-09-15 they appear in the served bytes of
`ca/supervisor-district.html` as a dated table rather than only inside a
JavaScript-rendered card.

**3 recorded gaps**, all data-quality — the smallest gap list in the fleet.

San Francisco sends **no** point-query to any government server: measured in a
real browser by `scripts/probe_point_transmission.mjs`, zero of its layers fire
an `.atPoint` hook. It is the only instance of which that is true.

## Tasks — manager owns this section

| task | state | opened | notes |
|---|---|---|---|
| **`sf-congress-district-offices` is a false gap record** | **merged** #1039 `70bf63f` — retired 2026-09-19, confirmed on main 2026-09-21 | 2026-09-19 | It tells a reader "Congressional cards show the Washington D.C. office only, not the local district office." MEASURED in Chromium at SF City Hall with the congress layer on: the card's Offices disclosure carries TWO tel links, `tel:4155564862` (a San Francisco district number) and one built from the D.C. address. 50 of 52 records in `congress-roster.json` carry a `districtOffice`, and `ca/index.html:9658` renders it labelled "District Office". So the card shows both offices and the record is false. New York found the same text false on its own instance, fixed its copy in #1036, and correctly did NOT touch this one — its PR says so in as many words, and that it needed this browser read first. It has it now. Fix follows #1036, because both edit the same guidebook block. |
| The malformed phone link #1036 fixes is 53 blocks here — the fleet's worst | **merged** with #1036 `70a7799`, as predicted: the fix was in the shared engine fence and reached this instance with nothing SF-specific to do | 2026-09-19 | San Francisco carries 53 of the fleet's 84 office blocks that render an ADDRESS as a dialable number, more than any other instance. `tel:1236205150511` is one of them, confirmed live in the probe above. The fix is in the shared engine fence, so it reaches this instance with nothing SF-specific to do. |

## Status — manager writes here until a session is assigned

**2026-09-19.** Board created; corrected the same day. It first named the New
York session as owner. That session's scope is New York only, and San Francisco
has no session because no work is being done on it.

Nothing is in progress and nothing is broken. The instance serves 16 layers,
names all 11 Supervisors, and carries three data-quality gaps — the smallest gap
list in the fleet.

## Open questions for Adam

- None. A session is assigned when there is work; until then this board records
  what the instance already does.
