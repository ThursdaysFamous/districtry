#!/usr/bin/env python3
"""
Build the Idaho Senate and House of Representatives rosters (legislative
district -> current officeholders) as same-origin app-data files, from the
Idaho Legislature's own membership pages at legislature.idaho.gov, so the
id-senate / id-house cards join a small roster instead of reaching another
host at click time.

Idaho elects one senator and two representatives (House Seat A and Seat B)
from each of its 35 legislative districts, so both cards join the same
district map. index.html's id-senate / id-house layers fetch
data/app/id-senate-members.json and id-house-members.json lazily on first
click. This script writes the Senate roster shaped for the registerIlgaChamber
factory ({district -> {name, party, email, phone, url}}) and the House roster
as {district -> {seats: 2, members: [Seat A, Seat B]}}, the shape Arizona's and
Washington's House rosters brought to the factory. A weekly GitHub Action
(.github/workflows/update-id-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The Senate's and House's membership pages (legislature.idaho.gov/senate/
membership/ and /house/membership/) print one block per sitting member: the
name and party letter, an e-mail address at senate.idaho.gov or
house.idaho.gov, a leadership title for some, the district, for a representative the seat ("House Seat A"),
and a Statehouse telephone the page marks "(Session Only)". That day they
listed all 35 senators and all 70 representatives. Each block also prints the
member's home address lines between the district and the Statehouse
telephone. THE ADDRESS IS NEVER READ: this script takes the name, party,
e-mail link, district link, seat line and the one telephone link the page
labels "Statehouse", and nothing else in the block. The telephone ships with
the page's own words, "Statehouse (session only)", under the fleet's rule of
2026-10-17. Each member is linked to the Legislature's page for the member's
district, as the block links it (with the session year).

ROBOTS. legislature.idaho.gov/robots.txt was read on 2026-11-12 and no rule in
its group for every client matches the two membership pages. It is read
through scripts/robots_policy.py with the User-Agent the fetches send.

Honesty: names are never guessed. A seat the page carries nobody for gets a
dated record (or a short district its listed members and the date); a seat
printed twice stops the build.

Usage:
    python3 id/scripts/build_id_legislature_roster.py [output_dir]
    python3 id/scripts/build_id_legislature_roster.py --save DIR [output_dir]
    python3 id/scripts/build_id_legislature_roster.py --offline DIR [output_dir]
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


USER_AGENT = "districtry/1.0 (+https://districtry.com/id/)"
HOST = "https://legislature.idaho.gov"
PAGES = {"S": HOST + "/senate/membership/", "H": HOST + "/house/membership/"}
DISTRICT_PAGE = HOST + "/legislators/membership/?yr=%s&district=%s"

# 35 of 35 senators and 70 of 70 representatives were listed on 2026-11-12.
CHAMBERS = {
    "S": {"out": "id-senate-members.json", "label": "Senate", "seats": 35,
          "expected": 31, "fields": {"party": 0.9, "email": 0.9, "phone": 0.8, "url": 0.9}},
    "H": {"out": "id-house-members.json", "label": "House", "seats": 35, "per_district": 2,
          "expected": 63,
          "fields": {"party": 0.9, "email": 0.9, "phone": 0.8, "url": 0.9}},
}
PARTIES = {"R": "Republican", "D": "Democratic", "I": "Independent",
           "L": "Libertarian", "C": "Constitution"}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@(senate|house)\.idaho\.gov$", re.I)
BLOCK_RE = re.compile(
    r'<p><strong>([^<]+)</strong>\((\w+)\)<br />\s*<strong><a href="mailto:([^"]+)">[^<]*'
    r'</a></strong><br />\s*(?:<strong>[^<]*</strong><br />\s*)?'
    r'<a href="/legislators/membership/\?yr=(\d{4})&(?:#038;|amp;)?'
    r'district=(\d+)">District (\d+)</a><br />(.*?)</p>', re.S)
SEAT_RE = re.compile(r"^\s*House Seat ([AB])<br />")
PHONE_RE = re.compile(r'<br />\s*Statehouse\s*<a class="mob-tel" href="tel:\+?1?(\d{10})">'
                      r'<span[^>]*>[^<]*</span></a>\s*\(Session Only\)')


def sources(raw):
    return [("senate.html", PAGES["S"], {}), ("house.html", PAGES["H"], {})]


def parse(raw, notes):
    entries = []
    for chamber, name_file in (("S", "senate.html"), ("H", "house.html")):
        page = raw[name_file].decode("utf-8", "replace")
        blocks = BLOCK_RE.findall(page)
        if not blocks:
            raise SystemExit("FAIL: the %s page carries no member block in the form this "
                             "build reads; read it and update BLOCK_RE"
                             % CHAMBERS[chamber]["label"])
        rows = []
        for printed, letter, email, year, linked, district, rest in blocks:
            if linked != district:
                raise SystemExit("FAIL: a %s block links district %s and prints %s"
                                 % (CHAMBERS[chamber]["label"], linked, district))
            district = str(int(district))
            where = "%s %s" % (CHAMBERS[chamber]["label"], district)
            name = clean(printed)
            if not name or re.search(r"\d", name):
                raise SystemExit("FAIL: %s's block names %r" % (where, name))
            if letter not in PARTIES:
                raise SystemExit("FAIL: %s's party letter %r is one this builder has no "
                                 "name for" % (where, letter))
            member = {"name": name, "party": PARTIES[letter]}
            email = clean(email)
            if EMAIL_RE.match(email):
                member["email"] = email
            elif email:
                notes.append("%s: an e-mail address off the Legislature's domains was not "
                             "carried" % where)
            seat = ""
            if chamber == "H":
                m = SEAT_RE.match(rest)
                if not m:
                    raise SystemExit("FAIL: %s's block (%s) prints no House seat line"
                                     % (where, name))
                seat = m.group(1)
            phone = PHONE_RE.search(rest)
            if phone:
                digits = phone.group(1)
                add_phones(member, labelled_phones(
                    [("%s-%s-%s" % (digits[:3], digits[3:6], digits[6:]),
                      "Statehouse (session only)")], where, notes))
            member["url"] = DISTRICT_PAGE % (year, district)
            rows.append((seat, district, member))
        for seat, district, member in sorted(rows, key=lambda r: (int(r[1]), r[0])):
            if chamber == "H" and sum(1 for s, d, _ in rows if d == district and s == seat) > 1:
                raise SystemExit("FAIL: House %s Seat %s is printed twice" % (district, seat))
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
