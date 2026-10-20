#!/usr/bin/env python3
"""
Build sc/data/app/sc-city-wards.json: the 75 council districts and wards of
the twelve South Carolina cities and towns above 25,000 people whose
councils elect members by district: nine from the place's own map, Sumter's
from an election map and two from the state's copy.

    python3 sc/scripts/build_sc_city_wards.py            # fetch, check, write
    python3 sc/scripts/build_sc_city_wards.py --check    # offline
    python3 sc/scripts/build_sc_city_wards.py --watch    # has any city's map changed?

The work is scripts/city_ward_maps.py; this file says where each place's map
is and how to read it. WHICH places are drawn is read from the seats file the
council roster is built from (sc/data/source/sc-city-council-seats.json):
twelve of the thirteen with a seat their district's own voters elect.
Anderson, the thirteenth, is not drawn, because it publishes its districts
only as pictures in PDF files (sc/scripts/build_sc_city_councils.py, whose
`undrawn` table this reads, and scripts/build_eam_status.py, which records
it); Mount Pleasant, Goose Creek, Myrtle Beach and Bluffton elect every seat
by the whole place, so a reader votes for every seat wherever they live.

A MAP PER PLACE, NOT THE STATE'S. The Revenue and Fiscal Affairs Office
publishes a statewide map of municipal council districts (238 districts in
40 municipalities when read on 2026-10-16), and it draws all twelve. It is
used for two. Measured against the Census Bureau's 2020 blocks inside each
place's current Census outline, the state's copy leaves more of a place's
people in no district than the place's own map does in eight of the ten:
Columbia 829 against 96, Greenville 913 against 117, Summerville 814 against
none, North Charleston 470 against 5, Charleston 490 against 276, Greer 294
against 1, Rock Hill 38 against none and Sumter 2,138 against 2,085 (leaving
out the state's seventh Sumter district, below), with Spartanburg 9 against
23 and Hilton Head Island none in either. The state's copy also draws seven
districts in Sumter, which elects six wards. So each place's map is used
where there is one that can be drawn.

WHO PUBLISHES EACH, read on 2026-10-16. Charleston, Columbia, Rock Hill and
Greenville serve theirs from their own GIS servers (Charleston's layer was
found in its MapNet viewer's configuration); North Charleston,
Summerville, Spartanburg, Hilton Head Island and Greer publish theirs in
ArcGIS Online organizations whose other layers are that place's own parcels,
zoning and streets. Greer's carries 11 records for its 6 districts, three of
them in more than one piece. Sumter's is the "City of Sumter Council" layer
of the election service on gis.sumter-sc.com, a server whose base map
service is named Sumter_City_County, and the card says where it comes from.

FLORENCE AND AIKEN ARE THE STATE'S COPY. Aiken's own map service publishes
its six districts with no shapes: every record's geometry is empty. Florence's
own map was last edited on 20 April 2023, before the ordinance the state's
copy names (2023-29, effective 11 September 2023) took effect, and each of
its three districts overlaps the state's by only 0.90 of the two together;
the state's copy names its ordinance, so it is used. The office says its map
is "NOT to be construed or used as a 'legal description'" and that a user
"should not rely on the data", and the card says the lines are the state's
copy and not a legal description.

SUMTER'S SIX WARDS LEAVE OUT SHAW AIR FORCE BASE. 13.71 km2 of the Census
outline of Sumter lies in none of the city's six wards, and 13.43 km2 of it
is the Census's own outline of Shaw Air Force Base (TIGERweb's military
installations layer, read 2026-10-16); of the 2,085 people the city's map
leaves out at the 2020 census, 2,064 live there. The state's copy draws that
ground as a seventh district. The city's six are drawn, so a point on the
base answers no ward, which is what the city's map says; why the base has no
ward was not established.

EACH MAP IS A MAP OF ITS PLACE, measured on 2026-10-16 against the Census
outline of the place: the share of the place its districts cover, and the
share of the districts outside the place. Each source's floor and ceiling
below are five points from what was measured, so a few annexed blocks pass
and another city's map, or a county's, does not. Hilton Head Island's wards
reach into the water around the island, which is why 37.9% of them lies
outside the place. North Charleston's cover 95.3% of the place, and the rest
held 5 people at the 2020 census. Florence's leave out 694 of its people,
Aiken's 375 and Charleston's 276; a point on that ground answers no
district, which is what those maps say.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
sc-municipal-officeholders): the state's map of council districts lags the
places' own, draws a seventh Sumter district the city does not elect,
spells places its own way ("HILTON HEAD"), records dates as epoch
milliseconds and areas in square feet, and omits Anderson; no place's map
says which plan it is or when it took effect, bar the state's; one city's
map service has no shapes; one city publishes its districts only as
pictures; one city's layer is findable only in a viewer's configuration;
and one city packs each member's name into the district field.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, HERE)

import build_sc_city_councils as councils  # noqa: E402
import city_ward_maps as cwm  # noqa: E402

RFA = ("https://gis.state.sc.us/arcgis/rest/services/Boundaries_Districts/"
       "Municipal_Council_Districts/FeatureServer/0")
NUMBER = r"([1-9][0-9]?)"

# (covers, outside) floors and ceilings, five points from the shares measured
# on 2026-10-16 that each comment gives.
SOURCES = (
    cwm.Source("4513330",  # Charleston: covers 98.9%, 5.8% outside
               "https://gis.charleston-sc.gov/arcgis2/rest/services/External/"
               "mapnetExternal/MapServer/13",
               "DIST_ID", NUMBER, records=12, covers=93.9, outside=10.8,
               drawn_from="the City of Charleston's own map"),
    cwm.Source("4516000",  # Columbia: 99.7%, 1.4%
               "https://gis.columbiasc.gov/cola/rest/services/Public/CoCInfoBoundary/"
               "MapServer/1",
               "LABEL", r"DISTRICT ([1-4])", records=4, covers=94.7, outside=6.4,
               drawn_from="the City of Columbia's own map"),
    cwm.Source("4550875",  # North Charleston: 95.3%, 1.4%
               "https://services3.arcgis.com/BLrzoqoB28p9t3a7/arcgis/rest/services/"
               "Council_Districts/FeatureServer/0",
               "DISTRICT", NUMBER, records=10, covers=90.3, outside=6.4,
               drawn_from="the City of North Charleston's own map"),
    cwm.Source("4561405",  # Rock Hill: 99.2%, 1.8%
               "https://crh-vmw-gisvdr1.cityofrockhillsc.gov/arcgis/rest/services/"
               "DynamicStaticServices/DynamicService/MapServer/9",
               "WARD", NUMBER, records=6, covers=94.2, outside=6.8,
               drawn_from="the City of Rock Hill's own map"),
    cwm.Source("4530850",  # Greenville: 99.6%, 2.8%; the field reads "1- <member>",
               # and only the number is kept
               "https://citygis.greenvillesc.gov/arcgis/rest/services/FindElectedOfficials/"
               "Find_Your_Elected_Officials/MapServer/1",
               "DISTRICT", r"([1-4])- .+", records=4, covers=94.6, outside=7.8,
               drawn_from="the City of Greenville's own map"),
    cwm.Source("4570270",  # Summerville: 99.6%, 4.3%
               "https://services8.arcgis.com/0zSnoqwLCR3i1Yfw/arcgis/rest/services/"
               "Council_Districts/FeatureServer/0",
               "DISTRICT", NUMBER, records=6, covers=94.6, outside=9.3,
               drawn_from="the Town of Summerville's own map"),
    cwm.Source("4570405",  # Sumter: 84.1%, 0.6% (Shaw Air Force Base, above)
               "https://gis.sumter-sc.com/server/rest/services/ElectionAdministration/"
               "ElectionAdministration/MapServer/1109",
               "DISTRICTID", r"WARD([1-6])", records=6, covers=79.1, outside=5.6,
               drawn_from="the election map published on gis.sumter-sc.com"),
    cwm.Source("4525810",  # Florence, the state's copy: 93.0%, 3.0%
               RFA, "DISTRICT", NUMBER, records=3, covers=88.0, outside=8.0,
               where="Municipali = 'FLORENCE'",
               drawn_from="the state Revenue and Fiscal Affairs Office's copy of the city's "
                   "districts, which the office says is not a legal description"),
    cwm.Source("4568290",  # Spartanburg: 99.3%, 1.0%
               "https://services9.arcgis.com/HoRra3ATPLGmyjn6/arcgis/rest/services/"
               "CouncilDistricts_2023/FeatureServer/0",
               "District", NUMBER, records=6, covers=94.3, outside=6.0,
               drawn_from="the City of Spartanburg's own map"),
    cwm.Source("4534045",  # Hilton Head Island: 100.0%, 37.9% (water)
               "https://services1.arcgis.com/t1pOARESVtLutuqb/arcgis/rest/services/"
               "2022_Town_Council_Wards/FeatureServer/0",
               "WARD_NUM", NUMBER, records=6, covers=95.0, outside=42.9,
               drawn_from="the Town of Hilton Head Island's own map"),
    cwm.Source("4530985",  # Greer: 99.4%, 4.4%; 11 records for 6 districts
               "https://services1.arcgis.com/bskBH6JV42oEWJvZ/arcgis/rest/services/"
               "City_Council_Districts_Current/FeatureServer/0",
               "District", NUMBER, records=11, parts=5, covers=94.5, outside=9.4,
               drawn_from="the City of Greer's own map"),
    cwm.Source("4500550",  # Aiken, the state's copy: 96.5%, 0.6%
               RFA, "DISTRICT", NUMBER, records=6, covers=91.5, outside=5.6,
               where="Municipali = 'AIKEN'",
               drawn_from="the state Revenue and Fiscal Affairs Office's copy of the city's "
                   "districts, which the office says is not a legal description"),
)

SPEC = cwm.Spec(
    tag="sc",
    label="build_sc_city_wards",
    user_agent="districtry/1.0 (+https://districtry.com/sc/)",
    seats_file="sc-city-council-seats.json",
    out_file="sc-city-wards.json",
    sources=SOURCES,
    undrawn=councils.SPEC.undrawn,
    card_claims=(
        "each place's own map of its districts",
        "not a legal description",
    ),
    # Each point is one the Census's place map puts in the place named
    # (TIGERweb, read 2026-10-16), and its district is the answer that
    # place's own map gave the same day.
    inside=(
        (-81.03310, 34.00040, "4516000-2", "a point in Columbia"),
        (-79.93090, 32.77660, "4513330-8", "a point in Charleston"),
        (-82.39970, 34.84850, "4530850-3", "a point in Greenville"),
    ),
    outside=(
        (-80.47040, 33.97443, "a point on Shaw Air Force Base, inside the Census outline of "
                              "Sumter and in none of the city's six wards"),
        (-82.65010, 34.50090, "a point in Anderson, whose districts are not drawn"),
    ),
)

if __name__ == "__main__":
    cwm.main(SPEC, __doc__)
