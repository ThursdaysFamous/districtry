#!/usr/bin/env python3
"""Woodford County's 26 fire, park and library district officers, from AFRs.

WHY THIS EXISTS. il/index.html dispatches Woodford in the fire, park and
library layers off boundaries dissolved from the county's own parcel fabric,
and that fabric carries a district NAME and a tax code and nothing else -- no
trustee, no address, no telephone. That is the
`woodford-special-district-boards` gap, whose record said until 2026-09-10
that "the county publishes no list of the people who run these districts".

THE COUNTY DOES NOT AND THE DISTRICTS THEMSELVES DO. Every Illinois unit of
local government files an Annual Financial Report with the Comptroller, whose
Contact Information section names role-holders with the title the unit filed.
comptroller_afr.py carries that route and its rules -- including which contact
values a filing witnesses as the UNIT's rather than one filer's; this file
carries only what is specific to Woodford. Measured 2026-09-10: 25 of the 26
districts file a contact block.

THE 26TH IS NOT A FAILURE AND IS NAMED HERE RATHER THAN LEFT UNMATCHED.
MINONK CITY LIBRARY is a MUNICIPAL library, not a library district -- the
shipped boundary file says so in its own note, its territory being the City of
Minonk -- so it files inside the city's AFR and has no unit of its own. Peoria
meets the same shape in Peoria Public Library and Peoria Heights.

EIGHT OF THE 25 FILE UNDER ANOTHER COUNTY, because a cross-county district
files once, under its home county: six fire districts and two library
districts serve slivers of Woodford from McLean, Tazewell and LaSalle. Peoria's
scraper reports its two as unmatched -- correct there, because it does not know
which unit in another county is the same district. Here the answer was
measured, so it is written down:

  * SEVEN ARE NAMED FOR THE TOWN THEY FILE FROM, and the Woodford territory of
    each is a small sliver on the edge of the county nearest that town. Carlock
    (42 km2) and Hudson (1 km2) sit on Woodford's southern line, with Carlock
    and Hudson villages in McLean just across it; Gridley (5 km2) on the
    eastern line, Gridley village in McLean just east; Dana (5 km2) in the
    north-east corner, Dana village in LaSalle beyond it; Deer Creek (11 km2)
    on the south-west line, Deer Creek village in Tazewell below it.
  * CENTRAL FIRE DISTRICT IS THE ONE WHOSE NAME NAMES NO TOWN, so it gets its
    own reasoning rather than the pattern's. Its Woodford territory is a 9 km2
    sliver on the western line at 40.748-40.772 N, and Tazewell's Central Fire
    Protection District files from 24651 Spring Creek Rd, WASHINGTON -- the
    town immediately south of that sliver. It is also the only unit in Illinois
    filed as "Central - a Fire Protection District"; the Warehouse's other
    Central-prefixed fire districts are Central Adams, Central Groveland,
    Central Stickney, Central Warren County and Centralia, none of them
    adjacent to Woodford.

THE JOIN IS AN EXPLICIT TABLE OF UNIT CODES, NOT A NAME MATCH, following Logan
rather than Peoria: a Warehouse search is a SUBSTRING match over unit names, so
a name join across four counties would be guesswork where naming each unit
outright cannot be got subtly wrong. Every row is checked against the
Warehouse's own label, type and county on each run -- FOUR requests cover all
25 -- so a renumbered or reassigned code fails the run instead of shipping
another district's trustees.

THE DISTRICT NAMES COME FROM THE SHIPPED BOUNDARY FILES, not from a live
service, because those files are what the card holds at render time -- the join
key has to be the string the app will look up. A name in one and not the other
fails the run rather than silently dropping a district.
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
APP_DATA = os.path.join(REPO_ROOT, "il", "data", "app")
BOUNDARIES = {"fire": "woodford-fire-districts.json",
              "park": "woodford-park-districts.json",
              "library": "woodford-library-districts.json"}

# district name as the boundary file writes it -> the unit that files for it.
# `label`, `unit_type` and `county` are the Warehouse's own words for that unit
# and are VERIFIED on every run, so this table cannot come to name another body.
DISTRICTS = [
    # name in the boundary file        code           Warehouse label      type                        county
    ("Benson Fire District",           "102/010/06", "Benson",            "Fire Protection District", "Woodford"),
    ("Congerville Fire District",      "102/020/06", "Congerville",       "Fire Protection District", "Woodford"),
    ("El Paso Fire District",          "102/030/06", "El Paso",           "Fire Protection District", "Woodford"),
    ("Eureka-Goodfield Fire District", "102/040/06", "Eureka-Goodfield",  "Fire Protection District", "Woodford"),
    ("Germantown Fire District",       "102/050/06", "Germantown",        "Fire Protection District", "Woodford"),
    ("Metamora Rural Fire District",   "102/060/06", "Metamora",          "Fire Protection District", "Woodford"),
    ("Minonk Fire District",           "102/063/06", "Minonk",            "Fire Protection District", "Woodford"),
    ("Roanoke Fire District",          "102/065/06", "Roanoke",           "Fire Protection District", "Woodford"),
    ("Secor Fire District",            "102/070/06", "Secor",             "Fire Protection District", "Woodford"),
    ("Spring Bay Fire District",       "102/080/06", "Spring Bay",        "Fire Protection District", "Woodford"),
    ("Washburn Fire District",         "102/090/06", "Washburn",          "Fire Protection District", "Woodford"),
    ("Carlock Fire District",          "064/040/06", "Carlock",           "Fire Protection District", "Mclean"),
    ("Gridley Fire Protection District", "064/100/06", "Gridley",         "Fire Protection District", "Mclean"),
    ("Hudson Fire District",           "064/110/06", "Hudson",            "Fire Protection District", "Mclean"),
    ("Central Fire District",          "090/040/06", "Central",           "Fire Protection District", "Tazewell"),
    ("Deer Creek Fire District",       "090/070/06", "Deer Creek",        "Fire Protection District", "Tazewell"),
    ("Dana Fire District",             "050/020/06", "Dana",              "Fire Protection District", "Lasalle"),
    ("Grant Memorial Park District",   "102/010/12", "Grant Memorial",    "Park District",            "Woodford"),
    ("Metamora Park District",         "102/015/12", "Metamora",          "Park District",            "Woodford"),
    ("Roanoke Park District",          "102/020/12", "Roanoke",           "Park District",            "Woodford"),
    ("El Paso District Library",       "102/015/10", "El Paso",           "Public Library District",  "Woodford"),
    ("Eureka Library District",        "102/005/10", "Eureka",            "Public Library District",  "Woodford"),
    ("IL Prairie Library District",    "102/010/10", "Illinois Prairie",  "Public Library District",  "Woodford"),
    ("Carlock Library District",       "064/065/10", "Carlock",           "Public Library District",  "Mclean"),
    ("Deer Creek Library District",    "090/010/10", "Deer Creek",        "Public Library District",  "Tazewell"),
]

# A shipped district that files NO AFR of its own, with the reason. This is not
# the same as a district whose filing could not be read: a body with no unit of
# its own has nothing to look up, and saying so is more useful to the next
# reader than an unmatched line.
NOT_FILED = {
    "Minonk City Library": "a municipal library inside the City of Minonk, "
                           "not a library district — it files within the "
                           "city's own report and has no unit of its own",
}

KIND_OF_TYPE = {"Fire Protection District": "fire",
                "Park District": "park",
                "Public Library District": "library"}

# THE WAREHOUSE'S SPELLING OF A COUNTY IS NOT THE COUNTY'S OWN, and `filesIn`
# is the one value in this file a READER sees. The Warehouse writes "Mclean"
# and "Lasalle"; the counties write McLean and LaSalle, and so does the rest of
# il/index.html -- two cards saying "Mclean County" beside a dozen saying
# "McLean County" is one site spelling one county two ways.
#
# THE ALIAS IS FOR DISPLAY ONLY. Every search and every verification still uses
# the Warehouse's own spelling, because that is the string its search matches;
# only the value that rides the card is rewritten. A county not listed here
# ships exactly as the Warehouse writes it, which is right for Woodford and
# Tazewell, where the two agree.
COUNTY_DISPLAY = {"Mclean": "McLean", "Lasalle": "LaSalle"}


def fail(msg):
    sys.exit("woodford-district-officials: FATAL — " + msg)


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
    25 districts.
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

    warnings, unmatched, districts = [], [], {}
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
        if county != "Woodford":
            entry["filesIn"] = COUNTY_DISPLAY.get(county, county)
        for field, value in (("address", block["street"]), ("city", block["city"]),
                             ("phone", block["phone"]), ("email", block["email"])):
            if value:
                entry["office"][field] = value
        for bucket, person in block["officers"]:
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
    for u in unmatched:
        print("  NOT MATCHED: %s" % u, file=sys.stderr)
    board = sum(len(d.get("board") or []) for d in districts.values())
    heads = sum(len(d.get("heads") or []) for d in districts.values())
    print("scraped %d of %d Woodford district(s): %d board officer(s), %d "
          "appointed -> %s" % (len(districts), len(DISTRICTS) + len(NOT_FILED),
                               board, heads, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
