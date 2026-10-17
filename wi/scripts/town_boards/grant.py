"""Grant County: the county clerk's 2026-2027 County Directory (PDF).

The section "Town, Village and City Officials" gives each town a page headed
"Town of <Name>", with one office per line in the form "Chairperson – <name>"
or "Supervisor – <name>" and the officer's telephone and e-mail on the line
below. The numbers on that line ship on the officer with the label the
directory prints (Adam, 2026-10-17; `role_then_name`), and so does the e-mail
address (Adam, 2026-10-17: "E-mails too"). Read with the token on 2026-10-15
(robots.txt: 134 bytes, no rule matches the file)."""

import re

from . import role_then_name, split_blocks

COUNTY_FIPS = "043"
COUNTY_NAME = "Grant"
SOURCES = ["https://gcinternetwebsite.co.grant.wi.gov/wp-content/uploads/"
           "simple-file-list/County-Clerk/2026-2027-Directory.pdf"]


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = text.find("Town, Village and City Officials")
    if start < 0:
        raise RuntimeError("the 'Town, Village and City Officials' section "
                           "was not found")
    section = text[start:]
    # the villages follow the towns; stop at the first village page
    end = re.search(r"(?m)^Village of ", section)
    if end:
        section = section[:end.start()]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^Town of ([A-Za-z .'\-]+?)\s*$"):
        people = role_then_name(block, stop_re=r"^(Clerk|Treasurer)\b")
        if people:
            towns[town] = people
    m = re.search(r"\b(20\d\d\s*-\s*20\d\d)\b", text[:3000])
    return {"towns": towns, "edition": m.group(1) if m else None}
