#!/usr/bin/env python3
"""
Build data/app/lasalle-county-board-districts.json — LaSalle's 2022-2031 County
Board districts, DERIVED by dissolving the county's own current precinct layer
per the district assignment the county's election canvasses prove it administers.

WHY THIS EXISTS — the 2026-07-31 validation pass found the county's only
published board-district GIS (AGOL CountyBoardDistricts) is the SUPERSEDED
2011-2021 apportionment: frozen 2015-08-25 in schema and data, 2010 census
populations in its Pop100 column, and a roster that disagrees with the county's
current directory on 18 of 29 seats, with returning members renumbered into
different districts. The current map — "Redistricting Map Scenario 6A", adopted
by Resolution #21-126 (Nov 2021, 24-4) for the 2022 through 2030 elections — is
published only as a vector-PDF map pair (DocumentCenter/View/318 + 319, drawn
by Bruce Harris & Associates). No current district GIS exists on either county
server or its ArcGIS Online org.

WHAT THE ASSIGNMENT IS DERIVED FROM — not the map alone: the county's own
Statements of Votes Cast. The Nov 2024 general and Mar 2026 general-primary
canvasses together carry a County Board contest for every one of the 29
districts, listing per precinct which district's contest its voters received —
the county's own administration of the adopted map on the CURRENT precinct
fabric. 108 of 119 precincts vote wholly in one district (the two cycles
overlap on districts 4 and 26 and agree everywhere). The remaining 11 are
SPLIT: their canvass rows register voters in TWO districts, because the county
re-precincted after adoption and let these precincts straddle the district
line (registered-voter counts per side are recorded in SPLITS below).

THE APPROXIMATION, STATED — a split precinct is drawn here with its MAJORITY
side, so the minority side of each is drawn with the wrong district. Measured
against the adopted map's own printed populations, the total misplacement is
~1,659 of 109,658 residents (1.5%), concentrated around the 11 named precincts.
The card says so wherever an affected district renders. Everywhere else the
boundary is the county's own precinct geometry, exact: 9 districts' populations
reproduce the printed values TO THE PERSON (asserted below), and every district
edge is a county-drawn precinct edge.

REFINEMENT PATH (recorded in docs/DATA_LAYER_GUIDEBOOK.md): cut the 11 split
precincts along the adopted map's vector district lines (the Stephenson
georeference route) — or retire this build entirely the day the county
publishes its 2022-2031 districts as GIS.

Regenerate when the county re-precincts (the guards below fail loudly if the
fabric changes) or reapportions (next due after the 2030 census).

Usage:
    python3 scripts/build_lasalle_board_districts.py
    python3 scripts/build_lasalle_board_districts.py --check
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from build_metro_outline import (  # noqa: E402  (shared machinery — do not fork)
    HEADERS, REQUEST_TIMEOUT, point_in_rings,
)
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    make_fail, require_robots_once,
)

# WHY SHAPELY AND NOT build_metro_outline's dissolve(): that dissolve cancels
# segments walked twice, which requires the fabric to share EXACT vertex chains
# along every interior edge. LaSalle's county fabric does not — measured on
# district 16, whose four precincts dissolve to a spurious 3-segment ring plus
# a boundary that fails containment for Deer Park's centroid. unary_union does
# real geometric union and is immune to hairline vertex mismatches; the
# point_in_rings verification below then proves the SHIPPED GeoJSON with the
# same even-odd test the app uses, so the two libraries cross-check each other.

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "lasalle-county-board-districts.json")

PRECINCT_URL = ("https://gis.lasallecounty.org/arcgis/rest/services/"
                "PollingPlaceLocator/MapServer/1/query")
SOURCE_LABEL = ("LaSalle County Resolution #21-126 map (2022-2031), composed from the "
                "county's own precinct GIS per its 2024 + 2026 election canvasses")

# The county's 2020 census population, and the per-precinct population column the
# precinct layer carries. If the county re-precincts, names or the total shift
# and this build refuses to run until the canvass-derived tables are re-derived.
EXPECT_TOTAL_POP = 109658

# Whole precincts per district — each votes entirely in one district's County
# Board contest (Nov 2024 general + Mar 2026 general-primary Statements of Votes
# Cast; the cycles overlap on districts 4 and 26 and agree on every shared row).
WHOLE = {
    "1": ["MENDOTA 1", "MENDOTA 2", "MENDOTA 6", "MENDOTA 7"],
    "2": ["EARL 2", "MENDOTA 4", "MENDOTA 5", "MERIDEN 1", "OPHIR 1"],
    "3": ["ADAMS 1", "ADAMS 2", "EARL 1"],
    "4": ["NORTHVILLE 2", "NORTHVILLE 3", "NORTHVILLE 4", "NORTHVILLE 6"],
    "5": ["NORTHVILLE 1", "NORTHVILLE 5", "NORTHVILLE 7"],
    "6": ["MISSION 1"],
    "7": ["MANLIUS 1", "MANLIUS 4", "MILLER 1", "RUTLAND 2"],
    "8": ["DAYTON 1", "DAYTON 2", "FREEDOM 1", "WALLACE 1"],
    "9": ["DIMMICK 1", "MENDOTA 3", "TROY GROVE 1", "TROY GROVE 2", "WALTHAM 1"],
    "10": ["LA SALLE 10", "PERU 6", "PERU 7", "PERU 8"],
    "11": ["PERU 3", "PERU 5", "PERU 9"],
    "12": ["LA SALLE 5", "PERU 10", "PERU 11", "PERU 2"],
    "13": ["LA SALLE 1", "LA SALLE 3", "LA SALLE 4", "PERU 1"],
    "14": ["LA SALLE 6", "LA SALLE 9"],
    "15": ["LA SALLE 11", "LA SALLE 12", "LA SALLE 13", "LA SALLE 14"],
    "16": ["DEER PARK 1", "LA SALLE 2", "UTICA 1", "UTICA 2"],
    "17": ["OTTAWA 10", "SOUTH OTTAWA 2", "SOUTH OTTAWA 4", "SOUTH OTTAWA 6"],
    "18": ["OTTAWA 13", "OTTAWA 8", "OTTAWA 9"],
    "19": ["OTTAWA 11", "OTTAWA 12", "OTTAWA 4"],
    "20": ["OTTAWA 1", "OTTAWA 2", "OTTAWA 3", "SOUTH OTTAWA 1"],
    "21": ["SOUTH OTTAWA 3", "SOUTH OTTAWA 5", "SOUTH OTTAWA 7"],
    "22": ["FALL RIVER 1", "RUTLAND 1", "RUTLAND 3"],
    "23": ["MANLIUS 2", "MANLIUS 3", "MANLIUS 5"],
    "24": ["ALLEN 1", "BROOKFIELD 1", "FARM RIDGE 1", "GRAND RAPIDS 1",
           "OTTER CREEK 1", "SOUTH OTTAWA 8"],
    "25": ["BRUCE 7", "BRUCE 8", "BRUCE 9", "OTTER CREEK 3"],
    "26": ["BRUCE 5", "OTTER CREEK 2"],
    "27": ["BRUCE 2", "BRUCE 3", "BRUCE 4", "EAGLE 1"],
    "28": ["BRUCE 1", "BRUCE 10", "BRUCE 11"],
    "29": ["EAGLE 2", "EAGLE 3", "EDEN 1", "GROVELAND 1", "HOPE 1", "OSAGE 1",
           "RICHLAND 1", "VERMILLION 1"],
}

# Split precincts: canvass rows register voters in TWO district contests.
# "registered" is each side's registered-voter count as printed in the SVC;
# the precinct is drawn with its majority side.
SPLITS = {
    "BRUCE 12": {"majority": "28", "registered": {"27": 127, "28": 396}},
    "BRUCE 6": {"majority": "26", "registered": {"25": 139, "26": 733}},
    "EDEN 2": {"majority": "15", "registered": {"15": 271, "29": 105}},
    "LA SALLE 7": {"majority": "14", "registered": {"14": 466, "16": 11}},
    "LA SALLE 8": {"majority": "14", "registered": {"14": 664, "16": 46}},
    "MISSION 2": {"majority": "6", "registered": {"6": 804, "7": 43}},
    "OTTAWA 5": {"majority": "19", "registered": {"18": 102, "19": 451}},
    "OTTAWA 6": {"majority": "20", "registered": {"17": 118, "20": 248}},
    "OTTAWA 7": {"majority": "18", "registered": {"17": 30, "18": 451}},
    "PERU 4": {"majority": "10", "registered": {"10": 425, "11": 65}},
    "SERENA 1": {"majority": "3", "registered": {"3": 504, "5": 345}},
}

# The adopted map prints each district's 2020 population. For districts whose
# membership involves no split precinct and no post-adoption re-precincting,
# the dissolve must reproduce the printed number TO THE PERSON — the same
# arithmetic proof Stephenson's and Carroll's builds carry. Asserted for the
# nine districts that satisfied it when this table was derived; a failure
# means the county re-precincted and the canvass tables must be re-derived.
PRINTED_POP = {"1": 3934, "2": 3966, "4": 3850, "8": 3649, "9": 3731,
               "12": 3870, "13": 3747, "21": 3660, "23": 3662}


fail = make_fail("lasalle-board")


def fetch_precincts():
    # THE SITE'S RULES ARE READ BEFORE THE FIRST QUERY, with the identity this
    # fetch sends. gis.lasallecounty.org had been recorded as unreadable, which
    # RFC 9309 files as disallow-all; re-measured from a GitHub runner on
    # 2026-10-01, the vantage this builder runs from, it answers HTTP 404 for
    # robots.txt and so publishes no rules at all. The earlier reading was a
    # timeout on one runner moment and was never anybody's policy.
    require_robots_once(PRECINCT_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="lasalle-board")
    resp = requests.get(PRECINCT_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "1=1",
        "outFields": "PRECINCT,SUM_P0010001",
        "returnGeometry": "true",
        "outSR": "4326",
        "resultRecordCount": "200",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if not feats:
        fail("county precinct service returned no features")
    return feats


def rings_of_feature(feature):
    geom = feature["geometry"]
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [r for poly in geom["coordinates"] for r in poly]


def interior_point(feature):
    """A point deep inside the feature's LARGEST part. shapely picks it (the
    county fabric carries centimeter-scale sliver parts — Ottawa 4's first
    MultiPolygon part is ~4 cm wide — and a sliver's interior sits exactly on
    the seam between districts, where independently simplified unions blur)."""
    # Local, not module scope: this module's composition constant is
    # imported by the ROSTER builder, whose CI job installs no geometry
    # stack. Keep the heavy imports on the path that needs them.
    from shapely.geometry import shape
    geom = shape(feature["geometry"]).buffer(0)
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda g: g.area)
    p = geom.representative_point()
    return p.y, p.x


def main():
    # Local, not module scope: this module's composition constant is
    # imported by the ROSTER builder, whose CI job installs no geometry
    # stack. Keep the heavy imports on the path that needs them.
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped file, write nothing")
    args = ap.parse_args()

    feats = fetch_precincts()
    by_name = {}
    for f in feats:
        name = str(f["properties"].get("PRECINCT") or "").strip().upper()
        if not name:
            fail("a precinct feature carries no PRECINCT name")
        if name in by_name:
            fail("precinct name %r appears twice in the county layer" % name)
        by_name[name] = f

    assignment = {}
    for d, names in WHOLE.items():
        for p in names:
            if p in assignment:
                fail("precinct %s assigned twice" % p)
            assignment[p] = d
    for p, s in SPLITS.items():
        if p in assignment:
            fail("split precinct %s also listed as whole" % p)
        if s["majority"] not in s["registered"]:
            fail("split %s: majority %s not among its registered sides" % (p, s["majority"]))
        assignment[p] = s["majority"]

    missing = sorted(set(assignment) - set(by_name))
    if missing:
        fail("assigned precinct(s) not in the county layer: %s — the county "
             "re-precincted; re-derive the canvass tables" % ", ".join(missing))
    extra = sorted(set(by_name) - set(assignment))
    if extra:
        fail("county precinct(s) in no district: %s — the county re-precincted; "
             "re-derive the canvass tables" % ", ".join(extra))

    total_pop = sum(int(f["properties"].get("SUM_P0010001") or 0) for f in feats)
    if total_pop != EXPECT_TOTAL_POP:
        fail("county population sums to %d, expected %d — the precinct fabric "
             "changed; re-derive the canvass tables" % (total_pop, EXPECT_TOTAL_POP))

    districts = sorted({d for d in assignment.values()}, key=int)
    if len(districts) != 29:
        fail("assignment covers %d districts, expected 29" % len(districts))

    for d, want in PRINTED_POP.items():
        got = sum(int(by_name[p]["properties"].get("SUM_P0010001") or 0)
                  for p, dd in assignment.items() if dd == d)
        if got != want:
            fail("district %s sums to %d, but the adopted map prints %d — the "
                 "county re-precincted inside a district this build treats as "
                 "drift-free; re-derive the canvass tables" % (d, got, want))

    features = []
    for d in districts:
        members = sorted(p for p, dd in assignment.items() if dd == d)
        union = unary_union([shape(by_name[p]["geometry"]).buffer(0) for p in members])
        # Simplify conservatively (~10 m; preserve_topology keeps rings valid).
        # Adjacent districts simplify independently, so shared edges can drift
        # apart by up to the tolerance — the same accepted hairline as the other
        # derived-boundary builds. The containment guard below bounds it.
        union = union.simplify(0.0001, preserve_topology=True)
        geometry = json.loads(json.dumps(mapping(union)))
        splits_here = [
            {"precinct": p, "drawnWith": s["majority"],
             "alsoIn": [k for k in sorted(s["registered"], key=int) if k != s["majority"]][0],
             "registered": s["registered"]}
            for p, s in sorted(SPLITS.items()) if d in s["registered"]
        ]
        props = {"district": d, "precincts": members, "source": SOURCE_LABEL}
        if splits_here:
            props["splits"] = splits_here
        features.append({"type": "Feature", "properties": props,
                         "geometry": geometry})

    # Dissolve correctness: every precinct's interior point must land in exactly
    # the district polygon its canvass row assigns it to. Fully derived — no
    # hand-picked anchors to go stale.
    for p, d in sorted(assignment.items()):
        lat, lng = interior_point(by_name[p])
        hits = [f["properties"]["district"] for f in features
                if point_in_rings(lat, lng, rings_of_feature(f))]
        if hits != [d]:
            fail("interior point of %s should land in district %s, got %s"
                 % (p, d, hits or "none"))

    payload = {"type": "FeatureCollection", "features": features}
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("data/app/lasalle-county-board-districts.json is missing — run this script")
        with open(OUT_PATH, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != text:
            fail("shipped file differs from a fresh build (%d vs %d bytes)"
                 % (len(shipped), len(text)))
        print("lasalle-board: OK — matches a fresh build (29 districts from %d precincts, "
              "%d split, %d printed populations reproduced exactly, %d bytes)"
              % (len(assignment), len(SPLITS), len(PRINTED_POP), len(text)))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("lasalle-board: wrote %s — 29 districts from %d precincts (%d split, drawn "
          "with their majority side), %d printed populations reproduced exactly, "
          "%d bytes" % (os.path.relpath(OUT_PATH, REPO_ROOT), len(assignment),
                        len(SPLITS), len(PRINTED_POP), len(text)))


if __name__ == "__main__":
    main()
