"""Pierce County: the county's 2026 Official Directory (PDF).

Its MUNICIPAL GOVERNMENT pages give each town under a "TOWN of <NAME>" heading,
then each office as an upper-case heading on its own line (CHAIRPERSON,
SUPERVISORS, CLERK, ...). Each officer under it is a line "Name (e-mail) ......
phone" followed by a line of home address, which often ends in a second number
("... Cell: (715) 555-0100"). Only the lines with a dot leader under the
CHAIRPERSON and SUPERVISORS headings are used. The name is the text before the
leader, with the e-mail in brackets taken off; the number after the leader
ships, and so does a number at the end of the address line below when a label
naming a person's line ("Cell:", "Home:") stands before it. The address itself
is not read. The page's "COUNTY BOARD SUPERVISOR" heading is a different office
and ends the board. Read with the token on 2026-10-15 (robots.txt on
cms5.revize.com: 312 bytes, "Allow: /*.pdf$")."""

import re

from . import (clean, following_phones, person, phones_after_name,
               split_blocks)

COUNTY_FIPS = "093"
COUNTY_NAME = "Pierce"
SOURCES = ["https://cms5.revize.com/revize/piercewi/Agendas%20and%20Minutes/"
           "Government/Board%20of%20Supervisor/2026%20Directory_Pierce%20County.pdf"]

_LEADER = re.compile(r"\s*(\.{2,}|…+).*$")


_HEADING = r"^[A-Z][A-Z /&'.,()-]+$"


def _people(block):
    out = []
    role = None
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    for i, line in enumerate(lines):
        if re.fullmatch(_HEADING, line):
            role = {"CHAIRPERSON": "Chairperson", "CHAIRMAN": "Chairperson",
                    "SUPERVISORS": "Supervisor",
                    "SUPERVISOR": "Supervisor"}.get(line)
            continue
        if role and _LEADER.search(line):
            name = _LEADER.sub("", line)
            name = clean(re.sub(r"\([^)]*@[^)]*\)", " ", name))
            if name:
                phones = phones_after_name(line, name)
                phones += following_phones(lines, i + 1, limit=2,
                                           stop_re=_HEADING)
                out.append(person(name, role, phones))
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
