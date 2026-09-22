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
| **Hancock (#1018) — MERGED BY ADAM, THEN REVERTED BY HIM (#1058 `4e9aa16`); still waiting on the ask** | **open, waiting on an ask** | 2026-09-19, row corrected 2026-09-21 | **This row's original premise was wrong and the correction is this session's, not mine.** It said the page had moved under the parser and called it the Rock Island shape. Measured against the live page, with robots read first as the scraper's own client: the scraper reproduces the bot PR exactly, the county's own page prints `Jo0n Mason (R)`, and `Josh Turner` and `Alex Blythe` appear on it zero times. One `<li>` per member, so there is no column association to slip. The zero is the COUNTY'S typo and the two name changes are real edits to the county's page. The certified returns deepen it rather than settling it — Billy Cramer has no county board contest ever, and Joshua L. Turner won the 2026 District 4 Republican primary — which fits mid-term appointments and fits a county page edited wrongly, and cannot tell them apart. `ACCEPTED_NAMES` is ruled out by its own docstring. So nothing ships: the merged name gate refuses `Jo0n Mason` (verified on a merged tree, exit 1), `John Mason` would guess at a real person's name, and `Josh Turner` would name someone the county no longer lists. **What Hancock needs is the ask to `elections@hancockcounty-il.gov` — the District 4 member's correct name, and whether Billy Cramer holds District 2. Illinois drafts; Adam sends.** Carried to Adam 2026-09-19. **CORRECTED 2026-09-21: this row said HELD and that stopped being true.** #1018 was merged (`02706fd`) and Adam reverted it the same day (#1058, `4e9aa16`), so main carries Hancock's pre-#1018 names — all fifteen correct — and the PR is closed rather than waiting. Nothing about the evidence above changes, and neither does the ask. What does change is that the next weekly run will re-propose the same three edits against a reverted file, so this recurs on a schedule until the county answers. |
| **Reddick Fire: the #1023 caveat is unexecuted and now TWO files depend on it — DO SECOND** | **assigned 2026-09-21** | 2026-09-19 | One fire district (comptroller code `053/085/06`, filing in Livingston) appears in **both** `grundy-district-officials.json` and `kankakee-district-officials.json`. #1023 took Grundy's copy to the 2026 filing last week and #1053 took Kankakee's tonight, so both now name SUE BERGAN as C.E.O. with an empty office, where the 2025 filing named ROBERT LOWERY and carried 210 E MAIN ST and (815) 365-4911. #1053 was merged rather than held because holding it would have left the two files disagreeing about one district, which is worse than either answer. **But the look #1023 asked for — confirm against the actual AFR that the district filed it that way — has still not happened**, and the finding worth carrying is that a single filing propagates through several county rosters on successive weekly runs, so one unverified read reaches more cards than the PR carrying it suggests. The retention gate cannot see this: two records in a pooled file is below every threshold it sets. |
| **The two-witness rule has a SECOND loss shape and only the first is written down (#1076)** | **assigned 2026-09-22** | 2026-09-22 | Merged as `8f59be1` after reading the source rather than the count guards. Metamora Public Library District's telephone left `woodford-district-officials.json` and the drop is CORRECT, but not for the reason `comptroller_afr.witnessed()` documents. Read live 2026-09-22, robots first as the scraper's own client (allowed, no delay stated), both years through the same parser: FY2025 carried `(309) 367-4591` in all four slots, Smith in A/B/D and Weddle in C, so two surnames witnessed it; FY2026 carries `(309) 921-5074 Ext: 101` in A, B and D, **every one of them Smith**, against `(309) 645-0963` in C beside a gmail address. So the unit did not lose a co-signer with an unchanged value, as Reddick Fire did — **it filed a DIFFERENT telephone and the new one has one witness.** That makes carrying the old number forward worse than dropping it: it would publish a number the unit's own current filing has replaced. Adam's preserve ruling does not reach it, because the host served fine and the publisher gave new information rather than refusing a read. **Wanted: the phone-change shape recorded in `witnessed()`'s docstring beside Reddick's**, so the next reader does not read every phone loss as who-signed drift. Worth measuring in the same pass: the FY2026 value carries `Ext: 101`, which the parser strips at `Ext` — an extension is evidence the line is an institution's switchboard rather than a person's, and whether that should count toward witnessing is an open question, **not** a licence to relax the two-surname rule. Retention could not see this: one record in a pooled file is below every threshold. |
| **#1025 and #1028 collide with no git conflict — merge order matters** | **closed — merged in the planned order** | 2026-09-19 | Found by this session and verified by the manager on both branches. #1025's `ACCEPTED_NAMES` excuses Bartonville's `’s Email: clerk@bartonville.org`; #1028 deletes exactly that value; different files, so git reports nothing. Either order leaves main failing `validate_officeholder_names.py` on "stale, remove it". Order: **#1028 first, then drop the Bartonville entry from #1025 before it merges.** The edit is NYC/SF's to make — routed to them 2026-09-19. Illinois offered and correctly did not touch another session's branch. |
| Bartonville's phantom Clerk (#1028) | **merged** `d450c52`, before #1025 `a3d11c0` as planned | 2026-09-19 | Fixed the parse first, then widened the guard. One fabricated name off the municipality card. |
| Six roster workflows: shared pages after the branch cut (#1030) | **merged** `5338913` | 2026-09-19 | Stops weekly jobs dying when another workflow merges mid-crawl, and deepens the checkout so sitemap dates are real. |
| **Will County: move it from `REQUIRED_COUNTIES` into `PRESERVABLE`** (#982, #996, #1026) | **merged** #1043 `851bb01`, proved by a dispatched run rather than by the diff | 2026-09-19 | Adam's ruling, 2026-09-19: "Add will county to the exception list so the remaining workflow can continue." The block itself is unchanged and is never worked around — what changes is that it stops withholding 36 other counties' turnover. Two edits: the `PRESERVABLE` entry, and the workflow's build step, which gates on `scrape_will.outcome == 'success'` and so never runs. Cook stays required. The cost is real and gets stated rather than smoothed: a preserved full-body county means a Will council member who changes stays stale, and no count floor notices. Ask 28 stays drafted and unsent. |
| **L2 publishes a library's OWN NAME where its director goes, and #1062 would ship it — DO FIRST** | **open, PR held 2026-09-21** | 2026-09-21 | The weekly library-contacts PR replaces Atkinson Public Library District's `admin.name` `Ninette Carton` with **`Atkinson Public Library`**, role Director. MEASURED against the live source, robots read first with this repo's reader as `districtry/1.0` (allowed, no delay): `librarylearning.org/atkinson-public-library-district` carries `Name: Atkinson Public Library`, `Title: Director`, and `Ninette` appears zero times. **The scraper is faithful and the value is still unshippable** — the card would name an institution as the person who runs it, and would do so by removing a real name that ships today. `il-library-district-officials.json` has no `heads` for Atkinson, so nothing else fills that slot. **Neither guard can see it:** the name gate judges shape and this string is well formed, and the retention gate measures per source, where one record of 250 is below every threshold. Wanted: a builder guard that refuses an L2 administrator whose name matches the library's own record key, or is a prefix or suffix of it, ships that record with no administrator, and prints it every run. The other four changes in #1062 are correct and were each checked against the source — Rick Warren's vanishing `admin` is the builder working, because #1057 gave its filing a `heads` entry naming the same person, so the card still names her from the filing. |
| **Plattville's Clerk ships as `Beth Fals 56` — DO FIRST** | **assigned 2026-09-21** | 2026-08-01 | **Corrected 2026-09-19:** this board first said the value was held in `ACCEPTED_NAMES`. It is not — that table arrives with #1025 and is not on main, so the name is simply shipping and has been since 2026-08-01. Must be **dropped, not repaired** to `Beth Fals` — the Douglas County rule. |
| General Assembly roster is stale | open | 2026-09-19 | Raised by this session; the manager had it nowhere. Measured on main: `il-house-members.json` last moved 2026-09-08, `il-senate-members.json` 2026-09-02. Its workflow failed on 09-14 and was fixed on 09-18, so the next scheduled run is the first test. Reader-facing — these are the people on the state House and Senate cards. |
| Logan County's 11 municipalities and 65 officials are frozen | blocked | — | The county's own robots.txt disallows the directory the Clerk's yearbook sits under. That is the host's answer. |
| 2 of 64 districted board cards name no office | open | 2026-09-15 | Down from 50 on 2026-09-06. The long tail. |

## Status — this session owns this section

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
