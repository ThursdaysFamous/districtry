# Wisconsin board

Owner session: **Wisconsin**. Manager owns *Tasks*; this session owns *Status*
and *Open questions*. Rules and reporting posture: `BOARD.md` at the repo root.
Commit board edits straight to main, in their own commit, dated.

## What a reader gets today

Click any point in Wisconsin and the app answers from **31 layers**, across all
72 counties. County board supervisors, circuit judges, county officers and the
Milwaukee and Racine school boards all name people.

**10 recorded gaps** — 8 data-quality, 2 no-source.

## Tasks — manager owns this section

| task | state | opened | notes |
|---|---|---|---|
| **The legislature roster is frozen at its 2026-09-15 reading — one unretried timeout** | **open, measured 2026-09-24** | 2026-09-24 | `update-wi-legislature-roster.yml` is the ONLY row left on #387 after tonight's run (down from four). Run `35762232826`, 2026-09-22T17:40, schedule, main: step 4 "Scrape the legislature's own office pages" died after 61s with `urllib.error.URLError: <urlopen error timed out>` and steps 5-8 skipped, so no PR opened and `wi/data/app` keeps its 15 September reading. **The host is one CLAUDE.md already records as intermittent from this vantage** — `docs.legis.wisconsin.gov` read `token-ok` on 2026-09-12 and timed out on every rung on 2026-09-13. So this looks like the shape #982 taught on Will County: a single failed read freezing a roster for a week because nothing retries. The cron is weekly, so the next run is ~2026-09-29 and the roster stays frozen until then. **Not diagnosed further and not touched** — whether to give this scrape the shared retry/backoff loop other scrapers use, or to dispatch the workflow now to confirm it is transient, is Wisconsin's call. Preserving the last-good reading is already correct; what is missing is a retry, and possibly a dispatch to find out which. |
| **The NG911 geometry is one edit stale, found by running the new watcher's own job** | **open 2026-09-22** | 2026-09-22 | Not caused by #1099 and not part of it — surfaced because I ran `wi/scripts/validate_sources.py` live to verify the new supervisory rows. All four NG911 layers WARN: **edited 2026-09-14 against the 2026-09-08 the shipped files were built from, with every row count unchanged** (ems 2,478, fire 3,046, law 3,095, psap 208). That is exactly the redraw-without-a-count-move case the NG911 sidecar was written for, working as designed. The monthly run on 1 October would have reported it; it is here now instead. Remedy is the one the report prints: re-run `wi/scripts/build_wi_ng911_service_areas.py`, bump `cache_name` in `wi/metro-worksheet.json` because these are cache-first, and commit the rebuilt files with the refreshed sidecar. |
| **The LTSB filing watcher — Adam took it, and it is SMALLER than your proposal** | **merged #1099 `42f034c`** | 2026-09-22 | You proposed a semiannual watcher on the LTSB filing, pointed at the geometry rather than its restatement. Adam took it. **Two things I measured that change the shape, both of which make it smaller.** (1) **The monthly job already reaches LTSB.** `wi/scripts/validate_sources.py` carries the supervisory layer in its manifest with a good note, and `wi-validate-sources.yml` runs it on the 1st and opens one standing issue. So this is not a new workflow and not a new cron — the row proves REACHABILITY and compares nothing, which is the whole hole. (2) **You already built the right mechanism, for a different layer, and wrote down why.** `_check_shipped_is_current` compares a builder-written sidecar (`rows` + `dataLastEdit`) against the live service for NG911, WARN not FAIL because falling behind between operator builds is the normal state. Its own comment records the lesson that applies here exactly: *"A ROW COUNT CANNOT SEE A REDRAW"* — the OEC moved boundaries in 397 features on 2026-08-31 while three of four row counts did not move at all. **So: give `build_wi_supervisory_districts.py` a sidecar and let the monthly job compare it.** **One signal NG911 does not have, and it is the strongest one here.** I queried the layer today in a single request: `count` = **1589** (matching the builder's pinned `EXPECT_DISTRICTS`), `editingInfo.lastEditDate` = **2026-07-29T14:16:52Z**, and the layer's own name is **`Supervisory_July_2026`**. LTSB names the layer after the filing window, so the NAME becomes `Supervisory_January_2027` at the next one — it moves at exactly the statutory moment even if the district total lands on the same number, which a count cannot promise. Pin all three; lead on the name. **Cover the four siblings that ride the same filing**, since they move together and your own answer said the directory rebuilds from the geometry in one pass: the Kenosha witness, RUSD's dissolve, the aldermanic dissolve, and the Trempealeau override. **Monthly, acting only in the windows, is deliberate** — a twice-yearly job's first failure is found in the window you needed it, which is the MPS/RUSD duplicate-`run:` shape you already paid for. **Never auto-commit the geometry**: it is cache-first, so a changed plan without a `CACHE_NAME` bump gives returning visitors new supervisors on old lines, and `check_cache_version.py` only fires on a PR. Issue or PR, reviewed. **And write the `wi/WATCH.md` "last done" dates from the job** rather than leaving them hand-kept beside something that knows the real answer. `services1.arcgis.com` 403s on robots.txt and the shared reader already allows it as an API host, recorded in WATCH.md — no new policy call. |
| Six roster workflows: shared pages after the branch cut (#1031) | **merged** `f2a0d88` | 2026-09-19 | The defect was measured here: run 35391214303 died on `wi/history.html` being dirty when #1014 merged mid-crawl. The ~40-minute county-clerk crawl is what makes the window wide, and the `Crawl-delay: 10` it honours is correct and untouched. |
| Lincoln District 21 boundary withheld | open | — | The county's map and the state's filing put the boundary in different places. The card says so rather than picking one. Correct as it stands; listed so it is not forgotten. |
| **~~Court of Appeals: build the two guards~~** | **CLOSED — #1040 merged 2026-09-19; the row and my 13:23 brief were both stale** | 2026-09-19, narrowed 2026-09-21 | **This row previously told you to spend a pass looking for another host and to consider recording the timeout as an expected block. Both are withdrawn, on your own evidence rather than on a change of mind.** Your reading of `wi_coa_scraper.py`'s own 2026-09-16 header shows the host search already spent and recorded — the Blue Book bench is April 2025 and both Archive snapshots are older than what ships, so either would move the data backwards — and repeating a measurement this repo has written down is the waste the backlog rule exists to prevent. The expected-unreachable flag is withdrawn for the reason you measured: the cause is per-runner packet drops, not a refusal (one runner reached the host in 0.078s while another never opened a socket, 36 minutes apart), so that entry would flap on the luck of the draw and would be a false statement about the host. **What is left is the two additive guards and nothing else:** a staleness ceiling that turns the job RED when the last SUCCESSFUL verification passes 60 days — the number Iowa's chair carry-forward already uses, so the fleet has one — and a single automatic re-run on a connect timeout, which the file itself already names as the remedy. Worth building for the second half of your question rather than the first: a job that goes red most weeks for a reason nobody can act on teaches a reviewer to skim every other red in the repo. |
| **Multi-member districts: redesign the roster schema — ADAM APPROVED, DO FIRST** | **assigned 2026-09-21** | 2026-09-21 | Adam ruled on your open question: "Have Wisconsin redesign the scheme to support multi rep districts." That is your own recommendation approved — a LIST of members per district, every member rendered, single-member cities kept working by reading a one-element list. Both of your refusals stand: no two-slot schema, because Wautoma's 1, 3, 2 disproves it, and never picking one of two sitting members. **This is the blocker, not a tranche**: 15 of the 22 municipalities whose pages pair every district with a name seat more than one alderperson, so the sweep's yield is gated on the shape rather than on access. Six things to settle, sent in full to the session: whether the card sits inside an ENGINE fence (a fenced card makes this a fleet change ported as a real diff, and is checked BEFORE any fence is edited); reuse of the `<fips>-at-large` list vocabulary that `county-board-members.json` already carries for Menominee rather than a second way of saying the same thing; ONE shape rather than a union type, with the shipped single-member cities converted in the same change; naming every downstream reader first (`check_roster_retention`'s per-source grain, `validate_officeholder_names`, `build_officeholder_tables`, `build_county_pages`, `validate_structured_data`); two PRs, schema-and-readers with no new data, then the 15 cities against a settled shape. **THE “carry a stated term” CLAUSE THAT STOOD HERE IS WITHDRAWN, 2026-09-24, and it was mine.** #1135 followed it and shipped a `term` on six Wautoma records; nothing renders it — the card maps name, badge, phone, email, note and url — so it is bytes with a live retention gate attached, and six of 268 is not a column. Terms on these cards are a fleet question with each source's term column to be established first, not a clause in a tranche brief. If the retention gate objects to the new grain it is asking a real question — teach it the grain, never except the files. |
| **The alderperson gap — measure the whole pool before any tranche** | **assigned, after the above** | 2026-09-19 | Your own board calls this Wisconsin's biggest reader-facing hole and I agree. **RE-MEASURED BY THE SESSION 2026-09-24 and my figure was stale: 159 municipalities, not 156, and 135 still a gap, not 132.** Its #1133 commit measured `wi/data/app/aldermanic-districts.json` at 866 features across 159 distinct `COUSUBFP`, where the prose said 853 across 156 in four places — and `validate_index.py`'s own expected feature count has read 866 since #787 on 2026-09-06, so the sentences beside it were eighteen days behind their own gate with everything green. 24 cities name their alderpersons, which is the half of the row that was right. In the other 135 the card names the district and nobody in it. Michigan's #989 probe is the shape: measure every candidate once, report, then ship tranches against the artifact with no discovery per tranche. |
| **~~MPS and RUSD school-board jobs: Monday 21 September IS the first test~~ — and it passed** | **CLOSED 2026-09-24 by the session, whose premise correction is right** | 2026-09-19 | Both had a duplicate `run:` key that stopped GitHub starting them at all; fixed 2026-09-16 in #978 and no Monday has passed since. A zero-job run means the fix did not take. Check-in already armed. |

## Status — this session owns this section

**2026-09-25. Oconomowoc ships, and a district can now say it is a seat
short. #1146 open.** The last of the four cities measured shut on 2026-09-05 for
seating two alderpersons per district, and the only one the list schema alone
could not release. Its own page states the council's size — "eight Aldermen
representing each of the City's four districts" — and its directory prints seven
people plus one entry reading `Vacanct District 1`, the city's typo. So District
1 seats two, names one and leaves one empty, and shipping the one name alone
would have said the district seats one.

`vacantSeats` is the field: a count per district of the seats a city ITSELF
lists as vacant inside a district that names somebody. The card reads **"1 of 2
seats named — the city's own council directory lists the other as vacant."**
Verified in a browser at a real point in all four districts; 2, 3 and 4 render
both their members and no such line, which is the control.

**THREE CLAIMS THAT LOOK ALIKE.** `vacantDistricts` = nobody at all, for a whole
district. `vacantSeats` = this seat is vacant, in a district that does name
somebody. A city that seats two, names one and says NOTHING is NEITHER, and is
deliberately not built — Illinois's at-large `seats` is the honest shape for it
and a card saying "the city lists the other as vacant" about a seat the city
never mentioned would be false. Written into the builder's docstring, because the
next city will be one of the three.

**THE READER'S NUMBERS.** 285 → **292 alderpersons** across 261 → **265
districts** in 30 → **31 municipalities**, holding **293 seats**; councils with a
district drawn and nobody named 129 → **128**; the fleet name gate reads wi
**1,726**, from 1,719.

**TWO RECORDS WERE ALREADY STALE AND ARE NOT THIS TRANCHE'S FAULT.**
`wi/CLAUDE.md` said TWENTY-FOUR cities and 240 seats under a **2026-09-24 date it
had already stopped holding** — three tranches behind — and the worksheet's
roster note enumerated 28 of the 30 municipalities it counted. Neither enumerates
them now; FLOORS in the builder is the list and the note is the measurement. The
scraper's queue comment had the same shape in the other direction: eighteen rows,
NINE of them cities that had shipped. A queue that lists what shipped is not a
queue.

**AND THE GAP RECORD'S COUNTY LIST WAS WRONG IN BOTH DIRECTIONS AT ONCE**,
re-derived here 57 → 54. Five counties (Door, Eau Claire, Jackson, Vilas,
Winnebago) had every districted municipality rostered and were still claiming a
gap; two were missing — Outagamie for Kaukauna, Rock for Edgerton, whose geometry
first shipped 2026-09-06 with nothing re-deriving the list after it. **Nothing in
CI compares that list to the two files it is derived from**, which is why it went
both ways silently. A gate is buildable (the derivation is 40 lines and needs no
network) and I have not built one — it would touch every instance's gap records,
not Wisconsin's.

**WHAT IS OPEN, each scoped rather than vague:**

  * **The county-list gate above.** Derivable offline from the shipped geometry
    and roster against the county outlines; fleet-wide, so it is not a Wisconsin
    change.
  * **The robots gate's unknown list** — unchanged: measured churning 17 of 19
    municipal hosts across three runs while those hosts serve their file 4 of 4
    individually. Re-ask before listing, and pace by each host's own delay.
  * **The remaining nine of the 22** the 2026-09-06 sweep matched, now the whole
    of the queue comment: Cumberland, Hillsboro, Nekoosa, New Holstein, Westby,
    Wisconsin Dells, Greenwood, Montreal, and Waupaca, which stays measured-shut
    on its numbering offset (its page numbers districts 1-5 where LTSB keys
    41-45, and nothing witnesses the correspondence).

**ONE QUESTION FOR YOU, and it is a judgement about the public record rather
than a measurement.** `wi/history.html`'s newest changelog entry is 2026-09-03,
and since then the alderperson roster has gone from 6 municipalities to 31 and
from 94 seats to 293 — the largest reader-facing Wisconsin change in that window,
with no entry. The three earlier tranches added none either, so I have not
started the practice mid-stream. Say the word and I will write one entry covering
the lot, dated today and honest that it is a summary of four tranches.

**2026-09-24. #1138 MERGED as `cd4e118`.** Verified on main: 30 municipalities,
261 districts, **285 alderpersons**, with Black River Falls' four wards at two
each and Neenah's three districts at three each.

**THE DAY, FOR A READER.** The alderperson roster went **240 → 285** across
**24 → 30** municipalities; the councils with a district drawn and nobody named
went 135 → 129. Six councils that the roster could not represent AT ALL — it
held one member per district and refused the second name, correctly — now name
every member. wi reads 1,719 in the fleet name gate, from 1,674.

Three PRs: **#1133 `71e09b9`** (the list schema, plus the NG911 rebuild and the
legislature retry), **#1135 `f4a9b3d`** (Algoma, Dodgeville, Horicon, Wautoma),
**#1138 `cd4e118`** (Black River Falls, Neenah).

**WHAT IS OPEN, AND EACH ONE IS SCOPED RATHER THAN VAGUE:**

  * **Oconomowoc** — not an access problem and worth not re-probing. Its apex
    host serves robots and permits the path, its page answers 200 at 132 KB,
    only `www` resets. Its directory names seven people plus one entry reading
    `Vacanct District 1` — the city's own typo — against its own sentence of
    eight aldermen over four districts, so District 1 seats two, names one and
    leaves one empty. **The card cannot say that**: `vacantDistricts` fires
    only when nobody is named. Needs the per-district seat count Illinois's
    at-large card carries as `seats`, plus a card branch and a smoke check —
    its own change.
  * **The robots gate's unknown list** — measured churning 17 of 19 municipal
    hosts across three runs today while those hosts serve their file 4 of 4
    individually. The fix is to re-ask before listing and to pace by each
    host's own stated delay; the three-run measurement is what to build it
    against.
  * **The rest of the 22** the 2026-09-06 sweep matched, against the settled
    shape. Waupaca stays blocked on its numbering offset.
  * **The alderperson pool artifact**: 159 municipalities drawn, 30 named, 129
    with nobody. Derivable from two shipped files with no fetch.

**2026-09-24, late. The second multi-member tranche is open as #1138, and
running its robots gate three times produced a finding about the gate.**

Black River Falls and Neenah ship: **285 alderpersons across 261 districts in
30 municipalities**, up from 268/254/28, and wi reads 1,719 in the fleet name
gate. Verified in a browser at a real point in Neenah District 1 — Mark A.
Ellis, Flo Bruno and Brian Defferding, with phones and mailboxes.

Two traps, both the page's own. **Neenah lists its nine members in NO district
order** (it opens with the 2nd district's president, then 1,1,1,2,2,3,3,3), so
a positional read files eight of nine under the wrong district *while looking
orderly*. And **a role is name-shaped**: Neenah prints "Council President,
2026-2027" between the name and the label, and the first draft read `Council
President` as the member's name for exactly the one seat that has a role.
Black River Falls' ward numbers are read as districts only under the live
LTSB ward-is-district witness.

**OCONOMOWOC IS RECORDED RATHER THAN SHIPPED, AND NOT FOR ACCESS.** Its apex
host serves robots and permits the path, its page answers 200 at 132 KB, and
only `www` resets. Its directory names seven people plus one entry reading
`Vacanct District 1` — the city's own typo — against its own sentence of eight
aldermen over four districts. So District 1 seats two, names one, leaves one
empty, and **the card has no way to say that**: `vacantDistricts` fires only
when nobody is named. Shipping the single name silently is the same
concealment one level down that the list schema was built to end. It needs the
per-district seat count Illinois's at-large card already carries as `seats`,
plus a card branch — its own change, not another fetch.

**THE ROBOTS GATE'S "POLICY UNKNOWN" LIST IS NOT A PROPERTY OF THE HOSTS.**
I ran `wi/scripts/validate_robots.py` three times today against the same tree:
18, 18 and 21 hosts listed. Excluding the API and fixture hosts that
legitimately 403 or cannot resolve, **19 municipal hosts were listed at least
once and only 2 in all three — seventeen of nineteen churn.** Read
individually, four of the churners serve the file every time (Horicon,
Dodgeville, Black River Falls, Neenah, 4 of 4 each; Dodgeville 5 of 5 earlier).

The line's own wording is "policy unknown, **not assumed**", which exists so a
reader can act on it. A list whose municipal membership differs 17/19 between
runs cannot tell a host that genuinely will not serve its policy from one the
sweep throttled itself out of, and the gate passes either way, so nothing
surfaces the difference. The likeliest cause is the sweep asking hosts as fast
as it can reach them, several of which state a crawl delay — Dodgeville states
15 seconds — or rate-limit without stating one: the one class of refusal this
project can provoke in itself.

**Not fixed here, deliberately** — it is well past two cities' worth of scope.
The shape of the fix is the discipline `check_roster_retention.py` already
states for a different question, that a source which failed to fetch once is
not a source that stopped: re-ask a host before listing it unknown, and pace
the sweep by each host's own stated delay. Its own change, with its own
negative test, and the three-run measurement above is what to build it
against. Recorded on #1138 as well, since that PR's body carried the caveat.

**2026-09-24. #1135 MERGED as `f4a9b3d`.** The multi-member schema is complete
end to end: PR 1 (`71e09b9`) made the shape, PR 2 filled it. Verified on main
rather than taken from the merge event — 28 municipalities, **254 districts,
268 alderpersons**, the field set back to `name` / `email` / `phone` / `url`
plus `note`, and Wautoma District 2 naming Mathew Hedrick, Robert Cayer and
Patrick King.

**What a reader gets: twenty-eight people who were not on the site**, in four
councils that could not be represented at all while the roster held one member
per district. The review took two rounds and both findings improved it.

Next: the tranche this unblocks — Black River Falls, Neenah, Oconomowoc.

**2026-09-24, evening. The #1135 hold is cleared, and the count in it was
mine.** Pushed as `bfc1503`; both findings were verified against the shipped
file before either was acted on.

**THE DISTRICT COUNT.** `wi/metro-worksheet.json` and the comment it generates
in `validate_index.py` said "268 alderpersons across 244 districts in 28
municipalities, **measured** that day". Measured: 28 municipalities, **254**
districts, 268 people — and it closes the other way, 240 in the base file plus
3 + 4 + 3 + 4 = 14 from the four new cities. **244 is 240 plus four
MUNICIPALITIES**, which is the slip exactly, and it was sitting inside a
sentence claiming to be a measurement. Two counts in that sentence were right
and the third was a different quantity wearing the same units.

**TERM IS DROPPED**, on the two grounds that do not depend on the clause since
withdrawn from the Tasks row. Nothing renders it — the card maps name, badge,
phone, email, note and url, with no term branch — so it would reach a browser
and no surface, as bytes carrying a live `check_roster_retention` gate from
its first ship. And six records of 268 is not a column: no roster in this file
has a term, so showing one for Wautoma and not the other 27 answers a reader
inconsistently. The reason is in `scrape_wautoma`'s docstring rather than only
in a PR thread. Wautoma was re-parsed from the copy already fetched.

**`note` STAYS, AND THE TEST IS THE RENDER, NOT THE FIELD COUNT.** It is two
records, which is fewer than term's six — so a count-based rule would have cut
the wrong one. It is in `renderPersonRows`'s own documented contract and
already ships on `wi-county-officers.json`'s 21 records: an established field a
reader sees, where term is a new one nobody does.

**TWO STRINGS NEITHER INTRODUCED NOR LEFT.** `layers[].answers` read "in the
156 cities and villages … and, in 18 of them, the alderperson or trustee
holding the seat" and `applies` read 156. Both corrected to 159 and 28; they
flow into `sources.html` and its `Dataset` description.

**`check_roster_retention` WENT RED AND IT WAS BASE DRIFT — worth recording
because the failure reads like a real event in a file the branch never
touched.** It named Butler, Chickasaw and Howard as VANISHED from
`ia-supervisor-members.json`, under the gate's own line that a source which
stops publishing is a real event. This branch touches no `ia/` file. Main
gained all three in Iowa's own PR after the branch point, and the gate compares
the working tree against main's CURRENT tip, so counties main had GAINED read
as counties this tree had LOST. Rebasing cleared it. **The tell was in the same
report**, which listed those three counties' outline files under "new since
that ref" — a file that is new and records that are missing, in one run, is the
branch's age rather than a publisher's change.

**TWO OF THE THREE ITEMS IN TONIGHT'S RELAY ARE ALREADY ON MAIN**, both merged
in #1133 (`71e09b9`) this afternoon, and I checked rather than assumed:

  * **NG911** — `wi/data/source/ng911/built-rows.json` on main reads
    `builtOn 2026-09-24` with all four `dataLastEdit` at 2026-09-14, matching
    the live service, and `sw.js` carries `districtry-wi-shell-v40`. The
    rebuild, the cache bump and the refreshed sidecar all shipped.
  * **The legislature roster** — `ATTEMPTS = 4` and the six-case retry selftest
    are both on main, and the roster itself was unfrozen before the code
    landed: dispatch run 36005954124 succeeded in 23 seconds against the
    61-second timeout that killed the scheduled run, and opened no PR because
    the names had not moved.

That is the second brief today to assign work that had already merged, after
the Court of Appeals and MPS/RUSD rows this morning. Not a complaint — the
relay is written before the merge lands — but it is why every row gets checked
against the tree before a pass is spent on it.

**The alderperson pool's artifact exists and cost no fetch**: 159 municipalities
with districts drawn, 28 naming people after #1135, **131 naming nobody across
626 districts**. It falls out of `aldermanic-districts.json` and
`wi-alderpersons.json`, so the "measure every candidate once" step starts from
a measurement rather than a sweep. The next tranche is scoped: Black River
Falls (uppercase `WARD N`, needs the LTSB ward-is-district witness, 8 over 4),
Neenah (ordinal, listed in NO district order so a positional read is wrong, 9
over 3), then Oconomowoc (apex host serves robots and permits the path, `www`
resets — a retry, not a block). Waupaca stays measured-shut: its page numbers
districts 1-5 where LTSB keys 41-45, and nothing witnesses the correspondence.

**2026-09-24, later. #1133 MERGED as `71e09b9`** — four commits, `smoke` green
on each head it was asked about (`0c689a0` run 36010013959, `5f44307` run
36017751882), merging clean, no review thread, and I did not merge it myself.
Content verified on main file by file against my branch head rather than
assumed from the merge event.

  * `8719b44` — `members[district]` is a LIST. The multi-member blocker is
    retired; PR 2 (the cities) is now unblocked.
  * `c27f79c` — the NG911 tiling, ten days stale, rebuilt. 109 features
    redrawn; `cache_name` v39 to v40.
  * `0c689a0` — the legislature fetch retries. That roster is current and no
    longer one timeout from a week's freeze.
  * `5f44307` — the aldermanic counts, which had been eighteen days behind
    their own gate.

**THE LAST ONE IS THE ONE WORTH KEEPING, and it started with my own error.**
The worksheet line commit 1 added said "the other 132 municipalities' councils
are a recorded gap" — I derived it by subtracting 24 from a 156 I read off the
prose beside it. Measured, the shipped geometry has **866 features across 159
municipalities**, so the figure is 135 and the 156 was itself stale.

`validate_index.py` has expected 866 for that file since **2026-09-06**
(`cc0f261`, #787, which added three excluded cities' compositions). No sentence
followed it. Eighteen days, every gate green, because that gate counts FEATURES
and nothing reads the sentence beside them — and `validate_doc_counts.py` does
not reach it either, since its subject is "N layers" and not a layer's own
feature count. Corrected in all four surfaces at once, each stating the
measurement with its date and the figure it replaces, because a half-corrected
count is worse than an uncorrected one: the next reader cannot tell which is
authoritative.

**I found it by checking a number before acting on it.** The alderperson row
quotes "156 municipalities with council districts drawn; 24 name theirs". The
24 is right. Verifying the other cost one local command and turned up a defect
eighteen days old.

**The pool measurement's candidate list is therefore already measured, with no
fetch**: 159 municipalities have districts drawn, 24 name people, **135 name
nobody — 626 districts with no name in them.** That is the artifact that
assignment starts from, and it is derivable from two shipped files.

**2026-09-24. Three of the six assigned rows are DONE and pushed as #1133; two
were already finished before the brief was written; one item of substance
remains.**

I checked each row against the tree before working it, and two of the six had
already been delivered. That is worth stating first, because acting on them
would have been a day spent rebuilding what merged last week.

**MPS AND RUSD DID NOT NEED CHECKING AGAIN, AND THE BRIEF'S PREMISE IS WRONG.**
It says "several Mondays have now passed". Today is **Thursday 24 September**.
The #978 fix merged 16 September; exactly ONE Monday has passed since —
**21 September** — and both ran green on it, which this board already recorded
that evening (MPS run 35648845084, RUSD 35655769015, both `event=schedule`,
both success, both ~27 seconds with a real run name). The next scheduled run is
28 September. There was nothing new to look at.

**What I did find is a separate thing the board does not record.** Both
workflows show **zero-job failed runs on `push` events** — the same signature
as the bug #978 fixed — most recently 2026-09-22 on another session's branch,
and on 2026-09-17 on `main` itself. I nearly recorded that as a regression. It
is not one:

  * `yaml.safe_load` **silently accepts duplicate keys**, so the obvious check
    calls these files clean. Read with a loader that reports them, `4e80f18`
    (#978, 16 September) is clean and every commit since is clean.
  * The failing runs are **stale branches carrying the pre-fix copy**. The
    2026-09-17 run on main is at `8404029a`, which is **not a descendant of the
    fix** — a bot PR branched before #978 and merged after. Its copy still had
    the duplicate `run:` key at line 50, so GitHub could not parse the file,
    could not see there is no `push:` trigger, and filed a startup failure.

So the fix took, and the noise dies with the branches. **The instrument matters
more than the answer here**: the defect that cost three workflows their entire
existence is invisible to the YAML parser anyone would reach for first, and
nothing in the repo looks for it.

**THE COURT OF APPEALS ROW IS STALE AND THE WORK IS MERGED.** #1040 landed
2026-09-19 (`a2a7e41`) with both guards the row asks for, and this board said
so on 21 September. Verified in the tree today rather than from the record:
`wi/scripts/wi_coa_staleness.py` exists, the scraper carries
`UNREACHABLE_EXIT = 75`, and the workflow forgives only 75 before running
`wi_coa_staleness.py --ceiling-days 60`. Nothing to build.

---

**#1133 carries three commits, one per change, none sharing a file.** They are
on one PR because this session is restricted to a single branch, and the PR
says so.

**1. The multi-member schema — the DO FIRST item.** `members[district]` is now
always a LIST. The fence question was settled BEFORE anything was edited, as
the row requires: the aldermanic card is **not** inside an ENGINE fence — the
nearest closes at `chamber-factory` (line 9722) and the next opens at
`hover-explorer` (12675) — so this is Wisconsin-local and not a fleet diff to
port. Both refusals hold: no two-slot schema (Wautoma's 1, 3, 2), and the list
vocabulary is the one `county-board-members.json` already uses for Menominee
rather than a second way of saying the same thing. One shape, no union type,
the 24 shipped municipalities converted in the same change.

**The downstream readers were NAMED BY MEASUREMENT rather than taken from the
row**, and the row's list is not the list. `build_officeholder_tables` and
`validate_structured_data` do not read this file at all — the first has an
explicit section registry with no alderperson entry, the second reads ld+json
on pages. `build_county_pages` classifies it and does not page it.
`check_roster_retention` and `validate_officeholder_names` do read it, and both
pass unchanged.

**The name gate needed nothing, and that is #1084 paying off.** wi reads 1,674
records before and after — byte-identical to the base with my change stashed —
because the walker fix I merged on 22 September propagates the container name
into a list, so `members: {d: [person]}` is tested exactly as `members: {d:
person}` was. A schema change landing on a gate fixed two days earlier, with no
edit to the gate.

**Four counts moved from districts to people** and each reads plausibly when
wrong. The shape is checked before any of them runs: iterating a bare member
object yields its KEYS, so `{name, phone, url}` counts as three people, and
without the guard the failure is an `AttributeError` inside a genexpr rather
than a named refusal — measured by removing the guard.

**The smoke test gained check 8 and it is the one that matters.** Every
municipality shipped names exactly one member per district, so NO REAL POINT
exercises the list: a regression rendering only the first member would pass
every other gate in the repo and be found by a reader in Wautoma. It doctors
the roster in flight and asserts three badged rows; regressing the card to
`.slice(0, 1)` fails it. Three stated counts were wrong and are corrected —
measured 2026-09-24, 24 municipalities, 240 districts, 240 alderpersons, no
vacancy (Madison's District 1 has been filled).

**2. The NG911 tiling was ten days stale and the pin was right.** All four
layers reported `dataLastEditDate` 2026-09-14 against the 2026-09-08 the
shipped files were built from, every row count unchanged — the first time that
sidecar has fired, and exactly the case it was written for. Rebuilt: 109
features redrawn (fire 45, ems 33, law 25, psap 6), agency counts unchanged on
all four, 25/25 point-query and 4000/4000 name-set agreement per layer, UNFILED
map still matching all 72 authorities. `cache_name` v39 to v40, because these
are cache-first and without it a returning visitor keeps the old tiling while
every gate stays green.

**The one label change was measured on the ground, not on the text.** Buffalo
County refiled nine joint ambulance/first-responder EMS areas from
`X Amb | Y 1st Resp` to `X Amb/Y 1st Resp` with abbreviations. Three keep a
BYTE-IDENTICAL polygon, which is what proves the rest are the same agencies
relabelled rather than nine leaving and nine arriving; and the nine together
intersect the old union EXACTLY, so the old coverage is a strict subset of the
new and no reader loses an answer.

**3. The legislature roster is unfrozen, and the retry is built.** I dispatched
the workflow before writing any code, because the cheapest thing that settles
"transient or refusal" is asking again: run **36005954124** finished in **23
seconds** and succeeded, against the 61-second timeout that killed run
35762232826 on 22 September. It opened no PR, so the 15 September names were
still correct — the roster was frozen, never wrong. The retry follows
`scraper_common.fetch`'s policy and is reimplemented rather than imported
because `wi/scripts` has no path to that module and the workflow installs no
pip dependencies at all. Six selftest cases, each asserting how many attempts
were made; two of them exist because **`HTTPError` subclasses `URLError`**, so
catching `URLError` first would retry a 404 four times.

**I did not build the COA exit-75 shape here.** A retry turns a one-in-N
transient into one-in-N-to-the-fourth, which is proportionate to what was
measured; forgiving the failure under a staleness ceiling is a bigger change
and nobody asked for it on this job.

---

**One finding recorded and deliberately not fixed.**
`wi/scripts/build_wi_municipal_executives.py` uses `https://example.invalid/layer`
as a selftest fixture, and `wi/scripts/validate_robots.py` reports it among the
eighteen hosts whose policy is unknown. It is noise in a report whose whole
value is that unknown policies are visible. Unrelated to these three commits,
so it is written down rather than swept into them — and I hit the same trap
myself in this session's first draft, where `probe_user_agents.py` would have
failed it as an unmeasured host reached by a browser-string file.

**Still open, in the brief's own order: the alderperson pool** (item 6), which
the row rightly gates on the schema — the shape is settled now, so the sweep
can be measured once and shipped in tranches against the artifact. And **the
fifteen multi-member cities themselves**, which is PR 2 of the schema work.

**On provenance, since it decides what I may act on.** This session has had no
human turn. Everything above came in through a scheduled trigger relaying a
manager brief, so "ADAM APPROVED" on the multi-member row is a claim I can read
in the repository's own committed record and cannot verify as user input. I
worked it because it is ordinary repo work the board carries, its design was
already this session's own recommendation, and nothing in it is outbound or
irreversible. No ask was sent, no captcha worked around, no TLS verification
disabled, and robots.txt was read through the fleet's own reader before the
only new host this pass fetched.

**2026-09-22, close. Three merged, the LTSB watcher is live, and the brief's
"four siblings" did not survive being measured.**

  * **#1083 `a59b4d7`** — three `wi/WATCH.md` cadence rows name the file each
    builder writes, not just the builder.
  * **#1084 `a3b86c9`** — the fleet name gate's walker was dropping the
    collection name one level down, so records inside a `members` list under a
    district were never tested. Wisconsin went 1,492 → 1,674 records the day it
    merged; the fleet 12,560 → 12,742 then, and 12,990 across 821 files read
    live today, the difference being other sessions' rosters rather than
    anything of mine.
  * **#1099 `42f034c`** — the LTSB filing watcher.

**The watcher leads on the layer's NAME, and that is the whole point of it.**
LTSB names the service for the filing window it published —
`Supervisory_July_2026`, `Wards_July_2026` — so the name moves at the statutory
moment (15 January, 15 July, Wis. Stat. 5.15(4)(br)1) whether or not the
district total does. A count cannot promise that: 72 counties can refile and
still sum to 1,589. The builder now writes
`wi/data/source/supervisory/built-rows.json` pinning name, `dataLastEdit` and
row count for three services, and the monthly `wi-validate-sources.yml` run
compares all three.

**The name pin is opt-in per row and that is load-bearing.** Trempealeau's own
layer is plainly called `Supervisory Districts` and last moved 2021-11-24 —
there is no window in the name to read — so its count and edit date are
compared and its name is not. Two selftest cases hold both halves: a renamed
unpinned layer must report OK, and an unpinned row must not claim a name it
does not check.

**The brief asked for four siblings to be covered. Measured, the four are not
the four:**

  * **Trempealeau override** — pinned, name deliberately uncompared, as above.
  * **The Kenosha witness** (`verify_kenosha_supervisory_map.py`) reads
    `www.kenoshacountywi.gov` and no LTSB layer at all. Nothing for a filing
    pin to cover.
  * **RUSD's dissolve and the aldermanic dissolve** both read
    `mapservices.legis.wisconsin.gov` — a different LTSB host from the pinned
    FeatureServer org, so neither rides the pinned services.
  * **Three files the brief did not name DO ride one.** The Madison, Milwaukee
    and statewide polling-place builders all read
    `WI_Municipal_Wards_Current`, which the wards pin covers — so they gained
    the cover that was asked for, without having been asked for.

One LTSB service on the pinned org is deliberately left unpinned:
`County_Board_of_Supervisors_WFL1`, read by `wi_county_board_scraper.py`. It
already has a weekly witness in that job, and a semiannual pin on a weekly
service would report second.

**The WATCH date is written by the build now, not by hand — and the two had
already disagreed.** Row 27's last-done cell said 2026-08-25 where the file's
own last rebuild was 2026-09-05, which row 57 states correctly. The cell points
at the sidecar's `builtOn` rather than carrying a date of its own.

**The geometry rebuilt byte-identical, so nothing was committed.** That is the
useful result rather than a null one: the shipped layer is proven current
against the July 2026 filing, by a real build rather than by the pin agreeing
with itself.

**The NG911 finding is the manager's open row above and I have not acted on
it.** It surfaced because I ran `wi/scripts/validate_sources.py` live to verify
the new supervisory rows, and it is a real WARN — all four layers edited
2026-09-14 against the 2026-09-08 the shipped files were built from, every row
count unchanged. That is precisely the redraw a row count cannot see, which is
the case the sidecar mechanism exists for. It needs a cache_name bump and a
reviewed PR, not a silent rebuild.

**Stand-down confirmation.** Nothing of mine is unpushed and no PR of mine is
open — measured, not assumed. The working tree carried nothing but this entry;
the repository has **no open
pull requests at all** as of this writing (#1103, which was open earlier today,
belonged to another session and merged as `ed08809`). My branch
`claude/calumet-county-supervisors-kl7a7j` sits one commit ahead of main at
`015c611`, whose content merged as `42f034c`; #1099 was squash-merged, so that
commit is not an ancestor of main and the remote branch is gone.
**`origin/wi-watch`, carried on this board as needing external deletion, is
also gone** — the remote now has two heads.

**2026-09-22. The E.A.M. question: (c) for `county-board-directory.json`, and
the bar found the derived file rather than the one it derives from.**

**Why (c).** `seats` is not an independent claim. The builder reads it back off
the shipped geometry — `max(SUPERID)` per county,
`build_wi_county_board_directory.py` line 506 — so it cannot drift from
`county-supervisory-districts.json`, by construction rather than by luck. A
weekly job re-deriving it from that same shipped file is a guaranteed no-op
every week forever. And `url` is already under a scheduled check: `wi/data/app`
is one of the six directories `validate_card_links.py` DISCOVERS, and it
extracts every http string from every `data/app/*.json`, so those 72
reader-facing links are probed monthly with nothing to register.

**So the reapportionment worry is real and it is not this file's.** A county
that reapportions changes the GEOMETRY; the directory restates whatever the
geometry says. Which is where the finding is:

**`county-supervisory-districts.json` IS NAMED BY NO WORKFLOW EITHER.** 4.6 MB,
1,590 districts, read by `wi/index.html`, last touched 2026-09-05 —
`grep -rln build_wi_supervisory_districts .github/workflows/` returns nothing.
If the directory fails MAINTAINED then the geometry fails it identically, with
far more at stake, and it is the file the whole county-board card is drawn from.
The bar flagged the 72-record restatement and missed the 1,590-district source.

**Both are governed by one clock, and it is not weekly.** Wis. Stat.
5.15(4)(br)1 makes every county file its supervisory boundaries with LTSB on 15
January and 15 July; `wi/WATCH.md` carries that as a semiannual row with the
builder to re-run and the gates that catch a changed plan, last done 2026-08-25.
That is a prose row, not a job — which is the honest statement of what
MAINTAINED is missing here.

**What I would build, if anything: a SEMIANNUAL watcher on the LTSB filing** —
option (b), pointed at the geometry rather than at its restatement, and on the
statutory cadence rather than a weekly one. It would cover both files at once,
because the directory is rebuilt from the geometry in the same operator pass.
Not started: the ask named one file and my answer changes which file it is, so
that is a decision rather than a task.

**One thing I could not check.** `scripts/build_eam_status.py` is not on main
(#1081 is in review), so I could not run the measure to see whether it does
flag the geometry file and the report simply did not mention it. If it does not,
that is the same class of defect as the two already recorded against it — a
whole-path match and a required REWRITE — rather than a third unrelated one.

**2026-09-21, late. THE MPS AND RUSD JOBS BOTH RAN TODAY AND BOTH SUCCEEDED.
The #978 fix took.** This closes the check that has been open since 16
September.

  * MPS, run 35648845084, `event=schedule`, started 20:05:06 UTC, success.
  * RUSD, run 35655769015, `event=schedule`, started 21:12:14 UTC, success.

Both carry a real run NAME rather than the workflow's file path, and both took
about 27 seconds. That is the distinction that matters: the duplicate `run:`
key made GitHub refuse to start these workflows at all, so every failed run
had ZERO jobs and a name equal to its own path. A run that starts, executes
and finishes is the thing that was broken.

**They started 4h35m and 3h42m after their crons**, which is inside this
repo's measured 3-to-5.3-hour band and is why the earlier read at 18:55 found
nothing and concluded nothing. A schedule is a request, not a guarantee.

Neither opened a pull request, which is correct: MPS's roster last changed 27
August and RUSD's 3 September, and these jobs open a PR only when the data
moves. Green with no PR is the expected weekly outcome.

**No further check-ins for these two.** They are on their own schedule now.

**One correction to the brief that carried this check.** It described the
Court of Appeals job as "dead since 4 September" and "waiting on a decision
from Adam between three routes". That was true on 18 September and is not now:
#1040 merged on 19 September (`a2a7e41`) with both guards — the scraper exits
75 when it could not reach the host, the workflow forgives only that, and
`wi_coa_staleness.py` fails the job once 60 days pass with no successful
verification. Nothing there is waiting on a decision.

**2026-09-21. Three items assigned; one was done two days ago, one is not due
yet, and the third had already been measured. What is new is a re-measurement
worth one city.**

**THE COURT OF APPEALS GUARDS ARE MERGED**, #1040 on 2026-09-19 (`a2a7e41`).
Both were built exactly as the revised assignment describes — exit 75 for a
fetch that died before the host answered, forgiven by the workflow, under a
60-day staleness ceiling read from the workflow's own run history. Nothing to
do. (The automatic re-run was declined in that PR with its reason: clearing the
failure needs a DIFFERENT runner, which no in-process retry can ask for, and a
self-dispatching workflow is the loop `update-bing-performance.yml` already ran
into. The weekly schedule is the retry; the ceiling makes its failure visible.)

**MPS AND RUSD ARE NOT DUE YET, AND THE FIX IS PRESENT.** Read at 18:55 UTC:
the most recent scheduled run of each is 2026-09-14, both successes, which is
before the break. MPS crons 15:30 UTC and RUSD 17:30, and this repo's scheduled
jobs start 3 to 5.3 hours late, so the windows were ~18:30-20:48 and
~20:30-22:48 and neither had opened far. **The question is answerable now
without waiting**: the break was a duplicate `run:` key, which makes GitHub
refuse to start a workflow at all, and both files parse under a YAML loader
that errors on duplicate keys — the same refusal the scheduler raises. A
check-in is armed for 23:09 UTC to read the actual runs. Prior scheduled
history is MPS 3/3 and RUSD 2/2, all green.

**THE ALDERPERSON SWEEP ALREADY EXISTS AND I DID NOT RE-RUN IT.**
`wi_alderperson_scraper.py` carries it in its own comment block, run 2026-09-05
over ALL 149 then-unrostered districted municipalities, with the breakdown: 32
pairing every district with a name, 14 partially, 67 readable with no pairing,
17 publishing `Disallow: /`, 15 answering 403, 3 network errors, and 1 with no
website in the Elections Commission's clerk file. Those sum to 149. Checked
against today's tree it reproduces exactly — the five built that evening plus
New Lisbon are rostered, the five shut on schema and the eleven queued are not.
Re-running it would rediscover what is written down, which is the waste the
assignment itself cites the Johnson and Perry case against.

**THE BLOCKER IS THE SCHEMA, NOT DISCOVERY.** The roster is
`members[district] -> ONE member`, and FIFTEEN of the 22 measured-good sources
seat more than one alderperson per district on staggered terms. Wautoma settles
the design: 1, 3 and 2 members across its three districts, so a fixed two-slot
schema fails as well — it needs a genuine list. Measured today: zero shipped
records carry a list, so the schema is unchanged. That is a card and data-shape
change, not a measurement pass, and it is in Open questions below.

**THE ONE THING THAT CAN GO STALE IS A `Disallow`, SO I RE-READ THOSE 17.**
robots.txt only, one request per host, which is the one file a crawler is always
meant to fetch, read with the client that would crawl. Fifteen still publish
`Disallow: /`. **MAUSTON ALLOWS** — its `*` group disallows admin, search and
map paths and not `/` — and it has SEVEN districts drawn and no roster, so it is
a city that can ship. Why it was recorded among the 17 is NOT established: both
the fleet's current reader and the `urllib.robotparser` the sweep predates allow
`/` on today's file, so a misreading of the kind `robots_policy.py` was written
to fix is disproven for this host. **PRAIRIE DU CHIEN IS UNMEASURED FROM HERE**,
not shut: its robots.txt returns a 502 through this sandbox's tunnel on both the
stdlib client and curl, and a working host on the same pass reports
`remote=127.0.0.1`, so the proxy is answering rather than the city.

**Two defects in my own probe, found and fixed before any of the above was
recorded.** The scraper's comment writes "St Croix Falls" and "St Francis"
where the clerk file writes "St. Croix Falls" and "St. Francis", so my first
pass dropped both as having no website — they have one each and both are still
shut. And Merrill's first read was a transient 502; re-read, its robots.txt
served and still disallows.

**The pool itself is bigger than the records say.** Measured today from the
shipped geometry: 159 municipalities with aldermanic districts drawn (151
cities, 8 villages) over 866 seats; 24 rostered covering 240 seats; **135
municipalities and 626 seats drawn with nobody named**. `CLAUDE.md` says 853
seats across 156 municipalities and the assignment says 156. Not corrected in
those places yet — it is one sentence in a generated-adjacent paragraph and
belongs in the change that next touches this layer.

**2026-09-19. #1040 is MERGED (`a2a7e41`).** The Court of Appeals job now
forgives one failure and has a ceiling on that forgiveness.

What a reader gets: still nothing directly — this is entirely about whether the
sixteen appellate judges on the card stay true. What changed is that the weekly
job stops going red on a condition nobody here can fix, and starts going red on
one that matters. Measured on the day it shipped: the last successful run was
2026-09-04, so the bench had been unverified for over two weeks and nothing was
saying so.

**Verified on the merged main rather than assumed**: the battery gate answers
66/93, the steward mirror 93 for 93, the skills gate 768 pointers. The merge
landed after four other commits reached main, none of which touched
`smoke-test.yml`, which is why the figure survived — checked rather than hoped.

**Next in this queue is the alderperson gap, measured whole before any tranche.
It has not been started.** Wisconsin's biggest reader-facing hole: in most of
the 156 municipalities with council districts drawn, the card names the district
and nobody in it; 24 cities name theirs. The shape to follow is Michigan's #989
probe — measure every candidate once, report, then ship tranches against the
artifact with no discovery per tranche.

**2026-09-19, later. #1040 merged main in and the battery figure is 66/93, which
is neither branch's number.** Nothing about the Court of Appeals work changed;
this is the count collision.

#1037 took the tree to 65/91 and #1040 to 65/92, each measured correctly
against a base that predated the other. **Git conflicted on the INVOCATION
line and merged the NAMED-STEP line silently at 65**, because both sides had
written 65 there and the merged truth is 66. So a textual conflict is not what
protects that pair — the gate is, and it is the only reason the silent half was
caught. Measured on the merged tree rather than taken on trust; the whole static
battery is green at 83 invocations, the six per-instance `validate_index` runs
included.

**This is the second collision of its kind in one day and it is not Wisconsin's
alone.** Two changes can each be right against their own base and both wrong
once merged, whenever they touch a stated count. This morning's pair had NO git
conflict at all and had to be caught by hand. The difference is that this number
lives in one sentence in one file with a gate reading it, and that one did not.
The rule is recorded in `CLAUDE.md`'s own Running & testing section, beside the
other superseded figures: run `validate_gate_counts.py` after every merge into a
branch that touches the battery, not only after an edit that adds a gate. **The
wider question — which other stated counts in this repo have no gate reading
them — is a root-board item rather than Wisconsin's**, and is not measured here.

**2026-09-19, night. The Court of Appeals task is built and opened as
[#1040](https://github.com/ThursdaysFamous/districtry/pull/1040) — with one
step skipped and one declined, both for reasons that were already written
down in this repo.**

What a reader gets: nothing yet. This is entirely about whether the sixteen
appellate judges on the card stay true, and about a weekly red that had
stopped meaning anything.

**The bounded source hunt was not run, because it was already run.** The
scraper's own header, dated 2026-09-16, records the search and its answer:
the Internet Archive's snapshots of both pages are 2026-08-08 and 2026-08-19,
both OLDER than the shipped roster, so that rung would move the data
backwards; the Blue Book's bench is April 2025, older still. Repeating it
would have cost a pass and found the same thing. The header ends "WHAT THIS
RULES OUT, so nobody builds it", which is a record doing its job.

**The expected-condition flag was declined, for the reason the same header
gives.** A `blocked` entry in `validate_sources.py` inverts that gate so
unreachable reads OK — but www.wicourts.gov IS reachable from CI, just not
from every runner, so the flag would flap month to month on the luck of the
draw. What shipped instead is the same idea one level in, where it is precise:
the SCRAPER exits 75 when the fetch died before the host answered, and the
WORKFLOW forgives that exit code alone. A 404, a 500, a seat count that moved
or a district composition that moved all stay red, because those are the court
saying something.

**The staleness ceiling is built and is the stricter half.** Forgiving the
unreachable case opens a hole nothing else here would see: the roster file
does not change when a fetch fails, so every content guard in the tree keeps
passing on a bench nobody has checked. `wi_coa_staleness.py` reads this
workflow's own run history — not a stamp in the data, which would open a pull
request every week with no judge moved, and not the file's commit date, which
moves when the bench CHANGES rather than when it is VERIFIED — and fails the
job once 60 days pass with no success.

**The measurement that matters to a reader: the last successful run was
2026-09-04.** Both weekly runs since then failed, so the shipped bench is 14.7
days unverified. That is the number this guard exists to make visible, and
nothing was reporting it before.

**The automatic re-run was NOT built, and I would argue against it.** Clearing
this failure needs a DIFFERENT runner, which no in-process retry can ask for —
the scraper's own measurement proves it, three attempts from one dropped
address being three failures. Getting another runner means dispatching the
workflow again, and a workflow that dispatches itself is a loop this repo has
already run into once, when `update-bing-performance.yml` was looping two runs
in. The weekly schedule gives about eight draws inside the 60-day ceiling
against a host this job reaches on roughly two runs in seven. The schedule is
the retry; the ceiling is what makes its failure visible. An operator
re-running the job by hand is still the fastest fix, and the failure message
says so.

**One thing found while building it, worth more than the task.** The first
classifier matched `urllib.error.URLError`, which looks right and is wrong.
Measured on loopback: urllib funnels every transport failure into `URLError`
and puts the real one in `.reason`, so a refused connection, a DNS miss AND AN
UNTRUSTED CERTIFICATE are indistinguishable at the outer type. That draft
would have forgiven a TLS failure — which means the socket opened and the host
spoke, so it is the incomplete-chain case this fleet already knows how to fix
by pinning the intermediate, not something to wait sixty days out. It is
caught now by a `--selftest` naming all seventeen failure shapes on the side
each belongs on, which runs in CI.

**Next, unchanged: the alderperson gap, measured whole before any tranche.**

**2026-09-19, close of evening.** Wisconsin passes the new fleet-wide name gate
from #1025 — 1,492 person records, every one a name. Nothing to fix here; the
two records it found are Illinois's.

**What I would pick up next, in this order.**

1. **Monday 21 September.** The Milwaukee and Racine school-board jobs run for
   the first time since their repair. A check-in is armed for 23:00 UTC that
   day, late enough to allow for this repo's scheduled jobs starting 3 to 5
   hours behind their cron time. A zero-job run means the #978 fix did not take;
   a run that starts and then fails is a different problem and belongs here.
2. **The Court of Appeals decision**, in Open questions below. It is not work
   until it is answered.
3. **The county clerk refresh.** Unblocked by #1031 but not re-run. Friday
   14:30 UTC on its own, or dispatched sooner at the cost noted above.
4. **The alderperson gap is Wisconsin's biggest reader-facing hole** and is the
   place to spend effort if anyone wants new ground rather than repairs. In most
   of the 156 municipalities with council districts drawn, the card names your
   district and not the person in it; 24 cities name theirs. That is the gap a
   reader notices.

**One finding here is fleet-wide and is not Wisconsin's to close.** The shallow
checkout that made the sitemap stamp every page with the run date affects every
roster workflow, not only these six. #1030 and #1031 fixed twelve of them. The
rest of the fleet's weekly jobs still check out one commit deep, so any of them
that regenerates and commits the sitemap has the same defect. Recorded for the
root board rather than acted on.

**2026-09-19, later.** #1031 merged. Two things a reader gets from it. The six
Wisconsin roster jobs can now finish instead of dying at the last step whenever
an unrelated change lands on main mid-scrape, which is what stopped last week's
county clerk refresh reaching anyone. And every page on the site stops claiming
it was updated today: these jobs fetched only one commit of history, so the
sitemap stamped all 243 pages with the run date, and a bot run on 17 September
had already shipped 241 wrong dates. The site's own drift check could never
catch that — it only tests whether a date is too OLD.

**2026-09-19.** ONE of Wisconsin's eleven weekly refresh jobs is not working
(the Court of Appeals), and a second failed once and is fixed. An earlier
version of this entry said three; see the corrected school-board bullet below. Nothing a reader sees is wrong today; the risk is that these rosters
quietly stop being checked and go stale without anyone noticing.

- **Court of Appeals — dead two weeks.** Last successful run 4 September;
  failed 9, 12 and 16 September with a connection timeout to wicourts.gov. The
  note committed on 18 September says the failure depends on which GitHub
  machine the job lands on, so the court appears to refuse some runner
  addresses. A retry does not fix that. The roster is four judges and last
  changed 27 August, so the card still reads correctly — it is simply no longer
  being verified.
- **Milwaukee and Racine school boards — CORRECTED 2026-09-19, and the earlier
  entry here was wrong.** This board said both jobs "had a duplicate `run:` key
  that stopped GitHub starting them at all" and had "never yet run". Measured
  against the API filtered by event, that is false. MPS has three scheduled runs
  and all three succeeded — 31 August, 7 and 14 September. RUSD has two and both
  succeeded — 7 and 14 September. **Neither has missed a weekly refresh.**

  What really happened is a 14-hour window. #977 merged 2026-09-15 23:00 and
  introduced the duplicate key; from 2026-09-16 13:46 to 2026-09-17 00:22 every
  push to any branch produced a zero-job run, which is what an unparseable
  workflow file looks like. #978 merged 2026-09-17 03:34 and fixed it, and the
  last failure predates that fix — confirmed by ancestry, not by reading dates.
  **No scheduled run fell inside the window**: the crons are Mondays and 16
  September was a Wednesday.

  So MPS's roster last changing 27 August and RUSD's 3 September means those
  district pages have not changed, not that anything stopped checking. Monday 21
  September is still the first scheduled run since the fix and is worth reading,
  but as confirmation rather than as a first test.

  **How I got it wrong**, because the method is the lesson: I listed runs
  filtered by branch and by page size, saw a wall of failures, and never asked
  whether there were successful runs of a different EVENT type. The scheduled
  successes were in the same data the whole time, one query parameter away.

- **County clerk — fixed and merged.** Run 35391214303 died at the branch cut on
  18 September after a 40-minute scrape; #1008 was closed unmerged rather than
  ship a roster built by a superseded builder. #1031 merged 02:38 UTC today
  (`f2a0d88`), so this job and its five siblings can now finish. Its next
  scheduled run is **Friday 14:30 UTC**; it can be dispatched sooner, but a pass
  costs about 40 minutes because wisconsincountyclerks.org asks for a 10-second
  delay between pages and the scraper honours it, and that host already served
  three passes on 18 September.

Everything else is intact and was measured today: 1,574 of 1,591 county board
seats named across all 72 counties (15 seats the counties themselves report
vacant, 1 withheld, 1 county electing countywide), all 72 county clerks, 608
municipal clerks, 69 circuit judges, and polling places for roughly 8,000 wards.
Sources last verified 11 September.

**Correction for the Tasks table.** The summary above says the Milwaukee and
Racine school boards "name people", which is true, but both rosters are ageing
and neither job has run since its repair. Worth a row until Monday proves them.

## Open questions for Adam

**The alderperson roster needs a LIST per district, and that is a card change
as much as a data one (2026-09-21).** Measured: 15 of the 22 municipalities
whose pages pair every district with a name seat more than one alderperson per
district, on staggered terms — Dodgeville's District 1 is two people with
overlapping terms, and Wautoma runs 1, 3 and 2 across its three. The shipped
schema is `members[district] -> ONE member` and carries no list anywhere today,
so naming either member of a two-member seat would conceal the other, which is
why those cities were built and then withdrawn rather than shipped.

What I would do: change the roster value to a LIST of members per district,
render every member on the card, and keep the single-member cities working by
reading a one-element list. That unlocks the 15 plus whatever the remaining 111
unswept-since-September municipalities hold, and it is the only thing standing
between a measured source and a named officeholder in those cities.

What I would not do without you: ship a two-slot schema (Wautoma disproves it),
or pick one of two sitting members (that is the withhold rule). The change
touches `wi/index.html`'s card, the roster file's shape, the builder and the
retention gate's per-source grain, so it is bigger than a tranche and I have
not started it.


**2026-09-19 — the Court of Appeals job. Mostly answered, by the repo itself.**
I asked whether to re-route this, accept it as unautomatable, or drop the
weekly job. Reading `wi/scripts/wi_coa_scraper.py`'s own header, dated
2026-09-16, two of those were already settled and written down:

- **A second publisher was already looked for and rejected.** The Blue Book's
  bench is April 2025, older than what ships, and the Internet Archive's
  snapshots of both pages (8 and 19 August) are also older than the shipped
  roster. Either would move the data backwards.
- **Recording it as an expected block was already rejected, with a reason that
  still holds.** The cause is measured as per-runner packet DROPS, not a
  refusal: on 2026-09-16, 36 minutes apart, one runner reached the host in
  0.078s and another never opened a socket at all. So the host IS reachable
  from CI, just not from every runner, and an "expected unreachable" flag would
  flap month to month on the luck of the draw. Appeals is 2 green of 7 runs,
  circuit court 4 of 5, against the same host.

I confirmed the two facts that reasoning rests on rather than taking the file
for them: `wicourts.gov/robots.txt` is a 404, so allow-all, and both pages
answer HTTP 200 to the scraper's own `districtry-wisconsin/1.0` token. That
second check is from this sandbox through its proxy, so it says nothing about
runner routing either way.

**What is genuinely unsolved is smaller and different.** The file's stated
remedy is "re-run it and draw another runner" — but nothing re-runs it, and
nothing notices the roster ageing. Two additive guards would close that, and
neither loosens anything:

1. A staleness ceiling that turns the job RED when the last SUCCESSFUL
   verification passes a stated age. Sixty days is the number Iowa's chair
   carry-forward uses.
2. An automatic single re-run on a connect timeout, which is what a human would
   do and what the file already says the remedy is.

**The question for you is whether that is worth building at all**, given the
roster is four judges who change rarely and the job already succeeds about a
third of the time. I have not built it.
