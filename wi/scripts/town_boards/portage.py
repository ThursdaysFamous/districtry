"""Portage County: the county clerk's Official Directory (PDF, "County
Directory PDF").

Its TOWN OFFICERS pages give each town under a "TOWN OF <NAME>" heading and a
three-column table (Name, Phone/Email/Fax, Address). In the extracted text each
officer is one line, "Chairperson: Raymond Oksuita 715-581-7208 10734 Lake Helen
Heights", with the e-mail and the rest of the home address on the next line.
Only the text between the office's colon and the telephone number is read; a
row with no telephone number to end the name is dropped rather than guessed at.
Read with the token on 2026-10-15 (robots.txt: 816 bytes, no rule matches the
file)."""

import re

from . import clean, norm_role, split_blocks

COUNTY_FIPS = "097"
COUNTY_NAME = "Portage"
SOURCES = ["https://www.co.portage.wi.gov/DocumentCenter/View/567/"
           "County-Directory-PDF"]

_ROW = re.compile(r"^(Chairperson|Chairman|Supervisor[^:]*):\s*(.+?)\s+"
                  r"\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("TOWN OFFICERS\nTOWN OF")
    if start < 0:
        raise RuntimeError("the TOWN OFFICERS pages were not found")
    section = text[start:]
    end = section.find("VILLAGE OFFICERS")
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
    # the cover prints "Updated 10-14-2026"
    m = re.search(r"Updated\s+(\d{1,2}-\d{1,2}-20\d\d)", text[:1500])
    return {"towns": towns,
            "edition": ("updated " + m.group(1)) if m else None}
