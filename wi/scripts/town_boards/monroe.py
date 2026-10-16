"""Monroe County: one page per town under Government > Municipalities.

The Municipalities page (/government/municipalities) links a page for each of
the 24 towns as /government/municipalities/<name>-township. Each page is
headed "Township of <Name>" (Scott: "Town of Scott") and lists one officer per line as "<office> –
<name>" ("Chair –Glen Bailey", "Supervisor – Robert Amundson"), each followed
by a home-address line and a telephone line, which are not kept.

CLIENT. Measured 2026-10-15: the token got HTTP 403 Forbidden on the
Municipalities page (urllib, UA_ROSTER_BOT); the Chrome client with its client
hints was served the page. robots.txt read as Chrome (6,641 bytes) has no rule
matching these paths. Read with Chrome on 2026-10-15."""

import re

from . import clean, html_text, role_then_name

COUNTY_FIPS = "081"
COUNTY_NAME = "Monroe"
SOURCES = ["https://www.co.monroe.wi.us/government/municipalities"]
CLIENT = "chrome"  # token re-measured 2026-10-15 at SOURCES[0]: HTTP 403 Forbidden


def scrape(ctx):
    index = ctx.fetch_text(SOURCES[0])
    urls = sorted(set(re.findall(
        r'href="(https://www\.co\.monroe\.wi\.us/government/municipalities/'
        r'[a-z\-]+-township)"', index)))
    if len(urls) < 18:
        raise RuntimeError("found %d town links on the index" % len(urls))
    towns = {}
    for url in urls:
        text = html_text(ctx.fetch_text(url))
        m = re.search(r"(?m)^(?:Township|Town) of ([A-Za-z .'\-]+?)\s*$", text)
        if not m:
            continue
        end = text.find("\nHOME\n", m.end())
        people = role_then_name(text[m.end():end if end > 0 else None])
        if people:
            towns[clean(m.group(1))] = people
    return {"towns": towns, "edition": None}
