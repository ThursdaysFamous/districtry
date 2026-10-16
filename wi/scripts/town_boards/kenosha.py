"""Kenosha County: the county clerk's 2026-2027 Directory of Public Officials
(PDF; the county's "County Directory PDF" page redirects to the file at
DocumentCenter/View/14781 on the same host).

Each town has a page headed "TOWN OF <NAME>" giving the town hall, then each
office as a heading line ("Chairperson", "Chairman", "Supervisor",
"Supervisor #1") with the holder's name, a dot leader and a telephone on the
next line. The county-board members for the town follow under "County Board
Supervisor(s)" and are not read.

CLIENT. Read with Chrome on 2026-10-15. The same day this project's token got
a Cloudflare "Attention Required" page with HTTP 403 on both robots.txt and the
directory; read as Chrome, robots.txt (816 bytes) has no rule matching the
directory page, so it is allowed; the redirect stays on the same host."""

import re

from . import role_then_name, split_blocks

COUNTY_FIPS = "059"
COUNTY_NAME = "Kenosha"
CLIENT = "chrome"  # token re-measured 2026-10-15 at SOURCES[0]: HTTP 403 Forbidden
SOURCES = ["https://www.kenoshacountywi.gov/1018/County-Directory-PDF"]


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
        people = role_then_name(block, stop_re=r"^County Board Supervisor")
        if people:
            towns[town.title()] = people
    m = re.search(r"\b(20\d\d\s*-\s*20\d\d)\b", text[:500])
    return {"towns": towns, "edition": m.group(1) if m else None}
