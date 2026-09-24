---
name: gap-record
description: Write, correct or retire an entry in the guidebook's gaps block — record a MEASURED absence in the two-audience shape build_coverage_gaps.py enforces, keep the ask ledger inside its blocker field, and regenerate the panel files, the history pages and COUNTY_STATUS so the gates stay green. Use it for "record the gap for Jasper — measured, not guessed", "write up Bureau's blocker, the assessor sent a licence", "Pope says NOT YET ASKED but we sent three, fix the ledger", "add a coverage gap for Jones County's supervisor districts", "retire the stale coverage claims for the seven counties that shipped", "build_coverage_gaps says summary is 312 characters", "the NYC panel needs a gap for the community-board roster". Not for probing the source (county-n-plus-1), drafting the e-mail (outbound-ask), or a red PR (steward).
---

# A gap record

A gap record is the only thing that makes an absence visible: four counties
sat unbuilt for weeks with every gate green because nothing was on file to
notice. `CLAUDE.md` carries that lesson and the "record the blocker you
MEASURED" rule; `scripts/build_coverage_gaps.py` enforces the record's shape
and is the authority on it; the voice rules are
`docs/DATA_LAYER_GUIDEBOOK.md` § "How to write a gap record". This is the
procedure, thin because the content churns daily.

## 1. Where it lives, and what reads it

The block between `<!-- ==== GUIDEBOOK:BEGIN gaps ==== -->` and its END marker
in `docs/DATA_LAYER_GUIDEBOOK.md` — one JSON object keyed by each instance's
`this_metro` (its `metro-worksheet.json`); an instance's array must exist
even if empty. `scripts/build_coverage_gaps.py` renders it to each instance's
`<tag>/data/app/coverage-gaps.json` for the Data gaps panel;
`docs/COUNTY_STATUS.md` (Illinois only), the history pages' measured tile
and the weekly fleet-status run read the result. Line numbers in the block
move daily; grep the markers.

## 2. Before writing, read your own records

Grep the guidebook for the unit — it may already live inside another record
that names several counties. Grep the scraper tables and builder docstrings.
Read `docs/ASK_DRAFTS.md`. Search the sent mail: treat the record as a
hypothesis about the mailbox, and write the real date back. A near-duplicate
ask to a non-replying office is worse than no ask.

## 3. Decide whether it belongs

Only gaps a READER COULD HELP CLOSE — a missing or blocked source, or a shipped
layer's known hole. Not a concept that structurally does not apply (that is a
matrix cell), not a live outage (the card reports it), not a parity debt.

## 4. The shape — two audiences, five refusals

`REQUIRED` in the builder is eight keys: `id`, `concept`, `area`, `kind`,
`summary`, `why`, `blocker`, `wanted`. `layer` and `counties` are optional
but validated when present: `layer` is a registered id in THAT instance's
worksheet, or null for an unbuilt concept; `counties` are shipped outline
slugs (an unserved county with a gap ships its outline as gap-location
geometry only), and they are what NAMES the counties a gap affects — the
panel's where-you-clicked section and `COUNTY_STATUS` read the array, never
the prose. The fifth refusal: an instance that ships county outlines must
have at least one gap tagged with a county, or the build refuses — the first
gap you write for a new instance carries `counties`. `kind` is one of `KINDS`:
`no-source` / `blocked` (a source exists and refuses automation or is
licence-gated) / `data-quality` (a shipped layer with a known hole).

**The reader fields** — `summary`, `why`, `wanted` — ship to the panel, each
at most `READER_MAX` characters, and the builder refuses a URL or hostname,
an ISO date (write "since 2021"), or two adjacent all-caps words of three or
more letters; the voice — what DOES work in the same breath, one plain
sentence of cause, what would close it — is the guidebook's.

**`blocker`** — unbounded, never shipped, an append-only dated log in record
voice for the next maintainer. **Four elements or it is not a measurement: the
URL tried, the CLIENT it was tried with, the DATE, and WHAT CAME BACK — and the
conclusion states what is true of THAT URL, never of the body.** "Forest does
not resolve" is unfalsifiable and was wrong; "GET https://co.forest.wi.gov/
with the pinned browser headers, 2026-08-25 → 200, zero occurrences of
district" is a fact whose next reader sees at a glance that ONE address was
tried. Eight Wisconsin counties shipped in a day in 2026 and not one had
started publishing anything new: every record was accurate about its page and
false as written, and the form is what would have shown it. Open with the date
and method of the first measurement (`Checked 2 Aug 2026 …`,
`MEASURED 2026-08-26 by …`); prefix
every later finding with a dated tag — CORRECTED, RE-MEASURED, SWEPT, PARTLY
CLOSED, CLOSED, ANSWERED — and keep the disproved sentence in place under its
correction. Every host, date and status goes here, in the vocabulary of what
was measured: unresponsive, licence-gated, split-precinct, raster-only. "No
source exists" is almost never one of them. Two host findings that are
opposites: a clerk domain with NO A record and a live MX is mail-only — no
site here, the ask route intact (`scripts/probe_incomplete_tls_chains.py`
reports it as no-dns); a domain that RESOLVES and refuses HTTP is a website
that exists and blocks this client — record it as `blocked` with the
refusal's measured shape (WAF deny, captcha 202, incomplete TLS chain),
never as "no website".

## 5. The ask ledger — the vocabulary is the contract, the place varies

`NOT YET ASKED` → `NOT YET ASKED — DRAFTED` → `ASKED <date>`, written the day
it goes and never before → `ANSWERED <date>` with the reply's substance, or
`UNRESPONSIVE` only after the follow-up cadence in `docs/ASK_DRAFTS.md`. No
structured `asked` field exists. WHERE it is written differs by instance —
Illinois in the record's `blocker`; Iowa also in `ia/WATCH.md`; Wisconsin in
the guidebook's Wisconsin ask-ledger section and `wi/WATCH.md` as well as the
blocker — and the outbound-ask skill is the authority on placement.

## 6. Closing — three shapes, and one retirement that must not happen

(a) A county that shipped WITH something still missing gets a successor
entry under a new id whose blocker opens `Successor to <old-id>, RETIRED
<date> when <county> shipped …` and carries forward what the retired record
got wrong — that is the part worth keeping. (b) A gap closed outright is
deleted and its story goes to a dated backlog section. (c) A partial close
stays, `PARTLY CLOSED <date>`, may downgrade `kind` to `data-quality`, and
narrows `wanted`. Retire only the records of counties that SHIPPED: an
unserved county's record, through its `counties` tag, is what lists it as
frontier in `docs/COUNTY_STATUS.md`, and deleting it demotes the county to
unresearched. A gap closed on a source a READER contributed owes a credit row
in `docs/SOURCE_CREDITS.md` — gap id, link, submitter or "anonymous", date —
and a mention in the changelog entry; no gate can see that step. A
`no-source` entry ages badly in one direction only; re-test them periodically.

## 7. Regenerate, then gate — every file that reads the block

```bash
python3 scripts/build_coverage_gaps.py                                                     # Illinois
python3 scripts/build_coverage_gaps.py --metro wisconsin --out wi/data/app/coverage-gaps.json
python3 scripts/build_coverage_gaps.py --metro iowa      --out ia/data/app/coverage-gaps.json
python3 scripts/build_coverage_gaps.py --metro michigan  --out mi/data/app/coverage-gaps.json
python3 scripts/build_history_page.py            # the history tiles COUNT the shipped gap files
python3 scripts/build_county_status.py
python3 scripts/validate_gap_counts.py           # a number a record STATES vs the file it describes
python3 scripts/build_about_page.py              # about.html states the fleet-wide gap TOTAL
python3 scripts/build_sitemap.py                 # a regenerated history page moves its lastmod
```

**The last two were missing from this list until 2026-09-22, and both went red
on the first change that followed it.** Six new Michigan records took
`about.html`'s recorded-gap total from 146 to 152, and regenerating
`mi/history.html` moved the lastmod the sitemap publishes for it — so a run
that did exactly what this section said still failed two gates. Neither reads
the gaps block directly, which is why they were not obvious: one counts the
shipped gap FILES and the other dates a page those files regenerate.

`build_about_page.py` is the one most easily missed and it is not optional: about.html
publishes the fleet's recorded-gap TOTAL, so adding or retiring ONE record anywhere
moves it and `--check` fails the merge. It was absent from this list until 2026-09-22,
when a record written by following this section exactly went red in CI on that gate
alone.

**A record that STATES a count declares it** — `counts`, checked by the last
line above and never shipped. Write the declaration in the same edit as the
number: `ia-board-chair` said 43 of 99 for eleven days while its file held 38,
and the prose, the complement and `ia/WATCH.md` were all wrong together.

Those are the lines `.github/workflows/smoke-test.yml` runs; a key CI does
not check (`nyc`, `sf`) still needs its `--metro <key> --out <tag>/data/app/coverage-gaps.json`
run, and only the weekly GAPS notice catches it otherwise. `--out` is
MANDATORY beside `--metro` in BOTH modes: without it a write clobbers
Illinois's file and a check mis-compares against it. Then `--check` on each,
and the steward battery.

## 8. Never

- Never a hostname, a status code or a date in a reader field.
- Never "no website" for a domain that resolves and refuses; never "no source exists" for a blocker that was measured as something else.
- Never a conclusion about a body from one URL, and never a blocker missing its client or its date.
- Never edit the record without regenerating every file in §7.
- Never retire an unserved county's record.
