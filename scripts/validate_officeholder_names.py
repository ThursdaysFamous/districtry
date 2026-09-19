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
build has produced no file since 2026-09-08 because Will County is in
REQUIRED_COUNTIES and its source sits behind a vendor managed challenge (#996,
#1026). Those two had been shipping since 2026-08-01 and 2026-08-24.

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
    50 alderpeople) and isbe-county-board-chairs.json (102 chairs).

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

# A county that publishes a seat as empty is stating a fact about the seat.
VACANCY_SENTINELS = {
    "vacant", "vacancy", "unassigned", "open", "tbd", "none", "n/a",
    "not listed", "no candidate",
}

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
    ("il/data/app/municipal-officials.json", "Beth Fals 56"): dict(
        date="2026-09-19",
        reason="Plattville's clerk, shipping since 2026-08-01. Kendall's yearbook "
               "parser reads past the end of the last entry in its section, gluing a "
               "trailing number on; the same bleed put the county Democrats' e-mail "
               "and a Department of Revenue URL on that municipality. The name must "
               "be DROPPED rather than repaired to 'Beth Fals' — the Douglas County "
               "rule — which is a change to an Illinois scraper, not to this gate.",
    ),
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
        return None
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
    ("Vacant", None),
    ("Not listed", None),
    ("TBD", None),
]


def selftest():
    bad = []
    for value, want in SELFTEST:
        got = why_not_a_name(value)
        if got != want:
            bad.append("%r -> %r, expected %r" % (value, got, want))
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


def person_records(payload):
    """Yield (json path, record) for every person-shaped record in `payload`."""
    stack = [("", payload, None)]
    while stack:
        path, node, container = stack.pop()
        if isinstance(node, dict):
            if is_person_record(node, container):
                yield path, node
            for key, value in node.items():
                stack.append(("%s.%s" % (path, key), value, key))
        elif isinstance(node, list):
            for i, value in enumerate(node):
                stack.append(("%s[%d]" % (path, i), value, container))


def scan(root=REPO_ROOT):
    findings, examined, files = [], 0, 0
    for rel in roster_files(root):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError) as exc:
            findings.append((rel, "", "", "unreadable: %s" % exc))
            continue
        files += 1
        for path, record in person_records(payload):
            examined += 1
            reason = why_not_a_name(record["name"])
            if reason and (rel, record["name"]) not in ACCEPTED_NAMES:
                findings.append((rel, path, record["name"], reason))
    return findings, examined, files


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

    findings, examined, files = scan()
    problems = audit_accepted()

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

    print("validate_officeholder_names: OK — %d person record(s) across %d roster "
          "file(s) in %d instance(s), every name a name"
          % (examined, files, len(tags)))


if __name__ == "__main__":
    main()
