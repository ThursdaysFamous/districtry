#!/usr/bin/env python3
"""Every shipped officeholder name must be a name.

WHY THIS EXISTS. On 2026-09-04 the weekly municipal-officials refresh (#705)
replaced all 112 of Rock Island County's published officeholder names with
telephone numbers, party labels and fragments of the source PDF's page footer.
A reader in Reynolds was shown a Village President named "(309) 372-8292
Citizens"; a reader in Rock Island a Mayor named "Appointed" and a Ward 2
Alderman named "NP". It shipped through a human-reviewed bot PR with every gate
green and stood for fifteen days.

THAT COUNTY WAS FIXED BY #1024, WHICH IS NOT THIS. That change repaired the
parser and rebuilt the data, and added a refusal inside
build_municipal_officials_roster.py so the same builder cannot write such a
value again. This gate is the other half, and the difference is measurable
rather than argued: run against the tree #1024 merged into, it still found TWO
records — Plattville's "Beth Fals 56" and Bartonville's "'s Email:
clerk@bartonville.org", the second of which #1028 then fixed at source. A
refusal at WRITE time cannot see a defect that is
already on the base branch when the writer does not run, and the municipal
build produced no file between 2026-09-08 and 2026-09-19 because Will County
was in REQUIRED_COUNTIES while its source sat behind a vendor managed challenge
(#996, #1026). Those two had been shipping since 2026-08-01 and 2026-08-24.
Will moved to PRESERVABLE on 2026-09-19, so that particular freeze is over —
the point this gate makes does not depend on it, because any required source
can stop the writer and a write-time refusal still cannot see what is already
shipped.

The two predicates are also different sizes, and the survivors are in the gap:
#1024's fabricated_name() refuses three shapes (a phone number, a party label,
a leading digit) and this one refuses nine, so "Beth Fals 56" (digits, but not
leading) and an e-mail address both pass there and fail here. Two readers of
one question is this fleet's own recurring defect, so the right end state is
that builder importing why_not_a_name from here — recorded as the follow-up
rather than done in passing, because it is an Illinois file and this is not an
Illinois change.

WHY NOTHING CAUGHT IT, which is the part worth keeping. Three guards looked at
that file and none of them asks this question:

  * the scraper's own floors are COUNTS (MIN_OFFICIALS = 100, and the broken
    run emitted 112). A parser that mis-associates every field still emits the
    right number of records, because the count is a function of how many cells
    the document has rather than of whether each one landed on its own person.
  * check_roster_retention.py measures a field's PRESENCE per source. `name`
    was present on every record, so nothing was lost by its reading; and this
    file pools at file level (629 keys, past that gate's 200-source threshold),
    so a whole county changing at once reads as a small share of the file.
  * build_county_pages.py's four adapters enumerate every county officeholder
    in the fleet — and list this exact file in NOT_COUNTY_BOARDS, deliberately
    and correctly, because village trustees are not a county board. The fleet's
    person enumerators were blind to the one file that broke.

So this gate is neither a count nor a diff. It is ABSOLUTE: it reads the
shipped tree and fails on any person record whose name is not a name, whether
or not the change under review touched that file. That is why it is its own
script rather than a rule inside check_roster_retention.py, which answers a
question only about what a diff changed and would therefore go quiet on a
defect the moment it reached the base branch.

WHAT A PERSON RECORD IS — A SHAPE, NOT A FIELD NAME. Half the roster files in
this fleet use `name` for a DISTRICT ("Precinct 3", "Ward 5", "Harter V"), so a
gate keyed on the field name alone reports 300+ findings that are all correct
data. Measured 2026-09-18 across 757 files, the three shapes below select
10,975 genuine person records and no district:

  * a record carrying a `role` beside its name (the districted county boards,
    every municipal body, the township officials);
  * a record inside a members / board / officers / head / chair / commissioners
    / supervisors / judges / trustees / council / aldermen / justices /
    delegation container (Wisconsin's seats, Iowa's supervisors);
  * a flat record carrying a `title` plus a party, e-mail or phone, or one
    carrying both a phone and an e-mail — the shape Lake County writes every
    district in, and the shape of il/data/source/ward-members.json (Chicago's
    50 alderpeople) and isbe-county-board-chairs.json (102 chairs);
  * a flat record carrying a `party` — added 2026-09-19, see below.

WHAT THE FIRST FOUR SHAPES COULD NOT SEE, and how that was found. The gate's
own OK line said "10,986 person records ... in 6 instance(s)", which reads as
fleet coverage and was not: measured per instance, New York contributed ZERO
while shipping 380 published officeholders, San Francisco 2 and Michigan 60.
Those three write rosters keyed district -> person — {"1": {"name": "Nick
LaLota", "party": "Republican", ...}} — with no `role`, no person container and
no `title`, so not one of the four shapes reached them.

A PARTY IS THE ONE FIELD ONLY A PERSON CARRIES, so that is the fifth shape. A
boundary, a building and a polling place all have a name and an address; none
has a political party. Measured across the fleet it reaches 1,462 more records,
239 of them New York's, and introduces ZERO new findings.

KEYING ON `office` WAS THE OBVIOUS NEXT STEP AND IS MEASURED AND REJECTED. It
would reach New York's council members, and it would also sweep in 549 Illinois
municipality records, 29 township records and {"name": "Cicero Public Library",
"office": {...}} — none of them people. All of them pass why_not_a_name(),
because a village's name and a library's name are perfectly good names, so the
gate would have gone green over a predicate that had stopped meaning what it
says. The rejection is in SHAPE_SELFTEST beside the shapes that were adopted.

SO NEW YORK'S 51 COUNCIL MEMBERS ARE STILL NOT EXAMINED, and the gate says so
out loud rather than burying it in a total: every run prints the per-instance
split, and an instance whose rosters it can see NOTHING in is named on a BLIND
line. That is not a failure — an instance can legitimately ship geometry before
it ships a roster, which is how Michigan arrived — but it can no longer be
invisible.

THE PREDICATE WAS ONLY HALF OF IT; THE WALK WAS THE OTHER HALF (2026-09-22).
is_person_record() can be perfectly right about a record person_records() never
hands it. The walk passed the IMMEDIATE PARENT KEY as `container`, and the two
branches disagreed: the list branch PRESERVED it, the dict branch REPLACED it
with the child's key. So {"members": [{...}]} was examined and
{"members": {"01": {...}}} was not -- the same roster, differing only in
whether its collection is a list or is keyed by district, and "members" never
reaching the predicate in the second case. SHAPE_SELFTEST's second case asserts
that arm works and it does, through 942 list-shaped records, so every test in
this file passed while the dict-shaped ones went unexamined. A keyed collection
now passes its own name through one level, exactly as a list already did, and
WALK_SELFTEST holds both shapes to the same answer. Measured fleet-wide the
change admits 182 records in two files -- wi-alderpersons.json 175,
mps-school-board-members.json 7 -- every one a person, with no false positive
and no new finding.

1,156 OFFICEHOLDERS ARE STILL OUTSIDE THIS GATE, AND THAT IS A MEASUREMENT.
1,175 WAS THE FIGURE BEFORE THIS CHANGE and it is kept here because the two are
a different question: 1,175 is what the flat-keyed class held when it was
re-measured, 1,156 is what is left once PERSON_PATHS declares Illinois's 19, and
a first draft of this paragraph printed the larger one as the remainder while
enumerating the smaller one three lines below — a total its own list disproved.
Corrected 2026-09-25 from the 1,592 this paragraph stated on 2026-09-22, which
was stale in the harmless direction: two of the four files it named as the
largest blind sets are now fully examined — `mi-commissioner-members.json` (185
records) and `wi-county-officers.json` (442) — recovered by the same walk fix
that landed with the figure. A number in a paragraph that calls itself a
measurement is still stale when it stops reproducing, whichever way it moved.
Illinois's own 19 are no longer among them: `il/data/app/school-board-members.json`
is DECLARED in PERSON_PATHS below, which is the route out this paragraph named
and did not build. What remains is `wi/data/app/county-board-members.json` 1,096
(beside 479 the walk reaches in the same file), `ny/data/app/council-members.json`
51, `wi/data/app/mpd-district-captains.json` 7 and
`wi/data/app/wi-municipal-executives.json` 2.
Before the walk fix it was 1,774 across 19 files; running why_not_a_name() over
all of them found ZERO defective, so this is a guard hole rather than a shipped
defect, and it is recorded here because the next pass would otherwise measure
it again. The remainder are flat, keyed by seat at the TOP level with no
collection name anywhere -- {"5514119": {"county": "Wood", "district": 19,
"name": "Bill L. Leichtnam", ...}} -- so no structural signal exists for the
walk to carry. The largest are wi/county-board-members.json 1,097,
mi-commissioner-members.json 197, wi-county-officers.json 125 and
ny/council-members.json 51.

THE ROUTE OUT IS A DECLARATION, NOT A WIDER PREDICATE, and the arithmetic is
why. Field shape cannot tell a person from a place: a precinct, a polling
place, a school site and a library all carry {name, address, url}. Relaxing the
shape test far enough to reach those 1,592 admits about 23,000 place records,
6,072 of which carry digits and would FAIL this gate on names their publishers
chose -- "Judicial District 8", "Eagle Grove Pct 4". What that needs is a
declared table of the json paths that hold people, re-audited against the tree
every run and FAILING on an orphan, in the shape ACCEPTED_DROPS and
NOT_COUNTY_BOARDS already use here. Not done in this change, and named rather
than implied.

SEVEN OF THIRTEEN PERSON_CONTAINERS NEVER DECIDE AN ADMISSION, measured the
same day, and that is fine in two different ways. `board` (4,164 records),
`head` (615) and `officers` (832) are shadowed because every record under them
carries a `role`, so the first arm admits them -- they are insurance against a
builder that stops emitting one. `aldermen`, `commissioners`, `council` and
`delegation` match nothing in the fleet at all; `aldermen` was anticipated
while the alderperson roster is in fact written `members` keyed by district,
which is the one shape the walk was dropping.

WHAT IS AND IS NOT A FINDING. A vacancy a county publishes is data, not a
defect: "Vacant", "Not listed", "TBD" and their spellings pass, because
Wisconsin's roster ships 16 real ones and saying so is the honest answer. What
fails is a value that can only be a mis-parse: a telephone number, a date, an
e-mail address or URL, a bare party label standing where a person should be, a
field label carried through from the source ("Clerk's Email: ..."), a value
with no letters in it at all, and a value carrying digits — the last is safe
HERE and nowhere else, because inside a genuine person record a digit means a
row index or a page number welded on.

SURFACE: DISCOVERED, NEVER LISTED. Every instance's data/app and data/source,
where an instance is a top-level directory with its own index.html — the rule
validate_card_links.py and validate_instance_registration.py already discover
the fleet by. data/source is included because a roster living there is still a
roster: Chicago's ward members and seven Illinois counties' GIS-sourced boards
are read from it by build_county_pages.py, and reach a crawler on 188 served
pages.

ACCEPTED_NAMES is EMPTY, which is a measurement rather than an omission: on
introduction every finding in the fleet was a defect and every one was fixed in
the same change. An entry added later carries a reason and a date and is
re-audited on every run, the property ACCEPTED_DROPS, EXPECTED_UNREACHABLE and
ACCEPTED_SHORTFALLS already have — it FAILS when its file has left the tree
(orphaned) and when its value is no longer in the tree (stale, so the exception
is a permanent hole with nothing saying so).

    python3 scripts/validate_officeholder_names.py            # the CI gate
    python3 scripts/validate_officeholder_names.py --report   # every record examined
"""

import argparse
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A record in one of these containers is a person even without a `role`.
PERSON_CONTAINERS = {
    "members", "board", "officers", "head", "chair", "commissioners",
    "supervisors", "judges", "trustees", "council", "aldermen", "justices",
    "delegation",
}

# A publisher that writes one of these where a name goes is stating a fact about
# the SEAT: nobody holds it. It is never a person, so it is refused here exactly
# as a party label is, and a roster records the fact STRUCTURALLY instead —
# `vacancies: N` on the district (Sangamon, Logan) or `vacant: true` on the seat
# where the seat carries a role worth keeping (Wisconsin, CCPSA).
#
# THIS TABLE ALLOWED THE WORD UNTIL 2026-09-23, and what that cost is measured
# rather than supposed: `il/county-board/logan.html` published a schema.org
# `Person` named `VACANT`, and `il/police-district.html` published two named
# `Vacant`, all three as visible text as well. Neither pipeline mentions the
# word anywhere — in both cases it is the source's own string carried straight
# through, which is precisely what a gate on names is for.
#
# ONE TABLE, THREE READERS. `why_not_a_name` refuses it, and the two scrapers
# that meet it convert on `is_vacancy_marker` rather than each carrying a copy
# of the list (scripts/logan_county_board_scraper.py, scripts/ccpsa_scraper.py).
VACANCY_SENTINELS = {
    "vacant", "vacancy", "unassigned", "open", "tbd", "none", "n/a",
    "not listed", "no candidate",
}


def is_vacancy_marker(value):
    """True when `value` is a publisher's word for an empty seat.

    The scrapers call this to convert such a row into the structural record the
    cards and the per-county pages already render, BEFORE the value can reach a
    roster — so this gate never has to see it.
    """
    return isinstance(value, str) and value.strip().lower() in VACANCY_SENTINELS

# A party label is never a person, whatever column it was read out of.
PARTY_LABELS = {
    "np", "appointed", "democratic", "democrat", "republican", "citizens",
    "progressive", "conservative", "independent", "nonpartisan", "libertarian",
    "green", "indep. party", "indep. cand.", "no party", "d", "r",
}

PHONE_RE = re.compile(r"^\(?\d{3}\)?[ .\-]?\d{3}[ .\-]?\d{4}\b")
DATE_RE = re.compile(r"^\d+/\d+/\d{4}$")
URL_RE = re.compile(r"^https?://", re.I)
FIELD_LABEL_RE = re.compile(r"(?:e-?mail|phone|fax|website|address)\s*:", re.I)

# (instance-relative path, exact value) -> {"reason": ..., "date": "YYYY-MM-DD"}
#
# ONE ENTRY, and it is a KNOWN-BAD VALUE ALREADY IN THE SHIPPED TREE that this
# gate found and that fixing belongs to somebody else — an Illinois parser
# defect, older than and unrelated to the Rock Island break #1024 repaired.
# Recording it is what lets the gate land now rather than waiting; it does not
# hide it, because audit_accepted() prints it on every run and FAILS the moment
# the value leaves the tree, so the entry cannot outlive the fix that retires
# it.
#
# THE SECOND ENTRY LASTED ABOUT AN HOUR AND ITS RETIREMENT IS THE PROPERTY
# WORKING. Bartonville's phantom second Clerk was excused here on 2026-09-19 and
# #1028 fixed it at source the same evening, at which point audit_accepted()
# failed this file with "stale, remove it" and the entry was deleted. That is
# the better outcome and the one this comment argues for: an exception is a
# placeholder for a fix, not a substitute for one.
#
# THE REASON IS NEVER "the source publishes it that way". It is this repo
# reading a document wrongly:
ACCEPTED_NAMES = {
    # EMPTY AGAIN AS OF 2026-09-21, which is a measurement rather than an
    # omission. Its one entry excused Plattville's "Beth Fals 56" and said the
    # name must be DROPPED rather than repaired — that was done at the source,
    # so the value no longer exists and the entry went with it. Leaving it
    # would have been the stale-entry failure audit_accepted() exists to catch.
}


def why_not_a_name(value):
    """Return why `value` cannot be a person's name, or None if it can be.

    Shared with the scrapers so there is one reader of this question: a builder
    that emits a name its own gate would reject should refuse to write rather
    than wait for CI to notice.
    """
    if not isinstance(value, str):
        return "not a string"
    text = value.strip()
    if not text:
        return "empty"
    if text.lower() in VACANCY_SENTINELS:
        return "a vacancy marker standing where a person should be"
    if text.lower() in PARTY_LABELS:
        return "a party label standing where a person should be"
    if PHONE_RE.match(text):
        return "a telephone number"
    if DATE_RE.match(text):
        return "a date"
    if "@" in text:
        return "an e-mail address"
    if URL_RE.match(text):
        return "a URL"
    if FIELD_LABEL_RE.search(text):
        return "a field label carried through from the source"
    if not re.search(r"[A-Za-z]", text):
        return "no letters in it"
    if re.search(r"\d", text):
        return "digits in it"
    return None


# Every case below was taken from the shipped tree rather than imagined: the
# rejections are the values the 2026-09-04 regression published, and the
# acceptances are real officeholders and real published vacancies. The check
# runs on every invocation rather than behind a flag, because a predicate this
# short is exactly the kind that gets "simplified" into rejecting O'Brien.
SELFTEST = [
    ("(309) 372-8292 Citizens", "a telephone number"),
    ("309-798-5353", "a telephone number"),
    ("NP", "a party label standing where a person should be"),
    ("Appointed", "a party label standing where a person should be"),
    ("Indep. Cand.", "a party label standing where a person should be"),
    ("128/28/2026", "a date"),
    ("’s Email: clerk@bartonville.org", "an e-mail address"),
    ("Beth Fals 56", "digits in it"),
    ("", "empty"),
    ("—", "no letters in it"),
    ("https://example.gov/mayor", "a URL"),
    ("Clerk's Email: x@y.gov", "an e-mail address"),
    ("Michelle Carr-Bruce", None),
    ("Gary N. Lueker", None),
    ("Jane E. Lundquist", None),
    ('Robert "Mike" Stewart', None),
    ("Dora “Villarreal” Nieman", None),
    ("Bo O'Brien", None),
    ("Ronald (Ron) A. Willhite", None),
    # THE THREE THAT FLIPPED, 2026-09-23. These read `None` — accepted as a
    # name — until Logan's `VACANT` and CCPSA's two `Vacant` were found on
    # served pages as schema.org `Person` nodes. A publisher's word for an
    # empty seat is a fact about the SEAT, and the rosters that meet one now
    # record it structurally before it can reach a name field, so the predicate
    # refuses it here.
    ("Vacant", "a vacancy marker standing where a person should be"),
    ("Not listed", "a vacancy marker standing where a person should be"),
    ("TBD", "a vacancy marker standing where a person should be"),
    # The refusal is on the WHOLE value, never a prefix: a surname that merely
    # starts like one is still a name, and widening this into a substring test
    # would take real people off a card.
    ("Vance Parker", None),
    ("Noneman", None),
    ("Openshaw", None),
]


# THE SHAPE PREDICATE GETS ITS OWN TABLE, because it is the half that was
# wrong. why_not_a_name() was tested from the first commit and is_person_record()
# was not, and the untested half is the one that silently examined none of New
# York's 380 published officeholders. (record, container) -> is it a person.
SHAPE_SELFTEST = [
    # The four original arms.
    ({"name": "Jane Doe", "role": "Clerk"}, None, True),
    ({"name": "Jane Doe"}, "members", True),
    ({"name": "Jane Doe", "title": "Chair", "email": "j@x.gov"}, None, True),
    ({"name": "Jane Doe", "phone": "555", "email": "j@x.gov"}, None, True),
    # The arm added 2026-09-19. A party is the one field only a person has.
    ({"name": "Nick LaLota", "party": "Republican"}, None, True),
    # ...and it must not reach through a party attribute on a POLYGON.
    ({"name": "District 5", "party": "R", "geometry": {}}, None, False),
    # Places carry a name and an address exactly as a person does. Every one of
    # these was a real false positive from a wider predicate that was measured
    # and rejected: keying on `office` swept in 549 Illinois municipality
    # records, 29 townships and one public library, all of which passed
    # why_not_a_name() because their names are perfectly good names.
    ({"name": "Cicero Public Library", "office": {"address": "5225 W. Cermak"}},
     None, False),
    ({"name": "ASHWAUBENON FIRE STATION NO. 2", "address": "x"}, None, False),
    # A district is not a person, which is why this is a shape and not a field.
    ({"name": "Precinct 3"}, None, False),
    ({"name": "Harter V"}, None, False),
    # KNOWN BLIND, and recorded rather than asserted away: New York's council
    # roster is {district: {name, office}}, which is structurally identical to
    # the library above. 51 real people this gate does not examine. Widening to
    # reach them needs a signal that separates a person's office from a place's
    # address, and no field in the fleet carries one today.
    # 51 IS THIS FILE'S SHARE AND NOT THE TOTAL: measured 2026-09-22, 1,592
    # officeholders across the fleet are blind for this same flat-keyed reason
    # (wi/county-board-members.json alone is 1,097). See the docstring -- the
    # route out is a declared table of person-bearing paths, not a wider
    # predicate, and the WALK fix that landed with this note is a different
    # defect that recovered a different 182.
    ({"name": "Christopher Marte", "office": "65 East Broadway"}, None, False),
]


# THE WALK GETS A TABLE TOO, because is_person_record() can be perfectly right
# about a record the walk never hands it. {"members": {"01": {...}}} is the
# same roster as {"members": [{...}]}, and until 2026-09-22 the first was
# examined and the second was not: the list branch PRESERVED the container and
# the dict branch REPLACED it with the district id, so "members" never reached
# the predicate. SHAPE_SELFTEST's second case asserts that arm works, and it
# does -- 942 records reach it through list-shaped rosters -- so the gate's own
# tests all passed while 182 people in two files went unexamined.
# (payload, the paths that must come out).
WALK_SELFTEST = [
    # The pair that was asymmetric. Both are one person under `members`.
    ({"members": [{"name": "Ada Lovelace"}]}, [".members[0]"]),
    ({"members": {"01": {"name": "Ada Lovelace"}}}, [".members.01"]),
    # ...at any depth, which is how the city rosters are actually written.
    ({"80075": {"members": {"08": {"name": "Dean Peterson"}}}},
     [".80075.members.08"]),
    # A keyed collection passes its OWN name through and does NOT hand it to a
    # person's sub-objects: `office` must not inherit `members`, or every
    # address in the fleet becomes a person.
    ({"members": {"01": {"name": "Ada Lovelace",
                         "office": {"name": "City Hall"}}}},
     [".members.01"]),
    # The pass-through is one level and is keyed on the collection's NAME, so a
    # container cannot leak across a file. A polling place under a district id
    # is still a place.
    ({"wards": {"01": {"name": "Ward 1 Polling Place"}}}, []),
]


def selftest():
    bad = []
    for value, want in SELFTEST:
        got = why_not_a_name(value)
        if got != want:
            bad.append("%r -> %r, expected %r" % (value, got, want))
    for record, container, want in SHAPE_SELFTEST:
        got = is_person_record(record, container)
        if got != want:
            bad.append("is_person_record(%r, %r) -> %r, expected %r"
                       % (record, container, got, want))
    for payload, want in WALK_SELFTEST:
        got = sorted(path for path, _ in person_records(payload))
        if got != sorted(want):
            bad.append("person_records(%r) -> %r, expected %r"
                       % (payload, got, sorted(want)))
    return bad


def is_person_record(node, container):
    if not isinstance(node.get("name"), str):
        return False
    if "role" in node:
        return True
    if container in PERSON_CONTAINERS:
        return True
    if "title" in node and any(k in node for k in ("party", "email", "phone")):
        return True
    if "phone" in node and "email" in node and "geometry" not in node:
        return True
    # A political party is the one field in this fleet that ONLY a person
    # carries. A boundary, a building and a polling place all have a name and
    # an address; none of them has a party. This arm is what reaches the
    # rosters keyed district -> person, which the four above miss entirely.
    if "party" in node and "geometry" not in node:
        return True
    return False


def instances(root=REPO_ROOT):
    """Top-level directories carrying their own index.html AND data/app — the
    tree is canonical, never a table (validate_instance_registration.py's rule).

    BOTH tests, because index.html alone is not the fleet's definition and
    answers wrong: `districtry/` is the brand-asset directory, it carries an
    index.html, it ships no roster, and counting it made this gate report seven
    instances where every other reader reports six.
    """
    out = []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if (os.path.isfile(os.path.join(path, "index.html"))
                and os.path.isdir(os.path.join(path, "data", "app"))):
            out.append(name)
    return out


def roster_files(root=REPO_ROOT):
    for tag in instances(root):
        for sub in ("data/app", "data/source"):
            directory = os.path.join(root, tag, sub)
            if not os.path.isdir(directory):
                continue
            for name in sorted(os.listdir(directory)):
                if name.endswith(".json"):
                    yield os.path.relpath(os.path.join(directory, name), root)


def person_records(payload, declared=()):
    """Yield (json path, record) for every person-shaped record in `payload`.

    `declared` is the path prefixes PERSON_PATHS names for this file, whose
    child records are people by declaration rather than by shape — the one
    case no predicate can decide.
    """
    stack = [("", payload, None)]
    while stack:
        path, node, container = stack.pop()
        if isinstance(node, dict):
            mine = is_person_record(node, container)
            if not mine and path in declared:
                # The declared node itself is the collection; its VALUES are the
                # people, so admit each child that carries a name rather than
                # the collection.
                for key, value in node.items():
                    if isinstance(value, dict) and isinstance(value.get("name"), str):
                        yield "%s.%s" % (path, key), value
                continue
            if mine:
                yield path, node
            # A dict under a person container is a KEYED COLLECTION -- a roster
            # written {"members": {"01": {...}}} rather than {"members": [...]}.
            # It passes its own name through to its records, exactly as the list
            # branch below already does, so the SAME roster is examined whether
            # its collection is a list or is keyed by district.
            keyed = container in PERSON_CONTAINERS and not mine
            for key, value in node.items():
                stack.append(("%s.%s" % (path, key), value,
                              container if keyed else key))
        elif isinstance(node, list):
            for i, value in enumerate(node):
                stack.append(("%s[%d]" % (path, i), value, container))


# THE DECLARED PERSON-BEARING PATHS — the route out this file's docstring named
# and did not build. A roster keyed by seat at the TOP level with no collection
# name anywhere carries no structural signal for the walk, and NO PREDICATE CAN
# SUPPLY ONE: a precinct, a polling place, a school site and a library all carry
# {name, address, url}, so relaxing the shape test to reach the people admits
# about 23,000 place records, 6,072 of them carrying digits their publishers
# chose. Measured again 2026-09-25 while building this, and my own two attempts
# at a predicate both mislabelled a file, which is the argument for a table
# rather than against it: `ia-city-contact.json` scored PERSON on its telephone
# where its `name` is a city ("Ackley"), and `municipal-officials.json` scored
# neither where its top-level `name` is a municipality whose people the walk
# already reaches under `board`/`officers`/`head`.
#
# So each entry is a judgement about one file, made by reading it: the rel path,
# the json path under which its people sit ("" for the top-level dict's own
# values), why, and the date. `audit_declared()` re-reads every entry on every
# run and FAILS on one that has left the tree or admits nothing, the shape
# ACCEPTED_NAMES and NOT_COUNTY_BOARDS already use here.
#
# ONLY ILLINOIS'S FILE IS DECLARED, DELIBERATELY. The fleet's remaining
# flat-keyed officeholders are `wi/data/app/county-board-members.json` (1,096
# supervisors, beside 479 the walk already reaches in the same file),
# `ny/data/app/council-members.json` (51), `wi/data/app/mpd-district-captains.json`
# (7) and `wi/data/app/wi-municipal-executives.json` (2) — 1,156 in total, which
# is 1,175 less the 19 this table declares, and
# examining them is not this session's to decide, because a declaration that
# turns this gate red lands on that instance's next pull request and the per-file
# judgement belongs to whoever knows that data.
#
# THAT 1,175 ALSO CORRECTS THE 1,592 THE DOCSTRING STATES, which was measured
# 2026-09-22 and is stale in the harmless direction: two of the four files it
# names as blind are now fully examined — `mi-commissioner-members.json` (185
# records) and `wi-county-officers.json` (442) — recovered by the walk fix that
# landed with it. A stale figure in a paragraph that calls itself a measurement
# is still stale.
PERSON_PATHS = {
    "il/data/app/school-board-members.json": (
        "",
        "Chicago's elected school board, keyed by the boundary's own row number "
        "with no collection name: {\"1\": {\"name\", \"email\", \"profileUrl\", "
        "\"subDistrict\"}}. Nineteen named people this gate did not examine, on a "
        "roster that stopped being hand-curated on 2026-09-23 and is now scraped "
        "weekly from cpsboe.org — so a parse defect here would ship a wrong name "
        "onto a card and an officeholder table with nothing looking at it.",
        "2026-09-25"),
}


def declared_paths(rel):
    """The json path prefixes under which `rel` is declared to hold people."""
    entry = PERSON_PATHS.get(rel.replace(os.sep, "/"))
    return () if entry is None else (entry[0],)


def audit_declared(root=REPO_ROOT):
    """A declared path FAILS when it is orphaned or admits nothing.

    Same posture as ACCEPTED_NAMES below: an entry nothing re-checks is a
    permanent claim about a file that may have changed shape underneath it.
    """
    problems = []
    for rel, (prefix, why, date) in sorted(PERSON_PATHS.items()):
        path = os.path.join(root, *rel.split("/"))
        if not os.path.exists(path):
            problems.append("%s is declared person-bearing and is not in the "
                            "tree; drop the entry or restore the file" % rel)
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError) as exc:
            problems.append("%s is declared person-bearing and does not read: "
                            "%s" % (rel, exc))
            continue
        n = sum(1 for _ in person_records(payload, declared=(prefix,)))
        base = sum(1 for _ in person_records(payload))
        if n <= base:
            problems.append("%s: the declaration admits %d record(s) and the "
                            "walk already reached %d, so it adds nothing — the "
                            "file has changed shape, or the entry was never "
                            "needed" % (rel, n, base))
        else:
            print("  declared %-46s +%d record(s) (%s)"
                  % (rel, n - base, date))
    return problems


def scan(root=REPO_ROOT):
    findings, examined, files = [], 0, 0
    per_instance = {}
    for rel in roster_files(root):
        tag = rel.split(os.sep)[0]
        per_instance.setdefault(tag, 0)
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError) as exc:
            findings.append((rel, "", "", "unreadable: %s" % exc))
            continue
        files += 1
        for path, record in person_records(payload, declared_paths(rel)):
            examined += 1
            per_instance[tag] += 1
            reason = why_not_a_name(record["name"])
            if reason and (rel, record["name"]) not in ACCEPTED_NAMES:
                findings.append((rel, path, record["name"], reason))
    return findings, examined, files, per_instance


def audit_accepted(root=REPO_ROOT):
    """An accepted entry FAILS when it is orphaned or stale. Re-read every run,
    because an exception nothing re-checks is a permanent hole in the gate."""
    problems = []
    if not ACCEPTED_NAMES:
        return problems
    shipped = set(roster_files(root))
    for (rel, value), entry in sorted(ACCEPTED_NAMES.items()):
        if rel not in shipped:
            problems.append("ACCEPTED_NAMES names %s, which no instance ships "
                            "— orphaned, remove it" % rel)
            continue
        with open(os.path.join(root, rel), encoding="utf-8") as handle:
            payload = json.load(handle)
        if not any(record["name"] == value for _p, record in person_records(payload)):
            problems.append("ACCEPTED_NAMES excuses %r in %s and that value is no "
                            "longer there — stale, remove it" % (value, rel))
        else:
            print("  accepted: %s — %r (%s, %s)"
                  % (rel, value, entry.get("reason", "no reason recorded"),
                     entry.get("date", "no date")))
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", action="store_true",
                        help="print every person record examined, per file")
    args = parser.parse_args()

    broken = selftest()
    if broken:
        print("validate_officeholder_names: FAIL — the predicate itself has moved:",
              file=sys.stderr)
        for line in broken:
            print("  - %s" % line, file=sys.stderr)
        sys.exit(1)

    tags = instances()
    if len(tags) < 2:
        print("validate_officeholder_names: FAIL — found %d instance(s) (%s); the "
              "surface is discovered from the tree and cannot be this small"
              % (len(tags), ", ".join(tags) or "none"), file=sys.stderr)
        sys.exit(1)

    findings, examined, files, per_instance = scan()
    problems = audit_accepted() + audit_declared()

    if args.report:
        for rel in sorted(set(f[0] for f in findings)):
            print("  %s" % rel)
            for _rel, path, value, reason in findings:
                if _rel == rel:
                    print("      %-40r %s   at %s" % (value, reason, path))

    if not examined:
        print("validate_officeholder_names: FAIL — 0 person records found across %d "
              "roster file(s). A gate that can only be vacuous is not a gate; the "
              "record shapes in is_person_record() have stopped matching the data."
              % files, file=sys.stderr)
        sys.exit(1)

    if findings or problems:
        print("validate_officeholder_names: FAIL", file=sys.stderr)
        for rel, path, value, reason in findings:
            print("  - %s: %r is %s   (at %s)" % (rel, value, reason, path),
                  file=sys.stderr)
        for problem in problems:
            print("  - %s" % problem, file=sys.stderr)
        print("  Fix the builder that wrote the value. Excusing one needs an "
              "ACCEPTED_NAMES entry with a reason and a date, and a reason that "
              "is not 'the source publishes it that way' — a source that "
              "publishes a telephone number where a person goes is a source this "
              "repo is reading wrongly.", file=sys.stderr)
        sys.exit(1)

    # PRINT THE SPLIT, NEVER THE TOTAL ALONE. "in N instance(s)" counts
    # instances DISCOVERED, not instances covered, and the two are different
    # numbers: it read "6 instance(s)" while New York contributed 0 records of
    # its own. A total plus an instance count reads as fleet coverage; the
    # split is what shows where this gate can and cannot see.
    split = "  ".join("%s %d" % (tag, per_instance.get(tag, 0))
                      for tag in sorted(per_instance))
    blind = [tag for tag in sorted(per_instance) if not per_instance.get(tag, 0)]
    print("validate_officeholder_names: OK — %d person record(s) across %d roster "
          "file(s) in %d instance(s), every name a name"
          % (examined, files, len(tags)))
    print("  per instance: %s" % split)
    if blind:
        # NOT a failure: an instance can legitimately ship geometry before it
        # ships a roster, which is how Michigan arrived. It is printed loudly
        # because the alternative is that it stays invisible, which is the
        # state New York was in — 380 named people, none of them examined.
        print("  BLIND: %s ship roster files and this gate examines NO record in "
              "them. Their names are not checked. Either their records match "
              "none of is_person_record()'s shapes, or they carry no people yet."
              % ", ".join(blind))


if __name__ == "__main__":
    main()
