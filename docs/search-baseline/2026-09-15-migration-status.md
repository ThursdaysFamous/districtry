# Migration status, 2026-09-15 — SEO audit phase 0

**What this is.** The SEO audit of 15 Sep 2026 opens with a phase 0 of five items, four of
them about the domain move rather than about the site. This file records what each one's
state actually is, measured on the day, and what now watches the two that are ongoing
commitments rather than one-off actions.

**Why it is committed.** Phase 0's two live items — keep the old domain forwarding, and hold
rewrites on the pages its traffic lands on — are commitments with no natural end date and no
artifact. Written only in an audit they would be forgotten the first time somebody edited
`/il/`. One is now a monthly check; the other is written here and printed by that check every
run, because a hold nobody can see is a hold nobody keeps.

## The five items

| # | Item | State on 2026-09-15 |
|---|---|---|
| 1 | Search Console access via the service account | Done before this audit. `scripts/gsc_fetch.py` reads it daily. |
| 2 | Change of Address (24 Aug) + path forwarding on all three old domains | Done. Re-measured below. |
| 3 | Keep chidistricts.com registered and forwarding ≥ 1 year | **Already satisfied by nearly three.** Registered to 2029-07-10, 1,028 days out, read from Verisign RDAP. Now checked monthly. |
| 4 | Request indexing for `/il/ward.html` | Requested by the operator. Nothing on this side was blocking it — evidence below. |
| 5 | Hold large rewrites on redirect targets | Standing. The three pages and the condition that lifts the hold are below. |

## The redirect map, re-measured

Every old URL Google had indexed **with impressions** before the move (the table in
`2026-08-24-chidistricts-gsc.md`), followed to its final status:

| Old URL | Hops | Final | Status |
|---|---|---|---|
| `chidistricts.com/` | 2 | `districtry.com/il/` | 200 |
| `chidistricts.com/school-board.html` | 1 | `districtry.com/il/school-board.html` | 200 |
| `chidistricts.com/police-district.html` | 1 | `districtry.com/il/police-district.html` | 200 |
| `chidistricts.com/sources.html` | 1 | `districtry.com/il/sources.html` | 200 |
| `chidistricts.com/county-board.html` | 1 | `districtry.com/il/county-board.html` | 200 |
| `nyc.chidistricts.com/` | 2 | `districtry.com/ny/` | 200 |
| `sf.chidistricts.com/` | 2 | `districtry.com/ca/` | 200 |

Seven of seven. **One row corrects the baseline document**, which maps
`chidistricts.com/county-board.html` to the ROOT `/county-board.html` stub: the registrar
forwards it straight to `/il/county-board.html`, the real page rather than a meta-refresh
shell. Better than documented, so the measurement is what the check asserts.

The forwarding is a path-preserving wildcard, not a per-URL list — an unlisted old path
lands on `/il/<path>` and 404s there if no such page exists. So the check's seven rows are a
sample of a general rule rather than the whole of it.

Query strings are dropped by the forwarding (`?utm_source=share` does not survive); fragments
like `#point=` do, because they never reach the server. The audit files that as Low with no
fix, and it is a Squarespace path-forwarding constraint rather than something this repo sets.

## Why `/il/ward.html` was "unknown", and what it was not

Google reported the URL unknown. Everything this side controls was already correct on
2026-09-15:

- serves **HTTP 200**, 36,614 bytes;
- declares `<meta name="robots" content="index, follow">` and a canonical naming itself;
- is in `sitemap.xml` with `lastmod` 2026-09-12, submitted 13 Sep;
- is linked from **seven** Illinois pages, and the link on `/il/` — an indexed page — is in
  the **served markup**, not injected by script, so it is reachable by crawl as well as by
  sitemap.

So the gap is Google's crawl backlog, and Request Indexing was the only available lever. The
audit's other suggestion — homepage links — is real but is phase 1: the fleet landing page
links none of the eleven question pages.

## Standing: pages held from rewrite

These are 301 **targets** of old URLs that still earn impressions. Rewriting one while Google
is still deciding whether the redirect source and the target are the same page throws away
the signal the move exists to transfer.

| Page | Held because |
|---|---|
| `districtry.com/il/` | `chidistricts.com/` — 50 clicks, 1,245 impressions pre-move |
| `districtry.com/il/school-board.html` | `chidistricts.com/school-board.html` — 65 impressions |
| `districtry.com/il/police-district.html` | `chidistricts.com/police-district.html` — 37 impressions |

**What lifts the hold:** the new URL earning impressions of its own in the districtry.com
property. `data/search-performance.json` carries per-page rows and is refreshed daily, so
this is measurable rather than a judgement call. Small changes — a title, a link, a date —
are not what this holds; it holds restructuring and rewriting.

The audit's staged title plan follows the same logic: place-first titles on `/ca/`, `/wi/`,
`/ia/` and `/mi/` now, `/il/` after the migration settles, and `/ny/` last because it earns
8 of the site's 13 clicks.

## What watches this now

`scripts/check_legacy_redirects.py`, monthly, inside
`.github/workflows/validate-sources.yml` — the same run that already checks dataset freshness
and card links, folding all three into one tracking issue. It asserts every row of the
redirect map above still lands, warns when the registration falls inside a year, and prints
the held pages every run so the hold stays visible while it lasts. It never edits anything.

Run it by hand with `python3 scripts/check_legacy_redirects.py`, or `--offline` to list the
surface without touching the network.

## Phase 1, item by item

### 1. Place names in every title and H1 — done 2026-09-15

Six pages were headed `Common questions` and six `Sources & Data Layers`, and four map
titles named no place. All twelve H1s now carry the instance's `landing_name`, and the four
staged map titles read `<Place> district lookup — districtry <Place>`.

`/il/` and `/ny/` map titles stay staged, per the hold above.

`il/faq.html` keeps its `<title>` and body `<h2>` naming Chicago while its H1 now names
Illinois. Both are true of that instance and neither is duplicated across the fleet, so the
audit's finding does not reach them; changing an indexed title was not in this change's
scope. It is worth deciding separately — the page answers for 92 counties.

### 2. Address box on every question page — done 2026-09-15

All eleven question pages (`il/ward.html`, `il/county-board.html`, `il/precinct.html`,
`il/school-board.html`, `il/police-district.html`, `ny/council-district.html`,
`ny/community-board.html`, `ca/supervisor-district.html`, `wi/county-board.html`,
`ia/county-supervisor.html`, `mi/county-commissioner.html`) now carry an address field above
their existing link. Generated by `scripts/build_question_forms.py`, `--check` in CI.

It does not geocode. It builds `./#q=<address>` and the app runs its own bounded search —
so no question page contacts a third party, and the address rides the hash, where
GoatCounter's `count.js` cannot send it. The app selects a result only when the geocoder
returns exactly one.

`il/school-board.html` and `il/police-district.html` are on the hold list and got the box
anyway. The hold is on restructuring and rewriting; this adds a field above an existing link
and changes no prose. Said here so the decision is on the record rather than implied.

### 3. Static officeholder tables — two of three, 2026-09-15

`ny/council-district.html` and `ca/supervisor-district.html` now carry a dated table of all
51 Council Members and all 11 Supervisors, `Person` markup per row, generated by
`scripts/build_officeholder_tables.py` (`--check` in CI). Measured that day, those 62 names
appeared in no served byte of this site; both rosters had shipped as `data/app` files for
months and nothing was missing except the table.

The two weekly roster workflows now regenerate the page in the same run, and the gate FAILS
a workflow that does not — otherwise the failure lands on the bot's own PR.

**Chicago's 50 alderpeople took a roster pipeline first**, built the same day.
`il/index.html` fetches Socrata `htai-wnw4` live on first toggle, so there was no file for a
page to read at all. `scripts/chicago_ward_scraper.py` + `build_chicago_ward_roster.py` make
one weekly (`update-chicago-ward-roster.yml`, Tue 23:00 UTC, opening a PR), and
`/il/ward.html` now names all 50 in its HTML — the page phase 0 asked Google to re-index, and
Chicago wards are the site's largest search term.

**The roster is in `il/data/source/`, not `il/data/app/`, and a gate is why.**
`validate_index.py` requires every file in an instance's `data/app` to be referenced by its
`index.html`, and this one is not: the card still calls Socrata. That gate is right, so the
file sits with the other build-time inputs and is served to nobody. The day the card moves
onto the file it moves to `data/app`, gains a worksheet entry and a network-first `sw.js`
line, and the gate passes.

The card staying live also decided a sentence on the page. "The map above reads the same
roster" is true of NYC and SF, whose rosters the app serves, and false of Chicago, where the
two can differ by up to a week. The generator reads the roster's own path and prints whichever
sentence is true.

### 4. Verified dates and `dateModified` — measured, not built

Measured 2026-09-15: **no page on this site carries `dateModified`**, and 3 of the 75
Illinois county board pages print a visible verified date (`alexander`, `edwards`, `wabash`
— the three whose at-large records carry a `verified` field the others do not).

The obvious implementation does not work, and the reason is worth writing down before
someone tries it. A county page's date should be its roster's, and git can supply that:
`git log -1 --format=%cs -- <roster>`, the same call `build_sitemap.py` already makes for
`lastmod`. But the weekly roster jobs open a PR and **this repo squash-merges**, which
rewrites the committer date to the merge day. A job that runs Monday writes Monday into the
page and commits both files together; the squash lands Wednesday; from then on git says the
roster last changed Wednesday while the page says Monday, and `build_county_pages.py --check`
fails on `main` for every roster PR that did not merge the day it opened.

`build_sitemap.py` survives this only because its check tolerates a day of staleness. A
printed date is a claim to a reader, and a day of tolerance is not a thing to give it.

So the date has to live in the data, not in git: a roster stamps when it was read, and the
page prints that. Wisconsin's `county-board-members.json` already carries `asOf` on 183
records. Illinois's 75 do not, and stamping them means touching the builders behind 60 weekly
workflows — which is the real size of this item, and why it is recorded here rather than
half-done.

The guide pages (faq, sources, the question pages, history) are a separable and much smaller
piece: their date is the instance's own `verified_date`, a human-set worksheet value with no
chicken-and-egg at all. Their `ld+json` is hand-written, so it needs an injector and a drift
gate — about 31 pages.

### Still open

- **`dateModified` on the guide pages** from each worksheet's `verified_date`. Small.
- **`asOf` stamps on the county rosters**, and the dates on the 170 county pages that follow.
  Large: it reaches the builders behind 60 weekly workflows.


## Phase 2

### 1. State legislator and congressional pages — done 2026-09-15

Twelve pages, two per instance: `<tag>/state-legislature.html` and
`<tag>/congress.html`, generated by `scripts/build_legislator_pages.py`
(`--check` in CI). They name 1,058 officeholders — every member of all six
states' two chambers and their U.S. House delegations — none of whom appeared
in any served byte of this site, on a site with no page at all for "who is my
state representative" or "who is my congressman".

The generator owns the head, the prose and the structure and preserves the four
regions other generators fill, so all four `--check`s stay order-independent.
No seat count is stated: every count is `len(roster)` at build time.

Twelve weekly workflows rewrite one of the eighteen rosters; each now
regenerates its page and the sitemap in the same run, gated.

### 2. Cook County roster — done 2026-09-15

`il/county-board/cook.html` returned 404 while the Illinois hub's own prose
named Cook. The cause was not a missing page but a missing roster: the app
fetches the county's GIS people table live, and `build_county_pages.py`
enumerates roster FILES.

Two other sources were measured and rejected — the county website publishes no
machine-readable members list, and the open-data portal's commissioner dataset
seats a member who died in 2018. The GIS table is maintained; one column in it
is not, so no term or election date is carried.

`scripts/cook_county_board_scraper.py` + `build_cook_county_board.py` write the
roster weekly; 17 districts plus the Board President.

### 3. NYC police precinct page — done 2026-09-15

`ny/police-precinct.html`. The audit measured about 60 impressions at positions
7–9 across "find my precinct" and roughly 25 variants, 0 clicks, every one of
them landing on `/ny/` — a page that answers the question among twenty-seven
others and never says the word in a heading.

The page carries the address box, a section on what the card shows, one on how a
precinct, a sector and a station house differ, and a generated table of all 78
commanding officers. No precinct count is written into the prose; the table's
own sentence is the only place a number appears and it is `len(roster)`.

Three changes to `build_officeholder_tables.py`, each of them the smallest thing
that made this roster fit:

- **`name_field`.** `nypd-precinct-info.json` names the person in `commander`.
  Nothing mechanical says which key on a record holds a person, so it is stated
  per section the way `seat` and `holder` already are, defaulting to `name`.
- **`unit` and `prep`.** The lede read "All N seats on <body>", which is right
  for the eleven entries whose holders are elected and wrong for the one whose
  holders are appointed. Both words are stated, with the elected reading as the
  default. The same sentence's "where the roster does not name a seat" became
  "where the roster names nobody", which needed no variant at all.
- **A derived citation column.** Each of the 78 commanders comes from that
  precinct's own NYPD page, and the 78 links are 78 different pages, so the
  column exists where every named record carries `source_url` — measured
  2026-09-15, that is this roster and no other the tables read. Deliberately not
  keyed on `url`, which nine legislature rosters carry as the member's own
  official page; adding a column to those tables is a different decision. The
  cell carries no `itemprop`: it sits inside the row's Person scope, and the
  precinct's page is a citation for the row rather than a property of the
  person.

`check_workflows()` caught the missing half before it shipped, which is what it
was written for: it failed the build naming `ny-update-nypd-roster.yml` and the
two lines it lacked. That workflow now regenerates the page and the sitemap.

### 4. The other missing large counties — done 2026-09-15

Seven, not six, and one gap rather than seven. The audit named Winnebago,
Madison, St. Clair, Champaign, McLean and Kankakee; measured against
`il/index.html`'s own board cards, Champaign has no card at all (it is inside
the unserved Champaign/Ford/Piatt enclave) and Effingham and Whiteside were
missing too. The seven with a card and no page are Effingham, Kankakee, Madison,
McLean, St. Clair, Whiteside and Winnebago — 158 seats.

**None of them was missing a source.** Each publishes its members on the SAME
GIS feature that carries the board boundary, so the app asks for both in one
request and no roster file ever existed — and `build_county_pages.py` enumerates
roster FILES. That is the Cook County shape exactly, and the fix is the same:
snapshot what the app fetches, weekly, into `il/data/source/`.

The earlier note here about Winnebago was half right and half wrong. Its roster
does ship 20 districts with an e-mail and a phone and no `name`, and deriving a
name from `ABooker@` is a guess this project does not make — but the name was
never missing. `build_winnebago_county_board_roster.py` reads it from WinGIS to
cross-check the board page and then deliberately drops it, because the card gets
it from WinGIS live. The county page now takes the same GIS name, so the two
cannot disagree.

Four things the build decided, each of them a property of a county's own
service rather than a preference:

- **Four record shapes.** One seat per row for five counties; two seats in
  parallel COLUMNS for McLean (`REPNAME`/`REPNAME2`, a seat with no name being a
  vacancy that drops out, the app's own rule); nine names in ONE
  comma-separated string for Whiteside; and a layer holding every office's
  districts in one table, filtered exactly as `whitesideIsBoardFeature` filters
  it.
- **Whiteside's split is guarded.** Nine names in one field split on commas
  because no member's name contains one. St. Clair's own roster carries "Robert
  Allen, Jr.", so that day is coming; a fragment that is a bare suffix now fails
  the build naming the county rather than shipping half-people.
- **A link that names the county is dropped.** Whiteside's `districturl1` is the
  same board page on all three rows, so it is the file's `sourceUrl` and rides
  no member — the rule `build_cook_county_board.py` states for `url1`.
- **A gate that asks what the page generator cannot.** `--check` reads
  `il/index.html`'s own board-card titles and FAILS on a county that has one,
  has no roster file, and is neither snapshotted nor recorded with a reason. One
  is recorded: Christian, whose site has answered every client with a Cloudflare
  managed challenge since 2026-09-15 and whose last readable board page named
  only its Chairman and Vice Chairman.

**Two latent defects in the page generator, both surfaced by Winnebago being
the one county described by two files.** Its data/app roster is contact-only —
twenty flat records with an e-mail, a phone and a source URL and no name
anywhere, because the card reads the member from WinGIS live — and the new
data/source roster names the same twenty. `il_districted` globbed both
directories into one `sorted()` list and let the later path replace the earlier,
so which file won was an accident of the two directory names sorting
`app` before `source`. It happened to produce the right page; the other order
would have produced a county naming nobody, and either way the county's own
published e-mail and phone were dropped from every row. The rule is stated now:
the data/source file wins, the data/app file must not name anybody the source
file does not, and a disagreement about who holds a seat FAILS rather than
picking one. `build_il_gis_board_rosters.py` folds the contact onto the members
it seats, refusing where a district has more than one member and so no
unambiguous owner for one address. And `NAMES_NOBODY` — which recorded Winnebago
as naming nobody — failed the build as stale the moment the collision stopped
hiding it. That table is empty now.

**One defect found in passing, in a gate rather than in this work.** An ArcGIS
`/query` URL now carries its query string in the literal instead of a `params`
dict, because `probe_user_agents.py` builds its host inventory by reading URL
literals and fetches each as written. Passed separately, the probe fetched a
`/query` path with no parameters, which the service is entitled to refuse — and
did, recording `gisportal.co.madison.il.us` as `all-refused` on all four rungs
while this scraper was reading 26 rows from it in the same minute. That is the
wrong-address defect the probe already records, one step further in: the address
was right and the request was not. Four county GIS hosts are measured now
(`token-ok` on all four), taking the artifact to 294 hosts and 224 `token-ok`,
with the three documents that quote those figures updated in the same change.

### 5. Consistent counts — done 2026-09-15

Two surfaces, and both defects were the same shape one level down from the one
the gates already guard: a number that cannot DRIFT from its source and does not
MEASURE what its own label says.

**The history pages' stat tiles.** The tiles are measured at build time through
a tiny vocabulary, so a tile cannot fall out of step with the file it counts.
Two of them counted the wrong quantity from the day they shipped. Wisconsin's
said **1,591 county-board seats named on the card**: 1,591 is the roster's KEY
count, of which 16 are vacant, one is withheld, and one is Menominee's at-large
key holding TWO countywide supervisors. The county files 1,590 supervisory
districts with the state and elects two more countywide, so there are 1,592
seats and 1,575 people named, and 1,591 is neither. Illinois's said **629
villages, towns and cities with their own officials named**, where 41 of the 629
name nobody at all; the true figure is 588.

Two verbs were added — `people:<fields>` and `keys-naming:<fields>` — and they
NAME THE FIELDS because nothing can infer them: `name` on a Wisconsin
county-board record is a supervisor and on an Illinois municipal record is the
village. The tiles now read 1,575 and 588.

**The gate took two goes, and the first one was the mistake it now guards
against.** Its first draft failed any `keys` metric whose label used a person
word, which failed two true tiles — "118 Illinois House seats with their member,
party and both offices" is correct, one key per seat, every key naming a member.
A word cannot tell a true claim from a false one. So the word list now only
decides WHETHER TO CHECK, and the check is measured: a `keys` metric under such a
label must declare where its people are, and fails when the key count and the
naming-key count differ. Three tiles declare it and pass.

**traffic.html carried three different windows.** Every figure in its prose sits
in a `<span data-stat="key">` whose text the page overwrites at load from its own
data block, so the literal inside is what a crawler reads and what a reader with
no JavaScript sees — hand-typed once and never again. The header said "July 10 –
August 29, 2026 · 51 days", the note said "July 14 – September 13, 2026, 62
days", and the data said 15 July to 14 September. `build_traffic_page.py` now
writes twelve of those literals from the same data it already derives, and FAILS
when two spans naming one key carry different text — which is exactly the two
windows, both `data-stat="range"`. That check immediately found a second pair:
`peakLabel` read "August 24" in one place and "Monday, Aug 24 — rebrand day" in
the other. The remaining 43 hand-typed keys are PRINTED on every run rather than
assumed current. All twelve were verified in Chromium against what the page
actually renders, which is the check that proves the builder computes them the
same way the page does.

The third example in the audit's finding, overberg.co's "4 places live", is on a
site this repository does not build.

### 6. `/about.html` — done 2026-09-15

`/about.html`, `/methodology` and `/corrections` all returned 404, on a domain
whose answers compete in search results with the county and state pages they are
drawn from. A reader deciding whether to trust a name had nowhere on this site to
learn who publishes it, how often it is re-read, or what happens when it is
wrong; the footers pointed at overberg.co/why/, a different site about a
different thing.

**It is generated, and that is the point.** An about page is where a project
states its size, and a stated size is the claim that goes stale first — "six
apps", "91 counties", "2,711 officeholders" have each moved inside a fortnight in
this repo's history. So it carries no number the generator did not read from a
shipped file on the run that wrote it: the fleet and each instance's scope from
`metros.json`, layer counts and verified dates from each worksheet, 183 county
pages and 2,869 seats from `build_county_pages.py`'s own adapters, 1,248 tabled
names from `build_officeholder_tables.py`, 145 recorded gaps from the shipped
`coverage-gaps.json` files, and 127 scheduled jobs from the workflow directory
GitHub actually reads. `--check` fails when the tree moves under it.

**The root pages now share one shell.** `/about.html` needed the same head, the
same 350 lines of CSS, the same masthead and the same footer as `/privacy.html`,
and the choice was between a second copy and one function. A second copy of that
is how the fleet came to carry four hand-kept palettes. `render_page()` in
`build_privacy_page.py` takes the four things a page owns — masthead title, the
line under it, the comment naming its generator, and its `<main>` — and the
privacy page comes out byte-identical, which its own `--check` proves.

Three things the build found:

- `recorded_gaps()` looked for a `gaps` key, found none, and reported **0** for a
  tree carrying 145. A derived number quietly derived from nothing is the exact
  failure this page exists to avoid, so it fails now rather than printing zero.
- `page_consistency_test.mjs` requires every page in the sitemap to link the
  privacy page, and the shared shell carries no such link — `privacy.html` is
  exempt from its own rule, so the shell never needed one. This page is the
  shell's first other user.
- The 183 county pages went stale the moment the About link was added to the
  shared footer byline, and `build_county_pages.py --check` said so. That is the
  one-copy byline working.

### 7. County-page uniqueness — measured and improved, not yet at 60%

The audit reported the county pages at a median 27% unique text against a 60%
target, 2 of 170 passing. **Re-measured on this branch before touching
anything: median 42.2%, 21 of 183 passing, median 336 words, 79 under 300.** The
audit's figure was taken before the pages gained Cook, the seven GIS-only
counties and the shared-byline About link; it is not reproduced and it is not
disputed, it is superseded by a figure whose method is stated.

`scripts/measure_county_page_text.py` keeps that method, because the first
version of it lived in a scratch directory. **It reports two numbers, and one of
them exists because the other cannot see the defect it finds.** The audit's
measure is the share of a page's distinct 5-word shingles that appear on no
other county page. That compares SETS, so a sentence printed 29 times counts
exactly as much as a sentence printed once — and Wisconsin's Dunn County page
said the same 27-word provenance sentence **29 times, 783 of its 1,312 words**,
while scoring an unremarkable 47% unique. Seven pages did it, 134 repetitions
between them. The second number is the share of a page's words inside a sentence
the page repeats.

Two changes:

- **The per-member provenance explanation is lifted to one copy per page**, which
  is the collapse the audit asked for. `freshness()` now returns the DATE and the
  EXPLANATION separately: the date can differ row to row and stays on the row,
  the explanation is a fact about the county's WEBSITE and is printed once. Dunn
  went from 1,312 words to 556. The repeated-sentence figure went from 9 pages to
  0 — and the shingle figure moved by nothing at all, which is the point of
  measuring both.
- **Every page now names an office to ask.** 171 of 183 carry a county clerk with
  an office, a telephone and an e-mail (Illinois and Wisconsin) or the board's own
  line and the representation plan the county elects under (Iowa), read from the
  file the app already reads for the same county. Michigan publishes no county
  clerk roster, so its eleven carry none rather than a blank block. Illinois's
  Peoria is the one real absence: 101 of 102 counties are in the clerk file and
  Peoria is not.

**The join is the app's own `normCountyName`, character for character**, and it
had to be: the Illinois clerk file's keys are space-stripped (`JODAVIESS`,
`ROCKISLAND`, `STCLAIR`) and Wisconsin's clerk file spells two counties
differently from its own supervisor roster ("Fond du Lac" against "Fond Du Lac",
"St. Croix" against "St Croix"). A title-case join dropped six real counties'
contacts over a spelling, and the build printed the six, which is how it was
caught.

**After both: median 45.5%, 28 of 183 passing, median 356 words, 68 under 300.**

**TWO FILES NOW STATE A SEAT COUNT ON ONE IOWA PAGE, so the two are gated
against each other.** The page says "3 districts and the 3 members who hold
them" from the roster and "the county elects 3 supervisors under Plan 3" from
the officers file. Measured 2026-09-15 all 17 agree; a page that states both and
contradicts itself is worse than one that states neither, so a disagreement
fails the build. Its negative test caught the gate reporting into a list that is
checked BEFORE the loop that fills it, where the failure was collected and never
read — a gate whose own test is the only thing that would have found it.

**THE REMAINING LEVER IS MEASURED AND BLOCKED ON A MISSING FILE.** The audit's
other suggestion — the districts that overlap each county — is the biggest
per-county fact still unwritten, and it would link the new legislator pages from
183 places. All four instances ship congressional and both legislative chambers
as geometry, and a grid-sampled overlap runs in well under a second and gives
right answers where it can be checked (Warren County: congressional 15 and 17,
Senate 36 and 47, House 71 and 94 — internally consistent, since Illinois pairs
two House districts to each Senate district). **Illinois ships county polygons
for only the counties that need a coverage test**, so Cook and most others have
no geometry here at all; the app fetches a 3.5 MB statewide county layer from
TIGERweb at runtime. Closing this needs an Illinois county fabric shipped as a
file, which is its own pipeline and its own gate.

**A cheap neighbouring-county adjacency was tried and rejected, which is worth
recording so it is not tried again.** Snapping the shipped outlines to a ~440 m
grid and calling two counties adjacent when they share a cell gives correct
answers for Warren, Monroe and Jo Daviess and says **Cook County borders
nothing** — the outlines are independently simplified and do not share vertices.
Clean, fast, confidently wrong: the same shape as the Knox fill-colour method
this project already records. An adjacency worth shipping comes from the Census
Bureau's own county adjacency file.

### 8. Google Analytics only where it is needed — done 2026-09-15

`gtag.js` is about 175 KB and was on **15 pages**, thirteen of which draw no
map. On `il/county-board.html` it was roughly 69% of the payload, beside a 3 KB
cookieless counter. It is now on **two**: `il/index.html` and `ny/index.html`,
the two apps whose worksheets declare a `ga_id`.

**Nothing this project reports on was lost.** GoatCounter was already on all
fifteen, and GoatCounter is what `data/goatcounter-traffic.json` and the traffic
report read.

**Two of the thirteen were reporting into another instance's property.**
`ca/sources.html` and `wi/sources.html` loaded Google Analytics while their own
apps declare no `ga_id` at all — both pages were cloned from Illinois's, and the
tag came with them. Nothing compared them: `brand.analytics` is the one place
that says whether an instance runs GA, `generate_metro_files.py` emits it into
that instance's `index.html` and nowhere else, and every sub-page's copy was
hand-written. `build_privacy_page.py` measures each app's own `index.html`,
which is the right subject for what it publishes and cannot see a sub-page.

`scripts/validate_analytics.py` is that comparison, and it fails on a GA tag
anywhere the worksheet does not put it.

**IT ALSO FOUND THE MIRROR IMAGE, AND THAT ONE IS NOT THIS SESSION'S TO DECIDE.**
Measured 2026-09-15: **192 of 236 pages carry no counter at all** — all 183
per-county pages, the four history pages, and five root pages (`404.html`,
`about.html`, `coverage-map.html`, `sponsorship.html`, `traffic.html`). So the
traffic report, whose subject is what this fleet gets read, has never counted
the largest page set on the site: the 183 pages carrying 2,869 officeholders,
which are the whole subject of this phase.

Two of the 192 are deliberate and recorded with a reason — the 404 page, where a
count would put other people's broken links in the report as pages, and the
coverage map, which is the landing page's iframe body rather than a destination.
**The other 190 are an omission nobody decided.** Adding a counter to 190 pages
changes what those pages send, which is the operator's call, so the figure is
HELD rather than fixed: the gate fails when it moves in either direction, up
because a page shipped uncounted, down because somebody closed part of the gap
and the recorded number has to move with it.

### Still open in phase 2

- County-page uniqueness above 60%, which needs the overlapping-districts work
  above and therefore an Illinois county fabric.
- **Splitting and minifying the map script.** Not attempted, and the reason is
  worth stating rather than leaving as an omission. The script is ~1.4 MB inline
  in each `index.html`, in ES5, fenced with the `ENGINE:BEGIN` markers
  `compose_app.py` splices and `check_engine_parity.py` lints — the fences are
  line-anchored comments, so a minifier that strips comments destroys the
  mechanism that keeps one copy of the engine across six instances. Externalising
  the script means changing how every instance is composed and served. The audit
  rates the finding High and also records that it is lab-measured only and blocks
  neither indexing nor ranking; it is a build-system change, not a template one,
  and it deserves its own PR rather than the end of a long session.
- **Split and minify the map script; load GA only where it is needed.**
