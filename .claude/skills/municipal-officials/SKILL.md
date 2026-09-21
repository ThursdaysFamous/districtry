---
name: municipal-officials
description: Add or repair an ILLINOIS county's municipal governing-body roster — choose the source by the five-rung ladder, measure the fetch class with the client the scraper will use, write the per-county scraper with the settled record shape and three floors, register it in the builder's four tables, wire its three workflow edits with preservation, and join any suburban ward polygons to the ward layer. Use it for "add Kankakee's municipal officials", "the clerk sent a yearbook PDF, wire it in", "the DuPage scraper 403'd again — preserve it or add a Playwright rung?", "what floors for a new county in municipal-officials.json", "why is Freeport missing from Stephenson's roster", "Peru published ward polygons, add its seats", "close the hamilton-municipal-officials gap". Illinois only: Wisconsin has no builder in this shape and Iowa's cities are its own tier. Not for a county BOARD roster (county-n-plus-1), a red bot PR (steward), or a plain who-is-the-mayor question.
---

# A county's municipalities

`docs/EXPANSION_GUIDE.md` §3.4 is five hundred lines of rule interleaved with
the anecdote that earned it, which is the right record and the wrong thing to
read at task time. `CLAUDE.md` carries the scraper → builder → bot-PR pattern,
the retention gate's file-level treatment of this file, and the link gate's
WARN cap on village URLs. This is the thirteen steps in order, with the
current names, for a pipeline repeated for every county in `COUNTY_FIPS`
without changing shape. What changes per county is the source and the
numbers, and those live in code this points at.

## 1. Source — the five-rung ladder, in order; take the first hit

1. The county clerk's elected-officials database or API — look for an XHR/JSON backend before settling for a PDF (Cook's DOEO class).
2. The clerk's directory or yearbook document. READ IT BEFORE ASSUMING ITS DEPTH: "mayor-level" yearbooks have carried whole boards.
3. A council-of-governments or mayors-conference directory (DMMC class).
4. County GIS municipal-boundary contact attributes (Lake class → a contact-only card).
5. Link-only — the rule-4 floor.

Never scrape N heterogeneous municipal sites as a default. Statewide
aggregators (IML, the Comptroller's CEO, Google Civic) are a verified dead
end. Before writing an HTML parser for a city CMS, check
`/wp-json/wp/v2/types` and the page source for `application/ld+json`. Record
the outcome in `docs/DATA_LAYER_GUIDEBOOK.md` either way; a no-source outcome
becomes a `<county>-municipal-officials` gap id in the gaps block.

## 2. Measure the fetch class with the client the scraper will actually use

A successful `curl` proves nothing about `requests` — the Akamai counties
fingerprint the HTTP client. Classify the response by §3.4's block-taxonomy
table (a Cloudflare challenge → a Playwright rung exists; a network deny → a
browser rung only if a challenge sits underneath; an Akamai hard WAF deny →
nothing beats it, record it, keep the rungs so the source resumes on its own,
let preservation carry the data; a SiteGround reputation score → change the
CALLER, never the retry count); the table carries the measured header and
body-size signatures. Do not widen `WAYBACK_MAX_AGE_DAYS` — the
Archive-snapshot age guard each wayback-rung scraper carries — for one source.
The engine ladder is written PER SCRAPER on the four-rung model of
`scripts/mchenry_municipal_officials_scraper.py --engine auto|requests|playwright|wayback`
(Kendall and DuPage carry the same); `scripts/cook_municipal_officials_scraper.py`
is the three-rung JSON-API shape with no Archive rung. From
`scripts/scraper_common.py` reuse `fetch()` for the paced `requests` rung and
`make_fail()` for the failure voice — `fetch()` is one paced GET, never a
ladder — and import the UA constant the sibling with the same fetch class
already sends: the constants pin definitions, not a fleet value, because
several sites key on the exact string.

## 3. Discover, never hardcode, a year-stamped document URL

A year-versioned URL is a scraper with an expiry date. Read the link from the
page that links it. On Revize sites the discovered link is RELATIVE and
resolving it against the page 404s as a 200-shaped HTML page: try
`<cdn-root>/<filename>` first, page-relative second, and require actual
`%PDF` bytes. Match section headings anchored `^…$` (an index with dot leaders
repeats them) and bound a section by the next STRUCTURAL marker, measured
before adopted.

## 4. Write `scripts/<county>_municipal_officials_scraper.py`

It takes `--out` (a document-sourced county also takes `--pdf` for an
archived or local copy; the workflow line must match the scraper's own CLI)
and emits per-county records the builder resolves. Inherit the shape: keys
omitted where the source names nobody; `head`, `board` and `officers` stay
separate so a mayor-level county ships `head` with no `board`; contact is
MUNICIPALITY-level under `office` unless the source publishes it per member,
and a per-person value equal to the hall line is dropped; Library Trustees
are excluded; capture per-member `district` from day one even with no ward
geometry — that is what makes the ward tier free later. Parse PDFs with a
layout-preserving reader (`pypdf` layout mode, `pdfplumber`), never flattened
text; substring headers longest-first, since `\b` fails silently; "At Large"
labels a group; `(IND)` is a party code; an undelimitable address returns
nothing.

**Flags and labels.** `appointed: true` ONLY where the source says so — an
appointed OFFICE and an elected office held by an APPOINTEE both need it.
Where the source marks nothing, the SCRAPER carries its own `APPOINTED_TITLES`
set (LaSalle's, Henry's, Livingston's are the models —
`scripts/lasalle_municipal_officials_scraper.py`) and sets the flag on the
record; the builder only copies it. Term facts ride the person under the
label the source uses — `nextElection`, `termExpires`, `lastElected` — never
normalised into one field, and a future-tense fact already past is not
rendered. Carry the form of government as the source labels it ("Village of
Alsip"); a bare name takes the Census designation, never an invented one, and
a stated form is never downgraded.

## 5. The name → GEOID join

Key by the 7-digit place GEOID via
`il/data/source/st17_il_place_by_county2020.txt`. Use the builder's
`norm_place()` (strips a PREFIX form-word, the clerk's side) and
`norm_census_place()` (strips a SUFFIX, the Census side) — one normaliser that
strips both ends reduced "City of Calumet City" to CALUMET and "Rock City" to
ROCK. A source misspelling gets an explicit, reviewable alias: a PLACE name may
be corrected to join; a PERSON's name never. Every lookup is county-qualified
or refuses an ambiguous name (two Wilmingtons, two Windsors); a ward number can
identify two people, so a seat lookup returns all holders. Run the join over
the county's FULL place list before shipping — a wrong match is silent.

## 6. Drop classes — every one reported

Placeholders in the name column (`VACANT_NAMES`) never reach a card. A
separate body printed alongside (a zoning board, a village police list) is
dropped. A combined title ("Trustee/Zoning Chairperson") reduces to the
municipal seat it names; only a title reducing to nothing is dropped. One
person printed as both Village President and Trustee: the head row wins, the
board row is dropped with a log line, and the one-seat shortfall is RECORDED
as a gap, not absorbed. Never blend a physical and a mailing address —
combine lines only within a labelled group, prefer physical, leave city empty
rather than borrow; anchor ZIPs with the +4 optional. The group-heading
vocabulary is never finished: warn on an unmatched candidate heading, or
assert every municipality yielded a board.

## 7. Floors — three per county, each a deliberate under-tolerance

`municipalities`, `members`, `heads` — as `MIN_*` in the scraper and a
`COUNTY_FLOORS` entry in `scripts/build_municipal_officials_roster.py`, where
the current values live (the guide's list is stale). A head-level county's
member floor sits ABOVE its head count; a head floor may sit BELOW the
municipality count only with the municipality and the reason written beside
the number; a small county gets a TIGHT floor; a contact-only county's member
and head floors are 0 by design. A count floor cannot see a swap: read the
built file back grouped (`collections.Counter` over board sizes per
municipality, eyes on the extremes) before shipping.

## 8. Register in the builder — four tables, and they must agree

Add the county to `COUNTY_FIPS`, `COUNTY_FLOORS`, `PRESERVABLE` and
`COUNTY_PRECEDENCE` in `scripts/build_municipal_officials_roster.py`, with its
precedence reason written where the existing pairs write theirs. Audit all
four before shipping — Tazewell sat in two of the four (`PRESERVABLE` and
`COUNTY_PRECEDENCE`) with no floors and a statewide-only GEOID lookup. NEVER
add a county to `REQUIRED_COUNTIES` (**Cook only** since #1043; Will was in
it and moved to `PRESERVABLE` when its directory went behind a managed
challenge): a source is non-preservable only when building without it would
silently ship mayors where councils belong. Precedence is `pick_entry` in the
builder — override > depth > county order (§3.4 "Merge & precedence"): run the build and read
every `NOTE: … is listed by both` line, because a straddling municipality the
new county wins or loses at equal depth is a decision; a one-town exception
goes in `PLACE_SOURCE_OVERRIDE` with its mandatory reason, never by
reordering the list. A city payload enters through `--enrich` and can only
FILL fields the county left empty or INSERT a municipality the county omitted
wholesale; an unmatched name is logged, two possible matches refuse.

```bash
python3 scripts/<county>_municipal_officials_scraper.py --out /tmp/<county>.json
python3 scripts/build_municipal_officials_roster.py <every county's output> \
    [--enrich <city payloads>] \
    [--preserve il/data/app/municipal-officials.json --preserved <source ids>]
```

The builder rewrites the whole file from the inputs it is given, so pass
every county that should ship. `--preserve` may name the shipped file
directly in one invocation (the builder reads it before writing); the
workflow copies it to `/tmp` first — do not "fix" either to match the other.
Preservation is stated, never silent: the build prints `PRESERVED` lines and
the workflow lifts them into the PR body.

## 9. Post-build checks, every county

Compare the scraped municipality list against the county's Census place list
— a missing entry is invisible in the output, and the omission can be the
COUNTY SEAT and deliberate (Will lost Lockport and Wilmington to a PDF text
layer; Stephenson's "City and Villages" page lists no city). Never infer
coverage from a page's apparent completeness; a source's title is a claim
about its scope. Check the central city has a card — its council already has
a layer, so it is the municipality most likely to be skipped. Heed the
builder's warning against `municipal-ward-coverage.json`: ward geometry with
no districted seat in the roster means one side is stale, and the
MUNICIPALITY's own site is the tiebreaker. Re-test a recorded "unbuildable"
before believing it — a non-build record is a snapshot of what was tried.

## 10. Wire the workflow — three edits, each named

In `.github/workflows/update-municipal-officials.yml`:

1. **The scrape step**: `id: scrape_<county>`, `continue-on-error: true`.
2. **The TRACK step** ("Track a blocked or broken source"): its `outcome` in that step's `if:` list, a `<COUNTY>_OUTCOME` env entry, AND a `raise_issue "<County>"` line — all three, or a failure files nothing (the workflow's own comments record Tazewell and Mason reaching that state).
3. **The BUILD step**: one `add "${{ steps.scrape_<county>.outcome }}" <preserve-id> county /tmp/<county>_municipal_officials.json` line, where `<preserve-id>` is the `PRESERVABLE` key — that line is what turns a failed scrape into `--preserved <id>`. The build step's OWN `if:` stays **Cook-only** (`steps.scrape_cook.outcome == 'success'`); never gate a multi-source build on every source succeeding — rule 4's terminal case guarantees some will block permanently.

Read `steps.<id>.outcome`, never the jobs API's `conclusion`, which reports a
swallowed failure as success. Akamai counties need Playwright as the day-one
rung, which is why the workflow installs Chromium. If the scraper imports
anything not on the workflow's single `pip install` line, add it there
(constrained by `scripts/requirements.txt`) or import it inside the function
that needs it — `python3 scripts/validate_workflow_deps.py` is the gate. The
workflow already regenerates the history page, runs `validate_index.py`, and
gates its PR on the data diff — do not add a second copy of any of those.

## 11. The ward tier

A new ward city is three edits, then the build: a `municipalWardEntry` row in
the `ward` dispatch table in `il/index.html` (Cook GIS's Municipal Ward layer
and Will GIS's `Ward_Districts` are the loader models); an entry in BOTH
`STATIC_ENTRY_MUNICIPALITIES` and `ENTRY_COUNTY_FIPS` in
`scripts/build_municipal_ward_coverage.py` (a name that exists twice in
Illinois refuses without the county); then
`python3 scripts/build_municipal_ward_coverage.py` — and check the new
municipality is in the printed per-entry counts, because an entry missing
from the tables is dropped silently. Seat-holders join by municipality plus
seat number; per-seat contact renders ONLY where a source carries it per
member. The bounded rung-5 exception — scraping a city's own site — has four
shipped shapes and no fifth: per-seat contact for ward cities (Will's cities,
Joliet); a municipality the county omits wholesale (Freeport); a county with
no municipal source at all (Galesburg); a districting the county feed does
not carry (Skokie). Each is a bounded payload keyed to named places in
`PRESERVABLE`, never a sweep.

## 12. App side, only if the data widens what a section can hold

The officers heading is `municipalOfficersLabel()` (none appointed → Other
Elected Officials; all → Appointed Officials; mixed → Other Officials) — a
fixed heading over new record kinds is an unreviewed claim. A fact on two
cards gets ONE render helper (`municipalTermNote()`). Sort each field as the
SEAT's or the PERSON's before joining two sources; it usually removes the
need for a fuzzy name match.

## 13. Verify and close

A point sweep per depth class — full council, mayor-level, contact-only,
identity-only, unincorporated-empty — plus one independent cross-check of a
parsed council against the city's own published roster (§3.6). If the county
changes what `municipal-officials.json` must carry, edit the
`data_files.rosters` entry for it in `metro-worksheet.json` (`min_keys` +
`note`) and run `python3 scripts/generate_metro_files.py` — the floor in
`scripts/validate_index.py` is a GENERATED region and is never hand-edited
(adding a county rarely moves it). Regenerate `docs/COUNTY_STATUS.md`; record
the county's posture and any gap in the guidebook; then the steward battery
and a PR.

## 14. Nevers this file adds

- Never add a county to `REQUIRED_COUNTIES`; never register it in fewer than the four builder tables.
- Never hardcode a year-stamped document URL.
- Never correct a person's name to make a join; never blend two labelled addresses; never blend member lists from two sources.
- Never mark `appointed` where neither the source nor the scraper's `APPOINTED_TITLES` says so, and never exclude an appointee.
- Never gate the build on every source; never read the jobs API's `conclusion` as the truth about a scrape.
- Never infer a county seat is present because the page looked complete.
