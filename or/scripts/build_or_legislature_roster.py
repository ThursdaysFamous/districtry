#!/usr/bin/env python3
"""
Build the Oregon Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from the Oregon State
Legislature's own data service at api.oregonlegislature.gov, so the or-senate
/ or-house cards join a small roster instead of reaching another host at click
time.

index.html's or-senate / or-house layers fetch data/app/or-senate-members.json
and or-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
capitolOffice, url}}, or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-or-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The legislature publishes an OData service (the source of its Oregon
Legislative Information System). LegislativeSessions lists each session with
its BeginDate; LegislativeSessions('<key>')/Legislators lists the members of
one session, one record each: FirstName, LastName, Chamber ("S" or "H"),
DistrictNumber, Party ("Democrat" or "Republican"), CapitolAddress ("900 Court
St NE, H-479, Salem, OR, 97301"), CapitolPhone ("503-986-1419"), EmailAddress
at oregonlegislature.gov and WebSiteUrl (the member's page on
oregonlegislature.gov). The session read is the REGULAR session (a key ending
"R1") with the latest BeginDate on or before the day of the run: on 2026-11-12
that was 2026R1, which listed 30 senators and 60 representatives, every seat
of both chambers, and named the members appointed since the 2025 session
(House 48 and 51 and Senate 26 differ from 2025R1's list). A session that has
not begun yet is never read, so members elected in November are not shown
before they are sworn in.

WHAT IS READ. From each member: the name, chamber, district, party, Capitol
address and telephone, the e-mail address when it is at
oregonlegislature.gov, and the member's page. Nothing else the record carries
is read; it carries no home address.

ROBOTS. api.oregonlegislature.gov/robots.txt answered 404 on 2026-11-12, which
RFC 9309 reads as no restriction; it is read through scripts/robots_policy.py
with the User-Agent the fetches send before the first fetch, and a stated
Crawl-delay is honoured.

Honesty: names are never guessed. A seat no member is listed for gets a record
naming nobody, dated; a district listed twice in one session stops the build
for a person to read, because the service then names two members for one seat.

Usage:
    python3 or/scripts/build_or_legislature_roster.py [output_dir]
    python3 or/scripts/build_or_legislature_roster.py --save DIR [output_dir]
    python3 or/scripts/build_or_legislature_roster.py --offline DIR [output_dir]
"""

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

USER_AGENT = "districtry/1.0 (+https://districtry.com/or/)"
PACE_SECONDS = 1.0
ATTEMPTS = 4
RETRY_SECONDS = 20.0

SERVICE = "https://api.oregonlegislature.gov/odata/odataservice.svc"
SESSIONS = SERVICE + "/LegislativeSessions?$format=json"
LEGISLATORS = SERVICE + "/LegislativeSessions('%s')/Legislators?$format=json"

# 30 of 30 senators and 60 of 60 representatives were listed on 2026-11-12.
CHAMBERS = {
    "S": {"out": "or-senate-members.json", "label": "Senate", "seats": 30,
          "expected": 27, "of": "the Oregon State Senate",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.8}},
    "H": {"out": "or-house-members.json", "label": "House of Representatives",
          "seats": 60, "expected": 54, "of": "the Oregon House of Representatives",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.8}},
}

PARTIES = {"Democrat": "Democratic", "Democratic": "Democratic",
           "Republican": "Republican"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

SESSION_KEY_RE = re.compile(r"^\d{4}R1$")
# Measured 2026-11-12: 87 of the 90 records print "900 Court St NE, H-479,
# Salem, OR, 97301"; two write the room "Room H-380" and one the street "Court
# St.". All three are the Capitol and are carried in the one form.
ADDRESS_RE = re.compile(r"^900 Court St\.? NE, (?:Room )?([HS]-\d{2,4}[A-Z]?), Salem, OR,? (97301)$")
PHONE_RE = re.compile(r"^\d{3}-\d{3}-\d{4}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@oregonlegislature\.gov$", re.I)
PAGE_RE = re.compile(r"^https://(www\.)?oregonlegislature\.gov/\S+$")

_SESSION = None
_GATE = None
_PACER = None
_LAST = {}


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
        _SESSION.headers["Accept"] = "application/json"
    return _SESSION


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
        wait = PACE_SECONDS - (time.time() - _LAST[host])
        if wait > 0:
            time.sleep(wait)
        try:
            with _PACER.hold(url):
                resp = session().get(url, timeout=60)
            _LAST[host] = time.time()
            resp.raise_for_status()
            return resp.content.decode("utf-8-sig")
        except requests.RequestException as exc:
            _LAST[host] = time.time()
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                session().close()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


class Pages:
    def __init__(self, offline=None, save=None):
        self.offline, self.save = offline, save

    def get(self, name, url):
        source = self.offline or (self.save if self.save and
                                  os.path.exists(os.path.join(self.save, name)) else None)
        if source:
            with open(os.path.join(source, name), encoding="utf-8") as fh:
                return json.load(fh)
        body = fetch(url)
        if self.save:
            os.makedirs(self.save, exist_ok=True)
            with open(os.path.join(self.save, name), "w", encoding="utf-8") as fh:
                fh.write(body)
        return json.loads(body)


def current_session(sessions, today):
    begun = []
    for rec in sessions:
        key = str(rec.get("SessionKey") or "")
        begin = str(rec.get("BeginDate") or "")[:10]
        if SESSION_KEY_RE.match(key) and begin and begin <= today:
            begun.append((begin, key))
    if not begun:
        raise SystemExit("FAIL: the service lists no regular session that has begun")
    return max(begun)[1]


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def build(records, key, previous, today):
    seats = {"S": {}, "H": {}}
    notes = {"S": [], "H": []}
    for rec in records:
        chamber = rec.get("Chamber")
        if chamber not in CHAMBERS:
            raise SystemExit("FAIL: a %s record names chamber %r" % (key, chamber))
        cfg = CHAMBERS[chamber]
        try:
            district = int(str(rec.get("DistrictNumber") or "").strip())
        except ValueError:
            raise SystemExit("FAIL: a %s record names district %r"
                             % (key, rec.get("DistrictNumber")))
        where = "%s %d" % (cfg["label"].split()[0], district)
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats[chamber]:
            raise SystemExit("FAIL: %s is listed twice in session %s, so the service "
                             "names two members for one seat — read it before "
                             "shipping" % (where, key))
        name = " ".join(str(rec.get(f) or "").strip() for f in ("FirstName", "LastName")).strip()
        name = re.sub(r"\s+", " ", name)
        if not name or re.search(r"\d", name):
            raise SystemExit("FAIL: %s's record names %r" % (where, name))
        member = {"name": name}
        n = notes[chamber]
        party = str(rec.get("Party") or "").strip()
        if party in PARTIES:
            member["party"] = PARTIES[party]
        elif party:
            member["party"] = party
            n.append("%s: party printed as %r ships as printed" % (where, party))
        email = str(rec.get("EmailAddress") or "").strip()
        if EMAIL_RE.match(email):
            member["email"] = email
        elif email:
            n.append("%s: an e-mail address off oregonlegislature.gov was not carried" % where)
        office = []
        m = ADDRESS_RE.match(str(rec.get("CapitolAddress") or "").strip())
        if m:
            office = ["900 Court St NE", "Room " + m.group(1), "Salem, OR " + m.group(2)]
        elif rec.get("CapitolAddress"):
            n.append("%s: the Capitol address reads %r, not carried"
                     % (where, rec.get("CapitolAddress")))
        phone = str(rec.get("CapitolPhone") or "").strip()
        if PHONE_RE.match(phone):
            office.append(phone)
        elif phone:
            n.append("%s: the Capitol telephone reads %r, not carried" % (where, phone))
        if office:
            member["capitolOffice"] = office
        page = str(rec.get("WebSiteUrl") or "").strip()
        if PAGE_RE.match(page):
            member["url"] = page
        seats[chamber][district] = member
    out = {}
    for chamber, cfg in CHAMBERS.items():
        for district in range(1, cfg["seats"] + 1):
            if district not in seats[chamber]:
                prev = previous[chamber].get(str(district)) or {}
                seats[chamber][district] = {
                    "asOf": (prev.get("asOf") if not prev.get("name") else None) or today}
                notes[chamber].append("%s %d: no member listed"
                                      % (cfg["label"].split()[0], district))
        out[chamber] = check(chamber, seats[chamber])
    return out, notes


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
    pages = Pages(offline, save)
    key = current_session(pages.get("sessions.json", SESSIONS).get("value") or [], today)
    records = pages.get("legislators.json", LEGISLATORS % key).get("value") or []
    previous = {c: previous_roster(out_dir, cfg) for c, cfg in CHAMBERS.items()}
    built, notes = build(records, key, previous, today)
    os.makedirs(out_dir, exist_ok=True)
    for chamber in ("S", "H"):
        cfg, roster = CHAMBERS[chamber], built[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for m in roster.values() if m.get("name")]
        print("Wrote %s from session %s (%d of %d seats named, %d with a party, %d "
              "with an e-mail address, %d with a Capitol office)"
              % (out_path, key, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("capitolOffice"))), file=sys.stderr)
        for note in notes[chamber]:
            print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
