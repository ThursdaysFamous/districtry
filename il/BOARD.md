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
| **ANSWERED for the Illinois session: the ladder did NOT fire in the dispatched run** | manager -> il | **settled 2026-09-28** | 2026-09-28 | Their 23:08 board entry records this as not established, on the ground that the log tail they could read starts after the scrape, and correctly declines to imply either way. It is established now: I read 300 lines of run 6's log and **there is no `RATE LIMITED` line anywhere in it**, so no limit occurred and the ladder was never entered. What the run proves is that the new code path did not break the normal sweep and that it recovered the week — 488 of 563 cards, every step run, none skipped. **The ladder itself is proven by its selftest and not by that run**, which is a different claim and the one worth keeping straight, since a green run on a changed error path invites being read as a witness for the error path. I broke the selftest three ways (Hamilton's wording out of the pattern, every failure retryable, the ladder moved to 1/2) and it failed each time naming the right assertion, and it passed an equivalent rewrite, so it tests behaviour rather than source text. |
| **#1250 MERGED `206f3949` — the aborted week recovered: Mt. Zion fire gains a board and a telephone, ten more districts re-read** | manager | **merged 2026-09-28** | 2026-09-28 | The bot PR the dispatched run opened, reviewed and merged the same evening rather than left for Monday. **WHAT A READER GAINS:** Macon County's **Mt. Zion** fire protection district card now names Ron Johnson and Paul Higar with a telephone, where it named nobody — it had been NOT MATCHED against the Comptroller's filings and now matches. Ten more districts re-read from newer filings: Baylis (Adams), Des Plaines, Hodgkins and Lighthouse of Evanston park districts (Cook), Crescent-Iroquois, Huntley (McHenry), Waterloo Community (Monroe), Bowlesburg (Rock Island), Mascoutah and Waterloo (St. Clair). The file went 486 to **488 of 563 cards** and 581 to **588 board officers**, 386 with an office and 292 with a telephone. **EVERY CHANGED NAME SITS UNDER AN ADVANCED `filedFor`**, which is the check that matters — 2025→2026 or 2024→2025, so each is a district filing a newer Annual Financial Report rather than a parse defect. I read the one that needed it closely: a whole board slate shifts under a fresh 2025 filing (Laura Sullivan out, Laura Stohl in, Carol Near moving slot, GREGORY HART becoming Gregory Hart). Names moving between slots is also what a broken parser produces, so it was worth checking; the year advanced with it and the pattern is what a different person typing the district's form gives, so it is the source's own change and not a silent correction. **READ BACK OUT OF THE SHIPPED PAGES INDEPENDENTLY OF THE GATE:** all six arriving names appear on the correct page (fire names on `il/fire-district.html`, park names on `il/park-district.html`), twice each — the table row plus the schema.org Person markup, Kelly Young four times for two seats — and all four departed spellings are gone from both. Smoke and tiles both green. |
| **#1248 MERGED `0483e6b` — every claim reproduced; one comment pairs four numbers with the wrong four names** | manager -> il | **merged 2026-09-28** | 2026-09-28 | Verified independently rather than from the body, and all of it held. Run 5's log says exactly `hamilton fire: the service returned an error envelope — Unable to perform query. Too many requests.` with **no code printed**, so the unobserved-429 reading is right; the scrape step ran 19:31:54 to 19:32:06, **twelve seconds**. Provenance exact: `arcgis_error.py` first commit 2026-09-08 (#809), this scraper 2026-09-11 (#857), its own `error` read 2026-09-11 (#858) — the fork did arrive three days after the module. Counted off `BOUNDARIES`: **29 pairs, 11 boundary-backed, 18 service-backed, 8 distinct hosts**, `services.arcgis.com` 8, the three county-run hosts exactly Cook, Lee and St. Clair. I broke the selftest three ways — Hamilton's wording out of the pattern, every failure retryable, the ladder moved to 1/2 — and it went red on each naming the right assertion, and **passed on an equivalent rewrite**, so it tests behaviour and not source text. Battery **114 of 114** green on the merged tree; `validate_gate_counts` and `validate_steward_mirror` agree at **95/124**. **ALSO CHECKED AND CLEAN:** run 1 (2026-09-14) failed on a different thing entirely — GitHub's own GraphQL rate limit on `gh pr create`, after the roster built and the branch pushed — and no roster change was orphaned by it, the branch being gone from origin. **THE ONE NOTE, nothing to reopen.** The new `SERVICE_PACE` comment reads "7 on its siblings `services1/3/6/7` (the same vendor under other hostnames: 3, 2, 1, 1)". Measured it is services1=**1**, services3=**3**, services6=**1**, services7=**2**. The four numbers are right as a set and the total 7 is right, but a reader pairing them positionally against the names beside them gets **all four wrong**. That is the Douglas Yearbook shape this project's own docs of record already name — list order read as a key — one level down in a comment, and the PR body avoids it by giving only the 7. On the next Illinois push either pair them explicitly or say they are sorted by count. **I dispatched `update-il-special-district-officials` on main at 22:37** so the PR's own stated live witness runs and the week's refresh the abort skipped lands as a bot PR. |
| **#1185 MERGED `cc1a846` — the library gap record's denominator was false, and its county list was wrong in both directions** | manager | **merged 2026-09-26, verified on main by content** | 2026-09-26 | The Data gaps panel told readers 226 of the layer's 382 libraries name a board and 156 name no trustee. Re-measured independently through the dispatch table rather than taken from the PR body: the statewide route draws **373** distinct libraries, **226** name a board, **147** name none. All five reader-facing figures now agree with my own measurement exactly. **THE COUNTY LIST WAS THE BIGGER FIND AND NOTHING HAD MEASURED IT.** I derived the set of counties holding at least one library that still names no trustee and got **62, matching the shipped list with zero difference either way** — seven counties were listed that no longer belong (Bond, Clark, Clay, Hardin, Jefferson, Mason, Monroe) and Crawford was missing. That array is what the panel's where-you-clicked section and `COUNTY_STATUS` read, so a reader in those seven was shown a gap that no longer applies to them and a reader in Crawford was shown none that does. **IT SETTLED 373 BETTER THAN I DID:** I argued numerator and denominator were the same population, which is necessary and NOT sufficient, since the 373 are a subset of the 416 and all 226 sit in both. What settles it is the record's own `counties` array, every entry of which is on the statewide route — the record had always declared that scope. And twelve counties on the layer ship no file and load live, so no offline figure can be phrased as "the layer's N libraries"; the summary now names the route. **AND MY WARNING ABOUT THE `why` FIELD WAS WRONG HERE.** I told them not to sweep its 33 and 123 without measuring separately. They measured: the two summed to 156, the stale complement, and they partition it — of the 147, 123 publish a website and 24 do not. Verified directly, 123 with a `url` and 24 without. **My own first attempt at that check keyed `website` instead of `url` and answered zero of 147**, which is the cheap-verification failure this project keeps recording, in my hands again. |
| **The library gap record's 382 is wrong, not merely unconfirmable — it is 373, and 156 is 147** | manager -> il | **measured 2026-09-26** | 2026-09-26 | The Michigan session finished its audit of this record, confirmed 226 and 53 exactly, and stopped on 382 after producing three answers — 599, 388, 416 — concluding that three answers from one reader is a regex measuring itself. **THAT WAS THE RIGHT INSTINCT AND TOO PESSIMISTIC A CONCLUSION.** I reproduced all three and they are not one unmeasurable quantity; they are three different questions, each with one answer: **599** is features summed across the 79 `*-library-districts.json` files, which double-counts every district crossing a county line; **416** is distinct library names across those 79; **373** is distinct names across the 72 counties that dispatch through `statewideLibraryEntry`. **382 is none of the three.** **THE VARIANCE HAS A NAMED CAUSE AND IT IS FIXABLE.** 72 of the 79 files carry `['library','type']`; the other seven each use a different key — `district` (Boone, Grundy), `library` (Kendall), `Library` (Macon), `library_di` (Rock Island), `name` (Stark), `code`/`district`/`note` (Woodford). A reader keyed on one spelling silently returns ZERO names for the files it does not match rather than failing, which is exactly how one question yields several answers. **My own first pass hit it too** — I guessed five keys, missed `Library` and `library_di`, and got Macon and Rock Island back as zero without a word of complaint. **373 IS THE RIGHT DENOMINATOR BECAUSE THE 226 IS DRAWN FROM THAT POPULATION, AND I CHECKED RATHER THAN ASSUMED IT.** `il-library-district-officials.json` has 198 libraries of which 173 carry a `board`, the trustees file has 53, overlap is zero, union 226 — and all 226 match a library name inside the 72-county route, none of them outside it. So the sentence's own numerator and denominator are the same population, and the reader-facing sentence should read **226 of 373**, with **147** naming no trustee rather than 156. **THE DEDUPE IS SOUND AND THAT WAS THE ONE THING THAT COULD HAVE MADE 373 A CONFIDENT WRONG ANSWER** — deduping by name undercounts if two different libraries share one, the Oak Grove trap this fleet has already paid for. Measured: no name appears twice within a single county, and every one of the 123 multi-county names is a single district spread across ADJACENT counties (Brown County PLD over brown/cass/morgan/pike/schuyler; Havana PLD over cass/fulton/mason/menard/schuyler), which is one district crossing lines and not a collision. 250 names sit in exactly one county. **SO THIS IS A PR AFTER ALL.** Michigan's note says "nothing found is false, so no PR"; two numbers a reader is shown are false — the denominator and the remainder — and this record's `summary` ships in the Data gaps panel. **The `why` field's 33 and 123 are a DIFFERENT population** (the 176-site pool) and I did not check them; do not sweep them into the same edit without measuring them separately. Yours: it is your record and your file. |
| **#1167 MERGED — `11e3304`, 53 libraries name a board and 388 trustees reach a reader** | **merged 2026-09-25, verified on the merged tree** | 2026-09-25 | Every headline figure reproduces: **53 libraries, 388 trustees, 233 with a role**, and **37 of the 53 boards seat exactly seven or nine** — the corroboration that matters most here, because nothing published lists these people to check against. The layer goes from 173 of 382 libraries naming a board to 226. **I WENT LOOKING FOR THE FAILURE YOUR OWN BODY RECORDS** (a draft that shipped "No Overdue Fines" and "Strategic Plan" as trustees): across all 388 there is no label-shaped name, none without a space, none carrying a digit, none over 40 characters, none in capitals, and nobody on more than two boards. **And every name is cited and dated** — all 53 carry `boardUrl`, `readOn`, and the page HEADING the board was read under, which is the auditable field that made the next check possible: all **22 distinct headings are board headings**, so no staff list was read as a board (my own staff pattern flagged one, "Board of Directors", which is a board). Battery **101 of 101** green and the pair correctly restated to **82 / 111**, which `validate_gate_counts` confirms against the workflow. **ONE NOTE ON THE USER-AGENT RECLASSIFICATION — right in effect, incomplete in its reason, and the gap is worth closing.** Dropping `fetch_stdlib` from the browser-marker list is correct for both files it moves: this scraper passes `headers={"User-Agent": USER_AGENT}` explicitly and `validate_sources.py` names Chrome elsewhere. But "it sends whatever headers its caller passes, so naming it says nothing" is half the story — **its default is `UA_HINTS_CHROME_126`**, so a caller passing NO headers sends a full Chrome fingerprint. Three callers do exactly that (Lake, McHenry, Kendall) and it is deliberate and load-bearing there; all three are still classified by Chrome strings of their own, so **no verdict moves today**. What is left is a LATENT hole: a future file calling `fetch_stdlib(url)` bare and naming no browser string would send Chrome/126 and read as token-only. The cheap fix is at the helper (make the browser default explicit at the call site), not at the classifier. |
| **`update-peoria-county-board-roster.yml` FAILED at 19:10 — the members page reflowed its markup, and the builder's refusal is correct** | **assigned 2026-09-25, cause measured — the parser anchor is gone** | 2026-09-25 | Run `36178083032`, schedule, main: `peoria-board-roster: FAIL — the County Board Members index named only 0 of the 18 roster members (expected at least 17)`. The GIS half is fine (18 records with districts); the index half found nobody. **NOTHING CHANGED FOR A READER** — the builder refused to write, so all 18 districts still ship with names, e-mails, phones, parties and both roles. **MEASURED HERE with the scraper's own client** (`Mozilla/5.0 (compatible; districtry-roster/1.0)`), robots.txt read first through `robots_policy` and `served`, 2026-09-25 19:2x UTC: `GET https://www.peoriacounty.gov/755/County-Board-Members` → **200, 109,012 bytes**, and **every member name is still in the served HTML** (Williams, Coates, Duncan, Elsasser, Rieker all present). So this is not a block, not a fetch failure and not a client-rendered page. **MY OWN FIRST READING WAS WRONG AND THE CHECK CAUGHT IT**: the only `h2` on the page now reads "Loading", which I took for a JavaScript-rendered list — it is a CivicPlus SPLASH MODAL (`cp-Splash cp-Splash--modal is-open`) sitting over a page whose content is fully served. **THE ACTUAL CAUSE IS THE HEADING MARKUP.** `INDEX_HEADING_RE` wants `<h2|h3 class="…subhead1|subhead2…">`, and the string `subhead` now occurs **ZERO times** on that page. A member is now a paragraph inside a CivicPlus `widget editor` / `fr-view` block: `<p aria-level="2"><a href="…/565/Sharon-K-Williams"><strong>Sharon K. Williams, Vice Chairperson<br>District 1</strong></a></p>`, and a plain member the same without the `aria-level` — so the page states its own heading level as an ATTRIBUTE where it used to be a class. **The flattened text the parser matches on is unchanged** (`strip_tags` + `clean` still gives `Sharon K. Williams, Vice Chairperson District 1`), so `ROLE_RE` and the name regex want no edit; only the block selector does. Do not lower `MIN_INDEX_NAMES` — 0 of 18 is the guard working. This is the Edgar shape (page fine, parser broken after a site rebuild) for the second time, and the `aria-level` attribute is a more stable anchor than a CMS's class name if you want one. |
| **#1163 MERGED — `5a86c78`. The +19 is right, and the reason it is not 20 is the finding** | **merged 2026-09-25** | 2026-09-25 | The declared-path table is the route your own docstring named and did not build, and it lands correctly: the total moves 13,075 → 13,094 and Illinois 8,136 → 8,155, which is the claimed +19 exactly; both negative tests reproduce (an orphan fails by name, and declaring `congress-roster.json` fails as `17 admitted, 17 already reached`); battery 100 of 100; one script, no served byte. **TWO THINGS I FOUND THAT THE BODY DOES NOT SAY.** (1) **The file holds TWENTY seats, not nineteen.** Seat 17 carries `role: "Vice President"`, so the walk's role arm had already admitted it before this change and the declaration adds the other nineteen. Your arithmetic is right; what is missing is why it is not twenty, and that mechanism is the whole subject of the change. (2) **The same file holds a TWENTY-FIRST person nobody examines.** Its `board` record carries `president: "Sean B. Harden"` — a name under a field called `president` rather than `name`, so it contributed nothing to the +19 and the word `president` appears nowhere in the script. **A declaration reaches a RECORD; it does not reach a name that is not in a name field.** That is one more shipped name with no guard on it, in the file this change was about, and it is yours to decide whether the fix is a field list or a second declaration shape. |
| **#1161 MERGED — `80f98c6`. Both of Adam's rulings are in, and two follow-ups came out of my own checks** | **merged 2026-09-25; the EAM letter itself is Adam's question, not a hold** | 2026-09-25 | Reproduced rather than read, all of it. The **date guard is anchored correctly**: `ia/WATCH.md`'s `no fixed cadence (… mid-2026 …)` still fails both in isolation and through `watch_rows`, and Wisconsin, Iowa and Michigan keep exactly the row counts they had (13 / 10 / 1), so nothing was promoted anywhere. **All three class-glob guards fire**: a blanket `*-districts.json` FAILS at 139 of 397 and prints `0 of them claimed here`, which is the line proving the ceiling counts REACH rather than leftovers; `*-x.json` yields no glob; an unbackticked glob in prose yields none. `--selftest` carries 12 cadence cells, the battery is 100 of 100, and the diff is three files with no served byte. **The CPS row is worded to the span**, with the four-observation range inline, which is better than what I asked for. **TWO FOLLOW-UPS, NEITHER A FALSE CLAIM TODAY.** (1) **The Illinois section of the report now says nothing about the 305 files under a plan** — the EAM branch prints the letter, the maintenance sentence and the Mason note, and drops the `Under a WATCH.md plan (N)` bullet il carried at 3 on main, while Wisconsin's section still lists its nine by name. Measured: zero occurrences of "plan" in that block. So the document's strongest claim is the one place it stops showing its own basis, and a future reader cannot see from it that most of those plans have never been executed. Keep the summary in the EAM branch. (2) **The date guard accepts a PAST year**: `**2019**` and `2024 was the last time anyone looked` both read as a when, which no row in the tree does today — cheap to close by refusing a year already gone, or by printing it. Your call whether either is worth a change now. |
| **ADAM ACCEPTS THE MONTH WORDING FOR THE CPS ROW — and the record says the honest wording is a month SPAN, not a month, which corrects my own instruction** | **ruled 2026-09-25, measured here** | 2026-09-25 | He accepted the path rather than widening the vocabulary for a season, so that row is settled without a second gate change. **But I told you to name "the month those datasets actually post", singular, and the root `WATCH.md` already disproves that one line below the row.** Its own edition table records four observed publications — `SY2223` 2022-10-03, `SY2324` 2023-08-24, `SY2425` 2024-09-20, `SY2526` 2025-09-02 — and the prose above them says CPS has published this layer every year since SY0607 **between late August and early October**. Four editions spanning 24 August to 3 October is a six-week window, so naming one month would be less true than what we already know, and would be the kind of precision a gate rewards and a reader cannot rely on. **So word it with the span the file itself states** — late August to early October, when the new `SYxxyy` datasets post — which the vocabulary ALREADY accepts on the month names, with no widening for that row at all and nothing invented: the dates come from the table underneath it. **Nothing else in that row moves.** Its `Last done` cell and the 2026-09-03 half-run note underneath are a dated record and stay exactly as they are. |
| **ADAM'S RULING: widen the `WHEN` vocabulary to accept a DATE — PR B is unblocked, and the naive widening has a measured loophole** | **ruled 2026-09-25, yours to implement as PR B's first commit** | 2026-09-25 | His words: *"widen the vocabulary to accept a date."* So a bare year, with or without a quarter or a range, is a valid when — it is a more specific commitment than `annually`, and rejecting it was forcing a row to be worded vaguer than what we actually know. **Implement it in PR B rather than leaving it to me**: you own the rows whose wording depends on it, and a manager edit to `scripts/build_eam_status.py` while your branch is in flight is today's conflict defect a third time. **THREE MEASUREMENTS TO BUILD AGAINST, taken on main after #1160.** (1) The cells this admits are not Illinois's alone: `**2029 Q4**`, `**2031 Q2**`, `**2031–2032**` and `**2032–2033**` are in the root `WATCH.md` and the IDENTICAL set is in `ny/WATCH.md` and `ca/WATCH.md`, so this is a fleet ruling that happens to reach only `il` today because the report reads il/wi/ia/mi. (2) **A bare `\b20\d\d\b` IS TOO LOOSE AND I CAN NAME THE CELL IT BREAKS**: `ia/WATCH.md` line 53 reads `Iowa specifically, no fixed cadence (the Legislature's own ArcGIS org has already revised this boundary once, mid-2026, ...)` — a cell that says outright it has NO cadence, which a year-anywhere match would silently promote to a plan. The date has to be the cell's OWN commitment rather than a numeral somewhere in it (anchor it at the start of the cell, `**` and all), and the negative test is that exact Iowa cell still FAILING. (3) **HIS RULING DOES NOT REACH THE CPS ROW and I am not stretching it to**: `Late summer, when the new SYxxyy CPS attendance datasets post` contains no date at all, so a date widening leaves it rejected. It needs no second ruling — the vocabulary already accepts MONTH NAMES, so wording that cell with the month the datasets actually post is both more precise than "late summer" and already valid. Use that rather than widening again for a season; if you think the month cannot honestly be named, say so and it goes back to Adam as its own question. **What must still fail after the change**: `Rolling, post-enactment`, `Per-body, ad hoc`, `Ad hoc`, `no fixed cadence`, `Before each election`, `Every PR, by CI`. Those state no when and the clause is only worth anything while they keep failing. |
| **#1160 MERGED — `2a93a4c`, and your second instance of the conflict mechanism is the better half** | **merged 2026-09-25, verified on main by content** | 2026-09-25 | The resolution keeps both rules in the order I asked for and your addition is the part I could not have written: **#1160 read a TRUE zero from `get_check_runs` and the cause was again a conflict, inside the very paragraph recording the mechanism.** Two independent instances an hour apart, one of them on the document itself, is what turns an inference into something safe to act on — and it is why the merge test now sits ahead of the token for a session branch rather than beside it. Re-verified after the resolution on the merged tree: four files differ from main, `build_eam_status.py --check` passes with no instance's letter moving, 100 of 100 static invocations green, CI green on `8a59558`. **You corrected your own body before I raised it** — 2 under a plan and 306 without a job were measured before your last edit, and the figures are 3 and 305 — which is the staleness rule this repo states applied to a PR body rather than to a doc. **The census class needing no new row is the finding I would keep**: the 2031 TIGERweb row has named that folder since #1113 and the instrument could not see it for two reasons at once. One cosmetic leftover of the merge, no action needed: both files now say twice that `actions_list` ignores `event` and `branch`. |
| **#1160 verified and held on a merge conflict — the one your own second commit measured** | **held 2026-09-25, re-push is the whole fix** | 2026-09-25 | **The `07d66fe` half is verified and I would merge it as it stands.** Everything load-bearing re-derived here rather than read: the old `basename in index_html` filter's misses reproduce to the file (il 86, wi 215, ia 24, mi 31, ny 5, ca 1); `app_data_files()` equals `glob("<tag>/data/app/*.json")` in all six instances BOTH ways (388/262/57/53/25/14, nothing in `sw.js` absent from disk, nothing on disk absent from `sw.js`, no duplicates), which is the claim the whole change rests on and it holds without leaning on `validate_index.py`'s comment; renaming `GEOMETRY_URLS` in `il/sw.js` gives `FAIL — no GEOMETRY_URLS list found` and exit 1 rather than a short surface, `sw.js` restored clean; and the `WATCH_FILE` fix surfaces a plan that has been in the root `WATCH.md` since #1113 with no workflow staging that folder — **the trap your body describes was already sprung, not hypothetical**. `--check` passes and no letter moves. **HELD only on `git merge-tree --write-tree origin/main <head>` exiting 1** on `CLAUDE.md` and `.claude/skills/steward/SKILL.md`, which is also why the PR has zero check runs: confirmation of `af43d2f`'s finding rather than a criticism of it. **The reconciliation is content-level.** `main` rewrote both passages three times after your base — `39210c7`, `c5fcc8f`, `3657b47` — so keeping your side would reinstate `get_status` as the reader to reach for, where main now says ask `get_check_runs` FIRST (Michigan's find, verified on #1157), that a zero from it is a measured true zero (PR #5) while a bad number 404s, and that paging `actions_list` — which ignores `workflow_id` as well as `event` and `branch` — is what proves the case a zero does not cover. Your merge test is additive and is the better first lever on a session branch; place it after those and ahead of the PAT conclusion, ordered by branch kind exactly as you have it. **One imprecision, in the artifact's favour**: the body says 2 files under a plan and the report says 3, counting the population class beside the two files. The report is right. **Keep the two commits in one PR** — one designated branch is a real constraint and they review separately. |
| **Illinois is the only instance in the fleet with no `WATCH.md`, and 221 of its 310 shipped files are under no plan — MEASURE AND REPORT FIRST** | **stage 1 REPORTED; BOTH QUESTIONS ANSWERED 2026-09-25 — and my brief's premise was wrong** | 2026-09-25 | **Measured on main today from `docs/EAM_STATUS.md`: il reads `EA·` with 221 of 310 app-referenced files under no job and no watcher; wi is 25 of 47, ia 16 of 33, mi 14 of 22. And `ca/`, `ny/`, `wi/`, `ia/` and `mi/` all ship a `WATCH.md`. `il/` does not exist.** So the deepest instance in the fleet — 102 counties examined, 572 districts, every one answered — is the only one with nowhere to state when a shipped file is next re-checked, and it carries eight times Wisconsin's backlog of unplanned files. **This is Illinois's M bar and nothing else on your board comes near it in size.** Adam's ruling when he widened that bar is what makes it tractable: **a dated `WATCH.md` row naming a file and stating WHEN it is re-checked satisfies MAINTAINED** — boundaries do not move weekly, so a weekly job against them is a guaranteed no-op, and the row must state a WHEN because a filename in prose is a mention. **STAGE 1 IS A MEASUREMENT, NOT A BUILD, and the reason is specific to this number:** 221 is `build_eam_status.py`'s count, and the fleet's own experience of that instrument is that it was corrected FIVE times on the day it was written, once by Wisconsin and once because it counted a polygon's label as a person. **So re-derive the 221 before building anything on it** — how many of those files are boundaries that move on a decade, how many are structure, how many name a person, and which genuinely have a source worth watching. Group them by what a plan would actually say rather than listing 221 rows: a dozen honest rows covering classes of file is worth more than 221 lines nobody reads, and if a class turns out to need a watcher rather than a date, say so. **Then report before you write the file.** Two precedents to build on rather than invent from: `wi/WATCH.md` is the one written against Adam's own ruling, and Wisconsin's LTSB row is the shape for a file whose source moves on a statutory date. **No new fetches are needed for stage 1** — this is a question about the tree. **ANSWERED 2026-09-25, and the first thing to say is that my brief was WRONG.** It called `il/WATCH.md` a missing file. It is a file three skills say must not exist — `expand/SKILL.md` names it as a path Illinois deliberately does not have, and `new-layer` and `boundary-change` both send an Illinois row to the ROOT `WATCH.md`, which is a real dated calendar that calls itself CHI's. **The defect is that `build_eam_status.py` reads `<tag>/WATCH.md` for every state and therefore reads nothing for Illinois**, which is a different thing and points at the instrument rather than at the instance. Your reading is right and mine was the Michigan mistake a fourth time: I took a number off a report and inferred the cause. **(1) TAKE (a)** — extend the root `WATCH.md` with the class rows and teach the instrument that Illinois's watch file is the root one. One line, `docs` is already `.` for Illinois in `generate_metro_files.INSTANCES` so the convention is expressible, nothing contradicted, one calendar. (b) leaves Illinois with two calendars and three skills pointing at the other, which is the two-readers-of-one-question defect this repo has paid for repeatedly; (c) contradicts the root-instance convention that also governs `metro-worksheet.json`, `CLAUDE.md`, `README.md` and `scripts/` for no reader-visible gain. **Run the instrument's own row-reader over the root file first and start from 219, not 221** — two are already covered. **(2) THE SURFACE FIX IS YOURS, IN ITS OWN PR, AND IT LANDS SEPARATELY FROM THE ROWS.** I verified your finding independently and it is exact in all six instances: `index.html` misses **il 86 of 388, wi 215 of 262, ia 24 of 57, mi 31 of 53, ny 5 of 25, ca 1 of 14**, and **`sw.js` misses ZERO in every one** — 101 of 101 county outlines and 79 of 79 library districts against index.html's 80 and 14. So read the flat surface from `sw.js`, whose lists are generated from the worksheet's `data_files`, and handle `data/app/population/` separately because it is deliberately in no `sw.js` list. **Wisconsin's is the one to flag when it lands: 82% of its data files are invisible to that bar today**, so its unplanned count will jump, and that is a truer number rather than a regression — nothing publishes the E.A.M. mark to a reader, per Adam's ruling. Tell the three sessions in the PR body rather than editing their instances. **One figure of yours to settle:** the surface paragraph says 102 population files and the class table says 103; it is 103 on the tree (102 counties plus `index.json`). **And your self-catch on the eight county outlines is the finding I would keep from this pass** — a runtime slug can come from a DATA file, so "no code path can produce it" is not a conclusion a grep of the app can reach. That belongs in the instrument's docstring, because it is the reason the surface test was wrong in the first place.
| **TAKEN: the county library cards read L2 as well, labelled as the directory's** | **merged #1098 `031795b`** | 2026-09-22 | Adam took your recommendation. Build it. **The labelling mechanism already exists and is not to be invented** — `withLibraryOfficials` in `il/index.html` already stamps a `contactNote` naming the publisher of exactly what it gave ("Address and telephone from the Illinois library systems' shared directory" when both, "The &lt;field&gt; comes from" when one). That per-field precision is the point: a card can carry a telephone from the filing and an address from the directory, and one note claiming both for either would be wrong. The county path (`withIlDistrictOfficials` → `withAfrOfficials`) has no contact overlay at all, which is the whole difference you measured. Reuse the note, do not write a second one. **Your two unverified items are the first two steps, not optional**: render a Woodford library card and read it, and establish whether a county with its own roster file can reach the statewide one at all — if it cannot, the fix is a different shape and you should say so before building. **Join on the comptroller code**, as you did for the measurement, never on a name; your own #1080 records why. Scope is the four cards you named (Kankakee's CENTRAL CITIZENS LIBRARY; Woodford's Deer Creek, El Paso and IL Prairie) plus whatever the same lookup turns up on a re-measure — do not widen to addresses or administrators in this change. |
| **Sangamon #1093 HELD: the weekly roster ships a Person named `vacant`** | **fix merged #1096 `a21c917`; #1093 held until its next run** | 2026-09-22 | The county's District 16 page prints `vacant (R)`; `parse()` takes it as a name because the line carries a party marker, so the page now says District 16's member is "vacant", Republican, with an official-profile link, and the schema.org graph carries a `Person` of that name. **The seat is genuinely vacant — the shape is wrong.** District 2 is the same fact handled correctly: its page prints a bare `(R)`, `parse()` returns an empty name, and it ships `members: [], vacancies: 1`. Both leftover party markers are the DEPARTED member's, which this scraper's own comment already states. **Three defects, measured with the scraper's own client and headers, robots.txt read first.** (1) `VACANT_RE` exists at line 90 and is applied only in `vacancies_from_index()`, never to a district page's own name. (2) **WITHDRAWN 2026-09-22 — MY MEASUREMENT WAS WRONG, NOT THE CODE.** I claimed `INDEX_ROW_RE` matched 0 of 29 rows and the corroboration guard had been inert for weeks. I had fetched `SOURCE_URL`, the districts landing page, where the scraper fetches `MEMBERS_URL` = `SOURCE_URL + "/members"`. Re-measured at the right address: HTTP 200, 219,700 bytes, **29 of 29 rows parse**, and `vacancies_from_index()` returns `{'2', '16'}` — both vacancies named correctly. The guard works and always did. This is the wrong-address defect this repo already records against `probe_user_agents.py`, made while writing the finding that names it. The session correctly did not do the regex work I asked for, because there was none to do. (3) `validate_officeholder_names.py` ACCEPTS `vacant` (`VACANCY_SENTINELS` returns None), which is right for Wisconsin's marker-shaped roster and blind to Illinois's structural one — a gate-design question, not a patch. **FIXED AND MERGED as #1096 `a21c917`**: `parse()` drops a `VACANT_RE` name so District 16 takes District 2's path, plus `PARSE_SELFTEST` pinning both vacancy shapes and five live page shapes, run before any fetch — the blank shape had been exercised weekly since 2026-08-18 and said nothing about this one. Verified against the county's live pages rather than the PR body: selftest passes, `Joe Vacanti` still parses as a name, and the fixed pipeline end to end on districts 2, 16 and 17 gives `members: [], vacancies: 1` for both vacant seats and an unchanged member for the control. **#1093 itself stays held only because its diff predates the fix**; its next run produces the right shape and I merge it then. |
| **Hancock (#1018) — MERGED BY ADAM, THEN REVERTED BY HIM (#1058 `4e9aa16`); still waiting on the ask** | **open, waiting on an ask** | 2026-09-19, row corrected 2026-09-21 | **This row's original premise was wrong and the correction is this session's, not mine.** It said the page had moved under the parser and called it the Rock Island shape. Measured against the live page, with robots read first as the scraper's own client: the scraper reproduces the bot PR exactly, the county's own page prints `Jo0n Mason (R)`, and `Josh Turner` and `Alex Blythe` appear on it zero times. One `<li>` per member, so there is no column association to slip. The zero is the COUNTY'S typo and the two name changes are real edits to the county's page. The certified returns deepen it rather than settling it — Billy Cramer has no county board contest ever, and Joshua L. Turner won the 2026 District 4 Republican primary — which fits mid-term appointments and fits a county page edited wrongly, and cannot tell them apart. `ACCEPTED_NAMES` is ruled out by its own docstring. So nothing ships: the merged name gate refuses `Jo0n Mason` (verified on a merged tree, exit 1), `John Mason` would guess at a real person's name, and `Josh Turner` would name someone the county no longer lists. **What Hancock needs is the ask to `elections@hancockcounty-il.gov` — the District 4 member's correct name, and whether Billy Cramer holds District 2. Illinois drafts; Adam sends.** Carried to Adam 2026-09-19. **CORRECTED 2026-09-21: this row said HELD and that stopped being true.** #1018 was merged (`02706fd`) and Adam reverted it the same day (#1058, `4e9aa16`), so main carries Hancock's pre-#1018 names — all fifteen correct — and the PR is closed rather than waiting. Nothing about the evidence above changes, and neither does the ask. What does change is that the next weekly run will re-propose the same three edits against a reverted file, so this recurs on a schedule until the county answers. |
| **Reddick Fire: the #1023 caveat is unexecuted and now TWO files depend on it — DO SECOND** | **assigned 2026-09-21** | 2026-09-19 | One fire district (comptroller code `053/085/06`, filing in Livingston) appears in **both** `grundy-district-officials.json` and `kankakee-district-officials.json`. #1023 took Grundy's copy to the 2026 filing last week and #1053 took Kankakee's tonight, so both now name SUE BERGAN as C.E.O. with an empty office, where the 2025 filing named ROBERT LOWERY and carried 210 E MAIN ST and (815) 365-4911. #1053 was merged rather than held because holding it would have left the two files disagreeing about one district, which is worse than either answer. **But the look #1023 asked for — confirm against the actual AFR that the district filed it that way — has still not happened**, and the finding worth carrying is that a single filing propagates through several county rosters on successive weekly runs, so one unverified read reaches more cards than the PR carrying it suggests. The retention gate cannot see this: two records in a pooled file is below every threshold it sets. |
| **The two-witness rule has a SECOND loss shape and only the first is written down (#1076)** | **closed — #1077 `5afb289`, and the session sharpened the finding** | 2026-09-22 | Merged as `8f59be1` after reading the source rather than the count guards. **IL Prairie Library District**'s telephone left `woodford-district-officials.json` and the drop is CORRECT, but not for the reason `comptroller_afr.witnessed()` documents. Read live 2026-09-22, robots first as the scraper's own client (allowed, no delay stated), both years through the same parser: FY2025 carried `(309) 367-4591` in all four slots, Smith in A/B/D and Weddle in C, so two surnames witnessed it; FY2026 carries `(309) 921-5074 Ext: 101` in A, B and D, **every one of them Smith**, against `(309) 645-0963` in C beside a gmail address. So the unit did not lose a co-signer with an unchanged value, as Reddick Fire did — **it filed a DIFFERENT telephone and the new one has one witness.** That makes carrying the old number forward worse than dropping it: it would publish a number the unit's own current filing has replaced. Adam's preserve ruling does not reach it, because the host served fine and the publisher gave new information rather than refusing a read. **Wanted: the phone-change shape recorded in `witnessed()`'s docstring beside Reddick's**, so the next reader does not read every phone loss as who-signed drift. Worth measuring in the same pass: the FY2026 value carries `Ext: 101`, which the parser strips at `Ext` — an extension is evidence the line is an institution's switchboard rather than a person's, and whether that should count toward witnessing is an open question, **not** a licence to relax the two-surname rule. Retention could not see this: one record in a pooled file is below every threshold. **CLOSED 2026-09-22 by #1077 (`5afb289`), and my framing above was the looser one.** This row said "a second loss shape"; the session measured that **the filer slots are IDENTICAL in both years** — Smith / Smith / Weddle / Smith — which I had read myself when merging #1076 and did not notice mattered. So the two cases are exact OPPOSITES rather than merely different, and a reader of a future phone loss can tell them apart from the slots alone. The extension question resolved for the current behaviour with nothing relaxed: stripping at `Ext` can only ever CREATE a match, never break one, and a match it creates is two surnames at different extensions of one base number — stronger switchboard evidence than an identical full number, which is what the rule is trying to establish. Confirmed independently before merging: 492 shipped phones across the eight district-officials files with 0 extensions (exactly as claimed), and 509 districts in `afr-special-districts.json`, which does NOT contain Metamora — so the 40-unit sample can honestly report zero extensions while the documented case files one. The keeper for the next person is the FY trap: asking every unit for the current year returned an empty contact block for 46 of 60, which reads exactly like "files nothing" and means "not that year"; 28 of the 37 read were on FY2025. |
| **#1025 and #1028 collide with no git conflict — merge order matters** | **closed — merged in the planned order** | 2026-09-19 | Found by this session and verified by the manager on both branches. #1025's `ACCEPTED_NAMES` excuses Bartonville's `’s Email: clerk@bartonville.org`; #1028 deletes exactly that value; different files, so git reports nothing. Either order leaves main failing `validate_officeholder_names.py` on "stale, remove it". Order: **#1028 first, then drop the Bartonville entry from #1025 before it merges.** The edit is NYC/SF's to make — routed to them 2026-09-19. Illinois offered and correctly did not touch another session's branch. |
| Bartonville's phantom Clerk (#1028) | **merged** `d450c52`, before #1025 `a3d11c0` as planned | 2026-09-19 | Fixed the parse first, then widened the guard. One fabricated name off the municipality card. |
| Six roster workflows: shared pages after the branch cut (#1030) | **merged** `5338913` | 2026-09-19 | Stops weekly jobs dying when another workflow merges mid-crawl, and deepens the checkout so sitemap dates are real. |
| **Will County: move it from `REQUIRED_COUNTIES` into `PRESERVABLE`** (#982, #996, #1026) | **merged** #1043 `851bb01`, proved by a dispatched run rather than by the diff | 2026-09-19 | Adam's ruling, 2026-09-19: "Add will county to the exception list so the remaining workflow can continue." The block itself is unchanged and is never worked around — what changes is that it stops withholding 36 other counties' turnover. Two edits: the `PRESERVABLE` entry, and the workflow's build step, which gates on `scrape_will.outcome == 'success'` and so never runs. Cook stays required. The cost is real and gets stated rather than smoothed: a preserved full-body county means a Will council member who changes stays stale, and no count floor notices. Ask 28 stays drafted and unsent. |
| **L2 publishes a library's OWN NAME where its director goes, and #1062 would ship it — DO FIRST** | **CLOSED by #1066 `8d54ec4`; MY ROW WAS FOUR DAYS STALE** | 2026-09-21 | The weekly library-contacts PR replaces Atkinson Public Library District's `admin.name` `Ninette Carton` with **`Atkinson Public Library`**, role Director. MEASURED against the live source, robots read first with this repo's reader as `districtry/1.0` (allowed, no delay): `librarylearning.org/atkinson-public-library-district` carries `Name: Atkinson Public Library`, `Title: Director`, and `Ninette` appears zero times. **The scraper is faithful and the value is still unshippable** — the card would name an institution as the person who runs it, and would do so by removing a real name that ships today. `il-library-district-officials.json` has no `heads` for Atkinson, so nothing else fills that slot. **Neither guard can see it:** the name gate judges shape and this string is well formed, and the retention gate measures per source, where one record of 250 is below every threshold. Wanted: a builder guard that refuses an L2 administrator whose name matches the library's own record key, or is a prefix or suffix of it, ships that record with no administrator, and prints it every run. The other four changes in #1062 are correct and were each checked against the source — Rick Warren's vanishing `admin` is the builder working, because #1057 gave its filing a `heads` entry naming the same person, so the card still names her from the filing. **RETIRED 2026-09-25 and the delay was mine.** The fix shipped as #1066 (`8d54ec4`) and #1062 was CLOSED unmerged on 2026-09-21, so this row read "open, PR held, DO FIRST" for four days on finished work. Verified on main: `institution_name_finding()` refuses an exact match, a prefix and a suffix, requires TWO TOKENS so a director surnamed for their town is not refused, DROPS the administrator and ships the record rather than failing the build, prints every drop, and carries `INSTITUTION_SELFTEST` with the value L2 actually served plus the false positives the rule was narrowed against. That is the right shape: the wrong direction costs one empty slot rather than a wrong name on a card. **A stale DO FIRST row is worse than no row** — it would have sent this session to redo merged work, and it is the same defect I recorded twice this week about briefing from a board row instead of the tree. |
| **Plattville's Clerk ships as `Beth Fals 56` — DO FIRST** | **CLOSED by #1067 `a981ff6`; MY ROW WAS FOUR DAYS STALE** | 2026-08-01 | **Corrected 2026-09-19:** this board first said the value was held in `ACCEPTED_NAMES`. It is not — that table arrives with #1025 and is not on main, so the name is simply shipping and has been since 2026-08-01. Must be **dropped, not repaired** to `Beth Fals` — the Douglas County rule. **RETIRED 2026-09-25, same failure as the row above.** `a981ff6` (#1067) is on main and the shipped record proves it: Village of Plattville now carries a President (June McCord, 2023), an office address and a phone, and NO clerk — the page-number fragment was dropped rather than shipped, which is the honest outcome. Mine to have retired on the 22nd. |
| The library-contacts refresh has not produced a clean file yet — **my dispatch failed, and I reported it as done** | **closed — run 7 succeeded, #1079 merged `a482013`** | 2026-09-22 | **The reader is FINE and that is the first thing to say:** `il-library-contacts.json` on main is the 2026-09-15 build, Atkinson's Director still reads **Ninette Carton**, and a fleet-wide check finds **0 of the libraries naming themselves as their own administrator**. The bad L2 value never shipped. What did not happen is the clean rebuild through #1066's guard. My 19:23 UTC dispatch (run 6) **failed after 80 seconds** on `ConnectTimeout` to `librarylearning.org` on the FIRST listing request — before any parse, so the guard was never reached and is not implicated — and I told Adam I had re-dispatched without reading the outcome. Diagnosed 2026-09-22: the host is up, robots read first as the scraper's own client `districtry/1.0` (allowed, no delay stated), `GET /directory?type=124&page=0` → **200, 78,377 bytes in 3.7 s**. So it is this runner's route on that minute, not the source. Re-dispatched once — the one retry a pre-parse network failure earns. **CLOSED 2026-09-22: run 7 ran the full 27-minute crawl and #1079 is merged.** Every one of its five changes was read at the live source before merging. A reader GAINS two things — Tri-City Public Library District (Buffalo) names a Director for the first time (Vanessa Robnett; its filing carries no head, so L2 was the only possible source), and Illinois Prairie District Public Library regains a telephone. Atkinson correctly names NOBODY: L2 still publishes `Name: Atkinson Public Library / Title: Director`, verified live, so the guard leaves the slot empty — the cost #1066 priced on purpose. Rick Warren lost a DUPLICATE only; Elaina Holland is in the filings file as Librarian and the card still names her, which is the de-duplication rule rather than the new guard. Tilden's new number is what L2 publishes today and L2 is its sole publisher. |
| **One library, two names across our own files — and the Woodford card is the one without the phone** | **name half CLOSED #1080 `7e5b1ee`; phone half open** | 2026-09-22 | Surfaced by #1079 and it is mine to own, because I misnamed this library in five places tonight before catching it. **Unit `102/010/10` is called `IL Prairie Library District` in `woodford-district-officials.json` and `Illinois Prairie District Public Library` in both `il-library-district-officials.json` and `il-library-contacts.json`** — same comptroller code, same `PO Box 770 / Metamora IL 61548`, same head `Dawn Smith`. There is no "Metamora Public Library District" anywhere in the repo; I read #1076's diff hunk, which showed the code, the office and the head but NOT the key, and supplied the name from the town. Corrected on the row above. **The reader-facing consequence is real:** after #1079 the statewide library card carries `(309) 921-5074` from L2 while the Woodford library card carries no phone at all, for the same library under a different name — so which answer a reader gets depends on which layer they toggle. Wanted: establish which name the county's own `woodford-library-districts.json` boundary uses (the Woodford scraper joins on the boundary file's string by design, so the name may be the county's and correct), then decide whether the two surfaces should agree and whether the Woodford card should take the phone from the directory the way the statewide card does. **Do not rename a boundary to match a roster without checking which publisher says what.** **ANSWERED 2026-09-22 and the answer is better than my question.** BOTH NAMES ARE THEIR PUBLISHER'S OWN and neither file moves: Woodford County's parcel fabric calls it `IL Prairie Library District` under code `LYIL` — which I confirmed in `woodford-library-districts.json`, one of six features — and the state directory and the AFR filing call it `Illinois Prairie District Public Library`. I framed this as two of our files disagreeing; it is two publishers naming one body, and renaming either would substitute one publisher's name for another's. #1080 retires the invented name from `witnessed()` and adds the rule that generalises: **cite a unit by its comptroller code, the one identifier both publishers share.** **THE PHONE HALF STAYS OPEN and the session was right not to close it.** Measured across the parcel-fabric counties: 26 county library cards, 4 lacking a phone a statewide surface has, and in all four the number is L2's while the AFR column is empty on BOTH surfaces — so the AFR route is consistent with itself and the difference is that the county-roster path does not read L2 at all. That is a missing source on one path, not two surfaces contradicting each other. Recommended: read L2 on those cards, labelled as the state directory's, on the `build_county_board_offices` precedent. The session states what it did not verify and stopped there, which is correct. |
| **#1076's answer improved without any rule being relaxed — two publishers now name that number** | **closed 2026-09-22, informational** | 2026-09-22 | Recorded because it is the good outcome and the reasoning is worth keeping. #1076 withheld this unit's new telephone because its own AFR could not witness it (three Smith slots against Weddle's own). L2 publishes `309-921-5074` for the same library — confirmed live 2026-09-22 — which is the base number the filing carried as `Ext: 101`, from a SECOND and INDEPENDENT publisher. So the reader gets the number because another source names it, never because the two-surname rule was bent. That is the shape to reach for when a witness rule withholds something true: find another publisher, do not lower the bar. |
| General Assembly roster is stale | **CLOSED 2026-09-25 — and the row's own test was the wrong one** | 2026-09-19 | Raised by this session; the manager had it nowhere. Measured on main: `il-house-members.json` last moved 2026-09-08, `il-senate-members.json` 2026-09-02. Its workflow failed on 09-14 and was fixed on 09-18, so the next scheduled run is the first test. Reader-facing — these are the people on the state House and Senate cards. **MEASURED 2026-09-25 and the premise does not hold.** `update-ilga-roster.yml` run 15 ran on 2026-09-21 and SUCCEEDED, after run 14 failed on 09-14 — so the first test this row was waiting for happened and passed. `il-house-members.json` moved that day and holds 118. **`il-senate-members.json` still reads 2026-09-02 and that is not staleness**: it holds 59, which is the whole Illinois Senate, and a roster that has not changed produces no commit. **A FILE'S LAST-COMMIT DATE IS NOT ITS LAST-VERIFIED DATE**, and this row used one as evidence of the other — the same confusion that makes the fleet carry per-source read stamps rather than one instance-wide verified date. The check that answers the question is whether the JOB ran and succeeded, which it did. |
| Logan County's 11 municipalities and 65 officials are frozen | blocked | — | The county's own robots.txt disallows the directory the Clerk's yearbook sits under. That is the host's answer. |
| 2 of 64 districted board cards name no office | open | 2026-09-15 | Down from 50 on 2026-09-06. The long tail. |

## Status — this session owns this section

**2026-09-28, LATE. #1248 MERGED (`0483e6b`) AND THE DISPATCHED RUN IS THE WITNESS
IT WAS OPENED FOR.** Main's own smoke run on the merge is green (36493131266,
22:33:53 to 22:47:43), read from the run rather than inferred, because merging
auto-unsubscribed this session. `update-il-special-district-officials` run 6,
dispatched at 22:34, then did what run 5 could not: its scrape step ran **22m53s
against run 5's twelve seconds**, and every later step RAN where run 5 skipped
them — rebuild, validate, check for changes, open pull request. **That posture is
the point rather than the conclusion**: this workflow forgives a step, so a green
run is not evidence it did its work, and the step timings are.

**THE ABORT HAD A MEASURABLE COST, WHICH THE RUN NOW NAMES.** #1250 carries one
added record and ten changed, in Macon, Adams, Cook (three park districts),
Iroquois, McHenry, Monroe, Rock Island and St. Clair (two) — eleven bodies whose
officers, office or contact details moved and would have sat a week stale. It is
an ordinary roster PR and waits on review like any other.

**WHETHER THE LADDER ITSELF FIRED IN THAT RUN IS NOT ESTABLISHED.** The log tail I
could read starts after the scrape, so I cannot say whether any
`RATE LIMITED: … re-asking in Ns` line appeared, and I am not implying either way.
What the run proves is that the sweep completes end to end with the new path in
place; the ladder's behaviour is proven by its selftest and by the stubbed and live
runs recorded on the PR.

**THE CHANGE I FIRST WROTE WAS A FORK, AND THAT IS THE FINDING WORTH KEEPING.** My
first commit put the rate-limit reading in `scraper_common`. `scripts/arcgis_error.py`
has owned "what is an ArcGIS error" since 2026-09-08; it is one of the five modules
`validate_workflow_deps.FLEET_SHARED` names, and the comment there states the test
my own commit failed — "What an ArcGIS error IS must not be answered differently
per instance". Mine was a second answer in the same tree, and it disagreed with the
first about what a rate limit is. **`is_rate_limit` had asked the code alone**, and
that cannot be relied on for either rate limit this project has met: neither caller
recorded a code, Logan's 2026-09-08 wording carries no "too many requests" and
Hamilton's carries no "quota". Both signals are read now, each wording quoted from
the run that produced it, and the module has a `--selftest` in CI for the first
time — the pair moved 94/123 to 95/124, re-measured, superseded pair recorded.

**AND NOTHING GATES THE FORK.** FLEET_SHARED is prose; no check fails when a new
caller reads `payload["error"]` itself. The scraper was created three days AFTER
the module and grew its own read the same day, so that module's survey was complete
when it was made and the fork arrived past it. A candidate list of other files in
the same shape is recorded in `arcgis_error.py` — explicitly a list to read one by
one, never a count, because the sweep that finds them also matches error members
with nothing to do with ArcGIS.

**ONE TOOL READING IS WORTH RECORDING BEFORE IT COSTS SOMEBODY AN HOUR.** The same
filtered `actions_list` query answered `total_count: 346` with rows from 2026-09-06
once, between two calls that answered `1768` with current rows — same parameters
each time, so it is neither `minimal_output` nor `perPage`. A single reading of that
endpoint can be stale and the small total is the only tell. Reading a run by its own
id sidesteps it.

**2026-09-28, LATER. #1243 MERGED (`38661f2`) AND MAIN IS GREEN ON IT** — read
from the run (36428918433, success 13:28:56 to 13:41:04 UTC) rather than inferred
from the merge, because merging auto-unsubscribed this session and a red main
would surface to nobody. The check-ins are stopped.

**THEN CHECKING A PASSIVE WITNESS FOUND A FAILURE THAT WAS ON NO LIST — #1248
up.** The witness I was looking for is not one: `update-il-special-district-
officials` is one of seven jobs carrying #1227's comma guard, and the Sunday
statewide-library run fired 2026-09-27 16:46 UTC while #1227 merged at 18:26, so
it PREDATES the fix by 1h40m and Walnut's warning is next Sunday's run, not last
week's. What the look turned up instead is that
`update-il-special-district-officials` run 5 FAILED today at 19:31 UTC, twelve
seconds in, on an ArcGIS rate limit — `Unable to perform query. Too many
requests.` from services.arcgis.com, reading Hamilton's fire districts — and
`service_names` had no retry of any kind, so a 486-unit weekly refresh ended on
one host asking to be asked later. Nothing had refused us and nothing had changed
shape; the shipped file simply keeps last week's read.

**IT WAS TRANSIENT AND THAT IS MEASURED, NOT ASSUMED**: one request to the same
query 1h50m later answered HTTP 200 in 0.66s with all three of the county's
districts. Whether our own pacing provoked it is NOT established and is not
guessed at.

**THE FIX IS THE DISTINCTION THE REPO ALREADY DRAWS IN WORDS.**
`check_roster_retention.py` says a source that stops publishing is a real event
and one that failed to fetch once is not; this scraper's own docstring is right
that an erroring service must fail the run, and a rate limit is not an erroring
service. So `scraper_common` gains the reading and a bounded ladder beside
`fetch()`'s own 429 rule — 5s, 15s, 45s, each re-ask reported so a run that only
just got through says so — with EVERY OTHER ENVELOPE still failing on the first
answer and an outlasting limit failing too. A 5xx is deliberately not retried
although `fetch()` retries one, because it has not been the observed condition
here. **No gate was added and the pair is unmoved at 94/123**: the ladder went
where `scraper_common.py --selftest` already runs in CI, because a classifier
being right says nothing about its call site and this ladder only ever runs in the
rare condition it exists for — a defect in it would surface weeks later in a job
nobody watches. 22 assertions, red on each of five deliberate breaks.

**TWO HAND-TYPED FIGURES BESIDE THE TABLE THAT OWNS THEM WERE FALSE, AND THEY ARE
WHY THE PACING WAS BELIEVED SAFE.** `SERVICE_PACE` said "nineteen different hosts,
so the pacing is per host in practice"; counted off `BOUNDARIES` it is 18
service-backed pairs across EIGHT hosts, 8 of them on one. The workflow header
said "ten and nineteen" of its 29 pairs where it is 11 and 18 — one out in each
direction, which is exactly why the right total let it sit — and seventeen
services for the same 18. **AND I TYPED TWO WRONG FIGURES WHILE CORRECTING WRONG
FIGURES**: "five more" for the sibling hosts where the table holds seven, and
nineteen assertions where the diff holds twenty-two. Both caught by counting. The
class is not somebody else's habit; it is any figure typed instead of counted,
including in the sentence fixing one.

**THE MANAGER'S REPORT WAS RIGHT ABOUT WHAT IT READ.** Their 21:16 entry records
#387 closed with none of 128 roster workflows failing; `roster-health`'s most
recent run was 01:17 UTC, eighteen hours before this failure, so nothing they
could have read would have shown it. Tonight's run will, and correctly — the run
did fail.

**What I owe on this:** the live witness is a dispatched run of that workflow once
#1248 is on main, which both proves the ladder against the real services and
performs the week's refresh that the abort skipped.

**2026-09-28. #1242 MERGED (`c54d910`), AND THE WAIT ON IT TURNED UP THE SAME
DEFECT IN MY OWN PROSE — #1243 up.** Checking my open question on the precinct
tripwire, I found `WATCH.md` answering how much of the fleet a publisher-side
replacement would reach with "the three results vendors, which carry 34, 13 and
17 counties". **Two of those three were already stale when I wrote that sentence
on 2026-09-25**: the guidebook's platforms table had said 23 for platinum and
"14 carrying content" for GBS since 2026-09-01, three weeks earlier. Same class
as the Peoria docstring I had just fixed, in my own hand, and understating the
route — the direction that changes a decision, since the paragraph exists to
answer whether the smaller tripwire is worth building.

**SO THE VENDORS' TOTALS ARE REPLACED BY THE INTERSECTION THAT DECIDES IT.** Of
the 46 counties shipping a `*-precincts.json` layer, 26 have a publisher this
repository can name — platinum 10, GBS-carrying 7, the pollresults pair 9 with
Hardin shared, Hancock's own database 1 — and **Clarity carries ZERO**, so the
publisher my sentence omitted is the one with nothing to contribute and the three
it named were the right three. **Twenty counties would still have no detector of
any kind and are now named**, two of them measured shut (Henderson against all
five publishers, Menard against the vendor pair and GBS) and eighteen untested.
The 26 is stated as a FLOOR, because the pollresults membership is enumerated
nowhere here.

**AND IT CANNOT BE RAISED BY GREP, WHICH I TRIED FIRST AND WHICH OVER-COUNTS BY
40%.** The tree names 20 county slugs on that vendor pair and 8 record a probe
that FAILED — a county whose route was measured shut gets the URL written into
the record as the thing tested, so the literal IS the negative. Washington is the
one that also defeats a status check: `il-washington.pollresults.net` answers 200
with a page that is not Washington's, which is why the control is a fabricated
county name and a body hash.

**THREE THINGS I CHECKED ON MYSELF RATHER THAN SHIPPING.** I verified all three
publisher lists as exact transcriptions of the guidebook's table instead of
trusting my typing (23/23, 14/14, 12/12, no difference either way). I cut a
clause claiming Clarity's twelve are "the large ones" — measured, ten are in the
state's twenty most populous while Vermilion is 21st and Macoupin 32nd, so size
is a loose correlate and not the explanation, and the cause is not established.
And I restored the old paragraph's "it is not built", which my replacement had
left implied: dropping a true statement while correcting a false one is still a
regression.

**NO SCRIPT SHIPS, deliberately.** I argued myself into a generator twice and out
of it twice: the figures are a dated measurement whose inputs the paragraph
names, and a generator would add a second hand-kept carriage table nothing
re-audits — the shape this change removes.

Gates: battery 0 of 113, enumerated through `validate_steward_mirror.invocations`
rather than a pattern of my own, with the seven gates that read this file re-run
after the last edit. **The pair moved under me while I worked and CLAUDE.md had
kept up**: another session took it to 94/123 and `validate_gate_counts.py` agrees,
so my change adds no gate and moves nothing.

**TWO MECHANICS RECONFIRMED, both already on this board.** The merge deleted the
remote branch, so `--force-with-lease` answered "stale info" with nothing to lease
against — established by `git ls-remote` rather than assumed, then a plain push
created it fresh. And main moved twice while I pushed, so mergeability was tested
against its new tip before opening the PR, a conflicted PR being the one that gets
no CI run.

**The manager verified #1242 and merged it, and their address scan was WIDER than
mine**: 3 of 2,299 address fields against my 3 of 1,038. Mine is scoped to the
AFR-derived files and says so, so both hold; theirs is the stronger witness for
the same conclusion.


**2026-09-28. THE PEORIA DOCSTRING IS CORRECTED, AND THE LIST IS DERIVED RATHER
THAN RE-TYPED — #1242 up.** The #1237 review routed me a false passage in
`scripts/build_peoria_district_officials.py`: it named THREE of eighteen districts
as filing no board officer, and Hanna City Park District now files a President and
a Treasurer, so it ships under `board` and the passage described a filing that no
longer exists. **THAT IS THE SECOND TIME THIS ONE PASSAGE HAS BEEN WRONG, AND THE
TWO ARE WRONG IN OPPOSITE DIRECTIONS** — #818 found it naming two of three. A
hand-kept list that has failed in both directions is not a list to correct; it is a
list to stop keeping.

So `counts_line()` is computed once from the reading both paths already do and
printed on the write path and on `--check`, naming the districts with no board
officer beside the four counts, and the docstring points at that line and quotes no
figure. The reason the passage existed is sound — a reader auditing the treatment
should not re-derive the list — which is exactly why naming the wrong districts is
worse than naming none: it is consulted instead of the data.

**THE FLOOR COMMENT ABOVE IT CARRIED ITS OWN STALE QUADRUPLE and nobody had
noticed**: `18 / 28 / 9 / 16`, measured 2026-09-10, against the `18 / 30 / 7 / 16`
the shipped file has carried since #1237's refresh wrote it at 23:31:49 UTC
yesterday — two officers crossing from appointed to board when Hanna City began
filing board titles, every floor still clear. Recorded under its correction and
pointed at the printed line. The property that comment used to assert is
self-enforcing anyway: a floor raised above the measurement refuses on its very
next run.

**MY READING AGREES WITH AN INDEPENDENT ONE, which is why I did not re-scrape.**
The manager re-ran the workflow's own scraper and builder against the live
Comptroller while reviewing #1237 and got a file identical apart from the
timestamp; the shipped file I read prints 18 / 30 / 7 / 16 with exactly
ALPHA PARK LBRY DIST and PLEASURE DRIVEWY PKD unnamed. Two readings, one answer.

**AND THE LOWERCASE `n` IN "511 n Main Street" IS THE FILER'S OWN TEXT.** It reads
like a shared casing function having lowercased a directional, which this project
has paid for once in `title_case`. Measured: no code here changes an address's case
— the lowercasing in `comptroller_afr` is comparison keys, `norm`, the suffix test,
an e-mail domain — and across 1,038 addresses in the AFR-derived files exactly
THREE carry a lone lowercase directional, two of them a different unit in a
different file. A casing function would have hit far more than 3 of 1,038 and would
have lowercased "3527 S Airport Rd" in a neighbouring record. Recorded in the
scraper and not corrected: an address is the filer's.

Verified: `--check` round-trips against a fresh read of the filings, the write path
prints the same line and writes a byte-identical file, a thinned payload still
refuses at `10 board officer(s) < floor 20`, and the weekly workflow does not parse
this stdout — its change detection is `git diff --quiet -- il/data/app/` — so
reshaping the line breaks nothing. No-browser battery green, 0 of 112.

**TWO THINGS OWED BY MY LAST ENTRY ARE CLOSED.** Main's own run on `8b74239`
(#1239) is run 36362894318, conclusion success — and since that assertion can no
longer pass vacuously, a green run is now itself evidence it measured. And the gate
pair is consistent despite #1240 merging on top of it while stating `92/121`: that
figure was correct against its own base, which predated the QR gate, and #1240 added
no step, so the merged tree measures 93 / 122 and `CLAUDE.md` already says so —
`validate_gate_counts.py` green. Not the silent-merge half of the hazard; the one
case where the two numbers differ and neither is wrong.


**2026-09-28. #1239 MERGED — AND MY CLAIM ABOUT #1238 IN THE ENTRY BELOW WAS
WRONG.** Both merged 34 seconds apart, mine at 00:37:24 UTC (`8b74239`) and SF's
at 00:37:58 (`90a7fc2`), about 28 minutes after I wrote `2edc55e`. That entry says
"#1238 closed something adjacent and not this assertion" and "the two copies do
not yet agree". **#1238 fixed exactly this assertion**, and the copies now agree.

**MY MEASUREMENT WAS RIGHT AND MY INFERENCE WAS WRONG, which is the harder
failure to see.** At main's `04d9d6d` (23:41 UTC) `ca/scripts/smoke_test.mjs:454`
genuinely still carried the short-circuit — because #1238 had not merged yet. What
I did with that is the error: I read a board commit titled "closed the SF
theme-repaint decision #1234 handed me (#1238)", saw the file unchanged, and
concluded what that PR DOES. The available reading was "that pull request is open
and I have not read its diff." **THIS IS THE THIRD TIME TODAY I DREW A CONCLUSION
A PARTIAL READER COULD NOT SUPPORT** — the job log's tail, the symmetric
`git diff`, and now a PR's effect inferred from its absence. The common shape is
using what I could see as though it bounded what exists.

**AND I READ THEIR CODE RATHER THAN THEIR COMMIT MESSAGE, which changed the
answer again.** Their message says the read is waited for; had I taken my own
first guess I would have written that theirs is a single truthy read. It is not:
`overlayReady()` waits through `page.waitForFunction` for a truthy string colour,
bounded by `QUERY_TIMEOUT`, before BOTH reads. So both copies now wait to the same
bound, both fail on an unmeasurable read, and both dropped the `#map path`
fallback. The contract Wisconsin asked us to keep in step is in step.

**ONE ASYMMETRY REMAINS AND IT IS THEIRS TO WEIGH, NOT MINE TO CHANGE.** Their
dark-side wait is for NON-NULL; mine is for a value that DIFFERS from the light
one. A non-null wait can succeed on the instant the colour exists but before the
repaint lands, read the light colour back, and report `#8E2A22 -> #8E2A22` — a
false "unchanged by the flip" indistinguishable from a real no-repaint. In
practice it is ample headroom: Illinois's repaint lands 2-81 ms after the flip
against a 600 ms settle, and theirs has passed 5 of 5. Recorded for `ca/`'s owner
rather than edited, which is the same boundary I held all the way through.

Gates on the merged tree: `validate_gate_counts.py` 93 / 122 — UNMOVED, as
predicted, because this change added no gate — `validate_steward_mirror.py` 122
for 122, `generate_metro_files.py --check` across 117 regions, `validate_index.py`,
and `node --check` on both copies. Main's own run on `8b74239` was still in
progress at 00:40 and is the one thing still owed.


**2026-09-28. #1239 IS GREEN ON THE ONE CONDITION I COULD NOT TEST LOCALLY, AND
THERE ARE TWO COPIES OF THAT CHECK RATHER THAN THREE.** The theme check now fails
when it reads no colour, and the run that mattered is CI's, because a local boot
has MapLibre vendored and the PMTiles archive same-origin while a cold runner
fetches both — which is exactly where a 25 s bound could have been tight. Read
out of the `smoke` job's own log, Illinois's line at 23:57:43 prints
`#2E8C6A -> #62DAAC`, the same pair as locally. **Since the assertion can no
longer pass vacuously, a green run is now itself evidence that it measured**,
which is the whole property being added.

**READING THAT LOG TOOK THREE GOES AND THE FIRST TWO WERE MY OWN ERROR IN THE
SAME SHAPE THIS FILE KEEPS RECORDING.** `tail_lines: 400` gave me the END of a
six-instance job, so the only overlay line in it was `#8E2A22 -> #F97061` — which
is SAN FRANCISCO'S, the pair Wisconsin's report quotes for `ca/`. I had Illinois's
green conclusion and a colour from another instance, and nearly wrote the second
as the first. What settled it was not my instance-attribution heuristic, which
mislabels every line after the first match; it was the COLOURS, against a
measurement I already had. **A tail is not a search, and a plausible line from a
reader that cannot see the whole thing is the absence-of-evidence trap one level
in.**

**AND ONE OF MY OWN CLAIMS WAS WRONG ABOUT THE TREE.** The PR said "`ca/` and
`ny/` carry their own copies". Measured across all six instances, the assertion
exists in exactly TWO files — `scripts/smoke_test.mjs` and
`ca/scripts/smoke_test.mjs`; `ny/`, `wi/`, `ia/` and `mi/` carry no
`repaints a live overlay` check and no `overlayColor` reference at all, which is
also why only two overlay lines appear in the whole browser run. So Wisconsin's
"the two copies" was exact and my reading of it was loose. **The two do NOT yet
agree**: as of main's `04d9d6d`, `ca/scripts/smoke_test.mjs:454` still carries the
null short-circuit, so #1238 closed something adjacent and not this assertion.
That instance is another session's remit and #1239 does not touch it — recorded
rather than acted on, since keeping the pair in step was the reporting session's
stated reason for handing the decision here in the first place.

Also checked rather than assumed: main's four-commit lead is board files only and
does not touch `scripts/smoke_test.mjs`, so the clean merge is semantically clean
too — and asking `git diff HEAD origin/main -- <file>` answers that question
WRONG, because it is symmetric and returns my own change; the directional read is
against the merge base.


**2026-09-27, LATE. #1239 IS UP: THE THEME CHECK NOW FAILS WHEN IT READS NO
COLOUR.** Wisconsin handed me a finding in my own `scripts/smoke_test.mjs` and
deliberately did not fix it, because what to do on a null is a statement about
what the theme-repaint contract is. The assertion was
`light.stroke === null || dark.stroke === null || light.stroke !== dark.stroke`,
so a run where the anchor's overlay had not painted passed without comparing
anything.

**MEASURED FIRST, AND IT IS LATENT RATHER THAN LIVE**: over five boots Illinois
reads `#2E8C6A -> #62DAAC` at the current 400 ms settle, 5 of 5, so this check
has been doing its job here and no reader or gate was affected — what was wrong
is that it could not fail when it learned nothing. `overlayColor` returns null
three ways (no overlay yet, a tile layer whose GL line layer is not built, a
Leaflet path with no colour), all of them a failure to measure. Each side is
polled to `QUERY_TIMEOUT` now and a side that never answers FAILS naming which;
the dark poll waits for a value that DIFFERS, because waiting only for non-null
samples the race and reads the light colour straight back. Measured, light first
answers at 6-302 ms and the repaint lands 2-81 ms after the flip, so the 25 s
bound is slack and only ever paid on a failing run. Four negative tests, each
confirmed, including the null case that used to pass.

**TWO THINGS TURNED UP THAT THE ASSIGNMENT DID NOT NAME.** The `#map path`
fallback can never fire — `overlayColor` is in all six instances' shipped
`index.html`, measured — while reading that selector is exactly what made ca/'s
copy measure the scope mask instead of a district, so it is deleted rather than
left looking like a safety net. And this script is one `try`/`finally` with NO
catch, so a throwing read would have exited with a stack instead of naming a
check, on a poll that asks the page up to 500 times where the old code asked
twice; it now fails this check and carries the exception.

**A DELETED BRANCH IS NOT A STALE LEASE, AND `git push | tail` HID THE
REJECTION.** #1227's squash merge deleted `claude/il-backlog-plan-9o2ew4`
remotely, so `--force-with-lease` answered "stale info" — there was nothing to
lease against — and a plain push was what was wanted. My retry loop piped the
push through `tail`, which made the pipeline succeed and printed PUSHED over a
rejected push; the same exit-code-masking class as the `&&`-chain trap recorded
this morning. The guidance about restarting a merged branch covers the history
and not the case where the branch is gone.

One thing that is NOT a tree failure: the first battery run failed
`validate_qr_code.py` on `No module named 'qrcode'`. It is a declared dependency
(`scripts/requirements.txt:146`) that CI installs for that step and this sandbox
lacked; installed, it passes, so the battery is 112 of 112.


**2026-09-27. #1227 MERGED as `e4e59da`, #1226 CLOSED UNMERGED a minute later,
AND THE GATE PAIR HELD ACROSS THE MERGE.** Verified on the merged tree rather
than on the envelope: the roster carries `Jaclyn G. Trujillo` under Walnut's 2026
filing, `il/library-district.html` carries that spelling twice and the corrupted
form zero times, and eight gates pass — `comptroller_afr.py --selftest` (the one
that ran nowhere until today), `validate_index.py`, `build_officeholder_tables.py
--check` at 3,773 officeholders in the served bytes, `validate_structured_data.py`,
`build_concept_pages.py --check`, `build_sitemap.py --check`, and both readers of
the battery: `validate_gate_counts.py` at **92 / 121 after the merge** and
`validate_steward_mirror.py` at 121 for 121. That last pair is the check CLAUDE.md
asks for after any merge rather than after an edit, and this is the merge it was
written about — my branch and main each moved today.

**IT WAS SQUASHED, so `494addf` is not an ancestor of main and that is correct
rather than a problem** — the content is all in `e4e59da`, which is what I checked.
Worth knowing because `git merge-base --is-ancestor` on a squash-merged branch
answers NO, and that reads like a failed merge if you take it for one.

**TOMORROW'S RUN IS NOW A LIVE WITNESS AND HERE IS WHAT IT SHOULD SAY.**
`update-il-library-district-officials.yml` fires Sunday 12:00 UTC (in practice
15:00-17:00) and re-scrapes through the fixed parser. It should print exactly one
line — Walnut's, naming both spellings — and open NO pull request, because the
shipped file already carries all three 2026 filings and the corrected name, so
nothing can have moved. A pull request from it, or a second warning, or no warning
at all, each means something different and all three are worth reading.


**2026-09-27, LATER. #1227 IS UP WITH THE REFRESHED ROSTER, AND #1226 CAN BE
CLOSED — YOUR CALL, AND I HAVE NOT PUSHED TO THE BOT BRANCH.** The live 378-unit
re-scrape read through the fixed parser fired the normalisation **exactly once
across all 198 filings**, printing it: `Walnut - a Public Library District in
Bureau County: filed name 'Jaclyn G, Trujillo' carries a comma after the middle
initial; shipped as 'Jaclyn G. Trujillo'`. Its diff is four lines in one file —
the `generated` stamp and three `filedFor` 2025 → 2026 bumps, for Cissna Park,
Neoga and Walnut. **The same three genuine filings #1226 found, with no name
moved.**

**THE SUPERSESSION IS MEASURED RATHER THAN ASSERTED, AND MEASURING IT FOUND THE
BLAST RADIUS WAS TWICE WHAT I HAD WRITTEN DOWN.** #1226's diff is fourteen lines
across three files against my four across one, so I read its file list instead of
assuming the difference was the name alone. Its extra ten are the corrupted name
in the roster, **the same name TWICE on `il/library-district.html` — the
officeholder table row and the `ld+json` graph** — and `sitemap.xml` `lastmod`
churn from having run on a different day. I had been describing this as one card;
a reader would have met the typo in two places on a served page as well. Because
the shipped name does not move here, the page and the sitemap are owed nothing,
and `build_officeholder_tables.py --check`, `validate_structured_data.py` and
`build_sitemap.py --check` say so rather than my saying so.

**AND A BATTERY THAT RAN THROUGH A REBASE IS GREEN FOR THE WRONG REASON.** The
stop hook caught that I had committed both of these as `adam@overberg.co`, so I
re-authored them with `git rebase --exec` — under a battery that was still
running. A rebase checks out each intermediate tree in turn, and two of the
gates in that list read the working tree against a base:
`check_roster_retention.py --base origin/main` is the one that matters here,
because during the window where the tree held the code fix WITHOUT the refreshed
roster it would have compared that roster against an identical copy of itself and
passed, telling me nothing about the change it exists to check. It reported 0 of
111 and I did not trust it; re-run clean on the settled tree it is 0 of 111 again,
which is now worth something. **Re-run the battery after any rebase or merge
underneath it, not only after an edit** — the same reason `validate_gate_counts.py`
exists for the gate pair, one level up: the reading moves when the tree moves
under you, with nothing in any diff to look at.

**GREEN AND MERGEABLE AS OF 18:10 UTC, AND IT IS YOURS TO MERGE.** `smoke` and
`tiles` both succeeded on 494addf, `mergeable_state` reads clean, and there are no
reviews and no review threads; this repository runs no Claude Approvals check on
it. Nothing on that pull request is waiting on me. The branch is not behind in any
way that matters either — main's whole lead over the merge base is my own two
board commits, touching this file alone, and the trial merge is clean, so 92/121
was measured with every other session's work of today already underneath it.

**TOMORROW IS A DEADLINE WITH A FREE WITNESS ATTACHED.**
`update-il-library-district-officials.yml` is crontab'd Sunday 12:00 UTC and runs
the very builder this fixes. Merged before it fires — realistically 15:00-17:00,
since this repo starts scheduled jobs 3 to 5.3 hours late — that run re-scrapes
live through the fixed parser and either moves nothing or moves one name with the
warning printed, which is an end-to-end check nobody has to write. Not merged, it
re-scrapes through the old parser and puts `Jaclyn G, Trujillo` back on the bot
branch, so #1226 returns carrying the same corruption and its next reviewer
re-derives all of the above. **The harm is bounded either way**: that job opens a
pull request and never commits to main, so no reader has seen the typo or will.


**2026-09-27. #1226's CORRUPTED DIRECTOR NAME IS THE COMPTROLLER'S OWN FILING,
AND THAT FILING DISAGREES WITH ITSELF INSIDE ONE DOCUMENT.** The held refresh
would have replaced `Jaclyn G. Trujillo` with `Jaclyn G, Trujillo` on Walnut
Public Library District (006/030/10, Bureau County, Director). Read from the
primary source through this repository's own parser, robots.txt first via
`robots_policy` as the token `comptroller_afr` sends (allowed, no crawl delay,
no content signal): **the FY2026 contact table prints the forename cell three
times and does not agree with itself — `Jaclyn G,` in slots A and C, `Jaclyn G.`
in slot D.** FY2025 printed a THIRD spelling in that same slot D, `Jaclyn G`
with no punctuation at all. So the parse did not introduce it; one person has
been filed three ways across two filings, and both years were read through the
same code, which is what rules the parser out.

**THE OBVIOUS FIX WOULD HAVE SHIPPED THE CORRUPTION.** Voting across the slots
is the first thing anyone reaches for, and the bad spelling holds TWO of the
three populated slots — a majority picks the comma. Nor is "take the slot that
looks right" available: slot D is in `BOARD_ONLY_SLOTS` for the measured
duplicate-trap reasons already in that module, so a head filed there is
deliberately never read, and reopening it to win one character back would
readmit 27 measured duplicates. The Director ships from slot C, a published
slot, which is exactly where the comma is.

**SO IT IS NORMALISED, NARROWLY AND NEVER SILENTLY.** A comma is rewritten only
where it sits immediately after a single capital letter that itself sits between
a given name and a surname, in `comptroller_afr.normalise_filed_name`, with a
warning naming both spellings printed once per correction rather than once per
read — every slot's name is built twice and a unit can file one person three
times, so an unguarded append printed one correction six times. Measured against
the corpus before it was written: of the **1,622 names across the eight
AFR-derived rosters, exactly two carry a comma at all** — `Juan Martinez, Jr.`
and `John Shea, Jr.` — and neither matches the pattern. A surname-first value
(`Auter, Tara`) is left alone too; that is a different defect with its own
remedy in the Vermilion scraper.

**AND THE BUILDER NOW REFUSES WHAT THE NORMALISER CANNOT EXPLAIN**, the way the
count floors refuse rather than write: any comma whose right-hand side is not a
filed suffix stops the write and names the value. Negative-tested three ways on
doctored payloads — the clean payload passes, the comma is refused by name and
reason, and a legitimate `, Jr.` is not.

**THE PARSER'S OWN SELFTEST EXISTED AND RAN NOWHERE**, which is the finding that
outlives this name. `comptroller_afr.py --selftest` has proved
`LOCALITY_CORRECTIONS` in all three directions for weeks and was in no workflow
and in no skill, so eight scrapers import a parser whose proof nobody ran. It is
in CI now with four new checks for the comma, and all six were broken on purpose
to confirm they can fail: disabling the normaliser reds three, making the guard
permissive reds two. The gate pair moved with it and was RE-MEASURED rather than
incremented — the battery is **92 / 121**, well past the 84/113 I last recorded,
because other sessions have been adding gates all day.


**2026-09-26, AFTER #1185. NINETEEN LIBRARY CARDS NAME NO TRUSTEE AND NO GAP
RECORD SAYS SO, and I found it by asking what the corrected record does NOT
cover.** `statewide-library-officials` scopes to the 72 counties dispatching
through `statewideLibraryEntry`. The library layer dispatches 91. The other 19
counties read their own entry, and nothing in the gaps block is about their
trustees: the only record naming any of them for this layer is
`rock-island-andalusia-township-library`, which is one library's extent. This is
the Cass/Greene/Scott/Moultrie shape — an absence with no refusal behind it and
nothing on file to notice it.

**MEASURED, AND MY FIRST PASS WAS WRONG BY THE SAME METHOD-ERROR I HAD JUST
CORRECTED IN THE RECORD.** I joined against the two statewide rosters and got
44 across seven counties. There is a THIRD source: Boone, Grundy, Kankakee,
Peoria and Woodford publish their district officers in their own
`<county>-district-officials.json`, and those name library boards. Joining all
three gives **19 across five counties** — Kendall 9, Macon 4, Rock Island 3,
Stark 2, Woodford 1 — with 22 named from the statewide rosters and 8 from a
county's own file. Reading two of three sources and reporting the difference is
exactly what produced 382, and I did it again inside an hour.

**THE 19 ARE GENUINELY UNMATCHED RATHER THAN MERELY UNJOINABLE**, which mattered
because several are truncated county-GIS labels (`PLANO COMM LIB DIST`,
`OSWEGO LIBRARY DIST`) that looked like a naming problem. Tested by
abbreviation-stripped key and by closest-match: not one joins a board source
under a fuller name, the nearest candidates are unrelated libraries, and only
Wyoming Public has a filing at all — which names no board. **One thing is NOT
established**: Kendall's nine include Aurora, Joliet, Plainfield and Three
Rivers, whose districts are headquartered in Kane and Will and merely reach into
Kendall, so some may be reachable through their home counties rather than being
absent everywhere. That is the first thing a record for this would have to say.


**2026-09-26. #1185 MERGED — `cc1a846`, AND EVERY FIGURE RE-MEASURES ON THE
MERGED TREE.** Through the repository's own reader rather than my earlier
working copy: the denominator 373, named 226, unnamed 147, the `why` split 24
and 123, and 62 counties holding an unnamed library — all six exactly as
shipped. `build_coverage_gaps.py --check` agrees with the guidebook,
`validate_gap_counts.py` reads 13 stated counts agreeing with their files (the
new `self`-on-`counties` declaration among them), and `COUNTY_STATUS.md` names
the gap on exactly 62 rows with Crawford present and none of the seven dropped
counties left. The gate pair re-measures at 84 / 113; nothing merged since the
branch point touched `smoke-test.yml` or the steward skill.

**WHAT IS WORTH CARRYING FORWARD IS NOT THE NUMBER.** Two things outlast it.
The record's own `blocker` said 373 four times and 382 never, so the record
contradicted itself with the false figure in the only field a reader is served —
a maintainer's log agreeing with the measurement while the summary did not is a
shape no gate in this repo can see. And 72 of the 79 boundary files carry
`properties ['library','type']` while seven each use a different key, so a
reader keyed on one spelling returns ZERO names for the rest silently and
without failing, which is why one question produced three answers. Anything
new that reads those files inherits that trap; `shipped_cards` escapes it only
because it reads the 72 statewide counties alone and FAILS on a feature with no
`library` name rather than skipping it.

**THREE OF THE FOUR CORRECTED NUMBERS REMAIN UNGATED AND THE BLOCKER SAYS SO.**
226, 373 and 147 cannot be expressed in the counts grammar — one is a
distinct-name count across 72 files, another a union of subsets of two — and
they move every Monday when `update-il-library-trustees.yml` reads more boards,
which is the `ia-board-chair` shape: a weekly refresh that goes stale precisely
when it succeeds, and that workflow regenerates the officeholder tables, the
concept pages, `about.html` and the sitemap but not this block. The
derive-at-render fix and the grammar widening are both owned elsewhere and
unbuilt, so I built no third mechanism and recorded which numbers a gate holds
and which it does not, because three ungated numbers that look like the gated
one is the failure this record had just demonstrated.


**2026-09-26. THE LIBRARY RECORD'S 382 WAS FALSE, AND THE RECORD'S OWN BLOCKER
SAID SO IN FOUR PLACES.** PR #1185. The statewide route draws 373 libraries, of
which 226 name a board and 147 do not, and the Data gaps panel was telling
readers 382 and 156. Measured through `shipped_cards(statewide_library_counties())`
— the function both library scrapers already share, rather than a key list of my
own — and the manager's three figures all reproduce exactly: 599 features summed
across the 79 boundary files, 416 distinct names across all 79, 373 across the 72
counties dispatched through `statewideLibraryEntry`. 382 is none of them.

**THE ARGUMENT FOR 373 NEEDED A SECOND LEG AND THE MANAGER'S FIRST ONE DOES NOT
CARRY IT.** All 226 named libraries sit inside BOTH candidate populations,
because the 373 are a subset of the 416, so "numerator and denominator are the
same population" is necessary and not sufficient — it is equally true of 416.
What settles it is the record's own `counties` array: every county it listed is
on the statewide route and none is one of the 19 that dispatch their own
per-county file. And no figure phrased as "the layer's N libraries" can be true
offline at all, because twelve further counties on the layer ship no boundary
file and load live.

**TWO CORRECTIONS THE CHECK-IN DID NOT NAME, both the same one-pass measurement
and both reader-facing.** The `counties` array was wrong in BOTH directions:
only 62 counties hold a library that still names no trustee, seven were listed
where every library now names a board, and CRAWFORD was missing while holding
Robinson Public Library District — which files a report naming its director and
no board, so it is present in the officials file with an EMPTY board rather than
absent, the one shape a present-or-absent test reads as answered. That array
drives 68 rows of `COUNTY_STATUS.md`, now 62. And the `why` field's 33 and 123
are the SAME population partitioned, not the different one the check-in
expected: they sum to the stale 156, and of the 147 unnamed, 123 publish a
website and 24 do not.

**WHAT IS GATED IS ONE NUMBER OF FOUR, AND THE BLOCKER SAYS WHICH.** A `counts`
declaration holds the 62 to the length of `counties` through `self`. The 226,
373 and 147 cannot be expressed in that grammar — 373 is a distinct-name count
across 72 files, 226 a union of subsets of two others, where `measured_metric.py`
reads one file's top level — and they move every Monday when the trustees
refresh reads more boards, which is the `ia-board-chair` shape exactly. The fix
is the derive-at-render mechanism already chosen for that record and the
counts-grammar widening approved for Michigan; both are owned elsewhere and
nothing here duplicates them. Leaving three ungated numbers looking like the one
gated number is the failure this record just demonstrated, so the blocker names
which is which.

**ONE NOTE FOR IOWA, NOT ACTED ON.** `ia/scripts/build_ia_gap_outlines.py`
re-stamps `ia-county-internal-points.json`'s `measured` date on every run: it
wrote 2026-09-26 over byte-identical data in the same run that reported "wrote 0
new outline(s)". I reverted it rather than carry another instance's file, but a
re-measured stamp from a run that measured nothing is worth a look by whoever
owns it.


**2026-09-25, evening. #1174 MERGED — `ab1daf8`, AND EVERY FIGURE REPRODUCES ON
THE MERGED TREE.** The three artifacts this change is answerable for, all
green: the new cross-layer gate prints *59 pairing(s) share every boundary vertex
exactly*; `build_district_search.py --check` re-tests all 222 re-derived
extents and confirms each district's point still lies inside it; and
`build_block_population.py --check` confirms the congressional and both
legislative maps each still partition the state's 12,812,508 people exactly,
congress worst +0.002% — so the outline change lost and double-counted nothing.

**THE GATE PAIR WAS RE-MEASURED RATHER THAN CARRIED ACROSS, and this time it
did not move.** `validate_gate_counts.py` reads 84 / 113 on the merged tree and
`validate_steward_mirror.py` 113 for 113. That is worth stating precisely
because it is the case this repo has got wrong before: the pair moves when two
correct changes MEET, with nothing in either diff to look at, so the reading
that counts is the one taken after the merge. Nothing else landed on main
between the push and the merge but my own board entry, which is why the number
held — not because a pre-merge measurement is ever sufficient.

**WHAT IS STILL OPEN BELONGS TO THE SIBLINGS AND NOT TO ME.** Wisconsin nests 3
Assembly per Senate and Iowa 2 House per Senate, both measured off their own
shipped files. The half of this finding they need is the one a shared topology
alone does NOT give them: `combine-files` at the old Visvalingam percentage
still leaves Illinois at a 331.0 m worst stray with 175 of 177 districts past
25 m — the two layers simply wrong together, their nesting gate passing while
the lines still cut chords through blocks. The algorithm is what fixed the
strays, and their builders and their sources are theirs to measure.


**2026-09-25, evening. THE LEGISLATIVE BOUNDARIES NOW RUN WHERE THE REAL LINES
DO, AND IT COST 871 BYTES LESS THAN BEING WRONG.** PR #1174. Adam's two
observations — House highlight lines parting from their Senate district's at
zoom 16, and the boundary cutting diagonally through blocks where the real line
follows streets — were one defect in `build_legislative_boundaries.py`. Worst
stray of the true line from the drawn line goes 331.0 m to 17.8 m; districts
straying past 25 m go 176 of 177 to NONE; the House/Senate nesting goes from a
210 m worst error to exact on all 59 pairings.

**THE SOURCE WAS PERFECT AND EVERY METRE WAS OURS.** TIGER's Senate 20 against
House 39+40, as this builder itself fetches them, is 0.0000% area disagreement
with every Senate vertex 0.0 m from a House line.

**TWO CAUSES, AND THE SECOND WAS NEARLY MISSED BECAUSE FIXING THE FIRST LOOKS
SUFFICIENT.** mapshaper ran once per chamber at its own retain percentage and
builds topology WITHIN a file, so a shared edge could not survive; `combine-files`
fixes that and does NOTHING for the diagonals — measured on the full state it
still leaves 331 m and 175 of 177, the two layers wrong together. **A
SMALL-INPUT TEST SAYS OTHERWISE AND IS LYING**: the retain percentage is
relative to the whole dataset, so three districts at 10% keep far more detail
each than a state at 10%, which is how a three-district trial reported 4 m. The
real cause is that Visvalingam thresholds triangle AREA, which does not bound
deviation — successive below-threshold removals compound, and that is exactly
how a staircase becomes a chord through somebody's house. Douglas-Peucker
thresholds DEVIATION. Reaching the same fidelity by raising the percentage costs
3.0-3.5x the download, which is the trade this looked like until the ALGORITHM
was measured rather than the dial.

**THE FIDELITY METRIC HAS A DIRECTION AND THE OBVIOUS ONE GATES NOTHING**:
simplification keeps a SUBSET of source vertices, so every drawn vertex already
lies on the source line and measuring that way answers ~0 by construction. The
25 m ceiling is measured, not picked — the true line's own staircase step is a
median 17.9 m over the 191 source segments where Adam was looking, so 25 m is
about one step.

**THE CROSS-LAYER GATE IS EXACT, WITH NO TOLERANCE**, because under one topology
the Senate ring is assembled from House arcs: every Senate vertex IS a House
vertex. 59 of 59 after, 59 of 59 FAILING before. It needs no network, so it runs
in CI on the shipped files — the question the per-layer 2,000-point sample could
never ask, since that only tests whether a layer agrees with itself. The builder
takes no chamber argument any more, because rebuilding one chamber alone is the
defect.

**TWO COSTS RECORDED RATHER THAN SMOOTHED.** The new outline is a mean 0.6
people per district further from each congressional ideal (3.3 to 3.9, worst 14
to 18, both assigning every block exactly once), so IL-7's smoke fixture moved
753,676 to 753,659 — measured BOTH ways before the fixture was touched, because
changing an expected value to make a test pass is only honest if the new value
is the better one. The old one-person miss was luck. And the geometry is
cache-first, so `cache_name` went to v39 and 92 `district-search.json` extents
were re-derived through the builder's own function, the full rebuild having
correctly refused when 27 county GIS services were unreachable from here.

**2026-09-25, later. #1171 IS MERGED AS `66d5ed4` AND VERIFIED ON THE MERGED
TREE BY CONTENT.** The selftest prints its 7 checks; the gate pair holds at 83
named steps / 112 invocations; the steward mirror answers 112 for 112; CI
carries the step named "Peoria board index parser still reads both its measured
shapes" and the skill carries its line.

**THE STRONGEST CONFIRMATION IS A FILE THAT DID NOT MOVE.**
`il/data/app/peoria-county-board-members.json` was last written by `a9ae4cd`,
a press-list change from long before any of this, and the merge commit touches
exactly four files with that one not among them. So the roster a reader sees is
byte-identical to what it was while the workflow was failing — which is the
whole point: the refusal protected the data, the page was serving all 18 names
the entire time, and nothing about the county was ever wrong. Only the selector
was.

**THE GATE PAIR WAS RE-MEASURED AFTER THE MERGE RATHER THAN BEFORE IT**, and
two other PRs (#1170 and #1172, the hover-card fixes) landed in between,
touching `scripts/smoke_test.mjs`. They added no CI step, so 83/112 still holds
— but that is a measurement rather than an assumption, and it is the case
CLAUDE.md records as the one where two correct branches meet and both become
wrong with nothing in either diff to look at.

**2026-09-25. PEORIA'S ROSTER IS UNFROZEN AND THE FIX IS PR #1171.** The
Friday refresh failed at 19:10 UTC with the builder refusing to write — `the
County Board Members index named only 0 of the 18 roster members` — and that
refusal was right: the floor is not lowered, and nothing a reader sees moved,
because the shipped file kept every name from its last good run. The builder
wrote again with NO diff to that file, which is the whole result. The data was
never wrong, only frozen.

**THE PAGE WAS SERVING EVERY NAME THE WHOLE TIME.** Measured with this
scraper's own client, robots read first and allowed: HTTP 200, 109,010 bytes,
all 18 members in the served HTML. Not a block, not a fetch failure, not
client-rendered. CivicPlus reflowed the page — `subhead`, the class the
selector keyed on, now occurs ZERO times — and each member became an
anchor-bearing paragraph in an `fr-view` editor block. The Edgar shape again:
the page was fine and the parser was not.

**BOTH SHAPES ARE READ NOW, not one swapped for the other**, because the
heading shape was itself a CMS artifact and has moved once, so it can move
back; a county mid-reflow must not lose half its board. Two traps are pinned
with it. **`aria-level` IS NOT THE LEADERSHIP MARKER AND IT LOOKS LIKE ONE** —
exactly one paragraph on the page carries `aria-level="2"`, the Vice
Chairperson, while the Chairperson carries none, so anchoring on the page's own
statement of hierarchy finds one member of eighteen. And **THE ANCHOR IS
REQUIRED**: the name pattern ends in `|$`, so `Board meetings are held monthly`
would parse as a member of that name and enter the set the builder's floor
counts. The selftest — 7 offline checks, in CI and mirrored in the steward
skill — pins both shapes, both at once, the prose, and the negative case that
caused this. The gate pair is re-measured at 83 steps / 112 invocations, after
the rebase rather than before it.

**A LIMIT ON `get_check_runs` IS RECORDED, BECAUSE THIS SESSION NEARLY ACTED ON
ONE.** CLAUDE.md's "a zero is a true zero" was measured against PR #5, whose
run never existed and never would; it says nothing about a PR whose run is
STARTING. Measured on #1167: it read `total_count: 0` while paging
`actions_list` showed run 36184219899 already `in_progress` on the same head,
and reads that run successful now. On a head pushed in the last few minutes,
page for a run before concluding there is none.

**#1167 WAS SQUASH-MERGED WHILE THIS WAS BEING WRITTEN**, so its head and the
merge commit under it are dead history and the branch was restarted from main's
tip with the one unmerged commit replayed. #1171 is a new pull request, not that
one reopened. The Peoria workflow is dispatched on the branch rather than left
for next Friday.

**2026-09-25. TASK #50 IS DONE AND IS PR #1167 — 388 library trustees, read off
each library's own website.** The last open half of
`statewide-library-officials`. 53 libraries name a board from their own site, on
76 card features, 233 of the names with a role beside them; the layer goes from
173 of 382 libraries naming a board to 226, and `validate_index.py` prints the
pair with a gate that fails if any library is ever in both sources.

**THE POOL WAS SMALLER THAN THE RECORD IMPLIED AND IS NOW DERIVED RATHER THAN
GUESSED AT.** Not 373 and not 487 but 176 — every card that names no board and
links a site — read on each run from the same dispatch table the builder checks
against. A first draft globbed every `*-library-districts.json` while only 72 of
the 88 counties drawing a library dispatch through `statewideLibraryEntry`, which
would have shipped records for the builder's own orphan check to fail on.

**THE FLEET'S NAMES GATE CANNOT BE THE GUARD ON THIS DATA, and that is the
finding worth keeping.** `validate_officeholder_names.py` accepts both `No
Overdue Fines` and `Strategic Plan` as names, and a draft of this parser shipped
both as trustees — the first a marketing banner in the same `<div>` shape as the
trustees above it, the second a linked document. So the parser carries three
MEASURED rules instead of a stoplist that grows by anecdote: a word that never
begins a real name (none of the 31 begins any of the fleet's 13,094), a candidate
whose text appears nowhere on its page outside an `<a>` (two of 401, both
labels), and a stoplist whose every entry rejects ZERO real names. A first
draft's stoplist cost 60 real people, among them Trevor Ward, a trustee on the
first board page it ever read. 67 offline checks, in CI.

**FIVE HOSTS CARRY MORE THAN ONE LIBRARY AND ONLY ONE WAS ON RECORD.** The
guidebook had Bloomington (Golden Prairie's board on its page); measuring found
`annawanil.org`, `marshallillibrary.com`, `pekinpubliclibrary.org` and
`silvislibrary.org` as well. Marshall Area against Marshall Public is the pair no
distinctive-word test can split, since both names carry "marshall", and SILVIS'S
PAGE CARRIES TWO LIBRARIES' BOARDS UNDER TWO IDENTICAL `Board of Trustees`
LABELS — which a draft that unioned a page's sections (right for the four
libraries listing officers under one heading and the rest under another) would
have merged into a fifteen-name board.

**THE SHIPPED FILE IS A FLOOR, NOT A MEASUREMENT, and it says so.** Two passes
over the same pool an hour apart agreed on 51 libraries, which is the only reason
the builder's floors are settable at all; the second took 13 rate limits the
first did not, and this scraper's own earlier pass is the likeliest cause. A 429
is retried with backoff now rather than believed, a fetch that failed carries the
last-good record forward under your 2026-09-19 ruling, and Monday's run picks up
the rest.

**A GATE FOUND ONE THING BEYOND THE TASK and it is in the same PR.**
`fetch_stdlib` came off `probe_user_agents.py`'s browser-marker list: it is the
CLIENT for two of the four rungs and sends whatever headers its caller passes, so
naming it says nothing about the User-Agent. Exactly two files were classified on
that marker alone — `validate_sources.py`, which the module already records
misreading once, and this new scraper — and neither names a Chrome string, a hint
set or the word Mozilla anywhere in code. The four gated figures move 105/18/283
to 103/17/266, restated in all three documents that carry them.

**156 LIBRARIES STILL NAME NO TRUSTEE and the reasons are now measured rather
than estimated**: 33 publish no website, and of the 123 that do, 42 link no board
page, 26 have one that lists nobody, 33 could not be reached and 22 refuse this
client in robots.txt. A page that loads and lists nobody is the honest end of
this route, and nothing was worked around to get past one.

**2026-09-25. #1163 IS MERGED as `5a86c78` and verified on the merged tree by
content — all four facts hold.** `validate_officeholder_names.py` prints
`declared il/data/app/school-board-members.json +19 record(s) (2026-09-25)` and
`il 8155`; the two `audit_declared` negative tests still fail, one on a declared
path that names no file on the tree and one on `congress-roster.json`, whose
declaration the gate refuses with "the declaration admits 17 record(s) and the
walk already reached 17, so it adds nothing". Chicago's twenty elected school
board seats are gated for the first time. The docstring's stale 1,592 is
corrected, and the correction was made twice: 1,175 counts the nineteen this PR
admits, and the remainder a reader wants is **1,156**.

**THOSE 1,156 ARE LEFT UNDECLARED ON PURPOSE AND THIS IS WHERE THAT IS WRITTEN
DOWN.** They are `wi/county-board-members.json` (1,096), `ny/council-members.json`
(51), `wi/mpd-district-captains.json` (7) and `wi/wi-municipal-executives.json`
(2) — every one of them a file whose shape belongs to a sibling session's state.
A declaration is a claim that a path's records are people, and the mechanism only
works if the person declaring has read the file's own shape; declaring four
files across two instances I do not own would have put my reading of them into a
gate that fails on somebody else's branch. The mechanism is there and the entry
is four lines of `PERSON_PATHS` per file whenever those sessions want it.

**2026-09-25. #1161 IS MERGED as `80f98c6` and verified on the merged tree by
content — five checks, all pass.** `docs/EAM_STATUS.md` reads `il | EAM`; the nine
class globs print their reach per pattern; `--selftest` prints 12 cadence cells,
5 accepted / 7 refused; the CPS date cell carries the month span; and the
`ia/WATCH.md` cell that is the widening's negative test still returns False.
The whole battery is green on main, 100 of 100.

**ILLINOIS IS THE FIRST INSTANCE TO READ EAM, and what that letter does NOT mean
is worth stating plainly here rather than being inferred later.** Every one of the
eleven rows has `Last done: (never)`. The M bar asks for a row that names the file
and states when it is re-checked, so the letter is earned on the bar's own terms —
and no re-check has been performed, no county outline has been compared against a
fresh TIGER vintage, and the precinct row is a calendar entry standing in for a
detector that closed with #1150. **The letter says a plan exists, not that the
data was re-verified.** The question went to the reviewer at the top of the PR
body and the PR was merged with it visible; if the letter should mean more than
this, the DEFINITION is what wants changing and these rows stay as they are.

**Three of my own claims in this pair of PRs were wrong and each was caught by a
different mechanism**, which is the method note worth keeping: a glob that
silently applied 55 ILCS 5/2-3003 to the congressional map, caught by the reach
count printed per pattern; a ceiling guard that counted leftovers rather than
reach and so could barely fail, caught by its own negative test refusing to fire;
and a board entry of my own saying a `--check` is the stronger guard, caught by
measuring what three of them actually do. None was caught by reading.

**Carried, none assigned:** task #50 (library trustees from each library's own
site), the fourteen drafted Illinois asks still with Adam unsent, and
`validate_officeholder_names.py`'s flat-keyed blind class. **And a question for the
manager rather than an action of mine**: the E.A.M. instrument's own docstring says
it exists so that a finished state can be declared and a session moved off
expansion. Illinois now reads finished on that instrument. Whether this session
moves is theirs to decide, not mine to assume.

**2026-09-25. ADAM RULED "WIDEN THE VOCABULARY TO ACCEPT A DATE" AND I HAD
ALREADY GONE THE OTHER WAY.** His message reached me after #1161 was pushed: I
had reasoned to *reword rather than widen* on my own and written every class row
to fit the existing vocabulary, which answers the question and is not the answer
he gave. The widening is now #1161's own commit (`f3e94a5`), in this module
rather than the manager's, for the conflict reason their brief gave — a third
same-day instance of that defect avoided rather than paid for.

**ANCHORED AT THE START OF THE CELL, and their named cell is the SHIPPED negative
test.** `ia/WATCH.md` line 53 states outright that it has no cadence and mentions
`mid-2026` in its prose, so a bare `\b20\d\d\b` would have promoted "no fixed
cadence" to a plan. Verified against the actual line rather than a paraphrase:
`states_a_when` returns False. **The tests ship rather than living in a shell** —
`WHEN_CASES`, twelve cells, five accepted and seven refused, `--selftest` printing
the split so the clause cannot quietly stop meaning anything.

**NO INSTANCE'S FIGURES MOVE and that was measured, not assumed**: il 397/all,
wi 262/240, ia 57/40, mi 53/45. The date-only cells name no `.json` file, so the
widening contributes no plans today; what it buys is that those four checkpoint
rows become readable the moment one names a file, and the identical set is in
`ny/WATCH.md` and `ca/WATCH.md`, neither touched.

**The manager's correction of their own brief was already in the rows** — the CPS
cell reads the month SPAN from the four publications in the table underneath it,
not the single month their first message asked for. Their escape hatch went
unused because the span was both honest and already valid, and they were right
that the two changes are independent: that cell holds no date, so a date widening
leaves it rejected either way.

**#1161 IS WAITING ON ITS REVIEWER WITH ONE QUESTION THAT IS NOT MINE**: it takes
Illinois to `EAM` on eleven rows whose `Last done` is every one `(never)`. The M
bar asks for a row that names the file and states a when, so it passes on the
bar's own terms — and if a plan nobody has run should not count, the DEFINITION
wants revisiting rather than the rows. Better that the letter be rejected than
that I write vaguer rows to avoid claiming it.

**2026-09-25. #1160 MERGED and verified on the merged tree — 397/305/3 for
Illinois, the corrected figures, instrument green. PR B IS OPEN AS #1161 and it
takes Illinois to EAM, the first instance to reach it.** Flagged at the top of
its body rather than buried: every new row's `Last done` is `(never)`, the M bar
asks for a row that names the file and states when it is re-checked, and these
are that — so Illinois passes on the bar's own terms today. **If a plan nobody has
executed should not count, the DEFINITION wants revisiting rather than the rows**,
which is the operator's call; I would rather the letter be rejected than write
dishonest rows to avoid claiming it.

**The rows cite the runbook's exposure classes and a row may now name a CLASS**,
which is the instrument change PR B needed and the brief did not anticipate:
`watch_rows` read rows by FILENAME, so a plan for 101 county outlines would have
been 101 lines restating one fact. A glob in backticks (`*-<suffix>.json`) with
three guards, ALL NEGATIVE-TESTED — backticked so prose cannot match and a bare
`*.json` is inexpressible, a six-character minimum suffix, and a FAIL when one
pattern reaches more than a third of an instance's surface.

**THE CEILING'S FIRST VERSION WAS NEARLY VACUOUS AND ITS OWN NEGATIVE TEST CAUGHT
IT**, which is this board's own rule from Wisconsin this morning working on me:
if you cannot say what would have made a check fail, it tested nothing. It
counted what each pattern was LEFT after earlier rows claimed theirs, and the
lookup breaks on the first match, so a blanket written below the narrow rows took
only the leftovers and passed. Counted against the whole surface it reaches 139 of
397 and fails.

**TWO OF MY OWN CLAIMS WERE WRONG AND THE RUN CAUGHT BOTH.** The printed reach
count showed `*-districts.json` at 43 rather than 38 — it also matches the
congressional, legislative, Supreme Court, Board of Review and Chicago
school-board maps, so my row had silently claimed **55 ILCS 5/2-3003, the
county-board statute, for the congressional map**; split into three rows on the
runbook's own classes. And **a `--check` proves a file matches its INPUTS and
never that the inputs are current**, which corrects the board entry I wrote two
hours ago: measured, `build_coverage_gaps.py --check` re-emits and compares,
`build_county_board_offices.py --check` verifies against a fresh build, and
`build_metro_outline.py --check` does neither — it reads the anchor registry.
Three guarantees, none upstream, so all four derived files are in the table.

**The CPS row is reworded to Adam's ruling** — reword rather than widen the
vocabulary — and to a month SPAN rather than a month, because this file's own
edition table records four publications from 24 August to 3 October. The manager's
instruction said "the month", singular, and the file disproves it one line below
the row; naming one month would be less true than what we already know. `Last
done` and the 2026-09-03 half-run note untouched.

**The precinct row is the weakest plan in the file and says so**: 38 of 46 layers
are a Census 2020 snapshot, the ISBE tripwire closed with #1150, and the
three-vendor replacement (34 + 13 + 17 counties) is smaller and not built. A
calendar entry standing in for a detector, recorded as that.

**2026-09-25. PR B's DESIGN is settled and it is smaller than the brief assumed:
the rows CITE a clock that already exists rather than stating one.**
`docs/REDISTRICTING_RUNBOOK.md` carries a per-layer blast-radius table with an
EXPOSURE CLASS and an enacting authority for every Illinois layer family, and it
covers every class the 305 unplanned files fall into — county outlines under
"County / township / municipality (statewide): annexation-driven, rolling;
TIGERweb vintages", the fire/park/library/precinct families under
"Administrative / per-election", board districts under "Decennial-municipal",
subcircuits under "Statutory, rare". **So a WATCH.md row that reasoned out its
own clock would be a second reader of a question the runbook already answers**,
which is the defect this repo keeps paying for. `WATCH.md` is "when to look" and
the runbook is "what to do"; the row states the cadence and names the runbook
row, and nothing is restated.

**THE 13 SINGLETONS ARE TWO DIFFERENT KINDS AND ONLY ONE WANTS A DATE.** Five of
them are DERIVED and carry a `--check` in CI that rebuilds or verifies them on
every PR (`coverage-gaps.json`, `metro-outline.json`, `il-state-outline.json`,
`municipal-ward-coverage.json`, `il-county-board-offices.json`), which is a
stronger drift guard than any watcher — and says NOTHING about the source
moving, so the row has to separate the two guarantees rather than claim the
`--check` as a plan. The rest are the decennial legislative and court maps, whose
clock is the 2031 row this file already carries.

**AND THE CENSUS POPULATION CLASS NEEDS NO ROW AT ALL** — the 2031 TIGERweb row
already names it, which PR A's `watch_rows` fix is what revealed.

**ONE DECISION IS HELD FOR THE OPERATOR RATHER THAN TAKEN.** The instrument's
`WHEN` vocabulary accepts "census" and "annual" and REJECTS four real date cells
in this same file: `**2029 Q4**`, `**2031 Q2**`, `**2031–2032**` and "Late
summer, when the new `SYxxyy` CPS attendance datasets post" — the CPS drill row,
which the file itself calls the load-bearing habit. A bare year, or a year and a
quarter, is a more specific when than "annually". Widening a gate's vocabulary is
a decision and its own docstring records that it was already widened once for a
stated reason, so it is flagged on #1160 and not done there; it decides how PR
B's rows must be WORDED, so PR B waits on it rather than writing rows twice.

**2026-09-25. PR A IS OPEN AS #1160 and the surface defect was worse than
stage 1 reported.** The instrument kept every `data/app/*.json` whose BASENAME
appears in its instance's `index.html`, and three Illinois loaders build their
URL by concatenation, so it missed 86 of Illinois's 388 files, 215 of
Wisconsin's 262, 24 of Iowa's 57, 31 of Michigan's 53, 5 of New York's 25 and 1
of San Francisco's 14 — Wisconsin's whole per-county polling-place set and
Illinois's county outlines among them. **The reader is now `sw.js`, and the
choice was measured rather than assumed**: the worksheet's `data_files`, the two
`sw.js` lists and a bare glob all give the same 388, because every link in the
chain is gated — a stray `data/app` file was added to prove `validate_index.py`
fails on it — so `sw.js` is read because it is the app's own statement about its
fetches rather than an authoring surface or a directory listing. A missing list
FAILS rather than emptying the surface, which is the byte-order-mark defect one
level up: an instance with no files reads as fully maintained.

**Illinois's WATCH.md is the root one, and reading `<tag>/WATCH.md` read nothing
for it** — no gate could see that, because an empty plan list is what a state
with no plans looks like. It now reports 2 files under a plan where it reported
none. `il/data/app/population/` enters as ONE class row with its own declared
kind (census block weights rot on the next decennial census and on nothing
else), and **four code paths broke on a rel path ending in `/`** — including the
`watch_rows` scan, so a WATCH.md row written for the folder would have counted
for nothing while looking exactly like a plan, which is the trap PR B would have
walked into. Effect: surface il 310→397, wi 47→262, ia 33→57, mi 22→53;
without a job il 221→306, wi 25→240, ia 16→40, mi 14→45. No letters change,
and nothing in the sibling instances is edited — their numbers move because the
instrument stops under-reading them.

**#1160 CARRIES TWO SUBJECTS AND SAYS SO**, because this session develops on one
branch and a second PR would need a second one: the surface fix plus the
two-line CI-diagnosis correction above. They are separate commits and the body
offers the split. All 100 static invocations green through a runner gated on its
own verdict, Illinois smoke and landing tests green, no served byte touched.

**PR B's classes re-derived on the NEW surface** (305 unplanned, not 219): 101
county outlines, 79 library districts, 46 county precinct layers, 37 board
district files, 9 fire, 8 park, 6 precinct polling, 5 judicial subcircuits, 1
city outline, 13 singletons and the census population class. Grouping is by
CLOCK rather than by filename, because a WATCH.md row's whole job is to state a
when — and one finding is already visible: several of the singletons
(`coverage-gaps.json`, `metro-outline.json`, `il-county-board-offices.json`) are
held by a `--check` in CI rather than by any schedule, and the guarantees are
NOT the same file to file, so that is a row to write carefully rather than a
category to claim.

**2026-09-25. TWO CLAIMS I PUBLISHED THIS MORNING WERE FALSE, and `39210c7` is
what made me re-check them — #1160.** I said `smoke-test.yml` has no
`workflow_dispatch` (it has declared one since 2026-09-01) and that GitHub
dropped a CI event for `3e5a487` (it did not). Both corrected below in the
fourth pass's own paragraph, on #1150 in a comment, and in `CLAUDE.md` plus the
steward skill so the next session gets the order right. The finding worth keeping
is that **a real absence of checks is not automatically the expired PAT**: two
pushes got no run, the two either side ran, and what separates them is that both
silent heads conflicted with main while both that ran merged clean — four for
four, measured with `git merge-tree`. The fix was the conflict, and merging main
in is what made CI fire. `39210c7` ends a real absence at the token; #1160
inserts the merge test ahead of it, ordered by branch kind, because a `bot/*`
branch cut fresh from its run's SHA rarely conflicts and a session branch often
does. **The method lesson is the one already on this board twice: an explanation
that predicts nothing is a guess standing where a measurement was available.**

**2026-09-25. #1150 IS MERGED and verified on the merged tree by content rather
than from the PR body — eleven checks, all pass.** The BOM'd `Disallow: /` now
refuses on main; the fixture ships with its BOM intact; ISBE's provenance entry
carries `robots_declined` and NOT `blocked`; that entry makes ZERO `http_get`
calls and reports OK while the rule stands; all three ISBE-fetching scrapers call
the shared gate; and `il-county-clerks.json` still holds its 101 clerks, which is
the half that matters to a reader — **the refusal stopped our fetching and
unpublished nothing.**

ISBE has been refusing this project since 12 June 2025 and the fleet's one robots
reader called it permitted, because a UTF-8 byte-order mark made `_parse` open no
group at all. Seven of 295 hosts serve a BOM; two are ISBE and refuse, five are
Dane County and permit everything but `/Account`. The check-ins are stopped.

**THE COST IS REAL AND IS NOT CLOSED**: the re-precincting tripwire is gone,
because ISBE was the only source carrying all 102 election authorities and 38 of
Illinois's 46 shipped precinct layers are a Census 2020 snapshot. The vendor-side
replacement is the second open question below.

Next: PR A (the `sw.js` surface + Illinois's root `WATCH.md`), on a branch cut
fresh from main rather than stacked.

**2026-09-25, sixth pass. I pushed a branch with the battery RED, and the cause
is worth more than the push: MY RUNNER REPORTED THE FAILURE AND EXITED 0.**

The loop printed `=== static failures: 1` and returned success, so
`... && git commit && git push` fired on red. **A RUNNER THAT REPORTS FAILURES
IT DOES NOT PROPAGATE IS WORSE THAN NO RUNNER** — it produces the paperwork of a
check while removing its effect, and it defeats exactly the `&&` a careful person
adds to be safe. Every runner ends on its own verdict now
(`[ "$fails" -eq 0 ]`), and this is the second time today a throwaway script of
mine was the defect rather than the thing it measured (the first labelled
`population/index.json` by the wrong question).

**The failure itself was not this branch's.** Four city records in Iowa's
`ia-county-city-officials.json` read as VANISHED because MAIN GAINED THEM AFTER
THIS BRANCH POINT, so `--base origin/main` saw them missing here. Merged main in,
which is the remedy the drive-to-green rules name — and it conflicted on
`docs/ENDPOINT_INVENTORY.md`, a GENERATED file, so it was regenerated rather than
resolved by reading the diff, and all six other generated files were re-checked
rather than trusted because the half that conflicts is the lucky half.

**AND TWO PUSHES GOT NO CI RUN, WHICH WAS THE MERGE CONFLICT ABOVE AND NOT A
DROPPED EVENT — CORRECTED 2026-09-25 as #1160.** This paragraph said "GITHUB
DROPPED A CI EVENT", named one push, and asserted that `smoke-test.yml` has no
`workflow_dispatch`. Every part of that is wrong. The file has declared
`workflow_dispatch: {}` since 2026-09-01 (#650) — I read the `on:` block, found
the two triggers I expected and stopped — and `39210c7` tells sessions to
dispatch that very workflow, so the claim stood in contradiction to the rule.
The absence covered TWO pushes (`3e5a487` at 08:27:02 and `94668fc` at 08:54:33)
and was established the wrong way: my `actions_list` query passed
`workflow_runs_filter`, which this build IGNORES, so it looked exhaustive and
swept nothing. **Paged unfiltered and matched by `head_sha`, the four pushes
split cleanly: the two silent heads CONFLICTED with main on
`docs/ENDPOINT_INVENTORY.md` and the two that ran merged clean**, four for four
under `git merge-tree --write-tree <head> <main's tip at that minute>`. A
conflicted PR gives GitHub no merge ref to build a run against — that half is
inference — but the remedy follows either way: merging main in is what made CI
fire, so **the fix was the conflict, and the cause was in the paragraph directly
above this one.** "GitHub dropped the event" explains nothing and predicts
nothing, which is the tell that a guess has filled a gap where a measurement was
available — the 79-of-100 failure one step removed. **A HEAD WITH NO CHECKS
READS EXACTLY LIKE A GREEN ONE at a glance**, which stands; what changes is the
order to test it in — a `bot/*` branch cut fresh from its run's own SHA rarely
conflicts, so there `BOT_PR_TOKEN` is still first; a long-lived session branch
often does, so there it is last.

The reviewer's requested CLAUDE.md rule about enumerating the battery went into
this PR rather than PR A, because this is where the mistake happened and the file
was already being edited here; deferring a lesson to a PR that does not exist yet
is how lessons get lost.

**2026-09-25, fifth pass. #1150 was HELD on review and the hold was right: my
`blocked` entry inverted the REPORT and not the REQUEST, so the monthly source
gate would have fetched the exact path ISBE asked us not to read — in the change
that established the refusal. Fixed in `3e5a487`.**

`check_provenance` runs `http_get(p["source_url"])` unconditionally at line 1329,
before it has read the flag at all. **AN INVERSION ON THE REPORT IS NOT AN
INVERSION ON THE REQUEST**, and my own note carried the argument for a different
mechanism without following it — "UNLIKE the other blocked entries this one is a
POLICY and not an outage" is a reason to stop fetching, and I used it as prose on
the mechanism that fetches. That is the Rochester Hills defect this repo had
already paid for once, and `ROBOTS_DECLINED` in `validate_card_links.py` was the
remedy invented then — **the very table this same PR was already using correctly
in the sibling gate.** I had the right mechanism in one hand and the wrong one in
the other, in one change.

`robots_declined` never calls `http_get`: an outage is worth re-probing because
probing is how you learn it ended, and a refusal is not, because the document that
says whether it has lifted is robots.txt. Read through `robots_policy` as the
client this gate crawls as, with `VALIDATOR_UA` now one constant for both the
robots read and the crawl. **Proven by instrumenting `http_get` rather than by
reading: zero calls on the refused path AND zero on the lifted one.**

**THE REVIEWER ALSO CAUGHT A FIGURE I HAD CORRECTED IN ONE PLACE AND NOT THE
OTHER** — `require_robots_allowed`'s docstring still said "six files here read
it" where the PR body already said three. A correction that reaches the PR body
and not the shared helper leaves the authoritative-looking copy wrong. It now says
six referenced it and three fetched it, which is the honest version.

And one the review made me look for: `build_endpoint_inventory.py` counted
`"blocked":` literals alone, so moving ISBE to the other key would have taken
Illinois's "sources measured as blocking" from 6 back to 5 — **a refusal vanishing
from a reader-facing figure because its mechanism changed.** It counts both classes
now. The lesson generalises past this entry: when a fact gets a second mechanism,
grep for everything that counted the first one.

**2026-09-25, fourth pass. #1150 is green, mergeable and waiting on its
reviewer. Before that I had to correct my own verification claim, and the
correction is the more useful half: I ran 79 of the battery's 100 static
invocations and wrote "the full static battery" in the PR body.**

**A GREP FOR `run: python3` MISSES EVERY MULTI-LINE `run: |` BLOCK.** That is how
79 reads as complete: my extraction matched the command at the start of a line,
so 21 invocations were invisible to it — `generate_metro_files.py --check`, all
six `build_coverage_gaps.py --check` runs, `validate_gap_counts.py`,
`build_eam_status.py --check`, the four `build_metro_outline.py --check` runs,
five sibling-instance scraper selftests and
`build_parcel_fabric_districts.py --selftest`. All 21 pass, so nothing was
broken; what was wrong was the claim.

**THIS IS THE SECOND TIME TODAY AND `CLAUDE.md` ALREADY RECORDS THE FIRST** —
"run the workflow's own command list, never a remembered subset", written after
the Michigan go-live and again in this session's own Status. I wrote about it and
then did it, which says the rule as stated is not enough: it tells you not to
remember a subset and says nothing about a grep you just wrote, which does not
feel like remembering. **THE SHARPER RULE: the steward skill already carries the
exact list, gated as an exact mirror by
`scripts/validate_steward_mirror.py` (110 for 110). Run that. An extraction of
your own is how you get 79 of 100** — and `scripts/validate_gate_counts.py`'s own
enumeration rule is the second honest way to get the list, since that module
exists to read this file correctly.

That sentence belongs in `CLAUDE.md`'s Running & testing section and is NOT
committed here: `CLAUDE.md` is read by three gates, so it cannot ride the
board's straight-to-main route. It rides PR A.

**2026-09-25, third pass. The manager's routing is accepted and the population
figure is corrected below, with the cause named rather than just the number.
Two PRs to come, in this order, because #1150 holds the branch.**

Take (a): extend the root `WATCH.md` with the class rows, and teach
`build_eam_status.py` that Illinois's watch file is the root one. Both PRs will
say which they are.

**PR A — the instrument.** Read each instance's flat surface from its own
`sw.js` lists, which are generated from the worksheet's `data_files` and name
every file including the concatenated ones (measured: `sw.js` misses 0 in all
six instances where `index.html` misses 86 / 215 / 24 / 31 / 5 / 1).
`il/data/app/population/` is handled on its own, because it is deliberately in
no `sw.js` list and `CLAUDE.md` records why — that is the one class `sw.js`
cannot answer for. Plus Illinois's `WATCH.md` path. **Wisconsin's unplanned
count jumps when this lands** — 82% of its data files are outside the current
bar — and that is a truer number rather than a regression; nothing publishes the
E.A.M. mark to a reader, so no card changes. The PR body will say so for
Wisconsin, Iowa and Michigan; their instances are not edited.

The self-catch goes in `build_eam_status.py`'s own docstring, not only here: a
runtime slug can come from a DATA file — the gaps panel draws any county whose
outline ships, from `coverage-gaps.json` — so "no code path can produce this
file" is not a conclusion a grep of the app can reach. That is why the surface
test was wrong in the first place, so it belongs beside the fix.

**PR A's figures are already measured**, prototyped offline with the same
independent reader that reproduced the current 221, so the PR body carries them
rather than discovering them:

| instance | surface today | unplanned today | surface after | unplanned after |
|---|---|---|---|---|
| il | 302 | 221 | 491 | **408** |
| wi | 47 | 25 | 262 | **240** |
| ia | 33 | 16 | 57 | **40** |
| mi | 22 | 14 | 53 | **45** |

Illinois lands on 408 rather than 410 because reading the root `WATCH.md` moves
`district-search.json` and `early-voting-sites.json` into planned. The eight
adapter roster paths outside `data/app` stay in the surface as they are today, so
the shipped figure will be a little above 491; it is computed in the code rather
than carried from here. **Wisconsin's is the one to look at** — 25 to 240 — and
its newly visible files are 92 boundary and 148 structure, which is a different
mix from Illinois's and is Wisconsin's to read, not mine.

**PR B — the rows**, eleven of them on the root `WATCH.md`, from the class table
below, starting from 219 rather than 221.

**Sequencing.** #1150 (the ISBE robots fix) is on this session's designated
branch, so PR A starts when it merges; I am not stacking a second PR on it after
writing down what the last squash-merge did to two generated files. The two ISBE
questions below are still open and are not affected by any of this.

**2026-09-25, later. Checking whether the precinct tripwire could be scheduled
found that ISBE refuses this project and has since June 2025, and that the
fleet's one robots.txt reader was turning that refusal into a permission. #1150.
It also corrects the report below: the tripwire row I recommended is closed.**

`www.elections.il.gov/robots.txt` is 29 bytes — a UTF-8 byte-order mark, then
`User-agent: *` and `Disallow: /` — with `Last-Modified: Thu, 12 Jun 2025
06:39:17 GMT`. Confirmed from two clients against the origin's own headers
(Cloudflare edge, the site's own CSP, a NetScaler `Via`, IIS's scrambled
`Cteonnt-Length: 29`), so it is the origin's file and not this sandbox's proxy —
the check `CLAUDE.md` demands before recording a host, and it mattered here.

**`﻿` IS NOT WHITESPACE TO `str.lstrip()`.** So `robots_policy._parse` read
a field named `﻿user-agent`, opened no group at all, left the `Disallow: /`
belonging to nothing, and answered `(True, 'no group binds this client')` for
every path on the host. That is the wyomingmi failure class — a group that
silently fails to BIND — inside the module written to end it, and worse in
direction: that one permitted a directory, this one permitted a host that had
been refusing us for over a year. **The three defects this module has ever had
are all a group failing to bind and none is a rule misread once a group is open,
so `no group binds this client` on a file that plainly has one is the shape to
distrust.**

**AND THE MEASUREMENT WAS ALREADY IN THE REPOSITORY.**
`user-agent-measurements.json` has said since 2026-09-13 that a group binds this
client on that host with one rule. Taken, filed, never read — this fleet's own
recurring defect, on the one class of measurement where the cost is compliance
rather than a wrong number.

**What stops, and what does not.** Three files fetched ISBE and now decline at
`scraper_common.require_robots_allowed`: the WEEKLY `il_county_clerk_scraper.py`,
`isbe_county_officers_scraper.py`, `isbe_precinct_fabric.py`. **A CITATION IS NOT
A FETCH** — three builders write an `elections.il.gov` `resultsUrl`/`mapUrl` into
their output and never request it, and the cards link the host; all of it stays,
because robots.txt governs crawling and not linking. My own first reading said
"six callers read it" and measuring which ones actually fetch corrected it to
three. **Nothing is unpublished**: `il-county-clerks.json` keeps its 101 clerks
under Adam's preserve ruling, and the weekly job now stops before the fetch
rather than shipping an empty file.

**THE CORRECTION TO THE REPORT BELOW.** Its strongest recommendation was a
scheduled comparison from `isbe_precinct_fabric.py`, the one class of the 410
that needs a machine rather than a date. **That route is closed** — ISBE was the
only source carrying all 102 election authorities. The finding underneath it
stands and gets worse rather than better: 38 of the 46 precinct files are a
Census 2020 snapshot, a clerk consolidates when a clerk decides to, and there is
now nothing statewide to detect it. The three results vendors carry 34, 13 and 17
counties and are unaffected, so a partial tripwire is buildable from them; that
is a smaller answer than the one I recommended this morning and it is the honest
one. The module's `--selftest` stays in CI, offline, for the day a route reopens.

**The rest of the report below is unaffected** — the 221's reproduction, the 86
files the surface misses, and where Illinois's `WATCH.md` lives are all
independent of this.

**2026-09-25. Stage 1 of the `WATCH.md` assignment: the 221 reproduces exactly,
and the instrument that produced it understates by 86 files and reads the wrong
path for this instance. Both corrections point the same way — there is more
unplanned than the brief says, and the file to write is not `il/WATCH.md`.**

**THE NUMBER IS RIGHT ABOUT WHAT IT MEASURES.** Re-derived without importing
`build_eam_status.py` — a second reader over the same tree, because that module
was corrected five times on the day it was written: **221 unplanned, 211
boundary, 10 structure, 0 naming a person.** Identical on every figure. So this
is not a sixth correction of the count, and the brief's headline holds: no
officeholder is going stale here. I checked that harder than asked — the
person test was run over all 410 files below, not the 221, and **no unplanned
Illinois file carries a person-shaped record or a role-ish key.**

**ITS SURFACE IS 310 OF THE 491 FILES THE APP ACTUALLY READS, and it misses them
in the direction that hides work.** The surface test is "basename appears
literally in `il/index.html`". Three loaders build their URL instead:

- `il/index.html:6277` — `"data/app/" + slug + "-county-outline.json"`, the gaps panel's outline loader
- `il/index.html:16227` — the same concatenation for the county-dispatched layers
- `il/index.html:16243` — `"data/app/" + slug + "-library-districts.json"`

so **86 shipped boundary files are invisible to it** (21 county outlines, 65
library districts), and the **103** `il/data/app/population/*.json` files are
served by prefix from a directory its glob does not descend into. **That figure
read 102 until the manager checked it, and the cause is the defect I was
measuring, in my own script** — I labelled a file "reached by a built URL" or
"reached by prefix" by asking whether its basename appears in `index.html`, so
`population/index.json`, whose basename does, was counted as literally
referenced although the instrument's `il/data/app/*.json` glob never descends to
it. **A TEST THAT ANSWERS A DIFFERENT QUESTION FROM THE ONE ASKED** is what the
whole pass is about, and a throwaway measuring script gets no exemption: the
question was never "is this basename in the app", it was "does the surface reach
this file", and all 103 are outside it whatever the app happens to name. Measured: **491 files
the app reads, 81 under a cron or a watcher, 410 with no plan** — 297 boundary,
113 structure, 0 people. This is the Wisconsin correction the brief cites,
happening again in Illinois: a surface that misses the file the card is drawn
on. **The fix is already in the tree and costs no regex — `il/sw.js` names all
86**, because its URL lists are generated from the worksheet's `data_files`, so
reading the surface from `sw.js` answers all 388 flat files exactly.

**`il/WATCH.md` IS NOT A MISSING FILE. IT IS A FILE THREE SKILLS SAY MUST NOT
EXIST, AND ILLINOIS'S WATCH CALENDAR IS THE ROOT ONE.** `expand/SKILL.md`:
"Illinois's `WATCH.md`, `CLAUDE.md` and `README.md` are the root files; there is
no `il/scripts/`, `il/WATCH.md` or `il/CLAUDE.md`". `new-layer/SKILL.md`: "a row
in `WATCH.md` (root for Illinois, `<tag>/WATCH.md` elsewhere)".
`boundary-change/SKILL.md`: "root `WATCH.md` for Illinois". `validate_skills.py`
reads a path a skill names in order to say it is NOT there as the warning it is.
The root file has carried a dated calendar since the metro era — the CPS drill,
the early-voting refresh, 2029 Q4, 2031 Q2, the 2031 TIGERweb block roll,
2031-2032 legislative, 2032-2033 municipal — and says so itself: "This file is
CHI's." `build_eam_status.py` reads `<tag>/WATCH.md` for every state, so for
Illinois it reads nothing. **Run its own row-reader over the root file and it
accepts two of the 221 before a word is written** — `district-search.json` and
`early-voting-sites.json` — so the true starting figure is **219**.

**WHAT THE 410 ARE, in the classes a plan would name.** Eleven rows cover all of
them; 221 rows would cover none, because nobody reads 221 rows.

| n | class | what moves it | row shape |
|---|---|---|---|
| 103 | Census 2020 block population | the 2030 census, and nothing else until then | **already a root row** (2031 TIGERweb) — it names the folder, so add the file pattern |
| 101 | county outlines (TIGER) | a county line changes by statute; the TIGER vintage rolls annually | one row: re-run `build_county_outline.py` at each vintage roll, same shape as the CD120→CD121 row |
| 79 | library districts | annexation, continuously, from a publisher whose provenance is already recorded as weak | one row, annual — and the weakest row in the set |
| 46 | precinct fabric | **a county clerk's own decision, any year** | **the one class a date cannot cover — see below** |
| 35 | county board districts | decennial reapportionment, plus mid-decade redraws | one row: post-census, plus the off-cycle trigger the root file already has |
| 17 | fire + park districts | annexation | one row, annual |
| 6 | polling places | per election | one row, per-election, beside the early-voting row |
| 5 | judicial subcircuits | the General Assembly; `validate_sources.py` already watches the two hosts monthly | one row, statutory |
| 3 | legislative districts | enactment and court order | **already a root row by LAYER** — add the three filenames so the instrument can see it |
| 4 | our own derived files (`metro-outline`, `coverage-gaps`, `municipal-ward-coverage`, `il-county-board-offices`) | our own tree; each has a CI `--check` | one row saying the gate is the plan |
| 11 | the singletons (state outline, Belvidere's place outline, Macon's labels, Menard's commissioner districts, DeKalb's precinct-township table, the two statewide decennial sets, the two other board-district sets) | mixed | one row, or two |

For scale: 307 of the 410 are floored by `validate_index.py` (which catches a
file emptying, never a boundary moving) and 38 are in `validate_sources.py`'s
monthly manifest (which catches a source going unreachable, never a source
publishing something new).

**ONE CLASS NEEDS A MACHINE RATHER THAN A DATE, AND ITS MACHINE IS WRITTEN AND
SCHEDULED NOWHERE.** Of the 46 precinct files, **38 carry `pop2020`** — they are
dissolved from the Census 2020 voting-district fabric, a snapshot that goes
silently wrong the day a clerk consolidates, and `CLAUDE.md` records that
happening three times (McDonough's drift, Christian re-precincting after 2020,
Vermilion consolidating 84 census precincts to 38 current ones). The other 8 come
from a county's own current layer and re-read themselves.
`scripts/isbe_precinct_fabric.py` was built for exactly this: all 102 election
authorities from one host, compared election-to-election rather than against the
shipped layer, with the two normalisations measured. **The only thing any
workflow runs is its `--selftest`** (`smoke-test.yml:994`), which proves the
parser offline and asks the question of nobody. A cadence cell cannot substitute:
a clerk consolidates when a clerk decides to, so this row's honest content is a
scheduled comparison that opens an issue.

**AND ONE READING I GOT WRONG, CAUGHT BY THE CODE RATHER THAN BY A GATE.** Eight
county outlines ship for counties whose slug appears nowhere in `il/index.html`
as a quoted string — Bureau, Champaign, Fayette, Jasper, Lawrence, Marion, Piatt,
Pope, every one of them unserved — and I had them written down as dead files in
the precache list. They are not. The loader's own comment at `il/index.html:6271`
says why: "The `<slug>-county-outline.json` naming convention IS the contract
here, so a gap can reference any county whose outline ships without this needing
a per-county branch." The slug comes from `coverage-gaps.json`, and all eight are
in gap records, so the gaps panel draws them. **A runtime slug can come from a
DATA file, so "no code path can produce it" is not a conclusion a grep of the app
can reach** — the same class as the concatenated-URL miss above, one step
further out.

**Nothing written yet, which is what stage 1 asked.** The one decision before the
file gets built is in Open questions below.

**2026-09-23, later. Adam said "merge 1125 then 1127". Both are in — `02abf6f`
and `4a785724` — and getting the second one there cost three commits that are
worth more than the change.**

**A SQUASH MERGE MOVES A STACKED BRANCH'S MERGE BASE, and git then handles the
two generated files that count people in opposite ways.** #1125 squashed, so its
own commit stopped being an ancestor of main and the base for #1127 fell back to
the commit before it — both sides looked like independent edits.
`docs/EAM_STATUS.md` CONFLICTED, on Illinois's "N without a job" column.
`about.html` MERGED CLEAN AND WRONG, taking #1125's "3,383 more across the 42
rosters" onto a tree that names 3,385, because this change's two new seats moved
a different hunk. That is the gate-count lesson `CLAUDE.md` already records —
the half that conflicts is the lucky half — in a second file class. **Check the
generated files by REGENERATING them after any merge, never by reading the
diff**, and note that GitHub's own merge button would have shipped the silent
one.

**A MERGE COMMIT COMMITS THE INDEX, which is my own error and the one I would
repeat.** I regenerated `about.html` on disk, read its one-line diff, and never
`git add`ed it — only `EAM_STATUS.md`, because its conflict forced me to. So the
commit whose message describes fixing that value shipped the wrong one. `git
status` caught it; no gate had run yet. **Stage the regeneration in the same
breath as running it.**

**A RED SMOKE JOB HAS A GREEN LOG TAIL.** The job accumulates failures with
`|| status=1`, so every gate after the failing one still runs and prints, and
the last line of a failed run is a pass. I read the tail twice before working
that out. The failure was `build_history_page.py --check`: that page's job-count
tile is MEASURED from the worksheet's own `workflows[]`, and this change adds
one. **Reproduce a red run with the steward skill's battery, never by reading
the log.**

**And I had been running a SUBSET and calling it the full battery.** The PR body
said "full static battery green" when a dozen gates had never been run against
this change — `build_history_page` among them. `CLAUDE.md` records this exact
mistake from Michigan's go-live ("run the workflow's own command list, never a
remembered subset") and I made it anyway. The skill exists to be opened BEFORE
the first push.

What actually shipped is in #1127's body: the Chicago school board roster is a
weekly pipeline off the Board's own index instead of a hand-curated file, and
two of its twenty seats were wrong — District 9a said VACANT where the Board
names its Vice President, District 10b named a member who resigned in March.

**2026-09-23. Adam asked me to fix the school board one too. Following it to
the source found the seat is not vacant — #1127.**

`school-board-members.json` mapped district 17 to the bare string `VACANT`, the
third case of the shape #1125 fixed. **The Chicago Board of Education's own
member index names its VICE PRESIDENT in that seat**, Dr. Angel L. Velez, and
the file was wrong about a second one: district 20 named Olga Bautista, who the
Board's own news of 4 September says resigned in March and was succeeded by
Connie L. Anderson on 27 August. District 7 misspelled Karen Zaccor.

**The record said the drift was unavoidable and that claim was the defect.**
`sources.html` and the worksheet both said the roster is hand-curated "because
no machine-readable roster is published for this board". `cpsboe.org/about/bios`
publishes all 21 seats as an `<ol class="bios">` — `.name`, `.title` and
`.district` spans per member, each linked to a bio page carrying the same three
plus a `cps.edu` address. Nothing here had looked since the layer shipped.

**So the fix is a pipeline, not a corrected value.** Scraper, builder and a
weekly job on the pattern every other roster uses. The join is read off the
shipped geometry's own sub-district label, because the two publishers number the
same seats differently — the boundary 1..20, the Board 1A..10B — and a table
written down here would outlive a re-districting.

**ABSENCE IS NOT VACANCY, and the two sources are why that is a guard rather
than a comment.** CPS's own page listed twenty of twenty-one seats the same day,
with no row for District 10B at all — the seat Anderson holds. A district the
Board's index does not carry FAILS the build; only a seat the Board itself
prints as empty becomes `{vacant: true}`, on #1125's shared `is_vacancy_marker`.
That vacancy carries no role, unlike CCPSA's: there a role is the seat's
committee assignment, here it is an office the members elect one of their own
to, and an empty seat cannot hold the vice presidency.

**Four guards, each negative-tested to exit 1** — the two witnesses disagreeing,
a district named by nobody, a telephone number where a name goes, and a printed
vacancy shipping as a seat. The index is one block of repeating markup, so a
pattern that reads it wrongly reads all twenty-one wrongly and every count still
passes; that is what the per-member bio fetch buys.

**The card gained what the card order asks and it never had**: the Board's own
office from its published hCard, and its President in a `Citywide` section on
every card — he holds no district, and the Board says so with an EMPTY district
span rather than no span. It also stopped reading "Sub-district **District** 9a",
which it had done since the layer shipped.

**What I did not fix, measured rather than implied.**
`validate_officeholder_names.py` examines **1 of the 20** records in this file —
the Vice President, admitted only because his `role` trips the first shape arm.
The other nineteen are the flat-keyed blind class that gate's own docstring
already records, and the route out it names is a declared table of person-bearing
paths, not a wider predicate. What changed is that all twenty now go through
`why_not_a_name()` at WRITE time, weekly — the check a hand-curated file could
never have.

**One line for the manager**: the reader-facing half of this is that a person in
sub-district 9a has been told their seat is empty while the Board's Vice
President holds it, and a person in 10b has been given a member who left in
March. Both are fixed in #1127, which is open.

**2026-09-23. Adam took the VACANCY_SENTINELS question — #1125 fixes Logan and
CCPSA both, and the gate now refuses the word.**

**Removing the allowance would not have been enough, which is the part worth
keeping.** Every other rule in `why_not_a_name` passes `"VACANT"` happily — not
a party label, no digits, no `@`, has letters — so deleting the early return
would have left it accepted by silence. It takes an explicit refusal, and the
gate's own `SELFTEST` pinned the old answer and failed until flipped, which is
the test doing its job on the thing I changed.

**The shape is per source and both already existed.** Logan takes
`vacancies: 1` on the district — counted, never named, the posture its own
siblings ship. CCPSA takes `vacant: true` on the seat WITH its role, because
each council seats three under named roles and dropping the row would report a
two-member body the city seats three of; `build_officeholder_tables.py` already
renders that record as "Vacant" with no `Person` behind it.

**Both sources read live, robots first as each scraper's own client.** Logan
prints `DISTRICT 5 / MEMBER / VACANT` with none of the address, phone or e-mail
every other member carries. CCPSA prints the word where a name goes with the
seat's role beside it and an `a.see-more` to `ccpsa.chicago.gov/member/vacant/`
— which answers **200 with 51 KB**, a real profile page about nobody, and is
not carried.

**A builder was counting members where it meant seats.**
`build_logan_board_roster.py` failed on any district not holding exactly two
MEMBERS, so it would have refused to write the moment a seat emptied. Seats now,
with the contact floors measured against the named count.

**Verified:** both pipelines re-run end to end with no named person moving,
zero `Person` nodes named a sentinel across all 416 served pages (from three on
two), Logan's page reading "1 of 2 seats here is vacant", and three CCPSA cards
rendered in Chromium — the 3rd and 12th at "2 elected councilors · 1 vacant
seat", the 1st unchanged as the control.

**One thing recorded and not fixed:** `school-board-members.json` maps district
17 to the bare string `VACANT`, and the gate cannot see it at all — it examines
person-shaped DICTS, never a district-to-name-STRING roster. It reaches no page
as a person, because `build_officeholder_tables.py` converts it at read time.
That is a blind spot in the walker rather than the defect Adam named, so it is
written down here instead of widened into #1125.

**2026-09-22, stand-down. Nothing of mine is unpushed and no PR of mine is
open — confirmed, not assumed.**

Checked three ways: the working tree is clean on `main`; `scripts/sangamon_county_board_scraper.py`
is byte-identical between my branch and `origin/main`, with `PARSE_SELFTEST`
present; and `withCountyLibraryPhone` and `libraryDirectoryNote` are both in
the shipped `il/index.html`. The forty-odd `claude/*` branches still on this
checkout are squash-merged leftovers — their commits are not ancestors of main
by construction, which is what a squash merge does and is not unpushed work.
One PR is open fleet-wide, **#1103**, and it is another session's phone
card-list change, not mine.

**Three things landed.** #1096 (`a21c917`) stopped the Sangamon parser reading
the county's word for an empty seat as a person's name, with `PARSE_SELFTEST`
pinning both vacancy shapes before any fetch. #1093 merged as `b2799fd` after
the refresh I dispatched produced the right output, so both empty Sangamon
seats now ship as `{"members": [], "vacancies": 1}` and the `Person` node is
gone rather than renamed. #1098 (`031795b`) gave four county library cards the
state directory's telephone, joined on the comptroller code.

**The correction on `45a2c06` is the one worth carrying.** I had written that
CCPSA's two `Vacant` records stay inside the app card and reach no crawler.
They reach one: `build_officeholder_tables.py` puts that roster on
`il/police-district.html` as visible text and as `Person` nodes. Swept across
all 414 served pages, it is three nodes on two pages rather than one.
**My first measurement walked `data/app` and stopped there, which answers
where the strings are and not where a reader meets them** — and this project
built the generated pages precisely so those rosters would reach a crawler, so
the data files were the wrong boundary for a question about what gets
published.

**Read tomorrow, not tonight.** #1102 (`ecbff07`) gave 62 scheduled roster
workflows a `build_eam_status.py` step and `docs/EAM_STATUS.md` in their
`git add`, with `check_workflows()` gating it. Most of those 62 are Illinois's.
That closes the hole #1093 exposed from the other side: the refresh went red on
its own bot PR because Sangamon lost a member, the report's people count moved,
and no workflow rebuilt the file it counts.

**Still Adam's, not mine:** the fourteen Illinois asks, Ask 28 to the Will
County Clerk above all — the only route to unfreezing the municipal roster.
Not drafted around, and Will is not re-probed.

**2026-09-22. Both PRs merged, and the dispatched Sangamon run produced the
right shape — #1093 is yours to merge.**

#1096 (`a21c917`) and #1098 (`031795b`) are in. The dispatched refresh
(run 10, `workflow_dispatch` on `d96a08d`) finished green and force-pushed
`bot/sangamon-county-board-roster-update`, so **#1093's diff is now the fix's
output rather than the defect's.** Read against the refreshed diff, not
predicted:

- `sangamon-county-board-members.json` District 16 → `{"members": [],
  "sourceUrl": …, "vacancies": 1}`, byte-identical in shape to District 2.
- `il/county-board/sangamon.html` — the `Person` node is GONE rather than
  renamed. `ItemList` position 16 keeps its name and carries no `item`, which
  is the "a seat nobody is named for is still a list position" rule working,
  and the section renders **"1 of 1 seat here is vacant, as the county reports
  it."**
- Every derived count moved with it: `about.html` 3,644 → 3,643,
  `county-board.html` 1,108 → 1,107 and Sangamon 28 → 27 members, and the
  page's own title, description and lede 28 → 27.

The word `vacant` appears nowhere as a name in the diff. Nothing further on
this is mine.

**2026-09-22. #1096 merged; the Sangamon refresh is dispatched so #1093 does not
wait a week.**

Your row says #1093 "stays held only because its diff predates the fix" and
that its next run produces the right shape. **The next SCHEDULED run is Tuesday
15:00 UTC — seven days out**, and today's already happened, so #1093 would have
sat until then with a schema.org `Person` named `vacant` in its diff.
`update-sangamon-county-board-roster.yml` carries `workflow_dispatch`, and it
re-cuts `bot/sangamon-county-board-roster-update` from main's current tip and
force-pushes, refreshing the open PR rather than opening a second one — so I
dispatched it on `main` at `d96a08d`, which carries the fix. I did not touch
the bot branch: the bot pushes, through its own builder and `validate_index`
gate, and you still review the diff. Expected shape for District 16 on that
run: `{"members": [], "sourceUrl": …, "vacancies": 1}`, identical to District
2, and `il/county-board/sangamon.html` losing the `Person` node rather than
renaming it.

**On your withdrawal — the cause is the useful half and it generalises.** You
fetched `SOURCE_URL` where the scraper fetches `MEMBERS_URL = SOURCE_URL +
"/members"`. Both answer 200 with a large body, so nothing about the wrong
address looks wrong: the landing page simply has no member rows, and a regex
that matches none of them reads exactly like a regex that has stopped working.
The only tell is the byte count — 215,795 against the members index's 219,700.
**A page that answers 200 is not evidence you asked the right question of it**,
which is the same finding `probe_user_agents.py` records for 37 hosts probed at
a URL fragment. Worth carrying: when a measurement says a guard is inert, check
the address the CODE uses before the code itself — the scraper's own constant,
not the one a human would type.

**2026-09-22. The county library cards read L2 now — #1098, and the two
unverified items were both answerable.**

**Can a county path reach the statewide file at all? Yes, and the join key was
the only real question.** `loadIlLibraryOfficials()` and
`loadIlLibraryContacts()` are module-level cached loaders any path can call.
But **`il-library-contacts.json` carries no comptroller code** — it is keyed by
library name and holds `address`, `admin`, `city`, `phone`, `url` and nothing
else — so a direct code join was never available. The filing roster is the
bridge: `il-library-district-officials.json` carries a code on all 198 of its
records and is keyed the way L2 is, and 196 of its 198 names are in L2. All
four target codes resolve through it.

**What a Woodford card looked like, rendered.** IL Prairie: board, administration,
the filing note, then `Office / PO Box 770, Metamora IL 61548` — an address and
no telephone. Deer Creek had **no contact row at all**, because
`afrDistrictPeople` draws one only when the filing gives an address, a phone or
an e-mail and Deer Creek's office block is empty. So the fix adds a row on one
card and fills a row on the other.

**The shape is what you assumed, so it was built.** `withCountyLibraryPhone`
wraps the four entries that read their own county roster (Woodford, Grundy,
Kankakee, Peoria), joins on the comptroller code, and calls the SAME
`libraryDirectoryNote()` — lifted out of `withLibraryOfficials` unchanged, so
the rule has one copy. Nothing else ported.

**ONE DELIBERATE DIFFERENCE BETWEEN THE TWO PATHS, and it is the thing worth
your eye.** The statewide stamper applies the directory's telephone
UNCONDITIONALLY. Measured 2026-09-22, that is safe — 138 libraries publish a
telephone in both files and **all 138 agree digit for digit** — but it means the
statewide card shows "The telephone comes from the Illinois library systems'
shared directory" on cards whose own filing publishes the same number. The
county path stamps only where the filing gives none, so its note is never that.
I did not change the statewide path: it is outside this change's scope and the
displayed number is correct either way. Recorded below as a question.

**The re-measure turned up nothing new, and that is a result.** The four are the
whole set. **Ten more library cards in those counties have no telephone from
either publisher** — Woodford's Eureka; Grundy's Coal City, Fossil Ridge and
Three Rivers; Peoria's Brimfield and Dunlap; Kankakee's Bourbonnais, Bradley,
Edward Chipman and Manteno. Each files under a code
`il-library-district-officials.json` does not carry, and none appears in L2
under any spelling. A bounded absence in both statewide sources, not a failed
join.

**Verified in a browser on every shape**, including the two that must NOT change
(Carlock and Eureka keep their filing's number with no note). Kankakee's live
boundary was served from its own response bytes: **Chromium in this sandbox
cannot reach k3gis.net** — it does not use the agent proxy, the same
environmental limit `CLAUDE.md` records for the CDN — while `requests` through
the proxy reads the service fine (HTTP 200, 162,411 bytes, robots read first:
no robots.txt, 404, allow all).

**One comment corrected in the same change, because the new code's argument
rests on it.** The note over `loadIlLibraryContacts` said the file "carries only
what the Comptroller filings do not". That stopped being true on 2026-09-15,
when its builder began keeping the directory's copy wherever the two publishers
agree. Leaving a stale premise next to a function whose correctness depends on
the overlap existing is how the next reader gets it wrong.

**#1098 is on `claude/il-backlog-plan-9o2ew4-library-phone`, not the session's
own branch**, which still carries the open and unrelated Sangamon fix (#1096).
Putting this there would have widened that PR with work it is not about. Moved
on request.

**2026-09-22. Sangamon #1093 fixed as #1096 — and one of the three measurements
in the hold does not reproduce.**

**The fix.** `parse()` now drops a name matching `VACANT_RE` instead of
returning it, so District 16 takes District 2's path. Verified end to end: the
scraper writes `{"district": "16", "vacant": true, "url": ...}`, identical in
shape to District 2, and the builder turns both into
`{"members": [], "vacancies": 1}`. Every floor passes and none was lowered.
Reverting the one-line guard in a copy makes the new selftest fail, so the test
is proved to test the thing. Full static battery green plus the Illinois smoke
test. **#1093 should not merge until its branch is re-run on this.**

**CORRECTION — the index guard is LIVE, not dead.** The hold's defect (2) says
`INDEX_ROW_RE` matches **0 of 29 rows** and the corroborated-vacancy branch
could not fire. Measured today with the scraper's own client and headers,
robots read first (allowed, no crawl-delay, no Content-Signal): the index
answers 200 at 219,700 bytes, **`INDEX_ROW_RE` matches 29 of 29 rows**, and
`vacancies_from_index()` returns `{'2', '16'}`. The run prints
`index lists 2 vacant district(s): 2, 16`.

**#1093's own diff says the same thing from the other side**, which is the
stronger proof because it needs no fetch: District 2 stayed
`{"members": [], "vacancies": 1}` through that very run, and the ONLY branch
that can produce that key is the index one — the fallback drops the district
entirely. So the bot run the hold was written from had a working index guard,
and the 0-of-29 reading was taken some other way.

**What that changes for the fix:** `INDEX_ROW_RE` is NOT re-derived — rewriting
a regex that matches every row is how a working guard gets broken — and
District 16 lands on the **corroborated** branch rather than on District 2's
uncorroborated silent skip, which is a better outcome than the hold predicted.
The vacancy ships because two county sources agree, not because one went quiet.
The hold's third item, whether an unreadable index should stay a soft note, is
therefore not settled here: nothing has been observed reading it as unreadable,
so there is no measurement to settle it with.

**Defect (3) is on the board below rather than patched**, as instructed.

**A selftest, because a live run only tests this week's shapes.** The blank
vacancy shape had been exercised weekly since 2026-08-18 and said nothing about
the other one. `PARSE_SELFTEST` pins eight fixtures minimised from what the
county served today — both vacancy shapes, the three member-block shapes the
module docstring already records as having cost a rewrite, a case/inflection
pair, and a two-token name starting with the vacancy word so the guard cannot
later widen into a prefix test and take a real person off the board. Every
street in them is replaced with a placeholder: those are residences, and that
rule does not stop at a test fixture.

**2026-09-22. The phone half of the two-names row, measured — and it is NOT
the two surfaces disagreeing.**

**There is only ONE library layer.** `library-district` is county-dispatched;
`il-library-district-officials.json` (AFR) and `il-library-contacts.json` (L2)
are ROSTER files feeding it, not a second layer. So "which answer a reader gets
depends on which layer they toggle" is not the mechanism — what differs is
which roster a county's dispatch entry consults.

**Measured by the comptroller code, which is the key both files share** (a name
match is what made my first attempt unreliable): **26 county library cards
across the parcel-fabric counties; 4 lack a telephone that a statewide surface
has** — Kankakee's CENTRAL CITIZENS LIBRARY, and Woodford's Deer Creek, El Paso
and IL Prairie. **In all four the number comes from L2 and the AFR column is
empty on BOTH surfaces.**

**So the AFR route does not contradict itself.** It withholds the same values in
the county roster and the statewide one, which is the two-witness rule being
consistent rather than two publishers disagreeing. The whole difference is that
**the county-roster path does not read L2 at all** and the statewide path does.

**Recommendation, for the manager or Adam to take or refuse:** have the county
library cards read L2 as well, **labelled as the state library directory's**,
the way `build_county_board_offices.py` labels its ISBE-sourced addresses — a
second-hand number that reads as the district's own is the small lie that
precedent already names. It is four cards today and the lookup is by a code both
files carry. The alternative is to leave it, which costs a reader in Woodford a
published telephone that a reader elsewhere gets.

**What I have NOT verified, and would check before building:** how a Woodford
library card actually renders, and whether a county with its own roster file can
reach the statewide one at all. I measured the data behind the difference, not
the render path.

**2026-09-22. The two-names row, half answered and half deliberately left
open.** [#1080](https://github.com/ThursdaysFamous/districtry/pull/1080).

**The boundary name is the COUNTY's and is not to be changed.**
`woodford-library-districts.json` carries `IL Prairie Library District` with
code `LYIL`, out of Woodford County's own parcel fabric, and
`woodford-district-officials.json` joins on that string by design. The state
directory and the AFR filing call the same body `Illinois Prairie District
Public Library`. Same comptroller code, same PO Box 770, same head. **Two
publishers naming one body, so neither file is renamed** — which is the answer
the routed row asked for and the reason its own warning was right.

**#1077's docstring called it "Metamora Public Library District", which neither
publisher uses**, and that is mine: the manager supplied the name from the town
in the filing's address and I wrote it into code without checking it against a
key. #1080 replaces it, names the unit by its comptroller code, and records
the rule — cite a unit by the identifier both publishers share. **I also got
the check wrong twice**: I first reported the docstring clean because a
single-line grep missed a name wrapping across two lines, and the first
rewording said the bad name "appears nowhere in this repo" in the sentence that
put it there.

**THE PHONE HALF IS NOT ANSWERED AND I AM NOT GUESSING IT.** A quick join
across the three files reported no statewide phone for this very unit, which
#1079 demonstrably added — so the join is unreliable and no coverage figure is
offered. Whether the Woodford library card should take a telephone from the
statewide directory needs a join through the key the builders actually use,
which is more than a name match.

**2026-09-22. #1078 merged (`3cd68b2`) and verified on the merged tree** — the
docstring carries the library re-sample (40 of 198, all read, 2 filing an
extension: Illinois Prairie = `102/010/10` and Kewanee), the 77-unit combined
figure and the "a sample inherits its inventory's scope" line;
`comptroller_afr --selftest` and `validate_python_hygiene` pass there.

**TWO THINGS THE SAME NIGHT'S WEEKLY RUN SETTLED, neither of them mine to
push.** #1079 (`a482013`) is the first library-contacts refresh since #1066's
institution guard shipped, and the guard did exactly what it was priced to do:
L2 still publishes `Name: Atkinson Public Library / Title: Director`, the
refresh dropped `Ninette Carton` because the source genuinely no longer names
her, and **the institution did NOT take her place** — Atkinson's `admin` is
absent rather than wrong. That is #1066 working in production on its first
real run, at the cost it recorded in advance: an empty slot beats an
institution presented as a person.

**And Metamora's telephone came back by the other route.** The same run gives
Illinois Prairie District Public Library `(309) 921-5074` from L2 — the same
base number the AFR filing carries with `Ext: 101` and which `witnessed()`
correctly withholds for having one surname. So the reader loses nothing in the
end: the AFR route declines to publish a number no second filer corroborates,
and a source that names it as the LIBRARY's own supplies it instead. Worth
holding onto, because it is the case for the two-witness rule rather than
against it — withholding cost a reader nothing where another publisher stands
behind the same value.

**2026-09-22. My extension sample measured a population the case is not in.**
[#1078](https://github.com/ThursdaysFamous/districtry/pull/1078), correcting
#1077's own record.

`afr-special-districts.json` holds FIRE (323) and PARK (186) districts and NO
libraries, while Metamora is a LIBRARY district — so #1077's "0 filing an
extension anywhere" was a clean zero over a population the phenomenon does not
occur in, printed three paragraphs below the case it appears to answer for.
Accurate about what was measured, misleading about what it bears on, and the
manager caught it on merge rather than this session.

**Re-measured on the right population rather than caveated.** The shipped
library file carries 198 comptroller codes; 40 sampled, **all 40 read, 2 filing
an extension** — Illinois Prairie District Public Library, which IS 102/010/10,
the documented unit, and Kewanee Public Library District at
`(309) 853-3333 Ext: 1136`. So extensions occur at about 5% of library
districts and the first sample could not have seen one.

**The conclusion does not move**: 77 units read across both populations, 0
where stripping creates a witness the raw values deny. The structural argument
always settled it — stripping can only create a match, never break one — and
the sample only ever bounded how often the case arises. Nothing is relaxed.
The lesson is recorded with it: **a sample inherits its inventory's scope**.

**2026-09-22. The Metamora phone loss is Reddick's mirror image, and the task
row's premise held.** [#1077](https://github.com/ThursdaysFamous/districtry/pull/1077).

**Verified rather than taken from the row**, both years through the module's
own parser with robots read first as the scraper's own client: FY2025 carried
`(309) 367-4591` in all four slots, FY2026 carries `(309) 921-5074 Ext: 101` in
A, B and D against `(309) 645-0963` in C. **What the row did not say is that
the FILER SLOTS ARE IDENTICAL in both years** — Smith / Smith / Weddle / Smith
throughout. So Reddick kept one value and lost a signer; Metamora kept both
signers and filed new values. Exact opposites, which is a cleaner thing for the
next reader to hold than "a second shape", and it is what the docstring now
says.

**The extension question is measured and resolves FOR the current behaviour.**
Stripping at `Ext` can only CREATE a match, never break one, and the match it
creates — two surnames at different extensions of one base number — is stronger
evidence of a switchboard than an identical full number, which is what the rule
is trying to establish. Sampled 40 of the 509 units, each asked for its OWN
latest fiscal year: 37 read, **0 filing an extension anywhere, 0 manufactured
witnesses**. Stated as a sample, not the corpus. All 492 shipped phones on this
route carry no extension, because the split discards every one. **Nothing is
relaxed**: one surname is one surname.

**A trap that cost the first run and is recorded with it**: most units' latest
filing is not the current year. Asking all 60 of a first sample for FY2026
returned an empty contact block for 46, which reads exactly like "this unit
files nothing" and means "not that year" — 28 of the 37 later read were on
FY2025 and only 8 on FY2026. Ask `latest_fiscal_year()` per unit.

**2026-09-21. Three assigned tasks, three PRs, and the third answered a
different question than it was asked.**

**[#1066](https://github.com/ThursdaysFamous/districtry/pull/1066) — the L2
guard.** Verified the finding myself against the live source before building:
`librarylearning.org`'s Primary Administrator block for Atkinson reads
`Name: Atkinson Public Library`, `Title: Director`, `Ninette` nowhere on the
page. The rule was MEASURED against the 285 shipped administrators rather than
reasoned — equality alone does NOT catch it (the record key carries a trailing
`District` the name does not), prefix-or-suffix catches it and flags zero, and
`contains` also flags zero but is wider than the defect. Two tokens minimum,
because one cannot be told from a surname matching the town. It DROPS and
prints rather than failing the build, because the residual risk runs the other
way — a library named after a person (this dataset has Rick Warren Memorial)
could appoint a director sharing the namesake, and a false positive must cost
an empty slot, never a wrong name on a card. No exception entry.
**MERGED as `8d54ec4`, and verified on the merged tree rather than from the PR
body**: `institution_not_person` is at `scripts/build_il_library_contacts.py:109`
and its six-case `INSTITUTION_SELFTEST` passes there, catching the value L2
actually served and clearing all four false-positive cases. The builder takes a
scraped file, so it is not a CI gate — the selftest is what runs, and it runs on
every invocation ahead of argument parsing.

**[#1067](https://github.com/ThursdaysFamous/districtry/pull/1067) —
Plattville.** The trailing-token sweep found exactly ONE occurrence file-wide,
so no wider fix is owed. But the same bleed put two MORE false values on that
card: `info@kendalldems.net` — the county Democrats' address — as the village
office's e-mail, and the Illinois Department of Revenue's transfer-tax page as
its website. Three untrue statements, not one. The cause is
`kendall_municipal_officials_scraper.parse()` setting `in_section = True` and
never setting it back, so the LAST municipality alphabetically absorbs the
rest of the document. **The end-marker fix is deliberately NOT made**: choosing
one needs the document, Kendall blocks every rung including the Archive, and
nothing is cached — a guessed, untestable marker would swap a known defect for
an unknown one. The cause is written at the line that causes it. `ACCEPTED_NAMES`
is empty again.
**MERGED as `a981ff6` and verified on the merged tree**: Plattville's record now
carries head, office address and phone and NOTHING else — the `officers` array,
`office.email` and `url` are all gone, so a reader is told three fewer untrue
things. `ACCEPTED_NAMES` is empty with its reason written in, the Kendall
scraper carries the trailing-number refusal, and `validate_officeholder_names`,
`check_roster_retention` and `validate_index` all pass on main.

**The ILGA roster bot PR [#1063](https://github.com/ThursdaysFamous/districtry/pull/1063)
merged too, as `4887020`** — not this session's to merge, but verified on the
merged tree: `il-house-members.json` District 13 now reads `By appointment only`
/ `(773) 657-4655`, which is what ilga.gov serves today. The House roster is
current again for the first time since 2026-09-08.

**[#1068](https://github.com/ThursdaysFamous/districtry/pull/1068) — Reddick
Fire, and the caveat closes on neither branch it offered.** Read both filings
through the module's own parser: **FY2026 is not sparser.** It carries
`210 E MAIN ST` in all four slots and `(815) 365-4911` in all four. What
changed is WHO SIGNED — FY2025's slot B was ROBERT LOWERY against SUE BERGAN
in the other three; FY2026 is SUE BERGAN in all four. `witnessed()` ships a
value only where two differently-surnamed filers gave it, so nothing has a
second witness and nothing ships. **The roster is right and the builder is
working.** Not relaxed: these slots routinely carry the FILER's own office
(Reddick's filed e-mail is an outside accountant's), and the FY2026 filing
disagrees with itself on the ZIP. No data changed; the measurement landed in
`witnessed()`'s docstring so the next person to find an AFR address missing
has the cause and the counter-argument in hand.
**MERGED as `62dd6bf` and verified on the merged tree**: `witnessed()`'s docstring
on main carries the whole measurement — the FY2025 slot-B LOWERY against BERGAN,
the FY2026 all-BERGAN form, the accountant's e-mail domain and the filing's own
ZIP disagreement — and `comptroller_afr --selftest` passes there. No data moved,
which was the point: the roster was already right.

**ALL THREE ASSIGNED TASKS ARE MERGED AND VERIFIED** — #1066 `8d54ec4`,
#1067 `a981ff6`, #1068 `62dd6bf` — each checked on the merged tree rather than
from its PR body. Two of this session's later PRs, #1073 and #1074, remain open
and green.

**The General Assembly roster row is answered, and answering it found a second
thing.** `update-ilga-roster.yml` ran today at 18:24 UTC and SUCCEEDED — its
first green run since 09-14, so the 09-18 fix holds. It opened bot PR
[#1063](https://github.com/ThursdaysFamous/districtry/pull/1063), one changed
block, which I verified against the live page rather than from the diff:
`5025 N. Broadway` and `348-3434` occur ZERO times on ilga.gov today and
`By appointment only` and `657-4655` occur once each, so Rep. Hoan Huynh's
District 13 office really has moved to appointment-only. **The Senate half did
not change at all**, which is why `il-senate-members.json` still dates to
09-02; that is the source standing still, not the job failing. #1063 is a
roster PR and wants a human read before it merges.

**[#1072](https://github.com/ThursdaysFamous/districtry/pull/1072) — what that
verification turned up.** `ilga_scraper.py` had NO reference to robots.txt, and
ilga.gov asks for `Crawl-delay: 10` while the scraper ran at 0.5s across one
page per member. **The delay sits in the SECOND of two `User-agent: *` groups**,
split by a Googlebot group — the half `urllib.robotparser` drops, which is the
shape `scripts/robots_policy.py` was written for, so this is that reader earning
its keep on a live host rather than a fixture. Two traps are recorded with it:
adding the gate naively would have shut the scraper off ENTIRELY, because
`RobotsGate` reads through the session it is handed and this host omits its
intermediate, so the TLS failure reads as disallow-all — in CI too, with a
reason naming policy rather than TLS; and the module docstring's
`REQUESTS_CA_BUNDLE` warning was one variable short, since requests reads
`CURL_CA_BUNDLE` next and this sandbox sets both. The cheaper route was measured
and is closed: the sitemap carries no `lastmod` and lists no member page, so a
conditional crawl cannot be built. **The cost is real and is Adam's to refuse:
the weekly job goes from ~3.5 minutes to ~32.**
**MERGED as `2cea459` at 20:23 UTC, and verified on the merged tree rather than
from the PR body**: a real paced scrape of two Senate members runs end to end in
21.7s — three requests, two 10s gaps — reading `robots.txt served (610 bytes):
no rule in 2 binding group(s) matches`, pacing at 10.0s, and both records
parsing with their Springfield and district offices. `validate_python_hygiene`,
`probe_user_agents --check`, `validate_gate_counts` and
`validate_steward_mirror` all pass on main, and the gate pair is unmoved at
68/95 because the change adds no gate. **The next scheduled run, Monday
2026-09-28, is the first at the new pace and the first real test of the ~32
minutes** — if it is going to time out or collide with anything, that is when.

**[#1073](https://github.com/ThursdaysFamous/districtry/pull/1073) — the skill
edit the classifier had been refusing went through.** `.claude/skills/
municipal-officials/SKILL.md` said `REQUIRED_COUNTIES` was "Cook and Will only"
in one place and that the build step's `if:` "stays Cook-and-Will only" in
another; main says `("Cook",)` and `steps.scrape_cook.outcome == 'success'`.
An agent following it would have re-made the exact failure #1043 retired. The
workflow literal is now quoted rather than paraphrased, so the sentence is
checkable in one grep. **No gate is added and that is argued rather than
assumed**: `validate_skills.py` resolves POINTERS, so it catches a renamed
constant and cannot catch a changed one, and across the eleven skills the shape
that failed here is essentially this one sentence — a prose-parsing gate would
be a seventh hand-kept reader of a fact the code already owns. If Adam wants it
anyway I will build it.
**MERGED as `d6e9288` and verified on the merged tree**: both corrected claims
are on main and both still match the code they describe — line 137 against
`REQUIRED_COUNTIES = ("Cook",)` at `build_municipal_officials_roster.py:416`,
and line 183 against `if: steps.scrape_cook.outcome == 'success'` at
`update-municipal-officials.yml:605`. `validate_skills.py` passes with 11
skills and 772 pointers. **The skill edit #1043 flagged on 2026-09-19 and the
classifier refused is now closed**, and the second claim quotes the workflow's
literal, so a reader can re-check that sentence in one grep.

**[#1074](https://github.com/ThursdaysFamous/districtry/pull/1074) — the "2 of 64
board cards name no office" row is now an ask rather than an open question.**
Clinton and Franklin are the two, and the gap's `blocker` recorded NO ASK STATE
while `docs/ASK_DRAFTS.md` held nothing for either county — an empty blocker on
a gap whose only route left is an ask. Re-probed both board pages first, robots
read as the scrapers' own client: **Clinton answers 200 in 74,904 bytes with no
street address anywhere**, and Franklin's only non-residential address is
`100 Public Square, Benton` in the SITE-WIDE FOOTER beside the county's general
phone, which the attribute-it-in-words rule already on this gap correctly
declines. **What is new is a disagreement** — the state's directory records
Franklin's Clerk at `901 Public Square`, a different number on the same street —
so Franklin's ask is NARROW (which of the two is the building) where Clinton's
is open, and a narrow ask is likelier to be answered. Nothing is shipped from
inference: the clerk street in this repo is the CLERK'S office for both and no
source says the board sits there. **The Franklin home addresses were already
recorded on 2026-09-04 and the scraper asserts the payload address-free before
writing** — I raised it as a possible leak and it was measured and refused long
before I looked. Ask 29 is DRAFTED and held; Adam sends.
**MERGED as `a660e6d` and verified on the merged tree**: Ask 29 is at
`docs/ASK_DRAFTS.md:2250` carrying both Clerk addresses, and the gap's blocker
decodes cleanly with the re-probe, the 901-against-100 disagreement and
`NOT YET ASKED — DRAFTED as Ask 29` all present. `build_coverage_gaps --check`,
`build_county_status --check` and `validate_index` pass, and the shipped
`coverage-gaps.json` is unchanged, which is what a blocker-only edit should do.

**THE OPEN-PR QUEUE IS EMPTY.** Five PRs this session, all merged and each
verified on the merged tree rather than from its own body: #1066 `8d54ec4`,
#1067 `a981ff6`, #1068 `62dd6bf`, #1072 `2cea459`, #1073 `d6e9288`,
#1074 `a660e6d` — six with the bot roster PR #1063 `4887020`, which was not
this session's to merge but was verified against the live page before it went.
Check-ins stopped.

**What Illinois is waiting on is Adam, not this session.** Fourteen drafted
asks sit unsent — the thirteen already listed below plus Ask 29 — and the
Hancock ask still blocks the one county whose weekly run will keep re-proposing
the same three edits until the county answers. **Ask 28, to the Will County
Clerk, is the one with a consequence today**: it is the only route to
unfreezing the municipal roster.

**One thing to watch with no owner**: the next `update-ilga-roster.yml` run is
Monday 2026-09-28, the first at the 10s crawl delay — about 32 minutes against
3.5. No `timeout-minutes` is set so it has 360 minutes of headroom, but that
run is where a timeout or a collision would show.

**On the recurring Hancock churn, since it was asked for.** The weekly run will
keep re-proposing the same three edits against the reverted file until the
county answers, because the page is what it reads and the page is what is
wrong. Options I can see: leave it and re-hold weekly (costs a review each
week, keeps the signal); add Hancock to a preserve list so the roster carries
forward and the job stops proposing (silences a real source change, and this
county is not blocked, so it would be the wrong instrument); or gate the
builder on the county's own certified candidate database, which has no
District 4 Mason and no board contest for Billy Cramer. **I would leave it and
re-hold**, because the churn is one review a week and the alternatives either
hide a real change or build a second reader of a question the ask will settle.
It is Adam's ask to send.


**2026-09-19, 16:45. #1018: THE PARSER IS NOT AT FAULT, AND THE PREMISE IN THE
TASK ROW IS WRONG.** The row reads "the page moved under the parser". It did
not. Measured, with robots read first through `robots_policy.py` as the
scraper's own client (allowed, no crawl delay, no Content-Signal):

- Running `hancock_county_board_scraper.py` against the live page reproduces
  the bot PR **exactly** — 5 districts, 15 members, twelve names unchanged.
- The page itself prints **`Jo0n Mason (R)`**, one occurrence. The zero is the
  COUNTY'S OWN TYPO, not a corruption this repo introduced.
- `Josh Turner` and `Alex Blythe` appear **zero times** on the page. So these
  are two genuine roster changes, not a mis-association.
- The parser reads one `<li>` per member. There is no column association to
  slip, which is what makes this NOT the Rock Island shape.

**`ACCEPTED_NAMES` IS RULED OUT BY ITS OWN RULE.** That table's docstring says
in terms: "NEITHER REASON IS 'the source publishes it that way'." This is
exactly that, so an entry there would be the one thing it forbids.

**THE CERTIFIED RETURNS DEEPEN IT RATHER THAN SETTLING IT.** Hancock's own
results database (`electionstats.hancockcounty-il.gov`, `/candidates/search/`,
param `name`) says: Billy Cramer has **no county board contest ever** — he is a
Pilot Grove Township trustee, 2021 and 2025. No Mason has run in District 4;
Kelly Mason ran in District **1** in 2024. And **Joshua L. Turner won the 2026
District 4 Republican primary**, so the man the page just dropped is its
nominee for November.

That is consistent with two mid-term APPOINTMENTS, which no election record
would ever show — and it is equally consistent with the county having edited
its page wrongly. **The returns cannot distinguish those two**, which is
precisely why this needs the county rather than more inference.

**So nothing ships and #1018 stays held.** Shipping `John Mason` guesses at a
real person's name; `Jo0n Mason` is refused by the merged name gate and is a
typo either way; `Josh Turner` would name someone the county no longer lists.
The route is an ask to `elections@hancockcounty-il.gov` — the address the
county publishes — on two questions: the District 4 member's correct name, and
whether Billy Cramer holds District 2. **Drafted next; Adam sends, never this
session.**

**2026-09-19, 16:20.** THE FREEZE IS OVER, PROVED BY A RUN RATHER THAN BY THE
DIFF. #1043 is green, and the municipal workflow dispatched by hand against its
branch (run 35453832897) succeeded at 16:15 — but success is what that workflow
reported for eleven days while refusing to build, so the log is the evidence
and not the conclusion. It shows the build step running, the roster changing,
and a bot PR opening:
[#1044](https://github.com/ThursdaysFamous/districtry/pull/1044), 328
insertions and 155 deletions.

Its body carries the line this change existed to produce:

    PRESERVED (blocked this run, carried forward from the shipped roster):
    joliet 1, kendall 6, logan 11, mchenry 27, will 31

**`will 31` — the exact count measured before the change.** Diffed entry by
entry against main: 629 municipalities before and after, none dropped, **48
changed across five counties** — DuPage 17, Rock Island 15, Livingston 14,
Mason 1, Kendall 1. Will, McHenry and Logan each show **0 changed**, which is
preservation doing precisely what was claimed for it.

**The one entry that looked like a counter-example is not.** Kendall is
preserved and yet one of its six municipalities moved: Plano's `board` went
from `null` to eight named aldermen with a city e-mail each. That is the
`--enrich` path, not the county path — Plano's own city payload runs fresh and
can only FILL a field the county left empty. Kendall's six county entries were
carried forward untouched. A preserved county's data was never rewritten;
checking that specifically is what turns the safety argument into a
measurement.

**2026-09-19, afternoon.** [#1043](https://github.com/ThursdaysFamous/districtry/pull/1043)
opens: Will moves from `REQUIRED_COUNTIES` to `PRESERVABLE`, so the municipal
roster refreshes again for the first time since 8 September. Adam approved it
directly. 14 gates pass.

**What a reader gets back:** 36 counties' mayors, presidents and council
members start being rechecked weekly again. They had been eleven days stale
because Will's Clerk moved its directory behind a managed challenge and Will
was one of two counties the builder refused to build without — so every weekly
run scraped all 37 sources, skipped the build on Will alone, and reported
success. Nothing went red for eleven days.

**What a reader loses, and it is said on the card's own gap record rather than
here:** Will's own 31 towns now carry forward indefinitely. A trustee who
changes will not change here, and no count floor will notice, because all 31
municipalities remain. The gap's `area` narrows from "every Illinois town card"
to Will County alone, because the wider claim stopped being true.

**The measurement, in case it is questioned later:** the comment that held Will
in `REQUIRED_COUNTIES` described building WITHOUT a full-body county and was
applied to PRESERVING one. Preserved entries re-enter through the same
`absorb()` -> `pick_entry`, which sorts on depth then `COUNTY_PRECEDENCE`, so
order cannot demote anything. All 31 Will entries are at maximum depth and Will
ranks second behind Cook, so its 28 straddles resolve exactly as they do today
— the six it loses to Cook it already loses.

**Owed and not paid:** `.claude/skills/municipal-officials/SKILL.md` still says
`REQUIRED_COUNTIES` is "Cook and Will only", in the body and in its Nevers.
Every edit to that file was refused by this environment's permission
classifier, so it is stale and flagged rather than quietly skipped.
`validate_skills.py` cannot catch it — it checks that a named path or
identifier exists, not that the prose is true. It needs one line from a session
that can write the file.

**Next:** #1018's cause (Hancock's `Jo0n Mason`, never hand-corrected), then
Marshall's weekly job, whose fix merged in #968 after its last failing run, so
the honest state is "fixed, unproven" until it next fires.

**2026-09-19, end of the evening.** Pausing here. Main is `8506c8c`. Three
Illinois changes merged tonight — #1024 (Rock Island's 112 fabricated names),
#1028 (Bartonville's phantom Clerk) and #1030 (the six workflows) — alongside
#1031, #1025 and #1023.

**No reader is seeing Hancock's corrupted name.** Checked on main: the shipped
`hancock-county-board-members.json` names all fifteen members correctly,
`Josh Turner` and `Alex Blythe` among them. The corruption exists only in the
held bot PR #1018, which is the hold working.

**Next thing I would pick up: the cause behind #1018.** The merged name gate
answers `digits in it` for `Jo0n Mason`, so rebasing that PR turns it red, which
is the gate doing its job and not the question. The question is what
`hancockcounty-il.gov` is serving now. Two simultaneous name changes on a
fifteen-seat board, one of them with a zero where an `h` belongs, reads like the
page moved under the parser rather than like two members being replaced — so
`Alex Blythe` → `Billy Cramer` is suspect for the same reason, and `Billy Cramer`
passes every gate we have. The builder's only drift guard is the member count,
five districts of three, which a mis-associated parse satisfies exactly. This is
the Rock Island shape again and it wants the parser diagnosed, never `Jo0n`
hand-corrected to `John`: if the parse slipped, the surname is as suspect as the
given name, and repairing a guess produces a more convincing guess.

**2026-09-19, later still.** #1030 merged (`5338913`), so both Illinois PRs are
in and nothing from this session is in review. Verified on main: all six roster
workflows now run **zero** shared-page generators before the branch cut and run
them after, every checkout carries `fetch-depth: 0`, and all 131 workflow files
parse. Wisconsin's equivalent (#1031) landed straight after.

What this fixes for a reader is indirect but real: those six weekly jobs were
dying whenever another workflow merged a shared page mid-crawl, and a job that
dies opens no pull request, so the roster it refreshes silently stayed frozen.
It also stops every bot roster PR rewriting all 243 sitemap dates — the shallow
checkout made every page claim it changed that day.

**2026-09-19, later.** #1028 merged (`d450c52`). Verified on main: 4,332 person
records in `il/data/app/municipal-officials.json`, **zero** that fail
`fabricated_name`, and the string `clerk@bartonville.org` appears nowhere in
the file. Bartonville's phantom second Clerk is gone from what a reader
downloads.

**The #1025 collision predicted below is now live and measured.** Running that
branch's `validate_officeholder_names.py` against merged main:

    validate_officeholder_names: FAIL
      - ACCEPTED_NAMES excuses '’s Email: clerk@bartonville.org' in
        il/data/app/municipal-officials.json and that value is no longer there
        — stale, remove it

That is the gate working exactly as designed: an exception cannot outlive the
fix that retires it. The fix is to delete that one `ACCEPTED_NAMES` entry from
#1025 before it merges; its Plattville entry stays, because `Beth Fals 56` is
still shipping. I have told the NYC/SF session and have not touched their
branch.

**2026-09-19.** Nothing in progress. Both Illinois PRs are in review and green,
and I am not opening a third until they land or Adam picks the next item.

**#1025 and #1028 collide, and git shows no conflict because they touch
different files.** #1025 records Bartonville's `’s Email: clerk@bartonville.org`
in `ACCEPTED_NAMES`, and its `audit_accepted()` fails when an excused value is
no longer in the file — "stale, remove it". #1028 removes exactly that value.
So merging both, in either order, leaves main failing
`validate_officeholder_names.py` until that one entry is deleted. Simplest
order is #1028 first, then drop the Bartonville entry from #1025 before it
merges. I can make that edit on #1025's branch if the NYC/SF session would
rather not.

**Correction to the Tasks table:** `ACCEPTED_NAMES` is not on main — it arrives
with #1025. Plattville's `Beth Fals 56` is held nowhere today; it is simply
shipping, and has been since 2026-08-01.

**What a reader is missing right now**, in order of how many people it reaches:

- **Municipal officials are eleven days old.** The roster naming the mayors,
  presidents and council members of 37 counties' cities and villages last
  rebuilt on 2026-09-08. Will County is one of two counties the builder refuses
  to build without, and its directory sits behind a vendor managed challenge we
  do not work around. Every weekly run scrapes the other sources, refuses the
  build, and reports success, so nothing goes red. Ask 28 is the only route and
  it is drafted, unsent.
- **Logan County's 11 municipalities and 65 officials are frozen** by that
  county's own robots.txt, which disallows the directory the Clerk's yearbook
  sits in (#1027). Compliance, not an outage — the check re-runs weekly and
  resumes on its own if the policy changes. Ask 23 is drafted, unsent.
- ~~**The General Assembly roster has not refreshed since 2026-09-08**~~ —
  **ANSWERED 2026-09-21.** The workflow ran green today and opened #1063, which
  is verified against the live page and waiting on a human read. The Senate file
  is unchanged because the Senate pages are unchanged.
- ~~**`il/county-board/logan.html` names a member `VACANT`**~~ — **FIXED
  2026-09-23 as #1125**, with CCPSA's two on `il/police-district.html`. The
  word is refused by the name gate now, so it cannot ship as a person from any
  roster in the fleet.

Nothing else on the Illinois map is known to be wrong. The coverage ring checks
out at five rings with all 93 inside and 10 outside anchors correct; 62 of the
64 districted board cards name an office; 83 county pages name 1,108 board
members; 55 counties have their precincts drawn.

**Stale record found, not yet fixed.** `docs/ASK_DRAFTS.md` Ask 12 still lists
Christian County as owing a second follow-up about which precinct Taylorville 9
was carved from. That question was answered on 2026-09-15 by the county's own
registration counts and Christian has shipped, so the row should read OVERTAKEN
the way Knox's already does. The same file and the Christian gap record also
disagree on the clerk's first name — Jodie in the drafts, Kandi in the
guidebook — and neither is guessed at.

## Open questions for Adam

- **2026-09-26 — 19 library cards name no trustee and no gap record covers
  them. Not blocking; it is a scope call, and I would write the record.** The
  measurement is in Status above. `statewide-library-officials` now correctly
  says 226 of 373 on the statewide route, and that correctness is what exposes
  this: the 19 counties that dispatch their own library entry are outside every
  library gap record there is, so a reader in Yorkville or Blue Mound is told
  nothing about an absence the app has.

  **(i) Write one gap record for the 19, which I would do.** It is a day's work
  at most: the population is derived from the dispatch table the same way the
  corrected record's is, so it cannot go stale by hand, and `counties` would
  carry the five so `COUNTY_STATUS.md` names them. Its `blocker` would state the
  Kendall nuance — four of those nine are Kane and Will districts reaching into
  Kendall, so the record must not claim they are unnamed everywhere until that
  is checked. Cost: one more record on a panel that already carries 104.
  **(ii) Extend `statewide-library-officials` to all 91 counties instead.** I
  would not: its numerator is the two statewide rosters, the other 19 counties'
  people come from three further files, and one record whose denominator mixes
  four sources is how 382 happened.
  **(iii) Chase the trustees first and record only what stays open.** Honest,
  but it leaves the absence unstated for however long the chase takes, and the
  chase is the larger job.

  I would take (i) and treat any trustees found afterwards as narrowing it.


- **2026-09-25 — ISBE refuses this project, so the county-clerk roster has no
  route and 46 precinct layers have no statewide tripwire. BLOCKING for the
  precinct half; the clerk half needs a decision, not a blocker.** The measurement
  and what #1150 already does are in Status above. Two things are left open.

  **(a) `il-county-clerks.json` has no refresh any more.** The weekly job stops at
  the gate, and the 101 clerks it last read are preserved and carried forward, so
  no reader loses an answer — but the file is now as current as its last
  successful run and will drift as clerks turn over. Three courses.
  **(i) Ask ISBE.** Their robots.txt is a blanket `Disallow: /` with no group for
  anyone, which is the shape a site publishes without thinking about civic reuse
  rather than one aimed at us; a short note asking whether a named group could be
  added, or the directory offered as a download, is exactly the ask route this
  project already runs with clerks. It costs one e-mail and it is the only course
  that reopens the whole host, including the precinct tripwire. **I would take
  this, and I would draft it and hold it — nothing is sent by a session.**
  **(ii) Rebuild the roster from the 102 counties' own clerk pages**, which this
  repo already reaches for other facts. Real work, and it trades one refusing host
  for 102 that mostly permit. **(iii) Let it stand** on the preserved records with
  a dated note. Honest, and it decays.

  **(b) The precinct tripwire needs a smaller replacement, and I would build it.**
  38 of Illinois's 46 shipped precinct layers are dissolved from Census 2020
  voting districts; a county clerk consolidates whenever a clerk decides to, and
  as of today nothing detects it. The three results vendors carry 34, 13 and 17
  counties between them, so a vendor-side comparison covers a real fraction rather
  than all 102 — worth building, and worth stating on the coverage record that the
  counties no vendor carries have **no** drift detection at all rather than
  letting the old "ISBE covers everything" sentence stand. This is the largest
  correctness exposure Illinois has right now: a precinct card can be silently
  wrong and no gate in the repo would know.

- **ANSWERED 2026-09-25 by the manager (`d9939c0`): take (a), and the surface
  fix is mine in its own PR, landing separately from the rows. It also retired
  its own brief — the defect is the instrument reading `<tag>/WATCH.md` for every
  state, not Illinois lacking a file.** Kept below as the record of what was
  measured and offered.

- **2026-09-25 — where Illinois's watch plan goes, and one fleet-wide
  measurement fault it exposed. Neither is blocking; both want a yes before I
  write the file.** Stage 1 of the assignment is in Status above.

  **(1) The assignment says `il/WATCH.md`; three skills say that file must not
  exist.** `expand/SKILL.md` names it as a path Illinois deliberately does not
  have, `new-layer/SKILL.md` and `boundary-change/SKILL.md` both send an
  Illinois row to the ROOT `WATCH.md`, and `validate_skills.py` treats a path a
  skill names in order to say it is absent as the warning it is. The root file
  is a real dated calendar and calls itself CHI's. Three courses:
  **(a) extend the root file with the eleven class rows and teach
  `build_eam_status.py` that Illinois's watch file is the root one** — one line
  in the instrument (`docs` is already `.` for Illinois in
  `generate_metro_files.INSTANCES`, so the convention is expressible), eleven
  rows, nothing contradicted; **(b) create `il/WATCH.md`** — satisfies the
  instrument untouched and leaves Illinois with two watch calendars and three
  skills pointing at the other one, which is the two-readers-of-one-question
  defect this repo has paid for repeatedly; **(c) move the root file to
  `il/WATCH.md`** — one calendar again, but it contradicts the root-instance
  convention that also governs `metro-worksheet.json`, `CLAUDE.md`, `README.md`
  and `scripts/`, and needs three skills plus `validate_doc_counts.py` changed
  in the same breath for no reader-visible gain. **I would take (a).**

  **(2) The M bar's file surface misses most of the fleet's per-county files,
  and Wisconsin's number is the one most wrong.** `build_eam_status.py` counts a
  data file as part of an instance's surface when its basename appears literally
  in that instance's `index.html`. Every instance fetches its per-county files
  through a built URL instead (`"data/app/" + slug + "-county-outline.json"` and
  friends), so measured today: **il misses 86 of 388, wi misses 215 of 262, ia
  24 of 57, mi 31 of 53, ny 5, ca 1 — and in every instance 100% of the missed
  files are named in that instance's `sw.js`**, whose URL lists are generated
  from the worksheet. So the fix is to read the surface from the generated list
  rather than from a regex over the app, and it needs no new file and no new
  convention. **It will move four instances' published M column**, Wisconsin's
  from 47 files measured to 262 plus its rosters — its "25 without a job" is
  measured on 18% of its own data directory. **I would fix it in the same PR as
  (1)**, because it is a root fleet script and Illinois runs from root, and
  because leaving it means Illinois's own plan is written against a denominator
  we know is wrong. Say otherwise and I will leave the instrument alone and note
  the fault instead.

- **The statewide library card credits the directory for a number the filing
  also publishes, on up to 138 cards.** `withLibraryOfficials` applies L2's
  telephone unconditionally and then prints "The telephone comes from the
  Illinois library systems' shared directory." Measured 2026-09-22, the two
  publishers agree digit for digit on all 138 libraries that carry one in both
  files, so **no card shows a wrong number** — this is about what the note
  claims, not about the value. A reader can fairly take that sentence to mean
  the filing did not have it. **Three courses, none taken:** leave it (the note
  names where the displayed value came from, which is literally true); stamp
  only into a gap, as #1098's county path now does, which makes the note mean
  the narrower thing on every card in the layer; or reword it. I did not pick
  one, because the statewide path was outside #1098's scope and changing a
  sentence on ~138 shipped cards is not a side effect to take on unasked. The
  address has the same shape and was not measured.
- **Deer Creek's card now names a telephone and no address, where the directory
  publishes both.** That is the stated scope of #1098 working exactly as asked
  — telephone only, no addresses — and it is worth seeing once before deciding
  whether the address should follow. The directory has `205 East First Avenue
  Post Office Box 347, Deer Creek` for it and the filing has nothing.

- ~~**A `Person` named `VACANT` is live on `il/county-board/logan.html`**~~ —
  **ANSWERED 2026-09-23. Adam: "fix the VACANCY_SENTINELS thing — Logan and
  CCPSA both."** Built as #1125. `why_not_a_name` REFUSES the word now rather
  than allowing it, both rosters record the fact structurally (`vacancies: 1`
  on Logan's district, `vacant: true` with its role on CCPSA's seat), and the
  two scrapers convert on one shared `is_vacancy_marker` instead of each
  carrying a copy of the table. Zero `Person` nodes named a sentinel across all
  416 served pages, down from three on two.

- **Deer Creek's card now names a telephone and no address, where the directory
  publishes both.** That is the stated scope of #1098 working exactly as asked
  — telephone only, no addresses — and it is worth seeing once before deciding
  whether the address should follow. The directory has `205 East First Avenue
  Post Office Box 347, Deer Creek` for it and the filing has nothing.

- **A `Person` named `VACANT` is already live on `il/county-board/logan.html`,
  and the gate that should catch it is the one #1093 asked about.**
  `VACANCY_SENTINELS` in `scripts/validate_officeholder_names.py` returns None
  for `vacant`, `vacancy`, `tbd`, `none`, `open` and five more, so the word
  passes as a name. The hold on #1093 called that "right for Wisconsin's
  marker-shaped roster and blind to Illinois's structural one", and **measured
  fleet-wide today, that is the wrong way round.** Nothing in Wisconsin uses the
  marker shape at all: its vacancies are structural (`vacant: true` on 15
  `county-board-members` records and one school-board record, plus 16
  `withheld`). The only three records in the fleet that put the word where a
  name goes are **Illinois's** — `logan-county-board-members.json` District 5,
  and two in `ccpsa-district-councils.json` — and NEITHER pipeline mentions the
  word anywhere, so in both cases it is the source's string carried straight
  through as if it were a person, which is exactly the defect #1096 just fixed
  in Sangamon. Illinois's own structural shape is in six files
  (`vacancies: N` in Sangamon, Boone, Jo Daviess, Lee, Stephenson;
  `vacant: true` in Shelby). **Consequence a reader gets today:** Logan's page
  carries `"@type": "Person", "name": "VACANT"` in its schema.org graph and a
  member row reading `VACANT`, published. **CORRECTED 2026-09-22 — I said
  CCPSA's two "render in the app card rather than in served bytes, so they do
  not reach a crawler". They reach one.** `build_officeholder_tables.py` puts
  that roster on `il/police-district.html`, where both appear as `Person` nodes
  in the ld+json AND as visible text. Swept across all 414 served pages'
  ld+json: **two pages, three such nodes** — Logan's `VACANT` and
  police-district.html's two `Vacant`. My first measurement walked `data/app`
  and stopped there, which answered where the STRINGS are and not where a
  reader meets them; the generated pages are a second surface and this project
  built them precisely so those rosters would reach a crawler.
  **The proposal, not applied:** drop the sentinel allowance, convert those
  three records to the structural shape their siblings already use, and let the
  gate reject the word outright — which would make it impossible to ship this
  again anywhere in the fleet. **Not done unilaterally** because it edits a
  shared gate and two rosters this session was not asked to touch, and because
  the Logan and CCPSA sources should be read before their records are reshaped
  rather than after. Say the word and it is one change.

- **Thirteen Illinois asks are drafted and waiting on you to send them** — Asks
  2, 9, 10, 11, 13, 16, 18, 19, 21, 23, 26, 27 and 28 in `docs/ASK_DRAFTS.md`,
  of which 18 and 19 you deliberately held. **Ask 28, to the Will County Clerk,
  is the one with a consequence today**: it is the only route to unfreezing the
  municipal roster above.
- **Two second follow-ups are past due** (Ask 12): Ford and Piatt, each asked
  3 August with one follow-up spent on 16 August. Christian's row in that table
  is overtaken and Knox's already says do not send.
- **Bureau County wants $150 and a licence whose terms forbid republishing what
  we would build with it.** Ask 9 asks for modified permission and offers the
  free fallback in the same note. Purchases are yours alone; nothing has been
  spent and nothing is queued.
