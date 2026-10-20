#!/usr/bin/env python3
"""
Build tn/data/app/tn-city-wards.json: the 72 council districts and wards of
the eleven Tennessee cities above 25,000 people whose councils elect members
by district or ward and publish a map of them that can be drawn, each from
the city's own map or, for two, a copy of it.

    python3 tn/scripts/build_tn_city_wards.py            # fetch, check, write
    python3 tn/scripts/build_tn_city_wards.py --check    # offline
    python3 tn/scripts/build_tn_city_wards.py --watch    # has any city's map changed?

The work is scripts/city_ward_maps.py; this file says where each city's map
is and how to read it. WHICH cities are drawn is read from the seats file the
council roster is built from (tn/data/source/tn-city-council-seats.json):
eleven of the thirteen with a seat their district's own voters elect.

THE OTHER TWO are not drawn, and tn/scripts/build_tn_city_councils.py, whose
`undrawn` table this reads, says why for each: the only copy of Knoxville's
districts published as data, from Knoxville and Knox County's mapping agency
(KGIS), reserves all rights and allows no copy without its written
permission; and Lebanon publishes its wards only as the county election
commission's PDF files. scripts/build_eam_status.py records both as owed.

TWO CITIES ARE DRAWN FROM A COPY, because the map server the city itself
runs cannot be read. Both were found on 2026-10-17 by looking for every
published copy of the lines before recording the cities as unreadable.

CHATTANOOGA's nine districts are read from the City of Chattanooga's own
copy on ArcGIS Online (Council_Districts, created 18 November 2025, last
edited 26 November 2025). The copy the city's own map server calls
authoritative cannot be read, because that server's robots.txt shuts this
project out of its map services, and Hamilton County's copy answers every
record with its shape withheld. The city's map of its districts on ArcGIS
Online says they are "Effective April 14, 2025", and three measurements, on
2026-10-17, say this copy is that plan: it was made after that date; a
second copy the city made on 30 October 2025
(Chattanooga_Council_Districts_Enriched) matches it exactly; and on the
Census Bureau's 2020 blocks it holds the city's people within 4.6% of an
equal share (-4.6% to +4.2%), where the city's two copies from 2024 (COUNCIL
and Council Districst1_WFL1), made before the plan took effect, run from
13.1% under to 12.8% over and put 50.2 km2 in a different district. That
it is the plan in force is an inference from those measurements. What it
cannot show: the authoritative layer's record on ArcGIS Online was last
modified on 16 October 2026, whether its lines changed then cannot be seen
from here, and a change there that the city does not copy here would not be
noticed, by --watch or by anything else this project can read. The city's
Maps & OpenData page says the city's and Hamilton County's GIS teams provide
"public ArcGIS Layers and Feature Services to support your planning needs";
the copy read here states no licence, and the authoritative layer's record
carries only a disclaimer of accuracy and liability.

HENDERSONVILLE's six wards are read from Sumner County's copy (City of
Hendersonville Wards, layer 29 of the county's property-search service, its
data last edited 16 June 2026), because the city's own map server answers
robots.txt with HTTP 500, which this project reads as a refusal (RFC 9309
section 2.3.1.4). Each ward's record carries the redistricting plan's own
population figures, and they sum to 61,753, the city's 2020 census count,
each ward within 489 people of the plan's equal share of 10,292; measured
against the Census Bureau's 2020 blocks the wards hold the city's people
within 4.3% of an equal share (-2.1% to +4.3%). The city's own map of them
is a PDF named "WardMap2022", created 13 September 2022, and the county
election commission links the city's "2022 Hendersonville Ward Map"; this
copy was not compared with either, so that it is the same plan is inferred
from the population figures. As a control, the county's copy of Gallatin's
wards in the same service (layer 28) assigns every square metre it shares
with Gallatin's own map, which this file draws, to the same ward, 91.6 km2
in all, while leaving out 4.6 km2 the city's map includes: a county's copy
can lag a city's newest land. No licence is stated on the service.

MEMPHIS ELECTS BY TWO KINDS OF DISTRICT, seven districts of one member each
and two super districts of three members each, and its own map server
publishes each kind as a layer of its own, both described as the districts of
Ordinance 5870, signed 30 June 2023. Each layer is a source here
(scripts/city_ward_maps.py, step 1), so a point in Memphis lies in one
district and one super district and the card names the members of both. The
number is read from CD and SD alone: each record also carries a name field,
and in the district layer it names another district for six of the seven
(district 2's record reads "Council District 6"). Whether these layers are
the plan the city's own district maps show was measured on 2026-10-16
against four of those maps, PDF files stamped "Map Produced 1/2/2024":
located by each file's own georeference and compared pixel by pixel, the
served districts agree with each map on 98.96% to 99.87% of its district
pixels, against 77.84% to 89.88% for the city's older plan, and every sample
taken 150 feet apart along the served line between the two super districts
lies within 4 pixels of the line the maps draw. Two other copies of the same
lines on the city's servers describe themselves as last updated in 2012 and
2015; their polygons are this plan's, so it is the descriptions that are
out of date.

NASHVILLE IS NOT AMONG THE THIRTEEN. Its 35 Metropolitan Council districts are
the county commission districts of Davidson County, which the County
Commission District layer already draws and whose members it names, so they
are not drawn twice; the seats file names Nashville's mayor and vice mayor
only, and scripts/build_eam_status.py records the council as drawn by that
layer.

NO STATE OFFICE PUBLISHES THEM. The Comptroller of the Treasury's
redistricting service carries every other kind of district in the state
(county commission, school board, precinct) and no city ward, so each city's
map is read from the city.

WHO PUBLISHES EACH, read on 2026-10-16: Memphis's own map server
(gis.memphistn.gov, the two layers above), Clarksville and Montgomery
County's shared GIS (gis.mcgtn.org), Franklin's own map server, Jackson's ArcGIS
Online organization ("Council Plan A Effective May 2023"), Cleveland's,
Gallatin's and Mount Juliet's own map servers (Mount Juliet's through an
ArcGIS Online proxy), Columbia's ArcGIS Online organization,
Morristown's ("City Wards", described as updated with its redistricting in
May 2026), and, read on 2026-10-17, the City of Chattanooga's and Sumner
County's ArcGIS Online organizations (the two copies above).

IS EACH THE CURRENT MAP. Only three say which plan they are: Memphis's names
the ordinance and the day it was signed, Jackson's names the plan and when it
took effect, and Morristown's says it was updated with the city's 2026
redistricting. Chattanooga's and Hendersonville's are measured above. For
the eight others, the districts were measured
against the Census Bureau's 2020 blocks inside each city's current Census
outline on 2026-10-16, and every city's districts hold its people to within
7.7% of an equal share (Clarksville within 5.0%, Franklin 3.3%, Jackson
1.5%, Cleveland 2.9%, Gallatin 7.5%, Columbia 6.3%, Mount Juliet 3.8% and
Morristown 7.7%). A plan drawn on the 2010 census would not balance that
closely on the 2020 count in cities that grew as these did, so each is taken
to be a plan drawn after the 2020 census, which is an inference for the six
that do not say so and is recorded as one here. Cleveland's records carry an
update date of 2 December 2016, which the balance contradicts; why was not
established.

EACH MAP IS A MAP OF ITS CITY, measured on 2026-10-16 against the Census
outline of the place: the share of the place its districts cover, and the
share of the districts outside the place. Each source's floor and ceiling
below are five points from what was measured, so a few annexed blocks pass
and another city's map, or a county's, does not. Hendersonville's wards
cover 85.0% of the Census outline of the city, read 2026-10-17, because the
outline takes in the Cumberland River and its creeks along the city's shore
and the wards do not: 97.6% of the ground they leave out is water in the
Census Bureau's own areal hydrography (named there as the Cumberland River
and Drakes Creek), and no 2020 census block on it has anyone living in it. Mount Juliet's districts
reach 8.1 km2 beyond the Census outline of the city, and all but 0.1 km2 of
that lies inside the city's own City Limits layer in the same service (last
edited 25 August 2026, 82.3 km2 against the Census's 70.6): land annexed
since the Census drew its outline. A point there answers its district here
while the City or Town card, which reads the Census outline, does not yet
show the city.

PRIVACY. Franklin's ward layer carries contact fields beside each ward,
Mount Juliet's district field packs each commissioner's name beside the
number ("1-<name>"), Chattanooga's copy carries each member's name in a field
of its own, and Sumner County's copy of Hendersonville's wards carries the
aldermen's names and the names of the staff who edited it, so the builder
asks every source for the district field alone (scripts/city_ward_maps.py
requests nothing else) and reads Mount Juliet's number from its separate
CITYDIST field.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
tn-municipal-officeholders): no state office publishes Tennessee's city
council districts; eight of the eleven maps drawn do not say which plan they
are or when it took effect; one county withholds the shapes of its city's
districts while publishing their numbers, so the only readable copy is one
the city keeps beside the map it calls authoritative, which this project may
not read; one city's map server cannot be asked whether it may be read, so
its wards are read from the county's property-search copy, which records no
plan and no date the plan took effect; one city publishes its current wards
only as PDF files; the only copy of one city's districts published as data
reserves all rights; one city packs its members' names into the district
field; and one city's district layer names six of its seven districts with
another district's name, while two other copies of its lines carry
descriptions years out of date.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, HERE)

import build_tn_city_councils as councils  # noqa: E402
import city_ward_maps as cwm  # noqa: E402

NUMBER = r"([1-9][0-9]?)"

# (covers, outside) floors and ceilings, five points from the shares measured
# on 2026-10-16 (2026-10-17 for Chattanooga and Hendersonville) that each
# comment gives.
SOURCES = (
    cwm.Source("4748000",  # Memphis's districts: covers 99.9%, 0.8% outside
               "https://gis.memphistn.gov/server/rest/services/Basemaps/"
               "Administrative_Boundaries/MapServer/1",
               "CD", NUMBER, records=7, covers=94.9, outside=5.8, wards=range(1, 8),
               drawn_from="the City of Memphis's own map of its districts under Ordinance "
                   "5870, signed 30 June 2023"),
    cwm.Source("4748000",  # Memphis's super districts: 99.9%, 0.8%
               "https://gis.memphistn.gov/server/rest/services/Basemaps/"
               "Administrative_Boundaries/MapServer/2",
               "SD", NUMBER, records=2, covers=94.9, outside=5.8, wards=(8, 9),
               word="Super District", key="4748000-sd",
               drawn_from="the City of Memphis's own map of its super districts under "
                   "Ordinance 5870, signed 30 June 2023"),
    cwm.Source("4715160",  # Clarksville: covers 99.6%, 0.0% outside
               "https://gis.mcgtn.org/arcgis/rest/services/CityWard/MapServer/1",
               "DISTRICT", NUMBER, records=12, covers=94.6, outside=5.0,
               drawn_from="the City of Clarksville's map, published by Clarksville and "
                   "Montgomery County's shared GIS"),
    cwm.Source("4727740",  # Franklin: 99.8%, 0.8%
               "https://publicmaps.franklintn.gov/arcgis/rest/services/Maps/"
               "GovernmentServices/MapServer/21",
               "NAME", NUMBER, records=4, covers=94.8, outside=5.8,
               drawn_from="the City of Franklin's own map"),
    cwm.Source("4737640",  # Jackson: 99.6%, 1.8%; the field reads "D1" to "D9"
               "https://services3.arcgis.com/k6aQP9AQncZQEtBv/arcgis/rest/services/"
               "PSALayers/FeatureServer/86",
               "District", r"D([1-9])", records=9, covers=94.6, outside=6.8,
               drawn_from="the City of Jackson's own map of its Plan A, effective May 2023"),
    cwm.Source("4715400",  # Cleveland: 99.7%, 4.9%
               "https://gis.clevelandtn.gov/arcgis/rest/services/CityCouncilDistricts/"
               "CityCouncilDistricts/MapServer/0",
               "DISTRICTID", NUMBER, records=5, covers=94.7, outside=9.9,
               drawn_from="the City of Cleveland's own map"),
    cwm.Source("4728540",  # Gallatin: 99.2%, 3.2%
               "https://arcweb.gallatin-tn.gov/arcgis/rest/services/Features/"
               "City_Council_Districts/MapServer/2",
               "District", NUMBER, records=5, covers=94.2, outside=8.2,
               drawn_from="the City of Gallatin's own map"),
    cwm.Source("4716540",  # Columbia: 99.1%, 1.2%
               "https://services6.arcgis.com/ubRvNDgGwwJuZMcL/arcgis/rest/services/"
               "Wards_VL/FeatureServer/0",
               "DISTRICT", NUMBER, records=5, covers=94.1, outside=6.2,
               drawn_from="the City of Columbia's own map"),
    cwm.Source("4750780",  # Mount Juliet: 99.6%, 10.3% (annexed land, above)
               "https://utility.arcgis.com/usrsvcs/servers/621b088a06a84f16b412e25b8d127804/"
               "rest/services/Administration_City/FeatureServer/1",
               "CITYDIST", NUMBER, records=4, covers=94.6, outside=15.3,
               drawn_from="the City of Mt. Juliet's own map"),
    cwm.Source("4750280",  # Morristown: 99.8%, 0.3%
               "https://services.arcgis.com/xhDV83hFoiDFnMbw/arcgis/rest/services/"
               "Morristown_Ward_Map/FeatureServer/0",
               "districtid", NUMBER, records=4, covers=94.8, outside=5.3,
               drawn_from="the City of Morristown's own map, updated with its 2026 "
                   "redistricting"),
    cwm.Source("4714000",  # Chattanooga: 99.8%, 0.2% (the city's copy, above)
               "https://services2.arcgis.com/OIAIimblRxPs0xxc/arcgis/rest/services/"
               "Council_Districts/FeatureServer/0",
               "COUNCIL", NUMBER, records=9, covers=94.8, outside=5.2,
               drawn_from="a copy the City of Chattanooga publishes of its own map"),
    cwm.Source("4733280",  # Hendersonville: 85.0% (the river, above), 0.3%; six
               # wards in 19 records, 13 of them further parts of a ward
               "https://services5.arcgis.com/I2fcoygeHRmx0WzS/arcgis/rest/services/"
               "PSALayers/FeatureServer/29",
               "DISTRICT", NUMBER, records=19, parts=13, covers=80.0, outside=5.3,
               drawn_from="Sumner County's copy of the City of Hendersonville's map"),
)

SPEC = cwm.Spec(
    tag="tn",
    label="build_tn_city_wards",
    user_agent="districtry/1.0 (+https://districtry.com/tn/)",
    seats_file="tn-city-council-seats.json",
    out_file="tn-city-wards.json",
    sources=SOURCES,
    undrawn=councils.SPEC.undrawn,
    card_claims=(
        "each city's own map of its districts",
        "a published copy of it",
    ),
    # Each point is one the Census's place map puts in the place named
    # (TIGERweb, read 2026-10-16, and 2026-10-17 for Chattanooga,
    # Hendersonville and Lebanon), and its district is the answer the map
    # drawn for that city gave the same day. A point in Memphis lies in a
    # district and a super district, and names both.
    inside=(
        (-90.04900, 35.14950, ["4748000-7", "4748000-8"],
         "a point in Memphis, in District 7 and Super District 8"),
        (-87.35950, 36.52980, "4715160-6", "a point in Clarksville"),
        (-88.81390, 35.61450, "4737640-2", "a point in Jackson"),
        (-86.86890, 35.92510, "4727740-4", "a point in Franklin"),
        (-85.21281, 35.13527, "4714000-3", "a point in Chattanooga"),
        (-86.59601, 36.31271, "4733280-2", "a point in Hendersonville"),
    ),
    outside=(
        (-83.92070, 35.96060, "a point in Knoxville, whose districts are not drawn"),
        (-86.29111, 36.20806, "a point in Lebanon, whose wards are not drawn"),
        (-86.78160, 36.16270, "a point in Nashville, whose council districts the County "
                              "Commission District layer draws"),
    ),
)

if __name__ == "__main__":
    cwm.main(SPEC, __doc__)
