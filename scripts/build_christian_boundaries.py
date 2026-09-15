#!/usr/bin/env python3
"""
Build il/data/app/christian-county-board-districts.json — Christian County's
four County Board districts (16 members, four per district on staggered
terms; docs/EXPANSION_GUIDE.md Part 3; scripts/vtd_board_districts.py holds
the machinery).

THIS COUNTY SHIPS DISTRICTS AND NOT PRECINCTS, and that is the whole shape of
the problem it posed. Christian re-precincted after the 2020 census: the
Census 2020 voting-district layer carries THIRTY Christian precincts and the
county now runs TWENTY-NINE, so `check_fabric` — the Jasper test — fails by
construction and no precinct layer can be drawn from census geometry. Its gap
record read that as a block on the districts too, for three weeks. It is not:
the districts were drawn on the thirty, and the thirty are exactly what the
census publishes.

WHAT THE COUNTY DREW. christiancountyil.gov publishes
Reapportionment-Plan-on-File-with-County-Clerk-2021.pdf, three scanned pages:
the county's own COUNTY BOARD DISTRICT AND PRECINCT MAP on 2020 census data
(Supervisor of Assessments, printed 6 October 2021), the 2021 Reapportionment
Plan Recommendations by Board Chairman Wells, and the superseded 2012 plan on
2010 data. The map publishes four district populations — 8,918 / 8,210 /
8,441 / 8,463 against a county of 34,032 — and per-precinct populations for
the three townships it insets. Those three inset tables reproduce the Census
2020 POP100 of every Taylorville, Pana and South Fork voting district to the
person, which is what identifies the map's fabric as the census fabric.

THE POPULATION IDENTITY IS THE GATE, and what it proves is bounded. Dissolving
the thirty voting districts by the composition below gives 8,918 / 8,210 /
8,441 / 8,463 — the county's own four figures, in the county's own district
numbering, summing to its exact 34,032. Four sums matching across a thirty-way
partition is not a coincidence, and it pins the composition. It does NOT by
itself say anything about a precinct created after the map was printed: it is
re-doing the county's 2021 arithmetic, so a later change is invisible to it.
That question is answered separately, below.

FOUR WITNESSES, THREE OF THEM CERTIFIED ELECTIONS. The county's Statement of
Votes Cast for the 8 November 2022 General and the 5 November 2024 General
(il-christian.accessliberty.com) and its certified 2026 General Primary
(il-christian.pollresults.net, Final, updated 1 April 2026) each run all four
board contests and each partitions the county's 29 current precincts into the
same four districts, with no precinct in two of them. The 2022 canvass prints
every one of the 29 rows in every contest, dashed where a precinct is not in
that district, so its blocks are gated on seeing 29 rows; 2024 prints only the
participating rows and is gated on matching 2022 instead.

WHERE TAYLORVILLE 9 CAME FROM — the question this county was actually stuck
on, answered by the county's own registration counts rather than by a map or a
reply. Comparing registered voters per precinct between the 6 April 2021
consolidated election (the last under the old fabric) and the 8 November 2022
General (the first under the new one), ordinary drift across the county runs
-53 to +8. Three precincts move by hundreds:

    TAYLORVILLE #4   1,397 -> 993     -404
    TAYLORVILLE #5   1,337 -> 1,008   -329
    TAYLORVILLE #9       — ->  597     new
    PANA #4            647 -> 1,107   +460   (PANA #5, 535, retired)
    SOUTH FORK #2      462 ->  887    +425   (SOUTH FORK #3, 476, retired)

Taylorville #9 was carved out of Taylorville #4 and #5 and out of nothing
else: every other Taylorville precinct moves inside the countywide drift band
(#1 -35, #2 -49, #3 +3, #6 -15, #7 -45, #8 -39). Both parents are District 2
and so is #9, so no district line moved, and census TAYLORVILLE 4 and 5 are
wholly District 2 whatever the internal line between #4, #5 and #9 now is. The
same table shows the other two changes are merges INSIDE one district — Pana 5
into Pana 4, both District 4; South Fork 3 into South Fork 2, both District 2 —
so neither can move a line either.

TWO THINGS THE RECORD SAID THAT ARE WRONG, corrected here rather than carried:
its parenthetical "(an eight-member board)" — the plan document states 16
members, four districts of four, and the 2022 General ran a 4-year and a
2-year contest in each district, which is the staggering; and its finding that
the canvass archive's "download handler returns 404 for the pageid/mid pair
its own page advertises" — the handler takes a per-row fileid as well, and all
60 canvasses download with it.

WHERE EACH CLAIM IS GATED, since they are not all in one place. That every
current precinct is in exactly one district, and that the one precinct created
after the census was carved from precincts of a single district, are checked in
derive_composition. That every RETIRED voting district rode the right precinct is
checked by the population gate instead: sending Pana 5 to a District 2 precinct
moves 902 people and the four sums stop matching the county's map. The county's
own four figures are what make that gate worth having.

THE CARD SHOWS THE COUNTY'S CURRENT PRECINCTS, NOT THE CENSUS NAMES. The first
draft shipped the dissolve's own inputs in the reader's row, which named South
Fork 3 and Pana 5 — retired in 2022 — and omitted Taylorville 9 altogether. Both
lists ship: `precincts` is what a reader is in today, `dissolvedFrom` is what the
polygon is made of.

THE ROSTER DOES NOT SHIP. christiancountyil.gov sits behind a Cloudflare
managed challenge as of 2026-09-15 (HTTP 403, 58 characters of visible text,
to the districtry token on requests, to the stdlib client, and to three pinned
browser strings alike), which is an access control and is not worked around.
The county's board page named only its Chairman and Vice Chairman when it was
last readable, so no member roster existed to scrape even before the challenge.
The cards name your district, its precincts and the board's office (from the state's
County Officers Book, via the concept's own officeFallback), and link the board.
Gap christian-county-board-roster.
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
                             "christian-county-board-districts.json")

COUNTY_FIPS = "021"
COUNTY_POP_2020 = 34032
EXPECTED_VTDS = 30              # the 2020 fabric the plan was drawn on
SEATS_PER_DISTRICT = 4          # sixteen members, four per district, staggered

PLAN_URL = ("https://www.christiancountyil.gov/wp-content/uploads/"
            "Reapportionment-Plan-on-File-with-County-Clerk-2021.pdf")
RESULTS_URL = "https://il-christian.pollresults.net/"
ARCHIVE_URL = "https://il-christian.accessliberty.com/pastelections.aspx"
BOARD_URL = "https://www.christiancountyil.gov/county-board/"

SOURCE_LABEL = ("Census 2020 voting districts dissolved per Christian County's "
                "own 2021 County Board District and Precinct Map, corroborated "
                "by its certified 2022 and 2024 General canvasses and its "
                "certified 2026 General Primary")

# THE COMPOSITION, as the county's own certified elections state it: which of
# its TWENTY-NINE CURRENT precincts vote in each board district. The 8 November
# 2022 and 5 November 2024 Generals and the 2026 General Primary all give
# exactly this, with no precinct in two districts. Spelling is the county's.
CURRENT_PRECINCTS = {
    "1": ("ASSUMPTION", "LOCUST", "MAY", "MOSQUITO", "MT AUBURN",
          "PRAIRIETON", "STONINGTON"),
    "2": ("BUCKHART", "SOUTH FORK #1", "SOUTH FORK #2",
          "TAYLORVILLE #4", "TAYLORVILLE #5", "TAYLORVILLE #9"),
    "3": ("JOHNSON", "TAYLORVILLE #1", "TAYLORVILLE #2", "TAYLORVILLE #3",
          "TAYLORVILLE #6", "TAYLORVILLE #7", "TAYLORVILLE #8"),
    "4": ("BEAR CREEK", "GREENWOOD", "KING", "PANA #1", "PANA #2", "PANA #3",
          "PANA #4", "RICKS", "ROSAMOND"),
}

# The 2020 -> 2022 fabric change, each entry read off the county's own
# registration counts (see the docstring). A voting district the county
# retired, and the current precinct it merged into.
RETIRED_VTDS = {"PANA 5": "PANA #4", "SOUTH FORK 3": "SOUTH FORK #2"}
# A current precinct with no voting district of its own, and the voting
# districts it was carved out of.
NEW_PRECINCTS = {"TAYLORVILLE #9": ("TAYLORVILLE 4", "TAYLORVILLE 5")}

# The county's OWN four district populations, printed in the legend of its 2021
# map. The dissolve must reproduce all four exactly: this is what ties the
# composition to the county's plan rather than to our reading of its canvasses.
PUBLISHED_POP = {"1": 8918, "2": 8210, "3": 8441, "4": 8463}

# A mis-assignment moves a whole voting district between districts; Christian's
# smallest is 198 people and its largest 3,137, so any such error lands well
# past this ceiling. The county's own plan measures 0.048 (District 1).
BALANCE_DEV_MAX = 0.30
MAX_OVERLAP_M2 = 1.0
MIN_COVERED = 0.9999

fail = make_fail("christian-boundaries")


def census_name(precinct):
    """The county writes PANA #4 where the census writes PANA 4."""
    return precinct.replace("#", "").replace("  ", " ").strip()


def derive_composition(fail):
    """The Census 2020 voting districts each board district is made of, DERIVED
    from the county's current precincts rather than kept as a second hand-typed
    table that could disagree with the first.

    A current precinct contributes the voting district of the same name, except
    one the county created after the census, which has none. A voting district
    the county retired rides the district of the precinct it merged into. Every
    such change must land INSIDE one board district: a merge or a split that
    crosses a district line means the county redrew the plan, and then no
    dissolve of the 2020 fabric can express it."""
    where, seen = {}, []
    for dnum, names in CURRENT_PRECINCTS.items():
        for precinct in names:
            seen.append(precinct)
            where[precinct] = dnum
    dupes = sorted({p for p in seen if seen.count(p) > 1})
    if dupes:
        fail("precinct(s) %s appear in more than one district — the county's "
             "canvasses report each exactly once" % ", ".join(dupes))

    by_census = {census_name(p): p for p in where}
    composition = {d: [] for d in CURRENT_PRECINCTS}
    for precinct, dnum in where.items():
        if precinct in NEW_PRECINCTS:
            parents = NEW_PRECINCTS[precinct]
            parent_districts = set()
            for parent in parents:
                owner = by_census.get(parent)
                if owner is None:
                    fail("%s was carved from %s, which is not one of the county's "
                         "current precincts" % (precinct, parent))
                parent_districts.add(where[owner])
            if parent_districts != {dnum}:
                fail("%s sits in district %s but was carved from precincts in "
                     "district(s) %s — that split crosses a district line"
                     % (precinct, dnum, ", ".join(sorted(parent_districts))))
            continue
        composition[dnum].append(census_name(precinct))
    for retired, into in RETIRED_VTDS.items():
        if into not in where:
            fail("%s retired into %s, which is not one of the county's current "
                 "precincts" % (retired, into))
        composition[where[into]].append(retired)
    return {d: tuple(sorted(v)) for d, v in composition.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file matches a fresh build")
    args = ap.parse_args()

    from shapely.geometry import shape, mapping     # noqa: E402  (heavy, function-local)
    from shapely.ops import unary_union, transform  # noqa: E402

    COMPOSITION = derive_composition(fail)

    claimed = [n for names in COMPOSITION.values() for n in names]
    if len(claimed) != EXPECTED_VTDS:
        fail("the composition names %d voting districts, expected %d"
             % (len(claimed), EXPECTED_VTDS))

    vtds = V.fetch_vtds(COUNTY_FIPS, shape, fail)
    if len(vtds) != EXPECTED_VTDS:
        fail("the census voting-district layer carries %d Christian features, "
             "expected %d — the 2020 fabric this plan was drawn on has moved "
             "under us" % (len(vtds), EXPECTED_VTDS))
    county_geom, county_pop = V.fetch_county(COUNTY_FIPS, shape, fail)
    if county_pop != COUNTY_POP_2020:
        fail("census county population is %d, expected %d"
             % (county_pop, COUNTY_POP_2020))
    # The county re-precincted, so check_fabric (name-for-name against the
    # CURRENT precinct list) is the wrong test and would fail correctly. What
    # still applies is the half that tests the fabric: the thirty must tile the
    # county. check_partition below supplies the other half.
    V.check_fabric_composed(vtds, county_pop, fail)
    where = V.check_partition(COMPOSITION, vtds, fail)

    districts, pops = V.dissolve(COMPOSITION, vtds, unary_union)
    for dnum in sorted(PUBLISHED_POP):
        if pops[dnum] != PUBLISHED_POP[dnum]:
            fail("district %s dissolves to %d people; Christian County's own "
                 "2021 plan map publishes %d. The composition no longer "
                 "reproduces the county's plan — re-read the map before "
                 "shipping" % (dnum, pops[dnum], PUBLISHED_POP[dnum]))

    ideal = county_pop / float(len(COMPOSITION))
    worst = max(((abs(pops[d] - ideal) / ideal), d) for d in pops)
    if worst[0] > BALANCE_DEV_MAX:
        fail("district %s deviates %.1f%% from the per-district ideal (ceiling "
             "%.1f%%) — that is a mis-assignment, not an apportionment"
             % (worst[1], 100 * worst[0], 100 * BALANCE_DEV_MAX))
    overlap, covered = V.check_tiling(districts, county_geom, transform,
                                      MAX_OVERLAP_M2, MIN_COVERED, unary_union, fail)

    district_features = []
    for dnum in sorted(COMPOSITION, key=int):
        district_features.append({
            "type": "Feature",
            "properties": {"district": dnum, "name": "District %s" % dnum,
                           # What a reader is in TODAY, in the county's own
                           # spelling — never the census names, three of which
                           # name precincts the county no longer runs.
                           "precincts": [V.title_case(n) for n in CURRENT_PRECINCTS[dnum]],
                           # What the polygon is a dissolve OF, for provenance.
                           "dissolvedFrom": [V.title_case(n) for n in COMPOSITION[dnum]],
                           "pop2020": pops[dnum], "seats": SEATS_PER_DISTRICT},
            "geometry": V.round_geom(districts[dnum], mapping),
        })
    payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL, "planUrl": PLAN_URL, "boardUrl": BOARD_URL,
            "resultsUrl": RESULTS_URL, "archiveUrl": ARCHIVE_URL,
            "canvass": ("Composition from Christian County's own 2021 County "
                        "Board District and Precinct Map, whose four published "
                        "district populations this dissolve reproduces exactly "
                        "(8,918 / 8,210 / 8,441 / 8,463 of 34,032). Three "
                        "certified elections independently partition the "
                        "county's 29 current precincts into the same four "
                        "districts with no precinct in two of them: the 2022 "
                        "and 2024 Generals and the 2026 General Primary."),
            "note": ("Four districts electing FOUR members each (16 seats) on "
                     "staggered terms — the 2022 General ran a 4-year and a "
                     "2-year contest in every district. Each district lists "
                     "the county's CURRENT precincts, as its certified returns "
                     "name them; `dissolvedFrom` lists the thirty Census 2020 "
                     "voting districts the polygon is a dissolve of, which is "
                     "the fabric the plan was drawn on. The two differ because "
                     "the county re-precincted to 29 after the census, and all "
                     "three changes fell inside a single district, so no "
                     "district boundary moved. Members are not named: the "
                     "county's board page lists only its Chairman and Vice "
                     "Chairman, and the county's site is behind a managed "
                     "challenge."),
        },
        "features": district_features,
    }

    V.verify_point_in_rings(COMPOSITION, vtds, district_features, point_in_rings, fail)

    print("christian-boundaries: %d voting districts -> %d board districts of "
          "%d seats" % (EXPECTED_VTDS, len(COMPOSITION), SEATS_PER_DISTRICT))
    print("  populations: %s (total %d = census POP100) — all four match the "
          "county's own 2021 plan map; worst deviation %.2f%% in district %s"
          % (", ".join("D%s=%d" % (d, pops[d]) for d in sorted(pops, key=int)),
             county_pop, 100 * worst[0], worst[1]))
    print("  tiling: overlap %.2f m2; %.4f%% of the county covered"
          % (overlap, 100 * covered))
    V.write_or_check([(OUT_DISTRICTS, V.dumps(payload))],
                     args.check, REPO_ROOT, fail, "christian")


if __name__ == "__main__":
    main()
