#!/usr/bin/env python3
"""
State Outline Builder (the scope mask's REGION band)
====================================================
Builds data/app/ca-state-outline.json, the dissolved outline of all 58
California counties, from Census TIGERweb. It is the middle band of this
instance's wash, the ground where the statewide layers answer and the San
Francisco layers do not.

WHY CALIFORNIA HAS THREE BANDS. This instance began as a San Francisco app
and grew into a California one on 2026-11-11 (Adam's choice of "Grow" over a
second instance beside it). Its city layers, the Board of Supervisors, the
police districts, the neighbourhoods and the rest, answer inside the city
only, while the county, municipality, school district, ZIP, congressional and
both legislative layers answer anywhere in the state. So the wash needs three
zones, as New York's does (docs/EXPANSION_GUIDE.md section 2.5.1): inside the
city everything answers, outside California nothing does, and between the two
the statewide layers still answer. The COVERAGE ring is unchanged: it is the
union of the supervisor districts the app already draws its wash from
(data/app/supervisor-districts.json), and this file is the second argument of
drawOutOfScopeMask.

WHY A COUNTY DISSOLVE RATHER THAN TIGERweb's STATE POLYGON (layer 0), as New
York uses. Texas's builder dissolves the county fabric (layer 1) so the outline
always agrees with state-counties.json, which comes from the same layer; this
file copies that, so the County card and the wash agree about where California
ends. The coastal counties' polygons carry the water out to the county line,
so the band runs over the bays and a strip of the Pacific, and the ring count
is a measurement the --check line prints, not a prediction made here: the
Channel Islands and the Farallones are detached from the mainland.

The dissolve mirrors the app's `coverageOutlineRings` exactly: a segment
walked by two features is an interior border and is dropped; survivors chain
back into closed rings.

California borders Oregon, Nevada and Arizona, and Mexico. Nevada and Arizona
are live instances; Oregon is in a later batch of the state-level launch.
OUTSIDE carries towns just over each line, and in Mexico and the Pacific, to
prove the dissolve did not leak, and the worksheet's negative point is in the
Mexicali Valley, in Mexico, which no instance will ever serve.

Usage:
    python3 ca/scripts/build_state_outline.py                 # writes data/app/ca-state-outline.json
    python3 ca/scripts/build_state_outline.py --check         # verify the shipped file, write nothing
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

# Every California county's 3-digit FIPS: the 58 odd numbers 001 to 115.
# The band claims the whole state, because every statewide layer answers in
# all of them. It must stay a plain literal assignment at module top.
METRO_COUNTY_FIPS = (
    "001", "003", "005", "007", "009", "011", "013", "015",
    "017", "019", "021", "023", "025", "027", "029", "031",
    "033", "035", "037", "039", "041", "043", "045", "047",
    "049", "051", "053", "055", "057", "059", "061", "063",
    "065", "067", "069", "071", "073", "075", "077", "079",
    "081", "083", "085", "087", "089", "091", "093", "095",
    "097", "099", "101", "103", "105", "107", "109", "111",
    "113", "115",
)
STATE_FIPS = "06"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "ca-state-outline.json")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")

HEADERS = {"User-Agent": "districtry state-outline builder (+https://districtry.com/ca/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One INSIDE anchor per county: the Census Bureau's own internal point for it
# (INTPTLAT/INTPTLON on TIGERweb State_County layer 1), which the Census
# places inside it by construction. Each was still verified inside its own
# SIMPLIFIED rings in the shipped state-counties.json, and inside no other
# county, before being trusted here. All 58 passed on 2026-11-11. Keyed by the
# county's name without "County".
INSIDE = {
    "Alameda": (37.64010, -121.90681),
    "Alpine": (38.60241, -119.84498),
    "Amador": (38.44337, -120.65170),
    "Butte": (39.66534, -121.60321),
    "Calaveras": (38.19107, -120.55411),
    "Colusa": (39.17774, -122.23756),
    "Contra Costa": (37.90799, -121.95899),
    "Del Norte": (41.74707, -123.95317),
    "El Dorado": (38.78561, -120.53422),
    "Fresno": (36.76115, -119.65501),
    "Glenn": (39.60255, -122.40170),
    "Humboldt": (40.70666, -123.92618),
    "Imperial": (33.04081, -115.35540),
    "Inyo": (36.61086, -117.30701),
    "Kern": (35.35563, -118.71864),
    "Kings": (36.07248, -119.81553),
    "Lake": (39.10810, -122.74548),
    "Lassen": (40.70798, -120.60859),
    "Los Angeles": (34.19640, -118.26186),
    "Madera": (37.20576, -119.74932),
    "Marin": (38.05137, -122.74640),
    "Mariposa": (37.57434, -119.91172),
    "Mendocino": (39.43270, -123.42752),
    "Merced": (37.19391, -120.72147),
    "Modoc": (41.59292, -120.71837),
    "Mono": (37.90993, -118.87907),
    "Monterey": (36.24010, -121.31558),
    "Napa": (38.50735, -122.32600),
    "Nevada": (39.30781, -120.74350),
    "Orange": (33.67569, -117.77721),
    "Placer": (39.06702, -120.71624),
    "Plumas": (39.99230, -120.82437),
    "Riverside": (33.80059, -115.94841),
    "Sacramento": (38.44850, -121.34249),
    "San Benito": (36.61165, -121.08581),
    "San Bernardino": (34.85666, -116.18157),
    "San Diego": (33.01934, -116.76984),
    "San Francisco": (37.72724, -123.03223),
    "San Joaquin": (37.93494, -121.27230),
    "San Luis Obispo": (35.38819, -120.44890),
    "San Mateo": (37.41468, -122.37150),
    "Santa Barbara": (34.53668, -120.03836),
    "Santa Clara": (37.22161, -121.68954),
    "Santa Cruz": (37.01219, -122.00769),
    "Shasta": (40.76025, -122.04407),
    "Sierra": (39.57693, -120.52199),
    "Siskiyou": (41.58634, -122.53369),
    "Solano": (38.26723, -121.93959),
    "Sonoma": (38.52170, -122.91642),
    "Stanislaus": (37.56225, -121.00280),
    "Sutter": (39.03619, -121.70394),
    "Tehama": (40.12616, -122.23227),
    "Trinity": (40.64786, -123.11463),
    "Tulare": (36.22883, -118.78106),
    "Tuolumne": (38.02140, -119.96481),
    "Ventura": (34.35901, -119.13290),
    "Yolo": (38.67942, -121.90143),
    "Yuba": (39.27013, -121.34426),
}

# Towns just over each state line, and the worksheet's negative point, each
# checked against TIGERweb's own state layer on 2026-11-11 (the Census answer,
# not a guess from a map; controls: the State Capitol in Sacramento returns
# California and a point in the open Pacific 300 km off Monterey returns no
# state): four in Nevada, three in Arizona and three in Oregon, which TIGERweb
# names, and three in Mexico and two in the Pacific, where it names no state.
# Keys read "Place (XX)" or name the country, so county_of() names no
# California county.
OUTSIDE = {
    "Reno (NV)": (39.52960, -119.81380),
    "Carson City (NV)": (39.16380, -119.76740),
    "Las Vegas (NV)": (36.16990, -115.13980),
    "Laughlin (NV)": (35.16780, -114.57300),
    "Bullhead City (AZ)": (35.14780, -114.56830),
    "Lake Havasu City (AZ)": (34.48390, -114.32250),
    "Yuma (AZ)": (32.69270, -114.62770),
    "Brookings (OR)": (42.05260, -124.28400),
    "Klamath Falls (OR)": (42.22490, -121.78170),
    "Lakeview (OR)": (42.18880, -120.34580),
    "Tijuana (Baja California, MX)": (32.51490, -117.03820),
    "Mexicali (Baja California, MX)": (32.62450, -115.45230),
    "Mexicali Valley (MX), the worksheet's negative point": (32.40000, -115.60000),
    "Pacific Ocean, 150 km off Point Conception": (34.00000, -122.00000),
    "Pacific Ocean, 120 km off Cape Mendocino": (40.40000, -125.80000),
}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="ca-build-state-outline")
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
    scale = math.cos(math.radians(37.0))  # California's middle latitude

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
            problems.append("%s should be INSIDE the state outline and is not" % label)
    for label, (lat, lng) in sorted(OUTSIDE.items()):
        if point_in_rings(lat, lng, rings):
            problems.append("%s should be OUTSIDE the state outline and is not" % label)
    return problems


def group_rings(rings):
    """Nest each ring under the ring that encloses it — outers, then their holes.

    How many outer rings California's fabric dissolves to is a
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
            "properties": {"name": "California (%d counties)" % len(METRO_COUNTY_FIPS)},
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
        print("ca-state-outline: OK — %d ring(s), %d vertices, all %d inside / %d outside "
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
