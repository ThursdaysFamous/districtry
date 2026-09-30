#!/usr/bin/env python3
"""
Build data/app/woodford-county-board-districts.json by dissolving TIGER
township geometry according to the county's adopted apportionment ordinance.

WHY THIS EXISTS — the county publishes no board-district GIS. Its GIS presence
is TCRPC's (the Tri-County Regional Planning Commission, its GIS of record,
like Logan's), and TCRPC carries precincts and townships but no board
districts. What the county DOES publish is Ordinance No. 2020/21 #005 (the
reapportionment plan, adopted 2021-05-18 as amended, effective 2022-12-05 —
scanned into the board's own May 2021 agenda packet), which composes the three
districts from WHOLE TOWNSHIPS:

    DISTRICT ONE:   Linn, Cazenovia, Clayton, Minonk, Roanoke, Greene,
                    Panola, Palestine, El Paso, and Kansas
    DISTRICT TWO:   Partridge, Spring Bay, and Worth
    DISTRICT THREE: Metamora, Cruger, Olio, and Montgomery

Fifteen members, five elected at large from each district. That is a complete,
authoritative definition, and the app already ships and trusts TIGER township
geometry (the statewide `township` layer) — so the boundary is DERIVED, not
guessed, exactly as Livingston's is: every edge is a township edge the Census
publishes, and the only judgement is which township goes where, which the
ordinance states outright. Anything needing judgement — a split township, an
unresolved name, an unassigned township — is a hard failure below.

The 2026-07-31 validation pass measured the composition's 17 names against
TIGER 17/17, no reconciliation needed (Livingston needed one).

Regenerate only when the county reapportions. Output is one feature per
district, mapshaper-free: the dissolve is the same edge-cancellation walk
build_metro_outline.py uses, so a county outline and this file cannot disagree
about where a township edge is.

Usage:
    python3 scripts/build_woodford_board_districts.py
    python3 scripts/build_woodford_board_districts.py --check
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
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "woodford-county-board-districts.json")

COUNTY_FIPS = "203"
COUNTY_NAME = "Woodford County"
# The ordinance rides pages 12-14 of the board's own May 2021 agenda packet.
SOURCE_URL = "https://www.woodford-county.org/AgendaCenter/ViewFile/Agenda/_05182021-1183"

TIGER_COUSUB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/1/query")

# Ordinance 2020/21 #005 section 2, verbatim in reading order.
DISTRICTS = {
    "1": ["Linn", "Cazenovia", "Clayton", "Minonk", "Roanoke", "Greene",
          "Panola", "Palestine", "El Paso", "Kansas"],
    "2": ["Partridge", "Spring Bay", "Worth"],
    "3": ["Metamora", "Cruger", "Olio", "Montgomery"],
}

# county spelling -> TIGER BASENAME. Empty on purpose: the validation pass
# measured all 17 names identical. Kept so a future census rename has a
# declared place to land instead of a fuzzy match.
NAME_FIXES = {}

# Points that must land in the district the ordinance says they do — the guard
# that proves the composition was applied and simplified without moving a
# line. Each town's township was verified before being written down.
ANCHORS = [
    (40.7392, -89.0165, "1", "El Paso (El Paso Twp)"),
    (40.9045, -89.0343, "1", "Minonk (Minonk Twp)"),
    (40.8018, -89.1997, "1", "Roanoke (Roanoke Twp)"),
    (40.7664, -89.4670, "2", "Germantown Hills (Worth Twp)"),
    (40.8281, -89.5262, "2", "Spring Bay (Spring Bay Twp)"),
    (40.7214, -89.2723, "3", "Eureka, county seat (Olio Twp)"),
    (40.7903, -89.3609, "3", "Metamora (Metamora Twp)"),
]


fail = make_fail("woodford-board")


def fetch_townships():
    require_robots_once(TIGER_COUSUB, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-woodford-board-districts")
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


def rings_of_feature(feature):
    geom = feature["geometry"]
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [r for poly in geom["coordinates"] for r in poly]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped file, write nothing")
    args = ap.parse_args()

    feats = fetch_townships()
    by_name = {}
    for f in feats:
        by_name[(f["properties"].get("BASENAME") or "").strip()] = f

    published = [(d, NAME_FIXES.get(n, n)) for d, names in DISTRICTS.items() for n in names]
    missing = sorted({n for _, n in published if n not in by_name})
    if missing:
        fail("published township(s) not in TIGER: %s" % ", ".join(missing))
    claimed = [n for _, n in published]
    if len(claimed) != len(set(claimed)):
        fail("a township is listed in more than one district")
    unassigned = sorted(set(by_name) - set(claimed))
    if unassigned:
        fail("TIGER township(s) in no district: %s — the ordinance's composition "
             "is incomplete or has changed" % ", ".join(unassigned))

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
            fail("data/app/woodford-county-board-districts.json is missing — run this script")
        with open(OUT_PATH, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != text:
            fail("shipped file differs from a fresh build (%d vs %d bytes)"
                 % (len(shipped), len(text)))
        print("woodford-board: OK — matches a fresh build (%d districts, %d townships, %d bytes)"
              % (len(features), len(claimed), len(text)))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("woodford-board: wrote %s — %d districts from %d townships, %d bytes"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(features), len(claimed), len(text)))
    for f in features:
        print("   district %s: %d townships" % (f["properties"]["district"],
                                                len(f["properties"]["townships"])))


if __name__ == "__main__":
    main()
