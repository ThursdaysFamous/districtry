"""Eau Claire County: the county's Municipalities page (HTML).

The page links nine of the county's thirteen towns to their own web sites and
publishes officers only for the other four (Fairchild, Ludington, Otter Creek
and Wilson), as a directory of cards: each card has the officer's name in an
<h2> and a description "Chair<br />Town of Fairchild" or "First Supervisor<br
/>Town of ...", followed by a telephone number, e-mail and home address, which
are not read. The page prints no edition or date. Read with the token on
2026-10-15 (no robots.txt, HTTP 404, allow all)."""

import re

from . import clean, looks_like_person, norm_role, person

COUNTY_FIPS = "035"
COUNTY_NAME = "Eau Claire"
SOURCES = ["https://eauclairecounty.gov/government/municipalities.php"]
# only these four towns are published by the county; the rest link out
MIN_TOWNS = 4
PARTIAL_NOTE = ("Eau Claire County's list names the board for 4 of its 13 "
                "towns and links the others to their own websites.")

_CARD = re.compile(r"<h2>([^<]+)</h2>\s*(?:<!--[^>]*-->\s*)*"
                   r"<span class=\"rz-business-desc\">([^<]+)<br\s*/?>\s*"
                   r"Town of ([^<]+)</span>", re.I)
_ORDINAL = {"first": "1", "second": "2", "third": "3", "fourth": "4"}


def scrape(ctx):
    page = ctx.fetch_text(SOURCES[0])
    towns = {}
    for name, label, town in _CARD.findall(page):
        label = clean(label)
        # "First Supervisor" -> "Supervisor 1", so the seat is kept
        m = re.match(r"^(first|second|third|fourth)\s+supervisor$", label, re.I)
        role = ("Supervisor " + _ORDINAL[m.group(1).lower()]) if m else norm_role(label)
        name = clean(name)
        if role and looks_like_person(name):
            towns.setdefault(clean(town), []).append(person(name, role))
    return {"towns": towns, "edition": None}
