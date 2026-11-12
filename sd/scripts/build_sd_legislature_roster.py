#!/usr/bin/env python3
"""
Build the South Dakota Senate and House of Representatives rosters (district
-> current officeholders) as same-origin app-data files, from the South Dakota
Legislature's own data service at sdlegislature.gov, so the sd-senate /
sd-house cards join a small roster instead of reaching another host at click
time.

index.html's sd-senate / sd-house layers fetch data/app/sd-senate-members.json
and sd-house-members.json lazily on first click and join them to the
pre-built legislative geometry by district. This script writes the two rosters
shaped for the registerIlgaChamber factory. A weekly GitHub Action
(.github/workflows/update-sd-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

TWO REPRESENTATIVES FROM MOST DISTRICTS, ONE FROM FOUR. South Dakota elects
one senator from each of its 35 districts. Thirty-three districts elect two
representatives at large; districts 26 and 28 are each split into two House
districts (26A and 26B, 28A and 28B) electing one representative each. The
House roster is therefore keyed by House district, the way TIGERweb's lower
chamber layer names them ("19", "26A"), and every record carries `seats` and
`members` (the shape New Hampshire's and Maryland's House rosters use). That
is 70 representatives in 37 House districts.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

sdlegislature.gov/api/Sessions lists every session; this script reads the
regular session with the latest start date on or before the day of the run,
so members elected in November are not shown before the session they are
seated for. On 2026-11-12 that was the 2026 session (SessionId 71), and
sdlegislature.gov/api/SessionMembers/Session/71 listed 35 senators and 70
representatives, every seat of both chambers, with MemberType ("S" or "H"),
District ("01", "26A"), Name ("Andera, Bobbi L.", printed here first name
first), PartyName and SessionMemberId, the number in the member's page
address (sdlegislature.gov/Legislators/Profile/<id>/Detail, read from the
site's own route table). The list carries no e-mail address or telephone:
every contact field was empty on all 105 records, so the card links the
member's page.

WHAT IS NEVER READ. Each record also has fields for the member's home address,
city and ZIP code; none of them is read, and no part of them ships.

ROBOTS. sdlegislature.gov/robots.txt (325 bytes) was read on 2026-11-12 and no
rule in it matches /api/. It is read through scripts/robots_policy.py with the
User-Agent the fetches send, before the first of the two fetches this script
makes.

Honesty: names are never guessed. A seat the list names nobody for gets a
dated record saying how many members were listed; a member listed twice, or
more members than a district elects, stops the build.

Usage:
    python3 sd/scripts/build_sd_legislature_roster.py [output_dir]
    python3 sd/scripts/build_sd_legislature_roster.py --save DIR [output_dir]
    python3 sd/scripts/build_sd_legislature_roster.py --offline DIR [output_dir]
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


USER_AGENT = "districtry/1.0 (+https://districtry.com/sd/)"
SESSIONS = "https://sdlegislature.gov/api/Sessions"
MEMBERS = "https://sdlegislature.gov/api/SessionMembers/Session/%d"
PAGE = "https://sdlegislature.gov/Legislators/Profile/%d/Detail"

# Thirty-three House districts elect two representatives; the four halves of
# districts 26 and 28 elect one each.
HOUSE_DISTRICTS = {}
for _d in range(1, 36):
    if _d in (26, 28):
        HOUSE_DISTRICTS["%dA" % _d] = 1
        HOUSE_DISTRICTS["%dB" % _d] = 1
    else:
        HOUSE_DISTRICTS[str(_d)] = 2

# 35 of 35 senators and 70 of 70 representatives were listed on 2026-11-12.
CHAMBERS = {
    "S": {"out": "sd-senate-members.json", "label": "Senate", "seats": 35,
          "expected": 32, "fields": {"party": 0.9, "url": 0.9}},
    "H": {"out": "sd-house-members.json", "label": "House", "districts": HOUSE_DISTRICTS,
          "expected": 63, "fields": {"party": 0.9, "url": 0.9}},
}
PARTIES = {"Republican": "Republican", "Democratic": "Democratic",
           "Democrat": "Democratic", "Independent": "Independent",
           "Libertarian": "Libertarian"}
DISTRICT_RE = re.compile(r"^0*(\d{1,2})([AB]?)$")


def session_id(raw, quiet=False):
    """The regular session with the latest start date on or before today."""
    today = datetime.date.today().isoformat()
    best = None
    for s in json.loads(raw["sessions.json"].decode("utf-8-sig")):
        start = str(s.get("StartDate") or "")[:10]
        if s.get("SpecialSession") or not start or start > today:
            continue
        if best is None or start > best[0]:
            best = (start, int(s["SessionId"]))
    if best is None:
        raise SystemExit("FAIL: no regular session has started by %s" % today)
    if not quiet:
        print("session %d (started %s)" % (best[1], best[0]), file=sys.stderr)
    return best[1]


def sources(raw):
    yield "sessions.json", SESSIONS, {}
    yield "members.json", MEMBERS % session_id(raw), {}


def first_name_first(printed):
    """"Andera, Bobbi L." -> "Bobbi L. Andera"; a suffix after a second comma
    ("Smith, John, Jr.") stays at the end."""
    parts = [p.strip() for p in printed.split(",")]
    if len(parts) == 2 and all(parts):
        return "%s %s" % (parts[1], parts[0])
    if len(parts) == 3 and all(parts):
        return "%s %s %s" % (parts[1], parts[0], parts[2])
    return printed


def parse(raw, notes):
    sid = session_id(raw, quiet=True)
    entries = []
    for rec in json.loads(raw["members.json"].decode("utf-8-sig")):
        if rec.get("InactiveDate"):
            continue
        if int(rec.get("SessionId") or 0) != sid:
            raise SystemExit("FAIL: a member record belongs to session %r, not %d"
                             % (rec.get("SessionId"), sid))
        chamber = str(rec.get("MemberType") or "").strip()
        if chamber not in CHAMBERS:
            raise SystemExit("FAIL: a record names member type %r" % chamber)
        m = DISTRICT_RE.match(str(rec.get("District") or "").strip())
        if not m:
            raise SystemExit("FAIL: a record names district %r" % rec.get("District"))
        district = m.group(1) + m.group(2)
        if chamber == "S" and m.group(2):
            raise SystemExit("FAIL: a senator's district reads %r" % rec.get("District"))
        where = "%s %s" % (CHAMBERS[chamber]["label"], district)
        name = first_name_first(clean(rec.get("Name")))
        if not name or re.search(r"\d", name):
            raise SystemExit("FAIL: %s's record names %r" % (where, name))
        member = {"name": name}
        party = clean(rec.get("PartyName"))
        if party in PARTIES:
            member["party"] = PARTIES[party]
        elif party:
            raise SystemExit("FAIL: %s's party %r is one this builder has no name for"
                             % (where, party))
        try:
            member["url"] = PAGE % int(rec.get("SessionMemberId"))
        except (TypeError, ValueError):
            notes.append("%s: member id %r, no page linked" % (where, rec.get("SessionMemberId")))
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
