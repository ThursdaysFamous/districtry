#!/usr/bin/env python3
"""
Build data/app/franklin-precincts.json + data/app/franklin-county-board-districts.json
— Franklin County's 35 voting precincts and 3 County Board districts, composed
from the county's own certified election returns (docs/EXPANSION_GUIDE.md
§3.5.1, the canvass route; scripts/vtd_board_districts.py holds the machinery).

A THIRD RESULTS VENDOR, AND THE FIRST COUNTY THIS PROJECT HAS REACHED THROUGH
IT. Clark, Crawford, Mercer and Edgar all came from the accessliberty /
pollresults pair. Franklin's Clerk publishes through
platinumelectionresults.com instead — a .NET application whose county cards
carry a `data-county` id and route to /turnouts/county/<id> (Franklin is 21).
Its index names the EIGHT Illinois counties it serves: Clinton, DeKalb,
Franklin, Henry, Marion, Pike, Randolph and Wayne. Two of those eight are
unserved frontier counties with open records of their own (Marion, Wayne),
which is why the vendor is named here rather than only in this county's notes.

WHAT THE VENDOR PUBLISHES. Per-precinct race pages, one per precinct per
election, back to 2016:
    /history/prraces/<election>/21/<precinctId>
Each carries every contest that precinct actually voted on, so the set of
precincts carrying a district's board contest IS that district's composition.

THREE CERTIFIED ELECTIONS AGREE, EXACTLY — one better than the Clark standard,
which asks for two witnesses per district and gets three for all three here:

  * 2024 GENERAL — all 35 precincts carry one "FOR MEMBER OF THE COUNTY BOARD"
    contest. They partition into Neil Hargis 13, Brad Wilson 13, David Bartoni
    9: 35 precincts, each claimed exactly once.
  * 2022 GENERAL — same 35 precincts, same three sets, different candidates
    (the seats are staggered, so a different third of the board was up).
  * 2026 GENERAL PRIMARY — and this one NAMES THE DISTRICTS in its contest
    headers ("FOR COUNTY BOARD DISTRICT 1"), which is what turns the county's
    members page from the only district key into a corroborated one.

THE DISTRICT KEY IS CORROBORATED, NOT ASSUMED. The 2024 and 2022 canvasses
name candidates, not districts. The county's own members page groups its nine
members under District 1, 2 and 3 — Hargis under 1, Wilson under 2, Bartoni
under 3 — and the 2026 primary's numbered headers independently produce the
same three precinct sets. Two publishers, one answer.

THE COUNTY ALSO DRAWS ITS PRECINCTS, found 2026-10-10. Its ArcGIS Online org
publishes Precinct_Franklin/FeatureServer/0 on services7.arcgis.com
(gb3yKpyyBmugDAn1), 35 polygons whose Precinct names equal the 35 shipped here
exactly, data last edited 2026-09-15. The county's own pages do not link it.
The shapes shipped here are Census 2020 voting districts composed by canvass,
so that layer is the better geometry source and the obvious next rebuild.

A WRONG SHORTCUT, RECORDED BECAUSE IT LOOKED RIGHT. The vendor's precinct ids
group 51xx-54xx, 61xx-64xx and 71xx-74xx, which reads exactly like a district
key. It is not one: Browning 1 (6201) and Browning 3 (6203) sit in District 1
while Browning 2 (6202) sits in District 2, and the prefixes interleave across
all three districts. The hypothesis was tested against the ballots rather than
assumed, and it failed.

THE JASPER TEST PASSES. TIGER's Census 2020 voting-district layer carries
exactly 35 Franklin features summing to the county's exact 37,804, and 34 of
the 35 names match the county's own spelling character for character. The one
that differs is CAVE 1, which the county writes Cave — the vestigial-1 rule,
recorded in CENSUS_SPELLING below rather than smoothed away, and the shipped
features carry both spellings.

THE POPULATION SPREAD IS THE COUNTY'S OWN and is recorded, not smoothed:
three districts of three members each, so the ideal is a third of the county.

THIS IS A RARE OPERATOR STEP (requests + shapely). Re-run only if Franklin
reapportions, re-precincts, or TIGERweb republishes the VTD fabric. Output is
deterministic, so --check is a byte compare.

Usage:
    python3 scripts/build_franklin_boundaries.py [--check]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_metro_outline import point_in_rings  # noqa: E402
import vtd_board_districts as V  # noqa: E402
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PRECINCTS = os.path.join(REPO_ROOT, "il", "data", "app", "franklin-precincts.json")
OUT_DISTRICTS = os.path.join(REPO_ROOT, "il", "data", "app",
                             "franklin-county-board-districts.json")

COUNTY_FIPS = "055"
COUNTY_POP_2020 = 37804
EXPECTED_PRECINCTS = 35
# Three members per district, staggered — read from the county's own members
# page, which prints three rows under each district heading. The canvasses
# agree by construction: each general election fills one seat per district.
SEATS_PER_DISTRICT = 3

RESULTS_URL = "https://platinumelectionresults.com/turnouts/county/21"
BOARD_URL = "https://franklincountyil.gov/county-board-members/"
ELECTIONS_URL = "https://franklincountyil.gov/elections/"

SOURCE_LABEL = ("Census 2020 voting districts dissolved per the composition of "
                "Franklin County's certified 2024 General, 2022 General and "
                "2026 General Primary results, published per precinct by "
                "County Clerk Paris Dunk's results system "
                "(platinumelectionresults.com)")

# THE COMPOSITION, read from the per-precinct returns of three certified
# elections that agree exactly. All 35 precincts, each in exactly one district.
# The weekly roster run re-reads this from the live feed and fails if it moves.
COMPOSITION = {
    "1": ("BARREN", "BROWNING 1", "BROWNING 3", "GOODE 1", "GOODE 2",
          "SIX MILE 1", "SIX MILE 2", "SIX MILE 3",
          "TYRONE 1", "TYRONE 2", "TYRONE 3", "TYRONE 4", "TYRONE 5"),
    "2": ("BENTON 1", "BENTON 2", "BENTON 3", "BENTON 4", "BENTON 5",
          "BENTON 6", "BENTON 7", "BROWNING 2", "CAVE", "EASTERN",
          "EWING 1", "EWING 2", "NORTHERN"),
    "3": ("DENNING 1", "DENNING 2", "DENNING 3", "DENNING 4", "DENNING 5",
          "FRANKFORT 1", "FRANKFORT 2", "FRANKFORT 3", "FRANKFORT 4"),
}
# county spelling -> census BASENAME, for the one the publishers write
# differently. 34 of 35 match exactly, so this one pairs uniquely.
CENSUS_SPELLING = {"CAVE": "CAVE 1"}

# Measured 0.114 (District 2) against a 12,601 ideal — an ordinary adopted-plan
# spread, and tighter than Mercer's shipped -14.6%.
BALANCE_DEV_MAX = 0.30
MAX_OVERLAP_M2 = 1.0
MIN_COVERED = 0.9999


fail = make_fail("franklin-boundaries")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped files match a fresh build")
    args = ap.parse_args()

    from shapely.geometry import shape, mapping   # noqa: E402  (heavy, function-local)
    from shapely.ops import unary_union, transform  # noqa: E402

    claimed = [n for names in COMPOSITION.values() for n in names]
    if len(claimed) != EXPECTED_PRECINCTS:
        fail("the composition names %d precincts, expected %d"
             % (len(claimed), EXPECTED_PRECINCTS))

    vtds = V.apply_aliases(V.fetch_vtds(COUNTY_FIPS, shape, fail),
                           CENSUS_SPELLING, fail)
    if len(vtds) != EXPECTED_PRECINCTS:
        fail("the census voting-district layer carries %d Franklin precincts, "
             "expected %d" % (len(vtds), EXPECTED_PRECINCTS))
    county_geom, county_pop = V.fetch_county(COUNTY_FIPS, shape, fail)
    if county_pop != COUNTY_POP_2020:
        fail("census county population is %d, expected %d"
             % (county_pop, COUNTY_POP_2020))
    V.check_fabric(vtds, claimed, county_pop, fail)
    where = V.check_partition(COMPOSITION, vtds, fail)

    districts, pops = V.dissolve(COMPOSITION, vtds, unary_union)
    ideal = county_pop / float(len(COMPOSITION))
    worst = max(((abs(pops[d] - ideal) / ideal), d) for d in pops)
    if worst[0] > BALANCE_DEV_MAX:
        fail("district %s deviates %.1f%% from the per-district ideal (ceiling "
             "%.0f%%) — that is a mis-assignment, not an apportionment"
             % (worst[1], 100 * worst[0], 100 * BALANCE_DEV_MAX))
    overlap, covered = V.check_tiling(districts, county_geom, transform,
                                      MAX_OVERLAP_M2, MIN_COVERED, unary_union, fail)

    precinct_features = []
    for key in sorted(vtds, key=lambda k: vtds[k]["basename"]):
        rec = vtds[key]
        props = {"name": V.title_case(rec["basename"]), "district": where[key],
                 "geoid": rec["geoid"], "pop2020": rec["pop"]}
        # Both spellings ride the feature, so a reader searching either finds it.
        if rec.get("censusName"):
            props["censusName"] = V.title_case(rec["censusName"])
        precinct_features.append({
            "type": "Feature",
            "properties": props,
            "geometry": V.round_geom(rec["geom"], mapping),
        })
    precincts_payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL, "resultsUrl": RESULTS_URL,
            "electionsUrl": ELECTIONS_URL,
            "note": ("Franklin County's 35 precincts are the Census 2020 voting "
                     "districts, which carry the county's own 35 precinct names "
                     "34/35 character for character and sum to its exact 2020 "
                     "population; the census writes CAVE 1 where the county "
                     "writes Cave, and both spellings ride the feature. Each "
                     "feature also carries its County Board district, which is "
                     "whole-precinct — no precinct is split between districts. "
                     "Polling places are not shown here: the county publishes "
                     "no precinct-to-polling-place pairing as data."),
        },
        "features": precinct_features,
    }

    district_features = []
    for dnum in sorted(COMPOSITION, key=int):
        district_features.append({
            "type": "Feature",
            "properties": {"district": dnum, "name": "District %s" % dnum,
                           "precincts": [V.title_case(n) for n in COMPOSITION[dnum]],
                           "pop2020": pops[dnum], "seats": SEATS_PER_DISTRICT},
            "geometry": V.round_geom(districts[dnum], mapping),
        })
    districts_payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL, "resultsUrl": RESULTS_URL, "boardUrl": BOARD_URL,
            "canvass": ("Composition from three certified elections that agree "
                        "exactly: the 2024 General and 2022 General (whose "
                        "board contests name candidates, keyed to districts by "
                        "the county's own members page) and the 2026 General "
                        "Primary (whose contest headers name the districts "
                        "outright). Each district's precinct list is identical "
                        "in all three, and the three lists partition the "
                        "county's 35 precincts exactly once each"),
            "note": ("Three districts of THREE members each, staggered, "
                     "dissolved from Census 2020 voting districts. Franklin "
                     "publishes no board-district boundary as data and its GIS "
                     "page links no public map service, so these boundaries "
                     "are derived from the election returns instead."),
        },
        "features": district_features,
    }

    V.verify_point_in_rings(COMPOSITION, vtds, district_features, point_in_rings, fail)

    prec_body = V.dumps(precincts_payload)
    dist_body = V.dumps(districts_payload)
    print("franklin-boundaries: %d precincts -> %d districts of %d; census fabric "
          "matches the county's precinct list %d/%d"
          % (EXPECTED_PRECINCTS, len(COMPOSITION), SEATS_PER_DISTRICT,
             EXPECTED_PRECINCTS, EXPECTED_PRECINCTS))
    print("  populations: %s (total %d = census POP100; worst deviation %.1f%% in "
          "district %s — the county's own plan)"
          % (", ".join("D%s=%d" % (d, pops[d]) for d in sorted(pops, key=int)),
             county_pop, 100 * worst[0], worst[1]))
    print("  tiling: overlap %.2f m2; %.4f%% of the county covered"
          % (overlap, 100 * covered))
    V.write_or_check([(OUT_PRECINCTS, prec_body), (OUT_DISTRICTS, dist_body)],
                     args.check, REPO_ROOT, fail, "franklin")


if __name__ == "__main__":
    main()
