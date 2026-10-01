#!/usr/bin/env python3
"""
Build data/app/carroll-county-board-districts.json by dissolving TIGER township
geometry according to the county's own published district map.

WHY THIS EXISTS — the county publishes no vector district data. Carroll's GIS is
an assessor/parcel vendor site with no REST service, and the map it does publish
(County.Board.District.Update.2021.pdf, "CARROLL COUNTY, IL 2021 County Board
Districts", produced by the Carroll County GIS Department) is a RASTER export:
65 embedded images and only frame-and-legend vector paths, so there is nothing
in it to extract the way Stephenson's vector map allowed.

It did not need extracting. Carroll's three districts run EXACTLY along township
lines — every district edge on that map follows a township boundary — so the
composition can simply be read off it, and the boundary composed from TIGER
township geometry per that published rule. This is the Livingston recipe
unchanged: we are not inventing a boundary, we are composing published
boundaries per a published rule, and anything requiring judgement is a hard
failure below rather than a best-effort match.

THE ONE RECONCILIATION, recorded rather than silently patched: the map labels
Carroll's consolidated townships by their HISTORIC halves — CHERRY GROVE and
SHANNON as separate labels, ROCK CREEK and LIMA as separate labels — where TIGER
carries the merged "Cherry Grove-Shannon" and "Rock Creek-Lima". Both merged
townships lie wholly inside District 3, so no district line depends on the
distinction and the mapping is forced, not chosen. It is declared in NAME_FIXES
so the diff shows it.

The map prints each district's 2020 population (5190 / 5459 / 5053, summing to
the county's 15,702) but no per-township figure, so unlike Stephenson there is no
arithmetic cross-check available here. What IS checked is completeness: all 12
TIGER townships must be claimed exactly once, which is the guard that catches a
misread far more reliably than a plausible-looking total would.

Regenerate only when the county reapportions (this map is the 2021 plan, drawn on
the 2020 census).

Usage:
    python3 scripts/build_carroll_board_districts.py
    python3 scripts/build_carroll_board_districts.py --check
"""

import argparse
import json
import os
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
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "carroll-county-board-districts.json")

COUNTY_FIPS = "015"
COUNTY_NAME = "Carroll County"
SOURCE_URL = "https://www.carrollcountyil.gov/County.Board.District.Update.2021.pdf"

# TIGERweb County Subdivisions — the same service the statewide `township`
# layer answers from, so this file's edges are the edges that layer draws.
TIGER_COUSUB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/1/query")

# The county's published composition, verbatim in reading order.
DISTRICTS = {
    "1": ["Washington", "Woodland", "Freedom", "Salem", "Savanna"],
    "2": ["Mount Carroll", "York", "Fairhaven"],
    "3": ["Cherry Grove", "Shannon", "Rock Creek", "Lima", "Wysox", "Elkhorn Grove"],
}
# The map's printed 2020 population per district, carried so the numbers this was
# read against stay visible even though they cannot be cross-checked township by
# township (the map prints no per-township figure).
DISTRICT_POP = {"1": 5190, "2": 5459, "3": 5053}

# map label -> TIGER BASENAME. Carroll merged two pairs of townships; the county's
# map still labels each historic half separately. Both merged townships sit wholly
# in District 3, so the merge cannot move a district line — which is what makes
# this forced rather than a fuzzy match. Two labels collapsing onto one TIGER name
# is also why the duplicate check below runs on the MAPPED names.
NAME_FIXES = {
    "Cherry Grove": "Cherry Grove-Shannon", "Shannon": "Cherry Grove-Shannon",
    "Rock Creek": "Rock Creek-Lima", "Lima": "Rock Creek-Lima",
}

# Points that must land in the district the county says they do — the guard that
# proves the composition was applied and simplified without moving a line, not
# merely parsed. Each was geocoded and its containing TOWNSHIP read back from
# TIGER before being written down, so the expected district is derived from the
# published composition rather than recalled. District 1 is two townships, so it
# is the one most likely to break if a name mapping goes wrong.
ANCHORS = [
    (42.0945, -90.1568, "1", "Savanna (Savanna Twp)"),
    (42.1748, -89.8739, "1", "Lake Carroll (Freedom Twp)"),
    (42.1410, -90.1576, "1", "Mississippi Palisades State Park (Washington Twp)"),
    (42.0949, -89.9777, "2", "Mount Carroll, county seat (Mount Carroll Twp)"),
    (41.9589, -90.0993, "2", "Thomson (York Twp)"),
    (42.0134, -89.8907, "2", "Chadwick (Fairhaven Twp)"),
    (42.1021, -89.8330, "3", "Lanark (Rock Creek-Lima Twp)"),
    (42.1547, -89.7398, "3", "Shannon (Cherry Grove-Shannon Twp)"),
    (41.9634, -89.7746, "3", "Milledgeville (Wysox Twp)"),
]


fail = make_fail("carroll-board")


def fetch_townships():
    require_robots_once(TIGER_COUSUB, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-carroll-board-districts")
    resp = requests.get(TIGER_COUSUB, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, COUNTY_FIPS),
        "outFields": "BASENAME,NAME,GEOID",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if not feats:
        fail("TIGERweb returned no townships for county %s" % COUNTY_FIPS)
    return feats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped file, write nothing")
    args = ap.parse_args()

    feats = fetch_townships()
    by_name = {}
    for f in feats:
        by_name[(f["properties"].get("BASENAME") or "").strip()] = f

    published = [(d, NAME_FIXES.get(n, n)) for d, names in DISTRICTS.items() for n in names]
    # Every published township must resolve, and every TIGER township must be
    # claimed exactly once. Either failure means the composition and the census
    # have diverged — a reapportionment or a rename — and a human must look.
    missing = sorted({n for _, n in published if n not in by_name})
    if missing:
        fail("published township(s) not in TIGER: %s" % ", ".join(missing))
    claimed = sorted({n for _, n in published})
    homes = {}
    for d, n in published:
        homes.setdefault(n, set()).add(d)
    split = sorted(n for n, ds in homes.items() if len(ds) > 1)
    if split:
        fail("township(s) claimed by more than one district: %s" % ", ".join(split))
    unassigned = sorted(set(by_name) - set(claimed))
    if unassigned:
        fail("TIGER township(s) in no district: %s — the county's composition is "
             "incomplete or has changed" % ", ".join(unassigned))

    features = []
    for district in sorted(DISTRICTS, key=lambda d: int(d)):
        # dedupe: two map labels can name the same TIGER township (Cherry
        # Grove + Shannon), and passing one feature twice makes every edge cancel
        # in the dissolve, which surfaces as "open chain" rather than as a
        # wrong shape
        members = sorted({NAME_FIXES.get(n, n) for n in DISTRICTS[district]})
        rings = dissolve([by_name[n] for n in members])
        rings = [simplify(r, SIMPLIFY_TOLERANCE_M) for r in rings]
        polys = group_rings(rings)
        geometry = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                    else {"type": "MultiPolygon", "coordinates": polys})
        features.append({
            "type": "Feature",
            "properties": {
                "district": district,
                "townships": sorted(members),
                "source": SOURCE_URL,
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
            fail("data/app/carroll-county-board-districts.json is missing — run this script")
        with open(OUT_PATH, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != text:
            fail("shipped file differs from a fresh build (%d vs %d bytes)"
                 % (len(shipped), len(text)))
        print("carroll-board: OK — matches a fresh build (%d districts, %d townships, %d bytes)"
              % (len(features), len(claimed), len(text)))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("carroll-board: wrote %s — %d districts from %d townships, %d bytes"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(features), len(claimed), len(text)))
    for f in features:
        print("   district %s: %d townships" % (f["properties"]["district"],
                                                len(f["properties"]["townships"])))


def rings_of_feature(feature):
    geom = feature["geometry"]
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [r for poly in geom["coordinates"] for r in poly]


if __name__ == "__main__":
    main()
