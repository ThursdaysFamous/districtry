"""Washington County: the county's 2026 Washington County Directory (PDF).

Under "TOWNS, VILLAGES, AND CITIES" each town has a "TOWN OF <NAME>" heading,
then one line per officer in the form "Chairperson, Robert Bingen" or
"Supervisor #1, Jeff Infalt", each followed by a line carrying that person's
address and telephone number, which is not read. The towns come first and the
villages follow. Read with the token on 2026-10-15: www.washcowisco.gov's
robots.txt (339 bytes) has no rule matching the file, and the request is
redirected to cdnsm5-hosted.civiclive.com, whose robots.txt answers 403, which
RFC 9309 reads as no policy (allow)."""

import re

from . import looks_like_person, norm_role, person, split_blocks, strip_contact

COUNTY_FIPS = "131"
COUNTY_NAME = "Washington"
SOURCES = ["https://www.washcowisco.gov/UserFiles/Servers/Server_16227954/"
           "Image/2026%20Washington%20County%20Directory.pdf"]
MIN_TOWNS = 11

# "Chairperson, Name" or "Supervisor #2, Name"; "Plan Comm Chr." and the like
# do not match because the line must open with the role word
_ROLE_LINE = re.compile(r"^(Chairperson|Supervisor(?:\s*#\s*\d+)?)\s*,\s*(.+)$")


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("TOWNS, VILLAGES, AND CITIES")
    if start < 0:
        raise RuntimeError("the 'TOWNS, VILLAGES, AND CITIES' section was not found")
    end = re.search(r"(?m)^(VILLAGE|CITY) OF ", text[start:])
    section = text[start:start + end.start()] if end else text[start:]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^TOWN OF ([A-Z .'\-]+?)\s*$"):
        people = []
        for line in block.split("\n"):
            m = _ROLE_LINE.match(line.strip())
            if not m:
                continue
            role = norm_role(m.group(1))
            name = strip_contact(m.group(2))
            if role and looks_like_person(name):
                people.append(person(name, role))
        if people:
            towns[town.title()] = people
    m = re.search(r"DIRECTORY\s*\n\s*(\d{4})\b", text[:400])
    return {"towns": towns, "edition": m.group(1) if m else None}
