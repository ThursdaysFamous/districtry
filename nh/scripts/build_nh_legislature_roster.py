#!/usr/bin/env python3
"""
Build the New Hampshire Senate and House rosters as same-origin app-data
files, so the nh-senate and nh-house cards join a small roster instead of
reaching a third-party host at click time.

TWO ROUTES, THE LEGISLATURE'S OWN FIRST (Adam's choice of 2026-11-10 for every
state in the state-level launch: "start with the legislatures own sites with
Open states as a fall back").

  1. The General Court's own member file, https://gc.nh.gov/downloads/members.txt,
     a tab-separated list of every senator and representative with each one's
     chamber, county, district, party and legislative e-mail address. Its
     column names are the ones Open States' own New Hampshire scraper reads
     (openstates-scrapers, scrapers_next/nh/people.py, read 2026-11-11). The
     file also prints each representative's home address and telephone. THE
     ADDRESS IS NEVER READ, and nothing in this file prints, logs or carries
     it. The telephone is not read in this pass (nh/WATCH.md).
  2. Open States' bulk export of current legislators,
     https://data.openstates.org/people/current/nh.csv, compiled from the
     General Court's own pages (each row lists the page it was read from):
     name, party, district, e-mail and the member's own page on gc.nh.gov.
     ONLY AN ADDRESS AT THE LEGISLATURE'S OWN DOMAIN IS CARRIED FROM THIS
     ROUTE. Many representatives give the General Court a personal address
     (gmail.com, comcast.net, a campaign domain), and this project publishes an
     official's own address only where a government source prints it beside
     them. Open States is not a government, and with gc.nh.gov unreadable
     here nothing confirmed what the General Court prints, so those addresses
     are left off rather than taken on Open States' word; route 1, which is
     the General Court's own file, carries whatever it prints.

Route 1 is tried first on every run. robots.txt is read through
scraper_common.require_robots_once before anything is fetched from the host,
and an unreadable robots.txt disallows (RFC 9309 2.3.1.4). Route 1 is used
only when BOTH chambers it yields pass every check below; otherwise the run
says why and builds from route 2. MEASURED 2026-11-11 FROM THE BUILD SANDBOX,
gc.nh.gov answered every request, robots.txt included, with an empty reply,
so the first shipped roster came from route 2; whether a GitHub runner reaches
the General Court is the first weekly run's question.

THE HOUSE IS 400 SEATS IN 203 NAMED DISTRICTS, NOT NUMBERED ONES. A district
is a county and a number ("Hillsborough 41"), and it elects between one and
ten representatives. 164 of them are BASE districts that tile the state, and
39 are FLOTERIAL districts, each the whole of two or more base districts,
electing more representatives from all of them together. So the House roster
is keyed by district name, every record is {seats, members[, asOf]} whatever
the seat count, and HOUSE_DISTRICT_SEATS below is the plan's seat table:
copied from Open States' metadata for New Hampshire
(openstates/metadata, openstates_metadata/data/nh.py, read 2026-11-10), it
sums to 400 seats in 203 districts, and its 203 names are exactly the 164
base and 39 floterial districts nh/scripts/build_legislative_boundaries.py
measures from the state's own district files. The builder refuses a district
it does not know, and a district listed with more members than it elects.

Honesty: names are never guessed. A district listed with fewer members than
it elects says how many it lists and on what day (asOf), and that date is kept
from the previous build while the record stays short, so an unchanged roster
produces an unchanged file and no weekly PR. A Senate district nobody is
listed for is a dated empty record. Neither ever says "vacant": a source
naming nobody is a fact about the source, not a statement by the chamber.

Usage:
    python3 build_nh_legislature_roster.py [--openstates-csv nh.csv] [output_dir]
    python3 build_nh_legislature_roster.py --selftest

--openstates-csv builds from a local copy of the Open States export and skips
route 1, which is how this file was first built offline.
"""

import csv
import datetime
import io
import json
import os
import re
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import (  # noqa: E402  (FLEET_SHARED)
    require_robots_once, UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, UA_STDLIB_DEFAULT)


LEGISLATURE_URL = "https://gc.nh.gov/downloads/members.txt"
OPENSTATES_URL = "https://data.openstates.org/people/current/nh.csv"
HOUSE_DIRECTORY = "https://gc.nh.gov/house/members/"
SENATE_PAGE = "https://gc.nh.gov/senate/members/webpages/district%02d.aspx"

COUNTIES = ("Belknap", "Carroll", "Cheshire", "Coos", "Grafton", "Hillsborough",
            "Merrimack", "Rockingham", "Strafford", "Sullivan")
PARTIES = {"d": "Democratic", "r": "Republican", "i": "Independent",
           "democratic": "Democratic", "republican": "Republican",
           "independent": "Independent", "libertarian": "Libertarian"}
NAME_OK = re.compile(r"^[^\W\d_][^\W\d_ .'\-]*(?:[ .'\-]+[^\W\d_]+)*\.?$")

HOUSE_DISTRICT_SEATS = {
    # Belknap: 8 districts, 18 seats
    'Belknap 1': 1, 'Belknap 2': 2, 'Belknap 3': 1, 'Belknap 4': 1,
    'Belknap 5': 4, 'Belknap 6': 4, 'Belknap 7': 3, 'Belknap 8': 2,
    # Carroll: 8 districts, 15 seats
    'Carroll 1': 3, 'Carroll 2': 2, 'Carroll 3': 2, 'Carroll 4': 2,
    'Carroll 5': 1, 'Carroll 6': 2, 'Carroll 7': 1, 'Carroll 8': 2,
    # Cheshire: 18 districts, 22 seats
    'Cheshire 1': 1, 'Cheshire 2': 1, 'Cheshire 3': 1, 'Cheshire 4': 1,
    'Cheshire 5': 1, 'Cheshire 6': 2, 'Cheshire 7': 1, 'Cheshire 8': 1,
    'Cheshire 9': 1, 'Cheshire 10': 2, 'Cheshire 11': 1, 'Cheshire 12': 1,
    'Cheshire 13': 1, 'Cheshire 14': 1, 'Cheshire 15': 2, 'Cheshire 16': 1,
    'Cheshire 17': 1, 'Cheshire 18': 2,
    # Coos: 7 districts, 9 seats
    'Coos 1': 2, 'Coos 2': 1, 'Coos 3': 1, 'Coos 4': 1, 'Coos 5': 2,
    'Coos 6': 1, 'Coos 7': 1,
    # Grafton: 18 districts, 26 seats
    'Grafton 1': 3, 'Grafton 2': 1, 'Grafton 3': 1, 'Grafton 4': 1,
    'Grafton 5': 2, 'Grafton 6': 1, 'Grafton 7': 1, 'Grafton 8': 3,
    'Grafton 9': 1, 'Grafton 10': 1, 'Grafton 11': 1, 'Grafton 12': 4,
    'Grafton 13': 1, 'Grafton 14': 1, 'Grafton 15': 1, 'Grafton 16': 1,
    'Grafton 17': 1, 'Grafton 18': 1,
    # Hillsborough: 45 districts, 123 seats
    'Hillsborough 1': 4, 'Hillsborough 2': 7, 'Hillsborough 3': 3,
    'Hillsborough 4': 3, 'Hillsborough 5': 3, 'Hillsborough 6': 3,
    'Hillsborough 7': 3, 'Hillsborough 8': 3, 'Hillsborough 9': 3,
    'Hillsborough 10': 3, 'Hillsborough 11': 3, 'Hillsborough 12': 8,
    'Hillsborough 13': 6, 'Hillsborough 14': 2, 'Hillsborough 15': 2,
    'Hillsborough 16': 2, 'Hillsborough 17': 2, 'Hillsborough 18': 2,
    'Hillsborough 19': 2, 'Hillsborough 20': 2, 'Hillsborough 21': 2,
    'Hillsborough 22': 2, 'Hillsborough 23': 2, 'Hillsborough 24': 2,
    'Hillsborough 25': 2, 'Hillsborough 26': 2, 'Hillsborough 27': 1,
    'Hillsborough 28': 2, 'Hillsborough 29': 4, 'Hillsborough 30': 3,
    'Hillsborough 31': 1, 'Hillsborough 32': 3, 'Hillsborough 33': 2,
    'Hillsborough 34': 3, 'Hillsborough 35': 2, 'Hillsborough 36': 2,
    'Hillsborough 37': 1, 'Hillsborough 38': 2, 'Hillsborough 39': 2,
    'Hillsborough 40': 4, 'Hillsborough 41': 3, 'Hillsborough 42': 3,
    'Hillsborough 43': 4, 'Hillsborough 44': 2, 'Hillsborough 45': 1,
    # Merrimack: 30 districts, 45 seats
    'Merrimack 1': 1, 'Merrimack 2': 1, 'Merrimack 3': 2, 'Merrimack 4': 2,
    'Merrimack 5': 2, 'Merrimack 6': 1, 'Merrimack 7': 2, 'Merrimack 8': 3,
    'Merrimack 9': 4, 'Merrimack 10': 4, 'Merrimack 11': 1, 'Merrimack 12': 2,
    'Merrimack 13': 2, 'Merrimack 14': 1, 'Merrimack 15': 1, 'Merrimack 16': 1,
    'Merrimack 17': 1, 'Merrimack 18': 1, 'Merrimack 19': 1, 'Merrimack 20': 1,
    'Merrimack 21': 1, 'Merrimack 22': 1, 'Merrimack 23': 1, 'Merrimack 24': 1,
    'Merrimack 25': 1, 'Merrimack 26': 1, 'Merrimack 27': 2, 'Merrimack 28': 1,
    'Merrimack 29': 1, 'Merrimack 30': 1,
    # Rockingham: 40 districts, 91 seats
    'Rockingham 1': 3, 'Rockingham 2': 3, 'Rockingham 3': 1, 'Rockingham 4': 3,
    'Rockingham 5': 2, 'Rockingham 6': 1, 'Rockingham 7': 1, 'Rockingham 8': 1,
    'Rockingham 9': 2, 'Rockingham 10': 3, 'Rockingham 11': 4,
    'Rockingham 12': 2, 'Rockingham 13': 10, 'Rockingham 14': 2,
    'Rockingham 15': 2, 'Rockingham 16': 7, 'Rockingham 17': 4,
    'Rockingham 18': 2, 'Rockingham 19': 1, 'Rockingham 20': 3,
    'Rockingham 21': 1, 'Rockingham 22': 1, 'Rockingham 23': 1,
    'Rockingham 24': 2, 'Rockingham 25': 9, 'Rockingham 26': 1,
    'Rockingham 27': 1, 'Rockingham 28': 1, 'Rockingham 29': 4,
    'Rockingham 30': 2, 'Rockingham 31': 2, 'Rockingham 32': 1,
    'Rockingham 33': 1, 'Rockingham 34': 1, 'Rockingham 35': 1,
    'Rockingham 36': 1, 'Rockingham 37': 1, 'Rockingham 38': 1,
    'Rockingham 39': 1, 'Rockingham 40': 1,
    # Strafford: 21 districts, 38 seats
    'Strafford 1': 2, 'Strafford 2': 3, 'Strafford 3': 1, 'Strafford 4': 3,
    'Strafford 5': 1, 'Strafford 6': 1, 'Strafford 7': 1, 'Strafford 8': 1,
    'Strafford 9': 1, 'Strafford 10': 4, 'Strafford 11': 3, 'Strafford 12': 4,
    'Strafford 13': 1, 'Strafford 14': 1, 'Strafford 15': 1, 'Strafford 16': 1,
    'Strafford 17': 1, 'Strafford 18': 1, 'Strafford 19': 3, 'Strafford 20': 1,
    'Strafford 21': 3,
    # Sullivan: 8 districts, 13 seats
    'Sullivan 1': 1, 'Sullivan 2': 1, 'Sullivan 3': 3, 'Sullivan 4': 1,
    'Sullivan 5': 1, 'Sullivan 6': 3, 'Sullivan 7': 1, 'Sullivan 8': 2,
}

SENATE_SEATS = 24
assert len(HOUSE_DISTRICT_SEATS) == 203 and sum(HOUSE_DISTRICT_SEATS.values()) == 400

# What scripts/validate_chamber_rosters.py reads: the Senate is numbered 1-24,
# and the House states its named districts and their seats instead of a count.
# Floors catch a truncated download or a changed schema while tolerating the
# vacancies a 400-member House always carries: measured 2026-11-10, the Open
# States export named 382 representatives and all 24 senators.
CHAMBERS = {
    "upper": {"out": "nh-senate-members.json", "label": "Senate",
              "seats": SENATE_SEATS, "expected": 22},
    "lower": {"out": "nh-house-members.json", "label": "House",
              "districts": HOUSE_DISTRICT_SEATS, "expected": 360},
}
# Measured 2026-11-11 on the Open States route: 353 of the 406 members named
# carry an address at the Legislature's own domain (the other 53 gave the
# General Court a personal one, which this route does not carry, and two
# carry none). A field nearly every row carries going missing is the Brown
# County shape: the row count holds and the contact detail silently goes.
MIN_EMAIL_SHARE = 0.8
# The Legislature's own mail domains: the only addresses route 2 carries.
LEGISLATURE_EMAIL_DOMAINS = ("gc.nh.gov", "leg.state.nh.us")

INSTANCE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")


class SourceRefused(Exception):
    """A route whose answer did not pass a check; the run falls back."""


def county_name(raw):
    """A county as the plan spells it, from the spellings sources use."""
    text = (raw or "").strip().replace("ö", "o").replace("Ö", "O")
    for county in COUNTIES:
        if text.lower() == county.lower():
            return county
    return None


def clean_name(raw):
    name = re.sub(r"\s+", " ", raw or "").strip()
    if not name or not NAME_OK.match(name) or len(name) > 60:
        raise SourceRefused("a name that is not a name: %r" % name[:60])
    return name


def member_record(name, party, email, url):
    member = {"name": clean_name(name)}
    if party:
        key = party.strip().lower()
        if key not in PARTIES:
            raise SourceRefused("a party the builder has no word for: %r" % party)
        member["party"] = PARTIES[key]
    if email:
        email = email.strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", email, re.I):
            raise SourceRefused("an e-mail address that is not one: %r" % email)
        member["email"] = email
    if url:
        member["url"] = url
    return member


def senate_page(number):
    return SENATE_PAGE % int(number)


# ---- route 1: the General Court's own member file --------------------------
LEGISLATURE_COLUMNS = ("LastName", "FirstName", "MiddleName", "LegislativeBody",
                       "County", "District", "party", "WorkEmail")


def decode_members_txt(raw):
    """The file is not UTF-8 throughout: Open States' scraper repairs two names
    whose accented letters arrive as bytes 0x82 and 0x89, which are e-acute and
    e-diaeresis in the DOS code page 850. So UTF-8 is tried and code page 850
    is the fallback, which reads plain ASCII identically."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp850")


def parse_members_txt(text):
    """(senate, house) as {district: [member, ...]} from the General Court's
    file. Reads only the columns named above; the address columns are never
    touched."""
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    header = [h.strip() for h in (reader.fieldnames or [])]
    missing = [c for c in LEGISLATURE_COLUMNS if c not in header]
    if missing:
        raise SourceRefused("the member file has no %s column" % ", ".join(missing))
    senate, house = {}, {}
    for row in reader:
        row = {(k or "").strip(): (v or "") for k, v in row.items()}
        body = row["LegislativeBody"].strip().upper()
        name = " ".join(p for p in (row["FirstName"].strip(), row["MiddleName"].strip(),
                                    row["LastName"].strip()) if p)
        number = row["District"].strip().lstrip("0")
        if not number.isdigit():
            raise SourceRefused("a district number that is not one: %r" % row["District"])
        if body == "S":
            if not 1 <= int(number) <= SENATE_SEATS:
                raise SourceRefused("Senate district %s is not one of 1-24" % number)
            senate.setdefault(number, []).append(
                member_record(name, row["party"], row["WorkEmail"], senate_page(number)))
        elif body == "H":
            county = county_name(row["County"])
            if not county:
                raise SourceRefused("a county the plan does not have: %r" % row["County"])
            house.setdefault("%s %s" % (county, number), []).append(
                member_record(name, row["party"], row["WorkEmail"], None))
        else:
            raise SourceRefused("a chamber code the builder has no word for: %r" % body)
    return senate, house


def fetch_legislature():
    require_robots_once(LEGISLATURE_URL, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT,
                        label="nh-build-nh-legislature-roster")
    req = urllib.request.Request(LEGISLATURE_URL, headers=UA_HEADERS_ROSTER_BOT)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return decode_members_txt(resp.read())


# ---- route 2: Open States' export -------------------------------------------
def first_gc_link(links):
    """The member's own page on the General Court's site, from Open States'
    semicolon-joined links cell; nothing else in that cell is carried."""
    for candidate in (links or "").split(";"):
        candidate = candidate.strip()
        if re.match(r"^https://gc\.nh\.gov/(house|senate)/members/", candidate, re.I):
            return candidate
    return None


def legislature_email(raw):
    """An address at the Legislature's own domain, or None (see route 2 in
    the module docstring for why nothing else is carried from Open States)."""
    email = (raw or "").strip()
    domain = email.rpartition("@")[2].lower()
    return email if domain in LEGISLATURE_EMAIL_DOMAINS else None


def parse_openstates(rows):
    senate, house = {}, {}
    for row in rows:
        chamber = (row.get("current_chamber") or "").strip()
        district = (row.get("current_district") or "").strip()
        name = row.get("name") or ""
        if not district or not name.strip():
            continue
        member = member_record(name, row.get("current_party"),
                               legislature_email(row.get("email")),
                               first_gc_link(row.get("links")))
        if chamber == "upper":
            number = district.lstrip("0")
            if not number.isdigit() or not 1 <= int(number) <= SENATE_SEATS:
                raise SourceRefused("Senate district %r is not one of 1-24" % district)
            senate.setdefault(number, []).append(member)
        elif chamber == "lower":
            county, _, number = district.rpartition(" ")
            county = county_name(county)
            if not county or not number.isdigit():
                raise SourceRefused("a House district the plan does not have: %r" % district)
            house.setdefault("%s %s" % (county, number.lstrip("0")), []).append(member)
    return senate, house


def fetch_openstates():
    require_robots_once(OPENSTATES_URL, UA_STDLIB_DEFAULT,
                        label="nh-build-nh-legislature-roster")
    req = urllib.request.Request(OPENSTATES_URL, headers={"User-Agent": UA_STDLIB_DEFAULT})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return list(csv.DictReader(io.StringIO(resp.read().decode("utf-8"))))


# ---- the checks every route passes, and the records -------------------------
def check_chambers(senate, house):
    for number, members in senate.items():
        if len(members) > 1:
            raise SourceRefused("Senate district %s lists %d members" % (number, len(members)))
    unknown = sorted(d for d in house if d not in HOUSE_DISTRICT_SEATS)
    if unknown:
        raise SourceRefused("House district(s) the plan does not have: %s" % ", ".join(unknown))
    for district, members in house.items():
        if len(members) > HOUSE_DISTRICT_SEATS[district]:
            raise SourceRefused("%s lists %d members for %d seats"
                                % (district, len(members), HOUSE_DISTRICT_SEATS[district]))
    named_senate = len(senate)
    named_house = sum(len(m) for m in house.values())
    if named_senate < CHAMBERS["upper"]["expected"]:
        raise SourceRefused("%d senators named (expected at least %d)"
                            % (named_senate, CHAMBERS["upper"]["expected"]))
    if named_house < CHAMBERS["lower"]["expected"]:
        raise SourceRefused("%d representatives named (expected at least %d)"
                            % (named_house, CHAMBERS["lower"]["expected"]))
    everyone = [m for ms in senate.values() for m in ms] + [m for ms in house.values() for m in ms]
    emails = sum(1 for m in everyone if m.get("email"))
    if emails < MIN_EMAIL_SHARE * len(everyone):
        raise SourceRefused("only %d of %d members carry an e-mail address"
                            % (emails, len(everyone)))


def load_previous(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def senate_records(senate, prev, today):
    out = {}
    for n in range(1, SENATE_SEATS + 1):
        key = str(n)
        if key in senate:
            out[key] = senate[key][0]
        else:
            before = prev.get(key) or {}
            out[key] = {"asOf": before.get("asOf") if not before.get("name") and before.get("asOf") else today}
    return out


def house_records(house, prev, today):
    out = {}
    for district, seats in HOUSE_DISTRICT_SEATS.items():
        members = sorted(house.get(district, []), key=lambda m: m["name"].split(" ")[-1] + " " + m["name"])
        record = {"seats": seats, "members": members}
        if len(members) < seats:
            before = prev.get(district) or {}
            was_short = len(before.get("members") or []) < seats and before.get("asOf")
            record["asOf"] = before["asOf"] if was_short else today
        out[district] = record
    return out


def write(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def build(out_dir, openstates_csv=None):
    route = None
    senate = house = None
    if openstates_csv is None:
        try:
            senate, house = parse_members_txt(fetch_legislature())
            check_chambers(senate, house)
            route = "the General Court's own member file (%s)" % LEGISLATURE_URL
        except SystemExit as exc:  # a robots refusal or an unreadable robots.txt
            print("nh-legislature-roster: route 1 not read (robots.txt: exit %s); "
                  "building from Open States" % exc.code, file=sys.stderr)
        except SourceRefused as exc:
            print("nh-legislature-roster: route 1 refused (%s); building from "
                  "Open States" % exc, file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 - any fetch failure falls back
            print("nh-legislature-roster: route 1 failed (%s: %s); building from "
                  "Open States" % (exc.__class__.__name__, exc), file=sys.stderr)
    if route is None:
        if openstates_csv:
            with open(openstates_csv, encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
        else:
            rows = fetch_openstates()
        try:
            senate, house = parse_openstates(rows)
            check_chambers(senate, house)
        except SourceRefused as exc:
            print("nh-legislature-roster: FAIL — Open States export refused (%s); "
                  "refusing to overwrite the rosters" % exc, file=sys.stderr)
            sys.exit(1)
        route = "Open States' export (%s)" % OPENSTATES_URL
    today = datetime.date.today().isoformat()
    os.makedirs(out_dir, exist_ok=True)
    senate_path = os.path.join(out_dir, CHAMBERS["upper"]["out"])
    house_path = os.path.join(out_dir, CHAMBERS["lower"]["out"])
    write(senate_path, senate_records(senate, load_previous(senate_path), today))
    write(house_path, house_records(house, load_previous(house_path), today))
    short = sorted((d for d in HOUSE_DISTRICT_SEATS
                    if len(house.get(d, [])) < HOUSE_DISTRICT_SEATS[d]),
                   key=list(HOUSE_DISTRICT_SEATS).index)
    print("nh-legislature-roster: built from %s — %d of 24 senators, %d of 400 "
          "representatives; districts listing fewer members than they elect: %s"
          % (route, len(senate), sum(len(m) for m in house.values()),
             ", ".join(short) or "none"), file=sys.stderr)


# ---- self-test: route 1's parser on a file shaped like the General Court's ---
SELFTEST_FILE = (  # bytes, as the server sends them: 0x82 and 0x94 are code page 850
    b"LastName\tFirstName\tMiddleName\tLegislativeBody\tCounty\tDistrict\tparty\t"
    b"electedStatus\tAddress\taddress2\tcity\tZipcode\tPhone\tWorkEmail\tGenderCode\n"
    b"Doe\tJane\tQ.\tS\t\t07\tR\t\t107 North Main Street\t\tConcord\t03301\t"
    b"(603) 555-0100\tjane.doe@leg.state.nh.us\tF\n"
    b"Roe\tRich\x82\t\tH\tCo\x94s\t006\tD\t\t1 Example Road\t\tBerlin\t03570\t"
    b"(603) 555-0101\trich.roe@gc.nh.gov\tM\n"
)


def selftest():
    bad = []
    senate, house = parse_members_txt(decode_members_txt(SELFTEST_FILE))
    jane = senate.get("7", [{}])[0]
    if jane.get("name") != "Jane Q. Doe" or jane.get("party") != "Republican":
        bad.append("senator parsed as %r" % jane)
    if jane.get("url") != SENATE_PAGE % 7:
        bad.append("senator page %r" % jane.get("url"))
    rich = house.get("Coos 6", [{}])[0]
    if rich.get("name") != "Riché Roe" or rich.get("party") != "Democratic":
        bad.append("representative parsed as %r (county keys %r)" % (rich, list(house)))
    blob = json.dumps([senate, house])
    if "Example Road" in blob or "Main Street" in blob or "03570" in blob or "555-01" in blob:
        bad.append("an address or telephone reached a record")
    try:
        parse_members_txt("LastName\tFirstName\n")
        bad.append("a file missing the party and district columns was read")
    except SourceRefused:
        pass
    try:
        check_chambers({}, {"Belknap 1": [{"name": "A"}, {"name": "B"}]})
        bad.append("two members for Belknap 1's one seat passed")
    except SourceRefused:
        pass
    try:
        check_chambers({}, {"Belknap 99": [{"name": "A"}]})
        bad.append("a district the plan does not have passed")
    except SourceRefused:
        pass
    for name in ("J.R. Hoell", "Mary Jane O'Brien-Smith", "Dan McGuire Jr."):
        try:
            clean_name(name)
        except SourceRefused:
            bad.append("a real name shape refused: %r" % name)
    for name in ("12 Main St", "Doe, Jane"):
        try:
            clean_name(name)
            bad.append("a non-name passed: %r" % name)
        except SourceRefused:
            pass
    os_rows = [{"name": "Pat Poe", "current_chamber": "lower", "current_district": "Coos 6",
                "current_party": "Republican", "email": "pat.poe@example-mail.com",
                "links": "https://gc.nh.gov/house/members/member.aspx?pid=1"},
               {"name": "Lee Loe", "current_chamber": "upper", "current_district": "3",
                "current_party": "Democratic", "email": "Lee.Loe@gc.nh.gov", "links": ""}]
    os_senate, os_house = parse_openstates(os_rows)
    if "email" in os_house.get("Coos 6", [{}])[0]:
        bad.append("route 2 carried an address outside the Legislature's domain")
    if os_senate.get("3", [{}])[0].get("email") != "Lee.Loe@gc.nh.gov":
        bad.append("route 2 dropped a Legislature address: %r" % os_senate.get("3"))
    prev = {"Belknap 2": {"seats": 2, "members": [{"name": "A"}], "asOf": "2026-11-01"}}
    rec = house_records({"Belknap 2": [{"name": "A"}]}, prev, "2026-11-11")["Belknap 2"]
    if rec.get("asOf") != "2026-11-01":
        bad.append("a district still short lost its first date: %r" % rec)
    rec = house_records({"Belknap 2": [{"name": "A"}, {"name": "B"}]}, prev, "2026-11-11")["Belknap 2"]
    if "asOf" in rec:
        bad.append("a district now full kept a date: %r" % rec)
    if bad:
        for b in bad:
            print("nh-legislature-roster selftest: FAIL — %s" % b)
        return 1
    print("nh-legislature-roster: selftest OK — route 1 parses a file shaped like "
          "the General Court's, never carries its address or telephone, carries "
          "only Legislature addresses from Open States, and refuses an over-full or "
          "unknown district")
    return 0


def main():
    args = sys.argv[1:]
    if args == ["--selftest"]:
        sys.exit(selftest())
    openstates_csv = None
    if args[:1] == ["--openstates-csv"]:
        if len(args) < 2:
            print(__doc__, file=sys.stderr)
            sys.exit(2)
        openstates_csv = args[1]
        args = args[2:]
    if len(args) > 1:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    build(args[0] if args else DEFAULT_OUT_DIR, openstates_csv)


if __name__ == "__main__":
    main()
