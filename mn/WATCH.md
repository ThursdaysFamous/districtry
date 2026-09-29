# WATCH.md — redistricting watch calendar

The one place the dates live: *when to look* for boundary and roster changes in this
instance's sources. The repo's `docs/REDISTRICTING_RUNBOOK.md` is *what to do* when a
boundary changes. Update the "Last done" column each time you complete a row — a
checkpoint with a stale date is a checkpoint that didn't happen.

This instance arrived DARK (PR 1, 2026-09-29): `mn/**` is blanket-excluded from the
Pages deploy and `metros.json` carries no `mn` entry, so nothing here is reachable by a
reader yet. Rows marked **GO-LIVE** are what has to happen in the change that publishes it.

---

## Standing (automated — verify, don't perform)

| Cadence | What | Where | You do |
|---|---|---|---|
| Weekly (Mon 13:40 UTC) | U.S. House (MN) roster refresh | `.github/workflows/update-mn-congress-roster.yml` → PR on change | Review + merge the PR; a week with a surprise diff is worth a look at the source |

Only one roster refreshes here, because only one roster ships. The two chamber cards and
the county card name nobody — gaps `mn-legislature-roster`, `mn-county-commissioner-roster`
and `mn-county-officers` in `docs/DATA_LAYER_GUIDEBOOK.md`.

---

## GO-LIVE — what the publishing change has to carry

| What | Why it cannot wait | Last done |
|---|---|---|
| **Iowa's fix (#1267) and Wisconsin's matching one must both be on `main` before this instance is published.** Iowa settled its own dependency in #1267 by having its checks REFUSE `fleet-outlines.json` rather than moving its point, which is the better answer — the point stays where it was measured and the gate stops reading a file that will legitimately change. Iowa also found that **Wisconsin's negative point (47.39, -92.97) is inside Minnesota** and has the same dependency, and Wisconsin fixed it the same way in **#1268**. Check both are merged, and check no instance added after 2026-09-29 has arrived with the same problem, before publishing. #1268 also measured the thing that makes this a pattern rather than three coincidences: sampling Wisconsin's whole `permalink_gate` every 0.25 degrees, **all 609 points land in some state**, and the 300 outside Wisconsin are Michigan 163, Minnesota 76, Iowa 47 and Illinois 14 — three of them live instances today. There is no point to move to, and the Great Lakes are no refuge because Michigan's fabric is water-inclusive. Refusing the fleet file is the answer, not a better point | Either instance's smoke test would fail on the publishing PR, and the symptom — a timeout waiting for a masthead button on a page that has navigated away — names nothing about the cause | — |
| **Iowa's own negative point starts handing off the day this instance is published.** `ia/metro-worksheet.json` pins 43.65, -93.37, which is inside Minnesota; once `mn` is in `fleet-outlines.json` the Iowa app's `placeOwner` will hand that selection to `/mn/` and Iowa's smoke test will find its page navigated away. That is exactly how this instance's own first negative point failed — 43.45, -93.37 in Worth County, Iowa, which passed every static test and made the browser leave. **A negative point must be outside every LIVE instance, not only outside its own.** **SUPERSEDED IN ITS REMEDY, NOT IN ITS LESSON**: Iowa did not move its point, it made its checks refuse the fleet file (#1267). The lesson stands and generalises — every live instance's negative point has to be re-read against a new instance's outline, which is what turned up Wisconsin's | Iowa's smoke test would fail on the publishing PR, and the symptom (a timeout waiting for a masthead button) does not name the cause | — |
| **This instance's own negative point is sound today and rests on North Dakota being unserved.** Cass County, ND is outside every live instance, so `placeOwner` finds no owner and the app selects the point locally — which is why `mn/scripts/smoke_test.mjs` does not refuse `fleet-outlines.json` the way Iowa's and Wisconsin's now do (#1267, #1268). It breaks the day a Dakotas instance ships, silently, as a timeout waiting for a masthead button. Adopting the refusal pattern here would close it by construction and is one `page.route` line; it is NOT done in PR 1, because nothing is broken and widening that PR to pre-empt an instance nobody has planned is the operator's call rather than this thread's | Not a go-live blocker — a Dakotas blocker. Recorded so the next state's thread finds it rather than rediscovering it as a timeout | — |
| Rebuild `fleet-outlines.json` (`scripts/build_fleet_outlines.py`) with Minnesota's outline as a `SOURCES` entry, and add an `mn` row to `metros.json` | The front door and every sibling app route by that file; without it no address in Minnesota reaches this app, and the landing page does not list it | — |
| **The fleet hand-off bbox must be CLIPPED, and this is the Michigan case again.** Minnesota's county fabric runs east to -89.4834 (Cook County's tip on Lake Superior), which contains Wisconsin's own centre (44.9, -89.565) — so an unclipped box fails `validate_index.py`'s "a bbox must not contain a sibling metro's centre" rule on `wi`. Only Cook County reaches east of -89.60; the next county east edge is Lake at -90.7952, so clipping the fleet box costs one county's lakeshore tip in a fallback the apps no longer use for routing | Measured 2026-09-29 on the shipped `mn/data/app/state-counties.json`. `metro_explorers`' own self-entry is exempt from that rule and carries the full extent; the FLEET box in `metros.json` is the one to clip | — |
| Add an `mn` entry to the other six instances' `metro_explorers`, and check each one's new entry does not contain that instance's own centre | A sibling that does not list Minnesota sends a Minnesota address nowhere; one that lists it before the deploy publishes `/mn/` sends a reader to a 404 | — |
| Narrow the `'mn/**'` line in `deploy-pages.yml` to `mn/data/state mn/data/source mn/scripts`, matching `ia` and `mi` | `validate_instance_registration.py` holds the deploy exclude and `metros.json` together in both directions, so this and the `metros.json` row are one change | — |

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

| What | Why it is here | Last done |
|---|---|---|
| **The Secretary of State's precinct layer is this instance's whole growth path and it is ONE service.** `enterprise.gisdata.mn.gov` → `us_mn_state_sos/bdry_votingdistricts/FeatureServer/0`, 4,105 precincts, `maxRecordCount` 2000 so it pages. Seven layers dissolve out of its own attributes: `ctycomdist` (447 county commissioner districts, all 87 counties), `pctcode` (precincts), `juddist` (10 judicial), `swcdist_n` (117 soil & water), `hospdist_n` (16 hospital), `parkdist_n` (3 park) and `ward` (274 wards in 76 cities). **A single upstream service is a single point of failure for seven layers**, so watch its `Service Modified` stamp (2026-09-17 when measured) and re-check the seven field names, not just the endpoint | Measured 2026-09-29. `gis.data.mn.gov`'s robots.txt allows this client with **Crawl-delay: 60** binding on `*` — honoured, and it makes a full page-through slow rather than impossible. The separate `www.mngeo.state.mn.us` serves a Radware Bot Manager captcha to this project's token: obeyed, never worked around, and it costs nothing because the data is on the enterprise host. **Do not let a later pass read "MnGeo is blocked" as "Minnesota publishes nothing"** — that is the Knox shape | 2026-09-29 |
| **The commissioner ROSTER route is unproven, not closed, and the difference is one measurement.** The SoS's companion results service `bdry_electionresults_2022_2030` carries federal and state contests only — no commissioner column — so composing a roster out of certified returns is shut there. Its `LocalRacesInCounty` pages were read for ONE county at ONE election id with no commissioner contest found, which is one reading and not a finding. If those pages carry commissioner contests, all 447 seats come from one publisher; if they do not, this is the Michigan shape — 87 counties in tranches off their own board pages | This is the next research question for this instance, and it decides whether the flagship layer ships with names or without | 2026-09-29 (one county, one election id) |
| **A negative point must be outside every live instance.** See the GO-LIVE row above. The two points tried before Cass County, North Dakota are recorded in full in `mn/metro-worksheet.json`'s `negative_point.note`, including why Lake Superior does not work: Minnesota's TIGER county fabric is water-inclusive to the international boundary, so a point in open lake at 47.6, -90.0 is named `Lk Superior` by TIGERweb's hydrography **and is still inside Cook County** | Both failures looked obvious and both were caught by measurement rather than reasoning | 2026-09-29 |

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
