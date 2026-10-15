#!/usr/bin/env python3
"""Pontiac's six council districts — from OAKLAND COUNTY's 2026 layer.

Pontiac elects one council member from each of six districts and a council
president at large. Oakland County's GIS publishes the 2026 districts as the
public item "Council Districts" (snippet: "City Council districts 2026 for the
City of Pontiac", access information "City of Pontiac"), whose service is
named Adult_Use_Marihuana_Overlay_District because the county built it for
licensing review; the districts themselves "originate from official City of
Pontiac zoning amendments", in the item's own words, and carry the district in
a field called `Zoning` ("District 1".."District 6"). The operator ruled on
2026-09-29 that a county's published map may be the source for a city's wards.

THE CITY'S OWN SEVEN-DISTRICT LAYER IS THE OLD PLAN and is not read: it agrees
with the state's 2026 precincts on 45% of points (measured 2026-10-15).

ONLY THE DISTRICT IS READ. The layer carries a council member's name per
district (`NAME2`) and demographic shares; neither is read. The card's members
come from the city's council page (mi-municipal-officials.json), read weekly.

THE LINES AGREE AND THE OUTER EDGE DOES NOT. Against the state's own 2026
precinct fabric, 99.75% of the points both maps cover are in the same district
(measured 2026-10-15); the county's layer runs about 0.3 km² past the city's
edge. So this city gates on the "lines" rule (mi_ward_common.py), with the
edge held by the Census tiling gate, the rule recommended to the operator on
2026-10-15.

TERMS. The item's licence field is a disclaimer, not a restriction: "The City
of Pontiac retains authority over City Council districts. Data is
informational and should not substitute for official ordinance verification."
It is carried and quoted, the Grand Rapids precedent, and the card says where
the lines come from. The build refuses if that text changes.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mi_ward_common as wc  # noqa: E402

SERVICE = ("https://services1.arcgis.com/GE4Idg9FL97XBa3P/arcgis/rest/services/"
           "Adult_Use_Marihuana_Overlay_District/FeatureServer")
LAYER = SERVICE + "/0"
ITEM_ID = "162981d60bb442928bcad4b1b2af8e3a"
EXPECT_TITLE = "Council Districts"
EXPECT_TERMS = ("The City of Pontiac retains authority over City Council districts. Data is "
                "informational and should not substitute for official ordinance verification.")

CFG = {
    "name": "Pontiac",
    "slug": "pontiac",
    "out_file": "mi-pontiac-wards.json",
    "place_geoid": "2665440",
    "place_name": "Pontiac city",
    "state_where": "Jurisdiction_Name = 'Pontiac' AND COUNTYFIPS = '125'",
    "expect_wards": ("1", "2", "3", "4", "5", "6"),
    "expect_state": {"1": 3, "2": 3, "3": 2, "4": 2, "5": 2, "6": 2},
    "agreement": "lines",
    "robots_urls": (LAYER, "https://www.arcgis.com/sharing/rest/content/items/" + ITEM_ID),
    "min_blocks": 500,
}


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
    print("re-checking the item and its stated terms…")
    root = wc.curl_json(SERVICE + "?f=json", 120)
    if root.get("serviceItemId") != ITEM_ID:
        wc.fail(CFG, "the service now belongs to item %r, expected %s"
                % (root.get("serviceItemId"), ITEM_ID))
    item = wc.curl_json("https://www.arcgis.com/sharing/rest/content/items/%s?f=json"
                        % ITEM_ID, 120)
    if item.get("title") != EXPECT_TITLE:
        wc.fail(CFG, "the item is now titled %r, expected %r" % (item.get("title"), EXPECT_TITLE))
    terms = wc.item_terms(ITEM_ID)
    if terms != EXPECT_TERMS:
        wc.fail(CFG, "the item's stated terms changed to %r — read them before "
                     "republishing" % terms)
    print("  terms: %s" % terms)
    print("fetching the county's Pontiac council districts…")
    wards = wc.esri(LAYER, {"where": "1=1", "outFields": "Zoning"})
    key = lambda p: wc.ward_number(p.get("Zoning") or p.get("WARD"))  # noqa: E731
    wc.gate_and_write(CFG, wards, key)


if __name__ == "__main__":
    main()
