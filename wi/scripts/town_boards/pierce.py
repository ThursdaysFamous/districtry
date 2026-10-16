"""Pierce County: the county's 2026 Official Directory (PDF).

Its MUNICIPAL GOVERNMENT pages give each town under a "TOWN of <NAME>" heading,
then each office as an upper-case heading on its own line (CHAIRPERSON,
SUPERVISORS, CLERK, ...). Each officer under it is a line "Name (e-mail) ......
phone" followed by a line of home address, which is never read. Only the lines
with a dot leader under the CHAIRPERSON and SUPERVISORS headings are used, with
the e-mail in brackets and everything after the leader taken off. The page's
"COUNTY BOARD SUPERVISOR" heading is a different office and ends the board.
Read with the token on 2026-10-15 (robots.txt on cms5.revize.com: 312 bytes,
"Allow: /*.pdf$")."""

import re

from . import clean, split_blocks

COUNTY_FIPS = "093"
COUNTY_NAME = "Pierce"
SOURCES = ["https://cms5.revize.com/revize/piercewi/Agendas%20and%20Minutes/"
           "Government/Board%20of%20Supervisor/2026%20Directory_Pierce%20County.pdf"]

_LEADER = re.compile(r"\s*(\.{2,}|…+).*$")


def _people(block):
    out = []
    role = None
    for line in block.split("\n"):
        line = line.strip()
        if re.fullmatch(r"[A-Z][A-Z /&'.,()-]+", line):
            role = {"CHAIRPERSON": "Chairperson", "CHAIRMAN": "Chairperson",
                    "SUPERVISORS": "Supervisor",
                    "SUPERVISOR": "Supervisor"}.get(line)
            continue
        if role and _LEADER.search(line):
            name = _LEADER.sub("", line)
            name = clean(re.sub(r"\([^)]*@[^)]*\)", " ", name))
            if name:
                out.append({"name": name, "role": role})
    return out


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("MUNICIPAL GOVERNMENT\nTOWN of")
    if start < 0:
        raise RuntimeError("the MUNICIPAL GOVERNMENT town pages were not found")
    section = text[start:]
    end = re.search(r"(?m)^(VILLAGE|CITY) of ", section)
    if end:
        section = section[:end.start()]
    towns = {}
    for town, block in split_blocks(section,
                                    r"(?m)^TOWN of ([A-Z][A-Z .']+?)\s*$"):
        people = _people(block)
        if people:
            towns[town.title()] = people
    m = re.search(r"\b(20\d\d)\b", text[:200])
    return {"towns": towns, "edition": m.group(1) if m else None}
