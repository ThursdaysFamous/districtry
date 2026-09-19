# A Wikidata item for districtry — drafted, not created

<!-- ==== GENERATED FILE — DO NOT HAND-EDIT ==== -->
<!-- Emitted by scripts/build_wikidata_draft.py.
     Regenerate:  python3 scripts/build_wikidata_draft.py
     Drift gate:  python3 scripts/build_wikidata_draft.py --check
     Re-verify:   python3 scripts/build_wikidata_draft.py --verify  (network) -->

**Nothing here has been entered on wikidata.org.** Creating the item is an edit
to a public database that other people will build on, made under a declared
conflict of interest, and it goes when a person decides it goes — the rule
`docs/ASK_DRAFTS.md` and `docs/PRESS_LIST.md` already set for everything
outbound.

## Read this before creating it

**The conflict of interest is real and must be declared.** Wikidata asks an
editor with a connection to a subject to say so. Anyone creating this item
should be editing from an account whose user page states the connection, and
should expect — and welcome — other editors changing it.

**Notability is the open question, and this project cannot settle it.**
Wikidata's notability policy admits an item that "refers to an instance of a
clearly identifiable conceptual or material entity ... that can be described
using serious and publicly available references." As of 2026-09-16 the
references available are the site itself and its source repository, both
first-party. The press list records 17 newsrooms contacted and one reply
expressing interest; no third-party piece has published. An item created on
first-party references alone can be nominated for deletion, and that is a
foreseeable outcome rather than a surprise. **The cheap course is to wait for
one published third-party article and create the item citing it.** The other
course — create it now and accept the risk — is a legitimate choice and is the
operator's, not this file's.

**Do not create an item for the person.** A biography item about a living
private individual carries obligations this project is not set up to meet, and
the audit asked for an item about the project.

## The item

| Field | Value |
|---|---|
| Label (en) | districtry |
| Description (en) | web application for finding the civic districts that cover a United States address, and who represents them |
| Also known as (en) | districtry.com; Chicago District Explorer (the project's name before 2026-08-24) |

### Statements

| Property | Value | Note |
|---|---|---|
| P31 (instance of) | Q35127 (website) | |
| P31 (instance of) | Q189210 (web application) | A second value, not a replacement: it is a website and it is an application served through one. |
| P856 (official website) | https://districtry.com | |
| P1324 (source code repository URL) | https://github.com/ThursdaysFamous/districtry | |
| P17 (country) | Q30 (United States) | |
| P407 (language of work or name) | Q1860 (English) | |
| P275 (copyright license) | Q13785927 (Apache Software License 2.0) | The CODE licence, from this repository's own `LICENSE`. |
| P275 (copyright license) | Q1224853 (Open Database License) | The DATA licence, from `LICENSE-DATA.md`, which covers the compiled databases and explicitly not the public records underneath them. Enter both or neither — one alone states half of what this project publishes. |
| P1001 (applies to jurisdiction) | Q1204 (Illinois) | the `/il/` instance |
| P1001 (applies to jurisdiction) | Q1384 (New York) | the `/ny/` instance |
| P1001 (applies to jurisdiction) | Q62 (San Francisco) | the `/ca/` instance |
| P1001 (applies to jurisdiction) | Q1537 (Wisconsin) | the `/wi/` instance |
| P1001 (applies to jurisdiction) | Q1546 (Iowa) | the `/ia/` instance |
| P1001 (applies to jurisdiction) | Q1166 (Michigan) | the `/mi/` instance |

### What is deliberately absent

**No count of anything.** Not counties, not layers, not officeholders. Every one
of those is true on the day it is typed and nobody will come back to a Wikidata
item when it moves — the same reason no generated page here states a seat count.
The jurisdictions above come from `metros.json`, so a new state reaches this
draft by being registered rather than by being remembered.

**P571 (inception).** The date the project began is not readable from this repository:
its git history here is shallow and the public changelog's earliest entry is a
snapshot rather than a start. The operator knows it; this file will not guess
it. Add it when creating the item, sourced to something public.

**Developer, operator and author.** Each of those properties takes an ITEM, and
the only candidate is a person — see the rule above. Leave them empty.

## Every id above, verified

Fetched from `Special:EntityData` on **2026-09-16**, with the English label
wikidata.org returned. `--verify` re-fetches and fails on a label that has moved.
This matters: the first draft of this table used Q193424 for "web application",
which is the item for **web service**.

**Nothing re-runs `--verify` on a schedule, and that is deliberate rather than an
oversight.** This file exists for one human action; a monthly job re-checking
twenty labels would be machinery guarding a document nobody is reading in the
months between. Run it immediately before creating the item.

**Which Wikidata URLs this project may read was measured, not assumed.** Its own
robots reader (`scripts/robots_policy.py`) says `/w/api.php` is disallowed and so
is `query.wikidata.org/sparql`, so neither the search API nor SPARQL is available
here. `/wiki/Special:EntityData/*.json` is explicitly allowed, and is the only
endpoint used.

| Id | Label on 2026-09-16 |
|---|---|
| `P1001` | applies to jurisdiction |
| `P1324` | source code repository URL |
| `P17` | country |
| `P275` | copyright license |
| `P31` | instance of |
| `P407` | language of work or name |
| `P571` | inception |
| `P856` | official website |
| `Q1166` | Michigan |
| `Q1204` | Illinois |
| `Q1224853` | Open Database License |
| `Q13785927` | Apache Software License 2.0 |
| `Q1384` | New York |
| `Q1537` | Wisconsin |
| `Q1546` | Iowa |
| `Q1860` | English |
| `Q189210` | web application |
| `Q30` | United States |
| `Q35127` | website |
| `Q62` | San Francisco |
