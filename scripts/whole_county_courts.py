#!/usr/bin/env python3
"""
Whole-county court districts: the half every state's court builder shares.

A court district made of WHOLE counties needs no map and no publisher's
geometry: the instance already ships its county fabric
(`<tag>/data/app/state-counties.json`), so a district is a county list and a
dissolve. Kentucky's builder (ky/scripts/build_ky_court_districts.py) was the
first to do it; this module is that builder's machinery made shareable, so a
state builder only says where its county lists come from and how to read them.

Each state builder hands this module a list of Tilings: one output file, the
units in it, and for each unit its county list and any properties of its own.
This module then

  * checks the lists PARTITION the state: every county in exactly one unit,
    no name the fabric does not carry. That is the whole correctness question
    for a whole-county tiling. A county named twice would give one piece of
    ground to two courts; a county left out would tell a reader there that no
    court answers. A failure names the county.
  * dissolves each unit from the fabric (build, needs shapely), checking that
    a dissolve of disjoint counties neither gains nor loses ground;
  * re-verifies a shipped file offline (`--check`, stdlib only): the units,
    their county lists and their properties must match what the source says
    today, and each shipped shape must cover exactly the ground its own
    counties cover, measured on the sphere.

DO NOT SIMPLIFY AFTER DISSOLVING. The app cancels an interior border only where
two features share coordinates exactly, and the county fabric is already
simplified, so a dissolve of it introduces no vertex and no seam. Simplifying
the result again would move shared edges apart and draw hairlines between
neighbouring courts.

A unit's `counties` property is the county list sorted, and `unit` is the
key a card prints. Everything else a state builder puts in `props` ships as
given and is compared exactly by `--check`.
"""

import collections
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EARTH_KM = 6371.0088


class Tiling(object):
    """One output file of whole-county units.

    rows: [(unit, [county BASENAME, ...], {extra property: value})]
    want: how many units the source must yield, so a parse that loses a unit
          stops the build instead of shipping a smaller state.
    """

    def __init__(self, out_file, unit_word, rows, want, authority):
        self.out_file = out_file
        self.unit_word = unit_word
        self.rows = rows
        self.want = want
        self.authority = authority


def fail(label, msg):
    print("%s: FAIL — %s" % (label, msg))
    sys.exit(1)


def app_dir(tag):
    return os.path.join(ROOT, tag, "data", "app")


def county_geometry(tag, label):
    """{BASENAME: geometry} from the instance's own county fabric."""
    path = os.path.join(app_dir(tag), "state-counties.json")
    with open(path) as fh:
        feats = json.load(fh)["features"]
    out = {}
    for f in feats:
        name = (f.get("properties") or {}).get("BASENAME")
        if not name:
            fail(label, "a county feature in %s/data/app/state-counties.json "
                 "carries no BASENAME" % tag)
        if name in out:
            fail(label, "%s appears twice in the county fabric" % name)
        out[name] = f["geometry"]
    return out


def check_partition(label, tiling, counties):
    """Every county in exactly one unit, and no name the fabric lacks."""
    rows = tiling.rows
    if len(rows) != tiling.want:
        fail(label, "%s: the source yields %d %ss, expected %d"
             % (tiling.out_file, len(rows), tiling.unit_word, tiling.want))
    units = [u for u, _cs, _p in rows]
    dup = sorted(set(u for u in units if units.count(u) > 1), key=str)
    if dup:
        fail(label, "%s: unit(s) %s appear twice" % (tiling.out_file, dup))
    seen = collections.Counter(c for _u, cs, _p in rows for c in cs)
    unknown = sorted(set(seen) - set(counties))
    if unknown:
        fail(label, "%s names %d county/counties the fabric does not carry: %s"
             % (tiling.out_file, len(unknown), ", ".join(unknown)))
    twice = sorted(c for c, k in seen.items() if k > 1)
    if twice:
        fail(label, "%s puts %s in more than one %s, so one piece of ground "
             "would be claimed by two courts"
             % (tiling.out_file, ", ".join(twice), tiling.unit_word))
    missing = sorted(set(counties) - set(seen))
    if missing:
        fail(label, "%s leaves out %d county/counties, so a reader there would "
             "be told no court answers: %s"
             % (tiling.out_file, len(missing), ", ".join(missing)))
    for unit, names, _p in rows:
        if not names:
            fail(label, "%s: %s %s names no county"
                 % (tiling.out_file, tiling.unit_word, unit))


def properties(tiling, unit, names, extra):
    props = {"unit": unit, "counties": sorted(names),
             "authority": tiling.authority}
    for key, value in (extra or {}).items():
        if key in props:
            fail("whole-county-courts", "a state builder set the reserved "
                 "property %r" % key)
        props[key] = value
    return props


def rings_of(geometry, label):
    """Every linear ring of a Polygon or MultiPolygon, outer and inner alike."""
    kind = geometry.get("type")
    if kind == "Polygon":
        return list(geometry["coordinates"])
    if kind == "MultiPolygon":
        return [r for part in geometry["coordinates"] for r in part]
    fail(label, "unexpected geometry type %r" % kind)


def ring_area_km2(ring):
    """Signed spherical area, so a hole subtracts and winding decides sign."""
    total = 0.0
    for i in range(len(ring) - 1):
        lon1, lat1 = math.radians(ring[i][0]), math.radians(ring[i][1])
        lon2, lat2 = math.radians(ring[i + 1][0]), math.radians(ring[i + 1][1])
        total += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
    return total * EARTH_KM * EARTH_KM / 2.0


def measure(geometry, label):
    """Area the way a reader's ground is measured, holes subtracted."""
    return abs(sum(ring_area_km2(r) for r in rings_of(geometry, label)))


def build(tag, label, tilings):
    try:
        from shapely.geometry import mapping, shape
        from shapely.ops import unary_union
    except ImportError:
        fail(label, "the build path needs shapely (pip install -c "
             "scripts/requirements.txt shapely). `--check` is stdlib only.")
    counties = county_geometry(tag, label)
    for tiling in tilings:
        check_partition(label, tiling, counties)
        features, worst = [], 0.0
        for unit, names, extra in tiling.rows:
            parts = [shape(counties[c]) for c in names]
            merged = unary_union(parts)
            # A dissolve of disjoint counties neither gains nor loses ground.
            want_area = sum(p.area for p in parts)
            worst = max(worst, abs(merged.area - want_area) / want_area)
            features.append({
                "type": "Feature",
                "properties": properties(tiling, unit, names, extra),
                "geometry": mapping(merged),
            })
        if worst > 1e-9:
            fail(label, "%s: a dissolve moved ground by %.2e of its own area"
                 % (tiling.out_file, worst))
        body = json.dumps({"type": "FeatureCollection", "features": features},
                          separators=(",", ":"))
        with open(os.path.join(app_dir(tag), tiling.out_file), "w") as fh:
            fh.write(body)
        print("%s: wrote %s — %d %ss, %.1f KB, area drift %.1e"
              % (label, tiling.out_file, len(features), tiling.unit_word,
                 len(body) / 1024.0, worst))


def check(tag, label, tilings):
    counties = county_geometry(tag, label)
    for tiling in tilings:
        check_partition(label, tiling, counties)
        full = os.path.join(app_dir(tag), tiling.out_file)
        if not os.path.exists(full):
            fail(label, "%s is missing. Run this builder without --check."
                 % tiling.out_file)
        with open(full) as fh:
            shipped = json.load(fh)["features"]
        by_unit = {}
        for f in shipped:
            unit = (f.get("properties") or {}).get("unit")
            if unit in by_unit:
                fail(label, "%s ships unit %r twice" % (tiling.out_file, unit))
            by_unit[unit] = f
        if len(by_unit) != len(tiling.rows):
            fail(label, "%s ships %d %ss and the source names %d"
                 % (tiling.out_file, len(by_unit), tiling.unit_word,
                    len(tiling.rows)))
        worst = 0.0
        for unit, names, extra in tiling.rows:
            f = by_unit.get(unit)
            if f is None:
                fail(label, "%s ships no %s %r"
                     % (tiling.out_file, tiling.unit_word, unit))
            want = properties(tiling, unit, names, extra)
            if f["properties"] != want:
                fail(label, "%s %s %r ships properties %r and the source says "
                     "%r" % (tiling.out_file, tiling.unit_word, unit,
                             f["properties"], want))
            # THE IDENTITY, re-derived from the fabric rather than trusted: the
            # shipped shape must cover exactly the ground its own counties do.
            drawn = measure(f["geometry"], label)
            named = sum(measure(counties[c], label) for c in names)
            worst = max(worst, abs(drawn - named) / named)
        if worst > 1e-6:
            fail(label, "%s: a shipped shape differs from its own counties' "
                 "ground by %.2e of its area, so the file and the source "
                 "disagree" % (tiling.out_file, worst))
        print("%s: %s — %d %ss, every county in exactly one, area identity "
              "within %.1e" % (label, tiling.out_file, len(tiling.rows),
                               tiling.unit_word, worst))
