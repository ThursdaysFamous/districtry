# WATCH.md — redistricting watch calendar

The one place the dates live: *when to look* for boundary and roster changes in this
instance's sources. The repo's `docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a
boundary changes. Update the "Last done" column each time you complete a row — a
checkpoint with a stale date is a checkpoint that didn't happen.

This instance arrived DARK (PR 1, 2026-09-29) and was **PUBLISHED on 2026-09-30** — live at
districtry.com/mn/, with the deploy exclude narrowed to `mn/data/state mn/data/source
mn/scripts` and an `mn` row in `metros.json`. The **GO-LIVE** rows below are kept with their
dates filled in rather than deleted: each one is a thing that had to be true before publishing,
and the next state's thread reads them as a checklist rather than as history.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| Weekly (Mon 13:40 UTC) | U.S. House (MN) roster refresh | `.github/workflows/update-mn-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |
| Monthly (1st, 18:00 UTC) | Source-freshness check: are the 13 cited TIGERweb and USGS endpoints still answering, and is every built `data/app` file still present | `.github/workflows/mn-validate-sources.yml` → opens or refreshes one tracking issue | Read the issue. Nothing is auto-applied: swapping a dataset is schema-sensitive, so the issue is the signal and the job stays green |

**THE MONTHLY CHECK WAS MISSING UNTIL 2026-10-01 AND EVERY OTHER INSTANCE HAD ONE.**
`mn/scripts/validate_sources.py` shipped with PR 1 and ran in no workflow at all, so
this instance's only automated source check was the weekly roster refresh — which
re-reads one page and can say nothing about the 13 TIGERweb and USGS endpoints the
other twelve layers draw on (measured 2026-10-01 off the validator's own manifest;
its Socrata table is empty, because no layer here reads a portal dataset). Its own docstring said the workflow was deferred because
the instance was dark and pointed at a GO-LIVE row below that carries it; the instance
stopped being dark on 2026-09-30 and that row was never written. Both are fixed
together. The `mn-` prefix is load-bearing for the reason every sibling's file states:
Actions reads workflows only from the repository root, where all nine instances share
one namespace.

Only one roster refreshes here, because only one roster ships. The two chamber cards and
the county card name nobody — gaps `mn-legislature-roster`, `mn-county-commissioner-roster`
and `mn-county-officers` in `docs/DATA_LAYER_GUIDEBOOK.md`.

---

## GO-LIVE — what the publishing change has to carry

| Item | What | Why it cannot wait | Last done |
|---|---|---|---|
| Sibling fixes on main | **Iowa's fix (#1267) and Wisconsin's matching one must both be on `main` before this instance is published.** Iowa settled its own dependency in #1267 by having its checks REFUSE `fleet-outlines.json` rather than moving its point, which is the better answer — the point stays where it was measured and the gate stops reading a file that will legitimately change. Iowa also found that **Wisconsin's negative point (47.39, -92.97) is inside Minnesota** and has the same dependency, and Wisconsin fixed it the same way in **#1268**. Check both are merged, and check no instance added after 2026-09-29 has arrived with the same problem, before publishing. #1268 also measured the thing that makes this a pattern rather than three coincidences: sampling Wisconsin's whole `permalink_gate` every 0.25 degrees, **all 609 points land in some state**, and the 300 outside Wisconsin are Michigan 163, Minnesota 76, Iowa 47 and Illinois 14 — three of them live instances today. There is no point to move to, and the Great Lakes are no refuge because Michigan's fabric is water-inclusive. Refusing the fleet file is the answer, not a better point | Either instance's smoke test would fail on the publishing PR, and the symptom — a timeout waiting for a masthead button on a page that has navigated away — names nothing about the cause |2026-09-30 (both merged: #1267, #1268) |
| Iowa's negative point | **Iowa's own negative point starts handing off the day this instance is published.** `ia/metro-worksheet.json` pins 43.65, -93.37, which is inside Minnesota; once `mn` is in `fleet-outlines.json` the Iowa app's `placeOwner` will hand that selection to `/mn/` and Iowa's smoke test will find its page navigated away. That is exactly how this instance's own first negative point failed — 43.45, -93.37 in Worth County, Iowa, which passed every static test and made the browser leave. **A negative point must be outside every LIVE instance, not only outside its own.** **SUPERSEDED IN ITS REMEDY, NOT IN ITS LESSON**: Iowa did not move its point, it made its checks refuse the fleet file (#1267). The lesson stands and generalises — every live instance's negative point has to be re-read against a new instance's outline, which is what turned up Wisconsin's | Iowa's smoke test would fail on the publishing PR, and the symptom (a timeout waiting for a masthead button) does not name the cause |2026-09-30 (settled in #1267 by refusing the fleet file, not by moving the point) |
| Our negative point | **This instance's own negative point is sound today and rests on North Dakota being unserved.** Cass County, ND is outside every live instance, so `placeOwner` finds no owner and the app selects the point locally — which is why `mn/scripts/smoke_test.mjs` does not refuse `fleet-outlines.json` the way Iowa's and Wisconsin's now do (#1267, #1268). It breaks the day a Dakotas instance ships, silently, as a timeout waiting for a masthead button. Adopting the refusal pattern here would close it by construction and is one `page.route` line; it is NOT done in PR 1, because nothing is broken and widening that PR to pre-empt an instance nobody has planned is the operator's call rather than this thread's | Not a go-live blocker — a Dakotas blocker. Recorded so the next state's thread finds it rather than rediscovering it as a timeout | — |
| Fleet point sweep | **THE FLEET WAS SWEPT FOR THIS AND #1267 AND #1268 COVER ALL OF IT.** The coordinator asked whether anything BESIDES a `NEGATIVE_POINT` centres a point Minnesota will claim. Swept 2026-09-29 over every `scripts/*.mjs`, `*/scripts/*.mjs`, `*/metro-worksheet.json` and `metros.json` in the tree: **48 coordinate pairs, of which exactly two land inside the shipped `mn/data/app/metro-outline.json`** — Iowa's negative point (43.65, -93.37) and Wisconsin's (47.39, -92.97), the two already fixed. Every other point is inside its own instance: Iowa's Marshalltown anchor and statewide gap probe, Wisconsin's Marathon anchor, statewide probe and Madison aldermanic permalink, Illinois's Evanston school probe, New York's City Hall probe, and the root landing test's seven destinations (Dallas, Marquette, Sturgeon Bay, Dubuque, Rock Island, Ironwood, the Gary stub). **The offline anchors in each instance's `build_metro_outline.py` are deliberately not in that count**: an `OUTSIDE` anchor is a point outside that instance's own ring, tested in Python against a shipped file with no browser to navigate, so Minnesota's arrival cannot touch it. So nothing is owed to another state's thread | A second instance breaking on the publishing PR is the one failure whose symptom — a timeout waiting for a masthead button on a page that has navigated away — names nothing about its cause, which is why the sweep is recorded with its surface and its count rather than as "checked" | 2026-09-29 |
| Fleet outlines | Rebuild `fleet-outlines.json` (`scripts/build_fleet_outlines.py`) with Minnesota's outline as a `SOURCES` entry, and add an `mn` row to `metros.json` | The front door and every sibling app route by that file; without it no address in Minnesota reaches this app, and the landing page does not list it |2026-09-30 (7 instances, 86,031 bytes; `mn` → `mn/data/app/metro-outline.json`) |
| Clipped hand-off bbox | **The fleet hand-off bbox must be CLIPPED, and this is the Michigan case again.** Minnesota's county fabric runs east to -89.4834 (Cook County's tip on Lake Superior), which contains Wisconsin's own centre (44.9, -89.565) — so an unclipped box fails `validate_index.py`'s "a bbox must not contain a sibling metro's centre" rule on `wi`. Only Cook County reaches east of -89.60; the next county east edge is Lake at -90.7952, so clipping the fleet box costs one county's lakeshore tip in a fallback the apps no longer use for routing | Measured 2026-09-29 on the shipped `mn/data/app/state-counties.json`. `metro_explorers`' own self-entry is exempt from that rule and carries the full extent; the FLEET box in `metros.json` is the one to clip |2026-09-30 (clipped to maxLng -89.58; the cost is recorded in metros.json's own $comment) |
| Sibling explorer lists | Add an `mn` entry to the other six instances' `metro_explorers`, and check each one's new entry does not contain that instance's own centre | A sibling that does not list Minnesota sends a Minnesota address nowhere; one that lists it before the deploy publishes `/mn/` sends a reader to a 404 |2026-09-30 (`--sync-fleet`; every instance's `validate_index.py` passes) |
| Deploy exclude | Narrow the `'mn/**'` line in `deploy-pages.yml` to `mn/data/state mn/data/source mn/scripts`, matching `ia` and `mi` | `validate_instance_registration.py` holds the deploy exclude and `metros.json` together in both directions, so this and the `metros.json` row are one change |2026-09-30 |

---

## Still owed after go-live — what the publishing change did NOT carry

| Item | What | Why it was left, and what it costs a reader | Last done |
|---|---|---|---|
| faq.html | **`faq.html` — every other live instance has one and this one does not.** The go-live change shipped `sources.html`, because that page GENERATES: each of the thirteen `layers[]` entries already carried a `source` block, so its matrix and credit rows came out of the worksheet with nothing to write. The FAQ is hand-written prose answering questions about THIS state — what a Minnesota township is, why the two chamber cards name nobody, what the school-district tilings mean — and prose cloned from a sibling and search-replaced is how Michigan's go-live shipped Iowa's whole identity block. So it is its own change rather than a rushed one | A reader has no page answering the questions the cards raise, and the masthead is one link shorter than every sibling's. Not a wrong answer anywhere — an absent one | — |
| history.html | **`history.html` — the instance has no deployment record page.** `il`, `wi`, `ia` and `mi` each carry one, GENERATED by `scripts/build_history_page.py` from a `history_page` worksheet key plus measured stat tiles. It needs the key, the changelog prose, and the reciprocal obligation the generator imposes: every weekly workflow that rewrites a file a tile counts must regenerate the page in the same run. Minnesota has one weekly workflow today (the U.S. House roster), so that obligation is small now and grows with each roster built | Nothing a reader is told is wrong; the instance simply publishes no record of its own changes | — |
| Smoke test reads the fleet file | **This instance's own smoke test still reads `fleet-outlines.json`.** See the Dakotas row above — Iowa and Wisconsin both moved to refusing that file (#1267, #1268) and this instance did not, because nothing is broken while the Dakotas are unserved | Not a live defect. It becomes one, silently, the day a Dakotas instance ships | — |

---

## Per-class re-checks — the files no job rewrites

`docs/EAM_STATUS.md` measures whether every data file the app reads is under a stated
plan: a scheduled job that rewrites it, a scheduled watcher on its source, or a row
here that names it and says WHEN it is re-checked. Measured 2026-10-01, **six of this
instance's seven files were under none of the three.** Only `congress-roster.json` was,
through the weekly refresh in the Standing table above.

A weekly job cannot serve the other six. Five are boundary geometry and the sixth has
no upstream at all, so a scraper run every Tuesday against a county outline that moves
once a decade is a guaranteed no-op; a stated cadence here is the honest alternative.
Every file is named individually rather than as a glob, because there are six of them
and this instance has no file class large enough to need one.

**ONE OF THE SIX WAS ALREADY READING AS PLANNED, OFF PROSE, AND THAT IS WHY THE
BENCHMARK COUNTED FIVE.** `build_eam_status.py` reads a table row's FIRST cell as
the cadence, and three tables in this file — GO-LIVE, Still owed, and Minnesota
specifically — put a paragraph there rather than a when. One of those paragraphs
records a fleet sweep dated 2026-09-29 and names `metro-outline.json` in passing, and
the cadence vocabulary matches a bare `20\d\d-\d\d-\d\d` anywhere in the cell, so a
sweep date promoted a narrative row to a maintenance plan for a file it was not about.
Nothing was wrong with the instrument's rule and nothing is wrong with the prose; the
two met in the one place the rule assumes a column holds a cadence. Those three tables
now carry a short label column, so their first cell states no when and the only rows
claiming these files are the ones below. **The measured figure is six of seven, not
five** — worth stating because a file that passes off a date in somebody else's
sentence looks exactly like a file that passes.

**THE RUNBOOK HAS NO MINNESOTA SECTION**, so each clock below states its own authority
rather than quoting one. `docs/REDISTRICTING_RUNBOOK.md` carries per-layer exposure
classes for Chicago, New York, San Francisco, Wisconsin and Michigan and stops there;
Iowa and Minnesota both reach it through nothing. Writing one is not this instance's to
do alone — it is a fleet document — and the absence is recorded here so the next pass
knows the quoting convention Illinois uses is unavailable to Minnesota.

| Cadence | File | The clock, and whose it is | Last done |
|---|---|---|---|
| **Each decennial census** (next: **2031–2032**), and on any court-ordered or mid-decade redraw | `congress-districts.json`, `mn-senate-districts.json`, `mn-house-districts.json` | All three are drawn on the census cycle and all three ship from one mapshaper topology, so one trigger moves all of them. The Per-decade table below is the procedure — it carries the no-arguments rule, the count checks and the `FIDELITY_MAX_M` re-measurement; this row is only the when | 2026-09-29 (initial build) |
| **Annually**, when TIGERweb publishes a new county vintage | `state-counties.json` | The county fabric is TIGERweb's State_County layer 1, and the Census Bureau rolls that vintage rather than announcing a boundary change. Annexations and the rare county-line adjustment arrive inside a vintage roll, which is why the clock is the publisher's and not a redistricting cycle. The runbook gives the same family a *TIGER-rolling* class in Michigan's and Wisconsin's own sections. **`mn/scripts/build_state_counties.py` HAS NO `--check`**, so a re-read here is a rebuild and a diff, not a verification | 2026-09-29 (initial build: 87 counties) |
| Same roll (**annually**, the TIGERweb county vintage) | `metro-outline.json` | Dissolved from the same fabric as the row above, so it has no clock of its own — but it is not a no-op to re-check, because the coverage ring carries 87 INSIDE anchors at interior points and a moved county line can put one outside its own county. `mn/scripts/build_metro_outline.py --check` is what says so, and unlike the counties builder it exists | 2026-09-29 (initial build: 87 counties, 1 ring, 5,287 vertices, all 87 anchors correct) |
| **Annually** | `coverage-gaps.json` | The one file here with no upstream publisher: its source is this project's own gaps block for `minnesota` in `docs/DATA_LAYER_GUIDEBOOK.md`, and what decays is the records rather than a dataset — an ask that was answered, a source that reopened, a county that shipped. `build_coverage_gaps.py --check` runs on every pull request and proves the file matches the guidebook; it can never say the guidebook is still true, which is why a gate is not a cadence and this row exists | 2026-09-29 (initial build: 6 records) |

---

## Per-election — the seats above the boundaries

| When | What | Last done |
|---|---|---|
| After each U.S. general (November, even years) | The delegation turns over; the weekly congress-legislators refresh picks it up | 2026-09-29 (initial build: 8/8, each with a district office) |
| After each Minnesota general (November, even years) and each January seating | The two chamber rosters turn over — and this instance names nobody in either, so there is nothing to refresh until `mn-legislature-roster` is built. Until then the cards enter the engine chamber factory's roster-miss path and link each chamber's own directory | — (gap `mn-legislature-roster`) |
| After each Minnesota general | The 447 county commissioners turn over, and no publisher pairs them with their districts (gap `mn-county-commissioner-roster`) | — |

---

## Per-decade — the census redistricting cycle

| When | What | Last done |
|---|---|---|
| After each decennial census (next: 2031–2032) | Congressional + legislative districts redraw: re-run `mn/scripts/build_legislative_boundaries.py` (**NO arguments** — it rebuilds all three chambers in one mapshaper run and rejects a per-chamber argument, because rebuilding one alone is what broke Illinois's and Iowa's House/Senate nesting), confirm the counts against the apportioned delegation and the 67/134 chambers, re-verify the smoke anchors, and bump `sw.cache_name` — this geometry is cache-first. A redistricting also re-opens `FIDELITY_MAX_M`: it is 34.0 m because Minnesota's own median staircase step measures 31.2 m (mn-house) and 37.6 m (mn-senate), so **re-measure that step on the new lines rather than carrying the number forward** | 2026-09-29 (initial build as one topology: 100.00% agreement on all three, 67/67 nesting pairings exact, worst stray 17.7 m against the 34.0 m ceiling) |
| After each decennial census | `mn/scripts/build_state_counties.py` and `mn/scripts/build_metro_outline.py` — county boundaries move rarely, but the outline's 87 INSIDE anchors are interior points and a boundary change can put one outside its own county. `build_metro_outline.py --check` is what says so | 2026-09-29 (initial build: 87 counties, 1 ring, 5,287 vertices, all 87 anchors correct) |

---

## Minnesota specifically — no fixed cadence

| Item | What | Why it is here | Last done |
|---|---|---|---|
| SoS precinct service | **The Secretary of State's precinct layer is this instance's whole growth path and it is ONE service.** `enterprise.gisdata.mn.gov` → `us_mn_state_sos/bdry_votingdistricts/FeatureServer/0`, 4,105 precincts, `maxRecordCount` 2000 so it pages. Seven layers dissolve out of its own attributes: `ctycomdist` (447 county commissioner districts, all 87 counties), `pctcode` (precincts), `juddist` (10 judicial), `swcdist_n` (117 soil & water), `hospdist_n` (16 hospital), `parkdist_n` (3 park) and `ward` (274 wards in 76 cities). **A single upstream service is a single point of failure for seven layers**, so watch its `Service Modified` stamp (2026-09-17 when measured) and re-check the seven field names, not just the endpoint | Measured 2026-09-29. `gis.data.mn.gov`'s robots.txt allows this client with **Crawl-delay: 60** binding on `*` — honoured, and it makes a full page-through slow rather than impossible. The separate `www.mngeo.state.mn.us` serves a Radware Bot Manager captcha to this project's token: obeyed, never worked around, and it costs nothing because the data is on the enterprise host. **Do not let a later pass read "MnGeo is blocked" as "Minnesota publishes nothing"** — that is the Knox shape | 2026-09-29 |
| Commissioner roster route | **The commissioner ROSTER route is unproven, not closed, and the difference is one measurement.** The SoS's companion results service `bdry_electionresults_2022_2030` carries federal and state contests only — no commissioner column — so composing a roster out of certified returns is shut there. Its `LocalRacesInCounty` pages were read for ONE county at ONE election id with no commissioner contest found, which is one reading and not a finding. If those pages carry commissioner contests, all 447 seats come from one publisher; if they do not, this is the Michigan shape — 87 counties in tranches off their own board pages | This is the next research question for this instance, and it decides whether the flagship layer ships with names or without | 2026-09-29 (one county, one election id) |
| Negative point rule | **A negative point must be outside every live instance.** See the GO-LIVE row above. The two points tried before Cass County, North Dakota are recorded in full in `mn/metro-worksheet.json`'s `negative_point.note`, including why Lake Superior does not work: Minnesota's TIGER county fabric is water-inclusive to the international boundary, so a point in open lake at 47.6, -90.0 is named `Lk Superior` by TIGERweb's hydrography **and is still inside Cook County** | Both failures looked obvious and both were caught by measurement rather than reasoning | 2026-09-29 |

## Tribal-nation roster hosts, measured 2026-09-29 under RFC 9309

Not a gate. A record of what one client got from which address, so the next pass
does not repeat the probe or read a stale verdict as a finding.

- `www.redlakenation.org` — the nation's site, and a **managed challenge fronts
  robots.txt itself** (11,990 bytes of markup, not a document), so `RobotsGate`
  declines the host and nothing further is asked of it. Bare
  `redlakenation.org` is a default IIS7 welcome page and `redlakenation.com` is
  a for-sale parking page; neither is the nation and neither is a refusal.
  A verdict recorded against either would have been about nothing.
- `mn.gov/indian-affairs` — the state's own compilation, and the one publisher
  that would list every nation's council in one place. robots.txt allows.
  On the first request of the day it served the **districtry token** HTTP 200
  and a real 40,518-byte page. The probe then tried the Chrome string, which
  Radware redirected to its interstitial, and **every request from this address
  since — the token's included — is 302'd there**. So a host that had been
  serving us now blocks us, and our own probe is the likeliest cause: the same
  posture this repository already takes on a 429.
  **A crawler here sends the token and does not try the browser rung.** Trying
  it is what closed the door, and a browser string is not a superset of the
  token — Kendall and McHenry are the reverse case, 200 only to the stdlib
  client carrying Chrome's hints. Ask both rungs only where one has failed.
- Readable to the token: `whiteearth.com` (Crawl-delay 30, honoured),
  `millelacsband.com`, `llojibwe.org` (Leech Lake; the earlier `llojibwe.net`
  reading was at the wrong domain).

None of this is in a shipped file yet. Tribal geometry rides a later PR and the
per-nation rosters are their own change; a nation that cannot be read becomes a
recorded gap naming its own government.

**MINNESOTA'S TRIBAL GAP RECORD IS NOT THIS INSTANCE'S TO WRITE.** The fleet-wide
tribal-government thread owns it and carries it in PR #1273, so nothing here
opens a second record for the same absence — two records of one gap is how they
come to disagree. That thread also settled the one boundary question this
instance had raised: the **Lake Traverse** reservation's intersection with
Minnesota is a **zero-area line**, because the reservation's eastern edge IS the
state line and no Minnesota ground is enclosed. The 0.139 km² this thread had
measured was a SIMPLIFIED state outline measured against a full-precision
reservation, which is an artefact of two different detail levels rather than
ground. Minnesota's tribal subdivisions are 17.

## Judicial elections — MEASURED 2026-10-01 for the Covered test

**MINNESOTA ELECTS ITS TRIAL JUDGES BY DISTRICT. YES.** `docs/DONE_STANDARD.md`
leaves this to each thread for Michigan, Minnesota and Kentucky and asserts it
of none of the three; this is Minnesota's answer, from the state's own published
law, read with this instance's own user agent after a robots check through
`scripts/robots_policy.py` (`www.revisor.mn.gov` serves a 342-byte policy whose
one binding group matches none of these paths).

Three provisions settle it together:

- **Minn. Const. art. VI § 7** — "The term of office of all judges shall be six
  years and until their successors are qualified. They shall be elected by the
  voters **from the area which they are to serve** in the manner provided by
  law." Art. VI § 4 puts the number and boundaries of the judicial districts in
  statute.
- **Minn. Stat. § 2.722 subd. 1** — the state "is divided into ten judicial
  districts composed of the following named counties, respectively, **in each of
  which districts judges shall be chosen** as hereinafter specified", then lists
  each district's counties and its judge count.
- **Minn. Stat. § 204B.36 subd. 4** — the ballot. "Each seat for an associate
  justice, associate judge, or judge of the district court must be numbered. The
  words 'Supreme Court,' 'Court of Appeals,' and **'(number) District Court'**
  must be printed above the respective judicial office groups." So a voter is
  handed their own district's numbered seats, which is the by-district election
  the test asks about.

**THE COURT OF APPEALS IS THE COUNTER-EXAMPLE AND IT IS WHY THE ANSWER NEEDED
READING RATHER THAN INFERRING.** § 480A.02 subd. 3 designates one seat on that
court for each congressional district and requires a year's residence in it —
which reads exactly like a districted court — while **subd. 4 says all judges
are subject to STATEWIDE election, "whether they serve in at-large or
congressional district seats."** That is the residency-district-with-countywide-
election shape this project already handles in Iowa: the district is real, the
election is not held in it, and nobody is elected by it. A seat designation is
not an electorate. The Supreme Court is statewide outright.

**WHAT THAT MAKES BUILDABLE, AND WHAT IS NOT MEASURED HERE.** § 2.722's ten
county lists are a PARTITION of the state: parsed from the statute they name
**87 counties with no county in two districts and none missing**, against the 87
features `mn/data/app/state-counties.json` already ships, and 287 judgeships in
all. So the geometry is a dissolve of a fabric this instance already carries,
with the statute as the composition and the county count as its own gate — no
new boundary publisher is needed. NOT measured, and not claimed: whether any
Minnesota publisher offers the ten districts as a layer of their own, and
whether a machine-readable roster of sitting judges exists. `www.mncourts.gov`
answers a robots request **403 — no readable policy, which RFC 9309 files with a
404 and therefore allows** — and nothing here has fetched a page from it. A
roster route is the next question, not an answered one, and a layer that draws
ten districts and names none of 287 judges is the faked depth this project
refuses.

Nothing in this entry ships. It is the Covered test's question answered, and the
judicial layer is its own change.

## The Covered test — what each missing level IS, measured 2026-10-01

The report scores Minnesota 5 of 13 levels. Eight are open, and the report says
of each only that it is open — "a floor", in its own words. This section is what
each one actually is in Minnesota, so the next change builds instead of
researching. **Nothing here is a gap record and nothing here is credited toward
the test.** `docs/DONE_STANDARD.md` credits a record only after a dated ask that
was refused, or an ask plus one follow-up and thirty days of silence, and **no
Minnesota office has been asked anything by this project**. So every level below
is open on the merits, which is the honest position.

Law read from `www.revisor.mn.gov` (342-byte robots policy, no rule matches
these paths). The catalogue read is `gis.data.mn.gov`, which `gisdata.mn.gov`
301s to and whose **robots.txt states Crawl-delay 60** — honoured, one request a
minute, which is why this was seven queries and not a sweep.

**LEVEL 10, SCHOOL BOARDS BY DISTRICT, IS THE ONE THE STANDARD LEFT TO THIS
THREAD, AND THE ANSWER IS: THE LEVEL EXISTS, OPT-IN, DISTRICT BY DISTRICT.**
Minn. Stat. § 205A.12 subd. 1 — "Any independent school district **may** alter
its organization into separate election districts for the purpose of election of
board members by following the procedures in this section." It takes a board
resolution or a petition and then a referendum (subd. 2-3), the districts must be
compact, contiguous and near-equal in population and are numbered (subd. 4), and
a candidate then files for the election district they live in (subd. 5). So this
is neither a statewide yes like Iowa's director districts nor a no: **some
Minnesota school districts elect by district and most elect at large, and which
ones is a measurement nobody here has taken.** The level is therefore OPEN and
not "does not exist". What the catalogue does publish is school district
BOUNDARIES statewide, which is the wrong geometry for this level — a district's
own election districts are a sub-fabric, published if at all by the district.

**LEVEL 4, COUNTY BOARDS, IS DISTRICTED IN EVERY COUNTY BY STATUTE — AND THE
GEOMETRY IS PUBLISHED COUNTY BY COUNTY, NOT STATEWIDE.** Minn. Stat. § 375.025
subd. 1: "Each county **shall** be divided into as many districts numbered
consecutively as it has members of the county board", bounded by town, municipal,
ward or precinct lines, within ten percent of the county average. So there is no
at-large county in Minnesota to carry on a County card, and all 87 want drawn
districts — the Illinois shape, 87 times. A relevance search of the state
catalogue returned **no statewide commissioner-district layer** and two
county-published ones (Hennepin's `Commissioner Districts`, Dakota's
`County Commissioner Districts (2022)`), with Ramsey publishing its own
precincts. **That is a relevance search of ten rows, not an inventory**, so it
is evidence that no statewide layer surfaced and not proof that none exists.

**LEVEL 9, TOWNSHIPS, EXISTS AND ITS BODY IS ELECTED TOWN-WIDE.** Minn. Stat.
§ 367.03 subd. 1 — three supervisors elected in each town at the town general
election, two under option A. So the town is the unit and there is no sub-town
district to draw: the level is answered by naming each town's board, exactly the
shape `docs/DONE_STANDARD.md` counts for New York's towns and Michigan's
townships. The GEOMETRY is already published statewide —
**`City, Township, and Unorganized Territory in Minnesota`** (MnDOT_GIS, the CTU
fabric), with a `County, City and Township (CTU) Lookup Table` beside it. The
ROSTERS are the whole of the work and they are per-town, in the high hundreds;
no statewide roster surfaced.

**LEVEL 11, PRECINCTS, HAS A STATEWIDE PUBLISHER.** **`Voting Districts,
Minnesota`** on the state's own catalogue, beside `Minnesota General Election
Results, 2022-2030` per precinct. This is the cheapest of the eight to close and
it is a layer a reader sees, so it is not this thread's to self-merge.

**LEVEL 12, SPECIAL DISTRICTS, HAS AT LEAST ONE ELECTED-BY-AREA BODY AND AT
LEAST ONE THAT IS APPOINTED, AND THE DIFFERENCE DECIDES WHETHER IT BELONGS ON A
MAP AT ALL.** Hospital districts: § 447.32 subd. 1 — "governed by a hospital
board composed of one member elected from each city and town in the district and
one member elected at large", which is an elected-by-area body and in scope.
Watershed districts: § 103D.311 subd. 2 — managers are **APPOINTED** by the
county boards, so a watershed district has no elected seat and drawing one would
name an appointee as a representative. `Watershed Management Districts and
Organizations` is published statewide; that makes it drawable and not an
officeholder level. **Which Minnesota special districts elect and which appoint
has not been enumerated**, and this project's own rule is that the answer decides
the layer, not the availability of the boundary.

**LEVEL 8, THE TEN JUDICIAL DISTRICTS, IS CONFIRMED ABOVE AND ITS GEOMETRY NEEDS
NO PUBLISHER.** See the judicial section: § 2.722's county lists partition the
state 87/87, so the districts dissolve from `state-counties.json`. A relevance
search of the catalogue surfaced no judicial-district layer, which is consistent
and is again not proof. **The roster is the blocker, not the boundary**: 287
judgeships and no machine-readable list established, and a layer that draws ten
districts and names nobody is the faked depth this project refuses.

**LEVEL 13, TRIBAL GOVERNMENTS, IS NOT THIS INSTANCE'S.** The fleet-wide
tribal-government thread owns it, as the section above already records.

**WHAT THIS MEANS FOR THE MARK.** Six of the eight want a layer and a roster
that a reader sees, so none of them is this thread's to self-merge, and two of
them (every county's board, every town's board) are the largest single pieces of
work this instance has in front of it. Nothing here can be closed by writing a
record, because nobody has been asked. Minnesota will not pass Covered today and
saying otherwise would be the thing this file exists to prevent.
