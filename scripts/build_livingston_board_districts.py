#!/usr/bin/env python3
"""
Build data/app/livingston-county-board-districts.json by dissolving TIGER
township geometry according to the county's own published district composition.

WHY THIS EXISTS — the county publishes no GIS at all. Livingston has no ArcGIS
Online presence, no self-hosted server, and only a vendor assessor site; research
pass 4 found nothing to fetch. What it DOES publish, in prose on its board page,
is that its three board districts are made of WHOLE TOWNSHIPS:

    District 1: All of Pontiac and Rooks Creek Townships
    District 2: Reading, Newton, Sunbury, Nevada, Dwight, Round Grove, Long
                Point, Amity, Esmen, Odell, Union, Broughton and Owego Townships
    District 3: All of Nebraska, Saunemin, Sullivan, Waldo, Pike, Eppards Point,
                Avoca, Pleasant Ridge, Charlotte, Indian Grove, Forrest,
                Chatsworth, Belle Prairie, Fayette and Germanville Townships

That is a complete, authoritative definition, and the app already ships and
trusts TIGER township geometry (the statewide `township` layer). So the district
boundary is DERIVED, not guessed: every edge of the result is a township edge the
Census publishes, and the only judgement is which township goes in which
district, which the county states outright.

This is a deliberate narrowing of "never guess". We are not inventing a boundary;
we are composing published boundaries per a published rule. Anything that would
require judgement — a township split between districts, a name that does not
resolve, a township left unassigned — is a hard failure below rather than a
best-effort match.

THE ONE RECONCILIATION, recorded rather than silently patched: the county writes
"Newton" where TIGER names the township "Newtown". 30 names published, 30
townships in TIGER, 29 exact matches, one left over on each side — so the mapping
is forced, not chosen. It is declared in NAME_FIXES below so the diff shows it.

Regenerate only when the county reapportions (it last did so effective
2002-12-02, and the 2020 census brought no change). Output is one feature per
district, mapshaper-free: the dissolve is the same edge-cancellation walk
build_metro_outline.py uses, so a county outline and this file cannot disagree
about where a township edge is.

Usage:
    python3 scripts/build_livingston_board_districts.py
    python3 scripts/build_livingston_board_districts.py --check
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
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "livingston-county-board-districts.json")

COUNTY_FIPS = "105"
COUNTY_NAME = "Livingston County"
SOURCE_URL = "https://www.livingstoncountyil.gov/government/board.php"

# TIGERweb County Subdivisions — the same service the statewide `township`
# layer answers from, so this file's edges are the edges that layer draws.
TIGER_COUSUB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/1/query")

# The county's published composition, verbatim in reading order.
DISTRICTS = {
    "1": ["Pontiac", "Rooks Creek"],
    "2": ["Reading", "Newton", "Sunbury", "Nevada", "Dwight", "Round Grove",
          "Long Point", "Amity", "Esmen", "Odell", "Union", "Broughton", "Owego"],
    "3": ["Nebraska", "Saunemin", "Sullivan", "Waldo", "Pike", "Eppards Point",
          "Avoca", "Pleasant Ridge", "Charlotte", "Indian Grove", "Forrest",
          "Chatsworth", "Belle Prairie", "Fayette", "Germanville"],
}

# county spelling -> TIGER BASENAME. Only for names where the two disagree and
# the mapping is forced by elimination; never a fuzzy match.
NAME_FIXES = {"Newton": "Newtown"}

# Points that must land in the district the county says they do — the guard that
# proves the composition was applied and simplified without moving a line, not
# merely parsed. Each was geocoded and its containing TOWNSHIP read back from
# TIGER before being written down, so the expected district is derived from the
# published composition rather than recalled. District 1 is two townships, so it
# is the one most likely to break if a name mapping goes wrong.
ANCHORS = [
    (40.8809, -88.6298, "1", "Pontiac, county seat (Pontiac Twp)"),
    (41.0945, -88.4251, "2", "Dwight (Dwight Twp)"),
    (41.0036, -88.5253, "2", "Odell (Odell Twp)"),
    (40.7473, -88.5148, "3", "Fairbury (Indian Grove Twp)"),
    (40.7536, -88.2920, "3", "Chatsworth (Chatsworth Twp)"),
    (40.8781, -88.8612, "3", "Flanagan (Nebraska Twp)"),
]


fail = make_fail("livingston-board")


def fetch_townships():
    require_robots_once(TIGER_COUSUB, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-livingston-board-districts")
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
    claimed = [n for _, n in published]
    if len(claimed) != len(set(claimed)):
        fail("a township is listed in more than one district")
    unassigned = sorted(set(by_name) - set(claimed))
    if unassigned:
        fail("TIGER township(s) in no district: %s — the county's composition is "
             "incomplete or has changed" % ", ".join(unassigned))

    features = []
    for district in sorted(DISTRICTS, key=lambda d: int(d)):
        members = [NAME_FIXES.get(n, n) for n in DISTRICTS[district]]
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
            fail("data/app/livingston-county-board-districts.json is missing — run this script")
        with open(OUT_PATH, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != text:
            fail("shipped file differs from a fresh build (%d vs %d bytes)"
                 % (len(shipped), len(text)))
        print("livingston-board: OK — matches a fresh build (%d districts, %d townships, %d bytes)"
              % (len(features), len(claimed), len(text)))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("livingston-board: wrote %s — %d districts from %d townships, %d bytes"
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
