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
| **Illinois is the only instance in the fleet with no `WATCH.md`, and 221 of its 310 shipped files are under no plan — MEASURE AND REPORT FIRST** | **assigned 2026-09-25, DO FIRST** | 2026-09-25 | **Measured on main today from `docs/EAM_STATUS.md`: il reads `EA·` with 221 of 310 app-referenced files under no job and no watcher; wi is 25 of 47, ia 16 of 33, mi 14 of 22. And `ca/`, `ny/`, `wi/`, `ia/` and `mi/` all ship a `WATCH.md`. `il/` does not exist.** So the deepest instance in the fleet — 102 counties examined, 572 districts, every one answered — is the only one with nowhere to state when a shipped file is next re-checked, and it carries eight times Wisconsin's backlog of unplanned files. **This is Illinois's M bar and nothing else on your board comes near it in size.** Adam's ruling when he widened that bar is what makes it tractable: **a dated `WATCH.md` row naming a file and stating WHEN it is re-checked satisfies MAINTAINED** — boundaries do not move weekly, so a weekly job against them is a guaranteed no-op, and the row must state a WHEN because a filename in prose is a mention. **STAGE 1 IS A MEASUREMENT, NOT A BUILD, and the reason is specific to this number:** 221 is `build_eam_status.py`'s count, and the fleet's own experience of that instrument is that it was corrected FIVE times on the day it was written, once by Wisconsin and once because it counted a polygon's label as a person. **So re-derive the 221 before building anything on it** — how many of those files are boundaries that move on a decade, how many are structure, how many name a person, and which genuinely have a source worth watching. Group them by what a plan would actually say rather than listing 221 rows: a dozen honest rows covering classes of file is worth more than 221 lines nobody reads, and if a class turns out to need a watcher rather than a date, say so. **Then report before you write the file.** Two precedents to build on rather than invent from: `wi/WATCH.md` is the one written against Adam's own ruling, and Wisconsin's LTSB row is the shape for a file whose source moves on a statutory date. **No new fetches are needed for stage 1** — this is a question about the tree. |
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
