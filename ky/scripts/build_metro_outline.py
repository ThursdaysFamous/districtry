#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for Kentucky, the dissolved outline of the
WHOLE STATE, since coverage is statewide from day one — from Census
TIGERweb. Unlike Wisconsin's narrower "roster-covered" ring, Kentucky's wash
makes no partial claim yet: METRO_COUNTY_FIPS is all 87 counties, and
DISPATCH_COUNTY_FIPS stays empty on purpose — this instance has no
per-county dispatch layers (none of its four layers are county-keyed).

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK THE
ROSTER. When a future layer becomes county-keyed (e.g. `county-supervisor`
answering only where a plan is confirmed), narrow METRO_COUNTY_FIPS to what
actually answers and add DISPATCH_COUNTY_FIPS entries — following the
Wisconsin precedent (`wi/scripts/build_metro_outline.py`) rather than
inventing a new shape. Until then, the outline is simply Kentucky's border.

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
chain back into closed rings. Kentucky's 120 counties dissolve to a single
ring (a state with no islands or enclaves) — verified by the county-count
assertion in `fetch_counties()`, not assumed.

Usage:
    python3 build_metro_outline.py                 # writes data/app/metro-outline.json
    python3 build_metro_outline.py --check         # verify the shipped file, write nothing
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
# point_in_rings) are shared machinery other Kentucky builders could import
# rather than fork, matching the Wisconsin precedent's reasoning.

TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "State_County/MapServer/1/query")

# Every Kentucky county's 3-digit FIPS — the served area IS the whole state.
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
)
STATE_FIPS = "21"
# No dispatch entries: none of Kentucky's four layers are county-keyed yet.
DISPATCH_COUNTY_FIPS = {}

_UNLISTED = sorted(set(DISPATCH_COUNTY_FIPS.values()) - set(METRO_COUNTY_FIPS))
assert not _UNLISTED, (
    "DISPATCH_COUNTY_FIPS names county FIPS %s that METRO_COUNTY_FIPS omits — a "
    "county cannot be served and outside the coverage ring at the same time"
    % _UNLISTED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "metro-outline.json")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/ky/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One INSIDE anchor per county (area-weighted polygon centroid, verified
# interior against that county's own rings before being trusted here) —
# ring closure alone is not proof a dissolve kept every county. No OUTSIDE
# anchors: every Kentucky county is served, so there is no unserved neighbour
# to prove excluded (the negative point in metro-worksheet.json, in Sumner
# County, Tennessee, covers "clearly outside the state" instead).
#
# THE ANCHORS ARE INTERIOR POINTS, NOT CENTROIDS, and the difference matters in
# this state. Kentucky's western counties along the Mississippi and its eastern
# counties in the Appalachian folds are long and curved, and a county's
# area-weighted centroid can fall outside its own rings. Each point here was
# produced by a horizontal-scanline search — the midpoint of the widest span of
# county interior across forty latitudes — and then verified point-in-polygon
# against that county's own geometry before being written down. A centroid that
# happened to land outside would make this gate fail on a correct dissolve.
INSIDE = {
    "Adair": (37.10899, -85.3155),
    "Allen": (36.65921, -86.18147),
    "Anderson": (37.97019, -84.98205),
    "Ballard": (37.0256, -89.01388),
    "Barren": (36.93509, -85.95594),
    "Bath": (38.17089, -83.77806),
    "Bell": (36.67589, -83.67421),
    "Boone": (39.05512, -84.75923),
    "Bourbon": (38.21177, -84.20847),
    "Boyd": (38.37701, -82.7047),
    "Boyle": (37.62931, -84.84298),
    "Bracken": (38.76494, -84.06684),
    "Breathitt": (37.53351, -83.28412),
    "Breckinridge": (37.79008, -86.4167),
    "Bullitt": (37.99338, -85.71177),
    "Butler": (37.19744, -86.65771),
    "Caldwell": (37.18652, -87.90753),
    "Calloway": (36.54145, -88.26052),
    "Campbell": (38.87692, -84.33938),
    "Carlisle": (36.81281, -88.99631),
    "Carroll": (38.66172, -85.09953),
    "Carter": (38.31123, -83.06128),
    "Casey": (37.31554, -84.93492),
    "Christian": (37.00267, -87.50195),
    "Clark": (37.93179, -84.15343),
    "Clay": (37.20034, -83.72639),
    "Clinton": (36.62909, -85.14714),
    "Crittenden": (37.36824, -88.06355),
    "Cumberland": (36.85028, -85.40176),
    "Daviess": (37.68088, -87.11473),
    "Edmonson": (37.2186, -86.23733),
    "Elliott": (38.11142, -83.07826),
    "Estill": (37.72123, -83.91055),
    "Fayette": (38.0192, -84.46989),
    "Fleming": (38.38361, -83.68882),
    "Floyd": (37.68561, -82.75441),
    "Franklin": (38.19896, -84.86554),
    "Fulton": (36.51037, -89.12718),
    "Gallatin": (38.77072, -84.86518),
    "Garrard": (37.70508, -84.60545),
    "Grant": (38.62175, -84.6351),
    "Graves": (36.75744, -88.65251),
    "Grayson": (37.49471, -86.35001),
    "Green": (37.19098, -85.51997),
    "Greenup": (38.50784, -82.91755),
    "Hancock": (37.88749, -86.77887),
    "Hardin": (37.72269, -85.94212),
    "Harlan": (36.87864, -83.20213),
    "Harrison": (38.46797, -84.32638),
    "Hart": (37.32931, -85.92225),
    "Henderson": (37.78159, -87.55092),
    "Henry": (38.41396, -85.10425),
    "Hickman": (36.72362, -89.00972),
    "Hopkins": (37.32605, -87.59201),
    "Jackson": (37.34154, -83.96251),
    "Jefferson": (38.16, -85.66493),
    "Jessamine": (37.86615, -84.57198),
    "Johnson": (37.88159, -82.80402),
    "Kenton": (38.81333, -84.51531),
    "Knott": (37.28743, -82.91774),
    "Knox": (36.93558, -83.82679),
    "Larue": (37.48407, -85.67976),
    "Laurel": (37.05815, -84.09466),
    "Lawrence": (38.00594, -82.76854),
    "Lee": (37.54517, -83.7339),
    "Leslie": (37.09096, -83.35776),
    "Letcher": (37.16963, -82.82108),
    "Lewis": (38.59319, -83.35032),
    "Lincoln": (37.47955, -84.65379),
    "Livingston": (37.25904, -88.35925),
    "Logan": (36.89057, -86.83596),
    "Lyon": (36.96875, -88.05744),
    "Madison": (37.7667, -84.29754),
    "Magoffin": (37.71101, -83.10145),
    "Marion": (37.55542, -85.27967),
    "Marshall": (36.75424, -88.29989),
    "Martin": (37.7569, -82.48853),
    "Mason": (38.59667, -83.80891),
    "McCracken": (37.02095, -88.66394),
    "McCreary": (36.61026, -84.5058),
    "McLean": (37.56232, -87.2056),
    "Meade": (37.94886, -86.17099),
    "Menifee": (37.98067, -83.60714),
    "Mercer": (37.74438, -84.85294),
    "Metcalfe": (36.95468, -85.59469),
    "Monroe": (36.6319, -85.70922),
    "Montgomery": (38.00964, -83.88754),
    "Morgan": (37.90399, -83.22338),
    "Muhlenberg": (37.21891, -87.12548),
    "Nelson": (37.79188, -85.52699),
    "Nicholas": (38.31966, -83.99034),
    "Ohio": (37.39622, -86.85464),
    "Oldham": (38.38081, -85.47004),
    "Owen": (38.52192, -84.838),
    "Owsley": (37.46284, -83.71338),
    "Pendleton": (38.78847, -84.38145),
    "Perry": (37.33061, -83.32426),
    "Pike": (37.52548, -82.30389),
    "Powell": (37.85228, -83.84047),
    "Pulaski": (37.09922, -84.59301),
    "Robertson": (38.49216, -84.05197),
    "Rockcastle": (37.34581, -84.31524),
    "Rowan": (38.1593, -83.4168),
    "Russell": (36.99771, -85.02047),
    "Scott": (38.20631, -84.56789),
    "Shelby": (38.28576, -85.22601),
    "Simpson": (36.65851, -86.58721),
    "Spencer": (38.03326, -85.30315),
    "Taylor": (37.41032, -85.31398),
    "Todd": (36.65251, -87.19742),
    "Trigg": (36.86375, -87.91382),
    "Trimble": (38.57819, -85.3005),
    "Union": (37.6426, -87.9479),
    "Warren": (37.05599, -86.38407),
    "Washington": (37.7311, -85.20775),
    "Wayne": (36.84974, -84.8233),
    "Webster": (37.5659, -87.60088),
    "Whitley": (36.68402, -84.09469),
    "Wolfe": (37.70408, -83.46583),
    "Woodford": (38.10832, -84.74612),
}

# DETACHED PARTS a county's own anchor cannot reach, one entry per part, each
# with the reason it needs one. These are tested exactly as INSIDE is, and they
# are kept SEPARATE from it so the one-anchor-per-county identity above stays
# exact — that identity is what catches a county added to METRO_COUNTY_FIPS with
# no anchor, and a second anchor sitting in INSIDE would make a doubled county
# and a missing one look the same.
#
# Kentucky has exactly one: the Kentucky Bend, the piece of Fulton County the
# Mississippi loops around, enclosed by Missouri and Tennessee and reachable by
# road only through Tennessee. Fulton's own anchor is on the mainland, so without
# this entry the dissolve could drop the exclave and every gate would stay green.
# TIGERweb names this point Fulton County, STATE 21 (measured 2026-09-30).
#
# THE KEY SHAPE IS "County, part" AND NOT "part (County)". county_of() reads a
# PARENTHETICAL as the county — "Marion (Williamson)" is the city of Marion
# vouching for Williamson County — so "Fulton (Kentucky Bend)" made the gate look
# for a county called Kentucky Bend and refuse the build. It reads a comma as a
# qualifier on the county named first, which is the shape this needs.
INSIDE_DETACHED = {
    "Fulton, Kentucky Bend": (36.54654, -89.51885),
}
OUTSIDE = {}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="ky-build-metro-outline")
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
    """Douglas-Peucker. County borders are survey-grid straight lines, so this
    collapses a large vertex count to a small one with no visible change to a
    wash whose whole job is to say "coverage ends here". Distances are
    metres, with longitude compressed by cos(latitude) so the tolerance means
    the same thing on both axes."""
    if len(ring) < 3:
        return ring
    tol = tolerance_m / 111320.0
    scale = math.cos(math.radians(42.0))

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
    for label, (lat, lng) in sorted(list(INSIDE.items()) + list(INSIDE_DETACHED.items())):
        if not point_in_rings(lat, lng, rings):
            problems.append("%s should be INSIDE the metro outline and is not" % label)
    for label, (lat, lng) in sorted(OUTSIDE.items()):
        if point_in_rings(lat, lng, rings):
            problems.append("%s should be OUTSIDE the metro outline and is not" % label)
    return problems


def group_rings(rings):
    """Nest each ring under the ring that encloses it — outers, then their holes.

    Kentucky's 120 counties dissolve to TWO outer rings and no holes, so the
    outline is a MultiPolygon. THAT WAS PREDICTED WRONG BEFORE IT WAS RUN: this
    docstring said one ring, on the reasoning that the Kentucky Bend — the piece
    of Fulton County the Mississippi loops around — is part of a county that is
    contiguous with the rest of the state, so it would ride the same ring. It is
    not. MEASURED 2026-09-30: the mainland ring is 104,529.68 km2 over 3,344
    vertices, and the Bend is a separate ring of 69.53 km2 over 39, bounded
    -89.5712..-89.4654 by 36.4975..36.5816. The Bend touches no other part of
    Kentucky: Missouri and Tennessee enclose it, and the only road in comes
    through Tennessee. COUNTY CONTIGUITY IS NOT LAND CONTIGUITY, and a dissolve
    answers the second question.

    The Bend therefore carries an INSIDE anchor of its own, "Fulton (Kentucky
    Bend)", because Fulton County's own anchor sits on the mainland — so without
    it the dissolve could drop the exclave entirely and every gate would stay
    green. TIGERweb names that point Fulton County, STATE 21.

    The general nesting logic is kept identical to Wisconsin's build so a future
    partial-coverage narrowing needs no new code, only a smaller
    METRO_COUNTY_FIPS.
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
    for key in sorted(INSIDE_DETACHED):
        if county_of(key) not in {county_of(k) for k in INSIDE}:
            problems.append(
                "INSIDE_DETACHED names %s, whose county %s carries no INSIDE anchor — "
                "a detached part belongs to a served county or it is not this "
                "instance's ground at all" % (key, county_of(key)))
        if key in INSIDE:
            problems.append(
                "%s appears in BOTH INSIDE and INSIDE_DETACHED — the two lists are "
                "disjoint so the one-anchor-per-county identity stays exact" % key)
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
        print("metro-outline: OK — %d ring(s), %d vertices, all %d inside "
              "(+%d detached) / %d outside anchors correct"
              % (len(rings), sum(len(r) for r in rings),
                 len(INSIDE), len(INSIDE_DETACHED), len(OUTSIDE)), file=sys.stderr)
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
