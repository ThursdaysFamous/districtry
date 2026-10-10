#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for Tennessee, the dissolved
outline of the WHOLE STATE, since coverage is statewide from day one — from
Census TIGERweb. Unlike Wisconsin's narrower "roster-covered" ring, this
wash makes no partial claim yet: METRO_COUNTY_FIPS is all 95 counties, and
DISPATCH_COUNTY_FIPS stays empty on purpose — this instance has no
per-county dispatch layers, because none of its twelve layers is
county-keyed.

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK WHAT
ANSWERS. Every Tennessee county elects its county commission from districts,
and the Comptroller of the Treasury publishes all of them in one statewide
service, so when a county-commission layer arrives it is expected to answer
in all 95 counties at once and this list should not need narrowing. If a
county ever drops out of that answer, narrow METRO_COUNTY_FIPS to what
actually answers and add DISPATCH_COUNTY_FIPS entries, following
`wi/scripts/build_metro_outline.py` rather than inventing a new shape. Until
then, the outline is simply the state's border.

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
once. Tennessee's 95 counties union to one polygon (measured 2026-10-10 with
shapely on the full-precision fabric), so one ring is the expected answer,
and --check is what says so.

Tennessee borders eight states, two of them live instances (Kentucky and
North Carolina), so OUTSIDE carries one city just over each of the eight
lines — Arkansas and Missouri across the Mississippi included — to prove the
dissolve did not leak. The worksheet's negative point is in Alabama, which no
instance serves.

Usage:
    python3 tn/scripts/build_metro_outline.py                 # writes data/app/metro-outline.json
    python3 tn/scripts/build_metro_outline.py --check         # verify the shipped file, write nothing
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

# Every Tennessee county's 3-digit FIPS — the served area IS the whole state.
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
    "177", "179", "181", "183", "185", "187", "189",
)
STATE_FIPS = "47"
# No dispatch entries: none of this instance's twelve layers is county-keyed yet.
DISPATCH_COUNTY_FIPS = {}

_UNLISTED = sorted(set(DISPATCH_COUNTY_FIPS.values()) - set(METRO_COUNTY_FIPS))
assert not _UNLISTED, (
    "DISPATCH_COUNTY_FIPS names county FIPS %s that METRO_COUNTY_FIPS omits — a "
    "county cannot be served and outside the coverage ring at the same time"
    % _UNLISTED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "metro-outline.json")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/tn/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One INSIDE anchor per county (area-weighted centroid of the county's
# largest ring, each one verified interior against that county's own rings
# before being trusted here) — ring closure alone is not proof a dissolve kept
# every county. All 95 were verified interior against their own county's
# full-precision rings when this table was generated, 2026-10-10, and every
# one sits at least 1 km inside its own county and 2 km inside the state, so
# the 25 m simplification below cannot move an edge past one.
INSIDE = {
    "Anderson": (36.11844, -84.19846),
    "Bedford": (35.51380, -86.45889),
    "Benton": (36.06978, -88.06827),
    "Bledsoe": (35.59637, -85.20513),
    "Blount": (35.68722, -83.92554),
    "Bradley": (35.15411, -84.85960),
    "Campbell": (36.40351, -84.14938),
    "Cannon": (35.80868, -86.06174),
    "Carroll": (35.97318, -88.45026),
    "Carter": (36.29272, -82.12748),
    "Cheatham": (36.26115, -87.08678),
    "Chester": (35.42175, -88.61346),
    "Claiborne": (36.48585, -83.66042),
    "Clay": (36.55116, -85.54386),
    "Cocke": (35.92544, -83.12118),
    "Coffee": (35.49062, -86.07476),
    "Crockett": (35.81354, -89.13953),
    "Cumberland": (35.95039, -84.99835),
    "Davidson": (36.16952, -86.78486),
    "DeKalb": (35.97987, -85.83276),
    "Decatur": (35.60302, -88.10877),
    "Dickson": (36.14902, -87.35670),
    "Dyer": (36.05919, -89.41367),
    "Fayette": (35.19701, -89.41416),
    "Fentress": (36.38049, -84.93246),
    "Franklin": (35.15496, -86.09218),
    "Gibson": (35.99661, -88.93262),
    "Giles": (35.20215, -87.03478),
    "Grainger": (36.27626, -83.50962),
    "Greene": (36.17535, -82.84583),
    "Grundy": (35.38837, -85.72258),
    "Hamblen": (36.21715, -83.26666),
    "Hamilton": (35.18081, -85.16476),
    "Hancock": (36.52365, -83.22183),
    "Hardeman": (35.20687, -88.99308),
    "Hardin": (35.19868, -88.18449),
    "Hawkins": (36.44116, -82.94469),
    "Haywood": (35.58322, -89.28384),
    "Henderson": (35.65426, -88.38799),
    "Henry": (36.33184, -88.30121),
    "Hickman": (35.80325, -87.47331),
    "Houston": (36.28597, -87.71704),
    "Humphreys": (36.04082, -87.77563),
    "Jackson": (36.35921, -85.67315),
    "Jefferson": (36.05098, -83.44631),
    "Johnson": (36.45494, -81.85177),
    "Knox": (35.99322, -83.93709),
    "Lake": (36.33538, -89.49347),
    "Lauderdale": (35.76054, -89.63051),
    "Lawrence": (35.21727, -87.39558),
    "Lewis": (35.52728, -87.49310),
    "Lincoln": (35.14052, -86.58894),
    "Loudon": (35.73520, -84.31118),
    "Macon": (36.53203, -86.00727),
    "Madison": (35.60814, -88.83847),
    "Marion": (35.12933, -85.62199),
    "Marshall": (35.46886, -86.76502),
    "Maury": (35.61693, -87.07702),
    "McMinn": (35.42474, -84.61747),
    "McNairy": (35.17545, -88.56364),
    "Meigs": (35.51288, -84.81329),
    "Monroe": (35.44264, -84.25280),
    "Montgomery": (36.49686, -87.38289),
    "Moore": (35.28462, -86.35877),
    "Morgan": (36.13502, -84.64920),
    "Obion": (36.35823, -89.14880),
    "Overton": (36.34500, -85.28808),
    "Perry": (35.64263, -87.85897),
    "Pickett": (36.55841, -85.07499),
    "Polk": (35.11990, -84.52332),
    "Putnam": (36.14083, -85.49519),
    "Rhea": (35.60867, -84.92442),
    "Roane": (35.84786, -84.52324),
    "Robertson": (36.52544, -86.87057),
    "Rutherford": (35.84271, -86.41674),
    "Scott": (36.42854, -84.50352),
    "Sequatchie": (35.37115, -85.41059),
    "Sevier": (35.78466, -83.52419),
    "Shelby": (35.18425, -89.89400),
    "Smith": (36.25054, -85.95671),
    "Stewart": (36.50110, -87.83846),
    "Sullivan": (36.51292, -82.30414),
    "Sumner": (36.46940, -86.46036),
    "Tipton": (35.50155, -89.73604),
    "Trousdale": (36.39204, -86.15675),
    "Unicoi": (36.11073, -82.43234),
    "Union": (36.28787, -83.83751),
    "Van Buren": (35.69598, -85.45261),
    "Warren": (35.67868, -85.77850),
    "Washington": (36.29330, -82.49742),
    "Wayne": (35.23992, -87.78801),
    "Weakley": (36.29830, -88.71774),
    "White": (35.92666, -85.45560),
    "Williamson": (35.89383, -86.89866),
    "Wilson": (36.15487, -86.29778),
}
# One city just across each of Tennessee's eight state lines, so a dissolve
# that leaked past the border fails the build rather than washing another
# state. Each was checked against TIGERweb's own state and county layers on
# 2026-10-10 (Census answer, not a guess from a map), with the State Capitol
# as the control that returns Tennessee.
OUTSIDE = {
    "Bowling Green, Kentucky": (36.9685, -86.4808),
    "Abingdon, Virginia": (36.7098, -81.9773),
    "Murphy, North Carolina": (35.0876, -84.0213),
    "Dalton, Georgia": (34.7698, -84.9702),
    "Huntsville, Alabama": (34.7304, -86.5861),
    "Corinth, Mississippi": (34.9343, -88.5223),
    "West Memphis, Arkansas": (35.1465, -90.1845),
    "Caruthersville, Missouri": (36.1931, -89.6556),
}

def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="tn-build-metro-outline")
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
    scale = math.cos(math.radians(35.8))

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

    How many outer rings Tennessee's fabric dissolves to is a
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
