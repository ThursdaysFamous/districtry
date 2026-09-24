# districtry fleet board

**What this is.** One board per instance, plus this one for work that belongs to
no single state. It exists so the project's state lives in a file Adam can read
rather than in a session's head.

**How it works.**

- **Two owners, two sections.** The manager session owns *Tasks*. The state's
  own session owns *Status* and *Open questions*. Neither edits the other's
  section, because two writers on one paragraph is a merge conflict every time.
- **Board updates commit STRAIGHT TO MAIN**, in their own commit, never inside a
  feature PR. A board that waits for a PR to merge is stale for as long as that
  PR sits open, which defeats the point. Prose only — no data file, no generated
  region, nothing a gate reads.
- **A session updates its board in the same turn it finishes a piece of work.**
  Every entry carries a date. A board nobody updates is worse than no board:
  that is how `ia/WATCH.md` came to say the chair roster covers 43 counties when
  it covers 38.
- **No generator and no CI gate**, deliberately. This is hand-written markdown
  until it earns machinery. The manager reports a stale board to Adam rather
  than failing anyone's merge over it.
- **A question goes in Open questions, never into a session's own chat.**
  Adam's instruction, 2026-09-19: questions are "sent to their boards for you to
  invest and bring to my attention here". Adam does not read the state sessions;
  he reads the manager session. A question asked in a session's own turn is a
  question nobody answers, and it stalls that session while looking like
  progress. Write it dated, with what was measured, what the options are, what
  each costs, and which the session would pick — a question carrying a
  recommendation is far easier to answer than an open one. The manager settles
  what it can and puts the rest to Adam. A question that blocks everything says
  the word **blocking**, and is escalated rather than waiting for the next board
  pass.
- **The manager merges the state sessions' PRs.** Standing authority from Adam,
  2026-09-19, and his instruction to the sessions to accept it. No session waits
  on him for a pull request and none asks per PR. It lowers no bar: every merge
  is verified on the MERGED tree rather than from a PR body, and a PR that
  cannot be verified is held and reported. Holds are the mechanism working —
  #1018 is held because a bot shipped a name with a zero in it. It is not
  authority for a session to merge its own PR. Adam's own SEO and branding
  session is outside all of this, as it always was.

**Reporting.** The manager reports to Adam what changed **for a reader of the
site**. CI plumbing, gate counts and session bookkeeping are not reported unless
they are blocking something.

| board | instance | session |
|---|---|---|
| `il/BOARD.md` | Illinois | Illinois |
| `wi/BOARD.md` | Wisconsin | Wisconsin |
| `ia/BOARD.md` | Iowa | Iowa |
| `mi/BOARD.md` | Michigan | Michigan |
| `ny/BOARD.md` | New York City | New York |
| `ca/BOARD.md` | San Francisco | **none — no work in progress** |

Six instances, five sessions, one instance each. **San Francisco has no session
because no work is being done on it** — that is a deliberate state, not a gap,
and its board says so. A session gets assigned when there is work.

**Two corrections, both 2026-09-19, both from Adam.** This table first said Iowa
had no session; it does (`session_01GDDwuCzmWxgdbz3V8GHrjJ`, running since
2026-08-27), and the manager inferred its absence from a session listing that
omitted it — the one thing `docs/MANAGER.md` already says never to do. Query the
id; a listing that does not show a session is not evidence the session is gone.
The table then paired one session with both `ny/` and `ca/`; that session's
scope is **New York only**.

---

## Tasks — cross-cutting work, manager owns this section

Work here belongs to no single state. A task that lives inside one instance
belongs on that instance's board instead.

| task | owner | state | opened |
|---|---|---|---|
| **~~HELD #1137 (Iowa)~~ and #1138 (Wisconsin) — both MERGED** | manager | **MERGED 2026-09-24 `1427f64`, `cd4e118`** | 2026-09-24 |
| ↳ **#1137** — Iowa fixed both held lines and turned my one NOT-BLOCKING note into the better finding. I had said the shipped guard surfaces a `KeyError` rather than a drift report and called it a docstring clause; Iowa re-ran it as a negative test and came back with the CAUSE — `render()` copies the allowlist with `e[key]`, so the first record WITHOUT a `counts` key crashes before a byte is written, and the moved-file path fires only if EVERY record carries one. So re-running the builder's own check catches both where diffing the shipped file catches the less likely half, and the failure message no longer names a cause it cannot know. Re-verified: docstring says four history pages and four are written with nothing changing on rebuild, the duplicated comment is gone, all four declarations still pass, 99 of 99 static, 803 skill pointers, 81/109. One cosmetic leftover noted, not held — the SUCCESS line still says “no shipped coverage-gaps.json moved”. **#1138** — 17 more alderpersons, Black River Falls 8 over 4 and Neenah 9 over 3; 30 municipalities / 261 districts / 285 people, LOST 0, every count matching the file and 30 + 129 = 159. **The check that carried it is one neither side set up for**: all 17 e-mail local parts match their own row's name, which a separator-count parser filing one member's contact onto another's row cannot produce on either page. And `require_ward_is_district` was read rather than taken on its docstring — it reads LTSB's OWN ward-to-alder filing and requires the identity mapping live on every run, so Black River Falls' ward numbers are not assumed to be district numbers. Holding Oconomowoc is right: “District 1 seats two, names one” is a thing the card cannot say, and it waits on the per-district seat count rather than on another fetch. Two follow-ups routed: the `155 + Appleton` parenthetical (my #1135 note landed after #1138 was pushed, so untouched rather than declined), and a `where this note read 240 in 24` breadcrumb that now skips a revision. |  |  |  |
| **~~HELD #1135 (Wisconsin)~~ — cleared and MERGED; 28 alderpersons in four multi-member cities** | manager | **MERGED 2026-09-24 `f4a9b3d`** | 2026-09-24 |
| ↳ Wisconsin fixed both inside the hour and its board (`4aa675b`) reaches the same reading of the count I did: **244 is 240 plus four MUNICIPALITIES**, sitting inside a sentence claiming to be a measurement. Re-verified on the merged tree: 254 stated and 254 held, 240 → 268 triples with LOST 0 unchanged, and `term` gone from the file entirely (`name` 268, `phone` 133, `url` 124, `email` 102, `note` 2) with the reason in `scrape_wautoma`'s docstring rather than only on a board. It also took the 156 → 159 and 18 → 28 corrections onto all four surfaces. Battery 98 of 98 static here, its CI green. **ONE FOLLOW-UP, AND IT IS THE TAIL OF MY OWN REQUEST**: moving the headline to 159 left the parenthetical behind it — “the 159 cities and villages … (155 from the counties' own filings, plus Appleton from its city clerk's)” now reads as 156 on `wi/sources.html` and in its `Dataset` description. The right number is in Wisconsin's own geometry note: FOUR cities are locally composed because their counties file wards uncoded (Appleton 15, Berlin 6, Kaukauna 4, Edgerton 3), so 155 + 4 = 159. Not worth holding 28 officeholders over, so it shipped and the fix is routed. **A correction that moves a headline has to move everything that adds up to it.** |  |  |  |
| **HELD #1137 (Iowa) — the gap-count gate is right; two lines in the new shared module are not** | manager → iowa | **held 2026-09-24, comment on the PR** | 2026-09-24 |
| ↳ The assignment came back better than I specified it. **I broke every branch myself on the merged tree rather than reading the list**, and all eight fail as claimed — the one that matters is dropping a county from the chairs roster, which fires BOTH numbers (`states 38, the source holds 37` and `states 61, the source holds 62 (99 - 37)`), so the original defect is caught whole rather than half. Verified independently of the gate: chairs 38 keys, officers 99, complement 61, `ia-supervisor-district-seats.counties` 15, and **`counts` appears in zero of the six shipped `coverage-gaps.json`**, so the declaration really does ship to nobody. History pages byte-identical, battery **99 of 99 static** on the merged tree, CI green, `validate_gate_counts` 81/109 and `validate_steward_mirror` 109 for 109. The design argument stands on its own terms: the 152/153 table settles it empirically, and a gate that enumerated numbers would be measuring its own regex. **Held on two lines in `scripts/measured_metric.py`.** (1) Its docstring states the proof of its own faithfulness as **“all twelve history pages”** where the builder writes **four** — and Iowa had already corrected exactly that on `ia/BOARD.md` an hour earlier (`8a879d0`), so the correction reached the record and not the code, which is this gate's own subject one level up. (2) The seven-line `PERSON_WORDS` comment is pasted twice, a lift artifact in a module two gates now read. Two smaller notes, neither blocking: the shipped guard surfaces a `KeyError: 'counts'` from the builder rather than a drift report (it still refuses and names the right file); and `.claude/skills/gap-record/SKILL.md` §7 lists `build_about_page.py` twice with two different comments, pre-existing, the new line having landed between them. |  |  |  |
| **HELD #1135 (Wisconsin) — 28 alderpersons are right, two stated things are not** | manager → wisconsin | **held 2026-09-24, comment on the PR** | 2026-09-24 |
| ↳ The data half verified on the merged tree and is good: **240 → 268 name triples, 24 → 28 municipalities, LOST 0**, the 28 added all in the four new cities (Algoma 8, Dodgeville 8, Horicon 6, Wautoma 6), every district value a list, **no address-shaped value anywhere in the file**, and Wautoma renders 1/3/2 — the uneven council the list schema was argued from. Its CI green, and the 98-invocation static battery green here. **Two findings, neither of which a gate can see.** (1) `metro-worksheet.json`'s `min_keys` note and `wi/scripts/validate_index.py`'s comment both state **"268 alderpersons across 244 districts", measured that day**; the shipped file holds **254**, and it closes both ways — the base file has 240 districts and the four cities add 3+4+3+4 = 14. 244 reads like 240 plus four MUNICIPALITIES. A figure in a note that says *measured* has to be the measurement. (2) **`term` is a NEW field** — main's file carries name/url/phone/email only — on six Wautoma records, read from `Term Expires: (\d{4})`, **rendered by nothing** (the card maps name, badge, phone, email, note, url and has no `term` branch) and unmentioned in the PR body. Three costs: `check_roster_retention.py` protects a field from its first ship, so the page dropping it later reddens a weekly bot PR over something no reader sees, and removing it then needs an `ACCEPTED_DROPS` entry; it is the exact column the Cook County rule names ("take from a source only the columns it maintains"); and **Iowa's board recorded the opposite answer about the identical string the same day** (Worth's `Term Expires: 2022` beside two current supervisors — "never a term or an election date"). **CORRECTED WITHIN THE HOUR, AND THE CORRECTION IS MINE**: `wi/BOARD.md`'s own assignment row for this work ends “carrying a stated term where a source gives one”, so Wisconsin took that column because the board told it to, and my framing of it as unexplained was wrong. Ruled rather than handed back: **drop the field**, on two grounds that do not need the Cook rule — nothing renders it, and six of 268 is not a column, so terms on these cards are a fleet question with each source's term column to be established first. The clause is struck from the Wisconsin row in the same commit. **Finding 1 is now the whole of the hold.** Also noted, not blocking: the worksheet's `answers` still says **156 cities and villages** and **"in 18 of them"** while the shipped geometry measures **866 features across 159 distinct COUSUBFP** — which is what makes this PR's own gap-summary 156 → 159 correct — and 18 is now ten short; both strings flow into `wi/sources.html` and its `Dataset` description. |  |  |  |
| **~~Reviewed and merged #1136 (Iowa)~~ — three counties now name the supervisor who holds each district** | manager | **MERGED 2026-09-24 `b54f852`** | 2026-09-24 |
| ↳ Reader-facing: Butler, Chickasaw and Howard County cards and per-county pages stop saying "which district each one holds is not published" and name the holder of each district. **The check that carries it is the roster diff on the merged tree**: named seats 67 → 78, ADDED 11, **LOST 0, CHANGED 0**, counties 17 → 20 — so the widened `DISTRICT_RE` added counties and moved nobody, which is the claim the change rests on. All eleven new names agree exactly, set for set, with `ia-county-officers.json`, the independent roster those pages already read, so the only new fact is the number. Negative-tested here rather than taken from the body: narrowing the pattern back makes Butler read "the page names no district" again, and Kossuth's rotated page returns a **collision** (district 3 twice, 1 missing) so gate 3 refuses it — while a directional reader of the same flat text returns a clean 1..5 permutation, which is exactly why refusing is right, and Iowa's own board already records the decisive reason: **"Kossuth admits both"** orders and flat text cannot choose. Bookkeeping checks out in every place it has to: the gap's stated count 18 → 15 is the same three counties leaving `counties`, `area` and `ia/WATCH.md`; the three retired outlines leave `GEOMETRY_FILES`, `DYNAMIC_REFERENCE` and `sw.js`'s `GEOMETRY_URLS` together with the **cache bump v11 → v12** those cache-first files require; `EAM_STATUS` 67 → 78 and `ENDPOINT_INVENTORY` 61 → 58 Iowa data files match the tree. CI ran this time and was green (10m11s), and the 98-invocation static battery is green here on the merged tree. |  |  |  |
| **~~Reviewed and merged #1134 (Iowa) and #1133 (Wisconsin)~~** | manager | **both MERGED 2026-09-24** | 2026-09-24 |
| ↳ **#1134 `d1e9393`** — one line, a dated `RE-MEASURED` section on `ia-supervisor-district-seats`'s blocker. Verified rather than taken on the body: the reader fields are context lines in the diff, all six `build_coverage_gaps` checks plus history, county-status and about pass, and rebuilding for real leaves no generated file changed, so the blocker really is non-shipped. `ia_county_chair_scraper` does carry the robots gate, `HostPacer` and the districtry token at lines 105-107 and 605-606, so the claim about HOW it fetched holds. Arithmetic closes both ways: 3+5+3+5+3+3 = 22 supervisors named, 6 publishing + 5 wrong-page + 7 unfetched = 18 counties. **GitHub started no CI run on that branch at all**, so the 98-invocation static battery was run here on the merged tree instead of merging on a partial check. **#1133 `71e09b9`** — the load-bearing check is that no alderperson moved: old and new agree on 240 `(municipality, district, name)` triples exactly, 24 municipalities, every district value now a list, every list length 1. The builder's shape guard was negative-tested and refuses a bare member object BY NAME before any count runs (`members must be a LIST (got dict)`), which is the failure mode its docstring says it exists to prevent — iterating a bare object counts `name`, `phone`, `url` as three people. Its own CI green, and the battery green here on the merged tree. |  |  |  |
| **I BRIEFED THREE SESSIONS FROM MY OWN TASKS TABLES AND TWO OF THE THREE WERE STALE** | manager | **recorded 2026-09-24** | 2026-09-24 |
| ↳ The wakes at 13:23 UTC worked — all three answered within the hour, wrote their boards and opened #1133 and #1134. What they answered with first was that my briefs were out of date. **Michigan: all three DO FIRST rows had merged on 2026-09-22.** #1091 landed as `7aba70cf` with the held sentence fixed on THREE surfaces rather than the one I found, the certified-returns route shipped as `mi-commissioner-returns.json`, and tranche 6 is moot. Verified before repeating it: 48 scraped counties and 35 certified, DISJOINT, union **83 of 83** — every Michigan county names a commissioner, where an hour earlier I told Adam the roster was at 48 of 83. **Wisconsin: two of six rows were already delivered**, and the MPS/RUSD row's premise was wrong in a way anyone could have checked — it said "several Mondays have now passed" when one had, and their board had already recorded both jobs green on it. The Court of Appeals row was stale because #1040 merged on 19 September. **Iowa: the chair count was fixed by #1034 on 19 September** and says 38/61 on all four surfaces, so my brief's claim that a reader is shown 43 was false. **THE CAUSE IS ONE HABIT, NOT THREE MISTAKES: I read the Tasks table as the state of the work instead of as a claim about the tree.** My own root board recorded #1091's merge on 2026-09-22 (`a72b50a`), so Michigan's row contradicted my own board two rows apart. A brief is a measurement like any other — take it from the tree at the moment of writing, and where a row states a figure, re-derive the figure. The three sessions each checked before acting and lost nothing; the cost was entirely mine to pay in their reading time. |  |  |  |
| **Woke Wisconsin, Iowa and Michigan and handed each its own board's brief** | manager | **sent 2026-09-24 13:23 UTC** | 2026-09-24 |
| ↳ Adam's instruction, after a board review found all three had assigned "DO FIRST" work from 21-22 September and no Status entry since the 22nd, while Illinois and New York had written on the 23rd. Woken by the recorded route — a poke-only Routine per session bound with `persistent_session_id`, then `fire_trigger` (`trig_01Ni5CLgLqx675pstm61RWk6` Wisconsin, `trig_01164hRz4j5B5NpqFSaSYVLo` Iowa, `trig_017F6stPgvGeAyzd86Wz5da5` Michigan). **Each brief is that session's OWN Tasks table in priority order, never a new assignment**: Wisconsin the cheap MPS/RUSD run check, then the Adam-approved multi-member roster schema, then the frozen legislature roster, the stale NG911 geometry and the two Court of Appeals guards; Iowa the chair gap record that ships 43 to a reader where the file holds 38, then Mitchell County's parser without `--allow-drop`, then the ~305 unmeasured officer phone numbers; Michigan the #1091 regenerate now that #1089 has landed, then Adam's ruling on the certified-returns route for all 35 counties with its four recorded traps, then tranche 6. Each also carries the standing rules it needs — its own Status and Open questions are its own, boards commit straight to main, code goes in a PR behind the steward battery, and no officeholder is ever guessed. Michigan was told its three questions to Adam are still unanswered and not to block on them. |  |  |  |
| **~~The endpoint and dataset inventory is GENERATED now — `docs/ENDPOINT_INVENTORY.md`~~** | manager | **MERGED 2026-09-24 as `26d747f` (#1132)** | 2026-09-24 |
| ↳ Adam asked for an inventory of every external endpoint the apps call at runtime, every dataset in the build, and the terms for each. Answering it meant reading six `index.html` files and six `validate_sources.py` manifests, and my first hand-written pass got three things wrong at once: the Socrata portals fell in with the links, TIGERweb was counted twice, and the per-kind buckets summed to a total larger than the host list because one host had landed in two of them. So it is generated — `scripts/build_endpoint_inventory.py`, `--check` in CI — with every figure read from the file that owns it, hosts classified ONCE by path shape (which is the only thing separating a request this site makes from a link a reader clicks), `build_privacy_page.py` IMPORTED rather than re-decided and the two readers held to each other per app on CARTO, cdnjs and the geocoders, point transmission read from the artifact because `CLAUDE.md`'s prose says 4 for an app the artifact says 5, and the four "not recorded anywhere here" claims re-audited every run so the build fails once somebody records one. Five negative tests. Gate pair 79/107 → 80/108. |  |  |  |
| ↳ **MERGED**, all 80 static steps green including the new one (step 33 of the smoke job, 10 s). Nothing a reader of the site sees changed: the document is in `docs/`, served to nobody. Regenerate it after any change that moves a runtime host, a dataset manifest or the point-transmission artifact — `--check` is step 33 and will say so. |  |  |  |
| **A RED SMOKE RUN'S LOG TAIL IS GREEN — read the step list, never the tail** | manager | **recorded 2026-09-23** | 2026-09-23 |
| ↳ The `smoke` job accumulates failures with `|| status=1` and exits at the end, so every step after the failing one still runs and still prints its passes. On #1127 I pulled the failed job's log with `tail_lines=60`, read `All root-page checks passed` / `point-transmission.json matches what the apps actually do` / `probe-contrast-pairs: OK`, and had no sign of the failure at all — it was step 28 of 86, `build_history_page.py --check`, nine minutes earlier. **A log tail answers “what ran last”, not “what failed”.** Read the job's STEP LIST (`actions_list` → `list_workflow_jobs`) and find the step whose conclusion is `failure`, then fetch that step's own output. Illinois hit the same thing on the same run and records it in #1127's commit; it is on the root board because every session reads red runs, and because the cheap wrong move (trusting the tail) looks exactly like a green run. |  |  |  |
| **~~`fleet_status.py` reads the last completed run on ANY branch, so a deleted branch's startup failure becomes a health row~~** | manager | **FIXED 2026-09-23** | 2026-09-23 |
| ↳ `scripts/fleet_status.py:412` queries `/actions/workflows/<f>/runs?per_page=1&status=completed` with no `branch=` and no `event=`. Two of #138's seven WARN rows — `update-mps-school-board-roster.yml` and `update-rusd-school-board-roster.yml` — are not failed refreshes at all: both ran GREEN on their own Monday schedules on main (2026-09-21T20:05:06Z and 21:12:14Z), after the dashboard measured at 19:50:12Z. What it reported are zero-job, zero-duration PUSH runs carrying the file path in place of the workflow's `name:` — the shape GitHub records for a workflow file it cannot start. **THIS ONE REPEATS RATHER THAN SELF-CORRECTS**: the latest completed run of each today is another such run on `claude/goat-counter-data-access-g5ycax`, a branch that is gone from origin, so nothing supersedes it until the next Monday schedule — and this workflow's cron is 15:00 UTC where MPS's is 15:30 and RUSD's 17:30. Posted on #138 with the other five rows re-measured (three cleared on their own later runs, two unchanged and correct). **The inference is read off the runs, not off the deleted branch's copy of the file, which is unfetchable.** |  |  |  |
| **~~`docs/MANAGER.md` contradicts the prompt that loads it~~** | manager | **FIXED 2026-09-23** | 2026-09-23 |
| ↳ Line 9 still says the facts that go stale "belong on the tracking issue, whose latest comment is the only state that survives a container", and the word *board* appears NOWHERE in the file — grep on `0b341f2`, 0 occurrences. The hourly routine reads the root `BOARD.md` first and `MANAGER.md` second, so the rules file tells the next manager the opposite of what the prompt does. The boards landed in `b3ac708` on 2026-09-19 and 161 commits have touched one since; `MANAGER.md` never followed. Recorded on #960. |  |  |  |
| **~~`CLAUDE.md` calls Kendall and McHenry hand-verified because they "block all automated fetch"~~ — false since 2026-09-03, not 2026-09-10 as this row first said** | manager | **FIXED 2026-09-23** | 2026-09-23 |
| ↳ `CLAUDE.md`'s Data pipeline section (line 306) still lists `kendall-county-board-members.json` + `mchenry-county-board-members.json` as hand-verified on that ground. `54786f5` ended it on 2026-09-03 by adding a stdlib rung between `requests` and `playwright`: the Akamai edge refuses the `requests` stack and serves a stdlib client sending real Chromium Sec-CH-UA hints, and it needs BOTH — the leave-one-out is in `user-agent-measurements.json` (requests+token 403, stdlib+token 403, requests+chrome 403, stdlib+chrome 200). Two scheduled runs each have scraped the live pages since with the report step SKIPPED, and both scrapes reproduce the shipped rosters exactly. #234 and #235 closed on that measurement 2026-09-23; the sentence is the last place the retired claim survives. |  |  |  |
| ↳ **FIXED, and the diagnosis in the row above was wrong in two places.** The branch is not the test: run `35166293478` is the same zero-job shape ON MAIN, so filtering to `branch=main` would have cleared today's rows by luck and left the defect. And `check_roster_workflow_health.py` — which writes #387, the report that tells a human a roster is frozen — had the SAME defect and the row never said so; its MPS and RUSD FAILING rows are the same two phantom runs. `scripts/workflow_run_evidence.py` is now the one reader both scripts ask, because two readers of one question is where this fleet's recurring defect starts. The test is whether a job ever ran: a shape proxy that costs nothing narrows it, then the job count CONFIRMS before anything is dropped, and an unconfirmable run is kept — silence about a frozen roster is the expensive direction. A never-started run on the default branch is kept and reported, because there it means the shipped file cannot start. Replayed through the real `classify()`, MPS goes FAILING → OK and reproduces #387's exact wrong string. 16-assertion self-test, negative-tested three ways, wired into CI; the gate pair moves to 79 / 107. |  |  |  |
| **~~`docs/EAM_STATUS.md` counts officeholders and NO workflow regenerates it~~** | manager | **MERGED 2026-09-22 as #1102 `484ad74`** | 2026-09-22 |
| ↳ Found by #1093 going red on its own bot PR. The file carries a live per-instance count of named officeholders (Illinois 998); Sangamon District 16 became a vacancy, the count moved to 997, and `build_eam_status.py --check` failed the refresh that caused it. **`grep -rln build_eam_status .github/workflows/` returns `smoke-test.yml` alone** — the `--check`, never the build. And unlike `build_county_pages.py`, `build_officeholder_tables.py` and `build_concept_pages.py`, it has **no `check_workflows()`**: the gate those three carry precisely so a weekly job that rewrites a roster they count cannot merge without regenerating. So every roster workflow in the fleet goes red on its own pull request the first time its record count moves, and the failure lands on a bot PR nobody wrote. I regenerated the file onto the bot branch to unblock #1093; that is the symptom. The fix is the gate plus the regeneration step in whichever workflows it names, and it is mine rather than an instance's because the file is fleet-wide. |
| ↳ **FIXED IN #1102, 2026-09-22.** `build_eam_status.py` gains the `check_workflows()` its three sibling generators have, and **62 scheduled workflows gain the regenerate step and the `git add`**. The surface is MEASURED rather than listed: the siblings each carry a hand-written `counts` list because each owns a handful of pages, while this report reads every roster `build_county_pages`' own adapters read — 71 files across four instances today, a set that moves whenever a county ships — so the gate takes `load_rosters()`'s own `paths` and asks `refreshed_by()` which scheduled job stages one. **It is the adapter surface and not every `data/app` file**, which Michigan measured rather than assumed (`mi/BOARD.md`, `69986bd`): of its six weekly roster jobs only `update-mi-commissioner-roster.yml` moves the figure, because `people` counts the districts these adapters name and not every officeholder an instance ships — requiring the step on the other five would ask 59 workflows fleet-wide to regenerate a file they cannot change. **BOTH CHECKS LOOK FOR A COMMAND AND A STAGED PATH, NEVER A MENTION, AND THE FIRST DRAFT DID NOT.** The step carries a comment naming the script and the file, so an `in text` test is satisfied by that comment; the draft's second check was vacuous for exactly that reason and a negative test that stripped the path from `git add` PASSED. All three failure branches are now negative-tested, and the gate refuses a run that finds no workflow at all. `docs/EAM_STATUS.md` itself does not change — no data moved. | | | |
| **Michigan's 35 unserved counties now name a commissioner** | Michigan | **merged** #1091 `7aba70c` | 2026-09-22 |
| ↳ Adam opened the certified-returns route; Michigan built it to the Clark posture in under an hour. All 83 counties have a page, 615 of 619 districts name someone, up from 366. **I held it once**: the first head rendered all 35 with the default lede — "exactly as the county publishes them", about counties like Oakland whose site answers 403 — because main's renderer had no hook for the `lede`/`cta_note`/`desc` their records already carried. CI was green on it; only reading the page caught it. Fixed by #1089's hook, re-verified on a merged tree. | | | |
| **Officeholders in rosters that reach no served byte** | manager | **merged** #1089 `be825c6` — 310 shipped; two decisions open below | 2026-09-22 |
| ↳ *measurement*: a fleet audit of every roster in every instance's `data/app` and `data/source` against all 367 authored pages, raw and escaped, found **~500 named officeholders in NO served byte** and **~8,800 more** in rosters where fewer than half the names reach a page. Harness validated first: NYC 51/51 and SF 11/11 read as published, Detroit 0/9 as missing. | | | |
| ↳ *shipped in #1089*: Chicago's 65 Police District Council members onto the existing police-district page; new `mi/city-council.html` (24), `ia/city-council.html` (46), `ia/county-auditor.html` (99), `il/supreme-court.html` (64), `ny/borough.html` (12). The tables now carry **2,075** people against 1,765 before. | | | |
| ↳ *2026-09-22, Adam*: "use the statewide files for the special districts". **Merged** #1094 `0a82b9b` — `il/fire-district.html`, `il/park-district.html`, `il/library-district.html`, **1,310 people** (590 across 287 fire protection districts, 327 across 162 park districts, 393 across 198 libraries), each with the body's office and telephone. Two things the data forced: the roster is keyed by county and a district is not, so a cross-county district is keyed by the Comptroller's unit code rather than printed twice; and a row takes the district's own FILED name, because DuPage publishes `Addison` and Boone publishes `1` through `5`, which a map card reads fine and a page row does not. The fire page states that it cannot say how your trustees got there — 70 ILCS 705 appoints them unless a referendum said otherwise, and no filing says which. | | | |
| ↳ *still open, needs Adam*: two bounded absences recorded in the builders rather than widened into. Six counties (Boone, Grundy, Kankakee, Logan, Peoria, Woodford) publish their district officers in their own per-county files, ~229 people, which these pages do not read. And `il-library-contacts.json` names a director for **169 further libraries** that file no report at all, which the app's card already stamps. Either is one more adapter. Plus the four thin rosters with no non-thin home: BART directors (9), Milwaukee police captains (7), Cook library trustees (8), Cook Board of Review (3). | | | |
| Roster workflows: regenerate shared pages after the branch cut | IL + WI | **merged** #1030 `5338913`, #1031 `f2a0d88` | 2026-09-19 |
| Absolute gate on every shipped officeholder name | New York | **merged** #1025 `a3d11c0` | 2026-09-19 |
| #1025 and #1028 collided with no git conflict. | New York | **closed** — New York merged main in first and measured all four states rather than dropping the entry blind, so the branch was correct in either merge order | 2026-09-19 |
| `privacy.html` understated three events sent through `shareCopyButton` | manager | **merged** #1046 `dd5ce05` — the page named ten events while every app sends thirteen. An unreadable `trackEvent` call is now an ERROR rather than a skip; resolution follows one hop and fails naming the line otherwise. Coordinate events stay at two: these three send a name and nothing else | 2026-09-18 |
| Shallow checkout makes every roster PR rewrite all 243 sitemap dates | manager | **merged** — 73 workflows deepened and `scripts/validate_workflow_checkout.py` is on main, failing any workflow that commits `sitemap.xml` without full history or re-shallows it afterwards | 2026-09-19 |
| A scheduled workflow that has NEVER run is invisible to every gate here | manager | **closed — measured** | 2026-09-19 | Swept across all six instances: of 128 scheduled workflows only two have never run, and the calendar explains both. Michigan raised it as a class of blind spot and it is real, but the fleet has no instance of it today, so nothing is built. Re-measure if the count ever moves. |
| The six-pointed star is Chicago's and five apps were wearing it | manager | **merged** #1056 `e903810` | 2026-09-20 | Adam: "SF should adopt the standard pin. The star is reserved for Chicago." Measured, SF was not the only one. The star reached THREE surfaces per app — masthead wordmark, empty-state glyph, map pin — and Illinois had already settled the pin for itself (flag star inside Chicago only, blue circle everywhere else). wi/ia/mi had followed on the pin; SF had not; NOBODY had followed on the wordmark, so Chicago's flag emblem was the masthead glyph of four unrelated apps. It was also broken beyond branding: the shared dark-map rule reaches a `<circle>` only, so SF's star and NYC's teardrop were one colour in both themes. Now ca/wi/ia/mi take the teardrop for wordmark and empty state, ca and ny take the fleet circle as the pin, Illinois untouched. Verified in Chromium on main, seven points, both themes. |
| A cloned instance file keeps the original's text and nothing checks it | manager | open | 2026-09-20 | THIRD occurrence. `mi/sources.html` served Iowa's whole identity block; Michigan's commissioner roster cloned a parser that shipped zero districts; and #1056 found Iowa's and Michigan's map-marker comments were Wisconsin's verbatim — "means nothing in Wisconsin" — sitting in two other states' code. Each was found by a person reading, weeks apart, and each was fixed one at a time. `page_consistency_test.mjs` gained the canonical/og:url check after the first, which catches an identity block and nothing else. The general shape is a cloned file keeping a claim about the instance it came from; a comment is harmless and a canonical is not, so the question is what class is worth a gate rather than whether to fix a fourth by hand. Not started, and not urgent — boarded so the fourth one is recognised as a pattern rather than a surprise. |
| **How the manager wakes a state session, when `SendMessage` cannot** | manager | **closed — route found and used 2026-09-21** | 2026-09-21 | **CORRECTED the same day: the earlier row said the sessions could not be woken at all, and that was wrong about the fleet while being right about one tool.** All five state sessions are IDLE and healthy — Illinois `session_01TifBPZMzrNEir2idEUqro2`, Wisconsin `session_012JWArkaHs7hGqRHxkjGoKw`, Iowa `session_01GDDwuCzmWxgdbz3V8GHrjJ`, Michigan `session_013TPP9BCk1NnjK5EfTUfvGm`, New York `session_01HzrNZpsGsGwVHNh8Wgj9Mb`, each queried by id rather than inferred from a listing. What is missing is the channel: this session has no cross-session send available today, `ListAgents` reports no reachable peer, and a send by id and by name both fail. So the assignments are written into each board's Tasks table instead, which is where a session reads its marching orders on resume, and Adam nudges each session for it to pick them up. `SendMessage` and `ListAgents` reach peers on THIS machine, and the state sessions are cloud sessions, so both report no reachable agent and a send by id or by name fails. That is a fact about one channel, not about the sessions. **The route that works is a Routine bound to a session:** `create_trigger` with `persistent_session_id` and the assignment as its prompt, no cron and no `run_once_at`, then `fire_trigger` to deliver it immediately. All five were woken this way at 18:50 UTC, each call returning the target session id, and Illinois's record confirmed delivery — `updated_at` moved to the firing second, `unread` true, worker epoch 192 to 193. **Starting fresh sessions was still the wrong answer and stays the wrong answer**: Illinois carries 634k tokens of context and Wisconsin 502k, and a second owner on one instance is the failure this board records from 2026-09-19. The assignments also live on each board, which is where a session reads them on resume, so the two routes agree rather than competing. |
| `llms.txt` counts the per-county pages and 61 of 63 refresh workflows do not regenerate it | manager | open, **RE-MEASURED 2026-09-24** | 2026-09-19 | Found by Iowa when its own weekly run went red on a file it never touched. `llms.txt` states the page count, a county dropping out moves it, and only Michigan's and Iowa's workflows rebuild it. Iowa fixed its own and boarded the general case rather than editing four instances' workflows unasked, which was right. The recurrence-proof fix is a GATE — `build_county_pages.py --check` already fails a workflow that does not regenerate its own pages, and nothing does the same for `llms.txt`. Counted here as 60 of 62 rather than Iowa's 61 of 63: their denominator included `smoke-test.yml`, which runs `--check` and regenerates nothing. **RE-MEASURED 2026-09-24 and the pair has moved, which is the reason to state a method rather than a number: 63 scheduled workflows now regenerate the per-county pages and only TWO of those also regenerate `llms.txt` — Iowa's `update-ia-supervisor-roster.yml` and Michigan's `update-mi-commissioner-roster.yml` — so it is 61 of 63. The denominator is the workflows that can MOVE the count (those staging `build_county_pages.py` output), not every `update-*.yml`, of which there are 112; `deploy-pages.yml` regenerates it too and is not a refresh. #1102 fixed exactly this shape for `docs/EAM_STATUS.md` by giving its generator the `check_workflows()` gate its three siblings carry, so the fix here is the same one applied to `build_llms_txt.py`, and until it exists the number keeps moving.** |

## Status — manager writes here

**2026-09-24 01:40 — night's close.** Seven things merged tonight, four of them
changing what a reader sees. Main green on every commit bar the last, which was
still running at close and is covered by a scheduled check.

**What moved for a reader.**

- **Chicago's school board card was wrong in two of twenty districts** and is now
  right in all twenty (#1127, Illinois's). Sub-district 9a said the seat was
  vacant while the Board's own Vice President holds it; 10b named a member who
  resigned in March. I verified every district against `cpsboe.org`'s live index
  and found zero mismatches. The hand-curated file became a weekly pipeline.
- **That card is now searchable by the Board's own seat names** (#1129) — "2b"
  rather than "District 4", which is what the card had been printing all along.
- **Detroit's council card reads the city's own page again** (#1126), not a
  twelve-day-old archive copy. The archive fallback stays: one direct answer is
  not proof an intermittent block has lifted.
- **Wisconsin's Court of Appeals names the right Presiding Judge for District II**
  (#1123), after that job had opened no PR for eighteen days.

**What moved for nobody but is now true**: the three tree-side defects (#1124),
Boone's stamp-only refresh (#1128), and the roster-health report telling the
truth about which refreshes are failing.

**THE FIX FROM #1124 WAS CONFIRMED ON LIVE DATA, which is the only kind of
confirmation that counts here.** #387's 00:58 run went from four FAILING rows
plus one UNPROVEN to ONE. Both phantom rows are gone — they had been reporting
runs in which no job ever started, on a branch deleted from origin, and would
have repeated every week.

**One real thing is left open and it is Wisconsin's**: the legislature roster is
frozen at its 2026-09-15 reading on a single unretried `urlopen` timeout, next
scheduled run ~2026-09-29. Routed to `wi/BOARD.md` with the run named. Preserving
the last-good reading is already correct; a retry is what is missing.

**Three mistakes of my own, all caught and none shipped.** I read a failed run's
log TAIL and saw only passes, because the smoke job accumulates failures — now a
task row on this board, since every session reads red runs. A compound
`git fetch` aborted on a deleted ref, left main stale, and my checkout silently
landed on main, so a batch of gates came back green for a tree I had not meant to
test; I re-ran against the real merged tree rather than reporting those. And I
wrote a fix for #1127's history-page failure that Illinois had already pushed
byte-identically, and dropped mine rather than pushing a duplicate.

Adam's hourly routine is left running. It is cheap, it answers "nothing changed"
on a quiet hour, and a red main overnight should wake somebody.

**APPENDED 01:57.** #1130 landed after the above was written and is merged as
`b804a8c`: the school board's flat 1-20 numbers become an internal key and every
surface a reader sees carries the sub-district. **It fixes a live misleading label**
— measured on the shipped labels, our "District 4" was the Board's sub-district 2b
while the Board's own 4A and 4B were our 7 and 8, so a reader cross-referencing the
official name was sent to a seat on the other side of the city. Verified as a
relabelling and not a data change: the same 21 records, the same 21 names.
**Adam then asked that this thread stay with the session that wrote it**
(`session_01EipC4SzjcT91Nzy9D4HJCJ`), so #1129, #1130 and anything following from
them are theirs, including watching `b804a8c` to green. Poked with the state and the
one thing I noticed and did not act on — the sub-district labels derive from the
boundary's `longName`, so a replaced boundary file moves them silently. My own check
on that commit is cancelled so we are not both watching it; the hourly routine's
cheap gate still reads main's newest smoke conclusion.

**2026-09-23 — the three tree-side defects are fixed, and the first one's diagnosis
was wrong twice.** Adam said to take them. Nothing here changes what a reader of the
site sees; all three are about whether this project's own reports tell the truth.

- **The run-health defect was wider and different than recorded.** The row said
  `fleet_status.py` reads the newest completed run on any BRANCH. The branch is not
  the test: run `35166293478` is the same zero-job shape on MAIN, so a `branch=main`
  filter would have cleared today's two rows by luck and left the defect in place.
  And the row named one script where there are two — `check_roster_workflow_health.py`
  writes #387, the report that tells a human a roster is frozen, and its MPS and RUSD
  FAILING rows are the same two phantom runs. **The real test is whether a job ever
  ran.** `scripts/workflow_run_evidence.py` is now the one reader both scripts ask,
  because two readers of one question is where this fleet's recurring defect starts.
  A free shape proxy narrows it and the job count CONFIRMS before anything is
  dropped; an unconfirmable run is KEPT, because silence about a frozen roster is the
  expensive direction. A never-started run on the default branch is kept and reported
  — there it means the shipped file cannot start. Replayed through the real
  `classify()`, MPS goes FAILING → OK and reproduces #387's exact wrong string. The
  adjacent question it does NOT decide — whether a dispatch on a feature branch
  should clear the staleness clock for the shipped roster — is recorded in the module
  rather than answered, because narrowing that would move workflows this change has
  not measured one by one.
- **`docs/MANAGER.md` now names the boards.** It had said durable state belongs on
  "the tracking issue, whose latest comment is the only state that survives a
  container", and the word *board* appeared nowhere in 310 lines. True when written
  on 2026-09-15, false four days later; a commit touched the file seven hours after
  the boards landed and did not revisit it. The disproved sentence is kept in place
  under its correction.
- **`CLAUDE.md` no longer calls Kendall and McHenry hand-verified.** `54786f5` took
  them off it on 2026-09-03, not 2026-09-10 as the task row said, and both have
  refreshed weekly from their own scrapes since. **My own first draft of that
  correction was itself wrong**: it said Playwright is the rung that reaches them,
  taking the phrase from the `blocked` note on the counties' municipal yearbook
  sources, which are a different surface. Measured on the board-members page itself,
  the working rung is the stdlib client plus Sec-CH-UA hints — `requests`+token,
  stdlib+token and `requests`+Chrome all 403, stdlib+Chrome 200 at 120,795 bytes.
  A source that needs a browser-class client is not a source that blocks automation,
  and the retired claim had recorded the two as one thing.

The gate pair moves to **79 named steps / 107 invocations**, measured after the last
edit, with the steward mirror restated to match.

**2026-09-23 evening — the Wisconsin Court of Appeals roster unfroze after 18 days,
and District II has a new Presiding Judge.** `update-wi-court-of-appeals-roster.yml`
had not opened a PR since 2026-09-05. It was the UNPROVEN row on #387: #1040 gave the
job one forgiven failure, and its first run after that fix drew a runner that could
reach `www.wicourts.gov` — the block is per-runner egress IP, measured in the
scraper's own docstring, not a source change. **Merged as #1123.**

What moved for a reader: Wisconsin's Court of Appeals card for District II now names
**Maria S. Lazar** as Presiding Judge at (262) 521-5233, where it named Mark D.
Gundrum. Gundrum is still on that bench; only the role moved. Verified against the
court's own contact page, fetched today as the scraper's own client
(`districtry-wisconsin/1.0`; that host's robots.txt is a 404, so allow-all, read
through `robots_policy.py` before the fetch). The page prints
`LAZAR, HON. MARIA S. - Presiding Judge` first and `GUNDRUM, HON. MARK D.` third with
no role, which is exactly the diff. **The role is parsed from the page's own label,
not from list position** — so this is the court's statement, not a reordering
artefact. The four-judge seat gate passed and no other district moved.

The merged tree was verified before the merge, not the PR body: `wi/validate_index.py`,
`check_roster_retention.py`, `check_cache_version.py` and `build_eam_status.py --check`
all green with the bot branch merged onto current main. Nothing generated reads this
roster, so no page needed regenerating.

**Also merged to main while this session was reviewing issues: #1122, `/ai.html`.**
Not mine — the feature session's — but verified here on the merged tree afterwards,
because two branches can each be right against their own base and both wrong once
merged. The gate pair holds at **78 named steps / 106 invocations** (`validate_gate_counts.py`
and `validate_steward_mirror.py` agree), and `build_ai_page.py --check`,
`build_about_page.py --check`, `build_privacy_page.py --check`, `validate_analytics.py`,
`build_llms_txt.py --check` and `robots_policy.py --selftest` all pass. For a reader:
the site now has a page saying it is mostly written by AI agents, what they do and
what they do not, and `about.html` no longer claims every name comes from the body
that elects the person — the Congress and several state-legislature rosters come from
the @unitedstates project and Open States.

**2026-09-23 — reviewed all 14 open issues; 4 updated, 2 closed, 8 left alone.**
Adam asked for the standing reviews to be updated only where something has changed.
Fourteen agents investigated one issue each against primary sources, and every
"something changed" verdict went to two independent refuters before anything was
posted. **Nine claimed a change; five were refuted and dropped.** In each dropped
case the refuter whose job was to RE-MEASURE found the conclusion did not follow
from the evidence, which is the outcome that rule exists for — posting a wrong
update to a standing issue costs more than posting nothing.

- **#235 McHenry and #234 Kendall — CLOSED.** The edge block ended 2026-09-03 with
  `54786f5`; two scheduled runs each have scraped the counties' live pages since
  with the "Report blocked source" step SKIPPED, and both scrapes reproduce the
  shipped rosters exactly. `validate_sources.py` has said "can close" since that
  day. **Closing loses nothing**: the report step re-files a fresh issue when no
  open one carries the title, which was checked in the workflow rather than assumed.
- **#138 Fleet status — commented.** Two WARN rows are a measurement defect that
  repeats; see the task row above.
- **#960 Manager check-in log — commented.** Its body stopped describing the
  check-in on 2026-09-19 and `MANAGER.md` never followed; see the task row above.
- **Eight left alone** (#1121, #1027, #304, #202, #201, #200, #1026, #387, #654,
  #259 — ten counting the two whose change claim was refuted twice). Each still
  describes reality, and a bot re-posting the same row is not a change.

**THE RUN CONCLUSION IS NOT THE EVIDENCE, and it decided both closes.** Every one
of these county workflows carries `continue-on-error: true` on its scrape step, so
the job goes green whether it fetched the county or not. What moved is the REPORT
step's own conclusion — `skipped` on each run since the fix, `success` on the run
that posted the last "still blocked" row. A reviewer reading run conclusions would
have seen green for six weeks before the block lifted and green after, and learned
nothing.

**2026-09-22, end of day. All five state sessions stood down for the night; main
green at `ecbff07`.** Adam asked to wrap the state sessions. All five were already
IDLE with their last turns complete, nothing unpushed and no PR of their own open —
verified from the session records rather than assumed — so the wrap was a stand-down
message each, not an interruption of work in flight.

- **Illinois** — #1093, #1096, #1098 merged; its own `45a2c06` correction (the
  VACANCY_SENTINELS reach is three nodes across two pages, not one) is the live
  record and supersedes #1096's merged body.
- **Wisconsin** — #1083, #1084, #1099 merged; the LTSB filing watcher is live. The
  NG911 geometry rebuild stays open and stays Wisconsin's.
- **Iowa** — #1095 merged; the 18 Plan 3 counties are a recorded gap a reader can
  see. Re-sent Adam's preserve ruling as a standing correction, since its builder
  deleted Bremer and Hamilton on a 500 and a genuine refusal read as a mandate.
- **Michigan** — #1091 merged plus three board commits. **Its 23:06 self-check-in was
  disabled** (`trig_01PaWcv8fdroQ1P424WYFE2B`): it would have woken the session into a
  turn expecting decisions that were not coming tonight.
- **New York** — idle since 2026-09-21 with everything shipped; nothing to stand down
  beyond confirming it.

**MICHIGAN'S TWO OPEN QUESTIONS WERE NOT CONVERTED INTO MANAGER DECISIONS, AND THAT
WAS THE CALL.** #1086's commit 2 turns on a promise Michigan made on #1087 not to
re-push unasked, and only the person it was made to can release it; the Keweenaw
wash-vs-outline choice is a fleet engine change plus a record-shape change, which is
not a thing to start at 23:10 and leave half-landed. Both carry to Adam with
Michigan's own recommendations attached. Michigan's re-measurement of that patch —
catching it decaying and saying so before writing "applies cleanly" into its own
entry — is why leaving it costs nothing but a further day of decay.

**One session is deliberately NOT stood down**: `session_01EipC4SzjcT91Nzy9D4HJCJ`
(the compare-districts map labels, #1100/#1101 merged, #1103 open with its own
23:15 merge-when-green wake). It is not a state session, it is driving its own PR,
and stopping it mid-flight would leave an open PR nobody owns overnight.

**2026-09-19, third pass. The open-PR queue is empty but for one hold.** Adam
asked for the open PRs to be merged; two of the three went in, verified on a
tree with `origin/main` merged rather than from a PR body.

- **New York is statewide (#1042).** A reader in Albany or Buffalo typing their
  address at the front door is now routed to `/ny/` with the point selected,
  instead of being told they are outside everywhere districtry covers. The app
  opens on the state rather than the harbour, an upstate `#point=` link
  resolves, and it calls itself districtry New York. Re-measured here: the
  shipped bbox is wider than the widest shipped geometry on all four sides, so
  nothing is clipped, and every sibling instance's `METRO_EXPLORERS` table
  learned the new box — without that, an upstate address typed into the
  Wisconsin app would not have been offered New York at all.
- **Michigan's board probe records the robots reading for the host it accepts
  (#1045).** Both of its load-bearing claims were negative-tested here rather
  than read: deleting one record's robots reading makes `--check` name the
  affected records and exit 1, and `--check` runs clean with a `requests` that
  raises on import. The gate-count pair is the merged tree's own measurement,
  67/94, not either branch's.
- **#1018 is held and the hold is now Adam's to clear.** See question 2.
- **The preserve ruling is live for a reader, and the same guard caught a second case an hour later.**
  Iowa's weekly run re-ran through the new builder (#1048, `bb1676e`): all 17 counties ship, Bremer and
  Hamilton carried forward with their three supervisors each, and **not one of the 67 names changed** —
  checked rather than assumed. Their two pages now tell a reader plainly: *"last read 2026-08-28 and no
  longer re-read… These names will go out of date."* Every still-read county keeps the scheduled sentence.
- **Michigan's weekly run then proposed deleting Delta and Otsego — 14 commissioners — and is HELD (#1052).**
  Not the Iowa case: I read both counties' robots.txt with this repo's own reader as the scraper's client,
  and **neither refuses us**; both board pages answer HTTP 200 at ~109 KB and still name their
  commissioners. Nothing at either source changed. That makes it a scraper defect, routed to Michigan with
  the evidence and with three things not to do — no `ACCEPTED_DROPS` entry, no merge on a re-run that
  happens to come back green, no lowering the guard.
- **The Detroit roster PR now says what its run moved (#1047).** Its weekly PR opened with the
  same sentence every week — "this changes data about real officeholders" — and on both of the
  two refreshes that have ever happened, the only thing that moved was an Archive timestamp. A
  body that cries officeholder every week is how a reviewer learns to skim the week it matters.
  The summariser refuses to claim nothing moved about a document it has not fully accounted for,
  which I negative-tested: an unrecognised field produced "fields this summary cannot name"
  rather than a clean bill. It also found that detroitmi.gov served this client directly on
  2026-09-09, so the block is intermittent where four places called it standing.
- **The queue being empty is why #1046 exists.** With nothing left to review I took the one open
  unassigned task: the privacy page named ten analytics events while every app sends thirteen.

**Manager's own work.** The shallow-checkout defect Wisconsin recorded as
fleet-wide was 73 workflows wide, not twelve; every one is deepened and
`validate_workflow_checkout.py` now fails a workflow that commits `sitemap.xml`
without full history or that re-shallows it afterwards. `docs/MANAGER.md`
records the standing merge authority. Michigan's "a workflow that has never run
is invisible to every gate" was swept across all six instances: of 128
scheduled workflows only two have never run, both explained by the calendar.

Main is at `bb1676e`. Open: #1018 held (Hancock), #1048 held (see question 4). #1049 merged.

**#1048 is no longer red for the reason its own PR body gives.** That body names
`build_llms_txt.py --check`, which was true when it opened; Iowa's own regeneration commit
fixed that half, and the run's log ends in `check_roster_retention.py` and exit 1. So the
gate now refusing the merge is the one that objects to two counties vanishing — which is
question 4 exactly, and is the gate working rather than an obstacle to clear.

## Open questions for Adam

**1. Is "5 boroughs" still the right scope line for New York?** Not blocking.
Raised by the New York session on its own board and carried here unchanged,
because it is now visible on the live front door: the landing page renders
**New York · 5 boroughs** beside **Wisconsin · all 72 counties**, while 15 of
New York's 33 layers answer everywhere in the state and a click in Buffalo
returns seven cards naming real officeholders. The coverage map tells the
two-tier story correctly — a dashed state wash over a solid five-borough fill —
so the map and the scope line now say different things. Three options: leave
it, which understates the instance on the one line most readers see; "statewide,
5 boroughs in depth", honest about both tiers but the only scope string in the
fleet that is not a count; or "all 62 counties", which matches the other
statewide instances and overstates, because no county tier exists yet and the
county card names nobody. **The session would take the middle one and so would
I** — the rule being protected is "never claim a county tier you do not have",
and naming both tiers keeps that.

**2. Hancock needs an e-mail, and only you can send it.** Not blocking anything
else. #1018 is a weekly roster PR that would ship `Jo0n Mason` — a zero where an
`h` belongs — and replace `Alex Blythe` with `Billy Cramer` in the same run. The
Illinois session measured it properly and my first reading of it was wrong: the
parser is fine, the county's own page prints the zero, and the two replaced
names appear on that page zero times, so these are real edits by the county.
The certified returns make it stranger rather than clearer — Billy Cramer has
never run for county board, and Joshua L. Turner, the man the page just dropped,
won the 2026 District 4 Republican primary. That fits two mid-term appointments
and it fits a county page edited wrongly, and nothing published can tell them
apart. Every repair available to us is a guess at a real person's name, so
nothing ships. The ask is two questions to `elections@hancockcounty-il.gov`:
the District 4 member's correct name, and whether Billy Cramer holds District 2.
Illinois drafts it. **Meanwhile main names all fifteen Hancock members
correctly, so no reader sees any of this.**

**4. CLOSED 2026-09-19 — a refusal stops the fetch and never unpublishes, and Iowa's builder now does it.**

**A correction to what I told Adam about this, twice.** I reported that two Iowa counties "came off the site" and that six named supervisors and two county pages were lost. **They were not.** #1048 is a bot PR that has never been merged; main has carried Bremer and Hamilton with all six names and both county pages throughout, verified against the shipped roster and the file's own git log. What happened is that a weekly run PROPOSED the deletion, `check_roster_retention` refused it, and the PR was held. Nothing reached a reader. The episode is the guard working, not a loss — and it matters which, because one of those is a reason to look harder at the guards and the other is a reason to trust them.

Original ruling below.

**4a. ANSWERED 2026-09-19 — a refusal stops the fetch and never unpublishes.** Adam's words: "Preserve data we have already fetched." Recorded in `CLAUDE.md`'s robots section as standing fleet policy (#1050) and routed to Iowa to implement. Obeying a refusal and deleting what it gave us earlier are different acts; the first is not in question and the second costs a reader the answer while gaining the publisher nothing. Illinois and Wisconsin had already landed here independently, which is what made Iowa visible as the outlier. Iowa shipped that builder change as #1051 (`61a3b48`). #1048 stays held until the next weekly run writes real `readOn` dates — and a preserved county needs a per-source last-read stamp, because the card prints one instance-wide verified date that would otherwise assert a verification nobody performed.

**3. New York's county tier has no owner.** Not blocking. Of 57 non-city
counties, 26 have an unverified board form in the plan's own table, and each is
settled from a certified election document when that county is built. Worth
knowing whether the New York session starts it or whether New York rests here.
| The manager's cheap gate read STALE state from the GitHub API | manager | open — measured once, watch for a second | 2026-09-22 | At the 13:21 UTC check-in, `actions_list` for `smoke-test.yml` on `main` returned `total_count` **1090** and a newest run of **#1061, 2026-09-21T00:22Z**. Every check that hour and the four before it had read `total_count` 1162 with a 2026-09-22 head, and `git fetch` against the repository at the same minute showed main at `3cc29d3` with four commits the API listing did not contain. **So the listing was roughly a day behind and looked exactly like a quiet hour.** That is the failure mode the cheap gate cannot see by construction: it reports "nothing changed" from a stale read and a "nothing changed" reply is indistinguishable from a correct one. Caught only because the number went DOWN — 1162 to 1090 — which a reader watching the same figure each hour notices and a fresh reader would not. **Mitigation used and worth keeping: verify a surprising API answer against `git fetch origin main` before believing it**, which is the notification's own standing instruction and cost one command. Not yet worth a gate: one occurrence, cause unknown (cache, replica lag or pagination), and the repository read is authoritative and cheap. If it recurs, the fix is to take SINCE from `git log origin/main` rather than from the API at all. |
| **E.A.M. — the official definition of "done" for a state** | manager | **MERGED 2026-09-22 as `1b1697b` (#1081); the gate runs on every PR** | 2026-09-22 | Adam asked when a state counts as done and ruled the three questions that decide it. **A state is done when it is EXAMINED, ANSWERED and MAINTAINED**, and passing all three **switches that state's session from expansion to maintenance** — it stops hunting counties and only tends what ships. **"No gaps left" was rejected and the reason is the whole design:** Illinois carries 104 gap records and is the deepest instance in the fleet where San Francisco carries two, so counting gaps rewards not looking. The bars measure what this project controls instead of what county publishers control. **EXAMINED** — every county of the state is served by a roster or named by a gap record, denominator the whole state and never the coverage ring (a ring denominator is vacuous: a state serves every county it has bothered to list). **ANSWERED** — every district drawn names a member, is marked vacant, or carries a note; **honesty is the bar, not completeness**, per Adam's ruling, so a card naming two of three seats and stating the third is unlisted passes. **MAINTAINED** — every data file **the app reads** is under a stated plan: a scheduled job that rewrites it, a scheduled watcher on its source, or a `<tag>/WATCH.md` row naming it and stating WHEN it is re-checked. **Internal only**, per Adam: publishing the mark would promise readers something a county publisher can revoke any week. **CORRECTED 2026-09-22, hours after this row was written, and the correction is the point of the row.** M first measured only the ROSTER files the per-county pages read. **Wisconsin found that hole without being able to run the measure** (#1081 is not on main): it flagged their 72-record `county-board-directory.json` and MISSED `county-supervisory-districts.json` — 1,590 districts, 4.6 MB, the file the county-board card is drawn on and the one the directory restates. A bar that fails a restatement and passes its source is not measuring what it claims to. Measured at that scope, **311 of 435 app-referenced data files across the fleet were under no job and no watcher** and the bar said nothing about any of them. Adam widened it the same day, and allowed a dated `WATCH.md` row to satisfy it, because boundaries do not move weekly — Wisconsin's are filed with LTSB on 15 January and 15 July BY STATUTE, so a weekly job against them is a guaranteed no-op. The row must state a WHEN; a filename in prose is a mention. **Measured under the widened bar: il EA· (221 files with no plan and NO `WATCH.md` at all), wi EA· (30), ia ·A· (16), mi ·A· (14). NOTHING IS E.A.M.** Illinois passed for one hour under the narrow bar, which was not looking at 221 of its own shipped files. **ANSWERED already passes everywhere** (0 unanswered of 2,599 districts, 3,005 people), which is the honesty rule holding on its own and why that ruling was right. `scripts/build_eam_status.py` computes it and `docs/EAM_STATUS.md` is generated, so **the mark goes backward** — negative-tested: one unexamined county flips Wisconsin to `·A·`, and a county denominator shrunk to flatter the score fails loudly. **A LIMIT WORTH KNOWING BEFORE TRUSTING A NUMBER FROM IT: this measure was corrected FOUR times on the day it was built — three by its author, one by Wisconsin — and it has no self-test that would have caught any of them.** Every catch came from reading a finding against its source before acting on it. Each defect had the same shape: confidently wrong in a readable way, naming a file and giving a reason that did not survive contact with the source. That is the failure this project is built to catch in DATA, and it applies to the instruments too. **THE FIFTH CORRECTION CAME THE NEXT HOUR AND IT WAS THE REPORT ITSELF (#1085).** M counted people with `blob.count('"name"')`, and a GeoJSON feature's `properties.name` is a POLYGON'S LABEL — so the report told four sessions that `mi-precincts.json` "names **3,895** people and nothing refreshes them, so they go stale at the speed that board turns over", about a precinct boundary layer whose lines move once a decade. Measured: **171 report lines claimed a person count, 12,654 people in total, and EVERY ONE WAS WRONG** — 169 FeatureCollections plus two polling-place files whose names are buildings. **AN OVERSTATEMENT MISROUTES WORK EXACTLY AS AN UNDERSTATEMENT DOES**: it sends a session to build a weekly scraper for a file that needs none. Corrected, the report says something quite different and worth knowing: of **276** unmaintained files across the fleet, **257 are boundaries, 19 are structure, and NOT ONE NAMES A PERSON** — no officeholder is going stale anywhere for want of a job, and what these files want is a stated re-check cadence, not a scraper. No mark moved, because the count was report prose. **The classifier now has the self-test this row said it lacked**, ten files whose shape is settled including the ones the old reader got wrong, failing on a case whose file has left the tree; and an `eval` that had been making `validate_python_hygiene.py` skip its whole-file name check — on this exact file — is now `ast.literal_eval`. The battery pair goes 69/96 to 69/97. **MERGED 2026-09-22 as `8c64d51`**, verified on main. **THE MERGE ORDER HAD TO BE INVERTED AND THAT WAS FOUND BY A STOP HOOK RATHER THAN BY THINKING.** This PR adds a gate to the battery, so merging it first would have turned #1083 and #1082 — both green, both already reviewed — red against a check that did not exist when either was written. The announced order had this one first. It was caught only because a stop hook flagged an uncommitted `docs/EAM_STATUS.md` left on a throwaway verification branch, which prompted a look at what the branch was verifying; the order was then measured both ways before being changed, and the two went in as `a59b4d7` and `bd9060c` ahead of it. **A NEW GATE IS ALWAYS THE LAST MERGE OF ITS BATCH**, because every other open PR was written against a battery that did not have it. |
| **A county tag with no outline makes the gaps panel claim a clean spot** | manager -> mi | open, held on #1086 2026-09-22 | 2026-09-22 | Found holding Michigan's `counties` arrays, and it is the honesty rule rather than a style point. The Data gaps panel locates a gap by fetching `data/app/<slug>-county-outline.json`; **Michigan ships none** (`metro-outline.json` alone), so all 35 fetches 404 and `appliesHere` returns false, while `mappable` flips TRUE because the arrays are now non-empty. `here` is empty and `inCoverage` is true, so the lede falls to "Nothing recorded is missing where you clicked" — **told to a reader standing in one of the 35 counties whose board this app cannot answer.** Point-in-polygoned four seats (Munising, Cadillac, Corunna, Bessemer) against Michigan's own wash: all four inside. **The empty arrays were accidentally protecting the reader** — `mappable` was false, so the panel used its honest cannot-tell wording, which is why populating them correctly makes the panel worse before it makes it better. The branch's own comment says "Neither may claim their spot is clean", written after this exact bug was measured in Wisconsin. Two routes given: ship the 35 outlines as gap-location geometry (what the gap-record skill already prescribes), or make `mappable` require the outline to have LOADED. **THE GENERAL RULE IS THE PART WORTH KEEPING: a `counties` tag is a promise the panel can locate the county, and an instance with no outlines cannot keep it** — so any instance populating `counties` must ship the geometry in the same change or the tag makes the app lie. Illinois and Wisconsin ship outlines and are unaffected; Iowa ships 2 of 99 and is the next one this can bite. Second-order: `fetchJSONWithRetry(..., 2)` is 3 requests per county per click, so 35 untagged-geometry counties is ~105 failing requests on every panel open. **CLOSED 2026-09-22 as `0f73fc2` (#1087), Adam ruling "ship the outlines".** 35 files, 80.1 KB, built by `mi/scripts/build_mi_gap_outlines.py`; Michigan reads **EA·** and a click in Alger, Wexford, Shiawassee or Gogebic now names the gap that applies there. **THE TWO HALVES COULD NOT LAND SEPARATELY AND THAT IS THE DURABLE PART**: `build_coverage_gaps.py`'s county check went back to STRICT, so outlines-without-tags fails the fifth refusal and tags-without-outlines fails the slug check — my morning relaxation to `if outlines` was the wrong fix for a real problem, and skipping a check is what let a tag exist with no geometry. #1086 is merged into #1087 with its commits rather than retyped. **AND THE BUILD'S OWN DEFECT IS THE ONE WORTH CARRYING**: the first pass wrote `alger-county-county-outline.json` (TIGERweb's NAME is "Alger County"), and ALL 1,225 internal assertions passed it, because the outlines were perfectly consistent WITH EACH OTHER. **NOTHING IN A SELF-CONSISTENT VERIFICATION CAN SEE A NAMING CONVENTION** — only comparing to the CONSUMER can, which is now `check_slugs_match_gap_records()` and reports UNCHECKED rather than OK when no gap names a county. Verification is the Census's own INTPTLAT/INTPTLON per county, inside its own outline and outside all 34 others, rather than the hand-typed anchor pairs Illinois's equivalent carries: 35 counties is 35 chances to mistype a coordinate and have it read as data. **The derived county list means a roster tranche retires an outline on its own, and `--check` FAILS on one for a county since served — so the tranche and the rebuild travel together.** |
| **Michigan keeps its "why not" records where the measurement cannot see them** | manager | open, routed 2026-09-22 | 2026-09-22 | Found by E.A.M. rather than by reading. Michigan scores **48 of 83 counties examined** while `mi/data/source/mi-county-board-probe.json` records a measured blocker for **25 more** — so it is examined at 73 of 83 in substance and scores 48. **Two readers of one question, which is the defect this repo names in its own docs repeatedly.** The gap record is the canonical home for "why this county is not served" (the gap-record skill says a gap record is the only thing that makes an absence visible); a probe artifact is a measurement filed somewhere only its own author reads. Wanted: promote the 25 into gap records, keeping the probe as the instrument that produces them rather than as the place they live. **Not done to Michigan's instance unasked** — this is their call and their bookkeeping. **RE-ROUTED 2026-09-22 15:07 UTC WITH THE ARITHMETIC MEASURED, and the block turned out to be OURS rather than theirs.** #1082 promoted the probes into 26 gap records and every `counties` array came out EMPTY — because `build_coverage_gaps.py` validated each slug against an instance's shipped outlines with `outlines is not None`, and an instance with none returns an EMPTY SET, so it rejected every tag Michigan could ever write. **Michigan ships zero county outlines, so the array was unreachable by construction and nobody could have seen that from the record.** #1081 fixed it (`if outlines`). Measured on main after the merge: Michigan's roster covers 48 counties, its six `mi-county-board-*` records name 35 between them, the two sets are DISJOINT and sum to exactly 83 — so populating the arrays takes E from 48/83 to 83/83 and the mark from `·A·` to `EA·`, with nothing else about the instance changing. Routed with the caveat that the 35 came off a regex over the records' own `area` prose, which is exactly the Bay/Marquette hazard Michigan warned about: good enough to prove the arithmetic, not good enough to ship, so the arrays go from `mi-county-board-probe.json` and the prose becomes a restatement of the array. |
