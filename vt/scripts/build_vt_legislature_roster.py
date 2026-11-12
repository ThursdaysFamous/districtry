#!/usr/bin/env python3
"""
Build the Vermont Senate and House of Representatives rosters (district ->
current officeholders) as same-origin app-data files, from the Vermont
Legislature's own member lists at legislature.vermont.gov, so the vt-senate /
vt-house cards join a small roster instead of reaching another host at click
time.

index.html's vt-senate / vt-house layers fetch data/app/vt-senate-members.json
and vt-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district name. This script writes the two rosters
shaped for the registerIlgaChamber factory. A weekly GitHub Action
(.github/workflows/update-vt-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

EVERY VERMONT DISTRICT IS NAMED, AND MOST ELECT MORE THAN ONE MEMBER. The
Senate's 30 senators are elected from 16 districts electing one to three each;
the House's 150 representatives from 109 districts electing one or two (68
one-seat and 41 two-seat districts). Both rosters are keyed by the district's
name as TIGERweb's state legislative layers spell it (BASENAME: "Chittenden
Central", "Addison-1"), and every record carries `seats` and `members`, the
shape New Hampshire's House roster uses. The seat plan below is the 2022
reapportionment as the Legislature's own lists showed it on 2026-11-12, when
every seat of both chambers was filled: the active members per district summed
to 30 and 150, and the House names matched TIGERweb's 109 exactly. Three Senate
districts are spelled differently by the two publishers ("Chittenden-Central",
"Chittenden-North" and "Chittenden-Southeast" on the Legislature's list); the
table SENATE_SPELLING maps them, and any other name the build has not seen
stops it.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

legislature.vermont.gov/people/all/<year>/Senate and /House are the
Legislature's member lists; each fills its table from
legislature.vermont.gov/people/loadAll/<year>/Senate (or /House), which this
script reads. The year is the calendar year of the run; the biennium's
members elected in November take office in January, when the next year's list
holds them. That day the 2026 lists carried 32 Senate and 158 House rows, of
which 30 and 150 had no TerminationReason (the others read "Resigned ..."),
each with FirstName, LastName, NameSuffix, District, Party and PersonID, the
number in the member's page address (legislature.vermont.gov/people/single/
<year>/<PersonID>). The party is shipped as the list prints it, including the
fusion labels ("Democrat/Progressive", "Republican/Democrat").

WHAT IS NOT CARRIED, AND WHY. The list's rows also carry e-mail and telephone
fields, and they are not what the member's own page prints: on 2026-11-12 the
page for PersonID 15769 printed an e-mail address at leg.state.vt.us and a
telephone, and neither matched any e-mail or telephone field of that member's
row in the list. So no e-mail address or telephone is read from the list, and
the card links the member's page, where the Legislature prints them. Each row
also carries the member's home, work and mailing addresses, town and ZIP
codes; none of them is read, and no part of them ships.

ROBOTS. legislature.vermont.gov/robots.txt (236 bytes) was read on 2026-11-12:
no rule in it matches /people/, and it states a Crawl-delay of 30, which the
shared HostPacer honours between the two fetches this script makes. It is read
through scripts/robots_policy.py with the User-Agent the fetches send.

Honesty: names are never guessed. A district listing fewer members than it
elects gets a dated record saying how many were listed; a district the build
does not know, or more members than a district elects, stops the build.

Usage:
    python3 vt/scripts/build_vt_legislature_roster.py [output_dir]
    python3 vt/scripts/build_vt_legislature_roster.py --save DIR [output_dir]
    python3 vt/scripts/build_vt_legislature_roster.py --offline DIR [output_dir]
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


USER_AGENT = "districtry/1.0 (+https://districtry.com/vt/)"
LIST = "https://legislature.vermont.gov/people/loadAll/%d/%s"
PAGE = "https://legislature.vermont.gov/people/single/%d/%d"

SENATE_DISTRICTS = {
    "Addison": 2, "Bennington": 2, "Caledonia": 1, "Chittenden Central": 3,
    "Chittenden North": 1, "Chittenden South East": 3, "Essex": 1, "Franklin": 2,
    "Grand Isle": 1, "Lamoille": 1, "Orange": 1, "Orleans": 1, "Rutland": 3,
    "Washington": 3, "Windham": 2, "Windsor": 3,
}
SENATE_SPELLING = {
    "Chittenden-Central": "Chittenden Central",
    "Chittenden-North": "Chittenden North",
    "Chittenden-Southeast": "Chittenden South East",
}
HOUSE_TWO_SEAT = (
    "Addison-1", "Addison-3", "Addison-4", "Bennington-2", "Bennington-4",
    "Bennington-5", "Caledonia-3", "Caledonia-Essex", "Chittenden-13",
    "Chittenden-14", "Chittenden-15", "Chittenden-16", "Chittenden-18",
    "Chittenden-19", "Chittenden-2", "Chittenden-20", "Chittenden-21",
    "Chittenden-22", "Chittenden-23", "Chittenden-3", "Chittenden-Franklin",
    "Franklin-1", "Franklin-4", "Franklin-5", "Grand Isle-Chittenden",
    "Lamoille-2", "Lamoille-Washington", "Orange-Washington-Addison",
    "Orleans-Lamoille", "Rutland-2", "Washington-1", "Washington-2",
    "Washington-3", "Washington-4", "Washington-Chittenden", "Washington-Orange",
    "Windham-3", "Windsor-1", "Windsor-3", "Windsor-6", "Windsor-Orange-2",
)
HOUSE_ONE_SEAT = (
    "Addison-2", "Addison-5", "Addison-Rutland", "Bennington-1", "Bennington-3",
    "Bennington-Rutland", "Caledonia-1", "Caledonia-2", "Caledonia-Washington",
    "Chittenden-1", "Chittenden-10", "Chittenden-11", "Chittenden-12",
    "Chittenden-17", "Chittenden-24", "Chittenden-25", "Chittenden-4",
    "Chittenden-5", "Chittenden-6", "Chittenden-7", "Chittenden-8", "Chittenden-9",
    "Essex-Caledonia", "Essex-Orleans", "Franklin-2", "Franklin-3", "Franklin-6",
    "Franklin-7", "Franklin-8", "Lamoille-1", "Lamoille-3", "Orange-1", "Orange-2",
    "Orange-3", "Orange-Caledonia", "Orleans-1", "Orleans-2", "Orleans-3",
    "Orleans-4", "Rutland-1", "Rutland-10", "Rutland-11", "Rutland-3", "Rutland-4",
    "Rutland-5", "Rutland-6", "Rutland-7", "Rutland-8", "Rutland-9",
    "Rutland-Bennington", "Rutland-Windsor", "Washington-5", "Washington-6",
    "Windham-1", "Windham-2", "Windham-4", "Windham-5", "Windham-6", "Windham-7",
    "Windham-8", "Windham-9", "Windham-Windsor-Bennington", "Windsor-2",
    "Windsor-4", "Windsor-5", "Windsor-Addison", "Windsor-Orange-1",
    "Windsor-Windham",
)
HOUSE_DISTRICTS = dict([(d, 2) for d in HOUSE_TWO_SEAT] + [(d, 1) for d in HOUSE_ONE_SEAT])

# 30 of 30 senators and 150 of 150 representatives were listed on 2026-11-12.
CHAMBERS = {
    "Senate": {"out": "vt-senate-members.json", "label": "Senate",
               "districts": SENATE_DISTRICTS, "expected": 27,
               "fields": {"party": 0.9, "url": 0.9}},
    "House": {"out": "vt-house-members.json", "label": "House",
              "districts": HOUSE_DISTRICTS, "expected": 135,
              "fields": {"party": 0.9, "url": 0.9}},
}


def year():
    return datetime.date.today().year


def sources(raw):
    return [("senate.json", LIST % (year(), "Senate"), {}),
            ("house.json", LIST % (year(), "House"), {})]


def district_key(chamber, printed):
    name = clean(printed)
    if name.endswith(" District"):
        name = name[:-len(" District")]
    if chamber == "Senate":
        name = SENATE_SPELLING.get(name, name)
    if name not in CHAMBERS[chamber]["districts"]:
        raise SystemExit("FAIL: the %s list names district %r, which this build does "
                         "not know; read the Legislature's district list and update "
                         "the seat plan" % (chamber, printed))
    return name


def parse(raw, notes):
    entries = []
    for name, chamber in (("senate.json", "Senate"), ("house.json", "House")):
        rows = json.loads(raw[name].decode("utf-8-sig")).get("data")
        if not isinstance(rows, list):
            raise SystemExit("FAIL: the %s list is not a list of members" % chamber)
        for rec in rows:
            if clean(rec.get("TerminationReason")):
                continue
            district = district_key(chamber, rec.get("District"))
            where = "%s %s" % (chamber, district)
            parts = [clean(rec.get("FirstName")), clean(rec.get("LastName"))]
            suffix = clean(rec.get("NameSuffix"))
            full = " ".join(p for p in parts if p) + ((" " + suffix) if suffix else "")
            if not all(parts) or re.search(r"\d", full):
                raise SystemExit("FAIL: %s's row names %r" % (where, full))
            member = {"name": full}
            party = clean(rec.get("Party"))
            if party:
                member["party"] = party
            try:
                member["url"] = PAGE % (year(), int(rec.get("PersonID")))
            except (TypeError, ValueError):
                notes.append("%s: member id %r, no page linked" % (where, rec.get("PersonID")))
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
