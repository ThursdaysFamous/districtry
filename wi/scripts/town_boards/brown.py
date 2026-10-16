"""Brown County: the county clerk's 2026-2027 Brown County Directory (PDF,
file dated 09-10-26).

The "TOWNS" section lists each town under a "TOWN OF <NAME>" heading (repeated
with "ELECTED OFFICIALS" or "STAFF" when a town runs over a page), and each
office on one line as "Chairman ........ NAME", with the officer's address,
telephone and e-mail on the dotted lines after it. Only the role line is read.
The section ends at "ONEIDA NATION". Read with the token on 2026-10-15
(robots.txt served empty, allow all)."""

import re

from . import clean, looks_like_person, norm_role, person

COUNTY_FIPS = "009"
COUNTY_NAME = "Brown"
SOURCES = ["https://www.browncountywi.gov/i/f/files/County-Clerk/Directory/"
           "2026-27%20%20BROWN%20COUNTY%20DIRECTORY%2009-10-26%20.pdf"]

_HEAD = re.compile(r"^TOWN OF ([A-Z .'\-]+?)(?:\s+(?:STAFF|ELECTED OFFICIALS))?\s*$")
_ROLE = re.compile(r"^((?:Chair\w*|Supervisor)(?:\s*(?:No\.?|#)\s*\d+)?)"
                   r"\s*\.?\s*\.{2,}\s*(.+)$", re.I)


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = re.search(r"(?m)^TOWNS\s*\nTOWN OF ", text)
    if not start:
        raise RuntimeError("the TOWNS section was not found")
    end = text.find("ONEIDA NATION", start.end())
    section = text[start.start():end if end > 0 else len(text)]
    towns = {}
    town = None
    for ln in section.split("\n"):
        ln = ln.strip()
        m = _HEAD.match(ln)
        if m:
            town = clean(m.group(1)).title()
            continue
        m = _ROLE.match(ln)
        if not (m and town):
            continue
        role = norm_role(m.group(1))
        name = clean(m.group(2).strip(". …"))
        if role and looks_like_person(name):
            towns.setdefault(town, []).append(person(name, role))
    m = re.search(r"(\d{4}-\d{4}) BROWN COUNTY DIRECTORY", text)
    return {"towns": towns, "edition": m.group(1) if m else None}
