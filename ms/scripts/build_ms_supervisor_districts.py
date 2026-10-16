#!/usr/bin/env python3
"""
Build ms/data/app/ms-supervisor-districts.json: the county supervisor
districts of the Mississippi counties whose CURRENT lines this app has
confirmed, so the app can say which of a county's five supervisors represents
a point. The County card names all five in every county; this layer draws the
district only where its lines are known to be the ones in force.

WHERE THE LINES COME FROM. Every Mississippi county elects five supervisors,
each from a district (five counties call them "beats"). The Census Bureau
carries all 410 districts as county subdivisions: TIGERweb's current layer
(tigerWMS_Current, layer 22, "January 1, 2026 vintage") has BASENAME 1 to 5 in
every county, every one nonfunctioning (FUNCSTAT N), which is how the Census
files a supervisor district. No state office publishes a statewide map of the
current lines, measured 2026-10-15.

WHY MOST COUNTIES ARE NOT DRAWN. Counties redrew their districts after the
2020 census, and in most of them the Census never received the new lines: the
2026 layer still carries the lines in its own 2020 edition
(tigerWMS_Census2020, layer 20), and in most of those counties that edition
puts every resident in the same district as its 2010 edition
(tigerWMS_Census2010, layer 28, the lines it held on January 1, 2010). Those
lines would name the wrong supervisor for many readers. The planning
measurement found the old lines put 34% of Madison County's residents in a
different district from the one they now vote in, 16% of Lee's and 9.5% of
Harrison's.

TWO SOURCES OF CONFIRMED LINES, each a STATED list:

  CENSUS_COUNTIES — the Census's own lines, where the Census has received the
  new ones. Two measurements, both re-taken on every build from the Census's
  own data:

  1. Its 2026 lines differ from the 2020 edition's, so the county sent the
     Census new lines after the 2020 census. The witness is people, not area:
     the build counts the residents whose district NUMBER the change moved
     (each 2020 census block assigned by its internal point).
  2. On the 2020 census's own block counts the five districts hold nearly
     equal numbers of people: the largest and smallest differ by no more than
     MAX_DEVIATION_PCT percent of an equal share. Lines drawn to balance on
     the 2020 census pass this; the older lines the Census still carries
     mostly do not.

  COUNTY_SOURCES — a map the county publishes, or its planning and
  development district publishes for it, where the Census still carries the
  old lines. The same two measurements are taken on the county's lines, plus
  the evidence that names them as the plan adopted after the 2020 census (the
  entry's own comment lists what each county's is), plus a third: the Census's
  current lines in that county must STILL be its 2020 edition's, so the day the
  Census receives the county's new lines the build stops and a person decides
  whether the county moves to the first list.

Measured 2026-10-15 across all 82 counties (`--survey` re-takes it): 12
counties pass both Census measurements, at 3.2% to 9.0%, and their
2020-edition lines measure 15.6% to 85.6% on the same blocks. Of the 70
counties whose 2026 lines ARE the 2020 edition's, 64 measure more than 10%,
and six measure under it — Lafayette 2.5%, Marshall 6.1%, Montgomery 6.2%,
Jefferson Davis 6.8%, Walthall 7.7% and Marion 7.8%. Those six are NOT drawn:
their lines balance on 2020 population, so a county may have kept them, but it
may equally have redrawn them and never told the Census, and nothing here can
tell which. A county's own published map, or its answer to a letter, is what
settles one of them. Marion's 2026 layer differs from its 2020 edition by a
sliver on the line between districts 4 and 5 (about 19 m2, 0.0000027% of the
county, measured 2026-10-15). It moves nobody, so `--survey` reports 0 people
moved and the test does not count it as a change.

THE OLD LINES ARE OLDER THAN THE 2010 CENSUS IN MOST OF THOSE COUNTIES, and
this docstring called them "the lines drawn after the 2010 census" until
2026-10-16, when `--survey` first measured them against the 2010 edition,
whose POP100 is the 2010 census's own count of each district: in 52 of the 64
counties whose 2020 edition measures more than 10%, it puts every 2020
resident in the same district as the 2010 edition, so the Census's lines there
have moved nobody since January 1, 2010, and in 49 of those 52 the districts
were already more than 10% apart on the 2010 census's own counts. The 49 held
1,504,204 of the state's 2,961,279 residents in 2020. Seven of them (Coahoma,
Greene, Harrison, Hinds, Lauderdale, Sunflower and Yazoo) hold a 2020 block of
more than 1,000 people, which may be a prison or a campus that a plan can
leave out of its count, so their figures may overstate how far apart a plan's
own count would put the districts. Estimated from that block's 2020 count
against an equal share, leaving it out could account for the whole figure only
in Coahoma and Sunflower; the other 47 held 1,456,843 residents.

A survey of every county's own website and its planning and development
district's on 2026-10-15 found 14 counties publishing lines of their own that
differ from the Census's; the eleven in COUNTY_SOURCES are the ones whose
publication names or proves its own currency, and the other three wait for
more evidence (ms/WATCH.md). Three of the eleven (Lee, Pearl River and Perry,
added 2026-10-16) are proved by the county's own map of its voting precincts,
which follows the county's lines and not the Census's; precinct_witness() says
what is measured.

NOTHING TRACED SHIPS, from a county's own map: its lines only decide which
district each 2020 census block belongs to (the one covering most of the
block's area), and each district is drawn as the union of its blocks, so every
vertex this file ships is the Census Bureau's — the method
ia/scripts/build_county_supplied_supervisor_districts.py uses for the same
question. A plan adopted after the 2020 census assigns whole 2020 blocks, so
this recovers the plan's own lines from a map drawn on another base, and it
puts the county line exactly where the neighbouring counties' blocks put it.
Measured 2026-10-15, seven of the first eight maps follow the blocks closely:
every populated block lies at least 93% inside one district, and in the six
that publish a population per district the blocks reproduce those figures to
the person (Rankin's after the two blocks its plan sets aside). Lamar's map is
drawn on another base (its county line runs up to 60 m from the Census's), so
its worst populated block is 72% inside one district, and 17 blocks with
nobody living in them in 2020 (0.586 km2) are split about evenly between two;
each goes to the larger share, and MAX_EVEN_KM2 bounds that ground. The three
added 2026-10-16 follow the blocks less closely: the worst populated block is
79% inside one district in Lee, 74% in Pearl River and 64% in Perry, and
blocks with nobody in them are split about evenly on 0.010 km2 in Lee (one
block) and 0.160 km2 in Perry (seven). In those three the precinct map checks
that the blocks went to the right districts: it puts 10 of Lee's 83,343
residents, none of Pearl River's 56,145 and 8 of Perry's 11,511 in a different
district from the drawn lines.

GATES BEFORE ANYTHING IS WRITTEN:
  - every drawn county has exactly five districts numbered 1 to 5;
  - the Secretary of State's directory (ms-county-officials.json) names a
    supervisor, or a vacancy, for each of those five districts, in the
    county's own word ("District" or "Beat"), and where a county's map names
    its supervisors, the same surnames as the directory's for the same
    numbers;
  - the confirmations above, with every populated 2020 block in exactly one
    district, and the county's block total equal to its tract total;
  - for a county's own map, its numbering is the 2020 edition's (the
    one-to-one pairing of the two that keeps the most residents in a district
    of the same number is 1-1 to 5-5), and every block's assignment is clear:
    a populated block at least MIN_POPULATED_SHARE inside one district;
  - for a county proved by its precinct map, the precinct witness: the map
    puts no more than PRECINCT_MAX_OFF_SHARE of the county's residents in a
    different district from the drawn lines and at least MIN_PEOPLE_MOVED in
    a different district from the Census's, and all but
    PRECINCT_MAX_UNPLACED_SHARE of them in exactly one precinct;
  - the fleet's 2,000-point agreement test between the simplified districts
    and the full-precision lines, sampled inside the drawn counties;
  - the fidelity ceiling the legislative builder pins (no source vertex more
    than build_legislative_boundaries.FIDELITY_CEILING_M from its district as
    drawn), and the people simplification moves across a line, printed;
  - the county witness: at points sampled over the drawn counties, a point
    the County layer (state-counties.json) puts in a drawn county must lie in
    one of THAT county's districts, and a point it puts elsewhere in none,
    except within EDGE_M of a county line, where two simplified files may
    differ by their two strays.

TWO FILES ARE WRITTEN: the districts, and ms-supervisor-counties.json, the
drawn counties by GEOID, which is what the app's coverage test reads. That test
runs on a reader's first selection whether or not the layer is on, and it used
to read the districts file itself: 150 KB gzipped for twenty counties, measured
2026-10-15. It now finds the point's county in state-counties.json, which the
County card loads on every selection anyway, and looks it up in the list, which
is under 1 KB. Within a few metres of a county line the two files can put a
point in different counties, because each was simplified on its own (a drawn
county's edge sits at most 5.0 m from the County layer's line, measured
2026-10-16); the county witness below bounds that strip, and there the layer
follows the County card. `--check` fails if the list and the districts file name different
counties.

SIMPLIFICATION. Douglas-Peucker in metres, the legislative builder's method,
for the reason its docstring gives, and ALL DRAWN COUNTIES IN ONE MAPSHAPER
RUN, so a line two districts share — inside a county or where two drawn
counties meet — is one arc simplified once. The interval is 5 m under the
legislative builder's 8 m ceiling, the county file's setting, which Adam chose
for these lines before the instance opened ("Finer first", 2026-10-16).
Measured that day against the 20 m interval it replaced, on the same sources:

    setting           worst stray   people moved   county edge apart   gzipped
    dp interval=20       20.6 m       3 (Perry)          20.4 m          176 KB
    dp interval=5         5.6 m       0                   5.0 m          384 KB

"People moved" is the residents of 2020 blocks whose district simplification
changes; "county edge apart" is the farthest a drawn county's outer edge sits
from the County layer's line, either way round.

WHAT `--check` CAN AND CANNOT SEE. It is offline and runs in CI: the shipped
file's counties, numbering, county names and sources, the roster join, the
record in data/source/ms-supervisor-districts.source.json (each county's
measurements, held again to the gates above, and for a county's own map the
evidence it was read with), the
Census edition the app's card names, and the county witness against the
shipped state-counties.json. It cannot re-measure population or re-read a
county's map, because neither is shipped; the figures it prints are the ones
the build measured and recorded, and a hand edit to them is not something it
can catch.

robots.txt: tigerweb.geo.census.gov serves a 189-byte HTML page at
/robots.txt rather than a policy (HTTP 200, read 2026-10-15), which the shared
reader takes as no robots.txt, so every path is allowed. Every host is read
through scraper_common.require_robots_once before its first fetch, with the
same client the fetches send. gis.cmpdd.org sends its certificate without the
intermediate that signed it, so the build completes the chain from
scripts/aia_bundle.py's pinned copy rather than turning verification off.

Prerequisites: Node.js (mapshaper via `npx mapshaper@<pinned>`), and for the
build (not --check) shapely and pyproj as scripts/requirements.txt pins them.

Usage:
    python3 ms/scripts/build_ms_supervisor_districts.py           # fetch, build, write
    python3 ms/scripts/build_ms_supervisor_districts.py --check   # offline gate (CI)
    python3 ms/scripts/build_ms_supervisor_districts.py --survey  # all 82 counties, writes nothing
"""

import argparse
import atexit
import collections
import datetime
import hashlib
import itertools
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
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

sys.path.insert(0, _HERE)
import build_legislative_boundaries as blb  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(blb.__file__)) == _HERE, blb.__file__

APP_DATA_DIR = os.path.join(INSTANCE, "data", "app")
SOURCE_DIR = os.path.join(INSTANCE, "data", "source")
OUT = os.path.join(APP_DATA_DIR, "ms-supervisor-districts.json")
COUNTY_LIST = os.path.join(APP_DATA_DIR, "ms-supervisor-counties.json")
RECORD = os.path.join(SOURCE_DIR, "ms-supervisor-districts.source.json")
COUNTIES_FILE = os.path.join(APP_DATA_DIR, "state-counties.json")
ROSTER_FILE = os.path.join(APP_DATA_DIR, "ms-county-officials.json")

USER_AGENT = "districtry/1.0 (+https://districtry.com/ms/)"
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
CURRENT = TIGERWEB + "tigerWMS_Current/MapServer/22"
CURRENT_NAME = "County Subdivisions"
CURRENT_VINTAGE = "January 1, 2026"
EDITION_2020 = TIGERWEB + "tigerWMS_Census2020/MapServer/20"
EDITION_2010 = TIGERWEB + "tigerWMS_Census2010/MapServer/28"  # January 1, 2010 vintage
BLOCKS = TIGERWEB + "Tracts_Blocks/MapServer/12"   # Census 2020 blocks, POP100
TRACTS = TIGERWEB + "Tracts_Blocks/MapServer/10"   # Census 2020 tracts, POP100
STATE = "28"

# The counties whose Census lines are confirmed current, by three-digit code.
# STATED, never derived: `--survey` prints any county that newly passes both
# tests (when the Census rolls a vintage) and a person adds it here after
# looking, because a county passing a population test is a reason to look and
# not yet a reason to draw.
CENSUS_COUNTIES = {
    "019": "Choctaw",
    "025": "Clay",
    "033": "DeSoto",
    "043": "Grenada",
    "077": "Lawrence",
    "087": "Lowndes",
    "099": "Neshoba",
    "103": "Noxubee",
    "105": "Oktibbeha",
    "137": "Tate",
    "155": "Webster",
    "159": "Winston",
}

# The counties drawn from a map the county publishes, or its planning and
# development district publishes for it, because the Census still carries its
# 2020 edition there, which in six of them (Copiah, Harrison, Hinds, Perry,
# Simpson and Warren) puts every resident in the same district as its 2010
# edition (measured 2026-10-16 by `--survey`). STATED, never derived, like the
# list above. Each entry names the evidence that its lines are the ones adopted
# after the 2020 census, and the build re-reads that evidence every time:
#   layer_name       the layer's own name, compared exactly; "Supervisor
#                    Districts Adopted 2022" names its own adoption;
#   service_says     a phrase the map service's own description must carry;
#   document         a document the county publishes, pinned by its SHA-256,
#                    whose printed map was compared with the layer by eye on
#                    the date given; a changed document stops the build until
#                    a person compares the new one;
#   plan_population  a population field published with each district, which
#                    must equal the 2020 census's own block counts;
#   precincts        the county's own map of its voting precincts, which must
#                    follow these lines and not the Census's: `url` and
#                    `layer_name` as above, `name_field` naming each precinct,
#                    and `district_field` where each precinct names its
#                    supervisor district. A precinct that names none belongs to
#                    the district holding most of its residents under the lines
#                    being tested. precinct_witness() says what is measured.
# `label_field` is a field naming the district in words ("Supervisor District
# 3"), which must name the same number as `field`. `names` is a field naming
# each district's supervisor, which must agree with the Secretary of State's
# directory. `set_aside` names blocks a plan's own population figures leave
# out, with their 2020 population: each is re-read from the Census and must
# hold at least SET_ASIDE_PEOPLE_PER_HOME people per housing unit, the shape
# of a prison or a dormitory rather than of homes. `source` is the sentence the
# card prints.
CMPDD = "https://gis.cmpdd.org/server/rest/services/Hosted/"
_CMPDD_SOURCE = ("%s County's supervisor districts as the Central Mississippi Planning "
                 "and Development District publishes them in its map viewer for the "
                 "county")
COUNTY_SOURCES = {
    "029": {"county": "Copiah",
            "url": CMPDD + "Copiah_County_Feature_Layer/FeatureServer/15",
            "field": "district", "label_field": "name",
            "layer_name": "Supervisor Districts Adopted 2022",
            "plan_population": "population",
            "source": _CMPDD_SOURCE % "Copiah"},
    # The layer's own description and the service's description still name the
    # plan adopted in 2013 on the 2010 census; the service's serviceDescription
    # says these lines were approved in 2023 from the 2020 census (all three
    # read 2026-10-15). The lines side with the second: they are not the
    # Census's lines for the county, and they balance at 6.2% on the 2020
    # blocks where the Census's measure 45.6%. The Census's lines are not the
    # 2013 plan either, which this comment said they were until 2026-10-16:
    # they put every resident in the same district as its 2010 edition, the
    # lines it held on January 1, 2010, which measure 35.8% apart on the 2010
    # census's own counts. The layer
    # also names each district's supervisor, and the names are the directory's.
    "047": {"county": "Harrison",
            "url": ("https://geo.co.harrison.ms.us/server/rest/services/AGO/"
                    "HarrisonCounty_SupervisorDistrict/FeatureServer/0"),
            "field": "DISTRICT", "names": "DIST_NAME",
            "layer_name": "HarrisonCounty_Supervisor Districts",
            "service_says": "approved 2023 as a result of the 2020 US Census",
            "source": ("Harrison County's supervisor districts as the county publishes "
                       "them on its own map server")},
    "049": {"county": "Hinds",
            "url": CMPDD + "Hinds_County_Map/FeatureServer/17",
            "field": "district", "label_field": "name2",
            "layer_name": "Hinds Supervisor Districts",
            "plan_population": "population",
            "source": _CMPDD_SOURCE % "Hinds"},
    # The county's own website publishes a printed map of these districts,
    # dated 8/09/2022 by the county's GIS department; its districts were
    # compared with this layer's by eye on 2026-10-15 and match.
    "073": {"county": "Lamar",
            "url": ("https://services1.arcgis.com/mz3jHVSffoNsLuEB/arcgis/rest/services/"
                    "Lamar_Service/FeatureServer/15"),
            "field": "ID", "label_field": "NAME",
            "layer_name": "Supervisor Districts",
            "document": {
                "url": ("https://www.lamarcountyms.gov/ms/wp-content/uploads/2022/08/"
                        "sup_dist_districts.pdf"),
                "sha256": "95d18adb65beeb3519c6e7f1aaaace84130a9f90f5552690b84cbdea00694081",
                "compared": "2026-10-15"},
            "source": ("Lamar County's supervisor districts as published in the parcel "
                       "viewer the county's website links to")},
    # The account publishing this layer is named for the county, which is all
    # that says whose map it is; an identical copy in another account is named
    # Supr_Dist_Adopted_2022_Lee_Co (no resident differs, measured 2026-10-15).
    # The witness is the Lee County Circuit Clerk's 2024 precinct splits, which
    # describe themselves as the Circuit Clerk's and name each split's
    # supervisor district. The map the county's website links under "Maps"
    # (the Board of Supervisors Map, whose districts are a layer called
    # Supervisor Zones) puts 122 residents in a different district from this
    # layer and is not used: it disagrees with the Circuit Clerk's splits for
    # 128 people, against 10 for this layer, and a populated block lies as
    # little as 30% inside one of its districts, so it cannot be resolved to
    # whole blocks (measured 2026-10-15 and 2026-10-16).
    "081": {"county": "Lee",
            "url": ("https://services3.arcgis.com/j2GTvlDqmJmX3REZ/arcgis/rest/services/"
                    "New_Districts/FeatureServer/4"),
            "field": "DISTRICT",
            "layer_name": "Lee Supervisor Districts 2022",
            "precincts": {
                "url": ("https://services.arcgis.com/AzU5dE5IP7kWAdH7/arcgis/rest/services/"
                        "Lee_County_Master_Splits_2024/FeatureServer/0"),
                "layer_name": "MasterSplitAugust24",
                "name_field": "PRECINCT", "district_field": "SUPERVISOR"},
            "source": ("Lee County's supervisor districts from the map published online as "
                       "Lee Supervisor Districts 2022, which the Lee County Circuit Clerk's "
                       "2024 voting precinct map follows")},
    "089": {"county": "Madison",
            "url": CMPDD + "Madison_County_Map/FeatureServer/44",
            "field": "district", "label_field": "name",
            "layer_name": "Supervisor Districts Adopted 2022",
            "plan_population": "population",
            "source": _CMPDD_SOURCE % "Madison"},
    # The county's Board of Supervisors page links "Find My Supervisor" to a map
    # whose supervisor districts are this layer, and the same page links the
    # county's printed map, titled "Board of Supervisors Districts Effective
    # January 1, 2023", which was compared with this layer by eye on 2026-10-16
    # and matches. The layer names each district's supervisor; only the names
    # are read, to compare with the directory. Its own service's 2023 precinct
    # layer names each precinct's district.
    "109": {"county": "Pearl River",
            "url": ("https://services6.arcgis.com/9h5t9CkNYcgSXrCh/arcgis/rest/services/"
                    "Redistricting_2023/FeatureServer/91"),
            "field": "District", "names": "ElectedRep",
            "layer_name": "BOS2023",
            "document": {
                "url": ("https://pearlrivercounty.net/DocumentCenter/View/115/"
                        "Pearl-River-Board-Supervisors-Map-2023-PDF"),
                "sha256": "a83c2415c1cafe3d40a644e7005a82e998a286e8e8268babe7818b842f1844f1",
                "compared": "2026-10-16"},
            "precincts": {
                "url": ("https://services6.arcgis.com/9h5t9CkNYcgSXrCh/arcgis/rest/services/"
                        "Redistricting_2023/FeatureServer/92"),
                "layer_name": "Precincts2023",
                "name_field": "PrecinctName", "district_field": "District"},
            "source": ("Pearl River County's supervisor districts from the Find My Supervisor "
                       "map on the county's website, which matches the county's printed map "
                       "of the districts effective 1 January 2023")},
    # The county's Board of Supervisors page links "Find My Supervisor" to the
    # county's GIS map, which draws this layer as its Supervisor Districts and a
    # layer of 2023 voting precincts beside it. Two other layers in the same
    # account draw the same lines (0.00074% of the county's area differs,
    # measured 2026-10-16).
    "111": {"county": "Perry",
            "url": ("https://services3.arcgis.com/V34P0GFhKji2Th5l/arcgis/rest/services/"
                    "Perry_Addressing_Service/FeatureServer/9"),
            "field": "name",
            "layer_name": "SUPERVISOR_DISTRICTS",
            "precincts": {
                "url": ("https://services3.arcgis.com/V34P0GFhKji2Th5l/arcgis/rest/services/"
                        "PRECINCTS_2023/FeatureServer/0"),
                "layer_name": "PRECINCTS_2023",
                "name_field": "Name"},
            "source": ("Perry County's supervisor districts from the Find My Supervisor map "
                       "on the county's website, whose 2023 voting precincts follow the same "
                       "lines")},
    # The plan's own population figures leave out two blocks: 3,633 people in a
    # block with 3 housing units (District 5) and 157 in a block with none
    # (District 1), read from the Census 2026-10-15. Counting them, the five
    # districts differ by 19.2% of an equal share on the 2020 blocks; the record
    # carries the figure with them set aside as the plan sets them aside.
    "121": {"county": "Rankin",
            "url": CMPDD + "Rankin_County_Feature_Layer/FeatureServer/13",
            "field": "district", "label_field": "name", "names": "supervisor_name",
            "layer_name": "Supervisor Districts Adopted 2021",
            "plan_population": "population",
            "set_aside": {"281210205002004": 3633, "281210203041070": 157},
            "source": _CMPDD_SOURCE % "Rankin"},
    "127": {"county": "Simpson",
            "url": CMPDD + "Simpson_County_Feature_Layer/FeatureServer/32",
            "field": "district", "label_field": "name",
            "layer_name": "Supervisor Districts Adopted 2022",
            "plan_population": "population",
            "source": _CMPDD_SOURCE % "Simpson"},
    "149": {"county": "Warren",
            "url": CMPDD + "Warren_County_Feature_Layer/FeatureServer/21",
            "field": "district", "label_field": "name",
            "layer_name": "Supervisor Districts Adopted 2022",
            "plan_population": "population",
            "source": _CMPDD_SOURCE % "Warren"},
}
# gis.cmpdd.org sends its own certificate without the GoDaddy intermediate that
# signed it, measured 2026-10-15; the intermediate is pinned in
# scripts/aia_bundle.py rather than verification turned off.
PINNED_CHAINS = {"gis.cmpdd.org": "godaddy-g2"}
SET_ASIDE_PEOPLE_PER_HOME = 10
# What the record keeps of an entry, so --check can hold the entry to it.
WITNESS_KEYS = ("layer_name", "service_says", "document", "plan_population", "names",
                "set_aside", "precincts")
# A county's precinct map as a witness (precinct_witness). It must put no more
# than PRECINCT_MAX_OFF_SHARE of the county's residents in a different district
# from the drawn lines, while putting at least MIN_PEOPLE_MOVED in a different
# district from the Census's, so that it tells the two apart; and it must place
# all but PRECINCT_MAX_UNPLACED_SHARE of them in exactly one precinct. Measured
# 2026-10-16 on the three counties that use one, with residents placed by their
# 2020 block's internal point: Lee 10 of 83,343 residents against 13,351 for
# the Census's lines, Pearl River 0 of 56,145 against 4,919, and Perry 8 of
# 11,511 against 444.
PRECINCT_MAX_OFF_SHARE = 0.005
PRECINCT_MAX_UNPLACED_SHARE = 0.01
# Resolving a county's map to whole 2020 blocks. A populated block must lie at
# least MIN_POPULATED_SHARE inside one district, or the people in it could be
# given either supervisor (measured worst 2026-10-15: Lamar 0.721, the other
# seven 0.933 or more; 2026-10-16: Lee 0.789, Pearl River 0.745, Perry 0.639).
# A block with nobody in it that no district covers to EVEN_SHARE is split
# about evenly; it goes to the larger share, and the ground in such blocks is
# bounded per county by MAX_EVEN_KM2 (measured Lamar 0.586 km2 in 17 blocks,
# Perry 0.160 km2 in 7 and Lee 0.010 km2 in 1, the other eight none).
MIN_POPULATED_SHARE = 0.6
EVEN_SHARE = 0.55
MAX_EVEN_KM2 = 1.0

DISTRICTS = ("1", "2", "3", "4", "5")
MAX_DEVIATION_PCT = 10.0
# A change smaller than this many residents is not counted as new lines: it is
# the size of a boundary correction, not of a redistricting plan. Measured
# 2026-10-15, the smallest change among the twelve moves 530 people (Choctaw),
# and Clay's, which covers 0.07% of the county's area, moves 689.
MIN_PEOPLE_MOVED = 50
SIMPLIFY = "interval=5"
EDGE_M = 20.0               # two simplified files, each within the 8 m ceiling (5.0 m apart at most, 2026-10-16)
AGREEMENT_SAMPLES = 2000
WITNESS_SAMPLES = 4000
PAGE = 20000


# ---------------------------------------------------------------- fetching --
def _get(url, params):
    q = url + "/query?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            require_robots_once(q, USER_AGENT, headers={"User-Agent": USER_AGENT},
                                label="ms-build-ms-supervisor-districts")
            req = urllib.request.Request(q, headers={"User-Agent": USER_AGENT,
                                                     "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=240) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and "error" in data:
                # An ArcGIS error is an object, not an empty answer.
                raise RuntimeError("TIGERweb answered an error: %r" % (data["error"],))
            return data
        except Exception as err:  # noqa: BLE001 — retried, then raised
            if attempt == 3:
                raise
            print("supervisor-districts: retrying after %s" % err, file=sys.stderr)
            time.sleep(2 ** (attempt + 1))


def _layer_name(url):
    req = urllib.request.Request(url + "?f=json", headers={"User-Agent": USER_AGENT})
    require_robots_once(url, USER_AGENT, headers={"User-Agent": USER_AGENT},
                        label="ms-build-ms-supervisor-districts")
    with urllib.request.urlopen(req, timeout=120) as resp:
        meta = json.loads(resp.read().decode("utf-8"))
    return meta.get("name"), meta.get("description") or ""


_BUNDLES = {}


def _bundle(host):
    """The CA bundle for a host that leaves out its intermediate, else None."""
    key = PINNED_CHAINS.get(host)
    if key is None:
        return None
    if key not in _BUNDLES:
        path = aia_bundle.ca_bundle("ms-build-ms-supervisor-districts", key)
        atexit.register(lambda p=path: os.path.exists(p) and os.remove(p))
        _BUNDLES[key] = path
    return _BUNDLES[key]


def _fetch(url, pace=1.0):
    """GET one url as this builder's client, after its host's robots.txt, with
    the pinned chain where the host needs one. Bytes; raises after 4 tries."""
    host = urllib.parse.urlsplit(url).hostname
    bundle = _bundle(host)
    ctx = ssl.create_default_context(cafile=bundle) if bundle else None
    require_robots_once(url, USER_AGENT, headers={"User-Agent": USER_AGENT},
                        label="ms-build-ms-supervisor-districts", verify=bundle)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            time.sleep(pace)
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                return resp.read()
        except Exception as err:  # noqa: BLE001 — retried, then raised
            if attempt == 3:
                raise
            print("supervisor-districts: retrying %s after %s" % (host, err), file=sys.stderr)
            time.sleep(2 ** (attempt + 1))


def _fetch_json(url, params=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    data = json.loads(_fetch(url).decode("utf-8"))
    if isinstance(data, dict) and "error" in data:
        # An ArcGIS error is an object, not an empty answer.
        raise SystemExit("FAIL: %s answered an error: %r" % (url, data["error"]))
    return data


# ------------------------------------------------------------ ArcGIS rings --
# EVERY POLYGON THIS BUILDER READS ARRIVES AS ARCGIS JSON AND IS CONVERTED
# HERE, NEVER AS THE SERVER'S OWN GEOJSON, because the server's conversion was
# measured wrong on 2026-10-15. Asked for GeoJSON, Lamar County's layer sent
# District 3, whose two parts ArcGIS's own JSON gives as two clockwise outer
# rings, as ONE Polygon, which makes the smaller part (3.0 km2, 15 blocks, 1,317
# people) a hole lying outside the larger. The same all-districts query had
# sent the correct MultiPolygon minutes earlier and did again minutes later, and
# a query for that district alone sent it every time, so the fault comes and
# goes. The population checks caught it, as a district in which those people
# lived nowhere. TIGERweb's conversion was not seen to fail and is read the
# same way regardless, because a Census district read like that would ship
# with a hole where its second part should be and no population check would
# notice: the point test the checks use reads rings even-odd, which counts
# the misread part either way.
def _ring_area(ring):
    """A ring's shoelace area in square degrees: negative when the ring runs
    clockwise, which is how ArcGIS draws an outer ring."""
    return sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
               for i in range(len(ring) - 1)) / 2.0


def esri_polygon(rings, what):
    """ArcGIS JSON rings as a GeoJSON geometry, by ArcGIS's own rule: a
    clockwise ring is an outer ring, a counter-clockwise one is a hole, and a
    hole belongs to the smallest outer ring that covers it. Anything that
    rule cannot place stops the build."""
    from shapely.geometry import Point, Polygon
    from shapely.prepared import prep
    outers, holes = [], []
    for ring in rings or []:
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise SystemExit("FAIL: %s has a ring that is not closed" % what)
        area = _ring_area(ring)
        if area == 0:
            raise SystemExit("FAIL: %s has a ring with no area" % what)
        (outers if area < 0 else holes).append(ring)
    if not outers:
        raise SystemExit("FAIL: %s has no outer ring" % what)
    shells = [Polygon(r) for r in outers]
    ready = [prep(s) for s in shells]
    parts = [[r] for r in outers]
    for hole in holes:
        homes = [i for i, s in enumerate(ready)
                 if all(s.covers(Point(x, y)) for x, y in hole[:-1])]
        if not homes:
            raise SystemExit("FAIL: %s has a hole outside every outer ring" % what)
        parts[min(homes, key=lambda i: shells[i].area)].append(hole)
    if len(parts) == 1:
        return {"type": "Polygon", "coordinates": parts[0]}
    return {"type": "MultiPolygon", "coordinates": parts}


def esri_features(data, what, key):
    """GeoJSON-shaped features from an ArcGIS JSON query answer. `key` names
    the attribute a failure message identifies a feature by."""
    sr = data.get("spatialReference") or {}
    if data.get("features") and 4326 not in (sr.get("wkid"), sr.get("latestWkid")):
        raise SystemExit("FAIL: %s answered in spatial reference %r, not 4326" % (what, sr))
    out = []
    for f in data.get("features") or []:
        attrs = f.get("attributes") or {}
        rings = (f.get("geometry") or {}).get("rings")
        out.append({"type": "Feature", "properties": attrs,
                    "geometry": (esri_polygon(rings, "%s %s %r" % (what, key, attrs.get(key)))
                                 if rings else None)})
    return out


# Rounding to six decimals leaves a few rings touching themselves, which
# shapely calls invalid: 20 of the 21,142 blocks in the eight county-map
# counties, measured 2026-10-15, where buffer(0) changed each one's area by at
# most 2.2e-15 of itself, which is arithmetic noise. A part read as a hole
# outside its shell loses the whole part to the same repair (Lamar's District
# 3 would have lost its 3.0 km2 second part, which the repair measures as a
# 0.6% change in area), so a repair that changes the area by more than one part
# in a million stops the build instead.
REPAIR_TOLERANCE = 1e-6


def checked_shape(geom, what):
    """A shapely geometry for a GeoJSON one, repaired only where the repair
    leaves what it covers unchanged."""
    from shapely.geometry import shape
    from shapely.validation import explain_validity
    g = shape(geom)
    if g.is_valid:
        return g
    fixed = g.buffer(0)
    if g.area <= 0 or abs(fixed.area - g.area) > REPAIR_TOLERANCE * g.area:
        raise SystemExit("FAIL: %s is not a valid polygon (%s), and repairing it would "
                         "change its area by %.4f%%"
                         % (what, explain_validity(g),
                            100.0 * (fixed.area - g.area) / g.area if g.area else 100.0))
    return fixed


def fetch_county_layer(spec):
    """The county's own layer: its name, the service's descriptions, and its
    features at full precision."""
    meta = _fetch_json(spec["url"], {"f": "json"})
    service = _fetch_json(spec["url"].rsplit("/", 1)[0], {"f": "json"})
    fc = _fetch_json(spec["url"] + "/query", {
        "where": "1=1", "outFields": "*", "returnGeometry": "true", "outSR": "4326",
        "geometryPrecision": "6", "f": "json"})
    if fc.get("exceededTransferLimit"):
        raise SystemExit("FAIL: %s hit its transfer limit" % spec["url"])
    return {"name": meta.get("name"),
            "descriptions": " ".join(str(service.get(k) or "") for k in
                                     ("serviceDescription", "description")),
            "features": esri_features(fc, spec["url"], spec["field"])}


def fetch_cousubs(url, counties, extra=""):
    """{county3: {district: feature}} for the given counties, full precision;
    `extra` names more fields to read (",POP100" for the 2010 edition's own
    count of each district)."""
    where = "STATE='%s' AND COUNTY IN (%s)" % (STATE, ",".join("'%s'" % c for c in sorted(counties)))
    feats, offset = [], 0
    while True:
        page = _get(url, {
            "where": where, "outFields": "GEOID,COUNTY,BASENAME,FUNCSTAT" + extra,
            "outSR": "4326", "geometryPrecision": "6", "f": "json",
            "orderByFields": "GEOID", "resultOffset": offset, "resultRecordCount": 1000,
        })
        got = esri_features(page, url, "GEOID")
        feats.extend(got)
        more = page.get("exceededTransferLimit")
        if not got or (len(got) < 1000 and not more):
            break
        offset += len(got)
    out = {}
    for f in feats:
        p = f.get("properties") or {}
        c, d = p.get("COUNTY"), str(p.get("BASENAME") or "").strip()
        if not f.get("geometry"):
            raise SystemExit("FAIL: %s %s district %r has no geometry" % (url, c, d))
        if d in out.setdefault(c, {}):
            raise SystemExit("FAIL: %s county %s carries district %r twice" % (url, c, d))
        out[c][d] = f
    return out


def fetch_blocks(county3, detail=False):
    """[(lng, lat, people)] for every populated 2020 block in the county, or
    with `detail` [(lng, lat, people, GEOID, housing units)]."""
    out, seen, offset = [], set(), 0
    while True:
        data = _get(BLOCKS, {
            "where": "STATE='%s' AND COUNTY='%s' AND POP100>0" % (STATE, county3),
            "outFields": "GEOID,INTPTLAT,INTPTLON,POP100,HU100", "returnGeometry": "false",
            "orderByFields": "GEOID", "resultOffset": offset, "resultRecordCount": PAGE,
            "f": "json",
        })
        feats = data.get("features") or []
        for f in feats:
            a = f["attributes"]
            if a["GEOID"] in seen:
                raise SystemExit("FAIL: block %s returned twice across pages" % a["GEOID"])
            seen.add(a["GEOID"])
            row = (float(a["INTPTLON"]), float(a["INTPTLAT"]), int(a["POP100"]))
            out.append(row + (a["GEOID"], int(a["HU100"])) if detail else row)
        if len(feats) < PAGE and not data.get("exceededTransferLimit"):
            break
        offset += len(feats)
    return out


def fetch_block_polygons(county3):
    """Every 2020 block in the county, populated or not, as GeoJSON-shaped
    features (read as ArcGIS JSON, esri_polygon) with GEOID, POP100, HU100 and
    the internal point, to six decimals."""
    out, seen, offset = [], set(), 0
    while True:
        page = _get(BLOCKS, {
            "where": "STATE='%s' AND COUNTY='%s'" % (STATE, county3),
            "outFields": "GEOID,POP100,HU100,INTPTLAT,INTPTLON", "returnGeometry": "true",
            "outSR": "4326", "geometryPrecision": "6", "orderByFields": "GEOID",
            "resultOffset": offset, "resultRecordCount": 3000, "f": "json",
        })
        got = esri_features(page, BLOCKS, "GEOID")
        for f in got:
            g = f["properties"]["GEOID"]
            if g in seen:
                raise SystemExit("FAIL: block %s returned twice across pages" % g)
            if not f.get("geometry"):
                raise SystemExit("FAIL: block %s has no geometry" % g)
            seen.add(g)
        out.extend(got)
        more = page.get("exceededTransferLimit")
        if len(got) < 3000 and not more:
            break
        offset += len(got)
    return out


def tract_totals():
    """{county3: people} from the 2020 tract layer, an aggregation this script
    does not perform — the witness that the block read is complete."""
    stats = json.dumps([{"statisticType": "sum", "onStatisticField": "POP100",
                         "outStatisticFieldName": "pop"}])
    data = _get(TRACTS, {"where": "STATE='%s'" % STATE, "groupByFieldsForStatistics": "COUNTY",
                         "outStatistics": stats, "f": "json"})
    return {f["attributes"]["COUNTY"]: int(f["attributes"]["pop"]) for f in data["features"]}


# ------------------------------------------------------------- measuring ----
def _index(features_by_district):
    return [(d, f["geometry"], blb._bbox(f["geometry"])) for d, f in features_by_district.items()]


def _where(model, x, y):
    hits = [d for d, geom, bb in model
            if bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3] and blb._point_in_geometry((x, y), geom)]
    return hits


def assign(blocks, districts):
    """{district: people}, plus the people in no district and in two, and the
    per-block answers (for comparing two sets of lines block by block)."""
    model = _index(districts)
    pop = {d: 0 for d in districts}
    none = multi = 0
    answers = []
    for x, y, n in blocks:
        hits = _where(model, x, y)
        if len(hits) == 1:
            pop[hits[0]] += n
            answers.append(hits[0])
        elif not hits:
            none += n
            answers.append(None)
        else:
            multi += n
            answers.append("MULTI")
    return pop, none, multi, answers


def deviation_pct(pop):
    vals = [pop.get(d, 0) for d in DISTRICTS]
    ideal = sum(vals) / 5.0
    return 100.0 * (max(vals) - min(vals)) / ideal if ideal else float("inf")


def measure_county(c3, cur, old, blocks):
    """The two confirmations for one county, as numbers."""
    pop, none, multi, now = assign(blocks, cur)
    old_pop, _, _, then = assign(blocks, old) if old else ({}, 0, 0, [None] * len(blocks))
    moved = sum(n for (x, y, n), a, b in zip(blocks, now, then) if a != b)
    return {
        "people": sum(n for _, _, n in blocks),
        "deviation_pct": round(deviation_pct(pop), 2),
        "deviation_2020_edition_pct": round(deviation_pct(old_pop), 2) if old else None,
        "people_moved_from_2020_edition": moved,
        "people_in_no_district": none,
        "people_in_two_districts": multi,
        "district_people": {d: pop[d] for d in DISTRICTS if d in pop},
    }


_NUMBER = re.compile(r"^\s*(?:SD|(?:Supervisor\s+)?District\s*)?0*([1-5])\s*$", re.I)
_WORDS = re.compile(r"\bDistrict\s+0*([1-5])\s*$", re.I)
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


def district_number(value):
    """'SD3', 'District 3', '3' and 3 all read as '3'; anything else as None."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        value = "%d" % value if float(value) == int(value) else str(value)
    m = _NUMBER.match(str(value))
    return m.group(1) if m else None


def districts_of(spec, features):
    """{district: feature} from a county's own layer, and what is wrong with it."""
    out, problems = {}, []
    for f in features:
        p = f.get("properties") or {}
        d = district_number(p.get(spec["field"]))
        if d is None:
            problems.append("%s %r is not a district 1-5" % (spec["field"], p.get(spec["field"])))
            continue
        if d in out:
            problems.append("district %s appears twice" % d)
            continue
        if (f.get("geometry") or {}).get("type") not in ("Polygon", "MultiPolygon"):
            problems.append("district %s has no polygon" % d)
            continue
        label = spec.get("label_field")
        if label:
            m = _WORDS.search(str(p.get(label) or ""))
            if not m or m.group(1) != d:
                problems.append("district %s is called %r in %s" % (d, p.get(label), label))
        out[d] = f
    if sorted(out) != list(DISTRICTS):
        problems.append("the layer draws districts %s, not 1-5" % sorted(out))
    return out, problems


def _surname(name):
    words = [w.strip(".,").lower() for w in str(name).split()]
    words = [w for w in words if w and w not in _SUFFIXES]
    return words[-1] if words else ""


def _edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def names_problems(spec, ds, directory):
    """A layer that names each district's supervisor must name the person the
    Secretary of State's directory names for the same number: the surname equal,
    or one letter apart ("Schoggen" in the layer, "Schoggens" in the directory).
    This is the strongest check that the layer's numbers are the county's."""
    field = spec.get("names")
    if not field:
        return [], 0
    seats = {str(s.get("district")): s for s in (directory or {}).get("supervisors") or []}
    problems, checked = [], 0
    for d, f in sorted(ds.items()):
        layer_name = (f.get("properties") or {}).get(field)
        seat = seats.get(d) or {}
        if not layer_name or not seat.get("name"):
            continue  # a vacancy or an unnamed district says nothing about numbering
        a, b = _surname(layer_name), _surname(seat["name"])
        if a != b and _edit_distance(a, b) > 1:
            problems.append("district %s: the layer names %r and the directory %r"
                            % (d, layer_name, seat["name"]))
        checked += 1
    return problems, checked


def measure_published(spec, ds, cur, old, blocks):
    """The checks on a county's own lines, as numbers and problems. `blocks` is
    fetch_blocks(..., detail=True); `ds` the county's districts, already cut to
    the county's own outline."""
    pts = [(x, y, n) for x, y, n, _, _ in blocks]
    pop, none, multi, now = assign(pts, ds)
    _, _, _, census_now = assign(pts, cur)
    old_pop, _, _, census_then = assign(pts, old)
    problems = []
    moved = sum(n for (x, y, n), a, b in zip(pts, now, census_then) if a != b)
    census_moved = sum(n for (x, y, n), a, b in zip(pts, census_now, census_then) if a != b)
    # The plan's own set-asides, each re-read from the Census.
    aside = spec.get("set_aside") or {}
    if aside and not spec.get("plan_population"):
        problems.append("set-aside blocks without a published population to justify them")
    found = {g: (n, h, a) for (x, y, n, g, h), a in zip(blocks, now)}
    aside_by_district = {d: 0 for d in DISTRICTS}
    for geoid, stated in sorted(aside.items()):
        if geoid not in found:
            problems.append("set-aside block %s is not a populated block of the county" % geoid)
            continue
        n, h, a = found[geoid]
        if n != stated:
            problems.append("set-aside block %s holds %d people, not %d" % (geoid, n, stated))
        if h * SET_ASIDE_PEOPLE_PER_HOME > n:
            problems.append("set-aside block %s has %d housing units for %d people — homes, "
                            "not group quarters" % (geoid, h, n))
        if a not in DISTRICTS:
            problems.append("set-aside block %s is in no single district" % geoid)
        else:
            aside_by_district[a] += n
    counted = {d: pop.get(d, 0) - aside_by_district[d] for d in DISTRICTS}
    plan = None
    if spec.get("plan_population"):
        plan = {}
        for d, f in sorted(ds.items()):
            v = (f.get("properties") or {}).get(spec["plan_population"])
            plan[d] = int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
        off = {d: (plan[d], counted[d]) for d in DISTRICTS if plan.get(d) != counted[d]}
        if off:
            problems.append("the published population differs from the 2020 blocks "
                            "(published, blocks): %s" % off)
    # Numbering: the county's districts against the 2020 edition's, which
    # carry the same numbers. The pairing that keeps the most people in a
    # district of the same number must be 1-1, 2-2 and so on. Plurality alone
    # is not the test: a district that changed a lot can hold more of its
    # neighbour's old residents than of its own (Madison's District 1, measured
    # 2026-10-15), while the best one-to-one pairing still keeps its number.
    weight = {}
    for (x, y, n), a, b in zip(pts, now, census_then):
        weight[(a, b)] = weight.get((a, b), 0) + n
    score = {perm: sum(weight.get((d, perm[i]), 0) for i, d in enumerate(DISTRICTS))
             for perm in itertools.permutations(DISTRICTS)}
    best = max(score.values())
    if score[DISTRICTS] != best:
        winner = [p for p, s in score.items() if s == best][0]
        problems.append("the numbering does not follow the 2020 edition's: the best pairing "
                        "is %s, keeping %d people against %d for 1-5"
                        % (dict(zip(DISTRICTS, winner)), best, score[DISTRICTS]))
    m = {
        "people": sum(n for _, _, n in pts),
        "people_set_aside": sum(aside_by_district.values()),
        "deviation_pct": round(deviation_pct(counted), 2),
        "deviation_2020_edition_pct": round(deviation_pct(old_pop), 2),
        "people_moved_from_2020_edition": moved,
        "census_people_moved_from_2020_edition": census_moved,
        "people_in_no_district": none,
        "people_in_two_districts": multi,
        "district_people": counted,
        "plan_population": plan,
        "numbering_kept_people": score[DISTRICTS],
    }
    return m, problems


def source_witness_problems(spec, layer):
    """The evidence an entry names for its lines being the current plan, re-read
    now. `layer` is fetch_county_layer(spec)."""
    problems = []
    if layer["name"] != spec["layer_name"]:
        problems.append("the layer is now called %r, not %r" % (layer["name"], spec["layer_name"]))
    phrase = spec.get("service_says")
    if phrase and phrase not in layer["descriptions"]:
        problems.append("the service's description no longer says %r" % phrase)
    doc = spec.get("document")
    if doc:
        got = hashlib.sha256(_fetch(doc["url"])).hexdigest()
        if got != doc["sha256"]:
            problems.append("%s has changed (SHA-256 %s, compared with the layer on %s as %s) "
                            "— compare the new map with the layer, then pin it"
                            % (doc["url"], got, doc["compared"], doc["sha256"]))
    if not (phrase or doc or spec.get("plan_population") or spec.get("precincts")):
        # A layer's name alone is compared, never counted: "Supervisor
        # Districts" says nothing about which plan it draws.
        problems.append("the entry names no evidence that these are the current lines")
    return problems


def fetch_precincts(pspec):
    """A county's precinct layer: its name and its precincts at full
    precision. Only the precinct's name and district fields are asked for, so
    nothing else such a layer carries is read (Coahoma's 2022 precinct and
    supervisor layers carry population by race, read 2026-10-16)."""
    meta = _fetch_json(pspec["url"], {"f": "json"})
    fields = [pspec["name_field"]] + ([pspec["district_field"]]
                                      if pspec.get("district_field") else [])
    fc = _fetch_json(pspec["url"] + "/query", {
        "where": "1=1", "outFields": ",".join(fields), "returnGeometry": "true",
        "outSR": "4326", "geometryPrecision": "6", "f": "json"})
    if fc.get("exceededTransferLimit"):
        raise SystemExit("FAIL: %s hit its transfer limit" % pspec["url"])
    return meta.get("name"), esri_features(fc, pspec["url"], pspec["name_field"])


def precinct_witness(spec, ds, census, pts):
    """A county's own voting precincts as the witness that its lines are the
    ones its elections use. Each populated 2020 block goes to the precinct
    holding its internal point. The district a block SHOULD be in is the one
    its precinct names, or, for a layer naming none, the one holding most of
    the precinct's residents under the lines being tested; the second asks
    only whether the precincts nest inside those lines, which a precinct map
    can do for one plan and not for a plan that cuts across its precincts.
    Counted for the county's lines as drawn (`ds`, resolved to blocks) and for
    the Census's current lines (`census`). Returns (measurements, problems)."""
    from shapely import STRtree
    from shapely.geometry import Point
    pspec = spec["precincts"]
    name, feats = fetch_precincts(pspec)
    problems = []
    if name != pspec["layer_name"]:
        problems.append("the precinct layer is now called %r, not %r"
                        % (name, pspec["layer_name"]))
    shapes, named = [], []
    for f in feats:
        p = f.get("properties") or {}
        label = p.get(pspec["name_field"])
        if not f.get("geometry"):
            problems.append("precinct %r has no polygon" % label)
            continue
        if pspec.get("district_field"):
            d = district_number(p.get(pspec["district_field"]))
            if d is None:
                problems.append("precinct %r names %s %r, not a district 1-5"
                                % (label, pspec["district_field"], p.get(pspec["district_field"])))
                continue
            named.append(d)
        shapes.append(checked_shape(f["geometry"], "precinct %r" % label))
    if len(shapes) < len(DISTRICTS):
        problems.append("the precinct layer holds %d precincts" % len(shapes))
        return None, problems
    if pspec.get("district_field") and sorted(set(named)) != list(DISTRICTS):
        problems.append("the precincts name districts %s, not 1-5" % sorted(set(named)))
    tree = STRtree(shapes)
    where, none, multi = [], 0, 0
    for x, y, n in pts:
        pt = Point(x, y)
        hits = [int(i) for i in tree.query(pt) if shapes[int(i)].covers(pt)]
        if len(hits) == 1:
            where.append(hits[0])
            continue
        where.append(None)
        if hits:
            multi += n
        else:
            none += n

    def off(lines):
        _, _, _, answers = assign(pts, lines)
        if pspec.get("district_field"):
            want = [named[w] if w is not None else None for w in where]
        else:
            tally = {}
            for (x, y, n), w, a in zip(pts, where, answers):
                if w is not None:
                    tally.setdefault(w, collections.Counter())[a] += n
            want = [tally[w].most_common(1)[0][0] if w is not None else None for w in where]
        return sum(n for (x, y, n), e, a in zip(pts, want, answers)
                   if e is not None and e != a)

    people = sum(n for _, _, n in pts)
    m = {"precincts_read": len(shapes),
         "precinct_people_in_none": none,
         "precinct_people_in_two": multi,
         "precinct_people_off": off(ds),
         "precinct_people_off_census": off(census)}
    if none + multi > PRECINCT_MAX_UNPLACED_SHARE * people:
        problems.append("%d residents are in no precinct and %d in two (ceiling %.0f%% of %d)"
                        % (none, multi, 100 * PRECINCT_MAX_UNPLACED_SHARE, people))
    if m["precinct_people_off"] > PRECINCT_MAX_OFF_SHARE * people:
        problems.append("the precincts put %d residents in a different district from these "
                        "lines (ceiling %.1f%% of %d) — they do not follow them"
                        % (m["precinct_people_off"], 100 * PRECINCT_MAX_OFF_SHARE, people))
    if m["precinct_people_off_census"] < MIN_PEOPLE_MOVED:
        problems.append("the precincts put only %d residents in a different district from the "
                        "Census's lines, so they do not tell the two apart"
                        % m["precinct_people_off_census"])
    return m, problems


def resolve_to_blocks(raw, block_feats):
    """A county's own districts decide which district each 2020 block is in —
    the one covering most of the block's area — and each district is then the
    union of its blocks, so every vertex drawn is the Census Bureau's. Returns
    ({district: feature}, stats, problems); each feature keeps the county
    layer's properties (its population and names are checked from them)."""
    from pyproj import Transformer
    from shapely import STRtree, set_precision
    from shapely.geometry import mapping
    from shapely.ops import transform, unary_union
    to_m = Transformer.from_crs(4326, 5070, always_xy=True).transform  # equal area
    keys = sorted(raw)
    polys = [transform(to_m, checked_shape(raw[d]["geometry"], "district %s" % d)) for d in keys]
    tree = STRtree(polys)
    members = {d: [] for d in keys}
    problems, even, worst = [], [], 1.0
    for f in block_feats:
        p = f["properties"]
        g = checked_shape(f["geometry"], "block %s" % p["GEOID"])
        gm = transform(to_m, g)
        best, bd = 0.0, None
        if gm.area > 0:
            for i in tree.query(gm):
                share = polys[i].intersection(gm).area / gm.area
                if share > best:
                    best, bd = share, keys[i]
        if bd is None:
            problems.append("block %s lies in none of the county's districts" % p["GEOID"])
            continue
        if int(p["POP100"]) > 0:
            worst = min(worst, best)
            if best < MIN_POPULATED_SHARE:
                problems.append("block %s (%d people) is only %.0f%% inside district %s"
                                % (p["GEOID"], int(p["POP100"]), 100 * best, bd))
        elif best < EVEN_SHARE:
            even.append(gm.area)
        members[bd].append(g)
    even_km2 = sum(even) / 1e6
    if even_km2 > MAX_EVEN_KM2:
        problems.append("%d blocks with nobody in them, %.3f km2, are split about evenly "
                        "between districts (ceiling %.1f km2)" % (len(even), even_km2, MAX_EVEN_KM2))
    out = {}
    for d in keys:
        if not members[d]:
            problems.append("district %s holds no 2020 block" % d)
            continue
        union = set_precision(unary_union(members[d]), 1e-6)
        if union.geom_type not in ("Polygon", "MultiPolygon") or union.is_empty:
            problems.append("district %s unions to a %s" % (d, union.geom_type))
            continue
        out[d] = {"type": "Feature", "properties": dict(raw[d].get("properties") or {}),
                  "geometry": json.loads(json.dumps(mapping(union)))}
    stats = {"blocks_read": len(block_feats),
             "block_share_worst_populated": round(worst, 3),
             "blocks_split_evenly": len(even),
             "blocks_split_evenly_km2": round(even_km2, 3)}
    return out, stats, problems


# ------------------------------------------------------------- the build ----
def county_names():
    with open(COUNTIES_FILE) as fh:
        fc = json.load(fh)
    return {f["properties"]["GEOID"]: f["properties"]["NAME"] for f in fc["features"]}, fc


def roster_problems(roster, drawn):
    """The directory must name the same five districts the map draws."""
    problems = []
    for geoid in sorted(drawn):
        o = roster.get(geoid)
        if not o:
            problems.append("%s: no entry in ms-county-officials.json" % geoid)
            continue
        if o.get("label") not in ("District", "Beat"):
            problems.append("%s: directory label %r" % (geoid, o.get("label")))
        got = sorted(str(s.get("district")) for s in o.get("supervisors") or [])
        if got != list(DISTRICTS):
            problems.append("%s: the directory names districts %s, the map draws 1-5"
                            % (geoid, got))
        for s in o.get("supervisors") or []:
            if not (s.get("name") or s.get("vacant") is True):
                problems.append("%s district %s: neither a name nor a vacancy"
                                % (geoid, s.get("district")))
    return problems


def drawn_lines():
    """{county GEOID: "census" or "county"}: where each drawn county's lines come
    from."""
    both = sorted(set(CENSUS_COUNTIES) & set(COUNTY_SOURCES))
    if both:
        raise SystemExit("FAIL: %s are in both CENSUS_COUNTIES and COUNTY_SOURCES" % both)
    out = {STATE + c: "census" for c in CENSUS_COUNTIES}
    out.update({STATE + c: "county" for c in COUNTY_SOURCES})
    return out


_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def structure_problems(features, names, expected):
    """`expected` is drawn_lines(): which counties are drawn, and from what."""
    problems = []
    by = {}
    for f in features:
        p = f.get("properties") or {}
        geoid = p.get("countyfips")
        where = "%s district %s" % (geoid, p.get("district"))
        by.setdefault(geoid, []).append(str(p.get("district")))
        if p.get("county") != names.get(geoid):
            problems.append("%s carries county name %r, state-counties.json says %r"
                            % (where, p.get("county"), names.get(geoid)))
        if p.get("label") not in ("District", "Beat"):
            problems.append("%s: label %r" % (where, p.get("label")))
        want = expected.get(geoid)
        if p.get("lines") != want:
            problems.append("%s: lines %r, expected %r" % (where, p.get("lines"), want))
        if want == "county":
            spec = COUNTY_SOURCES[geoid[2:]]
            if p.get("source") != spec["source"]:
                problems.append("%s: source %r, COUNTY_SOURCES says %r"
                                % (where, p.get("source"), spec["source"]))
            if not _ISO_DATE.match(str(p.get("read") or "")):
                problems.append("%s: read %r is not a date" % (where, p.get("read")))
            aside = sum((spec.get("set_aside") or {}).values())
            if p.get("set_aside", 0) != aside:
                problems.append("%s: set_aside %r, COUNTY_SOURCES sets aside %d"
                                % (where, p.get("set_aside"), aside))
        elif "source" in p or "read" in p or "set_aside" in p:
            problems.append("%s: drawn from the Census and carries a county's source" % where)
        g = f.get("geometry") or {}
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            problems.append("%s: geometry %r" % (where, g.get("type")))
    if set(by) != set(expected):
        problems.append("drawn counties %s, expected %s"
                        % (sorted(by), sorted(expected)))
    for geoid, ds in sorted(by.items()):
        if sorted(ds) != list(DISTRICTS):
            problems.append("%s draws districts %s, not 1-5" % (geoid, sorted(ds)))
    return problems


def _edge_index(county_feats):
    return {g: blb._seg_index(f) for g, f in county_feats.items()}


def _near_line(pt, seg_idx, metres):
    gx, gy = int(math.floor(pt[0] / 0.02)), int(math.floor(pt[1] / 0.02))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for a, b in seg_idx.get((gx + dx, gy + dy), ()):
                if blb._point_to_segment_m(pt, a, b) <= metres:
                    return True
    return False


def county_witness(features, counties_fc, drawn, samples=WITNESS_SAMPLES, seed=2026):
    """Points over the drawn counties: the County layer and this layer must
    agree about the county, except within EDGE_M of a county line."""
    county_feats = {f["properties"]["GEOID"]: f for f in counties_fc["features"]}
    cmodel = [(g, f["geometry"], blb._bbox(f["geometry"])) for g, f in county_feats.items()]
    dmodel = [((f["properties"]["countyfips"], str(f["properties"]["district"])),
               f["geometry"], blb._bbox(f["geometry"])) for f in features]
    edges = _edge_index({g: county_feats[g] for g in drawn})
    box = [1e9, 1e9, -1e9, -1e9]
    for g in drawn:
        b = blb._bbox(county_feats[g]["geometry"])
        box = [min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])]
    rng = random.Random(seed)
    inside = agree = edge = 0
    bad = []
    for _ in range(samples):
        pt = (rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3]))
        cs = [g for g, geom, bb in cmodel
              if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
              and blb._point_in_geometry(pt, geom)]
        ds = [k for k, geom, bb in dmodel
              if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
              and blb._point_in_geometry(pt, geom)]
        county = cs[0] if len(cs) == 1 else None
        if county in drawn:
            inside += 1
        ok = (len(ds) == 1 and ds[0][0] == county) if county in drawn else (not ds)
        if ok:
            agree += 1
            continue
        near = any(_near_line(pt, edges[g], EDGE_M) for g in drawn)
        if near:
            edge += 1
        else:
            bad.append((round(pt[1], 5), round(pt[0], 5), county, ds))
    return inside, agree, edge, bad


def agreement(src_feats, out_feats, drawn_box, samples=AGREEMENT_SAMPLES, seed=2024):
    """The fleet's 2,000-point protocol, sampled where the districts are: only
    points inside a source district count toward the 2,000."""
    def key(f):
        return (f["properties"]["countyfips"], str(f["properties"]["district"]))
    src = [(key(f), f["geometry"], blb._bbox(f["geometry"])) for f in src_feats]
    new = [(key(f), f["geometry"], blb._bbox(f["geometry"])) for f in out_feats]
    rng = random.Random(seed)
    n = agree = overlaps = tries = 0
    while n < samples:
        tries += 1
        if tries > samples * 200:
            raise SystemExit("FAIL: could not place %d points inside the districts" % samples)
        pt = (rng.uniform(drawn_box[0], drawn_box[2]), rng.uniform(drawn_box[1], drawn_box[3]))
        o = [k for k, g, bb in src if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
             and blb._point_in_geometry(pt, g)]
        if not o:
            continue
        n += 1
        s = [k for k, g, bb in new if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
             and blb._point_in_geometry(pt, g)]
        if len(s) > 1:
            overlaps += 1
        if len(o) == 1 and len(s) == 1 and o[0] == s[0]:
            agree += 1
    return agree, n, overlaps


def _measure_census_county(c3, nm, cur, old, tracts):
    """The Census's own lines in one CENSUS_COUNTIES county: (measurements,
    the block points they were taken on, problems)."""
    ds = cur.get(c3) or {}
    if sorted(ds) != list(DISTRICTS):
        return None, None, ["the Census draws districts %s" % sorted(ds)]
    problems = []
    bad_func = [d for d, f in ds.items() if (f["properties"].get("FUNCSTAT") or "") != "N"]
    if bad_func:
        problems.append("districts %s are not nonfunctioning subdivisions — a functioning "
                        "one is a town or township, not a supervisor district" % bad_func)
    blocks = fetch_blocks(c3)
    m = measure_county(c3, ds, old.get(c3), blocks)
    if m["people"] != tracts.get(c3):
        problems.append("blocks sum to %d, tracts to %s" % (m["people"], tracts.get(c3)))
    if m["people_in_no_district"] or m["people_in_two_districts"]:
        problems.append("%d people in no district and %d in two"
                        % (m["people_in_no_district"], m["people_in_two_districts"]))
    if m["deviation_pct"] > MAX_DEVIATION_PCT:
        problems.append("the five districts differ by %.2f%% of an equal share on 2020 "
                        "population (ceiling %.0f%%) — not lines drawn on the 2020 census"
                        % (m["deviation_pct"], MAX_DEVIATION_PCT))
    if m["people_moved_from_2020_edition"] < MIN_PEOPLE_MOVED:
        problems.append("the 2026 lines move %d people from the 2020 edition's — no evidence "
                        "the county sent the Census new lines"
                        % m["people_moved_from_2020_edition"])
    print("%-10s %7d people  %5.2f%% now, %6.2f%% on the 2020 edition's lines, %6d people's "
          "district number moved"
          % (nm, m["people"], m["deviation_pct"], m["deviation_2020_edition_pct"],
             m["people_moved_from_2020_edition"]), file=sys.stderr)
    return m, blocks, problems


def _measure_county_map(c3, spec, cur, old, tracts, roster):
    """A COUNTY_SOURCES county's own lines, re-read and resolved to whole 2020
    blocks: (measurements, {district: feature}, block points, problems)."""
    layer = fetch_county_layer(spec)
    problems = source_witness_problems(spec, layer)
    raw, found = districts_of(spec, layer["features"])
    problems += found
    if sorted(raw) != list(DISTRICTS):
        return None, None, None, problems
    named, checked = names_problems(spec, raw, roster.get(STATE + c3))
    problems += named
    if sorted(cur.get(c3) or {}) != list(DISTRICTS) or sorted(old.get(c3) or {}) != list(DISTRICTS):
        return None, None, None, problems + ["the Census does not draw districts 1-5 here"]
    block_feats = fetch_block_polygons(c3)
    ds, stats, resolved = resolve_to_blocks(raw, block_feats)
    problems += resolved
    if sorted(ds) != list(DISTRICTS):
        return None, None, None, problems
    detail = []
    for f in block_feats:
        p = f["properties"]
        if int(p["POP100"]) > 0:
            detail.append((float(p["INTPTLON"]), float(p["INTPTLAT"]), int(p["POP100"]),
                           p["GEOID"], int(p["HU100"])))
    m, measured = measure_published(spec, ds, cur[c3], old[c3], detail)
    problems += measured
    if m["people"] != tracts.get(c3):
        problems.append("blocks sum to %d, tracts to %s" % (m["people"], tracts.get(c3)))
    if m["people_in_no_district"] or m["people_in_two_districts"]:
        problems.append("%d people in no district and %d in two"
                        % (m["people_in_no_district"], m["people_in_two_districts"]))
    if m["deviation_pct"] > MAX_DEVIATION_PCT:
        problems.append("the five districts differ by %.2f%% of an equal share on 2020 "
                        "population (ceiling %.0f%%) — not lines drawn on the 2020 census"
                        % (m["deviation_pct"], MAX_DEVIATION_PCT))
    if m["people_moved_from_2020_edition"] < MIN_PEOPLE_MOVED:
        problems.append("the county's lines move %d people from the Census's 2020 edition — "
                        "no evidence they are newer" % m["people_moved_from_2020_edition"])
    if m["census_people_moved_from_2020_edition"] >= MIN_PEOPLE_MOVED:
        problems.append("the Census's current lines now differ from its 2020 edition's by %d "
                        "people, so it may have received the county's new lines: compare "
                        "them with the county's and decide whether the county moves to "
                        "CENSUS_COUNTIES" % m["census_people_moved_from_2020_edition"])
    m.update(stats)
    m["layer_name"] = layer["name"]
    m["names_checked"] = checked
    print("%-10s %7d people  %5.2f%% now, %6.2f%% on the Census's lines, %6d people's "
          "district number differs; %d blocks, worst populated block %.0f%% inside one "
          "district, %d split evenly (%.3f km2)"
          % (spec["county"], m["people"], m["deviation_pct"], m["deviation_2020_edition_pct"],
             m["people_moved_from_2020_edition"], stats["blocks_read"],
             100 * stats["block_share_worst_populated"], stats["blocks_split_evenly"],
             stats["blocks_split_evenly_km2"]), file=sys.stderr)
    pts = [(x, y, n) for x, y, n, _, _ in detail]
    if spec.get("precincts"):
        pm, found = precinct_witness(spec, ds, cur[c3], pts)
        problems += found
        if pm is None:
            return None, None, None, problems
        m.update(pm)
        print("%-10s %d precincts: %d residents in a different district from these lines, "
              "%d from the Census's; %d in no precinct, %d in two"
              % (spec["county"], pm["precincts_read"], pm["precinct_people_off"],
                 pm["precinct_people_off_census"], pm["precinct_people_in_none"],
                 pm["precinct_people_in_two"]), file=sys.stderr)
    return m, ds, pts, problems


def build(args):
    names, counties_fc = county_names()
    with open(ROSTER_FILE) as fh:
        roster = json.load(fh)
    expected = drawn_lines()
    stated = dict(CENSUS_COUNTIES)
    stated.update({c: spec["county"] for c, spec in COUNTY_SOURCES.items()})
    for c3, nm in sorted(stated.items()):
        if names.get(STATE + c3) != nm + " County":
            raise SystemExit("FAIL: %s%s is %r in state-counties.json, this builder says %r"
                             % (STATE, c3, names.get(STATE + c3), nm))
    problems = roster_problems(roster, set(expected))
    if problems:
        raise SystemExit("FAIL (roster):\n  " + "\n  ".join(problems))

    name, desc = _layer_name(CURRENT)
    if name != CURRENT_NAME or CURRENT_VINTAGE not in desc:
        raise SystemExit("FAIL: %s is now %r (%r), not the %s %s — re-take the survey "
                         "before drawing a different vintage"
                         % (CURRENT, name, desc[:80], CURRENT_VINTAGE, CURRENT_NAME))

    read = datetime.date.today().isoformat()
    cur = fetch_cousubs(CURRENT, stated)
    old = fetch_cousubs(EDITION_2020, stated)
    tracts = tract_totals()
    record, lines, pts, failures = {}, {}, {}, []
    for c3 in sorted(CENSUS_COUNTIES):
        m, blocks, found = _measure_census_county(c3, CENSUS_COUNTIES[c3], cur, old, tracts)
        failures += ["%s: %s" % (CENSUS_COUNTIES[c3], p) for p in found]
        if m is not None:
            record[c3], lines[c3], pts[c3] = m, cur[c3], blocks
    for c3 in sorted(COUNTY_SOURCES):
        spec = COUNTY_SOURCES[c3]
        m, ds, blocks, found = _measure_county_map(c3, spec, cur, old, tracts, roster)
        failures += ["%s: %s" % (spec["county"], p) for p in found]
        if m is not None:
            record[c3], lines[c3], pts[c3] = m, ds, blocks
    if failures:
        raise SystemExit("FAIL:\n  " + "\n  ".join(failures))

    src_feats = []
    for geoid, kind in sorted(expected.items()):
        c3 = geoid[2:]
        for d in DISTRICTS:
            props = {"countyfips": geoid, "county": names[geoid], "district": d,
                     "label": roster[geoid]["label"], "lines": kind, "key": geoid + "-" + d}
            if kind == "county":
                props["source"] = COUNTY_SOURCES[c3]["source"]
                props["read"] = read
                aside = sum((COUNTY_SOURCES[c3].get("set_aside") or {}).values())
                if aside:
                    # the card says how many people the balance check leaves out
                    props["set_aside"] = aside
            src_feats.append({"type": "Feature", "properties": props,
                              "geometry": lines[c3][d]["geometry"]})
    with tempfile.TemporaryDirectory() as tmp:
        sp = os.path.join(tmp, "src.geojson")
        with open(sp, "w") as fh:
            json.dump({"type": "FeatureCollection", "features": src_feats}, fh)
        op = os.path.join(tmp, "out.geojson")
        blb.run_mapshaper(sp, SIMPLIFY, op)
        with open(op) as fh:
            simplified = json.load(fh)
    out_feats = simplified["features"]

    problems = structure_problems(out_feats, names, expected)
    if problems:
        raise SystemExit("FAIL (structure after simplifying):\n  " + "\n  ".join(problems))

    box = [1e9, 1e9, -1e9, -1e9]
    for f in src_feats:
        b = blb._bbox(f["geometry"])
        box = [min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])]
    agree, n, overlaps = agreement(src_feats, out_feats, box)
    if overlaps or agree < 0.995 * n:
        raise SystemExit("FAIL: %d/%d points agree with the full-precision lines and %d "
                         "fall in two districts" % (agree, n, overlaps))
    step = blb.median_source_step_m(src_feats)
    worst, over = blb.check_fidelity(src_feats, out_feats, "key")
    if over:
        raise SystemExit("FAIL: %d district(s) stray past the %.0f m ceiling (worst %.1f m): %s"
                         % (len(over), blb.FIDELITY_CEILING_M, worst, ", ".join(sorted(over)[:5])))
    print("supervisor-districts: %d/%d points agree, 0 in two districts; median source step "
          "%.2f m, worst stray %.1f m against a %.0f m ceiling"
          % (agree, n, step, worst, blb.FIDELITY_CEILING_M), file=sys.stderr)

    # What simplification costs in people: each block's district under the
    # drawn lines against the full-precision lines.
    by_county_out = {}
    for f in out_feats:
        p = f["properties"]
        by_county_out.setdefault(p["countyfips"][2:], {})[str(p["district"])] = f
    for c3, m in sorted(record.items()):
        _, _, _, drawn_answers = assign(pts[c3], by_county_out[c3])
        _, _, _, true_answers = assign(pts[c3], lines[c3])
        shifted = sum(n for (x, y, n), a, b in zip(pts[c3], drawn_answers, true_answers)
                      if a != b)
        m["simplification_people_moved"] = shifted
        if shifted > 0.01 * m["people"]:
            raise SystemExit("FAIL: simplifying moves %d of %s County's %d people across a "
                             "line" % (shifted, stated[c3], m["people"]))

    for f in out_feats:
        f["properties"].pop("key", None)
    inside, agreed, edge, bad = county_witness(out_feats, counties_fc, set(expected))
    if bad:
        raise SystemExit("FAIL: the County layer and this one disagree about the county at "
                         "%d point(s) away from any county line, e.g. %s" % (len(bad), bad[:3]))
    print("supervisor-districts: county witness %d/%d points agree (%d inside the drawn "
          "counties); %d differ within %.0f m of a county line"
          % (agreed, WITNESS_SAMPLES, inside, edge, EDGE_M), file=sys.stderr)

    fc = {"type": "FeatureCollection", "features": sorted(
        out_feats, key=lambda f: (f["properties"]["countyfips"], f["properties"]["district"]))}
    compact = json.dumps(fc, separators=(",", ":"))
    if json.loads(compact) != fc:
        raise SystemExit("FAIL: round-trip mismatch before writing")
    with open(OUT, "w") as fh:
        fh.write(compact)
    write_county_list(fc["features"])
    counties = {}
    for c3, m in sorted(record.items()):
        geoid = STATE + c3
        entry = dict(county=names[geoid], lines=expected[geoid], **m)
        if expected[geoid] == "county":
            spec = COUNTY_SOURCES[c3]
            entry["url"] = spec["url"]
            entry["read"] = read
            entry["evidence"] = {k: spec[k] for k in WITNESS_KEYS if k in spec}
        counties[geoid] = entry
    rec = {
        "_about": ("GENERATED by ms/scripts/build_ms_supervisor_districts.py. What each drawn "
                   "county's lines were measured against when the shipped file was built: "
                   "the Census's own 2020 blocks, its 2020 edition of the same county "
                   "subdivisions, and its block total against its tract total; and for a "
                   "county drawn from its own map, the map's address, the evidence it was "
                   "read with, and how cleanly it resolved to whole blocks. --check holds "
                   "the shipped file to this record."),
        "built": read,
        "source": CURRENT,
        "vintage": CURRENT_VINTAGE,
        "edition_2020": EDITION_2020,
        "max_deviation_pct": MAX_DEVIATION_PCT,
        "counties": counties,
    }
    os.makedirs(SOURCE_DIR, exist_ok=True)
    with open(RECORD, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("supervisor-districts -> %s: %d districts in %d counties (%d from the Census, %d from "
          "the county's own map), %d bytes (dp %s)"
          % (os.path.relpath(OUT, INSTANCE), len(fc["features"]), len(expected),
             len(CENSUS_COUNTIES), len(COUNTY_SOURCES), len(compact), SIMPLIFY), file=sys.stderr)


def county_list(features):
    """{GEOID: county name} for every county the districts file draws, in
    GEOID order: what ms-supervisor-counties.json must hold."""
    out = {}
    for f in features:
        p = f.get("properties") or {}
        out[p.get("countyfips")] = p.get("county")
    return dict(sorted(out.items()))


def write_county_list(features):
    listed = county_list(features)
    with open(COUNTY_LIST, "w") as fh:
        json.dump(listed, fh, indent=1)
        fh.write("\n")
    return listed


# --------------------------------------------------------------- --check ----
def record_problems(rec, expected):
    """The record's measurements, held to the gates the build applied."""
    problems = []
    recorded = rec.get("counties") or {}
    if set(recorded) != set(expected):
        problems.append("the record names counties %s, the builder %s"
                        % (sorted(recorded), sorted(expected)))
    for geoid, m in sorted(recorded.items()):
        kind = expected.get(geoid)
        if m.get("lines") != kind:
            problems.append("%s: recorded lines %r, the builder says %r"
                            % (geoid, m.get("lines"), kind))
        if m.get("deviation_pct") is None or m["deviation_pct"] > MAX_DEVIATION_PCT:
            problems.append("%s: recorded deviation %r" % (geoid, m.get("deviation_pct")))
        if (m.get("people_moved_from_2020_edition") or 0) < MIN_PEOPLE_MOVED:
            problems.append("%s: recorded %r people moved from the 2020 edition"
                            % (geoid, m.get("people_moved_from_2020_edition")))
        if (sum((m.get("district_people") or {}).values()) + (m.get("people_set_aside") or 0)
                != m.get("people")):
            problems.append("%s: district totals do not sum to the county's people" % geoid)
        if (m.get("simplification_people_moved") or 0) > 0.01 * (m.get("people") or 0):
            problems.append("%s: simplifying moved %r people" % (geoid,
                                                             m.get("simplification_people_moved")))
        if kind != "county":
            continue
        spec = COUNTY_SOURCES[geoid[2:]]
        if m.get("url") != spec["url"]:
            problems.append("%s: read from %r, COUNTY_SOURCES says %r"
                            % (geoid, m.get("url"), spec["url"]))
        evidence = {k: spec[k] for k in WITNESS_KEYS if k in spec}
        if m.get("evidence") != evidence:
            problems.append("%s: the record was built with evidence %r and COUNTY_SOURCES "
                            "now says %r — rebuild" % (geoid, m.get("evidence"), evidence))
        if m.get("layer_name") != spec["layer_name"]:
            problems.append("%s: the layer read was called %r" % (geoid, m.get("layer_name")))
        if not _ISO_DATE.match(str(m.get("read") or "")):
            problems.append("%s: read %r is not a date" % (geoid, m.get("read")))
        if (m.get("census_people_moved_from_2020_edition") or 0) >= MIN_PEOPLE_MOVED:
            problems.append("%s: the Census's own lines had changed when this was built"
                            % geoid)
        if spec.get("plan_population") and m.get("plan_population") != m.get("district_people"):
            problems.append("%s: the published population %r is not the blocks' %r"
                            % (geoid, m.get("plan_population"), m.get("district_people")))
        if m.get("people_set_aside") != sum((spec.get("set_aside") or {}).values()):
            problems.append("%s: %r people set aside, COUNTY_SOURCES names %d"
                            % (geoid, m.get("people_set_aside"),
                               sum((spec.get("set_aside") or {}).values())))
        if spec.get("names") and not m.get("names_checked"):
            problems.append("%s: no supervisor's name was compared" % geoid)
        if (m.get("block_share_worst_populated") or 0) < MIN_POPULATED_SHARE:
            problems.append("%s: a populated block was %r inside its district"
                            % (geoid, m.get("block_share_worst_populated")))
        if (m.get("blocks_split_evenly_km2") or 0) > MAX_EVEN_KM2:
            problems.append("%s: %r km2 in blocks split evenly"
                            % (geoid, m.get("blocks_split_evenly_km2")))
        if spec.get("precincts"):
            people = m.get("people") or 0
            got = [m.get(k) for k in ("precincts_read", "precinct_people_off",
                                      "precinct_people_off_census", "precinct_people_in_none",
                                      "precinct_people_in_two")]
            if not all(isinstance(v, int) and not isinstance(v, bool) for v in got):
                problems.append("%s: the record carries no precinct measurements" % geoid)
                continue
            read, off, off_census, none, two = got
            if read < len(DISTRICTS):
                problems.append("%s: %d precincts were read" % (geoid, read))
            if off > PRECINCT_MAX_OFF_SHARE * people:
                problems.append("%s: the precincts put %d residents in a different district "
                                "from the lines drawn" % (geoid, off))
            if off_census < MIN_PEOPLE_MOVED:
                problems.append("%s: the precincts put only %d residents in a different "
                                "district from the Census's lines" % (geoid, off_census))
            if none + two > PRECINCT_MAX_UNPLACED_SHARE * people:
                problems.append("%s: %d residents were in no precinct and %d in two"
                                % (geoid, none, two))
    return problems


def check():
    names, counties_fc = county_names()
    with open(ROSTER_FILE) as fh:
        roster = json.load(fh)
    with open(OUT) as fh:
        fc = json.load(fh)
    with open(RECORD) as fh:
        rec = json.load(fh)
    expected = drawn_lines()
    problems = structure_problems(fc.get("features") or [], names, expected)
    problems += roster_problems(roster, set(expected))
    for f in fc.get("features") or []:
        p = f.get("properties") or {}
        word = (roster.get(p.get("countyfips")) or {}).get("label")
        if p.get("label") != word:
            problems.append("%s district %s is labelled %r and the directory says %r"
                            % (p.get("countyfips"), p.get("district"), p.get("label"), word))
        m = (rec.get("counties") or {}).get(p.get("countyfips")) or {}
        if p.get("lines") == "county" and p.get("read") != m.get("read"):
            problems.append("%s district %s says it was read on %r and the record %r"
                            % (p.get("countyfips"), p.get("district"), p.get("read"),
                               m.get("read")))
    problems += record_problems(rec, expected)
    # The app's coverage test reads the list, not the districts, so a list
    # naming a county the districts file does not draw shows the layer with
    # nothing to answer, and one missing a county hides districts that exist.
    try:
        with open(COUNTY_LIST) as fh:
            listed = json.load(fh)
    except (OSError, ValueError) as e:
        listed = None
        problems.append("ms-supervisor-counties.json does not read: %s" % e)
    drawn = county_list(fc.get("features") or [])
    if listed is not None and listed != drawn:
        if not isinstance(listed, dict):
            listed = {}
        extra = sorted(set(listed.items()) - set(drawn.items()))
        missing = sorted(set(drawn.items()) - set(listed.items()))
        problems.append("ms-supervisor-counties.json differs from the districts file: it "
                        "lists %s that the file does not draw and leaves out %s; rebuild"
                        % (extra or "nothing", missing or "nothing"))
    # The card names the edition in words ("January 1, 2026 edition"), so a
    # rebuild from a new vintage that left the card alone would tell a reader
    # the wrong edition. Both are held to the record here.
    if rec.get("vintage") != CURRENT_VINTAGE:
        problems.append("the record was built from the %r layer and CURRENT_VINTAGE is %r"
                        % (rec.get("vintage"), CURRENT_VINTAGE))
    with open(os.path.join(INSTANCE, "index.html"), encoding="utf-8") as fh:
        if "(%s edition)" % rec.get("vintage") not in fh.read():
            problems.append("ms/index.html's supervisor card does not name the %s edition "
                            "the shipped file was built from" % rec.get("vintage"))
    inside, agreed, edge, bad = county_witness(fc.get("features") or [], counties_fc,
                                               set(expected))
    if bad:
        problems.append("the County layer and this one disagree about the county at %d "
                        "point(s) away from any county line, e.g. %s" % (len(bad), bad[:3]))
    if problems:
        print("FAIL: ms-supervisor-districts.json\n  " + "\n  ".join(problems))
        return 1
    recorded = rec["counties"]
    devs = sorted(m["deviation_pct"] for m in recorded.values())
    print("OK: ms-supervisor-districts.json draws %d districts in %d counties (%d from the "
          "Census, %d from the county's own map), each numbered 1-5 and named in the "
          "directory; recorded deviations %.2f%%-%.2f%% on 2020 population (ceiling %.0f%%, "
          "measured at build, not re-measured here); county witness %d/%d agree, %d differ "
          "within %.0f m of a county line"
          % (len(fc["features"]), len(expected), len(CENSUS_COUNTIES), len(COUNTY_SOURCES),
             devs[0], devs[-1], MAX_DEVIATION_PCT, agreed, WITNESS_SAMPLES, edge, EDGE_M))
    return 0


# -------------------------------------------------------------- --survey ----
def survey():
    """Every county's two measurements, printed; writes nothing. It also says
    how old the lines are where the Census still carries its 2020 edition: for
    each county, the residents whose district the 2020 edition and the 2010
    edition (the lines the Census held on January 1, 2010) number differently,
    and how far apart the 2010 edition's districts were on the 2010 census's
    own count of each (its POP100)."""
    names, _ = county_names()
    allc = sorted(g[2:] for g in names)
    cur = fetch_cousubs(CURRENT, allc)
    old = fetch_cousubs(EDITION_2020, allc)
    older = fetch_cousubs(EDITION_2010, allc, ",POP100")
    rows, stale, total = [], [], 0
    for c3 in allc:
        if sorted(cur.get(c3) or {}) != list(DISTRICTS):
            rows.append((c3, "the Census draws %s" % sorted(cur.get(c3) or {})))
            continue
        blocks = fetch_blocks(c3)
        m = measure_county(c3, cur[c3], old.get(c3), blocks)
        total += m["people"]
        current = (m["deviation_pct"] <= MAX_DEVIATION_PCT
                   and m["people_moved_from_2020_edition"] >= MIN_PEOPLE_MOVED)
        verdict = ("CURRENT" if current else
                   "unchanged, balanced" if m["deviation_pct"] <= MAX_DEVIATION_PCT else
                   "changed, unbalanced" if m["people_moved_from_2020_edition"] >= MIN_PEOPLE_MOVED
                   else "stale")
        listed = ("listed" if c3 in CENSUS_COUNTIES else
                  "the county's own map" if c3 in COUNTY_SOURCES else
                  "NOT LISTED" if current else "")
        then10 = older.get(c3) or {}
        if old.get(c3) and sorted(then10) == list(DISTRICTS):
            a20 = assign(blocks, old[c3])[3]
            a10 = assign(blocks, then10)[3]
            differ = sum(n for (x, y, n), a, b in zip(blocks, a20, a10) if a != b)
            dev10 = deviation_pct({d: int(f["properties"].get("POP100") or 0)
                                   for d, f in then10.items()})
            older_text = "%6d differ from 2010 edition, which measured %6.2f%% on 2010 counts" % (
                differ, dev10)
        else:
            differ = dev10 = None
            older_text = "2010 edition draws %s" % sorted(then10)
        if verdict == "stale":
            stale.append((c3, m["people"], differ, dev10))
        rows.append((c3, "%-22s %6.2f%% now  %6.2f%% 2020 edition  %6d moved  %-20s %s  %s"
                     % (names[STATE + c3], m["deviation_pct"], m["deviation_2020_edition_pct"],
                        m["people_moved_from_2020_edition"], verdict, older_text, listed)))
    for c3, line in rows:
        print(c3, line)
    same = [r for r in stale if r[2] == 0]
    unbalanced = [r for r in same if r[3] > MAX_DEVIATION_PCT]
    print("%d counties carry the Census's 2020 edition and measure more than %g%% on the 2020 "
          "blocks. In %d of them the 2010 edition puts every 2020 resident in the same district, "
          "and %d of those %d measured more than %g%% on the 2010 census's own counts; those %d "
          "held %d of the state's %d residents in 2020."
          % (len(stale), MAX_DEVIATION_PCT, len(same), len(unbalanced), len(same),
             MAX_DEVIATION_PCT, len(unbalanced), sum(r[1] for r in unbalanced), total))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    ap.add_argument("--survey", action="store_true", help="measure all 82 counties, write nothing")
    args = ap.parse_args()
    if args.check:
        return check()
    if args.survey:
        return survey()
    build(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
