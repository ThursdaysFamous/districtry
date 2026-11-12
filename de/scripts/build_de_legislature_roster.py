#!/usr/bin/env python3
"""
Build the Delaware Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from the Delaware General
Assembly's own member lists at legis.delaware.gov, so the de-senate / de-house
cards join a small roster instead of reaching another host at click time.

index.html's de-senate / de-house layers fetch data/app/de-senate-members.json
and de-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, url}},
or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-de-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The General Assembly's Senate and House member pages
(legis.delaware.gov/Chambers/Senate/AssemblyMembers and
/Chambers/House/AssemblyMembers) draw their tables from /json/Senate/GetSenators
and /json/House/GetRepresentatives, which each page names as its table's read
address and asks with a POST carrying the table's paging fields; this script
sends what the page sends and asks for 100 rows. (The page address itself
answers a POST with the page's HTML, not the table.) That day the Senate list carried 21 rows and
the House list 41, one per district, each with DistrictNumber, PersonFullName,
PartyCode ("D" or "R") and PersonId. A district nobody holds would come back
with no PersonId, which the page itself prints as "Vacant".

THE MEMBER PAGE IS THE GENERAL ASSEMBLY'S OWN. The list's own link for each
member (LegislatorDetailLink) goes to the member's party caucus site
(senatedems.delaware.gov, senategop.delaware.gov, housedems.delaware.gov or
housegop.delaware.gov), which is a partisan site and not a government
publication, so it is never linked. The card links
legis.delaware.gov/LegislatorDetail?personId=<PersonId>, which redirects to
the member's page on the General Assembly's own site (measured 2026-11-12:
personId 24715 answered with "Senator Daniel Cruce (D)"). The lists carry no
e-mail address or telephone, so the card links that page for them.

ROBOTS. legis.delaware.gov has no robots.txt: on 2026-11-12 the address
answered with the site's own HTML page, which RFC 9309 reads as no restriction.
It is read through scripts/robots_policy.py with the User-Agent the fetches
send, before the first of the two fetches this script makes.

Honesty: names are never guessed. A district the list names nobody for gets a
record naming nobody, dated; a district listed twice stops the build.

Usage:
    python3 de/scripts/build_de_legislature_roster.py [output_dir]
    python3 de/scripts/build_de_legislature_roster.py --save DIR [output_dir]
    python3 de/scripts/build_de_legislature_roster.py --offline DIR [output_dir]
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


USER_AGENT = "districtry/1.0 (+https://districtry.com/de/)"
LIST = "https://legis.delaware.gov/json/%s"
PAGE = "https://legis.delaware.gov/LegislatorDetail?personId=%d"
FORM = {"sort": "DistrictNumber-asc", "page": "1", "pageSize": "100",
        "group": "", "filter": ""}
FORM_HEADERS = {"X-Requested-With": "XMLHttpRequest"}

# 21 of 21 senators and 41 of 41 representatives were listed on 2026-11-12.
CHAMBERS = {
    "S": {"out": "de-senate-members.json", "label": "Senate", "seats": 21,
          "expected": 19, "fields": {"party": 0.9, "url": 0.9}},
    "H": {"out": "de-house-members.json", "label": "House", "seats": 41,
          "expected": 37, "fields": {"party": 0.9, "url": 0.9}},
}
PARTIES = {"R": "Republican", "D": "Democratic", "I": "Independent"}
CHAMBER_IDS = {"S": 1, "H": 2}


def sources(raw):
    return [("senate.json", LIST % "Senate/GetSenators", {"data": FORM, "headers": FORM_HEADERS}),
            ("house.json", LIST % "House/GetRepresentatives", {"data": FORM, "headers": FORM_HEADERS})]


def parse(raw, notes):
    entries = []
    for name, chamber in (("senate.json", "S"), ("house.json", "H")):
        body = json.loads(raw[name].decode("utf-8-sig"))
        if body.get("Errors"):
            raise SystemExit("FAIL: the %s list answered with errors: %r"
                             % (chamber, body.get("Errors")))
        rows = body.get("Data") or []
        if int(body.get("Total") or 0) > len(rows):
            raise SystemExit("FAIL: the %s list holds %s rows and sent %d"
                             % (chamber, body.get("Total"), len(rows)))
        for rec in rows:
            if int(rec.get("ChamberId") or 0) != CHAMBER_IDS[chamber]:
                raise SystemExit("FAIL: a %s row names chamber %r"
                                 % (chamber, rec.get("ChamberId")))
            try:
                district = str(int(rec.get("DistrictNumber")))
            except (TypeError, ValueError):
                raise SystemExit("FAIL: a %s row names district %r"
                                 % (chamber, rec.get("DistrictNumber")))
            where = "%s %s" % (CHAMBERS[chamber]["label"], district)
            if rec.get("PersonId") is None:
                notes.append("%s: the list prints the seat as vacant" % where)
                continue
            name_ = clean(rec.get("PersonFullName"))
            if not name_ or re.search(r"\d", name_):
                raise SystemExit("FAIL: %s's row names %r" % (where, name_))
            member = {"name": name_}
            party = str(rec.get("PartyCode") or "").strip()
            if party in PARTIES:
                member["party"] = PARTIES[party]
            elif party:
                raise SystemExit("FAIL: %s's party letter %r is one this builder has "
                                 "no name for" % (where, party))
            member["url"] = PAGE % int(rec["PersonId"])
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
