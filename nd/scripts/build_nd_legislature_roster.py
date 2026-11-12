#!/usr/bin/env python3
"""
Build the North Dakota Senate and House of Representatives rosters (district
-> current officeholders) as same-origin app-data files, from the North Dakota
Legislative Branch's own pages at ndlegis.gov, so the nd-senate / nd-house
cards join a small roster instead of reaching another host at click time.

North Dakota elects one senator and two representatives from each of its 47
legislative districts, except District 4, whose two representatives are
elected from two subdistricts, 4A and 4B, which TIGERweb's lower-house layer
draws as two districts of their own. index.html's nd-senate / nd-house layers fetch
data/app/nd-senate-members.json and nd-house-members.json lazily on first
click and join them to the pre-built geometry: the Senate by district number,
the House by district or subdistrict. This script writes the Senate roster
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
phone, url}}) and the House roster as {district -> {seats, members[, asOf]}}
(seats 2, or 1 for 4A and 4B). A weekly GitHub Action
(.github/workflows/update-nd-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The assembly's members-by-district page
(ndlegis.gov/assembly/69-2025/regular/members/members-by-district) prints
every member who has served in the 69th Legislative Assembly: chamber, name,
district and party, and, for a member whose service began or ended during
the assembly, a status line ("Active 8/5/2026", "Resigned 8/4/2026",
"Deceased 4/25/2026"). That day it carried 148 members, seven of whom had
resigned or died; this script drops every member whose status is not
"Active" or absent, and stops on a status word it does not know. The 141 it
keeps fill every seat: 47 senators and 94 representatives. Each member's
biography page (linked from the list) prints the member's e-mail address at
ndlegis.gov and, for most, telephone numbers, each under a label ("Cell",
"Home", "Work"); the script reads the biography's contact block only.

WHICH ASSEMBLY. Legislators' terms begin on 1 December after the election
(the list itself dates one new member "Active 12/1/2024"),
so before 1 December 2026 the script reads the 69th Assembly's page and from
that day the 70th's (70-2027). If the 70th's page is not yet published, the
build stops rather than show the 69th's members after their terms end.

WHAT IS READ ON A BIOGRAPHY PAGE: the e-mail link and the telephone fields of
the contact block, each with its own label. A number the page prints beside
the member ships on that member with that label under the fleet's rule of
2026-10-17; a number labelled "Fax" does not ship. The biography text and the
photograph are not read.

ROBOTS. ndlegis.gov/robots.txt (2,046 bytes) was read on 2026-11-12: its
group for every client disallows Drupal's own paths and no rule matches the
assembly or biography pages. It is read through scripts/robots_policy.py
with the User-Agent the fetches send; the pages are read one a second.

Honesty: names are never guessed. A seat with no sitting member gets a dated
record (or a short district its listed members and the date); a district
listing more sitting members than it elects stops the build.

Usage:
    python3 nd/scripts/build_nd_legislature_roster.py [output_dir]
    python3 nd/scripts/build_nd_legislature_roster.py --save DIR [output_dir]
    python3 nd/scripts/build_nd_legislature_roster.py --offline DIR [output_dir]
"""

import datetime
import html
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

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
ATTEMPTS = 4
RETRY_SECONDS = 20.0


USER_AGENT = "districtry/1.0 (+https://districtry.com/nd/)"
HOST = "https://ndlegis.gov"
LIST = HOST + "/assembly/%s/regular/members/members-by-district"
PAUSE = 1.0  # seconds between pages; robots.txt states no delay


def assembly(today=None):
    """The assembly whose members sit today: terms begin on 1 December."""
    today = today or datetime.date.today()
    return "69-2025" if today < datetime.date(2026, 12, 1) else "70-2027"


HOUSE_DISTRICTS = {str(d): 2 for d in range(1, 48) if d != 4}
HOUSE_DISTRICTS.update({"4A": 1, "4B": 1})

# 47 of 47 senators and 94 of 94 representatives were sitting on 2026-11-12.
CHAMBERS = {
    "S": {"out": "nd-senate-members.json", "label": "Senate", "seats": 47,
          "expected": 42, "fields": {"party": 0.9, "email": 0.9, "url": 0.9}},
    "H": {"out": "nd-house-members.json", "label": "House", "districts": HOUSE_DISTRICTS,
          "expected": 85, "fields": {"party": 0.9, "email": 0.9, "url": 0.9}},
}
CHAMBER_WORDS = {"Senator": "S", "Representative": "H"}
PARTIES = {"Republican": "Republican", "Democrat": "Democratic",
           "Democratic": "Democratic", "Independent": "Independent",
           "Democratic-NPL": "Democratic-NPL"}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@ndlegis\.gov$", re.I)
ITEM_RE = re.compile(r'<li class="member-item(.*?)</li>', re.S)
BIO_RE = re.compile(r'<a href="(/biography/[a-z0-9-]+)">')
STATUS_RE = re.compile(r'</a>\s*<div class="member-status">([^<]*)</div>')
DISTRICT_RE = re.compile(r'<div class="district">\s*District (\w+) \| '
                         r'<span class="sr-only">([^<]*)</span>')
FIELD_RE = re.compile(r'<div class="field field--name-field-([a-z0-9-]+) field--type-'
                      r'(telephone|email)[^"]*">\s*<div class="field__label">([^<]*)</div>\s*'
                      r'<div class="field__item">(.*?)</div>', re.S)


def sitting(raw):
    """[(chamber, district, name, party, biography path)] for every member the
    list does not mark as gone."""
    page = raw["list.html"].decode("utf-8", "replace")
    rows = []
    for item in ITEM_RE.findall(page):
        chamber = re.search(r'member-chamber">([^<]*)<', item)
        name = re.search(r'member-name">([^<]*)<', item)
        place = DISTRICT_RE.search(item)
        bio = BIO_RE.search(item)
        if not (chamber and name and place and bio):
            raise SystemExit("FAIL: a member item lacks a chamber, name, district or "
                             "biography link in the form this build reads")
        word = clean(chamber.group(1))
        if word not in CHAMBER_WORDS:
            raise SystemExit("FAIL: a member item names chamber %r" % word)
        status = STATUS_RE.search(item)
        status = clean(status.group(1)) if status else ""
        state = status.split(" ")[0] if status else ""
        who = clean(name.group(1))
        if state in ("Resigned", "Deceased"):
            continue
        if state not in ("", "Active"):
            raise SystemExit("FAIL: %s's status %r is one this builder has no reading for"
                             % (who, status))
        district = place.group(1).upper().lstrip("0")
        rows.append((CHAMBER_WORDS[word], district, who, clean(place.group(2)),
                     bio.group(1)))
    if not rows:
        raise SystemExit("FAIL: the members-by-district page carries no member in the "
                         "form this build reads; read it and update ITEM_RE")
    return rows


def sources(raw):
    yield "list.html", LIST % assembly(), {}
    for _chamber, _district, _name, _party, bio in sitting(raw):
        yield "bio-%s.html" % bio.rsplit("/", 1)[1], HOST + bio, {}


def parse(raw, notes):
    entries = []
    for chamber, district, name, party, bio in sitting(raw):
        where = "%s %s" % (CHAMBERS[chamber]["label"], district)
        if not name or re.search(r"\d", name):
            raise SystemExit("FAIL: %s's item names %r" % (where, name))
        member = {"name": name}
        if party in PARTIES:
            member["party"] = PARTIES[party]
        elif party:
            raise SystemExit("FAIL: %s's party %r is one this builder has no name for"
                             % (where, party))
        page = raw["bio-%s.html" % bio.rsplit("/", 1)[1]].decode("utf-8", "replace")
        block = page.split("biography-contact-information-wrapper", 1)
        pairs = []
        if len(block) == 2:
            for _key, kind, label, value in FIELD_RE.findall(block[1].split("print__wrapper")[0]):
                label = clean(label)
                if kind == "email":
                    email = clean(value)
                    if EMAIL_RE.match(email) and "email" not in member:
                        member["email"] = email
                    elif email and not EMAIL_RE.match(email):
                        notes.append("%s: an e-mail address off ndlegis.gov was not carried"
                                     % where)
                elif label.lower() != "fax":
                    pairs.append((clean(value), label.lower()))
        else:
            notes.append("%s: the biography page has no contact block" % where)
        add_phones(member, labelled_phones(pairs, where, notes))
        member["url"] = HOST + bio
        if chamber == "S" and not district.isdigit():
            raise SystemExit("FAIL: a senator is listed for district %r" % district)
        entries.append((chamber, district, member))
    return entries


def clean(text):
    """One line of text as a reader sees it: entities decoded, tags and runs
    of whitespace collapsed."""
    text = re.sub(r"<[^>]+>", " ", str(text or ""))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def normal_phone(text):
    """A ten-digit number as NNN-NNN-NNNN, whatever punctuation it was printed
    with, or None when the text is not one telephone number."""
    if re.search(r"[A-Za-z]", text or ""):
        return None
    digits = re.sub(r"\D", "", text or "")
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def labelled_phones(pairs, where, notes):
    """[(printed number, label or "")] -> the member's telephones, one entry
    per number, carrying every label it was printed under."""
    labels, order = {}, []
    for printed, label in pairs:
        printed = clean(printed)
        if not printed:
            continue
        number = normal_phone(printed)
        if not number:
            notes.append("%s: a telephone printed as %r is not one number, not carried"
                         % (where, printed))
            continue
        if number not in labels:
            labels[number] = []
            order.append(number)
        if label and label not in labels[number]:
            labels[number].append(label)

    def joined(words):
        return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]
    return [("%s %s" % (joined(labels[n]), n)) if labels[n] else n for n in order]


def add_phones(member, numbers):
    if numbers:
        member["phone"] = numbers[0]
        if numbers[1:]:
            member["phonesExtra"] = numbers[1:]


_SESSION = None
_GATE = None
_PACER = None
_ASKED = set()
_LAST = {}


def session():
    global _SESSION, _GATE, _PACER
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
        _GATE = RobotsGate(_SESSION, USER_AGENT)
        _PACER = HostPacer(_GATE)
    return _SESSION


def fetch(url, data=None, headers=None):
    """One request, after robots.txt is read with the client that sends it;
    a stated Crawl-delay is honoured by the shared HostPacer."""
    import requests

    session()
    host = urllib.parse.urlsplit(url).netloc
    ok, why = _GATE.allows(url)
    if host not in _ASKED:
        _ASKED.add(host)
        print("robots.txt %s: %s" % (host, why), file=sys.stderr)
    if not ok:
        raise SystemExit("FAIL: robots.txt refuses %s (%s)" % (url, why))
    # A builder that fetches many pages from one host sets PAUSE (seconds),
    # on top of any Crawl-delay the host states.
    wait = globals().get("PAUSE", 0.0) - (time.time() - _LAST.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        try:
            _LAST[host] = time.time()
            with _PACER.hold(url):
                if data is None:
                    resp = _SESSION.get(url, headers=headers, timeout=60)
                else:
                    resp = _SESSION.post(url, data=data, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                _SESSION.close()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


def load(offline, save):
    """Every source, by the name it is saved under. sources() is handed the
    sources read so far, so a later address can depend on an earlier answer."""
    raw = {}
    for name, url, opts in sources(raw):
        if offline:
            with open(os.path.join(offline, name), "rb") as fh:
                raw[name] = fh.read()
            continue
        raw[name] = fetch(url, **opts)
        if save:
            os.makedirs(save, exist_ok=True)
            with open(os.path.join(save, name), "wb") as fh:
                fh.write(raw[name])
    return raw


def district_keys(cfg):
    if "districts" in cfg:
        return list(cfg["districts"])
    return [str(d) for d in range(1, cfg["seats"] + 1)]


def seats_in(cfg, key):
    if "districts" in cfg:
        return cfg["districts"][key]
    return cfg.get("per_district", 1)


def multi(cfg):
    return "districts" in cfg or cfg.get("per_district", 1) > 1


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def build(entries, previous, today):
    """Seat every listed member, and give every seat nobody is listed for a
    dated record naming nobody. The date is carried forward from the last
    roster while the same seat stays short, so a weekly rerun changes nothing
    until the source does."""
    listed = {c: {} for c in CHAMBERS}
    notes = {c: [] for c in CHAMBERS}
    for chamber, key, member in entries:
        cfg = CHAMBERS[chamber]
        where = "%s %s" % (cfg["label"], key)
        if key not in district_keys(cfg):
            raise SystemExit("FAIL: %s is not one of the chamber's districts" % where)
        members = listed[chamber].setdefault(key, [])
        if len(members) >= seats_in(cfg, key):
            raise SystemExit("FAIL: %s lists more members than the %d seat(s) it elects"
                             % (where, seats_in(cfg, key)))
        if any(m["name"] == member["name"] for m in members):
            raise SystemExit("FAIL: %s lists %s twice" % (where, member["name"]))
        members.append(member)
    out = {}
    for chamber, cfg in CHAMBERS.items():
        roster = {}
        for key in district_keys(cfg):
            members = listed[chamber].get(key, [])
            seats = seats_in(cfg, key)
            prev = previous[chamber].get(key) or {}
            if multi(cfg):
                rec = {"seats": seats, "members": members}
                if len(members) < seats:
                    same = ([m.get("name") for m in prev.get("members") or []]
                            == [m.get("name") for m in members])
                    rec["asOf"] = (prev.get("asOf") if same else None) or today
                    notes[chamber].append("%s %s: %d of %d members listed"
                                          % (cfg["label"], key, len(members), seats))
            elif members:
                rec = members[0]
            else:
                rec = {"asOf": (prev.get("asOf") if not prev.get("name") else None) or today}
                notes[chamber].append("%s %s: no member listed" % (cfg["label"], key))
            roster[key] = rec
        out[chamber] = check(chamber, roster)
    return out, notes


def named_members(cfg, roster):
    if multi(cfg):
        return [m for rec in roster.values() for m in rec.get("members") or []]
    return [m for m in roster.values() if m.get("name")]


def check(chamber, roster):
    cfg = CHAMBERS[chamber]
    named = named_members(cfg, roster)
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
    parse_notes = []
    entries = parse(load(offline, save), parse_notes)
    previous = {c: previous_roster(out_dir, cfg) for c, cfg in CHAMBERS.items()}
    built, notes = build(entries, previous, today)
    os.makedirs(out_dir, exist_ok=True)
    for chamber, cfg in CHAMBERS.items():
        roster = built[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = named_members(cfg, roster)
        total = sum(seats_in(cfg, k) for k in district_keys(cfg))
        print("Wrote %s (%d of %d seats named, %d with a party, %d with an e-mail "
              "address, %d with a telephone)"
              % (out_path, len(named), total,
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("phone"))), file=sys.stderr)
        for note in notes[chamber]:
            print("  " + note, file=sys.stderr)
    for note in parse_notes:
        print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
