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
  Wayne       BUILT 2026-10-26. 15 towns, one supervisor each, read off the
              board page's "Members" list as name-then-", Town" pairs. The
              state's county-website table publishes www.co.wayne.ny.us,
              which answers the IIS default page; the county is at
              www.waynecountyny.gov. The Chair is also a town's supervisor and
              is listed twice, so only the row naming a town is a seat.
  Fulton      BUILT 2026-10-26. 20 seats: ten towns, the CITY OF GLOVERSVILLE
              by its six wards and the CITY OF JOHNSTOWN by its four, the Glens
              Falls shape twice. Fulton also has a TOWN of Johnstown beside
              the city, which is why a unit is keyed by name and type wherever
              two units of one county share a name (unit_key below).
  Wyoming     BUILT 2026-10-26. 16 towns. The board page names only the Chair
              and links the county's own "2026 Roster" of county, town and
              village officials, a 68-page PDF compiled by the Board's office
              (dated 22 September 2026 in its own metadata), whose third page
              lists each town's supervisor with a party letter. The link is
              found on the board page each run rather than stored, so next
              year's roster is read when the county posts it. The PDF also
              prints each supervisor's home address and two telephone
              columns; NEITHER SHIPS. The telephone columns are HOME and TOWN,
              and where a row has only one number the text layer does not say
              which column it sits in, so a number could be published as an
              office line when it is somebody's home. Names and parties only.
  Livingston  BUILT 2026-10-26, on the route recorded below: one page per town
              supervisor, seventeen fetches a run, each page naming the
              supervisor with an e-mail and a telephone. The URL table maps
              each page to its town, which is what settles the two
              abbreviations ("N. Dansville", "W. Sparta") without an alias.
              The 2026-10-01 note follows as written:
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
import time

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
    # www.co.wayne.ny.us, the host the state's table publishes, answers the
    # IIS default page. The county's own site is www.waynecountyny.gov.
    "wayne": {
        "county": "Wayne",
        "url": "https://www.waynecountyny.gov/460/Board-of-Supervisors",
        "board": "Wayne County Board of Supervisors",
        "seats": 15,
    },
    "fulton": {
        "county": "Fulton",
        "url": "https://www.fultoncountyny.gov/board-supervisors",
        "board": "Fulton County Board of Supervisors",
        "seats": 20,
    },
    # The board page links the roster PDF; scrape_wyoming() follows that link.
    "wyoming": {
        "county": "Wyoming",
        "url": "https://www.wyomingco.net/149/Board-of-Supervisors",
        "board": "Wyoming County Board of Supervisors",
        "seats": 16,
    },
    "livingston": {
        "county": "Livingston",
        "url": "https://www.livingstoncounty.us/96/Board-of-Supervisors",
        "board": "Livingston County Board of Supervisors",
        "seats": 17,
    },
}

# ONE PAGE PER SUPERVISOR, taken from the county's own sitemap on 2026-10-26.
# The table, not the page heading, names the town: the county abbreviates
# North Dansville and West Sparta in its headings ("N. Dansville Town
# Supervisor"), and the fabric spells both out.
LIVINGSTON_PAGES = {
    "Avon": "805/Avon-Town-Supervisor",
    "Caledonia": "807/Caledonia-Town-Supervisor",
    "Conesus": "808/Conesus-Town-Supervisor",
    "Geneseo": "809/Geneseo-Town-Supervisor",
    "Groveland": "810/Groveland-Town-Supervisor",
    "Leicester": "811/Leicester-Town-Supervisor",
    "Lima": "812/Lima-Town-Supervisor",
    "Livonia": "813/Livonia-Town-Supervisor",
    "Mount Morris": "815/Mount-Morris-Town-Supervisor",
    "North Dansville": "816/N-Dansville-Town-Supervisor",
    "Nunda": "817/Nunda-Town-Supervisor",
    "Ossian": "818/Ossian-Town-Supervisor",
    "Portage": "819/Portage-Town-Supervisor",
    "Sparta": "820/Sparta-Town-Supervisor",
    "Springwater": "821/Springwater-Town-Supervisor",
    "West Sparta": "822/W-Sparta-Town-Supervisor",
    "York": "823/York-Town-Supervisor",
}
LIVINGSTON_BASE = "https://www.livingstoncounty.us/"


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


def parse_wayne(lines, units):
    """[{unit, name}] from the "Members" list: a name, then ", <Town>".

    The list also carries the Clerk of the Board and the County Administrator
    in exactly that shape, with their office where a town would be, and the
    Chair twice — once as ", Madam Chair" and once as her town. Only a row
    whose second line names a town of this county is a seat.
    """
    out = []
    for i in range(len(lines) - 1):
        nxt = lines[i + 1]
        if not nxt.startswith(","):
            continue
        unit = nxt[1:].strip()
        if unit not in units:
            continue
        out.append({"unit": unit, "unitType": units[unit],
                    "name": lines[i].strip()})
    return out


FULTON_ROW = re.compile(
    r"^(Town|City)\s+of\s+(.+?)(?:\s*,\s*Ward\s+(\d+))?\s*:\s*$")


def parse_fulton(lines, units):
    """[{unit, name, role}] from the "Town of X:" / "City of X, Ward N:" rows.

    Fulton seats the CITY OF GLOVERSVILLE by six wards and the CITY OF
    JOHNSTOWN by four, so a city row carries its ward as the member's role,
    the Warren reasoning. The line after a heading is the member; a following
    "(Chairman of the Board 2026)" line is the board office, not a seat, and
    is not read.
    """
    out = []
    for i, line in enumerate(lines):
        m = FULTON_ROW.match(line)
        if not m or i + 1 >= len(lines):
            continue
        kind = m.group(1).lower()
        unit = unit_key(m.group(2).strip(), kind, units)
        if unit not in units:
            continue
        row = {"unit": unit, "unitType": kind, "name": lines[i + 1].strip()}
        if m.group(3):
            row["role"] = "Ward %s supervisor" % m.group(3)
        out.append(row)
    return out


def parse_wyoming(lines, units):
    """[{unit, name, party}] from the roster PDF's supervisors table.

    Each row's text runs party letter, town, name, then a home address and up
    to two telephone numbers. Only the first three ship (see the docstring
    table for why the telephones do not). The table follows a "TOWN" column
    heading and is read until every town has been seen once.
    """
    out, seen = [], set()
    for i in range(len(lines) - 2):
        party, unit, name = lines[i], lines[i + 1], lines[i + 2]
        if len(party) != 1 or not party.isalpha() or unit not in units:
            continue
        if unit in seen:
            continue
        seen.add(unit)
        row = {"unit": unit, "unitType": units[unit], "name": name.strip()}
        if PARTY.get(party):
            row["party"] = PARTY[party]
        else:
            print("ny-supervisor-scraper: wyoming — %s is published %s, which "
                  "the roster gives no legend for, so no party ships"
                  % (row["name"], party))
        out.append(row)
    return out


LIVINGSTON_HEADING = re.compile(r"Town Supervisor$")


def parse_livingston_page(lines, unit, url):
    """{unit, name, email, phone, url} from one supervisor's own page.

    The page's own heading ("Avon Town Supervisor") appears in its breadcrumb
    and as its title, and the side menu repeats every OTHER town's heading
    after the member block — a first draft took the last match and named all
    seventeen supervisors "Agendas, Minutes". So the member is read after the
    occurrence of this page's own heading whose next lines are a name and then
    "Email:" or "Phone:", skipping the two one-letter text-size buttons.
    """
    rest = None
    for i, ln in enumerate(lines):
        if not LIVINGSTON_HEADING.search(ln):
            continue
        cand = [x for x in lines[i + 1:i + 12] if x != "A"]
        # Avon's supervisor chairs the county board, and his page puts that
        # title on its own line between his name and "Email:"; it is carried
        # as the role and never as the name.
        if len(cand) >= 2 and not cand[0].endswith(":") \
                and cand[1].startswith(("Email:", "Phone:")):
            # Portage prints "Email: none" on one line, so a label is matched
            # by its start, and no address ships without an "@".
            rest, role = cand, None
            break
        if len(cand) >= 3 and not cand[0].endswith(":") \
                and not cand[1].endswith(":") \
                and "Board of Supervisors" in cand[1] \
                and cand[2].startswith(("Email:", "Phone:")):
            rest, role = [cand[0]] + cand[2:], cand[1].split(",")[0].strip()
            break
    if rest is None:
        return None
    row = {"unit": unit, "unitType": "town", "name": rest[0], "url": url}
    if role:
        row["role"] = role
    for k, ln in enumerate(rest):
        if ln == "Email:" and k + 1 < len(rest) and "@" in rest[k + 1]:
            row["email"] = rest[k + 1].strip()
        if ln == "Phone:" and k + 1 < len(rest):
            row["phone"] = rest[k + 1].strip()
    return row


PARSERS = {"saratoga": parse_saratoga, "schoharie": parse_schoharie,
           "warren": parse_warren, "delaware": parse_delaware,
           "wayne": parse_wayne, "fulton": parse_fulton,
           "wyoming": parse_wyoming}


def units_of(county):
    """{unit key: MUNI_TYPE} for every town and city of `county`.

    A UNIT IS KEYED BY ITS NAME UNLESS TWO UNITS OF THE COUNTY SHARE IT.
    Fulton has a city and a town both called Johnstown (and Chenango a city
    and a town of Norwich), and a name-keyed map silently kept one of each
    pair. Those units are keyed "Johnstown (city)" and "Johnstown (town)",
    which the app looks up first; every other unit keeps its bare name, so
    no shipped key moved.
    """
    with open(FABRIC, encoding="utf-8") as f:
        feats = json.load(f)["features"]
    pairs = [(p["NAME"], p["MUNI_TYPE"])
             for p in (x.get("properties") or {} for x in feats)
             if p.get("COUNTY") == county]
    names = [n for n, _ in pairs]
    return {("%s (%s)" % (n, t) if names.count(n) > 1 else n): t
            for n, t in pairs}


def unit_key(name, kind, units):
    """The key `units_of` gave the unit called `name` of type `kind`."""
    both = "%s (%s)" % (name, kind)
    return both if both in units else name


def fetch_page(url):
    """One page, retried twice after a reset connection and never after a 403.

    LIVINGSTON'S AND WAYNE'S HOSTS RESET CONNECTIONS (measured 2026-10-01 and
    again 2026-10-26, each serving the same page on the next attempt), and
    Livingston is seventeen fetches a run, so one reset would otherwise end
    the whole weekly refresh. An HTTP error is an answer and is not retried.
    """
    import time
    import urllib.error
    require_robots_once(url, UA_ROSTER_BOT, label="ny-supervisors")
    for attempt in range(3):
        try:
            body = fetch_stdlib(url, headers={"User-Agent": UA_ROSTER_BOT},
                                timeout=45)
            break
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    if isinstance(body, bytes):
        body = body.decode("utf-8", "replace")
    return body


def wyoming_roster_lines(board_html):
    """The roster PDF's lines, found by its link on the board page.

    The link's own words are "<year> Roster", so the run reads whichever
    roster the county currently links rather than a stored address that
    would go on answering with last year's document.
    """
    import urllib.parse
    import urllib.request
    import pymupdf
    hrefs = re.findall(
        r'<a[^>]+href="([^"]*DocumentCenter/View/[^"]+)"[^>]*>\s*(\d{4})\s+Roster\s*</a>',
        board_html, re.I)
    if not hrefs:
        raise SystemExit("ny-supervisor-scraper: wyoming board page links no "
                         "'<year> Roster' document")
    href, year = max(hrefs, key=lambda h: h[1])
    url = urllib.parse.urljoin(SOURCES["wyoming"]["url"], href)
    require_robots_once(url, UA_ROSTER_BOT, label="ny-supervisors")
    req = urllib.request.Request(url, headers={"User-Agent": UA_ROSTER_BOT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        pdf = resp.read()
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    print("ny-supervisor-scraper: wyoming — reading the %s Roster, %s, %d pages"
          % (year, url, doc.page_count))
    lines = []
    # The supervisors table is on the third page; reading the first five
    # keeps a page shuffled by a year's edit in reach without reaching the
    # town and village officers further in, whose rows share its shape.
    for page in list(doc)[:5]:
        lines += [ln.strip() for ln in page.get_text().splitlines() if ln.strip()]
    return lines


def scrape(key):
    src = SOURCES[key]
    units = units_of(src["county"])
    if key == "livingston":
        members = []
        # Seventeen pages from one host: read a second apart. Unpaced, the
        # host reset the connection partway through on 2026-10-26.
        for n, (unit, path) in enumerate(sorted(LIVINGSTON_PAGES.items())):
            if n:
                time.sleep(1.5)
            url = LIVINGSTON_BASE + path
            row = parse_livingston_page(visible_lines(fetch_page(url)), unit, url)
            if row:
                members.append(row)
    else:
        body = fetch_page(src["url"])
        if key == "wyoming":
            members = parse_wyoming(wyoming_roster_lines(body), units)
        else:
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
    # ONE COUNTY THAT FAILS DOES NOT END THE RUN. Delaware's page answered
    # this client 200 on 2026-10-16 and 403 from 2026-10-23, and because one
    # exception here ended the whole scrape, the four counties that still
    # served went unrefreshed with it. A county that fails is recorded with
    # its error, the builder carries its last shipped record forward
    # (the preserve ruling of 2026-09-19), and the run fails only when EVERY
    # county failed, which is a broken scraper rather than a refusing host.
    out = {}
    for key in sorted(SOURCES):
        try:
            out[key] = scrape(key)
        except Exception as e:  # noqa: BLE001 — recorded, never swallowed
            out[key] = {"county": SOURCES[key]["county"], "error": repr(e)[:300]}
            print("ny-supervisor-scraper: %s — NOT READ: %s" % (key, out[key]["error"]))
            continue
        rec = out[key]
        print("ny-supervisor-scraper: %s — %d member(s) over %d unit(s)"
              % (key, len(rec["members"]), rec["units"]))
    if all("error" in r for r in out.values()):
        raise SystemExit("ny-supervisor-scraper: no county could be read")
    parent = os.path.dirname(os.path.abspath(dest))
    os.makedirs(parent, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    print("ny-supervisor-scraper: wrote %s" % dest)


if __name__ == "__main__":
    main()
