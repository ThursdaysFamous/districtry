#!/usr/bin/env python3
"""
Build the New Jersey Senate and General Assembly rosters (district -> current
officeholders) as same-origin app-data files, from the New Jersey
Legislature's OWN member roster at www.njleg.state.nj.us, so the nj-senate /
nj-assembly cards join a small roster instead of reaching a third-party host
at click time.

index.html's nj-senate / nj-assembly layers fetch data/app/nj-senate-members.json
and nj-assembly-members.json lazily on first click and join them to the
pre-built legislative geometry by district number. This script writes the two
rosters shaped for the registerIlgaChamber factory: the Senate as {district ->
{name, party, email, districtOffice, url}}, one senator per district, and the
General Assembly as {district -> {"seats": 2, "members": [two such rows]}},
because each of New Jersey's 40 legislative districts elects one senator and
TWO members of the General Assembly (N.J. Const. art. IV, sec. 2). A weekly
GitHub Action (.github/workflows/update-nj-legislature-roster.yml) reruns it
and opens a PR when a roster changes, so officeholder data gets a human look
before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-10. The Legislature's roster page,
/legislative-roster, is a Next.js page whose own data block (the
`__NEXT_DATA__` script) carries the whole roster as `legrosterData[0]`: one
record per member with the name ("Amato Jr., Carmen F."), the chamber code
(S or A), the district, the party ("Republican", "Democrat"), a vacancy sort
key and the member's page (/legislative-roster/<key>/<slug>). That day it held
120 members: 40 senators, one for each district, and 80 members of the
Assembly, two for each, all marked current. Each member's page fills itself in
from the Legislature's own feed, /api/legislatorData/legislatorBio/<key>, the
address the page's own script requests; it answers with three lists: the
member (with the name in reading order, the status and the member's
legislative mailbox, `ccMailName`, an @njleg.org address), the member's
offices, and the member's committees. These pages list the 222nd Legislature;
the Assembly was elected in November 2025 and the Senate in November 2023, and
both are next on the ballot in November 2027.

WHAT IS READ, AND WHAT IS NEVER READ. From the roster: the chamber, the
district, the party and the member's page. From the feed: the name in reading
order, the status, the mailbox, and the office the Legislature labels
"District Office" with address code D, which is the member's main district
office. A member can list a second office (address code S); it is not read,
because the card holds one district office, and the member's page lists it.
The committees, the photograph and the biography are never read. The contact
link on the roster opens a web form, which is not carried. The fax number is
never read. Every office ships only if it is labelled a District Office, has a
street, a city in New Jersey and a five-digit ZIP code, so nothing that is not
an office can ride along.

THE E-MAIL ADDRESS is the member's own legislative mailbox, printed in the
member's own record. The fleet's rule since 2026-10-17 (Adam: "E-mails too")
is that an address a government source prints in one official's own entry is
that official's. An address printed for two or more members is an office's and
ships on no row. Only an @njleg.org address is carried.

THE DISTRICT OFFICE'S TELEPHONE rides inside the office block. An office the
Legislature prints for two or three members of one district (they often share
one) is still an office, and each member's card shows it as that member's
district office, which is what the Legislature's own pages do.

ROBOTS AND PACING. www.njleg.state.nj.us's robots.txt is read through
scripts/robots_policy.py with the User-Agent the fetches send, before the first
fetch. Read 2026-11-10: one `*` group, `Allow: /`, and no Crawl-delay. The
host is paced at one request a second regardless, so a run takes about two
minutes for its 121 requests.

Honesty: names are never guessed. A district the roster gives fewer members
than it elects ships those it gives, dated; a Senate district with no row ships
as vacant, naming the roster; a district carrying more members than it elects
stops the build.

Usage:
    python3 nj/scripts/build_nj_legislature_roster.py [output_dir]
    python3 nj/scripts/build_nj_legislature_roster.py --save DIR [output_dir]
    python3 nj/scripts/build_nj_legislature_roster.py --offline DIR [output_dir]

--save writes every page fetched into DIR (roster.html, bio/<key>.json),
reading back any it already holds; --offline reads them back instead of
fetching, for building and testing without the network.
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/nj/)"
# The host states no delay; it is paced at one second regardless.
MIN_PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

SITE = "https://www.njleg.state.nj.us"
ROSTER_URL = SITE + "/legislative-roster"
BIO_URL = SITE + "/api/legislatorData/legislatorBio/%d"

# Floors catch a truncated roster or a layout change while tolerating real
# vacancies: 40 of 40 senators and 80 of 80 members of the Assembly were named
# on 2026-11-10.
CHAMBERS = {
    "S": {"out": "nj-senate-members.json", "label": "Senate", "seats": 40,
          "per_district": 1, "expected": 36, "code": "S",
          "name": "The New Jersey Legislature",
          # The share of named members carrying each field, floored below what
          # 2026-11-10 measured: every current member printed a party, a
          # mailbox and a main district office. A field falling under its
          # floor is the Brown County shape: the row count holds and the
          # contact goes.
          "fields": {"party": 0.9, "email": 0.9, "districtOffice": 0.8}},
    "A": {"out": "nj-assembly-members.json", "label": "Assembly", "seats": 40,
          "per_district": 2, "expected": 72, "code": "A",
          "name": "The New Jersey Legislature",
          "fields": {"party": 0.9, "email": 0.9, "districtOffice": 0.8}},
}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
# The slug after the key is the title and surname as the site writes it,
# apostrophes and full stops included ("senator-o'scanlon", "assemblyman-
# azzariti-jr."); only the key is read.
BIO_LINK_RE = re.compile(r"^/legislative-roster/(\d+)/[A-Za-z0-9.'-]+$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@njleg\.org$", re.I)
PHONE_RE = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")
ZIP_RE = re.compile(r"^\d{5}(?:-\d{4})?$")
PARTIES = {"Democrat": "Democrat", "Republican": "Republican"}

_SESSION = None


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
    return _SESSION


_GATE = None
_PACER = None
_LAST = {}


def gate():
    global _GATE, _PACER
    if _GATE is None:
        _GATE = RobotsGate(session(), USER_AGENT)
        _PACER = HostPacer(_GATE)
    return _GATE


def fetch(url):
    import requests

    ok, why = gate().allows(url)
    host = urllib.parse.urlsplit(url).netloc
    if host not in _LAST:
        print("robots.txt %s: %s" % (host, why), file=sys.stderr)
        _LAST[host] = 0.0
    if not ok:
        raise SystemExit("FAIL: robots.txt refuses %s (%s)" % (url, why))
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        wait = MIN_PACE_SECONDS - (time.time() - _LAST[host])
        if wait > 0:
            time.sleep(wait)
        try:
            with _PACER.hold(url):
                resp = session().get(url, timeout=120)
            _LAST[host] = time.time()
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as exc:  # reset, timeout, 5xx
            _LAST[host] = time.time()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


class Pages:
    """Fetch, save or replay the pages one run reads."""

    def __init__(self, offline=None, save=None):
        self.offline, self.save = offline, save

    def get(self, name, url):
        source = self.offline or (self.save if self.save and
                                  os.path.exists(os.path.join(self.save, name)) else None)
        if source:
            # --offline, or a page an interrupted --save run already wrote.
            with open(os.path.join(source, name), encoding="utf-8") as fh:
                return fh.read()
        body = fetch(url)
        if self.save:
            path = os.path.join(self.save, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)
        return body


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def roster_records(page):
    """The roster page's own data block: one record per member."""
    m = NEXT_DATA_RE.search(page)
    if not m:
        raise SystemExit("FAIL: the roster page no longer carries its __NEXT_DATA__ "
                         "block — its layout changed")
    try:
        data = json.loads(m.group(1))
        records = data["props"]["pageProps"]["legrosterData"][0]
    except (ValueError, KeyError, IndexError, TypeError):
        raise SystemExit("FAIL: the roster page's data block no longer holds "
                         "legrosterData[0] — its layout changed")
    if not isinstance(records, list) or len(records) < 100:
        raise SystemExit("FAIL: the roster page's data block lists %s members — its "
                         "layout changed" % (len(records) if isinstance(records, list) else "no"))
    return records


def bio_record(pages, key):
    body = pages.get("bio/%d.json" % key, BIO_URL % key)
    try:
        data = json.loads(body)
        person = data[0][0]
        offices = data[1] if len(data) > 1 and isinstance(data[1], list) else []
    except (ValueError, KeyError, IndexError, TypeError):
        raise SystemExit("FAIL: the Legislature's feed for member %d no longer answers "
                         "[[member], [offices], ...] — its layout changed" % key)
    return person, offices


def main_office(offices, where, notes):
    """The member's main district office as card lines, or None."""
    picked = [o for o in offices
              if isinstance(o, dict) and o.get("Address_Type") == "District Office"
              and o.get("Address_Code") == "D"]
    if not picked:
        if offices:
            notes.append("%s: no main district office (address code D) is listed" % where)
        return None
    o = picked[0]
    street = (o.get("Street_Address") or "").strip()
    city = (o.get("City") or "").strip()
    state = (o.get("State") or "").strip()
    zipcode = (o.get("Zipcode") or "").strip()
    # A field holding several numbers ("(908) 316-0266, (908) 327-9119") ships
    # its first, because every telephone the fleet ships dials one number
    # (scripts/validate_telephones.py); the member's page lists the rest.
    phones = [p.strip() for p in (o.get("Phone_Number") or "").split(",") if p.strip()]
    phone = phones[0] if phones and all(PHONE_RE.match(p) for p in phones) else None
    if phones and not phone:
        notes.append("%s: the district office's telephone is not printed as numbers, "
                     "so it was not carried" % where)
    elif len(phones) > 1:
        notes.append("%s: the district office prints %d telephone numbers; the first "
                     "was carried" % (where, len(phones)))
    lines = []
    if street or city or zipcode:
        if not street or not city or state != "NJ" or not ZIP_RE.match(zipcode):
            notes.append("%s: the main district office is not printed as a New Jersey "
                         "street address with a ZIP code, so its address was not "
                         "carried" % where)
        else:
            lines = [street, "%s, NJ %s" % (city, zipcode)]
    elif phone:
        # Measured 2026-11-10: one member's main office printed a telephone and
        # no address, which ships as the office's telephone alone.
        notes.append("%s: the main district office prints a telephone and no address"
                     % where)
    if phone:
        lines.append(phone)
    return lines or None


def member_row(pages, rec, where, notes):
    link = BIO_LINK_RE.match(rec.get("BioLink") or "")
    if not link:
        raise SystemExit("FAIL: %s's roster record carries no member page — the "
                         "roster's layout changed" % where)
    key = int(link.group(1))
    person, offices = bio_record(pages, key)
    name = re.sub(r"\s+", " ", (person.get("Full_Name") or "")).strip()
    if not name:
        raise SystemExit("FAIL: the Legislature's feed names no one for member %d (%s)"
                         % (key, where))
    if person.get("Legislator_Status") != "A":
        notes.append("%s: %s's status reads %r rather than A (active)"
                     % (where, name, person.get("Legislator_Status")))
    member = {"name": name}
    party = PARTIES.get((rec.get("PartyDescription") or "").strip())
    if party:
        member["party"] = party
    else:
        notes.append("%s: %s's party reads %r, which was not carried"
                     % (where, name, rec.get("PartyDescription")))
    mail = (person.get("ccMailName") or "").strip()
    if EMAIL_RE.match(mail):
        member["email"] = mail
    elif mail:
        notes.append("%s: %s's mailbox %r is not an @njleg.org address, so it was not "
                     "carried" % (where, name, mail))
    office = main_office(offices, where, notes)
    if office:
        member["districtOffice"] = office
    member["url"] = SITE + link.group(0)
    return member


def build_chamber(chamber, records, pages, previous, today):
    cfg = CHAMBERS[chamber]
    by_district, notes = {}, []
    for rec in records:
        if rec.get("RosterHouseCode") != cfg["code"]:
            continue
        try:
            district = int(rec.get("Roster_District"))
        except (TypeError, ValueError):
            raise SystemExit("FAIL: a %s roster record carries no district number"
                             % cfg["label"])
        where = "%s %d" % (cfg["label"], district)
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d districts"
                             % (where, cfg["seats"]))
        if rec.get("VacantSort"):
            notes.append("%s: a record marked vacant was not read" % where)
            continue
        by_district.setdefault(district, []).append(member_row(pages, rec, where, notes))
    seats = {}
    for district in range(1, cfg["seats"] + 1):
        where = "%s %d" % (cfg["label"], district)
        members = by_district.get(district, [])
        if len(members) > cfg["per_district"]:
            raise SystemExit("FAIL: %s carries %d current members for %d seats"
                             % (where, len(members), cfg["per_district"]))
        if cfg["per_district"] == 1:
            if members:
                seats[district] = members[0]
            else:
                prev = previous.get(str(district)) or {}
                seats[district] = {
                    "vacant": True,
                    "vacantWhy": "%s's roster lists no current senator for this district."
                                 % cfg["name"],
                    "sourceUrl": ROSTER_URL,
                    # The day the roster was first read saying so, kept across runs.
                    "asOf": (prev.get("asOf") if prev.get("vacant") else None) or today,
                }
                notes.append("%s: no current member, shipped as vacant" % where)
            continue
        record = {"seats": cfg["per_district"], "members": members}
        if len(members) < cfg["per_district"]:
            prev = previous.get(str(district)) or {}
            prev_short = len(prev.get("members") or []) < cfg["per_district"] and prev.get("asOf")
            record["asOf"] = prev.get("asOf") if prev_short else today
            record["sourceUrl"] = ROSTER_URL
            notes.append("%s: %d of %d members listed" % (where, len(members),
                                                          cfg["per_district"]))
        seats[district] = record
    return seats, notes


def named_members(chamber, roster):
    out = []
    for rec in roster.values():
        if CHAMBERS[chamber]["per_district"] > 1:
            out.extend(m for m in rec.get("members") or [] if m.get("name"))
        elif rec.get("name"):
            out.append(rec)
    return out


def check(chamber, seats):
    cfg = CHAMBERS[chamber]
    roster = {str(d): seats[d] for d in range(1, cfg["seats"] + 1)}
    named = named_members(chamber, roster)
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


def build(pages, out_dir, today):
    records = roster_records(pages.get("roster.html", ROSTER_URL))
    built = {}
    for chamber in ("S", "A"):
        previous = previous_roster(out_dir, CHAMBERS[chamber])
        seats, notes = build_chamber(chamber, records, pages, previous, today)
        built[chamber] = (check(chamber, seats), notes)

    # An address printed for two or more members, in either chamber, is an
    # office's and ships on no member's row.
    holders = {}
    for chamber, (roster, _) in built.items():
        for member in named_members(chamber, roster):
            if member.get("email"):
                holders.setdefault(member["email"].lower(), []).append(
                    "%s %s" % (CHAMBERS[chamber]["label"], member["name"]))
    shared = {a for a, who in holders.items() if len(who) > 1}
    for who in sorted(" and ".join(w) for w in holders.values() if len(w) > 1):
        print("NOTE: one e-mail address is printed for %s, so it is an office's and "
              "ships on no member's row" % who, file=sys.stderr)
    for chamber, (roster, _) in built.items():
        for member in named_members(chamber, roster):
            if (member.get("email") or "").lower() in shared:
                del member["email"]
    return built


def main():
    args = sys.argv[1:]
    offline = save = None
    while args and args[0] in ("--offline", "--save"):
        if len(args) < 2:
            print(__doc__.split("Usage:")[1].split("--save writes")[0], file=sys.stderr)
            sys.exit(1)
        if args[0] == "--offline":
            offline = args[1]
        else:
            save = args[1]
        args = args[2:]
    if len(args) > 1 or (offline and save) or (args and args[0].startswith("-")):
        print("usage: %s [--offline DIR | --save DIR] [output_dir]" % sys.argv[0],
              file=sys.stderr)
        sys.exit(1)
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    today = datetime.date.today().isoformat()

    built = build(Pages(offline, save), out_dir, today)

    # Write only once BOTH chambers have passed every guard, so a failure in
    # the Assembly cannot leave a fresh Senate file beside a stale Assembly one.
    os.makedirs(out_dir, exist_ok=True)
    for chamber, (roster, notes) in built.items():
        cfg = CHAMBERS[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = named_members(chamber, roster)
        print("Wrote %s (%d of %d seats named, %d with an e-mail, %d with a district "
              "office)" % (out_path, len(named), cfg["seats"] * cfg["per_district"],
                           sum(1 for m in named if m.get("email")),
                           sum(1 for m in named if m.get("districtOffice"))),
              file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)
    if _PACER is not None:
        for line in _PACER.report():
            print(line, file=sys.stderr)


if __name__ == "__main__":
    main()
