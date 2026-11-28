#!/usr/bin/env python3
"""
Build nd/data/app/nd-city-wards.json: the seven council wards of Grand
Forks, the one North Dakota city of 25,000 people or more whose wards elect
their own members, read from the map the city publishes.

    python3 nd/scripts/build_nd_city_wards.py            # fetch, check, write
    python3 nd/scripts/build_nd_city_wards.py --check    # offline
    python3 nd/scripts/build_nd_city_wards.py --watch    # has the city's map changed?

The work is scripts/city_ward_maps.py; this file says where the city's map is
and how to read it. WHICH cities are drawn is read from the seats file the
council roster is built from (nd/data/source/nd-city-council-seats.json):
every city with a seat its own ward's voters elect. Fargo, Bismarck, Minot,
West Fargo, Williston and Dickinson elect every seat by the whole city.

THE MAP, read on 2026-11-28: "Wards", layer 45 of the City of Grand Forks GIS
office's OpenDataLayers service in ArcGIS Online, seven records, each naming
its ward's member and the member's page on the city's site, last edited on
2026-11-21. The same office publishes "Approved Ward and Precincts 2022".

IS IT THE CURRENT MAP. Measured against the Census Bureau's 2020 blocks
(each populated block's internal point inside the city's current Census
outline), the seven wards hold 8,243 to 8,764 people, 6.2% apart around an
equal share: what a map drawn on the 2020 census shows. That it is the map
in force is an inference from that and from the city keeping its members'
names on it, recorded as one.

IT IS A MAP OF ITS CITY, measured on 2026-11-28 against the Census outline of
the place: its wards cover 99.4% of the place, and 0.5% of them lie outside
it. The floor and ceiling below are five points from those shares.

PRIVACY. The builder asks the layer for its ward field and nothing else; it
also carries each ward's member's name and the member's page.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
nd-municipal-officeholders): no state office publishes North Dakota's city
wards, and the city's map does not say when its lines were adopted.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, HERE)

import build_nd_city_councils as councils  # noqa: E402
import city_ward_maps as cwm  # noqa: E402

SOURCES = (
    cwm.Source("3832060",  # Grand Forks: covers 99.4%, 0.5% outside
               "https://services5.arcgis.com/tEvkdB384rqq9Ook/arcgis/rest/services/"
               "OpenDataLayers/FeatureServer/45",
               "districtid", r"([1-7])", records=7, covers=94.4, outside=5.5,
               drawn_from="the City of Grand Forks's own map"),
)

SPEC = cwm.Spec(
    tag="nd",
    label="build_nd_city_wards",
    user_agent="districtry/1.0 (+https://districtry.com/nd/)",
    seats_file="nd-city-council-seats.json",
    out_file="nd-city-wards.json",
    sources=SOURCES,
    undrawn=councils.SPEC.undrawn,
    card_claims=(
        "the map its city publishes",
    ),
    # More than 500 metres inside Ward 7 of the city's map and inside the
    # Census's outline of the city (TIGERweb, read 2026-11-28); Ward 7 is the
    # answer the city's map gave when asked about the point the same day.
    inside=(
        (-97.07116, 47.90727, "3832060-7", "a point in Grand Forks"),
    ),
    # The Census's internal point of the place (TIGERweb, read 2026-11-28).
    outside=(
        (-100.76857, 46.81586, "a point in Bismarck, which elects every seat by the whole "
                               "city"),
    ),
)

if __name__ == "__main__":
    cwm.main(SPEC, __doc__)
