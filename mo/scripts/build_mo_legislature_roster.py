#!/usr/bin/env python3
"""
Build the Missouri Senate and Missouri House rosters (district -> current
officeholder) as same-origin app-data files, from each chamber's OWN
publications, so the mo-senate / mo-house cards join a small roster instead of
reaching a third-party host at click time.

index.html's mo-senate / mo-house layers fetch data/app/mo-senate-members.json
and mo-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
capitolOffice, url?}}, or a vacancy record). A weekly GitHub Action
(.github/workflows/update-mo-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHERE THE SENATORS ARE, MEASURED 2026-10-21. The Senate's directory,
www.senate.mo.gov/Senators/SenatorDirectory/, prints one card per seat: the
senator's name linked to their own page, the district, the party, the Capitol
office's room number and its telephone. That day it held 34 cards, 33 senators
and one card reading "Vacant" for District 10. The vacant card still prints a
room and a telephone, which belong to the office and not to any senator, and
neither ships. Above the cards the page prints the address every room number
belongs to ("201 W Capitol Ave., Rm. room number, Jefferson City, MO 65101");
the script reads that sentence off the page and stops if it changes, rather
than writing an address the page no longer gives.

THE SENATORS' E-MAIL ADDRESSES ARE NOT ON ANY SENATE PAGE, so they come from
the Secretary of State's General Assembly Roster, a PDF the office publishes
each year and links from www.sos.mo.gov/pubs ("2026 General Assembly Roster"
that day). Its page "State Senators by District" prints each senator's name,
district, room and e-mail address on one line. An address ships only when the
roster's line for that district names the surname the Senate's directory names
and the address's own name contains it, because the roster is printed once a
year and a seat can change hands after it: on 2026-10-21 it still printed
Travis Fitzwater for District 10, which the Senate shows as vacant. The PDF is
read with pdftotext (poppler-utils) in layout mode, which keeps each printed
line whole; pypdf's layout mode, tried first, broke most lines of this page
apart.

WHERE THE REPRESENTATIVES ARE. house.mo.gov states "Crawl-delay: 120" and
disallows every address carrying a query string, which is how its member pages
are addressed, so its pages are not read. The House publishes the same records
for exactly this use at documents.house.mo.gov: a list file naming one XML file
per district, rebuilt hourly, "to reduce load from scraping technology". That
host's robots.txt asks for 20 seconds between requests, so a run takes about 55
minutes for 163 districts plus the list. The session's file prefix is read from
the House's own SessionSet.js, so a new session is followed without an edit.
On 2026-10-21 the House's own member page counted 163 seats, 155 members and 8
vacancies.

WHAT IS READ, AND WHAT IS NEVER READ. From each representative's file: the
first and last name, the district, the party, the Capitol address, its
telephone and the member's e-mail address. The same file also gives the
member's home town, a legislative assistant's name, a biography and the
counties the district touches; none of those is read. No home address is
published by either chamber and none ships.

NO MEMBER PAGE IS LINKED FOR A REPRESENTATIVE, because house.mo.gov addresses
each member's page with a query string its robots.txt disallows, and the
monthly link check (scripts/validate_card_links.py) would have to fetch every
one. Its path-prefix exceptions cannot express a rule about query strings, so
the card links the House's member roster page instead, which is permitted. A
senator's own page is linked: the Senate's robots.txt disallows nothing.

THE E-MAIL ADDRESS ships as printed, because the fleet's rule since 2026-10-17
(Adam: "E-mails too") is that an address a government source prints in one
official's own entry is that official's. An address printed for two or more
members is an office's and ships on no member's row.

ROBOTS. Each host's robots.txt is read through scripts/robots_policy.py with
the User-Agent the fetches send, before its first fetch, and a stated
Crawl-delay is honoured by its HostPacer. Read 2026-10-21: www.senate.mo.gov
(61 bytes) and www.sos.mo.gov (199 bytes) disallow nothing this script reads
and state no delay; documents.house.mo.gov (30 bytes) states Crawl-delay 20.

Honesty: names are never guessed. A seat a chamber shows as vacant gets a
vacancy record naming that chamber's own publication; a seat with no record,
or with two, stops the build.

Usage:
    python3 mo/scripts/build_mo_legislature_roster.py [output_dir]
    python3 mo/scripts/build_mo_legislature_roster.py --save DIR [output_dir]
    python3 mo/scripts/build_mo_legislature_roster.py --offline DIR [output_dir]

--save writes every file fetched into DIR (senate-directory.html,
sos-pubs.html, ga-roster.pdf, house-session.js, house-list.xml and
house/<district>.xml), reading back any it already holds; --offline reads them
back instead of fetching, for building and testing without the network.
"""

import datetime
import html as html_module
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from robots_policy import HostPacer, RobotsGate  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/mo/)"
# Every host is paced at one second even where it states no delay.
MIN_PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

SENATE_DIRECTORY = "https://www.senate.mo.gov/Senators/SenatorDirectory/"
SOS_PUBS = "https://www.sos.mo.gov/pubs"
HOUSE_SESSION_JS = "https://documents.house.mo.gov/SessionSet.js"
HOUSE_ROSTER_PAGE = "https://house.mo.gov/MemberRoster.aspx"

# Floors catch a truncated list or a layout change while tolerating real
# vacancies: 33 of 34 senators and 155 of 163 representatives were named on
# 2026-10-21.
CHAMBERS = {
    "S": {"out": "mo-senate-members.json", "label": "Senate", "seats": 34,
          "expected": 30, "body": "The Missouri Senate"},
    "H": {"out": "mo-house-members.json", "label": "House", "seats": 163,
          "expected": 145, "body": "The Missouri House of Representatives"},
}
# A field nearly every named member carried on 2026-10-21. One going missing
# is the Brown County shape: the row count holds and the contact goes.
MIN_FIELD_SHARE = 0.9

PARTY_NAMES = {"Republican": "Republican", "Democrat": "Democratic",
               "Democratic": "Democratic", "Independent": "Independent",
               "Libertarian": "Libertarian"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\(?\d{3}\)?[ -]?\d{3}-\d{4}$")

# One Senate directory card: its header link, then label/value pairs.
CARD_LINK_RE = re.compile(r'<div class="card__header[^"]*">\s*<a href="([^"]*)"[^>]*>(.*?)</a>',
                          re.S)
CARD_FIELD_RE = re.compile(
    r'<span class="detail-grid__label"[^>]*>(.*?)</span>\s*'
    r'<span class="detail-grid__value"[^>]*>(.*?)</span>', re.S)
# The sentence above the cards that says where every room number is.
SENATE_ADDRESS_RE = re.compile(
    r"Senator\s*<i>senator's name</i>\s*<br>\s*(.*?),\s*Rm\.\s*<em>room number</em>\s*<br>"
    r"\s*(.*?)\s*</p>", re.S)

# The General Assembly Roster's link on the Secretary of State's publications
# page, e.g. ".../GARoster/2026GARoster.pdf" ... "2026 General Assembly Roster".
GA_ROSTER_LINK_RE = re.compile(
    r'href="([^"]*GARoster[^"]*\.pdf)"[^>]*>\s*(\d{4}) General Assembly Roster\s*<', re.I)
# A line of the roster's "State Senators by District" page:
# "Bean, Jason S. (R). . . .25 . . . . 321. . . .jason.bean@senate.mo.gov".
GA_LINE_RE = re.compile(
    r"^(?P<last>[^,(]+),\s*(?P<first>[^()]+?)\s*\((?P<party>[A-Z])\)[\s.]*?"
    r"(?P<district>\d{1,2})[\s.]+(?P<room>\d+[A-Z]?)[\s.]+(?P<email>\S+)")

_SESSION = None


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
    return _SESSION


_GATE = None
_PACER = None
_LAST = {}


def gate():
    global _GATE, _PACER
    if _GATE is None:
        _GATE = RobotsGate(session(), USER_AGENT)
        _PACER = HostPacer(_GATE)
    return _GATE


def fetch(url, binary=False):
    import requests

    ok, why = gate().allows(url)
    host = urllib.parse.urlsplit(url).netloc
    if host not in _LAST:
        print("robots.txt %s: %s" % (host, why), file=sys.stderr)
        _LAST[host] = 0.0
    if not ok:
        raise SystemExit("FAIL: robots.txt refuses %s (%s)" % (url, why))
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        wait = MIN_PACE_SECONDS - (time.time() - _LAST[host])
        if wait > 0:
            time.sleep(wait)
        try:
            with _PACER.hold(url):
                resp = session().get(url, timeout=120)
            _LAST[host] = time.time()
            resp.raise_for_status()
            if binary:
                return resp.content
            # Every page and file read here declares or is UTF-8.
            resp.encoding = resp.encoding if resp.encoding and "utf" in resp.encoding.lower() \
                else "utf-8"
            return resp.text
        except requests.RequestException as exc:  # reset, timeout, 5xx
            _LAST[host] = time.time()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


class Pages:
    """Fetch, save or replay the files one run reads."""

    def __init__(self, offline=None, save=None):
        self.offline, self.save = offline, save

    def get(self, name, url, binary=False):
        source = self.offline or (self.save if self.save and
                                  os.path.exists(os.path.join(self.save, name)) else None)
        if source:
            # --offline, or a file an interrupted --save run already wrote.
            with open(os.path.join(source, name), "rb" if binary else "r",
                      **({} if binary else {"encoding": "utf-8"})) as fh:
                return fh.read()
        body = fetch(url, binary)
        if self.save:
            path = os.path.join(self.save, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb" if binary else "w",
                      **({} if binary else {"encoding": "utf-8"})) as fh:
                fh.write(body)
        return body


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


def letters(text):
    """Lower-case letters only, accents dropped: O’Laughlin -> olaughlin."""
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if c.isalpha() and not unicodedata.combining(c)).lower()


def party_word(word, where, notes):
    if not word:
        return None
    if word not in PARTY_NAMES:
        notes.append("%s: party printed as %r ships as printed" % (where, word))
    return PARTY_NAMES.get(word, word)


def plain_email(raw, where, notes):
    if not raw:
        return None
    if EMAIL_RE.match(raw):
        return raw
    notes.append("%s: an e-mail entry that is not one plain address was not carried" % where)
    return None


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def vacancy(cfg, why, source, previous, district, today):
    prev = previous.get(str(district)) or {}
    return {
        "vacant": True,
        "vacantWhy": why,
        "sourceUrl": source,
        # The day the chamber was first read saying so, kept across runs.
        "asOf": (prev.get("asOf") if prev.get("vacant") else None) or today,
    }


# --- Senate -----------------------------------------------------------------

def senate_address(page):
    """(street, city line) from the directory's correspondence sentence."""
    m = SENATE_ADDRESS_RE.search(page)
    if not m:
        raise SystemExit("FAIL: the Senate directory no longer prints the sentence "
                         "giving the address of every room number — the page layout "
                         "changed, so no Capitol address can be written")
    street, city = clean(m.group(1)), clean(m.group(2))
    if not re.search(r"\d", street) or "MO" not in city:
        raise SystemExit("FAIL: the Senate directory's address reads %r / %r" % (street, city))
    return street, city


def parse_senate_directory(page):
    """[card] in page order."""
    grid = page.find('class="senators-grid"')
    if grid < 0:
        raise SystemExit("FAIL: the Senate directory carries no card grid — the page "
                         "layout changed")
    cards = []
    for block in page[grid:].split('<div class="card">')[1:]:
        link = CARD_LINK_RE.search(block)
        fields = {}
        for label, value in CARD_FIELD_RE.findall(block):
            key = clean(label)
            if key in fields:
                raise SystemExit("FAIL: a Senate directory card prints %r twice" % key)
            fields[key] = clean(value)
        if not link or "District" not in fields:
            raise SystemExit("FAIL: a Senate directory card carries no name or district "
                             "— the page layout changed (%r)" % sorted(fields))
        district = re.fullmatch(r"District (\d+)", fields["District"])
        if not district:
            raise SystemExit("FAIL: a Senate directory card's district reads %r"
                             % fields["District"])
        cards.append({
            "district": int(district.group(1)),
            "name": clean(link.group(2)),
            "url": html_module.unescape(link.group(1)).strip(),
            "party": fields.get("Party", ""),
            "room": fields.get("Capitol Office", ""),
            "phone": fields.get("Capitol Phone", ""),
        })
    return cards


def ga_roster_url(pubs_page):
    """The newest General Assembly Roster PDF the publications page links."""
    found = []
    for href, year in GA_ROSTER_LINK_RE.findall(pubs_page):
        found.append((int(year), urllib.parse.urljoin(SOS_PUBS, html_module.unescape(href))))
    if not found:
        raise SystemExit("FAIL: www.sos.mo.gov/pubs links no General Assembly Roster — "
                         "the page layout changed")
    return max(found)


def pdf_text(pdf_bytes):
    """pdftotext -layout over the whole PDF, one string per page."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "roster.pdf")
        with open(path, "wb") as fh:
            fh.write(pdf_bytes)
        try:
            out = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", path, "-"],
                                 check=True, capture_output=True, timeout=300)
        except FileNotFoundError:
            raise SystemExit("FAIL: pdftotext is not installed (apt-get install "
                             "poppler-utils)")
    return out.stdout.decode("utf-8", "replace").split("\f")


def ga_senate_emails(pages):
    """{district: (surname, email)} from 'State Senators by District'."""
    page = [p for p in pages if "State Senators by District" in p and "Email Address" in p]
    if len(page) != 1:
        raise SystemExit("FAIL: the General Assembly Roster has %d pages headed 'State "
                         "Senators by District' with an e-mail column (expected 1)"
                         % len(page))
    lines = page[0].split("\n")
    found = {}
    for i, line in enumerate(lines):
        m = GA_LINE_RE.match(line.strip())
        if not m:
            continue
        email = m.group("email")
        if email.endswith(("@", ".")) and i + 1 < len(lines):
            # A long address wraps: its tail is the first word of the next line.
            tail = lines[i + 1].split()
            if tail and re.fullmatch(r"[A-Za-z0-9.-]+", tail[0]):
                email += tail[0]
        district = int(m.group("district"))
        if district in found:
            raise SystemExit("FAIL: the General Assembly Roster prints Senate District %d "
                             "twice" % district)
        found[district] = (m.group("last").strip(), email)
    if len(found) < 30:
        raise SystemExit("FAIL: read only %d senators' lines from the General Assembly "
                         "Roster (expected about 34) — the page layout changed" % len(found))
    return found


def build_senate(pages, previous, today):
    cfg = CHAMBERS["S"]
    page = pages.get("senate-directory.html", SENATE_DIRECTORY)
    street, city = senate_address(page)
    cards = parse_senate_directory(page)
    year, roster_url = ga_roster_url(pages.get("sos-pubs.html", SOS_PUBS))
    emails = ga_senate_emails(pdf_text(pages.get("ga-roster.pdf", roster_url, binary=True)))
    seats, notes = {}, []
    for card in cards:
        district = card["district"]
        where = "Senate %d" % district
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats:
            raise SystemExit("FAIL: %s carries two directory cards" % where)
        if card["name"].lower() == "vacant":
            seats[district] = vacancy(
                cfg, "The Missouri Senate's senator directory lists this seat as vacant.",
                SENATE_DIRECTORY, previous, district, today)
            notes.append("%s: vacant" % where)
            continue
        member = {"name": card["name"]}
        party = party_word(card["party"], where, notes)
        if party:
            member["party"] = party
        # The address only when the roster's line for this seat names the
        # same surname and the address's own name contains it.
        line = emails.get(district)
        if line:
            surname, email = line
            if letters(surname) and letters(surname) in letters(card["name"]) \
                    and letters(surname) in letters(email.split("@")[0]):
                email = plain_email(email, where, notes)
                if email:
                    member["email"] = email
            else:
                notes.append("%s: the %d General Assembly Roster prints %s for this seat, "
                             "so its e-mail address was not carried" % (where, year, surname))
        else:
            notes.append("%s: the %d General Assembly Roster prints no line for this seat"
                         % (where, year))
        office = []
        room = card["room"]
        if room:
            if not re.fullmatch(r"\d+[A-Z]?", room):
                raise SystemExit("FAIL: %s's Capitol office reads %r" % (where, room))
            office = ["%s, Room %s" % (street, room), city]
        phone = card["phone"]
        if phone:
            if PHONE_RE.match(phone):
                office.append(phone)
            else:
                notes.append("%s: the Capitol telephone is not printed as one number, so "
                             "it was not carried" % where)
        if office:
            member["capitolOffice"] = office
        url = card["url"]
        parts = urllib.parse.urlsplit(url)
        if parts.scheme == "https" and parts.netloc == "www.senate.mo.gov" \
                and parts.path.lower() == "/senators/member":
            member["url"] = url
        else:
            notes.append("%s: the directory links %r, which is not a senator's page, so "
                         "no link ships" % (where, url))
        seats[district] = member
    return seats, notes


# --- House ------------------------------------------------------------------

def house_base(session_js):
    m = re.search(r"var baseURL = '(https://documents\.house\.mo\.gov/xml/\d+-)';", session_js)
    if not m:
        raise SystemExit("FAIL: SessionSet.js no longer names the session's file prefix "
                         "(var baseURL = '...') — the House changed how it publishes")
    return m.group(1)


def house_list(xml_text, base):
    """{district: url} from the House's member list file."""
    root = ET.fromstring(xml_text)
    out = {}
    for row in root.findall("RepresentativeXML"):
        district = (row.findtext("RepresentativeDistrict") or "").strip()
        link = (row.findtext("RepresentativeXMLLink") or "").strip()
        if not district.isdigit() or not link.startswith(base):
            raise SystemExit("FAIL: a House list row reads %r / %r" % (district, link))
        if int(district) in out:
            raise SystemExit("FAIL: the House list names District %s twice" % district)
        out[int(district)] = link
    return out


def house_member(xml_text, where):
    """The fields this script reads from one representative's file, or None
    when the file names nobody."""
    root = ET.fromstring(xml_text)
    info = root.find("RepresentativeData/RepresentativeInfo")
    if info is None:
        return None
    # Only these fields are read; Hometown, LegislativeAssistant, Biography and
    # Counties are never touched.
    get = lambda tag: clean(info.findtext(tag) or "")  # noqa: E731
    fields = {tag: get(tag) for tag in ("FirstName", "LastName", "DistrictNum", "Party",
                                        "CapitolAddress", "PhoneNumber", "EmailAddress")}
    if not fields["LastName"] and not fields["FirstName"]:
        return None
    if not fields["DistrictNum"].isdigit():
        raise SystemExit("FAIL: %s's file carries no district number" % where)
    return fields


def capitol_lines(address):
    """The House's Capitol address as printed, one line per comma part, less
    the chamber's own name: "MO House of Representatives, 201 West Capitol
    Avenue, Room 414, Jefferson City MO 65101"."""
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if parts and parts[0].lower().startswith("mo house of representatives"):
        parts = parts[1:]
    return parts


def build_house(pages, previous, today):
    cfg = CHAMBERS["H"]
    base = house_base(pages.get("house-session.js", HOUSE_SESSION_JS))
    links = house_list(pages.get("house-list.xml", base + "MemberList.XML"), base)
    missing = [d for d in range(1, cfg["seats"] + 1) if d not in links]
    extra = [d for d in links if not 1 <= d <= cfg["seats"]]
    if missing or extra:
        raise SystemExit("FAIL: the House list leaves out District(s) %s and names %s"
                         % (missing, extra))
    seats, notes = {}, []
    for district in range(1, cfg["seats"] + 1):
        where = "House %d" % district
        fields = house_member(pages.get("house/%03d.xml" % district, links[district]), where)
        if fields is None or "vacant" in (fields["FirstName"] + " " + fields["LastName"]).lower():
            seats[district] = vacancy(
                cfg, "The Missouri House of Representatives' own member file for this "
                     "district names nobody.",
                HOUSE_ROSTER_PAGE, previous, district, today)
            notes.append("%s: vacant" % where)
            continue
        if int(fields["DistrictNum"]) != district:
            raise SystemExit("FAIL: the House list's file for District %d says District %s"
                             % (district, fields["DistrictNum"]))
        name = " ".join(p for p in (fields["FirstName"], fields["LastName"]) if p)
        member = {"name": name}
        party = party_word(fields["Party"], where, notes)
        if party:
            member["party"] = party
        email = plain_email(fields["EmailAddress"], where, notes)
        if email:
            member["email"] = email
        office = capitol_lines(fields["CapitolAddress"])
        phone = fields["PhoneNumber"]
        if phone:
            if PHONE_RE.match(phone):
                office.append(phone)
            else:
                notes.append("%s: the Capitol telephone is not printed as one number, so "
                             "it was not carried" % where)
        if office:
            member["capitolOffice"] = office
        seats[district] = member
    return seats, notes


# --- both -------------------------------------------------------------------

def check(chamber, seats):
    cfg = CHAMBERS[chamber]
    missing = [d for d in range(1, cfg["seats"] + 1) if d not in seats]
    if missing:
        raise SystemExit("FAIL: the %s has no record for District(s) %s"
                         % (cfg["label"], ", ".join(map(str, missing))))
    roster = {str(d): seats[d] for d in range(1, cfg["seats"] + 1)}
    named = [m for m in roster.values() if m.get("name")]
    if len(named) < cfg["expected"]:
        raise SystemExit("FAIL: resolved %d named %s districts (expected >= %d) — "
                         "refusing to overwrite the roster with an incomplete chamber"
                         % (len(named), cfg["label"], cfg["expected"]))
    for field in ("email", "capitolOffice"):
        have = sum(1 for m in named if m.get(field))
        if have < MIN_FIELD_SHARE * len(named):
            raise SystemExit("FAIL: only %d of %d %s members carry %s — a field nearly "
                             "every member carried stopped arriving"
                             % (have, len(named), cfg["label"], field))
    return roster


def build(pages, out_dir, today):
    built = {}
    for chamber, builder in (("S", build_senate), ("H", build_house)):
        previous = previous_roster(out_dir, CHAMBERS[chamber])
        seats, notes = builder(pages, previous, today)
        built[chamber] = (check(chamber, seats), notes)

    # An address printed for two or more members, in either chamber, is an
    # office's and ships on no member's row.
    holders = {}
    for chamber, (roster, _) in built.items():
        for district, member in roster.items():
            if member.get("email"):
                holders.setdefault(member["email"].lower(), []).append(
                    "%s %s" % (CHAMBERS[chamber]["label"], district))
    shared = {a for a, who in holders.items() if len(who) > 1}
    for who in sorted(" and ".join(w) for w in holders.values() if len(w) > 1):
        print("NOTE: one e-mail address is printed for %s, so it is an office's and "
              "ships on no member's row" % who, file=sys.stderr)
    for roster, _ in built.values():
        for member in roster.values():
            if member.get("email", "").lower() in shared:
                del member["email"]
    return built


def main():
    args = sys.argv[1:]
    offline = save = None
    while args and args[0] in ("--offline", "--save"):
        if len(args) < 2:
            print(__doc__.split("Usage:")[1].split("--save writes")[0], file=sys.stderr)
            sys.exit(1)
        if args[0] == "--offline":
            offline = args[1]
        else:
            save = args[1]
        args = args[2:]
    if len(args) > 1 or (offline and save):
        print("usage: %s [--offline DIR | --save DIR] [output_dir]" % sys.argv[0],
              file=sys.stderr)
        sys.exit(1)
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    today = datetime.date.today().isoformat()

    built = build(Pages(offline, save), out_dir, today)

    # Write only once BOTH chambers have passed every guard, so a failure in
    # the House cannot leave a fresh Senate file beside a stale House one.
    os.makedirs(out_dir, exist_ok=True)
    for chamber, (roster, notes) in built.items():
        cfg = CHAMBERS[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for m in roster.values() if m.get("name")]
        print("Wrote %s (%d of %d seats named, %d with an e-mail, %d with a Capitol "
              "office, %d with its telephone)"
              % (out_path, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("capitolOffice")),
                 sum(1 for m in named
                     if any(PHONE_RE.match(x) for x in m.get("capitolOffice", ())))),
              file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)
    if _PACER is not None:
        for line in _PACER.report():
            print(line, file=sys.stderr)


if __name__ == "__main__":
    main()
