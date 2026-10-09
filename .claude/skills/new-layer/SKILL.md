---
name: new-layer
description: Add a NEW layer, toggle or concept to an instance — starting with the test that decides whether it is a layer at all (most proposals are a dispatch entry or a card row), then the factory, the card, the sidebar position, nesting, and the same-change bookkeeping split three ways — what the worksheet GENERATES, what OTHER generators re-derive, and what is hand-edited. Use it for "add an appellate-district layer to il", "wi: new layer for technical college districts", "is ROE a layer or a county-card row?", "where does community-college sit in the sidebar", "nest mpd-squad-area under mpd-district", "validate_index says LAYER_SIDEBAR_RANK is missing an id", "add the guidebook matrix row for ia-judicial-district", "should mwrd become a sanitary-district concept now that a second county publishes one", and for changing what an EXISTING layer's card renders. Not for a county's dispatch entry into a shipped concept (county-n-plus-1), a new state (new-state-instance), restyling an existing layer, or a red PR (steward).
---

# A new layer

`CLAUDE.md` carries the layer contract, the factories by name, the card order,
the honesty rules and the worksheet mechanism, and is loaded every turn;
`docs/EXPANSION_GUIDE.md` §2.2.1 carries the factory patterns and Part 4 the
new-concept procedure. This carries what an agent gets wrong at the moment it
is asked for "a new layer": it skips the gate (most proposals are not
layers), forgets the one rank list the worksheet does not generate, misses
the OTHER generators that read the same worksheet, and never writes the
guidebook rows that only the weekly fleet-status run notices, a week later.

## 1. Run the gate before writing code — §1.6, five questions

1. **Level and function** (§1.1). If it duplicates a concept that exists at that level, it is a dispatch entry (county-n-plus-1) or a card row. Stop; no layer.
2. **Election geometry** (§1.2) decides the surface. DISTRICTED → a polygon concept layer. AT-LARGE → roster rows on the unit's identity card, never a polygon. APPOINTED → labelled rows or links only. PARTY OFFICE (committeeperson and the like) → out of scope by standing decision.
3. **Dispatch dimension** (§1.3): by county (`registerCountyLayer`), by municipality (a place-GEOID join or entries keyed by municipality), by election authority (coverage carved out of the county, the `suburbanCookCoverage` shape), or none (one statewide source).
4. **The officeholder story**, decided AND built in the same change (§3.3, rule 4). The honesty floor is a link plus a recorded gap.
5. **The record**: a guidebook row (three edits, §5), and an Appendix A row for the reference instance.

A dedicated single-county layer converts to a dispatched concept when its
SECOND county ships; the current single-county layers and their conversion
triggers are §1.5's list. Never create a second dedicated layer for the same
class (§1.5, §3.2).

## 2. Check the record before researching

`docs/DATA_LAYER_GUIDEBOOK.md` — the concept coverage matrix, its Pattern
legend (which factory each shipped sibling used), the parity debts and the
backlog. A sibling that SHIPS the concept: reuse its pattern and source
notes. A sibling that recorded NO HONEST ANALOG: check whether the rationale
applies here before re-researching. A cell already marked not shipped carries
a measured route; start from it.

## 3. Launch consolidated, through a factory — §2.2.1, plus two rules it buries

A genuinely new concept launches with a `registerCountyLayer` dispatch table
from day one if it is multi-source, entries via `polygonCountyEntry`, and
through a factory where one fits (`CLAUDE.md` names them; §2.2.1 has the
non-factory patterns worth copying). Two rules an agent misses there: the two
school factories build loaders through the Socrata-only `makeCachedLoader`,
so on another portal convert to an injected loader as `registerPolygonLayer`
accepts; and a bespoke block that joins a roster declares
`hoverOfficial{load?, name()}` prefetched on toggle-on, so hover never fires
a network request, with `hoverName` read from the SAME properties the card
reads. Declare an honest `coverage(point)`.

## 4. The card

Order and helpers are Part 4 step 4 plus `docs/CARD_RENDER_API.md`'s
"Pattern → caller mapping" — pick the helper by pattern from that table and
never bypass one; helpers are data-only by contract. Editing an existing
card is the same vocabulary. If the source carries identity, location or
contact the card does not yet show, record the gap in the guidebook backlog
rather than shipping silently.

## 5. Bookkeeping in the same change — three classes, not two

**Generated from the worksheet.** Add a `layers[]` entry to the instance's
`metro-worksheet.json` (the root one for Illinois): `id`, `label`, `group`,
`area_rank` are required; `source` needs `answers` + `boundary`, `people`
unless the concept names nobody, `applies` for a coverage-gated layer — and
with `sources_page` set (every state instance sets it) the generator refuses
a layer without `source`. `area_rank` must stay exactly 1..N with no gaps or
duplicates: insert by renumbering everything below the new rank, never by a
half-step or a duplicate. Bump `min_register_layer` if the layer uses a bare
`registerLayer(` call; add to `hover_name_keys` / `hover_number_keys` only if
the generic hover path needs a new property; a `<tag>/data/app` file goes in
`data_files.geometry` (with `min_features` / `max_features`) or
`data_files.rosters` (with `min_keys`), and a pre-built geometry file passes
§2.5's 2,000-point / zero-double-classification check before it ships (the
boundary-change skill carries the drill). Give the layer a link code in the
root `layer-codes.json` — two or three lowercase letters or digits, starting
with a letter, never a code already listed (retired ones included) and never
another layer's id — because share links write layers by code and the code is
permanent; the generator refuses a layer without one, and its `--check` fails
on a code changed or removed against the base branch. Then one run:

```bash
python3 scripts/generate_metro_files.py
```

emits `LAYER_AREA_RANK`, `LAYER_CODES`, `EXPECT_LAYER_IDS` and `MIN_REGISTER_LAYER`, the
`sw.js` URL lists, the smoke test's `EXPECT_LAYERS`, the `sources.html` matrix
row and the instance `CLAUDE.md` layer count.

**Generated by a DIFFERENT generator — re-run in the same change.**
- `python3 scripts/build_history_page.py` — any instance whose worksheet carries `history_page` counts its layers in a MEASURED tile.
- `python3 scripts/build_county_status.py` — a new `registerCountyLayer` table in `il/index.html` changes `docs/COUNTY_STATUS.md`.
- `python3 scripts/build_privacy_page.py` — a layer that adds an external host or a server-side point query moves the measured table.
- `python3 scripts/build_dark_map_palette.py` — a new outline `color` gets its dark twin DERIVED into a GENERATED region; its `--check` fails otherwise.

**Hand-edited, because nothing generates them.**
- `LAYER_SIDEBAR_RANK` in the instance's `index.html` — grep for `var LAYER_SIDEBAR_RANK`; if the instance has none (`ny/`, `ca/` today) the sidebar renders in registration order and there is nothing to rank (§6).
- A row in the instance's `validate_sources.py` manifest.
- The guidebook, THREE edits: the `GUIDEBOOK:BEGIN coverage-map` JSON (the only one a gate diffs — the weekly `scripts/fleet_status.py`), the instance's row in `## Per-fork inventories` (pattern, source, roster/join, coverage function), and the concept-matrix cell (add the concept row if it is new fleet-wide) — plus any drop WITH its rationale; silence is the only wrong answer.
- An Appendix A row for an `il/` layer (the reference instance's classification, §1.6 step 5); a `wi/` or `ia/` layer has no appendix table and goes to the guidebook alone.
- A blast-radius row in the instance's section of `docs/REDISTRICTING_RUNBOOK.md` for any new boundary layer — add the section if the instance has none — and a row in `WATCH.md` (root for Illinois, `<tag>/WATCH.md` elsewhere) for anything date-bound (§6.6).

## 6. Sidebar position

Where an instance carries `LAYER_SIDEBAR_RANK`, position is that list and the
instance's `validate_index.py` asserts it matches the registered id set 1:1
(`scripts/validate_index.py` for Illinois); a `subOf` layer must be IN the
list (the check is set membership) and by convention sits right after its
parent, though it renders inside the parent whatever its rank. Within a
group: identity hierarchy → representation → service and taxing overlays →
amenity points, broad to specific within each family; toggled-on layers float
to the top regardless, so the rank governs the RESTING order. Illinois ranks
Political by DEMAND, most-searched first, by an operator decision recorded in
Part 4 with its evidence; another instance follows that only if its own
`LAYER_SIDEBAR_RANK` comment records a demand basis — otherwise the
governance order applies to Political too. Re-rank only from real Search
Console or GoatCounter data, never by feel.

## 7. Nesting

Set `subOf` only for genuine legal containment PLUS numbering — never mere
geometric overlap; cross-group nesting is impossible by design; never gate an
elected body behind a service toggle. Part 4 holds the evaluated-and-rejected
list (a municipality under a county, special districts under a county);
read it before proposing a nest that is on it.

## 8. Gates

`python3 scripts/generate_metro_files.py --check`; the instance's
`validate_index.py` (the `registerLayer(` floor, both rank lists, the
exactly-one-list rule for `<tag>/data/app`, a `sources.html` row per layer); its
`smoke_test.mjs` (exact layer count, coverage-hide, permalink stability, the
alias shim if an id was renamed — `il/index.html` carries
`CONSOLIDATED_LAYER_ALIASES`; another instance builds the shim first, §3.1);
`python3 scripts/build_history_page.py --check`,
`python3 scripts/build_county_status.py --check`,
`python3 scripts/build_privacy_page.py --check` and
`python3 scripts/build_dark_map_palette.py --check` for the second class
above; `python3 scripts/compose_app.py --check` if a fence was touched;
`python3 scripts/build_coverage_gaps.py --check` (with `--metro` and `--out`
for a non-Illinois instance) if a gap was written. The steward skill carries
the whole battery.

## 9. Nevers

- Never register a polygon for a body that elects at large, or a layer for an appointed or party office.
- Never a second dedicated layer for a class that has one; convert at the second county.
- Never rank by feel; never re-rank Political without recorded demand data.
- Never rename a layer id — ids live in shipped permalinks; change the label and add an alias.
- Never ship a layer with no guidebook row, and never a drop without its reason.
- Never leave a second generator un-run: a green worksheet `--check` says nothing about the history, status, privacy or palette gates.
