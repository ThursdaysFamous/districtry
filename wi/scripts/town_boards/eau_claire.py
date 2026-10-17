"""Eau Claire County: the county's Municipalities page (HTML).

The page links nine of the county's thirteen towns to their own web sites and
publishes officers only for the other four (Fairchild, Ludington, Otter Creek
and Wilson), as a directory of cards: each card has the officer's name in an
<h2> and a description "Chair<br />Town of Fairchild" or "First Supervisor<br
/>Town of ...", followed by a telephone link, e-mail and home address. The
number the telephone link shows ships on the officer (and neither ships when
the link dials a different number); the address is not read. The page prints
no edition or date. Read with the token on 2026-10-15 (no robots.txt, HTTP 404,
allow all)."""

import re

from . import clean, html_text, looks_like_person, norm_role, person, phones_in

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
_TEL_LINK = re.compile(r"(?is)<a\b[^>]*href\s*=\s*[\"']tel:[^\"']*[\"'][^>]*>(.*?)</a>")


def _card_phones(card):
    """The numbers the card's telephone links show, nothing else of it."""
    out = []
    for inner in _TEL_LINK.findall(card):
        out.extend(phones_in(html_text(inner)))
    return out


def scrape(ctx):
    page = ctx.fetch_text(SOURCES[0])
    towns = {}
    cards = list(_CARD.finditer(page))
    for i, m in enumerate(cards):
        name, label, town = m.groups()
        # the card runs to the next card's name, or at most 4,000 characters
        end = cards[i + 1].start() if i + 1 < len(cards) else m.end() + 4000
        card = page[m.end():min(end, m.end() + 4000)]
        label = clean(label)
        # "First Supervisor" -> "Supervisor 1", so the seat is kept
        o = re.match(r"^(first|second|third|fourth)\s+supervisor$", label, re.I)
        role = ("Supervisor " + _ORDINAL[o.group(1).lower()]) if o else norm_role(label)
        name = clean(name)
        if role and looks_like_person(name):
            towns.setdefault(clean(town), []).append(
                person(name, role, _card_phones(card)))
    return {"towns": towns, "edition": None}
