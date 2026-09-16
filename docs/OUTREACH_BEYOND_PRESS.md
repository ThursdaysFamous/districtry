# Outreach beyond the press list — clerks, civic tech, libraries

The search audit's phase 3 asks for "a Wikidata item and outreach to clerks,
civic-tech groups, libraries and newsrooms." The Wikidata item is drafted in
`docs/WIKIDATA.md`. **Newsrooms are done and running**: `docs/PRESS_LIST.md` is
a verified list with a send protocol and a ledger that records the day each
pitch went out. This file is the other three audiences, and it deliberately
contains **no contacts**.

**Nothing here is sent by an agent.** The rules are the ones
`docs/ASK_DRAFTS.md` and `docs/PRESS_LIST.md` already set, for the same reason:
a cold message to a named person is outward-facing and cannot be recalled, so it
goes when a person decides it goes, one address per message, with the send date
recorded the day it goes and never before.

## Why there are no addresses in this file

The press list took a research pass plus a mechanical re-check —
`scripts/verify_press_list.py` looked for every address on the page cited for
it. A list compiled to a lower standard than that is worse than no list: it
produces sends to addresses nobody confirmed, which is how a sender becomes a
spammer rather than a correspondent. If any of the three audiences below is
worth pitching, it is worth compiling the same way, into the same JSON, under
the same verification. Guessing an address from a pattern is the one thing that
pass forbade.

## 1. County clerks — the audience with a conflict

**This is the one to think hardest about, and the case against it is strong.**
This project already writes to county clerks, constantly, asking for data:
`docs/ASK_DRAFTS.md` holds those drafts and the guidebook records each ask's
send date and reply. Those are working relationships with people who answer
questions for free and get nothing back.

A promotional pitch sent into that relationship spends it. A clerk who has
answered a boundary question and then receives a marketing e-mail from the same
project has been converted from a correspondent into a lead, and the next
genuine question is likelier to go unanswered. **The ask route is worth more to
this project than the link would be.**

What is defensible, and is a different thing from a pitch: when a clerk asks
what the data was for — several have — answer with the county's own page
(`/il/county-board/<county>.html` names their board; `/il/precinct.html` and the
map name their precincts) and say the data is theirs, cited to them, and free to
correct. That is a reply, not outreach, and it needs no list.

**If a clerk campaign is ever run anyway, it must be a separate sender address
and a separate thread from every data ask**, so a clerk who wants nothing to do
with it can say so without closing the question route.

## 2. Civic-technology groups — the best fit

These are the people who will actually use the thing and tell others: Code for
America brigades and their local successors, open-data meetups, a state's civic
hacking community, election-administration and redistricting researchers.

Three things make this audience different from a newsroom and should shape the
message:

- **They want the data, not the map.** The link that earns a reply is
  `/llms.txt`, the sources page with its layer matrix, `LICENSE-DATA.md`, and
  the repository — not the homepage. The pitch is "here is a compiled,
  cited, ODbL database of United States civic boundaries and who holds each
  seat, and here is every gap it records about itself."
- **The gap records are the credential.** `coverage-gaps.json` and
  `docs/COUNTY_STATUS.md` say what this project does not know and why. To a
  newsroom that is a caveat; to this audience it is the evidence the thing was
  built honestly.
- **The ask is contribution, not coverage.** A brigade in a state with no
  instance is the shortest path to that state existing.

## 3. Libraries — the audience that needs the least from us

Public libraries and law libraries publish "how do I find my elected officials"
guides, and those guides are exactly where a district lookup belongs. A librarian
adding a link to a research guide is a durable, relevant citation of the kind the
audit's backlink finding is actually about.

Two notes. The useful link is the **state's own instance** (`/il/`, `/wi/`) or
one of the question pages, never the fleet root — a guide for Wisconsin patrons
pointing at a six-state landing page is a worse answer than the one it replaced.
And a library that maintains such a guide has an obvious contact route on the
guide itself, which means this audience needs no compiled list at all: it is
reached one guide at a time, by whoever is looking at the guide.

## What would have to be true before any of this is worth doing

The audit's own finding is that the site has one backlink, and its own
recommendation is Wikidata first, then these audiences. `docs/WIKIDATA.md`
records why even that one is a judgement call today: the references available
are first-party. **A published third-party article changes all three of these
conversations at once** — it is the reference the Wikidata item wants, the
credential a brigade mailing list will read, and the thing a librarian can cite
in a guide. The press list is the route to it and is already in motion.

So the honest order is: finish the press wave, wait for a piece, then the
Wikidata item, then civic tech, then libraries. Clerks, on the reasoning above,
not at all.
