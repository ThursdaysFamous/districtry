"""Columbia County: the county clerk's 2026-2027 Official Directory (PDF).

Each town has its own page under a "TOWN OF <NAME>" heading. Each officer is
one line, "Town Board Chair – Name (telephone)" or "Supervisor 1 – Name
(telephone)", with the home address and an e-mail on the lines after it. The
number after the name ships on the officer (Adam, 2026-10-17;
`role_then_name`); the home address and the e-mail address are not read. The
towns run up to "VILLAGE OF ARLINGTON". Read with the token on 2026-10-15
(robots.txt: 218 bytes, no group binds this client)."""

import re

from . import clean, role_then_name, split_blocks

COUNTY_FIPS = "021"
COUNTY_NAME = "Columbia"
SOURCES = ["https://www.co.columbia.wi.us/ColumbiaCounty/Portals/2/"
           "CountyClerkFiles/Directory.pdf"]


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = re.search(r"(?m)^TOWN OF ARLINGTON\s*$", text)
    if not start:
        raise RuntimeError("the towns section was not found")
    end = re.search(r"(?m)^VILLAGE OF ", text[start.start():])
    section = text[start.start():start.start() + end.start()] if end else text[start.start():]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^TOWN OF ([A-Z .'\-]+?)\s*$"):
        people = role_then_name(block, stop_re=r"^(Clerk|Treasurer)\b")
        if people:
            towns[clean(town).title()] = people
    m = re.search(r"(\d{4}-\d{4})\s*\nOfficial Directory", text)
    return {"towns": towns, "edition": m.group(1) if m else None}
