"""Rings the simplifier drops, judged by the ANSWER they change rather than by
their area — one mechanism for every Wisconsin boundary builder.

WHY THE ANSWER AND NOT THE AREA. `keep-shapes` protects a SHAPE and not a RING:
a multipolygon is one feature, so once one ring survives the guarantee is met and
every hole and every detached part is eligible for removal like any other
geometry. Some of those losses cost a reader the right answer and some cost
nothing, and AREA DOES NOT TELL THEM APART. Measured on this state's own layers:
a 31.7 m2 ring on Washington Island moves 610 of 900 points inside it from
district 1 to the water pseudo-district, while far larger dropped rings move
nothing at all. (That ring was described here as being IN Lake Michigan until
2026-09-27, which was an inference from its coordinate rather than a measurement;
TIGER's areal hydrography finds no water at it. CLAUDE.md carries the rule.)
An aggregate dropped-area ceiling would therefore license the drops that cost a
reader an answer and fail on the ones that cost nothing, which is why this module
computes the answer for every dropped ring instead.

WHAT IT COMPUTES, PER DISTINCT RING. Points provably inside the ring are put to
the FULL-PRECISION source and to the DRAWN output, and THE ANSWER A READER IS
GIVEN is compared:

    unchanged      the reader is told the same district -- no declaration needed
    gap-closed     the reader was told NO district and is now told one
    wrong-name     the reader is told a different district
    false-silence  the reader was told a district and is now told none
    degenerate     no point can be found inside the ring at all

THE READER'S ANSWER IS ONE DISTRICT, NOT THE SET, AND THAT DISTINCTION CHANGES
THE COUNT BY A THIRD. The app's `findFeatureContaining` scans the shipped features
in file order and BREAKS ON THE FIRST MATCH, so where two districts both contain a
point a reader sees whichever comes first and never learns of the second. A drop
that takes the set from {A, B, C} to {A} therefore changes no reader's answer if A
came first both times, and counting it would have this builder confessing to a
wrong answer it does not give. Measured on the shipped geometry: 102 rings change
the SET and 73 change what a reader is told. `wi/WATCH.md` row 57 established this
in September and put it exactly -- quote 63 to a reader and 133 to a builder -- and
the first version of this module measured the set anyway. The set is recorded
beside each answer as `before_all` / `after_all`, because a builder wants to know
the geometry moved even where the card does not.

`wrong-name` and `false-silence` are the harms and must be declared one by one.
`unchanged` and `degenerate` need nothing. `gap-closed` is counted but not
declared per ring, and that is a judgement this module states rather than hides:
a hole that NO district covers is a gap in the publisher's own coverage, so
closing it moves a reader from "you are in no supervisory district" to the
district that surrounds them on every side. The supporting measurement is that
LTSB's own statewide geometry overlaps ITSELF on 0.017% of its area, so gaps and
overlaps are the same stitching artefact between 72 county submissions. IT IS
STILL AN INFERENCE: a hole could in principle be a deliberate void, and closing
it would then name a district for ground no district holds. So the COUNT is
declared and gated, and a rebuild that starts closing a different number of gaps
fails and has to be looked at.

THE SAMPLER IS A SCANLINE, AND A BOUNDING-BOX GRID IS THE WRONG TOOL HERE.
Nearly every dropped ring is a thin sliver along a county line, so its bounding
box is mostly outside it. Measured on the supervisory layer's own 464 distinct
dropped rings, a 0.25 m bbox grid needed 15,597,792 cells for a single ring and
STILL found no point inside 157 of them; the scanline finds points in 355 and
uses 1,457 points in total. An interior SPAN on a scanline has positive width by
construction, so its midpoint is inside -- but the sampler only ever PROPOSES,
and `point_in_ring` decides, because 1.02% of those midpoints are rejected where
a ring is degenerate or self-touching.

AND THE SAMPLE COUNT IS THE RING'S OWN, NOT A ROUND NUMBER. One scanline sits
between each pair of distinct vertex latitudes, so a three-vertex sliver gets one
point and a complex ring gets one per span per scanline -- measured, a median of
2 and a maximum of 77 -- thinned evenly to SCANLINE_MAX_POINTS above that. Two
rings at the shipped setting return DIFFERENT answers at different points inside
themselves, so one point is demonstrably not always enough and a fixed single
sample would have missed them.

SAMPLING MUST BE DETERMINISTIC, WHICH COST ONE WRONG MEASUREMENT TO LEARN. A
first version drew points until it had a target number, refining the grid until
it did; run twice with different targets on one file it answered 308 and 307
answer-changing rings, 41 and 38 unchanged. A gate whose verdict depends on how
hard it looked cannot say which rings need declaring, so nothing here is
target-driven.
"""

import math
import re

# THIS IS NO LONGER THE RETAINED-RING TEST, AND THE COMMENT THAT STOOD HERE WAS
# WRONG ABOUT THE ONE CASE IT EXCUSED (corrected 2026-09-27). It read:
#
#   "A SOURCE RING COUNTS AS DROPPED when none of its own vertices survived, and
#    this is the threshold for 'survived' ... The one way this reads wrong is safe:
#    a dropped ring lying exactly on ANOTHER ring's drawn line would measure as
#    retained, and its stray would then be held to the caller's fidelity ceiling
#    -- stricter than a declaration, never looser."
#
# Safe for the FIDELITY CEILING and not for the thing this module is for. A ring
# that reads as retained is never put to `classify`'s answer test, so a ring that
# is GONE has its answer measured by nothing -- and the shape that triggers it, a
# zero-width spur joined to the main body, turned out to be the modal small-ring
# shape on the NG911 layers rather than a corner. `find_dropped` now answers by an
# exact vertex-subset test with no threshold at all; see its docstring.
#
# WHAT THE CONSTANT STILL DOES is set `SAMPLE_STEP_M` below: it is finer than any
# simplification interval this fleet ships, which is the property that use needs.
RETAINED_RING_M = 1.0

# The largest area a ring may have and still be reported `degenerate` — i.e. no
# point can be found inside it. DERIVED FROM THE SHIPPED COORDINATE PRECISION,
# not fitted to what has been observed. These files ship at 6 decimals, and one
# 6-decimal cell measures 0.0821 m x 0.1105 m at 42.5 N through 0.0759 m x
# 0.1105 m at 47.0 N — 0.0084 to 0.0091 m2 across Wisconsin's latitudes. A ring
# smaller than one cell cannot be guaranteed to hold an interior span of positive
# width at all, so 0.01 m2 is one cell rounded up to cover the whole state.
#
# ABOVE THIS BOUND, A RING WITH NO INTERIOR POINT IS A FAILURE OF THE SAMPLER
# rather than a ring with no inside, and the caller is told to fail rather than
# to pass it silently. That guard is why the bound is derived: the first bbox-grid
# sampler reported rings of 97.6 m2 and 131.6 m2 as having no interior point, and
# an observed-maximum bound would have grown to cover them. Fitting it to the data
# is the same mistake as choosing a ceiling to fit the drops.
DEGENERATE_MAX_M2 = 0.01

# Scanlines per ring, above which they are thinned evenly. 64 is a cap on work
# rather than a measurement: the median ring offers 2 points and the largest 77.
SCANLINE_MAX_POINTS = 64

# How far apart two samples inside one ring may be, in metres. NOT A NEW NUMBER:
# it is RETAINED_RING_M, the distance at which a vertex counts as having survived,
# reused because it is already finer than any simplification interval this fleet
# ships — so no boundary the drawn output draws can pass between two samples
# unseen. A four-vertex rectangle has one scanline and would otherwise be judged
# on a single point however large it is.
SAMPLE_STEP_M = RETAINED_RING_M

# How close a dropped ring must be to a declared one to be the same ring, in
# metres, and how far its area may differ.
RING_MATCH_M = 25.0
RING_MATCH_AREA = 0.10

KIND_UNCHANGED = "unchanged"
KIND_GAP_CLOSED = "gap-closed"
KIND_WRONG_NAME = "wrong-name"
KIND_FALSE_SILENCE = "false-silence"
KIND_DEGENERATE = "degenerate"
HARM_KINDS = (KIND_WRONG_NAME, KIND_FALSE_SILENCE)


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def mscale(lat):
    """Metres per degree of longitude and of latitude at `lat`."""
    return (111320.0 * math.cos(math.radians(lat)), 110540.0)


def rings(geom):
    """Every ring of a Polygon or MultiPolygon, outer rings and holes alike."""
    if not geom:
        return []
    if geom["type"] == "Polygon":
        return [r for r in geom["coordinates"] if r]
    if geom["type"] == "MultiPolygon":
        return [r for poly in geom["coordinates"] for r in poly if r]
    return []


def ring_area_m2(ring):
    """Unsigned planar area, metres squared, at the ring's own latitude."""
    if len(ring) < 3:
        return 0.0
    sx, sy = mscale(sum(p[1] for p in ring) / float(len(ring)))
    a = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i][0] * sx, ring[i][1] * sy
        x2, y2 = ring[(i + 1) % len(ring)][0] * sx, ring[(i + 1) % len(ring)][1] * sy
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def ring_centre(ring):
    """Mean of the DISTINCT vertices — the identity a declaration is matched on.

    Distinct, because a closed ring repeats its first vertex and would otherwise
    pull the centre towards it.
    """
    pts = sorted({(round(p[0], 9), round(p[1], 9)) for p in ring})
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def ring_verts(ring):
    """Distinct vertices, so a closed ring is not counted one high."""
    return len({(round(p[0], 9), round(p[1], 9)) for p in ring})


def ring_signature(ring):
    """Identity of a ring's GEOMETRY, at the 6 decimals these files ship.

    One ring geometry can be dropped from several features at once — a sliver on
    a shared boundary sits in both districts that drew it, and on the water line
    in the land district and the water pseudo-district, in both chambers — so
    drops are grouped by this rather than counted per feature.
    """
    return tuple(sorted((round(p[0], 6), round(p[1], 6)) for p in ring))


def point_in_ring(pt, ring):
    x, y = pt
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def point_in_geometry(pt, geom):
    """Even-odd over every ring, so a point in a hole is correctly OUTSIDE."""
    if geom is None:
        return False
    if geom["type"] == "Polygon":
        inside = False
        for ring in geom["coordinates"]:
            if point_in_ring(pt, ring):
                inside = not inside
        return inside
    if geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            inside = False
            for ring in poly:
                if point_in_ring(pt, ring):
                    inside = not inside
            if inside:
                return True
    return False


def bbox(geom):
    b = [1e9, 1e9, -1e9, -1e9]

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            b[0], b[1] = min(b[0], c[0]), min(b[1], c[1])
            b[2], b[3] = max(b[2], c[0]), max(b[3], c[1])
        else:
            for x in c:
                walk(x)

    walk(geom["coordinates"])
    return b


def model(features, key_prop):
    """(key, geometry, bbox) per feature — the form `districts_at` scans."""
    return [(f["properties"].get(key_prop), f["geometry"], bbox(f["geometry"]))
            for f in features if f.get("geometry")]


def reader_answer(mod, pt):
    """The ONE district a reader is told they are in, or None.

    THIS IS THE ANSWER THE GATE JUDGES, AND IT IS NOT THE SET. The app's
    `findFeatureContaining` scans the shipped features in file order, bbox-rejects,
    ray-casts, and BREAKS ON THE FIRST MATCH — so where two districts both contain
    a point, a reader is shown whichever comes first in the file and never learns
    of the second. `wi/WATCH.md` row 57 established this in September and put it
    exactly: quote 63 to a reader and 133 to a builder.

    So a drop that changes the SET from {A, B, C} to {A} changes no reader's answer
    if A came first both times, and counting it as harm would have this builder
    confessing to a wrong answer it does not give. The set is still recorded beside
    it, because a builder wants to know the geometry moved even where the card
    does not.

    `mod` must be in the file's own feature order, which is what `model` returns
    and what mapshaper preserves through simplification.
    """
    for k, g, bb in mod:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and point_in_geometry(pt, g):
            return k
    return None


def districts_at(mod, pt):
    """Every district of `mod` containing `pt`, sorted, as a tuple."""
    return tuple(sorted(
        k for k, g, bb in mod
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
        and point_in_geometry(pt, g)))


def _seg_dist_m(p, a, b, sx, sy):
    px, py = (p[0] - a[0]) * sx, (p[1] - a[1]) * sy
    bx, by = (b[0] - a[0]) * sx, (b[1] - a[1]) * sy
    L = bx * bx + by * by
    if L <= 0:
        return math.hypot(px, py)
    t = max(0.0, min(1.0, (px * bx + py * by) / L))
    return math.hypot(px - t * bx, py - t * by)


def index_segments(rs, cell=0.01):
    """Bucket every segment of `rs` into a degree grid for nearest-segment work."""
    grid = {}
    for r in rs:
        for i in range(len(r) - 1):
            a, b = r[i], r[i + 1]
            for cx in range(int(math.floor(min(a[0], b[0]) / cell)),
                            int(math.floor(max(a[0], b[0]) / cell)) + 1):
                for cy in range(int(math.floor(min(a[1], b[1]) / cell)),
                                int(math.floor(max(a[1], b[1]) / cell)) + 1):
                    grid.setdefault((cx, cy), []).append((a, b))
    return grid, cell


def dist_to_drawn(p, grid, cell, sx, sy):
    """Distance from `p` to the nearest indexed segment, widening the search."""
    best = float("inf")
    cx, cy = int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell))
    span = 1
    while span <= 8:
        for i in range(cx - span, cx + span + 1):
            for j in range(cy - span, cy + span + 1):
                for a, b in grid.get((i, j), ()):
                    d = _seg_dist_m(p, a, b, sx, sy)
                    if d < best:
                        best = d
        if best < span * cell * min(sx, sy):
            return best
        span *= 2
    return best


def interior_points(ring, max_pts=SCANLINE_MAX_POINTS):
    """Points provably inside `ring`, from interior SPANS on scanlines.

    A bbox grid is the wrong sampler for these rings: nearly all are thin slivers
    along a county line, so the bounding box is mostly outside the ring. Measured
    on the supervisory layer's own 464 distinct dropped rings, a 0.25 m bbox grid
    needed 15,597,792 cells for a single ring and STILL found no point inside 157
    of them. An interior SPAN on a scanline has positive width by construction, so
    its midpoint is inside — but the sampler only ever PROPOSES, and
    `point_in_ring` decides, because 1.02% of those midpoints are rejected where a
    ring is degenerate or self-touching.

    TWO THINGS SET THE SAMPLE COUNT, AND THE VERTICES ALONE ARE NOT ENOUGH.
    A scanline sits between each pair of distinct vertex latitudes, which suits a
    sliver traced with many vertices. It is not enough for a LARGE ring with few:
    a four-vertex rectangle has two distinct latitudes and therefore ONE scanline
    and ONE point, whoever big it is — which is exactly the case where one point
    is not representative, and a fixture of that shape is what caught it. So the
    scanlines are also subdivided, and each span sampled along its length, until
    consecutive samples are no more than SAMPLE_STEP_M apart.

    The step is RETAINED_RING_M, this module's own measured constant, rather than
    a new round number: it is the distance at which a vertex counts as having
    survived, and it is finer than any simplification interval this fleet ships,
    so no boundary the drawn output draws can pass between two samples unseen.

    Work is bounded by `max_pts` per ring, thinned evenly so the choice stays a
    deterministic function of the ring.
    """
    r = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else list(ring)
    n = len(r)
    if n < 3:
        return []
    ys = sorted({p[1] for p in r})
    if len(ys) < 2:
        return []
    sx, sy = mscale((ys[0] + ys[-1]) / 2.0)
    step_lat = SAMPLE_STEP_M / sy
    cuts = []
    for i in range(len(ys) - 1):
        lo, hi = ys[i], ys[i + 1]
        cuts.append((lo + hi) / 2.0)
        extra = int((hi - lo) / step_lat)          # subdivide a tall gap
        for k in range(1, min(extra, max_pts)):
            cuts.append(lo + (hi - lo) * k / float(extra + 1))
    cuts = sorted(set(cuts))
    if len(cuts) > max_pts:
        st = len(cuts) / float(max_pts)
        cuts = [cuts[int(i * st)] for i in range(max_pts)]
    step_lng = SAMPLE_STEP_M / max(sx, 1e-9)
    out = []
    for y in cuts:
        xs = []
        for i in range(n):
            x1, y1 = r[i][0], r[i][1]
            x2, y2 = r[(i + 1) % n][0], r[(i + 1) % n][1]
            if (y1 > y) != (y2 > y):
                xs.append(x1 + (x2 - x1) * (y - y1) / (y2 - y1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            x0, x1 = xs[k], xs[k + 1]
            if x1 <= x0:
                continue
            steps = max(1, min(int((x1 - x0) / step_lng), max_pts))
            for j in range(steps):
                base = x0 + (x1 - x0) * (j + 0.5) / steps
                for f in (0.0, -0.25, 0.25):
                    p = (base + (x1 - x0) * f / steps, y)
                    if x0 < p[0] < x1 and point_in_ring(p, ring):
                        out.append(p)
                        break
        if len(out) > max_pts * 4:
            break
    return out


#!/usr/bin/env python3


# --------------------------------------------------------------------------
# what was dropped, and what it costs a reader
# --------------------------------------------------------------------------

def source_step_m(src_by_key, dropped_sigs=()):
    """How far the TRUE line runs before it turns, per segment, in metres.

    THE CEILING A FIDELITY GATE HOLDS TO IS DERIVED FROM THIS AND NEVER BORROWED.
    Illinois's 25 m came from the median length of the source line's own segments
    around one neighbourhood of a street grid, and a Wisconsin county's 911 filing
    seam is not that geometry. A number carried over from another layer family is a
    number nobody measured here.

    Returns the sorted list of segment lengths on RETAINED rings, which is the set
    `measure_stray` reports on, so the ceiling and the measurement describe the
    same lines.
    """
    out = []
    for key, geom in src_by_key.items():
        for r in rings(geom):
            if ring_signature(r) in dropped_sigs:
                continue
            if len(r) < 2:
                continue
            sx, sy = mscale(r[0][1])
            for i in range(len(r) - 1):
                a, b = r[i], r[i + 1]
                d = math.hypot((b[0] - a[0]) * sx, (b[1] - a[1]) * sy)
                if d > 0:
                    out.append(d)
    out.sort()
    return out


def measure_stray(src_by_key, drawn_by_key, dropped_sigs=()):
    """How far the TRUE line strays from the chord drawn in its place, per key.

    THE DIRECTION MATTERS AND THE OBVIOUS ONE GATES NOTHING: simplification KEEPS a
    subset of the source vertices, so every drawn vertex already sits on the source
    line and measuring drawn -> source answers ~0 by construction. What a reader
    sees is the true line straying from the chord drawn for it, so that is what is
    measured here — source vertex to nearest DRAWN segment.

    AND ON RETAINED RINGS ONLY. A ring none of whose own vertices survived is not a
    stray an interval controls; it is a shape that is gone, and `classify` measures
    it as an ANSWER instead. Pooling the two makes the ceiling a function of the
    smallest ring in the state — measured on the chambers layer, that read 17.5 m
    against a 15 m ceiling on a ring that was not there at all. WHICH RINGS THOSE
    ARE IS THE CALLER'S ANSWER, in `dropped_sigs` from `classify`, so the two gates
    agree about the dropped set by construction rather than by coincidence.

    Returns (per_key, stats). `per_key` maps key -> {"worst", "at"}; `stats` carries
    the pooled distribution (`all` sorted, plus `worst`, `worst_key`, `worst_at`)
    and `dropped`, the number of rings skipped.
    """
    per_key = {}
    pooled = []
    dropped = 0
    worst, wkey, wat = 0.0, None, None
    for key, sgeom in src_by_key.items():
        if key not in drawn_by_key:
            continue
        dr = rings(drawn_by_key[key])
        sr = rings(sgeom)
        if not dr or not sr:
            continue
        sx, sy = mscale(sr[0][0][1])
        grid, cell = index_segments(dr)
        kworst, kat = 0.0, None
        for r in sr:
            if ring_signature(r) in dropped_sigs:
                dropped += 1
                continue
            for pt in r:
                d = dist_to_drawn((pt[0], pt[1]), grid, cell, sx, sy)
                pooled.append(d)
                if d > kworst:
                    kworst, kat = d, (pt[0], pt[1])
        per_key[key] = {"worst": kworst, "at": kat}
        if kworst > worst:
            worst, wkey, wat = kworst, key, kat
    pooled.sort()
    return per_key, {"all": pooled, "worst": worst, "worst_key": wkey,
                     "worst_at": wat, "dropped": dropped}


# THE OUTPUT'S OWN COORDINATE CELL, in metres: 6 decimals of latitude, which is
# the narrower of the two axes at Wisconsin's latitudes (a degree of longitude is
# shorter, so its cell is smaller still -- taking the latitude cell is therefore
# the CONSERVATIVE reading, and a ring this measurement calls narrower than the
# cell is narrower on both axes). A ring narrower than this cannot be drawn by the
# file it ships in, so a vertex whose two ring neighbours sit closer together than
# one cell is on a SPUR: the ring doubles back through it, it encloses no area, and
# its distance from the drawn line is the length of that spur rather than a
# boundary anyone can stand beside. Callers shipping at a different precision pass
# their own.
OUTPUT_CELL_M = 0.111

# The disc a fidelity failure's own neighbourhood is swept over, as shells x spokes
# out to the vertex's own stray distance -- so the far shell lands where the drawn
# line runs and the near ones cover the ground between. 12 x 24 is 288 points per
# over-limit vertex, which is cheap because an over-limit vertex is rare: on
# Wisconsin's four NG911 layers, 79 of 3,953,583 source vertices stray over 2 m.
FIDELITY_SHELLS = 12
FIDELITY_SPOKES = 24


def check_fidelity(source_features, drawn_features, key_prop, dropped_sigs,
                   limit, cell_m=OUTPUT_CELL_M):
    """Does the true line stray past `limit` anywhere a reader's ANSWER changes?

    Returns (ok, message). On a failure the message names the worst surviving
    stray, where it is and which way the answer moves; on a pass it names the limit
    nothing reached. EITHER WAY IT NAMES EVERY EXCLUDED COUNT, so a run that
    excludes a great deal says so rather than reading as a clean pass.

    THE METRES ALONE ARE THE WRONG SUBJECT, and that is measured rather than
    asserted. On Wisconsin's four NG911 layers a ceiling derived from their own
    median source step lands at 2.45-3.43 m; at that value it fails seven vertices
    that cost no reader anything, and set high enough to pass them it is 126 m and
    gates nothing. So this couples the two: a vertex over the limit is a FAILURE
    unless one of FOUR MEASURED PREDICATES clears it. None of them is a pinned list
    of coordinates, and each one's count is printed every run.

      * SPUR -- the vertex's two ring neighbours sit closer together than one
        output cell, so the ring is narrower there than the file can draw and
        encloses no area. Its stray is a spur's length.
      * AGREES -- the disc around it, out to its own stray distance, is answered
        identically by the source features and the drawn features at every one of
        FIDELITY_SHELLS x FIDELITY_SPOKES points. Nothing there changes hands.
      * DECLARED RING -- every point that DOES differ lies inside a ring
        `dropped_sigs` names. `classify` already measured that ring's answer change
        and `check` already requires it declared, so failing here too would demand
        the same harm be written down in two tables.
      * GAP CLOSED -- every difference is a point the SOURCE answered with nothing
        and the drawn output answers with a district. This one was found by the
        selftest rather than reasoned out: assertion 16 asserted that closing a
        64 m notch with nobody next door changes no answer, and it changes one --
        from NO AGENCY to A. `classify` calls that `gap-closed`, holds the COUNT
        rather than declaring each ring, and does not call it harm, so this reads
        the direction the same way. A difference from one district to another, or
        from a district to nothing, is harm and fails.

    WHAT IT CANNOT SEE is stated rather than implied: the disc is a sample, so a
    disagreement smaller than the gap between its points is missed, and the
    exclusion is per VERTEX rather than per region, so a long excursion whose
    middle changes hands while both its ends agree could clear on each vertex
    separately. Both are why the ceiling is kept near one source step instead of
    being widened until nothing fails.
    """
    src = {k: f["geometry"] for k, f in _by_key(source_features, key_prop).items()}
    drawn = {k: f["geometry"] for k, f in _by_key(drawn_features, key_prop).items()}
    smod = model(source_features, key_prop)
    dmod = model(drawn_features, key_prop)
    dropped_rings_by_sig = {}
    for k, geom in src.items():
        for r in rings(geom):
            sig = ring_signature(r)
            if sig in dropped_sigs:
                dropped_rings_by_sig.setdefault(sig, r)

    worst, wkey, wat = 0.0, None, None
    fails = []
    n_spur = n_agree = n_declared = n_gap = 0
    for key, sgeom in src.items():
        if key not in drawn:
            continue
        dr = rings(drawn[key])
        sr = rings(sgeom)
        if not dr or not sr:
            continue
        grid, cell = index_segments(dr)
        # A SOURCE VERTEX THE DRAWN RINGS STILL CARRY IS AT DISTANCE 0 BY SET
        # MEMBERSHIP, so it needs no geometry query at all. Simplification keeps
        # most vertices, so this skips the great majority of the scan exactly
        # rather than approximately: measured on these four layers it is 3.95M
        # vertices asked down to the handful that were removed.
        kept = {(pt[0], pt[1]) for ring in dr for pt in ring}
        for r in sr:
            if ring_signature(r) in dropped_sigs or len(r) < 3:
                continue
            sx, sy = mscale(r[0][1])
            n = len(r) - 1 if r[0] == r[-1] else len(r)
            for i in range(n):
                v = r[i]
                if (v[0], v[1]) in kept:
                    continue
                d = dist_to_drawn((v[0], v[1]), grid, cell, sx, sy)
                if d <= limit:
                    continue
                a, b = r[(i - 1) % n], r[(i + 1) % n]
                span = math.hypot((b[0] - a[0]) * sx, (b[1] - a[1]) * sy)
                if span < cell_m:
                    n_spur += 1
                    continue
                diffs = _answer_diffs_around(smod, dmod, v, d, sx, sy)
                if not diffs:
                    n_agree += 1
                    continue
                if all(any(point_in_ring((p[0], p[1]), rr)
                           for rr in dropped_rings_by_sig.values())
                       for p in diffs):
                    n_declared += 1
                    continue
                # THE DIRECTION DECIDES, exactly as `classify`'s kinds do: a point
                # the source answered with nothing and the output answers with a
                # district is the gap-closed direction, which this project counts
                # and does not call harm. Anything else -- one district for
                # another, or a district for nothing -- is harm.
                # `reader_answer` answers None for "no district", never "".
                # The first draft tested `!= ""`, which is True of None, so every
                # gap-closing difference read as harm -- and its own message then
                # printed "NO DISTRICT" beside the harm it had just claimed, which
                # is what gave it away.
                harm = [p for p in diffs if p[2] is not None]
                if not harm:
                    n_gap += 1
                    continue
                fails.append((d, key, v, harm[0]))
                if d > worst:
                    worst, wkey, wat = d, key, v

    excl = ("%d spur(s) on a span under %.3f m, %d vertex/vertices whose own "
            "neighbourhood is answered identically, %d whose every difference lies "
            "inside a ring already declared as dropped, %d whose every difference "
            "only fills ground the source answered with nothing"
            % (n_spur, cell_m, n_agree, n_declared, n_gap))
    if fails:
        fails.sort(reverse=True)
        d, key, v, p = fails[0]
        return False, ("%d vertex/vertices stray past %.1f m where the answer "
                       "changes; worst %.1f m on %r at %.6f,%.6f, where "
                       "%.6f,%.6f is answered %r and would be answered %r; "
                       "excluded %s"
                       % (len(fails), limit, d, key, v[1], v[0], p[1], p[0],
                          p[2] if p[2] is not None else "NO DISTRICT",
                          p[3] if p[3] is not None else "NO DISTRICT", excl))
    return True, ("no retained vertex strays past %.1f m where the answer changes; "
                  "excluded %s" % (limit, excl))


def _answer_diffs_around(smod, dmod, v, reach, sx, sy):
    """Points on a disc around `v` where the source and drawn answers differ.

    The disc reaches out to `v`'s own stray distance, so its far shell lands where
    the drawn line runs. Returns the differing points, so the caller can ask
    whether each is inside a ring already declared dropped rather than taking a
    single yes or no.
    """
    out = []
    for j in range(1, FIDELITY_SHELLS + 1):
        rad = reach * j / float(FIDELITY_SHELLS)
        for k in range(FIDELITY_SPOKES):
            th = 2 * math.pi * k / FIDELITY_SPOKES
            p = (v[0] + rad * math.cos(th) / sx, v[1] + rad * math.sin(th) / sy)
            before = reader_answer(smod, p)
            after = reader_answer(dmod, p)
            if before != after:
                # (lng, lat, before, after) -- the caller reads the DIRECTION off
                # `before`, so it cannot be recovered by a second query that might
                # disagree with this one.
                out.append((p[0], p[1], before, after))
    return out


def pct(sorted_vals, q):
    """The q-th percentile (0..100) of an already-sorted list, or 0.0 if empty."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    i = (len(sorted_vals) - 1) * (q / 100.0)
    lo = int(math.floor(i))
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (i - lo)


def _by_key(features, key_prop):
    return {f["properties"].get(key_prop): f
            for f in features if f.get("geometry")}


def find_dropped(source_features, drawn_features, key_prop):
    """[(key, ring)] for every SOURCE ring the drawn output does not carry.

    Compared feature by feature: a ring belongs to one district, so the question is
    whether THAT district's drawn geometry kept it, not whether some other
    district's line happens to pass through it.

    IT IS EXACT AND USES NO DISTANCE THRESHOLD, AND THE THRESHOLD IT REPLACED WAS
    UNDERCOUNTING (corrected 2026-09-27). This asked whether ANY ONE of a source
    ring's vertices lay within `RETAINED_RING_M` of the feature's drawn geometry,
    and called the ring retained if one did. A ZERO-WIDTH SPUR JOINED TO THE MAIN
    BODY SATISFIES THAT BY CONSTRUCTION — its join vertex sits on the main body's
    own drawn line — so a spur that is entirely gone read as retained, and its
    ANSWER went unmeasured. Measured on Wisconsin's four NG911 layers that is not a
    corner case but the modal small-ring shape: 138 of the 241 rings under 200 m2
    have a mean width under 0.5 m, and the narrowest print 0.000 m over spans of
    32 m, 470 m, 691 m and 2,289 m. The old test missed 31 rings across those four
    layers (fire 7, law 14, psap 3, ems 7), so EVERY harm count this module has
    produced before this change is a FLOOR rather than a count.

    WHAT REPLACES IT NEEDS NOTHING MEASURED. `-simplify` REMOVES vertices; it does
    not move them and does not merge rings, and both sides are written at the same
    `precision=`, so every drawn ring's vertices are an exact SUBSET of the vertices
    of one source ring. Claim each drawn ring to its source ring; the unclaimed
    source rings are the dropped ones.

    A SMALL DRAWN RING CAN SIT INSIDE TWO SOURCE RINGS' VERTEX SETS, and that is
    resolved by ELIMINATION rather than by a heuristic. Measured, one case exists on
    these layers: Appleton Police's 4-vertex drawn ring is a subset of both a
    71-vertex ring and a 9-vertex ring that share those four vertices. Unambiguous
    claims are taken first; an ambiguous drawn ring then takes the one candidate
    still unclaimed. Where that leaves no single candidate this RAISES rather than
    guessing, because picking one would silently attribute a drop to the wrong ring.

    THAT SENTENCE CLAIMED A GATE THAT DOES NOT EXIST, and it stays above its
    correction: "AND THE COUNT IS GATED AGAINST ARITHMETIC NOBODY HERE CONTROLS:
    per key, the number of unclaimed source rings must equal len(source rings) -
    len(drawn rings). That identity held on all four NG911 layers at 165, 118, 10
    and 149, so the test is checked against the ring counts rather than trusted."
    The identity is TRUE BY CONSTRUCTION: the loop above gives every drawn ring
    exactly one free source ring or raises, so len(claimed) == len(dr) whenever
    this returns, hence len(out) == len(sr) - len(dr) always. Verified by trying to
    build a return value that violates it -- a drawn ring matching no source ring,
    two drawn rings wanting one source ring, more drawn rings than source rings --
    and every attempt RAISES instead of returning. Nothing outside the function
    asserts it either; the 165/118/10/149 reading was a development measurement and
    nothing re-checks it. Adding that assertion anywhere would be the vacuous gate
    two post-checks were already removed for.

    WHAT ACTUALLY PROTECTS THIS, both real and both in code: the RAISE above, which
    is what makes the removes-but-never-moves assumption checkable rather than
    assumed -- a simplifier that MOVED a vertex would fail the subset test and stop
    the build -- and each declaring builder's PINNED per-layer counts beside its
    `ACCEPTED_DROPPED_RINGS`, so a change in the dropped set fails until a person
    re-reads it. Neither is arithmetic this function controls.
    """
    src, drawn = _by_key(source_features, key_prop), _by_key(drawn_features, key_prop)
    out = []
    for key, sf in src.items():
        df = drawn.get(key)
        if df is None:
            continue
        dr, sr = rings(df["geometry"]), rings(sf["geometry"])
        if not dr or not sr:
            continue
        vsets = [set(map(tuple, r)) for r in sr]
        hits = []
        for d in dr:
            dv = set(map(tuple, d))
            hits.append([i for i, vs in enumerate(vsets) if dv <= vs])
        claimed = set()
        for cand in sorted(range(len(dr)), key=lambda j: len(hits[j])):
            free = [i for i in hits[cand] if i not in claimed]
            if len(free) == 1:
                claimed.add(free[0])
                continue
            raise RuntimeError(
                "%r drawn ring %d of %d (%d vertices) matches %d source ring(s) and "
                "%d of them are still unclaimed; a drawn ring's vertices are a subset "
                "of exactly one source ring's unless two source rings share them, and "
                "that is resolved by elimination. Picking one here would attribute a "
                "dropped ring to the wrong shape, so this stops instead."
                % (key, cand, len(dr), len(dr[cand]), len(hits[cand]), len(free)))
        # NO POST-CHECK HERE, AND TWO WERE WRITTEN AND REMOVED. A draft asserted
        # `len(claimed) == len(dr)` and then that the unclaimed count equals
        # len(sr) - len(dr); NEITHER CAN FIRE. The loop above adds exactly one
        # element per drawn ring or raises, and `free` excludes what is already
        # claimed, so the first is true by construction and the second follows from
        # it arithmetically. Shipping a guard that cannot fail is the vacuous-gate
        # failure this repository records elsewhere, so the identity is checked
        # where it is not implied -- against the ring counts, outside this function,
        # which is how it was verified at 165, 118, 10 and 149 on the NG911 layers.
        for i in range(len(sr)):
            if i in claimed:
                continue
            out.append((key, sr[i]))
    return out


def interior_at_precision(pts, ring, lo=6, hi=12):
    """The first sampled point that is STILL inside once rounded, and to how many
    decimals it had to be kept.

    Rounding is not free and this project has paid for it once: at 45.41 N the
    FOURTH decimal is 11.05 m of latitude and 7.81 m of longitude, so rounding a
    point to it displaced it out of a ring 7.5 m across and the answer measured
    there was the surrounding water. Six decimals is about 0.1 m, which is inside
    any ring of a few square metres — but it is NOT enough for every ring here,
    and that is measured rather than assumed: a 0.04 m2 ring in Fond du Lac
    County holds no 6-decimal point at all, so the precision RISES per ring until
    the rounded point is provably inside, instead of a fixed 6 that silently
    yields nothing.

    Returns ((lng, lat), decimals) or (None, None).
    """
    for nd in range(lo, hi + 1):
        for p in pts:
            q = (round(p[0], nd), round(p[1], nd))
            if point_in_ring(q, ring):
                return q, nd
    return None, None


def _merge_coincident(groups):
    """One SLIVER is one record, even when two districts each drew it separately.

    Grouping by `ring_signature` alone is not enough: where a boundary sliver
    belongs to two districts, each county's submission traces it with its own
    vertices, so the two rings coincide on the ground and differ byte for byte.
    Measured on the supervisory layer, that produced TWO harm records for one
    0.84 m2 sliver in Grant County — and no single declaration can satisfy both,
    because each names a different district in its `features`.

    So groups are merged when they pass the SAME identity test a declaration is
    matched on, `RING_MATCH_M` and `RING_MATCH_AREA`. The merge is deterministic:
    signatures are visited in sorted order and each joins the first cluster it
    matches.
    """
    out = []
    for sig in sorted(groups):
        g = groups[sig]
        c, m2 = ring_centre(g["ring"]), ring_area_m2(g["ring"])
        for o in out:
            sx, sy = mscale(o["centre"][1])
            d = math.hypot((c[0] - o["centre"][0]) * sx, (c[1] - o["centre"][1]) * sy)
            span = max(m2, o["m2"], 1e-6) * RING_MATCH_AREA
            if d <= RING_MATCH_M and abs(m2 - o["m2"]) <= max(span, 0.01):
                o["features"].extend(g["features"])
                o["signatures"].extend(g["signatures"])
                break
        else:
            out.append({"ring": g["ring"], "features": list(g["features"]),
                        "signatures": list(g["signatures"]),
                        "centre": c, "m2": m2})
    return {i: o for i, o in enumerate(out)}


def classify(layers):
    """Every dropped ring, grouped by geometry, with the answer it changes.

    `layers` is {name: {"source": [...], "drawn": [...], "key": "PROP"}}. One
    ring can be dropped from several features and several layers at once, so the
    grouping is by `ring_signature` and each record names every feature it was
    dropped from.

    A RECORD CARRIES `signatures`, PLURAL, so a caller can ask whether a given
    source ring was dropped without re-deciding it with a second copy of the
    threshold. Plural because a record is a CLUSTER: `_merge_coincident` folds
    rings that coincide on the ground but differ byte for byte, which is what two
    districts tracing one sliver with their own vertices produces. Measured on
    Wisconsin's chambers, the Door County sliver has TWO signatures behind one
    record — district 1's tracing and the water pseudo-district's — so a singular
    field covers one of them and a caller filtering on it sees the other ring as
    retained. That is not hypothetical: it is how the chambers builder's fidelity
    gate failed on 17.5 m the first time this field was wired up, which is the
    same two-readers defect arriving through the fix for it.

    THE ANSWER IS RECORDED PER LAYER BECAUSE IT DIFFERS BY LAYER FOR ONE RING.
    Wisconsin's Door County ring leaves Senate 1 for the SENATE water row and
    Assembly 1 for the ASSEMBLY water row, which are different strings; testing
    one layer and assuming the other would leave half of every declaration in a
    multi-layer family unchecked. Carried here from the chambers builder's own
    hand-written gate, which this replaces.

    Returns (records, stats). A record is::

        {"m2", "verts", "features": ["layer:key", ...], "kinds": [...],
         "kind": "wrong-name", "harm": True, "interior": {"lat", "lng"},
         "answers": {layer: {"before": [...], "after": [...]}},
         "signatures": [ring_signature(r), ...], "sampled": n, "mixed": False}

    `mixed` is a ring that answers DIFFERENTLY at different points inside itself.
    It is reported rather than reduced to one pair, because no single declaration
    describes such a ring and a human should look at it. Measured: none at
    Douglas-Peucker interval 4 through 25, two at the visvalingam setting this
    replaces.
    """
    mods = {}
    groups = {}
    for name, spec in layers.items():
        mods[name] = (model(spec["source"], spec["key"]),
                      model(spec["drawn"], spec["key"]))
        for key, ring in find_dropped(spec["source"], spec["drawn"], spec["key"]):
            sig = ring_signature(ring)
            g = groups.setdefault(sig, {"ring": ring, "features": [],
                                       "signatures": [sig]})
            g["features"].append("%s:%s" % (name, key))
    groups = _merge_coincident(groups)

    records = []
    stats = {KIND_UNCHANGED: 0, KIND_GAP_CLOSED: 0, KIND_WRONG_NAME: 0,
             KIND_FALSE_SILENCE: 0, KIND_DEGENERATE: 0,
             "rings": len(groups), "mixed": 0}
    for sig, g in groups.items():
        ring = g["ring"]
        m2 = ring_area_m2(ring)
        pts = interior_points(ring)
        if not pts:
            # A ring with no inside cannot change an answer — but only below the
            # measured bound. Above it, the SAMPLER failed and the caller must
            # not be told the ring is harmless.
            stats[KIND_DEGENERATE] += 1
            records.append({"m2": m2, "verts": ring_verts(ring),
                            "centre": ring_centre(ring),
                            "signatures": sorted(set(g["signatures"])),
                            "features": sorted(g["features"]),
                            "kinds": [KIND_DEGENERATE], "kind": KIND_DEGENERATE,
                            "harm": False, "interior": None, "answers": {},
                            "sampled": 0, "mixed": False,
                            "oversized": m2 > DEGENERATE_MAX_M2})
            continue
        pairs = {}
        sets = {}
        kinds = set()
        for name, (sm, dm) in mods.items():
            if not any(f.startswith(name + ":") for f in g["features"]):
                continue
            sets.setdefault(name, set())
            seen = set()
            for p in pts:
                before, after = reader_answer(sm, p), reader_answer(dm, p)
                sets[name].add((districts_at(sm, p), districts_at(dm, p)))
                seen.add((before, after))
                if before == after:
                    continue
                kinds.add(KIND_GAP_CLOSED if before is None else
                          (KIND_FALSE_SILENCE if after is None else KIND_WRONG_NAME))
            pairs[name] = sorted(seen, key=lambda t: (t[0] or "", t[1] or ""))
        mixed = any(len(v) > 1 for v in pairs.values())
        harm = bool(kinds & set(HARM_KINDS))
        kind = "+".join(sorted(kinds)) if kinds else KIND_UNCHANGED
        if not kinds:
            stats[KIND_UNCHANGED] += 1
        else:
            for k in kinds:
                stats[k] += 1
        if mixed:
            stats["mixed"] += 1
        interior, idec = interior_at_precision(pts, ring)
        answers = {}
        for name, prs in pairs.items():
            b, a = prs[0]
            sb, sa = sorted(sets.get(name, {((), ())}))[0]
            answers[name] = {"before": [b] if b else [], "after": [a] if a else [],
                             "before_all": list(sb), "after_all": list(sa),
                             # EVERY distinct pair measured inside the ring, not
                             # only the first. A ring inside a place where the
                             # SOURCE overlaps itself answers several ways, and
                             # until 2026-09-27 that list was computed here and
                             # thrown away, leaving `check` with nothing to hold a
                             # declaration of such a ring to.
                             "pairs": [{"before": [x] if x else [],
                                        "after": [y] if y else []}
                                       for x, y in prs]}
        records.append({"m2": m2, "verts": ring_verts(ring),
                        "centre": ring_centre(ring), "ring": ring,
                        "signatures": sorted(set(g["signatures"])),
                        "features": sorted(g["features"]),
                        "kinds": sorted(kinds) or [KIND_UNCHANGED], "kind": kind,
                        "harm": harm,
                        "interior": ({"lat": interior[1], "lng": interior[0],
                                      "decimals": idec} if interior else None),
                        "answers": answers, "sampled": len(pts), "mixed": mixed,
                        "oversized": False})
    records.sort(key=lambda r: -r["m2"])
    return records, stats


# Figures a declaration's own PROSE states, in the two units its own fields carry.
# Anchored so a number is read only where the unit follows it: `6.35 m2`,
# `18 vertices`, `4-vertex`. A bare number in prose ("dp at 1, 5 and 15 m all drop
# it") is not a claim about this ring and is not read as one.
_WHY_AREA = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*m2\b")
_WHY_VERTS = re.compile(r"(?<![\d.])(\d+)[\s-]*(?:vertices|vertex)\b")


def _why_disagreements(dec):
    """Numbers a declaration's `why` states that the declaration's own fields
    contradict, as a list of sentences.

    `check()` reads every other field of a declaration against the measurement
    and never read `why` — the one field a person actually reads. On 2026-09-27
    the aldermanic table shipped a `why` saying 6.06 m2 beside an `m2` of 6.35,
    a superseded figure left in the prose when the field was corrected; it was
    caught on review, by a person, and nothing here could have caught it.
    `_match`'s area tolerance is RING_MATCH_AREA, 10%, so that gate had no
    chance of it either — 0.29 m2 on a 6.35 m2 ring is well inside 10%.

    So this holds the declaration INTERNALLY consistent: the prose against the
    fields, where `_match` already holds the fields against the ring. The
    comparand is the DECLARED value rather than the measured one deliberately —
    two numbers a reader of the table sees at once are what went wrong, and
    holding the prose to the measurement instead would let a table read
    inconsistently while passing.

    An area must be a valid rounding of `m2` AT THE PRECISION THE PROSE WRITES
    IT TO, so `31.7 m2` for 31.70 passes and `6 m2` for 6.35 passes, while a
    prose figure MORE precise than the field fails — writing 36.749 beside a
    field of 36.75 is the same inconsistency pointing the other way. A vertex
    count is exact. A `why` stating neither is not checked: this reads
    arithmetic somebody wrote twice, never prose.
    """
    why = dec.get("why") or ""
    out = []
    for text in _WHY_AREA.findall(why):
        dp = len(text.split(".")[1]) if "." in text else 0
        if abs(float(text) - float(dec.get("m2", 0))) > 0.5 * (10 ** -dp):
            out.append("its `why` states %s m2 where its `m2` is %s"
                       % (text, dec.get("m2")))
    for text in _WHY_VERTS.findall(why):
        if int(text) != dec.get("verts"):
            out.append("its `why` states %s vertices where its `verts` is %s"
                       % (text, dec.get("verts")))
    return out


def check_prose(declarations):
    """Every declaration's `why` agrees with its own fields. Offline, no geometry.

    `check()` runs this too, but only on a BUILD path — which needs the network
    and mapshaper, so the prose of a table somebody edits by hand would be read
    by nobody until the next rebuild. That is the shape this repository keeps
    paying for: a measurement filed where the next pass does not look. This is
    the same reading with no inputs but the table itself, so it runs in CI.
    """
    problems = []
    for d in declarations:
        for said in _why_disagreements(d):
            problems.append("declaration at %.6f,%.6f contradicts itself: %s"
                            % (d["lat"], d["lng"], said))
    if problems:
        return False, "; ".join(problems)
    return True, "%d declaration(s): each `why` agrees with its own m2 and verts" % len(declarations)


def _declaring_modules(scripts_dir):
    """Builders that carry a declaration table, DISCOVERED from the tree.

    A hand-kept list here would go stale the first time a builder gains or loses
    its table, and a gate agreeing with its own list is the failure mode
    `validate_instance_registration.py` was written for. So this reads the
    directory: any `build_*.py` whose source names ACCEPTED_DROPPED_RINGS.
    """
    import os as _os
    found = []
    for name in sorted(_os.listdir(scripts_dir)):
        if not (name.startswith("build_") and name.endswith(".py")):
            continue
        with open(_os.path.join(scripts_dir, name)) as f:
            if "ACCEPTED_DROPPED_RINGS" in f.read():
                found.append(name[:-3])
    return found


def _check_all_declarations():
    """`--check`: every declaring builder's table, prose against its own fields.

    NEGATIVE-TESTING THIS NEEDS `python3 -B` OR A CLEARED `__pycache__`, and
    finding that out cost a wrong reading. It reads the tables by IMPORTING each
    builder, so it goes through Python's bytecode cache, which validates on the
    source's mtime TRUNCATED TO WHOLE SECONDS and its size. Breaking a `why` on
    purpose and restoring it within the same second — `6.35` for `6.06`, equal
    length — leaves both unchanged, so the interpreter reuses the broken
    bytecode and the gate goes on failing a file that is correct on disk.
    """
    import importlib
    import os as _os
    import sys as _sys
    here = _os.path.dirname(_os.path.abspath(__file__))
    _sys.path.insert(0, here)
    mods = _declaring_modules(here)
    if not mods:
        print("FAIL: no builder in %s declares ACCEPTED_DROPPED_RINGS — this gate "
              "cannot pass having found nothing to read" % here)
        return 1
    status = 0
    total = 0
    with_ceiling = []
    without = []
    for name in mods:
        mod = importlib.import_module(name)
        decs = getattr(mod, "ACCEPTED_DROPPED_RINGS")
        if isinstance(decs, dict):        # a multi-layer builder keys by layer
            decs = [d for layer in sorted(decs) for d in decs[layer]]
        total += len(decs)
        ok, msg = check_prose(decs)
        print("  %s %s: %s" % ("ok  " if ok else "FAIL", name, msg))
        if not ok:
            status = 1

        # A BUILDER'S TWO PER-LAYER TABLES MUST NAME THE SAME LAYERS. A layer that
        # gains a dropped-ring gate and silently lacks a fidelity ceiling is the
        # hand-kept-pair defect this repo keeps paying for, and it is checkable
        # offline even though the CEILING'S OWN DERIVATION is not: that needs the
        # median source step, which needs the fetch.
        ceil = getattr(mod, "FIDELITY_MAX_M", None)
        gaps = getattr(mod, "GAP_CLOSED", None)
        if ceil is None:
            without.append(name)
            continue
        with_ceiling.append(name)
        if isinstance(ceil, dict) and isinstance(gaps, dict):
            if set(ceil) != set(gaps):
                print("  FAIL %s: FIDELITY_MAX_M names %s and GAP_CLOSED names %s; "
                      "a layer with one and not the other is gated by half"
                      % (name, sorted(ceil), sorted(gaps)))
                status = 1
        elif isinstance(ceil, dict) != isinstance(gaps, dict):
            print("  FAIL %s: FIDELITY_MAX_M is %s and GAP_CLOSED is %s; one is "
                  "per-layer and the other is not"
                  % (name, type(ceil).__name__, type(gaps).__name__))
            status = 1

    # NAMED AND COUNTED RATHER THAN SILENT. These builders gate what their dissolve
    # DROPS and not how far their retained boundary MOVED, which is a real gap and
    # not a decision -- `check_fidelity` is layer-agnostic and each one needs its
    # own ceiling derived from its own median source step, which needs that
    # builder's fetch.
    if without:
        print("  note %d declaring builder(s) carry no FIDELITY_MAX_M, so their "
              "retained boundary is ungated: %s" % (len(without), ", ".join(without)))
    print("dropped-ring declarations: %d across %d builder(s); %d gate retained "
          "fidelity, %d do not%s"
          % (total, len(mods), len(with_ceiling), len(without),
             "" if not status else " — FAILED"))
    return status


def _match(rec, dec):
    """Is `dec` a declaration of `rec`'s ring? Centre and area, both."""
    sx, sy = mscale(rec["centre"][1])
    d = math.hypot((rec["centre"][0] - dec["lng"]) * sx,
                   (rec["centre"][1] - dec["lat"]) * sy)
    if d > RING_MATCH_M:
        return False
    span = max(rec["m2"], dec["m2"], 1e-6) * RING_MATCH_AREA
    return abs(rec["m2"] - dec["m2"]) <= max(span, 0.01)


def check(records, stats, declarations, gap_closed):
    """Every harming drop declared, every declaration found. Default is FAIL.

    THE DEFAULT IS THE POINT. A dropped ring that costs a reader the right answer
    fails this build unless somebody has written down which answer it costs, and
    a declaration that no longer matches anything fails too — the shape
    ACCEPTED_DROPS, EXPECTED_UNREACHABLE and ACCEPTED_SHORTFALLS already use
    across the fleet. What is NOT declared per ring is the drop that changes no
    answer, which is what keeps the table a handful instead of hundreds.

    `gap_closed` is the caller's expected count of holes that no district covered
    and the drawn output now fills. Those are not declared one by one — see the
    module docstring for the inference that rests on and why it is an inference —
    but the COUNT is held exactly, so a rebuild that starts closing a different
    number of them stops and gets read.
    """
    problems = []

    over = [r for r in records if r["kind"] == KIND_DEGENERATE and r["oversized"]]
    for r in over:
        problems.append(
            "ring of %.4f m2 at %.6f,%.6f yielded no interior point, and the "
            "measured bound for that is %.4f m2 — the SAMPLER failed, so this "
            "ring's answer is unknown rather than unchanged"
            % (r["m2"], r["centre"][1], r["centre"][0], DEGENERATE_MAX_M2))

    # A MIXED RING IS ONE THE SOURCE OR THE OUTPUT ANSWERS SEVERAL WAYS INSIDE,
    # and until 2026-09-27 it was an unconditional failure here with no remedy —
    # which made this gate unusable by any layer whose publisher files OVERLAPPING
    # polygons. Wisconsin's NG911 law layer is exactly that layer, and deliberately
    # so: its builder uses plain `-dissolve` rather than `-dissolve2` in order to
    # keep the real concurrent jurisdiction a sheriff and a municipal PD file over
    # the same ground. Measured that day, its four mixed rings at dp interval=1 are
    # one hairline under 1 m2 inside a THREE-way overlap of three Brown County
    # agencies' own filings, where the source itself answers differently point to
    # point; no interval resolves it, because the simplifier did not author it.
    #
    # So a mixed ring may now be declared — by declaring EVERY pair, in
    # `answer_pairs`, held to the measured set exactly. That is more written down
    # rather than less: the refusal stands for a mixed ring nobody has described,
    # and for one described with a single before/after pair, which is the claim
    # that cannot be true of it.
    mixed_ok = set()
    for r in records:
        if not r.get("mixed"):
            continue
        hit = [i for i, d in enumerate(declarations)
               if _match(r, d) and d.get("answer_pairs")]
        if r["harm"] and len(hit) == 1:
            mixed_ok.add(id(r))
            continue
        problems.append(
            "ring of %.2f m2 at %.6f,%.6f answers differently at different "
            "points inside itself (%s) — declare every pair in `answer_pairs`%s"
            % (r["m2"], r["centre"][1], r["centre"][0],
               "; ".join("%s: %d distinct" % (k, len(v["pairs"]))
                         for k, v in sorted(r["answers"].items())),
               "" if r["harm"] else ", and this one changes no answer at all, "
               "which this module cannot summarise either"))

    harms = [r for r in records if r["harm"]]
    used = set()
    for r in harms:
        hit = [i for i, d in enumerate(declarations) if _match(r, d)]
        if not hit:
            problems.append(
                "UNDECLARED %s: %.2f m2, %d vertices, at %.6f,%.6f, dropped from "
                "%s; a reader there is answered %s and would now be answered %s"
                % (r["kind"], r["m2"], r["verts"], r["centre"][1], r["centre"][0],
                   ", ".join(r["features"]),
                   _answer_text(r["answers"], "before"),
                   _answer_text(r["answers"], "after")))
            continue
        if len(hit) > 1:
            problems.append("ring at %.6f,%.6f matches %d declarations"
                            % (r["centre"][1], r["centre"][0], len(hit)))
        i = hit[0]
        used.add(i)
        d = declarations[i]
        if d.get("kind") != r["kind"]:
            problems.append("declaration at %.6f,%.6f calls it %r; measured %r"
                            % (d["lat"], d["lng"], d.get("kind"), r["kind"]))
        if sorted(d.get("features", [])) != r["features"]:
            problems.append("declaration at %.6f,%.6f names features %s; measured %s"
                            % (d["lat"], d["lng"], sorted(d.get("features", [])),
                               r["features"]))
        if r.get("mixed"):
            # ONE FORM PER CASE. A mixed ring has no single before/after pair, so
            # the single-pair fields are refused on it rather than checked against
            # the arbitrary first one; a ring that answers one way is held to the
            # single pair and must NOT carry a set.
            if d.get("answer_before") or d.get("answer_after"):
                problems.append("declaration at %.6f,%.6f carries answer_before/"
                                "answer_after for a ring that answers several ways; "
                                "use answer_pairs alone" % (d["lat"], d["lng"]))
            want = {k: sorted((tuple(sorted(pr.get("before") or [])),
                               tuple(sorted(pr.get("after") or [])))
                              for pr in v)
                    for k, v in (d.get("answer_pairs") or {}).items()}
            got = {k: sorted((tuple(sorted(pr["before"])), tuple(sorted(pr["after"])))
                             for pr in v["pairs"])
                   for k, v in r["answers"].items()}
            if want != got:
                problems.append("declaration at %.6f,%.6f claims answer_pairs %s; "
                                "measured %s" % (d["lat"], d["lng"], want, got))
        else:
            if d.get("answer_pairs"):
                problems.append("declaration at %.6f,%.6f carries answer_pairs for a "
                                "ring that answers ONE way; use answer_before and "
                                "answer_after" % (d["lat"], d["lng"]))
            for which, field in (("before", "answer_before"), ("after", "answer_after")):
                want = {k: sorted(v) for k, v in (d.get(field) or {}).items()}
                got = {k: sorted(v[which]) for k, v in r["answers"].items()}
                if want != got:
                    problems.append("declaration at %.6f,%.6f claims %s %s; measured %s"
                                    % (d["lat"], d["lng"], field, want, got))
        ip = d.get("interior")
        if not ip:
            problems.append("declaration at %.6f,%.6f carries no interior point"
                            % (d["lat"], d["lng"]))
        elif "ring" in r and not point_in_ring((ip["lng"], ip["lat"]), r["ring"]):
            problems.append("declaration at %.6f,%.6f gives an interior point "
                            "(%.6f,%.6f) that is NOT inside its ring"
                            % (d["lat"], d["lng"], ip["lat"], ip["lng"]))
        for said in _why_disagreements(d):
            problems.append("declaration at %.6f,%.6f contradicts itself: %s"
                            % (d["lat"], d["lng"], said))

    for i, d in enumerate(declarations):
        if i not in used:
            problems.append("declaration at %.6f,%.6f matches no dropped ring — "
                            "the geometry moved, so retire or re-measure it"
                            % (d["lat"], d["lng"]))

    if stats[KIND_GAP_CLOSED] != gap_closed:
        problems.append(
            "%d dropped hole(s) that no district covered are now filled by one; "
            "the builder declares %d. Each moves a reader from 'no district' to "
            "the district around them, so the count is held rather than the rings"
            % (stats[KIND_GAP_CLOSED], gap_closed))

    if problems:
        return False, "; ".join(problems)
    return True, ("%d dropped ring(s): %d harm none (%d unchanged, %d degenerate), "
                  "%d close a coverage gap, %d declared harm(s) "
                  "(%d wrong-name, %d false-silence)"
                  % (stats["rings"], stats[KIND_UNCHANGED] + stats[KIND_DEGENERATE],
                     stats[KIND_UNCHANGED], stats[KIND_DEGENERATE],
                     stats[KIND_GAP_CLOSED], len(harms),
                     stats[KIND_WRONG_NAME], stats[KIND_FALSE_SILENCE]))


def _answer_text(answers, which):
    bits = []
    for layer, a in sorted(answers.items()):
        v = a[which]
        bits.append("%s %s" % (layer, ", ".join(v) if v else "NO DISTRICT"))
    return "; ".join(bits)


# --------------------------------------------------------------------------
# selftest — fixtures only, no network, no data files
# --------------------------------------------------------------------------

def _sq(lng, lat, w, h):
    """A closed rectangular ring, counter-clockwise."""
    return [[lng, lat], [lng + w, lat], [lng + w, lat + h], [lng, lat + h], [lng, lat]]


def _feat(key, geom):
    return {"properties": {"K": key}, "geometry": geom}


def _poly(*rs):
    return {"type": "Polygon", "coordinates": [list(r) for r in rs]}


def _multi(*polys):
    return {"type": "MultiPolygon",
            "coordinates": [[list(r) for r in p] for p in polys]}


def _selftest():
    fails = []

    def ck(name, cond, extra=""):
        if cond:
            print("  ok   %s" % name)
        else:
            fails.append(name)
            print("  FAIL %s %s" % (name, extra))

    OUT = _sq(-89.00, 44.00, 0.01, 0.01)          # ~800 m x 1110 m
    HOLE = _sq(-88.9960, 44.0040, 0.001, 0.001)   # ~80 m x 111 m
    HALF = _sq(-88.9960, 44.0040, 0.0005, 0.001)  # left half of the hole

    def run(src, drawn):
        return classify({"L": {"source": src, "drawn": drawn, "key": "K"}})

    # 1. a retained ring is not reported dropped at all
    recs, st = run([_feat("A", _poly(OUT, HOLE))], [_feat("A", _poly(OUT, HOLE))])
    ck("a ring the drawn output keeps is not reported dropped", st["rings"] == 0)

    # 2. a dropped hole no district covers -> gap-closed, not harm
    recs, st = run([_feat("A", _poly(OUT, HOLE))], [_feat("A", _poly(OUT))])
    ck("a dropped hole nobody covers is gap-closed",
       st["rings"] == 1 and st[KIND_GAP_CLOSED] == 1 and not recs[0]["harm"],
       "got %s" % st)
    ck("gap-closed records the answer both ways",
       recs and recs[0]["answers"]["L"]["before"] == []
       and recs[0]["answers"]["L"]["after"] == ["A"],
       "got %s" % (recs[0]["answers"] if recs else None))

    # 3. a dropped hole ANOTHER district fills -> wrong-name, a harm
    src = [_feat("A", _poly(OUT, HOLE)), _feat("B", _poly(HOLE))]
    drw = [_feat("A", _poly(OUT)), _feat("B", _poly(HOLE))]
    recs, st = run(src, drw)
    h = [r for r in recs if r["harm"]]
    ck("a dropped hole another district fills is wrong-name",
       len(h) == 1 and h[0]["kind"] == KIND_WRONG_NAME, "got %s" % st)
    # THE READER'S ANSWER AND THE SET ARE DIFFERENT FACTS, and this fixture is
    # where that shows: the reader goes from B to A because A comes first in the
    # file, while the SET grows from {B} to {A, B}. A gate judging the set would
    # call this a harm on a page whose card never mentioned B.
    ck("wrong-name names the reader's answer, and the set beside it",
       h and h[0]["answers"]["L"]["before"] == ["B"]
       and h[0]["answers"]["L"]["after"] == ["A"]
       and h[0]["answers"]["L"]["after_all"] == ["A", "B"],
       "got %s" % (h[0]["answers"] if h else None))

    # 4. a dropped detached PART -> false-silence
    FAR = _sq(-88.90, 44.00, 0.002, 0.002)
    recs, st = run([_feat("C", _multi([OUT], [FAR]))], [_feat("C", _poly(OUT))])
    h = [r for r in recs if r["harm"]]
    ck("a dropped detached part is false-silence",
       len(h) == 1 and h[0]["kind"] == KIND_FALSE_SILENCE, "got %s" % st)
    ck("false-silence records an empty AFTER",
       h and h[0]["answers"]["L"]["after"] == [], "got %s" % (h[0]["answers"] if h else None))

    # 5. a ring below one coordinate cell is degenerate, and harmless
    # COLLINEAR, which is what the real ones are: measured, all 109 rings the
    # sampler cannot reach on the supervisory layer are at or below 0.002 m2. A
    # small TRIANGLE is not the fixture for this — a 0.44 m2 one is sampleable,
    # and writing that first is what proved the sampler reaches genuinely small
    # rings rather than giving up on them.
    TINY = [[-88.9950, 44.0050], [-88.99499, 44.0050], [-88.99498, 44.0050],
            [-88.9950, 44.0050]]
    recs, st = run([_feat("A", _poly(OUT, TINY))], [_feat("A", _poly(OUT))])
    ck("a sub-cell ring is degenerate rather than a harm",
       st[KIND_DEGENERATE] == 1 and not any(r["harm"] for r in recs), "got %s" % st)
    ok, msg = check(recs, st, [], st[KIND_GAP_CLOSED])
    ck("a degenerate ring under the bound does not fail the gate", ok, msg)

    # 6. an UNSAMPLEABLE ring ABOVE the bound must FAIL — the sampler failed, so
    #    the ring's answer is unknown rather than unchanged. Forced by making the
    #    sampler return nothing, which is the only honest way to reach this state.
    global interior_points
    real = interior_points
    try:
        interior_points = lambda ring, max_pts=SCANLINE_MAX_POINTS: []
        recs, st = run([_feat("A", _poly(OUT, HOLE))], [_feat("A", _poly(OUT))])
        ok, msg = check(recs, st, [], st[KIND_GAP_CLOSED])
        ck("an unsampleable ring above the bound FAILS", not ok and "SAMPLER failed" in msg, msg)
    finally:
        interior_points = real

    # 7. a ring that answers two ways inside itself FAILS rather than picking one
    src = [_feat("D", _poly(OUT, HOLE)), _feat("E", _poly(HALF))]
    drw = [_feat("D", _poly(OUT)), _feat("E", _poly(HALF))]
    recs, st = run(src, drw)
    ck("a ring answering two ways is reported mixed", st["mixed"] == 1, "got %s" % st)
    ok, msg = check(recs, st, [], st[KIND_GAP_CLOSED])
    ck("a mixed ring FAILS", not ok and "differently at different" in msg, msg)

    # 6a. THE CASE THE OLD RETAINED TEST MISSED, which is what makes this fixture
    #     worth having: a separate source ring SHARING A VERTEX with the main body.
    #     The old test asked whether ANY vertex was within RETAINED_RING_M of the
    #     feature's drawn geometry and called the ring retained when one was, so a
    #     hairline joined to the main body read as kept while being entirely gone.
    TOUCH = [[-89.00, 44.00], [-88.9980, 44.000002], [-88.9990, 44.000004],
             [-89.00, 44.00]]
    sf = _feat("A", _multi([OUT], [TOUCH]))
    df = _feat("A", _poly(OUT))
    got = find_dropped([sf], [df], "K")
    ck("a ring sharing a vertex with the main body is found dropped",
       len(got) == 1 and ring_signature(got[0][1]) == ring_signature(TOUCH),
       "found %d" % len(got))
    # ... and this is the property that made the old test miss it, asserted rather
    # than described, so the fixture cannot quietly stop exercising the fix.
    _g, _c = index_segments(rings(df["geometry"]))
    _sx, _sy = mscale(TOUCH[0][1])
    ck("the fixture really is the shape the old threshold called retained",
       min(dist_to_drawn((p[0], p[1]), _g, _c, _sx, _sy) for p in TOUCH)
       <= RETAINED_RING_M,
       "its nearest vertex is further than RETAINED_RING_M, so it tests nothing")

    # 6b. A SMALL DRAWN RING INSIDE TWO SOURCE RINGS' VERTEX SETS resolves by
    #     elimination, never by picking. Measured, one real case exists: Appleton
    #     Police's 4-vertex drawn ring is a subset of both a 71-vertex ring and a
    #     9-vertex ring that share those four vertices.
    SHARED = [[-88.50, 44.50], [-88.49, 44.50], [-88.49, 44.51], [-88.50, 44.50]]
    BIG = SHARED[:-1] + [[-88.48, 44.52], [-88.50, 44.52], [-88.50, 44.50]]
    sf = _feat("A", _multi([BIG], [SHARED]))
    df = _feat("A", _multi([BIG], [SHARED]))
    got = find_dropped([sf], [df], "K")
    ck("two source rings sharing a vertex set resolve by elimination, nothing dropped",
       got == [], "found %d" % len(got))

    # 6c. ... and where elimination leaves no single candidate it RAISES rather than
    #     attributing the drop to the wrong shape.
    df = _feat("A", _poly(SHARED))
    try:
        find_dropped([sf], [df], "K")
        ck("an unresolvable ambiguity RAISES", False, "it returned instead")
    except RuntimeError as exc:
        ck("an unresolvable ambiguity RAISES", "resolved by elimination" in str(exc),
           str(exc)[:90])

    # 7a. ... and PASSES once every pair it shows is declared. This fixture's hole
    #      answers E before and D after on its left half, where E covers, and
    #      NOTHING before and D after on its right half, where nobody does — two
    #      pairs, one ring. Until 2026-09-27 no declaration could describe it, which
    #      made this gate unusable by any layer whose source overlaps itself.
    mr = [r for r in recs if r.get("mixed")][0]
    mixed_dec = {"lat": mr["centre"][1], "lng": mr["centre"][0], "m2": mr["m2"],
                 "verts": mr["verts"], "interior": mr["interior"],
                 "features": mr["features"], "kind": mr["kind"],
                 "answer_pairs": {"L": mr["answers"]["L"]["pairs"]},
                 "why": "fixture", "date": "2026-09-27"}
    ok, msg = check(recs, st, [mixed_dec], st[KIND_GAP_CLOSED])
    ck("a mixed ring declaring every pair passes", ok, msg)
    ck("the fixture really does show more than one pair",
       len(mr["answers"]["L"]["pairs"]) > 1,
       "pairs=%s" % mr["answers"]["L"]["pairs"])

    short = dict(mixed_dec)
    short["answer_pairs"] = {"L": mr["answers"]["L"]["pairs"][:1]}
    ok, msg = check(recs, st, [short], st[KIND_GAP_CLOSED])
    ck("a mixed ring declaring only SOME of its pairs FAILS",
       not ok and "claims answer_pairs" in msg, msg)

    single = dict(mixed_dec)
    del single["answer_pairs"]
    single["answer_before"] = {"L": mr["answers"]["L"]["before"]}
    single["answer_after"] = {"L": mr["answers"]["L"]["after"]}
    ok, msg = check(recs, st, [single], st[KIND_GAP_CLOSED])
    ck("a mixed ring declared with ONE pair still FAILS",
       not ok and "declare every pair" in msg, msg)

    both = dict(mixed_dec)
    both["answer_before"] = {"L": mr["answers"]["L"]["before"]}
    ok, msg = check(recs, st, [both], st[KIND_GAP_CLOSED])
    ck("a mixed ring carrying both forms FAILS",
       not ok and "use answer_pairs alone" in msg, msg)

    # 8. the declaration contract: undeclared harm fails; a good declaration passes
    src = [_feat("A", _poly(OUT, HOLE)), _feat("B", _poly(HOLE))]
    drw = [_feat("A", _poly(OUT)), _feat("B", _poly(HOLE))]
    recs, st = run(src, drw)
    ok, msg = check(recs, st, [], st[KIND_GAP_CLOSED])
    ck("an undeclared harm FAILS", not ok and "UNDECLARED wrong-name" in msg, msg)
    h = [r for r in recs if r["harm"]][0]
    good = {"lat": h["centre"][1], "lng": h["centre"][0], "m2": h["m2"],
            "verts": h["verts"], "interior": h["interior"], "features": h["features"],
            "kind": h["kind"],
            "answer_before": {"L": h["answers"]["L"]["before"]},
            "answer_after": {"L": h["answers"]["L"]["after"]},
            "why": "fixture", "date": "2026-09-26"}
    ok, msg = check(recs, st, [good], st[KIND_GAP_CLOSED])
    ck("a correct declaration passes", ok, msg)

    # 9. every field of the declaration is load-bearing
    for field, mutate, want in (
            ("kind", lambda d: d.update(kind=KIND_FALSE_SILENCE), "calls it"),
            ("answer_before", lambda d: d.update(answer_before={"L": ["Z"]}), "answer_before"),
            ("answer_after", lambda d: d.update(answer_after={"L": ["Z"]}), "answer_after"),
            ("features", lambda d: d.update(features=["L:zzz"]), "names features"),
            ("interior", lambda d: d.update(interior={"lat": 44.5, "lng": -89.5,
                                                      "decimals": 6}),
             "NOT inside")):
        bad = dict(good)
        mutate(bad)
        ok, msg = check(recs, st, [bad], st[KIND_GAP_CLOSED])
        ck("a wrong %s FAILS" % field, not ok and want in msg, msg)

    # 9b. ... and the pair SET is refused on a ring that answers one way, so there
    #      is exactly one form per case rather than two ways to say one thing.
    ok, msg = check(recs, st,
                    [dict(good, answer_pairs={"L": [{"before": ["B"], "after": ["A"]}]})],
                    st[KIND_GAP_CLOSED])
    ck("a single-answer ring declaring answer_pairs FAILS",
       not ok and "answers ONE way" in msg, msg)

    # 9a. the `why` PROSE is load-bearing too, which it was not until 2026-09-27.
    #     The failing fixture is the real defect: #1219 shipped a `why` saying
    #     6.06 m2 beside an `m2` of 6.35, and every gate here passed it.
    ok, msg = check(recs, st, [dict(good, why="%.2f m2 of dry land" % good["m2"])],
                    st[KIND_GAP_CLOSED])
    ck("a `why` agreeing with its own m2 passes", ok, msg)
    ok, msg = check(recs, st, [dict(good, why="6.06 m2 of dry land")],
                    st[KIND_GAP_CLOSED])
    ck("a `why` stating an m2 its own field contradicts FAILS",
       not ok and "contradicts itself" in msg and "6.06 m2" in msg, msg)
    ok, msg = check(recs, st, [dict(good, why="%d m2 of dry land" % round(good["m2"]))],
                    st[KIND_GAP_CLOSED])
    ck("a `why` rounding its own m2 to a whole number passes", ok, msg)
    # A BARE NUMBER IN PROSE IS NOT A CLAIM ABOUT THIS RING. Every real `why` in
    # the fleet names the settings it tested ("dp at 1, 5 and 15 m all drop it"),
    # and reading those as areas would fail every declaration there is.
    settings_why = ("visvalingam 25% and dp at 1, 5 and 15 m all drop it; "
                    + "%.2f m2 of dry land" % good["m2"])
    ok, msg = check(recs, st, [dict(good, why=settings_why)], st[KIND_GAP_CLOSED])
    ck("a `why` naming the settings it tested is not read as areas", ok, msg)
    ok, msg = check(recs, st,
                    [dict(good, why="a %d-vertex sliver" % (good["verts"] + 1))],
                    st[KIND_GAP_CLOSED])
    ck("a `why` stating a vertex count its own field contradicts FAILS",
       not ok and "vertices where its `verts`" in msg, msg)
    ok, msg = check(recs, st, [dict(good, why="a %d-vertex sliver" % good["verts"])],
                    st[KIND_GAP_CLOSED])
    ck("a `why` agreeing on its vertex count passes", ok, msg)

    # 9c. the stray measurement: DIRECTION, the dropped-ring skip, and the step.
    #
    # A known answer by construction: the source's bottom edge carries one extra
    # vertex pushed 0.0002 deg south of the straight edge the drawn ring keeps, so
    # the true line strays from the chord by exactly that in metres.
    BUMP_DY = 0.0002
    sxx, syy = mscale(44.0)
    expect_m = BUMP_DY * syy
    src_ring = [[-89.00, 44.00], [-88.995, 44.00 - BUMP_DY], [-88.99, 44.00],
                [-88.99, 44.01], [-89.00, 44.01], [-89.00, 44.00]]
    drawn_ring = [[-89.00, 44.00], [-88.99, 44.00],
                  [-88.99, 44.01], [-89.00, 44.01], [-89.00, 44.00]]
    S = {"A": _poly(src_ring)}
    D = {"A": _poly(drawn_ring)}
    sper, sst = measure_stray(S, D)
    ck("the stray is the TRUE line's distance from the drawn chord",
       abs(sst["worst"] - expect_m) < 0.05,
       "measured %.3f m, expected %.3f m" % (sst["worst"], expect_m))

    # THE OBVIOUS DIRECTION GATES NOTHING, and this is that claim as a test:
    # simplification keeps a SUBSET of the source vertices, so every drawn vertex
    # already lies on the source line and drawn -> source answers ~0 whatever the
    # setting. A gate measuring that way would pass anything.
    _per2, st2 = measure_stray(D, S)
    ck("measured the other way round it answers ~0, which is why it is not measured that way",
       st2["worst"] < 0.01, "got %.4f m" % st2["worst"])

    # A DROPPED RING MUST NOT BE MEASURED INTO THE STRAY. On the chambers layer
    # that mistake read 17.5 m against a 15 m ceiling on a ring that was not
    # there at all, so both halves are asserted: skipped when the caller names it,
    # and wildly over when it does not.
    HOLE2 = _sq(-88.996, 44.004, 0.001, 0.001)
    S2 = {"A": _poly(src_ring, HOLE2)}
    _per3, st3 = measure_stray(S2, D, dropped_sigs={ring_signature(HOLE2)})
    ck("a ring the caller calls dropped is skipped, not measured as stray",
       abs(st3["worst"] - expect_m) < 0.05 and st3["dropped"] == 1,
       "worst %.3f m, dropped %d" % (st3["worst"], st3["dropped"]))
    _per4, st4 = measure_stray(S2, D)
    ck("and pooling it instead blows the measurement up",
       st4["worst"] > expect_m * 3,
       "worst %.3f m against the real %.3f m" % (st4["worst"], expect_m))

    steps = source_step_m(S2, dropped_sigs={ring_signature(HOLE2)})
    ck("the step distribution covers the retained ring's own segments only",
       len(steps) == len(src_ring) - 1 and steps == sorted(steps),
       "got %d segment(s) for a %d-vertex ring" % (len(steps), len(src_ring)))

    ck("pct reads the ends and the middle of a sorted list",
       pct([], 50) == 0.0 and pct([5.0], 99) == 5.0
       and pct([0.0, 1.0, 2.0, 3.0, 4.0], 0) == 0.0
       and pct([0.0, 1.0, 2.0, 3.0, 4.0], 100) == 4.0
       and abs(pct([0.0, 1.0, 2.0, 3.0, 4.0], 50) - 2.0) < 1e-9,
       "pct misread")

    # 10. an orphan declaration fails, and the gap-closed count is held
    orphan = dict(good)
    orphan.update(lat=45.5, lng=-90.5)
    ok, msg = check(recs, st, [good, orphan], st[KIND_GAP_CLOSED])
    ck("a declaration matching nothing FAILS", not ok and "matches no dropped ring" in msg, msg)
    ok, msg = check(recs, st, [good], st[KIND_GAP_CLOSED] + 1)
    ck("a moved gap-closed count FAILS", not ok and "declares" in msg, msg)

    # 11. two districts drawing ONE sliver separately are one record, not two
    #
    # THE OFFSET MUST SURVIVE 6-DECIMAL ROUNDING or this fixture tests the wrong
    # mechanism. It was 1e-7 until 2026-09-27, which `ring_signature` rounds away,
    # so the two rings shared a signature and were folded by the grouping dict
    # while `_merge_coincident` — the thing this case exists to exercise — was
    # never reached. 2e-6 degrees is about 0.2 m: distinct signatures, same ground,
    # comfortably inside RING_MATCH_M and RING_MATCH_AREA.
    a = _sq(-88.50, 44.50, 0.0002, 0.0002)
    b = [[p[0] + 2e-6, p[1] + 2e-6] for p in a]          # same ground, other vertices
    src = [_feat("P", _poly(_sq(-88.60, 44.40, 0.02, 0.02), a)),
           _feat("Q", _poly(_sq(-88.52, 44.40, 0.02, 0.02), b))]
    drw = [_feat("P", _poly(_sq(-88.60, 44.40, 0.02, 0.02))),
           _feat("Q", _poly(_sq(-88.52, 44.40, 0.02, 0.02)))]
    recs, st = run(src, drw)
    ck("one sliver drawn twice is ONE record naming both districts",
       st["rings"] == 1 and recs and sorted(recs[0]["features"]) == ["L:P", "L:Q"],
       "rings=%d features=%s" % (st["rings"], recs[0]["features"] if recs else None))
    # ... and the record must name EVERY signature it folded, because a caller
    # filtering source rings on `signatures` sees any it omits as retained. This
    # is the chambers builder's fidelity gate, which failed on 17.5 m when the
    # field was singular.
    want = {ring_signature(a), ring_signature(b)}
    got = set(recs[0]["signatures"]) if recs else set()
    ck("a merged record names every signature it folded",
       len(want) == 2 and got == want,
       "distinct source signatures=%d, record carries %d" % (len(want), len(got)))

    # 12. the interior point's precision rises for a ring 6 decimals cannot hold
    NARROW = [[-88.9950, 44.00500], [-88.994990, 44.00500],
              [-88.994995, 44.005004], [-88.9950, 44.00500]]
    pts = interior_points(NARROW)
    if pts:
        q6, nd = interior_at_precision(pts, NARROW)
        ck("a ring too small for 6 decimals records more of them",
           q6 is None or nd >= 6, "decimals=%s" % nd)
    else:
        ck("a ring too small for 6 decimals records more of them", True)

    # 13. check_fidelity: a genuine chord across ground that changes hands FAILS.
    # A's source has a 60 m notch bitten out of its left edge which B fills; the
    # drawn A closes the notch, so A now covers ground the source gave to B.
    WIDE = _sq(-89.00, 44.00, 0.02, 0.01)
    NOTCH_SRC = [[-89.00, 44.000], [-88.99, 44.000], [-88.99, 44.010],
                 [-89.00, 44.010], [-89.00, 44.007],
                 [-88.9992, 44.005],            # ~64 m in from the edge
                 [-89.00, 44.003], [-89.00, 44.000]]
    NOTCH_DRAWN = [[-89.00, 44.000], [-88.99, 44.000], [-88.99, 44.010],
                   [-89.00, 44.010], [-89.00, 44.000]]
    FILLER = [[-89.00, 44.003], [-88.9992, 44.005], [-89.00, 44.007],
              [-89.002, 44.007], [-89.002, 44.003], [-89.00, 44.003]]
    src = [_feat("A", _poly(NOTCH_SRC)), _feat("B", _poly(FILLER))]
    drw = [_feat("A", _poly(NOTCH_DRAWN)), _feat("B", _poly(FILLER))]
    ok, msg = check_fidelity(src, drw, "K", set(), 10.0)
    ck("a chord across ground that changes hands FAILS the fidelity gate",
       not ok and "where the answer changes" in msg, "got %r" % msg)

    # 14. ... and the SAME geometry passes when the ceiling is above the stray,
    # which is what proves 13 failed on the metres rather than on the shape.
    ok2, msg2 = check_fidelity(src, drw, "K", set(), 500.0)
    ck("the same geometry passes under a ceiling above its stray", ok2,
       "got %r" % msg2)

    # 15. a SPUR is excluded by the measured predicate and counted, not failed.
    # The vertex sits 150 m out with its two neighbours at the same point, so the
    # ring doubles back through it and encloses nothing.
    SPUR_SRC = [[-89.00, 44.000], [-88.99, 44.000], [-88.99, 44.010],
                [-89.00, 44.010], [-89.00, 44.005],
                [-89.0019, 44.005],             # ~150 m out
                [-89.00, 44.005], [-89.00, 44.000]]
    ok3, msg3 = check_fidelity([_feat("A", _poly(SPUR_SRC))],
                               [_feat("A", _poly(NOTCH_DRAWN))], "K", set(), 10.0)
    ck("a zero-width spur is excluded as a spur and counted",
       ok3 and "1 spur(s)" in msg3, "got %r" % msg3)

    # 16. THE SAME NOTCH WITH NOBODY NEXT DOOR IS THE GAP-CLOSED DIRECTION, and
    # this assertion is why the gate reads a direction at all. It first asserted
    # that closing the notch "changes no answer", and it changes one: from NO
    # AGENCY to A. That is what `classify` calls gap-closed, counts, and does not
    # call harm -- so the gate counts it here too rather than failing.
    ok4, msg4 = check_fidelity([_feat("A", _poly(NOTCH_SRC))],
                               [_feat("A", _poly(NOTCH_DRAWN))], "K", set(), 10.0)
    ck("filling ground the source answered with nothing is counted, not failed",
       ok4 and "answered with nothing" in msg4, "got %r" % msg4)

    # 17. A FALSE SILENCE FAILS, which is the direction that makes 16 an exclusion
    # rather than a hole. A's source pushes a 64 m SPIKE out past its own edge and
    # the drawn output cuts the chord across its base, so a reader in the spike was
    # told A and is now told nothing, with no neighbour to step in.
    #
    # THE FIRST DRAFT OF THIS ASSERTION TESTED A DIRECTION SIMPLIFICATION CANNOT
    # PRODUCE: it swapped the two arguments, making the drawn ring the one with the
    # notch. The stray is measured SOURCE vertex to nearest DRAWN segment, and a
    # simplified ring's vertices are a subset of its source's, so every source
    # vertex sat at 0 and nothing was over the limit. The gate reported a clean
    # pass and the assertion read as a gate that could not see a false silence.
    SPIKE_SRC = [[-89.00, 44.000], [-88.99, 44.000], [-88.99, 44.010],
                 [-89.00, 44.010], [-89.00, 44.007],
                 [-89.0008, 44.005],            # ~64 m OUT past the edge
                 [-89.00, 44.003], [-89.00, 44.000]]
    ok5, msg5 = check_fidelity([_feat("A", _poly(SPIKE_SRC))],
                               [_feat("A", _poly(NOTCH_DRAWN))], "K", set(), 10.0)
    ck("cutting off a spike nobody else covers FAILS as a false silence",
       not ok5 and "NO DISTRICT" in msg5, "got %r" % msg5)

    print("%s — %d failure(s)" % ("dropped_rings selftest", len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    import sys as _sys
    if "--selftest" in _sys.argv[1:]:
        _sys.exit(_selftest())
    if "--check" in _sys.argv[1:]:
        _sys.exit(_check_all_declarations())
    print(__doc__)
