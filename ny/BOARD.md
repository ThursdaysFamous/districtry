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
| Absolute gate on every shipped officeholder name (#1025) | **merged** `a3d11c0` | 2026-09-19 | Fleet-wide, not NY-specific. Your fifth record shape, keyed on `party`, is what made it see New York's own 239 records at all — the gate's "6 instance(s)" line had been reading as coverage it did not have. |
| **PR 3, the go-live** | **assigned** | 2026-09-19 | Adam's ruling, 2026-09-19: "Ny phase 3". `docs/NY_EXPANSION_PLAN.md` §PR 3. What makes the working statewide tier reachable through the front door, the address box and shared links. |
| **The false congress-offices gap record and the empty CEC roster** | **assigned — ships no later than PR 3** | 2026-09-19 | Not deferred, and not a separate priority: the go-live is what starts sending upstate readers to both. The CEC record says what you corrected — the DOE decentralised the listings across 32 council sites, so the members are published and not reachable by one scraper. "The source is gone" would have been a false blocker. |
| Six statewide layers have no `validate_sources.py` row and no `ny/WATCH.md` row | open, inside PR 3 | 2026-09-19 | The plan's own rules required them in the same change as PR 2. After go-live a renamed New York State service breaks a live tier with nothing watching. |
| The layer count is written four ways across the tree | open, inside PR 3 | 2026-09-19 | 27, 31, 32 and 33; two of those match no commit this repository ever had. The unsent press pitch at 27 is Adam's file — flag it, do not edit it. |

**Scope, 2026-09-19 (from Adam).** This session covers New York and nothing
else. It was briefed earlier as owning San Francisco too; it does not.

**Scope note, 2026-09-19.** This session spent part of tonight fixing an
Illinois defect that was already assigned to the Illinois session, producing a
duplicate of #1024. That was a manager routing failure, not this session's.
Illinois work belongs to Illinois.

## Status — this session owns this section

**2026-09-19, #1042 verified and waiting.** CI is green on the head
(`372e7d7`), there is no merge conflict, and the only comments on the PR are
mine. Nothing on it is waiting on this session.

Main moved twice while it was open. The second time, `git merge-tree` reported a
clean auto-merge — and that was not taken as the answer, because both sides edit
`docs/DATA_LAYER_GUIDEBOOK.md` and two gates parse figures out of that file, so a
clean auto-merge can still be a state neither side ever had. The merged tree was
materialised and run rather than assumed: the two edits are disjoint, and
`validate_doc_counts`, `validate_officeholder_names`, `validate_gate_counts`,
`validate_steward_mirror`, the six `build_coverage_gaps --check` runs and
`build_coverage_map --check` all pass on it. No second merge commit was pushed —
the head is green and a merge that changes nothing costs a CI cycle.

**A finding worth keeping, because it is a gap in a family this repo otherwise
gates hard.** The PR body said "76 of 76 static gates". That was measured before
the merge commit that is now part of the PR, which is exactly the failure
`CLAUDE.md` spells out — a figure measured before the change it claims to include
is stale the moment it is written. Re-extracted from `smoke-test.yml` rather than
corrected by arithmetic: 93 invocations, 81 of them static gates, all 81 passing.
`validate_gate_counts.py` exists precisely so this cannot happen to `CLAUDE.md`,
and `validate_steward_mirror.py` so it cannot happen to the skill — but **nothing
measures a figure typed into a PR body, a comment, or a check-in prompt**, and
all three carried a wrong one today. The correction is on the PR. Whether that is
worth a gate is a real question and not obviously yes: a PR body is written once
and read once, unlike the two files that are gated.

**2026-09-19, go-live.** PR 3 is open as #1042. New York is a statewide
instance from the reader's side, not just underneath.

What changes for a reader, which is the only reason this PR exists. Typing an
upstate address at the front door used to return "outside every place districtry
covers today"; it now routes to the app with the point selected. The map opens
on the state instead of the harbour. A shared upstate permalink resolves instead
of being silently dropped. The search box finds an Albany address. And the app
stops calling itself New York City.

**The plan's geocoder swap was measured and rejected**, and what shipped is
better than the swap or the status quo. The state's own geocoder resolves
"20 W 34th St, New York, NY" ten miles away in Bensonhurst — it eats the
directional W as a street name — and never returns the right address for
"350 5th Ave, Manhattan, NY", eating Manhattan the same way. So GeoSearch keeps
the city, where it is authoritative, and a zero-result city search falls through
to a state-bounded provider. That fall-through is NOT a nicety: the existing
sibling-metro lookup excludes this instance by construction, so the moment the
bbox widened, an upstate hit landed inside our own box and was dropped.

**Two measurements caught things that would have shipped wrong.** The probe that
measures what the app sends to a server reported New York at ONE layer instead
of five, because moving the ground-truth anchor upstate hid the city tier from
it — the privacy page would have published that number. And the plan's own
proposed bounding box would have clipped the state's eastern edge, because it
was derived from the legislative extent while the plan's own text says to take
it from the county fabric.

**The plan's status block is corrected here too.** It claimed PR 2 was unstarted
for a day after PR 2 merged, and that is what cost this session an hour
yesterday.

Item 9, the press list, is deliberately not done — it is an outbound file and
Adam owns it.

**The three things this board asked PR 3 to carry are in it** (`87ee4fe`), and
one was worse than the board recorded. `ny/scripts/validate_sources.py` was not
merely missing rows for the statewide layers — it was FAILING, and had been
since PR 2, because its judicial-districts entry still described five boroughs
relabelled, built from a Census service by Illinois's builder. That layer has
been 13 statewide districts from the state's own county fabric since 2026-09-18.
So the one gate watching these sources was watching the wrong source, and it
said so by exiting 1 rather than by drifting quietly, which is the gate working.

The statewide tier now has freshness entries; it did not before, and that check
is one-directional, so it can see a manifest entry the app dropped but never an
app file the manifest never had. `ny/WATCH.md` is corrected too — it described
per-metro forks retired at R2.1 and told a reader to keep the file at the repo
root, where it has never been.

What is still missing is stated on that file rather than implied: the statewide
layers have freshness entries but no redistricting-watch ROW, because county and
municipal boundaries move by annexation rather than on a cycle, and the trigger
needs deciding rather than inventing.

**2026-09-19, later.** PR 3 is started. Two of the three card defects from the
entry below are fixed and a third was found while proving the first.

**#1036 is open** — "Three things New York's cards said that were not true". It
is the prerequisite for the go-live, because all three are wrong in front of a
mostly-in-the-city audience today and would be wrong in front of every upstate
reader the front door starts sending here.

1. `nyc-congress-district-offices` is RETIRED. Read in Chromium: the card
   renders District Office FIRST, with street, city and a dialable number. All
   26 records carry it, because the builder already reads the district-offices
   file the record itself named as the outstanding enrichment. A Closed record
   section carries the story and the verbatim blocker. When that enrichment
   landed is NOT established — this checkout is shallow from 2026-09-15 — so
   the closing date is when it was measured, not when it became true.
2. The CEC gap is RECORDED, in the decentralised wording rather than the
   "source is gone" wording corrected in the entry below.
3. **The same browser read found the card wrong the other way.** The D.C.
   office rendered the BUILDING ADDRESS as the telephone number, linked
   `tel:245205153210`, while the line that said `Phone: 202-225-7944` sat
   beneath it as plain text. The phone test matched a ZIP+4. Fleet-wide that is
   84 of 1,454 office blocks — 30 in New York (every congressional D.C.
   office), 53 in San Francisco, 1 in Wisconsin. It is ENGINE code, so the fix
   reaches all six instances. After: 84 to 0, exactly 84 changed, nothing
   dropped, verified in a browser on both affected instances.

So the gap record was wrong about the card in one direction while the card was
wrong in another, and one reading found both. Neither is catchable by any gate
here: both are claims about what a reader sees.

**A smoke assertion went red and was not weakened.** New York's cold
gaps-panel check asserted a section count of one; the panel groups by kind, so
that is data, not an invariant — which the comment fifteen lines below it
already says, having fixed the identical constant in the warm check the day
before. It now derives the count from the shipped kinds, negative-tested both
ways. San Francisco carried the same constant and passes BY ACCIDENT, all three
of its gaps being one kind, so it was fixed there too rather than left armed
for an instance with no session to find it.

Go-live research is running on the three items that need measuring before code:
the Wikidata item for the STATE (its gate fails only on a missing entry, so a
wrong id would ship), the new anchor set, and the state geocoder.

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
  Education Councils — with no gap record, while `ny-update-cec-roster.yml`
  installs Playwright and Chromium every Wednesday to run a discovery walk that
  finds nothing. **Corrected the same evening:** this entry first said the
  scraper's docstring reports the source "is gone". It does not, and the
  difference decides what to do about it — the DOE DECENTRALISED the listings
  across 32 independent council sites (cec3.org, cec14.org, DOE Google Sites)
  with no uniform URL and no NYC Open Data dataset, so the members are
  published and simply not reachable by one scraper. The card degrades to the
  council page and names nobody, which is correct; what is missing is a gap
  record saying so.
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

**1. Is "5 boroughs" still the right scope line for New York?** Not blocking —
#1042 ships it unchanged, because the plan says it stays until a county joins
the ring and I would rather raise a disagreement than deviate quietly.

Measured: the landing page now reads **New York · 5 boroughs** beside
**Wisconsin · all 72 counties**, while 15 of New York's 33 layers answer
everywhere in the state and a click in Buffalo returns seven cards. A reader
comparing those two rows would reasonably conclude New York is a city app, which
stopped being true yesterday. The coverage map does tell the two-tier story
correctly — a dashed state wash and a solid five-borough fill — so the map and
the scope line now say different things.

The options, and what each costs. Leave it: consistent with the plan, and
understates the instance on the one line most readers see. Change it to
something like "statewide, 5 boroughs in depth": honest about both tiers, but it
is the only scope string in the fleet that is not a count, so it may read as
special pleading. Change it to "all 62 counties": matches the other statewide
instances and overstates, because no county tier exists yet — the county card
names nobody.

**I would take the middle one.** The rule the plan is protecting is "never claim
a county tier you do not have", and a phrase naming both tiers keeps that while
telling a reader what the app actually does.

**2. The county tier is the real remaining work, and it has no owner.** Not
blocking. Of 57 non-city counties, 26 have an unverified form in the plan's own
table, and the plan is explicit that each is settled from a certified election
document when that county is built. Nothing is assigned. Worth knowing whether
you want this session to start it, or whether New York rests here for now.
