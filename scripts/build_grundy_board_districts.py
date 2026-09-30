#!/usr/bin/env python3
"""
Build data/app/grundy-county-board-districts.json — Grundy's 3 County Board
districts, DERIVED by dissolving the county's own precinct layer per the
adopted "Approved County Board Districts (10/12/2021)" map.

WHY THIS EXISTS — the county GIS publishes no board-district geometry (full
23-folder enumeration, re-checked 2026-07-31; the CountyClerk folder holds
only PollingPlaces_SPIE_Public). The adopted map is published as a PDF whose
text layer lists exactly the 40 precincts the shipped county-precinct layer
carries, each with its 2020 census population, plus the three district
totals — but the precinct-to-district assignment itself is encoded only as
the map's drawn district boundary.

HOW THE ASSIGNMENT WAS DERIVED (2026-08-02, recorded so it can be re-run):
programmatically, not by eye. The PDF page was rendered at 300 dpi, the
teal district-boundary strokes isolated by color, the three enclosed
regions labeled by connected-component analysis, and each precinct label
placed into a region using its text-layer coordinates. The proof is
arithmetic: the per-precinct populations printed on the map sum, under this
assignment, to EXACTLY the district totals the map prints —
D1 17,663 / D2 17,364 / D3 17,506 (= 52,533, the printed county total).
Any single misassignment would shift two of those sums by that precinct's
population, so an exact three-way match pins every row. Those populations
and totals are embedded below and re-asserted on every run.

No precinct is split: the adopted districts are compositions of whole
current precincts (the map's own subtitle is "Populations by Precinct and
District"), so unlike LaSalle there is no majority-side approximation and
every district edge is a county-drawn precinct edge.

NAME NORMALIZATION — the map prints Grundy's nine single-precinct townships
bare ("MAZON") where the GIS layer writes an explicit number ("MAZON 1");
both are normalized to the numbered form, and only when the bare name has
no numbered sibling on the map (all nine are unambiguous).

Regenerate when the county re-precincts (the guards below fail loudly if
the 40-name fabric changes) or reapportions (next due after the 2030
census).

Usage:
    python3 scripts/build_grundy_board_districts.py
    python3 scripts/build_grundy_board_districts.py --check
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
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    make_fail,
    require_robots_once,
)

# WHY SHAPELY AND NOT build_metro_outline's dissolve(): same reason as the
# LaSalle build — segment-cancellation dissolve requires exact shared vertex
# chains along interior edges, which county fabrics don't reliably have.
# unary_union does real geometric union; the point_in_rings verification
# below then proves the SHIPPED GeoJSON with the same even-odd test the app
# uses, so the two libraries cross-check each other.

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "grundy-county-board-districts.json")

PRECINCT_URL = ("https://maps.grundyco.org/arcgis/rest/services/"
                "CountyClerk/PollingPlaces_SPIE_Public/MapServer/1/query")
SOURCE_LABEL = ("Approved County Board Districts (10/12/2021), composed from the "
                "county's own precinct GIS per the adopted map's precinct list")
MAP_URL = ("https://www.grundycountyil.gov/Documents/Government/County%20Chairman/"
           "ApprovedBoardDistrictsMap1_2020CensusData_TotalPopByCurrentPrecinct_"
           "20211013_BoardDistrictsByGrundyVoterPrecinctData_ForFullBoard.pdf")

# Every precinct with its 2020 census population AS PRINTED ON THE ADOPTED
# MAP, keyed by the GIS layer's numbered spelling. These are the transcription
# proof, not decoration: the per-district sums are asserted against the map's
# printed totals on every run.
DISTRICTS = {
    "1": {
        "ERIENNA 1": 1566, "ERIENNA 2": 842, "MORRIS 1": 1414, "MORRIS 2": 1671,
        "MORRIS 3": 1327, "MORRIS 4": 1280, "MORRIS 5": 1447, "NETTLE CREEK 1": 501,
        "NORMAN 1": 321, "SARATOGA 1": 1363, "SARATOGA 3": 1101, "SARATOGA 4": 1875,
        "VIENNA 1": 666, "WAUPONSEE 1": 1165, "WAUPONSEE 2": 1124,
    },
    "2": {
        "AUX SABLE 1": 1864, "AUX SABLE 2": 1507, "AUX SABLE 3": 1378,
        "AUX SABLE 4": 2966, "AUX SABLE 5": 2781, "AUX SABLE 6": 2744,
        "AUX SABLE 7": 2121, "SARATOGA 2": 1082, "SARATOGA 5": 921,
    },
    "3": {
        "BRACEVILLE 1": 2161, "BRACEVILLE 2": 1285, "BRACEVILLE 3": 1515,
        "BRACEVILLE 4": 1502, "FELIX 1": 1257, "FELIX 2": 1103, "FELIX 3": 1099,
        "FELIX 4": 979, "GARFIELD 1": 1454, "GOODFARM 1": 353, "GOOSE LAKE 1": 798,
        "GOOSE LAKE 2": 957, "GREENFIELD 1": 991, "HIGHLAND 1": 256, "MAINE 1": 293,
        "MAZON 1": 1503,
    },
}
# The district totals as printed on the adopted map (with the county total).
PRINTED_POP = {"1": 17663, "2": 17364, "3": 17506}
EXPECT_TOTAL_POP = 52533


fail = make_fail("grundy-board")


def fetch_precincts():
    require_robots_once(PRECINCT_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-grundy-board-districts")
    resp = requests.get(PRECINCT_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "1=1",
        "outFields": "NAME",
        "returnGeometry": "true",
        "outSR": "4326",
        "resultRecordCount": "100",
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
    """A point deep inside the feature's LARGEST part (the LaSalle rationale:
    a sliver part's interior sits exactly on a district seam, where
    independently simplified unions blur)."""
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

    # The embedded tables must reproduce the map's printed arithmetic before
    # anything is fetched — a bad edit fails here, not in shipped geometry.
    assignment = {}
    for d, members in DISTRICTS.items():
        for p, pop in members.items():
            if p in assignment:
                fail("precinct %s assigned twice" % p)
            assignment[p] = d
        got = sum(members.values())
        if got != PRINTED_POP[d]:
            fail("district %s populations sum to %d, but the adopted map prints %d — "
                 "the embedded transcription was edited; re-derive it from the map"
                 % (d, got, PRINTED_POP[d]))
    if sum(PRINTED_POP.values()) != EXPECT_TOTAL_POP:
        fail("printed district totals do not sum to the county total")
    if len(assignment) != 40:
        fail("assignment covers %d precincts, expected 40" % len(assignment))

    feats = fetch_precincts()
    by_name = {}
    for f in feats:
        name = str(f["properties"].get("NAME") or "").strip().upper()
        if not name:
            fail("a precinct feature carries no NAME")
        if name in by_name:
            fail("precinct name %r appears twice in the county layer" % name)
        by_name[name] = f

    missing = sorted(set(assignment) - set(by_name))
    if missing:
        fail("assigned precinct(s) not in the county layer: %s — the county "
             "re-precincted; re-derive the map transcription" % ", ".join(missing))
    extra = sorted(set(by_name) - set(assignment))
    if extra:
        fail("county precinct(s) in no district: %s — the county re-precincted; "
             "re-derive the map transcription" % ", ".join(extra))

    features = []
    for d in sorted(DISTRICTS, key=int):
        members = sorted(DISTRICTS[d])
        union = unary_union([shape(by_name[p]["geometry"]).buffer(0) for p in members])
        # Simplify conservatively (~10 m; preserve_topology keeps rings valid).
        # Adjacent districts simplify independently, so shared edges can drift
        # apart by up to the tolerance — the same accepted hairline as the
        # other derived-boundary builds. The containment guard below bounds it.
        union = union.simplify(0.0001, preserve_topology=True)
        geometry = json.loads(json.dumps(mapping(union)))
        features.append({"type": "Feature", "properties": {
            "district": d,
            "population2020": PRINTED_POP[d],
            "precincts": members,
            "source": SOURCE_LABEL,
            "mapUrl": MAP_URL,
        }, "geometry": geometry})

    # Dissolve correctness: every precinct's interior point must land in
    # exactly the district polygon the map assigns it to. Fully derived — no
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
            fail("data/app/grundy-county-board-districts.json is missing — run this script")
        with open(OUT_PATH, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != text:
            fail("shipped file differs from a fresh build (%d vs %d bytes)"
                 % (len(shipped), len(text)))
        print("grundy-board: OK — matches a fresh build (3 districts from 40 precincts, "
              "all 3 printed populations reproduced exactly, %d bytes)" % len(text))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("grundy-board: wrote %s — 3 districts from 40 whole precincts, all 3 "
          "printed populations reproduced exactly, %d bytes"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(text)))


if __name__ == "__main__":
    main()
