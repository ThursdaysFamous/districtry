#!/usr/bin/env python3
"""Kankakee County's 28 fire, park and library district officers, from AFRs.

WHY THIS EXISTS. il/index.html dispatches Kankakee in the fire, park and
library layers off the county's OWN taxing-district service (k3gis.net,
Taxing_Districts2 layers 10, 5 and 3). Those three layers declare a full
contact schema — telephone, website, email — and populate NONE of it, measured
0/17, 0/4, 0/8, so they ship identity-only. That is the
`kankakee-special-districts` gap, whose record said until 2026-09-10 that what
was wanted is "a Kankakee directory of fire protection, park and library
districts with contact details".

NO SUCH DIRECTORY IS NEEDED, BECAUSE THE DISTRICTS PUBLISH IT THEMSELVES.
Every Illinois unit of local government files an Annual Financial Report with
the Comptroller, whose Contact Information section names role-holders with the
title the unit filed. comptroller_afr.py carries that route and its rules —
including which contact values a filing witnesses as the UNIT's rather than
one filer's; this file carries only what is specific to Kankakee. Measured
2026-09-10: 25 of the 27 units file a contact block, naming 33 board officers
and 15 appointed heads.

THE JOIN KEY IS A LIVE VALUE, NOT A COMMITTED FILE, and that is the one way
this differs in shape from Woodford's and Grundy's. Their boundaries ship as
GeoJSON in this repo, so the scraper reads the district names off disk. Kankakee
draws from the county's service at render time, so the names are read from that
same service here — the join key has to be the string the app will look up.
A name in the service and not in this table, or the reverse, fails the run.

TWO FEATURES, ONE DISTRICT. The fire layer publishes MANTENO FIRE ST1 and
MANTENO FIRE ST2: two STATIONS of Manteno Community Fire Protection District,
which files once. Both names are in the table against the same unit code, the
filing is fetched once and stamped onto both, and the two cards are identical
apart from the name the county gave each polygon.

THREE DISTRICTS FILE UNDER ANOTHER COUNTY, because a cross-county district
files once, under its home county: Reddick Community FPD in Livingston, Fossil
Ridge Public Library District in Will, and Central Citizens' Public Library
District in Iroquois. Each carries `filesIn` so a reader knows where to look.
Reddick and Fossil Ridge are the same two units Grundy's scraper reads, which
is what a district spanning three counties looks like from three directions.

THE ONE SHIPPED NAME WITH NO UNIT IS SUN RIVER TERRACE LIBRARY, and it is
named rather than left unmatched: the Warehouse files Sun River Terrace as a
VILLAGE (046/087/32) and no library district of that name anywhere in Illinois,
so it is a municipal library filing inside the village's own report — the shape
Minonk City Library takes in Woodford and Peoria Public Library in Peoria.

TWO FILE NOTHING THIS RUN AND THAT IS NOT THE SAME THING. Greater Momence FPD
and Limestone Twp FPD both HAVE units (046/060/06, 046/080/06) which are
verified every run; their Warehouse landing pages carry no fiscal year, so
there is no report to read. Both ship the run a filing appears, with nothing to
edit here.

THE JOIN IS AN EXPLICIT TABLE OF UNIT CODES, NOT A NAME MATCH, following Logan,
Woodford and Grundy — and Kankakee gives the sharpest reason yet. A Warehouse
search is a SUBSTRING match, so searching this county's names hits:

  * KANKAKEE PARK — the district is filed "Kankakee Valley - a Park District",
    and "Kankakee Valley" ALSO names an Airport Authority in the same county.
  * REDDICK FIRE — "Reddick" returns three units in three counties, of which
    one is a village and one a LaSalle library district.
  * The county's own names are abbreviations that do not match the filings at
    all: CABERY FIRE files as "Cabery Area", MOMENCE FIRE as "Greater Momence",
    LIMESTONE FIRE as "Limestone Twp", SALINA FIRE as "Salina Township".

Every row is checked against the Warehouse's own label, type and county on each
run — FOUR requests cover all 27 — so a renumbered or reassigned code fails the
run instead of shipping another district's officers.
"""

import argparse
import datetime
import difflib
import json
import sys
import time
import urllib.parse
import urllib.request

from comptroller_afr import (  # noqa: E402  (shared machinery — do not fork)
    PACE, SEARCH_FORM, WAREHOUSE, contact_block, enumerate_county, new_session)

# The same service il/index.html reads, and the same layer indices. A layer
# that moves breaks the app's own cards too, so this failing is the right
# signal rather than a separate thing to keep in step.
K3_LAYERS = {"fire": 10, "park": 5, "library": 3}
K3_QUERY = ("https://k3gis.net/arcgis/rest/services/BASE/Taxing_Districts2"
            "/MapServer/%d/query")

# district name as the county's service writes it -> the unit that files for it.
# `label`, `unit_type` and `county` are the Warehouse's own words for that unit
# and are VERIFIED on every run, so this table cannot come to name another body.
DISTRICTS = [
    # name in the county's layer     code          Warehouse label        type                        county
    ("AROMA FIRE",                  "046/010/06", "Aroma",               "Fire Protection District", "Kankakee"),
    ("BOURBONNAIS FIRE",            "046/020/06", "Bourbonnais",         "Fire Protection District", "Kankakee"),
    ("CABERY FIRE",                 "046/030/06", "Cabery Area",         "Fire Protection District", "Kankakee"),
    ("ESSEX FIRE",                  "046/040/06", "Essex",               "Fire Protection District", "Kankakee"),
    ("GRANT PARK FIRE",             "046/050/06", "Grant Park",          "Fire Protection District", "Kankakee"),
    ("MOMENCE FIRE",                "046/060/06", "Greater Momence",     "Fire Protection District", "Kankakee"),
    ("KANKAKEE TWP FIRE",           "046/070/06", "Kankakee Twp",        "Fire Protection District", "Kankakee"),
    ("LIMESTONE FIRE",              "046/080/06", "Limestone Twp",       "Fire Protection District", "Kankakee"),
    # Two stations of one district; see the module docstring.
    ("MANTENO FIRE  ST1",           "046/090/06", "Manteno Community",   "Fire Protection District", "Kankakee"),
    ("MANTENO FIRE  ST2",           "046/090/06", "Manteno Community",   "Fire Protection District", "Kankakee"),
    ("OTTO FIRE",                   "046/110/06", "Otto",                "Fire Protection District", "Kankakee"),
    ("PEMBROKE FIRE",               "046/120/06", "Pembroke",            "Fire Protection District", "Kankakee"),
    ("PILOT FIRE",                  "046/130/06", "Pilot Twp",           "Fire Protection District", "Kankakee"),
    ("ST. ANNE FIRE",               "046/140/06", "St. Anne",            "Fire Protection District", "Kankakee"),
    ("SALINA FIRE",                 "046/150/06", "Salina Township",     "Fire Protection District", "Kankakee"),
    ("REDDICK FIRE",                "053/085/06", "Reddick Community",   "Fire Protection District", "Livingston"),
    ("BOURBONNAIS TWP. PARK",       "046/005/12", "Bourbonnais",         "Park District",            "Kankakee"),
    ("KANKAKEE PARK",               "046/010/12", "Kankakee Valley",     "Park District",            "Kankakee"),
    ("LIMESTONE PARK",              "046/020/12", "Limestone",           "Park District",            "Kankakee"),
    ("MOMENCE PARK",                "046/030/12", "Momence",             "Park District",            "Kankakee"),
    ("BRADLEY LIBRARY",             "046/005/10", "Bradley",             "Public Library District",  "Kankakee"),
    ("MANTENO LIBRARY",             "046/010/10", "Manteno",             "Public Library District",  "Kankakee"),
    ("BOURBONNAIS LIBRARY",         "046/020/10", "Bourbonnais",         "Public Library District",  "Kankakee"),
    ("EDWARD CHIPMAN PUBLIC LIB",   "046/030/10", "Edward Chipman",      "Public Library District",  "Kankakee"),
    ("PEMBROKE PUBLIC LIBRARY",     "046/035/10", "Pembroke",            "Public Library District",  "Kankakee"),
    ("FOSSIL RIDGE LIBRARY",        "099/005/10", "Fossil Ridge",        "Public Library District",  "Will"),
    ("CENTRAL CITIZENS LIBRARY",    "038/025/10", "Central Citizens'",   "Public Library District",  "Iroquois"),
]

# A shipped district that files NO AFR of its own, with the reason. This is not
# the same as a district whose filing could not be read: a body with no unit of
# its own has nothing to look up, and saying so is more useful to the next
# reader than an unmatched line.
NOT_FILED = {
    "SUN RIVER TERRACE LIBRARY": "a municipal library inside the Village of "
                                 "Sun River Terrace, not a library district — "
                                 "the Warehouse files the village (046/087/32) "
                                 "and no library district of this name anywhere "
                                 "in Illinois, so it files within the village's "
                                 "own report and has no unit to look up",
}

KIND_OF_TYPE = {"Fire Protection District": "fire",
                "Park District": "park",
                "Public Library District": "library"}

# THE WAREHOUSE'S SPELLING OF A COUNTY IS NOT ALWAYS THE COUNTY'S OWN, and
# `filesIn` is the one value in this file a READER sees. Kankakee's three
# cross-county filers sit in Livingston, Will and Iroquois, which both
# publishers spell identically, so this table is empty — it is kept because the
# next county will need it and an absent table reads as an oversight.
COUNTY_DISPLAY = {}

# An office one person holds. A district filing one of these TWICE has filed one
# person under two spellings, not a two-president board — the shape Grundy's
# Prairie Creek Library showed. A plural office (Trustee, Commissioner) is
# deliberately absent: repeating it is what a board looks like.
SINGULAR_OFFICES = {"president", "acting president", "vice president",
                    "treasurer", "secretary", "sec./treas.", "chairman",
                    "chief", "director", "acting director"}


def fail(msg):
    sys.exit("kankakee-district-officials: FATAL — " + msg)


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


def service_district_names():
    """The `unit_name` values the app will key on, from the county's service."""
    names = []
    for kind, index in sorted(K3_LAYERS.items()):
        query = urllib.parse.urlencode({"where": "1=1", "outFields": "unit_name",
                                        "returnGeometry": "false", "f": "json"})
        url = (K3_QUERY % index) + "?" + query
        try:
            with urllib.request.urlopen(url, timeout=90) as fh:
                payload = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            fail("could not read the county's %s layer (%s): %s"
                 % (kind, url, exc))
        found = [(f.get("attributes") or {}).get("unit_name")
                 for f in payload.get("features") or []]
        found = [n for n in found if n]
        if not found:
            fail("the county's %s layer returned no unit_name values — the "
                 "service changed shape" % kind)
        names.extend(found)
    return names


def verify_units(session):
    """Assert every row of DISTRICTS still names the unit it claims.

    ONE SEARCH PER COUNTY, not one per unit: enumerate_county returns every
    typed unit the Warehouse files under a county, so four requests cover all
    27 districts.
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

    shipped = service_district_names()
    table = {name for name, _c, _l, _t, _co in DISTRICTS} | set(NOT_FILED)
    missing = sorted(set(shipped) - table)
    extra = sorted(table - set(shipped))
    if missing or extra:
        fail("the county's service and this table name different districts — "
             "not in the table: %s; not in the service: %s"
             % (missing or "none", extra or "none"))

    s = new_session()                          # holds the ColdFusion cookie
    verify_units(s)

    warnings, unmatched, notes, districts = [], [], [], {}
    blocks = {}                                # one fetch per UNIT, not per name
    for name, code, label, unit_type, county in DISTRICTS:
        if code not in blocks:
            time.sleep(PACE)
            blocks[code] = contact_block(s, code, "%s - a %s in %s County"
                                         % (label, unit_type, county), warnings)
        block = blocks[code]
        if not block:
            unmatched.append("%s — unit %s files no contact block" % (name, code))
            continue
        entry = {"kind": KIND_OF_TYPE[unit_type], "comptrollerCode": code,
                 "filedFor": block["filedFor"], "office": {}}
        # A district filing under another county is stated on the record, not
        # smoothed away: a reader checking the filing needs to know where to
        # look for it.
        if county != "Kankakee":
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
    print("scraped %d of %d Kankakee district(s): %d board officer(s), %d "
          "appointed -> %s" % (len(districts), len(DISTRICTS) + len(NOT_FILED),
                               board, heads, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
