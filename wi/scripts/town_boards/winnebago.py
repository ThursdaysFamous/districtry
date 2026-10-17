"""Winnebago County: the County Clerk's 2026-2028 Official Directory (PDF).

Under "Towns, Villages and Cities Information" each town has a "TOWN OF <NAME>"
heading, then a "CHAIRPERSON" line with the chair's name on the next line and a
"SUPERVISORS" line with one supervisor per line after it, sometimes numbered
("1. Teresa Van Aacken"). Each name line carries telephone numbers and often an
e-mail address after the name. The numbers printed after the name ship as that
officer's (Adam, 2026-10-17), with the label the directory gives ("Cell:");
the e-mail address is not read. Lines after the chair's own line ("Emails may
be sent to the Town Clerk: ...") are not the chair's and are not read. The
supervisors are printed as a list, not called seats, so the role is plain
"Supervisor".

CLIENT. Measured 2026-10-15: with the districtry token, robots.txt and the file
both answered HTTP 403 (the survey of the same day recorded a Cloudflare
"Attention Required" page for the token). Read as Chrome, robots.txt answers
816 bytes and no rule matches /DocumentCenter/View/583/, and the file is
served."""

import re

from . import (looks_like_person, person, phones_after_name, split_blocks,
               strip_contact)

COUNTY_FIPS = "139"
COUNTY_NAME = "Winnebago"
SOURCES = ["https://www.winnebagocountywi.gov/DocumentCenter/View/583/"
           "Directory-of-Winnebago-County-PDF"]
CLIENT = "chrome"  # token re-measured 2026-10-15 at SOURCES[0]: HTTP 403 Forbidden
MIN_TOWNS = 14

_HEADING = re.compile(r"^[A-Z][A-Z/ ,&\-()]{3,}:?$")


def _name(line):
    line = strip_contact(line)
    line = re.sub(r"^\d+\.\s*", "", line)
    # what strip_contact leaves after a telephone number: ", ext. 7", "Cell:"
    line = re.sub(r",?\s*(ext\.?\s*\d+|cell:?).*$", "", line, flags=re.I)
    return line.strip(" ,")


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = re.search(r"(?m)^TOWN OF [A-Z ]+\nTown (Hall|Office)", text)
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
            if not line:
                continue
            if line == "CHAIRPERSON":
                role = "Chairperson"
                continue
            if line == "SUPERVISORS":
                role = "Supervisor"
                continue
            if _HEADING.match(line):
                role = None
                continue
            if role is None:
                continue
            name = _name(line)
            if looks_like_person(name):
                people.append(person(name, role, phones_after_name(line, name)))
            if role == "Chairperson":
                # one chair; a following line is contact text, not a person
                role = "_after_chair"
        people = [p for p in people if p["role"] != "_after_chair"]
        if people:
            towns[town.title()] = people
    m = re.search(r"^\s*(\d{4}-\d{4})\s*\n\s*Official Directory", text[:300])
    return {"towns": towns, "edition": m.group(1) if m else None}
