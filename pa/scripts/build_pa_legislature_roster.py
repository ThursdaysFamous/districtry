#!/usr/bin/env python3
"""
Build the Pennsylvania Senate and House of Representatives rosters (district
-> current officeholder) as same-origin app-data files, from the General
Assembly's OWN member pages at palegis.us, so the pa-senate / pa-house cards
join a small roster instead of reaching a third-party host at click time.

index.html's pa-senate / pa-house layers fetch data/app/pa-senate-members.json
and pa-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
capitolOffice, url}}, or a vacancy record). A weekly GitHub Action
(.github/workflows/update-pa-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-10. The General Assembly's site prints
one member list per chamber, www.palegis.us/senate/members and
www.palegis.us/house/members, with one card per member: the member's name in
reading order, the party as a letter (data-party "R" or "D") and the district
as a three-digit number (data-district "029"), and a link to the member's own
page (/senate/members/bio/69/sen-argall). That day the Senate list held 50
cards for the 50 seats and the House list 203 for the 203 seats. Each member's
own page prints a "Capitol Address" block: the Capitol office (a room and
building, "177 Main Capitol"), the chamber's mailing box in Harrisburg, the
office telephone and a fax number.

Most Senate cards also carry the senator's e-mail address, written into the
page by a short script ("Name", "Domain" and "Ext" joined with an @), which the
builder reassembles exactly as the page does: 36 of the 50 on 2026-11-10. The
other 14 link a contact form on the senator's own site instead, and the House
cards link each representative's contact form on pahouse.com, so those members
carry no e-mail address. No contact-form link is carried; the card links the
member's page, which links the form.

WHAT IS READ, AND WHAT IS NEVER READ. From each member: the name, the
district, the party, the Capitol office and its mailing address as printed,
the office telephone, the senator's e-mail address and the member's own page.
The fax number is never read. The cards also list the counties a district
covers, and the member pages print district offices, biographies and staff;
none of those is read, and no district office ships, because the builder has
no way to tell one apart from a member's home. Every Capitol office must name
Harrisburg's Capitol ZIP code (171xx) or the build refuses it.

THE E-MAIL ADDRESS ships as the page writes it, because the fleet's rule since
2026-10-17 (Adam: "E-mails too") is that an address a government source prints
in one official's own entry is that official's. An address printed for two or
more members is an office's and ships on no member's row.

ROBOTS. www.palegis.us's robots.txt is read through scripts/robots_policy.py
with the User-Agent the fetches send, before the first fetch, and a stated
Crawl-delay is honoured by its HostPacer. Read 2026-11-10: the file's one
group names the UserWay accessibility scanner's browser string, and no group
names this client or `*`, so no rule binds these fetches. The host is paced at
one request a second regardless.

Honesty: names are never guessed. A seat missing from a chamber's list gets a
vacancy record naming that list; a seat carried by two cards stops the build.

Usage:
    python3 pa/scripts/build_pa_legislature_roster.py [output_dir]
    python3 pa/scripts/build_pa_legislature_roster.py --save DIR [output_dir]
    python3 pa/scripts/build_pa_legislature_roster.py --offline DIR [output_dir]

--save writes every page fetched into DIR (senate-list.html, senate/<id>.html,
house-list.html and house/<id>.html), reading back any it already holds;
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/pa/)"
# The host is paced at one second even where it states no delay.
MIN_PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

SITE = "https://www.palegis.us"
LISTS = {"S": SITE + "/senate/members", "H": SITE + "/house/members"}

# Floors catch a truncated list or a layout change while tolerating real
# vacancies: 50 of 50 senators and 203 of 203 representatives were named on
# 2026-11-10.
CHAMBERS = {
    "S": {"out": "pa-senate-members.json", "label": "Senate", "seats": 50,
          "expected": 45, "cards": 40, "path": "senate",
          "body": "The Pennsylvania Senate",
          # The share of named members carrying each field, floored below what
          # 2026-11-10 measured: every senator printed a party and a Capitol
          # office, and 36 of 50 cards an e-mail address (the other 14 link a
          # contact form). A field falling under its floor is the Brown County
          # shape: the row count holds and the contact goes.
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.6}},
    "H": {"out": "pa-house-members.json", "label": "House of Representatives",
          "seats": 203, "expected": 185, "cards": 160, "path": "house",
          "body": "The Pennsylvania House of Representatives",
          # The House list prints no e-mail address for anyone.
          "fields": {"party": 0.9, "capitolOffice": 0.9}},
}

PARTY_NAMES = {"R": "Republican", "D": "Democratic", "I": "Independent"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")

# One member card, split on its opening class.
CARD_SPLIT = 'class="col-6 col-sm-6 col-lg-3 member '
CARD_PARTY_RE = re.compile(r'data-party="([A-Z]*)"')
CARD_DISTRICT_RE = re.compile(r'data-district="(\d+)"')
# A slug can carry an apostrophe (rep-o'neal), which the URL percent-encodes.
CARD_LINK_RE = re.compile(r'href="\s*/(senate|house)/members/bio/(\d+)/([a-z0-9\'-]+)"')
CARD_NAME_RE = re.compile(r'<span class="thumb-info-inner">([^<]*)</span>')
# The senator's e-mail address as the card's script writes it.
CARD_MAIL_RE = re.compile(
    r'var Name\s*=\s*"([^"]*)";\s*var Domain\s*=\s*"([^"]*)";\s*var Ext\s*=\s*"([^"]*)";')
# The member page's "Capitol Address" list.
OFFICE_RE = re.compile(
    r'<div class="h5 mb-1">Capitol Address</div>\s*<ul class="list list-icons">(.*?)</ul>',
    re.S)
OFFICE_ITEM_RE = re.compile(r"<li>(.*?)</li>", re.S)
OFFICE_TITLE_RE = re.compile(r"<i title='([^']*)'")
CAPITOL_ZIP_RE = re.compile(r"\bHarrisburg, PA 171\d\d(-\d{4})?$")

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


def parse_list(chamber, page):
    cfg = CHAMBERS[chamber]
    cards = []
    for chunk in page.split(CARD_SPLIT)[1:]:
        # One card's markup ends where the next begins; the script that writes
        # the e-mail address sits inside it.
        district = CARD_DISTRICT_RE.search(chunk)
        link = CARD_LINK_RE.search(chunk)
        name = CARD_NAME_RE.search(chunk)
        if not (district and link and name):
            raise SystemExit("FAIL: a %s member card lacks its district, page link or "
                             "name — the list's layout changed" % cfg["label"])
        if link.group(1) != cfg["path"]:
            raise SystemExit("FAIL: the %s list links a member page under /%s/"
                             % (cfg["label"], link.group(1)))
        party = CARD_PARTY_RE.search(chunk)
        mail = CARD_MAIL_RE.search(chunk)
        cards.append({
            "district": int(district.group(1)),
            "id": link.group(2),
            "slug": link.group(3),
            "name": clean(name.group(1)),
            "party": party.group(1) if party else None,
            "email": ("%s@%s%s" % mail.groups()) if mail else None,
        })
    if len(cards) < cfg["cards"]:
        raise SystemExit("FAIL: the %s member list yielded %d cards — its layout changed"
                         % (cfg["label"], len(cards)))
    return cards


def party_word(letter, where, notes):
    if not letter:
        notes.append("%s: no party printed" % where)
        return None
    if letter not in PARTY_NAMES:
        notes.append("%s: party printed as %r ships as printed" % (where, letter))
    return PARTY_NAMES.get(letter, letter)


def plain_email(raw, where, notes):
    if not raw:
        return None
    raw = raw.strip()
    if EMAIL_RE.match(raw):
        return raw
    notes.append("%s: an e-mail entry that is not one plain address was not carried" % where)
    return None


def capitol_office(page, where, notes):
    """The Capitol office as printed on the member's page: the office, the
    mailing address and the office telephone, in that order. The member's own
    name heads the list and is dropped; the fax line is never read."""
    m = OFFICE_RE.search(page)
    if not m:
        notes.append("%s: the member's page prints no Capitol address" % where)
        return []
    office, phone = [], None
    for item in OFFICE_ITEM_RE.findall(m.group(1)):
        title = OFFICE_TITLE_RE.search(item)
        title = title.group(1) if title else None
        text = clean(item)
        if not text or "<strong>" in item:
            continue  # the member's own name
        if title == "Fax":
            continue
        if title == "Phone":
            if PHONE_RE.match(text):
                phone = text
            else:
                notes.append("%s: the Capitol telephone is not printed as one number, so "
                             "it was not carried" % where)
            continue
        if title in ("Capitol Office", "Capitol Mailing Address") or title is None:
            office.append(text)
            continue
        notes.append("%s: a Capitol address line titled %r was not read" % (where, title))
    if not office or not CAPITOL_ZIP_RE.search(office[-1]):
        notes.append("%s: the Capitol address reads %r, which does not end in a "
                     "Harrisburg Capitol ZIP code, so it was not carried" % (where, office))
        return []
    if phone:
        office.append(phone)
    return office


def build_chamber(chamber, pages, previous, today):
    cfg = CHAMBERS[chamber]
    list_url = LISTS[chamber]
    cards = parse_list(chamber, pages.get("%s-list.html" % cfg["path"], list_url))
    seats, notes = {}, []
    for card in cards:
        district = card["district"]
        where = "%s %d" % (cfg["label"], district)
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats:
            raise SystemExit("FAIL: %s carries two member cards" % where)
        url = "%s/%s/members/bio/%s/%s" % (SITE, cfg["path"], card["id"],
                                           urllib.parse.quote(card["slug"], safe="-"))
        page = pages.get("%s/%s.html" % (cfg["path"], card["id"]), url)
        surname = card["name"].split()[-1].lower()
        if surname in ("jr.", "sr.", "ii", "iii", "iv") and len(card["name"].split()) > 1:
            surname = card["name"].split()[-2].lower().rstrip(",")
        if surname not in clean(page).lower():
            raise SystemExit("FAIL: %s's page does not name %s" % (where, card["name"]))
        member = {"name": card["name"]}
        party = party_word(card["party"], where, notes)
        if party:
            member["party"] = party
        email = plain_email(card["email"], where, notes)
        if email:
            member["email"] = email
        office = capitol_office(page, where, notes)
        if office:
            member["capitolOffice"] = office
        member["url"] = url
        seats[district] = member
    for district in range(1, cfg["seats"] + 1):
        if district not in seats:
            seats[district] = vacancy(
                "%s's member list names no one for this district." % cfg["body"],
                list_url, previous, district, today)
            notes.append("%s %d: no card, shipped as vacant" % (cfg["label"], district))
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
