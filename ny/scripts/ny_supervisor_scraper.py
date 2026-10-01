#!/usr/bin/env python3
"""Scrape the board rosters of New York's board-of-supervisors counties.

WHY THIS COUNTY SHAPE FIRST. New York county boards come in two forms. A
county that ELECTS A LEGISLATURE from districts needs geometry drawn before
anybody can be named, which is the Tompkins route. A BOARD OF SUPERVISORS
needs no new geometry at all: the seat IS the town, so the unit is already
drawn by this instance's statewide cities-and-towns fabric, and naming the
member answers the county's governing body over ground the app already has.
Nine of the 57 counties outside the city say "board of supervisors" on their
own front page (measured 2026-10-01, recorded on the ny-county-governing-body
gap record), and this file carries the ones whose roster is actually published
in a form a program can read.

WHAT IS AND IS NOT HERE, measured 2026-10-01 at the exact page each scraper
fetches, through `require_robots_once` with the client that does the fetching:

  Saratoga    BUILT. 23 seats across 19 towns and 2 cities.
  Schoharie   BUILT. 16 towns, with party, mailing address and telephone.
  Warren      NOT BUILT. The roster is a table per municipality whose columns
              are Ward / Town / County, with the city of Glens Falls seated by
              ward and Queensbury holding one Town seat and three County ones.
              It is structured and readable and it is a different parse; it is
              the next one to do rather than a blocker.
  Ontario     NOT BUILT, and deliberately. The only name list on the board
              page is the CAPTION OF A GROUP PHOTOGRAPH ("1st Row (Left to
              Right): …"), which pairs a name with a town and also carries the
              Clerk of the Board, the County Administrator and the Deputy
              County Administrator, who hold no seat. A caption is a
              description of a picture, not a roster, and nothing in it says
              which of its names is a member.
  Hamilton    NOT BUILT. The board page names the Chairman and nobody else.
  Essex       NOT BUILT. The board page names the Chairman and Vice-Chairman,
              each with a party and a town, and sends a reader to a county
              directory PDF for the rest.

TWO SEATS FOR ONE TOWN IS NORMAL HERE AND IS WHY NOTHING IS KEYED ONE NAME
PER UNIT. New York County Law lets a town or city elect more than one
supervisor, and Saratoga's own page seats two for the town of Clifton Park and
two for the city of Saratoga Springs. A roster keyed `unit -> person` would
have dropped one of each pair and read as complete.

SCHOHARIE'S TRAP IS THE TOWN COLUMN. Its table carries the Clerk, the Deputy
Clerk and a third staff member in exactly the same shape as a member, with
their ROLE in the column every member fills with a town name — so a parse that
trusts that column ships three staff as supervisors. The guard is this
instance's own cities-and-towns fabric: a row whose town is not a town of that
county is not a member, and the count must come out at the number of units the
fabric holds.
"""

import html
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "scripts"))

from scraper_common import (  # noqa: E402
    UA_ROSTER_BOT, fetch_stdlib, require_robots_once)

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", ".."))
FABRIC = os.path.join(REPO_ROOT, "ny", "data", "app", "ny-cities-towns.json")
# NOT INSIDE THE REPOSITORY. This file is the scrape, which the builder
# then turns into the shipped roster; nothing reads it afterwards, and a
# default that wrote into the tree would leave a copy of last week's
# scrape sitting beside this week's roster with nothing comparing them.
# The weekly job passes --out explicitly for the same reason.
OUT = os.path.join(tempfile.gettempdir(), "ny-supervisor-scrape.json")

SOURCES = {
    "saratoga": {
        "county": "Saratoga",
        "url": "https://www.saratogacountyny.gov/board-of-supervisors/",
        "board": "Saratoga County Board of Supervisors",
        "seats": 23,
    },
    "schoharie": {
        "county": "Schoharie",
        "url": "https://www.schohariecounty-ny.gov/departments/board_of_supervisors/index.php",
        "board": "Schoharie County Board of Supervisors",
        "seats": 16,
    },
}

# "Town of Ballston - Supervisor John Antoski" and
# "Town of Clifton Park - Supervisors Philip C. Barrett and Ram mohan Lalukota".
# The dash is an ASCII hyphen on some rows and an en dash on others, which the
# first draft of this pattern got wrong and which cost the town of Charlton.
SARATOGA_ROW = re.compile(
    r"^(Town|City)\s+of\s+(.+?)\s*[-–—]\s*Supervisors?\s+(.+?)\s*$")
PARTY = {"D": "Democrat", "R": "Republican", "C": "Conservative"}
SCHOHARIE_NAME = re.compile(r"^(.+?)\s*\((D|R|C)\)\s*(?:,\s*(.+?))?\s*$")


def visible_lines(body):
    """The page's visible text, one line per element, scripts removed.

    A LINE-PER-ELEMENT READ RATHER THAN A PARSER because both pages put each
    field in its own cell, and the one thing this must never do is join two
    cells into one string — Richland's bulk endpoint shipped
    `Olney Precinct 11020Olney Precinct 10`, which parses cleanly and wrongly.
    """
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", body)
    text = html.unescape(re.sub(r"<[^>]+>", "\n", body))
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def parse_saratoga(lines, units):
    """[{unit, unitType, name}] from the "Town of X - Supervisor Y" rows."""
    out = []
    for line in lines:
        m = SARATOGA_ROW.match(line)
        if not m:
            continue
        kind, unit, people = m.group(1).lower(), m.group(2).strip(), m.group(3)
        if unit not in units:
            continue
        for person in re.split(r"\s+and\s+", people):
            person = person.strip().rstrip(".")
            if person:
                out.append({"unit": unit, "unitType": kind, "name": person})
    return out


def parse_schoharie(lines, units):
    """[{unit, name, party, role, address, phone}] from the members table.

    The row's own order is name, address, (optional fax), town, phone, so the
    town is found by LOOKING FOR A TOWN rather than by counting cells — the
    optional fax line shifts every later cell on five of the sixteen rows.
    """
    out = []
    for i, line in enumerate(lines):
        m = SCHOHARIE_NAME.match(line)
        if not m:
            continue
        name, party, role = m.group(1).strip(), m.group(2), (m.group(3) or "").strip()
        window = lines[i + 1:i + 7]
        unit = next((w for w in window if w in units), None)
        if not unit:
            continue                      # the Clerk and the two deputies
        address = window[0] if window else None
        phone = None
        for w in window:
            digits = re.sub(r"\D", "", w)
            if len(digits) == 10 and w != address:
                phone = w.strip()
        row = {"unit": unit, "unitType": "town", "name": name,
               "party": PARTY[party]}
        if role:
            row["role"] = role
        if address and address not in (unit,):
            row["address"] = address
        if phone:
            row["phone"] = phone
        out.append(row)
    return out


PARSERS = {"saratoga": parse_saratoga, "schoharie": parse_schoharie}


def units_of(county):
    with open(FABRIC, encoding="utf-8") as f:
        feats = json.load(f)["features"]
    return {p["NAME"]: p["MUNI_TYPE"]
            for p in (x.get("properties") or {} for x in feats)
            if p.get("COUNTY") == county}


def scrape(key):
    src = SOURCES[key]
    require_robots_once(src["url"], UA_ROSTER_BOT, label="ny-supervisors")
    body = fetch_stdlib(src["url"], headers={"User-Agent": UA_ROSTER_BOT},
                        timeout=45)
    if isinstance(body, bytes):
        body = body.decode("utf-8", "replace")
    units = units_of(src["county"])
    members = PARSERS[key](visible_lines(body), units)
    if not members:
        raise SystemExit("ny-supervisor-scraper: %s parsed no members from %s"
                         % (key, src["url"]))
    return {"county": src["county"], "board": src["board"],
            "sourceUrl": src["url"], "seats": src["seats"],
            "units": len(units), "members": members}


def main():
    args = sys.argv[1:]
    dest = OUT
    if "--out" in args:
        i = args.index("--out")
        if i + 1 >= len(args):
            raise SystemExit("ny-supervisor-scraper: --out needs a path")
        dest = args[i + 1]
    out = {}
    for key in sorted(SOURCES):
        out[key] = scrape(key)
        rec = out[key]
        print("ny-supervisor-scraper: %s — %d member(s) over %d unit(s)"
              % (key, len(rec["members"]), rec["units"]))
    parent = os.path.dirname(os.path.abspath(dest))
    os.makedirs(parent, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    print("ny-supervisor-scraper: wrote %s" % dest)


if __name__ == "__main__":
    main()
