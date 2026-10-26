#!/usr/bin/env python3
"""
Build tn/data/app/tn-school-board-from-commission.json: the school board
districts of 38 Tennessee counties whose board of education is elected from
the county commission's own districts, drawn from the commission districts
this app already ships.

    python3 tn/scripts/build_tn_school_board_from_commission.py           # build, check, write
    python3 tn/scripts/build_tn_school_board_from_commission.py --check   # rebuild in memory, compare

Both modes are offline and need only the standard library: the input is
tn/data/app/tn-commission-districts.json, built from the Comptroller of the
Treasury's map by build_tn_commission_districts.py beside this file. --check
is run by build_tn_school_board_districts.py --check, which CI runs, so this
file is gated without a workflow step of its own.

WHY THESE COUNTIES. The Comptroller publishes a map of school board districts
for eighteen counties (build_tn_school_board_districts.py). For the other 77,
no office publishes one. But a county board of education is set up by the
county's private acts, and many of those acts say the board is elected from
the commission's districts: "coextensive with the county legislative body
districts established by resolution of the county legislative body from time
to time" (Bradley, Private Acts of 2002, Chapter 163) is the common wording.
Each county's acts were read on the University of Tennessee County Technical
Assistance Service's site (ctas.tennessee.edu, "Private Acts" for the county,
chapter VI "Education"), 2026-10-26. A county is drawn here ONLY where a
government source says how its board districts relate to the commission's:

  * SAME_AS_COMMISSION (33 counties): the act says the school districts are
    the commission districts, one for one, and either follows the commission
    when it redistricts ("from time to time", "as now or hereafter
    constituted", "modified when ... modified") or was written for the
    commission's current districts. Each district here is a copy of the
    commission district, coordinate for coordinate. Bedford and Decatur's acts
    say "magisterial districts ... as now constituted or may hereafter be
    constituted", the old name for the same districts.
  * GROUPED (5 counties): each school district is two or three whole
    commission districts, and the source names which: an act for Putnam
    (Private Acts of 1993, Chapter 90, "two adjoining", with the pairs as the
    school system's own board page lists them), Rutherford and Warren; the
    county election commission's 2022 official ballot for Coffee; and the
    county election commission's precinct chart, revised 25 February 2026, for
    Montgomery. Each district here is the union of its commission districts,
    made by cancelling the edges the commission districts share. Both sides of
    a shared edge carry the same vertices in the shipped file (measured
    2026-10-26 against shapely's union: the same polygons to 0.0 area), and the
    build refuses a group whose edges do not cancel into one ring, which is
    also the test that its districts adjoin.

Held, and drawn nowhere until a source settles them (tn/WATCH.md lists each
with its reason): Haywood, whose 1993 act pairs commission districts 1 and 5,
which no longer touch; Grundy, whose act names a different number of districts
from the commission's map; Hamblen and Dickson, whose acts pair districts by
numbers that may since have changed; the counties whose acts say "magisterial
districts" with no "hereafter" (Hardin, Humphreys, Moore, Overton); the
counties whose acts say nothing about the commission (Loudon, Monroe and
others), and Gibson, which has special school districts and no county board.

A DISTRICT IS NOT A SEAT. Some of these acts elect two or three members from
a district (Benton, Campbell, Grainger, Lake, McMinn, Polk), so the card says a
district may elect more than one member and names no count.

A CITY OR SPECIAL SCHOOL DISTRICT. Several of these counties also have a city
or special school district (Oak Ridge in Anderson, Cleveland in Bradley,
Murfreesboro in Rutherford, Franklin in Williamson). Whether its residents vote
for the county board differs by county and was not read, so these districts
are drawn over the whole county and the card says to ask the county election
commission.

The `basis` property carries the sentence the card prints about where the
district comes from, written here, so the card and this table cannot disagree.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "..", "data", "app")
SOURCE = os.path.join(APP, "tn-commission-districts.json")
COMPTROLLER = os.path.join(APP, "tn-school-board-districts.json")
OUT = os.path.join(APP, "tn-school-board-from-commission.json")
INDEX = os.path.join(HERE, "..", "index.html")
LABEL = "build_tn_school_board_from_commission"

# county name: (number of commission districts, the act)
SAME_AS_COMMISSION = {
    "Anderson": (8, "the Private Acts of 2002, Chapter 101"),
    "Bedford": (9, "the Private Acts of 1974, Chapter 293"),
    "Benton": (6, "the Private Acts of 2002, Chapter 87"),
    "Bradley": (7, "the Private Acts of 2002, Chapter 163"),
    "Campbell": (5, "the Private Acts of 1993, Chapter 15"),
    "Carter": (8, "the Private Acts of 2002, Chapter 76"),
    "Decatur": (9, "the Private Acts of 1977, Chapter 37"),
    "Franklin": (8, "the Private Acts of 1933, Chapter 108, as rewritten in 2000"),
    "Grainger": (5, "the Private Acts of 1972, Chapter 392, as amended"),
    "Hamilton": (11, "the Private Acts of 2022, Chapter 50"),
    "Hawkins": (7, "the Private Acts of 1939, Chapter 129, as amended"),
    "Henderson": (7, "the Private Acts of 1992, Chapter 192"),
    "Hickman": (7, "the Private Acts of 2002, Chapter 108"),
    "Jackson": (6, "the Private Acts of 1992, Chapter 209"),
    "Lake": (3, "the Private Acts of 2012, Chapter 77"),
    "Lauderdale": (8, "the Private Acts of 2002, Chapter 79"),
    "Lewis": (9, "the Private Acts of 1992, Chapter 184"),
    "Lincoln": (8, "the Private Acts of 1937, Chapter 93, as amended"),
    "Marion": (5, "the Private Acts of 2002, Chapter 129"),
    "Marshall": (9, "the Private Acts of 1982, Chapter 282"),
    "Maury": (11, "the Private Acts of 2012, Chapter 46"),
    "McMinn": (5, "the Private Acts of 1999, Chapter 61"),
    "McNairy": (7, "the Private Acts of 1992, Chapter 239, as amended"),
    "Meigs": (5, "the Private Acts of 2002, Chapter 135"),
    "Obion": (7, "the Private Acts of 2002, Chapter 139"),
    "Polk": (4, "the Private Acts of 2022, Chapter 64"),
    "Rhea": (9, "the Private Acts of 2002, Chapter 104"),
    "Sequatchie": (9, "the Private Acts of 2002, Chapter 83"),
    "Smith": (8, "the Private Acts of 2002, Chapter 84"),
    "Tipton": (9, "the Private Acts of 2002, Chapter 140"),
    "Wayne": (7, "the Private Acts of 1953, Chapter 89, as amended"),
    "Weakley": (9, "the Private Acts of 2002, Chapter 80"),
    "Williamson": (12, "the Private Acts of 1972, Chapter 323, as amended"),
}

# county name: (number of commission districts, what the source is, the word
# for one school district, [commission districts making up each, in order])
GROUPED = {
    "Coffee": (9, "The Coffee County Election Commission's official ballot of August "
               "2022 elects each of the county's three school board seats from three "
               "of the county commission's districts", "Seat",
               [[1, 3, 4], [2, 6, 7], [5, 8, 9]]),
    "Montgomery": (21, "The Montgomery County Election Commission's precinct chart, "
                   "revised 25 February 2026, makes each of the county's seven school "
                   "board districts three of the county commission's districts", "District",
                   [[9, 18, 20], [4, 5, 6], [8, 12, 16], [7, 10, 11], [13, 14, 17],
                    [1, 2, 21], [3, 15, 19]]),
    "Putnam": (12, "The Private Acts of 1993, Chapter 90, make each of the county's six "
               "school board districts two adjoining county commission districts, and "
               "Putnam County Schools lists which", "District",
               [[1, 6], [2, 3], [11, 12], [4, 5], [7, 8], [9, 10]]),
    "Rutherford": (21, "The Private Acts of 1967-68, Chapter 454, as amended, make each "
                   "of the county's seven school board districts three of the county "
                   "commission's districts", "District",
                   [[5, 11, 12], [1, 2, 3], [4, 6, 7], [8, 9, 10], [17, 18, 21],
                    [13, 15, 16], [14, 19, 20]]),
    "Warren": (12, "The Private Acts of 1994, Chapter 122, make each of the county's six "
               "school board districts two of the county commission's districts", "District",
               [[2, 3], [1, 6], [4, 5], [7, 8], [9, 10], [11, 12]]),
}

ALL = sorted(set(SAME_AS_COMMISSION) | set(GROUPED))
# the card's empty note names every county drawn here, in this order
COUNTY_SENTENCE = ", ".join(ALL[:-1]) + " and " + ALL[-1]


def fail(msg):
    raise SystemExit("%s: FATAL: %s" % (LABEL, msg))


def and_list(nums):
    nums = [str(n) for n in nums]
    return ", ".join(nums[:-1]) + " and " + nums[-1]


def rings(geometry):
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    if geometry["type"] == "MultiPolygon":
        return [r for poly in geometry["coordinates"] for r in poly]
    fail("a commission district is a %s" % geometry["type"])


def union(geoms, what):
    """The outline of polygons that tile a region, by cancelling the edges
    they share. Refuses unless what is left is exactly one ring."""
    edges = {}
    for g in geoms:
        for ring in rings(g):
            pts = [tuple(p) for p in ring]
            for a, b in zip(pts, pts[1:]):
                if a != b:
                    edges[(a, b)] = edges.get((a, b), 0) + 1
    nxt = {}
    for (a, b), n in edges.items():
        if (b, a) in edges:
            if edges[(b, a)] != n:
                fail("%s: an edge is shared unevenly" % what)
            continue
        if n != 1 or a in nxt:
            fail("%s: the outline branches, so these districts do not join into one area" % what)
        nxt[a] = b
    if not nxt:
        fail("%s: nothing is left after the shared edges cancel" % what)
    start = min(nxt)
    ring, cur = [start], nxt[start]
    while cur != start:
        if len(ring) > len(nxt):
            fail("%s: the outline does not close" % what)
        ring.append(cur)
        cur = nxt[cur]
    ring.append(start)
    if len(ring) - 1 != len(nxt):
        fail("%s: these districts do not join into one area (%d edges, a ring of %d)"
             % (what, len(nxt), len(ring) - 1))
    return {"type": "Polygon", "coordinates": [[list(p) for p in ring]]}


def build():
    with open(SOURCE, encoding="utf-8") as fh:
        commission = json.load(fh)["features"]
    with open(COMPTROLLER, encoding="utf-8") as fh:
        mapped = {f["properties"]["board"] for f in json.load(fh)["features"]}
    by = {}
    for f in commission:
        p = f["properties"]
        name = p["county"]
        if not name.endswith(" County"):
            fail("a commission district's county reads %r" % name)
        by.setdefault(name[:-len(" County")], {})[p["district"]] = f
    out = []
    for name in ALL:
        if name + " County" in mapped:
            fail("%s County is also on the Comptroller's school board map: draw it from "
                 "one source only" % name)
        districts = by.get(name)
        if districts is None:
            fail("%s County has no commission districts in %s" % (name, os.path.basename(SOURCE)))
        n = (SAME_AS_COMMISSION.get(name) or GROUPED[name])[0]
        if sorted(districts) != list(range(1, n + 1)):
            fail("%s County's commission districts are %s, and this table says 1 to %d: "
                 "read its act again before drawing it" % (name, sorted(districts), n))
        fips = districts[1]["properties"]["countyfips"]
        board = name + " County"
        if name in SAME_AS_COMMISSION:
            act = SAME_AS_COMMISSION[name][1]
            basis = (act[0].upper() + act[1:] + ", say " + board + "'s school board "
                     "districts are the county commission's districts.")
            for d in range(1, n + 1):
                out.append({"type": "Feature", "properties": {
                    "key": "%s-%d" % (fips, d), "board": board, "label": "District %d" % d,
                    "countyFips": fips, "basis": basis},
                    "geometry": districts[d]["geometry"]})
        else:
            _, said, word, groups = GROUPED[name]
            used = sorted(x for g in groups for x in g)
            if used != list(range(1, n + 1)):
                fail("%s County's groups use commission districts %s, not each of 1 to %d once"
                     % (name, used, n))
            for i, group in enumerate(groups, 1):
                what = "%s County %s %d" % (name, word, i)
                geom = union([districts[d]["geometry"] for d in group], what)
                out.append({"type": "Feature", "properties": {
                    "key": "%s-%d" % (fips, i), "board": board, "label": "%s %d" % (word, i),
                    "countyFips": fips,
                    "basis": "%s; this one is the commission's Districts %s." % (
                        said, and_list(group))},
                    "geometry": geom})
    keys = [f["properties"]["key"] for f in out]
    if len(set(keys)) != len(keys):
        fail("two districts share a key")
    return (json.dumps({"type": "FeatureCollection", "features": out},
                       separators=(",", ":"), ensure_ascii=False) + "\n"), out


def check_card():
    with open(INDEX, encoding="utf-8") as fh:
        # the card's strings are split across "..." + "..." joins
        page = re.sub(r'"\s*\+\s*"', "", fh.read())
    for claim in (COUNTY_SENTENCE, "loadTnSchoolBoardFromCommission",
                  "data/app/tn-school-board-from-commission.json"):
        if claim not in page:
            fail("tn/index.html no longer carries %r, which the school board card must say "
                 "about this file" % claim)


def main(argv):
    text, feats = build()
    check_card()
    summary = "%d districts in %d counties (%d copied, %d joined from commission districts)" % (
        len(feats), len(ALL),
        sum(SAME_AS_COMMISSION[c][0] for c in SAME_AS_COMMISSION),
        sum(len(GROUPED[c][3]) for c in GROUPED))
    if "--check" in argv:
        try:
            with open(OUT, encoding="utf-8") as fh:
                shipped = fh.read()
        except FileNotFoundError:
            fail("%s is missing" % os.path.relpath(OUT))
        if shipped != text:
            fail("%s is not what the commission districts and this table build: run "
                 "python3 tn/scripts/build_tn_school_board_from_commission.py"
                 % os.path.relpath(OUT))
        print("%s: OK, %s" % (LABEL, summary))
        return
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("%s: wrote %s, %s, %d bytes" % (LABEL, os.path.relpath(OUT), summary, len(text)))


if __name__ == "__main__":
    main(sys.argv[1:])
