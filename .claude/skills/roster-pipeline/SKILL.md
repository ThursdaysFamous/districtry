---
name: roster-pipeline
description: Write or clone the roster pipeline for a county whose source and board form are already settled — the districted scraper → builder → weekly-workflow triple, or the at-large rows in the shared commissioners pair — so the file, its guards, its tripwire, its workflow and its registrations match the fleet's conventions and pass every gate on the first dispatch. Use it for "ship Jasper's roster, the Richland shape", "write build_ford_county_board.py and its workflow", "clone the Wayne triple for Marion", "Pope's clerk e-mailed three names, carry them like Wabash", "what cron slot is free", "MIN_EMAILS for Bureau, measured 5 of 7", "SITES entry or RETURNS_ROSTERS?", "what does a new roster builder have to refuse on". Not for deciding the source or the board's form (county-n-plus-1), municipal officials (municipal-officials), a red bot PR (steward), or a Wisconsin or Iowa county — their boards are one statewide workflow per concept, never a per-county triple, and county-n-plus-1 §9 carries their shapes.
---

# A roster's pipeline

`CLAUDE.md` carries the scraper → builder → bot-PR pattern, `BOT_PR_TOKEN`
and why it exists, the `git diff --quiet -- il/data/app/` gate and the
retention gate; the steward skill carries what to do when a run goes red;
county-n-plus-1 carries how the source and the board's form were settled.
This carries the MECHANICS: the REFERENCE triples — Richland, Wayne, Clay,
a fixed name rather than "the newest three" — are line-for-line identical in
everything that is not a county fact, and an agent opening a blank scraper
file gets those lines wrong by guessing. A newer triple is not automatically
a reference: diff it against these before cloning it. What legitimately
varies per county is listed at the end so it is never mistaken for
convention.

## 1. Pick the shape; it decides which files exist

**Districted** → its own triple: `scripts/<county>_county_board_scraper.py`,
`scripts/build_<county>_county_board.py`,
`.github/workflows/update-<county>-county-board-roster.yml`, writing
`il/data/app/<county>-county-board-members.json`. Three builder name forms
coexist in `scripts/` (`build_<c>_county_board.py`,
`build_<c>_county_board_roster.py`, `build_<c>_board_roster.py`) and the
form is not date-keyed; new work uses the first, which the three reference
triples use. `ls scripts/build_*` before cloning — never infer the form from
a date or a suffix.

**At-large** → NO new files. A `SITES` entry with a `parse_<county>` function
in `scripts/il_county_commissioners_scraper.py` — or a `DOCUMENT_ROSTERS` row
(a document the clerk sent: `document`, `verified`, `expect`, `members`) or a
`RETURNS_ROSTERS` row (certified winners) — plus an `EXPECT_MEMBERS` row in
`scripts/build_county_commissioners.py`. The key is `norm_key()`'s: uppercase
letters only, "COUNTY" stripped (`STCLAIR`, `JODAVIESS`), the same key
`il-county-clerks.json` uses. A county sits in exactly ONE of the three
tables. If the county styles its chair a new way, widen `ALLOWED_ROLES` and
`CHAIR_ROLES` TOGETHER — widening one without the other is the hole.

## 2. Clone from the three reference triples

Richland is the two-source tripwire (composition read from the county's GIS
each run); Wayne is the composition on the roster page, with a per-district
SUBSET exception (`PAGE_SUBSET_DISTRICTS` in
`scripts/build_wayne_county_board.py`, reason in the docstring); Clay is two
pages, with roles joined across surfaces. Richland and Wayne are the emit
shape (§3); Clay deviates in small ways — an `-o` default that is a file
rather than stdout, no `sort_keys`, payload keys `membersUrl` / `boardUrl`
rather than `source` — so clone the emit lines from Richland. Then grep the
new files for the old county's name, slug and domain — the workflow's PR
title and body are a human-review surface.

## 3. The scraper

`from scraper_common import make_fail, UA_ROSTER_BOT` (`scripts/scraper_common.py`);
`fail = make_fail("<county>-board-scraper")`; a `HEADERS` dict with the bot UA.
Never change a shipped scraper's UA constant — each constant is the exact
bytes its importers were already sending. `argparse` with `-o/--output`; the
workflow always passes `-o /tmp/<county>_board_raw.json`. Emit
`json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)` plus a
newline, naming the source beside the records. Scope the parse to the county's
MAINTAINED block and `fail()` if its marker vanishes, rather than reading names
off the whole page (Richland's committees list people who do not sit on the
board). A card whose position line does not parse: Clay's scraper `fail()`s
so the diagnostic names the card; Richland's `continue`s past it and lets the
builder's exact count catch the shortfall. Pick one and say which in the
docstring. Where the page prints a datum twice, require the copies to agree.
Emit ONLY what the page publishes — no party, term, phone or e-mail invented
— and say in the docstring what it publishes and what it does not. If the
tripwire input lives on the same page or on the county's GIS, re-read it into
the payload every run.

If the page arrives without its names and fills them in from a feed, read the
feed: its address, parameters and any key the page gives every visitor are in the
page's HTML or scripts. Re-read those from the page each run rather than pinning
them, since a key can rotate. Read robots.txt for the feed's host too. A sign-in
or managed challenge stays shut. A linked scanned PDF is a source too: render it
and read it as an image before calling the data unpublished.

## 4. The builder

`sys.argv[1]` is the raw JSON, optional `sys.argv[2]` the out dir,
`DEFAULT_OUT_DIR` is `il/data/app`; `fail = make_fail("<county>-board-roster")`.
Import ONLY constants — `COMPOSITION`, `COUNTY_PRECINCTS`,
`SEATS_PER_DISTRICT` — from `scripts/build_<county>_boundaries.py`
(`scripts/build_richland_boundaries.py` is the shape). The rule behind that:
`scripts/validate_workflow_deps.py` walks the workflow's ENTRY POINT whole,
function-local imports included, and reads only module scope in the modules
it imports — so the boundaries module keeps its shapely import inside
`main()` (the De Witt seam) and the builder imports nothing but constants
from it; a `from shapely` anywhere in the builder, even inside a function,
fails the merge gate and the weekly job dies on import. Compare names with
`norm` from `scripts/vtd_board_districts.py`.

**Run the drift check FIRST, before the roster.** Re-read the composition
against `COMPOSITION`: district set equal; per-district precinct set equal,
or a subset for districts in the subset exception. A drift `fail()` should
name the re-derivation script (Richland's do; one of Wayne's does not — fix
the message when you clone it). Then the roster guards — EXACT, never
floored: district count `== EXPECT_DISTRICTS`; total `== EXPECT_MEMBERS`; per
district `== SEATS_PER_DISTRICT`; every district key present in
`COMPOSITION`; a duplicate in a one-member district fails; a nameless member
fails. This departs from `docs/EXPANSION_GUIDE.md` §6.3's under-tolerance on
purpose: with `roster-health.yml` a vacancy is a red run with an owner, not a
wedged file. Contact fields take a floor BELOW the measured count with the
measurement in the comment — read `MIN_EMAILS` and its comment in the
Richland builder for the shape; Clay's scraper instead fails any card without
a phone — and phones get a shape check. At most one Chairman and one Vice
Chairman; when two county surfaces name the chair they must agree or the
build fails; a role joined by surname must be UNIQUE and the join is PRINTED
every run, shipping the roster page's spelling. Members sorted by name;
`json.dump(roster, indent=2, ensure_ascii=False, sort_keys=True)` plus newline.
The final prints say what was written, with counts and the chair, and then
state that the tripwire matched AND what it cannot see — Clay's print is the
model; a green tick that covered nothing is the alternative.

**Composition only in a linked PDF → no drift check is possible.** Assert the
weakest real substitute the page does publish (Cass: its seat counts, which
its population test depends on and which a reapportionment almost always
moves) and state in the builder's header AND the workflow's exactly what that
cannot catch (a redraw that leaves every district the same size).

## 5. The two output schemas

**Districted:** `{ "<district id>": { "members": [ {name, role?, email?, phone?} ], "sourceUrl": <roster page> } }`,
plus an optional top-level `board` entry for a county-level switchboard or
office (the Calhoun rule — Clark, Adams, Knox, White, Coles carry one), which
counts toward `min_keys`. The district is the KEY, never a member field, and
it must equal the district id in `<county>-county-board-districts.json`
exactly — the card joins the two files by that key. `seats` per entry only
where the builder tolerates a short list; `vacancies` only where the county
prints the word.

**At-large** (`il/data/app/il-county-commissioners.json`):
`{ "<KEY>": { county, structure, members[], seats?, office?, and EXACTLY ONE of sourceUrl | sourceDocument } }`.
`verified` (an ISO date) rides `sourceDocument` on the DOCUMENT tier only;
the returns tier's currency is each member's `districtSource`, and it adds
`seat`, `party` and `since` per member. `seats` may not be smaller than the
roster and may not EQUAL it — drop the field rather than ship a shortfall of
nothing.

There is NO `verifiedDate` key anywhere in the repo; `verified_date` is the
worksheet's UI key and unrelated. Two mappers render these, and they differ:
county-board entries go through `boardMemberPerson` in `il/index.html` (read
it for the field set; entries may append `since` / `districtSource` around
it), while the at-large County card has its own inline mapper in the
"At-large county board" block, which renders name, role-or-`seat`, phone,
email, `since` and `districtSource` and does NOT render `party`. Before
claiming a field ships, find it in the mapper the card actually uses. ADDING
A FIELD TO THE SCRAPER IS NOT ADDING IT TO THE APP.

## 6. The workflow

Five load-bearing lines, identical across the three
(`.github/workflows/update-richland-county-board-roster.yml` is the template):

- a header explaining BOTH jobs, roster and tripwire, and WHAT THE CHECK CANNOT SEE;
- `on: schedule` on the hour in a free slot — grep every `.github/workflows/*.yml` for `cron:`, pick an empty hour, and keep it before `roster-health.yml`'s cron (read the hour from that file; it runs after the last roster slot) — plus `workflow_dispatch: {}`;
- `permissions: contents: write / pull-requests: write`; checkout with `token: ${{ secrets.BOT_PR_TOKEN || github.token }}` (`CLAUDE.md` says why); `pip install -c scripts/requirements.txt requests` — only what the entry point and its module-scope closure need;
- scrape to `/tmp`, build, `python3 scripts/validate_index.py il/index.html`; a diff step on the whole `il/data/app/` directory writing `changed` to `$GITHUB_OUTPUT`;
- a PR step gated on `changed == 'true'`: a FIXED branch `bot/<county>-county-board-roster-update` (an unmerged PR is refreshed in place by the force-push rather than duplicated), CUT FROM MAIN'S CURRENT TIP rather than from the checkout the run started with — `git fetch --depth=1 origin main` then `git checkout -B "$branch" FETCH_HEAD`, copying the block every other roster workflow carries. `actions/checkout` is shallow and these runs take tens of minutes; if main gains a `.github/workflows/` change meanwhile, a branch cut from the stale checkout differs from main THERE too, and GitHub refuses the push as a workflow update for a token without `workflow` scope (measured 2026-09-02). The rebuilt files are carried across the re-cut, and a run where main touched those same data files errors instead of pushing. Then `git add` of the ONE data file (plus `il/history.html` if a history tile counts it), `git push -u origin "$branch" --force`, `gh pr list --head "$branch" --state open` guarding `gh pr create`, `GH_TOKEN` the same expression. The body names both scripts, says the PR changes data about real officeholders, and states what a tripwire failure would mean.

## 7. Register, regenerate, dispatch

One entry in `metro-worksheet.json`'s `data_files.rosters[]` —
`{"file": "<county>-county-board-members.json", "min_keys": N, "note": …}`;
`data_files.geometry[]` is the cache-first sibling a roster must NOT land in.
It generates BOTH `ROSTER_FILES` in `validate_index.py` and the network-first
`ROSTER_URLS` list in `il/sw.js` (`scripts/generate_metro_files.py`; a
`<tag>/data/app` file in zero or two lists fails). A `workflows[]` entry
`{"file", "purpose", "schedule"}` feeds the metro facts. The file is not
registered until `il/index.html` fetches it by that literal `data/app/<file>`
path from the county's `county-board` dispatch entry (county-n-plus-1's
step) — `validate_index.py` fails "index.html does not reference
data/app/<file>" otherwise. Then:

```bash
python3 scripts/generate_metro_files.py
python3 scripts/validate_workflow_deps.py
python3 scripts/check_roster_retention.py --base origin/main   # a NEW file is ignored; a reshaped one is not
```

and the steward battery. A roster's page gets NO row in
`scripts/validate_sources.py` today (grep it for the county before assuming;
that manifest is dataset endpoints). The guide's DeKalb rule in §3.5.1 asked
for the members page there because the monthly check could not otherwise see
it; since 2026-08-27 `scripts/validate_card_links.py` extracts every
`sourceUrl` and probes it monthly, so what a validate_sources row still adds
is the `blocked` inversion for a permanent, CI-measured block.
`roster-health.yml` discovers the workflow by filename (everything not in
`NOT_A_REFRESH`, `scripts/check_roster_workflow_health.py`) and reports it
NEW until one interval has passed.

**Dispatch the workflow the day it ships and read the log.** A green
`validate_index.py` says nothing about whether the job runs, and the sandbox
is not CI's address. **IT CANNOT BE DISPATCHED BEFORE THE MERGE, and that is
GitHub's rule rather than a permission problem** (measured 2026-09-27 on
`ny-update-tompkins-legislature-roster.yml`): the Actions workflow registry is
built from the DEFAULT branch, so a dispatch of a file that exists only on a
feature branch answers **404 Not Found** — the same body a missing repository
gives, which is what makes it easy to misread as the PAT. `actions_list`
`list_workflows` confirms it: every row's `html_url` names `blob/main/`. So the
dispatch is the first thing to do AFTER the merge, not part of the PR. A fetch failure on the first dispatch is a SAMPLE, not a
verdict — runner addresses are scored individually, and §3.5.1's DeKalb
bullets say how many draws before you write anything down.

## 8. NOT RE-READ and carry-forward — the at-large pair only

The commissioners scraper prints a NOT RE-READ line for every
`DOCUMENT_ROSTERS` county naming the document and its age; the builder prints
one for a county the scraper could not read this run and carries its shipped
members forward, refusing the whole write when `MAX_CARRIED_FRACTION` of
counties were carried — a run that carries most of the file is a systemic
block wearing a green tick. A zero parse on a 200 is treated as UNREAD, never
as an empty board. A single-county districted builder has NO carry-forward:
an unreadable page is a red run by design, and `roster-health.yml` is what
gives that red an owner.

## 9. Retention exceptions

`ACCEPTED_DROPS` in `scripts/check_roster_retention.py` is keyed on the
instance-relative label — `"<tag>/data/app/<file>:<field>"`,
`"…:<group>:<field>"` for one source in a shared file, or `"…:<group>"` for a
county that stops publishing entirely (the Grundy shape) — with a dated
reason; a bare filename never matches and the gate stays red. The thresholds
(`MIN_PRESENT`, `MIN_ABSOLUTE_DROP`, `RECORD_COLLAPSE_RATIO`) live beside it.
Copy the shape of the entry that exists — it records that the builder now
REFUSES the field, not merely that its absence is tolerated.

## 10. What legitimately varies — and so never belongs here

URLs, markers and regexes; which contact fields ship; every `EXPECT_*` and
`MIN_*` number; the tripwire input (GIS inventory, page composition, a seat
count, none) and its stated blind spot; subset exceptions; role-join rules;
fetch posture (plain `requests.get`, `scraper_common.fetch`, or a pinned
intermediate); the UA constant; the cron slot; the `-o` default. Wisconsin
and Iowa do NOT use the per-county triple. Wisconsin: a `COUNTIES` entry in
`wi/scripts/wi_county_board_scraper.py`, a robots.txt check
(`wi/scripts/validate_robots.py`), and one
`.github/workflows/update-wi-county-board-roster.yml` re-scraping every
reachable county into one file; its builder REFUSES to drop a county it
shipped last week unless a human passes `--allow-drop <County>` by hand — the
workflow passes nothing. Iowa: one state aggregate, every file and workflow
`ia-` prefixed, the board switchboard hoisted to `boardPhone`, under
`docs/IA_EXPANSION_PLAN.md`. Read the instance's `CLAUDE.md` first.

## 11. Nevers

- Never floor a count the source states exactly; never lower a floor to get a build to write.
- Never derive a floor from another unit's document — count the field on the page in front of you and put the measured figure in the comment; a guessed floor failed a correct county and reads exactly like the publisher having broken something.
- Never invent a field the page does not publish; never add a field the card does not render and call it shipped.
- Never import shapely, pypdf or requests anywhere in a script a workflow runs directly — the entry point is walked whole; a module it imports keeps such imports function-local.
- Never carry a districted county forward; never treat a zero parse as an empty board.
- Never a per-run branch name; never `git add` the whole directory.
- Never change a shipped scraper's UA constant in a shared module.
- Never call a workflow shipped before it has been dispatched and its log read, and never record a block from one red dispatch.
