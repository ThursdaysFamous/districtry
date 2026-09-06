#!/usr/bin/env python3
"""Build Marshall County's fourteen voting precincts from Census 2020 voting districts.

FOUND BY AUDITING GAP RECORDS BY DATE, not by probing Marshall. Its record
(`marshall-precinct-geometry`) was last measured 3 Aug 2026 — a fortnight before
this project found the election-results vendors, and three weeks before it
learned to test one by CONTENT. A record whose newest measurement predates a
route is a hypothesis about a route that did not exist, and 24 of Illinois's 100
gap records are in that position; sweeping the nine county-precinct ones found
four counties a vendor carries, of which this is the cleanest.

THE CANVASS NAMES EVERY PRECINCT. il-marshall.pollresults.net is the Clerk's own
results site — the AngularJS shell whose entire result set is embedded in the
page as JSON, the shape build_clark_boundaries.py documents — 165,199 bytes with
a unique md5 against the vendor's 7,720-byte generic shell, which is what
il-zzzfakecounty and il-notarealcounty return. THE FABRICATED-COUNTY CONTROL IS
THE TEST, never the status code: this vendor answers 200 for counties it does
not carry.

THE JASPER TEST PASSES 14/14 WITH NO ALIAS AT ALL — the cleanest of the four —
and the fourteen POP100 values sum to Marshall's own 2020 population of 11,742
to the person. No dissolve is needed and none is performed.

NO BOARD DISTRICT SHIPS HERE. Marshall's board districts are a separate concern
and this file is precincts only; a `district` property would invent a join this
build has not made.

NO POLLING PLACE SHIPS. A polling place belongs with a roster guard and a date
rather than inside a geometry file — the rule Calhoun's build set.

THIS IS A RARE OPERATOR STEP (requests + shapely). Re-run only if Marshall
re-precincts or TIGERweb republishes the voting-district fabric. Output is
deterministic, so --check is a byte compare.

Usage:
    python3 scripts/build_marshall_precincts.py            # write
    python3 scripts/build_marshall_precincts.py --check    # verify shipped == fresh
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtd_board_districts as V  # noqa: E402
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PRECINCTS = os.path.join(REPO_ROOT, "il", "data", "app", "marshall-precincts.json")

COUNTY_FIPS = "123"
COUNTY_POP_2020 = 11742
EXPECTED_PRECINCTS = 14

RESULTS_URL = "https://il-marshall.pollresults.net/"
SOURCE_LABEL = ("Census 2020 voting districts, one per precinct, carrying the "
                "fourteen precinct names Marshall County's own certified "
                "canvasses use")

COUNTY_PRECINCTS = (
    "BELL PLAIN", "BENNINGTON", "EVANS", "HENRY 1", "HENRY 2", "HOPEWELL",
    "LA PRAIRIE", "LACON 1", "LACON 2", "RICHLAND", "ROBERTS", "SARATOGA",
    "STEUBEN", "WHITEFIELD",
)

# NONE. The county's certified returns and the census fabric agree on all
# fourteen names exactly, which is why this county is the cleanest of the four
# the date audit turned up.
ALIASES = {}

MAX_OVERLAP_M2 = 1.0
MIN_COVERED = 0.9999


fail = make_fail("marshall-precincts")



def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file matches a fresh build")
    args = ap.parse_args()

    from shapely.geometry import shape, mapping   # noqa: E402  (heavy, function-local)
    from shapely.ops import unary_union, transform  # noqa: E402

    if len(COUNTY_PRECINCTS) != EXPECTED_PRECINCTS:
        fail("the precinct list names %d precincts, expected %d"
             % (len(COUNTY_PRECINCTS), EXPECTED_PRECINCTS))

    vtds = V.fetch_vtds(COUNTY_FIPS, shape, fail)
    county_geom, county_pop = V.fetch_county(COUNTY_FIPS, shape, fail)
    if county_pop != COUNTY_POP_2020:
        fail("census county population is %d, expected %d"
             % (county_pop, COUNTY_POP_2020))
    if ALIASES:
        V.apply_aliases(vtds, ALIASES, fail)

    # The Jasper test proper: names one-for-one AND the population identity.
    V.check_fabric(vtds, COUNTY_PRECINCTS, county_pop, fail)

    # One voting district per precinct. check_partition still runs, because it is
    # what proves nothing is claimed twice and nothing is left over — the guard
    # that would catch a future re-precincting that kept the same count.
    composition = {V.title_case(p): [p] for p in COUNTY_PRECINCTS}
    V.check_partition(composition, vtds, fail)

    precincts, pops = V.dissolve(composition, vtds, unary_union)
    overlap, covered = V.check_tiling(precincts, county_geom, transform,
                                      MAX_OVERLAP_M2, MIN_COVERED, unary_union, fail)

    features = []
    for name in sorted(composition):
        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "pop2020": pops[name],
            },
            "geometry": V.round_geom(precincts[name], mapping),
        })

    payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL,
            "resultsUrl": RESULTS_URL,
            "note": ("Marshall County's fourteen voting precincts. The Census 2020 "
                     "voting districts carry the county's own fourteen precinct "
                     "names ONE FOR ONE WITH NO ALIAS AT ALL and sum to its exact "
                     "2020 population of 11,742, so the fabric is the county's and "
                     "nothing is dissolved. The names come from the Clerk's own "
                     "certified canvasses at il-marshall.pollresults.net. No board "
                     "district is carried: this file is precincts only, and a "
                     "district property would invent a join this build has not "
                     "made. No polling place is carried either — that belongs "
                     "with a roster guard rather than in a geometry file."),
        },
        "features": features,
    }

    body = V.dumps(payload)
    print("marshall-precincts: %d voting districts -> %d precincts (pop %d = census "
          "POP100)" % (len(vtds), len(composition), county_pop))
    print("  %s" % ", ".join("%s=%d" % (n, pops[n]) for n in sorted(pops)))
    print("  tiling: overlap %.2f m2; %.4f%% of the county covered"
          % (overlap, 100 * covered))
    V.write_or_check([(OUT_PRECINCTS, body)], args.check, REPO_ROOT, fail, "marshall")


if __name__ == "__main__":
    main()
