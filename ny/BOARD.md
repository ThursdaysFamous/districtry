# New York City board

Owner session: **New York**. Manager owns *Tasks*; this session owns *Status*
and *Open questions*. Rules and reporting posture:
`BOARD.md` at the repo root. Commit board edits straight to main, in their own
commit, dated.

## What a reader gets today

Click any point in New York City and the app answers from **33 layers** — the
most in the fleet after Illinois. All 51 Council Members are named, and since
2026-09-15 they appear in the served bytes of `ny/council-district.html` as a
dated table rather than only inside a JavaScript-rendered card.

**4 recorded gaps**, all data-quality. The cleanest gap list in the fleet.

## Tasks — manager owns this section

| task | state | opened | notes |
|---|---|---|---|
| Absolute gate on every shipped officeholder name (#1025) | in review | 2026-09-19 | Fleet-wide, not NY-specific — it reads the shipped tree for names that are not names, across 10,986 person records in 757 files. Tracked on the fleet board too. |

**Scope, 2026-09-19 (from Adam).** This session covers New York and nothing
else. It was briefed earlier as owning San Francisco too; it does not.

**Scope note, 2026-09-19.** This session spent part of tonight fixing an
Illinois defect that was already assigned to the Illinois session, producing a
duplicate of #1024. That was a manager routing failure, not this session's.
Illinois work belongs to Illinois.

## Status — this session owns this section

**2026-09-19.** New York is further along than its own plan says, and the
statewide tier is reachable today rather than only built.

What a reader gets: 33 layers — 18 answer only inside New York City, 14 answer
statewide, 1 answers only outside the city. **Measured in Chromium, not
inferred:** a reader who pans to Albany or Buffalo and clicks gets 7 cards
naming real officeholders (Paul Tonko, Patricia Fahy, Gabriella Romero;
Timothy Kennedy, April Baskin, Jonathan Rivera) plus county, municipality,
school district and judicial district. Those are floors — the live-API layers
cannot be reached from this sandbox, so production answers more. The 17
city-only cards correctly hid themselves upstate, so the coverage gating works.

So "dark" describes what points at the tier, not what it can do. The front door
tells an upstate reader "outside every place districtry covers today", because
New York's registered bbox stops at latitude 41.0; the in-app address box is
New York City only; an upstate `#point=` permalink is refused; the app still
calls itself New York City and the coverage map draws one dot labelled
"5 boroughs". That is PR 3, which has not started.

**The plan document's status block is stale and cost this session an hour.** It
still reads "PR 2 and PR 3 are NOT started". PR 2 merged 2026-09-18 as
`8765e9b` (#1007) and edited that same file without touching the block six
lines above it. This session repeated the stale claim to Adam before measuring
against git. Read the log, never the block.

Three defects found and not fixed, all reader-facing:

* `nyc-congress-district-offices` says congressional cards show only the
  Washington office. All 26 records carry a local district office and
  `ny/index.html:11060` renders it labelled "District Office". The one panel
  whose job is being accurate about absence is inaccurate.
* `ny/data/app/cec-members.json` ships as `{}` — zero of 32 Community
  Education Councils — with no gap record, while a weekly workflow installs
  Chromium to run a scraper whose own docstring says the source is gone.
* The six statewide layers PR 2 shipped have no `validate_sources.py` row and
  no `ny/WATCH.md` row, both of which the plan's own rules require in the same
  change. If New York State renames one of those services, nothing notices.

Also: the layer count is written four ways across the tree (27, 31, 32, 33) and
two of those match no commit the repository ever had; an unsent press pitch
still says 27. `ny/WATCH.md` describes sibling forks and a Chicago master repo,
neither of which has existed since the consolidation.

**#1025 merged** (`a3d11c0`). It is fleet-wide, but New York found its second
defect: `is_person_record()` examined **zero** of New York's 380 published
officeholders, because New York writes rosters as `{district: {name, party,
…}}` and none of the four shapes matched. The gate's own line said "6
instance(s)", which reads as coverage it did not have. A fifth shape keyed on
`party` — the one field only a person carries — took it to 12,446 records with
New York at 239 and zero new findings. Keying on `office` would have reached
New York's 51 council members and also 549 Illinois municipalities, 29
townships and the Cicero Public Library, so it was measured, rejected, and
written into the self-test. Those 51 are still unexamined, and the gate now
names a blind instance out loud.

Paused here at Adam's direction. Next, when picked up: PR 3, or the two small
live defects above as a shorter change first.

## Open questions for Adam

**Settled 2026-09-19:** board edits for this instance commit straight to
`main`, in their own commit — Adam granted it directly, which is what this
session was waiting on rather than a manager instruction to do so.

**1. Start PR 3, the go-live?** Twelve real edits, scoped in
`docs/NY_EXPANSION_PLAN.md`. It is what makes the working statewide tier
reachable through the front door, the address box and shared links.

**2. Fix the false gap record and the empty CEC roster first?** Both are live,
both are small, and neither is part of PR 3.
