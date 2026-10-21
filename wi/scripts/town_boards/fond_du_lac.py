"""Fond du Lac County: one page per town under "Area Cities, Villages and
Townships".

The "Towns" page (/community/area-cities-villages-and-townships/towns) links a
page for each of the 21 towns. Each town page has a table of Position /
Address / Contact, one cell per line in the page text: the office
("Chairperson", "Supervisor I", "Supervisor II"), then the name, then the
officer's home address, telephone and e-mail. The telephone cells ship on the
officer, with the label the county puts after a number ("~ Home", "~ Cell");
a number marked "~ Fax" does not. The e-mail cell ships too (Adam,
2026-10-17: "E-mails too"), except where its link writes to a different
address than it shows; the home address is not read.

CLIENT. Measured 2026-10-15: the token got HTTP 403 Forbidden on the Towns
page (urllib, UA_ROSTER_BOT); the same page served in full (about 154 KB) to
the Chrome client with its client hints. robots.txt read as Chrome has no rule
matching these paths. Read with Chrome on 2026-10-15."""

import re

from . import clean, html_text, role_then_name

COUNTY_FIPS = "039"
COUNTY_NAME = "Fond du Lac"
SOURCES = ["https://www.fdlco.wi.gov/community/area-cities-villages-and-townships/towns"]
CLIENT = "chrome"  # token re-measured 2026-10-15 at SOURCES[0]: HTTP 403 Forbidden


def scrape(ctx):
    index = ctx.fetch_text(SOURCES[0])
    links = {}
    for url, name in re.findall(
            r"<a href=['\"](https://www\.fdlco\.wi\.gov/community/"
            r"area-cities-villages-and-townships/towns/[a-z0-9\-]+)['\"][^>]*>"
            r"([^<]+)</a>", index):
        links.setdefault(clean(name), url)
    if len(links) < 15:
        raise RuntimeError("found %d town links on the Towns page" % len(links))
    towns = {}
    for town, url in sorted(links.items()):
        text = html_text(ctx.fetch_text(url))
        # the officers' table starts at its "Position" header and ends at the
        # page footer
        start = text.find("\nPosition\n")
        if start < 0:
            continue
        end = text.find("SUBSCRIBE", start)
        people = role_then_name(text[start:end if end > 0 else None])
        if people:
            towns[town] = people
    return {"towns": towns, "edition": None}
