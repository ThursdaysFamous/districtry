#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for Ohio, the dissolved outline
of the WHOLE STATE, since coverage is statewide from day one — from Census
TIGERweb. Unlike Wisconsin's narrower "roster-covered" ring, this wash makes
no partial claim: METRO_COUNTY_FIPS is all 88 counties, and
DISPATCH_COUNTY_FIPS stays empty on purpose — this instance has no
per-county dispatch layers.

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK WHAT
ANSWERS. Every statewide layer answers in all 88 of them, so the wash claims
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
once. The Lake Erie counties' polygons carry the lake out to the county
line, so the wash runs over that water, and the ring count is a
measurement the --check line prints, not a prediction made here.

Ohio borders Michigan, Indiana, Kentucky, West Virginia and Pennsylvania,
every one a live instance, and Lake Erie, whose northern half is Canada's.
OUTSIDE carries towns just over each line, a point in Lake Erie's Canadian
waters and two places in Ontario, to prove the dissolve did not leak; the
worksheet's negative point is Leamington, Ontario, which no instance will
ever serve.

Usage:
    python3 oh/scripts/build_metro_outline.py                 # writes data/app/metro-outline.json
    python3 oh/scripts/build_metro_outline.py --check         # verify the shipped file, write nothing
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

# Every Ohio county's 3-digit FIPS, the 88 the Census lists for the state
# (001 to 175, odd numbers) — the served area IS the whole state.
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
)
STATE_FIPS = "39"
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

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/oh/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One INSIDE anchor per county: the Census Bureau's own internal point for it
# (INTPTLAT/INTPTLON on TIGERweb State_County layer 1), which the Census
# places inside it by construction. Each was still verified interior against
# its own SIMPLIFIED rings in the shipped state-counties.json, and inside no
# other county, before being trusted here — ring closure alone is not proof a
# dissolve kept every county. All 88 passed when this table was generated,
# 2026-11-11. Keyed by the county's name without "County".
INSIDE = {
    "Adams": (38.83447, -83.47808),
    "Allen": (40.77163, -84.10646),
    "Ashland": (40.84327, -82.27013),
    "Ashtabula": (41.90670, -80.74530),
    "Athens": (39.33286, -82.04587),
    "Auglaize": (40.56118, -84.22401),
    "Belmont": (40.01891, -80.96783),
    "Brown": (38.93138, -83.86677),
    "Butler": (39.43975, -84.56578),
    "Carroll": (40.57988, -81.09079),
    "Champaign": (40.14266, -83.77211),
    "Clark": (39.91703, -83.78368),
    "Clermont": (39.05205, -84.14948),
    "Clinton": (39.42884, -83.79646),
    "Columbiana": (40.77007, -80.77845),
    "Coshocton": (40.29671, -81.93011),
    "Crawford": (40.84852, -82.92478),
    "Cuyahoga": (41.55504, -81.60496),
    "Darke": (40.12970, -84.62212),
    "Defiance": (41.32168, -84.48643),
    "Delaware": (40.27894, -83.00746),
    "Erie": (41.39414, -82.58684),
    "Fairfield": (39.74759, -82.62668),
    "Fayette": (39.55521, -83.46188),
    "Franklin": (39.96987, -83.00909),
    "Fulton": (41.59726, -84.12427),
    "Gallia": (38.81705, -82.30175),
    "Geauga": (41.49932, -81.17351),
    "Greene": (39.68748, -83.89489),
    "Guernsey": (40.05666, -81.49787),
    "Hamilton": (39.19693, -84.54419),
    "Hancock": (41.01053, -83.66642),
    "Hardin": (40.66042, -83.66408),
    "Harrison": (40.29232, -81.09157),
    "Henry": (41.33226, -84.06943),
    "Highland": (39.18442, -83.60136),
    "Hocking": (39.49034, -82.48345),
    "Holmes": (40.56562, -81.93002),
    "Huron": (41.14508, -82.59464),
    "Jackson": (39.01348, -82.61414),
    "Jefferson": (40.39938, -80.76353),
    "Knox": (40.40360, -82.42238),
    "Lake": (41.77814, -81.19733),
    "Lawrence": (38.60384, -82.51707),
    "Licking": (40.09482, -82.47990),
    "Logan": (40.38755, -83.76634),
    "Lorain": (41.43880, -82.17972),
    "Lucas": (41.68232, -83.46890),
    "Madison": (39.89659, -83.40089),
    "Mahoning": (41.01088, -80.77040),
    "Marion": (40.58803, -83.16880),
    "Medina": (41.11617, -81.89976),
    "Meigs": (39.08981, -82.02840),
    "Mercer": (40.53533, -84.63206),
    "Miami": (40.05333, -84.22841),
    "Monroe": (39.72625, -81.09100),
    "Montgomery": (39.75374, -84.29059),
    "Morgan": (39.62495, -81.86170),
    "Morrow": (40.52527, -82.79773),
    "Muskingum": (39.96605, -81.94351),
    "Noble": (39.76724, -81.45254),
    "Ottawa": (41.54550, -83.01261),
    "Paulding": (41.11895, -84.58212),
    "Perry": (39.74319, -82.23795),
    "Pickaway": (39.64895, -83.05283),
    "Pike": (39.07119, -83.05287),
    "Portage": (41.16897, -81.19696),
    "Preble": (39.73881, -84.64476),
    "Putnam": (41.02442, -84.12955),
    "Richland": (40.77416, -82.54277),
    "Ross": (39.32254, -83.05873),
    "Sandusky": (41.35532, -83.14278),
    "Scioto": (38.81489, -82.99868),
    "Seneca": (41.11999, -83.12755),
    "Shelby": (40.33668, -84.20414),
    "Stark": (40.81413, -81.36567),
    "Summit": (41.12185, -81.53493),
    "Trumbull": (41.30637, -80.77040),
    "Tuscarawas": (40.44757, -81.47107),
    "Union": (40.29590, -83.36704),
    "Van Wert": (40.85449, -84.58764),
    "Vinton": (39.25286, -82.48620),
    "Warren": (39.42566, -84.16994),
    "Washington": (39.45060, -81.49054),
    "Wayne": (40.82966, -81.88719),
    "Williams": (41.56496, -84.58432),
    "Wood": (41.36018, -83.62268),
    "Wyandot": (40.83978, -83.31368),
}

# Towns just over each state line, and the worksheet's negative point, each
# checked against TIGERweb's own state layer on 2026-11-11 (Census answer, not
# a guess from a map; controls: the Ohio Statehouse returns Ohio and a point in
# the open Atlantic returns no state), and each lies in no feature of the
# shipped state-counties.json: two in Michigan, two in Indiana, three in
# Kentucky, four in West Virginia and two in Pennsylvania, which TIGERweb
# names; and three in Canada (one in Lake Erie's Canadian waters, two on
# Ontario's land), where it names no state. Keys read "Place (XX)" or name the
# country, so county_of() names no Ohio county.
OUTSIDE = {
    "Monroe (MI)": (41.91640, -83.39770),
    "Adrian (MI)": (41.89750, -84.03720),
    "Fort Wayne (IN)": (41.07930, -85.13940),
    "Richmond (IN)": (39.82890, -84.89020),
    "Covington (KY)": (39.08370, -84.50860),
    "Maysville (KY)": (38.64120, -83.74440),
    "Ashland (KY)": (38.47840, -82.63790),
    "Huntington (WV)": (38.41920, -82.44520),
    "Parkersburg (WV)": (39.26670, -81.56150),
    "Wheeling (WV)": (40.06400, -80.72090),
    "Weirton (WV)": (40.41890, -80.58950),
    "New Castle (PA)": (41.00370, -80.34700),
    "Sharon (PA)": (41.23310, -80.49340),
    "Lake Erie's Canadian waters, 45 km north of Cleveland": (42.45000, -81.50000),
    "Leamington (Ontario, Canada), the worksheet's negative point": (42.05310, -82.59980),
    "Pelee Island (Ontario, Canada)": (41.77000, -82.65000),
}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="oh-build-metro-outline")
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
    scale = math.cos(math.radians(40.4))  # Ohio's middle latitude

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

    How many outer rings Ohio's fabric dissolves to is a
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
