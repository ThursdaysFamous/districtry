#!/usr/bin/env python3
"""How far a simplified boundary file strays from the full-precision lines it
was simplified from, in metres.

The direction matters and the obvious one gates nothing: simplification KEEPS a
subset of the source vertices, so every drawn vertex already sits on the source
line and measuring drawn -> source answers ~0 by construction. What a reader
sees is the true line straying from the chord drawn in its place, so this
measures every SOURCE vertex's distance to the nearest DRAWN segment of the same
feature, matched by `key_prop`.

The algorithm is the one scripts/build_legislative_boundaries.py runs on
Illinois's three chambers (and its copies in ia, in, ky and mn), with the
feature key taken as an argument rather than fixed to BASENAME, so the ten
state county builders that import this module measure their counties by GEOID.

Stdlib only: the builders that import it need nothing beyond curl and mapshaper.

Usage:
    python3 scripts/boundary_fidelity.py --selftest
"""

import math
import sys


def _mscale(lat):
    return (111320.0 * math.cos(math.radians(lat)), 110540.0)


def _seg_dist_m(p, a, b, sx, sy):
    px, py = p[0] * sx, p[1] * sy
    ax, ay = a[0] * sx, a[1] * sy
    bx, by = b[0] * sx, b[1] * sy
    dx, dy = bx - ax, by - ay
    d2 = dx * dx + dy * dy
    if d2 == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / d2
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _rings(geom):
    if geom["type"] == "Polygon":
        return list(geom["coordinates"])
    if geom["type"] == "MultiPolygon":
        return [r for poly in geom["coordinates"] for r in poly]
    return []


def _index_segments(rings, cell=0.01):
    grid = {}
    for r in rings:
        for i in range(len(r) - 1):
            a, b = (r[i][0], r[i][1]), (r[i + 1][0], r[i + 1][1])
            x0, x1 = sorted((a[0], b[0]))
            y0, y1 = sorted((a[1], b[1]))
            for gx in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
                for gy in range(int(math.floor(y0 / cell)), int(math.floor(y1 / cell)) + 1):
                    grid.setdefault((gx, gy), []).append((a, b))
    return grid, cell


def _dist_to_drawn(p, grid, cell, sx, sy):
    gx, gy = int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell))
    best = float("inf")
    rad = 0
    while rad <= 4:
        for i in range(gx - rad, gx + rad + 1):
            for j in range(gy - rad, gy + rad + 1):
                if rad and abs(i - gx) != rad and abs(j - gy) != rad:
                    continue
                for a, b in grid.get((i, j), ()):
                    d = _seg_dist_m(p, a, b, sx, sy)
                    if d < best:
                        best = d
        # one band past the first hit, so a nearer segment just outside the
        # band that produced it cannot be missed
        if best < float("inf") and rad >= 1:
            break
        rad += 1
    return best


def worst_strays(source_features, drawn_features, key_prop):
    """{key: (worst stray in metres, (lng, lat) of the source vertex)} for every
    feature present in both files. A key missing from either side is the
    caller's feature-count check, not this one."""
    drawn = {f["properties"].get(key_prop): f for f in drawn_features}
    out = {}
    for sf in source_features:
        key = sf["properties"].get(key_prop)
        df = drawn.get(key)
        if df is None:
            continue
        dr = _rings(df["geometry"])
        sr = _rings(sf["geometry"])
        if not dr or not sr:
            continue
        sx, sy = _mscale(sr[0][0][1])
        grid, cell = _index_segments(dr)
        worst, where = 0.0, None
        for r in sr:
            for pt in r:
                d = _dist_to_drawn((pt[0], pt[1]), grid, cell, sx, sy)
                if d > worst:
                    worst, where = d, (pt[0], pt[1])
        out[key] = (worst, where)
    return out


def check_fidelity(source_features, drawn_features, key_prop, limit_m, name_prop=None):
    """(ok, message): ok only if no feature strays further than `limit_m`."""
    strays = worst_strays(source_features, drawn_features, key_prop)
    if not strays:
        return False, "no feature matched on %s between the source and the drawn file" % key_prop
    names = {}
    if name_prop:
        names = {f["properties"].get(key_prop): f["properties"].get(name_prop)
                 for f in source_features}

    def label(key):
        n = names.get(key)
        return "%s (%s)" % (n, key) if n else str(key)

    over = sorted((w, k) for k, (w, _) in strays.items() if w > limit_m)
    wkey = max(strays, key=lambda k: strays[k][0])
    worst, where = strays[wkey]
    if over:
        return False, ("%d of %d feature(s) stray further than %.1f m from the true line; "
                       "worst is %s at %.1f m (%.5f,%.5f)"
                       % (len(over), len(strays), limit_m, label(wkey), worst, where[1], where[0]))
    return True, "worst stray %.1f m, %s; ceiling %.1f m" % (worst, label(wkey), limit_m)


def selftest():
    # A 0.01-degree square at 40 N whose east edge bulges out by a known amount
    # at its midpoint; the "drawn" file has the bulge simplified away.
    lat0, lng0, step = 40.0, -90.0, 0.01
    sx, sy = _mscale(lat0)
    bulge_m = 30.0
    bulge = bulge_m / sx
    mid = lat0 + step / 2
    src_ring = [[lng0, lat0], [lng0 + step, lat0], [lng0 + step + bulge, mid],
                [lng0 + step, lat0 + step], [lng0, lat0 + step], [lng0, lat0]]
    drawn_ring = [[lng0, lat0], [lng0 + step, lat0], [lng0 + step, lat0 + step],
                  [lng0, lat0 + step], [lng0, lat0]]

    def fc(ring, key):
        return [{"type": "Feature", "properties": {"GEOID": key, "NAME": "Test"},
                 "geometry": {"type": "Polygon", "coordinates": [ring]}}]

    failures = []
    strays = worst_strays(fc(src_ring, "01"), fc(drawn_ring, "01"), "GEOID")
    w = strays["01"][0]
    if abs(w - bulge_m) > 0.5:
        failures.append("bulge measured %.2f m, expected %.1f m" % (w, bulge_m))
    ok, msg = check_fidelity(fc(src_ring, "01"), fc(drawn_ring, "01"), "GEOID", 25.0, "NAME")
    if ok or "Test (01)" not in msg:
        failures.append("a 30 m stray passed a 25 m ceiling: %s" % msg)
    ok, msg = check_fidelity(fc(src_ring, "01"), fc(drawn_ring, "01"), "GEOID", 35.0)
    if not ok:
        failures.append("a 30 m stray failed a 35 m ceiling: %s" % msg)
    # Identical files stray by nothing, and the direction is source -> drawn:
    # the drawn file's own vertices all lie on the source line.
    ok, msg = check_fidelity(fc(src_ring, "01"), fc(src_ring, "01"), "GEOID", 0.01)
    if not ok:
        failures.append("an identical file did not pass a 1 cm ceiling: %s" % msg)
    w_rev = worst_strays(fc(drawn_ring, "01"), fc(src_ring, "01"), "GEOID")["01"][0]
    if w_rev > 0.01:
        failures.append("drawn -> source answered %.2f m; it should be ~0 by construction" % w_rev)
    # A key in neither file cannot read as a pass.
    ok, msg = check_fidelity(fc(src_ring, "01"), fc(drawn_ring, "02"), "GEOID", 25.0)
    if ok:
        failures.append("files sharing no key passed: %s" % msg)
    if failures:
        for f in failures:
            print("boundary_fidelity selftest FAIL: " + f)
        return 1
    print("boundary_fidelity selftest OK: a 30 m bulge measures %.2f m, both ceilings "
          "decide it, the direction holds, and no shared key cannot pass" % w)
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(selftest())
    print(__doc__)
    sys.exit(2)
