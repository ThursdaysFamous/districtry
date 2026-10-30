#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for Virginia, the dissolved outline of
the WHOLE STATE, since coverage is statewide from day one — from Census
TIGERweb. Unlike Wisconsin's narrower "roster-covered" ring, this wash makes
no partial claim: METRO_COUNTY_FIPS is all 95 counties and all 38 independent
cities (county equivalents, 510 to 840), and DISPATCH_COUNTY_FIPS stays empty
on purpose — this instance has no per-county dispatch layers.

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK WHAT
ANSWERS. Every statewide layer answers in all 133 counties and cities, so the
wash claims the whole state. If a layer is ever built that answers in only
some of them and the map should say so, narrow METRO_COUNTY_FIPS to what
actually answers, following `wi/scripts/build_metro_outline.py` (or
Missouri's two-output builder) rather than inventing a new shape.

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
once. Virginia's Eastern Shore is separated from the rest of the state by
the Chesapeake Bay, which TIGER's county fabric assigns to the counties and
cities on its shores, and its Potomac border runs along the Maryland bank,
so the ring count is a measurement the --check line prints, not a
prediction made here.

Virginia borders North Carolina, Tennessee and Kentucky, which are live, and
West Virginia, Maryland and the District of Columbia, which no instance
serves. OUTSIDE carries towns just over each line to prove the dissolve did
not leak, and the worksheet's negative point is in the open Atlantic east of
Cape Charles, where no state answers.

Usage:
    python3 va/scripts/build_metro_outline.py                 # writes data/app/metro-outline.json
    python3 va/scripts/build_metro_outline.py --check         # verify the shipped file, write nothing
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

# Every Virginia county's 3-digit FIPS (001 to 199) and every independent
# city's (510 to 840) — the served area IS the whole state.
# BOTH constants below must stay plain literal assignments at module top:
# validate_index.py reads them via ast.literal_eval without importing.
METRO_COUNTY_FIPS = (
    "001", "003", "005", "007", "009", "011", "013", "015",
    "017", "019", "021", "023", "025", "027", "029", "031",
    "033", "035", "036", "037", "041", "043", "045", "047",
    "049", "051", "053", "057", "059", "061", "063", "065",
    "067", "069", "071", "073", "075", "077", "079", "081",
    "083", "085", "087", "089", "091", "093", "095", "097",
    "099", "101", "103", "105", "107", "109", "111", "113",
    "115", "117", "119", "121", "125", "127", "131", "133",
    "135", "137", "139", "141", "143", "145", "147", "149",
    "153", "155", "157", "159", "161", "163", "165", "167",
    "169", "171", "173", "175", "177", "179", "181", "183",
    "185", "187", "191", "193", "195", "197", "199", "510",
    "520", "530", "540", "550", "570", "580", "590", "595",
    "600", "610", "620", "630", "640", "650", "660", "670",
    "678", "680", "683", "685", "690", "700", "710", "720",
    "730", "735", "740", "750", "760", "770", "775", "790",
    "800", "810", "820", "830", "840",
)
STATE_FIPS = "51"
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

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/va/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One INSIDE anchor per county or city: the Census Bureau's own internal point
# for it (INTPTLAT/INTPTLON on TIGERweb State_County layer 1), which the
# Census places inside it by construction. Each was still verified interior
# against its own SIMPLIFIED rings in the shipped state-counties.json, and
# inside no other county or city, before being trusted here — ring closure
# alone is not proof a dissolve kept every county. All 133 passed when this
# table was generated, 2026-10-29. A county is keyed by its name and an
# independent city by its name with "City" ("Richmond" is the county and
# "Richmond City" the city; likewise Fairfax, Franklin and Roanoke).
INSIDE = {
    "Accomack": (37.76349, -75.75496),
    "Albemarle": (38.02418, -78.55351),
    "Alexandria City": (38.81881, -77.08323),
    "Alleghany": (37.78790, -80.00867),
    "Amelia": (37.33193, -77.97746),
    "Amherst": (37.62930, -79.15476),
    "Appomattox": (37.37073, -78.81094),
    "Arlington": (38.87834, -77.10070),
    "Augusta": (38.17264, -79.14079),
    "Bath": (38.06837, -79.73120),
    "Bedford": (37.31268, -79.52686),
    "Bland": (37.13061, -81.12585),
    "Botetourt": (37.56544, -79.79755),
    "Bristol City": (36.61721, -82.15755),
    "Brunswick": (36.76420, -77.86148),
    "Buchanan": (37.26812, -82.03815),
    "Buckingham": (37.57393, -78.52917),
    "Buena Vista City": (37.72940, -79.35809),
    "Campbell": (37.21015, -79.09543),
    "Caroline": (38.02803, -77.35374),
    "Carroll": (36.73200, -80.72782),
    "Charles City": (37.36105, -77.05417),
    "Charlotte": (37.00904, -78.65857),
    "Charlottesville City": (38.03766, -78.48538),
    "Chesapeake City": (36.67938, -76.30179),
    "Chesterfield": (37.37843, -77.58585),
    "Clarke": (39.11505, -77.99060),
    "Colonial Heights City": (37.26168, -77.39680),
    "Covington City": (37.78106, -79.98543),
    "Craig": (37.44714, -80.29018),
    "Culpeper": (38.48593, -77.95648),
    "Cumberland": (37.52019, -78.25284),
    "Danville City": (36.58175, -79.40826),
    "Dickenson": (37.13670, -82.34922),
    "Dinwiddie": (37.07350, -77.63549),
    "Emporia City": (36.69618, -77.53598),
    "Essex": (37.93547, -76.92790),
    "Fairfax": (38.82952, -77.27325),
    "Fairfax City": (38.85318, -77.29903),
    "Falls Church City": (38.88472, -77.17560),
    "Fauquier": (38.74410, -77.82150),
    "Floyd": (36.93143, -80.35027),
    "Fluvanna": (37.83074, -78.28338),
    "Franklin": (36.98923, -79.88305),
    "Franklin City": (36.68401, -76.94140),
    "Frederick": (39.20032, -78.26961),
    "Fredericksburg City": (38.29927, -77.48666),
    "Galax City": (36.66564, -80.91431),
    "Giles": (37.31457, -80.70704),
    "Gloucester": (37.40400, -76.52308),
    "Goochland": (37.71881, -77.91763),
    "Grayson": (36.65237, -81.21579),
    "Greene": (38.29798, -78.47016),
    "Greensville": (36.68034, -77.56028),
    "Halifax": (36.76646, -78.93961),
    "Hampton City": (37.04796, -76.29729),
    "Hanover": (37.76021, -77.49132),
    "Harrisonburg City": (38.43625, -78.87330),
    "Henrico": (37.43752, -77.30033),
    "Henry": (36.62061, -79.98066),
    "Highland": (38.36624, -79.56447),
    "Hopewell City": (37.29101, -77.29894),
    "Isle of Wight": (36.90142, -76.70757),
    "James City": (37.32484, -76.77789),
    "King George": (38.27700, -77.16283),
    "King William": (37.70826, -77.09105),
    "King and Queen": (37.71777, -76.90558),
    "Lancaster": (37.70484, -76.41265),
    "Lee": (36.70172, -83.13011),
    "Lexington City": (37.78233, -79.44432),
    "Loudoun": (39.08120, -77.63890),
    "Louisa": (37.97270, -77.95979),
    "Lunenburg": (36.94555, -78.24053),
    "Lynchburg City": (37.39907, -79.19529),
    "Madison": (38.41206, -78.27696),
    "Manassas City": (38.74681, -77.48263),
    "Manassas Park City": (38.76942, -77.44026),
    "Martinsville City": (36.68353, -79.86365),
    "Mathews": (37.42930, -76.26379),
    "Mecklenburg": (36.68726, -78.36896),
    "Middlesex": (37.60678, -76.52011),
    "Montgomery": (37.17610, -80.38849),
    "Nelson": (37.78959, -78.88312),
    "New Kent": (37.50857, -76.99883),
    "Newport News City": (37.07646, -76.52064),
    "Norfolk City": (36.92301, -76.24464),
    "Northampton": (37.31171, -75.92014),
    "Northumberland": (37.85773, -76.39001),
    "Norton City": (36.93155, -82.62600),
    "Nottoway": (37.14103, -78.05399),
    "Orange": (38.24933, -78.01109),
    "Page": (38.62321, -78.49187),
    "Patrick": (36.66723, -80.28637),
    "Petersburg City": (37.20473, -77.39237),
    "Pittsylvania": (36.82172, -79.39850),
    "Poquoson City": (37.12836, -76.30353),
    "Portsmouth City": (36.86385, -76.36237),
    "Powhatan": (37.54940, -77.91286),
    "Prince Edward": (37.22488, -78.43296),
    "Prince George": (37.18733, -77.22099),
    "Prince William": (38.70112, -77.47958),
    "Pulaski": (37.06339, -80.71344),
    "Radford City": (37.12012, -80.55915),
    "Rappahannock": (38.68452, -78.16826),
    "Richmond": (37.94289, -76.73056),
    "Richmond City": (37.53140, -77.47601),
    "Roanoke": (37.33079, -80.19124),
    "Roanoke City": (37.27846, -79.95817),
    "Rockbridge": (37.81452, -79.44775),
    "Rockingham": (38.50761, -78.88533),
    "Russell": (36.93066, -82.09283),
    "Salem City": (37.28533, -80.05524),
    "Scott": (36.71278, -82.61362),
    "Shenandoah": (38.85620, -78.57399),
    "Smyth": (36.84205, -81.53965),
    "Southampton": (36.72007, -77.10381),
    "Spotsylvania": (38.18243, -77.65723),
    "Stafford": (38.42308, -77.45805),
    "Staunton City": (38.15798, -79.06188),
    "Suffolk City": (36.69716, -76.63478),
    "Surry": (37.11976, -76.88017),
    "Sussex": (36.92665, -77.25973),
    "Tazewell": (37.12539, -81.56292),
    "Virginia Beach City": (36.77911, -76.02845),
    "Warren": (38.90822, -78.20759),
    "Washington": (36.74780, -81.95033),
    "Waynesboro City": (38.06716, -78.90142),
    "Westmoreland": (38.10931, -76.80393),
    "Williamsburg City": (37.26895, -76.70866),
    "Winchester City": (39.17387, -78.17636),
    "Wise": (36.97456, -82.62156),
    "Wythe": (36.89988, -81.08303),
    "York": (37.22091, -76.39553),
}
# Towns just across each state line, so a dissolve that leaked past the
# border fails the build rather than washing another state. Each was checked
# against TIGERweb's own state layer on 2026-10-29 (Census answer, not a guess
# from a map; controls: the worksheet's anchor at the State Capitol is inside
# its own county, and the open-Atlantic point returns no state), and each lies
# in no feature of the shipped state-counties.json: three in Tennessee, two in
# Kentucky, seven in West Virginia, five in Maryland, the District of
# Columbia, eight in North Carolina and the worksheet's negative point.
OUTSIDE = {
    "Bristol, Tennessee": (36.57300, -82.18800),
    "Kingsport, Tennessee": (36.54840, -82.56180),
    "Cumberland Gap, Tennessee": (36.59600, -83.66600),
    "Middlesboro, Kentucky": (36.60840, -83.71660),
    "Elkhorn City, Kentucky": (37.30400, -82.35100),
    "Williamson, West Virginia": (37.67400, -82.27700),
    "Bluefield, West Virginia": (37.26960, -81.22230),
    "White Sulphur Springs, West Virginia": (37.79650, -80.29760),
    "Pendleton County seat, Franklin, West Virginia": (38.64340, -79.33170),
    "Romney, West Virginia": (39.34200, -78.75700),
    "Martinsburg, West Virginia": (39.45620, -77.96390),
    "Harpers Ferry, West Virginia": (39.32540, -77.73890),
    "Point of Rocks, Maryland": (39.27600, -77.53900),
    "Bethesda, Maryland": (38.98470, -77.09470),
    "the White House, Washington, District of Columbia": (38.89770, -77.03650),
    "Oxon Hill, Maryland": (38.80340, -76.98970),
    "Pocomoke City, Maryland": (38.07570, -75.56800),
    "Ocean City, Maryland": (38.33650, -75.08490),
    "Corolla, North Carolina": (36.37800, -75.83000),
    "Moyock, North Carolina": (36.52400, -76.17800),
    "Murfreesboro, North Carolina": (36.44260, -77.09830),
    "Roanoke Rapids, North Carolina": (36.46130, -77.65420),
    "Roxboro, North Carolina": (36.39380, -78.98280),
    "Eden, North Carolina": (36.48820, -79.76640),
    "Mount Airy, North Carolina": (36.49930, -80.60730),
    "Sparta, North Carolina": (36.50540, -81.12070),
    "the open Atlantic east of Cape Charles": (37.00000, -75.30000),
}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="va-build-metro-outline")
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
    scale = math.cos(math.radians(38.0))  # Virginia's middle latitude

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

    How many outer rings Virginia's fabric dissolves to is a
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
