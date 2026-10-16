"""Marathon County: the county clerk's 2026-2027 Directory of Public Officials
(PDF).

Under "TOWN OFFICERS" each town is headed "TOWN OF <NAME>", and each office is
one line, "CHAIRMAN, <name> ..... <telephone>" or "SUPERVISOR, <name> .....
<telephone>", with the officer's home address on the line below.

CLIENT. Read with Chrome on 2026-10-15. The same day this project's token got
a plain HTTP 403 on both robots.txt and the document; read as Chrome,
robots.txt (6,641 bytes) has no rule matching the document's path, so it is
allowed."""

import re

from . import looks_like_person, norm_role, person, split_blocks, strip_contact

COUNTY_FIPS = "073"
COUNTY_NAME = "Marathon"
CLIENT = "chrome"  # token re-measured 2026-10-15 at SOURCES[0]: HTTP 403 Forbidden
SOURCES = ["https://www.marathoncounty.gov/home/showpublisheddocument/"
           "19337/639258567174130000"]

_ROW = re.compile(r"^(CHAIR\w*|SUPERVISOR(?:\s*#?\s*\d+)?)\s*,\s*(.+)$", re.I)
_CUT = re.compile(r"\s*(…|\.{2,}).*$")


def _officers(block):
    people = []
    for ln in block.split("\n"):
        m = _ROW.match(ln.strip())
        if not m:
            continue
        role = norm_role(m.group(1))
        name = strip_contact(_CUT.sub("", m.group(2)))
        if role and looks_like_person(name):
            people.append(person(name, role))
    return people


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("TOWN OFFICERS")
    if start < 0:
        raise RuntimeError("the 'TOWN OFFICERS' section was not found")
    section = text[start:]
    end = re.search(r"(?m)^(VILLAGE OFFICERS|VILLAGE OF |CITY OF )", section)
    if end:
        section = section[:end.start()]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^TOWN OF ([A-Z .'\-]+?)\s*$"):
        people = _officers(block)
        if people:
            towns[town.title()] = people
    m = re.search(r"\b(20\d\d\s*-\s*20\d\d)\b", text[:1000])
    return {"towns": towns, "edition": m.group(1) if m else None}
