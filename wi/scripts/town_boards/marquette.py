"""Marquette County: the county's Directory 2026-2027 (PDF, file dated
06.30.2026).

Its "Town, Village, and City Officers" pages list each town under a "Town of
<Name>" heading, then the board laid out in two columns: one text line carries
up to two "Role Name" pairs ("Chairperson Scott Kempley Supervisor Roger
Wallis"), followed by the two people's home addresses, phones and e-mails, which
are never read. Only the lines that open with Chairperson or Supervisor are
used. Read with the token on 2026-10-15 (robots.txt: 190 bytes, no rule matches
the file)."""

import re

from . import clean, norm_role, split_blocks

COUNTY_FIPS = "077"
COUNTY_NAME = "Marquette"
SOURCES = ["https://www.marquettecountywi.gov/wp-content/uploads/2026/06/"
           "2026-2027-County-Directory-in-Publisher-06.30.2026.pdf"]

# A role as the county prints it, with an optional seat number and the en dash
# some rows put after it ("Supervisor 1– Dennis Daye").
_ROLE = re.compile(r"\b(Chairperson|Supervisor(?:\s+\d)?)\s*[–-]?\s+")


def _people(block):
    out = []
    for line in block.split("\n"):
        line = line.strip()
        if not re.match(r"^(Chairperson|Supervisor)\b", line):
            continue
        hits = list(_ROLE.finditer(line))
        for i, m in enumerate(hits):
            end = hits[i + 1].start() if i + 1 < len(hits) else len(line)
            name = re.sub(r"\(\d{4}\)", "", line[m.end():end])
            role = norm_role(m.group(1))
            if role and clean(name):
                out.append({"name": clean(name), "role": role})
    return out


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("Town, Village, and City Officers")
    if start < 0:
        raise RuntimeError("the 'Town, Village, and City Officers' pages "
                           "were not found")
    section = text[start:]
    end = re.search(r"(?m)^-?\s*(Village|City) of ", section)
    if end:
        section = section[:end.start()]
    towns = {}
    for town, block in split_blocks(section,
                                    r"(?m)^-?\s*Town of ([A-Z][a-z]+"
                                    r"(?: [A-Z][a-z]+)?)\b.*$"):
        people = _people(block)
        if people:
            towns[town] = people
    m = re.search(r"\b(20\d\d)\s*[-–]?\s*(20\d\d)\b", text[:400])
    return {"towns": towns,
            "edition": ("%s-%s" % m.groups()) if m else None}
