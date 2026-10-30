#!/usr/bin/env python3
"""
Build the Georgia Senate and Georgia House rosters (district -> current
officeholder) as same-origin app-data files, from the General Assembly's OWN
member data, so the ga-senate / ga-house cards join a small roster instead of
reaching a third-party host at click time.

index.html's ga-senate / ga-house layers fetch data/app/ga-senate-members.json
and ga-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
capitolOffice, url}}, or a vacancy record). A weekly GitHub Action
(.github/workflows/update-ga-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-10-29. The General Assembly's site,
www.legis.ga.gov, is one page whose script reads every member from the
assembly's own data service at www.legis.ga.gov/api/. That service answers
401 until a visitor presents a token, and the page's script obtains one for
every visitor from /api/authentication/token, with a key it computes from a
fixed string in the same script and the current time in milliseconds. Reading
the service with that token is reading the page the way it is published to
every visitor (Adam's rule of 2026-10-06: a key a page hands every anonymous
visitor is page configuration, not a credential). Nothing here signs in.

THE KEY'S INGREDIENTS ARE READ FROM THE PAGE'S OWN SCRIPT ON EVERY RUN, never
copied into this file: the page's main script is named in its HTML, and the
script carries the fixed prefix, the `obscureKey` and the word passed to
getKey. If the page changes how it builds the key, the regular expressions
below stop matching and the build stops, saying so, rather than sending a
guessed key.

WHAT IS READ. /api/sessions names the current regular session (id 1033 on
2026-10-29, "2025-2026 Regular Session"). /api/members/list/<session>?chamber=
2 (Senate) and =1 (House) list every member who sat in it, with the district
and the day a member left the seat (dateVacated); a member with a dateVacated
no longer holds the seat. On 2026-10-29 the Senate list held 61 names for 56
seats and the House 186 for 180, every seat with exactly one sitting member.
Then each sitting member's /api/members/detail/<id> gives the name the page
displays, the party, the Capitol office's room and telephone, and the
member's e-mail address. The party is a number the script names itself
(0 Democrat, 1 Republican, 2 Independent, 3 Other), read here from the same
enum.

WHAT IS NEVER READ OR SHIPPED. The detail record also carries a home
telephone and a cell telephone for some members, and a district address. The
page's own script never displays the home or cell telephone (neither field
name occurs in any of its scripts, read 2026-10-29), so they are not
something the General Assembly prints beside a member, and they do not ship.
The district address is displayed, but on 2026-10-29 96 of the 236 were post
office boxes and others plainly homes, and the card pins a district office on
the map, which a post office box or a home would misplace; none ships until
each is read as an office (recorded in ga/WATCH.md). The fax number, the
occupation, the committees and the biography are not read either.

THE CARD LINKS THE MEMBER'S OWN PAGE on www.legis.ga.gov
(members/senate/<id> or members/house/<id>), whose robots.txt answers with
the page's own HTML rather than a robots file, which RFC 9309 reads as no
policy: allow all.

Honesty: names are never guessed. A seat with no sitting member gets a
vacancy record naming the General Assembly's own list; a seat with two
sitting members stops the build.

Usage:
    python3 ga/scripts/build_ga_legislature_roster.py [output_dir]
    python3 ga/scripts/build_ga_legislature_roster.py --save DIR [output_dir]
    python3 ga/scripts/build_ga_legislature_roster.py --offline DIR [output_dir]

--save writes every file fetched into DIR (sessions.json, list-<chamber>.json
and detail/<id>.json), reading back any it already holds; --offline reads them
back instead of fetching, for building and testing without the network.
"""

import datetime
import hashlib
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/ga/)"
# Every host is paced at one second even where it states no delay.
MIN_PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

SITE = "https://www.legis.ga.gov/"
API = SITE + "api/"
MEMBER_PAGE = SITE + "members/%s/%d"
DIRECTORY = {"S": SITE + "members/senate", "H": SITE + "members/house"}

# The page's main script, named in its HTML.
MAIN_SCRIPT_RE = re.compile(r'<script src="(main\.[0-9a-f]+\.js)"')
# getKey(word, ms) = SHA512(prefix + obscureKey + word + ms), as the script
# writes it on 2026-10-29:
#   getKey=function(e,t){return Vt.SHA512("QFpCwKfd7f"+i.a.obscureKey+e+t)}
GETKEY_RE = re.compile(
    r'getKey=function\((\w),(\w)\)\{return \w+\.SHA512\("([^"]+)"\+\w+\.\w+\.obscureKey\+\1\+\2\)\}')
OBSCURE_RE = re.compile(r'obscureKey:"([^"]+)"')
WORD_RE = re.compile(r'append\("key",this\.getKey\("([^"]+)",e\)\)')

# Floors catch a truncated list or a layout change while tolerating real
# vacancies: every one of the 56 senators and 180 representatives was named on
# 2026-10-29.
CHAMBERS = {
    "S": {"out": "ga-senate-members.json", "label": "Senate", "seats": 56,
          "expected": 50, "code": 2, "slug": "senate",
          "body": "The Georgia State Senate"},
    "H": {"out": "ga-house-members.json", "label": "House", "seats": 180,
          "expected": 165, "code": 1, "slug": "house",
          "body": "The Georgia House of Representatives"},
}
# A field nearly every named member carried on 2026-10-29. One going missing
# is the Brown County shape: the row count holds and the contact goes.
MIN_FIELD_SHARE = 0.9

# The script's own enum (0 Democrat, 1 Republican, 2 Independent, 3 Other),
# written with the party names the fleet's other rosters use.
PARTY_NAMES = {0: "Democratic", 1: "Republican", 2: "Independent"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_DIGITS_RE = re.compile(r"^\d{10}$")
PHONE_RE = re.compile(r"^\d{3}-\d{3}-\d{4}$")

_SESSION = None
_GATE = None
_PACER = None
_LAST = {}
_TOKEN = None


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
    return _SESSION


def gate():
    global _GATE, _PACER
    if _GATE is None:
        _GATE = RobotsGate(session(), USER_AGENT)
        _PACER = HostPacer(_GATE)
    return _GATE


def fetch(url, headers=None, as_json=False):
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
                resp = session().get(url, headers=headers or {}, timeout=120)
            _LAST[host] = time.time()
            resp.raise_for_status()
            if as_json:
                return resp.json()
            resp.encoding = "utf-8"
            return resp.text
        except (requests.RequestException, ValueError) as exc:  # reset, timeout, 5xx, bad JSON
            _LAST[host] = time.time()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


def token():
    """The token the page's script obtains for every visitor."""
    global _TOKEN
    if _TOKEN is not None:
        return _TOKEN
    page = fetch(SITE)
    m = MAIN_SCRIPT_RE.search(page)
    if not m:
        raise SystemExit("FAIL: www.legis.ga.gov no longer names its main script — "
                         "the page changed, so the key cannot be read")
    script = fetch(SITE + m.group(1))
    getkey, obscure, word = (GETKEY_RE.search(script), OBSCURE_RE.search(script),
                             WORD_RE.search(script))
    if not (getkey and obscure and word):
        raise SystemExit("FAIL: the page's script no longer builds its key the way this "
                         "script reads it (getKey %s, obscureKey %s, word %s) — read the "
                         "script again before changing anything"
                         % (bool(getkey), bool(obscure), bool(word)))
    ms = str(int(time.time() * 1000))
    key = hashlib.sha512((getkey.group(3) + obscure.group(1) + word.group(1) + ms)
                         .encode("utf-8")).hexdigest()
    got = fetch(API + "authentication/token?" + urllib.parse.urlencode({"key": key, "ms": ms}),
                headers={"Accept": "application/json"}, as_json=True)
    if not isinstance(got, str) or len(got) < 20:
        raise SystemExit("FAIL: the token service answered %r, not a token" % (got,))
    _TOKEN = got
    return _TOKEN


def api(path):
    return fetch(API + path, headers={"Accept": "application/json",
                                      "Authorization": "Bearer " + token()},
                 as_json=True)


class Pages:
    """Fetch, save or replay the files one run reads."""

    def __init__(self, offline=None, save=None):
        self.offline, self.save = offline, save

    def get(self, name, path):
        source = self.offline or (self.save if self.save and
                                  os.path.exists(os.path.join(self.save, name)) else None)
        if source:
            # --offline, or a file an interrupted --save run already wrote.
            with open(os.path.join(source, name), encoding="utf-8") as fh:
                return json.load(fh)
        body = api(path)
        if self.save:
            out = os.path.join(self.save, name)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(body, fh, ensure_ascii=False, indent=1)
        return body


def current_session(sessions):
    """The current regular session's id, and its description."""
    regular = [s for s in sessions or [] if s.get("isCurrent") and s.get("type") == 0]
    if len(regular) != 1:
        raise SystemExit("FAIL: /api/sessions marks %d current regular sessions, not one"
                         % len(regular))
    return int(regular[0]["id"]), str(regular[0].get("description") or "")


def phone_text(raw):
    digits = re.sub(r"\D", "", str(raw or ""))
    if not digits:
        return None
    if not PHONE_DIGITS_RE.match(digits):
        return False
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def capitol_lines(addr, where, notes):
    """The Capitol office as the page prints it: room and building, city line,
    telephone. No fax."""
    if not isinstance(addr, dict):
        return []
    lines = []
    for key in ("address1", "address2"):
        v = (addr.get(key) or "").strip()
        if v:
            lines.append(v)
    city, state, zip_ = [(addr.get(k) or "").strip() for k in ("city", "state", "zip")]
    if city or state or zip_:
        lines.append(("%s, %s %s" % (city, state, zip_)).strip().strip(","))
    phone = phone_text(addr.get("phone"))
    if phone is False:
        notes.append("%s: the Capitol telephone is not one ten-digit number, so it was "
                     "not carried" % where)
    elif phone:
        lines.append(phone)
    return lines


def plain_email(raw, where, notes):
    raw = (raw or "").strip()
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


def vacancy(chamber, previous, district, today):
    cfg = CHAMBERS[chamber]
    prev = previous.get(str(district)) or {}
    return {
        "vacant": True,
        "vacantWhy": "%s's own member list names nobody sitting in this seat."
                     % cfg["body"],
        "sourceUrl": DIRECTORY[chamber],
        # The day the chamber was first read saying so, kept across runs.
        "asOf": (prev.get("asOf") if prev.get("vacant") else None) or today,
    }


def build_chamber(chamber, pages, sid, previous, today):
    cfg = CHAMBERS[chamber]
    listing = pages.get("list-%s.json" % cfg["slug"],
                        "members/list/%d?chamber=%d" % (sid, cfg["code"]))
    if not isinstance(listing, list) or not listing:
        raise SystemExit("FAIL: the %s list is empty or not a list" % cfg["label"])
    sitting = {}
    for row in listing:
        district = row.get("districtNumber")
        if not isinstance(district, int) or not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: a %s list row names district %r" % (cfg["label"], district))
        if row.get("sessionId") not in (None, sid):
            raise SystemExit("FAIL: a %s list row belongs to session %r" % (cfg["label"],
                                                                          row.get("sessionId")))
        if row.get("dateVacated"):
            continue
        if district in sitting:
            raise SystemExit("FAIL: the %s list names two sitting members for District %d"
                             % (cfg["label"], district))
        sitting[district] = row
    seats, notes = {}, []
    for district in range(1, cfg["seats"] + 1):
        where = "%s %d" % (cfg["label"], district)
        row = sitting.get(district)
        if row is None:
            seats[district] = vacancy(chamber, previous, district, today)
            notes.append("%s: vacant" % where)
            continue
        mid = int(row["id"])
        detail = pages.get("detail/%d.json" % mid,
                           "members/detail/%d?session=%d&chamber=%d" % (mid, sid, cfg["code"]))
        if not isinstance(detail, dict):
            raise SystemExit("FAIL: %s's detail record is not an object" % where)
        if detail.get("districtNumber") != district or detail.get("chamber") != cfg["code"]:
            raise SystemExit("FAIL: %s's detail record says %s District %r"
                             % (where, detail.get("chamber"), detail.get("districtNumber")))
        if detail.get("dateVacated"):
            raise SystemExit("FAIL: %s's list row is sitting and its detail record says it "
                             "left on %s" % (where, detail["dateVacated"]))
        name = (detail.get("displayName") or row.get("fullName") or "").strip()
        if not name:
            raise SystemExit("FAIL: %s's sitting member has no name" % where)
        member = {"name": re.sub(r"\s+", " ", name)}
        party = detail.get("party", row.get("party"))
        if party in PARTY_NAMES:
            member["party"] = PARTY_NAMES[party]
        elif party is not None:
            notes.append("%s: party code %r is not one this script names, so no party "
                         "shipped" % (where, party))
        email = plain_email(detail.get("email") or
                            (detail.get("capitolAddress") or {}).get("email"), where, notes)
        if email:
            member["email"] = email
        office = capitol_lines(detail.get("capitolAddress"), where, notes)
        if office:
            member["capitolOffice"] = office
        member["url"] = MEMBER_PAGE % (cfg["slug"], mid)
        seats[district] = member
    return seats, notes


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
    sid, description = current_session(pages.get("sessions.json", "sessions"))
    print("session %d: %s" % (sid, description), file=sys.stderr)
    built = {}
    for chamber in ("S", "H"):
        previous = previous_roster(out_dir, CHAMBERS[chamber])
        seats, notes = build_chamber(chamber, pages, sid, previous, today)
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
