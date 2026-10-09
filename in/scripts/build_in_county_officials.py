#!/usr/bin/env python3
"""Indiana's county commissioners and county council members, from the
Indiana Election Division's certified results, every name dated to the
election that seated it.

WHAT THIS PUBLISHES AND WHAT IT DOES NOT. An Indiana county outside
Indianapolis is run by two elected bodies: a three-member board of
commissioners and a seven-member county council (nine in St. Joseph County,
seven districts and no at-large seats in Lake). The Election Division's
results site, enr.indianavoters.in.gov, keeps every certified general in an
archive of plain JSON files, one per office category, and between them the
2022 and 2024 generals name a winner for every seat on both bodies in 91 of
the 92 counties: commissioners serve staggered four-year terms, council
district seats were on the 2022 ballot and the three at-large seats on 2024's.

A winner is a fact with a date on it. It is NOT a statement of who holds the
seat today: Indiana fills a vacancy by party caucus rather than by special
election, so somebody appointed since the election does not appear in any
result, and the person who won still shows here. So every seat names its
election, and the card and the county page say so in words — the posture Adam
opened for Michigan's certified-returns route on 2026-09-22 and Minnesota
ships its 447 commissioners under (mn/scripts/build_mn_commissioner_roster.py).

MARION COUNTY IS NOT IN EITHER FILE, ON PURPOSE. Indianapolis and Marion County
are consolidated, and the county's legislative body is the 25-member
City-County Council, elected in the 2023 municipal general. Neither office
category this builder reads carries Marion, and folding a city council into a
file of county commissioners would put the wrong heading over it. It is gap
in-county-government's remaining county.

A RESULT COUNTS FROM THE DAY ITS TERM BEGINS, NOT THE DAY IT IS CERTIFIED.
County officers elected in November take office the following January 1, so a
general is read only once that January has come. The November 2026 winners
therefore reach this file on the first run of 2027, and until then the 2022
winners they replace are still the people holding those seats. The archive
directory for a general appears once the Election Division archives it; a
year with no archive yet is printed and skipped, and the next run picks it up.

ONE PUBLISHING FAULT IS CORRECTED AND EVERY INSTANCE OF IT IS LISTED. In nine
2022 council races the results give the race the WHOLE council's seat count
(7, or 9 in St. Joseph) instead of 1, and flag every candidate as a winner.
Each of those races is for one district seat, so the candidate with the most
votes won it; `MISFILED_SEAT_COUNTS` lists every such race with the winners
the results flag and the one the votes elect, and the build fails on a race
showing the fault that the table does not list, or on an entry that no longer
matches what the results publish. No other race is corrected.

A RACE WHOSE TITLE DOES NOT SAY WHICH SEAT IT IS keeps its winner and says so.
Daviess County's four 2022 council races are all titled "County Council
Member", Clinton's 2022 commissioner race "County Commissioner", and Boone's
"Dist 36" names a district Boone does not have. `UNSTATED_TITLES` lists each
with its reason; the seat is labelled with the title as published rather than
a district this project would have to guess, and a new title the parser cannot
place fails the build.

Usage:
    python3 in/scripts/build_in_county_officials.py          # fetch and write
    python3 in/scripts/build_in_county_officials.py --check  # offline gate
"""

import argparse
import datetime
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from scraper_common import (  # noqa: E402
    UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, require_robots_once)

HOST = "https://enr.indianavoters.in.gov"
ARCHIVE = HOST + "/archive/%dGeneral"
SETTINGS = ARCHIVE + "/data/settings.json"
OFFICE_FILE = ARCHIVE + "/data/OffCatC_%s_A.json"
PAGE = ARCHIVE + "/index.html"
REQUEST_TIMEOUT = 60
PACE_SECONDS = 0.5

# The Election Division's own office-category ids, read off each archive's
# statewideElectionsC_A.json on 2026-10-09.
COMMISSIONER_CATEGORY = "1024"   # "County Commissioner"
COUNCIL_CATEGORY = "1033"        # "County Council Member"

# Every seat on both bodies was on the 2022 or the 2024 ballot, so 2022 is the
# floor and both are required.
FIRST_YEAR = 2022
REQUIRED_YEARS = (2022, 2024)

STATE_FIPS = "18"
COUNTIES_FILE = os.path.join(INSTANCE, "data", "app", "state-counties.json")
COMMISSIONERS_OUT = os.path.join(INSTANCE, "data", "app", "in-county-commissioners.json")
COUNCILS_OUT = os.path.join(INSTANCE, "data", "app", "in-county-councils.json")

# The one county neither office category carries, and why.
NOT_IN_RESULTS = {
    "Marion": "Indianapolis and Marion County are consolidated; the county's "
              "legislative body is the City-County Council, elected in the "
              "municipal general, not a board of commissioners or a county council",
}

# Seats per body, per county, where the county differs from the statewide
# shape (IC 36-2-2: three commissioners; IC 36-2-3: seven council members).
COMMISSIONER_SEATS = 3
COUNCIL_SEATS = 7
COUNCIL_SEATS_BY_COUNTY = {"St. Joseph": 9}

# (year, county, published title) -> the winners the results flag and the one
# the votes elect. Measured 2026-10-09 on the 2022 archive.
MISFILED_SEAT_COUNTS = {
    (2022, "Pulaski", "Pulaski County Council, District 3"):
        ("7", ["Jerome C Locke", 'Robert M "Bob" Keller Jr.', "Josh Stacy"], "Jerome C Locke"),
    (2022, "Spencer", "Spencer County Council, District 3"):
        ("7", ["DAVID FROMME", "TODD GRUNDHOEFER"], "DAVID FROMME"),
    (2022, "Spencer", "Spencer County Council, District 4"):
        ("7", ["JUSTIN GROSE", "TODD B RUXER"], "JUSTIN GROSE"),
    (2022, "St. Joseph", "St. Joseph County Council, District A"):
        ("9", ["Joe Thomas", "Bobby K Kruszynski Jr"], "Joe Thomas"),
    (2022, "St. Joseph", "St. Joseph County Council, District B"):
        ("9", ["Amy Drake", "Corey Noland"], "Amy Drake"),
    (2022, "St. Joseph", "St. Joseph County Council, District E"):
        ("9", ["Diana Hess", "Jason Kring"], "Diana Hess"),
    (2022, "St. Joseph", "St. Joseph County Council, District H"):
        ("9", ["Bryan J Tanner", "Mark A Voelker"], "Bryan J Tanner"),
    (2022, "Washington", "Washington County Council, District 3"):
        ("7", ["Preston L Shell", "RHONDA ANN GREENE"], "Preston L Shell"),
    (2022, "Washington", "Washington County Council, District 4"):
        ("7", ["Karen Wischmeier", "David Norton"], "Karen Wischmeier"),
}

# (year, county, published title) -> why the seat cannot be placed. Measured
# 2026-10-09. The seat ships labelled with the title as published.
UNSTATED_TITLES = {
    (2022, "Clinton", "County Commissioner"):
        "the race's title names no district",
    (2024, "Ohio", "County Commissioner"):
        "the race's title names no district",
    (2022, "Daviess", "County Council Member"):
        "three of Daviess County's four 2022 council races carry this same "
        "title, none naming a district",
    (2022, "Daviess", "County County Member"):
        "the race's title names no district",
    (2022, "Boone", "Boone County Council Dist 36"):
        "the title reads \"Dist 36\" and Boone County has four council districts",
    (2022, "Ohio", "Ohio County Council"):
        "the race's title names no district",
}
# Ohio's 2024 council race is titled "Ohio County Council" too, and it is the
# three at-large seats: the only three-seat council race a county has.
AT_LARGE_TITLES = {(2024, "Ohio", "Ohio County Council")}

# District races filed with a seat count other than 1 whose winner flag is
# still right; collected per run and printed, never corrected.
MISFILED_COUNT_ONLY = []

NUMBER_WORDS = {"1st": "1", "2nd": "2", "3rd": "3", "4th": "4", "5th": "5",
                "6th": "6", "7th": "7"}


def fail(msg):
    raise SystemExit("build-in-county-officials: FATAL: %s" % msg)


def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def county_geoids():
    """county name -> 5-digit GEOID, from the shipped county layer, so the
    roster can never name a county the map does not draw."""
    with open(COUNTIES_FILE, encoding="utf-8") as f:
        feats = json.load(f)["features"]
    out = {}
    for feat in feats:
        p = {k.lower(): v for k, v in feat["properties"].items()}
        name = re.sub(r"\s+County$", "", str(p.get("name") or p.get("basename")))
        out[name] = str(p["geoid"])
    if len(out) != 92:
        fail("the shipped county layer draws %d counties, expected 92" % len(out))
    return out


def results_county(name, geoids):
    """The results spell DeKalb "Dekalb" and LaGrange/LaPorte the same way the
    map does not; match without case or spaces."""
    key = re.sub(r"[^a-z]", "", name.lower())
    for ours in geoids:
        if re.sub(r"[^a-z]", "", ours.lower()) == key:
            return ours
    fail("the results name a county %r the map does not draw" % name)


def seat_label(year, county, title, body):
    """(label, kind, why) for one race. kind is "district", "at-large" or
    "unstated"."""
    if (year, county, title) in AT_LARGE_TITLES:
        return "At large", "at-large", None
    why = UNSTATED_TITLES.get((year, county, title))
    if why:
        return "Seat titled “%s”" % title, "unstated", why
    t = re.sub(r"\s+", " ", title).strip()
    t = re.sub(r",?\s*%s County$" % re.escape(county), "", t, flags=re.I)
    if re.search(r"at[- ]large", t, re.I):
        return "At large", "at-large", None
    m = (re.search(r"(?:District|Dist\.?)\s*#?\s*(\d+|[A-I])\b", t)
         or re.search(r"\b(\d+)\s*(?:st|nd|rd|th)?\s+District\b", t)
         or re.search(r"\bDist\.?\s*(\d+)\s+(?:County\s+)?(?:Council|Commissioner)", t))
    if not m:
        m2 = re.search(r"Of\s+(\d+(?:st|nd|rd|th))\s+District", t, re.I)
        if m2:
            return "District %s" % NUMBER_WORDS[m2.group(1).lower()], "district", None
        m3 = (re.search(r"District\s+([A-Z][a-z]+)$", t)
              or re.search(r"\b([A-Z][a-z]+)\s+(?:District|Dist)$", t))
        if m3:
            return "%s District" % m3.group(1), "district", None
        fail("%d %s: cannot place the %s race titled %r — add it to "
             "UNSTATED_TITLES with the reason, or teach seat_label the form"
             % (year, county, body, title))
    num = m.group(1)
    if num.isdigit() and int(num) > 9:
        fail("%d %s: %r names district %s — record it in UNSTATED_TITLES"
             % (year, county, title, num))
    return "District %s" % num, "district", None


def fetch_json(session, url):
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    resp = session.get(url, timeout=REQUEST_TIMEOUT)
    time.sleep(PACE_SECONDS)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def counting_years(session, today):
    """The generals this run reads: certified, archived, and whose terms have
    begun. Prints every other year it asked about and why it was left out."""
    years = []
    for year in range(FIRST_YEAR, today.year + 1, 2):
        settings = fetch_json(session, SETTINGS % year)
        if settings is None:
            print("  %d general: no archive yet — skipped" % year)
            continue
        root = settings.get("Root") or {}
        if root.get("Certified") != "T":
            print("  %d general: archived but not certified — skipped" % year)
            continue
        if today < datetime.date(year + 1, 1, 1):
            print("  %d general: certified; its winners take office on "
                  "January 1, %d — held until then" % (year, year + 1))
            continue
        years.append((year, root))
    got = {y for y, _ in years}
    for y in REQUIRED_YEARS:
        if y not in got:
            fail("the %d general is not readable — every seat rests on it" % y)
    return years


def party_names(root):
    return {str(p["POLITICALPARTYID"]): p["PARTY_NAME"]
            for p in as_list((root.get("PolParties") or {}).get("PolParty"))}


def election_date(root):
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", root.get("CurrentElection") or "")
    if not m:
        fail("an archive's settings carry no election date: %r" % root.get("CurrentElection"))
    return "%s-%s-%s" % (m.group(3), m.group(1), m.group(2))


def races(session, year, root, category, body, geoids):
    """Every race in one office category of one general, as dicts."""
    doc = fetch_json(session, OFFICE_FILE % (year, category))
    if doc is None:
        fail("the %d general has no office file for category %s" % (year, category))
    parties = party_names(root)
    when = election_date(root)
    out = []
    regions = as_list(doc["Root"]["OfficeCategory"]["Regions"]["Region"])
    for region in regions:
        county = results_county(region["MAP_JURISDICTION_NAME"], geoids)
        for race in as_list((region.get("Races") or {}).get("Race")):
            title = race["OFFICE_TITLE"]
            cands = as_list((race.get("Candidates") or {}).get("Candidate"))
            flagged = [c for c in cands if c.get("isWinner") == "T"]
            seats = int(race.get("NumofSeats") or 0)
            label, kind, why = seat_label(year, county, title, body)
            key = (year, county, title)
            if key in MISFILED_SEAT_COUNTS:
                pub_seats, pub_winners, elected = MISFILED_SEAT_COUNTS[key]
                got = [re.sub(r"\s+", " ", c["NAME_ON_BALLOT"]).strip() for c in flagged]
                top = max(cands, key=lambda c: int(c.get("TOTAL_VOTES") or 0))
                if (str(seats) != pub_seats or sorted(got) != sorted(pub_winners)
                        or re.sub(r"\s+", " ", top["NAME_ON_BALLOT"]).strip() != elected):
                    fail("MISFILED_SEAT_COUNTS %r no longer matches the results: "
                         "%d seats, flagged %r" % (key, seats, got))
                flagged, seats = [top], 1
            elif kind == "district" and len(flagged) > 1:
                fail("%d %s: %r is one district seat and flags %d winners — "
                     "record it in MISFILED_SEAT_COUNTS after reading the votes"
                     % (year, county, title, len(flagged)))
            if kind != "at-large" and seats != 1:
                # a district race elects one member whatever count it is filed
                # under; the misfiled count is counted and printed
                MISFILED_COUNT_ONLY.append((year, county, title, seats))
                seats = 1
            if len(flagged) != seats:
                fail("%d %s: %r elects %d and flags %d winners"
                     % (year, county, title, seats, len(flagged)))
            people = []
            for c in sorted(flagged, key=lambda c: -int(c.get("TOTAL_VOTES") or 0)):
                person = {"name": re.sub(r"\s+", " ", c["NAME_ON_BALLOT"]).strip()}
                party = parties.get(str(c.get("POLITICALPARTYID")))
                if party:
                    person["party"] = party
                people.append(person)
            out.append({"year": year, "election": when, "county": county,
                        "title": title, "label": label, "kind": kind,
                        "why": why, "people": people,
                        "sourceUrl": PAGE % year})
    return out


def assemble(all_races, geoids, expect_seats):
    """county -> seats, the newest race for each seat winning."""
    by_county = {}
    for race in sorted(all_races, key=lambda r: r["year"]):
        seats = by_county.setdefault(race["county"], {})
        if race["kind"] == "unstated":
            # never matched across elections: keyed on the race itself
            seats[("unstated", race["year"], race["title"], len(seats))] = race
        else:
            seats[(race["kind"], race["label"])] = race
    out = {}
    for county, seats in sorted(by_county.items()):
        rows = []
        for race in seats.values():
            for person in race["people"]:
                row = {"seat": race["label"], "election": race["election"],
                       "office": race["title"], "sourceUrl": race["sourceUrl"]}
                row.update(person)
                if race["why"]:
                    row["seatNotStated"] = race["why"]
                rows.append(row)
        rows.sort(key=lambda r: (r["seat"] == "At large",
                                 r["seat"].startswith("Seat titled"), r["seat"]))
        out[geoids[county]] = {"county": county, "seats": rows}
    return out


def check(roster, geoids, body, expect, by_county=None):
    problems = []
    by_county = by_county or {}
    want = {g for c, g in geoids.items() if c not in NOT_IN_RESULTS}
    if set(roster) != want:
        problems.append("%s: %d counties, expected %d (missing %s, extra %s)"
                        % (body, len(roster), len(want),
                           sorted(want - set(roster)), sorted(set(roster) - want)))
    for geoid, rec in sorted(roster.items()):
        n = by_county.get(rec.get("county"), expect)
        seats = rec.get("seats") or []
        if len(seats) != n:
            problems.append("%s: %s County names %d seats, expected %d"
                            % (body, rec.get("county"), len(seats), n))
        for s in seats:
            if not (s.get("name") or "").strip():
                problems.append("%s: %s County seat %r names nobody"
                                % (body, rec.get("county"), s.get("seat")))
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", s.get("election") or ""):
                problems.append("%s: %s County seat %r carries no election date"
                                % (body, rec.get("county"), s.get("seat")))
            if not (s.get("sourceUrl") or "").startswith(HOST + "/archive/"):
                problems.append("%s: %s County seat %r carries no source"
                                % (body, rec.get("county"), s.get("seat")))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped files to the shipped county layer")
    args = ap.parse_args()
    geoids = county_geoids()
    if args.check:
        problems = []
        for path, body, expect, by_county in (
                (COMMISSIONERS_OUT, "commissioners", COMMISSIONER_SEATS, None),
                (COUNCILS_OUT, "council", COUNCIL_SEATS, COUNCIL_SEATS_BY_COUNTY)):
            with open(path, encoding="utf-8") as f:
                problems += check(json.load(f), geoids, body, expect, by_county)
        if problems:
            for p in problems:
                print("build-in-county-officials: FAIL: " + p)
            raise SystemExit(1)
        print("build-in-county-officials --check: OK — commissioners and council "
              "named for %d of 92 counties, every seat dated to its election "
              "(Marion recorded as not in these results)" % (92 - len(NOT_IN_RESULTS)))
        return
    import requests  # noqa: PLC0415
    session = requests.Session()
    session.headers.update(UA_HEADERS_ROSTER_BOT)
    today = datetime.date.today()
    years = counting_years(session, today)
    print("generals read: %s" % ", ".join(str(y) for y, _ in years))
    comm, coun = [], []
    for year, root in years:
        comm += races(session, year, root, COMMISSIONER_CATEGORY, "commissioner", geoids)
        coun += races(session, year, root, COUNCIL_CATEGORY, "council", geoids)
    for key in list(MISFILED_SEAT_COUNTS) + list(UNSTATED_TITLES) + list(AT_LARGE_TITLES):
        seen = any((r["year"], r["county"], r["title"]) == key for r in comm + coun)
        if not seen:
            fail("a table entry %r matches no race the results publish — drop it" % (key,))
    if MISFILED_COUNT_ONLY:
        print("  %d district races are filed under a seat count other than 1 "
              "and flag one winner, which is read as published: %s"
              % (len(MISFILED_COUNT_ONLY), "; ".join(
                  "%d %s %r (%d)" % r for r in MISFILED_COUNT_ONLY)))
    commissioners = assemble(comm, geoids, COMMISSIONER_SEATS)
    councils = assemble(coun, geoids, COUNCIL_SEATS)
    problems = (check(commissioners, geoids, "commissioners", COMMISSIONER_SEATS)
                + check(councils, geoids, "council", COUNCIL_SEATS, COUNCIL_SEATS_BY_COUNTY))
    if problems:
        for p in problems:
            print("build-in-county-officials: FAIL: " + p)
        raise SystemExit(1)
    for path, data in ((COMMISSIONERS_OUT, commissioners), (COUNCILS_OUT, councils)):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, ensure_ascii=False, sort_keys=True)
            f.write("\n")
        print("wrote %s: %d counties, %d seats"
              % (os.path.relpath(path, os.path.dirname(INSTANCE)), len(data),
                 sum(len(r["seats"]) for r in data.values())))


if __name__ == "__main__":
    main()
