#!/usr/bin/env python3
"""
Build ks/data/app/ks-city-wards.json: the 41 council wards and districts of
the seven Kansas cities of 25,000 people or more whose wards elect their own
members and whose current maps are drawn here, each read from the map the
city, or its county's election office, publishes.

    python3 ks/scripts/build_ks_city_wards.py            # fetch, check, write
    python3 ks/scripts/build_ks_city_wards.py --check    # offline
    python3 ks/scripts/build_ks_city_wards.py --watch    # has any city's map changed?

The work is scripts/city_ward_maps.py; this file says where each city's map
is and how to read it. WHICH cities are drawn is read from the seats file the
council roster is built from (ks/data/source/ks-city-council-seats.json):
every city with a seat its own ward's voters elect, less the three that
ks/scripts/build_ks_city_councils.py declares undrawn (its `undrawn` table,
which this reads).

DRAWN, read on 2026-11-28: Wichita 6 districts (the City of Wichita's own map
server), Derby 4 wards (Sedgwick County's map of voting districts, whose City
Council layer draws the wards of four Sedgwick County cities and names the
city in a field, so it is asked for Derby's alone), Overland Park 6 wards
(the city's map of its 144 ward precincts, one record per precinct, merged
here into one outline per ward), Kansas City 8 districts (the Unified
Government's map of its commission districts, "Updated 08-25-2023"),
Olathe 4 wards (the city's own map server), Topeka 9 districts (the city's
map in ArcGIS Online) and Hutchinson 4 districts (the city's "City Council
Districts 2024"). Each ward's card says whose map it is drawn from.

IS EACH THE CURRENT MAP. Measured against the Census Bureau's 2020 blocks
(each populated block's internal point inside the city's current Census
outline), as the spread between the largest and smallest ward as a share of
an equal one: Wichita 2.4%, Topeka 4.6%, Hutchinson 5.3%, Derby 8.4% and
Olathe 10.3%. That is what a map drawn on the 2020 census shows; it does not
prove when a map was drawn, so that each is the map in force is an inference,
recorded as one. Two need more than that:

  Overland Park's wards are 18.2% apart on the 2020 census, and the map
  carries its own population figure for each precinct, on which its six wards
  hold 33,722 to 36,101 people, 6.9% apart, and 207,990 in all, more than the
  197,238 the 2020 census counted. So it was balanced on the city's own later
  figures. Its member fields name the twelve members the city's council page
  names, ward by ward, and the layer was last edited on 2026-09-04.

  Kansas City's commission districts reach past the city: the Unified
  Government governs all of Wyandotte County, and the voters of Bonner
  Springs, Edwardsville and the county's part of Lake Quivira elect its
  commissioners too. So the map is not cut at the city's limits, and 17.9% of
  it lies outside the Census outline of Kansas City (District 7 holds most of
  Bonner Springs and Edwardsville). Over the whole county its eight districts
  hold 20,863 to 21,563 people on the 2020 census, 3.3% apart, and every
  district was last edited between 2022-12-08 and 2023-07-07. The same
  publisher's older map, "Commission Districts" (item modified 2020-02-19),
  is 23.0% apart and is not used.

NOT DRAWN, each with its reason in build_ks_city_councils.py's `undrawn`:
Lenexa publishes no map of its wards this project may read (Johnson County's
map server, which draws them, disallows this project's reader in its
robots.txt, measured 2026-11-28); Shawnee's and Leawood's maps are 18.8% and
18.7% apart on the 2020 census, and Shawnee's carries 2010 census figures, so
which map is in force is a question for each city, as Lawton's was in
Oklahoma.

EACH MAP IS A MAP OF ITS CITY, measured on 2026-11-28 against the Census
outline of the place: the share of the place its wards cover, and the share
of the wards outside the place. Each source's floor and ceiling below are
five points from what was measured, so a few annexed blocks pass and another
city's map, or a county's, does not.

PRIVACY. The builder asks each layer for its ward field and nothing else.
Six carry more: Wichita's, Derby's (Sedgwick County's), Overland Park's,
Kansas City's and Olathe's each member's name, Olathe's each member's e-mail
address and term, and Topeka's each member's name, e-mail address, telephone
number and photograph.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
ks-municipal-officeholders): no state office publishes Kansas's city wards;
the seven maps carry the ward number under seven different field names; none
says when its lines were adopted, except Hutchinson's in its title and
Kansas City's in its description; the Unified Government keeps an older,
unequal map public beside the current one; Overland Park's and Shawnee's
publish only precincts; and Lenexa's wards can be read only from a county
server that refuses automated readers.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, HERE)

import build_ks_city_councils as councils  # noqa: E402
import city_ward_maps as cwm  # noqa: E402

NUMBER = r"([1-9][0-9]?)"

# (covers, outside) floors and ceilings, five points from the shares measured
# on 2026-11-28 that each comment gives.
SOURCES = (
    cwm.Source("2079000",  # Wichita: covers 99.5%, 1.2% outside
               "https://gismaps.wichita.gov/ageweb/rest/services/COWGIS/Districts/MapServer/3",
               "COUNCIL", NUMBER, records=6, covers=94.5, outside=6.2,
               drawn_from="the City of Wichita's own map"),
    cwm.Source("2017800",  # Derby: 99.4%, 2.1%
               "https://services7.arcgis.com/McLat6HlPl45bNBv/arcgis/rest/services/"
               "Sedgwick_County_Voter_Districts/FeatureServer/20",
               "CouDistNo", NUMBER, where="CityCD='DB'", records=4, covers=94.4, outside=7.1,
               drawn_from="Sedgwick County's map of voting districts"),
    cwm.Source("2053775",  # Overland Park: 99.9%, 0.1%; 144 precincts for 6 wards
               "https://services1.arcgis.com/YQsWDBr0DjMtoTQo/arcgis/rest/services/"
               "Ward_Precincts/FeatureServer/0",
               "WARD", NUMBER, records=144, parts=138, dissolve=True, covers=94.9, outside=5.1,
               drawn_from="the City of Overland Park's own map of its ward precincts"),
    cwm.Source("2036000",  # Kansas City: 99.8%, 17.9% (the districts cover the county)
               "https://services1.arcgis.com/Qo2HHQp8vgPs2wg3/arcgis/rest/services/"
               "Commission_Districts_Aug_2023/FeatureServer/66",
               "District", NUMBER, records=8, covers=94.8, outside=22.9,
               drawn_from="the Unified Government's own map of its commission districts"),
    cwm.Source("2052575",  # Olathe: 99.8%, 0.2%; the field reads "WARD 1"
               "https://arcgis.olatheks.org/arcgis/rest/services/Public/Planning/MapServer/5",
               "WARD", r"WARD ([1-4])", records=4, covers=94.8, outside=5.2,
               drawn_from="the City of Olathe's own map"),
    cwm.Source("2071000",  # Topeka: 99.7%, 0.7%
               "https://services1.arcgis.com/EvtgI3PZ9PyCGJZS/arcgis/rest/services/"
               "CityCouncil/FeatureServer/0",
               "DISTNO", NUMBER, records=9, covers=94.7, outside=5.7,
               drawn_from="the City of Topeka's own map"),
    cwm.Source("2033625",  # Hutchinson: 96.5%, 0.3%; the field reads "SOUTHWEST DISTRICT"
               "https://services.arcgis.com/H9W1xrHipXQYSaRp/arcgis/rest/services/"
               "City_Council_Districts_2024/FeatureServer/0",
               "NAME", r"(NORTHEAST|NORTHWEST|SOUTHEAST|SOUTHWEST) DISTRICT", records=4,
               rename={"NORTHEAST": "Northeast", "NORTHWEST": "Northwest",
                       "SOUTHEAST": "Southeast", "SOUTHWEST": "Southwest"},
               covers=91.5, outside=5.3,
               drawn_from="the City of Hutchinson's own map"),
)

SPEC = cwm.Spec(
    tag="ks",
    label="build_ks_city_wards",
    user_agent="districtry/1.0 (+https://districtry.com/ks/)",
    seats_file="ks-city-council-seats.json",
    out_file="ks-city-wards.json",
    sources=SOURCES,
    undrawn=councils.SPEC.undrawn,
    card_claims=(
        "the map its city publishes",
    ),
    # Each point is more than 400 metres inside one ward of the city's map and
    # inside the Census's outline of the city (TIGERweb, read 2026-11-28), and
    # its ward is the answer that city's map gave when asked about the point
    # the same day.
    inside=(
        (-97.34684, 37.73976, "2079000-6", "a point in Wichita"),
        (-97.25244, 37.53525, "2017800-4", "a point in Derby, drawn from Sedgwick County's map"),
        (-94.70512, 38.82182, "2053775-6", "a point in Overland Park, whose wards are merged "
                                           "from precincts"),
        (-94.72689, 39.13209, "2036000-8", "a point in Kansas City"),
        (-94.76989, 38.90531, "2052575-4", "a point in Olathe, whose map names each ward "
                                           "\"WARD 4\""),
        (-95.74755, 39.04775, "2071000-9", "a point in Topeka"),
        (-97.93181, 38.04581, "2033625-Southwest", "a point in Hutchinson, whose districts "
                                                   "are named"),
    ),
    # Each is the Census's internal point of the place (TIGERweb, read
    # 2026-11-28).
    outside=(
        (-95.26547, 38.95955, "a point in Lawrence, which elects its whole commission by "
                              "the whole city"),
        (-94.80394, 38.96527, "a point in Lenexa, whose wards are not drawn"),
        (-94.80581, 39.01749, "a point in Shawnee, whose wards are not drawn"),
        (-94.62524, 38.90726, "a point in Leawood, whose wards are not drawn"),
    ),
)

if __name__ == "__main__":
    cwm.main(SPEC, __doc__)
