#!/usr/bin/env python3
"""The township officers the county lists name, for the Minnesota towns whose
board is in no election results file the state publishes.

WHAT THIS ADDS. `build_mn_town_boards.py` names the boards of the 704 towns
that hold their town election in November, from the Secretary of State's own
results. The towns that vote in March are in no file the state publishes, and
were gap mn-township-officers. Many county auditors publish a list of every
township's officers, collected each year from the towns' own certifications;
`mn_county_town_officers_scraper.py` reads those lists (names, offices and
terms only) into mn/data/source/mn-county-town-officers.json. This joins each
listed town to its TIGER township record and writes the towns the election
results do not already name to mn/data/app/mn-county-town-officers.json.

ONE SOURCE PER TOWN. A town the election results name keeps those names and
gets nothing from here: two lists on one card would disagree about who sits
whenever a seat changed hands between them, and the reader could not tell which
to believe. Where both name a town, the two are compared as a witness and the
agreement is printed every run (the county list read correctly is the claim it
tests), never merged.

A COUNTY LIST IS DATED. Each list says when it was made where it says so at
all, and every record carries the day it was read, so the card can say "on
Aitkin County's list, read 16 October 2026" and never more than that.

WHICH TOWN. A county list names a town by name within its county. It joins to
the TIGER township (LSADC 44) of the same county whose BASENAME is the same
name compared without case, spaces or punctuation, "Saint" read as "St".
ALIASES carries the four names a list prints differently from TIGER, each
re-audited every run so an entry cannot outlive the spelling it bridges; any
other name that joins nothing fails the build.

Usage:
    python3 mn/scripts/build_mn_county_town_officers.py           # fetch TIGER and write
    python3 mn/scripts/build_mn_county_town_officers.py --check   # offline gate
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, HERE)

SOURCE_FILE = os.path.join(INSTANCE, "data", "source", "mn-county-town-officers.json")
OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-county-town-officers.json")
BOARDS_FILE = os.path.join(INSTANCE, "data", "app", "mn-town-boards.json")
COUNTIES_FILE = os.path.join(INSTANCE, "data", "app", "state-counties.json")

# (county, the name the county's list prints) -> TIGER's BASENAME, each
# measured 2026-10-16 against TIGERweb's county subdivision layer.
ALIASES = {
    ("Faribault", "Blue Earth"): "Blue Earth City",  # TIGER keeps the township's full name
    ("Faribault", "Winnebago"): "Winnebago City",
    ("Marshall", "Mcrea"): "McCrea",  # the list's spelling; the town is McCrea
    ("Polk", "Grove Park"): "Grove Park-Tilden",
}

# Measured 2026-10-16: 29 counties' lists name 693 towns, 416 of them towns
# the election results do not name, with 2,019 officers between them. The
# floors sit under it so a county whose host is down for a week (its last-good
# list is kept) does not stop the refresh, while a reader that loses a format
# does.
MIN_COUNTIES = 25
MIN_TOWNS = 360
MIN_OFFICERS = 1700

OFFICES = {"Supervisor", "Supervisor (chair)", "Supervisor (vice chair)", "Clerk",
           "Treasurer", "Clerk-Treasurer", "Deputy Clerk", "Deputy Treasurer"}


def fail(msg):
    raise SystemExit("build-mn-county-town-officers: FATAL: %s" % msg)


def squash(name):
    name = re.sub(r"\bsaint\b", "st", name.lower())
    return re.sub(r"[^a-z]", "", name)


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def county_fips():
    out = {}
    for f in load(COUNTIES_FILE)["features"]:
        p = f["properties"]
        out[p["BASENAME"]] = p["COUNTY"]
    if len(out) != 87:
        fail("state-counties.json names %d counties, not 87" % len(out))
    return out


def build(source, townships):
    """source: the scraper's snapshot; townships: TIGER records keyed by
    COUSUB, as build_mn_town_boards.fetch_townships returns them."""
    fips = county_fips()
    boards = load(BOARDS_FILE)
    index = {}
    for rec in townships.values():
        if rec.get("LSADC") == "44":
            county = rec["GEOID"][2:5]
            index.setdefault((county, squash(rec["BASENAME"])), []).append(rec)
    out, used, unmatched = {}, set(), []
    agree = compared = overlap = 0
    for county, entry in sorted(source["counties"].items()):
        if county not in fips:
            fail("%r is not a Minnesota county" % county)
        for town, officers in sorted(entry["towns"].items()):
            base = ALIASES.get((county, town), town)
            if (county, town) in ALIASES:
                used.add((county, town))
            hits = index.get((fips[county], squash(base)), [])
            if len(hits) != 1:
                unmatched.append("%s County's %s (%d TIGER townships match)"
                                 % (county, town, len(hits)))
                continue
            tiger = hits[0]
            geoid = tiger["GEOID"]
            if geoid in boards:
                overlap += 1
                # the witness: how many of the election winners the county
                # list also names, by surname, since one source prints a
                # middle initial or a nickname the other does not
                listed = {squash(o["name"].split()[-1]) for o in officers}
                for seat in boards[geoid].get("seats", []):
                    if seat.get("name"):
                        compared += 1
                        agree += squash(seat["name"].split()[-1]) in listed
                continue
            rec = {
                "name": tiger["NAME"],
                "county": county,
                "read": entry["read"],
                "sourceUrl": (entry.get("townUrls") or {}).get(town) or entry["urls"][0],
                "officers": [{k: o[k] for k in ("office", "seat", "name", "termEnds") if o.get(k)}
                             for o in officers],
            }
            as_of = (entry.get("townAsOf") or {}).get(town) or entry.get("asOf")
            if as_of:
                rec["asOf"] = as_of
            out[geoid] = rec
    for key in sorted(set(ALIASES) - used):
        fail("ALIASES %s/%s is no longer printed by that county's list; "
             "remove the entry" % key)
    if unmatched:
        fail("these listed towns join no TIGER township:\n  " + "\n  ".join(unmatched))
    print("witness: the county lists carry the surnames of %d of the %d election "
          "winners in the %d towns both cover" % (agree, compared, overlap))
    return out


def check(roster, source=None):
    problems = []
    boards = load(BOARDS_FILE)
    fips = county_fips()
    officers = 0
    counties = set()
    for geoid, rec in roster.items():
        where = "%s (%s)" % (rec.get("name"), geoid)
        if not re.match(r"^27\d{8}$", geoid):
            problems.append("%r is not a Minnesota county subdivision GEOID" % geoid)
        if geoid in boards:
            problems.append("%s is named by the election results too; one source per town" % where)
        if fips.get(rec.get("county")) != geoid[2:5]:
            problems.append("%s is filed under %s County, whose code is not in its GEOID"
                            % (where, rec.get("county")))
        counties.add(rec.get("county"))
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(rec.get("read", ""))):
            problems.append("%s carries no date it was read" % where)
        if not str(rec.get("sourceUrl", "")).startswith("https://"):
            problems.append("%s carries no source address" % where)
        if not rec.get("officers"):
            problems.append("%s names nobody" % where)
        for o in rec.get("officers", []):
            officers += 1
            name = o.get("name", "")
            if o.get("office") not in OFFICES:
                problems.append("%s: %r is not a town office" % (where, o.get("office")))
            # names and offices only: no address, telephone or e-mail
            if not name or re.search(r"\d|@|https?:", name) or len(name.split()) < 2:
                problems.append("%s: %s %r is not a name alone" % (where, o.get("office"), name))
            extra = set(o) - {"office", "seat", "name", "termEnds"}
            if extra:
                problems.append("%s carries %s, which this file never publishes"
                                % (where, ", ".join(sorted(extra))))
    if source is not None:
        listed = {(e_county, squash(t)) for e_county, e in source["counties"].items()
                  for t in e["towns"]}
        for geoid, rec in roster.items():
            base = re.sub(r" township$", "", rec["name"], flags=re.I)
            alias = {squash(v): k[1] for k, v in ALIASES.items() if k[0] == rec["county"]}
            if (rec["county"], squash(alias.get(squash(base), base))) not in listed:
                problems.append("%s (%s) is in no county list the snapshot carries"
                                % (rec["name"], geoid))
    if len(counties) < MIN_COUNTIES:
        problems.append("%d counties, floor %d" % (len(counties), MIN_COUNTIES))
    if len(roster) < MIN_TOWNS:
        problems.append("%d towns, floor %d" % (len(roster), MIN_TOWNS))
    if officers < MIN_OFFICERS:
        problems.append("%d officers, floor %d" % (officers, MIN_OFFICERS))
    return problems, officers, len(counties)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to its rules, its floors and "
                         "the scraper's snapshot")
    args = ap.parse_args()
    source = load(SOURCE_FILE)
    if args.check:
        roster = load(OUT_FILE)
        problems, officers, counties = check(roster, source)
        if problems:
            for p in problems:
                print("build-mn-county-town-officers: FAIL: " + p)
            raise SystemExit(1)
        print("build-mn-county-town-officers --check: OK — %d officers in %d towns "
              "from %d counties' lists, none of them a town the election results name"
              % (officers, len(roster), counties))
        return
    import requests  # noqa: PLC0415
    import build_mn_town_boards as boards  # noqa: PLC0415
    from scraper_common import require_robots_once  # noqa: PLC0415
    # the TIGER fetch is build_mn_town_boards's, with its client; read the
    # host's policy here too, as that client, so this file asks before it fetches
    require_robots_once(boards.TIGER_LAYER, boards.USER_AGENT)
    townships = boards.fetch_townships(requests.Session())
    roster = build(source, townships)
    problems, officers, counties = check(roster, source)
    if problems:
        for p in problems:
            print("build-mn-county-town-officers: FAIL: " + p)
        raise SystemExit(1)
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(roster, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d officers in %d towns from %d counties"
          % (os.path.relpath(OUT_FILE, REPO), officers, len(roster), counties))


if __name__ == "__main__":
    main()
