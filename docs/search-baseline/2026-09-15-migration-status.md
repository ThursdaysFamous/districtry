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

**Chicago's 50 alderpeople are not tabled.** `il/index.html` fetches Socrata `htai-wnw4` live
on first toggle of the ward layer, so there is no shipped roster to read. `NOT_YET` records
that with its date and is re-audited every run. The dataset carries all 50 with a name, ward
office address, phone, e-mail and website, so the work is a roster pipeline — scraper,
builder, count guard, weekly workflow opening a PR — plus one decision: whether the card
keeps reading Socrata live beside a shipped snapshot, or moves to the file.

Given `/il/ward.html` is the page phase 0 asked Google to re-index and Chicago wards are the
site's largest search term, this is the highest-value item left in phase 1.

### Still open

- **Chicago ward roster pipeline**, and the table that follows it. See above.
- **Verified dates and `dateModified`** site-wide. 3 of 75 Illinois county pages show one.
