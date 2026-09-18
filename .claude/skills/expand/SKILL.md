---
name: expand
description: The shared plumbing every districtry expansion rides — which file owns each fact (worksheet vs engine/ vs data/app), the roster triad's contract, the fetch-engine ladder, which route to try first for each datum, and what a change still owes after it merges. Use it at the START of any change that grows an instance when no narrower skill fits, and for the cross-cutting questions: "where does the Iowa auditor builder go", "add a layers[] row and regenerate everything that reads the worksheet", "the card helper needs an emptyNote, where does that edit go", "which route first for Kenosha's board roster", "Pierce is behind Akamai — Playwright or the Archive rung", "what do I still owe after shipping the precinct layer". It routes to county-n-plus-1, new-state-instance, new-layer, roster-pipeline, municipal-officials, boundary-change, gap-record and outbound-ask, and points at docs/EXPANSION_GUIDE.md Part 6 rather than restating it. Not for a red PR (steward) or a data question.
---

# The spine every expansion rides

`CLAUDE.md` carries the worksheet mechanism, the engine fences, the layer
contract, the scraper → builder → bot-PR pattern and every gate's story, and is
loaded on every turn. `docs/EXPANSION_GUIDE.md` §0 and Part 6 are the doctrine.
This carries the part an agent gets wrong at the START of an expansion task —
where each kind of edit actually goes, and what a change owes after it merges
— plus the deltas the guide does not carry, once, so the path skills can
point here instead of each restating it.

## 1. Route the task (§0.3)

- A new state → **new-state-instance**.
- A CITY instance growing into its STATE (NYC → New York) → in place, in the order `docs/EXPANSION_GUIDE.md` §0.2.1 gives: the statewide tier as one dark change, the city layers as the §3.0 city tier, go-live as its own change, then **county-n-plus-1** per county. The worked plan is `docs/NY_EXPANSION_PLAN.md`.
- One more county or roster inside an instance → **county-n-plus-1**; its roster mechanics → **roster-pipeline** for Illinois, or county-n-plus-1 §9 for Wisconsin and Iowa (one statewide workflow per concept, never a per-county triple); an Illinois county's villages → **municipal-officials**.
- A new concept or toggle → **new-layer**, gated by §1.6.
- A boundary that moved → **boundary-change**.
- A gap record to write, correct or retire → **gap-record**; an e-mail to a public office → **outbound-ask**.
- A PR to drive to green → **steward**.

The expansion invariant (§0.4): a county adds dispatch entries and roster
rows, never a layer; an at-large body adds roster rows ONLY — no dispatch
entry, no coverage function, no toggle.

A CITY tier inside a state instance (§3.0) is that instance's depth, and no
narrower skill owns it: one coverage gate per city, dissolved from the city's
own ward fabric and never a bbox; a concept that appears in a second city
becomes a dispatched concept exactly as a county concept does; the city's
publisher outranks the state's for what the city administers, with the state's
answer kept as the fallback so a failed city file degrades instead of
dead-ending; two surfaces always, the live service and the open-data extract,
with a build-time witness comparing them. §3.1 holds the dispatcher's
semantics — coverage is the OR of the entries, the query dispatches by
containment, a downed county's error propagates rather than reading as "no
result" — and the rule that every retired per-county id is appended to the
instance's alias shim, so shipped permalinks keep working.

## 2. Find the instance's files before writing anything (§0.1)

`<tag>/metro-worksheet.json`, `<tag>/scripts/` (builders, scrapers, the
instance's own `validate_index.py`, `smoke_test.mjs`, `validate_sources.py`),
`<tag>/data/app/` (runtime files), `<tag>/data/source/` (build inputs, excluded
from the deploy), `<tag>/WATCH.md`, `<tag>/CLAUDE.md`. The exception is
Illinois, which runs from the ROOT — `INSTANCES` in
`scripts/generate_metro_files.py` says so (`docs` is `.`): the root
`metro-worksheet.json` is Chicago's, root `scripts/` holds fleet tooling AND
Illinois's own builders and scrapers, and Illinois's `WATCH.md`, `CLAUDE.md`
and `README.md` are the root files; there is no `il/scripts/`, `il/WATCH.md`
or `il/CLAUDE.md`. A new state follows Wisconsin's shape. Never `sys.path`
into another instance's scripts — `scripts/validate_workflow_deps.py`
resolves a sibling import only inside the instance's own `scripts/` and
charges anything else against the workflow's `pip install` line. Shared
machinery is therefore COPIED into `<tag>/scripts/` or promoted to a root
fleet helper, never imported across trees; root `scripts/` is Illinois's
tree, not a shared library.

## 3. Any per-instance fact → the worksheet → regenerate

```bash
pip install -c scripts/requirements.txt jsonschema             # the generator exits 1 without it
python3 scripts/generate_metro_files.py                  # every instance
python3 scripts/generate_metro_files.py --instance wi    # one
python3 scripts/generate_metro_files.py --sync-fleet     # first, whenever metros.json changed
python3 scripts/generate_metro_files.py --check          # the CI gate
```

The generated regions are in `index.html`, `sw.js`, `sources.html`,
`validate_index.py`, `smoke_test.mjs`, `CLAUDE.md` and `README.md`. A layer is
a `layers[]` row with a `source` block — the generator refuses without one
whenever the worksheet sets `sources_page`, which also requires
`verified_date`; the schema (`schema/metro-worksheet.schema.json`) itself
requires only id, label, group and area rank. Set both keys and give every
layer a `source`.

## 4. An engine change → the block under `engine/` → recompose

```bash
python3 scripts/compose_app.py                  # splice engine/ into every registered instance
python3 scripts/compose_app.py --instance ia    # one
python3 scripts/compose_app.py --check          # the CI gate
```

It is a FLEET change and must be right for every instance. The
instance-neutral way to add behaviour is an optional field a layer opts into —
`emptyNote`, `coverage`, `subOf`, `pointOfInterest`'s coordinates — so a layer
declaring nothing is unchanged. `--extract-from` repopulates `engine/` FROM
one instance and is the adoption door, not the edit path. A NEW block is two
steps: write `engine/<index.html|sw.js|shared>/<name>.txt` by hand, then seed
the `ENGINE:BEGIN/END <name>` pair at the same relative slot in EVERY instance
file — compose only fills fences that exist, and `--check` cannot see a fence
an instance lacks, so a block fenced in one instance ships to one instance,
green. `ls engine/` is the block inventory (`docs/ENGINE_SYNC.md`'s list omits
`engine/shared/`, and the file is engine history, not procedure).

## 5. A new roster → the triad pattern (§6.3; roster-pipeline has the Illinois mechanics)

§6.3 is the contract — scraper, builder with a floor, workflow on a fixed
`bot/*` branch opening a PR. Only Illinois instantiates it per county; the
statewide instances run one workflow per concept. In Illinois reuse
`scripts/scraper_common.py` (`make_fail`, the UA constants, `fetch`) and
`scripts/aia_bundle.py` (the pinned intermediates); in any other instance
the instance CARRIES ITS OWN COPY inside `<tag>/scripts/` (§0.1). A retired
script gets a "Supersedes …" line in its successor's docstring AND is deleted
— `docs/OPTIMIZATION_PLAYBOOK.md` §8 records the one a merge resurrected.

## 6. Choose the fetch engine by the ladder, and record the rung per target

Plain requests (`scripts/ilga_scraper.py` is the template) → `--engine auto`,
requests then Playwright (`scripts/cpd_district_scraper.py`) → Playwright from
day one for a known bot block → the Internet Archive Save-Page-Now rung for a
total block (`scripts/kendall_county_board_scraper.py`, with its
`WAYBACK_MAX_AGE_DAYS` guard and standing-issue conversion) → REJECTED, with
the alternative documented. A captcha or a 202 is an access control, not an
obstacle. If the official site is unscrapeable, a maintained open aggregator
may supply STRUCTURED fields while the official site stays the card's link.
Keyed enrichments ship dark — a missing secret degrades to the unenriched
roster; app tokens are public, real API keys are repo secrets and never in
`index.html`.

## 7. For each datum, work §6.4's route column top-down — by path, never copied

Take the first route that honestly works, record the outcome, and never
invent what no route provides; contact comes from the roster's OWN source,
never backfilled from a weaker one; VERIFIED means you fetched it and saw
records (§2.6.1).

## 8. Freshness fires on a successor, never on age (§6.3)

A year-versioned id gets a manifest row in the instance's
`validate_sources.py`; the check fires on a newer edition or a 404, surfaces
as a tracking issue, never as an edit.

## 9. Gates: the steward battery, not §6.5's table

`.github/workflows/smoke-test.yml` is the source of truth and the steward
skill carries it in CI's order with the real invocations; §6.5's table omits
gates CI runs. Two worth naming for a fleet change:
`python3 scripts/validate_workflow_deps.py`, and
`python3 scripts/build_landing_page.py --check` — at GO-LIVE the front door
must list the instance; while an instance is dark it must NOT be in
`metros.json` (new-state-instance §4).

## 10. What a change still owes after it merges (§6.6)

- The weekly workflow(s) it added, on staggered cron slots — the live schedule is the instance `CLAUDE.md`'s generated metro-facts block — and DISPATCHED ONCE BY HAND the day it ships, its log read: `validate_workflow_deps.py` is a static import check, and a workflow that has never run is not a workflow yet (§3.5.1).
- A `validate_sources.py` manifest row per dataset endpoint, and per roster SOURCE whose block is measured — a `"blocked": …` row is how reachable-again becomes a WARN; the link gate only extracts and probes URLs.
- A `WATCH.md` row (root for Illinois, `<tag>/WATCH.md` elsewhere) for anything with a date, a filing window or a per-election refresh, with its last-run value: the calendar is the only thing that fires for data no gate can check.
- `docs/DATA_LAYER_GUIDEBOOK.md` rows — coverage map, inventory, matrix, gap records naming their counties.
- A blast-radius row in `docs/REDISTRICTING_RUNBOOK.md` for every new boundary layer; check that runbook's per-instance sections against the instance's `layers[]` before assuming it is current — it has lagged whole instances before.

## 11. Working style (§0.5)

Locate code by grep anchor, never by line number; keep measurement separate
from conclusion — "this host refuses this client" is what was measured, "this
agency publishes nothing" is a claim the measurement does not support.

## 12. Nevers this file adds

- Never put an instance's builder in another instance's tree, reach across with `sys.path`, or import root `scripts/` from a non-Illinois instance.
- Never fire freshness on age.
- Never call a workflow shipped before it has been dispatched once.
- Never ship a boundary layer without its runbook row and its WATCH row.
