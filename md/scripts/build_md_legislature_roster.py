#!/usr/bin/env python3
"""
Build the Maryland Senate and House of Delegates rosters as same-origin
app-data files, from the Maryland General Assembly's own member pages at
mgaleg.maryland.gov, so the md-senate / md-house cards join a small roster
instead of reaching another host at click time.

THE TWO CHAMBERS ARE SHAPED DIFFERENTLY, AND SO ARE THEIR ROSTERS. Maryland
elects one senator and three delegates from each of 47 legislative districts.
A district's three delegates are elected either from the whole district or
from subdistricts drawn inside it: "1A", "1B" and "1C" elect one each, "2A"
elects two and "2B" one. So the Senate roster (md-senate-members.json) keys
the 47 districts by number to one member each, for the registerIlgaChamber
factory, and the House roster (md-house-members.json) keys the 71 districts
and subdistricts the map draws ("3", "38A") to {seats, members[, asOf]}, read
by index.html's own md-house block, as New Hampshire's House is. A weekly
GitHub Action (.github/workflows/update-md-legislature-roster.yml) reruns this
script and opens a PR when a roster changes.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The Senate's and House's member indexes (/mgawebsite/Members/Index/senate and
/house) carry one entry per member: the name ("Amprey, Marlon"), linked to
the member's page (/mgawebsite/Members/Details/<id>), the district ("District
40", "District 38A"), the counties, and the party ("Democrat" or
"Republican"). That day the Senate's held 47 members, one for every district,
and the House's 140 of the 141 delegates: District 36, which elects three
delegates from the whole district, listed two. Each member's page prints an
"Annapolis Info" block (the office building and room, "6 Bladen Street" or
"11 Bladen Street", and "Annapolis, MD 21401"), its telephone ("Phone
410-841-3520"), and a "Contact" e-mail link at house.maryland.gov or
senate.maryland.gov.

HOW MANY DELEGATES EACH DISTRICT ELECTS is DELEGATES below, read off that
day's House index: every whole district elects three, and each subdistrict
the number the index listed for it, which sums to 141 with District 36 at
three. The weekly run refuses a list naming more delegates for a district than
DELEGATES says, or naming a district the map does not draw, so a new plan
cannot be read into the old one.

WHAT IS READ. From each member: the name, district, party, the Annapolis
office address and telephone, the legislative e-mail address and the member's
page. The "Interim Info" block and the district office are not read, nor are
biographies, committees or staff. An office address that does not end in
"Annapolis, MD 2140x" is not carried.

ROBOTS. mgaleg.maryland.gov/robots.txt answered 404 on 2026-11-12, which RFC
9309 reads as no restriction; it is read through scripts/robots_policy.py with
the User-Agent the fetches send before the first fetch, and a stated
Crawl-delay is honoured. Pages are fetched one a second regardless.

Honesty: names are never guessed. A seat no member is listed for is shown as
one the index names nobody for, with the day it was read.

Usage:
    python3 md/scripts/build_md_legislature_roster.py [output_dir]
    python3 md/scripts/build_md_legislature_roster.py --save DIR [output_dir]
    python3 md/scripts/build_md_legislature_roster.py --offline DIR [output_dir]
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/md/)"
PACE_SECONDS = 1.0
ATTEMPTS = 4
RETRY_SECONDS = 20.0
SITE = "https://mgaleg.maryland.gov"
INDEX = SITE + "/mgawebsite/Members/Index/%s"
DETAILS = SITE + "/mgawebsite/Members/Details/%s"

# Whole districts elect three delegates; each subdistrict the number below.
WHOLE = 3
SUBDISTRICTS = {
    "1A": 1, "1B": 1, "1C": 1, "2A": 2, "2B": 1, "7A": 2, "7B": 1, "9A": 2,
    "9B": 1, "11A": 1, "11B": 2, "12A": 2, "12B": 1, "27A": 1, "27B": 1,
    "27C": 1, "29A": 1, "29B": 1, "29C": 1, "30A": 2, "30B": 1, "33A": 1,
    "33B": 1, "33C": 1, "34A": 2, "34B": 1, "35A": 2, "35B": 1, "37A": 1,
    "37B": 2, "38A": 1, "38B": 1, "38C": 1, "42A": 1, "42B": 1, "42C": 1,
    "43A": 2, "43B": 1, "44A": 1, "44B": 2, "47A": 2, "47B": 1,
}
DIVIDED = {re.match(r"\d+", k).group() for k in SUBDISTRICTS}
DELEGATES = dict(SUBDISTRICTS)
DELEGATES.update({str(n): WHOLE for n in range(1, 48) if str(n) not in DIVIDED})

CHAMBERS = {
    # 47 of 47 senators were listed on 2026-11-12.
    "S": {"out": "md-senate-members.json", "label": "Senate", "seats": 47,
          "expected": 42, "index": "senate", "domain": "senate.maryland.gov",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.9}},
    # 140 of 141 delegates were listed on 2026-11-12.
    "H": {"out": "md-house-members.json", "label": "House of Delegates",
          "districts": DELEGATES, "expected": 127, "index": "house",
          "domain": "house.maryland.gov",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.9}},
}

PARTIES = {"Democrat": "Democratic", "Democratic": "Democratic",
           "Republican": "Republican"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

ENTRY_RE = re.compile(
    r'<dd>\s*<a href="/mgawebsite/Members/Details/([a-z0-9]+)">(.*?)</a>\s*<br />\s*'
    r'District ([0-9]+[A-C]?)\s*<br />(.*?)<br />\s*([A-Za-z ]+?)\s*<br />', re.S)
ANNAPOLIS_RE = re.compile(
    r'<dt class="col-sm-3">Annapolis Info</dt>\s*<dd class="col-sm-9">\s*<dl>\s*'
    r'<dd>(.*?)</dd>\s*<dd>(.*?)</dd>', re.S)
CITY_RE = re.compile(r"^Annapolis,? MD 2140\d(-\d{4})?$")
PHONE_RE = re.compile(r"Phone (\d{3}-\d{3}-\d{4})")
MAILTO_RE = re.compile(r'<dt class="col-sm-3">Contact</dt>.*?href="mailto:([^"?]+)', re.S)
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@(house|senate)\.maryland\.gov$", re.I)


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


_SESSION = None
_GATE = None
_PACER = None
_LAST = [0.0]


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
    return _SESSION


def fetch(url):
    import requests

    global _GATE, _PACER
    if _GATE is None:
        _GATE = RobotsGate(session(), USER_AGENT)
        _PACER = HostPacer(_GATE)
        ok, why = _GATE.allows(url)
        print("robots.txt %s: %s" % (urllib.parse.urlsplit(url).netloc, why), file=sys.stderr)
    ok, why = _GATE.allows(url)
    if not ok:
        raise SystemExit("FAIL: robots.txt refuses %s (%s)" % (url, why))
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        wait = PACE_SECONDS - (time.time() - _LAST[0])
        if wait > 0:
            time.sleep(wait)
        try:
            with _PACER.hold(url):
                resp = session().get(url, timeout=60)
            _LAST[0] = time.time()
            resp.raise_for_status()
            return resp.content.decode("utf-8", errors="replace")
        except requests.RequestException as exc:
            _LAST[0] = time.time()
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
                return fh.read()
        body = fetch(url)
        if self.save:
            path = os.path.join(self.save, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)
        return body


def name_of(listed):
    parts = [p.strip() for p in listed.split(",") if p.strip()]
    if len(parts) == 2:
        return "%s %s" % (parts[1], parts[0])
    if len(parts) == 3:
        return "%s %s %s" % (parts[1], parts[0], parts[2])
    return listed


def read_member(pages, ident, listed, district, party, where, notes):
    url = DETAILS % ident
    page = pages.get("member/%s.html" % ident, url)
    name = name_of(clean(listed))
    if not name or re.search(r"\d", name):
        raise SystemExit("FAIL: %s's entry names %r" % (where, listed))
    member = {"name": name}
    party = clean(party)
    if party in PARTIES:
        member["party"] = PARTIES[party]
    elif party:
        member["party"] = party
        notes.append("%s: party printed as %r ships as printed" % (where, party))
    block = ANNAPOLIS_RE.search(page)
    office = []
    if block:
        lines = [clean(x) for x in re.split(r"<br\s*/?>", block.group(1)) if clean(x)]
        if lines and CITY_RE.match(lines[-1]):
            office = lines
        else:
            notes.append("%s: the Annapolis address reads %r, not carried" % (where, lines))
        phone = PHONE_RE.search(clean(block.group(2)))
        if phone:
            office.append(phone.group(1))
    else:
        notes.append("%s: the member's page prints no Annapolis office" % where)
    if office:
        member["capitolOffice"] = office
    mail = MAILTO_RE.search(page)
    email = urllib.parse.unquote(mail.group(1)).strip() if mail else ""
    if EMAIL_RE.match(email):
        member["email"] = email
    elif email:
        notes.append("%s: an e-mail address off the legislature's domains was not carried"
                     % where)
    member["url"] = url
    return member


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def build_senate(pages, previous, today):
    cfg = CHAMBERS["S"]
    entries = ENTRY_RE.findall(pages.get("senate-index.html", INDEX % cfg["index"]))
    if len(entries) < cfg["seats"] - 5:
        raise SystemExit("FAIL: the Senate index yielded %d entries — its layout changed"
                         % len(entries))
    seats, notes = {}, []
    for ident, listed, district, _counties, party in entries:
        if not district.isdigit() or not 1 <= int(district) <= cfg["seats"]:
            raise SystemExit("FAIL: a Senate entry names District %r" % district)
        d = int(district)
        where = "Senate %d" % d
        if d in seats:
            raise SystemExit("FAIL: %s is listed twice" % where)
        seats[d] = read_member(pages, ident, listed, d, party, where, notes)
    for d in range(1, cfg["seats"] + 1):
        if d not in seats:
            prev = previous.get(str(d)) or {}
            seats[d] = {"asOf": (prev.get("asOf") if not prev.get("name") else None) or today}
            notes.append("Senate %d: no member listed" % d)
    roster = {str(d): seats[d] for d in range(1, cfg["seats"] + 1)}
    check(cfg, [m for m in roster.values() if m.get("name")])
    return roster, notes


def build_house(pages, previous, today):
    cfg = CHAMBERS["H"]
    entries = ENTRY_RE.findall(pages.get("house-index.html", INDEX % cfg["index"]))
    if len(entries) < 120:
        raise SystemExit("FAIL: the House index yielded %d entries — its layout changed"
                         % len(entries))
    members, notes = {d: [] for d in DELEGATES}, []
    for ident, listed, district, _counties, party in entries:
        if district not in DELEGATES:
            raise SystemExit("FAIL: a House entry names District %r, which is not one the "
                             "map draws — a new plan, read it before shipping" % district)
        where = "House %s" % district
        members[district].append(read_member(pages, ident, listed, district, party, where, notes))
        if len(members[district]) > DELEGATES[district]:
            raise SystemExit("FAIL: %s lists %d delegates and elects %d"
                             % (where, len(members[district]), DELEGATES[district]))
    roster = {}
    for district, seats in DELEGATES.items():
        listed = sorted(members[district], key=lambda m: m["name"].split()[-1])
        rec = {"seats": seats, "members": listed}
        if len(listed) < seats:
            prev = previous.get(district) or {}
            rec["asOf"] = (prev.get("asOf") if len(prev.get("members") or []) == len(listed)
                           else None) or today
            notes.append("House %s: %d of %d delegates listed" % (district, len(listed), seats))
        roster[district] = rec
    check(cfg, [m for rec in roster.values() for m in rec["members"]])
    return roster, notes


def check(cfg, named):
    if len(named) < cfg["expected"]:
        raise SystemExit("FAIL: resolved %d named %s members (expected >= %d) — "
                         "refusing to overwrite the roster with an incomplete chamber"
                         % (len(named), cfg["label"], cfg["expected"]))
    for field, share in sorted(cfg["fields"].items()):
        have = sum(1 for m in named if m.get(field))
        if have < share * len(named):
            raise SystemExit("FAIL: only %d of %d %s members carry %s, under the floor "
                             "of %d%% — a field the members carried stopped arriving"
                             % (have, len(named), cfg["label"], field, round(share * 100)))


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
    built = {
        "S": build_senate(pages, previous_roster(out_dir, CHAMBERS["S"]), today),
        "H": build_house(pages, previous_roster(out_dir, CHAMBERS["H"]), today),
    }
    os.makedirs(out_dir, exist_ok=True)
    for chamber, (roster, notes) in built.items():
        cfg = CHAMBERS[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        if chamber == "S":
            named = [m for m in roster.values() if m.get("name")]
            total = cfg["seats"]
        else:
            named = [m for rec in roster.values() for m in rec["members"]]
            total = sum(DELEGATES.values())
        print("Wrote %s (%d of %d seats named, %d with a party, %d with an e-mail "
              "address, %d with an Annapolis office)"
              % (out_path, len(named), total,
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("capitolOffice"))), file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
