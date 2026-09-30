---
name: new-state-instance
description: Stand up a brand-new state instance `<tag>/` in this repo — worksheet first, DARK fleet registration, engine composition, the national tier, anchors and the coverage wash, the localization sweep, and go-live as its own change. Use it whenever a task names a state the fleet does not serve, from its very first PR — "stand up Minnesota as mn/", "Indiana PR 1, worksheet and national tier", "bring up mo/", "register Michigan in the fleet", "what does the coverage key need for a two-band state", "Ohio go-live PR", "pick the anchors for the mn smoke test". It carries the bring-up ORDER, the three decisions that come before the first layer, and the registration steps split into what happens dark and what happens at go-live — the split docs/EXPANSION_GUIDE.md Part 2 gets wrong and Iowa's port corrected; Part 2 holds the rules and this says when to open it. Not for deepening a state that already exists (county-n-plus-1), a new layer inside an instance (new-layer), or a red PR (steward).
---

# A new state

The next instance will follow the same twenty-odd steps as the last, and the
failure mode is recorded in the guide's own words: of the registration list,
"every item on that list was missed by a real port." `CLAUDE.md` carries the
instance model, the worksheet mechanism, the engine fences and the layer
contract, and is loaded every turn; `docs/EXPANSION_GUIDE.md` Part 2 is the
bring-up procedure, and `docs/IA_EXPANSION_PLAN.md` is the worked record of
the most recent port, PR by PR. Neither is restated here. What is here is the
ORDER, the three decisions that precede the first layer, and the registration
steps — found by reading the scripts, not the guide, and split into the ones
that happen DARK and the ones that happen at go-live, which is the split the
guide's §2.4 gets wrong.

## 1. Three decisions before the first layer

**Arrival shape** (§0.2). Statewide-first is the default for a state: three
national publishers — TIGERweb, the USGS National Map, the
`unitedstates/congress-legislators` roster — tile every state on day one, so
an instance has honest layers before anyone has been asked for anything.
Statewide-first must not fake depth: a county card that names nobody is
honest; a polygon for a body that elects at large is not. The number of
coverage BANDS is not decided by arrival shape — §7 carries the test.

**Platform** (§2.6): identify the state's portal before wiring a layer, and
read §2.6 for Socrata / ArcGIS / CKAN mechanics and the token rules. Two
halves of it an agent drops: a real API key that 401s without it is a repo
secret and never goes in `index.html` (a Socrata app token is a public
front-end constant); and there is NO token analogue for a public
ArcGIS/TIGERweb/CKAN read — if a public endpoint throttles or WAFs, ship the
layer as a static file instead.

**Geocoder** (§2.6). In order: a state-authoritative keyless geocoder WITH real
autocomplete replaces both reference geocoders; else Photon, state-bounded,
for type-ahead; Nominatim only as a debounced submit-time fallback, on the
serial ≥1 s POI queue its policy requires.

## 2. The instance takes the statewide shape, never Illinois's

Read the instance set — and the Illinois asymmetry (worksheet, scripts and
smoke test at the repo root, a mechanical follow-up rather than a pattern) —
from `INSTANCES` in `scripts/generate_metro_files.py`; the newest statewide
rows there are the worked examples. A new instance is a folder:
`<tag>/index.html`, `sw.js`, `sources.html`, `faq.html`,
`metro-worksheet.json`, `<tag>/data/app/`, `<tag>/data/source/`,
`<tag>/scripts/` (its own `validate_index.py`, `smoke_test.mjs`,
`validate_sources.py`, builders), `WATCH.md`, `CLAUDE.md`. Every instance
script resolves imports inside its own tree; `scripts/validate_workflow_deps.py`
fails a `sys.path` reach into another. Shared machinery is therefore COPIED
into `<tag>/scripts/` or promoted to a root fleet helper — never imported
across trees. `wi/scripts/build_metro_outline.py`,
`wi/scripts/build_legislative_boundaries.py` and
`wi/scripts/build_congress_roster.py` are the copies to start from.

## 3. The worksheet, before any layer

The required keys are the schema's, not the guide's table:
`schema/metro-worksheet.schema.json`, read beside `wi/metro-worksheet.json`
rather than the guide's example column. The keys that carry the decisions:
`this_metro` and `metro_name`; `metro_bbox` and a `permalink_gate` that is
LOOSER than it; `metro_center` framing the WHOLE state; `domains.canonical`;
`brand` (with `brand.instance_tag`) — opt-in, but every state instance sets
it; `brand.analytics.goatcounter_url`, copied from a sibling because the
fleet counts on ONE shared GoatCounter site keyed by path, and never a
`ga_id` (the schema says a rebrand must not add a tracker); `coverage_key`
(§7); `anchors`, `anchor_point`, `negative_point`; `data_files`; `sw`. Two
facts that are NOT worksheet keys: the folder/URL tag is a `metros.json`
fact, and `STATE_FIPS` is a hand-written literal in the state-config block
of the instance's `index.html` (grep `var STATE_FIPS` in `wi/index.html`),
which every TIGERweb query reads.

## 4. Register DARK on day one — every hand-kept list the fleet scripts carry

Fleet-level machinery should DISCOVER instances (`validate_card_links.py`
does), and every hand-kept list that does not is a registration step. The
guide's §2.4 puts `metros.json` on day one; Iowa's PR 0 measured that as
wrong — `render_cards()` in `scripts/build_landing_page.py` and `sync_fleet()`
in `scripts/generate_metro_files.py` filter nothing, so a `metros.json` entry
renders a live landing card the day it lands, and with the folder still
excluded from the deploy that card is a 404. So: nothing that PUBLISHES the
instance until §11. Dark, in the first PR:

- `INSTANCES` in `scripts/generate_metro_files.py` — app, scripts, docs and worksheet paths per instance; nothing generates for a tag that is not here.
- `INSTANCES` and `SUBPAGES` in `scripts/compose_app.py` — the app files and EVERY sub-page; an unlisted tag is skipped by compose AND by its `--check`, so hand-copied fences pass the parity gate green while carrying whatever bytes they were cloned with (Iowa's `faq.html` was found missing from `SUBPAGES` at go-live).
- `INSTANCE_WORKSHEET` in `scripts/build_landing_page.py`; the instance rows in `scripts/build_manifests.py` (PWA icons and `manifest.webmanifest`), `scripts/build_history_page.py` and `FACE_CARRIERS` in `scripts/build_brand_tokens.py`.
- the `INSTANCES` array in `scripts/vendor_leaflet.sh` — until the tag is here the sandbox smoke test really does die on `L is not defined`, and the timeout is yours, not environmental.
- `.github/workflows/smoke-test.yml` — three lines: the instance's `validate_index.py`, its `smoke_test.mjs`, and `python3 scripts/build_coverage_gaps.py --check --metro <this_metro> --out <tag>/data/app/coverage-gaps.json`; an ungated folder merges through CI while nothing looks at it.
- a `<this_metro>` array in the guidebook's `GUIDEBOOK:BEGIN gaps` block (empty is allowed), `coverage-gaps.json` in the worksheet's `data_files.rosters`, and the guidebook's coverage map, inventory, matrix and each drop with its structural reason.
- `.github/workflows/deploy-pages.yml` — one blanket `<tag>/**` line in `EXCLUDES`, so nothing half-built publishes.
- `metro_explorers` in the new worksheet hand-seeded from a sibling's array — exactly what `--sync-fleet` will produce once the instance is in `metros.json`, deferred to go-live.
- a monthly `<tag>-validate-sources.yml` cloned from `wi-validate-sources.yml`.

The list is self-correcting: before the first PR, grep `scripts/` and
`.github/` for the newest tag in quotes (`"ia"` today) — every hit is a row
to add. `docs/IA_EXPANSION_PLAN.md`'s PR 0 is the worked record.

**AND A GATE THAT CANNOT SEE DARKNESS FAILS THE WHOLE FLEET, WHICH IS THE
ARRIVAL'S OTHER COST.** `dark_instances()` in
`scripts/validate_instance_registration.py` is the fleet's definition — it
reads the blanket `<tag>/**` line in `deploy-pages.yml`'s `EXCLUDES`, the one
thing that actually decides whether a folder is published. Indiana arrived on
2026-09-29 as the first dark instance since three other generators were
written, and all three had restated the rule their own way: `build_llms_txt.py`
asserted `metros.json` and the tree are EQUAL, `build_question_forms.py` failed
on an instance "not in metros.json", and `build_sitemap.py` wanted to LIST the
dark folder's pages, which are 404s. All three read `dark_instances()` now. So
on the next arrival, run the whole battery BEFORE assuming the failures are
yours: a red gate naming `metros.json` and the tree in the same breath is
probably a fourth generator that has never met a dark instance, and the fix is
to give it that one reader rather than to publish early.

## 5. Compose, generate, then the national tier

After §4's `compose_app.py` rows exist:

```bash
python3 scripts/compose_app.py               # splice engine/ into every REGISTERED instance
python3 scripts/generate_metro_files.py      # emit every GENERATED region from the worksheets
```

Then ship the national tier first — §2.3 step 4 and §2.6's federal tier name
the layers; a unicameral legislature rides `Legislative/MapServer` layer 1,
so register ONE chamber. Decide the rest of the roster from the guidebook's
concept matrix: walk the reference's layers, map each to the local
equivalent, and DROP, NEVER FAKE, recording each drop with its structural
reason (Wisconsin's drops, §2.3 step 5, are the model).

## 6. Every layer is a worksheet row — and what that row generates

With `sources_page` set — every state instance sets it; it is what generates
`sources.html` — every `layers[]` entry must carry `source` or the generator
refuses. That ordered list IS `LAYER_AREA_RANK` — largest to smallest, every
registered id with no exceptions, sub-layers ranked just before their parent
— and one run of `generate_metro_files.py` emits it along with
`EXPECT_LAYER_IDS`, `MIN_REGISTER_LAYER`, the `sw.js` URL lists, the smoke
test's `EXPECT_LAYERS` and the `sources.html` matrix row. `LAYER_SIDEBAR_RANK`
is hand-edited in the instance's `index.html` (the new-layer skill carries the
placement rule). Factories, `hoverName`, `hoverOfficial` and the
`makeCachedLoader` caveat are §2.2.1's; cards go through the helpers in
`docs/CARD_RENDER_API.md`, data-only, never HTML. Land the cheapest REAL
roster during the module work, not in a later pipeline pass: real data
flushes factory paths a placeholder never exercises.

## 7. Anchors, ground truth, and the wash

Pick at least three API-free anchor layers. The worksheet's `anchors[]` names
each layer and the district expected at `anchor_point`; `negative_point`
must miss EVERY anchor, chosen against a shoreline-clipped layer (mid-water
positives are legally correct on water-inclusive layers). Each anchor is
built by the instance's OWN builder under `<tag>/scripts/` —
`wi/scripts/build_legislative_boundaries.py` is the precedent, carrying the
2,000-seeded-point / ≥99.5% / zero-double-classification `validate()` inline,
and `wi/scripts/build_wi_county_outlines.py` the county-outline sibling.
`scripts/build_embedded_boundaries.py` is Illinois's and writes `il/data/app/`:
read it for the method, never register a state in its `LAYERS`. Every
`<tag>/data/app/` file appears in exactly one of the worksheet's
`data_files.geometry` / `data_files.rosters`; bump `sw.cache_name` on any
change to those lists.

Draw the wash from a purpose-built outline, never from an anchor and never
from stitched per-county files — the engine cancels interior borders only on
EXACT shared coordinates, and independently simplified county files leave
seams. One query, dissolved at build time, simplified hard, and the builder
refuses to write unless one anchor per county still falls inside and known
outside cities fall outside; `wi/scripts/build_metro_outline.py` is the copy
to start from.

Then decide the BANDS by §2.5.1's test, not by arrival shape: three only when
full coverage is a proper subset of a wider region whose layers still answer
throughout. Wisconsin is three bands and NYC and SF are two (§2.5.1's table)
— a two-band key is not a degraded key. Add `coverage_key` to the worksheet
— `outside` required, `region{edge,label,sub}` only for three bands — and do
not derive the words from the metro name. **A three-band instance owes
GEOMETRY as well as words**: the region ring, simplified at the SAME
tolerance as the coverage outline and wired as the second argument of
`drawOutOfScopeMask`. The root `scripts/build_metro_outline.py` shows the
shape (layer 0 of the same MapServer as its second output); the WI ring was
split out by hand and `wi/scripts/build_metro_outline.py` does NOT regenerate
it, so give the copied builder that second output rather than copying the
gap. A declared `region` with no geometry silently yields a two-band key and
no error — check the map, not the worksheet.

## 8. Verify each dataset before wiring it (§2.6.1)

Run §2.6.1's protocol; three of its steps fail silent and are worth carrying.
Sample exact VALUES, not field names — equality is case-sensitive and numerics
arrive as strings. Re-seed the worksheet's `hover_number_keys` and
`hover_name_keys` from OBSERVED keys; a stale list degrades the popup softly
and no gate notices. Verify COVERAGE, not existence — count how many of N
records carry the field and set floors below 100%.

## 9. Re-derive every gate constant; then the two hand audits

§2.2 lists the constants; most are worksheet-emitted, so the write point is
the worksheet (`anchors`, `data_files`, `sw`, `layers`). If re-coring from a
copy, delete only the `registerXxx({…})` calls and their preamble, keep every
factory and loader, then grep the ENTIRE file for now-undefined identifiers
in both directions. No gate covers two things: cross-group parity (for each
field any card renders — address, pin, phone, links — check every other card
that could carry it), and toggling every polygon layer to hover the
ground-truth points for REAL identities — a real port shipped label-only.

## 10. The localization sweep, at assembly and again before launch (§2.7)

Run §2.7 with two corrections. Drop the `data-goatcounter` fingerprint — the
fleet shares one tag, so the sweep would flag the correct value. Add the
SIBLING state's name: Iowa's go-live found `Wisconsin` in its JSON-LD,
aria-label and teaser copy. Never police `<tag>/data/`, and leave the
`TEMPLATE:BEGIN/END` markers alone.

## 11. Verify with the WHOLE battery, then go live as its own change

`.github/workflows/smoke-test.yml` is the source of truth for the battery
and the steward skill's §1 carries its invocations — run that, from the repo
root, one server for every instance; §2.9's list is a subset. `EXPECT_LAYERS`
is asserted exactly and the negative point must miss every anchor. In a
sandbox the SessionStart hook vendors Leaflet ONLY for instances in
`scripts/vendor_leaflet.sh`'s `INSTANCES`; after that, a
`page.waitForFunction` timeout is environmental.

Go-live is its own PR (Iowa's was its tenth), and it is the whole switch, not
one line: narrow the blanket `<tag>/**` exclude in
`.github/workflows/deploy-pages.yml` to the granular set the other instances
use (`<tag>/data/source`, `<tag>/data/state`, `<tag>/scripts`,
`<tag>/data/*.geojson`) and add `<tag>` to its `for published in` presence
loop; add the `metros.json` entry (`tag`, `landing_name`, `blurb`, `scope`,
`url`, `bbox` and the rest, copied from a sibling) and run
`python3 scripts/generate_metro_files.py --sync-fleet`; add the tag to
`AREAS` in `scripts/build_coverage_map.py` (an outline pair, `state_outline`
None for a single-tier instance — a `metros.json` tag in neither `AREAS` nor
`CITY_TAGS` fails its `--check`, and a state is never a marker); every page
the instance serves in `sitemap.xml` (`scripts/page_consistency_test.mjs`
derives its page list from it); README's fleet-table row and its
"<n> instances" prose, which `python3 scripts/build_county_status.py --check`
scans — Iowa shipped while README said "four instances" and every gate stayed
green. Then regenerate `python3 scripts/build_landing_page.py`,
`python3 scripts/build_privacy_page.py` and `python3 scripts/build_coverage_map.py`
— the privacy page is MEASURED from the shipped `index.html`, so it reflects
the instance only once its analytics and geocoder posture are real — and
write `<tag>/CLAUDE.md`, `<tag>/WATCH.md` and the phase plan as
`docs/<TAG>_EXPANSION_PLAN.md` (`docs/IA_EXPANSION_PLAN.md` is the precedent).

## 12. Nevers

- Never copy the Illinois root layout; never copy a gate constant, a floor, or a hover-key list from a sibling.
- Never publish the instance before go-live: no `metros.json` entry, no `--sync-fleet`, no `AREAS` row while the folder is excluded from the deploy.
- Never register a state in Illinois's `scripts/build_embedded_boundaries.py`; never import across instance trees.
- Never fake depth — no polygon for an at-large body, no name for an office nobody publishes.
- Never stitch county outlines into a wash; never derive the coverage key's words from the metro name.
- Never put a real API key in `index.html`; never add a `ga_id`.
- Never police `<tag>/data/` in the localization sweep, and never sweep the `TEMPLATE` markers away.
- Never run §2.9's subset and call it verified.
