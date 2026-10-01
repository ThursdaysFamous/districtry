#!/usr/bin/env python3
"""Read the City of Galesburg's own council page into a municipal-officials enrichment payload.

WHY A CITY SCRAPER AND NOT A COUNTY ONE. Knox County has no municipal-officials
source at all — its Clerk's site is dead (knoxclerk.org resets HTTPS and 503s
plain HTTP, confirmed from two networks) and the county's own website answers
403 to every automated client. The CITY, however, publishes a full council page
at www.ci.galesburg.il.us with a name, ward, direct phone and term for all seven
aldermen plus the mayor. So this rides the builder's --enrich path, which exists
for exactly this shape: a municipality no county directory covers, supplied by
its own site.

WHY IT IS NEEDED AT ALL, given the ward layer already carries names. Galesburg's
ward polygons ship a MEMBER column, and it is NOT read. Its ward NUMBERING is
confirmed correct by this page, seven for seven — but one of its names is stale:
the layer says "Heather Zeigler Acerra" where the city says "Heather Acerra".
That is the COLES RULE, which this project paid for once already on a county
board layer whose officeholder column was six names wrong: a GIS attribute table
is a snapshot, and the body's own page is the record. Geometry from the layer,
people from the page.

WHAT THE PAGE PUBLISHES. Each seat is a block reading "<Ordinal> Ward City
Council Member - <Name>", followed by a direct phone ("Phone: 309/370-7943") and
"Current Term: <yyyy> - <yyyy>". The addresses on the page are all CITY HALL,
55 W. Tompkins Street — the seats publish no home addresses, so there is nothing
here to refuse, but the parser reads the office block once rather than per-seat
so a future change cannot quietly turn a residence into a shipped address (the
Madison/Peoria rule).

ORDINALS, NOT DIGITS. The page writes "Fifth Ward", never "Ward 5", so the ward
number is mapped from the ordinal word. An unrecognised ordinal is dropped with
a warning rather than guessed into a number.

Usage:
    python3 scripts/galesburg_council_scraper.py --out /tmp/galesburg_council.json
"""

import os
import argparse
import datetime
import json
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import (UA_HEADERS_ROSTER_BOT,  # noqa: E402  (shared machinery)
                            require_robots_once)

SITE = "https://www.ci.galesburg.il.us"
OFFICIALS_PAGE = (SITE + "/government/elected_officials___election_offices/"
                  "mayor_and_city_council/index.php")
JURISDICTION = "City of Galesburg"
COUNTY = "Knox"

# City Hall — the office address for every seat on this council. Read from a
# constant rather than per-seat precisely so a page change cannot promote a
# personal address into the office block.
OFFICE = {
    "office_address": "55 W. Tompkins Street",
    "office_city": "Galesburg",
    "office_state": "IL",
    "office_zip": "61401",
    "office_phone": "309-345-3600",
    "office_email": None,
}

WARDS = 7
MIN_OFFICIALS = 7          # seven aldermen; the mayor is a bonus, not a floor
MIN_SEATS = 7
MIN_PHONES = 6

ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4,
            "fifth": 5, "sixth": 6, "seventh": 7}

# OUR OWN IDENTITY, MEASURED RATHER THAN ASSUMED (2026-10-01). This file
# used to send a Chrome string. Every page it fetches was re-read with
# scraper_common's districtry token on this file's own HTTP stack and
# answered in full, so the browser string was claiming a client this
# project does not run for no measured gain. A site that measurably
# refuses the token gets the browser rung back, per host, with the
# measurement written here.
HEADERS = dict(UA_HEADERS_ROSTER_BOT)
TIMEOUT = 60

# A name token is capitalised AND not one of the page's own layout words. The
# exclusion is not cosmetic: without it the match runs straight past the name
# into the next label and yields "Angelica Mangieri Phone" — the page puts
# "Phone:" immediately after every seat's name, so every one of the seven was
# wrong. Same reason "Mayor and City Council" cannot become a person.
_STOP = (r"Phone|Email|E-mail|Current|Term|Ward|City|Council|Member|Mayor|"
         r"Strategic|Watch|Proposed|Share|Agendas|Find|Use|Street|Galesburg")
_WORD = r"(?!(?:" + _STOP + r")\b)[A-Z][A-Za-z.'’-]+"
NAME = _WORD + r"(?:\s+" + _WORD + r"){0,3}"
SEAT_RE = re.compile(
    r"(First|Second|Third|Fourth|Fifth|Sixth|Seventh)\s+Ward\s+City\s+Council\s+"
    r"Member\s*[-–]\s*(" + NAME + r")", re.I)
# The page writes "Mayor Peter Schwartzman" with no dash, unlike the ward seats.
MAYOR_RE = re.compile(r"\bMayor\s+(" + NAME + r")")
PHONE_RE = re.compile(r"Phone:\s*([0-9]{3}[/\-.][0-9]{3}[-.][0-9]{4})")
TERM_RE = re.compile(r"Current Term:\s*([0-9]{4})\s*[-–]\s*([0-9]{4})")

# How far past a seat header to look for that seat's own phone and term. The
# blocks run ~300 characters; a wider window would read the NEXT seat's phone.
BLOCK_CHARS = 320


def visible_text(html):
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def clean(value):
    if not value:
        return None
    value = " ".join(str(value).split())
    return value or None


def normalise_phone(raw):
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 10:
        return None
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    warnings = []
    require_robots_once(OFFICIALS_PAGE, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-galesburg-council-scraper")
    resp = requests.get(OFFICIALS_PAGE, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    text = visible_text(resp.text)
    scraped_at = (datetime.datetime.now(datetime.timezone.utc)
                  .strftime("%Y-%m-%dT%H:%M:%SZ"))

    records = []
    seen_wards = set()
    for m in SEAT_RE.finditer(text):
        ordinal = m.group(1).lower()
        ward = ORDINALS.get(ordinal)
        if not ward:
            warnings.append("unrecognised ordinal %r — seat dropped rather than guessed"
                            % m.group(1))
            continue
        if ward in seen_wards:
            continue
        seen_wards.add(ward)
        block = text[m.start():m.start() + BLOCK_CHARS]
        phone = PHONE_RE.search(block)
        term = TERM_RE.search(block)
        records.append(dict(
            OFFICE,
            jurisdiction=JURISDICTION,
            office="Alderman",
            district="Ward %d" % ward,
            name=clean(m.group(2)),
            person_phone=normalise_phone(phone.group(1)) if phone else None,
            person_email=None,
            term="%s-%s" % (term.group(1), term.group(2)) if term else None,
            source_url=OFFICIALS_PAGE,
            scraped_at=scraped_at,
        ))

    mayor = MAYOR_RE.search(text)
    if mayor:
        records.append(dict(
            OFFICE,
            jurisdiction=JURISDICTION,
            office="Mayor",
            district=None,
            name=clean(mayor.group(1)),
            person_phone=None,
            person_email=None,
            source_url=OFFICIALS_PAGE,
            scraped_at=scraped_at,
        ))
    else:
        warnings.append("no mayor found on the council page")

    seats = sum(1 for r in records if r["district"])
    phones = sum(1 for r in records if r["person_phone"])
    problems = []
    if seats != MIN_SEATS:
        problems.append("%d ward seats, expected %d" % (seats, MIN_SEATS))
    if len(records) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(records), MIN_OFFICIALS))
    if phones < MIN_PHONES:
        problems.append("%d direct phones < floor %d" % (phones, MIN_PHONES))
    for warning in warnings:
        print("  warning: %s" % warning, file=sys.stderr)
    if problems:
        raise SystemExit("galesburg-council: " + "; ".join(problems)
                         + " — refusing to write")

    payload = {
        "county": COUNTY,
        "kind": "municipal-enrichment",
        "directory_url": OFFICIALS_PAGE,
        "officials_page": OFFICIALS_PAGE,
        "scraped_at": scraped_at,
        "municipalities": [{"name": JURISDICTION, "source_url": OFFICIALS_PAGE,
                            "scraped_at": scraped_at}],
        "officials": records,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print("scraped Galesburg: %d officials (%d ward seats, %d with a direct phone) -> %s"
          % (len(records), seats, phones, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
