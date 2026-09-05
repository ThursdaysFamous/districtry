# State Expansion Guide — the primary guide for growing districtry

Status: **live — the single entry point for growing the fleet.** Owner: this repo (there
are no forks to point at any more).

**This is a rewrite, and the reframing is the point.** The previous edition was a *metro*
expansion guide: its central path was "port the app to another city as a separate repo and
site", and Illinois's county growth was a special case bolted beside it. Both halves of
that framing are now wrong. The fleet consolidated into ONE repo where every instance is a
folder served at its own path (R2.3, `docs/DEV_PROCESS_ASSESSMENT.md`), the per-metro forks
and the engine release channel are retired, and — decisively — **the two deepest instances
grew as STATES, not as cities.** Illinois reached 91 counties from a Chicago starting
point; Wisconsin was built statewide from day one and grew city tiers downward. The unit of
expansion is the state instance, so this guide is organized around it.

Everything specific and dated — which county taught what, which publisher refused what —
lives in `docs/DATA_LAYER_GUIDEBOOK.md` and the per-instance `CLAUDE.md`. **This guide holds
the rules; the guidebook holds the record.** When they disagree, the guidebook is what was
measured and this document is what somebody concluded.

Consolidated 2026-07-27 from five docs (`METRO_EXPANSION_PLAYBOOK.md`,
`STATEWIDE_EXPANSION_PLAYBOOK.md`, `COUNTY_LAYER_CONSOLIDATION.md`,
`MUNICIPAL_COUNCILS_PLAYBOOK.md`, `ILLINOIS_LAYER_STANDARDIZATION.md`), preserved verbatim
under `docs/archive/`; rewritten around the state unit 2026-08-27 after Wisconsin's fourth
phase, folding in the lessons of both deep instances.

---

## 0. Orientation

### 0.1 What a state instance is

An instance is a **folder at the repo root named for its URL path**, serving at
`districtry.com/<tag>/`. It owns its app, its data, its scripts, its worksheet and its
operations calendar; it shares the engine, the fleet machinery and the docs.

```
<tag>/                     il/ ny/ ca/ wi/  — the tag is the URL segment
  index.html               the whole app: styles, engine fences, layer modules
  sw.js                    service worker; SHELL + GEOMETRY (cache-first) + ROSTER (network-first)
  sources.html  faq.html   generated sub-pages
  history.html             generated, opt-in (worksheet `history_page`)
  metro-worksheet.json     every per-instance fact, ONCE — drives all GENERATED regions
  data/app/*.json          runtime-fetched boundary + roster files
  data/source/             build inputs; EXCLUDED from the Pages deploy
  scripts/                 this instance's builders, scrapers, validate_index, smoke_test
  WATCH.md                 the instance's operations calendar
  CLAUDE.md                the instance's own agent brief
```

Repo root holds what is genuinely fleet-level: the landing page and `privacy.html` (both
generated), `metros.json` (the fleet manifest), `engine/` (the single copy of the engine),
`scripts/` (fleet tooling **and** Illinois's own), `docs/`, and the CI workflows.

**One asymmetry to know before you copy anything.** Illinois is the reference instance and
still runs out of the ROOT — root `metro-worksheet.json` is Chicago's, root `scripts/` holds
both fleet tooling and Illinois's 260-odd builders, and there is no `il/scripts/`. NY, CA and
WI each own `<tag>/scripts/` and `<tag>/metro-worksheet.json`. **A new state follows the WI
shape, not the IL one.** `scripts/validate_workflow_deps.py` enforces it: an instance script
must resolve its imports inside its own tree, so a `sys.path` insert reaching into another
instance fails CI. When you need shared machinery, the instance carries its own copy or the
helper moves to the root — never a cross-instance reach.

### 0.2 The two arrival shapes — decide yours before the first layer

The fleet has built states both ways, and the choice changes the roster, the coverage
bands, and what "done" means.

| | **Statewide-first** (Wisconsin) | **Metro-first** (Illinois, NYC, SF) |
|---|---|---|
| Day one | every layer a statewide publisher answers for | one city's full civic stack |
| Growth | *downward* into city tiers (Milwaukee, then Madison) | *outward* county by county |
| Coverage bands | usually two — in-state / outside; three where full coverage is a proper subset of a region whose layers still answer (Wisconsin, per §2.5.1's measured table) | three for Illinois; two for a city instance (NYC, SF) — §2.5.1's table is what was measured |
| Layers a metro can't have | PSAP + NG911 service areas, statewide court tiers, technical-college districts | — |
| Layers a state can't cheaply have | neighborhood fabrics, city police beats, ward-level polling | — |
| Risk | thin cards everywhere; identity-only layers dominate | a wash that greys out territory you came to serve |
| Fastest to a useful app | yes — national publishers tile a whole state on day one | no — the depth is the point |

**Prefer statewide-first for a new state.** Wisconsin reached twelve honest layers in a day
from national and state publishers, then earned depth where publishers existed; Illinois
spent its first year as one city and is still filling counties. Statewide-first also gets
the coverage question right by construction: the instance answers everywhere in the state
from the start, so there is no shrinking wash to maintain.

The one thing statewide-first must not do is **fake depth**. A statewide instance whose
county cards name nobody is honest; a statewide instance that invents a county board roster
is not. Depth arrives per county, on evidence, exactly as in Part 3.

### 0.3 The paths

| Path | You are… | Part |
|---|---|---|
| **A — a new state instance** | standing up `<tag>/` for a state the fleet does not serve | Part 2 |
| **B — deepening a state** | adding a county, a city tier, or a roster inside an existing instance | Part 3 |
| **C — a new concept/layer** | adding a layer idea to any instance | Part 4 |

Every path rides the same machinery — worksheet + generated regions, engine composition,
scraper→builder→PR pipelines, gates — documented once in **Part 6**. **Part 5 is the
lessons**: what Illinois's 91 counties and Wisconsin's four phases actually taught,
organized by the question they answer rather than by the county that paid for them.

### 0.4 The standing invariants (every path, non-negotiable)

1. **Honesty rules.** Officeholder data is never guessed; no verifiable source → the card
   links the official body and the gap is recorded. Honesty is **per-field** (a source that
   verifies names may not publish party/contact — store `null`, render "not published",
   never backfill from a weaker source). External strings always render through
   `sanitize()`/`textContent`. Never draw a boundary no agency publishes; never snap a
   no-match to the nearest polygon; appointed officials are labeled, never presented as
   elected.
2. **The expansion invariant** (Part 1): expanding coverage changes **which dispatch
   entries and roster rows exist — never which layers exist.** A new toggle is justified
   only by a governance function no current concept covers, and it launches consolidated.
   The "or" is real: some counties add **roster rows only** — an at-large board has no
   district geometry to dispatch on, so it ships with no dispatch entry, no coverage
   function and no toggle, riding the county's identity card instead.
3. **The at-large rule**: a body elected by the whole unit adds zero point-discrimination —
   it rides the unit's identity card, never a polygon layer.
4. **Officeholder sourcing ships with the boundary** (rule 4, §3.3) — decided and BUILT in
   the same change, never deferred.
5. **Engine parity by construction.** Code inside `ENGINE:BEGIN/END` fences is composed from
   the single copy under `engine/` by `scripts/compose_app.py`. **Never edit inside a fence
   in an instance file** — edit the block under `engine/` and recompose. There is no release
   channel and no per-instance copy to drift; the committed bytes are the deployed bytes.
   Never inline an instance value in a fence — add a `METRO:BEGIN config` variable.
6. **A measurement is not a conclusion.** Record what you observed and what it bounds,
   separately. "This host refuses this client" is a measurement; "this agency publishes
   nothing" is a claim about the world that the measurement does not support. §5.1 is
   mostly this rule paying for itself.
7. **Gates green before merge** (§6.5) — and roster changes always land as human-reviewed
   PRs, never direct commits to `main`.

### 0.5 Working style

Build in small, cheap, focused threads; paste only this guide's relevant contract/tables
plus the one module being worked on — never the whole app. Locate code by **grep anchor**
(a symbol or distinctive substring), never by line number (line-number anchors went stale
within weeks the one time they were tried). Record surprises as you find them, in the same
change: an unrecorded surprise is one the next pass pays for again (§5.5).

---

# PART 1 — Doctrine: the governance taxonomy

The audit behind this Part classified all 39 shipped layers (2026-07-27, Appendix A) by
**purpose, level of governance, function within governance, and election geometry**, so
expansion reuses concepts instead of multiplying them. Chicago is not a special case — it
is the **reference instance** of each concept (`ward` = districted municipal council;
`ward-precinct` = municipal-election-authority precinct; CPS zones = one district's
attendance boundaries). Where Chicago has a concept nobody else has, that is recorded, not
generalized; where others have the same concept in a different *shape*, the axes below
absorb the difference.

## 1.1 The axes

**Level:** Federal · State (incl. elected judiciary) · County · Township · Municipal ·
School district · Special-purpose district · Election administration · Reference/amenity.

**Function:** representation (a seat on a body) · whole-unit office (mayor, clerk) ·
service/taxing jurisdiction (fire/park/library/TIF) · service assignment (attendance zone,
police beat, polling place) · election administration · reference.

Out of scope by standing decision: **party offices** (precinct committeeperson,
ward/township committeeman) — the fleet's "recommend never" class.

## 1.2 Election geometry — the axis that decides surfacing

| Election geometry | Surfacing rule | Shipped precedents |
|---|---|---|
| **DISTRICTED** — seats elected by sub-geography | polygon concept layer; card names *your* representative | `ward`, `county-board`, `school-board`, `judicial-subcircuit`, `ccbr` |
| **AT-LARGE** — whole-unit electorate | roster rows on the unit's **identity card**; never a polygon | mayor + trustees on `municipality`; clerk on `county`; MWRD's nine at-large commissioners = link row |
| **APPOINTED** | labeled rows/links only | CPS network chiefs; NYC community-board chair |
| **NONE / ADMINISTRATIVE** | identity + honest links | precincts, ZIP, TIF, attendance zones |

This is the answer to "Chicago elects its council by ward; Elmhurst elects at-large": same
concept, different election geometry, zero new layers. Worked example:

| Place | Head of government | Governing body | Surface |
|---|---|---|---|
| Chicago | Mayor + City Clerk + City Treasurer on the `municipality` card (SHIPPED 2026-07-28) | 50 alderpersons by ward | body: `ward` layer; head + citywide officers: `municipality` card, whose council section points at the ward layer rather than listing 50 seats |
| Berwyn (Cook) | Mayor on `municipality` card | full ward-badged council on the card; *your* alderperson from the consolidated `ward` layer (SHIPPED 2026-07, §3.4) | Pattern A card + Pattern B polygon, both live |
| Alsip (Cook) | Village President on card | 6 at-large trustees on card | identity card only — correctly no polygon |

## 1.3 Sourcing dimension ≠ dispatch dimension

- **Dispatch by county** — disjoint county footprints, one concept toggle
  (`registerCountyLayer`): `county-board`, `judicial-subcircuit`, `fire-district`,
  `park-district`, `library-district`, `county-precinct`.
- **Dispatch by municipality** — two shipped shapes: the `municipality` card's roster
  join (one statewide tiling, county-*sourced* rosters keyed by place GEOID), and the
  consolidated `ward` layer's dispatch table keyed by municipality (the dispatcher's
  first non-county key — `opts.entries`; Chicago + suburban Cook + Evanston + Will
  cities + Aurora), whose suburban seat-holders join `municipal-officials.json` by
  municipality + seat number so the ward card can never name someone different from
  the Municipality card's list.
- **Dispatch by election authority** — Illinois voting is run by ~108 authorities: 101
  county clerks (scraped weekly from ISBE for the `county` card), a few municipal boards
  of election commissioners (Chicago's is one), Peoria's appointed commission.
  `ward-precinct` (Chicago BOE) vs `county-precinct` (clerks) is this dimension in
  production; a future municipal-commission city (Rockford/Bloomington class) joins as an
  authority entry, coverage-carved out of its county exactly as `suburbanCookCoverage`
  carves Chicago out of Cook. `early-voting` generalizes the same way (per-authority site
  files, hand-curated per election).
- **No dispatch** — one statewide source: the TIGERweb identity layers, the chamber
  layers, `zip-code`.

## 1.4 The three surfacing patterns

- **Pattern A — identity layer + whole-unit officers on its card** (`county` + clerk;
  `municipality` + mayor/board/officers; `township` + officers — shipped 2026-08-19, Cook first).
- **Pattern B — districted-body concept layer**, dispatched per source (`ward`,
  `county-board`, `school-board`, `judicial-subcircuit`, `ccbr`, the service/taxing
  district layers).
- **Pattern C — nearest-N amenity** (`police-station`, `fire-station`, `post-office`,
  `library`, `school-site`, `early-voting`) — honest straight-line proximity, N small.

## 1.5 Standing rules earned by the audit

- **Commission-county boards** (17 downstate counties elect 3 commissioners county-wide;
  some township counties elect boards at-large): at-large → `county`-card roster rows, no
  polygon, no toggle change. Decide districted-vs-at-large per county at expansion — and
  decide it from a CERTIFIED ELECTION DOCUMENT, never from a board page that happens not
  to mention districts (§3.5.1). Six counties ship this way as of 2026-08-02: Monroe and
  Randolph (commission form, 3 each), Pike 9, Brown 7, Calhoun 5, Putnam 5.
- **School governance:** every IL district board except Chicago's ERSB is elected
  whole-district → Pattern A enrichment on the `school-district-*` cards; attendance zones
  are per-district opt-ins; a new county changes nothing in the schools group.
- **Complete-tiling rule** for special-district layers: municipal service rows belong in a
  county's tiling only where it records that municipal class **completely** (Kendall
  library funds kept; McHenry's lone Crystal Lake row excluded; municipal fire rows always
  excluded — a municipal fire department is the municipality). A partial inclusion lies by
  omission.
- **Single-county conversion triggers:** a dedicated layer converts to a dispatched
  concept when its second county ships — `tif-district` → Kendall's `TIF_Districts`
  service; `mwrd` → a `sanitary-district` concept if a second county's sanitary tiling
  ships (the MWRD *body* is unique; the *class* isn't — Cook's Clerk catalog carries an
  unwired Sanitary tiling L12). `dupage-county-special-police` has no analog sighted.
- **Whole-unit officer rosters recur** and often share sources: county officers beyond the
  clerk (per county, rule 4), township officers (a SHIPPED concept since 2026-08-19 —
  township-officials.json, Cook's Clerk directory first; new counties ride the same clerk
  yearbooks as the municipal scrape — capture both sections in one pass; verify depth at
  build time; TOI link floor).
- **"Who polices this point"** generalizes as card rows (municipal PD candidate row +
  Sheriff among county officers) + the metro-wide `police-station` layer — never invented
  geography. `ccpsa-district-council` stays Chicago-unique.
- Cheap statewide judicial notes: the five **Appellate Districts** share the Supreme Court
  map (a card row, never a layer); the elected **ROE regional superintendent** is a
  DERIVE-class candidate (verify the Cook/Chicago carve-outs); the statewide
  `judicial-circuit` DERIVE stays blocked (no authoritative machine-readable
  county→circuit source — never hand-encode).

Recorded candidates from the audit live in `docs/DATA_LAYER_GUIDEBOOK.md`'s backlog
(the "Governance-standardization pass" entry).

## 1.6 The new-concept test (gatekeeper for every proposal)

1. Which level + function (§1.1)? Duplicates an existing concept at that level → it is a
   dispatch entry or card row there, full stop.
2. Which election geometry (§1.2)? Districted → consolidated concept layer. At-large →
   identity-card rows. Appointed → labeled links. Party office → out of scope.
3. Which dispatch dimension (§1.3)?
4. Officeholder story in the same change (rule 4); honesty floor = link, gap recorded.
5. Guidebook row + Appendix A classification updated in the same change.

---


---

# PART 2 — Path A: a new state instance

**Wisconsin is the worked example.** It arrived 2026-08-25 as the first state to expand IN
PLACE, and its import commits are the reference for state N+1. The template-repo route that
briefly existed for this was built, proven end-to-end, and retired the same day in favour of
in-place expansion — one deploy surface, no cross-repo sync (§2.8 is the decision record).

**Scope, honestly.** This recipe targets US states with district-based elected civic
geography. It leans hard on three national publishers that tile every state — Census
TIGERweb, the USGS National Map, and the congressional/legislative roster projects — and
then on whatever the state itself publishes. A state with no open GIS office is a thinner
instance, not an impossible one; a state whose legislature publishes ward-level geography
(Wisconsin's LTSB) is a much richer one.

## 2.1 The state worksheet — fill this in first

Every per-instance fact lives ONCE in `<tag>/metro-worksheet.json`, and the GENERATED
regions in `index.html`, `sw.js`, `sources.html`, `validate_index.py`, `smoke_test.mjs`,
`CLAUDE.md` and `README.md` are emitted from it. Fill it before writing a layer.

| Parameter | Wisconsin | Derive yours |
|---|---|---|
| `this_metro` / `metro_name` | `wisconsin` / Wisconsin | the instance id and display name |
| fleet `tag` | `wi` | the URL segment and folder name — postal code for a state |
| `STATE_FIPS` | `55` | 2-digit Census FIPS; drives every TIGERweb query |
| `metro_bbox` | state envelope | geocoder bias, POI viewbox, geolocation check |
| `metro_center` + zooms | Wausau-ish, zoom 7 | frame the whole state, not a city |
| `permalink_gate` | looser than the bbox | rejects absurd `#point=` values |
| Geocoders | Photon (state-bounded) + Nominatim POI | §2.6; a state-authoritative geocoder wins if one exists |
| Coverage bands | **two** — in-state / outside | §2.5.1; a statewide instance is usually two |
| Ground truth | Marathon County point → 9 anchor layers; negative point off the NW corner | §2.5 |
| Offline anchors | counties, school districts, chambers, congress | ≥3 static-file layers |
| Legislature | Senate 33 / Assembly 99 | chamber sizes gate the roster floors |
| Congressional seats | 8 | from `data/state/` at bootstrap |
| Board/commission structure | 72 counties, 1,590 supervisory districts | the depth question Part 3 answers |
| Domain / brand / analytics | districtry.com/wi/, the fleet's shared GoatCounter endpoint | never the reference's domain or brand; analytics copied from a sibling — one shared site, keyed by path (corrected 2026-09-02) |

## 2.2 What the instance inherits vs writes

**Inherits, untouched:** every `ENGINE:BEGIN/END` block, composed from `engine/` by
`scripts/compose_app.py`. Map boot, the layer registry and card framework, state/sequence,
permalinks, the hover explorer, shared utilities, the ArcGIS/TIGER loaders, and the layer
factories (`registerPolygonLayer`, `registerIlgaChamber`, `registerNearestPointLayer`,
`registerSchoolZone`). You never edit these in the instance; you edit `engine/` and
recompose, which changes every instance at once.

**Writes:** the `METRO:BEGIN config` block (worksheet-generated), the layer modules, and the
branding rows. A new instance's `index.html` lands around 7–9k lines before its own layers
grow it.

**Re-core surgery notes, paid for in a real port:** delete only the `registerXxx({…})` calls
and their instance-specific preamble; keep every factory and loader. Then grep the ENTIRE
surviving file for calls to now-undefined identifiers — dangling references run both
directions, and a kept factory calling a deleted helper crashes only when the first REAL
roster lands, because placeholder data never exercises the path. Instance vocabulary also
hides in engine code as **feature-property name literals**: re-seed
`HOVER_NUMBER_KEYS`/`HOVER_NAME_KEYS` from the new state's observed field names (stale lists
fail silently — the hover popup degrades softly by design and no gate notices).

**Test and gate constants are re-derived, never copied**: the smoke test's `POINT` /
`OFFLINE` / `EXPECT_LAYERS` / `EXPECT_DISTRICT` and second point; `validate_index.py`'s
`MIN_REGISTER_LAYER` / `GEOMETRY_FILES` / `ROSTER_FILES`; the `validate_sources.py`
manifest; every count floor; `sw.js`'s `CACHE_NAME` and its three lists.

## 2.2.1 The layer contract (identical in every instance)

```js
{
  id, group,                    // political | safety | schools | geography
  label,
  overlay: { load, style | pointToLayer },   // lazy, cached
  query(point, seq) -> Promise<Result|null>, // point-in-district + roster join; seq-tagged
  render(result) -> HTMLElement,             // all external strings sanitized
  pointOfInterest(result) -> {label,address}|null   // optional geocoded pin
}
```

Optional fields the core honors: `subOf`, `color`, `onToggle(on)`, `hoverName(feature)`,
`hoverOfficial{load?, name()}`, `coverage(point)`, `compact`, `primaryLink`. Five
non-negotiable module rules: seq-tagged results; toggle-off clears the card; failures
surface inside that card only; sanitize everything external; explicit honest
no-result/no-match/slow states. **Hover-parity rule:** hover identity comes from the same
properties the card reads (factories derive it; a bespoke block declares `hoverName`, plus
`hoverOfficial` when the card joins a roster — prefetched on toggle-on so hover never
fires a network request). An appointed official's hover name carries its role.

**Factories before bespoke blocks:** `registerPolygonLayer` (declarative fields card) ·
`registerSchoolZone` (zone → school + POI + profile link) · `registerCpsNetwork`
(officeholder rides the boundary dataset's props) · `registerIlgaChamber` (boundary +
same-origin roster keyed by district; the congress/state-chamber pattern, incl. office
groups) · `registerNearestPointLayer` (nearest-N haversine). Non-factory patterns to
copy: two-live-datasets join (`ward`); shared-geometry, one loader → N layers
(`ccpsa-district-council`; NYC borough = county serving three offices); nearest-N bespoke
(`school-site`, polygon campus footprints). Platform coupling: `registerSchoolZone` /
`registerCpsNetwork` build loaders via the Socrata-only `makeCachedLoader` — on a
non-Socrata portal convert them to an injected `loader` (follow `registerPolygonLayer`'s
existing opt).

**Cards** follow the fleet content order — layer name, district identifier, then wherever
a verifiable source exists: representative(s), office location, contact, link — rendered
through the card-helpers vocabulary (`docs/CARD_RENDER_API.md`; helpers are data-only by
contract, never pass HTML).

## 2.3 The bring-up checklist (in order)

1. **Create `<tag>/`** from the reference shape and fill the §2.1 worksheet.
2. **Register in the fleet** (§2.4) — this is day-one work, and every item on that list was
   missed by a real port.
3. **Compose and generate**: `scripts/compose_app.py` then
   `scripts/generate_metro_files.py`. Never hand-edit a GENERATED region or a fence.
4. **Ship the national tier first.** TIGERweb answers for every state on day one: counties,
   county subdivisions, places, school districts (unified / elementary / secondary), ZCTAs,
   and the legislative + congressional chambers. USGS National Map adds police stations,
   fire stations and post offices as nearest-N. These are ~12 honest layers before you have
   asked anybody for anything, and they are what makes a statewide instance useful in a day.
5. **Decide the layer roster from the concept matrix** (`docs/DATA_LAYER_GUIDEBOOK.md`):
   walk the reference layers, map each to the local equivalent, and **drop, never fake,
   where no honest analog exists** — recording each drop with its structural reason.
   Wisconsin's drops are the model: park districts are not a unit of government there;
   library boards are appointed, so the concept ships as *points* rather than a taxing
   district; the technical-college board is appointed by statute, so the layer is
   identity-only and says so.
6. **Write `LAYER_AREA_RANK` largest→smallest** — every registered id appears, no exceptions
   (two consumers: restacking and hover profiles; a missing id is invisible to both), with
   sub-layers ranked just before their parent. Then `LAYER_SIDEBAR_RANK` (§4).
7. **Pick ≥3 offline anchors + ground truth** (§2.5), including the negative point.
8. **Decide the coverage bands and name them** (§2.5.1).
9. **Map the pipeline per roster** (§6.3): engine ladder rung, count floors — and land the
   cheapest real roster during the module threads, not a later pipeline thread. Real data
   flushes factory paths that placeholders never exercise.
   **Officeholder sourcing ships with each layer** (rule 4, §3.3).
10. **Re-derive every gate constant** and the three `sw.js` lists.
11. **Cross-group parity audit**: for each field any group's card renders (address, pin,
    phone, links), check every other card that could carry it. No gate catches this class;
    only a side-by-side pass does. Second axis: toggle every polygon layer and hover the
    ground-truth points, confirming real identities — the popup fails soft by design and
    shipped label-only in a real port.
12. **Run the localization sweep** (§2.7), write `<tag>/CLAUDE.md` and `<tag>/WATCH.md`, and
    record the roster in the guidebook.

## 2.4 Day-one registration

In the **repo root**: (1) **at go-live, not on day one** — add the instance to `metros.json`
with `id`, `tag`, `url`, `landing_name` and `blurb`, then run
`generate_metro_files.py --sync-fleet` — `sync_fleet` projects a whitelist into each
instance's `metro_explorers` and deliberately keeps the three landing fields fleet-level, so
they never reach an app. CORRECTED 2026-09-02 from Iowa's PR 0 (`docs/IA_EXPANSION_PLAN.md`):
`render_cards()` and `sync_fleet()` filter nothing, so a `metros.json` entry renders a live,
clickable landing card the day it lands, and while the folder is still excluded from the
deploy that card is a 404 — until go-live, hand-seed the new worksheet's `metro_explorers`
from a sibling's array, which is exactly what `--sync-fleet` will produce later; (2) regenerate the root landing page
(`build_landing_page.py`) and `privacy.html` (`build_privacy_page.py`) — the privacy page is
**measured from each app's shipped `index.html`**, so a new instance appears there only once
its analytics and geocoder posture are real; (3) add its `validate_index.py` and
`smoke_test.mjs` invocations to `smoke-test.yml`; (4) add it to the guidebook (coverage map,
inventory, matrix, drops included); (5) drop it from the deploy's EXCLUDES list — that is
the switch that makes it live — and add its `data/source` and `scripts` to the excludes so
build inputs and tooling never publish; the same file's `for published in` presence loop is a
hand-kept list too, and the go-live PR extends it (Iowa's did), together with (1).

In the **instance**: (6) its own `scripts/` with `validate_index.py`, `smoke_test.mjs`,
`validate_sources.py` and its builders — imports resolving inside its own tree, which
`validate_workflow_deps.py` enforces; (7) PWA icons and `manifest.webmanifest` (generated —
`build_manifests.py`); (8) analytics — copy `brand.analytics.goatcounter_url` from a sibling
worksheet: the fleet counts on ONE shared GoatCounter site keyed by path, and never add a
`ga_id` (the schema says a rebrand must not add a tracker). CORRECTED 2026-09-02: this item
used to say "its own GoatCounter site and tag", which no instance has ever shipped — all five
worksheets carry the same endpoint; `trackEvent` still no-ops silently when the key is
absent, and a real port shipped days of zero analytics that way; (9) *(operator)* any CI
secrets its scrapers need.

**Anything fleet-level that names the instances should DISCOVER them, not list them.** Every
hand-kept fleet list is a registration step, and this one is the step most often missed:
`validate_card_links.py` carried its authored pages and its roster directories as literals,
both were extended by hand for Wisconsin on 2026-08-26, and Iowa arrived the NEXT DAY and was
added to neither — `ia/index.html`, `ia/faq.html`, `ia/sources.html` and Iowa's whole
`data/app` (303 URLs, 52 of them this repo's own) sat outside the link gate, where a dead link
stays green forever. Both are now derived: every `*.html` at the root and in each instance
folder, one `data/app` per instance, where an instance is a top-level directory with its own
`index.html` and `data/app/`. One caveat if you reach for the generator's table to do the same
elsewhere: `from generate_metro_files import INSTANCES` **exits 1** when `jsonschema` is
missing rather than raising `ImportError`, so the usual `try/except ImportError` fallback does
not catch it — `check_roster_retention.py` carries exactly that guard and dies at import
without the package, which only its own workflow happens to install.

## 2.5 Offline anchors, ground truth, and the coverage wash

Live civic APIs are flaky and CI-hostile, so the test strategy rests on ≥3 **API-free
anchor layers** shipped as same-origin static files: the smoke test classifies ground
truth against them; `validate_index.py` pins their feature counts; `sw.js` serves them
cache-first (vs network-first rosters — never a stale officeholder). The wash marks
*where deep coverage ends*, never "no data here" — regional layers still resolve under
it, and it fails silent.

**Draw the wash from a purpose-built metro outline, not from whichever anchor happens to
tile something** (revised 2026-07-28; Chicago previously passed its school-board anchor).
Two reasons, and the second is the one that bites:

1. **The boundary must track coverage as it grows.** Chicago's wash was the *city* limits
   because that is what the anchor tiled, so as the collar counties filled in it kept
   greying out territory the app had come to serve — a Will or DuPage point resolves
   17–21 of 39 layers against Chicago's 32 and suburban Cook's 25. Coverage thins across
   a metro; it rarely stops at one layer's edge. Pick the boundary from what the app
   *answers*, and re-check it after any county expansion. Removing the wash entirely is
   the opposite error: the tiers are real, and a wash-free map claims a parity the data
   does not support.
2. **Per-county outline files will not dissolve.** The engine cancels an interior border
   only where the two neighbours share EXACT coordinates. Chicago's six
   `*-county-outline.json` files were simplified independently, so they share as few as
   **2** vertices along a real border and would leave hairline seams or fail the closure
   guard. Build one polygon from a **single** query against one source (a TIGERweb
   multi-county fetch returns 2,034 shared vertices on Cook/DuPage) and dissolve it at
   build time — `scripts/build_metro_outline.py` is the reference, mirroring the engine's
   own algorithm so the shipped file is what the browser would have computed.

Simplify hard and validate the *simplified* rings: metro outlines are mostly survey-grid
straight lines, so Douglas-Peucker at 25 m took Chicago's from 2,665 vertices to **62**
(2.5 KB), and the builder refuses to write unless one anchor per county still falls
inside and known outside cities fall outside — ring closure alone does not prove a county
wasn't dropped. The payoff is also a boot cost: the old anchor was an 83 KB fetch in PSI's
669 ms initial-navigation chain for a decorative wash.

Produce anchors with `scripts/build_embedded_boundaries.py`
(pinned mapshaper, Visvalingam keep-shapes) and its validation: **≥99.5% agreement on
2,000 seeded points AND zero double-classification**, counts/properties unchanged —
register every anchor in its `LAYERS` dict so regeneration never regresses to manual.
Pin a **negative point** where geography allows (water, enclaves, county slivers) and
pick it against a shoreline-clipped layer — whether mid-water is a no-match depends on
the dataset, and the water-inclusive layer's positive answer is legally correct.
**Exactly-one-list invariant:** every `data/app/` file appears in exactly one of
`GEOMETRY_URLS`/`ROSTER_URLS` (in neither = never cached; wrong list = wrong freshness) —
machine-checked in `validate_index.py`; bump `CACHE_NAME` on any list change.

### 2.5.1 The coverage key — decide the instance's BANDS, then name them

The wash has a legend, and the legend is worksheet data. Two decisions, in this order.

**First, how many bands does this instance have?** A wash is two bands by default —
inside coverage, and outside it. It is **three** only when full coverage is a proper
SUBSET of a wider region whose layers still answer throughout, and the middle band says
"you still get something here" rather than "nothing here". Answer it by looking at what
the instance's own layers cover, not by whether a state exists:

| Instance | Coverage geometry | Bands | Why |
|---|---|---|---|
| Illinois | the served counties | **3** | county/township/municipality/school-district/ZIP answer statewide; the county layers do not |
| Wisconsin | the counties whose supervisor ROSTER ships (`metro-outline.json`); `wi-state-outline.json` is the region ring | **3** | every layer answers statewide — the middle band means "district shown, supervisor not named", a narrower claim than the other three instances' middle/outer bands make (it was 2 bands at launch, when coverage *was* the state outline; #523 split them the day the roster shipped) |
| San Francisco | the 11 supervisor districts | 2 | no wider region in play |
| New York City | the 5 boroughs | 2 | same |

A two-band key is not a degraded key. Until it shipped the grey was unexplained in every
instance, and one row saying "Outside New York City" is the whole of what that map claims.

**Second, name them.** Add `coverage_key` to the instance's worksheet — `outside` is
required, `region` (`edge`, `label`, `sub`) only for a three-band instance — and
regenerate; `generate_metro_files.py` emits `COVERAGE_KEY` into the metro-config region.
**Do not try to derive the words.** Chicago's `METRO_NAME` is "Chicago" while its coverage
is 89 Illinois counties, so `"Outside " + METRO_NAME` is wrong in exactly the instance
that most needs the key. Omit the whole object and the engine's `typeof` guard draws the
wash with no key, byte-identically to before — the same inertness rule `brand` and
`poi_geocode_bbox` follow.

**A three-band instance owes GEOMETRY as well as words.** The middle band needs the wider
region's ring, passed as the second argument at boot —
`drawOutOfScopeMask(loadCoverageGeometry, loadRegionGeometry)`. Build it, do not fetch it:
Illinois' ring live from TIGERweb is **332 KB over 19,789 vertices**, four times the fetch
§2.5 above exists to have removed for this same decorative wash. It is the second output
of `build_metro_outline.py`, from layer 0 of the same MapServer as the county dissolve.
**Simplify it at the same tolerance as the coverage outline** — where a served county
fronts the region's edge the two rings trace the same line, and simplified apart they open
slivers of a false middle band along it.

The key renders only the bands the draw actually produced, so a declared `region` whose
geometry fails to load degrades the wash and the key together rather than leaving a label
over a band that is not on the map. Declaring `region` without wiring the geometry
therefore gets you a two-band key and no error — check the map, not the worksheet.


## 2.6 Platforms, sources, geocoding


Identify the portal platform first — it changes how every layer queries:

- **Socrata**: four-by-four ids, `/resource/{id}.json` SoQL; server-side
  point-in-polygon via `intersects(geom, 'POINT(lng lat)')` (lng-first WKT) — a
  *research/verification* tool here, not the runtime path (every layer downloads its
  boundary once and classifies client-side; per-click portal calls would multiply
  throttling exposure and break overlays/hover/anchors/failure isolation).
- **ArcGIS Hub / REST FeatureServer**: `…/FeatureServer/<n>/query`; always request
  `outSR=4326` (native projections are often State Plane); page past `maxRecordCount`
  while `exceededTransferLimit` (`loadArcGISPaged`).
- **CKAN**: a catalog, not a query engine — download once, convert, ship as a §2.5-style
  static file (follow "GeoServices/WFS" links to any real live endpoint).

**The federal/universal tier is free for any US metro**: TIGERweb
(`Legislative/MapServer` 0/1/2 + county/place siblings, `STATE='<fips>'`; unicameral and
council-only jurisdictions ride layer 1 — register one chamber, not two) +
`unitedstates/congress-legislators` (`legislators-current.json`, CC0 — the reference
builder re-parameterizes on state + count; the 2026-07 enrichment joins
`legislators-district-offices.json` by bioguide id).

**Geocoding decision rule:** (1) a city-authoritative keyless geocoder with real
autocomplete replaces *both* reference geocoders (NYC GeoSearch is the exemplar); else
(2) Photon for type-ahead; (3) Nominatim as debounced submit-time fallback ONLY (its
policy forbids autocomplete; keep the serial ≥1s POI queue). **App tokens:** a Socrata
app token is a public throttling identifier — front-end constant by design; a real API
key (401s without it) is a repo secret, server-side only, never in `index.html`. No
token analog exists for ArcGIS/TIGERweb/CKAN public reads — if a public endpoint
throttles/WAFs, ship the layer as a static file instead.

## 2.6.1 Dataset research & verification protocol

1. Live-sample field names before wiring; seed `findPropCI` aliases with observed keys.
2. Label every registry row VERIFIED / UNVERIFIED / **UNVERIFIED-fetch** (exists but
   WAF/key-blocked — it changes the pipeline engine), with the fetch date.
3. The portal-page id and the geometry-serving id can differ — record which of
   `loadSocrataGeoJSON`'s three routes actually served geometry.
4. Map-type Socrata datasets serve geometry only via the export or v3-view route — set
   the per-dataset route override rather than burning failing routes per load.
5. Probe server-side point-in-polygon once with a known landmark — validates endpoint,
   operator, and geometry column in one query.
6. Watch record caps (Socrata `$limit=1000`; ArcGIS transfer caps) — filter server-side
   or page.
7. Anchor simplification passes the 2,000-point protocol (§2.5), unmodified.
8. A layer with no honest source gets an honest registry row — drop or link, never
   invent.
9. Point datasets may serve no geometry on the geojson route (coordinates only in
   `latitude`/`longitude` properties) — `makeSocrataPointLoader` assembles the
   FeatureCollection.
10. Sample exact **values**, not just field names — SoQL string equality is
    case-sensitive (`'Police Station'` matched 0 where `'POLICE STATION'` matched 80);
    numeric-looking fields arrive as float strings. Normalize in the loader.
11. **Verify coverage, not existence** — a pattern confirmed on one sample can cover a
    fraction of the roster (Legistar carried district URLs for ~24/51 members; NYPD pages
    resolve 74/78 COs). Count how many of N records carry the thing; set floors below
    100%.
12. **Soft-degrading surfaces ship broken — audit by hand**: the hover popup's fallback
    keys, empty states, anything that renders em-dashes instead of erroring (§2.3 step 9).

Registry columns: layer target (+ expected count) · source type · id/endpoint **+ the
route that served geometry** · geometry column + observed fields · roster source ·
CRS/paging/auth notes · status + date.

## 2.6.2 Generic gotchas (each paid for in a real port)

One boundary hosting several offices → one cached loader, N layers. Assume MultiPolygon;
spot-check a gnarly one. Trust authoritative polygons over intuition (Marble Hill).
In-bounds ≠ in-district — honest no-match, never snap; in multi-county metros register a
county context layer and word county-office empty states to point at it. Nearest-N can
cross water — keep N=3, label "as the crow flies". Non-residential polygons are real
answers — surface the type field. Honesty is per-field (§0.4). Elected-but-superseded
bodies exist (HISD's trustees under a state-appointed board): label the actual governance
status, show both bodies, each labeled — never hide the elected roster, never present
appointees as it.


## 2.7 The localization sweep (leftover-reference-state gate)

At assembly and again before launch, grep the new instance for the reference's
fingerprints — `chidistricts`, `cityofchicago`, `ChiExplorer`, `chicago`, the reference's
`data-goatcounter` tag — across `index.html sw.js README.md CLAUDE.md WATCH.md
manifest.webmanifest scripts/ .github/`. Allowlist: fence comments naming the reference,
the reference's own `metro_explorers` entry, deliberate doc citations. **Everything else is
a leftover.** Past escapes include a Chicago-biased geocoder shipping through five threads
of another instance, Chicago SEO metadata, stale `validate_sources.py` manifests and
orphaned seal art.

Two refinements the one live day of the retired template route paid for, and they
generalize to any sweep:

- **Anchor reference URLs to URL position** (`//chidistricts`), because the fleet's own
  subdomains legitimately contain the bare string — found by Wisconsin's own domain within
  minutes.
- **Never police `data/`.** The real world contains the reference's vocabulary — found by
  the School City of East Chicago, Indiana.

## 2.8 The template-repo route (RETIRED 2026-08-24, decision record)

**Decided shape: states expand IN PLACE — not as per-state forks.** A template repository
GENERATED from this tree once existed, from which each state started via GitHub's "Use this
template", bootstrapped by one command. It was built, merged, and proven end to end the same
day: the generated template boot-tested as a real Indiana app in CI, and a real Wisconsin
repo went from "Use this template" to green CI in minutes. The operator then retired the
route in favour of in-place expansion — one deploy surface, no cross-repo sync — and
Wisconsin, the state the route was proven on, shipped IN PLACE as `wi/` the following day.

What survives deliberately: the `TEMPLATE:BEGIN/END` span markers in `index.html`/`sw.js`.
They are inert comments AND the line-by-line map of what is instance-specific versus engine,
which in-place multi-state work needs just as much. Do not sweep them. The builders
themselves (`build_state_template.py`, `bootstrap_state.py`, `check_template_placeholders.py`,
`templates/state/`) were deleted with the rest of the per-state fork machinery in R2.1.

## 2.9 Verification

Run in this order; each is cheap and each has caught a real regression:

```bash
python3 scripts/generate_metro_files.py --check     # generated-region drift
python3 scripts/compose_app.py --check              # engine fences match engine/
python3 scripts/build_coverage_gaps.py --check      # gap records match the guidebook
python3 <tag>/scripts/validate_index.py <tag>/index.html
python3 scripts/build_landing_page.py --check       # the fleet's front door lists you
python3 scripts/build_privacy_page.py --check       # measured from your shipped app
python3 scripts/build_manifests.py --check
python3 scripts/build_dark_map_palette.py --check   # your layer colours have dark twins
python3 scripts/validate_workflow_deps.py           # your scripts import inside your tree
python3 <tag>/scripts/validate_sources.py           # every source row resolves
# behaviour gate — serve the REPO ROOT, one server for every instance:
python3 -m http.server 8000
BASE_URL=http://localhost:8000/<tag>/ node <tag>/scripts/smoke_test.mjs
```

`EXPECT_LAYERS` is asserted exactly, ground truth classifies against the anchors, and the
negative point must miss every anchor. **Sandbox note:** the SessionStart hook vendors
Leaflet and MapLibre per instance (`scripts/vendor_leaflet.sh`) because headless Chromium
cannot reach the CDN through the agent proxy. That is environmental, never a code
regression — and the script exits 1 rather than skipping silently when it cannot find an
instance's app file, because a silent skip once produced a smoke-test timeout 45 seconds
later that looked exactly like an app bug.

---

# PART 3 — Path B: deepening a state

Depth is added a **unit at a time**: a county, a city tier, or a roster. The unit differs by
state — Illinois grows by county because its civic geography is county-organized; Wisconsin
grows by county for boards and precincts and by CITY for the tiers only a municipality
publishes (police districts, neighborhoods, TIF, ward-level polling). Both obey the same
invariant: **a new unit adds dispatch entries and roster rows, never new layers.**

**Before anything technical, ask what governs.** §1.6's taxonomy test resolves most
proposals to a dispatch entry or an identity-card enrichment rather than a layer, and §5.1's
sourcing questions decide whether the unit is buildable at all. A unit that is not buildable
gets a MEASURED gap record (§5.5) — that is a completed piece of work, not a failure.

## 3.0 The city tier — the statewide instance's version of depth

A statewide instance's cities publish concepts the state does not: Wisconsin's Milwaukee and
Madison tiers carry police districts, squad areas, neighborhood fabrics, tax-incremental
districts and ward-level polling places, none of which any statewide publisher offers. The
pattern:

- **One coverage gate per city** (`milwaukeeCoverage`, `madisonCoverage`), built from the
  city's own ward fabric dissolved to its corporate limits — not from a bbox.
- **A concept that appears in a second city becomes a dispatched concept**, exactly as a
  county concept does. Wisconsin's TIF toggle answers in both cities through one layer.
- **The city's own publisher outranks the state's** for anything the city administers,
  because the city runs it — but keep the state's answer as the fallback rather than
  partitioning, so a city file failing to load degrades instead of dead-ending.
- **Two surfaces, always**: the city's live service AND its open-data extract, with the
  build-time witness comparing them. That witness has caught a service and a shapefile
  spelling one neighborhood differently, a layer carrying retired districts the live service
  omits, and a city GIS layer stale on one seat against certified returns.


## 3.1 Dispatcher semantics (decided, shipped)

- **Coverage = OR of the entries' coverages**, checked in table order (cached same-origin
  outline tests). Outside every sourced county the layer hides; a throwing check falls
  through; an all-throwing miss propagates so the engine's fail-open applies.
- **Query dispatches by containment, not coverage**: try each county's own geometry in
  order; first containment hit wins (they cannot overlap). A downed county is skipped
  while others resolve; if no county matched and one errored, the error propagates — a
  point in the downed county gets the honest error card + Retry, never a lying "No
  result".
- **Overlay = union** of sourced counties' boundaries, each feature wrapped (not mutated —
  caches are shared) and stamped `dxCounty` for hover dispatch. A county failing at load
  drops out of the union while others draw (known tradeoff: the engine caches overlay
  geojson per session, so a partial union persists until reload; the query path refetches
  with Retry and is unaffected).
- **Hover-roster prefetch is all-or-retry**: the composite `hoverOfficial.load` rejects if
  any county's load fails (the engine caches only resolved rosters), so the next toggle-on
  retries; already-loaded counties resolve instantly from cache.
- **One style + a generic toggle label** per concept. County identity moves into the card
  (a `Body`/`Court`/`County` row, or the clerk link) right after the district identifier.
- **Permalinks keep working**: retired per-county ids are rewritten by the instance-side alias
  shim that runs before boot-time hash parsing; every consolidation appends its retired
  ids there.
- An entry's coverage may be **narrower than its county**: `county-precinct`'s Cook entry
  uses `suburbanCookCoverage` (in Cook AND NOT Chicago) because city precincts belong to
  the BOE's `ward-precinct` layer — the carve-out test fails toward "not Chicago" so a
  city-tiling outage can't take down suburban service.
- **The key doesn't have to be a county** — the dispatch only ever required disjoint
  footprints. `ward` is the precedent (2026-07): municipal wards consolidated onto it as
  municipality-keyed entries via `opts.entries` (the general spelling alongside
  `opts.counties`). Two wrinkles worth copying: order the table so the cheapest
  already-cached coverage test sits first and short-circuits the OR (Chicago first —
  most traffic never fetches the suburban coverage file), and make a multi-source
  entry's coverage test a small **prebuilt outline file**
  (`data/app/municipal-ward-coverage.json`, `build_municipal_ward_coverage.py`) rather
  than the live services — the engine evaluates `coverage` for every declaring layer on
  every point selection.

## 3.2 What consolidates, what doesn't

- Concepts consolidate; **bodies don't merge** — `ccbr` (property-tax appeals) is not
  Cook's legislature and stays its own layer.
- `ward-precinct` stays a city layer: same concept as county precincts, different parent
  (`subOf ward`) and different election authority (§1.3).
- **Municipal governments are NOT county-dispatched**: the sourcing dimension is the
  county, but the dispatch dimension is the municipality — 284 metro municipalities tile
  from one statewide source and 47 span county lines, so a county-keyed table would
  resolve the wrong body at borders. They join the statewide `municipality` card by place
  GEOID (§3.4).
- **Single-county concepts** stay dedicated until a second county ships (conversion
  triggers in §1.5).
- A county-specific layer is only ever created for a concept no consolidated layer covers
  yet (as `dupage-county-special-police` remains).

## 3.3 Rule 4 — officeholder sourcing is determined AT expansion, never deferred

For every concept a new county brings in, the same change that ships the boundary decides
— and builds — the officeholder story:

1. **GIS attrs**: the county's boundary service carries member/contact fields (Lake; Kane
   names) → verify against the published directory and use them; no pipeline. GIS attrs
   and a directory pipeline **compose** (Kane: GIS names as hover+fallback, weekly
   SharePoint scrape adds party/phone/email + the countywide Chair; Lake: GIS live fields
   + a weekly scrape adds Chair/Vice-Chair tags, applied only on a name match so a missed
   reorganization degrades to role-less rows).

   **Two measurements decide branch 1, and a service passing one can still fail the
   other.** *Is the column populated?* — DeKalb declares `Member1`/`Member2` phone and
   e-mail and populates the phones on 0 of 12 districts, so a schema is not data. *Is the
   column CURRENT?* — Freeport's ward service populates `Alderperson` on every feature and
   its `editingInfo.dataLastEditDate` is 2024-05-21, so it was still naming a holder the
   April 2025 election had replaced. **A live service is not a current service.** Read
   `editingInfo` off the layer's `?f=json` before treating an officeholder column as
   branch 1; if the last data edit predates the most recent election for that seat, the
   column is a snapshot, not a roster, and the county/city directory wins. Boundary
   geometry from the same layer can still be sound — staleness is per-field.
2. **Official directory, no GIS fields** (Will, DuPage, Kendall class): scraper + builder
   + weekly PR-opening workflow ships **in the same expansion change**. Bot-managed sites
   are not an excuse — the engine ladder (requests → Playwright → Internet Archive SPN;
   `kendall_county_board_scraper.py` / `mchenry_county_board_scraper.py` are the
   templates) handles Cloudflare and Akamai fronts alike.
3. **No verifiable source**: the card links the official body; the guidebook records the
   gap. The floor, never the default.

**Terminal case (verified 2026-07 on Kendall/McHenry):** a source may block ALL automated
fetch — direct, real-browser, and the Archive's crawler. The pipeline still ships: the
roster holds hand-verified transcription (every record carrying `source_url`), the weekly
workflow attempts the ladder and converts total failure into a standing tracking issue
(green run — the validate-sources pattern), a 45-day snapshot age guard ensures stale is
never served as fresh, and automation resumes the moment any rung unblocks.

## 3.4 Rule 5 — municipal governments ship with their county

A county brings its municipalities; rule 4 applies to them in the same expansion change.
Status: **twelve counties SHIPPED** (2026-07-31) — 349 municipalities on one weekly-CI
`municipal-officials.json`, 1,379 board members and 335 ward/district seats. Depth is per
county, and the mix is the point: **six full-governing-body** sources (Cook 129, Will 30,
LaSalle 26, Winnebago 11, Ogle 13, Stephenson 11), **five head-level** (McHenry 27,
Kane 24, DuPage 23, Kendall 7, Carroll 7), and **one contact-only** (Lake 41, which publishes
no names anywhere county-side). Four city-level payloads fill what a county cannot:
Will's ward cities and Joliet (per-seat contact), Skokie (trustee districts), and Freeport
(the whole city — see *county source omits a municipality*, below).
The concept: for a point in an incorporated place, name who governs it — head of
government, governing body, other elected officers, hall contact, official site — joined
onto the statewide `municipality` card by **7-digit place GEOID** (join precedent:
`il-county-clerks.json` on `county`). Unsourced places keep the identity-only card, so
statewide behavior degrades honestly with no coverage declaration.

**The two-body split** (the `county`/`county-board` shape): whole-municipality officers
ride this card, with a ward-elected city's full council listed ward-badged; *your* seat
is answered by the consolidated `ward` layer wherever ward polygons are published
(SHIPPED 2026-07 — see Tier B below). **The roster carries a per-member `district` field
from day one** (Cook MUNIW and the Will directory supply it) — that is what made the
ward tier a geometry-and-dispatch change with no re-scrape, and the rule holds for every
future county source.

**The five-rung source ladder** (work in order, take the first hit, record the outcome in
the guidebook either way):

1. County clerk elected-officials database/API (Cook's DOEO class — look for an XHR/JSON
   backend before settling for PDFs).
2. Clerk directory/yearbook document (Will's flipbook directory; Kane/Kendall/McHenry
   yearbooks — expect mayor-level depth, full-body if lucky).
3. Council-of-governments / mayors-conference directory (DuPage's DMMC class).
4. County GIS municipal-boundary contact attributes (Lake class — contact-only card).
5. Link-only — the rule-4 floor. Never scrape 50 heterogeneous municipal sites as a
   default (a per-muni upgrade is a deliberate decision, not a source of record).

**Per-county sources, as built** (each scraper names its own source; postures measured
2026-07-28 during the build):

| County | Source | Depth | Fetch class |
|---|---|---|---|
| **DuPage** | DMMC Membership Directory PDF — discover the dated URL from `dmmc-cog.org/membership-list/` (it rotated between research and build: `…/2025/08/…8.4.2025-1.pdf` → `…/2026/05/…5.12.2026.pdf`) | head of government only; **no trustees** (county publishes nothing municipal — verified negative) | clean fetch; 4-column text PDF, annual |
| **Kane** | Clerk Government Guide PDF — `clerk.kanecountyil.gov/Elections/Documents/GovernmentGuide.pdf` (stable URL) | head + municipal clerk; **no trustees** | clean fetch; 84-page text PDF, annual |
| **McHenry** | Clerk County Yearbook "Cities & Villages" page — `mchenrycountyil.gov/county-government/county-yearbook/cities-villages` | head + elected clerk/treasurer (+ per-person contact for a few); **no trustees** | Akamai **client-fingerprinted** — see below |
| **Kendall** | Clerk Yearbook & Government Guide PDF — `kendallcountyil.gov/home/showdocument?id=184` | head + clerk + treasurer; **no trustees** | same Akamai posture as McHenry; pypdf |
| **Lake** | **No names published county-side (firm double-verified negative).** Lake GIS Municipalities FeatureServer — `services3.arcgis.com/HESxeTbDliKKvec2/arcgis/rest/services/Municipalities/FeatureServer/0` | hall address/phone/email/website; **no names** → rule-4 branch 3 | open ArcGIS query |

**The counties added since** (2026-07-29 → 07-31), which broke the "clerk yearbooks are
mayor-level" expectation the table above set — **read the yearbook before assuming its
depth**, because three of these five carry whole boards:

| County | Source | Depth | Fetch class |
|---|---|---|---|
| **LaSalle** | Clerk Municipality Officials PDF, linked from `lasallecountyil.gov/294/Officials` | **full body** incl. ward numbers | clean; the one source needing word POSITIONS (`pdfplumber`) — six interleaving columns |
| **Winnebago** | WinGIS `ElectedOfficials` MapServer, **one layer per municipality** | **full body** | open ArcGIS; note `/public`, not `/arcgis` |
| **Ogle** | Clerk yearbook "OGLE COUNTY CITIES & VILLAGES", discovered from the clerk page | **full body** + hall address/phone/website | clean; `pypdf` line extraction |
| **Stephenson** | county Cities & Villages directory page | **full body**, each office marked `(Elected)`/`(Appointed)` | clean static Revize HTML |
| **Carroll** | Clerk yearbook "Cities and Village Officers", discovered from the clerk page | head + clerk | clean; `pypdf`, but see the CDN note below |

**A year-versioned document URL is a scraper with an expiry date.** Carroll's yearbook is
`2025-2026 YEARBOOK.pdf` and Ogle's `2025- 2027 Yearbook.pdf`; both are renamed on
republication, so both are discovered from the clerk page rather than hardcoded — the
DMMC precedent, now the default for any clerk document. Carroll adds a wrinkle worth
expecting on Revize sites: **the discovered link is RELATIVE and resolving it against the
page 404s**, because the site redirects PDFs to its CDN, which serves them from the site
ROOT rather than from the page's directory. Try `<cdn-root>/<filename>` first and the
page-relative form second, and require actual `%PDF` bytes before accepting either — the
404 arrives as a 200-shaped HTML page.

**The Akamai counties fingerprint the HTTP CLIENT, not just its headers** (measured on
both, 2026-07-28, with a byte-identical full browser header set): **curl gets 200 where
python-requests gets 403**. So a complete header set is necessary but not sufficient, and
"add a browser User-Agent" is not the fix — **Playwright is the day-one rung** for these
two, which is why the workflow installs Chromium. Their scrapers still try `requests`
first (cheap, fails fast) and fall back to the Internet Archive, which genuinely does hold
snapshots of the McHenry yearbook path again (2025-03-06 onward). Note for the next
county: measure the rung with the *client the scraper will actually use* — a successful
curl proves nothing about `requests`.

**Three kinds of block, and only two of them have a rung** (taxonomy from the first live
CI run, 2026-07-28 — the run that took six of ten scrapers and blocked four). Read the
response *headers and body size* before writing anything, because they tell you which
one you have and therefore whether a rung can exist at all:

| Block | Signature | Beaten by |
|---|---|---|
| **Challenge** | Cloudflare; 403 or a 200 interstitial ("Just a moment", `cf-browser-verification`) | a browser rung — there is something to solve |
| **Network deny** | same request, 200 from a developer machine and 403 from a CI runner | a browser rung **only if** a challenge sits underneath (DuPage: it did) |
| **Hard WAF deny** | Akamai; small static body (~408 bytes) with `x-reference-error` | *nothing* — Joliet's browser rung fails identically to `requests` |
| **Reputation score** | SiteGround; HTTP **202** (not an error status), ~220-byte body, `SG-Captcha: challenge`, refresh to `/.well-known/sgcaptcha/?…&y=ipr:<CALLER IP>` | changing the CALLER, not the request — see §3.5.1 |

A hard deny is rule-4 terminal: record it, keep whatever rungs exist so the source
resumes automatically if the edge relaxes, and let preservation carry the data. Do NOT
reach for the Archive reflexively — evaluate it, then say what you found. Joliet's
captures are *good* (the archived index still yields all nine bio links, the bio pages
still carry their e-mails) and it was still declined, because the newest index capture
was 69 days old against the 45-day guard: a conventional rung would refuse every run,
and widening the guard for one source spends a fleet-wide honesty rule on data that
preservation already covers — a last-good entry scraped from the real site beats a dated
copy of it. **The guard is the point, not an obstacle to route around.**

**Two source defects worth expecting elsewhere.** DMMC prints phone numbers with **no
area code** and states no default, so DuPage ships `phone: null` rather than a dead
`tel:` link — per-field honesty beats a completed guess. Kendall's yearbook misspells
Minooka as "Minnoka"; the scraper carries an explicit, reviewable alias so the place
still joins its Census GEOID. Correcting a place NAME to make a geographic join is not
the same as inventing officeholder data — no person's name is ever altered.

**Appointed officials ship FLAGGED, not excluded — and there are two different kinds.**
The original rule here was exclusion, on the reasoning that the card's officers section is
titled "Other Elected Officials" and an appointee under it would be mislabeled. The
five-county build reversed it: several sources print village administrators, city
managers, deputy clerks and superintendents beside the elected officers, and dropping them
loses real officeholders a resident may need to reach. They ship with `appointed: true`
and the card renders an explicit **Appointed** badge on the row. 78 such records ship
today across Cook, Will, LaSalle, Ogle and Stephenson.

The two kinds are not interchangeable and both need the flag:
- **An appointed OFFICE** — city manager, administrator, deputy clerk, superintendent.
  Never elected by anyone.
- **An elected office held by an APPOINTEE** — Cook ships 7 trustees, 4 alderpersons and
  a mayor appointed to fill vacancies; Stephenson's page marks 3 trustees `(Appointed)`.
  The seat is elective; this person did not win it.

**Only mark appointed where the source says so.** Stephenson marks 66 of its 86 rows
explicitly, which is the strongest signal any source in this file publishes; the other 20
ship with **no** flag rather than an assumed "elected". Where a source marks nothing, the
office title is the only guide, and the known-appointed title set is the
whole of it. (CORRECTED 2026-09-02: that set is per SCRAPER — `APPOINTED_TITLES` in `scripts/lasalle_municipal_officials_scraper.py`, Henry's and Livingston's — and the builder only copies the flag; nothing in `scripts/build_municipal_officials_roster.py` carries one.)

**The section header follows what the section holds** (fixed 2026-07-31; it was a fixed
"Other Elected Officials" for as long as appointees have shipped, which stated something
false on 40 municipalities — 25 of whose officers are appointed to the last one). The
label is `municipalOfficersLabel()`: none appointed → *Other Elected Officials*, all
appointed → *Appointed Officials*, mixed → *Other Officials*. **The generalizable rule:
when a data change starts putting new kinds of record into an existing section, the
section's fixed heading becomes an unreviewed claim about them.** A per-row badge is
necessary but not sufficient — a reader takes the heading as the category. Check the
headings whenever a source widens what a section can contain.

(Shipped-county sources, for reference: Cook = the Clerk's Directory of Elected Officials
JSON API, `cookcountyclerkil.gov/api/ElectedOfficial/GetByJurisdictionType?id=MUNIS` +
`id=MUNIW` for ward alderpersons — its Socrata copies are 2014-frozen, never use; Will =
the Clerk's "Will County Directory" FlipHTML5 flipbook, discovered from willcountyclerk.gov
nav, never a hardcoded book id.) **Statewide aggregators are a verified dead end** (IML
paid print; the Comptroller's "CEO" is often the appointed manager; Google Civic reps
endpoint sunset) — per-county clerk sources are the only honest architecture.

**Merge & precedence (the 47 multi-county municipalities):** key by place GEOID via the
Census place-by-county file (`st17_il_place_by_county2020.txt`, copy under
`data/source/`); dedupe to the **deepest** source — full body (2) > head-only (1) >
contact-only (0) — county order breaks ties only at equal depth. Never blend member lists
from two sources; record the winning `sourceUrl` per entry. The builder refuses to write
if the dropped entry had a board and the kept one didn't.

**Roster schema + shape decisions the Cook/Will builds settled** (inherit them):
`{ "<geoid>": { name, county, head?, board?: [{name, role, district?}], officers?,
office?: {address?, phone?, email?}, url?, sourceUrl } }` — people keys **omitted
entirely** where the source names nobody; contact is municipality-level (verified: Cook's
per-person phone/email columns are empty for all 1,134 records) and renders once on the
hall row; head/board/officers stay separate sections so a mayor-level county ships a
`head` with no `board` honestly; **Library Trustees are excluded** (they sit on
`library-district` boards, not the municipal body). Two shape additions from the
five-county build: **per-person `phone`/`email` ride the person** where — and only where —
the source publishes them per member (McHenry prints a direct line or office e-mail for a
few officials); a "personal" number equal to the village-hall line is dropped, because
carrying it would imply a direct line the source doesn't publish. And **`nextElection`
(a year) rides the person** where the county publishes it (Cook: 100% of records):
municipal terms are STAGGERED — 103 of suburban Cook's 104 village boards mix two cycles —
so "when is this seat next on the ballot" varies seat by seat and is exactly what a
resident wants; the card drops a year already past rather than calling a stale seat's
election "next".

**Count floors: three per county (municipalities / members / heads), each a deliberate
under-tolerance against measured live values** — ordinary turnover passes, a coverage loss
fails and leaves the last good file in place. Built: cook ≥120 · will ≥30 · lasalle ≥22 ·
winnebago ≥10 · ogle ≥11 · stephenson ≥9 · dupage ≥32 · kane ≥26 · mchenry ≥26 ·
kendall ≥12 · carroll ≥6 · lake ≥48, with a merged total ≥250 (built: 349). Three rules
the floors themselves encode:
- For a **head-level** county the member floor must sit ABOVE the head count, or a run
  that silently lost every clerk still passes.
- **A head floor may legitimately sit below the municipality count**, and writing it flush
  would fail on correct data: Winnebago publishes no mayor layer for Loves Park or
  Machesney Park, Stephenson's page lists no president for Dakota, Carroll's Thomson
  presidency is vacant. Say which municipality and why, beside the number.
- **A small county gets a tight floor.** Carroll's whole county is seven municipalities;
  slack that is prudent against Cook's 129 is, at that size, room for a real loss to slip
  through. (The same reasoning set the Carroll BOARD roster's floor at the full nine
  members rather than one under — see the "Distirct" typo in the guidebook.)
- Lake's member/head floors are **0 by design** — it publishes no names, so the
  municipality count is the only real guard there.

**The central city is a municipality too.** Chicago's own card named nobody until
2026-07-28 while every suburb named its mayor — the recorded suburban-parity asymmetry.
The fix needed no new source: the Cook Clerk's directory covers all of Cook (only its
address *search* is suburban-only) and publishes the city's three citywide elected
officers under its own jurisdiction type (`CHIWD`), while the 50 ward seats sit under a
separate type (`CHICA`) and stay the `ward` layer's answer. The card renders the head +
citywide officers and, in place of a 50-row council, a section that says the seats are
elected by ward and points at that layer — an empty section there would read as "this
city has no council". **Check this for every instance:** the reference city is the one
municipality a metro build is most likely to skip, because its council already has a
layer.

**Term data: label it as the source labels it.** Three counties publish three different
term facts and none of them is interchangeable — Cook the next election date, Will the
year a term expires, Kendall the date last elected. They ride the person as
`nextElection` / `termExpires` / `lastElected` and render as "Next election 2029" /
"Term expires 2027" / "Elected 2025". Normalising them into one field would state
something no source says. Two rules that fall out: a *future*-tense fact already in the
past is not rendered (both feeds carry a few stale seats), and where a source publishes
more than one fact, keep only the one the card will show — Cook's last-elected date would
have added ~1,000 unread fields beside its next-election date.

**A fact that appears on two cards gets ONE render helper.** Municipal term data surfaces
on both the Municipality card and the City Ward seat card, and the concept is split by
design — the Municipality card suppresses districted councils, so a ward-elected
resident's own seat exists only on the Ward card. Two copies of the labelling and the
past-year gate would let the same fact drift into two wordings, which reads to a user as
two different claims. Extract the helper the moment the second card wants the fact
(`municipalTermNote()`), rather than pasting the branch.

**Match a fact to the SEAT or to the PERSON, and let that decide whether you need a name
join.** Chicago's term data comes from a different source than its alderperson names (the
City's roster carries contact but no term fields, so the Clerk's `CHICA` type supplies
them). Next-election is the seat's — all 50 wards run on one cycle, so it is true of Ward
43 whoever sits in it, and it needs no name match at all. The Clerk's `appointed` flag is
the person's, and the two rosters format names differently enough (12 of 50 differ by
middle initial, nickname or suffix) that pinning it to the other roster's name would be a
heuristic — so it is deliberately not carried. When two sources describe one seat, sort
each field this way before joining; it usually removes the need for fuzzy name matching
rather than motivating it.

**A multi-source roster build must never gate on a source that can block
permanently.** The municipal-officials workflow originally required all ten
scrapers to succeed, reasoning that dropping a county would delete live
officeholders. The first live run (2026-07-28) showed the cost: four sources
403'd GitHub's runner IPs — McHenry and Kendall block every rung including the
Archive's crawler, DuPage and Joliet answer a developer machine but not the
datacenter ranges — so the build skipped and the roster froze *for every
county*, including six that had scraped perfectly. An all-or-nothing gate over
N sources fails whenever ANY one is permanently blocked, and rule-4's terminal
case guarantees some will be.

The fix is per-source preservation, not a looser gate: a blocked source carries
forward its currently shipped entries (`--preserve` + `--preserved <id>`) while
every other source refreshes. Three properties make that safe to automate —
copy them:
1. **Some sources are not preservable.** Cook and Will are the only
   full-governing-body sources here, so building without either would silently
   ship mayors where councils belong — no count floor would notice, because the
   municipalities all remain. The builder refuses rather than degrade.
2. **Preserved data re-enters through the ordinary merge paths**, so it cannot
   take a shortcut the fresh path doesn't have: a preserved county goes through
   the same cross-county precedence, and a preserved city payload through the
   same `merge_contact` that can only fill fields the county left empty — so it
   can never resurrect a seat-holder the county has since replaced.
3. **Preservation is stated, never silent.** The build prints which sources were
   carried forward and how many entries each contributed, and the PR body
   repeats it: preserved data is shipped but *not re-verified this run*, which a
   reviewer has to be able to see.

Diagnostic note for any workflow using `continue-on-error`: the jobs API reports
a swallowed failure as `conclusion: success`, so a run can look entirely green
while half its steps failed. Read `steps.<id>.outcome` (the result *before*
`continue-on-error`), or the step logs — not the API's conclusion.

**Name the jurisdiction the way the source labels its form of government.** Cook prints
"Village of Alsip"; Kane groups under CITIES/VILLAGES and DMMC tags each entry (V)/(C).
Carrying that into the jurisdiction string is what lets the card title the hall row "City
Hall" vs "Village Hall" — the builder strips the prefix again before joining on GEOID, so
it costs nothing.

**A source that publishes BARE names is no longer a degradation.** That used to fall
through to a generic "Municipal Hall"; since 2026-07-31 the builder takes the legal form
from the **Census reference file's own designation** (`"Rock City village"` →
`"Village of Rock City"`) whenever the source states none. Two sources needed it —
Stephenson's page and Winnebago's GIS layers — and it is not an inference about the place,
it is the Census's own word for it. It applies **only** where the source is silent: a
source that states a form keeps its own wording, because "United City of Yorkville" is
Yorkville's legal name and Census's plain "City of Yorkville" would be a downgrade.

**Three name shapes, and conflating two of them ate a municipality.** The source side and
the Census side label the form on **opposite ends**, and a third class publishes no form
at all:

| shape | example | who writes it |
|---|---|---|
| prefixed | `City of Calumet City` | almost every clerk directory |
| suffixed | `Calumet City city` | the Census place-by-county file, always |
| bare | `Rock City` | Stephenson's page, Winnebago's GIS |

One normalizer stripping *both* ends looks defensive and is wrong in both directions: it
reduced the clerk's "City of Calumet City" to `CALUMET`, and on a bare name it ate the
second word of "Rock City" and left `ROCK`, which matches no Census place — a hard build
failure for the lucky case, and a silent mismatch for any name whose form-word sits
somewhere other than the end. They are now two functions, `norm_census_place()` (suffix)
and `norm_place()` (prefix), and the split was measured before it was made: **no source in
the file emits a Census-style suffix**, so nothing needed the other strip. Abbreviations
are expanded in the shared tail — Carroll's clerk writes "Mt. Carroll" where Census writes
"Mount Carroll" — because that is one word abbreviated, not a different name. *Any
name→GEOID join in a new county should be run over the county's full place list before
shipping; a name that fails to match is loud, but a name that matches the WRONG place is
not.*

**PDF-parse lessons (the Will build was ~10× Cook, all source-format; the PDF counties
will hit the same class):** parse the real PDF with a layout-preserving reader (`pypdf`
layout mode / `pdfplumber`), never a line-flattened rendition. In flattened text: labels
glue to neighbors (match section headers as plain substrings, longest-first — `\b` fails
silently); a repeated section header absorbs into the next name (blank headers before
scanning); "At Large" labels a group, not a seat; names carry nicknames/curly quotes/comma
suffixes (an ALL-CAPS `(IND)` is a party code, not a nickname); officer names need a
greedy-but-bounded pattern (the term-expiry anchor that saves board names is absent);
an undelimitable address returns None — ship no address line rather than a guessed one.

**The bounded per-city exception (Will, 2026-07-28).** Rung 5 says never scrape
heterogeneous municipal sites as a source of record. The one shape that earns an
exception: **the cities whose seats the `ward` layer answers**, because the Municipality
card now sends readers to a per-seat card and that card should be able to name a way to
reach the seat's holder. Will's clerk directory publishes no per-seat contact (only the
municipality's and, sometimes, the clerk's), and its ward GIS carries geometry only, so
the three reachable ward cities' own sites supply it — Crest Hill per-alderperson phones,
Wilmington per-alderperson e-mail. Two rules keep it safe: **the county clerk stays the
roster of record** (a city site contributes CONTACT to a municipality the county already
covers — never adding, renaming, or re-roling a seat-holder; an unmatched name is logged,
not merged), and **a per-person value equal to the municipality's main line is dropped**,
since that is not a direct line. Name matching is surname + given-name overlap or
truncation, falling back to a *unique* surname within that one council and logging when
it does; two possible matches refuse rather than guess.

**Never join on a name that isn't unique in your state.** Illinois has two Wilmingtons and
two Windsors, and a first-match-wins lookup picks whichever the file lists first — that put
Greene County's Wilmington in the ward-coverage file and hid the ward layer in the real one.
Every name→entity lookup is county-qualified, or refuses an ambiguous name; none of them
silently take the first hit. The same rule covers a *key* that isn't unique: a ward number
identifies two people in cities that elect two alderpersons per ward, so the seat lookup
returns all holders, not the first. Both classes fail silently and neither has a gate —
audit them by running the lookup over real data (`docs/DATA_LAYER_GUIDEBOOK.md`, the
2026-07-28 name-collision sweep, records what was checked).

**When the county source silently omits a municipality.** Will's directory drops Lockport
and Wilmington entirely — the flipbook's text layer is missing their entry HEADERS, so the
entry split cannot see them, and no parser recovers text that isn't there. Both are ward
cities, so each resolved a ward polygon with no seat-holder behind it. The same city-site
pass supplies those two rosters outright. **Check for this class after EVERY county build,
document-sourced or not:** compare the scraped municipality list against the county's
Census place list, since a missing entry is invisible in the output — it simply isn't
there.

**The omission can be the COUNTY SEAT, and it can be deliberate.** Will's was a PDF defect;
Stephenson's is editorial. Its page is a *village* directory — all ten villages and not
Freeport, which at ~23,600 people is more than half the county's municipal population.
Nothing in the output looks wrong; the largest city in the county simply has no card. Two
things follow. **Never infer coverage from a page's apparent completeness** — ten of eleven
is a very convincing nine-tenths. And **a source's title is a claim about its scope**: a
page called "City and Villages" that names one city and lists none of it is telling you
where to look next. Freeport enters through the same `--enrich` path as Lockport and
Wilmington, which inserts a municipality the county omits wholesale rather than merely
filling contact. Where a large municipality's own site publishes its body, that is a
bounded rung-5 exception in the Will-ward-cities sense, not a slide toward scraping every
municipality.

**A city running a CMS may publish its roster as an API you can query instead of a page
you must parse.** Freeport is WordPress: its governing body is an `lsvr_person` post type
in an `elected-officials` category, so MEMBERSHIP is a REST query
(`/wp-json/wp/v2/lsvr_person?lsvr_person_cat=<id>`, the id resolved from the category
SLUG, never hardcoded) and a seat that changes hands leaves the category the moment the
city updates it. Each person page then carries a schema.org `Person` JSON-LD block with
name, jobTitle, email and telephone — a machine-readable contract the city publishes
deliberately, and far steadier than the rendered markup around it. **Check `/wp-json/wp/v2/types`
and the page source for `application/ld+json` before writing an HTML parser**; it costs one
request and it turned the metro's fussiest source class into ten clean records.

**Do not blend two labelled addresses.** Ogle's Adeline is the one block that labels a
PHYSICAL and a MAILING address, and they are different places — 8763 vs 9069 N. Main St,
and the mailing city is Leaf River, not Adeline. The scan took the street from the first
address-looking line and the city/ZIP from the first line carrying one, producing an
address that appears on no document the county publishes. Twelve of the county's thirteen
blocks *do* spread one address across several lines, so combining across lines is right —
the rule is to combine only WITHIN a labelled group. Prefer the physical address (the hall
is where the office is); if it carries no city, leave the city empty rather than borrowing
the mailing address's. The same pass found Rochelle's `61068-0601` failing a `\d{5}$`
anchor, which had been silently dropping that city's entire locality: **anchor ZIPs with
the +4 optional.**

**An officer list contains things that are not officers, and names that are not people.**
Three classes, all of which would have shipped:
- **A separate body printed alongside** — Davis's zoning board of appeals, German Valley's
  hired village police. Appointed members of a different body; on a "who represents you"
  card they are people holding no municipal office.
- **A placeholder in the name column** — "Vacant" (Carroll's Thomson president),
  "Unassigned" (German Valley). A card must never print one as a person's name. Thomson
  ships with no head, which is the accurate answer.
- **A combined title** — "Trustee/Zoning Chairperson" is a sitting TRUSTEE who also chairs
  zoning. Filtering on the substring "Zoning" would have dropped a real board member, so
  the title is reduced to the municipal seat it names and only a title that reduces to
  nothing is dropped.

Drop them, but **report every drop** — the count belongs in the run summary, so a source
that starts printing a new body is visible rather than quietly filtered. The same applies
to a row the source itself leaves incomplete: Dakota has a resident's name against a blank
office cell and is also the one village listing no president, which makes the inference
obvious and still wrong to make. It ships nowhere, the run warns, and the guidebook
carries the gap.

**When the county and the county's GIS disagree, the municipality is the tiebreaker.**
Cook GIS mapped four Skokie trustee districts while the Clerk's directory listed all six
trustees as municipality-wide — a district polygon with nobody attached. Neither source
was lying: Skokie moved to four districts plus two at-large in April 2025, the GIS
followed, and the Clerk's feed simply doesn't carry the assignment. The village's own
site is the authority on its own districting, and it is the only thing that settles which
side is stale. A municipality with ward geometry and no districted seat in the roster is
that smell; the builder now warns on it against `municipal-ward-coverage.json`.

**Re-test a recorded "unbuildable" before believing it.** Joliet was skipped as
unbuildable — joliet.gov 403'd every client tried, jolietcity.org looked client-rendered,
and the only Archive snapshot was four years stale. Re-tested a day later, both premises
were wrong in instructive ways: the 403 was the same **client fingerprint** as the Akamai
counties (a complete browser header set gets 200, so Playwright carries it), and
jolietcity.org is not the city's site at all but a parked domain serving a redirect stub.
The city publishes a council index plus a page per member, each with a direct phone and
e-mail. A non-build record is a snapshot of what was tried, not a property of the source;
re-testing one costs minutes.

**Budget for per-page layout drift within a single site.** Joliet's nine bio pages use
four shapes: the mayor has no seat line where members do, one member's seat rides inline
after the name ("…Quillman, At-large"), one member's e-mail is split across two lines
mid-token, and one member's URL lacks the "-bio" suffix every other page has — that last
one silently dropped him until the link pattern was widened. Anchor on the stable element
(here the e-mail address) and walk outward, rather than trusting fixed offsets, and make
the count floor the real roster size so a dropped member fails the run.

**A count floor cannot see a swap, and two of them shipped (2026-07-31).** Ogle's
yearbook parser passed its floor of 90 officials with 114 — while ten of those "officials"
were sentences off the following page ("Other Special Districts", "www.census.gov") and
the county's largest city was missing its entire council. The two errors ran in opposite
directions, so no total moved enough to notice. Both were the same class of mistake: a
parser right about the record SHAPE and wrong about where the shape STOPS. Two habits
come out of it, and both are cheap:

- **Bound a section by the next structural marker, not by the next heading you happened
  to notice.** The end sentinel named the POLLING PLACES heading; GENERAL INFORMATION sat
  between, its content was indented, and an open group accumulator ate it. The bound is
  now "the next ALL-CAPS heading of any kind" — and it was *measured* before it was
  adopted (four matching lines in the whole book, the first is the right one, none inside
  a municipality block). A sentinel you have verified beats a sentinel you have guessed,
  and a structural rule beats both.
- **Read the built file back, grouped, before you ship it.** One `collections.Counter`
  over board sizes per municipality showed a village with sixteen trustees and a city of
  9,600 with none. Every count guard in the pipeline was green. Add this read to any pass
  that touches a roster: per-key sizes sorted, eyes on the extremes.

**A group-heading vocabulary is a list of words, and the list is never finished.**
Rochelle's six seats are printed under "Councilmen". The parser knew Trustees, Council
Members, Commissioners and Aldermen. One missing word cost a whole council silently,
because an unrecognised heading is not an error — it is just a line that matches nothing.
Where a parser keys on a closed vocabulary, either warn on an unmatched candidate line or
assert that every municipality yielded a board; a floor over the total will not do it.

**Two source rows can contradict each other, and "which is right" is sometimes
answerable from law rather than from data.** DeKalb's yearbook prints Hinckley's Sarah
Quirk as Village President AND as a Trustee. Illinois elects a village president to that
office separately, and no one holds both seats at once, so exactly one row is stale —
that is a fact about the offices, not a guess about the person. The head row wins (the
more specific claim), the board row is dropped with a log line, and because the village
is then one trustee short of its six, the shortfall is RECORDED as a gap rather than
absorbed. The general rule: when a source is internally inconsistent, prefer the reading
that a structural fact settles, drop the other loudly, and record what the drop costs.

**Ask a served county what it still publishes — the answer is often "a lot".** DeKalb had
been a dispatch county for five concepts and its clerk was publishing, untouched, the
richest municipal document in the fleet: all 14 municipalities' full governing bodies
with each seat's NEXT ELECTION date. Expansion attention naturally goes to the next
county; the cheaper win is frequently the one already inside the ring.

**Discover an annually restamped document from the page that links it, and anchor headings
to whole lines.** DeKalb's yearbook lives on the CLERK's domain under
`/wp-content/uploads/<year>/<month>/`, and is linked from the COUNTY's reference page.
Hardcoding the stamped path goes stale in a year, so the scraper reads the link (the
Carroll/Will pattern). And its two section headings appear TWICE in the book — once as
the section, once in the index followed by dot leaders — so a substring search bounded the
section to a few characters of dots. Match headings `^...$`.

**Roster ahead of geometry is as common as the reverse, and it is the cheaper half to
finish.** Five cities in this pass — La Salle, Peru, Earlville, Byron, Polo — already have
every alderman in `municipal-officials.json` from their county clerk, keyed by ward, and
publish no ward polygon anywhere (La Salle's ward map is a PNG). The moment any of them
publishes geometry, the card names its seats with no roster work at all: DeKalb's four
cities and Mendota went from nothing to named seats in one change because the roster was
already there. When adding a county's municipal roster, capture the ward numbers even if
no geometry exists yet — that is the half that makes the other half free.

**Tier B — suburban municipal wards (SHIPPED 2026-07).** Shipped as **entries of the
existing `ward` layer**, keyed by municipality (§3.1) — one toggle, one concept, whether
Chicago calls it a ward or Joliet a council district. Sources: Cook GIS
`politicalBoundary/MapServer/22` "Municipal Ward" (21 suburbs incl. Skokie's 2025
trustee districts; joins the DOEO MUNIW roster — same publisher); Will GIS
`Ward_Districts` (Joliet/Lockport/Crest Hill/Wilmington); Evanston + Aurora
self-publish. Seat-holders join `municipal-officials.json` by municipality + seat
number; per-seat contact renders ONLY where a source carries it per-member (Evanston) —
the roster's shared hall line on an individual's row would be a false implication.
Verified negatives, standing for future counties: no county-level ward layers in
Lake/DuPage/Kane/McHenry/Kendall (Waukegan is PDF-only) — a new county's ward-electing
suburbs join as further `ward` entries when a polygon source appears.

## 3.5 The county-N+1 checklist (one change-set)

**STEP ZERO, ADDED 2026-08-08 AFTER GETTING IT WRONG TWICE IN ONE DAY: SEARCH THE WEB
FOR THE COUNTY BEFORE PROBING ANYTHING.** Not a hostname sweep, not the ArcGIS Online
catalogue — an ordinary search engine query, the thing any member of the public would
type. Both failures below were found by the operator in seconds that way, after this
project had spent hours on careful measurement of the wrong server:

- **Morgan** was recorded as publishing its commissioners "nowhere a machine can read",
  on the strength of a thorough teardown of morgancounty-il.GOV — a client-rendered
  React shell with an empty backend. morgancounty-il.**COM** is the county's real site
  and publishes all three with role, party, term dates and personal e-mails. A search
  returns it first.
- **Jersey** was recorded as having no district boundaries at all. jerseycountyclerk-il.
  **gov** — the CLERK's own domain, distinct from the county's — has a MAPS section
  with a vector County Board Districts map. A search returns the PDF directly.

The rule the two share: **a county is not a domain.** The clerk roster gives you where
the CLERK is; the county may run a second site, the clerk may run their own, and `.gov`
and `.com` can coexist with entirely different content. Enumerate the county's WEBSITES
before concluding anything about what the county publishes. Cheap follow-ons worth
doing in the same minute: read the strings inside a site's own JavaScript bundle for
other hosts it knows about (Morgan's named the .com), and search for the artifact rather
than the county ("<county> Illinois county board district map"), which is what surfaced
Jersey's PDF.

**AND BEFORE EVEN SEARCHING, READ THE CLERK'S E-MAIL ADDRESS.** The 2026-08-09 resweep
of the fourteen counties recorded as having no website found NINE of them, and for nine
counties **the Clerk's e-mail domain IS the county's web domain** — a fact sitting in
`il/data/app/il-county-clerks.json`, scraped weekly from ISBE, for the whole time those
records claimed no site existed. This project was e-mailing those counties at those very
domains on 2026-08-05 while telling readers they had none. So step zero has a step
minus-one, and it costs one line:

    domain = clerk_email.split("@")[-1]      # try https://<domain> and https://www.<domain>

The name-permutation sweep failed because it permuted the COUNTY'S NAME. Counties do not
name their domains predictably — the resweep found `gallatinCO.illinois.gov` and
`colesCO.illinois.gov` (abbreviated), `clarkcountyil.ORG` (a TLD never tried),
`shelbycounty-il.gov`, `whitecounty-il.gov` and `popecountyil.com` — but their CLERKS'
addresses are already known, correct, and maintained by someone else.

Verify every hit before recording it — search results carry the same decoys the rest of
this guide warns about. The resweep alone turned up a Scott County TENNESSEE address, a
Cumberland County MAINE site, a Crawford County *Development Association*, a Shelby
County *real-estate agency* and a Gallatin *weather* page. Confirm a hit is the county
government — look for the clerk, board, sheriff and treasurer — before it goes in a
record.

**"Unreachable from here" is not "does not exist."** Coles publishes two sites and both
refuse this network; Pope's answers 503. Search engines index all three. Record the
distinction the way the Wabash entry does — it is the one of the fourteen that was
exactly right, because it was written from a Clerk's reply and a measurement rather than
from a failed guess.

**Never write "the county publishes no X" into a gap record, and above all never write
it to the person who maintains the source, without having searched.** It is a claim
about the world that is very often a claim about the search.

1. Coverage outline (TIGER county boundary → pre-built outline file) **and the scope
   mask in the same step**: add the county to `DISPATCH_COUNTY_FIPS` (slug → Census
   FIPS) and its FIPS to `METRO_COUNTY_FIPS` in `scripts/build_metro_outline.py`, give
   it an INSIDE anchor, drop it from OUTSIDE if listed, and rebuild.
   **This is now enforced** — `validate_index.py` check 8 reads the county keys out of
   index.html's own dispatch tables and fails the merge gate if one is missing from
   either table, so the county cannot ship greyed-out. Before that check existed the
   only guard was the OUTSIDE anchor list, which catches a county only if someone had
   already thought to name it; LaSalle, Kankakee, Boone and Grundy each shipped layers
   and stayed washed out for two research passes with nothing failing.
2. `county-board`: districted → dispatch entry + officeholder story; **at-large →
   county-card roster rows** (§1.5). Decide and record which, from a certified election
   document rather than from the board page's silence (§3.5.1). The at-large path is
   implemented: add a `SITES` entry + parser to `scripts/il_county_commissioners_scraper.py`
   and a seat count to `EXPECT_MEMBERS` in `build_county_commissioners.py`, so the county
   lands in `il/data/app/il-county-commissioners.json`, which the COUNTY card already reads —
   no dispatch entry, no toggle (§3.5.1; Monroe/Randolph are the reference pair, the
   tranche-5 four the larger case). If
   the board IS districted but the county publishes no boundary, check whether it
   publishes a COMPOSITION (whole townships or whole precincts) and derive from that, with
   the §3.5.1 drift check wired if the composition lives on an HTML page.
3. `judicial-subcircuit`: entry if the circuit has PA 102-0693 subcircuits; structurally
   n/a otherwise (Kendall precedent — record it).
4. `fire-district` / `park-district` / `library-district`: entries per available tilings
   (`polygonCountyEntry` adapter); municipal rows per the complete-tiling rule; gaps
   recorded (McHenry-park precedent).
5. `county-precinct`: entry keyed to the county's election authority; polling-place join
   where published (Kendall's GlobalID join is the model); carve out any municipal
   election commission the county contains.
6. `tif-district` (post-conversion): entry where the county publishes a tiling.
7. Municipal officials: the county's ladder rung (§3.4), keyed by place GEOID; township
   sections captured in the same scrape where the source prints them. Where the county
   or its cities publish suburban ward polygons, they join the consolidated `ward` layer
   as municipality-keyed entries (rebuild `municipal-ward-coverage.json` via
   `build_municipal_ward_coverage.py`).
8. County officers: the clerk row is automatic (ISBE, statewide); further officers per
   rule 4.
9. Statewide layers (`county`, `township`, `municipality`, `school-district-*`, chambers,
   `zip-code`): **nothing to do.**
10. Bookkeeping + gates: §6.1 worksheet entries and regeneration, §6.3 pipeline
    artifacts per new roster, §6.5 gates, guidebook coverage-map/inventory/matrix
    rows, smoke ground truth if the county adds an anchor — and regenerate the
    per-county completion table (`python3 scripts/build_county_status.py`, emitting
    `docs/COUNTY_STATUS.md`; its `--check` in smoke-test.yml fails the merge if the
    table lags the county change).

**Layer-count check: unchanged** — if a step wants a new toggle, run §1.6.

### 3.5.1 Rules earned county by county (2026-08-02 onward)

Each of these cost a real build. They apply to any county in any state, not just the ones
that taught them — the wording is Illinois's because Illinois paid for them. **Part 5 is
the cross-state synthesis**; this section is the county-work detail behind it, and where
the two overlap Part 5 is the shorter statement of the same rule.

- **A COUNTY THAT PUBLISHES ITS PARCEL LAYER UNDER A DISTRICT'S NAME HAS PUBLISHED THE
  DISTRICT.** Ask this before writing any county off for want of a boundary layer, and ask
  it of the PARCEL layer specifically — the sweep that misses it is the one that searches a
  county's catalogue for a *district* dataset, finds none, and stops. Woodford's record sat
  shut for five weeks saying its "Fire Protection Districts" service "returns 25,824
  records, one per parcel of land … it publishes the individual parcels instead of the
  combined district" — an accurate measurement and the wrong conclusion, because a dissolve
  is exactly what turns one into the other. Two shapes, easiest first:
  - **A SCREENING REGEX OVER FIELD NAMES IS NOT A FIELD LIST.** Whiteside's 70-field
    parcel layer was recorded as carrying no district or tax-code column on the strength
    of a pattern match for `fire|librar|park|dist|code|tax`. Its tax code is `CVTTXCD` —
    138 distinct five-digit values on 36,267 of 36,499 parcels — and it matches none of
    those tokens, because the column is named for the civil taxing unit and abbreviates
    "code" to `CD`. A regex is a way to rank a field list for reading, never a way to
    conclude one is empty. Read all of it; 70 names is a screenful.
    **THIS HAPPENED TWICE IN ONE DAY AND THE SECOND TIME WAS OVER HOSTNAMES**, which is
    what makes it a class rather than a field-naming quirk: the same pass screened
    Livingston's home page for `gis|arcgis|map|beacon|devnet|schneider|parcel` and reported
    NO GIS HOST, on a page linking `livingston.illinoisassessors.com` and
    `livingstoncountyiltax.us` — neither of which contains one of those tokens. Twenty-seven
    hosts; print them.
  - **The parcel carries the district's NAME** (Woodford: `Fire_Prote`, `Library_Di`,
    `Park_Distr`; Grundy: one comma-separated `Districts` field listing every body a
    parcel pays into). Nothing is transcribed and nothing is hand-mapped — dissolve the
    column.
  - **The parcel carries only a TAX CODE** (Boone). Then you also need the Clerk's
    "Taxcode Value within District Report" to say which codes pay into which district,
    and that report is hand-transcribed and pinned.
  Either way `scripts/build_parcel_fabric_districts.py` already holds the machinery — the
  75 ft road-void closing, the contested-seam rule, the probe gates — so a new county is a
  config entry, not a script. **Corroborate the district SET against a second county
  document**, never against the same layer restating itself: the Clerk's certified tax
  settlement sheets name and levy for exactly the districts that should come out.
  **Count the holes in PEOPLE, not acres.** Woodford's fire tiling covers 96.9% of the
  county and the largest gap by area is the Illinois River, which tells you nothing;
  against the county's own 16,889 address points, 1,738 of the 1,900 that land outside
  every district are one village that runs its own fire department and 83 sit on ground
  the county's fabric has no parcel for. The first number is a fact about water and the
  second is the answer.
  **And make the builder refuse a mislabelled column.** A source whose shipped value is
  not its column's own value must declare `out_prop`. Woodford shipped under `Fire_Prote`
  while the app read `district`; every static gate passed, every card rendered, and every
  district name read "Unknown" — caught only by looking at it in a browser.
  **When only the NARROWER document exists, test it against itself.** Boone's build takes
  its code sets from the Clerk's *Taxcode Value within District Report* because her
  *District Rates by Taxcode Report* is a rate list, not a membership list — read as one it
  omitted twelve of Boone's codes on 956 parcels. Whiteside publishes only the rates
  report, and a county that publishes only the narrower document is not automatically shut:
  that document has an internal arithmetic. Each tax-code block prints every levying
  district's rate and then the code's own total, so a district omitted from a code leaves
  the sum short — and Whiteside's 140 codes balance to four decimals across 1,140 rate
  lines, 140 of 140. Rule out the one omission arithmetic cannot see, a district present at
  0.0000, by checking whether the document prints zero-rate lines at all (Whiteside prints
  16, over 12 districts, one of them a village). **And do not promote a check that fails.**
  The obvious second witness here — summing the parcel layer's assessed value per district
  against the computation report's County Total EAV — runs +12% to +32% on twenty-one
  districts and negative on four, because a current assessed value and a tax year's
  rate-setting EAV are different quantities. Record that it does not work, so the next
  reader does not re-derive it and so nobody mistakes it for corroboration.

- **FETCHABLE IS NOT LICENSED. Read the publisher's terms before you build, and treat
  the answer as part of "is there a source?"** This is now step zero of county research,
  ahead of every technical probe. Champaign and Piatt were surveyed as BUILD-READY —
  their board districts and precincts answer instantly once a `Referer` header is set —
  and they are not buildable at all: the Champaign County GIS Consortium **sells** both
  counties' GIS data under signed licence agreements, and its Terms of Use grant only a
  personal, non-commercial, *transitory viewing* licence under which you may not copy the
  materials, use them for any public display, or "transfer the materials to another
  person or mirror the materials on any other server". A dispatch entry does all three.
  The referer check was therefore the EDGE OF A LICENCE, not hotlink protection to route
  around — and the technical ease of setting a header is exactly what makes this failure
  mode dangerous, because nothing breaks and nothing warns.
  **Concretely:** when a source is gated by anything (referer, token, login, a portal
  app), find out WHY before you find out how. Check the publisher's terms-of-use,
  data-request and store/pricing pages. A publisher that sells the layer, requires a
  signed agreement, or forbids redistribution is a **licensing block** — record it as a
  gap of kind `blocked`, ship the gap-location outline, and route the unlock to whoever
  holds the underlying PUBLIC RECORD (for election geography that is the county clerk as
  election authority, whatever a consortium licenses commercially). Never "solve" it by
  supplying the header. The same instinct applies to a county GIS office that runs a paid
  data-order form (the Jo Daviess shape) — same block, same route out.
  **And the route out WORKS — Jo Daviess proved it on 2026-08-17, the first
  licence-gated county ever cleared.** Its licence's redistribution clause was
  the Bureau clause with a valve ("without permission from JoDavGIS"), the
  permission was asked for BEFORE anything was signed or paid, the IT/GIS
  Director authorized display on chidistricts.com in writing, and only then
  did the operator sign and pay ($33.50, licence #008382). Two knock-ons for
  any county cleared this way: the RAW dataset stays OUT of data/source/raw
  (retained offline; the builder records byte sizes + sha256 per component —
  a deliberate, documented deviation from the archive convention), and the
  licence's Credits clause is honoured ON THE CARD, not just in the builder.
  The order of operations is the whole lesson: Bureau's $150 quote is still a
  block because its permission e-mail does not exist yet.

- **AND THE INVERSE, WHICH COSTS A WHOLE LAYER WHEN YOU GET IT WRONG: "ALL RIGHTS
  RESERVED" ON AN ITEM CAN BE THE TEXT OF A REQUIRED NOTICE RATHER THAN A REFUSAL OF
  USE.** The rule above says read the terms before you build; this is the same rule
  pointing the other way, and it is easier to miss because stopping *feels* like the
  careful choice. The City of Des Moines's ward layer (2026-08-28) carries item
  `licenseInfo` opening "© Copyright City of Des Moines, Iowa 2025. All rights
  reserved." Read alone that is the Piatt answer — an assertion of rights with no grant
  — and this project nearly recorded it as a licensing block. The city's own **Terms and
  Conditions of Use** say the opposite: applications using its portal data "must include
  the following disclaimer", and then quote that same string. The city contemplates
  applications using the data and states one condition for doing so. **An item's
  `licenseInfo` is where the licence lives; it is not always where the GRANT lives**, and
  a copyright notice quoted as a required attribution reads character-for-character like
  a copyright notice asserted as a prohibition.
  **Concretely:** before recording a `blocked` gap on the strength of a rights string,
  look for the portal's own terms/licence page — on an ArcGIS Hub site it is a page item
  the site config names (`slug: "terms"`), reachable through the sharing API even when
  the site itself renders client-side. If the terms impose a CONDITION rather than a
  prohibition, satisfy the condition and ship: Des Moines's disclaimer travels **in the
  data file** and renders **on the card**, not only in a builder comment a reader never
  opens, and the layer's worksheet row quotes it so the sources page carries it too.
  Watch for what else those terms say — Des Moines's include a **Right to Discontinue
  Feeds** clause, which is why that layer's weekly workflow re-fetches the service
  instead of assuming a pre-built file's source persists.

- **An AT-LARGE board is county-card rows, and the mechanism now exists — use it.** §1.5
  called this shape long before anything implemented it. Monroe and Randolph (2026-08-02)
  are the reference pair and Pike, Brown, Calhoun and Putnam (also 2026-08-02) the larger
  case: every one elects its board countywide, so there is no geometry for `county-board`
  to join and inventing a district would misstate how the county elects. Their members ride the COUNTY card via `data/app/il-county-commissioners.json`,
  keyed **exactly like `il-county-clerks.json`** (uppercase letters only) so the card
  performs one lookup shape for both rosters. Adding such a county is: a `SITES` entry
  plus a parser in `il_county_commissioners_scraper.py`, and nothing else — no dispatch
  entry, no toggle, no coverage function, no new fetch in the app. The county card grows a
  "County Board" section only for counties that appear in the roster, so a districted
  county's card is untouched (assert this against Cook when you add one). Three knock-ons
  to remember:
    - such a county's PRECINCT card must NOT carry a County Board District row (there
      isn't one);
    - it still needs its **coverage outline**, a **`METRO_COUNTY_FIPS`** entry and an
      **INSIDE anchor**, because a county-specific layer does answer there — the County
      card. The outline ships flagged `dynamic_reference: true`, since index.html names no
      loader for it (the gaps panel fetches it by slug);
    - **CORRECTION, 2026-08-02.** This bullet used to end "and the county still needs its
      `DISPATCH_COUNTY_FIPS` entry if any other layer answers there." Read the condition
      carefully: add the county there **only if it really does register a dispatch entry**.
      Monroe and Randolph do (precincts, fire), which is what made the old wording look
      safe; Pike, Brown, Calhoun and Putnam do not, and adding them would be wrong.
      **This is now a gate rather than a warning.** When the mistake was found, nothing
      caught it — `validate_index.py`'s coverage-ring check only ever looked from
      index.html outward, so a `DISPATCH_COUNTY_FIPS` row with no dispatch entry behind it
      passed silently. The check now runs both directions and fails on a listed county
      that registers nothing, naming the at-large case in its own error message. It
      doubles as a module-loss guard: a county whose dispatch entries are dropped or
      retargeted now fails too (both cases negative-tested).

- **A board whose districts elect DIFFERENT numbers of members balances per MEMBER, not
  per district — check the wrong one and you will reject a correct build.** Cass
  (2026-08-02) seats eleven members as 3/3/3/2. Its correctly-transcribed districts are
  **28.8% apart per district** — past any sane guard, reading exactly like a botched
  transcription — and **12.3% apart per member**, an ordinary rural apportionment. Before
  writing a population check, get the SEATS PER DISTRICT from the county's own roster page
  and divide by them. Do not assume every district elects the same number; that held for
  the first thirty-five counties and then stopped. If the per-member spread is still wild,
  *then* suspect the transcription.

- **A DERIVED boundary must watch the source it was derived from, or it will silently
  rot.** Every derived boundary shares one failure mode: the county edits its composition,
  the compiled table does not, and the app keeps drawing superseded lines with nothing
  failing. That is exactly how the LaSalle defect survived years. Where the composition
  lives on an HTML page the roster is already scraped from — De Witt and Washington,
  2026-08-02 — wire the check: have the scraper emit the composition it read, and have the
  ROSTER builder compare it against the table compiled into the boundary builder and
  **fail** on any difference. The weekly roster job then turns red on a redistricting.
  Cost: a few dozen lines. Two rules learned building it:
  - **Compare at the granularity the districts actually differ at.** De Witt's first
    version compared township names and passed a simulated "Clintonia 7,8" against a
    shipped "7,8,9" — the likeliest change there is, in a county where one township's nine
    precincts split across three districts. Parse to precinct level and compare sets.
  - **Prove it bites.** Write the negative tests (a unit lost, gained, renumbered, and a
    whole township moved) and watch each one fail the build before you trust it.

  Where the composition lives in a PDF the page merely LINKS, this check is not available.
  Find the weakest real substitute and be explicit that it is one — Cass's roster page
  publishes its SEAT COUNTS, which are the input its population test depends on, so the
  weekly build asserts those instead; a reapportionment almost always moves a seat. It
  cannot catch a redraw that leaves every district the same size. Say exactly that in the
  builder's header and the workflow's, rather than leaving a reader to assume the same
  protection.

- **A county that publishes its board TWICE will eventually disagree with itself, and
  you must decide which surface wins BEFORE you look at the numbers.** Tazewell's GIS
  seats a member its own website no longer lists and omits one who has his own member
  page; the website in turn puts a member in a district the GIS contradicts. The rule
  that survived scrutiny: **the surface that is demonstrably stale about WHO is on the
  board does not get to decide WHICH DISTRICT anyone represents — but it may still fill
  a district the fresher surface leaves blank, because filling a silence overrides
  nothing.** Record both values on every record (`districtSource`, plus the other
  surface's claim) and LOG each divergence in the scraper, so a county fixing or
  breaking its own page shows up in the weekly run rather than silently changing data.
- **Never let a count guard launder a disagreement into a decision.** Tazewell's two
  surfaces imply 7/7/7 and 7/8/6. A builder that enforced equal district sizes would
  have "resolved" the conflict by discarding the county's own current claim — which
  is exactly the kind of tidy arithmetic that reads as authoritative and isn't. Gate on
  what the sources AGREE about (here: 21 district members plus a countywide chairman)
  and leave the rest visible. If the county fixes its page, the file corrects itself.
- **Two layers can draw the same lines and still not be interchangeable.** Peoria's
  roster-carrying `ElectoralDistricts/3` and its `2020_County_Board_Districts` agreed at
  8/8 point tests; only the latter carries the per-district 2020 populations that PROVE
  it is the adopted map. Prefer the layer that carries its own evidence, and get the
  roster elsewhere. (Corollary: a large constant area ratio between two layers is a
  projection difference, not a geometry difference — point-test before concluding.)
- **A GIS layer can be the roster's SPINE without being the roster.** Peoria's
  `ElectoralDistricts/3` enumerates district → member name, party and member-page URL;
  the member pages carry the phone and e-mail no layer has. Machine-readable enumeration
  + per-page enrichment beats parsing an index page's markup, and gives a free
  cross-check against a third county surface.
- **Match names across county surfaces on surname + first initial, and require the match
  to be UNIQUE.** Prefix matching joins Rob/Robert and Matt/Matthew but NOT Mike/Michael,
  which is how a real member silently failed a cross-check. Uniqueness is what keeps the
  looseness safe; drop ambiguous keys from the lookup table entirely.
- **Read the annotations a source appends to a name, but only the unambiguous ones.**
  Tazewell prints "Jay Hall (R) 2024". The party letter ships (the county GIS
  independently agrees); the YEAR does not, because nothing on the page says whether it
  is a term expiry or an election year. Same page publishes a HOME ADDRESS — never
  collected, per the Madison precedent (a residence is not an office you can visit).
- **A source column that is a LINK belongs in the card's footer, not its body.** Peoria's
  taxing tilings are the fleet's first with a per-district website. `polygonCountyEntry`
  gained `hidden: true`, which captures a column for `primaryLink()`/`when()` without
  rendering it as a row — `query()` populates every keyed field regardless.
- **Test harness, not the app:** when a route-mocked test makes county A's entry answer
  in county B, suspect the mock before the dispatcher. URL needles must name the
  ORG AND SERVICE (`services.arcgis.com/<org>/…/<Service>`); a bare `FeatureServer/2/query`
  matches half the fleet's counties and will feed them the wrong county's polygons.
  Also: block service workers (they bypass `page.route`), and force a real document load
  between points — a hash-only change leaves the previous point's cards on screen and
  silently passes stale assertions.
- **PROVE "AT LARGE" FROM A CERTIFIED ELECTION DOCUMENT. A board page that never
  says "district" is not evidence.** Putting a county's whole board on the County
  card claims that all N members represent every resident. If the county actually
  elects by district and merely fails to publish them, that claim is wrong in the
  worst direction — it tells a reader nine people represent them when one does. The
  page's silence proves nothing; the ballot does. Each tranche-5 county was checked
  against its own canvass or specimen ballot before shipping: Pike's 2024 summary
  names the contest "FOR COUNTY BOARD - AT LARGE" across all 31 precincts, Brown's
  2026 primary shows "COUNTY BOARD MEMBER (VOTE FOR) 3" countywide across all 14,
  and Calhoun's ballot file reads "CO.COMMISSIONER **CWD**". Record WHICH document
  proved it, per county, in the scraper — the next reader should not have to redo
  the search to trust the card.
- **A county can be SERVED with no dispatch entry at all.** The at-large tier is the
  first group whose only county-specific answer is the County card's board section:
  no coverage function, no toggle, no `DISPATCH_COUNTY_FIPS` row. They still belong
  in `METRO_COUNTY_FIPS` with an INSIDE anchor, because that list means "a
  county-specific layer answers here", not "this county has a dispatch entry" — the
  same reason the judicial-subcircuit secondary counties are in it. Their outlines
  ship flagged `dynamic_reference: true`, since index.html names no loader for them
  and they are fetched by slug for the gaps panel.
- **AN IDENTICAL PHONE NUMBER ON EVERY MEMBER ROW IS A SWITCHBOARD, NOT CONTACT.**
  Calhoun prints 618-576-9700 ext. 2 under all five commissioners. Repeating it five
  times implies five direct lines that do not exist, so it is hoisted to the board
  office and shown once. The test is mechanical — collect the distinct numbers, and
  if exactly one covers the whole board, it belongs to the board.
- **A HONEST CAVEAT THAT LEAVES THE READER NOWHERE IS STILL A DEAD END. Say what the
  card cannot answer AND what in the app can.** The whole-board rule above makes a card
  qualify a list it cannot key — Iowa's plan 3 counties got *"one of these supervisors
  represents you, not the whole board"*. That is true, it satisfies the rule, and for the
  18 plan 3 counties whose districts nobody has keyed it is the entire answer a reader
  gets: the list in front of them cannot resolve their question, full stop. Correct and
  useless is a real failure mode, and it is easy to ship because every honesty check
  passes.
  **Concretely:** before settling on a caveat, ask what the app still knows. Iowa's answer
  was sitting one card away — all 40 plan 3 counties ship NUMBERED district geometry, so
  the County Supervisor District card names the reader's district whether or not anyone
  keyed its supervisors, and its own footer links that county's board page. So the note
  became conditional on KEYING rather than on the plan: a keyed county explains its
  district badges, an unkeyed one adds a second row in the card's own "Not shown —
  <reason>" idiom that names the limitation and points at the card that does answer. Two
  smaller things fell out of writing it properly — it counts the board rather than
  assuming five ("one of these three" in a 3-seat county), and the keyed/unkeyed test is
  computed from the data rather than from the plan, so a county that gains a keying starts
  reading correctly with no copy edit.

- **FIX THE ROSTER, THEN FIX EVERY CARD THAT READS IT — the count is not always one.**
  Iowa applied the switchboard rule above to `ia-county-officers.json` and its County
  card and called it done, while a SECOND file carried the same people onto a second
  card: `ia-supervisor-members.json` copied each supervisor's phone out of the officer
  roster before the hoist, so the County Supervisor District card went on printing the
  courthouse number under one name. That is strictly worse than the form the rule was
  written against — where five identical numbers at least LOOK like a switchboard, one
  number under one supervisor reads as their own line and nothing on the card
  contradicts it. **A derived roster inherits the defect its parent was just cured of**,
  and the mechanical test cannot see it, because the derived file shows one phone per
  card and no repetition at all. So the guard belongs where the copy happens: the
  supervisor builder now REFUSES to write if a member row arrives carrying a phone,
  which makes a genuine per-person line something an operator has to admit rather than
  something a loop inherits. Before closing out any roster fix, grep for every reader of
  that file.
- **READ THE TEXT OR READ THE LINK — decide per source, and never assume the link is
  the safer one.** Putnam's board page 404s on all five member profile links and
  points TWO of them at a member who has left the board; the visible text is
  correct. St. Clair is the exact mirror: its captions are wrong and the URLs right.
  Neither surface earns blanket trust, so check which one the county actually
  maintains before keying on it. (Brown adds the miniature version: one member's
  phone is marked up as `mail:` where every other row has `tel:`, so reading phones
  out of hrefs silently drops him. Read the visible number.)
- **A TEXT LAYER THAT EXTRACTS AS NOISE IS WORSE THAN NO TEXT LAYER, because it parses.**
  Mason's roster PDF is a scan carrying a text layer written in a non-embedded font whose
  encoding does not survive extraction: pdfplumber and pdftotext both return line noise
  ("xRF# ISgH tlgP") and neither errors. A scraper reading that would not fail — it would
  ship confident garbage under real officeholders' names, which is the single worst
  outcome this pipeline can produce. **Before writing any PDF scraper, look at what
  extraction actually returns and check it against the document.** `pdfimages -list` tells
  you in one command whether you are reading a page or a photograph of one.
- **A source that is FETCHABLE but not MACHINE-READABLE gets a WATCHER, not a scraper.**
  When the only roster is a scan, transcribe it by hand (the Kendall/McHenry posture) and
  automate the one thing a machine can still do: notice that the source moved. Mason's
  `scripts/mason_roster_watch.py` checks two things weekly and edits nothing —
  **(1) the page still links THAT EXACT document**, which matters most because a
  WordPress-published replacement lands at a new upload path and the old URL keeps
  serving the old file with a 200 forever (the `validate_sources.py` supersession
  failure), and **(2) the bytes still hash to a recorded fingerprint.** Either change
  opens a tracking issue asking a person to re-read. Make it deliberately noisy: a
  re-export of an identical scan raises a false alarm that costs one minute, while a
  missed roster change ships a wrong officeholder indefinitely. Say in the workflow that
  its output is a request for a person, not a diff.
- **When a source marks ANY member's address as legally protected, drop the
  residence-derived columns for the WHOLE roster — including the town.** Mason prints
  seven members' home addresses and an eighth row reading "SECURED ADDRESS". Shipping
  town-for-seven-and-blank-for-one would make the protected member the one row that
  stands out, which is the exact outcome the protection exists to prevent. The Madison
  precedent (never collect a residence) extends one column further here, and costs
  nothing: the card still carries name, district, party, role, phone, e-mail and term.
- **A note about how someone REACHED a seat is a note, never a badge.** Mason annotates
  two rows — an appointment date and a vacancy date, each with "will run for full term".
  Those describe a route to office, not an office; badging them would read as a title the
  member does not hold. They ride the muted note next to the term year.
- **The coverage outline can acquire an interior HOLE, and that is a correct state.**
  Mason closed the served ring around Menard, so `metro-outline.json` went from one ring
  to two — an outer ring plus a hole. Both consumers were already even-odd
  (`pointInPolygonRings`, and Leaflet's even-odd fill under the wash), so the enclosed
  county correctly reads as uncovered. **Check both before shipping the county that
  closes a ring**, and add the enclosed county to `OUTSIDE`: that anchor is what proves
  the hole is real rather than the outline having swallowed a county whole. Assert it in
  a card test too — a hole that silently inverts would tell residents of an unserved
  county that they are covered.
- **The served area can be DISJOINT — contiguity retired as a shipping gate
  (2026-08-04, operator decision).** Growth had been "one contiguous county at a time";
  by pass 12 the outline already carried two holes (Menard and Bureau: enclosed,
  researched, source-blocked — proof that adjacency never predicted serveability), and
  pass 11 measured the frontier as ask-gated, so holding new counties to ring-adjacency
  had stopped ordering the work and started refusing it. A county now joins the moment a
  county-keyed layer answers in it, wherever it sits; contiguity survives only as a
  research-ordering preference. Two rules are UNCHANGED and still binding: a county
  never joins for a rich statewide answer (the Centralia/Marion trap,
  `build_metro_outline.py`), and a dispatched layer never answers inside the wash — a
  municipality in an unserved county waits for its county (the Galesburg record,
  `galesburg-wards-outside-the-ring`).
  **A THIRD RULE was added on 2026-08-21 (operator decision), and it narrows this one:
  the county-keyed layer that lets a county join must be its BOARD or its PRECINCTS.**
  Lawrence County forced the question. Its own GIS publishes four fire protection
  districts — clean, non-overlapping, 0.02% spill outside the county line, 84.2% of the
  county covered — and no board or precinct layer anywhere in its four-service org, so
  by the letter of the rule above it qualified. It was HELD OUT. Every county served
  carries a board or a precinct layer, and the coverage wash is read by visitors as
  *"we can tell you who represents you here"*; a fire taxing district, however clean,
  does not answer that. The finding stays on file in `lawrence-county-board` rather
  than being built, and the same test now applies to any county whose only county-keyed
  layer is a fire, park, library or drainage district. This does not narrow anything
  else: an at-large county still joins on its County-card roster alone (fifteen have),
  because that roster IS the who-represents-you answer. **First-island checklist** — EXERCISED by
  Effingham on 2026-08-04, the same day this rule landed (the pass-13 sweep found it
  build-ready; the shipped metro-outline.json is now a MultiPolygon whose second
  polygon is the island's own outer ring), and again by Hamilton on 2026-08-05 (the
  second island — the pass-14 ask campaign's first answer, built the same day). Kept as the recipe for every later island —
  the first detached county had to, and each next one must: (1) rebuild `build_metro_outline.py`,
  run `--check`, and confirm the emitted geometry is a MultiPolygon with the island as
  its own OUTER ring — not a hole (the pass-4 nesting bug this machinery was written
  against: an island emitted as a second ring of one Polygon reads as a hole, renders
  identically under the wash, and answers False to every containment test inside it);
  (2) give the island an INSIDE anchor and anchor the gap between island and mainland
  OUTSIDE, so the unserved corridor is proven washed; (3) load the app and eyeball the
  wash at the island's edges — even-odd rendering is verified for holes, not yet for a
  second outer; (4) run the §3.5 step-1 mechanics unchanged (`DISPATCH_COUNTY_FIPS` +
  `METRO_COUNTY_FIPS` + `validate_index.py` check 8); (5) `check_envelopes` will force
  `metro_bbox`/`permalink_gate` to widen around the island — that also widens the
  bounded geocoder's viewbox for the whole metro, so re-read the §6.1 worksheet
  implications deliberately instead of accepting the automatic number.
- **A workflow's PR title and body are a human-review surface: county drift there is a
  real defect, not cosmetics.** Three roster workflows cloned from Iroquois's kept
  Iroquois's DOMAIN and its "4 districts, four members each" description while scraping
  and titling a different county — so a Washington roster PR would have asked a reviewer
  to approve officeholder changes under another county's provenance. When cloning a
  workflow, grep the new file for the OLD county's name and domain before committing.
- **A frontier county you cannot serve still needs its outline** if it carries a recorded
  gap: the gaps panel tests the pin against `<slug>-county-outline.json`, so without one
  a reader in a greyed-out county is told nothing is missing there. Ship the outline,
  tag the gap with the slug, mark the worksheet entry `dynamic_reference: true`, and
  add NOTHING to `DISPATCH_COUNTY_FIPS` — the county stays unserved by construction.
  Derive the anchors from TIGERweb's own Incorporated Places centroids and round-trip
  each through a point-in-county query rather than recalling coordinates.
- **A block rate measured from ONE egress is not a property of the site.** DeKalb's
  scraper carried a confident number — "roughly two requests in three come back as the
  stub and the third serves the page" — and its first scheduled run failed with six
  stubs in a row, which that number makes a 1-in-700 event. The response says why:
  SiteGround's SG-Captcha refreshes to `…/sgcaptcha/?…&y=ipr:<CALLER IP>`, `ipr` for IP
  reputation. It scores the ADDRESS, so the observed rate is a fact about where you
  measured from — ~1 in 2 from one egress, 6 of 6 from a GitHub Actions runner, same
  code, same hour. Two consequences: **retry counts are the wrong dial** (no number of
  draws beats a score), and **a block must be measured from CI before it is described**,
  because a developer machine and a runner are different clients. Dispatch the workflow
  on your branch and read the log — that is the only measurement that predicts the
  weekly run. Note the scoring is per-HOST: dekalbcounty.org challenges while the
  clerk's own dekalbcountyclerkil.gov, which serves the yearbook PDF, never did.
- **…and "measured from CI" means SAMPLED from CI. One run is not a measurement, and
  neither is three.** DeKalb was dispatched four times on one commit. Runs A, B and C
  were refused on every rung — B under a real Chromium that held 24s on the
  interstitial — which is about as convincing as a negative result gets, and the
  conclusion drawn from it ("blocked from CI, give it the McHenry posture") went into a
  commit message, a docstring, the source registry and a public issue comment. Run D was
  then carried by plain `requests` on its FIRST try in 0.9s. Nothing had changed but the
  runner's address. **A reputation-scored edge has no per-CI verdict at all**, because CI
  is not one caller: GitHub draws runners from a pool and the edge scores each address
  separately. The honest artifact is a rate with its sample size, not a verdict — and
  three consecutive failures are exactly the evidence shape that feels conclusive and
  is not. Re-run until you see the other outcome or can say how hard you looked for it.
  The practical upside: this makes `continue-on-error` + a standing issue the right
  posture for a better reason than "the source is gone" — a job that fails on address
  luck should not go red, and the weekly cadence self-heals when the next draw lands
  differently. Reserve the terminal McHenry/Kendall posture for sources that refuse
  every caller, which is a claim you can only make after sampling several.
- **A bug in the prober reads exactly like a block, and it is the more likely of the
  two.** The CI run meant to answer "does a real browser clear this edge" instead
  printed `Page.content: Unable to retrieve content because the page is navigating` —
  the scraper asking for content while the stub's `content="0;…"` refresh was in flight.
  The rung lasted under a second and never saw a settled document of either kind, yet
  the log line sits next to the genuine failures and reads as one. Taken at face value
  it would have moved a county to the terminal "blocked everywhere" posture on the
  strength of a race in the prober. **A browser rung must POLL** — tolerate the
  mid-navigation error as the challenge working, wait, read again — and its failure
  message must distinguish *still navigating* from *interstitial still served*. More
  generally: before believing a rung's verdict, check that the rung ran long enough to
  have a verdict. Compare its wall time against what the work should have cost.
- **A workflow that has never run is not a workflow yet — dispatch it the day you
  ship it.** Six workflows were merged without ever having executed. Dispatched
  manually on 2026-08-02, FIVE failed in the same minute on the same line, and had
  been broken since the day each shipped: `ModuleNotFoundError: No module named
  'shapely'`. Every derived-boundary roster builder imports its district composition
  from the matching `*_board_districts.py` (that is the weekly drift check, and it is
  the right design), and those modules imported shapely at MODULE SCOPE — so importing
  a tuple of township names dragged in the geometry stack, which the roster jobs
  correctly never install because they do no geometry. Cass, De Witt, Marshall, Mason
  and Washington: the entire tranche-4 tier, silently, from day one. The sixth passed,
  and it is the at-large roster — the one county tier with no districts module to
  import from. **Nothing else could have caught it.** The scrapers were fine, the
  builders were fine, the data was fine, `validate_index` passed, and every local run
  worked because a developer machine has shapely installed. The defect lived in the
  seam between a script's import graph and its workflow's pip line, and no gate looked
  at that seam. Two rules follow. (1) **Dispatch every new workflow before you call the
  tranche done** — a green `validate_index` says nothing about whether the job runs.
  (2) The fix is to move the heavy import into the function that uses it, not to add
  the package to the pip line: a module exporting a constant should cost a constant to
  import. `scripts/validate_workflow_deps.py` now enforces exactly this in
  `smoke-test.yml` — it walks each workflow entry point's transitive module-scope
  imports through `scripts/` and fails on any third-party module the workflow does not
  install. It is stdlib-only so it runs before any dependency exists, and it treats
  function-local and `try:`-guarded imports as lazy by design.
- **A count floor that counts NAMES cannot tell a vacancy from a regression — count
  SEATS.** Lee's weekly refresh failed its first-ever run with `19 members < floor 20`,
  and the floor was right: the county's roster PDF has a literal gap where the
  twentieth row belongs — District 3's rows run y=320.9, y=339.1, then jump to
  y=375.3, and at y=357.6 sits a single cell reading "3" with no name, party, term or
  address. A vacant seat, printed as one. The tempting fixes are both wrong: lowering
  the floor to 19 blinds it to the parse regression it exists to catch (which is
  exactly what tripped it before — a name set 3pt low, lost to a fixed row band), and
  dropping the row ships "19 members" when the truth is "19 members and a vacancy" —
  a different claim about the board, since the county apportioned five seats to that
  district and one is unfilled. Record the nameless row as a vacancy, count seats
  (named + vacant) against the floor, and attach `vacancies` to the district:
  **counted, never named**, the Livingston/Stephenson posture the engine already
  renders. Any county whose source prints a seat it cannot fill will hit this, so
  reach for it before touching the floor.
- **A source that throttles is not a source that blocks, and needs the opposite
  response.** Henry's first run died on `429 Too Many Requests` against the second of
  its two district listings, fetched a fraction of a second after the first. Nothing
  is blocking: the county answers a bare client fine and simply asks to be paced, but
  the scraper had no retry at all, so one 429 killed the week. Back off and retry,
  honour a numeric `Retry-After` (cap it — an unbounded value from a server is a way
  to hang CI), pace multi-page fetches apart, and do NOT retry 401/403/404: a moved
  directory is not fixed by waiting, and burning five attempts on it turns a clear
  error into a slow one.
- **Register a roster's own source URL, not just its geometry's.** DeKalb's board
  districts were in `validate_sources.py` (an ArcGIS endpoint, always fine) while the
  members page the card's names actually come from was not, so the monthly check
  reported the layer healthy through the block. A layer with a scraper has TWO sources;
  both belong in the registry. CORRECTED 2026-09-02: since `scripts/validate_card_links.py`
  (2026-08-27) extracts every `sourceUrl` in every instance's `data/app` and probes it in
  the same monthly run, the members page is watched without a manifest row — and no
  districted roster page carries one today. What a `validate_sources.py` row still adds is
  the `blocked` inversion for a permanent, CI-measured block. And don't reach for `"blocked"` on a conditional block —
  that flag inverts the check, and it is for permanent ones where unreachable is the
  expected state. Where a source answers sometimes, both states are worth reporting.

- **A TLS ERROR IS NOT AN HTTP STATUS, and recording one as a block costs a county.**
  `coles-county-board` sat as a no-source gap for a year reading "BOTH REFUSE THIS
  NETWORK", and on 2026-08-17 that one phrase turned out to cover three different
  facts: `co.coles.il.us` has no DNS record, `www.co.coles.il.us` really does reset the
  connection, and `colesco.illinois.gov` **answers HTTP 200 with a complete page**. What
  failed on the third was certificate *verification* — the county's server sends only its
  leaf and never the intermediate that signed it, so `requests`, `curl` and `urllib` all
  stop at "unable to get local issuer certificate" while browsers and search crawlers
  sail through by fetching the missing issuer from the leaf's own AIA extension. A server
  misconfiguration had been written into a gap record, and into a drafted reply telling
  the Clerk her site was blocking us.
  **So: get a host to the point of ANSWERING before recording what it does.** Count the
  certificates it sends (`openssl s_client -connect <host>:443 -showcerts | grep -c
  'BEGIN CERTIFICATE'`) and compare against a control host — one certificate where a
  control sends three is an incomplete chain, not a refusal. Then separate "refused me"
  (a status, a challenge page, a reset) from "handed me something I could not verify".
  The remedy for the latter is standard and disables nothing: fetch the intermediate from
  the AIA URI the certificate publishes, pin its SHA-256, and verify the full chain
  (`scripts/coles_county_board_scraper.py`). **Never `verify=False`** — that trades a
  fixable annoyance for an unauthenticated source of officeholder data. Two corollaries:
  a probe run from an unusual environment may report unreachable for reasons of its own
  (a trimmed CA store, an egress gateway's own 503), so name WHO answered before
  believing it; and a source blocked this way is permanent until the county fixes its
  server, which is what the `validate_sources.py` `blocked` inversion is for — but write
  the reason so the next reader does not re-file it as a refusal.

- **A ROSTER COLUMN ON A BOUNDARY LAYER IS A SNAPSHOT OF ITS PUBLICATION DATE, and the
  Effingham/McLean shape is not self-identifying.** Rule 4's happy path — "the member
  rides the boundary layer, so no scraper and no weekly workflow" — is real, and Coles
  looks exactly like it: 12 districts on a live county service, with `Official`, `party`,
  `term`, `phone`, `email` and `Population` columns sitting right there. Every one of
  those columns was frozen the day the layer was published (2022-04-23). Six of the
  twelve names had since left the board; District 11's `term` still read "2022"; the
  `Population` column summed to the county's **2010** census count to the person. A build
  that took the layer at face value would have printed six wrong officeholders under six
  real districts — the worst output this pipeline can produce — and nothing would have
  failed.
  **So before choosing the no-scraper path, spend one fetch: open the county's own roster
  page and compare the names.** Two cheap staleness tells cost nothing to check and both
  fired here — the item's `created`/`modified` timestamps in the ArcGIS item JSON, and
  a population column that sums to the *previous* decennial count rather than the current
  one (compare against TIGERweb `POP100`; it also tells you which map you are looking at).
  A county that republishes a boundary rarely republishes its people. Note the opposite
  finding held too and is worth stating separately: Coles's *polygons* were current —
  proven as exact unions of the county's own precincts and matched 12/12 against the
  composition its board page publishes today — so the answer was geometry-from-the-service
  and people-from-the-page, not "distrust the layer".

- **"I DO NOT HAVE MAPS AVAILABLE" IS NOT THE END OF A COUNTY. If the districts are
  unions of whole precincts, the county's certified canvasses ARE the boundary
  description — and the Census 2020 voting districts are the polygons, IF they still
  match the county's current precincts.** Clark's Clerk answered the standing ask on
  2026-08-18 with one sentence: *"The County Board is elected by districts. I do not
  have maps available."* That settles §3.5 step 2 and refuses the geometry ask in the
  same breath, and the county shipped four hours later as the 65th, with **no map
  involved at any stage** — a first for this fleet. The route, in order, and it is
  cheap enough to try on any districted county whose Clerk says no:
  1. **Find the election authority's results archive**, which is usually NOT the county
     website. Clark's is `il-clark.accessliberty.com` (the Clerk's own site, one
     text-layer canvass PDF per election back to 2006) with a live feed at
     `il-clark.pollresults.net`. The county site merely links them from an Election
     Results page.
  2. **Read the "COUNTY BOARD n DISTRICT MEMBER" contests.** A canvass tabulates each
     contest precinct by precinct, so the contest's precinct list IS the district's
     composition — and the header ("Vote for one") gives the seat count. Walk the
     GENERAL elections newest-first; the first one carrying a district is the one that
     seated its current member, which handles staggered terms with no schedule
     hard-coded. **Primaries never seat anybody and must never be read as a roster.**
  3. **Require a second witness per district.** Clark's 2022 General carries all seven
     contests; the 2024 General re-tabulates 3/4/7 and the 2026 General Primary
     re-tabulates 1/2/5/6 — so no district rests on one document, and a transcription
     slip cannot survive. (The 2022-2024 board list the county publishes agreed too,
     and could not be relied on: it is a scan whose District column renders a 6 as a 5.
     The canvass settled the digit.)
  4. **Apply THE JASPER TEST before dissolving anything.** The census VTD fabric is the
     county's precincts *as of January 2020*, not necessarily today. Clark passes: 23
     census features, 23 county precinct names, 23/23 by name, POP100 summing to the
     county's exact population, and all three canvasses tabulating the same 23 names.
     Jasper FAILS the same test — five census Wade voting districts against four
     current county precincts, and no assignment of the fifth reproduces a lawful plan
     — which is why Jasper is still unbuilt while Clark shipped on the identical
     technique. **The test is the whole difference between the two, so run it first.**
  5. **The roster comes free**, and is a stronger claim than a board page makes: each
     member is whoever the county CERTIFIED as elected, per district. State it that way
     on the card (`districtSource`: "elected 2024 (District 3, certified canvass)"),
     because a canvass cannot show a mid-term appointment and the card must not imply
     one. Do not badge a chair — a chairmanship is elected from within the body and no
     certified document shows it.
  6. **Wire the composition check into the weekly roster run.** The dissolve is only
     correct while the canvasses keep tabulating the same precincts in the same
     districts, so re-read that list every week and FAIL when it moves. That is the
     re-precincting/redistricting tripwire, and it is free once step 2 is written.
  **The fleet-scale corollary, recorded in the guidebook backlog:** Clark's results
  vendor serves **34 Illinois counties** under `il-<county>.accessliberty.com` /
  `il-<county>.pollresults.net`, fourteen of them unserved — including both coverage
  enclaves. Precinct-level certified returns answer §3.5 step 2 *and* supply the
  composition, without waiting for a reply.

  **Two traps on this vendor, both paid for.** (a) The per-county DOWNLOAD HANDLER ids
  differ — Clark 58/188, Edgar 59/189, Bond 52/220 — and a wrong pair returns the
  vendor's LOGIN PAGE as a PDF: HTTP 200, plausible size, not a canvass. Verify every
  download starts `%PDF` and reads "Statement of Votes Cast" for the right county.
  (b) **A 200 from `il-<county>.*` PROVES NOTHING ABOUT WHETHER THE COUNTY IS CARRIED**
  (measured 2026-08-20): the hostnames resolve for *any* county name and serve a generic
  shell, so `il-hancock`, `il-jackson`, `il-marion` and `il-warren` all answer 200 while
  carrying no data at all. Test by CONTENT, not status — a carried county returns its
  result set inline (Bond and Clark: 34 `electionData` blocks, a 57–58 KB past-elections
  page, 60 downloadable canvasses), while an uncarried one returns a 7,720-byte template
  whose `electionData` hits are unfilled Angular placeholders and a 10.6 KB archive with
  ZERO download links, byte-identical from county to county. Counting `Download.aspx`
  links on `pastelections.aspx` is the cheapest reliable test: 0 means not carried.

## 3.6 Verification

The standard gates (§6.5) plus: the Playwright smoke test's coverage-hide, permalink
stability, and alias-shim assertions (an old-id `layers=` link must light the consolidated
toggle); a live dispatch harness against the real county endpoints asserting (a) each test
point matches exactly one county's geometry and (b) known ground-truth districts resolve
(Loop → Cook commissioner district; Wheaton → DuPage board 4; a Will point → board
district + roster entry). For municipal rosters: a point sweep per depth class — full
council, mayor-level, contact-only, identity-only, unincorporated-empty — plus one
independent cross-check of a parsed council against the city's own published roster
(the Aurora check pattern).

---

---

# PART 4 — Path C: a new concept or layer

1. **Run the §1.6 taxonomy test.** Most proposals resolve to a dispatch entry (Part 3) or
   an identity-card enrichment, not a layer.
2. **Consult the concept matrix** (`docs/DATA_LAYER_GUIDEBOOK.md`): if a sibling ships
   the concept, reuse its recorded pattern and source notes; if a sibling recorded a
   drop, check whether the rationale applies before re-researching.
3. **Genuinely new concept:** it launches consolidated (a dispatch table from day one if
   multi-source), registers through a factory where one fits, declares honest coverage,
   and ships its officeholder story in the same change (rule 4; the route map is §6.4).
4. **Card — the information-surfacing standard.** The card leads with the layer name
   (the card header), then the district identifier, then — **wherever a verifiable
   source exists** — the representative(s)/officeholder(s), the office location,
   contact info, and a link to more detail, in that order. The order maps onto the
   card-helpers vocabulary (`docs/CARD_RENDER_API.md`) as: **identifier pill
   (`cardIdentifier`) → person rows (badges/notes/committee expanders) → office group →
   contact line → footer link (`primaryLink`)**; name-only layers render as `compact`
   cards. Helpers are data-only by contract: never pass HTML; email renders as a mailto
   link and is never printed; phone rows carry a `tel:` href built by the helper; absent
   fields render nothing. Deviate from the order only where the concept demands it
   (nearest-N lists, no-officer geography/identity concepts, honesty-rule link-only
   judicial bodies) — and when identity, location, or contact data exists in a layer's
   source but isn't on the card yet, **record the gap in the guidebook backlog rather
   than shipping it silently**. Hover identity follows the parity rule (§2.2.1): the
   popup reads the same fields the card does.
5. **Bookkeeping in the same change**: worksheet layer entry (+ rank, hover keys as
   needed) → regenerate; `LAYER_AREA_RANK` placement; a `LAYER_SIDEBAR_RANK` position
   (below); sw list if a `data/app/` file is added; `validate_sources.py` manifest row;
   guidebook coverage map + inventory + matrix (drops recorded with rationale — silence
   is the only wrong answer); Appendix A row.

**Sidebar placement standard (recorded 2026-07-28).** A layer's position in its sidebar
group is set by the instance's explicit `LAYER_SIDEBAR_RANK` (grep it in `index.html` —
applied by a boot-time sort; `validate_index.py` asserts the list matches the registered
id set 1:1, exactly as it does for `LAYER_AREA_RANK`) — never by registration order,
which had accreted by build thread rather than design (Early Voting led the Political
group; a DuPage unincorporated tax district led Public Safety). The order within each
group: **identity hierarchy → representation → service/taxing overlays → amenity
points, broad → specific within each family.** Toggled-on layers still float to the top
of their group, so the rank governs the resting order, not the active one. A new layer
takes its rank in the same change that registers it.

**Exception — Political is DEMAND-ordered, most-searched concept first** (operator
call, 2026-07-28). No Search Console / query data is connected, so the ranking rests on
the best available public proxy — 12-month Wikipedia pageviews (Jul 2025 – Jun 2026,
en.wiki, user traffic) for each concept's closest article: congressional districts of
Illinois **254k** ≫ IL House **62k** > IL Senate **49k** ≈ Chicago City Council **48k**
(ward) > early voting **23k** > Cook County Board **19k** ≫ Board of Review **4.2k** ≈
Chicago Board of Education **3.4k** ≈ IL Supreme Court **3.4k** ≫ judicial subcircuits
(~0, no article). Hence: congress → il-house → il-senate → ward → early-voting →
county-board → ccbr → school-board → il-supreme-court → judicial-subcircuit. Known
proxy weaknesses, recorded so the next pass can do better: pageviews measure national
concept interest, not Chicago-resident lookup intent (which likely boosts `ward` — the
city runs a dedicated alderman-lookup tool for a reason), and early-voting/CCBR demand
is seasonal (election windows, appeal windows) rather than steady. **Re-rank from real
query data when Search Console (or GoatCounter arrival) exports exist; the bottom tier
(ccbr / school-board / il-supreme-court) is statistically tied and ordered by
recurrence of its seasonal spikes.**

**Nesting determination (recorded 2026-07-28; Wisconsin added 2026-08-27).** The `subOf`
tree — County → Township → Voting Precinct, Ward → Ward Precinct, Police District → Beat —
encodes genuine legal containment-plus-numbering hierarchies and is complete for the
reference instance. **Wisconsin runs the same shape and was missing its top level until
2026-08-27:** County → County Subdivision → Municipal Ward, plus Police District (Milwaukee)
→ Squad Area. The county level was drift rather than a decision — `county-subdivision` is
the same TIGER layer 1 the reference instance nests as `township` — and the containment is
MEASURED, not assumed: Wisconsin's 608 incorporated municipalities occupy 671 subdivision
records, because the 58 that cross a county line get one record per county (Wisconsin Dells
has four). **Municipality/`City or Village` is deliberately NOT nested and cannot be:** a
TIGER Place is one record for the whole municipality regardless of how many counties it
spans, so it is the one municipal layer that does not sit inside a county. Evaluated and deliberately kept
flat: **CCPSA District Council** under Police District (shares geometry 1:1, but it is
an elected representation body — the app never gates an elected office behind a service
toggle); **CPS zones/networks** under the unified school district (a toggle
prerequisite on the city's most-used school layers, with no fleet precedent);
**special districts** under `county` (independent taxing bodies, not county sub-units —
the county is their sourcing dimension, not their parent); **`tif-district`** under
`municipality` (legally defensible — TIFs are municipal ordinance districts — but low
benefit, and TIF converts to a dispatched concept at its second county, §1.5).
Cross-group nesting is impossible by design: a sub renders inside its parent's block in
the parent's group section. The bar for a future nest is genuine containment-with-
numbering (precincts are numbered within townships, beats within districts), never
mere geometric overlap.

---

---

# PART 5 — What the two deep states taught

Illinois reached 91 counties; Wisconsin reached 31 layers across four phases. The rules
below are organized by the **question they answer**, not by the county that paid for them —
the per-county record is `docs/DATA_LAYER_GUIDEBOOK.md` and the two `CLAUDE.md` narratives.
Every one of these cost a real build, and every one applies to any state. **§3.5.1 carries
the county-work detail** — the longer, Illinois-worded originals of the rules this part
states once and generally.

## 5.1 Is there a source? — the question that is answered wrong most often

**This section exists because the fleet's single most repeated error is recording a
measurement of a WEBSITE as a fact about an AGENCY.** It has now happened in both states,
at county scale and at state scale, and it has been expensive every time.

**AND THE RULE ABOVE, WRITTEN HERE FIRST, DID NOT STOP IT HAPPENING EIGHT MORE TIMES.**
On 2026-09-02 Wisconsin's last eight counties shipped in a day — Lincoln, Barron, Forest,
Florence, Sawyer, Ashland, Douglas, Iron — and **not one of them had started publishing
anything new**. Every one was already publishing when this project recorded that it was
not. So the failure is not that the rule was unknown; it is that the rule is a conclusion
and the records were written in a form no later reader could check it against. Hence:

> **THE FORM OF A BLOCKER RECORD IS A RULE, NOT A STYLE.** A blocker must carry the URL
> tried, the CLIENT it was tried with, the DATE, and WHAT CAME BACK — and it must state
> its conclusion **about that URL**, never about the body. "Forest does not resolve" is
> unfalsifiable and was wrong; "GET `https://co.forest.wi.gov/` with the pinned browser
> headers on 2026-08-25 → 200, zero occurrences of `district`" is a fact, and the next
> reader sees at a glance that ONE address was tried. Every one of the eight records was
> accurate about its page and false as written. The unbounded `blocker` field exists
> precisely to hold this; nothing about it is too long.

Two corollaries the same day earned:

- **Finding the host that serves a board page is not reading it.** Barron's record was
  *corrected* a week before it shipped — a sweep found the working host and put it in the
  directory table — and nobody opened the page. It is 75 KB of prose naming two people,
  and it LINKS the roster twice, under anchor text that says exactly what it is. **A
  correction that fixes a link is not a look at a county**, and the fix must end with the
  question the record answers: does this page NAME anyone?
- **The direction of a working prefix is a per-county measurement.** Barron answers on
  `www.` and fails bare; Forest answers bare and fails on `www.`. Neither is a default,
  and a record naming one without the other has tested half the county's front door.

- **A blocked website is not a blocked agency.** Knox County's record said its site
  "refuses every request" — true of the website, written as though it described the county.
  Knox has four hosts: the site denies, its GIS server serves freely, its CMS serves the
  same site's documents unblocked, and a fourth is simply dead. Johnson and Perry were
  reached **without their own websites being read at all**, because a county's ELECTION
  AUTHORITY is a separate publisher on a separate host. At state scale Wisconsin repeated
  it exactly: elections.wi.gov sits behind a Cloudflare challenge, a fortnight of careful
  measurement recorded the challenge accurately, and the conclusion drawn from it — that
  the statewide polling list could not be had — was wrong. **Asked directly, the Elections
  Commission sent the whole file in an afternoon**, and the ward card went from two cities
  to 7,131 of 7,161 wards.
- **An UNBLOCKED website is not the only website — ask the BODY's own host.** The rule
  above has a twin that is easier to miss, because nothing refuses you and nothing warns.
  Wisconsin swept all 72 counties for a district-keyed supervisor list, recorded 50 as
  publishing none, and drafted 42 e-mails asking for it. Nine of the fifty were publishing
  a complete one. Dane County — the state's second-largest board, 37 seats — publishes its
  roster at `board.danecounty.gov`, a different host from the `countyofdane.com` the
  project's own clerk file carried; the sweep asked each COUNTY's site and never the
  BOARD's. A county board, a school board, a court system and an election authority are
  each capable of having their own subdomain, their own CMS, and their own vocabulary.
  **When a sweep of "the county's website" returns nothing, that is a fact about one host.**
- **A link harvest scores the HREF, not only the words on the link.** Crawford County
  (WI) stayed in that same "publishes nothing" bucket for two more days, and its front
  page had been linking the whole seventeen-district roster the entire time — under a nav
  item whose anchor text reads *Government*. Only the address says board
  (`/boardsupervisors`). A body has no obligation to label its link the way a sweep
  searches for it, so score the URL and the text, and follow a promising path even when
  its wording is generic. Check the redirect before blaming the domain, too: the clerks'
  association publishes this county as a `.org` that serves the `.gov`'s own page, so the
  host was never what stood in the way.
- **RE-READ YOUR OWN RECORDS BEFORE RE-PROBING THE WORLD.** All nine of those recoveries
  came out of files this project had already written, not out of any new source. The
  trigger was a builder docstring that cited a county's board page as the authority for
  its seat count — a page nobody had ever wired into the roster scraper, while an e-mail
  was being drafted asking that county for the list it publishes. A gap record, a
  docstring and a scraper table are three places the same county can be described
  differently; when they disagree, one of them is a shipped bug. Audit them against each
  other on a schedule, and treat a long, confident blocker as a place to look rather than
  a reason not to.
- **GREP THE SHIPPED APP BEFORE PROBING A HOSTNAME — the strongest form of the rule
  above.** On 2026-09-05 two Illinois gap records were corrected in one pass, and both
  said the same false thing: that the county's GIS host "was not identified from here".
  Winnebago's host is `maps.wingis.org/public`, hard-coded in `il/index.html` as
  `WINNEBAGO_GIS` and read on every visit for that county's board districts, precincts,
  Rockford's wards and eleven municipalities' officials. Macoupin's is
  `data.macoupincountyil.gov`, likewise read on every visit. Both records were written
  while probing GUESSED hostnames (`gis.wincoil.gov`, `maps.wincoil.gov`) — and the rule
  that a guessed host's failure must not be recorded as the county's is right, but it
  stops one step short: **the host was not unknown, it was in the repo.** A gap record and
  a loader in the same repository are two descriptions of one county.
  **AND THE SEARCH INCLUDES THE GAP RECORDS THEMSELVES — the same change failed this rule
  one record down while writing it.** Its Livingston entry said the county "references no
  GIS, mapping, parcel or tax-inquiry host of ANY kind", and the SIBLING record
  `livingston-precincts`, fourteen lines above it in the same file, had said since July
  that the county's "only mapping product is the assessment office's mail-order parcel
  program, at 10 to 20 cents per parcel". No probe was needed to know better; a `grep -n
  livingston` would have done it. A county's own gap records are written at different
  times by different passes asking different questions, so they are the cheapest place a
  contradiction shows up and the last place anyone looks. Before any probe, grep for the
  county's name in: the instance's `index.html`, its `scripts/`, `validate_sources.py`,
  **and `docs/DATA_LAYER_GUIDEBOOK.md` itself** — every record, not the one being edited.
- **READ THE OPERATIVE LICENCE, NOT THE TERMS PAGE.** A public "Terms of Use" page and the
  data licence a purchaser signs are different documents that answer different questions,
  and the permissive one is the one a probe finds first. WinGIS's `/Terms` carries no
  redistribution clause at all — a no-warranty clause, a limitation of liability, and a
  credits requirement — and reading it alone produced the conclusion that Winnebago was
  freely licensable. Its Data License Agreement, a PDF linked from its /GISData page and NOT from
  /Terms (which carries no occurrence of "licens" at all), says
  "reproduction or redistribution of digital datasets or products derived therefrom
  outside of licensee's organization or entity is expressly forbidden" — WORD FOR WORD the
  clause that stopped Bureau, and the same class as the CCGISC licence that withdrew
  Champaign and Piatt. The same mistake was made on Grundy the same week in the other
  direction: the fee schedule was recorded from its parcel line while the line above it
  priced "Individual Boundary Data of Taxing Bodies". **Find the document that binds, quote
  the clause, and note which document you did NOT read.**
- **The ask is a route, not a last resort.** Put it in the ladder beside the technical
  probes. Its cost is one e-mail; its yield in this fleet includes a statewide polling
  file, a licence-gated county's written permission, several precinct tables no county
  publishes, and — as often — a clean, citable NO that closes a question for good. Draft
  asks in batches, send them, and **record the send date**; a silent ask is not a closed
  one. **A follow-up is a recovery mechanism, not a nudge:** one county's Clerk answered
  the question that unblocked a whole build only on the THIRD attempt, because her spam
  folder ate the first two. Follow up at ~3 weeks, again 2 weeks later, and only then
  record the route UNRESPONSIVE — which is a different claim from "no source exists".
- **Measure from the vantage that matters.** A block observed from a development sandbox
  may not exist from CI. Wisconsin's WEC and Milwaukee's police pages both refuse the
  sandbox and answer GitHub's runners plain; the scraper's vantage is CI, so a sandbox
  probe failing is expected and proves nothing. Conversely a proxy's own 403 is not the
  site's 403 — check who answered before recording a host as blocked.
- **Some "unreachable" hosts are misconfigured, not absent.** An **incomplete TLS chain**
  (leaf served without its intermediate) fails every automated client and no browser
  notices, so it reads identically to a dead host. Two counties were written off this way
  before the pattern was recognised; the fix is to supply the intermediate by AIA with a
  **pinned hash**, never by disabling verification. Sweep for it
  (`scripts/probe_incomplete_tls_chains.py`), and sweep `gis.<domain>` as well as the bare
  and `www` hosts — the old host list could never have found the one host that mattered.
- **HTTP 202 is never a document**, and a captcha is an access control. `202 Accepted` is
  what several challenge fronts return; treat it as unreachable, not reachable, or a
  validator will cheerfully report a blocked source as fine. **Nothing here defeats a
  challenge.** A real browser executing a managed JS challenge is sanctioned where the
  publisher clearly intends human access; CAPTCHA-solving, evasion and fingerprint-spoofing
  are not, and a captcha'd county is reached by another publisher or not at all.
- **FETCHABLE IS NOT LICENSED — read the terms before you build.** This is step zero,
  ahead of every technical probe. Two counties were surveyed as build-ready because their
  layers answer instantly once a `Referer` header is set, and they are not buildable at all:
  their GIS consortium SELLS the data under signed agreement and its terms grant only
  transitory personal viewing. The referer check was **the edge of a licence, not hotlink
  protection to route around** — and the technical ease of setting a header is exactly what
  makes this dangerous, because nothing breaks and nothing warns. When a source is gated by
  anything, find out WHY before you find out how. A licensing block is a gap of kind
  `blocked`, and the route out goes to whoever holds the underlying PUBLIC RECORD. **That
  route works:** one licence-gated county was cleared by asking for written permission
  BEFORE signing or paying, and its board districts ship under the county's authorization
  with the licence's credit clause honoured on the card.
- **Enumerate the ORG, not the viewer.** A county's web map shows what it *uses*; the
  ArcGIS org behind it shows what the county *has*. One county's viewer names a single
  parcel service while its org carries fifty-four services including board districts and
  voting districts. Cheaper still, and now the FIRST check: an unauthenticated query to
  `arcgis.com/sharing/rest/search` — one request, needs nothing from the county's own site,
  and it found a 26-service GIS office at a county whose Clerk had written "our county does
  not have shapefiles or GIS layers."
- **A vendor's carriage is PER-ELECTION.** Election-results platforms serve many counties,
  and sweeping one election slug is not sweeping the vendor: re-running one sweep across ten
  slugs found two more counties previously recorded as uncarried. Test carriage by CONTENT
  across every known vendor, never by a vendor's published county list — that list shows
  only the election running right now.
- **Two publishers can compose each other even when neither references the other.** One
  county publishes a board-district layer and a precinct layer with no district attribute on
  a precinct and no precinct list on a district; overlaid, every precinct sits 98.4–100%
  inside a single district. Before writing a county off for want of a precinct-to-district
  TABLE, check whether it publishes the two LAYERS.

- **AN AGGREGATE IS NOT ITS RECORDS, and an index is not the document.** This is the
  navigation rule one level up, and it cost Wisconsin its last county. Iron's own staff
  directory — 832 KB, 213 mailboxes — contains the word *district* **zero times**, and its
  board page lists all fifteen seats with their titles and no districts. Both were
  read, both readings were correct, and the county was recorded as publishing no
  district-keyed roster. Every one of its fourteen filled seats has an entry in that same
  directory stating its district and the towns and wards the district is made of, and the
  board page **links all fourteen, in the anchors the names were read out of**. A summary view is
  compiled for a purpose that is not yours; when a listing omits the field you need,
  **open one record before concluding the field is absent**. The same day, on the same
  CMS, another county's per-member pages had been enumerated an hour earlier — so the
  method was known and simply not applied to the county that needed it.
- **Read the page BODY, not its navigation.** Iowa's auditor scraper shipped with a docstring
  saying the Secretary of State published no readable statewide roster because the page "links
  out to each county's own page rather than listing names itself". The page's county DROPDOWN is
  a list of links; underneath it sits a full card per county with the name, the party and an
  e-mail address, for all 99. The cost of that misreading was measured when it was corrected:
  99 e-mail addresses and 4 parties on a layer that had already shipped. A `<select>` of anchors
  is a table of contents, and a table of contents is not the document.

## 5.2 Is it the right source? — verification

- **Currency is a measurement, not a reading of a name.** One county publishes three
  board-district layers; the best-labelled one holds the superseded 2011 plan and the plan
  in force sits in an undocumented layer with a typo in its own name. A plan drawn to a
  census balances on that census: on 4,943 blocks the shipped layer runs 0.7% worst
  deviation against the better-labelled one's 15.1%. **Gate the comparison in BOTH
  directions** — refuse to write if the superseded layer ever comes into balance too.
- **Two witnesses, and prefer witnesses of different kinds.** Geometry witnessed by
  arithmetic beats geometry witnessed by another map. A confident, clean answer derived by
  sampling a map's fill colours was WRONG — those fills were per-township decoration — and
  what caught it was precinct-count arithmetic from certified returns. That arithmetic is
  now a gate in the builder rather than a comment.
- **Read the OBJECTS, never the pixels.** A vector PDF's districts are filled PATH objects
  whose exact fill colours pair one-for-one with the legend; that is readable. A raster scan
  is not, and colour-sampling a raster is forbidden. And **nothing traced ships**: where a
  map was used to resolve split precincts, the map only ever chose between two options that
  certified returns had already named, and the geometry came from census blocks.
- **The whole-unit test before any dissolve** ("the Jasper test"): the composing units must
  match the county's own current names one-for-one AND their populations must sum to the
  county's exact total. A county whose census voting districts no longer match its current
  precincts fails, and failing is the correct outcome — several counties are unbuilt for
  exactly this reason and that is the guide working.
- **Population deviation is a gate with an override that only the source can grant.** The
  dissolve guard enforces a 30% worst-deviation ceiling. Two counties exceeded it with
  their composition independently corroborated twice over; each shipped only after the
  County Clerk confirmed in writing that the plan is current, with the measured deviation
  recorded on the record rather than smoothed away. **The ceiling is raised for the county
  alone, never widened for the fleet, and never on a derivation merely going
  uncontradicted.**
- **Check the balance the body actually elects.** A board whose districts elect DIFFERENT
  numbers of members balances per MEMBER, not per district. One county's correctly
  transcribed districts are 28.8% apart per district — reading exactly like a botched
  transcription — and 12.3% apart per member, an ordinary rural apportionment. Get seats
  per district from the county's own roster before writing any population check.
- **A DERIVED boundary must watch the source it was derived from, or it rots silently.**
  The county edits its composition, the compiled table does not, and the app keeps drawing
  superseded lines with nothing failing. Where the composition lives on a page the roster is
  already scraped from, wire the check: the scraper emits the composition it read and the
  ROSTER builder fails on any difference, so the weekly job turns red on a redistricting.
  Compare at the granularity the districts actually differ at — one first version compared
  township names and passed a simulated change that moved precincts within a township — and
  **prove it bites** with negative tests (a unit lost, gained, renumbered, a whole township
  moved) before trusting it.
- **Reconcile the two authorities' vocabularies before concluding a district is missing.**
  A district nearly went unbuilt because four certified canvasses never named it; the cause
  was that two election authorities NAME CONTESTS DIFFERENTLY (`COUNTY BOARD 8TH DISTRICT
  MEMBER` vs `CO. BD. MEMBER D8`), so searching one vocabulary returned zero matches in a
  report that carried three such contests. The plausible explanation already written into
  this project's own docs was wrong, and measuring it was what showed that.
- **An independent witness disagreeing has THREE explanations, not two.** Wisconsin checks
  every county's published ward composition against the state's own ward layer, and the
  first version sorted each unmatched ward into "the county is wrong" or "the state is
  wrong". Both were wrong for Marathon: its composition names City of Marshfield wards 1-3,
  the state files Marathon's Marshfield as 12, 16 and 19, and 1-3 exist under **Wood**
  County, because the city straddles the line. So an unmatched unit is one of three things
  — it sits elsewhere in the same county under a different spelling, it sits in a
  NEIGHBOURING county because its municipality crosses the border, or it exists nowhere —
  and only the third is evidence about the document. Costing one extra query, and only when
  there is something to explain, the check now says which; before that it printed a
  confident wrong explanation weekly. **A witness that can only say "mismatch" will be read
  as saying "the source is stale."**
- **A floor is a measurement of what a source publishes, never a target for it.** Every
  scraper floors its counts so a silently-emptied field fails the weekly run. Barron's ward
  floor was set to 90 by scaling from ANOTHER county's document; Barron publishes 63,
  and a correct build failed on a number this project invented. Count the field on the page
  in front of you, set the floor a little under THAT, and write the measured figure in the
  comment ("25 today: five districts are whole municipalities carrying no ward number").
  A floor derived from another unit is a guess wearing a gate's clothes — and the failure
  it produces looks exactly like the publisher having broken something.

## 5.3 What the card is allowed to say

- **Provisional data ships only wearing every qualifier its source gave you.** Wisconsin's
  statewide polling list arrived months before the Commission publishes it, and the operator
  chose to display it. Five conditions, settled BEFORE the file arrived and every one a build
  gate: (1) the election is NAMED on the card, because a polling place is per-election and a
  date alone does not say which; (2) the word *provisional* appears in the reader's own
  sentence — not a badge, not inside an expander; (3) the pull is dated and attributed;
  (4) the authoritative lookup stays the prominent confirmation route; (5) **the file carries
  its election date and the card RETIRES the pairing once that date passes.** The flag is per
  FILE, never per record. Condition 5 is the one with no precedent elsewhere in the app: a
  per-election list that outlives its election looks current and is not, so forgetting to
  refresh must fail toward silence rather than toward last year's building.
- **An empty result is sometimes an answer, and should say so.** "This point isn't inside
  any district in this layer" reads as a lookup that failed. For a layer of incorporated
  places, a point outside every one of them is in unincorporated territory — that IS the
  answer. The engine's `emptyNote` lets a layer say what its own empty state means; layers
  that declare nothing keep the generic wording.
- **A layer's LABEL must match what the layer holds.** Wisconsin's "Municipality" layer
  carried 608 incorporated places and not one of the state's 1,242 towns, while statute and
  the state's own election vocabulary make a town a municipality. The app therefore
  contradicted itself in two cards at once. The label now says "City or Village"; the layer
  **id** did not change, because ids live in shipped `layers=` permalinks and renaming one
  breaks other people's links.
- **A shortfall is stated, never concealed.** A three-seat board whose county publishes two
  names ships two names AND says a third seat is unlisted. This required adding `seats`
  beside the members on the identity-card roster — the districted layers had been saying it
  since early on, and the at-large card simply had no way to.
- **Absence is content.** A gap record is the only thing that makes a missing dataset
  visible to a reader, and the Data gaps panel leads with the gaps that apply where the
  reader clicked — which requires every gap to name the COUNTIES it affects and the instance
  to ship a containment outline per county. Wisconsin shipped ten gaps with empty county
  lists and zero outlines, so its panel could never lead locally and told a reader who HAD
  clicked to click first. Where county granularity cannot express the truth, **over-claim
  rather than under-claim** and let the gap's own area line correct it: telling a reader
  something might be missing near them is recoverable, telling them nothing is missing is
  not.
- **Never mirror a source's private data.** A state file offered for the map included two
  entries whose voting location is a clerk's HOME, at a residential address. The agency may
  publish that; committing it to a public repository indefinitely is a different act, and
  this project does not make it. Run the check on every replacement file.

- **When two publishers name different officeholders, WITHHOLD — do not prefer one.** Iowa's
  county officers are published by a daily-regenerated association portal and by each office's
  own statewide directory, and the honest finding is that *neither wins categorically*. The
  portal ships an APPOINTED chief deputy in the elected sheriff's row in three counties (and an
  appointed assistant in a fourth's county-attorney row); the directories are dated documents
  and go stale, so a county's own site names a sheriff their PDF has not caught up with. The
  same pattern held for the auditor, where an association and the Secretary of State disagree in
  three counties and the counties' own sites resolve them **2-1 for the state**. So the ladder is:
  resolve what you can MEASURE, pin what a THIRD WITNESS settled (with the witness URL in the
  pin), and ship NO NAME for the rest, saying on the card that two directories disagree and who
  each names. A preference rule would have shipped a chief deputy as an elected sheriff in three
  counties, silently, forever. **Make the pin table fail when a pin outlives its disagreement**,
  or it calcifies into an assertion nobody re-checks.
- **A name difference is usually not a disagreement, and the naive test says it is.** Before any
  of the above can fire, "same person, spelled differently" has to be recognised: honorifics and
  post-nominals (`Mr. Shawn Harden, J.D.` / `SHAWN M. HARDEN`), a dropped middle initial, a hyphen
  (`Cosgrove-Whitmer` / `COSGROVE WHITMER`), spacing inside a surname (`VanDerMaaten` /
  `VAN DER MAATEN`), a suffix, a typographic apostrophe, a trade-body designation
  (`JARED HARMON (J-CINA)`), a one-character misspelling, and NICKNAMES — `Jeff`/`Jeffrey`,
  `Tammy`/`Tamara`, `Cathy`/`Catherine`, none of which a prefix rule catches. In every case that
  turned out to be two different people, the SURNAMES differed outright; in every false positive
  they matched exactly. Lean the test on the surname, and state its limit (two people sharing a
  surname and a first initial in one county office would read as one).
- **An ALL-CAPS source needs a name-aware title case, not the generic one.** The fleet's
  `cardTitleCase` is built for feed strings and turns `McGOWAN` into `Mcgowan` and `O\u2019TOOLE`
  into `O\u2019toole`. A name needs Mc/Mac, a leading letter-apostrophe, single-letter initials,
  roman numerals and hyphenated surnames handled explicitly — and it should be keyed to the
  office whose SOURCE is all-caps, never applied by detection, because running it over a
  correctly-cased name risks changing a spelling its own publisher chose.

## 5.4 Shape and structure

- **Depth is dispatch entries and roster rows, never new layers.** This is the expansion
  invariant, and 91 counties have not broken it once. A cross-county concept registers ONE
  toggle holding a per-county entry table, with coverage = the OR of its counties' tests.
- **An at-large body rides the identity card.** No geometry, no dispatch entry, no coverage
  function, no toggle — and three knock-ons that were each learned the hard way: such a
  county's precinct card must NOT carry a board-district row; it still needs its coverage
  outline and INSIDE anchor, because a county-specific card DOES answer there; and it must
  NOT be added to the dispatch-county list, which is now a two-directional gate that fails
  on a listed county registering nothing.
- **A parser keyed to a WORD is blind to a COLUMN.** If the extractor needs the literal
  word beside the number — `District 7` — then a page that says it ONCE in a table header
  and prints bare numerals in the cells is invisible, and the record will say the publisher
  offers "no district column" when having one is precisely why it could not be read. Three
  Wisconsin counties sat in a no-source gap for that reason. Before writing a publisher off
  for shape, ask what shapes the reader can actually see, and add the table reading: pair
  the numeral cell with the nearest name cell, **stopping at the next numeral** so a row
  with no readable name can never borrow its neighbour's.
- **Roles are often published OUTSIDE the rows they belong to.** A body's chair and vice
  chairs frequently sit in an officers block above the member list rather than beside the
  member's own row, so an extractor that only sees a role attached to the name it is
  reading will find none — and any downstream rule keyed to "the roster marks no chair"
  then fires wrongly. In Wisconsin that rule WITHHELD the chair on counties whose pages
  name one in plain text. Join the block to the roster on a unique full name, print every
  join, and never overwrite a role a row already carries.
- **The before/after ambiguity follows you into every new block.** Wherever a name and its
  key sit on separate lines, some publishers put the name first and some the key first,
  and the wrong choice yields a full, plausible, entirely wrong answer shifted by one. It
  is pinned per source for district rows — and it recurs, unpinned, the moment you parse a
  new region of the same page: an officers block cost exactly that, filing one county's
  Second Vice Chair as First. Three cases are safe: the line carries its own name (use it
  and look no further); exactly one neighbouring line reads as a name (use that one); both
  do (attach nothing and say so).
- **Nest only on containment the source enforces.** Wisconsin's county subdivisions nest
  under County because 608 incorporated municipalities occupy 671 subdivision records — the
  58 that cross a county line get one record per county. The Places layer is one record per
  municipality however many counties it spans, so it is the one municipal layer that CANNOT
  be nested. Note the cost before nesting: `subOf` hides a child whenever any ancestor is
  off, transitively.
- **Per-county files beat one statewide file for anything a reader consults pointwise.**
  Wisconsin's polling pairing is 72 county files at ~9 KB rather than one at ~950 KB, keyed
  by the same county slug the gaps panel already computes. It also gives each file its own
  count floor in the validator, where a single envelope object would have floored at two.
- **Contiguity is not a shipping gate.** A county joins whenever a county-keyed layer
  answers in it, wherever it sits; the served area can be disjoint, and has been. Islands
  and enclaves are recomputed from the data, never patched — and **read the ring count from
  the builder's `--check`, never from a map in your head.** Predictions about which join
  closes which hole have been wrong three times, each time by reasoning that was true of
  every neighbour taken alone and false of the block taken together.

## 5.5 Process — how knowledge is kept

- **A measurement filed in a backlog and nowhere else is a measurement the next pass
  repeats.** Two counties' board forms sat answered in a backlog for a day while their
  records went on calling the question undeterminable. Findings go where the next reader
  will look: the gap record, the builder's docstring, the WATCH row.
- **A gap record is the only thing that makes an absence visible.** Four served counties
  were missing their precinct layers for weeks with no refusal, no missing publisher and
  every gate green — simply nothing on file to notice. The audit worth repeating is: which
  units are served but lack layer X, AND lack a record explaining why?
- **Record the blocker you MEASURED, not the one you inferred.** A sweep of twelve counties
  shipped three and produced nine honest no's, and the nine were most of the value: each now
  carries a measured blocker instead of a guess. "Unresponsive", "licence-gated",
  "split-precinct", "raster-only" are different claims with different routes out; "no source
  exists" is almost never one of them.
- **Re-examine written-off units when the METHOD changes, rather than re-probing them.**
  Five counties are shut because their districts split precincts. That is not a reason to
  re-run the same probes; it is a reason to ask a different question — do they publish a
  VECTOR map? — which is how a sixth shipped.
- **Correct the record in the same change that disproves it.** Several records here were
  wrong for weeks in ways nothing could catch, because the thing they described was a
  website, a name, or an assumption. When a build disproves its own gap record, rewriting
  that record is part of the build, not follow-up work.
- **A gate's own coverage is a claim nobody measured.** Every gate here answers "is X
  true of the things I look at", and what it looks at is a list somebody wrote once.
  Three fired on the same day. Wisconsin's robots gate proved every scraped host is
  permitted, and could not see a host moved onto the excluded list and left registered as
  a live carrier. The directory cross-check compared 41 counties against the scraper and
  was blind to the 8 that ride a different table, so a wrong hostname in either could not
  disagree with the other. And `validate_index.py` checks that each data file sits in
  exactly ONE of the service worker's two lists — a real question, and a different one
  from whether the cache version moved, so five merged PRs rewrote a cache-first file
  and none bumped it. **Ask of every gate: what is IN its surface, how did it get there,
  and what is the shape of the thing that would be outside it?** Then negative-test the
  surface itself — remove a known-good entry and confirm the gate notices — not only the
  rule. **And so is every list that says WHICH THINGS the gate looks at.** A 2026-09-02 audit of the gates themselves found four such lists unmeasured: nine places enumerate the fleet and only five derive it, two instances shipped a provenance page no validator checked, the coverage ring's own gate validates a hand-kept anchor list and ran in no workflow at all, and the county-coverage check was a VACUUM in two of three statewide instances — walking an empty dispatch table and printing "0 dispatched counties all inside the coverage ring" as though it were a result. **A check that cannot fail is worse than a missing one, because its green is read as evidence.** All four were green at the time; three had already shipped a real fault earlier. **A gate's EXCEPTION list is part of that surface too.** The retention gate's accepted
  drops are consulted only where a diff observes the field going away, so the day after the
  drop merges nothing observes it and the exception goes silent forever — a permanent hole
  in the gate with no line anywhere saying so, and a docstring claiming the opposite. Every
  exception list in this repo now re-checks itself against the SHIPPED tree and fails on an
  entry that is orphaned (its file or its source is gone) or stale (the thing it excused is
  back), which `validate_card_links.py` and `validate_contrast.py` already did.
- **A check that has never failed has not been tested, and neither has a retry path.**
  The cache gate above was written, its negative test passed, and it failed on its first
  real use: it read the committed `HEAD` where a merge gate must read the working tree,
  and in CI those are identical, which is exactly how such a gate looks green forever
  while measuring nothing. Its negative test had passed for the wrong reason too — the
  file it perturbed happened to be current on `main`, so nothing differed. The same shape
  with the opposite sign: a scraper's live-retry path, guarded by "this county will
  probably keep refusing", carried a crash for weeks and ran **on the single day the
  county's challenged page answered** — a rung that exists for one day in a hundred must
  be exercised on the other ninety-nine, by forcing it. Prove a failure the gate must
  catch, on the tree shape it will actually see; a green you have not made go red is a
  green you have not read.
- **A RED from a hand-built harness is more likely the harness than the code.** The rule
  above says prove a gate can fail; its twin says do not believe the failure until the
  harness itself is witnessed. Three times in one session an ad-hoc verification returned
  a confident negative and was wrong every time, and each first reading was "the new code
  is broken". An isolated call to a new validator check was handed the repo ROOT as its
  `repo_root`, so it read the reference instance's county list instead of the instance
  under test and reported eleven spurious failures. A browser harness stubbed a Census
  service with Esri-shaped JSON where the loader asks for `f=geojson`, so the layer found
  no feature and the card fell back to its empty note — which looks exactly like a broken
  join. The same harness then keyed a municipality by a GEOID typed from memory
  (`5530250` for a Greendale that is `5531125`), so the lookup missed and the officeholder
  row was absent — which looks exactly like a broken render. **Before believing a harness's
  no, make it say yes about something already known true**: point it at a case that must
  pass, and only trust the failure once the control passes beside it. A harness is written
  in minutes and reviewed by nobody; the code it doubts has usually been through a gate.
- **Before changing shared code, look for the shared answer.** A name-validity helper
  used by every county was loosened to admit one county's `John (Jack) Bomberg`, whose
  per-token test rejects `(Jack)`; the change shadowed an existing nickname pattern and
  broke name detection fleet-wide. The file already contained a helper written for exactly
  that class of name — a parenthesised nickname, stripped for the TEST while the county's
  own spelling ships — added for another county's `Melvin (Bob) Frank` weeks earlier. The
  cost is not the bug — that was caught in minutes — it is that a shared function is the
  one place where a local fix is a fleet-wide change, and the second implementation is
  usually already there. **Grep the shared module for the problem before editing it for
  the case.**

---

# PART 6 — Shared machinery (every path)

## 6.1 Worksheet + generated regions

Per-instance facts live ONCE in `<tag>/metro-worksheet.json` (Illinois's is the root
`metro-worksheet.json` — §0.1's asymmetry); `GENERATED:BEGIN/END` regions in `index.html`,
`sw.js`, `sources.html`, `validate_index.py`, `smoke_test.mjs`, `CLAUDE.md` and `README.md`
are emitted from it. **Never hand-edit a generated region** — edit the worksheet and run
`python3 scripts/generate_metro_files.py` (`--check` is the CI drift gate; `--sync-fleet`
propagates fleet-manifest changes).

A layer cannot ship without a worksheet `layers[]` row carrying a `source` block — the
generator refuses otherwise, and that row is what puts the layer on `sources.html` and into
every gate.

## 6.2 The engine

One copy, under `engine/`, spliced into every instance by `scripts/compose_app.py`
(`--check` is the CI drift gate). **Edit the block under `engine/` and recompose**; never
edit inside an `ENGINE:BEGIN/END` fence in an instance file. Parity holds because there is
nothing to keep in sync, and the committed bytes are the deployed bytes — a fence edit now
actually reaches production, where the retired release channel used to overwrite it at
deploy time.

Consequences worth stating: an engine change is a **fleet** change, so it must be right for
every instance, and the instance-neutral way to add behaviour is an optional field a layer
opts into (`emptyNote`, `coverage`, `subOf`, `pointOfInterest`'s optional coordinates) —
layers that declare nothing behave exactly as before. `docs/ENGINE_SYNC.md` remains the
authoritative engine document: block inventory, new-block seeding, the tombstone convention
for retiring helpers.


## 6.3 The pipeline pattern (every roster)

**Scraper** → raw intermediate JSON, one record per member with `source_url` +
`scraped_at`; unfindable fields are `null`, per-member failures become `{error}` records
— never dropped or invented members. **Builder** → `data/app/*.json`, refusing to
overwrite below its count floor (floors are deliberate under-tolerances so vacancies
don't wedge the weekly run; placeholder rosters get floor 0, raised after first scrape),
stable key order for clean diffs. **Weekly workflow** → fixed `bot/*` branch, force-push,
**opens a PR, never commits to main** — officeholder data always gets human review.

**Fetch-engine escalation ladder** (cheapest that works, recorded per target): plain
requests (`ilga_scraper.py` template) → `--engine auto` requests+Playwright fallback
(`cpd_district_scraper.py`) → Playwright day one (known bot-block) → Internet Archive
SPN rung for total blocks (`kendall_county_board_scraper.py` — with the 45-day age guard
and standing-issue conversion, §3.3) → **rejected** (key-gated AND WAF-hard),
documented with the alternative. When the official site is unscrapeable, a maintained
open aggregator honestly supplies *structured* fields (Open States, congress-legislators)
while the official site stays the card's link target. **Ship keyed enrichments dark** —
a missing secret degrades to the unenriched roster. Key hygiene: app tokens are public;
real API keys are repo secrets, never in `index.html`.

**Freshness chores:** year-versioned Socrata datasets get a monthly successor check —
fire on a **newer edition in the catalog or a 404, never on age** (age alone cries
wolf). ArcGIS analog: record layer URL + item id; treat an HTTP-200 JSON *error body* as
unreachable; search the owning org's catalog for a successor item. Both surface as
tracking issues (`validate_sources.py` + `validate-sources.yml`), never auto-edits —
dataset swaps are schema-sensitive.

## 6.4 Routes to data — the determined map

Every datum a card surfaces has a determined route family. Work each column top-down —
take the first route that honestly works, record the outcome, and never invent what no
route provides. Fetch posture for anything scraped is always the §6.3 engine ladder;
the verification bar for any source is §2.6.1 (VERIFIED means *you* fetched it and saw
records); freshness watching is §6.3's chores.

| Data | Routes, in preference order | Governing rule | Shipped precedents |
|---|---|---|---|
| **District boundary — statewide concept** | TIGERweb `STATE='NN'` live → pre-built statewide file (`build_legislative_boundaries.py`, cache-first) | FREE class (§3.3); 2,000-point simplification gate on pre-built (§2.5) | chambers + congress; county/township/municipality/school-district/ZCTA |
| **District boundary — county/city concept** | county or city GIS service (dispatch entry) → pre-built static from the enacted shapefile or a one-time download (throttled/CKAN/permission-locked class) → county Clerk tax-agency tiling | one district per point (§3.1); municipal rows per the complete-tiling rule (§1.5); every id in the `validate_sources.py` manifest | county boards; Kane/McHenry subcircuits pre-built; Cook fire/park/library/TIF tilings |
| **Officeholders (any elected body)** | boundary-GIS attributes verified against the published directory → official directory scrape (weekly review-PR) → maintained open aggregator for *structured* fields only → hand-verified transcription (terminal case: 45-day age guard + standing issue) → link-only floor | rule 4 (§3.3): decided and built with the boundary; never guessed; per-field honesty; count floors | Lake/Kane GIS attrs; ILGA/CPD/county-board scrapers; Open States + congress-legislators; Kendall/McHenry rosters; `il-supreme-court` link-only |
| **Municipal governing bodies** | the five-rung ladder: clerk elected-officials API → clerk yearbook/directory → COG directory → county-GIS contact attributes → link-only | §3.4: GEOID-keyed, deepest-source precedence, statewide aggregators are a recorded dead end | Cook DOEO; Will directory; DMMC; Lake GIS |
| **Office location + contact** | the roster's own source, never backfilled from a weaker one; unit-level contact renders once on the hall/office row; per-seat contact only where the source is per-member | §0.4 per-field honesty; §3.4 schema rules | congress district offices (congress-legislators join); Evanston per-seat contact |
| **Election administration** | authority-keyed sources (ISBE's election-authority directory is the roster of authorities) → county polling-place joins where published → hand-curated per-election site files | §1.3 dispatch-by-authority; human-review PRs | county-clerk roster; Kendall's GlobalID polling join; `early-voting` |
| **Amenity points (nearest-N)** | national USGS structures layers (bbox-widened) → city/portal point datasets (`makeSocrataPointLoader` class) | nearest-N honesty: N small, "as the crow flies" on the card | police/fire stations + post offices (USGS); CPL `library`, `school-site` |



## 6.5 The gates

Run these before every merge; `smoke-test.yml` runs them on every PR and push to `main`.

| Gate | What it catches |
|---|---|
| `generate_metro_files.py --check` | a hand-edited GENERATED region |
| `compose_app.py --check` | an instance file whose fences drifted from `engine/` |
| `<tag>/scripts/validate_index.py <tag>/index.html` | parse errors, `registerLayer(` floor, rank lists not 1:1 with registered ids, inline datasets, missing `data/app` files or wrong counts, sw exactly-one-list, dispatched counties outside the ring, a layer with no `sources.html` row |
| `node <tag>/scripts/smoke_test.mjs` | boot, exact layer count, ground-truth classification, negative point, failure isolation, coverage-hide, permalink stability |
| `build_coverage_gaps.py --check` | a gap record that drifted from the guidebook |
| `check_roster_retention.py --base origin/main` | a roster field that silently stopped being published |
| `check_cache_version.py --base origin/main` | a cache-first data file changed without its instance's `CACHE_NAME` |
| `validate_instance_registration.py` | an instance folder that some table, the fleet manifest or a CI list does not name |
| `build_metro_outline.py --check` (per statewide instance) | the shipped ring, and an anchor list that has drifted from `METRO_COUNTY_FIPS` |
| `validate_sources.py` | a superseded dataset, a dead source, a `blocked` source becoming reachable |
| `validate_card_links.py` | a URL a reader would click that no longer resolves |
| `validate_workflow_deps.py` | an instance script importing outside its own tree |
| `build_landing_page.py` / `build_privacy_page.py` / `build_manifests.py` / `build_dark_map_palette.py` `--check` | root and per-instance generated pages, and a layer colour with no dark twin |
| `landing_test.mjs` / `page_consistency_test.mjs` | the root's generated pages in a real browser |

**Three gates deserve their reasoning.** `check_roster_retention.py` exists because every
other roster guard floors a COUNT: a county's seven published e-mail addresses once went
empty while seven rows in, seven rows out kept every floor satisfied. It measures **per
source**, not per file — pooled across a shared roster file, one county's vanishing column
reads as an 18% dip that passes everything; and its `ACCEPTED_DROPS` entries are re-audited
against the shipped tree every run, so an exception cannot outlive its reason in silence.
And `validate_sources.py` inverts for sources
carrying `"blocked"`: unreachable is reported OK and **reachable-again is the WARN**, because
that is the state a human can act on. Without the flag the monthly issue reopens with the
same no-op warnings forever, which is how a report stops being read.

`check_cache_version.py` guards the one thing a cache-first policy costs, and it is the
gate an expansion is most likely to need. **Cache-first data has a second, invisible
shipping step.** Each instance's service worker serves rosters network-first, so a changed
officeholder reaches a returning visitor at once, and serves boundary geometry cache-first,
which is instant and works offline and reaches that visitor **only when `CACHE_NAME`
changes**. `metro-outline.json` — the coverage wash — is cache-first, and every county a
state adds rewrites it. Wisconsin added seven counties across five PRs; every one rewrote
that ring, none bumped the cache, and returning visitors got the new supervisors on their
cards and the old wash on their map, **greying out the very counties that had just been
added** — the app contradicting itself with every gate green. The gate takes the cache-first
list from the BASE's `sw.js`, because that is what a returning visitor already holds; it
asks for no bump on network-first files, whose weekly roster PRs would turn the bump into
noise nobody reads; and it requires a DIFFERENT name, not an increment, because any
different name evicts the old cache. **For an expansion the rule is simply: if the change
touches a file in `GEOMETRY_URLS`, the same change bumps `CACHE_NAME`.**

## 6.6 Post-expansion operations

Every expansion leaves standing obligations, and they are the difference between a layer
that stays true and one that quietly rots:

- the **weekly roster workflows** it added (staggered cron slots; the live schedule is the
  instance CLAUDE.md's generated metro-facts block) — always opening PRs, never committing
  to `main`;
- its `validate_sources.py` manifest rows;
- **`<tag>/WATCH.md`** — the instance's operations calendar. Anything with a date, a filing
  window, or a per-election refresh belongs here with its last-run value recorded, because
  the calendar is the only thing that fires for data no gate can check;
- guidebook rows kept current — coverage map, inventory, matrix, and the gap records with
  their county lists;
- **redistricting exposure**: every new boundary layer gets a blast-radius row in
  `docs/REDISTRICTING_RUNBOOK.md`, and pre-built geometry ties its rebuild to that runbook's
  triggers (decennial, court-ordered, administrative, annual school-zone rotation).

---

# APPENDIX A — Worked example: the reference instance's layer classification (2026-07-27)

Classification is this guide's; **counts, sources, and roster provenance live in
`docs/DATA_LAYER_GUIDEBOOK.md`** (machine-checked weekly). Statewide story: DONE =
already statewide · ENTRY = counties join as dispatch entries · ROSTER = counties join
as roster rows · GATED = honest instance of a general concept, generalized through a
different concept/card · UNIQUE = recorded Chicago/Cook-only.

### Political (11)

| id | Answers | Level | Elected by | Statewide story |
|---|---|---|---|---|
| `congress` | your U.S. House rep | Federal | district | DONE |
| `il-senate` / `il-house` | your state legislators | State | district | DONE |
| `il-supreme-court` | your Supreme Court district | State (judicial) | district (5) | DONE · Appellate-row candidate (§1.5) |
| `judicial-subcircuit` | your resident-judge subcircuit | State (judicial), county-organized | subcircuit; structurally n/a in some circuits | ENTRY · statewide circuit DERIVE blocked |
| `county-board` | your county-board district + member | County | district (metro); commission counties at-large | ENTRY where districted · county-card rows where at-large |
| `ccbr` | your Board of Review district | County | district — elected only in Cook | UNIQUE · elsewhere appointed → link row at most |
| `school-board` | your ERSB district + member | School district | district — IL's only districted school board | UNIQUE as polygon · elsewhere Pattern A (§1.5) |
| `ward` | your alderperson / council member | Municipal | ward or council district | ENTRY — the consolidated municipal-ward concept, dispatch keyed by municipality (Chicago + suburban Cook + Evanston + Will cities + Aurora shipped 2026-07); new ward-publishing sources join as entries |
| `ward-precinct` | your Chicago precinct | Election administration | n/a | GATED — authority-dispatched concept (§1.3) |
| `early-voting` | nearest early-voting/drop-box sites | Election administration | n/a | GATED — per-authority files (§1.3) |

### Safety (7)

| id | Answers | Level | Elected by | Statewide story |
|---|---|---|---|---|
| `police-district` | your CPD district + station | Municipal dept | n/a (labeled) | GATED — general concept = card rows + Sheriff (§1.5) |
| `police-beat` | your CPD beat | Municipal dept | n/a | UNIQUE (`subOf police-district`) |
| `ccpsa-district-council` | your elected police-oversight council | Municipal | district (22) | UNIQUE — no analog anywhere in the fleet |
| `fire-district` | which FPD taxes/serves you | Special district | trustees typically appointed; card follows source depth | ENTRY · municipal fire depts excluded by rule |
| `dupage-county-special-police` | township special-police tax area | Township special district | n/a (funds elected Sheriff) | single-county; converts only on a second analog |
| `police-station` / `fire-station` | nearest stations | amenity | n/a | DONE-capable (USGS national; bbox widens) |

### Schools (9)

| id | Answers | Level | Elected by | Statewide story |
|---|---|---|---|---|
| `school-district-{unified,secondary,elementary}` | which district serves/taxes you | School district | board elected whole-district (ERSB the exception) | DONE (identity) · Pattern A enrichment candidate |
| `cps-network` / `cps-hs-network` | your CPS admin network + chief | District internal | n/a (appointed, labeled) | UNIQUE (mega-district phenomenon) |
| `cps-elementary` / `cps-middle` / `cps-high` | your zoned school | School district | n/a | GATED — per-district opt-in class, never statewide |
| `school-site` | nearest schools | amenity | n/a | Chicago-sourced · statewide source candidates recorded |

### Geography (12)

| id | Answers | Level | Elected by | Statewide story |
|---|---|---|---|---|
| `county` | your county + clerk | County | clerk county-wide | DONE · officer-roster enrichment per rule 4; at-large boards land here |
| `township` | your township / county subdivision | Township | officers township-wide | DONE (identity statewide + officers for Cook 2026-08-19, township-officials.json; further counties via clerk yearbooks/GIS — Tazewell next recorded); Chicago structural empty |
| `municipality` | your municipality + its government | Municipal | head municipal-wide; board at-large or by ward | DONE (identity) · ROSTER per county (§3.4) · Chicago head + citywide officers SHIPPED |
| `county-precinct` | your voting precinct (+ polling place) | Election administration | n/a | ENTRY per authority · Kendall polling-place join is the model |
| `park-district` | which park district serves you | Special district | elected commissioners | ENTRY · McHenry recorded gap |
| `library-district` | which library body taxes you | Special district | district trustees elected; municipal funds appointed | ENTRY · complete-tiling rule |
| `mwrd` | in/out of the MWRD | Special district | nine at-large commissioners → link row | Cook body UNIQUE; class conversion trigger (§1.5) |
| `tif-district` | your TIF district | Municipal finance overlay | none | Cook today · Kendall conversion trigger |
| `community-area` | your Chicago community area | Reference | none | UNIQUE — correctly city-only |
| `zip-code` | your ZCTA | Reference | none | DONE |
| `post-office` | nearest post offices | amenity | n/a | DONE-capable (USGS national) |
| `library` | nearest library branches | amenity | n/a | Chicago (CPL) · statewide candidate recorded; `library-district` answers governance |


# APPENDIX B — Doc map

**This guide is the only entry point for expansion work.** Deliberately separate, live:

- `docs/DATA_LAYER_GUIDEBOOK.md` — the fleet layer **registry and record**: coverage map
  (machine-checked weekly), concept × instance matrix, recorded drops, the gap records with
  their county lists, and the backlog. Updated in the same change as any layer
  add/rename/remove. **When this guide and the guidebook disagree, the guidebook is what
  was measured.**
- `docs/DEV_PROCESS_ASSESSMENT.md` — the consolidation decision record (R2.1/R2.3/R5): why
  the forks, the template repo and the engine release channel are gone.
- `docs/ENGINE_SYNC.md` — the engine **protocol**: block inventory, new-block seeding, the
  tombstone convention for retiring helpers.
- `docs/CARD_RENDER_API.md` — the card-helper **API reference**.
- `docs/REDISTRICTING_RUNBOOK.md` — the boundary-change **ops runbook** (blast-radius
  inventory, decennial + off-cycle triggers).
- `docs/COUNTY_STATUS.md` — the generated per-county view for the reference instance
  (service tier, board posture, dispatch entries, open gaps). Generated by
  `scripts/build_county_status.py`; never hand-edited.
- `<tag>/WATCH.md` — the instance's operations calendar. `<tag>/CLAUDE.md` — the instance's
  agent brief plus the generated metro-facts block (live counts and workflow schedules).
- `docs/WI_PHASE2_PLAN.md`, `docs/WI_PHASE4_PLAN.md` — worked phase plans for a
  statewide-first instance; useful as shape, not as a checklist to re-run.

**History & records** (frozen, provenance only): `docs/archive/` —
`METRO_EXPANSION_PLAYBOOK.md` (original Part I plus the NYC worked example Part II),
`METRO_EXPANSION_NYC.md` (NYC thread log), `METRO_EXPANSION_SF_WORKSHEET.md` (a completed
port worksheet), `STATEWIDE_EXPANSION_PLAYBOOK.md`, `COUNTY_LAYER_CONSOLIDATION.md`,
`MUNICIPAL_COUNCILS_PLAYBOOK.md` (decision records this guide absorbed),
`MECHANIZATION_PLAYBOOK.md` (conversions 1–3, done). Root-level:
`docs/BUILD_PLAYBOOK_1.md` (original build log; the instance CLAUDE.md wins on contract
language), `docs/OPTIMIZATION_PLAYBOOK.md` + `docs/PERFORMANCE_ANALYSIS_2026-07.md` (dated
measurement records), `docs/COUNTY_SEALS_REVIEW.md` (marker-art tracker),
`docs/engine-changelog/` (per-release notes from the retired channel),
`docs/design_handoff_*/` (design records).
