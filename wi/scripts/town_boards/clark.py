"""Clark County: the county clerk's Official Directory 2026-2027 (PDF).

"OFFICIALS OF THE MUNICIPALITIES / Clark County Towns" lists each town under a
"TOWN OF <NAME>" heading, then each office on its own line with the officer's
name on the next, and the officer's telephone numbers after the name or on the
lines below it. Those numbers ship on the officer (Adam, 2026-10-17;
`role_then_name`), with the label the directory prints, and so does an e-mail
address printed there (Adam, 2026-10-17: "E-mails too"); an address is not
read. Read with the token on 2026-10-15 (robots.txt: 495 bytes, Allow: /)."""

import re

from . import role_then_name, split_blocks

COUNTY_FIPS = "019"
COUNTY_NAME = "Clark"
SOURCES = ["https://www.clarkcountywi.gov/_files/ugd/"
           "02a99f_c46d29ba61a748bf9c2bafa592d7461c.pdf"]


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("Clark County Towns")
    if start < 0:
        raise RuntimeError("the 'Clark County Towns' section was not found")
    # the villages and cities follow the towns; stop at their section
    end = re.search(r"Clark County (Villages|Cities)", text[start:])
    section = text[start:start + end.start()] if end else text[start:]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^\d*TOWN OF ([A-Z .'\-]+?)\s*$"):
        people = role_then_name(block, stop_re=r"^Clerk\b")
        if people:
            towns[town.title()] = people
    # the cover prints the years above the title: "2026-2027 / OFFICIAL DIRECTORY"
    m = re.search(r"(\d{4}\s*-\s*\d{4})\s*\n\s*OFFICIAL DIRECTORY", text, re.I)
    return {"towns": towns, "edition": m.group(1) if m else None}
