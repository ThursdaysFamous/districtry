"""Taylor County: the county's "Towns" directory page (HTML).

One page lists every town under a "Town of <Name>" heading; each officer is a
line "Chairman Brian Phelps" or "Supervisor Earl Hinkel", followed by the
officer's telephone number and home address on lines of their own, and now
and then an e-mail address under those. The number line below the officer's
line ships, and so does the e-mail address (Adam, 2026-10-17: "E-mails too");
the address line is not read. The page prints no edition or date. Read with
the token on 2026-10-15 over https (robots.txt: 116 bytes, no rule matches the
page)."""

import re

from . import (clean, following_emails, following_phones, html_text,
               looks_like_person, norm_role, person, split_blocks)

COUNTY_FIPS = "119"
COUNTY_NAME = "Taylor"
SOURCES = ["https://co.taylor.wi.us/directory/towns/"]

_LINE = re.compile(r"^(Chair(?:man|person|woman)?|Supervisor(?:\s*#?\s*\d+)?)"
                   r"\s+(\S.*)$")


def scrape(ctx):
    text = html_text(ctx.fetch_text(SOURCES[0]))
    towns = {}
    for town, block in split_blocks(text, r"(?m)^Town of ([A-Za-z .'\-]+?)\s*$"):
        people = []
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        for i, ln in enumerate(lines):
            m = _LINE.match(ln)
            if not m:
                continue
            role, name = norm_role(m.group(1)), clean(m.group(2))
            if role and looks_like_person(name):
                # the e-mail line, where there is one, is under the address
                people.append(person(name, role, following_phones(
                    lines, i + 1, limit=2, stop_re=_LINE.pattern),
                    emails=following_emails(lines, i + 1, limit=3,
                                            stop_re=_LINE.pattern)))
        if people:
            towns[town] = people
    return {"towns": towns, "edition": None}
