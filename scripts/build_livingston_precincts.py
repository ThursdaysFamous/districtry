#!/usr/bin/env python3
"""Build Livingston County's forty-six voting precincts from Census 2020 voting districts.

FOUND BY AUDITING GAP RECORDS BY DATE. Its record (`livingston-precincts`) was
last measured 31 Jul 2026 and said "the county publishes no mapping data at
all" — still true, and no longer the question. That measurement predates this
project's discovery of the election-results vendors by nearly three weeks; a
record whose newest measurement predates a route is a hypothesis about a route
that did not exist.

THE CANVASS NAMES EVERY PRECINCT. il-livingston.pollresults.net is the Clerk's
own results site, 302,663 bytes with a unique md5 against the vendor's
7,720-byte generic shell — the body il-zzzfakecounty and il-notarealcounty both
return. THE FABRICATED-COUNTY CONTROL IS THE TEST, never the status code.

THE JASPER TEST PASSES 46/46 after ONE alias, and the forty-six POP100 values
sum to Livingston's own 2020 population of 35,815 to the person.

FIVE NAMES DIFFER BETWEEN THE TWO PUBLISHERS AND THEY RESOLVE IN OPPOSITE
DIRECTIONS, which is the whole reason they are decided one at a time rather than
aliased in a batch:

  * INDIAN GRV 1-4 (canvass) against INDIAN GROVE 1-4 (census). The census's own
    county-subdivision layer names the township INDIAN GROVE, so "Grv" is the
    results feed ABBREVIATING a name, not the county spelling it differently.
    The CENSUS WINS and no alias is needed — this file simply declares the four
    census names, which is the Scott precedent (MERRIT against MERRITT, where
    the dropped letter was the feed's and Merritt is the township).
  * CHATSWORTH 1 (canvass) against CHATSWORTH (census). Here the county ATTACHES
    A NUMBER the census leaves off, exactly as Greene does with WRIGHTS 2 and
    Putnam with HENNEPIN 1. A number the county puts on its own ballot is the
    county's designation, so the COUNTY WINS and the alias renames the census.

Reading either case by the other's rule would ship a wrong name: aliasing all
five to the canvass would publish "Indian Grv", and taking the census for all
five would drop a numeral the county's own ballot carries.

NO BOARD DISTRICT SHIPS HERE: this file is precincts only, and a `district`
property would invent a join this build has not made. NO POLLING PLACE SHIPS —
that belongs with a roster guard rather than inside a geometry file.

THIS IS A RARE OPERATOR STEP (requests + shapely). Re-run only if Livingston
re-precincts or TIGERweb republishes the voting-district fabric. Output is
deterministic, so --check is a byte compare.

Usage:
    python3 scripts/build_livingston_precincts.py            # write
    python3 scripts/build_livingston_precincts.py --check    # verify shipped == fresh
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtd_board_districts as V  # noqa: E402
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)



REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PRECINCTS = os.path.join(REPO_ROOT, "il", "data", "app", "livingston-precincts.json")

COUNTY_FIPS = "105"
COUNTY_POP_2020 = 35815
EXPECTED_PRECINCTS = 46

RESULTS_URL = "https://il-livingston.pollresults.net/"
SOURCE_LABEL = ("Census 2020 voting districts, one per precinct, carrying the "
                "forty-six precinct names Livingston County's own certified "
                "canvasses use, with Indian Grove spelled as the census names "
                "the township rather than as the results feed abbreviates it")

# As they SHIP. Forty-five are the census spelling (which the canvass agrees with
# on forty-one and abbreviates on the four Indian Groves); CHATSWORTH 1 is the
# county's own designation. See the docstring for why the two cases go opposite
# ways.
COUNTY_PRECINCTS = (
    "AMITY", "AVOCA", "BELLE PRAIRIE", "BROUGHTON", "CHARLOTTE", "CHATSWORTH 1",
    "DWIGHT 1", "DWIGHT 2", "DWIGHT 3", "DWIGHT 4", "EPPARDS POINT", "ESMEN",
    "FAYETTE", "FORREST 1", "GERMANVILLE", "INDIAN GROVE 1", "INDIAN GROVE 2",
    "INDIAN GROVE 3", "INDIAN GROVE 4", "LONG POINT", "NEBRASKA 1", "NEVADA",
    "NEWTOWN", "ODELL 1", "OWEGO", "PIKE", "PLEASANT RIDGE", "PONTIAC 1",
    "PONTIAC 10", "PONTIAC 2", "PONTIAC 3", "PONTIAC 4", "PONTIAC 5",
    "PONTIAC 6", "PONTIAC 7", "PONTIAC 8", "PONTIAC 9", "READING 1",
    "READING 2", "ROOKS CREEK", "ROUND GROVE", "SAUNEMIN", "SULLIVAN",
    "SUNBURY", "UNION", "WALDO",
)

# ONE, and it is a designation rather than a spelling — the Greene case. The
# four Indian Groves are deliberately NOT here: there the results feed is the
# one abbreviating, so the census name ships and nothing needs renaming.
ALIASES = {
    "CHATSWORTH 1": "CHATSWORTH",
}

MAX_OVERLAP_M2 = 1.0
MIN_COVERED = 0.9999


fail = make_fail("livingston-precincts")




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
            "note": ("Livingston County's forty-six voting precincts. The Census 2020 "
                     "voting districts carry the county's own precinct names one for "
                     "one after a single rename and sum to its exact 2020 population "
                     "of 35,815, so the fabric is the county's and nothing is "
                     "dissolved. The names come from the Clerk's own certified "
                     "canvasses at il-livingston.pollresults.net. Five names differ "
                     "between the two publishers and go opposite ways: the county "
                     "attaches a numeral to Chatsworth, so its designation ships, "
                     "while the results feed abbreviates Indian Grove to 'Indian "
                     "Grv', so the census's own township spelling ships for those "
                     "four. No board district is carried: this file is precincts "
                     "only. No polling place is carried either — that belongs with "
                     "a roster guard rather than in a geometry file."),
        },
        "features": features,
    }

    body = V.dumps(payload)
    print("livingston-precincts: %d voting districts -> %d precincts (pop %d = census "
          "POP100)" % (len(vtds), len(composition), county_pop))
    print("  %s" % ", ".join("%s=%d" % (n, pops[n]) for n in sorted(pops)))
    print("  tiling: overlap %.2f m2; %.4f%% of the county covered"
          % (overlap, 100 * covered))
    V.write_or_check([(OUT_PRECINCTS, body)], args.check, REPO_ROOT, fail, "livingston")


if __name__ == "__main__":
    main()
