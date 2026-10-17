"""Kewaunee County: the county clerk's 2026-2027 Official Directory (PDF,
"FINAL 5/5/26").

Under "TOWN, VILLAGE AND CITY OFFICERS" each town is headed "TOWN OF <NAME>:"
and each office is one line, "Chairman . . . . . <name>" or
"Supervisor #1 . . . . <name>", with the officer's home address and telephone
and e-mail on the two lines below. The telephone line ships on the officer,
with the e-mail address printed after the number on it; the address is not
read. Read with the token on 2026-10-15 (robots.txt served empty, so
everything is allowed)."""

import re

from . import (following_emails, following_phones, norm_role, person,
               split_blocks)

COUNTY_FIPS = "061"
COUNTY_NAME = "Kewaunee"
SOURCES = ["https://www.kewauneeco.org/i/f/files/"
           "2026-2027%20Official%20Directory%20FINAL%205_5_26.pdf"]

_ROW = re.compile(r"^((?:Chair\w*|Supervisor)(?:\s*#\s*\d+)?)\s*[. ]{3,}\s*(.+)$",
                  re.I)


def _officers(block):
    people = []
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    for i, ln in enumerate(lines):
        m = _ROW.match(ln)
        if not m:
            continue
        role = norm_role(m.group(1))
        # the typesetting puts a space before a full stop ("Barry J . Fenendael")
        name = re.sub(r"\s+\.", ".", m.group(2)).strip()
        if role:
            # the address line, then "920-555-0100 - e-mail"
            people.append(person(name, role,
                                 following_phones(lines, i + 1, limit=3),
                                 emails=following_emails(lines, i + 1, limit=3)))
    return people


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("TOWN, VILLAGE AND CITY OFFICERS")
    if start < 0:
        raise RuntimeError("the 'TOWN, VILLAGE AND CITY OFFICERS' section "
                           "was not found")
    section = text[start:]
    end = re.search(r"(?m)^(VILLAGE|CITY) OF ", section)
    if end:
        section = section[:end.start()]
    towns = {}
    for town, block in split_blocks(section,
                                    r"(?m)^TOWN OF ([A-Z .'\-]+?):?\s*$"):
        people = _officers(block)
        if people:
            towns[town.title()] = people
    m = re.search(r"\b(20\d\d\s*-\s*20\d\d)\b", text[:3000])
    return {"towns": towns, "edition": m.group(1) if m else None}
