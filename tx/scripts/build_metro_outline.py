#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for Texas, the dissolved outline
of the WHOLE STATE, since coverage is statewide from day one — from Census
TIGERweb. Unlike Wisconsin's narrower "roster-covered" ring, this wash makes
no partial claim: METRO_COUNTY_FIPS is all 254 counties, and
DISPATCH_COUNTY_FIPS stays empty on purpose — this instance has no
per-county dispatch layers.

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK WHAT
ANSWERS. Every statewide layer answers in all 254 of them, so the wash claims
the whole state. If a layer is ever built that answers in only some of them
and the map should say so, narrow METRO_COUNTY_FIPS to what actually answers,
following `wi/scripts/build_metro_outline.py` (or Missouri's two-output
builder) rather than inventing a new shape.

Why this exists: the out-of-scope wash (index.html, ENGINE `scope-mask`)
marks where the app's fullest answer ends. It also keeps a boot cost out —
painting the wash from a live boundary fetch cost the reference fork 669 ms
in PSI's critical chain (docs/OPTIMIZATION_PLAYBOOK.md) before it
pre-built. This file is one small pre-dissolved feature.

WHY A BUILD STEP RATHER THAN TIGERweb's OWN STATE POLYGON (layer 0):
dissolving from the county fabric (layer 1) — rather than fetching the
state layer directly — is what lets this same script narrow to a subset of
counties the day coverage becomes partial, without changing shape. It also
means this file's geometry always agrees with `state-counties.json`'s own
fabric, since both come from the same layer.

The dissolve mirrors the app's `coverageOutlineRings` exactly: a segment
walked by two features is an interior border and is dropped; survivors
chain back into closed rings. READ THE RING COUNT FROM --check, NEVER FROM
A MAP IN YOUR HEAD — this project has got that wrong from a map more than
once. The coastal counties' polygons carry the bays and the Gulf out to the
county line, so the wash runs over that water, and the ring count is a
measurement the --check line prints, not a prediction made here.

Texas borders New Mexico, Oklahoma, Arkansas and Louisiana, and Mexico along
the Rio Grande. Oklahoma, Arkansas and Louisiana are live instances and New
Mexico is in the last batch of the state-level launch. OUTSIDE carries towns
just over each line, and in Mexico and the Gulf, to prove the dissolve did
not leak, and the worksheet's negative point is in Coahuila, Mexico, which
no instance will ever serve.

Usage:
    python3 tx/scripts/build_metro_outline.py                 # writes data/app/metro-outline.json
    python3 tx/scripts/build_metro_outline.py --check         # verify the shipped file, write nothing
"""

import argparse
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

# `requests` is imported INSIDE the one function that fetches, not at module
# scope: this module's pure-geometry helpers (simplify, rings_of,
# point_in_rings) are shared machinery this instance's other builders can import
# rather than fork, matching the Wisconsin precedent's reasoning.

TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "State_County/MapServer/1/query")

# Every Texas county's 3-digit FIPS: the 254 odd numbers 001 to 507 — the
# served area IS the whole state.
# BOTH constants below must stay plain literal assignments at module top:
# validate_index.py reads them via ast.literal_eval without importing.
METRO_COUNTY_FIPS = (
    "001", "003", "005", "007", "009", "011", "013", "015",
    "017", "019", "021", "023", "025", "027", "029", "031",
    "033", "035", "037", "039", "041", "043", "045", "047",
    "049", "051", "053", "055", "057", "059", "061", "063",
    "065", "067", "069", "071", "073", "075", "077", "079",
    "081", "083", "085", "087", "089", "091", "093", "095",
    "097", "099", "101", "103", "105", "107", "109", "111",
    "113", "115", "117", "119", "121", "123", "125", "127",
    "129", "131", "133", "135", "137", "139", "141", "143",
    "145", "147", "149", "151", "153", "155", "157", "159",
    "161", "163", "165", "167", "169", "171", "173", "175",
    "177", "179", "181", "183", "185", "187", "189", "191",
    "193", "195", "197", "199", "201", "203", "205", "207",
    "209", "211", "213", "215", "217", "219", "221", "223",
    "225", "227", "229", "231", "233", "235", "237", "239",
    "241", "243", "245", "247", "249", "251", "253", "255",
    "257", "259", "261", "263", "265", "267", "269", "271",
    "273", "275", "277", "279", "281", "283", "285", "287",
    "289", "291", "293", "295", "297", "299", "301", "303",
    "305", "307", "309", "311", "313", "315", "317", "319",
    "321", "323", "325", "327", "329", "331", "333", "335",
    "337", "339", "341", "343", "345", "347", "349", "351",
    "353", "355", "357", "359", "361", "363", "365", "367",
    "369", "371", "373", "375", "377", "379", "381", "383",
    "385", "387", "389", "391", "393", "395", "397", "399",
    "401", "403", "405", "407", "409", "411", "413", "415",
    "417", "419", "421", "423", "425", "427", "429", "431",
    "433", "435", "437", "439", "441", "443", "445", "447",
    "449", "451", "453", "455", "457", "459", "461", "463",
    "465", "467", "469", "471", "473", "475", "477", "479",
    "481", "483", "485", "487", "489", "491", "493", "495",
    "497", "499", "501", "503", "505", "507",
)
STATE_FIPS = "48"
# No dispatch entries: none of this instance's layers is county-dispatched.
DISPATCH_COUNTY_FIPS = {}

_UNLISTED = sorted(set(DISPATCH_COUNTY_FIPS.values()) - set(METRO_COUNTY_FIPS))
assert not _UNLISTED, (
    "DISPATCH_COUNTY_FIPS names county FIPS %s that METRO_COUNTY_FIPS omits — a "
    "county cannot be served and outside the coverage ring at the same time"
    % _UNLISTED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "metro-outline.json")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/tx/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One INSIDE anchor per county: the Census Bureau's own internal point for it
# (INTPTLAT/INTPTLON on TIGERweb State_County layer 1), which the Census
# places inside it by construction. Each was still verified interior against
# its own SIMPLIFIED rings in the shipped state-counties.json, and inside no
# other county, before being trusted here — ring closure alone is not proof a
# dissolve kept every county. All 254 passed when this table was generated,
# 2026-11-11. Keyed by the county's name without "County".
INSIDE = {
    "Anderson": (31.84126, -95.66173),
    "Andrews": (32.31226, -102.64021),
    "Angelina": (31.25190, -94.61113),
    "Aransas": (28.12262, -96.96750),
    "Archer": (33.61631, -98.68727),
    "Armstrong": (34.96418, -101.35664),
    "Atascosa": (28.89148, -98.53556),
    "Austin": (29.89190, -96.27017),
    "Bailey": (34.06752, -102.83034),
    "Bandera": (29.75680, -99.24359),
    "Bastrop": (30.10077, -97.31064),
    "Baylor": (33.61877, -99.20828),
    "Bee": (28.41608, -97.74259),
    "Bell": (31.03701, -97.47963),
    "Bexar": (29.44867, -98.52015),
    "Blanco": (30.26620, -98.39933),
    "Borden": (32.73859, -101.43920),
    "Bosque": (31.90190, -97.63788),
    "Bowie": (33.44606, -94.42239),
    "Brazoria": (29.16782, -95.43465),
    "Brazos": (30.65671, -96.30239),
    "Brewster": (29.80900, -103.25246),
    "Briscoe": (34.52517, -101.20589),
    "Brooks": (27.03499, -98.21528),
    "Brown": (31.76414, -98.99846),
    "Burleson": (30.49349, -96.62209),
    "Burnet": (30.78963, -98.20119),
    "Caldwell": (29.83240, -97.62814),
    "Calhoun": (28.44172, -96.57957),
    "Callahan": (32.29315, -99.37225),
    "Cameron": (26.10292, -97.47896),
    "Camp": (32.97458, -94.97908),
    "Carson": (35.40550, -101.35536),
    "Cass": (33.08370, -94.35758),
    "Castro": (34.53362, -102.25879),
    "Chambers": (29.69637, -94.66945),
    "Cherokee": (31.84388, -95.15634),
    "Childress": (34.51570, -100.20959),
    "Clay": (33.78590, -98.21292),
    "Cochran": (33.60844, -102.83045),
    "Coke": (31.87711, -100.63523),
    "Coleman": (31.91421, -99.34662),
    "Collin": (33.19449, -96.57943),
    "Collingsworth": (34.96538, -100.27127),
    "Colorado": (29.59617, -96.50879),
    "Comal": (29.81238, -98.25813),
    "Comanche": (31.95164, -98.54962),
    "Concho": (31.31888, -99.86365),
    "Cooke": (33.63920, -97.21034),
    "Coryell": (31.39118, -97.79802),
    "Cottle": (34.09191, -100.27644),
    "Crane": (31.44634, -102.55169),
    "Crockett": (30.71753, -101.40421),
    "Crosby": (33.60914, -101.29871),
    "Culberson": (31.44591, -104.52694),
    "Dallam": (36.28637, -102.59402),
    "Dallas": (32.76699, -96.77842),
    "Dawson": (32.74253, -101.94877),
    "DeWitt": (29.08251, -97.36311),
    "Deaf Smith": (34.94077, -102.60756),
    "Delta": (33.38593, -95.67335),
    "Denton": (33.20513, -97.12114),
    "Dickens": (33.61536, -100.78762),
    "Dimmit": (28.42359, -99.76587),
    "Donley": (34.95504, -100.81585),
    "Duval": (27.68112, -98.49739),
    "Eastland": (32.32465, -98.83656),
    "Ector": (31.86530, -102.54251),
    "Edwards": (29.98593, -100.30740),
    "El Paso": (31.76220, -106.24137),
    "Ellis": (32.34689, -96.79696),
    "Erath": (32.23621, -98.21834),
    "Falls": (31.25193, -96.93413),
    "Fannin": (33.59116, -96.10499),
    "Fayette": (29.88485, -96.91100),
    "Fisher": (32.74047, -100.40312),
    "Floyd": (34.07373, -101.30327),
    "Foard": (33.96331, -99.81683),
    "Fort Bend": (29.52660, -95.77101),
    "Franklin": (33.17585, -95.21907),
    "Freestone": (31.70175, -96.14496),
    "Frio": (28.86938, -99.10900),
    "Gaines": (32.74394, -102.63156),
    "Galveston": (29.23527, -94.88778),
    "Garza": (33.18379, -101.30113),
    "Gillespie": (30.32509, -98.94183),
    "Glasscock": (31.86801, -101.52149),
    "Goliad": (28.66070, -97.43041),
    "Gonzales": (29.46288, -97.49010),
    "Gray": (35.40254, -100.81237),
    "Grayson": (33.62455, -96.67578),
    "Gregg": (32.48639, -94.81627),
    "Grimes": (30.54323, -95.98808),
    "Guadalupe": (29.58267, -97.94900),
    "Hale": (34.06844, -101.82289),
    "Hall": (34.45319, -100.57634),
    "Hamilton": (31.70734, -98.11176),
    "Hansford": (36.27285, -101.35693),
    "Hardeman": (34.28990, -99.74570),
    "Hardin": (30.32956, -94.39249),
    "Harris": (29.85727, -95.39304),
    "Harrison": (32.54799, -94.37442),
    "Hartley": (35.84024, -102.61005),
    "Haskell": (33.17596, -99.73077),
    "Hays": (30.06122, -98.02927),
    "Hemphill": (35.81600, -100.27919),
    "Henderson": (32.21244, -95.85344),
    "Hidalgo": (26.39946, -98.17675),
    "Hill": (31.98323, -97.13059),
    "Hockley": (33.60593, -102.34340),
    "Hood": (32.43015, -97.83168),
    "Hopkins": (33.14897, -95.56543),
    "Houston": (31.32304, -95.42160),
    "Howard": (32.30343, -101.43872),
    "Hudspeth": (31.45087, -105.37755),
    "Hunt": (33.12331, -96.08423),
    "Hutchinson": (35.83705, -101.36275),
    "Irion": (31.30342, -100.98130),
    "Jack": (33.23553, -98.16928),
    "Jackson": (28.95980, -96.58908),
    "Jasper": (30.75293, -94.02229),
    "Jeff Davis": (30.62847, -104.19036),
    "Jefferson": (29.85403, -94.14932),
    "Jim Hogg": (27.05323, -98.74757),
    "Jim Wells": (27.73352, -98.09081),
    "Johnson": (32.37965, -97.36491),
    "Jones": (32.74405, -99.87760),
    "Karnes": (28.90861, -97.85271),
    "Kaufman": (32.61450, -96.28819),
    "Kendall": (29.94352, -98.70927),
    "Kenedy": (26.89021, -97.59114),
    "Kent": (33.18478, -100.76972),
    "Kerr": (30.05372, -99.37444),
    "Kimble": (30.47947, -99.74640),
    "King": (33.61427, -100.24535),
    "Kinney": (29.34709, -100.41770),
    "Kleberg": (27.43873, -97.66062),
    "Knox": (33.61189, -99.73036),
    "La Salle": (28.35110, -99.09677),
    "Lamar": (33.66726, -95.57035),
    "Lamb": (34.06886, -102.34802),
    "Lampasas": (31.19673, -98.24089),
    "Lavaca": (29.38258, -96.92363),
    "Lee": (30.32134, -96.97664),
    "Leon": (31.30049, -95.99562),
    "Liberty": (30.18609, -94.85537),
    "Limestone": (31.54754, -96.59362),
    "Lipscomb": (36.28020, -100.27268),
    "Live Oak": (28.35148, -98.12689),
    "Llano": (30.70758, -98.68469),
    "Loving": (31.88761, -103.45297),
    "Lubbock": (33.61147, -101.81994),
    "Lynn": (33.17841, -101.81849),
    "Madison": (30.96688, -95.93037),
    "Marion": (32.79833, -94.35685),
    "Martin": (32.30983, -101.96184),
    "Mason": (30.70391, -99.23684),
    "Matagorda": (28.77476, -96.00153),
    "Maverick": (28.72979, -100.31668),
    "McCulloch": (31.20548, -99.35986),
    "McLennan": (31.55116, -97.20095),
    "McMullen": (28.38492, -98.57885),
    "Medina": (29.35366, -99.11108),
    "Menard": (30.88527, -99.85884),
    "Midland": (31.81427, -102.00245),
    "Milam": (30.79124, -96.98439),
    "Mills": (31.50188, -98.60723),
    "Mitchell": (32.30412, -100.92439),
    "Montague": (33.67836, -97.72501),
    "Montgomery": (30.29881, -95.50296),
    "Moore": (35.83568, -101.89050),
    "Morris": (33.11647, -94.73127),
    "Motley": (34.05790, -100.79315),
    "Nacogdoches": (31.61864, -94.62146),
    "Navarro": (32.04335, -96.47641),
    "Newton": (30.78672, -93.73925),
    "Nolan": (32.31234, -100.41811),
    "Nueces": (27.73997, -97.51630),
    "Ochiltree": (36.27874, -100.81586),
    "Oldham": (35.40192, -102.59762),
    "Orange": (30.11805, -93.89235),
    "Palo Pinto": (32.75230, -98.31801),
    "Panola": (32.16398, -94.30516),
    "Parker": (32.77710, -97.80590),
    "Parmer": (34.53216, -102.78485),
    "Pecos": (30.77330, -102.71815),
    "Polk": (30.78455, -94.83734),
    "Potter": (35.39868, -101.89380),
    "Presidio": (30.00589, -104.26162),
    "Rains": (32.87046, -95.79561),
    "Randall": (34.96253, -101.89555),
    "Reagan": (31.37519, -101.51440),
    "Real": (29.83010, -99.81255),
    "Red River": (33.61963, -95.04843),
    "Reeves": (31.30837, -103.71271),
    "Refugio": (28.32212, -97.16247),
    "Roberts": (35.83860, -100.83668),
    "Robertson": (31.02548, -96.51494),
    "Rockwall": (32.89943, -96.41162),
    "Runnels": (31.84507, -99.98131),
    "Rusk": (32.10942, -94.75638),
    "Sabine": (31.34330, -93.85191),
    "San Augustine": (31.38245, -94.16318),
    "San Jacinto": (30.57439, -95.16314),
    "San Patricio": (28.01179, -97.51716),
    "San Saba": (31.15514, -98.81929),
    "Schleicher": (30.89623, -100.52722),
    "Scurry": (32.74435, -100.91335),
    "Shackelford": (32.74382, -99.34700),
    "Shelby": (31.79014, -94.14258),
    "Sherman": (36.27859, -101.89926),
    "Smith": (32.37378, -95.26894),
    "Somervell": (32.21811, -97.77005),
    "Starr": (26.53094, -98.74023),
    "Stephens": (32.73805, -98.83934),
    "Sterling": (31.83594, -101.05988),
    "Stonewall": (33.17958, -100.25381),
    "Sutton": (30.52219, -100.51336),
    "Swisher": (34.52632, -101.74386),
    "Tarrant": (32.77212, -97.29122),
    "Taylor": (32.29713, -99.89043),
    "Terrell": (30.23234, -102.07251),
    "Terry": (33.17123, -102.33928),
    "Throckmorton": (33.17070, -99.20580),
    "Titus": (33.21439, -94.96771),
    "Tom Green": (31.39727, -100.46438),
    "Travis": (30.23953, -97.69105),
    "Trinity": (31.09668, -95.15169),
    "Tyler": (30.76930, -94.37566),
    "Upshur": (32.73535, -94.94118),
    "Upton": (31.35369, -102.04159),
    "Uvalde": (29.35030, -99.76841),
    "Val Verde": (29.87529, -101.14332),
    "Van Zandt": (32.55879, -95.83691),
    "Victoria": (28.79637, -96.97120),
    "Walker": (30.74313, -95.56984),
    "Waller": (30.01359, -95.98215),
    "Ward": (31.50310, -103.09742),
    "Washington": (30.21508, -96.41027),
    "Webb": (27.74654, -99.33550),
    "Wharton": (29.27848, -96.22967),
    "Wheeler": (35.39262, -100.25309),
    "Wichita": (33.98818, -98.70807),
    "Wilbarger": (34.08492, -99.24244),
    "Willacy": (26.48186, -97.59473),
    "Williamson": (30.64908, -97.60506),
    "Wilson": (29.17388, -98.08673),
    "Winkler": (31.82794, -102.97193),
    "Wise": (33.21731, -97.66299),
    "Wood": (32.78359, -95.38217),
    "Yoakum": (33.16234, -102.83224),
    "Young": (33.15878, -98.67839),
    "Zapata": (26.99698, -99.18260),
    "Zavala": (28.86465, -99.75983),
}

# Towns just over each state line, and the worksheet's negative point, each
# checked against TIGERweb's own state layer on 2026-11-11 (Census answer, not
# a guess from a map; controls: the State Capitol returns Texas and a point in
# the open Gulf returns no state; re-read the same way 2026-11-11 with those
# controls before this change shipped), and each lies in no feature of the
# shipped state-counties.json: four in New Mexico, four in Oklahoma, one in
# Arkansas, three in Louisiana, which TIGERweb names; and seven in Mexico and
# one in the Gulf, where it names no state. Keys read "Place (XX)" or name the
# country, so county_of() names no Texas county.
OUTSIDE = {
    "Las Cruces (NM)": (32.31990, -106.76370),
    "Hobbs (NM)": (32.70260, -103.13600),
    "Clovis (NM)": (34.40480, -103.20520),
    "Clayton (NM)": (36.45170, -103.18410),
    "Guymon (OK)": (36.68280, -101.48150),
    "Altus (OK)": (34.63810, -99.33400),
    "Durant (OK)": (33.99400, -96.37080),
    "Idabel (OK)": (33.89570, -94.82660),
    "Ashdown (AR)": (33.67430, -94.13100),
    "Shreveport (LA)": (32.52520, -93.75020),
    "Leesville (LA)": (31.14350, -93.26100),
    "Lake Charles (LA)": (30.22660, -93.21740),
    "Ciudad Juarez (Chihuahua, MX)": (31.69040, -106.42450),
    "Ojinaga (Chihuahua, MX)": (29.54610, -104.40920),
    "Piedras Negras (Coahuila, MX)": (28.70000, -100.52360),
    "Coahuila desert (MX), the worksheet's negative point": (28.50000, -101.50000),
    "Nuevo Laredo (Tamaulipas, MX)": (27.47630, -99.51640),
    "Reynosa (Tamaulipas, MX)": (26.08060, -98.28830),
    "Matamoros (Tamaulipas, MX)": (25.86900, -97.50270),
    "Gulf of Mexico, 150 km off Freeport": (27.50000, -95.00000),
}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="tx-build-metro-outline")
    resp = requests.get(TIGERWEB, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": where,
        "outFields": "NAME,GEOID",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if len(feats) != len(METRO_COUNTY_FIPS):
        print("FATAL: TIGERweb returned %d counties, expected %d — the query or the "
              "service changed" % (len(feats), len(METRO_COUNTY_FIPS)), file=sys.stderr)
        sys.exit(1)
    return feats


def rings_of(feature):
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        return list(geom.get("coordinates") or [])
    if geom.get("type") == "MultiPolygon":
        return [r for poly in (geom.get("coordinates") or []) for r in poly]
    return []


def dissolve(features):
    """Drop every segment walked twice (an interior border), chain the rest.

    Mirrors index.html's coverageOutlineRings so the shipped file is exactly
    what the browser would have computed — one algorithm, two places, and the
    validation below proves this one.
    """
    counts, seg_pts = {}, {}
    for feat in features:
        for ring in rings_of(feat):
            for i in range(len(ring) - 1):
                a, b = tuple(ring[i][:2]), tuple(ring[i + 1][:2])
                if a == b:
                    continue
                key = (a, b) if a < b else (b, a)
                counts[key] = counts.get(key, 0) + 1
                seg_pts[key] = (a, b)

    adj = {}
    for key, n in counts.items():
        if n != 1:
            continue  # interior border — both neighbours walked it
        a, b = seg_pts[key]
        adj.setdefault(a, []).append((key, b))
        adj.setdefault(b, []).append((key, a))

    used, rings = set(), []
    for seed, n in counts.items():
        if n != 1 or seed in used:
            continue
        start, cur = seg_pts[seed][0], seg_pts[seed][1]
        used.add(seed)
        ring = [list(start), list(cur)]
        while cur != start:
            nxt = None
            for key, pt in adj.get(cur, ()):
                if key not in used:
                    nxt = (key, pt)
                    break
            if nxt is None:
                print("FATAL: open chain while dissolving — the counties do not tile "
                      "cleanly (a source change?)", file=sys.stderr)
                sys.exit(1)
            used.add(nxt[0])
            cur = nxt[1]
            ring.append(list(cur))
        rings.append(ring)
    return rings


def simplify(ring, tolerance_m=SIMPLIFY_TOLERANCE_M):
    """Douglas-Peucker. Many county borders are survey-grid straight lines, so this
    collapses a large vertex count to a small one with no visible change to a
    wash whose whole job is to say "coverage ends here". Distances are
    metres, with longitude compressed by cos(latitude) so the tolerance means
    the same thing on both axes."""
    if len(ring) < 3:
        return ring
    tol = tolerance_m / 111320.0
    scale = math.cos(math.radians(41.0))  # Texas's middle latitude

    def perp(p, a, b):
        ax, ay = a[0] * scale, a[1]
        bx, by = b[0] * scale, b[1]
        px, py = p[0] * scale, p[1]
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    keep = {0, len(ring) - 1}
    stack = [(0, len(ring) - 1)]
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        worst, wi = 0.0, None
        for k in range(i + 1, j):
            d = perp(ring[k], ring[i], ring[j])
            if d > worst:
                worst, wi = d, k
        if worst > tol and wi is not None:
            keep.add(wi)
            stack.append((i, wi))
            stack.append((wi, j))
    out = [ring[i] for i in sorted(keep)]
    if out[0] != out[-1]:
        out.append(out[0])  # a ring must close
    return out


def point_in_rings(lat, lng, rings):
    """Even-odd test against every ring, matching the app's pointInGeometry."""
    inside = False
    for ring in rings:
        for i in range(len(ring) - 1):
            x1, y1 = ring[i][0], ring[i][1]
            x2, y2 = ring[i + 1][0], ring[i + 1][1]
            if (y1 > lat) != (y2 > lat):
                if lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                    inside = not inside
    return inside


def validate(rings):
    problems = []
    for label, (lat, lng) in sorted(INSIDE.items()):
        if not point_in_rings(lat, lng, rings):
            problems.append("%s should be INSIDE the metro outline and is not" % label)
    for label, (lat, lng) in sorted(OUTSIDE.items()):
        if point_in_rings(lat, lng, rings):
            problems.append("%s should be OUTSIDE the metro outline and is not" % label)
    return problems


def group_rings(rings):
    """Nest each ring under the ring that encloses it — outers, then their holes.

    How many outer rings Texas's fabric dissolves to is a
    measurement rather than a prediction (see the module docstring), and the
    nesting logic is unchanged from the Wisconsin/Iowa/Michigan build either
    way, so a future partial-coverage narrowing needs no new code — only a
    smaller METRO_COUNTY_FIPS.
    """
    ordered = sorted(rings, key=len, reverse=True)
    polys = []  # [outer, hole, hole, ...]
    for ring in ordered:
        lng, lat = ring[0][0], ring[0][1]
        for poly in polys:
            if point_in_rings(lat, lng, [poly[0]]):
                poly.append(ring)  # enclosed -> a hole in that outer
                break
        else:
            polys.append([ring])
    return polys


def check_envelopes(rings):
    """The input shell must reach at least as far as the data does.

    METRO_BBOX (geocoder viewbox + the geolocate gate) and PERMALINK_GATE (the
    #point= sanity bound) are hand-set values in metro-worksheet.json that
    describe "where we serve" — checked against the SIMPLIFIED rings, i.e.
    the geometry actually shipped, per the Wisconsin precedent that caught
    three real envelope gaps the hard way.
    """
    xs = [p[0] for ring in rings for p in ring]
    ys = [p[1] for ring in rings for p in ring]
    env = {"minLng": min(xs), "maxLng": max(xs), "minLat": min(ys), "maxLat": max(ys)}
    try:
        with open(WORKSHEET, encoding="utf-8") as f:
            worksheet = json.load(f)
    except (IOError, ValueError) as exc:
        return ["could not read metro-worksheet.json (%s)" % exc]

    problems = []
    for key in ("metro_bbox", "permalink_gate"):
        box = worksheet.get(key)
        if not box:
            problems.append("metro-worksheet.json has no %s" % key)
            continue
        for edge, cmp_ in (("minLng", "gt"), ("minLat", "gt"), ("maxLng", "lt"), ("maxLat", "lt")):
            if edge not in box:
                problems.append("%s is missing %s" % (key, edge))
                continue
            too_tight = box[edge] > env[edge] if cmp_ == "gt" else box[edge] < env[edge]
            if too_tight:
                problems.append(
                    "%s.%s is %.4f but the served area reaches %.4f — widen it, or a "
                    "point there is silently rejected" % (key, edge, box[edge], env[edge]))
    return problems


def build_geojson(rings):
    polys = group_rings(rings)
    geometry = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                else {"type": "MultiPolygon", "coordinates": polys})
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "%d-county coverage area" % len(METRO_COUNTY_FIPS)},
            "geometry": geometry,
        }],
    }


# --- the anchor registry: one anchor per served county, and no county both ----
#
# THE ANCHOR LIST IS THIS GATE'S OWN SURFACE, and until 2026-09-02 nothing
# checked it. `--check` validates the SHIPPED ring against INSIDE/OUTSIDE and
# never rebuilds from METRO_COUNTY_FIPS, so a county added to that tuple
# without an anchor is green by construction — the ring is simply never asked
# about it. That is how Wisconsin greyed out seven counties for two days with
# every gate in the repo passing, and what its validator's
# check_coverage_ring_tracks_roster was written for.
#
# The convention every instance already follows is one INSIDE anchor per served
# county, so the count identity below turns "somebody added a FIPS and forgot
# the anchor" (or the reverse) into a failure, offline, from source alone. A
# true rebuild-and-diff would be stronger and needs TIGERweb, which is why it
# is not in CI; this is what can be proven without the network.
#
# KEY SHAPES DIFFER BY INSTANCE AND BOTH ARE CORRECT. The reference instance
# keys anchors "Place (County)" because its ring is a subset of its state and a
# reader needs to know which county a town vouches for; the statewide instances
# whose ring IS the state key them by county name alone. A check that demanded
# either shape would fail correct instances, so county_of() accepts both.
def county_of(anchor_key):
    """The county an anchor vouches for, from either key shape.

    "Marion (Williamson)" -> "Williamson"; "Bond, 3rd Circuit" -> "Bond";
    "Fond du Lac" -> "Fond du Lac".
    """
    key = anchor_key.strip()
    # No regex on purpose: these modules import only what they build with, and
    # a gate should not add a dependency to say something this simple.
    if key.endswith(")") and "(" in key:
        key = key[key.rindex("(") + 1:-1]
    return key.split(",")[0].strip()


def check_anchor_registry():
    """Problems with the anchor lists themselves, as a list of strings."""
    problems = []
    if len(INSIDE) != len(METRO_COUNTY_FIPS):
        problems.append(
            "%d INSIDE anchor(s) for %d served county/counties — every served "
            "county carries exactly one anchor, so these must match. A county "
            "added to METRO_COUNTY_FIPS without an anchor is never tested "
            "against the ring, and an anchor with no county is testing ground "
            "the wash no longer claims."
            % (len(INSIDE), len(METRO_COUNTY_FIPS)))
    seen = {}
    for key in INSIDE:
        seen.setdefault(county_of(key), []).append(key)
    for county, keys in sorted(seen.items()):
        if len(keys) > 1:
            problems.append(
                "%s has %d INSIDE anchors (%s) — with one anchor per county the "
                "count identity above cannot tell a doubled county from a "
                "missing one" % (county, len(keys), ", ".join(sorted(keys))))
    both = sorted({county_of(k) for k in INSIDE} & {county_of(k) for k in OUTSIDE})
    if both:
        problems.append(
            "%s appear(s) in BOTH INSIDE and OUTSIDE — when a county joins, its "
            "OUTSIDE anchor moves rather than being left behind, or the ring is "
            "asserted to both contain and exclude the same ground" % ", ".join(both))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", default=OUT_PATH)
    ap.add_argument("--check", action="store_true",
                    help="validate the shipped file instead of rebuilding")
    args = ap.parse_args()

    if args.check:
        with open(args.out) as f:
            shipped = json.load(f)
        # rings_of() flattens Polygon and MultiPolygon alike, so the anchor test
        # reads the file the same way whether or not the served area is one region.
        rings = rings_of(shipped["features"][0])
        problems = (check_anchor_registry() + validate(rings)
                    + check_envelopes(rings))
        for p in problems:
            print("FAIL: %s" % p, file=sys.stderr)
        if problems:
            sys.exit(1)
        print("metro-outline: OK — %d ring(s), %d vertices, all %d inside / %d outside "
              "anchors correct" % (len(rings), sum(len(r) for r in rings),
                                   len(INSIDE), len(OUTSIDE)), file=sys.stderr)
        return

    rings = [simplify(r) for r in dissolve(fetch_counties())]
    problems = (check_anchor_registry() + validate(rings)
                + check_envelopes(rings))
    for p in problems:
        print("FATAL: %s" % p, file=sys.stderr)
    if problems:
        print("FATAL: refusing to write an outline that misplaces its anchors",
              file=sys.stderr)
        sys.exit(1)

    with open(args.out, "w") as f:
        json.dump(build_geojson(rings), f, separators=(",", ":"))
        f.write("\n")
    size = os.path.getsize(args.out)
    print("wrote %s: %d ring(s), %d vertices, %.1f KB"
          % (args.out, len(rings), sum(len(r) for r in rings), size / 1024.0),
          file=sys.stderr)


if __name__ == "__main__":
    main()
