#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for North Carolina, the dissolved
outline of the WHOLE STATE, since coverage is statewide from day one — from
Census TIGERweb. Unlike Wisconsin's narrower "roster-covered" ring, this
wash makes no partial claim yet: METRO_COUNTY_FIPS is all 100 counties, and
DISPATCH_COUNTY_FIPS stays empty on purpose — this instance has no
per-county dispatch layers, because none of its eleven layers is
county-keyed.

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK THE
ROSTER. North Carolina publishes no statewide commissioner-district
geometry (measured 2026-09-29 across seven catalogues; NCGS 153A-20 and
153A-22(f) explain why — the delineation lives in each county clerk's
office as a written description), so when `county-commissioner` starts
answering it will answer county by county, the Illinois shape. On that day
narrow METRO_COUNTY_FIPS to what actually answers and add
DISPATCH_COUNTY_FIPS entries, following the Wisconsin precedent
(`wi/scripts/build_metro_outline.py`) rather than inventing a new shape.
Until then, the outline is simply the state's border.

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
once, and North Carolina is a state where the guess is tempting: the Outer
Banks look like islands. MEASURED 2026-09-29 IT IS ONE RING, 2,292
vertices, because TIGERweb's county fabric is WATER-INCLUSIVE for the
inland sounds — Pamlico Sound belongs to Hyde County and Albemarle Sound to
Tyrrell — so the banks tile continuously through county water rather than
sitting apart.

The consequence for the wash is deliberate and correct where it happens: a
point on open sound water reads INSIDE coverage, because that water
genuinely is assigned to a North Carolina county. It is also why this
instance's negative point is out in the open ATLANTIC east of Hatteras
rather than on a sound picked off a map — a negative point inside Pamlico
Sound would be inside coverage and the assertion would be vacuous.

Usage:
    python3 nc/scripts/build_metro_outline.py                 # writes data/app/metro-outline.json
    python3 nc/scripts/build_metro_outline.py --check         # verify the shipped file, write nothing
"""

import argparse
import json
import math
import os
import sys

# `requests` is imported INSIDE the one function that fetches, not at module
# scope: this module's pure-geometry helpers (simplify, rings_of,
# point_in_rings) are shared machinery this instance's other builders can import
# rather than fork, matching the Wisconsin precedent's reasoning.

TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "State_County/MapServer/1/query")

# Every North Carolina county's 3-digit FIPS — the served area IS the whole state.
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
    "193", "195", "197", "199",
)
STATE_FIPS = "37"
# No dispatch entries: none of this instance's eleven layers is county-keyed yet.
DISPATCH_COUNTY_FIPS = {}

_UNLISTED = sorted(set(DISPATCH_COUNTY_FIPS.values()) - set(METRO_COUNTY_FIPS))
assert not _UNLISTED, (
    "DISPATCH_COUNTY_FIPS names county FIPS %s that METRO_COUNTY_FIPS omits — a "
    "county cannot be served and outside the coverage ring at the same time"
    % _UNLISTED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "metro-outline.json")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/nc/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# One INSIDE anchor per county (area-weighted centroid of the county's
# largest ring, each one verified interior against that county's own rings
# before being trusted here, with a horizontal-scanline fallback for the
# water-carved shapes whose centroid lands outside their own rings) — ring
# closure alone is not proof a dissolve kept every county. All 100 were
# verified interior against their own county's rings when this table was
# generated, 2026-09-29. No OUTSIDE anchors: every North Carolina county is
# served, so there is no unserved neighbour to prove excluded (the negative
# point in metro-worksheet.json, in the open Atlantic east of Hatteras,
# covers "clearly outside the state" instead).
INSIDE = {
    "Alamance": (36.04371, -79.39942),
    "Alexander": (35.92103, -81.17703),
    "Alleghany": (36.49154, -81.12702),
    "Anson": (34.97379, -80.10271),
    "Ashe": (36.43409, -81.50038),
    "Avery": (36.07661, -81.92260),
    "Beaufort": (35.48698, -76.84531),
    "Bertie": (36.06563, -76.96671),
    "Bladen": (34.61464, -78.56371),
    "Brunswick": (34.03887, -78.22741),
    "Buncombe": (35.61118, -82.53010),
    "Burke": (35.74961, -81.70476),
    "Cabarrus": (35.38678, -80.55188),
    "Caldwell": (35.95304, -81.54644),
    "Camden": (36.34112, -76.16095),
    "Carteret": (34.86126, -76.53574),
    "Caswell": (36.39327, -79.33352),
    "Catawba": (35.66204, -81.21506),
    "Chatham": (35.70262, -79.25540),
    "Cherokee": (35.13386, -84.06345),
    "Chowan": (36.12656, -76.60213),
    "Clay": (35.05719, -83.75016),
    "Cleveland": (35.33409, -81.55554),
    "Columbus": (34.26565, -78.65502),
    "Craven": (35.11769, -77.08200),
    "Cumberland": (35.04873, -78.82768),
    "Currituck": (36.36730, -75.93695),
    "Dare": (35.66494, -75.68523),
    "Davidson": (35.79326, -80.21272),
    "Davie": (35.92909, -80.54448),
    "Duplin": (34.93653, -77.93303),
    "Durham": (36.03603, -78.87659),
    "Edgecombe": (35.91288, -77.59706),
    "Forsyth": (36.13057, -80.25636),
    "Franklin": (36.08277, -78.28570),
    "Gaston": (35.29435, -81.18024),
    "Gates": (36.44494, -76.70053),
    "Graham": (35.35017, -83.83358),
    "Granville": (36.30407, -78.65272),
    "Greene": (35.48500, -77.67576),
    "Guilford": (36.07947, -79.78892),
    "Halifax": (36.25745, -77.65173),
    "Harnett": (35.36888, -78.86933),
    "Haywood": (35.55606, -82.98217),
    "Henderson": (35.33623, -82.47996),
    "Hertford": (36.35864, -76.98071),
    "Hoke": (35.01754, -79.23728),
    "Hyde": (35.40812, -76.14497),
    "Iredell": (35.80704, -80.87345),
    "Jackson": (35.28758, -83.14086),
    "Johnston": (35.51782, -78.36571),
    "Jones": (35.02172, -77.35517),
    "Lee": (35.47519, -79.17148),
    "Lenoir": (35.23877, -77.64125),
    "Lincoln": (35.48560, -81.22353),
    "Macon": (35.15047, -83.42217),
    "Madison": (35.85804, -82.70576),
    "Martin": (35.84321, -77.10923),
    "McDowell": (35.68169, -82.04931),
    "Mecklenburg": (35.24677, -80.83274),
    "Mitchell": (36.01320, -82.16358),
    "Montgomery": (35.33247, -79.90548),
    "Moore": (35.31065, -79.48137),
    "Nash": (35.96725, -77.98644),
    "New Hanover": (34.18156, -77.86560),
    "Northampton": (36.41773, -77.39682),
    "Onslow": (34.70984, -77.41577),
    "Orange": (36.06112, -79.12065),
    "Pamlico": (35.15102, -76.66946),
    "Pasquotank": (36.26502, -76.24924),
    "Pender": (34.51510, -77.88844),
    "Perquimans": (36.17722, -76.40762),
    "Person": (36.39010, -78.97181),
    "Pitt": (35.59330, -77.37450),
    "Polk": (35.27928, -82.16968),
    "Randolph": (35.71034, -79.80600),
    "Richmond": (35.00605, -79.74778),
    "Robeson": (34.64025, -79.10386),
    "Rockingham": (36.39601, -79.77499),
    "Rowan": (35.63943, -80.52475),
    "Rutherford": (35.40260, -81.91983),
    "Sampson": (34.99159, -78.37144),
    "Scotland": (34.84088, -79.48043),
    "Stanly": (35.31192, -80.25100),
    "Stokes": (36.40192, -80.23966),
    "Surry": (36.41465, -80.68792),
    "Swain": (35.48682, -83.49274),
    "Transylvania": (35.20218, -82.79830),
    "Tyrrell": (35.86941, -76.17045),
    "Union": (34.98836, -80.53074),
    "Vance": (36.36492, -78.40793),
    "Wake": (35.79031, -78.65028),
    "Warren": (36.39651, -78.10672),
    "Washington": (35.83926, -76.56931),
    "Watauga": (36.23111, -81.69643),
    "Wayne": (35.36396, -78.00400),
    "Wilkes": (36.20619, -81.16297),
    "Wilson": (35.70515, -77.91866),
    "Yadkin": (36.16053, -80.66523),
    "Yancey": (35.89895, -82.30763),
}
OUTSIDE = {}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
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

    How many outer rings North Carolina's fabric dissolves to is a
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
