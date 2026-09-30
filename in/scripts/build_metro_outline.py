#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for Indiana, the dissolved outline of the
WHOLE STATE, since coverage is statewide from day one — from Census TIGERweb.
Unlike Wisconsin's narrower "roster-covered" ring, Indiana's wash makes no
partial claim yet: METRO_COUNTY_FIPS is all 92 counties, and
DISPATCH_COUNTY_FIPS stays empty on purpose — this instance has no per-county
dispatch layers.

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK THE ROSTER.
When a future layer becomes county-keyed (the board of commissioners and the
county council both will be, answering only where a district plan has been
read), narrow METRO_COUNTY_FIPS to what actually answers and add
DISPATCH_COUNTY_FIPS entries — following the Wisconsin precedent
(`wi/scripts/build_metro_outline.py`) rather than inventing a new shape. Until
then, the outline is simply Indiana's border.

Why this exists: the out-of-scope wash (index.html, ENGINE `scope-mask`) marks
where the app's fullest answer ends. It also keeps a boot cost out — painting
the wash from a live boundary fetch cost the reference fork 669 ms in PSI's
critical chain (docs/OPTIMIZATION_PLAYBOOK.md) before it pre-built. This file
is one small pre-dissolved feature.

WHY A BUILD STEP RATHER THAN TIGERweb's OWN STATE POLYGON (layer 0):
dissolving from the county fabric (layer 1) — rather than fetching the state
layer directly — is what lets this same script narrow to a subset of counties
the day coverage becomes partial, without changing shape. It also means this
file's geometry always agrees with `state-counties.json`'s own fabric, since
both come from the same layer.

The dissolve mirrors the app's `coverageOutlineRings` exactly: a segment walked
by two features is an interior border and is dropped; survivors chain back into
closed rings. READ THE RING COUNT FROM --check, NEVER FROM A MAP IN YOUR HEAD.
Indiana looks like a state that must dissolve to one simple ring, and two of
its edges are places where TIGER's county fabric does not follow the border a
reader would draw: the Lake Michigan counties run out to the state water
boundary, and the Ohio River counties run to the low-water mark on the
Kentucky side. The consequence for the wash is deliberate and correct — water
TIGER assigns to an Indiana county reads INSIDE coverage — and it is why this
instance's negative point is a point on LAND in Kentucky (downtown Louisville)
rather than one out on a river or a lake.

Usage:
    python3 in/scripts/build_metro_outline.py                 # writes data/app/metro-outline.json
    python3 in/scripts/build_metro_outline.py --check         # verify the shipped file, write nothing
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
# point_in_rings) are shared machinery other Indiana builders could import
# rather than fork, matching the Wisconsin precedent's reasoning.

TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "State_County/MapServer/1/query")

# Every Indiana county's 3-digit FIPS — the served area IS the whole state.
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
    "177", "179", "181", "183",
)
STATE_FIPS = "18"
# No dispatch entries: none of Indiana's eleven layers are county-keyed yet.
DISPATCH_COUNTY_FIPS = {}

_UNLISTED = sorted(set(DISPATCH_COUNTY_FIPS.values()) - set(METRO_COUNTY_FIPS))
assert not _UNLISTED, (
    "DISPATCH_COUNTY_FIPS names county FIPS %s that METRO_COUNTY_FIPS omits — a "
    "county cannot be served and outside the coverage ring at the same time"
    % _UNLISTED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "metro-outline.json")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/in/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One INSIDE anchor per county (area-weighted centroid of the county's
# largest ring, each one verified interior against that county's own rings
# before being trusted here, with a horizontal-scanline fallback for the
# lake-carved shapes whose centroid lands in open water) — ring closure
# alone is not proof a dissolve kept every county. No OUTSIDE anchors:
# every Indiana county is served, so there is no unserved neighbour to
# prove excluded (the negative point in metro-worksheet.json, in downtown
# Louisville across the Ohio River, covers "clearly outside the state"
# instead).
INSIDE = {
    "Adams": (40.74566, -84.93665),
    "Allen": (41.09086, -85.06655),
    "Bartholomew": (39.20597, -85.89760),
    "Benton": (40.60626, -87.31091),
    "Blackford": (40.47360, -85.32482),
    "Boone": (40.05081, -86.46871),
    "Brown": (39.19621, -86.22737),
    "Carroll": (40.58286, -86.56348),
    "Cass": (40.76149, -86.34594),
    "Clark": (38.47722, -85.70712),
    "Clay": (39.39273, -87.11576),
    "Clinton": (40.30169, -86.47516),
    "Crawford": (38.29238, -86.45169),
    "Daviess": (38.70241, -87.07206),
    "DeKalb": (41.39758, -84.99908),
    "Dearborn": (39.14520, -84.97325),
    "Decatur": (39.30701, -85.50114),
    "Delaware": (40.22753, -85.39690),
    "Dubois": (38.36428, -86.87980),
    "Elkhart": (41.59738, -85.85876),
    "Fayette": (39.64006, -85.17873),
    "Floyd": (38.31871, -85.90704),
    "Fountain": (40.12086, -87.24200),
    "Franklin": (39.41487, -85.06028),
    "Fulton": (41.04697, -86.26358),
    "Gibson": (38.31188, -87.58457),
    "Grant": (40.51584, -85.65473),
    "Greene": (39.03633, -86.96205),
    "Hamilton": (40.07248, -86.05203),
    "Hancock": (39.82355, -85.77324),
    "Harrison": (38.19505, -86.11143),
    "Hendricks": (39.76951, -86.50998),
    "Henry": (39.93104, -85.39644),
    "Howard": (40.48358, -86.11694),
    "Huntington": (40.82923, -85.48818),
    "Jackson": (38.90642, -86.03755),
    "Jasper": (41.02300, -87.11612),
    "Jay": (40.43792, -85.00563),
    "Jefferson": (38.78577, -85.43857),
    "Jennings": (38.99693, -85.62806),
    "Johnson": (39.48997, -86.10164),
    "Knox": (38.68913, -87.41799),
    "Kosciusko": (41.24410, -85.86072),
    "LaGrange": (41.64261, -85.42650),
    "LaPorte": (41.54902, -86.74237),
    "Lake": (41.47221, -87.37639),
    "Lawrence": (38.84116, -86.48345),
    "Madison": (40.16166, -85.71935),
    "Marion": (39.78171, -86.13846),
    "Marshall": (41.32485, -86.26176),
    "Martin": (38.70801, -86.80306),
    "Miami": (40.76950, -86.04502),
    "Monroe": (39.16092, -86.52314),
    "Montgomery": (40.04037, -86.89329),
    "Morgan": (39.48155, -86.44621),
    "Newton": (40.95584, -87.39754),
    "Noble": (41.39860, -85.41747),
    "Ohio": (38.95009, -84.96506),
    "Orange": (38.54178, -86.49507),
    "Owen": (39.31281, -86.83766),
    "Parke": (39.77362, -87.20637),
    "Perry": (38.07964, -86.63803),
    "Pike": (38.39878, -87.23217),
    "Porter": (41.50884, -87.07333),
    "Posey": (38.02177, -87.86848),
    "Pulaski": (41.04183, -86.69878),
    "Putnam": (39.66626, -86.84500),
    "Randolph": (40.15764, -85.01131),
    "Ripley": (39.10346, -85.26239),
    "Rush": (39.61995, -85.46576),
    "Scott": (38.68507, -85.74747),
    "Shelby": (39.52370, -85.79170),
    "Spencer": (38.01401, -87.00774),
    "St. Joseph": (41.61672, -86.28986),
    "Starke": (41.28093, -86.64764),
    "Steuben": (41.64387, -85.00076),
    "Sullivan": (39.08883, -87.41469),
    "Switzerland": (38.82613, -85.03700),
    "Tippecanoe": (40.38860, -86.89411),
    "Tipton": (40.31135, -86.05186),
    "Union": (39.62555, -84.92515),
    "Vanderburgh": (38.02483, -87.58584),
    "Vermillion": (39.85381, -87.46398),
    "Vigo": (39.43064, -87.38996),
    "Wabash": (40.84569, -85.79400),
    "Warren": (40.34691, -87.35331),
    "Warrick": (38.09217, -87.27207),
    "Washington": (38.59999, -86.10530),
    "Wayne": (39.86441, -85.00988),
    "Wells": (40.72919, -85.22122),
    "White": (40.74976, -86.86548),
    "Whitley": (41.13938, -85.50509),
}
OUTSIDE = {}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="in-build-metro-outline")
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
    scale = math.cos(math.radians(44.5))

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

    Indiana's county fabric dissolves to its own ring count — read it
    (see the module docstring), so this degrades to the Polygon case exactly
    as Iowa's does. The nesting logic is unchanged from the Wisconsin/Iowa
    build so a future partial-coverage narrowing needs no new code, only a
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
