#!/usr/bin/env python3
"""Muskegon's four commission wards — from MUSKEGON COUNTY's map server.

Muskegon elects one city commissioner from each of four wards and two at
large. The city runs no map service; the county's GIS publishes the city's
wards in a service built for exactly this question — "A web application that
helps identify your City of Muskegon Ward Commissioner"
(City_of_Muskegon/City_of_Muskegon_Commission_Districts, layer 2, "Wards"), one
polygon per ward, named "City of Muskegon, Ward N". The operator ruled on
2026-09-29 that a county's published map may be the source for a city's wards.

ANOTHER COUNTY SERVICE SAYS "For use by Muskegon County GIS Only", and this
build does not read it. That line is on a different service; this one states no
terms and describes itself as a public lookup. The build refuses if this
service starts stating any text beyond that description.

THE LINES AGREE AND THE OUTER EDGE DOES NOT. Against the state's own 2026
precinct fabric, 99.7% of the points both maps cover are in the same ward
(measured 2026-10-15); the rest of the difference is the city's outer edge,
so this city gates on the "lines" rule (mi_ward_common.py) with the edge held
by the Census tiling gate, the rule recommended to the operator on 2026-10-15.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mi_ward_common as wc  # noqa: E402

SERVICE = ("https://maps.muskegoncountygis.com/arcgis/rest/services/City_of_Muskegon/"
           "City_of_Muskegon_Commission_Districts/MapServer")
LAYER = SERVICE + "/2"
EXPECT_LAYER_NAME = "Wards"
EXPECT_TEXT = ["serviceDescription: A web application that helps identify your City of "
               "Muskegon Ward Commissioner"]

CFG = {
    "name": "Muskegon",
    "slug": "muskegon",
    "out_file": "mi-muskegon-wards.json",
    "place_geoid": "2656320",
    "place_name": "Muskegon city",
    "state_where": "Jurisdiction_Name = 'Muskegon' AND COUNTYFIPS = '121'",
    "expect_wards": ("1", "2", "3", "4"),
    "expect_state": {"1": 2, "2": 2, "3": 3, "4": 2},
    "agreement": "lines",
    "robots_urls": (LAYER,),
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
    print("re-checking what the county states on its service…")
    stated = wc.service_text(SERVICE) + wc.service_text(LAYER)
    if stated != EXPECT_TEXT:
        wc.fail(CFG, "the service now states %r (expected only %r) — read it before "
                     "republishing" % (stated, EXPECT_TEXT))
    print("  terms: none stated; %s" % stated)
    meta = wc.curl_json(LAYER + "?f=json", 120)
    if meta.get("name") != EXPECT_LAYER_NAME:
        wc.fail(CFG, "layer 2 is now %r, expected %r" % (meta.get("name"), EXPECT_LAYER_NAME))
    print("fetching the county's City of Muskegon wards…")
    wards = wc.esri(LAYER, {"where": "Ward_Name LIKE 'City of Muskegon, Ward %'",
                            "outFields": "Ward_Name"})
    key = lambda p: wc.ward_number(p.get("Ward_Name") or p.get("WARD"))  # noqa: E731
    wc.gate_and_write(CFG, wards, key)


if __name__ == "__main__":
    main()
