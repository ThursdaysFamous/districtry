"""Waupaca County: the County Clerk's Directory of Public Officials (HTML page).

The page's "Town Officials" section has a "TOWN OF <NAME>" heading per town,
then each office on a line of its own ("Chair", "Supervisor 1", sometimes with
a second duty after a slash, "Supervisor 2/Animal Control") with the officer's
name on the next line, followed by a home address, a "Phone" line with the
telephone number below it and an "Email" line. The telephone number ships (a
number under a "Fax" line does not), and so does the e-mail address (Adam,
2026-10-17: "E-mails too"); the home address is not read. Fremont prints its
two supervisors as
"East Side Supervisor" and "West Side Supervisor", kept as "Supervisor (East
Side)". Read with the token on 2026-10-15
(robots.txt: HTTP 404, so no policy). The page prints "Directory of Public
Officials 2026" and "Directory updated" with a date."""

import re

from . import (following_emails, following_phones, html_text,
               looks_like_person, person, split_blocks, strip_contact)

COUNTY_FIPS = "135"
COUNTY_NAME = "Waupaca"
SOURCES = ["https://public4.co.waupaca.wi.us/CountyDirectory"]
MIN_TOWNS = 20


# a role line: "Chair", "Supervisor 1", "Supervisor 2/Animal Control",
# "Chair/Animal Control", "East Side Supervisor"; the duty after a slash is
# not part of the role
_ROLE = re.compile(r"^(?:(East|West|North|South) Side )?(Chair|Supervisor)"
                   r"(?:\s+(\d+))?\s*(?:/.*)?$")


def _board(block):
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    people = []
    for i, line in enumerate(lines[:-1]):
        m = _ROLE.match(line)
        if not m:
            continue
        if m.group(2) == "Chair":
            role = "Chairperson"
        else:
            role = "Supervisor"
            if m.group(3):
                role += " " + m.group(3)
            elif m.group(1):
                role += " (%s Side)" % m.group(1)
        name = strip_contact(lines[i + 1])
        if looks_like_person(name):
            people.append(person(name, role, following_phones(
                lines, i + 2, limit=8, stop_re=_ROLE.pattern),
                emails=following_emails(lines, i + 2, limit=8,
                                        stop_re=_ROLE.pattern)))
    return people


def scrape(ctx):
    text = html_text(ctx.fetch_text(SOURCES[0]))
    start = text.find("TOWN OF ")
    end = text.find("Village Officials", start)
    if start < 0 or end < 0:
        raise RuntimeError("the town section was not found")
    section = text[start:end]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^TOWN OF ([A-Z .'\-]+?)\s*$"):
        people = _board(block)
        if people:
            towns[town.title()] = people
    m = re.search(r"Directory updated\s*\n\s*([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    t = re.search(r"Directory of Public Officials (\d{4})", text)
    edition = None
    if t:
        edition = t.group(1) + (", updated " + m.group(1) if m else "")
    return {"towns": towns, "edition": edition}
