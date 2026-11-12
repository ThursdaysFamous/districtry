#!/usr/bin/env python3
"""
Build the Massachusetts Senate and House of Representatives rosters as
same-origin app-data files, from the General Court's own member lists at
malegislature.gov, so the ma-senate / ma-house cards join a small roster
instead of reaching another host at click time.

MASSACHUSETTS NAMES ITS DISTRICTS. Every Senate and House district is a name
("Third Middlesex", "Second Plymouth and Norfolk", "19th Suffolk"), never a
number, so each roster is keyed by the district's name as the map's own
boundary file spells it (TIGER's BASENAME) and read by index.html's own
ma-senate / ma-house block. Each record is {seats: 1, members: [...]}, the
shape New Hampshire's and Maryland's named House districts take, carrying
`title`, the name as the General Court writes it, for the card. A weekly
GitHub Action (.github/workflows/update-ma-legislature-roster.yml) reruns this
script and opens a PR when a roster changes.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

malegislature.gov/Legislators/Members/Senate and /House are one table each, a
row per seat: first name and last name (linked to /Legislators/Profile/<id>),
District, Party ("Democrat", "Republican" or "Unenrolled"), Room (the member's
State House room), Phone Number and Email Address (at masenate.gov or
mahouse.gov). That day the Senate's held 40 members, every seat, and the
House's 157 members and three rows reading "Vacant" (1st Franklin, 16th and
17th Middlesex). A vacant row still prints the district office's room and
telephone; neither is carried.

THE TWO LISTS SPELL SOME NAMES DIFFERENTLY. TIGER writes a district of
several counties with hyphens ("Hampshire-Franklin-Worcester",
"Barnstable-Dukes-Nantucket") where the General Court writes commas and "and"
("Hampshire, Franklin and Worcester"), and keeps "and" in others ("Second
Plymouth and Norfolk"). A name is matched after replacing every comma and
every " and " with a hyphen on both sides; a list name that matches no
district the map draws stops the build.

WHAT IS READ. From each member: the name, district, party, State House room
and telephone, the e-mail address at the General Court's domains, and the
member's page. Nothing else is printed in the table.

ROBOTS. malegislature.gov/robots.txt was read on 2026-11-12: "User-agent: * /
Disallow:", everything allowed and no Crawl-delay. It is read through
scripts/robots_policy.py with the User-Agent the fetches send before the
first fetch, and a stated Crawl-delay is honoured.

Honesty: names are never guessed. A seat the General Court lists as vacant is
shown as vacant with the day it was first read so; a seat missing from its
list is shown as one the list names nobody for.

Usage:
    python3 ma/scripts/build_ma_legislature_roster.py [output_dir]
    python3 ma/scripts/build_ma_legislature_roster.py --save DIR [output_dir]
    python3 ma/scripts/build_ma_legislature_roster.py --offline DIR [output_dir]
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/ma/)"
PACE_SECONDS = 2.0
ATTEMPTS = 4
RETRY_SECONDS = 20.0
SITE = "https://malegislature.gov"
LISTS = {"S": SITE + "/Legislators/Members/Senate", "H": SITE + "/Legislators/Members/House"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")


def districts_of(geometry):
    """{name: 1} for every district the map's boundary file draws."""
    with open(os.path.join(DEFAULT_OUT_DIR, geometry), encoding="utf-8") as fh:
        return {f["properties"]["BASENAME"]: 1 for f in json.load(fh)["features"]}


# 40 of 40 senators and 157 of 160 representatives were listed on 2026-11-12.
CHAMBERS = {
    "S": {"out": "ma-senate-members.json", "label": "Senate",
          "districts": districts_of("ma-senate-districts.json"), "expected": 36,
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.9}},
    "H": {"out": "ma-house-members.json", "label": "House of Representatives",
          "districts": districts_of("ma-house-districts.json"), "expected": 144,
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.9}},
}

PARTIES = {"Democrat": "Democratic", "Democratic": "Democratic",
           "Republican": "Republican", "Unenrolled": "Unenrolled"}

ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
PROFILE_RE = re.compile(r'href="(/Legislators/Profile/[A-Za-z0-9_]+)"')
ROOM_RE = re.compile(r"^[0-9]{1,4}(-?[A-Z])?$|^B-?\d{1,3}$")
PHONE_RE = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@(masenate|mahouse)\.gov$", re.I)


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


def key(name):
    return re.sub(r"\s*,\s*|\s+and\s+", "-", name.strip()).lower()


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
        print("robots.txt %s: %s" % (urllib.parse.urlsplit(url).netloc, _GATE.allows(url)[1]),
              file=sys.stderr)
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


def load(chamber, offline, save):
    name = "%s.html" % ("senate" if chamber == "S" else "house")
    if offline:
        with open(os.path.join(offline, name), encoding="utf-8") as fh:
            return fh.read()
    body = fetch(LISTS[chamber])
    if save:
        os.makedirs(save, exist_ok=True)
        with open(os.path.join(save, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    return body


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def build_chamber(chamber, page, previous, today):
    cfg = CHAMBERS[chamber]
    by_key = {key(n): n for n in cfg["districts"]}
    if len(by_key) != len(cfg["districts"]):
        raise SystemExit("FAIL: two %s districts match one name" % cfg["label"])
    roster, notes = {}, []
    rows = [r for r in ROW_RE.findall(page) if TD_RE.search(r)]
    if len(rows) < len(cfg["districts"]) - 6:
        raise SystemExit("FAIL: the %s list held %d rows — its layout changed"
                         % (cfg["label"], len(rows)))
    for row in rows:
        tds = [clean(x) for x in TD_RE.findall(row)]
        vacant = "Vacant" in tds[:3]
        if vacant:
            # A vacant row has no photo cell: [star, picture, "Vacant", district, ...]
            listed_district = tds[tds.index("Vacant") + 1]
        else:
            if len(tds) < 9:
                raise SystemExit("FAIL: a %s row has %d cells" % (cfg["label"], len(tds)))
            first, last, listed_district, party, room, phone, email = tds[2:9]
        district = by_key.get(key(listed_district))
        if not district:
            raise SystemExit("FAIL: the %s list names %r, which is not a district the map "
                             "draws — read it before shipping" % (cfg["label"], listed_district))
        where = "%s %s" % (cfg["label"].split()[0], listed_district)
        if district in roster:
            raise SystemExit("FAIL: %s is listed twice" % where)
        if vacant:
            prev = previous.get(district) or {}
            roster[district] = {
                "title": listed_district, "seats": 1, "members": [], "vacant": True,
                "sourceUrl": LISTS[chamber],
                "asOf": (prev.get("asOf") if prev.get("vacant") else None) or today}
            notes.append("%s: listed as vacant" % where)
            continue
        name = re.sub(r"\s+", " ", "%s %s" % (first, last)).strip()
        if not first or not last or re.search(r"\d", name):
            raise SystemExit("FAIL: %s's row names %r" % (where, name))
        member = {"name": name}
        if party in PARTIES:
            member["party"] = PARTIES[party]
        elif party:
            member["party"] = party
            notes.append("%s: party printed as %r ships as printed" % (where, party))
        office = []
        if ROOM_RE.match(room):
            office.append("Room " + room)
        elif room:
            notes.append("%s: the room reads %r, not carried" % (where, room))
        if PHONE_RE.match(phone):
            office.append(phone)
        elif phone:
            notes.append("%s: the telephone reads %r, not carried" % (where, phone))
        if office:
            member["capitolOffice"] = office
        if EMAIL_RE.match(email):
            member["email"] = email
        elif email:
            notes.append("%s: an e-mail address off the General Court's domains was not "
                         "carried" % where)
        prof = PROFILE_RE.search(row)
        if prof:
            member["url"] = SITE + prof.group(1)
        roster[district] = {"title": listed_district, "seats": 1, "members": [member]}
    for district in cfg["districts"]:
        if district not in roster:
            prev = previous.get(district) or {}
            roster[district] = {
                "title": district, "seats": 1, "members": [],
                "asOf": (prev.get("asOf") if not prev.get("members") else None) or today}
            notes.append("%s %s: not listed" % (cfg["label"].split()[0], district))
    named = [m for rec in roster.values() for m in rec["members"]]
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
    return {d: roster[d] for d in sorted(roster)}, notes


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
    built = {}
    for chamber in ("S", "H"):
        built[chamber] = build_chamber(chamber, load(chamber, offline, save),
                                       previous_roster(out_dir, CHAMBERS[chamber]), today)
    os.makedirs(out_dir, exist_ok=True)
    for chamber, (roster, notes) in built.items():
        cfg = CHAMBERS[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for rec in roster.values() for m in rec["members"]]
        print("Wrote %s (%d of %d seats named, %d vacant, %d with a party, %d with an "
              "e-mail address, %d with a State House room or telephone)"
              % (out_path, len(named), len(cfg["districts"]),
                 sum(1 for r in roster.values() if r.get("vacant")),
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("capitolOffice"))), file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
