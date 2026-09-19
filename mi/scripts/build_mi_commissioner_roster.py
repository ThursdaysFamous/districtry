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

NO HOME ADDRESS AND NO PARTY FROM THE STATE. Eight of the counties added in
tranche 5 print members' HOME addresses — Barry, Cheboygan, Hillsdale, Ionia
and Osceola in full, street and city — and no parser reads an address field,
so none of it is in the cache and none can reach the card. Party ships only
where a county prints it on its own page (Muskegon and Barry); taking it from
the state column would attach a 2024 fact to a 2026 person.

THREE WAYS A DISTRICT CAN BE UNNAMED, and each gets its own sentence on the
card, because they are not the same statement to a reader:
  * the county's own row names no person (Monroe 2, a malformed directory row);
  * the county calls the seat VACANT in its own words (Ionia 3, Clinton 4 —
    Clinton carries its own Notice of Vacancy for that seat on the same page);
  * the county contradicts itself about who holds it (Lenawee 5, CONTRADICTED).

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

# Floors. Measured 2026-09-19 after tranche 7: 48 counties, 366 seats shipped.
# The basis is "any two counties may go dark": 48 - 2 = 46 counties, and 366
# less the two biggest boards (Kent 21 + Eaton 15) = 330 seats, which is the
# tightest figure that basis allows. Raise them when a tranche lands, never
# lower one to get past a failure.
MIN_COUNTIES = 46
MIN_DISTRICTS = 330

# Fields a district row may carry, in card order. Anything else the scraper
# learns is dropped here rather than shipped unreviewed.
FIELDS = ("name", "role", "party", "phone", "email", "profileUrl")

# A DISTRICT WHOSE ROSTER ROW THE SAME COUNTY CONTRADICTS ON ANOTHER OF ITS OWN
# SURFACES. This is neither a parse failure nor a vacancy: the row names
# somebody, and the county has said in its own words on its own site that the
# naming is no longer true. Shipping the name would repeat exactly the error
# this pipeline exists to avoid — the state layer still names Wayne District
# 5's commissioner, who died in June 2025 — and calling the seat vacant would
# assert a filling nothing here can see, since a Michigan board vacancy is
# filled by appointment. So the district ships NAMED BY NOBODY with this reason
# on its card.
#
# THE ENTRY RETIRES ITSELF. It applies only while the roster still carries the
# recorded name at that district: when the county updates its own page the name
# no longer matches, the new name SHIPS, and the run prints a line telling
# whoever reads it to delete the entry. An entry naming a county that has left
# the roster FAILS the build rather than sitting unread, the property
# ACCEPTED_DROPS and EXPECTED_UNREACHABLE already have elsewhere in the fleet.
CONTRADICTED = {
    ("091", "5"): {
        "name": "Jim Daly",
        "why": "Lenawee's own News Flash of 10 September 2026 announces the "
               "death of Commissioner James \u201cJim\u201d Daly and says he "
               "represented District 5; the county's commissioner directory "
               "still lists him here. The two county surfaces disagree, so this "
               "app names nobody for this seat.",
        "source": "https://www.lenawee.mi.us/CivicAlerts.aspx?AID=3012",
        "recorded": "2026-09-15",
    },
}


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
    withheld, retire, vacant = {}, [], {}
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
        # Drop any district this county contradicts on its own other surface.
        # Done BEFORE the shortfall maths so a withheld seat counts as missing
        # exactly like a row that named nobody, and the card says which.
        for (cf, cd), note in sorted(CONTRADICTED.items()):
            if cf != fips or cd not in keyed:
                continue
            got = (keyed[cd].get("name") or "").strip()
            if got == note["name"]:
                del keyed[cd]
                withheld[(cf, cd)] = note
            else:
                retire.append((county, cd, note["name"], got))
        # A DISTRICT THE COUNTY ITSELF CALLS VACANT. This is a third case and
        # not either of the other two: the row is not malformed (Monroe) and no
        # second county surface contradicts it (Lenawee) — the county's own
        # board page states in its own words that nobody holds the seat. Ionia
        # District 3 is the first, and its page carries the previous
        # commissioner's whole entry commented out beneath the word, which is
        # why the parser strips comments before reading anything.
        for district in sorted(keyed, key=lambda k: (not k.isdigit(), k)):
            if keyed[district].get("vacant"):
                del keyed[district]
                vacant[(fips, district)] = county

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
            why = dict((cd, note["why"]) for (cf, cd), note in withheld.items()
                       if cf == fips and cd in missing)
            for (cf, cd), name in sorted(vacant.items()):
                if cf == fips and cd in missing:
                    why[cd] = ("%s County's own board page lists this district as "
                               "vacant. A Michigan board vacancy is filled by "
                               "appointment, and the county's page names no "
                               "appointee." % name)
            if why:
                # A per-district reason, because the two cases a reader meets
                # are not the same fact: Monroe's row carries no name, and
                # Lenawee's carries one the county has contradicted. A card
                # with no specific reason falls back to the generic sentence.
                directory[fips]["unnamedWhy"] = why
            short.append((county, len(drawn), missing))

    for county, why in skipped:
        print("  skipped %s — %s" % (county, why))
    for county, seats, missing in short:
        # Two different absences, so two different sentences: a row that names
        # nobody, or a row the county contradicts elsewhere on its own site.
        held = sorted(cd for (cf, cd), _n in withheld.items()
                      if cd in missing
                      and directory.get(cf, {}).get("county") == county)
        empty = sorted(cd for (cf, cd), nm in vacant.items()
                       if cd in missing and nm == county)
        bare = [d for d in missing if d not in held and d not in empty]
        parts = []
        if bare:
            parts.append("district(s) %s named by nobody on the county's own page"
                         % ", ".join(bare))
        if empty:
            parts.append("district(s) %s the county's own page calls vacant"
                         % ", ".join(empty))
        if held:
            parts.append("district(s) %s withheld, the county contradicting its "
                         "own roster" % ", ".join(held))
        print("  %s ships %d of %d \u2014 %s, stated on the card"
              % (county, seats - len(missing), seats, "; ".join(parts)))

    for (cf, cd), note in sorted(withheld.items()):
        print("  withheld %s district %s \u2014 the roster names %r, recorded "
              "%s, contradicted by %s"
              % (cf, cd, note["name"], note["recorded"], note["source"]))
    for county, cd, was, now in retire:
        print("  RETIRE the CONTRADICTED entry for %s district %s: it records %r "
              "and the county now names %r, which ships" % (county, cd, was, now))
    # An entry naming a county no longer in the roster is unread forever, so it
    # fails rather than calcifying.
    orphans = sorted(k for k in CONTRADICTED if k[0] not in directory)
    if orphans:
        fail("CONTRADICTED names %s, absent from the roster \u2014 retire the "
             "entry" % ", ".join("%s/%s" % k for k in orphans))

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
