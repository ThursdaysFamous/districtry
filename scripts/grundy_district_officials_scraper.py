#!/usr/bin/env python3
"""Grundy County's 21 fire, park and library district officers, from AFRs.

WHY THIS EXISTS. il/index.html dispatches Grundy in the fire, park and library
layers off boundaries dissolved from the county's own parcel fabric, and that
fabric carries a district NAME and a tax code and nothing else. That is the
`grundy-special-district-boards` gap, whose record said until 2026-09-10 that
naming these trustees needs "each body's own page one at a time".

THE COUNTY DOES NOT NAME THEM AND THE DISTRICTS THEMSELVES DO. Every Illinois
unit of local government files an Annual Financial Report with the Comptroller,
whose Contact Information section names role-holders with the title the unit
filed. comptroller_afr.py carries that route and its rules -- including which
contact values a filing witnesses as the UNIT's rather than one filer's; this
file carries only what is specific to Grundy. Measured 2026-09-10: 20 of the 21
districts file a contact block, naming 31 board officers and 11 appointed
heads.

THE RECORD'S READING OF THE COUNTY STANDS AND IS NOT CONTRADICTED. It measured
the county's own Appointed Local Public Entity Report and found it names nine
of these bodies, gives each an address and a composition sentence, and names no
individual anywhere. All of that is still true. What the record did not name is
that a SECOND publisher carries the people, which is why the route it proposed
was the slowest one available.

THE ONE THAT DOES NOT FILE IS MAZON FIRE, and it is NOT recorded as unfilable.
Its unit exists and is verified on every run (032/025/06); its Warehouse
landing page simply carries no fiscal year, so there is no report to read a
contact block out of. That is a state which can change without anyone editing
this file, so Mazon stays in the table and is reported unmatched each run
rather than moved to a "does not file" list.

TEN OF THE 21 FILE UNDER ANOTHER COUNTY, because a cross-county district files
once, under its home county: five fire districts, four library districts and
one park district serve parts of Grundy from LaSalle, Will and Livingston.

THE GEOMETRY HERE IS THE INVERSE OF WOODFORD'S AND CANNOT BE READ THE SAME WAY.
Woodford's cross-county filers hold a SLIVER of Woodford, so a sliver on the
county line nearest the filing town identified each one. Grundy's parcel fabric
is CLIPPED TO GRUNDY, so every one of these ten polygons measures 100% inside
Grundy and 0% inside the county it files in -- the shipped shape is the Grundy
PART of a district whose body lies elsewhere. Adjacency still corroborates
(every one of the ten touches the county it files in, 0-11 m, the 11 m being a
digitisation gap on Braidwood's 0.2 km2 fragment) but it cannot identify, since
several touch two counties at once.

WHAT IDENTIFIES THEM IS THE FILING'S OWN ADDRESS. Eight of the ten file from
the town they are named for -- Braidwood FPD and Fossil Ridge Library from
Braidwood, Channahon Park and Three Rivers Library from Channahon, Prairie
Creek Library from Dwight, Seneca Library from Seneca, Reddick FPD from Reddick
-- and ALLEN TWP FPD FILES FROM RANSOM, which is the one that needed checking:
Ransom is a village in Allen Township, LaSalle County, immediately across
Grundy's western line from the 8 km2 fragment the app draws. The remaining two,
DWIGHT FIRE and SENECA FIRE PROTECTION & AMBULANCE, file no address at all and
rest on name uniqueness plus adjacency: a Warehouse search returns exactly one
fire district of each name in Illinois, and each fragment touches the county
that unit files in.

THE JOIN IS AN EXPLICIT TABLE OF UNIT CODES, NOT A NAME MATCH, following Logan
and Woodford: a Warehouse search is a SUBSTRING match over unit names, so a
name join across four counties would be guesswork where naming each unit
outright cannot be got subtly wrong. Every row is checked against the
Warehouse's own label, type and county on each run -- FOUR requests cover all
21 -- so a renumbered or reassigned code fails the run instead of shipping
another district's trustees.

A SINGULAR OFFICE FILED TWICE IS ONE PERSON, AND GRUNDY IS THE FIRST COUNTY IN
THE FLEET TO SHOW IT. Prairie Creek Library files "Victoria Ferguson" as
President in one slot and "Victoria Furguson" as President in another: one
person, one seat, two spellings of a surname. No shipped AFR roster carried
that shape before this county (checked across Boone, Logan, Peoria and
Woodford), so it is handled by a rule rather than by naming her: where one
district files the SAME singular office twice under surnames within one edit of
each other, the later slot is dropped and the drop is PRINTED every run. A
person holding two DIFFERENT offices is untouched, which matters immediately --
Seneca Fire files Gerald Johnson as both President and Treasurer, and that is a
small district's real arrangement rather than a duplicate.

THE DISTRICT NAMES COME FROM THE SHIPPED BOUNDARY FILES, not from a live
service, because those files are what the card holds at render time -- the join
key has to be the string the app will look up. A name in one and not the other
fails the run rather than silently dropping a district.
"""

import argparse
import datetime
import difflib
import json
import os
import sys
import time

from comptroller_afr import (  # noqa: E402  (shared machinery — do not fork)
    PACE, SEARCH_FORM, WAREHOUSE, contact_block, enumerate_county, new_session)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA = os.path.join(REPO_ROOT, "il", "data", "app")
BOUNDARIES = {"fire": "grundy-fire-districts.json",
              "park": "grundy-park-districts.json",
              "library": "grundy-library-districts.json"}

# district name as the boundary file writes it -> the unit that files for it.
# `label`, `unit_type` and `county` are the Warehouse's own words for that unit
# and are VERIFIED on every run, so this table cannot come to name another body.
DISTRICTS = [
    # name in the boundary file    code          Warehouse label         type                        county
    ("BRACEVILLE FIRE",           "032/005/06", "Braceville",            "Fire Protection District", "Grundy"),
    ("COAL CITY FIRE",            "032/010/06", "Coal City",             "Fire Protection District", "Grundy"),
    ("GARDNER FIRE",              "032/020/06", "Gardner",               "Fire Protection District", "Grundy"),
    ("MAZON FIRE",                "032/025/06", "Mazon",                 "Fire Protection District", "Grundy"),
    ("MINOOKA FIRE",              "032/030/06", "Minooka",               "Fire Protection District", "Grundy"),
    ("MORRIS FIRE & AMBUL",       "032/040/06", "Morris Ambulance and",  "Fire Protection District", "Grundy"),
    ("S WILMINGTON FIRE",         "032/050/06", "South Wilmington",      "Fire Protection District", "Grundy"),
    ("VERONA-KINSMAN FIRE",       "032/060/06", "Verona-Kinsman",        "Fire Protection District", "Grundy"),
    ("ALLEN FIRE",                "050/010/06", "Allen Twp",             "Fire Protection District", "Lasalle"),
    ("SENECA FIRE PROT & AMBUL",  "050/120/06", "Seneca Fire Protection & Ambulance District",
                                                                         "Fire Protection District", "Lasalle"),
    ("BRAIDWOOD FIRE",            "099/160/06", "Braidwood",             "Fire Protection District", "Will"),
    ("DWIGHT FIRE",               "053/030/06", "Dwight",                "Fire Protection District", "Livingston"),
    ("REDDICK FIRE",              "053/085/06", "Reddick Community",     "Fire Protection District", "Livingston"),
    ("GODLEY PARK DISTRICT",      "032/010/12", "Godley",                "Park District",            "Grundy"),
    ("CHANNAHON PARK DISTRICT",   "099/015/12", "Channahon",             "Park District",            "Will"),
    ("COAL CITY LIBRARY",         "032/010/10", "Coal City",             "Public Library District",  "Grundy"),
    ("MORRIS AREA LIBRARY",       "032/020/10", "Morris Area",           "Public Library District",  "Grundy"),
    ("SENECA LIBRARY",            "050/020/10", "Seneca",                "Public Library District",  "Lasalle"),
    ("FOSSIL RIDGE LIBRARY",      "099/005/10", "Fossil Ridge",          "Public Library District",  "Will"),
    ("THREE RIVERS LIBRARY",      "099/060/10", "Three Rivers",          "Public Library District",  "Will"),
    ("PRAIRIE CREEK LIBRARY",     "053/070/10", "Prairie Creek",         "Public Library District",  "Livingston"),
]

# A shipped district that files NO AFR of its own, with the reason. Grundy has
# none: all 21 have a unit, and the one that files no readable contact block
# (Mazon) is a unit with no report this year rather than a body without a unit,
# so it stays in DISTRICTS and reports unmatched. The table is kept because the
# builder's cross-check reads it and because the next county will have one.
NOT_FILED = {}

KIND_OF_TYPE = {"Fire Protection District": "fire",
                "Park District": "park",
                "Public Library District": "library"}

# THE WAREHOUSE'S SPELLING OF A COUNTY IS NOT THE COUNTY'S OWN, and `filesIn`
# is the one value in this file a READER sees. The Warehouse writes "Lasalle";
# the county writes LaSalle, and so does the rest of il/index.html. THE ALIAS IS
# FOR DISPLAY ONLY -- every search and every verification still uses the
# Warehouse's own spelling, because that is the string its search matches. Will
# and Livingston are absent because the two publishers agree on them.
COUNTY_DISPLAY = {"Lasalle": "LaSalle"}

# An office one person holds. A district filing one of these TWICE has filed one
# person under two spellings, not a two-president board -- see the module
# docstring. A plural office (Trustee, Commissioner) is deliberately absent:
# repeating it is what a board looks like.
SINGULAR_OFFICES = {"president", "acting president", "vice president",
                    "treasurer", "secretary", "sec./treas.", "chairman",
                    "chief", "director", "acting director"}


def fail(msg):
    sys.exit("grundy-district-officials: FATAL — " + msg)


def surname(name):
    parts = [p for p in (name or "").replace(",", " ").split() if p]
    return parts[-1].lower() if parts else ""


def drop_refiled_duplicates(name, officers, notes):
    """Drop a singular office filed twice under one near-identical name.

    Returns the officers to keep. Every drop is appended to `notes` so a run
    says which name it removed and which it kept, rather than a board quietly
    losing a row.
    """
    kept, seen = [], {}
    for bucket, person in officers:
        role = (person.get("role") or "").strip().lower()
        if role in SINGULAR_OFFICES and role in seen:
            first = seen[role]
            close = difflib.SequenceMatcher(
                None, surname(first["name"]), surname(person["name"])).ratio()
            if close >= 0.8:
                notes.append("%s files %s twice — kept %r, dropped %r (one "
                             "person, two spellings)"
                             % (name, person.get("role"), first["name"],
                                person["name"]))
                continue
        if role in SINGULAR_OFFICES:
            seen.setdefault(role, person)
        kept.append((bucket, person))
    return kept


def shipped_district_names():
    """The `district` values the app will key on, from the boundary files."""
    names = []
    for _kind, filename in sorted(BOUNDARIES.items()):
        path = os.path.join(APP_DATA, filename)
        with open(path, encoding="utf-8") as fh:
            geojson = json.load(fh)
        found = [(f.get("properties") or {}).get("district")
                 for f in geojson.get("features") or []]
        found = [n for n in found if n]
        if not found:
            fail("%s carries no district names — the boundary file changed shape"
                 % filename)
        names.extend(found)
    return names


def verify_units(session):
    """Assert every row of DISTRICTS still names the unit it claims.

    ONE SEARCH PER COUNTY, not one per unit: enumerate_county returns every
    typed unit the Warehouse files under a county, so four requests cover all
    21 districts.
    """
    wanted = {}
    for _name, code, label, unit_type, county in DISTRICTS:
        wanted.setdefault(county, {})[code] = "%s - a %s in %s County" % (
            label, unit_type, county)
    for county, codes in sorted(wanted.items()):
        time.sleep(PACE)
        units = dict(enumerate_county(session, county))
        if not units:
            fail("the Warehouse returned no %s County units — the search "
                 "changed shape" % county)
        for code, expected in sorted(codes.items()):
            got = units.get(code)
            if got is None:
                fail("unit %s is no longer filed under %s County — the "
                     "Warehouse renumbered it, or the district dissolved"
                     % (code, county))
            if got != expected:
                fail("unit %s is now %r, expected %r — this table would ship "
                     "another district's officers" % (code, got, expected))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    shipped = shipped_district_names()
    table = {name for name, _c, _l, _t, _co in DISTRICTS} | set(NOT_FILED)
    missing = sorted(set(shipped) - table)
    extra = sorted(table - set(shipped))
    if missing or extra:
        fail("the boundary files and this table name different districts — "
             "not in the table: %s; not in the boundary files: %s"
             % (missing or "none", extra or "none"))

    s = new_session()                          # holds the ColdFusion cookie
    verify_units(s)

    warnings, unmatched, notes, districts = [], [], [], {}
    for name, code, label, unit_type, county in DISTRICTS:
        time.sleep(PACE)
        block = contact_block(s, code, "%s - a %s in %s County"
                              % (label, unit_type, county), warnings)
        if not block:
            unmatched.append("%s — unit %s files no contact block" % (name, code))
            continue
        entry = {"kind": KIND_OF_TYPE[unit_type], "comptrollerCode": code,
                 "filedFor": block["filedFor"], "office": {}}
        # A district filing under another county is stated on the record, not
        # smoothed away: a reader checking the filing needs to know where to
        # look for it.
        if county != "Grundy":
            entry["filesIn"] = COUNTY_DISPLAY.get(county, county)
        for field, value in (("address", block["street"]), ("city", block["city"]),
                             ("phone", block["phone"]), ("email", block["email"])):
            if value:
                entry["office"][field] = value
        for bucket, person in drop_refiled_duplicates(name, block["officers"], notes):
            entry.setdefault(bucket, []).append(person)
        districts[name] = entry

    for name, reason in sorted(NOT_FILED.items()):
        unmatched.append("%s — %s" % (name, reason))

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
    for n in notes:
        print("  DUPLICATE: %s" % n, file=sys.stderr)
    for u in unmatched:
        print("  NOT MATCHED: %s" % u, file=sys.stderr)
    board = sum(len(d.get("board") or []) for d in districts.values())
    heads = sum(len(d.get("heads") or []) for d in districts.values())
    print("scraped %d of %d Grundy district(s): %d board officer(s), %d "
          "appointed -> %s" % (len(districts), len(DISTRICTS) + len(NOT_FILED),
                               board, heads, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
