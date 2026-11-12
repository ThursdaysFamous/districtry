#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for Nebraska, the dissolved outline
of the WHOLE STATE, since coverage is statewide from day one — from Census
TIGERweb. Unlike Wisconsin's narrower "roster-covered" ring, this wash makes
no partial claim: METRO_COUNTY_FIPS is all 93 counties, and
DISPATCH_COUNTY_FIPS stays empty on purpose — this instance has no
per-county dispatch layers.

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK WHAT
ANSWERS. Every statewide layer answers in all 93 of them, so the wash claims
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
once.

Nebraska borders South Dakota, Iowa, Missouri, Kansas, Colorado and Wyoming,
every one of which has its own districtry app once this batch opens. Nebraska
is landlocked, so the worksheet's negative point sits on a neighbour's land,
in Clay County, South Dakota, north of the Missouri River. That app does not
move the point: the smoke test only boots the map there, and a booted point is
never handed to another app.

Usage:
    python3 ne/scripts/build_metro_outline.py                 # writes data/app/metro-outline.json
    python3 ne/scripts/build_metro_outline.py --check         # verify the shipped file, write nothing
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

# Every Nebraska county's 3-digit FIPS, read from TIGERweb 2026-11-12 — the served area IS
# the whole state.
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
    "177", "179", "181", "183", "185",
)
STATE_FIPS = "31"
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

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/ne/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One INSIDE anchor per county: the Census Bureau's own internal point for it
# (INTPTLAT/INTPTLON on TIGERweb State_County layer 1), which the Census
# places inside it by construction. The build and --check both test each
# against its own SIMPLIFIED rings in the shipped state-counties.json and
# against the dissolved outline, so ring closure alone is never taken as
# proof a dissolve kept every county. Read 2026-11-12. Keyed by the Census name
# without "County".
INSIDE = {
    "Adams": (40.52063, -98.50004),
    "Antelope": (42.18323, -98.05804),
    "Arthur": (41.57207, -101.69570),
    "Banner": (41.53975, -103.72626),
    "Blaine": (41.93194, -99.99641),
    "Boone": (41.70393, -98.07048),
    "Box Butte": (42.21038, -103.08178),
    "Boyd": (42.89445, -98.77302),
    "Brown": (42.35956, -99.92392),
    "Buffalo": (40.85527, -99.07498),
    "Burt": (41.85418, -96.33775),
    "Butler": (41.22605, -97.13200),
    "Cass": (40.90794, -96.14819),
    "Cedar": (42.60456, -97.25686),
    "Chase": (40.53039, -101.69419),
    "Cherry": (42.57096, -101.04276),
    "Cheyenne": (41.21424, -103.01193),
    "Clay": (40.52367, -98.05086),
    "Colfax": (41.57496, -97.08894),
    "Cuming": (41.91587, -96.78852),
    "Custer": (41.39389, -99.72687),
    "Dakota": (42.39013, -96.56498),
    "Dawes": (42.71292, -103.13571),
    "Dawson": (40.86775, -99.81580),
    "Deuel": (41.11190, -102.33261),
    "Dixon": (42.48520, -96.85577),
    "Dodge": (41.57681, -96.64563),
    "Douglas": (41.29709, -96.15407),
    "Dundy": (40.18017, -101.68113),
    "Fillmore": (40.52504, -97.59671),
    "Franklin": (40.18320, -98.96208),
    "Frontier": (40.53095, -100.40668),
    "Furnas": (40.19225, -99.90864),
    "Gage": (40.25516, -96.68344),
    "Garden": (41.63336, -102.30298),
    "Garfield": (41.90691, -98.95128),
    "Gosper": (40.50909, -99.82321),
    "Grant": (41.89790, -101.79307),
    "Greeley": (41.56756, -98.53057),
    "Hall": (40.86603, -98.50266),
    "Hamilton": (40.87562, -98.02329),
    "Harlan": (40.17971, -99.40285),
    "Hayes": (40.53723, -101.04796),
    "Hitchcock": (40.17690, -101.04422),
    "Holt": (42.45929, -98.78477),
    "Hooker": (41.92032, -101.11732),
    "Howard": (41.21685, -98.51334),
    "Jefferson": (40.18292, -97.15674),
    "Johnson": (40.39548, -96.26438),
    "Kearney": (40.50912, -98.94760),
    "Keith": (41.19424, -101.64445),
    "Keya Paha": (42.87548, -99.71835),
    "Kimball": (41.19927, -103.70315),
    "Knox": (42.63440, -97.89135),
    "Lancaster": (40.78355, -96.68866),
    "Lincoln": (41.05032, -100.74448),
    "Logan": (41.58009, -100.40799),
    "Loup": (41.89820, -99.51452),
    "Madison": (41.90993, -97.60686),
    "McPherson": (41.64841, -101.12085),
    "Merrick": (41.16979, -98.03106),
    "Morrill": (41.73220, -102.99059),
    "Nance": (41.40239, -97.99141),
    "Nemaha": (40.38724, -95.85252),
    "Nuckolls": (40.17649, -98.04684),
    "Otoe": (40.63799, -96.13103),
    "Pawnee": (40.13782, -96.24509),
    "Perkins": (40.85762, -101.62747),
    "Phelps": (40.51636, -99.40656),
    "Pierce": (42.27141, -97.61099),
    "Platte": (41.57687, -97.51347),
    "Polk": (41.18793, -97.57066),
    "Red Willow": (40.16942, -100.46858),
    "Richardson": (40.12374, -95.71860),
    "Rock": (42.39475, -99.42085),
    "Saline": (40.51680, -97.13175),
    "Sarpy": (41.11506, -96.10913),
    "Saunders": (41.22326, -96.64718),
    "Scotts Bluff": (41.85051, -103.70302),
    "Seward": (40.87194, -97.14038),
    "Sheridan": (42.50801, -102.35833),
    "Sherman": (41.21874, -98.97285),
    "Sioux": (42.47065, -103.73217),
    "Stanton": (41.90505, -97.17711),
    "Thayer": (40.17313, -97.59609),
    "Thomas": (41.85553, -100.52474),
    "Thurston": (42.15406, -96.53394),
    "Valley": (41.56409, -98.98348),
    "Washington": (41.53397, -96.22458),
    "Wayne": (42.21075, -97.12624),
    "Webster": (40.18065, -98.49859),
    "Wheeler": (41.92257, -98.52085),
    "York": (40.87306, -97.59674),
}

# Places just over each line, and the worksheet's negative point, each checked
# against TIGERweb's own state layer on 2026-11-12 (Census answer, not a guess from a
# map; controls: Nebraska State Capitol returns Nebraska, the Colorado State Capitol
# returns Colorado, and a point in the open Atlantic returns no state). The build and
# --check both refuse if any lies inside the dissolved outline. Keys read
# "Place (XX)", the postal code, so county_of() names no Nebraska county.
OUTSIDE = {
    "Yankton (SD)": (42.8711, -97.3973),
    "Vermillion (SD)": (42.7794, -96.9292),
    "Burke (SD)": (43.1825, -99.2923),
    "Martin (SD)": (43.1725, -101.7329),
    "Edgemont (SD)": (43.3000, -103.8252),
    "Torrington (WY)": (42.0625, -104.1844),
    "Pine Bluffs (WY)": (41.1822, -104.0691),
    "Julesburg (CO)": (40.9886, -102.2643),
    "St. Francis (KS)": (39.7722, -101.8000),
    "Norton (KS)": (39.8339, -99.8915),
    "Belleville (KS)": (39.8247, -97.6325),
    "Marysville (KS)": (39.8411, -96.6472),
    "Rock Port (MO)": (40.4111, -95.5150),
    "Council Bluffs (IA)": (41.2619, -95.8608),
    "Sioux City (IA)": (42.4963, -96.4049),
    "Clay County, South Dakota, north of the Missouri River, the worksheet's negative point": (42.8700, -97.0500),
}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="ne-build-metro-outline")
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
    scale = math.cos(math.radians(41.5))  # Nebraska's middle latitude

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

    How many outer rings Nebraska's fabric dissolves to is a
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
