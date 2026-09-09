#!/usr/bin/env python3
"""Logan County's seven park district officers, from their own AFR filings.

WHY THIS EXISTS. il/index.html dispatches Logan in the park layer off a
boundary the Tri-County Regional Planning Commission drew, and that dataset
carries a district NAME and nothing else -- no trustee, no address, no
telephone. That is the `logan-park-district-boards` gap, whose record said
until 2026-09-09 that "neither the commission nor the county publishes who
runs these districts".

NEITHER OF THEM DOES, AND THE DISTRICTS THEMSELVES DO. Every Illinois unit of
local government files an Annual Financial Report with the Comptroller, and
its Contact Information section names role-holders with the title the unit
filed. comptroller_afr.py carries that route and its rules; this file carries
only what is specific to Logan. Measured 2026-09-08: all seven districts file,
all seven for FY2025, every one with a street, city, telephone and e-mail.

THE JOIN IS AN EXPLICIT TABLE OF UNIT CODES, NOT A NAME MATCH, and Logan is
why the distinction is not pedantry: the Warehouse search is a SUBSTRING match
over unit names, so searching "Armington" also returns seven FARMINGTON units
in Fulton and Peoria counties. Peoria's scraper matches names because it joins
25 districts and a table would rot; Logan joins seven, where naming each unit
outright is both shorter and impossible to get subtly wrong. Each row is
checked against the Warehouse's own label and county before it is read, so a
renumbered or reassigned code fails the run instead of shipping another
district's trustees.

TWO OF THE SEVEN FILE UNDER ANOTHER COUNTY, because a cross-county district
files once, under its home county: Armington Community Park District files in
Tazewell and San Jose Park District in Mason, and neither appears in a search
for Logan. Peoria's scraper meets the same shape in Farmington and
Williamsfield and reports them unmatched -- correct there, because it does not
know which unit in another county is the same district. Here the answer was
measured, so it is written down and the districts ship.

THE DISTRICT NAMES COME FROM THE SHIPPED BOUNDARY FILE, not from a live
service, because that file is what the card holds at render time -- the join
key has to be the string the app will look up. (Peoria reads its live GIS for
the same reason: its boundaries are fetched live too.) A name that appears in
one and not the other fails the run rather than silently dropping a district.
"""

import argparse
import datetime
import json
import os
import sys
import time

from comptroller_afr import (  # noqa: E402  (shared machinery — do not fork)
    PACE, SEARCH_FORM, WAREHOUSE, contact_block, enumerate_county, new_session)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOUNDARIES = os.path.join(REPO_ROOT, "il", "data", "app",
                          "logan-park-districts.json")

# district name as the boundary file writes it -> the unit that files for it.
# `label` is the Warehouse's own name for that unit and `county` the county it
# files under; both are VERIFIED against the Warehouse on every run, so this
# table cannot quietly come to name the wrong district.
DISTRICTS = [
    ("Atlanta",         "054/010/12", "Atlanta Memorial",   "Logan"),
    ("Armington",       "090/005/12", "Armington Community", "Tazewell"),
    ("Chestnut Beason", "054/015/12", "Chestnut-Beason",    "Logan"),
    ("Emden",           "054/017/12", "Emden",              "Logan"),
    ("Lincoln",         "054/020/12", "Lincoln",            "Logan"),
    ("Mt. Pulaski",     "054/030/12", "Mt. Pulaski",        "Logan"),
    ("San Jose",        "060/020/12", "San Jose",           "Mason"),
]


def fail(msg):
    sys.exit("logan-district-officials: FATAL — " + msg)


def shipped_district_names():
    """The `district` values the app will key on, from the boundary file."""
    with open(BOUNDARIES, encoding="utf-8") as f:
        geojson = json.load(f)
    names = [(f.get("properties") or {}).get("district")
             for f in geojson.get("features") or []]
    names = [n for n in names if n]
    if not names:
        fail("%s carries no district names — the boundary file changed shape"
             % os.path.relpath(BOUNDARIES, REPO_ROOT))
    return names


def verify_units(session):
    """Assert every row of DISTRICTS still names the unit it claims.

    ONE SEARCH PER COUNTY, not one per unit: enumerate_county returns every
    typed unit the Warehouse files under a county, so three requests cover all
    seven districts.
    """
    wanted = {}
    for _name, code, label, county in DISTRICTS:
        wanted.setdefault(county, {})[code] = label
    for county, codes in sorted(wanted.items()):
        time.sleep(PACE)
        units = dict(enumerate_county(session, county))
        for code, label in sorted(codes.items()):
            got = units.get(code)
            if got is None:
                fail("unit %s is no longer filed under %s County — the "
                     "Warehouse renumbered it, or the district dissolved"
                     % (code, county))
            expected = "%s - a Park District in %s County" % (label, county)
            if got != expected:
                fail("unit %s is now %r, expected %r — this table would ship "
                     "another district's officers" % (code, got, expected))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    shipped = shipped_district_names()
    table = {name for name, _c, _l, _co in DISTRICTS}
    missing = sorted(set(shipped) - table)
    extra = sorted(table - set(shipped))
    if missing or extra:
        fail("the boundary file and this table name different districts — "
             "not in the table: %s; not in the boundary file: %s"
             % (missing or "none", extra or "none"))

    s = new_session()                          # holds the ColdFusion cookie
    verify_units(s)

    warnings, unmatched, districts = [], [], {}
    for name, code, label, county in DISTRICTS:
        time.sleep(PACE)
        block = contact_block(s, code, "%s (%s County)" % (label, county),
                              warnings)
        if not block:
            unmatched.append("%s — unit %s files no contact block" % (name, code))
            continue
        entry = {"kind": "park", "comptrollerCode": code,
                 "filedFor": block["filedFor"], "office": {}}
        # A district filing under another county is stated on the record, not
        # smoothed away: a reader checking the filing needs to know where to
        # look for it.
        if county != "Logan":
            entry["filesIn"] = county
        for field, value in (("address", block["street"]), ("city", block["city"]),
                             ("phone", block["phone"]), ("email", block["email"])):
            if value:
                entry["office"][field] = value
        for bucket, person in block["officers"]:
            entry.setdefault(bucket, []).append(person)
        districts[name] = entry

    if not districts:
        for w in warnings:
            print("  WARN: %s" % w, file=sys.stderr)
        for u in unmatched:
            print("  NOT MATCHED: %s" % u, file=sys.stderr)
        fail("no district files a contact block — the search or the form broke")

    payload = {
        "source": "Illinois Comptroller, Annual Financial Report — Contact Information",
        "sourceUrl": WAREHOUSE,
        "officialsPage": SEARCH_FORM,
        "generated": datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "districts": districts,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")

    for w in warnings:
        print("  WARN: %s" % w, file=sys.stderr)
    for u in unmatched:
        print("  NOT MATCHED: %s" % u, file=sys.stderr)
    board = sum(len(d.get("board") or []) for d in districts.values())
    heads = sum(len(d.get("heads") or []) for d in districts.values())
    print("scraped %d of %d Logan park district(s): %d board officer(s), %d "
          "appointed -> %s" % (len(districts), len(DISTRICTS), board, heads,
                               args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
