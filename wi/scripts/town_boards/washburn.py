"""Washburn County: the county clerk's Information Directory 2026 (PDF).

"MUNICIPAL OFFICIALS" lists each town under a "TOWN OF <NAME>" heading. Each
officer is one line holding the office, the name and the home address with no
separator ("Chair Jacob Anderson W7796 30th Ave. Barronett WI ..."), followed
by a telephone/e-mail line. A town whose supervisors are elected at large
prints "Supervisors at" / "Large Joseph Swan N2702 ..." and then each further
supervisor as a bare "Dale Damon N4499 ..." line. The name is the words before
the first address word (a rural number such as W7796, a street number, or PO
Box); a line with no address word is not read. The officer's telephone number
ships: the one that ends the officer's own line, if any, and the numbers on the
telephone/e-mail line below it. The e-mail address on those lines ships too
(Adam, 2026-10-17: "E-mails too"); the address is not read. Read with the
token on 2026-10-15 (robots.txt: 175 bytes, no rule matches the
document)."""

import re

from . import (clean, end_phones, following_emails, following_phones,
               line_emails, looks_like_person, norm_role, person)

COUNTY_FIPS = "129"
COUNTY_NAME = "Washburn"
SOURCES = ["https://co.washburn.wi.us/wp-content/uploads/2026/07/"
           "information-directory-2026-original.pdf"]

_ADDR_WORD = re.compile(r"^([NSEW]?\d+[A-Z]?\.?|PO|P\.O\.)$")
# a line in a supervisors-at-large list that opens another office ends the list
_OTHER = re.compile(r"^(Clerk|Treasurer|Assessor|Constable|Dep\b|Deputy|"
                    r"Chair|Supervisor|TOWN|Town|Typically|Website|Zoning|"
                    r"Building|Polling|Road|Patrol)")


def name_before_address(text):
    """'Jacob Anderson W7796 30th Ave. ...' -> 'Jacob Anderson'; None when no
    address word follows the name."""
    words = text.split()
    for i, w in enumerate(words):
        if _ADDR_WORD.match(w):
            return clean(" ".join(words[:i])) if i else None
    return None


def read_block(block):
    people = []
    at_large = False
    lines = [x.strip() for x in block.split("\n") if x.strip()]

    def below(i):
        # the telephone/e-mail line below the officer's line, where the
        # wrapped heading "Supervisors at / Large" can print its last word
        # ("Large 715-555-0100 ...")
        return [re.sub(r"(?i)^(?:at\s+)?large\b\s*", "", ln)
                for ln in lines[i + 1:i + 2]]

    def phones(i, rest, name):
        # the number ending the officer's own line, then the line below it
        return (end_phones(rest[rest.find(name) + len(name):])
                + following_phones(below(i), 0, limit=1))

    def emails(i, rest, name):
        # the e-mail address ending the officer's own line or on the line
        # below it
        return (line_emails(rest[rest.find(name) + len(name):])
                + following_emails(below(i), 0, limit=1))

    for i, ln in enumerate(lines):
        m = re.match(r"^(Chair\w*|Supervisor\s*#?\d+)\s+(.*)$", ln)
        if m:
            at_large = False
            role, name = norm_role(m.group(1)), name_before_address(m.group(2))
            if role and name and looks_like_person(name):
                people.append(person(name, role, phones(i, m.group(2), name),
                                     emails=emails(i, m.group(2), name)))
            continue
        m = re.match(r"^Supervisors\b(?:\s+at\b)?(?:\s+Large\b)?\s*(.*)$", ln, re.I)
        if m:
            at_large = True
            ln = m.group(1)
        elif at_large and _OTHER.match(ln):
            at_large = False
            continue
        if not at_large or not ln:
            continue
        ln = re.sub(r"^(At\s+)?Large\b\s*", "", ln, flags=re.I)
        name = name_before_address(ln)
        if name and looks_like_person(name):
            people.append(person(name, "Supervisor", phones(i, ln, name),
                                 emails=emails(i, ln, name)))
    return people


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = re.search(r"(?m)^TOWN OF BARRONETT\s*$", text)
    end = re.search(r"(?m)^VILLAGE OF ", text[start.end():]) if start else None
    if not start or not end:
        raise RuntimeError("the town listings were not found")
    section = text[start.start():start.end() + end.start()]
    hits = list(re.finditer(r"(?m)^TOWN OF ([A-Z .'\-]+?)\s*$", section))
    towns = {}
    for i, m in enumerate(hits):
        stop = hits[i + 1].start() if i + 1 < len(hits) else len(section)
        people = read_block(section[m.end():stop])
        if people:
            towns[clean(m.group(1)).title()] = people
    ed = re.search(r"DIRECTORY\s+(\d{4})", text[:200])
    return {"towns": towns, "edition": ed.group(1) if ed else None}
