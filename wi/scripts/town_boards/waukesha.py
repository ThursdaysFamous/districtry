"""Waukesha County: the County Clerk's 2026 Directory of Public Officials (PDF).

Each town has its own page headed "Town of <Name>", listing each office on a
line of its own ("Chairperson", "Supervisor") with the officer's name on the
next line, followed on that line by a telephone number or e-mail address, which
are taken off. Some towns print a home address on a further line, which is not
read. Read with the token on 2026-10-15 (robots.txt: 188 bytes, no rule matches
the file)."""

import re

from . import role_then_name, split_blocks

COUNTY_FIPS = "133"
COUNTY_NAME = "Waukesha"
SOURCES = ["https://www.waukeshacounty.gov/media/vcmhmesm/2026-directory-final.pdf"]
MIN_TOWNS = 8


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    towns = {}
    # the table of contents prints "Town of Brookfield – page 20", which the
    # end-of-line anchor leaves out; the town pages print the name alone
    for town, block in split_blocks(text, r"(?m)^Town of ([A-Z][A-Za-z .'\-]+?)\s*$"):
        stop = re.search(r"(?m)^(Village|City) of ", block)
        if stop:
            block = block[:stop.start()]
        people = role_then_name(block, stop_re=r"^(Municipal Judge|Clerk|Treasurer)\b")
        if people:
            towns[town] = people
    m = re.search(r"(\d{4}) Directory of Public", text[:600])
    return {"towns": towns, "edition": m.group(1) if m else None}
