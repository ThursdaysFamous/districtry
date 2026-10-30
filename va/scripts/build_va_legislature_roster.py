#!/usr/bin/env python3
"""
Build the Senate of Virginia and Virginia House of Delegates rosters (district
-> current officeholder) as same-origin app-data files, from each chamber's
OWN member pages, so the va-senate / va-house cards join a small roster
instead of reaching a third-party host at click time.

index.html's va-senate / va-house layers fetch data/app/va-senate-members.json
and va-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
capitolOffice, url}}, or a vacancy record). A weekly GitHub Action
(.github/workflows/update-va-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHERE THE SENATORS ARE, MEASURED 2026-10-29. The Senate's member list,
apps.senate.virginia.gov/Senator/index.php, prints one card per seat: the
senator's name linked to their own page (memberpage.php?id=S115), the district,
the party, the Capitol office's telephone and a district telephone. That day it
held 40 cards for the 40 seats. Each senator's own page prints the session
office (the General Assembly Building, a room number, the Senate's post office
box in Richmond and the office telephone), the senator's e-mail address, and a
district office. The session office, its telephone and the e-mail address are
read from the senator's page; the list's card gives the name, the district and
the party.

WHERE THE DELEGATES ARE. The House's member list, house.vga.virginia.gov/members,
prints one card per seat: the delegate's name ("Anderson, Jessica L.") linked
to their own page (/members/H0386), the district, the Capitol office's room,
the Capitol and district telephones and the delegate's e-mail address. On
2026-10-29 it held 100 cards, 99 delegates and District 20 printed "Vacant".
Each delegate's own page prints the name in reading order ("Jessica L.
Anderson"), the party as a letter before the district's description ("D -
Counties of James City (part) ..."), and the Capitol office (the General
Assembly Building, 201 North 9th Street, Richmond, the room number and the
office telephone). The name, the party and the Capitol office come from the
delegate's page; the e-mail address from the list's card.

WHAT IS READ, AND WHAT IS NEVER READ. From each member: the name, the
district, the party, the Capitol (session) office as printed, its telephone,
the member's e-mail address and the member's own page. Both chambers also
print a district office, which this builder has no way to tell apart from a
member's home, and staff names, and the House prints a biography; none of those
is read, and no district office ships. A telephone that is not printed as one number is not carried.

THE E-MAIL ADDRESS ships as printed, because the fleet's rule since 2026-10-17
(Adam: "E-mails too") is that an address a government source prints in one
official's own entry is that official's. An address printed for two or more
members is an office's and ships on no member's row.

ROBOTS. Each host's robots.txt is read through scripts/robots_policy.py with
the User-Agent the fetches send, before its first fetch, and a stated
Crawl-delay is honoured by its HostPacer. Read 2026-10-29:
apps.senate.virginia.gov answers 404 (no robots.txt, allow all) and
house.vga.virginia.gov serves a 99-byte file holding only a comment, which
binds nobody. Every host is paced at one request a second regardless.

Honesty: names are never guessed. A seat a chamber shows as vacant gets a
vacancy record naming that chamber's own list; a seat with no record, or with
two, stops the build.

Usage:
    python3 va/scripts/build_va_legislature_roster.py [output_dir]
    python3 va/scripts/build_va_legislature_roster.py --save DIR [output_dir]
    python3 va/scripts/build_va_legislature_roster.py --offline DIR [output_dir]

--save writes every page fetched into DIR (senate-list.html,
senate/<id>.html, house-list.html and house/<id>.html), reading back any it
already holds; --offline reads them back instead of fetching, for building and
testing without the network.
"""

import datetime
import html as html_module
import json
import os
import re
import sys
import time
import urllib.parse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from robots_policy import HostPacer, RobotsGate  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/va/)"
# Every host is paced at one second even where it states no delay.
MIN_PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

SENATE_LIST = "https://apps.senate.virginia.gov/Senator/index.php"
SENATE_MEMBER = "https://apps.senate.virginia.gov/Senator/memberpage.php?id=%s"
HOUSE_LIST = "https://house.vga.virginia.gov/members"
HOUSE_MEMBER = "https://house.vga.virginia.gov/members/%s"

# Floors catch a truncated list or a layout change while tolerating real
# vacancies: 40 of 40 senators and 99 of 100 delegates were named on
# 2026-10-29.
CHAMBERS = {
    "S": {"out": "va-senate-members.json", "label": "Senate", "seats": 40,
          "expected": 36, "body": "The Senate of Virginia"},
    "H": {"out": "va-house-members.json", "label": "House of Delegates", "seats": 100,
          "expected": 90, "body": "The Virginia House of Delegates"},
}
# A field nearly every named member carried on 2026-10-29. One going missing
# is the Brown County shape: the row count holds and the contact goes.
MIN_FIELD_SHARE = 0.9

PARTY_NAMES = {"Republican": "Republican", "Democrat": "Democratic",
               "Democratic": "Democratic", "Independent": "Independent",
               "R": "Republican", "D": "Democratic", "I": "Independent"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\(?\d{3}\)?[ -]?\d{3}-\d{4}$")

# One Senate list card: the member page link and name, then the district chip.
SENATE_CARD_RE = re.compile(
    r'<h5 class="card-title[^"]*">\s*<a [^>]*href="//apps\.senate\.virginia\.gov/Senator/'
    r'memberpage\.php\?id=(S\d+)\s*"[^>]*>(.*?)</a>\s*</h5>\s*'
    r'<span class="senator-chip">\s*District (\d+)\s*</span>(.*?)(?=senator-card|$)', re.S)
SENATE_PARTY_RE = re.compile(r"<strong>Party:</strong>\s*([A-Za-z]+)")
# The senator's own page: the session office block and the e-mail address.
SENATE_OFFICE_RE = re.compile(
    r"<h4[^>]*><strong>Session Office</strong></h4>(.*?)<h4", re.S)
SENATE_EMAIL_RE = re.compile(
    r'<div class="Emailtxt">\s*<p><a href="mailto:([^"]+)">', re.S)

# One House list card, split on its opening class.
HOUSE_CARD_SPLIT = 'class="delegate-card'
HOUSE_LINK_RE = re.compile(r'href="/members/(H\d+)">([^<]+)</a>')
HOUSE_DISTRICT_RE = re.compile(r'District:</span>\s*(\d+)')
HOUSE_EMAIL_RE = re.compile(r'href="mailto:([^"]+)"')
HOUSE_VACANT_RE = re.compile(r'<h2 class="[^"]*">\s*Vacant\s*</h2>')
# The delegate's own page: the name in reading order, the party letter before
# the district's description, and the Capitol office block.
HOUSE_NAME_RE = re.compile(
    r'aria-label="Delegate Basic Details"[^>]*>\s*<h2[^>]*>\s*(.*?)\s*</h2>', re.S)
HOUSE_PARTY_RE = re.compile(r'<p class="[^"]*tracking-wide">\s*([A-Z])\s+-\s+[^<]*</p>')
HOUSE_OFFICE_RE = re.compile(
    r'<div id="capitol-office-content"[^>]*>(.*?)</div>', re.S)

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


def fetch(url):
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
            # Every page read here declares UTF-8.
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as exc:  # reset, timeout, 5xx
            _LAST[host] = time.time()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


class Pages:
    """Fetch, save or replay the pages one run reads."""

    def __init__(self, offline=None, save=None):
        self.offline, self.save = offline, save

    def get(self, name, url):
        source = self.offline or (self.save if self.save and
                                  os.path.exists(os.path.join(self.save, name)) else None)
        if source:
            # --offline, or a page an interrupted --save run already wrote.
            with open(os.path.join(source, name), encoding="utf-8") as fh:
                return fh.read()
        body = fetch(url)
        if self.save:
            path = os.path.join(self.save, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)
        return body


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


def block_lines(fragment):
    """The printed lines of an address block: split on <br>, tags dropped."""
    parts = re.split(r"<br\s*/?>", fragment or "", flags=re.I)
    return [ln for ln in (clean(p) for p in parts) if ln]


def party_word(word, where, notes):
    if not word:
        notes.append("%s: no party printed" % where)
        return None
    if word not in PARTY_NAMES:
        notes.append("%s: party printed as %r ships as printed" % (where, word))
    return PARTY_NAMES.get(word, word)


def plain_email(raw, where, notes):
    if not raw:
        return None
    raw = raw.strip()
    if EMAIL_RE.match(raw):
        return raw
    notes.append("%s: an e-mail entry that is not one plain address was not carried" % where)
    return None


def phone_line(raw, where, notes):
    raw = (raw or "").strip()
    if not raw:
        return None
    if PHONE_RE.match(raw):
        return raw
    notes.append("%s: the Capitol telephone is not printed as one number, so it was "
                 "not carried" % where)
    return None


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def vacancy(why, source, previous, district, today):
    prev = previous.get(str(district)) or {}
    return {
        "vacant": True,
        "vacantWhy": why,
        "sourceUrl": source,
        # The day the chamber was first read saying so, kept across runs.
        "asOf": (prev.get("asOf") if prev.get("vacant") else None) or today,
    }


# --- Senate -----------------------------------------------------------------

def parse_senate_list(page):
    cards = []
    for m in SENATE_CARD_RE.finditer(page):
        member_id, name, district, rest = m.group(1), clean(m.group(2)), int(m.group(3)), m.group(4)
        party = SENATE_PARTY_RE.search(rest)
        cards.append({"id": member_id, "name": name, "district": district,
                      "party": party.group(1) if party else None})
    if len(cards) < 30:
        raise SystemExit("FAIL: the Senate's member list yielded %d cards — its layout "
                         "changed" % len(cards))
    return cards


def senate_office(member_page, where, notes):
    """The session office as printed, less the chamber's own name, with its
    telephone and no fax; and the e-mail address."""
    office = []
    m = SENATE_OFFICE_RE.search(member_page)
    if m:
        lines = block_lines(m.group(1))
        phone = None
        for ln in lines:
            if ln.lower().startswith("phone:"):
                phone = phone_line(ln.split(":", 1)[1], where, notes)
            elif ln.lower().startswith("fax:") or ln.lower() == "senate of virginia":
                continue
            elif ln.lower().startswith("room no:"):
                if office:
                    office[-1] = "%s, Room %s" % (office[-1], ln.split(":", 1)[1].strip())
                else:
                    office.append("Room %s" % ln.split(":", 1)[1].strip())
            else:
                office.append(ln)
        if phone:
            office.append(phone)
    else:
        notes.append("%s: the senator's page prints no session office" % where)
    em = SENATE_EMAIL_RE.search(member_page)
    email = plain_email(em.group(1), where, notes) if em else None
    if not em:
        notes.append("%s: the senator's page prints no e-mail address" % where)
    return office, email


def build_senate(pages, previous, today):
    cfg = CHAMBERS["S"]
    cards = parse_senate_list(pages.get("senate-list.html", SENATE_LIST))
    seats, notes = {}, []
    for card in cards:
        district = card["district"]
        where = "Senate %d" % district
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats:
            raise SystemExit("FAIL: %s carries two member cards" % where)
        if card["name"].lower() == "vacant":
            seats[district] = vacancy(
                "The Senate of Virginia's member list shows this seat as vacant.",
                SENATE_LIST, previous, district, today)
            notes.append("%s: vacant" % where)
            continue
        member = {"name": card["name"]}
        party = party_word(card["party"], where, notes)
        if party:
            member["party"] = party
        url = SENATE_MEMBER % card["id"]
        page = pages.get("senate/%s.html" % card["id"], url)
        if card["name"].split()[-1].lower() not in clean(page).lower():
            raise SystemExit("FAIL: %s's page does not name %s" % (where, card["name"]))
        office, email = senate_office(page, where, notes)
        if email:
            member["email"] = email
        if office:
            member["capitolOffice"] = office
        member["url"] = url
        seats[district] = member
    return seats, notes


# --- House ------------------------------------------------------------------

def parse_house_list(page):
    cards = []
    for chunk in page.split(HOUSE_CARD_SPLIT)[1:]:
        district = HOUSE_DISTRICT_RE.search(chunk)
        if not district:
            raise SystemExit("FAIL: a House member card prints no district")
        link = HOUSE_LINK_RE.search(chunk)
        email = HOUSE_EMAIL_RE.search(chunk)
        cards.append({
            "district": int(district.group(1)),
            "vacant": bool(HOUSE_VACANT_RE.search(chunk)) and not link,
            "id": link.group(1) if link else None,
            "listName": clean(link.group(2)) if link else None,
            "email": email.group(1) if email else None,
        })
    if len(cards) < 90:
        raise SystemExit("FAIL: the House's member list yielded %d cards — its layout "
                         "changed" % len(cards))
    return cards


def house_office(member_page, where, notes):
    """The Capitol office as printed on the delegate's page: the building,
    the street, the city, the room and the office telephone, in that order,
    with nothing after the telephone (the e-mail address and staff names)."""
    m = HOUSE_OFFICE_RE.search(member_page)
    if not m:
        notes.append("%s: the delegate's page prints no Capitol office" % where)
        return []
    text = clean(m.group(1))
    building = re.search(r"^(General Assembly Building)\s+", text)
    street = re.search(r"(\d+ North 9th Street), (Richmond, Virginia \d{5})", text)
    room = re.search(r"Room Number:\s*([0-9A-Za-z]+)", text)
    phone = re.search(r"Office:\s*(\(\d{3}\) \d{3}-\d{4})", text)
    office = []
    if building:
        office.append(building.group(1) + (", Room %s" % room.group(1) if room else ""))
    if street:
        office += [street.group(1), street.group(2)]
    if phone:
        office.append(phone.group(1))
    if not (building and street):
        notes.append("%s: the Capitol office reads %r and was not carried" % (where, text[:120]))
        return []
    return office


def build_house(pages, previous, today):
    cfg = CHAMBERS["H"]
    cards = parse_house_list(pages.get("house-list.html", HOUSE_LIST))
    seats, notes = {}, []
    for card in cards:
        district = card["district"]
        where = "House %d" % district
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats:
            raise SystemExit("FAIL: %s carries two member cards" % where)
        if card["vacant"]:
            seats[district] = vacancy(
                "The Virginia House of Delegates' member list shows this seat as vacant.",
                HOUSE_LIST, previous, district, today)
            notes.append("%s: vacant" % where)
            continue
        if not card["id"]:
            raise SystemExit("FAIL: %s's card names nobody and does not say vacant" % where)
        url = HOUSE_MEMBER % card["id"]
        page = pages.get("house/%s.html" % card["id"], url)
        name = HOUSE_NAME_RE.search(page)
        if not name:
            raise SystemExit("FAIL: %s's page prints no name" % where)
        name = clean(name.group(1))
        surname = card["listName"].split(",")[0].strip().lower()
        if surname not in name.lower():
            raise SystemExit("FAIL: %s's page names %r and the list %r"
                             % (where, name, card["listName"]))
        member = {"name": name}
        party = HOUSE_PARTY_RE.search(page)
        party = party_word(party.group(1) if party else None, where, notes)
        if party:
            member["party"] = party
        email = plain_email(card["email"], where, notes)
        if email:
            member["email"] = email
        office = house_office(page, where, notes)
        if office:
            member["capitolOffice"] = office
        member["url"] = url
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
    for field in ("email", "capitolOffice", "party"):
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
