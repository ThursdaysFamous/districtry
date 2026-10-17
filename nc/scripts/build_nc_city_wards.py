#!/usr/bin/env python3
"""
Build nc/data/app/nc-city-wards.json: the 100 council districts and wards of
the seventeen North Carolina cities above 25,000 people whose councils elect
members by district or ward, each read from the map its city or its county
publishes.

    python3 nc/scripts/build_nc_city_wards.py            # fetch, check, write
    python3 nc/scripts/build_nc_city_wards.py --check    # offline
    python3 nc/scripts/build_nc_city_wards.py --watch    # has any city's map changed?

The work is scripts/city_ward_maps.py; this file says where each city's map
is and how to read it. WHICH cities are drawn is read from the seats file the
council roster is built from (nc/data/source/nc-city-council-seats.json):
all seventeen with a seat their district's own voters elect, so none is
declared undrawn. All six of Gastonia's wards are drawn although the members
for Wards 3, 4 and 6 were elected by the whole city, because Wards 1, 2 and 5
elect their own members and from 2027 all six do (the city's `how` in the
seats file says so).

NOT DRAWN: Durham, Concord, Hickory and Morrisville tie seats to wards or
districts and elect every seat by the whole place, so a district there
would elect no one of its own; the other 21 places elect every seat by the
whole place.

NO STATE OFFICE PUBLISHES THEM. The State Board of Elections publishes each
election's precinct results and a statewide map of precincts, and no map of
any city's council districts, so each city's map is read from whoever
publishes it.

WHO PUBLISHES EACH, read on 2026-10-16: twelve cities publish their own,
from their own map servers or ArcGIS Online organizations (Charlotte,
Raleigh, Winston-Salem, Fayetteville, Cary, Greenville, Gastonia, Rocky
Mount, Wilson, Goldsboro, New Bern and Statesville), and five are published
by their county: Guilford County's for Greensboro and High Point, Onslow
County's for Jacksonville, Iredell County's for Mooresville and Lee County's
for Sanford. Each district's card says whose map it is drawn from. Three
layers carry a record that is not a district, and each is left out by the
source's `where`: Greenville's has one whose district reads "Non Voting"
(39,879 people at the 2020 census, all but 0.1% of its area outside the
city), Goldsboro's one numbered 0 that draws the whole city at once, and
Cary's records with no district at all.

RALEIGH'S ONLY READABLE COPY IS LABELLED A PROPOSAL. The city's live layer
(maps.raleighnc.gov) is closed to this project by its robots.txt, and the
city's website answers with Cloudflare's managed challenge, so the map drawn
is the copy the city published in its ArcGIS Online organization in November
2021, described as "Proposed Council Districts, Scenario 2". A search engine
quotes the city's redistricting page as saying the council adopted Scenario 2
on 1 March 2022 by Resolution 2022-339; that page could not be read here, so
the precincts are the measurement: the precincts that carried each Raleigh
district's contest on 5 November 2024 lie 99.9% to 100% inside the same
district on this map.

JACKSONVILLE'S COUNTY PUBLISHES TWO MAPS OF ITS WARDS, which name a
different ward on 6.0% of the ground inside the city that both draw. The one
drawn, Onslow County's "City of Jacksonville Wards" (its TemplateSite
service), holds the city's 2020 people to within 3.4% of an equal share; the
other, in the county's Census 2020 publications, leaves them as far apart as
14,412 and 21,152. Both pass the precinct test below, which cannot tell them
apart here, so the balance decides, and that is an inference recorded as
one. In June 2026 the council voted to redraw its wards rather than lose them
to House Bill 1038, which would elect every seat by the whole city from 2027
and was before the General Assembly when this was written; nc/WATCH.md asks
for the map to be read again once the council adopts new wards.

IS EACH THE CURRENT MAP. Only three layers say anything about it:
Charlotte's says it shows "the current city council district boundaries",
Rocky Mount's that its boundaries "were voted on and finalized in 2022", and
Statesville's was last edited on 8 September 2026. Every map was therefore
measured two ways on 2026-10-16:
  * Against the precincts that voted. For each of the 97 districts whose own
    voters elect a member, the State Board of Elections' precinct results for
    that district's most recent election (October 2023 to November 2025) say
    which precincts carried its contest, and the State Board's own precinct
    map (nc/data/app/nc-precincts.json) says where those precincts are: for
    95 of the 97, those precincts hold all but at most 162 of the 2020
    residents the map puts in the district. The other two are Raleigh's
    District B (13,466 of 93,709 outside) and Cary's District D (19,769 of
    42,956), and each district's contest was carried by two precincts that
    are no longer on the precinct map under the codes they had, so the test
    cannot settle those two. Gastonia's Wards 3, 4 and 6 are not tested,
    because the whole city voted in their contests.
  * Against the Census Bureau's 2020 blocks inside each city's current Census
    outline: each city's districts hold its people to within 9.2% of an equal
    share (Charlotte 3.3%, Raleigh 2.4%, Greensboro 2.8%, Winston-Salem 1.8%,
    Fayetteville 4.8%, Cary 5.1%, High Point 8.9%, Greenville 4.3%, Gastonia
    2.2%, Jacksonville 3.4%, Rocky Mount 5.1%, Mooresville 5.6%, Wilson 3.7%,
    Goldsboro 4.2%, New Bern 8.2%, Sanford 9.2% and Statesville 8.7%). The
    four over 8% are not shown by their balance to be plans drawn on the 2020
    census; the precinct test is what says their maps are the ones the
    sitting members were elected from.

EACH MAP IS A MAP OF ITS CITY, measured on 2026-10-16 against the Census
outline of the place: the share of the place its districts cover, and the
share of the districts outside the place. Each source's floor and ceiling
below are five points from what was measured, so a few annexed blocks pass
and another city's map, or a county's, does not. Raleigh's districts cover
96.9% of the city's Census outline and leave 1,641 of its 2020 people in no
district, and High Point's cover 96.3% and leave 622, 586 of them in Guilford
County, whose map it is; Winston-Salem's leave 557, Greenville's 106,
Gastonia's 105 and Greensboro's 53. Why each leaves that ground out was not
established. A point there answers no district, which is what those maps
say.

PRIVACY. The builder asks each layer for its district field and nothing
else. Several carry more beside each district: New Bern's each alderman's
home address, telephone and e-mail; Charlotte's each member's e-mail; and
High Point's, Greenville's, Rocky Mount's, Wilson's and Cary's the members'
names or telephone numbers.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
nc-municipal-officeholders): no state office publishes North Carolina's city
council districts; the seventeen maps come from sixteen publishers under
eight different field names; only Charlotte's says it is current and only
Rocky Mount's says when it was adopted; Raleigh's only copy this project may
read is labelled a proposal; one county publishes two different maps of one
city's wards; one layer is described as the city limits (Greenville's), one
service as electric power lines of 2005 (Iredell County's), and one as
polling places, credited to the City of Naperville, Illinois (Cary's); and
one city's ward layer carries its aldermen's home addresses.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, HERE)

import build_nc_city_councils as councils  # noqa: E402
import city_ward_maps as cwm  # noqa: E402

NUMBER = r"([1-9][0-9]?)"
GUILFORD = ("https://gcgis.guilfordcountync.gov/arcgis/rest/services/GISDV/"
            "Elected_Representation/MapServer/")

# (covers, outside) floors and ceilings, five points from the shares measured
# on 2026-10-16 that each comment gives.
SOURCES = (
    cwm.Source("3712000",  # Charlotte: covers 99.8%, 0.3% outside
               "https://gis.charlottenc.gov/arcgis/rest/services/PLN/CouncilDistricts/"
               "MapServer/0",
               "District", NUMBER, records=7, covers=94.8, outside=5.3,
               drawn_from="the City of Charlotte's own map"),
    cwm.Source("3755000",  # Raleigh: 96.9%, 3.0%
               "https://services.arcgis.com/v400IkDOw1ad7Yad/ArcGIS/rest/services/"
               "Council_Districts_Scenario_2/FeatureServer/1",
               "PROP_2", r"([A-E])", records=5, covers=91.9, outside=8.0,
               drawn_from="a copy of the City of Raleigh's map of its districts, published "
                   "by the city in November 2021, which matches the precincts that voted "
                   "in each district's 2024 election"),
    cwm.Source("3728000",  # Greensboro: 99.7%, 0.8%
               GUILFORD + "4",
               "DISTRICT", NUMBER, records=5, covers=94.7, outside=5.8,
               drawn_from="Guilford County's map of Greensboro's districts"),
    cwm.Source("3775000",  # Winston-Salem: 99.9%, 0.1%; the wards are named
               "https://arcgis2.cityofws.org/arcgissmwa02/rest/services/OICv2/Boundaries2/"
               "MapServer/0",
               "WARD", r"(East|North|Northeast|Northwest|South|Southeast|Southwest|West)",
               records=8, covers=94.9, outside=5.1,
               drawn_from="the City of Winston-Salem's own map"),
    cwm.Source("3722920",  # Fayetteville: 99.9%, 0.1%
               "https://gismaps.fayettevillenc.gov/cofpublicgis/rest/services/"
               "CityCouncilDistricts/CityCouncilDistricts/MapServer/0",
               "District", NUMBER, records=9, covers=94.9, outside=5.1,
               drawn_from="the City of Fayetteville's own map"),
    cwm.Source("3710740",  # Cary: 99.6%, 0.6%
               "https://maps-apis.carync.gov/server/rest/services/Elections/Elections/"
               "FeatureServer/2",
               "DISTRICTID", r"([A-D])", records=4, covers=94.6, outside=5.6,
               where="DISTRICTID IS NOT NULL",
               drawn_from="the Town of Cary's own map"),
    cwm.Source("3731400",  # High Point: 96.3%, 0.3%
               GUILFORD + "10",
               "DISTRICT", NUMBER, records=6, covers=91.3, outside=5.3,
               drawn_from="Guilford County's map of High Point's wards"),
    cwm.Source("3728080",  # Greenville: 98.4%, 1.3%
               "https://gisonline.greenvillenc.gov/arcgis/rest/services/Published/"
               "MapServer/1",
               "District", NUMBER, records=5, covers=93.4, outside=6.3,
               where="District <> 'Non Voting'",
               drawn_from="the City of Greenville's own map"),
    cwm.Source("3725580",  # Gastonia: 99.4%, 0.6%
               "https://cogserver.gastonianc.gov/serverweb/rest/services/AdminBnds/"
               "GastoniaCouncilWards/MapServer/0",
               "WARD_NUM", NUMBER, records=6, covers=94.4, outside=5.6,
               drawn_from="the City of Gastonia's own map"),
    cwm.Source("3734200",  # Jacksonville: 99.7%, 2.0%
               "https://gismaps.onslowcountync.gov/arcgis/rest/services/TemplateSite/"
               "OperationalLayers/MapServer/60",
               "WARD_NUM", NUMBER, records=4, covers=94.7, outside=7.0,
               drawn_from="Onslow County's map of Jacksonville's wards"),
    cwm.Source("3757500",  # Rocky Mount: 99.5%, 0.8%; 11 records for 7 wards
               "https://services.arcgis.com/4MdqIsNzxG7xyTvf/arcgis/rest/services/"
               "City_Council_Districts/FeatureServer/6",
               "WARD", NUMBER, records=11, parts=4, covers=94.5, outside=5.8,
               drawn_from="the City of Rocky Mount's own map, which it says was finalized "
                   "in 2022"),
    cwm.Source("3744220",  # Mooresville: 98.8%, 2.2%
               "https://maps.iredellcountync.gov/server/rest/services/Data/Elections/"
               "MapServer/3",
               "WARD", NUMBER, records=4, covers=93.8, outside=7.2,
               drawn_from="Iredell County's map of Mooresville's wards"),
    cwm.Source("3774540",  # Wilson: 99.8%, 1.4%
               "https://gisservices.wilsonnc.org/services/rest/services/communitymaps/"
               "communitymaps/MapServer/34",
               "DIST", NUMBER, records=7, covers=94.8, outside=6.4,
               drawn_from="the City of Wilson's own map"),
    cwm.Source("3726880",  # Goldsboro: 99.8%, 0.4%
               "https://gis.goldsboronc.gov/arcgis/rest/services/Election_Districts/"
               "FeatureServer/0",
               "DISTRICTID", NUMBER, records=6, covers=94.8, outside=5.4,
               where="DISTRICTID <> '0'",
               drawn_from="the City of Goldsboro's own map"),
    cwm.Source("3746340",  # New Bern: 99.8%, 0.3%; 11 records for 6 wards
               "https://gis.newbernnc.gov/arcgis/rest/services/Boundary/NewBern_Wards/"
               "FeatureServer/0",
               "Ward_Num", NUMBER, records=11, parts=5, covers=94.8, outside=5.3,
               drawn_from="the City of New Bern's own map"),
    cwm.Source("3759280",  # Sanford: 99.2%, 1.2%; 58 records for 5 wards
               "https://lee-arcgis.leecountync.gov/arcgis/rest/services/Political/"
               "POLITICAL/MapServer/1",
               "WARD", r"WARD ([1-5])", records=58, parts=53, covers=94.2, outside=6.2,
               drawn_from="Lee County's map of Sanford's wards"),
    cwm.Source("3764740",  # Statesville: 99.4%, 2.8%
               "https://services2.arcgis.com/WbGEgSzGTEPg4fr6/arcgis/rest/services/"
               "Stvl_Election_Wards/FeatureServer/0",
               "WARD", NUMBER, records=6, covers=94.4, outside=7.8,
               drawn_from="the City of Statesville's own map"),
)

SPEC = cwm.Spec(
    tag="nc",
    label="build_nc_city_wards",
    user_agent="districtry/1.0 (+https://districtry.com/nc/)",
    seats_file="nc-city-council-seats.json",
    out_file="nc-city-wards.json",
    sources=SOURCES,
    undrawn=councils.SPEC.undrawn,
    card_claims=(
        "the map its city or its county publishes",
    ),
    # Each point is one the Census's place map puts in the place named
    # (TIGERweb, read 2026-10-16), and its district is the answer that
    # city's map gave the same day.
    inside=(
        (-80.80292, 35.24796, "3712000-1", "a point in Charlotte"),
        (-78.61010, 35.78245, "3755000-C", "a point in Raleigh"),
        (-79.86492, 36.07530, "3728000-4", "a point in Greensboro, from Guilford "
                                           "County's map"),
        (-80.16777, 36.09319, "3775000-East", "a point in Winston-Salem, whose wards "
                                              "are named"),
    ),
    outside=(
        (-78.89860, 35.99400, "a point in Durham, whose wards elect no one of their own"),
        (-80.57950, 35.40880, "a point in Concord, whose districts elect no one of their "
                              "own"),
        (-82.55150, 35.59510, "a point in Asheville, which elects its whole council by "
                              "the whole city"),
    ),
)

if __name__ == "__main__":
    cwm.main(SPEC, __doc__)
