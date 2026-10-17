#!/usr/bin/env python3
"""
Build in/data/app/in-appeals-districts.json: the three geographic districts of
the Court of Appeals of Indiana, each a group of whole counties, dissolved from
the shipped county fabric.

    python3 in/scripts/build_in_appeals_districts.py          # writes (needs shapely)
    python3 in/scripts/build_in_appeals_districts.py --check  # offline, stdlib only

The dissolve, the partition gate and the offline check are
scripts/whole_county_courts.py, shared with the other states; this file says
where Indiana's county lists come from and how they are read.

WHY THESE DISTRICTS AND NOT THE OTHERS. The court has fifteen judges in five
districts. Three judges come from each of the 1st, 2nd and 3rd Districts and
"stand for retention only in their districts"; the 4th and 5th Districts each
take one judge from each of the first three and stand for retention statewide
(the court's "Court of Appeals Districts" page). So only the first three are
districts a voter answers to, and only they are drawn. Indiana's trial courts
are not drawn either: every judicial circuit is one county except Dearborn and
Ohio, which share one (the Indiana Prosecuting Attorneys Council, citing Ind.
Const. art. 7, sec. 16), so the County layer already answers where a trial
court sits.

THE COUNTY LISTS ARE READ FROM THE COURT'S MAP, which is the one place the
court publishes them. The districts are set in the Indiana Code, and the
General Assembly publishes the Code only through a script-driven site that
serves this project nothing it can read (measured 2026-10-15, recorded as a
data-publishing hurdle). in/data/source/courts/coa-district-map-reading.tsv
records each county's district as read from the court's own map image, with
the image's address, size and SHA-256 and the method.

TWO GUARDS AGAINST A MISREAD COUNTY. The counts per district are pinned (53,
19 and 20, measured on the map), and every district must dissolve to ONE piece
of ground: a county put in the wrong district would almost always sit apart
from the rest of it, so a district that comes out in two pieces stops the build
and names itself.
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))

import whole_county_courts as wcc  # noqa: E402  (FLEET_SHARED)

LABEL = "build-in-appeals-districts"
SOURCE = os.path.join(os.path.dirname(_HERE), "data", "source", "courts")
READING = "coa-district-map-reading.tsv"
PAGE = "coa-districts-page.txt"
OUT = "in-appeals-districts.json"
COUNTS = {1: 53, 2: 19, 3: 20}


def lines(name):
    with open(os.path.join(SOURCE, name)) as fh:
        return [ln.rstrip("\n") for ln in fh if ln.strip() and not ln.startswith("#")]


def tilings():
    by = {}
    for ln in lines(READING):
        county, district = ln.split("\t")
        by.setdefault(int(district), []).append(county)
    got = dict((d, len(v)) for d, v in by.items())
    if got != COUNTS:
        wcc.fail(LABEL, "the map reading puts %r counties in each district, and "
                 "%r were measured" % (got, COUNTS))
    page = " ".join(lines(PAGE))
    for phrase in ("stand for retention only in their districts",
                   "Judges representing the 4th and 5th districts stand for "
                   "retention statewide"):
        if phrase not in page:
            wcc.fail(LABEL, "the court's districts page no longer says %r, which "
                     "the card repeats" % phrase)
    rows = [(d, by[d], {}) for d in sorted(by)]
    return [wcc.Tiling(OUT, "appeals district", rows, len(COUNTS),
                       "The Court of Appeals of Indiana's own district map, read "
                       "16 October 2026")]


def parts(geometry):
    if geometry["type"] == "Polygon":
        return 1
    return len(geometry["coordinates"])


def one_piece():
    import json
    with open(os.path.join(wcc.app_dir("in"), OUT)) as fh:
        feats = json.load(fh)["features"]
    for f in feats:
        n = parts(f["geometry"])
        if n != 1:
            wcc.fail(LABEL, "District %s dissolves to %d pieces of ground; a county "
                     "has probably been read into the wrong district"
                     % (f["properties"]["unit"], n))
    print("%s: each of the %d districts is one piece of ground" % (LABEL, len(feats)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file, write nothing")
    args = ap.parse_args()
    if args.check:
        wcc.check("in", LABEL, tilings())
    else:
        wcc.build("in", LABEL, tilings())
    one_piece()
    if args.check:
        print("%s: OK" % LABEL)


if __name__ == "__main__":
    main()
