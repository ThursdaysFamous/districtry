#!/usr/bin/env python3
"""
Build ms/data/app/ms-city-wards.json: the wards of the Mississippi cities whose
mayor and council this app names (data/app/ms-city-councils.json) and whose
current ward lines are confirmed, drawn by the `city-ward` layer in
ms/index.html.

WHICH CITIES. The council reader names the mayor and council of the 15 cities
above 25,000 people, and every one of the 15 elects members by ward. This
builder draws NINE of them, the ones whose ward map is published as a GIS layer
AND is confirmed as the plan in force (CITIES below, each entry's `evidence`).
The other six are not drawn, each for a measured reason (NOT_DRAWN), and their
City cards still name the mayor and council:

  Biloxi       its layer Wards2022 is the city's, and Ordinance 2468 (November
               16, 2021) redrew the wards on the 2020 census, but the layer's
               own population figures do not match the 2020 census blocks
               inside its lines (Ward 6 by 392 people) and on those blocks the
               wards are 15.7% apart, so whether the layer is the ordinance's
               plan is not established.
  Hattiesburg  its layer describes itself as digitized from the 2012
               ordinance, its own population figures sum to 45,991 against the
               2020 count of 48,730, and the council chose a new plan on
               January 18, 2022; whether the layer is that plan is not
               established.
  Horn Lake    the only layer is DeSoto County's, whose adoption date is empty
               for every Horn Lake ward (filled for Southaven, Olive Branch and
               Hernando), and the city publishes no ward map.
  Meridian,    each publishes its ward map as a PDF only.
  Madison,
  Greenville

THE LINES BETWEEN WARDS ARE EACH CITY'S OWN PUBLISHED MAP, never redrawn. A
ward line runs along streets, and nothing here can say better than the city
where it runs. Five layers are the city's own (Jackson, Gulfport, Olive Branch,
Tupelo, Oxford); one is DeSoto County's municipal ward layer, which carries the
date the city adopted the wards (Southaven); three are the Central Mississippi
Planning and Development District's (Clinton, Pearl, Brandon), and each of
those cities' websites links or embeds the planning district's map viewer for
the city, which opens with that ward layer shown (measured 2026-10-17 from each
viewer's web map: Clinton's Maps page links it as Zoning, Land Use, and
Infrastructure, beside the adopted ward plan itself as its Ward Map; Pearl's
site links it as its City Districts Map; Brandon's Interactive Map Viewer page
embeds it). Only the ward field is requested from each layer, plus the one field a witness reads (Southaven's adoption date, Oxford's
layer name for its at-large polygon, the total population four layers carry);
several of these layers also carry member names or population by race, and
none of that is asked for.

THE CITY'S OUTER EDGE IS THE CENSUS BUREAU'S MAP OF THE CITY (TIGERweb's
current incorporated place, the layer the City card reads), because the ward
layers run past their cities' limits and the cities' own counts end at them.
Measured 2026-10-17 on 2020 census blocks: Brandon's Ward 1 runs over 1.94 km2
outside the city where 195 people live, Jackson's Wards 4, 6 and 7 over three
blocks of 51 people outside it, and three pairs of neighbouring cities' layers
claim the same ground, all of it empty of people: Jackson and Pearl 131,085 m2,
99.6% of it inside Pearl on the Census map; Clinton and Jackson 73,449 m2, all
of it inside Clinton; Olive Branch and Southaven 5,736 m2, 88.7% of it inside
Southaven. Cut at the Census line, Jackson's, Clinton's and
Brandon's wards hold exactly the people each layer's own population field
gives, ward by ward, and Pearl's do in five wards of six (OWN_POPULATION). So
the cut is where the cities' plans end, and it is also what keeps the ward card
from naming a ward of a city the City card says a point is not in.

THE GATES, ASKED OF EVERY CITY ON EVERY BUILD
---------------------------------------------
1. THE WARDS ARE THE ROSTER'S. The layer's ward numbers must be exactly the
   ward seats ms-city-councils.json names for the city ("Ward 1".."Ward N").
2. THE WITNESS STILL SAYS WHAT IT SAID. Each entry pins the evidence the build
   can re-read: the layer's own name ("Wards 12-5-2023"), or Southaven's
   adoption date in the county's layer. A renamed layer or a new adoption date
   is a redistricting until a person has read it, so the build stops.
3. THE PEOPLE ARE PINNED. Each ward's people on the 2020 census, counted by
   every populated block's internal point inside the ward as cut at the city's
   limits, are pinned per ward (`people`), and so are the people the cut takes
   away (`outside`) and the people inside the limits whom no ward holds
   (`gap`). A line that moves moves people, so a city that redraws its wards
   stops the build here even with the same number of wards, and so does a
   Census line that moves. The spread between the largest and smallest ward
   prints on every run.
4. THE CITY'S OWN COUNT, where its layer publishes one, must equal those
   people ward by ward, except a difference recorded with its reason
   (OWN_POPULATION).
5. TILING against the same Census place: the wards' area over the place's must
   sit near 1, and the ground inside the place that no ward holds has per-city
   ceilings at about 2.5 times what was measured on 2026-10-17, as Iowa's ward
   builder sets its own. Its compact parts print on every run. Measured that
   day, they hold nobody and each lies inside the city on the 2020 census's map
   as well as today's: in Jackson four dry parcels of 4 to 10 ha, three pieces
   lying mostly or wholly in the Pearl River on the Census Bureau's water map
   and one dry part of 0.36 ha, and in Oxford one of 10.8 ha. A reader who
   clicks there is told the city's ward map draws no ward there.
6. NO TWO CITIES CLAIM ONE PLACE. Cut at the Census places, which do not
   overlap, two cities' wards share no ground. In the drawn file the one place
   where they do is recorded in ACCEPTED_OVERLAPS, a hairline on the line
   between Jackson and Pearl, and the ward card names both cities' wards there.
7. SIMPLIFICATION KEEPS EVERY ANSWER BUT THE RECORDED ONES. All nine cities are
   simplified in one shared topology (Douglas-Peucker, interval 3 m, which
   bounds how far the drawn line can stray from the city's), so a line two
   wards share is drawn once. Then: every populated 2020 block gets the same
   wards from the drawn file as from the cut wards, the true line strays no
   more than FIDELITY_MAX_M from the drawn one, no ward loses a ring, 4,000
   seeded points per city agree at 99.5% or better, and the drawing adds no
   overlap at those points. Three exceptions were measured on 2026-10-17, and
   each is a declaration checked on every build, which fails when a declaration
   stops matching what it describes as well as when something new appears: a
   1.55 m2 sliver of Oxford's Ward 5 that the drawing removes
   (ACCEPTED_DROPPED_PARTS), one Pearl block of 4 people that the drawn line
   puts in Ward 6, where the city's own count has them (ACCEPTED_MOVED_BLOCKS),
   and the Jackson-Pearl hairline (ACCEPTED_OVERLAPS).

Oxford's six wards are 20.0% apart on the 2020 census, the widest of the nine;
its map is the one the Board of Aldermen approved on May 19, 2023 (the city's
signed PDF, which this layer matches), and why the plan is that uneven is not
established. Olive Branch's wards hold 6,839 people who lived outside the city
on the 2020 census's map and inside it on today's, because the city has
annexed ground since and its ward map covers it.

Two of the maps draw neighbouring wards over each other in places, and that is
the map as published, not this builder: measured 2026-10-17, Oxford's puts
6,484 m2 in two wards across seven pairs of wards, the largest Wards 2 and 4
over 3,970 m2, and DeSoto County's puts 616 m2 of Southaven in two wards
across six pairs, the largest Wards 3 and 4 over 466 m2. No 2020 census point
lies in any of it, and the totals print on every run. The ward card names every
ward the map draws over a point, so a reader there is told both.

Usage:
    python3 ms/scripts/build_ms_city_wards.py            # fetch, check, write
    python3 ms/scripts/build_ms_city_wards.py --check    # offline, on what ships

The --check also holds two hand-written sentences to CITIES and NOT_DRAWN: the
City Ward card's empty state in ms/index.html and the layer's "Where it
applies" on the sources page (the worksheet's `applies`), so a city drawn or
dropped here fails the check until both say so.

WHAT WAS READ IS RECORDED. Nothing runs this build on a schedule, and a city
can redraw its wards inside a layer whose name stays the same (Gulfport's is
named Wards, Tupelo's WARDS), so the build writes
data/source/ms-city-wards.source.json: for every city, the layer's address and
name, the date the layer gives for its last edit, and a SHA-256 of the lines
the layer and the Census Bureau's map of the city served (lines_sha256). The
monthly source check (validate_sources.py) asks both questions again, the same
way (layer_params, place_params), and reports any city whose lines moved; the
--check holds the record to CITIES.
"""

import argparse
import atexit
import datetime
import hashlib
import json
import math
import os
import random
import re
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(_HERE)
# APPENDED, not inserted: the shared scripts/ directory has a
# build_legislative_boundaries.py of its own (Illinois's), and this file must
# import the one beside it.
sys.path.append(os.path.join(os.path.dirname(INSTANCE), "scripts"))
import aia_bundle  # noqa: E402  (FLEET_SHARED — the one copy of the pins)
from scraper_common import require_robots_allowed  # noqa: E402  (FLEET_SHARED)

sys.path.insert(0, _HERE)
import build_legislative_boundaries as blb  # noqa: E402  (same instance tree)
import build_ms_supervisor_districts as sb  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(blb.__file__)) == _HERE, blb.__file__

APP_DATA_DIR = os.path.join(INSTANCE, "data", "app")
OUT = os.path.join(APP_DATA_DIR, "ms-city-wards.json")
SOURCE_RECORD = os.path.join(INSTANCE, "data", "source", "ms-city-wards.source.json")
ROSTER_FILE = os.path.join(APP_DATA_DIR, "ms-city-councils.json")
COUNTIES_FILE = os.path.join(APP_DATA_DIR, "state-counties.json")

USER_AGENT = "districtry/1.0 (+https://districtry.com/ms/)"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}
LABEL = "ms-build-ms-city-wards"
TIGERWEB_PLACE = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                  "Places_CouSub_ConCity_SubMCD/MapServer/4")
CMPDD = "https://gis.cmpdd.org/server/rest/services/Hosted/"
# gis.cmpdd.org serves only its leaf certificate; the chain is completed from
# scripts/aia_bundle.py's pinned intermediate, never by turning verification off.
PINNED_CHAINS = {"gis.cmpdd.org": "godaddy-g2"}
MIN_DELAY_S = 1.0

MAPSHAPER = "mapshaper@0.6.102"
SIMPLIFY = ["dp", "interval=3", "keep-shapes"]
PRECISION = "0.000001"
FIDELITY_MAX_M = 4.0
AGREEMENT_SAMPLES = 4000
MIN_AGREEMENT = 0.995
COMPACTNESS_CEILING = 0.30
COMPACTNESS_MIN_AREA_M2 = 2000.0
IDENTITY_RATIO_LO = 0.90
IDENTITY_RATIO_HI = 1.15
# Where two cities' cut wards meet along the Census line between them, the
# arithmetic of the cut leaves slivers of no real size (measured 2026-10-17:
# two, of 4e-09 and 4e-08 m2). A part this large or larger is ground both
# cities claim: none is allowed in the cut wards, and in the drawn file each
# must be one ACCEPTED_OVERLAPS records.
OVERLAP_MIN_M2 = 0.01
# A declaration matches the part or block it names when its point is within
# this distance and, for an area, the area within this share.
DECLARED_WITHIN_M = 1.0
DECLARED_AREA_SHARE = 0.10


def _int(v):
    return int(str(v).strip())


def _ward_word(v):
    """'Ward 3' -> 3."""
    s = str(v).strip()
    if not s.lower().startswith("ward "):
        raise ValueError("expected 'Ward N', got %r" % s)
    return int(s[5:])


def _cmpdd(service, layer):
    return "%s%s/FeatureServer/%d" % (CMPDD, service, layer)


# Each entry: the city's Census id and name, the layer, the where clause, the
# field carrying the ward and how to read it, any field a witness reads, the
# page a reader can open, the sentence the card prints about where the lines
# come from, the evidence that the plan is in force, the witness the build
# re-reads, each ward's people on the 2020 census (measured 2026-10-17), and
# the two tiling ceilings (uncovered sq mi, largest uncovered part m2), set at
# about 2.5 times what was measured, as Iowa's are.
CITIES = [
    dict(geoid="2836000", city="Jackson",
         layer="https://services2.arcgis.com/n0wqzAPJddc1vROD/arcgis/rest/services/"
               "Jackson_Adopted_Wards_2024/FeatureServer/0",
         where="1=1", field="Ward", read=_int,
         page="https://jacksonms.gov/government/city-council/ward-maps/",
         source="the City of Jackson's ward map, the one its Ward Maps page shows, "
                "in a layer named Jackson Adopted Wards 2024",
         evidence="The city's Ward Maps page embeds this layer, named Adopted Wards "
                  "2024, and its own population field gives, ward by ward, the 2020 "
                  "census's people inside its lines cut at the city's limits: "
                  "153,701 in all, Jackson's 2020 count.",
         witness={"layer_name": "Jackson_Adopted_Wards_2024"},
         own="Population",
         people={"1": 22988, "2": 22542, "3": 21567, "4": 21122, "5": 21358, "6": 23102,
                 "7": 21022}, outside=51, gap=0,
         max_sqmi=3.5, max_part_m2=2060000),
    dict(geoid="2829700", city="Gulfport",
         layer="https://maps.gulfport-ms.gov/arcgis/rest/services/CityServices/"
               "GPT_WardsVotingPrecinct_2025/MapServer/2",
         where="1=1", field="WARD", read=_int,
         page="https://www.gulfport-ms.gov/government/city_council.php",
         source="the City of Gulfport's own map server, in its 2025 service for "
                "wards, voting precincts and polling places",
         evidence="The city's own map server publishes these wards in its 2025 "
                  "elections service (source table Wards_2025), and the city put an "
                  "identical copy online in September 2026. No adoption date was "
                  "found; on the 2020 census the seven wards are 8.1% apart.",
         witness={"layer_name": "Wards"},
         own=None,
         people={"1": 10218, "2": 10610, "3": 10232, "4": 10295, "5": 10287, "6": 10226,
                 "7": 11058}, outside=0, gap=0,
         max_sqmi=1.0, max_part_m2=525000),
    dict(geoid="2869280", city="Southaven",
         layer="https://services6.arcgis.com/4Zxj9BGpFPVGgwpo/arcgis/rest/services/"
               "Municipal_Wards/FeatureServer/17",
         where="CITY='Southaven'", field="Ward", read=_int, extra=["ADOPTED"],
         page="https://southaven.org/550/Wards",
         source="DeSoto County's map of its cities' wards, which records that "
                "Southaven adopted these wards on June 18, 2024",
         evidence="DeSoto County's municipal ward layer records ADOPTED 2024-06-18 "
                  "on every Southaven ward, and the city's Wards page links its 2024 "
                  "ward map.",
         witness={"adopted": "2024-06-18"},
         own=None,
         people={"1": 9221, "2": 9471, "3": 8790, "4": 8788, "5": 8727, "6": 9638},
         outside=13, gap=0,
         max_sqmi=0.13, max_part_m2=92000),
    dict(geoid="2854040", city="Olive Branch",
         layer="https://services9.arcgis.com/VGtdH6iTQlVulSnr/arcgis/rest/services/"
               "Olive_Branch_Wards/FeatureServer/0",
         where="1=1", field="Ward", read=_int,
         page="https://www.obms.us/237/Interactive-City-Maps",
         source="the City of Olive Branch's official ward map, the one its "
                "Interactive City Maps page links",
         evidence="The city's Find My Ward Map links this layer (Municipal_Wards_"
                   "FINAL_2022), and DeSoto County's copy of the same wards records "
                   "that the city adopted them on June 7, 2022.",
         witness={"layer_name": "Municipal_Wards_FINAL_2022"},
         own=None,
         people={"1": 7594, "2": 7793, "3": 7940, "4": 7732, "5": 7929, "6": 7562},
         outside=0, gap=0,
         max_sqmi=0.15, max_part_m2=124000),
    dict(geoid="2874840", city="Tupelo",
         layer="https://services1.arcgis.com/K2lG4DOeDaa3nZkf/arcgis/rest/services/"
               "WARDS/FeatureServer/0",
         where="1=1", field="DIST_ID", read=_int,
         page="https://www.tupeloms.gov/departments/development-services/"
              "gis-maps-location-information",
         source="the City of Tupelo's ward map, the one its GIS maps page links",
         evidence="The city's GIS maps page links this layer as its ward map, "
                  "described as the current aldermen wards (created July 2023); it "
                  "differs from the city's 2013 wards, and on the 2020 census the "
                  "seven wards are 8.5% apart. No adoption date was found.",
         witness={"layer_name": "WARDS"},
         own=None,
         people={"1": 5184, "2": 5643, "3": 5363, "4": 5293, "5": 5482, "6": 5380,
                 "7": 5578}, outside=0, gap=0,
         max_sqmi=0.02, max_part_m2=22000),
    dict(geoid="2814420", city="Clinton",
         layer=_cmpdd("Clinton_Feature_Layer", 41),
         where="1=1", field="name", read=_ward_word,
         page="https://clintonms.org/maps/",
         source="the Central Mississippi Planning and Development District's map "
                "of the ward plan Clinton adopted on December 5, 2023, shown in the "
                "map viewer the city's Maps page links",
         evidence="The layer is named Wards 12-5-2023, the date of the city's "
                  "Adopted Ward Plan, and its own population field gives the 2020 "
                  "census's people inside its lines in every ward. The city's Maps "
                  "page links the planning district's map viewer, which opens with "
                  "this layer shown, and links the adopted plan itself as its Ward "
                  "Map.",
         witness={"layer_name": "Wards 12-5-2023"},
         own="population",
         people={"1": 4619, "2": 4547, "3": 4753, "4": 4670, "5": 4669, "6": 4842},
         outside=0, gap=0,
         max_sqmi=0.014, max_part_m2=23000),
    dict(geoid="2855760", city="Pearl",
         layer=_cmpdd("Pearl_Viewer_Feature_Service", 37),
         where="1=1", field="name", read=_ward_word,
         page="https://www.cityofpearl.com/government/board-of-aldermen/",
         source="the Central Mississippi Planning and Development District's map "
                "of Pearl's wards, in a layer named Adopted Pearl Wards Effective "
                "9-1-24, shown in the map viewer the city's website links as its "
                "City Districts Map",
         evidence="The city's website links the planning district's map viewer as "
                  "its City Districts Map, and the viewer opens with this layer "
                  "shown, titled New Wards Effective 9-1-24. "
                  "The layer is named Adopted Pearl Wards Effective 9-1-24, and its "
                  "own population field gives the 2020 census's people inside its "
                  "lines in five wards of six (Ward 6 by 4 people, OWN_POPULATION).",
         witness={"layer_name": "Adopted Pearl Wards Effective 9-1-24"},
         own="population",
         people={"1": 4513, "2": 4649, "3": 4359, "4": 4541, "5": 4502, "6": 4547},
         outside=0, gap=4,
         max_sqmi=0.015, max_part_m2=8900),
    dict(geoid="2854840", city="Oxford",
         layer="https://services3.arcgis.com/HJKXwJwr6cXL7ioD/arcgis/rest/services/"
               "2023_Wards/FeatureServer/0",
         where="1=1", field="LABEL2", read=_int, extra=["LAYER"],
         # The layer also holds one polygon for the at-large seat, the whole city.
         skip={"LAYER": "VotingWard-At-Large"},
         page="https://www.oxfordms.net/board-of-aldermen",
         source="the City of Oxford's ward map, the one its Board of Aldermen page "
                "links, which the board approved on May 19, 2023",
         evidence="The city's Board of Aldermen page links this layer as its "
                  "Interactive Ward Map ('Effective June 19, 2023'), and it matches "
                  "the city's 2023 Voting Ward Map, approved by the Board of Aldermen "
                  "on May 19, 2023 and signed by the mayor and the city clerk.",
         witness={"layer_name": "2023 Wards"},
         own=None,
         people={"1": 3873, "2": 4412, "3": 4417, "4": 4132, "5": 3868, "6": 4714},
         outside=0, gap=0,
         max_sqmi=0.20, max_part_m2=270000),
    dict(geoid="2808300", city="Brandon",
         layer=_cmpdd("Brandon_Feature_Layer", 2),
         where="1=1", field="name", read=_ward_word,
         page="https://brandonms.org/business/economic-development/interactive-map-viewer/",
         source="the Central Mississippi Planning and Development District's map "
                "of Brandon's wards, in a layer named Wards (Adopted 1/18/2022), "
                "shown in the map viewer the city's website embeds",
         evidence="The layer is named Wards (Adopted 1/18/2022) and its own "
                  "population field gives, ward by ward, the 2020 census's people "
                  "inside its lines cut at the city's limits; the city's own picture "
                  "of the map is dated March 7, 2022. The city's Interactive Map "
                  "Viewer page embeds the planning district's map viewer, which "
                  "opens with this layer shown.",
         witness={"layer_name": "Wards (Adopted 1/18/2022)"},
         own="population",
         people={"1": 4251, "2": 4219, "3": 4219, "4": 4177, "5": 4112, "6": 4160},
         outside=195, gap=0,
         max_sqmi=0.010, max_part_m2=7700),
]

NOT_DRAWN = {
    "2806220": "Biloxi: the layer's own population figures do not match the 2020 "
               "census blocks inside its lines, so whether it is the 2021 ordinance's "
               "plan is not established",
    "2831020": "Hattiesburg: the layer describes itself as the 2012 ordinance's lines "
               "and the council chose a new plan in January 2022",
    "2833700": "Horn Lake: no adoption date for its wards anywhere, and no ward map "
               "on the city's site",
    "2846640": "Meridian: ward map published as a PDF only",
    "2844520": "Madison: ward map published as a PDF only",
    "2829180": "Greenville: ward map published as a PDF only, and the city's site "
               "names no council member",
}

# Where a city's own population figure for a ward differs from the people the
# 2020 census puts inside that ward as cut at the city's limits: the difference
# and why, re-measured on every build. One, measured 2026-10-17.
OWN_POPULATION = {
    "2855760": {
        "6": (-4, "census block 281210202172041, 4 people, lies inside Pearl's limits "
                  "and its census point 0.7 m outside Pearl's Ward 6 on the city's map; "
                  "the city's own count puts those 4 people in Ward 6, and they are "
                  "this city's `gap`"),
    },
}

# What the drawn file answers differently from the cut wards. Each was measured
# on 2026-10-17 and each is checked on every build: the build fails when
# something not recorded here appears, and when a record no longer matches the
# part, block or overlap it names, so none can outlive what it describes.
#
# A part of a cut ward that the drawing removes. Matched by its point (the
# part's own representative point, to 6 decimals) within DECLARED_WITHIN_M,
# its area within DECLARED_AREA_SHARE and its vertex count; then the cut wards
# must answer `before` there and the drawn file `after`.
ACCEPTED_DROPPED_PARTS = [
    dict(city="Oxford", ward="5", lat=34.367176, lng=-89.548760, m2=1.55, verts=3,
         before=["5"], after=[],
         why="a three-cornered sliver of Ward 5 on the city's map, inside the city "
             "where its limits run around a 1.8 km2 hole in the Census Bureau's map "
             "of the city, and 3.2 m from the rest of the ward, the ground between "
             "them being in Ward 5 on the city's map and outside the city on the "
             "Census Bureau's; no census point is inside it, and the ground 2 to 4 m "
             "around it is in no ward on the cut wards either",
         date="2026-10-17"),
]

# A populated 2020 census block whose internal point the drawn file puts in
# other wards than the cut wards do, by its GEOID.
ACCEPTED_MOVED_BLOCKS = {
    "281210202172041": dict(
        city="Pearl", people=4, before=[], after=["6"],
        why="the block lies inside Pearl's limits and its census point 0.66 m outside "
            "Ward 6 on the city's map; the drawn line puts it in Ward 6, which is "
            "where the city's own count has these 4 people (OWN_POPULATION)",
        date="2026-10-17"),
}

# Ground two cities' drawn wards both cover, part by part, matched by the
# part's representative point within DECLARED_WITHIN_M, its area within
# DECLARED_AREA_SHARE and the wards that cover it.
ACCEPTED_OVERLAPS = [
    dict(wards=[("Jackson", "7"), ("Pearl", "6")], lat=32.287114, lng=-90.070808,
         m2=2.34,
         why="a hairline 104 m long and on average 2 cm wide on the line between the "
             "two cities, inside Pearl on the Census Bureau's map: there Pearl's Ward "
             "6 is cut at that line, Jackson's own Ward 7 line runs up to 0.3 m inside "
             "Jackson, and the two lines, simplified each on its own, cross. The ward "
             "card names both cities' wards at a point both cover",
         date="2026-10-17"),
]

# Every drawn ward's card says where its line comes from: the city's map, then
# the edge it is cut at.
EDGE = ", ending at the city's limits as the Census Bureau maps them"

PROPS = ("geoid", "city", "ward", "seat", "source", "sourceUrl")


def fail(msg):
    raise SystemExit("build-ms-city-wards: FATAL: %s" % msg)


# ---------------------------------------------------------------- fetching --
_BUNDLES = {}
_ROBOTS = {}
_LAST = {}


def _bundle(host):
    key = PINNED_CHAINS.get(host)
    if key is None:
        return None
    if key not in _BUNDLES:
        path = aia_bundle.ca_bundle(LABEL, key)
        atexit.register(lambda p=path: os.path.exists(p) and os.remove(p))
        _BUNDLES[key] = path
    return _BUNDLES[key]


def _fetch_json(url, params=None):
    """GET one url as this builder's client, after asking its host's robots.txt
    about that url's own path, waiting a second between requests to one host,
    with the pinned chain where the host needs one."""
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname
    bundle = _bundle(host)
    if (host, parts.path) not in _ROBOTS:
        why = require_robots_allowed(url, USER_AGENT, headers=HEADERS, label=LABEL,
                                     verify=bundle)
        _ROBOTS[(host, parts.path)] = why
        print("robots.txt %s%s: %s" % (host, parts.path, why), file=sys.stderr)
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    ctx = ssl.create_default_context(cafile=bundle) if bundle else None
    for attempt in range(4):
        wait = MIN_DELAY_S - (time.time() - _LAST.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(full, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                body = resp.read()
            _LAST[host] = time.time()
            break
        except Exception as err:  # noqa: BLE001 — retried, then raised
            _LAST[host] = time.time()
            if attempt == 3:
                raise
            print("city-wards: retrying %s after %s" % (host, err), file=sys.stderr)
            time.sleep(2 ** (attempt + 1))
    if body[:2] == b"\x1f\x8b":
        import gzip  # noqa: PLC0415
        body = gzip.decompress(body)
    data = json.loads(body.decode("utf-8"))
    if isinstance(data, dict) and "error" in data:
        # An ArcGIS error is an object, not an empty answer.
        fail("%s answered an error: %r" % (url, data["error"]))
    return data


def layer_params(c):
    """The query the build sends a city's ward layer, with only the fields it
    reads. The monthly source check sends the same one, so the two read the
    same lines."""
    fields = [c["field"]] + list(c.get("extra") or []) + ([c["own"]] if c.get("own") else [])
    return {"where": c["where"], "outFields": ",".join(fields), "returnGeometry": "true",
            "outSR": "4326", "geometryPrecision": "6", "f": "json"}


def place_params(c):
    """The query for the Census Bureau's map of the city, shared the same way."""
    return {"where": "GEOID='%s'" % c["geoid"], "outFields": "GEOID,BASENAME",
            "returnGeometry": "true", "outSR": "4326", "geometryPrecision": "6", "f": "json"}


def lines_sha256(fc, c=None):
    """A SHA-256 of the lines in one answer to layer_params or place_params:
    every ring as served, at the six decimals asked for, each feature keyed by
    its ward read this builder's way (the Census place by nothing), with the
    features and each feature's rings put in one order. The build records it
    for every city's ward layer and place (SOURCE_RECORD), and the monthly
    source check asks the same two questions and compares, because a city can
    move its lines inside a layer whose name stays the same: Gulfport's layer
    is named Wards and Tupelo's WARDS."""
    skip = (c or {}).get("skip") or {}
    rows = []
    for f in fc.get("features") or []:
        a = f.get("attributes") or {}
        if skip and all(a.get(k) == v for k, v in skip.items()):
            continue
        key = c["read"](a.get(c["field"])) if c else 0
        rings = sorted([[round(p[0], 6), round(p[1], 6)] for p in ring]
                       for ring in (f.get("geometry") or {}).get("rings") or [])
        rows.append([key, rings])
    rows.sort()
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode("ascii")).hexdigest()


def fetch_layer(c):
    """(layer meta, [GeoJSON-shaped features], the answer as served)."""
    meta = _fetch_json(c["layer"], {"f": "json"})
    fc = _fetch_json(c["layer"] + "/query", layer_params(c))
    if fc.get("exceededTransferLimit"):
        fail("%s: the layer hit its transfer limit" % c["city"])
    return meta, sb.esri_features(fc, c["layer"], c["field"]), fc


def fetch_place(c):
    """(the Census place as a GeoJSON-shaped feature, the answer as served)."""
    fc = _fetch_json(TIGERWEB_PLACE + "/query", place_params(c))
    feats = sb.esri_features(fc, TIGERWEB_PLACE, "GEOID")
    if len(feats) != 1:
        fail("%s: TIGERweb returned %d places for GEOID %s" % (c["city"], len(feats), c["geoid"]))
    name = feats[0]["properties"].get("BASENAME")
    if name != c["city"]:
        fail("%s: GEOID %s is %r on TIGERweb" % (c["city"], c["geoid"], name))
    return feats[0], fc


# ------------------------------------------------------------- the checks --
def roster_wards():
    """{geoid: [ward numbers]} from the council roster's "Ward N" seats."""
    with open(ROSTER_FILE, encoding="utf-8") as fh:
        roster = json.load(fh)
    out = {}
    for geoid, city in roster.items():
        nums = []
        for seat in city.get("seats") or []:
            label = seat.get("seat") or ""
            if label.startswith("Ward "):
                nums.append(int(label[5:]))
        out[geoid] = sorted(nums)
    return out, roster


def _date(ms):
    if ms is None:
        return None
    return datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc).strftime("%Y-%m-%d")


def wards_of(c, meta, feats, want):
    """{ward: shapely geometry} at the layer's full precision, after the ward
    set and the witness are checked."""
    from shapely.ops import unary_union
    skip = c.get("skip") or {}
    kept = []
    for f in feats:
        p = f["properties"]
        if skip and all(p.get(k) == v for k, v in skip.items()):
            continue
        if not f.get("geometry"):
            fail("%s: a feature has no geometry (%r)" % (c["city"], p.get(c["field"])))
        kept.append(f)
    if skip and len(kept) != len(feats) - 1:
        fail("%s: expected exactly one feature matching %r to set aside, found %d"
             % (c["city"], skip, len(feats) - len(kept)))
    groups = {}
    for f in kept:
        try:
            n = c["read"](f["properties"][c["field"]])
        except (TypeError, ValueError):
            fail("%s: a ward this builder does not read: %r"
                 % (c["city"], f["properties"].get(c["field"])))
        groups.setdefault(n, []).append(
            sb.checked_shape(f["geometry"], "%s ward %s" % (c["city"], n)))
    got = sorted(groups)
    if got != want:
        fail("%s: the layer holds wards %s and the council roster names seats for "
             "wards %s. A different set is a redistricting or the layer changing "
             "shape, and both need reading before anything ships." % (c["city"], got, want))
    w = c["witness"]
    if "layer_name" in w:
        name = meta.get("name")
        if w["layer_name"] is None:
            print("  layer name %r (not pinned yet)" % name, file=sys.stderr)
        elif name != w["layer_name"]:
            fail("%s: the layer is now named %r, not %r. A renamed ward layer is a new "
                 "plan until a person has read it." % (c["city"], name, w["layer_name"]))
    if "adopted" in w:
        dates = sorted(set(_date(f["properties"].get("ADOPTED")) for f in kept))
        if dates != [w["adopted"]]:
            fail("%s: the county's layer gives adoption dates %s, not %s. A new adoption "
                 "date is a redistricting until a person has read it."
                 % (c["city"], dates, w["adopted"]))
    return {n: unary_union(gs) for n, gs in groups.items()}, kept


def own_counts(c, kept):
    """{ward: people} as the city's own layer counts them, or None."""
    if not c.get("own"):
        return None
    out = {}
    for f in kept:
        n = c["read"](f["properties"][c["field"]])
        v = f["properties"].get(c["own"])
        if v is None:
            fail("%s ward %s: the layer no longer gives %s" % (c["city"], n, c["own"]))
        out[n] = out.get(n, 0) + int(v)
    return out


def polygonal(g, what):
    """The polygon parts of a shapely result: cutting can leave lines and points
    where two edges touch."""
    from shapely.geometry import MultiPolygon
    if g.is_empty:
        fail("%s is empty" % what)
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    polys = []
    for part in getattr(g, "geoms", []):
        if part.geom_type == "Polygon":
            polys.append(part)
        elif part.geom_type == "MultiPolygon":
            polys.extend(part.geoms)
    if not polys:
        fail("%s has no area" % what)
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)


def cut(c, wards, place, lat0):
    """Each ward cut at the city's limits as the Census place draws them."""
    out = {}
    for n, g in sorted(wards.items()):
        out[n] = polygonal(g.intersection(place), "%s ward %s cut at the city's limits"
                           % (c["city"], n))
        lost = _m2(g.difference(place), lat0)
        if lost > 1.0:
            print("  ward %s: %.0f m2 of the city's map lies outside the Census place"
                  % (n, lost), file=sys.stderr)
    return out


def _lat0(geoms):
    ys = [g.bounds[1] for g in geoms] + [g.bounds[3] for g in geoms]
    return (min(ys) + max(ys)) / 2.0


def _m2(g, lat0):
    """Area in square metres by a local plane at lat0, as Iowa's builder does."""
    return g.area * 111320.0 * math.cos(math.radians(lat0)) * 110540.0


def _perimeter_m(g, lat0):
    from shapely.affinity import scale
    return scale(g, xfact=111320.0 * math.cos(math.radians(lat0)), yfact=110540.0,
                 origin=(0, 0)).length


def tiling(c, wards, place, lat0):
    """The wards' area over the Census place's, and the ground inside the place
    that no ward holds. Who lives on that ground is people()'s `gap`."""
    from shapely.ops import unary_union
    union = unary_union(list(wards.values()))
    ratio = _m2(union, lat0) / _m2(place, lat0)
    gap = place.difference(union)
    parts = [] if gap.is_empty else (list(gap.geoms) if hasattr(gap, "geoms") else [gap])
    measured = []
    for p in parts:
        if p.geom_type != "Polygon":
            continue
        a = _m2(p, lat0)
        per = _perimeter_m(p, lat0)
        pp = 4.0 * math.pi * a / (per * per) if per else 0.0
        measured.append((a, pp))
    total_sqmi = sum(a for a, _ in measured) / 2.58999e6
    largest = max((a for a, _ in measured), default=0.0)
    compact = [a for a, pp in measured if a >= COMPACTNESS_MIN_AREA_M2 and pp > COMPACTNESS_CEILING]
    print("  tiling: wards/place area %.4f; %.4f sq mi of the place in no ward, in %d parts, "
          "largest %.0f m2; %d compact parts of %.0f m2 in all"
          % (ratio, total_sqmi, len(measured), largest, len(compact), sum(compact)),
          file=sys.stderr)
    problems = []
    if not IDENTITY_RATIO_LO <= ratio <= IDENTITY_RATIO_HI:
        problems.append("the wards' area is %.3f of the Census place's; outside %.2f-%.2f "
                        "this is not the same city" % (ratio, IDENTITY_RATIO_LO, IDENTITY_RATIO_HI))
    if c["max_sqmi"] is None:
        problems.append("no tiling ceiling is pinned yet (measured %.4f sq mi, largest part "
                        "%.0f m2)" % (total_sqmi, largest))
    elif total_sqmi > c["max_sqmi"] or largest > c["max_part_m2"]:
        problems.append("the ground in no ward (%.3f sq mi, largest part %.0f m2) has grown "
                        "past its measured ceiling (%.2f sq mi / %.0f m2)"
                        % (total_sqmi, largest, c["max_sqmi"], c["max_part_m2"]))
    return problems


def counties_for(geom):
    from shapely.geometry import shape
    with open(COUNTIES_FILE, encoding="utf-8") as fh:
        counties = json.load(fh)
    out = []
    for f in counties["features"]:
        cg = shape(f["geometry"])
        if cg.intersects(geom) and cg.intersection(geom).area > 1e-7:
            out.append(f["properties"]["GEOID"][2:])
    return sorted(out)


_BLOCKS = {}


def blocks_for(c3):
    """[(lng, lat, people, GEOID, housing units)] for every populated 2020
    block in the county."""
    if c3 not in _BLOCKS:
        _BLOCKS[c3] = sb.fetch_blocks(c3, detail=True)
    return _BLOCKS[c3]


def people(c, raw, wards, place):
    """{ward: people} on the 2020 census by block internal point, inside the
    wards as cut at the city's limits; with the people the cut takes away
    (inside the city's map, outside the Census place) and the people inside the
    place whom no ward holds. Also the blocks used, for the drawn-file check."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    from shapely.prepared import prep
    raw_union = unary_union(list(raw.values()))
    # Only the blocks inside the city's own envelope, widened by about 100 m:
    # a drawn ward keeps a subset of the cut ward's vertices, so it cannot reach
    # a block outside that envelope either.
    x0, y0, x1, y1 = raw_union.union(place).bounds
    blocks = []
    for c3 in counties_for(raw_union.union(place)):
        blocks.extend(b for b in blocks_for(c3)
                      if x0 - 0.001 <= b[0] <= x1 + 0.001 and y0 - 0.001 <= b[1] <= y1 + 0.001)
    ready = {n: prep(g) for n, g in wards.items()}
    in_raw, in_place = prep(raw_union), prep(place)
    pop = {n: 0 for n in wards}
    outside = gap = 0
    for x, y, n, _geoid, _hu in blocks:
        pt = Point(x, y)
        hits = [w for w, g in ready.items() if g.contains(pt)]
        if len(hits) > 1:
            fail("%s: %d people live in a block the city's layer puts in two wards"
                 % (c["city"], n))
        if hits:
            pop[hits[0]] += n
        elif in_place.contains(pt):
            gap += n
        elif in_raw.contains(pt):
            outside += n
    vals = list(pop.values())
    ideal = sum(vals) / float(len(vals))
    spread = 100.0 * (max(vals) - min(vals)) / ideal
    print("  people on the 2020 census: %s; %d in all, %.1f%% apart; %d inside the city's "
          "map and outside its limits, %d inside its limits and in no ward"
          % (", ".join("%d: %d" % (w, pop[w]) for w in sorted(pop)), sum(vals), spread,
             outside, gap), file=sys.stderr)
    problems = []
    got = {str(k): v for k, v in sorted(pop.items())}
    if got != c["people"]:
        problems.append("the 2020 census puts %s in its wards, not the pinned %s. A line "
                        "that moved is a redistricting until a person has read it"
                        % (got, c["people"]))
    if outside != c["outside"]:
        problems.append("%d people live inside the city's map and outside its limits, not "
                        "the pinned %d. The city's map or the Census line has moved"
                        % (outside, c["outside"]))
    if gap != c["gap"]:
        problems.append("%d people live inside the city's limits and in no ward, not the "
                        "pinned %d. A reader at home there would be told no ward"
                        % (gap, c["gap"]))
    return problems, pop, blocks


def own_problems(c, pop, own):
    """The city's own count against the people inside its cut wards."""
    if own is None:
        return []
    diff = {str(n): pop[n] - own.get(n, 0) for n in pop if pop[n] != own.get(n, 0)}
    want = {w: d for w, (d, _why) in OWN_POPULATION.get(c["geoid"], {}).items()}
    print("  the city's own count: %s" % ("the same in every ward" if not diff else
                                          "differs by %s" % diff), file=sys.stderr)
    if diff != want:
        return ["the city's own count differs from the 2020 census's people in its cut wards "
                "by %s, where OWN_POPULATION records %s" % (diff, want)]
    return []


def _parts(g):
    """The polygon parts of a shapely geometry; an intersection can also hold
    the lines and points where two edges touch."""
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    out = []
    for part in getattr(g, "geoms", []):
        out.extend(_parts(part))
    return out


def _part_m2(p):
    return _m2(p, (p.bounds[1] + p.bounds[3]) / 2.0)


def _metres(a, b):
    """Metres between two (lng, lat) points, by a local plane."""
    lat = (a[1] + b[1]) / 2.0
    return math.hypot((a[0] - b[0]) * 111320.0 * math.cos(math.radians(lat)),
                      (a[1] - b[1]) * 110540.0)


def _matches(rec, part, m2):
    """Whether a recorded part is this one: its point and its area."""
    rp = part.representative_point()
    return (_metres((rp.x, rp.y), (rec["lng"], rec["lat"])) <= DECLARED_WITHIN_M
            and abs(m2 - rec["m2"]) <= DECLARED_AREA_SHARE * rec["m2"])


def _wards_text(wards):
    return " and ".join("%s Ward %s" % (c, w) for c, w in wards)


def cross_city(items, what, declared):
    """Ground two cities' wards both cover, part by part. `items` are
    {city, ward, shape, geometry}. In the cut wards there must be none; in the
    drawn file every part must be one `declared` records, and every record must
    still match a part."""
    from shapely.ops import unary_union
    by_city = {}
    for it in items:
        by_city.setdefault(it["city"], []).append(it)
    cities = {c: unary_union([it["shape"] for it in its]) for c, its in by_city.items()}
    names = sorted(cities)
    found = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if not cities[a].intersects(cities[b]):
                continue
            for part in _parts(cities[a].intersection(cities[b])):
                m2 = _part_m2(part)
                if m2 < OVERLAP_MIN_M2:
                    continue
                rp = part.representative_point()
                wards = sorted((it["city"], it["ward"]) for it in by_city[a] + by_city[b]
                               if blb._point_in_geometry((rp.x, rp.y), it["geometry"]))
                found.append((part, m2, rp, wards))
    problems, used = [], set()
    for part, m2, rp, wards in found:
        hit = [i for i, rec in enumerate(declared)
               if i not in used and _matches(rec, part, m2)
               and sorted(tuple(w) for w in rec["wards"]) == wards]
        if hit:
            used.add(hit[0])
            print("cross-city: in the %s, %s both cover %.2f m2 at %.6f,%.6f, as "
                  "ACCEPTED_OVERLAPS records" % (what, _wards_text(wards), m2, rp.y, rp.x),
                  file=sys.stderr)
        else:
            problems.append("%s: %s both cover %.2f m2 at %.6f,%.6f, which nothing records"
                            % (what, _wards_text(wards), m2, rp.y, rp.x))
    for i, rec in enumerate(declared):
        if i not in used:
            problems.append("%s: ACCEPTED_OVERLAPS records %s covering %.2f m2 at %.6f,%.6f, "
                            "and no such overlap is there"
                            % (what, _wards_text(tuple(w) for w in rec["wards"]), rec["m2"],
                               rec["lat"], rec["lng"]))
    print("cross-city: in the %s, %d parts of %.2f m2 or more are covered by two cities' "
          "wards" % (what, len(found), OVERLAP_MIN_M2), file=sys.stderr)
    return problems


def own_overlaps(items, what):
    """Printed, never failed: ground a city's map puts in two of its own wards.
    It is the map as published, and the card names every ward there."""
    by_city = {}
    for it in items:
        by_city.setdefault(it["city"], []).append(it)
    out = []
    for city, its in sorted(by_city.items()):
        total, pairs, largest = 0.0, 0, None
        for i in range(len(its)):
            for j in range(i + 1, len(its)):
                a, b = its[i], its[j]
                if not a["shape"].intersects(b["shape"]):
                    continue
                m2 = sum(_part_m2(p) for p in _parts(a["shape"].intersection(b["shape"])))
                if m2 < OVERLAP_MIN_M2:
                    continue
                total += m2
                pairs += 1
                if largest is None or m2 > largest[0]:
                    largest = (m2, a["ward"], b["ward"])
        if pairs:
            out.append("%s %.0f m2 across %d pairs of wards, the largest Wards %s and %s "
                       "over %.0f m2" % (city, total, pairs, largest[1], largest[2], largest[0]))
    print("in two wards of one city, in the %s: %s" % (what, "; ".join(out) or "nowhere"),
          file=sys.stderr)


# ---------------------------------------------------------- simplifying -----
def _geojson(g):
    from shapely.geometry import mapping
    m = mapping(g)
    return json.loads(json.dumps(m))


def simplify_shared(exact):
    work = tempfile.mkdtemp(prefix="ms-wards-")
    src = os.path.join(work, "exact.json")
    dst = os.path.join(work, "simple.json")
    try:
        with open(src, "w") as fh:
            json.dump(exact, fh, separators=(",", ":"))
        proc = subprocess.run(
            ["npx", "--yes", MAPSHAPER, src, "-simplify"] + SIMPLIFY +
            ["-o", "precision=" + PRECISION, "format=geojson", dst],
            capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(dst):
            fail("mapshaper failed (%d): %s" % (proc.returncode, (proc.stderr or "")[-800:]))
        with open(dst) as fh:
            out = json.load(fh)
    finally:
        for p in (src, dst):
            if os.path.exists(p):
                os.remove(p)
        os.rmdir(work)
    if len(out.get("features") or []) != len(exact["features"]):
        fail("mapshaper returned %d features for %d" % (len(out.get("features") or []),
                                                          len(exact["features"])))
    return out


def _rings(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return sum(len(p) for p in polys)


def drawn_checks(exact, simple, blocks_by_city):
    """Every answer the cut wards give, the drawn file gives too, but the ones
    ACCEPTED_DROPPED_PARTS and ACCEPTED_MOVED_BLOCKS record."""
    from shapely.geometry import shape
    problems = []
    key = lambda f: (f["properties"]["geoid"], f["properties"]["ward"])  # noqa: E731
    src = {key(f): f for f in exact["features"]}
    new = {key(f): f for f in simple["features"]}
    if set(src) != set(new):
        fail("mapshaper changed the set of wards")
    geoid_of = {f["properties"]["city"]: f["properties"]["geoid"] for f in exact["features"]}
    city_of = {g: c for c, g in geoid_of.items()}
    models = {}
    for geoid in sorted(city_of):
        feats = [src[k] for k in sorted(src) if k[0] == geoid]
        models[geoid] = (blb._model(feats, "ward"), blb._model([new[key(f)] for f in feats], "ward"))

    def answers(geoid, pt):
        s_model, n_model = models[geoid]
        return sorted(blb._districts_at(s_model, pt)), sorted(blb._districts_at(n_model, pt))

    # parts the drawing removes: each recorded, each record still matching
    skip, dropped = set(), {}
    for rec in ACCEPTED_DROPPED_PARTS:
        geoid = geoid_of.get(rec["city"])
        f = src.get((geoid, rec["ward"]))
        if f is None:
            problems.append("ACCEPTED_DROPPED_PARTS records %s Ward %s, which is not drawn"
                            % (rec["city"], rec["ward"]))
            continue
        found = [p for p in _parts(shape(f["geometry"]))
                 if len(p.exterior.coords) - 1 == rec["verts"] and _matches(rec, p, _part_m2(p))]
        if len(found) != 1:
            problems.append("ACCEPTED_DROPPED_PARTS records a %.2f m2 part of %s Ward %s at "
                            "%.6f,%.6f, and the cut ward has %d such parts"
                            % (rec["m2"], rec["city"], rec["ward"], rec["lat"], rec["lng"],
                               len(found)))
            continue
        part = found[0]
        rp = part.representative_point()
        before, after = answers(geoid, (rp.x, rp.y))
        if (before, after) != (sorted(rec["before"]), sorted(rec["after"])):
            problems.append("ACCEPTED_DROPPED_PARTS: on the %.2f m2 part of %s Ward %s the cut "
                            "wards answer %s and the drawn file %s, not the recorded %s and %s"
                            % (_part_m2(part), rec["city"], rec["ward"], before, after,
                               rec["before"], rec["after"]))
            continue
        skip.add(tuple(tuple(v) for v in part.exterior.coords))
        dropped[(geoid, rec["ward"])] = dropped.get((geoid, rec["ward"]), 0) + 1
        print("dropped: %s Ward %s's %.2f m2 part at %.6f,%.6f is drawn as %s, as "
              "ACCEPTED_DROPPED_PARTS records" % (rec["city"], rec["ward"], _part_m2(part),
                                                  rp.y, rp.x, after or "no ward"),
              file=sys.stderr)
    # rings: none lost but the recorded ones
    for k in sorted(src):
        a, b = _rings(src[k]["geometry"]), _rings(new[k]["geometry"])
        if a - dropped.get(k, 0) != b:
            problems.append("%s Ward %s has %d rings on the cut wards and %d drawn, and "
                            "ACCEPTED_DROPPED_PARTS records %d dropped"
                            % (city_of[k[0]], k[1], a, b, dropped.get(k, 0)))
    # fidelity: the true line's stray from the drawn chord, on every ring the
    # drawing keeps
    worst = 0.0
    for k in sorted(src):
        idx = blb._seg_index(new[k])
        for ring in blb._rings_of(src[k]["geometry"]):
            if tuple(tuple(v) for v in ring) in skip:
                continue
            for v in ring[:-1]:
                gx, gy = int(math.floor(v[0] / 0.02)), int(math.floor(v[1] / 0.02))
                cand = []
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        cand += idx.get((gx + dx, gy + dy), ())
                if cand:
                    worst = max(worst, min(blb._point_to_segment_m(v, a, b) for a, b in cand))
    print("fidelity: the cut wards' lines stray at most %.2f m from the drawn ones (ceiling "
          "%.1f)" % (worst, FIDELITY_MAX_M), file=sys.stderr)
    if worst > FIDELITY_MAX_M:
        problems.append("the cut wards' lines stray %.2f m from the drawn ones, over %.1f m"
                        % (worst, FIDELITY_MAX_M))
    # people: every populated block, the same wards but the recorded ones
    moved = {}
    for geoid in sorted(models):
        for x, y, n, gid, _hu in blocks_by_city[geoid]:
            before, after = answers(geoid, (x, y))
            if before != after:
                moved[(city_of[geoid], gid)] = (n, before, after)
    print("people: %d of the 2020 census's residents get other wards from the drawn file "
          "than from the cut wards" % sum(v[0] for v in moved.values()), file=sys.stderr)
    want = {(rec["city"], gid): rec for gid, rec in ACCEPTED_MOVED_BLOCKS.items()}
    for (city, gid), (n, before, after) in sorted(moved.items()):
        rec = want.get((city, gid))
        said = "%s %s on the cut wards and %s drawn" % (city, before or "no ward",
                                                      after or "no ward")
        if rec is None:
            problems.append("block %s, %d people: %s, which nothing records" % (gid, n, said))
        elif (rec["people"], sorted(rec["before"]), sorted(rec["after"])) != (n, before, after):
            problems.append("block %s: ACCEPTED_MOVED_BLOCKS records %d people, %s to %s, and "
                            "the build finds %d people, %s" % (gid, rec["people"], rec["before"],
                                                              rec["after"], n, said))
        else:
            print("people: block %s, %d people, %s, as ACCEPTED_MOVED_BLOCKS records"
                  % (gid, n, said), file=sys.stderr)
    for (city, gid), rec in sorted(want.items()):
        if (city, gid) not in moved:
            problems.append("ACCEPTED_MOVED_BLOCKS records block %s in %s, and the drawn file "
                            "gives it the same wards as the cut wards" % (gid, city))
    # seeded points per city, the fleet's agreement gate, and no added overlap
    for geoid in sorted(models):
        s_model, n_model = models[geoid]
        xs = [b for _, _, bb in s_model for b in (bb[0], bb[2])]
        ys = [b for _, _, bb in s_model for b in (bb[1], bb[3])]
        rng = random.Random(int(geoid))
        agree = s_over = n_over = 0
        for _ in range(AGREEMENT_SAMPLES):
            pt = (rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys)))
            a = blb._districts_at(s_model, pt)
            b = blb._districts_at(n_model, pt)
            s_over += len(a) > 1
            n_over += len(b) > 1
            agree += sorted(a) == sorted(b)
        city = city_of[geoid]
        if agree < MIN_AGREEMENT * AGREEMENT_SAMPLES:
            problems.append("%s: %d of %d seeded points agree" % (city, agree, AGREEMENT_SAMPLES))
        if n_over > s_over:
            problems.append("%s: the drawing adds overlap (%d points against the cut wards' %d)"
                            % (city, n_over, s_over))
        print("agreement: %s %d of %d seeded points, overlap %d on the cut wards and %d drawn"
              % (city, agree, AGREEMENT_SAMPLES, s_over, n_over), file=sys.stderr)
    return problems


# ------------------------------------------------------------------ build --
def build():
    want, roster = roster_wards()
    for c in CITIES:
        if c["geoid"] not in roster:
            fail("%s is not in the council roster" % c["city"])
    drawn = {c["geoid"] for c in CITIES}
    for geoid in roster:
        if geoid not in drawn and geoid not in NOT_DRAWN:
            fail("%s is in the council roster and neither drawn nor recorded as not "
                 "drawn" % roster[geoid].get("name"))
    problems = []
    exact = {"type": "FeatureCollection", "features": []}
    blocks_by_city, cut_items, read = {}, [], {}
    for c in CITIES:
        print("%s (%s)" % (c["city"], c["layer"]), file=sys.stderr)
        meta, feats, served = fetch_layer(c)
        edited = (meta.get("editingInfo") or {}).get("dataLastEditDate") or \
            (meta.get("editingInfo") or {}).get("lastEditDate")
        print("  layer %r, last edited %s" % (meta.get("name"), _date(edited) or "not stated"),
              file=sys.stderr)
        raw, kept = wards_of(c, meta, feats, want[c["geoid"]])
        lat0 = _lat0(list(raw.values()))
        place_feat, place_served = fetch_place(c)
        place = sb.checked_shape(place_feat["geometry"], "%s place" % c["city"])
        read[c["geoid"]] = {"city": c["city"], "layer": c["layer"],
                            "layer_name": meta.get("name"),
                            "last_edited": _date(edited),
                            "lines_sha256": lines_sha256(served, c),
                            "place_sha256": lines_sha256(place_served)}
        wards = cut(c, raw, place, lat0)
        problems += ["%s: %s" % (c["city"], p) for p in tiling(c, wards, place, lat0)]
        p_problems, pop, blocks = people(c, raw, wards, place)
        problems += ["%s: %s" % (c["city"], p) for p in p_problems]
        problems += ["%s: %s" % (c["city"], p) for p in own_problems(c, pop, own_counts(c, kept))]
        blocks_by_city[c["geoid"]] = blocks
        for n in sorted(wards):
            cut_items.append(dict(city=c["city"], ward=str(n), shape=wards[n],
                                  geometry=_geojson(wards[n])))
            exact["features"].append({
                "type": "Feature",
                "properties": {"geoid": c["geoid"], "city": c["city"], "ward": str(n),
                               "seat": "Ward %d" % n, "source": c["source"] + EDGE,
                               "sourceUrl": c["page"]},
                "geometry": _geojson(wards[n]),
            })
    own_overlaps(cut_items, "cut wards")
    problems += cross_city(cut_items, "cut wards", [])
    simple = simplify_shared(exact)
    problems += drawn_checks(exact, simple, blocks_by_city)
    drawn_items = [dict(city=f["properties"]["city"], ward=f["properties"]["ward"],
                        shape=sb.checked_shape(f["geometry"], "drawn %s Ward %s"
                                               % (f["properties"]["city"], f["properties"]["ward"])),
                        geometry=f["geometry"]) for f in simple["features"]]
    own_overlaps(drawn_items, "drawn file")
    problems += cross_city(drawn_items, "drawn file", ACCEPTED_OVERLAPS)
    if problems:
        fail("refusing to write:\n  " + "\n  ".join(problems))
    out = {"type": "FeatureCollection", "features": []}
    for f in simple["features"]:
        out["features"].append({"type": "Feature",
                                "properties": {k: f["properties"][k] for k in PROPS},
                                "geometry": f["geometry"]})
    out["features"].sort(key=lambda f: (f["properties"]["city"], int(f["properties"]["ward"])))
    record = {
        "_about": ("GENERATED by ms/scripts/build_ms_city_wards.py. What each drawn city's "
                   "wards were read from when the shipped file was built: the ward layer's "
                   "address and name, the date the layer gives for its last edit, and a "
                   "SHA-256 of the lines the layer and the Census Bureau's map of the city "
                   "served (lines_sha256). The monthly source check asks both again and "
                   "compares; --check holds this record to CITIES."),
        "built": datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
        "cities": read,
    }
    check(out, record)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
        fh.write("\n")
    os.makedirs(os.path.dirname(SOURCE_RECORD), exist_ok=True)
    with open(SOURCE_RECORD, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("ms-city-wards -> %s: %d wards in %d cities, %d bytes; the lines read are recorded "
          "in %s" % (os.path.relpath(OUT, INSTANCE), len(out["features"]), len(CITIES),
                     os.path.getsize(OUT), os.path.relpath(SOURCE_RECORD, INSTANCE)),
          file=sys.stderr)


APP_FILE = os.path.join(INSTANCE, "index.html")
WORKSHEET_FILE = os.path.join(INSTANCE, "metro-worksheet.json")
_NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven",
                 "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
                 "fifteen")


def _city_list(text):
    """'Jackson, Gulfport and Brandon' -> ['Jackson', 'Gulfport', 'Brandon']."""
    head, sep, last = text.rpartition(" and ")
    if not sep:
        return [text.strip()]
    return [s.strip() for s in head.split(",")] + [last.strip()]


def check_stated_cities(roster):
    """Two sentences a reader is shown say which cities are drawn, and both are
    written by hand: the ward card's empty state in ms/index.html, and the
    sources page's "Where it applies" for this layer, which the worksheet
    carries. Each must name exactly the cities CITIES draws, give their count
    in words, and name no city NOT_DRAWN records, and the sources page must
    name exactly the NOT_DRAWN cities as the ones left out. A city added to or
    taken out of CITIES therefore fails here until both sentences say so."""
    drawn = [c["city"] for c in CITIES]
    left = [v.split(":", 1)[0] for v in NOT_DRAWN.values()]
    if set(roster) != {c["geoid"] for c in CITIES} | set(NOT_DRAWN):
        fail("CITIES and NOT_DRAWN together are not the council roster's %d cities"
             % len(roster))
    count = _NUMBER_WORDS[len(drawn)]
    with open(APP_FILE, encoding="utf-8") as fh:
        app = fh.read()
    at = app.find('id: "city-ward"')
    m = re.compile(r'emptyNote:\s*((?:"(?:[^"\\]|\\.)*"\s*\+\s*)*"(?:[^"\\]|\\.)*")\s*,'
                   ).search(app, at) if at >= 0 else None
    if m is None:
        fail("ms/index.html: no emptyNote found after the city-ward layer's id")
    note = "".join(json.loads(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"', m.group(1)))
    lead = "This map draws the wards of %s of Mississippi's %d cities of 25,000 people or more (" % (
        count, len(roster))
    if lead not in note:
        fail("ms/index.html: the City Ward card's empty state does not say %r" % lead)
    named = _city_list(note.split(lead, 1)[1].split(")", 1)[0])
    if named != drawn:
        fail("ms/index.html: the City Ward card's empty state names %s, and CITIES "
             "draws %s" % (named, drawn))
    stray = [c for c in left if c in note]
    if stray:
        fail("ms/index.html: the City Ward card's empty state names %s, which this "
             "file does not draw" % stray)
    with open(WORKSHEET_FILE, encoding="utf-8") as fh:
        layer = [x for x in json.load(fh)["layers"] if x["id"] == "city-ward"]
    if len(layer) != 1:
        fail("ms/metro-worksheet.json: %d city-ward layers" % len(layer))
    applies = layer[0]["source"]["applies"]
    first, sep, rest = applies.partition(". ")
    if not sep or _city_list(first) != drawn:
        fail("ms/metro-worksheet.json: the City Ward row's \"Where it applies\" opens "
             "%r, and CITIES draws %s" % (first, drawn))
    lead = "The other %s cities of 25,000 people or more (" % _NUMBER_WORDS[len(left)]
    if not rest.startswith(lead):
        fail("ms/metro-worksheet.json: the City Ward row's \"Where it applies\" does not "
             "go on %r" % lead)
    if sorted(_city_list(rest[len(lead):].split(")", 1)[0])) != sorted(left):
        fail("ms/metro-worksheet.json: the City Ward row's \"Where it applies\" leaves "
             "out other cities than NOT_DRAWN records (%s)" % sorted(left))
    answers = layer[0]["source"]["answers"]
    if "in the %s Mississippi cities" % count not in answers:
        fail("ms/metro-worksheet.json: the City Ward row's \"What it answers\" does not "
             "say \"in the %s Mississippi cities\"" % count)
    print("check: the City Ward card's empty state and the sources page name the %s "
          "cities drawn, and the sources page the %s left out" % (count, len(left)),
          file=sys.stderr)


def check_source_record(record):
    """The build's record of what it read names every drawn city, at the layer
    CITIES gives and under the name its witness pins where it pins one, with
    both fingerprints, so the monthly source check compares the lines served
    now with the lines the shipped file was drawn from."""
    if not isinstance(record, dict) or not isinstance(record.get("cities"), dict):
        fail("%s is not a record of cities" % os.path.relpath(SOURCE_RECORD, INSTANCE))
    if not re.match(r"^\d{4}-\d\d-\d\d$", str(record.get("built", ""))):
        fail("the source record carries no build date")
    by_geoid = {c["geoid"]: c for c in CITIES}
    if set(record["cities"]) != set(by_geoid):
        fail("the source record names %s and CITIES names %s; rebuild"
             % (sorted(record["cities"]), sorted(by_geoid)))
    for geoid, rec in sorted(record["cities"].items()):
        c = by_geoid[geoid]
        if (rec.get("city"), rec.get("layer")) != (c["city"], c["layer"]):
            fail("%s: the source record was read from %s, not the layer CITIES gives; "
                 "rebuild" % (c["city"], rec.get("layer")))
        pinned = c["witness"].get("layer_name")
        if pinned and rec.get("layer_name") != pinned:
            fail("%s: the source record read a layer named %r, and the witness pins %r; "
                 "rebuild" % (c["city"], rec.get("layer_name"), pinned))
        for key in ("lines_sha256", "place_sha256"):
            if not re.match(r"^[0-9a-f]{64}$", str(rec.get(key, ""))):
                fail("%s: the source record carries no %s" % (c["city"], key))
    print("check: the source record names the %d cities' layers as CITIES does, read %s"
          % (len(by_geoid), record["built"]), file=sys.stderr)


def check(out, record=None):
    """The offline half, on what ships: the cities are CITIES, each city's
    wards are its council roster's ward seats, every feature carries exactly
    the properties the card reads, and no seeded point inside one city's ward
    is inside another city's. A point inside two wards of one city is counted
    and printed, because two of the cities' own maps draw that. Then the two
    hand-written sentences naming the drawn cities are held to CITIES
    (check_stated_cities), and so is the record of what the build read
    (check_source_record), the shipped one unless `record` is given."""
    want, _roster = roster_wards()
    feats = out.get("features") or []
    have = {}
    by_geoid = {c["geoid"]: c for c in CITIES}
    for f in feats:
        p = f.get("properties") or {}
        if tuple(sorted(p)) != tuple(sorted(PROPS)):
            fail("a feature carries %s, not %s" % (sorted(p), sorted(PROPS)))
        c = by_geoid.get(p["geoid"])
        if c is None:
            fail("the file draws %s (%s), which is not in CITIES" % (p["city"], p["geoid"]))
        if (p["city"], p["source"], p["sourceUrl"]) != (c["city"], c["source"] + EDGE, c["page"]):
            fail("%s ward %s does not carry its city's name, source and page as CITIES "
                 "states them" % (p["city"], p["ward"]))
        if p["seat"] != "Ward %s" % p["ward"]:
            fail("%s: seat %r does not match ward %r" % (p["city"], p["seat"], p["ward"]))
        have.setdefault(p["geoid"], []).append(int(p["ward"]))
    if set(have) != set(by_geoid):
        fail("the file draws %s and CITIES names %s" % (sorted(have), sorted(by_geoid)))
    for geoid, nums in have.items():
        if sorted(nums) != want.get(geoid):
            fail("%s: the file draws wards %s and the council roster names %s"
                 % (by_geoid[geoid]["city"], sorted(nums), want.get(geoid)))
    in_two = 0
    for f in feats:
        p = f["properties"]
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        ring = max((poly[0] for poly in polys), key=len)
        xs = [v[0] for v in ring]
        ys = [v[1] for v in ring]
        found = 0
        for i in range(1, 9):
            for j in range(1, 9):
                pt = (min(xs) + (max(xs) - min(xs)) * i / 9.0,
                      min(ys) + (max(ys) - min(ys)) * j / 9.0)
                if not blb._point_in_geometry(pt, g):
                    continue
                found += 1
                hits = [(q["properties"]["city"], q["properties"]["seat"]) for q in feats
                        if blb._point_in_geometry(pt, q["geometry"])]
                others = [h for h in hits if h[0] != p["city"]]
                if others:
                    fail("%.5f,%.5f inside %s %s is also inside %s"
                         % (pt[1], pt[0], p["city"], p["seat"],
                            ", ".join("%s %s" % h for h in others)))
                in_two += len(hits) > 1
        if found < 4:
            fail("could not seed four interior points in %s %s" % (p["city"], p["seat"]))
    print("check: %d wards in %d cities, each city's wards exactly its council roster's "
          "ward seats, no seeded point inside two cities' wards, %d inside two wards of one "
          "city" % (len(feats), len(have), in_two), file=sys.stderr)
    check_stated_cities(_roster)
    if record is None:
        with open(SOURCE_RECORD, encoding="utf-8") as fh:
            record = json.load(fh)
    check_source_record(record)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to CITIES and the council roster, "
                         "and the app's and the sources page's sentences naming the drawn "
                         "cities to CITIES")
    args = ap.parse_args()
    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            check(json.load(fh))
        return
    build()


if __name__ == "__main__":
    main()
