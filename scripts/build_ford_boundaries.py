#!/usr/bin/env python3
"""
Build il/data/app/ford-county-board-districts.json — Ford County's three
County Board districts (12 members, four per district on staggered terms;
docs/EXPANSION_GUIDE.md Part 3; scripts/vtd_board_districts.py holds the
machinery).

THE PLAN IN FORCE IS RESOLUTION 21-101, and this county's gap record spent two
months unable to say so. Res. 21-59 (2021) adopted a twelve-member board of
three districts and listed each as "To be determined", because the census data
had not arrived by the statutory deadline. Res. 21-101, "Amending Resolution No.
21-59 — adopting the 2021 reapportionment plan following the 2020 federal
decennial census", fills them in. It is on the county's own server
(fordcounty.illinois.gov/wp-content/uploads/2021/11/, read 2026-10-15 with this
project's token; robots.txt permits the path) and its Exhibit A, effective the
first Monday in December 2022, reads:

    District 1 - Patton 1, 2, 3, 5, 6, 7 and Button Townships
    District 2 - Rogers, Mona, Pella, Brenton, Lyman, Wall, Peach Orchard,
                 Sullivant, Patton 4 Townships
    District 3 - Drummer 1, 2, 3, 4, 5 and Dix Townships

"Townships" there means the county's precincts, which are named for them; the
county's 22 precincts are the 22 Census 2020 voting districts, name for name,
summing to its exact 2020 population of 13,534 (check_fabric below).

THREE WITNESSES IN THE SAME RESOLUTION AGREE, and they are of different kinds:

  * THE TEXT above, which names every precinct once.
  * ITS POPULATION TABLE ("Ford County Board Redistricting Based on 2020
    Federal Decennial Census"), which prints each precinct's 2020 count and
    each proposed district's total: 4,640 / 4,250 / 4,644. Every one of the 22
    precinct figures equals the census POP100 of the same-named voting
    district (PLAN_PRECINCT_POP, checked to the person), and the dissolve
    reproduces all three district totals (PLAN_POP).
  * ITS MAP, a coloured raster: Patton 3's 193 people are shaded District 1,
    Patton 4's 845 District 2, and the Drummer and Dix block District 3.

PATTON 3 IS WHOLLY DISTRICT 1, and that settles the question this county was
recorded shut on. The county's board page lists Patton 3 under both Districts 1
and 3, and the county's certified 2026 General Primary carries a Patton 3 ballot
style in the District 3 contest too. The adopted plan does not: its text puts
Patton 3 in District 1 alone, its table assigns all 193 of Patton 3's people to
District 1, and its map shades it District 1. What the District 3 ballot style
covers is NOT ESTABLISHED. It may be a style with no voters, or a piece of
Patton Township the precinct map does not show; nothing published says, and it
is not guessed at. The polygon follows the adopted plan, and the card says the
precinct is listed under District 3 as well.

THE ROSTER AGREES WITH THE PLAN'S SHAPE: the County Clerk's letter of
2026-10-01 names twelve members, four per district (build_ford_county_board.py).

THIS IS A RARE OPERATOR STEP (requests + shapely). Re-run only if Ford
reapportions, re-precincts, or TIGERweb republishes the VTD fabric. Output is
deterministic, so --check is a byte compare.

Usage:
    python3 scripts/build_ford_boundaries.py [--check]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_metro_outline import point_in_rings  # noqa: E402
import vtd_board_districts as V  # noqa: E402
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DISTRICTS = os.path.join(REPO_ROOT, "il", "data", "app",
                             "ford-county-board-districts.json")

COUNTY_FIPS = "053"
COUNTY_POP_2020 = 13534
EXPECTED_PRECINCTS = 22
SEATS_PER_DISTRICT = 4          # twelve members, four per district, staggered

PLAN_URL = ("https://fordcounty.illinois.gov/wp-content/uploads/2021/11/"
            "RES-21-101-AMEND-RES-21-59-ADOPT-REAPOR-PLAN-AND-MAPS.pdf")
BOARD_URL = "https://fordcounty.illinois.gov/ford-county-board/"

SOURCE_LABEL = ("Census 2020 voting districts dissolved per Ford County "
                "Resolution 21-101, the county's 2021 reapportionment plan "
                "(Exhibit A, effective December 2022)")

# THE COMPOSITION, exactly as Exhibit A of Res. 21-101 lists it.
COMPOSITION = {
    "1": ("PATTON 1", "PATTON 2", "PATTON 3", "PATTON 5", "PATTON 6",
          "PATTON 7", "BUTTON"),
    "2": ("ROGERS", "MONA", "PELLA", "BRENTON", "LYMAN", "WALL",
          "PEACH ORCHARD", "SULLIVANT", "PATTON 4"),
    "3": ("DRUMMER 1", "DRUMMER 2", "DRUMMER 3", "DRUMMER 4", "DRUMMER 5", "DIX"),
}

# The county's current precinct list: the Exhibit A names, which its certified
# 2026 General Primary returns also carry, 22 of 22.
COUNTY_PRECINCTS = tuple(n for names in COMPOSITION.values() for n in names)

# The resolution's own population table, "2020 CENSUS" column, per precinct.
PLAN_PRECINCT_POP = {
    "ROGERS": 381, "MONA": 267, "PELLA": 160, "BRENTON": 861, "LYMAN": 516,
    "WALL": 190, "PEACH ORCHARD": 551, "SULLIVANT": 479,
    "DRUMMER 1": 645, "DRUMMER 2": 625, "DRUMMER 3": 918, "DRUMMER 4": 1017,
    "DRUMMER 5": 841, "DIX": 598,
    "PATTON 1": 723, "PATTON 2": 622, "PATTON 3": 193, "PATTON 4": 845,
    "PATTON 5": 760, "PATTON 6": 907, "PATTON 7": 1203, "BUTTON": 232,
}
# The same table's "PROPOSED 2021" district totals.
PLAN_POP = {"1": 4640, "2": 4250, "3": 4644}

# A mis-assignment moves a whole precinct; Ford's smallest is 160 people, and
# the plan itself measures 5.8% (District 2).
BALANCE_DEV_MAX = 0.30
MAX_OVERLAP_M2 = 1.0
MIN_COVERED = 0.9999

fail = make_fail("ford-boundaries")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file matches a fresh build")
    args = ap.parse_args()

    from shapely.geometry import shape, mapping     # noqa: E402  (heavy, function-local)
    from shapely.ops import unary_union, transform  # noqa: E402

    if len(COUNTY_PRECINCTS) != EXPECTED_PRECINCTS:
        fail("the composition names %d precincts, expected %d"
             % (len(COUNTY_PRECINCTS), EXPECTED_PRECINCTS))
    if set(PLAN_PRECINCT_POP) != set(COUNTY_PRECINCTS):
        fail("the plan's population table and its Exhibit A name different "
             "precincts")
    for dnum, total in PLAN_POP.items():
        got = sum(PLAN_PRECINCT_POP[n] for n in COMPOSITION[dnum])
        if got != total:
            fail("the plan's table gives District %s %d people and its precinct "
                 "rows for that district sum to %d — the table was misread"
                 % (dnum, total, got))

    vtds = V.fetch_vtds(COUNTY_FIPS, shape, fail)
    if len(vtds) != EXPECTED_PRECINCTS:
        fail("the census voting-district layer carries %d Ford features, "
             "expected %d" % (len(vtds), EXPECTED_PRECINCTS))
    county_geom, county_pop = V.fetch_county(COUNTY_FIPS, shape, fail)
    if county_pop != COUNTY_POP_2020:
        fail("census county population is %d, expected %d"
             % (county_pop, COUNTY_POP_2020))

    V.check_fabric(vtds, COUNTY_PRECINCTS, county_pop, fail)
    for name, want in sorted(PLAN_PRECINCT_POP.items()):
        got = vtds[V.norm(name)]["pop"]
        if got != want:
            fail("the census gives %s %d people and Res. 21-101's table %d — "
                 "the plan was not drawn on this fabric" % (name, got, want))
    where = V.check_partition(COMPOSITION, vtds, fail)

    districts, pops = V.dissolve(COMPOSITION, vtds, unary_union)
    for dnum in sorted(PLAN_POP):
        if pops[dnum] != PLAN_POP[dnum]:
            fail("district %s dissolves to %d people; Res. 21-101 prints %d"
                 % (dnum, pops[dnum], PLAN_POP[dnum]))
    ideal = county_pop / float(len(COMPOSITION))
    worst = max(((abs(pops[d] - ideal) / ideal), d) for d in pops)
    if worst[0] > BALANCE_DEV_MAX:
        fail("district %s deviates %.1f%% from the per-district ideal (ceiling "
             "%.0f%%) — that is a mis-assignment, not an apportionment"
             % (worst[1], 100 * worst[0], 100 * BALANCE_DEV_MAX))
    overlap, covered = V.check_tiling(districts, county_geom, transform,
                                      MAX_OVERLAP_M2, MIN_COVERED, unary_union, fail)

    district_features = []
    for dnum in sorted(COMPOSITION, key=int):
        district_features.append({
            "type": "Feature",
            "properties": {"district": dnum, "name": "District %s" % dnum,
                           "precincts": [V.title_case(n) for n in COMPOSITION[dnum]],
                           "pop2020": pops[dnum], "seats": SEATS_PER_DISTRICT},
            "geometry": V.round_geom(districts[dnum], mapping),
        })
    payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL, "planUrl": PLAN_URL, "boardUrl": BOARD_URL,
            "canvass": ("Composition from Exhibit A of Ford County Resolution "
                        "21-101. The same resolution's population table gives "
                        "every precinct's 2020 count, all 22 equal to the census, "
                        "and district totals of 4,640 / 4,250 / 4,644, which this "
                        "dissolve reproduces exactly; its map shades the same "
                        "precincts the same way."),
            "note": ("Three districts electing FOUR members each (12 seats) on "
                     "staggered terms, effective December 2022. Patton 3 is "
                     "drawn wholly in District 1, as the plan's text, table and "
                     "map all place it. The county's board page also lists "
                     "Patton 3 under District 3, and its 2026 primary carried a "
                     "Patton 3 ballot style in the District 3 contest; what that "
                     "covers is not published."),
        },
        "features": district_features,
    }

    V.verify_point_in_rings(COMPOSITION, vtds, district_features, point_in_rings, fail)

    print("ford-boundaries: %d census voting districts -> %d board districts of "
          "%d seats" % (EXPECTED_PRECINCTS, len(COMPOSITION), SEATS_PER_DISTRICT))
    print("  populations: %s (total %d = census POP100) — every precinct and all "
          "three districts match Res. 21-101's own table; worst deviation %.1f%% "
          "in district %s"
          % (", ".join("D%s=%d" % (d, pops[d]) for d in sorted(pops, key=int)),
             county_pop, 100 * worst[0], worst[1]))
    print("  tiling: overlap %.2f m2; %.4f%% of the county covered"
          % (overlap, 100 * covered))
    print("  Patton 3 drawn in District 1 only, per the plan; the county also "
          "lists it under District 3, which nothing published explains")
    V.write_or_check([(OUT_DISTRICTS, V.dumps(payload))],
                     args.check, REPO_ROOT, fail, "ford")


if __name__ == "__main__":
    main()
