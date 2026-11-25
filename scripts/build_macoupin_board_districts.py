#!/usr/bin/env python3
"""
Build data/app/macoupin-county-board-districts.json — Macoupin's nine County
Board districts, taken AS THE COUNTY PUBLISHES THEM.

WHY THIS COUNTY WAS STUCK, AND WHAT UNSTUCK IT. The gap record said the county
publishes district maps a person can read and no data behind them, and that
was true of every channel it had checked: the Socrata portal
(data.macoupincountyil.gov, 61 assets, precincts and school districts only) and
the Clerk's Map Room (PDFs). Re-checked 2026-10-15, the county ALSO publishes
boundaries in ArcGIS Online, owned by its own account (`acoe_macoupin`), behind
its public property map at macoupin-il.bhamaps.com. The item carries no licence
text and the map's print template reads "(c) Macoupin County, 2024"; nothing
restricts reuse or display.

THE LAYER MOVED, AND THE OLD ONE WAS THE PRE-2022 MAP (2026-11-25). Until
2026-11-16 the source was GIS_Layers layer 3, "Board Districts". On 2026-11-16
the county deleted that service and published Macoupin_Reference_Boundaries,
whose layer 2, "County Board Districts", is nine polygons keyed `BoardDistr`
"District 1" .. "District 9". Districts 1, 2, 7, 8 and 9 are the same shapes
(areas equal to within 50 square feet); 3, 4, 5 and 6 are not, and the
difference is exactly the change Ordinance O-2021.06 made to the 2012-2021 map,
as the Clerk's redistricting page states it: District 3 loses Shipman 2 to
District 6, and District 4 loses Cahokia 1 and 4 to District 5 and gains
Cahokia 5. So the deleted layer still drew the 2012-2021 lines on that edge,
and from 2026-10-15 to this rebuild the app showed 1,337 people (Census 2020)
in the wrong district. Three readings confirm the new layer is the adopted
plan: the Clerk's Map Room PDFs of Districts 3, 4 and 5 (dated 11/15/21 and
11/19/21) draw the same lines; the county's 3 November 2026 results put every
vote cast in current Cahokia 1 in the District 5 race and none of Cahokia 2's
in it; and the Citizen's Guide (January 2025) list below now agrees on Cahokia
too.

THREE WITNESSES, none of which is the layer itself:

  1. THE CENSUS 2020 VOTING DISTRICTS NEST IN IT. Ordinance O-2021.06 (passed
     18-0 on 9 Nov 2021) writes the plan in the 2005-2021 precinct lines, and
     the Census 2020 voting districts ARE that fabric: every one of the 61 lies
     in exactly one of the county's nine polygons (the worst at 99.6% of its
     area, the rest edge slivers between two independently digitised
     linework sets). That composition is pinned below as VTD_COMPOSITION and
     re-measured on every run, so a redraw of the county's layer fails here.
  2. THE COUNTY'S OWN PRECINCT LIST AGREES. The Citizen's Guide to Macoupin
     County (macoupincountyil.gov, January 2025) lists each district's current
     precincts: Staunton 1-4 in District 1, Bunker Hill 1-3, Dorchester and
     Hilyard in 2, Brighton 1-3 and "Eastern Half of Shipman" in 3, Cahokia 2
     in 4, Cahokia 1 in 5, and so on. Overlaid on the county's current
     precinct layer (layer 3 of the same service), Cahokia 1 and 2 each fall
     wholly in the district the Guide lists, Shipman divides between 3 and 6
     as the Guide says, and Girard 1 and 2 divide between 7 and 9, which the
     Guide writes "Portion of Girard 1 & 2". Measured once, not re-run: the
     Guide is a PDF and witness 1 already pins the same composition.
  3. THE POPULATIONS ADD UP TO THE PERSON. The county's 2020 population,
     44,967, is placed exactly once across the nine districts, and each
     district's block sum equals its voting districts' sum exactly. The spread
     is +10.6% to -6.8% of the 4,996 ideal, which is the plan as drawn and is
     printed rather than smoothed.

The geometry ships UNSIMPLIFIED (6,215 vertices) at six decimals, so the
shared edges between districts are the county's own and cannot drift apart.

Usage:
    python3 scripts/build_macoupin_board_districts.py
    python3 scripts/build_macoupin_board_districts.py --check
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtd_board_districts as V  # noqa: E402  (shared machinery — do not fork)
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_HEADERS_ROSTER_BOT,
    make_fail,
    require_robots_once,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app",
                        "macoupin-county-board-districts.json")
POP_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "population", "17117.json")

COUNTY_FIPS = "117"
COUNTY_POP_2020 = 44967
EXPECT_DISTRICTS = 9
SEATS_PER_DISTRICT = 2

LAYER_URL = ("https://services.arcgis.com/LYDdxoqTV7fw9teL/arcgis/rest/services/"
             "Macoupin_Reference_Boundaries/FeatureServer/2")
KEY_FIELD = "BoardDistr"
SOURCE_LABEL = ("Macoupin County GIS, County Board Districts "
                "(Macoupin_Reference_Boundaries layer 2), plan of Ordinance O-2021.06")
# The layer's own Shape__Area per district (in the service's own units, which
# measure as square feet), as shipped 2026-11-25. The weekly roster job re-reads these without geometry and
# fails when any moves, which is the cheapest way to see a redraw: a change to
# a district's line changes its area. A redraw that moved a line and kept every
# area to the square metre would pass, and nothing cheaper can see it.
DISTRICT_AREAS = {"1": 509224874, "2": 3027856528, "3": 1524607856,
                  "4": 667675155, "5": 1879618241, "6": 9575906241,
                  "7": 1862872290, "8": 863699685, "9": 4278424983}

# Census 2020 voting districts by district, as measured 2026-11-25 (Shipman 2,
# Cahokia 1, 4 and 5 moved from the 2026-10-15 reading of the deleted layer). Each must
# put at least MIN_NEST of its area in the district named here.
VTD_COMPOSITION = {
    "1": ["STAUNTON 1", "STAUNTON 2", "STAUNTON 3", "STAUNTON 4", "STAUNTON 5"],
    "2": ["BUNKER HILL 1", "BUNKER HILL 2", "BUNKER HILL 3", "DORCHESTER 1",
          "DORCHESTER 2", "HILLYARD"],
    "3": ["BRIGHTON 1", "BRIGHTON 2", "BRIGHTON 3", "SHIPMAN 1"],
    "4": ["CAHOKIA 2", "CAHOKIA 5", "MT. OLIVE 1", "MT. OLIVE 2",
          "MT. OLIVE 3", "MT. OLIVE 4", "MT. OLIVE 5", "MT. OLIVE 6"],
    "5": ["CAHOKIA 1", "CAHOKIA 3", "CAHOKIA 4", "GILLESPIE 1", "GILLESPIE 2",
          "GILLESPIE 3", "GILLESPIE 4", "GILLESPIE 5", "GILLESPIE 6"],
    "6": ["BARR", "BIRD", "CHESTERFIELD", "NORTH PALMYRA", "POLK", "SCOTTVILLE",
          "SHIPMAN 2", "SHIPMAN 3", "SOUTH OTTER", "SOUTH PALMYRA",
          "WESTERN MOUND"],
    "7": ["GIRARD 1", "NORTH OTTER", "VIRDEN 1", "VIRDEN 2", "VIRDEN 3", "VIRDEN 4"],
    "8": ["CARLINVILLE 2", "CARLINVILLE 3", "CARLINVILLE 4", "CARLINVILLE 5",
          "CARLINVILLE 6"],
    "9": ["BRUSHY MOUND", "CARLINVILLE 1", "GIRARD 2", "HONEY POINT", "NILWOOD 1",
          "NILWOOD 2", "SHAWS POINT"],
}
EXPECT_VTDS = 61
# The worst measured share was 0.9879 on the deleted layer (2026-10-15) and is
# 0.996 on its replacement (2026-11-25, Cahokia 5); 0.98 stays the floor.
MIN_NEST = 0.98
# Census block population by district, measured 2026-11-25 from the shipped
# population file. Re-asserted exactly; a moved line moves people.
EXPECT_POP = {"1": 5526, "2": 5288, "3": 4655, "4": 4857, "5": 5069,
              "6": 4914, "7": 4861, "8": 5116, "9": 4681}
# Two points the deleted pre-2022 layer put in Districts 4 and 3 and the
# adopted plan puts in 5 (Cahokia 1) and 6 (Shipman 2), so a build from a
# stale copy of the old lines fails here.
SENTINELS = {(39.13129, -89.72776): "5", (39.11348, -90.11859): "6"}
# Districts against the Census 2020 county outline. The county's own linework
# and TIGER's differ by a hairline band (0.028% of the county, measured).
MAX_OVERLAP_M2 = 50.0
MIN_COVERED = 0.995

fail = make_fail("macoupin-board")


def district_key(value):
    """'District 4' -> '4'; anything else comes back unchanged and fails the
    caller's key check."""
    text = str(value or "").strip()
    match = re.match(r"^District\s+(\d+)$", text)
    return match.group(1) if match else text


def fetch_districts():
    url = LAYER_URL + "/query"
    require_robots_once(url, UA_HEADERS_ROSTER_BOT["User-Agent"],
                        headers=UA_HEADERS_ROSTER_BOT,
                        label="il-build-macoupin-board-districts")
    import requests
    resp = requests.get(url, headers=UA_HEADERS_ROSTER_BOT, timeout=90, params={
        "where": "1=1", "outFields": KEY_FIELD, "returnGeometry": "true",
        "outSR": "4326", "f": "geojson"})
    resp.raise_for_status()
    data = resp.json() or {}
    if data.get("error"):
        fail("the county layer answered an error: %r" % data["error"])
    feats = data.get("features") or []
    if len(feats) != EXPECT_DISTRICTS:
        fail("the county layer returned %d districts, expected %d"
             % (len(feats), EXPECT_DISTRICTS))
    return feats


def main():
    from shapely.geometry import Point, mapping, shape
    from shapely.ops import transform, unary_union
    from shapely.prepared import prep
    from build_metro_outline import point_in_rings

    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file, write nothing")
    args = ap.parse_args()

    named = [n for ns in VTD_COMPOSITION.values() for n in ns]
    if len(named) != EXPECT_VTDS or len(set(named)) != EXPECT_VTDS:
        fail("VTD_COMPOSITION names %d voting districts (%d distinct), expected %d"
             % (len(named), len(set(named)), EXPECT_VTDS))
    if sum(EXPECT_POP.values()) != COUNTY_POP_2020:
        fail("EXPECT_POP does not sum to the county's 2020 population")

    districts = {}
    for f in fetch_districts():
        key = district_key((f.get("properties") or {}).get(KEY_FIELD))
        if key not in VTD_COMPOSITION:
            fail("the county layer carries a district keyed %r" % key)
        if key in districts:
            fail("district %s appears twice in the county layer" % key)
        geom = shape(f["geometry"])
        districts[key] = geom if geom.is_valid else geom.buffer(0)

    # Witness 1: the 2005-2021 precinct fabric nests in the county's polygons.
    vtds = V.fetch_vtds(COUNTY_FIPS, shape, fail)
    if len(vtds) != EXPECT_VTDS:
        fail("the census carries %d Macoupin voting districts, expected %d"
             % (len(vtds), EXPECT_VTDS))
    worst = 1.0
    for d, names in VTD_COMPOSITION.items():
        for name in names:
            rec = vtds.get(V.norm(name))
            if rec is None:
                fail("voting district %s is not in the census layer" % name)
            share = rec["geom"].intersection(districts[d]).area / rec["geom"].area
            worst = min(worst, share)
            if share < MIN_NEST:
                fail("voting district %s puts only %.1f%% of its area in District %s "
                     "— the county's layer has been redrawn; re-measure the "
                     "composition before shipping" % (name, share * 100, d))

    # Witness 3: every person placed once, in the measured districts.
    county_geom, county_pop = V.fetch_county(COUNTY_FIPS, shape, fail)
    if county_pop != COUNTY_POP_2020:
        fail("the census county layer reports %d people, expected %d"
             % (county_pop, COUNTY_POP_2020))
    V.check_tiling(districts, county_geom, transform, MAX_OVERLAP_M2, MIN_COVERED,
                   unary_union, fail)
    with open(POP_PATH, encoding="utf-8") as handle:
        blocks = json.load(handle)["points"]
    prepared = {d: prep(g) for d, g in districts.items()}
    pops = {d: 0 for d in districts}
    for lng, lat, people in blocks:
        pt = Point(lng, lat)
        hits = [d for d, g in prepared.items() if g.contains(pt)]
        if len(hits) != 1:
            fail("a census block at %.5f,%.5f (%d people) lands in %s"
                 % (lat, lng, people, hits or "no district"))
        pops[hits[0]] += people
    if pops != EXPECT_POP:
        fail("district populations moved: got %r, expected %r" % (pops, EXPECT_POP))

    features = []
    for d in sorted(districts, key=int):
        features.append({"type": "Feature", "properties": {
            "district": d,
            "population2020": pops[d],
            "source": SOURCE_LABEL,
        }, "geometry": V.round_geom(districts[d], mapping)})

    # The app's own even-odd test, on the rounded output.
    V.verify_point_in_rings(VTD_COMPOSITION, vtds, features, point_in_rings, fail)
    for (lat, lng), want in SENTINELS.items():
        got = [f["properties"]["district"] for f in features
               if point_in_rings(lat, lng, V.rings_of(f["geometry"]))]
        if got != [want]:
            fail("%.5f,%.5f lands in %s, the adopted plan puts it in District %s"
                 % (lat, lng, got or "no district", want))

    payload = {"type": "FeatureCollection", "features": features}
    ideal = COUNTY_POP_2020 / float(EXPECT_DISTRICTS)
    print("macoupin-board: %d districts from the county's own layer; %d census "
          "voting districts nest (worst %.1f%%)" % (len(features), EXPECT_VTDS,
                                                    worst * 100))
    for d in sorted(pops, key=int):
        print("   district %s: %5d people (%+.1f%% of ideal)"
              % (d, pops[d], (pops[d] - ideal) / ideal * 100))
    V.write_or_check([(OUT_PATH, V.dumps(payload))], args.check, REPO_ROOT, fail,
                     "macoupin board districts")


if __name__ == "__main__":
    main()
