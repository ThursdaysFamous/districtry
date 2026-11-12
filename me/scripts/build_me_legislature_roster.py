#!/usr/bin/env python3
"""
Build the Maine Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from the Maine
Legislature's own pages at legislature.maine.gov, so the me-senate / me-house
cards join a small roster instead of reaching another host at click time.

index.html's me-senate / me-house layers fetch data/app/me-senate-members.json
and me-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
phone, url}}, or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-me-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The House. legislature.maine.gov/house/Home/ExportActiveMembers?format=csv is
the House's own export of its sitting members: Name, Party ("Democrat",
"Republican" or "Unenrolled", Maine's word for a member enrolled in no party),
District, Email at legislature.maine.gov and Phone, among other columns. That
day it held 150 members for 151 districts; District 46 had no row, so its
record names nobody. The export links no member page, so the card links the
House's member list.

The Senate. legislature.maine.gov/senate/senators/9536 is the Senate's page
"Senators", listing each senator as "<name> (<party letter>-<county>)" and
linking the senator's own page (legislature.maine.gov/district<N>); that day
it listed 35 senators, one for each district. This script reads that list and
then each senator's page, which prints "Senate District <N>" and the
senator's e-mail address at legislature.maine.gov; a page whose district
differs from the list's stops the build. The pages' "State House" telephone is
the Senate's office line, printed for many senators, so it is not carried.

THE TELEPHONE SHIPS AS PRINTED. The House export prints one number beside
each representative and labels none, so the card prints the number without a
label. Under the fleet's rule of 2026-10-17 a number a government source prints
beside an official ships on that official.

WHAT IS NEVER READ. The House export also carries each member's residence,
city and ZIP code; none of them is read, and no part of them ships. The
senators' pages print a mailing address at the State House, which is not read
either, nor are committees or biographies.

TERMS. Maine's legislators elected in November take office in early December.
The export and the Senate page list the sitting members, and the weekly
refresh carries the new ones when the Legislature posts them.

ROBOTS. legislature.maine.gov/robots.txt (205 bytes) was read on 2026-11-12 and
no rule in it matches /house/ or /senate/ or the senators' pages, and it states
no Crawl-delay. It is read through scripts/robots_policy.py with the
User-Agent the fetches send, before the first fetch, and the host is paced at
one request a second.

Honesty: names are never guessed. A seat no source lists gets a record naming
nobody, dated; a seat listed twice stops the build.

Usage:
    python3 me/scripts/build_me_legislature_roster.py [output_dir]
    python3 me/scripts/build_me_legislature_roster.py --save DIR [output_dir]
    python3 me/scripts/build_me_legislature_roster.py --offline DIR [output_dir]
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


import csv  # noqa: E402
import io  # noqa: E402

USER_AGENT = "districtry/1.0 (+https://districtry.com/me/)"
HOST = "https://legislature.maine.gov"
HOUSE_EXPORT = HOST + "/house/Home/ExportActiveMembers?format=csv"
SENATORS = HOST + "/senate/senators/9536"
PAUSE = 1.0  # seconds between the senators' pages; robots.txt states no delay

# 35 of 35 senators and 150 of 151 representatives were listed on 2026-11-12.
CHAMBERS = {
    "S": {"out": "me-senate-members.json", "label": "Senate", "seats": 35,
          "expected": 31, "fields": {"party": 0.9, "email": 0.9, "url": 0.9}},
    "H": {"out": "me-house-members.json", "label": "House", "seats": 151,
          "expected": 136, "fields": {"party": 0.9, "email": 0.9, "phone": 0.8}},
}
PARTIES = {"D": "Democratic", "Democrat": "Democratic", "Democratic": "Democratic",
           "R": "Republican", "Republican": "Republican",
           "I": "Independent", "Independent": "Independent",
           "U": "Unenrolled", "Unenrolled": "Unenrolled",
           "G": "Green Independent", "Green Independent": "Green Independent",
           "L": "Libertarian", "Libertarian": "Libertarian"}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@legislature\.maine\.gov$", re.I)
SENATOR_RE = re.compile(
    r'<a href="/[dD]istrict(\d+)">([^<]+)</a>(?:\s|&nbsp;)*\(([A-Z])-([^)]+)\)')


def senators(raw):
    """[(district, name, party letter)] from the Senate's list."""
    page = raw["senators.html"].decode("utf-8", "replace")
    rows = [(int(d), clean(n), p) for d, n, p, _county in SENATOR_RE.findall(page)]
    if not rows:
        raise SystemExit("FAIL: the Senate's page lists no senators in the form "
                         "this build reads; read it and update SENATOR_RE")
    return rows


def sources(raw):
    yield "house.csv", HOUSE_EXPORT, {}
    yield "senators.html", SENATORS, {}
    for district, _name, _party in senators(raw):
        yield "senator-%d.html" % district, "%s/district%d" % (HOST, district), {}


def party_of(printed, where):
    party = clean(printed)
    if not party:
        return None
    if party not in PARTIES:
        raise SystemExit("FAIL: %s's party %r is one this builder has no name for"
                         % (where, party))
    return PARTIES[party]


def parse_house(raw, notes):
    entries = []
    rows = list(csv.DictReader(io.StringIO(raw["house.csv"].decode("utf-8-sig"))))
    for col in ("Name", "Party", "District", "Email", "Phone"):
        if rows and col not in rows[0]:
            raise SystemExit("FAIL: the House export has no %s column" % col)
    for rec in rows:
        try:
            district = str(int(clean(rec.get("District"))))
        except ValueError:
            raise SystemExit("FAIL: a House row names district %r" % rec.get("District"))
        where = "House %s" % district
        name = clean(rec.get("Name"))
        if not name or re.search(r"\d", name):
            raise SystemExit("FAIL: %s's row names %r" % (where, name))
        member = {"name": name}
        party = party_of(rec.get("Party"), where)
        if party:
            member["party"] = party
        email = clean(rec.get("Email"))
        if EMAIL_RE.match(email):
            member["email"] = email
        elif email:
            notes.append("%s: an e-mail address off legislature.maine.gov was not carried"
                         % where)
        add_phones(member, labelled_phones([(rec.get("Phone"), "")], where, notes))
        entries.append(("H", district, member))
    return entries


def labelled_email(page):
    """The value on the first "Email:" line after the page's heading."""
    start = page.find("<h1")
    body = re.sub(r"<script.*?</script>", "", page[start:start + 8000], flags=re.S)
    lines = [ln.strip() for ln in html.unescape(re.sub(r"<[^>]+>", "\n", body)).split("\n")]
    lines = [ln for ln in lines if ln and ln != ":"]
    for i, ln in enumerate(lines[:-1]):
        if ln.rstrip(":").strip() == "Email":
            return lines[i + 1].lstrip(":").strip()
    return None


def parse_senate(raw, notes):
    entries = []
    for district, name, letter in senators(raw):
        where = "Senate %d" % district
        page = raw["senator-%d.html" % district].decode("utf-8", "replace")
        said = set(int(d) for d in re.findall(r"Senate District\s*(\d+)", page))
        if said != {district}:
            raise SystemExit("FAIL: %s's page names Senate district(s) %s"
                             % (where, sorted(said)))
        # The page heads itself with a shorter form of the name ("Sen. Joe
        # Baldacci" for the list's "Joseph M. Baldacci"), so the surname is
        # what must agree; the list's form is the one shipped.
        heading = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
        surname = name.split()[-1]
        if not heading or surname not in clean(heading.group(1)):
            raise SystemExit("FAIL: %s's page does not name %s in its heading"
                             % (where, surname))
        member = {"name": name}
        party = party_of(letter, where)
        if party:
            member["party"] = party
        # The address on the page's own "Email:" line; about a third of the
        # pages print it as text rather than as a mailto link.
        email = labelled_email(page)
        if EMAIL_RE.match(email or ""):
            member["email"] = email
        else:
            notes.append("%s: the page's Email line reads %r, not carried"
                         % (where, email))
        member["url"] = "%s/district%d" % (HOST, district)
        entries.append(("S", str(district), member))
    return entries


def parse(raw, notes):
    return parse_senate(raw, notes) + parse_house(raw, notes)


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
