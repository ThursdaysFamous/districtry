# Source credits

People who found a source that closed a data gap in this app.

Most gaps here are not code problems. They are gaps because no publisher publishes the
data, or because the publisher blocks automated fetching — so finding a usable source is
often harder than wiring it up, and it is the contribution that actually moves coverage.
This file is where that work is credited.

**How a credit is earned.** Submit a source through
[the intake template](../.github/ISSUE_TEMPLATE/source-submission.yml) (the app's **Data
gaps** panel deep-links to it with the gap prefilled). If the source is verified and ships,
the PR that ships it adds a row below and names the submitter in its changelog entry. There
is no cash bounty — the credit is the reward.

**What counts as shipped.** The source has to survive the project's ordinary bar: a
publisher we can cite, data we re-verified ourselves, and a card that ends up saying
something true it could not say before. A source that turns out to be stale, unlicensed,
or already-known is recorded as checked in
[`docs/DATA_LAYER_GUIDEBOOK.md`](DATA_LAYER_GUIDEBOOK.md)'s gaps block — so the next person
does not spend time on it — but it does not earn a row here.

## Credits

| Gap closed | Source found | Credited to | Shipped |
|---|---|---|---|
| `jones-county-supervisor` (Iowa) | The county's own supervisor-district file, `BOS_2022`, sent on request | Jones County GIS Coordinator, through the County Auditor's office | 2026-10-07 |
| `ia-tama-supervisor-map` (Iowa) | The county's own 2025 supervisor-district and precinct maps, sent on request | Tama County Auditor | 2026-10-07 |

## Maintainers: adding a credit

1. Close the gap's entry in the guidebook's `GUIDEBOOK:BEGIN gaps` block (or downgrade
   `no-source` → `data-quality` if the source only partly closes it), then
   `python3 scripts/build_coverage_gaps.py`.
2. Add a row above: the gap id, a link to the source, the submitter as they asked to be
   credited, and the release or date it shipped.
3. Name them in the changelog entry too. A credit buried in one file is a weaker thank-you
   than a credit in the thing people read.

If a submitter asks not to be named, record the credit as _anonymous_ rather than dropping
the row — the gap still closed because someone did the work.
