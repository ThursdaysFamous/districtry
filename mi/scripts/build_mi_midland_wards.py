#!/usr/bin/env python3
"""Midland's five council wards — from the city's own map server.

Midland elects one council member from each of five wards. The city's ArcGIS
Server publishes "Council Wards" (Miscellaneous/MapServer, layer 7): its ten
voting precincts, each carrying WARD. Dissolving them by WARD gives the wards.

ONLY THE WARD NUMBER IS READ. The same layer carries a councilman's name, home
address, telephone and photograph per precinct, and those are not read: a
name field on a map layer is not a roster (Michigan's county-commissioner
refusal), and nobody's home address ships. The card's members come from the
city's council page (mi-municipal-officials.json), read weekly.

THE LINES AGREE AND THE OUTER EDGE DOES NOT. Against the state's own 2026
precinct fabric the city's precincts put every sampled point that both maps
cover in the same ward. What differs is the city's edge: land the city has
annexed is in the state's precincts and not yet in this layer, about 1.5% of
the ground either map covers (measured 2026-10-15). So this city gates on the
"lines" rule (mi_ward_common.py), with the edge held by the Census tiling
gate, the rule recommended to the operator on 2026-10-15. A reader on that
annexed ground is told no ward rather than a wrong one.

TERMS. The service's copyright line reads "City of Midland Michigan", which is
attribution and states no restriction; the build refuses if it changes.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mi_ward_common as wc  # noqa: E402

SERVICE = "https://arcgis1.midland-mi.org/arcgis/rest/services/Miscellaneous/MapServer"
LAYER = SERVICE + "/7"
EXPECT_LAYER_NAME = "Council Wards"
EXPECT_TEXT = ["copyrightText: City of Midland Michigan"]

CFG = {
    "name": "Midland",
    "slug": "midland",
    "out_file": "mi-midland-wards.json",
    "place_geoid": "2653780",
    "place_name": "Midland city",
    # Midland city lies in Midland County (111) and a sliver of Bay (017).
    "state_where": "Jurisdiction_Name = 'Midland' AND COUNTYFIPS IN ('111','017')",
    "expect_wards": ("1", "2", "3", "4", "5"),
    "expect_state": {"1": 2, "2": 2, "3": 2, "4": 2, "5": 2},
    "agreement": "lines",
    "robots_urls": (LAYER,),
    "min_blocks": 500,
}
EXPECT_SOURCE = {"1": 2, "2": 2, "3": 2, "4": 2, "5": 2}


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
    print("re-checking what the city states on its service…")
    stated = wc.service_text(SERVICE) + wc.service_text(LAYER)
    if stated != EXPECT_TEXT:
        wc.fail(CFG, "the service now states %r (expected only %r) — read it before "
                     "republishing" % (stated, EXPECT_TEXT))
    print("  terms: %s" % stated)
    meta = wc.curl_json(LAYER + "?f=json", 120)
    if meta.get("name") != EXPECT_LAYER_NAME:
        wc.fail(CFG, "layer 7 is now %r, expected %r — the city has republished its "
                     "service and the layer must be found again"
                % (meta.get("name"), EXPECT_LAYER_NAME))
    print("fetching the city's precincts…")
    precincts = wc.esri(LAYER, {"where": "1=1", "outFields": "WARD,PRECINCT"})
    key = lambda p: wc.ward_number(p.get("WARD"))  # noqa: E731
    counts = wc.counts_by(precincts, key)
    print("  city: %d precincts, per ward %s" % (len(precincts), counts))
    if counts != EXPECT_SOURCE:
        wc.fail(CFG, "the city assigns %s precincts per ward, expected %s"
                % (counts, EXPECT_SOURCE))
    wards = wc.dissolve(CFG, precincts, key)
    wc.gate_and_write(CFG, wards, key)


if __name__ == "__main__":
    main()
