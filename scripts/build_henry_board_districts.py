#!/usr/bin/env python3
"""
Build data/app/henry-county-board-districts.json by dissolving TIGER
township geometry according to the county's adopted apportionment ordinance.

WHY THIS EXISTS — the county publishes no board-district GIS (its public
viewer is Sidwell Portico, parcels and townships only). What it DOES
publish is the adopted plan: Ordinance 21-33, adopted 2021-11-18 by a 16-0
vote (the board's own Recessed Annual Session minutes), codified at county
code Sec. 30.03, republished by the county clerk today as "2022 County
Board Districts" (DocumentCenter/View/301) and filed with the Illinois
State Board of Elections as the county's re-apportionment map. Two
districts, ten members each, composed from WHOLE TOWNSHIPS.

HOW THE COMPOSITION WAS PROVEN (2026-08-02) — the clerk's map is a raster,
so the 12+12 assignment below was read from its drawn boundary and then
pinned arithmetically THREE ways:
  1. The map prints every township's population for BOTH census years and
     both district totals for both years; the composition below reproduces
     all four printed totals to the person (2010: 25,158 + 25,328 = 50,486;
     2020: 24,931 + 24,353 = 49,284 — each the county's official census
     total). A single misassignment would shift two sums.
  2. All 24 printed 2020 township populations equal the official Census
     POP100 values exactly (re-asserted live on every run, below).
  3. All 24 township names match TIGER 24/24 (and the county's own
     PoliticalTownships_Henry layer carries the same 24), so no NAME_FIXES
     are needed.

The boundary is DERIVED, not guessed, exactly as Livingston's and
Woodford's are: every edge is a township edge the Census publishes, and the
only judgement is which township goes where, which the proof above pins.

Regenerate only when the county reapportions. Output is one feature per
district, mapshaper-free: the dissolve is the same edge-cancellation walk
build_metro_outline.py uses, so a county outline and this file cannot
disagree about where a township edge is.

Usage:
    python3 scripts/build_henry_board_districts.py
    python3 scripts/build_henry_board_districts.py --check
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
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "henry-county-board-districts.json")

COUNTY_FIPS = "073"
COUNTY_NAME = "Henry County"
# The clerk's own republication of the adopted Ordinance 21-33 map.
SOURCE_URL = "https://www.henrycty.com/DocumentCenter/View/301/2022-County-Board-Districts-PDF"

# Geometry AND the live population cross-check both come from TIGERweb; the
# Census2020 vintage carries POP100, which the base layer does not.
TIGER_COUSUB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "tigerWMS_Census2020/MapServer/20/query")

# Ordinance 21-33's composition with each township's populations AS PRINTED
# ON THE ADOPTED MAP — (2010, 2020) — keyed by the TIGER BASENAME (verbatim
# match, all 24). These are the transcription proof, not decoration: the
# per-district sums are asserted against the map's printed totals, and the
# 2020 column against live Census POP100, on every run.
DISTRICTS = {
    "1": {
        "Colona": (6822, 6706), "Hanna": (2344, 2308), "Phenix": (1672, 1713),
        "Loraine": (290, 244), "Yorktown": (431, 447), "Edford": (667, 685),
        "Geneseo": (7468, 7567), "Atkinson": (1274, 1246), "Western": (3053, 2974),
        "Osco": (459, 434), "Munson": (400, 385), "Cornwall": (278, 222),
    },
    "2": {
        "Alba": (220, 173), "Annawan": (1112, 1143), "Lynn": (745, 763),
        "Andover": (954, 881), "Cambridge": (2525, 2405), "Burns": (265, 248),
        "Kewanee": (10162, 9800), "Oxford": (1213, 1176), "Clover": (938, 847),
        "Weller": (422, 413), "Galva": (2837, 2712), "Wethersfield": (3935, 3792),
    },
}
# The district totals as printed on the adopted map, (2010, 2020).
PRINTED_POP = {"1": (25158, 24931), "2": (25328, 24353)}

# Points that must land in the district the ordinance says they do — the guard
# that proves the composition was applied and simplified without moving a
# line. Each town's township was verified against the county's own
# PoliticalTownships_Henry layer before being written down.
ANCHORS = [
    (41.4489, -90.1543, "1", "Geneseo (Geneseo Twp)"),
    (41.4839, -90.3468, "1", "Colona (Colona Twp)"),
    (41.3545, -90.3815, "1", "Orion (Western Twp)"),
    (41.3036, -90.1929, "2", "Cambridge, county seat (Cambridge Twp)"),
    (41.2456, -89.9246, "2", "Kewanee (Kewanee Twp)"),
    (41.1675, -90.0432, "2", "Galva (Galva Twp)"),
    (41.3978, -89.9070, "2", "Annawan (Annawan Twp)"),
]


fail = make_fail("henry-board")


def fetch_townships():
    require_robots_once(TIGER_COUSUB, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-henry-board-districts")
    resp = requests.get(TIGER_COUSUB, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, COUNTY_FIPS),
        "outFields": "BASENAME,NAME,GEOID,POP100",
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

    # The embedded tables must reproduce the map's printed arithmetic before
    # anything is fetched — a bad edit fails here, not in shipped geometry.
    for d, members in DISTRICTS.items():
        for yr_idx, yr in ((0, "2010"), (1, "2020")):
            got = sum(pops[yr_idx] for pops in members.values())
            if got != PRINTED_POP[d][yr_idx]:
                fail("district %s %s populations sum to %d, but the adopted map "
                     "prints %d — the embedded transcription was edited; re-derive "
                     "it from the map" % (d, yr, got, PRINTED_POP[d][yr_idx]))

    feats = fetch_townships()
    by_name = {}
    for f in feats:
        by_name[(f["properties"].get("BASENAME") or "").strip()] = f

    published = [(d, n) for d, members in DISTRICTS.items() for n in members]
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

    # Proof leg 2, live: every printed 2020 population must equal the official
    # Census POP100 for its township.
    for d, members in DISTRICTS.items():
        for n, pops in members.items():
            live = by_name[n]["properties"].get("POP100")
            if live is not None and int(live) != pops[1]:
                fail("township %s: map prints 2020 population %d but Census "
                     "POP100 is %s — the transcription is wrong" % (n, pops[1], live))

    features = []
    for district in sorted(DISTRICTS, key=lambda d: int(d)):
        members = sorted(DISTRICTS[district])
        rings = dissolve([by_name[n] for n in members])
        rings = [simplify(r, SIMPLIFY_TOLERANCE_M) for r in rings]
        polys = group_rings(rings)
        geometry = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                    else {"type": "MultiPolygon", "coordinates": polys})
        features.append({
            "type": "Feature",
            "properties": {
                "district": district,
                "population2020": PRINTED_POP[district][1],
                "townships": members,
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
            fail("data/app/henry-county-board-districts.json is missing — run this script")
        with open(OUT_PATH, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != text:
            fail("shipped file differs from a fresh build (%d vs %d bytes)"
                 % (len(shipped), len(text)))
        print("henry-board: OK — matches a fresh build (%d districts, %d townships, "
              "all 4 printed district totals + 24 Census POP100 values reproduced, %d bytes)"
              % (len(features), len(claimed), len(text)))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("henry-board: wrote %s — %d districts from %d townships, all 4 printed "
          "district totals + 24 Census POP100 values reproduced, %d bytes"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(features), len(claimed), len(text)))
    for f in features:
        print("   district %s: %d townships" % (f["properties"]["district"],
                                                len(f["properties"]["townships"])))


if __name__ == "__main__":
    main()
