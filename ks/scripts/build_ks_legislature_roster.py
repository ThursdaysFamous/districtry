#!/usr/bin/env python3
"""
Build the Kansas Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from the Kansas
Legislature's own member feed at kslegislature.gov, so the ks-senate /
ks-house cards join a small roster instead of reaching another host at click
time.

index.html's ks-senate / ks-house layers fetch data/app/ks-senate-members.json
and ks-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
capitolOffice, url}}, or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-ks-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The legislature's website reads its member lists from a JSON feed it
publishes beside them: /li/api/v13/rev-1/members/ lists every member of each
chamber (house_members, senate_members: KPID, NAME, STATUS), and
/li/api/v13/rev-1/members/<KPID>/ returns one member's record. That day the
list carried 40 senators and 125 representatives, every one "Active", which
is every seat of both chambers. A member's record prints FULLNAME, DISTRICT,
PARTY ("Republican" or "Democrat"), EMAIL at house.ks.gov or senate.ks.gov,
OFFICENUM (the Statehouse room, "168-W") and OFFPH (the Statehouse telephone,
"785-296-8153"). The member's own page on the legislature's site
(/b2025_26/legislators/<KPID>/, which the site's older /li/b2025_26/members/
address redirects to) prints the same room, telephone and e-mail address
under "Contact & Info", and every page's footer prints the Statehouse address,
"300 SW 10th Ave, Topeka, KS 66612", which is carried under the room.

WHAT IS READ, AND WHAT IS NEVER READ. From each member: the name, district,
party, the e-mail address when it is at the legislature's own domain, the
Statehouse room and telephone, and the member's page. The record also carries
home and business addresses and telephones (every HM* and BUS* field), a cell
telephone, a spouse's name and an occupation; none of those is read.

ROBOTS. www.kslegislature.gov/robots.txt answered 404 on 2026-11-12, which
RFC 9309 reads as no restriction; it is read through scripts/robots_policy.py
with the User-Agent the fetches send before the first fetch, and a stated
Crawl-delay is honoured. The feed is paced at one request a second regardless.

Honesty: names are never guessed. A seat no member is listed for gets a record
naming nobody, dated; a seat carried twice stops the build.

Usage:
    python3 ks/scripts/build_ks_legislature_roster.py [output_dir]
    python3 ks/scripts/build_ks_legislature_roster.py --save DIR [output_dir]
    python3 ks/scripts/build_ks_legislature_roster.py --offline DIR [output_dir]

--save writes every response fetched into DIR (members.json and
member/<KPID>.json), reading back any it already holds; --offline reads them
back instead of fetching, for building and testing without the network.
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/ks/)"
PACE_SECONDS = 1.0
ATTEMPTS = 4
RETRY_SECONDS = 20.0

SITE = "https://www.kslegislature.gov"
FEED = SITE + "/li/api/v13/rev-1/members/"
STATEHOUSE = ["300 SW 10th Ave", "Topeka, KS 66612"]

# Floors catch a truncated feed or a layout change while tolerating real
# vacancies: 40 of 40 senators and 125 of 125 representatives were listed on
# 2026-11-12.
CHAMBERS = {
    "S": {"out": "ks-senate-members.json", "label": "Senate", "seats": 40,
          "expected": 36, "list": "senate_members", "prefix": "sen_",
          "domain": "senate.ks.gov", "of": "the Kansas Senate",
          # The share of named members carrying each field, floored below what
          # 2026-11-12 measured. A field falling under its floor is the Brown
          # County shape: the row count holds and the contact goes.
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.8}},
    "H": {"out": "ks-house-members.json", "label": "House of Representatives",
          "seats": 125, "expected": 113, "list": "house_members", "prefix": "rep_",
          "domain": "house.ks.gov", "of": "the Kansas House of Representatives",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.8}},
}

PARTIES = {"Republican": "Republican", "Democrat": "Democratic",
           "Democratic": "Democratic"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

KPID_RE = re.compile(r"^(sen|rep)_[a-z0-9_]+$")
ROOM_RE = re.compile(r"^\d{1,3}-[NSEW]$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@(house|senate)\.ks\.gov$", re.I)

def normal_phone(text):
    """A ten-digit number as NNN-NNN-NNNN, whatever punctuation the feed
    printed it with ("4357492828", "(801) 450-3701", "785 296-7122"), or None
    when the text is not one telephone number."""
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
                resp = session().get(url, timeout=45)
            _LAST[host] = time.time()
            resp.raise_for_status()
            return resp.content.decode("utf-8")
        except requests.RequestException as exc:  # reset, timeout, 5xx
            _LAST[host] = time.time()
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                session().close()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


class Pages:
    """Fetch, save or replay the responses one run reads."""

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
            path = os.path.join(self.save, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)
        return json.loads(body)


def biennium(today):
    """The legislature's two-year session as its addresses spell it: a
    session starts in an odd year, so 2026 is b2025_26."""
    year = int(today[:4])
    start = year if year % 2 else year - 1
    return "b%d_%02d" % (start, (start + 1) % 100)


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def unlisted(previous, district, today):
    prev = previous.get(str(district)) or {}
    return {"asOf": (prev.get("asOf") if not prev.get("name") else None) or today}


def build_chamber(chamber, pages, listing, previous, today):
    cfg = CHAMBERS[chamber]
    entries = listing.get(cfg["list"])
    if not isinstance(entries, list) or len(entries) < cfg["seats"] - 6:
        raise SystemExit("FAIL: the feed's %s list carries %r entries — its layout "
                         "changed" % (cfg["label"], len(entries or [])))
    page_base = "%s/%s/legislators/" % (SITE, biennium(today))
    seats, notes = {}, []
    for entry in entries:
        kpid = str(entry.get("KPID") or "")
        if not KPID_RE.match(kpid) or not kpid.startswith(cfg["prefix"]):
            raise SystemExit("FAIL: a %s list entry carries KPID %r" % (cfg["label"], kpid))
        if entry.get("STATUS") != "Active":
            notes.append("%s: listed as %r, not read" % (kpid, entry.get("STATUS")))
            continue
        rec = pages.get("member/%s.json" % kpid, FEED + kpid + "/").get("content") or {}
        if rec.get("KPID") != kpid:
            raise SystemExit("FAIL: the feed's record for %s names KPID %r"
                             % (kpid, rec.get("KPID")))
        district = rec.get("DISTRICT")
        where = "%s %s" % (cfg["label"].split()[0], district)
        if not isinstance(district, int) or not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s's record names district %r, not one of the "
                             "chamber's %d" % (kpid, district, cfg["seats"]))
        if district in seats:
            raise SystemExit("FAIL: %s is listed twice" % where)
        name = re.sub(r"\s+", " ", str(rec.get("FULLNAME") or "")).strip()
        if not name or re.search(r"\d", name):
            raise SystemExit("FAIL: %s's record names %r" % (where, name))
        member = {"name": name}
        party = str(rec.get("PARTY") or "").strip()
        if party in PARTIES:
            member["party"] = PARTIES[party]
        elif party:
            member["party"] = party
            notes.append("%s: party printed as %r ships as printed" % (where, party))
        else:
            notes.append("%s: no party printed" % where)
        email = str(rec.get("EMAIL") or "").strip()
        if EMAIL_RE.match(email):
            member["email"] = email
        elif email:
            notes.append("%s: an e-mail address off the legislature's domain was "
                         "not carried" % where)
        room = str(rec.get("OFFICENUM") or "").strip()
        printed = str(rec.get("OFFPH") or "").strip()
        phone = normal_phone(printed) or ""
        office = []
        if ROOM_RE.match(room):
            office = ["Room " + room] + STATEHOUSE
        elif room:
            notes.append("%s: the room reads %r, not carried" % (where, room))
        if phone:
            office.append(phone)
        elif printed:
            notes.append("%s: the Statehouse telephone reads %r, not carried"
                         % (where, printed))
        if office:
            member["capitolOffice"] = office
        else:
            notes.append("%s: no Statehouse room or telephone printed" % where)
        member["url"] = page_base + kpid + "/"
        seats[district] = member
    for district in range(1, cfg["seats"] + 1):
        if district not in seats:
            seats[district] = unlisted(previous, district, today)
            notes.append("%s %d: no member listed" % (cfg["label"].split()[0], district))
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
    pages = Pages(offline, save)
    listing = pages.get("members.json", FEED).get("content") or {}

    built = {}
    for chamber in ("S", "H"):
        previous = previous_roster(out_dir, CHAMBERS[chamber])
        seats, notes = build_chamber(chamber, pages, listing, previous, today)
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
              "address, %d with a Statehouse office)"
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
