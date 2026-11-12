#!/usr/bin/env python3
"""
Build the Ohio Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from each chamber's OWN
site (ohiosenate.gov and ohiohouse.gov), so the oh-senate / oh-house cards join
a small roster instead of reaching a third-party host at click time.

index.html's oh-senate / oh-house layers fetch data/app/oh-senate-members.json
and oh-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party,
capitolOffice, url}}, or a vacancy record). A weekly GitHub Action
(.github/workflows/update-oh-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-11.

Both chambers' lists showed the 136th General Assembly that day; the members
elected on 3 November 2026 take office in January 2027.

The Senate's member list, ohiosenate.gov/senators (which redirects to
/members/directory), carries one entry per senator: the senator's name, a
line "District <n> | <R or D>", and a link to the senator's page
(/members/<slug>). 32 of the 33 seats were named that day; District
13's entry read "Vacant". Each senator's
page names the senator in its member-name heading, prints the district, and
carries an Address block (the Statehouse or Senate Building, "1 Capitol
Square", the floor and the room; 7 of the 32 also print "Columbus, Ohio
43215") and a Phone block. No e-mail address is
printed; the senator's contact page is a form.

The House's member list, ohiohouse.gov/members (which redirects to
/members/directory), carries one entry per member: the name, a line
"District <n> | <R or D>", and a link to the member's page (/members/<slug>).
99 of the 99 seats were named that day. Each member's page prints the name
in its title ("Representative <name> - District <n>"), the district and the
party letter, and an office block (77 South High Street, the floor, and
"Columbus, OH 43215"; 8 of the 99 stop at the floor) followed by "Phone:
(614) ..." and a fax line, which is not carried. Two members' pages printed
no office at all that day, and their cards carry none. No e-mail address is printed; the member's contact page is a
form.

WHAT IS READ, AND WHAT IS NEVER READ. From each member: the name, the
district, the party letter, the Columbus office address and its telephone as
printed, and the member's own page. Home towns, district offices,
biographies, fax lines and staff are never read. Every office address must
end in a Columbus ZIP code (4321x) or carry the street line of the
Statehouse ("1 Capitol Square") or the Riffe Center ("77 South High
Street"), or it is not carried.

ROBOTS. Both hosts' robots.txt are read through scripts/robots_policy.py with
the User-Agent the fetches send, before the first fetch, and a stated
Crawl-delay is honoured by its HostPacer. Read 2026-11-11: both files are
"User-agent: * / Disallow:" (everything allowed, no Crawl-delay). The Senate
is paced at one request a second and the House at one every two seconds
regardless.

Honesty: names are never guessed. A seat the chamber lists as vacant, or that
is missing from its list, gets a vacancy record naming that list; a seat
carried twice stops the build.

Usage:
    python3 oh/scripts/build_oh_legislature_roster.py [output_dir]
    python3 oh/scripts/build_oh_legislature_roster.py --save DIR [output_dir]
    python3 oh/scripts/build_oh_legislature_roster.py --offline DIR [output_dir]

--save writes every page fetched into DIR (senate-list.html, senate/<slug>.html,
house-list.html and house/<slug>.html), reading back any it already holds;
--offline reads them back instead of fetching, for building and testing
without the network.
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/oh/)"
MIN_PACE_SECONDS = 1.0
HOST_PACE_SECONDS = {"www.ohiohouse.gov": 2.0}
ATTEMPTS = 4
RETRY_SECONDS = 20.0

SENATE_SITE = "https://www.ohiosenate.gov"
HOUSE_SITE = "https://www.ohiohouse.gov"
LISTS = {"S": SENATE_SITE + "/members/directory",
         "H": HOUSE_SITE + "/members/directory"}

# Floors catch a truncated list or a layout change while tolerating real
# vacancies: 33 of 33 senators and 99 of 99 representatives were named on
# 2026-11-11.
CHAMBERS = {
    "S": {"out": "oh-senate-members.json", "label": "Senate", "seats": 33,
          "expected": 29, "of": "the Ohio Senate", "site": SENATE_SITE,
          # The share of named members carrying each field, floored below what
          # 2026-11-11 measured. A field falling under its floor is the Brown
          # County shape: the row count holds and the contact goes.
          "fields": {"party": 0.9, "capitolOffice": 0.9}},
    "H": {"out": "oh-house-members.json", "label": "House of Representatives",
          "seats": 99, "expected": 89, "of": "the Ohio House of Representatives",
          "site": HOUSE_SITE,
          "fields": {"party": 0.9, "capitolOffice": 0.9}},
}

PARTY_LETTERS = {"R": "Republican", "D": "Democratic"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

PHONE_RE = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")
CAPITOL_ZIP_RE = re.compile(r"\bColumbus,? (?:Ohio|OH) 4321\d(-\d{4})?$")
# The Statehouse and the Senate Building share one street address, and the
# House's offices are in the Riffe Center at 77 South High Street. Measured
# 2026-11-11, 25 of the 32 senators' pages stop their address at the room
# number ("Senate Building / 1 Capitol Square / Ground Floor / 038") and 8 of
# the 99 House members' pages at the floor ("77 South High Street / 13th
# Floor"), printing no city line. A block carrying one of these street lines
# is the Columbus office as printed and is carried without a city line being
# added.
CAPITOL_STREETS = ("1 Capitol Square", "77 South High Street")
# The Senate's pages print the room as a bare number on the line after the
# floor ("First Floor / 138"): 31 of the 32 senators' pages, measured
# 2026-11-11 (the other prints "SH-303", which is carried as printed). A bare
# number on a card reads as nothing, so that one line is written "Room 138",
# which is how the Senate's building numbers its offices; no other line is
# changed.
ROOM_NUMBER_RE = re.compile(r"^\d{2,4}$")

# Both lists: one media box per member, its link, the name line and the
# "District <n> | <letter>" line.
LIST_BOX_RE = re.compile(
    r'<div class="media-container media-container-portrait[^"]*">\s*'
    r'<a target="_self"\s+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
CAPTION_RE = re.compile(r'media-overlay-caption-text-line-(\d)">(.*?)</div>\s*(?=<div|$)', re.S)
DISTRICT_PARTY_RE = re.compile(r"^District (\d+)\s*\|?\s*([A-Z])?$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

SENATE_NAME_RE = re.compile(r'<h1 class="member-name">(.*?)</h1>', re.S)
SENATE_DISTRICT_RE = re.compile(r'<div class="member-district">\s*District (\d+)\s*</div>')
INFO_MODULE_RE = re.compile(
    r"<div class='member-info-bar-label'>(.*?)</div>\s*"
    r"<div class='member-info-bar-value'>(.*?)</div>\s*</div>", re.S)

HOUSE_TITLE_RE = re.compile(r"<title>\s*Representative (.*?) - District (\d+) \|", re.S)
HOUSE_PARTY_RE = re.compile(r'<div class="member-info-box-party">\s*<span>([A-Z])</span>')
# The unlabelled office module: its address value, then the telephone.
HOUSE_OFFICE_RE = re.compile(
    r"<div class='member-info-bar-module'>\s*<div>\s*"
    r"<div class='member-info-bar-value'>(.*?)</div>\s*</div>\s*"
    r"<div>\s*<div class='member-info-bar-value'>Phone:\s*([^<]*)</div>", re.S)

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
        wait = HOST_PACE_SECONDS.get(host, MIN_PACE_SECONDS) - (time.time() - _LAST[host])
        if wait > 0:
            time.sleep(wait)
        try:
            with _PACER.hold(url):
                resp = session().get(url, timeout=45)
            _LAST[host] = time.time()
            resp.raise_for_status()
            # Both sites declare UTF-8.
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as exc:  # reset, timeout, 5xx
            _LAST[host] = time.time()
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                session().close()  # a fresh connection on the next attempt
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


def address_lines(block):
    """The lines of a printed address block, split on its line breaks and on
    the <div> the House wraps its street line in."""
    parts = re.split(r"<br\s*/?>|</div>", block)
    return [clean(p) for p in parts if clean(p)]


def columbus_office(lines, phone, where, notes):
    """The office address as printed, which must end at the line carrying a
    Columbus ZIP code or, where no city line is printed, carry the street
    line of the Statehouse or the Riffe Center; then its telephone."""
    ends = [i for i, text in enumerate(lines) if CAPITOL_ZIP_RE.search(text)]
    if not ends and any(street in lines for street in CAPITOL_STREETS):
        ends = [len(lines) - 1]
    if not ends:
        notes.append("%s: the office address reads %r, which carries neither a "
                     "Columbus ZIP code nor a Capitol street line, so it was "
                     "not carried" % (where, lines))
        return []
    office = lines[:ends[-1] + 1]
    office = ["Room " + text if ROOM_NUMBER_RE.match(text) and i > 0
              and office[i - 1].endswith("Floor") else text
              for i, text in enumerate(office)]
    if len(lines) > ends[-1] + 1:
        notes.append("%s: %d line(s) after the office address were not carried"
                     % (where, len(lines) - ends[-1] - 1))
    phone = clean(phone)
    if PHONE_RE.match(phone):
        office.append(phone)
    elif phone:
        notes.append("%s: the office telephone reads %r, not carried" % (where, phone))
    else:
        notes.append("%s: no office telephone printed" % where)
    return office


def party_of(letter, where, notes):
    if letter in PARTY_LETTERS:
        return PARTY_LETTERS[letter]
    if letter:
        notes.append("%s: party printed as %r ships as printed" % (where, letter))
        return letter
    notes.append("%s: no party printed" % where)
    return None


def read_list(page, chamber):
    """[(slug, name, district, letter)] from a chamber's directory page."""
    cfg = CHAMBERS[chamber]
    out = []
    for href, body in LIST_BOX_RE.findall(page):
        slug = href.rstrip("/").split("/")[-1]
        if not SLUG_RE.match(slug):
            raise SystemExit("FAIL: a %s list entry links %r, not a member page"
                             % (cfg["label"], href))
        lines = {}
        for n, text in CAPTION_RE.findall(body):
            lines[n] = clean(text.replace("&nbsp;", " "))
        name, info = lines.get("1", ""), lines.get("2", "")
        m = DISTRICT_PARTY_RE.match(info)
        if not name or not m:
            raise SystemExit("FAIL: a %s list entry reads %r / %r, not a name and "
                             "'District <n> | <party>'" % (cfg["label"], name, info))
        out.append((slug, name, int(m.group(1)), m.group(2)))
    return out


def surname_in(listed, printed):
    words = [w for w in re.split(r"[\s,]+", listed) if w]
    surname = words[-1].lower()
    if surname.rstrip(".") in ("jr", "sr", "ii", "iii", "iv") and len(words) > 1:
        surname = words[-2].lower()
    return surname in printed.lower()


def build_chamber(chamber, pages, previous, today):
    cfg = CHAMBERS[chamber]
    list_url = LISTS[chamber]
    key = "senate" if chamber == "S" else "house"
    entries = read_list(pages.get("%s-list.html" % key, list_url), chamber)
    if len(entries) < cfg["seats"] - 3:
        raise SystemExit("FAIL: the %s member list yielded %d entries — its layout "
                         "changed" % (cfg["label"], len(entries)))
    seats, notes = {}, []
    for slug, listed, district, letter in entries:
        where = "%s %d" % (cfg["label"].split()[0], district)
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats:
            raise SystemExit("FAIL: %s is listed twice" % where)
        if listed.lower() == "vacant":
            seats[district] = vacancy(
                "The member list of %s lists this seat as vacant." % cfg["of"],
                list_url, previous, district, today)
            notes.append("%s: listed as vacant" % where)
            continue
        url = "%s/members/%s" % (cfg["site"], slug)
        page = pages.get("%s/%s.html" % (key, slug), url)
        if chamber == "S":
            named = SENATE_NAME_RE.search(page)
            printed_district = SENATE_DISTRICT_RE.search(page)
            name = clean(named.group(1)) if named else ""
            page_district = int(printed_district.group(1)) if printed_district else None
            page_letter = letter
        else:
            title = HOUSE_TITLE_RE.search(page)
            name = clean(title.group(1)) if title else ""
            page_district = int(title.group(2)) if title else None
            party_box = HOUSE_PARTY_RE.search(page)
            page_letter = party_box.group(1) if party_box else None
        if not name:
            raise SystemExit("FAIL: %s's page does not name its member" % where)
        if page_district != district:
            raise SystemExit("FAIL: %s's page names District %s" % (where, page_district))
        if not surname_in(listed, name):
            raise SystemExit("FAIL: %s's page names %r, which the list (%r) does not"
                             % (where, name, listed))
        if letter and page_letter and letter != page_letter:
            raise SystemExit("FAIL: %s's page prints party %r and the list %r"
                             % (where, page_letter, letter))
        member = {"name": name}
        party = party_of(letter or page_letter, where, notes)
        if party:
            member["party"] = party
        if chamber == "S":
            modules = {clean(label): value for label, value in INFO_MODULE_RE.findall(page)}
            address = modules.get("Address")
            if address:
                office = columbus_office(address_lines(address), modules.get("Phone", ""),
                                         where, notes)
                if office:
                    member["capitolOffice"] = office
            else:
                notes.append("%s: the senator's page prints no office address" % where)
        else:
            block = HOUSE_OFFICE_RE.search(page)
            if block:
                office = columbus_office(address_lines(block.group(1)), block.group(2),
                                         where, notes)
                if office:
                    member["capitolOffice"] = office
            else:
                notes.append("%s: the member's page prints no office address" % where)
        member["url"] = url
        seats[district] = member
    for district in range(1, cfg["seats"] + 1):
        if district not in seats:
            seats[district] = vacancy(
                "The member list of %s names no one for this district." % cfg["of"],
                list_url, previous, district, today)
            notes.append("%s %d: not listed, shipped as vacant"
                         % (cfg["label"].split()[0], district))
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


def build(pages, out_dir, today):
    built = {}
    for chamber in ("S", "H"):
        previous = previous_roster(out_dir, CHAMBERS[chamber])
        seats, notes = build_chamber(chamber, pages, previous, today)
        built[chamber] = (check(chamber, seats), notes)
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
        print("Wrote %s (%d of %d seats named, %d with a party, %d with an office "
              "address, %d with its telephone)"
              % (out_path, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("party")),
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
