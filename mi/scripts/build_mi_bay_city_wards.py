#!/usr/bin/env python3
"""Bay City's nine commission wards — from BAY COUNTY's ward map.

Bay City elects nine commissioners, one per ward. Three publishers draw the
wards:

  the city      `Wards` (BayCityGIS_COBC), 9 features, last edited 2023-12-12
  Bay County    `Where_Do_I_Vote__WFL1` layer 6 "City Wards" (BayCoGIS),
                9 features named "Bay City Ward 1".."9", last edited
                2026-04-29, licenseInfo EMPTY                 <- what this reads
  the state     the 2026 voting precincts, one precinct per ward

THE CLERK'S ANSWER. On 2026-10-22 the City Clerk wrote that the ward lines
have not changed and that the current ward map is the one on Bay County's GIS
map. That is why the county's layer is read rather than the city's own: the
clerk named it, it was edited this year, and it matches the county's precinct
layer to within 76 m2 (measured 2026-10-22). The city's and the county's maps
put every resident in the same ward; they differ only along the river.

WHY THE "residents" RULE. Measured 2026-10-22 against the state's 2026
precincts, the county's wards agree on 98.408% of 4,000 points where both draw
a ward ("lines") — below the 99% floor, which is not moved. Every one of those
differences holds nobody: 70% of the differing ground is the Saginaw River in
the Census Bureau's own water layer, and the rest is riverbank and
Middleground Island (about 81,000 m2 that the county puts in Ward 4 and the
state's precincts in Ward 3). Counted over every populated Census 2020 block,
32,649 people are told the same ward by both maps and 0 a different one; 12
people sit inside the county's Ward 1 and outside the state's Bay City
precincts, which is the outer edge and is held by the tiling gate. So the
gate here asks the reader's question — is a person at home told the right
ward — and the area figures still print on every run.

THE COST, STATED. A click on the river or on Middleground Island can name a
different ward from the one the state's precinct map would give. Nobody lives
there.

THE LICENCE. The county states no terms on the item (licenseInfo empty). An
empty licence ships under the operator's rule; it is re-read every run and the
build fails if terms appear, so a person reads them before the next rebuild.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mi_ward_common as wc  # noqa: E402

COUNTY_ORG = "https://services7.arcgis.com/NsdAMAHBh4C0qHfJ/arcgis/rest/services"
SERVICE = COUNTY_ORG + "/Where_Do_I_Vote__WFL1/FeatureServer/6"
ITEM = "7cb7d9eefc9f423bb8be6ace050bcc44"
ITEM_URL = "https://www.arcgis.com/sharing/rest/content/items/%s?f=json" % ITEM

CFG = {
    "name": "Bay City",
    "slug": "bay-city",
    "out_file": "mi-bay-city-wards.json",
    "place_geoid": "2606020",
    "place_name": "Bay City city",
    # Bay County is 017. "Bay City" alone would not be safe statewide.
    "state_where": "Jurisdiction_Name = 'Bay City' AND COUNTYFIPS = '017'",
    "expect_wards": tuple(str(n) for n in range(1, 10)),
    "expect_state": {str(n): 1 for n in range(1, 10)},
    "agreement": "residents",
    "agreement_why": ("the county's wards and the state's precincts divide the Saginaw "
                      "River and the empty Middleground Island differently; the clerk "
                      "confirmed on 2026-10-22 that the lines have not changed and that "
                      "the county's map is current"),
    "robots_urls": (SERVICE + "/query", ITEM_URL),
    "min_blocks": 1000,
}


def assert_no_terms():
    terms = wc.item_terms(ITEM)
    if terms:
        wc.fail(CFG, "Bay County now states terms on its ward map: %r. Read them before "
                     "rebuilding." % terms[:300])
    print("  licence: the county still states no terms on this item")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    args = ap.parse_args()
    if args.check:
        wc.check_main(CFG)
        return

    print("reading robots.txt for every host this build fetches…")
    wc.require_robots(CFG)
    print("re-reading the county's stated terms…")
    assert_no_terms()
    print("fetching Bay County's city-ward layer…")
    wards = wc.esri(SERVICE, {"where": "NAME LIKE 'Bay City Ward %'", "outFields": "NAME"})
    key = lambda p: wc.ward_number(p.get("NAME") if "NAME" in p else p.get("WARD"))  # noqa: E731
    wc.gate_and_write(CFG, wards, key)


if __name__ == "__main__":
    main()
