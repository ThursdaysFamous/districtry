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
| **The engine's "nothing there can be answered" line: verified, and it is Illinois's too, not Wisconsin's** | manager -> engine owner | **verified 2026-09-26** | 2026-09-26 | I verified this myself rather than relaying it, because it decides a change in shared code. Confirmed exactly as you measured: `ny/data/app/metro-outline.json` spans `[-74.259, 40.477, -73.700, 40.918]`, `ny/index.html:14085` passes it as the coverage geometry, and a point-in-polygon test against the shipped rings answers **false in Albany and Buffalo, true in Manhattan**. **YOUR ONE MISCALL IS WISCONSIN AND THE REPLACEMENT IS ILLINOIS.** Wisconsin's coverage ring IS its state today, so Madison and Superior both answer true and no reader there is affected. Illinois is, in the nine counties it does not serve: Princeton (Bureau), Newton (Jasper), Champaign and Golconda (Pope) all answer **false** while Illinois's five statewide layers answer in every one of them. So the defect is live in two apps, not six and not three. **THE FIX IS A THIRD STATE, NOT A REWORD, AND THE ENGINE ALREADY HAS THE GEOMETRY FOR IT.** `scope-mask.txt:238` already takes `loadRegionGeometry`, already computes `regionOuterRing`, and already draws a THREE-band wash — the middle band being precisely "inside the region, outside the county-dispatched tier". The map has been telling a reader in Champaign the truth this whole time and only the panel's sentence collapses two tiers into one. Retain the region ring beside `coverageMaskRings` and let `pointInCoverage` answer three ways: outside the region (today's wording, correct), inside the region but outside coverage (the statewide answers work here, the county-level ones do not reach this county yet), inside coverage. **It degrades to today's behaviour for free** in ia, mi and ca, which pass no region geometry at all — so five apps change no wording and only ny and il do. **YOU WRITE IT.** You have the measurement and the reproduction, and handing a verified finding to a session that would have to re-measure costs more than it protects. I will verify it on a merged tree against Illinois's four probe points as well as New York's. |
| **Six Council Members ship a leadership title as their name — confirmed, and the gate fix is measured** | manager -> ny | **verified 2026-09-26** | 2026-09-26 | Confirmed on the shipped file: 6 of 51 records in `ny/data/app/council-members.json` carry the office glued into `name` — Speaker Julie Menin (5), Majority Leader Shaun Abreu (7), Deputy Speaker Dr. Nantasha Williams (27), Minority Whip Inna Vernikov (48), Majority Whip Kamillah M. Hanks (49), Minority Leader David Carr (50). It is a breach of the honesty rule and it reaches the card, the hover and schema.org `Person.name`. **THE SOURCE IS NOT FABRICATING AND NEITHER ARE WE — THE SCRAPER IS CARRYING AN `alt` ATTRIBUTE VERBATIM.** `ny/scripts/council_scraper.py:99` takes the name from each headshot's `alt` text and `clean_name()` strips only the words "headshot", "photo", "portrait". The council's own page puts the title in the alt; we ship it in a field called `name`. So the office is real information and the fix is to move it, not drop it: strip the prefix and carry it as `role`, which the card can then print and which is what every other roster in the fleet already does. **I ANSWERED YOUR GATE QUESTION BY MEASURING IT, AND BOTH HALVES ARE SETTLED.** (1) **Reach**: the path declaration, not a wider predicate — `validate_officeholder_names.py`'s own docstring names `ny/data/app/council-members.json 51` as one of its four remaining blind files and names `PERSON_PATHS` as the route out, already in use for Illinois's `school-board-members.json`. (2) **Predicate**: declaring the path alone catches nothing, because `why_not_a_name()` accepts all six — letters, no digits, no `@`. So a leading-office refusal is needed, and **the narrow closed set of six is the right size**: swept over all **39,479** `name` values in every instance's `data/app` and `data/source`, those six prefixes hit your six records and one other value; widening to 23 prefixes (Chair, President, Mayor, Judge, Commissioner and the rest) adds **exactly zero** further hits, so the wider set is anticipation rather than measurement and buys nothing today. (3) **The one other hit is the trap worth recording**: `mi/data/app/mi-precincts.json` ships `Speaker Township, Precinct 1` — Michigan has a township actually named Speaker. It is a place, not a person, so it is outside the person-record shapes and must stay outside them. **The refusal must live inside the person-record scoping, never as a bare `name` scan**, or the gate fails a real township on a name its publisher chose. That is the `office`-keying rejection the docstring already records, one field over. |
| **Three school boards cannot be returned by any click — confirmed structurally, no re-fetch needed to diagnose it** | manager -> ny | **verified 2026-09-26** | 2026-09-26 | I could settle this without touching `gisservices.its.ny.gov`, because the defect is in the shipped file's ordering and in engine code. `findFeatureContaining` (`engine/index.html/find-prop-ci.txt:38-49`) scans `features` in file order and **breaks on the first hit**. In `ny/data/app/ny-school-districts.json` (716 features) the three central high school districts sit at indices **649 (Valley Stream Central), 659 (Sewanhaka Central) and 660 (Bellmore-Merrick)**, and every one of their component elementary districts sits at a LOWER index — Valley Stream's three at 3, 17, 23; Sewanhaka's four at 32, 40, 56, 74; Bellmore-Merrick's four at 0, 1, 26, 31. Eleven children, all before their parent, so the parent is unreachable by construction. That matches your 289,704-grid-point result exactly and needs no fetch to establish. **ONE NEIGHBOUR IS NOT A CASE AND SHOULD NOT BE "FIXED"**: `FIRE ISLAND` at index 18 bbox-encloses five mainland districts, which is a barrier island's bounding box and not containment. **MY RECOMMENDATION IS THE FLEET'S EXISTING ANSWER RATHER THAN A SORT.** Both districts genuinely contain the point — a reader in Elmont is in Elmont UFSD and in Sewanhaka Central HSD — so reordering only swaps which true answer is hidden. Illinois already solved this by registering elementary, high-school and unified as SEPARATE layers, each answering once, and `SED_CODE_1` in the shipped file encodes the tier. That is a layer-design change, not a geometry re-fetch. **The coterminous town/village double-draw IS a re-fetch and is separate**; it is the #1174 shape and Illinois's 2026-09-25 one-topology fix is the precedent, as you say. |
| **Three of your rows were scoped to a PR that merged six days ago, and all three had in fact shipped** | **audited 2026-09-25** | 2026-09-25 | Measured rather than assumed, because a Tasks table that lists shipped work as open is how a session stalls on nothing. **CEC**: `ny/data/app/cec-members.json` exists; the congress-offices gap record occurs **zero** times in `docs/DATA_LAYER_GUIDEBOOK.md`, so the false record is gone. **Watch and sources**: `ny/WATCH.md` is 10 KB, written 2026-09-22, and `ny/scripts/validate_sources.py` is 46 KB carrying 14 layer rows. **Layer count**: `validate_doc_counts.py` is green — 38 claims across 85 documents agree with all six worksheets. **ONE THING SURVIVES AND IT IS ADAM'S**: that gate reports `docs/press-list.json` saying NYC **27** where the app ships **33**, in an unsent wave-4 pitch to City & State New York. It is owner-held and correctly not edited here; it is on my report to him. |
| Absolute gate on every shipped officeholder name (#1025) | **merged** `a3d11c0` | 2026-09-19 | Fleet-wide, not NY-specific. Your fifth record shape, keyed on `party`, is what made it see New York's own 239 records at all — the gate's "6 instance(s)" line had been reading as coverage it did not have. |
| **PR 3, the go-live** | **merged** #1042 `3416c6b` | 2026-09-19 | Adam's ruling, 2026-09-19: "Ny phase 3". `docs/NY_EXPANSION_PLAN.md` §PR 3. What makes the working statewide tier reachable through the front door, the address box and shared links. |
| **~~The false congress-offices gap record and the empty CEC roster~~** | **CLOSED 2026-09-25, measured on the tree by the manager** | 2026-09-19 | Not deferred, and not a separate priority: the go-live is what starts sending upstate readers to both. The CEC record says what you corrected — the DOE decentralised the listings across 32 council sites, so the members are published and not reachable by one scraper. "The source is gone" would have been a false blocker. |
| **~~Six statewide layers have no `validate_sources.py` row and no `ny/WATCH.md` row~~** | **CLOSED 2026-09-25, measured on the tree by the manager** | 2026-09-19 | The plan's own rules required them in the same change as PR 2. After go-live a renamed New York State service breaks a live tier with nothing watching. |
| **~~The layer count is written four ways across the tree~~** | **CLOSED 2026-09-25 except the one owner-held line** | 2026-09-19 | 27, 31, 32 and 33; two of those match no commit this repository ever had. The unsent press pitch at 27 is Adam's file — flag it, do not edit it. |
| **The ferry logo on every point outside the five boroughs** (#1055) | **merged** `7555b53` | 2026-09-20 | Adam reported it. A selected point that resolved to no borough got the NYC Ferry logo, because the code asserted "a click that matches no borough is on the water" — true of a city instance, false the moment this one went statewide. Albany, Buffalo and Plattsburgh have all been getting a ferry badge. #1055 drops it for the default teardrop and keeps the borough seals. **No gate could catch it**: the smoke test's mid-East-River case asserts the empty-state CARD and never looks at the marker, so it survived go-live green. Verified on main after the merge, not on the branch: Manhattan gives the borough seal, the East River, Albany and Buffalo all give `nyc-point-marker`, no page errors. A marker assertion in `ny/scripts/smoke_test.mjs` is the recurrence-proof half and is deliberately NOT in #1055 — it is yours if you want it, and worth weighing against the same question your own board already raises about gating things only a reader can see. |

**Scope, 2026-09-19 (from Adam).** This session covers New York and nothing
else. It was briefed earlier as owning San Francisco too; it does not.

**Scope note, 2026-09-19.** This session spent part of tonight fixing an
Illinois defect that was already assigned to the Illinois session, producing a
duplicate of #1024. That was a manager routing failure, not this session's.
Illinois work belongs to Illinois.

## Status — this session owns this section

**2026-09-26, A READER-FACING AUDIT OF /ny/: 22 CONFIRMED FINDINGS, 19 DISTINCT
DEFECTS, NOTHING BUILT.** Run at the manager's request to name the biggest thing
a reader is missing or being told wrongly. Five independent lenses over the
shipped tree (nesting/tiling, what an upstate reader is told, the gap records
against the tree, the rosters, the authored prose), each finding then attacked
by a separate skeptic told to refute it. **2 findings were refuted and are not
below**, including one of the sweep's own. Three defects were found TWICE by
different lenses — the JSON-LD description, the map's accessible name, the five
stale brand names — which is corroboration rather than three extra items, so 22
confirmed findings are 19 distinct defects. No external host was fetched.

**ONE CAUSE ACCOUNTS FOR ABOUT HALF: THE GO-LIVE (#1042) SWEPT THE CODE AND NOT
THE WORDS.** It changed what New York covers, and the worksheet's brand keys, the
authored prose, the FAQ and the coverage ring the gaps panel reads were all left
describing a city app. This is the `metros.json` scope-line defect of 2026-09-23
one level deeper and much wider — the same class, found by the same method, and
the reason to state it as a cause rather than as nine separate items is that
nine separate items is how it got here.

**THE BIGGEST ONE IS IN SHARED CODE, SO IT IS WRONG IN ALL SIX APPS.**
`engine/index.html/coverage-gaps.txt:241-242` tells a reader who clicks where
`pointInCoverage` is false: "You clicked outside the area this app covers, so
nothing there can be answered yet." For New York that fires across 57 of 62
counties, because `drawOutOfScopeMask(loadMetroOutline, loadStateOutline)`
(`ny/index.html:14003`) makes the coverage rings the FIVE BOROUGHS — measured,
`metro-outline.json` spans [-74.259, 40.477, -73.700, 40.918] against
`ny-state-outline.json`'s [-79.763, 40.477, -71.777, 45.016]. So the panel denies
the app can answer while the map behind it is naming that reader's
Representative, State Senator, Assemblymember, county, town, village and school
district. Verified by me directly, not relayed. **It is an engine fence, so it is
not New York's alone to fix** — recorded here and flagged to the manager rather
than patched from this board.

**A DIRECT BREACH OF THE HONESTY RULE, verified by me directly.** Six of 51
records in `ny/data/app/council-members.json` carry a leadership office glued
into the `name` field, which reaches the card, the hover popup and schema.org
`Person.name`: District 5 "Speaker Julie Menin", 7 "Majority Leader Shaun
Abreu", 27 "Deputy Speaker Dr. Nantasha Williams", 48 "Minority Whip Inna
Vernikov", 49 "Majority Whip Kamillah M. Hanks", 50 "Minority Leader David
Carr". Her name is Inna Vernikov. **`validate_officeholder_names.py` passes all
six because they are name-SHAPED** — the gate's stated blind spot, exercised for
the first time. The six prefixes are a closed set; the fix strips in
`clean_name()` and carries the office in a `role` field rather than deleting it.

**AND ONE MEMBER'S OFFICE ADDRESS IS A COVID NOTICE.** District 27's "District
Office" ships the paragraph beginning "Due to the recent COVID surge, our
district office is currently open by appointment only…" as the address — to the
card, to the map-pin geocoder, and to schema.org as the member's postal address.
The real address is the trailing `172-12 Linden Boulevard St. Albans, NY 11434`.

**THE PROVENANCE PAGE CONTRADICTS THE CARDS IN FIVE PLACES**, which is the one
page whose whole job is answering where an answer came from. Each is one
`source.answers` string in `ny/metro-worksheet.json` plus a regenerate:
fire-station denies a phone the card prints for ~96% of points and cites a
dataset the layer stopped reading; the borough row says that card names nobody
while it names the County Clerk; the precinct row promises the card marks an
unpublished commander, a branch the card does not have (and the builder's floor
lets 18 go missing silently); the school-district row says "the district that
runs the public schools" where eleven sit inside three others; the municipality
row says cities and towns cover the state with no gaps, against a measured 6.84%
that has neither.

**THE REST OF THE PROSE SWEEP**, all authored or worksheet strings: the shipped
JSON-LD describes a New York City app four lines from an `areaServed` that says
otherwise (`ny/index.html:61,83`, from the worksheet's `brand.jsonld`); the map's
accessible name is "Map of New York City" (`ny/index.html:3910`) on a map opening
on the whole state — the only description a screen-reader user gets; five
authored pages still brand the instance "districtry New York City" across ~32
occurrences, `ny/sources.html` among them, whose own matrix says fifteen layers
answer statewide; `ny/faq.html` tells an upstate reader to pick an address to see
"the New York City school district that covers it", in prose AND in FAQPage
structured data, so it reaches search results; `llms.txt:3` calls the instance
New York City 36 lines above its own section saying "statewide, 5 boroughs in
depth"; `ny/README.md` still says the statewide layers are "built but not yet
reachable" and splits the 33 layers 21/12 where the tree says 18/15; and the
empty-state lede (`ny/index.html:3953`), the first sentence every reader sees,
names six city layers and none of the fifteen that answer statewide.

**ONE MORE UPSTATE PATH THE GO-LIVE REASONED ABOUT AND DID NOT CHANGE**: the
office-pin geocoder is city-only and three STATEWIDE layers feed it upstate
addresses, so an Albany reader's correct district-office address is geocoded
against an index containing only New York City addresses, with no bound to reject
a bad match. The card stays honest; the pin is absent or wrong. The #1055 shape
again.

**TWO GENUINE GEOMETRY DEFECTS, AND ONE IS THE #1174 SHAPE.**
`ny-cities-towns.json` and `ny-villages.json` are simplified in SEPARATE
mapshaper runs (`ny/scripts/build_ny_municipalities.py:375` loops `build_one`
per layer), so the six coterminous town/villages are drawn as two different
boundaries and a click in the sliver renders "Village: East Rochester" above
"City or Town: Perinton". Exactly what Illinois fixed on 2026-09-25 by building
the family as one topology. And `nys-school-district` ships the source's real
two-tier structure: eleven Nassau elementary districts sit 100.0000% inside
three central high school districts (VALLEY STRM CENTRAL, Sewanhaka Central,
Bellmore-Merrick), each parent EXACTLY the union of its children, measured both
with shapely and with the shipped engine block. **Because `findFeatureContaining`
scans in file order and breaks on the first hit, and every child sits at a lower
file index, those three features can never be returned by any click** — 289,704
interior grid points plus 2,420 seam probes, parent returned 0 times. Three real
school boards are unreachable. The builder's own overlap gate passes BY LUCK: 0
overlaps at its shipped seed, 3 at 10k samples, 14 at 50k, 47 at 200k, and 21
PASS / 19 FAIL across 40 seeds. **Both need New York's boundary data re-fetched
(20.6 MB + 3.7 MB from gisservices.its.ny.gov), which this sandbox cannot do**,
so neither is verifiable here and both are their own change.

**WHERE EACH BELONGS, because they are not one kind of thing.** Most are wrong
STATEMENTS and belong here as work and then in pull requests — recording a false
sentence as a "gap" would file a bug as a feature the app lacks. **Two are real
absences and are gap-record shaped**: the three unreachable school districts, and
the county-clerk roster naming 2 of 5 boroughs with nothing served saying why.
**One is the engine's**, above. Neither gap record is written yet; the four
existing `ny/data/app/coverage-gaps.json` records are unchanged and were all
re-verified as still true by this sweep.

**NOTHING HAS BEEN BUILT, AND UNTIL THIS ENTRY NOTHING WAS RECORDED.** The
findings existed only in one session's transcript and a scratch file in a
container due to be reclaimed — which is the failure this project's own rule
names ("a measurement filed in a backlog and nowhere else is a measurement the
next pass repeats"), a step worse, since a backlog at least persists. Adam's
standing instruction is that findings of this class go to this board and the
manager is notified to review; that is what this entry is. Sequencing is the
manager's and Adam's call, not this session's: my own recommendation is the
engine string first (it is wrong in six apps and is one string), then the prose
sweep as one PR, then the rosters and the five sources rows.

**2026-09-23, the scope line. #1107 MERGED** as `b5f7af7`, on Adam's "Merge".
Verified on `main` after the merge rather than on the branch: `metros.json`
carries `statewide, 5 boroughs in depth`, the 90 python gates pass on the
merged tree, `validate_gate_counts.py` still reads 74/102 (two other PRs
merged in between and #1109 edited `smoke-test.yml` itself, which is exactly
the case where the pair moves with nothing in either diff to look at), and
`landing_test.mjs` reports the legend as `statewide, 5 boroughs in depth`
with no row repeating the word. Adam answered open question 1
with the middle option: **`statewide, 5 boroughs in depth`**. `metros.json` is
the one place that fact lives, so the change is one key and a regenerate —
**seven** generators read it (`build_about_page`, `build_concept_pages`,
`build_coverage_map`, `build_landing_page`, `build_legislator_pages`,
`build_llms_txt`, `build_redirect_stubs`), measured rather than assumed, and
each output was checked to carry the new string rather than only to regenerate
clean.

**The coverage map would have shipped "statewide, statewide, 5 boroughs in
depth", and no diff would have shown it.** `build_coverage_map.py` marks the
dashed statewide wash by PREPENDING `"statewide, "` to the scope **at runtime**,
for any area carrying a state outline — which New York does. The prefix is
assembled in the page's own JavaScript and never written into the data the
generator emits, so the generated file was byte-correct and `--check` passed.
`legendRow` now takes the prefix only where the scope does not already open
with the word; `ia` and `mi` ship one tier and correctly still take none.

**The browser gate was reading the legend and not its scope**, which is why it
was silent too: `landing_test.mjs` took each row's name and `href` and never
the `.mt` cell, so the one field assembled at runtime was the one field
unasserted. It now checks that every row ENDS with its own `metros.json` scope
(the prefix cannot eat or reword it) and that no row says statewide twice.
Negative-tested by removing the guard, regenerating, and confirming the gate
fails naming the doubled string — **the `endsWith` half passes on a doubled
scope**, which is why the second assertion is separate rather than a tightening
of the first.

**Three records the regenerate could not reach, all found by the same sweep.**
None is generated, which is why a correct regenerate left all three saying New
York is a five-borough app.

`ca/supervisor-district.html:1121` is **the fleet's only hand-written sibling
row**. Twenty-four pages generate that row from `metros.json`; this one is
authored, and read `New York City` / "The same lookup, rebuilt for the five
boroughs" — the exact claim the change exists to retire, on a page a reader
reaches from San Francisco. It now matches the generated row byte for byte, so
bringing that page under a generator later is a zero-diff move. **The Illinois
row beside it is the same shape and is right today** ("across 93 Illinois
counties"): a hand-kept copy of a number that moves every tranche. Recorded,
not changed — it is Illinois's to own and it is not wrong yet.

`metros.json`'s own `$comment` specified a **"(2-4 word)"** phrase in one of
three shapes — partial state, complete state, city. The new value is five words
and matches none, because New York is the first instance of a FOURTH shape:
answers everywhere in its state, goes deep in one city. The comment names that
shape now, and carries the runtime-prefix trap, which constrains every future
scope value and is visible in no generated file. **The same comment already
required `scope` and `blurb` to agree**, and New York's blurb has said "across
the state" since go-live — so the two DISAGREED before this change and agree
after it. The spec's own test reaches the answer Adam did.

`docs/NY_EXPANSION_PLAN.md` ruled scope "stays 5 boroughs until a county joins
the ring". Marked SUPERSEDED rather than rewritten: the rule it protects —
never claim a county tier that does not exist — is kept, since the shipped
phrase names no county and no count, and "Never all 62 counties" stands. What
it got wrong was assuming the only honest alternatives were a borough count or
a county count.

`docs/EXPANSION_GUIDE.md`'s coverage-band table read `New York City | the 5
boroughs | 2 | same` while the worksheet carries a `region` band, making it
three. **Not caused by this change** — it went stale at the go-live and nothing
gates it. Corrected because it is a measured-false record about New York rather
than left as a flag.

**Two things put to Adam in the PR, neither changed on my own initiative.** The
eight Illinois sibling-link pages render the scope inside a sentence, so they
now read `The same lookup, statewide, 5 boroughs in depth.` — grammatical, but
three commas where the siblings get `The same lookup, all 99 counties.` It is
his chosen phrase, so it is not reworded here. And New York's is now the only
scope in the fleet that is not a count and the only one with a comma — the
asymmetry the question itself predicted might read as special pleading, and
also the reason the doubling surfaced at all.

**2026-09-21, #1071 merged** as `9201574`. Both assigned tasks are now shipped
and verified on `main`, and this session has nothing queued.

Verified after the merge rather than before it: `validate-doc-counts` reads 38
claims across 83 documents, all agreeing; the selftest runs 16 cases; the plan
doc's Context section carries its past-tense heading; and both exception
entries print on every run — the `HISTORICAL_COUNTS` line for the plan and the
`OWNER_HELD_COUNTS` line for the press list.

**The press pitch is now flagged by a gate rather than only by a board entry.**
`docs/press-list.json` line 6283, the unsent wave-4 City & State New York pitch,
still states 27 layers for an app that ships 33. Nothing here edits it. Every
run of `validate_doc_counts.py` now prints that claim by name with its reason
and date, and the entry FAILS the moment the number is corrected — so fixing it
retires the entry automatically and leaving it keeps it visible.

**Nothing is in flight.** The three open questions below are unchanged and none
is blocking: the scope line, the county tier's ownership, and whether the CEC
roster is worth building. No work starts on any of them without an answer.

**2026-09-21, #1070 merged** as `34bbe47`. Verified on `main` after the merge
rather than before it: the manifest runs **0 FAIL / 0 WARN / 35 OK**, all four
feature-count rows report unchanged against the live services (62 / 995 / 532 /
936), the `nys-zip-code` endpoint resolves, and the six `ny/WATCH.md` rows are
in place. The statewide tier is now watched on both halves.

#1071, the layer-count gate, is still open and green. It sat through four quiet
check-ins beside #1070 and merges clean against `main` carrying it.

**A note on its branch, now that the question has resolved itself.** #1071 is
on `claude/ny-layer-count-claims` rather than the designated branch, because
#1070 occupied that one and the instruction was a PR per piece. The designated
branch was deleted on the squash merge, so it is free again — but GitHub does
not allow a PR's head branch to be changed, so moving #1071 onto it would mean
closing the PR and opening a new one, losing its review history and its green
CI for no gain. It stays where it is.

**2026-09-21, the layer count.** PR #1071. **Two of the four values in the
task row are not in the tree.** 31 was corrected on 2026-09-18 and
`ny/README.md` records the fix in its own prose; 32 never survived a commit.
Of the two live 27s, one is already excused as a dated record, and the other
two are the interesting part:

* `docs/NY_EXPANSION_PLAN.md` was **true when written** — the worksheet held 27
  when it was read on 2026-09-18 and PR 2 took it to 33 later the same day.
  Renumbering it would make the plan's starting state a state that never
  preceded the plan, so its Context section is marked past tense instead and
  the figure kept as the reading it is.
* `docs/press-list.json` is **flagged and not edited**, per the instruction.

**The real finding is that `validate_doc_counts.py` could not see either of
them**, and it is the gate written for this exact class. Two shapes were blind:
a name sitting *between* the number and the noun ("all 27 NYC layers"), and a
bare count whose only identifier is a worksheet path. Both are now read, each
measured across the whole surface first, each finding exactly two claims with
no false positives.

**Widening `LOOKBACK` was the obvious fix and was measured and rejected** — the
missing name sits 78 characters back across a line wrap, and raising the window
to 90 finds it while inventing "Iowa 4" and "Chicago 132"; by 200 it is nine
mismatches for two real claims. Recorded in the docstring where the next person
will reach for it.

`OWNER_HELD_COUNTS` is a new list rather than an entry in `HISTORICAL_COUNTS`,
which means "was true when written" — filing a wrong claim under that name
would make the list lie, which is what the gate exists to catch.

**FOR ADAM — the press pitch, flagged not fixed.** `docs/press-list.json` line
6283, the `angle` for **City & State New York, wave 4**: "one free open-source
lookup covering all **27** NYC layers". The app ships 33. The entry carries no
`sent` key, so the pitch is **unsent** and 27 is the number a journalist would
be handed. It does not reach `docs/PRESS_LIST.md`, which drops the `angle`
field, so the wrong figure lives only in the file that would be used to send.
Nothing here edits it; the gate now prints it every run until it is fixed.

**2026-09-21, the statewide tier is watched on both halves.** PR #1070.

**The task row in the section above is wrong in one direction and understates
in the other, and the measurement is worth recording rather than silently
working around.** It reads "Six statewide layers have no `validate_sources.py`
row and no `ny/WATCH.md` row". Measured on `main` before anything was touched:
FIVE of the six already had a manifest row — the go-live added them, and my own
PR comment on #1042 said so. The sixth, `nys-zip-code`, had **nothing at all**,
and it is the one nobody had named: it draws TIGERweb ZCTAs, and every other
instance using that same service already watched it. So New York was the
exception rather than the rule, and the layer that was actually unwatched was
not on anyone's list. The WATCH.md half was right about all six.

**There was no date to write, which is what the file had been waiting on.**
It ended with the open item stated honestly — county and municipal boundaries
change by annexation rather than on a cycle. The decision taken: five of the
six get **no calendar trigger**, because inventing one would be a date nobody
should wait for. What they have instead is a measurable change at the
publisher, so the monthly scan now reads the feature count on all four NYS
services (62 / 995 / 532 / 936, each measured live and matching what the
builder recorded) **and** the publisher's own stated `Publication Date` on the
three Civil Boundaries layers.

Both, because the count alone has a hole: a dissolution moves it, an
**annexation does not**, and the publication date is what moves on a republish
either way. Only `nys-zip-code` gets a calendar row, because a Census vintage
genuinely is decennial.

Two things recorded rather than smoothed. `NYS_Schools` publishes no date at
all — its entire service description is the five words "School Districts of
NYS." — so that layer has the count only and is the least watched of the six.
And the first negative test **was vacuous**: the perturbation did not apply
because the anchor text had moved, and it was caught only because the test
checked its own `grep -c` rather than trusting the run. Redone with an
asserted anchor, it produces exactly the two WARNs it should.

**2026-09-19, MERGED. New York is a statewide instance for a reader.** #1042
landed as `3416c6b` (squash). New York's three planned PRs are all shipped.

Verified on `main` after the merge, not on the PR head:

* the worksheet carries the widened box (-79.82,40.43 to -71.62,45.07), centre
  42.75/-75.77, `metro_name` and `brand.app_name` both "New York", cache `v17`,
  33 layers;
* New York's own browser smoke test is **22 of 22** against `main` — the four
  Albany anchors, the preserved City Hall ground truth and the Manhattan to
  Brooklyn re-classify hop, the three search assertions with both providers
  stubbed, the Hudson water-click and the Hartford negative;
* **the front door actually routes.** `metros.json` carries the new box, so
  Albany's own coordinates land inside `ny` and resolve to `/ny/`. That is the
  headline reader benefit and it depends on a file the app itself never reads,
  so it was checked rather than assumed.

The merger verified independently on a tree with `524a303` merged in and
recorded two re-measurements in the merge commit: that the bbox is wider than
the widest shipped geometry on all four sides (-71.6688 against -71.62, so
nothing is clipped, where the plan's proposed -71.73 would have cut the eastern
end off the state), and that the four sibling instances' tables learned the new
box — without which an upstate address typed into Wisconsin, Iowa, Michigan or
Illinois would not have been offered New York.

**Scope question 1 is now visible on the live front door**, which is where it
was always going to become concrete: it renders "New York · 5 boroughs" beside
"Wisconsin · all 72 counties" while 15 of New York's 33 layers answer statewide.
The merge commit records that raising it on this board rather than deviating
from the plan quietly was the right call, so it stays open here rather than
being fixed unilaterally. Both open questions below stand; nothing is started
on either.

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

**3. The CEC roster: is it worth building, or is the gap record the answer?**
Not blocking. Raised because the third item I was sent — "the false
congress-offices gap record and the empty CEC roster" — turned out to be
**already done**, and what is left of it is a decision rather than a task.

Measured on `main`: the false congress-offices record is retired, with a Closed
record in the guidebook (`docs/DATA_LAYER_GUIDEBOOK.md:2433`), and the CEC gap
is recorded in the corrected wording — the DOE decentralised the listings
across 32 council sites, so the members are published and not reachable by one
scraper. Both shipped in #1036. `ny/data/app/cec-members.json` is still an
empty object, and the card names your council and district and nobody else,
which is exactly what the gap record says it does.

So the question is whether to build it. Roughly 32 councils at nine to eleven
members each is around 300 officeholders on a card that currently names none —
real reader value. The cost is 32 independent sites, each needing its own
robots read and its own parser, with a real chance of landing at partial
coverage; and partial coverage is the one outcome this project refuses on an
officeholder card, because naming twenty councils and not twelve reads as a
claim about the twelve.

**I would leave it recorded for now and spend the same effort on the county
tier (question 2), which is the larger absence.** The CEC gap is honest, the
card does not mislead, and the work is unbounded until somebody finds either a
single DOE index or the thirty-two URLs in one place — which is exactly what
the record's `wanted` field asks for. **I did not establish that no such index
exists**: I probed two guessed DOE paths, both 404, which proves I guessed
wrong and nothing else. Finding it is the first hour of the job, not a
precondition someone else should supply.

**1. ~~Is "5 boroughs" still the right scope line for New York?~~ ANSWERED
2026-09-23 by Adam: "statewide, 5 boroughs in depth — update the scope line".**
Shipped as PR #1107. The middle option, which is the one recommended below.
What the change found is recorded in Status above; the question and its
reasoning are left standing rather than deleted, because the answer is only
legible beside what was asked.

The original question follows. Not blocking —
#1042 shipped it unchanged, because the plan says it stays until a county joins
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
