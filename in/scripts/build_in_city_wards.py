#!/usr/bin/env python3
"""
Build in/data/app/in-city-wards.json: the council districts of the Indiana
cities of 25,000 people or more whose council the city roster
(data/app/in-city-officials.json) names by "District N" seats, and whose
current district lines are confirmed.

WHICH CITIES. Indiana has 39 cities and towns of 25,000 people or more on the
2020 census (docs/expected-governments.json). They fall into four groups, each
stated below and held to that list on every build and by --check:

  CITIES             eleven drawn here: Bloomington, Elkhart, Goshen,
                     Greenwood, Jeffersonville, Lawrence, New Albany,
                     Noblesville, Westfield, Plainfield and Valparaiso.
  COUNTY_DRAWN       Indianapolis, whose council is the Indianapolis
                     City-County Council, elected from Marion County's 25
                     districts, which the County Council District layer
                     already draws (in/scripts/build_in_council_districts.py).
  NOT_DRAWN          fourteen whose roster names "District N" seats but whose
                     current lines are not established or cannot be read
                     here, each with its measured reason.
  NO_DISTRICT_SEATS  thirteen whose roster names its seats some other way
                     ("Ward 1", "Seat 1", "Northwest District"), so a
                     district this file draws could not be joined to a seat.

HOW A PLAN IS CONFIRMED. A district plan is drawn on one census, and on that
census its districts hold nearly equal numbers of people; on the census
before, the same lines are unequal, because people moved in between. So each
layer is counted on both censuses' blocks (each populated block's internal
point inside the layer's districts), and a layer that balances on the 2020
census and not on the 2010 census is lines drawn after the 2020 census.
Measured 2026-10-26, as the spread between the largest and smallest district
as a share of an equal one:

                   2010 census      2020 census
                   (the layer as    (cut at the
                   served)          city's limits)
  Bloomington        28.8%           7.0%
  Elkhart            16.5%           9.0%
  Goshen             22.3%           4.8%
  Greenwood          62.3%           4.5%
  Jeffersonville     33.0%           4.2%
  Lawrence           31.1%           8.1%
  New Albany         16.5%           7.0%
  Noblesville        58.6%           9.8%
  Westfield          67.0%           5.6%
  Plainfield         33.0%           6.5%
  Valparaiso         29.1%           5.3%

The same test is what leaves several cities out (NOT_DRAWN): South Bend's
layer is 2.8% apart on the 2010 census and 8.2% on the 2020 census, and
Portage's 4.1% and 10.3%, so both are the plans from the 2010 census;
Lafayette's layer carries its own population figures, and they are its
districts' 2010 counts.

WHO PUBLISHES EACH LAYER. Where ArcGIS Online names the organization that
owns a layer, the card says so: the City of Bloomington, the City of Goshen
(with Elkhart County GIS), the City of Greenwood, the City of Jeffersonville,
Hamilton County GIS (Noblesville and Westfield), Porter County (Valparaiso)
and the City of Indianapolis and Marion County's open data (Lawrence). For
Elkhart, New Albany and Plainfield the owning organization's name is not
readable to this client, so the card names the layer and not a publisher.

THE LINES BETWEEN DISTRICTS ARE EACH LAYER'S OWN, never redrawn. Only the
district field is requested from each layer.

THE CITY'S OUTER EDGE IS THE CENSUS BUREAU'S MAP OF THE CITY (TIGERweb's
current incorporated place), because the district layers run past the cities'
limits and the cities' counts end at them. Cut there, the district card never
names a district of a city the City card says a point is not in.

THE GATES, ASKED OF EVERY CITY ON EVERY BUILD
---------------------------------------------
1. THE DISTRICTS ARE THE ROSTER'S. The layer's districts must be exactly the
   "District N" seats in-city-officials.json names for the city.
2. THE WITNESS STILL SAYS WHAT IT SAID. Each entry pins the layer's own name.
   A renamed layer is a redistricting until a person has read it.
3. THE PEOPLE ARE PINNED. Each district's people on the 2020 census, counted
   by every populated block's internal point inside the district as cut at
   the city's limits, are pinned (`people`), and so are the people inside the
   layer's districts and outside the city's limits (`outside`) and the people
   inside the limits whom no district holds (`gap`). A line that moves moves
   people, so a redrawn plan stops the build here. Six cities have people
   in no district (Elkhart 58, Goshen 18, New Albany 98, Noblesville 384,
   Plainfield 9 and Valparaiso 265, measured 2026-10-26): ground the Census
   Bureau puts inside the city that the city's layer leaves out of every
   district, which a reader there is told. The build prints each such block.
   A populated block a city's own layer puts in two of its districts is
   counted in neither, and recorded in ACCEPTED_SHARED_BLOCKS: one, in
   Elkhart, where the layer puts 15,137 m2 in both District 1 and District 3.
4. THE LAYER'S OWN COUNT, where it carries one, must equal those people
   district by district, except a difference recorded with its reason
   (OWN_POPULATION). None of the eleven layers drawn carries one.
5. TILING against the same Census place: the districts' area over the place's
   must sit between 0.90 and 1.15, and the ground inside the place that no
   district holds has per-city ceilings at about 2.5 times what was measured
   on 2026-10-26.
6. NO TWO CITIES CLAIM ONE PLACE, in the cut districts or the drawn file.
7. SIMPLIFICATION KEEPS EVERY ANSWER. All cities are simplified in one shared
   topology (Douglas-Peucker, interval 3 m), so a line two districts share is
   drawn once. Then every populated 2020 block gets the same districts from
   the drawn file as from the cut districts, the true line strays no more
   than FIDELITY_MAX_M from the drawn one, no district loses a ring, 4,000
   seeded points per city agree at 99.5% or better, and the drawing adds no
   overlap at those points. An exception is a declaration in
   ACCEPTED_DROPPED_PARTS, ACCEPTED_MOVED_BLOCKS or ACCEPTED_OVERLAPS, checked
   on every build.

A ring the layer serves with no area at all covers no ground and changes no
answer, so it is left out; how many each city's layer serves is pinned
(`flat_rings`), so a change in that number stops the build.

Usage:
    python3 in/scripts/build_in_city_wards.py            # fetch, check, write
    python3 in/scripts/build_in_city_wards.py --check    # offline, on what ships

The --check also holds the hand-written statements naming the drawn cities
to CITIES: the City Council District card's empty state and the City card's
list of drawn cities (IN_WARD_CITIES) in in/index.html, and the layer's
"Where it applies" and "What it answers" in the worksheet. Until the
`city-ward` layer is wired into the app, --check fails there and says so; the
build itself does not ask it.

WHAT WAS READ IS RECORDED in data/source/in-city-wards.source.json: for every
city, the layer's address and name, the date the layer gives for its last
edit, and a SHA-256 of the lines the layer and the Census Bureau's map of the
city served, so a later read can tell whether a city moved its lines inside
a layer whose name stayed the same. The --check holds the record to CITIES.
"""

import argparse
import datetime
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(_HERE)
REPO_ROOT = os.path.dirname(INSTANCE)

sys.path.insert(0, _HERE)
import build_legislative_boundaries as blb  # noqa: E402  (same instance tree)
import city_ward_common as cw  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(blb.__file__)) == _HERE, blb.__file__

APP_DATA_DIR = os.path.join(INSTANCE, "data", "app")
OUT = os.path.join(APP_DATA_DIR, "in-city-wards.json")
SOURCE_RECORD = os.path.join(INSTANCE, "data", "source", "in-city-wards.source.json")
ROSTER_FILE = os.path.join(APP_DATA_DIR, "in-city-officials.json")
COUNCIL_FILE = os.path.join(APP_DATA_DIR, "in-council-districts.json")
COUNTIES_FILE = os.path.join(APP_DATA_DIR, "state-counties.json")
EXPECTED_FILE = os.path.join(REPO_ROOT, "docs", "expected-governments.json")
APP_FILE = os.path.join(INSTANCE, "index.html")
WORKSHEET_FILE = os.path.join(INSTANCE, "metro-worksheet.json")

TIGERWEB_PLACE = cw.TIGERWEB + "Places_CouSub_ConCity_SubMCD/MapServer/4"

MAPSHAPER = "mapshaper@0.6.102"
SIMPLIFY = ["dp", "interval=3", "keep-shapes"]
PRECISION = "0.000001"
FIDELITY_MAX_M = 4.0
AGREEMENT_SAMPLES = 4000
MIN_AGREEMENT = 0.995
IDENTITY_RATIO_LO = 0.90
IDENTITY_RATIO_HI = 1.15
OVERLAP_MIN_M2 = 0.01
DECLARED_WITHIN_M = 1.0
DECLARED_AREA_SHARE = 0.10


def _num(v):
    """A district number as a layer serves it: '3' or 3 or 3.0 -> '3'."""
    s = str(v).strip()
    f = float(s)
    if f != int(f) or f < 1:
        raise ValueError("not a district number: %r" % (v,))
    return str(int(f))


def _district_word(v):
    """'District 3' -> '3'."""
    m = re.fullmatch(r"District\s+(\d+)", str(v).strip())
    if not m:
        raise ValueError("not 'District N': %r" % (v,))
    return _num(m.group(1))


def _order(d):
    return (0, int(d), "") if str(d).isdigit() else (1, 0, str(d))


def _item(item_id):
    return "https://www.arcgis.com/home/item.html?id=" + item_id


# Each entry: the city's Census id and name, the layer, the where clause, the
# field carrying the district and how to read it, the page a reader can open,
# the sentence the card prints about where the lines come from, the witness,
# each district's people on the 2020 census as cut at the city's limits, the
# people outside the limits and in no district, the flat rings the layer
# serves (all measured 2026-10-26), and the two tiling ceilings (uncovered sq
# mi, largest uncovered part m2), about 2.5 times what was measured.
CITIES = [
    dict(geoid="1805860", city="Bloomington",
         layer="https://services9.arcgis.com/47GwVXZ9a8thrviM/arcgis/rest/services/"
               "City_Council_Districts/FeatureServer/0",
         where="1=1", field="district_id", read=_num,
         page=_item("80e74cecad81490fb19316b86b3c0a2b"),
         source="the City of Bloomington's map of its council districts",
         witness={"layer_name": "City Council Districts"},
         people={"1": 12962, "2": 13816, "3": 13046, "4": 13355, "5": 13097, "6": 12892},
         outside=0, gap=0, flat_rings=0,
         # measured 0.0144 sq mi in no district, the largest part 4,255 m2
         max_sqmi=0.036, max_part_m2=11000),
    dict(geoid="1820728", city="Elkhart",
         layer="https://services5.arcgis.com/RhRpaq8RpEQjlpir/arcgis/rest/services/"
               "City_Council_Districts/FeatureServer/1",
         where="district<>'At-Large'", field="district", read=_district_word,
         page=_item("23ea0c3c07d2432aa682da8dd100bb76"),
         source="the map of Elkhart's council districts published on ArcGIS Online as "
                "City Council Districts",
         witness={"layer_name": "City Council District"},
         people={"1": 9368, "2": 9198, "3": 8864, "4": 9017, "5": 8557, "6": 9188},
         outside=0, gap=58, flat_rings=0,
         # measured 0.4340 sq mi in no district, the largest part 228,166 m2
         max_sqmi=1.09, max_part_m2=570000),
    dict(geoid="1828386", city="Goshen",
         layer="https://services8.arcgis.com/trHxDV6stlqDdGWV/arcgis/rest/services/"
               "CouncilDistricts2023/FeatureServer/0",
         where="1=1", field="Label", read=_num,
         page=_item("3ece619762434d09a82308cc18f71053"),
         source="the City of Goshen's map of its council districts (Elkhart County GIS and "
                "City of Goshen GIS)",
         witness={"layer_name": "CouncilDistricts2023"},
         people={"1": 6984, "2": 6988, "3": 7058, "4": 6833, "5": 6723},
         outside=0, gap=18, flat_rings=0,
         # measured 0.1326 sq mi in no district, the largest part 156,015 m2
         max_sqmi=0.33, max_part_m2=390000),
    dict(geoid="1829898", city="Greenwood",
         layer="https://services2.arcgis.com/6DdnNWEqLRF18ltQ/arcgis/rest/services/"
               "Greenwood_Common_Council/FeatureServer/0",
         where="CityCommonCouncil>0", field="CityCommonCouncil", read=_num,
         page=_item("8b46eb4c40794d25888c79e1447933c7"),
         source="the City of Greenwood's map of its Common Council districts",
         witness={"layer_name": "Common Council Shaded"},
         people={"1": 10703, "2": 10750, "3": 10364, "4": 10468, "5": 10756, "6": 10844},
         outside=0, gap=0, flat_rings=0,
         # measured 0.0270 sq mi in no district, the largest part 10,682 m2
         max_sqmi=0.068, max_part_m2=27000),
    dict(geoid="1838358", city="Jeffersonville",
         layer="https://services.arcgis.com/NuZplX0yD9b0Mx90/arcgis/rest/services/"
               "city_council_districts/FeatureServer/0",
         where="1=1", field="district", read=_num,
         page=_item("323464ab4c0a4a488a3934c8150458b2"),
         source="the City of Jeffersonville's map of its council districts",
         witness={"layer_name": "Jeffersonville_CityCouncil"},
         people={"1": 8311, "2": 8392, "3": 8104, "4": 8440, "5": 8107, "6": 8093},
         outside=0, gap=0, flat_rings=0,
         # measured 0.0621 sq mi in no district, the largest part 124,300 m2
         max_sqmi=0.16, max_part_m2=311000),
    dict(geoid="1842426", city="Lawrence",
         layer="https://gis.indy.gov/server/rest/services/OpenData/OpenData_Political/"
               "MapServer/5",
         where="TOWN='Lawrence'", field="DISTRICT", read=_num,
         page="https://gis.indy.gov/server/rest/services/OpenData/OpenData_Political/"
              "MapServer/5",
         source="the City of Indianapolis and Marion County's open data map of Lawrence's "
                "council districts",
         witness={"layer_name": "Town Council Districts"},
         people={"1": 7816, "2": 8479, "3": 8055, "4": 8404, "5": 8192, "6": 8424},
         outside=24, gap=0, flat_rings=0,
         # measured 0.0127 sq mi in no district, the largest part 4,790 m2
         max_sqmi=0.032, max_part_m2=12000),
    dict(geoid="1852326", city="New Albany",
         layer="https://services5.arcgis.com/fhY0REQd0M65vDjz/arcgis/rest/services/"
               "New_Albany_2020_Census_Council_Districts/FeatureServer/0",
         where="1=1", field="DISTRICT", read=_num,
         page=_item("f20374a9b3e2425f99964d566a6cbeee"),
         source="the map of New Albany's council districts published on ArcGIS Online as "
                "New Albany 2020 Census Council Districts",
         witness={"layer_name": "New Albany 2020 Census Council Districts"},
         people={"1": 6205, "2": 6182, "3": 6418, "4": 6125, "5": 6393, "6": 6570},
         outside=0, gap=98, flat_rings=0,
         # measured 0.1305 sq mi in no district, the largest part 168,942 m2
         max_sqmi=0.33, max_part_m2=422000),
    dict(geoid="1854180", city="Noblesville",
         layer="https://services5.arcgis.com/beYj0ONLvCt8qxHA/arcgis/rest/services/"
               "Election_Municipal_Council_2023/FeatureServer/5",
         where="MUNI='Noblesville'", field="DIST", read=_num,
         page=_item("c8e7398ed75e4f358e0cd723f07ec270"),
         source="Hamilton County GIS's map of Noblesville's council districts",
         witness={"layer_name": "Election Municipal Council 2026"},
         people={"1": 12310, "2": 12146, "3": 11299, "4": 11301, "5": 11446, "6": 11170},
         outside=31, gap=384, flat_rings=1,
         # measured 0.1990 sq mi in no district, the largest part 53,087 m2
         max_sqmi=0.50, max_part_m2=133000),
    dict(geoid="1882700", city="Westfield",
         layer="https://services5.arcgis.com/beYj0ONLvCt8qxHA/arcgis/rest/services/"
               "Election_Municipal_Council_2023/FeatureServer/5",
         where="MUNI='Westfield'", field="DIST", read=_num,
         page=_item("c8e7398ed75e4f358e0cd723f07ec270"),
         source="Hamilton County GIS's map of Westfield's council districts",
         witness={"layer_name": "Election Municipal Council 2026"},
         people={"1": 9408, "2": 9233, "3": 9122, "4": 9172, "5": 9640},
         outside=100, gap=0, flat_rings=0,
         # measured 0.0574 sq mi in no district, the largest part 27,591 m2
         max_sqmi=0.14, max_part_m2=69000),
    dict(geoid="1860246", city="Plainfield",
         layer="https://services6.arcgis.com/3ejT7DEfNyzKXZBD/arcgis/rest/services/"
               "2021_Council_Districts/FeatureServer/0",
         where="1=1", field="ID", read=_num,
         page=_item("446a33730b074447944d4be477bc615b"),
         source="the map of Plainfield's council districts published on ArcGIS Online as "
                "2021 Council Districts",
         witness={"layer_name": "2021 Council Districts"},
         people={"1": 7049, "2": 7220, "3": 7022, "4": 6923, "5": 6768},
         outside=31, gap=9, flat_rings=0,
         # measured 0.0848 sq mi in no district, the largest part 69,229 m2
         max_sqmi=0.21, max_part_m2=173000),
    dict(geoid="1878326", city="Valparaiso",
         layer="https://services6.arcgis.com/TQ2Al5QIvv4tMBL7/arcgis/rest/services/"
               "ElectionGeography_public_27e9bb8eaa1148d08269f6122529bc74/FeatureServer/0",
         where="districtid IN ('92','93','94','95','96')", field="districtname",
         read=_district_word,
         page=_item("ba336e1392784cad874a387b1568d8e0"),
         source="Porter County's map of Valparaiso's council districts",
         witness={"layer_name": "ElectoralDistricts"},
         people={"1": 6672, "2": 6931, "3": 7033, "4": 6734, "5": 6823},
         outside=0, gap=265, flat_rings=0,
         # measured 0.9631 sq mi in no district, the largest part 826,537 m2
         max_sqmi=2.4, max_part_m2=2070000),
]

# Cities whose council districts another layer draws: the county whose
# council districts the County Council District layer draws for them.
COUNTY_DRAWN = {
    "1836003": ("Indianapolis", "18097"),
}

NOT_DRAWN = {
    "1801468": "Anderson: the one district layer found (Districts_Ord14_24, last edited "
               "October 2024) is 34.3% apart on the 2020 census and 23.1% on the 2010 "
               "census; a federal court ruled the council's 2024 districts unconstitutional "
               "in October 2024 and the council later adopted another map, and that this "
               "layer is that map is not established",
    "1814734": "Columbus: its council districts are published as a PDF only",
    "1825450": "Franklin: its council districts are published as a PDF only",
    "1825000": "Fort Wayne: its map server answers this client with a challenge page",
    "1840392": "Kokomo: no district layer was found",
    "1846908": "Marion: no district layer was found",
    "1849932": "Mishawaka: its district layer is 10.0% apart on the 2010 census and 10.6% "
               "on the 2020 census, and no adoption after the 2020 census was found",
    "1851876": "Muncie: its district layer is 14.1% apart on the 2010 census and 13.4% on "
               "the 2020 census, and no adoption after the 2020 census was found",
    "1861092": "Portage: the district layer found is 4.1% apart on the 2010 census and "
               "10.3% on the 2020 census, so it is the plan from the 2010 census",
    "1864260": "Richmond: its district layer is 11.0% apart on the 2010 census and 12.2% "
               "on the 2020 census, and no adoption after the 2020 census was found",
    "1871000": "South Bend: its district layer is 2.8% apart on the 2010 census and 8.2% on "
               "the 2020 census, so it is the plan from the 2010 census",
    "1875428": "Terre Haute: its district layer is 45.5% apart on the 2010 census and 33.3% "
               "on the 2020 census, so neither census confirms it, and no adoption after "
               "the 2020 census was found",
    "1840788": "Lafayette: the district layer found, last edited in July 2020, carries its "
               "districts' 2010 census counts as its own population figures",
    "1882862": "West Lafayette: the district layer found is named for the 2014 plan and is "
               "36.5% apart on the 2020 census",
}

# Cities whose roster names its council seats some other way than "District
# N", so no district this file could draw joins to a seat.
NO_DISTRICT_SEATS = {
    "1808416": "Brownsburg", "1810342": "Carmel", "1816138": "Crown Point",
    "1819486": "East Chicago", "1822000": "Evansville", "1823278": "Fishers",
    "1827000": "Gary", "1831000": "Hammond", "1834114": "Hobart",
    "1848528": "Merrillville", "1848798": "Michigan City", "1868220": "Schererville",
    "1886372": "Zionsville",
}

# A layer's own population figure for a district that differs from the 2020
# census's people inside it: the difference and why. None is needed.
OWN_POPULATION = {}

# Populated blocks a city's own layer puts in two of its districts, by block:
# the city and the districts. The card names every district there; these
# people are counted in no district's pinned figure, and a block added to or
# gone from this list stops the build.
ACCEPTED_SHARED_BLOCKS = {
    "180390017011028": dict(
        city="Elkhart", people=8, districts=["1", "3"],
        why="Elkhart's layer puts 15,137 m2 around 41.72424,-85.96759 in both District 1 "
            "and District 3, and this block's census point is inside it, so which of the "
            "two its 8 residents vote in is not established; the card names both "
            "(measured 2026-10-26)",
        date="2026-10-26"),
}

# What the drawn file answers differently from the cut districts, each checked
# on every build: the part (or, with hole=True, the hole) at that point with
# that many corners and about that area, and the districts the cut and the
# drawn file answer inside it. Measured 2026-10-26; no census point is inside
# any of them.
_SLIVER = ("a sliver of the layer's district that touches the rest of the district at "
           "one corner, too thin for the drawing to keep")
ACCEPTED_DROPPED_PARTS = [
    dict(city="Elkhart", district="3", lat=41.721088, lng=-85.966319, m2=41.7624, verts=7,
         before=["3"], after=[],
         why="a strip of District 3 about 160 m long and well under a metre wide, beside the "
             "ground Elkhart's layer puts in both District 1 and District 3 "
             "(ACCEPTED_SHARED_BLOCKS), touching the rest of District 3 at one corner",
         date="2026-10-26"),
    dict(city="Elkhart", district="3", lat=41.697899, lng=-85.925762, m2=0.23, verts=3,
         hole=True, before=[], after=["3"],
         why="a three-cornered hole of about a quarter of a square metre in District 3, "
             "which the drawing fills",
         date="2026-10-26"),
    dict(city="Noblesville", district="5", lat=40.015677, lng=-85.971075, m2=0.6099, verts=4,
         before=["5"], after=[], why=_SLIVER, date="2026-10-26"),
    dict(city="Noblesville", district="6", lat=40.030762, lng=-85.933416, m2=0.1528, verts=4,
         before=["6"], after=[], why=_SLIVER, date="2026-10-26"),
    dict(city="Noblesville", district="6", lat=40.016228, lng=-85.919260, m2=0.3686, verts=4,
         before=["6"], after=[], why=_SLIVER, date="2026-10-26"),
    dict(city="Westfield", district="3", lat=40.072282, lng=-86.109283, m2=0.6058, verts=5,
         before=["3"], after=[], why=_SLIVER, date="2026-10-26"),
]
ACCEPTED_MOVED_BLOCKS = {}
ACCEPTED_OVERLAPS = []

EDGE = ", ending at the city's limits as the Census Bureau maps them"

PROPS = ("geoid", "city", "district", "seat", "source", "sourceUrl")


def fail(msg):
    raise SystemExit("build-in-city-wards: FATAL: %s" % msg)


# ---------------------------------------------------------------- fetching --
def layer_params(c):
    """The query sent to a city's district layer, with only the district field."""
    return {"where": c["where"], "outFields": c["field"], "returnGeometry": "true",
            "outSR": "4326", "geometryPrecision": "6", "f": "json"}


def place_params(c):
    return {"where": "GEOID='%s'" % c["geoid"], "outFields": "GEOID,BASENAME",
            "returnGeometry": "true", "outSR": "4326", "geometryPrecision": "6", "f": "json"}


def lines_sha256(fc, c=None):
    """A SHA-256 of the lines in one answer: every ring as served, each feature
    keyed by its district (the Census place by nothing), in one order."""
    rows = []
    for f in fc.get("features") or []:
        a = f.get("attributes") or {}
        key = c["read"](a.get(c["field"])) if c else ""
        rings = sorted([[round(p[0], 6), round(p[1], 6)] for p in ring]
                       for ring in (f.get("geometry") or {}).get("rings") or [])
        rows.append([key, rings])
    rows.sort()
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode("ascii")).hexdigest()


def fetch_layer(c):
    """(layer meta, [GeoJSON-shaped features], the answer as served, flat rings)."""
    meta = cw.open_json(c["layer"] + "?f=json")
    fc = cw.get(c["layer"], layer_params(c))
    if fc.get("exceededTransferLimit"):
        fail("%s: the layer hit its transfer limit" % c["city"])
    cw.DROPPED_FLAT_RINGS.clear()
    feats = cw.esri_features(fc, c["layer"], c["field"])
    flat = sum(cw.DROPPED_FLAT_RINGS.values())
    return meta, feats, fc, flat


def fetch_place(c):
    fc = cw.get(TIGERWEB_PLACE, place_params(c))
    feats = cw.esri_features(fc, TIGERWEB_PLACE, "GEOID")
    if len(feats) != 1:
        fail("%s: TIGERweb returned %d places for GEOID %s" % (c["city"], len(feats), c["geoid"]))
    name = feats[0]["properties"].get("BASENAME")
    if name != c["city"]:
        fail("%s: GEOID %s is %r on TIGERweb" % (c["city"], c["geoid"], name))
    return feats[0], fc


# ------------------------------------------------------------- the checks --
def roster_districts():
    """{geoid: [district keys]} from the roster's "District N" seats, and the
    roster."""
    with open(ROSTER_FILE, encoding="utf-8") as fh:
        roster = json.load(fh)
    out = {}
    for geoid, city in roster.items():
        keys = []
        for seat in city.get("seats") or []:
            m = re.match(r"^District ([0-9]+)$", str(seat.get("seat") or ""))
            if m:
                keys.append(m.group(1))
        out[geoid] = sorted(keys, key=_order)
    return out, roster


def _date(ms):
    if ms is None:
        return None
    return datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc).strftime("%Y-%m-%d")


def districts_of(c, meta, feats, want):
    """{district: shapely geometry} after the district set and witness are
    checked."""
    from shapely.ops import unary_union
    groups = {}
    for f in feats:
        if not f.get("geometry"):
            fail("%s: a feature has no geometry (%r)" % (c["city"], f["properties"].get(c["field"])))
        try:
            d = c["read"](f["properties"][c["field"]])
        except (TypeError, ValueError):
            fail("%s: a district this builder does not read: %r"
                 % (c["city"], f["properties"].get(c["field"])))
        groups.setdefault(d, []).append(
            cw.checked_shape(f["geometry"], "%s district %s" % (c["city"], d)))
    got = sorted(groups, key=_order)
    if got != want:
        fail("%s: the layer holds districts %s and the city roster names seats for "
             "districts %s. A different set is a redistricting or the layer changing "
             "shape, and both need reading before anything ships." % (c["city"], got, want))
    name = meta.get("name")
    if name != c["witness"]["layer_name"]:
        fail("%s: the layer is now named %r, not %r. A renamed district layer is a new "
             "plan until a person has read it." % (c["city"], name, c["witness"]["layer_name"]))
    return {d: unary_union(gs) for d, gs in groups.items()}


def cut(c, districts, place, lat0):
    out = {}
    for d, g in sorted(districts.items(), key=lambda kv: _order(kv[0])):
        out[d] = cw.polygonal(g.intersection(place), "%s district %s cut at the city's limits"
                              % (c["city"], d))
        lost = _m2(g.difference(place), lat0)
        if lost > 1.0:
            print("  district %s: %.0f m2 of the layer lies outside the Census place"
                  % (d, lost), file=sys.stderr)
    return out


def _lat0(geoms):
    ys = [g.bounds[1] for g in geoms] + [g.bounds[3] for g in geoms]
    return (min(ys) + max(ys)) / 2.0


def _m2(g, lat0):
    return g.area * 111320.0 * math.cos(math.radians(lat0)) * 110540.0


def tiling(c, districts, place, lat0):
    from shapely.ops import unary_union
    union = unary_union(list(districts.values()))
    ratio = _m2(union, lat0) / _m2(place, lat0)
    gap = place.difference(union)
    parts = [] if gap.is_empty else (list(gap.geoms) if hasattr(gap, "geoms") else [gap])
    areas = [_m2(p, lat0) for p in parts if p.geom_type == "Polygon"]
    total_sqmi = sum(areas) / 2.58999e6
    largest = max(areas, default=0.0)
    print("  tiling: districts/place area %.4f; %.4f sq mi of the place in no district, in %d "
          "parts, largest %.0f m2" % (ratio, total_sqmi, len(areas), largest), file=sys.stderr)
    problems = []
    if not IDENTITY_RATIO_LO <= ratio <= IDENTITY_RATIO_HI:
        problems.append("the districts' area is %.3f of the Census place's; outside %.2f-%.2f "
                        "this is not the same city" % (ratio, IDENTITY_RATIO_LO, IDENTITY_RATIO_HI))
    if total_sqmi > c["max_sqmi"] or largest > c["max_part_m2"]:
        problems.append("the ground in no district (%.3f sq mi, largest part %.0f m2) has "
                        "grown past its measured ceiling (%.3f sq mi / %.0f m2)"
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
    if c3 not in _BLOCKS:
        _BLOCKS[c3] = cw.fetch_blocks(c3, detail=True)
    return _BLOCKS[c3]


def people(c, raw, districts, place):
    """{district: people} on the 2020 census inside the districts as cut at the
    city's limits, with `outside` and `gap` checked against their pins."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    from shapely.prepared import prep
    raw_union = unary_union(list(raw.values()))
    x0, y0, x1, y1 = raw_union.union(place).bounds
    blocks = []
    for c3 in counties_for(raw_union.union(place)):
        blocks.extend(b for b in blocks_for(c3)
                      if x0 - 0.001 <= b[0] <= x1 + 0.001 and y0 - 0.001 <= b[1] <= y1 + 0.001)
    ready = {d: prep(g) for d, g in districts.items()}
    in_raw, in_place = prep(raw_union), prep(place)
    pop = {d: 0 for d in districts}
    outside = gap = 0
    gap_blocks = []
    shared = {}
    for x, y, n, geoid in blocks:
        pt = Point(x, y)
        hits = sorted((d for d, g in ready.items() if g.contains(pt)), key=_order)
        if len(hits) > 1:
            shared[geoid] = (n, hits)
            continue
        if hits:
            pop[hits[0]] += n
        elif in_place.contains(pt):
            gap += n
            gap_blocks.append((geoid, n, y, x))
        elif in_raw.contains(pt):
            outside += n
    vals = list(pop.values())
    spread = 100.0 * (max(vals) - min(vals)) / (sum(vals) / float(len(vals)))
    print("  people on the 2020 census: %s; %d in all, %.1f%% apart; %d inside the layer's "
          "districts and outside the city's limits, %d inside its limits and in no district"
          % (", ".join("%s: %d" % (d, pop[d]) for d in sorted(pop, key=_order)), sum(vals),
             spread, outside, gap), file=sys.stderr)
    for geoid, n, lat, lng in gap_blocks:
        print("    in no district: block %s, %d people, at %.6f,%.6f" % (geoid, n, lat, lng),
              file=sys.stderr)
    problems = []
    want_shared = {g: (r["people"], r["districts"]) for g, r in ACCEPTED_SHARED_BLOCKS.items()
                   if r["city"] == c["city"]}
    for geoid, (n, hits) in sorted(shared.items()):
        print("    in two districts: block %s, %d people, Districts %s" % (geoid, n, hits),
              file=sys.stderr)
    if shared != want_shared:
        problems.append("the layer puts blocks %s in two districts, and ACCEPTED_SHARED_BLOCKS "
                        "records %s" % (shared, want_shared))
    got = {d: pop[d] for d in sorted(pop, key=_order)}
    if got != c["people"]:
        problems.append("the 2020 census puts %s in its districts, not the pinned %s. A line "
                        "that moved is a redistricting until a person has read it"
                        % (got, c["people"]))
    if outside != c["outside"]:
        problems.append("%d people live inside the layer's districts and outside the city's "
                        "limits, not the pinned %d" % (outside, c["outside"]))
    if gap != c["gap"]:
        problems.append("%d people live inside the city's limits and in no district, not "
                        "the pinned %d" % (gap, c["gap"]))
    return problems, pop, blocks


def _parts(g):
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
    lat = (a[1] + b[1]) / 2.0
    return math.hypot((a[0] - b[0]) * 111320.0 * math.cos(math.radians(lat)),
                      (a[1] - b[1]) * 110540.0)


def _matches(rec, part, m2):
    rp = part.representative_point()
    return (_metres((rp.x, rp.y), (rec["lng"], rec["lat"])) <= DECLARED_WITHIN_M
            and abs(m2 - rec["m2"]) <= DECLARED_AREA_SHARE * rec["m2"])


def _districts_text(items):
    return " and ".join("%s District %s" % (c, d) for c, d in items)


def cross_city(items, what, declared):
    """Ground two cities' districts both cover. In the cut districts there must
    be none; in the drawn file every part must be one `declared` records."""
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
                hits = sorted((it["city"], it["district"]) for it in by_city[a] + by_city[b]
                              if blb._point_in_geometry((rp.x, rp.y), it["geometry"]))
                found.append((part, m2, rp, hits))
    problems, used = [], set()
    for part, m2, rp, hits in found:
        hit = [i for i, rec in enumerate(declared)
               if i not in used and _matches(rec, part, m2)
               and sorted(tuple(w) for w in rec["districts"]) == hits]
        if hit:
            used.add(hit[0])
        else:
            problems.append("%s: %s both cover %.2f m2 at %.6f,%.6f, which nothing records"
                            % (what, _districts_text(hits), m2, rp.y, rp.x))
    for i, rec in enumerate(declared):
        if i not in used:
            problems.append("%s: ACCEPTED_OVERLAPS records %s covering %.2f m2 at %.6f,%.6f, "
                            "and no such overlap is there"
                            % (what, _districts_text(tuple(w) for w in rec["districts"]),
                               rec["m2"], rec["lat"], rec["lng"]))
    print("cross-city: in the %s, %d parts of %.2f m2 or more are covered by two cities' "
          "districts" % (what, len(found), OVERLAP_MIN_M2), file=sys.stderr)
    return problems


def own_overlaps(items, what):
    """Printed, never failed: ground a city's layer puts in two of its own
    districts."""
    by_city = {}
    for it in items:
        by_city.setdefault(it["city"], []).append(it)
    out = []
    for city, its in sorted(by_city.items()):
        total, pairs = 0.0, 0
        for i in range(len(its)):
            for j in range(i + 1, len(its)):
                a, b = its[i], its[j]
                if not a["shape"].intersects(b["shape"]):
                    continue
                m2 = sum(_part_m2(p) for p in _parts(a["shape"].intersection(b["shape"])))
                if m2 >= OVERLAP_MIN_M2:
                    total += m2
                    pairs += 1
        if pairs:
            out.append("%s %.2f m2 across %d pairs of districts" % (city, total, pairs))
    print("in two districts of one city, in the %s: %s" % (what, "; ".join(out) or "nowhere"),
          file=sys.stderr)


# ---------------------------------------------------------- simplifying -----
def simplify_shared(exact):
    work = tempfile.mkdtemp(prefix="in-wards-")
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
    """Every answer the cut districts give, the drawn file gives too, but the
    ones ACCEPTED_DROPPED_PARTS and ACCEPTED_MOVED_BLOCKS record."""
    from shapely.geometry import shape
    problems = []
    key = lambda f: (f["properties"]["geoid"], f["properties"]["district"])  # noqa: E731
    src = {key(f): f for f in exact["features"]}
    new = {key(f): f for f in simple["features"]}
    if set(src) != set(new):
        fail("mapshaper changed the set of districts")
    geoid_of = {f["properties"]["city"]: f["properties"]["geoid"] for f in exact["features"]}
    city_of = {g: c for c, g in geoid_of.items()}
    models = {}
    for geoid in sorted(city_of):
        feats = [src[k] for k in sorted(src) if k[0] == geoid]
        models[geoid] = (blb._model(feats, "district"),
                         blb._model([new[key(f)] for f in feats], "district"))

    def answers(geoid, pt):
        s_model, n_model = models[geoid]
        return sorted(blb._districts_at(s_model, pt)), sorted(blb._districts_at(n_model, pt))

    skip, dropped = set(), {}
    for rec in ACCEPTED_DROPPED_PARTS:
        geoid = geoid_of.get(rec["city"])
        f = src.get((geoid, rec["district"]))
        if f is None:
            problems.append("ACCEPTED_DROPPED_PARTS records %s District %s, which is not drawn"
                            % (rec["city"], rec["district"]))
            continue
        if rec.get("hole"):
            from shapely.geometry import Polygon
            rings = [Polygon(r) for p in _parts(shape(f["geometry"])) for r in p.interiors]
        else:
            rings = _parts(shape(f["geometry"]))
        found = [p for p in rings
                 if len(p.exterior.coords) - 1 == rec["verts"] and _matches(rec, p, _part_m2(p))]
        if len(found) != 1:
            problems.append("ACCEPTED_DROPPED_PARTS records a %.2f m2 part of %s District %s "
                            "at %.6f,%.6f, and the cut district has %d such parts"
                            % (rec["m2"], rec["city"], rec["district"], rec["lat"], rec["lng"],
                               len(found)))
            continue
        part = found[0]
        rp = part.representative_point()
        before, after = answers(geoid, (rp.x, rp.y))
        if (before, after) != (sorted(rec["before"]), sorted(rec["after"])):
            problems.append("ACCEPTED_DROPPED_PARTS: on the %.2f m2 part of %s District %s the "
                            "cut districts answer %s and the drawn file %s, not the recorded "
                            "%s and %s" % (_part_m2(part), rec["city"], rec["district"], before,
                                           after, rec["before"], rec["after"]))
            continue
        skip.add(tuple(tuple(v) for v in part.exterior.coords))
        dropped[(geoid, rec["district"])] = dropped.get((geoid, rec["district"]), 0) + 1
    for k in sorted(src):
        a, b = _rings(src[k]["geometry"]), _rings(new[k]["geometry"])
        if a - dropped.get(k, 0) != b:
            problems.append("%s District %s has %d rings on the cut districts and %d drawn, "
                            "and ACCEPTED_DROPPED_PARTS records %d dropped"
                            % (city_of[k[0]], k[1], a, b, dropped.get(k, 0)))
    worst = 0.0
    for k in sorted(src):
        idx = cw.seg_index(new[k])
        for ring in cw.rings_of(src[k]["geometry"]):
            if tuple(tuple(v) for v in ring) in skip:
                continue
            for v in ring[:-1]:
                gx, gy = int(math.floor(v[0] / 0.02)), int(math.floor(v[1] / 0.02))
                cand = []
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        cand += idx.get((gx + dx, gy + dy), ())
                if cand:
                    worst = max(worst, min(cw.point_to_segment_m(v, a, b) for a, b in cand))
    print("fidelity: the cut districts' lines stray at most %.2f m from the drawn ones "
          "(ceiling %.1f)" % (worst, FIDELITY_MAX_M), file=sys.stderr)
    if worst > FIDELITY_MAX_M:
        problems.append("the cut districts' lines stray %.2f m from the drawn ones, over %.1f m"
                        % (worst, FIDELITY_MAX_M))
    moved = {}
    for geoid in sorted(models):
        for x, y, n, gid in blocks_by_city[geoid]:
            before, after = answers(geoid, (x, y))
            if before != after:
                moved[(city_of[geoid], gid)] = (n, before, after)
    print("people: %d of the 2020 census's residents get other districts from the drawn file "
          "than from the cut districts" % sum(v[0] for v in moved.values()), file=sys.stderr)
    want = {(rec["city"], gid): rec for gid, rec in ACCEPTED_MOVED_BLOCKS.items()}
    for (city, gid), (n, before, after) in sorted(moved.items()):
        rec = want.get((city, gid))
        said = "%s %s on the cut districts and %s drawn" % (city, before or "no district",
                                                          after or "no district")
        if rec is None:
            problems.append("block %s, %d people: %s, which nothing records" % (gid, n, said))
        elif (rec["people"], sorted(rec["before"]), sorted(rec["after"])) != (n, before, after):
            problems.append("block %s: ACCEPTED_MOVED_BLOCKS records %d people, %s to %s, and "
                            "the build finds %d people, %s" % (gid, rec["people"], rec["before"],
                                                              rec["after"], n, said))
    for (city, gid), rec in sorted(want.items()):
        if (city, gid) not in moved:
            problems.append("ACCEPTED_MOVED_BLOCKS records block %s in %s, and the drawn file "
                            "gives it the same districts as the cut districts" % (gid, city))
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
            problems.append("%s: the drawing adds overlap (%d points against the cut "
                            "districts' %d)" % (city, n_over, s_over))
        print("agreement: %s %d of %d seeded points, overlap %d on the cut districts and %d "
              "drawn" % (city, agree, AGREEMENT_SAMPLES, s_over, n_over), file=sys.stderr)
    return problems


# ------------------------------------------------------------------ build --
def build():
    want, roster = roster_districts()
    check_groups(roster)
    problems = []
    exact = {"type": "FeatureCollection", "features": []}
    blocks_by_city, cut_items, read = {}, [], {}
    for c in CITIES:
        print("%s (%s)" % (c["city"], c["layer"]), file=sys.stderr)
        meta, feats, served, flat = fetch_layer(c)
        edited = (meta.get("editingInfo") or {}).get("dataLastEditDate") or \
            (meta.get("editingInfo") or {}).get("lastEditDate")
        print("  layer %r, last edited %s; %d rings with no area left out"
              % (meta.get("name"), _date(edited) or "not stated", flat), file=sys.stderr)
        if flat != c["flat_rings"]:
            problems.append("%s: the layer serves %d rings with no area, not the pinned %s"
                            % (c["city"], flat, c["flat_rings"]))
        raw = districts_of(c, meta, feats, want[c["geoid"]])
        lat0 = _lat0(list(raw.values()))
        place_feat, place_served = fetch_place(c)
        place = cw.checked_shape(place_feat["geometry"], "%s place" % c["city"])
        read[c["geoid"]] = {"city": c["city"], "layer": c["layer"],
                            "layer_name": meta.get("name"),
                            "last_edited": _date(edited),
                            "lines_sha256": lines_sha256(served, c),
                            "place_sha256": lines_sha256(place_served)}
        districts = cut(c, raw, place, lat0)
        problems += ["%s: %s" % (c["city"], p) for p in tiling(c, districts, place, lat0)]
        p_problems, pop, blocks = people(c, raw, districts, place)
        problems += ["%s: %s" % (c["city"], p) for p in p_problems]
        if OWN_POPULATION.get(c["geoid"]):
            problems.append("%s: OWN_POPULATION records a difference, and this layer carries "
                            "no population figures" % c["city"])
        blocks_by_city[c["geoid"]] = blocks
        for d in sorted(districts, key=_order):
            cut_items.append(dict(city=c["city"], district=d, shape=districts[d],
                                  geometry=cw.geojson(districts[d])))
            exact["features"].append({
                "type": "Feature",
                "properties": {"geoid": c["geoid"], "city": c["city"], "district": d,
                               "seat": "District %s" % d, "source": c["source"] + EDGE,
                               "sourceUrl": c["page"]},
                "geometry": cw.geojson(districts[d]),
            })
    own_overlaps(cut_items, "cut districts")
    problems += cross_city(cut_items, "cut districts", [])
    simple = simplify_shared(exact)
    problems += drawn_checks(exact, simple, blocks_by_city)
    drawn_items = [dict(city=f["properties"]["city"], district=f["properties"]["district"],
                        shape=cw.checked_shape(f["geometry"], "drawn %s District %s"
                                               % (f["properties"]["city"],
                                                  f["properties"]["district"])),
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
    out["features"].sort(key=lambda f: (f["properties"]["city"],
                                        _order(f["properties"]["district"])))
    record = {
        "_about": ("GENERATED by in/scripts/build_in_city_wards.py. What each drawn city's "
                   "council districts were read from when the shipped file was built: the "
                   "district layer's address and name, the date the layer gives for its last "
                   "edit, and a SHA-256 of the lines the layer and the Census Bureau's map of "
                   "the city served. --check holds this record to CITIES."),
        "built": datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
        "cities": read,
    }
    check(out, record, stated=False)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
        fh.write("\n")
    os.makedirs(os.path.dirname(SOURCE_RECORD), exist_ok=True)
    with open(SOURCE_RECORD, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("in-city-wards -> %s: %d districts in %d cities, %d bytes; the lines read are "
          "recorded in %s" % (os.path.relpath(OUT, INSTANCE), len(out["features"]), len(CITIES),
                              os.path.getsize(OUT), os.path.relpath(SOURCE_RECORD, INSTANCE)),
          file=sys.stderr)


_NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven",
                 "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
                 "fifteen")


def _city_list(text):
    head, sep, last = text.rpartition(" and ")
    if not sep:
        return [text.strip()]
    return [s.strip() for s in head.split(",")] + [last.strip()]


def expected_cities():
    with open(EXPECTED_FILE, encoding="utf-8") as fh:
        units = json.load(fh)["units"]["in"]
    return {u["geoid"]: u["name"] for u in units if u.get("kind") == "place"}


def check_groups(roster):
    """CITIES, COUNTY_DRAWN, NOT_DRAWN and NO_DISTRICT_SEATS are exactly
    Indiana's places of 25,000 people or more, no place in two; every city
    drawn or not drawn has "District N" seats in the roster; every city in
    NO_DISTRICT_SEATS has none; a county-drawn city's county is drawn by the
    County Council District layer with one district per roster seat."""
    expected = expected_cities()
    drawn = [c["geoid"] for c in CITIES]
    groups = [set(drawn), set(COUNTY_DRAWN), set(NOT_DRAWN), set(NO_DISTRICT_SEATS)]
    if len(drawn) != len(set(drawn)):
        fail("a city is in CITIES twice")
    if sum(len(g) for g in groups) != len(set().union(*groups)):
        fail("a city is in two of CITIES, COUNTY_DRAWN, NOT_DRAWN and NO_DISTRICT_SEATS")
    if set().union(*groups) != set(expected):
        fail("the four groups together are %s, and Indiana's places of 25,000 people or more "
             "are %s" % (sorted(set().union(*groups)), sorted(expected)))
    for c in CITIES:
        if not expected[c["geoid"]].startswith(c["city"] + " "):
            fail("%s: the Census id %s is %r" % (c["city"], c["geoid"], expected[c["geoid"]]))
    want, _ = roster_districts()
    for geoid in drawn + sorted(NOT_DRAWN):
        if not want.get(geoid):
            fail("%s is not in the city roster with \"District N\" seats" % expected[geoid])
    for geoid, name in sorted(NOT_DRAWN.items()):
        if not expected[geoid].startswith(name.split(":", 1)[0] + " "):
            fail("NOT_DRAWN names %r for %s" % (name.split(":", 1)[0], expected[geoid]))
    for geoid, name in sorted(NO_DISTRICT_SEATS.items()):
        if not expected[geoid].startswith(name + " "):
            fail("NO_DISTRICT_SEATS names %r for %s" % (name, expected[geoid]))
        if want.get(geoid):
            fail("%s now has \"District N\" seats in the city roster; it belongs in CITIES "
                 "or NOT_DRAWN" % name)
    with open(COUNCIL_FILE, encoding="utf-8") as fh:
        council = json.load(fh)
    for geoid, (name, fips) in sorted(COUNTY_DRAWN.items()):
        if not expected[geoid].startswith(name + " "):
            fail("COUNTY_DRAWN names %r for %s" % (name, expected[geoid]))
        got = sorted({str(f["properties"]["district"]) for f in council["features"]
                      if f["properties"].get("fips") == fips}, key=_order)
        if not got or got != want.get(geoid):
            fail("%s: the County Council District layer draws districts %s for county %s and "
                 "the city roster names %s" % (name, got, fips, want.get(geoid)))


def check_stated_cities(roster):
    """The hand-written statements naming the drawn cities: the City Council
    District card's empty state and the City card's list of drawn cities
    (IN_WARD_CITIES) in in/index.html, and the layer's "Where it applies" and
    "What it answers" in the worksheet. The empty state must say "This map
    draws the council districts of <count> of Indiana's <total> cities of
    25,000 people or more (<the cities CITIES draws>)"; the list must hold
    exactly CITIES' Census ids; "Where it applies" must open with the cities
    CITIES draws; "What it answers" must say "in the <count> Indiana cities"."""
    check_groups(roster)
    drawn = [c["city"] for c in CITIES]
    total = len(expected_cities())
    count = _NUMBER_WORDS[len(drawn)]
    with open(APP_FILE, encoding="utf-8") as fh:
        app = fh.read()
    at = app.find('id: "city-ward"')
    if at < 0:
        fail("in/index.html: no city-ward layer is registered yet, so nothing tells a reader "
             "which cities are drawn")
    m = re.compile(r'emptyNote:\s*((?:"(?:[^"\\]|\\.)*"\s*\+\s*)*"(?:[^"\\]|\\.)*")\s*,'
                   ).search(app, at)
    if m is None:
        fail("in/index.html: no emptyNote found after the city-ward layer's id")
    note = "".join(json.loads(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"', m.group(1)))
    lead = ("This map draws the council districts of %s of Indiana's %d cities of 25,000 "
            "people or more (" % (count, total))
    if lead not in note:
        fail("in/index.html: the City Council District card's empty state does not say %r" % lead)
    named = _city_list(note.split(lead, 1)[1].split(")", 1)[0])
    if named != drawn:
        fail("in/index.html: the City Council District card's empty state names %s, and "
             "CITIES draws %s" % (named, drawn))
    listed = re.search(r'var IN_WARD_CITIES = \[([^\]]*)\];', app)
    if listed is None:
        fail("in/index.html: no IN_WARD_CITIES list, which the City card reads to say "
             "whether a city's districts are drawn")
    ids = re.findall(r'"(\d{7})"', listed.group(1))
    want = sorted(c["geoid"] for c in CITIES)
    if sorted(ids) != want or len(ids) != len(set(ids)):
        fail("in/index.html: IN_WARD_CITIES lists %s, and CITIES draws %s" % (ids, want))
    with open(WORKSHEET_FILE, encoding="utf-8") as fh:
        layer = [x for x in json.load(fh)["layers"] if x["id"] == "city-ward"]
    if len(layer) != 1:
        fail("in/metro-worksheet.json: %d city-ward layers" % len(layer))
    applies = layer[0]["source"]["applies"]
    first, sep, _rest = applies.partition(". ")
    if not sep or _city_list(first) != drawn:
        fail("in/metro-worksheet.json: the City Council District row's \"Where it applies\" "
             "opens %r, and CITIES draws %s" % (first, drawn))
    if "in the %s Indiana cities" % count not in layer[0]["source"]["answers"]:
        fail("in/metro-worksheet.json: the City Council District row's \"What it answers\" "
             "does not say \"in the %s Indiana cities\"" % count)
    print("check: the City Council District card's empty state, the City card's list and "
          "the sources page name the %s cities drawn" % count, file=sys.stderr)


def check_source_record(record):
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
        if rec.get("layer_name") != c["witness"]["layer_name"]:
            fail("%s: the source record read a layer named %r, and the witness pins %r; "
                 "rebuild" % (c["city"], rec.get("layer_name"), c["witness"]["layer_name"]))
        for k in ("lines_sha256", "place_sha256"):
            if not re.match(r"^[0-9a-f]{64}$", str(rec.get(k, ""))):
                fail("%s: the source record carries no %s" % (c["city"], k))
    print("check: the source record names the %d cities' layers as CITIES does, read %s"
          % (len(by_geoid), record["built"]), file=sys.stderr)


def check(out, record=None, stated=True):
    """The offline half, on what ships: the cities are CITIES, each city's
    districts are its roster's "District N" seats, every feature carries
    exactly the properties the card reads, and no seeded point inside one
    city's district is inside another city's. With `stated`, the statements
    naming the drawn cities are held to CITIES too; and the record of what the
    build read is held to CITIES."""
    want, roster = roster_districts()
    check_groups(roster)
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
            fail("%s district %s does not carry its city's name, source and page as CITIES "
                 "states them" % (p["city"], p["district"]))
        if p["seat"] != "District %s" % p["district"]:
            fail("%s: seat %r does not match district %r" % (p["city"], p["seat"], p["district"]))
        have.setdefault(p["geoid"], []).append(str(p["district"]))
    if set(have) != set(by_geoid):
        fail("the file draws %s and CITIES names %s" % (sorted(have), sorted(by_geoid)))
    for geoid, keys in have.items():
        if sorted(keys, key=_order) != want.get(geoid):
            fail("%s: the file draws districts %s and the city roster names %s"
                 % (by_geoid[geoid]["city"], sorted(keys, key=_order), want.get(geoid)))
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
    print("check: %d districts in %d cities, each city's districts exactly its roster's "
          "district seats, no seeded point inside two cities' districts, %d inside two "
          "districts of one city" % (len(feats), len(have), in_two), file=sys.stderr)
    if record is None:
        with open(SOURCE_RECORD, encoding="utf-8") as fh:
            record = json.load(fh)
    check_source_record(record)
    if stated:
        check_stated_cities(roster)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file and its source record to CITIES and "
                         "the city roster, and the app's and worksheet's statements naming "
                         "the drawn cities to CITIES")
    args = ap.parse_args()
    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            check(json.load(fh))
        return
    build()


if __name__ == "__main__":
    main()
