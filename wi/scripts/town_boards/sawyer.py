"""Sawyer County: "Municipal Govt Contacts" and its per-town pages (partial).

The index page (/314/Municipal-Govt-Contacts) links a county page for six of
the sixteen towns (Couderay, Meadowbrook, Ojibwa, Radisson, Sand Lake,
Weirgor); the other ten link out to each town's own website, which this
module does not read. Each county town page lists one officer per line as
"<office> – <name>, <address> - <telephone>" ("Chairman – Jane Doe. 1234W
County Rd. ..."), or (Meadowbrook) the office and name on one line and the
address, a dot leader and the telephone on the next. The name is kept, and so
is the telephone number that ends the officer's line, or the one after the
leader on the line below, and the e-mail address that ends the officer's line
or stands on the line below; the address before it is not read. Read with the
token on 2026-10-15 (robots.txt: 816 bytes, no rule matches these paths)."""

import re
import urllib.parse

from . import (clean, end_phones, following_emails, following_phones,
               html_text, line_emails, looks_like_person, norm_role, person)

COUNTY_FIPS = "113"
COUNTY_NAME = "Sawyer"
SOURCES = ["https://www.sawyercounty.gov/314/Municipal-Govt-Contacts"]
MIN_TOWNS = 6
PARTIAL_NOTE = ("The county's town pages name the board for 6 of its 16 "
                "towns; the other 10 are linked to their own websites.")

_LINE = re.compile(r"^((?:town\s+)?(?:chair\w*|supervisor)"
                   r"(?:\s*#?\s*\d+|\s+[IVX]+\b)?)\s*[-–—:]\s*(.+)$", re.I)


def _name(rest):
    """The name is what comes before the first comma, or before a full stop
    that is followed by an address number ("Jane Doe. 1234W County Rd."), or
    before a " - " that leads to a telephone number. Returns the name and the
    rest of the line after it."""
    parts = re.split(r",|\.\s+(?=\S*\d)|\s+[-–—]\s*(?=\(?\d)", rest, maxsplit=1)
    return clean(parts[0]), (rest[len(parts[0]):] if len(parts) > 1 else "")


def scrape(ctx):
    index = ctx.fetch_text(SOURCES[0])
    links = {}
    for href, name in re.findall(
            r'<a [^>]*href="(/\d+/Town-of-[^"]+)"[^>]*>\s*Town of ([^<]+?)\s*</a>',
            index):
        links.setdefault(clean(name), urllib.parse.urljoin(SOURCES[0], href))
    if len(links) < MIN_TOWNS:
        raise RuntimeError("found %d county town pages on the index" % len(links))
    towns = {}
    for town, url in sorted(links.items()):
        text = html_text(ctx.fetch_text(url))
        head = "Town of %s\nTown of %s\n" % (town, town)
        start = text.find(head)
        if start < 0:
            continue
        people = []
        lines = [ln.strip() for ln in text[start + len(head):].split("\n")[:40]]
        for i, ln in enumerate(lines):
            m = _LINE.match(ln)
            if not m:
                continue
            role = norm_role(m.group(1))
            name, after = _name(m.group(2))
            if role and looks_like_person(name):
                phones = end_phones(after)
                phones += following_phones(lines, i + 1, limit=1)
                emails = line_emails(after)
                emails += following_emails(lines, i + 1, limit=1)
                people.append(person(name, role, phones, emails=emails))
        if people:
            towns[town] = people
    return {"towns": towns, "edition": None}
