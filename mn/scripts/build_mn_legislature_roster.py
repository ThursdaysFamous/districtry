#!/usr/bin/env python3
"""
Build the Minnesota Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from each chamber's own
site, so the mn-senate / mn-house cards join a small roster instead of naming
nobody.

index.html's mn-senate / mn-house layers fetch data/app/mn-senate-members.json
and mn-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district. This script writes the two rosters shaped
for the registerIlgaChamber factory. A weekly GitHub Action
(.github/workflows/update-mn-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-14.

THE SENATE. The Senate's site is www.mnsenate.gov (www.senate.mn answers every
address with a 301 to the same path there, measured 2026-11-15, so that host
is the one read), and its member list is drawn by a script that reads one
feed, /api/members, with no key and no sign-in.
That day the feed held 67 senators for 67 districts (34 DFL, 33 Republican),
each with a name, district, party, e-mail address, an office in the Minnesota
Senate Building or the Capitol (two lines, the second "St. Paul, MN 55155")
and a telephone number. A senator's own page is
/members/member_bio.html?mem_id=<mem_id>, the address the site's script
builds. The older host www.senate.mn.gov could not be reached at all from the
machine this was written on, so nothing is read from it.

THE HOUSE. www.house.mn.gov/members is one page of six tabs. The tab named
"District Order" (id "District") held all 134 sitting members that day, 67
DFL and 67 Republican, each as "Name (61A, DFL)" linked to the member's
page, followed by the member's office in a State Office Building (lines ending
"St. Paul, MN 55155"), a telephone number and an e-mail address. ONLY THAT
TAB IS READ. The page also carries a "Members-Elect" tab, the 134 people
elected on 3 November 2026, who take office in January 2027; reading every tab
would name two people for a seat, so a district listed twice inside the one
tab stops the build.

THE HOUSE'S DISTRICTS ARE LETTERED ("61A"), so its roster is keyed by that
name and each record is {"seats": 1, "members": [...]}, the shape
scripts/validate_chamber_rosters.py holds for a chamber whose districts are
not the numbers 1 to N (Maryland's House is the precedent). The page prints
"01A"; the key is "1A", which is what the app's join produces from the
boundary file.

AN OFFICE ADDRESS SHIPS ONLY WHEN IT IS IN ST. PAUL. Both chambers print each
member's Capitol-complex office. A block whose last line is not "St. Paul, MN
551.." is not carried and the run says which district, never the lines.

THE PARTY. Both sites print "DFL" and "R". They ship as
"Democratic-Farmer-Labor" and "Republican"; any other value ships as printed
and the run says so.

ROBOTS, read 2026-11-14 with the client the fetches send.
www.house.mn.gov/robots.txt: its `*` group disallows /Fiscal2/ and nothing
else; no Crawl-delay. www.mnsenate.gov/robots.txt: HTTP 404, no policy. Both are
read through scripts/robots_policy.py before the first fetch of each host.

Honesty: names are never guessed. A seat with no sitting member listed gets a
record naming nobody, dated; two sitting members for one seat stop the build.

Usage:
    python3 mn/scripts/build_mn_legislature_roster.py [output_dir]
    python3 mn/scripts/build_mn_legislature_roster.py --save DIR [output_dir]
    python3 mn/scripts/build_mn_legislature_roster.py --offline DIR [output_dir]
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
ATTEMPTS = 4
RETRY_SECONDS = 20.0
SENATE_SITE = "https://www.mnsenate.gov"
SENATE_FEED = SENATE_SITE + "/api/members"
SENATE_PAGE = SENATE_SITE + "/members/member_bio.html?mem_id=%d"
HOUSE_SITE = "https://www.house.mn.gov"
HOUSE_LIST = HOUSE_SITE + "/members"
SOURCES = {"S": (SENATE_FEED, "senate-members.json"),
           "H": (HOUSE_LIST, "house-members.html")}

HOUSE_DISTRICTS = {"%d%s" % (n, half): 1 for n in range(1, 68) for half in "AB"}

# 67 of 67 senators and 134 of 134 representatives were seated on 2026-11-14.
CHAMBERS = {
    "S": {"out": "mn-senate-members.json", "label": "Senate", "seats": 67,
          "expected": 60, "title": "Senator",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.9}},
    "H": {"out": "mn-house-members.json", "label": "House of Representatives",
          "districts": HOUSE_DISTRICTS, "expected": 120,
          "title": "Representative",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.9}},
}

PARTIES = {"DFL": "Democratic-Farmer-Labor", "R": "Republican"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

PANE_RE = re.compile(r'<div[^>]+class="tab-pane[^"]*"[^>]*\bid="([^"]+)"')
MEMBER_RE = re.compile(
    r'<h5[^>]*>\s*<a href="(/members/profile/\d+)">\s*<b>([^<]+?)\s*'
    r'\((\d{1,2}[AB]),\s*([A-Za-z]+)\)\s*</b>\s*</a>\s*</h5>(.*?)</div>', re.S)
MAILTO_RE = re.compile(r'href="mailto:([^"?]+)"')
PHONE_RE = re.compile(r"^\d{3}-\d{3}-\d{4}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
ST_PAUL_RE = re.compile(r"^St\. Paul, MN 551\d\d(-\d{4})?$")


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


_SESSION = None
_GATE = None
_PACER = None


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
        except requests.RequestException as exc:
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                session().close()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


def load(offline, save):
    bodies = {}
    for chamber, (url, name) in SOURCES.items():
        if offline:
            with open(os.path.join(offline, name), encoding="utf-8") as fh:
                bodies[chamber] = fh.read()
            continue
        bodies[chamber] = fetch(url)
        if save:
            os.makedirs(save, exist_ok=True)
            with open(os.path.join(save, name), "w", encoding="utf-8") as fh:
                fh.write(bodies[chamber])
    return bodies


def party_of(printed, where, notes):
    printed = (printed or "").strip()
    if printed in PARTIES:
        return PARTIES[printed]
    if printed:
        notes.append("%s: party printed as %r ships as printed" % (where, printed))
    return printed or None


def office_of(lines, phone, where, notes):
    """The office block a chamber prints, kept only when it ends in St. Paul;
    the telephone number goes under it when it is one whole number."""
    lines = [line for line in lines if line]
    office = []
    if lines and ST_PAUL_RE.match(lines[-1]):
        office = list(lines)
    elif lines:
        notes.append("%s: the office block does not end in St. Paul, not carried" % where)
    if phone and PHONE_RE.match(phone):
        office.append(phone)
    elif phone:
        notes.append("%s: the telephone reads %r, not carried" % (where, phone))
    return office


def build_senate(body, notes):
    try:
        members = json.loads(body)["members"]
    except (ValueError, KeyError, TypeError):
        raise SystemExit("FAIL: the Senate's member feed is not the JSON it was")
    if not isinstance(members, list) or len(members) < 50:
        raise SystemExit("FAIL: the Senate's member feed held %s members — its shape changed"
                         % (len(members) if isinstance(members, list) else "no list of"))
    seats = {}
    for row in members:
        try:
            district = int(str(row.get("dist")).strip())
        except ValueError:
            raise SystemExit("FAIL: a senator's district reads %r" % row.get("dist"))
        where = "Senate %d" % district
        if not 1 <= district <= CHAMBERS["S"]["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's seats" % where)
        if district in seats:
            raise SystemExit("FAIL: %s is listed twice" % where)
        name = clean(str(row.get("preferred_full_name") or ""))
        if not name or re.search(r"\d", name):
            raise SystemExit("FAIL: %s names %r" % (where, name))
        member = {"name": name}
        party = party_of(row.get("party"), where, notes)
        if party:
            member["party"] = party
        email = clean(str(row.get("email") or ""))
        if EMAIL_RE.match(email):
            member["email"] = email
        elif email:
            notes.append("%s: the e-mail reads %r, not carried" % (where, email))
        office = office_of([clean(str(row.get("office_address_first_line") or "")),
                            clean(str(row.get("office_address_second_line") or ""))],
                           clean(str(row.get("full_phone_number") or "")), where, notes)
        if office:
            member["capitolOffice"] = office
        try:
            member["url"] = SENATE_PAGE % int(row.get("mem_id"))
        except (TypeError, ValueError):
            notes.append("%s: no member id, so no link to the senator's page" % where)
        seats[district] = member
    return seats


def house_key(printed):
    return printed.lstrip("0")


def build_house(body, notes):
    panes = [(m.start(), m.group(1)) for m in PANE_RE.finditer(body)]
    ids = [pane_id for _, pane_id in panes]
    if "District" not in ids:
        raise SystemExit("FAIL: the House members page has no \"District Order\" tab "
                         "(tabs found: %s)" % (", ".join(ids) or "none"))
    at = ids.index("District")
    start = panes[at][0]
    end = panes[at + 1][0] if at + 1 < len(panes) else len(body)
    seats = {}
    for page, name, printed, party, rest in MEMBER_RE.findall(body[start:end]):
        key = house_key(printed)
        where = "House %s" % key
        if key not in HOUSE_DISTRICTS:
            raise SystemExit("FAIL: %s is not one of the chamber's districts" % where)
        if key in seats:
            raise SystemExit("FAIL: %s is listed twice in the District Order tab" % where)
        name = clean(name)
        if not name or re.search(r"\d", name):
            raise SystemExit("FAIL: %s names %r" % (where, name))
        member = {"name": name}
        party = party_of(party, where, notes)
        if party:
            member["party"] = party
        mail = MAILTO_RE.search(rest)
        email = html_module.unescape(mail.group(1)).strip() if mail else ""
        if EMAIL_RE.match(email):
            member["email"] = email
        elif email:
            notes.append("%s: the e-mail reads %r, not carried" % (where, email))
        block = rest.split("<b>E-mail</b>")[0]
        lines = [clean(part) for part in re.split(r"<br\s*/?>", block)]
        lines = [line for line in lines if line]
        phone = ""
        if lines and re.match(r"^[\d() .-]{7,}$", lines[-1]):
            phone = lines.pop()
        office = office_of(lines, phone, where, notes)
        if office:
            member["capitolOffice"] = office
        member["url"] = HOUSE_SITE + page
        seats[key] = member
    if len(seats) < 100:
        raise SystemExit("FAIL: the District Order tab held %d members — its layout changed"
                         % len(seats))
    return seats


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def unnamed_since(prev, today):
    """The day a seat was first read with nobody listed, kept across runs."""
    prev = prev if isinstance(prev, dict) else {}
    named = prev.get("name") or any(
        isinstance(m, dict) and m.get("name") for m in prev.get("members") or [])
    return (prev.get("asOf") if not named else None) or today


def check_floors(chamber, named):
    cfg = CHAMBERS[chamber]
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


def build(bodies, previous, today):
    notes = {"S": [], "H": []}
    senate = build_senate(bodies["S"], notes["S"])
    house = build_house(bodies["H"], notes["H"])
    out = {"S": {}, "H": {}}
    for district in range(1, CHAMBERS["S"]["seats"] + 1):
        key = str(district)
        if district in senate:
            out["S"][key] = senate[district]
        else:
            out["S"][key] = {"asOf": unnamed_since(previous["S"].get(key), today)}
            notes["S"].append("Senate %d: no sitting member listed" % district)
    for key in HOUSE_DISTRICTS:
        if key in house:
            out["H"][key] = {"seats": 1, "members": [house[key]]}
        else:
            out["H"][key] = {"seats": 1, "members": [],
                             "asOf": unnamed_since(previous["H"].get(key), today)}
            notes["H"].append("House %s: no sitting member listed" % key)
    check_floors("S", list(senate.values()))
    check_floors("H", list(house.values()))
    return out, notes


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
    previous = {c: previous_roster(out_dir, cfg) for c, cfg in CHAMBERS.items()}
    built, notes = build(load(offline, save), previous, today)
    os.makedirs(out_dir, exist_ok=True)
    for chamber in ("S", "H"):
        cfg, roster = CHAMBERS[chamber], built[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for rec in roster.values()
                 for m in (rec.get("members") if "members" in rec else [rec])
                 if m.get("name")]
        print("Wrote %s (%d of %d seats named, %d with a party, %d with an e-mail "
              "address, %d with a Capitol office)"
              % (out_path, len(named), len(roster),
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("capitolOffice"))), file=sys.stderr)
        for note in notes[chamber]:
            print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
