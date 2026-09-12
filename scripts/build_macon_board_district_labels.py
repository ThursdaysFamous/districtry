#!/usr/bin/env python3
"""Label Macon County's five UNNUMBERED board district shapes, from the Clerk's map.

THE PROBLEM THIS SOLVES. Macon publishes its five board districts as live GIS —
and every attribute on every one of them is null. No district number, no
representative, no party, no contact. `macon-county-board-labels` recorded that
on 2026-08-02 and held the board card back, because numbering five shapes by
where they sit on a map is a guess about who represents whom. The gap named its
own cure:

    "District numbers for the five shapes — a labelled clerk's map, the adopted
     redistricting ordinance, or simply the county filling in the district field
     its own data already has. Any one of those turns the board on the same day."

County Clerk Josh Tanner sent the first of those on 2026-08-07: "Macon County
Board Districts 2022", a colour-coded map with a legend numbering the districts
1 to 5. Archived under data/source/raw/.

WHAT THIS SHIPS, AND WHY IT IS NOT THE GEOMETRY. The county's shapes are correct
and live; only the labels were missing. So this emits FIVE ANCHOR POINTS — one
per district, each inside a precinct the map colours unambiguously — and the app
labels the live shapes at runtime by asking which anchor each one contains. That
keeps the county's own geometry authoritative (if they redraw it, the app gets
the new lines), and it keeps this file to the five facts actually learned.

WHY ANCHORS RATHER THAN OBJECTIDs. OBJECTID is the only other handle the service
offers, and it is exactly the kind of key that changes when a layer is
republished — silently reassigning every district. An anchor point survives a
republish, survives a boundary nudge, and states the finding in the form it was
actually read: "the district containing Maroa is District 3."

HOW THE ASSIGNMENT WAS VERIFIED, which matters more than the anchors themselves.
Not by eye and not by position. Each of the county's five shapes was intersected
with the county's own 64 precincts to get its MEMBERSHIP LIST, and those lists
were compared against the map's colour regions precinct by precinct:

    OBJECTID 16  ->  D1  Decatur 1,2,3,5,10,15,17,18,20,23        (pink)
    OBJECTID 17  ->  D2  + South Macon, Mt. Zion 1-3, S. Wheatland 1-3  (tan)
    OBJECTID 18  ->  D3  + Maroa, Friends Creek, Hickory Point …  (teal)
    OBJECTID 19  ->  D4  + Oakley, Whitmore 1-2, Long Creek 1-6   (yellow-green)
    OBJECTID 20  ->  D5  + Niantic, Austin, Illini, Harristown …  (blue)

Every outlier lands correctly — Decatur 24 alone in the northern group, Decatur
4/7/28 in the eastern, Decatur 22/25 in the western — which a position-based
guess would not reproduce. The roster is a third, independent check: the county
publishes 15 members keyed by district, and they come out 3 per district across
all five.

(The OBJECTIDs happen to run 16..20 in district order. That is a coincidence and
is deliberately NOT what this relies on — reading it off the ordering would have
been the guess the gap record refused to make, and it would be unverifiable the
day the county republishes the layer.)

Usage:
    python3 scripts/build_macon_board_district_labels.py            # write
    python3 scripts/build_macon_board_district_labels.py --check    # verify live
    python3 scripts/build_macon_board_district_labels.py --offline  # skip the network
"""

import argparse
import json
import os
import sys

try:
    import requests
    from shapely.geometry import shape, Point
except ImportError:  # pragma: no cover
    sys.exit("requests and shapely are required: "
             "pip install -c scripts/requirements.txt requests shapely")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "macon-board-district-labels.json")

SERVICE = ("https://services1.arcgis.com/a3k0qIja5SolIRYR/arcgis/rest/services/"
           "ElectionGeography_public_e465746545b04d86ad93c78e731c292a/FeatureServer/")
BOARD_LAYER = SERVICE + "2"        # Electoral Districts — the five unlabelled shapes
PRECINCT_LAYER = SERVICE + "1"     # Voting Precincts — used for the membership check
HEADERS = {"User-Agent": "districtry boundary builder (+https://districtry.com/il/)"}
REQUEST_TIMEOUT = 90

SOURCE_NOTE = ("Macon County Clerk Josh Tanner, \"Macon County Board Districts "
               "2022\" (colour-coded, legend numbering districts 1-5), supplied "
               "by e-mail 2026-08-07 and archived as data/source/raw/Macon "
               "County Board Districts 2022.pdf")

EXPECTED_DISTRICTS = 5

# One point per district, each an interior point of a precinct the map colours
# unambiguously. The precinct is named so the reading stays checkable against
# the archived map by anybody, without this script.
ANCHORS = {
    1: {"lat": 39.85122, "lon": -88.96016, "precinct": "DECATUR 15",  "colour": "pink"},
    2: {"lat": 39.69752, "lon": -88.97441, "precinct": "SOUTH MACON", "colour": "tan"},
    3: {"lat": 40.00802, "lon": -88.97373, "precinct": "MAROA",       "colour": "teal"},
    4: {"lat": 39.90138, "lon": -88.80280, "precinct": "OAKLEY",      "colour": "yellow-green"},
    5: {"lat": 39.85972, "lon": -89.18021, "precinct": "NIANTIC",     "colour": "blue"},
}

# The membership check above, as an assertion. Each district must contain these
# precincts — the ones the map's colour regions show — and the check fails if the
# county's shapes ever stop matching the map they sent.
MEMBERSHIP = {
    1: ["DECATUR 1", "DECATUR 15", "DECATUR 23"],
    2: ["SOUTH MACON", "MT. ZION 1", "SOUTH WHEATLAND 1"],
    3: ["MAROA", "FRIENDS CREEK", "DECATUR 24"],
    4: ["OAKLEY", "WHITMORE 1", "LONG CREEK 2", "DECATUR 28"],
    5: ["NIANTIC", "AUSTIN", "HARRISTOWN", "DECATUR 22", "DECATUR 25"],
}


def fetch(url, fields):
    resp = requests.get(url + "/query", headers=HEADERS, timeout=REQUEST_TIMEOUT,
                        params={"where": "1=1", "outFields": fields,
                                "outSR": "4326", "f": "geojson"})
    resp.raise_for_status()
    return resp.json()


def verify():
    board = fetch(BOARD_LAYER, "OBJECTID,district")
    feats = board.get("features") or []
    if len(feats) != EXPECTED_DISTRICTS:
        sys.exit("the county's Electoral Districts layer now has %d shapes, not %d "
                 "— re-read the Clerk's map before trusting these labels"
                 % (len(feats), EXPECTED_DISTRICTS))

    shapes = [(f["properties"].get("OBJECTID"), shape(f["geometry"])) for f in feats]
    # If the county ever fills in its own district field, say so loudly: this
    # whole file becomes unnecessary that day.
    filled = [f["properties"].get("district") for f in feats
              if f["properties"].get("district") not in (None, "")]
    if filled:
        print("  NOTE: the county's own `district` field is now populated (%s). "
              "Prefer it and retire these labels." % filled)

    assigned = {}
    for district, a in sorted(ANCHORS.items()):
        pt = Point(a["lon"], a["lat"])
        holders = [oid for oid, g in shapes if g.contains(pt)]
        if len(holders) != 1:
            sys.exit("anchor for District %d (%s) falls in %d shapes, not exactly "
                     "one — the county's geometry moved and the labels must be "
                     "re-read from the map.\n  %s"
                     % (district, a["precinct"], len(holders), SOURCE_NOTE))
        assigned[district] = holders[0]
    if len(set(assigned.values())) != EXPECTED_DISTRICTS:
        sys.exit("the five anchors do not land in five DIFFERENT shapes (%s) — "
                 "the labelling is not a bijection and nothing should ship"
                 % assigned)

    precincts = fetch(PRECINCT_LAYER, "name")
    by_name = {}
    for f in precincts.get("features") or []:
        by_name[str(f["properties"].get("name") or "").strip().upper()] = shape(f["geometry"])
    problems = []
    for district, names in sorted(MEMBERSHIP.items()):
        oid = assigned[district]
        bg = dict(shapes)[oid]
        for name in names:
            g = by_name.get(name)
            if g is None:
                problems.append("precinct %r is no longer published" % name)
                continue
            share = g.intersection(bg).area / g.area if g.area else 0
            if share < 0.5:
                problems.append("%s is only %.0f%% inside District %d"
                                % (name, 100 * share, district))
    if problems:
        sys.exit("the county's shapes no longer match the Clerk's map:\n    %s\n  %s"
                 % ("\n    ".join(problems), SOURCE_NOTE))
    return assigned


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify, write nothing")
    parser.add_argument("--offline", action="store_true",
                        help="skip the live verification (drift check only)")
    args = parser.parse_args()

    if args.offline:
        print("Macon board labels: offline — %d anchors, live verification skipped"
              % len(ANCHORS))
        assigned = None
    else:
        assigned = verify()
        print("Macon board labels: %d anchors, each in exactly one shape, all five "
              "distinct" % len(ANCHORS))
        for d in sorted(assigned):
            print("   District %d  <-  OBJECTID %-3s  (anchor: %s, %s on the map)"
                  % (d, assigned[d], ANCHORS[d]["precinct"], ANCHORS[d]["colour"]))
        print("   membership check passed for %d named precincts"
              % sum(len(v) for v in MEMBERSHIP.values()))

    payload = json.dumps({
        "source": SOURCE_NOTE,
        "note": ("Anchor points that label the county's five UNNUMBERED board "
                 "district shapes. The app fetches the county's live geometry and "
                 "assigns each shape the district whose anchor it contains; if that "
                 "is not a one-to-one match the layer refuses to label rather than "
                 "guessing."),
        "districts": {str(d): ANCHORS[d] for d in sorted(ANCHORS)},
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n"

    existing = None
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH) as handle:
            existing = handle.read()
    if args.check:
        if existing != payload:
            sys.exit("DRIFT: %s does not match a fresh build"
                     % os.path.relpath(OUT_PATH, REPO_ROOT))
        print("  --check OK — shipped file matches")
        return
    with open(OUT_PATH, "w") as handle:
        handle.write(payload)
    print("  wrote %s" % os.path.relpath(OUT_PATH, REPO_ROOT))


if __name__ == "__main__":
    main()
