"""Oconto County: the "Town Board" pages under Municipalities (partial).

The Municipalities page (/474/Municipalities) carries the site's whole menu,
which links a "Town Board" page for only two of the county's 23 towns: Bagley
(/481/Town-Board) and Riverview (/502/Town-Board). Every other town page gives
the clerk's contact and nothing on the board. Each Town Board page has a
"Members" list, one member per line as "<name>, <office> (Voting Member)"
(Bagley) or "<name> - <office>" (Riverview); telephone and e-mail lines are
not kept. The town is read from the page's breadcrumb. Read with the token on
2026-10-15 (robots.txt: 816 bytes, no rule matches these paths)."""

import re
import urllib.parse

from . import clean, html_text, looks_like_person, norm_role, person

COUNTY_FIPS = "083"
COUNTY_NAME = "Oconto"
SOURCES = ["https://www.ocontocountywi.gov/474/Municipalities"]
MIN_TOWNS = 2
PARTIAL_NOTE = ("The county's town pages name the board for 2 of its 23 "
                "towns, Bagley and Riverview.")

_LINE = re.compile(r"^(.+?)\s*(?:,|\s[-–—])\s*((?:town\s+)?(?:chair\w*|supervisor)"
                   r"(?:\s*#?\s*\d+|\s+[IVX]+\b)?)\b(.*)$", re.I)


def scrape(ctx):
    index = ctx.fetch_text(SOURCES[0])
    hrefs = sorted(set(re.findall(r'<a [^>]*href="(/\d+/Town-Board)"', index)))
    if len(hrefs) < MIN_TOWNS:
        raise RuntimeError("found %d Town Board pages in the menu" % len(hrefs))
    towns = {}
    for href in hrefs:
        page = ctx.fetch_text(urllib.parse.urljoin(SOURCES[0], href))
        crumbs = re.findall(r'class="breadCrumb"[^>]*>\s*Town of ([^<]+?)\s*</a>',
                            page)
        if len(set(crumbs)) != 1:
            continue
        town = clean(crumbs[0])
        text = html_text(page)
        start = text.find("\nMembers\n")
        if start < 0:
            continue
        people = []
        for ln in text[start:].split("\n")[:30]:
            m = _LINE.match(ln.strip())
            if not m:
                continue
            role = norm_role(m.group(2))
            name = clean(m.group(1))
            if role and looks_like_person(name):
                people.append(person(name, role))
        if people:
            towns[town] = people
    return {"towns": towns, "edition": None}
