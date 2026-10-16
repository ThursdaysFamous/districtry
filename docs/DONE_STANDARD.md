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
**Covered**. The mark becomes **E.A.M.C.** It stays internal — docs and CI,
never a reader-facing badge — for the reason it always was: publishing it would
promise readers something county publishers can revoke in any given week.

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
6. The governing body of every local government above 25,000 people that
   governs its residents generally (see below).
7. School district boundaries.
14. Township or county subdivision boundaries (added 2026-10-14; see below).

**Required where the state has them**

8. Courts whose judges are elected by district.
9. Townships or other general-purpose sub-county governments.
10. School boards elected by district.
11. Election precincts.
12. Special districts the state's own law creates — fire, park, library,
    sanitary, technical college and the rest — wherever a publisher offers them.
13. Tribal governments. In scope in every state by the mandate of 2026-09-29.
    Illinois, Wisconsin and Michigan answer it; the rest of the fleet is to come.

A level in the second group is covered when either the app answers it or a
record states that the state does not have it. Where a state genuinely lacks a
level — a state with no townships, say — the entry is covered by that fact
rather than by work, and the record states the fact and where it was checked.

Townships (level 9) pass when the township boards are named wherever a list of
them is published (Adam, 2026-10-15). A state where only some counties publish
their township officers passes on those counties, and the card says so for the
townships it cannot name.

## Township and county subdivision boundaries

Added on 2026-10-14 at Adam's request: the layer that tells a reader which
township, town or county subdivision a point is in is expected in every state,
like the county, municipal and school district maps beside it. It is numbered
14 rather than slotted in beside them so that every earlier level keeps the
number the reports and threads already use.

It is a **boundary** level, and it is separate from entry 9. Entry 9 asks
whether the app names the sub-county *government* where one exists. This one
asks whether the app draws the map at all. Every state is divided into county
subdivisions: in some they are governments (Illinois and Indiana townships,
Michigan and Wisconsin towns and townships, New York towns), and in others they
are areas the Census draws for counting only (Kentucky, Oklahoma and South
Carolina's census county divisions), or legal areas the Census records as
having no functioning government (North Carolina's and Arkansas's townships,
Tennessee's civil districts, Mississippi's supervisor districts). The map is
owed either way; where the units govern nobody, the card says so rather than
implying a government. Mississippi's county subdivisions ARE its supervisor
districts, so its supervisor district map is its answer to this level, and the
level stays open until every county's current lines are drawn: in 70 counties
the Census's own copy still carries the lines of its 2020 edition, and in 54 of
them those lines put every resident in the same district as its January 2010
edition did (measured 2026-10-16).
Arkansas's are drawn from the state's own township map rather than the
Census's: the two disagree about how many townships a county has in 27
counties, and in the two counties checked, Washington and Scott, the Census's
map is the out-of-date one (measured 2026-10-15).

**The Census map is the default source, not the last word.** Where a county
publishes finer lines than the Census does, the county's lines are the better
answer. The case that prompted this is Chicago: the Census treats the whole city
as one subdivision, "Chicago city", while Cook County's own map draws the eight
townships inside it. A layer that answers "Chicago city" there does not pass:
Adam ruled on 2026-10-14 that the level stays open until the finer lines are
drawn, and Illinois's layer drew the eight townships the same day. The general
rule is the same: where a county publishes finer lines that the Census map
merges, the level is open until the finer lines are drawn.

San Francisco is one city and one county, so the level does not apply to it, for
the same reason levels 3, 5, 7 and 9 do not.

## Where the city line sits, and which units count

The local governing body is required for every unit of 25,000 people or more on
the 2020 Census that is the **general-purpose government** for its residents —
the body that governs them because nothing smaller does.

That is every incorporated city and village. It is **also** a New York town and
a Michigan township, because in those two states the town or township is what
governs everyone outside a village or city; leaving them out would let New York
look answered while most of upstate was not. Measured 2026-10-01: 67 New York
towns and 34 Michigan townships clear the line, all of them distinct from the
cities and villages already counted.

It is **not** an Illinois township. Eighty-four of those clear the line, and
they are limited-purpose — roads, assessment, general assistance — while an
unincorporated Illinois resident is governed generally by the county. They are
still owed under entry 9 below, which is where Illinois's township officials
already sit. Nor is an Indiana township, for the same reason: measured
2026-10-11, 61 clear the line, and the trustee runs township assistance, fire
protection and cemeteries while the county governs an unincorporated resident.
No active township or town in Iowa, Kentucky, Wisconsin, Minnesota, North
Carolina, Oklahoma, South Carolina, Tennessee, Arkansas or Mississippi reaches
25,000 (North Carolina's townships and Tennessee's civil districts govern
nobody, Kentucky, Oklahoma and South Carolina are divided into census county
divisions, which are statistical areas, every Arkansas township is one the
Census records as having no functioning government, and Mississippi's county
subdivisions are its supervisor districts, which elect a member of the county's
board and govern nobody themselves), so the question does not arise in those
ten today; if one ever does, it is answered by the
general-purpose test above and not by a per-state exception.

| app | units at 25,000+ | of which towns or townships |
|---|---|---|
| New York | 104 | 67 |
| Illinois | 89 | — |
| Michigan | 82 | 34 |
| Minnesota | 43 | — |
| North Carolina | 42 | — |
| Indiana | 39 | — |
| Wisconsin | 35 | — |
| Tennessee | 28 | — |
| Arkansas | 19 | — |
| Iowa | 18 | — |
| Kentucky | 17 | — |
| South Carolina | 17 | — |
| Oklahoma | 16 | — |
| Mississippi | 15 | — |

That is 564 governments across the fourteen statewide apps. The first seven rows
were measured 2026-10-01, Arkansas's 2026-10-15, Mississippi's 2026-10-16 and the
rest 2026-10-11;
until then the scoring tool read a state it had not measured as one with nothing
to answer, so Indiana, North Carolina and Oklahoma passed this entry unchecked.
San Francisco is one city, so its city tier is the whole app.

**A city is answered when a reader clicking inside it is told who governs that
point.** Where the council elects by district, that means the districts are
drawn and the members named. Where it elects at large, naming the members is
the whole answer and there is no district to draw — the precedent Iowa already
set for countywide-elected bodies. This matters: many Illinois villages above
25,000 elect their trustees at large, so a rule demanding drawn districts
everywhere would fail them for a boundary that does not exist.

Adam confirmed this on 2026-10-15 for the county body as well as the city one,
and the scoring tool has enforced it since: a county or city whose body is
elected by district counts only where those districts are drawn, and naming its
members is not enough. A seat that the whole county or city elects, even if its
holder must live in a district, is an at-large seat and needs no map; Indiana's
county commissioners and Kentucky's commissioner-form fiscal courts are elected
that way.

## What a record has to do to count

A level counts as covered by record only when all of this is true:

- The absence is **measured** — we know what the publisher does and does not
  offer, not that we could not find it.
- We **asked**, by name, and did not get what we wanted. A refusal counts
  straight away. Silence counts once we have asked, sent one follow-up, and
  waited thirty days from that follow-up — which is the ordinary case, because
  most of these asks are never answered at all. Both the ask and the follow-up
  are recorded with their dates in the existing ask ledger.
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
| Iowa | all 99 | 91 counties |
| Michigan | all 83 | 52 counties |
| Illinois | 60 of 102 | 83 counties |
| New York | 1 of 62 | 1 |
| Minnesota | none | none |
| Kentucky | none | none |

Iowa's figure read **21 counties** and Illinois's **all served counties** until
2026-10-01, when the count behind them was found to look for names only inside
districts. A board elected **at large** has no districts and carries its members
at the top of its record, so 70 Iowa counties and 20 Illinois counties naming
real people were counted as naming nobody. Naming the members is the whole
answer for an at-large body, which this standard says above; both shapes count
now. Neither state's level closes either way.

**Local governing body, units at 25,000+**

| app | districts drawn | members named | of |
|---|---|---|---|
| Illinois | 35 | 83 | 89 |
| Wisconsin | 28 | 14 | 35 |
| Iowa | 3 | 3 | 18 |
| Michigan | 7 | 4 | 82 |
| New York | 1 | 1 | 104 |
| Minnesota | 0 | 0 | 43 |
| Kentucky | 0 | 0 | 17 |

No app names a single New York town board or Michigan township board today, so
all 101 of those are new work.

Illinois's six unanswered cities are Champaign, Danville, Decatur, Normal,
Quincy and Urbana. Michigan draws seven — Detroit, Warren, Grand Rapids, Flint,
Rochester Hills, Battle Creek and Jackson — and names members in four of them.
Its own layer note names only Detroit and Grand Rapids and is stale, which is
the Michigan thread's to correct; this table was first written from that note
and read 3, which is why a count comes from the registrations and never from a
comment about them. The named figure read 3 until 2026-10-01, when the Michigan
thread pointed out that Battle Creek has shipped a weekly-refreshed commission
roster since #786 — so the reading that a count comes from the registrations
cost nothing here only because the registration was itself incomplete. Wisconsin's twenty-one unnamed councils are Beloit,
Brookfield, Caledonia, De Pere, Fitchburg, Fond du Lac, Franklin, Greenfield,
Janesville, La Crosse, Menomonee Falls, Mequon, Mount Pleasant, Muskego, Oak
Creek, Oshkosh, Sun Prairie, Wausau, Wauwatosa, West Allis and West Bend.

Illinois already passes Examined, so every county it does not dispatch is either
served another way or carries a record; the fourth test does not re-ask that
question.

**Everything else**

- Courts by district: Illinois, Wisconsin, Iowa and New York answer them.
  Michigan, Minnesota and Kentucky ship no such layer, and all three have since
  confirmed in their own notes that they elect judges by district, so the entry
  is owed in each. Kentucky's reaches furthest: all four court levels elect by
  district — Supreme Court, Court of Appeals, 57 circuits and 59 district-court
  districts — and every one of those districts is a set of whole counties
  written into statute, so the lines are buildable from statute text and county
  boundaries the app already ships.
- School boards elected by district: Chicago, Milwaukee, Racine, Iowa's
  statewide director districts and New York City's community education councils.
  Kentucky ships none and owes them: its thread has confirmed that every county
  school board is elected by division, five divisions per county, each built
  from whole precincts. Kentucky's independent school boards are elected at
  large, so they are named rather than drawn.
- Precincts: Illinois (83 counties), Iowa, Michigan, Minnesota, New York, San
  Francisco and Wisconsin's wards, and since 2026-10-15 Kentucky, Indiana, North
  Carolina, South Carolina, Tennessee and Arkansas, each drawn from the one
  statewide precinct map a government office in that state publishes. Oklahoma
  ships none: its State Election Board sent the question of using its precinct
  maps to the University of Oklahoma's Center for Spatial Analysis, which was
  asked on 2026-10-01 and has not answered, and no precinct layer ships there
  until it does.
- Tribal governments: no app answers one.

## Launching is a lower bar than being done

Kentucky going live with four layers was right — an app that answers Congress,
both state chambers and county lines is useful on its first day, and waiting for
the county tier would have held it back for months. Being live and being done
are different questions and the report only measures the second.
