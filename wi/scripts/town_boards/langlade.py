"""Langlade County: the county clerk's 2026-2027 County Directory (PDF, file
named "as of 9-1-2026").

Under "TOWN OFFICIALS" each town is headed by its name in capitals on a line
of its own ("ACKLEY"). Each office is one line, "CHAIR: <name>, <home
address>" or "SUPV: #1 <name>, <home address>", with the town, ZIP code and
telephone on the line below; only the text before the first comma is read
for the name, so the address is never kept, and on the line below only the
telephone after the dot leader is read, never the town and ZIP before it. An
e-mail address printed on a line of its own under that ships on the officer.
Read with the token on 2026-10-15 (robots.txt served empty, so everything is
allowed)."""

import re

from . import (following_emails, following_phones, looks_like_person,
               norm_role, person, split_blocks)

COUNTY_FIPS = "067"
COUNTY_NAME = "Langlade"
SOURCES = ["https://www.co.langlade.wi.us/i/f/files/county%20clerk/Phone/"
           "2026-2027%20COUNTY%20DIRECTORY%20as%20of%209-1-2026%20(002).pdf"]

_ROW = re.compile(r"^(CHAIR\w*|SUPV\.?|SUPERVISOR)\s*:?\s*(#\s*\d+)?\s*:?\s*(.+)$",
                  re.I)
_SUFFIX = re.compile(r"^(Jr|Sr|II|III|IV)\.?$", re.I)


def _officers(block):
    people = []
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    for i, ln in enumerate(lines):
        m = _ROW.match(ln)
        if not m:
            continue
        role = norm_role("Supervisor" if m.group(1).upper().startswith("SUP")
                         else "Chair")
        if role != "Chairperson" and m.group(2):
            role = norm_role("Supervisor " + m.group(2).replace(" ", ""))
        parts = [p.strip() for p in m.group(3).split(",")]
        name = parts[0]
        # a suffix printed after a comma ("Eugene Matuszewski, Jr.") belongs
        # to the name, not the address that follows it
        if len(parts) > 1 and _SUFFIX.match(parts[1]):
            name += ", " + parts[1]
        if looks_like_person(name):
            people.append(person(name, role,
                                 following_phones(lines, i + 1, limit=2),
                                 emails=following_emails(lines, i + 1, limit=2)))
    return people


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("TOWN OFFICIALS")
    if start < 0:
        raise RuntimeError("the 'TOWN OFFICIALS' section was not found")
    section = text[start + len("TOWN OFFICIALS"):]
    end = re.search(r"(?m)^(VILLAGE|CITY) OF ", section)
    if end:
        section = section[:end.start()]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^([A-Z][A-Z .'\-]+?)\s*$"):
        people = _officers(block)
        if people:
            towns[town.title()] = people
    # the edition is printed only in the file's name
    return {"towns": towns, "edition": "2026-2027, as of 9-1-2026"}
