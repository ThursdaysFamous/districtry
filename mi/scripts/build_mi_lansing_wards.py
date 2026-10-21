#!/usr/bin/env python3
"""Lansing's four council wards — the CITY's own map, under the city's licence.

Lansing elects eight council members: four by ward and four at large. The
city's ArcGIS org publishes the current plan three times:

  VotingWards   4 features, WARDID 1-4, licenseInfo EMPTY,
                snippet "Wards for the City of Lansing, updated for the 2022
                elections"                                    <- what this reads
  City_Wards    9 features, licenseInfo CC BY-NC 4.0,
                description "City of Lansing wards, as defined in the 2020
                redistricting cycle"
  Wards        10 features, licenseInfo EMPTY

`City_Wards` and `Wards` are not rival plans: they carry ward 2 in four parts
plus two features keyed DT and MR that are not wards at all. `VotingWards` is
the same plan as four whole wards, which is why it is the one read here.

THE LICENCE. An unstated licence is silence, not a grant, and the same
publisher states NonCommercial terms on the same plan one item away, so the
terms that govern Lansing's ward lines are taken to be:

    "This work is licensed under a Creative Commons Attribution-NonCommercial
     4.0 International License."

quoted from the City_Wards item. From 2026-09-05 this script measured the
wards and refused to write them while that question was open. On 2026-10-20
the operator ruled that districtry may use the map with the credit the licence
asks for. So the card and the sources page credit the City of Lansing, name
the licence and link it, and say what was changed (coordinates rounded to six
decimal places; nothing else). The licence clause is re-read EVERY RUN and the
build fails if it has moved in either direction, so a relicence is read by a
person before the next rebuild.

THE THREE GATES (shared with the other cities, mi_ward_common.py)
1. COMPOSITION. Four wards, 1-4, in the city's layer, and 27 precincts
   7/7/6/7 across them in the state's own 2026 precinct fabric.
2. CURRENCY. The city's wards against the state's precincts dissolved by
   their WARD column, at 4,000 points, on the "lines" rule (the operator's
   2026-10-16 edge ruling). Measured 2026-09-05 with this script's earlier
   sampler: 99.893%.
3. TILING. The wards' Census 2020 population against the Census place's.
"""

import argparse
import html as htmllib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mi_ward_common as wc  # noqa: E402

CITY_ORG = "https://services1.arcgis.com/pNPbgWy7hpfFGWoZ/arcgis/rest/services"
SERVICE = CITY_ORG + "/VotingWards/FeatureServer/0"
# The licensed sibling — read only to re-assert the licence clause each run.
LICENCE_ITEM = "59912a33858b4a05b6cd4226aa78dc3a"
LICENCE_URL = "https://www.arcgis.com/sharing/rest/content/items/%s?f=json" % LICENCE_ITEM
LICENCE_CLAUSE = ("This work is licensed under a Creative Commons "
                  "Attribution-NonCommercial 4.0 International License")

CFG = {
    "name": "Lansing",
    "slug": "lansing",
    "out_file": "mi-lansing-wards.json",
    "place_geoid": "2646000",
    "place_name": "Lansing city",
    # Lansing city reaches into Ingham (065), Eaton (045) and Clinton (037).
    # "Lansing Township" is a separate jurisdiction and does not match.
    "state_where": "Jurisdiction_Name = 'Lansing' AND COUNTYFIPS IN ('065','045','037')",
    "expect_wards": ("1", "2", "3", "4"),
    "expect_state": {"1": 7, "2": 7, "3": 6, "4": 7},
    "agreement": "lines",
    "robots_urls": (SERVICE + "/query", LICENCE_URL),
    "min_blocks": 1500,
}


def assert_licence_unchanged():
    """The licence clause is re-read every run, never trusted from this file.

    FLATTEN FIRST. The clause is split across an anchor tag and a styled span,
    and carries a non-breaking space; matching the raw HTML reports a relicence
    that has not happened. (Measured 2026-09-05: the first draft did exactly
    that.)"""
    item = wc.curl_json(LICENCE_URL, 120)
    live = htmllib.unescape(re.sub(r"<[^>]+>", " ", item.get("licenseInfo") or ""))
    live = re.sub(r"\s+", " ", live.replace("\xa0", " ")).strip()
    if LICENCE_CLAUSE not in live:
        wc.fail(CFG, "the city's stated licence has CHANGED. This build records %r, which "
                     "is no longer in the item's licenseInfo. Read the new terms and update "
                     "the card's credit before rebuilding." % LICENCE_CLAUSE)
    print("  licence: the city still states CC BY-NC 4.0 on this plan")


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
    print("re-reading the city's stated licence…")
    assert_licence_unchanged()
    print("fetching the city's ward service…")
    wards = wc.esri(SERVICE, {"where": "1=1", "outFields": "WARDID"})
    key = lambda p: wc.ward_number(p.get("WARDID") if "WARDID" in p else p.get("WARD"))  # noqa: E731
    wc.gate_and_write(CFG, wards, key)


if __name__ == "__main__":
    main()
