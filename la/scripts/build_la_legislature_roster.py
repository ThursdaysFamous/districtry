#!/usr/bin/env python3
"""
Build the Louisiana Senate and Louisiana House rosters (district -> current
officeholder) as same-origin app-data files, from each chamber's OWN member
list and member pages, so the la-senate / la-house cards join a small roster
instead of reaching a third-party host at click time.

index.html's la-senate / la-house layers fetch data/app/la-senate-members.json
and la-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script reads each chamber's
"full info" member list and each member's own page, and writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
districtOffice, url}}, or a vacancy record). A weekly GitHub Action
(.github/workflows/update-la-legislature-roster.yml) reruns this and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-10-20. The House publishes one card per
seat at house.louisiana.gov/H_Reps/H_Reps_FullInfo and the Senate at
senate.la.gov/Senators_FullInfo. Each card prints the member's name surname
first ("Turner, Christopher"), the district, the party, the district office's
address and telephone, the member's e-mail address, and a link to the member's
own page. That day the House list held 105 cards, 103 members and two seats
printed as "Vacant - District 77" and "Vacant - District 92", and the Senate's
39 cards, 38 members and "Vacant - District 14". A vacant seat's card still
prints an office address and telephone, which belonged to the member who left;
neither ships.

THE NAME IS THE MEMBER PAGE'S, NOT THE LIST'S, because the list drops part of
some names when it turns them round: on 2026-10-20 the Senate list printed
"Morris, John C. "Jay"" and his own page "John C. "Jay" Morris III", and the
list printed "Landry, Jr. Terry" where his page reads "Terry Landry, Jr.". So
every member's page is fetched for the name in the order the legislature writes
it, and the page must agree with the list about the district and the surname or
the build stops, because the two pages would then describe different people.

WHAT IS READ, AND WHAT IS NEVER READ. From the list: the district, the district
office's address lines and telephone, and the e-mail address. From the member's
page: the name, the party and the district. The member's page also names a
legislative assistant and a fax number; neither is read. A district office
address ships because the legislature prints it as the member's district office,
the office a constituent visits; this project never publishes a home address,
and none of these cards prints one.

THE DISTRICT OFFICE'S TELEPHONE rides inside the office block, where the card
shows it as the office's number. On 2026-10-20 it was printed as one ten-digit
number on 143 of the 144 member cards, and on one as a word number with its
digits in brackets after it ("504-83POLLY (837-6559)"). A word number is read
only when its letters spell the bracketed digits on a telephone keypad, and then
ships as those digits with the area code in front; anything else is not carried
and the run says so without printing the number.

THE E-MAIL ADDRESS ships as the list prints it, on whatever domain, because the
fleet's rule since 2026-10-17 (Adam: "E-mails too") is that an address a
government page prints in one official's own entry is that official's. An
address the list prints for two or more members is an office's and ships on no
member's row. Every address that day was on the legislature's legis.la.gov.

ROBOTS. house.louisiana.gov and senate.la.gov each answer /robots.txt with the
same 42 bytes, "User-agent:* / Allow:/ / Disallow: /private/" (read 2026-10-20),
so every path this script reads is permitted. Each host's policy is read before
its first fetch through scraper_common.require_robots_once, with the same
User-Agent the fetches send. No Crawl-delay is stated; the pages are paced at
one second anyway. Both hosts serve their whole certificate chain (verified
against the public roots alone that day), so nothing is pinned.

Honesty: names are never guessed. A seat the list shows as vacant gets a vacancy
record naming the chamber's list; a seat with no card, or with two, stops the
build.

Usage:
    python3 la/scripts/build_la_legislature_roster.py [output_dir]
    python3 la/scripts/build_la_legislature_roster.py --save DIR [output_dir]
    python3 la/scripts/build_la_legislature_roster.py --offline DIR [output_dir]

--save writes every page fetched into DIR (list-H.html, list-S.html and
member/<chamber>-<district>.html), reading back any it already holds; --offline
reads them back instead of fetching, for building and testing without the
network.
"""

import datetime
import html as html_module
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/la/)"
PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

# Floors catch a truncated list or a layout change while tolerating real
# vacancies: 103 of 105 representatives and 38 of 39 senators were named on
# 2026-10-20.
CHAMBERS = {
    "H": {"page": "https://house.louisiana.gov/H_Reps/H_Reps_FullInfo",
          "out": "la-house-members.json", "label": "House",
          "body": "The Louisiana House of Representatives",
          "heading": "State Representative", "expected": 100, "seats": 105},
    "S": {"page": "https://senate.la.gov/Senators_FullInfo",
          "out": "la-senate-members.json", "label": "Senate",
          "body": "The Louisiana Senate",
          "heading": "State Senator", "expected": 36, "seats": 39},
}
# Every named member carried an e-mail address and a district office on
# 2026-10-20. A field every row carries going missing is the Brown County
# shape: the row count holds and the contact goes.
MIN_FIELD_SHARE = 0.9

# Both pages print the party as a word. Anything else ships as printed, and the
# run says so, rather than being guessed at.
PARTY_NAMES = {"Republican": "Republican", "Democrat": "Democratic",
               "Democratic": "Democratic", "Independent": "Independent"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

# One list card's fields, each a <span> whose id names the field and ends with
# the card's index: body_ListView1w2_DISTRICTNUMBERLabelw_94 on the House list,
# body_ListView11_DISTRICTNUMBERLabel1_34 on the Senate's.
LIST_FIELD_RE = re.compile(
    r'id="body_[A-Za-z0-9]+_(LASTFIRST|DISTRICTNUMBER|PARTYAFFILIATION|OFFICEADDRESS|'
    r'DISTRICTOFFICEPHONE|EMAILADDRESSPUBLIC)Label[A-Za-z0-9]*_\d+">(.*?)</span>', re.S)
LIST_LINK_RE = re.compile(r'class="legnamelink" href="([^"]+)"')
VACANT_RE = re.compile(r"^Vacant - District (\d+)$")
MEMBER_FIELD_RE = re.compile(
    r'id="body_FormView1111_(FULLNAME1|PARTYAFFILIATION1|DISTRICTNUMBER1)Label">(.*?)</span>',
    re.S)
PLAIN_PHONE_RE = re.compile(r"^\(?\d{3}\)?[ -]?\d{3}-\d{4}$")
WORD_PHONE_RE = re.compile(r"^(\d{3})-([0-9A-Z]{7})\s*\((\d{3})-(\d{4})\)$")
KEYPAD = {c: str(d) for d, letters in ((2, "ABC"), (3, "DEF"), (4, "GHI"), (5, "JKL"),
                                        (6, "MNO"), (7, "PQRS"), (8, "TUV"), (9, "WXYZ"))
          for c in letters}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

_SESSION = None
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

    require_robots_once(url, USER_AGENT, label="la-build-la-legislature-roster")
    wait = PACE_SECONDS - (time.time() - _LAST[0])
    if wait > 0:
        time.sleep(wait)
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        try:
            resp = session().get(url, timeout=60)
            _LAST[0] = time.time()
            resp.raise_for_status()
            resp.encoding = resp.encoding or "utf-8"
            return resp.text
        except requests.RequestException as exc:  # reset, timeout, 5xx
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


class Pages:
    """Fetch, save or replay the pages one run reads."""

    def __init__(self, offline=None, save=None):
        self.offline, self.save = offline, save

    def get(self, name, url):
        if self.offline:
            with open(os.path.join(self.offline, name), encoding="utf-8") as fh:
                return fh.read()
        if self.save and os.path.exists(os.path.join(self.save, name)):
            # A page an interrupted --save run already wrote is read back
            # rather than fetched twice.
            with open(os.path.join(self.save, name), encoding="utf-8") as fh:
                return fh.read()
        text = fetch(url)
        if self.save:
            path = os.path.join(self.save, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        return text


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


def fold(text):
    """Lower case without accents, so "Gallé" on one page is "Galle" on none."""
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def parse_list(page, chamber):
    """[card] from a chamber's full-info list, one per <fieldset>."""
    cfg = CHAMBERS[chamber]
    cards = []
    for block in page.split("<fieldset>")[1:]:
        fields = {}
        for key, value in LIST_FIELD_RE.findall(block):
            if key in fields:
                raise SystemExit("FAIL: a %s list card prints %s twice — the page "
                                 "layout changed" % (cfg["label"], key))
            fields[key] = value
        if not fields:
            continue
        link = LIST_LINK_RE.search(block)
        district = clean(fields.get("DISTRICTNUMBER"))
        if not district.isdigit() or not clean(fields.get("LASTFIRST")) or not link:
            raise SystemExit("FAIL: a %s list card carries no district, name or link "
                             "— the page layout changed (%r)"
                             % (cfg["label"], sorted(fields)))
        cards.append({
            "district": int(district),
            "lastfirst": clean(fields.get("LASTFIRST")),
            "party": clean(fields.get("PARTYAFFILIATION")),
            # The address keeps its line breaks: one line per <span> line.
            "address": [clean(line) for line in
                        html_module.unescape(fields.get("OFFICEADDRESS") or "").split("\n")
                        if clean(line)],
            "phone": clean(fields.get("DISTRICTOFFICEPHONE")),
            "email": clean(fields.get("EMAILADDRESSPUBLIC")),
            "url": urllib.parse.urljoin(cfg["page"], html_module.unescape(link.group(1))),
        })
    return cards


def office_phone(raw, where, notes):
    """The district office's telephone as a dialable number, or None."""
    if not raw:
        return None
    if PLAIN_PHONE_RE.match(raw):
        return raw
    word = WORD_PHONE_RE.match(raw)
    if word:
        area, letters, exchange, line = word.groups()
        spelled = "".join(KEYPAD.get(c, c) for c in letters)
        if spelled == exchange + line:
            return "(%s) %s-%s" % (area, exchange, line)
        notes.append("%s: the district office's word number does not spell the "
                     "digits printed beside it, so it was not carried" % where)
        return None
    notes.append("%s: the district office's telephone is not printed as one "
                 "number, so it was not carried" % where)
    return None


def member_fields(page, cfg, where):
    """(name, party_word, district) from a member's own page."""
    fields = {}
    for key, value in MEMBER_FIELD_RE.findall(page):
        fields.setdefault(key, clean(value))
    if cfg["heading"] not in page:
        raise SystemExit("FAIL: %s's page does not read %r — the page layout "
                         "changed, or the link leads somewhere else"
                         % (where, cfg["heading"]))
    name = fields.get("FULLNAME1")
    district = fields.get("DISTRICTNUMBER1", "")
    if not name or not district.isdigit():
        raise SystemExit("FAIL: %s's page carries no name or district — the page "
                         "layout changed" % where)
    return name, fields.get("PARTYAFFILIATION1", ""), int(district)


def read_previous(out_dir, cfg):
    path = os.path.join(out_dir, cfg["out"])
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def build(pages, out_dir, today):
    built = {}
    for chamber, cfg in CHAMBERS.items():
        cards = parse_list(pages.get("list-%s.html" % chamber, cfg["page"]), chamber)
        previous = read_previous(out_dir, cfg)
        seats, notes = {}, []
        for card in cards:
            district = card["district"]
            where = "%s %d" % (cfg["label"], district)
            if not 1 <= district <= cfg["seats"]:
                raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                                 % (where, cfg["seats"]))
            if district in seats:
                raise SystemExit("FAIL: %s carries two list cards" % where)
            vacant = VACANT_RE.match(card["lastfirst"])
            if vacant:
                if int(vacant.group(1)) != district:
                    raise SystemExit("FAIL: the %s card reads %r" % (where, card["lastfirst"]))
                prev = previous.get(str(district)) or {}
                seats[district] = {
                    "vacant": True,
                    "vacantWhy": "%s lists this seat as vacant on its members page." % cfg["body"],
                    "sourceUrl": cfg["page"],
                    "asOf": (prev.get("asOf") if prev.get("vacant") else None) or today,
                }
                notes.append("%s: vacant" % where)
                continue
            page = pages.get("member/%s-%d.html" % (chamber, district), card["url"])
            name, party, page_district = member_fields(page, cfg, where)
            # The member's page must agree with the list about which seat and
            # which person, or the two pages describe different people and
            # nothing from either ships.
            if page_district != district:
                raise SystemExit("FAIL: the list puts %r in %s and the member's page "
                                 "says District %d" % (card["lastfirst"], where, page_district))
            surname = card["lastfirst"].split(",")[0].strip()
            if not surname or fold(surname) not in fold(name):
                raise SystemExit("FAIL: %s: the list names %r and the member's page %r"
                                 % (where, card["lastfirst"], name))
            member = {"name": name}
            word = party or card["party"]
            if party and card["party"] and party != card["party"]:
                notes.append("%s: the list prints the party %r and the member's page "
                             "%r; the page's ships" % (where, card["party"], party))
            if word:
                member["party"] = PARTY_NAMES.get(word, word)
                if word not in PARTY_NAMES:
                    notes.append("%s: party printed as %r ships as printed" % (where, word))
            if card["email"]:
                if EMAIL_RE.match(card["email"]):
                    member["email"] = card["email"]
                else:
                    notes.append("%s: an e-mail entry that is not one plain address was "
                                 "not carried" % where)
            office = list(card["address"])
            phone = office_phone(card["phone"], where, notes)
            if phone:
                office.append(phone)
            if office:
                member["districtOffice"] = office
            member["url"] = card["url"]
            seats[district] = member

        missing = [d for d in range(1, cfg["seats"] + 1) if d not in seats]
        if missing:
            raise SystemExit("FAIL: the %s list carries no card for District(s) %s"
                             % (cfg["label"], ", ".join(map(str, missing))))
        roster = {str(d): seats[d] for d in range(1, cfg["seats"] + 1)}
        named = [m for m in roster.values() if m.get("name")]
        if len(named) < cfg["expected"]:
            raise SystemExit("FAIL: resolved %d named %s districts (expected >= %d) — "
                             "refusing to overwrite the roster with an incomplete "
                             "chamber" % (len(named), cfg["label"], cfg["expected"]))
        for field in ("email", "districtOffice"):
            have = sum(1 for m in named if m.get(field))
            if have < MIN_FIELD_SHARE * len(named):
                raise SystemExit("FAIL: only %d of %d %s members carry %s — a field the "
                                 "list carried on every member stopped arriving"
                                 % (have, len(named), cfg["label"], field))
        built[chamber] = (roster, notes)

    # An address the lists print for two or more members, in either chamber,
    # is an office's and ships on no member's row.
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
    # the Senate cannot leave a fresh House file beside a stale Senate one.
    os.makedirs(out_dir, exist_ok=True)
    for chamber, (roster, notes) in built.items():
        cfg = CHAMBERS[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for m in roster.values() if m.get("name")]
        print("Wrote %s (%d of %d seats named, %d with an e-mail, %d with a district "
              "office, %d with its telephone)"
              % (out_path, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("districtOffice")),
                 sum(1 for m in named
                     if any(PLAIN_PHONE_RE.match(x) for x in m.get("districtOffice", ())))),
              file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
