"""Chippewa County: the county's Official Directory 2026-2027 (PDF).

The "TOWN OFFICIALS" section (ending at "VILLAGE OFFICIALS") opens each town
with a line "Town of <Name> – (Town Hall – address)". Each office is an
all-capital heading ("CHAIRMAN", "SUPERVISORS", "CLERK", ...) followed by one
line per officer: "Name – (telephone) ...... home address", sometimes with an
e-mail line after it. The name is the text before the telephone, and the
numbers between the name and the dot leader ship on the officer, as does the
e-mail address on an "Email:" line directly under the officer's line; the
address after the leader is not read. Read with the token on 2026-10-15 (robots.txt:
816 bytes, no rule matches the document's path)."""

import re

from . import (add_emails, clean, line_emails, looks_like_person, person,
               phones_after_name)

COUNTY_FIPS = "017"
COUNTY_NAME = "Chippewa"
SOURCES = ["https://chippewacountywi.gov/DocumentCenter/View/366/"
           "County-Directory-PDF"]

_HEADING = re.compile(r"^[A-Z][A-Z/&\- ]{3,}$")
_TOWN = re.compile(r"(?m)^Town of ([A-Za-z .']+?)\s*[–\-]?\s*\(")


def _name(line):
    """The text before the telephone number: an en dash anywhere, a hyphen
    followed by a space or a bracket, an opening bracket, or a dot leader ends
    the name ("Heather Rothbauer-Wanish – (715) ..." keeps its hyphen)."""
    return clean(re.split(r"–|-(?=[\s(])|\(|\.{3,}", line)[0])


def _people(block):
    people, role = [], None
    last = None         # the board member on the line just above
    for ln in block.split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        if re.match(r"^e-?mail", ln, re.I):
            # the e-mail line under a board member's line is theirs
            if last is not None:
                add_emails(last, line_emails(ln))
            last = None
            continue
        last = None
        if _HEADING.match(ln):
            if re.match(r"^CHAIR(MAN|PERSON|WOMAN)?$", ln):
                role = "Chairperson"
            elif re.match(r"^SUPERVISORS?$", ln):
                role = "Supervisor"
            else:
                role = None
            continue
        if role is None:
            continue
        name = _name(ln)
        if looks_like_person(name):
            last = person(name, role, phones_after_name(ln, name))
            people.append(last)
            if role == "Chairperson":
                role = None
    return people


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = re.search(r"(?m)^TOWN OFFICIALS\s*$", text)
    if not start:
        raise RuntimeError("the TOWN OFFICIALS section was not found")
    end = re.search(r"(?m)^VILLAGE OFFICIALS\s*$", text[start.end():])
    section = text[start.end():start.end() + end.start()] if end else text[start.end():]
    hits = list(_TOWN.finditer(section))
    towns = {}
    for i, m in enumerate(hits):
        stop = hits[i + 1].start() if i + 1 < len(hits) else len(section)
        people = _people(section[m.end():stop])
        if people:
            towns[clean(m.group(1))] = people
    m = re.search(r"OFFICIAL DIRECTORY\s*\n\s*(\d{4}-\d{4})", text)
    return {"towns": towns, "edition": m.group(1) if m else None}
