"""Vernon County: the county clerk's Official Directory 2026-2027, First
Edition (PDF).

"TOWN OFFICIALS" lists each town under a "TOWN OF <NAME>" heading; each office
is one dot-leader line, "Chair.......... Jeff Cermak" or "Supervisor No. 1
........ Jeff Benson", followed by a line with the home address and telephone
number ("... WI 54665 608-555-0100"), and sometimes a line of e-mail address
and a second number. The number that ends the address line is read on its own
and ships, and so does the number on an e-mail line below it. The e-mail
address on that line ships too (Adam, 2026-10-17: "E-mails too"); the address
is not read. Read with the token on 2026-10-15; the
county's link redirects to cms8.revize.com, whose robots.txt (312 bytes)
allows *.pdf."""

import re

from . import (OTHER_OFFICE, clean, end_phones, following_emails,
               following_phones, looks_like_person, norm_role, person,
               split_blocks)

COUNTY_FIPS = "123"
COUNTY_NAME = "Vernon"
SOURCES = ["https://www.vernoncountywi.gov/County%20Clerk/Directory.pdf"]

_LINE = re.compile(r"^(Chair\w*|Supervisor(?:\s*No\.?\s*\d+|\s*#?\s*\d+)?)"
                   r"\s*[.…]{2,}[\s.…]*([^.…\s].*)$")


def scrape(ctx):
    text = ctx.pdf_text(SOURCES[0])
    start = re.search(r"(?m)^TOWN OFFICIALS\s*$", text)
    end = re.search(r"(?m)^VILLAGE OFFICIALS", text)
    if not start or not end:
        raise RuntimeError("the TOWN OFFICIALS section was not found")
    section = text[start.end():end.start()]
    towns = {}
    for town, block in split_blocks(section, r"(?m)^TOWN OF ([A-Z .'\-]+?)\s*$"):
        people = []
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        for i, ln in enumerate(lines):
            m = _LINE.match(ln)
            if not m:
                continue
            role, name = norm_role(m.group(1)), clean(m.group(2))
            if role and looks_like_person(name):
                phones, emails = [], []
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                if nxt and not (_LINE.match(nxt) or OTHER_OFFICE.search(nxt)):
                    # the officer's own address line: only the number that
                    # ends it is read
                    phones = end_phones(nxt)
                    phones += following_phones(lines, i + 2, limit=1,
                                               stop_re=_LINE.pattern)
                    emails = following_emails(lines, i + 2, limit=1,
                                              stop_re=_LINE.pattern)
                people.append(person(name, role, phones, emails=emails))
        if people:
            towns[town.title()] = people
    ed = re.search(r"Official Directory\s*\n\s*(\d{4}\s*-\s*\d{4})\s*\n\s*"
                   r"(\w+ Edition)?", text)
    edition = " ".join(x for x in ed.groups() if x) if ed else None
    return {"towns": towns, "edition": edition}
