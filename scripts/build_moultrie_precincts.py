#!/usr/bin/env python3
"""Build Moultrie County's sixteen voting precincts from Census 2020 voting districts.

WHY THIS COUNTY HAD NO PRECINCT LAYER. Moultrie joined the ring on 2026-08-18
through the County card alone — its board is elected at large, so it has no
district geometry and no dispatch entry. Nothing was blocking its precincts; there
was simply no gap record saying they were missing. The 2026-08-20 audit that found
eleven such counties is the reason this file exists, and this build gives Moultrie
its first dispatch entry of any kind.

THE COUNTY DRAWS THEM TOO, found 2026-10-10: Coles County's map server hosts
Moultrie/Voter_Precincts/MapServer/0 on www.colesco.illinois.gov (read with
aia_bundle.ca_bundle("coles"), the Coles incomplete-chain host), 16 polygons
named Lowe, Lovington 1-2, Jonathan Creek, East Nelson, Marrowbone 1-2, Dora 1,
Whitley and Sullivan 1-7 — the same sixteen. The census shapes below still
ship; that layer is the better geometry source.

THE PRECINCTS ARE THE CENSUS FABRIC, ONE FOR ONE. THE JASPER TEST PASSES 16/16 and
their POP100 sums to the county's 2020 population of 14,526 to the person.

NO ALIAS IS NEEDED, THOUGH THE TWO SOURCES LOOK DIFFERENT AT A GLANCE. The county's
results feed writes SULLIVAN #1 where the census writes SULLIVAN 1 — a numbering
glyph, and exactly the kind of difference norm() exists to absorb, since case,
punctuation and spacing differ freely between a county's feed and a census
BASENAME. COUNTY_PRECINCTS below carries the county's rendering because that is
what the Jasper test must match; the shipped features are LABELLED from the census
basename because "#" is the feed's punctuation rather than part of a name.

THE NAMES COME FROM THE COUNTY'S OWN CERTIFIED RETURNS. Its 2026 General Primary on
il-moultrie.pollresults.net carries one PrecinctName per precinct across its race
data, naming all sixteen and no seventeenth, and reports 16 precincts reporting of
16.

NO BOARD DISTRICT SHIPS AND NONE EVER WILL. The same returns carry the board's
contest as "COUNTY BOARD DISTRICT AT LARGE MEMBER" — the county's own wording — so
Moultrie elects its nine members county-wide and there is no district for a
precinct to belong to. They ride the County card
(data/app/il-county-commissioners.json).

NO POLLING PLACE SHIPS — that belongs with a roster guard and a date.

THIS IS A RARE OPERATOR STEP (requests + shapely). Re-run only if Moultrie
re-precincts or TIGERweb republishes the voting-district fabric. Output is
deterministic, so --check is a byte compare.

Usage:
    python3 scripts/build_moultrie_precincts.py            # write
    python3 scripts/build_moultrie_precincts.py --check    # verify shipped == fresh
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtd_board_districts as V  # noqa: E402
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PRECINCTS = os.path.join(REPO_ROOT, "il", "data", "app", "moultrie-precincts.json")

COUNTY_FIPS = "139"
COUNTY_POP_2020 = 14526
EXPECTED_PRECINCTS = 16

RESULTS_URL = "https://il-moultrie.pollresults.net/"
SOURCE_LABEL = ("Census 2020 voting districts, one per precinct, carrying the "
                "sixteen precinct names Moultrie County's certified 2026 "
                "General Primary names one committeeperson contest at a time")

# The county's sixteen precincts, spelled as its own certified returns spell
# them. This list IS the Jasper test's input: the census fabric must carry these
# sixteen names and no others.
COUNTY_PRECINCTS = (
    "DORA #1",
    "EAST NELSON #1",
    "JONATHAN CREEK #1",
    "LOVINGTON #1",
    "LOVINGTON #2",
    "LOWE #1",
    "MARROWBONE #1",
    "MARROWBONE #2",
    "SULLIVAN #1",
    "SULLIVAN #2",
    "SULLIVAN #3",
    "SULLIVAN #4",
    "SULLIVAN #5",
    "SULLIVAN #6",
    "SULLIVAN #7",
    "WHITLEY #1",
)

# County spelling -> census BASENAME. None: the county's feed prefixes its numbers with '#', which norm() absorbs.
ALIASES = {}

MAX_OVERLAP_M2 = 1.0
MIN_COVERED = 0.9999


fail = make_fail("moultrie-precincts")


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

    # One voting district per precinct, LABELLED from the census basename, which drops the '#' the county's results feed prefixes its numbers with.
    # check_partition still runs, because it is what proves nothing is claimed
    # twice and nothing is left over — the guard that would catch a future
    # re-precincting that kept the same count.
    composition = {}
    for precinct in COUNTY_PRECINCTS:
        label = V.title_case(vtds[V.norm(precinct)]["basename"])
        if label in composition:
            fail("two precincts label as %r — the census basenames are not "
                 "distinct under this county's rendering" % label)
        composition[label] = [precinct]
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
            "note": ("Moultrie County's sixteen voting precincts. The Census 2020 voting "
                     "districts carry the county's own sixteen precinct names and sum to "
                     "its exact 2020 population, so the fabric is the county's and nothing "
                     "is dissolved. The names and the count both come from the county's "
                     "certified 2026 General Primary. Each feature is labelled from the "
                     "census basename, which drops the '#' the county's results feed "
                     "prefixes its numbers with — a numbering glyph rather than part of a "
                     "name. NO BOARD DISTRICT is carried and none ever will be: the same "
                     "returns carry the board's contest as COUNTY BOARD DISTRICT AT LARGE "
                     "MEMBER, so Moultrie elects its nine members county-wide and they "
                     "ride the County card. No polling place ships either — that belongs "
                     "with a roster guard and a date."),
        },
        "features": features,
    }

    body = V.dumps(payload)
    print("moultrie-precincts: %d voting districts -> %d precincts (pop %d = census "
          "POP100)" % (len(vtds), len(composition), county_pop))
    print("  %s" % ", ".join("%s=%d" % (n, pops[n]) for n in sorted(pops)))
    print("  tiling: overlap %.2f m2; %.4f%% of the county covered"
          % (overlap, 100 * covered))
    V.write_or_check([(OUT_PRECINCTS, body)], args.check, REPO_ROOT, fail, "moultrie")


if __name__ == "__main__":
    main()
