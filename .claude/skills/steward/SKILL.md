---
name: steward
description: How to drive a districtry pull request to green — the full local gate battery with its real invocations, in CI's order, and how to read a red or check-less bot roster PR as the data event it usually is. Use it whenever a task names a PR or a CI failure — "the smoke test is red on my branch", "drive #412 to green", "bot PR failed Roster fields still published", "coverage gaps says 60884 vs N bytes", "landing_test fails on //", "the bot PRs show zero checks", "compose_app --check is red after my engine edit", "which gates do I run before pushing" — and before any push to this repo. Not for the first red run of a NEW county's workflow (county-n-plus-1), a source or board-form decision (roster-pipeline), the gap text itself (gap-record), or a question about the data.
---

# Stewarding a districtry PR

This file exists for one job: an agent reacting to CI or review activity on a
districtry pull request. It carries only what the default PR-driving rules and
`CLAUDE.md` do **not** already say. Everything about architecture, the ENGINE
fences, the honesty rules and the layer contract lives in `CLAUDE.md`
(Illinois's, at the repo root) and `ca/CLAUDE.md`, `ny/CLAUDE.md`,
`wi/CLAUDE.md`, `ia/CLAUDE.md`, `mi/CLAUDE.md`, is loaded on every turn, and is deliberately
**not** restated here — two documents stating one convention is how
`ENGINE_SYNC.md` drifted from the fences it described.

## 1. Reproduce CI locally — the whole battery, in CI's own order

The generic advice ("run the repo's lint, format, typecheck and unit tests")
does not apply: this repo has none of those. It has the gates in
`.github/workflows/smoke-test.yml` — Python drift gates, then one static and
one browser run per instance, then the root pages — and **that file is the
source of truth**: if this list and that file disagree, that file wins and
this one is stale. The generating rule is one `validate_index.py` line and
one `smoke_test.mjs` line per top-level directory carrying an `index.html`
and a `<tag>/data/app/`, and one `build_coverage_gaps.py` line per instance
with a key in the guidebook's gaps block.

Two of these are easy to get wrong, and both fail in a way that misleads:

- **Illinois' smoke test lives at the repo root**, `scripts/smoke_test.mjs`,
  not `il/scripts/`. Every other instance has its own under `<tag>/scripts/`.
  Guessing the symmetric path gives `MODULE_NOT_FOUND`, which reads like a
  missing dependency rather than a wrong path.
- **`build_coverage_gaps.py`'s `--metro` and `--out` travel together** —
  either alone fails. `--metro` only chooses which key to emit; without
  `--out` it writes to, or compares against, Illinois' shipped file and fails
  with a byte-count mismatch against that ~60 KB file that looks like real
  drift in the instance you named.

```bash
pip install -c scripts/requirements.txt jsonschema

# --- static gates (stdlib unless noted; fail fast, run these first)
python3 scripts/generate_metro_files.py --check          # GENERATED regions vs worksheets
python3 scripts/build_coverage_gaps.py --check
python3 scripts/build_coverage_gaps.py --check --metro wisconsin --out wi/data/app/coverage-gaps.json
python3 scripts/build_coverage_gaps.py --check --metro iowa      --out ia/data/app/coverage-gaps.json
python3 scripts/build_coverage_gaps.py --check --metro michigan  --out mi/data/app/coverage-gaps.json
python3 scripts/build_coverage_gaps.py --check --metro nyc       --out ny/data/app/coverage-gaps.json
python3 scripts/build_coverage_gaps.py --check --metro sf        --out ca/data/app/coverage-gaps.json
python3 wi/scripts/build_wi_county_board_directory.py --check
python3 wi/scripts/build_wi_county_outlines.py --check
python3 scripts/build_brand_tokens.py --check
python3 scripts/validate_contrast.py                     # text vs ground, both tiers
python3 scripts/compose_app.py --check                   # engine/ vs every instance's fences
python3 scripts/check_engine_parity.py --fleet            # fences agree across instances; names partial blocks
python3 scripts/build_county_status.py --check
python3 scripts/backfill_board_seats.py --check
python3 scripts/build_county_board_offices.py --check  # ISBE addresses still agree with the counties' own
python3 scripts/build_dark_map_palette.py --check
python3 scripts/build_landing_page.py --check
python3 scripts/build_coverage_map.py --check            # every instance's outline path resolves
python3 scripts/build_privacy_page.py --check
python3 scripts/build_history_page.py --check
python3 scripts/build_manifests.py --check
python3 scripts/build_county_pages.py --check            # the 164 per-county board pages (il 75, wi 72, ia 17) vs their rosters, the 60 workflows that rewrite one, and any county roster no adapter reads
python3 scripts/build_llms_txt.py --check                 # /llms.txt vs the fleet it describes; its page set comes from sitemap.xml, so it cannot name a page that is not there
python3 scripts/build_sitemap.py --check                 # sitemap.xml PARSES as XML, and every page's lastmod matches its last commit (regenerate with no flag; a page you have edited but not committed dates today, so the order you run it in no longer matters). A parse FAIL means no crawler can read any of it — that is what a double hyphen in its header comment did on 2026-09-12.
python3 scripts/validate_favicon.py
python3 scripts/validate_shell_continuations.py
python3 scripts/validate_workflow_deps.py
python3 scripts/undeliverable.py                         # the shipped e-mail domains still resolve MX; the recorded dead ones are still dead
python3 scripts/validate_skills.py                       # every skill's pointers resolve
python3 scripts/validate_arcgis_format.py                # no app asks ArcGIS for f=geojson
node scripts/esri_rings_test.mjs                          # ring nesting, on fixtures
node scripts/build_og_image.mjs --check                    # every surface's social card is the one the renderer wrote, labelled with its metros.json tag (provenance, not pixels)
python3 scripts/validate_instance_registration.py         # every instance named in every table
python3 scripts/validate_instance_assets.py               # every same-origin asset a page names exists
python3 scripts/build_metro_outline.py --check           # IL ring + anchor registry
python3 wi/scripts/build_metro_outline.py --check
python3 ia/scripts/build_metro_outline.py --check
python3 mi/scripts/build_metro_outline.py --check
python3 scripts/build_press_list.py --check                # PRESS_LIST.md vs press-list.json
python3 scripts/validate_doc_counts.py                    # "N layers" in prose vs the worksheets
python3 scripts/validate_doc_counts.py --selftest         # pattern C reads the one real "N for <instance>" count and not the four sentences sharing its shape
python3 scripts/validate_serp_lengths.py                  # every page's title and description fit a search result
python3 scripts/robots_policy.py --selftest                # the one robots.txt reader against three saved files AND this site's own (its Content-Signal must parse: search=yes, ai-input=yes, ai-train=no, use=reference), plus the per-host Crawl-delay pacer: one queue per delay-stating site, `www.` folded, others parallel
python3 scripts/probe_user_agents.py --selftest           # read_robots() over stub responses: the robots-read path --probe depends on
python3 scripts/probe_user_agents.py --check              # user-agent measurements vs the tree; retired brands; unmeasured browser-string files; the figures CLAUDE.md, the guidebook and scraper_common.py quote
python3 wi/scripts/build_wi_circuit_court_roster.py --selftest      # the circuit-court name join: three recoveries, and the collisions it must refuse
python3 scripts/isbe_precinct_fabric.py --selftest         # the five Jasper-test reconciliation causes
python3 ia/scripts/ia_county_minutes_chair_scraper.py --selftest   # the four refusals that stand between a chair card and a wrong name
python3 ia/scripts/build_ia_county_chair.py --selftest              # the carry-forward rules: only `unreachable`, never a refusal, never past 60 days or a January
python3 ia/scripts/build_ia_county_officers.py --selftest           # display_name strips a salutation and keeps a Jr./Sr. suffix and a published credential; and the party name-join, which ships no party when no ISAC row matches the officer or when two do
python3 scripts/build_parcel_fabric_districts.py --selftest        # the geometry repair's three refusals and its drop count
python3 scripts/scraper_common.py --selftest                # the nine AFR builders' what-moved line, both ways: silent on a stamp-only week, names the record on a real one
python3 scripts/check_roster_retention.py --base origin/main
python3 scripts/check_cache_version.py --base origin/main       # cache-first data vs CACHE_NAME

# --- per-instance static gate (every instance, run from the repo ROOT)
python3 scripts/validate_index.py    il/index.html
python3 ca/scripts/validate_index.py ca/index.html
python3 ny/scripts/validate_index.py ny/index.html
python3 wi/scripts/validate_index.py wi/index.html
python3 ia/scripts/validate_index.py ia/index.html
python3 mi/scripts/validate_index.py mi/index.html

# --- browser gates: ONE server at the repo root, every instance
python3 -m http.server 8000 &
BASE_URL=http://localhost:8000/il/ node scripts/smoke_test.mjs
BASE_URL=http://localhost:8000/ca/ node ca/scripts/smoke_test.mjs
BASE_URL=http://localhost:8000/ny/ node ny/scripts/smoke_test.mjs
BASE_URL=http://localhost:8000/wi/ node wi/scripts/smoke_test.mjs
BASE_URL=http://localhost:8000/ia/ node ia/scripts/smoke_test.mjs
BASE_URL=http://localhost:8000/mi/ node mi/scripts/smoke_test.mjs
BASE_URL=http://localhost:8000      node scripts/landing_test.mjs
BASE_URL=http://localhost:8000      node scripts/page_consistency_test.mjs
BASE_URL=http://localhost:8000      node scripts/probe_point_transmission.mjs --check
BASE_URL=http://localhost:8000      node scripts/probe_contrast_pairs.mjs
```

`scripts/landing_test.mjs` defaults to port 8131, so `BASE_URL` is mandatory
for it, and it concatenates `BASE + "/"` without stripping — a trailing slash
fails every bare-visit assertion with `http://localhost:8000//`;
`scripts/page_consistency_test.mjs` and `scripts/probe_contrast_pairs.mjs`
strip one. Do not `pkill -f` the server
by its command line from a shell whose own command line contains it.

`scripts/build_county_pages.py` red comes in four shapes and each names its
own fix. A STALE page means a roster changed and the pages were not
regenerated — run it with no flag. A roster name that "does not appear on the
page it generated" means the template stopped rendering something, not that
the roster is wrong. A workflow that "never runs scripts/build_county_pages.py"
needs the regenerate step beside its `git add`, which is why bot roster PRs
carry it. And `NAMES_NOBODY` records the one county whose roster names nobody;
if it fails as stale, that county's roster has started naming people and the
entry should go so the page generates.

`scripts/page_consistency_test.mjs` red on a `target … is 24px or clear of its
neighbours` line means a control is under WCAG 2.5.8's 24px floor AND close
enough to a neighbour to be mis-tapped; the message gives its size, its parent
and the neighbour's distance. The fix is nearly always the container's spacing
rather than the control (a wrapped link row wants a bigger row gap or
line-height), and a control floating over the map wants `min-height: 24px`. If
one of 2.5.8's own exceptions genuinely covers it, record it in
`TARGET_EXCEPTIONS` naming which exception and why — an entry there fails once
nothing matches it. Red on `carries a skip link` or `carries a <main>` means a
new page shipped without the keyboard entry every other page has.

`scripts/probe_contrast_pairs.mjs` measures every text node on every sitemap
page in both themes and asserts one thing: a pair below its WCAG floor is one
`scripts/validate_contrast.py` already measures and already calls short. Red
here is not "the palette got worse" — it is "a colour pair is painted that the
static table has no row for", which is a real class, since that table is
STATED and a pair with no row reads as covered. The message names the page,
the selector and the two RGB values; write the row in `PAIRS`, run
`python3 scripts/validate_contrast.py` to get its measured ratio, then either
fix the colour or record it in `ACCEPTED_SHORTFALLS`. The join is on painted
colours rather than token names, because that is the only vocabulary both
sides share.

`scripts/probe_point_transmission.mjs` is the one browser gate that is not a
page test: it measures which layers send the reader's selected point to a
server, which neither a regex nor a structural read can see. A registration
factory serves as many layers as it is CALLED, `registerCountyLayer` closes
over its entries, and — the one that cost a wrong published figure — a layer
that merely CARRIES an `.atPoint` hook may never fire it, since the hook is
invoked only inside `queryFeatureAt` and the nearest-point factory calls its
loader directly. So the probe replaces every hook with a recorder and counts
the ones that FIRE, at more than one point because coverage-gated layers are
not queried outside their coverage. Red here
means an app changed what it transmits — re-run it WITHOUT `--check`, then
`python3 scripts/build_privacy_page.py`, and read the diff to
`point-transmission.json` as the privacy claim it is. `build_privacy_page.py`
fails separately, and earlier, when an app's `.atPoint` sites or
`LAYER_AREA_RANK` have moved since the probe last ran; that failure names the
same two commands.

Not in CI, but run before shipping a change that touches a source or a card
link, because the monthly job will otherwise find it for you (both need
`pip install -c scripts/requirements.txt requests`):
`python3 scripts/validate_sources.py` (each instance has its own under
`<tag>/scripts/`) and `python3 scripts/validate_card_links.py`.

## 2. Reading a bot roster PR — four surfaces, and the worst one is quiet

The `update-*.yml` workflows — all but a handful of `.github/workflows/` —
open `bot/*` PRs, so they are the majority of PRs this repo sees, and the
generic "fix and push" posture points the wrong way on them. The cause is
nearly always **a publisher changing what it publishes**, not a defect in the
diff. Where the red is tells you what it is:

- **A red bot PR** is `smoke-test.yml` on the bot branch. `check_roster_retention.py` red = a field stopped being published: read the failure (it names the file, the field and the per-source coverage), look at the publisher's page before touching anything, and either record a legitimate drop in `ACCEPTED_DROPS` with a reason and a date or fix the scraper. A generated-page `--check` red (`build_history_page.py`, `build_county_status.py`) on a bot PR = the WORKFLOW file lacks the regenerate + `git add` step for a file its tiles count; fix `.github/workflows/<job>.yml`, not the branch, or it is red again next week (`update-county-commissioners-roster.yml` regenerates neither, and `build_county_status.py` reads that file's keys).
- **`check_cache_version.py` red** = the change rewrote a file the instance's `sw.js` serves CACHE-FIRST (its `GEOMETRY_URLS` list — `metro-outline.json` above all, which every county join rewrites) without bumping that instance's `CACHE_NAME`. The fix is the bump, in this same change, and any different name will do — it is not an increment. Do NOT satisfy it by moving the file to the network-first list: a returning visitor otherwise keeps the old geometry indefinitely and sees new officeholders drawn against a stale map, which is the failure the gate exists for and which no other gate can see.
- **A red scheduled RUN** in the Actions tab, with no PR at all, is a scraper failing or a builder REFUSING to write — its count guard or floor tripped before the PR step existed. That refusal is the builder working. Diagnose the source; do not lower the floor. `roster-health.yml` is what gives that red an owner.
- **The monthly source issue** is never red: `validate-sources.yml` keeps its job green and opens one tracking issue. A host recorded as `blocked` reported REACHABLE is the deliberate inversion — becoming reachable is the actionable state, and the fix is to reconsider the block, not to silence it.
- **A bot PR with NO checks is worse than a red one**: the PAT that makes bot PRs run CI has expired, and the retention gate never ran. Never merge on green-by-absence; check `BOT_PR_TOKEN` first (`CLAUDE.md`, the `BOT_PR_TOKEN` paragraph).

## 3. Nevers specific to this repo

- **Never loosen a floor, a count guard, a retention threshold or a population deviation ceiling to get a check green.** Those numbers are the honesty mechanism, not test scaffolding. Raising one is a decision with a named reason and a source that confirms it — `CLAUDE.md`'s Wayne and Clay paragraphs are the two precedents, each for one county on the clerk's own written confirmation, with the measured value recorded rather than smoothed.
- GENERATED regions and ENGINE fences, roster data and `main`, a sandbox `L is not defined`: `CLAUDE.md` carries all three rules; the check that fails on a hand-edited region is telling you the generate step was skipped.

## 4. Judgment

A gate that fails is usually right. Before changing code to satisfy one, state
what the gate is actually asserting and why the current tree violates it — the
most common correct fix in this repo is to run a generator, not to edit an
artifact. **A HAND-BUILT HARNESS THAT FAILS IS USUALLY WRONG**, and
the two are opposite reflexes: a gate has been through review and many runs, a
throwaway verification script has been through neither. Three ad-hoc harnesses
in one session each returned a confident negative about correct code — a wrong
`repo_root`, an Esri-shaped stub where the loader wanted `f=geojson`, and a
GEOID typed from memory. Before believing a harness's no, make it say yes about
a case already known true, and read the two side by side. When regenerating: `build_brand_tokens.py` before `compose_app.py`
(both scripts' docstrings agree; `--check` is order-independent);
`generate_metro_files.py` on either side of those (the two docstrings
disagree on its place and `compose_app.py` says they cannot contend for a
line); `build_coverage_gaps.py` before `build_county_status.py` and
`build_history_page.py`, which read what it writes.
