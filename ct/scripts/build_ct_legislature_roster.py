#!/usr/bin/env python3
"""
Build the Connecticut Senate and House of Representatives rosters (district
-> current officeholder) as same-origin app-data files, from the General
Assembly's own legislator list as the state publishes it on data.ct.gov, so
the ct-senate / ct-house cards join a small roster instead of reaching another
host at click time.

index.html's ct-senate / ct-house layers fetch data/app/ct-senate-members.json
and ct-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
capitolOffice, url}}, or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-ct-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The General Assembly's "Current Legislators" download is published as the
state open-data dataset rgw6-bpst ("Current Connecticut Legislators") on
data.ct.gov, and the dataset's own /resource/ endpoint answers it as JSON.
That day it held 187 records: 36 senators (office_code "S") and 151
representatives ("H"), one for every district of each chamber, each carrying
the district as a three-digit `dist` ("001"), the name in parts, the party
("Democrat" or "Republican"), the Legislative Office Building room, a
Capitol telephone, an e-mail address and the member's caucus page.

THE TELEPHONE IS THE OFFICE'S, SO IT SHIPS AS THE OFFICE'S. 167 of the 187
records print one of a handful of caucus numbers (860-240-8585 beside 64
members, 860-240-8700 beside 49), which by the fleet's rule belongs to the
office the members sit in rather than to any of them. Every number, shared or
not, therefore ships on the card's Capitol office, under the room, and never
as the member's own telephone.

THE E-MAIL FIELD IS NOT ALWAYS AN ADDRESS. The 25 Senate Democrats' records
hold the caucus website's address there instead; that is not an e-mail
address and is not carried. An address printed beside two or more members
would be an office's and would ship on nobody; none was that day.

THE MEMBER'S PAGE IS ITS CAUCUS'S. Each record's url is the member's page on
their caucus's website: the House and Senate Democrats' sites are under
ct.gov (housedems.ct.gov, senatedems.ct.gov), the House and Senate
Republicans' are not (cthousegop.com, ctsenaterepublicans.com). The state's
own dataset prints all four, so all four are carried, each only where the
address is printed for that one member; limiting the links to ct.gov would
have dropped every Republican's page and none of the Democrats'.

THE ADDRESS. 175 records print the building as "Legislative Office Building",
10 as "Legislative Office Bldg", one as "300 Capitol Avenue" and one as "300
Capitol Ave., LOB", all in "Hartford, CT 06106-1591" (spaced variously, two
without the +4). They are one building, which the dataset itself places at 300
Capitol Avenue, so every card prints "Room <n>", "Legislative Office Building",
"300 Capitol Avenue" and "Hartford, CT 06106-1591". Four senators' records
print no room number; their cards carry the building without a room.

WHAT IS READ, AND WHAT IS NEVER READ. The query names its columns ($select),
so the dataset's home address, home town and home telephone fields are never
requested, let alone read.

ROBOTS. data.ct.gov/robots.txt, read 2026-11-12, puts `User-agent: *` under a
Crawl-delay of 1 second and disallows nothing under /resource/. It is read
through scripts/robots_policy.py with the User-Agent the fetch sends before the
fetch, and its Crawl-delay is honoured through HostPacer. A run makes one
request.

Honesty: names are never guessed. A seat no member is listed for gets a record
naming nobody, dated; a seat carried twice stops the build.

Usage:
    python3 ct/scripts/build_ct_legislature_roster.py [output_dir]
    python3 ct/scripts/build_ct_legislature_roster.py --save DIR [output_dir]
    python3 ct/scripts/build_ct_legislature_roster.py --offline DIR [output_dir]

--save writes the response into DIR (legislators.json), reading it back when
DIR already holds it; --offline reads it back instead of fetching, for
building and testing without the network.
"""

import collections
import datetime
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/ct/)"
ATTEMPTS = 4
RETRY_SECONDS = 20.0

DATASET = "rgw6-bpst"
DATASET_PAGE = "https://data.ct.gov/d/" + DATASET
COLUMNS = ("dist", "office_code", "first_name", "middle_initial", "last_name",
           "suffix", "commonly_used_name", "capitol_street_address",
           "capitol_city", "capitol_phone", "room_number", "party", "email",
           "url")
FEED = ("https://data.ct.gov/resource/%s.json?" % DATASET) + urllib.parse.urlencode(
    {"$select": ",".join(COLUMNS), "$limit": "1000"})

# The building and its street, as the dataset itself prints them.
BUILDING = ["Legislative Office Building", "300 Capitol Avenue"]
STREETS = {"legislative office building", "legislative office bldg",
           "300 capitol avenue", "300 capitol ave., lob"}
CITY_RE = re.compile(r"^Hartford,\s+CT\s+(06106(?:-\d{4})?)$")

# Floors catch a truncated download or a column that stopped arriving while
# tolerating real vacancies: 36 of 36 senators and 151 of 151 representatives
# were listed on 2026-11-12.
CHAMBERS = {
    "S": {"out": "ct-senate-members.json", "label": "Senate", "seats": 36,
          "expected": 32,
          # The share of named members carrying each field, floored below what
          # 2026-11-12 measured (e-mail 11 of 36: the other 25 records hold a
          # website there). A field falling under its floor is the Brown County
          # shape: the row count holds and the contact goes.
          "fields": {"party": 0.9, "capitolOffice": 0.9, "url": 0.9,
                     "email": 0.2}},
    "H": {"out": "ct-house-members.json", "label": "House", "seats": 151,
          "expected": 136,
          "fields": {"party": 0.9, "capitolOffice": 0.9, "url": 0.9,
                     "email": 0.8}},
}

PARTIES = {"Republican": "Republican", "Democrat": "Democratic",
           "Democratic": "Democratic"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

ROOM_RE = re.compile(r"^\d{1,4}[A-Z]?$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@([a-z]+\.)?ct\.gov$", re.I)
URL_RE = re.compile(r"^https?://[A-Za-z0-9.-]+\.[a-z]{2,}(/\S*)?$")


def normal_phone(text):
    """A ten-digit number as NNN-NNN-NNNN, or None when the text is not one
    telephone number."""
    if re.search(r"[A-Za-z]", text or ""):
        return None
    digits = re.sub(r"\D", "", text or "")
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


_SESSION = None
_GATE = None
_PACER = None


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
        _SESSION.headers["Accept"] = "application/json"
    return _SESSION


def fetch(url):
    import requests

    global _GATE, _PACER
    if _GATE is None:
        _GATE = RobotsGate(session(), USER_AGENT)
        _PACER = HostPacer(_GATE)
    ok, why = _GATE.allows(url)
    print("robots.txt %s: %s" % (urllib.parse.urlsplit(url).netloc, why),
          file=sys.stderr)
    if not ok:
        raise SystemExit("FAIL: robots.txt refuses %s (%s)" % (url, why))
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        try:
            with _PACER.hold(url):
                resp = session().get(url, timeout=60)
            resp.raise_for_status()
            return resp.content.decode("utf-8")
        except requests.RequestException as exc:  # reset, timeout, 5xx
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                session().close()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


def read_feed(offline=None, save=None):
    source = offline or (save if save and os.path.exists(
        os.path.join(save, "legislators.json")) else None)
    if source:
        with open(os.path.join(source, "legislators.json"), encoding="utf-8") as fh:
            return json.load(fh)
    body = fetch(FEED)
    if save:
        os.makedirs(save, exist_ok=True)
        with open(os.path.join(save, "legislators.json"), "w", encoding="utf-8") as fh:
            fh.write(body)
    return json.loads(body)


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def unlisted(previous, district, today):
    prev = previous.get(str(district)) or {}
    return {"asOf": (prev.get("asOf") if not prev.get("name") else None) or today,
            "sourceUrl": DATASET_PAGE}


def clean(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def person_name(rec):
    first = clean(rec.get("commonly_used_name")) or clean(rec.get("first_name"))
    parts = [first, clean(rec.get("middle_initial")), clean(rec.get("last_name"))]
    name = " ".join(p for p in parts if p)
    suffix = clean(rec.get("suffix"))
    if suffix:
        name += (", " if suffix.lower().rstrip(".") in ("jr", "sr") else " ") + suffix
    return name


def build_chamber(chamber, records, previous, today, emails, urls):
    cfg = CHAMBERS[chamber]
    rows = [r for r in records if r.get("office_code") == chamber]
    if len(rows) < cfg["seats"] - 6:
        raise SystemExit("FAIL: the dataset carries %d %s records — its layout "
                         "changed" % (len(rows), cfg["label"]))
    seats, notes = {}, []
    for rec in rows:
        dist = clean(rec.get("dist"))
        if not re.match(r"^\d{1,3}$", dist) or not 1 <= int(dist) <= cfg["seats"]:
            raise SystemExit("FAIL: a %s record names district %r, not one of the "
                             "chamber's %d" % (cfg["label"], dist, cfg["seats"]))
        district = int(dist)
        where = "%s %d" % (cfg["label"], district)
        if district in seats:
            raise SystemExit("FAIL: %s is listed twice" % where)
        name = person_name(rec)
        if not clean(rec.get("last_name")) or re.search(r"\d", name):
            raise SystemExit("FAIL: %s's record names %r" % (where, name))
        member = {"name": name}
        party = clean(rec.get("party"))
        if party in PARTIES:
            member["party"] = PARTIES[party]
        elif party:
            member["party"] = party
            notes.append("%s: party printed as %r ships as printed" % (where, party))
        else:
            notes.append("%s: no party printed" % where)
        email = clean(rec.get("email"))
        if EMAIL_RE.match(email):
            if emails[email.lower()] > 1:
                notes.append("%s: an e-mail address printed beside %d members is "
                             "an office's and ships on nobody"
                             % (where, emails[email.lower()]))
            else:
                member["email"] = email
        elif email and "@" in email:
            notes.append("%s: an e-mail address off the state's domain was not "
                         "carried" % where)
        office = []
        street = clean(rec.get("capitol_street_address")).lower()
        city = CITY_RE.match(clean(rec.get("capitol_city")))
        if street in STREETS and city:
            room = clean(rec.get("room_number"))
            if ROOM_RE.match(room):
                office.append("Room " + room)
            elif room:
                notes.append("%s: the room reads %r, not carried" % (where, room))
            office += BUILDING + ["Hartford, CT " + city.group(1)]
        elif street or rec.get("capitol_city"):
            notes.append("%s: the office reads %r, %r, not carried"
                         % (where, rec.get("capitol_street_address"),
                            rec.get("capitol_city")))
        printed = clean(rec.get("capitol_phone"))
        phone = normal_phone(printed)
        if phone:
            office.append(phone)
        elif printed:
            notes.append("%s: the Capitol telephone reads %r, not carried"
                         % (where, printed))
        if office:
            member["capitolOffice"] = office
        url = clean(rec.get("url"))
        if URL_RE.match(url) and urls[url.lower()] == 1:
            member["url"] = url
        elif url:
            notes.append("%s: the member page %r is not one address printed for "
                         "this member alone, not carried" % (where, url))
        seats[district] = member
    for district in range(1, cfg["seats"] + 1):
        if district not in seats:
            seats[district] = unlisted(previous, district, today)
            notes.append("%s %d: no member listed" % (cfg["label"], district))
    return seats, notes


def check(chamber, seats):
    cfg = CHAMBERS[chamber]
    roster = {str(d): seats[d] for d in range(1, cfg["seats"] + 1)}
    named = [m for m in roster.values() if m.get("name")]
    if len(named) < cfg["expected"]:
        raise SystemExit("FAIL: resolved %d named %s districts (expected >= %d) — "
                         "refusing to overwrite the roster with an incomplete chamber"
                         % (len(named), cfg["label"], cfg["expected"]))
    for field, share in sorted(cfg["fields"].items()):
        have = sum(1 for m in named if m.get(field))
        if have < share * len(named):
            raise SystemExit("FAIL: only %d of %d %s members carry %s, under the floor "
                             "of %d%% — a field the members carried stopped arriving"
                             % (have, len(named), cfg["label"], field, round(share * 100)))
    return roster


def main():
    args = sys.argv[1:]
    offline = save = None
    while args and args[0] in ("--offline", "--save"):
        if len(args) < 2:
            sys.exit("usage: %s [--offline DIR | --save DIR] [output_dir]" % sys.argv[0])
        if args[0] == "--offline":
            offline = args[1]
        else:
            save = args[1]
        args = args[2:]
    if len(args) > 1 or (offline and save):
        sys.exit("usage: %s [--offline DIR | --save DIR] [output_dir]" % sys.argv[0])
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    today = datetime.date.today().isoformat()
    records = read_feed(offline, save)
    if not isinstance(records, list):
        raise SystemExit("FAIL: the dataset answered %r, not a list of records"
                         % type(records).__name__)
    emails = collections.Counter(clean(r.get("email")).lower() for r in records
                                 if EMAIL_RE.match(clean(r.get("email"))))
    urls = collections.Counter(clean(r.get("url")).lower() for r in records)

    built = {}
    for chamber in ("S", "H"):
        previous = previous_roster(out_dir, CHAMBERS[chamber])
        seats, notes = build_chamber(chamber, records, previous, today, emails, urls)
        built[chamber] = (check(chamber, seats), notes)

    # Write only once BOTH chambers have passed every guard.
    os.makedirs(out_dir, exist_ok=True)
    for chamber, (roster, notes) in built.items():
        cfg = CHAMBERS[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for m in roster.values() if m.get("name")]
        print("Wrote %s (%d of %d seats named, %d with a party, %d with an e-mail "
              "address, %d with a Capitol office)"
              % (out_path, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("capitolOffice"))), file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)
    if _PACER is not None:
        for line in _PACER.report():
            print(line, file=sys.stderr)


if __name__ == "__main__":
    main()
