"""Trempealeau County: one page per town on the county website.

The county's home page links a page for each town at
/town_of_<name>/index.php (the /township/... links are stubs). Fourteen of the
fifteen towns have one; Albion has none. Each page has a "TOWN OF <NAME>
OFFICIALS" list, one officer per line as "<name> - <office>" ("Mike Wineski -
Chairman", "John E. Krett - Supervisor"). Read with the token on 2026-10-15
(robots.txt: HTTP 404, so no policy and allow all)."""

import re
import urllib.parse

from . import clean, html_text, looks_like_person, norm_role, person

COUNTY_FIPS = "121"
COUNTY_NAME = "Trempealeau"
SOURCES = ["https://co.trempealeau.wi.us/"]

_LINE = re.compile(r"^(.+?)\s+[-–—]\s+((?:town\s+)?(?:chair\w*|supervisor)"
                   r"(?:\s*#?\s*\d+|\s+[IVX]+)?)\s*$", re.I)


def scrape(ctx):
    home = ctx.fetch_text(SOURCES[0])
    slugs = sorted(set(re.findall(r'href="(?:/|https://co\.trempealeau\.wi\.us/)?'
                                  r'(town_of_[a-z_]+)/index\.php"', home)))
    if len(slugs) < 10:
        raise RuntimeError("found %d town links on the home page" % len(slugs))
    towns = {}
    for slug in slugs:
        url = urllib.parse.urljoin(SOURCES[0], slug + "/index.php")
        text = html_text(ctx.fetch_text(url))
        m = re.search(r"TOWN OF ([A-Z .'\-]+?) OFFICIALS\s*\n", text)
        if not m:
            continue
        town = clean(m.group(1)).title()
        people = []
        for ln in text[m.end():].split("\n"):
            ln = ln.strip()
            if re.match(r"^Please Note", ln, re.I):
                break
            hit = _LINE.match(ln)
            if not hit:
                continue
            role = norm_role(hit.group(2))
            name = clean(hit.group(1))
            if role and looks_like_person(name):
                people.append(person(name, role))
        if people:
            towns[town] = people
    return {"towns": towns, "edition": None}
