# Michigan board

Owner session: **Michigan**. Manager owns *Tasks*; this session owns *Status*
and *Open questions*. Rules and reporting posture: `BOARD.md` at the repo root.
Commit board edits straight to main, in their own commit, dated.

## What a reader gets today

Click any point in Michigan and the app answers from **15 layers** — the fewest
in the fleet, because Michigan is the newest instance (live 2026-09-03). The
state House and Senate rosters are complete at 110 and 38.

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

**2026-09-19, tranche 6 merged.** #1035 is in. **47 of Michigan's 83 counties
name your commissioner — 358 of the 619 seats, 60.9% of the state by
population.** This morning it was 16 counties and 51.6%.

Picking up Cass, the last candidate. Its probe URL is the board's committees
page, so this one costs a fetch: robots.txt and the county's own board page,
and nothing more.

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

- Nothing outstanding.
