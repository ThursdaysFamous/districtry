"""Price County: the county's Directory of County, City, Village and Town
Officers, 2025-2026 edition (PDF).

The town section follows the villages: each town under a "TOWN OF <NAME>"
heading, then one line per office, "Chairperson........ Jeff Hoogland" or
"Supervisor #1........ Glenn Uhren", with the officer's home address and
telephone on the next line, the number in brackets at the end of it
("... WI 54555 (715-555-0100)"). That bracketed number is read on its own and
ships; the address before it is not read. Where the first line below holds an
address and no number, the second line is read the same way, unless it opens
another office. The section ends at "OTHER TAXING AUTHORITIES". Read with the
token on 2026-10-15 (robots.txt: 816 bytes, no rule matches the file)."""

import re

from . import OTHER_OFFICE, clean, norm_role, person, phones_in, split_blocks

COUNTY_FIPS = "099"
COUNTY_NAME = "Price"
SOURCES = ["https://co.price.wi.us/DocumentCenter/View/891/"
           "Price-County-Directory?bidId="]

_ROW = re.compile(r"^(Chairperson|Chairman|Supervisor(?:\s*#?\d+)?)\s*"
                  r"[.…]{2,}\s*(.+)$")
# the bracketed telephone number that ends an officer's address line
_AT_END = re.compile(r"\(([^()]*)\)\s*$")


def _numbers(lines, i):
    """The officer's numbers: the bracket ending the line below the office
    line, or, where that line has none, the bracket ending the line after."""
    for ln in lines[i + 1:i + 3]:
        if OTHER_OFFICE.search(ln) or _ROW.match(ln):
            return []
        m = _AT_END.search(ln)
        if m:
            return phones_in(m.group(1))
    return []


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = re.search(r"(?m)^TOWN OF ", text)
    if not start:
        raise RuntimeError("no 'TOWN OF' heading was found")
    section = text[start.start():]
    end = section.find("OTHER TAXING AUTHORITIES")
    if end > 0:
        section = section[:end]
    towns = {}
    for town, block in split_blocks(section,
                                    r"(?m)^TOWN OF ([A-Z][A-Z .']+?)\s*$"):
        people = []
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        for i, line in enumerate(lines):
            m = _ROW.match(line)
            role = norm_role(m.group(1)) if m else None
            if role:
                people.append(person(clean(m.group(2)), role,
                                     _numbers(lines, i)))
        if people:
            towns[town.title()] = people
    m = re.search(r"\b(20\d\d)\s*[-–]\s*(20\d\d)\b", text[:200])
    return {"towns": towns,
            "edition": ("%s-%s" % m.groups()) if m else None}
