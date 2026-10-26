#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds TWO files from Census TIGERweb's county layer, the way Illinois's
builder does (scripts/build_metro_outline.py):

  * data/app/metro-outline.json — the COVERAGE ring: the dissolved outline of
    the counties whose commission or council district lines this app draws
    (METRO_COUNTY_FIPS), where a reader is told which member represents the
    point. The map leaves this ground clear.
  * data/app/mo-state-outline.json — the REGION ring: the dissolved outline of
    all 114 counties and the City of St. Louis (STATE_COUNTY_FIPS), where every
    statewide layer answers and the County card names the whole commission or
    council. The map washes the strip between the two lightly and the key
    says the commission districts are not drawn there yet.

TWO TIERS BY ADAM'S CHOICE OF 2026-10-26 ("Shade the map like IL is
currently"). Until that day this file claimed the whole state as coverage,
because the County card names every county's commission and a narrower wash
greys out ground the app answers for. That is still true, and it is why the
middle band is LIGHT and its key names what is missing (the district lines)
rather than calling the ground uncovered. The two tiers show a reader where the
county's district lines are drawn, which is how this instance comes online:
county by county, as each county's own map proves its lines.

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK WHAT
ANSWERS. METRO_COUNTY_FIPS must be exactly the counties
data/app/mo-commission-counties.json lists (the counties
mo/scripts/build_mo_commission_districts.py draws), and --check and
mo/scripts/validate_index.py both fail when they differ. So a county the
commission builder draws joins this ring in the same change: add its FIPS here
and its INSIDE anchor, move it out of RING_OUTSIDE, and rebuild.
STATE_COUNTY_FIPS must be the 115 the county layer draws and the roster names.

Why this exists: the out-of-scope wash (index.html, ENGINE `scope-mask`)
marks where the app's fullest answer ends. It also keeps a boot cost out —
painting the wash from a live boundary fetch cost the reference fork 669 ms
in PSI's critical chain (docs/OPTIMIZATION_PLAYBOOK.md) before it
pre-built. This file is one small pre-dissolved feature.

WHY A BUILD STEP RATHER THAN TIGERweb's OWN STATE POLYGON (layer 0):
dissolving from the county fabric (layer 1) — rather than fetching the
state layer directly — is what lets this same script draw the coverage ring
as a subset of the same counties from the same fetch. It also
means this file's geometry always agrees with `state-counties.json`'s own
fabric, since both come from the same layer.

The dissolve mirrors the app's `coverageOutlineRings` exactly: a segment
walked by two features is an interior border and is dropped; survivors
chain back into closed rings. READ THE RING COUNT FROM --check, NEVER FROM
A MAP IN YOUR HEAD — this project has got that wrong from a map more than
once. Missouri's eastern border follows the Mississippi River and its
northwestern border the Missouri, whose old channels leave pieces of one
state on the other bank, so the ring count is a measurement the --check line
prints, not a prediction made here.

Missouri borders eight states: Iowa, Illinois, Kentucky, Tennessee, Arkansas
and Oklahoma, which are live, and Kansas and Nebraska, which no instance
serves. OUTSIDE carries towns just over each line to prove the dissolve did
not leak, and the worksheet's negative point is in Kansas, about 57 km west of
the line, where no instance answers today.

Usage:
    python3 mo/scripts/build_metro_outline.py                 # writes both files
    python3 mo/scripts/build_metro_outline.py --check         # verify the shipped file, write nothing
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

# Every Missouri county's 3-digit FIPS, and the City of St. Louis's (510) —
# the REGION ring, where the statewide layers and the County card answer.
# ALL THREE constants below must stay plain literal assignments at module top:
# validate_index.py reads them via ast.literal_eval without importing.
STATE_COUNTY_FIPS = (
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
    "177", "179", "181", "183", "185", "186", "187", "189",
    "195", "197", "199", "201", "203", "205", "207", "209",
    "211", "213", "215", "217", "219", "221", "223", "225",
    "227", "229", "510",
)
# The COVERAGE ring: the counties whose commission or council district lines
# the County Commission District layer draws, exactly the keys of
# data/app/mo-commission-counties.json (30 on 2026-10-26).
METRO_COUNTY_FIPS = (
    "011", "013", "021", "029", "037", "041", "043", "051",
    "053", "057", "063", "089", "093", "109", "113", "119", "125",
    "127", "131", "157", "161", "167", "169", "173", "177",
    "195", "201", "217", "219", "223",
)
STATE_FIPS = "29"
# No dispatch entries: none of this instance's layers is county-dispatched
# (the commission district layer is one statewide layer that hides outside the
# counties it draws).
DISPATCH_COUNTY_FIPS = {}

_UNLISTED = sorted(set(DISPATCH_COUNTY_FIPS.values()) - set(METRO_COUNTY_FIPS))
_NOT_IN_STATE = sorted(set(METRO_COUNTY_FIPS) - set(STATE_COUNTY_FIPS))
assert not _NOT_IN_STATE, "METRO_COUNTY_FIPS names %s, outside STATE_COUNTY_FIPS" % _NOT_IN_STATE
assert not _UNLISTED, (
    "DISPATCH_COUNTY_FIPS names county FIPS %s that METRO_COUNTY_FIPS omits — a "
    "county cannot be served and outside the coverage ring at the same time"
    % _UNLISTED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "metro-outline.json")
STATE_OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "mo-state-outline.json")
COMMISSION_COUNTIES = os.path.join(REPO_ROOT, "data", "app", "mo-commission-counties.json")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/mo/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One STATE_INSIDE anchor per county: the Census Bureau's own internal point for the
# county (INTPTLAT/INTPTLON on TIGERweb State_County layer 1), which the
# Census places inside the county by construction. Each was still verified
# interior against that county's own SIMPLIFIED rings in the shipped
# state-counties.json, and inside no other county, before being trusted here —
# ring closure alone is not proof a dissolve kept every county. All 115 passed
# when this table was generated, 2026-10-21. "St. Louis" is the county and
# "St. Louis City" the independent city.
STATE_INSIDE = {
    "Adair": (40.19067, -92.60359),
    "Andrew": (39.98886, -94.80355),
    "Atchison": (40.43185, -95.43755),
    "Audrain": (39.21448, -91.84342),
    "Barry": (36.69938, -93.83433),
    "Barton": (37.50091, -94.34406),
    "Bates": (38.25722, -94.33925),
    "Benton": (38.30104, -93.28794),
    "Bollinger": (37.32012, -90.02699),
    "Boone": (38.98986, -92.31020),
    "Buchanan": (39.66037, -94.80817),
    "Butler": (36.71518, -90.40313),
    "Caldwell": (39.65900, -93.97918),
    "Callaway": (38.83555, -91.92345),
    "Camden": (38.02650, -92.76533),
    "Cape Girardeau": (37.38414, -89.68566),
    "Carroll": (39.42738, -93.50023),
    "Carter": (36.94486, -90.94571),
    "Cass": (38.64647, -94.35455),
    "Cedar": (37.73365, -93.85001),
    "Chariton": (39.51797, -92.96162),
    "Christian": (36.96974, -93.18761),
    "Clark": (40.40727, -91.72947),
    "Clay": (39.31555, -94.42150),
    "Clinton": (39.60882, -94.39561),
    "Cole": (38.50323, -92.28003),
    "Cooper": (38.84709, -92.81007),
    "Crawford": (37.96656, -91.31394),
    "Dade": (37.43235, -93.85488),
    "Dallas": (37.68358, -93.03381),
    "Daviess": (39.96284, -93.97005),
    "DeKalb": (39.89466, -94.40719),
    "Dent": (37.60307, -91.48972),
    "Douglas": (36.94652, -92.51589),
    "Dunklin": (36.15302, -90.06225),
    "Franklin": (38.41300, -91.07283),
    "Gasconade": (38.44118, -91.50578),
    "Gentry": (40.20813, -94.40532),
    "Greene": (37.25820, -93.34064),
    "Grundy": (40.11254, -93.56505),
    "Harrison": (40.34568, -93.99247),
    "Henry": (38.38649, -93.79263),
    "Hickory": (37.93691, -93.32299),
    "Holt": (40.09572, -95.21907),
    "Howard": (39.14337, -92.69593),
    "Howell": (36.77437, -91.88737),
    "Iron": (37.62597, -90.69959),
    "Jackson": (39.00579, -94.34300),
    "Jasper": (37.20520, -94.33726),
    "Jefferson": (38.25763, -90.54369),
    "Johnson": (38.74153, -93.81187),
    "Knox": (40.13686, -92.14683),
    "Laclede": (37.65970, -92.59484),
    "Lafayette": (39.06871, -93.80264),
    "Lawrence": (37.10652, -93.83003),
    "Lewis": (40.08456, -91.72880),
    "Lincoln": (39.06226, -90.96292),
    "Linn": (39.86444, -93.10802),
    "Livingston": (39.77852, -93.54820),
    "Macon": (39.82979, -92.56434),
    "Madison": (37.47448, -90.34341),
    "Maries": (38.16262, -91.92360),
    "Marion": (39.80754, -91.63538),
    "McDonald": (36.62281, -94.35225),
    "Mercer": (40.42141, -93.56763),
    "Miller": (38.21668, -92.42988),
    "Mississippi": (36.82626, -89.29593),
    "Moniteau": (38.63304, -92.58364),
    "Monroe": (39.49827, -92.00646),
    "Montgomery": (38.93518, -91.46543),
    "Morgan": (38.42102, -92.87489),
    "New Madrid": (36.59426, -89.65595),
    "Newton": (36.90837, -94.33503),
    "Nodaway": (40.36114, -94.88315),
    "Oregon": (36.68531, -91.40183),
    "Osage": (38.46425, -91.85950),
    "Ozark": (36.64959, -92.45855),
    "Pemiscot": (36.20992, -89.78594),
    "Perry": (37.71113, -89.80212),
    "Pettis": (38.72401, -93.29270),
    "Phelps": (37.86633, -91.79035),
    "Pike": (39.34014, -91.17128),
    "Platte": (39.37868, -94.76149),
    "Polk": (37.61676, -93.40082),
    "Pulaski": (37.82483, -92.20702),
    "Putnam": (40.47861, -93.01453),
    "Ralls": (39.55346, -91.52479),
    "Randolph": (39.43925, -92.49296),
    "Ray": (39.30840, -93.99575),
    "Reynolds": (37.36646, -90.97228),
    "Ripley": (36.64553, -90.86914),
    "Saline": (39.13584, -93.20416),
    "Schuyler": (40.46936, -92.51902),
    "Scotland": (40.44769, -92.14282),
    "Scott": (37.04779, -89.56810),
    "Shannon": (37.15250, -91.39133),
    "Shelby": (39.79753, -92.08872),
    "St. Charles": (38.78110, -90.67492),
    "St. Clair": (38.04219, -93.77730),
    "St. Francois": (37.80726, -90.47195),
    "St. Louis": (38.64044, -90.44550),
    "St. Louis City": (38.63570, -90.24458),
    "Ste. Genevieve": (37.88584, -90.16153),
    "Stoddard": (36.85156, -89.94748),
    "Stone": (36.74582, -93.45784),
    "Sullivan": (40.20959, -93.10978),
    "Taney": (36.64983, -93.04282),
    "Texas": (37.31426, -91.96448),
    "Vernon": (37.85023, -94.34170),
    "Warren": (38.76190, -91.15931),
    "Washington": (37.94261, -90.89702),
    "Wayne": (37.11382, -90.45654),
    "Webster": (37.28080, -92.87608),
    "Worth": (40.48050, -94.41920),
    "Wright": (37.26763, -92.47999),
}
# Towns just across each state line, so a dissolve that leaked past the
# border fails the build rather than washing another state. Each was checked
# against TIGERweb's own state layer on 2026-10-21 (Census answer, not a guess
# from a map; controls: Jefferson City returns Missouri and a point in the
# open Gulf of Mexico returns no state), and each lies in no feature of the
# shipped state-counties.json: three in Iowa, five across the Mississippi in
# Illinois, two in Kentucky, one in Tennessee, four in Arkansas, one in
# Oklahoma, five in Kansas and two in Nebraska.
STATE_OUTSIDE = {
    "Keokuk, Iowa": (40.39700, -91.38490),
    "Lamoni, Iowa": (40.62280, -93.93300),
    "Shenandoah, Iowa": (40.76550, -95.37220),
    "Quincy, Illinois": (39.93560, -91.40990),
    "Alton, Illinois": (38.89060, -90.18430),
    "East St. Louis, Illinois": (38.62450, -90.15100),
    "Chester, Illinois": (37.91370, -89.82210),
    "Cairo, Illinois": (37.00530, -89.17650),
    "Wickliffe, Kentucky": (36.96450, -89.08900),
    "Hickman, Kentucky": (36.57120, -89.18620),
    "Tiptonville, Tennessee": (36.37840, -89.47810),
    "Blytheville, Arkansas": (35.92730, -89.91900),
    "Piggott, Arkansas": (36.38290, -90.19070),
    "Mammoth Spring, Arkansas": (36.49560, -91.54040),
    "Bentonville, Arkansas": (36.37290, -94.20880),
    "Miami, Oklahoma": (36.87450, -94.87750),
    "Baxter Springs, Kansas": (37.02370, -94.73550),
    "Pittsburg, Kansas": (37.41090, -94.70470),
    "Fort Scott, Kansas": (37.83980, -94.70830),
    "Kansas City, Kansas": (39.11420, -94.62750),
    "Troy, Kansas": (39.78360, -95.08940),
    "Falls City, Nebraska": (40.06060, -95.60190),
    "Nebraska City, Nebraska": (40.67640, -95.85970),
}

# The coverage ring's anchors, from the same table: each drawn county's own
# internal point is INSIDE the ring, and every other county's, with every
# town over the state line, is OUTSIDE it. So the ring is proven to hold each
# county it claims and none it does not, and the count identity in
# check_anchor_registry still reads one INSIDE anchor per served county.
RING_COUNTIES = (
    "Barton",
    "Bates",
    "Buchanan",
    "Camden",
    "Cass",
    "Chariton",
    "Christian",
    "Cole",
    "Cooper",
    "Dade",
    "DeKalb",
    "Howard",
    "Iron",
    "Lawrence",
    "Lincoln",
    "Maries",
    "Marion",
    "McDonald",
    "Miller",
    "Perry",
    "Phelps",
    "Polk",
    "Pulaski",
    "Ralls",
    "Ray",
    "Saline",
    "Scott",
    "Vernon",
    "Warren",
    "Wayne",
)
INSIDE = {name: STATE_INSIDE[name] for name in RING_COUNTIES}
OUTSIDE = dict(STATE_OUTSIDE)
OUTSIDE.update({name + ", not drawn": STATE_INSIDE[name]
                for name in STATE_INSIDE if name not in RING_COUNTIES})


def fetch_counties():
    """All 115 county features; the ring is dissolved from the subset."""
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in STATE_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="mo-build-metro-outline")
    resp = requests.get(TIGERWEB, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": where,
        "outFields": "NAME,GEOID",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if len(feats) != len(STATE_COUNTY_FIPS):
        print("FATAL: TIGERweb returned %d counties, expected %d — the query or the "
              "service changed" % (len(feats), len(STATE_COUNTY_FIPS)), file=sys.stderr)
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
    scale = math.cos(math.radians(38.3))  # Missouri's middle latitude

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


def validate(rings, inside=None, outside=None, what="the metro outline"):
    inside = INSIDE if inside is None else inside
    outside = OUTSIDE if outside is None else outside
    problems = []
    for label, (lat, lng) in sorted(inside.items()):
        if not point_in_rings(lat, lng, rings):
            problems.append("%s should be INSIDE %s and is not" % (label, what))
    for label, (lat, lng) in sorted(outside.items()):
        if point_in_rings(lat, lng, rings):
            problems.append("%s should be OUTSIDE %s and is not" % (label, what))
    return problems


def validate_state(rings):
    return validate(rings, STATE_INSIDE, STATE_OUTSIDE, "the state outline")


def check_commission_counties():
    """The ring claims exactly the counties the commission district layer
    draws: METRO_COUNTY_FIPS and RING_COUNTIES against
    data/app/mo-commission-counties.json, offline."""
    try:
        with open(COMMISSION_COUNTIES, encoding="utf-8") as f:
            drawn = json.load(f)
    except (IOError, ValueError) as exc:
        return ["could not read mo-commission-counties.json (%s)" % exc]
    problems = []
    fips = {k[2:] for k in drawn}
    if fips != set(METRO_COUNTY_FIPS):
        problems.append(
            "METRO_COUNTY_FIPS and mo-commission-counties.json disagree: drawn and "
            "not in the ring %s, in the ring and not drawn %s. A county the "
            "commission builder draws joins the ring in the same change."
            % (sorted(fips - set(METRO_COUNTY_FIPS)) or "none",
               sorted(set(METRO_COUNTY_FIPS) - fips) or "none"))
    names = {(v.get("county") or "").replace(" County", "") for v in drawn.values()}
    if names != set(RING_COUNTIES):
        problems.append(
            "RING_COUNTIES and mo-commission-counties.json name different counties: "
            "%s against %s" % (sorted(set(RING_COUNTIES) - names), sorted(names - set(RING_COUNTIES))))
    return problems


def group_rings(rings):
    """Nest each ring under the ring that encloses it — outers, then their holes.

    How many outer rings Missouri's fabric dissolves to is a
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


def build_geojson(rings, name=None):
    polys = group_rings(rings)
    geometry = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                else {"type": "MultiPolygon", "coordinates": polys})
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": name or ("%d-county coverage area" % len(METRO_COUNTY_FIPS))},
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
    ap.add_argument("--state-out", default=STATE_OUT_PATH)
    ap.add_argument("--check", action="store_true",
                    help="validate the shipped files instead of rebuilding")
    args = ap.parse_args()

    if args.check:
        with open(args.out) as f:
            shipped = json.load(f)
        with open(args.state_out) as f:
            shipped_state = json.load(f)
        # rings_of() flattens Polygon and MultiPolygon alike, so the anchor test
        # reads the file the same way whether or not the served area is one region.
        rings = rings_of(shipped["features"][0])
        state_rings = rings_of(shipped_state["features"][0])
        problems = (check_anchor_registry() + check_commission_counties()
                    + validate(rings) + validate_state(state_rings)
                    + check_envelopes(state_rings))
        for p in problems:
            print("FAIL: %s" % p, file=sys.stderr)
        if problems:
            sys.exit(1)
        print("metro-outline: OK — %d ring(s), %d vertices, all %d inside / %d outside "
              "anchors correct" % (len(rings), sum(len(r) for r in rings),
                                   len(INSIDE), len(OUTSIDE)), file=sys.stderr)
        print("mo-state-outline: OK — %d ring(s), %d vertices, all %d inside / %d outside "
              "anchors correct" % (len(state_rings), sum(len(r) for r in state_rings),
                                   len(STATE_INSIDE), len(STATE_OUTSIDE)), file=sys.stderr)
        return

    feats = fetch_counties()
    ring_feats = [f for f in feats
                  if str((f.get("properties") or {}).get("GEOID", ""))[-3:] in METRO_COUNTY_FIPS]
    if len(ring_feats) != len(METRO_COUNTY_FIPS):
        print("FATAL: %d of the %d ring counties came back" % (len(ring_feats), len(METRO_COUNTY_FIPS)),
              file=sys.stderr)
        sys.exit(1)
    rings = [simplify(r) for r in dissolve(ring_feats)]
    state_rings = [simplify(r) for r in dissolve(feats)]
    problems = (check_anchor_registry() + check_commission_counties()
                + validate(rings) + validate_state(state_rings)
                + check_envelopes(state_rings))
    for p in problems:
        print("FATAL: %s" % p, file=sys.stderr)
    if problems:
        print("FATAL: refusing to write an outline that misplaces its anchors",
              file=sys.stderr)
        sys.exit(1)

    for path, rr, name in ((args.out, rings, None),
                           (args.state_out, state_rings, "Missouri (all 115 counties)")):
        with open(path, "w") as f:
            json.dump(build_geojson(rr, name), f, separators=(",", ":"))
            f.write("\n")
        size = os.path.getsize(path)
        print("wrote %s: %d ring(s), %d vertices, %.1f KB"
              % (path, len(rr), sum(len(r) for r in rr), size / 1024.0),
              file=sys.stderr)


if __name__ == "__main__":
    main()
