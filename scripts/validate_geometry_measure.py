#!/usr/bin/env python3
"""Hold the engine's geometry-measure block to shapely, on the fleet's own districts.

WHAT IT GUARDS. engine/index.html/geometry-measure.txt is the app's only way to
say how much of one district lies in another — the percentages a comparison of
districts will print. The app has no geometry library, so the block is hand
written (scanlines over the even-odd rule, rows weighted by their area on a
sphere), and a number a reader is shown has to be held to something that is
not the block itself. This gate runs THE BLOCK AS SHIPPED — read from the
engine file, evaluated in Node, never re-implemented here — and compares
three answers with independent ones:

  area     against the spherical area of the same rings, taken from shapely's
           even-odd assembly of them (outer rings minus holes, each ring's
           area by the spherical-excess sum, the formula turf.js uses);
  overlap  the share of one district another covers, against shapely's
           intersection, both areas taken on the sphere the same way;
  weight   the points inside a district, against shapely's `contains`, on
           seeded random points — this one must agree EXACTLY, because it is
           a count, not a measurement.

THE CASES ARE REAL DISTRICTS, CHOSEN FOR THEIR SHAPES: legislative maps that
nest and cross (Illinois House in Congress), fire districts with holes and
detached parts (Cook, Macon), Wisconsin's multipart senate districts, New
York's and San Francisco's city maps. A case file that stops shipping FAILS
rather than being skipped, so the case set cannot quietly shrink.

TOLERANCES ARE STATED WITH THEIR MEASUREMENT. The block samples MEASURE_ROWS
lines, so its area is an estimate; the bounds below were set from the worst
error measured on these cases when the block was written (2026-09-23), with
margin, and the OK line prints the current worst so a drift is visible long
before it fails.

Usage:
  python3 scripts/validate_geometry_measure.py            # the CI gate
  python3 scripts/validate_geometry_measure.py --report   # every case's error
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys

from shapely.geometry import Point, Polygon
from shapely.prepared import prep

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCK = os.path.join(ROOT, "engine", "index.html", "geometry-measure.txt")
EARTH_KM = 6371.0088  # the block's radius; the reference must use the same sphere

# (file, file) — each feature of the first measured against each feature of
# the second it touches. Every feature of every file named here is also
# measured for area.
PAIRS = [
    ("il/data/app/il-house-districts.json", "il/data/app/congress-districts.json"),
    ("il/data/app/il-senate-districts.json", "il/data/app/congress-districts.json"),
    ("il/data/app/school-board-districts.json", "il/data/app/ccbr-districts.json"),
    ("il/data/app/cook-fire-districts.json", "il/data/app/congress-districts.json"),
    ("il/data/app/macon-fire-districts.json", "il/data/app/macon-park-districts.json"),
    ("wi/data/app/wi-assembly-districts.json", "wi/data/app/wi-senate-districts.json"),
    ("ny/data/app/state-assembly-districts.json", "ny/data/app/state-senate-districts.json"),
    ("ca/data/app/police-districts.json", "ca/data/app/supervisor-districts.json"),
]
WEIGHT_FILES = [
    "il/data/app/cook-fire-districts.json",
    "il/data/app/macon-fire-districts.json",
    "il/data/app/school-board-districts.json",
    "wi/data/app/wi-senate-districts.json",
]
WEIGHT_POINTS = 1500
SEED = 20260923

# Measured 2026-09-23 on these cases at MEASURE_ROWS = 512: worst area error
# 0.21% (a 0.3 km² Cook fire district; p99 0.10%), worst overlap error 0.09
# percentage points (p99 0.06). The bounds carry margin; a real regression (a
# wrong sphere factor, a lost hole, a half-row offset) moves these by whole
# percents. Measured the same day with the block deliberately broken: dropping
# the row's latitude factor fails 650 cases, and reading only each polygon's
# outer ring (every hole lost) fails 38 — 14 areas, 7 shares and 17 point
# weights.
MAX_AREA_REL = 0.005       # 0.5% of the district's area
MAX_SHARE_ABS = 0.005      # half a percentage point of share
MIN_AREA_KM2 = 0.05        # below this a district is a sliver; its relative error is noise

NODE_DRIVER = r"""
const fs = require("fs");
const block = fs.readFileSync(process.argv[1], "utf8");
const m = new Function(block + "\nreturn { measureArea, measureOverlap, measurePointWeight };")();
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const out = {
  area: cases.area.map((g) => m.measureArea(g)),
  overlap: cases.overlap.map(([a, b]) => m.measureOverlap(cases.geoms[a], cases.geoms[b])),
  weight: cases.weight.map(([g, pts]) => m.measurePointWeight(cases.geoms[g], pts)),
};
process.stdout.write(JSON.stringify(out));
"""


def rings_of(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    if geom["type"] == "MultiPolygon":
        return [r for p in geom["coordinates"] for r in p]
    return []


def even_odd(geom):
    """The rings assembled the way the block reads them: every ring toggles
    inside/outside, whatever its winding or nesting."""
    shape = None
    for ring in rings_of(geom):
        if len(ring) < 4:
            continue
        p = Polygon(ring).buffer(0)
        shape = p if shape is None else shape.symmetric_difference(p)
    return shape


def ring_area_km2(coords):
    """Spherical area of one ring (the spherical-excess sum turf.js uses)."""
    n = len(coords)
    if n < 3:
        return 0.0
    total = 0.0
    for i in range(n):
        lo = coords[i]
        mid = coords[(i + 1) % n]
        hi = coords[(i + 2) % n]
        total += (math.radians(hi[0]) - math.radians(lo[0])) * math.sin(math.radians(mid[1]))
    return abs(total * EARTH_KM * EARTH_KM / 2)


def sphere_area_km2(shape):
    polys = getattr(shape, "geoms", [shape])
    area = 0.0
    for p in polys:
        if p.is_empty or p.geom_type != "Polygon":
            continue
        area += ring_area_km2(list(p.exterior.coords)[:-1])
        for hole in p.interiors:
            area -= ring_area_km2(list(hole.coords)[:-1])
    return area


def load(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        raise SystemExit("validate-geometry-measure: FAIL — case file %s no longer ships; "
                         "replace the case, never drop it silently" % rel)
    with open(path, encoding="utf-8") as fh:
        feats = json.load(fh)["features"]
    return [f for f in feats if (f.get("geometry") or {}).get("type") in ("Polygon", "MultiPolygon")]


def name_of(rel, i, f):
    p = f.get("properties") or {}
    for k in ("BASENAME", "NAME", "name", "district", "DISTRICT", "DISTRICTN"):
        if p.get(k) not in (None, ""):
            return "%s#%s" % (os.path.basename(rel), p[k])
    return "%s[%d]" % (os.path.basename(rel), i)


def build_cases():
    geoms, names, shapes, index = [], [], [], {}

    def add(rel):
        if rel in index:
            return index[rel]
        ids = []
        for i, f in enumerate(load(rel)):
            geoms.append(f["geometry"])
            names.append(name_of(rel, i, f))
            shapes.append(even_odd(f["geometry"]))
            ids.append(len(geoms) - 1)
        index[rel] = ids
        return ids

    overlap = []
    for a_rel, b_rel in PAIRS:
        a_ids, b_ids = add(a_rel), add(b_rel)
        for a in a_ids:
            if shapes[a] is None:
                continue
            for b in b_ids:
                if shapes[b] is not None and shapes[a].bounds and shapes[a].intersects(shapes[b]):
                    overlap.append((a, b))
    rng = random.Random(SEED)
    weight = []
    for rel in WEIGHT_FILES:
        for g in add(rel):
            if shapes[g] is None:
                continue
            x0, y0, x1, y1 = shapes[g].bounds
            pts = [[round(rng.uniform(x0, x1), 7), round(rng.uniform(y0, y1), 7), rng.randint(1, 9)]
                   for _ in range(WEIGHT_POINTS)]
            weight.append((g, pts))
    area = list(range(len(geoms)))
    return geoms, names, shapes, area, overlap, weight


def run_block(geoms, area, overlap, weight):
    payload = json.dumps({"geoms": geoms, "area": [geoms[i] for i in area],
                          "overlap": overlap, "weight": weight})
    res = subprocess.run(["node", "-e", NODE_DRIVER, BLOCK], input=payload, capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit("validate-geometry-measure: FAIL — the block did not run in Node:\n" + res.stderr[-2000:])
    return json.loads(res.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true", help="print every case's error")
    args = ap.parse_args()
    geoms, names, shapes, area, overlap, weight = build_cases()
    got = run_block(geoms, area, overlap, weight)
    fails, worst = [], {"area": (0.0, ""), "share": (0.0, ""), "weight": 0}

    for k, g in enumerate(area):
        if shapes[g] is None:
            continue
        want = sphere_area_km2(shapes[g])
        have = got["area"][k]
        if want < MIN_AREA_KM2:
            continue
        rel = abs(have - want) / want
        if rel > worst["area"][0]:
            worst["area"] = (rel, names[g])
        if args.report:
            print("area   %-44s %12.4f km²  shapely %12.4f  %+.3f%%" % (names[g], have, want, 100 * (have - want) / want))
        if rel > MAX_AREA_REL:
            fails.append("%s: area %.4f km², the rings' spherical area is %.4f (%.2f%%)"
                         % (names[g], have, want, 100 * rel))

    for k, (a, b) in enumerate(overlap):
        sa, sb = shapes[a], shapes[b]
        # both areas on the sphere: a planar share in degrees drifts by
        # ~0.3 points across a district two degrees of latitude tall
        whole = sphere_area_km2(sa)
        want = sphere_area_km2(sa.intersection(sb)) / whole if whole else 0.0
        have = got["overlap"][k]["share"]
        err = abs(have - want)
        if err > worst["share"][0]:
            worst["share"] = (err, "%s in %s" % (names[a], names[b]))
        if args.report and (want > 0.001 or have > 0.001):
            print("share  %-44s in %-30s %6.2f%%  shapely %6.2f%%" % (names[a], names[b], 100 * have, 100 * want))
        if err > MAX_SHARE_ABS:
            fails.append("%s in %s: share %.2f%%, shapely says %.2f%%" % (names[a], names[b], 100 * have, 100 * want))

    for k, (g, pts) in enumerate(weight):
        shape = prep(shapes[g])
        want = sum(w for x, y, w in pts if shape.contains(Point(x, y)))
        have = got["weight"][k]
        if have != want:
            worst["weight"] += 1
            fails.append("%s: points inside weigh %s, shapely says %s" % (names[g], have, want))

    if fails:
        print("validate-geometry-measure: FAIL")
        for f in fails[:40]:
            print("  - " + f)
        if len(fails) > 40:
            print("  … and %d more" % (len(fails) - 40))
        return 1
    print("validate-geometry-measure: OK — %d area(s) within %.1f%% (worst %.3f%%, %s), %d overlap share(s) "
          "within %.1f point(s) (worst %.3f, %s), %d point-weight case(s) exact against shapely"
          % (len(area), 100 * MAX_AREA_REL, 100 * worst["area"][0], worst["area"][1], len(overlap),
             100 * MAX_SHARE_ABS, 100 * worst["share"][0], worst["share"][1], len(weight)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
