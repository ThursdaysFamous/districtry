#!/usr/bin/env python3
"""
Build ok/data/app/ok-city-wards.json: the 56 council wards and districts of
the nine Oklahoma cities above 25,000 people whose wards elect their own
members and whose maps this project may draw, each read from the map its
city publishes.

    python3 ok/scripts/build_ok_city_wards.py            # fetch, check, write
    python3 ok/scripts/build_ok_city_wards.py --check    # offline
    python3 ok/scripts/build_ok_city_wards.py --watch    # has any city's map changed?

The work is scripts/city_ward_maps.py; this file says where each city's map
is and how to read it. WHICH cities are drawn is read from the seats file the
council roster is built from (ok/data/source/ok-city-council-seats.json):
every city with a seat its own ward's voters elect, less the two that
ok/scripts/build_ok_city_councils.py declares undrawn.

NOT DRAWN: Lawton and Muskogee elect their members by ward, and
build_ok_city_councils.py says why neither map is drawn (Lawton's published
map does not divide the 2020 census population evenly, so it may not be the
map in force, and Muskogee publishes none this project may read). Broken
Arrow, Owasso, Jenks and Edmond tie seats to wards and elect every seat by
the whole city, so a ward there would elect no one of its own, and
Stillwater's council has no wards.

NO STATE OFFICE PUBLISHES THEM. The State Election Board publishes precinct
maps and results, and no map of any city's wards, so each city's map is read
from the city.

WHO PUBLISHES EACH, read on 2026-10-16: all nine cities publish their own,
from their own map servers (Moore, Midwest City, Bartlesville and Shawnee) or
from ArcGIS Online (Oklahoma City, Tulsa, Norman, Enid and Bixby). Each
ward's card says whose map it is drawn from.

IS EACH THE CURRENT MAP. Norman's layer says it was "Updated September 13,
2022 by O-2223-8", an ordinance. Bixby's gives each ward a population, and
for three of its five wards that is exactly the 2020 census count of the
ground the ward covers (the other two differ by 19 and 68 people). Tulsa's
carries the metes-and-bounds description of each of its nine election
districts and was last edited on 29 January 2026; Shawnee's Ward 5 was last
edited on 22 September 2026 and its other wards on 2 July 2026, Bixby's layer
on 26 August 2026, Midwest City's Ward 5 on 2 October 2025 and Enid's layer
on 4 August 2025; Oklahoma City's,
Moore's and Bartlesville's say nothing about when they were drawn. So each
map was measured against the Census Bureau's 2020 blocks inside the city's
current Census outline on 2026-10-16, and each city's wards hold its people
to within 5.3% of an equal share (Oklahoma City 2.0%, Tulsa 2.7%, Norman
5.3%, Moore 0.6%, Midwest City 3.9%, Enid 5.1%, Bartlesville 4.0%, Shawnee
0.9% and Bixby 4.1%). That is what a map drawn on the 2020 census shows, and
it does not prove when a map was drawn, since a city whose people grew
evenly could keep an older map this balanced; that each of the nine is the
map in force is an inference, recorded as one. No city election in Oklahoma
is published as precinct results this project may read (the State Election
Board's results site refuses it), so the precinct test North Carolina's
builder runs is not available here. Lawton's map fails the balance
measurement, which is why it is not drawn.

EACH MAP IS A MAP OF ITS CITY, measured on 2026-10-16 against the Census
outline of the place: the share of the place its wards cover, and the share
of the wards outside the place. Each source's floor and ceiling below are
five points from what was measured, so a few annexed blocks pass and another
city's map, or a county's, does not. Bixby's wards cover 97.5% of the city's
Census outline and leave 14 of its 2020 people in no ward; Tulsa's leave
176, Shawnee's 36, Midwest City's 32, Bartlesville's 8 and Oklahoma City's
5. Why each leaves that ground out was not established. A point there
answers no ward, which is what those maps say.

PRIVACY. The builder asks each layer for its ward field and nothing else.
Six carry more beside each ward: Oklahoma City's, Tulsa's, Moore's, Midwest
City's and Bixby's each member's name (Tulsa's and Moore's in a field for
"Representative Name(s)", beside a district website), and Shawnee's each
commissioner's name and fields called Contact and Photo.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
ok-municipal-officeholders): no state office publishes Oklahoma's city
wards; the nine maps carry the ward number under eight different field
names, Shawnee's in a field named for a state code (STATEFP10); only
Norman's says when it was adopted; Lawton's published map does not divide
the 2020 census population evenly; and Muskogee publishes no map of its
wards this project may read.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, HERE)

import build_ok_city_councils as councils  # noqa: E402
import city_ward_maps as cwm  # noqa: E402

NUMBER = r"([1-9][0-9]?)"

# (covers, outside) floors and ceilings, five points from the shares measured
# on 2026-10-16 that each comment gives.
SOURCES = (
    cwm.Source("4055000",  # Oklahoma City: covers 99.7%, 0.3% outside
               "https://utility.arcgis.com/usrsvcs/servers/666b9654ab104ba7ac49870c66190e9c/"
               "rest/services/OpenData/Government_Boundaries/FeatureServer/2",
               "WARD", NUMBER, records=8, covers=94.7, outside=5.3,
               drawn_from="the City of Oklahoma City's own map"),
    cwm.Source("4075000",  # Tulsa: 99.6%, 0.2%
               "https://services2.arcgis.com/XkZ90iCdbTJ9oNXl/arcgis/rest/services/"
               "Council_Districts/FeatureServer/0",
               "DISTRICTID", NUMBER, records=9, covers=94.6, outside=5.2,
               drawn_from="the City of Tulsa's own map"),
    cwm.Source("4052500",  # Norman: 100.0%, 0.2%
               "https://services.arcgis.com/rt1leD4Hj3sLGHNL/arcgis/rest/services/"
               "Council_Wards/FeatureServer/1",
               "WARDNO", NUMBER, records=8, covers=95.0, outside=5.2,
               drawn_from="the City of Norman's own map"),
    cwm.Source("4049200",  # Moore: 99.9%, 0.1%; the field reads "Ward 1"
               "https://gis.cityofmoore.com/arcgis/rest/services/OpenData/"
               "Government_Services/MapServer/20",
               "NAME", r"Ward ([1-3])", records=3, covers=94.9, outside=5.1,
               drawn_from="the City of Moore's own map"),
    cwm.Source("4048350",  # Midwest City: 99.5%, 0.3%
               "https://maps.midwestcityok.org/arcgis/rest/services/OpenData/CouncilWards/"
               "MapServer/0",
               "Ward", NUMBER, records=6, covers=94.5, outside=5.3,
               drawn_from="the City of Midwest City's own map"),
    cwm.Source("4023950",  # Enid: 99.6%, 0.1%; the field reads "01", and Ward 2 is two records
               "https://services6.arcgis.com/LIvKKeLD11lMmJuJ/arcgis/rest/services/"
               "Ward_Publishing_Doc/FeatureServer/8",
               "WARD_CODE", r"0([1-6])", records=7, parts=1, covers=94.6, outside=5.1,
               drawn_from="the City of Enid's own map"),
    cwm.Source("4004450",  # Bartlesville: 99.7%, 0.4%
               "https://arcgissrv.cityofbartlesville.org/arcgisserver/rest/services/Citymaps/"
               "CityMaps_BvilleGIS/MapServer/32",
               "DIST_ID", NUMBER, records=5, covers=94.7, outside=5.4,
               drawn_from="the City of Bartlesville's own map"),
    cwm.Source("4066800",  # Shawnee: 99.2%, 0.4%; the ward is in a field named STATEFP10
               "https://maps.shawneeok.org/server/rest/services/City_Wards/FeatureServer/0",
               "STATEFP10", NUMBER, records=6, covers=94.2, outside=5.4,
               drawn_from="the City of Shawnee's own map"),
    cwm.Source("4006400",  # Bixby: 97.5%, 0.7%; 11 records for 5 wards
               "https://services6.arcgis.com/TI4WUPORw6hUtDVO/arcgis/rest/services/"
               "City_Council_Wards/FeatureServer/0",
               "Ward", NUMBER, records=11, parts=6, covers=92.5, outside=5.7,
               drawn_from="the City of Bixby's own map"),
)

SPEC = cwm.Spec(
    tag="ok",
    label="build_ok_city_wards",
    user_agent="districtry/1.0 (+https://districtry.com/ok/)",
    seats_file="ok-city-council-seats.json",
    out_file="ok-city-wards.json",
    sources=SOURCES,
    undrawn=councils.SPEC.undrawn,
    card_claims=(
        "the map its city publishes",
    ),
    # Each point is one the Census's place map puts in the place named
    # (TIGERweb, read 2026-10-16), and its ward is the answer that city's map
    # gave the same day; each is more than 250 metres from a ward's edge.
    inside=(
        (-97.50330, 35.49230, "4055000-7", "a point in Oklahoma City"),
        (-95.94000, 36.09500, "4075000-9", "a point in Tulsa, whose wards are called "
                                           "districts"),
        (-97.49000, 35.33000, "4049200-3", "a point in Moore, whose map names each ward "
                                           "\"Ward 3\""),
        (-97.87840, 36.39560, "4023950-5", "a point in Enid, whose map numbers each ward "
                                           "\"05\""),
    ),
    outside=(
        (-97.47810, 35.65280, "a point in Edmond, whose wards elect no one of their own"),
        (-98.39590, 34.60360, "a point in Lawton, whose wards are not drawn yet"),
        (-97.05840, 36.11560, "a point in Stillwater, which elects its whole council by "
                              "the whole city"),
    ),
)

if __name__ == "__main__":
    cwm.main(SPEC, __doc__)
