"""Oneida County: the county clerk's 2026-2027 Directory (PDF, "2026 Directory
Final Website").

Each town has its own page under a "TOWN OF <NAME>" heading. Every office has
an upper-case heading of its own ("CASSIAN CHAIR", "CASSIAN SUPERVISORS",
"CASSIAN CLERK"), and each officer under it takes a name line ending in a dot
leader and a telephone number, then two lines of mailing address and e-mail,
which are never read. Only the lines with a dot leader under the CHAIR and
SUPERVISORS headings are used: the text before the leader is the name, and the
number after it ships on the officer (Adam, 2026-10-17). Read with the token
on 2026-10-15 (robots.txt: 123 bytes, no rule matches the file)."""

import re

from . import clean, person, phones_after_name, split_blocks

COUNTY_FIPS = "085"
COUNTY_NAME = "Oneida"
SOURCES = ["https://www.oneidacountywi.gov/wp-content/uploads/2018/08/"
           "2026-Directory-Final-Website.pdf"]

_HEADING = re.compile(r"^[A-Z][A-Z .']+ (CHAIR\w*|SUPERVISORS?|CLERK\w*|"
                      r"TREASURER|ASSESSOR|FIRE CHIEF|CONSTABLE\w*|"
                      r"DEPUTY\b.*|[A-Z ]+)$")
_LEADER = re.compile(r"\s*(\.{3,}|…+).*$")


def _people(block):
    out = []
    role = None
    for line in block.split("\n"):
        line = line.strip()
        if not line:
            continue
        if _HEADING.match(line) and line.upper() == line:
            if re.search(r" CHAIR\w*$", line) and "VICE" not in line:
                role = "Chairperson"
            elif re.search(r" SUPERVISORS?$", line):
                role = "Supervisor"
            else:
                role = None
            continue
        if role and _LEADER.search(line):
            name = clean(_LEADER.sub("", line))
            if name:
                out.append(person(name, role, phones_after_name(line, name)))
    return out


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    towns = {}
    # the contents page lists "Town of Cassian 33"; the town pages open with
    # the upper-case heading on a line of its own
    for town, block in split_blocks(text, r"(?m)^TOWN OF ([A-Z][A-Z .']+?)\s*$"):
        people = _people(block)
        if people:
            towns[town.title()] = people
    m = re.search(r"\b(20\d\d)\s*[-–]\s*(20\d\d)\b", text[:2000])
    return {"towns": towns,
            "edition": ("%s-%s" % m.groups()) if m else None}
