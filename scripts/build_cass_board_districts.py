#!/usr/bin/env python3
"""
Build data/app/cass-county-board-districts.json — Cass's 4 County Board
districts, DERIVED by dissolving Census 2020 voting districts per the
composition the county publishes as a table.

WHY THIS EXISTS — the county's GIS is a Beacon/Schneider parcel viewer with no
public REST surface, and it publishes no board-district geometry. What it does
publish is "CASS COUNTY BOARD DISTRICTS", a one-page PDF listing each district
as a column of named, numbered precincts. That PDF is text-extractable (it was
read directly, not OCR'd) and its 21 precinct names match TIGER's Census 2020
voting districts for the county EXACTLY, name and number, 21/21.

TWO THINGS TO KNOW BEFORE TRUSTING THIS BUILD:

1. NO WEEKLY DRIFT CHECK IS POSSIBLE HERE. De Witt's and Washington's derived
   boundaries are cross-checked every week because those counties print their
   composition on the same HTML page their roster is scraped from. Cass prints
   it only in a PDF that the roster page merely links, so a redistricting would
   NOT turn a weekly job red on the composition itself. What the roster builder
   CAN check — and does — is that the SEATS PER DISTRICT still match the table
   below, which is the input the population test depends on. A reapportionment
   almost always changes those, so it is a real if indirect tripwire. Treat the
   composition as needing a human re-read at the next census.

2. THE BOARD IS NOT EVENLY SIZED, AND THAT CHANGES THE POPULATION TEST. Cass
   seats ELEVEN members as 3/3/3/2. Checking per-DISTRICT population reports a
   28.8% spread and looks like a broken transcription; checking per MEMBER — the
   basis a multi-member apportionment actually balances on — reports 12.3%,
   which is an ordinary rural apportionment. The seat counts below come from the
   county's own board page and are what make the test meaningful.

Usage:
    python3 scripts/build_cass_board_districts.py
    python3 scripts/build_cass_board_districts.py --check
"""

import argparse
import json
import os
import re
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

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "cass-county-board-districts.json")

VTD_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
           "tigerWMS_Census2020/MapServer/58/query")     # 58 = Voting Districts
STATE_FIPS = "17"
COUNTY_FIPS = "017"
ROSTER_URL = "https://co.cass.il.us/elected-officials/cass-county-board"
COMPOSITION_PDF = "https://co.cass.il.us/download_file/view/446/202"
SOURCE_LABEL = ("Census 2020 voting districts dissolved per the county's own "
                "'CASS COUNTY BOARD DISTRICTS' table")

# Transcribed from the county's PDF, column by column. The numbers are part of
# the precinct names, not district ordinals.
DISTRICTS = {
    "1": ["BEARDSTOWN 1", "BEARDSTOWN 2", "BEARDSTOWN 3", "BEARDSTOWN 4"],
    "2": ["BEARDSTOWN 5", "BEARDSTOWN 6", "BEARDSTOWN 7", "BEARDSTOWN 8", "HAGENER 9"],
    "3": ["BLUFF SPRINGS 10", "ARENZVILLE 11", "SANGAMON VALLEY 12",
          "VIRGINIA 13", "VIRGINIA 14", "VIRGINIA 15"],
    "4": ["PHILADELPHIA 16", "PANTHER CREEK 17", "CHANDLERVILLE 18",
          "NEWMANSVILLE 19", "ASHLAND 20", "ASHLAND 21"],
}
# Seats per district, from the county's board page. See note 2 in the header:
# without these the population test measures the wrong thing.
SEATS = {"1": 3, "2": 3, "3": 3, "4": 2}
EXPECT_PRECINCTS = 21
# Per-MEMBER spread. Loose on purpose — a transcription smoke test, not a
# Voting Rights Act analysis.
MAX_POP_SPREAD = 0.20


fail = make_fail("cass-board")


def norm(name):
    return " ".join(str(name or "").upper().split())


def fetch_vtds():
    require_robots_once(VTD_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-cass-board-districts")
    resp = requests.get(VTD_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, COUNTY_FIPS),
        "outFields": "BASENAME,NAME,POP100", "returnGeometry": "true",
        "outSR": "4326", "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if not feats:
        fail("TIGERweb returned no voting districts for the county")
    return feats


def rings_of(geometry):
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    return [r for poly in geometry["coordinates"] for r in poly]


def interior_point(geom):
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

    assigned = [norm(n) for names in DISTRICTS.values() for n in names]
    if len(assigned) != len(set(assigned)):
        dupes = sorted({n for n in assigned if assigned.count(n) > 1})
        fail("the composition names these precincts more than once: %s" % ", ".join(dupes))
    if len(assigned) != EXPECT_PRECINCTS:
        fail("the composition names %d precincts, the county runs %d"
             % (len(assigned), EXPECT_PRECINCTS))
    if sorted(SEATS) != sorted(DISTRICTS):
        fail("SEATS and DISTRICTS name different districts")

    feats = fetch_vtds()
    by_name, pops = {}, {}
    for f in feats:
        props = f.get("properties") or {}
        name = props.get("BASENAME") or re.sub(r"\s+Voting District$", "", props.get("NAME") or "")
        key = norm(name)
        if not key:
            continue
        by_name[key] = f
        if props.get("POP100") is not None:
            pops[key] = int(props["POP100"])
    if len(by_name) != EXPECT_PRECINCTS:
        fail("TIGER carries %d voting districts for the county, expected %d — the "
             "county re-precincted; re-read the composition PDF before rebuilding"
             % (len(by_name), EXPECT_PRECINCTS))

    missing = sorted(set(assigned) - set(by_name))
    if missing:
        fail("the composition names precincts TIGER does not have: %s" % ", ".join(missing))
    unassigned = sorted(set(by_name) - set(assigned))
    if unassigned:
        fail("TIGER has precincts no district claims: %s" % ", ".join(unassigned))

    district_pop = {}
    for district, names in DISTRICTS.items():
        vals = [pops.get(norm(n)) for n in names]
        if any(v is None for v in vals):
            fail("no Census 2020 population for: %s"
                 % ", ".join(n for n, v in zip(names, vals) if v is None))
        district_pop[district] = sum(vals)

    total = sum(district_pop.values())
    seats = sum(SEATS.values())
    per_member = total / float(seats)
    spread = max(abs(district_pop[d] / float(SEATS[d]) - per_member)
                 for d in district_pop) / per_member
    if spread > MAX_POP_SPREAD:
        fail("districts are unbalanced by %.1f%% PER MEMBER (%s) — beyond what a real "
             "apportionment would allow, so the composition or the seat counts are "
             "suspect" % (spread * 100,
                          ", ".join("%s=%d/%d" % (d, district_pop[d], SEATS[d])
                                    for d in sorted(district_pop))))

    features = []
    for district in sorted(DISTRICTS):
        parts = [shape(by_name[norm(n)]["geometry"]).buffer(0) for n in DISTRICTS[district]]
        merged = unary_union(parts)
        if merged.is_empty:
            fail("district %s dissolved to an empty geometry" % district)
        features.append({
            "type": "Feature",
            "properties": {"district": district, "precincts": len(DISTRICTS[district]),
                           "seats": SEATS[district], "pop2020": district_pop[district]},
            "geometry": mapping(merged),
        })

    for district, names in DISTRICTS.items():
        for name in names:
            lat, lon = interior_point(shape(by_name[norm(name)]["geometry"]).buffer(0))
            hits = [f["properties"]["district"] for f in features
                    if point_in_rings(lat, lon, rings_of(f["geometry"]))]
            if hits != [district]:
                fail("precinct %s lands in %s, expected only %s"
                     % (name, hits or "no district", district))

    payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL,
            "compositionPdf": COMPOSITION_PDF,
            "rosterUrl": ROSTER_URL,
            "note": ("Cass publishes no board GIS; these are Census 2020 voting "
                     "districts dissolved per the county's own published district "
                     "table. The board seats 11 members as 3/3/3/2, so the districts "
                     "balance per member rather than per district."),
        },
        "features": features,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"
    summary = ", ".join("%s=%dp/%dseats/%d people" % (f["properties"]["district"],
                                                      f["properties"]["precincts"],
                                                      f["properties"]["seats"],
                                                      f["properties"]["pop2020"])
                        for f in features)
    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("%s does not exist" % OUT_PATH)
        with open(OUT_PATH, encoding="utf-8") as f:
            if f.read() != body:
                fail("%s differs from a fresh build" % OUT_PATH)
        print("cass-board: OK — matches a fresh build (%s; per-member spread %.1f%%)"
              % (summary, spread * 100))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(body)
    print("cass-board: wrote %s — 4 districts (%s), total %d across %d seats, "
          "per-member spread %.1f%%" % (OUT_PATH, summary, total, seats, spread * 100))


if __name__ == "__main__":
    main()
