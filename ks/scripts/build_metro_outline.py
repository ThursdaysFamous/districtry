#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for Kansas, the dissolved outline
of the WHOLE STATE, since coverage is statewide from day one — from Census
TIGERweb. Unlike Wisconsin's narrower "roster-covered" ring, this wash makes
no partial claim: METRO_COUNTY_FIPS is all 105 counties, and
DISPATCH_COUNTY_FIPS stays empty on purpose — this instance has no
per-county dispatch layers.

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK WHAT
ANSWERS. Every statewide layer answers in all 105 of them, so the wash claims
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

Kansas borders Nebraska, Missouri, Oklahoma and Colorado. Missouri and
Oklahoma are live instances; Colorado is built hidden in this same batch;
Nebraska is in the last batch. Kansas is landlocked, so the worksheet's
negative point sits in Webster County, Nebraska, and the change that makes
Nebraska live moves it.

Usage:
    python3 ks/scripts/build_metro_outline.py                 # writes data/app/metro-outline.json
    python3 ks/scripts/build_metro_outline.py --check         # verify the shipped file, write nothing
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

# Every Kansas county's 3-digit FIPS, read from TIGERweb 2026-11-12 — the served area IS
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
    "177", "179", "181", "183", "185", "187", "189", "191",
    "193", "195", "197", "199", "201", "203", "205", "207",
    "209",
)
STATE_FIPS = "20"
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

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/ks/)"}
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
    "Allen": (37.88423, -95.30094),
    "Anderson": (38.21511, -95.29205),
    "Atchison": (39.53254, -95.31340),
    "Barber": (37.22291, -98.68505),
    "Barton": (38.48124, -98.76784),
    "Bourbon": (37.85610, -94.85093),
    "Brown": (39.82593, -95.56990),
    "Butler": (37.77365, -96.83884),
    "Chase": (38.29947, -96.59403),
    "Chautauqua": (37.15426, -96.24540),
    "Cherokee": (37.16939, -94.84570),
    "Cheyenne": (39.78990, -101.72732),
    "Clark": (37.23383, -99.81387),
    "Clay": (39.34496, -97.16885),
    "Cloud": (39.48733, -97.64139),
    "Coffey": (38.23645, -95.72914),
    "Comanche": (37.18144, -99.25129),
    "Cowley": (37.23451, -96.83725),
    "Crawford": (37.50582, -94.85390),
    "Decatur": (39.78354, -100.45971),
    "Dickinson": (38.86774, -97.15794),
    "Doniphan": (39.78850, -95.14723),
    "Douglas": (38.89642, -95.29095),
    "Edwards": (37.88359, -99.30475),
    "Elk": (37.45603, -96.24464),
    "Ellis": (38.91460, -99.31731),
    "Ellsworth": (38.70085, -98.20536),
    "Finney": (38.04981, -100.73997),
    "Ford": (37.68851, -99.88474),
    "Franklin": (38.55802, -95.27896),
    "Geary": (39.00216, -96.76803),
    "Gove": (38.91724, -100.48736),
    "Graham": (39.35497, -99.87989),
    "Grant": (37.54754, -101.29936),
    "Gray": (37.74451, -100.45172),
    "Greeley": (38.48040, -101.80597),
    "Greenwood": (37.87935, -96.24173),
    "Hamilton": (37.99524, -101.79369),
    "Harper": (37.18818, -98.06659),
    "Harvey": (38.05014, -97.43671),
    "Haskell": (37.55507, -100.87998),
    "Hodgeman": (38.08749, -99.89841),
    "Jackson": (39.41110, -95.79449),
    "Jefferson": (39.23961, -95.37533),
    "Jewell": (39.77701, -98.22262),
    "Johnson": (38.88391, -94.82233),
    "Kearny": (37.99446, -101.30814),
    "Kingman": (37.55295, -98.14453),
    "Kiowa": (37.56123, -99.28654),
    "Labette": (37.19147, -95.29747),
    "Lane": (38.48129, -100.46619),
    "Leavenworth": (39.18951, -95.03898),
    "Lincoln": (39.04723, -98.21438),
    "Linn": (38.21655, -94.84493),
    "Logan": (38.90722, -101.15689),
    "Lyon": (38.45540, -96.16164),
    "Marion": (38.35965, -97.10277),
    "Marshall": (39.78271, -96.52124),
    "McPherson": (38.39581, -97.64749),
    "Meade": (37.24425, -100.36063),
    "Miami": (38.56677, -94.83297),
    "Mitchell": (39.39303, -98.20736),
    "Montgomery": (37.18954, -95.74240),
    "Morris": (38.68820, -96.65145),
    "Morton": (37.18525, -101.80952),
    "Nemaha": (39.79104, -96.00538),
    "Neosho": (37.56428, -95.31568),
    "Ness": (38.48044, -99.90875),
    "Norton": (39.78387, -99.89924),
    "Osage": (38.65021, -95.70826),
    "Osborne": (39.34826, -98.76794),
    "Ottawa": (39.13796, -97.65480),
    "Pawnee": (38.18148, -99.23477),
    "Phillips": (39.78451, -99.34215),
    "Pottawatomie": (39.38219, -96.33711),
    "Pratt": (37.64759, -98.74012),
    "Rawlins": (39.78620, -101.07674),
    "Reno": (37.94818, -98.07835),
    "Republic": (39.82891, -97.65088),
    "Rice": (38.34718, -98.20142),
    "Riley": (39.29121, -96.72749),
    "Rooks": (39.34601, -99.32449),
    "Rush": (38.52360, -99.30918),
    "Russell": (38.91604, -98.77095),
    "Saline": (38.79179, -97.65156),
    "Scott": (38.48188, -100.90636),
    "Sedgwick": (37.68104, -97.46105),
    "Seward": (37.17202, -100.84871),
    "Shawnee": (39.04181, -95.75566),
    "Sheridan": (39.35055, -100.44123),
    "Sherman": (39.35135, -101.71986),
    "Smith": (39.78466, -98.78543),
    "Stafford": (38.03563, -98.71989),
    "Stanton": (37.56593, -101.78938),
    "Stevens": (37.20164, -101.31742),
    "Sumner": (37.23667, -97.49338),
    "Thomas": (39.35768, -101.09376),
    "Trego": (38.92130, -99.86542),
    "Wabaunsee": (38.95515, -96.20126),
    "Wallace": (38.92663, -101.77110),
    "Washington": (39.77672, -97.09561),
    "Wichita": (38.48386, -101.34626),
    "Wilson": (37.55851, -95.74517),
    "Woodson": (37.88819, -95.75847),
    "Wyandotte": (39.11310, -94.76312),
}

# Places just over each line, and the worksheet's negative point, each checked
# against TIGERweb's own state layer on 2026-11-12 (Census answer, not a guess from a
# map; controls: Kansas State Capitol returns Kansas, Boston returns
# Massachusetts, and a point in the open Pacific returns no state). The build and
# --check both refuse if any lies inside the dissolved outline. Keys read
# "Place (XX)", the postal code, so county_of() names no Kansas county.
OUTSIDE = {
    "Kansas City (MO)": (39.0997, -94.5786),
    "Joplin (MO)": (37.0842, -94.5133),
    "St. Joseph (MO)": (39.7675, -94.8467),
    "Miami (OK)": (36.8745, -94.8775),
    "Ponca City (OK)": (36.7070, -97.0856),
    "Alva (OK)": (36.8048, -98.6665),
    "Beaver (OK)": (36.8164, -100.5199),
    "Lamar (CO)": (38.0872, -102.6208),
    "Burlington (CO)": (39.3061, -102.2694),
    "Wray (CO)": (40.0758, -102.2238),
    "Falls City (NE)": (40.0608, -95.6019),
    "Superior (NE)": (40.0209, -98.0698),
    "McCook (NE)": (40.2017, -100.6254),
    "Webster County, Nebraska, north of the Kansas line, the worksheet's negative point": (40.2000, -98.5000),
}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="ks-build-metro-outline")
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
    scale = math.cos(math.radians(38.5))  # Kansas's middle latitude

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

    How many outer rings Kansas's fabric dissolves to is a
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
