"""Florence County: one page per town under Government > Municipalities.

The municipalities page (/government/municipalities/) links each of the eight
towns as ?i=<id>. Each town page lists its elected officials as the office on
one line ("Chairman", "Supervisor") and the name on the next, followed by
telephone, e-mail link and mailing-address lines. The "Phone:" line ships on
the officer; the address is not read. Read with the token on 2026-10-15
(robots.txt served empty, so allow all)."""

import re
import urllib.parse

from . import clean, html_text, role_then_name

COUNTY_FIPS = "037"
COUNTY_NAME = "Florence"
SOURCES = ["https://www.florencecountywi.com/government/municipalities/"]


def scrape(ctx):
    index = ctx.fetch_text(SOURCES[0])
    links = {}
    for href, name in re.findall(
            r'<a href="(/government/municipalities/\?i=[0-9a-f]+)"[^>]*>([^<]+)</a>',
            index):
        links.setdefault(clean(name), urllib.parse.urljoin(SOURCES[0], href))
    if len(links) < 6:
        raise RuntimeError("found %d town links on the index" % len(links))
    towns = {}
    for town, url in sorted(links.items()):
        text = html_text(ctx.fetch_text(url))
        # the officials follow the page's introduction sentence
        start = text.find("names and contact information")
        if start < 0:
            continue
        people = role_then_name(text[start:])
        if people:
            towns[town] = people
    return {"towns": towns, "edition": None}
