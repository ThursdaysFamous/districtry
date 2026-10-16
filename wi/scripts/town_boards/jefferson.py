"""Jefferson County: the county clerk's County Directory (PDF).

Each town has a page headed "TOWN OF <NAME>". Every officer is a small block
laid out in two columns: the officer's name and "PH: <telephone>" on the first
line (or the name alone with the telephone on the next line), and the office
("Chair", "Supervisor", "Supervisor 2", "Clerk"...) in a left-hand column at
the start of a following line, beside the officer's home address. The
county-board members who represent the town follow at the foot of the page
and carry no "PH:" line. Read with the token on 2026-10-15 (the file is
served from cms4files.revize.com, whose robots.txt allows /*.pdf$; the county
host has no robots.txt)."""

import re

from . import looks_like_person, norm_role, person, split_blocks, strip_contact

COUNTY_FIPS = "055"
COUNTY_NAME = "Jefferson"
SOURCES = ["https://jeffersoncountywi.gov/County%20Clerk/"
           "JeffersonCountyDirectory.pdf"]

_ROLE = re.compile(r"^(Chair\w*|Vice\s+Chair\w*|Supervisor|Supv\.?)"
                   r"(?:\s+(#?\d+|[IVX]+)(?=\s|$))?\s*(.*)$", re.I)
_STREET = re.compile(r"^([NWES]\d|\d|P\.?\s?O\.?\s+Box\b)", re.I)
_FOOT = re.compile(r"Districts:|^County\b|Population:", re.I | re.M)


def _name_part(line):
    """The text of a line before its "PH:" telephone, e-mail and address."""
    return strip_contact(re.split(r"PH:", line)[0])


def _officers(block):
    # the county-board members and district numbers at the foot of the page
    # are not the town board
    foot = _FOOT.search(block)
    if foot:
        block = block[:foot.start()]
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    people = []
    for i, ln in enumerate(lines):
        m = _ROLE.match(ln)
        if not m:
            continue
        label = m.group(1) + (" " + m.group(2) if m.group(2) else "")
        role = norm_role(label)
        if not role:
            continue
        # the name sits after the office on the same line ("Chair Barry Boos
        # PH: ..."), or above it on the line that carries "PH:" ("Kyle Kulow
        # PH: ..." / "Chair N7154 ..."), sometimes with a street line between
        # the two; when that line is the telephone alone the name is one line
        # higher still. A name with no telephone stands directly above.
        name = _name_part(m.group(3))
        if not looks_like_person(name):
            name = ""
            j = i - 1
            while j >= 0 and j >= i - 3 and _STREET.match(lines[j]):
                j -= 1
            if j >= 0 and not _ROLE.match(lines[j]):
                prev = lines[j]
                if "PH:" in prev:
                    name = _name_part(prev)
                    if not name and prev.startswith("PH:") and j > 0:
                        name = _name_part(lines[j - 1])
                elif j == i - 1:
                    name = _name_part(prev)
        if looks_like_person(name):
            people.append(person(name, role))
    return people


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
        people = _officers(block)
        if people:
            towns[town.title()] = people
    m = re.search(r"Revised\s+(\d{1,2}/\d{1,2}/\d{4})", text)
    return {"towns": towns, "edition": "revised " + m.group(1) if m else None}
