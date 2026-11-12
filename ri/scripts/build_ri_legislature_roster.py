#!/usr/bin/env python3
"""
Build the Rhode Island Senate and House of Representatives rosters (district
-> current officeholder) as same-origin app-data files, from the Rhode Island
General Assembly's own member list at rilegislature.gov, so the ri-senate /
ri-house cards join a small roster instead of reaching another host at click
time.

index.html's ri-senate / ri-house layers fetch data/app/ri-senate-members.json
and ri-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
phone, url}}, or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-ri-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The Senate's and House's member pages (rilegislature.gov/senators/default.aspx
and /representatives/default.aspx) fill themselves in after they open, from
one SharePoint list, "legislationInformation", which each page asks for with a
SOAP GetListItems call to rilegislature.gov/_vti_bin/Lists.asmx (rowLimit 300).
This script sends the same request the pages send. That day the list held 124
rows, 112 of them marked active (ows_ActiveFlag 1): 38 senators, every Senate
seat, and 74 representatives. House District 31 had no active row, so its
record names nobody. Each row carries the member's name, chamber, district
("4.00000000000000"), party ("Democrat", "Republican" or "Independent"), an
e-mail address at rilegislature.gov (all 112), a telephone (99 of 112) and the
member's biography page on rilegislature.gov.

THE TELEPHONE SHIPS AS PRINTED. The list prints one number beside each member
and labels none, so the card prints the number without a label. Under the
fleet's rule of 2026-10-17 a number a government source prints beside an
official ships on that official.

WHAT IS NEVER READ. Each row also carries ows_city, the member's town, which
the pages print under the name; it is never read and does not ship.
Photographs and leadership titles are not read either.

ROBOTS. rilegislature.gov/robots.txt (837 bytes) was read on 2026-11-12 and no
rule in it matches /_vti_bin/. It is read through scripts/robots_policy.py
with the User-Agent the fetch sends, before the one request this script makes.

Honesty: names are never guessed. A seat the list carries no active row for
gets a record naming nobody, dated; a seat carried twice stops the build.

Usage:
    python3 ri/scripts/build_ri_legislature_roster.py [output_dir]
    python3 ri/scripts/build_ri_legislature_roster.py --save DIR [output_dir]
    python3 ri/scripts/build_ri_legislature_roster.py --offline DIR [output_dir]
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


import xml.etree.ElementTree as ET  # noqa: E402

USER_AGENT = "districtry/1.0 (+https://districtry.com/ri/)"
LISTS = "https://www.rilegislature.gov/_vti_bin/Lists.asmx"
# The request the member pages send, word for word.
ENVELOPE = (
    "<soap:Envelope xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' "
    "xmlns:xsd='http://www.w3.org/2001/XMLSchema' "
    "xmlns:soap='http://schemas.xmlsoap.org/soap/envelope/'>"
    "<soap:Body>"
    "<GetListItems xmlns='http://schemas.microsoft.com/sharepoint/soap/'>"
    "<listName>legislationInformation</listName>"
    "<rowLimit>300</rowLimit>"
    "</GetListItems>"
    "</soap:Body>"
    "</soap:Envelope>")
SOAP_HEADERS = {"Content-Type": 'text/xml; charset="utf-8"'}

# 38 of 38 senators and 74 of 75 representatives were listed on 2026-11-12.
CHAMBERS = {
    "Senate": {"out": "ri-senate-members.json", "label": "Senate", "seats": 38,
               "expected": 34, "fields": {"party": 0.9, "email": 0.9, "phone": 0.7}},
    "House": {"out": "ri-house-members.json", "label": "House", "seats": 75,
              "expected": 67, "fields": {"party": 0.9, "email": 0.9, "phone": 0.7}},
}
PARTIES = {"Democrat": "Democratic", "Democratic": "Democratic",
           "Republican": "Republican", "Independent": "Independent"}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@rilegislature\.gov$", re.I)
PAGE_RE = re.compile(r"^https://www\.rilegislature\.gov/(senators|representatives)/[^\s,]+$", re.I)


def sources(raw):
    return [("list.xml", LISTS, {"data": ENVELOPE.encode("utf-8"), "headers": SOAP_HEADERS})]


def parse(raw, notes):
    root = ET.fromstring(raw["list.xml"])
    rows = [e.attrib for e in root.iter() if e.tag.endswith("}row") or e.tag == "row"]
    if not rows:
        raise SystemExit("FAIL: the member list answered with no rows")
    entries = []
    for rec in rows:
        if rec.get("ows_ActiveFlag") != "1":
            continue
        chamber = clean(rec.get("ows_chamber"))
        if chamber not in CHAMBERS:
            raise SystemExit("FAIL: an active row names chamber %r" % chamber)
        try:
            number = float(rec.get("ows_district") or "")
        except ValueError:
            raise SystemExit("FAIL: an active row names district %r" % rec.get("ows_district"))
        if number != int(number):
            raise SystemExit("FAIL: an active row names district %r" % rec.get("ows_district"))
        district = str(int(number))
        where = "%s %s" % (chamber, district)
        name = clean(rec.get("ows_legislator_name"))
        if not name or re.search(r"\d", name):
            raise SystemExit("FAIL: %s's row names %r" % (where, name))
        member = {"name": name}
        party = clean(rec.get("ows_political_party"))
        if party in PARTIES:
            member["party"] = PARTIES[party]
        elif party:
            raise SystemExit("FAIL: %s's party %r is one this builder has no name for"
                             % (where, party))
        email = clean(rec.get("ows_email"))
        if EMAIL_RE.match(email):
            member["email"] = email
        elif email:
            notes.append("%s: an e-mail address off rilegislature.gov was not carried" % where)
        add_phones(member, labelled_phones([(rec.get("ows_phone"), "")], where, notes))
        page = clean((rec.get("ows_legislator_bioURL") or "").split(",")[0])
        if PAGE_RE.match(page):
            member["url"] = page
        elif page:
            notes.append("%s: biography page %r not linked" % (where, page))
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
