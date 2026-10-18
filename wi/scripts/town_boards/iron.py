"""Iron County: one page per town on the county website.

The "Municipalities" page (/170/Municipalities) links a page for each of the
ten towns. Each town page carries a table of Title / Name / Phone / Email (some
towns add an Address column), one cell per line in the page text: "Chairman",
then the name; "Supervisor", then the name. The name, the Phone cell and the
Email cell are kept; the Address cell is not read.

THE EMAIL CELL IS SCRAMBLED, AND IT IS READ THE WAY A VISITOR'S BROWSER READS
IT. The site replaces every address with Cloudflare's "email protection" link,
which shows "Email", or "Email" and the officer's name, and carries the
address only as a token that Cloudflare's own script on the page decodes for
every visitor. That is not an access control (Adam, 2026-10-09), so each page
is read as the browser shows it (`ctx.fetch_text(url, cloudflare=True)`), and
an address whose link is labelled with any name but that of the member in
whose row it sits is not read for that member (`town_boards.label_fits`).
Until 2026-10-17 the Email cell was not read at all. Measured that day, nine
board members' rows carry an address: six each carry one printed nowhere
else, labelled with that member's own name, and ship it; the Town of Knight's
chair and two supervisors carry one address the town prints for six of its
officials, which is the town's and ships on none. Read with the token on
2026-10-15 and 2026-10-17 (robots.txt: 816 bytes, no rule matches these
paths)."""

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
    index = ctx.fetch_text(SOURCES[0], cloudflare=True)
    links = _town_links(index, SOURCES[0])
    if len(links) < 8:
        raise RuntimeError("found %d town links on the index" % len(links))
    towns = {}
    for town, url in sorted(links.items()):
        text = html_text(ctx.fetch_text(url, cloudflare=True))
        # the board table starts at its "Title" header; the side menu above it
        # repeats every town's name
        start = text.find("\nTitle\n")
        if start < 0:
            continue
        people = role_then_name(text[start:])
        if people:
            towns[town] = people
    return {"towns": towns, "edition": None}
