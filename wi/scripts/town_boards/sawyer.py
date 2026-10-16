"""Sawyer County: "Municipal Govt Contacts" and its per-town pages (partial).

The index page (/314/Municipal-Govt-Contacts) links a county page for six of
the sixteen towns (Couderay, Meadowbrook, Ojibwa, Radisson, Sand Lake,
Weirgor); the other ten link out to each town's own website, which this
module does not read. Each county town page lists one officer per line as
"<office> – <name>, <address> - <telephone>" ("Chairman – James Bassett.
12353W Chafer Rd. ..."); only the name is kept. Read with the token on
2026-10-15 (robots.txt: 816 bytes, no rule matches these paths)."""

import re
import urllib.parse

from . import clean, html_text, looks_like_person, norm_role, person

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
    that is followed by an address number ("James Bassett. 12353W Chafer
    Rd."), or before a " - " that leads to a telephone number."""
    rest = re.split(r",|\.\s+(?=\S*\d)|\s+[-–—]\s*(?=\(?\d)", rest, maxsplit=1)[0]
    return clean(rest)


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
        for ln in text[start + len(head):].split("\n")[:40]:
            m = _LINE.match(ln.strip())
            if not m:
                continue
            role = norm_role(m.group(1))
            name = _name(m.group(2))
            if role and looks_like_person(name):
                people.append(person(name, role))
        if people:
            towns[town] = people
    return {"towns": towns, "edition": None}
