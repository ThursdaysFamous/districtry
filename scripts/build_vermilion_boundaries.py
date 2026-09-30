#!/usr/bin/env python3
"""
Build data/app/vermilion-county-board-districts.json — Vermilion County's 9
County Board districts, shipped as the county's own GIS draws them.

VERMILION WAS NEVER BLOCKED. Its gap record said the county's website "is not
reachable from this project's network", and that sentence was true of a TLS
handshake and false of the county. vercountyil.gov redirects to
www.vercounty.org, which serves the COLES PATTERN — its leaf certificate
without the GoGetSSL intermediate, so every automated client reports a failure
no browser ever sees. Supplying that intermediate by AIA (pinned by hash, in
vermilion_county_board_scraper.py — never by disabling verification) opens the
whole site: a maintained 27-member board roster, and two authorities' certified
returns going back to 2010.

The boundaries did not even need the site. The county's GIS publishes to
ArcGIS Online under the DanvilleILGIS org (services6.arcgis.com/am689ZyfXfdo9vCK),
which carries twenty-six public services, and A VIEWER SHOWS WHAT IT USES WHILE
THE ORG SHOWS WHAT THE COUNTY HAS. Three of them draw board districts:

    Districts/FeatureServer/3    "Board Districts", inside a service described
                                 as "Governmental and school districts in
                                 Vermilion County IL"
    CountyBoardDistricts/0       the same geometry, plus Name/Party/Elected/
                                 Email columns for three members apiece
    CountyBoardDistrcts2021/0    no description, no metadata, a typo in its
                                 own name

THE WELL-LABELLED LAYER IS THE OBSOLETE ONE. Districts/3 and CountyBoardDistricts
are the same polygons to six decimal places of IoU, and that roster's newest
Elected year is 2018 on e-mail addresses the county no longer uses — the Coles
shape, a roster riding a boundary and going stale on it. The misspelled,
undocumented CountyBoardDistrcts2021 is materially different (IoU 0.13 against
Districts/3 in District 8, 0.28 in District 9).

WHICH IS CURRENT IS A MEASUREMENT, NOT A READING OF ITS NAME, and it is a GATE
below rather than a sentence here. Assigning all 4,943 Census 2020 blocks by
centroid:

    CountyBoardDistrcts2021   8,209 - 8,298 against an 8,243 ideal   worst 0.7%
    Districts/3               7,609 - 9,484                          worst 15.1%

A plan drawn to the 2020 census balances on the 2020 census. One of these was
and one was not, and the builder refuses to write unless that stays true in both
directions.

THREE INDEPENDENT WITNESSES, none of them the layer checking itself:

  * Both authorities' certified returns name all nine districts. Vermilion has
    TWO election authorities — the County Clerk outside the City of Danville and
    the Danville Election Commission inside it — and THEY USE DIFFERENT CONTEST
    NAMES. The clerk spells them out ("COUNTY BOARD 8TH DISTRICT MEMBER"); the
    commission abbreviates ("CO. BD. MEMBER D8"). Reading only the clerk's
    convention finds districts 1-8 across four certified canvasses and reports
    DISTRICT 9 AS NOT EXISTING; it is in the commission's 2026 General Primary,
    "CO.BD.MEMBER D9 (VOTE FOR) 2 (WITH 4 OF 4 PRECINCTS COUNTED)".
  * The nine tile the county: 99.98% covered, with pairwise overlap and outside
    spill both digitisation noise between independently drawn products.
  * Every one of the county's 74,188 residents lands in exactly one district.

NO PRECINCT LAYER SHIPS, and that is a measured refusal rather than an omission.
The org's "Voting Precincts" layer carries 84 features matching the Census 2020
fabric 84/84 — which is precisely the problem: Vermilion re-precincted after the
2020 census, and its own certified canvasses have reported 38 clerk precincts
and 22 commission precincts since June 2022. The GIS layer is the 2020 fabric,
sixty current precincts drawn as eighty-four superseded ones. The org's
"VoterCodes" layer (79 features named C51, C72, CITY) is not a precinct layer at
all and splits across district lines everywhere; it is named here so nobody
mistakes it for one later.

THIS IS A RARE OPERATOR STEP (requests + shapely). Re-run if Vermilion
reapportions. Output is deterministic, so --check is a byte compare.

Usage:
    python3 scripts/build_vermilion_boundaries.py [--check]
"""

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtd_board_districts as V  # noqa: E402
from scraper_common import require_robots_once, make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DISTRICTS = os.path.join(REPO_ROOT, "il", "data", "app",
                             "vermilion-county-board-districts.json")

COUNTY_FIPS = "183"
COUNTY_POP_2020 = 74188
EXPECTED_DISTRICTS = 9
SEATS_PER_DISTRICT = 3          # 27 members, three per district, staggered

ORG = "https://services6.arcgis.com/am689ZyfXfdo9vCK/arcgis/rest/services"
DISTRICT_SERVICE = ORG + "/CountyBoardDistrcts2021/FeatureServer/0/query"
LEGACY_SERVICE = ORG + "/Districts/FeatureServer/3/query"
BLOCK_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
             "tigerWMS_Census2020/MapServer/10/query")

BOARD_URL = "https://www.vercounty.org/county-board/county-board-members/"
ELECTIONS_URL = "https://www.vercounty.org/county-clerk/election-results/"
COMMISSION_URL = ("https://www.vercounty.org/election-commission/"
                  "election-results-information/")

SOURCE_LABEL = ("Vermilion County's own County Board district boundaries, "
                "published as a public feature service by the county's GIS "
                "(services6.arcgis.com/am689ZyfXfdo9vCK), with population from "
                "the Census 2020 block file")

# THE CURRENCY GATE. The county publishes two board-district maps and only one
# was drawn to the 2020 census. This build refuses to write unless the layer it
# ships is inside the tight ceiling AND the superseded one is outside it —
# because if the legacy layer ever balances too, the county has redistricted and
# a human must work out which map is now in force.
CURRENT_DEV_MAX = 0.05          # measured 0.007
LEGACY_DEV_MIN = 0.10           # measured 0.151

MAX_OVERLAP_M2 = 150000.0       # measured 27,349 across all 36 pairs
MAX_OUTSIDE_M2 = 1500000.0      # measured 484,861 — 0.02% of the county
MIN_COVERED = 0.999


fail = make_fail("vermilion-boundaries")


def fetch_service(url, shape_fn, key_fn):
    """The county's own districts, keyed by district number."""
    import requests
    require_robots_once(url, V.HEADERS["User-Agent"], headers=V.HEADERS,
                        label="il-build-vermilion-boundaries")
    resp = requests.get(url, headers=V.HEADERS, timeout=V.REQUEST_TIMEOUT,
                        params={"where": "1=1", "outFields": "*",
                                "returnGeometry": "true", "outSR": "4326",
                                "f": "geojson"})
    resp.raise_for_status()
    out = {}
    for feature in resp.json().get("features") or []:
        geom = shape_fn(feature["geometry"])
        if not geom.is_valid:
            geom = geom.buffer(0)
        key = key_fn(feature["properties"])
        if key in out:
            fail("%s returned district %s twice" % (url, key))
        out[key] = geom
    return out


def fetch_blocks():
    """Census 2020 blocks, ordered by GEOID.

    Blocks need orderByFields for paging — without it the service silently
    returns an empty page rather than an error, which reads as "this county has
    no blocks" instead of "ask again".
    """
    import requests
    blocks, offset = [], 0
    while True:
        require_robots_once(BLOCK_URL, V.HEADERS["User-Agent"], headers=V.HEADERS,
                            label="il-build-vermilion-boundaries")
        resp = requests.get(BLOCK_URL, headers=V.HEADERS,
                            timeout=V.REQUEST_TIMEOUT, params={
                                "where": "STATE='17' AND COUNTY='%s'" % COUNTY_FIPS,
                                "outFields": "GEOID,POP100,CENTLAT,CENTLON",
                                "returnGeometry": "false",
                                "orderByFields": "GEOID",
                                "resultOffset": offset,
                                "resultRecordCount": 2000, "f": "json"})
        resp.raise_for_status()
        page = resp.json().get("features") or []
        if not page:
            break
        blocks.extend(f["attributes"] for f in page)
        offset += len(page)
        if len(page) < 2000:
            break
    if not blocks:
        fail("the Census 2020 block service returned nothing for Vermilion")
    return blocks


def populations(districts, blocks, point_cls, tree_cls):
    """Assign every block's people to the district holding its centroid."""
    keys = sorted(districts, key=int)
    geoms = [districts[k] for k in keys]
    tree = tree_cls(geoms)
    pops = dict((k, 0) for k in keys)
    unplaced = 0
    for block in blocks:
        pop = int(block["POP100"] or 0)
        if not pop:
            continue
        point = point_cls(float(block["CENTLON"]), float(block["CENTLAT"]))
        placed = False
        for idx in tree.query(point):
            if geoms[idx].contains(point):
                pops[keys[idx]] += pop
                placed = True
                break
        if not placed:
            unplaced += pop
    return pops, unplaced


def worst_deviation(pops):
    ideal = sum(pops.values()) / float(len(pops))
    return max(((abs(pops[d] - ideal) / ideal), d) for d in pops)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file matches a fresh build")
    args = ap.parse_args()

    from shapely.geometry import shape, mapping, Point  # noqa: E402 (heavy)
    from shapely.ops import unary_union, transform      # noqa: E402
    from shapely.strtree import STRtree                 # noqa: E402

    county_geom, county_pop = V.fetch_county(COUNTY_FIPS, shape, fail)
    if county_pop != COUNTY_POP_2020:
        fail("census county population is %d, expected %d"
             % (county_pop, COUNTY_POP_2020))

    districts = fetch_service(DISTRICT_SERVICE, shape,
                              lambda p: str(p.get("District")).strip())
    if len(districts) != EXPECTED_DISTRICTS:
        fail("the county's CountyBoardDistrcts2021 service returned %d features, "
             "expected %d" % (len(districts), EXPECTED_DISTRICTS))
    keys = sorted(districts, key=int)
    if keys != [str(i) for i in range(1, EXPECTED_DISTRICTS + 1)]:
        fail("the districts are keyed %s, expected 1-%d"
             % (keys, EXPECTED_DISTRICTS))

    blocks = fetch_blocks()
    block_total = sum(int(b["POP100"] or 0) for b in blocks)
    if block_total != county_pop:
        fail("the Census 2020 blocks sum to %d and the county to %d"
             % (block_total, county_pop))

    pops, unplaced = populations(districts, blocks, Point, STRtree)
    if unplaced:
        fail("%d people fall in none of the county's nine districts — the layer "
             "no longer covers the county" % unplaced)
    worst = worst_deviation(pops)
    if worst[0] > CURRENT_DEV_MAX:
        fail("district %s deviates %.1f%% from the per-district ideal (ceiling "
             "%.0f%%) — the shipped layer no longer looks like a plan drawn to "
             "the 2020 census" % (worst[1], 100 * worst[0], 100 * CURRENT_DEV_MAX))

    # ---- the currency gate -------------------------------------------------
    # The county publishes a second, better-labelled board-district map. It is
    # the SUPERSEDED one, and the only thing that says so is its population
    # balance. Measure it every run: if it ever comes into balance, Vermilion has
    # redistricted onto it and a human must decide which map is in force.
    legacy = fetch_service(
        LEGACY_SERVICE, shape,
        lambda p: str(p.get("District_Number") or "").strip().split()[-1])
    if len(legacy) != EXPECTED_DISTRICTS:
        fail("the county's legacy Districts/3 layer returned %d features, "
             "expected %d" % (len(legacy), EXPECTED_DISTRICTS))
    legacy_pops, legacy_unplaced = populations(legacy, blocks, Point, STRtree)
    legacy_worst = worst_deviation(legacy_pops)
    if legacy_unplaced == 0 and legacy_worst[0] < LEGACY_DEV_MIN:
        fail("the county's OTHER board-district layer (Districts/3) now balances "
             "to %.1f%% on the 2020 census, where it measured 15.1%% when this "
             "build was written. Two layers cannot both be the current plan — "
             "re-read which one the county has adopted before shipping again."
             % (100 * legacy_worst[0]))

    # ---- tiling ------------------------------------------------------------
    lat = county_geom.centroid.y
    mx, my = 111320.0 * math.cos(math.radians(lat)), 110574.0
    area = lambda g: transform(lambda x, y, z=None: (x * mx, y * my), g).area  # noqa: E731
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

    # ---- output ------------------------------------------------------------
    features = []
    for dnum in keys:
        features.append({
            "type": "Feature",
            "properties": {"district": dnum, "name": "District %s" % dnum,
                           "pop2020": pops[dnum], "seats": SEATS_PER_DISTRICT},
            "geometry": V.round_geom(districts[dnum], mapping),
        })
    payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL,
            "boardUrl": BOARD_URL,
            "electionsUrl": ELECTIONS_URL,
            "commissionUrl": COMMISSION_URL,
            "canvass": (
                "Vermilion has TWO election authorities and they name the same "
                "contests differently: the County Clerk, outside the City of "
                "Danville, spells them out (\"COUNTY BOARD 8TH DISTRICT "
                "MEMBER\"), and the Danville Election Commission, inside it, "
                "abbreviates (\"CO. BD. MEMBER D8\"). Between them their "
                "certified returns name all nine districts — districts 1-8 in "
                "four of the clerk's canvasses from 2022 on, and District 9 in "
                "the commission's 17 March 2026 General Primary."),
            "note": (
                "Nine districts of three members each, 27 in all, on staggered "
                "terms. The boundaries are the county's own, published as a "
                "public feature service by its GIS and shipped as drawn — no "
                "dissolve and no map to interpret. The county publishes a second, "
                "better-labelled board-district map which is SUPERSEDED: this one "
                "runs 8,209-8,298 against an 8,243 ideal on the Census 2020 "
                "blocks, a worst deviation of 0.7%, where the other runs "
                "7,609-9,484 and 15.1%. No precinct layer ships for Vermilion: "
                "the county re-precincted after the 2020 census, and the "
                "precinct layer its GIS publishes is the superseded 84-precinct "
                "fabric rather than the 38 clerk and 22 commission precincts its "
                "own canvasses have reported since 2022."),
        },
        "features": features,
    }

    body = V.dumps(payload)
    print("vermilion-boundaries: %d districts of %d members each (%d seats)"
          % (len(features), SEATS_PER_DISTRICT,
             len(features) * SEATS_PER_DISTRICT))
    print("  populations: %s (total %d = census POP100; worst deviation %.2f%% "
          "in district %s)"
          % (", ".join("D%s=%d" % (d, pops[d]) for d in keys), county_pop,
             100 * worst[0], worst[1]))
    print("  currency gate: the superseded Districts/3 layer measures %.1f%% "
          "(floor %.0f%%), so it is still the older plan"
          % (100 * legacy_worst[0], 100 * LEGACY_DEV_MIN))
    print("  tiling: overlap %.0f m2; %.0f m2 outside the county; %.4f%% covered"
          % (overlap, outside, 100 * covered))
    V.write_or_check([(OUT_DISTRICTS, body)], args.check, REPO_ROOT, fail,
                     "vermilion")


if __name__ == "__main__":
    main()
