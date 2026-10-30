#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for Georgia, the dissolved outline of
the WHOLE STATE — from Census TIGERweb. METRO_COUNTY_FIPS is all 159
counties, and DISPATCH_COUNTY_FIPS stays empty on purpose: this instance has
no per-county dispatch layers yet.

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK WHAT
ANSWERS. Every statewide layer this instance ships (the U.S. House, both
chambers of the General Assembly, the county, the city, the school district,
the ZIP code and the census county division) answers in all 159 counties, so
the wash claims the whole state. County commission districts are not drawn
yet, and that is recorded as a gap rather than drawn as a narrower ring. When
the commission layer arrives and draws some counties and not others, narrow
this file the way `mo/scripts/build_metro_outline.py` did on 2026-10-26 (two
tiers: the counties whose district lines are drawn, and the state), rather
than inventing a new shape.

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
once. Georgia's coast is a fringe of barrier islands, and its eastern border
follows the Savannah River and its southwestern the Chattahoochee, so the ring
count is a measurement the --check line prints, not a prediction made here.

Georgia borders five states: Tennessee, North Carolina and South Carolina,
which are live, and Alabama and Florida, which no instance serves. OUTSIDE
carries towns just over each line to prove the dissolve did not leak, and the
worksheet's negative point is Tallahassee, Florida, about 26 km south of the
line, where no instance answers today.

Usage:
    python3 ga/scripts/build_metro_outline.py                 # writes data/app/metro-outline.json
    python3 ga/scripts/build_metro_outline.py --check         # verify the shipped file, write nothing
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

# Every Georgia county's 3-digit FIPS — the served area IS the whole state.
# BOTH constants below must stay plain literal assignments at module top:
# validate_index.py reads them via ast.literal_eval without importing.
METRO_COUNTY_FIPS = (
    "001", "003", "005", "007", "009", "011", "013", "015",
    "017", "019", "021", "023", "025", "027", "029", "031",
    "033", "035", "037", "039", "043", "045", "047", "049",
    "051", "053", "055", "057", "059", "061", "063", "065",
    "067", "069", "071", "073", "075", "077", "079", "081",
    "083", "085", "087", "089", "091", "093", "095", "097",
    "099", "101", "103", "105", "107", "109", "111", "113",
    "115", "117", "119", "121", "123", "125", "127", "129",
    "131", "133", "135", "137", "139", "141", "143", "145",
    "147", "149", "151", "153", "155", "157", "159", "161",
    "163", "165", "167", "169", "171", "173", "175", "177",
    "179", "181", "183", "185", "187", "189", "191", "193",
    "195", "197", "199", "201", "205", "207", "209", "211",
    "213", "215", "217", "219", "221", "223", "225", "227",
    "229", "231", "233", "235", "237", "239", "241", "243",
    "245", "247", "249", "251", "253", "255", "257", "259",
    "261", "263", "265", "267", "269", "271", "273", "275",
    "277", "279", "281", "283", "285", "287", "289", "291",
    "293", "295", "297", "299", "301", "303", "305", "307",
    "309", "311", "313", "315", "317", "319", "321",
)
STATE_FIPS = "13"
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

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/ga/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One INSIDE anchor per county: the Census Bureau's own internal point for the
# county (INTPTLAT/INTPTLON on TIGERweb State_County layer 1), which the
# Census places inside the county by construction. Each was still verified
# interior against that county's own SIMPLIFIED rings in the shipped
# state-counties.json, and inside no other county, before being trusted here —
# ring closure alone is not proof a dissolve kept every county. All 159 passed
# when this table was generated, 2026-10-29.
INSIDE = {
    "Appling": (31.73973, -82.29010),
    "Atkinson": (31.29681, -82.87815),
    "Bacon": (31.55676, -82.45191),
    "Baker": (31.31958, -84.45488),
    "Baldwin": (33.05949, -83.25546),
    "Banks": (34.34996, -83.49582),
    "Barrow": (33.99201, -83.71230),
    "Bartow": (34.24092, -84.83819),
    "Ben Hill": (31.73058, -83.16296),
    "Berrien": (31.28865, -83.22787),
    "Bibb": (32.80900, -83.69405),
    "Bleckley": (32.43540, -83.33172),
    "Brantley": (31.19733, -81.98298),
    "Brooks": (30.82293, -83.58191),
    "Bryan": (32.01797, -81.43854),
    "Bulloch": (32.39449, -81.74144),
    "Burke": (33.06018, -82.00016),
    "Butts": (33.29036, -83.95822),
    "Calhoun": (31.52128, -84.62629),
    "Camden": (30.91336, -81.64202),
    "Candler": (32.40398, -82.07128),
    "Carroll": (33.58224, -85.08053),
    "Catoosa": (34.90021, -85.13939),
    "Charlton": (30.75429, -82.13376),
    "Chatham": (31.97552, -81.08982),
    "Chattahoochee": (32.34745, -84.78802),
    "Chattooga": (34.47418, -85.34529),
    "Cherokee": (34.24432, -84.47506),
    "Clarke": (33.95219, -83.36715),
    "Clay": (31.62153, -84.98552),
    "Clayton": (33.55251, -84.41318),
    "Clinch": (30.91765, -82.70261),
    "Cobb": (33.93574, -84.57779),
    "Coffee": (31.54977, -82.84462),
    "Colquitt": (31.18949, -83.76985),
    "Columbia": (33.55207, -82.24961),
    "Cook": (31.15252, -83.42944),
    "Coweta": (33.35290, -84.76214),
    "Crawford": (32.70944, -83.97917),
    "Crisp": (31.92027, -83.75653),
    "Dade": (34.85242, -85.50620),
    "Dawson": (34.44434, -84.17359),
    "DeKalb": (33.77066, -84.22634),
    "Decatur": (30.88021, -84.58408),
    "Dodge": (32.16437, -83.16787),
    "Dooly": (32.15200, -83.80717),
    "Dougherty": (31.53259, -84.20904),
    "Douglas": (33.70124, -84.76731),
    "Early": (31.32419, -84.90672),
    "Echols": (30.71156, -82.90208),
    "Effingham": (32.36168, -81.34337),
    "Elbert": (34.11641, -82.84193),
    "Emanuel": (32.59120, -82.30019),
    "Evans": (32.15309, -81.89016),
    "Fannin": (34.86715, -84.31627),
    "Fayette": (33.41272, -84.49394),
    "Floyd": (34.26372, -85.21365),
    "Forsyth": (34.22473, -84.12086),
    "Franklin": (34.37505, -83.22799),
    "Fulton": (33.79003, -84.46818),
    "Gilmer": (34.69052, -84.45481),
    "Glascock": (33.22749, -82.60691),
    "Glynn": (31.21303, -81.49592),
    "Gordon": (34.50967, -84.87386),
    "Grady": (30.87590, -84.24496),
    "Greene": (33.57671, -83.16662),
    "Gwinnett": (33.95876, -84.02574),
    "Habersham": (34.63439, -83.52587),
    "Hall": (34.31757, -83.81850),
    "Hancock": (33.26922, -83.00047),
    "Haralson": (33.79516, -85.22006),
    "Harris": (32.73155, -84.91243),
    "Hart": (34.34903, -82.96303),
    "Heard": (33.29135, -85.13789),
    "Henry": (33.45295, -84.15402),
    "Houston": (32.45815, -83.66231),
    "Irwin": (31.60431, -83.27704),
    "Jackson": (34.13093, -83.56237),
    "Jasper": (33.31698, -83.68915),
    "Jeff Davis": (31.81177, -82.63691),
    "Jefferson": (33.05818, -82.42000),
    "Jenkins": (32.79521, -81.96752),
    "Johnson": (32.69458, -82.66397),
    "Jones": (33.02166, -83.56220),
    "Lamar": (33.07444, -84.14669),
    "Lanier": (31.03820, -83.06316),
    "Laurens": (32.39322, -82.92632),
    "Lee": (31.81842, -84.14668),
    "Liberty": (31.80808, -81.44441),
    "Lincoln": (33.79215, -82.44830),
    "Long": (31.74956, -81.74287),
    "Lowndes": (30.83334, -83.26884),
    "Lumpkin": (34.56814, -83.99893),
    "Macon": (32.36269, -84.05123),
    "Madison": (34.12755, -83.20865),
    "Marion": (32.35942, -84.52870),
    "McDuffie": (33.48061, -82.47957),
    "McIntosh": (31.48522, -81.37207),
    "Meriwether": (33.02927, -84.66706),
    "Miller": (31.16293, -84.73040),
    "Mitchell": (31.22900, -84.19204),
    "Monroe": (33.01878, -83.92184),
    "Montgomery": (32.17211, -82.53335),
    "Morgan": (33.59865, -83.49942),
    "Murray": (34.79710, -84.73799),
    "Muscogee": (32.51074, -84.87410),
    "Newton": (33.55275, -83.85136),
    "Oconee": (33.83647, -83.43682),
    "Oglethorpe": (33.86618, -83.06777),
    "Paulding": (33.92217, -84.86888),
    "Peach": (32.57156, -83.83155),
    "Pickens": (34.45696, -84.49041),
    "Pierce": (31.35400, -82.21037),
    "Pike": (33.08115, -84.38946),
    "Polk": (33.99602, -85.18834),
    "Pulaski": (32.23880, -83.48185),
    "Putnam": (33.32115, -83.36865),
    "Quitman": (31.86294, -85.00480),
    "Rabun": (34.88393, -83.40487),
    "Randolph": (31.76265, -84.75231),
    "Richmond": (33.36149, -82.07500),
    "Rockdale": (33.65208, -84.02637),
    "Schley": (32.26344, -84.32271),
    "Screven": (32.74475, -81.61758),
    "Seminole": (30.93396, -84.86769),
    "Spalding": (33.26235, -84.28490),
    "Stephens": (34.55358, -83.29059),
    "Stewart": (32.07323, -84.83491),
    "Sumter": (32.04227, -84.20429),
    "Talbot": (32.70460, -84.53003),
    "Taliaferro": (33.55932, -82.87527),
    "Tattnall": (32.04377, -82.05921),
    "Taylor": (32.55467, -84.25143),
    "Telfair": (31.91364, -82.93106),
    "Terrell": (31.77719, -84.43945),
    "Thomas": (30.86460, -83.91990),
    "Tift": (31.45700, -83.52593),
    "Toombs": (32.12193, -82.33066),
    "Towns": (34.90253, -83.73226),
    "Treutlen": (32.40959, -82.57088),
    "Troup": (33.03448, -85.02836),
    "Turner": (31.72480, -83.62032),
    "Twiggs": (32.66585, -83.42588),
    "Union": (34.83333, -83.98926),
    "Upson": (32.88184, -84.29228),
    "Walker": (34.73580, -85.30546),
    "Walton": (33.78389, -83.73183),
    "Ware": (31.05088, -82.42151),
    "Warren": (33.40832, -82.67581),
    "Washington": (32.97184, -82.79811),
    "Wayne": (31.54925, -81.91007),
    "Webster": (32.04669, -84.55383),
    "Wheeler": (32.10526, -82.73385),
    "White": (34.64418, -83.74300),
    "Whitfield": (34.80180, -84.96847),
    "Wilcox": (31.96272, -83.43826),
    "Wilkes": (33.77903, -82.74792),
    "Wilkinson": (32.80427, -83.17551),
    "Worth": (31.55177, -83.84996),
}
# Towns just across each state line, so a dissolve that leaked past the
# border fails the build rather than washing another state. Each was checked
# against TIGERweb's own state layer on 2026-10-29 (Census answer, not a guess
# from a map; controls: Atlanta returns Georgia and a point in the open Gulf
# of Mexico returns no state), and each lies in no feature of the shipped
# state-counties.json: six in Florida, six in Alabama, two in Tennessee, two
# in North Carolina and four in South Carolina. Phenix City, Alabama sits on
# the Chattahoochee's far bank from Columbus, and North Augusta, South
# Carolina on the Savannah's from Augusta, so those two test the river lines
# at their closest. Two keys carry the place's kind ("Chattahoochee town",
# "Jasper city") because the anchor registry reads the word before a comma as
# a county, and Georgia has counties of both names.
OUTSIDE = {
    "Tallahassee, Florida": (30.43830, -84.28070),
    "Chattahoochee town, Florida": (30.70520, -84.84520),
    "Jennings, Florida": (30.60130, -83.10070),
    "Jasper city, Florida": (30.51830, -82.94820),
    "Hilliard, Florida": (30.69110, -81.91730),
    "Fernandina Beach, Florida": (30.66970, -81.46260),
    "Phenix City, Alabama": (32.47100, -85.00080),
    "Lanett, Alabama": (32.86870, -85.19050),
    "Eufaula, Alabama": (31.89130, -85.14550),
    "Heflin, Alabama": (33.64900, -85.58750),
    "Fort Payne, Alabama": (34.44430, -85.71970),
    "Bridgeport, Alabama": (34.94760, -85.71440),
    "Chattanooga, Tennessee": (35.04560, -85.30970),
    "Ducktown, Tennessee": (35.03370, -84.38320),
    "Murphy, North Carolina": (35.08760, -84.03460),
    "Highlands, North Carolina": (35.05260, -83.19680),
    "Westminster, South Carolina": (34.66480, -83.09660),
    "McCormick, South Carolina": (33.91320, -82.29320),
    "North Augusta, South Carolina": (33.50180, -81.96510),
    "Hardeeville, South Carolina": (32.28710, -81.07900),
}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="ga-build-metro-outline")
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
    scale = math.cos(math.radians(32.7))  # Georgia's middle latitude

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

    How many outer rings Georgia's fabric dissolves to is a
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
