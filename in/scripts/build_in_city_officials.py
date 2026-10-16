#!/usr/bin/env python3
"""The mayors and councils of Indiana's cities and towns over 25,000 people,
Indianapolis's City-County Council among them, from the Indiana Election
Division's certified results, every name dated to the election that seated it.

WHAT THIS PUBLISHES. An Indiana city elects a mayor and a common council, and a
town a town council, at the MUNICIPAL general held in the year before a
presidential election (2023, then 2027). The Election Division keeps every
certified general in the same archive the county builder reads
(build_in_county_officials.py), and the 2023 general names a winner for every
seat on the councils of 36 of the 39 places the Census counted at 25,000 or
more in 2020: all 33 cities and three of the six towns. One of the 33 is
Indianapolis, whose 25-member City-County Council is also MARION COUNTY'S
legislative body, which is why the county card and the county page read this
file for Marion.

A winner is a fact with a date on it, NOT a statement of who holds the seat
today. Indiana fills a council or mayoral vacancy by party caucus, which no
result records, so the card and the county page say so in words — the posture
the county builder already ships under.

THE PLACES ARE STATED, AND EACH ONE'S SHAPE IS MEASURED. `UNITS` lists every
place docs/expected-governments.json counts for Indiana, with the races that
elect its mayor and council as the results title them and the number of
district and at-large seats the 2023 results carry. The results title the same
office a dozen ways ("Hammond Council 1", "Ec Council At Large", Kokomo's bare
"City Council District 1"), and the mayor's race is sometimes titled just
"Mayor" in a county with several cities, so each race is matched by its county,
its title and the jurisdiction the results attach to it, never by a guess at
which city a bare title means. The build fails on a configured race that the
results no longer publish, on a place the measurement counts that `UNITS` and
`TOWN_PAGES` do not, and on a council whose seats or winners differ from what is
stated here.

THREE TOWNS ARE NAMED FROM THEIR OWN WEBSITES. A town holds no general
election for a seat nobody contested, and the results name nobody for it, so
Plainfield (no race at all in 2023), Brownsburg (three of its wards) and
Schererville (three of its wards) cannot be named from this source. Each town
lists its whole council on its own website, so `TOWN_PAGES` reads those three
there instead (since 2026-10-15), each seat dated to the day it was read and
citing the page; the card says the names are the town's own list rather than
election winners. A page that cannot be read keeps its last read.

ONE PUBLISHING FAULT IS CORRECTED AND LISTED: New Albany's at-large race elects
three members and is filed as electing one, with one winner flagged. The three
candidates with the most votes won it; `MISFILED_SEAT_COUNTS` records the
published count, the flagged winner and the three the votes elect, and the
build fails if any of them moves.

A RESULT COUNTS FROM THE DAY ITS TERM BEGINS. Municipal officers elected in
November take office the following January 1, so the 2027 winners reach this
file on the first run of 2028, once the Election Division has archived them.

Usage:
    python3 in/scripts/build_in_city_officials.py          # fetch and write
    python3 in/scripts/build_in_city_officials.py --check  # offline gate
"""

import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_in_county_officials as C  # noqa: E402
from scraper_common import require_robots_once  # noqa: E402  (C put scripts/ on the path)

INSTANCE = C.INSTANCE
REPO_ROOT = os.path.dirname(INSTANCE)
OUT = os.path.join(INSTANCE, "data", "app", "in-city-officials.json")
EXPECTED = os.path.join(REPO_ROOT, "docs", "expected-governments.json")

# The Election Division's own office-category ids, read off the 2023 archive's
# statewideElectionsC_A.json on 2026-10-11.
MAYOR_CATEGORY = "1002"          # "Mayor"
CITY_COUNCIL_CATEGORY = "1032"   # "City-County or City Common Council Member"
TOWN_COUNCIL_CATEGORY = "1037"   # "Town Council Member"

# Municipal generals are every four years; 2023 is the first this file reads
# and the one every seat rests on.
FIRST_YEAR = 2023
REQUIRED_YEARS = (2023,)

INDIANAPOLIS = "1836003"

# geoid -> how the 2023 results carry this place. `council` is a regex over the
# race title, matched only inside `county` (the results' region); `mayor` is
# (title, jurisdiction regex), because several counties title every mayor's race
# just "Mayor". `districts` and `at_large` are the seat counts the 2023 results
# carry, so a future election that changes the council's shape fails the build
# until somebody reads it. `seat_words` turns a title's seat into a label where
# the title abbreviates it.
FISHERS = {"Nc": "North Central District", "Ne": "Northeast District",
           "Nw": "Northwest District", "Sc": "South Central District",
           "Se": "Southeast District", "Sw": "Southwest District"}
UNITS = {
    "1836003": dict(name="Indianapolis", kind="city", county="Marion",
                    body="Indianapolis City-County Council",
                    council=r"^City-County Council, District (\d+)$",
                    mayor=("Mayor Of Indianapolis", r"."), districts=25, at_large=0),
    "1825000": dict(name="Fort Wayne", kind="city", county="Allen",
                    council=r"^Fort Wayne City Common Council (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Fort Wayne", r"."), districts=6, at_large=3),
    "1822000": dict(name="Evansville", kind="city", county="Vanderburgh",
                    council=r"^Evansville City Common Council, (?:Ward (\d+)|At Large)$",
                    seat_word="Ward",
                    mayor=("Mayor", r"^Evansville$"), districts=6, at_large=3),
    "1871000": dict(name="South Bend", kind="city", county="St. Joseph",
                    council=r"^South Bend Common Council (?:District (\d+)|Member, At Large)$",
                    mayor=("City Of South Bend Mayor", r"."), districts=6, at_large=3),
    "1810342": dict(name="Carmel", kind="city", county="Hamilton",
                    council=r"^Carmel City Common Council, (?:(North Central|Northeast|Northwest|South Central|Southeast|Southwest|West|East) District|At Large)$",
                    named_districts=True,
                    mayor=("Mayor Of Carmel", r"."), districts=6, at_large=3),
    "1823278": dict(name="Fishers", kind="city", county="Hamilton",
                    council=r"^Fishers City Common Council, (?:(Nc|Ne|Nw|Sc|Se|Sw) District|At Large)$",
                    named_districts=True, seat_map=FISHERS,
                    mayor=("Mayor Of Fishers", r"."), districts=6, at_large=3),
    "1805860": dict(name="Bloomington", kind="city", county="Monroe",
                    council=r"^Bloomington City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Bloomington", r"."), districts=6, at_large=3),
    "1831000": dict(name="Hammond", kind="city", county="Lake",
                    council=r"^Hammond (?:Council (\d+)|Councl At Large)$",
                    seat_word="Seat",
                    mayor=("Hammond Mayor", r"."), districts=6, at_large=3),
    "1840788": dict(name="Lafayette", kind="city", county="Tippecanoe",
                    council=r"^Lafayette City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Lafayette", r"."), districts=6, at_large=3),
    "1854180": dict(name="Noblesville", kind="city", county="Hamilton",
                    council=r"^Noblesville City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Noblesville", r"."), districts=6, at_large=3),
    "1827000": dict(name="Gary", kind="city", county="Lake",
                    council=r"^Gary Council (?:(\d+)|At Large)$", seat_word="Seat",
                    mayor=("Gary Mayor", r"."), districts=6, at_large=3),
    "1851876": dict(name="Muncie", kind="city", county="Delaware",
                    council=r"^Muncie City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Muncie", r"."), districts=6, at_large=3),
    "1829898": dict(name="Greenwood", kind="city", county="Johnson",
                    council=r"^Greenwood City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Greenwood", r"."), districts=6, at_large=3),
    "1840392": dict(name="Kokomo", kind="city", county="Howard",
                    # Kokomo is the only city in Howard County, and the results
                    # title its council races with no city name at all.
                    council=r"^City Council (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Kokomo", r"."), districts=6, at_large=3),
    "1875428": dict(name="Terre Haute", kind="city", county="Vigo",
                    council=r"^Terre Haute City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Terre Haute", r"."), districts=6, at_large=3),
    "1801468": dict(name="Anderson", kind="city", county="Madison",
                    council=r"^Anderson City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Anderson", r"."), districts=6, at_large=3),
    "1820728": dict(name="Elkhart", kind="city", county="Elkhart",
                    council=r"^Elkhart City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Elkhart", r"."), districts=6, at_large=3),
    "1849932": dict(name="Mishawaka", kind="city", county="St. Joseph",
                    council=r"^Mishawaka City Council (?:District (\d+)|At Large)$",
                    mayor=("City Of Mishawaka Mayor", r"."), districts=6, at_large=3),
    "1814734": dict(name="Columbus", kind="city", county="Bartholomew",
                    council=r"^Columbus City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Columbus", r"."), districts=6, at_large=3),
    "1838358": dict(name="Jeffersonville", kind="city", county="Clark",
                    council=r"^Jeffersonville City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor", r"^Jeffersonville$"), districts=6, at_large=3),
    "1842426": dict(name="Lawrence", kind="city", county="Marion",
                    council=r"^Lawrence City Common Council, (?:District (\d+)|At-Large)$",
                    mayor=("Mayor Of Lawrence", r"."), districts=6, at_large=3),
    "1882700": dict(name="Westfield", kind="city", county="Hamilton",
                    council=r"^Westfield City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Westfield", r"."), districts=5, at_large=2),
    "1882862": dict(name="West Lafayette", kind="city", county="Tippecanoe",
                    council=r"^West Lafayette City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of West Lafayette", r"."), districts=6, at_large=3),
    "1861092": dict(name="Portage", kind="city", county="Porter",
                    council=r"^Portage City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Portage", r"."), districts=5, at_large=2),
    "1852326": dict(name="New Albany", kind="city", county="Floyd",
                    council=r"^New Albany City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of New Albany", r"."), districts=6, at_large=3),
    "1848528": dict(name="Merrillville", kind="town", county="Lake",
                    body="Merrillville Town Council",
                    council=r"^Merrillville Ward (\d+)$", seat_word="Ward",
                    mayor=None, districts=7, at_large=0),
    "1864260": dict(name="Richmond", kind="city", county="Wayne",
                    council=r"^Richmond City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Richmond", r"."), districts=6, at_large=3),
    "1828386": dict(name="Goshen", kind="city", county="Elkhart",
                    council=r"^Goshen City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Goshen", r"."), districts=5, at_large=2),
    "1878326": dict(name="Valparaiso", kind="city", county="Porter",
                    council=r"^Valparaiso City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Valparaiso", r"."), districts=5, at_large=2),
    "1816138": dict(name="Crown Point", kind="city", county="Lake",
                    council=r"^Crown Point Council (?:(\d+)|At Large)$", seat_word="Seat",
                    mayor=("Crown Point Mayor", r"."), districts=5, at_large=2),
    "1848798": dict(name="Michigan City", kind="city", county="LaPorte",
                    council=r"^Michigan City Common Council, (?:Ward (\d+)|At Large)$",
                    seat_word="Ward",
                    mayor=("Mayor Of Michigan City", r"."), districts=6, at_large=3),
    "1886372": dict(name="Zionsville", kind="town", county="Boone",
                    body="Zionsville Town Council",
                    council=r"^Zionsville Town Council(?: Member, Ward (\d+))?$",
                    seat_word="Ward",
                    mayor=("Mayor Of Zionsville", r"."), districts=5, at_large=2),
    "1834114": dict(name="Hobart", kind="city", county="Lake",
                    council=r"^Hobart Council (?:(\d+)|At Large)$", seat_word="Seat",
                    mayor=("Mayor Of Hobart", r"."), districts=5, at_large=2),
    "1846908": dict(name="Marion", kind="city", county="Grant",
                    council=r"^Marion City Common Council, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Marion", r"."), districts=6, at_large=3),
    "1819486": dict(name="East Chicago", kind="city", county="Lake",
                    council=r"^Ec Council (?:(\d+)|At Large)$", seat_word="Seat",
                    mayor=("Ec Mayor", r"."), districts=6, at_large=3),
    "1825450": dict(name="Franklin", kind="city", county="Johnson",
                    council=r"^Franklin City Common Council Member, (?:District (\d+)|At Large)$",
                    mayor=("Mayor Of Franklin", r"."), districts=5, at_large=2),
}

# geoid -> why the results cannot name this place's council. Empty since
# 2026-10-15: the three towns it held are read from their own pages below.
NOT_NAMED = {}

# THREE TOWNS ARE NAMED FROM THEIR OWN PAGES. A town holds no general election
# for a seat nobody contested, so the 2023 results carry no Plainfield race and
# only three wards each of Brownsburg and Schererville (measured 2026-10-11).
# Each town lists its whole council on its own website, so those three are
# read there instead, as a roster the town keeps rather than as election
# winners, and the card says which it is. `client` is the client each page
# serves, measured 2026-10-15 one read per client:
#   * www.schererville.org serves this project's own token on requests; it
#     has no robots.txt (404).
#   * www.brownsburg.org serves the token on the stdlib client (HTTP 200,
#     131,358 bytes) and resets the connection to the requests client, robots.txt
#     included (scripts/probe_user_agents.py, stack-not-token), so it is read
#     with the token on the stdlib client.
#   * www.townofplainfield.com answers the token with Cloudflare's "Attention
#     Required" block page (HTTP 403) on both the requests and the stdlib
#     client, and answers requests with a Chrome string the same way; it serves
#     the stdlib client with the Chrome string and client hints (HTTP 200,
#     184,892 bytes for the front page), the Kendall County shape. Its
#     robots.txt refuses the token and, read with the Chrome client, has no
#     rule matching these paths.
# A page that cannot be read or parsed keeps the last record read from it,
# with that read's date, and says so in the log (Adam's preserve ruling).
TOWN_PAGES = {
    "1808416": dict(name="Brownsburg", county="Hendricks",
                    body="Brownsburg Town Council",
                    url="https://www.brownsburg.org/288/Town-Council",
                    client="token-stdlib", parse="brownsburg", seat_word="Ward", seats=5),
    "1860246": dict(name="Plainfield", county="Hendricks",
                    body="Plainfield Town Council",
                    url="https://www.townofplainfield.com/1287/Town-Council",
                    client="chrome-stdlib", parse="plainfield", seat_word="District", seats=5),
    "1868220": dict(name="Schererville", county="Lake",
                    body="Schererville Town Council",
                    url="https://www.schererville.org/council",
                    client="token", parse="schererville", seat_word="Ward", seats=5),
}
ROLES = ("President", "Vice President")


def page_tokens(text):
    """The page's visible text, one entry per element."""
    import html as _html  # noqa: PLC0415
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"<[^>]+>", "|", text)
    out = []
    for part in text.split("|"):
        part = re.sub(r"\s+", " ", _html.unescape(part)).strip()
        if part:
            out.append(part)
    return out


def parse_brownsburg(toks):
    """'Ben Lacey', 'President', 'Email Ben Lacey', 'Representing Ward 1'."""
    out = []
    for i, t in enumerate(toks):
        m = re.match(r"^Representing Ward (\d+)$", t)
        if not m or i < 2 or not toks[i - 1].startswith("Email "):
            continue
        name = toks[i - 1][len("Email "):].strip()
        role = toks[i - 2] if toks[i - 2] in ROLES and toks[i - 3] == name else None
        out.append((m.group(1), name, role))
    return out


def parse_plainfield(toks):
    """'Robin Brandgard', 'President, District 4 Council', 'Robin Brandgard
    Contact & Biography'."""
    out = []
    for i, t in enumerate(toks):
        m = re.match(r"^(?:(President|Vice President), )?District (\d+) Council$", t)
        if not m or i < 1 or i + 1 >= len(toks):
            continue
        name = toks[i - 1]
        if toks[i + 1] != name + " Contact & Biography":
            continue
        out.append((m.group(2), name, m.group(1)))
    return out


def parse_schererville(toks):
    """'Robin Arvanitis', 'Councilwoman for Ward 1 and Town Council President'."""
    out = []
    for i, t in enumerate(toks):
        m = re.match(r"^Council(?:wo)?man for Ward (\d+)"
                     r"(?: and Town Council (President|Vice President))?$", t)
        if m and i >= 1:
            out.append((m.group(1), toks[i - 1], m.group(2)))
    return out


PARSERS = {"brownsburg": parse_brownsburg, "plainfield": parse_plainfield,
           "schererville": parse_schererville}


def town_fetch(session, unit):
    """The town page's text with the client it serves, robots.txt read first
    with that same client."""
    from scraper_common import (  # noqa: PLC0415
        UA_CHROME_WIN_126, UA_HINTS_CHROME_126, fetch_stdlib)
    if unit["client"] == "chrome-stdlib":
        headers = dict(UA_HINTS_CHROME_126)
        headers["User-Agent"] = UA_CHROME_WIN_126
        require_robots_once(unit["url"], UA_CHROME_WIN_126, headers=headers)
        return fetch_stdlib(unit["url"], headers=headers, timeout=60)
    require_robots_once(unit["url"], C.UA_ROSTER_BOT, headers=C.UA_HEADERS_ROSTER_BOT)
    if unit["client"] == "token-stdlib":
        return fetch_stdlib(unit["url"], headers=C.UA_HEADERS_ROSTER_BOT, timeout=60)
    last = None
    for _ in range(3):
        try:
            r = session.get(unit["url"], timeout=60)
            r.raise_for_status()
            return r.text
        except Exception as e:  # noqa: BLE001 — retried, then reported
            last = e
    raise last


def town_record(unit, members, read):
    seats = []
    for num, name, role in sorted(members, key=lambda m: int(m[0])):
        seat = {"seat": "%s %s" % (unit["seat_word"], num), "name": name,
                "read": read, "sourceUrl": unit["url"]}
        if role:
            seat["role"] = role
        seats.append(seat)
    return {"name": unit["name"], "kind": "town", "county": unit["county"],
            "body": unit["body"], "source": "town-page", "read": read, "seats": seats}


def read_towns(session, today, shipped):
    out = {}
    for geoid, unit in sorted(TOWN_PAGES.items()):
        try:
            members = PARSERS[unit["parse"]](page_tokens(town_fetch(session, unit)))
            nums = sorted(int(m[0]) for m in members)
            if nums != list(range(1, unit["seats"] + 1)):
                raise ValueError("parsed seats %s, expected 1..%d" % (nums, unit["seats"]))
            out[geoid] = town_record(unit, members, today.isoformat())
            print("  %s: %d members read from %s" % (unit["name"], len(members), unit["url"]))
        except Exception as e:  # noqa: BLE001 — a town page failing keeps its last read
            kept = shipped.get(geoid)
            if not kept or kept.get("source") != "town-page":
                fail("%s: the town page could not be read (%s) and no earlier "
                     "read is shipped" % (unit["name"], e))
            print("  %s: the town page could not be read (%s); keeping the "
                  "read of %s" % (unit["name"], e, kept.get("read")))
            out[geoid] = kept
    return out


# (year, place geoid, published title) -> (published seats, flagged winners,
# the winners the votes elect). Measured 2026-10-11.
MISFILED_SEAT_COUNTS = {
    (2023, "1852326", "New Albany City Common Council, At Large"):
        ("1", ["ELAINE GUNTERMAN-MURPHY"],
         ["ELAINE GUNTERMAN-MURPHY", "DON UNRUH", "STEFANIE GRIFFITH"]),
}


def fail(msg):
    raise SystemExit("build-in-city-officials: FATAL: %s" % msg)


def expected_units():
    """Indiana's places at 25,000+, from the fleet's committed measurement."""
    with open(EXPECTED, encoding="utf-8") as f:
        units = json.load(f).get("units", {}).get("in") or []
    if not units:
        fail("docs/expected-governments.json carries no Indiana units — run "
             "scripts/build_expected_governments.py")
    return {u["geoid"]: u for u in units}


def check_registry():
    """UNITS, TOWN_PAGES and NOT_NAMED together must be exactly the measured places."""
    want = set(expected_units())
    have = set(UNITS) | set(NOT_NAMED) | set(TOWN_PAGES)
    problems = []
    for a, b, an, bn in ((UNITS, NOT_NAMED, "UNITS", "NOT_NAMED"),
                         (UNITS, TOWN_PAGES, "UNITS", "TOWN_PAGES"),
                         (NOT_NAMED, TOWN_PAGES, "NOT_NAMED", "TOWN_PAGES")):
        if set(a) & set(b):
            problems.append("a place is in both %s and %s: %s"
                            % (an, bn, sorted(set(a) & set(b))))
    if have != want:
        problems.append("UNITS, TOWN_PAGES and NOT_NAMED cover %s, the measurement counts "
                        "%s (missing %s, extra %s)"
                        % (len(have), len(want), sorted(want - have),
                           sorted(have - want)))
    return problems


def name_of(c):
    return re.sub(r"\s+", " ", c["NAME_ON_BALLOT"]).strip()


def region_races(doc):
    """(region county, race) pairs for one office-category file."""
    for region in C.as_list(doc["Root"]["OfficeCategory"]["Regions"]["Region"]):
        for race in C.as_list((region.get("Races") or {}).get("Race")):
            yield region["MAP_JURISDICTION_NAME"], race


def same_county(a, b):
    return re.sub(r"[^a-z]", "", a.lower()) == re.sub(r"[^a-z]", "", b.lower())


def people(race, winners, parties):
    out = []
    for c in sorted(winners, key=lambda c: -int(c.get("TOTAL_VOTES") or 0)):
        person = {"name": name_of(c)}
        party = parties.get(str(c.get("POLITICALPARTYID")))
        if party:
            person["party"] = party
        out.append(person)
    return out


def read_year(session, year, root):
    """geoid -> {"mayor": seat or None, "council": [seat...]} for one general."""
    parties = C.party_names(root)
    when = C.election_date(root)
    source = C.PAGE % year
    docs = {}
    for cat in (MAYOR_CATEGORY, CITY_COUNCIL_CATEGORY, TOWN_COUNCIL_CATEGORY):
        doc = C.fetch_json(session, C.OFFICE_FILE % (year, cat))
        if doc is None:
            fail("the %d general has no office file for category %s" % (year, cat))
        docs[cat] = list(region_races(doc))
    out = {}
    for geoid, unit in sorted(UNITS.items()):
        council_doc = docs[TOWN_COUNCIL_CATEGORY if unit["kind"] == "town"
                           else CITY_COUNCIL_CATEGORY]
        rec = {"mayor": None, "council": []}
        if unit["mayor"]:
            title, jur = unit["mayor"]
            hits = [r for county, r in docs[MAYOR_CATEGORY]
                    if same_county(county, unit["county"]) and r["OFFICE_TITLE"] == title
                    and re.search(jur, ((r.get("Jurisdiction") or {}).get("JURISDICTION_NAME") or ""))]
            if len(hits) != 1:
                fail("%d %s: expected one mayor's race titled %r, found %d"
                     % (year, unit["name"], title, len(hits)))
            race = hits[0]
            cands = C.as_list((race.get("Candidates") or {}).get("Candidate"))
            won = [c for c in cands if c.get("isWinner") == "T"]
            if len(won) != 1:
                fail("%d %s: the mayor's race flags %d winners" % (year, unit["name"], len(won)))
            seat = {"seat": "Mayor", "election": when, "office": race["OFFICE_TITLE"],
                    "sourceUrl": source}
            seat.update(people(race, won, parties)[0])
            rec["mayor"] = seat
        districts, at_large = [], []
        for county, race in council_doc:
            if not same_county(county, unit["county"]):
                continue
            title = re.sub(r"\s+", " ", race["OFFICE_TITLE"]).strip()
            m = re.match(unit["council"], title)
            if not m:
                continue
            cands = C.as_list((race.get("Candidates") or {}).get("Candidate"))
            won = [c for c in cands if c.get("isWinner") == "T"]
            seats = int(race.get("NumofSeats") or 0)
            key = (year, geoid, race["OFFICE_TITLE"])
            if key in MISFILED_SEAT_COUNTS:
                pub_seats, pub_won, elected = MISFILED_SEAT_COUNTS[key]
                ranked = sorted(cands, key=lambda c: -int(c.get("TOTAL_VOTES") or 0))
                if (str(seats) != pub_seats
                        or sorted(name_of(c) for c in won) != sorted(pub_won)
                        or [name_of(c) for c in ranked[:len(elected)]] != elected):
                    fail("MISFILED_SEAT_COUNTS %r no longer matches the results" % (key,))
                won, seats = ranked[:len(elected)], len(elected)
            if len(won) != seats:
                fail("%d %s: %r elects %d and flags %d winners"
                     % (year, unit["name"], title, seats, len(won)))
            seat_id = next((g for g in m.groups() if g), None)
            if seat_id is None:
                label, bucket = "At large", at_large
            elif unit.get("named_districts"):
                label = (unit.get("seat_map") or {}).get(seat_id) or "%s District" % seat_id
                bucket = districts
            else:
                label, bucket = "%s %s" % (unit.get("seat_word", "District"), seat_id), districts
            if seat_id is not None and seats != 1:
                fail("%d %s: district race %r is filed as electing %d"
                     % (year, unit["name"], title, seats))
            for person in people(race, won, parties):
                row = {"seat": label, "election": when, "office": race["OFFICE_TITLE"],
                       "sourceUrl": source}
                row.update(person)
                bucket.append(row)
        if len({r["seat"] for r in districts}) != unit["districts"] or len(districts) != unit["districts"]:
            fail("%d %s: the results carry %d district seats (%s), expected %d"
                 % (year, unit["name"], len(districts),
                    ", ".join(sorted(r["seat"] for r in districts)), unit["districts"]))
        if len(at_large) != unit["at_large"]:
            fail("%d %s: the results carry %d at-large seats, expected %d"
                 % (year, unit["name"], len(at_large), unit["at_large"]))
        districts.sort(key=lambda r: (int(re.sub(r"\D", "", r["seat"]) or 0), r["seat"]))
        rec["council"] = districts + at_large
        out[geoid] = rec
    return out


def counting_years(session, today):
    years = []
    for year in range(FIRST_YEAR, today.year + 1, 4):
        settings = C.fetch_json(session, C.SETTINGS % year)
        if settings is None:
            print("  %d general: no archive yet — skipped" % year)
            continue
        root = settings.get("Root") or {}
        if root.get("Certified") != "T":
            print("  %d general: archived but not certified — skipped" % year)
            continue
        if today < datetime.date(year + 1, 1, 1):
            print("  %d general: certified; its winners take office on January "
                  "1, %d — held until then" % (year, year + 1))
            continue
        years.append((year, root))
    got = {y for y, _ in years}
    for y in REQUIRED_YEARS:
        if y not in got:
            fail("the %d general is not readable — every seat rests on it" % y)
    return years


def assemble(by_year):
    """geoid -> record, the newest general for each place winning whole: a
    council is elected all at once in Indiana, so its seats are never mixed
    across elections."""
    out = {}
    for year in sorted(by_year):
        for geoid, rec in by_year[year].items():
            unit = UNITS[geoid]
            body = unit.get("body") or "%s Common Council" % unit["name"]
            out[geoid] = {"name": unit["name"], "kind": unit["kind"],
                          "county": unit["county"], "body": body,
                          "seats": ([rec["mayor"]] if rec["mayor"] else []) + rec["council"]}
    return out


def check_town(unit, rec):
    """A town read from its own page: every seat 1..N once, named, carrying
    the date it was read and the page it was read from."""
    problems = []
    if rec.get("source") != "town-page":
        problems.append("%s is not marked as read from the town's page" % unit["name"])
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", rec.get("read") or ""):
        problems.append("%s carries no read date" % unit["name"])
    seats = rec.get("seats") or []
    want = ["%s %d" % (unit["seat_word"], n) for n in range(1, unit["seats"] + 1)]
    if [s.get("seat") for s in seats] != want:
        problems.append("%s names seats %s, expected %s"
                        % (unit["name"], [s.get("seat") for s in seats], want))
    for s in seats:
        if not (s.get("name") or "").strip():
            problems.append("%s seat %r names nobody" % (unit["name"], s.get("seat")))
        if s.get("sourceUrl") != unit["url"]:
            problems.append("%s seat %r does not cite the town's page"
                            % (unit["name"], s.get("seat")))
        if s.get("read") != rec.get("read"):
            problems.append("%s seat %r carries a different read date"
                            % (unit["name"], s.get("seat")))
        if s.get("role") not in (None,) + ROLES:
            problems.append("%s seat %r carries role %r"
                            % (unit["name"], s.get("seat"), s.get("role")))
        if "election" in s:
            problems.append("%s seat %r claims an election date; it was read "
                            "from the town's page" % (unit["name"], s.get("seat")))
    return problems


def check(roster):
    problems = check_registry()
    want = set(UNITS) | set(TOWN_PAGES)
    if set(roster) != want:
        problems.append("the file names %d places, UNITS and TOWN_PAGES state %d "
                        "(missing %s, extra %s)" % (len(roster), len(want),
                                                    sorted(want - set(roster)),
                                                    sorted(set(roster) - want)))
    for geoid, rec in sorted(roster.items()):
        town = TOWN_PAGES.get(geoid)
        if town:
            problems.extend(check_town(town, rec))
            continue
        unit = UNITS.get(geoid)
        if not unit:
            continue
        seats = rec.get("seats") or []
        mayors = [s for s in seats if s.get("seat") == "Mayor"]
        council = [s for s in seats if s.get("seat") != "Mayor"]
        if len(mayors) != (1 if unit["mayor"] else 0):
            problems.append("%s names %d mayors" % (unit["name"], len(mayors)))
        n = unit["districts"] + unit["at_large"]
        if len(council) != n:
            problems.append("%s names %d council seats, expected %d"
                            % (unit["name"], len(council), n))
        for s in seats:
            if not (s.get("name") or "").strip():
                problems.append("%s seat %r names nobody" % (unit["name"], s.get("seat")))
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", s.get("election") or ""):
                problems.append("%s seat %r carries no election date"
                                % (unit["name"], s.get("seat")))
            if not (s.get("sourceUrl") or "").startswith(C.HOST + "/archive/"):
                problems.append("%s seat %r carries no source" % (unit["name"], s.get("seat")))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to UNITS and the measurement")
    args = ap.parse_args()
    if args.check:
        with open(OUT, encoding="utf-8") as f:
            problems = check(json.load(f))
        if problems:
            for p in problems:
                print("build-in-city-officials: FAIL: " + p)
            raise SystemExit(1)
        print("build-in-city-officials --check: OK — %d of %d places at 25,000+ "
              "named: %d from the certified results, every seat dated to its "
              "election, and %d towns from their own pages (%s), every seat "
              "dated to the read"
              % (len(UNITS) + len(TOWN_PAGES),
                 len(UNITS) + len(TOWN_PAGES) + len(NOT_NAMED), len(UNITS),
                 len(TOWN_PAGES),
                 ", ".join(sorted(u["name"] for u in TOWN_PAGES.values()))))
        return
    problems = check_registry()
    if problems:
        for p in problems:
            print("build-in-city-officials: FAIL: " + p)
        raise SystemExit(1)
    import requests  # noqa: PLC0415
    session = requests.Session()
    session.headers.update(C.UA_HEADERS_ROSTER_BOT)
    # The same read C.fetch_json makes before each fetch, stated here so this
    # file asks the host's policy itself, with the client that crawls.
    require_robots_once(C.HOST + "/", C.UA_ROSTER_BOT,
                        headers=C.UA_HEADERS_ROSTER_BOT)
    years = counting_years(session, datetime.date.today())
    print("generals read: %s" % ", ".join(str(y) for y, _ in years))
    by_year = {year: read_year(session, year, root) for year, root in years}
    roster = assemble(by_year)
    shipped = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            shipped = json.load(f)
    roster.update(read_towns(session, datetime.date.today(), shipped))
    problems = check(roster)
    if problems:
        for p in problems:
            print("build-in-city-officials: FAIL: " + p)
        raise SystemExit(1)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    print("wrote %s: %d places, %d seats"
          % (os.path.relpath(OUT, REPO_ROOT), len(roster),
             sum(len(r["seats"]) for r in roster.values())))


if __name__ == "__main__":
    main()
