"""Wood County: the County Clerk's Official Directory 2026-2027 (PDF).

The "TOWN OFFICIALS" pages give each town a "TOWN OF <NAME>" heading, then a
"CHAIRPERSON:" line and a "SUPERVISORS:" line (some marked "Numbered Seats").
Each officer's entry opens with "Name, street address" (a seat as "#1 Name,
..." where numbered), then a line of city, ZIP code and telephone and often an
e-mail line. Only the text before the first comma of the opening line is read;
the city line is told apart by the ZIP code right after its comma. Read with the
token on 2026-10-15 (robots.txt: HTTP 404, so no policy)."""

import re

from . import looks_like_person, person, split_blocks

COUNTY_FIPS = "141"
COUNTY_NAME = "Wood"
SOURCES = ["https://woodcountywi.gov/Departments/Clerk/Doc/WoodCountyDirectory.pdf"]
MIN_TOWNS = 20

_ENTRY = re.compile(r"^(?:#\s*(\d+)\s+)?([^,]+),\s*(.*)$")
# the city line after an entry: "Arpin, 54410 715-...", "Wisconsin Rapids, WI 54494"
_CITY_REST = re.compile(r"^(WI\s+)?5[34]\d{3}(-\d{4})?\b")


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = re.search(r"(?m)^TOWN OF [A-Z ]+$", text)
    if not start:
        raise RuntimeError("the town section was not found")
    end = re.search(r"(?m)^(VILLAGE|CITY) OF ", text[start.start():])
    section = text[start.start():start.start() + end.start()] if end \
        else text[start.start():]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^TOWN OF ([A-Z .'\-]+?)\s*$"):
        people = []
        role = None
        for raw in block.split("\n"):
            line = raw.strip()
            if re.match(r"^CHAIRPERSON\b", line):
                role = "Chairperson"
                continue
            if re.match(r"^SUPERVISORS?\b", line):
                role = "Supervisor"
                continue
            if re.match(r"^[A-Z][A-Z ]{2,}\s*(\(.*\))?\s*:", line):
                role = None            # CLERK:, TREASURER:, ASSESSOR: ...
                continue
            if role is None:
                continue
            m = _ENTRY.match(line)
            if not m or _CITY_REST.match(m.group(3)) or line.lower().startswith("email"):
                continue
            name = m.group(2).strip()
            if not looks_like_person(name):
                continue
            seat = role
            if role == "Supervisor" and m.group(1):
                seat = "Supervisor #" + m.group(1)
            people.append(person(name, seat))
            if role == "Chairperson":
                role = "_done"
        if people:
            towns[town.title()] = people
    m = re.search(r"OFFICIAL DIRECTORY\s*\n\s*(\d{4}-\d{4})", text)
    return {"towns": towns, "edition": m.group(1) if m else None}
