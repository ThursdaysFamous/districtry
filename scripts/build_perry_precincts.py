#!/usr/bin/env python3
"""Build Perry County's twenty-seven voting precincts from Census 2020 voting districts.

WHY THIS COUNTY WAS DARK, AND WHAT OPENED IT. Perry's recorded blocker is its
website: the county's site refuses this client, so nothing it publishes about
itself could be read. That blocker is unchanged and this build does not touch it.
What changed is that the county's ELECTION AUTHORITY publishes somewhere else —
results.gbsvote.com, which carries THIRTEEN Illinois counties (plus one in
Indiana) — and a county's certified canvass answers both questions a join needs
without the county's own site being reachable at all.

THE VENDOR WAS NOT A NEW DISCOVERY AND SHOULD NOT BE READ AS ONE. This project
recorded it in its own backlog on 2026-08-20, swept it county by county, and
measured this county's board form from it that day. What did not happen for the
day after is the rest: the finding never reached the county's gap record, never reached
CLAUDE.md's list of results platforms, and never became a build. A measurement
filed in a backlog and nowhere else is a measurement the next pass repeats.

THE BOARD'S FORM IS SETTLED, AND IT IS AT LARGE. Perry's certified 2026 General
Primary carries a single "FOR COUNTY COMMISSIONER" contest per party, each
reporting 27 of 27 precincts — the same 27-of-27 every countywide office on that
ballot reports (County Clerk and Recorder, County Treasurer, Sheriff, Treasurer).
There is no district-suffixed board contest anywhere in it, and the contests that
report 1 of 1 are the twenty-seven precinct committeeperson races, which is the
expected shape and the check that the reporting counts mean what they appear to.
So Perry is a COMMISSION county electing county-wide: THERE IS NO BOARD GEOMETRY
TO SEEK and none should be invented. Its commissioners are not carried here
either — that is a roster, it belongs on the County card with a source and a date,
and the only county source for it is the site this client cannot read.

CORRECTED 2026-10-20: the site can be read now. Asked with our own token on
Python's own HTTP client, perrycountyil.gov served its commissioners page three
times running, twenty seconds apart, naming all three, so they ride the County
card from `scripts/il_county_commissioners_scraper.py` (its PERRY entry records
the reading). The two sentences above, and the opening paragraph's "That blocker
is unchanged", were true of the holding page the site answered in August.

THE PRECINCTS ARE THE CENSUS FABRIC, ONE FOR ONE. THE JASPER TEST PASSES 27/27:
the census voting districts carry Perry's twenty-seven precinct names exactly, and
their POP100 sums to the county's own 2020 population of 20,945 to the person. No
dissolve is needed and none is performed — each precinct IS one voting district.

ONE SPELLING IS RECORDED RATHER THAN CHOSEN BETWEEN. The county's results feed
writes its county-seat precincts closed up, DUQUOIN 1 through DUQUOIN 12, where
the census writes DU QUOIN 1 through DU QUOIN 12 — two words, which is how the
city itself spells its name. That is a rendering difference and not a different
precinct, and it is exactly what the shared module's norm() exists to absorb: case,
punctuation and spacing differ freely between a county's results feed and a census
BASENAME. So COUNTY_PRECINCTS below carries the county's rendering, because that is
what the county published and what the Jasper test must match, while each shipped
feature is LABELLED from the census basename, because "Du Quoin" is the place's
name and "Duquoin" would be this project inventing a spelling nobody uses. Both
renderings are therefore in this file's provenance and neither is silently
preferred.

NO POLLING PLACE SHIPS. That belongs with a roster guard and a date rather than
inside a geometry file — the rule Calhoun's build set — and in this county it is
not readable anyway.

THIS IS A RARE OPERATOR STEP (requests + shapely). Re-run only if Perry
re-precincts or TIGERweb republishes the voting-district fabric. Output is
deterministic, so --check is a byte compare.

Usage:
    python3 scripts/build_perry_precincts.py            # write
    python3 scripts/build_perry_precincts.py --check    # verify shipped == fresh
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtd_board_districts as V  # noqa: E402
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PRECINCTS = os.path.join(REPO_ROOT, "il", "data", "app", "perry-precincts.json")

COUNTY_FIPS = "145"
COUNTY_POP_2020 = 20945
EXPECTED_PRECINCTS = 27

RESULTS_URL = "https://results.gbsvote.com/locations/counties.asp?p_id=3&l_id=283"
SOURCE_LABEL = ("Census 2020 voting districts, one per precinct, carrying the "
                "twenty-seven precinct names Perry County's certified 2026 "
                "General Primary names one committeeperson contest at a time")

# The county's twenty-seven precincts, spelled as its own certified returns spell
# them — including DUQUOIN closed up, which the census writes DU QUOIN. This list
# IS the Jasper test's input: the census fabric must carry these twenty-seven
# names and no others, and norm() is what lets the two renderings meet.
COUNTY_PRECINCTS = (
    "BEAUCOUP",
    "CUTLER",
    "DUQUOIN 1", "DUQUOIN 2", "DUQUOIN 3", "DUQUOIN 4", "DUQUOIN 5", "DUQUOIN 6",
    "DUQUOIN 7", "DUQUOIN 8", "DUQUOIN 9", "DUQUOIN 10", "DUQUOIN 11", "DUQUOIN 12",
    "PINCKNEYVILLE 1", "PINCKNEYVILLE 2", "PINCKNEYVILLE 3", "PINCKNEYVILLE 4",
    "PINCKNEYVILLE 5", "PINCKNEYVILLE 6", "PINCKNEYVILLE 7", "PINCKNEYVILLE 8",
    "SUNFIELD",
    "SWANWICK",
    "TAMAROA 1",
    "TAMAROA 2",
    "WILLISVILLE",
)

MAX_OVERLAP_M2 = 1.0
MIN_COVERED = 0.9999


fail = make_fail("perry-precincts")


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

    # The Jasper test proper: names one-for-one AND the population identity.
    V.check_fabric(vtds, COUNTY_PRECINCTS, county_pop, fail)

    # One voting district per precinct, LABELLED from the census basename so
    # Du Quoin keeps its own spelling (see the note at the top). check_partition
    # still runs, because it is what proves nothing is claimed twice and nothing
    # is left over — the guard that would catch a future re-precincting that
    # kept the same count.
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
            "note": ("Perry County's twenty-seven voting precincts. The Census 2020 "
                     "voting districts carry the county's own twenty-seven precinct "
                     "names one for one and sum to its exact 2020 population, so the "
                     "fabric is the county's and nothing is dissolved. The names and "
                     "the count both come from the county's certified 2026 General "
                     "Primary, which prints a committeeperson contest per precinct "
                     "per party and reads \"27 OF 27 PRECINCTS REPORTING\" — the "
                     "county's own website refuses this client and was not readable. "
                     "Each feature is labelled from the census basename, so the "
                     "county seat keeps its own spelling: the results feed writes "
                     "DUQUOIN closed up where the census and the city write Du Quoin, "
                     "a rendering difference rather than a different precinct. NO "
                     "BOARD DISTRICT is carried: the same canvass carries a single "
                     "countywide FOR COUNTY COMMISSIONER contest per party over all "
                     "twenty-seven precincts and no district-suffixed board contest "
                     "at all, so Perry elects its board county-wide and there is no "
                     "district for a precinct to belong to. No commissioner is named "
                     "here either — that is a roster, and the only county source for "
                     "it is the blocked site. No polling place ships, for the same "
                     "reason and by the same rule."),
        },
        "features": features,
    }

    body = V.dumps(payload)
    print("perry-precincts: %d voting districts -> %d precincts (pop %d = census "
          "POP100)" % (len(vtds), len(composition), county_pop))
    print("  %s" % ", ".join("%s=%d" % (n, pops[n]) for n in sorted(pops)))
    print("  tiling: overlap %.2f m2; %.4f%% of the county covered"
          % (overlap, 100 * covered))
    V.write_or_check([(OUT_PRECINCTS, body)], args.check, REPO_ROOT, fail, "perry")


if __name__ == "__main__":
    main()
