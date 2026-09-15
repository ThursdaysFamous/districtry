#!/usr/bin/env python3
"""
Build mi/data/app/mi-commissioner-members.json — which commissioner holds each
Michigan county commissioner district, keyed by 3-digit county FIPS (the same
CountyFIPS mi-commissioner-districts.json carries) and read by mi/index.html's
County Commissioner District card.

WHAT IT ADDS. The district layer draws all 619 districts across 83 counties
and names nobody, because the only statewide name source is the state layer's
own Commissioner column and that column holds the November 2024 election
winners rather than the people in office now. This file names the commissioner
for the counties that publish the answer themselves. It is built in TRANCHES:
mi_commissioner_scraper.py's COUNTIES table is what yields today and its
PROBES table records every county tried and what stopped it.

THE COUNTY'S OWN PAGE WINS, ALWAYS. The scraper carries the state column's
name alongside each scraped one purely so this build can PRINT the
disagreement; nothing from that column reaches data/app. Measured 2026-09-13
across the first tranche's 76 seats: 53 agree exactly and 23 differ. Read by
hand, 7 of the 23 are a different person — Macomb 1, Muskegon 4, 5, 6 and 7,
Wayne 5 (the seat whose named commissioner died on 10 June 2025) and Wayne 8 —
and the other 16 are the same person written differently, including one typo
in the state column (Saginaw 4 "Sheldon Mattews" for Matthews). The run prints
the total and every difference; it does not try to sort them, because the test
that would (compare surnames) reads "Michael J. Howard II" against "Michael
Howard" as two people and "Matthews" against "Mattews" as two people too.

FOUR GATES, AND A COUNTY FAILING ANY OF THEM SHIPS NOTHING
------------------------------------------------------------
  1. The county's districts are exactly 1..N with no gaps and no repeats.
  2. N equals the seat count mi-commissioner-districts.json carries for that
     county's FIPS — so a redistricting or a board resize turns this run red
     instead of shipping a roster keyed to lines that moved.
  3. N equals the seat count the scraper's own table states, which is the
     second half of the same tripwire: the table is what a human read, the
     geometry is what the state publishes, and they have to agree.
  4. Every district names a person, and no two districts in one county name
     the same person — two identical names on one board is a parse collision,
     not a board.

A county that fails is named with its reason and simply does not appear; the
card falls back to what it already said. The floors below are floors, not
targets: one county changing CMS is ordinary and must not stop the other five
refreshing, a collapse must stop everything.

NO HOME ADDRESS AND NO PARTY FROM THE STATE. None of these six counties
publishes a member's home address and no parser reads an address field.
Muskegon is the only one publishing party on its own page, so party ships for
Muskegon and for nobody else; taking it from the state column would attach a
2024 fact to a 2026 person.

Usage:
    python3 mi/scripts/mi_commissioner_scraper.py      # refresh the cache
    python3 mi/scripts/build_mi_commissioner_roster.py
    python3 mi/scripts/build_mi_commissioner_roster.py --check
"""

import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)                       # mi/
APP_DATA_DIR = os.path.join(INSTANCE, "data", "app")
CACHE = os.path.join(HERE, ".cache", "mi_commissioner_roster.json")
DISTRICTS = os.path.join(APP_DATA_DIR, "mi-commissioner-districts.json")
OUT = os.path.join(APP_DATA_DIR, "mi-commissioner-members.json")

# Floors. Measured 2026-09-15: 11 counties, 119 seats. The basis is "any two
# counties may go dark": 11 - 2 = 9 counties, and 119 less the two biggest
# boards (Kent 21 + Macomb 13) = 85 seats, which is the tightest figure that
# basis allows. Raise them when a tranche lands, never lower one to get past a
# failure.
MIN_COUNTIES = 9
MIN_DISTRICTS = 85

# Fields a district row may carry, in card order. Anything else the scraper
# learns is dropped here rather than shipped unreviewed.
FIELDS = ("name", "role", "party", "phone", "email", "profileUrl")


def fail(msg):
    print("mi-commissioner-roster: FAIL — %s" % msg, file=sys.stderr)
    raise SystemExit(1)


def load(path, what):
    try:
        with open(path) as handle:
            return json.load(handle)
    except OSError as exc:
        fail("no %s at %s (%s)" % (what, path, exc))


def seats_from_geometry():
    """How many districts the shipped geometry draws per county FIPS."""
    seats = {}
    for feat in load(DISTRICTS, "commissioner districts")["features"]:
        props = feat["properties"]
        seats.setdefault(props["CountyFIPS"], set()).add(int(props["District"]))
    return {fips: nums for fips, nums in seats.items()}


def main():
    check_only = "--check" in sys.argv[1:]

    cache = load(CACHE, "commissioner cache — run mi_commissioner_scraper.py first")
    geometry = seats_from_geometry()

    directory, skipped, short = {}, [], []
    agree, differ = 0, 0
    for fips in sorted(cache.get("counties", {})):
        entry = cache["counties"][fips]
        county = entry.get("county") or fips
        keyed = entry.get("districts") or {}
        drawn = geometry.get(fips)
        if not drawn:
            skipped.append((county, "no district geometry for FIPS %s" % fips))
            continue
        want = set(str(n) for n in drawn)
        stray = sorted(set(keyed) - want, key=lambda k: (not k.isdigit(), k))
        if stray:
            skipped.append((county, "names district(s) %s the geometry does not draw "
                                    "(it draws %s)"
                            % (stray, sorted(want, key=int))))
            continue
        # A COUNTY SHORT OF ITS OWN SEAT COUNT SHIPS WHAT IT PUBLISHES, and the
        # card states the shortfall. Refusing the county instead conceals every
        # name it DOES publish in order to avoid stating one absence, which is
        # backwards: Monroe publishes eight of nine and the ninth is missing
        # because the county's own directory row for it names a district where
        # a person should be. This is Illinois's Alexander decision — the
        # roster block carries `seats` beside its members and the shortfall
        # renders in the same words — applied to a districted board.
        missing = sorted(want - set(keyed), key=int)
        if entry.get("seats") != len(drawn):
            skipped.append((county, "scraper table says %s seats, geometry draws %d"
                            % (entry.get("seats"), len(drawn))))
            continue
        names = [(rec.get("name") or "").strip() for rec in keyed.values()]
        if not all(names):
            skipped.append((county, "%d district(s) name nobody"
                            % sum(1 for n in names if not n)))
            continue
        if len(set(names)) != len(names):
            skipped.append((county, "two districts name the same person — a parse "
                                    "collision, not a board"))
            continue

        districts = {}
        for district, rec in keyed.items():
            row = {}
            for field in FIELDS:
                value = rec.get(field)
                if value not in (None, ""):
                    row[field] = value
            districts[district] = row
            state_name = (rec.get("stateColumnName") or "").strip()
            if not state_name:
                continue
            if state_name == row["name"]:
                agree += 1
            else:
                # Two buckets, not three. A surname test looks like it can
                # separate a respelling from a replacement and cannot: it reads
                # "Michael J. Howard II" against "Michael Howard" as two people
                # (the suffix is the last token) and "Sheldon Matthews" against
                # the state's "Sheldon Mattews" the same way. Every difference
                # is printed and the split is left to whoever reads the run.
                differ += 1
                print("  %s %s: county says %r, the state layer still says %r"
                      % (county, district, row["name"], state_name))
        directory[fips] = {
            "county": county,
            "seats": len(drawn),
            "sourceUrl": entry.get("sourceUrl"),
            "districts": districts,
        }
        if missing:
            # Named so the card can say which district, rather than only that
            # the count is short.
            directory[fips]["unnamedDistricts"] = missing
            short.append((county, len(drawn), missing))

    for county, why in skipped:
        print("  skipped %s — %s" % (county, why))
    for county, seats, missing in short:
        print("  %s ships %d of %d — district(s) %s named by nobody on the county's "
              "own page, stated on the card"
              % (county, seats - len(missing), seats, ", ".join(missing)))

    total = sum(len(e["districts"]) for e in directory.values())
    if len(directory) < MIN_COUNTIES:
        fail("only %d counties resolved, floor is %d" % (len(directory), MIN_COUNTIES))
    if total < MIN_DISTRICTS:
        fail("only %d districts resolved, floor is %d" % (total, MIN_DISTRICTS))

    print("  state column: %d of %d seats agree exactly, %d differ (printed above)"
          % (agree, agree + differ, differ))

    payload = {fips: directory[fips] for fips in sorted(directory)}
    rendered = json.dumps(payload, indent=1, sort_keys=True) + "\n"

    if check_only:
        current = ""
        if os.path.exists(OUT):
            with open(OUT) as handle:
                current = handle.read()
        if current != rendered:
            fail("%s is stale — re-run mi_commissioner_scraper.py and this builder"
                 % os.path.relpath(OUT, os.path.dirname(INSTANCE)))
        print("mi-commissioner-roster: OK — %d counties, %d districts, shipped file matches"
              % (len(payload), total))
        return 0

    with open(OUT, "w") as handle:
        handle.write(rendered)
    print("mi-commissioner-roster: wrote %d counties, %d districts -> %s (%s)"
          % (len(payload), total, os.path.relpath(OUT, os.path.dirname(INSTANCE)),
             datetime.now(timezone.utc).strftime("%Y-%m-%d")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
