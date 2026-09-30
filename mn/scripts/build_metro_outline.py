#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for Minnesota, the dissolved outline of the
WHOLE STATE, since coverage is statewide from day one — from Census
TIGERweb. Unlike Wisconsin's narrower "roster-covered" ring, Minnesota's wash
makes no partial claim yet: METRO_COUNTY_FIPS is all 87 counties, and
DISPATCH_COUNTY_FIPS stays empty on purpose — this instance has no
per-county dispatch layers (none of its four layers are county-keyed).

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK THE
ROSTER. When a future layer becomes county-keyed (e.g. `county-supervisor`
answering only where a plan is confirmed), narrow METRO_COUNTY_FIPS to what
actually answers and add DISPATCH_COUNTY_FIPS entries — following the
Wisconsin precedent (`wi/scripts/build_metro_outline.py`) rather than
inventing a new shape. Until then, the outline is simply Minnesota's border.

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
chain back into closed rings. Minnesota's 87 counties dissolve to a single
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
# point_in_rings) are shared machinery other Minnesota builders could import
# rather than fork, matching the Wisconsin precedent's reasoning.

TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "State_County/MapServer/1/query")

# Every Minnesota county's 3-digit FIPS — the served area IS the whole state.
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
    "161", "163", "165", "167", "169", "171", "173",
)
STATE_FIPS = "27"
# No dispatch entries: none of Minnesota's four layers are county-keyed yet.
DISPATCH_COUNTY_FIPS = {}

_UNLISTED = sorted(set(DISPATCH_COUNTY_FIPS.values()) - set(METRO_COUNTY_FIPS))
assert not _UNLISTED, (
    "DISPATCH_COUNTY_FIPS names county FIPS %s that METRO_COUNTY_FIPS omits — a "
    "county cannot be served and outside the coverage ring at the same time"
    % _UNLISTED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "metro-outline.json")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/mn/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One INSIDE anchor per county (area-weighted polygon centroid, verified
# interior against that county's own rings before being trusted here) —
# ring closure alone is not proof a dissolve kept every county. No OUTSIDE
# anchors: every Minnesota county is served, so there is no unserved neighbour
# to prove excluded (the negative point in metro-worksheet.json, out in
# Lake Superior, covers "clearly outside the state" instead).
INSIDE = {
    "Aitkin": (46.6082, -93.41549),
    "Anoka": (45.27324, -93.24647),
    "Becker": (46.93465, -95.67392),
    "Beltrami": (47.97377, -94.93762),
    "Benton": (45.69913, -93.99883),
    "Big Stone": (45.42611, -96.41095),
    "Blue Earth": (44.03459, -94.06703),
    "Brown": (44.24216, -94.72749),
    "Carlton": (46.59238, -92.67705),
    "Carver": (44.82068, -93.8026),
    "Cass": (46.9496, -94.32535),
    "Chippewa": (45.02236, -95.56668),
    "Chisago": (45.50247, -92.90834),
    "Clay": (46.89235, -96.49066),
    "Clearwater": (47.57777, -95.379),
    "Cook": (47.72667, -90.38599),
    "Cottonwood": (44.00711, -95.18115),
    "Crow Wing": (46.48237, -94.07086),
    "Dakota": (44.67189, -93.06544),
    "Dodge": (44.02259, -92.86209),
    "Douglas": (45.93375, -95.4535),
    "Faribault": (43.67393, -93.948),
    "Fillmore": (43.674, -92.09018),
    "Freeborn": (43.67384, -93.34882),
    "Goodhue": (44.40969, -92.72291),
    "Grant": (45.93405, -96.01218),
    "Hennepin": (45.00457, -93.47697),
    "Houston": (43.67144, -91.49283),
    "Hubbard": (47.10863, -94.91662),
    "Isanti": (45.56149, -93.29517),
    "Itasca": (47.50952, -93.63196),
    "Jackson": (43.67417, -95.15411),
    "Kanabec": (45.94522, -93.29347),
    "Kandiyohi": (45.1524, -95.00474),
    "Kittson": (48.77667, -96.7828),
    "Koochiching": (48.24546, -93.78337),
    "Lac qui Parle": (44.9955, -96.17347),
    "Lake": (47.52322, -91.40883),
    "Lake of the Woods": (48.77128, -94.90453),
    "Le Sueur": (44.37146, -93.73014),
    "Lincoln": (44.4126, -96.26709),
    "Lyon": (44.41349, -95.83897),
    "Mahnomen": (47.32524, -95.80905),
    "Marshall": (48.35813, -96.36848),
    "Martin": (43.67436, -94.55107),
    "McLeod": (44.82356, -94.27244),
    "Meeker": (45.12311, -94.52734),
    "Mille Lacs": (45.93805, -93.6301),
    "Morrison": (46.01262, -94.26842),
    "Mower": (43.6715, -92.75249),
    "Murray": (44.02212, -95.76328),
    "Nicollet": (44.34987, -94.24739),
    "Nobles": (43.67424, -95.75339),
    "Norman": (47.32648, -96.45528),
    "Olmsted": (44.00378, -92.40179),
    "Otter Tail": (46.40882, -95.70804),
    "Pennington": (48.06623, -96.03671),
    "Pine": (46.12076, -92.74128),
    "Pipestone": (44.023, -96.25865),
    "Polk": (47.77385, -96.4018),
    "Pope": (45.58602, -95.4445),
    "Ramsey": (45.01711, -93.09957),
    "Red Lake": (47.87169, -96.0953),
    "Redwood": (44.40366, -95.25383),
    "Renville": (44.72681, -94.94714),
    "Rice": (44.35427, -93.2967),
    "Rock": (43.67463, -96.25321),
    "Roseau": (48.77515, -95.81081),
    "Scott": (44.64852, -93.53582),
    "Sherburne": (45.444, -93.77479),
    "Sibley": (44.57948, -94.2321),
    "St. Louis": (47.58987, -92.46149),
    "Stearns": (45.55215, -94.6131),
    "Steele": (44.02235, -93.22609),
    "Stevens": (45.58614, -96.00026),
    "Swift": (45.28274, -95.68145),
    "Todd": (46.07063, -94.8976),
    "Traverse": (45.77218, -96.47164),
    "Wabasha": (44.28429, -92.23025),
    "Wadena": (46.58575, -94.96943),
    "Waseca": (44.02212, -93.58728),
    "Washington": (45.03889, -92.88381),
    "Watonwan": (43.97843, -94.61406),
    "Wilkin": (46.35708, -96.46834),
    "Winona": (43.98685, -91.77916),
    "Wright": (45.17394, -93.96304),
    "Yellow Medicine": (44.71625, -95.86836),
}
OUTSIDE = {}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="mn-build-metro-outline")
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
    for label, (lat, lng) in sorted(INSIDE.items()):
        if not point_in_rings(lat, lng, rings):
            problems.append("%s should be INSIDE the metro outline and is not" % label)
    for label, (lat, lng) in sorted(OUTSIDE.items()):
        if point_in_rings(lat, lng, rings):
            problems.append("%s should be OUTSIDE the metro outline and is not" % label)
    return problems


def group_rings(rings):
    """Nest each ring under the ring that encloses it — outers, then their holes.

    Minnesota's 87 counties dissolve to ONE outer ring with no interior holes or
    detached regions (verified — a second ring here would mean an island or
    enclave the anchors don't already know about), so this degrades to the
    Polygon-not-MultiPolygon case in practice, but the general nesting logic
    is kept identical to Wisconsin's build so a future partial-coverage
    narrowing needs no new code, only a smaller METRO_COUNTY_FIPS.
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
