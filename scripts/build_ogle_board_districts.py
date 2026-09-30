#!/usr/bin/env python3
"""
Build data/app/ogle-county-board-districts.json by dissolving Census 2020 voting
districts according to the county's own adopted reapportionment resolution.

WHY THIS EXISTS — Ogle publishes a complete board roster and no district
geometry. Its GIS is a Beacon/Schneider parcel viewer with no REST service, its
ArcGIS Online org holds forest-preserve and cemetery layers, and its only
precinct publication is a 51-page PDF map atlas. What it DOES publish is the
composition, in the resolution that adopted the map:

    RESOLUTION R-2021-1106, ADOPTION OF THE OGLE COUNTY REAPPORTIONMENT MAP
    adopted 2021-11-16, signed Patricia Nordman (Vice-Chairman), attested
    Laura J. Cook (County Clerk); 24 members, 8 districts of 3, for the years
    December 2022 to December 2031.

That is a complete, authoritative definition in PRECINCT terms, and the Census
publishes those precincts as 2020 Voting Districts. So the boundary is DERIVED,
not guessed: every edge of the result is a census edge, and the only judgement is
which precinct goes in which district, which the county states outright. Same
deliberate narrowing of "never guess" as build_livingston_board_districts.py —
compose published boundaries per a published rule, and fail hard on anything
that would require judgement.

WHICH RESOLUTION. There are TWO. R-2021-0607 (June 2021) adopted a first plan;
R-2021-1106 (November 2021) re-adopted with District 5 corrected. The June plan
listed District 5 as "Marion Township precincts 1, 2, and 3, and Rockvale
Township precincts 1 and 2" and named LEAF RIVER nowhere at all — a township in
no district. November added it. The unassigned-precinct guard below is exactly
what would have caught that, which is a fair reason to trust it. All 460
resolution and ordinance PDFs the county has published from 2007 to 2026 were
scanned: these two are the only reapportionment adoptions, and nothing amends
R-2021-1106.

ONE TOWNSHIP IS SPLIT. Districts 3 and 4 divide FLAGG township (the city of
Rochelle) between them; every other district is made of whole townships. So the
D3/D4 line is the only district edge in the county that depends on precinct
geometry rather than township geometry — which is why two of the anchors below
sit either side of it, and why SPLIT_TOWNSHIPS is asserted rather than assumed.

THE ONE DIVERGENCE, recorded rather than silently patched: the resolution names
52 precincts and the 2020 census carries exactly those 52, one for one. The
county has since retired FORRESTON 3 and now runs 51 (its 2025-2027 clerk's
yearbook lists Forreston 1 and 2 only, in both the polling places and both
parties' committeeperson lists). That consolidation cannot move a district line:
Forreston 1, 2 and 3 are all in District 7, so the union is unchanged. The
check_whole_townships() guard below is what keeps that true — if a future
re-precincting ever split a township that the resolution treats as whole, the
build fails instead of shipping a line the county never drew.

Regenerate only when the county reapportions (next due after the 2030 census).

Usage:
    python3 scripts/build_ogle_board_districts.py
    python3 scripts/build_ogle_board_districts.py --check
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from build_metro_outline import (  # noqa: E402  (shared machinery — do not fork)
    HEADERS, REQUEST_TIMEOUT, SIMPLIFY_TOLERANCE_M, STATE_FIPS,
    dissolve, group_rings, point_in_rings, simplify,
)
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    make_fail,
    require_robots_once,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "ogle-county-board-districts.json")

COUNTY_FIPS = "141"
COUNTY_NAME = "Ogle County"
SOURCE_URL = ("https://www.oglecountyil.gov/document_center/County%20Board/"
              "Resolutions%20and%20Ordinances/Resolutions%20-%20Archived/"
              "Resolutions%202021/Resolutions%20-%20November-2021.pdf")
SOURCE_LABEL = "Ogle County Resolution R-2021-1106 (adopted 2021-11-16)"

# Census 2020 Voting Districts — the precincts the resolution is written in.
TIGER_VTD = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
             "tigerWMS_Census2020/MapServer/58/query")
# County Subdivisions — the same service the statewide `township` layer answers
# from, used only to CORROBORATE the dissolve (see check_whole_townships).
TIGER_COUSUB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/1/query")

# R-2021-1106's composition, verbatim in the resolution's reading order.
DISTRICTS = {
    "1": ["Dement", "Lynnville", "Monroe", "Scott"],
    "2": ["Oregon-Nashua 1", "Oregon-Nashua 2", "Oregon-Nashua 3", "Oregon-Nashua 4",
          "Oregon-Nashua 5", "Oregon-Nashua 6", "White Rock", "Pine Rock", "Lafayette"],
    "3": ["Flagg 1", "Flagg 2", "Flagg 3", "Flagg 6", "Flagg 7"],
    "4": ["Flagg 4", "Flagg 5", "Flagg 8", "Flagg 9", "Flagg 10", "Flagg 11"],
    "5": ["Leaf River", "Marion 1", "Marion 2", "Marion 3", "Rockvale 1", "Rockvale 2"],
    "6": ["Byron 1", "Byron 2", "Byron 3", "Byron 4"],
    "7": ["Mount Morris 1", "Mount Morris 2", "Mount Morris 3", "Mount Morris 4",
          "Forreston 1", "Forreston 2", "Forreston 3", "Maryland"],
    "8": ["Buffalo 1", "Buffalo 2", "Buffalo 3", "Brookville", "Eagle Point",
          "Grand Detour", "Lincoln", "Pine Creek", "Taylor", "Woosung"],
}

# The resolution spells it out, the census abbreviates. Declared so the diff
# shows it rather than a fuzzy matcher hiding it.
NAME_FIXES = {"MOUNT MORRIS": "MT MORRIS"}

# The only township the resolution divides. Asserted, not assumed: a future plan
# that split a second township would change what this build is willing to claim.
SPLIT_TOWNSHIPS = {"FLAGG"}

# Points that must land in the district the resolution puts them in. Every one
# was DERIVED, not recalled: the place was geocoded, its containing precinct read
# back from the census layer, and the district then looked up in DISTRICTS above.
# Four sit in Flagg township, two either side of the D3/D4 line — the county's
# only district edge that is not also a township edge.
ANCHORS = [
    (41.9307, -88.9645, "1", "Creston (Dement precinct)"),
    (42.0984, -89.0007, "1", "Monroe Center (Monroe precinct)"),
    (42.1017, -89.0932, "1", "Davis Junction (Scott precinct)"),
    (42.0148, -89.3323, "2", "Oregon, county seat (Oregon-Nashua 2)"),
    (41.9239, -89.0687, "3", "Rochelle (Flagg 1)"),
    (41.8924, -89.0779, "3", "Rochelle Municipal Airport (Flagg 7)"),
    (41.9511, -89.0645, "4", "Hillcrest (Flagg 8)"),
    (41.9427, -89.0781, "4", "Rochelle Township High School (Flagg 8)"),
    (42.1256, -89.4037, "5", "Leaf River (Leaf River precinct)"),
    (42.1072, -89.1793, "5", "Stillman Valley (Marion 3)"),
    (42.1270, -89.2557, "6", "Byron (Byron 1)"),
    (42.0503, -89.4312, "7", "Mount Morris (Mt Morris 4)"),
    (42.1262, -89.5791, "7", "Forreston (Forreston 1)"),
    (42.1434, -89.4904, "7", "Adeline (Maryland precinct)"),
    (41.9861, -89.5793, "8", "Polo (Buffalo 3)"),
]


fail = make_fail("ogle-board")


def norm(value):
    key = re.sub(r"[^A-Z0-9 ]", "", (value or "").upper()).strip()
    for long, short in NAME_FIXES.items():
        if key.startswith(long):
            key = short + key[len(long):]
    return re.sub(r"\s+", "", key)


def township_of(precinct):
    """'Flagg 11' -> 'FLAGG'. The census names precincts '<township> <n>', and a
    township with a single precinct carries the bare township name."""
    return re.sub(r"[0-9]+$", "", norm(precinct))


def fetch(url, extra_fields):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-ogle-board-districts")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, COUNTY_FIPS),
        "outFields": extra_fields,
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if not feats:
        fail("TIGERweb returned no features from %s for county %s" % (url, COUNTY_FIPS))
    return feats


def rings_of_feature(feature):
    geom = feature["geometry"]
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [r for poly in geom["coordinates"] for r in poly]


def check_whole_townships(by_precinct, townships):
    """Corroborate the precinct dissolve against the township layer.

    Every township the resolution treats as whole must be exactly reconstructed
    by its precincts. This is what makes the result trustworthy without a county
    GIS to compare against: two independently published census layers have to
    agree about where the county's internal lines are, and 6 of the 8 districts
    are made only of these edges. Sampled rather than compared vertex-for-vertex
    because the two layers are generalized separately — a shared edge is the same
    LINE, not the same vertex list.
    """
    claimed = {}
    for names in DISTRICTS.values():
        for p in names:
            claimed.setdefault(township_of(p), []).append(p)

    split = sorted(t for t, ps in claimed.items()
                   if len({d for d, names in DISTRICTS.items()
                           for p in names if township_of(p) == t}) > 1)
    if set(split) != SPLIT_TOWNSHIPS:
        fail("townships split between districts are %s, expected %s — the "
             "composition changed and the whole-township corroboration below no "
             "longer covers what it used to"
             % (split or "none", sorted(SPLIT_TOWNSHIPS)))

    problems = []
    for tname, precincts in sorted(claimed.items()):
        if tname in SPLIT_TOWNSHIPS:
            continue
        twp = townships.get(tname)
        if twp is None:
            fail("no TIGER township named %s to corroborate against" % tname)
        twp_rings = rings_of_feature(twp)
        prec_rings = [r for p in precincts for r in rings_of_feature(by_precinct[norm(p)])]
        # sample the township's own vertices, nudged inward toward its centroid,
        # plus a coarse grid over its bounding box
        xs = [c[0] for r in twp_rings for c in r]
        ys = [c[1] for r in twp_rings for c in r]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        pts = [(cy + (c[1] - cy) * 0.97, cx + (c[0] - cx) * 0.97)
               for r in twp_rings for c in r[::7]]
        for i in range(12):
            for j in range(12):
                pts.append((min(ys) + (max(ys) - min(ys)) * (i + 0.5) / 12,
                            min(xs) + (max(xs) - min(xs)) * (j + 0.5) / 12))
        agree = total = 0
        for lat, lng in pts:
            a = point_in_rings(lat, lng, twp_rings)
            b = point_in_rings(lat, lng, prec_rings)
            total += 1
            agree += (a == b)
        if agree < total:
            problems.append("%s: %d/%d sample points agree" % (tname, agree, total))
    if problems:
        fail("precinct union does not reconstruct these whole townships — the "
             "census precinct and township layers disagree about the county's "
             "internal lines: %s" % "; ".join(problems))
    return len(claimed) - len(SPLIT_TOWNSHIPS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped file, write nothing")
    args = ap.parse_args()

    by_precinct = {}
    for f in fetch(TIGER_VTD, "BASENAME,NAME,GEOID"):
        by_precinct[norm(f["properties"].get("BASENAME"))] = f
    townships = {}
    for f in fetch(TIGER_COUSUB, "BASENAME,NAME,GEOID"):
        townships[norm(f["properties"].get("BASENAME"))] = f

    published = [(d, norm(p)) for d, names in DISTRICTS.items() for p in names]
    # Every published precinct must resolve, and every census precinct must be
    # claimed exactly once. The second half is the guard that caught the June
    # plan's missing Leaf River; without it a whole township can silently vanish
    # from the map and every district still looks well formed.
    missing = sorted({p for _, p in published if p not in by_precinct})
    if missing:
        fail("precinct(s) named by the resolution are not in the 2020 census: %s"
             % ", ".join(missing))
    claimed = [p for _, p in published]
    if len(claimed) != len(set(claimed)):
        dupes = sorted({p for p in claimed if claimed.count(p) > 1})
        fail("precinct(s) listed in more than one district: %s" % ", ".join(dupes))
    unassigned = sorted(set(by_precinct) - set(claimed))
    if unassigned:
        fail("census precinct(s) in no district: %s — the composition is "
             "incomplete or the county has re-precincted" % ", ".join(unassigned))

    whole = check_whole_townships(by_precinct, townships)

    features = []
    for district in sorted(DISTRICTS, key=int):
        members = [norm(p) for p in DISTRICTS[district]]
        rings = dissolve([by_precinct[p] for p in members])
        rings = [simplify(r, SIMPLIFY_TOLERANCE_M) for r in rings]
        polys = group_rings(rings)
        geometry = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                    else {"type": "MultiPolygon", "coordinates": polys})
        features.append({
            "type": "Feature",
            "properties": {
                "district": district,
                "precincts": DISTRICTS[district],
                "source": SOURCE_LABEL,
            },
            "geometry": geometry,
        })

    payload = {"type": "FeatureCollection", "features": features}

    for lat, lng, want, label in ANCHORS:
        hit = [f["properties"]["district"] for f in features
               if point_in_rings(lat, lng, rings_of_feature(f))]
        if hit != [want]:
            fail("%s should be district %s, got %s" % (label, want, hit or "no district"))

    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("data/app/ogle-county-board-districts.json is missing — run this script")
        with open(OUT_PATH, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != text:
            fail("shipped file differs from a fresh build (%d vs %d bytes)"
                 % (len(shipped), len(text)))
        print("ogle-board: OK — matches a fresh build (%d districts, %d precincts, "
              "%d whole townships corroborated, %d anchors, %d bytes)"
              % (len(features), len(claimed), whole, len(ANCHORS), len(text)))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("ogle-board: wrote %s — %d districts from %d precincts, %d whole townships "
          "corroborated against the township layer, %d anchors hold, %d bytes"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(features), len(claimed),
             whole, len(ANCHORS), len(text)))
    for f in features:
        print("   district %s: %d precincts" % (f["properties"]["district"],
                                                len(f["properties"]["precincts"])))


if __name__ == "__main__":
    main()
