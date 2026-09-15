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

### Still open in phase 2

- **The other missing large counties**: Winnebago, Madison, St. Clair,
  Champaign, McLean and Kankakee. Winnebago is the instructive one — its roster
  ships with 20 districts carrying an e-mail and a phone each and **no `name`
  field at all**, so `build_county_pages.py` correctly gives it no page. The
  e-mail local parts look like names (`ABooker@`, `JWebster@`); deriving a
  person's name from an e-mail address is exactly the guess this project does
  not make. That is a scraper gap, not a page gap.
- **NYC police precinct page.** ~60 impressions at positions 7–9, 0 clicks, all
  landing on `/ny/`.
- **`/about.html`**, consistent counts, county-page uniqueness above 60%.
- **Split and minify the map script; load GA only where it is needed.**
