#!/usr/bin/env python3
"""
Build ne/data/app/ne-city-wards.json: the 30 council wards and districts of
the six Nebraska cities of 25,000 people or more whose wards elect their own
members, each read from the map the city, or its county, publishes.

    python3 ne/scripts/build_ne_city_wards.py            # fetch, check, write
    python3 ne/scripts/build_ne_city_wards.py --check    # offline
    python3 ne/scripts/build_ne_city_wards.py --watch    # has any city's map changed?

The work is scripts/city_ward_maps.py; this file says where each city's map
is and how to read it. WHICH cities are drawn is read from the seats file the
council roster is built from (ne/data/source/ne-city-council-seats.json):
every city with a seat its own ward's voters elect. Kearney, the seventh city
of 25,000 or more, elects every seat by the whole city.

DRAWN, read on 2026-11-28: Omaha 7 districts (the map Douglas County's GIS
office keeps for the city, which says the City Council approved the plan on
21 December 2021), Lincoln 4 districts (the City of Lincoln's own map server;
five records, District 2 in two), Bellevue 6 wards (Sarpy County's election
map, whose City Ward layer draws the wards of every Sarpy County city and
names the city in a field, so it is asked for Bellevue's alone), Grand Island
5 wards, Fremont 4 wards and Hastings 4 wards (each the city's own map in
ArcGIS Online). Each ward's card says whose map it is drawn from.

IS EACH THE CURRENT MAP. Measured against the Census Bureau's 2020 blocks
(each populated block's internal point inside the city's current Census
outline), as the spread between the largest and smallest ward as a share of
an equal one: Lincoln 0.7%, Fremont 2.5%, Bellevue 3.4%, Hastings 5.4%, Grand
Island 7.0% and Omaha 11.0%. Omaha's plan is the one its layer says was
approved on 21 December 2021, after the 2020 census; inside the city's
outline as the Census maps it today its seven districts hold 67,184 to
74,910 people. That each map is the one in force is an inference from those
figures and, for Omaha, the layer's own statement; each layer's member fields
also name the members the city's own page names.

FOUR MAPS DRAW SOME LINES TWICE. Lincoln's, Bellevue's, Grand Island's and
Fremont's wards overlap one another in thin strips along shared lines, where
two neighbours were drawn a few metres apart: measured 2026-11-28 as twice the
radius of the largest circle inside each strip, at most 0.8 m (Lincoln),
1.0 m (Bellevue), 1.3 m (Grand Island) and 4.5 m (Fremont, whose largest strip
covers 2,852 m2 between Wards 1 and 2). Each strip is drawn in the ward that
sorts first and cut from the other (city_ward_maps.trim_overlaps), so a point
there answers one ward, and the build stops if a strip grows wider than the
source's `overlap_max_m`. Omaha's and Hastings's maps overlap nowhere.

EACH MAP IS A MAP OF ITS CITY, measured on 2026-11-28 against the Census
outline of the place: the share of the place its wards cover, and the share
of the wards outside the place. Each source's floor and ceiling below are
five points from what was measured. Fremont's wards cover 88.9% of the
city's Census outline and leave 11 of its 2020 people in no ward; Bellevue's
leave 96. Why each leaves that ground out was not established; a point there
answers no ward.

PRIVACY. The builder asks each layer for its ward field and nothing else.
Every one carries more beside each ward: the members' names (all six), each
member's e-mail address and photograph (Grand Island), the mayor's name
(Bellevue, Fremont), and fields called ADDRESS1, PHONEHOME1, EMAIL1 and the
like (Hastings), which were empty when read.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
ne-municipal-officeholders): no state office publishes Nebraska's city wards;
the six maps carry the ward number under five different field names; and
only Omaha's says when its plan was adopted.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, HERE)

import build_ne_city_councils as councils  # noqa: E402
import city_ward_maps as cwm  # noqa: E402

NUMBER = r"([1-9][0-9]?)"

# (covers, outside) floors and ceilings, five points from the shares measured
# on 2026-11-28 that each comment gives.
SOURCES = (
    cwm.Source("3137000",  # Omaha: covers 99.8%, 0.3% outside
               "https://dcgis.org/server/rest/services/Hosted/"
               "Omaha_City_Council_Districts_(source)_view/FeatureServer/0",
               "district", NUMBER, records=7, covers=94.8, outside=5.3,
               drawn_from="the map Douglas County's GIS office keeps for the City of Omaha"),
    cwm.Source("3128000",  # Lincoln: 99.9%, 0.6%; 5 records for 4 districts
               "https://gis.lincoln.ne.gov/public/rest/services/Planning/Elections/MapServer/0",
               "CCDIST", NUMBER, records=5, parts=1, overlap_max_m=2.0, covers=94.9, outside=5.6,
               drawn_from="the City of Lincoln's own map"),
    cwm.Source("3103950",  # Bellevue: 96.9%, 1.8%
               "https://services.arcgis.com/OiG7dbwhQEWoy77N/ArcGIS/rest/services/"
               "ElectionAdmin_BV_vw/FeatureServer/8",
               "DISTRICTID", NUMBER, where="CITY='Bellevue'", records=6,
               overlap_max_m=2.0, covers=91.9,
               outside=6.8, drawn_from="Sarpy County's election map"),
    cwm.Source("3119595",  # Grand Island: 99.9%, 0.5%
               "https://services3.arcgis.com/H1fomogcAqX4720J/ArcGIS/rest/services/"
               "PV1_DistrictManagement/FeatureServer/5",
               "DISTRICTID", NUMBER, records=5, overlap_max_m=2.0, covers=94.9, outside=5.5,
               drawn_from="the City of Grand Island's own map"),
    cwm.Source("3117670",  # Fremont: 88.9%, 1.5%
               "https://services5.arcgis.com/6VKlIQXg1rgWny7H/arcgis/rest/services/"
               "Wards/FeatureServer/1",
               "WardID", NUMBER, records=4, overlap_max_m=5.0, covers=83.9, outside=6.5,
               drawn_from="the City of Fremont's own map"),
    cwm.Source("3121415",  # Hastings: 98.6%, 0.4%
               "https://services1.arcgis.com/TYPEVuuXULssEXx8/arcgis/rest/services/"
               "Voting_Wards/FeatureServer/0",
               "WARD", NUMBER, records=4, covers=93.6, outside=5.4,
               drawn_from="the City of Hastings's own map"),
)

SPEC = cwm.Spec(
    tag="ne",
    label="build_ne_city_wards",
    user_agent="districtry/1.0 (+https://districtry.com/ne/)",
    seats_file="ne-city-council-seats.json",
    out_file="ne-city-wards.json",
    sources=SOURCES,
    undrawn=councils.SPEC.undrawn,
    card_claims=(
        "the map its city publishes",
    ),
    # Each point is more than 500 metres inside one ward of the city's map and
    # inside the Census's outline of the city (TIGERweb, read 2026-11-28), and
    # its ward is the answer that city's map gave when asked about the point
    # the same day.
    inside=(
        (-96.12166, 41.29258, "3137000-7", "a point in Omaha"),
        (-96.73911, 40.84607, "3128000-4", "a point in Lincoln"),
        (-95.92878, 41.14965, "3103950-6", "a point in Bellevue, drawn from Sarpy County's map"),
        (-98.36972, 40.92775, "3119595-5", "a point in Grand Island"),
        (-96.47119, 41.43090, "3117670-4", "a point in Fremont"),
        (-98.37691, 40.59875, "3121415-4", "a point in Hastings"),
    ),
    # The Census's internal point of the place (TIGERweb, read 2026-11-28).
    outside=(
        (-99.08231, 40.70175, "a point in Kearney, which elects every seat by the whole "
                              "city"),
    ),
)

if __name__ == "__main__":
    cwm.main(SPEC, __doc__)
