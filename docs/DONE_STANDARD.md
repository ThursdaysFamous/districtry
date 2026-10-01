# When a state app is done — the agreed standard

Settled with Adam on 2026-10-01. This is the rule of record. The report that
scores each app against it is `scripts/build_eam_status.py`, which writes
`docs/EAM_STATUS.md`; that script is owned by the App and engine thread and
this document is its specification, not a second copy of its output.

## Why there is a fourth test

Until today a state was done when it was **Examined**, **Answered** and
**Maintained**. Those three ask whether we looked everywhere, whether every
district we draw names somebody or says why not, and whether every file the app
reads is under a stated re-check plan. All three are about how honestly and how
durably we handle what we ship.

None of them asks how much of a government we ship at all. So an app could pass
while answering almost nothing below the county. Measured on 2026-10-01, three
of the eight live apps were in that position:

- **New York** answers wards, school zones, police precincts and poll sites —
  all inside New York City. Outside the city it draws county board districts in
  one county of 62.
- **Minnesota** draws townships and cities but has no elected seat below the
  state at all: no county boards, no councils, no school boards.
- **Kentucky** ships four things: Congress, both state chambers, county
  outlines.

All three passed. The standard now has a fourth test that they do not pass.

## The four tests

A state is done when it is **Examined**, **Answered**, **Maintained** and
**Covered**.

The first three are unchanged and are documented in
`scripts/build_eam_status.py`.

**Covered** — the app answers every level of government it is expected to
answer, to the depth set out below, or carries a written, measured record of why
a level cannot be answered.

## The argument against this, and why it is accepted anyway

Coverage was deliberately left out of the standard on 2026-09-22, for a good
reason: holding a state open until every county ships hands the definition of
done to county publishers. Illinois carries over a hundred gap records and is
the deepest app in the fleet; an app with two records is more likely
under-researched than complete. Counting absences punishes looking.

That objection stands, and the fourth test is shaped around it rather than
against it. **Covered scores whether we did the work, not whether the data
exists.** A level that no publisher offers, which we have asked about and been
refused, counts as covered. A level nobody has looked at does not. The report
therefore cannot be failed by a county clerk's decision, only by ours.

The loophole this creates is real and is bounded in the next section: a lazy app
could write records instead of building. That is why a record only counts after
an ask, and why every record is re-audited on each run.

## The expected list

One list of government **functions** for every state. Each state maps its own
names onto it — a county governing body is a county board in Illinois and
Wisconsin, supervisors in Iowa, commissioners in Michigan, a fiscal court in
Kentucky, a county legislature in New York. The list does not change per state;
which entries apply does.

**Required in every state**

1. The U.S. House seat.
2. Both chambers of the state legislature.
3. County boundaries.
4. The county governing body — its districts drawn where it elects by district,
   its members named — in every county of the state.
5. Municipal boundaries.
6. The governing body of every municipality above 25,000 people (see below).
7. School district boundaries.

**Required where the state has them**

8. Courts whose judges are elected by district.
9. Townships or other general-purpose sub-county governments.
10. School boards elected by district.
11. Election precincts.
12. Special districts the state's own law creates — fire, park, library,
    sanitary, technical college and the rest — wherever a publisher offers them.
13. Tribal governments. In scope in every state by the mandate of 2026-09-29;
    no app answers one yet, and the fleet-wide layer is in planning.

A level in the second group is covered when either the app answers it or a
record states that the state does not have it. Where a state genuinely lacks a
level — a state with no townships, say — the entry is covered by that fact
rather than by work, and the record states the fact and where it was checked.

## Where the city line sits

The municipal governing body is required for every incorporated place of 25,000
people or more, counted on the 2020 Census. Measured on 2026-10-01 that is 287
cities across the seven statewide apps:

| app | cities at 25,000+ | share of the state's city population they hold |
|---|---|---|
| Illinois | 89 | 64% |
| Michigan | 48 | 68% |
| Minnesota | 43 | 59% |
| New York | 37 | 84% |
| Wisconsin | 35 | 56% |
| Iowa | 18 | 49% |
| Kentucky | 17 | 58% |

San Francisco is one city, so its city tier is the whole app.

**A city is answered when a reader clicking inside it is told who governs that
point.** Where the council elects by district, that means the districts are
drawn and the members named. Where it elects at large, naming the members is
the whole answer and there is no district to draw — the precedent Iowa already
set for countywide-elected bodies. This matters: many Illinois villages above
25,000 elect their trustees at large, so a rule demanding drawn districts
everywhere would fail them for a boundary that does not exist.

## What a record has to do to count

A level counts as covered by record only when all of this is true:

- The absence is **measured** — we know what the publisher does and does not
  offer, not that we could not find it.
- We **asked**, by name, and were refused or got no answer. The ask is recorded
  with its date in the existing ask ledger.
- The record says what we wanted, who we asked and what happened, in the shape
  the gap records already use.

A record written without an ask does not count, and the report should say so
rather than pass it.

## Retroactive

All eight live apps are re-scored against the fourth test now, and an app can
lose the pass it holds today. New apps are scored as they arrive.

## The starting position

Measured 2026-10-01, before any work against this standard.

**County governing body, every county**

| app | districts drawn | members named |
|---|---|---|
| Wisconsin | all 72 | all 72 |
| Iowa | all 99 | 21 counties |
| Michigan | all 83 | 52 counties |
| Illinois | 60 of 102 | all served counties |
| New York | 1 of 62 | 1 |
| Minnesota | none | none |
| Kentucky | none | none |

**Municipal governing body, cities at 25,000+**

| app | districts drawn | members named | of |
|---|---|---|---|
| Illinois | 35 | 83 | 89 |
| Wisconsin | 28 | 14 | 35 |
| Iowa | 3 | 3 | 18 |
| Michigan | 2 | 2 | 48 |
| New York | 1 | 1 | 37 |
| Minnesota | 0 | 0 | 43 |
| Kentucky | 0 | 0 | 17 |

Illinois's six unanswered cities are Champaign, Danville, Decatur, Normal,
Quincy and Urbana. Wisconsin's twenty-one unnamed councils are Beloit,
Brookfield, Caledonia, De Pere, Fitchburg, Fond du Lac, Franklin, Greenfield,
Janesville, La Crosse, Menomonee Falls, Mequon, Mount Pleasant, Muskego, Oak
Creek, Oshkosh, Sun Prairie, Wausau, Wauwatosa, West Allis and West Bend.

Illinois already passes Examined, so every county it does not dispatch is either
served another way or carries a record; the fourth test does not re-ask that
question.

**Everything else**

- Courts by district: Illinois, Wisconsin, Iowa and New York answer them.
  Michigan, Minnesota and Kentucky ship no such layer. Whether each of those
  three elects judges by district is for its own thread to confirm before the
  entry is scored against it; nothing here measured it.
- School boards elected by district: Chicago, Milwaukee, Racine, Iowa's
  statewide director districts and New York City's community education councils.
  Kentucky ships none, and whether its county school boards are elected by
  division is for the Kentucky thread to confirm.
- Precincts: Illinois (83 counties), Iowa, Michigan, New York, San Francisco and
  Wisconsin's wards. Minnesota and Kentucky ship none.
- Tribal governments: no app answers one.

## Launching is a lower bar than being done

Kentucky going live with four layers was right — an app that answers Congress,
both state chambers and county lines is useful on its first day, and waiting for
the county tier would have held it back for months. Being live and being done
are different questions and the report only measures the second.
