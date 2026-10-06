---
name: boundary-change
description: Respond to a boundary change in any instance — a redistricting, a court-ordered remap, a TIGERweb vintage roll, a Socrata dataset-id rotation, an LTSB filing, an administrative district reorg — by classifying how the layer ships, rebuilding it through each builder's own gate, bumping the service-worker cache the RIGHT way, re-anchoring the smoke test, auditing roster join keys, and landing it without stale maps. Use it for "CPS posted the SY2627 boundaries, run the drill", "TIGERweb rolled to CD120, the congress layer is stale", "LTSB republished after the July filing", "Council passed the new ward map, effective 2027 — what breaks", "Kane redrew its subcircuits", "P.L. 94-171 data landed". It carries the drill's corrected mechanics — docs/REDISTRICTING_RUNBOOK.md still says to bump sw.js by hand, and that is a GENERATED region — and points at the runbook's tables, never copies them. Not for adding a county (county-n-plus-1), a new layer (new-layer), or a red PR (steward).
---

# When a boundary moves

`docs/REDISTRICTING_RUNBOOK.md` holds the decennial timeline, the off-cycle
triggers, the per-instance blast-radius inventories and the appendix of
authorities — read them there. Measured 2026-09-02, three of its MECHANICS
are wrong in the direction an agent following it would fail a gate: it says
to bump `CACHE_NAME` in `sw.js` (a GENERATED region — the bump is a worksheet
key), it says one of three anchors is registered in the embedded-boundaries
builder (all of `LAYERS` there is), and it promises a detection layer that
was never built; and it has no section for every instance (`ia/WATCH.md`
cites it anyway). Re-check with
`grep -n "CACHE_NAME\|1 of its 3\|expected_successor\|### IA" docs/REDISTRICTING_RUNBOOK.md`
before trusting either the runbook or this paragraph. This carries the drill
with those corrected, each section naming the runbook steps it replaces so a
WATCH row's "Steps 2–6" resolves. `CLAUDE.md` carries the cache-first /
network-first split, the freshness gate and the worksheet mechanism.

## 0. Open the instance's calendar first

The row for the source that moved — root `WATCH.md` for Illinois, `wi/WATCH.md`,
`ia/WATCH.md`, `ca/WATCH.md`, `ny/WATCH.md` — names the builder to re-run and
its gates, and has a date column to stamp at the end ("Last done", or the
"Done" tick in the root file's fixed-checkpoint table). A checkpoint with a
stale date is a checkpoint that didn't happen.

## 1. Enactment and effective date, separately, citing the instrument (runbook 1)

Ordinance, public act, court order, statutory filing. The policy is
show-current-until-effective; record both dates before touching geometry.
Dual-map display is out of scope without an explicit instruction.

## 2. Classify how the layer SHIPS — by a test, not by concept (runbook 2)

A layer whose file appears in the instance worksheet's `data_files.geometry[]`
is PRE-BUILT: its `WATCH.md` row and the file's worksheet `note` name the
builder, which is the intake. Wisconsin and Iowa pre-build even their county
fabric and school districts; only Illinois fetches its county layer live, so
never classify by concept name. A layer with no file is live-fetched and a
vintage roll reaches it on its own — EXCEPT that a live loader carrying a
`where=` vintage filter or a numbered historical layer index (grep the loader
for `status=` / `Historical`; Kendall's precincts and suburban Cook's are the
Illinois cases) still needs a code re-check on a redraw. Shapefile-derived
layers: the archive goes in `il/data/source/raw/` under a name encoding layer,
vintage and enactment citation, the full-precision GeoJSON in `il/data/`, then
its `LAYERS` entry in `scripts/build_embedded_boundaries.py` — whose `source`
paths read `il/data/*.geojson` (fixed 2026-09-02; they used to read
`data/*.geojson` off the repo root and die with a FileNotFoundError before
mapshaper ran).

## 3. Acquire in this order, and never trace (runbook 3–4)

The enacting body's own shapefile or service → the portal's new dataset id →
the TIGER/Line vintage. `docs/IL_COUNTY_RECORD.md` (Vermilion, Douglas) carries the catalogue-then-org order for
finding a publisher's service. Never scrape or trace a rendered map; the
county builders enforce the same.

## 4. Rebuild and let each builder's OWN gate decide (runbook 5, 6, 8)

The gates differ, and the refusal you get says which: the simplification
builders (`scripts/build_embedded_boundaries.py` and the three legislative
builders, `scripts/build_legislative_boundaries.py` and its `wi/scripts/` and
`ia/scripts/` copies) validate 2,000 seeded points against the
pre-simplification source at ≥99.5% with zero double-classification; the
Wisconsin dissolves sample larger sets at 99.9% and tolerate overlaps
inherited from the source; the county dissolves gate on composition
witnesses, the Jasper test and the population ceiling. Read the builder's
docstring for what it refuses on, and never move any of those numbers to
pass. `min_features` is a floor in Illinois, a +1 band in Wisconsin and an
equality in Iowa — set it to the apportioned count with a comment when a
remap changes seat count, never raise it past a failure.

## 5. The two rolls that recur (runbook 2, 10, 11)

**TIGERweb Congress.** The Congress-numbered field is whatever
`LAYERS['congress']['fields'][0]` says in the three legislative builders;
confirm the live name at `Legislative/MapServer/0?f=json`. A stale field makes
TIGERweb answer HTTP 200 with an error envelope, and the builder dies with
"returned no features" — read that as "the vintage rolled", not an outage —
so update `fields` in ALL THREE builders, since each instance ships its own
congress file and cache name; the app's district-number extractor has its
own field list and name-regex fallback. Update the `note` on the TIGERweb
`PROVENANCE` entries in `scripts/validate_sources.py`.

**Socrata year.** The CPS annual rotation is THREE copies, in this order:
before any of them, pull one feature from the new dataset
(`/resource/<id>.geojson?$limit=1`) and confirm every field the
`registerCpsZone` block reads is still present under the same name — the
swap is schema-sensitive and the smoke test never exercises live layers, so
this is the only gate. Then (1) the `datasetId:` literals in `il/index.html`;
(2) the `layers[].source.boundary[]` label and url in `metro-worksheet.json`,
then `python3 scripts/generate_metro_files.py` — that is what `sources.html`
renders, and an unchanged worksheet stays green while citing the superseded
dataset; (3) the id in the `SOCRATA` list of `scripts/validate_sources.py`,
whose manifest-vs-index drift guard is NOT in CI — run
`python3 scripts/validate_sources.py` locally. Grep the old id across the repo
before opening the PR; `docs/DATA_LAYER_GUIDEBOOK.md` and
`docs/BUILD_PLAYBOOK_1.md` carry it as history and may stay. This is the ONLY boundary roll the monthly issue detects on its
own; the runbook's per-source vintage watch was never built.

## 6. The worksheet, never the generated files (runbook 10, 12)

In `metro-worksheet.json` (or the instance's): `data_files.geometry[]`
`min_features` / `max_features` for each rebuilt file (the validator's floors
are emitted from them); **`sw.cache_name`** — `sw.js` serves boundary files from its
cache with no revalidation (since 2026-09-26), so without a bump a returning
visitor keeps the OLD file for good; the bump purges the old cache, the new
file is fetched the first time a layer uses it, and
`check_cache_version.py` fails a change that edits a cache-first file without
one; the
`sw-version-history` TEMPLATE comment in `il/sw.js` is abandoned since the
rebrand — do not extend it; `anchors[].expected`, `anchor_point`,
`negative_point` if an anchor layer moved (they emit the smoke test's
`EXPECT_DISTRICT`, `POINT`, `NEGATIVE_POINT`); `layers[].area_rank` if
relative area ordering changed (`LAYER_AREA_RANK` must stay 1..N with no
gaps); `verified_date`. Then:

```bash
python3 scripts/generate_metro_files.py
python3 scripts/generate_metro_files.py --check
```

Every `<tag>/data/app` file must sit in exactly one of the service worker's two
lists; `validate_index.py` enforces it.

## 7. The regression sentinel — Illinois by hand, elsewhere the anchors (runbook 12)

In Illinois, `MOVE_POINT` and `STRAGGLER_FILE` in `scripts/smoke_test.mjs`
sit in a `TEMPLATE` region, not a generated one: re-classify the landmark
points against the NEW geometry and ADD a sentinel — a point that changed
district across the remap — so the test proves the geometry is new rather
than stale. In `wi/` and `ia/` those names are contract stubs whose check was
dropped; the remap witness there is the worksheet's `anchors[]` —
re-classify `expected`, or add an anchor in the changed layer — or restore
the move-point check from the Illinois file into the instance's smoke test.

## 8. Audit the roster join keys (runbook 9)

Districts can be RENUMBERED, not only redrawn. Check that each scraper and
builder still joins officials to the right district ids. Where a county's
roster builder asserts the precinct composition against its boundary builder,
the weekly job going RED after a remap is the tripwire working: update the
compiled composition, never silence it. Official sources lag a remap, so
spot-check three known officials' districts against news sources before
merging the roster PR that follows.

## 9. Land it, and stamp what the runbook cannot generate (runbook 13–14)

The steward battery, then a PR — officeholder changes stay human-reviewed. In
the same PR: stamp the `WATCH.md` row; update the layer's blast-radius row
and appendix row in `docs/REDISTRICTING_RUNBOOK.md` BY HAND — the runbook
says these become generated once Conversion 2 lands, Conversion 2 landed on
2026-07-13, and the tables were never converted, so a runbook whose tables go
stale on first use has failed its purpose. An instance with no section gets a
Wisconsin-style inventory block. Work one layer at a time; touch nothing that
did not change.

## 10. Nevers this file adds

- Never show a not-yet-effective map; never touch geometry before both dates are recorded.
- Never trace a rendered map, and never take a portal id over the enacting body's own file.
- Never move a builder's gate number — a floor, a band, an agreement percentage — to get past a rebuild failure.
- Never bump `CACHE_NAME` in `sw.js`; bump `sw.cache_name` in the worksheet and regenerate.
- Never ship a remap without a regression sentinel (Illinois) or a re-classified anchor (elsewhere).
- Never silence a composition tripwire that went red on a remap.
- Never swap a Socrata id without checking the new schema, and never in fewer than three places.
- Never leave the runbook's own rows stale in the PR that changed what they describe.
