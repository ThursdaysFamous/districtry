#!/usr/bin/env python3
"""
Build la/data/app/la-city-wards.json: the council districts of the Louisiana
cities whose council the City, Town or Village card names
(data/app/la-municipal-officials.json) and whose current district lines are
confirmed, drawn by the `city-ward` layer in la/index.html.

WHICH CITIES. Louisiana has 13 cities of 25,000 people or more on the 2020
census (docs/expected-governments.json), and every one of them elects council
members by district. They fall into three groups, each stated below and held
to that list by --check:

  CITIES        four drawn here, each from the city's own published district
                map, confirmed as the plan in force: Lafayette, Bossier City,
                Central and Slidell.
  PARISH_DRAWN  three whose council is their parish's governing body, so
                their districts are the parish's and the Police Jury or
                Council District layer draws them
                (la/scripts/build_la_parish_districts.py): New Orleans (the
                New Orleans City Council, Orleans Parish), Baton Rouge (the
                Metropolitan Council, East Baton Rouge Parish) and Houma (the
                Terrebonne Parish Council). The Secretary of State's list of
                municipal officials names none of the three, because it names
                these bodies as the parishes'.
  NOT_DRAWN     six whose current lines are not established or cannot be
                drawn here, each for a measured reason:

  Monroe        the only district layer found was last edited on June 2, 2022,
                before the council adopted new districts (Ordinance 12,147,
                December 27, 2022); on the 2020 census its districts are 35.5%
                apart and on the 2010 census 11.3%, so it is the old plan. A
                March 2026 report (KEDM) describes a further change between
                Districts 1 and 4.
  Kenner        its district layer is 11.3% apart on the 2020 census and 6.4%
                on the 2010 census, 788 people inside the city on the 2020
                census are in no district on it, and no plan adopted on the
                2020 census was found.
  Alexandria    the council redrew three districts in April 2024, a mayoral
                veto followed and an attempt to override it failed in December
                2025 (KALB, December 18, 2025), so which plan is in force is not
                established, and no district layer was found.
  New Iberia    the only district layer found is the 2012 plan's.
  Lake Charles  the council adopted Plan B in July 2022, and it is published
                as a PDF only.
  Shreveport    the one district layer found (the City's, on the regional GIS)
                carries a notice that no one may copy or distribute it except
                under a written agreement with the Regional Geographic
                Information System and the Northwest Louisiana Council of
                Governments, so it is not drawn without one.

HOW A PLAN IS CONFIRMED. A district plan is drawn on one census, and on that
census its districts hold nearly equal numbers of people; on the census
before, the same lines are unequal, because people moved in the ten years
between. So each city's layer is counted on both censuses' blocks (each
populated block's internal point inside the layer's own districts), and a
layer that balances on the 2020 census and not on the 2010 census is lines
drawn after the 2020 census. Measured 2026-10-21, as the spread between the
largest and smallest district as a share of an equal one:

                 2010 census      2020 census
                 (the layer as    (cut at the
                 served)          city's limits)
  Lafayette        16.2%          10.7%
  Bossier City     19.3%          10.6% (the 2022 plan's own figures: 8.4%)
  Central          22.4%           6.5%
  Slidell          26.1%           8.4%

Beside that, each city's own pages say these are its current districts:

  Lafayette     the Lafayette City Council's page (the councils' page of the
                Lafayette Consolidated Government) links Find Your Council
                Member, a map whose district layer is this one, named
                LCG.LafayetteCityDistricts; LCG's own copy of the plan
                (LCG_CityCouncilDistricts_2023) cuts at the city's limits to
                the same districts. The council adopted the districts on June
                21, 2022, drawn on the 2020 census (KATC; The Advocate).
  Bossier City  the city's Public Map Portal page links Find Your Councilman,
                an app the city describes as the one used to find council
                members for an address, whose map's layer is this one, named
                Council_Districts. The city's 2022 plan, published as a layer
                named Districts with its own population figures (13,118,
                12,070, 12,268, 12,436 and 12,809: 62,701, Bossier City's 2020
                count), matches the 2020 census's people inside these lines in
                Districts 1 to 4; District 5 holds 600 more, all in one block
                outside the city on the 2020 census's map and inside it on
                today's (OWN_POPULATION).
  Central       the city's City Council page shows this map under Current
                Council District Map, described as the council districts
                "remapped per 2020 Census Data; November 2022 election,
                effective January 2023"; the layer is named Council Districts
                2023 and its own population figures sum to 29,565, Central's
                2020 count. They match the 2020 census's people inside its
                lines in three districts of five; Districts 1 and 3 differ by
                29 people each way (OWN_POPULATION). East Baton Rouge Parish's
                copy of the same districts puts every 2020 resident in the
                same district. The city's 2022 maps of the plan, one per
                district in the 2022 Council Districts Maps folder on its
                website, print a table titled Plan 4 Demographics whose
                Districts 1 and 3 differ from this map's by one block of 174
                people (OWN_POPULATION); both the city's current map and the
                parish's copy put that block in District 3.
  Slidell       the city's City Council page shows this map under its Council
                Districts tab, and its layer is named Slidell Council
                Districts. The page says the council has nine members, seven
                elected by district and two at large. No adoption date was
                found.

THE LINES BETWEEN DISTRICTS ARE EACH CITY'S OWN PUBLISHED MAP, never redrawn.
Only the district field is requested from each layer, plus the population
field the two cities' own figures are read from (Central's, and Bossier City's
plan layer, read without its lines); several of these layers also carry
member names, photographs, telephone numbers or population by race, and none
of that is asked for.

THE CITY'S OUTER EDGE IS THE CENSUS BUREAU'S MAP OF THE CITY (TIGERweb's
current incorporated place, the layer the City, Town or Village card reads),
because the district layers run past the cities' limits and the cities' own
counts end at them, as Mississippi's ward builder found
(ms/scripts/build_ms_city_wards.py). Cut there, the district card never names
a district of a city the City card says a point is not in.

THE GATES, ASKED OF EVERY CITY ON EVERY BUILD
---------------------------------------------
1. THE DISTRICTS ARE THE ROSTER'S. The layer's districts must be exactly the
   district seats la-municipal-officials.json names for the city ("District
   1".."District 5", "District A".."District G").
2. THE WITNESS STILL SAYS WHAT IT SAID. Each entry pins the layer's own name,
   and Bossier City's the name of its plan layer. A renamed layer is a
   redistricting until a person has read it, so the build stops.
3. THE PEOPLE ARE PINNED. Each district's people on the 2020 census, counted
   by every populated block's internal point inside the district as cut at
   the city's limits, are pinned per district (`people`), and so are the
   people the cut takes away (`outside`) and the people inside the limits
   whom no district holds (`gap`). A line that moves moves people, so a city
   that redraws its districts stops the build here even with the same number
   of districts, and so does a Census line that moves. The spread prints on
   every run.
4. THE CITY'S OWN COUNT, where it publishes one, must equal those people
   district by district, except a difference recorded with its reason
   (OWN_POPULATION).
5. TILING against the same Census place: the districts' area over the place's
   must sit near 1, and the ground inside the place that no district holds
   has per-city ceilings at about 2.5 times what was measured on 2026-10-21.
6. NO TWO CITIES CLAIM ONE PLACE, in the cut districts or the drawn file.
7. SIMPLIFICATION KEEPS EVERY ANSWER. All four cities are simplified in one
   shared topology (Douglas-Peucker, interval 3 m), so a line two districts
   share is drawn once. Then every populated 2020 block gets the same
   districts from the drawn file as from the cut districts, the true line
   strays no more than FIDELITY_MAX_M from the drawn one, no district loses a
   ring, 4,000 seeded points per city agree at 99.5% or better, and the
   drawing adds no overlap at those points. An exception is a declaration in
   ACCEPTED_DROPPED_PARTS, ACCEPTED_MOVED_BLOCKS or ACCEPTED_OVERLAPS, checked
   on every build. One was needed on 2026-10-21: a sliver of Lafayette's
   District 3 of about 60 square centimetres, which the drawing drops and
   which nobody lives in. Without it, the true line strays at most 2.99 m from
   the drawn one.

Usage:
    python3 la/scripts/build_la_city_wards.py            # fetch, check, write
    python3 la/scripts/build_la_city_wards.py --check    # offline, on what ships

The --check also holds three hand-written statements to CITIES, PARISH_DRAWN
and NOT_DRAWN: the City Council District card's empty state and the City
card's list of drawn cities (LA_WARD_CITIES) in la/index.html, and the layer's
"Where it applies" and "What it answers" on the sources page (the worksheet's
`applies` and `answers`), so a city drawn or dropped here fails the check
until all of them say so.

WHAT WAS READ IS RECORDED. Nothing runs this build on a schedule, and a city
can redraw its districts inside a layer whose name stays the same, so the
build writes data/source/la-city-wards.source.json: for every city, the
layer's address and name, the date the layer gives for its last edit, and a
SHA-256 of the lines the layer and the Census Bureau's map of the city served
(lines_sha256), and for Bossier City a SHA-256 of its plan layer's figures.
The monthly source check (validate_sources.py) asks the same questions again,
the same way (layer_params, place_params, plan_params), and reports any city
whose lines moved; the --check holds the record to CITIES.
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
import time
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(_HERE)
REPO_ROOT = os.path.dirname(INSTANCE)
# APPENDED, not inserted: the shared scripts/ directory has a
# build_legislative_boundaries.py of its own (Illinois's), and this file must
# import the one beside it.
sys.path.append(os.path.join(REPO_ROOT, "scripts"))
from scraper_common import require_robots_allowed  # noqa: E402  (FLEET_SHARED)

sys.path.insert(0, _HERE)
import build_legislative_boundaries as blb  # noqa: E402  (same instance tree)
import build_la_parish_districts as pd  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(blb.__file__)) == _HERE, blb.__file__

APP_DATA_DIR = os.path.join(INSTANCE, "data", "app")
OUT = os.path.join(APP_DATA_DIR, "la-city-wards.json")
SOURCE_RECORD = os.path.join(INSTANCE, "data", "source", "la-city-wards.source.json")
ROSTER_FILE = os.path.join(APP_DATA_DIR, "la-municipal-officials.json")
PARISH_LIST = os.path.join(APP_DATA_DIR, "la-parish-district-parishes.json")
COUNTIES_FILE = os.path.join(APP_DATA_DIR, "state-counties.json")
EXPECTED_FILE = os.path.join(REPO_ROOT, "docs", "expected-governments.json")

USER_AGENT = "districtry/1.0 (+https://districtry.com/la/)"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}
LABEL = "la-build-la-city-wards"
TIGERWEB_PLACE = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                  "Places_CouSub_ConCity_SubMCD/MapServer/4")
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
# A part of two cities' districts this large or larger is ground both claim.
OVERLAP_MIN_M2 = 0.01
# A declaration matches the part or block it names when its point is within
# this distance and, for an area, the area within this share.
DECLARED_WITHIN_M = 1.0
DECLARED_AREA_SHARE = 0.10


def _num(v):
    """A district number as a layer serves it, a string or a number: '3' or
    3 or 3.0 -> '3'."""
    s = str(v).strip()
    f = float(s)
    if f != int(f) or f < 1:
        raise ValueError("not a district number: %r" % (v,))
    return str(int(f))


def _order(d):
    """Districts in their own order: numbers by value, letters by letter."""
    return (0, int(d), "") if str(d).isdigit() else (1, 0, str(d))


# Each entry: the city's Census id and name, the layer, the where clause, the
# field carrying the district and how to read it, the page a reader can open,
# the sentence the card prints about where the lines come from, the witness
# the build re-reads, the field or plan layer the city's own figures come
# from, each district's people on the 2020 census as cut at the city's limits
# (measured 2026-10-21), and the two tiling ceilings (uncovered sq mi, largest
# uncovered part m2), set at about 2.5 times what was measured.
CITIES = [
    dict(geoid="2240735", city="Lafayette",
         layer="https://maps.lafayettela.gov/arcgis/rest/services/BaseLayers/"
               "LCG_LafayetteCityDistricts/FeatureServer/0",
         where="1=1", field="DST_NUM", read=_num,
         page="https://www.lafayettela.gov/your-government/city-and-parish-councils/",
         source="the Lafayette Consolidated Government's map of the Lafayette City "
                "Council's districts, the one its Find Your Council Member map shows, "
                "adopted on June 21, 2022",
         witness={"layer_name": "LCG.LafayetteCityDistricts"},
         own=None,
         people={"1": 22776, "2": 24948, "3": 25341, "4": 25376, "5": 23055},
         outside=199, gap=0,
         # measured 0.1095 sq mi in no district, the largest part 42,961 m2
         max_sqmi=0.27, max_part_m2=107000),
    dict(geoid="2208920", city="Bossier City",
         layer="https://services1.arcgis.com/jh7pbmmfSzUSNziy/arcgis/rest/services/"
               "Council_Districts/FeatureServer/7",
         where="1=1", field="DISTRICT", read=_num,
         page="https://bossiercity.org/558/Public-Map-Portal",
         source="the City of Bossier City's map of its council districts, the one its "
                "Find Your Councilman map shows",
         witness={"layer_name": "Council_Districts"},
         own=None,
         # The city's 2022 plan, read for its own figures and not its lines.
         plan=dict(layer="https://services1.arcgis.com/jh7pbmmfSzUSNziy/arcgis/rest/"
                         "services/Council_Map/FeatureServer/0",
                   layer_name="Districts", field="DISTRICT", read=_num, own="POPULATION"),
         people={"1": 13118, "2": 12070, "3": 12268, "4": 12436, "5": 13409},
         outside=0, gap=0,
         # measured 0.0442 sq mi in no district, the largest part 24,824 m2
         max_sqmi=0.11, max_part_m2=62000),
    dict(geoid="2213960", city="Central",
         layer="https://services5.arcgis.com/wATr0UsvWt8807Pv/arcgis/rest/services/"
               "COC_COUNCIL_DISTRICTS/FeatureServer/139",
         where="1=1", field="DISTRICT", read=_num,
         page="https://www.central-la.gov/page/city-council",
         source="the City of Central's map of its council districts, drawn on the 2020 "
                "census for the November 2022 election, the one its City Council page "
                "shows",
         witness={"layer_name": "Council Districts 2023"},
         own="POPULATION",
         people={"1": 5881, "2": 6030, "3": 5923, "4": 5673, "5": 6058},
         outside=13, gap=0,
         # measured 0.0128 sq mi in no district, the largest part 12,613 m2
         max_sqmi=0.032, max_part_m2=32000),
    dict(geoid="2270805", city="Slidell",
         layer="https://services7.arcgis.com/NbYh5dTYeFoc2wlO/arcgis/rest/services/"
               "Slidell_Council_Districts_Map_WFL1/FeatureServer/0",
         where="1=1", field="NAME", read=pd._letter,
         # Two features with a blank name lie outside the city and hold nobody
         # (measured 2026-10-21); they are set aside, and their count is pinned.
         skip={"NAME": " "}, skip_count=2,
         page="https://myslidell.com/government/slidell-city-council/",
         source="the City of Slidell's map of its council districts, the one the "
                "Council Districts tab of its City Council page shows",
         witness={"layer_name": "Slidell Council Districts"},
         own=None,
         people={"A": 4091, "B": 4252, "C": 4002, "D": 4162, "E": 3923, "F": 3909,
                 "G": 4117},
         # The 3 people in no district are census block 221030410023043, inside
         # the city on the Census Bureau's map, in 8,751 m2 of it around
         # 30.2722,-89.7577 that the city's map leaves out of every district,
         # its census point 8 m from District E (measured 2026-10-21).
         outside=39, gap=3,
         # measured 0.1472 sq mi in no district, the largest part 33,291 m2
         max_sqmi=0.37, max_part_m2=83000),
]

# The cities whose council is their parish's governing body, by Census id: the
# parish whose districts the Police Jury or Council District layer draws.
PARISH_DRAWN = {
    "2255000": ("New Orleans", "22071"),
    "2205000": ("Baton Rouge", "22033"),
    "2236255": ("Houma", "22109"),
}

NOT_DRAWN = {
    "2251410": "Monroe: the only district layer found is the plan from before the "
               "council's December 2022 ordinance",
    "2239475": "Kenner: its district layer balances on the 2010 census and not the "
               "2020 census, and no plan adopted on the 2020 census was found",
    "2200975": "Alexandria: which plan is in force after the 2024 redraw is not "
               "established, and no district layer was found",
    "2254035": "New Iberia: the only district layer found is the 2012 plan's",
    "2241155": "Lake Charles: its 2022 plan is published as a PDF only",
    "2270000": "Shreveport: its district layer may not be copied without a written "
               "agreement with the regional GIS that publishes it",
}

# Where a city's own population figure for a district differs from the people
# the 2020 census puts inside that district as cut at the city's limits: the
# difference (census minus the city's) and why, re-measured on every build.
OWN_POPULATION = {
    "2208920": {
        "5": (600, "census block 220150111193005, 600 people, lies outside Bossier City "
                   "on the 2020 census's map of the city and inside it on today's; the "
                   "city's current map puts it in District 5, and its 2022 plan, drawn "
                   "on the city as it was in 2020, in no district"),
    },
    "2213960": {
        "1": (-29, "the layer's own figures count 29 more people in District 1 than the "
                   "2020 census puts inside its lines, and 29 fewer in District 3. No "
                   "populated block crosses the line between the two by more than 0.1% "
                   "of its area, and no block or set of blocks along it holds 29 people, "
                   "so the difference is not a block the line cuts; where it comes from "
                   "was not established. The city's own 2022 maps of the plan (Plan 4) "
                   "give a third pair, 6,055 and 5,749: the census's people inside these "
                   "lines with block 220330044012000, 174 people, in District 1 instead "
                   "of District 3. East Baton Rouge Parish's copy of the districts puts "
                   "that block in District 3, as this map does (measured 2026-10-21)"),
        "3": (29, "the same 29 people as District 1's difference"),
    },
}

# What the drawn file answers differently from the cut districts, each checked
# on every build like Mississippi's (ms/scripts/build_ms_city_wards.py). One
# part was needed on 2026-10-21, and no block or overlap.
ACCEPTED_DROPPED_PARTS = [
    dict(city="Lafayette", district="3", lat=30.178674, lng=-92.033240, m2=0.0059, verts=3,
         before=["3"], after=[],
         why="a three-cornered sliver of District 3 of about 60 square centimetres, where "
             "the city's line between Districts 3 and 4 meets the Census Bureau's map of "
             "the city's limits, 43.5 m from the rest of the district: the ground between "
             "them is in District 3 on the city's map and outside the city on the Census "
             "Bureau's, and the ground 3 m and 10 m around it is in District 4 or outside "
             "the city. No census point is inside it",
         date="2026-10-21"),
]
ACCEPTED_MOVED_BLOCKS = {}
ACCEPTED_OVERLAPS = []

# Every drawn district's card says where its line comes from: the city's map,
# then the edge it is cut at.
EDGE = ", ending at the city's limits as the Census Bureau maps them"

PROPS = ("geoid", "city", "district", "seat", "source", "sourceUrl")


def fail(msg):
    raise SystemExit("build-la-city-wards: FATAL: %s" % msg)


# ---------------------------------------------------------------- fetching --
_ROBOTS = {}
_LAST = {}


def _fetch_json(url, params=None):
    """GET one url as this builder's client, after asking its host's robots.txt
    about that url's own path, waiting a second between requests to one host."""
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname
    if (host, parts.path) not in _ROBOTS:
        why = require_robots_allowed(url, USER_AGENT, headers=HEADERS, label=LABEL)
        _ROBOTS[(host, parts.path)] = why
        print("robots.txt %s%s: %s" % (host, parts.path, why), file=sys.stderr)
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    for attempt in range(4):
        wait = MIN_DELAY_S - (time.time() - _LAST.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(full, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=180) as resp:
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
    """The query the build sends a city's district layer, with only the fields
    it reads. The monthly source check sends the same one, so the two read the
    same lines."""
    fields = [c["field"]] + ([c["own"]] if c.get("own") else [])
    return {"where": c["where"], "outFields": ",".join(fields), "returnGeometry": "true",
            "outSR": "4326", "geometryPrecision": "6", "f": "json"}


def place_params(c):
    """The query for the Census Bureau's map of the city, shared the same way."""
    return {"where": "GEOID='%s'" % c["geoid"], "outFields": "GEOID,BASENAME",
            "returnGeometry": "true", "outSR": "4326", "geometryPrecision": "6", "f": "json"}


def plan_params(plan):
    """The query for a city's plan layer: its district and population fields,
    and no lines."""
    return {"where": "1=1", "outFields": "%s,%s" % (plan["field"], plan["own"]),
            "returnGeometry": "false", "f": "json"}


def _skipped(attrs, c):
    skip = c.get("skip") or {}
    return bool(skip) and all(attrs.get(k) == v for k, v in skip.items())


def lines_sha256(fc, c=None):
    """A SHA-256 of the lines in one answer to layer_params or place_params:
    every ring as served, at the six decimals asked for, each feature keyed by
    its district read this builder's way (the Census place by nothing), with
    the features and each feature's rings put in one order. The build records
    it for every city's layer and place (SOURCE_RECORD), and the monthly
    source check asks the same two questions and compares, because a city can
    move its lines inside a layer whose name stays the same."""
    rows = []
    for f in fc.get("features") or []:
        a = f.get("attributes") or {}
        if c and _skipped(a, c):
            continue
        key = c["read"](a.get(c["field"])) if c else ""
        rings = sorted([[round(p[0], 6), round(p[1], 6)] for p in ring]
                       for ring in (f.get("geometry") or {}).get("rings") or [])
        rows.append([key, rings])
    rows.sort()
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode("ascii")).hexdigest()


def plan_rows(answer, plan):
    """{district: people} from one answer to plan_params."""
    out = {}
    for f in answer.get("features") or []:
        a = f.get("attributes") or {}
        d = plan["read"](a.get(plan["field"]))
        v = a.get(plan["own"])
        if v is None:
            fail("the plan layer gives no %s for district %s" % (plan["own"], d))
        out[d] = out.get(d, 0) + int(round(float(v)))
    return out


def plan_sha256(answer, plan):
    """A SHA-256 of a plan layer's figures, as plan_rows reads them."""
    rows = sorted(plan_rows(answer, plan).items())
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode("ascii")).hexdigest()


def fetch_layer(c):
    """(layer meta, [GeoJSON-shaped features], the answer as served)."""
    meta = _fetch_json(c["layer"], {"f": "json"})
    fc = _fetch_json(c["layer"] + "/query", layer_params(c))
    if fc.get("exceededTransferLimit"):
        fail("%s: the layer hit its transfer limit" % c["city"])
    return meta, pd.esri_features(fc, c["layer"], c["field"]), fc


def fetch_place(c):
    """(the Census place as a GeoJSON-shaped feature, the answer as served)."""
    fc = _fetch_json(TIGERWEB_PLACE + "/query", place_params(c))
    feats = pd.esri_features(fc, TIGERWEB_PLACE, "GEOID")
    if len(feats) != 1:
        fail("%s: TIGERweb returned %d places for GEOID %s" % (c["city"], len(feats), c["geoid"]))
    name = feats[0]["properties"].get("BASENAME")
    if name != c["city"]:
        fail("%s: GEOID %s is %r on TIGERweb" % (c["city"], c["geoid"], name))
    return feats[0], fc


def fetch_plan(c):
    """({district: people} as the city's plan layer gives them, its name, a
    fingerprint of the figures), or (None, None, None) for a city with none."""
    plan = c.get("plan")
    if not plan:
        return None, None, None
    meta = _fetch_json(plan["layer"], {"f": "json"})
    if meta.get("name") != plan["layer_name"]:
        fail("%s: the plan layer is now named %r, not %r. A renamed plan layer is a new "
             "plan until a person has read it." % (c["city"], meta.get("name"),
                                                   plan["layer_name"]))
    answer = _fetch_json(plan["layer"] + "/query", plan_params(plan))
    return plan_rows(answer, plan), meta.get("name"), plan_sha256(answer, plan)


# ------------------------------------------------------------- the checks --
def roster_districts():
    """{geoid: [district keys]} from the city roster's "District X" seats, and
    the roster."""
    with open(ROSTER_FILE, encoding="utf-8") as fh:
        roster = json.load(fh)
    out = {}
    for geoid, city in roster.items():
        keys = []
        for seat in city.get("seats") or []:
            m = re.match(r"^District ([0-9]+|[A-Z])$", str(seat.get("seat") or ""))
            if m:
                keys.append(m.group(1))
        out[geoid] = sorted(keys, key=_order)
    return out, roster


def _date(ms):
    if ms is None:
        return None
    return datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc).strftime("%Y-%m-%d")


def districts_of(c, meta, feats, want):
    """{district: shapely geometry} at the layer's full precision, after the
    district set and the witness are checked."""
    from shapely.ops import unary_union
    kept = []
    for f in feats:
        if _skipped(f["properties"], c):
            continue
        if not f.get("geometry"):
            fail("%s: a feature has no geometry (%r)" % (c["city"], f["properties"].get(c["field"])))
        kept.append(f)
    if c.get("skip") and len(feats) - len(kept) != c["skip_count"]:
        fail("%s: expected %d features matching %r to set aside, found %d"
             % (c["city"], c["skip_count"], c["skip"], len(feats) - len(kept)))
    groups = {}
    for f in kept:
        try:
            d = c["read"](f["properties"][c["field"]])
        except (TypeError, ValueError):
            fail("%s: a district this builder does not read: %r"
                 % (c["city"], f["properties"].get(c["field"])))
        groups.setdefault(d, []).append(
            pd.checked_shape(f["geometry"], "%s district %s" % (c["city"], d)))
    got = sorted(groups, key=_order)
    if got != want:
        fail("%s: the layer holds districts %s and the city roster names seats for "
             "districts %s. A different set is a redistricting or the layer changing "
             "shape, and both need reading before anything ships." % (c["city"], got, want))
    name = meta.get("name")
    if name != c["witness"]["layer_name"]:
        fail("%s: the layer is now named %r, not %r. A renamed district layer is a new "
             "plan until a person has read it." % (c["city"], name, c["witness"]["layer_name"]))
    return {d: unary_union(gs) for d, gs in groups.items()}, kept


def own_counts(c, kept, plan):
    """{district: people} as the city's own figures count them, or None."""
    if plan is not None:
        return plan
    if not c.get("own"):
        return None
    out = {}
    for f in kept:
        d = c["read"](f["properties"][c["field"]])
        v = f["properties"].get(c["own"])
        if v is None:
            fail("%s district %s: the layer no longer gives %s" % (c["city"], d, c["own"]))
        out[d] = out.get(d, 0) + int(round(float(v)))
    return out


def cut(c, districts, place, lat0):
    """Each district cut at the city's limits as the Census place draws them."""
    out = {}
    for d, g in sorted(districts.items(), key=lambda kv: _order(kv[0])):
        out[d] = pd.polygonal(g.intersection(place), "%s district %s cut at the city's limits"
                              % (c["city"], d))
        lost = _m2(g.difference(place), lat0)
        if lost > 1.0:
            print("  district %s: %.0f m2 of the city's map lies outside the Census place"
                  % (d, lost), file=sys.stderr)
    return out


def _lat0(geoms):
    ys = [g.bounds[1] for g in geoms] + [g.bounds[3] for g in geoms]
    return (min(ys) + max(ys)) / 2.0


def _m2(g, lat0):
    """Area in square metres by a local plane at lat0."""
    return g.area * 111320.0 * math.cos(math.radians(lat0)) * 110540.0


def _perimeter_m(g, lat0):
    from shapely.affinity import scale
    return scale(g, xfact=111320.0 * math.cos(math.radians(lat0)), yfact=110540.0,
                 origin=(0, 0)).length


def tiling(c, districts, place, lat0):
    """The districts' area over the Census place's, and the ground inside the
    place that no district holds. Who lives on that ground is people()'s
    `gap`."""
    from shapely.ops import unary_union
    union = unary_union(list(districts.values()))
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
        measured.append((a, pp, p))
    total_sqmi = sum(a for a, _, _ in measured) / 2.58999e6
    largest = max((a for a, _, _ in measured), default=0.0)
    compact = [(a, p) for a, pp, p in measured
               if a >= COMPACTNESS_MIN_AREA_M2 and pp > COMPACTNESS_CEILING]
    print("  tiling: districts/place area %.4f; %.4f sq mi of the place in no district, in %d "
          "parts, largest %.0f m2; %d compact parts of %.0f m2 in all"
          % (ratio, total_sqmi, len(measured), largest, len(compact),
             sum(a for a, _ in compact)), file=sys.stderr)
    for a, p in sorted(compact, key=lambda t: -t[0]):
        rp = p.representative_point()
        print("    compact part of %.0f m2 at %.6f,%.6f" % (a, rp.y, rp.x), file=sys.stderr)
    problems = []
    if not IDENTITY_RATIO_LO <= ratio <= IDENTITY_RATIO_HI:
        problems.append("the districts' area is %.3f of the Census place's; outside %.2f-%.2f "
                        "this is not the same city" % (ratio, IDENTITY_RATIO_LO, IDENTITY_RATIO_HI))
    if c["max_sqmi"] is None:
        problems.append("no tiling ceiling is pinned yet (measured %.4f sq mi, largest part "
                        "%.0f m2)" % (total_sqmi, largest))
    elif total_sqmi > c["max_sqmi"] or largest > c["max_part_m2"]:
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
    """[(lng, lat, people, GEOID)] for every populated 2020 block in the
    parish."""
    if c3 not in _BLOCKS:
        _BLOCKS[c3] = pd.fetch_blocks(c3, detail=True)
    return _BLOCKS[c3]


def people(c, raw, districts, place):
    """{district: people} on the 2020 census by block internal point, inside the
    districts as cut at the city's limits; with the people the cut takes away
    (inside the city's map, outside the Census place) and the people inside
    the place whom no district holds. Also the blocks used, for the drawn-file
    check."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    from shapely.prepared import prep
    raw_union = unary_union(list(raw.values()))
    # Only the blocks inside the city's own envelope, widened by about 100 m:
    # a drawn district keeps a subset of the cut district's vertices, so it
    # cannot reach a block outside that envelope either.
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
    for x, y, n, geoid in blocks:
        pt = Point(x, y)
        hits = [d for d, g in ready.items() if g.contains(pt)]
        if len(hits) > 1:
            fail("%s: %d people live in a block the city's map puts in two districts"
                 % (c["city"], n))
        if hits:
            pop[hits[0]] += n
        elif in_place.contains(pt):
            gap += n
            gap_blocks.append((geoid, n, y, x))
        elif in_raw.contains(pt):
            outside += n
    vals = list(pop.values())
    ideal = sum(vals) / float(len(vals))
    spread = 100.0 * (max(vals) - min(vals)) / ideal
    print("  people on the 2020 census: %s; %d in all, %.1f%% apart; %d inside the city's "
          "map and outside its limits, %d inside its limits and in no district"
          % (", ".join("%s: %d" % (d, pop[d]) for d in sorted(pop, key=_order)), sum(vals),
             spread, outside, gap), file=sys.stderr)
    for geoid, n, lat, lng in gap_blocks:
        print("    in no district: block %s, %d people, at %.6f,%.6f" % (geoid, n, lat, lng),
              file=sys.stderr)
    problems = []
    got = {d: pop[d] for d in sorted(pop, key=_order)}
    if got != c["people"]:
        problems.append("the 2020 census puts %s in its districts, not the pinned %s. A line "
                        "that moved is a redistricting until a person has read it"
                        % (got, c["people"]))
    if outside != c["outside"]:
        problems.append("%d people live inside the city's map and outside its limits, not "
                        "the pinned %s. The city's map or the Census line has moved"
                        % (outside, c["outside"]))
    if gap != c["gap"]:
        problems.append("%d people live inside the city's limits and in no district, not "
                        "the pinned %d. A reader at home there would be told no district"
                        % (gap, c["gap"]))
    return problems, pop, blocks


def own_problems(c, pop, own):
    """The city's own count against the people inside its cut districts."""
    if own is None:
        return []
    problems = []
    if set(own) != set(pop):
        problems.append("the city's own figures are for districts %s, and its map draws %s"
                        % (sorted(own, key=_order), sorted(pop, key=_order)))
    diff = {d: pop[d] - own.get(d, 0) for d in sorted(pop, key=_order) if pop[d] != own.get(d, 0)}
    want = {d: v for d, (v, _why) in OWN_POPULATION.get(c["geoid"], {}).items()}
    print("  the city's own count: %s" % ("the same in every district" if not diff else
                                          "differs by %s" % diff), file=sys.stderr)
    if diff != want:
        problems.append("the city's own count differs from the 2020 census's people in its "
                        "cut districts by %s, where OWN_POPULATION records %s" % (diff, want))
    return problems


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


def _districts_text(items):
    return " and ".join("%s District %s" % (c, d) for c, d in items)


def cross_city(items, what, declared):
    """Ground two cities' districts both cover, part by part. `items` are
    {city, district, shape, geometry}. In the cut districts there must be
    none; in the drawn file every part must be one `declared` records, and
    every record must still match a part."""
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
    """Printed, never failed: ground a city's map puts in two of its own
    districts. It is the map as published, and the card names every district
    there."""
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
                    largest = (m2, a["district"], b["district"])
        if pairs:
            out.append("%s %.2f m2 across %d pairs of districts, the largest Districts %s and "
                       "%s over %.2f m2" % (city, total, pairs, largest[1], largest[2],
                                            largest[0]))
    print("in two districts of one city, in the %s: %s" % (what, "; ".join(out) or "nowhere"),
          file=sys.stderr)


# ---------------------------------------------------------- simplifying -----
def simplify_shared(exact):
    work = tempfile.mkdtemp(prefix="la-wards-")
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

    # parts the drawing removes: each recorded, each record still matching
    skip, dropped = set(), {}
    for rec in ACCEPTED_DROPPED_PARTS:
        geoid = geoid_of.get(rec["city"])
        f = src.get((geoid, rec["district"]))
        if f is None:
            problems.append("ACCEPTED_DROPPED_PARTS records %s District %s, which is not drawn"
                            % (rec["city"], rec["district"]))
            continue
        found = [p for p in _parts(shape(f["geometry"]))
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
    # rings: none lost but the recorded ones
    for k in sorted(src):
        a, b = _rings(src[k]["geometry"]), _rings(new[k]["geometry"])
        if a - dropped.get(k, 0) != b:
            problems.append("%s District %s has %d rings on the cut districts and %d drawn, "
                            "and ACCEPTED_DROPPED_PARTS records %d dropped"
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
    print("fidelity: the cut districts' lines stray at most %.2f m from the drawn ones "
          "(ceiling %.1f)" % (worst, FIDELITY_MAX_M), file=sys.stderr)
    if worst > FIDELITY_MAX_M:
        problems.append("the cut districts' lines stray %.2f m from the drawn ones, over %.1f m"
                        % (worst, FIDELITY_MAX_M))
    # people: every populated block, the same districts but the recorded ones
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
        meta, feats, served = fetch_layer(c)
        edited = (meta.get("editingInfo") or {}).get("dataLastEditDate") or \
            (meta.get("editingInfo") or {}).get("lastEditDate")
        print("  layer %r, last edited %s" % (meta.get("name"), _date(edited) or "not stated"),
              file=sys.stderr)
        raw, kept = districts_of(c, meta, feats, want[c["geoid"]])
        lat0 = _lat0(list(raw.values()))
        place_feat, place_served = fetch_place(c)
        place = pd.checked_shape(place_feat["geometry"], "%s place" % c["city"])
        plan, plan_name, plan_sha = fetch_plan(c)
        read[c["geoid"]] = {"city": c["city"], "layer": c["layer"],
                            "layer_name": meta.get("name"),
                            "last_edited": _date(edited),
                            "lines_sha256": lines_sha256(served, c),
                            "place_sha256": lines_sha256(place_served)}
        if plan is not None:
            read[c["geoid"]]["plan"] = {"layer": c["plan"]["layer"], "layer_name": plan_name,
                                        "figures_sha256": plan_sha}
        districts = cut(c, raw, place, lat0)
        problems += ["%s: %s" % (c["city"], p) for p in tiling(c, districts, place, lat0)]
        p_problems, pop, blocks = people(c, raw, districts, place)
        problems += ["%s: %s" % (c["city"], p) for p in p_problems]
        problems += ["%s: %s" % (c["city"], p)
                     for p in own_problems(c, pop, own_counts(c, kept, plan))]
        blocks_by_city[c["geoid"]] = blocks
        for d in sorted(districts, key=_order):
            cut_items.append(dict(city=c["city"], district=d, shape=districts[d],
                                  geometry=pd._geojson(districts[d])))
            exact["features"].append({
                "type": "Feature",
                "properties": {"geoid": c["geoid"], "city": c["city"], "district": d,
                               "seat": "District %s" % d, "source": c["source"] + EDGE,
                               "sourceUrl": c["page"]},
                "geometry": pd._geojson(districts[d]),
            })
    own_overlaps(cut_items, "cut districts")
    problems += cross_city(cut_items, "cut districts", [])
    simple = simplify_shared(exact)
    problems += drawn_checks(exact, simple, blocks_by_city)
    drawn_items = [dict(city=f["properties"]["city"], district=f["properties"]["district"],
                        shape=pd.checked_shape(f["geometry"], "drawn %s District %s"
                                               % (f["properties"]["city"],
                                                  f["properties"]["district"])),
                        geometry=f["geometry"]) for f in simple["features"]]
    own_overlaps(drawn_items, "drawn file")
    problems += cross_city(drawn_items, "drawn file", ACCEPTED_OVERLAPS)
    measure_areas(simple)
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
        "_about": ("GENERATED by la/scripts/build_la_city_wards.py. What each drawn city's "
                   "council districts were read from when the shipped file was built: the "
                   "district layer's address and name, the date the layer gives for its last "
                   "edit, a SHA-256 of the lines the layer and the Census Bureau's map of the "
                   "city served (lines_sha256), and for a city whose own figures come from a "
                   "plan layer, that layer's name and a SHA-256 of its figures. The monthly "
                   "source check asks the same questions again and compares; --check holds "
                   "this record to CITIES."),
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
    print("la-city-wards -> %s: %d districts in %d cities, %d bytes; the lines read are "
          "recorded in %s" % (os.path.relpath(OUT, INSTANCE), len(out["features"]), len(CITIES),
                              os.path.getsize(OUT), os.path.relpath(SOURCE_RECORD, INSTANCE)),
          file=sys.stderr)


def measure_areas(fc):
    """Printed for the worksheet's rank note: each drawn district's area."""
    from shapely.geometry import shape
    areas = []
    for f in fc["features"]:
        g = shape(f["geometry"])
        areas.append((_m2(g, (g.bounds[1] + g.bounds[3]) / 2.0) / 1e6,
                      "%s's District %s" % (f["properties"]["city"], f["properties"]["district"])))
    areas.sort()
    vals = [a for a, _ in areas]
    mid = len(vals) // 2
    median = vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2.0
    print("areas: %d districts, a mean %.1f km2 (median %.1f, from %.1f for %s to %.1f for %s)"
          % (len(vals), sum(vals) / len(vals), median, areas[0][0], areas[0][1],
             areas[-1][0], areas[-1][1]), file=sys.stderr)


APP_FILE = os.path.join(INSTANCE, "index.html")
WORKSHEET_FILE = os.path.join(INSTANCE, "metro-worksheet.json")
_NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven",
                 "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
                 "fifteen")


def _city_list(text):
    """'Lafayette, Central and Slidell' -> ['Lafayette', 'Central', 'Slidell']."""
    head, sep, last = text.rpartition(" and ")
    if not sep:
        return [text.strip()]
    return [s.strip() for s in head.split(",")] + [last.strip()]


def expected_cities():
    """{geoid: name} for Louisiana's cities of 25,000 people or more, from
    docs/expected-governments.json."""
    with open(EXPECTED_FILE, encoding="utf-8") as fh:
        units = json.load(fh)["units"]["la"]
    return {u["geoid"]: u["name"] for u in units if u.get("kind") == "place"}


def check_groups(roster):
    """CITIES, PARISH_DRAWN and NOT_DRAWN are exactly Louisiana's cities of
    25,000 people or more, with no city in two; every city drawn here or not
    drawn is in the city roster with a district seat, every parish-drawn city
    is not (its council is its parish's) and its parish is one the
    parish-district layer draws."""
    expected = expected_cities()
    drawn = [c["geoid"] for c in CITIES]
    groups = [set(drawn), set(PARISH_DRAWN), set(NOT_DRAWN)]
    if sum(len(g) for g in groups) != len(set().union(*groups)):
        fail("a city is in two of CITIES, PARISH_DRAWN and NOT_DRAWN")
    if set().union(*groups) != set(expected):
        fail("CITIES, PARISH_DRAWN and NOT_DRAWN together are %s, and Louisiana's cities of "
             "25,000 people or more are %s" % (sorted(set().union(*groups)), sorted(expected)))
    for c in CITIES:
        if not expected[c["geoid"]].startswith(c["city"] + " "):
            fail("%s: the Census id %s is %r" % (c["city"], c["geoid"], expected[c["geoid"]]))
    want, _ = roster_districts()
    for geoid in drawn + sorted(NOT_DRAWN):
        if not want.get(geoid):
            fail("%s is not in the city roster with district seats" % expected[geoid])
    for geoid, name in sorted(NOT_DRAWN.items()):
        if not expected[geoid].startswith(name.split(":", 1)[0] + " "):
            fail("NOT_DRAWN names %r for %s" % (name.split(":", 1)[0], expected[geoid]))
    with open(PARISH_LIST, encoding="utf-8") as fh:
        parishes = json.load(fh)
    for geoid, (name, parish) in sorted(PARISH_DRAWN.items()):
        if not expected[geoid].startswith(name + " "):
            fail("PARISH_DRAWN names %r for %s" % (name, expected[geoid]))
        if geoid in roster:
            fail("%s is in the city roster, so its council is not only its parish's" % name)
        if parish not in parishes:
            fail("%s's parish %s is not one the Police Jury or Council District layer draws"
                 % (name, parish))


def check_stated_cities(roster):
    """Four things a reader is shown say which cities are drawn, and all are
    written by hand: the City Council District card's empty state and the City
    card's list of drawn cities (LA_WARD_CITIES) in la/index.html, and the
    sources page's "Where it applies" and "What it answers" for this layer,
    which the worksheet carries. The empty state and "Where it applies" must
    name exactly the cities CITIES draws, give their count in words, name the
    parish-drawn cities as PARISH_DRAWN does and the left-out cities as
    NOT_DRAWN does; the list must hold exactly CITIES' Census ids. A city
    added to or taken out of a group therefore fails here until all of them
    say so."""
    check_groups(roster)
    drawn = [c["city"] for c in CITIES]
    left = [v.split(":", 1)[0] for v in NOT_DRAWN.values()]
    by_parish = [name for name, _ in PARISH_DRAWN.values()]
    total = len(expected_cities())
    count = _NUMBER_WORDS[len(drawn)]
    parish_sentence = "%s are governed by their parish's council" % _and(by_parish)
    with open(APP_FILE, encoding="utf-8") as fh:
        app = fh.read()
    at = app.find('id: "city-ward"')
    m = re.compile(r'emptyNote:\s*((?:"(?:[^"\\]|\\.)*"\s*\+\s*)*"(?:[^"\\]|\\.)*")\s*,'
                   ).search(app, at) if at >= 0 else None
    if m is None:
        fail("la/index.html: no emptyNote found after the city-ward layer's id")
    note = "".join(json.loads(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"', m.group(1)))
    lead = ("This map draws the council districts of %s of Louisiana's %d cities of 25,000 "
            "people or more (" % (count, total))
    if lead not in note:
        fail("la/index.html: the City Council District card's empty state does not say %r" % lead)
    named = _city_list(note.split(lead, 1)[1].split(")", 1)[0])
    if named != drawn:
        fail("la/index.html: the City Council District card's empty state names %s, and "
             "CITIES draws %s" % (named, drawn))
    if parish_sentence not in note:
        fail("la/index.html: the City Council District card's empty state does not say %r"
             % parish_sentence)
    stray = [c for c in left if c in note]
    if stray:
        fail("la/index.html: the City Council District card's empty state names %s, which "
             "this file does not draw" % stray)
    listed = re.search(r'var LA_WARD_CITIES = \[([^\]]*)\];', app)
    if listed is None:
        fail("la/index.html: no LA_WARD_CITIES list, which the City card reads to say "
             "whether a city's districts are drawn")
    ids = re.findall(r'"(\d{7})"', listed.group(1))
    want = sorted(c["geoid"] for c in CITIES)
    if sorted(ids) != want or len(ids) != len(set(ids)):
        fail("la/index.html: LA_WARD_CITIES lists %s, and CITIES draws %s" % (ids, want))
    with open(WORKSHEET_FILE, encoding="utf-8") as fh:
        layer = [x for x in json.load(fh)["layers"] if x["id"] == "city-ward"]
    if len(layer) != 1:
        fail("la/metro-worksheet.json: %d city-ward layers" % len(layer))
    applies = layer[0]["source"]["applies"]
    first, sep, rest = applies.partition(". ")
    if not sep or _city_list(first) != drawn:
        fail("la/metro-worksheet.json: the City Council District row's \"Where it applies\" "
             "opens %r, and CITIES draws %s" % (first, drawn))
    if parish_sentence not in rest:
        fail("la/metro-worksheet.json: the City Council District row's \"Where it applies\" "
             "does not say %r" % parish_sentence)
    lead = "The other %s cities of 25,000 people or more (" % _NUMBER_WORDS[len(left)]
    if lead not in rest:
        fail("la/metro-worksheet.json: the City Council District row's \"Where it applies\" "
             "does not say %r" % lead)
    if sorted(_city_list(rest.split(lead, 1)[1].split(")", 1)[0])) != sorted(left):
        fail("la/metro-worksheet.json: the City Council District row's \"Where it applies\" "
             "leaves out other cities than NOT_DRAWN records (%s)" % sorted(left))
    answers = layer[0]["source"]["answers"]
    if "in the %s Louisiana cities" % count not in answers:
        fail("la/metro-worksheet.json: the City Council District row's \"What it answers\" "
             "does not say \"in the %s Louisiana cities\"" % count)
    print("check: the City Council District card's empty state, the City card's list and "
          "the sources page name the %s cities drawn, the %d governed by their parish and "
          "the %d left out" % (count, len(by_parish), len(left)), file=sys.stderr)


def _and(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def check_source_record(record):
    """The build's record of what it read names every drawn city, at the layer
    CITIES gives and under the name its witness pins, with both fingerprints
    (and the plan's, where a city has one), so the monthly source check
    compares the lines served now with the lines the shipped file was drawn
    from."""
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
        plan = c.get("plan")
        got = rec.get("plan")
        if bool(plan) != bool(got):
            fail("%s: the source record %s a plan layer and CITIES %s one; rebuild"
                 % (c["city"], "names" if got else "names no", "names" if plan else "names no"))
        if plan and ((got.get("layer"), got.get("layer_name")) != (plan["layer"],
                                                                   plan["layer_name"])
                     or not re.match(r"^[0-9a-f]{64}$", str(got.get("figures_sha256", "")))):
            fail("%s: the source record's plan layer is not the one CITIES gives; rebuild"
                 % c["city"])
    print("check: the source record names the %d cities' layers as CITIES does, read %s"
          % (len(by_geoid), record["built"]), file=sys.stderr)


def check(out, record=None):
    """The offline half, on what ships: the cities are CITIES, each city's
    districts are its roster's district seats, every feature carries exactly
    the properties the card reads, and no seeded point inside one city's
    district is inside another city's. Then the hand-written statements
    naming the drawn cities are held to CITIES (check_stated_cities), and so
    is the record of what the build read (check_source_record), the shipped
    one unless `record` is given."""
    want, roster = roster_districts()
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
    check_stated_cities(roster)
    if record is None:
        with open(SOURCE_RECORD, encoding="utf-8") as fh:
            record = json.load(fh)
    check_source_record(record)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to CITIES and the city roster, and "
                         "the app's and the sources page's statements naming the drawn "
                         "cities to CITIES, PARISH_DRAWN and NOT_DRAWN")
    args = ap.parse_args()
    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            check(json.load(fh))
        return
    build()


if __name__ == "__main__":
    main()
