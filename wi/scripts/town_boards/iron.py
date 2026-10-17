"""Iron County: one page per town on the county website.

The "Municipalities" page (/170/Municipalities) links a page for each of the
ten towns. Each town page carries a table of Title / Name / Phone / Email, one
cell per line in the page text: "Chairman", then the name; "Supervisor", then
the name. The name and the Phone cell are kept. The Email cell is not read:
measured 2026-10-17, the site replaces each address with Cloudflare's "email
protection" link, which shows no address and which this package does not
decode. Read with the token on 2026-10-15 (robots.txt: 816 bytes, no rule
matches these paths)."""

import re
import urllib.parse

from . import html_text, role_then_name

COUNTY_FIPS = "051"
COUNTY_NAME = "Iron"
SOURCES = ["https://www.co.iron.wi.gov/170/Municipalities"]


def _town_links(page, base):
    out = {}
    for href, name in re.findall(
            r'<a [^>]*href="(/\d+/Town-of-[^"]+)"[^>]*>\s*Town of ([^<]+?)\s*</a>',
            page):
        out.setdefault(name.strip(), urllib.parse.urljoin(base, href))
    return out


def scrape(ctx):
    index = ctx.fetch_text(SOURCES[0])
    links = _town_links(index, SOURCES[0])
    if len(links) < 8:
        raise RuntimeError("found %d town links on the index" % len(links))
    towns = {}
    for town, url in sorted(links.items()):
        text = html_text(ctx.fetch_text(url))
        # the board table starts at its "Title" header; the side menu above it
        # repeats every town's name
        start = text.find("\nTitle\n")
        if start < 0:
            continue
        people = role_then_name(text[start:])
        if people:
            towns[town] = people
    return {"towns": towns, "edition": None}
