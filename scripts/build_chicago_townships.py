#!/usr/bin/env python3
"""Chicago's eight townships, for the Illinois township layer.

WHY THIS FILE EXISTS. The township layer draws the Census Bureau's county
subdivisions, and the Census draws Chicago as ONE subdivision, "Chicago city"
(GEOID 1703114000). Chicago still has eight townships in law -- Hyde Park,
Jefferson, Lake, Lake View, North, Rogers Park, South and West -- with no
township government since 1902; the Cook County Assessor and the Board of
Review use them to group property in the city. A reader asking where
Jefferson Township is got "Chicago city" instead (Adam, 2026-10-14, who chose
to have them drawn).

WHERE THE LINES COME FROM. Cook County GIS, politicalBoundary layer 3
("Political Township"), which draws all 38 Cook townships, the eight Chicago
ones among them. The county's lines and the Census's Chicago outline are two
drawings of related borders and do not agree exactly -- measured 2026-10-14,
the eight cover 593.8 km2 of the Census's 600.9, and 2.0 km2 of them lies
outside it. Most of the 9.1 km2 they leave uncovered is lakefront landfill
the Census's outline carries and the county's shoreline does not (3.7 km2
around McCormick Place, 3.0 km2 at the south lakefront), and the rest is
slivers along the city limit.

SO THE CENSUS OUTLINE DECIDES WHERE CHICAGO IS, AND THE COUNTY DECIDES WHICH
TOWNSHIP. Each township is clipped to the Census's Chicago polygon, so the
eight meet every other layer's city limit exactly and the township layer
still tiles Illinois with no gap and no overlap. Ground inside the Census
outline that no county township covers goes to the township whose line is
NEAREST -- a Voronoi split of points sampled along the townships' own edges
-- which is what extending each township line straight into the landfill
does. That assignment is this builder's, not the county's, and the shipped
file says so in its metadata.

The file is read twice: by il/index.html's township loader, which puts the
eight in place of "Chicago city", and by scripts/mirror_tiger_tiles.py, which
does the same before it builds the township tile archive, so tile and file
answer alike.

  python3 scripts/build_chicago_townships.py           # fetch, build, write
  python3 scripts/build_chicago_townships.py --check   # offline: the shipped file
"""
import argparse
import datetime
import json
import math
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

OUT = os.path.join(ROOT, "il", "data", "app", "chicago-townships.json")

COOK_URL = ("https://gis.cookcountyil.gov/traditional/rest/services/politicalBoundary/"
            "MapServer/3/query")
TIGER_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
             "Places_CouSub_ConCity_SubMCD/MapServer/1/query")
CHICAGO_GEOID = "1703114000"

# Cook's NAME -> the name the card prints, in the Census's own style
# ("Homer township"), so a Chicago township reads like every other one.
TOWNSHIPS = {
    "HYDE PARK": "Hyde Park",
    "JEFFERSON": "Jefferson",
    "LAKE": "Lake",
    "LAKE VIEW": "Lake View",
    "NORTH": "North",
    "ROGERS PARK": "Rogers Park",
    "SOUTH": "South",
    "WEST": "West",
}

PRECISION = 6            # ~0.1 m; the Census's 5-decimal vertices survive exactly
SAMPLE_M = 20            # spacing of the edge points the landfill is split by
# measured 2026-10-14: 593.8 km2 of 600.9 covered by the county's lines; a
# rebuild that covers much less means the county's layer changed shape
MIN_COVERED_SHARE = 0.97
KM2 = 111.32 ** 2 * math.cos(math.radians(41.85))


def fail(msg):
    sys.exit("build_chicago_townships: FAIL — " + msg)


def fetch_geojson(url, params):
    from scraper_common import UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, require_robots_once
    full = url + "?" + urllib.parse.urlencode(params)
    require_robots_once(full, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT,
                        label="build-chicago-townships")
    req = urllib.request.Request(full, headers=UA_HEADERS_ROSTER_BOT)
    with urllib.request.urlopen(req, timeout=120) as r:
        doc = json.load(r)
    if "error" in doc:
        fail("%s answered an error: %s" % (url, doc["error"]))
    return doc


def round_geom(g):
    from shapely import set_precision
    from shapely.geometry import mapping
    g = set_precision(g, 10 ** -PRECISION)
    m = mapping(g)

    def rnd(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], PRECISION), round(c[1], PRECISION)]
        return [rnd(x) for x in c]
    return {"type": m["type"], "coordinates": rnd(m["coordinates"])}


def build():
    from shapely.geometry import MultiPoint, shape
    from shapely.ops import unary_union, voronoi_diagram

    tiger = fetch_geojson(TIGER_URL, {"where": "GEOID='%s'" % CHICAGO_GEOID, "outFields": "GEOID,NAME",
                                      "outSR": 4326, "f": "geojson", "geometryPrecision": 5})
    feats = tiger.get("features") or []
    if len(feats) != 1:
        fail("the Census answered %d features for Chicago city, not 1" % len(feats))
    chicago = shape(feats[0]["geometry"]).buffer(0)

    cook = fetch_geojson(COOK_URL, {"where": "1=1", "outFields": "NAME", "returnGeometry": "true",
                                    "outSR": 4326, "f": "geojson"})
    raw = {}
    for f in cook.get("features") or []:
        n = ((f.get("properties") or {}).get("NAME") or "").strip()
        if n in TOWNSHIPS:
            if n in raw:
                fail("Cook County draws %s twice" % n)
            raw[n] = shape(f["geometry"]).buffer(0)
    missing = sorted(set(TOWNSHIPS) - set(raw))
    if missing:
        fail("Cook County no longer draws %s" % ", ".join(missing))

    # clip to Chicago, then make the eight disjoint (a county drawing can
    # overlap itself by a sliver; the first in name order keeps it)
    clipped, taken = {}, None
    for n in sorted(raw):
        g = raw[n].intersection(chicago)
        if taken is not None:
            g = g.difference(taken)
        clipped[n] = g
        taken = g if taken is None else taken.union(g)
    covered = taken.area / chicago.area
    if covered < MIN_COVERED_SHARE:
        fail("the county's eight townships cover %.1f%% of the Census's Chicago, under the %.0f%% "
             "measured when this was written" % (100 * covered, 100 * MIN_COVERED_SHARE))

    gap = chicago.difference(taken)
    gap_km2 = gap.area * KM2
    # split the uncovered ground by nearest township edge
    near = gap.buffer(0.02)
    step = SAMPLE_M / 111320.0
    pts, owner = [], []
    for n, g in clipped.items():
        edge = g.boundary.intersection(near)
        if edge.is_empty:
            continue
        lines = getattr(edge, "geoms", [edge])
        for ln in lines:
            if ln.length == 0:
                continue
            k = max(1, int(ln.length / step))
            for i in range(k + 1):
                p = ln.interpolate(i / k, normalized=True)
                pts.append((p.x, p.y))
                owner.append(n)
    seen, upts, uown = set(), [], []
    for p, n in zip(pts, owner):
        key = (round(p[0], 7), round(p[1], 7))
        if key in seen:
            continue
        seen.add(key)
        upts.append(p)
        uown.append(n)
    from shapely.strtree import STRtree
    from shapely.geometry import Point
    cells = voronoi_diagram(MultiPoint(upts), envelope=near.envelope)
    tree = STRtree([Point(p) for p in upts])
    extra = {n: [] for n in clipped}
    for cell in cells.geoms:
        idx = tree.query(cell, predicate="intersects")
        hit = None
        for i in idx:
            if cell.contains(Point(upts[i])) or cell.touches(Point(upts[i])):
                hit = i
                break
        if hit is None:
            hit = int(tree.nearest(cell.centroid))
        piece = cell.intersection(gap)
        if not piece.is_empty:
            extra[uown[hit]].append(piece)
    out = {}
    for n, g in clipped.items():
        whole = unary_union([g] + extra[n]).buffer(0) if extra[n] else g
        out[n] = whole.intersection(chicago)
    # final partition: disjoint, inside Chicago, nothing of Chicago left out
    union = unary_union(list(out.values()))
    left = chicago.difference(union).area * KM2
    if left > 0.001:
        fail("%.4f km2 of Chicago is in no township after the split" % left)
    names = sorted(out)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ov = out[a].intersection(out[b]).area * KM2
            if ov > 0.001:
                fail("%s and %s overlap by %.4f km2" % (a, b, ov))

    features = []
    for n in names:
        geom = round_geom(out[n])
        props = {
            "NAME": "%s township" % TOWNSHIPS[n],
            "BASENAME": TOWNSHIPS[n],
            "STATE": "17",
            "COUNTY": "031",
            "COOK_TWP": n,
        }
        features.append({"type": "Feature", "properties": props, "geometry": geom})
        print("  %-12s %7.2f km2 (%6.3f from the uncovered ground)"
              % (n, out[n].area * KM2, sum(p.area for p in extra[n]) * KM2))
    doc = {
        "type": "FeatureCollection",
        "metadata": {
            "built": datetime.date.today().isoformat(),
            "lines": "Cook County GIS politicalBoundary layer 3 (Political Township)",
            "outline": "U.S. Census TIGERweb county subdivision %s (Chicago city)" % CHICAGO_GEOID,
            "method": ("each township clipped to the Census outline of Chicago; the %.2f km2 of that "
                       "outline no county township covers is given to the nearest township edge by "
                       "this builder" % gap_km2),
            "replaces_geoid": CHICAGO_GEOID,
        },
        "features": features,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, separators=(",", ":"))
        fh.write("\n")
    print("build_chicago_townships: wrote %s — 8 townships, %.1f%% of Chicago from the county's "
          "lines, %.2f km2 split by nearest edge" % (os.path.relpath(OUT, ROOT), 100 * covered, gap_km2))


def check():
    if not os.path.isfile(OUT):
        fail("%s is missing" % os.path.relpath(OUT, ROOT))
    doc = json.load(open(OUT, encoding="utf-8"))
    feats = doc.get("features") or []
    got = sorted((f.get("properties") or {}).get("COOK_TWP") for f in feats)
    if got != sorted(TOWNSHIPS):
        fail("the file holds %s, not Chicago's eight townships" % got)
    if (doc.get("metadata") or {}).get("replaces_geoid") != CHICAGO_GEOID:
        fail("the file does not say which Census subdivision it replaces")
    from shapely.geometry import shape
    shapes = {}
    for f in feats:
        p = f["properties"]
        if p.get("NAME") != "%s township" % TOWNSHIPS[p["COOK_TWP"]]:
            fail("%s is named %r" % (p["COOK_TWP"], p.get("NAME")))
        g = shape(f["geometry"])
        if not g.is_valid or g.is_empty:
            fail("%s's geometry is not a valid polygon" % p["COOK_TWP"])
        shapes[p["COOK_TWP"]] = g
    names = sorted(shapes)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ov = shapes[a].intersection(shapes[b]).area * KM2
            if ov > 0.001:
                fail("%s and %s overlap by %.4f km2" % (a, b, ov))
    print("build_chicago_townships: OK — 8 townships, disjoint, %.1f km2 in all"
          % (sum(g.area for g in shapes.values()) * KM2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="offline check of the shipped file")
    a = ap.parse_args()
    check() if a.check else build()


if __name__ == "__main__":
    main()
