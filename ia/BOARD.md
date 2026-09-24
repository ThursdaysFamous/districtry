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
| **BUILD THE GATE: a gap record's stated count against the file it describes** | **assigned 2026-09-24, DO FIRST** | 2026-09-24 | Your finding, your fix. Adam sent it to you. The `ia-board-chair` record told readers 43 of 99 counties while the file held 38, for eleven days, and #1034 corrected the NUMBER and added no gate — so the next Friday run can make it stale again in silence. **RE-MEASURED BY ME 2026-09-24 through `build_coverage_gaps.load_gaps()` so this row is not another stale claim: 155 records across 6 instances, 152 numbers across 67 records in the three reader fields.** Your board says 153; it is 152 now, which is the argument for the gate rather than against your count. Three are the checkable shape and all three are rewritten weekly: `ia-board-chair` states 38/99/61 against a file holding 38; `ia-supervisor-district-seats` states 18 against its own 18-long `counties`; `mi-commissioner-roster` states 83/48/35 against a members file holding 48 — **and that third one moved TODAY**, because Michigan's certified-returns roster took the state to 83 of 83 across two files, so treat it as in flux and settle with Michigan rather than encoding its shape from a snapshot. **THE DECLARATION MUST BE EXPLICIT, NEVER A HEURISTIC.** 152 numbers of which three are checkable means any rule that infers which number to check is wrong about 149 of them: district numbers, years, area codes, a parcel count, "911", a metres figure. **AND THE VOCABULARY ALREADY EXISTS — do not invent a second one.** `build_history_page.py` solved this exact problem for its measured tiles with a deliberately tiny grammar (`keys` / `features` / `sum:<field>` / `count-nonzero:<field>` / `people:<fields>` / `keys-naming:<fields>`, `METRIC_RE` at line 109). Two readers of one question is where this fleet's recurring defect starts, so lift or share that reader rather than writing a parallel one. **Constraints:** the declaration must NOT ship — the reader fields are length-capped and go to the Data gaps panel, so it belongs beside them and out of the served file, and `--check` must prove the shipped `coverage-gaps.json` is byte-identical after it. It must fail in BOTH directions (record says more than the file, and less). It must refuse a declaration naming a file or field that does not exist, rather than passing vacuously — the `ACCEPTED_DROPS` property. Negative-test every branch and say which you witnessed failing. **Scope is the fleet, not Iowa:** the records live in one guidebook block and the gate belongs in `scripts/`, so it covers all six instances; coordinate with Michigan before touching their record's text. |  |  |  |
| **The 18 counties that elect by district and publish no district have no gap record** | **merged #1095 `9d7f318`** | 2026-09-22 | The one thing my answer to your STOP did not hand you. Measured on main today: of the 35 PLAN 3 counties, 17 have a districted roster and **18 do not** — Black Hawk, Butler, Calhoun, Cass, Chickasaw, Dickinson, Guthrie, Howard, Ida, Kossuth, Lee, Montgomery, Osceola, Palo Alto, Sioux, Washington, Winnebago, Worth. Their pages already say the true thing (Black Hawk: "elects its board of supervisors by district … which district each one holds is not published in the source this page reads"), and **no gap record says it**, so the absence is invisible to `coverage-gaps.json`, to COUNTY_STATUS and to a reader who might close it. This is a SHARPER absence than the existing `Supervisor roster covers 17 of 99` row, which pools these 18 with the 14 PLAN 2, the 2 transitioning and Jones — counties where there is no district to name at all. A district exists in all 18 and somebody publishes it. `data-quality`, not `no-source`: the card names the right people and cannot place them. Follow the gap-record skill; the reader fields take no hostname, no status code and no date. |
| **Answer to your STOP on the at-large adapter** | **answered, no action for you** | 2026-09-22 | You were right that a flat roster is not an at-large board, and right that the fleet already has a rule against saying so. You were reading main `d428959`, which predates #1088 — the adapter it ships never rendered the 35 + 2 as at-large. `IA_PLAN_PAGE` gave plan 2, plan 3, transitioning and plan-less counties their own lede and map-link note from the start. **What your objection did catch is everything BESIDE the lede**, and it was real: the meta and og description said "elected at large across the whole county" on all 35, the index page suffixed each row ", at large", and both the index lede's tally and the builder's operator line counted them. `at_large` was picking the renderer and asserting the election method at once. Fixed on the branch (`793aebc`): the plan table now carries a `desc` and an `index_note`, the record carries `claims_at_large` (plan 1 alone), and the flag means only "render the flat body". The index now reads **39 at large · 14 countywide · 18 by district · 2 at large until 2026 · 1 with no method stated (Jones) · 17 districted** = 91, which reconciles exactly with your breakdown — your 53 "at-large" is plan 1 plus plan 2. **Your three other corrections all stand and are in.** `ba34bea` proves the `NOT_COUNTY_BOARDS` reason was wrong when written and not overtaken — that entry is gone. `ia_board_contact()` was already reading the file, which is the part worth keeping: a file can be adapter-read and still need a `NOT_COUNTY_BOARDS` line because `check_registration()` subtracts only what the ADAPTERS read; it is moot now that an adapter reads it, so nothing changes in the gate. And its docstring's two counts were each short by one — measured 2026-09-22, 91 boardPhone and 90 supervisorPlan, corrected and dated in `9b008ca`. **One thing to set straight: Wright.** You read it in both withheld groups. That was my briefing MESSAGE, not the shipped records — `ia/data/app/coverage-gaps.json` has `-impossible` at six (adair, floyd, humboldt, lucas, pottawattamie, tama) and `-disagrees` at two (warren, wright), verified today. My message was wrong; the data was not. **Nothing here is yours to do.** Your three assigned rows above are unchanged and still the order. |
| **The chair gap record's NUMBER is fixed; its FORM is still not stale-proof** | **half CLOSED 2026-09-19 by #1034; the gate half is open** | 2026-09-19 | `ia-board-chair`'s reader text says "in 43 of Iowa's 99 counties… In the other 56 it cannot". The file holds **38**, so it is 38 and 61. This ships to the Data gaps panel, so it is wrong on the page a reader opens. `ia/WATCH.md` line 39 carries the same 43. This session already has it — its own last summary names it. |
| **Supervisor roster covers 17 of 99 counties** | open | — | Still the headline gap for DISTRICTS: `ia-supervisor-members.json` keys members to a district in 17 counties and the other 74 name people with no district at all. **It no longer caps the per-county pages** — since #1088 those 74 ship from `ia-county-officers.json`, so 91 counties have a page and 8 do not (the ones that file withholds, both recorded as gaps). The old note here said 26 counties get no page; that was true before #1088 and is not now. |
| City card names nobody | open | — | `ia-city-contact.json` covers 939 cities with contact details and no officeholder names; 834 have no website at all. |
| Precinct card cannot say where to vote | open | — | no-source. The polling-place precinct column was dropped upstream. |
| Johnson County districts pending; Jones County absent from the state layer | open | — | Two county-level data-quality holes. Johnson's minutes host refuses `districtry` in robots.txt — that is the host's answer, not a bug. |
| Marion ward card blocked | blocked | — | Access control. Never worked around. |
| **Mitchell County: re-read the page and fix the parser** | **assigned, second** | 2026-09-19 | Manager's answer to your open question, and it is agreement rather than an override: do NOT pass `--allow-drop`. The guard refused to write rather than drop five real supervisors, which is correct, and is why the supervisor roster has been frozen since 2026-08-28. Fix the cause. |
| `ia-county-officers.json` phone numbers have never been measured | **assigned, third** | 2026-09-19 | Yes to your question, with one condition: measure and report before building anything. ~305 numbers across 99 counties, same defect class #1000 fixed on the city rosters — a switchboard number rendered as a named person's direct line. A clean result is a result worth recording. |

**Do not re-probe the blocked counties with different headers.** Measured
2026-09-06: of the 20 counties the gated run calls unreachable, nine answer 403
and eight of those are Cloudflare, seven serving a managed challenge. A complete
header set with this project's own user-agent moved none of them, and a browser
user-agent is not an option. Polk is **withdrawn** rather than blocked — review
could not reproduce it, so it is client-dependent.

## Status — this session owns this section

**2026-09-24 (night, later) — #1139 merged and verified by content. THE BOARD
ENTRY ABOVE IT WAS WRONG AND #1140 CORRECTS IT WHILE FIXING WHAT WAS ACTUALLY
BROKEN.**

Winnebago is on main at `a92cee4`: the outline is gone, its page names Terry
Durby, `rank_link` ships, the tripwire's basis reads 81 districts in 19
counties, the cache is v13, and the gap record holds 14 counties with
`winnebago` absent and its stated count at 14.

### I re-tested my own queue item before building it, and it did not hold

Item 2 said `build_endpoint_inventory.py` "is named as a regenerate step in NO
workflow and NO skill", so the skills "run a green local battery, push, and
meet it in CI". The first half is true. **The second half is false.**
`gap-record` §7 ends "and the steward battery", `county-n-plus-1` says "the
whole steward battery before the push", and `build_endpoint_inventory.py
--check` is IN that battery. Every one of these is caught LOCALLY. I conflated
§7's REGENERATE list with the gate battery, which is exactly the distinction
§7 keeps.

### What the re-test found instead is worse and is real

Two hand-kept lists answer one question, and they had DIVERGED.
`county-n-plus-1`'s copy was four commands short of §7: `build_about_page.py`
(the one §7 itself calls most easily missed and not optional),
`build_sitemap.py`, `validate_gap_counts.py`, and **`--metro michigan`
entirely** — a whole instance, because the copy was written when there were
two non-Illinois statewide instances, its prose still said "Both instances",
Michigan shipped into one of the two lists, and nothing compared them.
`roster-pipeline` and `new-layer` carry no such list at all, so they were
never at risk.

**A premise I recorded as measured was an inference.** The measurement was
`grep -rln build_endpoint_inventory` returning three paths; the CONCLUSION
about red CI was not measured and was wrong. Re-test a queued item against
the tree before building on it — the grep was right and the sentence built on
it was not.

### #1140

`county-n-plus-1` points at §7 now and keeps only its county-specific steps,
so there is nothing left to diverge. §7 gains three lines, each from a step
this session got wrong today rather than from reading code:
`build_ia_gap_outlines.py` with its ORDER (it reads the SHIPPED file, so run
early it reports nothing stale — my mistake this afternoon),
`generate_metro_files.py` (a retired outline drops a worksheet entry and needs
the cache bump), and `build_endpoint_inventory.py` (a data/app file COUNT
moves on an add as much as a delete). §7's list was then run end to end on a
current tree as the test of the procedure itself: every generator no-ops.

### Deliberately not shipped

Running §7 surfaced a two-line `sitemap.xml` refresh — Mitchell's and
Winnebago's pages, the two #1139 changed. `build_sitemap.py`'s own docstring
already records that `lastmod` reads the last commit to touch a file, so a
page changed IN a commit reads as yesterday and its `--check` tolerates
exactly one day. It recurs by design and self-heals, so it is churn, and
restating it in §7 would be the two-copies defect this change exists to fix.

### Queue

1. **Michigan's `mi-commissioner-roster` declaration** — 83/48/35 across two
   disjoint files, theirs to confirm. Untouched.
2. **`ia/data/source/ia-county-internal-points.json` encoding drift** —
   `build_ia_gap_outlines.py` writes the escape where the committed file
   carries a literal em-dash, so running that builder always dirties it. I
   reverted it twice today. A line at most.

**2026-09-24 (night) — #1137 merged and verified by content. WINNEBAGO SHIPS
as #1139, and the queue's item 2 is done.**

#1137 is on main at `1427f64`; all three corrections survived and
`validate_gap_counts.py` reports 4 counts agreeing. The branch was restarted
from main, because GitHub deleted it on merge and a merged PR cannot carry
follow-up work.

### The predicted fix was not the fix

The gap record said the plain fallback paths would recover Winnebago. True,
and it treats the symptom. Measured: the home page links FIVE urls matching
`supervisor` and the board's own is SECOND, so a first-match rule was always
going to take the wrong one — `board_of_supervisors/boards_commissions/`, a
different set of bodies, matching only on its HREF while its LABEL says so.
**The label is what the county says a page is.** Ranked on the label, same one
link and same three-page budget, Winnebago keys Durby 1, Smith 2, Jensvold 3
in slot one.

### The obvious extra key is measured wrong and cost a county

Preferring the shallowest path looks like preferring a section root. On the
commonest county CMS it is the opposite: Linn's board page is
`/123/Board-of-Supervisors` at depth 2 while a NEWS ITEM and two CALENDAR
EVENTS sit at depth 1. That draft promoted the news story and **LINN DROPPED
OUT after keying correctly for weeks**. A query string replaced depth — an app
endpoint takes an id, a section page does not. **The 40-county regression is
the only thing that could have caught it: the depth draft passed Winnebago and
lost Linn in the same run.** Final sweep against the pre-change baseline —
gained Winnebago, lost none, every other county identical, one citation moved
(Mitchell, off an `#agendas` fragment).

### My own self-test put three hostnames into a measured surface

`probe_user_agents.py` reads a scheme-and-host literal as an address a file
reaches, so absolute fixtures registered Winnebago and Linn onto this
scraper's surface while the other 38 counties it fetches stayed absent — their
urls come from a data file — plus a fabricated `example.gov`. **A measurement
shaped by where a url happens to be quoted is worse than none.** The fixtures
are the pages' own relative hrefs now. And the comment explaining it had the
SAME defect: it quoted the scheme between backticks and the probe read a host
named a backtick. Caught by the gate, not by me.

### Two things I got wrong in the doing

Ran `build_ia_gap_outlines.py` before regenerating the shipped
`coverage-gaps.json`, which is the order §7 gives — the outline builder reads
the SHIPPED file, so it still wanted Winnebago and reported nothing stale.
Run in order it flags the orphan exactly as designed. And I shipped an
unrelated encoding churn in `ia-county-internal-points.json` into the working
tree twice before noticing the builder writes `\u2014` where the committed file
has a literal em-dash; reverted both times, and it is a latent drift anyone
running that builder will hit.

### Dickinson is not part of the regression

Its robots.txt answered the captcha-shaped 202, served 25 minutes later, then
202 again. The Black Hawk lesson a second time. On the allowed run its pages
carried no readable district and it fell out of the roster it had been
PRESERVED into — not caused by this change, not probed further, and the
preservation question it raises is the builder's.

### Queue after this

1. **Michigan's `mi-commissioner-roster` declaration** — 83/48/35 across two
   disjoint files, theirs to confirm, still untouched.
2. **`build_endpoint_inventory.py` is named as a regenerate step nowhere** —
   measured this afternoon, and this change hit it again exactly as predicted.
   Its own PR: name it in `county-n-plus-1` / `roster-pipeline` / `gap-record`
   §7, or once where a change's remaining obligations are stated.
3. **The `ia-county-internal-points.json` em-dash drift** above, if it is worth
   a line at all.

**2026-09-24 (evening, later still) — #1137 is GREEN and held for the manager.
The queued deletion-trigger question is MEASURED, and its premise was half
wrong — mine.**

#1137 head `45d357a`, smoke SUCCESS at 17:50 UTC, `mergeable_state: clean`.
Not merged by me. A re-check is armed for 18:45.

### The deletion-trigger question, answered by simulation rather than reading

I deleted three Iowa gap outlines on a clean tree and ran all **93** static
CI gates, baseline first (93 of 93 green in this sandbox, so every failure
below is the deletion). **Four fired, and they are two different things.**

THREE ARE LOUD AND CORRECT, and name the file and the reader consequence:
`build_coverage_gaps.py --check --metro iowa` ("county 'floyd' has no
data/app/floyd-county-outline.json — the gaps panel fetches that file to
decide whether this gap is where a reader clicked"),
`ia/scripts/build_ia_gap_outlines.py --check`, and `validate_gap_counts.py`
relaying the builder. **An orphaned outline cannot ship**, which the question
as written assumed was the danger. It is not.

ONE IS THE REAL CASE: `build_endpoint_inventory.py --check`, which fails with
"has drifted from the tree it describes" and names nothing that moved.

### The premise was wrong in two ways and I wrote both

1. **`docs/EAM_STATUS.md` was never the unnamed case.** My #1136 commit
   message says "both are `--check` gates that the three deleted data files
   moved". Its diff is one cell, `67 → 78` — the Iowa supervisor roster's
   DISTRICT count, which those three counties raised — and **62 workflows
   already carry `build_eam_status.py` as a regenerate step** for exactly that
   trigger. The simulation confirms it independently: delete the three files
   and EAM_STATUS stays green.
2. **The trigger is not deletion.** Adding one file — an empty
   `zzz-probe-temp.json` — fails the inventory identically. `files = len([f
   for f in os.listdir(appdir) if f.endswith(".json")])`, a raw count, so it
   moves in BOTH directions. Every county that ships a roster file moves it,
   not only a gap record whose `counties` array shrinks.

### Why the two disagree, which is worth keeping

`build_eam_status.py` globs `data/app` too, but filters
`if os.path.basename(f) in index_html` — it counts the files the app
references **by literal name**. Every gap outline is `"dynamic_reference":
true`, its filename built at runtime, so the whole gap-outline set is
invisible to it. `build_endpoint_inventory.py` counts every `.json` in the
directory. Two readers of one phrase, "shipped `data/app` files", and here the
difference is defensible — they publish different things — but it is why one
moved and the other did not, and nothing says so.

### The narrowed gap, and what it is owed

**`build_endpoint_inventory.py` is named as a regenerate step in NO workflow
and NO skill.** Measured: `grep -rln` finds it in `steward/SKILL.md` (as a
`--check`), in its own output document, and in `smoke-test.yml`. So the skills
for the paths that add and remove these files weekly — `county-n-plus-1`,
`roster-pipeline`, `gap-record` §7 — run a green local battery, push, and meet
it in CI. That is the same failure §7's own prose already records about
`build_about_page.py` and `build_sitemap.py`.

Its own FAIL line does say "regenerate it", so it is self-explaining once hit;
the cost is only that it is hit after pushing. **Not fixed, and deliberately
not on #1137's branch** — a PR per piece. It is the next change once #1137
merges, and the question is whether to name it in three skills or once in the
place that says what a change still owes.

**2026-09-24 (evening, later) — #1137's two blocking fixes are pushed as
`45d357a`, and the review's third item is fixed with them. Branch head clean
against main, CI running.**

The two that held it:

1. `measured_metric.py`'s docstring stated its own byte-identity proof as
   "all twelve history pages". **It is four.** I corrected that on this board
   an hour earlier and the code copy did not move with it — which is this
   gate's own subject one level up, in the module whose whole job is stopping
   a stated number from outliving the thing it describes. Re-derived rather
   than copied from the board: `build_history_page.py` prints `4 page(s)
   written (il, wi, ia, mi); opted out: ca, ny`, and regenerating leaves all
   four unchanged.
2. The seven-line `PERSON_WORDS` comment was pasted twice, verbatim.

### The third item was worth more than a wording fix

The review also flagged `check_shipped()`'s docstring — "the declaration
reaches no reader — proven, not asserted" — as saying nothing about what the
proof was, and its failure message as asserting the shipped file "moved".
**I re-ran the negative test rather than reword it, and the message was
wrong.** With `counts` added to the builder's `FIELD_ORDER`, all six
instances fail — by CRASHING, not by moving: `render()` copies the allowlist
with `e[key]`, so the first record WITHOUT a `counts` key raises
`KeyError: 'counts'` before a byte is written. A moved file is the other path
and fires only if EVERY record carries a declaration. Both are caught because
the guard re-runs the builder's own check; diffing the shipped file would
catch only the second. The docstring records the test and the message no
longer names a cause it cannot know. **A guard that fires for a reason its
own message denies is a guard whose next reader mis-diagnoses it.**

### The skill duplicate predates this branch

`.claude/skills/gap-record/SKILL.md` §7 listed `build_about_page.py` twice.
Checked against `origin/main`: **both copies are there**, one line apart,
with different trailing comments and a column of misalignment — my new
`validate_gap_counts.py` line landed between them and made it visible. The
surviving copy is the one the prose under the block means by "the last two".
`validate_skills.py` reads 803 pointers where it read 804, which is the
deletion and nothing else.

### Re-run after the merge, not incremented

`validate_gate_counts.py` **81 / 109, unchanged** after merging main in —
checked because the pair moves when two correct branches meet, not only when
a gate is added. The three commits main gained since this branch's base touch
neither `smoke-test.yml` nor `CLAUDE.md` nor the steward skill, so there was
nothing for it to move.

**2026-09-24 (evening) — the gap-record count gate is built and open as #1137.
#1136 merged and is verified by content.**

The assignment is done: `scripts/validate_gap_counts.py` plus
`scripts/measured_metric.py`, four declarations on Iowa's two records, wired
into CI as one step. Battery 108 of 109 — the one failure is the cert
interception, now proven environmental three times today and green in CI on
both #1134 and #1136.

### The 152 / 153 disagreement resolved, and it argued for the design

Both figures are correct. The corpus holds exactly ONE comma-grouped number,
`1,659` in `lasalle-board-districts-stale`, and a thousands-aware pattern
reads it as one where `\b\d{1,4}\b` reads it as two. Two careful readers, one
corpus, the same hour, differing because the RULE was never stated. That is
the whole case for constraint 1, so the declaration names which number it is
and which field states it, and the check is `(?<!\d)38(?!\d)` against that one
field — a membership test, never an enumeration. Of 153 numbers in the reader
fields, three are file-backed; a rule that inferred would be wrong about 150.

### What the negative tests found

Every branch was run rather than written, and the one that matters most is the
real case: dropping a county from the chairs roster fires BOTH numbers —
"states 38, the source holds 37" and "states 61, the source holds 62". That is
the original 43/56 defect caught whole, and it is what earns the `of`
complement its place rather than checking the count alone.

**They also found a defect in my own gate.** `measured_metric`'s evaluator
calls `fail` and then CARRIES ON, because `build_history_page.py`'s `fail`
exits the process. Mine accumulates, so a declaration naming a metric outside
the grammar walked past its own refusal and crashed with a traceback instead
of a verdict. `fail_stop` raises and each entry catches, so a run still
reports all its failures at once. **A gate that cannot survive its own
failure path is not a gate**, and only running the branch showed it.

### A correction I owe

I said "twelve history pages" in the design note earlier today and in the
#1137 write-up's first draft. **It is FOUR** — il, wi, ia and mi; ca and ny
opt out of `history_page`. The byte-identity proof of the shared-vocabulary
extraction is 4 of 4, not 12 of 12. The proof stands; the count was wrong.

### Left deliberately undone

**Michigan's `mi-commissioner-roster`** states 83 / 48 / 35 across two
disjoint files and the brief said it moved that day. The gate supports it
today — one declaration per number, two of them naming the second file — but
the shape is Michigan's to confirm, so nothing of theirs is touched. That is
the follow-up.

### Still queued behind it

1. **Winnebago** — page discovery in `ia_supervisor_district_scraper.py`,
   measured to be worth one county plus a correctness point, needing the
   17-county regression #1136 ran.
2. **`docs/EAM_STATUS.md` and `docs/ENDPOINT_INVENTORY.md` went stale on
   #1136 because three `data/app` files were DELETED**, and no procedure names
   them for that trigger. The gap-record skill's §7 now names the count gate,
   but a data-file DELETION is a different trigger and still has no list.


**2026-09-24 (late) — the 152 / 153 disagreement is REAL, REPRODUCIBLE, and is
the assignment's own best argument. Design settled; #1136 holds the branch.**

The brief re-measured 152 reader-field numbers where my board said 153, and
offered the drift as the argument for the gate. **It is better than that: both
figures are correct and the difference is one character.** Measured on
`227082f` through `load_gaps()`, the whole corpus contains exactly ONE
comma-grouped number — `1,659` in `lasalle-board-districts-stale`'s summary —
and:

| tokenizer | count |
|---|---|
| `\b\d+(?:,\d{3})*\b` (thousands-aware) | **152** |
| `\b\d{1,4}\b` and `\b\d+\b` (mine) | **153** |
| `\d[\d,]*` | 159 |

So the manager read `1,659` as one number and I read it as two. Neither of us
mis-measured; **neither of us stated the rule**. Two careful readers, one
corpus, the same hour, and a figure that cannot be reconciled without the
method beside it — which is the fleet's own "state the figure WITH ITS METHOD"
rule failing in miniature, and exactly why constraint 1 (explicit declaration,
never a heuristic) is right. A gate that enumerates numbers would be measuring
its own regex.

### Design, settled — the four constraints and where each lands

**Where it lives: `scripts/validate_gap_counts.py`, beside the builder, run
ONCE.** `build_coverage_gaps.py` runs six times with different `--metro`/`--out`;
the count question is fleet-wide over one guidebook block, so folding it in
would run one fleet check six times and make each instance's run depend on
every other instance's data files.

**The declaration needs NO change to `build_coverage_gaps.py`, which I
verified rather than assumed.** `render()` copies an explicit `FIELD_ORDER`
allowlist and there is no unknown-key rejection anywhere in the module, so a
`counts` key on a record is non-shipped BY CONSTRUCTION — constraint 3 is
satisfied by the builder's existing shape, and `--check` byte-identity proves
it the way #1134 proved its blocker non-shipped.

**The shape**, beside `blocker` and out of `FIELD_ORDER`:

    "counts": [
      {"value": 38, "in": "summary", "file": "ia/data/app/ia-county-board-chairs.json", "metric": "keys"},
      {"value": 61, "in": "summary", "file": "...same...", "metric": "keys", "of": 99}
    ]

`of` carries the COMPLEMENT, and it is not decoration: when this record was
wrong it said "43 … the other 56" and **both numbers were stale**. A gate
checking only the 38 leaves the 61 free to rot.

**`in` is required, and that is the tokenizer lesson applied to my own gate.**
The check is `(?<!\d)38(?!\d)` against that ONE named field — an exact
membership test for one number, never an enumeration — so the gate can say
"this record states 38 and its file holds 37" without ever needing a rule for
what counts as a number in general. A declaration whose `value` does not
appear in its named field FAILS, which is what stops a declaration drifting
away from the prose it is supposed to guard.

**Vocabulary: shared, not rewritten.** `build_history_page.py`'s `METRIC_RE`
(line 109) plus `PERSON_WORDS`, `_people_in` and `measure_metric` lift into
`scripts/measured_metric.py` with `fail` and the repo root injected; the
history page imports it and its twelve pages must come back byte-identical,
which is the proof the extraction was faithful.

**Branches to negative-test** (constraint 4, and I will say which I witnessed
failing rather than that I wrote them): value above the file, value below it,
a `file` that does not exist, a `metric` outside `METRIC_RE`, an `of`
complement that no longer subtracts, a `value` absent from its named field,
and the vacuity guard — the gate must refuse to pass having found no
declaration at all, the property `validate_instance_registration.py` already
has.

### What I am NOT deciding alone

Michigan's `mi-commissioner-roster` states 83 / 48 / 35 across two disjoint
files and the brief says it moved today. I will ship the gate with **Iowa's
two records declared** and leave Michigan's to a follow-up after coordinating,
rather than encode a snapshot of a roster in flux. Adding a declaration does
not touch their reader text, but the shape their two-file split needs is
theirs to confirm.

### Blocked, and on what

#1136 is green (smoke success on 6371c0a), clean against main, unmerged, and
it holds `claude/iowa-expansion-plan-isjrwa` — the one branch I can push. The
gate is a separate piece and widening #1136 to carry a new script is what the
PR-per-piece rule exists to stop, so this is written down rather than written.
**Nothing about the design depends on the merge**; the moment #1136 lands I
restart the branch from main and build it.

One thing from the brief worth keeping: CI started NO run on #1134's branch
and the manager ran the battery by hand. It did run on #1136. Worth watching
whether it recurs.


**2026-09-24 (evening) — #1134 merged; three of its six counties now ship as
#1136. The builder I was going to write already existed.**

#1134 merged and is verified by content on main. The next piece was "write the
builder for the six counties that publish the seat join", and the first thing
I found is that `ia/scripts/ia_supervisor_district_scraper.py` has been doing
exactly that for 17 counties since August — matching each known supervisor to
the nearest district number behind four gates. **These six were never a
missing builder; they were a regex reading one shape out of three.** Widened,
it keys Butler 3/3, Chickasaw 5/5 and Howard 3/3, each agreeing exactly with
the independent reading in the gap record. The roster goes 17 counties to 20,
78 districts keyed.

### I predicted the shipped gate was unsafe, and it is not

Gate 3 is the 1..N bijection I had just proved necessary-and-not-sufficient,
so I expected the cyclic shift to pass through it. It does not. `key_page`
takes the nearest token in EITHER direction, and mixing directions per name
produces **collisions rather than a clean shift** — which gate 3 catches. I
tested a linear district-first page and Kossuth's real rotated one and it
refused both. **The shift was a property of my own directional probe, not of
this parser**, and I should have tested before hypothesising a defect in
shipped officeholder code. Twice while testing it I printed a hardcoded
verdict that my own data contradicted; both are corrected in the transcript
and I derived the rest from the gate results.

Kossuth and Worth stay refused, correctly, and are now pinned in the
scraper's self-test AS REFUSALS — a later directional "improvement" would
return a clean permutation shifted one position round the cycle, and nothing
else in the repo could see that.

### The safety check that mattered, and one that is missing

Re-measured against all 17 counties already shipped: every one keys
identically. 17 unchanged, 0 changed. Bremer and Hamilton refuse by robots.txt
and keep their preserved records — the preserve ruling working.

**`docs/EAM_STATUS.md` and `docs/ENDPOINT_INVENTORY.md` both went stale on
this change and neither is named by the gap-record procedure.** They are
`--check` gates moved by DELETING three `data/app` files, which is a different
trigger from editing a gap record, so §7's list could not have caught them. I
found them only by running the whole battery. Worth a look at whether the
data-file-deletion path has a named regenerate list anywhere.

### Still queued

1. **Winnebago** — page discovery, not parsing. `candidate_pages` prefers a
   link to the county's boards AND COMMISSIONS list and spends its three-page
   budget before the plain path is tried, which keys 3/3 when fetched direct.
   Measured across all nine counties the sweep skipped for want of a page, the
   fallback paths recover Winnebago ALONE. One county plus a correctness point
   (the scraper prefers a page about other bodies), and it re-ranks pages for
   all 40 counties, so it wants its own regression run.
2. **The gap-record count gate or derivation**, recorded at `8e6d478` and
   untouched. This change is itself an instance of it: I had to hand-edit
   "18 Iowa counties" to 15 in the record, the area line, and the WATCH row.


**2026-09-24 (later) — the chair count is right and the FORM is still not
stale-proof. The DO-FIRST item is half done and nothing gates the other half.**

Re-verified on main at `3ed0e1f`, four surfaces: the guidebook record, the
shipped `ia/data/app/coverage-gaps.json`, `ia-county-board-chairs.json` itself
and `ia/WATCH.md` line 40 all say **38 and 61**. #1034 fixed that on
2026-09-19 and it has stayed fixed. **That half is done.**

The brief's other half was "prefer a form that cannot go stale", and that is
NOT done. #1034 changed the number and added no gate — checked its own diff:
it touched the guidebook and WATCH and nothing under `scripts/`. **Nothing in
the repo compares a gap record's stated count to the file it describes**, so
the next time the Friday run moves the chair count the record goes stale
again, silently, exactly as it did at 43.

### How wide the class is — measured, not guessed

Swept all 155 gap records for numbers in the three reader fields: **153
numbers across 67 records**. Almost all are not checkable and must not be —
district numbers, years, area codes, a parcel count, "911", a metres figure.
The checkable shape is narrow: a record stating *N of M* where N is the length
of a shipped file. **Three match their file exactly today, and all three are
rewritten by a weekly workflow:**

- `ia-board-chair` says 38 → `ia-county-board-chairs.json` holds 38
- `ia-supervisor-district-seats` says 18 → its own `counties` array holds 18
- `mi-commissioner-roster` says 48 → `mi-commissioner-members.json` holds 48

So this is a fleet shape rather than one Iowa record, and the one that has
already failed is the one we know about because a person read it.

### Two ways to fix it; I would take the second

**Gate it.** Parse the count out of the record and fail naming the file's real
value — the `validate_doc_counts.py` / `validate_gate_counts.py` shape, and the
FAIL line is the copy to paste. It must fail when it cannot FIND the number,
or a reworded sentence stops being checked in silence.

**Derive it at build time**, which I prefer. `build_coverage_gaps.py` already
renders the block to each panel file and already runs six times in CI with
`--check`, so a count substituted there cannot be stale by construction — the
history page's measured tiles and the legislator pages' `len(roster)` are the
same rule, and the history page already carries a deliberately tiny vocabulary
for exactly this. The cost is a substitution syntax inside prose that ships to
readers, which is a real cost and is why it is worth stating rather than just
doing.

**I have not done either**, and the reason is mechanical rather than a
judgement about the work: #1134 is open on the one branch I can push, a gate
is a second piece, and widening a docs-only measurement PR to carry a new
script is the thing the PR-per-piece rule exists to stop. It is queued behind
the six-county builder, and this entry is here so the measurement is not lost
with the container.


**2026-09-24 — the 18 counties' board pages are measured, and the route is
live: SIX of them publish the seat join. #1134 is open.**

The `ia-supervisor-district-seats` record said each county's own board page was
"an unexamined route rather than a measured refusal, and it is the next thing
to try before any ask goes out". That is now measured, and the record's blocker
carries it as a dated `RE-MEASURED` section. **Butler, Chickasaw, Howard,
Kossuth, Winnebago and Worth** print which supervisor holds which district on
their own pages — 22 of the 78 supervisors in the record. Read through
`ia_county_chair_scraper`'s own robots gate, host pacer and districtry token,
so robots.txt was read before the first fetch of each host as the client that
fetches. **No county was written to; NOT YET ASKED still holds for all 18.**

Five fetched a 200 that is **not the roster page** (Black Hawk's home page
carries all five names and the word *district* zero times) — the route is
partly examined there, not closed. Seven were not fetched: three 403s,
Dickinson's 202 captcha shape (an access control, not worked around), and three
whose robots.txt was unreachable, where RFC 9309 makes us abstain and the county
has stated nothing.

**Nothing ships in #1134.** A blocker is never served, and the six
`build_coverage_gaps` runs plus the three page builders all come back
byte-identical — which is the check that it really is non-shipped. The reader
fields stay as they are, because they describe what the app can tell a reader
and that has not changed for any of the 18.

### My method was wrong four times, and the fourth is the one worth keeping

Each wrong version produced a confident answer. A ±200-character window takes
the **first** token in the window, so Butler read 3/3 with all three supervisors
in district 1 — impossible for disjoint districts, and that impossibility is
the only reason it was caught. A digits-only pattern read Kossuth, which spells
its districts as words, as publishing nothing at all. Letting a bare digit count
as an ordinal matched the tail of a phone number and put Dean Eastman in
district 7.

**And the one arithmetic cannot catch:** on a page that heads each row with its
district, reading name-then-district pairs every name with the NEXT row's
heading and returns a **perfect bijection shifted one position around the
cycle**. A cyclic shift of a permutation is still a permutation, so the 1..N
gate passes on an assignment in which every supervisor is in the wrong district.
Five of the six admit exactly one order; **Kossuth admits both**. A bijection is
necessary and not sufficient, and the builder must read the page's own row
boundaries rather than flat text.

Two smaller things measured on the way. **Worth's page prints "Term Expires:
2022" beside two current supervisors** — names maintained, term column not — so
a builder takes the name and the district off these pages and never a term or
an election date (the Cook County rule). And **Black Hawk's verdict moved
between two runs 25 minutes apart**, robots-unknown then 200, so an unreachable
verdict is worth re-asking before it is believed, which is the rule Wisconsin's
builder already holds.

### What I did not do, and why

I did not build it. The brief was measure and report before building anything,
and the build is a real piece: a structural row parse (Kossuth proves flat text
cannot settle it), count guards, retention, and a weekly workflow. **It is the
next thing I would pick up unless the manager redirects.**

The twelve that do not publish it are what an ask would be for — a narrower and
better-founded ask than one to all 18, which is what the record would have
supported yesterday. The five whose fetched page was not the roster page want a
better page-discovery pass first, and that could raise the six.


**2026-09-22 — STAND DOWN. Nothing unpushed, no PR of mine open, no check-in
scheduled.**

Confirmed rather than asserted: working tree clean;
`claude/iowa-expansion-plan-isjrwa` level with its remote; the only open PR in
the repo is another session's engine work on the phone card list. Two local
branches sit ahead of main by commit id and **`git cherry` marks all five `+`,
which is the squash-merge blind spot rather than unpushed work** — the content
is on main (the minutes-chair scraper, the supervisor scraper's `readOn`, the
WATCH row). Verify by content; a squash breaks every id-based test, which is
the same trap that made `--is-ancestor` report #1065 and #1095 as MISSING.

**Shipped today:** #1065 (the chair note's last stale copy, plus the
`robots_policy` managed-challenge fix) and **#1095** (the 18-county gap record,
18 county outlines, the outline builder's third read, and the gap-record
skill's §7).

### Two corrections to the stand-down brief, both about the record

**The 18 counties' district lines are NOT "published nowhere".** They are
drawn and they ship — `ia-supervisor-districts.json` carries 3 to 5 districts
for every one of them, and a reader clicking inside one is correctly told which
district they are standing in. What nobody publishes is **which supervisor
holds which district**. The record says so, and Black Hawk is why it matters:
it shipped its own district geometry from its own county service on 2026-08-26
and is in the gap anyway.

**The preserve ruling is already enacted here, not pending.** Measured on main
tonight: `build_ia_supervisor_roster.py` carries 22 references to the preserved
path and no `ROBOTS_REFUSED_DROPS`; Bremer and Hamilton are BOTH in the shipped
roster and both county pages exist. That landed in #1051 on 2026-09-19, the
same day the deletion was caught — the acceptance test being that
`check_roster_retention` went quiet on its own with no exception naming either
county. The posture stands for anything that touches the builder next; the fix
itself does not need redoing.

### For tomorrow, not started

- **#1102's `check_workflows()`** touches three Iowa workflows — the supervisor
  roster, the county-officers roster and the county-chair roster. Not verified
  here; verifying it is tomorrow's first item rather than tonight's.
- **The 14 PLAN 2 counties and Story** remain the open question, unchanged by
  the merge: districts drawn, members named, no member keyed. The option I
  would take is a second record, because a PLAN 2 supervisor is nominated by
  district and elected countywide, so the reader sentence differs. One record
  for all 33 instead is a one-line change to the outline builder's third read.
- **`#board-at-large-N` id fragments** on those 18 pages — an identifier, not
  an assertion, and the manager's adapter. Flagged, not touched.

**2026-09-22 (later) — #1095 MERGED as `9d7f318`, verified on the merged tree.**

Content confirmed on main rather than SHA ancestry, because these land as
squashes: the gap record is present with all 18 `counties` tagged, 28 outlines
ship and every tagged slug has one, the outline builder carries its third read,
the skill's §7 fix is in, and `ia/WATCH.md` names the record. Thirteen gates
re-run green on merged main, including `build_ia_gap_outlines --check`,
`build_about_page --check`, `validate_gate_counts` (72/100),
`validate_steward_mirror` (100 for 100) and `validate_structured_data`.

**CI CAUGHT ONE THING AND IT WAS THE SKILL'S FAULT, NOT THE OVERSIGHT'S.**
`build_about_page --check` failed on the first push: `about.html` published 154
recorded data gaps against a tree that now holds 155, because this change adds
one. The gap-record skill's §7 is titled "every file that reads the block" and
did not list `build_about_page.py`, which states the fleet's gap TOTAL — so one
record anywhere moves it. I followed that list exactly and went red on the one
gate it omitted, and so would the next person. §7 now carries it with the date
it was found missing. **A remembered subset is not the battery**, which this
project already records from Michigan's go-live; I re-ran the generated-page
gates afterwards rather than the handful I had in mind.

### Still open for the manager — the 14 PLAN 2 counties and Story

Unchanged by the merge and still not mine to decide. Benton, Buena Vista,
Carroll, Cherokee, Clarke, Dallas, Delaware, Greene, Jackson, Muscatine,
O'Brien, Page, Plymouth, Woodbury and Story are in the IDENTICAL structural
position — districts drawn, members named, no member keyed. The option I would
take is a second record, because a PLAN 2 supervisor is nominated by district
and elected countywide, so "which of these people represents my district" has a
different answer there. If one record for all 33 is preferred instead, the
builder's third read drops its PLAN 3 scope in one line.

*Also still flagged and still not touched:* the per-county pages mint
`#board-at-large-N` id fragments on all 18. An identifier, not an assertion —
`roleName` reads "Supervisor" and the prose reads "by district" — so nothing
false reaches a reader, and it is the manager's adapter.

**2026-09-22 — the 18-county gap is recorded and shipped as #1095, and the
brief's framing was wrong in the one place that matters.**

**THE ABSENCE IS THE JOIN, NOT THE DISTRICT.** The brief said these counties
"elect by district and publish no district". They publish the districts.
Measured on the shipped tree at `7f8cbef`: `ia-supervisor-districts.json` draws
**3 to 5 districts for every one of the 18**, so a reader clicking inside one is
correctly told which district they are standing in; `ia-county-officers.json`
names 3 or 5 supervisors in each, carrying `name` + `party` on 333 of its 345
supervisor records and `name` alone on the other 12; and
`ia-supervisor-members.json` keys members to a district in 17 counties, none of
them these. **Black Hawk is the county that makes it concrete** — `ia/WATCH.md`
records it shipping real district geometry from its own county service on
2026-08-26, and the guidebook's Johnson record points at it as the county that
"publishes its own", which is true of the boundaries and false of the join. It
is in the record anyway.

The record is `ia-supervisor-district-seats`, `data-quality`, reader fields at
227/213/179 against the 240 cap, **NOT YET ASKED** with the honest scope stated:
the two statewide files are all that was read and **no county page was fetched
for this question**, so the per-county route is unexamined rather than refused.

**It touched the outline builder, and that was not optional.** A `counties` tag
is a promise the panel can locate — the Michigan defect Adam ruled on. Iowa
shipped 10 outlines, exactly the 10 its existing records tag, and
`build_ia_gap_outlines.py`'s two reads (the shipped gaps file; the counties
whose supervisors are withheld) **could not reach these 18**, which are neither.
It gains a third read: the record's own population, PLAN 3 only. Yields exactly
18 and empties itself as counties gain the join.

### Open question — the 14 PLAN 2 counties and Story

Measured the same day: **Benton, Buena Vista, Carroll, Cherokee, Clarke, Dallas,
Delaware, Greene, Jackson, Muscatine, O'Brien, Page, Plymouth, Woodbury** and
**Story** sit in the IDENTICAL structural position — districts drawn, members
named, no member keyed. The brief said PLAN 2 counties have "no district to name
at all"; they draw 3 to 5 each, so that is wrong too.

They are deliberately NOT in #1095. **The option I would take:** a second record
rather than widening this one. A PLAN 2 supervisor is nominated by district and
elected *countywide*, so "which of these people represents my district" has a
different answer there — arguably all of them — and folding it in would make one
reader sentence cover two different facts about representation. Story is a third
case again (transitioning under Senate File 75). If you would rather have one
record covering all 33, say so and the builder's third read drops its PLAN 3
scope in one line.

### One thing I checked and did not act on

The per-county pages mint structured-data ids as
`#board-at-large-1..N` on all 18 — an `@id` URL fragment, not prose and not
`roleName` (which correctly reads "Supervisor"). It is an identifier rather than
an assertion, so it states nothing false to a reader or a crawler, and it is
your adapter. Flagging it rather than touching it.

### My own error worth recording

`build_coverage_gaps.py` caught `why` at **247 characters against its 240 cap**.
I had printed that number in a pre-check and not compared it to the limit —
a measurement taken and then not read is the same as not taking it.

**2026-09-22 — ANSWER TO THE MANAGER'S THREE QUESTIONS ON THE EXAMINED SCORE.
STOP ON Q1: an at-large adapter over all 91 counties would publish a false
statement about 37 of them.** Measured on main at `d428959`.

**Q1 — the split is NOT what you read it as.** `supervisorPlan` is the right
discriminator for how a county ELECTS, but it does not partition the officers
file into at-large and districted, because **a supervisor record in that file
has no district field at all** — 333 records are `{name, party}` and 12 are
`{name}`, and that is every one of the 345.

| | |
|---|---|
| At-large: PLAN 1 + PLAN 2 | **53** |
| PLAN 3 — district-elected | **35**, all 35 with names in the officers file |
| — of those, districts KNOWN (`ia-supervisor-members.json`) | 17 |
| — of those, districts known NOWHERE | **18** |
| TRANSITIONING (Johnson, Story) | **2** |

So the adapter's 91 breaks down 53 at-large / 35 districted / 2 transitioning /
1 no plan (Jones). **Rendering the 35 + 2 as at-large is the error Illinois
already has a rule against** — CLAUDE.md: "a districted county's members on
the at-large card would read as elected countywide." Johnson and Story are
mid-transition under Senate File 75, so even "at-large" as of today is a
sentence with a date on it.

Your own worry was right and is worse than you put it: for the **17** a page
listing names without districts understates what we know, and for the **18** it
states nothing about districts because nothing is known — two different
sentences, neither of them "at-large". The 18 are Black Hawk, Butler, Calhoun,
Cass, Chickasaw, Dickinson, Guthrie, Howard, Ida, Kossuth, Lee, Montgomery,
Osceola, Palo Alto, Sioux, Washington, Winnebago, Worth.

**Also: all 17 districted counties are in BOTH files.** Whatever the adapter
does, those people can be listed twice — with a district in one source and
without in the other.

**Q2 — absence, and it is not an independent variable.** `supervisorPlan` is
KEY-ABSENT on 9 and present-null on 0. Those 9 are **exactly the 8 withheld
counties plus Jones**. So the plan is missing precisely where the roster was
withheld; it is not a separate class of 9 counties with an unrecorded plan.
**Jones is the only county with supervisors and no plan** — one county's hole,
worth its own line, not a sentence on nine cards.

**Q3 — the reason was WRONG WHEN WRITTEN, not overtaken, so there is nothing
to carry forward.** Supervisors first appear in that file at `ba34bea`,
2026-08-28 (#598), with 92 counties — **sixteen days before**
`NOT_COUNTY_BOARDS` was dated 2026-09-13. The file did not change under the
reason. Nobody made a deliberate decision to keep supervisors out of the
supervisor roster after the fact; the exclusion asserted "row officers, not
supervisors" about a file that already carried them.

**Two things you will hit that are not in your plan.**

1. `build_county_pages.py` **already reads this file** — `ia_board_contact()`
   pulls `boardPhone` and `supervisorPlan`. So it is simultaneously in
   `NOT_COUNTY_BOARDS` and read by an adapter, which may make the
   reclassification cheaper than you expect, and means `check_registration()`'s
   semantics need a look rather than an assumption.
2. That function's docstring is wrong in both numbers: it says boardPhone
   "90 of 99" (**actual 91**) and plan "(89)" (**actual 90**).

**One correction to your withheld list:** Wright is in the GEOMETRY group with
Warren, not the Iowa-Code-count group; you listed it in both. The code-count
group is **six** — Adair, Floyd, Humboldt, Lucas, Pottawattamie, Tama ("the
county directory lists N, and Iowa Code 331.201 allows only 3 or 5") — and the
geometry group is **two**, Warren and Wright ("the county directory lists 5,
and the supervisor-district geometry seats 3").

**What I would do**, since you asked for a view and not just a correction:
split the adapter by plan rather than writing one at-large adapter. 53 at-large
counties get the Illinois treatment unchanged; the 35 PLAN 3 counties get a
page that names the supervisors and says the county elects by district, with
the district named for the 17 and stated as not published for the 18; Johnson
and Story say they are transitioning. That still takes E to 99 of 99, and it
does it without any card claiming a countywide election that Iowa Code does not
give those counties.

I have not touched any of this and am not starting it — it is yours.

**2026-09-21 (later) — #1065 MERGED as `2d933ec`, both pieces, verified on the
merged tree.**

All four files landed: `scripts/robots_policy.py`, `ia/WATCH.md`,
`ia/metro-worksheet.json` and its regenerated `ia/scripts/validate_index.py`
line. **SHA ancestry is the wrong test here** — it was SQUASH-merged, so
`0a2d781` and `fa5977d` are not ancestors of main and a `--is-ancestor` check
reports both MISSING while their content is present. Verify content, not the
commit id.

Nine gates re-run on merged main, all green: `robots_policy --selftest` (83
assertions), `probe_user_agents --check` (294 hosts), `generate_metro_files
--check` (117 regions), `ia validate_index`, `validate_gate_counts` (68/95),
`validate_steward_mirror` (95 for 95), `validate_python_hygiene` (511 files),
`validate_skills` (772 pointers), `validate_doc_counts` (35 claims).

**THE TWO PIECES SHIPPED IN ONE PR AND SHOULD NOT HAVE.** Piece 2 was held
unpushed to keep one PR per piece; the session's git hook then flagged it, and
the hook was right — this container is ephemeral and reclaimed on inactivity,
so a validated commit existing only in it is one that gets lost silently, and
the designated branch is the only one pushable. Losing the work is the worse
failure. The bundling was taken deliberately, stated at the top of the PR body
with both pieces described separately, and offered for splitting. **The lesson
is about ORDER, not about the rule:** a piece finished while an earlier PR is
still open has nowhere to go, so either open its PR first or expect to bundle.

*A risk measured before the push rather than argued about:* piece 2's challenge
markers can only fire on a body that is genuinely HTML, and before this change
every HTML body at /robots.txt allowed unconditionally — so the only hosts it
can newly shut are the challenge case it was written for. All four real robots
bodies in the tree classify `shape=None`, `served`, `allows=True`, unchanged.
`www.iowacourts.gov` is the informative one: Cloudflare-fronted and still plain
text, which is the correct distinction — Cloudflare INSERTING a block into
robots.txt is not Cloudflare SERVING a challenge instead of it.

*One correction to something I said while waiting:* I flagged that main had
"gained a new gate" (`validate_officeholder_names.py`). It had not —
`smoke-test.yml` is unchanged since the PR's base and that script was modified,
not newly wired. The gate-count pair never moved. I checked it properly by
building a throwaway worktree at `origin/main`, merging the branch into it, and
running the count gates on THAT tree, which is the only place the
"two-correct-changes-meet" failure is visible.

**2026-09-21 — resumed on three tasks; two had already been done or had
expired, and the third is measured clean.**

**1. The chair gap record was already correct.** #1034 fixed it on 2026-09-19:
the Data gaps panel reads 38 and 61 today, and `ia/WATCH.md` line 39 says "38
of 99 counties as of 2026-09-18". Checked against the SHIPPED panel file rather
than the guidebook block, since the panel is what a reader opens. The last
stale copy was somewhere nobody named — `ia-county-board-chairs.json`'s note in
`ia/metro-worksheet.json`, wrong twice over: 43 was the superseded total, and
the "38 from its board-of-supervisors page" put that new total in a DIFFERENT
quantity's slot (the split is 33 pages + 5 minutes). **#1065.** My first attempt
hand-edited the generated `validate_index.py` and was reverted; the worksheet
owns it. The replacement states no live count at all and names where each
figure lives, because this is the third thing in three days to go stale by
having a weekly-moving number written into a sentence.

**2. Mitchell needed no fix, and the probe found the defect this board's own
WATCH row predicted.** Measured 2026-09-21 with the scraper's client, robots
first: `mitchellcounty.iowa.gov` serves its real site again — 70-byte
robots.txt, `User-agent: *` empty group, home page 110,546 bytes, supervisors
page 155,651 bytes pairing all five supervisors with districts 1-5, an invented
path 404s. The suspension ended on its own and the 2026-09-19 run keyed
Mitchell 5 of 5 (shipped in #1048). **No parser changed, `--allow-drop` never
passed — the guard was right to refuse for six weeks.**

*What the probe found instead:* the host runs an INTERMITTENT bot challenge and
**I tripped it myself** with four rapid requests including an invented URL;
eight spaced reads afterwards all returned the real file. So one bad read of
this host is not evidence of a suspension, and the trigger is our request shape.
That interstitial proved the defect: `robots_policy.classify()` returned
`served` for it and `allows()` answered TRUE — a managed challenge read as
permission to crawl, in the fleet's single robots reader. Fixed: HTML at
/robots.txt is no longer parsed as one; challenge markers refuse, any other
HTML still ALLOWS (a host with no robots.txt is open, and refusing there would
shut hosts serving us data). 10 new assertions, 73 → 83. **Committed and held
off the branch until #1065 merges, so the two pieces stay separately
reviewable.**

**3. The officer phones are clean, and that is the result.** 391 numbers across
99 counties, measured offline: **zero shared between officers in a county, zero
repeated across counties, all 391 distinct.** No county's `boardPhone` equals
any officer's. 80 counties' four officers share one area+exchange, which is
courthouse direct-dial rather than a switchboard, and 19 span several. The
defect #1000 fixed on the city rosters — one number rendered as several
people's direct line — **does not exist in this file.** The card already labels
each number under its office row rather than as a personal line.

*One of my three tests was vacuous and is not counted as evidence:*
`ia-county-board-directory.json` carries no phone field (keys are county, plan,
seats, url), so "does an officer's number equal the county's main number" was
never actually asked. Answering it needs a comparand this repo does not hold.
Nothing is proposed to build here.

**2026-09-19, 22:39 UTC — the preserve ruling is live, and the weekly run proves
it end to end.** #1051 merged at 22:25. Rather than leave #1048 carrying a
roster that deletes two counties' supervisors until next Saturday, I dispatched
`update-ia-supervisor-roster.yml` on main — the fix is only real once a run that
actually reads the counties writes the file, because a cache fixture's dates
would assert reads that never happened.

**The run rebuilt #1048 and every check passes.**

| | deleting run, 19:30 | preserving run, 22:25 |
|---|---|---|
| counties / districts | 15 / 61 | **17 / 67** |
| diff | 44 insertions, **1,000 deletions**, two county pages deleted | 25 insertions, **4 deletions**, nobody unpublished |
| `check_roster_retention` | FAIL, two sources VANISHED | **OK, quiet on its own** |
| #1048 CI | red | **green** |

Bremer (017) and Hamilton (079) each keep three supervisors, carrying
`readOn` and `asOf` of 2026-08-28 and the reader-facing reason. Mitchell, read
this run, carries `readOn` 2026-09-19 and NO `asOf` — the distinction is in the
data rather than asserted. Both county pages exist again and say "last read
2026-08-28 and no longer re-read ... These names will go out of date"; Mitchell
keeps "re-read on a schedule". Iowa's llms.txt line stays at 17.

**THE ACCEPTANCE TEST WAS THE RULING'S OWN AND IT PASSED WITHOUT AN EXCEPTION:**
the retention gate reports six accepted drops and neither county is among them.
That is the difference between fixing a cause and excusing a symptom, and it is
the test to reach for the next time a gate objects to a builder.

**A correction to how I described this all evening.** I repeatedly wrote that
the two counties "left" and that their pages "were deleted". That describes
#1048's DIFF and never the site: #1048 was never merged, and main carried
Bremer and Hamilton with all six names throughout. A weekly run PROPOSED a
deletion and the retention gate refused it. The distinction matters — one is a
loss to go and fix, the other is a guard working — and I was loose about it.

#1048 is green and waiting on human review. Not mine to merge: officeholder
data.

**2026-09-19, 21:20 UTC — Adam ruled PRESERVE, and my accepted-drop fix was the
wrong one.** The ruling is fleet policy: preserve data we have already fetched.
A robots refusal stops us READING a county; it does not require us to unpublish
three supervisors we fetched legitimately while the county was serving. My
`ACCEPTED_DROPS` entries excused the symptom — they taught the gate to accept a
deletion — where the cause was that `build_ia_supervisor_roster.py` deletes.
Reverted on the bot branch, so #1048 is correctly held red by the gate again.

**Iowa was the outlier and that is the argument for the change.** Illinois
preserves (`PRESERVABLE`), Wisconsin re-asks an `unreachable` verdict before
believing it, and this was the builder that deleted. Shipped as **#1051**:
`ROBOTS_REFUSED_DROPS` → `ROBOTS_REFUSED_PRESERVED` with both audits intact, the
previous roster read in full and carried forward, and `readOn` stamped by the
SCRAPER rather than the builder — a builder run against a week-old cache would
otherwise date every county today.

**THE RULING'S OWN RISK IS THE PART WORTH REMEMBERING.** A preserved county
ships officeholders nothing re-verifies, and the instance-wide "Data last
verified" date would then assert a verification we did not perform. So `asOf`
and `asOfWhy` ride the record and BOTH reader surfaces say so. The county PAGE
was the one nobody had looked at: it said the roster is *"re-read on a
schedule"*, which is false for these two counties, in served bytes a crawler
reads. It now says last read 2026-08-28 and no longer re-read, with the reason,
and a still-read county keeps the scheduled sentence.

**The acceptance test was the ruling's own**: `check_roster_retention` goes
quiet on its own, exit 0, six accepted drops and none of them these counties.
That is the difference between fixing the cause and excusing the symptom, and
it is the test to reach for the next time a gate objects.

*Measured, not assumed:* both refusals re-verified on both host spellings
(Bremer HTTP 500, Hamilton `Disallow: /` in its own per-tenant file at its CMS
vendor); the seed dates come from commit `bce3108`, 2026-08-28, the last weekly
run that wrote either county. No roster data ships in #1051 — the builder was
exercised against a cache fixture rather than by re-scraping 39 county sites,
and a fixture's dates would assert reads that did not happen, so the next
weekly run writes the real file.

*Corrected:* #1049's body said 61 of 63 workflows lack the llms.txt step.
Counting only workflows that REGENERATE county pages it is 60 of 62 — the
denominator included `smoke-test.yml`, which runs `--check` and regenerates
nothing. The conclusion is unchanged, and the proposed gate is still unbuilt.

**2026-09-19, later — the workflow fix merged, and the roster PR's SECOND red
was a different gate doing its job.** #1049 merged at 20:29 UTC, so
`update-ia-supervisor-roster.yml` now regenerates llms.txt and next week's run
will not repeat tonight's first failure.

With llms.txt fixed, #1048's run got further and failed on
`check_roster_retention.py` — Bremer (017) and Hamilton (079) VANISHED, three
records each, with the gate's own instruction: *GO AND LOOK AT THE PAGE before
accepting this.* **TWO GATES FAILED ON ONE PR FOR TWO UNRELATED REASONS, and
assuming the second was the first would have been wrong twice in one evening.**

*Went and looked*, with `robots_policy.fetch_verdict`, reading robots.txt only
and never the refused pages, on both host spellings of each. Bremer answers
HTTP 500 on /robots.txt — disallow-all under RFC 9309 and this project's own
rule. Hamilton's /robots.txt redirects to
`cms2.revize.com/revize/hamiltonia/robots.txt`, a PER-TENANT path and so
Hamilton's own file rather than its CMS vendor's, whose `Disallow: /` at line 18
is the longest match for /. Neither county stopped publishing; this project
declines to read them. That is the Palo case already in `ACCEPTED_DROPS`, and
the builder already carries both in `ROBOTS_REFUSED_DROPS`, which is why the run
SUCCEEDED while dropping them.

**Carrying the last-known supervisors forward is ruled out elsewhere rather than
decided here**: `build_ia_county_chair.py`'s carry-forward takes `unreachable`
and never a refusal, asserted by its own `--selftest`. Bremer's 500 is a robots
file that could not be read, not a page that could not be fetched; either way
the decision is to decline, so nothing may be carried.

**AN ORDERING TRAP, MEASURED BEFORE IT COST ANYTHING.** The obvious move was a
separate PR putting those entries on main. It would have been red by
construction: on main the roster still carries both counties, and the gate's own
stale-audit reads that and fails — "is STALE — the source `017` is back with 3
record(s)". An accepted drop is only valid on the tree that already lost the
source, which is why the Palo and Adams entries each landed in the change that
caused their drop. The entries ride #1048 (`e859550`) and must not be ported.

**#1048 is still NOT merged and is not mine to merge** — officeholder data,
human review. Two commits of mine are on its branch to clear the two failures;
if a re-run force-pushes that branch both are discarded and both failures
return.

*Unchanged and still proposed:* the `build_llms_txt.py --check` gate that would
catch the other 60 workflows, and the two `SyntaxWarning`s in
`build_county_pages.py`. Neither is started.

**2026-09-19 — the supervisor run passed, the prediction held exactly, and its
bot PR went red for a reason nobody was watching for.** The weekly job started
19:30 UTC and SUCCEEDED: 15 Plan 3 counties, 61 districts. Mitchell keyed 5 of 5
off its restored host, Bremer (3) and Hamilton (3) left on the robots refusals
already recorded in `ROBOTS_REFUSED_DROPS`, and `bremer.html` and
`hamilton.html` were deleted. No name changed and no seat moved. That is the
full rebuild I did this morning, produced by the job rather than by me, and the
roster is unfrozen for the first time since 2026-08-28. It is **PR #1048 and I
have not merged it** — officeholder data, human review.

**The red was `build_llms_txt.py --check`, and reading it rather than assuming
Mitchell is what found a real hole.** `llms.txt` COUNTS the per-county board
pages; dropping two took the fleet from 220 to 218 and Iowa's own line from 17
to 15, and `update-ia-supervisor-roster.yml` regenerates the county pages,
about.html and the sitemap but not the file that states the count. Measured
rather than inferred: main at `0e829be` is green at 220, so the failure is the
change's own and not inherited; on the bot branch `--check` FAILs, the builder
fixes it, `--check` passes. Fixed in **#1049** (Iowa's workflow, mirroring
Michigan's), and #1048 carries a separate commit regenerating the file so this
week's roster is reviewable green.

**The wider finding, and it is the same shape this repo keeps hitting.**
`update-mi-commissioner-roster.yml` has carried this exact step and this exact
reason since Michigan hit it — "the builder tolerates two going dark, so it can
happen on an ordinary weekly run" — and it was fixed in that one workflow and
recorded nowhere else. **61 of the 63 workflows that regenerate county pages
still lack the step, and no gate asks them to**: `build_county_pages.py --check`
fails a workflow that does not regenerate ITS pages, and nothing does the same
for llms.txt. Not every one of the 61 can move the count — only a workflow whose
roster can gain or lose a whole county can — so the number at risk is smaller
than 61 and was not measured per workflow.

*Proposed, not built:* the recurrence-proof fix is a GATE in
`build_llms_txt.py --check` of the shape `build_county_pages.py --check`
already has, which catches all 61 without 61 edits and cannot go stale as
workflows are added. Cost: one gate, plus whatever workflows it flags on its
first run — an unknown number of one-line YAML edits across four instances.
The alternative is to keep fixing them one at a time as each goes red, which is
what produced tonight. Recommendation: write the gate. Not started; it edits
other instances' workflows and nothing asked for it.

*Also found, smaller, not fixed:* `scripts/build_county_pages.py` emits two
`SyntaxWarning`s on the runner's CPython 3.14 — `\.` and `\s` in docstrings at
lines 1465 and 1693 (Python 3.11 files the same two as silent
`DeprecationWarning`s, which is why they surfaced only when the runner moved).
Cosmetic, and printed twice per run in 63 workflows plus every CI run. The fix
is two `r` prefixes.

**2026-09-19 — the queue is clear and both changes are on main; one item is
waiting on a clock.** #1038 merged as `ca7a284` and #1034 before it, both
verified on the merged tree rather than taken from the PR page: the chair-page
line prints the set difference (30) where it printed the subtraction (21), and
`CLAUDE.md`'s stale 26 is gone. Nothing of mine is open.

**The weekly supervisor run has not been due yet, and a late run is not a
missing one.** Its cron is Saturday 17:30 UTC and it was 15:43 UTC when I
checked. Its last three runs started 19:55, 19:18 and 19:34 UTC — 1h48m to
2h25m after the cron — so the earliest plausible start today is about 19:15.
Nothing is dispatched; a replacement run for a job that is merely late would
race the real one. What the run should show, from the full rebuild I did this
morning and did not ship: Mitchell keying 5 of 5 on its restored host, and
Bremer (3) and Hamilton (3) leaving on robots refusals already recorded in
`ROBOTS_REFUSED_DROPS`, with `bremer.html` and `hamilton.html` deleted from
`ia/county-supervisor/`. If it opens a bot PR it is not mine to merge — it gets
read and reported. If it fails, the reason gets read before Mitchell is blamed
again.

**2026-09-19 — the queue is clear; #1034 merged and #1038 is open.** The
38/61 gap-record correction landed. The last item, the chair-page count, is
#1038: `build_county_pages.py` printed `len(chairs) - len(out)`, which is right
only if every county with a member list also has a chair, and nine do not
(Bremer, Franklin, Hamilton, Lyon, Mitchell, Pocahontas, Polk, Sac, Webster).
It is the set difference now — 21 printed where the answer is 30. `CLAUDE.md`
carried the same figure as 26 and is corrected with it, quoting no live value,
because all three counts move weekly and the line prints them. No page content
changes; `--check` reads all 198 pages back and names every one of the 2,980
people on them.

**Where the four items ended.** 38/61 shipped. Mitchell needed no fix — its
host's suspension had lifted and it keys 5 of 5, so the roster unfreezes on its
own at the weekly run. The phone measurement came back clean on
`ia-county-officers.json` and found the shape one file over, in the auditors.
The count fix is #1038.

**Two things are waiting on a yes, neither built:** labelling the 17 auditors
whose phone is their county's board line, and giving the supervisor builder a
recorded excuse path for a measured suspended host.

**2026-09-19 — the phone measurement: `ia-county-officers.json` is clean, and
the finding is one file over.** Measured this morning, numbers normalised to
digits so the two published formats compare. That file carries **391 named
people, all 391 with a phone**, and on the switchboard question it comes back
clean four ways: **zero** numbers held by two or more named people in one
county, **zero** row officers carrying their own county's `boardPhone` across
91 testable counties, **zero** numbers shared by named people in different
counties, and **345 supervisors carrying no phone at all** — the officer builder
already hoists a board-wide number into `boardPhone` and strips it from the
member rows, and the roster builder raises rather than letting one back in. A
clean result, recorded as one.

**`ia-county-auditors.json` is where the shape shows up: 17 of 89 testable
auditors carry the same number as their county's board line.** It is not a
pipeline agreeing with itself — the auditors come from their own association's
directory and `boardPhone` is derived from ISAC's supervisor rows, so two
independent publishers land on one number. And it is not a wrong number: Iowa
Code 331.504 makes the auditor clerk to the board, so the board's line IS the
auditor's office. What makes it worth reporting is the RENDERING — `ia/index.html`
puts that number in the person row beside the name and the County Auditor badge,
while the office group below it carries only a label and an address, so a reader
sees a general office line presented as one person's.

**Why no existing guard sees it.** The switchboard rule this project already
wrote down (EXPANSION_GUIDE Part 5) fires when ONE number covers EVERY member of
a body. An auditor is one person in a different file, so a test that looks for a
number repeated across a board can never fire on them. The test that does catch
it is the cross-file one — auditor's phone against the board's hoisted
switchboard — and nothing runs it.

**Proposed, not built:** the #1000 treatment, which is a label rather than a
data change — mark those 17 as the board's office line the way the Iowa city
rows say "City office number", and keep the number dialable. Waiting for a yes.

**2026-09-19 — Mitchell needed no parser fix, and the reason is on the record
already.** I was told to re-read the page and fix the parser, and that premise
does not hold: `mitchellcounty.iowa.gov`'s hosting account was SUSPENDED, so the
host answered every path with one 7,640-byte cPanel page. The repo measured that
on 2026-09-13 (#943, `serves_one_document`) — one day AFTER the 2026-09-12 run
that failed, and this job runs Saturdays, so today is the first run to exercise
it. **The suspension has since been lifted.** Asked through the scraper's own
gated path this morning, robots served and allowing, Mitchell keys 5 of 5 off
`/board-of-supervisors/`. There was never a parser to fix and `--allow-drop`
would have dropped a county whose page was coming back.

**The full rebuild passes, and it is not a no-op.** 15 Plan 3 counties, 61
districts. Against the shipped file that is Mitchell staying and **Bremer (3) and
Hamilton (3) leaving** — six named supervisors — both on robots refusals already
recorded on 2026-09-13, Bremer's a 500 on its robots.txt and Hamilton's a `*`
Disallow through its CMS vendor. No name changed and no seat moved. I did NOT
ship it: the weekly job at 17:30 UTC produces exactly this diff as a bot PR, its
workflow already regenerates the county pages the roster feeds (verified — the
gate names `bremer.html` and `hamilton.html` for deletion), and officeholder data
belongs in that reviewed PR rather than in one of mine racing it.

**One latent gap found, reported rather than built.** A measured robots refusal
has a recorded excuse path (`ROBOTS_REFUSED_DROPS`, one entry per county with a
reason and a date, added by a person). A measured SUSPENDED HOST has none — it
can only be cleared by `--allow-drop`, which the weekly workflow does not pass
and should not. Mitchell recovering makes that moot today; the next suspended
county freezes the whole roster again with no recorded way out. The fix is to let
that same recorded table carry a non-robots standing condition, and it is a
decision about a guard rather than a bug, so it waits for a yes.

**2026-09-19 — the 38/61 correction is in review as #1034.** The
`ia-board-chair` record said 43 of 99 and the other 56; the shipped file holds
38, so the Data gaps panel was making a false statement to a reader. It reads 38
and 61 now. `ia/WATCH.md` carried the same 43 and two figures that had moved with
it — the per-route split is a weekly measurement (33 board pages, 4 minutes, 1
carried on 2026-09-18, against 38 and 5 a week earlier), and **the floors stay at
30 and 3** rather than following it down.

The blocker log now carries the vantage correction I had only written on this
board, appended with the superseded 2026-09-06 sandbox measurement left above it.
The Actions runner reports **15** unreachable rather than 20, in a different
shape, and **the eight answering HTTP 202 are new**: four of them resolved on
2026-09-11 and were behind a challenge a week later. Nothing was re-probed. Polk
now carries both readings with whose vantage each is.

**Next: Mitchell County.** Re-read the page and fix the parser — not
`--allow-drop`. The guard refused to write rather than drop five named
supervisors, which is why the supervisor roster has been frozen since 2026-08-28,
and talking a working guard out of its answer is not a fix. Then the
`ia-county-officers.json` phone measurement, reported before anything is built,
then the `len(chairs) - len(out)` one-liner.

**2026-09-19 — board commits go straight to main.** Adam answered the question
this section carried: the board rule wins, and board edits from this session
push directly rather than riding a pull request. This entry is the first one
that did. PR #1032, which held the two entries below while the question was
open, is closed as superseded rather than merged.

**2026-09-19, later — paused for the night.** Nothing of mine is in flight.
The Status below was written against main at `881d3f0`; main is `8506c8c` now
and none of tonight's merges change any figure in it. Iowa's own reading of the
fleet-wide name gate that arrived with them (`validate_officeholder_names.py`,
which discovers every instance rather than listing them): **2,181 Iowa person
records, every one a name, nothing accepted or flagged.** Its whole-fleet total
reads 12,446 across 757 files on this tree — the 10,985 in circulation is the
figure that file's own docstring quotes as its SUPERSEDED OK line, so it is a
relay of a corrected number rather than a disagreement with the gate.

**What I would pick up first, in this order.** (1) Mitchell County's supervisors
page, because the weekly supervisor job has been red on its guard since
2026-09-12 and ran red again today, which is why the 17-of-99 headline has not
moved since 2026-08-28. (2) The 43/56 in the `ia-board-chair` record and in
`ia/WATCH.md` line 39 — 38 and 61 — since that one is wrong on a page a reader
opens. (3) The `len(chairs) - len(out)` line in `build_county_pages.py`, a
one-line fix for a build-log figure that is 21 where the answer is 30.

**2026-09-19 — in flight: nothing.** Last work merged as #1000 (Iowa city
phones say whose number they are) and #1016 (the weekly chair refresh). What
follows is a read of Iowa taken against main at `881d3f0` this morning, newest
first.

**The chair count fell from 43 to 38 yesterday and a reader sees it.** #1016
merged the weekly refresh and five counties left the file. Four — O'Brien,
Osceola, Palo Alto and Plymouth — now answer HTTP 202 on robots.txt, an access
control, where they resolved normally a week earlier; the fifth, Union, timed
out. A sixth, Dallas, left for a different and real reason: its minutes stopped
yielding extractable text. Henry joined. So the reader-facing pair is **38 and
61**, which is the manager's top task and is correct as written.

The good news underneath it: every one of the 38 records now carries a
`confirmedOn` date, so the carry-forward built in #897 is armed for all of them
rather than for Clayton alone. Clayton itself was the test — it went unreachable
again on the 18th and was **carried** rather than dropped, exactly as predicted.
A county that goes dark next week keeps its chair for up to 60 days instead of
vanishing.

**The blocked-counties note on this board is one measurement behind, and the
rule it states still stands.** That paragraph was measured 2026-09-06 from this
sandbox: 20 unreachable, nine 403s, eight Cloudflare, seven managed challenges.
The 2026-09-18 GitHub Actions run — the vantage the weekly refresh actually uses
— reports a different shape: **15 unreachable**, of which 5 are a plain 403
(Clayton, Decatur, Guthrie, Hardin, Polk), **8 answer HTTP 202 on robots.txt**
(Dickinson, Emmet, Jefferson, O'Brien, Osceola, Palo Alto, Plymouth, Sioux), 1
is a connect timeout (Union) and 1 is robots.txt answering HTTP 500 (Bremer),
with Cherokee and Hamilton separately refusing by robots.txt. Do not re-probe
any of them — the point of the correction is that the 202 group is **new**, not
that anything should be retried. Four of those eight were readable on
2026-09-11.

**Polk answers 403 from the Actions runner.** This board calls Polk *withdrawn*
because review could not reproduce the block. That reading is still right about
review's vantage — but the client that runs the weekly refresh got 403 on
2026-09-18, so Polk is not going to resolve on its own and should not be
expected to.

**"26 counties have a chair and no board list" is 30, and no source of that
number was measured.** Three figures are in circulation: 26 (`CLAUDE.md`, from
the 43-chair era), 21 (printed by `build_county_pages.py` on every run) and 30
(the actual set difference). The builder computes it as `len(chairs) -
len(out)`, which is only correct if every county with a board list also has a
chair — nine do not (Bremer, Franklin, Hamilton, Lyon, Mitchell, Pocahontas,
Polk, Sac, Webster). Measured: 38 chairs, 17 board lists, 8 counties with both,
so **30 counties have a chair and no page**. It is a build-log line rather than
anything a reader sees, and the one-line fix belongs in its own change because
board commits are prose only.

**The supervisor roster has been frozen since 2026-08-28 because its weekly
refresh is red, and that is why the headline gap has not moved.** The
2026-09-12 run stopped itself:

> Mitchell (5 districts) shipped last time and keyed nothing this time — that
> is a page to re-read, not a diff to merge.

That is the guard working: Mitchell's page stopped naming its districts in a way
the scraper reads, and rather than silently dropping five real supervisors the
builder refused to write. But nobody has read that page since, the job runs
again today at 17:30 UTC, and it will fail again until someone does.

**One red job that costs a reader nothing, recorded so nobody chases it.** The
legislature refresh shows failure on 2026-09-15. It scraped, built, validated
and pushed fine, then died at `gh pr create` on the account's GraphQL rate
limit. The pull request was opened by hand and merged the same day as #974, so
the Senate and House rosters are current. Nothing has changed to stop it
recurring.

## Open questions for Adam

- **Neither of my two open findings should jump the queue, and here is the
  ranking anyway.** Asked whether either should, my answer is no — but if one
  moves first it should be the SUSPENDED-HOST excuse path, and the reason is the
  failure's shape rather than its likelihood. When a county's host is suspended
  the supervisor build does not drop that one county; it refuses to write at
  all, so a single dead host freezes the roster for all 99. Mitchell froze it
  for a week and would have frozen it indefinitely had the hosting account not
  been restored on its own. The only escape is `--allow-drop`, which is the
  lowered-guard rule in another costume. It is dormant today, which is why it
  does not jump.
  The AUDITOR LABELLING is the lower-consequence of the two: 17 counties where a
  reader sees a real, working office number presented beside one person's name.
  Misleading in emphasis, not wrong in fact — the auditor does answer it, under
  Iowa Code 331.504. Worth doing, worth doing after almost anything else.

- **Mitchell County** — re-read the page and fix the parser, or pass
  `--allow-drop` and let the county go? I would re-read it: five named
  supervisors is a real loss and the page changing shape is the likelier cause.
- **`ia-county-officers.json`'s phone numbers have never been measured** for the
  problem #1000 fixed on the city rosters — a single switchboard number repeated
  across several named people. It carries roughly 305 numbers across 99
  counties. Worth the measurement, or leave it?
