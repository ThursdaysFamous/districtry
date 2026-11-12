#!/usr/bin/env python3
"""
Build the Utah Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from the Utah
Legislature's own member feed at le.utah.gov, so the ut-senate / ut-house
cards join a small roster instead of reaching another host at click time.

index.html's ut-senate / ut-house layers fetch data/app/ut-senate-members.json
and ut-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
phone, phonesExtra, url}}, or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-ut-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

le.utah.gov/data/legislators.json is the feed the Senate's and House's own
member pages read: one record per sitting member, with formatName, house ("S"
or "H"), district, party ("R", "D", or "F"), email at le.utah.gov, and up to
three telephones (cell, workPhone, homePhone). That day it carried 29
senators (every seat) and 74 representatives; House District 16 had no
record. The party letter F is the Forward Party: the Senate's member page
prints "Forward Party" for the one senator carrying it (Emily Buss, District
11). The member pages are senate.utah.gov/sen/<id>/ and house.utleg.gov/rep/
<id>/ (house.utah.gov/rep/<id>/ redirects there).

THE TELEPHONES ARE THE MEMBER'S OWN AND SHIP WITH THEIR LABELS. The feed
prints each member's cell, work and home numbers beside the member, and under
the fleet's rule of 2026-10-17 a number a government source prints beside an
official ships on that official with the label the source gives it. One
number printed under several labels ships once, carrying every label.

WHAT IS NEVER READ. Each record also carries an `address`, which is the
member's home or post-office box ("PO Box 357, Brigham City, UT, 84302");
it is never read, and no part of it ships. Biographies, professions,
social-media handles and committee lists are not read either.

ROBOTS. le.utah.gov/robots.txt was read on 2026-11-12: its `*` group disallows
/ASP/, /asp/, /JSP/, /RSS/, /includes/, /templates/ and three /lfa/ paths and
states a Crawl-delay of 10, which the shared HostPacer honours; /data/ is not
disallowed. It is read through scripts/robots_policy.py with the User-Agent
the fetch sends, before the one fetch this script makes.

Honesty: names are never guessed. A seat the feed carries no record for gets a
record naming nobody, dated; a seat carried twice stops the build.

Usage:
    python3 ut/scripts/build_ut_legislature_roster.py [output_dir]
    python3 ut/scripts/build_ut_legislature_roster.py --save DIR [output_dir]
    python3 ut/scripts/build_ut_legislature_roster.py --offline DIR [output_dir]
"""

import datetime
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/ut/)"
ATTEMPTS = 4
RETRY_SECONDS = 20.0
FEED = "https://le.utah.gov/data/legislators.json"

# 29 of 29 senators and 74 of 75 representatives were listed on 2026-11-12.
CHAMBERS = {
    "S": {"out": "ut-senate-members.json", "label": "Senate", "seats": 29,
          "expected": 26, "page": "https://senate.utah.gov/sen/%s/",
          "fields": {"party": 0.9, "email": 0.9}},
    "H": {"out": "ut-house-members.json", "label": "House of Representatives",
          "seats": 75, "expected": 67, "page": "https://house.utleg.gov/rep/%s/",
          "fields": {"party": 0.9, "email": 0.9}},
}

PARTIES = {"R": "Republican", "D": "Democratic", "F": "Forward Party"}
PHONE_FIELDS = (("workPhone", "work"), ("cell", "cell"), ("homePhone", "home"))

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

ID_RE = re.compile(r"^[A-Z]{3,8}\d?$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@le\.utah\.gov$", re.I)

def normal_phone(text):
    """A ten-digit number as NNN-NNN-NNNN, whatever punctuation the feed
    printed it with ("4357492828", "(801) 450-3701", "785 296-7122"), or None
    when the text is not one telephone number."""
    if re.search(r"[A-Za-z]", text or ""):
        return None
    digits = re.sub(r"\D", "", text or "")
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


_SESSION = None


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
        _SESSION.headers["Accept"] = "application/json"
    return _SESSION


def fetch(url):
    import requests

    gate = RobotsGate(session(), USER_AGENT)
    pacer = HostPacer(gate)
    ok, why = gate.allows(url)
    print("robots.txt %s: %s" % (urllib.parse.urlsplit(url).netloc, why), file=sys.stderr)
    if not ok:
        raise SystemExit("FAIL: robots.txt refuses %s (%s)" % (url, why))
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        try:
            with pacer.hold(url):
                resp = session().get(url, timeout=60)
            resp.raise_for_status()
            return resp.content.decode("utf-8-sig")
        except requests.RequestException as exc:
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                session().close()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


def load(offline, save):
    if offline:
        with open(os.path.join(offline, "legislators.json"), encoding="utf-8") as fh:
            return json.load(fh)
    body = fetch(FEED)
    if save:
        os.makedirs(save, exist_ok=True)
        with open(os.path.join(save, "legislators.json"), "w", encoding="utf-8") as fh:
            fh.write(body)
    return json.loads(body)


def phones(rec, where, notes):
    """The member's telephones with the labels the feed prints them under."""
    labels = {}
    order = []
    for field, label in PHONE_FIELDS:
        printed = str(rec.get(field) or "").strip()
        if not printed:
            continue
        number = normal_phone(printed)
        if not number:
            notes.append("%s: the %s telephone reads %r, not carried" % (where, label, printed))
            continue
        if number not in labels:
            labels[number] = []
            order.append(number)
        labels[number].append(label)
    def joined(words):
        return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]
    return ["%s %s" % (joined(labels[n]), n) for n in order]


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def build(records, previous, today):
    seats = {"S": {}, "H": {}}
    notes = {"S": [], "H": []}
    for rec in records:
        chamber = rec.get("house")
        if chamber not in CHAMBERS:
            raise SystemExit("FAIL: a record names house %r" % chamber)
        cfg, n = CHAMBERS[chamber], notes[chamber]
        try:
            district = int(str(rec.get("district") or "").strip())
        except ValueError:
            raise SystemExit("FAIL: a record names district %r" % rec.get("district"))
        where = "%s %d" % (cfg["label"].split()[0], district)
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats[chamber]:
            raise SystemExit("FAIL: %s is listed twice" % where)
        name = re.sub(r"\s+", " ", str(rec.get("formatName") or "")).strip()
        if not name or re.search(r"\d", name):
            raise SystemExit("FAIL: %s's record names %r" % (where, name))
        member = {"name": name}
        party = str(rec.get("party") or "").strip()
        if party in PARTIES:
            member["party"] = PARTIES[party]
        elif party:
            raise SystemExit("FAIL: %s's party letter %r is one this builder has no "
                             "name for; read the chamber's member page and add it"
                             % (where, party))
        email = str(rec.get("email") or "").strip()
        if EMAIL_RE.match(email):
            member["email"] = email
        elif email:
            n.append("%s: an e-mail address off le.utah.gov was not carried" % where)
        numbers = phones(rec, where, n)
        if numbers:
            member["phone"] = numbers[0]
            if numbers[1:]:
                member["phonesExtra"] = numbers[1:]
        ident = str(rec.get("id") or "").strip()
        if ID_RE.match(ident):
            member["url"] = cfg["page"] % ident
        else:
            n.append("%s: member id %r, no page linked" % (where, ident))
        seats[chamber][district] = member
    out = {}
    for chamber, cfg in CHAMBERS.items():
        for district in range(1, cfg["seats"] + 1):
            if district not in seats[chamber]:
                prev = previous[chamber].get(str(district)) or {}
                seats[chamber][district] = {
                    "asOf": (prev.get("asOf") if not prev.get("name") else None) or today}
                notes[chamber].append("%s %d: no member listed"
                                      % (cfg["label"].split()[0], district))
        out[chamber] = check(chamber, seats[chamber])
    return out, notes


def check(chamber, seats):
    cfg = CHAMBERS[chamber]
    roster = {str(d): seats[d] for d in range(1, cfg["seats"] + 1)}
    named = [m for m in roster.values() if m.get("name")]
    if len(named) < cfg["expected"]:
        raise SystemExit("FAIL: resolved %d named %s districts (expected >= %d) — "
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
    records = (load(offline, save).get("legislators") or [])
    previous = {c: previous_roster(out_dir, cfg) for c, cfg in CHAMBERS.items()}
    built, notes = build(records, previous, today)
    os.makedirs(out_dir, exist_ok=True)
    for chamber in ("S", "H"):
        cfg, roster = CHAMBERS[chamber], built[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for m in roster.values() if m.get("name")]
        print("Wrote %s (%d of %d seats named, %d with a party, %d with an e-mail "
              "address, %d with a telephone)"
              % (out_path, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("phone"))), file=sys.stderr)
        for note in notes[chamber]:
            print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
