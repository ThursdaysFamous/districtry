"""Manitowoc County: the county clerk's 2025-2026 Official Directory (PDF).

This is the edition the survey of 2026-10-15 found on the county's site; a
2026-2027 edition, when it is posted, will need its own url here. Each town is headed "TOWN OF <NAME>", followed by the town
hall's details and then one office per line, "Chairperson <name> ....
(telephone)" or "Supervisor <name> .... (telephone)", with the officer's home
address on the next line. Read with the token on 2026-10-15 (robots.txt: 192
bytes, no rule matches the file)."""

import re

from . import role_then_name, split_blocks

COUNTY_FIPS = "071"
COUNTY_NAME = "Manitowoc"
SOURCES = ["https://manitowoccountywi.gov/wp-content/uploads/2025/10/"
           "2025-2026-Directory.pdf"]


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    first = re.search(r"(?m)^TOWN OF [A-Z]", text)
    if not first:
        raise RuntimeError("no 'TOWN OF' page was found")
    section = text[first.start():]
    end = re.search(r"(?m)^(VILLAGE|CITY) OF ", section)
    if end:
        section = section[:end.start()]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^TOWN OF ([A-Z .'\-]+?)\s*$"):
        people = role_then_name(block)
        if people:
            towns[town.title()] = people
    # the edition is printed only on the cover, where the text layer holds it
    # mirrored ("6202-5202" for 2025-2026), so it is read back to front
    edition = None
    for raw in re.findall(r"\b\d{4}-\d{4}\b", text[:400]):
        flipped = raw[::-1]
        if re.match(r"^20\d\d-20\d\d$", flipped):
            edition = flipped
            break
    return {"towns": towns, "edition": edition}
