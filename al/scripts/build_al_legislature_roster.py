#!/usr/bin/env python3
"""
Build the Alabama Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from the Alabama
Legislature's own member service (ALISON, alison.legislature.state.al.us),
so the al-senate / al-house cards join a small roster instead of reaching
another host at click time.

index.html's al-senate / al-house layers fetch data/app/al-senate-members.json
and al-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
capitolOffice}}, or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-al-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

The legislature's website (ALISON) draws its Senate and House member lists
from a GraphQL service at /graphql on the same host, and the site's own
scripts filter it to the sitting members with `active: { eq: true }`. Asked
for a body without that filter, the service also returns former members (44
Senate records that day, two of them for District 19). This script asks the
site's question, one body at a time, for each member's id, name, body, affiliation
("R" or "D"), district ("Senate District 22"), phone, email and State House
address (addressLine1 and 2, city, state, ZIP). That day it answered 37
Senate records and 106 House records: every one of the 35 Senate and 105
House districts once, plus three records with no district, the Lieutenant
Governor (the Senate's presiding officer), the Secretary of the Senate and
the Clerk of the House, which are not seats and are not carried.

Every member's address that day was the State House, "11 S Union Street" (the
Senate) or "11 South Union Street" (the House), with the suite in
addressLine2 and "Montgomery, AL 36130"; an address that is not 11 South
Union Street in Montgomery is not carried, so no home address can ship. The
telephone is the member's State House line.

THE E-MAIL ADDRESS IS THE ONE THE LEGISLATURE PRINTS FOR THE MEMBER. That day
28 of the 35 senators' addresses and 48 of the 105 representatives' were at
alsenate.gov or alhouse.gov; the rest were the member's own, at a mail
provider or the member's business. Under the fleet's rule of 2026-10-17 an
address a government source prints beside one official ships on that
official, so all are carried, except one printed beside two members, which
belongs to neither, and one that is not a single address (one record's held a
space).

ROBOTS. alison.legislature.state.al.us has no robots.txt: on 2026-11-12 the
path answered the site's own HTML page, which RFC 9309 reads as no policy; it is read
through scripts/robots_policy.py with the User-Agent the requests send before
the first request, and a stated Crawl-delay is honoured. The two requests are
paced two seconds apart regardless.

Honesty: names are never guessed. A seat no member is listed for gets a record
naming nobody, dated; a seat carried twice stops the build.

Usage:
    python3 al/scripts/build_al_legislature_roster.py [output_dir]
    python3 al/scripts/build_al_legislature_roster.py --save DIR [output_dir]
    python3 al/scripts/build_al_legislature_roster.py --offline DIR [output_dir]
"""

import collections
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/al/)"
PACE_SECONDS = 2.0
ATTEMPTS = 4
RETRY_SECONDS = 20.0
SERVICE = "https://alison.legislature.state.al.us/graphql"
QUERY = """query members($body: LegislativeBody) {
  legislativeMembers(where: { body: { eq: $body }, active: { eq: true } }, order: "lastName") {
    data { id firstName lastName body affiliation district phone email
           addressLine1 addressLine2 addressCity addressState addressZip
           leadershipTitle }
    count
  }
}"""

# 35 of 35 senators and 105 of 105 representatives were listed on 2026-11-12.
CHAMBERS = {
    "S": {"out": "al-senate-members.json", "label": "Senate", "seats": 35,
          "expected": 31, "body": "Senate", "prefix": "Senate District",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.8}},
    "H": {"out": "al-house-members.json", "label": "House of Representatives",
          "seats": 105, "expected": 94, "body": "House", "prefix": "House District",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.8}},
}

PARTIES = {"R": "Republican", "D": "Democratic"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

STATE_HOUSE_RE = re.compile(r"^11 (S|South) Union (Street|St\.?)$")
# The suite as printed: "Suite 727", "Suite 523-A", "Suite 517 F", and once a
# bare "526-B", which is written "Suite 526-B" as the other House offices are.
SUITE_RE = re.compile(r"^(?:(Suite|Room) )?(\d{2,4}(?:[ -]?[A-Z])?)$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def normal_phone(text):
    """A ten-digit number as (NNN) NNN-NNNN, the form most records print, or
    None when the text is not one telephone number."""
    if re.search(r"[A-Za-z]", text or ""):
        return None
    digits = re.sub(r"\D", "", text or "")
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return "(%s) %s-%s" % (digits[:3], digits[3:6], digits[6:])


_SESSION = None
_GATE = None
_PACER = None
_LAST = [0.0]


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
    return _SESSION


def ask(body):
    import requests

    global _GATE, _PACER
    if _GATE is None:
        _GATE = RobotsGate(session(), USER_AGENT)
        _PACER = HostPacer(_GATE)
        ok, why = _GATE.allows(SERVICE)
        print("robots.txt %s: %s" % (urllib.parse.urlsplit(SERVICE).netloc, why),
              file=sys.stderr)
        if not ok:
            raise SystemExit("FAIL: robots.txt refuses %s (%s)" % (SERVICE, why))
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        wait = PACE_SECONDS - (time.time() - _LAST[0])
        if wait > 0:
            time.sleep(wait)
        try:
            with _PACER.hold(SERVICE):
                resp = session().post(SERVICE, json={"query": QUERY, "variables": {"body": body}},
                                      timeout=60)
            _LAST[0] = time.time()
            resp.raise_for_status()
            text = resp.content.decode("utf-8")
            data = json.loads(text)
            if data.get("errors"):
                raise SystemExit("FAIL: the member service answered errors: %r"
                                 % data["errors"][:2])
            return text
        except requests.RequestException as exc:
            _LAST[0] = time.time()
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                session().close()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (SERVICE, ATTEMPTS, last))


def load(chamber, offline, save):
    name = "%s.json" % CHAMBERS[chamber]["body"].lower()
    if offline:
        with open(os.path.join(offline, name), encoding="utf-8") as fh:
            body = fh.read()
    else:
        body = ask(CHAMBERS[chamber]["body"])
        if save:
            os.makedirs(save, exist_ok=True)
            with open(os.path.join(save, name), "w", encoding="utf-8") as fh:
                fh.write(body)
    return ((json.loads(body).get("data") or {}).get("legislativeMembers") or {}).get("data") or []


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def state_house(rec):
    line1 = re.sub(r"\s+", " ", str(rec.get("addressLine1") or "")).strip()
    line2 = re.sub(r"\s+", " ", str(rec.get("addressLine2") or "")).strip()
    city = str(rec.get("addressCity") or "").strip()
    state = str(rec.get("addressState") or "").strip()
    zipc = str(rec.get("addressZip") or "").strip()
    if not (STATE_HOUSE_RE.match(line1) and city == "Montgomery" and state == "AL"
            and re.match(r"^361\d\d(-\d{4})?$", zipc)):
        return None
    lines = [line1]
    if line2:
        m = SUITE_RE.match(line2)
        if not m:
            return None
        lines.append(line2 if m.group(1) else "Suite " + m.group(2))
    lines.append("Montgomery, AL %s" % zipc)
    return lines


def build_chamber(chamber, records, shared, previous, today):
    cfg = CHAMBERS[chamber]
    seats, notes = {}, []
    for rec in records:
        if rec.get("body") != cfg["body"]:
            raise SystemExit("FAIL: a %s record names body %r" % (cfg["label"], rec.get("body")))
        printed = str(rec.get("district") or "").strip()
        if not printed:
            notes.append("%s %s (%s): no district, not a seat" % (
                rec.get("firstName"), rec.get("lastName"), rec.get("leadershipTitle")))
            continue
        m = re.match(r"^%s (\d+)$" % cfg["prefix"], printed)
        if not m:
            raise SystemExit("FAIL: a %s record names district %r" % (cfg["label"], printed))
        district = int(m.group(1))
        where = "%s %d" % (cfg["label"].split()[0], district)
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats:
            raise SystemExit("FAIL: %s is listed twice" % where)
        name = " ".join(str(rec.get(f) or "").strip() for f in ("firstName", "lastName"))
        name = re.sub(r"\s+", " ", name).strip()
        if not name or re.search(r"\d", name):
            raise SystemExit("FAIL: %s's record names %r" % (where, name))
        member = {"name": name}
        party = str(rec.get("affiliation") or "").strip()
        if party in PARTIES:
            member["party"] = PARTIES[party]
        elif party:
            member["party"] = party
            notes.append("%s: party printed as %r ships as printed" % (where, party))
        email = str(rec.get("email") or "").strip()
        if email and EMAIL_RE.match(email) and shared[email.lower()] == 1:
            member["email"] = email
        elif email:
            notes.append("%s: the e-mail address is %s, not carried" % (
                where, "printed beside more than one member" if EMAIL_RE.match(email)
                else "not a single address"))
        office = state_house(rec)
        if office is None and (rec.get("addressLine1") or rec.get("addressCity")):
            notes.append("%s: the address printed is not the State House, not carried" % where)
            office = []
        office = office or []
        phone = normal_phone(str(rec.get("phone") or ""))
        if phone:
            office.append(phone)
        elif rec.get("phone"):
            notes.append("%s: the telephone reads %r, not carried" % (where, rec.get("phone")))
        if office:
            member["capitolOffice"] = office
        seats[district] = member
    for district in range(1, cfg["seats"] + 1):
        if district not in seats:
            prev = previous.get(str(district)) or {}
            seats[district] = {"asOf": (prev.get("asOf") if not prev.get("name") else None) or today}
            notes.append("%s %d: no member listed" % (cfg["label"].split()[0], district))
    return seats, notes


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
    records = {c: load(c, offline, save) for c in ("S", "H")}
    shared = collections.Counter(str(r.get("email") or "").strip().lower()
                                 for rs in records.values() for r in rs if r.get("district"))
    built = {}
    for chamber in ("S", "H"):
        previous = previous_roster(out_dir, CHAMBERS[chamber])
        seats, notes = build_chamber(chamber, records[chamber], shared, previous, today)
        built[chamber] = (check(chamber, seats), notes)
    os.makedirs(out_dir, exist_ok=True)
    for chamber, (roster, notes) in built.items():
        cfg = CHAMBERS[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for m in roster.values() if m.get("name")]
        print("Wrote %s (%d of %d seats named, %d with a party, %d with an e-mail "
              "address, %d with a State House office)"
              % (out_path, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("capitolOffice"))), file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
