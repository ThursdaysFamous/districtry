#!/usr/bin/env python3
"""
Build the Kentucky Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from the General
Assembly's own site at legislature.ky.gov, so the ky-senate / ky-house cards
join a small roster instead of naming nobody.

index.html's ky-senate / ky-house layers fetch data/app/ky-senate-members.json
and ky-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
capitolOffice, phone?, phonesExtra?, url}}, or a record naming nobody). A
weekly GitHub Action (.github/workflows/update-ky-legislature-roster.yml)
reruns it and opens a PR when a roster changes, so officeholder data gets a
look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-14.

legislature.ky.gov/Legislators/senate and /Legislators/house-of-representatives
each print one card per member: the name, the party ("Republican" or
"Democrat"), the district, and a link to the member's own page,
/Legislators/Pages/Legislator-Profile.aspx?DistrictNumber=N (a senator's N is
100 plus the district). That day the lists held 38 senators for 38 districts
(32 Republican, 6 Democratic) and 100 representatives for 100 (80 and 20).
Kentucky elected half its Senate and its whole House on 3 November 2026, and
those terms begin on 1 January 2027; the lists name the sitting members.

Each member's own page prints, under headings of its own: Home City, Mailing
Address, Legislative Address, Phone Number(s) (each number labelled, "LRC:
502-564-8100", "Home: ...", "Work: ...") and Email.

WHAT IS READ FROM A MEMBER'S PAGE, AND WHAT IS NOT.

  * LEGISLATIVE ADDRESS is carried as the Capitol office, and only when its
    last line is in Frankfort. A member who gives another address there gets
    no office lines; the run says which district, never the lines.
  * MAILING ADDRESS AND HOME CITY ARE NEVER READ. Many members give a home
    address as their mailing address, and a home address never ships and
    never appears in a log.
  * THE TELEPHONES SHIP WITH THE PAGE'S OWN LABELS, under the fleet's rule of
    2026-10-17 that a number a government source prints beside one official
    ships on that official. The number labelled LRC is the Legislative
    Research Commission's line and goes under the Capitol office. Every other
    number rides the member's own row with its label ("home 502-555-0100"),
    the first as `phone` and the rest as `phonesExtra`. A number printed for
    two or more members is an office's and rides no member's row. A number
    labelled as a fax is not carried.
  * EMAIL is carried as printed.

The list and the member's own page must agree about the district and the
member's name, or the build stops.

ROBOTS. legislature.ky.gov/robots.txt (190 bytes) was read on 2026-11-14 with
the client the fetches send: no rule in its one binding group matches either
list or the member pages, and it states no Crawl-delay. The 138 member pages
are paced at one request a second anyway. It is read through
scripts/robots_policy.py before the first fetch.

Honesty: names are never guessed. A seat with no sitting member listed gets a
record naming nobody, dated; two members for one seat stop the build.

Usage:
    python3 ky/scripts/build_ky_legislature_roster.py [output_dir]
    python3 ky/scripts/build_ky_legislature_roster.py --save DIR [output_dir]
    python3 ky/scripts/build_ky_legislature_roster.py --offline DIR [output_dir]
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/ky/)"
ATTEMPTS = 4
RETRY_SECONDS = 20.0
PAUSE_SECONDS = 1.0
SITE = "https://legislature.ky.gov"
PROFILE = SITE + "/Legislators/Pages/Legislator-Profile.aspx?DistrictNumber=%d"

# 38 of 38 senators and 100 of 100 representatives were seated on 2026-11-14.
# `offset` is what the site adds to a district to number a member's page.
CHAMBERS = {
    "S": {"out": "ky-senate-members.json", "label": "Senate", "seats": 38,
          "expected": 34, "title": "Senator", "offset": 100,
          "list": SITE + "/Legislators/senate",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.9}},
    "H": {"out": "ky-house-members.json", "label": "House of Representatives",
          "seats": 100, "expected": 90, "title": "Representative", "offset": 0,
          "list": SITE + "/Legislators/house-of-representatives",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.9}},
}

PARTIES = {"Democrat": "Democratic", "Democratic": "Democratic",
           "Republican": "Republican"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

CARD_RE = re.compile(
    r'<a href="/Legislators/Pages/Legislator-Profile\.aspx\?DistrictNumber=(\d+)"'
    r'[^>]*class="Legislator-Card[^"]*"[^>]*>.*?<h3>(.*?)</h3>\s*<small>(.*?)</small>'
    r'\s*<p>\s*District:\s*(\d+)\s*</p>', re.S)
SECTION_RE = re.compile(r'<p class="title">(.*?)</p>(.*?)(?=<p class="title">|</div>)', re.S)
CIRCLE_RE = re.compile(r'<h3>District:</h3>\s*<div class="circle">\s*<h3>\s*(\d+)\s*</h3>')
PHONE_RE = re.compile(r"^\(?\d{3}\)?[ .-]?\d{3}[ .-]\d{4}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
FRANKFORT_RE = re.compile(r"^Frankfort,? KY 406\d\d(-\d{4})?$")


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


def digits(number):
    return re.sub(r"\D", "", number)


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
    ok, why = _GATE.allows(url)
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


class Pages(object):
    """The list and member pages, from the site or from a saved directory."""

    def __init__(self, offline, save):
        self.offline, self.save = offline, save
        self.fetched = 0

    def get(self, name, url):
        if self.offline:
            with open(os.path.join(self.offline, name), encoding="utf-8") as fh:
                return fh.read()
        if self.fetched:
            time.sleep(PAUSE_SECONDS)
        self.fetched += 1
        body = fetch(url)
        if self.save:
            os.makedirs(self.save, exist_ok=True)
            with open(os.path.join(self.save, name), "w", encoding="utf-8") as fh:
                fh.write(body)
        return body


def surname_words(name):
    return set(re.findall(r"[a-z]+", name.lower()))


def read_profile(body, where, listed_name, district, notes):
    """The member's own page -> (member fields, [(label, number)] of the
    numbers that are the member's own). Only the Legislative Address, the
    telephone numbers and the e-mail address are read."""
    circle = CIRCLE_RE.search(body)
    if not circle or int(circle.group(1)) != district:
        raise SystemExit("FAIL: %s's own page names district %s"
                         % (where, circle.group(1) if circle else "nothing"))
    words = surname_words(listed_name)
    if not words or not all(w in body.lower() for w in words):
        raise SystemExit("FAIL: %s's own page does not name %s" % (where, listed_name))
    sections = {}
    for title, rest in SECTION_RE.findall(body):
        sections.setdefault(clean(title), rest)
    fields, own = {}, []
    office = []
    block = sections.get("Legislative Address")
    if block:
        address = re.search(r"<address>(.*?)</address>", block, re.S)
        lines = [clean(part) for part in re.split(r"<br\s*/?>", address.group(1))] if address else []
        lines = [line for line in lines if line]
        if lines and FRANKFORT_RE.match(lines[-1]):
            office = lines
        elif lines:
            notes.append("%s: the Legislative Address is not in Frankfort, not carried" % where)
    # One <p> holds every number, one per line: "LRC: ...<br>Work: ...<br>
    # Work: ... (fax)". Each line is one entry; a fax line is not carried.
    entries = []
    for para in re.findall(r"<p>(.*?)</p>", sections.get("Phone Number(s)") or "", re.S):
        entries.extend(clean(part) for part in re.split(r"<br\s*/?>", para))
    for entry in entries:
        if not entry or re.search(r"fax", entry, re.I):
            continue
        label, _, number = entry.rpartition(":")
        label, number = label.strip(), number.strip()
        if not PHONE_RE.match(number):
            notes.append("%s: a telephone entry is not one whole number, not carried" % where)
            continue
        if label.upper() == "LRC":
            office.append(number)
        else:
            own.append((label.lower(), number))
    if office:
        fields["capitolOffice"] = office
    email = clean(sections.get("Email") or "")
    if EMAIL_RE.match(email):
        fields["email"] = email
    elif email:
        notes.append("%s: the e-mail entry is not one address, not carried" % where)
    return fields, own


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def build(pages, previous, today):
    seats = {"S": {}, "H": {}}
    notes = {"S": [], "H": []}
    own_numbers = {}
    for chamber, cfg in CHAMBERS.items():
        short = cfg["label"].split()[0]
        cards = CARD_RE.findall(pages.get("%s-list.html" % short.lower(), cfg["list"]))
        if len(cards) < cfg["expected"]:
            raise SystemExit("FAIL: the %s list held %d member cards — its layout changed"
                             % (cfg["label"], len(cards)))
        for page_number, name, party, district in cards:
            district, page_number = int(district), int(page_number)
            where = "%s %d" % (short, district)
            if not 1 <= district <= cfg["seats"]:
                raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                                 % (where, cfg["seats"]))
            if page_number != district + cfg["offset"]:
                raise SystemExit("FAIL: %s links member page %d, not the %d the site "
                                 "numbers that seat" % (where, page_number,
                                                        district + cfg["offset"]))
            if district in seats[chamber]:
                raise SystemExit("FAIL: %s is listed twice" % where)
            name = clean(name)
            if not name or re.search(r"\d", name):
                raise SystemExit("FAIL: %s's card names %r" % (where, name))
            member = {"name": name}
            party = clean(party)
            if party in PARTIES:
                member["party"] = PARTIES[party]
            elif party:
                member["party"] = party
                notes[chamber].append("%s: party printed as %r ships as printed" % (where, party))
            url = PROFILE % page_number
            fields, own = read_profile(
                pages.get("%s-%d.html" % (short.lower(), district), url),
                where, name, district, notes[chamber])
            member.update(fields)
            member["url"] = url
            member["_own"] = own
            for _, number in own:
                own_numbers.setdefault(digits(number), set()).add(where)
            seats[chamber][district] = member
    shared = {d for d, who in own_numbers.items() if len(who) > 1}
    for d in sorted(shared):
        print("NOTE: a number is printed for %s, so it is an office's and ships on "
              "no member's row" % " and ".join(sorted(own_numbers[d])), file=sys.stderr)
    out = {}
    for chamber, cfg in CHAMBERS.items():
        for member in seats[chamber].values():
            seen, numbers = set(), []
            for label, number in member.pop("_own"):
                if digits(number) in shared or digits(number) in seen:
                    continue
                seen.add(digits(number))
                numbers.append(("%s %s" % (label, number)).strip())
            if numbers:
                member["phone"] = numbers[0]
            if len(numbers) > 1:
                member["phonesExtra"] = numbers[1:]
        for district in range(1, cfg["seats"] + 1):
            if district not in seats[chamber]:
                prev = previous[chamber].get(str(district)) or {}
                seats[chamber][district] = {
                    "asOf": (prev.get("asOf") if not prev.get("name") else None) or today}
                notes[chamber].append("%s %d: no sitting member listed"
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
    previous = {c: previous_roster(out_dir, cfg) for c, cfg in CHAMBERS.items()}
    built, notes = build(Pages(offline, save), previous, today)
    os.makedirs(out_dir, exist_ok=True)
    for chamber in ("S", "H"):
        cfg, roster = CHAMBERS[chamber], built[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for m in roster.values() if m.get("name")]
        print("Wrote %s (%d of %d seats named, %d with a party, %d with an e-mail "
              "address, %d with a Capitol office, %d with a number of their own)"
              % (out_path, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("capitolOffice")),
                 sum(1 for m in named if m.get("phone"))), file=sys.stderr)
        for note in notes[chamber]:
            print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
