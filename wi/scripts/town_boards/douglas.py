"""Douglas County: one page per town under "Town & Village Officials".

The index page (/507/Town-Village-Officials) links a page for each of the
sixteen towns (/508/Amnicon through /528/Wascott). Each town page lists the
town hall, then each officer as "<office>, <name>" on one line ("Chair, Arthur
E. Amys", "Town Supervisor, Dennis Hill") or as the office alone with the name
on the next line ("Town & County Board Supervisor" / "Mark Liebaert"), each
followed by address and telephone lines, which are not kept. Summit prints
three supervisors and no chair, and is returned as printed. Read with the
token on 2026-10-15 (robots.txt: 816 bytes, no rule matches these paths)."""

import re
import urllib.parse

from . import clean, html_text, looks_like_person, norm_role, person

COUNTY_FIPS = "031"
COUNTY_NAME = "Douglas"
SOURCES = ["https://douglascountywi.gov/507/Town-Village-Officials"]

# the office, optionally prefixed "Town", "Town & County Board", "Town Board";
# then either ", <name>" or nothing (the name is on the next line)
_ROLE = re.compile(
    r"^(?:town\s+(?:&|and)\s+county\s+board\s+|town\s+board\s+|town\s+)?"
    r"(chair\w*|supervisor)(\s*#?\s*\d+|\s+[IVX]+\b)?\s*(?:[,:\-–]\s*(.*))?$",
    re.I)


def _board(text):
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    people = []
    for i, ln in enumerate(lines):
        m = _ROLE.match(ln)
        if not m:
            continue
        role = norm_role(m.group(1) + (m.group(2) or ""))
        if not role:
            continue
        name = clean(m.group(3)) if m.group(3) else (
            clean(lines[i + 1]) if i + 1 < len(lines) else "")
        if looks_like_person(name):
            people.append(person(name, role))
    return people


def scrape(ctx):
    index = ctx.fetch_text(SOURCES[0])
    # the town pages are the index's secondary menu items; the two villages
    # are named "<x>, Village of" and are left out
    links = {}
    for href, name in re.findall(
            r'<a href="(/5[0-2]\d/[^"]+)"[^>]*secondaryNavItem[^>]*>([^<]+)</a>',
            index):
        name = clean(name)
        if "village" in name.lower() or "city" in name.lower():
            continue
        links.setdefault(name, urllib.parse.urljoin(SOURCES[0], href))
    if len(links) < 12:
        raise RuntimeError("found %d town links on the index" % len(links))
    towns = {}
    for town, url in sorted(links.items()):
        text = html_text(ctx.fetch_text(url))
        # the town's own block starts at its "Business Hours" or "Town Hall"
        # heading below the title; the menu below the block repeats every
        # town's name and carries no office
        start = text.find("%s\n%s\n" % (town, town))
        if start < 0:
            continue
        people = _board(text[start:])
        if people:
            towns[town] = people
    return {"towns": towns, "edition": None}
