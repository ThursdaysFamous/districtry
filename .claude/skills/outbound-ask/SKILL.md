---
name: outbound-ask
description: Draft, hold, send-record and close an outbound e-mail to a named public office — a county clerk, auditor, GIS desk or state agency — asking for one missing detail, a name tiebreak, a dataset, or a licence confirmation, and keep the ask's state (drafted, sent, followed up, answered, unresponsive) honest across the ledgers. Use it for "draft an ask for Ford County, nothing publishes the map", "the Jo Daviess reply came in, record the yes", "three weeks on the Iowa auditor tranche, write the follow-ups", "Pope still hasn't answered, mark it unresponsive", "I sent the tranche 1 e-mails today", "two directories disagree on District 4, ask the county which", "put NOT YET ASKED — DRAFTED on the gap record", "is Bureau worth an ask or is it measured shut". Nothing here is ever sent by the agent. Not for probing a source (county-n-plus-1), the gap text itself (gap-record), press outreach (press-outreach), or a PR (steward).
---

# An ask to a public office

An e-mail to a named official is outward-facing and irreversible, and its
state has been got wrong in this repo in every way a gate cannot see: a
ledger read NOT YET ASKED through three sends, two ledgers said "held" about
mail already gone, a draft inferred a departure from a directory's silence,
and a yes recorded across the repo was left off the ask's own block.
`CLAUDE.md` carries the honesty rules, the Jo Daviess licence story, the Clay
spam-folder lesson and the vendor-sweep rule; `docs/ASK_DRAFTS.md`'s "How this
file is used" is the protocol (the operator sends; record the send date the
day it goes; the cadence; a clean NO is a good outcome) and
`docs/EXPANSION_GUIDE.md` §5.1 states that the ask is a route, not a last
resort. This carries the order, the variants, and where each state is
written down.

## 0. Before a word is drafted, find out whether this office was already written to

The ledger is a hypothesis about the mailbox, not a record of it: Pope's
record said NOT YET ASKED across three sends, and a near-duplicate fourth was
drafted off it and caught only because the operator recognised the address.
Grep `docs/DATA_LAYER_GUIDEBOOK.md`, `docs/ASK_DRAFTS.md` and the instance's
`WATCH.md` for the office, and write the real dates back before drafting
anything.

**SEARCH THE SENT FOLDER, BY ADDRESS AND BY DOMAIN, AND TRUST IT OVER THIS
REPOSITORY.** Where the Gmail connector is available that is one query
(`before:<today> in:anywhere {to:<domain> from:<domain>}`) and it is not
optional: on 2026-10-01 eleven letters this repo called unsent had already
gone, and two went out that afternoon introducing the project to clerks
written to twice in August. Search by DOMAIN as well as by address — the same
county answers at a clerk, a GIS and an assessor mailbox, and a letter to one
should not read as a first approach to the county. Bare keywords match
personal mail and tell you nothing; use `to:`/`from:`. The record of what has
been sent, drafted and answered is `docs/ASK_DRAFTS.md` § "The mailbox record".

**AND THE SEARCH IS A FACT CHECK ON THE LETTER, NOT ONLY ON ITS OPENING LINE.**
Before drafting, read what the office has already SAID and check it against what
the letter ASSERTS. On 2026-10-01 two Illinois letters explained a missing roster
by describing what a request to the county's published web address returns, when
both clerks had already written that their county has no website at all — a
measurement of a host is not a statement about a county, and where the office has
made the statement, the measurement is the weaker source. Count the earlier
letters and their dates too: one county recorded as never contacted had two
threads, and one recorded as having had two letters had had three.

## 1. An ask is the residue of a probe, never a first move

Read the unit's own site first; accept an address only when the officeholder's
own name vouches for it or its form is an office mailbox — a page window is
not a witness, and the first probe of one tranche returned a deputy's
personal address in four of seven counties. Re-run the probe before
re-sending an old draft: a redesigned site often starts publishing the thing.
Then check whether someone ELSE already publishes it — a state site, a results
vendor, the clerk domain in `il/data/app/il-county-clerks.json` — because
asking dozens of counties for an address that turns out to be published
spends the operator's credibility on a question they can answer with a link.
`docs/ASK_DRAFTS.md` § "What is NOT here, and why" records both outcomes with
their measured reasons: one 48-county batch HELD until the route it was waiting
on got built (it did, and the batch was never needed), and one 15-county tranche
WITHDRAWN unsent once a person began reading those sites by hand. Neither is the
same as unanswered; keep the three apart in the ledger.

**Never write "we cannot read your page" until the page's own feed has been
read.** A page that arrives empty and fills in its members a moment later gets
them from a feed whose address, parameters and visitor key are in the page
itself. Find them in the HTML and scripts, fetch the feed that way with the
scraper's own identity after the robots.txt read for that host, and compare with
a browser. Scott County (Illinois) and Lansing (Michigan) were both told their
pages were unreadable on 2026-10-06, and both were readable. A key every visitor
receives is page configuration; a sign-in or a managed challenge is never worked
around. `docs/DATA_LAYER_GUIDEBOOK.md`, "A page that fills itself in is read
through its own feed".

## 2. Pick the recipient by who owns the record

In Iowa that is the county auditor, never a guessed treasurer@ or sheriff@.
One e-mail per county even where two things are missing. For a permission or
licence question, REPLY ON THE ORIGINAL THREAD to the person who wrote the
authorization and cc the published office mailbox so it lands in the office's
record; cc-ing an administrator who was never on the thread is optional and
can read as an escalation.

## 3. Write to the template shape

Ask 3 in `docs/ASK_DRAFTS.md` is the skeleton: a subject naming the ONE thing;
who you are, the instance URL, free and non-commercial; what already ships for
this unit and from which named sources; the one thing not found and WHY it is
missing; a request for a one-line reply; and an explicit line that a "no" is a
genuinely useful answer, so declining is easy. Two things never go in: a home
address or personal contact detail, and a guessed name — leave it off. Sign
with the literal placeholders `<YOUR NAME>` / `<YOUR E-MAIL>`; they are
deliberately never filled in that public file.

Three variants: two publishers disagree on a NAME → name both people and ask
which is correct, a smaller question than an open one; a permission
confirmation → say plainly it is not a re-litigation and nothing is blocked
on it, restate the conditions the original permission carried (Jo Daviess's
four are enumerated in `LICENSE-DATA.md` §3 — point there rather than
paraphrase), offer a fresh authorization or a form, and offer take-down as a
real outcome; a dataset or licence question to an agency → say a "not public
/ not redistributable" answer is fully acceptable and will be recorded.

## 4. Never send

The operator sends. Nothing is sent automatically and no draft is sent by
the agent that wrote it — `docs/ASK_DRAFTS.md` rule 1, and the one never in
this file that has no exception. A new draft is a new `## Ask N —` section
there, or a `### <Unit> — <Recipient> <address>` block under a tranche
heading.

**And put it in the operator's mailbox as well as in the file** — his
instruction of 2026-10-01: *"All emails should be drafted in my mailbox along
side the repo."* One Gmail draft per recipient, created with the Gmail
connector's `create_draft`, never `send_message`; the wording copied from
`docs/ASK_DRAFTS.md` verbatim with `<YOUR NAME>` and `<YOUR E-MAIL>` filled in
and the Markdown taken out, because a mail client renders none of it. A draft
in the mailbox is the same state as a draft in the file — one step closer to
his hand, and no send date anywhere. Skip any letter whose recipient address
the repo does not record, and say which. `docs/ASK_DRAFTS.md` § "Which asks
have a draft in the operator's mailbox" is the record of which already do.

## 5. Record DRAFTED where the gap lives — and know where "there" is

The unit's gap record in `docs/DATA_LAYER_GUIDEBOOK.md` carries the state in
its `blocker` text: `NOT YET ASKED — DRAFTED`. Every instance with a
`<tag>/WATCH.md` carries the ask's dates there AS WELL — `wi/WATCH.md`'s ask
row and `ia/WATCH.md`'s tranche rows — and Wisconsin's asks also sit in the
guidebook's Wisconsin ask-ledger section; Illinois has no `WATCH.md` of its
own, so its ledger is the gap record's `blocker` alone. On any state change,
grep every one of those surfaces.

## 6. On send — the same day, never before

`docs/ASK_DRAFTS.md` rule 2 (the record also uses the name "Scott rule" for
an unrelated returns-name-winners point, so cite the file, not the name):
change `NOT YET ASKED — DRAFTED` to `ASKED <date>` in the gap record and the
WATCH rows, noting who was actually addressed and cc'd; and fix, in the SAME
commit, any published statement the send makes stale — `LICENSE-DATA.md`'s
"has not been re-sought" line was changed the day Ask 6 went, because a
published legal statement a day stale is a bug here. Ask 6 carries a
`> **SENT <date>.**` block at its head; the protocol does not require one,
and it is the surface most often left behind — if an ask has one, it is one
more place to keep true.

## 7. Follow up, then say UNRESPONSIVE — which is not "no source"

The cadence is `docs/ASK_DRAFTS.md` rule 3 (~3 weeks, then ~2). For a
permission ask, UNRESPONSIVE is a claim about the ask and never about the
permission: the existing authorization stands and the display continues.

## 8. On a reply — every surface, the same day

YES → `ANSWERED <date>` with the wording in the unit's guidebook entry, then
every place the gap was written. For Jo Daviess that was `LICENSE-DATA.md`
§3; the `license` string in the payload
`scripts/build_jodaviess_board_districts.py` writes (the data file re-ships
only when the operator re-runs the builder against the offline shapefile —
flag it, never hand-edit the JSON); the data-file note in
`metro-worksheet.json`, which regenerates the note in
`scripts/validate_index.py` (run `python3 scripts/generate_metro_files.py`);
the hand-kept manifest note in `scripts/validate_sources.py`; and the card's
fixed credit literal in `il/index.html` if the wording changes — the card
reads nothing from the data file, and `SOURCE_LABEL` was not touched. Then
the ask's own block in `docs/ASK_DRAFTS.md`, which is the surface a reply is
most often not written back to; check it on every YES and NO.

NO splits by what was asked. A data or licence question → `ANSWERED <date>`
in the blocker with the substance, the question closed for good, `wanted`
narrowed or the record retired. A display permission → the file leaves
`il/data/app/`, the dispatch entry, worksheet rows and outline membership go,
and the gap record reopens citing the withdrawal; that is a real outcome and
the ask should not pretend otherwise. Quote a reply as written, typo
included, and say which figure is the typo.

## 9. Nevers

- Never let a draft imply the agent will send.
- Never record a send date before the day it goes; never leave one unrecorded on that day.
- Never draft to an office without checking every ledger and the sent mail for a prior ask.
- Never infer from an absence — a directory that omits someone has not said they left.
- Never write a home address into the repo, even when a clerk's reply carries one.
- Never write "the county publishes no X" to the person who maintains the source without having searched.
- Never ask for something a state site or vendor already publishes.
