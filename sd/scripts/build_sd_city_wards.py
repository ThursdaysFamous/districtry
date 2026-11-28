#!/usr/bin/env python3
"""
Build sd/data/app/sd-city-wards.json: the nine council districts of Sioux
Falls and Aberdeen, two of the three South Dakota cities of 25,000 people or
more, each read from the map the city publishes.

    python3 sd/scripts/build_sd_city_wards.py            # fetch, check, write
    python3 sd/scripts/build_sd_city_wards.py --check    # offline
    python3 sd/scripts/build_sd_city_wards.py --watch    # has either city's map changed?

The work is scripts/city_ward_maps.py; this file says where each city's map
is and how to read it. WHICH cities are drawn is read from the seats file the
council roster is built from (sd/data/source/sd-city-council-seats.json):
every city with a seat its own ward's voters elect, less Rapid City, which
sd/scripts/build_sd_city_councils.py declares undrawn (its `undrawn` table,
which this reads).

DRAWN, read on 2026-11-28: Sioux Falls 5 districts (layer 5 of the City of
Sioux Falls's own Community map service) and Aberdeen 4 districts ("City
Council Districts (2021 Finalized)", in an ArcGIS Online organization whose
other layers are Aberdeen's own lots, roads and addresses, the layer a web
map titled "Aberdeen Council Districs" draws). Both cities name their
districts ("Northeast District"); each map writes the name ("Northeast").

IS EACH THE CURRENT MAP. Measured against the Census Bureau's 2020 blocks
(each populated block's internal point inside the city's current Census
outline): Sioux Falls's five districts hold 37,868 to 39,415 people, 4.0%
apart around an equal share, and Aberdeen's four hold 6,991 to 7,208, 3.0%
apart. Aberdeen's map carries its own population for each district, within
25 people of those counts. That each is the map in force is an inference from
those figures, recorded as one; Sioux Falls's layer also names each
district's member.

NOT DRAWN: Rapid City, whose five wards each elect two members. No map of its
wards that can be drawn was found (ArcGIS Online and the city's own map
server searched on 2026-11-28; the city's GIS office lists a voter precinct
map as a PDF), and build_sd_city_councils.py says so.

EACH MAP IS A MAP OF ITS CITY, measured on 2026-11-28 against the Census
outline of the place: Sioux Falls's districts cover 99.9% of the place, 1.3%
outside it; Aberdeen's 96.8%, 0.5% outside it. Each floor and ceiling below
is five points from what was measured.

PRIVACY. The builder asks each layer for its district field and nothing
else. Sioux Falls's also carries each member's name, photograph and page.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
sd-municipal-officeholders): no state office publishes South Dakota's city
council districts; neither map says when its lines were adopted beyond
Aberdeen's title; and Rapid City publishes no map of its wards that can be
read as lines.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, HERE)

import build_sd_city_councils as councils  # noqa: E402
import city_ward_maps as cwm  # noqa: E402

NAMED = r"(Central|Northeast|Northwest|Southeast|Southwest)"

SOURCES = (
    cwm.Source("4659020",  # Sioux Falls: covers 99.9%, 1.3% outside
               "https://gis.siouxfalls.gov/arcgis/rest/services/Data/Community/MapServer/5",
               "districtid", NAMED, records=5, covers=94.9, outside=6.3,
               drawn_from="the City of Sioux Falls's own map"),
    cwm.Source("4600100",  # Aberdeen: 96.8%, 0.5%
               "https://services5.arcgis.com/H3Xuuu0h4PaTeWwU/arcgis/rest/services/"
               "New_Final_Districts/FeatureServer/1",
               "District", NAMED, records=4, covers=91.8, outside=5.5,
               drawn_from="the City of Aberdeen's map of its council districts"),
)

SPEC = cwm.Spec(
    tag="sd",
    label="build_sd_city_wards",
    user_agent="districtry/1.0 (+https://districtry.com/sd/)",
    seats_file="sd-city-council-seats.json",
    out_file="sd-city-wards.json",
    sources=SOURCES,
    undrawn=councils.SPEC.undrawn,
    card_claims=(
        "the map its city publishes",
    ),
    # Each point is more than 500 metres inside one district of the city's map
    # and inside the Census's outline of the city (TIGERweb, read 2026-11-28),
    # and its district is the answer that city's map gave when asked about the
    # point the same day.
    inside=(
        (-96.78528, 43.49523, "4659020-Southwest", "a point in Sioux Falls"),
        (-98.49395, 45.45131, "4600100-Southwest", "a point in Aberdeen"),
    ),
    # The Census's internal point of the place (TIGERweb, read 2026-11-28).
    outside=(
        (-103.21792, 44.07107, "a point in Rapid City, whose wards are not drawn"),
    ),
)

if __name__ == "__main__":
    cwm.main(SPEC, __doc__)
