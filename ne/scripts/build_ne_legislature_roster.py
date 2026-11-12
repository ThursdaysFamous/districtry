#!/usr/bin/env python3
"""
Build the Nebraska Legislature roster (district -> current senator) as a
same-origin app-data file, from the Legislature's own pages at
nebraskalegislature.gov, so the ne-legislature card joins a small roster
instead of reaching another host at click time.

Nebraska's Legislature has one chamber: 49 senators, one from each
legislative district, elected on a ballot that names no party. index.html's
ne-legislature layer fetches data/app/ne-legislature-members.json lazily on
first click and joins it to the pre-built legislative geometry by district
number. This script writes the roster shaped for the registerIlgaChamber
factory ({district -> {name, email, phone, url}}, or a record naming nobody).
A weekly GitHub Action (.github/workflows/update-ne-legislature-roster.yml)
reruns it and opens a PR when the roster changes, so officeholder data gets a
look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The senator list (nebraskalegislature.gov/senators/senator_list.php) prints
each senator's name, surname first, and district, and links each district's
senator page (senators/landing-pages/index.php?District=N). That day it listed
all 49. Each senator page prints the senator's name and district, the
senator's Capitol office, one telephone and an e-mail address at leg.ne.gov.
This script reads the list and then every senator page.

WHAT IS READ ON A SENATOR PAGE: the "Sen." heading (to check the page is the
senator's), the district line (to check it is the district the list gives),
the telephone printed between them and the e-mail line, and the e-mail link.
The page labels the telephone with nothing, so the card prints the number
alone; under the fleet's rule of 2026-10-17 a number a government source
prints beside an official ships on that official. WHAT IS NEVER READ: the
office address lines, committee assignments, staff and the photograph.
Nebraska's ballot names no party, so no party is carried.

ROBOTS. nebraskalegislature.gov/robots.txt (135 bytes) was read on
2026-11-12: its group for every client disallows three search pages and
states "Crawl-delay: 3", which this script honours between requests. It is
read through scripts/robots_policy.py with the User-Agent the fetches send.

Honesty: names are never guessed. A district the list carries nobody for gets
a record naming nobody, dated; a senator page naming another district stops
the build.

Usage:
    python3 ne/scripts/build_ne_legislature_roster.py [output_dir]
    python3 ne/scripts/build_ne_legislature_roster.py --save DIR [output_dir]
    python3 ne/scripts/build_ne_legislature_roster.py --offline DIR [output_dir]
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


USER_AGENT = "districtry/1.0 (+https://districtry.com/ne/)"
HOST = "https://nebraskalegislature.gov/senators/"
LIST = HOST + "senator_list.php"
PAGE = HOST + "landing-pages/index.php?District=%s"

# 49 of 49 senators were listed on 2026-11-12.
CHAMBERS = {
    "L": {"out": "ne-legislature-members.json", "label": "Legislature", "seats": 49,
          "expected": 44, "fields": {"email": 0.9, "phone": 0.8, "url": 0.9}},
}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@leg\.ne\.gov$", re.I)
ROW_RE = re.compile(
    r'<li class="list-group-item[^"]*sen-list-item">\s*<a href="/senators/landing-pages/'
    r'index\.php\?District=(\d+)"><div class="row"><span class="col-9">([^<]+)</span>'
    r'<span class="col-3">(\d+)</span>')
MAILTO_RE = re.compile(r'href="mailto:([^"?]+)"', re.I)


def listed(raw):
    """[(district, "Last, First")] from the senator list. A commented-out row
    (the list keeps one for the Speaker inside an HTML comment) is skipped.
    The page prints the list twice (98 rows for 49 senators on 2026-11-12),
    so a repeated row is read once and a district printed with two names
    stops the build."""
    page = re.sub(r"<!--.*?-->", "", raw["list.html"].decode("utf-8", "replace"), flags=re.S)
    rows = []
    for linked, printed, district in ROW_RE.findall(page):
        if linked != district:
            raise SystemExit("FAIL: a list row links District %s and prints %s"
                             % (linked, district))
        row = (str(int(district)), clean(printed))
        if row in rows:
            continue
        if any(d == row[0] for d, _ in rows):
            raise SystemExit("FAIL: the senator list prints District %s with two names"
                             % row[0])
        rows.append(row)
    if not rows:
        raise SystemExit("FAIL: the senator list carries no row in the form this "
                         "build reads; read it and update ROW_RE")
    return rows


def sources(raw):
    yield "list.html", LIST, {}
    for district, _printed in listed(raw):
        yield "senator-%s.html" % district, PAGE % district, {}


def parse(raw, notes):
    entries = []
    for district, printed in listed(raw):
        where = "District %s" % district
        if "vacant" in printed.lower():
            notes.append("%s: the list prints %r" % (where, printed))
            continue
        surname = printed.split(",")[0].strip()
        page = raw["senator-%s.html" % district].decode("utf-8", "replace")
        text = clean(re.sub(r"<[^>]+>", " | ", page))
        # A title line (the Speaker's) can sit between the name and the district.
        m = re.search(r"\|\s*Sen\.\s+([^|]+?)(?:\s*\|)+(?:\s*[^|0-9]+?(?:\s*\|)+)?"
                      r"\s*District\s+(\d+)\s*\|(.*?)\|\s*Email:", text, re.S)
        if not m:
            raise SystemExit("FAIL: %s's page prints no \"Sen.\" heading, district line and "
                             "e-mail line in the form this build reads" % where)
        name, on_page, between = clean(m.group(1)), m.group(2), m.group(3)
        if str(int(on_page)) != district:
            raise SystemExit("FAIL: %s's page names District %s" % (where, on_page))
        if surname.lower() not in name.lower() or re.search(r"\d", name):
            raise SystemExit("FAIL: %s's page names %r, not the list's %r"
                             % (where, name, printed))
        member = {"name": name}
        mail = MAILTO_RE.search(page)
        email = clean(mail.group(1)) if mail else ""
        if EMAIL_RE.match(email):
            member["email"] = email
        elif email:
            notes.append("%s: an e-mail address off leg.ne.gov was not carried" % where)
        numbers = re.findall(r"\(\d{3}\)\s*\d{3}-\d{4}|\b\d{3}[-.]\d{3}[-.]\d{4}\b", between)
        add_phones(member, labelled_phones([(n, "") for n in numbers], where, notes))
        member["url"] = PAGE % district
        entries.append(("L", district, member))
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
