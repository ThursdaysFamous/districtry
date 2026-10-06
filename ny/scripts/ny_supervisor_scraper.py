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
in a form a program can read. All nine have now been read; four are built and
the five that are not each say why below, which is the whole point of the
list — a measurement filed nowhere is one the next pass repeats.

WHAT IS AND IS NOT HERE, measured 2026-10-01 at the exact page each scraper
fetches, through `require_robots_once` with the client that does the fetching:

  Saratoga    BUILT. 23 seats across 19 towns and 2 cities.
  Schoharie   BUILT. 16 towns, with party, mailing address and telephone.
  Warren      BUILT. 20 seats over 12 units, and the county where the seat
              and the unit come apart: ten towns seat one each, the city of
              Glens Falls seats five by ward under its own charter, and
              Queensbury seats a Town Supervisor plus four County
              Supervisors. Every member carries a role for that reason.
  Delaware    BUILT. 19 towns, one supervisor each, with party, postal
              address and telephone. Its board page is on delcony.gov while
              the state's own county-website table publishes
              co.delaware.ny.us, so the state table locates the county and
              not the page.
  Livingston  NOT BUILT. Its front page carries no board link at all and its
              SITEMAP carries one page PER TOWN SUPERVISOR, seventeen of them
              (/805/Avon-Town-Supervisor and so on), while /139 is a landing
              page with no roster. So the county is readable and costs
              seventeen fetches a run rather than one, and it abbreviates
              two towns the fabric spells out ("N. Dansville", "W. Sparta"),
              which needs an alias each. Measured 2026-10-01; the host also
              reset two of four requests, so a run wants a retry.
  Madison     NOT BUILT. /234/Supervisors answers 200 at 100 KB and renders
              to 72 visible lines carrying no town and no name, because the
              content is assembled in the browser — the Albany pattern
              already recorded on the ny-county-governing-body record.
              Measured 2026-10-01. Its Directory page is the next thing to
              read rather than a blocker.
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
    "warren": {
        "county": "Warren",
        "url": "https://warrencountyny.gov/bos",
        "board": "Warren County Board of Supervisors",
        "seats": 20,
    },
    # THE STATE PUBLISHES co.delaware.ny.us AND THE BOARD IS ON delcony.gov.
    # The state's own county-website table is the scaffolding this tranche
    # rests on and it carries the county's older host, which serves a front
    # page whose every government link points at delcony.gov. So the state
    # table locates a county and does not locate its board page, and the
    # second host gets its own robots read, which it passes.
    "delaware": {
        "county": "Delaware",
        "url": "https://www.delcony.gov/government/board/",
        "board": "Delaware County Board of Supervisors",
        "seats": 19,
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


WARREN_TERM = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}\s*-\s*\d{1,2}/\d{1,2}/\d{4}$")
WARREN_WARD = re.compile(r"^Ward\s+(\d+)$")


def parse_warren(lines, units):
    """[{unit, name, role, phone}] from the three stacked contact tables.

    WARREN IS THE COUNTY WHERE THE SEAT AND THE UNIT COME APART, and it is
    read off the page's own section headings rather than inferred. Ten towns
    seat one supervisor each; the CITY OF GLENS FALLS seats five, one elected
    from each of its wards under its own charter; and QUEENSBURY seats five,
    one Town Supervisor and four County Supervisors. So this county needs the
    role on every member, because a reader on a Glens Falls card is being
    shown five people of whom one is theirs, and a card that said nothing
    would read as five people who all represent them.

    The ROLE IS THE PAGE'S FIRST CELL and the section decides what it means:
    a town's row opens with the town name, a Glens Falls row with `Ward N`,
    and a Queensbury row with `Town` or `County`. A member is then the next
    line after that cell, confirmed by the term that follows it, which is
    what keeps the staff block at the foot of the page out — it carries
    names in the same shape and no term.
    """
    out = []
    section = None
    for i, line in enumerate(lines):
        if line == "City of Glens Falls":
            section = "Glens Falls"
            continue
        if line == "Queensbury":
            section = "Queensbury"
            continue
        if line in units and line != "Queensbury":
            section = line
        # A row is a label, a name and then a term. The term is the witness:
        # the page's staff block repeats the name shape without one.
        if i + 2 >= len(lines) or not WARREN_TERM.match(lines[i + 2]):
            continue
        label, name = line, lines[i + 1].strip()
        ward = WARREN_WARD.match(label)
        if section == "Glens Falls" and ward:
            unit, role = "Glens Falls", "Ward %s supervisor" % ward.group(1)
        elif section == "Queensbury" and label in ("Town", "County"):
            unit = "Queensbury"
            role = ("Town Supervisor" if label == "Town"
                    else "County Supervisor, elected town-wide")
        elif label in units:
            unit, role = label, None
        else:
            continue
        phone = None
        for w in lines[i + 3:i + 5]:
            if len(re.sub(r"\D", "", w)) >= 10:
                phone = w.strip()
                break
        row = {"unit": unit, "unitType": units[unit], "name": name}
        if role:
            row["role"] = role
        if phone:
            row["phone"] = phone
        out.append(row)
    return out


DELAWARE_NAME = re.compile(r"^(.+?)\s*\[([A-Z])\]\s*$")


def parse_delaware(lines, units):
    """[{unit, name, party, address, phone}] from the "Town of X" rows.

    One supervisor per town over all nineteen, each row a town heading, a
    WEIGHTED VOTE, the name with its party in square brackets, a two-line
    postal address and a telephone. The weighted vote is REAL AND IS NOT
    SHIPPED: Delaware's board casts 200 votes apportioned by population, from
    Bovina's 3 to Delhi's 22, so a supervisor there does not carry one vote
    of nineteen. It is a published attribute of the seat and would want a card
    field and a sentence of its own rather than riding in on a roster change.
    """
    out = []
    for i, line in enumerate(lines):
        if not line.startswith("Town of "):
            continue
        unit = line[len("Town of "):].strip()
        if unit not in units:
            continue
        # THE ROW ENDS AT THE NEXT TOWN HEADING. A fixed window swept the
        # following heading into Delhi's address, which shipped as
        # "5 Elm Street, Delhi, NY 13753, Town of Deposit" — a real street
        # address with another town's name welded onto it, which reads
        # entirely plausibly and names the wrong place.
        window = []
        for w in lines[i + 1:i + 8]:
            if w.startswith("Town of "):
                break
            window.append(w)
        hit = next(((j, DELAWARE_NAME.match(w)) for j, w in enumerate(window)
                    if DELAWARE_NAME.match(w)), None)
        if not hit:
            continue
        j, m = hit
        # THE ADDRESS ENDS AT THE TELEPHONE, AND THE LAST ROW IS WHY. Walton
        # is the nineteenth town, so no next heading closes its window, and
        # taking everything after the name swept the page's own prose and a
        # weather widget into its address. A row is name, street, town-state-zip,
        # telephone, so the telephone is the boundary and a row that has none
        # within four lines ships no address at all.
        rest = [w.strip() for w in window[j + 1:j + 5] if w.strip()]
        phone, address = None, ""
        for k, w in enumerate(rest):
            if len(re.sub(r"\D", "", w)) == 10:
                phone = w
                address = ", ".join(rest[:k])
                break
        row = {"unit": unit, "unitType": units[unit], "name": m.group(1).strip()}
        # A PARTY LETTER IS EXPANDED ONLY WHERE IT IS UNAMBIGUOUS, AND THIS
        # PAGE PUBLISHES NO LEGEND. D, R and C are the fleet's own three. New
        # York's [I] is not one of them — the Independence Party existed until
        # 2020 and an independent is a different thing — so the letter is
        # dropped rather than guessed at, and the drop is printed. A party is
        # officeholder data and the honesty rule covers it.
        party = PARTY.get(m.group(2))
        if party:
            row["party"] = party
        else:
            print("ny-supervisor-scraper: delaware — %s is published [%s], "
                  "which this page gives no legend for, so no party ships"
                  % (row["name"], m.group(2)))
        if address:
            row["address"] = address
        if phone:
            row["phone"] = phone
        out.append(row)
    return out


PARSERS = {"saratoga": parse_saratoga, "schoharie": parse_schoharie,
           "warren": parse_warren, "delaware": parse_delaware}


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
