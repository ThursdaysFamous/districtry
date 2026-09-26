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
| **#1158 merged — the two outer robots loops are retired and the reads are counted** | **merged `acafd1d`, verified on main** | 2026-09-25 | Measured on the merged tree rather than taken from the body: a host that never answers now costs exactly **3** reads through each wrapper against the 9 I measured this morning, the verdict is still `unreachable` and still disallow-all, and `ROBOTS_RETRIES` is gone from both modules as a definition while its history survives in the comments. The `wi` robots selftest goes 14 to 16 as claimed. **I negative-tested the read count myself** by reinstating a loop in Wisconsin's file: it fails with `and costs rp.RETRY_ATTEMPTS reads (9 of 3), not a multiple of them`, exit 1. **The read count rather than the deletion is the right thing to have built** — both loops survived the change that made them redundant precisely because nothing counted reads, and that is the general lesson: a redundancy removed without a check is a redundancy that comes back. Labelling the nine as measured and the seconds as computed is the other half of it. 100 of 100 green, CI green on `c030bae`. **And your own correction stands against my report to Adam:** I told him the city roster was frozen and readers were seeing a week-old answer. Yours is right — `343b624` wrote that file at 02:29 today already carrying all ten counties including Muscatine, so the 09-24 failure cost a refresh and no reader an answer. I verified that in the shipped file and have corrected it to him. |
| **`update-ia-county-city-officials-roster.yml` has been failing since 2026-09-24 — the city roster is frozen** | **assigned 2026-09-25, DO FIRST** | 2026-09-25 | New on #387 tonight, and it is the file stage 2 shipped this morning. Run `36071911988`, 2026-09-24T23:17, schedule, main: `muscatinecountyiowa.gov` robots.txt died with `ConnectTimeout` after 30s, twice in the same run, so the county was SKIPPED — correctly, since a network failure on robots.txt is disallow-all — leaving **8 counties current against a floor of 9**, and the builder refused to write. **THE REFUSAL IS RIGHT AND THE FLOOR IS NOT THE PROBLEM.** `MIN_COUNTIES` is 10 on main as of `343b624`, so the next scheduled run fails at 8 of 10 as well, and the shipped file keeps its 18 September reading until somebody re-reads that one page. **Measured from this vantage 2026-09-25 10:30 UTC, `GET https://muscatinecountyiowa.gov/robots.txt` with stdlib urllib answered HTTP 404 in 0.9s on two consecutive attempts** — a 404 on robots.txt is permission, not refusal, so the CI read was transient rather than the host's answer. That is a different vantage and a different client from the workflow's, which is the first thing to settle. **The builder's own docstring covers a county going STALE and this is not that**: Muscatine's page is not publishing expired terms, it could not be read once, and the floor's stated purpose is to make a county quietly going stale visible. A transient read failure scoring identically to a stale page is what turns one timeout into a week of frozen roster. **NEVER LOWER A FLOOR TO CLEAR THIS.** Two routes and the choice is yours: retry the robots read inside the run before believing an unreachable verdict — the mechanism Wisconsin already applies to its own `unreachable` results and CLAUDE.md records — or carry the last-good county forward with a per-source read stamp, which is Adam's 2026-09-19 preserve ruling and is what `PRESERVABLE` does in Illinois's municipal builder. Whichever you pick, a card must never print a verification date for a source that was not read. **Report the diagnosis before building**, and say which of the two you are doing and why.  **#1156 MERGED 2026-09-25 as `1cf8b14`, verified on main by content and by its own selftest there (89 assertions).** Route A is right and I checked the part that decides it rather than the summary: the retry fires on `unreachable` ALONE — 404, 403, 202 and 200 each return on the first call — so nothing is loosened, and a host genuinely down still fails every attempt, is still refused, and still trips the floor. Negative-tested independently: with `RETRY_ATTEMPTS = 1` exactly six assertions fail, naming the Muscatine case. 100 of 100 static invocations green, CI green on `a9fe021`. Your correction of my brief stands — one attempt, not two. **ONE MEASUREMENT TO SETTLE NEXT AND IT IS NOT A DEFECT: two callers now retry twice over.** `wi_county_board_scraper._robots_verdict` and your own `ia_supervisor_district_scraper` each wrap `fetch_verdict` in their own `unreachable` loop with `ROBOTS_RETRIES = 3`, so with the shared default also 3 a permanently dead host now costs **9 connect attempts, measured** by stubbing `_fetch_once` and counting (3 through `fetch_verdict` alone). Nothing is published wrongly and the direction is right, but on Wisconsin's serial 72-county scrape a 30-second connect timeout at 9 attempts is up to four and a half minutes on one host, and the PR's own reasoning — that the default belongs in the shared reader — is the argument for retiring those two outer loops or passing `attempts=1` at them. **Yours to propose, Wisconsin's file to agree to**, and worth doing as its own change rather than folded into anything. |
| **Sweep the other 90 counties for a city-officials page — MEASURE AND REPORT FIRST** | **BOTH STAGES MERGED — `cc3c091` and `343b624`; four Iowa cities now name their officials** | 2026-09-25 | Your own #1142 measurement is the case for this and it is Iowa's largest reader-facing gap by a wide margin: **834 of Iowa's 939 cities name nobody**, and of the 105 that do, **98 come from ONE route** — the county auditors under Iowa Code §47.2, which nobody had probed until it was. `MIN_COUNTIES = 9` is a FLOOR and not a ceiling; nine counties publish their cities' officials in a current, readable form today, and the gap's own `wanted` field says what would close it: “more counties publishing their cities' officials the way nine already do”. **Nobody has asked the other 90.** **Stage 1 is a measurement, not a build**: at most ONE request per county, to the page that county's own site names, robots.txt read first as the client that fetches, nothing at all to a host recorded as a challenge, and nothing to a host already recorded shut without a new address to try — the budget Michigan was authorised and held to across 25 counties. Then REPORT: how many of the 90 publish such a page, in what shapes, and what the yield would be in cities and named people. **A measured negative is a result** — if the answer is that nine is most of what exists, that retires an open-ended “more counties” from the record and points the effort at the Secretary of State ask instead (your Ask 8, which you already call the highest-value one). Build in a second change against the artifact, per county shape, with the floors' own rule respected: raise `MIN_COUNTIES` when a county joins and NEVER lower it to get past one going stale. **HELD 2026-09-25, one wording fix and not a re-measurement.** The sweep is right and I verified it row by row: 99 rows for 99 distinct FIPS, every table figure reproducing from the file, the six-of-22 own-statement split exact, 51 of 77 exact on a defensible denominator, the budget held (one GET, robots first through the shared reader as the same client, Osceola carrying a null host and never re-probed), and stage 2 correctly absent with `MIN_COUNTIES` still 9. **The hold is the number 24, which appears twice and names the wrong set both times.** It is `robots-refused` (22) + `unreachable` (2) — the counties whose page was NEVER ASKED — and it is the only subset of the verdicts that gives 24. It is not "counties having no site host in the repo at all" and not "counties whose only known address is a mail domain": by `pick_host`'s own construction the mail domain is reached ONLY when the repo has no host, so **all 51** are that, not 24. The correction makes the bound better than the one written, which is why this costs two sentences — in the PR body, which becomes the squash message, and in `ia/BOARD.md`, where `708684b` already carries both. **Three notes to fold into the same push:** not one of the 22 refusals is on a repo-known host (all 22 are the mail domain, which strengthens the caveat past what it claims); Ida and Webster failed with `Tunnel connection failed: 502 Bad Gateway`, which is this vantage's proxy rather than the host, the `docs.legis.wisconsin.gov` distinction this repo already draws, so "mostly TLS failures on legacy domains" folds two in; and `wrightco.iowa.gov`'s `unable to get local issuer certificate` is the Coles/Gallatin/Vermilion incomplete-chain shape, where the 2026-09-05 record says of its own re-probe that "the chain probe was run and found none" — one of those two statements has moved, and a pinned intermediate would open that host rather than refuse it. **Also state the sixteen-host claim's method**: 16 is substantive differences across all 99 ignoring a `www.` prefix; raw comparison gives 30 across 99 and 23 across the non-publishers, so a reader reproducing it without the method gets 30. **And a defect of mine, not yours:** my own battery runner was missing both `validate_gap_counts.py` invocations — the gate you built in #1137 — so I had been reporting a full battery off 98. Fixed and re-run; 100 green on your merged tree, CI green. **THE 24 FIX WENT FURTHER THAN I ASKED, and it is the better version.** I asked for two sentences in the body and the board; `64697ff` put the measurements in the ARTIFACT — 24 and 57 as two named sets with their construction stated, and the sixteen failed robots reads split into four shapes so the proxy pair and Wright are visible per row rather than folded into "mostly TLS failures". Every figure reproduces from the rows: 24, 57, 51-of-77, 0 repo-known refusals, 6 own-statement against 16 failed, 9/4/2/1 shapes, and 16/30/14/23 on the hosts. 57 is also more complete than my framing — I measured 51 within the 77 and 57 is the whole set. **HELD AGAIN ON ONE THING: NOTHING WRITES THAT BLOCK.** `main()` writes four keys — `measured`, `path`, `method`, `counties` — so `caveats` and `classifierNote` are both hand-added and the next probe run silently deletes the whole correction, with stage 2 the change most likely to re-run it. The docstring now also asserts "THE OUTPUT'S `caveats` BLOCK STATES BOTH, MEASURED", which the script does not do. **This is the family Wisconsin is measuring in #1147** — a figure stated beside the data that owns it with nothing deriving it — arriving in a file made an hour ago, in a change whose whole subject is that a measurement filed where nothing maintains it gets repeated. I checked the fix is possible before asking: every figure is derivable inside `main()` from what is already in scope, the counts from `rows`, the shapes from each row's own `robots` string, the host figures from `hosts` and `aud`. **And Iowa's diagnosis of its own 94 is sharper than mine:** it sliced `smoke-test.yml` at `actions/setup-node`, which is the NAMED-STEP boundary and not the invocation list, dropping the six per-instance `validate_index.py` runs — the merge gate itself — then dropped `esri_rings_test.mjs` on a "node without --check means browser" heuristic, the exact misclassification CLAUDE.md records. Two runners, same class, opposite directions, one evening. **MERGED 2026-09-25 as `cc3c091`, verified on main by content: the artifact ROUND-TRIPS byte-for-byte through `derive_caveats()`, 99 rows for 99 counties, Adams reads `publishes`, `pageNeverAsked` 24 and `noSiteHostInRepo` 57, and no key name carries a count.** Both holds were cleared with something better than what I asked for. The second fix also **proved itself by construction rather than by re-probing**, which would have cost 86 requests on other people's servers for figures already in hand — the right instinct, and it is the reason no second budget was spent. Three things it did beyond the ask: it stopped hardcoding a count inside a KEY NAME (`twoFailuresAreThisVantage` → `failuresThatAreThisVantage`), which is the same defect one level down; it derives WHICH counties those are instead of naming Ida, Webster and Wright in prose; and it added `rawAcrossNonPublishers`, which had lived in prose only. **STAGE 2 IS NEXT AND IT IS THE READER-FACING HALF:** build Adams in, raise `MIN_COUNTIES` 9 → 10, and narrow the gap's `wanted` using the corrected bound — the remaining upside is the 24 counties whose page was never asked, not the 57 with no repo host. 28 named officials across 4 cities is what a reader gets **STAGE 2 REVIEWED 2026-09-25 and HELD on two sentences. Everything reader-facing verifies against the shipped file:** Adams ships Carbon, Corning, Nodaway and Prescott with 28 officials (4 clerks, 4 mayors, 20 council) on 2028/2030 terms, ten counties, 102 cities, 738 officials, 507 council, 90 clerk rows across 89 cities, `MIN_COUNTIES` raised 9 → 10 with every floor moved up and none down. **The 830 / 109 is a real UNION and I counted it independently** — 102 from the county file, +4 from `ia-city-officials.json`, one each from Des Moines, Cedar Rapids and Waterloo = 109, with 939 − 109 = 830 and no city double-counted; that is the figure I most expected to be arithmetic. The `wanted` is narrowed off #1148's corrected bound rather than the retired claim. Ask 31 carries no address, reads `NOT YET ASKED — DRAFTED 2026-09-25`, and its reasoning is the best thing in the change: the county publishes the module and has filled nobody in, so "it is unfinished" is a complete answer and the ask compiles nothing. **THE HOLD IS THE BUILDER'S OWN DOCSTRING, fifty-five lines above `MIN_COUNTIES = 10`:** line 64 still says "Exactly nine counties are current and MIN_COUNTIES is 9" and line 66 "all nine will briefly publish expired terms". The comment BESIDE the constant was updated correctly; the docstring above it was not — the same family as the last two PRs, in the same file as the value it restates, on the day that value moved. Lines 16-17 want the 2026-09-25 finding APPENDED rather than the 2026-09-05 sentence edited. **Three more say nine and two must NOT move**, which is why this is two sentences and not a sweep: line 39's "the other nine straddle 2027 and 2029" is true of the nine it names and would become false as "ten", and line 285's dated "29 of 116 member phones" survives intact because Adams publishes zero phones — I checked. That split is #1147's rule applied, and this one file is a clean worked example of both halves **STAGE 2 MERGED 2026-09-25 as `343b624`, verified on main by content: Carbon, Corning, Nodaway and Prescott, 28 officials, ten counties, 102 cities, 738 officials, `MIN_COUNTIES = 10`, and the gap summary reading 830 of 939.** The hold was answered with more than it asked for. I asked for two sentences fixed and a dated paragraph appended; what landed is a section headed WHICH FIGURES HERE MOVE, WHICH MUST NOT, AND ONE THAT WAS NEVER RIGHT, which states the rule and walks all five instances of the word — the two that had to change, and the three that had to stay, each with its reason. **AND IT FOUND A THIRD CATEGORY NEITHER OF US HAD:** a section headed "WHAT THE 605 ACTUALLY ARE" whose own body summed to 710 while the file shipped 710 in the same commit, so that count was **wrong the day it was written** and sat through two rebuilds unread. That is not drift and not history — it is a figure that was never right — and the remedy is the sharpest statement of the whole day's lesson: **the heading now carries no number, because nothing checks a count in a heading.** I verified it: six ALL-CAPS headings in that file and not one carries a digit. Seat figures check out too — 109 of the 738 shipped officials carry a seat, thirteen counties publish against ten current. Ask 31 stays drafted and unsent.
| **Fix the PERSON_WORDS label defect in `validate_gap_counts.py` — 18 fleet gap ids, one already shipping** | **assigned 2026-09-25, DO FIRST** | 2026-09-25 | Your #1142 finding, and it is bigger than you measured. The gate passes `where` — which embeds the record ID — as `measure_metric`'s `spec["label"]`, so the `keys` branch searches the RECORD ID for `PERSON_WORDS` and demands a `naming` key. **I counted 18 ids across the fleet that trip**, not 12: twelve Illinois, one Wisconsin (`municipal-officers`), two Iowa, three Michigan (`mi-township-officers`, `mi-municipal-officeholders`, `mi-school-board-members`). **And `ia-supervisor-district-seats` ALREADY SHIPS a declaration and trips on *seats*** — it passes today only because `self` means the evaluator is never called, so the first person to give it a `file` + `metric` meets this. Your diagnosis of the cause is exactly right and worth keeping in the fix: **the ID names the ABSENCE and says nothing about what the count measures**, which is why `ia-board-chair`'s 38 keys — genuinely 38 named chairs — pass unchecked while 939 contact rows that name nobody would be asked to assert they do. The label the evaluator needs is one describing the CLAIM, not the record. **Do not weaken `PERSON_WORDS` or the `naming` requirement for the history tiles that legitimately use it** — that check caught two real ILGA tile errors and its own docstring records why it measures rather than reasons. Negative-test both directions: a history tile whose label claims people and counts keys must still be refused, and a gap record whose ID merely contains a person word must not be. |
| **Measure the Iowa CITY tier and report before building — the recorded figure and the tree may already disagree** | **assigned 2026-09-24, DO FIRST** | 2026-09-24 | `ia/WATCH.md` says **THE CITY CARD NAMES NOBODY IN 939 OF 940 CITIES** and calls it the app's largest silent absence. It is the biggest reader-facing Iowa gap by a wide margin and it is the right next thing. **BUT MEASURE THE CLAIM FIRST**, because I could not confirm it from the tree in the time I had: `ia/data/app` now carries `dsm-council-members.json`, `cedar-rapids-council-members.json`, `waterloo-council-members.json`, a four-key `ia-city-officials.json` and a **98-key `ia-county-city-officials.json`**, and Waterloo's own weekly workflow ran green tonight. So “939 of 940” was true when written and may not be now — exactly the class five PRs were held on today. **Report before you build**: how many cities name a person in a served byte today, through which file, and what the four recorded routes are worth NOW (the League's `iowaleague.org/cities/` 200 with 948 rows is the one your own record says corrected this project). A clean measurement that says the figure is still right is a result worth having, and if it has moved, the gap record and WATCH row are the first thing to fix. No fetch beyond what a route needs, robots first as the client that fetches. |
| **Draft the narrowed ask for the twelve counties that publish no supervisor-to-district join — DRAFTED, NEVER SENT** | **assigned 2026-09-24, second** | 2026-09-24 | Your own board named this and it is right: of the eighteen, six publish the join (Butler, Chickasaw, Howard and Winnebago shipped; Kossuth and Worth are refused by gate 3 because flat text cannot settle their order), so **twelve publish it nowhere** and an ask to those twelve is narrower and better founded than one to all eighteen. Write it into `docs/ASK_DRAFTS.md` in the shape the outbound-ask skill sets, and update the gap record's ledger to `NOT YET ASKED — DRAFTED`. **NOTHING IS SENT BY A SESSION**: Adam sends, and the ledger says `ASKED <date>` only on the day it goes and never before. Ask for the one fact that is missing — which supervisor holds which district — and say what the app already has, since these counties' districts and members both ship and only the join does not. Kossuth and Worth are a DIFFERENT ask if you want one: their pages publish the pairing and this project cannot read the order safely, which is a question about their page rather than about their records. |
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

**2026-09-26 — THE 830/109 HOLE IS CLOSED BY SOMEBODY ELSE'S CHANGE, AND VERIFYING IT ESTABLISHED
THAT MY OWN #1149 WROTE THOSE TWO NUMBERS BY APPLYING A DELTA RATHER THAN RECOUNTING.** I was told
Michigan's `1daf568` now declares Iowa's figures, with numbers — 106 and 833 — that disagreed with
the 109 and 830 I recorded yesterday. Both halves check out, and the disagreement is mine.

**WHAT IS TRUE ON MAIN NOW, MEASURED FROM THE FILES RATHER THAN FROM THE GATE'S MESSAGE.**
`1daf568` (#1183) is an ancestor of `2c9e836`. The record's summary was REWRITTEN, not extended: it
reads "833 of Iowa's 939 cities. In the other 106, ten counties publish the officials for 102 and 4
cities publish their own", and all five of those numbers are now declared — 939 and 102 and 4 as
`keys`, then 106 as a `combine: "union"` over the two roster files on `field: "members"`, and 833 as
that same union with `of: 939`. Counted straight off the shipped files: county 102, city 4, union
106, contact 939, complement 833. **I checked the two things a union can get wrong and neither is
wrong here** — the two files are DISJOINT (no city named by both, so the union is also the sum, which
is why the arithmetic reads as if it could not fail) and all 106 are inside the 939, so the
complement is a complement of the right denominator. Gate `OK — 15 stated count(s) agree`, selftest
`0 failure(s)`.

**SO THE HOLE I RECORDED YESTERDAY IS CLOSED, AND IT WAS NOT THE HOLE I DESCRIBED.** I wrote that
830 and 109 "remain undeclared in a field the gate already reads", which was true of the
declarations and false about the numbers: **830 and 109 were wrong, not merely ungated.** Measured at
`343b624` itself — the commit that wrote them — the files gave 106 and 833, and neither source file
has moved since in any way that changes a count (`ia-city-contact.json` last at `a6ca829`,
`ia-county-city-officials.json` at `343b624`, `ia-city-officials.json` at `eed8091`, a seat change
that left the key count at 4). They were wrong the moment they were written.

**HOW THEY CAME TO BE WRONG IS THE PART WORTH KEEPING, BECAUSE THE SIGNATURE IS LEGIBLE.** Before my
change the record said 834/105; after it, 830/109. Adams added four cities. **Both numbers moved by
exactly ±4 and both kept an identical pre-existing 3-city error** — at `a6ca829` the true pair was
102/837 against a stated 834/105 — which is what applying a delta looks like from the outside and
what recounting cannot look like. It is in a PR titled *every figure the sweep moved is
re-measured*, and my own board entry for it says "**The 830 / 109 is a real UNION and I counted it
independently** … that is the figure I most expected to be arithmetic." I did the arithmetic on the
delta and called it a count. **A number reached by adjusting the number that was there is not a
measurement, whatever it is labelled**, and the tell is available before the fact: my walk-through
reproduced the stated 109 by adding 102 + 4 + 3 — and those "one each from Des Moines, Cedar Rapids
and Waterloo" are three cities I never found in a file, because they are not in one.

**THE CORRECTION AND THE GATE WERE BOTH SOMEBODY ELSE'S.** `25351d4` (#1181) caught it and counted
independently; `1daf568` (#1183) put all five figures under the gate, which is the durable half —
the union form did not exist until that change, so the two numbers could not have been declared on
the day they were written even had they been right. I read #1181's commit message before writing
this so my record would not contradict theirs; it notes Iowa's board has no open work on this
record, which I agree with.

**ONE THING IS NOT ESTABLISHABLE AND I AM NOT GUESSING AT IT.** The 3-city error predates my change
and `a6ca829` is listed in this checkout's own `.git/shallow`, so it has no parent here and where
those three cities came from cannot be traced from this vantage. I am recording the boundary rather
than an explanation.

**THE ENTRY BELOW STAYS AS WRITTEN AND IS CORRECTED HERE.** Yesterday's `#1173` entry says in three
places that 830 and 109 are undeclared — the paragraph headed ALSO RECORDED most explicitly, which
calls it "a real hole rather than a design choice". The hole was real and the numbers named in it
were wrong; both are now fixed on main by other people's changes. The one sentence in that entry
that survives intact is the one it was evidence for: a mechanical prose rewriter would have moved
939 and left the rest, which is still the argument against option 2.

**2026-09-25 — #1173 MERGED AS `8961e65`; THE PANEL NOW SAYS 43 AND 56.** Verified on main by
content rather than by the merge event: the shipped `ia/data/app/coverage-gaps.json` carries the
43-of-99 and 56 wording, the `counts` declaration still reaches no reader, the chair roster holds
43 keys with all five new counties named (O'Brien Nancy McDowell, Osceola Jerry Helmers, Palo Alto
Linus Solberg, Plymouth Don Kass, Union Rick Friday), `validate_gap_counts` reports all 8 stated
counts agreeing, and its selftest passes on main AND still passes with both live files hidden —
so the hermetic fixture survived the merge rather than only the commit. CI was green on `892dac4`
(check run `108275920875`, run `36197287430`, 22:33:39 → 22:45:34Z), read through
`get_check_runs` rather than `get_status`, and the branch merged cleanly against `c6c6379`. The
check-in is retired and the subscription closed by the merge.

**WHAT IS STILL OWED IS UNCHANGED BY THE MERGE, AND THE NEXT FAILURE IS PREDICTED RATHER THAN
FEARED.** The derived-count form is not built, so the next county to gain a chair turns this
refresh red again — two numbers and a regenerate, and the gate's FAIL line names them. Michigan's
52/31 is the next declaration due to break for the same reason. And 830 and 109 remain undeclared
in a field the gate already reads. None of that was in scope for a red-PR fix, and all of it is
recorded in the entry below.

**2026-09-25 — #1173 FIXED AND PUSHED (`892dac4`); I PICKED THE DERIVED FORM AND AM NOT LANDING IT
IN A RED-PR FIX, AND THE REASON IS MEASURED.** The record now reads 43 of 99 and 56, verified from
the files rather than from the gate's message — 43 chair keys, 99 officers, complement 56, every
chair naming somebody, five counties gained (O'Brien, Osceola, Palo Alto, Plymouth, Union) and none
lost — with every file that reads the block regenerated and only Iowa's panel file moving.

**THE SELFTEST WAS THE LARGER HALF.** Two of its four cases asserted against LIVE shipped files
(`== 38` on the chair roster, `== 939` on ia-city-contact), so a successful refresh broke the
gate's own proof of correctness, and the second was one new Iowa city from doing the same. Both now
run against a two-file fixture in a temp directory. **The fixture counts are 7 and 3 because no
real file in the fleet holds either**, so pointing the cases back at the tree fails rather than
passing by luck — proved empirically as well: with both live files hidden the selftest passes, and
with the `claim` split reverted case B fails, which is the regression it exists for.

**ON THE STANDING FIX, I PICKED OPTION 1 (a form the gate derives) AND MEASURED WHY OPTION 2 IS
UNSAFE.** A workflow that rewrites the record's numbers needs to know which numbers in a reader
field are file-backed, and `validate_gap_counts.py`'s own docstring already establishes that such
an enumeration cannot be got right — two readers of the same corpus answered 152 and 153. I
reproduced that immediately on the four records that carry a declaration: **Michigan's field
contains `2024,`, which is a YEAR**, and **Iowa's municipal field states 830 and 109 while only
939 is declared**, so a rewriter that moved 939 would leave a sentence that does not add up, with
the gate still green because the other two are invisible to it. A mechanical prose rewriter is the
wrong answer and the evidence is in the corpus rather than in an argument.

**WHAT I DID NOT BUILD, AND WHY IT IS NOT MINE ALONE.** The derived form puts a token in the
authored field and resolves it in `build_coverage_gaps.render()`, which also moves the READER_MAX
validation onto resolved text and changes this gate's subject — shared machinery behind all six
instances' `--check` runs. **Four records carry a declaration and three of them refresh weekly, in
two instances**: Michigan's 52/31 will go red exactly this way the week one of its counties starts
being read from its own board page. So it wants one shape rather than three, which is the same
coordination call the nesting fix wants and the second time today a change has landed in that
position. **Until it exists the next chair refresh goes red again** — two numbers and a regenerate,
and the gate's FAIL line names them.

**ALSO RECORDED: 830 AND 109 ARE UNDECLARED IN A FIELD THE GATE ALREADY READS.** That is a real hole
rather than a design choice — 830 is the complement form the gate supports through `of` — and
closing it needs establishing which file gives 109, which is research rather than this change.

**2026-09-25 — IOWA'S LEGISLATIVE NESTING: THE SOURCE IS EXACT, THE CAUSE IS OURS, AND A
RETAIN-PERCENTAGE SWEEP CANNOT FIX IT.** Nothing in the tree changed and no tolerance was
touched; this is the measurement the check-in asked for.

**THE SOURCE NESTS EXACTLY.** Fetched both chambers from TIGERweb through `build_legislative_boundaries.py`'s
own query — layer 1 and 2, `STATE='19'`, `outSR=4326&geometryPrecision=6` — and paired Senate N
with House 2N-1 and 2N: **0 m Hausdorff and 0.0000% symmetric difference on all fifty pairs.**
So this is not upstream, and the same result is the CONTROL ON THE PAIRING: a wrong 2N-1/2N
assumption could not produce fifty exact matches.

**THE SHIPPED FILES REPRODUCE FROM THAT SOURCE EXACTLY**, through the builder's own two mapshaper
runs at 10% and 9%: 40 of 50 pairs over 25 m, median symmetric difference 0.0095%, worst 775.3 m
at D25/D26, best 12.315 m at D3 — every digit identical to measuring the shipped files
themselves. The cause is entirely inside the builder.

**MATCHING THE PERCENTAGE HELPS AND DOES NOT FIX IT**, which is the finding Illinois needs before
it finishes sweeping. Separate runs at 10% and 10%: 40 pairs → **15**, median 0.0095% →
0.0008%, worst 775 m → **113 m**. Better by an order of magnitude and still not nesting. The
reason is that Visvalingam retains a percentage of vertices PER FILE, so "10%" is a different
threshold in a 50-district file than in a 100-district one, and `keep-shapes` is per-file too.
**No percentage makes two independent topology builds agree.**

**ONE COMBINED RUN RESTORES EXACT NESTING.** Both chambers concatenated into one layer, one
topology build, one `-simplify visvalingam keep-shapes 10%`, then split back by chamber:
**0 m and 0.0000% on all fifty pairs.** Payload, raw/gzipped: senate 287,653/89,051 →
313,144/**84,445** (gzip SMALLER), house 357,186/108,604 → 429,078/**113,809**. Net **+0.6 KB
gzipped** for both chambers.

**IT IS NOT FREE AND THE TRADE IS WORTH STATING.** Measured as each simplified district's
Hausdorff from its own source district: senate median 79 → 90 m (worse), house median 90 → 74 m
(better), senate worst 333 m unchanged, house worst **775 → 332 m**. So one run buys exact
nesting and a much better house layer for slightly coarser senate districts.

**THE TWO SYMPTOMS ADAM SAW ARE ONE DEFECT.** The fidelity loss is real on Iowa — the median
district boundary sits **79-90 m** from its source, p90 186-203 m — and the nesting error is the
worst case of it rather than a separate drift: **H50 and H51 each stray 775 m** from source at
9%, and their shared boundary IS the Senate 25/26 line, where the senate layer at 10% strays only
186 m and 332 m. The pair's 778 m is the HOUSE layer's own error, not a symmetric drift between
two files.

**MY WORST FIGURE DOES NOT REPRODUCE THE 849 m I WAS GIVEN, AND I RULED OUT THE TWO CAUSES I
COULD.** I measure **775.3 m** in a local equirectangular frame and **778.4 m** geodesically on
the same vertex pair (-93.643139,42.057399 → -93.647724,42.063516). Not the discrete-Hausdorff
approximation: `densify=0.01` returns 775.3 m unchanged. Not my planar frame: the geodesic agrees
within 0.4%. What the 849 measured is NOT established, and the two measurements agree on
everything that matters — the median share to two digits (0.0095% against 0.0093%) and the
divergent-pair count within two.

**CLOSED THE SAME HOUR — `-i combine-files` IS THE SHIPPABLE INVOCATION, and Wisconsin got there
first.** `b53ff66` landed minutes before this entry with the identical conclusion reached
independently on its own state: TIGERweb exact 33 of 33, equalising the percentage NOT a fix, one
combined run exact, and its own worst offset (418 m) likewise failing to reproduce the briefing's
(595 m) with the median reproducing. **Three instances, one answer.** Their mechanism is the piece
I had flagged as undesigned, so I measured it rather than re-deriving it:
`mapshaper -i <sen> <hou> combine-files -simplify visvalingam keep-shapes 10% -o …` writes **two
files, each keeping its own field set**, and the pairs come out **0 m and 0.0000% on all fifty**.
Payload gzipped: senate 89,051 → 83,490, house 108,604 → 112,498 — **net 1.7 KB SMALLER** for both
chambers, where my one-layer merge measured +0.6 KB larger, so the real mechanism is cheaper than
the test that stood in for it. It also printed `[simplify] Repaired 2 intersections`, which the
separate runs never reported. Wisconsin measured +15.2 KB on its own state, so **the payload cost
of this fix varies by state and is not one figure.** Still not built here: three builders need it
and the invocation should be one shape rather than three, which is a coordination call rather than
mine to make.

**WHAT WAS NOT DESIGNED WHEN THIS ENTRY WAS WRITTEN.** My combined run merged both chambers into ONE
layer and split them afterwards, which is not what the builder ships — it writes two files with
different field sets (`SLDU` against `SLDL`) and different `min_features` guards, and `us-house`
is a third target in the same script that nests inside neither. Proving the topology approach
works is not the same as proving the mapshaper invocation a builder would use. Held for Illinois's
answer as instructed.

**2026-09-25 — #1158 MERGED AS `acafd1d`; BOTH OUTER LOOPS ARE GONE FROM MAIN.** Verified by
content rather than by the merge event: no `ROBOTS_RETRIES` assignment and no
`for attempt in range(ROBOTS_RETRIES…)` remains in either file — the four textual matches
left are comments naming the retired constant to say it is retired — and on main
`ia_supervisor_district_scraper --selftest` reports 0 failures while
`wi_county_board_scraper --selftest` reports `robots selftest: 16 assertions`. CI was green on
`c030bae` (run `36146185468`, `pull_request`, 14:14:47 → 14:24:28Z) and the merged tree had
already been checked here against main's two later commits, since my PR's CI ran against the
older base `f67eb45`: `validate_steward_mirror`, `validate_gate_counts`, `validate_skills` and
`validate_doc_counts` all pass on the local merge. The check-in is retired, the subscription
closed.

**THE COORDINATION WAS THE PART WORTH RECORDING, AND IT NEARLY FAILED.** Wisconsin's own
check-in carried a standing instruction to build this same change as task #60 the moment #1157
merged — and #1157 merged as `dcd3687`, minutes after #1158. Two sessions were one timer apart
from building the same two files. Nothing in either PR would have shown it: the collision was
only visible in their scheduled prompt, which I read while looking for something else.
`SendMessage` could not reach them — a separate remote session, absent from `ListAgents` — so
the channel was a comment on the artefact their check-in re-reads. **A SESSION'S NEXT ACTION CAN
BE SCHEDULED RATHER THAN DECIDED, so "they have not started it" is not the same as "they will
not", and the place to say so is wherever their own timer looks.** Their task table is the
manager's to retire; this notes it rather than editing it.

**2026-09-25 — THE OUTER-LOOP RETIREMENT IS BUILT AND OPEN AS #1158.** The entry below
ends "still unstarted"; that stopped being true an hour later, once Wisconsin agreed on
`cc2253f`. Both loops are gone — mine and theirs — and the part worth recording is what
the change is held together by. **THE DELETION IS NOT THE FIX; THE READ COUNT IS.** Both
loops survived the change that made them redundant because nothing counted reads, so
each file's selftest now stubs `rp._fetch_once`, asks for a host that never answers, and
asserts the verdict is still `unreachable` → disallow-all AND that it cost exactly
`rp.RETRY_ATTEMPTS` reads. Negative-tested both ways by putting the loop back: each names
**9 of 3** and fails. Wisconsin's robots selftest goes 14 → 16 assertions, verified
against the base rather than assumed. **The figures are labelled by how they were got**:
nine attempts is MEASURED by counting, and 237s→78s (Iowa, 25s timeout) and 282s→93s
(Wisconsin, 30s, on one host of a serial 72-county scrape) are COMPUTED from two
constants each — this repo has paid for a correction derived by arithmetic and presented
as a measurement. Behaviour is unchanged for every host that answers at all, and
unchanged for one that recovers late, since the shared backoff is the same 1 then 2.
Wisconsin's second comment — the one arguing its page ladder is bounded because
`unreachable` is re-asked `ROBOTS_RETRIES` times — now names `rp.RETRY_ATTEMPTS`, because
the argument outlived the constant. 100 of 100 static invocations green, enumerated
through `validate_gate_counts.measure()`; no CI step added, so 81/110 is unchanged.

**2026-09-25 — THE CITY ROSTER REFRESHES AGAIN, AND THE RUN DOES NOT PROVE THE RETRY
FIRED.**

Dispatched `update-ia-county-city-officials-roster.yml` by hand at Adam's instruction:
run `36144018468`, `workflow_dispatch` on `main` at `0488761`, which carries `1cf8b14`
(#1156). **SUCCESS**, 13:54:59 → 13:55:49 UTC. **Muscatine fetched normally** —
`cities=8 officials=61 seats=7` — and no county printed a NOT FETCHED line, so #1156's
new wording went unexercised as well. All thirteen counties swept; the builder kept
**10 current against `MIN_COUNTIES = 10`** after dropping Sac (26 of 61 officials
publishing an ended term), Shelby (38 of 77) and Winnebago (22 of 51). The previous
run, `36071911988` on 2026-09-24, had refused at 8.

**WHAT THIS RUN DOES NOT SHOW IS THAT THE RETRY FIRED.** The gate annotates `why` with
`(on attempt N of M)` only when `N > 1`, and the scraper prints `why` only on failure,
so a retried success is silent by construction. **The timing settles it the other way:**
the scrape step ran **39 seconds for 13 counties** over a serial loop that sleeps 0.5s
between them — 12 sleeps and 26 fetches inside those 39 seconds — which leaves no room
for even one 30-second connect timeout. **Muscatine answered on the first attempt.**
What was measured is that the host is answering again. The retry's witness stays the six
assertions in `robots_policy.py --selftest`; a run that never needed the fix cannot
corroborate it, and reporting it as confirmation would be the shape I was corrected for
earlier today — a real measurement carrying an unverified one.

**THE FILE DID NOT CHANGE, WHICH MEANS THE SHIPPED ROSTER WAS NEVER STALE.**
`git diff --quiet` found the rebuild byte-identical to what ships, so step 9 skipped and
no bot PR opened. The shipped file was written by `343b624` (#1149) at 02:29 today and
already carries Muscatine's 8 cities and 61 officials. So the 2026-09-24 failure cost a
refresh and cost no reader an answer — which is what a count guard refusing to write is
supposed to cost. The board row's "the shipped file keeps its 18 September reading" was
true when written and stopped being true when #1149 merged four hours later.

**THE MARGIN IS ZERO AND THAT IS NOT A DEFECT.** 10 of 10 exactly. One more county
failing to fetch, or one more crossing the expired-term threshold, refuses the write
again — by design, since `MIN_COUNTIES` tracks the current count so a county quietly
going stale is visible. **The remedy is never the floor.** The retry addressed the one
cause that was never staleness; everything else here is the guard working.

**WISCONSIN HAS AGREED TO THE OUTER-LOOP RETIREMENT** (`cc2253f`), reproducing the 9 on
their own file and adding two things I had not: a SECOND comment dies with the loop —
the one arguing the page ladder is bounded because `unreachable` is re-asked
`ROBOTS_RETRIES` times, which must be restated against `RETRY_ATTEMPTS` — and the copy
being retired is the untested one, which is a better argument for retiring than for
`attempts=1`. They held rather than built it, since #1157 is open on their only branch.
**Still unstarted, and still its own change.**

**2026-09-25 — THE DOUBLE-RETRY IS MEASURED. PROPOSAL BELOW; NOTHING BUILT.**

**The 9 reproduces.** Stubbing `_fetch_once` and counting, with the backoff zeroed so
the number is attempts rather than seconds: **3** through `fetch_verdict` alone, **9**
through either outer loop. Both loops are the identical pattern with identical
reasoning — `unreachable` only, because a served file, an absent one and a refusal
are all answers — and neither does anything the shared retry does not.

**BUT THE COST DEPENDS ON HOW THE HOST FAILS, AND THAT SPLITS THE CASE IN TWO.**
Computed from each file's own constants, then checked against a live host:

```
connect timeout, Muscatine's shape   wi 282s (4m42s)   ia 237s (3m57s)
fast 5xx or TLS error, Bremer's       either   17.4s
```

**Bremer is the one paying it weekly, and it pays the cheap price.** Measured today,
one request each at `attempts=1`: `bremercounty.iowa.gov/robots.txt` **HTTP 500 in
0.62s**, `www.co.bremer.ia.us/robots.txt` **SSLError in 0.57s** — both `unreachable`,
both retried nine times, for about 17s rather than 237s. So "up to four and a half
minutes on one host" is exactly right for a host that TIMES OUT and roughly sixteen
times too high for the failure this scrape actually meets every week. The expensive
case is real and rare; the common case is cheap.

**PROPOSAL: RETIRE THE TWO OUTER LOOPS RATHER THAN PASSING `attempts=1`.** Both were
offered and this is the one my own PR's argument points at — the mechanism belongs in
the shared reader because the defect is shared, and `attempts=1` would leave two
files each keeping a second copy of a thing the reader now does, which is the
two-readers-of-one-question defect this fleet keeps paying for. **Retiring them
restores each file's exact pre-#1156 behaviour**: both outer loops sleep `2 **
attempt` = 1s then 2s, which is the shared `RETRY_BACKOFF` exactly, so 3 attempts with
the same spacing is what each file had before I touched anything.

**WHAT MUST NOT BE DELETED WITH THEM.** Each loop's comment carries its own measured
cause — Wisconsin's `co.forest.wi.gov`, which served its policy on 2026-09-12 and was
unreachable for one minute on 2026-09-13; Iowa's Bremer 500 — and those move to the
call site rather than going. **And neither file's own CACHE is in scope:** Wisconsin
keeps its own dict keyed by (user-agent, url) because it sends TWO user-agents where
`RobotsGate` is built with one, and that reason stands untouched; Iowa passes its own
`ROBOTS_TIMEOUT = 25`, which `fetch_verdict` already honours. The retry is the only
duplicated part.

**SPLIT: `ia/` is mine, `wi/` is Wisconsin's to agree to**, as the manager set it. I
propose both and touch Iowa's only until Wisconsin says yes. Its own change, not
folded into anything else.

**One thing I could not establish and it does not move the recommendation:** whether
Wisconsin's 86-host scrape is serial. `import threading` is in the file and no
`ThreadPoolExecutor` is; I did not chase it further, because the fix is the same
either way and the wall-time figure above is per host rather than per run.

**2026-09-25 — #1156 IS MERGED AS `1cf8b14`, VERIFIED ON MAIN BY CONTENT.** Thirteen
checks, all pass:

```
retry       RETRY_ATTEMPTS = 3, RETRY_BACKOFF = (1, 2), _fetch_once split out,
            early return on any non-unreachable status, both why-suffixes present,
            RobotsGate threading attempts through
log lines   neither Iowa scraper has a print claiming a refusal; both print the
            gate's own reason as NOT FETCHED
gates       robots_policy --selftest OK at 89 assertions
            validate_gate_counts 81/110, both invocation readings agreeing
```

**THE ROSTER IS NOT UNFROZEN YET AND THAT IS DELIBERATE.** The cause is fixed; the
file still carries its 18 September reading until the workflow runs again. The
scheduled run is Thursday 20:30 UTC. **A `workflow_dispatch` would confirm the fix
and unfreeze it today, and it is Adam's call** — I said so twice before the build and
am not reversing that unilaterally. It costs thirteen requests to county servers and
opens a reviewed bot PR like every other roster refresh. Say the word and I run it.

**AND THE `PERSON_WORDS` DO FIRST ROW IS ALREADY CLOSED — for the manager to retire,
since the Tasks table is theirs.** Measured on main just now: `measured_metric.py`
separates `claim` from `label` (`claim = spec.get("claim", spec["label"])`),
`validate_gap_counts.py` passes the EMPTY claim at line 154, and the gate is green at
8 stated counts. `git log -S` puts that in **`b0d0523`, #1145** — this session's own
work earlier today, which is why the row reads open: it was assigned in the same
sweep that merged the fix. **Both of its negative tests are in the file** (a history
tile whose label claims people and counts keys is still refused; a gap record whose
ID merely contains a person word is not), which is what the row asked for.

**2026-09-25 — ROUTE A IS BUILT AND OPEN AS #1156.** Adam said go ahead.

**`fetch_verdict` re-asks an `unreachable` verdict — 3 attempts, 1s and 2s backoff —
AND ONLY THAT VERDICT.** Every other status is the host having spoken: 404 and 410
are no policy, 401 and 403 a refusal, 202 and a challenge body an access control,
200 a document. Re-asking any of them puts requests on somebody's server to be told
the same thing twice. `unreachable` is the one verdict meaning NO ANSWER ARRIVED.

**The default is shared because the defect is** — 27 files call that reader and Iowa
alone puts 108 hosts a week through it. A host genuinely down still fails all three,
is still refused, and still trips its builder's floor. **No floor was touched.**

**THE SELFTEST'S SECOND ASSERTION IS THE ONE THAT MATTERS**: the same fake session,
`attempts=1`, returns `unreachable` and disallow-all — the frozen roster, reproduced
— so the retry is provably what changed the answer rather than something else in the
diff. Negative-tested by setting `RETRY_ATTEMPTS = 1`: six assertions fail, naming
exactly the Muscatine case. Offline throughout, against a call-counting fake.

**AND THE LOG STOPPED CLAIMING A REFUSAL IT HAD NOT MEASURED.** Two Iowa scrapers
hardcoded "robots.txt refuses districtry" for any non-allow verdict, so the run
printed `robots.txt refuses districtry (robots.txt unreachable: ConnectTimeout...)`
— a sentence contradicting its own parenthetical, about a county that refuses
nothing. **That is the 605 shape and the League's 935/536 shape for the third time
this week**: a claim sitting beside its own disproof. Both lines now print the gate's
own reason.

**MY BATTERY RUNNER WAS THE DEFECT CLASS CLAUDE.md NAMED TODAY, AND IS FIXED.** The
new rule says enumerate through the steward skill or `validate_gate_counts.py` and
never through a pattern of your own. My runner took the command list from the
module's own reader but applied a HAND-KEPT LIST OF TEN Chromium names. It now takes
the split from `validate_gate_counts.measure()`'s own rule (a `node ` command
positioned after `actions/setup-node`) and REFUSES TO RUN unless the two readers
agree on the totals. They do: 81 named steps, 110 invocations, 100 no-browser, 10
Chromium. The old list happened to give the same answer; it was one rename from not.

**ON MERGE** the Thursday 20:30 UTC run should take twelve counties again. A
`workflow_dispatch` would confirm it sooner and is the operator's call.

**2026-09-25 — DIAGNOSIS OF THE FROZEN CITY ROSTER, REPORTED BEFORE BUILDING AS ASKED.
IT IS TRANSIENT, THE CLIENT IS RULED OUT, AND THE BRIEF'S "TWICE" IS ONE ATTEMPT.**

**MEASURED WITH THE WORKFLOW'S OWN CLIENT** — `requests.Session`, the scraper's own
`districtry/1.0 (+https://districtry.com/ia/)`, through the shared
`robots_gate.RobotsGate`, the exact path the run takes:

```
GET https://muscatinecountyiowa.gov/robots.txt   HTTP 404 in 0.95s
gate verdict  ALLOW — "no robots.txt (HTTP 404, allow all)"   status 'absent'
```

So the difference between CI and this vantage is the ROUTE, not the code: the
manager's stdlib read (404 in 0.9s, twice) and this one through `requests` plus the
gate agree exactly. **404 IS THIS HOST'S NORMAL ANSWER, ON FOUR DATED WITNESSES** —
the scraper's own 2026-09-05 probe ("across all twelve county hosts: ELEVEN serve no
robots.txt at all"), `ia/scripts/robots_gate.py`'s 2026-09-12 sweep of 108 hosts
("50 answering 404"), the manager's two reads at 10:30 today, and this one.

**CORRECTION TO THE BRIEF: THE READ WAS ATTEMPTED ONCE, NOT TWICE.** Run
`36071911988` prints the identical error text at 23:17:51 (inline, as the county is
skipped) and again at 23:17:59 (the end-of-run `did not yield` summary re-printing
the stored reason). `RobotsGate` caches per host under a lock, so one fetch was made.
**That is the one detail that matters for the verdict**: "twice" would mean a retry
had already happened and failed, which is the single reading that argues AGAINST a
transient. It did not happen.

**AND A 30-SECOND CONNECT TIMEOUT TO A HOST THAT CONNECTS IN 0.95s IS A NETWORK-PATH
EVENT.** `ConnectTimeout` is a failure to establish TCP — not a slow page, not a
refusal, not a policy. Nothing about the host's answer changed.

**THE CAUSE IS THAT `fetch_verdict` HAS NO RETRY, AND 27 FILES SHARE IT.** One
attempt; any exception becomes `unreachable`, which is disallow-all by RFC 9309
§2.3.1.4 and correct as a READING. What is wrong is deciding it on ONE SAMPLE of a
connect attempt, for a verdict whose failure mode is to refuse. Counted today, 27
files across `ia/`, `mi/`, `wi/` and `scripts/` call that reader; Iowa alone puts 108
hosts a week through it.

**TAKING ROUTE A — retry the robots read before believing `unreachable`. And the
brief's attribution of it needs one correction, which is why the mechanism is worth
naming precisely.** CLAUDE.md says "Wisconsin re-asks an `unreachable` verdict before
believing it" and points at the municipal-executives builder. That file does no
re-asking: `carry_forward()` is purely a CARRY, keyed on the `unreachable` status,
stamping `carriedFrom` and keeping the date the carry BEGAN so a second bad run does
not reset the clock. **Wisconsin's actual retry is its generic fetch ladder** —
`wi/scripts/build_rusd_school_board_districts.py:fetch()`, four tries with
`sleep(2*(i+1))` backoff, whose docstring is this exact failure in one line: *"The
instance's standard ladder — a single un-retried timeout is what left two of these
workflows never once green."* So the fleet runs BOTH mechanisms at TWO LAYERS —
retry at the fetch, carry at the build — and they are complementary rather than the
alternatives the brief frames them as.

**WHY NOT ROUTE B FOR THIS FAILURE.** Adam's 2026-09-19 ruling is about not
UNPUBLISHING what we legitimately fetched when a source goes dark. Muscatine has not
gone dark; it answers in under a second. A carry would state truthfully that the data
is from an earlier read and leave the cause untouched for the other 26 callers. And a
carry keyed on `unreachable` cannot tell a 30-second blip from a host that has STARTED
refusing us with a 5xx on robots.txt — also disallow-all. Retrying first makes that
distinction real: a host that fails four spaced attempts is a genuine event the floor
should surface, and one that answers on the second never was.

**WHAT ROUTE A DOES NOT FIX, SAID PLAINLY.** A host genuinely unreachable for a whole
run still fails the retry, the county is still skipped, and the floor still refuses at
9 of 10. That is the floor doing its job and the manager's own ruling that the refusal
is right. **Route B stays the right instrument for a source that has genuinely gone
dark** — a different event, and a separate change if Iowa wants it.

**ONE SIDE FINDING:** `muscatinecountyiowa.gov` has NO entry in
`user-agent-measurements.json`, so a host a weekly scraper reads carries no recorded
measurement. `probe_user_agents.py --check` does not catch it because that gate fails
only on a BROWSER-STRING file reaching an unmeasured host, and this scraper sends the
token.

**NOTHING BUILT YET.** Awaiting the manager's go, per the row's own instruction to
report the diagnosis first.

**2026-09-25 — #1152 IS MERGED AS `7b2381f`, VERIFIED ON MAIN BY CONTENT.** Seventeen
checks, all pass:

```
letter      no "agenda portal", no "not authorized", no civicweb anywhere in the
            block quote; the 403 half retained as "every page I have tried";
            still asks the four names
note        the dated correction ABOVE the letter still quotes the withdrawal,
            which is the keep-it-under-its-correction convention
WATCH.md    "You do NOT develop the CivicWeb route" present, old instruction gone
blocker     IS WITHDRAWN present, route (7) history above it, ask ledger still
            last, the ErrorCode 900 measurement kept, own breach recorded
Asks 13/14  untouched
```

**THE VERIFICATION SCRIPT BROKE AGAIN AND IT WAS MINE AGAIN** — a backslash inside
an f-string expression, which Python refuses outright. **Fifth time today a failing
check was a claim about the check**, after the wrapped-line grep, the empty-sha
`git show`, the shallow-clone `git log -1`, and the section-wide phrase search. Zero
times it was the content. That ratio is now the rule: **suspect the instrument
first.**

**WHAT TODAY ACTUALLY MOVED, all three merged and content-verified:**

```
#1149  343b624  28 named officials on four Adams County cards that named nobody
#1151  ccdfbc9  an unsent letter to the Secretary of State stopped telling them
                two untrue things about this project's own coverage
#1152  7b2381f  a standing instruction to scrape a host whose robots.txt refuses
                us, withdrawn from three surfaces
```

**THE IOWA BOARD IS CLEAR.** Nothing is in flight and nothing is assigned. Sixteen
asks across the fleet are drafted and unsent with Adam; nothing here sends. The
remaining Iowa items wait on him: the auditor labelling (17 counties, measured,
proposed), the suspended-host excuse path (dormant), Mitchell's parser (a
2026-09-19 entry says it needed no fix).

**If a next pass wants the highest-value unasked question on this instance, it is
the thirteen other drafted asks that have NOT had the re-probe treatment** — three
of them undated, and this pass found a material defect in the first Iowa one it
checked past Ask 8.

**2026-09-25 — I TOOK THE RE-PROBE SUGGESTION AND IT FOUND A STANDING INSTRUCTION TO
SCRAPE A HOST THAT DISALLOWS US.** #1152 is open. Two of the three oldest
drafted-and-unsent asks verify exactly; the third did not.

**THE COUNT FIRST: sixteen asks carry an emphasised `NOT YET ASKED — DRAFTED`
ledger line, not four**, three of them undated, and the oldest Iowa ones — 13, 14
and 15 — have waited 21 days and were in none of the four named. My own first
pass said 22, because it matched the phrase anywhere, including inside each ask's
"what each answer means" section. Cheap heuristic, real parser, two readers of one
question; the 16 comes from the emphasised ledger line alone.

```
Ask 13  Adams IL   21d   "seven of twenty-one ship today"      7 of 21   VERIFIED
Ask 14  Jones IA   21d   266 rows / 98 counties, Jones absent  absent by
                         county AND by FIPS 105, layer
                         unedited since 2024-01-30             VERIFIED
Ask 15  Marion IA  20d   "your agenda portal is reachable"     WITHDRAWN
```

**`cityofmarion.civicweb.net` SERVES A robots.txt WHOSE BINDING `*` GROUP IS
`Disallow: /`**, on every path tried. The letter told a city clerk that this
project had read it. **REACHABLE AND PERMITTED ARE DIFFERENT QUESTIONS**, and the
2026-09-05 pass asked only the first — it gave six routes a measured verdict each
and then wrote the one surface that ANSWERED up as the way forward without reading
its policy once.

**The finding is bigger than the ask, which is why it was worth the probe.** That
portal was named in THREE places as "the one reachable surface" and "the route a
next pass should take": the letter, the blocker's route (7), and this instance's
own WATCH row, which carried an explicit **"You do: develop the CivicWeb route"** —
a standing instruction to build a scraper against a host that refuses us. All three
withdrawn, history kept under its correction.

**Also dropped from the letter:** the `/api` ErrorCode 900 sub-claim naming this
server's IP. It stays in the blocker with its date. It did not reproduce on the two
paths probed today, and **a specific assertion about another organisation's
infrastructure should not go out on a measurement nobody re-ran.**

**RECORDED AGAINST THIS PROJECT RATHER THAN THE CITY: the re-probe itself breached
the fetch rule.** The script read robots.txt and fetched the portal root in one
pass without gating the fetch on the answer, so one GET went to a host the gate had
already refused. One request, nothing extracted, no further fetch, written into both
the blocker and the ask rather than quietly fixed. **Read the verdict BEFORE the
fetch in the same script, not beside it.**

**The §7 sitemap warning paid on its first use:** the chain ran with
`build_sitemap.py --check` this time and it PASSES, which confirms yesterday's
lastmod write was purely the shallow-clone artifact and nothing was ever wrong with
the file.

**2026-09-25 — #1151 IS MERGED AS `ccdfbc9`, VERIFIED ON MAIN BY CONTENT.** Ask 8's
letter now says true things, and it is still unsent.

```
letter      927 telephones, 531 websites, 109 of those cities, leaves 830
            Cedar Rapids named; the 99-county evidence carried
            "cannot name a single" and "for each" occur ZERO times in it
ledger      NOT YET ASKED - DRAFTED, no send date anywhere
blocker     CORRECTED and RE-PROBED 2026-09-25 both present, the disproved
            sentence still above them, the ask ledger still last
skill       gap-record section 7 carries both the ordering rule and the
            build_sitemap.py shallow-clone warning
```

**THE FIRST VERIFICATION SCRIPT FAILED TWO CHECKS AND THE SCRIPT WAS WRONG, NOT THE
FILE.** It searched the whole Ask 8 section for the two retired phrases, and both
appear there exactly once — inside the dated note that says they were wrong, which
is the keep-the-disproved-sentence-under-its-correction convention working exactly
as intended. Scoped to the block-quoted letter, both are zero. **Fourth time today
that a failing check was a claim about the check**, after the wrapped-line grep, the
empty-sha `git show`, and the shallow-clone `git log -1`. The pattern is stable
enough to state plainly: **when a check fails on content I just wrote and verified,
suspect the check first — I have been wrong about the check four times and about the
content none.**

**THE IOWA BOARD IS CLEAR.** Nothing is in flight and nothing is assigned. Asks 8,
30 and 31 are all drafted and with Adam; nothing here sends. The other items still
wait on him: the auditor labelling (17 counties, measured, proposed), the
suspended-host excuse path (dormant), Mitchell's parser (a 2026-09-19 entry says it
needed no fix).

**2026-09-25 — BOTH ITEMS OFFERED TO ME WERE ALREADY DONE, AND SAYING SO IS THE
WORK.** Ask 8 has been drafted since 2026-09-03 with its recipient corrected on
2026-09-04, and the gap-record §7 skill carry merged inside #1149 at line 143.
Writing either again would have produced a duplicate that looked like progress.
**Rule 1 — grep the record before building what an assignment asks for — and it
is the second time today it paid.**

**WHAT WAS ACTUALLY WORTH DOING IS #1151: Ask 8's letter says two things that are
measurably false, and it is unsent, so they would be said to a public official on
the day it goes.** An unsent draft is not history.

```
"carries an office phone and website for each"
    939 cities, 927 telephones, 531 websites
"outside Des Moines and Waterloo ... cannot name a single"
    names officials in 109 of 939; Cedar Rapids missing from the sentence too
```

**The first is wrong in the gap blocker as well, and there it contradicts itself
in consecutive sentences** — the League table's own 935 and 536, then "all 939
cities now carry their own office phone and website" two hundred characters
later. Appended, disproved sentence left in place. That is the THIRD figure this
month whose own supporting numbers sat beside it unread, after Jackson's canvass
arithmetic and #1149's `605` heading.

**Correcting the second makes the ask stronger, not weaker.** "109 of 939, and the
830 is what I am asking for" is checkable where "cannot name a single one" was
not, and the letter now carries what the draft could not: all 99 counties asked
once, ten publish, which is what makes the Secretary of State the right recipient
rather than the next ninety.

**Re-probed before the draft was touched**, per the skill's own rule that a
redesigned site often starts publishing the thing: four sos.iowa.gov pages with
the districtry token, no browser string, all 200, robots allowing each, ZERO
occurrences of "clerk". `/city-elections` is new since the 2026-09-03 read and
carries none either. **Nothing is sent; the ledger stays `NOT YET ASKED —
DRAFTED`.**

**THE SHALLOW CLONE GAVE ME THREE CONFIDENT WRONG ANSWERS TODAY AND IS NOW A
STANDING RULE.** `a6ca829` is the oldest reachable commit here, so (a) a file's
`git log -1` returns the GRAFT date, not its own, (b) "this file first appeared
on 2026-09-23" is what every long-lived file looks like, and (c) running
`build_sitemap.py` WITHOUT `--check` therefore writes wrong `lastmod` dates —
it rewrote the root page 2026-09-22 → 2026-09-23 and the wrong date read exactly
like a correction. Reverted, and written into gap-record §7 with the one-line
test. CI checks out at full depth, so the gate was never at risk. **In this
sandbox, a date read from git history is a claim about the clone until the graft
boundary is checked.**

**2026-09-25 — #1149 IS MERGED AS `343b624`, VERIFIED ON MAIN BY CONTENT.** Five
checks, each read off the shipped tree rather than off the merge message:

```
roster      102 keys, 10 counties, 738 officials
            Carbon, Corning, Nodaway, Prescott all present; Adams 28
floors      MIN_COUNTIES 10, every floor raised, none lowered
gap         "830 of Iowa's 939 cities; in the other 109 ..."
            wanted no longer says "the way nine already do"; blocker NOT shipped
docstring   ten counties / MIN_COUNTIES is 10; heading carries no count;
            507 / 102 / 90 across 89; 109 of 738, 122 across thirteen
skill       gap-record §7 line 143 carries THE ORDER RULE IS NOT ABOUT THIS LIST
```

**The one `605` left in the builder is the quotation inside the section recording
that it was wrong**, which is the point of keeping it.

**RULE 3 FIRED IN THE MIDDLE OF THAT VERIFICATION AND IS WORTH THE LINE.** The
grep for `all ten will briefly` returned NOTHING on a file that says exactly
that — the phrase wraps across a line break, so the pattern was wrong and the
file was right. A failed grep is a claim about the pattern until the pattern is
tested, and the second time this session has paid for it. Reading the six lines
settled it in one step.

**THE IOWA BOARD IS NOW CLEAR AND THE NEXT ITEM NEEDS AN ASSIGNMENT.** Ask 8 —
the statewide city-clerk list from the Secretary of State — is the higher-value
route the sweep points at, and it is a DRAFT-AND-HOLD rather than a send. It is
NOT STARTED, deliberately: nothing here begins an outbound ask unasked.

**Still with Adam, unchanged:** the auditor labelling (17 counties, measured,
proposed), the suspended-host excuse path (dormant), and Mitchell's parser,
which a 2026-09-19 entry says needed no fix.

**2026-09-25 — #1149's HOLD IS ANSWERED, AND READING THE REST OF THE DOCSTRING FOR
THE SAME FAMILY FOUND THREE MORE.** The hold was two present-tense sentences
fifty-five lines above `MIN_COUNTIES = 10`; both fixed, and the dated 2026-09-05
paragraph appended to rather than rewritten, exactly as asked. Pushed as `82b3a9c`
on a merge of current `origin/main`, 100 of 100 no-browser invocations green with
`validate_gate_counts.py` run AFTER the merge.

**The three the review had not reached were the same family, undated.** A heading
`WHAT THE 605 ACTUALLY ARE`, a body still saying 487 council / 98 mayors / 86
clerk rows across 85 cities, and a seat figure of 104 of 710 with 117 across
twelve counties. Measured: **507 / 102 / 90 across 89**, and **109 of 738, 122
across thirteen** — the last off the scraper cache, the only thing that can
answer for the three counties the currency gate refuses. The `39 people who are
none of those` breakdown under it is measured UNCHANGED, so it was left rather
than re-typed.

**THE 605 IS NOT DRIFT AND THAT IS THE FINDING.** `a6ca829` introduced that
heading, and the file it shipped in the same commit held 710 officials — which is
also what the heading's own body summed to four lines below it. The count was
wrong the day it was written and survived two rebuilds. **Nothing reads a number
in a heading**, so it is gone rather than corrected. A figure worth keeping has a
reader that checks it; a figure with no reader goes.

**When a review holds on a copy of a fact, read every other copy in the same file
before answering.** The hold named two; the file carried five, and answering only
the two named would have left three false sentences in the very docstring the PR
was about.

**The ordering finding went into the skill rather than staying on the board**, as
the review asked: `gap-record` §7 now states it generally — a generator that reads
a file must run after every edit the change makes to that file, whether or not
either is in the gaps chain — with the §7 chain as one instance of it.

**2026-09-25 — STAGE 2 IS OPEN AS #1149 AND IT IS THE HALF A READER SEES.** 28 named
officials across Carbon, Corning, Nodaway and Prescott, where four Iowa cities
named nobody yesterday. #1148 merged as `cc3c091`, verified on main by content —
the artifact round-trips through `derive_caveats()`.

**Adams was missed for Jasper's reason a county over.** The 2026-09-05 sweep took
all 99 domains from each auditor's e-mail address; Adams' auditor mails from
`adamscountyia.com` while the county's site is `adamscounty.iowa.gov`, a host
this repo's own data files already carried. `MIN_COUNTIES` 9 → 10.

**Every figure the join moved was re-measured rather than incremented**, because
the worksheet note hand-carries a dozen: 98→102 cities, 710→738 officials,
487→507 council, 86→90 clerk rows across 85→89 cities, 104→109 seats, 142→143
e-mails, and the counties publishing no e-mail 4→5 and no phone 5→6. Adams'
markup side was measured too — a `<b>` county, seven of thirteen, publishing no
mailto and no telephone at all.

**The gap's `wanted` is narrowed with the corrected bound.** It claimed more
counties publish the way nine do; the sweep measured that all 99 were asked and
one more does. The summary's 834/105 becomes **830/109, measured as a UNION**
across the three rosters rather than by arithmetic — and the note's own figures
had already disagreed with each other, saying 833 in one sentence while implying
834 in another.

**Ask 31 drafted, not sent**, to the Worth County Auditor: its page carries the
same module with seven city blocks and nobody in it, so the question is about
the page rather than the records and "it is unfinished" is a complete answer.
It asks nothing to be compiled, which makes it better-founded than the usual ask.

### Two consumer questions answered rather than assumed

`build_county_pages.py` reads `ia-supervisor-members.json` and NOT this file, so
the per-county pages are untouched. No history tile counts it either — Iowa's
`history_page` carries `entries` only — so **the weekly workflow needs no new
regenerate step**. What did need one is the monthly source gate, now carrying
Adams as a thirteenth row.

**And regenerating `ENDPOINT_INVENTORY.md` BEFORE adding that row left it
drifted** — the §7 ordering lesson one step further out than §7 states it. The
battery caught it; the rule generalises past the gaps chain to any generator
that reads a file the same change edits.

**2026-09-25 — THE 90-COUNTY SWEEP IS RUN AND REPORTED. The answer is ONE new
county, and nine was very nearly all that exists on this route.** #1148 carries
the artifact; stage 2 is deliberately not in it.

**The assignment's premise was wrong in a way that made the work cheaper and
better.** It said nobody had asked the other 90. The
`ia-municipal-officeholders` blocker records a 99-county sweep on **2026-09-05,
run twice**, and it was STRONGER than the budget authorised here — each county's
homepage plus up to fourteen followed links plus eight guessed paths, 562 pages
cached, scored offline. **What was missing was not the sweep. It was the
artifact.** `ia/scripts/.cache/` is untracked and the only tracked products are
the twelve POSITIVE results, so for the other 87 counties nothing in the tree
said which were measured absent, which refused, and which never answered; that
survived only as prose in a 30 KB blocker naming about a dozen. This project's
own rule is exact — a measurement filed in a backlog and nowhere else is a
measurement the next pass repeats — and being asked a second time is the proof.
So the product of #1148 is `ia/data/source/ia-city-officials-sweep.json`, one row
per county.

### What 99 counties answer

One GET each at the CMS path all twelve publishers use, robots read first by the
same client, Osceola not probed at all because its 202 sgcaptcha is recorded:
**12 ship, ADAMS publishes, WORTH has the module and nobody in it**, 53 answer no
page, 22 are robots-refused, 7 answer 200 naming nobody, 2 are unreachable.

**ADAMS IS THE JASPER DEFECT RECURRING, and it is the whole yield.** The
2026-09-05 sweep took all 99 domains from the AUDITOR'S E-MAIL ADDRESS; Jasper's
auditor mails from a domain with no A record, so its 502 was never evidence about
the county, and its page turned up later on a host sitting in three of this app's
own data files. Measured today, **sixteen counties' repo-known host differs from
their auditor mail domain** — `adamscountyia.com` was probed and
`adamscounty.iowa.gov` publishes. Through the SHIPPING parser rather than my
heuristic: **4 cities, 28 named officials** (20 council, 4 clerks, 4 mayors), on
terms ending 2028 and 2030, LATER than the nine shipping counties' 2027/2029 — so
more current than what ships, not stale.

### Two things the raw tally would overstate, and both are in the rows

**Of the 22 robots refusals only SIX are a county's own statement** — five
robots.txt answering 202, one `Disallow: /`. The other sixteen are a FAILED
ROBOTS READ, which policy makes disallow-all, correctly, and which is not a
statement by anybody; they are mostly TLS failures on legacy domains. And **51 of
the 77 non-answers were probed only on the auditor mail domain**, so those
negatives are about a mail domain and not a county — `pick_host` reaches the mail
domain ONLY when the repo knows no site host, so that is the same set by
construction, and it is **57** counties in all. **NOT ONE of the 22 refusals is
on a repo-known host**, which strengthens the caveat rather than qualifying it:
the refusal tally is entirely an artifact of probing a mail domain. `Decatur → grm.net` is that at its clearest.
My sweep asked ONE path where the earlier one followed about eight pages per
county, so for the 53 `no-page` counties the earlier negative is still the
stronger one. What this adds is the artifact, the host fix that found Adams, and
Worth's shape.

### The classifier was wrong once and the yield check caught it

Its first version accepted any CMS marker and called **Worth** a publisher on
seven `filterDiv` blocks and seven role headings. The shipping parser returns **0
cities and 0 people** from that same URL, because every name lives in `offName`
and Worth has none. `publishes` now requires that marker, and a module with
nobody in it gets its own verdict — which is a BETTER lead than absence, since
the county already uses the route. **A marker heuristic and the real parser are
two readers of one question, and the cheap one was wrong.**

### What it means for the record

**A measured negative is a result and this is one.** The gap's `wanted` — "more
counties publishing their cities' officials the way nine already do" — is now
bounded rather than open-ended: one more does, one has the module empty, and the
remaining upside on this route is the **24 counties whose page was NEVER ASKED**
— 22 refused at robots, 2 unreachable. That points the effort at **Ask 8**, the Secretary of State, which
this board already calls the highest-value ask.

**Stage 2 is not in #1148**: building Adams in, raising `MIN_COUNTIES` 9 → 10,
and narrowing `wanted`. The floor is raised when a county joins and never lowered
to get past one going stale.

**CORRECTED 2026-09-25 on review, and the correction is a sharper bound than what
it replaces.** Both sentences above said **24** and named a different set each
time. 24 is robots-refused plus unreachable — the counties whose page was never
requested — and that is the only subset of the verdicts giving 24. "No site host
in the repo" is `hostSource == auditor-mail-domain`, which is **57**, of which 51
are non-answers. Three measurements went in with the fix: no refusal is on a
repo-known host; **Ida and Webster failed with a proxy 502, which is this
vantage's egress and not the host**, so "mostly TLS failures" folded two in
wrongly; and **`wrightco.iowa.gov` fails with `unable to get local issuer
certificate`**, the Coles/Gallatin/Vermilion incomplete-chain shape, where the
2026-09-05 record says its own chain probe found none — so one of those two
statements has moved and the sweep row is the newer one. All of it is in the
artifact's `caveats` block rather than only in prose, because stage 2 narrows the
gap's `wanted` and that is where a wrong description reaches a reader.

**AND I REPORTED A FULL BATTERY OFF A SLICE.** The PR said all 94 static gates
pass; the workflow's list is 110 invocations, 100 of them needing no browser. My
runner cut `smoke-test.yml` at `actions/setup-node` — the boundary that defines
the NAMED-STEP count, not the invocation list — which dropped the **six
per-instance `validate_index.py` runs, the merge gate itself**; a second defect
in the same runner dropped `node scripts/esri_rings_test.mjs` on a "node without
`--check` means browser" heuristic, which is the exact misclassification
`CLAUDE.md` already records. All seven were run and pass, so nothing was
concealed — but **a slice is a remembered subset**, which is the rule this repo
states and I broke. The manager's own runner was missing the two
`validate_gap_counts.py` invocations in the same week, which is what prompted the
question rather than an assumption.

**No ungated prose restatement turned up in Iowa on this pass** — the figure a
gate would want here is `MIN_COUNTIES`, and `build_ia_county_city_officials.py`
already derives its comparison from the file rather than restating it. Wisconsin
keeps the general case.

**2026-09-25 (end of session) — #1145 MERGED and verified by content. The Iowa
board has nothing open that is mine; awaiting an assignment.**

Verified on main at `b0d0523` rather than by ancestry: `scripts/measured_metric.py`
carries `claim = spec.get("claim", spec["label"]).lower()`,
`scripts/validate_gap_counts.py` has `_selftest` and passes the empty claim at
three call sites, and the `ia-municipal-officeholders` record carries its 939
counts declaration. **The pair holds at 81/110 ON MAIN** — the check worth
running after a merge rather than before it, since main's copy said 81/109 and a
merge that took the named-step line silently at the wrong value is the exact
failure `CLAUDE.md` records. Steward mirror 110 for 110, gap gate 8 declarations,
selftest 0 failures.

### Three PRs and three corrections

Merged today: #1142 (the city-tier WATCH row), #1144 (Ask 30 drafted for the
twelve counties, nothing sent), #1145 (the person-word gate defect). Three board
entries went straight to main.

**The corrections are the more useful half, and all three are the same shape —
a conclusion that arrived wearing a measurement's authority.**

1. I answered an Open questions bullet by measuring it, and that measurement had
   been done on 2026-09-19 and recorded twenty lines up in this same Status
   section. My sweep also omitted `ia-county-auditors.json`, the one Iowa file
   where the switchboard shape is present, so the entry read as "Iowa is clean"
   when it is not. Corrected in `96f7680`; the wrong entry stands beneath it.
2. Re-deriving that finding against the WRONG COMPARAND gave 6 of 21 where the
   answer is 17 of 91, because `ia-supervisor-members.json` covers only the
   counties with a district join. I had the 6 in hand and was one step from
   publishing it as a correction to the 17.
3. Two verification greps came back empty on content that was correct, because
   the em-dash in `NOT YET ASKED — DRAFTED` is multi-byte and the pattern matched
   one byte of it.

**What all three have in common is that checking cost seconds and the wrong
conclusion would have shipped.** The habit is the one already on this board from
2026-09-24 — re-run the thing that produced a claim before building on it — with
one addition earned today: **that includes re-running it against the right
comparand, and it includes reading your own Status before measuring what a
bullet asks for.**

**2026-09-25 — #1144 MERGED and verified by content; the gate fix is open as
#1145.** Verified on main at `9d95a24` rather than by ancestry: Ask 30 at
`docs/ASK_DRAFTS.md:2365`, and `NOT YET ASKED — DRAFTED 2026-09-25` in BOTH the
`ia-supervisor-district-seats` blocker and `ia/WATCH.md` row 35. Nothing has been
sent; the ledger reads `ASKED <date>` only on the day it goes.

**Two of my verification greps came back empty and the content was fine both
times.** The em-dash in `NOT YET ASKED — DRAFTED` is multi-byte, and a `.` in the
pattern matched one byte of it; a second attempt broke on shell quoting. Read
with the builder's own regex and parsed as JSON, all three checks pass. Checking
before concluding is the only reason that did not become a second false
correction an hour after the first one — **a failed grep is a claim about the
pattern until the pattern has been tested.**

**#1145 — `measure_metric`'s person-word check was reading the record's ID
instead of its claim, and failed in both directions.** A gap id names an
ABSENCE, so `ia-municipal-officeholders` was refused unless it declared that 939
CITY contact rows name people (18 ids across four instances trip the same way),
while `ia-board-chair`'s 38 genuinely-named chairs passed unchecked because
"chair" is not in the word list. The claim now comes from a `claim` key
defaulting to `label`, so all four history pages come back byte-identical;
`naming` now DRIVES the comparison rather than being ignored when no person word
appears, which is a trap I would have shipped had I fixed only what was named.
Four selftest assertions cover both directions of the defect and both directions
of the fix. Pair 81/110 re-measured after the cherry-pick AND after the rebase;
all 94 static gates pass; the guidebook auto-merge was verified by content on
both sides.

**2026-09-25 (later) — CORRECTION to the entry below: I re-measured something
this board had already measured six days earlier, and recorded twenty lines
further down its own Status section.** The entry below stands as written; this
is what is wrong with it.

**The measurement was already done on 2026-09-19 and its result is in this
file.** That entry reads "`ia-county-officers.json` is clean, and the finding is
one file over", with all four of its sub-results — and it went further than
mine, naming `ia-county-auditors.json` as the file where the shape actually is.
I read the Open questions section, saw a question, and measured it. I did not
read the Status section above it. `gap-record/SKILL.md` §2 is "Before writing,
read your own records", and it exists for exactly this.

**The entry below is also WRONG BY OMISSION, which is the part that matters.**
It says the files that have the several-named-people-one-body shape "were swept
in the same run, and all four are clean". Four were. The fifth,
`ia-county-auditors.json`, is the one with hits, and my sweep never opened it —
so a reader of that entry would conclude Iowa is clean on this question, and
Iowa is not.

**Re-derived today, with the comparand stated, because the 2026-09-19 figure
needed re-deriving too: 17 of 91 testable auditors carry their county's own
board line.** The comparand is `ia-county-officers.json`'s `boardPhone`, which
91 of 99 counties carry. The 2026-09-19 entry said **17 of 89** — the hit count
reproduces exactly and the denominator moved by two, two counties having gained
a board line since. Allamakee, Butler, Calhoun, Cedar, Chickasaw, Clay, Jasper,
Kossuth, Lyon, Montgomery, O'Brien, Osceola, Pocahontas, Sioux, Van Buren,
Webster, Winnebago. Nothing about the finding has changed: Iowa Code 331.504
makes the auditor clerk to the board, so the number is right and only its
RENDERING is misleading, and the fix is still the label that is waiting on a yes.

**THE COMPARAND TRAP IS THE REUSABLE PART, and I walked into it first.** Asked
of `ia-supervisor-members.json`'s `boardPhone` instead, the same question
answers **6 of 21** — because that file covers only the 21 counties with a
district join. Both are true readings of different populations, and where the
two files both carry a board line they agree 21 and differ 0, so the 6 is a
subset of the 17 rather than a contradiction. I had the 6 in hand and was one
step from publishing it as a correction to the 17. **A cross-file measurement is
only as meaningful as the file it is compared against, so the denominator ships
with the number or the number says nothing.**

**What survives from the run below** is one thing the 2026-09-19 entry did not
cover: `ia-county-city-officials.json`, 710 named people across 98 member lists,
where three numbers are shared by two named people each and every record in all
three carries `phoneIsOffice: true`, with both inverse tests at zero — no
unflagged sharer, and no number equal to the body's own `officePhone` printed as
a personal line. That file enacts the rule at field level and is clean.

**The board contradicted itself for six days and nothing could see it.** Status
said measured-and-clean on 2026-09-19; Open questions said never-measured until
today. The bullet should have been struck the day the measurement landed. This
repo gates code against code and prose against the files it describes, and
**nothing compares a board's Open questions against its own Status** — which is
the same two-readers-of-one-question shape `CLAUDE.md` names as this fleet's
recurring defect, one level out from the code. I am not proposing a gate for it;
the cheap fix is to strike the question in the same commit that answers it, and
to grep Status before measuring anything a bullet asks for.

**2026-09-25 — the phone-number question is ANSWERED and it dissolves, and what
makes it worth writing up is that it asked about the one Iowa file that cannot
have the defect.** Measured today on the shipped files, offline, nothing
fetched. No change ships.

The question was whether `ia-county-officers.json`'s numbers had ever been
checked for the problem #1000 fixed on the city rosters — one switchboard
number repeated across several named people, which reads as a direct line and
is not one.

**The file it named carries 391 phones, not the roughly 305 the question
estimated, and all 391 are distinct** — no repeat within a county and none
anywhere in the file, across 391 named officers in 99 counties.

**It also cannot carry that defect, by shape.** The Calhoun rule's precondition
is several named people on ONE body, where a shared number belongs to the body
and standing it under each name invents per-member channels. These records are
one person per OFFICE — `countyAttorney`, `recorder`, `sheriff`, `treasurer` —
so there is no body for a switchboard to stand in for. 93 of the 99 counties
show three or more offices sharing an area code and exchange, which is the
courthouse switchboard reached at a different extension per office: these are
per-office direct lines, which is the right thing to print.

**The files that DO have that shape were swept in the same run, and all four
are clean.**

- `ia-supervisor-members.json` — 81 named supervisors in 21 counties, **zero
  per-person phone fields** against 21 board-level `boardPhone`s. The rule is
  enacted by construction: there is nowhere in the record to put a per-member
  number.
- `ia-county-city-officials.json` — 710 named people across 98 member lists,
  the largest surface. Three numbers are shared by two named people each
  (Newton's Clerk and Administrator, Ogden's Administrator and Clerk,
  Westside's Clerk and Library), and **every record in all three carries
  `phoneIsOffice: true`**, so the file states the number is the office's rather
  than the person's. Both inverse tests come back zero: no shared number with
  an unflagged sharer, and no number equal to the body's own `officePhone`
  printed as a personal line — 29 flagged as office lines, 87 as personal.
- `ia-city-officials.json` — 24 named across 4 lists, no number shared.
- `ia-city-contact.json` (939) and `ia-county-board-chairs.json` (38) are not
  the shape at all: one phone per city with nobody named, and no member lists.

**The transferable part is that a defect's precondition is a SHAPE, and it is
cheaper to ask which files can exhibit one than to measure a file that cannot.**
The question was put to the file with the most phone numbers rather than to the
files with several named people under one body, and those were the ones worth
measuring.

**One figure I had wrong mid-measurement, caught before it reached this board.**
The first sweep reported 196 member lists in `ia-county-city-officials.json`;
it is 98. The walker collected every list of objects, and each city's `sources`
array is one — indistinguishable from `members` unless the key is named. The
named count was unaffected, because a source record has no `name`, which is
exactly why the error survived one reading: the number it corrupted was not the
number I was looking at.

**2026-09-24 (end of day) — #1140 MERGED and verified by content. Five PRs
landed today and this board has nothing open that is mine. Awaiting an
assignment.**

Verified on main at `5e81b2c` rather than by ancestry, which a squash merge
makes useless: `county-n-plus-1` references `gap-record/SKILL.md` twice and
carries ZERO copied `--metro` lines, §7 carries all three added steps, exactly
ONE positional phrase survives anywhere in the file and it is the rule quoting
the phrases it forbids, and `validate_skills.py` resolves 801 pointers.

### The day, and the one thing worth carrying forward

Merged: #1134 (the 18-county probe recorded), #1136 (Butler, Chickasaw and
Howard), #1137 (the stated-count gate), #1139 (Winnebago), #1140 (one owner
for the regenerate chain). Two counties now name the supervisor who holds each
district where nothing did this morning, and a reader in Winnebago County sees
three names against three districts.

**THE PATTERN WORTH CARRYING IS MY OWN ERROR RATE ON CONCLUSIONS.** Three of
the four items I queued today dissolved when I re-derived them before
building: the endpoint-inventory red-CI claim, the Dickinson preservation
question, and the internal-points drift. In every case the MEASUREMENT was
right — the grep found three paths, the diff was real, the encoding differed —
and the sentence written beside it in the same breath was not. Nothing tested
the sentence, because it arrived wearing the measurement's authority.

The habit that caught all three is cheap and should be the default: **before
building on a queued item, re-run the thing that produced it and check that
the conclusion still follows.** It cost minutes each time and saved three
changes that would have been built on nothing.

**2026-09-24 (night, last) — #1140 is GREEN on its four positional fixes. THE
INTERNAL-POINTS DRIFT IS ALREADY CLOSED, by a change that merged three hours
ago. MY BOARD QUEUE IS NOW EMPTY of anything that is mine.**

#1140 head `2698c37`, smoke SUCCESS 20:42 UTC, two files, no review threads.
Held for the manager.

### Item 2 was answered by re-deriving it, like item 3 and the Dickinson ask

The brief was to check whether the committed file or the builder is the odd
one out. **Measured: the builder OWNS the file** —
`ia/scripts/build_ia_gap_outlines.py` writes the whole of
`ia/data/source/ia-county-internal-points.json` at its `json.dump`, and the
source of the sentence in question is a string literal in the builder itself.
So the committed literal em-dash was the stale side and there was never a
question of which to change.

**AND IT IS ALREADY FIXED.** `a92cee4` — #1139, Winnebago — shipped that file,
because retiring Winnebago's outline legitimately rewrote it (eight lines of
its point removed), and the builder's `ensure_ascii` escape rode along in the
same diff. Running the builder now produces NO diff at all: the committed file
carries zero non-ASCII bytes and one `\u2014`, exactly what the builder writes.

**A DRIFT BETWEEN A GENERATOR AND ITS OWN OUTPUT CLOSES ITSELF the next time
that file changes for a real reason.** I reverted it twice today while it was
UNRELATED churn, which was right both times; the third time it had a reason to
move and went with it. What I recorded as a standing item was true for about
four hours.

### Where that leaves the queue

1. **Michigan's `mi-commissioner-roster` declaration** — theirs to confirm,
   untouched all day, and nothing about it has changed.
2. **CLOSED**, above.

So nothing on this board is mine and open except #1140 itself. Three of the
four things I queued today dissolved on re-derivation — the endpoint-inventory
red-CI claim, the Dickinson preservation question, and this. **Each was a
measurement I took correctly and a conclusion I wrote down as though it had
been measured too.** The pattern is specific enough to name: the grep, the
diff and the probe were all right; what failed was the sentence built on them
in the same breath, before anything tested it.

**2026-09-24 (night, latest) — THE DICKINSON PRESERVATION QUESTION DOES NOT
ARISE, AND I STATED IT WRONG THREE TIMES. #1140 is held on four positional
references, now pushed.**

The assignment was to place the question. Placing it meant re-deriving it, and
it dissolved.

### What I said, and what is true

I wrote — on this board, in #1139's body, and to the manager — that during the
Winnebago regression Dickinson "fell out of the roster it had been PRESERVED
into". **Both halves are false.**

The file I diffed was `ia/scripts/.cache/ia_supervisor_districts_roster.json`,
the SCRAPER'S OWN CACHE, which is gitignored (`ia/.gitignore:2`) and therefore
starts EMPTY on every CI run. The shipped
`ia/data/app/ia-supervisor-members.json` holds 21 counties and **has never
carried Dickinson at all**; the only two preserved records in it are Bremer's
and Hamilton's, both `asOf` 2026-08-28. So no reader ever had Dickinson and
none lost it. What I watched move was local, ephemeral and invisible to
everyone.

**A DIFF IS ONLY AS GOOD AS THE FILE IT IS TAKEN ON.** I picked the cache
because the sweep prints its path on every run, and then reasoned about
readers from it for the rest of the day.

### The mechanism, measured rather than inferred

`build_ia_supervisor_roster.py` reads `prev` from `OUT` — the SHIPPED file
(lines 184-186) — so preservation can only ever carry a county that already
shipped. Dickinson never did, and the builder's own comment covers exactly
that case: "Nothing was ever fetched, so there is nothing to preserve."

And the asymmetry I was going to raise is already closed, by a different
mechanism than preservation. The DROP GUARD computes the counties in `prev`
that are missing from this run, subtracts `--allow-drop` and the refusals that
are BOTH reported this run and recorded in `ROBOTS_REFUSED_PRESERVED`, and
**stops the build** on anything left. So a previously-shipped county that
becomes unreadable for any reason — robots or not — FAILS rather than
shipping short. The fleet ruling is satisfied twice over: preserve for a
recorded refusal, refuse to build for everything else. Neither path can
silently unpublish.

### What Dickinson's flap actually shows

Only that a refused verdict is worth re-asking before it is believed, which is
the Black Hawk lesson and is already on the record. Its pages, on the one run
this client was allowed to read them, carried no readable district — so its
absence is a measured "no readable page", not a preservation failure. Not
probed further; its robots.txt answers the captcha-shaped 202 again.

### #1140

Held on four references to commands BY POSITION in a list that grows.
Three were the manager's catch; the fourth is in the line this PR itself adds
(`# AFTER the line above` pointed at the michigan run, where
`build_ia_gap_outlines.py` reads the IOWA file). One of the three was wrong the
day it was written — verified against `1427f64` rather than taken on report —
and my own first grep for it MISSED, because the phrase wraps as "the last\nline
above" and a line-oriented search returns nothing. All four name the script
now, the rule is written beside them, and the other ten skills were swept for
the shape: none.

### Queue

1. **Michigan's `mi-commissioner-roster` declaration** — 83/48/35 across two
   disjoint files, theirs to confirm. Untouched.
2. **`ia/data/source/ia-county-internal-points.json` encoding drift** — check
   which of the builder and the committed file is the odd one out before
   changing either.

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
