#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for Arkansas, the dissolved outline of
the WHOLE STATE, since coverage is statewide from day one — from Census
TIGERweb. Unlike Wisconsin's narrower "roster-covered" ring, this wash makes
no partial claim yet: METRO_COUNTY_FIPS is all 75 counties, and
DISPATCH_COUNTY_FIPS stays empty on purpose — this instance has no per-county
dispatch layers, because none of its ten layers is county-keyed.

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK WHAT
ANSWERS. Every Arkansas county is governed by a quorum court elected from
districts, and the state's GIS office publishes every county's quorum court
districts in one statewide service (775 districts across all 75 counties,
measured by the planning pass on 2026-10-09), so when the quorum court layer
arrives it is expected to answer in all 75 counties at once and this list
should not need narrowing. If a county ever drops out of that answer, narrow
METRO_COUNTY_FIPS to what actually answers and add DISPATCH_COUNTY_FIPS
entries, following `wi/scripts/build_metro_outline.py` rather than inventing
a new shape. Until then, the outline is simply the state's border.

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
once. Arkansas's eastern border follows the Mississippi River, whose old
channels leave pieces of one state on the other bank, so the ring count is a
measurement the --check line prints, not a prediction made here.

Arkansas borders six states: Missouri, Texas, Mississippi and Louisiana, which
no instance serves, Oklahoma, which is live, and Tennessee, which was built
hidden and is going live. OUTSIDE carries cities just over each line to prove
the dissolve did not leak, and the worksheet's negative point is in Texas,
where no instance answers.

Usage:
    python3 ar/scripts/build_metro_outline.py                 # writes data/app/metro-outline.json
    python3 ar/scripts/build_metro_outline.py --check         # verify the shipped file, write nothing
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

# Every Arkansas county's 3-digit FIPS — the served area IS the whole state.
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
    "145", "147", "149",
)
STATE_FIPS = "05"
# No dispatch entries: none of this instance's ten layers is county-keyed yet.
DISPATCH_COUNTY_FIPS = {}

_UNLISTED = sorted(set(DISPATCH_COUNTY_FIPS.values()) - set(METRO_COUNTY_FIPS))
assert not _UNLISTED, (
    "DISPATCH_COUNTY_FIPS names county FIPS %s that METRO_COUNTY_FIPS omits — a "
    "county cannot be served and outside the coverage ring at the same time"
    % _UNLISTED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "metro-outline.json")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/ar/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One INSIDE anchor per county: the Census Bureau's own internal point for the
# county (INTPTLAT/INTPTLON on TIGERweb State_County layer 1), which the
# Census places inside the county by construction. Each was still verified
# interior against that county's own SIMPLIFIED rings in the shipped
# state-counties.json, and inside no other county, before being trusted here
# — ring closure alone is not proof a dissolve kept every county. All 75
# passed when this table was generated, 2026-10-13.
INSIDE = {
    "Arkansas": (34.28957, -91.37655),
    "Ashley": (33.19084, -91.77227),
    "Baxter": (36.28027, -92.32995),
    "Benton": (36.33782, -94.25630),
    "Boone": (36.30430, -93.07924),
    "Bradley": (33.46649, -92.16920),
    "Calhoun": (33.56046, -92.51388),
    "Carroll": (36.33737, -93.54097),
    "Chicot": (33.27154, -91.30358),
    "Clark": (34.05332, -93.17621),
    "Clay": (36.36730, -90.41870),
    "Cleburne": (35.59363, -92.00890),
    "Cleveland": (33.89320, -92.18871),
    "Columbia": (33.22304, -93.23284),
    "Conway": (35.26569, -92.68925),
    "Craighead": (35.82773, -90.63142),
    "Crawford": (35.58296, -94.23619),
    "Crittenden": (35.19893, -90.30233),
    "Cross": (35.28569, -90.76398),
    "Dallas": (33.96782, -92.65400),
    "Desha": (33.82768, -91.24515),
    "Drew": (33.58724, -91.72278),
    "Faulkner": (35.14655, -92.33693),
    "Franklin": (35.50832, -93.88959),
    "Fulton": (36.38132, -91.81928),
    "Garland": (34.57885, -93.14693),
    "Grant": (34.28557, -92.42298),
    "Greene": (36.12061, -90.56635),
    "Hempstead": (33.73595, -93.66436),
    "Hot Spring": (34.31518, -92.94415),
    "Howard": (34.08306, -93.99093),
    "Independence": (35.73750, -91.55994),
    "Izard": (36.09488, -91.91363),
    "Jackson": (35.59647, -91.22321),
    "Jefferson": (34.27718, -91.92966),
    "Johnson": (35.57336, -93.46632),
    "Lafayette": (33.24063, -93.61151),
    "Lawrence": (36.05479, -91.10175),
    "Lee": (34.77950, -90.77972),
    "Lincoln": (33.95648, -91.74248),
    "Little River": (33.70194, -94.23629),
    "Logan": (35.21865, -93.72091),
    "Lonoke": (34.75511, -91.89413),
    "Madison": (36.01255, -93.72405),
    "Marion": (36.26666, -92.67858),
    "Miller": (33.30551, -93.90150),
    "Mississippi": (35.76694, -90.05221),
    "Monroe": (34.67951, -91.20331),
    "Montgomery": (34.54566, -93.66415),
    "Nevada": (33.66670, -93.30507),
    "Newton": (35.91074, -93.21590),
    "Ouachita": (33.59113, -92.87839),
    "Perry": (34.94949, -92.92757),
    "Phillips": (34.42792, -90.86000),
    "Pike": (34.15819, -93.65866),
    "Poinsett": (35.56882, -90.68116),
    "Polk": (34.49096, -94.23089),
    "Pope": (35.45652, -93.02684),
    "Prairie": (34.83112, -91.55362),
    "Pulaski": (34.77031, -92.31300),
    "Randolph": (36.34130, -91.02844),
    "Saline": (34.64852, -92.67446),
    "Scott": (34.85879, -94.06372),
    "Searcy": (35.89639, -92.69589),
    "Sebastian": (35.19698, -94.27499),
    "Sevier": (33.99488, -94.24328),
    "Sharp": (36.18662, -91.49142),
    "St. Francis": (35.02284, -90.75151),
    "Stone": (35.86064, -92.15960),
    "Union": (33.16822, -92.59814),
    "Van Buren": (35.59497, -92.52817),
    "Washington": (35.97800, -94.21727),
    "White": (35.25512, -91.75303),
    "Woodruff": (35.19278, -91.24454),
    "Yell": (34.99771, -93.40830),
}
# Cities just across each state line, so a dissolve that leaked past the
# border fails the build rather than washing another state. Each was checked
# against TIGERweb's own state layer on 2026-10-13 (Census answer, not a guess
# from a map; control: the State Capitol returns Arkansas): two in each of
# Missouri, Tennessee, Mississippi, Louisiana and Oklahoma, and one in Texas,
# whose short line with Arkansas runs through Texarkana.
OUTSIDE = {
    "Poplar Bluff, Missouri": (36.7570, -90.3929),
    "West Plains, Missouri": (36.7281, -91.8524),
    "Memphis, Tennessee": (35.1495, -90.0490),
    "Dyersburg, Tennessee": (36.0345, -89.3856),
    "Clarksdale, Mississippi": (34.2001, -90.5709),
    "Greenville, Mississippi": (33.4101, -91.0618),
    # Keyed with its parish, because Arkansas has a Monroe COUNTY and
    # county_of() reads "Monroe, Louisiana" as that county.
    "Monroe (Ouachita Parish, Louisiana)": (32.5093, -92.1193),
    "Bastrop, Louisiana": (32.7782, -91.9115),
    "Texarkana, Texas": (33.4300, -94.1000),
    "Sallisaw, Oklahoma": (35.4604, -94.7875),
    "Poteau, Oklahoma": (35.0537, -94.6236),
}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="ar-build-metro-outline")
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
    scale = math.cos(math.radians(34.75))  # Arkansas's middle latitude

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

    How many outer rings Arkansas's fabric dissolves to is a
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
