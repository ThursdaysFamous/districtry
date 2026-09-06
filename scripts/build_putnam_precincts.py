#!/usr/bin/env python3
"""Build Putnam County's eight voting precincts from Census 2020 voting districts.

WHY THIS COUNTY WAS SHUT AND WHY IT IS NOT. Its gap record
(`putnam-precinct-geometry`) was written on 2 Aug 2026 and it was accurate that
day: "Putnam runs no mapping system beyond an assessment-office parcel tool, and
no county items appear in any public map catalogue. The clerk publishes specimen
ballots and polling places as documents, not as data." All of that is still
true, and none of it is the question any more — because it was measured BEFORE
this project found the election-results vendors, in the sweeps of 18-21 Aug that
shipped Clark, Crawford, Mercer, Moultrie, Edgar, Cumberland, Johnson, Perry and
Hancock. A RECORD MEASURED BEFORE A ROUTE EXISTED IS A HYPOTHESIS ABOUT THE
ROUTE THAT DID NOT EXIST, and Putnam is the fourth county in this fleet to be
re-opened by re-reading its own record's DATE rather than its prose (Gallatin,
Vermilion and Knox were the others).

THE CANVASS NAMES EVERY PRECINCT, which is the whole difference between a county
that builds and one that does not. il-putnam.pollresults.net is the Clerk's own
results site — the AngularJS shell whose entire result set is embedded in the
page as JSON, the shape build_clark_boundaries.py already documents — and it
prints "8 PRECINCTS REPORTING / 0 PRECINCTS NOT REPORTING" beside per-precinct
rows naming Granville 1-4, Hennepin 1, Magnolia 1-2 and Senachwine 1.

THE VENDOR WAS TESTED BY CONTENT, NOT BY A STATUS CODE, because this project has
already been fooled once: pollresults answers 200 for a county it does not carry
and serves a generic shell. The control is a FABRICATED county name. Measured
2026-09-06: il-putnam.pollresults.net returns 139,297 bytes with a unique md5,
while il-zzzfakecounty and il-notarealcounty both return the same 7,720-byte
body — and so does il-washington, which is why Washington's own precinct gap
stays shut on this route. The sibling host il-<county>.accessliberty.com is
WORSE than useless for this test: it ECHOES whatever subdomain it is given into
the page, so "the page names the county" is true of a fabricated one too.

THE PRECINCTS ARE THE CENSUS FABRIC, ONE FOR ONE. THE JASPER TEST PASSES 8/8
after two aliases, and their POP100 sums to Putnam's own 2020 population of
5,637 to the person. No dissolve is needed and none is performed.

THE TWO ALIASES ARE THE GREENE CASE, NOT A SPELLING. The county attaches a "1"
to its two single-precinct townships where the census leaves them unnumbered —
HENNEPIN 1 and SENACHWINE 1 against HENNEPIN and SENACHWINE. A number the county
puts on its own ballot is the county's designation, so the county wins and the
alias RENAMES the census; apply_aliases refuses to make it a merge.

NO BOARD DISTRICT SHIPS AND NONE EVER WILL. Putnam elects its five commissioners
COUNTYWIDE — it is one of the at-large counties riding the County card
(data/app/il-county-commissioners.json) — so there is no district for a precinct
to belong to and a `district` property here would invent one.

NO POLLING PLACE SHIPS. The Clerk publishes them as documents rather than data,
and a polling place belongs with a roster guard and a date rather than inside a
geometry file — the rule Calhoun's build set and Gallatin's repeated.

THIS IS A RARE OPERATOR STEP (requests + shapely). Re-run only if Putnam
re-precincts or TIGERweb republishes the voting-district fabric. Output is
deterministic, so --check is a byte compare.

Usage:
    python3 scripts/build_putnam_precincts.py            # write
    python3 scripts/build_putnam_precincts.py --check    # verify shipped == fresh
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtd_board_districts as V  # noqa: E402
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PRECINCTS = os.path.join(REPO_ROOT, "il", "data", "app", "putnam-precincts.json")

COUNTY_FIPS = "155"
COUNTY_POP_2020 = 5637
EXPECTED_PRECINCTS = 8

RESULTS_URL = "https://il-putnam.pollresults.net/"
SOURCE_LABEL = ("Census 2020 voting districts, one per precinct, carrying the "
                "eight precinct names Putnam County's own certified canvasses use")

# The county's eight precincts, spelled as its own certified returns spell them.
# This list IS the Jasper test's input: the census fabric must carry these eight
# names and no others.
COUNTY_PRECINCTS = (
    "GRANVILLE 1",
    "GRANVILLE 2",
    "GRANVILLE 3",
    "GRANVILLE 4",
    "HENNEPIN 1",
    "MAGNOLIA 1",
    "MAGNOLIA 2",
    "SENACHWINE 1",
)

# County spelling -> census BASENAME. Two, and both are a DESIGNATION rather than
# a spelling: the county numbers its two single-precinct townships and the census
# does not. The Greene case exactly (WRIGHTS 2 against the census's WRIGHTS), and
# it runs the same way — a RENAME onto the county's own designation, never a
# merge, with apply_aliases refusing to touch a name the census already carries.
ALIASES = {
    "HENNEPIN 1": "HENNEPIN",
    "SENACHWINE 1": "SENACHWINE",
}

MAX_OVERLAP_M2 = 1.0
MIN_COVERED = 0.9999


fail = make_fail("putnam-precincts")


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
            "note": ("Putnam County's eight voting precincts. The Census 2020 "
                     "voting districts carry the county's own eight precinct "
                     "names one for one — after renaming two that the county "
                     "numbers and the census does not — and sum to its exact "
                     "2020 population, so the fabric is the county's and nothing "
                     "is dissolved. The names come from the Clerk's own certified "
                     "canvasses, which report eight precincts and name all eight. "
                     "No board district is carried: Putnam elects its five "
                     "commissioners countywide, so there is none. No polling "
                     "place is carried either — the Clerk publishes them as "
                     "documents, and that belongs with a roster guard rather "
                     "than in a geometry file."),
        },
        "features": features,
    }

    body = V.dumps(payload)
    print("putnam-precincts: %d voting districts -> %d precincts (pop %d = census "
          "POP100)" % (len(vtds), len(composition), county_pop))
    print("  %s" % ", ".join("%s=%d" % (n, pops[n]) for n in sorted(pops)))
    print("  tiling: overlap %.2f m2; %.4f%% of the county covered"
          % (overlap, 100 * covered))
    V.write_or_check([(OUT_PRECINCTS, body)], args.check, REPO_ROOT, fail, "putnam")


if __name__ == "__main__":
    main()
