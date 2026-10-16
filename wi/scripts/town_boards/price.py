"""Price County: the county's Directory of County, City, Village and Town
Officers, 2025-2026 edition (PDF).

The town section follows the villages: each town under a "TOWN OF <NAME>"
heading, then one line per office, "Chairperson........ Jeff Hoogland" or
"Supervisor #1........ Glenn Uhren", with the officer's home address and
telephone on the next line, which is never read. The section ends at "OTHER
TAXING AUTHORITIES". Read with the token on 2026-10-15 (robots.txt: 816 bytes,
no rule matches the file)."""

import re

from . import clean, norm_role, split_blocks

COUNTY_FIPS = "099"
COUNTY_NAME = "Price"
SOURCES = ["https://co.price.wi.us/DocumentCenter/View/891/"
           "Price-County-Directory?bidId="]

_ROW = re.compile(r"^(Chairperson|Chairman|Supervisor(?:\s*#?\d+)?)\s*"
                  r"[.…]{2,}\s*(.+)$")


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
        for line in block.split("\n"):
            m = _ROW.match(line.strip())
            role = norm_role(m.group(1)) if m else None
            if role:
                people.append({"name": clean(m.group(2)), "role": role})
        if people:
            towns[town.title()] = people
    m = re.search(r"\b(20\d\d)\s*[-–]\s*(20\d\d)\b", text[:200])
    return {"towns": towns,
            "edition": ("%s-%s" % m.groups()) if m else None}
