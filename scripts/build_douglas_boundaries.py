#!/usr/bin/env python3
"""
Build data/app/douglas-precincts.json and
data/app/douglas-county-board-districts.json — Douglas County's 17 voting
precincts and its 7 County Board districts.

THE COUNTY PUBLISHES ITS OWN BOARD DISTRICTS, and nobody here had looked. This
county sat on the frontier as a split-precinct county — two of its seventeen
precincts vote in two districts each, so no dissolve of whole precincts can draw
it — and the 2026-08-23 sweep that went looking for a vector district map found
something better: douglascountyil.gov links an ArcGIS web map whose application
config names ONE parcel service, while the ORG BEHIND THAT SERVICE
(services3.arcgis.com/HXjsHxkFFcZquC8P) carries FIFTY-FOUR, among them
CountyBoardDistricts and VotingDistricts. Both are shared public, Query-capable,
with empty licenseInfo and no copyright text.

A VIEWER SHOWS WHAT IT USES; THE ORG SHOWS WHAT THE COUNTY HAS. That is the
Richland finding for a second time, and it is why this build reads geometry
rather than deriving it: the districts ship AS THE COUNTY DRAWS THEM, with no
dissolve, no georeferencing and no map to interpret. The split precincts stop
mattering, because the districts do not have to be composed from precincts.

THE CERTIFIED RETURNS ARE THE CHECK, and they are not the same source. The
county publishes its own Election Summary Reports, and the 8 Nov 2022 General
ran all seven districts, printing for each the NUMBER of precincts that voted in
it (never their names — this is a summary report, not a Statement of Votes
Cast). Those seven numbers are:

    D1 2   D2 2   D3 3   D4 2   D5 3   D6 2   D7 5   = 19

Nineteen against a county of SEVENTEEN precincts, because the two split ones are
counted in both of their districts. Overlaying the county's precinct layer on
the county's district layer reproduces all seven numbers exactly, including both
splits — BOURBON 2 (60.0% District 1 / 39.9% District 3) and BOWDRE (62.5%
District 5 / 37.5% District 7). That is a seven-way agreement between two
independently maintained county products, and it is checked here rather than
described: CERTIFIED_PRECINCT_COUNTS is a gate.

THREE MORE THINGS VERIFIED RATHER THAN ASSUMED:

  * The district layer's own TOTAL_POP field sums to 19,740 — Douglas County's
    EXACT Census 2020 population — running 2,504 to 3,230 against a 2,820 ideal.
  * The seven tile the county: 99.97% covered, with pairwise overlap and outside
    spill both held under ceilings below. Those residuals are digitisation noise
    between two independently drawn county layers, not real gaps.
  * The census voting districts carry the county's own 17 precinct names 17/17
    and sum to the same 19,740, so the precinct layer is the county's fabric.

WHAT SHIPS FOR A SPLIT PRECINCT: a LIST of the two districts it lies in, not one
of them. In Bourbon 2 and Bowdre the precinct genuinely does not determine the
district, and the card says which two it could be rather than picking the larger
share. NO POLLING PLACE ships, by the rule Calhoun's build set.

THIS IS A RARE OPERATOR STEP (requests + shapely). Re-run if Douglas
reapportions or re-precincts. Output is deterministic, so --check is a byte
compare.

Usage:
    python3 scripts/build_douglas_boundaries.py [--check]
"""

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtd_board_districts as V  # noqa: E402
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    make_fail,
    require_robots_once,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PRECINCTS = os.path.join(REPO_ROOT, "il", "data", "app", "douglas-precincts.json")
OUT_DISTRICTS = os.path.join(REPO_ROOT, "il", "data", "app",
                             "douglas-county-board-districts.json")

COUNTY_FIPS = "041"
COUNTY_POP_2020 = 19740
EXPECTED_PRECINCTS = 17
EXPECTED_DISTRICTS = 7
SEATS_PER_DISTRICT = 1          # seven single-member districts, staggered

ORG = "https://services3.arcgis.com/HXjsHxkFFcZquC8P/arcgis/rest/services"
DISTRICT_SERVICE = ORG + "/CountyBoardDistricts/FeatureServer/0/query"
PRECINCT_SERVICE = ORG + "/VotingDistricts/FeatureServer/0/query"
GIS_URL = "https://douglascountyil.gov/supervisor-of-assessments"
ELECTIONS_URL = "https://douglascountyil.gov/clerk-recorder/elections"

SOURCE_LABEL = ("Douglas County's own County Board district boundaries, published "
                "as a public feature service by the county's GIS "
                "(services3.arcgis.com/HXjsHxkFFcZquC8P), with precincts from the "
                "Census 2020 voting districts")

# The county's certified 8 Nov 2022 General Election Summary Report ran all
# seven districts and printed the NUMBER of precincts voting in each. Nineteen
# against seventeen precincts, because the two split ones count twice.
CERTIFIED_PRECINCT_COUNTS = {"1": 2, "2": 2, "3": 3, "4": 2, "5": 3, "6": 2, "7": 5}
CERTIFIED_SOURCE = "the county's certified 8 November 2022 General Election Summary Report"

# A precinct holding at least this share of its area in a second district is
# SPLIT. Measured margin: the largest minority share among the fifteen whole
# precincts is 0.6%, and the two real splits sit at 39.9% and 37.5%.
SPLIT_SHARE_MIN = 0.05
BALANCE_DEV_MAX = 0.30          # measured 0.145
MAX_OVERLAP_M2 = 20000.0        # measured 2,853 across all 21 pairs
MAX_OUTSIDE_M2 = 200000.0       # measured 92,043 — 0.009% of the county
MIN_COVERED = 0.999


fail = make_fail("douglas-boundaries")


def fetch_service(url, shape_fn):
    import requests
    require_robots_once(url, V["User-Agent"], headers=V,
                        label="il-build-douglas-boundaries")
    resp = requests.get(url, headers=V.HEADERS, timeout=V.REQUEST_TIMEOUT,
                        params={"where": "1=1", "outFields": "*",
                                "returnGeometry": "true", "outSR": "4326",
                                "f": "geojson"})
    resp.raise_for_status()
    out = []
    for feature in resp.json().get("features") or []:
        geom = shape_fn(feature["geometry"])
        out.append((feature["properties"], geom if geom.is_valid else geom.buffer(0)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped files match a fresh build")
    args = ap.parse_args()

    from shapely.geometry import shape, mapping   # noqa: E402  (heavy, function-local)
    from shapely.ops import unary_union, transform  # noqa: E402

    county_geom, county_pop = V.fetch_county(COUNTY_FIPS, shape, fail)
    if county_pop != COUNTY_POP_2020:
        fail("census county population is %d, expected %d" % (county_pop, COUNTY_POP_2020))

    raw = fetch_service(DISTRICT_SERVICE, shape)
    if len(raw) != EXPECTED_DISTRICTS:
        fail("the county's CountyBoardDistricts service returned %d features, "
             "expected %d" % (len(raw), EXPECTED_DISTRICTS))
    districts, pops = {}, {}
    for props, geom in raw:
        # The service keys its districts as zero-padded strings ("001").
        name = str(props.get("Nam") or "").strip()
        dnum = name.lstrip("0") or name
        if not dnum.isdigit():
            fail("a district carries the unreadable key %r" % name)
        if dnum in districts:
            fail("the service returned district %s twice" % dnum)
        districts[dnum] = geom
        pops[dnum] = int(props.get("TOTAL_POP") or 0)
    if sorted(districts, key=int) != [str(i) for i in range(1, EXPECTED_DISTRICTS + 1)]:
        fail("the districts are keyed %s, expected 1-%d"
             % (sorted(districts), EXPECTED_DISTRICTS))
    if sum(pops.values()) != county_pop:
        fail("the district layer's TOTAL_POP sums to %d and the county to %d — the "
             "county's own layer no longer accounts for its whole population"
             % (sum(pops.values()), county_pop))

    vtds = V.fetch_vtds(COUNTY_FIPS, shape, fail)
    if len(vtds) != EXPECTED_PRECINCTS:
        fail("the census voting-district layer carries %d Douglas features, "
             "expected %d" % (len(vtds), EXPECTED_PRECINCTS))
    # The county's own precinct names, from its own VotingDistricts service —
    # this is what the Jasper test compares the census fabric against, rather
    # than a name list transcribed from anywhere.
    county_precincts = [str(props.get("NAME") or "").strip()
                        for props, _ in fetch_service(PRECINCT_SERVICE, shape)]
    if len(county_precincts) != EXPECTED_PRECINCTS:
        fail("the county's VotingDistricts service returned %d features, expected %d"
             % (len(county_precincts), EXPECTED_PRECINCTS))
    V.check_fabric(vtds, county_precincts, county_pop, fail)

    # ---- overlay: which district(s) each precinct lies in -------------------
    where, split_of = {}, {}
    for key, rec in vtds.items():
        geom = rec["geom"]
        shares = sorted(((geom.intersection(districts[d]).area / geom.area), d)
                        for d in districts)
        shares.reverse()
        held = [d for frac, d in shares if frac >= SPLIT_SHARE_MIN]
        if not held:
            fail("precinct %s lies in no district at all" % rec["basename"])
        if len(held) > 2:
            fail("precinct %s lies in %d districts (%s) — this build handles at "
                 "most two" % (rec["basename"], len(held), ", ".join(sorted(held, key=int))))
        if len(held) == 1:
            where[key] = held[0]
        else:
            split_of[key] = sorted(held, key=int)

    counts = {d: 0 for d in districts}
    for d in where.values():
        counts[d] += 1
    for held in split_of.values():
        for d in held:
            counts[d] += 1
    if counts != CERTIFIED_PRECINCT_COUNTS:
        fail("the overlay gives precinct counts %s, but %s prints %s — the county's "
             "two layers no longer agree with its own returns, and a human must "
             "re-measure before this county ships again"
             % (counts, CERTIFIED_SOURCE, CERTIFIED_PRECINCT_COUNTS))

    # ---- tiling ------------------------------------------------------------
    lat = county_geom.centroid.y
    mx, my = 111320.0 * math.cos(math.radians(lat)), 110574.0
    area = lambda g: transform(lambda x, y, z=None: (x * mx, y * my), g).area  # noqa: E731
    keys = sorted(districts, key=int)
    overlap = 0.0
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            overlap += area(districts[a].intersection(districts[b]))
    if overlap > MAX_OVERLAP_M2:
        fail("the county's districts overlap by %.0f m2 (ceiling %.0f)"
             % (overlap, MAX_OVERLAP_M2))
    union = unary_union(list(districts.values()))
    outside = area(union.difference(county_geom))
    if outside > MAX_OUTSIDE_M2:
        fail("the districts spill %.0f m2 outside the county line (ceiling %.0f)"
             % (outside, MAX_OUTSIDE_M2))
    covered = area(union.intersection(county_geom)) / area(county_geom)
    if covered < MIN_COVERED:
        fail("the districts cover only %.4f%% of the county" % (100 * covered))

    ideal = county_pop / float(EXPECTED_DISTRICTS)
    worst = max(((abs(pops[d] - ideal) / ideal), d) for d in pops)
    if worst[0] > BALANCE_DEV_MAX:
        fail("district %s deviates %.1f%% from the per-district ideal (ceiling %.0f%%)"
             % (worst[1], 100 * worst[0], 100 * BALANCE_DEV_MAX))

    # ---- output ------------------------------------------------------------
    precinct_features = []
    for key in sorted(vtds, key=lambda k: vtds[k]["basename"]):
        rec = vtds[key]
        props = {"name": V.title_case(rec["basename"]), "geoid": rec["geoid"],
                 "pop2020": rec["pop"]}
        if key in split_of:
            props["districts"] = split_of[key]
        else:
            props["district"] = where[key]
        precinct_features.append({"type": "Feature", "properties": props,
                                  "geometry": V.round_geom(rec["geom"], mapping)})
    precincts_payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL, "electionsUrl": ELECTIONS_URL,
            "note": ("Douglas County's 17 precincts are the Census 2020 voting "
                     "districts, which carry the county's own 17 precinct names "
                     "17/17 — matched against the county's own VotingDistricts "
                     "service — and sum to its exact 2020 population of 19,740. "
                     "Most features carry their County Board district; TWO carry "
                     "a list of two instead. Bourbon 2 and Bowdre are SPLIT "
                     "between districts, which the county states twice over: its "
                     "own district layer cuts through them, and its certified "
                     "2022 General counts 19 precinct-slots across seven "
                     "districts in a county of seventeen precincts. For those two "
                     "the precinct does not determine the district and the card "
                     "says so. No polling place ships: a polling place is a "
                     "roster fact rather than geometry."),
        },
        "features": precinct_features,
    }

    district_features = []
    for dnum in keys:
        whole = sorted((V.title_case(vtds[k]["basename"]) for k in where if where[k] == dnum))
        partial = sorted((V.title_case(vtds[k]["basename"]) for k in split_of
                          if dnum in split_of[k]))
        district_features.append({
            "type": "Feature",
            "properties": {"district": dnum, "name": "District %s" % dnum,
                           "precincts": whole, "partialPrecincts": partial,
                           "pop2020": pops[dnum], "seats": SEATS_PER_DISTRICT},
            "geometry": V.round_geom(districts[dnum], mapping),
        })
    districts_payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL, "gisUrl": GIS_URL, "electionsUrl": ELECTIONS_URL,
            "canvass": ("The boundaries are the county's own, published as a public "
                        "feature service by its GIS and shipped as drawn — no "
                        "dissolve, no map to interpret. They are checked against a "
                        "different county product: %s ran all seven districts and "
                        "printed the number of precincts voting in each (2, 2, 3, "
                        "2, 3, 2, 5 — nineteen across a county of seventeen, "
                        "because two precincts are split), and overlaying the "
                        "county's precinct layer on its district layer reproduces "
                        "all seven exactly, including both splits."
                        % CERTIFIED_SOURCE),
            "note": ("Seven single-member districts. Population comes from the "
                     "county layer's own TOTAL_POP field, which sums to the exact "
                     "Census 2020 county count of 19,740 and runs 2,504-3,230 "
                     "against a 2,820 ideal. Bourbon 2 and Bowdre lie in two "
                     "districts each and are named separately from the precincts "
                     "wholly inside, because a reader in one of them is not "
                     "wholly in this district."),
        },
        "features": district_features,
    }

    prec_body = V.dumps(precincts_payload)
    dist_body = V.dumps(districts_payload)
    print("douglas-boundaries: %d precincts and %d single-member districts "
          "(%d whole precincts + %d split between two districts each)"
          % (len(precinct_features), len(district_features), len(where), len(split_of)))
    print("  populations: %s (total %d = census POP100; worst deviation %.1f%% in "
          "district %s)"
          % (", ".join("D%s=%d" % (d, pops[d]) for d in keys), county_pop,
             100 * worst[0], worst[1]))
    print("  certified precinct counts confirmed: %s"
          % ", ".join("D%s=%d" % (d, CERTIFIED_PRECINCT_COUNTS[d]) for d in keys))
    print("  splits: %s"
          % "; ".join("%s -> D%s" % (V.title_case(vtds[k]["basename"]), "/D".join(v))
                      for k, v in sorted(split_of.items())))
    print("  tiling: overlap %.0f m2; %.0f m2 outside the county; %.4f%% covered"
          % (overlap, outside, 100 * covered))
    V.write_or_check([(OUT_PRECINCTS, prec_body), (OUT_DISTRICTS, dist_body)],
                     args.check, REPO_ROOT, fail, "douglas")


if __name__ == "__main__":
    main()
