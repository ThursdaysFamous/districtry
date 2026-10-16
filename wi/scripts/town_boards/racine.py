"""Racine County: the county clerk's 2026 Official Directory of Public
Officials (PDF).

"TOWN BOARDS AND OTHER OFFICIALS" gives each town under a "TOWN OF <NAME>"
heading, then each office on a line of its own ("Town Chairperson",
"Supervisor No. 1", "Clerk") with the officer's name on the next line, a dot
leader and a telephone number after it, and then lines of address and e-mail,
which are never read. Each town's page ends with the county board supervisors
who represent it, which is a different office and is not read.

CLIENT. On 2026-10-15 this project's token got HTTP 403 Forbidden for the
document (the same answer the 2026-10-15 survey recorded); the Chrome client
was served the 959,762-byte PDF. robots.txt read as Chrome (6,641 bytes) has
no rule matching the document's path."""

import re

from . import looks_like_person, norm_role, split_blocks, strip_contact

COUNTY_FIPS = "101"
COUNTY_NAME = "Racine"
SOURCES = ["https://www.racinecounty.gov/home/showpublisheddocument/54564/"
           "639186061809670000"]
CLIENT = "chrome"  # token re-measured 2026-10-15 at SOURCES[0]: HTTP 403 Forbidden

_ROLE = re.compile(r"^(?:Town\s+)?(Chairperson|Chairman|"
                   r"Supervisor(?:\s+No\.\s*\d+)?)$")


def _people(block):
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    out = []
    for i, ln in enumerate(lines):
        if re.match(r"^COUNTY BOARD SUPERVISOR", ln):
            break
        m = _ROLE.match(ln)
        if not m or i + 1 >= len(lines):
            continue
        name = strip_contact(lines[i + 1])
        role = norm_role(m.group(1))
        if role and looks_like_person(name):
            out.append({"name": name, "role": role})
    return out


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("TOWN BOARDS AND OTHER OFFICIALS")
    if start < 0:
        raise RuntimeError("the 'TOWN BOARDS AND OTHER OFFICIALS' section "
                           "was not found")
    section = text[start:]
    end = section.find("VILLAGE BOARDS AND OFFICIALS")
    if end > 0:
        section = section[:end]
    towns = {}
    for town, block in split_blocks(section,
                                    r"(?m)^TOWN OF ([A-Z][A-Z .']+?)\s*$"):
        people = _people(block)
        if people:
            towns[town.title()] = people
    m = re.search(r"\b(20\d\d)\b", text[:100])
    return {"towns": towns, "edition": m.group(1) if m else None}
