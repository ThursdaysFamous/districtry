"""Burnett County: the county's Directory, June 2026 (revised 05/21/2026),
PDF.

Each town is under a "TOWN OF <NAME>" heading; each office is a line of its own
("Chairman", "Supervisor", "Clerk (appointed)") with the officer's name and a
dotted leader to a telephone number on the next line, then the address and
e-mail. The number after the leader, and any on the lines below it up to the
next office, ship on the officer (Adam, 2026-10-17; `role_then_name`); the
address and the e-mail address are not read. The towns are followed by
"VILLAGE OF GRANTSBURG". One supervisor entry
in Blaine is printed twice across a page break, so repeated entries are
dropped. Read with the token on 2026-10-15 (robots.txt: 816 bytes, no rule
matches the document's path)."""

import re

from . import clean, role_then_name, split_blocks

COUNTY_FIPS = "013"
COUNTY_NAME = "Burnett"
SOURCES = ["https://burnettcountywi.gov/DocumentCenter/View/18333/"
           "Directory-with-cover---2026---NEWEST-single-view-revised-052126"]


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = re.search(r"(?m)^TOWN OF ANDERSON\s*$", text)
    if not start:
        raise RuntimeError("the towns section was not found")
    end = re.search(r"(?m)^VILLAGE OF ", text[start.start():])
    section = text[start.start():start.start() + end.start()] if end else text[start.start():]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^TOWN OF ([A-Za-z .'\-]+?)\s*$"):
        seen, people = set(), []
        for p in role_then_name(block, stop_re=r"^Clerk\b|^Treasurer\b"):
            # a leader set in ellipsis characters is not taken off by
            # strip_contact, which knows only full stops
            p["name"] = clean(re.sub(r"\s*[\u2026.]{2,}.*$", "", p["name"]))
            key = (p["name"].lower(), p["role"])
            if key not in seen:
                seen.add(key)
                people.append(p)
        if people:
            town = clean(town)
            towns[town.title() if re.search(r"[A-Z]{3}", town) else town] = people
    m = re.search(r"\(Revised (\d{2}/\d{2}/\d{4})\)", text)
    return {"towns": towns,
            "edition": ("June 2026, revised " + m.group(1)) if m else None}
