#!/usr/bin/env python3
"""The supervisors, clerk and treasurer of every Minnesota town that holds its
town election in November, from the Secretary of State's own election results,
every name dated to the election that seated it.

WHAT THIS PUBLISHES AND WHAT IT DOES NOT. A Minnesota town holds its town
general election either in March or, if it has chosen the alternative date, in
November (Minn. Stat. 205.075). November town contests are reported to the
Secretary of State and appear in the same `local.txt` results file
`build_mn_city_councils.py` reads ("Town Supervisor Seat B (Acoma Township)",
"Town Clerk (Acoma Township)"). March town elections are run by the towns
themselves and are in no results file this host publishes: the four March
election days 2023-2026 answer 404 on electionresultsfiles.sos.mn.gov
(measured 2026-10-15). So this file names the boards of the towns that vote in
November (706 towns in the 2022-2025 files, measured 2026-10-15, 704 of
them on the map) and nothing
about the rest of the 1,797. That remainder is gap mn-township-officers.

A winner is a fact with a date on it, not a statement of who holds the seat
today: a supervisor who has resigned, and the person the board appointed in
their place (367.03 subd. 6), are in no results file. So every name carries its
election, and the card says so in words — the council roster's posture.

TERMS, from the statute and not from the file. A November town elects its
supervisors and other officers for four years (367.03 subd. 4), or its
supervisors for six where the town has adopted subd. 4a, with the clerk and
treasurer in alternate years. So the two even-year generals since 2022 elect
every seat on a four-year board once, and a seat whose six-year term began in
November 2020 is in neither file. Such a seat is simply ABSENT here rather than
named from an older file: reading 2020 would put a pre-2022 winner on a board
whose seat letters may have been rearranged since, and the card says that a
seat not listed was not on a November ballot since 2022.

ONE SEAT PER OFFICE. Town supervisor contests name their seat ("Seat A",
"Seat 2"), so each office is one seat, held by whoever won the most recent
general for it, regular or special. "Town Supervisor At Large" elects as many
as its contest says; the clerk, the treasurer and a combined clerk-treasurer
are one seat each. The fill rules, the four ways a contest names nobody and the
rule for a person who won two seats are `build_mn_city_councils.py`'s, imported
rather than copied.

WHICH TOWN. The results name a town by its Census county subdivision code in
their sixth field, the last five digits of the subdivision's GEOID, which is
unique within Minnesota. Every code must join to exactly one TIGER township
record whose name is the results file's name, compared without case or spaces
("MeadowBrook" against "Meadow Brook"); a code with no such record fails the
build unless NO_TIGER_TOWNSHIP records why.

Usage:
    python3 mn/scripts/build_mn_town_boards.py          # fetch and write
    python3 mn/scripts/build_mn_town_boards.py --check  # offline gate
    python3 mn/scripts/build_mn_town_boards.py --cache DIR   # read saved local.txt files
"""

import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, HERE)

import build_mn_city_councils as council  # noqa: E402

USER_AGENT = council.USER_AGENT
OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-town-boards.json")
TIGER_LAYER = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
               "Places_CouSub_ConCity_SubMCD/MapServer/1/query")
TOWNSHIP_LSADC = "44"

OFFICE_RE = re.compile(
    r"^(?P<special>Special Election for )?Town "
    r"(?:Supervisor (?:Seat (?P<seat>\w+)|(?P<large>at Large))"
    r"|(?P<office>Clerk - Treasurer|Clerk|Treasurer))"
    r" \((?P<town>[^)]+?)(?: Township)?\)"
    r"(?: \(Elect (?P<elect>\d+)\))?"
    r"(?P<sprimary> \(Special Primary\))?$", re.I)

# Codes the results file carries that no TIGER township record does. Each is
# printed every run and FAILS once TIGER carries it again or the results stop
# naming it, so an entry cannot outlive what it describes.
NO_TIGER_TOWNSHIP = {
    "36440": ("Lent", "2026-10-15: TIGERweb's county subdivision layer carries "
              "no record with this code, so no point on the map answers Lent "
              "Township and its board has no card to sit on"),
    "37034": ("Lima", "2026-10-15: TIGERweb's county subdivision layer carries "
              "no record with this code, so no point on the map answers Lima "
              "Township and its board has no card to sit on"),
}

# Measured 2026-10-15: 2,813 of 3,115 seats named across 704 towns; 292 of the
# 302 left were won by write-in votes, which the results do not name. The
# floors sit under it so a canvass that leaves a few seats pending does not stop the
# refresh, while a parse that loses a file or a field does.
MIN_TOWNS = 680
MIN_NAMED = 2700


def fail(msg):
    raise SystemExit("build-mn-town-boards: FATAL: %s" % msg)


def squash(name):
    return re.sub(r"[^a-z]", "", name.lower())


def fetch_townships(session):
    from scraper_common import require_robots_once  # noqa: PLC0415
    require_robots_once(TIGER_LAYER, USER_AGENT)
    resp = session.get(TIGER_LAYER, params={
        "where": "STATE='27'", "outFields": "GEOID,NAME,BASENAME,COUSUB,LSADC",
        "returnGeometry": "false", "f": "json", "resultRecordCount": 5000,
    }, headers={"User-Agent": USER_AGENT}, timeout=council.REQUEST_TIMEOUT)
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:
        fail("TIGERweb answered an error: %r" % body["error"])
    if body.get("exceededTransferLimit"):
        fail("TIGERweb truncated the county subdivision list")
    rows = [f["attributes"] for f in body.get("features", [])]
    # 2,762 records measured 2026-09-29 (mn/index.html's Township or City
    # card); a short answer is a failure, not a smaller state
    if len(rows) < 2700:
        fail("TIGERweb returned %d county subdivisions, expected about 2,762"
             % len(rows))
    return {r["COUSUB"]: r for r in rows}


def office_key(m):
    if m.group("seat"):
        label = m.group("seat")
        return "Supervisor, Seat " + (label.upper() if label.isalpha() else label)
    if m.group("large"):
        return "Supervisor, at large"
    return {"clerk - treasurer": "Clerk-Treasurer", "clerk": "Clerk",
            "treasurer": "Treasurer"}[m.group("office").lower()]


def contests(elections):
    found = []
    for day in sorted(elections):
        groups = {}
        for line in elections[day].splitlines():
            if not line.strip():
                continue
            f = line.split(";")
            if len(f) < 16:
                fail("%s: a line with %d fields: %r" % (day, len(f), line[:120]))
            m = OFFICE_RE.match(f[4].strip())
            if not m:
                if re.match(r"^(Special Election for )?Town ", f[4].strip()):
                    fail("%s: a town contest this parser does not read: %r"
                         % (day, f[4].strip()))
                continue
            groups.setdefault((f[5].strip(), f[4].strip()), (m, []))[1].append(f)
        for (code, office), (m, rows) in sorted(groups.items()):
            found.append({
                "date": day, "code": code, "town": m.group("town"),
                "office": office, "key": office_key(m),
                "special": bool(m.group("special")),
                "labelled_primary": bool(m.group("sprimary")),
                "rcv": False, "elect": int(m.group("elect") or 1),
                "candidates": [(r[7].strip(), int(r[13])) for r in rows],
            })
    return found


def seat_order(key):
    if key.startswith("Supervisor, Seat "):
        label = key[len("Supervisor, Seat "):]
        return (0, label.isalpha(), label.zfill(3))
    return {"Supervisor, at large": (1,), "Clerk": (2,), "Clerk-Treasurer": (3,),
            "Treasurer": (4,)}[key]


def build(found, townships, today):
    by = {}
    names = {}
    for c in found:
        by.setdefault(c["code"], {}).setdefault(c["key"], []).append(c)
        names.setdefault(c["code"], set()).add(c["town"])
    roster, skipped = {}, []
    for code in sorted(by):
        rec = townships.get(code)
        if rec is None or rec["LSADC"] != TOWNSHIP_LSADC:
            if code in NO_TIGER_TOWNSHIP and rec is None:
                skipped.append(code)
                continue
            fail("results code %s (%s) joins %s, not a TIGER township"
                 % (code, ", ".join(sorted(names[code])),
                    rec["NAME"] if rec else "no TIGER record"))
        for n in names[code]:
            if squash(n) != squash(rec["BASENAME"]):
                fail("results code %s names %r, TIGER names %r"
                     % (code, n, rec["NAME"]))
        offices = by[code]
        lettered = [k for k in offices if re.match(r"^Supervisor, Seat [A-Z]$", k)]
        numbered = [k for k in offices if re.match(r"^Supervisor, Seat \d+$", k)]
        seats = []
        for key in sorted(offices, key=seat_order):
            events = offices[key]
            n = max([c["elect"] for c in events if not c["special"]] or [1])
            seats.extend(council.fill(code, key, n, events, today))
        if lettered and numbered:
            # The town has renamed its seats between elections, so a seat
            # under the old name may be a seat re-elected under the new one.
            # Keep only the newer naming's seats named; the older ones say why.
            newest = {k: max(c["date"] for c in offices[k]) for k in lettered + numbered}
            old = numbered if max(newest[k] for k in lettered) > max(
                newest[k] for k in numbered) else lettered
            for s in seats:
                if s["seat"] in old and s.get("name"):
                    s["unnamed"] = ("%s won this seat on %s under a name the "
                                    "town has since stopped using, so it may be "
                                    "a seat re-elected since under its new name"
                                    % (s.pop("name"), s["election"]))
        council.vacate_moved(seats)
        roster[rec["GEOID"]] = {"name": rec["NAME"], "seats": seats}
    for code, (name, why) in NO_TIGER_TOWNSHIP.items():
        if code not in skipped:
            fail("NO_TIGER_TOWNSHIP %s (%s) no longer describes the data — TIGER "
                 "carries it again or the results stopped naming it; drop the "
                 "entry" % (code, name))
        print("  not joined: %s Township (%s) — %s" % (name, code, why))
    return roster


def check(roster):
    problems = []
    named = total = 0
    for geoid, rec in roster.items():
        if not re.match(r"^27\d{8}$", geoid):
            problems.append("%r is not a Minnesota county subdivision GEOID" % geoid)
        names = [s["name"].lower() for s in rec.get("seats", []) if s.get("name")]
        twice = sorted({n for n in names if names.count(n) > 1})
        if twice:
            problems.append("%s names %s for more than one seat"
                            % (rec.get("name"), ", ".join(twice)))
        if not rec.get("seats"):
            problems.append("%s carries no seats" % rec.get("name"))
        for s in rec.get("seats", []):
            total += 1
            if s.get("name"):
                named += 1
                if not s.get("election") or not s.get("sourceUrl"):
                    problems.append("%s %s names somebody without the election "
                                    "that seated them" % (rec.get("name"), s.get("seat")))
            elif not s.get("unnamed"):
                problems.append("%s %s names nobody and says nothing about why"
                                % (rec.get("name"), s.get("seat")))
    if len(roster) < MIN_TOWNS:
        problems.append("%d towns, floor %d" % (len(roster), MIN_TOWNS))
    if named < MIN_NAMED:
        problems.append("%d seats named, floor %d" % (named, MIN_NAMED))
    return problems, named, total


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped roster to its own rules and floors")
    ap.add_argument("--cache", help="read saved <YYYYMMDD>.txt local results files "
                                    "from this folder instead of fetching them")
    args = ap.parse_args()
    if args.check:
        with open(OUT_FILE, encoding="utf-8") as fh:
            roster = json.load(fh)
        problems, named, total = check(roster)
        if problems:
            for p in problems:
                print("build-mn-town-boards: FAIL: " + p)
            raise SystemExit(1)
        print("build-mn-town-boards --check: OK — %d of %d seats named across %d "
              "November-election towns, each dated to the election that seated it"
              % (named, total, len(roster)))
        return
    import requests  # noqa: PLC0415
    session = requests.Session()
    today = datetime.date.today()
    townships = fetch_townships(session)
    if args.cache:
        elections = council.read_cache(args.cache)
    else:
        elections = council.fetch_elections(session, today)
    found = contests(elections)
    roster = build(found, townships, today)
    problems, named, total = check(roster)
    if problems:
        for p in problems:
            print("build-mn-town-boards: FAIL: " + p)
        raise SystemExit(1)
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(roster, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d towns, %d of %d seats named"
          % (os.path.relpath(OUT_FILE, REPO), len(roster), named, total))


if __name__ == "__main__":
    main()
