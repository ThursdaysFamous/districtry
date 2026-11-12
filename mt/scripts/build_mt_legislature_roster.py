#!/usr/bin/env python3
"""
Build the Montana Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, so the mt-senate and
mt-house cards join a small roster instead of reaching another host at click
time.

index.html's mt-senate / mt-house layers fetch data/app/mt-senate-members.json
and mt-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
url}}, or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-mt-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

THE LEGISLATURE'S OWN SITE WAS TRIED FIRST AND CANNOT SAY WHO SITS TODAY
(Adam's choice of 2026-11-10 for every state in the state-level launch: "start
with the legislatures own sites with Open states as a fall back"). Measured
2026-11-12: the member directory at legislators.legmt.gov fills itself in from
the Legislature's own member data, and that data already carries the terms
that begin in January for members re-elected on 3 November 2026. It held 154
records for 150 seats, 58 of them Senate records for 50 seats, with end dates
of 2028 for House members and 2030 for senators beside the records of the
members they will succeed, so the sitting members cannot be told from it. The
older leg.mt.gov roster answered 403 to this project's client.

SO THE MEMBERS COME FROM OPEN STATES' EXPORT OF CURRENT LEGISLATORS,
https://data.openstates.org/people/current/mt.csv, compiled from the
Legislature's own pages. On 2026-11-12 it named all 50 senators and all 100
representatives of the 69th Legislature, the Senate President and the House
Speaker of the 2025 session among them. From each row this script carries the
name, party, district, the member's e-mail address at legmt.gov (all 150) and
the member's page on legislators.legmt.gov. Open States is not a government,
so an address at any other domain would not be carried, and nothing else in
the row is read: not the district telephone, which Open States carries for 54
members, and not the address columns.

WHEN THE NEW LEGISLATURE SITS. The 70th Legislature convenes on 4 January
2027. Open States replaces its export when it records the new members, and the
weekly refresh then opens a pull request with them; mt/WATCH.md carries the
check.

ROBOTS. data.openstates.org/robots.txt answered 403 on 2026-11-12 (an S3
"Access Denied"), which RFC 9309 2.3.1.3 reads as no robots.txt: allow. It is
read through scripts/robots_policy.py with the User-Agent the fetch sends,
before the one request this script makes.

Honesty: names are never guessed. A seat the export names nobody for gets a
record naming nobody, dated; a seat named twice stops the build.

Usage:
    python3 mt/scripts/build_mt_legislature_roster.py [output_dir]
    python3 mt/scripts/build_mt_legislature_roster.py --save DIR [output_dir]
    python3 mt/scripts/build_mt_legislature_roster.py --offline DIR [output_dir]
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


USER_AGENT = "districtry/1.0 (+https://districtry.com/mt/)"
STATE = "mt"

# 50 of 50 senators and 100 of 100 representatives were named on 2026-11-12.
CHAMBERS = {
    "S": {"out": "mt-senate-members.json", "label": "Senate", "seats": 50,
          "expected": 45, "fields": {"party": 0.9, "email": 0.9, "url": 0.9}},
    "H": {"out": "mt-house-members.json", "label": "House", "seats": 100,
          "expected": 90, "fields": {"party": 0.9, "email": 0.9, "url": 0.9}},
}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@legmt\.gov$", re.I)
PAGE_RE = re.compile(r"^https://legislators\.legmt\.gov/#/legislator/\d+$")


def member_page(link):
    """The member's page in the Legislature's directory, or None."""
    return link if PAGE_RE.match(link) else None

import csv  # noqa: E402
import io  # noqa: E402

OPENSTATES = "https://data.openstates.org/people/current/%s.csv"
PARTIES = {"Democratic": "Democratic", "Democrat": "Democratic",
           "Republican": "Republican", "Independent": "Independent",
           "Nonpartisan": "Nonpartisan", "Libertarian": "Libertarian"}
OS_CHAMBERS = {"upper": "S", "lower": "H"}


def sources(raw):
    return [("openstates.csv", OPENSTATES % STATE, {})]


def parse(raw, notes):
    text = raw["openstates.csv"].decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise SystemExit("FAIL: the Open States export answered with no rows")
    entries = []
    for row in rows:
        chamber = OS_CHAMBERS.get((row.get("current_chamber") or "").strip())
        if chamber is None:
            raise SystemExit("FAIL: a row names chamber %r" % row.get("current_chamber"))
        district = (row.get("current_district") or "").strip().lstrip("0")
        if not district.isdigit():
            raise SystemExit("FAIL: a %s row names district %r"
                             % (CHAMBERS[chamber]["label"], row.get("current_district")))
        where = "%s %s" % (CHAMBERS[chamber]["label"], district)
        name = clean(row.get("name"))
        if not name or re.search(r"\d", name) or len(name) > 60:
            raise SystemExit("FAIL: %s's row names %r" % (where, name))
        member = {"name": name}
        party = clean(row.get("current_party"))
        if party in PARTIES:
            member["party"] = PARTIES[party]
        elif party:
            raise SystemExit("FAIL: %s's party %r is one this builder has no name for"
                             % (where, party))
        email = clean(row.get("email"))
        if EMAIL_RE.match(email):
            member["email"] = email
        elif email:
            notes.append("%s: an e-mail address off the Legislature's own domain was "
                         "not carried" % where)
        for link in (row.get("links") or "").split(";"):
            page = member_page(link.strip())
            if page:
                member["url"] = page
                break
        else:
            notes.append("%s: no member page on the Legislature's own site" % where)
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
