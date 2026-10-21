#!/usr/bin/env python3
"""
Measure which of Louisiana's 44 soil and water conservation districts cover
each parish, from the Department of Agriculture and Forestry's map.

    python3 la/scripts/measure_la_conservation_parishes.py PDF

An operator step: it is run when the Department's map changes, which
la/scripts/build_la_conservation_districts.py detects (MAP_FINGERPRINT) and
refuses to build past, and its answer is copied into that builder's PARISHES
table by hand, after a look at the parishes it reports, along with the
fingerprint it prints. Nothing in CI runs it. It needs pdfplumber, shapely and
pyproj (scripts/requirements.txt pins all three).

THE MAP. Page 1 of the Department's PDF is a vector drawing, not a picture:
each district is one or more closed, filled path objects in a colour of its
own, with the district's number printed inside, and the parish lines are
separate grey strokes (0.48 pt, grey 0.43). The map's credit line states its
projection, UTM NAD 83 zone 15 in metres. This reads the objects and never
the pixels (docs/EXPANSION_GUIDE.md), and it ships no geometry from the PDF:
what it produces is a list of district numbers per parish.

THE PICTURE HIDES WHAT THE OBJECTS SAY, AND THE OBJECTS ARE WHAT IS READ. The
map draws the state's coast as a black stroke 6 pt wide over the fills, which
is wider than Grand Isle is on the page (about 2.3 pt), so the printed map
shows the island as black. Its fill underneath is the Lafourche-Terrebonne
district's (below). A reading of the picture would have put all of Jefferson
Parish in one district.

THE METHOD.
  1. Every filled path is read as the region its own fill rule paints (each
     is one even-odd subpath, measured 2026-10-21: 47 paths, all straight
     segments), and assigned the number printed inside it, or, for a path
     with no number inside (an island, a detached part), the one number
     printed in a path of the same colour. No two fills overlap (measured
     2026-10-21: no fill hides any part of another), so the order they are
     drawn in does not matter.
  2. The shipped census parishes (la/data/app/state-counties.json) are
     projected to UTM zone 15 and fitted to the map's grey parish strokes by
     iterative closest point, starting from the parish names printed once on
     the map. Measured 2026-10-21: 1 pt = 441 m, median residual 0.12 pt on
     the matched samples.
  3. Each fitted parish is shrunk by 3, 4.5 and 6 pt (1.3, 2.0 and 2.6 km), so
     a district line that only follows the parish's own edge falls outside
     what is left, and the share of the filled area left in each district is
     measured.
  4. A parish is SPLIT between two districts when the same two lead at all
     three sizes and the second has at least SPLIT_SHARE of the filled area
     at every size. Otherwise it belongs wholly to the first. A third district
     at SPLIT_SHARE or more at any size stops the run, for a reading by hand.
     The length of line the two districts share inside the parish is printed
     beside each answer, and decides nothing: Jefferson's second district is
     an island, which shares no line with the first.

WHAT IT FOUND, 2026-10-21 (the copy edited 19 October 2026): seven parishes
split (Ascension, Caldwell, Iberville, Jefferson, Ouachita, Richland, St.
James), every other parish in one district, every district in at least one
parish. In Jefferson the second district, Lafourche-Terrebonne, is Grand Isle
and the land near it: 1.6 to 1.7% of the shrunk outline at all three sizes.
Checked the same day against the Census Bureau's incorporated places, with
controls first: Thibodaux and Houma lie wholly in that district's fill and
Kenner 98.6% in Crescent's, and 65.3% of Grand Isle town's area lies in
Lafourche-Terrebonne's fill, none in Crescent's, and the rest in water no
fill covers. Three more parishes show a second district's colour inside the
shrunk outline, under 1% of it, that shrinks or vanishes as the margin grows
(Madison, Tangipahoa, West Feliciana), which a district inside the parish
would not do: where the census and the map draw a parish edge differently
(Tangipahoa's against Livingston near Lake Maurepas), the map's fill of the
next parish reaches past the census line.
"""

import argparse
import collections
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
COUNTIES = os.path.join(INSTANCE, "data", "app", "state-counties.json")
sys.path.insert(0, HERE)
from build_la_conservation_districts import map_fingerprint  # noqa: E402  (one reader of the map)

CRS = "EPSG:26915"          # NAD83 / UTM zone 15N, the map's stated projection
PARISH_STROKE = (0.43137, 0.43137, 0.43137)
ERODE_PT = (3.0, 4.5, 6.0)
SPLIT_SHARE = 0.01
TOUCH_PT = 0.2


def _winding(pts, x, y):
    """The winding number and crossing count of the closed path pts about
    (x, y), for a ray running in +x."""
    w = cross = 0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 <= y) != (y2 <= y):
            t = (y - y1) / (y2 - y1)
            if x1 + t * (x2 - x1) > x:
                cross += 1
                w += 1 if y2 > y1 else -1
    return w, cross


def fill_region(pts, evenodd):
    """The region a closed path of straight segments paints under its own
    fill rule: every face of its noded outline whose inside point the rule
    paints."""
    from shapely.geometry import LineString
    from shapely.ops import polygonize, unary_union

    faces = polygonize(unary_union(LineString(list(pts) + [pts[0]])))
    keep = []
    for f in faces:
        c = f.representative_point()
        w, cross = _winding(pts, c.x, c.y)
        if (cross % 2 == 1) if evenodd else (w != 0):
            keep.append(f)
    return unary_union(keep)


def district_shapes(page):
    from shapely.geometry import Point
    from shapely.ops import unary_union

    nums = [w for w in page.extract_words(use_text_flow=False)
            if re.fullmatch(r"\d{1,2}", w["text"]) and 1 <= int(w["text"]) <= 44]
    paths = []
    for c in page.curves:
        if not c.get("fill"):
            continue
        not_straight = [p for p in (c.get("path") or []) if p[0] not in ("m", "l", "h")]
        if not_straight or sum(1 for p in (c.get("path") or []) if p[0] == "m") != 1:
            raise SystemExit("a filled path is not one subpath of straight segments; "
                             "fill_region reads only that shape")
        region = fill_region([tuple(p) for p in c["pts"]], bool(c.get("evenodd")))
        inside = {int(w["text"]) for w in nums
                  if region.contains(Point((w["x0"] + w["x1"]) / 2, (w["top"] + w["bottom"]) / 2))}
        paths.append([region, inside, tuple(c.get("non_stroking_color") or ())])
    if len(paths) < 44:
        raise SystemExit("only %d filled paths on the map page" % len(paths))
    for region, inside, colour in paths:
        if len(inside) > 1:
            raise SystemExit("a filled path holds two district numbers: %s" % sorted(inside))
    # Each district is filled in a colour of its own (measured 2026-10-21: 44
    # colours for 44 numbers), so a path with no number inside it (an island,
    # a detached part) is the district whose number is printed in a path of
    # its colour.
    by_colour = collections.defaultdict(set)
    for region, inside, colour in paths:
        by_colour[colour] |= inside
    for colour, found in by_colour.items():
        if len(found) != 1:
            raise SystemExit("the colour %s carries district numbers %s" % (colour, sorted(found)))
    for p in paths:
        if not p[1]:
            p[1] = set(by_colour[p[2]])
    parts = collections.defaultdict(list)
    for region, inside, colour in paths:
        parts[next(iter(inside))].append(region)
    shapes = {n: unary_union(v) for n, v in parts.items()}
    if sorted(shapes) != list(range(1, 45)):
        raise SystemExit("district numbers on the map: %s" % sorted(shapes))
    for a in shapes:
        for b in shapes:
            if a < b and shapes[a].intersection(shapes[b]).area > 0.5:
                raise SystemExit("districts %d and %d overlap on the map" % (a, b))
    return shapes


def stroke_samples(page):
    import numpy as np
    pts = []
    for cv in page.curves:
        if cv.get("fill") or not cv.get("stroke"):
            continue
        col = tuple(round(v, 5) for v in (cv.get("stroking_color") or ()))
        if col != PARISH_STROKE:
            continue
        seq = cv["pts"]
        for (x1, y1), (x2, y2) in zip(seq, seq[1:]):
            k = max(1, int(math.hypot(x2 - x1, y2 - y1) / 0.5))
            for i in range(k):
                pts.append((x1 + (x2 - x1) * i / k, y1 + (y2 - y1) * i / k))
    if len(pts) < 10000:
        raise SystemExit("only %d parish-line samples on the map page" % len(pts))
    return np.array(pts)


def fit(page, parishes, strokes):
    """The affine (3x2) taking projected metres to map points."""
    import numpy as np
    cell = 4.0
    grid = collections.defaultdict(list)
    for i, (x, y) in enumerate(strokes):
        grid[(int(x // cell), int(y // cell))].append(i)

    def nearest(q, maxd):
        gx, gy, r = int(q[0] // cell), int(q[1] // cell), int(maxd // cell) + 1
        best, bd = None, maxd
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                for i in grid.get((gx + dx, gy + dy), ()):
                    d = math.hypot(strokes[i, 0] - q[0], strokes[i, 1] - q[1])
                    if d < bd:
                        bd, best = d, i
        return best, bd

    src = []
    for name, geom in parishes.values():
        b = geom.boundary
        for i in range(int(b.length / 800)):
            q = b.interpolate(i * 800)
            src.append((q.x, q.y))
    src = np.array(src)
    labels = collections.defaultdict(list)
    for w in page.extract_words(use_text_flow=False):
        labels[w["text"]].append(((w["x0"] + w["x1"]) / 2, (w["top"] + w["bottom"]) / 2))
    a0, b0 = [], []
    for name, geom in parishes.values():
        short = re.sub(r"\s+Parish$", "", name)
        if " " in short or len(labels.get(short, [])) != 1:
            continue
        c = geom.centroid
        a0.append((c.x, c.y, 1))
        b0.append(labels[short][0])
    if len(a0) < 20:
        raise SystemExit("only %d parish names to start the fit from" % len(a0))
    m = np.linalg.lstsq(np.array(a0), np.array(b0), rcond=None)[0]
    for maxd in (30, 20, 15, 10, 8, 6, 5, 4, 3, 3, 2.5, 2.5, 2, 2, 2):
        q = np.c_[src, np.ones(len(src))] @ m
        pairs_s, pairs_d, ds = [], [], []
        for s, t in zip(src, q):
            i, d = nearest(t, maxd)
            if i is not None:
                pairs_s.append(s)
                pairs_d.append(strokes[i])
                ds.append(d)
        m = np.linalg.lstsq(np.c_[np.array(pairs_s), np.ones(len(pairs_s))],
                            np.array(pairs_d), rcond=None)[0]
    median = float(np.median(ds))
    scale = math.sqrt(abs(np.linalg.det(m[:2, :2])))
    print("fit: %d of %d samples matched, median %.3f pt, 1 pt = %.0f m"
          % (len(ds), len(src), median, 1 / scale))
    if median > 0.3:
        raise SystemExit("the parishes do not fit the map's parish lines (median %.3f pt)" % median)
    return m


def measure(pdf_path, counties=COUNTIES):
    import pdfplumber
    import pyproj
    from shapely.geometry import shape
    from shapely.ops import transform, unary_union

    page = pdfplumber.open(pdf_path).pages[0]
    print("map fingerprint: %s (%d items)" % map_fingerprint(page))
    shapes = district_shapes(page)
    strokes = stroke_samples(page)
    project = pyproj.Transformer.from_crs("EPSG:4269", CRS, always_xy=True).transform
    parishes = {}
    for f in json.load(open(counties))["features"]:
        p = f["properties"]
        parishes[str(p["GEOID"])] = (str(p["NAME"]), transform(project, shape(f["geometry"])))
    m = fit(page, parishes, strokes)

    def to_map(x, y, z=None):
        return (m[0, 0] * x + m[1, 0] * y + m[2, 0], m[0, 1] * x + m[1, 1] * y + m[2, 1])

    def polygons(g):
        if g.geom_type == "Polygon":
            return [g]
        return [p for q in getattr(g, "geoms", ()) for p in polygons(q)]

    edges = {n: unary_union([p.boundary for p in polygons(s)]) for n, s in shapes.items()}
    table, notes = {}, []
    for geoid, (name, geom) in sorted(parishes.items()):
        outline = transform(to_map, geom)
        seen = []
        for erode in ERODE_PT:
            core = outline.buffer(-erode)
            area = {n: core.intersection(s).area for n, s in shapes.items()}
            area = {n: a for n, a in area.items() if a > 0}
            total = sum(area.values())
            ranked = sorted(area, key=lambda n: -area[n])
            first = ranked[0]
            second = ranked[1] if len(ranked) > 1 else None
            share = area[second] / total if second else 0.0
            if len(ranked) > 2 and area[ranked[2]] / total >= SPLIT_SHARE:
                raise SystemExit("%s: a third district (%d) covers %.1f%% of the outline "
                                 "shrunk by %.1f pt; read it by hand"
                                 % (name, ranked[2], 100 * area[ranked[2]] / total, erode))
            line = 0.0
            if second:
                shared = edges[first].intersection(edges[second].buffer(TOUCH_PT))
                line = core.intersection(shared).length
            seen.append((first, second, share, line))
        pairs = {frozenset((f, s)) for f, s, share, line in seen}
        split = len(pairs) == 1 and all(s and share >= SPLIT_SHARE for f, s, share, line in seen)
        first, second = seen[0][0], seen[0][1]
        if split:
            # ordered by the share at the smallest margin; a parish divided
            # nearly in half (St. James) can change order at another margin
            table[geoid] = [first, second]
        else:
            if len({f for f, s, share, line in seen}) != 1:
                raise SystemExit("%s: the largest district changes with the margin" % name)
            table[geoid] = [first]
            if second and seen[0][2] >= 0.001:
                notes.append("%s: %d's colour covers %s of the shrunk outline at the three "
                             "margins; not split"
                             % (name, second, ", ".join("%.1f%%" % (100 * sh) if s == second
                                                        else "none" for f, s, sh, ln in seen)))
        print("%s %-28s %s  %s" % (geoid, name, table[geoid], "  ".join(
            "%.1fpt: %s/%s %.3f line %.1f" % (e, f, s, sh, ln)
            for e, (f, s, sh, ln) in zip(ERODE_PT, seen))))
    used = {n for v in table.values() for n in v}
    missing = sorted(set(shapes) - used)
    if missing:
        raise SystemExit("districts in no parish: %s" % missing)
    print()
    for n in notes:
        print("note:", n)
    return table


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pdf", help="a saved copy of the Department's map and contacts PDF")
    ap.add_argument("--counties", default=COUNTIES, help="the parish outlines (default: the shipped file)")
    args = ap.parse_args()
    table = measure(args.pdf, args.counties)
    print()
    print("PARISHES = {")
    for geoid, nums in sorted(table.items()):
        print('    "%s": %s,' % (geoid, json.dumps([str(n) for n in nums])))
    print("}")


if __name__ == "__main__":
    main()
