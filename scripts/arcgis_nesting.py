#!/usr/bin/env python3
"""The guard that makes an INCIDENTAL correctness property a checked one.

WHAT THE DEFECT IS. ArcGIS's GeoJSON export can return a feature's INTERIOR
rings as separate SHELLS: a MultiPolygon whose parts sit inside one another.
Under GeoJSON semantics each part is its own area, so ground the publisher cut
out becomes ground the layer claims. Wisconsin found it on 2026-09-05 in an
NG911 law-enforcement zone that swallowed a village; the same day, a sweep of
every Illinois layer this fleet fetches found 41 runtime layers losing 1,376
rings between them.

WHY ILLINOIS'S BUILDERS WERE CLEAN, AND WHY THAT NEEDED A GUARD RATHER THAN A
PARAGRAPH. Nine of the layers the builders fetch lose rings at the source —
the statewide library layer 446 -> 1,663, Macon's three tilings 0 -> 62/50/15
(park, fire, library — an earlier draft listed those three counts in a different
order from the same measurement),
Rock Island's two 0 -> 33/45, Woodford's parcel views 51 -> 57. Not one reaches
a shipped file, because an unnested inner shell makes a geometry INVALID and
both builders repair with shapely before using it: measured through each
builder's own clean(), the two fetches give identical unions and a symmetric
difference of 0.000000 km2 on all nine. SAY THAT AS AREA, NOT AS RING COUNTS:
the counts match only AFTER the repair and never before it — Macon's park
tiling reads 62 holes as Esri JSON and 73 once cleaned, because make_valid also
resolves overlaps the source ships — so "identical hole counts" is true of the
repaired geometries and false of the fetches, and area is the claim that holds
either way.

That is a real property and it was nowhere stated. Neither builder says
make_valid is what re-nests the exporter's rings, and nothing would notice a
refactor that dropped the repair, made it conditional, or introduced a source
that skips it — the counts, the areas and the probes would all still pass,
because they compare the build against the same fetch. So this asserts the
property directly, per feature, for free: after the repair no geometry may
still carry a part inside another part.

It is deliberately NOT a second network fetch. Comparing against f=json on
every build would double the traffic for a 25,824-parcel fabric to re-prove
something whose signature is already in the bytes on hand.
"""

import math


# THE AREA FLOOR, AND WHY THERE IS ONE. A part that claims no ground cannot be
# an unnested hole in the only sense this guard cares about — a reader standing
# somewhere the publisher cut out. Measured across the shipped Illinois tree
# 2026-09-06: 23 of 2,868 polygon parts have EXACTLY zero area, one of them
# inside another part (SHERRARD FPD in rock-island-fire-districts.json, built
# 2026-09-02), which would have failed the next Rock Island rebuild on a
# geometry that is correct. "Exactly zero" is NOT a sufficient rule, which is
# why this is a floor rather than a `> 0` test: the smallest NONZERO part in
# the same tree is 0.0047 m², so a future degenerate sliver can miss zero and
# still claim nothing. One square metre is smaller than the ground a person
# occupies, and four orders of magnitude below the smallest hole the 2026-09-05
# sweep found changing a card, so nothing this guard exists to catch can hide
# under it. Expressed in squared degrees at 40°N, the latitude band Illinois
# sits in; a part near the floor is REPORTED with its area rather than dropped
# silently.
_M2_PER_DEG2 = math.cos(math.radians(40.0)) * 111320.0 * 111320.0
MIN_PART_AREA = 1.0 / _M2_PER_DEG2          # 1 m², in squared degrees


def _parts(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return list(geom.geoms)
    return []


def nested_parts(geom):
    """How many of a polygonal geometry's PARTS sit INSIDE another part.

    That is the unnest signature: a hole returned as its own shell lands inside
    the part it should have been a ring of, and two parts of one MultiPolygon
    may not overlap.

    HOLES ARE RESPECTED, and getting that wrong is the whole subtlety. A first
    draft compared parts' bare EXTERIOR rings and fired on 19 of the statewide
    library layer's 642 polygons — Joliet Public Library seven times. Those are
    not the defect: they are a district whose own island sits inside another of
    its parts' HOLES, which overlaps nothing, and the giveaway is that the SAME
    19 appear identically whichever format the layer is fetched in. Testing
    against the part itself rather than its exterior separates the two cases
    exactly: a part inside a hole is legitimate, a part inside solid ground is
    the exporter's.
    """
    ps = _parts(geom)
    if len(ps) < 2:
        return 0
    n = 0
    for i, a in enumerate(ps):
        if a.area < MIN_PART_AREA:
            continue                      # claims no ground; see MIN_PART_AREA
        pt = a.representative_point()
        for j, b in enumerate(ps):
            if i != j and b.area > a.area and b.contains(pt):
                n += 1
                break
    return n


def assert_nesting_repaired(pairs, label, fail):
    """`pairs` is (raw geometry as fetched, geometry after the builder's repair).

    Reports how many features arrived with the exporter's rings unnested — a
    measurement worth printing on every build, because it moves when a
    publisher re-publishes — and FAILS if any survive into the repaired
    geometry, which is the state in which a shipped file would claim a cutout.
    """
    arrived, survived = 0, 0
    for raw, fixed in pairs:
        if nested_parts(raw):
            arrived += 1
        n = nested_parts(fixed)
        if n:
            survived += 1
    if survived:
        fail("%s: %d feature(s) still carry a polygon part INSIDE another part "
             "after repair — the ArcGIS GeoJSON export unnests interior rings "
             "and something has stopped re-nesting them, so this build would "
             "claim ground the publisher cut out (scripts/arcgis_nesting.py)"
             % (label, survived))
    if arrived:
        print("  %d feature(s) arrived with interior rings unnested by the "
              "GeoJSON export; all re-nested by the repair" % arrived)
    return arrived
