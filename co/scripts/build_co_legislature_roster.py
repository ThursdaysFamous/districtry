#!/usr/bin/env python3
"""
Build the Colorado Senate and House of Representatives rosters (district ->
current officeholder) as same-origin app-data files, from the Colorado General
Assembly's own legislator list at leg.colorado.gov, so the co-senate /
co-house cards join a small roster instead of reaching another host at click
time.

index.html's co-senate / co-house layers fetch data/app/co-senate-members.json
and co-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script writes the two rosters
shaped for the registerIlgaChamber factory ({district -> {name, party, email,
capitolOffice, url}}, or a record naming nobody). A weekly GitHub Action
(.github/workflows/update-co-legislature-roster.yml) reruns it and opens a PR
when a roster changes, so officeholder data gets a look before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-11-12.

leg.colorado.gov/legislators is one table, a row per member: Title (Senator
or Representative), Name ("Amabile, Judy", linked to the member's page),
District, Party ("Democrat" or "Republican"), Capitol Phone # and Email. That
day it held 36 senators and 66 representatives, 102 rows for 100 seats,
because two members who resigned stay listed with a note under the name
("Senator Michaelson Jenet resigned as of 2/13/26", "Representative Rutinel
resigned 9/4/26") beside the members appointed to their seats. A row carrying
a note that says the member resigned is not read; any other note stops the
build for a person to read. The page's footer prints the Capitol's address,
"200 E Colfax Avenue, Denver, CO 80203", which every member's own page prints
as the Capitol address, so it is carried above the member's Capitol
telephone; when the list stops printing it, it is not carried.

THE E-MAIL ADDRESS IS THE ONE THE GENERAL ASSEMBLY PRINTS. That day 100 of
the 102 were at coleg.gov; one was at gmail.com, and one senator's list row
and own page both print an address at senate.co.com. Under the fleet's rule
of 2026-10-17 an address a government source prints beside one official
ships on that official, so all are carried as printed.

ROBOTS. leg.colorado.gov/robots.txt was read on 2026-11-12: its `*` group
disallows admin and file-download paths and the calendars and journals, and
allows / ; /legislators is allowed and no Crawl-delay is stated. It is read
through scripts/robots_policy.py with the User-Agent the fetch sends, before
the one fetch this script makes.

Honesty: names are never guessed. A seat with no sitting member listed gets a
record naming nobody, dated; two sitting members for one seat stop the build.

Usage:
    python3 co/scripts/build_co_legislature_roster.py [output_dir]
    python3 co/scripts/build_co_legislature_roster.py --save DIR [output_dir]
    python3 co/scripts/build_co_legislature_roster.py --offline DIR [output_dir]
"""

import datetime
import html as html_module
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

USER_AGENT = "districtry/1.0 (+https://districtry.com/co/)"
ATTEMPTS = 4
RETRY_SECONDS = 20.0
SITE = "https://leg.colorado.gov"
LIST = SITE + "/legislators"
CAPITOL = ["200 E Colfax Avenue", "Denver, CO 80203"]

# 35 of 35 senators and 65 of 65 representatives were seated on 2026-11-12.
CHAMBERS = {
    "S": {"out": "co-senate-members.json", "label": "Senate", "seats": 35,
          "expected": 31, "title": "Senator",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.8}},
    "H": {"out": "co-house-members.json", "label": "House of Representatives",
          "seats": 65, "expected": 58, "title": "Representative",
          "fields": {"party": 0.9, "capitolOffice": 0.9, "email": 0.8}},
}

PARTIES = {"Democrat": "Democratic", "Democratic": "Democratic",
           "Republican": "Republican"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r'data-label="([^"]+)"[^>]*>(.*?)</t[dh]>', re.S)
PAGE_RE = re.compile(r'href="(/legislators/[a-z0-9-]+)"')
NOTE_RE = re.compile(r"<div class='mb-0'>(.*?)</div>", re.S)
RESIGNED_RE = re.compile(r"\bresigned\b", re.I)
PHONE_RE = re.compile(r"^\d{3}-\d{3}-\d{4}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


_SESSION = None


def session():
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = USER_AGENT
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
            return resp.content.decode("utf-8")
        except requests.RequestException as exc:
            if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                session().close()
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


def load(offline, save):
    if offline:
        with open(os.path.join(offline, "legislators.html"), encoding="utf-8") as fh:
            return fh.read()
    body = fetch(LIST)
    if save:
        os.makedirs(save, exist_ok=True)
        with open(os.path.join(save, "legislators.html"), "w", encoding="utf-8") as fh:
            fh.write(body)
    return body


def name_of(listed):
    """'Amabile, Judy' -> 'Judy Amabile'; a name with a suffix after a second
    comma ('Smith, John, Jr.') keeps it at the end."""
    parts = [p.strip() for p in listed.split(",") if p.strip()]
    if len(parts) == 2:
        return "%s %s" % (parts[1], parts[0])
    if len(parts) == 3:
        return "%s %s %s" % (parts[1], parts[0], parts[2])
    return listed


def previous_roster(out_dir, cfg):
    try:
        with open(os.path.join(out_dir, cfg["out"]), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def build(page, previous, today):
    titles = {cfg["title"]: c for c, cfg in CHAMBERS.items()}
    capitol = CAPITOL if all(line in page for line in CAPITOL) else []
    seats = {"S": {}, "H": {}}
    notes = {"S": [], "H": []}
    if not capitol:
        for n in notes.values():
            n.append("the list no longer prints the Capitol's address; not carried")
    rows = ROW_RE.findall(page)
    if len(rows) < 90:
        raise SystemExit("FAIL: the legislator list held %d rows — its layout changed" % len(rows))
    for row in rows:
        cells = {k: v for k, v in CELL_RE.findall(row)}
        if not cells:
            continue  # the header row
        title = clean(cells.get("Title"))
        if title not in titles:
            raise SystemExit("FAIL: a row's title reads %r" % title)
        chamber = titles[title]
        cfg, n = CHAMBERS[chamber], notes[chamber]
        note = NOTE_RE.search(cells.get("Name", ""))
        note = clean(note.group(1)) if note else ""
        name_cell = NOTE_RE.sub("", cells.get("Name", ""))
        listed = clean(name_cell)
        try:
            district = int(clean(cells.get("District")))
        except ValueError:
            raise SystemExit("FAIL: %s's row names district %r" % (listed, clean(cells.get("District"))))
        where = "%s %d" % (cfg["label"].split()[0], district)
        if note:
            if RESIGNED_RE.search(note):
                n.append("%s: %s is listed with the note %r and is not read" % (where, listed, note))
                continue
            raise SystemExit("FAIL: %s's row carries the note %r, which this builder "
                             "does not know how to read" % (where, note))
        if not 1 <= district <= cfg["seats"]:
            raise SystemExit("FAIL: %s is not one of the chamber's %d seats"
                             % (where, cfg["seats"]))
        if district in seats[chamber]:
            raise SystemExit("FAIL: %s is listed twice with no note saying one resigned"
                             % where)
        name = name_of(listed)
        if not name or re.search(r"\d", name):
            raise SystemExit("FAIL: %s's row names %r" % (where, listed))
        member = {"name": name}
        party = clean(cells.get("Party"))
        if party in PARTIES:
            member["party"] = PARTIES[party]
        elif party:
            member["party"] = party
            n.append("%s: party printed as %r ships as printed" % (where, party))
        email = clean(cells.get("Email"))
        if EMAIL_RE.match(email):
            member["email"] = email
        elif email:
            n.append("%s: the e-mail reads %r, not carried" % (where, email))
        phone = clean(cells.get("Capitol Phone #"))
        office = list(capitol)
        if PHONE_RE.match(phone):
            office.append(phone)
        elif phone:
            n.append("%s: the Capitol telephone reads %r, not carried" % (where, phone))
        if office:
            member["capitolOffice"] = office
        page_link = PAGE_RE.search(name_cell)
        if page_link:
            member["url"] = SITE + page_link.group(1)
        seats[chamber][district] = member
    out = {}
    for chamber, cfg in CHAMBERS.items():
        for district in range(1, cfg["seats"] + 1):
            if district not in seats[chamber]:
                prev = previous[chamber].get(str(district)) or {}
                seats[chamber][district] = {
                    "asOf": (prev.get("asOf") if not prev.get("name") else None) or today}
                notes[chamber].append("%s %d: no sitting member listed"
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
    previous = {c: previous_roster(out_dir, cfg) for c, cfg in CHAMBERS.items()}
    built, notes = build(load(offline, save), previous, today)
    os.makedirs(out_dir, exist_ok=True)
    for chamber in ("S", "H"):
        cfg, roster = CHAMBERS[chamber], built[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for m in roster.values() if m.get("name")]
        print("Wrote %s (%d of %d seats named, %d with a party, %d with an e-mail "
              "address, %d with a Capitol office)"
              % (out_path, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("party")),
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("capitolOffice"))), file=sys.stderr)
        for note in notes[chamber]:
            print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
