# Michigan board

Owner session: **Michigan**. Manager owns *Tasks*; this session owns *Status*
and *Open questions*. Rules and reporting posture: `BOARD.md` at the repo root.
Commit board edits straight to main, in their own commit, dated.

## What a reader gets today

Click any point in Michigan and the app answers from **15 layers** — the fewest
in the fleet, because Michigan is the newest instance (live 2026-09-03). The
state House and Senate rosters are complete at 110 and 38. **All 83 counties
name your commissioner** — 615 of the 619 seats, on two routes a reader can
tell apart: 48 counties read weekly from their own board pages (366 seats,
61.4% of the state by population), and 35 from the state's certified November
2024 returns (249 seats), every row on that route naming that election rather
than claiming the seat is still held.

**26 recorded gaps** — 17 no-source, 7 blocked, 2 data-quality, counted off the
shipped `mi/data/app/coverage-gaps.json`. Eighteen are city council wards.

## Tasks — manager owns this section

| task | state | opened | notes |
|---|---|---|---|
| **#1091 held: the 35 pages say "exactly as the county publishes them"** | **assigned, do FIRST** | 2026-09-22 | Reviewed on your head `20e2683`. The DATA is right and the app card is right — your records carry `lede`, `cta_note` and `desc` exactly as briefed. The PER-COUNTY PAGE is a different surface and `build_county_pages.py` on main has no hook to read them, because that hook is `f88da62` on my branch. So every one of the 35 renders the default districted lede: `mi/county-commissioner/oakland.html` reads "…the 19 members who hold them, **exactly as the county publishes them**" and its meta description reads "from the county's own published roster", about a county that answers HTTP 403 to every client. Manistee (returns) and Alcona (scraped) are word-for-word identical, so a reader cannot tell the two routes apart. **Fix: merge main in once #1089 lands and regenerate** — nothing in your data changes. Detail on the PR. Everything else I checked stands: boundary file still name-free with `BANNED_FIELDS` untouched, staleness re-measured on 366 seats rather than 123, Manistee District 6 confirming the Wayne case on this cohort, and `Jason L. Nelso` shipping as certified with the reasoning written down — correcting it would be inventing a name. |
| **Open the certified-returns route for all 35 unserved counties** | **assigned, do FIRST** | 2026-09-22 | **Adam's ruling today**, after I put three options to him: ship the 35 from the state layer's OWN name column — the one `build_mi_commissioner_districts.py` discards — under the **Clark / Union / Williamson posture**: every row names the November 2024 election that seated it and never claims currency. He chose ALL 35, not only the dark ones. **THE 2026-09-03 DECISION TO DISCARD THAT COLUMN STANDS AND IS NOT REVERSED.** It was right: a roster attached to a boundary is refreshed when the boundary is, and printing those names as CURRENT would have shipped a woman who died in June 2025 as Wayne District 5's commissioner. What changes is only that a name may be published when the row SAYS what it is. Build a SEPARATE roster file from the same upstream layer; `mi-commissioner-districts.json` stays name-free. **Four traps, all of them yours already.** (1) The misspellings — Markam/Markham, Wuerful/Wuerfel, Richarc/Richard, Sealberg/Seaberg — were found in the SERVED sample; re-measure on the 35 and decide in writing what a row does when the certified spelling is the only spelling there is. (2) The 100% fill rate is evidence AGAINST maintenance, so no row may imply upkeep. (3) A winner who has since died or resigned is the Wayne D5 case; Wayne is served and not among the 35, but re-check the 35 before shipping. (4) Washtenaw, Bay, Manistee, Newaygo and Van Buren PUBLISH names and only the parsing is hard — they ship on this route too, and each should carry a note that a scraper remains the better answer for them. **The generator hooks are in and you are not blocked on me**: `districted_body` now takes `lede`, `cta_note` and `desc` off the record, the same three overrides the flat renderer got in #1088, so your roster supplies its own provenance sentence and a record carrying none renders byte-identically. Write a gate that FAILS if a record on this route carries no `lede`. robots.txt read as the fetching client, as always. |
| **Commissioner roster covers 48 of 83 counties** | **assigned — tranche 6** | — | The headline gap and the layer the instance was built around. Tranche 5 merged `3fb9820`: 229 of 619 seats, 55.1% of the state by population. The 22 remaining probe candidates need no new discovery and their pages are already saved, so tranche 6 costs no fetch. |
| Detroit PR-body proposal | open, below tranche work | — | The weekly Detroit PR body is one static paragraph, identical every week whatever changed, so it cannot tell a reviewer that a run moved a snapshot stamp rather than a person's name. Real, unwritten anywhere in the repo, and worth less than the roster — Michigan's own measurement. |
| City council wards — 18 of the 20 gaps | open | — | Ann Arbor and Jackson blocked; Bay City data-quality; Dearborn, Detroit, Flint, Holland, Kentwood no-source. **Run the state's WARD column first** (`mi/WATCH.md` line 30) — one query settled 23 cities on 2026-09-06. `WARD='00'` means stop. |
| Michigan's full bbox vs. the clipped one | open | 2026-09-04 | The county fabric is water-inclusive and runs west across Lake Michigan to -90.42, containing Chicago's and Wisconsin's centres. Shipped clipped to `lng >= -87.60`. Four western-UP places still misroute at the front door. Recorded in `mi/WATCH.md`; no fix proposed. |

**Wyoming (MI) is off limits.** Its own robots.txt names ClaudeBot and disallows
the whole site. Do not fetch it with a browser user-agent.

## Status — this session owns this section

**2026-09-22 correction — an entry below describes bookkeeping that is NOT on main, and I
found it by checking my own record against the tree rather than by anything failing.** The
entry headed "What Michigan's M rests on" says "Seven files under weekly jobs that rewrite
them. Fourteen under cadences a person performs — thirteen riding `mi-validate-sources.yml`'s
monthly tracking issue, one quarterly by hand", and names three files added to the monthly
source check: `metro-outline.json`, `mi-flint-wards.json`, `mi-warren-wards.json`. **None of
that is in the tree.** That work was #1086's commit 2; the board entry went straight to main
as board entries do, #1086 was then CLOSED rather than merged, #1087 carried only its commit
1, and the bookkeeping went with the closed branch.

**Measured on `d96a08da` just now**, so the gap is stated and not estimated:
`mi/scripts/validate_sources.py` carries 20 `PROVENANCE` entries and NONE of the three named
files is among them; `mi/WATCH.md` names exactly ONE `data/app` file, not fifteen; and
`build_eam_status.py` prints `| mi | EA· | 83 | 83/83 | 619 | 615 | all | 22 | 14 without a
job |`. So Flint's and Warren's ward geometry, and the coverage wash's own outline, are still
shipping with no monthly source check at all — which is the thing that entry was written to
say had been fixed.

**A board entry that goes to main on its own commit outlives the PR it describes.** That is
the whole mechanism of the defect and it is not specific to this one: every entry in this
section was pushed separately from the change it reports, so any of them can be left standing
by a PR that closes instead of merging. The fleet's convention is a new dated entry rather
than an edit to the old one, so the entry below stays as written and this one corrects it.

**I am not re-pushing commit 2 to fix it.** On #1087 I asked the manager whether they wanted
it back as its own PR and said I would not re-push without their word; that is unanswered
after five hours, and a promise does not lapse because waiting became inconvenient. The
question is restated under Open questions with what each answer costs. Correcting the record
needed nobody's word and is done here.

**2026-09-22, #1091 merged (`7aba70c`) — and the hold on it found three surfaces, not
one.** The manager held the first head because all 35 certified-returns counties rendered
the default districted lede, "exactly as the county publishes them", about counties like
Oakland whose site answers 403. The prescribed fix was to merge main in for #1089's
`lede`/`cta_note`/`desc` hooks and regenerate. That was right and it was not enough.

**The merge crashed on the second surface.** `desc`'s substitution supplied `head`, `named`
and `districts` where the `lede` hook beside it supplies five keys including `county`, so the
first regenerate died on `KeyError: 'county'`. It had never shown because these records are
that hook's first consumer — every other `desc` in the fleet is on the flat branch and uses
positional `%d`. The districted hook now takes the same five keys, plain rather than escaped,
because `desc` is escaped once at insertion where the lede is inserted raw.

**Two more surfaces carried the same claim and neither was hooked at all.** A page states its
provenance in four places. The standfirst under the H1 read "Every member of the Oakland
County Board of Commissioners, from the county's own published roster" and the foot
disclaimer read "every name above is published by the county itself" — on every page of both
routes. Fixing only the two the hold named would have left an opening paragraph naming the
election with the next line and the last line contradicting it. Both are overridable off the
record now, and the disclaimer is hoisted out of the page shell into `DEFAULT_DISCLAIMER`
carrying the template's own line breaks. **Byte-identity for everything else is measured, not
asserted: regenerating changed exactly 35 files and left the other 294 untouched.**

The two new sentences are written in `build_mi_returns_roster.py` beside the lede rather than
composed in the generator, for the reason the manager gave for the first three: one wording,
where the data is built. Both gates were negative-tested. The roster `--check` reads them by
CONTENT rather than presence — a standfirst carrying the default wording passes a presence
test and tells a reader the opposite of the lede beside it — and poisoning Alger's gives two
FAILs and exit 1; removing them gives `build_county_pages.py` a FAIL naming both, exit 1.

Manistee (returns) against Alcona (scraped), county names factored out, now differ on all
four surfaces, and the scraped county is unchanged.

**A stale figure in this file's own preamble, corrected in the same commit as this entry.**
It read "48 of the 83 counties name your commissioner — 366 of the 619 seats", which my own
change made false, and "20 recorded gaps — 13 no-source, 5 blocked", which was already wrong
before it: the shipped `coverage-gaps.json` carries 26, of which 17 are no-source and 7
blocked. The second was not mine and is recorded rather than quietly fixed, because nothing
gates that preamble against the file it describes and the next reader deserves to know it can
drift.

Battery after the last edit: 84 of 84 static gates, all six instance smoke tests, page
consistency 56 findings all 56 this sandbox's cert error and 0 non-cert, point-transmission
`--check` OK, contrast probe OK across 389 pages, SERP lengths OK. `validate_gate_counts`
unchanged at 72/100 with the steward mirror agreeing 100 for 100 — no CI step was added.

**2026-09-22, the certified-returns route is built and open as #1091 — all 83 counties name a
commissioner, 615 of 619 districts in the served bytes, up from 366.** Adam's ruling built to
the Clark posture: a separate file, `mi-commissioner-returns.json`, every record carrying its
own sentence naming the general election of 5 November 2024, the builder refusing to write one
without it, and the card's badge reading "Elected Nov 2024" rather than "Commissioner" —
a bare office badge is the claim the 2026-09-03 decision refused. The boundary file stays
name-free and its BANNED_FIELDS guard is untouched.

**The staleness measurement is the part worth keeping, and it is 366 seats rather than 123.**
The 48 scraped counties give a comparand for every seat the state layer also covers: 234
identical, 104 the same surname in a different form, 28 a different surname — and those 28
read by hand are 18 naming a DIFFERENT PERSON (4.9%), 9 misspelling the same one and 1 a
missing space. On the 35 themselves only Manistee renders names in its served bytes, and there
6 of 7 match while District 6 does not: certified David Miehlke, the county's own page names
Karen Goodman. The Wayne case confirmed on this cohort rather than assumed.

**Two counties could not be measured and are recorded as that rather than as agreement.** Van
Buren renders its directory through a component, so none of its seven names is in the served
bytes and a substring test reads 0 of 7 — the method failing, not the county changing; the one
apparent hit was inside a CSS `repeat(...)`. Newaygo's board URL in the probe artifact, read
2026-09-19, answers 404 today.

**Nothing is corrected and one spelling is recorded.** On the 35 the certified spelling is the
only spelling there is. Nineteen one-edit surname pairs across the layer reduce to three
candidates under an asymmetry filter, and Wexford District 2's `Jason L. Nelso` ships as
certified with the reasoning written down.

**Two things this change had to correct rather than add, and both were mine.** Two gap-record
summaries said the cards "name no one" in those counties, which my own change made false to a
reader. And the Michigan smoke test asserted that Ingham names nobody and "must not fall back
to the boundary column" — the old rule written down as a test. It is rewritten rather than
deleted: what it guarded moved rather than went away.

**Three labels of mine were wrong today and the code was right each time** — I called Ingham a
served county, guessed Genesee's FIPS as 081 when it is 049, and chased a duplicated line that
my own `sed` had printed twice. Each cost a detour and none reached the tree. Look the county
up; do not name it from memory.

**2026-09-22, #1086 was closed and #1087 carries its first commit. A reader-facing miss
survives on main and I measured it rather than assuming the outlines closed it.** The point
48.19701,-88.08566 — Lake Superior, north of Isle Royale — is inside `metro-outline.json`,
is in Keweenaw County by `state-counties.json`, is named by `mi-county-board-page-not-found`,
and is inside NONE of the 35 shipped gap outlines. So `appliesHere` is false for every
record, `mappable` is true, `inCoverage` is true, and the lede reads "Nothing recorded is
missing where you clicked" — the sentence the hold was about. Rate: 1 of the 1,867 wash
points that land in a gap county, out of 4,000 sampled inside the wash at seed 20260922,
which is 99.946%. Zero of the 4,000 fell in no county of the fabric.

**Three simplifications of one boundary is the cause.** Keweenaw's gap outline carries 59
vertices, the fabric's Keweenaw 108, and the wash is one dissolved ring simplified whole, so
slivers exist between the wash's edge and each outline's edge. **Neither fix closes it**: the
`located` change I wrote does not, because 34 other outlines load and the tolerance I kept
lets the claim stand; the strict build gate does not, because the tag has geometry that
simply does not reach the wash's edge. And the 1,225 internal-point assertions cannot see it
— every one is an interior point against a self-consistent outline set, and no interior point
tests an edge.

**What I would change, and it is my earlier objection in its correct form.** Split the 35 out
of `state-counties.json` rather than re-simplifying from TIGERweb at the wash's tolerance,
so the county the fabric places a point in and the outline that contains it are the same
geometry. I said match the fabric rather than the wash because a dissolve has no interior
borders, and I named county-to-county seams as the risk; the measured miss is at the
wash-to-outline edge, so the objection held and half my reason for it did not. Reported on
#1087 with the reproduction and offered to do the rebuild; I have not touched that builder or
any outline file, because the manager asked that we not both build the same 35.

**Of #1086's three commits, one landed and one is now on no path to main.** Commit 1 is in
#1087 in full. Commit 3, the engine change, I am not asking back — the strict gate prevents
the shape it guarded — except for the browser-level `smoke-gap-probe` span, which reads the
actual lede in Chromium where #1087's verification simulated `appliesHere` over the files.
**Commit 2 is unsuperseded**: the 14 `mi/WATCH.md` rows naming the file each clocked row
governs, and three missing `PROVENANCE` entries, so Flint's and Warren's ward geometry ships
with no monthly source check at all. Main reads `EA· … 14 without a job`. Asked the manager
whether to bring it back as its own PR rather than re-pushing a closed PR's work.

**The two entries below this one describe a BRANCH and not main, and they stay as written.**
This section is append-only dated snapshots, so the entry claiming Michigan reads EAM and the
entry saying the engine fix is addressed are left alone: both were true of
`claude/next-state-priority-tmedsi` on the day. Neither is true of main, which reads
`EA· … 14 without a job` and carries `mappable` in its original form. This entry is the
correction and its place is the top of the file rather than inside theirs.

**I OVERWROTE THIS FILE FOUR TIMES TODAY AND RECOVERED IT FROM GIT.** Each board push built
`mi/BOARD.md` from my FEATURE BRANCH's working copy and then pushed it over main. The branch
never receives board commits — they go straight to main by design — so its copy was stale by
construction, and every push after the first silently reverted the entries before it: only the
newest survived, and the file on main carried one entry where it should have carried four.
Nothing was lost permanently, because all four commits are the same base plus their own
insertions, so replaying them against that base with difflib recovers each one exactly; the
rebuild is verified by every distinctive phrase appearing once and by every base line still
being present bar the two that one commit deliberately replaced. No other file and no other
session's content was touched — all four commits are `mi/BOARD.md` alone, and the manager's
own board edits are in the root `BOARD.md`. **THE RULE: build a board edit from
`origin/main`'s version of the file, never from the branch's working tree.** A `git diff
--stat` showing deletions on an append-only file is the tell, and it was there on the second
push; I read it as a rewrap and did not check.

**2026-09-22, the hold on #1086 was right and is addressed in `29f1388f`. The engine no
longer lets the gaps panel claim a clean spot it could not test.** Read the code before
changing it: `appliesHere` swallowed a failed outline fetch as "not here", so a 404 resolved
exactly like a point outside the county, and `mappable` came off a record's county ARRAY
rather than off whether any outline had loaded. Both halves had to move. `appliesHere`
reports three answers now — here, not here, could not tell — and `mappable` reads the third.
The third case gets its own words, because "these gaps aren't mapped to particular places" is
false of a record that names five counties and true of one that names none. Michigan's lede
at the Munising point reads "We could not check which of these affect the spot you clicked."

**One limit was kept rather than tightened, and it is the part worth disagreeing with.** One
outline loading and missing is still treated as evidence the point is clean — the same
tolerance the panel already extends to records carrying no county at all. Requiring every
tagged county to have located would be stricter and would suppress the clean-spot wording for
every reader of an instance with one unloadable outline. It is in the block's comment rather
than decided quietly.

**"Michigan is the only one affected" was checked rather than assumed**, across all six:
il 98 counties tagged / 101 outlines, ny 5/5, ca 1/1, wi 72/72, ia 2/2, mi 35/0. So the fix
is fleet-wide and changes one instance's reader today, with Iowa next in line at 2 outlines
for 99 counties.

**The 105 requests were exactly 105, measured in Chromium rather than estimated**: 35
counties times three attempts, all 404, with the fetch helper's 500 ms and 1000 ms backoff
between each pair, and zero further requests on a second open in the same session — the
rejection cache already handled that. The outline loader passes 0 retries now and it is 35.

**The check that would have caught it exists now.** `mi/scripts/smoke_test.mjs` carries the
reference fork's `smoke-gap-probe` span with a real fixture: Munising, in Alger County, which
`mi-county-board-no-district-key` names, verified against this instance's own
`state-counties.json` to fall in Alger and in no other county. All four of the manager's
points are recorded there. The expectation is DERIVED from the tree — whether that county's
outline file exists — so the day the outlines ship it flips to asserting the gap leads the
list rather than going on accepting the weaker wording. Reverting `mappable` alone in
`mi/index.html` fails it with the exact sentence the hold named.

All six instances' smoke tests pass, the static battery is clean, and no cache bump was
needed because `SHELL_URLS` is network-first.

**2026-09-22, Michigan reads EAM and is the first instance in the fleet to pass all three.**
Pushed to #1086 as a second commit. All 21 app files are under a stated plan, which took
naming rather than building: every one of the 14 the measure called unplanned already had a
`mi/WATCH.md` row stating a real clock and naming the builder to run, and not one named the
data file it writes. The measure's rule is a row that names the file and states a when, so
these were the mirror image of a loophole — the when was there and the filename was not.

**What Michigan's M rests on, so nobody has to infer it from a three-letter mark.** Seven
files under weekly jobs that rewrite them. Fourteen under cadences a person performs —
thirteen riding `mi-validate-sources.yml`'s monthly tracking issue, one quarterly by hand.
Adam's ruling allows that and gives the reason (a weekly job on a boundary is a guaranteed
no-op), and it is still a weaker guarantee than a rewrite.

**Three files were not in the monthly source check at all** — `metro-outline.json`,
`mi-flint-wards.json`, `mi-warren-wards.json` — so `mi-validate-sources.yml` had no
`PROVENANCE` row for them. Iowa registers its outline and Michigan did not. That mattered
before it was bookkeeping: a row saying "monthly, with `mi-validate-sources.yml`" would have
been false for Flint and Warren. All three answer HTTP 200 to the districtry token, measured
today; TIGERweb layer 1 names itself `Counties`, Flint's FeatureServer lists one layer, and
Warren's `serviceDescription` is the item snippet its builder quotes.

**One claim I nearly shipped was wrong and the two table lengths are what caught it.** The
draft row for `coverage-gaps.json` said the weekly commissioner job re-tries every county a
gap record names. It walks 58 of 83: `COUNTIES` holds the 48 that ship and `PROBES` the ten
candidates. So ten of the 35 counties named by records are re-fetched every Saturday and 25
are re-fetched by nothing, two of those policy-shut at any cadence. The row states that split
and puts the 25 plus the nineteen city and fabric records on a quarterly re-probe.

**I did not widen either gate, and both near-misses are written up as questions below.**
`build_eam_status.py` is untouched by this change. Its `WHEN` vocabulary rejects "whenever
TIGERweb rolls a vintage", which is a trigger its own docstring says should count, and
`watched_by` reads workflow text only, so a watcher whose subject list lives in the script it
invokes is invisible. Both would move il, wi and ia too, and widening a measure to get a pass
is the one move this repo's own rules put out of bounds.

**2026-09-22, the follow-up shipped as #1086 — Michigan measures 83 of 83 on EXAMINED.**
#1081 landed, so the derivation the two entries below describe as held is now committed. All
six records carry `counties`, parsed out of their own `area` strings through
`build_county_status.slug_of`: robots-declined 5, access-controlled 6, no-district-key 8,
prose-roster 4, page-not-found 10, no-website 2 — 35 counties. `build_coverage_gaps` reports
6 mapped to counties and `docs/EAM_STATUS.md` reads `mi | EA· | 83 | 83/83`.

**The array is measured now, not trusted.** `probe_mi_county_boards.py --check` compares the
union of the six arrays against both tables that know which counties are shut — the probe
artifact's 25 rows and the 10-county `PROBES` table in the scraper — and fails four ways: a
county we do not serve that no record names, a county named by a record that we do serve, a
county in two records, and a record whose `area` prose and `counties` array disagree. Before
the arrays were filled it failed naming exactly the 35 plus all six prose-vs-array
disagreements. Three negative tests each name the county: `alcona` added to a record,
`genesee` doubled, `shiawassee` dropped. Written because the empty arrays were the second
time this instance shipped a claim nothing compared against the thing it claimed.

**`probes_fips()` no longer parses that span itself.** It calls a new `probes_table()`, the
one reader of it, because the gate needed the county NAMES the FIPS reader was discarding and
a second parse of one hand-written literal is how the key-order defect #1069 fixed got there.
`mi_slug()` is a deliberate copy of `slug_of` rather than an import, and says so: that
function's one override maps `De Witt` to `dewitt`, an Illinois county.

**Nothing is served that was not served yesterday.** All 35 were already measured shut and
written up; what changed is that the fleet's own measure can see it. MAINTAINED is unchanged
at 14 of 21 app files with no plan and is the next bar.

**2026-09-22, #1082 merged as `bd9060c8`, verified on the merged tree.** All five gates pass
there — `build_coverage_gaps --check --metro michigan` at 26 gaps (7 blocked, 2 data-quality,
17 no-source), `build_about_page --check` at 152 recorded gaps fleet-wide, `build_sitemap
--check`, `build_history_page --check`, and `validate_skills` at 775 pointers. All six
records are in the file a reader downloads, each with the kind it was assigned by reading.

**The follow-up is still blocked and the reason is unchanged.** #1081 has not landed — main
still carries `if outlines is not None` at line 198 and ships no `build_eam_status.py` — so
all six records read `counties=0` and Michigan stays 48 of 83 on EXAMINED. Nothing about
that is new information; it is the state #1082's own body predicted. When the fix lands the
arrays are one derivation over the committed tree.

**2026-09-22, the gate fix works and Michigan measures 83 of 83 — but the follow-up cannot
be pushed until #1081 lands.** Measured, not predicted: with #1081's one-line fix applied
locally and uncommitted, and `counties` populated on all six records, `build_coverage_gaps`
reports 6 mapped to counties and Michigan reads **EA·** at 83/83. Then I reverted both. The
fix is on the manager's branch at `144ce42` and main still carries
`if outlines is not None` at line 198, so on main's gate all 35 tags are refused — I
confirmed that too, `county 'genesee' has no data/app/genesee-county-outline.json` and 34
more. Populating the arrays on my branch today would turn #1082 red and keep it red until
#1081 merged, so it is held rather than pushed, and #1082 stands as it is.

**The follow-up needs nothing preserved.** The county names live in each record's own `area`,
already committed, and the slugs derive from them with `build_county_status.slug_of` — so
when #1081 is on main this is one derivation over the committed tree, not a re-typing of 35
names. That was deliberate: deriving the slugs from the prose a reader is shown means the two
cannot drift, and there is only one place the names live.

**On the shortcut the manager declined.** Matching county names in the `area` prose would
have needed no gate change, and "Bay City" contains the county "Bay" — Michigan ships a
`bay-city-ward-boundary` gap record, so that route would have credited Bay County for a gap
about a city in Saginaw County. Worth stating because it is the same failure I hit an hour
earlier from the other direction.

**MAINTAINED is the next bar and it is 14 of 21 app files with no plan.** Not started. Under
#1081's widened measure a `WATCH.md` row naming a file and stating when it is re-checked
counts, so most of Michigan's 14 are a cadence question rather than a watcher to build —
`mi-commissioner-districts.json` is a decennial apportionment filing, the four TIGERweb
fabric layers roll on the census vintage. It waits on #1081 landing too, since the measure
that defines the bar is on that branch.

**2026-09-22, the probed blockers are gap records now, and it is 35 counties rather than
25.** #1082 open. The probe artifact holds 25; the `PROBES` table in
`mi_commissioner_scraper.py` holds 10 more it was gated on, and 48 + 25 + 10 = 83. That
second table is exactly as invisible to a gap-record reader as the first, so promoting only
the 25 would have left Oakland (19 seats), Ingham (15, the state capital), Genesee, Ottawa,
Livingston, Allegan, Washtenaw, Bay, Gogebic and Marquette in the state this change exists
to end. Six records rather than 35, because with no county outlines there is no
location-awareness and every record shows to every reader — each names its counties in
`area` and in the summary, grouped by what a reader could do about it. Michigan goes 20 to
26 gaps.

**EXAMINED does not move, and that is measured rather than predicted.** 48 of 83 before and
after, run with `build_eam_status.py` from #1081 against my own tree. Two things compose:
its `gap_counties()` reads only each record's `counties` array, and `build_coverage_gaps.py`
refuses a slug with no `data/app/<slug>-county-outline.json`. Illinois ships 101 of those
files; Michigan ships none. Negative-tested rather than inferred — tagging one county
returns `county 'alcona' has no data/app/alcona-county-outline.json`. So the promotion
delivers the stated purpose in full and delivers nothing to the score. The question below is
what to do about that, and it is a change to a shared gate rather than to this instance.

**I classified the ten by keyword-matching their prose first, and got two wrong in opposite
directions.** Bay landed in robots-declined because its write-up mentions a subdomain's
robots file; Marquette missed that class because its text does not contain the literal
string. The artifact's fields are structured and were used; the table's are prose for a
human and were read. Two records were also corrected against the artifact rather than
against my own earlier entry here: Tuscola is robots-disallowed on `.com` and
Sucuri-challenged on `.org`, and Branch's blocker is a 202 on its `.gov`, not robots at all.

**The gap-record skill's own regeneration list was two short.** A run that followed §7
exactly still failed `build_about_page` (the fleet-wide recorded-gap total, 146 to 152) and
`build_sitemap` (`mi/history.html`'s lastmod). Neither reads the gaps block directly, which
is why they were not obvious — one counts the shipped gap files, the other dates a page
those files regenerate. Both added to the skill with the miss recorded.

No reader field carries a count: `counted_prose_problems()` returns early when `counties` is
empty, so a number written in this shape is checked by nothing. 85 of 85 static gates pass,
the Michigan smoke test passes, `page_consistency_test.mjs` 0 non-cert. No host was fetched.

**2026-09-21, #1069 merged as `38f479e3`, verified on the merged tree.** The probe gate
passes there, `probes_fips` reads 10, and the frontier prints 48 ship / 10 recorded shut /
25 untried, which is the 83. `build_coverage_gaps.py --check --metro michigan` and
`build_history_page.py --check` both pass, Michigan's gap counts unmoved at 20 (5 blocked,
2 data-quality, 13 no-source). The ruling is in the merged bytes in all three places, and
Muskegon's `wanted` no longer offers a route the operator closed — the one reader-facing
field in the change.

Michigan has nothing unblocked again. The three questions below are all unanswered, and the
Tasks row above is still the manager's to update.

**2026-09-21, the assigned task was already shipped, so this is what I found looking for it.**
#1069 open. Tranche 6 is in, and tranche 7 with it: measured on today's tree,
`mi-commissioner-members.json` names 48 of 83 counties and 366 of 619 districts, and the
probe's candidate list holds zero. The Tasks row reading "26 of 83, 229 seats, assigned —
tranche 6" is the one my 2026-09-19 entry flagged as discharged. It is still the manager's
to update; nothing under it is outstanding.

**What I did instead, and it is a real defect.** `frontier()` in
`probe_mi_county_boards.py` finds the counties recorded shut with a regex over the whole
scraper source requiring `"county"` before `"fips"`. That file writes all 48 `COUNTIES`
entries fips-first and all 10 `PROBES` entries county-first, so the regex matched `PROBES`
exactly and `COUNTIES` not at all — right, and only because two tables in one file disagree
about key order, with the order it needed in the minority style. Rewriting one `PROBES`
entry the way every `COUNTIES` entry in the same file is written, which changes nothing
about its meaning, dropped that county out of the set and turned `--check` red with
"re-run the sweep". I proved it on Gogebic, whose robots.txt disallows this client, so the
gate's own advice would have been a fetch we may not make. Four of the ten refuse us that
way.

The fix reads the table's own span, takes either key order, and fails loudly when the parse
cannot account for every entry in it — the three per-entry keys must agree on the count and
the FIPS must be distinct. Three negative tests, each red before and after in the right
direction. I did not add an 83-county assertion: `frontier()` subtracts the built and
recorded sets from the shipped geometry, so 48 + 10 + 25 = 83 is arithmetic rather than a
claim, and a gate on it could only be vacuous.

**A negative result worth keeping, because deriving it cost most of this turn.** Every one
of Michigan's 83 counties is already in a machine-readable table — 48 in `COUNTIES`, 10 in
`PROBES`, 25 in the probe's artifact — and the partition is already held, because the
probe's `--check` compares the artifact against a frontier derived from the tree. A county
retired from `COUNTIES` that stops shipping lands in that frontier and turns the gate red.
I went looking for a hole there and there is none. Three times on the way I had a framing
that a measurement then contradicted: the ten looked unaccounted, then prose-only, then
`PROBES`-recorded. The record was right each time and my reading of it was not.

**The ward ruling is recorded where the repo still called it open**, which was the other
half of this change. `mi/WATCH.md`'s WARD-column row said the state route "is the operator's
call"; Wyoming's blocker said "the state route is open"; Muskegon's `wanted` offered "the
state fabric if that route is opened". All three now state the ruling, and Wyoming is a
measured shut rather than a pending decision, because its record already measures no city,
county or regional route either. Muskegon's `wanted` is the one reader-facing field in the
change, 185 characters against the 240 cap.

**Jackson is not settled by it, and my question was the thing that was wrong.** I asked
whether "the state's precinct fabric" may be the source, which conflated two cases. Jackson's
proposed source is Jackson County's own precinct layer — a different publisher — which
leaves the state's fabric as a genuinely independent second witness, a distinction its gap
record had already drawn before the ruling arrived. The narrower question is below.

Battery from the current `smoke-test.yml`: 85 static gates pass, the Michigan smoke test
passes, `page_consistency_test.mjs` reports 0 non-cert findings. No host was fetched for any
of this.

**2026-09-20, #1054 merged as `16e706a8`, and #1052 was closed rather than merged.**
Verified on the merged tree, not on my own PR body. `build_mi_commissioner_roster.py
--check` passes: **48 counties, 366 districts**, 45 carrying a `readAt`, three preserved
— Berrien (021), Kalamazoo (077), Kent (081), all three carried since 2026-09-19 behind
the Cloudflare challenge, each printed on every run. Delta (041) and Otsego (137) are in
the file, and `mi/county-commissioner/delta.html` and `otsego.html` name Malnar,
vanGinhoven, Deming and Drzewiecki in their served bytes. `validate_index.py` OK at 15
layers and 83 counties; `validate_gate_counts.py` and `validate_steward_mirror.py` still
agree at 68 named static steps and 95 invocations, so the merge moved neither.

#1052 closed at 00:11:06Z with **1,191 deletions that never reached main**. Fourteen
commissioners and two county pages stayed up.

Main's own push run on `16e706a8` was still in flight when this was written (run
35478684392, started 00:24:22Z). The check-in at 00:57Z confirms it and then stops; a red
main from this change would still be mine.

Michigan is back to having nothing unblocked. All three questions below are unanswered.

**2026-09-20, #1054 is green.** `smoke` concluded success on `b5825799` (run
35477402846, 23:55:29Z to 00:06:38Z), no review threads, mergeable clean against main at
`92511056`. Two things wait on the manager: merge #1054, and close #1052 rather than
merging it — a fresh weekly run on this code produces the same roster, 48 counties and 366
districts, without the Delta and Otsego deletions.

Nothing here is unblocked. Both questions below are still unanswered.

**2026-09-19, #1052's cause, and it was mine.** #1054 open. Delta and Otsego were serving
normally — re-read here at 5 of 5 in 110,308 bytes and 9 of 9 in 108,745 — so nothing at
either county had changed. The cause is in `mi_commissioner_scraper.py`, and the floor that
should have caught it is one I wrote during the Cass tranche.

`read_page` returns a fetch failure, and the loop PRINTED IT AND CONTINUED, so the county was
simply absent from the cache; only robots refusals reached `refused`. The builder then could
not tell a dropped connection from a county nobody tracks. And the floor permitted exactly
this event by construction: its basis was "any two counties may go dark", 48 − 2 = 46, tested
with `< MIN_COUNTIES`, and the run produced exactly 46. **A global count cannot protect a named
county.** The cache-write comment stated it as intent — "a county that has stopped yielding
must leave the file rather than linger on last week's answer" — which reads *was not read* as
*stopped yielding*, the distinction `check_roster_retention` has been drawing all along.

Michigan was the last statewide instance still deleting. It now carries a county forward per
Adam's ruling, only where the scraper says it TRIED, so a county retired from the table still
leaves normally.

**The second half was worse than the deletion, and I had not seen it.** A county read whose
parser matches nothing reached the roster with zero districts, passed every gate, and the card
then said "0 of 5 — named by nobody on the county's own page" about a county whose page names
all five. That is an affirmative false claim about a public body.

**I also got the fix wrong once.** My first version failed the run on a parsed-zero county.
The full run then had Midland parse to zero from a page that answered, and re-read alone it
gave 7 of 7 in 120,480 bytes — so that version would have turned the weekly job red on a flake,
which is how a reviewer learns to skim. Parsed-zero is now carried forward and printed, and the
ceiling is what turns a genuinely broken parser into a failure. The ceiling measures
`preservedSince` rather than `readAt`, because my first draft invented a `readAt` from the run's
own clock and stamped three counties as read today when they had not been read at all.

**On the manager's suggestion.** It proposed failing the run when a county that returned members
last week returns none this week. I did not take that shape: failing blocks the other 47
counties' real changes, and the Midland flake showed it would fire on transport noise. Preserve
plus a ceiling keeps the reader's answer, lets the rest of the state refresh, and still goes red
when a source is genuinely gone.

**A REAL FINDING WHILE TESTING: Kalamazoo, Kent and Berrien went behind a Cloudflare managed
challenge today.** `Cf-Mitigated: challenge`, a 5.7 KB "Just a moment..." body, on three
unrelated domains, with the egress proxy's own CONNECT returning 200 — so it is the sites and
not this sandbox. An access control, never worked around. Their 42 seats are carried forward and
the ceiling fires around 2026-11-03 if it has not lifted; `mi/WATCH.md` carries the row.

#1052 should be CLOSED rather than merged: a fresh weekly run on this code produces the roster
without the deletions. Roster content is unchanged at 48 counties and 366 districts.

**2026-09-19, the Detroit summariser merged, and Michigan is out of unblocked work.** #1047
is in as `08277b1f`, verified on the merged tree: the selftest passes there at 25 checks, the
CI step sits at `smoke-test.yml` line 95, and `validate_gate_counts.py` and
`validate_steward_mirror.py` agree at 68 named static steps and 95 invocations.

**Two rows in the Tasks table above are discharged and are the manager's to update.** The
commissioner row still reads "26 of 83 counties — assigned, tranche 6"; it is 48 of 83, 366 of
619 seats, tranche 7 merged, and the probe's candidate list is empty. The Detroit PR-body row
is #1047.

**What is left, and why none of it starts on its own.** The wards row waits on the
state-fabric-as-source question below. The 23 remaining shut counties wait on the request
budget below. The bbox row is now a question too, for a reason worth stating: that row says
"no fix proposed", and `mi/WATCH.md` proposes one — it is the scope that stops it, not the
absence of a route.

**2026-09-19, the Detroit PR-body task, and what it turned up.** #1047 open. The weekly
Detroit roster PR now writes its own title and body from the diff. The measurement that
justified it: across every commit that has ever touched that roster — three — the two that are
refreshes moved `archivedAt` and nothing else, while the body said "this changes data about
real officeholders. Please review the diff before merging." False on two of two.

**The bigger find was not the body.** `archivedAt` is null when the scraper's DIRECT rung
served and a timestamp when the Archive did, so the file records which rung answered each
week: archive on 2026-09-05, **null on 2026-09-09 — detroitmi.gov served this client
directly** — archive again on 2026-09-16. The Cloudflare challenge is intermittent, and four
places stated it as permanent: the workflow header, `mi/WATCH.md`, the builder's docstring and
`EXPECTED_UNREACHABLE` in `scripts/validate_card_links.py`, whose own comment says "the day
this answers is the day that scraper's direct rung serves and the archive hop can go". That
day came and went unremarked, because that inversion runs monthly and the PR body was static.
All four now state what was measured with its date. The entry STAYS — one success in three is
not a lifted block — and nothing here claims the block's current state; the next weekly run
says so in its own title.

Two defects caught in the writing, both worth the space. The selftest's OK line read
`"OK — %d checks" % 0 if not failures else "FAIL"`, which binds before the conditional and
could only ever print "0 checks" — a gate reporting itself vacuous. And the test fixtures used
real `detroitmi.gov` paths, so `probe_user_agents.py`, which reads URL literals out of Python
files, had started recording this script as a caller of a host it never contacts.

Battery 85 static all pass, 9 of 10 browser, `page_consistency_test.mjs` 0 non-cert. Gate
pair restated to 68/95, measured after the last edit.

**Michigan now has nothing left that needs neither a fetch budget nor an operator answer.**
Both board questions below are open and unanswered.

**2026-09-19, the probe's robots gap merged.** #1045 is in as `1619003e`, verified on the
merged tree rather than on my own PR body: `probe_mi_county_boards.py --check` passes there,
the CI step sits at `smoke-test.yml` line 81, and `validate_gate_counts.py` and
`validate_steward_mirror.py` both agree at 67 named static steps and 94 invocations.

**New York's statewide go-live merged between my branch point and this one** (#1042,
`3416c6b5`) and moved none of the battery — it touches neither `smoke-test.yml` nor
`CLAUDE.md` nor the steward skill — so the pair above is the merged tree's own figure and not
one carried across a merge unchecked. That is the case `CLAUDE.md` warns about, where two
branches are each right against their own base and the silently-merged half is the dangerous
one; it was checked rather than assumed.

Michigan has no tranche work left that needs neither a fetch budget nor an operator answer.
The candidate list is empty, the 23 remaining shut counties wait on the request budget asked
for below, and the ward front waits on the state-fabric-as-source question. The next item
needing neither is the Detroit PR-body task on the Tasks table.

**2026-09-19, the probe's robots gap closed.** #1045 open. Every county row in
`mi-county-board-probe.json` now carries the robots reading for the host the probe ACCEPTED,
not only for the ones it rejected, and `--check` fails a record that names a URL without one.
The reading keeps the verdict's own `why` — "robots.txt served (N bytes): <the deciding
rule>" — because a status alone cannot settle a disagreement: both of the contradictory
Gogebic readings would have said `served`. Host and board page are recorded separately, since
one file can allow `/` and disallow the path a board page sits under.

Backfilling the 25 recorded counties cost 33 readings and 24 fetches — robots.txt only, no
page, no verdict touched — and found two counties whose recorded reason is no longer the one
that governs. `www.iosco.org` now answers HTTP 403 on robots.txt, which the strict reading a
county website gets makes a refusal; read three times on both spellings, identical each time,
carrying `server: cloudflare` and the site's own `cf-ray`, so it is the host and not this
sandbox's proxy, which answered 200 to the CONNECT. `tuscolacounty.com` serves a 26-byte
robots.txt that disallows this client, where its recorded `challenge` came from its other
host. So **two of the 25 shut counties are shut by policy rather than by an absent page**,
which is what a re-examination should now expect.

Wiring `--check` into CI is what asked a second question the probe had never been asked: it
had reached across trees for `scripts/scraper_common.py`'s UA token since the day it was
written, and `validate_workflow_deps.py` had never looked, because that gate only reads the
scripts a workflow runs. A rule enforced only where a gate happens to look is a rule three
files were keeping by hand. The token is in-tree now with the note its siblings carry, and
`import requests` sits inside the one function that builds a session — proved by running
`--check` with an `ImportError`-raising `requests.py` on the path.

Battery: 84 static invocations pass, 9 of 10 browser gates pass, and
`page_consistency_test.mjs` reports 72 findings with 0 non-cert — all of them the GoatCounter
beacon's `ERR_CERT_AUTHORITY_INVALID` in this sandbox.

**2026-09-19, tranche 7 merged.** #1041 is in as `cb07f95e`, verified on the merged tree
rather than on my own PR body: `mi-commissioner-members.json` carries 48 counties and 366
districts, Cass holds 8 of 8 with District 1 reading Thomas Langley and
thomasl@cassco.org, and `mi/county-commissioner/cass.html` names both in the served bytes.
`validate_index.py`, `build_county_pages.py --check` and `validate_gate_counts.py` all pass
on that tree.

**The PR took three base merges and two of them were substantive**, which is the part worth
carrying. Main added a gate the branch's CI had never run — `validate_workflow_checkout.py`,
which exists because a sitemap-committing workflow in a shallow clone dates every entry to
the run day, and this change rewrites `sitemap.xml` — and then a Court of Appeals staleness
step. The battery went 80 → 81 → 83 no-browser invocations, and each time it was re-extracted
from the merged `smoke-test.yml` rather than from a saved list, because the gate list is the
thing that changes. A PR that sits for two hours on a fast-moving main is not idle; the
question is whether what landed is gated, and only a merge-base diff answers it.

Picking up the probe's own robots gap next — it needs no answer to the board's open question
and is the recorded prerequisite for any further sweep.

**2026-09-19, tranche 7 open.** #1041. Cass names its eight commissioners,
seven of them with an e-mail address. **48 of Michigan's 83 counties, 366 of
the 619 seats, 61.4% of the state by population** — and the probe's candidate
list is now EMPTY.

Cass cost two requests: its robots.txt and its board page, and it widens the
weekly run by one page from now on, which is the trade stated rather than made
quietly — seven addresses for one more request a week to a host already read. It was the last
candidate because the probe had scored the wrong page — the URL on its record
is the board's COMMITTEES page, which names all eight districts across five
committee rosters and is not a roster. A parser built on it would have shipped
a whole board and lost any commissioner who sits on no committee, and the
probe's own evidence cannot tell that page from the real one. The board page is
a different URL, linked from the committees page itself.

So Cass is the only county here that reads two pages, and each does one job.
The board page carries the people and the districts and no contact at all; the
committees page carries an address and the member's own district on one line.
The board page decides who is on the board. The committees page only adds an
address to a district already named, a district the two disagree on gets no
address and keeps its name, and a committees page whose shape has moved —
fewer than five addresses joining — refuses rather than shipping a thinner
card quietly. A committees page that simply does not fetch costs its own column
and nothing else.

Two stale things were corrected on the way past. The scraper's own docstring
still said twenty-six counties across four tranches, in three places, two
tranches after that stopped being true. And the sources page's comparison
against the state's own commissioner column was tranche 3's: re-measured across
all 48 counties, 234 of 366 seats agree exactly, 132 differ, and 18 of those
132 name a different person.

What is left on the probe's record is 25 counties measured shut, which is a
re-examination rather than a re-probe, and the probe's own gap: it records a
robots verdict only for the hosts it rejects, never for the one it accepts.

**2026-09-19, tranche 6 open.** #1035. Twenty-one more counties name your
commissioner: Alcona, Alpena, Arenac, Chippewa, Clare, Clinton, Delta, Emmet,
Houghton, Isabella, Lake, Luce, Mackinac, Menominee, Montcalm, Ontonagon,
Oscoda, Otsego, Presque Isle, Roscommon and Schoolcraft. That is **47 of
Michigan's 83 counties, 358 of the 619 seats, 60.9% of the state by
population** — up from 26 and 55.1% this morning. Each has its own page with
the names in the served bytes.

**No host was fetched to write any of it.** Every page came from the copy saved
during tranche 5's sweep, so those counties have seen two requests each in
total across both tranches.

**The catch that justified the pass is Houghton.** Its page puts the district
AFTER its own member, so the obvious reading gives a clean four of five with
every one paired to the wrong person and District 4 unnamed — and nothing in
the output says so. Mackinac is the same question with the opposite answer, so
every parser now states its side. Seven more traps are recorded at their
parsers, including a zero-width space in front of a Luce commissioner's name
and a shared county inbox that Chippewa would have handed to District 5 as
their own.

**It also found a defect in yesterday's work.** co.hillsdale.mi.us drops about
one connection in three from here and the drop lands on robots.txt, which is
read before the page — so the retry I added yesterday never covered it. Three
consecutive failures in one run dropped a county that had shipped that morning.
The robots read now retries five times.

**Cass is the one candidate left and I did not build it.** The URL the probe
scored is the board's committees page. All eight districts do appear across its
five committee lists, so a parser could assemble a whole board from them and
would silently lose any commissioner who sits on no committee. It waits for one
fetch of the real board page.

Next: Cass, then the 25 counties the probe recorded shut, then the probe's own
gap — it records a robots verdict only for the hosts it rejects.

**2026-09-19, merged.** Tranche 5 is in (#1033, merged 13:45 UTC as `3fb98206`).
Click a point in Barry, Cheboygan, Dickinson, Hillsdale, Ionia, Kalkaska,
Leelanau, Oceana, Osceola or Sanilac and the County Commissioner District card
now names the person, with a phone or an e-mail wherever the county publishes
one. That is 26 of Michigan's 83 counties, 229 of the 619 seats, 55.1% of the
state by population, up from 51.6%. Each of the ten also has its own page under
`mi/county-commissioner/` where the names are in the served bytes.

Picking up tranche 6 from the same list. The probe's remaining **22**
candidates need no new discovery, and every one of their pages is already
saved from last night's single fetch, so tranche 6 needs no fetch at all.
I published 24 last night and it was wrong — 34 minus the ten that shipped,
forgetting that Gogebic and Marquette left the pool the same day. 22 is the
artifact's own count after `--prune`.

**2026-09-19, later.** Tranche 5 is open as #1033. Ten more counties name your
commissioner: Barry, Cheboygan, Dickinson, Hillsdale, Ionia, Kalkaska,
Leelanau, Oceana, Osceola and Sanilac. That takes the card from 16 counties to
26, from 165 named seats to 229, and from 51.6% of Michigan's people to 55.1%.
Each of the ten also gets its own page under `mi/county-commissioner/`, where
the names are in the served bytes rather than behind a fetch.

**The weekly refresh has now run, and it moved nothing.** I dispatched it by
hand rather than waiting for the cron: run 35415178348, every step green, and
the change check came back empty, so the "open a pull request" step was skipped.
That is a result rather than a non-event. Those sixteen counties' names had
never been re-read since the day they shipped, and now they have been, and all
165 seats still name the same people. It is also the first evidence the roster
is stable rather than merely unchecked, and the job is proven end to end.

**A workflow that has never run is invisible to every gate here**, because
nothing in this repo measures the absence of a run. Michigan's was correctly
wired the whole time. Worth a sweep across the fleet at some point: which other
scheduled jobs have zero runs?

**On timing.** The instruction to update the board and pause reached me at
02:43 UTC, and tranche 5 was already built and under test by then; it opened as
#1033 eight minutes later. I have not started anything since. #1033 is watched
and I will drive it to green if CI goes red, but no new county work tonight.

Three things worth knowing from the work:

- **Two of the probe's candidates cannot be fetched at all.** Gogebic and
  Marquette each serve a robots.txt that disallows this client, read three
  times in a row, byte-identical to each other and to Genesee's and Ingham's.
  Both were recorded as candidates the day before. Either those files changed
  inside a day or the probe's read differed, and I cannot tell which: no
  archive holds either file, and the probe writes a robots status only for the
  hosts it rejects. That is the probe's own gap and it is recorded in its
  docstring.
- **Hillsdale is the opposite case.** Its robots.txt failed twice with a
  connection reset — which is disallow-all — and served a file allowing this
  path on the third try. A single transport failure is not a measurement. The
  scraper retries the transport now; it still takes a refusal and an HTTP
  status as answers.
- **Ionia District 3 is a seat the county itself calls vacant**, which is a
  third kind of unnamed seat beside Monroe's malformed row and Lenawee's
  self-contradiction, and gets its own sentence on the card. Its page carries
  the previous commissioner's whole entry commented out beneath the word, so a
  parser that reads comments would name a man the county has removed.

Every host in the tranche saw two requests, robots.txt and the page. Each page
was saved once and every parser written offline against the copy, because six
sweeps in four days tripped a WAF on Tuscola while the probe was being written.

Next: the candidates this tranche did not take. They need no new discovery.
(I wrote 24 here; it is 22 — corrected in the entry above.)

**2026-09-19.** Picking up tranche 5: more county commissioner names, from the
34 counties the probe in #989 measured as publishing a district-keyed board
page.

What the commissioner card gives a reader today is a name in 16 of 83 counties.
That is 165 of the 619 seats and 5,200,503 of Michigan's 10,077,331 people,
51.6%. In the other 67 counties the card gives the district number and names
nobody. The 34 candidates are 216 more seats and 1,064,500 more people;
shipping all of them would take it to 62.2%.

The candidates in population order start Clinton 79,128, Ionia 66,804, Montcalm
66,614, Marquette 66,017, Isabella 64,394, Barry 62,423, Cass 51,589. Clinton is
the largest of the 34, and 15 of them are under 25,000 people. Michigan is a
long tail from here, so a tranche is worth judging by seats and by whether the
page yields, not by population.

**The weekly refresh has never run.** `update-mi-commissioner-roster.yml` has
zero runs, ever. It is wired correctly — cron `30 20 * * 6`, `workflow_dispatch`,
in the shared root — but it landed on Saturday 2026-09-13 after that week's slot,
and tonight is the first Saturday since. So the 16 counties' names have not been
re-checked since the day they shipped, and the job has never been proven end to
end. I am dispatching it by hand rather than waiting for the cron.

The three items carried into the Tasks table, with the state I measured them in:

- **PR #979** merged on 2026-09-16. Its whole diff was one line: Detroit's
  roster going from `archivedAt: null` to a real snapshot stamp, so the card now
  prints which day's archived copy it read.
- **Tranche parser candidates** is `mi/data/source/mi-county-board-probe.json`,
  measured 2026-09-18: 34 candidate, 11 no-board-page, 7 no-districts, 3
  not-keyable, 2 no-confirmed-host, 2 challenge. It is the tranche 5 work list.
  `candidate` means a parser is worth writing, never that the county will ship.
- **Detroit PR-body proposal** is not implemented and is written down nowhere in
  the repo. The weekly Detroit PR body is one static paragraph, identical every
  week whatever changed, so it cannot tell a reviewer that a run moved a
  snapshot stamp rather than a person's name. It is worth doing and it is worth
  less than the roster.

Two corrections to my own last report:

- I said Emmet publishes 10 e-mail addresses as `mailto`. It publishes no
  `mailto` and ten Cloudflare-obfuscated ones. Same information, different
  markup — the Brown County shape the Kent and Lapeer parsers already decode.
  Lake (14) and Schoolcraft (5) are the same.
- Seven of the 34 candidates have a state-layer population that disagrees with
  the census, and Cheboygan's seven districts all publish Population 0 against a
  census 25,579. The probe artifact records the layer's figure and says so; every
  share above has the census on both sides.

## Open questions for Adam
**2026-09-22 — #1086's commit 2 is unsuperseded, on no path to main, and I promised not to
re-push it. Does it come back?** What it is: fourteen `mi/WATCH.md` rows naming the data file
each already-clocked row governs, and three `PROVENANCE` entries in
`mi/scripts/validate_sources.py` for `metro-outline.json`, `mi-flint-wards.json` and
`mi-warren-wards.json`. Measured on `d96a08da`: that table carries 20 entries and none of the
three, `mi/WATCH.md` names one `data/app` file, and the E.A.M. row reads `22 | 14 without a
job`. **The patch has decayed since I last tested it, and I nearly wrote "applies cleanly" into
this very entry before re-running it.** `git diff 9346ace7 3b383b82` applied to main at about
16:55 today; against `d96a08da` it does not. Measured per file: the 55 lines of
`mi/scripts/validate_sources.py` — the three `PROVENANCE` entries, which are the part that
closes the real hole — still apply CLEANLY; `mi/WATCH.md` CONFLICTS and needs a three-way
apply and a hand resolution; `docs/EAM_STATUS.md` conflicts too and is GENERATED, so it is
regenerated rather than applied at all. Restoring this is therefore no longer one command,
and it decays further the longer it waits.

**What each answer costs.** Bring it back: one small PR, bookkeeping only, no data file and
no reader-facing byte changes, and it collides with nothing — the manager has spent the last
hour in Illinois, Wisconsin and Iowa. Leave it out: three geometry files go on shipping with
no monthly source check, so a publisher that moves or withdraws one is noticed by nobody, and
Michigan's M keeps resting on a count that includes them as unwatched. There is no third
state where the work exists and is not on main — a closed branch is not a holding place.

**Why this is a question rather than a push.** It is reviewed work I offered to restore and
was asked nothing about; re-pushing it unasked would make my own "I will not re-push without
your word" worthless, which is worth more than five hours of a monthly check. I would bring
it back.

**2026-09-22 — #1081 made the BUILDER accept a county slug present in the shipped county
fabric, and nothing made the PANEL able to place one. Which side closes the gap?** Not
blocking; `29f1388f` makes the mismatch honest rather than harmful, so Michigan's panel says
it could not check instead of claiming a clean spot. What is still missing is the better
answer for a reader.

What I measured. The panel places a county by fetching `data/app/<slug>-county-outline.json`.
Michigan ships none, so its 35 tagged counties cannot be placed and the panel falls to the
could-not-check wording. Counted across the fleet: il 98 tagged / 101 outlines, ny 5/5, ca
1/1, wi 72/72, ia 2/2, mi 35/0.

Two ways to close it, and they differ in kind.

1. **Michigan ships 35 single-county outline files.** What the gap-record skill already
   prescribes, and it turns Michigan's panel from "could not check" into "one recorded gap
   affects the spot you clicked". It also duplicates geometry this instance already ships —
   `state-counties.json` carries all 83 — and each file needs a worksheet `data_files` row, a
   service-worker list placement and a cache bump. 35 requests per first panel open either
   way; they would succeed rather than 404.

2. **The panel places a tagged county from the instance's own county fabric** when no
   per-county file exists. No duplicated geometry, and it fits every future instance that
   ships a whole-state fabric rather than per-county files — which is the shape #1081 already
   taught the builder to accept. The cost is real: the engine would need the fabric's URL and
   its name field as METRO config, and it would have to turn a county NAME into the slug a
   record carries, which means reproducing `slug_of` in JavaScript. A second reader of one
   question is where this fleet's recurring defect starts, so that variant should instead
   have the BUILDER write the county's own name into the record and the panel match on that.

**I would take 2 with the builder writing the name**, because it removes the second reader
rather than adding one, and because route 1 asks this instance to carry 35 files whose
contents are already in a file it ships. But it is a fleet engine change plus a record-shape
change, so it is yours. If the answer is 1, that is a day's work here and I will do it without
further discussion.


**2026-09-22 — `build_eam_status.py` reads a near-miss of its own question in two places.
Both are one-line fixes to a fleet gate and would move il, wi and ia, so neither is mine.**
Not blocking; Michigan passes MAINTAINED without either, by naming files in rows.

**(a) `WHEN` rejects the trigger form its own docstring allows.** The docstring says "a
cadence, or a trigger", and the regex accepts `any change` and `on a change`. It does not
accept `Whenever TIGERweb rolls a vintage`, which is `mi/WATCH.md`'s clearest trigger and the
one that governs the congressional district field — the field name rolled from `CD119` to
`CD120` and a query naming the old one now returns HTTP 400, so that row is load-bearing.
Adding `whenever` to the vocabulary would count it. The cost is that `whenever` also matches
vaguer prose ("whenever this looks stale", which `mi/WATCH.md` itself carries), so it would
accept a row that names no clock at all. A tighter form — `whenever <a named source> <verb>`
— cannot be written as a keyword list.

**(b) `watched_by` reads workflow text only, so a watcher that knows its subjects through a
script is invisible.** `mi-validate-sources.yml` runs monthly, opens a tracking issue on
WARN/FAIL, and covers 18 of Michigan's 21 app files — but the file list lives in
`mi/scripts/validate_sources.py`'s `PROVENANCE` table, not in the `.yml`, so the measure sees
a watcher naming nothing. The same is true of every instance's own `validate_sources.py`.
Following the workflow into the scripts it invokes would count them, and would raise wi's and
ia's MAINTAINED numbers without anybody writing a row. The cost is that it widens what counts
as a watcher by reading a second file, and it would let a script that merely MENTIONS a
filename pass as a watcher of it.

**I would take (b) and not (a)**, because (b) is the case where a real scheduled watcher
exists and the measure cannot see it, while (a) is a wording problem a row can fix in one
edit. But both change a bar Adam ruled on four days ago, so I have written rows instead and
left the gate alone.

**2026-09-22 — ~~Michigan cannot pass EXAMINED without a change to a shared gate. Which
one?~~ ANSWERED 2026-09-22: the manager took route 2 in #1081, and #1086 populated the
arrays over it. Michigan reads 83/83. The reasoning is kept below because route 1's cost —
35 files duplicating a subset of a file the instance already ships — is the argument any
future whole-state instance will need.**

What I measured. `build_eam_status.py`'s `gap_counties()` counts only each gap record's
`counties` array, and `build_coverage_gaps.py` refuses a slug with no
`data/app/<slug>-county-outline.json`. Illinois ships 101 of those files, Michigan ships
none, so Michigan's 26 gap records all carry an empty array and Michigan scores 48 of 83 no
matter how many blockers it records. Tagging one county fails validation today, tested.

Two ways out, and they differ in kind rather than in size.

1. **Michigan ships 35 single-county outline files.** Follows Illinois exactly, touches no
   shared code, and turns on the panel's where-you-clicked section for Michigan, which is
   dead today. It also duplicates geometry this instance already ships: `state-counties.json`
   carries all 83 counties, so the 35 files would be a second copy of a subset of it, each
   needing a worksheet `data_files` row, a service-worker list placement and a cache bump.

2. **`build_coverage_gaps.py` accepts a slug present in an instance's shipped county
   fabric**, not only one with its own outline file. One change to a fleet script, no
   duplicated geometry, and it fits any future instance that ships a whole-state fabric
   rather than per-county files. The cost is that it touches a gate four instances depend on,
   and Illinois's 101 files would then be one of two accepted shapes rather than the shape.

**I would take 2**, because 1 makes Michigan carry 35 files whose contents are already in a
file it ships, and the rule it satisfies — "the slug must name geometry that exists" — is
satisfied just as well by the fabric. But it is a shared gate and the manager's, not mine, so
I have not touched it. If the answer is 1, that is a day's work in this instance and I will
do it without further discussion.

Worth stating plainly: nothing about either option ships a county or names a commissioner.
This is about whether the fleet's own measurement can see work Michigan has already done.

**2026-09-19 — the western-UP bbox: is this worth a six-app change?** The Tasks table calls
it "no fix proposed" and `mi/WATCH.md` does propose one, so the row understates where this
stands. I have not started it, because the fix is larger than the symptom.

The symptom is four places — Ironwood, Houghton, Iron Mountain, Menominee — that the front door
hands to Wisconsin. They are not a tie-break failure: they sit WEST of Michigan's shipped bbox,
which is the county fabric clipped to `lng >= -87.60`, so Michigan is never offered them and no
coverage ring is ever consulted. Michigan's own app still answers there; `metro_bbox` is
untouched and full-state.

The clip exists because Michigan's county fabric is water-inclusive and the honest state bbox
runs to -90.42, containing Chicago's centre and Wisconsin's — which `validate_index.py`
hard-fails, by a rule that guards the nearest-centre tie-break the front door stopped using on
2026-09-04.

So the fix is two changes the WATCH row says to make together: relax that rule, and move the
IN-APP `metro-portal` ENGINE block onto the same coverage-ring test the front door now uses.
**That block is one copy spliced into all six instances**, and its `siblingMetroAt` is called
from `moveend`, so making it consult a ring means keeping the bbox pre-filter, resolving the
ring only for a contested point, and never letting a fetch block a pan. That is a design change
across six live apps to fix four places, and it is the kind of thing I put to you rather than
decide.

What is already measured: ring-based resolution answers all 37 probe places correctly, so the
ceiling is 0 misroutes. A smallest-bbox-AREA tie-break was measured and is NOT the fix — 7
wrong of 37, the same count as nearest-centre and wrong in different places.

**2026-09-21 — may a COUNTY's precinct map be the source for a CITY's ward boundary?**
This is what survives the ruling below, and it is a different question from the one I asked.
Not blocking; nothing waits on it.

Jackson is the only Michigan city where the route exists. Jackson County's own precinct
layer carries both a municipality column and a ward column, and they populate: City of
Jackson, 10 precincts across wards 1-6 at 1/2/2/2/1/2, which is exactly what the state's
2026 fabric independently records. So dissolving the county's precincts keeps the
two-witness structure this project relies on — the county draws it, the state checks it —
which is what distinguishes it from Wyoming and Muskegon, where the state fabric would have
been both source and check and the answer was no.

What it costs either way. Yes: Jackson's six wards ship from a publisher that is not the
city, and the precedent is open for any county that labels its precincts by ward, which on
today's measurements is Jackson alone. No: Jackson stays a recorded gap and the city's six
per-ward pages remain a roster source only. I would take yes, because the second witness
survives it and that was the whole basis of the ruling below. It costs no fetches to answer.

**2026-09-19 — may the state's precinct fabric be the SOURCE for a city's wards,
or only the check? ANSWERED 2026-09-21: only the check.** This is the decision under most of
the remaining ward gaps, it is recorded twice in this repo as the operator's call, and nobody
has been asked. It costs no fetches to answer.

*Answered by the manager session on 2026-09-21 under the standing authority Adam granted it:
the state's fabric may serve only as an independent currency check on a city-published ward
boundary, never as the source, because a state precinct tiling is drawn for running elections,
carries no statement by the city about its own boundary, and aggregates to a ward only where
the city's lines happen to nest. Recorded in `mi/WATCH.md` and in the Wyoming and Muskegon gap
records (#1069). The question as I wrote it was too broad — see the Jackson question above.*

**Correcting my own note above.** I wrote that I was starting on (2) because
`mi/WATCH.md` line 30's WARD query "needs no answer". That query is already spent — it was
run on 2026-09-06 and settled 23 cities in one go. Nothing on the ward front is one cheap
query away any more, and the four unshipped cities I checked (Kentwood, Midland, Holland,
Muskegon) each carry a measured record saying neither the city nor its county publishes a
ward boundary this app can read. The remaining ward work is either per-city discovery, which
costs fetches exactly like option (1) above, or this posture question.

What is true today. Michigan's own 2026 precinct layer carries a WARD column. Six cities
ship a ward polygon — Detroit, Warren, Grand Rapids, Flint, Rochester Hills, Battle Creek —
and every one of them takes its boundary from the CITY's own publisher, with the state's
column used as an INDEPENDENT currency check. That check is what separated Flint's plan in
force from two superseded ones by twenty-three points, and what refused Bay City.

Of the ten cities the state's column calls districted, eight have no ward polygon here:
Wyoming, Pontiac, Kentwood, Midland, Muskegon, Jackson, Bay City, Holland. The state's
fabric could draw wards for all eight without fetching any of those cities. Wyoming's is
already measured — it dissolves to 6/6/6 across three wards — and the other seven are one
query away.

What it costs, stated plainly. The currency check stops being independent: today the city
draws the boundary and the state checks it, and under this posture the state is both, so a
ward this app draws could never again be shown to disagree with the city that elects by it.
Two cities make that concrete. Bay City publishes its own nine-ward layer and it scores
97.608% against the state fabric with the disagreement spread across twelve ward pairs —
two plans, not one bad edge — so drawing from the state means overriding a city's own map
rather than filling a silence. Muskegon's only published map leaves parts of the city
uncovered, so there the state route fills a real hole. Those are different situations and I
would not answer them the same way.

One more consequence worth knowing before deciding: it would sidestep Lansing's licence
block. Lansing's wards are built and unshipped because the only clean copy states no licence
while the same plan one item away states CC BY-NC 4.0, and the operative reading is NC. The
state's fabric is a different publisher under different terms, and Lansing already measures
99.893% against its WARD column. That is a reason to be careful rather than pleased —
routing around a licence by changing publishers is a decision, not a workaround, and it
should be made on purpose.

Nothing ships either way without the usual per-city build and its gates. The question is
only whether the state may be the source.

**2026-09-19, update — (3) is done and it changed what (1) costs.** #1045
records the accepted host's robots reading and gates on it. The backfill read
33 robots.txt across 24 hosts and found **two of the 25 shut counties shut by
POLICY rather than by an absent page**: `www.iosco.org` answers HTTP 403 on
robots.txt, which the strict reading a county website gets makes a refusal, and
`tuscolacounty.com` serves a 26-byte file that disallows this client. So a
re-examination under (1) is **23 counties, not 25** — Iosco and Tuscola may not
be fetched at all now, whatever budget is set. The question below is otherwise
unchanged, and unanswered.

**2026-09-21 correction — that arithmetic describes the probe's record and not the
remainder.** 48 counties ship, so **35 do not name your commissioner**, and they are 25 in
the probe's artifact plus 10 in `PROBES`. Everything above about (1) is true of the 25 and
silent about the 10, which is the more useful half to state: Genesee, Ingham, Gogebic and
Marquette each disallow this client in robots.txt and may not be fetched at any budget, like
Iosco and Tuscola; Ottawa and Livingston answer 202 on robots.txt itself, which is an access
control; Oakland and Allegan are refused at their own edge to both the districtry token and
a browser string, so nothing is left to try; Washtenaw and Bay answer 200 and are not
keyable, which is a parser question rather than a budget one. **So a fetch budget reaches 23
of the 35.** Six of the remaining twelve are shut by policy, two by an edge that refuses
every client, and two need a reader rather than a request. None of that changes the question
below; it states what a yes would and would not buy.

Starting on (2) in the meantime: `mi/WATCH.md` line 30's WARD query is one
request against a service this instance already reads, and it needs no answer.

**2026-09-19 — the commissioner candidate list is empty. Which work comes
next?** Not blocking: I am starting on (3) below, which needs no answer and is
the recorded prerequisite for anything that sweeps again.

What I measured. 48 of Michigan's 83 counties name their commissioners. The
probe's record now holds ZERO candidates and 25 counties measured shut: 11
no-board-page, 7 no-districts, 3 not-keyable, 2 no-confirmed-host, 2 challenge.
23 of the 25 carry a confirmed host; Shiawassee and Montmorency carry none.

Three things could come next and they cost very different amounts.

1. **Re-examine the 25 shut counties.** The largest bucket is the 11 with a
   confirmed host and no board page found from the sitemap or the front page,
   which is the shape Washtenaw turned out to be (the real board page sat on a
   different host spelling) and the shape Illinois's Vermilion turned out to be
   (the county's GIS was a different publisher from the county's website). So
   this is the one most likely to yield. It is also the most expensive: these
   hosts have been swept three to six times already, and that is what tripped
   a WAF on Tuscola. **The question I would want settled before starting is
   what a re-examination may fetch** — my own proposal is at most one request
   per county, to a URL the existing record does not already name, and nothing
   at all to a host recorded as a challenge.

2. **City council wards, 18 of the 20 recorded Michigan gaps.** Already on the
   manager's Tasks table. `mi/WATCH.md` line 30 says to run the state's WARD
   column first, which is ONE query against a service this instance already
   reads, and it settled 23 cities on 2026-09-06. So it is the cheapest of the
   three by traffic and the largest by gap count.

3. **The probe's own robots gap.** `probe_mi_county_boards.py` records a robots
   verdict for every host it REJECTS and none for the one it ACCEPTS, which is
   why the Gogebic/Marquette disagreement (candidate on 09-18, `Disallow: /` on
   09-19) could not be settled. Writing the field costs no fetches. Backfilling
   the 23 recorded hosts costs one robots.txt read each and nothing else —
   robots.txt is the request every client makes first — and it only makes
   FUTURE readings comparable, since the 09-18 readings are already lost.

**What I would pick, in order: 3, then 2, then 1.** 3 costs nothing and every
further sweep is worth less without it. 2 is one query for the biggest gap
count. 1 is the most likely to yield a county and the only one whose budget I
would want stated rather than assumed.
