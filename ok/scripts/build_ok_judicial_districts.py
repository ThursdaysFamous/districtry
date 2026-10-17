#!/usr/bin/env python3
"""
Build ok/data/app/ok-judicial-districts.json: Oklahoma's 26 district court
judicial districts, each a group of whole counties, dissolved from the shipped
county fabric, with every district judge office and the counties that elect it.

    python3 ok/scripts/build_ok_judicial_districts.py          # writes (needs shapely)
    python3 ok/scripts/build_ok_judicial_districts.py --check  # offline, stdlib only

The dissolve, the partition gate and the offline check are
scripts/whole_county_courts.py, shared with the other states; this file says
where Oklahoma's county lists come from and how they are read.

THE SOURCE IS THE STATE ELECTION BOARD'S ROSTER, because the statutes could
not be read. Both of the state's own publishers of the Oklahoma Statutes
refuse this project in robots.txt: the `*` group in each, which is the one
that binds this project, disallows every page, while oklegislature.gov admits
named search engines and oscn.net leaves only its news feeds open. Measured
2026-10-16 and recorded as a data-publishing hurdle. The Election Board's
"Roster of Oklahoma State and County Officers" (2024 edition, the newest)
lists every district judge office under its district with the counties whose
voters elect it, and closes with a key giving each county's district. Both parts are kept, as excerpts, in
ok/data/source/courts/ (see its README); the judges' names and home towns are
not copied, because these maps name no judge and this project never writes an
officeholder's home town.

ONE DISTRICT, SEVERAL ELECTORATES. Most districts elect every judge across the
whole district, but not all: in District 4 one office is elected by five
counties and two by the other four; in District 12 Office 2 is elected by all
three counties while Offices 1 and 3 are elected by parts; in District 14 nine
offices are elected by Pawnee and Tulsa and five by Tulsa alone. So each
district ships its offices with the counties that elect each one, and the card
lists them, rather than claiming every judge answers to every county.

TWO READINGS OF ONE DOCUMENT MUST AGREE. A district's counties are the union
of its offices' counties, and the key gives each county its district on its
own; the build stops on any county where the two disagree, and on any county
the offices put in two districts.
"""

import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))

import whole_county_courts as wcc  # noqa: E402  (FLEET_SHARED)

LABEL = "build-ok-judicial-districts"
SOURCE = os.path.join(os.path.dirname(_HERE), "data", "source", "courts")
OFFICES = "ok-roster-2024-district-judge-offices.txt"
KEY = "ok-roster-2024-key-to-districts.txt"
DISTRICTS = 26
COUNTIES = 77
OFFICE_COUNT = 75  # measured 2026-10-16 on the 2024 roster
# The roster writes one county as one word; the county fabric (TIGER's
# BASENAME) as two. Spelled out so a new difference stops the build.
ROSTER_NAMES = {"LeFlore": "Le Flore"}
KEY_ROW = re.compile(r"^([A-Z][A-Za-z]+(?: [A-Z][a-z]+)?)\s{2,}(\d+(?:,\s*\d+)*)\s+"
                     r"(\d+)\s+(\d+)\s+")


def lines(name):
    with open(os.path.join(SOURCE, name)) as fh:
        return [ln.rstrip("\n") for ln in fh if ln.strip() and not ln.startswith("#")]


def county(name):
    return ROSTER_NAMES.get(name, name)


def read_offices():
    """{district: [(office, [county, ...]), ...]} in the roster's order."""
    out = {}
    for ln in lines(OFFICES):
        m = re.match(r"^District (\d+), Office (\d+)\s*-\s*(.+)$", ln)
        if not m:
            wcc.fail(LABEL, "%s: unreadable office line %r" % (OFFICES, ln))
        d, office = int(m.group(1)), int(m.group(2))
        names = sorted(county(p.strip()) for p in m.group(3).split(",") if p.strip())
        if any(o == office for o, _n in out.get(d, [])):
            wcc.fail(LABEL, "District %d lists Office %d twice" % (d, office))
        out.setdefault(d, []).append((office, names))
    total = sum(len(v) for v in out.values())
    if total != OFFICE_COUNT:
        wcc.fail(LABEL, "the roster lists %d district judge offices, and %d were "
                 "measured; read the roster before changing OFFICE_COUNT"
                 % (total, OFFICE_COUNT))
    for d, offices in out.items():
        numbers = sorted(o for o, _n in offices)
        if numbers != list(range(1, len(numbers) + 1)):
            wcc.fail(LABEL, "District %d's offices are numbered %s" % (d, numbers))
    return out


def read_key():
    """{county: district} from the roster's key to districts by county."""
    out = {}
    for ln in lines(KEY):
        m = KEY_ROW.match(ln)
        if not m:
            wcc.fail(LABEL, "%s: unreadable key row %r" % (KEY, ln))
        name = county(m.group(1))
        if name in out:
            wcc.fail(LABEL, "the key lists %s twice" % name)
        out[name] = int(m.group(3))
    if len(out) != COUNTIES:
        wcc.fail(LABEL, "the key lists %d counties, expected %d" % (len(out), COUNTIES))
    return out


def tilings():
    offices = read_offices()
    if sorted(offices) != list(range(1, DISTRICTS + 1)):
        wcc.fail(LABEL, "the roster names districts %s, expected 1 to %d"
                 % (sorted(offices), DISTRICTS))
    key = read_key()
    rows = []
    for d in sorted(offices):
        members = sorted(set(c for _o, names in offices[d] for c in names))
        for c in members:
            if key.get(c) != d:
                wcc.fail(LABEL, "the offices put %s in District %d and the key says "
                         "District %s" % (c, d, key.get(c)))
        rows.append((d, members, {"offices": [
            {"office": o, "counties": names} for o, names in sorted(offices[d])]}))
    print("%s: %d offices in %d districts, every county agreeing with the "
          "roster's own key" % (LABEL, OFFICE_COUNT, len(rows)))
    return [wcc.Tiling("ok-judicial-districts.json", "judicial district", rows,
                       DISTRICTS,
                       "The Oklahoma State Election Board's roster of state and "
                       "county officers, 2024 edition")]


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file, write nothing")
    args = ap.parse_args()
    if args.check:
        wcc.check("ok", LABEL, tilings())
        print("%s: OK" % LABEL)
    else:
        wcc.build("ok", LABEL, tilings())


if __name__ == "__main__":
    main()
