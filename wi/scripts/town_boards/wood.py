"""Wood County: the County Clerk's Official Directory 2026-2027 (PDF).

The "TOWN OFFICIALS" pages give each town a "TOWN OF <NAME>" heading, then a
"CHAIRPERSON:" line and a "SUPERVISORS:" line (some marked "Numbered Seats").
Each officer's entry opens with "Name, street address" (a seat as "#1 Name,
..." where numbered), then a line of city, ZIP code and telephone, sometimes a
"Cell:" line, and often an e-mail line. Only the text before the first comma of
the opening line is read for the name; the city line is told apart by the ZIP
code right after its comma. The officer's numbers ship (Adam, 2026-10-17): the
one that ends the city line, read from the number onward only (`end_phones`),
so the street, city and ZIP code are never read, and any on the label lines
after it ("Cell: ..."), up to the next entry. The e-mail address on those
label lines ships too (Adam, 2026-10-17: "E-mails too"). Read with the token
on 2026-10-15 (robots.txt: HTTP 404, so no policy)."""

import re

from . import (end_phones, line_emails, looks_like_person, person,
               phone_line_numbers, split_blocks)

COUNTY_FIPS = "141"
COUNTY_NAME = "Wood"
SOURCES = ["https://woodcountywi.gov/Departments/Clerk/Doc/WoodCountyDirectory.pdf"]
MIN_TOWNS = 20

_ENTRY = re.compile(r"^(?:#\s*(\d+)\s+)?([^,]+),\s*(.*)$")
# the city line after an entry: "Arpin, 54410 715-...", "Wisconsin Rapids, WI 54494"
_CITY_REST = re.compile(r"^(WI\s+)?5[34]\d{3}(-\d{4})?\b")
# a line of an entry after its city line that holds a label and what it
# labels ("Cell: 715-...", "Email: ...")
_LABELLED = re.compile(r"(?i)^(?:cell|home|work|phone|e-?mail|fax)\b")


def _is_city(line):
    m = _ENTRY.match(line)
    return bool(m and _CITY_REST.match(m.group(3)))


def _numbers(lines, i):
    """The numbers of the entry that opens at lines[i]: the one ending its
    city line, then those on the label lines after it, up to the next entry
    or heading. Nothing else on those lines is read."""
    out = []
    j = i + 1
    if j < len(lines) and _is_city(lines[j]):
        out += end_phones(lines[j])
        j += 1
    while j < len(lines) and _LABELLED.match(lines[j]):
        out += phone_line_numbers(lines[j])
        j += 1
    return out


def _emails(lines, i):
    """The e-mail addresses on the label lines ("Email: ...") of the entry
    that opens at lines[i], the lines `_numbers` reads."""
    out = []
    j = i + 1
    if j < len(lines) and _is_city(lines[j]):
        j += 1
    while j < len(lines) and _LABELLED.match(lines[j]):
        out += line_emails(lines[j])
        j += 1
    return out


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
        lines = [raw.strip() for raw in block.split("\n")]
        for i, line in enumerate(lines):
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
            people.append(person(name, seat, _numbers(lines, i),
                                 emails=_emails(lines, i)))
            if role == "Chairperson":
                role = "_done"
        if people:
            towns[town.title()] = people
    m = re.search(r"OFFICIAL DIRECTORY\s*\n\s*(\d{4}-\d{4})", text)
    return {"towns": towns, "edition": m.group(1) if m else None}
