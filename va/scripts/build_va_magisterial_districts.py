#!/usr/bin/env python3
"""
Build va/data/app/va-magisterial-districts.json: the Magisterial District
layer, every county subdivision the Census Bureau files for Virginia, drawn
from the Department of Elections' own lines wherever a county's census
subdivisions are its election districts.

    python3 va/scripts/build_va_magisterial_districts.py              # fetch TIGERweb, build, write
    python3 va/scripts/build_va_magisterial_districts.py --source F   # build from a kept fetch
    python3 va/scripts/build_va_magisterial_districts.py --check      # offline, for CI
    python3 va/scripts/build_va_magisterial_districts.py --watch      # has the Census's copy moved?

WHY NOT THE CENSUS'S LINES ALONE. A Virginia county is divided into
magisterial districts, and in most counties they are the districts its board
of supervisors is elected from. The Census Bureau's county subdivisions are
its copy of them, and the copy lags a county's redistricting: measured
2026-10-30 against the districts va/scripts/build_va_local_districts.py draws
from the Department's precincts, the census copy puts a point in another
district on more than 1% of the county's ground in 45 of the 72 counties
below, and on more than half of Dinwiddie County's. Adam chose on 22 October
2026 ("as recommended", the plan's third choice) to draw this level from the
Department's current lines in the counties whose census subdivisions carry
the same names as their election districts, as Mississippi and Louisiana do
with their board districts, to draw the census copy elsewhere, and to count
each independent city as its own subdivision, the way San Francisco is
counted.

WHICH COUNTIES TAKE THE DEPARTMENT'S LINES. A county does when its census
subdivisions and the Department's election districts (va-local-districts.json,
kind "county") are the same set of names, one for one, compared after
`norm_name` takes out the word "district", punctuation, number words and
leading zeros. Ten counties spell a name differently in the two files,
and ALIAS records each spelling (measured 2026-10-30, every one read against
both files): Alleghany's "Clifton Forge" is "Clinton Forge" in the
Department's layer, Montgomery's census "A-1" is its election district "A",
Page's census "1 West Luray" is its "District 1", and Prince Edward's census
"101" is its "1". Measured 2026-10-30: 72 counties match. 19 others are
divided by both and differ in their names or their number, so the census copy
there is not the county's election districts and stays the census copy.
Highland, Madison and Mathews elect their boards at large and the Department
draws no districts there; Arlington is not divided by the Census; the 38
cities are one subdivision each.

HOW A MATCHED COUNTY IS DRAWN. Each district is the Department's district
inside the county's census ground, together with whatever of the census
copy's same-named district the Department's precincts leave undrawn (water,
mostly, and slivers along the county line):

    H_k = (D_k intersected with P) united with (T_k minus the union of the D's)

where P is the union of the county's census subdivisions. So the county keeps
exactly the census copy's ground and its edges at the county line, where it
meets a neighbour drawn from the census, and inside it every line is the
Department's. The result is snapped to the file's 6-decimal grid by shapely's
set_precision, which keeps it valid, and parts under a square metre are
dropped.

THE CENSUS COPY IS DRAWN TO WITHIN 12 METRES, the precinct file's setting:
one mapshaper run (Douglas-Peucker, keep-shapes, interval 12) over all 552
subdivisions, so an edge two subdivisions share is simplified once. Every
source vertex's distance to the drawn line is measured
(scripts/boundary_fidelity.py) and held to FIDELITY_CEILING_M, bar the one
dropped part ACCEPTED_STRAYS declares.

WHAT IS CHECKED BEFORE WRITING. All 552 subdivisions and the 72 matched
counties; every alias used; no two features overlapping wider than half a
metre; each county covering the ground its census subdivisions cover; inside
each matched county's census ground, every Department district answered by
its own feature at an interior point, and 20,000 points sampled across the
state answered at most once and, wherever both files answer in the same
county, by the same district.

--check is offline and stdlib only: the shipped file and the Department's
district file against the hashes recorded when this file was built (so a
redrawn va-local-districts.json fails until this is rebuilt), the matching
re-derived from the names both files ship, and the Department's districts
sampled against the shipped file. --watch reads the live layer's names and
areas, no geometry, against the recorded fingerprint.
"""

import argparse
import datetime
import gzip
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(INSTANCE), "scripts"))

import boundary_fidelity  # noqa: E402  (shared, stdlib only)

DATA = os.path.join(INSTANCE, "data", "app")
OUT = os.path.join(DATA, "va-magisterial-districts.json")
DISTRICTS = os.path.join(DATA, "va-local-districts.json")
RECORD = os.path.join(INSTANCE, "data", "source", "va-magisterial-districts.record.json")

LAYER = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
         "Places_CouSub_ConCity_SubMCD/MapServer/1")
FIELDS = "GEOID,NAME,BASENAME,STATE,COUNTY,LSADC,FUNCSTAT,AREALAND,AREAWATER"
SHIPPED_PROPS = ("GEOID", "NAME", "BASENAME", "COUNTY", "LSADC", "FUNCSTAT")
USER_AGENT = "districtry/1.0 (+https://districtry.com/va/)"
PAGE = 100
MAPSHAPER = "mapshaper@0.6.102"  # pinned, as in build_legislative_boundaries.py
SIMPLIFY = "interval=12"
PRECISION = "0.000001"

EXPECT_FEATURES = 552   # 513 magisterial districts, 38 cities, Arlington (2026-10-29)
EXPECT_MATCHED = 72     # counties drawn from the Department's lines (2026-10-30)

# 15 m, PINNED with headroom over the 13.1 m worst stray the first build
# measured at a 12 m interval (2026-10-30). A ceiling recomputed from the
# build it checks could never fail; the measured stray prints on every run.
FIDELITY_CEILING_M = 15.0

# A stray past the ceiling that is one whole part mapshaper dropped, declared
# rather than forgiven: keep-shapes keeps one ring of a feature, and a part
# this small cannot survive the simplification. Re-measured on every build,
# and the build FAILS when the part is gone from the source, is no longer
# that small, no longer strays, or the feature strays past the ceiling once
# the part is set aside. `answer_after` is what the shipped file tells a
# reader at the part's interior point, which --check re-reads offline.
ACCEPTED_STRAYS = {
    "5115390928": {
        "name": "Coles district",
        "county": "Prince William County",
        "part_m2": 13.6,
        "point": (-77.3865275, 38.673995),
        "stray_m": 682.5,
        "answer_after": ("5115394943", "department"),  # Occoquan district
        "why": ("A 13.6 m2 detached part of the census copy's Coles district, "
                "inside Occoquan district. Prince William County is drawn "
                "from the Department's lines, which put the point in "
                "Occoquan, so no reader is told the census copy's answer "
                "here either way."),
        "measured": "2026-10-30",
    },
}

# Overlap and cover tolerances. Snapping two features drawn from different
# files to one grid leaves slivers a few centimetres wide where they meet, so
# an overlap counts only when it is wider than half a metre
# (OVERLAP_WIDTH_DEG on each side) and at least a square metre in area.
OVERLAP_MIN_M2 = 1.0
OVERLAP_WIDTH_DEG = 2.5e-6
# Each county's features must cover the ground its census subdivisions cover.
# Snapping moves a line by up to half a grid cell (about 5 cm), which along a
# county's whole edge adds up to hundreds of square metres of sliver
# (measured 2026-10-30: up to 1,962 m2 in a county, all of it narrower than
# half a metre), so the test is by width, as for overlaps: no part of the
# difference wider than half a metre and a square metre or more in area.
SAMPLE_POINTS = 20000
CHECK_PER_DISTRICT = 5   # --check's points inside each Department district
CHECK_STATEWIDE = 3000   # --check's points across the state, each answered at most once
STATE_BBOX = (-83.7, 36.5, -75.2, 39.5)

WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
         "six": "6", "seven": "7", "eight": "8"}

# (county code, the census name as norm_name reads it) -> the Department's
# name as norm_name reads it. Each was read in both files on 2026-10-30; an
# entry the build does not use fails it.
ALIAS = {
    # Alleghany County: the census's "Clifton Forge East/West"; the
    # Department's layer spells the town Clinton Forge
    ("005", "clifton forge east"): "clinton forge east",
    ("005", "clifton forge west"): "clinton forge west",
    ("027", "rock lick"): "rocklick",          # Buchanan
    ("035", "piper gap"): "pipers gap",        # Carroll
    ("051", "sand lick"): "sandlick",          # Dickenson
    ("069", "red bud"): "redbud",              # Frederick
    ("077", "wilson creek"): "wilson",         # Grayson
    ("109", "green spring"): "green springs",  # Louisa
    # Montgomery: the census's "A-1" to "G-1" are its districts A to G
    ("121", "a 1"): "a", ("121", "b 1"): "b", ("121", "c 1"): "c", ("121", "d 1"): "d",
    ("121", "e 1"): "e", ("121", "f 1"): "f", ("121", "g 1"): "g",
    # Page: the census's names carry the place after the number
    ("139", "1 west luray"): "1", ("139", "2 east luray"): "2", ("139", "3 marksville"): "3",
    ("139", "4 newport"): "4", ("139", "5 shenandoah"): "5",
    # Prince Edward: the census's 101 to 801 are its districts 1 to 8
    ("147", "101"): "1", ("147", "201"): "2", ("147", "301"): "3", ("147", "401"): "4",
    ("147", "501"): "5", ("147", "601"): "6", ("147", "701"): "7", ("147", "801"): "8",
}


def fail(msg):
    print("build_va_magisterial_districts: FAIL: %s" % msg, file=sys.stderr)
    raise SystemExit(1)


def norm_name(s):
    s = str(s).lower()
    s = re.sub(r"\bdistrict\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = " ".join(WORDS.get(w, w) for w in s.split())
    return re.sub(r"\b0+(\d)", r"\1", s)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def department_by_county(districts):
    out = {}
    for f in districts["features"]:
        p = f["properties"]
        if p.get("kind") == "county":
            out.setdefault(p["countyFips"][2:], []).append(f)
    return out


def match_counties(census_feats, dept_by_county):
    """{county code: {census GEOID: Department key}} for every county whose
    census names and election district names are one set, and the set of
    ALIAS entries used. Reads only names, so --check can re-derive it from
    the shipped file."""
    by_county = {}
    for f in census_feats:
        by_county.setdefault(f["properties"]["COUNTY"], []).append(f)
    matched, used = {}, set()
    for code in sorted(by_county):
        dept = dept_by_county.get(code)
        if not dept:
            continue
        cen = {}
        for f in by_county[code]:
            k = norm_name(f["properties"]["BASENAME"])
            if (code, k) in ALIAS:
                k = ALIAS[(code, k)]
                used.add((code, norm_name(f["properties"]["BASENAME"])))
            cen.setdefault(k, []).append(f["properties"]["GEOID"])
        dn = {}
        for f in dept:
            dn.setdefault(norm_name(f["properties"]["name"]), []).append(f["properties"]["key"])
        if (sorted(cen) == sorted(dn) and all(len(v) == 1 for v in cen.values())
                and all(len(v) == 1 for v in dn.values())):
            matched[code] = {cen[k][0]: dn[k][0] for k in cen}
    return matched, used


# ---------- fetch ----------
def fetch_source():
    import requests  # noqa: PLC0415
    from scraper_common import require_robots_once  # noqa: PLC0415

    url = LAYER + "/query"
    require_robots_once(url, USER_AGENT, label="build_va_magisterial_districts")
    base = {"where": "STATE='51'", "outFields": FIELDS, "outSR": "4326", "f": "geojson",
            "geometryPrecision": "6", "orderByFields": "GEOID"}
    feats, offset = [], 0
    while True:
        r = requests.get(url, params=dict(base, resultOffset=offset, resultRecordCount=PAGE),
                         headers={"User-Agent": USER_AGENT}, timeout=300)
        r.raise_for_status()
        got = r.json()
        if "error" in got:
            # an API error is not an empty answer
            fail("TIGERweb answered an error: %r" % got["error"])
        page = got.get("features") or []
        feats += page
        offset += len(page)
        if not page or (not got.get("exceededTransferLimit") and len(page) < PAGE):
            break
    return {"type": "FeatureCollection", "features": feats}


def fetch_fingerprint():
    import requests  # noqa: PLC0415
    from scraper_common import require_robots_once  # noqa: PLC0415

    url = LAYER + "/query"
    require_robots_once(url, USER_AGENT, label="build_va_magisterial_districts")
    r = requests.get(url, params={"where": "STATE='51'", "outFields": FIELDS,
                                  "returnGeometry": "false", "orderByFields": "GEOID",
                                  "f": "json"},
                     headers={"User-Agent": USER_AGENT}, timeout=300)
    r.raise_for_status()
    got = r.json()
    if "error" in got:
        fail("TIGERweb answered an error: %r" % got["error"])
    if got.get("exceededTransferLimit"):
        fail("TIGERweb's attribute answer hit its transfer cap — page it")
    return fingerprint([f["attributes"] for f in got.get("features") or []])


def fingerprint(rows):
    """Which subdivisions the state has, by name, and each one's land and
    water area to the square metre, as the Census derives them from the
    shape. Sorted, so record order cannot move it."""
    lines = sorted("%s|%s|%d|%d" % (r.get("GEOID"), r.get("NAME"),
                                    int(r.get("AREALAND") or 0), int(r.get("AREAWATER") or 0))
                   for r in rows)
    return {"subdivisions": len(lines),
            "sha256": sha256_bytes("\n".join(lines).encode())}


def normalise(source):
    feats = []
    seen = set()
    for f in source.get("features") or []:
        p = f.get("properties") or {}
        geoid = str(p.get("GEOID") or "")
        if not re.fullmatch(r"51\d{8}", geoid):
            fail("a subdivision with an unreadable GEOID: %r" % p)
        if geoid in seen:
            fail("subdivision %s appears twice" % geoid)
        seen.add(geoid)
        if not f.get("geometry"):
            fail("subdivision %s has no geometry" % geoid)
        props = {k: p.get(k) for k in SHIPPED_PROPS}
        props["COUNTY"] = str(props["COUNTY"])
        feats.append({"type": "Feature", "properties": props, "geometry": f["geometry"]})
    feats.sort(key=lambda f: f["properties"]["GEOID"])
    return feats


def run_mapshaper(src_feats):
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "src.geojson")
        out = os.path.join(tmp, "out.geojson")
        with open(src, "w") as f:
            json.dump({"type": "FeatureCollection", "features": src_feats}, f)
        subprocess.run(["npx", "-y", MAPSHAPER, src, "-simplify", "dp", "keep-shapes", SIMPLIFY,
                        "-o", "precision=" + PRECISION, "format=geojson", out],
                       check=True, cwd=INSTANCE)
        with open(out) as f:
            got = json.load(f)
    return [{"type": "Feature", "properties": f["properties"], "geometry": f["geometry"]}
            for f in got["features"]]


# ---------- the declared stray ----------
def _ring_area_m2(ring):
    lat = ring[0][1]
    sx = 111320.0 * math.cos(math.radians(lat))
    a = 0.0
    for i in range(len(ring) - 1):
        a += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return abs(a) / 2 * sx * 110540.0


def check_strays(src_feats, drawn_feats):
    """(problems, worst stray outside the declarations, message lines)."""
    problems, lines = [], []
    strays = boundary_fidelity.worst_strays(src_feats, drawn_feats, "GEOID")
    if len(strays) != len(src_feats):
        problems.append("%d of %d subdivisions matched between the source and the drawn file"
                        % (len(strays), len(src_feats)))
    src = {f["properties"]["GEOID"]: f for f in src_feats}
    drawn = {f["properties"]["GEOID"]: f for f in drawn_feats}
    worst, wkey = 0.0, None
    for key, (w, _) in strays.items():
        if key in ACCEPTED_STRAYS:
            continue
        if w > worst:
            worst, wkey = w, key
        if w > FIDELITY_CEILING_M:
            problems.append("%s (%s) strays %.1f m from the true line, past the %.0f m ceiling"
                            % (src[key]["properties"]["NAME"], key, w, FIDELITY_CEILING_M))
    for key, decl in sorted(ACCEPTED_STRAYS.items()):
        if key not in src:
            problems.append("ACCEPTED_STRAYS names %s, which is no longer in the source" % key)
            continue
        w, where = strays.get(key, (0.0, None))
        if abs(w - decl["stray_m"]) > 1.0 or where is None or (
                abs(where[0] - decl["point"][0]) > 1e-4 or abs(where[1] - decl["point"][1]) > 1e-4):
            problems.append("ACCEPTED_STRAYS' %s now strays %.1f m at %r, declared %.1f m at %r"
                            % (key, w, where, decl["stray_m"], decl["point"]))
            continue
        geom = src[key]["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        keep, dropped = [], []
        for poly in polys:
            hit = boundary_fidelity_point_in_ring(decl["point"], poly[0])
            (dropped if hit else keep).append(poly)
        area = sum(_ring_area_m2(p[0]) for p in dropped)
        if len(dropped) != 1 or abs(area - decl["part_m2"]) > max(2.0, 0.2 * decl["part_m2"]):
            problems.append("ACCEPTED_STRAYS' %s: the declared part is %d part(s) of %.1f m2, "
                            "declared one of %.1f m2" % (key, len(dropped), area, decl["part_m2"]))
            continue
        rest = {"type": "Feature", "properties": src[key]["properties"],
                "geometry": {"type": "MultiPolygon", "coordinates": keep}}
        w2 = boundary_fidelity.worst_strays([rest], [drawn[key]], "GEOID")[key][0]
        if w2 > FIDELITY_CEILING_M:
            problems.append("%s strays %.1f m once its declared part is set aside, past the "
                            "%.0f m ceiling" % (key, w2, FIDELITY_CEILING_M))
        lines.append("declared stray: %s (%s, %s), a %.1f m2 part dropped, %.1f m; the rest "
                     "%.1f m" % (decl["name"], key, decl["county"], area, w, w2))
    lines.append("fidelity: worst stray %.1f m (%s) against a %.0f m ceiling, %d declared"
                 % (worst, wkey, FIDELITY_CEILING_M, len(ACCEPTED_STRAYS)))
    return problems, lines


def boundary_fidelity_point_in_ring(pt, ring):
    x, y = pt
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


# ---------- the hybrid (shapely) ----------
def m2(g):
    if g.is_empty:
        return 0.0
    return g.area * 111320.0 ** 2 * math.cos(math.radians(g.representative_point().y))


def polygons(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    if g.geom_type in ("MultiPolygon", "GeometryCollection"):
        out = []
        for x in g.geoms:
            out += polygons(x)
        return out
    return []


def clean(g):
    from shapely import make_valid  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415

    ps = [p for p in polygons(make_valid(g)) if m2(p) >= 1.0]
    return unary_union(ps) if ps else None


def rounded(o):
    if isinstance(o, float):
        return round(o, 6)
    if isinstance(o, (list, tuple)):
        return [rounded(x) for x in o]
    if isinstance(o, dict):
        return {k: rounded(v) for k, v in o.items()}
    return o


def build_hybrid(census, districts, matched):
    from shapely import set_precision  # noqa: PLC0415
    from shapely.geometry import mapping, shape  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415

    dept = {f["properties"]["key"]: f for f in districts["features"]}
    by_county = {}
    for f in census:
        by_county.setdefault(f["properties"]["COUNTY"], []).append(f)
    out, differs = [], {}
    for code in sorted(by_county):
        feats = by_county[code]
        if code not in matched:
            for f in feats:
                p = dict(f["properties"], lines="census")
                out.append({"type": "Feature", "properties": p, "geometry": f["geometry"]})
            continue
        pairs = matched[code]
        T = {f["properties"]["GEOID"]: shape(f["geometry"]).buffer(0) for f in feats}
        P = unary_union(list(T.values()))
        D = {g: shape(dept[pairs[g]]["geometry"]).buffer(0) for g in T}
        DU = unary_union(list(D.values()))
        moved = 0.0
        for f in feats:
            g = f["properties"]["GEOID"]
            h = D[g].intersection(P).union(T[g].difference(DU))
            h = clean(set_precision(clean(h), 1e-6))
            if h is None:
                fail("%s (%s) is empty once drawn from the Department's lines"
                     % (f["properties"]["NAME"], g))
            moved += m2(T[g].difference(h))
            p = dict(f["properties"], lines="department", district=pairs[g])
            out.append({"type": "Feature", "properties": p, "geometry": rounded(mapping(h))})
        differs[code] = moved / m2(P)
    return out, differs


def gate_hybrid(out, census, districts, matched):
    """Problems with the drawn file, and lines to print."""
    from shapely import STRtree  # noqa: PLC0415
    from shapely.geometry import Point, shape  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415

    problems, lines = [], []
    geoms = [shape(f["geometry"]) for f in out]
    invalid = [out[i]["properties"]["GEOID"] for i, g in enumerate(geoms) if not g.is_valid]
    bad_dept = [k for k in invalid if any(f["properties"]["GEOID"] == k and
                                          f["properties"]["lines"] == "department" for f in out)]
    if bad_dept:
        problems.append("%d feature(s) drawn from the Department's lines are not valid: %s"
                        % (len(bad_dept), ", ".join(bad_dept[:5])))
    lines.append("validity: %d census copies with a ring touching itself, as mapshaper "
                 "drew them (the app's even-odd test reads them as drawn): %s"
                 % (len(invalid), ", ".join(invalid) or "none"))
    geoms = [g if g.is_valid else g.buffer(0) for g in geoms]
    tree = STRtree(geoms)
    overlaps = []
    for i, g in enumerate(geoms):
        for j in tree.query(g):
            if j <= i:
                continue
            x = g.intersection(geoms[j])
            if m2(x) >= OVERLAP_MIN_M2 and not x.buffer(-OVERLAP_WIDTH_DEG).is_empty:
                overlaps.append((m2(x), out[i]["properties"]["GEOID"], out[j]["properties"]["GEOID"]))
    if overlaps:
        overlaps.sort(reverse=True)
        problems.append("%d pair(s) of features overlap wider than half a metre, worst %.1f m2 "
                        "(%s and %s)" % ((len(overlaps),) + overlaps[0]))
    # each county covers its census ground
    cen_by, out_by = {}, {}
    for f in census:
        cen_by.setdefault(f["properties"]["COUNTY"], []).append(shape(f["geometry"]).buffer(0))
    for f, g in zip(out, geoms):
        out_by.setdefault(f["properties"]["COUNTY"], []).append(g)
    worst = (0.0, None)
    for code in cen_by:
        d = unary_union(cen_by[code]).symmetric_difference(unary_union(out_by.get(code, [])))
        worst = max(worst, (m2(d), code))
        wide = [x for x in polygons(d.buffer(-OVERLAP_WIDTH_DEG)) if m2(x) > 0]
        wide = [x for x in polygons(d) if m2(x) >= OVERLAP_MIN_M2
                and not x.buffer(-OVERLAP_WIDTH_DEG).is_empty] if wide else []
        if wide:
            problems.append("county %s's features differ from its census ground by %d part(s) "
                            "wider than half a metre, %.1f m2 in all"
                            % (code, len(wide), sum(m2(x) for x in wide)))
    lines.append("cover: every county its census ground to within half a metre; the slivers "
                 "snapping leaves sum to at most %.1f m2 in a county (%s)" % worst)
    # every Department district answered by its own feature inside the census ground
    dept = {f["properties"]["key"]: f for f in districts["features"]}
    index = {f["properties"]["GEOID"]: i for i, f in enumerate(out)}
    checked = 0
    for code, pairs in sorted(matched.items()):
        P = unary_union(cen_by[code])
        for geoid, key in sorted(pairs.items()):
            part = shape(dept[key]["geometry"]).buffer(0).intersection(P)
            inner = part.buffer(-5e-6)
            q = (inner if not inner.is_empty else part).representative_point()
            hits = [out[j]["properties"]["GEOID"] for j in tree.query(q) if geoms[j].covers(q)]
            checked += 1
            if hits != [geoid]:
                problems.append("at an interior point of the Department's %s the drawn file "
                                "answers %s, not %s" % (key, hits, geoid))
    # a statewide sample: answered at most once, and by the Department's district
    dtree_geoms = [shape(f["geometry"]).buffer(0) for f in districts["features"]]
    dtree = STRtree(dtree_geoms)
    rng = random.Random(7)
    n = twice = agree = compared = 0
    while n < SAMPLE_POINTS:
        q = Point(rng.uniform(STATE_BBOX[0], STATE_BBOX[2]), rng.uniform(STATE_BBOX[1], STATE_BBOX[3]))
        hits = [j for j in tree.query(q) if geoms[j].covers(q)]
        if not hits:
            continue
        n += 1
        if len(hits) > 1:
            twice += 1
            continue
        p = out[hits[0]]["properties"]
        if p["lines"] != "department":
            continue
        dd = [districts["features"][j]["properties"] for j in dtree.query(q)
              if dtree_geoms[j].covers(q)]
        dd = [d for d in dd if d.get("kind") == "county" and d["countyFips"][2:] == p["COUNTY"]]
        if not dd:
            continue
        compared += 1
        if dd[0]["key"] == p["district"]:
            agree += 1
    if twice:
        problems.append("%d of %d sampled points are answered by two features" % (twice, n))
    if agree != compared:
        problems.append("the Department's districts and the drawn file disagree at %d of %d "
                        "sampled points" % (compared - agree, compared))
    lines.append("agreement: each of %d Department districts answered by its own feature at an "
                 "interior point; %d sampled points answered once each, the Department's "
                 "district at %d of %d where both answer in one county"
                 % (checked, n, agree, compared))
    _ = index
    return problems, lines


def shipped_bytes(feats):
    return json.dumps({"type": "FeatureCollection", "features": feats},
                      separators=(",", ":")).encode()


def build(source):
    with open(DISTRICTS, "rb") as f:
        districts_raw = f.read()
    districts = json.loads(districts_raw)
    src = normalise(source)
    if len(src) != EXPECT_FEATURES:
        fail("TIGERweb carries %d subdivisions for Virginia, expected %d — read what changed "
             "before changing EXPECT_FEATURES" % (len(src), EXPECT_FEATURES))
    dept = department_by_county(districts)
    matched, used = match_counties(src, dept)
    unused = sorted(set(ALIAS) - used)
    problems = []
    if unused:
        problems.append("ALIAS entries no census name used: %r" % unused)
    if len(matched) != EXPECT_MATCHED:
        problems.append("%d counties match, expected %d — read which before changing "
                        "EXPECT_MATCHED" % (len(matched), EXPECT_MATCHED))
    census = run_mapshaper(src)
    if [f["properties"]["GEOID"] for f in census] != [f["properties"]["GEOID"] for f in src]:
        fail("mapshaper's output does not carry the source's subdivisions in order")
    p2, lines = check_strays(src, census)
    problems += p2
    out, differs = build_hybrid(census, districts, matched)
    p3, l3 = gate_hybrid(out, census, districts, matched)
    problems += p3
    lines += l3
    shares = sorted(differs.values())
    lines.append("the census copy against the Department's lines, in the %d matched counties: "
                 "another district on at most 1%% of the county's ground in %d, at most 5%% in %d, "
                 "worst %.1f%% (%s)" % (len(shares), sum(1 for s in shares if s <= 0.01),
                                       sum(1 for s in shares if s <= 0.05),
                                       100 * max(shares), max(differs, key=differs.get)))
    for line in lines:
        print(line)
    if problems:
        for p in problems:
            print("build_va_magisterial_districts: FAIL: " + p, file=sys.stderr)
        raise SystemExit(1)
    raw = shipped_bytes(out)
    with open(OUT, "wb") as f:
        f.write(raw)
    county_names = {}
    for f in districts["features"]:
        county_names[f["properties"]["countyFips"][2:]] = f["properties"]["locality"]
    record = {
        "_comment": ("Written by va/scripts/build_va_magisterial_districts.py; held to the tree "
                     "by its --check. A change to va-local-districts.json fails that check "
                     "until this file is rebuilt."),
        "source": LAYER,
        "fetched": datetime.date.today().isoformat(),
        "fingerprint": fingerprint([f["properties"] for f in source["features"]]),
        "department_sha256": sha256_bytes(districts_raw),
        "shipped_sha256": sha256_bytes(raw),
        "features": len(out),
        "department_lines": {code: county_names.get(code, code) for code in sorted(matched)},
        "simplify": "dp keep-shapes " + SIMPLIFY,
    }
    with open(RECORD, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    print("wrote va/data/app/%s: %d subdivisions, %d of them in the %d counties drawn from the "
          "Department's lines; %d bytes, %d gzipped"
          % (os.path.basename(OUT), len(out),
             sum(1 for f in out if f["properties"]["lines"] == "department"), len(matched),
             len(raw), len(gzip.compress(raw))))


# ---------- --check (offline, stdlib) ----------
def _bbox(geom):
    xs, ys = [], []
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        for ring in poly:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def _inside(pt, geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        inside = False
        for ring in poly:
            if boundary_fidelity_point_in_ring(pt, ring):
                inside = not inside
        if inside:
            return True
    return False


def _model(feats):
    return [(_bbox(f["geometry"]), f) for f in feats]


def _hits(model, pt):
    return [f for (x0, y0, x1, y1), f in model
            if x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1 and _inside(pt, f["geometry"])]


def check():
    problems = []
    with open(OUT, "rb") as f:
        raw = f.read()
    with open(DISTRICTS, "rb") as f:
        districts_raw = f.read()
    with open(RECORD, encoding="utf-8") as f:
        record = json.load(f)
    if sha256_bytes(raw) != record.get("shipped_sha256"):
        problems.append("the shipped file does not hash to what the builder recorded — rebuild "
                        "it rather than editing it by hand")
    if sha256_bytes(districts_raw) != record.get("department_sha256"):
        problems.append("va-local-districts.json has changed since this file was built from it "
                        "— rebuild with va/scripts/build_va_magisterial_districts.py")
    geo = json.loads(raw)
    districts = json.loads(districts_raw)
    feats = geo["features"]
    if len(feats) != EXPECT_FEATURES or len(feats) != record.get("features"):
        problems.append("%d subdivisions shipped, expected %d" % (len(feats), EXPECT_FEATURES))
    geoids = [f["properties"].get("GEOID") for f in feats]
    if geoids != sorted(set(geoids)):
        problems.append("the subdivisions are not one each, in GEOID order")
    for f in feats:
        p = f["properties"]
        want = set(SHIPPED_PROPS) | {"lines"} | ({"district"} if p.get("lines") == "department" else set())
        if set(p) != want or p.get("lines") not in ("department", "census"):
            problems.append("%s carries %s" % (p.get("GEOID"), sorted(p)))
    matched, used = match_counties(feats, department_by_county(districts))
    if sorted(set(ALIAS) - used):
        problems.append("ALIAS entries no shipped census name uses: %r" % sorted(set(ALIAS) - used))
    if sorted(matched) != sorted(record.get("department_lines") or {}):
        problems.append("the counties whose names match are not the counties recorded as drawn "
                        "from the Department's lines")
    for f in feats:
        p = f["properties"]
        pairs = matched.get(p["COUNTY"])
        if pairs is None and p["lines"] != "census":
            problems.append("%s is drawn from the Department's lines in a county whose names "
                            "do not match" % p["GEOID"])
        if pairs is not None and (p["lines"] != "department" or p.get("district") != pairs.get(p["GEOID"])):
            problems.append("%s should be the Department's %s" % (p["GEOID"], pairs.get(p["GEOID"])))
    model = _model(feats)
    for key, decl in sorted(ACCEPTED_STRAYS.items()):
        hits = [(h["properties"]["GEOID"], h["properties"]["lines"]) for h in _hits(model, decl["point"])]
        if hits != [decl["answer_after"]]:
            problems.append("at ACCEPTED_STRAYS' %s the shipped file answers %r, declared %r"
                            % (key, hits, decl["answer_after"]))
    # the Department's districts, sampled: wherever the shipped file answers a
    # feature of the same county, it is that district's
    by_key = {}
    for f in feats:
        if f["properties"]["lines"] == "department":
            by_key[f["properties"]["district"]] = f["properties"]["GEOID"]
    rng = random.Random(30)
    compared = agree = 0
    for f in districts["features"]:
        p = f["properties"]
        if p["key"] not in by_key:
            continue
        x0, y0, x1, y1 = _bbox(f["geometry"])
        got, tries = 0, 0
        while got < CHECK_PER_DISTRICT and tries < 400:
            tries += 1
            pt = (rng.uniform(x0, x1), rng.uniform(y0, y1))
            if not _inside(pt, f["geometry"]):
                continue
            got += 1
            hits = [h for h in _hits(model, pt) if h["properties"]["COUNTY"] == p["countyFips"][2:]]
            if not hits:
                continue
            compared += 1
            if len(hits) == 1 and hits[0]["properties"]["GEOID"] == by_key[p["key"]]:
                agree += 1
            else:
                problems.append("inside the Department's %s the shipped file answers %s"
                                % (p["key"], [h["properties"]["GEOID"] for h in hits]))
    n = twice = 0
    while n < CHECK_STATEWIDE:
        pt = (rng.uniform(STATE_BBOX[0], STATE_BBOX[2]), rng.uniform(STATE_BBOX[1], STATE_BBOX[3]))
        hits = _hits(model, pt)
        if not hits:
            continue
        n += 1
        if len(hits) > 1:
            twice += 1
    if twice:
        problems.append("%d of %d points across the state are answered by two subdivisions"
                        % (twice, n))
    if problems:
        for p in problems:
            print("build_va_magisterial_districts: FAIL: " + p)
        raise SystemExit(1)
    print("build_va_magisterial_districts --check: OK — %d subdivisions, %d counties drawn from "
          "the Department's lines and held to va-local-districts.json, %d of %d sampled points "
          "inside its districts answered by the same district, %d points across the state "
          "answered once each" % (len(feats), len(matched), agree, compared, n))


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--check", action="store_true", help="offline: hold the shipped file to its record")
    ap.add_argument("--watch", action="store_true",
                    help="compare the live layer with the recorded fingerprint; exit 1 on a change")
    ap.add_argument("--source", help="build from a saved fetch instead of the network")
    ap.add_argument("--save-source", help="also write the raw fetch here")
    args = ap.parse_args()
    if args.check:
        check()
        return
    if args.watch:
        with open(RECORD, encoding="utf-8") as f:
            record = json.load(f)
        live = fetch_fingerprint()
        if live != record["fingerprint"]:
            print("build_va_magisterial_districts --watch: THE CENSUS'S COPY HAS CHANGED. "
                  "Recorded %s (%d subdivisions, fetched %s); live %s (%d). Rebuild this file "
                  "and bump the service worker's cache name."
                  % (record["fingerprint"]["sha256"][:12], record["fingerprint"]["subdivisions"],
                     record["fetched"], live["sha256"][:12], live["subdivisions"]))
            raise SystemExit(1)
        print("build_va_magisterial_districts --watch: unchanged since %s (%d subdivisions)"
              % (record["fetched"], live["subdivisions"]))
        return
    if args.source:
        with open(args.source, encoding="utf-8") as f:
            source = json.load(f)
    else:
        source = fetch_source()
        if args.save_source:
            with open(args.save_source, "w", encoding="utf-8") as f:
                json.dump(source, f)
    build(source)


if __name__ == "__main__":
    main()
