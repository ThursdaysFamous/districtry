# Michigan board

Owner session: **Michigan**. Manager owns *Tasks*; this session owns *Status*
and *Open questions*. Rules and reporting posture: `BOARD.md` at the repo root.
Commit board edits straight to main, in their own commit, dated.

## What a reader gets today

Click any point in Michigan and the app answers from **15 layers** — the fewest
in the fleet, because Michigan is the newest instance (live 2026-09-03). The
state House and Senate rosters are complete at 110 and 38. **48 of the 83
counties name your commissioner** — 366 of the 619 seats, 61.4% of the state by
population.

**20 recorded gaps** — 13 no-source, 5 blocked, 2 data-quality. Eighteen of the
twenty are city council wards.

## Tasks — manager owns this section

| task | state | opened | notes |
|---|---|---|---|
| **Commissioner roster covers 26 of 83 counties** | **assigned — tranche 6** | — | The headline gap and the layer the instance was built around. Tranche 5 merged `3fb9820`: 229 of 619 seats, 55.1% of the state by population. The 22 remaining probe candidates need no new discovery and their pages are already saved, so tranche 6 costs no fetch. |
| Detroit PR-body proposal | open, below tranche work | — | The weekly Detroit PR body is one static paragraph, identical every week whatever changed, so it cannot tell a reviewer that a run moved a snapshot stamp rather than a person's name. Real, unwritten anywhere in the repo, and worth less than the roster — Michigan's own measurement. |
| City council wards — 18 of the 20 gaps | open | — | Ann Arbor and Jackson blocked; Bay City data-quality; Dearborn, Detroit, Flint, Holland, Kentwood no-source. **Run the state's WARD column first** (`mi/WATCH.md` line 30) — one query settled 23 cities on 2026-09-06. `WARD='00'` means stop. |
| Michigan's full bbox vs. the clipped one | open | 2026-09-04 | The county fabric is water-inclusive and runs west across Lake Michigan to -90.42, containing Chicago's and Wisconsin's centres. Shipped clipped to `lng >= -87.60`. Four western-UP places still misroute at the front door. Recorded in `mi/WATCH.md`; no fix proposed. |

**Wyoming (MI) is off limits.** Its own robots.txt names ClaudeBot and disallows
the whole site. Do not fetch it with a browser user-agent.

## Status — this session owns this section

**2026-09-19, the probe's robots gap merged.** #1045 is in as `1619003e`, verified on the
merged tree rather than on my own PR body: `probe_mi_county_boards.py --check` passes there,
the CI step sits at `smoke-test.yml` line 81, and `validate_gate_counts.py` and
`validate_steward_mirror.py` both agree at 67 named static steps and 94 invocations.

**New York's statewide go-live merged between my branch point and this one** (#1042,
`3416c6b5`) and moved none of the battery — it touches neither `smoke-test.yml` nor
`CLAUDE.md` nor the steward skill — so the pair above is the merged tree's own figure and not
one carried across a merge unchecked. That is the case `CLAUDE.md` warns about, where two
branches are each right against their own base and the silently-merged half is the dangerous
one; it was checked rather than assumed.

Michigan has no tranche work left that needs neither a fetch budget nor an operator answer.
The candidate list is empty, the 23 remaining shut counties wait on the request budget asked
for below, and the ward front waits on the state-fabric-as-source question. The next item
needing neither is the Detroit PR-body task on the Tasks table.

**2026-09-19, the probe's robots gap closed.** #1045 open. Every county row in
`mi-county-board-probe.json` now carries the robots reading for the host the probe ACCEPTED,
not only for the ones it rejected, and `--check` fails a record that names a URL without one.
The reading keeps the verdict's own `why` — "robots.txt served (N bytes): <the deciding
rule>" — because a status alone cannot settle a disagreement: both of the contradictory
Gogebic readings would have said `served`. Host and board page are recorded separately, since
one file can allow `/` and disallow the path a board page sits under.

Backfilling the 25 recorded counties cost 33 readings and 24 fetches — robots.txt only, no
page, no verdict touched — and found two counties whose recorded reason is no longer the one
that governs. `www.iosco.org` now answers HTTP 403 on robots.txt, which the strict reading a
county website gets makes a refusal; read three times on both spellings, identical each time,
carrying `server: cloudflare` and the site's own `cf-ray`, so it is the host and not this
sandbox's proxy, which answered 200 to the CONNECT. `tuscolacounty.com` serves a 26-byte
robots.txt that disallows this client, where its recorded `challenge` came from its other
host. So **two of the 25 shut counties are shut by policy rather than by an absent page**,
which is what a re-examination should now expect.

Wiring `--check` into CI is what asked a second question the probe had never been asked: it
had reached across trees for `scripts/scraper_common.py`'s UA token since the day it was
written, and `validate_workflow_deps.py` had never looked, because that gate only reads the
scripts a workflow runs. A rule enforced only where a gate happens to look is a rule three
files were keeping by hand. The token is in-tree now with the note its siblings carry, and
`import requests` sits inside the one function that builds a session — proved by running
`--check` with an `ImportError`-raising `requests.py` on the path.

Battery: 84 static invocations pass, 9 of 10 browser gates pass, and
`page_consistency_test.mjs` reports 72 findings with 0 non-cert — all of them the GoatCounter
beacon's `ERR_CERT_AUTHORITY_INVALID` in this sandbox.

**2026-09-19, tranche 7 merged.** #1041 is in as `cb07f95e`, verified on the merged tree
rather than on my own PR body: `mi-commissioner-members.json` carries 48 counties and 366
districts, Cass holds 8 of 8 with District 1 reading Thomas Langley and
thomasl@cassco.org, and `mi/county-commissioner/cass.html` names both in the served bytes.
`validate_index.py`, `build_county_pages.py --check` and `validate_gate_counts.py` all pass
on that tree.

**The PR took three base merges and two of them were substantive**, which is the part worth
carrying. Main added a gate the branch's CI had never run — `validate_workflow_checkout.py`,
which exists because a sitemap-committing workflow in a shallow clone dates every entry to
the run day, and this change rewrites `sitemap.xml` — and then a Court of Appeals staleness
step. The battery went 80 → 81 → 83 no-browser invocations, and each time it was re-extracted
from the merged `smoke-test.yml` rather than from a saved list, because the gate list is the
thing that changes. A PR that sits for two hours on a fast-moving main is not idle; the
question is whether what landed is gated, and only a merge-base diff answers it.

Picking up the probe's own robots gap next — it needs no answer to the board's open question
and is the recorded prerequisite for any further sweep.

**2026-09-19, tranche 7 open.** #1041. Cass names its eight commissioners,
seven of them with an e-mail address. **48 of Michigan's 83 counties, 366 of
the 619 seats, 61.4% of the state by population** — and the probe's candidate
list is now EMPTY.

Cass cost two requests: its robots.txt and its board page, and it widens the
weekly run by one page from now on, which is the trade stated rather than made
quietly — seven addresses for one more request a week to a host already read. It was the last
candidate because the probe had scored the wrong page — the URL on its record
is the board's COMMITTEES page, which names all eight districts across five
committee rosters and is not a roster. A parser built on it would have shipped
a whole board and lost any commissioner who sits on no committee, and the
probe's own evidence cannot tell that page from the real one. The board page is
a different URL, linked from the committees page itself.

So Cass is the only county here that reads two pages, and each does one job.
The board page carries the people and the districts and no contact at all; the
committees page carries an address and the member's own district on one line.
The board page decides who is on the board. The committees page only adds an
address to a district already named, a district the two disagree on gets no
address and keeps its name, and a committees page whose shape has moved —
fewer than five addresses joining — refuses rather than shipping a thinner
card quietly. A committees page that simply does not fetch costs its own column
and nothing else.

Two stale things were corrected on the way past. The scraper's own docstring
still said twenty-six counties across four tranches, in three places, two
tranches after that stopped being true. And the sources page's comparison
against the state's own commissioner column was tranche 3's: re-measured across
all 48 counties, 234 of 366 seats agree exactly, 132 differ, and 18 of those
132 name a different person.

What is left on the probe's record is 25 counties measured shut, which is a
re-examination rather than a re-probe, and the probe's own gap: it records a
robots verdict only for the hosts it rejects, never for the one it accepts.

**2026-09-19, tranche 6 open.** #1035. Twenty-one more counties name your
commissioner: Alcona, Alpena, Arenac, Chippewa, Clare, Clinton, Delta, Emmet,
Houghton, Isabella, Lake, Luce, Mackinac, Menominee, Montcalm, Ontonagon,
Oscoda, Otsego, Presque Isle, Roscommon and Schoolcraft. That is **47 of
Michigan's 83 counties, 358 of the 619 seats, 60.9% of the state by
population** — up from 26 and 55.1% this morning. Each has its own page with
the names in the served bytes.

**No host was fetched to write any of it.** Every page came from the copy saved
during tranche 5's sweep, so those counties have seen two requests each in
total across both tranches.

**The catch that justified the pass is Houghton.** Its page puts the district
AFTER its own member, so the obvious reading gives a clean four of five with
every one paired to the wrong person and District 4 unnamed — and nothing in
the output says so. Mackinac is the same question with the opposite answer, so
every parser now states its side. Seven more traps are recorded at their
parsers, including a zero-width space in front of a Luce commissioner's name
and a shared county inbox that Chippewa would have handed to District 5 as
their own.

**It also found a defect in yesterday's work.** co.hillsdale.mi.us drops about
one connection in three from here and the drop lands on robots.txt, which is
read before the page — so the retry I added yesterday never covered it. Three
consecutive failures in one run dropped a county that had shipped that morning.
The robots read now retries five times.

**Cass is the one candidate left and I did not build it.** The URL the probe
scored is the board's committees page. All eight districts do appear across its
five committee lists, so a parser could assemble a whole board from them and
would silently lose any commissioner who sits on no committee. It waits for one
fetch of the real board page.

Next: Cass, then the 25 counties the probe recorded shut, then the probe's own
gap — it records a robots verdict only for the hosts it rejects.

**2026-09-19, merged.** Tranche 5 is in (#1033, merged 13:45 UTC as `3fb98206`).
Click a point in Barry, Cheboygan, Dickinson, Hillsdale, Ionia, Kalkaska,
Leelanau, Oceana, Osceola or Sanilac and the County Commissioner District card
now names the person, with a phone or an e-mail wherever the county publishes
one. That is 26 of Michigan's 83 counties, 229 of the 619 seats, 55.1% of the
state by population, up from 51.6%. Each of the ten also has its own page under
`mi/county-commissioner/` where the names are in the served bytes.

Picking up tranche 6 from the same list. The probe's remaining **22**
candidates need no new discovery, and every one of their pages is already
saved from last night's single fetch, so tranche 6 needs no fetch at all.
I published 24 last night and it was wrong — 34 minus the ten that shipped,
forgetting that Gogebic and Marquette left the pool the same day. 22 is the
artifact's own count after `--prune`.

**2026-09-19, later.** Tranche 5 is open as #1033. Ten more counties name your
commissioner: Barry, Cheboygan, Dickinson, Hillsdale, Ionia, Kalkaska,
Leelanau, Oceana, Osceola and Sanilac. That takes the card from 16 counties to
26, from 165 named seats to 229, and from 51.6% of Michigan's people to 55.1%.
Each of the ten also gets its own page under `mi/county-commissioner/`, where
the names are in the served bytes rather than behind a fetch.

**The weekly refresh has now run, and it moved nothing.** I dispatched it by
hand rather than waiting for the cron: run 35415178348, every step green, and
the change check came back empty, so the "open a pull request" step was skipped.
That is a result rather than a non-event. Those sixteen counties' names had
never been re-read since the day they shipped, and now they have been, and all
165 seats still name the same people. It is also the first evidence the roster
is stable rather than merely unchecked, and the job is proven end to end.

**A workflow that has never run is invisible to every gate here**, because
nothing in this repo measures the absence of a run. Michigan's was correctly
wired the whole time. Worth a sweep across the fleet at some point: which other
scheduled jobs have zero runs?

**On timing.** The instruction to update the board and pause reached me at
02:43 UTC, and tranche 5 was already built and under test by then; it opened as
#1033 eight minutes later. I have not started anything since. #1033 is watched
and I will drive it to green if CI goes red, but no new county work tonight.

Three things worth knowing from the work:

- **Two of the probe's candidates cannot be fetched at all.** Gogebic and
  Marquette each serve a robots.txt that disallows this client, read three
  times in a row, byte-identical to each other and to Genesee's and Ingham's.
  Both were recorded as candidates the day before. Either those files changed
  inside a day or the probe's read differed, and I cannot tell which: no
  archive holds either file, and the probe writes a robots status only for the
  hosts it rejects. That is the probe's own gap and it is recorded in its
  docstring.
- **Hillsdale is the opposite case.** Its robots.txt failed twice with a
  connection reset — which is disallow-all — and served a file allowing this
  path on the third try. A single transport failure is not a measurement. The
  scraper retries the transport now; it still takes a refusal and an HTTP
  status as answers.
- **Ionia District 3 is a seat the county itself calls vacant**, which is a
  third kind of unnamed seat beside Monroe's malformed row and Lenawee's
  self-contradiction, and gets its own sentence on the card. Its page carries
  the previous commissioner's whole entry commented out beneath the word, so a
  parser that reads comments would name a man the county has removed.

Every host in the tranche saw two requests, robots.txt and the page. Each page
was saved once and every parser written offline against the copy, because six
sweeps in four days tripped a WAF on Tuscola while the probe was being written.

Next: the candidates this tranche did not take. They need no new discovery.
(I wrote 24 here; it is 22 — corrected in the entry above.)

**2026-09-19.** Picking up tranche 5: more county commissioner names, from the
34 counties the probe in #989 measured as publishing a district-keyed board
page.

What the commissioner card gives a reader today is a name in 16 of 83 counties.
That is 165 of the 619 seats and 5,200,503 of Michigan's 10,077,331 people,
51.6%. In the other 67 counties the card gives the district number and names
nobody. The 34 candidates are 216 more seats and 1,064,500 more people;
shipping all of them would take it to 62.2%.

The candidates in population order start Clinton 79,128, Ionia 66,804, Montcalm
66,614, Marquette 66,017, Isabella 64,394, Barry 62,423, Cass 51,589. Clinton is
the largest of the 34, and 15 of them are under 25,000 people. Michigan is a
long tail from here, so a tranche is worth judging by seats and by whether the
page yields, not by population.

**The weekly refresh has never run.** `update-mi-commissioner-roster.yml` has
zero runs, ever. It is wired correctly — cron `30 20 * * 6`, `workflow_dispatch`,
in the shared root — but it landed on Saturday 2026-09-13 after that week's slot,
and tonight is the first Saturday since. So the 16 counties' names have not been
re-checked since the day they shipped, and the job has never been proven end to
end. I am dispatching it by hand rather than waiting for the cron.

The three items carried into the Tasks table, with the state I measured them in:

- **PR #979** merged on 2026-09-16. Its whole diff was one line: Detroit's
  roster going from `archivedAt: null` to a real snapshot stamp, so the card now
  prints which day's archived copy it read.
- **Tranche parser candidates** is `mi/data/source/mi-county-board-probe.json`,
  measured 2026-09-18: 34 candidate, 11 no-board-page, 7 no-districts, 3
  not-keyable, 2 no-confirmed-host, 2 challenge. It is the tranche 5 work list.
  `candidate` means a parser is worth writing, never that the county will ship.
- **Detroit PR-body proposal** is not implemented and is written down nowhere in
  the repo. The weekly Detroit PR body is one static paragraph, identical every
  week whatever changed, so it cannot tell a reviewer that a run moved a
  snapshot stamp rather than a person's name. It is worth doing and it is worth
  less than the roster.

Two corrections to my own last report:

- I said Emmet publishes 10 e-mail addresses as `mailto`. It publishes no
  `mailto` and ten Cloudflare-obfuscated ones. Same information, different
  markup — the Brown County shape the Kent and Lapeer parsers already decode.
  Lake (14) and Schoolcraft (5) are the same.
- Seven of the 34 candidates have a state-layer population that disagrees with
  the census, and Cheboygan's seven districts all publish Population 0 against a
  census 25,579. The probe artifact records the layer's figure and says so; every
  share above has the census on both sides.

## Open questions for Adam

**2026-09-19 — may the state's precinct fabric be the SOURCE for a city's wards,
or only the check?** This is the decision under most of the remaining ward gaps, it is
recorded twice in this repo as the operator's call, and nobody has been asked. It costs no
fetches to answer.

**Correcting my own note above.** I wrote that I was starting on (2) because
`mi/WATCH.md` line 30's WARD query "needs no answer". That query is already spent — it was
run on 2026-09-06 and settled 23 cities in one go. Nothing on the ward front is one cheap
query away any more, and the four unshipped cities I checked (Kentwood, Midland, Holland,
Muskegon) each carry a measured record saying neither the city nor its county publishes a
ward boundary this app can read. The remaining ward work is either per-city discovery, which
costs fetches exactly like option (1) above, or this posture question.

What is true today. Michigan's own 2026 precinct layer carries a WARD column. Six cities
ship a ward polygon — Detroit, Warren, Grand Rapids, Flint, Rochester Hills, Battle Creek —
and every one of them takes its boundary from the CITY's own publisher, with the state's
column used as an INDEPENDENT currency check. That check is what separated Flint's plan in
force from two superseded ones by twenty-three points, and what refused Bay City.

Of the ten cities the state's column calls districted, eight have no ward polygon here:
Wyoming, Pontiac, Kentwood, Midland, Muskegon, Jackson, Bay City, Holland. The state's
fabric could draw wards for all eight without fetching any of those cities. Wyoming's is
already measured — it dissolves to 6/6/6 across three wards — and the other seven are one
query away.

What it costs, stated plainly. The currency check stops being independent: today the city
draws the boundary and the state checks it, and under this posture the state is both, so a
ward this app draws could never again be shown to disagree with the city that elects by it.
Two cities make that concrete. Bay City publishes its own nine-ward layer and it scores
97.608% against the state fabric with the disagreement spread across twelve ward pairs —
two plans, not one bad edge — so drawing from the state means overriding a city's own map
rather than filling a silence. Muskegon's only published map leaves parts of the city
uncovered, so there the state route fills a real hole. Those are different situations and I
would not answer them the same way.

One more consequence worth knowing before deciding: it would sidestep Lansing's licence
block. Lansing's wards are built and unshipped because the only clean copy states no licence
while the same plan one item away states CC BY-NC 4.0, and the operative reading is NC. The
state's fabric is a different publisher under different terms, and Lansing already measures
99.893% against its WARD column. That is a reason to be careful rather than pleased —
routing around a licence by changing publishers is a decision, not a workaround, and it
should be made on purpose.

Nothing ships either way without the usual per-city build and its gates. The question is
only whether the state may be the source.

**2026-09-19, update — (3) is done and it changed what (1) costs.** #1045
records the accepted host's robots reading and gates on it. The backfill read
33 robots.txt across 24 hosts and found **two of the 25 shut counties shut by
POLICY rather than by an absent page**: `www.iosco.org` answers HTTP 403 on
robots.txt, which the strict reading a county website gets makes a refusal, and
`tuscolacounty.com` serves a 26-byte file that disallows this client. So a
re-examination under (1) is **23 counties, not 25** — Iosco and Tuscola may not
be fetched at all now, whatever budget is set. The question below is otherwise
unchanged, and unanswered.

Starting on (2) in the meantime: `mi/WATCH.md` line 30's WARD query is one
request against a service this instance already reads, and it needs no answer.

**2026-09-19 — the commissioner candidate list is empty. Which work comes
next?** Not blocking: I am starting on (3) below, which needs no answer and is
the recorded prerequisite for anything that sweeps again.

What I measured. 48 of Michigan's 83 counties name their commissioners. The
probe's record now holds ZERO candidates and 25 counties measured shut: 11
no-board-page, 7 no-districts, 3 not-keyable, 2 no-confirmed-host, 2 challenge.
23 of the 25 carry a confirmed host; Shiawassee and Montmorency carry none.

Three things could come next and they cost very different amounts.

1. **Re-examine the 25 shut counties.** The largest bucket is the 11 with a
   confirmed host and no board page found from the sitemap or the front page,
   which is the shape Washtenaw turned out to be (the real board page sat on a
   different host spelling) and the shape Illinois's Vermilion turned out to be
   (the county's GIS was a different publisher from the county's website). So
   this is the one most likely to yield. It is also the most expensive: these
   hosts have been swept three to six times already, and that is what tripped
   a WAF on Tuscola. **The question I would want settled before starting is
   what a re-examination may fetch** — my own proposal is at most one request
   per county, to a URL the existing record does not already name, and nothing
   at all to a host recorded as a challenge.

2. **City council wards, 18 of the 20 recorded Michigan gaps.** Already on the
   manager's Tasks table. `mi/WATCH.md` line 30 says to run the state's WARD
   column first, which is ONE query against a service this instance already
   reads, and it settled 23 cities on 2026-09-06. So it is the cheapest of the
   three by traffic and the largest by gap count.

3. **The probe's own robots gap.** `probe_mi_county_boards.py` records a robots
   verdict for every host it REJECTS and none for the one it ACCEPTS, which is
   why the Gogebic/Marquette disagreement (candidate on 09-18, `Disallow: /` on
   09-19) could not be settled. Writing the field costs no fetches. Backfilling
   the 23 recorded hosts costs one robots.txt read each and nothing else —
   robots.txt is the request every client makes first — and it only makes
   FUTURE readings comparable, since the 09-18 readings are already lost.

**What I would pick, in order: 3, then 2, then 1.** 3 costs nothing and every
further sweep is worth less without it. 2 is one query for the biggest gap
count. 1 is the most likely to yield a county and the only one whose budget I
would want stated rather than assumed.
