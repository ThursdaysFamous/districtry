# districtry Michigan — the expansion plan and its running record

> **SHIPPED 2026-09-03 — phases 1, 2 and go-live, in three PRs on one day.** Michigan is live at
> districtry.com/mi/ with 15 layers. **The running status is the Status table near the foot of this
> file; what is left is under Still open.** What go-live actually cost is recorded here because it
> was almost entirely NOT on any checklist.
> **Four defects had survived the full 38-gate battery twice, and three were the same shape — a
> claim nothing compared against the thing it claimed.** (1) `mi/fonts/` did not exist while
> `mi/index.html` declared 18 `@font-face` rules against it, and `mi/og-image.png` did not exist
> while three tags named it: the app would have served in system fonts forever and every social
> share would have been broken, with no error anywhere. `scripts/validate_instance_assets.py` is
> the new gate, and it had to be fixed mid-write — its first draft scanned `src`/`href` only,
> caught the fonts, and sailed straight past the og-image, which lives in a `content=` attribute.
> (2) `mi/sources.html` served **Iowa's entire identity block** — canonical, `og:url`,
> `og:site_name`, title and the whole ld+json graph — because the page was cloned from Iowa and
> only its GENERATED regions were ever regenerated; a canonical pointing at a sibling asks Google
> to drop this page in favour of that one. `page_consistency_test.mjs` passed it, because its check
> was `!!document.querySelector("link[rel=canonical]")` — whether the tag was THERE, never what it
> SAID. (3) A dead `tigerStatewideLoader`, inherited from Iowa and never called, made
> `build_privacy_page.py` publish that a Michigan layer sends your exact selected point to a
> government server, when none does. (4) **The fleet bbox is the portal hand-off box, not
> `metro_bbox`**: Michigan's water-inclusive fabric put Chicago's and Wisconsin's own centres inside
> Michigan's box and hard-failed `validate_index.py` on both — found only because the per-instance
> `validate_index` block had been skipped in favour of a remembered subset of the battery. **Run the
> workflow's own command list.** The western-UP counties that fall outside the narrowed box are
> recorded in `mi/WATCH.md`. **That record named a fix and the fix was wrong**: a smallest-bbox-AREA
> tie-break measures no better than the nearest-CENTRE rule it would replace (7 wrong of 37 either
> way, just at different places). #698 routed the front door against each instance's real coverage
> ring instead — 7 misroutes of 28 down to 4 — and four counties remain, for a reason that is not a
> tie-break at all.
>
> Two things go-live did NOT need, contrary to the guide: no sibling `CACHE_NAME` bump (the sibling
> change is confined to the network-first shell), and this file does not move to `docs/archive/` —
> neither Iowa's nor Wisconsin's plan did.

> Planning document, researched and verified 2026-09-03. `docs/IA_EXPANSION_PLAN.md` is the
> precedent for a committed phase plan; like it, this file STAYS IN `docs/` and is APPENDED TO
> when a phase ships (the header used to say it moves to `docs/archive/`; git says otherwise —
> Iowa's go-live commit 258022d appended 43 lines to `docs/IA_EXPANSION_PLAN.md` and renamed
> nothing, and the only archived plan, `docs/archive/WI_PHASE2_PLAN.md`, closed a PHASE rather
> than a go-live). The shipped instance (`mi/metro-worksheet.json`, `mi/CLAUDE.md`, the
> guidebook's Michigan column) supersedes it as the record of what IS; this stays the record of
> what was decided and why. Sources marked **VERIFIED** were fetched or queried on
> 2026-09-03 — endpoint, count, licence and failure mode recorded from the response, not from a
> catalog page. Facts marked **ASSERTED** are Michigan civic-structure claims carried from the
> research pass without a second independent fetch; each must be pinned to a primary citation in
> the PR that ships it, per `docs/EXPANSION_GUIDE.md`'s honesty rules.

## Why Michigan, and why now

The fleet was five instances when this was written on 2026-09-03 (Michigan made it six the same day): Illinois (91 counties, the reference
implementation), NYC, SF, Wisconsin (all 72 counties) and Iowa (all 99). Michigan was chosen as
the sixth from a five-state recon pass across the states bordering the existing
Illinois/Wisconsin/Iowa footprint, scored on one question: **does a single statewide publisher
carry county-board-district boundaries for every county?** That is the trait that made Wisconsin
and Iowa fast builds and whose absence made Illinois a county-by-county grind of 91 separate
research problems.

| Candidate | Verdict | The measurement |
|---|---|---|
| **Michigan** | **GREEN** | One state-owned layer, **83/83 counties in a single query** |
| Indiana | YELLOW | IGIO's Data Harvest is real but voluntary — **65/92 counties** across two vintages; the rest would be Illinois-shaped work |
| Nebraska | YELLOW | NebraskaMap hosts county-board layers **owned per county**, not one aggregate |
| Minnesota | RED | The Secretary of State states outright it has no commissioner-district maps online; MnGeo's statewide catalog carries none either; the shapefile page is bot-gated |
| Missouri | RED | No statewide aggregate; county government genuinely fragmented (valuation classes + a township-organization overlay in ~20 of 114); the SOS **sells** precinct results |

## The thesis: Michigan arrives with Wisconsin's shape, not Iowa's or Illinois's

Wisconsin's arrival keyed on one state-publisher layer, shippable because Wis. Stat.
5.15(4)(br) forces every county to file its district plan with the state. **Michigan has the
same shape and the same reason.** MCL 46.404/46.405 (ASSERTED — to be pinned in the PR that
ships the layer) requires each county's apportionment commission to file its adopted plan, and
the Department of State's Bureau of Elections compiles those filings into
**`2021 County Commissioner Districts v25`** —
`gisagocss.state.mi.us/arcgis/rest/services/OpenData/boundaries/MapServer/10`, **VERIFIED: all
83 county names returned by a single distinct-values query**, fields `CountyFIPS, County,
DistrictCode, DistrictName, Population, Commissioner, Party`.

Three things separate it from Iowa's flagship, and all three are in its favour:

- **The licence is stated, not merely absent.** Iowa's supervisor layer carries a null
  `licenseInfo` and an attribution-only posture inferred from silence. Michigan's AGO item
  (`4c8d0d854ac04d8787cb3cf6dab7fbec`) states it outright — **VERIFIED, verbatim**: "this
  dataset is a public record and…there are no restrictions on the use, reproduction, or
  distribution of this dataset". Note the Hub *site* item separately carries a site-wide
  `CC-BY-SA`; the dataset's own custom licence is what governs, and the two must not be
  conflated.
- **It carries people, not just polygons.** `Commissioner` and `Party` are **VERIFIED
  populated** on sampled records ("Jonathan Turnbull"/"Republican"), derived per the item's own
  description from the canvassed November 2024 election.
- **No known staleness bomb.** Iowa's shipped layer predated Senate File 75 and needed a
  three-county reconciliation before it could ship. Nothing equivalent surfaced for Michigan;
  county apportionment runs on the census cycle.

**NONE OF THAT SHIPS IN PHASE 1, DELIBERATELY.** A roster attached to a boundary is refreshed
when the boundary is — this repo's own Des Moines finding — so those names get their own
verification pass and their own change rather than riding in on the geometry's coat-tails. The
`county` card ships identity-only and *says on the card* that it does not name commissioners.

## Scope decisions

- **Phase 1 is the national tier only, exactly the WI/IA shape.** Four layers: `county`,
  `us-house`, `mi-senate`, `mi-house`. Every one is TIGERweb geometry plus a roster from a
  publisher already trusted fleet-wide.
- **The instance arrives DARK.** No `metros.json` entry, no `--sync-fleet`, no
  `build_coverage_map.py` row, and one blanket `mi/**` line in the deploy's EXCLUDES — the Iowa
  PR 0 posture, for the reason Iowa measured: a manifest entry renders a live landing card the
  day it lands, and for an excluded folder that card is a 404. CI runs against `mi/` from this
  PR forward all the same.
- **`sources_page` and `history_page` are set from this PR**, not backfilled (Wisconsin's
  `history_page` arrived three phases late and had to be written from git history).
- **No county-officer roster, no precinct layer, no school tier in phase 1** — each is a later
  change with its own verification, and each is a stated absence rather than a silent one.

## What phase 1 shipped, and what it measured

| Layer | Count | Boundary | Roster |
|---|---|---|---|
| `us-house` | 13 | TIGERweb Legislative/0 (**CD120**) | congress-legislators (CC0), 13/13 with a district office |
| `mi-senate` | 38 | TIGERweb Legislative/1 (SLDU) | Open States `mi.csv` + the Senate's own directory — **38/38 with a Capitol office** |
| `mi-house` | 110 | TIGERweb Legislative/2 (SLDL) | Open States `mi.csv` — 110/110 with e-mail, **no capitol office block** (below) |
| `county` | 83 | TIGERweb State_County/1 | none — identity only, stated on the card |

All four boundary builds passed the 2,000-random-point agreement gate at **100.00% with 0
overlaps**. Ground truth: the Michigan State Capitol (42.7337, -84.5553) → Ingham County, U.S.
House 7, Senate 21, House 77 — **VERIFIED against the shipped geometry, not assumed**. The
negative point is downtown Toledo, Ohio, measured to miss all four layers.

### Three findings worth carrying forward

**1. TIGERweb's congressional layer has rolled to the 120th Congress, and the old field is
GONE.** The layer is now named "120th Congressional Districts" and its district field is
`CD120`. A query naming the retired `CD119` does not return an empty set — it is **rejected with
HTTP 400, "Failed to execute query"** (VERIFIED; it is what made this instance's first
congressional build fail). Michigan's builder names `CD120`. **The sibling instances' builders
still name `CD119` and would fail identically on a rebuild** — their shipped files are fine, so
this is a latent break rather than a live one, but it is real and belongs to whoever next
rebuilds a congressional boundary in `il/`, `wi/` or `ia/`. It is deliberately not fixed here:
this PR does not touch sibling instances.

**2. Michigan's county fabric is WATER-INCLUSIVE, and the coverage ring is one polygon because
of it.** Every Great Lakes county's TIGERweb polygon runs out to the state water boundary —
Keweenaw County alone spans **2.57° of longitude**, from the Keweenaw Peninsula out past Isle
Royale — so both peninsulas and every island tile continuously and the dissolve yields **ONE
ring, 1,716 vertices** (VERIFIED via `--check`). Mid-Lake Michigan, mid-Lake Huron and the
Mackinac Straits all measure *inside* coverage; Toledo, Chicago and Toronto all measure outside.
That is correct — the water genuinely is assigned to Michigan counties — and it is why the
negative point had to be a point on land in another state. **The first draft of the outline
builder's own docstring asserted "several rings, two peninsulas plus islands" before the build
was run, and was wrong**: the same error this repo keeps re-learning in Illinois. Read the ring
count from `--check`, never from a map in your head.

**3. The Michigan House site could not be reached, and what that does and does not mean.**
Open States carries **no capitol phone or address for any Michigan legislator** (VERIFIED, 0 of
148 rows), so every contact detail must come from the chambers. The Senate's own all-senators
directory supplies phone, e-mail, office and contact page for all 38 seats — **but the parse is
not the obvious one**: the roster is an HTML-escaped `senatorInfo` attribute feeding a Lit
component, not a `var senatorInfo = [...]` assignment, and a parser written against the obvious
shape returns nothing from a page that plainly contains the data. (A research pass reported the
data's existence correctly and its shape incorrectly; the scraper was written against the page,
not the report.) `house.mi.gov`, meanwhile, fails TLS from this build environment with "unable
to get local issuer certificate" **even with the egress proxy's CA bundle explicitly supplied**,
while `senate.michigan.gov` answers 200 on identical flags and the proxy records no relay
failure. That is the incomplete-chain shape this repo documents for Coles, Gallatin and
Vermilion — **but TLS is re-terminated at the sandbox proxy, so this environment cannot observe
the site's real chain at all.** A measurement is not a conclusion (`docs/EXPANSION_GUIDE.md`
§0.4): it is recorded as unresolved in `mi/WATCH.md`, owing **one CI-side probe**, and the House
card ships without an office block rather than claiming one it cannot source.

## One gate changed, and why

`scripts/validate_instance_registration.py` required every instance in the tree to appear in
`metros.json`. That is right for a published instance and wrong for a dark one, and it collided
head-on with the arrival posture the same repo documents: Iowa's PR 0 measured that a
`metros.json` entry renders a live landing card immediately, so listing a deploy-excluded folder
publishes a 404. The gate now reads the deploy's own EXCLUDES to tell the two apart and checks
the biconditional — **listed if and only if published** — which is strictly stronger than what
it checked before: it now catches the 404 case as well as the invisible-instance case. Verified
in both directions (a dark `mi` passes; `mi` added to `metros.json` while still excluded fails
with the reason).

## Status

| | Shipped | What it cost, measured |
|---|---|---|
| **Phase 1 — the national tier** | 2026-09-03 (#685) | 4 layers: `county` 83, `us-house` 13, `mi-senate` 38, `mi-house` 110. All three boundary builds at 100.00% agreement, 0 overlaps. Found the CD119→**CD120** roll, which had broken nothing yet and would have broken the next rebuild in all five sibling instances |
| **Phase 2 — the flagship** | 2026-09-03 (#691) | `county-commissioner`, 619 districts across all 83 counties, GEOMETRY ONLY. The layer's own `Commissioner`/`Party` columns were measured against twelve counties' board pages (123 districts) and **dropped**: 93.5% right, every miss the same direction, and Wayne D5 still naming a commissioner who died in June 2025. A winners list is complete by construction, so its 100% fill rate is evidence AGAINST maintenance |
| **Go-live** | 2026-09-03 (#694) | Michigan published at districtry.com/mi/. Four defects surfaced that the full battery had been green on — missing fonts and OG image, Iowa's identity block on the sources page, a dead helper that made the privacy page overstate what the app sends, and a fleet bbox containing two siblings' centres. Two new gates (`validate_instance_assets.py`, and identity checks in `page_consistency_test.mjs`) |
| **Routing follow-up** | 2026-09-04 (#698) | Front-door routing moved off bbox tie-breaks onto each instance's own coverage ring: 7 misroutes of 28 real places down to 4. Also corrected three records that had named smallest-bbox-AREA as the fix — measured, it is no better than the rule it would replace |

**Phase 1's own "what shipped" section above is left exactly as written on the day.** It is the
record of what was true then, not a status board; this table is the status board.

## Still open

Each opens its own refreshed plan PR with its own measured ledger when it begins.

- ~~**Phase 3 — the fabric.**~~ **DONE, in two PRs (2026-09-04).** PR 1 shipped the four live
  TIGERweb layers — `county-subdivision`, `municipality` and the two school tilings — and PR 2 the
  precinct layer. Three things it settled that this entry got wrong or left open:
  - **The charter-township claim needed no citation.** It is readable straight off TIGER's own
    `NAME` suffix, 1,581 records of 1,581 (1,122 general-law, 118 charter), so the card's type row
    can never disagree with the name printed above it.
  - **The city/village distinction is the one that mattered, and this entry did not name it.** A
    Michigan city is independent of any township; a VILLAGE remains part of one — measured across
    all 252 villages at their interior points, zero exceptions — so a village resident has two
    general-purpose local governments and each card names the other.
  - **The precinct layer nearly shipped the wrong vintage.** The MapServer carrying the
    commissioner flagship stops at 2024; the 2026 map is on the state's AGO org, on another host,
    and Michigan consolidated 4,340 precincts into 3,895 between the cycles. What caught it was
    this repo's own guidebook cell, which had recorded the 2026 layer weeks earlier and never been
    acted on.
- **The amenity tier.** `zip-code` shipped 2026-09-04 as the 11th layer. Next are the USGS
  National Map point layers, all three verified present in Michigan's envelope that day — post
  offices 1,799 (structures layer 38), police 1,290 (layer 53), fire/EMS 2,838 (layer 51) — the
  same national source every sibling instance already uses.
- **Phase 4 — the city tiers.** DETROIT SHIPPED 2026-09-05 as the 15th layer: seven council
  districts from the city's own ArcGIS org, geometry only. Three of the city's services compete and
  their NAMES do not settle which is in force — one titled "Current" (live since 2016), one named
  2026, and one named 2013 that was CREATED in December 2025 — so the builder decides it by
  MEASUREMENT and gates it in both directions: "Current" must carry geometry identical to what
  ships, the 2013 archive must differ, the shipped plan must balance on Census 2020 (4.28% worst
  deviation) and the archive must not (13.51%, which is a plan drawn on 2010 seen from 2020). The
  seven districts sum to 639,111 — Detroit's Census 2020 population exactly — which is both the
  tiling proof and the reason `coverage` is the layer's own tiling with no separate city outline.
  THE ROSTER SHIPPED THE SAME DAY, ON REVIEW, AND THE FIX IS THE LESSON. The layer first shipped
  naming NOBODY, on a finding that five routes to the membership were shut. Two of the five were
  wrong. `data.detroitmi.gov` was recorded as challenged when it answers **HTTP 200 with a readable
  robots.txt** — a verdict reached by grepping a 68 KB page for the word "challenge" and finding
  one hit WHILE THE STATUS CODE SAID 200. And the fleet's OWN terminal fetch rung, the Internet
  Archive, in weekly use for Kendall and McHenry since 2026-07, was never attempted; it answers
  with all nine members, their districts and their roles. **A ROUTE NOT WALKED IS NOT A ROUTE
  MEASURED**, and five routes were claimed shut with four examined. So all nine ship — seven on the
  polygons, two at large in a `citywide` block (the Des Moines shape) — with the card printing which
  day's archived copy it read and the scraper refusing one over 45 days old. What survived
  measurement is narrower and holds: detroitmi.gov and mvic.sos.state.mi.us DO carry a genuine
  Cloudflare managed challenge on the plain AND the client-hints rung, so there is deliberately no
  headless rung here; and Legistar was abandoned in 2017 and never carried a district in
  OfficeRecordTitle where Milwaukee's does — test a vendor by content per city. The remaining gap is
  `detroit-council-contact`: no phone and no e-mail anywhere on either city surface, measured.
  Three further corrections came out of the same review — the org holds **1,512 items (795 feature
  services)**, not 225; the plan's own dates (adopted 2024-02-06, effective 2026-01-01) were sitting
  in the shipped service's `description` and were never cited; and `SIMPLIFY` at 8% moved D5's
  boundary 135 m, against a city tier that simplifies at 20-25%. All three are fixed.
  **GRAND RAPIDS SHIPPED 2026-09-05 AS THE SECOND CITY, AND CONVERTED THE CONCEPT.** §3.0 says a
  concept appearing in a second city becomes a DISPATCHED concept, so `detroit-council` became
  `city-ward` with two municipality-keyed entries, an alias shim for every permalink already shared,
  and `registerCountyLayer` ported in from Iowa — a third copy of shared code, recorded as a debt in
  `mi/WATCH.md` rather than promoted to `engine/` inside a PR about a city. No shared entry helper:
  Iowa's two cities are near-identical and Michigan's are not, and the dispatcher already lets each
  entry bring its own card.
  **THE CITY'S SHAPE CAME FROM THE CITY, NOT FROM MEMORY**: "This legislative body consists of the
  Mayor and six Commissioners… The residents of each Ward directly elect two commissioners." Two per
  ward ride the polygons; the mayor rides a citywide block.
  **THE REAL QUESTION WAS AGE.** The ward geometry was last edited **2018-01-24** — before the census
  it balances on — while its own description claims it is "maintained to reflect the most current
  adopted ward configuration". A description is a claim. Michigan's OWN 2026 precinct layer carries a
  WARD column assigning the city's 59 precincts 20/20/19, and dissolved by it, it agrees with the
  city's polygons on **99.575%** of 4,000 points: two independent publishers, one edited in 2018 and
  one built for the 2026 cycle, drawing the same three lines. So 2018 means UNCHANGED, and that
  agreement is a gate rather than a note. Balance is 3.60% worst on Census 2020.
  **THE POPULATION IDENTITY IS NOT EXACT AND IS NOT CLAIMED TO BE** — unlike Detroit's, which sums to
  its census count exactly. Twenty-one of 2,883 blocks fall on one side of the ward outline and the
  other side of the Census place outline (+66 against 198,917): two digitisations of one municipal
  edge. The builder bounds that rather than asserting zero, because pretending otherwise would have
  been the more comfortable lie.
  **SIX OF SEVEN SEATS SHIP, AND THE SEVENTH IS A STATED VACANCY.** The city publishes one Ward 1
  commissioner where Wards 2 and 3 have two, so the roster carries `seats` and the card accounts
  for the seventh — the Alexander machinery, used for the first time on a districted body. This
  PR first said "no vacancy stated anywhere", **on a measurement of one page**. The city's own news
  post of 2026-04-17 states the vacancy "was created following the resignation of former
  Commissioner Drew Robbins", and a 2026-03-31 post names ten applicants advancing. ONE PAGE IS NOT
  THE CITY — the same error that once called Detroit's open-data portal blocked. The card now names
  the vacancy and its cause, and deliberately says nothing about how it was resolved, because no
  city source found on 2026-09-05 does.
  **THE CAUSE WAS A STRING LITERAL IN THE CARD AND IS NOW DATA, WHICH IS THE THIRD OF THIS PR'S OWN
  CLAIMS TO BE WRONG.** That literal named Ward 1's predecessor on a row that fires for ANY ward the
  city names short of its seats, so a later Ward 2 or 3 vacancy would have rendered his name on the
  wrong card. The scraper now fetches and verifies the cause per ward from the city's own post, the
  builder refuses a vacancy for a ward the city fully seats or one with no on-site source, and the
  card renders the sentence — and a link to that post — from the roster, falling back to the
  neutral "not listed there" wording for a short ward with no verified cause. Nothing in CI had ever
  selected a point in either city, because the instance's anchor is in Lansing where `city-ward`
  hides; the smoke test now carries ten checks that do (eight `check(` call sites, six of them
  inside a loop over two wards). One of the ten is the only scenario that catches the ward-agnostic
  shape: a STUBBED roster that makes a FULL ward short, since under the broken code every check
  against the live roster still passes.
  A related trap avoided by construction: the departed
  commissioner's own page still answers 200 and is still in the sitemap, so a scraper walking
  sitemap entries would ship him as sitting. Each
  member's own page gives ward, e-mail and direct phone. Three traps recorded: the e-mail domain is
  `grcity.us` and NOT the website's, so a hostname-keyed scraper finds none; the listing's role
  labels sit beside an anchor that is not their own (the Franklin grid trap, which put Ward 1 on a
  Ward 3 member until the member pages contradicted it); and 616.456.3000 is on every page and is the
  switchboard, detected as the number common to all rather than hardcoded.
  **TWO MORE OF THIS PR'S OWN CLAIMS WERE WRONG AND ARE CORRECTED.** "The city publishes two ward
  services" came from a search capped at the first 100 of the org's 681 — swept in full there are
  EIGHT, of which three are byte-identical to what ships, one differs only at the perimeter and
  three are single-ward layers agreeing with their own ward. No newer plan exists, so the currency
  finding stands and only the count was wrong. And the shipped map disclaimer was an author-composed
  paraphrase while the docstring called it verbatim; the card now quotes the city's Data Access and
  Use Constraint Agreement in its own words, which is what the Des Moines precedent it cited
  actually does.
  **SIMPLIFICATION IS 50%, AND COPYING THE SIBLINGS' 20-25% WOULD HAVE BEEN WRONG**: mapshaper's
  percentage is a share of the SOURCE vertex count, so on a three-feature layer 20% leaves too little
  to describe the line and agreement falls to 98.95%, below the fleet's floor. The floor was never
  the thing to move.
  **AND A LATENT ENGINE BUG SURFACED**: `findPropCI` lowercases the property KEY and compares it
  against the candidate as given, so candidates must be lowercase. `["Ward", "WARD"]` could never
  match and rendered "Unknown ward" on a card whose feature plainly carried Ward; Detroit's
  `["District", "district_number"]` had been working only through its second, already-lowercase
  candidate. Both fixed, the contract recorded at the helper, and every call site in the file
  audited.
  **NEXT: no third Michigan city has been researched.** Lansing, Ann Arbor and Sterling Heights are
  the obvious candidates by population; none has been checked for a published boundary.
- **The 619 commissioners** — gap `mi-commissioner-roster`. The honest route is county-by-county
  against each board's own page, weekly and count-guarded; ten of the twelve counties sampled
  publish a readable one. Oakland answers only through its CMS origin and Ottawa sits behind a
  captcha, which this project does not route around.
- **Michigan's full fleet bbox**, and with it the last four misroutes (Ironwood, Houghton, Iron
  Mountain, Menominee). Needs `validate_index`'s "a bbox must not contain a sibling's centre"
  rule relaxed AND the in-app `metro-portal` moved onto the same ring test — its `siblingMetroAt`
  runs on `moveend`, so it needs the same pre-filter discipline and must never let a fetch block
  a pan. `mi/WATCH.md` carries the measurement; the ceiling is 0 misroutes.
- **One CI-side probe of `house.mi.gov`**, to settle whether its TLS failure is the site's own
  incomplete chain or an artifact of the build sandbox. Until then the House card ships without
  the Capitol contact block the Senate card has, rather than claiming one it cannot source.

## Conventions binding every PR

Scripts `mi/scripts/build_mi_*.py` / `mi_*_scraper.py`; workflows
`.github/workflows/update-mi-*.yml`, **every one `mi`-prefixed with no exceptions** — Wisconsin's
unprefixed workflows collided with the pre-consolidation Illinois naming and neither Iowa nor
Michigan repeats it. `BOT_PR_TOKEN`, fixed `bot/mi-*` branch, PR-never-push. Every layer gets a
worksheet `source` block (the generator refuses otherwise), a `LAYER_SIDEBAR_RANK` slot, a
`validate_sources.py` row, a `WATCH.md` row, and guidebook coverage-map + matrix updates in the
same change. GENERATED regions and ENGINE fences are never hand-edited — all module code is
instance-side, between the `chamber-factory` and `hover-explorer` fences. Scraped strings render
through `sanitize()`/`textContent`. The officeholder story ships with each boundary — a roster,
or a recorded gap, never silence. `min_register_layer` only rises. Files inside `mi/data/app/`
are named `mi-*`, never `michigan-*`.

---

## Phase 5 — the next three cities, measured (2026-09-05)

**Nothing shipped, and that is the finding.** Michigan stays at 15 layers and `city-ward`
keeps its two entries. Three gap records carry the measurement: `lansing-ward-boundary`,
`annarbor-ward-boundary`, `sterling-heights-council-form`.

**LANSING is build-ready on every axis except terms.** Its `VotingWards` service is exactly
four features, WARDID 1-4, and dissolved against the state's own 2026 precinct WARD column
(27 precincts, 7/7/6/7) it agrees on **99.893%** of sampled points — tighter than Grand
Rapids shipped at. The blocker is that the city publishes the same plan three times and the
one that states terms says **CC BY-NC 4.0**. The clean four-feature copy states nothing,
and **an unstated licence is silence, not a grant**: the same publisher states NonCommercial
terms on the same plan one item away, so taking the copy without the notice would be choosing
the reading that suits us. `mi/scripts/build_mi_lansing_wards.py` runs every gate, re-reads
the licence clause live each run, and **refuses to write** without `--licence-approved` —
"build it dark" is not enough in a public repository, where committing the derived file
would itself distribute the data.

**ANN ARBOR'S OBVIOUS CANDIDATES ARE ALL WRONG, EACH DIFFERENTLY**, and the city's own
publisher was not reached. `Wards and Precincts` is readable and **superseded** (47 features
against the state's current 41; per ward 9/8/9/10/11 against 9/6/8/8/10) — the Vermilion
shape. `City Council Districts` in the same org is **Los Angeles**, by its own service
description. That org also serves NYDOT labels and the NYC borough fabric, so it is not
Ann Arbor's publisher at all. The city's own portal answers and is a JavaScript application;
`gis.a2gov.org` fails at this environment's egress proxy, which says nothing about the host.
**Not measured shut** — two routes remain.

**STERLING HEIGHTS MAY NOT BE A `city-ward` CITY AT ALL.** Four signals point at an at-large
council, the sharpest being that the state's 2026 precinct fabric assigns `WARD='00'` to all
40 of its precincts where Grand Rapids reads 01-03, Lansing 01-04 and Ann Arbor 01-05. None
is the city or county saying so, so nothing is claimed: **an absence in one publisher's column
is a fact about that publisher.** Both witness routes were tried and are named in the record —
the city's own charter link serves a water-billing portal, Municode needs a browser, and
Clarity carries the Macomb slot but publishes an **empty election list**.

**THREE NAME TRAPS IN ONE PASS**, all caught by testing content rather than title:
`Lansing Ward Boundaries` is owned by `lansingks.org` — Lansing, **Kansas**; Ann Arbor's
`City Council Districts` is Los Angeles; and Ann Arbor's correctly-named ward layer is the
obsolete plan. **The catalogue tells you what a thing is called; only the content tells you
what it is.**

---

## Phase 5 continued — 23 more cities settled in one query (2026-09-06)

**The method's first test is now the cheapest thing in the pipeline, and it scales.** One
query against the state's own 2026 precinct fabric, filtered to 23 jurisdictions at once,
settles the only question that decides whether a city is a `city-ward` candidate at all:
does the state record a WARD for its precincts?

**TEN ARE DISTRICTED** and are candidates: Wyoming (3 wards), Rochester Hills (4),
Pontiac (6), Kentwood (2), Battle Creek (5), Midland (5), Muskegon (4), Jackson (6),
Bay City (9), Holland (6).

**THIRTEEN CARRY `WARD='00'` ON EVERY PRECINCT** — the Sterling Heights and Dearborn shape:
Livonia, Troy, Westland, Farmington Hills, Southfield, Kalamazoo, Novi, Dearborn Heights,
Taylor, Royal Oak, Saginaw, Portage, East Lansing.

**THOSE THIRTEEN GET NO PANEL GAP RECORD, AND THAT IS A STRUCTURAL ARGUMENT RATHER THAN
A SHORTCUT.** A gap record answers "what won't show on my card, and why". An at-large
council has no district for the card to name, so there is no absence in a district layer
to explain — the same reason this project gives an at-large county board roster rows on
its identity card and never a polygon. Sterling Heights and Dearborn carry records because
each is a very large city where a reader might reasonably expect a ward and where the
at-large reading is INFERRED from one publisher's column rather than confirmed; thirteen
more near-identical entries would flood the panel without telling a reader anything the
first two do not. The measurement lives here instead, where the next pass will look.

**WYOMING, THE LARGEST DISTRICTED CANDIDATE, IS THE FIRST CITY IN THE FLEET WHOSE
robots.txt NAMES CLAUDE AND SAYS NO** — `User-agent: ClaudeBot` / `Disallow: /` over the
whole site, with `Content-Signal: ai-train=no`, and every precinct map under a `/Portals/`
path disallowed to `*` as well. A browser user-agent would fetch those files; using one to
step around a rule written at Claude by name is exactly what this project does not do. The
state route is open — the state's own fabric would dissolve to 6/6/6 across three wards
without touching the city at all — but making the state the SOURCE rather than the
independent currency CHECK is a posture change, so it is recorded and left to the operator.
See gap `wyoming-mi-ward-boundary`.

